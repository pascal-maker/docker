"""Shared LLM client factory for Anthropic (direct or via LiteLLM proxy)."""

from __future__ import annotations

import os

from anthropic import AsyncAnthropic, omit


def get_anthropic_client(*, timeout: float = 60.0) -> AsyncAnthropic:
    """Build an AsyncAnthropic client for all agents.

    When LITELLM_PROXY_URL is set, traffic goes through the proxy (caching,
    load balancing). Otherwise the SDK talks to Anthropic directly.
    Uses LITELLM_MASTER_KEY when set (proxy auth), else ANTHROPIC_API_KEY.
    When using a proxy and no key is set, pass api_key=omit so the SDK
    explicitly omits the header and the proxy uses its own key.
    """
    base_url = os.getenv("LITELLM_PROXY_URL") or None
    api_key_val = (
        os.getenv("LITELLM_MASTER_KEY") or os.getenv("ANTHROPIC_API_KEY")
    ) or None
    if base_url is not None and not api_key_val:
        # anthropic.omit sentinel: SDK omits key; stubs expect str | None.
        return AsyncAnthropic(
            timeout=timeout,
            base_url=base_url,
            api_key=omit,  # type: ignore[arg-type]
            auth_token=omit,  # type: ignore[arg-type]
        )
    if base_url is not None and api_key_val:
        return AsyncAnthropic(
            timeout=timeout,
            base_url=base_url,
            api_key=api_key_val,
        )
    if api_key_val:
        return AsyncAnthropic(timeout=timeout, api_key=api_key_val)
    return AsyncAnthropic(timeout=timeout)
