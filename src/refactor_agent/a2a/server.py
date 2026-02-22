"""A2A HTTP server: Agent Card, request handler, Starlette app."""

from __future__ import annotations

from a2a.server.agent_execution import AgentExecutor  # noqa: TC002
from a2a.server.apps import A2AStarletteApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from refactor_agent.a2a.bridge import (
    BridgeCompatibleRequestHandler,
)
from refactor_agent.a2a.executor import (
    ASTRefactorAgentExecutor,
)

REFACTOR_SKILL = AgentSkill(
    id="refactor",
    name="Refactor code",
    description=(
        "Submit a refactoring request; the agent applies supported "
        "transformations and returns updated code. When approval is needed "
        "(e.g. name conflict), the agent will ask; reply in the same context "
        "to continue or cancel."
    ),
    tags=["refactor", "code"],
)

DEFAULT_AGENT_CARD = AgentCard(
    name="AST Refactor Agent",
    description=(
        "Semantic code refactoring. Submit a refactor request and get "
        "updated code. Supports human-in-the-loop when input is required."
    ),
    url="http://localhost:9999/",
    version="0.1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[REFACTOR_SKILL],
)


def build_app(
    agent_executor: AgentExecutor | None = None,
    agent_card: AgentCard | None = None,
) -> A2AStarletteApplication:
    """Build the A2A Starlette application.

    Args:
        agent_executor: Executor for refactor tasks; defaults to
            ASTRefactorAgentExecutor().
        agent_card: Public agent card; defaults to DEFAULT_AGENT_CARD.

    Returns:
        A2AStarletteApplication (call .build() to get the ASGI app).
    """
    executor = agent_executor or ASTRefactorAgentExecutor()
    card = agent_card or DEFAULT_AGENT_CARD
    request_handler = BridgeCompatibleRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(
        agent_card=card,
        http_handler=request_handler,
    )
