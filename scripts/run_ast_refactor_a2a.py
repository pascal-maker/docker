"""Run the AST refactor A2A server (HTTP on port 9999).

Usage:
  uv run python scripts/run_ast_refactor_a2a.py

Then:
  - GET http://localhost:9999/.well-known/agent-card.json for the Agent Card.
  - Send a message/send request with JSON body containing source, old_name,
    new_name (and optional scope_node) to execute a rename task.
"""

from __future__ import annotations

import sys

import uvicorn

from document_structuring_agent.ast_refactor.a2a_server import build_app

DEFAULT_PORT = 9999


def main() -> None:
    """Run the A2A server with uvicorn."""
    app_factory = build_app()
    asgi_app = app_factory.build()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    uvicorn.run(asgi_app, host="0.0.0.0", port=port)  # noqa: S104 — listen on all interfaces


if __name__ == "__main__":
    main()
