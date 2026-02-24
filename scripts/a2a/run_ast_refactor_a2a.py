"""Run the AST refactor A2A server (HTTP on port 9999).

Usage:
  uv run python scripts/a2a/run_ast_refactor_a2a.py

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

import os
import sys

import uvicorn
from dotenv import load_dotenv

load_dotenv()

from refactor_agent.a2a.auth_middleware import GitHubTokenMiddleware
from refactor_agent.a2a.method_logging import wrap_with_method_logging
from refactor_agent.a2a.server import build_app
from refactor_agent.auth.github_auth import GitHubTokenValidator
from refactor_agent.auth.user_store import UserStore

DEFAULT_PORT = 9999


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
