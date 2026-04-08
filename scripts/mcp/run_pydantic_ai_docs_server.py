"""Run the PydanticAI docs MCP server from the active environment.

Set ``PYDANTIC_AI_DOCS_SERVER_PATH`` to a local checkout if the module is not
installed in the current environment.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def _extend_sys_path_from_env() -> None:
    """Add an optional checkout path for the docs server to ``sys.path``."""
    repo_path = os.environ.get("PYDANTIC_AI_DOCS_SERVER_PATH")
    if repo_path is None:
        return

    module_root = Path(repo_path).expanduser().resolve()
    if not module_root.exists():
        msg = (
            "Configured PYDANTIC_AI_DOCS_SERVER_PATH does not exist: "
            f"{module_root}"
        )
        raise SystemExit(msg)

    resolved_module_root = str(module_root)
    if resolved_module_root not in sys.path:
        sys.path.insert(0, resolved_module_root)


def _main() -> None:
    """Execute the docs server module and surface a typed setup error."""
    _extend_sys_path_from_env()
    try:
        runpy.run_module("pydantic_ai_docs_server", run_name="__main__")
    except ModuleNotFoundError as error:
        if error.name != "pydantic_ai_docs_server":
            raise
        msg = (
            "Could not import `pydantic_ai_docs_server`. Install it in the "
            "active environment or set PYDANTIC_AI_DOCS_SERVER_PATH to a "
            "checkout containing that module."
        )
        raise SystemExit(msg) from error


if __name__ == "__main__":
    _main()
