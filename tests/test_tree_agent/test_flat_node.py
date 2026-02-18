"""Tests for flat_node conversion logic."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from document_structuring_agent.models.ocr_input import ElementMetadata
from document_structuring_agent.preprocessing.html_parser import ParsedElement
from document_structuring_agent.tree_agent.flat_node import (
    NodeStatus,
    convert_to_flat_nodes,
)


def _make_element(
    tag: str,
    text: str,
    data_idx: int = 0,
    page: int = 1,
    is_bold: bool = False,
    is_italic: bool = False,
    font_family: str | None = None,
) -> ParsedElement:
    meta = ElementMetadata(
        page_number=page,
        confidence=0.9,
        left=0.0,
        top=0.1,
        width=1.0,
        height=0.9,
        is_bold=is_bold,
        is_italic=is_italic,
        font_family=font_family,
    )
    elem = ParsedElement(tag=tag, data_idx=data_idx, html=f"<{tag}>{text}</{tag}>", text_content=text)
    elem.metadata = meta
    return elem


class TestConvertToFlatNodes:
    def test_assigns_sequential_ids(self):
        elements = [
            _make_element("h1", "Title", data_idx=0),
            _make_element("p", "Body", data_idx=1),
            _make_element("h2", "Section", data_idx=2),
        ]
        nodes = convert_to_flat_nodes(elements)
        assert [n.node_id for n in nodes] == ["n0", "n1", "n2"]

    def test_preserves_data_idx(self):
        elements = [_make_element("p", "text", data_idx=42)]
        nodes = convert_to_flat_nodes(elements)
        assert nodes[0].data_idx == 42

    def test_all_start_unplaced(self):
        elements = [_make_element("p", "text", data_idx=0)]
        nodes = convert_to_flat_nodes(elements)
        assert nodes[0].status == NodeStatus.UNPLACED

    def test_empty_input(self):
        assert convert_to_flat_nodes([]) == []


class TestNodeHints:
    def test_heading_level_from_tag(self):
        for tag, expected_level in [("h1", 1), ("h2", 2), ("h3", 3), ("p", None)]:
            elem = _make_element(tag, "text", data_idx=0)
            nodes = convert_to_flat_nodes([elem])
            assert nodes[0].hints.heading_level == expected_level

    def test_bold_flag(self):
        elem = _make_element("h2", "Bold heading", data_idx=0, is_bold=True)
        nodes = convert_to_flat_nodes([elem])
        assert nodes[0].hints.is_bold is True

    def test_italic_flag(self):
        elem = _make_element("p", "Italic text", data_idx=0, is_italic=True)
        nodes = convert_to_flat_nodes([elem])
        assert nodes[0].hints.is_italic is True

    def test_page_number(self):
        elem = _make_element("p", "text", data_idx=0, page=5)
        nodes = convert_to_flat_nodes([elem])
        assert nodes[0].hints.page_number == 5


class TestDescription:
    def test_bold_heading_description(self):
        elem = _make_element("h2", "2.1 Definitions", data_idx=0, page=3, is_bold=True)
        nodes = convert_to_flat_nodes([elem])
        desc = nodes[0].description
        assert "[bold]" in desc
        assert "2.1 Definitions" in desc
        assert "p3" in desc

    def test_table_description(self):
        elem = _make_element("table", "", data_idx=0)
        nodes = convert_to_flat_nodes([elem])
        assert "[table content]" in nodes[0].description

    def test_list_description(self):
        elem = _make_element("ul", "", data_idx=0)
        nodes = convert_to_flat_nodes([elem])
        assert "[list]" in nodes[0].description

    def test_long_text_truncated(self):
        long_text = "A" * 200
        elem = _make_element("p", long_text, data_idx=0)
        nodes = convert_to_flat_nodes([elem])
        assert len(nodes[0].description) < 200

    def test_no_metadata_falls_back_gracefully(self):
        elem = ParsedElement(
            tag="p", data_idx=None, html="<p>text</p>", text_content="text"
        )
        # metadata is None
        nodes = convert_to_flat_nodes([elem])
        assert nodes[0].node_id == "n0"
        assert nodes[0].hints.page_number == 0
