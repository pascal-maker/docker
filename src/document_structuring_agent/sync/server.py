"""WebSocket sync server: bootstrap and file messages write to a replica directory."""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)

DEFAULT_REPLICA_DIR = "/workspace"
DEFAULT_WS_PORT = 8765


def _replica_path(replica_root: Path, relative_path: str) -> Path | None:
    """Resolve path under replica_root; return None if path escapes (security)."""
    try:
        resolved = (replica_root / relative_path).resolve()
        resolved.relative_to(replica_root.resolve())
        return resolved
    except (ValueError, RuntimeError):
        return None


async def _handle_bootstrap(replica_root: Path, msg: dict) -> str | None:
    """Process bootstrap message: wipe replica and write all files. Returns error or None."""
    files = msg.get("files")
    if not isinstance(files, list):
        return "bootstrap requires 'files': [{ path, content }, ...]"
    if replica_root.exists():
        try:
            shutil.rmtree(replica_root)
        except OSError as e:
            return f"failed to clear replica dir: {e}"
    replica_root.mkdir(parents=True, exist_ok=True)
    for i, item in enumerate(files):
        if not isinstance(item, dict):
            return f"files[{i}] must be an object"
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not path.strip():
            return f"files[{i}].path must be a non-empty string"
        if not isinstance(content, str):
            return f"files[{i}].content must be a string"
        target = _replica_path(replica_root, path.strip())
        if target is None:
            return f"files[{i}].path escapes replica: {path!r}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return None


async def _handle_bootstrap_start(replica_root: Path) -> str | None:
    """Clear replica dir for chunked bootstrap. Returns error or None."""
    if replica_root.exists():
        try:
            shutil.rmtree(replica_root)
        except OSError as e:
            return f"failed to clear replica dir: {e}"
    replica_root.mkdir(parents=True, exist_ok=True)
    return None


async def _handle_file(replica_root: Path, msg: dict) -> str | None:
    """Process file message: write single file. Returns error or None."""
    path = msg.get("path")
    content = msg.get("content")
    if not isinstance(path, str) or not path.strip():
        return "file message requires non-empty 'path'"
    if not isinstance(content, str):
        return "file message requires 'content' string"
    target = _replica_path(replica_root, path.strip())
    if target is None:
        return f"path escapes replica: {path!r}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return None


async def _handle_connection(
    websocket: WebSocketServerProtocol,
    replica_root: Path,
) -> None:
    """Handle one WebSocket connection: parse JSON messages and apply to replica."""
    peer = websocket.remote_address
    logger.info("Sync client connected: %s", peer)
    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode())
            except (json.JSONDecodeError, TypeError) as e:
                await websocket.send(json.dumps({"error": f"invalid JSON: {e}"}))
                continue
            if not isinstance(msg, dict):
                await websocket.send(json.dumps({"error": "message must be an object"}))
                continue
            msg_type = msg.get("type")
            if msg_type == "bootstrap":
                err = await _handle_bootstrap(replica_root, msg)
                if err:
                    await websocket.send(json.dumps({"error": err}))
                else:
                    await websocket.send(json.dumps({"ok": "bootstrap"}))
            elif msg_type == "bootstrap_start":
                err = await _handle_bootstrap_start(replica_root)
                if err:
                    await websocket.send(json.dumps({"error": err}))
                else:
                    await websocket.send(json.dumps({"ok": "bootstrap_start"}))
            elif msg_type == "file":
                err = await _handle_file(replica_root, msg)
                if err:
                    await websocket.send(json.dumps({"error": err}))
                else:
                    await websocket.send(json.dumps({"ok": "file"}))
            else:
                await websocket.send(
                    json.dumps({"error": f"unknown type: {msg_type!r}"})
                )
    except websockets.exceptions.ConnectionClosed:
        logger.info("Sync client disconnected: %s", peer)
    except Exception as e:
        logger.exception("Sync handler error: %s", e)


async def run_sync_server(
    host: str = "0.0.0.0",
    port: int = DEFAULT_WS_PORT,
    replica_dir: str | None = None,
) -> None:
    """Run WebSocket sync server; blocks until stopped."""
    root = Path(replica_dir or os.environ.get("REPLICA_DIR", DEFAULT_REPLICA_DIR))
    root.mkdir(parents=True, exist_ok=True)
    logger.info("Sync server replica_dir=%s port=%s", root, port)

    async def handler(ws: WebSocketServerProtocol) -> None:
        await _handle_connection(ws, root)

    # Single-file messages; allow up to 16 MiB per message
    max_size = 16 * 2**20
    async with websockets.serve(handler, host, port, max_size=max_size) as server:
        await server.wait_closed()
