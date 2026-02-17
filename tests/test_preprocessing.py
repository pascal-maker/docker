from pathlib import Path

from document_structuring_agent.models.ocr_input import ElementMetadata
from document_structuring_agent.preprocessing.html_parser import (
    get_page_boundaries,
    parse_ocr_html,
)
from document_structuring_agent.preprocessing.metadata import (
    load_metadata,
    load_ocr_document,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestHtmlParser:
    def test_parse_simple_elements(self):
        html = '<h1 data-idx="0">Title</h1><p data-idx="1">Body text</p>'
        metadata = {
            0: ElementMetadata(page_number=1, confidence=0.95),
            1: ElementMetadata(page_number=1, confidence=0.9),
        }
        elements = parse_ocr_html(html, metadata)
        assert len(elements) == 2
        assert elements[0].tag == "h1"
        assert elements[0].data_idx == 0
        assert elements[0].text_content == "Title"
        assert elements[1].tag == "p"

    def test_page_header_filtering(self):
        html = '<p data-idx="0">Header</p><p data-idx="1">Content</p>'
        metadata = {
            0: ElementMetadata(page_number=1, confidence=0.9, is_page_header=True),
            1: ElementMetadata(page_number=1, confidence=0.9),
        }
        elements = parse_ocr_html(html, metadata)
        assert len(elements) == 1
        assert elements[0].data_idx == 1

    def test_table_preservation(self):
        html = (
            '<table data-idx="0">'
            "<tr><th>A</th><th>B</th></tr>"
            "<tr><td>1</td><td>2</td></tr>"
            "</table>"
        )
        metadata = {
            0: ElementMetadata(page_number=1, confidence=0.9),
        }
        elements = parse_ocr_html(html, metadata)
        assert len(elements) == 1
        assert elements[0].tag == "table"
        assert "<tr>" in elements[0].html
        assert "<th>A</th>" in elements[0].html

    def test_metadata_attachment(self):
        html = '<p data-idx="5">Text</p>'
        metadata = {
            5: ElementMetadata(
                page_number=2, confidence=0.88, is_bold=True, font_family="Arial"
            ),
        }
        elements = parse_ocr_html(html, metadata)
        assert elements[0].metadata is not None
        assert elements[0].metadata.page_number == 2
        assert elements[0].metadata.is_bold is True

    def test_elements_without_metadata(self):
        html = '<p data-idx="99">Orphan</p>'
        elements = parse_ocr_html(html, {})
        assert len(elements) == 1
        assert elements[0].metadata is None

    def test_page_boundaries(self):
        html = (
            '<p data-idx="0">Page 1 content</p>'
            '<p data-idx="1">Page 2 content</p>'
            '<p data-idx="2">Page 2 more</p>'
        )
        metadata = {
            0: ElementMetadata(page_number=1, confidence=0.9),
            1: ElementMetadata(page_number=2, confidence=0.9),
            2: ElementMetadata(page_number=2, confidence=0.9),
        }
        elements = parse_ocr_html(html, metadata)
        pages = get_page_boundaries(elements)
        assert len(pages) == 2
        assert len(pages[1]) == 1
        assert len(pages[2]) == 2


class TestMetadataLoader:
    def test_load_letter_metadata(self):
        metadata = load_metadata(FIXTURES / "sample_letter_metadata.json")
        assert 0 in metadata
        assert metadata[0].page_number == 1
        assert metadata[0].is_bold is True

    def test_load_ocr_document(self):
        doc = load_ocr_document(
            FIXTURES / "sample_letter.html",
            FIXTURES / "sample_letter_metadata.json",
        )
        assert doc.source_filename == "sample_letter.html"
        assert len(doc.element_metadata) == 15
        assert "<h1" in doc.html


class TestLegalScheduleFixture:
    def test_parse_legal_schedule(self):
        doc = load_ocr_document(
            FIXTURES / "sample_legal_schedule.html",
            FIXTURES / "sample_legal_schedule_metadata.json",
        )
        elements = parse_ocr_html(doc.html, doc.element_metadata)

        # Page header (idx=13) should be filtered out
        data_idxs = [e.data_idx for e in elements]
        assert 13 not in data_idxs

        # Should have 24 elements (25 total minus 1 page header)
        assert len(elements) == 24

        # First element should be the title
        assert elements[0].tag == "h1"
        assert "CREDIT AGREEMENT" in elements[0].text_content

        # Table should be preserved
        tables = [e for e in elements if e.tag == "table"]
        assert len(tables) == 1
