"""Tests for post-run Qdrant feedback hook."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from refactor_agent.agentic.error_taxonomy import FailureType
from refactor_agent.agentic.feedback import RunResult, post_run_hook
from refactor_agent.schedule.executor import ScheduleResult
from refactor_agent.schedule.models import RefactorSchedule


def test_post_run_hook_no_op_when_qdrant_url_unset(tmp_path: Path) -> None:
    """post_run_hook is no-op when QDRANT_URL not set."""
    with patch.dict("os.environ", {"QDRANT_URL": ""}, clear=False):
        schedule = RefactorSchedule(goal="test", operations=[])
        result = ScheduleResult(success=True, results=[])
        post_run_hook(tmp_path, schedule, result, failure_type=None)
    # No exception; hook ran and skipped


def test_run_result_model() -> None:
    """RunResult serializes correctly."""
    r = RunResult(
        success=False,
        goal="refactor foo",
        operation_count=3,
        failure_type=FailureType.GIT_CONFLICT,
    )
    assert r.success is False
    assert r.goal == "refactor foo"
    assert r.operation_count == 3
    assert r.failure_type == FailureType.GIT_CONFLICT
    assert r.applied_codemod_ids == []
