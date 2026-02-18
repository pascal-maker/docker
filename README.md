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
- **Rename task:** Send an A2A `message/send` request with a JSON body: `{"source": "<Python source>", "old_name": "...", "new_name": "...", "scope_node": "..."}` (optional). The server runs the rename and returns the result (summary + modified source) in the response.

**Test the A2A server:** With the server running, in another terminal:

```bash
uv run python scripts/test_a2a_rename.py
```

This GETs the agent card and POSTs a rename task; it prints the card and the agent’s response (summary + modified source). Optional: pass a base URL, e.g. `uv run python scripts/test_a2a_rename.py http://localhost:8080`.