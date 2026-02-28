from __future__ import annotations

import os

DEFAULT_MODEL = os.getenv("DSA_DEFAULT_MODEL", "anthropic:claude-sonnet-4-6")

# Request timeout (seconds) for orchestrator and AST refactor agent.
AGENT_REQUEST_TIMEOUT: float = 60.0

# Default max_tokens when prompt config does not specify one.
DEFAULT_AGENT_MAX_TOKENS: int = 4096

AGENT_VERSION: str = os.environ.get("AGENT_VERSION", "")


def is_agent_v2_enabled() -> bool:
    """True when AGENT_V2 is active: git, ScopeSpec, error taxonomy, Qdrant hook."""
    return AGENT_VERSION == "AGENT_V2"
