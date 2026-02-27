# GCP Terraform (dev, free tier, EU-only)

Infrastructure as code for the refactor-agent A2A backend and (later) dashboard. All resources are in **europe-west1** (Belgium, closest to Ghent) for **GDPR**; nothing is stored or run outside the EU.

## Layout

```
infra/
  main.tf, variables.tf, outputs.tf   # Root: providers, module calls, outputs
  dev.tfvars, secrets.tfvars.example

  shared/     # APIs, Firestore, secrets, GitHub Actions SA, Artifact Registry, Cloud Build, Sentry
  a2a/        # A2A Cloud Run service
  chainlit/   # Optional Chainlit Cloud Run
  site/       # Marketing site: Cloud Functions (auth, email), Firebase Hosting (planned)
  cloudflare/ # DNS and Email Routing for refactorum.com (planned)
```

If migrating from the previous flat structure, run `./scripts/migrate-state-to-modules.sh` before `terraform plan`.

**Firebase Hosting:** The `firebasehosting.googleapis.com` API is enabled via Terraform. You must also add the GCP project to Firebase: [Firebase Console](https://console.firebase.google.com) → Add project → Select existing GCP project. Then Terraform can manage `google_firebase_hosting_site`.

## Prerequisites

- [gcloud](https://cloud.google.com/sdk/docs/install) installed and logged in (`gcloud auth login`, `gcloud auth application-default login`).
- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.0.
- A GCP project with **billing enabled** (free-tier usage can still be $0).
- Docker (to build the A2A image).

## Backend (state) – do this first

**Local state is not safe** (no locking, easy to lose). Use a GCS backend in the same project and region (EU).

1. **Create the state bucket** (once per project, same region for GDPR):

   ```bash
   export PROJECT=your-gcp-project-id
   gsutil mb -l europe-west1 gs://${PROJECT}-terraform-state
   gsutil versioning set on gs://${PROJECT}-terraform-state
   ```

2. **Init Terraform with the backend** (from `infra/`):

   ```bash
   cd infra
   terraform init -reconfigure -backend-config="bucket=${PROJECT}-terraform-state"
   ```

   If you already have local state and want to migrate: run `terraform init -migrate-state` when prompted after adding the backend config.

3. **Optional**: Commit a `backend.config` (or use a script) so your bucket name is not in `main.tf`. You can also replace `REPLACE_OR_USE_BACKEND_CONFIG` in `main.tf` with your bucket name; then `terraform init -reconfigure` is enough.

## Quick start

1. **Create `dev.tfvars`** (project config; do not commit if it contains secrets):

   ```hcl
   # infra/dev.tfvars
   project_id = "your-gcp-project-id"
   region     = "europe-west1"
   a2a_image  = "europe-west1-docker.pkg.dev/your-gcp-project-id/refactor-agent/a2a-server:latest"
   ```

2. **Create `secrets.tfvars`** (gitignored): copy `secrets.tfvars.example` to `secrets.tfvars`. Set at least `anthropic_api_key`. See [Secrets and variables](#secrets-and-variables) for the full list.

3. **Build and push the A2A image** (from repo root):

   ```bash
   gcloud builds submit --tag europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/refactor-agent/a2a-server:latest . --project=YOUR_PROJECT_ID
   ```

   Or use the output after first apply: `terraform -chdir=infra output -raw ar_repo`.

4. **Terraform plan and apply** (after backend init above). Always use both var files:

   ```bash
   cd infra
   terraform plan -var-file=dev.tfvars -var-file=secrets.tfvars
   terraform apply -var-file=dev.tfvars -var-file=secrets.tfvars
   ```

   Or from repo root: `make infra-apply` (uses `dev.tfvars` and `secrets.tfvars` by default).

5. **Get the A2A URL**:

   ```bash
   terraform -chdir=infra output a2a_url
   ```

   Use this URL in the VS Code extension (`refactorAgent.a2aBaseUrl`) or for local testing.

## Probing and security check

From the repo root you can probe what is reachable with or without auth, and run a programmatic security check (e.g. in CI). The same checks run automatically in CI after deploy to staging; see `tests/security/` and the [Build and push images](../.github/workflows/build-push-images.yml) workflow.

- **Probe** (reports GET agent-card, GET `/`, POST message/send with/without auth):
  ```bash
  make probe-a2a A2A_URL=https://your-a2a-url.run.app
  ```
  Or pass the URL as the first argument: `uv run python scripts/a2a/probe_a2a.py https://...`

- **Security check** (exit 0/1 for CI; use `REQUIRE_AUTH_FOR_SEND=1` once you enforce auth so that POST without auth must return 401/403):
  ```bash
  make check-a2a-security A2A_URL=https://your-a2a-url.run.app
  REQUIRE_AUTH_FOR_SEND=1 make check-a2a-security A2A_URL=https://...
  ```

Today the A2A Cloud Run service allows unauthenticated invocations (`allUsers`). If you want only the agent card public and message/send behind auth, add application-level auth (e.g. require `Authorization: Bearer` for POST) and run the check with `REQUIRE_AUTH_FOR_SEND=1` so CI fails until the policy is satisfied.

## Dev endpoints (staging / production)

Environments are **image tags** in Artifact Registry (no separate API). Use **one version tag** for both: build once (e.g. `a2a-server:v0.2.0`), deploy to staging, then promote the same tag to production.

- **Staging:** In staging tfvars set `a2a_image = ".../a2a-server:v0.2.0"` and `a2a_min_instance_count = 1` (optional). Push a tag `v*` from `main` to trigger the [build-push workflow](../.github/workflows/build-push-images.yml); it builds and pushes that image tag. Apply with your staging tfvars.
- **Production:** After validating on staging, set the **same** `a2a_image = ".../a2a-server:v0.2.0"` in production tfvars and apply. No new build; same image promoted.
- **Outputs:** `a2a_url` is the A2A endpoint. When `chainlit_image` is set in tfvars, `chainlit_url` is the hosted Chainlit endpoint (restrict invoker via `chainlit_invoker_member`).

## Site deployment (Firebase Hosting)

The marketing site and auth/email Cloud Functions are in `infra/site/`. CI deploys via [deploy-site workflow](../.github/workflows/deploy-site.yml) when `site/` changes. See [docs/infra/site-deploy.md](../docs/infra/site-deploy.md) for GitHub OAuth, Resend, and Firebase setup. Terraform can sync `FIREBASE_SERVICE_ACCOUNT` to GitHub Actions when `firebase_service_account_json` is set in `secrets.tfvars` (see [Secrets and variables](#secrets-and-variables)).

## Backend (state) – reminder

If you did not set up the GCS backend (see **Backend (state) – do this first** above), you are using local state. Prefer the GCS backend for locking and durability.

## Secrets and variables

Terraform uses two var files:

| File | Purpose | Commit? |
|------|---------|---------|
| `dev.tfvars` | Project config: `project_id`, `region`, `a2a_image`, etc. | Optional (often env-specific) |
| `secrets.tfvars` | API keys, OAuth secrets, Firebase SA JSON, etc. | **Never** |

**Required in `secrets.tfvars` (minimal A2A):** `anthropic_api_key`.

**Optional (site, Chainlit, CI):** `chainlit_auth_secret`, `github_oauth_client_id`, `github_oauth_client_secret`, `github_token`, `github_repository`, `firebase_service_account_json`, `resend_api_key`, `sentry_auth_token`, `sentry_organization`, Cloudflare vars. See `secrets.tfvars.example` for the full list.

**GitHub Actions secrets sync:** When `github_token`, `github_repository`, and the relevant values are set in `secrets.tfvars`, Terraform syncs them to repo secrets: `VITE_GITHUB_OAUTH_CLIENT_ID`, `VITE_AUTH_CALLBACK_URL`, `FIREBASE_SERVICE_ACCOUNT`. For Firebase, put the service account JSON in `firebase_service_account_json` (heredoc or one-line). Alternatively, pass it at apply time: `terraform apply ... -var="firebase_service_account_json=$(cat firebase-sa.json | jq -c .)"`.

**Secret Manager:** Terraform creates the secret resources; you add values via `gcloud secrets versions add ... --data-file=-`. To rotate: add a new version; Cloud Run uses `version = "latest"` and picks it up on next deploy.

**Credentials rotation:** See [docs/infra/credentials-rotation.md](../docs/infra/credentials-rotation.md) for step-by-step instructions to rotate each credential (GitHub, Cloudflare, Resend, Firebase, Sentry, etc.) with correct permissions.

## Outputs

| Output         | Description                                                |
|----------------|------------------------------------------------------------|
| `a2a_url`      | Cloud Run URL for the A2A service.                        |
| `chainlit_url` | Cloud Run URL for the Chainlit UI (when `chainlit_image` is set). |
| `project_id`   | GCP project ID.                                            |
| `ar_repo`      | Full Artifact Registry repo (for build/push).              |

## Region and GDPR

- **region** defaults to `europe-west1` (Belgium). All resources (Cloud Run, Artifact Registry, Secret Manager replica, Firestore) use this region so data stays in the EU.
