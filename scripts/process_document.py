"""CLI entrypoint for processing a document through the structuring pipeline.

Usage:
    uv run python scripts/process_document.py <pdf_file>
    uv run python scripts/process_document.py <html_file> <metadata_json>
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from document_structuring_agent.pipeline.graph import process_document

if TYPE_CHECKING:
    from document_structuring_agent.models.ocr_input import OcrDocument


async def main(ocr_doc: OcrDocument) -> None:
    """Process a single document and print the structured output as JSON."""
    from langfuse import get_client

    results = await process_document(ocr_doc)

    output = [r.model_dump(mode="json") for r in results]
    print(json.dumps(output, indent=2))

    # Ensure all Langfuse events are flushed
    langfuse = get_client()
    langfuse.flush()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) == 2:
        # Single arg: PDF mode
        pdf_path = Path(sys.argv[1])
        if not pdf_path.exists():
            print(f"File not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)

        from document_structuring_agent.preprocessing.ocr import pdf_to_ocr_document

        ocr_doc = pdf_to_ocr_document(pdf_path)

    elif len(sys.argv) == 3:
        # Two args: HTML + metadata mode
        html_path = Path(sys.argv[1])
        metadata_path = Path(sys.argv[2])
        if not html_path.exists():
            print(f"HTML file not found: {html_path}", file=sys.stderr)
            sys.exit(1)
        if not metadata_path.exists():
            print(f"Metadata file not found: {metadata_path}", file=sys.stderr)
            sys.exit(1)

        from document_structuring_agent.preprocessing.metadata import load_ocr_document

        ocr_doc = load_ocr_document(html_path, metadata_path)

    else:
        print(
            f"Usage: {sys.argv[0]} <pdf_file>\n"
            f"       {sys.argv[0]} <html_file> <metadata_json>",
            file=sys.stderr,
        )
        sys.exit(1)

    asyncio.run(main(ocr_doc))
