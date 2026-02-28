"""ASGI router for combined A2A + sync app."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.types import Receive, Scope, Send


async def _combined_router(
    scope: Scope,
    receive: Receive,
    send: Send,
    *,
    a2a_app: object,
    sync_app: object,
) -> None:
    """Route by path and request type: A2A or Sync."""
    path = (scope.get("path") or "").rstrip("/") or "/"
    req_type = scope.get("type")

    if req_type == "http":
        method = scope.get("method", "")
        if path == "/.well-known/agent-card.json" and method == "GET":
            await a2a_app(scope, receive, send)
            return
        if path == "/sync/workspace" and method == "POST":
            await sync_app(scope, receive, send)
            return
        if path == "/" and method == "POST":
            await a2a_app(scope, receive, send)
            return
        # 404
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [[b"content-type", b"application/json"]],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b'{"error":"Not Found"}',
                "more_body": False,
            }
        )
        return

    if req_type == "websocket":
        if path == "/":
            await sync_app(scope, receive, send)
            return
        await send({"type": "websocket.close", "code": 4004, "reason": "Not Found"})


def build_combined_app_impl(
    *,
    a2a_app: object,
    sync_app: object,
) -> object:
    """Build the raw ASGI router (no middleware)."""

    async def _app(scope: Scope, receive: Receive, send: Send) -> None:
        await _combined_router(
            scope,
            receive,
            send,
            a2a_app=a2a_app,
            sync_app=sync_app,
        )

    return _app
