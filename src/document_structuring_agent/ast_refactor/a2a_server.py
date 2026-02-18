"""A2A HTTP server: Agent Card, request handler, Starlette app."""

from __future__ import annotations

from a2a.server.agent_execution import AgentExecutor  # noqa: TC002
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from document_structuring_agent.ast_refactor.a2a_executor import (
    ASTRefactorAgentExecutor,
)

RENAME_SKILL = AgentSkill(
    id="rename_symbol",
    name="Rename symbol",
    description=(
        "Rename a Python symbol in source code with scope-aware AST analysis. "
        "Preserves formatting and comments. Input: JSON with source, old_name, "
        "new_name, and optional scope_node."
    ),
    tags=["refactor", "rename", "python", "ast"],
    examples=[
        "Rename calculate_tax to compute_tax in the given source",
        '{"source": "def foo(): pass", "old_name": "foo", "new_name": "bar"}',
    ],
)

DEFAULT_AGENT_CARD = AgentCard(
    name="AST Refactor Agent",
    description=(
        "Semantic AST-level code refactoring for Python. Rename symbols with "
        "scope awareness; full formatting and comment preservation."
    ),
    url="http://localhost:9999/",
    version="0.1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[RENAME_SKILL],
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
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(
        agent_card=card,
        http_handler=request_handler,
    )
