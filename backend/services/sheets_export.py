"""
Google Sheets Export Service

This module provides CSV export functionality for LPO data, generating files
that match the LPO_Raw_Data and Marikiti_Pick_List tab structures.

For production Google Sheets integration, you can extend this module using
the google-api-python-client library:

    1. Install: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    2. Set up a Google Cloud project and enable the Google Sheets API
    3. Create a service account and download the credentials JSON
    4. Share your target spreadsheet with the service account email
    5. Use the Sheets API to write data directly:

        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials

        creds = Credentials.from_service_account_file('credentials.json')
        service = build('sheets', 'v4', credentials=creds)

        body = {'values': [headers] + rows}
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range='LPO_Raw_Data!A1',
            valueInputOption='RAW',
            body=body
        ).execute()

For automated workflows, consider using Make.com or Zapier to watch a Google
Drive folder for new PDFs, trigger the upload endpoint, then write results
to a shared Google Sheet.
"""

import csv
import io
from typing import List, Optional


def generate_raw_data_csv(items: List[dict]) -> str:
    """
    Format LPO line items as CSV with columns matching the LPO_Raw_Data tab.

    Args:
        items: List of dicts with keys: date, customer_name, item_name, quantity, unit

    Returns:
        CSV string with headers: Date, Customer Name, Item Name, Quantity, Unit
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Customer Name", "Item Name", "Quantity", "Unit"])

    for item in items:
        writer.writerow([
            item.get("date", ""),
            item.get("customer_name", ""),
            item.get("item_name", ""),
            item.get("quantity", ""),
            item.get("unit", ""),
        ])

    return output.getvalue()


def generate_pick_list_csv(master_items: List[dict], distribution: List[dict]) -> str:
    """
    Format the consolidated dashboard data as CSV matching the Marikiti_Pick_List tab.

    The output includes two sections:
    1. Master Procurement Totals (Item Name, Total Quantity, Unit)
    2. Distribution Breakdown (Customer Name, Item Name, Quantity, Unit)

    Args:
        master_items: List of dicts with keys: item_name, total_quantity, unit
        distribution: List of dicts with keys: customer_name, items (list of item dicts)

    Returns:
        CSV string with both sections separated by an empty row
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Section 1: Master Procurement Totals
    writer.writerow(["Master Procurement Totals"])
    writer.writerow(["Item Name", "Total Quantity", "Unit"])
    for item in master_items:
        writer.writerow([
            item.get("item_name", ""),
            item.get("total_quantity", ""),
            item.get("unit", ""),
        ])

    # Separator
    writer.writerow([])

    # Section 2: Distribution Breakdown
    writer.writerow(["Distribution Breakdown"])
    writer.writerow(["Customer Name", "Item Name", "Quantity", "Unit"])
    for entry in distribution:
        customer_name = entry.get("customer_name", "")
        for item in entry.get("items", []):
            writer.writerow([
                customer_name,
                item.get("item_name", ""),
                item.get("quantity", ""),
                item.get("unit", ""),
            ])

    return output.getvalue()


def generate_excel_export(
    raw_items: Optional[List[dict]] = None,
    master_items: Optional[List[dict]] = None,
    distribution: Optional[List[dict]] = None,
) -> bytes:
    """
    Generate an Excel (.xlsx) file with professional formatting.

    If raw_items is provided, generates a single sheet with raw data.
    If master_items and distribution are provided, generates two sheets:
    - "Master Procurement" with aggregated totals
    - "Distribution Breakdown" with per-customer breakdown

    Returns:
        bytes: The Excel file content as bytes
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()

    # Header styling
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")

    if raw_items is not None:
        # Raw data export - single sheet
        ws = wb.active
        ws.title = "LPO Raw Data"

        headers = ["Date", "Customer Name", "Item Name", "Quantity", "Unit"]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        for row_idx, item in enumerate(raw_items, 2):
            ws.cell(row=row_idx, column=1, value=item.get("date", ""))
            ws.cell(row=row_idx, column=2, value=item.get("customer_name", ""))
            ws.cell(row=row_idx, column=3, value=item.get("item_name", ""))
            ws.cell(row=row_idx, column=4, value=item.get("quantity", 0))
            ws.cell(row=row_idx, column=5, value=item.get("unit", ""))

        # Auto-adjust column widths
        column_widths = [12, 20, 20, 12, 10]
        for col_idx, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width

    else:
        # Pick list export - two sheets
        # Sheet 1: Master Procurement
        ws1 = wb.active
        ws1.title = "Master Procurement"

        headers = ["Item Name", "Total Quantity", "Unit"]
        for col_idx, header in enumerate(headers, 1):
            cell = ws1.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        for row_idx, item in enumerate(master_items or [], 2):
            ws1.cell(row=row_idx, column=1, value=item.get("item_name", ""))
            ws1.cell(row=row_idx, column=2, value=item.get("total_quantity", 0))
            ws1.cell(row=row_idx, column=3, value=item.get("unit", ""))

        column_widths = [25, 16, 10]
        for col_idx, width in enumerate(column_widths, 1):
            ws1.column_dimensions[get_column_letter(col_idx)].width = width

        # Sheet 2: Distribution Breakdown
        ws2 = wb.create_sheet(title="Distribution Breakdown")

        headers = ["Customer Name", "Item Name", "Quantity", "Unit"]
        for col_idx, header in enumerate(headers, 1):
            cell = ws2.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        row_idx = 2
        for entry in (distribution or []):
            customer_name = entry.get("customer_name", "")
            for item in entry.get("items", []):
                ws2.cell(row=row_idx, column=1, value=customer_name)
                ws2.cell(row=row_idx, column=2, value=item.get("item_name", ""))
                ws2.cell(row=row_idx, column=3, value=item.get("quantity", 0))
                ws2.cell(row=row_idx, column=4, value=item.get("unit", ""))
                row_idx += 1

        column_widths = [20, 20, 12, 10]
        for col_idx, width in enumerate(column_widths, 1):
            ws2.column_dimensions[get_column_letter(col_idx)].width = width

    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
