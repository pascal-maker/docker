"""Convert a PDF file to an OcrDocument using Docling."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from document_structuring_agent.logger import logger
from document_structuring_agent.models.ocr_input import (
    ElementMetadata,
    ElementMetadataMap,
    OcrDocument,
)

if TYPE_CHECKING:
    from pathlib import Path

    from docling_core.types.doc.document import (
        DoclingDocument,
        NodeItem,
        ProvenanceItem,
        RichTableCell,
        TableCell,
        TableItem,
    )


def pdf_to_ocr_document(pdf_path: Path) -> OcrDocument:
    """Convert a PDF file to an OcrDocument via Docling OCR.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        An OcrDocument with HTML containing ``data-idx`` attributes
        and per-element metadata.

    Raises:
        FileNotFoundError: If the PDF does not exist.
    """
    if not pdf_path.exists():
        msg = f"PDF file not found: {pdf_path}"
        raise FileNotFoundError(msg)

    logger.info("event=ocr_start", extra={"pdf": pdf_path.name})
    doc = _convert_pdf(pdf_path)
    html_parts, metadata_map = _build_ocr_output(doc)

    ocr_result = OcrDocument(
        html="\n".join(html_parts),
        element_metadata=ElementMetadataMap(metadata_map),
        source_filename=pdf_path.name,
    )
    logger.info(
        "event=ocr_finish",
        extra={"pdf": pdf_path.name, "elements": len(ocr_result.element_metadata.root)},
    )
    return ocr_result


def _convert_pdf(pdf_path: Path) -> DoclingDocument:
    """Run Docling DocumentConverter on a PDF.

    Docling automatically detects and uses MPS (Metal Performance Shaders)
    acceleration on Apple Silicon Macs for faster OCR processing. No explicit
    configuration is needed; MPS support is enabled via PyTorch's automatic
    device detection.
    """
    from docling.document_converter import DocumentConverter  # noqa: PLC0415

    logger.info("Initialising Docling converter (first run downloads models)...")
    converter = DocumentConverter()
    logger.info("Converting %s ...", pdf_path.name)
    result = converter.convert(str(pdf_path))
    logger.info("Conversion complete.")
    return result.document


def _build_ocr_output(
    doc: DoclingDocument,
) -> tuple[list[str], dict[int, ElementMetadata]]:
    """Transform a DoclingDocument into indexed HTML parts and metadata."""
    from docling_core.types.doc.document import (  # noqa: PLC0415
        ListItem,
        SectionHeaderItem,
        TableItem,
        TextItem,
        TitleItem,
    )

    page_heights = _get_page_heights(doc)

    html_parts: list[str] = []
    metadata: dict[int, ElementMetadata] = {}

    for idx, (item, _level) in enumerate(doc.iterate_items()):
        # Determine HTML tag
        if isinstance(item, TitleItem):
            tag = "h1"
        elif isinstance(item, SectionHeaderItem):
            tag = _heading_tag(item.level)
        elif isinstance(item, TableItem):
            tag = "table"
        elif isinstance(item, ListItem):
            tag = "li"
        elif isinstance(item, TextItem):
            tag = "p"
        else:
            tag = "p"

        # Build HTML
        if isinstance(item, TableItem):
            inner = _table_to_html(item)
            html_parts.append(f'<table data-idx="{idx}">{inner}</table>')
        else:
            text = item.text if hasattr(item, "text") else ""
            escaped = html.escape(text)
            html_parts.append(f'<{tag} data-idx="{idx}">{escaped}</{tag}>')

        # Build metadata
        meta = _extract_metadata(item, page_heights)
        metadata[idx] = meta

    return html_parts, metadata


def _heading_tag(level: int) -> str:
    """Map SectionHeaderItem.level to h2-h6 (h1 reserved for title)."""
    clamped = min(max(level, 1), 5)
    return f"h{clamped + 1}"


def _get_page_heights(doc: DoclingDocument) -> dict[int, float]:
    """Extract page heights for coordinate flipping."""
    return {
        page_no: page.size.height
        for page_no, page in doc.pages.items()
        if page.size is not None
    }


def _extract_metadata(
    item: NodeItem,
    page_heights: dict[int, float],
) -> ElementMetadata:
    """Extract ElementMetadata from a Docling item's provenance."""
    prov_list: list[ProvenanceItem] = getattr(item, "prov", [])

    if not prov_list:
        return ElementMetadata(page_number=1, confidence=1.0)

    prov = prov_list[0]
    bbox = prov.bbox

    left = float(bbox.l)
    top = float(bbox.t)
    width = float(bbox.r - bbox.l)
    height = float(bbox.b - bbox.t)

    # Handle BOTTOMLEFT coordinate origin: flip top
    from docling_core.types.doc.base import CoordOrigin  # noqa: PLC0415

    if bbox.coord_origin == CoordOrigin.BOTTOMLEFT:
        page_h = page_heights.get(prov.page_no, 0.0)
        if page_h > 0:
            top = page_h - float(bbox.t)
        height = abs(height)

    # Extract formatting if available
    is_bold = False
    is_italic = False
    formatting = getattr(item, "formatting", None)
    if formatting is not None:
        is_bold = formatting.bold
        is_italic = formatting.italic

    return ElementMetadata(
        page_number=prov.page_no,
        confidence=1.0,
        left=left,
        top=top,
        width=abs(width),
        height=height,
        is_bold=is_bold,
        is_italic=is_italic,
    )


def _table_to_html(table_item: TableItem) -> str:
    """Convert a Docling TableItem to inner HTML rows."""
    data = table_item.data
    if not data.table_cells:
        return ""

    # Build a grid from table_cells
    grid: dict[tuple[int, int], RichTableCell | TableCell] = {}
    for cell in data.table_cells:
        grid[(cell.start_row_offset_idx, cell.start_col_offset_idx)] = cell

    rows: list[str] = []
    for r in range(data.num_rows):
        row_cells: list[str] = []
        for c in range(data.num_cols):
            entry = grid.get((r, c))
            if entry is None:
                continue
            # Skip spanned-over positions (only render from start position)
            if entry.start_row_offset_idx != r or entry.start_col_offset_idx != c:
                continue

            cell_text = html.escape(entry.text)
            tag = "th" if entry.column_header else "td"
            attrs = ""
            if entry.col_span > 1:
                attrs += f' colspan="{entry.col_span}"'
            if entry.row_span > 1:
                attrs += f' rowspan="{entry.row_span}"'
            row_cells.append(f"<{tag}{attrs}>{cell_text}</{tag}>")
        if row_cells:
            rows.append(f"<tr>{''.join(row_cells)}</tr>")

    return "\n".join(rows)
