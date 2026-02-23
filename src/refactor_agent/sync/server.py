"""WebSocket sync server: bootstrap and file messages write to a replica directory."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Protocol

import websockets
from pydantic import ValidationError
from websockets.legacy.server import WebSocketServerProtocol

from refactor_agent.sync.logger import logger
from refactor_agent.sync.models import BootstrapMessage, FileMessage


class _StarletteWebSocket(Protocol):
    """Minimal protocol for Starlette WebSocket (receive_text/send_text)."""

    async def accept(self) -> None: ...
    async def receive_text(self) -> str: ...
    async def send_text(self, data: str) -> None: ...


DEFAULT_REPLICA_DIR = "/workspace"
DEFAULT_WS_PORT = 8765


def _replica_path(replica_root: Path, relative_path: str) -> Path | None:
    """Resolve path under replica_root; return None if path escapes (security)."""
    try:
        resolved = (replica_root / relative_path).resolve()
        resolved.relative_to(replica_root.resolve())
    except (ValueError, RuntimeError):
        return None
    else:
        return resolved


async def _handle_bootstrap(replica_root: Path, msg: BootstrapMessage) -> str | None:
    """Process bootstrap message: wipe replica and write all files. Returns error or None."""
    if replica_root.exists():
        try:
            shutil.rmtree(replica_root)
        except OSError as e:
            return f"failed to clear replica dir: {e}"
    replica_root.mkdir(parents=True, exist_ok=True)
    for i, item in enumerate(msg.files):
        target = _replica_path(replica_root, item.path.strip())
        if target is None:
            return f"files[{i}].path escapes replica: {item.path!r}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item.content, encoding="utf-8")
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


async def _handle_file(replica_root: Path, msg: FileMessage) -> str | None:
    """Process file message: write single file. Returns error or None."""
    target = _replica_path(replica_root, msg.path.strip())
    if target is None:
        return f"path escapes replica: {msg.path!r}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(msg.content, encoding="utf-8")
    return None


async def _handle_connection(
    websocket: WebSocketServerProtocol,
    replica_root: Path,
) -> None:
    """Handle one WebSocket connection: parse JSON messages and apply to replica."""
    peer = websocket.remote_address
    logger.info("Sync client connected", peer=str(peer))
    try:
        async for raw in websocket:
            try:
                msg = (
                    json.loads(raw)
                    if isinstance(raw, str)
                    else json.loads(raw.decode())
                )
            except (json.JSONDecodeError, TypeError) as e:
                await websocket.send(json.dumps({"error": f"invalid JSON: {e}"}))
                continue
            if not isinstance(msg, dict):
                await websocket.send(json.dumps({"error": "message must be an object"}))
                continue
            msg_type = msg.get("type")
            if msg_type == "bootstrap":
                try:
                    bootstrap_msg = BootstrapMessage.model_validate(msg)
                except ValidationError as e:
                    await websocket.send(
                        json.dumps({"error": f"invalid bootstrap: {e}"})
                    )
                    continue
                err = await _handle_bootstrap(replica_root, bootstrap_msg)
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
                try:
                    file_msg = FileMessage.model_validate(msg)
                except ValidationError as e:
                    await websocket.send(
                        json.dumps({"error": f"invalid file message: {e}"})
                    )
                    continue
                err = await _handle_file(replica_root, file_msg)
                if err:
                    await websocket.send(json.dumps({"error": err}))
                else:
                    await websocket.send(json.dumps({"ok": "file"}))
            else:
                await websocket.send(
                    json.dumps({"error": f"unknown type: {msg_type!r}"})
                )
    except websockets.exceptions.ConnectionClosed:
        logger.info("Sync client disconnected", peer=str(peer))
    except Exception:
        logger.exception("Sync handler error")


async def _handle_connection_starlette(
    websocket: _StarletteWebSocket,
    replica_root: Path,
) -> None:
    """Handle one WebSocket connection (Starlette API): parse JSON, apply to replica."""
    # websockets/Starlette protocol object (untyped); .client is peer address.
    peer = getattr(websocket, "client", ("unknown",))
    logger.info("Sync client connected", peer=str(peer))
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError) as e:
                await websocket.send_text(json.dumps({"error": f"invalid JSON: {e}"}))
                continue
            if not isinstance(msg, dict):
                await websocket.send_text(
                    json.dumps({"error": "message must be an object"})
                )
                continue
            msg_type = msg.get("type")
            if msg_type == "bootstrap":
                try:
                    bootstrap_msg = BootstrapMessage.model_validate(msg)
                except ValidationError as e:
                    await websocket.send_text(
                        json.dumps({"error": f"invalid bootstrap: {e}"})
                    )
                    continue
                err = await _handle_bootstrap(replica_root, bootstrap_msg)
                if err:
                    await websocket.send_text(json.dumps({"error": err}))
                else:
                    await websocket.send_text(json.dumps({"ok": "bootstrap"}))
            elif msg_type == "bootstrap_start":
                err = await _handle_bootstrap_start(replica_root)
                if err:
                    await websocket.send_text(json.dumps({"error": err}))
                else:
                    await websocket.send_text(json.dumps({"ok": "bootstrap_start"}))
            elif msg_type == "file":
                try:
                    file_msg = FileMessage.model_validate(msg)
                except ValidationError as e:
                    await websocket.send_text(
                        json.dumps({"error": f"invalid file message: {e}"})
                    )
                    continue
                err = await _handle_file(replica_root, file_msg)
                if err:
                    await websocket.send_text(json.dumps({"error": err}))
                else:
                    await websocket.send_text(json.dumps({"ok": "file"}))
            else:
                await websocket.send_text(
                    json.dumps({"error": f"unknown type: {msg_type!r}"})
                )
    except Exception as e:
        if "disconnect" not in str(e).lower():
            logger.exception("Sync handler error")


async def run_sync_server(
    host: str = "0.0.0.0",
    port: int = DEFAULT_WS_PORT,
    replica_dir: str | None = None,
) -> None:
    """Run WebSocket sync server; blocks until stopped."""
    root = Path(replica_dir or os.environ.get("REPLICA_DIR", DEFAULT_REPLICA_DIR))
    root.mkdir(parents=True, exist_ok=True)
    logger.info("Sync server started", replica_dir=str(root), port=port)

    async def handler(ws: WebSocketServerProtocol) -> None:
        await _handle_connection(ws, root)

    # Single-file messages; allow up to 16 MiB per message
    max_size = 16 * 2**20
    async with websockets.serve(handler, host, port, max_size=max_size) as server:  # type: ignore[arg-type]
        await server.wait_closed()
