"""Error taxonomy: classify failures and dispatch to correct response."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path  # noqa: TC003 — Path used at runtime in dispatch_on_failure

from refactor_agent.agentic.git import reset_to_last_commit
from refactor_agent.agentic.logger import logger
from refactor_agent.schedule.executor import (
    ScheduleResult,  # noqa: TC001 — used at runtime
)


class FailureType(StrEnum):
    """Failure categories from agentic-capabilities plan."""

    COMPILE_ERROR = "compile_error"
    JUDGE_VETO = "judge_veto"
    TEST_FAILURE = "test_failure"
    GIT_CONFLICT = "git_conflict"
    CONTEXT_OVERFLOW = "context_overflow"
    VALIDATOR_REJECT = "validator_reject"
    UNKNOWN = "unknown"


_PATTERNS: list[tuple[tuple[str, ...], FailureType]] = [
    (("conflict", "merge conflict"), FailureType.GIT_CONFLICT),
    (("compile", "syntax", "typeerror", "referenceerror"), FailureType.COMPILE_ERROR),
    (("test", "fail", "assertion"), FailureType.TEST_FAILURE),
    (("veto", "scope creep"), FailureType.JUDGE_VETO),
    (("overflow", "context", "budget", "token"), FailureType.CONTEXT_OVERFLOW),
    (("validator", "invalid", "reject", "dry-run"), FailureType.VALIDATOR_REJECT),
]


def classify_failure(result: ScheduleResult) -> FailureType:
    """Classify failure from ScheduleResult using heuristic pattern matching."""
    error = (result.error or "").lower()
    tb = (result.error_traceback or "").lower()
    combined = f"{error} {tb}"

    for keywords, failure_type in _PATTERNS:
        if any(kw in combined for kw in keywords):
            return failure_type

    for op_result in result.results:
        if "ERROR" in (op_result.summary or ""):
            return FailureType.COMPILE_ERROR

    return FailureType.UNKNOWN


def dispatch_on_failure(
    failure_type: FailureType,
    workspace: Path,
) -> None:
    """Dispatch to the correct handler for the failure type.

    Phase 0: GIT_CONFLICT -> reset_to_last_commit; others -> log only.
    Retry/course-correct logic comes in Phase 1+.
    """
    if failure_type == FailureType.GIT_CONFLICT:
        err = reset_to_last_commit(workspace)
        if err:
            logger.error("Failed to reset on git conflict", error=err)
        else:
            logger.info("Reset workspace after git conflict")
    else:
        logger.info(
            "Failure classified; no Phase 0 action",
            failure_type=failure_type.value,
        )
