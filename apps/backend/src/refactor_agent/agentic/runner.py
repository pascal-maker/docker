"""Phase 0 execution wrapper: git branch/commit/reset, error taxonomy, post-run hook."""

from __future__ import annotations

from refactor_agent.agentic.error_taxonomy import (
    classify_failure,
    dispatch_on_failure,
)
from refactor_agent.agentic.feedback import post_run_hook
from refactor_agent.agentic.git import commit_checkpoint, ensure_refactor_branch
from refactor_agent.agentic.logger import logger
from refactor_agent.orchestrator.deps import OrchestratorDeps  # noqa: TC001
from refactor_agent.schedule.executor import (  # noqa: TC001
    ScheduleResult,
    execute_schedule,
)
from refactor_agent.schedule.models import RefactorSchedule  # noqa: TC001


async def execute_schedule_with_agentic(
    schedule: RefactorSchedule,
    deps: OrchestratorDeps,
) -> ScheduleResult:
    """Execute schedule with Phase 0 agentic infrastructure.

    When is_agent_v2_enabled(): branch per run, commit on success, reset on
    git conflict, classify failures, post-run Qdrant hook.
    """
    workspace = deps.workspace

    err = ensure_refactor_branch(workspace, schedule.goal)
    if err:
        logger.warning("Could not create refactor branch; continuing", error=err)

    result = await execute_schedule(schedule, deps)

    if result.success:
        commit_err = commit_checkpoint(workspace, f"refactor: {schedule.goal}")
        if commit_err:
            logger.warning("Could not commit checkpoint", error=commit_err)
        post_run_hook(workspace, schedule, result, failure_type=None)
    else:
        failure_type = classify_failure(result)
        dispatch_on_failure(failure_type, workspace)
        post_run_hook(workspace, schedule, result, failure_type=failure_type)

    return result
