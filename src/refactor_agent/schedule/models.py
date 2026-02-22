"""Pydantic models for RefactorSchedule and operation variants."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class _BaseOp(BaseModel):
    """Common fields for all refactor operations."""

    id: str | None = None
    depends_on: list[str] = Field(default_factory=list, alias="dependsOn")
    rationale: str | None = None

    model_config = {"populate_by_name": True}


class RenameOp(_BaseOp):
    """Rename a symbol in a file (and optionally across the project)."""

    op: Literal["rename"] = "rename"
    file_path: str
    old_name: str
    new_name: str
    scope_node: str | None = None


class MoveSymbolOp(_BaseOp):
    """Move a symbol from one file to another."""

    op: Literal["move_symbol"] = "move_symbol"
    source_file: str
    target_file: str
    symbol_name: str


class MoveFileOp(_BaseOp):
    """Move a file to a new path."""

    op: Literal["move_file"] = "move_file"
    source_path: str
    target_path: str


class RemoveNodeOp(_BaseOp):
    """Remove a declaration (function, class, etc.) from a file."""

    op: Literal["remove_node"] = "remove_node"
    file_path: str
    symbol_name: str
    kind: str | None = None


class OrganizeImportsOp(_BaseOp):
    """Organize imports in a file."""

    op: Literal["organize_imports"] = "organize_imports"
    file_path: str


class CreateFileOp(_BaseOp):
    """Create a new file with given content (or placeholder)."""

    op: Literal["create_file"] = "create_file"
    file_path: str
    content: str = ""


RefactorOperation = Annotated[
    RenameOp
    | MoveSymbolOp
    | MoveFileOp
    | RemoveNodeOp
    | OrganizeImportsOp
    | CreateFileOp,
    Field(discriminator="op"),
]


class RefactorSchedule(BaseModel):
    """A planned set of refactor operations with an optional execution order."""

    model_config = {"extra": "forbid"}

    goal: str = Field(description="Short description of the refactor goal.")
    operations: list[RefactorOperation] = Field(
        default_factory=list,
        description="List of refactor operations; use [] if none. Always include this key.",
        min_length=0,
    )
