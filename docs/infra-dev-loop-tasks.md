# Dev loop: tasks to complete (you haven’t run Terraform yet)

Use this as a checklist. Go through in order; we can adjust as we go.

---

## Phase 1: GCP and Terraform (first time)

### 1.1 Prerequisites on your machine

- [x] **gcloud** installed and logged in:  
  `gcloud auth login` and `gcloud auth application-default login`
- [x] **Terraform** >= 1.0 installed
- [x] **Docker** available (for building images later)
- [x] Pick your **GCP project ID** (billing enabled; you already put it in GitHub secrets)

### 1.2 Create the Terraform state bucket (one-time per project)

Terraform state will live in GCS in the same project and region (EU).

- [x] Create bucket (replace `YOUR_PROJECT_ID` with your real project ID):

  ```bash
  export PROJECT=YOUR_PROJECT_ID
  gsutil mb -l europe-west1 gs://${PROJECT}-terraform-state
  gsutil versioning set on gs://${PROJECT}-terraform-state
  ```

### 1.3 Terraform backend and tfvars

- [x] **Init Terraform with GCS backend** (from repo root):

  ```bash
  cd infra
  terraform init -reconfigure -backend-config="bucket=YOUR_PROJECT_ID-terraform-state"
  ```

- [x] **Create a tfvars file** (do not commit it). Example `infra/dev.tfvars`:

  ```hcl
  project_id  = "YOUR_PROJECT_ID"
  region      = "europe-west1"
  a2a_image  = "europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/refactor-agent/a2a-server:latest"
  a2a_min_instance_count = 1   # optional: 1 for staging to avoid cold start
  # chainlit_image = "..."     # leave empty until you want hosted Chainlit
  # chainlit_invoker_member = "user:you@example.com"
  ```

  Use your real project ID. You don’t have an image yet; use `:latest` for the first apply (we’ll build and push in a later task).

### 1.4 Enable Cloud Build API and permissions via Terraform

