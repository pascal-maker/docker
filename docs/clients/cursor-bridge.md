# Using the A2A agent from Cursor (A2A–MCP bridge)

**VS Code users:** Use the [Refactor Agent extension](vscode-extension/overview.md); no MCP setup. The extension speaks A2A HTTP directly.

**Note:** The GongRzhe A2A–MCP bridge is incompatible with the sync deployment (executor requires `use_replica: true`). See [MCP integration](../mcp/README.md) for status and future plans.

Cursor talks to agents via MCP. To use the A2A refactor agent from Cursor, run an A2A–MCP bridge so Cursor can send tasks to your A2A server.

## Setup

1. **Start the A2A server:**

   ```bash
   uv run python scripts/a2a/run_ast_refactor_a2a.py
   ```

2. **Configure the A2A–MCP bridge** in `.cursor/mcp.json` (e.g. `uvx a2a-mcp-server` as the `a2a` server). The [GongRzhe A2A-MCP-Server](https://github.com/GongRzhe/A2A-MCP-Server) uses method names `tasks/send` and `tasks/sendSubscribe`; this A2A server rewrites them to the A2A-spec `message/send` and `message/stream` so the bridge works without changes. Restart or refresh MCP in Cursor so it loads the bridge.

3. **In Cursor**, use the bridge's MCP tools:
   - **`register_agent`** — register your agent, e.g. `http://localhost:9999`
   - **`send_message`** — send a rename task (same JSON payload as the A2A server accepts)
   - **`get_task_result`** — poll for the result when the task is async or in `input_required`

   Example prompt: *"Register the A2A agent at http://localhost:9999"* then *"Ask that agent to rename greet to main in this Python source: [paste source]. If it asks for confirmation, say yes."*

## Troubleshooting: -32601 "Method not found"

The server supports these A2A JSON-RPC methods: `message/send`, `message/stream`, `tasks/get`, `tasks/cancel`, `tasks/resubscribe`, and `tasks/pushNotificationConfig/*`.

When using the GongRzhe bridge, the server automatically rewrites `tasks/send` → `message/send` and `tasks/sendSubscribe` → `message/stream`, so -32601 should not occur for send/stream.

If another client uses a different method name, the server returns -32601. Check the A2A server log — each request's method is logged as `A2A JSON-RPC method: <name>` so you can see what was sent.
