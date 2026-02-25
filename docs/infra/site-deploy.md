# Site and Auth Functions Deployment

The site and its auth/email Cloud Functions are deployed via **Terraform** (infra/site module) and **Firebase Hosting**. See [architecture-schematic.md](architecture-schematic.md) section 5 for the diagram.

## Prerequisites

- GitHub OAuth App for web (see [GitHub OAuth App setup](#github-oauth-app-setup) below)
- Resend account and API key (for admin email notifications)
- GCP project with Firestore, Secret Manager, Cloud Functions APIs enabled
- Firebase project (add GCP project in [Firebase Console](https://console.firebase.google.com))

### GitHub OAuth App setup

**GitHub does not provide an API to create OAuth Apps** — registration is manual.

1. Go to https://github.com/settings/applications/new
2. Create a new OAuth App with:

| Field | Value |
|-------|-------|
| **Application name** | `Refactor Agent` |
| **Homepage URL** | `https://refactorum.com` |
| **Authorization callback URL** | `https://europe-west1-PROJECT.cloudfunctions.net/auth-github-callback` |

3. Copy the **Client ID** and **Client secret**.
4. Add the client secret to Secret Manager: `echo -n "your_secret" | gcloud secrets versions add refactor-agent-github-oauth-client-secret --data-file=-`
5. Set `github_oauth_client_id` and `github_oauth_client_secret` in `secrets.tfvars`. For GitHub Actions to receive build-time env vars, also set `github_token` and `github_repository`; Terraform will sync `VITE_GITHUB_OAUTH_CLIENT_ID` and `VITE_AUTH_CALLBACK_URL`. Run `terraform apply -var-file=dev.tfvars -var-file=secrets.tfvars`.

**Reminder:** Update the GitHub OAuth App URLs from localhost to production before deploying.

## Terraform deployment

The site module (`infra/site/`) manages:

- **Auth callback** Cloud Function (HTTP) — OAuth code exchange, Firestore user creation
- **Email notify** Cloud Function (Firestore trigger) — Resend admin notification on new pending user
- **Firebase Hosting** site (optional; set `count = 1` in `firebase_hosting.tf` when ready)

Secrets (`refactor-agent-github-oauth-client-secret`, `refactor-agent-resend-api-key`) are created by Terraform; add values via `gcloud secrets versions add`.

## Site build and deploy

**Build:** `pnpm --filter site build` → `site/dist/`

**Build-time env:** `VITE_GITHUB_OAUTH_CLIENT_ID`, `VITE_AUTH_CALLBACK_URL` (synced to GitHub Actions by Terraform when `github_token`, `github_repository`, and the values are set in `secrets.tfvars`).

**Deploy:** CI runs `FirebaseExtended/action-hosting-deploy` on push to `main` when `site/` changes. Requires `FIREBASE_SERVICE_ACCOUNT` secret. **Terraform can sync it:** set `firebase_service_account_json` in `secrets.tfvars` (heredoc or one-line JSON) and run `terraform apply`; Terraform pushes the value to GitHub. Alternatively, add the JSON manually: GitHub → Settings → Secrets and variables → Actions → New repository secret → `FIREBASE_SERVICE_ACCOUNT`. Get the JSON from Firebase Console (Project Settings → Service accounts → Generate new private key) or `firebase init hosting:github`.

**Manual deploy:** `firebase deploy --only hosting`

## Custom domain and email

- **Domain:** refactorum.com (Cloudflare). DNS and Email Routing in `infra/cloudflare/` module.
- **Email:** noreply@ and admin@refactorum.com forward via Cloudflare Email Routing. Sending via Resend (verify domain in Resend Dashboard).

## Local testing

1. Copy `functions/auth_callback/.env.example` to `functions/auth_callback/.env`.
2. Run `./scripts/run_auth_callback_local.sh`.
3. Run the site: `pnpm --filter site dev`. Set `site/.env` with `VITE_GITHUB_OAUTH_CLIENT_ID` and `VITE_AUTH_CALLBACK_URL=http://localhost:8080/auth/github/callback`.
4. Firestore must be available (real GCP project with ADC).
