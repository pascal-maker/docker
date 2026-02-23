"""CI runner: run planner per preset, optionally execute, produce report."""

from __future__ import annotations

import os
from pathlib import Path  # noqa: TC003 — Path used at runtime

from refactor_agent.ci.config import (
    CiConfigError,
    get_language_and_ext,
    resolve_presets,
)
from refactor_agent.ci.logger import logger
from refactor_agent.ci.report import (
    CiReport,
    PresetResult,
    operation_to_summary,
)
from refactor_agent.orchestrator.deps import OrchestratorDeps
from refactor_agent.schedule import create_planner_agent, execute_schedule, run_planner


async def run_ci(
    workspace: Path,
    config_path: Path | None = None,
    *,
    auto_apply: bool = True,
) -> CiReport:
    """Run refactor check for all resolved presets.

    For each preset: run planner; if operations and auto_apply and TypeScript,
    run executor. Builds a CiReport; failed=True when any preset had suggestions
    that were not auto-applied (or execution failed).
    """
    presets = resolve_presets(workspace, config_path)
    if not presets:
        return CiReport(preset_results=[], failed=False)

    if not (
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LITELLM_MASTER_KEY")
    ):
        raise CiConfigError(
            "LLM API key (ANTHROPIC_API_KEY or LITELLM_MASTER_KEY) required"
        )

    preset_results: list[PresetResult] = []
    any_failed = False

    for preset in presets:
        if preset.workspace_subdir:
            effective = (workspace / preset.workspace_subdir).resolve()
            if not effective.is_dir():
                preset_results.append(
                    PresetResult(
                        preset_id=preset.id,
                        goal=preset.goal,
                        operation_count=0,
                        auto_applied=False,
                        operations=[],
                        error=f"workspace_subdir is not a directory: {effective}",
                    ),
                )
                any_failed = True
                continue
            workspace_resolved = effective
        else:
            workspace_resolved = workspace.resolve()  # noqa: ASYNC240 — sync Path in CI
        language, file_ext = get_language_and_ext(workspace_resolved, preset)
        deps = OrchestratorDeps(
            language=language,
            workspace=workspace_resolved,
            mode="ci",
            file_ext=file_ext,
            get_user_input=None,
            schedule_output_ref=None,
            schedule_partial_ref=None,
        )
        agent = create_planner_agent()

        try:
            planner_result = await run_planner(agent, deps, preset.goal)
        except Exception as e:
            logger.exception("Planner failed for preset", preset_id=preset.id)
            preset_results.append(
                PresetResult(
                    preset_id=preset.id,
                    goal=preset.goal,
                    operation_count=0,
                    auto_applied=False,
                    operations=[],
                    error=str(e),
                ),
            )
            any_failed = True
            continue

        schedule = planner_result.schedule
        op_count = len(schedule.operations)
        summaries = [operation_to_summary(op) for op in schedule.operations]

        if op_count == 0:
            preset_results.append(
                PresetResult(
                    preset_id=preset.id,
                    goal=preset.goal,
                    operation_count=0,
                    auto_applied=True,
                    operations=[],
                ),
            )
            continue

        should_auto = auto_apply and language == "typescript"
        if should_auto:
            exec_result = await execute_schedule(schedule, deps)
            if exec_result.success:
                preset_results.append(
                    PresetResult(
                        preset_id=preset.id,
                        goal=schedule.goal,
                        operation_count=op_count,
                        auto_applied=True,
                        operations=summaries,
                    ),
                )
            else:
                preset_results.append(
                    PresetResult(
                        preset_id=preset.id,
                        goal=schedule.goal,
                        operation_count=op_count,
                        auto_applied=False,
                        operations=summaries,
                        error=exec_result.error,
                    ),
                )
                any_failed = True
        else:
            preset_results.append(
                PresetResult(
                    preset_id=preset.id,
                    goal=schedule.goal,
                    operation_count=op_count,
                    auto_applied=False,
                    operations=summaries,
                ),
            )
            any_failed = True

    return CiReport(preset_results=preset_results, failed=any_failed)
