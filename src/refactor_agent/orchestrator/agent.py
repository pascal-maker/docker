"""Orchestrator agent: single brain for dev UI and A2A."""

# NOTE: do NOT use `from __future__ import annotations` here.
# PydanticAI's @agent.tool decorator needs RunContext resolvable at runtime.

from pathlib import Path

from anthropic import AsyncAnthropic
from pydantic_ai import Agent, ModelSettings, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.tools import ToolDefinition

from refactor_agent.config import DEFAULT_MODEL
from refactor_agent.engine.registry import EngineRegistry
from refactor_agent.engine.subprocess_engine import SubprocessError
from refactor_agent.engine.typescript.ts_morph_engine import TsMorphProjectEngine
from refactor_agent.observability.langfuse_config import get_prompt, get_prompt_config
from refactor_agent.orchestrator.deps import (
    NeedInput,
    OrchestratorDeps,
    serialize_need_input,
)
from refactor_agent.schedule import create_planner_agent, run_planner

_PROMPT_NAME = "chat-agent"

_SCHEDULE_GUIDANCE = """

## Multi-step refactoring

For any refactor that involves **multiple operations** (moving several symbols, \
reorganising file structure, enforcing architectural boundaries, adopting a new \
folder layout, etc.), you MUST use `create_refactor_schedule` to produce a \
schedule. Do NOT call `move_symbol`, `organize_imports`, `remove_declaration`, \
or `format_file` individually for planned multi-step changes — the schedule \
executor handles those atomically and in the correct dependency order.

Use the individual mutation tools only for **single, isolated** edits the user \
explicitly asks for (e.g. "organize imports in auth.ts", "move `Foo` to bar.ts").
"""

_MUTATION_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "move_symbol",
        "organize_imports",
        "remove_declaration",
        "format_file",
    }
)


async def _prepare_tools(
    ctx: RunContext[OrchestratorDeps],
    tools: list[ToolDefinition],
) -> list[ToolDefinition]:
    """Hide mutation tools when they would cause problems.

    Plan mode is read-only: individual mutations skip apply_changes(),
    so letting the agent call them would discard all changes silently.
    After create_refactor_schedule runs, the executor handles mutations;
    removing the tools prevents the agent from duplicating that work.
    """
    if ctx.deps.schedule_produced or ctx.deps.mode == "Plan":
        return [t for t in tools if t.name not in _MUTATION_TOOL_NAMES]
    return tools


_TOOL_OPERATIONS: list[tuple[str, str]] = [
    ("rename_in_workspace", "Rename symbols across all workspace files"),
    ("find_references", "Find all references to a symbol"),
    (
        "remove_declaration",
        "Remove a declaration (function, class, interface, type, enum, variable)",
    ),
    ("move_symbol", "Move a symbol from one file to another"),
    ("format_file", "Format a file"),
    ("organize_imports", "Organize imports in a file"),
    ("show_diagnostics", "Show TypeScript diagnostics"),
    ("list_workspace_files", "List workspace files"),
    ("show_file_skeleton", "Show the AST skeleton of a file"),
    (
        "create_refactor_schedule",
        "Produce a multi-step refactor schedule; use for plan/schedule requests",
    ),
]


def _format_available_operations() -> str:
    return "\n".join(f"- {desc} using {name}." for name, desc in _TOOL_OPERATIONS)


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


async def _check_all_collisions(
    deps: OrchestratorDeps,
    files: list[Path],
    new_name: str,
    scope_node: str | None,
) -> list[str]:
    reports: list[str] = []
    for fp in files:
        source = fp.read_text(encoding="utf-8")
        try:
            engine = EngineRegistry.create(deps.language, source)
        except Exception:  # noqa: S112
            continue
        async with engine:
            collisions = await engine.check_name_collisions(
                new_name,
                scope_node,
            )
        if collisions:
            rel = str(fp.relative_to(deps.workspace))
            items = ", ".join(f"{c.kind} at {c.location}" for c in collisions)
            reports.append(f"  {rel}: conflicts with {items}")
    return reports


async def _apply_renames_per_file(
    deps: OrchestratorDeps,
    files: list[Path],
    old_name: str,
    new_name: str,
    scope_node: str | None,
) -> list[str]:
    results: list[str] = []
    for fp in files:
        source = fp.read_text(encoding="utf-8")
        try:
            engine = EngineRegistry.create(deps.language, source)
        except Exception:  # noqa: S112
            continue
        async with engine:
            result = await engine.rename_symbol(
                old_name,
                new_name,
                scope_node,
            )
            if result.startswith("ERROR:"):
                continue
            rel = str(fp.relative_to(deps.workspace))
            if deps.mode == "Plan":
                results.append(f"[plan] {rel}: {result}")
            else:
                new_source = await engine.to_source()
                fp.write_text(new_source, encoding="utf-8")
                results.append(f"{rel}: {result}")
    return results


