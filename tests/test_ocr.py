"""Tests for PDF-to-OCR preprocessing with Docling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from document_structuring_agent.preprocessing.ocr import (
    _build_ocr_output,
    _extract_metadata,
    _heading_tag,
    _table_to_html,
    pdf_to_ocr_document,
)

# ---------------------------------------------------------------------------
# Helpers to build mock Docling objects
# ---------------------------------------------------------------------------


def _make_prov(page_no=1, left=10.0, t=20.0, r=110.0, b=40.0):
    """Create a mock ProvenanceItem with TOPLEFT coord origin."""
    prov = MagicMock()
    prov.page_no = page_no
    prov.bbox.l = left
    prov.bbox.t = t
    prov.bbox.r = r
    prov.bbox.b = b
    prov.bbox.coord_origin = MagicMock()
    prov.bbox.coord_origin.__eq__ = lambda self, other: False  # not BOTTOMLEFT
    return prov


def _make_text_item(text="Hello", prov=None, formatting=None, label="paragraph"):
    """Create a mock TextItem."""
    item = MagicMock()
    item.__class__.__name__ = "TextItem"
    item.text = text
    item.prov = [prov] if prov else []
    item.formatting = formatting
    item.label = label
    return item


def _make_title_item(text="Title", prov=None):
    """Create a mock TitleItem."""
    item = MagicMock()
    item.text = text
    item.prov = [prov] if prov else []
    item.formatting = None
    return item


def _make_section_header(text="Section", level=1, prov=None):
    """Create a mock SectionHeaderItem."""
    item = MagicMock()
    item.text = text
    item.level = level
    item.prov = [prov] if prov else []
    item.formatting = None
    return item


def _make_table_item(cells, num_rows, num_cols, prov=None):
    """Create a mock TableItem with table_cells."""
    item = MagicMock()
    item.prov = [prov] if prov else []
    item.formatting = None
    item.data.table_cells = cells
    item.data.num_rows = num_rows
    item.data.num_cols = num_cols
    return item


def _make_table_cell(
    text="cell",
    row=0,
    col=0,
    row_span=1,
    col_span=1,
    column_header=False,
):
    cell = MagicMock()
    cell.text = text
    cell.start_row_offset_idx = row
    cell.end_row_offset_idx = row + row_span
    cell.start_col_offset_idx = col
    cell.end_col_offset_idx = col + col_span
    cell.row_span = row_span
    cell.col_span = col_span
    cell.column_header = column_header
    return cell


def _make_list_item(text="Item 1", prov=None):
    item = MagicMock()
    item.text = text
    item.prov = [prov] if prov else []
    item.formatting = None
    return item


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHeadingTag:
    def test_level_1_maps_to_h2(self):
        assert _heading_tag(1) == "h2"

    def test_level_2_maps_to_h3(self):
        assert _heading_tag(2) == "h3"

    def test_level_5_maps_to_h6(self):
        assert _heading_tag(5) == "h6"

    def test_level_above_5_clamped(self):
        assert _heading_tag(10) == "h6"

    def test_level_0_clamped_to_h2(self):
        assert _heading_tag(0) == "h2"


class TestExtractMetadata:
    def test_with_provenance(self):
        prov = _make_prov(page_no=3, left=10, t=20, r=110, b=40)
        item = _make_text_item(prov=prov)

        meta = _extract_metadata(item, page_heights={})
        assert meta.page_number == 3
        assert meta.left == 10.0
        assert meta.top == 20.0
        assert meta.width == 100.0
        assert meta.height == 20.0
        assert meta.confidence == 1.0

    def test_without_provenance(self):
        item = _make_text_item()
        meta = _extract_metadata(item, page_heights={})
        assert meta.page_number == 1
        assert meta.confidence == 1.0

    def test_formatting_bold_italic(self):
        prov = _make_prov()
        fmt = MagicMock()
        fmt.bold = True
        fmt.italic = True
        item = _make_text_item(prov=prov, formatting=fmt)

        meta = _extract_metadata(item, page_heights={})
        assert meta.is_bold is True
        assert meta.is_italic is True

    def test_no_formatting(self):
        prov = _make_prov()
        item = _make_text_item(prov=prov, formatting=None)

        meta = _extract_metadata(item, page_heights={})
        assert meta.is_bold is False
        assert meta.is_italic is False


class TestTableToHtml:
    def test_simple_table(self):
        cells = [
            _make_table_cell("Name", row=0, col=0, column_header=True),
            _make_table_cell("Value", row=0, col=1, column_header=True),
            _make_table_cell("Alice", row=1, col=0),
            _make_table_cell("100", row=1, col=1),
        ]
        table = _make_table_item(cells, num_rows=2, num_cols=2)
        result = _table_to_html(table)

        assert "<th>Name</th>" in result
        assert "<th>Value</th>" in result
        assert "<td>Alice</td>" in result
        assert "<td>100</td>" in result
        assert result.count("<tr>") == 2

    def test_colspan(self):
        cells = [
            _make_table_cell("Wide", row=0, col=0, col_span=2),
            _make_table_cell("A", row=1, col=0),
            _make_table_cell("B", row=1, col=1),
        ]
        table = _make_table_item(cells, num_rows=2, num_cols=2)
        result = _table_to_html(table)

        assert 'colspan="2"' in result

    def test_empty_table(self):
        table = _make_table_item([], num_rows=0, num_cols=0)
        assert _table_to_html(table) == ""

    def test_html_escaping_in_cells(self):
        cells = [_make_table_cell("<script>", row=0, col=0)]
        table = _make_table_item(cells, num_rows=1, num_cols=1)
        result = _table_to_html(table)

        assert "&lt;script&gt;" in result
        assert "<script>" not in result


class TestBuildOcrOutput:
    @patch("document_structuring_agent.preprocessing.ocr._get_page_heights")
    def test_sequential_data_idx(self, mock_pages):
        mock_pages.return_value = {}

        from docling_core.types.doc.document import (
            TextItem,
            TitleItem,
        )

        doc = MagicMock()
        title = _make_title_item("Doc Title")
        title.__class__ = TitleItem
        para = _make_text_item("Body text")
        para.__class__ = TextItem

        doc.iterate_items.return_value = [(title, 0), (para, 1)]

        html_parts, metadata = _build_ocr_output(doc)

        assert len(html_parts) == 2
        assert 'data-idx="0"' in html_parts[0]
        assert 'data-idx="1"' in html_parts[1]
        assert 0 in metadata
        assert 1 in metadata

    @patch("document_structuring_agent.preprocessing.ocr._get_page_heights")
    def test_title_becomes_h1(self, mock_pages):
        mock_pages.return_value = {}

        from docling_core.types.doc.document import TitleItem

        doc = MagicMock()
        title = _make_title_item("My Title")
        title.__class__ = TitleItem
        doc.iterate_items.return_value = [(title, 0)]

        html_parts, _ = _build_ocr_output(doc)
        assert html_parts[0].startswith("<h1")

    @patch("document_structuring_agent.preprocessing.ocr._get_page_heights")
    def test_section_header_becomes_h2(self, mock_pages):
        mock_pages.return_value = {}

        from docling_core.types.doc.document import SectionHeaderItem

        doc = MagicMock()
        header = _make_section_header("Section", level=1)
        header.__class__ = SectionHeaderItem
        header.level = 1
        doc.iterate_items.return_value = [(header, 0)]

        html_parts, _ = _build_ocr_output(doc)
        assert html_parts[0].startswith("<h2")

    @patch("document_structuring_agent.preprocessing.ocr._get_page_heights")
    def test_html_escaping(self, mock_pages):
        mock_pages.return_value = {}

        from docling_core.types.doc.document import TextItem

        doc = MagicMock()
        item = _make_text_item("a < b & c > d")
        item.__class__ = TextItem
        doc.iterate_items.return_value = [(item, 0)]

        html_parts, _ = _build_ocr_output(doc)
        assert "&lt;" in html_parts[0]
        assert "&amp;" in html_parts[0]
        assert "&gt;" in html_parts[0]

    @patch("document_structuring_agent.preprocessing.ocr._get_page_heights")
    def test_empty_document(self, mock_pages):
        mock_pages.return_value = {}
        doc = MagicMock()
        doc.iterate_items.return_value = []

        html_parts, metadata = _build_ocr_output(doc)
        assert html_parts == []
        assert metadata == {}


class TestPdfToOcrDocument:
    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            pdf_to_ocr_document(tmp_path / "nonexistent.pdf")

    @patch("document_structuring_agent.preprocessing.ocr._convert_pdf")
    def test_returns_ocr_document(self, mock_convert, tmp_path):
        from docling_core.types.doc.document import TextItem

        # Create a dummy PDF file so the path check passes
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 dummy")

        # Mock the Docling document
        doc = MagicMock()
        doc.pages = {}
        item = _make_text_item("Hello world", prov=_make_prov())
        item.__class__ = TextItem
        doc.iterate_items.return_value = [(item, 0)]
        mock_convert.return_value = doc

        result = pdf_to_ocr_document(pdf)

        assert result.source_filename == "test.pdf"
        assert 'data-idx="0"' in result.html
        assert "Hello world" in result.html
        assert len(result.element_metadata) == 1
