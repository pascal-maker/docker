---
title: Getting started
---

# Getting started

Two ways to use the refactor agent: run everything locally (Docker) or use the extension / Cursor bridge against a running server.

## Path 1: Run locally with Docker

1. **Start the server** (sync + A2A in one container):

   ```bash
   docker compose up --build
   ```

   This starts the sync server (port 8765) and A2A HTTP server (port 9999). Set `ANTHROPIC_API_KEY` in `.env` or the environment.

2. **Sync your workspace** to the replica (in another terminal):

   ```bash
   uv run python scripts/sync/run_poc_sync_client.py /path/to/your/project
   ```

   Or sync this repo: `uv run python scripts/sync/run_poc_sync_client.py .`

3. **Use a client** to talk to the agent:
   - **VS Code / Cursor:** Install the [Refactor Agent extension](../clients/vscode-extension/README.md); it speaks A2A HTTP directly.
   - **Cursor (MCP):** Configure the [A2A–MCP bridge](../clients/cursor-bridge.md) and point it at `http://localhost:9999`.

See [Docker deployment](../clients/docker-deployment.md) for details (LiteLLM proxy, env vars, running without Docker).

## Path 2: Use extension or Cursor (server already running)

If the A2A server is already running (e.g. started by someone else or in another terminal):

- **VS Code / Cursor:** Use the [Refactor Agent extension](../clients/vscode-extension/README.md). Configure the A2A base URL to match your server (e.g. `http://localhost:9999`).
- **Cursor only:** Use the [Cursor bridge](../clients/cursor-bridge.md): register the agent at your server URL, then use the bridge’s MCP tools to send refactor tasks.

## Dev UI (Chainlit)

For development and full feature visibility, run the Chat UI:

```bash
make ui
```

Then open the Chainlit app (default localhost:8000). See [Chat UI (Chainlit)](../clients/chat-ui.md) for modes (Ask / Auto / Plan), persistence, and auth.

## Next steps

- [Architecture](architecture.md) — how the orchestrator and two surfaces (Dev UI vs A2A) work.
- [Integrations](integrations.md) — all entry points (A2A, sync, dashboard, MCP).
- [Troubleshooting](troubleshooting.md) — common issues.
