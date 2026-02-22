"""Shared orchestrator agent: one brain for dev UI and A2A surfaces."""

from refactor_agent.orchestrator.agent import (
    create_orchestrator_agent,
    get_chat_agent_instructions,
)
from refactor_agent.orchestrator.deps import NeedInput, OrchestratorDeps
from refactor_agent.orchestrator.runner import (
    FinalOutput,
    NeedInputResult,
    OrchestratorResult,
    RunState,
    run_orchestrator,
)

__all__ = [
    "FinalOutput",
    "NeedInput",
    "NeedInputResult",
    "OrchestratorDeps",
    "OrchestratorResult",
    "RunState",
    "create_orchestrator_agent",
    "get_chat_agent_instructions",
    "run_orchestrator",
]
