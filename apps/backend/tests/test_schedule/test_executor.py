"""Tests for schedule executor (validation, topo, execution)."""

from __future__ import annotations

from pathlib import Path

import pytest

from refactor_agent.orchestrator.deps import OrchestratorDeps
from refactor_agent.schedule.executor import execute_schedule
from refactor_agent.schedule.models import (
    MoveSymbolOp,
    OrganizeImportsOp,
    RefactorSchedule,
)


def _deps(workspace: Path, language: str = "typescript") -> OrchestratorDeps:
    return OrchestratorDeps(
        language=language,
        workspace=workspace,
        mode="Auto",
        file_ext="*.ts",
    )


@pytest.fixture
def schedule_with_cycle() -> RefactorSchedule:
    """Schedule where op2 depends on op1 and op1 depends on op2."""
    return RefactorSchedule(
        goal="test cycle",
        operations=[
            MoveSymbolOp(
                id="op1",
                depends_on=["op2"],
                source_file="a.ts",
                target_file="b.ts",
                symbol_name="x",
            ),
            OrganizeImportsOp(
                id="op2",
                depends_on=["op1"],
                file_path="b.ts",
            ),
        ],
    )


@pytest.fixture
def schedule_unknown_dep() -> RefactorSchedule:
    """Schedule that references a non-existent depends_on id."""
    return RefactorSchedule(
        goal="test unknown dep",
        operations=[
            OrganizeImportsOp(
                id="op1",
                depends_on=["nonexistent"],
                file_path="a.ts",
            ),
        ],
    )


async def test_executor_rejects_cycle(
    schedule_with_cycle: RefactorSchedule,
    tmp_path: Path,
) -> None:
    """Executor returns error when depends_on has a cycle."""
    result = await execute_schedule(schedule_with_cycle, _deps(tmp_path))
    assert not result.success
    assert "Cycle" in (result.error or "")


async def test_executor_rejects_unknown_dep(
    schedule_unknown_dep: RefactorSchedule,
    tmp_path: Path,
) -> None:
    """Executor returns error when depends_on references unknown id."""
    result = await execute_schedule(schedule_unknown_dep, _deps(tmp_path))
    assert not result.success
    assert "unknown" in (result.error or "").lower()


async def test_executor_rejects_python_workspace(tmp_path: Path) -> None:
    """Executor returns error for Python workspace in PoC (TypeScript only)."""
    schedule = RefactorSchedule(
        goal="test",
        operations=[
            OrganizeImportsOp(file_path="a.py"),
        ],
    )
    deps = _deps(tmp_path, language="python")
    deps.file_ext = "*.py"
    result = await execute_schedule(schedule, deps)
    assert not result.success
    assert "TypeScript" in (result.error or "")
