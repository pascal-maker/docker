# Sync service

The sync service is the canonical way to get workspace state from a client to the server. All clients (VS Code extension, MCP bridge, Cursor, scripts) use it when using **use_replica** with the A2A server: (1) push workspace via the sync service, (2) call A2A with `use_replica: true`, (3) apply artifacts locally.

## Overview

- **Server:** [sync/server.py](../../../src/refactor_agent/sync/server.py) — listens (default port 8765), writes to a **replica directory** (`REPLICA_DIR`, default `/workspace`).
- **Client:** [sync/client.py](../../../src/refactor_agent/sync/client.py) — gathers files (e.g. `.py` under a root), pushes via WebSocket. Other clients (e.g. the VS Code extension) can implement the same protocol in TypeScript or use the HTTP upload endpoint.

## Running the sync server

```bash
uv run python -m refactor_agent.sync
```

Or:

```bash
uv run python scripts/sync/run_poc_sync_server.py
```

Default port: **8765** (override with `POC_SYNC_PORT`). Replica directory: **REPLICA_DIR** env (default `/workspace`). The A2A server must use the same `REPLICA_DIR` when handling requests with `use_replica: true`.

## Sync modes: clone vs full upload

**With `repo_url` (local + GitHub remote):** When `repo_url` is provided with bootstrap (POST `/sync/workspace` or WebSocket `bootstrap` message), the server clones the repo into `REPLICA_DIR` using the user's GitHub token. The client must send `Authorization: Bearer <token>` with `repo` scope. The server runs `git clone --depth 1` into the replica, then overlays any dirty/unsaved files from the request. This is faster when the workspace has a GitHub remote.

**Without `repo_url` (local-only):** When `repo_url` is omitted or null, the server skips the clone and writes only the files from the request. The client sends all workspace files (e.g. via `gatherWorkspaceFiles`). This supports strictly local workspaces with no remote. Slower but works without repository access.

On Cloud Run, sync and A2A share the same URL; the extension pushes workspace first, then calls A2A with `use_replica: true`.

## Ephemeral replica and TTL

The replica is ephemeral: it lives on the container's filesystem and is cleaned up after inactivity. Configure `REPLICA_TTL_MINUTES` (default 30); a background task clears `REPLICA_DIR` when no sync activity has occurred for that period. On reconnect or instance eviction, the client re-syncs (re-clone + overlay).

## WebSocket protocol

All messages are JSON. The server replies to each message with either `{"ok": "..."}` or `{"error": "..."}`.

### Message types

1. **`bootstrap_start`**  
   Clears the replica directory and prepares for a full sync. Send once, then send one or more `file` messages.

   Request: `{"type": "bootstrap_start"}`  
   Response: `{"ok": "bootstrap_start"}` or `{"error": "..."}`

2. **`bootstrap`**  
   Replaces the entire replica in one shot: wipe replica and write all listed files. Use when the full file list is small enough to send in one message (server allows up to 16 MiB per message).

   Request: `{"type": "bootstrap", "files": [{"path": "<relative path>", "content": "<file content>"}, ...]}`  
   Response: `{"ok": "bootstrap"}` or `{"error": "..."}`

   - `path` must be a non-empty string; it is relative to the replica root. Paths that escape the replica (e.g. `..`) are rejected.
   - `content` must be a string.

3. **`file`**  
   Writes or overwrites a single file in the replica.

   Request: `{"type": "file", "path": "<relative path>", "content": "<file content>"}`  
   Response: `{"ok": "file"}` or `{"error": "..."}`

## HTTP upload

The sync server exposes both WebSocket and HTTP. Clients can push workspace without WebSockets:

- **POST /sync/workspace**  
  Body: `{"files": [{"path": "<relative path>", "content": "<file content>"}, ...], "repo_url": "<optional GitHub URL>"}`  
  Same semantics as `bootstrap`: replaces the replica with the given files. If `repo_url` is provided, the server clones first then overlays files; otherwise it writes files only. Response: `200` with `{"ok": true}` or `4xx/5xx` with `{"error": "..."}`.

## Intended flow

1. **Push workspace** — Client gathers files (e.g. all `.py` under workspace root), sends via WebSocket (`bootstrap_start` + N×`file`, or one `bootstrap`) or POST `/sync/workspace`.
2. **Call A2A** — POST `message/send` with JSON body `{ "old_name": "...", "new_name": "...", "use_replica": true }`. Server reads workspace from `REPLICA_DIR`; do not send inline workspace.
3. **Apply artifacts** — For each `rename-result` artifact, apply `modified_source` to `path` in the client workspace.

## Security

- Paths are validated: they must not escape the replica root (e.g. `../` rejected).
- Run behind HTTPS and restrict access in production.
