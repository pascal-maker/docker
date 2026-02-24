"""Seed the refactor-issues dashboard DB with example check runs for local preview."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from refactor_agent.dashboard.models import IngestCheckResultBody, IngestOperation
from refactor_agent.dashboard.storage import init_db, insert_check_result

DEFAULT_DB = "dashboard.db"


def _db_path() -> Path:
    return Path(os.environ.get("REFACTOR_AGENT_DASHBOARD_DB", DEFAULT_DB))


def _make_run(
    org_id: str,
    repo_id: str,
    branch: str,
    pr_number: int | None,
    preset_id: str,
    goal: str,
    status: str,
    operations: list[tuple[str, str, str | None]],
    created_at: datetime,
) -> IngestCheckResultBody:
    return IngestCheckResultBody(
        org_id=org_id,
        repo_id=repo_id,
        branch=branch,
        pr_number=pr_number,
        preset_id=preset_id,
        goal=goal,
        status=status,
        operations=[
            IngestOperation(file_path=fp, op_type=op, rationale=rat)
            for fp, op, rat in operations
        ],
        timestamp=created_at,
    )


def main() -> None:
    db = _db_path()
    init_db(db)

    base = datetime.now(UTC)
    runs = [
        _make_run(
            org_id="demo",
            repo_id="demo/refactor-agent",
            branch="main",
            pr_number=None,
            preset_id="ddd-boundaries",
            goal="Enforce frontend/backend boundary: move get_order_handler to application layer",
            status="failed_with_suggestions",
            operations=[
                (
                    "frontend/get_order.py",
                    "move_symbol",
                    "Backend use case belongs in application layer",
                ),
                (
                    "application/use_cases/get_order.py",
                    "organize_imports",
                    None,
                ),
            ],
            created_at=base,
        ),
        _make_run(
            org_id="demo",
            repo_id="demo/refactor-agent",
            branch="feat/dashboard",
            pr_number=42,
            preset_id="vertical-slices",
            goal="Reorganize project into vertical slices by feature",
            status="failed_with_suggestions",
            operations=[
                (
                    "orders/order_repository.py",
                    "move_file",
                    "Co-locate order persistence with order domain",
                ),
                (
                    "orders/use_cases/create_order.py",
                    "rename",
                    "Align with slice naming",
                ),
            ],
            created_at=base,
        ),
        _make_run(
            org_id="demo",
            repo_id="demo/other-repo",
            branch="main",
            pr_number=10,
            preset_id="clean-imports",
            goal="Remove unused imports and group by standard library / third party / local",
            status="failed_with_suggestions",
            operations=[
                ("src/utils/helpers.py", "organize_imports", None),
                ("src/api/routes.py", "organize_imports", None),
            ],
            created_at=base,
        ),
        _make_run(
            org_id="acme",
            repo_id="acme/backend",
            branch="main",
            pr_number=None,
            preset_id="layered",
            goal="Move domain logic out of HTTP handlers into application layer",
            status="failed_with_suggestions",
            operations=[
                (
                    "handlers/orders.py",
                    "move_symbol",
                    "CreateOrder use case belongs in application/",
                ),
                (
                    "application/orders/create_order.py",
                    "create_file",
                    "New use case module",
                ),
            ],
            created_at=base,
        ),
    ]

    for body in runs:
        run_id = insert_check_result(db, body)
        print(
            f"Inserted run {run_id} — {body.repo_id} / {body.preset_id}: {body.goal[:50]}…"
        )

    print(
        f"\nSeeded {len(runs)} check runs into {db}. Open the dashboard and select org 'demo' or 'acme'."
    )


if __name__ == "__main__":
    main()
