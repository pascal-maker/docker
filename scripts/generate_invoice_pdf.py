"""Generate a two-page invoice test PDF with a line-items table and payment terms.

Usage:
    uv run --with fpdf2 python scripts/generate_invoice_pdf.py [output_path]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fpdf import FPDF


def _add_line_items_table(pdf: FPDF) -> None:
    """Add the invoice line-items table to the PDF."""
    col_w = [90, 20, 35, 35]

    # Header row
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(col_w[0], 8, "Description", border=1)
    pdf.cell(col_w[1], 8, "Qty", border=1, align="C")
    pdf.cell(col_w[2], 8, "Unit Price", border=1, align="R")
    pdf.cell(col_w[3], 8, "Total", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    # Data rows
    rows = [
        ("Software License - Annual", "3", "$1,200.00", "$3,600.00"),
        ("Implementation Services", "20", "$150.00", "$3,000.00"),
        ("Training Workshop (1 day)", "1", "$800.00", "$800.00"),
        ("Support Package - 6 months", "1", "$500.00", "$500.00"),
    ]
    pdf.set_font("Helvetica", "", 11)
    for desc, qty, unit, total in rows:
        pdf.cell(col_w[0], 8, desc, border=1)
        pdf.cell(col_w[1], 8, qty, border=1, align="C")
        pdf.cell(col_w[2], 8, unit, border=1, align="R")
        pdf.cell(col_w[3], 8, total, border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    # Totals rows
    label_w = col_w[0] + col_w[1] + col_w[2]
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(label_w, 8, "Subtotal", border=1, align="R")
    pdf.cell(
        col_w[3], 8, "$7,900.00", border=1, align="R", new_x="LMARGIN", new_y="NEXT"
    )

    pdf.cell(label_w, 8, "Tax (8.5%)", border=1, align="R")
    pdf.cell(col_w[3], 8, "$671.50", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(label_w, 8, "TOTAL DUE", border=1, align="R")
    pdf.cell(
        col_w[3], 8, "$8,571.50", border=1, align="R", new_x="LMARGIN", new_y="NEXT"
    )


def main(output_path: Path) -> None:  # noqa: PLR0915
    """Generate a two-page invoice test PDF."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Page 1: Invoice body ---
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 14, "INVOICE", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Sender block
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Acme Supplies Ltd", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "200 Commerce Road, Austin, TX 78701", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "invoice@acmesupplies.com", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "+1 512 555 0100", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Invoice metadata
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Invoice No: INV-2024-0042", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "Invoice Date: March 15, 2024", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Due Date: April 14, 2024", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Bill To block
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Bill To:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "Bright Horizons LLC", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "88 Tech Park Drive", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "San Francisco, CA 94107", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Line items table
    _add_line_items_table(pdf)

    # --- Page 2: Payment terms and notes ---
    pdf.add_page()

    # Payment Terms section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Payment Terms", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        6,
        "Payment is due within 30 days of the invoice date. "
        "Please remit payment by April 14, 2024.",
    )
    pdf.ln(2)
    pdf.multi_cell(
        0,
        6,
        "Accepted methods: Bank transfer (ACH/Wire), company check.",
    )
    pdf.ln(6)

    # Bank Transfer Details section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Bank Transfer Details", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, "Bank: First National Bank", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Account Name: Acme Supplies Ltd", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Routing No: 021000021", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Account No: 987654321", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Notes section
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Notes", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        6,
        "Please reference invoice number INV-2024-0042 in your payment.",
    )
    pdf.ln(2)
    pdf.multi_cell(
        0,
        6,
        "Late payments are subject to a 1.5% monthly finance charge.",
    )
    pdf.ln(8)

    # Footer
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, "Thank you for your business.", new_x="LMARGIN", new_y="NEXT")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    dest = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("tests/fixtures/pdf/sample_invoice.pdf")
    )
    main(dest)
