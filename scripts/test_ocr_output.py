"""Run OCR on a PDF and inspect the OcrDocument output.

Usage:
    uv run python scripts/test_ocr_output.py [pdf_path]
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from document_structuring_agent.preprocessing.ocr import pdf_to_ocr_document

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def main(pdf_path: Path) -> None:
    """Run OCR and print results."""
    import time

    print(f"Processing: {pdf_path}")
    print("Loading Docling (first run downloads models, may take a few minutes)...")
    sys.stdout.flush()

    t0 = time.time()
    doc = pdf_to_ocr_document(pdf_path)
    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s\n")

    print("=" * 60)
    print("HTML OUTPUT")
    print("=" * 60)
    print(doc.html)
    print()

    print("=" * 60)
    print("ELEMENT METADATA")
    print("=" * 60)
    for idx, meta in sorted(doc.element_metadata.items()):
        flags = []
        if meta.is_bold:
            flags.append("bold")
        if meta.is_italic:
            flags.append("italic")
        if meta.is_page_header:
            flags.append("page_header")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(
            f"  idx={idx}: page={meta.page_number} "
            f"bbox=({meta.left:.0f},{meta.top:.0f},{meta.width:.0f},{meta.height:.0f}) "
            f"conf={meta.confidence:.2f}{flag_str}"
        )

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  source_filename: {doc.source_filename}")
    print(f"  num_elements: {len(doc.element_metadata)}")
    print(f"  html_length: {len(doc.html)} chars")

    # Also dump as JSON for full inspection
    out_path = pdf_path.with_suffix(".ocr_output.json")
    with out_path.open("w") as f:
        json.dump(doc.model_dump(mode="json"), f, indent=2)
    print(f"\n  Full JSON written to: {out_path}")


if __name__ == "__main__":
    path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("tests/fixtures/pdf/sample_credit_agreement.pdf")
    )
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)
    main(path)
