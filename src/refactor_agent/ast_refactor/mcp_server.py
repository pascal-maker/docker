"""MCP server exposing AST refactor tools (rename_symbol) via FastMCP."""

from __future__ import annotations

from pathlib import Path

import libcst as cst
from fastmcp import FastMCP

from refactor_agent.ast_refactor.engine import LibCSTEngine

mcp = FastMCP("ast-refactor")


def _rename_symbol_in_file(  # noqa: PLR0911 — six exit paths kept for clarity
    file_path: Path,
    old_name: str,
    new_name: str,
    scope_node: str | None = None,
) -> str:
    """Read file, rename symbol with LibCSTEngine, write back.

    Returns summary or error string.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"ERROR: file not found: {file_path}"
    except OSError as e:
        return f"ERROR: could not read file: {e}"

    try:
        engine = LibCSTEngine(source)
    except cst.ParserSyntaxError as e:
        return f"ERROR: invalid Python syntax: {e}"

    result = engine.rename_symbol(old_name, new_name, scope_node)
    if result.startswith("ERROR:"):
        return result

    try:
        file_path.write_text(engine.to_source(), encoding="utf-8")
    except OSError as e:
        return f"ERROR: could not write file: {e}"

    return result


@mcp.tool()
def rename_symbol(
    file_path: str,
    old_name: str,
    new_name: str,
    scope_node: str | None = None,
) -> str:
    """Rename a Python symbol in a file using semantic AST analysis.

    Preserves formatting and comments. Optionally restrict to a function or
    class scope. Reads and overwrites the file at file_path.

    Args:
        file_path: Absolute or relative path to the Python file.
        old_name: Current symbol name in the file.
        new_name: Desired new name.
        scope_node: Optional function or class name to restrict the rename
            to that scope; None for file-wide rename.

    Returns:
        Summary string (e.g. 'Renamed X → Y: N occurrence(s) at lines ...')
        or an error string starting with 'ERROR:'.
    """
    path = Path(file_path).resolve()
    return _rename_symbol_in_file(path, old_name, new_name, scope_node)


if __name__ == "__main__":
    mcp.run()
