"""Run the POC WebSocket sync server (replica dir + port via env)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from document_structuring_agent.sync.server import run_sync_server

SYNC_PORT = int(os.environ.get("POC_SYNC_PORT", "8765"))

logging.basicConfig(level=logging.INFO)


def main() -> None:
    """Run sync server until interrupted."""
    asyncio.run(run_sync_server(port=SYNC_PORT))


if __name__ == "__main__":
    main()
    sys.exit(0)
