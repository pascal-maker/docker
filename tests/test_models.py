from document_structuring_agent.models.classification import (
    ClassificationResult,
    DocumentClassification,
)
from document_structuring_agent.models.document import StructuredDocument
from document_structuring_agent.models.nodes import (
    DocumentNode,
    NodeMetadata,
    NodeType,
)
from document_structuring_agent.models.ocr_input import ElementMetadata, OcrDocument
from document_structuring_agent.models.segmentation import (
    DocumentSegment,
    SegmentationResult,
)


class TestNodeModels:
    def test_document_node_minimal(self):
        node = DocumentNode(node_type=NodeType.PARAGRAPH, content="Hello world")
        assert node.node_type == NodeType.PARAGRAPH
        assert node.content == "Hello world"
        assert node.children == []
        assert node.metadata.page_start is None

    def test_document_node_with_children(self):
        child = DocumentNode(node_type=NodeType.PARAGRAPH, content="Child")
        parent = DocumentNode(
            node_type=NodeType.SECTION,
            title="Section 1",
            children=[child],
            metadata=NodeMetadata(page_start=1, page_end=1),
        )
        assert len(parent.children) == 1
        assert parent.children[0].content == "Child"
        assert parent.metadata.page_start == 1

    def test_document_node_recursive_serialization(self):
        tree = DocumentNode(
            node_type=NodeType.DOCUMENT,
            children=[
                DocumentNode(
                    node_type=NodeType.CHAPTER,
                    title="Chapter 1",
                    children=[
                        DocumentNode(
                            node_type=NodeType.SECTION,
                            title="Section 1.1",
                            children=[
                                DocumentNode(
                                    node_type=NodeType.PARAGRAPH,
                                    content="Body text.",
                                )
                            ],
                        )
                    ],
                )
            ],
        )
        data = tree.model_dump()
        assert data["node_type"] == "document"
        assert data["children"][0]["children"][0]["title"] == "Section 1.1"

    def test_node_type_values(self):
        assert NodeType.DOCUMENT.value == "document"
        assert NodeType.TABLE_CELL.value == "table_cell"
        assert NodeType.SIGNATURE_BLOCK.value == "signature_block"


class TestOcrInputModels:
    def test_element_metadata(self):
        meta = ElementMetadata(page_number=1, confidence=0.95)
        assert meta.page_number == 1
        assert meta.is_page_header is False

    def test_element_metadata_validation(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ElementMetadata(page_number=1, confidence=1.5)

    def test_ocr_document(self):
        doc = OcrDocument(
            html="<p data-idx='0'>Hello</p>",
            element_metadata={0: ElementMetadata(page_number=1, confidence=0.9)},
        )
        assert doc.source_filename is None
        assert 0 in doc.element_metadata


class TestClassificationModels:
    def test_classification_result(self):
        result = ClassificationResult(
            classification=DocumentClassification.LETTER,
            confidence=0.9,
            rationale="Contains salutation and signature",
        )
        assert result.classification == DocumentClassification.LETTER

    def test_all_classification_types(self):
        types = [e.value for e in DocumentClassification]
        assert "letter" in types
        assert "legal_schedule" in types
        assert "unknown" in types


class TestSegmentationModels:
    def test_segmentation_result(self):
        result = SegmentationResult(
            segments=[
                DocumentSegment(
                    label="Main Body",
                    html="<p>Content</p>",
                    element_metadata={},
                    page_start=1,
                    page_end=3,
                )
            ],
            num_documents_detected=1,
            rationale="Single document detected",
        )
        assert len(result.segments) == 1
        assert result.segments[0].is_separate_document is False


class TestDocumentModel:
    def test_structured_document(self):
        doc = StructuredDocument(
            root=DocumentNode(node_type=NodeType.DOCUMENT),
            classification=DocumentClassification.CONTRACT,
            source_filename="test.html",
            num_pages=5,
        )
        assert doc.classification == DocumentClassification.CONTRACT
        assert doc.num_pages == 5
