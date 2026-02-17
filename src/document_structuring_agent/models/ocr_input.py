from __future__ import annotations

from pydantic import BaseModel, Field


class ElementMetadata(BaseModel):
    """Per-element metadata from OCR, keyed by data-idx."""

    page_number: int
    confidence: float = Field(ge=0.0, le=1.0)
    left: float = 0
    top: float = 0
    width: float = 0
    height: float = 0
    is_bold: bool = False
    is_italic: bool = False
    font_family: str | None = None
    is_page_header: bool = False


class OcrDocument(BaseModel):
    """The full input: HTML content + per-element metadata."""

    html: str
    element_metadata: dict[int, ElementMetadata]
    source_filename: str | None = None
