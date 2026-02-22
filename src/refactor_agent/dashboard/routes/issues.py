"""Query API: list and detail for org issues."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from refactor_agent.dashboard.models import IssuesListResponse
from refactor_agent.dashboard.storage import get_issue_detail, list_issues

router = APIRouter(prefix="/api/orgs", tags=["issues"])


@router.get("/{org_id}/issues", response_model=IssuesListResponse)
def list_org_issues(
    request: Request,
    org_id: str,
    repo_id: str | None = None,
    preset_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> IssuesListResponse:
    """List check runs (issues) for an org with optional filters and pagination."""
    db_path = request.app.state.db_path
    items, total = list_issues(
        db_path,
        org_id,
        repo_id=repo_id,
        preset_id=preset_id,
        since=since,
        until=until,
        limit=min(limit, 100),
        offset=offset,
    )
    return IssuesListResponse(
        items=items,
        total=total,
        limit=min(limit, 100),
        offset=offset,
    )


@router.get("/{org_id}/issues/{run_id}")
def get_org_issue_detail(
    request: Request,
    org_id: str,
    run_id: UUID,
) -> dict[str, object]:
    """Return full check run with operations, or 404."""
    db_path = request.app.state.db_path
    detail = get_issue_detail(db_path, org_id, run_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    return detail.model_dump(mode="json")
