"""Chat-oriented PydanticAI agent for workspace-level refactoring."""

# NOTE: do NOT use `from __future__ import annotations` here.
# PydanticAI's @agent.tool decorator calls typing.get_type_hints() which
# needs RunContext resolvable at runtime, and `__future__.annotations`
# breaks this for nested (closure) functions.

from dataclasses import dataclass
from pathlib import Path

from anthropic import AsyncAnthropic
from pydantic_ai import Agent, ModelSettings, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from refactor_agent.config import DEFAULT_MODEL
from refactor_agent.engine.registry import EngineRegistry
from refactor_agent.engine.typescript.ts_morph_engine import (
    TsMorphProjectEngine,
)
from refactor_agent.observability.langfuse_config import get_prompt, get_prompt_config

_CHAT_PROMPT_NAME = "chat-agent"

# Single source of truth for tool names and one-line descriptions (used in prompt).
_CHAT_TOOL_OPERATIONS: list[tuple[str, str]] = [
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
]


def _format_available_operations() -> str:
    """Format tool operations for the chat agent prompt (Langfuse variable)."""
    return "\n".join(
        f"- {desc} using {name}." for name, desc in _CHAT_TOOL_OPERATIONS
    )


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


def _abs(deps: ChatDeps, rel_path: str) -> str:
    """Resolve a relative path to an absolute path within the workspace."""
    return str((deps.workspace / rel_path).resolve())


def _rel(deps: ChatDeps, abs_path: str) -> str:
    """Convert an absolute path to a relative path within the workspace."""
    try:
        return str(Path(abs_path).relative_to(deps.workspace))
    except ValueError:
        return abs_path


# ---------------------------------------------------------------------------
# Python per-file helpers (backward compat)
# ---------------------------------------------------------------------------


async def _check_all_collisions(
    deps: ChatDeps,
    files: list[Path],
    new_name: str,
    scope_node: str | None,
) -> list[str]:
    reports: list[str] = []
    for fp in files:
        source = fp.read_text(encoding="utf-8")
        try:
            engine = EngineRegistry.create(deps.language, source)
        except Exception:  # noqa: S112 — skip unparseable files
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
            engine = EngineRegistry.create(deps.language, source)
        except Exception:  # noqa: S112 — skip unparseable files
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


async def _rename_python(
    deps: ChatDeps,
    old_name: str,
    new_name: str,
    scope_node: str | None,
    force: bool,  # noqa: FBT001
) -> str:
    """Per-file rename for Python (backward compat)."""
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
            return (
                f"Collisions found for '{new_name}':\n"
                + "\n".join(collision_reports)
                + "\n\nAsk the user to confirm before "
                "proceeding with force=True."
            )

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


# ---------------------------------------------------------------------------
# TypeScript project-level helpers
# ---------------------------------------------------------------------------


