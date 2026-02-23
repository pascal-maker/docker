# Releasing

One **version tag** (e.g. `v0.2.0`) is built once, then deployed to **staging** and later **promoted** to production (same image, same tag).

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

The [Build and push images](.github/workflows/build-push-images.yml) workflow runs on:

- **Push tag `v*`** (e.g. `v0.2.0`) → builds and pushes `a2a-server:v0.2.0` to Artifact Registry.
- **Publish a GitHub Release** with the same tag → also triggers a build (same image; idempotent).

So pushing the tag is enough to get the image. You can optionally create a GitHub Release (Releases → Draft a new release, choose tag `v0.2.0`, add notes) for changelog and visibility.

## 3. Deploy to staging

Point your **staging** Terraform at this version:

- In staging tfvars (e.g. `staging.tfvars` or `dev.tfvars`):
  - `a2a_image = "europe-west1-docker.pkg.dev/YOUR_PROJECT/refactor-agent/a2a-server:v0.2.0"`
  - `a2a_min_instance_count = 1` (optional; avoids cold start).

Apply:

```bash
cd infra && terraform apply -var-file=staging.tfvars -var-file=secrets.tfvars
```

Smoke-test the staging URL (`terraform output a2a_url`).

## 4. Promote to production

When staging looks good, promote the **same** version to production (no new build):

- In **production** tfvars:
  - `a2a_image = ".../a2a-server:v0.2.0"` (same tag as staging).
  - `a2a_min_instance_count = 0` (or 1 if you want always-on).

Apply:

```bash
cd infra && terraform apply -var-file=prod.tfvars -var-file=secrets.tfvars
```

Production now runs the same image that was validated on staging.

## Summary

| Step              | Action                                              |
|-------------------|-----------------------------------------------------|
| **Tag**           | `git tag v0.2.0 && git push origin v0.2.0`          |
| **Build**         | Automatic (workflow builds image `:v0.2.0`)        |
| **Staging**       | Terraform apply with `a2a_image = "...:v0.2.0"`     |
| **Production**    | Terraform apply (prod tfvars) with same `...:v0.2.0`|

One version tag → one image → deploy to staging, then promote that same tag to production.

## Required secrets

The build workflow needs **GCP_SA_KEY** and **GCP_PROJECT_ID** (or repo variable). See [infra/README.md](../infra/README.md) and `make infra-gha-key`.
