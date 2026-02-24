#!/bin/sh
# Combined A2A + sync entrypoint for Cloud Run.
# Cloud Run sets PORT; the app reads it via os.environ.get("PORT", "9999").
set -e
exec python scripts/backend/run_refactor_backend.py
