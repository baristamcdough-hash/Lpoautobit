import io
from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_pdf_success(client: AsyncClient, sample_pdf_bytes: bytes):
    """Test successful PDF upload stores document and extracts data."""
    response = await client.post(
        "/api/lpo/upload",
        files=[("files", ("test_lpo.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] is not None
    assert len(data["documents"]) == 1
    doc = data["documents"][0]
    assert doc["filename"] == "test_lpo.pdf"
    assert doc["status"] == "completed"
    assert doc["customer_name"] is not None


@pytest.mark.asyncio
async def test_upload_non_pdf_returns_400(client: AsyncClient):
    """Test upload with non-PDF file returns 400 error."""
    content = b"This is not a PDF"
    response = await client.post(
        "/api/lpo/upload",
        files=[("files", ("test.txt", io.BytesIO(content), "text/plain"))],
    )
    assert response.status_code == 400
    assert "Only PDF files" in response.json()["detail"]


@pytest.mark.asyncio
async def test_fallback_extraction_works(client: AsyncClient, sample_pdf_bytes: bytes):
    """Test that the fallback extractor works when no API key is set."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
        response = await client.post(
            "/api/lpo/upload",
            files=[("files", ("test_lpo.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
        )
        assert response.status_code == 200
        data = response.json()
        doc = data["documents"][0]
        assert doc["status"] == "completed"
        # The fallback should extract at least some items
        assert doc["customer_name"] is not None


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
