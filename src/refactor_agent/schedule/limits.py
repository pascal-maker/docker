"""Hard limits for the planner agent to prevent infinite loops."""

# Maximum total tool calls in one planner run.
MAX_PLANNER_TOOL_CALLS_PER_RUN: int = 30

# Maximum number of LLM turns (model requests) in one planner run.
MAX_PLANNER_LLM_ROUNDS: int = 10

# Optional cap on the injected codebase structure string length.
# If the tree exceeds this, it is truncated; truncation may make the plan incomplete.
MAX_CODEBASE_STRUCTURE_CHARS: int = 150_000
