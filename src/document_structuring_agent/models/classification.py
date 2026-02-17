from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentClassification(StrEnum):
    """Supported document classification types."""

    LETTER = "letter"
    RECEIPT = "receipt"
    INVOICE = "invoice"
    LEGAL_SCHEDULE = "legal_schedule"
    SEC_FILING = "sec_filing"
    CONTRACT = "contract"
    REPORT = "report"
    UNKNOWN = "unknown"


class ClassificationResult(BaseModel):
    """LLM output for document classification with confidence and rationale."""

    classification: DocumentClassification
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
