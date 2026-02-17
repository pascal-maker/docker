from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DocumentClassification(str, Enum):
    LETTER = "letter"
    RECEIPT = "receipt"
    INVOICE = "invoice"
    LEGAL_SCHEDULE = "legal_schedule"
    SEC_FILING = "sec_filing"
    CONTRACT = "contract"
    REPORT = "report"
    UNKNOWN = "unknown"


class ClassificationResult(BaseModel):
    classification: DocumentClassification
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
