"""WebSocket sync server: bootstrap and file messages write to a replica directory."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import websockets
from pydantic import ValidationError
from websockets.legacy.server import WebSocketServerProtocol

from refactor_agent.sync.constants import DEFAULT_REPLICA_DIR, DEFAULT_WS_PORT
from refactor_agent.sync.logger import logger
from refactor_agent.sync.models import BootstrapMessage, FileMessage
from refactor_agent.sync.replica_ttl import update_replica_activity

# ASGI scope dict — structure defined by ASGI spec, not our code
type AsgiScope = dict[str, object]


class _StarletteWebSocket(Protocol):
    """Minimal protocol for Starlette WebSocket (receive_text/send_text)."""

    scope: AsgiScope

    async def accept(self) -> None: ...
    async def receive_text(self) -> str: ...
    async def send_text(self, data: str) -> None: ...


def _replica_path(replica_root: Path, relative_path: str) -> Path | None:
    """Resolve path under replica_root; return None if path escapes (security)."""
    try:
        resolved = (replica_root / relative_path).resolve()
        resolved.relative_to(replica_root.resolve())
    except (ValueError, RuntimeError):
        return None
    else:
        return resolved


def _parse_github_path(repo_url: str) -> str | None:
    """Extract owner/repo path from GitHub URL. Supports HTTPS and SSH formats."""
    url = repo_url.strip()
    # SSH: git@github.com:owner/repo.git
    if url.startswith("git@github.com:"):
        path = url.removeprefix("git@github.com:").strip("/").removesuffix(".git")
        return path or None
    # HTTPS: https://github.com/owner/repo.git
    parsed = urlparse(url)
    if parsed.hostname == "github.com" and parsed.path.strip("/"):
        path = parsed.path.strip("/").removesuffix(".git")
        return path or None
    return None


def _clone_repo(replica_root: Path, repo_url: str, token: str) -> str | None:
    """Clone repo into replica_root using token. Returns error or None."""
    path = _parse_github_path(repo_url)
    if not path:
        return f"unsupported repo_url: {repo_url}"
    clone_url = f"https://x-access-token:{token}@github.com/{path}.git"
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(replica_root)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return None
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode(errors="replace")
        return f"git clone failed: {stderr or str(e)}"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return f"git clone failed: {e}"


async def _handle_bootstrap(
    replica_root: Path,
    msg: BootstrapMessage,
    *,
    github_token: str | None = None,
) -> str | None:
    """Process bootstrap: optionally clone repo, then write files. Returns error or None."""
    if replica_root.exists():
        try:
            shutil.rmtree(replica_root)
        except OSError as e:
            return f"failed to clear replica dir: {e}"
    replica_root.mkdir(parents=True, exist_ok=True)

    if msg.repo_url and github_token:
        err = await asyncio.to_thread(
            _clone_repo, replica_root, msg.repo_url, github_token
        )
        if err:
            return err

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
                scope = getattr(websocket, "scope", None)
                token = (
                    (scope.get("state") or {}).get("github_token") if scope else None
                )
                err = await _handle_bootstrap(
                    replica_root, bootstrap_msg, github_token=token
                )
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
            update_replica_activity()
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
                state = websocket.scope.get("state")
                token = state.get("github_token") if isinstance(state, dict) else None
                err = await _handle_bootstrap(
                    replica_root, bootstrap_msg, github_token=token
                )
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
