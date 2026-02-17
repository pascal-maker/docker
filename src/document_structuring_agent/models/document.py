from __future__ import annotations

from pydantic import BaseModel

from document_structuring_agent.models.classification import DocumentClassification
from document_structuring_agent.models.nodes import DocumentNode


class StructuredDocument(BaseModel):
    """Final output of the pipeline: a fully parsed document tree."""

    root: DocumentNode
    classification: DocumentClassification = DocumentClassification.UNKNOWN
    source_filename: str | None = None
    num_pages: int | None = None
