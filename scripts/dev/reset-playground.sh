#!/usr/bin/env bash
# Reset the test playground(s) to a clean state.
# - In-repo playground (typescript, python): git restore to last commit.
# - Cloned NestJS playground: reset to origin/main.
# Use after partial refactor runs so the next run starts from a clean state.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$REPO_ROOT"

# Restore in-repo playground (playground/typescript, playground/python) to last commit.
reset_inrepo_playground() {
  if [[ ! -d "playground" ]]; then
    echo "Skip: playground/ not found."
    return 0
  fi
  echo "Resetting playground/ to last commit..."
  git restore playground/
  echo "Done: playground/ restored."
}

# Reset cloned NestJS playground to origin/main.
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

reset_inrepo_playground
reset_nestjs
