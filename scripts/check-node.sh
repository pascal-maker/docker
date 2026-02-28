#!/usr/bin/env sh
# Enforce fnm + Node 24 for this repo. Run before pnpm install.

set -e

if ! command -v fnm >/dev/null 2>&1; then
  echo "fnm is required. Install: brew install fnm"
  echo "Then: fnm install 24 && fnm use"
  exit 1
fi

CURRENT=$(node -v 2>/dev/null || echo "none")
case "$CURRENT" in
  v24.*) ;;
  *)
    echo "Node 24 required (found: $CURRENT). Run: fnm use"
    exit 1
    ;;
esac
