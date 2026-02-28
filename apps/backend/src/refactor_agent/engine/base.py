from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Self


@dataclass
class CollisionInfo:
    """Describes a name collision: existing definition that would be shadowed."""

    location: str  # e.g. "line 8"
    kind: str  # e.g. "FunctionDef", "ClassDef"


@dataclass
class ReferenceLocation:
    """A single reference to a symbol found across the project."""

    file_path: str
    line: int
    column: int
    text: str
    is_definition: bool


@dataclass
class DiagnosticInfo:
    """A TypeScript diagnostic (error / warning / suggestion)."""

    file_path: str
    line: int
    column: int
    message: str
    severity: str  # "error" | "warning" | "suggestion" | "message"
    code: int


class RefactorEngine(Protocol):
    """Async interface that any single-file refactoring engine must satisfy."""

    @property
    def language(self) -> str:
        """Language this engine operates on (e.g. 'python', 'typescript')."""
        ...

    async def __aenter__(self) -> Self:
        """Start any resources the engine needs (e.g. subprocess)."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Release resources."""
        ...

    async def get_skeleton(self) -> str:
        """Produce a text skeleton of the source."""
        ...

    async def rename_symbol(
        self,
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str:
        """Rename a symbol; return a summary or error string."""
        ...

    async def extract_function(
        self,
        scope_function: str,
        start_line: int,
        end_line: int,
        new_function_name: str,
    ) -> str:
        """Extract a block into a new function; return a summary or error."""
        ...

    async def check_name_collisions(
        self,
        new_name: str,
        scope_node: str | None = None,
    ) -> list[CollisionInfo]:
        """Return definitions that would collide with *new_name*."""
        ...

    async def to_source(self) -> str:
        """Return the current source text."""
        ...


class ProjectEngine(Protocol):
    """Async interface for project-level refactoring across multiple files.

    Unlike ``RefactorEngine`` (single-file), a ``ProjectEngine`` loads
    an entire workspace and operates across files.
    """

    @property
    def language(self) -> str:
        """Language this engine operates on."""
        ...

    async def __aenter__(self) -> Self:
        """Start the engine and load the project."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Release resources."""
        ...

    async def get_skeleton(self, file_path: str) -> str:
        """Produce a text skeleton of the given file."""
        ...

    async def rename_symbol(
        self,
        file_path: str,
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str:
        """Rename a symbol across the project; return a summary."""
        ...

    async def find_references(
        self,
        file_path: str,
        symbol_name: str,
    ) -> list[ReferenceLocation]:
        """Find all references to a symbol across the project."""
        ...

    async def remove_node(
        self,
        file_path: str,
        symbol_name: str,
        kind: str | None = None,
    ) -> str:
        """Remove a declaration by name; return a summary."""
        ...

    async def move_symbol(
        self,
        source_file: str,
        target_file: str,
        symbol_name: str,
    ) -> str:
        """Move a declaration to another file, updating imports."""
        ...

    async def format_file(self, file_path: str) -> str:
        """Format a file; return a summary."""
        ...

    async def organize_imports(self, file_path: str) -> str:
        """Organize imports in a file; return a summary."""
        ...

    async def get_diagnostics(
        self,
        file_path: str | None = None,
    ) -> list[DiagnosticInfo]:
        """Return diagnostics for a file or the whole project."""
        ...

    async def get_source(self, file_path: str) -> str:
        """Return the current source text of a project file."""
        ...

    async def get_changed_files(self) -> list[str]:
        """Return paths of files modified since project load."""
        ...
