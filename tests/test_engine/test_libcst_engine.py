"""Tests for LibCSTEngine: skeleton, rename_symbol, to_source, formatting."""

from __future__ import annotations

from refactor_agent.engine.python.libcst_engine import LibCSTEngine


async def test_parse_and_to_source_round_trip() -> None:
    """Round-trip preserves source including comments and formatting."""
    source = '''# leading comment
def foo(x, y):
    """Docstring."""
    z = x + y  # inline
    return z
'''
    engine = LibCSTEngine(source)
    assert await engine.to_source() == source


async def test_get_skeleton_function_def() -> None:
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
    skeleton = await engine.get_skeleton()
    assert "FunctionDef 'calculate_tax'" in skeleton
    assert "FunctionDef 'calculate_total'" in skeleton
    assert "args:" in skeleton
    assert "calls:" in skeleton
    assert "calculate_tax" in skeleton
    assert "round" in skeleton


async def test_rename_symbol_file_wide() -> None:
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
    result = await engine.rename_symbol("calculate_tax", "compute_tax", None)
    assert "Renamed" in result
    assert "compute_tax" in result
    out = await engine.to_source()
    assert "def compute_tax(" in out
    assert "compute_tax(subtotal" in out
    assert "calculate_tax" not in out


async def test_rename_symbol_preserves_formatting_and_comments() -> None:
    """Rename does not strip comments or change formatting."""
    source = """# Tax helper
def calculate_tax(amount, rate):
    return round(amount * rate, 2)  # 2 decimals
"""
    engine = LibCSTEngine(source)
    await engine.rename_symbol("calculate_tax", "compute_tax", None)
    out = await engine.to_source()
    assert "# Tax helper" in out
    assert "# 2 decimals" in out
    assert "def compute_tax(" in out


async def test_check_name_collisions_no_collision() -> None:
    """check_name_collisions returns empty when new_name is unused."""
    source = "def foo(): pass"
    engine = LibCSTEngine(source)
    collisions = await engine.check_name_collisions("bar", None)
    assert collisions == []


async def test_check_name_collisions_existing_function() -> None:
    """check_name_collisions returns collision when new_name is already defined."""
    source = """
def main() -> None:
    pass

def greet(name: str) -> str:
    return f"Hello, {name}!"
"""
    engine = LibCSTEngine(source)
    collisions = await engine.check_name_collisions("main", None)
    assert len(collisions) == 1
    assert collisions[0].kind == "FunctionDef"
    assert "line" in collisions[0].location


async def test_check_name_collisions_scoped() -> None:
    """check_name_collisions respects scope_node and only reports in same scope."""
    source = """
def outer():
    x = 1
    return x

def other():
    x = 2
    return x
"""
    engine = LibCSTEngine(source)
    collisions = await engine.check_name_collisions("value", "outer")
    assert collisions == []
    collisions = await engine.check_name_collisions("x", None)
    assert len(collisions) >= 2
    collisions = await engine.check_name_collisions("outer", None)
    assert len(collisions) == 1
    assert collisions[0].kind == "FunctionDef"


async def test_check_name_collisions_assign() -> None:
    """check_name_collisions reports module-level Assign to the same name."""
    source = """
SENTINEL = 42

def get_sentinel():
    return SENTINEL
"""
    engine = LibCSTEngine(source)
    collisions = await engine.check_name_collisions("SENTINEL", None)
    assert any(c.kind == "Assign" for c in collisions)


async def test_rename_symbol_not_found() -> None:
    """Return error string when symbol is not found."""
    source = "def foo(): pass"
    engine = LibCSTEngine(source)
    result = await engine.rename_symbol("bar", "baz", None)
    assert "ERROR" in result
    assert "not found" in result


async def test_rename_symbol_scoped() -> None:
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
    result = await engine.rename_symbol("x", "value", "outer")
    assert "Renamed" in result
    out = await engine.to_source()
    assert "value = 1" in out
    assert "return value" in out
    assert "x = 2" in out
    assert "return x" in out


async def test_extract_function_stub_returns_error() -> None:
    """LibCSTEngine.extract_function returns a clear error."""
    engine = LibCSTEngine("def f(): pass")
    result = await engine.extract_function("f", 1, 1, "g")
    assert "ERROR" in result
    assert "not yet implemented" in result or "extract_function" in result
