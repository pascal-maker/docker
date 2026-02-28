"""GitHub OAuth middleware: validate token, check user status, rate limit, audit log."""

from __future__ import annotations

import hmac
import os
import time
from typing import TYPE_CHECKING, Protocol, cast, override

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

if TYPE_CHECKING:
    from starlette.types import Scope

from refactor_agent.auth.github_auth import GitHubTokenValidator
from refactor_agent.auth.models import AuditLogEntry, UserRecord
from refactor_agent.auth.user_store import UserStore

A2A_API_KEY_ENV = "A2A_API_KEY"
ONBOARDING_MODE_ENV = "ONBOARDING_MODE"
ACCESS_REQUEST_URL = "https://refactor-agent.dev"  # placeholder; override via env

PUBLIC_PATHS = frozenset({"/.well-known/agent-card.json"})


class AuthState(Protocol):
    """Typed view of request.state for auth middleware."""

    github_token: str
    user_record: UserRecord


def _extract_bearer(request: Request) -> str | None:
    """Extract Bearer token from Authorization or X-API-Key header."""
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key.strip()
    return None


def _extract_bearer_from_scope(scope: Scope) -> str | None:
    """Extract Bearer token from ASGI scope headers (for WebSocket)."""
    headers = scope.get("headers") or []
    auth_val: bytes | None = None
    api_key_val: bytes | None = None
    for name, value in headers:
        if name.lower() == b"authorization" and value.lower().startswith(b"bearer "):
            auth_val = value[7:].strip()
            break
        if name.lower() == b"x-api-key":
            api_key_val = value.strip()
    if auth_val:
        return auth_val.decode(errors="replace")
    if api_key_val:
        return api_key_val.decode(errors="replace")
    return None


async def validate_token_for_scope(
    scope: Scope,
    *,
    validator: GitHubTokenValidator,
    user_store: UserStore,
    local_dev_key: str | None,
) -> tuple[UserRecord | None, str | None]:
    """Validate token from scope; return (UserRecord, None) or (None, error_detail)."""
    token = _extract_bearer_from_scope(scope)
    if not token:
        return None, "Missing or invalid Authorization header"

    if local_dev_key and hmac.compare_digest(local_dev_key, token):
        record = UserRecord(
            id="local-dev",
            github_login="local-dev",
            status="active",
        )
        return record, None

    github_user = await validator.validate(token)
    if not github_user:
        return None, "Invalid or expired GitHub token"

    if not user_store.is_available():
        return None, "Service unavailable: Auth not configured"

    onboarding_mode = os.environ.get(ONBOARDING_MODE_ENV, "alpha")
    user_record = await user_store.get_or_create_user(
        github_user, onboarding_mode=onboarding_mode
    )

    if user_record.status != "active":
        if user_record.status == "pending":
            access_url = os.environ.get("ACCESS_REQUEST_URL", ACCESS_REQUEST_URL)
            return None, f"Access pending approval. Apply at {access_url}"
        return None, user_record.ban_reason or "Access denied"

    if user_store.is_banned(user_record.id):
        return None, "Access denied"

    limit = user_record.rate_limit_override or 60
    allowed = await user_store.check_and_increment_rate_limit(
        user_record.id, limit=limit
    )
    if not allowed:
        return None, "Rate limit exceeded"

    return user_record, None


def _unauthorized(detail: str, accept: str = "") -> JSONResponse:
    """Return 401 JSON or SSE-style for streaming clients."""
    body = {"error": "Unauthorized", "detail": detail}
    if "text/event-stream" in accept:
        return JSONResponse(
            {"error": "unauthorized", "detail": detail},
            status_code=401,
            media_type="text/event-stream",
        )
    return JSONResponse(body, status_code=401)


def _forbidden(detail: str, accept: str = "") -> JSONResponse:
    """Return 403 JSON or SSE-style for streaming clients."""
    body = {"error": "Forbidden", "detail": detail}
    if "text/event-stream" in accept:
        return JSONResponse(
            {"error": "forbidden", "detail": detail},
            status_code=403,
            media_type="text/event-stream",
        )
    return JSONResponse(body, status_code=403)


def _rate_limited(accept: str = "") -> JSONResponse:
    """Return 429 rate limit exceeded."""
    body = {"error": "Rate limit exceeded", "detail": "Too many requests"}
    if "text/event-stream" in accept:
        return JSONResponse(
            {"error": "rate_limit", "detail": "Too many requests"},
            status_code=429,
            media_type="text/event-stream",
        )
    return JSONResponse(body, status_code=429)


class GitHubTokenMiddleware(BaseHTTPMiddleware):
    """Validate GitHub OAuth token, check user status, rate limit, audit log."""

    @override
    def __init__(
        self,
        app: ASGIApp,
        *,
        validator: GitHubTokenValidator | None = None,
        user_store: UserStore | None = None,
        local_dev_key: str | None = None,
        public_paths: frozenset[str] = PUBLIC_PATHS,
    ) -> None:
        super().__init__(app)
        self._validator = validator or GitHubTokenValidator()
        self._user_store = user_store or UserStore()
        self._local_dev_key = local_dev_key or os.environ.get(A2A_API_KEY_ENV)
        self._public_paths = public_paths

    @override
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Validate auth, check ban/rate limit, then call next."""
        path = request.url.path.rstrip("/") or "/"
        if path in self._public_paths:
            return await call_next(request)

        token = _extract_bearer(request)
        if not token:
            return _unauthorized("Missing or invalid Authorization header")

        accept = request.headers.get("accept", "")

        if self._local_dev_key and hmac.compare_digest(self._local_dev_key, token):
            state = cast("AuthState", request.state)
            state.github_token = token
            state.user_record = UserRecord(
                id="local-dev",
                github_login="local-dev",
                status="active",
            )
            return await call_next(request)

        github_user = await self._validator.validate(token)
        if not github_user:
            return _unauthorized("Invalid or expired GitHub token", accept)

        if not self._user_store.is_available():
            return JSONResponse(
                {"error": "Service unavailable", "detail": "Auth not configured"},
                status_code=503,
            )

        onboarding_mode = os.environ.get(ONBOARDING_MODE_ENV, "alpha")
        user_record = await self._user_store.get_or_create_user(
            github_user, onboarding_mode=onboarding_mode
        )

        if user_record.status != "active":
            if user_record.status == "pending":
                access_url = os.environ.get("ACCESS_REQUEST_URL", ACCESS_REQUEST_URL)
                return _forbidden(
                    f"Access pending approval. Apply at {access_url}",
                    accept,
                )
            return _forbidden(
                user_record.ban_reason or "Access denied",
                accept,
            )

        if self._user_store.is_banned(user_record.id):
            return _forbidden("Access denied", accept)

        limit = user_record.rate_limit_override or 60
        allowed = await self._user_store.check_and_increment_rate_limit(
            user_record.id, limit=limit
        )
        if not allowed:
            return _rate_limited(accept)

        state = cast("AuthState", request.state)
        state.github_token = token
        state.user_record = user_record

        t0 = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - t0) * 1000

        status_code = response.status_code
        await self._user_store.write_audit_log(
            AuditLogEntry(
                user_id=user_record.id,
                github_login=user_record.github_login,
                path=path,
                method=request.method,
                status_code=status_code,
                duration_ms=duration_ms,
            )
        )

        return response