def _is_reply_yes(reply: str) -> bool:
    return reply.strip().lower() in ("yes", "y", "proceed", "force")


def _is_reply_no(reply: str) -> bool:
    return reply.strip().lower() in ("no", "n", "cancel")


async def _rename_python(  # noqa: PLR0911
    deps: OrchestratorDeps,
    old_name: str,
    new_name: str,
    scope_node: str | None,
    force: bool,  # noqa: FBT001
) -> str:
    files = _scan_workspace(deps)
    if not files:
        return "No files found in workspace."

    if not force and deps.mode == "Ask":
        collision_reports = await _check_all_collisions(
            deps,
            files,
            new_name,
            scope_node,
        )
        if collision_reports:
            message = (
                f"Name collision for '{new_name}'. Reply with: yes to force, "
                "no to cancel, or a new name to use instead.\n\n"
                + "\n".join(collision_reports)
            )
            payload: dict[str, object] = {
                "old_name": old_name,
                "new_name": new_name,
                "collision_reports": collision_reports,
                "hint": "alternative_name",
            }
            need = NeedInput(type="rename_collision", message=message, payload=payload)
            if deps.get_user_input is not None:
                reply = await deps.get_user_input(need)
                if _is_reply_yes(reply):
                    force = True  # proceed despite collision
                elif _is_reply_no(reply):
                    return "Rename canceled."
                else:
                    new_name = reply.strip()
                    if not new_name:
                        return "Rename canceled."
                    force = True  # use new name, no need to ask again
            else:
                return serialize_need_input(need)

    results = await _apply_renames_per_file(
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


async def _rename_typescript(
    deps: OrchestratorDeps,
    old_name: str,
    new_name: str,
    scope_node: str | None,
) -> str:
    files = _scan_workspace(deps)
    if not files:
        return "No files found in workspace."

    try:
        async with TsMorphProjectEngine(deps.workspace) as engine:
            for fp in files:
                abs_path = str(fp.resolve())
                result = await engine.rename_symbol(
                    abs_path,
                    old_name,
                    new_name,
                    scope_node,
                )
                if "ERROR" not in result:
                    if deps.mode != "Plan":
                        await engine.apply_changes()
                    return result
    except SubprocessError as exc:
        return f"ERROR: rename failed for '{old_name}': {exc}"
    return f"Symbol '{old_name}' not found in any workspace file."


def _register_core_tools(agent: Agent[OrchestratorDeps, str]) -> None:
    @agent.tool
    async def rename_in_workspace(
        ctx: RunContext[OrchestratorDeps],
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
        force: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """Rename a symbol across all workspace files."""
        if ctx.deps.language == "typescript":
            return await _rename_typescript(
                ctx.deps,
                old_name,
                new_name,
                scope_node,
            )
        return await _rename_python(
            ctx.deps,
            old_name,
            new_name,
            scope_node,
            force,
        )

    @agent.tool
    async def list_workspace_files(
        ctx: RunContext[OrchestratorDeps],
    ) -> str:
        """List all files in the workspace."""
        files = _scan_workspace(ctx.deps)
        if not files:
            return "No files in workspace."
        return "\n".join(str(f.relative_to(ctx.deps.workspace)) for f in files)

    @agent.tool
    async def show_file_skeleton(
        ctx: RunContext[OrchestratorDeps],
        file_path: str,
    ) -> str:
        """Show the AST skeleton of a workspace file."""
        if ctx.deps.language == "typescript":
            try:
                async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                    return await eng.get_skeleton(
                        _abs(ctx.deps, file_path),
                    )
            except SubprocessError as exc:
                return f"ERROR: show_file_skeleton failed for {file_path}: {exc}"

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


_TS_ONLY = "This tool is only available for TypeScript workspaces."


def _register_analysis_tools(agent: Agent[OrchestratorDeps, str]) -> None:  # noqa: C901 — multiple tools with language guards and error handling
    @agent.tool
    async def find_references(
        ctx: RunContext[OrchestratorDeps],
        file_path: str,
        symbol_name: str,
    ) -> str:
        """Find all references to a symbol across the project (TypeScript only)."""
        if ctx.deps.language != "typescript":
            return _TS_ONLY
        try:
            async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                refs = await eng.find_references(
                    _abs(ctx.deps, file_path),
                    symbol_name,
                )
        except SubprocessError as exc:
            return f"ERROR: find_references failed for {file_path}: {exc}"
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

    @agent.tool
    async def show_diagnostics(
        ctx: RunContext[OrchestratorDeps],
        file_path: str | None = None,
    ) -> str:
        """Show TypeScript diagnostics for a file or the project (TypeScript only)."""
        if ctx.deps.language != "typescript":
            return _TS_ONLY
        abs_path = _abs(ctx.deps, file_path) if file_path else None
        try:
            async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                diags = await eng.get_diagnostics(abs_path)
        except SubprocessError as exc:
            return f"ERROR: show_diagnostics failed: {exc}"
        if not diags:
            return "No diagnostics found."
        lines = [f"Found {len(diags)} diagnostic(s):"]
        for d in diags:
            rel = _rel(ctx.deps, d.file_path)
            lines.append(
                f"  [{d.severity}] {rel}:{d.line} — {d.message} (TS{d.code})",
            )
        return "\n".join(lines)


def _register_mutation_tools(agent: Agent[OrchestratorDeps, str]) -> None:  # noqa: C901 — language guards add branches
    @agent.tool
    async def remove_declaration(
        ctx: RunContext[OrchestratorDeps],
        file_path: str,
        symbol_name: str,
        kind: str | None = None,
    ) -> str:
        """Remove a declaration from a file (TypeScript only)."""
        if ctx.deps.language != "typescript":
            return _TS_ONLY
        try:
            async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                result = await eng.remove_node(
                    _abs(ctx.deps, file_path),
                    symbol_name,
                    kind,
                )
                if ctx.deps.mode != "Plan":
                    await eng.apply_changes()
                return result
        except SubprocessError as exc:
            return f"ERROR: remove_declaration failed for {file_path}: {exc}"

    @agent.tool
    async def move_symbol(
        ctx: RunContext[OrchestratorDeps],
        source_file: str,
        target_file: str,
        symbol_name: str,
    ) -> str:
        """Move a declaration from one file to another (TypeScript only)."""
        if ctx.deps.language != "typescript":
            return _TS_ONLY
        try:
            async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                result = await eng.move_symbol(
                    _abs(ctx.deps, source_file),
                    _abs(ctx.deps, target_file),
                    symbol_name,
                )
                if ctx.deps.mode != "Plan":
                    await eng.apply_changes()
                return result
        except SubprocessError as exc:
            return f"ERROR: move_symbol failed for {symbol_name}: {exc}"

    @agent.tool
    async def format_file(
        ctx: RunContext[OrchestratorDeps],
        file_path: str,
    ) -> str:
        """Format a TypeScript file (TypeScript only)."""
        if ctx.deps.language != "typescript":
            return _TS_ONLY
        try:
            async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                result = await eng.format_file(_abs(ctx.deps, file_path))
                if ctx.deps.mode != "Plan":
                    await eng.apply_changes()
                return result
        except SubprocessError as exc:
            return f"ERROR: format_file failed for {file_path}: {exc}"

    @agent.tool
    async def organize_imports(
        ctx: RunContext[OrchestratorDeps],
        file_path: str,
    ) -> str:
        """Organize imports in a TypeScript file (TypeScript only)."""
        if ctx.deps.language != "typescript":
            return _TS_ONLY
        try:
            async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                result = await eng.organize_imports(
                    _abs(ctx.deps, file_path),
                )
                if ctx.deps.mode != "Plan":
                    await eng.apply_changes()
                return result
        except SubprocessError as exc:
            return f"ERROR: organize_imports failed for {file_path}: {exc}"


def _register_schedule_tool(agent: Agent[OrchestratorDeps, str]) -> None:
    """Register create_refactor_schedule; runs planner, stores schedule when ref set."""

    @agent.tool
    async def create_refactor_schedule(
        ctx: RunContext[OrchestratorDeps],
        goal: str,
    ) -> str:
        """Produce a refactor schedule for a multi-step goal (e.g. enforce boundaries).

        Use when the user asks for a plan, schedule, or multi-step refactor. Run the
        planner to get a RefactorSchedule; it is stored for the app to execute by mode.
        """
        planner_agent = create_planner_agent()
        schedule = await run_planner(planner_agent, ctx.deps, goal)
        if ctx.deps.schedule_output_ref is not None:
            ctx.deps.schedule_output_ref.append(schedule.model_dump_json())
        ctx.deps.schedule_produced = True
        n = len(schedule.operations)
        return (
            f"RefactorSchedule produced ({n} operations) for: "
            f"{schedule.goal!r}. "
            "Execution is handled automatically by the system. "
            "Do NOT call individual mutation tools — just summarise "
            "the plan to the user and stop."
        )


def create_orchestrator_agent(
    model: AnthropicModel | object | None = None,
) -> Agent[OrchestratorDeps, str]:
    """Create the shared orchestrator agent (dev UI and A2A).

    Args:
        model: Optional model (e.g. TestModel for tests). If None, built from config.
    """
    if model is None:
        config = get_prompt_config(_PROMPT_NAME)
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
    instructions = (
        get_prompt(
            _PROMPT_NAME,
            available_operations=_format_available_operations(),
        )
        + _SCHEDULE_GUIDANCE
    )

    agent: Agent[OrchestratorDeps, str] = Agent(
        model,
        deps_type=OrchestratorDeps,
        output_type=str,
        instructions=instructions,
        instrument=True,
        prepare_tools=_prepare_tools,
    )
    _register_core_tools(agent)
    _register_analysis_tools(agent)
    _register_mutation_tools(agent)
    _register_schedule_tool(agent)
    return agent
