# Site and Auth Functions Deployment

The site and its auth/email Cloud Functions are deployed via **Terraform** (infra/site module) and **Firebase Hosting**. See [architecture-schematic.md](architecture-schematic.md) section 5 for the diagram.

## Pre-deploy checklist (Terraform-first)

Use Terraform wherever possible. Manual steps only where APIs don't exist.

### 1. Manual steps (no Terraform API)

- [ ] **GitHub OAuth App** — https://github.com/settings/applications/new  
  | Field | Value |
  |-------|-------|
  | Application name | `Refactor Agent` |
  | Homepage URL | `https://refactorum.com` |
  | Authorization callback URL | `https://europe-west1-PROJECT.cloudfunctions.net/auth-github-callback` |
  Copy Client ID and Client secret.

- [ ] **Firebase project** — [Firebase Console](https://console.firebase.google.com) → Add project → select existing GCP project.

- [ ] **Firebase service account JSON** — Firebase Console → Project Settings → Service accounts → Generate new private key. Save for step 3.

### 2. Secret Manager (one-time)

Terraform creates the secret resources; you add values via gcloud:

```bash
echo -n "YOUR_GITHUB_OAUTH_CLIENT_SECRET" | gcloud secrets versions add refactor-agent-github-oauth-client-secret --data-file=- --project=PROJECT_ID
```

### 3. Terraform: set secrets.tfvars and apply

Add to `secrets.tfvars` (gitignored):

| Variable | Source |
|----------|--------|
| `github_token` | GitHub PAT with `admin:repo` |
| `github_repository` | `owner/refactor-agent` |
| `github_oauth_client_id` | From step 1 |
| `github_oauth_client_secret` | From step 1 |
| `firebase_service_account_json` | From step 1 (one-line JSON or heredoc) |
| `resend_api_key` | Resend Dashboard (for email notify) |

Then:

```bash
make infra-apply
```

Terraform syncs to GitHub Actions:

- `GCP_PROJECT_ID` (variable)
- `VITE_GITHUB_OAUTH_CLIENT_ID`
- `VITE_AUTH_CALLBACK_URL`
- `FIREBASE_SERVICE_ACCOUNT`

### 4. Optional: GDPR / legal (Belgium)

Add to `secrets.tfvars` (or `dev.tfvars`). Terraform syncs to GitHub Actions variables:

| Variable | Purpose |
|----------|---------|
| `vite_imprint_name` | Imprint name (e.g. "Thomas Decloedt") |
| `vite_imprint_email` | Contact email |
| `vite_privacy_policy_url` | Hosted URL (Termly/iubenda) or leave empty for `/privacy` |
| `vite_terms_url` | Hosted URL or leave empty for `/terms` |
| `vite_firebase_measurement_id` | Optional override. **Otherwise automatic:** Terraform creates a Firebase web app and syncs its Measurement ID. |

Then run `make infra-apply`. The deploy workflow passes these to the site build.

**Firebase Measurement ID:** Terraform creates a Firebase web app (`infra/site/firebase_web_app.tf`) and reads its Measurement ID. No manual step. Override with `vite_firebase_measurement_id` in tfvars if needed.

### 5. Deploy

- Push to `main` when `site/`, `functions/`, or `packages/design-system/` change → CI deploys.
- Or manual: `pnpm --filter site build` then `firebase deploy --only hosting`.

---

## GitHub OAuth App setup (detail)

**GitHub does not provide an API to create OAuth Apps** — registration is manual.

1. Go to https://github.com/settings/applications/new
2. Create a new OAuth App with the values in the table above (replace `PROJECT` with your GCP project ID).
3. Copy the **Client ID** and **Client secret**.
4. Add the client secret to Secret Manager (step 2 above).
5. Set `github_oauth_client_id` and `github_oauth_client_secret` in `secrets.tfvars`. With `github_token` and `github_repository`, Terraform syncs `VITE_GITHUB_OAUTH_CLIENT_ID` and `VITE_AUTH_CALLBACK_URL`. Run `terraform apply -var-file=dev.tfvars -var-file=secrets.tfvars`.

**Reminder:** Update the GitHub OAuth App URLs from localhost to production before deploying.

## Terraform deployment

The site module (`infra/site/`) manages:

- **Auth callback** Cloud Function (HTTP) — OAuth code exchange, Firestore user creation
- **Email notify** Cloud Function (Firestore trigger) — Resend admin notification on new pending user
- **Firebase Hosting** site (optional; set `count = 1` in `firebase_hosting.tf` when ready)

Secrets (`refactor-agent-github-oauth-client-secret`, `refactor-agent-resend-api-key`) are created by Terraform; add values via `gcloud secrets versions add`.

## Site build and deploy

**Build:** `pnpm --filter site build` → `site/dist/`

**Build-time env:** `VITE_GITHUB_OAUTH_CLIENT_ID`, `VITE_AUTH_CALLBACK_URL` (synced to GitHub Actions by Terraform). For GDPR compliance (Belgium): `VITE_PRIVACY_POLICY_URL`, `VITE_TERMS_URL`, `VITE_IMPRINT_NAME`, `VITE_IMPRINT_EMAIL`, `VITE_FIREBASE_MEASUREMENT_ID`. See `site/.env.example`.

**Deploy:** CI runs `FirebaseExtended/action-hosting-deploy` on push to `main` when `site/` changes. Requires `FIREBASE_SERVICE_ACCOUNT` secret. **Terraform can sync it:** set `firebase_service_account_json` in `secrets.tfvars` (heredoc or one-line JSON) and run `terraform apply`; Terraform pushes the value to GitHub. Alternatively, add the JSON manually: GitHub → Settings → Secrets and variables → Actions → New repository secret → `FIREBASE_SERVICE_ACCOUNT`. Get the JSON from Firebase Console (Project Settings → Service accounts → Generate new private key) or `firebase init hosting:github`.

**Manual deploy:** `firebase deploy --only hosting`

## Custom domain and email

- **Domain:** refactorum.com (Cloudflare). DNS and Email Routing in `infra/cloudflare/` module.
- **Email:** noreply@ and admin@refactorum.com forward via Cloudflare Email Routing. Sending via Resend (verify domain in Resend Dashboard).

## Local testing

1. Copy `functions/auth_callback/.env.example` to `functions/auth_callback/.env`.
2. Run `./scripts/run_auth_callback_local.sh`.
3. Run the site: `pnpm --filter site dev`. Copy `site/.env.example` to `site/.env` and set `VITE_GITHUB_OAUTH_CLIENT_ID`, `VITE_AUTH_CALLBACK_URL`, and optionally `VITE_IMPRINT_NAME`, `VITE_IMPRINT_EMAIL` for legal pages.
4. Firestore must be available (real GCP project with ADC).
