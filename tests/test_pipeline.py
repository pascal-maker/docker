"""Pipeline tests using PydanticAI's TestModel for deterministic testing."""

import pytest
from pydantic_ai import Agent

from document_structuring_agent.models.classification import (
    ClassificationResult,
    DocumentClassification,
)
from document_structuring_agent.models.nodes import DocumentNode, NodeType
from document_structuring_agent.models.ocr_input import ElementMetadata
from document_structuring_agent.models.segmentation import SegmentationResult
from document_structuring_agent.pipeline.nodes import _rule_based_segmentation
from document_structuring_agent.preprocessing.html_parser import parse_ocr_html


class TestRuleBasedSegmentation:
    def test_single_segment(self):
        html = '<p data-idx="0">Content</p>'
        metadata = {0: ElementMetadata(page_number=1, confidence=0.9)}
        elements = parse_ocr_html(html, metadata)
        segments = _rule_based_segmentation(elements)
        assert len(segments) == 1
        assert segments[0].label == "Content"

    def test_split_on_h1(self):
        html = (
            '<h1 data-idx="0">First Section</h1>'
            '<p data-idx="1">Body 1</p>'
            '<h1 data-idx="2">Second Section</h1>'
            '<p data-idx="3">Body 2</p>'
        )
        metadata = {
            0: ElementMetadata(page_number=1, confidence=0.9),
            1: ElementMetadata(page_number=1, confidence=0.9),
            2: ElementMetadata(page_number=2, confidence=0.9),
            3: ElementMetadata(page_number=2, confidence=0.9),
        }
        elements = parse_ocr_html(html, metadata)
        segments = _rule_based_segmentation(elements)
        assert len(segments) == 2
        assert segments[0].page_start == 1
        assert segments[1].page_start == 2

    def test_empty_input(self):
        segments = _rule_based_segmentation([])
        assert segments == []


class TestAgentsWithTestModel:
    """Test agents using PydanticAI's TestModel for deterministic output."""

    @pytest.mark.asyncio
    async def test_classification_agent_with_test_model(self):
        agent = Agent(
            "test",
            output_type=ClassificationResult,
            instructions="Classify documents.",
        )
        result = await agent.run("Sample letter content")
        assert isinstance(result.output, ClassificationResult)
        assert isinstance(result.output.classification, DocumentClassification)

    @pytest.mark.asyncio
    async def test_parser_agent_with_test_model(self):
        agent = Agent(
            "test",
            output_type=DocumentNode,
            instructions="Parse document structure.",
        )
        result = await agent.run("Sample document HTML")
        assert isinstance(result.output, DocumentNode)
        assert isinstance(result.output.node_type, NodeType)

    @pytest.mark.asyncio
    async def test_segmentation_agent_with_test_model(self):
        # TestModel can't generate valid dict[int, ElementMetadata] keys,
        # so we provide the custom output args directly.
        from pydantic_ai.models.test import TestModel

        agent = Agent(
            TestModel(
                custom_output_args={
                    "segments": [],
                    "num_documents_detected": 1,
                    "rationale": "test",
                }
            ),
            output_type=SegmentationResult,
            instructions="Segment the document.",
        )
        result = await agent.run("Sample elements summary")
        assert isinstance(result.output, SegmentationResult)
