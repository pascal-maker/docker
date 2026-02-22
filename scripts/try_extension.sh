#!/usr/bin/env bash
# Build the Refactor Agent VS Code extension and open it in Extension Development Host.
# Prerequisite: backend running (e.g. docker compose up a2a-server).
# Run from repo root: ./scripts/try_extension.sh <playground>
# Playground: "typescript" or "python" (opens playground/<playground> and sets refactorAgent.engine).

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT_DIR="$REPO_ROOT/vscode-extension"
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

# Set the correct engine for the extension (gathers the right files; backend uses the right language).
VSCODE_SETTINGS_DIR="$WORKSPACE_DIR/.vscode"
mkdir -p "$VSCODE_SETTINGS_DIR"
# Overwrite .vscode/settings.json with engine so try_extension.sh always sets it; other workspace settings can be re-added if needed.
printf '%s\n' "{\"refactorAgent.engine\": \"$PLAYGROUND\"}" > "$VSCODE_SETTINGS_DIR/settings.json"

cd "$EXT_DIR"
echo "Installing dependencies..."
npm install --no-audit --no-fund
echo "Compiling extension..."
npm run compile
echo "Opening Extension Development Host with playground/$PLAYGROUND (engine=$PLAYGROUND)..."
exec code --extensionDevelopmentPath="$EXT_DIR" "$WORKSPACE_DIR"