async def _rename_typescript(
    deps: ChatDeps,
    old_name: str,
    new_name: str,
    scope_node: str | None,
) -> str:
    """Project-level rename for TypeScript via TsMorphProjectEngine."""
    files = _scan_workspace(deps)
    if not files:
        return "No files found in workspace."

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
    return f"Symbol '{old_name}' not found in any workspace file."


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def _register_core_tools(agent: Agent[ChatDeps, str]) -> None:
    """Register rename, list, and skeleton tools (all languages)."""

    @agent.tool
    async def rename_in_workspace(
        ctx: RunContext[ChatDeps],
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
        force: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        """Rename a symbol across all workspace files.

        Args:
            ctx: Agent run context (injected).
            old_name: Current symbol name.
            new_name: Desired new name.
            scope_node: Optional function/class to restrict scope.
            force: Proceed despite name collisions (Python only).
        """
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
        if ctx.deps.language == "typescript":
            async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                return await eng.get_skeleton(
                    _abs(ctx.deps, file_path),
                )

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


def _register_analysis_tools(agent: Agent[ChatDeps, str]) -> None:
    """Register TypeScript analysis tools (find references, diagnostics)."""

    @agent.tool
    async def find_references(
        ctx: RunContext[ChatDeps],
        file_path: str,
        symbol_name: str,
    ) -> str:
        """Find all references to a symbol across the project.

        Args:
            ctx: Agent run context (injected).
            file_path: Relative path of the file containing the symbol.
            symbol_name: Name of the symbol to search for.
        """
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

    @agent.tool
    async def show_diagnostics(
        ctx: RunContext[ChatDeps],
        file_path: str | None = None,
    ) -> str:
        """Show TypeScript diagnostics for a file or the project.

        Args:
            ctx: Agent run context (injected).
            file_path: Optional relative path to scope diagnostics.
        """
        abs_path = _abs(ctx.deps, file_path) if file_path else None
        async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
            diags = await eng.get_diagnostics(abs_path)
        if not diags:
            return "No diagnostics found."
        lines = [f"Found {len(diags)} diagnostic(s):"]
        for d in diags:
            rel = _rel(ctx.deps, d.file_path)
            lines.append(
                f"  [{d.severity}] {rel}:{d.line} — {d.message} (TS{d.code})",
            )
        return "\n".join(lines)


def _register_mutation_tools(agent: Agent[ChatDeps, str]) -> None:
    """Register TypeScript mutation tools (remove, move, format, etc.)."""

    @agent.tool
    async def remove_declaration(
        ctx: RunContext[ChatDeps],
        file_path: str,
        symbol_name: str,
        kind: str | None = None,
    ) -> str:
        """Remove a declaration from a file.

        Args:
            ctx: Agent run context (injected).
            file_path: Relative path of the file.
            symbol_name: Name of the declaration to remove.
            kind: Optional kind (function, class, interface, etc.).
        """
        async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
            result = await eng.remove_node(
                _abs(ctx.deps, file_path),
                symbol_name,
                kind,
            )
            if ctx.deps.mode != "Plan":
                await eng.apply_changes()
            return result

    @agent.tool
    async def move_symbol(
        ctx: RunContext[ChatDeps],
        source_file: str,
        target_file: str,
        symbol_name: str,
    ) -> str:
        """Move a declaration from one file to another.

        Args:
            ctx: Agent run context (injected).
            source_file: Relative path of the source file.
            target_file: Relative path of the target file.
            symbol_name: Name of the declaration to move.
        """
        async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
            result = await eng.move_symbol(
                _abs(ctx.deps, source_file),
                _abs(ctx.deps, target_file),
                symbol_name,
            )
            if ctx.deps.mode != "Plan":
                await eng.apply_changes()
            return result

    @agent.tool
    async def format_file(
        ctx: RunContext[ChatDeps],
        file_path: str,
    ) -> str:
        """Format a TypeScript file.

        Args:
            ctx: Agent run context (injected).
            file_path: Relative path of the file to format.
        """
        async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
            result = await eng.format_file(
                _abs(ctx.deps, file_path),
            )
            if ctx.deps.mode != "Plan":
                await eng.apply_changes()
            return result

    @agent.tool
    async def organize_imports(
        ctx: RunContext[ChatDeps],
        file_path: str,
    ) -> str:
        """Organize imports in a TypeScript file.

        Args:
            ctx: Agent run context (injected).
            file_path: Relative path of the file.
        """
        async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
            result = await eng.organize_imports(
                _abs(ctx.deps, file_path),
            )
            if ctx.deps.mode != "Plan":
                await eng.apply_changes()
            return result


def create_chat_agent() -> Agent[ChatDeps, str]:
    """Create the chat-oriented refactoring agent.

    Fetches prompt and config from Langfuse (same pattern as AST refactor agent).
    """
    config = get_prompt_config(_CHAT_PROMPT_NAME)
    model_str = config.model or DEFAULT_MODEL
    instructions = get_prompt(
        _CHAT_PROMPT_NAME,
        available_operations=_format_available_operations(),
    )

    model_id = model_str.split(":")[-1] if ":" in model_str else model_str
    model_settings = ModelSettings(max_tokens=config.max_tokens or 4096)
    provider = AnthropicProvider(anthropic_client=AsyncAnthropic(timeout=60.0))
    model = AnthropicModel(model_id, provider=provider, settings=model_settings)

    agent: Agent[ChatDeps, str] = Agent(
        model,
        deps_type=ChatDeps,
        output_type=str,
        instructions=instructions,
        instrument=True,
    )
    _register_core_tools(agent)
    _register_analysis_tools(agent)
    _register_mutation_tools(agent)
    return agent
