"""Planner agent: produces RefactorSchedule from a user goal (read-only tools)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from langfuse import propagate_attributes
from pydantic_ai import (
    Agent,
    CallToolsNode,
    ModelRequestNode,
    RunContext,
)
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_graph import End

from refactor_agent.config import DEFAULT_MODEL
from refactor_agent.engine.registry import EngineRegistry
from refactor_agent.engine.subprocess_engine import SubprocessError
from refactor_agent.engine.typescript.ts_morph_engine import TsMorphProjectEngine
from refactor_agent.llm_client import get_anthropic_client
from refactor_agent.observability.langfuse_config import (
    LangfuseMetadata,
    get_prompt,
    get_prompt_config,
    get_prompt_name_and_version,
    langfuse_span,
)
from refactor_agent.orchestrator.deps import OrchestratorDeps, PlannerBudgetRef
from refactor_agent.schedule.codebase_structure import build_codebase_structure
from refactor_agent.schedule.limits import (
    DEFAULT_PLANNER_MAX_TOKENS,
    MAX_CODEBASE_STRUCTURE_CHARS,
    MAX_PLANNER_LLM_ROUNDS,
    MAX_PLANNER_TOOL_CALLS_PER_RUN,
    PLANNER_REQUEST_TIMEOUT,
)
from refactor_agent.schedule.models import RefactorSchedule
from refactor_agent.schedule.operation_descriptions import (
    build_operation_types_documentation,
)

_PLANNER_PROMPT_NAME = "refactor-planner"
_TS_ONLY = "This tool is only available for TypeScript workspaces."


def _scan_workspace(deps: OrchestratorDeps) -> list[Path]:
    if not deps.workspace.exists():
        return []
    files = deps.workspace.rglob(deps.file_ext)
    return sorted(p for p in files if "node_modules" not in p.parts)


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
            lines.append(
                f"  {rel}:{ref.line}:{ref.column}{tag} — {ref.text}",
            )
        return "\n".join(lines)

    @agent.tool
    async def get_planning_budget(ctx: RunContext[OrchestratorDeps]) -> str:
        """Return remaining tool-call and LLM-round budget for this planner run.

        Call this to decide whether to output the RefactorSchedule soon or use
        more tools. Prefer outputting the schedule when budget is low.
        """
        ref = ctx.deps.planner_budget_ref
        if ref is None:
            return (
                f"Budget: at most {MAX_PLANNER_TOOL_CALLS_PER_RUN} tool calls and "
                f"{MAX_PLANNER_LLM_ROUNDS} LLM rounds. Prefer outputting the "
                "RefactorSchedule soon."
            )
        tool_remaining = max(
            0,
            MAX_PLANNER_TOOL_CALLS_PER_RUN - ref.tool_calls,
        )
        rounds_remaining = max(
            0,
            MAX_PLANNER_LLM_ROUNDS - ref.llm_rounds,
        )
        return (
            f"Tool calls remaining: {tool_remaining}, LLM rounds remaining: "
            f"{rounds_remaining}. Prefer outputting the RefactorSchedule soon."
        )


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
- move_symbol: source_file, target_file, symbol_name — move one declaration between
  files (use when extracting a single symbol from a multi-symbol file)
- move_file: source_path, target_path — move an entire file to a new path. Updates
  all import paths across the project automatically. Parent directories are created
  on write. Prefer move_file over move_symbol when the whole file should relocate.
- remove_node: file_path, symbol_name, optional kind, id, dependsOn, rationale
- organize_imports: file_path — sort and remove unused imports in a file
- create_file: file_path, content — create a new file with the given content. Use
  only for files that need actual content (e.g. barrel index.ts, new modules). Do
  NOT use create_file just to create directories; move_file creates parent dirs.

All ops support optional id, dependsOn, rationale. Use "id" for a stable op
identifier. Use "dependsOn" (list of op ids) when an op must run after others
(e.g. organize_imports after move_file). Paths are relative to workspace root.

Output only a valid RefactorSchedule. Structural refactors only (rename, move
symbol, move file, remove node, organize imports, create file); no logic changes.
"""


