"""Run triage experiment on a Langfuse dataset.

Usage:
    uv run python scripts/langfuse/run_triage_experiment.py [options]

Requires: ANTHROPIC_API_KEY or LITELLM_MASTER_KEY, Langfuse keys, refactor-triage prompt.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from langfuse import Evaluation

# Add src to path for imports when run as script
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_BACKEND_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(_BACKEND_ROOT.parent.parent / ".env")  # Repo root .env

from refactor_agent.agentic.triage import run_triage
from refactor_agent.evals.langfuse_evals import (
    ExperimentConfig,
    run_experiment_on_dataset,
)
from refactor_agent.observability.langfuse_config import init_langfuse
from refactor_agent.orchestrator.deps import OrchestratorDeps


def _default_workspace() -> Path:
    """Default workspace for triage (TypeScript playground)."""
    repo_root = _BACKEND_ROOT.parent.parent
    nestjs = repo_root / "playground" / "nestjs-layered-architecture"
    if nestjs.exists():
        return nestjs
    ts_playground = repo_root / "playground" / "typescript"
    if ts_playground.exists():
        return ts_playground
    return _BACKEND_ROOT


def _category_accuracy_evaluator(
    *,
    input: object,  # noqa: A002, ARG001 — Langfuse evaluator callback signature
    output: object,
    expected_output: object,
    metadata: object,  # noqa: ARG001 — required by Langfuse callback
    **kwargs: object,  # noqa: ARG001 — required by Langfuse callback
) -> Evaluation | None:
    """Score 1.0 when output category matches expected_output.category.

    Returns None when expected_output has no category (skip score; Langfuse rejects value=None).
    """
    expected = expected_output
    if expected is None or not isinstance(expected, dict):
        return None
    exp_cat = expected.get("category")
    if not exp_cat:
        return None

    out = output
    if out is None:
        return Evaluation(name="category_accuracy", value=0.0, comment="No output")
    if hasattr(out, "category"):
        actual = getattr(out, "category", None)
    elif isinstance(out, dict):
        actual = out.get("category")
    else:
        return None

    match = str(actual).lower() == str(exp_cat).lower()
    return Evaluation(
        name="category_accuracy",
        value=1.0 if match else 0.0,
        comment=f"Expected {exp_cat}, got {actual}" if not match else "Match",
    )


async def _triage_task(*, item: object, **kwargs: object) -> object:
    """Run triage on item.input['goal']; return serializable result."""
    deps: OrchestratorDeps = kwargs["deps"]
    inp = getattr(item, "input", item) if not isinstance(item, dict) else item
    goal = inp.get("goal", "") if isinstance(inp, dict) else str(inp)
    result = await run_triage(goal, deps)
    return {
        "category": result.category,
        "confidence": result.confidence,
        "affected_files": result.scope_spec.affected_files[:10],
        "brief": result.brief or "",
    }


def main() -> int:
    """Run triage experiment on Langfuse dataset."""
    init_langfuse()

    parser = argparse.ArgumentParser(
        description="Run triage experiment on Langfuse dataset",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="refactor/triage-validation",
        help="Dataset name (default: refactor/triage-validation)",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace path (default: playground or apps/backend)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Experiment name (default: Triage experiment - <timestamp>)",
    )
    parser.add_argument(
        "--description",
        type=str,
        default="Triage validation experiment",
        help="Experiment description",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=3,
        help="Max concurrent triage runs (default: 3)",
    )
    args = parser.parse_args()

    workspace = args.workspace or _default_workspace()
    if not workspace.exists():
        print(f"Workspace not found: {workspace}", file=sys.stderr)
        return 1

    deps = OrchestratorDeps(
        language="typescript",
        workspace=workspace,
        mode="ci",
        file_ext="*.ts",
    )

    async def task(*, item: object, **kwargs: object) -> object:
        return await _triage_task(item=item, deps=deps, **kwargs)

    config = ExperimentConfig(
        evaluators=[_category_accuracy_evaluator],
        max_concurrency=args.max_concurrency,
    )
    result = run_experiment_on_dataset(
        dataset_name=args.dataset,
        task=task,
        name=args.name or "Triage experiment",
        description=args.description,
        config=config,
    )
    print(result.format())
    return 0


if __name__ == "__main__":
    sys.exit(main())
