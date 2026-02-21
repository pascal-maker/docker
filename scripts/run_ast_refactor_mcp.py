"""Run the AST refactor MCP server (stdio transport).

Usage:
  uv run python scripts/run_ast_refactor_mcp.py

Or add to Claude Code / Cursor MCP config, e.g.:
  {
    "mcpServers": {
      "ast-refactor": {
        "command": "uv",
        "args": ["run", "python", "scripts/run_ast_refactor_mcp.py"],
        "cwd": "/path/to/refactor-agent"
      }
    }
  }
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repo root is cwd and src is on path (MCP may start with wrong cwd)
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent
os.chdir(_repo_root)
_src = _repo_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from refactor_agent.mcp.server import mcp  # noqa: E402

if __name__ == "__main__":
    mcp.run()
