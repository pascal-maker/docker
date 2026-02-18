To run:
- Terminal 1: `uv run uvicorn api.main:app --reload --port 8000`
- Terminal 2: `cd ui && pnpm dev`

## AST refactor servers (MCP and A2A)

### MCP server (stdio)

Start the MCP server so Claude Code or Cursor can call the `rename_symbol` tool:

```bash
uv run python scripts/run_ast_refactor_mcp.py
```

The server uses stdio: a client spawns this process and talks to it over stdin/stdout. To add it as an MCP server in Claude Code or Cursor:

- **Command:** `uv`
- **Args:** `run`, `python`, `scripts/run_ast_refactor_mcp.py`
- **Required:** set **`cwd`** to this repo’s root (e.g. `/Users/thomas/Documents/personal/repos/document-structuring-agent`). Without it, the client will look for `scripts/run_ast_refactor_mcp.py` in the wrong directory and you’ll see: `can't open file '.../scripts/run_ast_refactor_mcp.py': No such file or directory`.

Example config (Claude Code / Cursor):

```json
{
  "mcpServers": {
    "ast-refactor": {
      "command": "uv",
      "args": ["run", "python", "scripts/run_ast_refactor_mcp.py"],
      "cwd": "/Users/thomas/Documents/personal/repos/document-structuring-agent"
    }
  }
}
```

Replace the `cwd` path with your actual repo root.

Tool: `rename_symbol(file_path, old_name, new_name, scope_node?)` — renames a Python symbol in a file using the LibCST engine (preserves formatting and comments).

### A2A server (HTTP)

Start the A2A server for agent-to-agent refactor tasks (default port 9999):

```bash
uv run python scripts/run_ast_refactor_a2a.py
```

Custom port:

```bash
uv run python scripts/run_ast_refactor_a2a.py 8080
```

Clients can reach it at:

- **Agent Card:** `GET http://localhost:9999/.well-known/agent-card.json` — discover the agent’s skills and capabilities.
- **Rename task:** Send an A2A `message/send` request with a JSON body: `{"source": "<Python source>", "old_name": "...", "new_name": "...", "scope_node": "..." (optional), "path": "path/to/file.py" (optional)}`. The server runs the rename and returns the result in the task **status message** and in a **rename-result artifact** with `modified_source` and (if you sent it) `path`, so the client can apply the edit to the right file. **Request formats:** (1) **Single-file:** source, old_name, new_name, optional path. (2) **Workspace (full impact):** old_name, new_name, workspace: [{path, source}, ...] — the agent finds which files reference the symbol and returns one rename-result artifact per impacted file; the client applies every artifact. (3) **Explicit files:** files: [{path, source}, ...] to refactor a fixed list. Apply each artifact’s modified_source to its path.

**Test the A2A server:** With the server running, in another terminal:

```bash
uv run python scripts/test_a2a_rename.py
```

This GETs the agent card and POSTs a rename task; it prints the card and the agent’s response (summary + modified source). Optional: pass a base URL, e.g. `uv run python scripts/test_a2a_rename.py http://localhost:8080`.

### Testing human-in-the-loop (name collision)

To trigger the "pause and ask" flow, send a rename that would cause a **name collision** (e.g. rename `greet` to `main` when `main` already exists in the file). The agent returns `input_required` and an artifact; you then send a second message with the same task to confirm or cancel.

**Note:** The server must be running the version that includes collision detection (human-in-the-loop). Restart the A2A server after pulling or changing the executor so it loads the latest code.

1. **Start the A2A server** (Terminal 1):

   ```bash
   uv run python scripts/run_ast_refactor_a2a.py
   ```

2. **Send a collision-producing request.** Easiest is the Python script (avoids JSON/shell escaping of the newline in `source`):

   ```bash
   uv run python scripts/test_a2a_collision.py
   ```

   The script sends a rename that would shadow `main`, then (unless you pass `--no`) sends `yes` to confirm. You should see `Response kind: task`, `Status state: input-required`, then the result of the confirmed rename.

   Alternatively with `curl`, ensure the `source` value in the inner JSON contains a real newline between the two `def` lines (e.g. `\"def main(): pass\\n\ndef greet(n): return n\"`). The response should have `"kind": "task"` and `"state": "input-required"` in `result.status`.

3. **Resume with yes or no:** From the response, take `result.id` (taskId) and `result.contextId`. Send a second `message/send` with the same `taskId` and `contextId` in the message, and the new user part as `"yes"` or `"no"`:

   ```bash
   curl -s -X POST http://localhost:9999 \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": "2",
       "method": "message/send",
       "params": {
         "message": {
           "kind": "message",
           "role": "user",
           "messageId": "m2",
           "contextId": "<contextId from step 2>",
           "taskId": "<taskId from step 2>",
           "parts": [{"kind": "text", "text": "yes"}]
         }
       }
     }'
   ```

   With `"yes"` you get the rename result; with `"no"` you get "Rename canceled."

### Using the A2A agent from Cursor (A2A–MCP bridge)

Cursor talks to agents via MCP. To use this A2A refactor agent from Cursor, run an **A2A–MCP bridge** so Cursor can send tasks to your A2A server. Project config is in `.cursor/mcp.json`.

1. **Start the A2A server** (so the agent is reachable):

   ```bash
   uv run python scripts/run_ast_refactor_a2a.py
   ```

2. **Ensure the A2A–MCP bridge is configured** in `.cursor/mcp.json` (e.g. `uvx a2a-mcp-server` as the `a2a` server). The [GongRzhe A2A-MCP-Server](https://github.com/GongRzhe/A2A-MCP-Server) uses method names `tasks/send` and `tasks/sendSubscribe`; this A2A server rewrites them to the A2A-spec `message/send` and `message/stream` so the bridge works without changes. Restart or refresh MCP in Cursor so it loads the bridge.

3. **In Cursor**, use the bridge's MCP tools:
   - **`register_agent`** — register your agent, e.g. `http://localhost:9999`
   - **`send_message`** — send a rename task (same JSON payload as above in the message part)
   - **`get_task_result`** — poll for the result when the task is async or in `input_required`

   Example prompt: *"Register the A2A agent at http://localhost:9999"* then *"Ask that agent to rename greet to main in this Python source: [paste source with both main and greet]. If it asks for confirmation, say yes."*

#### If you see -32601 "Method not found"

The server supports the A2A JSON-RPC methods: `message/send`, `message/stream`, `tasks/get`, `tasks/cancel`, `tasks/resubscribe`, and `tasks/pushNotificationConfig/*`. When using the [GongRzhe A2A-MCP-Server](https://github.com/GongRzhe/A2A-MCP-Server) bridge, the server automatically rewrites `tasks/send` and `tasks/sendSubscribe` to `message/send` and `message/stream`, so -32601 from that bridge should no longer occur for send/stream. If another client uses a different method name, the server returns **-32601**. Check the A2A server log: each request’s method is logged as **`A2A JSON-RPC method: <name>`** so you can see what was sent.