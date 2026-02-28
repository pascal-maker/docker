"""Create or update a Langfuse triage validation dataset from goals.

Usage:
    uv run python scripts/langfuse/create_triage_dataset.py [--goals-file PATH] [options]

When --goals-file is omitted, reads from stdin (one goal per line).
Optional second column (tab-separated) = expected_category for evaluator scoring.

Examples:
    echo "rename X to Y" | uv run python scripts/langfuse/create_triage_dataset.py
    uv run python scripts/langfuse/create_triage_dataset.py --goals-file goals.txt
    uv run python scripts/langfuse/create_triage_dataset.py \\
        --dataset refactor/triage-validation --goals-file goals.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to path for imports when run as script
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _SCRIPT_DIR.parent.parent  # scripts/langfuse -> scripts -> apps/backend

from dotenv import load_dotenv

load_dotenv(_BACKEND_ROOT.parent.parent / ".env")  # Repo root .env
sys.path.insert(0, str(_BACKEND_ROOT / "src"))

from refactor_agent.evals.langfuse_evals import DatasetItem, create_or_update_dataset


def _parse_goals_line(line: str) -> tuple[str, str | None]:
    """Parse 'goal' or 'goal\\tcategory' into (goal, expected_category)."""
    parts = line.strip().split("\t", 1)
    goal = parts[0].strip()
    expected = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    return (goal, expected)


def main() -> int:
    """Create or update triage dataset from goals."""
    parser = argparse.ArgumentParser(
        description="Create Langfuse triage validation dataset from goals",
    )
    parser.add_argument(
        "--goals-file",
        type=Path,
        help="Path to file with one goal per line (optional second column = expected_category)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="refactor/triage-validation",
        help="Dataset name (default: refactor/triage-validation)",
    )
    parser.add_argument(
        "--description",
        type=str,
        default="Refactor triage validation: goals with optional expected categories",
        help="Dataset description",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace path for metadata (optional)",
    )
    args = parser.parse_args()

    if args.goals_file:
        goals_raw = args.goals_file.read_text().splitlines()
    else:
        goals_raw = sys.stdin.readlines()

    lines = [
        line for line in goals_raw if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        print("No goals to add.", file=sys.stderr)
        return 1

    items: list[DatasetItem] = []
    for line in lines:
        goal, expected_category = _parse_goals_line(line)
        if not goal:
            continue
        item = DatasetItem(
            input={"goal": goal},
            expected_output={"category": expected_category}
            if expected_category
            else None,
            metadata={"workspace": str(args.workspace)} if args.workspace else None,
        )
        items.append(item)

    create_or_update_dataset(
        name=args.dataset,
        description=args.description,
        items=items,
    )
    print(f"Added {len(items)} item(s) to dataset {args.dataset!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
