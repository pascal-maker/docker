#!/usr/bin/env sh
# Enforce Node 24 for this repo. Run before pnpm install.
# Works with fnm (local) or actions/setup-node (CI).

set -e

CURRENT=$(node -v 2>/dev/null || echo "none")
case "$CURRENT" in
  v24.*) ;;
  *)
    echo "Node 24 required (found: $CURRENT)."
    if command -v fnm >/dev/null 2>&1; then
      echo "Run: fnm use"
    else
      echo "Install Node 24, or: brew install fnm && fnm install 24 && fnm use"
    fi
    exit 1
    ;;
esac
