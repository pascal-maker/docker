"""Unit tests for GitHubTokenMiddleware with mocked validator and user store."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from refactor_agent.a2a.auth_middleware import GitHubTokenMiddleware
from refactor_agent.auth.github_auth import GitHubTokenValidator
from refactor_agent.auth.models import GitHubUser, UserRecord
from refactor_agent.auth.user_store import UserStore


@pytest.fixture
def mock_validator() -> MagicMock:
    v = MagicMock(spec=GitHubTokenValidator)
    v.validate = AsyncMock(return_value=None)
    return v


@pytest.fixture
def mock_user_store() -> MagicMock:
    s = MagicMock(spec=UserStore)
    s.is_available.return_value = True
    s.get_or_create_user = AsyncMock(
        return_value=UserRecord(id="123", github_login="test", status="active")
    )
    s.is_banned.return_value = False
    s.check_and_increment_rate_limit = AsyncMock(return_value=True)
    s.write_audit_log = AsyncMock()
    return s


@pytest.fixture
def mock_request() -> MagicMock:
    req = MagicMock(spec=Request)
    req.url = MagicMock()
    req.url.path = "/"
    req.method = "POST"
    req.headers = {}
    req.state = MagicMock()
    return req


@pytest.mark.asyncio
async def test_middleware_rejects_missing_token(
    mock_validator: MagicMock,
    mock_user_store: MagicMock,
    mock_request: MagicMock,
) -> None:
    """Missing Authorization header returns 401."""
    mock_request.headers = {}
    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

    app = MagicMock()
    mw = GitHubTokenMiddleware(
        app,
        validator=mock_validator,
        user_store=mock_user_store,
        local_dev_key=None,
    )
    response = await mw.dispatch(mock_request, call_next)

    assert response.status_code == 401
    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_middleware_local_dev_key_bypass(
    mock_validator: MagicMock,
    mock_user_store: MagicMock,
    mock_request: MagicMock,
) -> None:
    """Valid A2A_API_KEY bypasses GitHub and Firestore."""
    mock_request.headers = {"authorization": "Bearer dev-key-123"}
    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

    app = MagicMock()
    mw = GitHubTokenMiddleware(
        app,
        validator=mock_validator,
        user_store=mock_user_store,
        local_dev_key="dev-key-123",
    )
    response = await mw.dispatch(mock_request, call_next)

    assert response.status_code == 200
    mock_validator.validate.assert_not_awaited()
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_middleware_pending_user_returns_403(
    mock_validator: MagicMock,
    mock_user_store: MagicMock,
    mock_request: MagicMock,
) -> None:
    """User with status pending gets 403."""
    mock_validator.validate = AsyncMock(
        return_value=GitHubUser(id=999, login="pending_user", email=None)
    )
    mock_user_store.get_or_create_user = AsyncMock(
        return_value=UserRecord(id="999", github_login="pending_user", status="pending")
    )
    mock_request.headers = {"authorization": "Bearer gh-token"}
    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

    app = MagicMock()
    mw = GitHubTokenMiddleware(
        app,
        validator=mock_validator,
        user_store=mock_user_store,
        local_dev_key=None,
    )
    response = await mw.dispatch(mock_request, call_next)

    assert response.status_code == 403
    call_next.assert_not_awaited()
