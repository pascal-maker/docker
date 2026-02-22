#!/bin/sh
# Chainlit UI entrypoint for Cloud Run. Listens on PORT (set by Cloud Run).
set -e
PORT="${PORT:-8000}"
exec python -m chainlit run src/refactor_agent/ui/app.py --host 0.0.0.0 --port "${PORT}"
