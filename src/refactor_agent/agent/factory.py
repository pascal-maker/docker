from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

if TYPE_CHECKING:
    from pydantic_ai.models.anthropic import AnthropicModelSettings

from refactor_agent.agent.constants import _PROMPT_NAME
from refactor_agent.agent.deps import ASTDeps
from refactor_agent.agent.tools import _register_tools
from refactor_agent.config import (
    AGENT_REQUEST_TIMEOUT,
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_MODEL,
)
from refactor_agent.llm_client import get_anthropic_client
from refactor_agent.observability.langfuse_config import get_prompt, get_prompt_config


def create_ast_refactor_agent() -> Agent[ASTDeps, None]:
    """Create the AST refactoring agent with rename_symbol and finish tools.

    Fetches prompt and config from Langfuse (same pattern as tree agent).
    """
    config = get_prompt_config(_PROMPT_NAME)
    model_str = config.model or DEFAULT_MODEL
    instructions = get_prompt(_PROMPT_NAME)

    model_id = model_str.split(":")[-1] if ":" in model_str else model_str
    model_settings: AnthropicModelSettings = {
        "max_tokens": config.max_tokens or DEFAULT_AGENT_MAX_TOKENS,
        "anthropic_cache_instructions": True,
        "anthropic_cache_tool_definitions": True,
    }
    provider = AnthropicProvider(
        anthropic_client=get_anthropic_client(timeout=AGENT_REQUEST_TIMEOUT),
    )
    model = AnthropicModel(model_id, provider=provider, settings=model_settings)

    # Agent overloads expect Literal model names or output_type type; we pass Model + None.
    agent: Agent[ASTDeps, None] = Agent(  # type: ignore[call-overload]
        model,
        deps_type=ASTDeps,
        output_type=None,
        instructions=instructions,
    )
    _register_tools(agent)
    return agent
