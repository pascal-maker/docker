from __future__ import annotations

from pydantic_ai import Agent, RunContext

from refactor_agent.agent.deps import ASTDeps


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
        return await ctx.deps.engine.rename_symbol(old_name, new_name, scope_node)

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
        return await ctx.deps.engine.extract_function(
            scope_function, start_line, end_line, new_function_name
        )

    @agent.tool
    async def finish(
        ctx: RunContext[ASTDeps],  # injected by framework
        summary: str,
    ) -> str:
        """Signal that refactoring is complete.

        Args:
            ctx: Agent run context (injected).
            summary: Brief summary of what was renamed.
        """
        return f"OK: {summary}"
