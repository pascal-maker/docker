from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class CollisionInfo:
    """Describes a name collision: existing definition that would be shadowed."""

    location: str  # e.g. "line 8"
    kind: str  # e.g. "FunctionDef", "ClassDef"


class RefactorEngine(Protocol):
    """Interface that any refactoring engine must satisfy."""

    def get_skeleton(self) -> str: ...
    def rename_symbol(
        self,
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str: ...
    def extract_function(
        self,
        scope_function: str,
        start_line: int,
        end_line: int,
        new_function_name: str,
    ) -> str: ...
    def check_name_collisions(
        self,
        new_name: str,
        scope_node: str | None = None,
    ) -> list[CollisionInfo]: ...
    def to_source(self) -> str: ...
