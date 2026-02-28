"""Structured report models for CI refactor check output."""

from __future__ import annotations

from typing import assert_never

from pydantic import BaseModel, Field

from refactor_agent.schedule.models import (  # noqa: TC001 — used at runtime for isinstance
    CreateFileOp,
    MoveFileOp,
    MoveSymbolOp,
    OrganizeImportsOp,
    RefactorOperation,
    RemoveNodeOp,
    RenameOp,
)


class OperationSummary(BaseModel):
    """Single operation entry for the report (op type, file path, rationale)."""

    op: str = Field(description="Operation type (e.g. rename, move_symbol).")
    file_path: str = Field(
        description="Primary file path; for moves, source → target.",
    )
    rationale: str | None = Field(default=None, description="Optional rationale.")


def _op_file_path(op: RefactorOperation) -> str:
    """Return a single file_path string for report display."""
    if isinstance(op, (RenameOp, RemoveNodeOp, OrganizeImportsOp, CreateFileOp)):
        return op.file_path
    if isinstance(op, MoveSymbolOp):
        return f"{op.source_file} → {op.target_file}"
    if isinstance(op, MoveFileOp):
        return f"{op.source_path} → {op.target_path}"
    assert_never(op)


def operation_to_summary(op: RefactorOperation) -> OperationSummary:
    """Build an OperationSummary from a RefactorOperation."""
    return OperationSummary(
        op=op.op,
        file_path=_op_file_path(op),
        rationale=op.rationale,
    )


class PresetResult(BaseModel):
    """Result of running one preset: goal, count, auto_applied, operations."""

    preset_id: str = Field(description="Preset id that was run.")
    goal: str = Field(description="Planner goal for this preset.")
    operation_count: int = Field(description="Number of suggested operations.")
    auto_applied: bool = Field(
        description="True if executor was run and all ops applied.",
    )
    operations: list[OperationSummary] = Field(
        default_factory=list,
        description="List of operations (suggestions or applied).",
    )
    error: str | None = Field(
        default=None,
        description="Error message if planner or executor failed.",
    )


class CiReport(BaseModel):
    """Full CI run report: list of preset results and overall fail flag."""

    preset_results: list[PresetResult] = Field(
        default_factory=list,
        description="Results per preset.",
    )
    failed: bool = Field(
        description="True when there are suggestions that were not auto-applied.",
    )
