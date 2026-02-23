"""API key validation for ingestion and optional dashboard read."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status


def _get_ingest_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> None:
    """Validate ingestion API key from X-API-Key or Authorization: Bearer.

    Reads expected key from request.app.state.ingest_api_key.
    Raises 401 if expected key is set and the request does not match.
    """
    # Starlette Request.app.state is untyped; we attach ingest_api_key in main.
    expected_key: str | None = getattr(request.app.state, "ingest_api_key", None)
    if not expected_key:
        return
    token: str | None = x_api_key
    if token is None and authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    if not token or token != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


RequireIngestApiKey = Annotated[None, Depends(_get_ingest_api_key)]
