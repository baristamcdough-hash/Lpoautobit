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
from typing import List


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
