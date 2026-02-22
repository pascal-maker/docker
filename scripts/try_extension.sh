#!/usr/bin/env bash
# Build the Refactor Agent VS Code extension and open it in Extension Development Host.
# Prerequisite: backend running (e.g. docker compose up a2a-server).
# Run from repo root: ./scripts/try_extension.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT_DIR="$REPO_ROOT/vscode-extension"

cd "$EXT_DIR"
echo "Installing dependencies..."
npm install --no-audit --no-fund
echo "Compiling extension..."
npm run compile
echo "Opening Extension Development Host..."
exec code --extensionDevelopmentPath="$EXT_DIR" "$REPO_ROOT"
