#!/usr/bin/env bash
# Copy Firebase service account JSON to infra/ and sync to GitHub Actions.
# Usage: ./scripts/infra/sync_firebase_sa.sh [path-to-firebase-key.json]
# If no path given, looks for firebase-sa.json in infra/ or current dir.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INFRA="$REPO_ROOT/infra"
TARGET="$INFRA/firebase-sa.json"

if [ $# -ge 1 ]; then
  SRC="$1"
  if [ ! -f "$SRC" ]; then
    echo "Error: $SRC not found"
    exit 1
  fi
  cp "$SRC" "$TARGET"
  echo "Copied to $TARGET"
elif [ -f "$INFRA/firebase-sa.json" ]; then
  echo "Using existing $TARGET"
elif [ -f "$REPO_ROOT/firebase-sa.json" ]; then
  cp "$REPO_ROOT/firebase-sa.json" "$TARGET"
  echo "Copied from repo root to $TARGET"
else
  echo "Usage: $0 <path-to-firebase-key.json>"
  echo "  Or: put firebase-sa.json in infra/ and run make infra-apply"
  echo ""
  echo "Get the JSON: Firebase Console → Project Settings → Service accounts → Generate new private key"
  exit 1
fi

echo "Running make infra-apply to sync to GitHub secret FIREBASE_SERVICE_ACCOUNT..."
cd "$REPO_ROOT" && make infra-apply
