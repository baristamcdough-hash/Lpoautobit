"""End-to-end integration tests for the LPO Consolidator pipeline."""

import csv
import io
from datetime import date

import pytest


@pytest.mark.asyncio
async def test_full_pipeline(client, sample_pdf_bytes):
    """
    End-to-end test that:
    1. Uploads a sample PDF via POST /api/lpo/upload
    2. Verifies the document appears in GET /api/lpo/raw-data
    3. Verifies GET /api/lpo/dashboard shows correct aggregation
    4. Verifies GET /api/lpo/export returns the uploaded data in CSV format
    """
    # Step 1: Upload a sample PDF
    files = [("files", ("safari_hotel_lpo.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))]
    upload_response = await client.post("/api/lpo/upload", files=files)
    assert upload_response.status_code == 200

    upload_data = upload_response.json()
    assert len(upload_data["documents"]) == 1
    doc = upload_data["documents"][0]
    assert doc["status"] == "completed"
    assert doc["customer_name"] == "Safari Hotel"

    # Step 2: Verify the document appears in raw data
    raw_response = await client.get("/api/lpo/raw-data")
    assert raw_response.status_code == 200

    raw_data = raw_response.json()
    assert len(raw_data) > 0

    # Verify expected items are present
    item_names = [item["item_name"] for item in raw_data]
    assert "Tomatoes" in item_names
    assert "Potatoes" in item_names

    # Step 3: Verify dashboard shows correct aggregation
    today = date.today().isoformat()
    dashboard_response = await client.get(f"/api/lpo/dashboard?date_filter={today}")
    assert dashboard_response.status_code == 200

    dashboard_data = dashboard_response.json()
    assert dashboard_data["date"] == today
    assert len(dashboard_data["master_procurement"]) > 0
    assert len(dashboard_data["distribution"]) > 0

    # Verify Safari Hotel is in the distribution
    customer_names = [d["customer_name"] for d in dashboard_data["distribution"]]
    assert "Safari Hotel" in customer_names

    # Step 4: Verify export returns the uploaded data
    export_response = await client.get(f"/api/lpo/export?format=csv&date={today}&type=raw")
    assert export_response.status_code == 200
    assert "text/csv" in export_response.headers["content-type"]

    reader = csv.reader(io.StringIO(export_response.text))
    rows = list(reader)
    # Should have header + at least 1 data row
    assert len(rows) >= 2
    headers = rows[0]
    assert headers == ["Date", "Customer Name", "Item Name", "Quantity", "Unit"]

    # Verify Safari Hotel data is in the export
    customer_names_in_csv = [row[1] for row in rows[1:]]
    assert "Safari Hotel" in customer_names_in_csv


@pytest.mark.asyncio
async def test_multiple_uploads_aggregate_correctly(client, sample_pdf_bytes):
    """Test that uploading multiple PDFs correctly aggregates in dashboard."""
    # Upload the same PDF twice (simulates two different customers)
    files = [("files", ("safari_hotel_lpo.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))]
    await client.post("/api/lpo/upload", files=files)
    files = [("files", ("safari_hotel_lpo.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))]
    await client.post("/api/lpo/upload", files=files)

    # Check dashboard shows aggregation
    today = date.today().isoformat()
    dashboard_response = await client.get(f"/api/lpo/dashboard?date_filter={today}")
    assert dashboard_response.status_code == 200

    dashboard_data = dashboard_response.json()
    # Master procurement should have aggregated quantities
    for item in dashboard_data["master_procurement"]:
        if item["item_name"] == "Tomatoes":
            # Two uploads of 5 each = 10 total
            assert item["total_quantity"] == 10.0
            break
