"""Script to generate sample LPO PDF files for testing."""

import os
import sys
from datetime import date
from pathlib import Path

from fpdf import FPDF


def create_lpo_pdf(
    customer_name: str,
    customer_address: str,
    lpo_number: str,
    items: list,
    output_path: str,
):
    """Generate a realistic-looking LPO PDF.

    Args:
        customer_name: Name of the customer/business.
        customer_address: Address of the customer.
        lpo_number: LPO reference number.
        items: List of tuples (item_name, quantity, unit, unit_price).
        output_path: Path to save the PDF file.
    """
    pdf = FPDF()
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(190, 12, text="LOCAL PURCHASE ORDER", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # LPO Details
    pdf.set_font("Helvetica", size=11)
    pdf.cell(95, 8, text=f"LPO No: {lpo_number}", new_x="RIGHT", new_y="TOP")
    pdf.cell(95, 8, text=f"Date: {date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(5)

    # Customer Info
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 8, text="Customer Details:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(190, 7, text=f"Customer: {customer_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(190, 7, text=f"Address: {customer_address}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Items Table Header
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(10, 8, text="#", border=1, align="C")
    pdf.cell(70, 8, text="Item Description", border=1, align="C")
    pdf.cell(30, 8, text="Quantity", border=1, align="C")
    pdf.cell(30, 8, text="Unit", border=1, align="C")
    pdf.cell(25, 8, text="Unit Price", border=1, align="C")
    pdf.cell(25, 8, text="Total", border=1, new_x="LMARGIN", new_y="NEXT", align="C")

    # Items
    pdf.set_font("Helvetica", size=10)
    grand_total = 0
    for i, (item_name, quantity, unit, unit_price) in enumerate(items, 1):
        total = quantity * unit_price
        grand_total += total
        pdf.cell(10, 7, text=str(i), border=1, align="C")
        pdf.cell(70, 7, text=item_name, border=1)
        pdf.cell(30, 7, text=str(quantity), border=1, align="C")
        pdf.cell(30, 7, text=unit, border=1, align="C")
        pdf.cell(25, 7, text=f"{unit_price:.0f}", border=1, align="R")
        pdf.cell(25, 7, text=f"{total:.0f}", border=1, new_x="LMARGIN", new_y="NEXT", align="R")

    # Total
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(140, 8, text="GRAND TOTAL (KES)", border=1, align="R")
    pdf.cell(50, 8, text=f"{grand_total:,.0f}", border=1, new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(10)

    # Footer
    pdf.set_font("Helvetica", size=9)
    pdf.cell(190, 6, text="Authorized Signature: ___________________", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(190, 6, text="Terms: Delivery within 24 hours of order. Payment Net 30.", new_x="LMARGIN", new_y="NEXT")

    # Save
    pdf.output(output_path)
    print(f"  Created: {output_path}")


def main():
    """Generate sample LPO PDFs."""
    output_dir = Path(__file__).parent.parent / "sample_pdfs"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating sample LPO PDFs...")

    # Safari Hotel LPO
    create_lpo_pdf(
        customer_name="Safari Hotel",
        customer_address="Mombasa Road, Nairobi",
        lpo_number="LPO-2024-001",
        items=[
            ("Tomatoes", 5, "Crates", 1500),
            ("Potatoes", 10, "Bags", 2500),
            ("Sukuma Wiki", 3, "Bunches", 200),
        ],
        output_path=str(output_dir / "safari_hotel_lpo.pdf"),
    )

    # Kilimani School LPO
    create_lpo_pdf(
        customer_name="Kilimani School",
        customer_address="Kilimani, Nairobi",
        lpo_number="LPO-2024-002",
        items=[
            ("Tomatoes", 3, "Crates", 1500),
            ("Potatoes", 8, "Bags", 2500),
            ("Onions", 15, "Nets", 1800),
        ],
        output_path=str(output_dir / "kilimani_school_lpo.pdf"),
    )

    # Junction Grocers LPO
    create_lpo_pdf(
        customer_name="Junction Grocers",
        customer_address="Junction Mall, Ngong Road, Nairobi",
        lpo_number="LPO-2024-003",
        items=[
            ("Onions", 20, "Nets", 1800),
            ("Tomatoes", 5, "Crates", 1500),
            ("Carrots", 2, "Bags", 3000),
        ],
        output_path=str(output_dir / "junction_grocers_lpo.pdf"),
    )

    print(f"\nDone! Generated 3 sample PDFs in {output_dir}/")


if __name__ == "__main__":
    main()
