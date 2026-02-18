"""Tests for TreeEngine operators and invariants."""

from __future__ import annotations

import pytest

from document_structuring_agent.tree_agent.engine import (
    TreeEngine,
    TreeEngineError,
    build_tree_engine,
)
from document_structuring_agent.tree_agent.flat_node import (
    FlatNode,
    NodeHints,
    NodeStatus,
)


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
        data_idx=None,
        tag=tag,
        description=f"<{tag}> p{page}",
        hints=hints,
    )


def _make_engine(n: int) -> tuple[TreeEngine, list[FlatNode]]:
    """Build a TreeEngine with n nodes n0..n{n-1}."""
    nodes = [_make_flat_node(f"n{i}") for i in range(n)]
    engine = build_tree_engine(nodes)
    return engine, nodes


class TestBuildTreeEngine:
    def test_all_nodes_unplaced_at_init(self):
        engine, nodes = _make_engine(3)
        for fn in engine.flat_nodes.values():
            assert fn.status == NodeStatus.UNPLACED

    def test_all_nodes_children_of_root(self):
        engine, _ = _make_engine(3)
        root_tn = engine.tree_nodes[engine.root_id]
        assert root_tn.children == ["n0", "n1", "n2"]

    def test_each_node_parent_is_root(self):
        engine, _ = _make_engine(3)
        for i in range(3):
            assert engine.tree_nodes[f"n{i}"].parent_id == engine.root_id

    def test_empty_engine(self):
        engine = build_tree_engine([])
        assert engine.flat_nodes == {}
        stats = engine.progress_stats
        assert stats.total == 0


class TestAdoptRange:
    def test_basic_adopt(self):
        engine, _ = _make_engine(4)
        count = engine.adopt_range("n0", "n1", "n2", "because")
        assert count == 2
        assert engine.tree_nodes["n1"].parent_id == "n0"
        assert engine.tree_nodes["n2"].parent_id == "n0"
        assert engine.tree_nodes["n0"].children == ["n1", "n2"]

    def test_adopted_nodes_marked_placed(self):
        engine, _ = _make_engine(3)
        engine.adopt_range("n0", "n1", "n2", "reason")
        assert engine.flat_nodes["n1"].status == NodeStatus.PLACED
        assert engine.flat_nodes["n2"].status == NodeStatus.PLACED

    def test_single_node_adopt(self):
        engine, _ = _make_engine(3)
        count = engine.adopt_range("n0", "n1", "n1", "reason")
        assert count == 1

    def test_parent_not_in_range_raises(self):
        engine, _ = _make_engine(4)
        with pytest.raises(TreeEngineError, match="inside the range"):
            engine.adopt_range("n1", "n0", "n2", "reason")

    def test_non_sibling_raises(self):
        engine, _ = _make_engine(4)
        # First adopt n1 under n0
        engine.adopt_range("n0", "n1", "n1", "reason")
        # Now n1 is under n0, n2 is still under root — they are not siblings
        with pytest.raises(TreeEngineError, match="not siblings"):
            engine.adopt_range("n0", "n1", "n2", "reason")

    def test_reversed_range_raises(self):
        engine, _ = _make_engine(4)
        with pytest.raises(TreeEngineError, match="reversed"):
            engine.adopt_range("n0", "n2", "n1", "reason")

    def test_nonexistent_parent_raises(self):
        engine, _ = _make_engine(2)
        with pytest.raises(TreeEngineError, match="does not exist"):
            engine.adopt_range("n99", "n0", "n1", "reason")


class TestPromote:
    def test_basic_promote(self):
        engine, _ = _make_engine(3)
        # n0 adopts n1 first
        engine.adopt_range("n0", "n1", "n1", "reason")
        # n1 is now under n0; promote it back to root level
        engine.promote("n1", "reason")
        # n1 should now be sibling of n0
        root_children = engine.tree_nodes[engine.root_id].children
        assert "n1" in root_children

    def test_promote_root_child_raises(self):
        engine, _ = _make_engine(2)
        with pytest.raises(TreeEngineError, match="already a direct child of root"):
            engine.promote("n0", "reason")

    def test_nonexistent_node_raises(self):
        engine, _ = _make_engine(2)
        with pytest.raises(TreeEngineError, match="does not exist"):
            engine.promote("n99", "reason")


