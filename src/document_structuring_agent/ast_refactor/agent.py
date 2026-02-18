"""AST refactor agent: PydanticAI agent with rename_symbol tool and run helper."""

from __future__ import annotations

from dataclasses import dataclass

from anthropic import AsyncAnthropic
from pydantic_ai import (  # noqa: TC002 — RunContext needed at runtime for tool ctx
    Agent,
    RunContext,
)
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.settings import ModelSettings

from document_structuring_agent.ast_refactor.engine import ASTEngine
from document_structuring_agent.config import DEFAULT_MODEL
from document_structuring_agent.langfuse_config import (
    get_prompt,
    get_prompt_config,
    init_langfuse,
)

_PROMPT_NAME = "ast-refactor-agent"


@dataclass
class ASTDeps:
    """Dependencies injected into every AST refactor agent tool call."""

    engine: ASTEngine
    target_rename: tuple[str, str]  # (old_name, new_name)


def create_ast_refactor_agent() -> Agent[ASTDeps, None]:
    """Create the AST refactoring agent with rename_symbol and finish tools.

    Fetches prompt and config from Langfuse (same pattern as tree agent).
    """
    config = get_prompt_config(_PROMPT_NAME)
    model_str = config.model or DEFAULT_MODEL
    instructions = get_prompt(_PROMPT_NAME)

    model_id = model_str.split(":")[-1] if ":" in model_str else model_str
    model_settings = ModelSettings(max_tokens=config.max_tokens or 4096)
    provider = AnthropicProvider(anthropic_client=AsyncAnthropic(timeout=60.0))
    model = AnthropicModel(model_id, provider=provider, settings=model_settings)

    # Custom AnthropicModel not in Agent's Literal overloads; runtime accepts it.
    agent: Agent[ASTDeps, None] = Agent(  # type: ignore[call-overload]
        model,
        deps_type=ASTDeps,
        output_type=None,
        instructions=instructions,
    )
    _register_tools(agent)
    return agent


def _register_tools(agent: Agent[ASTDeps, None]) -> None:
    """Register rename_symbol and finish tools on the agent."""

    @agent.tool
    async def rename_symbol(
        ctx: RunContext[ASTDeps],
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str:
        """Rename a symbol across the file or within a function/class scope.

        Args:
            ctx: Agent run context (injected).
            old_name: Current name in the file.
            new_name: Desired new name.
            scope_node: Optional function or class name to restrict the rename
                to that scope; None for file-wide rename.
        """
        return ctx.deps.engine.rename_symbol(old_name, new_name, scope_node)

    @agent.tool
    async def extract_function(
        ctx: RunContext[ASTDeps],
        scope_function: str,
        start_line: int,
        end_line: int,
        new_function_name: str,
    ) -> str:
        """Extract a range of lines from a function into a new function.

        The block is replaced by a call to the new function. Parameters are
        inferred from names used in the block but defined outside it. The new
        function is inserted immediately before scope_function.

        Args:
            ctx: Agent run context (injected).
            scope_function: Name of the function containing the block.
            start_line: First line of the block (1-based, inclusive).
            end_line: Last line of the block (1-based, inclusive).
            new_function_name: Name for the extracted function.
        """
        return ctx.deps.engine.extract_function(
            scope_function, start_line, end_line, new_function_name
        )

    @agent.tool
    async def finish(
        ctx: RunContext[ASTDeps],  # noqa: ARG001 — injected by framework
        summary: str,
    ) -> str:
        """Signal that refactoring is complete.

        Args:
            ctx: Agent run context (injected).
            summary: Brief summary of what was renamed.
        """
        return f"OK: {summary}"


async def run_ast_refactor(
    source: str,
    old_name: str,
    new_name: str,
) -> str:
    """Run the refactor agent once: skeleton + task, then return modified source.

    Args:
        source: Python source code to refactor.
        old_name: Symbol to rename.
        new_name: New name for the symbol.

    Returns:
        Modified source after applying the agent's rename_symbol tool calls.
    """
    init_langfuse()

    engine = ASTEngine(source)
    deps = ASTDeps(engine=engine, target_rename=(old_name, new_name))
    agent = create_ast_refactor_agent()

    skeleton = engine.get_skeleton()
    prompt = (
        f"AST skeleton of the file:\n\n{skeleton}\n\n"
        f"Task: rename {old_name!r} to {new_name!r} across all references. "
        "Use the rename_symbol tool, then call finish()."
    )

    await agent.run(prompt, deps=deps)
    return engine.to_source()


async def run_ast_extract_function(
    source: str,
    scope_function: str,
    start_line: int,
    end_line: int,
    new_function_name: str,
) -> str:
    """Run the refactor agent to extract a line range into a new function.

    Args:
        source: Python source code.
        scope_function: Function containing the block to extract.
        start_line: First line of block (1-based, inclusive).
        end_line: Last line of block (1-based, inclusive).
        new_function_name: Name for the extracted function.

    Returns:
        Modified source after the agent's extract_function tool call.
    """
    init_langfuse()

    engine = ASTEngine(source)
    deps = ASTDeps(engine=engine, target_rename=("", ""))
    agent = create_ast_refactor_agent()

    skeleton = engine.get_skeleton()
    prompt = (
        f"AST skeleton of the file:\n\n{skeleton}\n\n"
        f"Task: extract lines {start_line}-{end_line} from function "
        f"{scope_function!r} into a new function named {new_function_name!r}. "
        "Use the extract_function tool, then call finish()."
    )

    await agent.run(prompt, deps=deps)
    return engine.to_source()
