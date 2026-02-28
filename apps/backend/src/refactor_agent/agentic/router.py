"""Layer 1: Intent router — refactor vs general_chat, extract goal."""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import (
    Model,  # noqa: TC002 — Model used in create_router_agent signature
)
from pydantic_ai.models.anthropic import (  # noqa: TC002
    AnthropicModel,
    AnthropicModelSettings,  # TypedDict for model_settings at runtime
)
from pydantic_ai.providers.anthropic import AnthropicProvider

from refactor_agent.config import AGENT_REQUEST_TIMEOUT, DEFAULT_MODEL
from refactor_agent.llm_client import get_anthropic_client
from refactor_agent.models.prompt_config import PromptConfig
from refactor_agent.observability.langfuse_config import get_prompt_config


class RouteResult(BaseModel):
    """Result of intent routing."""

    intent: str = Field(
        description="One of: refactor, general_chat",
    )
    goal: str | None = Field(
        default=None,
        description="Extracted refactor goal when intent is refactor.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the classification.",
    )


_ROUTER_INSTRUCTIONS = """
You are an intent router. Given a user message, classify:
- **refactor**: User wants to refactor, reorganize, move, rename, or restructure code.
- **general_chat**: General question, explanation request, or non-refactor.

When intent is refactor, extract the goal as a short imperative (e.g. "rename X to Y",
"move module to feature slice", "enforce frontend/backend boundary").
When intent is general_chat, leave goal as null.

Output RouteResult with intent, goal (or null), and confidence 0.0 to 1.0.
"""


class _RouterDeps:
    """Empty deps for stateless Layer 1 router."""


def create_router_agent(
    model: Model | None = None,
) -> Agent[_RouterDeps, RouteResult]:
    """Create the Layer 1 intent router agent."""
    if model is None:
        try:
            config = get_prompt_config("refactor-router")
        except Exception:
            config = PromptConfig()
        model_str = config.model or DEFAULT_MODEL
        model_id = model_str.split(":")[-1] if ":" in model_str else model_str
        model_settings: AnthropicModelSettings = {
            "max_tokens": config.max_tokens or 1024,
            "anthropic_cache_instructions": True,
            "anthropic_cache_tool_definitions": True,
        }
        provider = AnthropicProvider(
            anthropic_client=get_anthropic_client(timeout=AGENT_REQUEST_TIMEOUT),
        )
        model = AnthropicModel(
            model_id,
            provider=provider,
            settings=model_settings,
        )
    agent: Agent[_RouterDeps, RouteResult] = Agent(
        model,
        deps_type=_RouterDeps,
        output_type=RouteResult,
        instructions=_ROUTER_INSTRUCTIONS,
    )
    return agent


async def route_intent(
    user_message: str,
    agent: Agent[_RouterDeps, RouteResult] | None = None,
) -> RouteResult:
    """Route user message to refactor or general_chat; extract goal if refactor."""
    router_agent = agent or create_router_agent()
    run = await router_agent.run(user_message, deps=_RouterDeps())
    return (
        run.output
        if isinstance(run.output, RouteResult)
        else RouteResult(
            intent="general_chat",
            goal=None,
            confidence=0.5,
        )
    )
