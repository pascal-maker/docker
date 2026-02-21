# refactor-agent

Semantic AST-level code refactoring as a service. Typed tree operations exposed as agent tools — rename, extract, move — with deterministic execution, scope awareness, and full formatting preservation.

## Quickstart

```bash
uv sync
make check        # format, lint, typecheck, test
make ui           # launch Chainlit dev UI at localhost:8000
```

## Architecture

```
engine/        pure refactoring operations (libcst, no framework deps)
agent/         PydanticAI agent (thin glue: tools delegate to engine)
observability/ Langfuse tracing + prompt management
a2a/           A2A protocol adapter
mcp/           MCP protocol adapter
ui/            Chainlit dev chat UI
sync/          WebSocket file sync (for Docker deployment)
```

## Docs

- [Chat UI](docs/chat-ui.md) — interactive dev interface (Chainlit)
- [A2A server](docs/a2a-server.md) — agent-to-agent protocol, request formats, collision testing
- [MCP server](docs/mcp-server.md) — MCP tool integration for Claude Code / Cursor
- [Cursor bridge](docs/cursor-bridge.md) — using the agent from Cursor via A2A–MCP bridge
- [Docker deployment](docs/docker-deployment.md) — containerized setup with file sync
- [Ideas](docs/ideas.md) — design notes, DSL concepts, future directions
