"""Run the sync server when invoked as python -m refactor_agent.sync."""

from __future__ import annotations

import asyncio
import logging
import os

from refactor_agent.sync.server import run_sync_server

logging.basicConfig(level=logging.INFO)
SYNC_PORT = int(os.environ.get("POC_SYNC_PORT", "8765"))


def main() -> None:
    """Run WebSocket sync server until interrupted."""
    asyncio.run(run_sync_server(port=SYNC_PORT))


if __name__ == "__main__":
    main()
