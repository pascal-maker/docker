"""Tests for structural validator."""

from __future__ import annotations

from pathlib import Path

from refactor_agent.agentic.validator import (
    ValidationResult,
    validate_schedule,
)
from refactor_agent.orchestrator.deps import OrchestratorDeps
from refactor_agent.schedule.models import (
    MoveFileOp,
    RefactorSchedule,
    RenameOp,
    ScopeSpec,
)


def _deps(workspace: Path) -> OrchestratorDeps:
    return OrchestratorDeps(
        language="typescript",
        workspace=workspace,
        mode="Auto",
        file_ext="*.ts",
    )


def test_validate_schedule_approved_when_scope_empty(tmp_path: Path) -> None:
    """Empty ScopeSpec approves any schedule with valid paths."""
    (tmp_path / "a.ts").write_text("export const x = 1;")
    schedule = RefactorSchedule(
        goal="rename",
        operations=[RenameOp(file_path="a.ts", old_name="x", new_name="y")],
    )
    result = validate_schedule(
        schedule,
        ScopeSpec(),
        _deps(tmp_path),
    )
    assert result.approved is True
    assert result.reason is None


def test_validate_schedule_rejects_file_outside_scope(tmp_path: Path) -> None:
    """Schedule touching file not in affected_files is rejected."""
    (tmp_path / "a.ts").write_text("export const x = 1;")
    (tmp_path / "b.ts").write_text("export const y = 2;")
    schedule = RefactorSchedule(
        goal="rename both",
        operations=[
            RenameOp(file_path="a.ts", old_name="x", new_name="x2"),
            RenameOp(file_path="b.ts", old_name="y", new_name="y2"),
        ],
    )
    scope = ScopeSpec(affected_files=["a.ts"])
    result = validate_schedule(schedule, scope, _deps(tmp_path))
    assert result.approved is False
    assert "b.ts" in (result.reason or "")
    assert "outside scope" in (result.reason or "")


def test_validate_schedule_rejects_forbidden_op_type(tmp_path: Path) -> None:
    """Schedule using forbidden op type is rejected."""
    (tmp_path / "a.ts").write_text("export const x = 1;")
    schedule = RefactorSchedule(
        goal="rename",
        operations=[RenameOp(file_path="a.ts", old_name="x", new_name="y")],
    )
    scope = ScopeSpec(
        affected_files=["a.ts"],
        forbidden_op_types=["rename"],
    )
    result = validate_schedule(schedule, scope, _deps(tmp_path))
    assert result.approved is False
    assert "rename" in (result.reason or "")
    assert "Forbidden" in (result.reason or "")


def test_validate_schedule_rejects_disallowed_op_type(tmp_path: Path) -> None:
    """Schedule using op type not in allowed list is rejected."""
    (tmp_path / "a.ts").write_text("export const x = 1;")
    schedule = RefactorSchedule(
        goal="rename",
        operations=[RenameOp(file_path="a.ts", old_name="x", new_name="y")],
    )
    scope = ScopeSpec(
        affected_files=["a.ts"],
        allowed_op_types=["move_file", "organize_imports"],
    )
    result = validate_schedule(schedule, scope, _deps(tmp_path))
    assert result.approved is False
    assert "rename" in (result.reason or "")


def test_validate_schedule_rejects_move_file_missing_source(tmp_path: Path) -> None:
    """move_file with non-existent source is rejected."""
    schedule = RefactorSchedule(
        goal="move",
        operations=[
            MoveFileOp(source_path="missing.ts", target_path="moved.ts"),
        ],
    )
    result = validate_schedule(
        schedule,
        ScopeSpec(),
        _deps(tmp_path),
    )
    assert result.approved is False
    assert "does not exist" in (result.reason or "")


def test_validate_schedule_rejects_move_file_existing_target(tmp_path: Path) -> None:
    """move_file when target already exists is rejected."""
    (tmp_path / "a.ts").write_text("x")
    (tmp_path / "b.ts").write_text("y")
    schedule = RefactorSchedule(
        goal="move",
        operations=[
            MoveFileOp(source_path="a.ts", target_path="b.ts"),
        ],
    )
    result = validate_schedule(
        schedule,
        ScopeSpec(),
        _deps(tmp_path),
    )
    assert result.approved is False
    assert "already exists" in (result.reason or "")


def test_validation_result_model() -> None:
    """ValidationResult serializes correctly."""
    r = ValidationResult(approved=False, reason="test reason")
    assert r.approved is False
    assert r.reason == "test reason"
