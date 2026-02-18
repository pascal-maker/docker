"""Tests for TreeEngine → StructuredDocument conversion."""

from __future__ import annotations

from document_structuring_agent.models.nodes import NodeType
from document_structuring_agent.tree_agent.converter import (
    tree_engine_to_structured_document,
)
from document_structuring_agent.tree_agent.engine import build_tree_engine
from document_structuring_agent.tree_agent.flat_node import (
    FlatNode,
    NodeHints,
    NodeStatus,
)


def _make_flat_node(
    node_id: str,
    tag: str = "p",
    page: int = 1,
    heading_level: int | None = None,
) -> FlatNode:
    hints = NodeHints(
        page_number=page,
        is_bold=False,
        is_italic=False,
        heading_level=heading_level,
        top_fraction=None,
        font_family=None,
        confidence=0.9,
    )
    return FlatNode(
        node_id=node_id,
        data_idx=node_id.__hash__() % 100,
        tag=tag,
        description=f'<{tag}> p{page} "some text"',
        hints=hints,
    )


class TestTreeEngineToStructuredDocument:
    def test_root_becomes_document_node(self):
        engine = build_tree_engine([_make_flat_node("n0")])
        doc = tree_engine_to_structured_document(engine, None)
        assert doc.root.node_type == NodeType.DOCUMENT

    def test_h1_becomes_heading_level_1(self):
        node = _make_flat_node("n0", tag="h1", heading_level=1)
        engine = build_tree_engine([node])
        doc = tree_engine_to_structured_document(engine, None)
        child = doc.root.children[0]
        assert child.node_type == NodeType.HEADING
        assert child.metadata.heading_level == 1

    def test_h2_becomes_heading_level_2(self):
        node = _make_flat_node("n0", tag="h2", heading_level=2)
        engine = build_tree_engine([node])
        doc = tree_engine_to_structured_document(engine, None)
        child = doc.root.children[0]
        assert child.node_type == NodeType.HEADING
        assert child.metadata.heading_level == 2

    def test_paragraph_tag(self):
        node = _make_flat_node("n0", tag="p")
        engine = build_tree_engine([node])
        doc = tree_engine_to_structured_document(engine, None)
        assert doc.root.children[0].node_type == NodeType.PARAGRAPH

    def test_table_tag(self):
        node = _make_flat_node("n0", tag="table")
        engine = build_tree_engine([node])
        doc = tree_engine_to_structured_document(engine, None)
        assert doc.root.children[0].node_type == NodeType.TABLE

    def test_source_filename_preserved(self):
        engine = build_tree_engine([_make_flat_node("n0")])
        doc = tree_engine_to_structured_document(engine, "test.pdf")
        assert doc.source_filename == "test.pdf"

    def test_anomalous_node_included_with_low_confidence(self):
        node = _make_flat_node("n0")
        engine = build_tree_engine([node])
        engine.mark_anomalous("n0", "OCR artifact", "delete")
        doc = tree_engine_to_structured_document(engine, None)
        child = doc.root.children[0]
        assert child.metadata.confidence is not None
        assert child.metadata.confidence < 0.5

    def test_uncertain_node_included(self):
        node = _make_flat_node("n0")
        engine = build_tree_engine([node])
        engine.mark_uncertain("n0", "ambiguous placement")
        doc = tree_engine_to_structured_document(engine, None)
        assert len(doc.root.children) == 1

    def test_nested_structure_preserved(self):
        nodes = [
            _make_flat_node("n0", tag="h1", heading_level=1),
            _make_flat_node("n1", tag="h2", heading_level=2),
            _make_flat_node("n2", tag="p"),
        ]
        engine = build_tree_engine(nodes)
        engine.adopt_range("n0", "n1", "n2", "reason")
        doc = tree_engine_to_structured_document(engine, None)
        assert len(doc.root.children) == 1  # just n0 at root
        h1 = doc.root.children[0]
        assert h1.node_type == NodeType.HEADING
        assert len(h1.children) == 2  # n1 and n2 under n0

    def test_page_metadata(self):
        node = _make_flat_node("n0", page=5)
        engine = build_tree_engine([node])
        doc = tree_engine_to_structured_document(engine, None)
        child = doc.root.children[0]
        assert child.metadata.page_start == 5

    def test_empty_engine(self):
        engine = build_tree_engine([])
        doc = tree_engine_to_structured_document(engine, None)
        assert doc.root.node_type == NodeType.DOCUMENT
        assert doc.root.children == []
