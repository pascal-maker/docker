#!/usr/bin/env bash
# Build the Refactor Agent VS Code extension, start the combined backend (A2A + sync),
# and open the Extension Development Host.
# Run from repo root: ./scripts/try_extension.sh <playground>
# Playground: "typescript" or "python" (opens playground/<playground> and sets refactorAgent.engine).

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT_DIR="$REPO_ROOT/vscode-extension"
REPLICA_DIR="$(mktemp -d -t refactor-agent-replica.XXXXXX)"
PLAYGROUND="${1:-}"

if [[ "$PLAYGROUND" != "typescript" && "$PLAYGROUND" != "python" ]]; then
  echo "Usage: $0 <playground>"
  echo "  playground: typescript | python"
  echo "Example: $0 typescript"
  exit 1
fi

WORKSPACE_DIR="$REPO_ROOT/playground/$PLAYGROUND"
if [[ ! -d "$WORKSPACE_DIR" ]]; then
  echo "Error: $WORKSPACE_DIR not found."
  exit 1
fi

cd "$REPO_ROOT"

# Load GOOGLE_CLOUD_PROJECT / GCLOUD_PROJECT from .env if present
if [[ -f .env ]]; then
  exports=$(uv run python -c "
from pathlib import Path
from dotenv import dotenv_values
for k, v in dotenv_values(Path('.env')).items():
    if k in ('GOOGLE_CLOUD_PROJECT', 'GCLOUD_PROJECT') and v:
        print(f'export {k}=\"{v}\"')
" 2>/dev/null)
  if [[ -n "$exports" ]]; then
    eval "$exports"
  fi
fi

# Kill any existing backend to avoid "address already in use"
if pkill -f run_refactor_backend 2>/dev/null; then
  echo "Stopped existing backend."
  sleep 1
fi

# Start combined backend (A2A + sync) in background
export REPLICA_DIR
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-${GCLOUD_PROJECT:-}}"
if [[ -z "$GOOGLE_CLOUD_PROJECT" ]]; then
  echo "Warning: GOOGLE_CLOUD_PROJECT not set. Sync will return 503. Add to .env:"
  echo "  GOOGLE_CLOUD_PROJECT=refactor-agent"
fi
echo "Starting backend (A2A + sync on port 9999, replica=$REPLICA_DIR)..."
uv run python scripts/run_refactor_backend.py &

# Wait for backend to be ready
for i in $(seq 1 30); do
  if curl -s -o /dev/null -w "%{http_code}" "http://localhost:9999/.well-known/agent-card.json" 2>/dev/null | grep -q 200; then
    echo "Backend ready."
    break
  fi
  if [[ $i -eq 30 ]]; then
    echo "Error: Backend did not start in time."
    exit 1
  fi
  sleep 0.5
done

# Set the correct engine for the extension (gathers the right files; backend uses the right language).
VSCODE_SETTINGS_DIR="$WORKSPACE_DIR/.vscode"
mkdir -p "$VSCODE_SETTINGS_DIR"
printf '%s\n' "{\"refactorAgent.engine\": \"$PLAYGROUND\", \"refactorAgent.a2aBaseUrl\": \"http://localhost:9999\", \"refactorAgent.syncUrl\": \"http://localhost:9999\"}" > "$VSCODE_SETTINGS_DIR/settings.json"

cd "$EXT_DIR"
echo "Installing dependencies..."
pnpm install
echo "Compiling extension..."
pnpm run compile
echo "Opening Extension Development Host with playground/$PLAYGROUND (engine=$PLAYGROUND)..."
echo "(Backend runs in background. To stop: pkill -f run_refactor_backend)"
exec code --extensionDevelopmentPath="$EXT_DIR" "$WORKSPACE_DIR"
