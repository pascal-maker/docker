# GitHub App Migration — Manual Steps

Step-by-step checklist of everything you need to do manually for the GitHub App migration. Code and Terraform changes are handled separately; this document covers only manual configuration.

**Prerequisites:** GCP project ID, region (e.g. `europe-west1`), site URL (e.g. `https://refactorum.com`).

---

## Step 1: Create the GitHub App

GitHub has no API for this; registration is manual.

1. Go to [GitHub → Settings → Developer settings → GitHub Apps → New GitHub App](https://github.com/settings/apps/new).

2. Fill in **Basic information**:

   | Field | Value |
   |-------|-------|
   | GitHub App name | `Refactor Agent` (or `Refactorum`) |
   | Description | Optional, e.g. "Agentic code refactoring with confidence" |
   | Homepage URL | `https://refactorum.com` (or your site URL) |

3. **Callback URL** — Add the auth callback URL (replace `PROJECT` with your GCP project ID):

   ```
   https://europe-west1-PROJECT.cloudfunctions.net/auth-github-callback
   ```

   Example: `https://europe-west1-refactor-agent.cloudfunctions.net/auth-github-callback`

   Note: GitHub requires HTTP/HTTPS. The extension uses a redirect from our success page to `vscode://`; do not add `vscode://` as a callback URL here.

4. **Setup URL** — Optional. Can leave blank or use your site (e.g. `https://refactorum.com`).

5. **Webhook** — Enable:

   | Field | Value |
   |-------|-------|
   | Active | Checked |
   | Webhook URL | `https://europe-west1-PROJECT.cloudfunctions.net/github-webhook` (or your webhook Cloud Function URL — set after deploy) |
   | Webhook secret | Generate a random string (e.g. `openssl rand -hex 32`). Save it for Step 4. |

6. **Permissions** — Repository permissions:

   | Permission | Access |
   |------------|--------|
   | Contents | Read and write |
   | Metadata | Read-only |

7. **Where can this GitHub App be installed?** — Select **Any account**.

8. **Request user authorization (OAuth) during installation** — Check **Yes**. This starts the OAuth flow right after install.

9. **Expiring user authorization** — Enable (recommended). Tokens expire after 8 hours; refresh tokens last 6 months.

10. Click **Create GitHub App**.

11. **Save these values** (you will need them for Steps 2–4):

    - **App ID** — On the app’s General page
    - **Client ID** — On the app’s General page (different from App ID)
    - **Client secret** — Click **Generate a new client secret**; copy immediately (shown once)
    - **Private key** — Click **Generate a private key**; downloads a `.pem` file. Keep it secure.

12. **Webhook events** — No action needed. GitHub sends `installation` and `installation_repositories` to all GitHub Apps by default. You cannot manually subscribe to them; they do not appear in the "Subscribe to events" list. Leave all optional events unchecked.

---

## Step 2: Add values to secrets.tfvars (Terraform)

All secrets are managed via Terraform. Add these to `infra/secrets.tfvars` (gitignored):

| Variable | Source | Notes |
|----------|--------|-------|
| `github_app_id` | Step 1 — App ID | Numeric, e.g. `123456` |
| `github_app_client_id` | Step 1 — Client ID | String, e.g. `Iv1.abc123...` |
| `github_app_client_secret` | Step 1 — Client secret | From "Generate a new client secret" |
| `github_app_private_key` | Step 1 — PEM file | Use `file()` to reference the downloaded key |
| `github_app_webhook_secret` | Step 1.5 — Webhook secret | The value you generated for the webhook |

**Private key:** Copy the downloaded `.pem` file to `infra/github-app-private-key.pem` (gitignored via `infra/*.pem`). Then in `secrets.tfvars` use the path (tfvars cannot call `file()`):

```hcl
github_app_private_key_path = "github-app-private-key.pem"
```

**Example block for secrets.tfvars:**

```hcl
github_app_id                = "123456"
github_app_client_id         = "Iv1.abc123def456"
github_app_client_secret     = "your_client_secret"
github_app_private_key_path  = "github-app-private-key.pem"
github_app_webhook_secret    = "your_webhook_secret_from_step_1"
```

Then run `make infra-apply`. Terraform creates the Secret Manager resources and populates them.

---

## Step 4: Update GitHub App webhook URL (after first deploy)

After the webhook Cloud Function is deployed, you need the final URL.

1. Get the webhook URL from Terraform output or Cloud Console (e.g. `https://europe-west1-PROJECT.cloudfunctions.net/github-webhook`).

2. Go to your GitHub App → **General** → **Webhook** section.

3. Update **Webhook URL** to the deployed URL.

4. If you changed the webhook secret, regenerate it in GitHub and update `github_app_webhook_secret` in `secrets.tfvars`, then re-apply.

---

## Step 5: Enable Device Flow for extension fallback

When the `vscode://` redirect is unreliable (e.g. some Linux setups, corporate proxies), the extension falls back to Device Flow. Enable it:

1. Go to your GitHub App → **General** → scroll to **Optional features**.

2. Click **Opt-in** next to **Device flow**.

3. The extension will use device flow when the browser flow fails: user enters the code at https://github.com/login/device.

---

## Step 6: Verify and test

1. **Terraform apply:**
   ```bash
   make infra-apply
   ```

2. **Test site flow:**
   - Open your site
   - Click "Request access"
   - You should be redirected to GitHub to install/authorize the app
   - After authorizing, you should land on the success page

3. **Test webhook (optional):**
   - In GitHub App settings, under **Webhook**, click **Recent Deliveries**
   - Trigger an event (e.g. add a repo to the installation)
   - Check that the delivery succeeds (200 response)

4. **Test extension:**
   - Open VS Code with the extension
   - Trigger sign-in (e.g. first sync)
   - Browser should open; after authorizing, you should return to VS Code with a session

---

## Checklist summary

- [ ] Step 1: Create GitHub App, save App ID, Client ID, Client secret, Private key
- [ ] Step 1: Enable webhook, set URL (placeholder OK), generate webhook secret
- [ ] Step 2: Copy PEM to `infra/github-app-private-key.pem`, add all `github_app_*` to `secrets.tfvars`
- [ ] Step 3: Run `make infra-apply`
- [ ] Step 4: After deploy, update GitHub App webhook URL to production
- [ ] Step 5: (Optional) Enable Device Flow
- [ ] Step 6: Test site and extension

---

## Rollback

If you need to revert to the OAuth App:

1. Uncomment `github_oauth_client_id` and `github_oauth_client_secret` in `secrets.tfvars`.
2. Revert the code changes (auth callback, site, extension).
3. Run `make infra-apply`.
4. Existing users will need to re-authorize with the OAuth App.
