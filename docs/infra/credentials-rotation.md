---
title: Credentials Rotation Guide
---

# Credentials Rotation Guide

Step-by-step instructions to rotate each credential used by Terraform and the app. Use this after exposure, expiry, or as part of regular security hygiene.

**Never commit `infra/secrets.tfvars`.** Update values there after each rotation, then run `make infra-apply` where Terraform syncs to GitHub Actions or GCP Secret Manager.

---

## 1. GitHub PAT (`github_token`)

**Used for:** Terraform sync of GitHub Actions secrets/variables and Dependabot security updates.

**Fine-grained token only** (no classic tokens).

1. Go to [GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/tokens?type=beta).
2. Click **Generate new token**.
3. **Token name:** e.g. `Refactor Agent`.
4. **Expiration:** 90 days or custom.
5. **Resource owner:** Your user
6. **Repository access:** Only select repositories → choose `refactor-agent`.
7. **Repository permissions** (Read and write for each):
   - **Secrets** — Actions repository secrets
   - **Variables** — Actions repository variables
   - **Administration** — Dependabot security updates
8. Generate and copy the token.
9. Update `github_token` in `secrets.tfvars`.

---

## 2. GitHub OAuth client secret (`github_oauth_client_secret`)

**Used for:** Auth callback Cloud Function (OAuth code exchange).

