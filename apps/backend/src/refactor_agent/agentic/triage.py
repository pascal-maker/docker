"""Layer 2 Triage: classify refactor goal into trivial/structural/paradigm/ambiguous."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext  # noqa: TC002 — RunContext in tool ctx type
from pydantic_ai.models import (
    Model,  # noqa: TC002 — Model in create_triage_agent signature
)
from pydantic_ai.models.anthropic import (  # noqa: TC002
    AnthropicModel,
    AnthropicModelSettings,  # TypedDict for model_settings at runtime
)
from pydantic_ai.providers.anthropic import AnthropicProvider

from refactor_agent.config import AGENT_REQUEST_TIMEOUT, DEFAULT_MODEL
from refactor_agent.engine.registry import EngineRegistry
from refactor_agent.engine.subprocess_engine import SubprocessError
from refactor_agent.engine.typescript.ts_morph_engine import TsMorphProjectEngine
from refactor_agent.llm_client import get_anthropic_client
from refactor_agent.observability.langfuse_config import get_prompt, get_prompt_config
from refactor_agent.orchestrator.deps import OrchestratorDeps
from refactor_agent.schedule.models import ScopeSpec

_TRIAGE_PROMPT_NAME = "refactor-triage"
_TS_ONLY = "This tool is only available for TypeScript workspaces."
_CONFIDENCE_THRESHOLD = 0.7


class TriageResult(BaseModel):
    """Result of triage: category, confidence, and scope constraint envelope."""

    category: str = Field(
        description="One of: trivial, structural, paradigm_shift, ambiguous",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the classification (0.0 to 1.0).",
    )
    scope_spec: ScopeSpec = Field(
        default_factory=ScopeSpec,
        description="Affected files, allowed/forbidden op types for downstream.",
    )
    brief: str | None = Field(
        default=None,
        description="Optional short summary of scope and estimated impact.",
    )


def _scan_workspace(deps: OrchestratorDeps) -> list[Path]:
    """Return sorted workspace files matching the extension."""
    if not deps.workspace.exists():
        return []
    files = deps.workspace.rglob(deps.file_ext)
    return sorted(p for p in files if "node_modules" not in p.parts)


def _abs(deps: OrchestratorDeps, rel_path: str) -> str:
    """Resolve relative path to absolute."""
    return str((deps.workspace / rel_path).resolve())


def _rel(deps: OrchestratorDeps, abs_path: str) -> str:
    """Resolve absolute path to workspace-relative."""
    try:
        return str(Path(abs_path).relative_to(deps.workspace))
    except ValueError:
        return abs_path


def _register_triage_tools(  # noqa: C901 — multiple tools with language guards
    agent: Agent[OrchestratorDeps, TriageResult],
) -> None:
    """Register read-only tools for the triage agent."""

    @agent.tool
    async def list_workspace_files(ctx: RunContext[OrchestratorDeps]) -> str:
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
        full = ctx.deps.workspace / file_path
        if not full.exists():
            return f"File not found: {file_path}"

        if ctx.deps.language == "typescript":
            try:
                async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                    return await eng.get_skeleton(_abs(ctx.deps, file_path))
            except SubprocessError as exc:
                return f"ERROR: get_skeleton failed for {file_path}: {exc}"
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
        try:
            async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                refs = await eng.find_references(
                    _abs(ctx.deps, file_path),
                    symbol_name,
                )
        except SubprocessError as exc:
            return f"ERROR: find_references ({symbol_name!r}): {exc}"
        if not refs:
            return f"No references found for '{symbol_name}'."
        lines = [f"Found {len(refs)} reference(s) for '{symbol_name}':"]
        for ref in refs:
            tag = " [definition]" if ref.is_definition else ""
            rel = _rel(ctx.deps, ref.file_path)
            lines.append(f"  {rel}:{ref.line}:{ref.column}{tag} — {ref.text}")
        return "\n".join(lines)

    @agent.tool
    async def get_reference_count(
        ctx: RunContext[OrchestratorDeps],
        file_path: str,
        symbol_name: str,
    ) -> str:
        """Return the number of references to a symbol (TypeScript only).

        Use for quick classification: e.g. > 10 refs suggests structural.
        """
        if ctx.deps.language != "typescript":
            return _TS_ONLY
        try:
            async with TsMorphProjectEngine(ctx.deps.workspace) as eng:
                refs = await eng.find_references(
                    _abs(ctx.deps, file_path),
                    symbol_name,
                )
        except SubprocessError as exc:
            return f"ERROR: {exc}"
        return f"{len(refs)} reference(s) for '{symbol_name}'"


_TRIAGE_INSTRUCTIONS = """
You are a refactor triage agent. Given a user goal (e.g. "rename X to Y", "move
module to feature slice"), classify the refactor type:

- **trivial**: Rename symbol, move single file, no cross-cutting concerns. Few refs.
- **structural**: Move module/directory, update imports across many files. Many refs.
- **paradigm_shift**: DDD → vertical slice, major architectural change.
- **ambiguous**: User knows something is wrong but not what.

Use tools to inspect the codebase: list_workspace_files, show_file_skeleton,
find_references, get_reference_count. "Rename X" with 200 refs -> structural.

Output a TriageResult with:
- category: trivial | structural | paradigm_shift | ambiguous
- confidence: 0.0 to 1.0
- affected_files: list of file paths likely to be touched (can be empty if unsure)
- allowed_op_types: e.g. ["rename", "move_file", "organize_imports"]
- forbidden_op_types: e.g. ["create_file"] if not in scope
- brief: optional short summary

When confidence < 0.7, lean toward the more complex category (trivial→structural,
structural→paradigm_shift).
"""


def create_triage_agent(
    model: Model | None = None,
    instructions_override: str | None = None,
) -> Agent[OrchestratorDeps, TriageResult]:
    """Create the triage agent with read-only tools."""
    if model is None:
        config = get_prompt_config(_TRIAGE_PROMPT_NAME)
        model_str = config.model or DEFAULT_MODEL
        model_id = model_str.split(":")[-1] if ":" in model_str else model_str
        model_settings: AnthropicModelSettings = {
            "max_tokens": config.max_tokens or 4096,
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
    instructions = (
        instructions_override
        if instructions_override is not None
        else get_prompt(_TRIAGE_PROMPT_NAME) or _TRIAGE_INSTRUCTIONS
    )
    agent: Agent[OrchestratorDeps, TriageResult] = Agent(
        model,
        deps_type=OrchestratorDeps,
        output_type=TriageResult,
        instructions=instructions,
    )
    _register_triage_tools(agent)
    return agent


def _apply_confidence_rounding(result: TriageResult) -> TriageResult:
    """Round up to more complex category when confidence < threshold."""
    if result.confidence >= _CONFIDENCE_THRESHOLD:
        return result
    if result.category == "trivial":
        return result.model_copy(update={"category": "structural"})
    if result.category == "structural":
        return result.model_copy(update={"category": "paradigm_shift"})
    return result


async def run_triage(
    goal: str,
    deps: OrchestratorDeps,
    agent: Agent[OrchestratorDeps, TriageResult] | None = None,
) -> TriageResult:
    """Run triage on goal; return TriageResult with confidence rounding applied."""
    triage_agent = agent or create_triage_agent()
    run = await triage_agent.run(
        f"Classify this refactor goal: {goal!r}",
        deps=deps,
    )
    raw = run.output
    if not isinstance(raw, TriageResult):
        raise TriageError("Triage agent did not return TriageResult")
    return _apply_confidence_rounding(raw)


class TriageError(Exception):
    """Raised when triage fails or returns invalid output."""
