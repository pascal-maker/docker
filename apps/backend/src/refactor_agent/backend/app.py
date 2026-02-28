"""Combined A2A + sync ASGI app for Cloud Run (single service, single port)."""

from __future__ import annotations

import asyncio
import contextlib
import os

from refactor_agent.a2a.auth_middleware import (
    GitHubTokenMiddleware,
    _extract_bearer_from_scope,
    validate_token_for_scope,
)
from refactor_agent.a2a.method_logging import wrap_with_method_logging
from refactor_agent.a2a.server import build_app as build_a2a_app
from refactor_agent.auth.github_auth import GitHubTokenValidator
from refactor_agent.auth.user_store import UserStore
from refactor_agent.backend.router import build_combined_app_impl
from refactor_agent.sync.app import build_sync_app
from refactor_agent.sync.replica_ttl import replica_ttl_loop


def _lifespan_wrapper(app: object) -> object:
    """Wrap app with lifespan: start replica TTL cleanup task on startup."""

    async def _with_lifespan(scope: dict, receive: object, send: object) -> None:
        if scope.get("type") != "lifespan":
            await app(scope, receive, send)
            return

        msg = await receive()
        if msg.get("type") == "lifespan.startup":
            task = asyncio.create_task(replica_ttl_loop())
            await send({"type": "lifespan.startup.complete"})
            msg = await receive()
            if msg.get("type") == "lifespan.shutdown":
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
                await send({"type": "lifespan.shutdown.complete"})

    return _with_lifespan


def _websocket_auth_middleware(app: object) -> object:
    """ASGI middleware: validate WebSocket auth before passing to app."""

    async def _ws_auth(scope: dict, receive: object, send: object) -> None:
        if scope.get("type") != "websocket":
            await app(scope, receive, send)
            return

        validator = GitHubTokenValidator()
        user_store = UserStore()
        local_dev_key = os.environ.get("A2A_API_KEY")

        user_record, err = await validate_token_for_scope(
            scope,
            validator=validator,
            user_store=user_store,
            local_dev_key=local_dev_key,
        )
        if err is not None:
            await send(
                {
                    "type": "websocket.close",
                    "code": 4003,
                    "reason": err[:123],
                }
            )
            return

        token = _extract_bearer_from_scope(scope)
        state = scope.setdefault("state", {})
        if not isinstance(state, dict):
            state = {}
            scope["state"] = state
        state["github_token"] = token
        state["user_record"] = user_record
        scope["state"] = state

        await app(scope, receive, send)

    return _ws_auth


def build_combined_app() -> object:
    """Build combined A2A + sync ASGI app with routing by path and request type."""
    a2a_factory = build_a2a_app()
    a2a_app = wrap_with_method_logging(a2a_factory.build())
    sync_app = build_sync_app()

    router = build_combined_app_impl(a2a_app=a2a_app, sync_app=sync_app)
    app = _websocket_auth_middleware(router)
    app = _lifespan_wrapper(app)
    return GitHubTokenMiddleware(
        app,
        validator=GitHubTokenValidator(),
        user_store=UserStore(),
        local_dev_key=os.environ.get("A2A_API_KEY"),
        public_paths=frozenset({"/.well-known/agent-card.json"}),
    )
