"""ASGI sync app: WebSocket + HTTP POST /sync/workspace for workspace upload."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute

from refactor_agent.sync.models import BootstrapMessage
from refactor_agent.sync.server import (
    DEFAULT_REPLICA_DIR,
    _handle_bootstrap,
    _handle_connection_starlette,
)

if TYPE_CHECKING:
    from refactor_agent.sync.server import _StarletteWebSocket


def _get_replica_root() -> Path:
    """Return replica directory path from env or default."""
    replica_dir = os.environ.get("REPLICA_DIR", DEFAULT_REPLICA_DIR)
    root = Path(replica_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


async def http_sync_workspace(request: Request) -> JSONResponse:
    """POST /sync/workspace: body { \"files\": [{ \"path\", \"content\" }, ...] }."""
    if request.method != "POST":
        return JSONResponse({"error": "method not allowed"}, status_code=405)
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        return JSONResponse({"error": f"invalid JSON: {e}"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "body must be a JSON object"}, status_code=400)
    try:
        bootstrap_msg = BootstrapMessage.model_validate(
            {"type": "bootstrap", "files": body.get("files", [])}
        )
    except ValidationError as e:
        return JSONResponse(
            {"error": f"invalid bootstrap payload: {e}"}, status_code=400
        )
    err = await _handle_bootstrap(_get_replica_root(), bootstrap_msg)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return JSONResponse({"ok": True})


async def websocket_sync(websocket: _StarletteWebSocket) -> None:
    """WebSocket at /: same protocol as run_sync_server."""
    await websocket.accept()
    await _handle_connection_starlette(websocket, _get_replica_root())


def build_sync_app() -> Starlette:
    """Build Starlette app with WebSocket at / and POST /sync/workspace."""
    return Starlette(
        routes=[
            Route("/sync/workspace", http_sync_workspace, methods=["POST"]),
            WebSocketRoute("/", websocket_sync),
        ],
    )


app = build_sync_app()
