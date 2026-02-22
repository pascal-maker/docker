from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Self


@dataclass
class CollisionInfo:
    """Describes a name collision: existing definition that would be shadowed."""

    location: str  # e.g. "line 8"
    kind: str  # e.g. "FunctionDef", "ClassDef"


class RefactorEngine(Protocol):
    """Async interface that any refactoring engine must satisfy."""

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
