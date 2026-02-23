#!/usr/bin/env bash
# Run the auth callback Cloud Function locally for testing the site's Request access flow.
#
# Usage:
#   ./scripts/run_auth_callback_local.sh
#
# Create functions/auth_callback/.env with GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET,
# GITHUB_OAUTH_REDIRECT_URI, SITE_URL, GOOGLE_CLOUD_PROJECT (see .env.example).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTH_CALLBACK_DIR="${SCRIPT_DIR}/../functions/auth_callback"

cd "$AUTH_CALLBACK_DIR"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

# Avoid macOS fork crash with gunicorn/Objective-C (objc_initializeAfterForkError)
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

uv run --with functions-framework functions-framework --target=auth_callback --port=8080
