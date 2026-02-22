"""Shared LLM client factory for Anthropic (direct or via LiteLLM proxy)."""

from __future__ import annotations

import os

from anthropic import AsyncAnthropic


def get_anthropic_client(*, timeout: float = 60.0) -> AsyncAnthropic:
    """Build an AsyncAnthropic client for all agents.

    When LITELLM_PROXY_URL is set, traffic goes through the proxy (caching,
    load balancing). Otherwise the SDK talks to Anthropic directly.
    Uses LITELLM_MASTER_KEY when set (proxy auth), else ANTHROPIC_API_KEY.
    """
    base_url = os.getenv("LITELLM_PROXY_URL") or None
    api_key = os.getenv("LITELLM_MASTER_KEY") or os.getenv("ANTHROPIC_API_KEY")
    return AsyncAnthropic(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )
