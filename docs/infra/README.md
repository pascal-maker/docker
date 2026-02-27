---
title: Infrastructure
---

# Infrastructure

Deploy and operate the refactor agent on GCP (Terraform, EU-only), release new versions, and run the dev loop.

## Contents

- [GCP (Terraform, EU)](gcp.md) — Deploy A2A and (later) dashboard; two surfaces (opaque A2A, transparent Dev UI); EU-only for GDPR.
- [Credentials rotation](credentials-rotation.md) — Step-by-step guide to rotate each secret (GitHub, Cloudflare, Resend, Firebase, Sentry, etc.) with correct permissions.
- [infra/README.md](../../infra/README.md) — **Dev setup**: tfvars, secrets, Terraform apply (always use both `dev.tfvars` and `secrets.tfvars`), GitHub Actions secrets sync.
- [Releasing](releasing.md) — Version tag, build, staging, promote to production; Terraform vars; optional CI deploy.
- [Dev-loop tasks](dev-loop-tasks.md) — Checklist: GCP project, Terraform state bucket, tfvars, phases.
- [Beta pricing](beta-pricing.md) — Beta UX/infra options: stateless vs long-lived; comparison table.

## Quick links

- Build and push images: [.github/workflows/build-push-images.yml](../../.github/workflows/build-push-images.yml)
- Terraform config: repo root [infra/](../../infra/) (not under docs)
