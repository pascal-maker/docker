"""MCP server exposing AST refactor tools (rename_symbol) via FastMCP."""

from __future__ import annotations

from pathlib import Path

import libcst as cst
from fastmcp import FastMCP

from refactor_agent.engine.python.libcst_engine import LibCSTEngine

mcp = FastMCP("ast-refactor")


async def _rename_symbol_in_file(
    file_path: Path,
    old_name: str,
    new_name: str,
    scope_node: str | None = None,
) -> str:
    """Read file, rename symbol with LibCSTEngine, write back.

    Returns summary or error string.
    """
    out: str = ""
    try:
        source = file_path.read_text(encoding="utf-8")  # noqa: ASYNC240 — sync I/O in MCP handler
    except FileNotFoundError:
        out = f"ERROR: file not found: {file_path}"
    except OSError as e:
        out = f"ERROR: could not read file: {e}"
    else:
        try:
            engine = LibCSTEngine(source)
        except cst.ParserSyntaxError as e:
            out = f"ERROR: invalid Python syntax: {e}"
        else:
            result = await engine.rename_symbol(old_name, new_name, scope_node)
            if result.startswith("ERROR:"):
                out = result
            else:
                try:
                    new_source = await engine.to_source()
                    file_path.write_text(  # noqa: ASYNC240 — sync I/O in MCP handler
                        new_source, encoding="utf-8"
                    )
                    out = result
                except OSError as e:
                    out = f"ERROR: could not write file: {e}"
    return out


@mcp.tool()
async def rename_symbol(
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
        Summary string (e.g. 'Renamed X -> Y: N occurrence(s) at lines ...')
        or an error string starting with 'ERROR:'.
    """
    path = Path(file_path).resolve()  # noqa: ASYNC240 — sync path resolution is fine
    return await _rename_symbol_in_file(path, old_name, new_name, scope_node)


if __name__ == "__main__":
    mcp.run()
