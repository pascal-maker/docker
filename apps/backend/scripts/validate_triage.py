"""Run triage against a list of goals; log category and confidence.

Usage:
    uv run python scripts/validate_triage.py [--goals-file PATH] [--workspace PATH]

When --goals-file is omitted, reads from stdin (one goal per line).
When --workspace is omitted, uses apps/backend/playground or similar fixture.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from pydantic import BaseModel

# Add src to path for imports when run as script
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_BACKEND_ROOT / "src"))

from refactor_agent.agentic.triage import run_triage
from refactor_agent.orchestrator.deps import OrchestratorDeps


class TriageValidationEntry(BaseModel):
    """Single triage result for validation output."""

    goal: str
    category: str
    confidence: float
    affected_files: list[str] = []
    brief: str = ""
    error: str | None = None


def _default_workspace() -> Path:
    """Default workspace for triage validation (playground or similar)."""
    playground = _BACKEND_ROOT.parent / "playground" / "nestjs-layered-architecture"
    if playground.exists():
        return playground
    return _BACKEND_ROOT


async def _run_triage_for_goal(
    goal: str,
    deps: OrchestratorDeps,
) -> TriageValidationEntry:
    """Run triage and return serializable result."""
    result = await run_triage(goal.strip(), deps)
    return TriageValidationEntry(
        goal=goal.strip(),
        category=result.category,
        confidence=result.confidence,
        affected_files=result.scope_spec.affected_files[:5],
        brief=result.brief or "",
    )


async def main() -> int:
    """Run triage validation."""
    parser = argparse.ArgumentParser(description="Validate triage against goals")
    parser.add_argument(
        "--goals-file",
        type=Path,
        help="Path to file with one goal per line",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace path (default: playground)",
    )
    args = parser.parse_args()

    if args.goals_file:
        goals = [
            line.strip()
            for line in args.goals_file.read_text().splitlines()
            if line.strip()
        ]
    else:
        goals = [line.strip() for line in sys.stdin if line.strip()]

    if not goals:
        print("No goals to validate.", file=sys.stderr)
        return 1

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

    results: list[TriageValidationEntry] = []
    for goal in goals:
        try:
            out = await _run_triage_for_goal(goal, deps)
            results.append(out)
            print(out.model_dump_json())
        except Exception as e:
            err_entry = TriageValidationEntry(
                goal=goal,
                category="error",
                confidence=0.0,
                error=str(e),
            )
            results.append(err_entry)
            print(err_entry.model_dump_json(), file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
