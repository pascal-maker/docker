"""Post-run Qdrant feedback hook: wire now; actual upsert in Phase 2."""

from __future__ import annotations

import os
from pathlib import Path  # noqa: TC003 — Path used at runtime for future Qdrant wiring

from pydantic import BaseModel

from refactor_agent.agentic.error_taxonomy import FailureType
from refactor_agent.agentic.logger import logger
from refactor_agent.schedule.executor import ScheduleResult  # noqa: TC001 — runtime
from refactor_agent.schedule.models import RefactorSchedule  # noqa: TC001 — runtime

QDRANT_URL_ENV = "QDRANT_URL"


class RunResult(BaseModel):
    """Result of a refactor run for feedback persistence."""

    success: bool
    goal: str
    operation_count: int
    phase_summary: str | None = None
    failure_type: FailureType | None = None
    applied_codemod_ids: list[str] = []


def post_run_hook(
    workspace: Path,
    schedule: RefactorSchedule,
    result: ScheduleResult,
    failure_type: FailureType | None,
) -> None:
    """Invoke after every refactor run (success or failure).

    When QDRANT_URL not set: no-op (log at debug).
    When set: stub implementation; actual Qdrant client in Phase 2.
    workspace is reserved for future use (e.g. project_id for multi-tenant).
    """
    run_result = RunResult(
        success=result.success,
        goal=schedule.goal,
        operation_count=len(schedule.operations),
        phase_summary=None,
        failure_type=failure_type,
        applied_codemod_ids=[],
    )
    qdrant_url = os.environ.get(QDRANT_URL_ENV, "").strip()
    if not qdrant_url:
        logger.debug(
            "Post-run hook skipped (QDRANT_URL not set)",
            success=run_result.success,
            goal=run_result.goal[:60],
            workspace=str(workspace),
        )
        return
    logger.info(
        "Post-run hook: would upsert to Qdrant (stub)",
        success=run_result.success,
        goal=run_result.goal[:60],
        failure_type=run_result.failure_type.value if run_result.failure_type else None,
    )
