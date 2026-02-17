"""Generate a simple test PDF with headings, paragraphs, and a table.

Usage:
    uv run --with fpdf2 python scripts/generate_test_pdf.py [output_path]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fpdf import FPDF


def _add_definition_table(pdf: FPDF) -> None:
    """Add the Article I definitions table to the PDF."""
    col_w = [50, 130]
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(col_w[0], 8, "Term", border=1)
    pdf.cell(col_w[1], 8, "Definition", border=1, new_x="LMARGIN", new_y="NEXT")

    rows = [
        ("Borrower", "XYZ Corporation, a Delaware corporation"),
        ("Commitment", "The aggregate amount of $50,000,000"),
        ("Maturity Date", "January 1, 2029"),
        ("Interest Rate", "Base Rate plus 2.00% per annum"),
    ]
    pdf.set_font("Helvetica", "", 11)
    for term, definition in rows:
        pdf.cell(col_w[0], 8, term, border=1)
        pdf.cell(col_w[1], 8, definition, border=1, new_x="LMARGIN", new_y="NEXT")


def main(output_path: Path) -> None:
    """Generate a multi-element test PDF."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Page 1 ---
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "Sample Credit Agreement", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Intro paragraph
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        6,
        (
            "This Credit Agreement is entered into as of January 1, 2024, "
            "by and between XYZ Corporation (the Borrower) and ABC Bank "
            "(the Lender)."
        ),
    )
    pdf.ln(4)

    # Section heading
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Article I - Definitions", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        6,
        "Section 1.1. The following terms have the meanings set forth below:",
    )
    pdf.ln(4)

    # Table
    _add_definition_table(pdf)
    pdf.ln(6)

    # Another section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Article II - Representations", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        6,
        (
            "The Borrower represents that it is a corporation duly organized, "
            "validly existing, and in good standing under the laws of the "
            "State of Delaware."
        ),
    )
    pdf.ln(4)

    # Signature block
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Signatures", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "XYZ Corporation", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "By: _________________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Name: John Executive", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Title: Chief Executive Officer", new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(output_path))
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    dest = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("tests/fixtures/pdf/sample_credit_agreement.pdf")
    )
    main(dest)
