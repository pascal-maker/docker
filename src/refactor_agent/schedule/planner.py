"""Planner agent: produces RefactorSchedule from a user goal (read-only tools)."""

from __future__ import annotations

from pathlib import Path

from anthropic import AsyncAnthropic
from pydantic_ai import Agent, ModelSettings, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from refactor_agent.config import DEFAULT_MODEL
from refactor_agent.engine.registry import EngineRegistry
from refactor_agent.engine.typescript.ts_morph_engine import TsMorphProjectEngine
from refactor_agent.observability.langfuse_config import get_prompt_config
from refactor_agent.orchestrator.deps import OrchestratorDeps
from refactor_agent.schedule.models import RefactorSchedule

_PLANNER_PROMPT_NAME = "chat-agent"
_TS_ONLY = "This tool is only available for TypeScript workspaces."


def _scan_workspace(deps: OrchestratorDeps) -> list[Path]:
    if not deps.workspace.exists():
        return []
    return sorted(deps.workspace.rglob(deps.file_ext))


def _abs(deps: OrchestratorDeps, rel_path: str) -> str:
    return str((deps.workspace / rel_path).resolve())


def _rel(deps: OrchestratorDeps, abs_path: str) -> str:
    try:
        return str(Path(abs_path).relative_to(deps.workspace))
    except ValueError:
        return abs_path


def _register_planner_tools(
    agent: Agent[OrchestratorDeps, RefactorSchedule],
) -> None:
    """Register read-only tools for the planner."""

    @agent.tool
    async def list_workspace_files(
        ctx: RunContext[OrchestratorDeps],
    ) -> str:
        """List all files in the workspace."""
        files = _scan_workspace(ctx.deps)
        if not files:
            return "No files in workspace."
        return "\n".join(
            str(f.relative_to(ctx.deps.workspace)) for f in files
        )

    @agent.tool
    async def show_file_skeleton(
        ctx: RunContext[OrchestratorDeps],
        file_path: str,
    ) -> str:
        """Show the AST skeleton of a workspace file."""
        if ctx.deps.language == "typescript":
            async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                return await eng.get_skeleton(_abs(ctx.deps, file_path))

        full = ctx.deps.workspace / file_path
        if not full.exists():
            return f"File not found: {file_path}"
        source = full.read_text(encoding="utf-8")
        try:
            engine = EngineRegistry.create(ctx.deps.language, source)
        except Exception:
            return f"Could not parse {file_path}."
        async with engine:
            return await engine.get_skeleton()

    @agent.tool
    async def find_references(
        ctx: RunContext[OrchestratorDeps],
        file_path: str,
        symbol_name: str,
    ) -> str:
        """Find all references to a symbol across the project (TypeScript only)."""
        if ctx.deps.language != "typescript":
            return _TS_ONLY
        async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
            refs = await eng.find_references(
                _abs(ctx.deps, file_path),
                symbol_name,
            )
        if not refs:
            return f"No references found for '{symbol_name}'."
        lines = [f"Found {len(refs)} reference(s) for '{symbol_name}':"]
        for ref in refs:
            tag = " [definition]" if ref.is_definition else ""
            rel = _rel(ctx.deps, ref.file_path)
            lines.append(
                f"  {rel}:{ref.line}:{ref.column}{tag} — {ref.text}",
            )
        return "\n".join(lines)


_PLANNER_INSTRUCTIONS = """
You are a refactoring planner. Given a user goal (e.g. "enforce frontend/backend
boundary", "refactor to vertical slice"), you produce a RefactorSchedule: a goal
string and an ordered list of refactor operations.

Use the read-only tools (list_workspace_files, show_file_skeleton, find_references)
to explore the codebase. Then output a RefactorSchedule with:
- goal: short description of the refactor goal
- operations: list of operations. Each has "op" and operation-specific fields.

Operation types:
- rename: file_path, old_name, new_name, optional scope_node, id, dependsOn, rationale
- move_symbol: source_file, target_file, symbol_name, optional id, dependsOn, rationale
- move_file: source_path, target_path, optional id, dependsOn, rationale
- remove_node: file_path, symbol_name, optional kind, id, dependsOn, rationale
- organize_imports: file_path, optional id, dependsOn, rationale
- create_file: file_path, content, optional id, dependsOn, rationale

Use "id" for a stable op identifier. Use "dependsOn" (list of op ids) when an op
must run after others (e.g. organize_imports after move_symbol). Paths relative
to workspace root.

Output only a valid RefactorSchedule. Structural refactors only (rename, move
symbol, move file, remove node, organize imports, create file); no logic changes.
"""


def create_planner_agent(
    model: AnthropicModel | object | None = None,
) -> Agent[OrchestratorDeps, RefactorSchedule]:
    """Create planner agent (structured output RefactorSchedule, read-only tools)."""
    if model is None:
        config = get_prompt_config(_PLANNER_PROMPT_NAME)
        model_str = config.model or DEFAULT_MODEL
        model_id = model_str.split(":")[-1] if ":" in model_str else model_str
        model_settings = ModelSettings(max_tokens=config.max_tokens or 4096)
        provider = AnthropicProvider(
            anthropic_client=AsyncAnthropic(timeout=60.0),
        )
        model = AnthropicModel(
            model_id,
            provider=provider,
            settings=model_settings,
        )

    agent: Agent[OrchestratorDeps, RefactorSchedule] = Agent(
        model,
        deps_type=OrchestratorDeps,
        output_type=RefactorSchedule,
        instructions=_PLANNER_INSTRUCTIONS,
        instrument=True,
    )
    _register_planner_tools(agent)
    return agent


async def run_planner(
    agent: Agent[OrchestratorDeps, RefactorSchedule],
    deps: OrchestratorDeps,
    user_message: str,
) -> RefactorSchedule:
    """Run the planner agent and return the validated RefactorSchedule."""
    result = await agent.run(user_message, deps=deps)
    return result.output
