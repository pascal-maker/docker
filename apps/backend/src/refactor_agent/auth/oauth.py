"""GitHub OAuth code-for-token exchange for web flow."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
import urllib.request

from pydantic import BaseModel

from refactor_agent.auth.logger import logger

# GitHub OAuth endpoint URL; S105 false positive (URL path, not credentials)
GITHUB_OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105


class GitHubTokenResponse(BaseModel):
    """GitHub OAuth token exchange response."""

    access_token: str
    token_type: str = ""
    scope: str = ""


async def exchange_code_for_token(
    code: str,
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    redirect_uri: str | None = None,
) -> str | None:
    """Exchange GitHub OAuth authorization code for access token.

    Returns the access token string, or None on failure.
    """
    cid = client_id or os.environ.get("GITHUB_OAUTH_CLIENT_ID")
    secret = client_secret or os.environ.get("GITHUB_OAUTH_CLIENT_SECRET")
    redirect = redirect_uri or os.environ.get("GITHUB_OAUTH_REDIRECT_URI")
    if not cid or not secret or not redirect:
        logger.warning(
            "GitHub OAuth exchange missing config",
            has_client_id=bool(cid),
            has_client_secret=bool(secret),
            has_redirect_uri=bool(redirect),
        )
        return None
    if not code or not code.strip():
        return None

    def _exchange() -> str | None:
        data = {
            "client_id": cid,
            "client_secret": secret,
            "code": code.strip(),
            "redirect_uri": redirect,
        }
        body = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            GITHUB_OAUTH_ACCESS_TOKEN_URL,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    return None
                raw: object = json.loads(resp.read().decode())
                parsed = GitHubTokenResponse.model_validate(raw)
                return parsed.access_token
        except Exception as e:
            logger.warning(
                "GitHub OAuth token exchange failed",
                error=str(e),
            )
            return None

    return await asyncio.to_thread(_exchange)
