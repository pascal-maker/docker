"""TypeScript refactoring engines using ts-morph via a subprocess bridge."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from refactor_agent.engine.base import (
    CollisionInfo,
    DiagnosticInfo,
    ReferenceLocation,
)
from refactor_agent.engine.subprocess_engine import SubprocessEngine

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)

_BRIDGE_DIR = Path(__file__).resolve().parent / "bridge"
_BRIDGE_ENTRY = _BRIDGE_DIR / "src" / "index.ts"
_TSX_BIN = _BRIDGE_DIR / "node_modules" / ".bin" / "tsx"


# ---------------------------------------------------------------------------
# Single-file engine (backward compat)
# ---------------------------------------------------------------------------


class TsMorphEngine(SubprocessEngine):
    """TypeScript engine that delegates to a ts-morph JSON-RPC bridge.

    Operates on a single in-memory source file.  Must be used as an
    async context manager::

        async with TsMorphEngine(source) as engine:
            result = await engine.rename_symbol("foo", "bar")
            new_src = await engine.to_source()
    """

    language: str = "typescript"

    def __init__(self, source: str) -> None:
        """Store the source to be sent on bridge init."""
        super().__init__()
        self._source = source

    def _command(self) -> list[str]:
        """Return command to start the ts-morph bridge process."""
        return [str(_TSX_BIN), str(_BRIDGE_ENTRY)]

    async def __aenter__(self) -> TsMorphEngine:
        """Start the bridge and initialize it with the source."""
        await super().__aenter__()
        await self._call("init", {"source": self._source})
        return self

    async def get_skeleton(self) -> str:
        """Return a text skeleton of the TypeScript source."""
        result = await self._call("get_skeleton", {})
        return str(result)

    async def rename_symbol(
        self,
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str:
        """Rename a symbol in the TypeScript source.

        Args:
            old_name: Current symbol name.
            new_name: Desired new name.
            scope_node: Optional function/class to restrict scope.
        """
        params: dict[str, Any] = {
            "old_name": old_name,
            "new_name": new_name,
        }
        if scope_node is not None:
            params["scope_node"] = scope_node
        result = await self._call("rename_symbol", params)
        if isinstance(result, dict):
            return str(result.get("summary", result))
        return str(result)

    async def extract_function(
        self,
        _scope_function: str,
        _start_line: int,
        _end_line: int,
        _new_function_name: str,
    ) -> str:
        """Not implemented for TypeScript."""
        return (
            "ERROR: extract_function is not yet implemented for TypeScript; "
            "only rename_symbol is supported."
        )

    async def check_name_collisions(
        self,
        new_name: str,
        scope_node: str | None = None,
    ) -> list[CollisionInfo]:
        """Check for existing definitions that would conflict with new_name."""
        params: dict[str, Any] = {"new_name": new_name}
        if scope_node is not None:
            params["scope_node"] = scope_node
        result = await self._call("check_name_collisions", params)
        if not isinstance(result, list):
            return []
        return [
            CollisionInfo(
                location=item.get("location", "unknown"),
                kind=item.get("kind", "unknown"),
            )
            for item in result
            if isinstance(item, dict)
        ]

    async def to_source(self) -> str:
        """Return the current TypeScript source text."""
        result = await self._call("to_source", {})
        return str(result)


# ---------------------------------------------------------------------------
# Project-level engine
# ---------------------------------------------------------------------------


class TsMorphProjectEngine(SubprocessEngine):
    """TypeScript project engine loading a real workspace via ts-morph.

    Loads all ``.ts`` / ``.tsx`` files from a workspace directory,
    enabling cross-file operations (rename, find references, move
    symbol, diagnostics, etc.).

    Must be used as an async context manager::

        async with TsMorphProjectEngine(workspace) as engine:
            result = await engine.rename_symbol(
                "greeter.ts",
                "greetUser",
                "sayHello",
            )
            changed = await engine.get_changed_files()
    """

    language: str = "typescript"

    def __init__(
        self,
        workspace: Path,
        tsconfig_path: Path | None = None,
    ) -> None:
        """Configure the project engine.

        Args:
            workspace: Root directory of the TypeScript project.
            tsconfig_path: Optional explicit tsconfig.json path.
                If omitted, the bridge auto-detects or uses defaults.
        """
        super().__init__()
        self._workspace = workspace.resolve()
        self._tsconfig = tsconfig_path

    def _command(self) -> list[str]:
        """Return command to start the ts-morph bridge process."""
        return [str(_TSX_BIN), str(_BRIDGE_ENTRY)]

    async def __aenter__(self) -> TsMorphProjectEngine:
        """Start the bridge and load the project."""
        await super().__aenter__()
        params: dict[str, Any] = {"root_dir": str(self._workspace)}
        if self._tsconfig is not None:
            params["tsconfig_path"] = str(self._tsconfig)
        result = await self._call("init_project", params)
        files = result.get("files", []) if isinstance(result, dict) else []
        logger.debug("Loaded %d files from %s", len(files), self._workspace)
        return self

    # -- Analysis ----------------------------------------------------------

    async def get_skeleton(self, file_path: str) -> str:
        """Return a text skeleton of the given project file."""
        result = await self._call(
            "get_skeleton",
            {"file_path": file_path},
        )
        return str(result)

    async def find_references(
        self,
        file_path: str,
        symbol_name: str,
    ) -> list[ReferenceLocation]:
        """Find all references to a symbol across the project."""
        result = await self._call(
            "find_references",
            {"file_path": file_path, "symbol_name": symbol_name},
        )
        if not isinstance(result, list):
            return []
        return [
            ReferenceLocation(
                file_path=item.get("file", ""),
                line=item.get("line", 0),
                column=item.get("column", 0),
                text=item.get("text", ""),
                is_definition=item.get("is_definition", False),
            )
            for item in result
            if isinstance(item, dict)
        ]

    async def get_diagnostics(
        self,
        file_path: str | None = None,
    ) -> list[DiagnosticInfo]:
        """Return TypeScript diagnostics for a file or whole project."""
        params: dict[str, Any] = {}
        if file_path is not None:
            params["file_path"] = file_path
        result = await self._call("get_diagnostics", params)
        if not isinstance(result, list):
            return []
        return [
            DiagnosticInfo(
                file_path=item.get("file", ""),
                line=item.get("line", 0),
                column=item.get("column", 0),
                message=item.get("message", ""),
                severity=item.get("severity", "error"),
                code=item.get("code", 0),
            )
            for item in result
            if isinstance(item, dict)
        ]

    # -- Mutations ---------------------------------------------------------

    async def rename_symbol(
        self,
        file_path: str,
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str:
        """Rename a symbol across the project.

        Args:
            file_path: File containing the symbol declaration.
            old_name: Current symbol name.
            new_name: Desired new name.
            scope_node: Optional function/class to restrict scope.
        """
        params: dict[str, Any] = {
            "file_path": file_path,
            "old_name": old_name,
            "new_name": new_name,
        }
        if scope_node is not None:
            params["scope_node"] = scope_node
        result = await self._call("rename_symbol", params)
        return _extract_summary(result)

    async def remove_node(
        self,
        file_path: str,
        symbol_name: str,
        kind: str | None = None,
    ) -> str:
        """Remove a declaration from a project file.

        Args:
            file_path: File containing the declaration.
            symbol_name: Name of the declaration to remove.
            kind: Optional kind filter (function, class, interface, etc.).
        """
        params: dict[str, Any] = {
            "file_path": file_path,
            "symbol_name": symbol_name,
        }
        if kind is not None:
            params["kind"] = kind
        result = await self._call("remove_node", params)
        return _extract_summary(result)

    async def move_symbol(
        self,
        source_file: str,
        target_file: str,
        symbol_name: str,
    ) -> str:
        """Move a declaration to another file, updating imports.

        Args:
            source_file: Current file containing the symbol.
            target_file: Destination file (created if it doesn't exist).
            symbol_name: Name of the declaration to move.
        """
        result = await self._call(
            "move_symbol_to_file",
            {
                "source_file": source_file,
                "target_file": target_file,
                "symbol_name": symbol_name,
            },
        )
        return _extract_summary(result)

    async def format_file(self, file_path: str) -> str:
        """Format a project file using the TypeScript formatter."""
        result = await self._call(
            "format_file",
            {"file_path": file_path},
        )
        return _extract_summary(result)

    async def organize_imports(self, file_path: str) -> str:
        """Organize imports in a project file (sort, remove unused)."""
        result = await self._call(
            "organize_imports",
            {"file_path": file_path},
        )
        return _extract_summary(result)

    # -- Source retrieval ---------------------------------------------------

    async def get_source(self, file_path: str) -> str:
        """Return the current source text of a project file."""
        result = await self._call(
            "get_source",
            {"file_path": file_path},
        )
        return str(result)

    async def get_changed_files(self) -> list[str]:
        """Return paths of files modified since project load."""
        result = await self._call("get_changed_files", {})
        if isinstance(result, dict):
            files = result.get("files", [])
            if isinstance(files, list):
                return [str(f) for f in files]
        return []

    async def apply_changes(self) -> list[str]:
        """Write all changed files back to disk.

        Returns the list of file paths that were written.
        """
        changed = await self.get_changed_files()
        written: list[str] = []
        for fp in changed:
            source = await self.get_source(fp)
            await asyncio.to_thread(
                Path(fp).write_text,
                source,
                encoding="utf-8",
            )
            written.append(fp)
        return written


def _extract_summary(result: object) -> str:
    """Pull a summary string from a bridge response dict."""
    if isinstance(result, dict):
        return str(result.get("summary", result))
    return str(result)
