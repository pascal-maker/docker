from __future__ import annotations

from refactor_agent.agent.deps import ASTDeps
from refactor_agent.agent.factory import create_ast_refactor_agent
from refactor_agent.engine.python.libcst_engine import LibCSTEngine
from refactor_agent.observability.langfuse_config import init_langfuse


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

    engine = LibCSTEngine(source)
    deps = ASTDeps(engine=engine, target_rename=(old_name, new_name))
    agent = create_ast_refactor_agent()

    skeleton = await engine.get_skeleton()
    prompt = (
        f"AST skeleton of the file:\n\n{skeleton}\n\n"
        f"Task: rename {old_name!r} to {new_name!r} across all references. "
        "Use the rename_symbol tool, then call finish()."
    )

    await agent.run(prompt, deps=deps)
    return await engine.to_source()


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

    engine = LibCSTEngine(source)
    deps = ASTDeps(engine=engine, target_rename=("", ""))
    agent = create_ast_refactor_agent()

    skeleton = await engine.get_skeleton()
    prompt = (
        f"AST skeleton of the file:\n\n{skeleton}\n\n"
        f"Task: extract lines {start_line}-{end_line} from function "
        f"{scope_function!r} into a new function named {new_function_name!r}. "
        "Use the extract_function tool, then call finish()."
    )

    await agent.run(prompt, deps=deps)
    return await engine.to_source()
