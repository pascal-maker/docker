---
title: Troubleshooting
---

# Troubleshooting

Common issues and where to find more detail.

## Cursor: -32601 "Method not found"

When using the A2A–MCP bridge with Cursor, the server supports A2A methods `message/send`, `message/stream`, `tasks/get`, `tasks/cancel`, etc. The GongRzhe bridge’s `tasks/send` and `tasks/sendSubscribe` are rewritten to these, so -32601 should not occur for send/stream. If you see -32601, check the A2A server log for the method name that was sent.

See [Cursor bridge](../clients/cursor-bridge.md) for setup and method details.

## pydantic-ai and Anthropic SDK compatibility

Import or compatibility issues between pydantic-ai and the Anthropic SDK (e.g. `UserLocation`) and workarounds.

See [pydantic-ai-anthropic-compat-issue.md](../reference/pydantic-ai-anthropic-compat-issue.md).

## VS Code extension: blank panel or missing messages

Use the webview DevTools and console logs to debug. Common causes: wrong A2A URL, server not running, or CORS/network.

See [VS Code extension — Debugging](../clients/vscode-extension/debugging.md).

## Scaling and pipeline failures

Findings on plan-vs-execution gaps, failure modes, and next steps for the refactor pipeline.

See [Scaling refactor pipeline](../reference/scaling-refactor-pipeline.md).

## Other

- **Sync client not connecting:** Check `POC_SYNC_WS_URL` (default `ws://localhost:8765`) and that the sync server is running ([Docker deployment](../clients/docker-deployment.md), [Sync service](../clients/sync-service.md)).
- **A2A server not responding:** Ensure the server is running (e.g. `uv run python scripts/run_ast_refactor_a2a.py`) and the URL in your client matches (default port 9999).
