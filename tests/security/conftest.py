"""Fixtures for security tests: A2A and Chainlit base URLs from env or settings."""

from __future__ import annotations

import pytest

from refactor_agent.a2a.probe_settings import A2aProbeSettings


@pytest.fixture(scope="session")
def a2a_base_url() -> str:
    """A2A server base URL: A2A_URL env or .refactor-agent-a2a-url or localhost default."""
    return A2aProbeSettings().a2a_url.rstrip("/")
