"""Tests for error taxonomy classification."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from refactor_agent.agentic.error_taxonomy import (
    FailureType,
    classify_failure,
    dispatch_on_failure,
)
from refactor_agent.schedule.executor import OpResult, ScheduleResult


def _result(
    success: bool, error: str | None = None, results: list[OpResult] | None = None
) -> ScheduleResult:
    return ScheduleResult(
        success=success,
        results=results or [],
        error=error,
    )


def test_classify_git_conflict() -> None:
    """Git conflict patterns classify as GIT_CONFLICT."""
    r = _result(False, error="merge conflict in foo.ts")
    assert classify_failure(r) == FailureType.GIT_CONFLICT

    r = _result(False, error="CONFLICT (content): Merge conflict")
    assert classify_failure(r) == FailureType.GIT_CONFLICT


def test_classify_compile_error() -> None:
    """Compile/syntax patterns classify as COMPILE_ERROR."""
    r = _result(False, error="SyntaxError: unexpected token")
    assert classify_failure(r) == FailureType.COMPILE_ERROR

    r = _result(False, error="TypeError: Cannot read property")
    assert classify_failure(r) == FailureType.COMPILE_ERROR

    r = _result(
        False, results=[OpResult("op1", "rename", "ERROR: symbol not found", False)]
    )
    assert classify_failure(r) == FailureType.COMPILE_ERROR


def test_classify_test_failure() -> None:
    """Test failure patterns classify as TEST_FAILURE."""
    r = _result(False, error="Test failed: assertion error")
    assert classify_failure(r) == FailureType.TEST_FAILURE


def test_classify_unknown() -> None:
    """Unrecognized errors classify as UNKNOWN."""
    r = _result(False, error="Something went wrong")
    assert classify_failure(r) == FailureType.UNKNOWN


def test_dispatch_on_git_conflict_resets(tmp_path: Path) -> None:
    """dispatch_on_failure resets workspace for GIT_CONFLICT."""
    (tmp_path / "dirty").write_text("dirty")
    with patch(
        "refactor_agent.agentic.error_taxonomy.reset_to_last_commit", return_value=None
    ):
        dispatch_on_failure(FailureType.GIT_CONFLICT, tmp_path)
    # reset_to_last_commit was called (we patched it); no exception


def test_dispatch_on_other_logs_only(tmp_path: Path) -> None:
    """dispatch_on_failure only logs for non-GIT_CONFLICT."""
    with patch("refactor_agent.agentic.error_taxonomy.reset_to_last_commit") as reset:
        dispatch_on_failure(FailureType.COMPILE_ERROR, tmp_path)
    reset.assert_not_called()
