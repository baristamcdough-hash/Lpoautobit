import csv
import io
from datetime import date

import pytest
import pytest_asyncio
from backend.models import LPODocument, LPOLineItem


@pytest.mark.asyncio
async def test_export_csv_returns_200(client, db_session):
    """Test that GET /api/lpo/export?format=csv returns 200 with text/csv content-type."""
    # Insert test data
    doc = LPODocument(filename="test.pdf", customer_name="Test Hotel", status="completed")
    db_session.add(doc)
    await db_session.flush()

    item = LPOLineItem(
        document_id=doc.id,
        item_name="Tomatoes",
        quantity=5.0,
        unit="Crates",
        date_extracted=date.today(),
    )
    db_session.add(item)
    await db_session.commit()

    response = await client.get("/api/lpo/export?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_export_csv_has_correct_headers(client, db_session):
    """Test that the raw CSV export contains correct headers."""
    doc = LPODocument(filename="test.pdf", customer_name="Safari Hotel", status="completed")
    db_session.add(doc)
    await db_session.flush()

    item = LPOLineItem(
        document_id=doc.id,
        item_name="Potatoes",
        quantity=10.0,
        unit="Bags",
        date_extracted=date.today(),
    )
    db_session.add(item)
    await db_session.commit()

    response = await client.get("/api/lpo/export?format=csv&type=raw")
    assert response.status_code == 200

    reader = csv.reader(io.StringIO(response.text))
    headers = next(reader)
    assert headers == ["Date", "Customer Name", "Item Name", "Quantity", "Unit"]


@pytest.mark.asyncio
async def test_export_date_filtering(client, db_session):
    """Test that date filtering returns only items from specified date."""
    doc = LPODocument(filename="test.pdf", customer_name="Test Hotel", status="completed")
    db_session.add(doc)
    await db_session.flush()

    # Item for today
    item_today = LPOLineItem(
        document_id=doc.id,
        item_name="Tomatoes",
        quantity=5.0,
        unit="Crates",
        date_extracted=date.today(),
    )
    # Item for a different date
    item_other = LPOLineItem(
        document_id=doc.id,
        item_name="Onions",
        quantity=3.0,
        unit="Bags",
        date_extracted=date(2020, 1, 1),
    )
    db_session.add(item_today)
    db_session.add(item_other)
    await db_session.commit()

    # Filter for 2020-01-01
    response = await client.get("/api/lpo/export?format=csv&date=2020-01-01&type=raw")
    assert response.status_code == 200

    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    # Header + 1 data row
    assert len(rows) == 2
    assert rows[1][2] == "Onions"


@pytest.mark.asyncio
async def test_export_picklist_type(client, db_session):
    """Test that picklist export type returns aggregated data."""
    doc1 = LPODocument(filename="test1.pdf", customer_name="Hotel A", status="completed")
    doc2 = LPODocument(filename="test2.pdf", customer_name="Hotel B", status="completed")
    db_session.add(doc1)
    db_session.add(doc2)
    await db_session.flush()

    # Two items with same name from different customers
    item1 = LPOLineItem(
        document_id=doc1.id,
        item_name="Tomatoes",
        quantity=5.0,
        unit="Crates",
        date_extracted=date.today(),
    )
    item2 = LPOLineItem(
        document_id=doc2.id,
        item_name="Tomatoes",
        quantity=3.0,
        unit="Crates",
        date_extracted=date.today(),
    )
    db_session.add(item1)
    db_session.add(item2)
    await db_session.commit()

    response = await client.get("/api/lpo/export?format=csv&type=picklist")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    content = response.text
    # Should contain aggregated total (5 + 3 = 8.0)
    assert "8.0" in content
    # Should contain both customers in distribution
    assert "Hotel A" in content
    assert "Hotel B" in content
