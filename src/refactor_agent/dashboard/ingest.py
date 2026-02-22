"""Ingestion API: POST /api/ingest/check-result."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from refactor_agent.dashboard.auth import _get_ingest_api_key
from refactor_agent.dashboard.models import IngestCheckResultBody
from refactor_agent.dashboard.storage import insert_check_result

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post(
    "/check-result",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_get_ingest_api_key)],
)
def ingest_check_result(
    request: Request,
    body: IngestCheckResultBody,
) -> dict[str, str]:
    """Accept a CI check result and persist it.

    Requires X-API-Key or Authorization: Bearer when ingest API key is configured.
    """
    db_path: Path = request.app.state.db_path
    run_id: UUID = insert_check_result(db_path, body)
    return {"id": str(run_id), "status": "created"}
