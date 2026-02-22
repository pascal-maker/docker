# Docker deployment

Runs the sync server and A2A refactor agent in one isolated container. The local sync client keeps a replica in sync on save over WebSockets; the agent reads from the replica. An MCP bridge applies refactor results to your local workspace.

## Start the server

```bash
docker compose up --build
```

This starts both the **LiteLLM proxy** (port 4000) and the **POC server** (8765 WebSocket sync, 9999 A2A HTTP). Set `ANTHROPIC_API_KEY` in the environment or `.env`; the POC server sends all LLM traffic through the proxy. To run only the POC server (e.g. to talk to Anthropic directly), use `docker compose up poc-server` and unset `LITELLM_PROXY_URL` in the environment.

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

## LiteLLM proxy

The Compose file includes a LiteLLM proxy so all LLM traffic is routed through one gateway (caching, load balancing). For local runs without Docker you can run the proxy separately:

1. Install: `pip install 'litellm[proxy]'` (or use a separate env).
2. Set `ANTHROPIC_API_KEY` in the environment.
3. From the repo root: `litellm --config config/litellm.yaml` (listens on port 4000).
4. In the app env set `LITELLM_PROXY_URL=http://localhost:4000`. Leave unset to talk to Anthropic directly.

### Environment variables

**App / adapter (when using the proxy):**

- `LITELLM_PROXY_URL` — optional; if set, all Anthropic traffic goes through this URL (e.g. `http://localhost:4000` or `http://litellm:4000` in Compose).
- `LITELLM_MASTER_KEY` — optional; proxy caller key when the proxy requires auth.
- `ANTHROPIC_API_KEY` — required for real model calls (used by the app when not using the proxy, and by the proxy when it calls Anthropic).

**Proxy process:**

- `ANTHROPIC_API_KEY` — for routing to Anthropic.
- If cache is enabled in `config/litellm.yaml`: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` (or `REDIS_URL`).

To point the Langfuse Playground and LLM-as-a-Judge at the same LiteLLM gateway (no UI setup), run once per project/environment:

```bash
# With LITELLM_PROXY_URL and Langfuse keys set (e.g. in .env):
uv run python scripts/setup_langfuse_llm_connection.py
```

If `LITELLM_PROXY_URL` is unset, the script no-ops. Optional: `LANGFUSE_LLM_CONNECTION_MODELS` (comma-separated model names; default `claude-sonnet-4-6`).

### Open WebUI stack

When the Open WebUI integration is added (adapter + Open WebUI in Compose), add the same LiteLLM proxy as a service in that stack. Use the same `config/litellm.yaml`; set `LITELLM_PROXY_URL=http://litellm:4000` (or the chosen service name) for the adapter and any other service that runs the refactor-agent code. No code change in the adapter beyond using the shared client.
