# Nx Cloud Setup

Nx Cloud provides remote caching for the TypeScript CI jobs (format-check, lint, typecheck), avoiding the "Unrecognized Cache Artifacts" issue when restoring `.nx/cache` from GitHub Actions.

## One-Time Manual Steps

### 1. Connect the workspace to Nx Cloud

From the repo root:

```bash
pnpm exec nx connect
```

Follow the prompts to create or link an Nx Cloud workspace (free tier, no credit card). When prompted, generate a **read-write** CI access token, or create one later in the [Nx Cloud dashboard](https://cloud.nx.app).

### 2. Add the token to secrets.tfvars

Add to `infra/secrets.tfvars` (gitignored):

```hcl
nx_cloud_access_token = "your-token-from-nx-connect"
```

### 3. Sync the secret to GitHub via Terraform

```bash
make infra-apply
```

Terraform will create the `NX_CLOUD_ACCESS_TOKEN` GitHub Actions secret. CI will then use Nx Cloud for remote caching.

## Verification

After pushing, check the [Nx Cloud dashboard](https://cloud.nx.app) for cache hits on CI runs.
