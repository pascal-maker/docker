from __future__ import annotations

import json
from pathlib import Path

from document_structuring_agent.models.ocr_input import ElementMetadata, OcrDocument


def load_metadata(path: Path) -> dict[int, ElementMetadata]:
    """Load per-element metadata from a JSON file keyed by data-idx."""
    raw = json.loads(path.read_text())
    return {int(k): ElementMetadata.model_validate(v) for k, v in raw.items()}


def load_ocr_document(html_path: Path, metadata_path: Path) -> OcrDocument:
    """Load an OcrDocument from an HTML file and a metadata JSON file."""
    html = html_path.read_text()
    metadata = load_metadata(metadata_path)
    return OcrDocument(
        html=html,
        element_metadata=metadata,
        source_filename=html_path.name,
    )
