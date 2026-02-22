"""Tests for CI runner (run_ci with mocked planner)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from refactor_agent.ci.runner import CiConfigError, run_ci
from refactor_agent.schedule.models import RefactorSchedule
from refactor_agent.schedule.planner import PlannerRunResult


@pytest.fixture
def workspace_with_config(tmp_path: Path) -> Path:
    """Workspace with .refactor-agent.yaml defining one preset."""
    config = tmp_path / ".refactor-agent.yaml"
    config.write_text(
        "presets:\n  - id: test-preset\n    goal: Test goal for CI.\n",
        encoding="utf-8",
    )
    return tmp_path


async def test_run_ci_no_presets_returns_empty_report(tmp_path: Path) -> None:
    """With no config and no REFACTOR_AGENT_GOAL, run_ci returns empty report and not failed."""
    report = await run_ci(workspace=tmp_path)
    assert report.failed is False
    assert report.preset_results == []


async def test_run_ci_no_api_key_raises(workspace_with_config: Path) -> None:
    """With presets but no API key, run_ci raises CiConfigError."""
    with patch.dict(
        "os.environ", {"ANTHROPIC_API_KEY": "", "LITELLM_MASTER_KEY": ""}, clear=False
    ):
        with pytest.raises(CiConfigError, match="LLM API key"):
            await run_ci(workspace=workspace_with_config)


async def test_run_ci_mocked_planner_empty_schedule_succeeds(
    workspace_with_config: Path,
) -> None:
    """With presets and mocked run_planner returning 0 ops, run_ci succeeds and report is correct."""
    schedule = RefactorSchedule(goal="Test goal", operations=[])
    planner_result = PlannerRunResult(schedule=schedule, partial=False)

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        with patch(
            "refactor_agent.ci.runner.run_planner",
            new_callable=AsyncMock,
            return_value=planner_result,
        ):
            report = await run_ci(workspace=workspace_with_config)

    assert report.failed is False
    assert len(report.preset_results) == 1
    pr = report.preset_results[0]
    assert pr.preset_id == "test-preset"
    assert pr.goal == "Test goal for CI."
    assert pr.operation_count == 0
    assert pr.auto_applied is True
    assert pr.operations == []


async def test_run_ci_mocked_planner_with_suggestions_report_only(
    workspace_with_config: Path,
) -> None:
    """With presets, mocked planner returns suggestions; Python so report-only, failed=True."""
    from refactor_agent.schedule.models import RenameOp

    schedule = RefactorSchedule(
        goal="Test goal",
        operations=[
            RenameOp(
                file_path="src/foo.py",
                old_name="x",
                new_name="y",
                rationale="test",
            ),
        ],
    )
    planner_result = PlannerRunResult(schedule=schedule, partial=False)

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
        with patch(
            "refactor_agent.ci.runner.run_planner",
            new_callable=AsyncMock,
            return_value=planner_result,
        ):
            report = await run_ci(workspace=workspace_with_config)

    assert report.failed is True
    assert len(report.preset_results) == 1
    pr = report.preset_results[0]
    assert pr.operation_count == 1
    assert pr.auto_applied is False
    assert len(pr.operations) == 1
    assert pr.operations[0].op == "rename"
    assert pr.operations[0].file_path == "src/foo.py"
