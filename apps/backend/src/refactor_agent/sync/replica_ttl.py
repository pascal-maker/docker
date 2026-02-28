"""Replica TTL: track last sync activity and cleanup after inactivity."""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path

from refactor_agent.sync.constants import DEFAULT_REPLICA_DIR
from refactor_agent.sync.logger import logger

# Module-level state for TTL tracking; PLW0603 suppressed — single-process state is intended.
_last_activity: list[float] = [0.0]


def update_replica_activity() -> None:
    """Record that sync activity occurred (call from POST /sync/workspace, WebSocket)."""
    _last_activity[0] = time.monotonic()


def _get_replica_dir() -> Path:
    """Return replica directory from env or default."""
    replica_dir = os.environ.get("REPLICA_DIR", DEFAULT_REPLICA_DIR)
    return Path(replica_dir)


def _get_ttl_minutes() -> int:
    """Return TTL in minutes from env (default 30)."""
    val = os.environ.get("REPLICA_TTL_MINUTES", "30")
    try:
        return max(1, int(val))
    except ValueError:
        return 30


async def cleanup_replica_if_idle() -> bool:
    """If no activity for TTL minutes, clear replica dir. Returns True if cleaned."""
    if _last_activity[0] == 0:
        return False
    ttl_minutes = _get_ttl_minutes()
    idle_secs = time.monotonic() - _last_activity[0]
    if idle_secs < ttl_minutes * 60:
        return False
    root = _get_replica_dir()
    if not root.exists():
        return False
    try:
        shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        logger.info("Replica TTL: cleaned up after %d min idle", ttl_minutes)
        _last_activity[0] = 0.0
        return True
    except OSError as e:
        logger.warning("Replica TTL cleanup failed: %s", e)
        return False


async def replica_ttl_loop() -> None:
    """Background task: check every minute and cleanup if idle."""
    while True:
        await asyncio.sleep(60)
        await cleanup_replica_if_idle()