class PlannerLimitExceededError(Exception):
    """Raised when the planner hits max tool calls or max LLM rounds."""

    def __init__(
        self,
        *,
        tool_calls: int,
        llm_rounds: int,
    ) -> None:
        self.tool_calls = tool_calls
        self.llm_rounds = llm_rounds
        super().__init__(
            "Planner exceeded max tool calls or max rounds; "
            "try a smaller workspace or a simpler goal."
        )


@dataclass
class PlannerRunResult:
    """Result of a planner run; partial=True when the run hit the budget limit."""

    schedule: RefactorSchedule
    partial: bool = False


def _last_assistant_text(messages: list[object]) -> str | None:
    """Return the concatenated text from the last model response message, or None."""
    # PydanticAI message/part types (untyped in our deps).
    for msg in reversed(messages):
        if type(msg).__name__ != "ModelResponse":
            continue
        parts = getattr(msg, "parts", [])
        texts: list[str] = []
        for part in parts:
            if type(part).__name__ == "TextPart":
                content = getattr(part, "content", None) or getattr(part, "text", None)
                if isinstance(content, str) and content.strip():
                    texts.append(content)
        if texts:
            return "\n".join(texts)
    return None


def _extract_json_object(text: str) -> str | None:
    """Extract a single JSON object from text (handles markdown fences, truncation)."""
    text = text.strip()
    # Strip markdown code block if present.
    fence = re.search(r"^```(?:json)?\s*\n?", text)
    if fence:
        text = text[fence.end() :].strip()
    end_fence = text.rfind("```")
    if end_fence != -1:
        text = text[:end_fence].strip()
    # Find first { and matching }.
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _parse_schedule_from_text(text: str) -> RefactorSchedule | None:
    """Try to parse a RefactorSchedule from assistant text. Returns None on failure."""
    raw = _extract_json_object(text)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    try:
        return RefactorSchedule.model_validate(data)
    except Exception:
        return None


def create_planner_agent(
    model: Model | None = None,
    instructions_override: str | None = None,
) -> Agent[OrchestratorDeps, RefactorSchedule]:
    """Create planner agent (structured output RefactorSchedule, read-only tools).

    When instructions_override is provided (e.g. from get_prompt with codebase
    structure), it is used as the agent instructions; otherwise the default
    static instructions are used.
    """
    if model is None:
        config = get_prompt_config(_PLANNER_PROMPT_NAME)
        model_str = config.model or DEFAULT_MODEL
        model_id = model_str.split(":")[-1] if ":" in model_str else model_str
        model_settings: AnthropicModelSettings = {
            "max_tokens": config.max_tokens or DEFAULT_PLANNER_MAX_TOKENS,
            "anthropic_cache_instructions": True,
            "anthropic_cache_tool_definitions": True,
        }
        provider = AnthropicProvider(
            anthropic_client=get_anthropic_client(timeout=PLANNER_REQUEST_TIMEOUT),
        )
        model = AnthropicModel(
            model_id,
            provider=provider,
            settings=model_settings,
        )

    instructions = (
        instructions_override
        if instructions_override is not None
        else _PLANNER_INSTRUCTIONS
    )
    agent: Agent[OrchestratorDeps, RefactorSchedule] = Agent(
        model,
        deps_type=OrchestratorDeps,
        output_type=RefactorSchedule,
        instructions=instructions,
        instrument=True,
    )
    _register_planner_tools(agent)
    return agent


def _count_tool_calls(node: object) -> int:
    """Return the number of tool invocations in a CallToolsNode."""
    # PydanticAI graph node (untyped).
    results = getattr(node, "tool_call_results", None)
    if results is None:
        return 0
    return len(results) if isinstance(results, dict) else 0