class TestDemoteRange:
    def test_basic_demote(self):
        engine, _ = _make_engine(4)
        count = engine.demote_range("n1", "n2", "n0", "reason")
        assert count == 2
        assert engine.tree_nodes["n1"].parent_id == "n0"
        assert engine.tree_nodes["n2"].parent_id == "n0"

    def test_new_parent_in_range_raises(self):
        engine, _ = _make_engine(4)
        with pytest.raises(TreeEngineError, match="inside the range"):
            engine.demote_range("n0", "n2", "n1", "reason")


class TestSwapSiblings:
    def test_basic_swap(self):
        engine, _ = _make_engine(3)
        root_children = engine.tree_nodes[engine.root_id].children
        assert root_children == ["n0", "n1", "n2"]
        engine.swap_siblings("n0", "n1", "reason")
        assert root_children == ["n1", "n0", "n2"]

    def test_non_siblings_raises(self):
        engine, _ = _make_engine(3)
        engine.adopt_range("n0", "n1", "n1", "reason")
        with pytest.raises(TreeEngineError, match="not siblings"):
            engine.swap_siblings("n1", "n2", "reason")


class TestMarkUncertain:
    def test_sets_status_and_reason(self):
        engine, _ = _make_engine(2)
        engine.mark_uncertain("n0", "not sure where this goes")
        fn = engine.flat_nodes["n0"]
        assert fn.status == NodeStatus.UNCERTAIN
        assert fn.uncertainty_reason == "not sure where this goes"

    def test_nonexistent_node_raises(self):
        engine, _ = _make_engine(2)
        with pytest.raises(TreeEngineError, match="does not exist"):
            engine.mark_uncertain("n99", "reason")


class TestMarkAnomalous:
    def test_sets_status_and_fields(self):
        engine, _ = _make_engine(2)
        engine.mark_anomalous("n1", "OCR artifact", "delete")
        fn = engine.flat_nodes["n1"]
        assert fn.status == NodeStatus.ANOMALOUS
        assert fn.anomaly_reason == "OCR artifact"
        assert fn.anomaly_suggestion == "delete"

    def test_nonexistent_node_raises(self):
        engine, _ = _make_engine(2)
        with pytest.raises(TreeEngineError, match="does not exist"):
            engine.mark_anomalous("n99", "reason", "delete")


class TestProgressStats:
    def test_initial_all_unplaced(self):
        engine, _ = _make_engine(3)
        stats = engine.progress_stats
        assert stats.total == 3
        assert stats.unplaced == 3
        assert stats.placed == 0
        assert stats.uncertain == 0
        assert stats.anomalous == 0

    def test_after_adopt(self):
        engine, _ = _make_engine(3)
        engine.adopt_range("n0", "n1", "n2", "reason")
        stats = engine.progress_stats
        assert stats.unplaced == 1  # n0 still unplaced
        assert stats.placed == 2

    def test_after_mixed_statuses(self):
        engine, _ = _make_engine(4)
        engine.adopt_range("n0", "n1", "n1", "reason")  # n1 placed
        engine.mark_uncertain("n2", "reason")  # n2 uncertain
        engine.mark_anomalous("n3", "reason", "delete")  # n3 anomalous
        stats = engine.progress_stats
        assert stats.placed == 1
        assert stats.unplaced == 1  # n0 still UNPLACED (it was the parent, not adopted)
        assert stats.uncertain == 1
        assert stats.anomalous == 1


class TestStuckDetection:
    def test_stuck_count_increments_when_no_progress(self):
        engine, _ = _make_engine(2)
        assert engine.stuck_count == 0
        engine.update_stuck_count()
        assert engine.stuck_count == 1
        engine.update_stuck_count()
        assert engine.stuck_count == 2

    def test_stuck_count_resets_on_progress(self):
        engine, _ = _make_engine(3)
        engine.update_stuck_count()
        assert engine.stuck_count == 1
        engine.adopt_range("n0", "n1", "n2", "reason")
        engine.update_stuck_count()
        assert engine.stuck_count == 0
