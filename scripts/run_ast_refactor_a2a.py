"""Run the AST refactor A2A server (HTTP on port 9999).

Usage:
  uv run python scripts/run_ast_refactor_a2a.py

Then:
  - GET http://localhost:9999/.well-known/agent-card.json for the Agent Card.
  - Send a message/send request with JSON body containing source, old_name,
    new_name (and optional scope_node) to execute a rename task.

Compatibility: The GongRzhe A2A-MCP-Server bridge uses method names
tasks/send and tasks/sendSubscribe (rewritten to message/send and
message/stream) and expects "type" as the Part discriminator; the A2A
SDK sends "kind". Responses are rewritten to add type=kind so the bridge
validates.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid

import uvicorn
from dotenv import load_dotenv

load_dotenv()

from refactor_agent.a2a.auth_middleware import GitHubTokenMiddleware
from refactor_agent.a2a.server import build_app
from refactor_agent.auth.github_auth import GitHubTokenValidator
from refactor_agent.auth.user_store import UserStore

DEFAULT_PORT = 9999
RPC_PATH = "/"

# GongRzhe A2A-MCP-Server uses these; A2A spec uses message/send, message/stream
BRIDGE_SEND = "tasks/send"
BRIDGE_SEND_STREAM = "tasks/sendSubscribe"
BRIDGE_GET_TASK = "tasks/getResult"  # some bridges use this for get_task_result

logger = logging.getLogger(__name__)


def _bridge_params_to_sdk(params: dict) -> dict:
    """Map bridge TaskSendParams-like params to SDK MessageSendParams (snake_case)."""
    message = params.get("message")
    if isinstance(message, dict):
        message = dict(message)
        if "messageId" not in message and "message_id" not in message:
            message["message_id"] = uuid.uuid4().hex
        # Use bridge's task id so server stores task under the same id the bridge
        # will pass to get_task_result (avoids "Task not found"). GongRzhe
        # A2A-MCP-Server sends it as params.id (TaskSendParams), not taskId.
        task_id = (
            message.get("task_id")
            or message.get("taskId")
            or params.get("taskId")
            or params.get("id")
        )
        if task_id is not None and "task_id" not in message:
            message["task_id"] = task_id
        context_id = message.get("contextId") or params.get("contextId")
        if context_id is not None and "context_id" not in message:
            message["context_id"] = context_id
    out = {"message": message, "metadata": params.get("metadata")}
    config = {}
    if params.get("acceptedOutputModes") is not None:
        config["accepted_output_modes"] = params["acceptedOutputModes"]
    if params.get("historyLength") is not None:
        config["history_length"] = params["historyLength"]
    if params.get("pushNotification") is not None:
        config["push_notification_config"] = params["pushNotification"]
    if config:
        out["configuration"] = config
    return out


def _bridge_get_task_params_to_sdk(params: dict) -> dict:
    """Map bridge task-get params (camelCase) to SDK TaskQueryParams (snake_case)."""
    out = dict(params)
    if "taskId" in out and "id" not in out:
        out["id"] = out["taskId"]
    if "historyLength" in out and "history_length" not in out:
        out["history_length"] = out["historyLength"]
    return out


def _add_type_from_kind(obj: dict | list) -> dict | list:
    """Recursively add "type" key (copy of "kind") so bridge accepts Part/Message."""
    if isinstance(obj, dict):
        out = dict(obj)
        if "kind" in out and "type" not in out:
            out["type"] = out["kind"]
        for k, v in out.items():
            out[k] = _add_type_from_kind(v)
        return out
    if isinstance(obj, list):
        return [_add_type_from_kind(item) for item in obj]
    return obj


def _rewrite_bridge_methods(payload: dict) -> dict:
    """Rewrite GongRzhe bridge method names to A2A spec so the SDK accepts them."""
    method = payload.get("method")
    if method == BRIDGE_SEND:
        payload = dict(payload)
        payload["method"] = "message/send"
        if "params" in payload and isinstance(payload["params"], dict):
            payload["params"] = _bridge_params_to_sdk(payload["params"])
        return payload
    if method == BRIDGE_SEND_STREAM:
        payload = dict(payload)
        payload["method"] = "message/stream"
        if "params" in payload and isinstance(payload["params"], dict):
            payload["params"] = _bridge_params_to_sdk(payload["params"])
        return payload
    if method == BRIDGE_GET_TASK:
        payload = dict(payload)
        payload["method"] = "tasks/get"
        if "params" in payload and isinstance(payload["params"], dict):
            payload["params"] = _bridge_get_task_params_to_sdk(payload["params"])
        return payload
    if method == "tasks/get":
        # Bridge may send taskId/historyLength; SDK expects id/history_length
        payload = dict(payload)
        if "params" in payload and isinstance(payload["params"], dict):
            payload["params"] = _bridge_get_task_params_to_sdk(payload["params"])
        return payload
    return payload


def wrap_with_method_logging(app: object) -> object:
    """Log JSON-RPC method and rewrite bridge method names for A2A compat."""

    async def middleware(scope: dict, receive: object, send: object) -> None:
        if scope.get("type") != "http" or scope.get("method") != "POST":
            await app(scope, receive, send)
            return
        if scope.get("path") != RPC_PATH:
            await app(scope, receive, send)
            return
        # Consume body once, log method, rewrite bridge methods, then replay
        body = b""
        more = True
        while more:
            msg = await receive()
            body += msg.get("body", b"")
            more = msg.get("more_body", False)
        try:
            payload = json.loads(body)
            method = payload.get("method", "<missing>")
            logger.info("A2A JSON-RPC method: %s", method)
            payload = _rewrite_bridge_methods(payload)
            body = json.dumps(payload).encode()
        except (json.JSONDecodeError, TypeError):
            pass

        async def replay_receive() -> dict:
            return {"type": "http.request", "body": body, "more_body": False}

        body_chunks: list[bytes] = []
        pending_start: dict | None = None

        def set_content_length(
            headers: list[list[bytes]], length: int
        ) -> list[list[bytes]]:
            out = []
            set_ = False
            for name, value in headers:
                if name.lower() == b"content-length":
                    out.append([name, str(length).encode()])
                    set_ = True
                else:
                    out.append([name, value])
            if not set_:
                out.append([b"content-length", str(length).encode()])
            return out

        async def intercept_send(message: dict) -> None:
            nonlocal body_chunks, pending_start
            if message.get("type") == "http.response.start":
                pending_start = message
                return
            if message.get("type") == "http.response.body":
                chunk = message.get("body", b"")
                if chunk:
                    body_chunks.append(chunk)
                if not message.get("more_body", False):
                    # Full response received; add type=kind so bridge accepts
                    full = b"".join(body_chunks)
                    try:
                        data = json.loads(full)
                        data = _add_type_from_kind(data)
                        full = json.dumps(data).encode()
                    except (json.JSONDecodeError, TypeError):
                        pass
                    # Send start with corrected Content-Length so uvicorn accepts
                    if pending_start is not None:
                        headers = list(pending_start.get("headers", []))
                        start_msg = {
                            **pending_start,
                            "headers": set_content_length(headers, len(full)),
                        }
                        await send(start_msg)
                        pending_start = None
                    await send(
                        {
                            "type": "http.response.body",
                            "body": full,
                            "more_body": False,
                        }
                    )
                    return
            await send(message)

        await app(scope, replay_receive, intercept_send)

    return middleware


def main() -> None:
    """Run the A2A server with uvicorn."""
    app_factory = build_app()
    asgi_app = app_factory.build()
    asgi_app.add_middleware(
        GitHubTokenMiddleware,
        validator=GitHubTokenValidator(),
        user_store=UserStore(),
        local_dev_key=os.environ.get("A2A_API_KEY"),
    )
    wrapped = wrap_with_method_logging(asgi_app)
    port_val = (
        sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PORT", str(DEFAULT_PORT))
    )
    port = int(port_val)
    uvicorn.run(wrapped, host="0.0.0.0", port=port)  # noqa: S104
    # Listen on all interfaces for local dev / bridge access


if __name__ == "__main__":
    main()
