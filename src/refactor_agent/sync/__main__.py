"""Run the sync server when invoked as python -m refactor_agent.sync."""

from __future__ import annotations

import logging
import os

import uvicorn

from refactor_agent.sync.app import app

logging.basicConfig(level=logging.INFO)
SYNC_PORT = int(os.environ.get("POC_SYNC_PORT", "8765"))


def main() -> None:
    """Run sync server (WebSocket at /, POST /sync/workspace) until interrupted."""
    uvicorn.run(app, host="0.0.0.0", port=SYNC_PORT)


if __name__ == "__main__":
    main()
