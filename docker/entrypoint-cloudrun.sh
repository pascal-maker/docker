#!/bin/sh
# A2A-only entrypoint for Cloud Run (no sync server).
# Cloud Run sets PORT; the app reads it via os.environ.get("PORT", "9999").
set -e
exec python scripts/run_ast_refactor_a2a.py
