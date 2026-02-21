"""Tests for MCP server: rename_symbol file read/write flow."""

from __future__ import annotations

from pathlib import Path

from refactor_agent.mcp.server import (
    _rename_symbol_in_file,
)


def test_rename_symbol_in_file_success(tmp_path: Path) -> None:
    """Helper renames symbol and writes file back; returns summary."""
    path = tmp_path / "code.py"
    path.write_text(
        "def calculate_tax(amount, rate):\n"
        "    return round(amount * rate, 2)\n"
        "\n"
        "def main():\n"
        "    print(calculate_tax(100, 0.2))\n",
        encoding="utf-8",
    )
    result = _rename_symbol_in_file(
        path, "calculate_tax", "compute_tax", scope_node=None
    )
    assert "Renamed" in result
    assert "compute_tax" in result
    content = path.read_text(encoding="utf-8")
    assert "def compute_tax(" in content
    assert "compute_tax(100" in content
    assert "calculate_tax" not in content


def test_rename_symbol_in_file_not_found() -> None:
    """Helper returns ERROR when file does not exist."""
    result = _rename_symbol_in_file(
        Path("/nonexistent/code.py"), "foo", "bar", scope_node=None
    )
    assert "ERROR" in result
    assert "not found" in result


def test_rename_symbol_in_file_invalid_syntax(tmp_path: Path) -> None:
    """Helper returns ERROR when file is not valid Python."""
    path = tmp_path / "bad.py"
    path.write_text("def foo( \n  syntax error", encoding="utf-8")
    result = _rename_symbol_in_file(path, "foo", "bar", scope_node=None)
    assert "ERROR" in result
    assert "syntax" in result.lower()


def test_rename_symbol_in_file_symbol_not_found(tmp_path: Path) -> None:
    """Helper returns ERROR when symbol is not in file."""
    path = tmp_path / "code.py"
    path.write_text("def foo(): pass\n", encoding="utf-8")
    result = _rename_symbol_in_file(path, "bar", "baz", scope_node=None)
    assert "ERROR" in result
    assert path.read_text() == "def foo(): pass\n"


def test_rename_symbol_in_file_with_scope(tmp_path: Path) -> None:
    """Helper passes scope_node to engine for scoped rename."""
    path = tmp_path / "code.py"
    path.write_text(
        "def outer():\n    x = 1\n    return x\n\n"
        "def other():\n    x = 2\n    return x\n",
        encoding="utf-8",
    )
    result = _rename_symbol_in_file(path, "x", "value", scope_node="outer")
    assert "Renamed" in result
    content = path.read_text()
    assert "value = 1" in content
    assert "x = 2" in content
