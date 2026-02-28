"""Pydantic models for dashboard ingestion and query API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IngestOperation(BaseModel):
    """Single operation in an ingest payload (file_path, op type, rationale)."""

    file_path: str = Field(
        description="Path to the file (or primary file) for this op."
    )
    op_type: str = Field(
        description="Operation type, e.g. rename, move_symbol, organize_imports."
    )
    rationale: str | None = Field(
        default=None, description="Optional rationale for the change."
    )


class IngestCheckResultResponse(BaseModel):
    """Response body for POST /api/ingest/check-result."""

    id: str = Field(description="Created check run UUID as string.")
    status: str = Field(description="Status of the ingestion, e.g. created.")


class IngestCheckResultBody(BaseModel):
    """Request body for POST /api/ingest/check-result."""

    org_id: str = Field(description="Organization identifier (e.g. GitHub org login).")
    repo_id: str = Field(description="Repository identifier (e.g. org/repo).")
    branch: str = Field(description="Branch name.")
    pr_number: int | None = Field(
        default=None, description="PR number if run is for a PR."
    )
    preset_id: str = Field(description="Preset identifier that produced this run.")
    goal: str = Field(description="Refactor goal from the check.")
    status: str = Field(
        description="Run status, e.g. passed, failed_with_suggestions.",
    )
    operations: list[IngestOperation] = Field(
        default_factory=list,
        description="List of suggested operations (file_path, op_type, rationale).",
    )
    timestamp: datetime | None = Field(
        default=None,
        description="When the check ran; server uses now if omitted.",
    )


class OperationOut(BaseModel):
    """Single operation in API output."""

    file_path: str
    op_type: str
    rationale: str | None = None
    sort_order: int = 0


class CheckRunRow(BaseModel):
    """One check_runs row from the DB (for type-safe row handling)."""

    id: UUID
    org_id: str
    repo_id: str
    branch: str
    pr_number: int | None
    preset_id: str
    goal: str
    status: str
    operation_count: int
    created_at: datetime


class IssueSummary(BaseModel):
    """Summary of a check run (one row in the list view)."""

    id: UUID
    org_id: str
    repo_id: str
    branch: str
    pr_number: int | None
    preset_id: str
    goal: str
    status: str
    operation_count: int
    created_at: datetime


class IssueDetail(BaseModel):
    """Full check run with operations (detail view)."""

    id: UUID
    org_id: str
    repo_id: str
    branch: str
    pr_number: int | None
    preset_id: str
    goal: str
    status: str
    operation_count: int
    created_at: datetime
    operations: list[OperationOut] = Field(default_factory=list)


class IssuesListResponse(BaseModel):
    """Paginated list of issue summaries."""

    items: list[IssueSummary]
    total: int
    limit: int
    offset: int
