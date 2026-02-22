"""SQLite persistence for check runs and operations."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from refactor_agent.dashboard.models import (
    IngestCheckResultBody,
    IssueDetail,
    IssueSummary,
    OperationOut,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    name TEXT,
    FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS check_runs (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    repo_id TEXT NOT NULL,
    branch TEXT NOT NULL,
    pr_number INTEGER,
    preset_id TEXT NOT NULL,
    goal TEXT NOT NULL,
    status TEXT NOT NULL,
    operation_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (org_id) REFERENCES organizations(id),
    FOREIGN KEY (repo_id) REFERENCES repositories(id)
);

CREATE TABLE IF NOT EXISTS check_run_operations (
    run_id TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    file_path TEXT NOT NULL,
    op_type TEXT NOT NULL,
    rationale TEXT,
    PRIMARY KEY (run_id, sort_order),
    FOREIGN KEY (run_id) REFERENCES check_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_check_runs_org_repo ON check_runs(org_id, repo_id);
CREATE INDEX IF NOT EXISTS idx_check_runs_created_at ON check_runs(created_at);
"""


def _get_conn(db_path: Path) -> sqlite3.Connection:
    """Open a connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    """Create tables if they do not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _get_conn(db_path) as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def get_cursor(db_path: Path) -> Generator[sqlite3.Cursor, None, None]:
    """Yield a cursor; commits on exit, rolls back on exception."""
    conn = _get_conn(db_path)
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_org_repo(cur: sqlite3.Cursor, org_id: str, repo_id: str) -> None:
    """Insert org and repo if not present (by id)."""
    cur.execute(
        "INSERT OR IGNORE INTO organizations (id, name) VALUES (?, ?)",
        (org_id, None),
    )
    cur.execute(
        "INSERT OR IGNORE INTO repositories (id, org_id, name) VALUES (?, ?, ?)",
        (repo_id, org_id, None),
    )


def insert_check_result(db_path: Path, body: IngestCheckResultBody) -> UUID:
    """Persist a check result and its operations; create org/repo if needed.

    Returns the assigned check run id.
    """
    run_id = uuid4()
    created_at = (body.timestamp or datetime.now(UTC)).isoformat()
    op_count = len(body.operations)

    with get_cursor(db_path) as cur:
        _ensure_org_repo(cur, body.org_id, body.repo_id)
        cur.execute(
            """INSERT INTO check_runs (
                id, org_id, repo_id, branch, pr_number, preset_id, goal,
                status, operation_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(run_id),
                body.org_id,
                body.repo_id,
                body.branch,
                body.pr_number,
                body.preset_id,
                body.goal,
                body.status,
                op_count,
                created_at,
            ),
        )
        for i, op in enumerate(body.operations):
            cur.execute(
                """INSERT INTO check_run_operations
                   (run_id, sort_order, file_path, op_type, rationale)
                   VALUES (?, ?, ?, ?, ?)""",
                (str(run_id), i, op.file_path, op.op_type, op.rationale),
            )
    return run_id


def _row_to_summary(row: dict[str, object]) -> IssueSummary:
    """Build IssueSummary from a check_runs row (dict)."""
    created_at_val = row["created_at"]
    created_at = (
        datetime.fromisoformat(str(created_at_val))
        if isinstance(created_at_val, str)
        else created_at_val
    )
    return IssueSummary(
        id=UUID(str(row["id"])),
        org_id=str(row["org_id"]),
        repo_id=str(row["repo_id"]),
        branch=str(row["branch"]),
        pr_number=cast(int | None, row["pr_number"]),
        preset_id=str(row["preset_id"]),
        goal=str(row["goal"]),
        status=str(row["status"]),
        operation_count=cast(int, row["operation_count"]),
        created_at=cast(datetime, created_at),
    )


def list_issues(
    db_path: Path,
    org_id: str,
    *,
    repo_id: str | None = None,
    preset_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[IssueSummary], int]:
    """List check runs (issues) for an org with optional filters.

    Returns (items, total_count).
    """
    conditions = ["org_id = ?"]
    args: list[object] = [org_id]
    if repo_id is not None:
        conditions.append("repo_id = ?")
        args.append(repo_id)
    if preset_id is not None:
        conditions.append("preset_id = ?")
        args.append(preset_id)
    if since is not None:
        conditions.append("created_at >= ?")
        args.append(since)
    if until is not None:
        conditions.append("created_at <= ?")
        args.append(until)
    where = " AND ".join(conditions)

    with get_cursor(db_path) as cur:
        cur.execute(f"SELECT COUNT(*) FROM check_runs WHERE {where}", args)
        total = cur.fetchone()[0]
        args_page: list[object] = [*args, limit, offset]
        cur.execute(
            f"""SELECT id, org_id, repo_id, branch, pr_number, preset_id, goal, status,
                       operation_count, created_at
                FROM check_runs WHERE {where}
                ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            args_page,
        )
        rows = cur.fetchall()
        col_names = [c[0] for c in cur.description]

    items = [_row_to_summary(dict(zip(col_names, row, strict=True))) for row in rows]
    return items, total


def get_issue_detail(db_path: Path, org_id: str, run_id: UUID) -> IssueDetail | None:
    """Fetch a single check run with its operations, or None if not found."""
    with get_cursor(db_path) as cur:
        cur.execute(
            """SELECT id, org_id, repo_id, branch, pr_number, preset_id, goal, status,
                      operation_count, created_at
               FROM check_runs WHERE id = ? AND org_id = ?""",
            (str(run_id), org_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        col_names = [c[0] for c in cur.description]
        run_dict = dict(zip(col_names, row, strict=True))
        created_at_val = run_dict["created_at"]
        created_at = (
            datetime.fromisoformat(str(created_at_val))
            if isinstance(created_at_val, str)
            else created_at_val
        )
        cur.execute(
            """SELECT file_path, op_type, rationale, sort_order
               FROM check_run_operations WHERE run_id = ? ORDER BY sort_order""",
            (str(run_id),),
        )
        op_rows = cur.fetchall()
        op_cols = [c[0] for c in cur.description]
        operations = [
            OperationOut(
                file_path=str(o["file_path"]),
                op_type=str(o["op_type"]),
                rationale=o["rationale"] if o["rationale"] is not None else None,
                sort_order=int(o["sort_order"]),
            )
            for o in [dict(zip(op_cols, r, strict=True)) for r in op_rows]
        ]
        return IssueDetail(
            id=UUID(str(run_dict["id"])),
            org_id=str(run_dict["org_id"]),
            repo_id=str(run_dict["repo_id"]),
            branch=str(run_dict["branch"]),
            pr_number=run_dict["pr_number"]
            if run_dict["pr_number"] is not None
            else None,
            preset_id=str(run_dict["preset_id"]),
            goal=str(run_dict["goal"]),
            status=str(run_dict["status"]),
            operation_count=int(run_dict["operation_count"]),
            created_at=created_at,
            operations=operations,
        )
