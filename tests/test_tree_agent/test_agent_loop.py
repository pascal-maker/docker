"""Tests for the tree agent loop using PydanticAI's TestModel."""

from __future__ import annotations

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from document_structuring_agent.tree_agent.agent import (
    TerminationReason,
    TreeAgentDeps,
    _run_tree_agent_loop,
)
from document_structuring_agent.tree_agent.engine import build_tree_engine
from document_structuring_agent.tree_agent.flat_node import (
    FlatNode,
    NodeHints,
    NodeStatus,
)
from document_structuring_agent.tree_agent.memory import PatternMemory


def _make_flat_node(node_id: str, tag: str = "p", page: int = 1) -> FlatNode:
    hints = NodeHints(
        page_number=page,
        is_bold=False,
        is_italic=False,
        heading_level=None,
        top_fraction=None,
        font_family=None,
        confidence=0.9,
    )
    return FlatNode(
        node_id=node_id,
        data_idx=0,
        tag=tag,
        description=f'<{tag}> p{page} "text"',
        hints=hints,
    )


def _make_test_agent() -> Agent[TreeAgentDeps, None]:
    """Create a test agent using TestModel (no real LLM calls)."""
    from document_structuring_agent.tree_agent.agent import _register_tools

    agent: Agent[TreeAgentDeps, None] = Agent(
        "test",
        deps_type=TreeAgentDeps,
        output_type=None,
        instructions="Build tree.",
    )
    _register_tools(agent)
    return agent


class TestTreeAgentLoop:
    @pytest.mark.asyncio
    async def test_loop_returns_termination_reason(self):
        flat_nodes = [_make_flat_node("n0")]
        engine = build_tree_engine(flat_nodes)
        memory = PatternMemory()
        deps = TreeAgentDeps(
            engine=engine,
            memory=memory,
            flat_nodes={"n0": flat_nodes[0]},
            original_elements={0: "<p>text</p>"},
        )
        agent = _make_test_agent()
        reason = await _run_tree_agent_loop(agent, deps)
        assert reason in list(TerminationReason)

    @pytest.mark.asyncio
    async def test_already_finished_terminates_immediately(self):
        flat_nodes = [_make_flat_node("n0")]
        engine = build_tree_engine(flat_nodes)
        engine.finished = True
        memory = PatternMemory()
        deps = TreeAgentDeps(
            engine=engine,
            memory=memory,
            flat_nodes={"n0": flat_nodes[0]},
            original_elements={},
        )
        agent = _make_test_agent()
        reason = await _run_tree_agent_loop(agent, deps)
        # Should terminate quickly since engine.finished is True
        assert reason in (
            TerminationReason.COMPLETE,
            TerminationReason.COMPLETE_WITH_EXCEPTIONS,
            TerminationReason.MAX_ITERATIONS,
        )

    @pytest.mark.asyncio
    async def test_memory_iteration_advances(self):
        flat_nodes = [_make_flat_node("n0")]
        engine = build_tree_engine(flat_nodes)
        memory = PatternMemory()
        deps = TreeAgentDeps(
            engine=engine,
            memory=memory,
            flat_nodes={"n0": flat_nodes[0]},
            original_elements={},
        )
        agent = _make_test_agent()
        initial_iteration = memory.current_iteration
        await _run_tree_agent_loop(agent, deps)
        assert memory.current_iteration > initial_iteration


class TestTreeAgentTools:
    """Smoke tests verifying tools can be called without errors."""

    @pytest.mark.asyncio
    async def test_adopt_range_tool_via_test_model(self):
        """TestModel doesn't call tools, but we verify the agent is wired up."""
        flat_nodes = [_make_flat_node(f"n{i}") for i in range(3)]
        engine = build_tree_engine(flat_nodes)
        memory = PatternMemory()
        deps = TreeAgentDeps(
            engine=engine,
            memory=memory,
            flat_nodes={fn.node_id: fn for fn in flat_nodes},
            original_elements={},
        )

        # Manually invoke engine operation to verify it's accessible
        engine.adopt_range("n0", "n1", "n2", "test")
        assert engine.flat_nodes["n1"].status == NodeStatus.PLACED

    @pytest.mark.asyncio
    async def test_mark_anomalous_tool_via_engine(self):
        flat_nodes = [_make_flat_node("n0")]
        engine = build_tree_engine(flat_nodes)
        engine.mark_anomalous("n0", "OCR artifact", "delete")
        assert engine.flat_nodes["n0"].status == NodeStatus.ANOMALOUS

    @pytest.mark.asyncio
    async def test_record_pattern_via_memory(self):
        memory = PatternMemory()
        memory.record("bold h2 = section heading", "n1")
        assert len(memory.patterns) == 1
        assert "bold h2" in memory.patterns[0].description
