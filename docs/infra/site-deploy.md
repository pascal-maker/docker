# Site and Auth Functions Deployment

The site and its auth/email Cloud Functions are deployed separately from the A2A/sync backend.

## Prerequisites

- GitHub OAuth App for web (see [GitHub OAuth App setup](#github-oauth-app-setup) below)
- Resend account and API key (for admin email notifications)
- GCP project with Firestore, Secret Manager, Cloud Functions APIs enabled

### GitHub OAuth App setup

Create a new OAuth App at https://github.com/settings/applications/new.

| Field | Value |
|-------|-------|
| **Application name** | `Refactor Agent` (or any name users will recognize) |
| **Homepage URL** | Your site URL (e.g. `https://refactor-agent.example.com` or `http://localhost:5173` for local dev) |
| **Application description** | Optional. e.g. "AI-powered code refactoring in your editor" |
| **Authorization callback URL** | Full URL of the auth callback Cloud Function, e.g. `https://europe-west1-PROJECT.cloudfunctions.net/auth-github-callback` |

The callback URL must match exactly what you deploy. For local testing, you can register `http://localhost:8080/auth/github/callback` if you run the auth callback locally (Functions Framework on port 8080).

After registering, GitHub shows a **Client ID** (use as `VITE_GITHUB_OAUTH_CLIENT_ID`) and lets you generate a **Client secret** (store in Secret Manager, use as `GITHUB_OAUTH_CLIENT_SECRET` for the Cloud Function).

**Scope:** The app requests `read:user user:email` (for profile and email; no `repo` — that's for the VS Code extension).

### Local testing

1. Copy `functions/auth_callback/.env.example` to `functions/auth_callback/.env` and fill in your GitHub OAuth Client ID, Client secret, and GCP project ID.
2. Run `./scripts/run_auth_callback_local.sh`.
3. In another terminal, run the site (`pnpm --filter site dev`). Ensure `site/.env` has `VITE_GITHUB_OAUTH_CLIENT_ID` and `VITE_AUTH_CALLBACK_URL=http://localhost:8080/auth/github/callback`.
4. Firestore must be available (real GCP project with ADC).

## 1. Auth Callback Cloud Function

Deploys the OAuth callback that exchanges GitHub code for token and creates Firestore user.

```bash
cd functions/auth_callback
gcloud functions deploy auth-github-callback \
  --gen2 \
  --runtime=python312 \
  --region=europe-west1 \
  --source=. \
  --entry-point=auth_callback \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars="SITE_URL=https://your-site.com,GITHUB_OAUTH_CLIENT_ID=xxx,GITHUB_OAUTH_CLIENT_SECRET=xxx,GITHUB_OAUTH_REDIRECT_URI=https://xxx.run.app/auth/github/callback" \
  --set-secrets="GITHUB_OAUTH_CLIENT_SECRET=refactor-agent-github-oauth-client-secret:latest"
```

Create the client secret in Secret Manager first:

```bash
echo -n "your_client_secret" | gcloud secrets create refactor-agent-github-oauth-client-secret --data-file=-
```

## 2. Email Notify Cloud Function

Deploys the Firestore trigger that emails admin on new pending user.

```bash
cd functions/email_notify
gcloud functions deploy email-notify-pending-user \
  --gen2 \
  --runtime=python312 \
  --region=europe-west1 \
  --source=. \
  --entry-point=on_user_created \
  --trigger-event-filters="type=google.cloud.firestore.document.v1.created" \
  --trigger-event-filters="database=(default)" \
  --trigger-event-filters-path-pattern="document=users/{userId}" \
  --set-env-vars="ADMIN_EMAIL=admin@example.com" \
  --set-secrets="RESEND_API_KEY=refactor-agent-resend-api-key:latest"
```

## 3. Site (Firebase Hosting or static)

Build and deploy the SPA:

```bash
pnpm --filter site build
# Deploy dist/ to Firebase Hosting, Cloud Storage, or similar
```

Set build-time env vars for the site. Create `site/.env` (or `site/.env.local` for local-only, gitignored):

```
VITE_GITHUB_OAUTH_CLIENT_ID=<Client ID from GitHub OAuth App>
VITE_AUTH_CALLBACK_URL=<Full URL of auth callback, e.g. https://xxx.cloudfunctions.net/auth-github-callback>
```

Restart the dev server after changing env vars (`pnpm --filter site dev`).

## Architecture

See [architecture-schematic.md](architecture-schematic.md) section 5 for the full deployment diagram.
