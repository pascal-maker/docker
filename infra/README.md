# GCP Terraform (dev, free tier, EU-only)

Infrastructure as code for the refactor-agent A2A backend and (later) dashboard. All resources are in **europe-west1** (Belgium, closest to Ghent) for **GDPR**; nothing is stored or run outside the EU.

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

1. **Create a tfvars file** (do not commit secrets):

   ```hcl
   # infra/dev.tfvars
   project_id = "your-gcp-project-id"
   region     = "europe-west1"
   a2a_image  = "europe-west1-docker.pkg.dev/your-gcp-project-id/refactor-agent/a2a-server:latest"
   ```

2. **Provider keys** (gitignored): copy `secrets.tfvars.example` to `secrets.tfvars`, set `anthropic_api_key` (and `chainlit_auth_secret` if using Chainlit). To change keys or add providers later: edit `secrets.tfvars` and run `terraform apply -var-file=dev.tfvars -var-file=secrets.tfvars` again.

3. **Build and push the A2A image** (from repo root):

   ```bash
   gcloud builds submit --tag europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/refactor-agent/a2a-server:latest . --project=YOUR_PROJECT_ID
   ```

   Or use the output after first apply:

   ```bash
   terraform -chdir=infra output -raw ar_repo
   # then: docker build -t $(terraform -chdir=infra output -raw ar_repo):latest . && docker push ...
   ```

4. **Terraform plan and apply** (after backend init above):

   ```bash
   cd infra
   terraform plan -var-file=dev.tfvars
   terraform apply -var-file=dev.tfvars
   ```

5. **Get the A2A URL**:

   ```bash
   terraform output a2a_url
   ```

   Use this URL in the VS Code extension (`refactorAgent.a2aBaseUrl`) or for local testing. Sync is not deployed; use workspace-in-JSON for hosted usage.

## Dev endpoints (staging / production)

Environments are **image tags** in Artifact Registry (no separate API): staging = tag from `main` (e.g. `:staging`), production = tag from a release (e.g. `:v1.0.0`). The same Cloud Run service is updated by pointing `a2a_image` at the desired tag.

- **Staging:** In your tfvars set `a2a_image = ".../a2a-server:staging"` and `a2a_min_instance_count = 1` so the first request avoids cold start. The [build-push workflow](../.github/workflows/build-push-images.yml) pushes `:staging` on push to `main`.
- **Production:** Set `a2a_image = ".../a2a-server:v1.0.0"` (or `:latest`) and keep `a2a_min_instance_count = 0` to scale to zero.
- **Outputs:** `a2a_url` is the A2A endpoint. When `chainlit_image` is set in tfvars, `chainlit_url` is the hosted Chainlit endpoint (transparent surface; restrict invoker via `chainlit_invoker_member`).

## Backend (state) – reminder

If you did not set up the GCS backend (see **Backend (state) – do this first** above), you are using local state. Prefer the GCS backend for locking and durability.

## Setting secret values

- Terraform only creates the **secret resources**; it never stores secret **values**.
- After `terraform apply`, add the first version of each secret with `gcloud secrets versions add ... --data-file=-` (as above).
- To rotate: add a new version; Cloud Run uses `version = "latest"` and will pick it up on next deploy or new instance.

## Outputs

| Output         | Description                                                |
|----------------|------------------------------------------------------------|
| `a2a_url`      | Cloud Run URL for the A2A service.                        |
| `chainlit_url` | Cloud Run URL for the Chainlit UI (when `chainlit_image` is set). |
| `project_id`   | GCP project ID.                                            |
| `ar_repo`      | Full Artifact Registry repo (for build/push).              |

## Region and GDPR

- **region** defaults to `europe-west1` (Belgium). All resources (Cloud Run, Artifact Registry, Secret Manager replica, Firestore) use this region so data stays in the EU.