1. Go to [GitHub → Settings → Developer settings → OAuth Apps](https://github.com/settings/developers).
2. Select your app (e.g. `Refactor Agent`).
3. Click **Generate a new client secret**.
4. Copy the secret immediately (shown once).
5. Update `github_oauth_client_secret` in `secrets.tfvars`.
6. Run `make infra-apply` — Terraform syncs the value to GCP Secret Manager.

---

## 3. Cloudflare API token (`cloudflare_api_token`)

**Used for:** DNS records (SPF, DKIM, Firebase Hosting) and Email Routing (addresses, rules).

1. Go to [Cloudflare Dashboard → My Profile → API Tokens](https://dash.cloudflare.com/profile/api-tokens).
2. Click **Create Token**.
3. Use **Create Custom Token**.
4. **Token name:** e.g. `refactor-agent-terraform`.
5. **Permissions** (add each). Cloudflare UI may show: **sending**, **security**, **routing addresses**. You need:

   | Permission type | Resource | Permission | UI name (approx.) |
   |-----------------|----------|------------|-------------------|
   | Zone | DNS | Edit | DNS |
   | Zone | Email Routing Rules | Edit | Under **routing** / Email Routing |
   | Account | Email Routing Addresses | Edit | **Routing addresses** |

6. **Zone resources:** For each Zone permission (DNS, Email Routing Rules), set **Include** → **Specific zone** → select `refactorum.com`.
7. **Account resources:** Include → Your account (for Email Routing Addresses).
8. Create and copy the token.
9. Update `cloudflare_api_token` in `secrets.tfvars`.

---

## 4. Resend API key (`resend_api_key`)

**Used for:** Admin email notifications (pending user signup).

**Note:** The API key is **not** on the Domains page. Domains shows DNS records (DKIM, SPF). Use **API Keys** in the left sidebar.

1. Go to [Resend Dashboard](https://resend.com) → click **API Keys** in the left nav (not Domains).
2. Click **Create API Key**.
3. **Name:** e.g. `Refactor Agent`.
4. **Permission:** Sending access (or Full access).
5. Create and copy the key.
6. Update `resend_api_key` in `secrets.tfvars`.
7. Run `make infra-apply` — Terraform syncs the value to GCP Secret Manager.

---

## 5. Resend DKIM (`resend_dkim_*`)

**Not a secret** — DNS record for domain verification. Resend can show either **CNAME** or **TXT** for DKIM.

1. Go to [Resend Dashboard → Domains](https://resend.com/domains).
2. Select your domain (e.g. `refactorum.com`).
3. Under **Domain Verification (DKIM)**:
   - If Resend shows a **CNAME**: set `resend_dkim_type = "CNAME"` (default) and `resend_dkim_target` = the target hostname (e.g. `resend._domainkey.resend.com`).
   - If Resend shows a **TXT** (Content = `p=MIGfMA0GCSqGSIb3DQE...`): set `resend_dkim_type = "TXT"` and `resend_dkim_target` = the full Content value from Resend.

---

## 6. Firebase service account (`firebase_service_account_json`)

**Used for:** GitHub Actions deploy to Firebase Hosting.

Firebase does not support revoking a key; you generate a new one and delete the old one after switching.

1. Go to [Firebase Console → Project Settings → Service accounts](https://console.firebase.google.com/project/_/settings/serviceaccounts/adminsdk).
2. Click **Generate new private key** → confirm → download the JSON.
3. Add to `secrets.tfvars`:
   - **Option A:** Minify the JSON (one line, no newlines) and paste as a string:
     ```hcl
     firebase_service_account_json = "{\"type\":\"service_account\",\"project_id\":\"refactor-agent\",...}"
     ```
   - **Option B:** Use a file (in `infra/main.tf` or a `-var`): `firebase_service_account_json = file("${path.module}/../firebase-sa.json")` — ensure `firebase-sa.json` is gitignored.
   - **Option C:** Put `firebase-sa.json` in `infra/` (gitignored); `make infra-apply` reads it automatically.
4. Run `make infra-apply` — Terraform syncs to GitHub Actions secret `FIREBASE_SERVICE_ACCOUNT`.
5. **Revoke old key:** Firebase Console → Project Settings → Service accounts → your service account → find the old key in the keys list → **Delete** (three dots menu).

---

## 7. Sentry auth token (`sentry_auth_token`)

**Used for:** Terraform Sentry provider (projects, teams, alerts).

**Token type:** Use a **personal auth token** (user-bound, custom scopes) or an **internal integration** token (org-bound, scopes editable). Organization auth tokens have fixed scopes and often lack `team:write`.

**Personal token:**
1. Go to [Sentry → Settings → Auth Tokens](https://sentry.io/settings/account/api/auth-tokens/) (or `https://de.sentry.io` for EU).
2. Click **Create New Token**.
3. **Name:** e.g. `Refactor Agent`.
4. **Scopes:** `project:read`, `project:write`, `org:read`, `team:read`, `team:write`.
5. Create and copy the token.

**Internal integration** (org-bound, better for CI):
1. Org → Settings → Developer Settings → Internal Integrations → New internal integration.
2. Under Permissions, add `project:read`, `project:write`, `org:read`, `team:read`, `team:write`.
3. Create and copy the token from the Tokens tab.

6. Update `sentry_auth_token` in `secrets.tfvars`.

---

## 8. Anthropic API key (`anthropic_api_key`)

**Used for:** A2A server LLM calls.

1. Go to [Anthropic Console → API Keys](https://console.anthropic.com/settings/keys).
2. Click **Create Key**.
3. **Name:** e.g. `Refactor Agent`.
4. Create and copy the key.
5. Update `anthropic_api_key` in `secrets.tfvars`.
6. Run `make infra-apply` — Terraform syncs the value to GCP Secret Manager.

---

## 9. Chainlit auth secret (`chainlit_auth_secret`)

**Used for:** Chainlit Dev UI authentication.

1. Generate a random string:
   ```bash
   openssl rand -base64 48
   ```
2. Update `chainlit_auth_secret` in `secrets.tfvars`.
3. Run `make infra-apply` — Terraform syncs the value to GCP Secret Manager.

---

## After rotation

1. Update `infra/secrets.tfvars` with all new values.
2. Run `make infra-apply` — Terraform syncs to GitHub Actions and creates new GCP Secret Manager versions from tfvars.
3. Revoke or delete the old credentials in each provider's UI.
