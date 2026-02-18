"""Flat node representation for the tree agent.

Converts raw ParsedElement objects from OCR preprocessing into FlatNode
objects that the tree agent can reason about. The description and hints
fields expose only structural signals — full HTML content is withheld
until explicitly requested via the read_nodes tool.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from document_structuring_agent.preprocessing.html_parser import ParsedElement

_HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_MAX_DESCRIPTION_TEXT = 80


class NodeStatus(StrEnum):
    """Placement status of a node during tree construction."""

    UNPLACED = "unplaced"
    PLACED = "placed"
    UNCERTAIN = "uncertain"
    ANOMALOUS = "anomalous"


class NodeHints(BaseModel):
    """Structural signals extracted from OCR metadata.

    Exposed in the skeleton view so the agent can make placement decisions
    without reading full HTML content.
    """

    page_number: int
    is_bold: bool
    is_italic: bool
    heading_level: int | None
    top_fraction: float | None
    font_family: str | None
    confidence: float


class FlatNode(BaseModel):
    """A single document element ready for tree placement.

    Immutable identity fields (node_id, data_idx, tag, description, hints)
    are set at conversion time. Status fields are mutated by the tree engine.
    """

    node_id: str
    data_idx: int | None
    tag: str
    description: str
    hints: NodeHints
    status: NodeStatus = NodeStatus.UNPLACED
    uncertainty_reason: str | None = None
    anomaly_reason: str | None = None
    anomaly_suggestion: str | None = None


def _build_description(tag: str, text_content: str, hints: NodeHints) -> str:
    """Build a concise human-readable description for the skeleton view."""
    parts: list[str] = [f"<{tag}>"]
    if hints.is_bold:
        parts.append("[bold]")
    if hints.is_italic:
        parts.append("[italic]")
    parts.append(f"p{hints.page_number}")

    if tag == "table":
        parts.append("[table content]")
    elif tag in ("ul", "ol"):
        parts.append("[list]")
    elif text_content:
        snippet = text_content[:_MAX_DESCRIPTION_TEXT].replace("\n", " ").strip()
        parts.append(f'"{snippet}"')

    return " ".join(parts)


def _build_hints(elem: ParsedElement) -> NodeHints:
    """Extract structural hints from a ParsedElement's metadata."""
    meta = elem.metadata
    heading_level = _HEADING_TAGS.get(elem.tag)

    if meta is None:
        return NodeHints(
            page_number=0,
            is_bold=False,
            is_italic=False,
            heading_level=heading_level,
            top_fraction=None,
            font_family=None,
            confidence=0.0,
        )

    top_fraction: float | None = None
    if meta.height > 0:
        top_fraction = round(meta.top / meta.height, 3)

    return NodeHints(
        page_number=meta.page_number,
        is_bold=meta.is_bold,
        is_italic=meta.is_italic,
        heading_level=heading_level,
        top_fraction=top_fraction,
        font_family=meta.font_family,
        confidence=meta.confidence,
    )


def convert_to_flat_nodes(elements: list[ParsedElement]) -> list[FlatNode]:
    """Convert a list of ParsedElements to FlatNodes in document order.

    Assigns stable IDs n0, n1, ... in order. The original data_idx is
    preserved for content lookup via the read_nodes tool.
    """
    result: list[FlatNode] = []
    for i, elem in enumerate(elements):
        hints = _build_hints(elem)
        description = _build_description(elem.tag, elem.text_content, hints)
        result.append(
            FlatNode(
                node_id=f"n{i}",
                data_idx=elem.data_idx,
                tag=elem.tag,
                description=description,
                hints=hints,
            )
        )
    return result
