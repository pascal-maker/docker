from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_ai import Agent

from document_structuring_agent.models.classification import DocumentClassification
from document_structuring_agent.models.document import StructuredDocument
from document_structuring_agent.models.nodes import DocumentNode
from document_structuring_agent.models.ocr_input import OcrDocument
from document_structuring_agent.models.segmentation import DocumentSegment
from document_structuring_agent.preprocessing.html_parser import ParsedElement


@dataclass
class PipelineState:
    """Mutable state passed through the pipeline graph."""

    ocr_document: OcrDocument
    parsed_elements: list[ParsedElement] = field(default_factory=list)
    segments: list[DocumentSegment] = field(default_factory=list)
    num_documents_detected: int = 1
    parsed_trees: list[DocumentNode] = field(default_factory=list)
    results: list[StructuredDocument] = field(default_factory=list)


@dataclass
class PipelineDeps:
    """Dependencies injected into pipeline graph nodes."""

    parser_registry: dict[DocumentClassification, Agent[None, DocumentNode]]
