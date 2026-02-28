"""Hard limits for the planner agent to prevent infinite loops."""

# Maximum total tool calls in one planner run.
MAX_PLANNER_TOOL_CALLS_PER_RUN: int = 22

# Maximum number of LLM turns (model requests) in one planner run.
MAX_PLANNER_LLM_ROUNDS: int = 7

# Default max_tokens for planner model (refactor schedules can be large). 8x typical 4k.
DEFAULT_PLANNER_MAX_TOKENS: int = 32_768

# HTTP timeout (seconds) for planner Anthropic requests. Large context can take minutes.
PLANNER_REQUEST_TIMEOUT: float = 300.0

# Optional cap on the injected codebase structure string length.
# If the tree exceeds this, it is truncated; truncation may make the plan incomplete.
MAX_CODEBASE_STRUCTURE_CHARS: int = 150_000
