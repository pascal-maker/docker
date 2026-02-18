"""Run the AST refactor MCP server (stdio transport).

Usage:
  uv run python scripts/run_ast_refactor_mcp.py

Or add to Claude Code / Cursor MCP config, e.g.:
  {
    "mcpServers": {
      "ast-refactor": {
        "command": "uv",
        "args": ["run", "python", "scripts/run_ast_refactor_mcp.py"],
        "cwd": "/path/to/document-structuring-agent"
      }
    }
  }
"""

from __future__ import annotations

import os
import sys

# Ensure repo root is cwd and src is on path (Cursor MCP may start process with wrong cwd)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)
os.chdir(_repo_root)
_src = os.path.join(_repo_root, "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from document_structuring_agent.ast_refactor.mcp_server import mcp

if __name__ == "__main__":
    mcp.run()
