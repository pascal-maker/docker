"""GitHub token validation with in-process TTL cache."""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request

from refactor_agent.auth.logger import logger
from refactor_agent.auth.models import GitHubUser

CACHE_TTL_SECS = 300.0
GITHUB_USER_URL = "https://api.github.com/user"


class GitHubTokenValidator:
    """Validates GitHub OAuth tokens via API with in-process TTL cache."""

    def __init__(self, cache_ttl_secs: float = CACHE_TTL_SECS) -> None:
        """Initialize with optional cache TTL (default 5 min)."""
        self._cache_ttl = cache_ttl_secs
        self._cache: dict[str, tuple[GitHubUser, float]] = {}

    async def validate(self, token: str) -> GitHubUser | None:
        """Validate token via GitHub API; return GitHubUser or None.

        Results are cached for cache_ttl_secs to avoid hitting GitHub on every request.
        """
        if not token or not token.strip():
            return None
        now = time.monotonic()
        if token in self._cache:
            user, expires = self._cache[token]
            if now < expires:
                return user
            del self._cache[token]
        fetched = await self._fetch_user(token)
        if fetched is not None:
            self._cache[token] = (fetched, now + self._cache_ttl)
            return fetched
        return None

    async def _fetch_user(self, token: str) -> GitHubUser | None:
        """Fetch user from GitHub API."""

        def _get() -> GitHubUser | None:
            req = urllib.request.Request(
                GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status != 200:
                        return None
                    raw: object = json.loads(resp.read().decode())
                    return GitHubUser.model_validate(raw)
            except Exception as e:
                logger.warning(
                    "GitHub user fetch failed",
                    error=str(e),
                )
                return None

        return await asyncio.to_thread(_get)
