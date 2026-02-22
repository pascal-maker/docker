#!/usr/bin/env bash
# Reset the cloned test playground(s) to a clean state.
# Use after partial refactor runs so the next run starts from origin.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO_ROOT"

NESTJS_DIR="playground/nestjs-layered-architecture"

reset_nestjs() {
  if [[ ! -d "$NESTJS_DIR" ]]; then
    echo "Skip: $NESTJS_DIR not found."
    return 0
  fi
  if [[ ! -d "$NESTJS_DIR/.git" ]]; then
    echo "Skip: $NESTJS_DIR is not a git repo (cannot reset)."
    return 0
  fi
  echo "Resetting $NESTJS_DIR..."
  (cd "$NESTJS_DIR" && git fetch origin && git reset --hard origin/main && git clean -fd)
  echo "Done: $NESTJS_DIR is clean (origin/main)."
}

reset_nestjs