def _try_partial_on_limit(
    run: object,
    span: object,
    tool_calls: int,
    llm_rounds: int,
) -> PlannerRunResult:
    """Try to parse a partial schedule from the last message; return or raise."""
    # PydanticAI run and Langfuse span (untyped).
    all_messages = getattr(run, "all_messages", None)
    messages = (all_messages() if callable(all_messages) else []) or []
    last_text = _last_assistant_text(messages)
    partial_schedule = _parse_schedule_from_text(last_text) if last_text else None
    if partial_schedule is not None:
        update_fn = getattr(span, "update", None)  # Langfuse span (untyped)
        if callable(update_fn):
            update_fn(
                output={
                    "goal": partial_schedule.goal,
                    "operation_count": len(partial_schedule.operations),
                    "operation_types": [op.op for op in partial_schedule.operations],
                    "partial": True,
                },
            )
        return PlannerRunResult(schedule=partial_schedule, partial=True)
    raise PlannerLimitExceededError(
        tool_calls=tool_calls,
        llm_rounds=llm_rounds,
    )


async def run_planner(
    _agent: Agent[OrchestratorDeps, RefactorSchedule],
    deps: OrchestratorDeps,
    user_message: str,
) -> PlannerRunResult:
    """Run the planner agent and return the validated RefactorSchedule.

    Builds codebase structure, injects it via the refactor-planner prompt, and
    runs with hard limits on tool calls and LLM rounds. When a limit is exceeded,
    tries to parse a partial RefactorSchedule from the last model output and
    returns it with partial=True; otherwise raises PlannerLimitExceededError.
    """
    codebase_structure = await build_codebase_structure(deps)
    if len(codebase_structure) > MAX_CODEBASE_STRUCTURE_CHARS:
        codebase_structure = (
            codebase_structure[:MAX_CODEBASE_STRUCTURE_CHARS]
            + "\n\n(truncated; structure may be incomplete)"
        )
    operation_types = build_operation_types_documentation()
    instructions = get_prompt(
        _PLANNER_PROMPT_NAME,
        codebase_structure=codebase_structure,
        operation_types=operation_types,
    )
    budget_note = (
        f"\n\nBudget: at most {MAX_PLANNER_TOOL_CALLS_PER_RUN} tool calls and "
        f"{MAX_PLANNER_LLM_ROUNDS} LLM rounds. Call get_planning_budget to check "
        "remaining; prefer outputting the RefactorSchedule early."
    )
    instructions = instructions + budget_note
    planner_agent = create_planner_agent(instructions_override=instructions)
    prompt_name, prompt_version = get_prompt_name_and_version(_PLANNER_PROMPT_NAME)
    span_metadata = LangfuseMetadata(
        prompt_name=prompt_name,
        **({"prompt_version": prompt_version} if prompt_version is not None else {}),
    )

    budget_ref = PlannerBudgetRef()
    deps.planner_budget_ref = budget_ref

    with langfuse_span(
        "refactor-planner",
        as_type="agent",
        span_input=user_message,
        metadata=span_metadata,
    ) as span:
        tool_calls = 0
        llm_rounds = 0
        with propagate_attributes(metadata={"prompt_name": prompt_name}):
            async with planner_agent.iter(user_message, deps=deps) as run:
                node = run.next_node
                while not isinstance(node, End):
                    next_node = await run.next(node)
                    if isinstance(node, ModelRequestNode):
                        llm_rounds += 1
                    elif isinstance(node, CallToolsNode):
                        tool_calls += _count_tool_calls(node)
                    budget_ref.tool_calls = tool_calls
                    budget_ref.llm_rounds = llm_rounds
                    if (
                        tool_calls > MAX_PLANNER_TOOL_CALLS_PER_RUN
                        or llm_rounds > MAX_PLANNER_LLM_ROUNDS
                    ):
                        return _try_partial_on_limit(run, span, tool_calls, llm_rounds)
                    node = next_node

                result = run.result
                if result is None:
                    raise PlannerLimitExceededError(
                        tool_calls=tool_calls,
                        llm_rounds=llm_rounds,
                    )
                schedule = result.output
                span.update(
                    output={
                        "goal": schedule.goal,
                        "operation_count": len(schedule.operations),
                        "operation_types": [op.op for op in schedule.operations],
                    },
                )
                return PlannerRunResult(schedule=schedule, partial=False)
