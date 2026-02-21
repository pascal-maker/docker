"""Sync client: connect to sync server, send bootstrap and file updates on save."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

import websockets

logger = logging.getLogger(__name__)


def _collect_py_files(root: Path) -> list[tuple[Path, str]]:
    """Return list of (path, content) for all .py files under root (relative path)."""
    out: list[tuple[Path, str]] = []
    root_resolved = root.resolve()
    for path in root_resolved.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root_resolved)
            content = path.read_text(encoding="utf-8")
            out.append((rel, content))
        except (OSError, ValueError):
            continue
    return out


async def _send_bootstrap(ws: websockets.WebSocketClientProtocol, root: Path) -> bool:
    """Send bootstrap as chunked messages (bootstrap_start + one file per message).

    Keeps each message under the default 1 MiB limit so no max_size increase needed.
    """
    files_list = _collect_py_files(root)
    # Clear replica, then send one file per message
    await ws.send(json.dumps({"type": "bootstrap_start"}))
    reply = await ws.recv()
    try:
        data = json.loads(reply)
        if "error" in data:
            logger.error("Bootstrap start error: %s", data["error"])
            return False
    except json.JSONDecodeError:
        logger.error("Bootstrap start reply not JSON: %s", reply[:200])
        return False
    for rel, content in files_list:
        path_str = str(rel).replace("\\", "/")
        msg = {"type": "file", "path": path_str, "content": content}
        await ws.send(json.dumps(msg))
        reply = await ws.recv()
        try:
            data = json.loads(reply)
            if "error" in data:
                logger.error("Bootstrap file %s error: %s", path_str, data["error"])
                return False
        except json.JSONDecodeError:
            logger.error("Bootstrap file reply not JSON: %s", reply[:200])
            return False
    return True


async def _send_file(
    ws: websockets.WebSocketClientProtocol,
    root: Path,
    path: Path,
) -> bool:
    """Send single file update. path is absolute or relative to root."""
    try:
        full = path if path.is_absolute() else root / path
        rel = full.resolve().relative_to(root.resolve()) if full.is_absolute() else path
        content = full.read_text(encoding="utf-8")
    except (OSError, ValueError) as e:
        logger.warning("Cannot read %s: %s", path, e)
        return False
    msg = {"type": "file", "path": str(rel).replace("\\", "/"), "content": content}
    await ws.send(json.dumps(msg))
    reply = await ws.recv()
    try:
        data = json.loads(reply)
        if "error" in data:
            logger.error("File sync error: %s", data["error"])
            return False
        return True
    except json.JSONDecodeError:
        logger.error("File reply not JSON: %s", reply[:200])
        return False


# Single-file messages can be large; allow up to 16 MiB per message
WS_MAX_MESSAGE_SIZE = 16 * 2**20


async def run_sync_client_with_queue(
    ws_url: str,
    root: Path,
    path_queue: asyncio.Queue[Path | None],
) -> None:
    """Connect, send bootstrap, then for each path from path_queue send file (None = exit)."""
    root = root.resolve()
    async with websockets.connect(ws_url, max_size=WS_MAX_MESSAGE_SIZE) as ws:
        ok = await _send_bootstrap(ws, root)
        if not ok:
            raise RuntimeError("Bootstrap failed")
        logger.info("Bootstrap sent for %s", root)
        while True:
            path = await path_queue.get()
            if path is None:
                break
            await _send_file(ws, root, path)
