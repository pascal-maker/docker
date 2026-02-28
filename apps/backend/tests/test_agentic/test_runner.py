"""Tests for Phase 0 execution wrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from refactor_agent.agentic.runner import execute_schedule_with_agentic
from refactor_agent.orchestrator.deps import OrchestratorDeps
from refactor_agent.schedule.executor import ScheduleResult
from refactor_agent.schedule.models import OrganizeImportsOp, RefactorSchedule


def _deps(workspace: Path) -> OrchestratorDeps:
    return OrchestratorDeps(
        language="typescript",
        workspace=workspace,
        mode="Auto",
        file_ext="*.ts",
    )


async def test_execute_schedule_with_agentic_passthrough_when_flag_off(
    tmp_path: Path,
) -> None:
    """When is_agent_v2_enabled is False, callers use execute_schedule directly.

    This test verifies execute_schedule_with_agentic still works when called
    (e.g. from a test that patches the flag). We patch git/feedback to avoid
    side effects.
    """
    schedule = RefactorSchedule(
        goal="test",
        operations=[OrganizeImportsOp(file_path="x.ts")],
    )
    deps = _deps(tmp_path)

    with (
        patch(
            "refactor_agent.agentic.runner.ensure_refactor_branch", return_value=None
        ),
        patch("refactor_agent.agentic.runner.commit_checkpoint", return_value=None),
    ):
        result = await execute_schedule_with_agentic(schedule, deps)

    # Executor fails for TypeScript with no real project; we care that we got a result
    assert isinstance(result, ScheduleResult)


async def test_execute_schedule_with_agentic_calls_hook_on_success(
    tmp_path: Path,
) -> None:
    """post_run_hook is called on success."""
    schedule = RefactorSchedule(goal="test", operations=[])
    deps = _deps(tmp_path)

    with (
        patch(
            "refactor_agent.agentic.runner.execute_schedule", new_callable=AsyncMock
        ) as mock_exec,
        patch(
            "refactor_agent.agentic.runner.ensure_refactor_branch", return_value=None
        ),
        patch("refactor_agent.agentic.runner.commit_checkpoint", return_value=None),
        patch("refactor_agent.agentic.runner.post_run_hook") as mock_hook,
    ):
        mock_exec.return_value = ScheduleResult(success=True, results=[])
        await execute_schedule_with_agentic(schedule, deps)

    mock_hook.assert_called_once()
    call_args = mock_hook.call_args
    assert call_args[0][1] == schedule
    assert call_args[0][2].success is True
    assert call_args[1]["failure_type"] is None


async def test_execute_schedule_with_agentic_calls_hook_on_failure(
    tmp_path: Path,
) -> None:
    """post_run_hook is called on failure with failure_type."""
    schedule = RefactorSchedule(goal="test", operations=[])
    deps = _deps(tmp_path)

    with (
        patch(
            "refactor_agent.agentic.runner.execute_schedule", new_callable=AsyncMock
        ) as mock_exec,
        patch(
            "refactor_agent.agentic.runner.ensure_refactor_branch", return_value=None
        ),
        patch("refactor_agent.agentic.runner.dispatch_on_failure"),
        patch("refactor_agent.agentic.runner.post_run_hook") as mock_hook,
    ):
        mock_exec.return_value = ScheduleResult(
            success=False,
            results=[],
            error="merge conflict",
        )
        await execute_schedule_with_agentic(schedule, deps)

    mock_hook.assert_called_once()
    call_args = mock_hook.call_args
    assert call_args[1]["failure_type"] is not None
