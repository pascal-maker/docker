#!/bin/sh
# Chainlit UI entrypoint for Cloud Run. Listens on PORT (set by Cloud Run).
set -e
PORT="${PORT:-8000}"
export CHAINLIT_APP_ROOT=apps/backend
exec python -m chainlit run apps/backend/src/refactor_agent/ui/app.py --host 0.0.0.0 --port "${PORT}"
