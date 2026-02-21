# Docker deployment

Runs the sync server and A2A refactor agent in one isolated container. The local sync client keeps a replica in sync on save over WebSockets; the agent reads from the replica. An MCP bridge applies refactor results to your local workspace.

## Start the server

```bash
docker compose up --build
```

Ports: **8765** (WebSocket sync), **9999** (A2A HTTP).

## Sync your workspace to the replica

In another terminal, run the sync client. It watches for file saves and pushes changes to the container's replica directory.

From this repo, sync another project:

```bash
uv run python scripts/run_poc_sync_client.py /path/to/your/python/project
```

Sync this repo itself:

```bash
uv run python scripts/run_poc_sync_client.py .
```

From another directory:

```bash
uv run python <this-repo>/scripts/run_poc_sync_client.py /path/to/your/python/project
```

Default WebSocket URL is `ws://localhost:8765`; override with `POC_SYNC_WS_URL` if needed.

## MCP bridge

Use the refactor bridge so Cursor/Claude can call the remote agent (`use_replica`) and apply artifacts locally. Configure an MCP server that runs `scripts/run_refactor_bridge.py` with `cwd` set to this repo and env `A2A_REFACTOR_URL=http://localhost:9999` (and optional `WORKSPACE_ROOT` for apply path resolution). See the refactor bridge script for details.
