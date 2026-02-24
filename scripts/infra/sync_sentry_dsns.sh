#!/usr/bin/env bash
# Sync Sentry DSNs from Terraform outputs into .env files.
# Run from repo root. Requires: terraform apply with Sentry enabled.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT/infra"

BACKEND=$(terraform output -raw sentry_dsn_backend 2>/dev/null || true)
FRONTEND=$(terraform output -raw sentry_dsn_frontend 2>/dev/null || true)
VSCODE=$(terraform output -raw sentry_dsn_vscode 2>/dev/null || true)

if [[ -z "$BACKEND" || -z "$FRONTEND" || -z "$VSCODE" ]]; then
  echo "Error: Sentry DSNs not found. Run: terraform apply -var-file=dev.tfvars -var-file=secrets.tfvars"
  exit 1
fi

_update_env() {
  local file="$1"
  local key="$2"
  local value="$3"
  local tmp
  tmp=$(mktemp)
  if [[ -f "$file" ]]; then
    if grep -q "^${key}=" "$file" 2>/dev/null; then
      grep -v "^${key}=" "$file" > "$tmp" || true
    else
      cat "$file" > "$tmp"
    fi
    echo "${key}=${value}" >> "$tmp"
    mv "$tmp" "$file"
    echo "  Updated $file"
  else
    echo "${key}=${value}" > "$file"
    echo "  Created $file"
  fi
}

echo "Syncing Sentry DSNs..."
_update_env "$REPO_ROOT/.env" "SENTRY_DSN" "$BACKEND"
_update_env "$REPO_ROOT/dashboard-ui/.env" "VITE_SENTRY_DSN" "$FRONTEND"
_update_env "$REPO_ROOT/site/.env" "VITE_SENTRY_DSN" "$FRONTEND"

echo ""
echo "VS Code extension: add to .vscode/settings.json or User Settings:"
echo "  \"refactorAgent.sentryDsn\": \"$VSCODE\""
echo ""
echo "Done."
