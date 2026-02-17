from __future__ import annotations

from pydantic import BaseModel

from document_structuring_agent.models.classification import DocumentClassification
from document_structuring_agent.models.ocr_input import ElementMetadataMap


class DocumentSegment(BaseModel):
    """A contiguous segment of an OCR document."""

    label: str
    html: str
    element_metadata: ElementMetadataMap
    classification: DocumentClassification = DocumentClassification.UNKNOWN
    is_separate_document: bool = False
    page_start: int | None = None
    page_end: int | None = None


class SegmentationResult(BaseModel):
    """LLM output for document segmentation with rationale."""

    segments: list[DocumentSegment]
    num_documents_detected: int = 1
    rationale: str
