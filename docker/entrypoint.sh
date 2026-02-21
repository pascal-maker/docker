#!/bin/sh
set -e
# Start WebSocket sync server in background (port 8765)
python -m refactor_agent.sync &
# Run A2A HTTP server in foreground (port 9999)
exec python scripts/run_ast_refactor_a2a.py
