"""Run the POC sync server (WebSocket + HTTP POST /sync/workspace)."""

from __future__ import annotations

import logging
import os
import sys

import uvicorn

from refactor_agent.sync.app import app

SYNC_PORT = int(os.environ.get("POC_SYNC_PORT", "8765"))

logging.basicConfig(level=logging.INFO)


def main() -> None:
    """Run sync server until interrupted."""
    uvicorn.run(app, host="0.0.0.0", port=SYNC_PORT)  # noqa: S104


if __name__ == "__main__":
    main()
    sys.exit(0)
