"""Tree agent: PydanticAI agent with tree operator tools and iterative loop.

The agent is given a skeleton XML view of the current tree state and emits
tree operator tool calls to restructure unplaced nodes. This continues until
all nodes are placed (or marked uncertain/anomalous) or the stuck threshold
is exceeded.

The agent loop accumulates message_history across iterations so the LLM
maintains context without re-discovering patterns each step.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from anthropic import AsyncAnthropic
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.settings import ModelSettings

from document_structuring_agent.config import DEFAULT_MODEL
from document_structuring_agent.langfuse_config import get_prompt, get_prompt_config
from document_structuring_agent.logger import logger
from document_structuring_agent.models.document import StructuredDocument
from document_structuring_agent.models.ocr_input import OcrDocument
from document_structuring_agent.preprocessing.html_parser import parse_ocr_html
from document_structuring_agent.tree_agent.converter import (
    tree_engine_to_structured_document,
)
from document_structuring_agent.tree_agent.engine import (
    TreeEngine,
    TreeEngineError,
    build_tree_engine,
)
from document_structuring_agent.tree_agent.flat_node import FlatNode, convert_to_flat_nodes
from document_structuring_agent.tree_agent.memory import PatternMemory
from document_structuring_agent.tree_agent.serializer import build_skeleton_xml

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage

_MAX_ITERATIONS = 20
_STUCK_THRESHOLD = 3
_PROMPT_NAME = "tree-agent"


class TerminationReason(StrEnum):
    """Reason the tree agent loop terminated."""

    COMPLETE = "complete"
    COMPLETE_WITH_EXCEPTIONS = "complete_with_exceptions"
    STUCK = "stuck"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class TreeAgentDeps:
    """Dependencies injected into every tree agent tool call."""

    engine: TreeEngine
    memory: PatternMemory
    flat_nodes: dict[str, FlatNode]
    original_elements: dict[int, str]


# ---------------------------------------------------------------------------
# Agent definition (module-level singleton, created lazily via factory)
# ---------------------------------------------------------------------------

def create_tree_agent() -> Agent[TreeAgentDeps, None]:
    """Create the iterative tree-building agent.

    Follows the same factory pattern as other agents in this project.
    Fetches prompt and config from Langfuse, uses AnthropicProvider with
    no timeout for long-running agentic sessions.
    """
    config = get_prompt_config(_PROMPT_NAME)
    model_str = config.model or DEFAULT_MODEL
    instructions = get_prompt(_PROMPT_NAME)

    model_id = model_str.split(":")[-1] if ":" in model_str else model_str
    model_settings = ModelSettings(max_tokens=config.max_tokens or 60000)
    provider = AnthropicProvider(anthropic_client=AsyncAnthropic(timeout=None))
    model = AnthropicModel(model_id, provider=provider, settings=model_settings)

    agent: Agent[TreeAgentDeps, None] = Agent(
        model,
        deps_type=TreeAgentDeps,
        output_type=None,
        instructions=instructions,
    )

    _register_tools(agent)
    return agent


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def _register_tools(agent: Agent[TreeAgentDeps, None]) -> None:
    """Register all tree operator tools on the given agent instance."""

    @agent.tool
    async def adopt_range(
        ctx: RunContext[TreeAgentDeps],
        parent_id: str,
        first_child_id: str,
        last_child_id: str,
        reasoning: str,
    ) -> str:
        """Make a contiguous range of sibling nodes children of parent_id.

        Args:
            parent_id: The node that will become the parent.
            first_child_id: First node in the range (inclusive).
            last_child_id: Last node in the range (inclusive).
            reasoning: Why these nodes belong under this parent.
        """
        try:
            count = ctx.deps.engine.adopt_range(
                parent_id, first_child_id, last_child_id, reasoning
            )
            return f"OK: {count} node(s) adopted under {parent_id!r}"
        except TreeEngineError as exc:
            return f"ERROR: {exc}"

    @agent.tool
    async def promote(
        ctx: RunContext[TreeAgentDeps],
        node_id: str,
        reasoning: str,
    ) -> str:
        """Move a node up one level, past its current parent.

        Args:
            node_id: The node to promote.
            reasoning: Why this node should be at a higher level.
        """
        try:
            ctx.deps.engine.promote(node_id, reasoning)
            return f"OK: {node_id!r} promoted"
        except TreeEngineError as exc:
            return f"ERROR: {exc}"

    @agent.tool
    async def demote_range(
        ctx: RunContext[TreeAgentDeps],
        first_child_id: str,
        last_child_id: str,
        new_parent_id: str,
        reasoning: str,
    ) -> str:
        """Push a contiguous range of siblings under new_parent_id.

        Args:
            first_child_id: First node in the range (inclusive).
            last_child_id: Last node in the range (inclusive).
            new_parent_id: The node that will become the new parent.
            reasoning: Why these nodes should be nested deeper.
        """
        try:
            count = ctx.deps.engine.demote_range(
                first_child_id, last_child_id, new_parent_id, reasoning
            )
            return f"OK: {count} node(s) demoted under {new_parent_id!r}"
        except TreeEngineError as exc:
            return f"ERROR: {exc}"

    @agent.tool
    async def swap_siblings(
        ctx: RunContext[TreeAgentDeps],
        node_a: str,
        node_b: str,
        reasoning: str,
    ) -> str:
        """Swap the positions of two siblings within the same parent.

        Args:
            node_a: First node to swap.
            node_b: Second node to swap.
            reasoning: Why these nodes should be reordered.
        """
        try:
            ctx.deps.engine.swap_siblings(node_a, node_b, reasoning)
            return f"OK: swapped {node_a!r} and {node_b!r}"
        except TreeEngineError as exc:
            return f"ERROR: {exc}"

    @agent.tool
    async def mark_uncertain(
        ctx: RunContext[TreeAgentDeps],
        node_id: str,
        reasoning: str,
    ) -> str:
        """Flag a node whose placement is uncertain.

        Use when you have placed a node but are not confident it is correct.
        The node will be flagged for review in the output.

        Args:
            node_id: The node to flag.
            reasoning: Why the placement is uncertain.
        """
        try:
            ctx.deps.engine.mark_uncertain(node_id, reasoning)
            return f"OK: {node_id!r} marked uncertain"
        except TreeEngineError as exc:
            return f"ERROR: {exc}"

    @agent.tool
    async def mark_anomalous(
        ctx: RunContext[TreeAgentDeps],
        node_id: str,
        reasoning: str,
        suggested_action: str,
    ) -> str:
        """Flag a node that does not fit anywhere in the document structure.

        Use for nodes that are clearly misplaced, OCR artifacts, or otherwise
        don't belong. Prefer this over forcing a bad placement.

        Args:
            node_id: The node to flag.
            reasoning: Why this node doesn't fit the document structure.
            suggested_action: What a human reviewer should do (e.g. 'human_review',
                'delete', 'move_to_appendix').
        """
        try:
            ctx.deps.engine.mark_anomalous(node_id, reasoning, suggested_action)
            return f"OK: {node_id!r} marked anomalous"
        except TreeEngineError as exc:
            return f"ERROR: {exc}"

    @agent.tool
    async def record_pattern(
        ctx: RunContext[TreeAgentDeps],
        description: str,
        example_node_id: str,
    ) -> str:
        """Save a confirmed structural rule to session memory.

        Call when you confirm a reliable rule about this document's structure
        so it can guide future iterations.

        Args:
            description: Human-readable pattern, e.g. 'bold h2 = section heading'.
            example_node_id: The node ID that confirmed this pattern.
        """
        ctx.deps.memory.record(description, example_node_id)
        return f"OK: pattern recorded — {description!r}"

    @agent.tool
    async def read_nodes(
        ctx: RunContext[TreeAgentDeps],
        node_ids: list[str],
    ) -> str:
        """Peek at the full HTML content of specific nodes.

        Use sparingly — only when the description and hints in the skeleton
        are insufficient to determine correct placement.

        Args:
            node_ids: List of node IDs to read content for.
        """
        parts: list[str] = []
        for nid in node_ids:
            fn = ctx.deps.flat_nodes.get(nid)
            if fn is None:
                parts.append(f"<!-- {nid}: not found -->")
                continue
            if fn.data_idx is None:
                parts.append(f"<!-- {nid}: no data_idx -->")
                continue
            html = ctx.deps.original_elements.get(fn.data_idx, "(no html)")
            parts.append(f"<!-- {nid} -->\n{html}")
        return "\n\n".join(parts)

    @agent.tool
    async def finish(
        ctx: RunContext[TreeAgentDeps],
        summary: str,
    ) -> str:
        """Signal that tree construction is complete.

        Call when all nodes are placed, marked uncertain, or marked anomalous.

        Args:
            summary: Brief summary of what was built and any notable decisions.
        """
        ctx.deps.engine.finished = True
        ctx.deps.engine.finish_summary = summary
        return f"OK: session complete — {summary}"


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def _build_iteration_prompt(
    skeleton_xml: str,
    stats_total: int,
    stats_placed: int,
    stats_unplaced: int,
    stats_uncertain: int,
    stats_anomalous: int,
    patterns_block: str,
    iteration: int,
) -> str:
    """Build the per-iteration user message for the agent."""
    return (
        f"=== Iteration {iteration + 1} / {_MAX_ITERATIONS} ===\n"
        f"Progress: {stats_placed}/{stats_total} placed,"
        f" {stats_unplaced} unplaced,"
        f" {stats_uncertain} uncertain,"
        f" {stats_anomalous} anomalous\n\n"
        f"Confirmed patterns:\n{patterns_block}\n\n"
        f"Current tree skeleton:\n{skeleton_xml}\n\n"
        "Use tree operator tools to place unplaced nodes. "
        "Call finish() when all nodes are placed or marked."
    )


async def _run_tree_agent_loop(
    agent: Agent[TreeAgentDeps, None],
    deps: TreeAgentDeps,
) -> TerminationReason:
    """Run the tree agent iteratively until a termination condition is met.

    Each iteration the agent receives a skeleton XML view plus progress
    summary and emits tree operator tool calls. Message history is
    accumulated across iterations so the LLM maintains context.

    Args:
        agent: Configured tree agent instance.
        deps: Dependencies including the mutable TreeEngine and PatternMemory.

    Returns:
        The reason the loop terminated.
    """
    message_history: list[ModelMessage] = []

    for iteration in range(_MAX_ITERATIONS):
        deps.memory.advance_iteration()
        stats = deps.engine.progress_stats

        if deps.engine.finished or stats.unplaced == 0:
            break

        if deps.engine.stuck_count >= _STUCK_THRESHOLD:
            logger.warning(
                "tree_agent stuck after %d iterations with %d unplaced nodes",
                iteration,
                stats.unplaced,
            )
            return TerminationReason.STUCK

        skeleton = build_skeleton_xml(deps.engine)
        patterns_block = deps.memory.to_prompt_block()
        prompt = _build_iteration_prompt(
            skeleton_xml=skeleton,
            stats_total=stats.total,
            stats_placed=stats.placed,
            stats_unplaced=stats.unplaced,
            stats_uncertain=stats.uncertain,
            stats_anomalous=stats.anomalous,
            patterns_block=patterns_block,
            iteration=iteration,
        )

        result = await agent.run(prompt, deps=deps, message_history=message_history)
        message_history = result.all_messages()

        deps.engine.update_stuck_count()

        logger.debug(
            "tree_agent iteration=%d placed=%d unplaced=%d",
            iteration + 1,
            deps.engine.progress_stats.placed,
            deps.engine.progress_stats.unplaced,
        )

    final_stats = deps.engine.progress_stats
    if final_stats.unplaced > 0:
        return TerminationReason.MAX_ITERATIONS
    if final_stats.uncertain > 0 or final_stats.anomalous > 0:
        return TerminationReason.COMPLETE_WITH_EXCEPTIONS
    return TerminationReason.COMPLETE


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_tree_agent(ocr_document: OcrDocument) -> StructuredDocument:
    """Process an OCR document using the iterative tree agent approach.

    Alternative to the prompt-pipeline. Accepts OcrDocument and returns
    StructuredDocument for compatibility. The existing pipeline is not
    affected.

    Args:
        ocr_document: OCR-processed document with HTML and element metadata.

    Returns:
        StructuredDocument containing the inferred hierarchical tree.
    """
    from document_structuring_agent.langfuse_config import init_langfuse

    init_langfuse()

    elements = parse_ocr_html(ocr_document.html, ocr_document.element_metadata)
    flat_nodes = convert_to_flat_nodes(elements)

    original_elements: dict[int, str] = {
        e.data_idx: e.html for e in elements if e.data_idx is not None
    }

    engine = build_tree_engine(flat_nodes)
    memory = PatternMemory()

    agent = create_tree_agent()
    deps = TreeAgentDeps(
        engine=engine,
        memory=memory,
        flat_nodes={fn.node_id: fn for fn in flat_nodes},
        original_elements=original_elements,
    )

    reason = await _run_tree_agent_loop(agent, deps)
    logger.info(
        "tree_agent finished reason=%s placed=%d unplaced=%d",
        reason,
        engine.progress_stats.placed,
        engine.progress_stats.unplaced,
    )

    return tree_engine_to_structured_document(engine, ocr_document.source_filename)
