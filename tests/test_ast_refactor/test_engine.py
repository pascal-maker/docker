"""Tests for LibCSTEngine: skeleton, rename_symbol, to_source, formatting."""

from __future__ import annotations

from document_structuring_agent.ast_refactor.engine import LibCSTEngine


def test_parse_and_to_source_round_trip() -> None:
    """Round-trip preserves source including comments and formatting."""
    source = '''# leading comment
def foo(x, y):
    """Docstring."""
    z = x + y  # inline
    return z
'''
    engine = LibCSTEngine(source)
    assert engine.to_source() == source


def test_get_skeleton_function_def() -> None:
    """Skeleton includes function name, args, calls, line numbers."""
    source = """
def calculate_tax(amount, rate):
    return round(amount * rate, 2)

def calculate_total(price, quantity, tax_rate):
    subtotal = price * quantity
    tax = calculate_tax(subtotal, tax_rate)
    return subtotal + tax
"""
    engine = LibCSTEngine(source)
    skeleton = engine.get_skeleton()
    assert "FunctionDef 'calculate_tax'" in skeleton
    assert "FunctionDef 'calculate_total'" in skeleton
    assert "args:" in skeleton
    assert "calls:" in skeleton
    assert "calculate_tax" in skeleton
    assert "round" in skeleton


def test_rename_symbol_file_wide() -> None:
    """Rename function and all call sites file-wide."""
    source = """
def calculate_tax(amount, rate):
    return round(amount * rate, 2)

def calculate_total(price, quantity, tax_rate):
    subtotal = price * quantity
    tax = calculate_tax(subtotal, tax_rate)
    return subtotal + tax
"""
    engine = LibCSTEngine(source)
    result = engine.rename_symbol("calculate_tax", "compute_tax", None)
    assert "Renamed" in result
    assert "compute_tax" in result
    out = engine.to_source()
    assert "def compute_tax(" in out
    assert "compute_tax(subtotal" in out
    assert "calculate_tax" not in out


def test_rename_symbol_preserves_formatting_and_comments() -> None:
    """Rename does not strip comments or change formatting."""
    source = """# Tax helper
def calculate_tax(amount, rate):
    return round(amount * rate, 2)  # 2 decimals
"""
    engine = LibCSTEngine(source)
    engine.rename_symbol("calculate_tax", "compute_tax", None)
    out = engine.to_source()
    assert "# Tax helper" in out
    assert "# 2 decimals" in out
    assert "def compute_tax(" in out


def test_rename_symbol_not_found() -> None:
    """Return error string when symbol is not found."""
    source = "def foo(): pass"
    engine = LibCSTEngine(source)
    result = engine.rename_symbol("bar", "baz", None)
    assert "ERROR" in result
    assert "not found" in result


def test_rename_symbol_scoped() -> None:
    """Rename only within a given function scope when scope_node is set."""
    source = """
def outer():
    x = 1
    return x

def other():
    x = 2
    return x
"""
    engine = LibCSTEngine(source)
    result = engine.rename_symbol("x", "value", "outer")
    assert "Renamed" in result
    out = engine.to_source()
    assert "value = 1" in out
    assert "return value" in out
    # other() should still have x
    assert "x = 2" in out
    assert "return x" in out


def test_extract_function_stub_returns_error() -> None:
    """LibCSTEngine.extract_function returns a clear error."""
    engine = LibCSTEngine("def f(): pass")
    result = engine.extract_function("f", 1, 1, "g")
    assert "ERROR" in result
    assert "not yet implemented" in result or "extract_function" in result
