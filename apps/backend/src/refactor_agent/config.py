from __future__ import annotations

import os

DEFAULT_MODEL = os.getenv("DSA_DEFAULT_MODEL", "anthropic:claude-sonnet-4-6")

# Request timeout (seconds) for orchestrator and AST refactor agent.
AGENT_REQUEST_TIMEOUT: float = 60.0

# Default max_tokens when prompt config does not specify one.
DEFAULT_AGENT_MAX_TOKENS: int = 4096
