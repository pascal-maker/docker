"""Tests for ScopeSpec model."""

from __future__ import annotations

from refactor_agent.schedule.models import RefactorSchedule, ScopeSpec


def test_scope_spec_defaults() -> None:
    """ScopeSpec has empty list defaults."""
    spec = ScopeSpec()
    assert spec.affected_files == []
    assert spec.allowed_op_types == []
    assert spec.forbidden_op_types == []


def test_scope_spec_roundtrip() -> None:
    """ScopeSpec round-trips through model_dump and model_validate."""
    spec = ScopeSpec(
        affected_files=["a.ts", "b.ts"],
        allowed_op_types=["move_file", "rename"],
        forbidden_op_types=["create_file"],
    )
    data = spec.model_dump()
    again = ScopeSpec.model_validate(data)
    assert again.affected_files == spec.affected_files
    assert again.allowed_op_types == spec.allowed_op_types
    assert again.forbidden_op_types == spec.forbidden_op_types


def test_refactor_schedule_scope_spec_optional() -> None:
    """RefactorSchedule accepts optional scope_spec."""
    schedule = RefactorSchedule(goal="test", operations=[])
    assert schedule.scope_spec is None

    spec = ScopeSpec(affected_files=["x.ts"])
    schedule_with = RefactorSchedule(goal="test", operations=[], scope_spec=spec)
    assert schedule_with.scope_spec is not None
    assert schedule_with.scope_spec.affected_files == ["x.ts"]
