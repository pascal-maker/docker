"""Chat UI: thin adapter over the shared orchestrator agent."""

from refactor_agent.orchestrator import (
    OrchestratorDeps,
    create_orchestrator_agent,
)

# Alias for minimal app changes.
ChatDeps = OrchestratorDeps
create_chat_agent = create_orchestrator_agent

__all__ = [
    "ChatDeps",
    "OrchestratorDeps",
    "create_chat_agent",
    "create_orchestrator_agent",
]
