# MCP server (stdio)

See [MCP integration](../mcp/README.md) for status and future plans.

Start the MCP server so Claude Code or Cursor can call the `rename_symbol` tool:

```bash
uv run --directory apps/backend python scripts/mcp/run_ast_refactor_mcp.py
```

The server uses stdio: a client spawns this process and talks to it over stdin/stdout.

## Configuration

To add it as an MCP server in Claude Code or Cursor:

- **Command:** `uv`
- **Args:** `run`, `python`, `scripts/mcp/run_ast_refactor_mcp.py`
- **Required:** set **`cwd`** to this repo's root. Without it, the client will look for the script in the wrong directory.

Example config (Claude Code / Cursor):

```json
{
  "mcpServers": {
    "ast-refactor": {
      "command": "uv",
      "args": ["run", "--directory", "apps/backend", "python", "scripts/mcp/run_ast_refactor_mcp.py"],
      "cwd": "<path-to-this-repo>"
    }
  }
}
```

Replace `<path-to-this-repo>` with the absolute path to your clone.

## Tool

`rename_symbol(file_path, old_name, new_name, scope_node?)` — renames a Python symbol in a file using the LibCST engine (preserves formatting and comments).
