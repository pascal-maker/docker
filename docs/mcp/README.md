# MCP integration

MCP (Model Context Protocol) lets Claude Code and Cursor call refactor tools. This directory documents the current state and planned direction.

## Current state

### In-repo MCP server (`ast-refactor`)

- **Status:** Works.
- **Location:** `src/refactor_agent/mcp/server.py`, `scripts/a2a/run_ast_refactor_mcp.py`
- Uses LibCST engine directly; reads file, renames, writes back. Does not call A2A or sync.
- See [clients/mcp-server.md](../clients/mcp-server.md) for setup.

### A2A–MCP bridge (GongRzhe)

- **Status:** Broken with sync deployment.
- The bridge sends inline `source` / `workspace` / `files` in the message. The executor now only accepts `use_replica: true` and rejects inline payloads with: *"use_replica must be true. Push workspace via sync first."*
- See [clients/cursor-bridge.md](../clients/cursor-bridge.md) for the previous setup.

## Future direction

We will build our own bridge with built-in sync. The MCP experience should ultimately match the VS Code extension: same flow (push workspace → A2A with `use_replica: true` → apply artifacts), but usable from Claude Code or Cursor for people who prefer MCP over the extension.
