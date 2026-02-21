"""Chat-oriented PydanticAI agent for workspace-level refactoring."""

from dataclasses import dataclass
from pathlib import Path

from anthropic import AsyncAnthropic
from pydantic_ai import Agent, ModelSettings, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from refactor_agent.config import DEFAULT_MODEL
from refactor_agent.engine.libcst_engine import LibCSTEngine

_SYSTEM_PROMPT = """\
You are a Python refactoring assistant. You operate on a workspace \
of Python files in the user's playground directory.

Available operations:
- Rename symbols (variables, functions, classes, parameters) across \
all workspace files using rename_in_workspace.
- List workspace files using list_workspace_files.
- Show the AST skeleton of a file using show_file_skeleton.

When the user asks to rename something, use rename_in_workspace. \
When asked about code structure, use show_file_skeleton or \
list_workspace_files. For general questions, respond conversationally.

If rename_in_workspace reports collisions, inform the user about \
the conflicting definitions and ask whether to proceed. If they \
confirm, call rename_in_workspace again with force=True.

Keep responses concise and helpful.\
"""


@dataclass
class ChatDeps:
    """Dependencies injected into chat agent tools."""

    language: str
    workspace: Path
    mode: str
    file_ext: str


def _scan_workspace(deps: ChatDeps) -> list[Path]:
    if not deps.workspace.exists():
        return []
    return sorted(deps.workspace.rglob(deps.file_ext))


def _check_all_collisions(
    deps: ChatDeps,
    files: list[Path],
    new_name: str,
    scope_node: str | None,
) -> list[str]:
    reports: list[str] = []
    for fp in files:
        source = fp.read_text(encoding="utf-8")
        try:
            engine = LibCSTEngine(source)
        except Exception:  # noqa: S112 — skip unparseable files
            continue
        collisions = engine.check_name_collisions(
            new_name,
            scope_node,
        )
        if collisions:
            rel = str(fp.relative_to(deps.workspace))
            items = ", ".join(f"{c.kind} at {c.location}" for c in collisions)
            reports.append(f"  {rel}: conflicts with {items}")
    return reports


def _apply_renames(
    deps: ChatDeps,
    files: list[Path],
    old_name: str,
    new_name: str,
    scope_node: str | None,
) -> list[str]:
    results: list[str] = []
    for fp in files:
        source = fp.read_text(encoding="utf-8")
        try:
            engine = LibCSTEngine(source)
        except Exception:  # noqa: S112 — skip unparseable files
            continue
        result = engine.rename_symbol(old_name, new_name, scope_node)
        if result.startswith("ERROR:"):
            continue
        rel = str(fp.relative_to(deps.workspace))
        if deps.mode == "Plan":
            results.append(f"[plan] {rel}: {result}")
        else:
            fp.write_text(engine.to_source(), encoding="utf-8")
            results.append(f"{rel}: {result}")
    return results


def _rename_across_files(
    deps: ChatDeps,
    old_name: str,
    new_name: str,
    scope_node: str | None,
    force: bool,  # noqa: FBT001 — LLM tool schema requires bool
) -> str:
    files = _scan_workspace(deps)
    if not files:
        return "No files found in workspace."

    if not force and deps.mode == "Ask":
        collision_reports = _check_all_collisions(
            deps,
            files,
            new_name,
            scope_node,
        )
        if collision_reports:
            return (
                f"Collisions found for '{new_name}':\n"
                + "\n".join(collision_reports)
                + "\n\nAsk the user to confirm before "
                "proceeding with force=True."
            )

    results = _apply_renames(
        deps,
        files,
        old_name,
        new_name,
        scope_node,
    )
    if not results:
        return f"Symbol '{old_name}' not found in any workspace file."
    label = "Plan" if deps.mode == "Plan" else "Rename"
    return f"{label} complete ({len(results)} file(s)):\n" + "\n".join(
        f"- {r}" for r in results
    )


def _create_model() -> AnthropicModel:
    model_str = DEFAULT_MODEL
    model_id = model_str.split(":")[-1] if ":" in model_str else model_str
    provider = AnthropicProvider(
        anthropic_client=AsyncAnthropic(timeout=60.0),
    )
    return AnthropicModel(model_id, provider=provider)


def _register_tools(agent: "Agent[ChatDeps, str]") -> None:
    @agent.tool
    async def rename_in_workspace(
        ctx: RunContext[ChatDeps],
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
        force: bool = False,  # noqa: FBT001, FBT002 — LLM tool schema
    ) -> str:
        """Rename a symbol across all workspace files.

        Args:
            ctx: Agent run context (injected).
            old_name: Current symbol name.
            new_name: Desired new name.
            scope_node: Optional function/class to restrict scope.
            force: Proceed despite name collisions.
        """
        return _rename_across_files(
            ctx.deps,
            old_name,
            new_name,
            scope_node,
            force,
        )

    @agent.tool
    async def list_workspace_files(
        ctx: RunContext[ChatDeps],
    ) -> str:
        """List all files in the workspace.

        Args:
            ctx: Agent run context (injected).
        """
        files = _scan_workspace(ctx.deps)
        if not files:
            return "No files in workspace."
        return "\n".join(str(f.relative_to(ctx.deps.workspace)) for f in files)

    @agent.tool
    async def show_file_skeleton(
        ctx: RunContext[ChatDeps],
        file_path: str,
    ) -> str:
        """Show the AST skeleton of a workspace file.

        Args:
            ctx: Agent run context (injected).
            file_path: Relative path within the workspace.
        """
        full = ctx.deps.workspace / file_path
        if not full.exists():
            return f"File not found: {file_path}"
        source = full.read_text(encoding="utf-8")
        try:
            engine = LibCSTEngine(source)
        except Exception:
            return f"Could not parse {file_path}."
        return engine.get_skeleton()


def create_chat_agent() -> "Agent[ChatDeps, str]":
    """Create the chat-oriented refactoring agent."""
    model = _create_model()
    agent: Agent[ChatDeps, str] = Agent(
        model,
        deps_type=ChatDeps,
        output_type=str,
        system_prompt=_SYSTEM_PROMPT,
        model_settings=ModelSettings(max_tokens=4096),
    )
    _register_tools(agent)
    return agent
