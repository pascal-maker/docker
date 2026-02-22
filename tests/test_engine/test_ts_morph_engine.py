"""Integration tests for TsMorphEngine (requires npm install in bridge dir)."""

from __future__ import annotations

import shutil

import pytest

from refactor_agent.engine.typescript.ts_morph_engine import TsMorphEngine

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="Node.js not installed",
)


async def test_rename_symbol_file_wide() -> None:
    """Rename propagates to both declaration and call site."""
    source = (
        "function greetUser(name: string): string {\n"
        '  return "Hello, " + name;\n'
        "}\n"
        'const msg = greetUser("world");\n'
    )
    async with TsMorphEngine(source) as engine:
        result = await engine.rename_symbol("greetUser", "sayHello")
        assert "Renamed" in result
        assert "sayHello" in result

        out = await engine.to_source()
        assert "function sayHello(" in out
        assert 'sayHello("world")' in out
        assert "greetUser" not in out


async def test_get_skeleton() -> None:
    """Skeleton includes function name, args."""
    source = (
        "function calculateTax(amount: number, rate: number): number {\n"
        "  return Math.round(amount * rate * 100) / 100;\n"
        "}\n"
    )
    async with TsMorphEngine(source) as engine:
        skeleton = await engine.get_skeleton()
        assert "FunctionDef 'calculateTax'" in skeleton
        assert "args:" in skeleton
        assert "amount" in skeleton
        assert "rate" in skeleton


async def test_rename_symbol_not_found() -> None:
    """Return error string when symbol is not found."""
    source = "function foo(): void {}\n"
    async with TsMorphEngine(source) as engine:
        result = await engine.rename_symbol("bar", "baz")
        assert "ERROR" in result
        assert "not found" in result


async def test_to_source_round_trip() -> None:
    """Source round-trips without change when no mutations are done."""
    source = "const x: number = 42;\n"
    async with TsMorphEngine(source) as engine:
        out = await engine.to_source()
        assert out == source


async def test_check_name_collisions() -> None:
    """Collision detected when new_name is already defined."""
    source = "function main(): void {}\nfunction greet(): string { return 'hi'; }\n"
    async with TsMorphEngine(source) as engine:
        collisions = await engine.check_name_collisions("main")
        assert len(collisions) == 1
        assert collisions[0].kind == "FunctionDef"
        assert "line" in collisions[0].location


async def test_check_name_collisions_no_collision() -> None:
    """No collision when new_name is unused."""
    source = "function foo(): void {}\n"
    async with TsMorphEngine(source) as engine:
        collisions = await engine.check_name_collisions("bar")
        assert collisions == []


async def test_extract_function_returns_error() -> None:
    """extract_function is not implemented for TypeScript."""
    source = "function f(): void {}\n"
    async with TsMorphEngine(source) as engine:
        result = await engine.extract_function("f", 1, 1, "g")
        assert "ERROR" in result
        assert "not yet implemented" in result