So the image build is fully IaC-driven and the build SA can read the source and push images. Run a **targeted** apply (skips Cloud Run so you don't get "image not found" yet):

- [x] From **repo root**:

  ```bash
  make infra-bootstrap
  ```

  Uses `infra/dev.tfvars` by default. For another tfvars file: `make infra-bootstrap INFRA_VAR_FILE=other.tfvars`. Answer `yes` when prompted.

  **If you get "bucket name is not available" (409):** the bucket already exists. Import it, then run `make infra-bootstrap` again:

  ```bash
  cd infra && terraform import -var-file=dev.tfvars google_storage_bucket.cloudbuild refactor-agent_cloudbuild
  ```

  (Use your project ID in the bucket name if different.)

### 1.5 Build and push the A2A image (required before Cloud Run)

Cloud Run requires the image to already exist in Artifact Registry. From **repo root**:

- [x] Run:

  ```bash
  make image-push
  ```

  Uses `GCP_PROJECT_ID=refactor-agent` and tag `latest` by default. Override with `make image-push GCP_PROJECT_ID=your-project A2A_IMAGE_TAG=staging`. This creates the image so Terraform can attach the Cloud Run service to it.

### 1.6 Provider keys (secrets.tfvars) and full Terraform apply

Secrets are managed in Terraform via a **gitignored** `secrets.tfvars`. Same flow to change keys or add providers: edit the file and run apply.

- [x] **Create secrets file** (once; do not commit):

  ```bash
  cp infra/secrets.tfvars.example infra/secrets.tfvars
  ```

  Edit `infra/secrets.tfvars` and set at least `anthropic_api_key` (e.g. from `.env` `ANTHROPIC_API_KEY`). Set `chainlit_auth_secret` when you deploy Chainlit.

- [x] **Full apply** (from repo root or `infra/`):

  ```bash
  make infra-apply
  ```

  Or: `cd infra && terraform apply -var-file=dev.tfvars -var-file=secrets.tfvars`. This creates APIs, Secret Manager secrets and their versions, GitHub Actions SA, and Cloud Run A2A.

**To change a key or add a provider later:** edit `infra/secrets.tfvars` (and add the variable in `variables.tf` + optional `google_secret_manager_secret_version` in `secrets.tf` if it’s a new provider), then run `make infra-apply` again.

---

## Phase 2: GitHub Actions service account key (Terraform-created SA, key via gcloud)

The Terraform in this repo can create a **service account for GitHub Actions** with the right role to run `gcloud builds submit`. You then create **one key** for that SA and add it to GitHub as `GCP_SA_KEY`.

### 2.1 Ensure Terraform created the GitHub Actions SA

- [x] If you already did the full apply in 1.6, the SA is created. If not, run `make infra-apply` once (see 1.6).
- [x] Get the SA email from Terraform:

  ```bash
  terraform -chdir=infra output -raw github_actions_sa_email
  ```

  (If that output doesn’t exist yet, we add it in the next step.)

### 2.2 Create a key for the SA and add to GitHub

- [x] From repo root:

  ```bash
  make infra-gha-key
  ```

  Creates `gh-actions-key.json` (set `GCP_PROJECT_ID` if not refactor-agent). Add its contents to GitHub repo secret **`GCP_SA_KEY`** (Settings → Secrets and variables → Actions), then delete the file: `rm gh-actions-key.json`.

You already added **GCP_PROJECT_ID** as a secret; the workflow uses that (or a variable) for the project.

---

## Phase 3: First image and Cloud Run A2A

(If you followed Phase 1 in order, you already built the image in 1.5 and applied in 1.6. Use this phase for re-builds after code changes.)

### 3.1 Build and push the A2A image (after code changes)

- [x] From repo root:

  ```bash
  make image-push
  ```

  Or with a custom project/tag: `make image-push GCP_PROJECT_ID=your-project A2A_IMAGE_TAG=staging`. The GitHub Actions workflow also builds and pushes on push to `main` (tag `:staging`).

### 3.2 Point Terraform at the image and re-apply (optional)

If your tfvars still has `a2a_image = "...:latest"`, you’re good. If you pushed `:staging`, set `a2a_image = "...:staging"` in tfvars and run:

- [x] `make infra-apply`

### 3.3 Set A2A URL for the extension (same repo)

- [x] `make infra-a2a-url` — writes the Cloud Run URL to `.refactor-agent-a2a-url`. The VS Code extension in this repo reads that file automatically (no settings needed).

---

## Phase 4: CI and GitHub Actions

### 4.1 Refactor check workflow

- [x] The refactor check workflow is already enabled (uncommented). Ensure repo secrets exist:
  - **ANTHROPIC_API_KEY**
  - **LANGFUSE_PUBLIC_KEY**
  - **LANGFUSE_SECRET_KEY**
  (Use the same values as in your `.env` for local runs.)

### 4.2 Build-and-push workflow

- [x] After 2.2, the build workflow has **GCP_PROJECT_ID** and **GCP_SA_KEY**. It does **not** run on push to `main`.
- [x] **Staging:** push a tag `staging` or `staging-*` (e.g. `git tag staging && git push origin staging`) → builds and pushes `a2a-server:staging` (or `:staging-<suffix>`).
- [x] **Production:** publish a GitHub release (e.g. `v1.0.0`) → builds and pushes `a2a-server:v1.0.0`.
- [x] (Optional) Set repo variable **GCP_REGION**: GitHub → Settings → Secrets and variables → Actions → **Variables** → Name `GCP_REGION`, Value `europe-west1`.

---

## Phase 5: Hosted Chainlit (optional)

Only if you want the Chainlit UI deployed on Cloud Run talking to the same A2A backend.

### 5.1 Terraform

- [ ] In `dev.tfvars`, set:
  - `chainlit_image` = same image as A2A (e.g. `.../a2a-server:staging`) — same image, different entrypoint.
  - `chainlit_invoker_member` = `"user:YOUR_EMAIL"` (so only you can open the Chainlit URL).
- [ ] `terraform -chdir=infra apply -var-file=dev.tfvars`

### 5.2 Get Chainlit URL

- [ ] `terraform -chdir=infra output chainlit_url`
- [ ] Open in browser (you’ll need to be logged in with the Google account that matches `chainlit_invoker_member`).

---

## Summary checklist

| # | Task |
|---|------|
| 1 | gcloud + Terraform + Docker ready; project ID chosen |
| 2 | GCS state bucket created and versioning enabled |
| 3 | `terraform init` with backend config |
| 4 | Create `dev.tfvars` (project_id, region, a2a_image) |
| 5 | First `terraform apply` (APIs, secrets, SA, etc.) |
| 6 | Create secrets.tfvars from example; set keys; run make infra-apply |
| 7 | Create GitHub Actions SA key with gcloud; add to GitHub as `GCP_SA_KEY` |
| 8 | Build and push A2A image (`make image-push` or workflow) |
| 9 | Get `a2a_url`; set in VS Code extension |
| 10 | Add ANTHROPIC + LANGFUSE secrets to GitHub for refactor check |
| 11 | (Optional) Enable Chainlit in tfvars; apply; use `chainlit_url` |

We can go through these one by one and adjust (e.g. project ID, region, or skipping Chainlit for now).

---

# Final step:

Make this fully reproducible end-to-end