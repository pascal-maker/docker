---
title: Integrations (APIs)
---

# Integrations (APIs)

The refactor agent exposes several entry points. This page lists them with short descriptions; follow the links for details.

## A2A server (HTTP)

Agent-to-agent refactor tasks over HTTP. Same orchestrator as the Chat UI; human-in-the-loop (e.g. name collision) uses `input_required` and resumption.

- **Agent Card:** `GET /.well-known/agent-card.json`
- **Refactor:** `POST /` with A2A `message/send` JSON-RPC (single-file, workspace, or explicit files).

See [A2A server (HTTP)](../clients/a2a-server.md) for endpoints, request formats, and Agent Card.

## Sync service

WebSocket service that keeps a **replica** of the client’s workspace on the server. All clients that use **use_replica** with the A2A server: (1) push workspace via sync, (2) call A2A with `use_replica: true`, (3) apply artifacts locally.

- **Server:** default port 8765; writes to a replica directory.
- **Client:** Python client or VS Code extension; same WebSocket protocol.

See [Sync service](../clients/sync-service.md) for running the server and the WebSocket protocol.

## Dashboard (ingestion API)

Centralized dashboard for refactor/architecture check results: CI posts to an ingestion API; users view issues by org/repo in a React UI.

- **Ingestion:** `POST /api/ingest/check-result`
- **Query:** `GET /api/orgs/{org_id}/issues` (list), `GET /api/orgs/{org_id}/issues/{run_id}` (detail).

See [Refactor issues dashboard](../contributing/dashboard.md) for running the backend and frontend and seeding sample data.

## MCP server (stdio)

Stdio MCP server for Claude Code or Cursor: one tool, `rename_symbol(file_path, old_name, new_name, scope_node?)`, using the LibCST engine. The client spawns the process and talks over stdin/stdout.

See [MCP server (stdio)](../clients/mcp-server.md) for the run command and MCP config (`cwd` must be the repo root).

## Summary

| Entry point      | Purpose                          | Doc |
|------------------|----------------------------------|-----|
| A2A HTTP         | Agent-to-agent refactor tasks    | [a2a-server.md](../clients/a2a-server.md) |
| Sync (WebSocket) | Workspace replica for use_replica| [sync-service.md](../clients/sync-service.md) |
| Dashboard API    | Ingest and query check results   | [dashboard.md](../contributing/dashboard.md) |
| MCP (stdio)      | rename_symbol for Claude/Cursor  | [mcp-server.md](../clients/mcp-server.md) |
