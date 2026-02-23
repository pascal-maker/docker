"""Run combined A2A + sync backend (single service, single port).

Usage:
  uv run python scripts/run_refactor_backend.py

Serves:
  - GET /.well-known/agent-card.json (public)
  - POST / (A2A JSON-RPC, auth required)
  - POST /sync/workspace (sync, auth required)
  - WebSocket / (sync, auth required)
"""

from __future__ import annotations

import os
import sys

import uvicorn
from dotenv import load_dotenv

load_dotenv()

from refactor_agent._log_config import configure_logging
from refactor_agent.backend.app import build_combined_app

DEFAULT_PORT = 9999


def main() -> None:
    """Run the combined backend with uvicorn."""
    configure_logging()
    app = build_combined_app()
    port_val = (
        sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PORT", str(DEFAULT_PORT))
    )
    port = int(port_val)
    uvicorn.run(app, host="0.0.0.0", port=port)  # noqa: S104


if __name__ == "__main__":
    main()
