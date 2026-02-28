"""Structural validator: ScopeSpec check and dry-run simulation."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 — Path used at runtime in workspace /
from typing import assert_never

from pydantic import BaseModel

from refactor_agent.orchestrator.deps import OrchestratorDeps  # noqa: TC001 — runtime
from refactor_agent.schedule.models import (  # noqa: TC001 — isinstance checks at runtime
    CreateFileOp,
    MoveFileOp,
    MoveSymbolOp,
    OrganizeImportsOp,
    RefactorOperation,
    RefactorSchedule,
    RemoveNodeOp,
    RenameOp,
    ScopeSpec,
)


class ValidationResult(BaseModel):
    """Result of schedule validation."""

    approved: bool
    reason: str | None = None


def _paths_touched_by_op(op: RefactorOperation) -> set[str]:
    """Return the set of file paths modified by this operation."""
    match op.op:
        case "rename":
            return {op.file_path}
        case "move_symbol":
            return {op.source_file, op.target_file}
        case "move_file":
            return {op.source_path, op.target_path}
        case "remove_node" | "organize_imports":
            return {op.file_path}
        case "create_file":
            return {op.file_path}


def _all_paths_touched(schedule: RefactorSchedule) -> set[str]:
    """Return all file paths that would be modified by the schedule."""
    out: set[str] = set()
    for op in schedule.operations:
        out |= _paths_touched_by_op(op)
    return out


def _op_type(op: RefactorOperation) -> str:
    """Return the operation type string."""
    return op.op


def _check_scope_spec(
    schedule: RefactorSchedule,
    scope_spec: ScopeSpec,
) -> str | None:
    """Check schedule against ScopeSpec. Return error message or None."""
    touched = _all_paths_touched(schedule)
    op_types = {_op_type(op) for op in schedule.operations}

    if scope_spec.affected_files:
        extra = touched - set(scope_spec.affected_files)
        if extra:
            return (
                f"Schedule touches files outside scope: {sorted(extra)}. "
                f"Allowed: {scope_spec.affected_files}"
            )

    if scope_spec.forbidden_op_types:
        forbidden_used = op_types & set(scope_spec.forbidden_op_types)
        if forbidden_used:
            return (
                f"Forbidden op types used: {sorted(forbidden_used)}. "
                f"Forbidden: {scope_spec.forbidden_op_types}"
            )

    if scope_spec.allowed_op_types:
        disallowed = op_types - set(scope_spec.allowed_op_types)
        if disallowed:
            return (
                f"Op types not in allowed list: {sorted(disallowed)}. "
                f"Allowed: {scope_spec.allowed_op_types}"
            )

    return None


def _check_move_file(op: MoveFileOp, workspace: Path) -> str | None:
    """Validate move_file paths."""
    src = workspace / op.source_path
    tgt = workspace / op.target_path
    if not src.exists():
        return f"move_file source does not exist: {op.source_path}"
    if src.resolve() != tgt.resolve() and tgt.exists() and tgt.is_file():
        return f"move_file target already exists: {op.target_path}"
    return None


def _check_op_paths(op: RefactorOperation, workspace: Path) -> str | None:  # noqa: PLR0911
    """Validate paths for a single operation."""
    if isinstance(op, MoveFileOp):
        return _check_move_file(op, workspace)
    if isinstance(op, RenameOp):
        return (
            None
            if (workspace / op.file_path).exists()
            else f"rename file does not exist: {op.file_path}"
        )
    if isinstance(op, MoveSymbolOp):
        return (
            None
            if (workspace / op.source_file).exists()
            else f"move_symbol source does not exist: {op.source_file}"
        )
    if isinstance(op, RemoveNodeOp):
        return (
            None
            if (workspace / op.file_path).exists()
            else f"remove_node file does not exist: {op.file_path}"
        )
    if isinstance(op, OrganizeImportsOp):
        return (
            None
            if (workspace / op.file_path).exists()
            else f"organize_imports file does not exist: {op.file_path}"
        )
    if isinstance(op, CreateFileOp):
        return (
            None
            if not (workspace / op.file_path).exists()
            else f"create_file target already exists: {op.file_path}"
        )
    assert_never(op)


def _check_paths(schedule: RefactorSchedule, workspace: Path) -> str | None:
    """Validate paths: sources exist, targets valid. Return error or None."""
    for op in schedule.operations:
        err = _check_op_paths(op, workspace)
        if err:
            return err
    return None


def validate_schedule(
    schedule: RefactorSchedule,
    scope_spec: ScopeSpec,
    deps: OrchestratorDeps,
) -> ValidationResult:
    """Validate schedule against ScopeSpec and dry-run path checks.

    ScopeSpec: affected_files, allowed_op_types, forbidden_op_types.
    Dry-run: source paths exist, target paths valid.
    Cycle detection in import graph is deferred to a future iteration.
    """
    scope_err = _check_scope_spec(schedule, scope_spec)
    if scope_err:
        return ValidationResult(approved=False, reason=scope_err)

    path_err = _check_paths(schedule, deps.workspace)
    if path_err:
        return ValidationResult(approved=False, reason=path_err)

    return ValidationResult(approved=True, reason=None)
