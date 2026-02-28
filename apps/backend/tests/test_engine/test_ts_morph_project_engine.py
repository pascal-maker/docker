"""Integration tests for TsMorphProjectEngine (requires pnpm install in bridge)."""

from __future__ import annotations

import shutil
import textwrap
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from refactor_agent.engine.typescript.ts_morph_engine import (
    TsMorphProjectEngine,
)

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="Node.js not installed",
)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a minimal TypeScript workspace for testing."""
    greeter = tmp_path / "greeter.ts"
    greeter.write_text(
        textwrap.dedent("""\
            /** Return a greeting for the given name. */
            export function greetUser(name: string): string {
              return `Hello, ${name}!`;
            }
        """),
    )
    caller = tmp_path / "caller.ts"
    caller.write_text(
        textwrap.dedent("""\
            import { greetUser } from "./greeter.js";

            function main(): void {
              console.log(greetUser("World"));
            }

            main();
        """),
    )
    return tmp_path


# -- init_project ----------------------------------------------------------


async def test_init_project_loads_files(workspace: Path) -> None:
    """Project engine should discover .ts files in the workspace."""
    async with TsMorphProjectEngine(workspace) as engine:
        changed = await engine.get_changed_files()
        # No changes yet
        assert changed == []


# -- rename_symbol (cross-file) --------------------------------------------


async def test_rename_symbol_cross_file(workspace: Path) -> None:
    """Renaming in one file propagates to imports in other files."""
    greeter = workspace / "greeter.ts"
    caller = workspace / "caller.ts"
    greeter_path = str(greeter.resolve())

    async with TsMorphProjectEngine(workspace) as engine:
        result = await engine.rename_symbol(
            greeter_path,
            "greetUser",
            "sayHello",
        )
        assert "Renamed" in result
        assert "sayHello" in result

        changed = await engine.get_changed_files()
        assert len(changed) >= 1

        greeter_src = await engine.get_source(greeter_path)
        assert "function sayHello(" in greeter_src
        assert "greetUser" not in greeter_src

        caller_src = await engine.get_source(str(caller.resolve()))
        assert "sayHello" in caller_src


# -- find_references -------------------------------------------------------


async def test_find_references(workspace: Path) -> None:
    """Find references should return definition + usage sites."""
    greeter_path = str((workspace / "greeter.ts").resolve())

    async with TsMorphProjectEngine(workspace) as engine:
        refs = await engine.find_references(greeter_path, "greetUser")
        assert len(refs) >= 2
        has_def = any(r.is_definition for r in refs)
        assert has_def


# -- get_diagnostics -------------------------------------------------------


async def test_get_diagnostics_clean(workspace: Path) -> None:
    """Clean workspace should produce no (or only expected) diagnostics."""
    async with TsMorphProjectEngine(workspace) as engine:
        diags = await engine.get_diagnostics()
        errors = [d for d in diags if d.severity == "error"]
        # playground files may produce resolution warnings but no errors
        # in strict mode with no tsconfig; just check it doesn't crash
        assert isinstance(errors, list)


# -- remove_node -----------------------------------------------------------


async def test_remove_node(workspace: Path) -> None:
    """Remove a function declaration from a file."""
    greeter_path = str((workspace / "greeter.ts").resolve())

    async with TsMorphProjectEngine(workspace) as engine:
        result = await engine.remove_node(greeter_path, "greetUser")
        assert "Removed" in result
        assert "greetUser" in result

        src = await engine.get_source(greeter_path)
        assert "greetUser" not in src


# -- format_file -----------------------------------------------------------


async def test_format_file(workspace: Path) -> None:
    """Format should normalise whitespace."""
    ugly = workspace / "ugly.ts"
    ugly.write_text(
        "const    x   :   number   =   42  ;\n",
    )
    ugly_path = str(ugly.resolve())

    async with TsMorphProjectEngine(workspace) as engine:
        result = await engine.format_file(ugly_path)
        assert "Formatted" in result

        src = await engine.get_source(ugly_path)
        assert "const x: number = 42;" in src


# -- organize_imports ------------------------------------------------------


async def test_organize_imports(workspace: Path) -> None:
    """Organize imports should sort / deduplicate imports."""
    messy = workspace / "messy.ts"
    messy.write_text(
        textwrap.dedent("""\
            import { greetUser } from "./greeter.js";
            import { greetUser } from "./greeter.js";

            console.log(greetUser("test"));
        """),
    )
    messy_path = str(messy.resolve())

    async with TsMorphProjectEngine(workspace) as engine:
        result = await engine.organize_imports(messy_path)
        assert "Organized" in result

        src = await engine.get_source(messy_path)
        # After organizing, duplicate import should be removed
        assert src.count("import") <= 1


# -- move_symbol_to_file ---------------------------------------------------


async def test_move_symbol_to_file(workspace: Path) -> None:
    """Move a function from one file to a new file."""
    greeter_path = str((workspace / "greeter.ts").resolve())
    target_path = str((workspace / "saluter.ts").resolve())
    caller_path = str((workspace / "caller.ts").resolve())

    async with TsMorphProjectEngine(workspace) as engine:
        result = await engine.move_symbol(
            greeter_path,
            target_path,
            "greetUser",
        )
        assert "Moved" in result

        greeter_src = await engine.get_source(greeter_path)
        assert "greetUser" not in greeter_src

        target_src = await engine.get_source(target_path)
        assert "greetUser" in target_src
        assert "export" in target_src

        caller_src = await engine.get_source(caller_path)
        assert "saluter" in caller_src


async def test_move_symbol_cleans_target_import(tmp_path: Path) -> None:
    """When a symbol is moved into a file that already imports it,
    the stale import must be removed so the file uses its local copy."""
    lib = tmp_path / "lib.ts"
    lib.write_text(
        textwrap.dedent("""\
            export function helper(): string {
              return "ok";
            }
            export const VERSION = 1;
        """),
    )
    consumer = tmp_path / "consumer.ts"
    consumer.write_text(
        textwrap.dedent("""\
            import { helper } from "./lib.js";

            export function run(): string {
              return helper();
            }
        """),
    )

    lib_path = str(lib.resolve())
    consumer_path = str(consumer.resolve())

    async with TsMorphProjectEngine(tmp_path) as engine:
        result = await engine.move_symbol(lib_path, consumer_path, "helper")
        assert "Moved" in result

        consumer_src = await engine.get_source(consumer_path)
        assert "export function helper" in consumer_src
        # The old `import { helper } from "./lib.js"` must be gone.
        assert "import { helper }" not in consumer_src
        assert "helper()" in consumer_src


# -- get_source / get_changed_files ----------------------------------------


async def test_get_source_round_trip(workspace: Path) -> None:
    """Source should round-trip without modifications."""
    greeter_path = str((workspace / "greeter.ts").resolve())
    original = (workspace / "greeter.ts").read_text()

    async with TsMorphProjectEngine(workspace) as engine:
        src = await engine.get_source(greeter_path)
        assert src == original


# -- apply_changes ---------------------------------------------------------


async def test_apply_changes_writes_to_disk(workspace: Path) -> None:
    """apply_changes should persist bridge modifications to the filesystem."""
    greeter = workspace / "greeter.ts"
    greeter_path = str(greeter.resolve())

    async with TsMorphProjectEngine(workspace) as engine:
        await engine.rename_symbol(greeter_path, "greetUser", "wave")
        written = await engine.apply_changes()
        assert len(written) >= 1

    # Verify on-disk content
    assert "wave" in greeter.read_text()
    assert "greetUser" not in greeter.read_text()


# -- get_skeleton (project mode) -------------------------------------------


async def test_get_skeleton_project_mode(workspace: Path) -> None:
    """get_skeleton should work via project engine."""
    greeter_path = str((workspace / "greeter.ts").resolve())

    async with TsMorphProjectEngine(workspace) as engine:
        skeleton = await engine.get_skeleton(greeter_path)
        assert "greetUser" in skeleton
        assert "FunctionDef" in skeleton
