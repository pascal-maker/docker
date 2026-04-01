"""TypeScript refactoring engines using ts-morph via a subprocess bridge."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import override

from refactor_agent.engine.base import (
    CollisionInfo,
    DiagnosticInfo,
    ReferenceLocation,
)
from refactor_agent.engine.logger import logger
from refactor_agent.engine.subprocess_engine import (
    JsonRpcParams,
    SubprocessEngine,
)
from refactor_agent.migration.models import ComponentInfo  # noqa: TC001 — runtime Pydantic model construction

_REPO_ROOT = Path(__file__).resolve().parents[6]
_BRIDGE_DIR = _REPO_ROOT / "packages" / "ts-morph-bridge"
_BRIDGE_ENTRY = _BRIDGE_DIR / "src" / "index.ts"


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

    @override
    def _command(self) -> list[str]:
        """Return command to start the ts-morph bridge process (pnpm exec from bridge dir)."""
        return ["pnpm", "exec", "tsx", str(_BRIDGE_ENTRY)]

    @override
    def _cwd(self) -> Path | None:
        """Run bridge from its directory so pnpm resolves tsx."""
        return _BRIDGE_DIR

    @override
    async def __aenter__(self) -> TsMorphEngine:
        """Start the bridge and initialize it with the source."""
        await super().__aenter__()
        await self._call(
            "init",
            JsonRpcParams.model_validate({"source": self._source}),
        )
        return self

    async def get_skeleton(self) -> str:
        """Return a text skeleton of the TypeScript source."""
        result = await self._call("get_skeleton", JsonRpcParams())
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
        result = await self._call(
            "rename_symbol",
            JsonRpcParams.model_validate(
                {
                    "old_name": old_name,
                    "new_name": new_name,
                    **({"scope_node": scope_node} if scope_node is not None else {}),
                }
            ),
        )
        if isinstance(result, dict):
            return str(result.get("summary", result))
        return str(result)

    async def extract_function(
        self,
        scope_function: str,
        start_line: int,
        end_line: int,
        new_function_name: str,
    ) -> str:
        """Not implemented for TypeScript."""
        _ = (
            scope_function,
            start_line,
            end_line,
            new_function_name,
        )  # Protocol signature; unused in stub
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
        result = await self._call(
            "check_name_collisions",
            JsonRpcParams.model_validate(
                {
                    "new_name": new_name,
                    **({"scope_node": scope_node} if scope_node is not None else {}),
                }
            ),
        )
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
        result = await self._call("to_source", JsonRpcParams())
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

    @override
    def _command(self) -> list[str]:
        """Return command to start the ts-morph bridge process (pnpm exec from bridge dir)."""
        return ["pnpm", "exec", "tsx", str(_BRIDGE_ENTRY)]

    @override
    def _cwd(self) -> Path | None:
        """Run bridge from its directory so pnpm resolves tsx."""
        return _BRIDGE_DIR

    async def __aenter__(self) -> TsMorphProjectEngine:
        """Start the bridge and load the project."""
        await super().__aenter__()
        result = await self._call(
            "init_project",
            JsonRpcParams.model_validate(
                {
                    "root_dir": str(self._workspace),
                    **(
                        {"tsconfig_path": str(self._tsconfig)}
                        if self._tsconfig is not None
                        else {}
                    ),
                }
            ),
        )
        files = result.get("files", []) if isinstance(result, dict) else []
        logger.debug("Loaded files", count=len(files), workspace=str(self._workspace))
        return self

    # -- Analysis ----------------------------------------------------------

    async def get_skeleton(self, file_path: str) -> str:
        """Return a text skeleton of the given project file."""
        result = await self._call(
            "get_skeleton",
            JsonRpcParams.model_validate({"file_path": file_path}),
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
            JsonRpcParams.model_validate(
                {
                    "file_path": file_path,
                    "symbol_name": symbol_name,
                }
            ),
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
        result = await self._call(
            "get_diagnostics",
            JsonRpcParams.model_validate(
                {"file_path": file_path} if file_path is not None else {}
            ),
        )
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
        params_dict = {
            "file_path": file_path,
            "old_name": old_name,
            "new_name": new_name,
        }
        if scope_node is not None:
            params_dict["scope_node"] = scope_node
        result = await self._call(
            "rename_symbol",
            JsonRpcParams.model_validate(params_dict),
        )
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
        params_dict = {
            "file_path": file_path,
            "symbol_name": symbol_name,
        }
        if kind is not None:
            params_dict["kind"] = kind
        result = await self._call(
            "remove_node",
            JsonRpcParams.model_validate(params_dict),
        )
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
            JsonRpcParams.model_validate(
                {
                    "source_file": source_file,
                    "target_file": target_file,
                    "symbol_name": symbol_name,
                }
            ),
        )
        return _extract_summary(result)

    async def create_file(self, file_path: str, content: str = "") -> str:
        """Create a new source file in the project.

        Args:
            file_path: Absolute or workspace-relative path for the new file.
            content: Initial file content (empty string creates a blank file).
        """
        result = await self._call(
            "create_file",
            JsonRpcParams.model_validate(
                {
                    "file_path": file_path,
                    "content": content,
                }
            ),
        )
        return _extract_summary(result)

    async def move_file(self, source_path: str, target_path: str) -> str:
        """Move a source file to a new path, updating all imports.

        Args:
            source_path: Current file path.
            target_path: Desired new file path.
        """
        result = await self._call(
            "move_file",
            JsonRpcParams.model_validate(
                {
                    "source_path": source_path,
                    "target_path": target_path,
                }
            ),
        )
        return _extract_summary(result)

    async def format_file(self, file_path: str) -> str:
        """Format a project file using the TypeScript formatter."""
        result = await self._call(
            "format_file",
            JsonRpcParams.model_validate({"file_path": file_path}),
        )
        return _extract_summary(result)

    async def organize_imports(self, file_path: str) -> str:
        """Organize imports in a project file (sort, remove unused)."""
        result = await self._call(
            "organize_imports",
            JsonRpcParams.model_validate({"file_path": file_path}),
        )
        return _extract_summary(result)

    # -- Source retrieval ---------------------------------------------------

    async def get_source(self, file_path: str) -> str:
        """Return the current source text of a project file."""
        result = await self._call(
            "get_source",
            JsonRpcParams.model_validate({"file_path": file_path}),
        )
        return str(result)

    async def get_changed_files(self) -> list[str]:
        """Return paths of files modified since project load."""
        result = await self._call("get_changed_files", JsonRpcParams())
        if isinstance(result, dict):
            files = result.get("files", [])
            if isinstance(files, list):
                return [str(f) for f in files]
        return []

    async def list_react_class_components(self) -> list[ComponentInfo]:
        """Return all React class components found in the project.

        Returns:
            List of ComponentInfo for each class extending React.Component
            or React.PureComponent found across all project source files.
        """
        result = await self._call(
            "list_react_class_components",
            JsonRpcParams(),
        )
        if not isinstance(result, list):
            return []
        return [
            ComponentInfo(
                file_path=item.get("file_path", ""),
                component_name=item.get("component_name", ""),
                lifecycle_methods=item.get("lifecycle_methods", []),
                has_state=bool(item.get("has_state", False)),
                has_refs=bool(item.get("has_refs", False)),
                line=int(item.get("line", 0)),
            )
            for item in result
            if isinstance(item, dict) and item.get("component_name")
        ]

    async def apply_changes(self) -> list[str]:
        """Write all changed files back to disk.

        Creates parent directories for new paths so that move_symbol targets
        (e.g. src/orders/shared/OrderId.ts) persist; otherwise a later op
        that re-inits the project from disk would not see the file and
        getSourceFile would throw "File not found in project".
        Resolves relative paths against the workspace so files are always
        written under the project root (avoids writing to cwd by mistake).
        Returns the list of file paths that were written.
        """
        changed = await self.get_changed_files()
        written: list[str] = []
        workspace_resolved = self._workspace.resolve()
        for raw_fp in changed:
            fp = str(raw_fp).strip()
            path = Path(fp)
            if not path.is_absolute():
                path = (self._workspace / path).resolve()
            else:
                path = path.resolve()
            try:
                path.relative_to(workspace_resolved)
            except ValueError:
                continue
            source = await self.get_source(fp)
            await asyncio.to_thread(
                path.parent.mkdir,
                parents=True,
                exist_ok=True,
            )
            await asyncio.to_thread(
                path.write_text,
                source,
                encoding="utf-8",
            )
            written.append(str(path))
        return written


def _extract_summary(result: object) -> str:
    """Pull a summary string from a bridge response dict."""
    if isinstance(result, dict):
        return str(result.get("summary", result))
    return str(result)
