import io
from datetime import date

import pytest
from httpx import AsyncClient


async def _upload_pdf(client: AsyncClient, customer_name: str, items: list) -> None:
    """Helper to upload a PDF with specific content."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(200, 10, text="LOCAL PURCHASE ORDER", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, text=f"Customer: {customer_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text=f"Date: {date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="Items Ordered:", new_x="LMARGIN", new_y="NEXT")
    for item in items:
        pdf.cell(200, 10, text=item, new_x="LMARGIN", new_y="NEXT")

    pdf_bytes = pdf.output()

    response = await client.post(
        "/api/lpo/upload",
        files=[("files", (f"{customer_name.lower().replace(' ', '_')}.pdf", io.BytesIO(pdf_bytes), "application/pdf"))],
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_dashboard_aggregation(client: AsyncClient):
    """Test dashboard returns correct aggregation when multiple customers order the same items."""
    # Upload two LPOs with overlapping items
    await _upload_pdf(client, "Safari Hotel", [
        "5 Crates Tomatoes",
        "10 Bags Potatoes",
    ])
    await _upload_pdf(client, "Kilimani School", [
        "3 Crates Tomatoes",
        "8 Bags Potatoes",
    ])

    response = await client.get(f"/api/lpo/dashboard?date_filter={date.today().isoformat()}")
    assert response.status_code == 200
    data = response.json()

    assert data["date"] == date.today().isoformat()

    # Check master procurement aggregation
    procurement = {item["item_name"].lower(): item for item in data["master_procurement"]}
    assert "tomatoes" in procurement
    assert procurement["tomatoes"]["total_quantity"] == 8.0  # 5 + 3
    assert "potatoes" in procurement
    assert procurement["potatoes"]["total_quantity"] == 18.0  # 10 + 8


@pytest.mark.asyncio
async def test_dashboard_date_filtering(client: AsyncClient):
    """Test date filtering returns only items from specified date."""
    # Upload a document (defaults to today)
    await _upload_pdf(client, "Safari Hotel", [
        "5 Crates Tomatoes",
    ])

    # Query for a different date should return empty
    response = await client.get("/api/lpo/dashboard?date_filter=2020-01-01")
    assert response.status_code == 200
    data = response.json()
    assert data["master_procurement"] == []
    assert data["distribution"] == []


@pytest.mark.asyncio
async def test_distribution_breakdown(client: AsyncClient):
    """Test distribution breakdown groups correctly by customer."""
    await _upload_pdf(client, "Safari Hotel", [
        "5 Crates Tomatoes",
        "10 Bags Potatoes",
    ])
    await _upload_pdf(client, "Junction Grocers", [
        "20 Nets Onions",
    ])

    response = await client.get(f"/api/lpo/dashboard?date_filter={date.today().isoformat()}")
    assert response.status_code == 200
    data = response.json()

    # Check distribution has both customers
    customers = {entry["customer_name"]: entry for entry in data["distribution"]}
    assert "Safari Hotel" in customers
    assert "Junction Grocers" in customers

    # Safari Hotel should have 2 items
    safari_items = customers["Safari Hotel"]["items"]
    assert len(safari_items) == 2

    # Junction Grocers should have 1 item
    junction_items = customers["Junction Grocers"]["items"]
    assert len(junction_items) == 1
    assert junction_items[0]["item_name"] == "Onions"


@pytest.mark.asyncio
async def test_raw_data_endpoint(client: AsyncClient):
    """Test raw data endpoint returns all line items."""
    await _upload_pdf(client, "Safari Hotel", [
        "5 Crates Tomatoes",
    ])

    response = await client.get(f"/api/lpo/raw-data?date_filter={date.today().isoformat()}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["item_name"] is not None
    assert data[0]["quantity"] > 0
