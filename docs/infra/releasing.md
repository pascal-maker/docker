# Releasing

One **version tag** (e.g. `v0.2.0`) is built once, then deployed to **staging** and later **promoted** to production (same image, same tag).

## Best practices (why not edit tfvars by hand)

Common practice is to **avoid editing tfvars for the release version**: the image tag should be supplied by the pipeline or the command line, not baked into a file. That way:

- The same tfvars (staging/prod) stay valid; you only change the **version** per deploy.
- CI can run `terraform apply` with `-var a2a_image=...` or `TF_VAR_a2a_image=...` so deploys are repeatable and traceable.

**Right now**: Build is automated (push tag → image in registry). Deploy is **manual**: you run Terraform yourself. You can still follow the practice by passing the image tag on the command line (see below) so you don’t edit tfvars. **Later**: You can add a deploy job (or separate workflow) that runs `terraform apply` in CI and passes the tag from the trigger; that usually means storing Terraform-sensitive values in GitHub Secrets (or Terraform Cloud) so the runner can apply without a local `secrets.tfvars`.

---

## 1. Create a version tag

From latest `main`:

```bash
git checkout main && git pull
```

Optionally bump `version` in `pyproject.toml`, then commit and push. Create and push a **semver tag**:

```bash
git tag v0.2.0   # or v1.0.0, v0.1.1, etc.
git push origin v0.2.0
```

## 2. Build runs automatically

The [Build and push images](../../../.github/workflows/build-push-images.yml) workflow runs on:

- **Push tag `v*`** (e.g. `v0.2.0`) → builds and pushes `a2a-server:v0.2.0` to Artifact Registry.
- **Publish a GitHub Release** with the same tag → also triggers a build (same image; idempotent).

So pushing the tag is enough to get the image. You can optionally create a GitHub Release (Releases → Draft a new release, choose tag `v0.2.0`, add notes) for changelog and visibility.

## 3. Deploy to staging

**Option A – Pass image tag on the command line (recommended)**  
Keep `a2a_image` in tfvars as a default or leave it out and pass it every time:

```bash
cd infra
export REGION="europe-west1"
export PROJECT="YOUR_GCP_PROJECT_ID"
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/refactor-agent/a2a-server:v0.2.0"

terraform apply \
  -var-file=staging.tfvars \
  -var-file=secrets.tfvars \
  -var="a2a_image=${IMAGE}" \
  -var="a2a_min_instance_count=1"
```

No need to edit staging.tfvars; the version is explicit in the command and in history.

**Option B – Set in tfvars**  
If you prefer, set `a2a_image = "..."` and `a2a_min_instance_count = 1` in staging tfvars, then:

```bash
cd infra && terraform apply -var-file=staging.tfvars -var-file=secrets.tfvars
```

Smoke-test the staging URL (`terraform output a2a_url`).

## 4. Promote to production

**Option A – Pass image tag (same as staging)**  
Same image tag as used for staging:

```bash
cd infra
export REGION="europe-west1"
export PROJECT="YOUR_GCP_PROJECT_ID"
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/refactor-agent/a2a-server:v0.2.0"

terraform apply \
  -var-file=prod.tfvars \
  -var-file=secrets.tfvars \
  -var="a2a_image=${IMAGE}" \
  -var="a2a_min_instance_count=0"
```

**Option B – Set in tfvars**  
Set `a2a_image = ".../a2a-server:v0.2.0"` (same tag as staging) and `a2a_min_instance_count = 0` in prod tfvars, then:

```bash
cd infra && terraform apply -var-file=prod.tfvars -var-file=secrets.tfvars
```

Production now runs the same image that was validated on staging.

## Summary

| Step              | Action                                                                 |
|-------------------|------------------------------------------------------------------------|
| **Tag**           | `git tag v0.2.0 && git push origin v0.2.0`                             |
| **Build**         | Automatic (workflow builds image `:v0.2.0`)                            |
| **Staging**       | `terraform apply -var-file=staging.tfvars -var-file=secrets.tfvars -var a2a_image=.../v0.2.0` |
| **Production**    | Same, with prod tfvars and same `a2a_image` tag                        |

One version tag → one image → deploy to staging (with `-var`), then promote that same tag to production.

## Optional: full deploy automation in CI

You can move to **push tag → build → auto-deploy staging → manual approval → production** by storing Terraform secrets in GitHub (or Terraform Cloud) and using GitHub Environments.

### 1. GitHub Secrets and variables

Ensure these are set (Settings → Secrets and variables → Actions):

| Name | Type | Purpose |
|------|------|---------|
| `GCP_SA_KEY` | Secret | JSON key for the service account used by GitHub Actions (build + Terraform) |
| `GCP_PROJECT_ID` | Secret or variable | GCP project ID |
| `TF_VAR_anthropic_api_key` | Secret | Passed to Terraform for the A2A server |
| `TF_VAR_chainlit_auth_secret` | Secret | Passed to Terraform for Chainlit auth |

Optional:

| Name | Type | Purpose |
|------|------|---------|
| `TERRAFORM_STATE_BUCKET` | Variable | GCS bucket for Terraform state. If unset, defaults to `{GCP_PROJECT_ID}-terraform-state`. |
| `GCP_REGION` | Variable | Region (default `europe-west1`) |

The service account must have roles needed for Terraform (e.g. Run admin, Secret Manager admin) and, for CI apply, **Storage Object Admin** on the Terraform state bucket. See `infra/README.md` and `make infra-gha-key`; the infra can grant the state bucket IAM via `terraform_state_bucket` and `cloudbuild_permissions.tf`.

### 2. GitHub Environments

Create two environments (Settings → Environments):

- **staging** – No approval required. Used by the “Build and push images” workflow when you push a `v*` tag; after the image is built, the `deploy-staging` job runs `terraform apply` with that tag and `a2a_min_instance_count=1`.
- **production** – Add **Required reviewers** (e.g. one or more team members). Used by the “Deploy to production” workflow.

### 3. Resulting flow

| Step | What happens |
|------|-------------------------------|
| **Push tag** | `git push origin v0.2.0` triggers “Build and push images”. |
| **Build** | Image `a2a-server:v0.2.0` is built and pushed to Artifact Registry. |
| **Staging** | `deploy-staging` runs `terraform apply` with that image and min instances 1. |
| **Production** | In Actions, run **Deploy to production** (workflow_dispatch), enter tag `v0.2.0`. After approval, the job runs `terraform apply` with that image and min instances 0. |

You still deploy the “right” way: the image tag is always passed via the workflow (no editing tfvars per release). Full automation is an optional next step once secrets and environments are configured.

## Required secrets

The build workflow needs **GCP_SA_KEY** and **GCP_PROJECT_ID** (or repo variable). For **automated deploy** (staging + production workflows), also add **TF_VAR_anthropic_api_key** and **TF_VAR_chainlit_auth_secret**, and configure GitHub Environments as in the optional section above. See [infra/README.md](../../../infra/README.md) and `make infra-gha-key`.
