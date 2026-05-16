"""Tests for the email ingestion service."""

import email
from datetime import date
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.models import LPODocument, LPOLineItem
from backend.services.email_ingest import EmailIngestConfig, EmailIngestService


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session using in-memory SQLite."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """Create an async test client with overridden database dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


def _make_email_with_pdf(pdf_bytes: bytes, filename: str = "order.pdf") -> bytes:
    """Helper to create a raw email message with a PDF attachment."""
    msg = MIMEMultipart()
    msg["From"] = "supplier@example.com"
    msg["To"] = "orders@example.com"
    msg["Subject"] = "New LPO Attached"

    # Add text body
    body = MIMEText("Please find attached our purchase order.", "plain")
    msg.attach(body)

    # Add PDF attachment
    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(pdf_part)

    return msg.as_bytes()


def _make_email_no_attachment() -> bytes:
    """Helper to create a raw email with no PDF attachment."""
    msg = MIMEMultipart()
    msg["From"] = "info@example.com"
    msg["To"] = "orders@example.com"
    msg["Subject"] = "General Inquiry"

    body = MIMEText("No attachment here.", "plain")
    msg.attach(body)

    return msg.as_bytes()


def _sample_pdf_bytes():
    """Generate sample PDF bytes for testing."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(200, 10, text="LOCAL PURCHASE ORDER", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, text="Customer: Test Hotel", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text=f"Date: {date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="Items Ordered:", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="5 Crates Tomatoes", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(200, 10, text="3 Bags Potatoes", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


class TestEmailIngestConfig:
    """Tests for EmailIngestConfig."""

    def test_disabled_by_default(self):
        """Service should be disabled when EMAIL_ENABLED is not set."""
        with patch.dict("os.environ", {}, clear=True):
            config = EmailIngestConfig()
            assert config.enabled is False

    def test_enabled_when_set(self):
        """Service should be enabled when EMAIL_ENABLED=true."""
        with patch.dict("os.environ", {"EMAIL_ENABLED": "true"}):
            config = EmailIngestConfig()
            assert config.enabled is True

    def test_not_configured_without_credentials(self):
        """is_configured should be False without email/password."""
        with patch.dict("os.environ", {"EMAIL_ENABLED": "true"}, clear=True):
            config = EmailIngestConfig()
            assert config.is_configured is False

    def test_configured_with_credentials(self):
        """is_configured should be True with email and password."""
        env = {
            "EMAIL_ENABLED": "true",
            "EMAIL_ADDRESS": "test@gmail.com",
            "EMAIL_PASSWORD": "app-password",
        }
        with patch.dict("os.environ", env, clear=True):
            config = EmailIngestConfig()
            assert config.is_configured is True
            assert config.email_address == "test@gmail.com"
            assert config.imap_host == "imap.gmail.com"
            assert config.imap_port == 993

    def test_custom_poll_interval(self):
        """Poll interval should be configurable."""
        with patch.dict("os.environ", {"EMAIL_POLL_INTERVAL": "10"}):
            config = EmailIngestConfig()
            assert config.poll_interval == 10


class TestEmailIngestService:
    """Tests for EmailIngestService."""

    def test_get_status_disabled(self):
        """Status should reflect disabled state."""
        config = EmailIngestConfig()
        config.enabled = False
        service = EmailIngestService(config=config)

        status = service.get_status()
        assert status["enabled"] is False
        assert status["last_poll_time"] is None
        assert status["emails_processed_today"] == 0

    @pytest.mark.asyncio
    async def test_poll_when_disabled(self):
        """Poll should return disabled message when not enabled."""
        config = EmailIngestConfig()
        config.enabled = False
        service = EmailIngestService(config=config)

        result = await service.poll()
        assert result["status"] == "disabled"

    @pytest.mark.asyncio
    async def test_poll_when_not_configured(self):
        """Poll should return error when credentials missing."""
        config = EmailIngestConfig()
        config.enabled = True
        config.email_address = ""
        config.email_password = ""
        service = EmailIngestService(config=config)

        result = await service.poll()
        assert result["status"] == "error"
        assert "not configured" in result["message"]

    def test_extract_pdf_attachments(self):
        """Should extract PDF attachments from email messages."""
        pdf_bytes = _sample_pdf_bytes()
        raw_email = _make_email_with_pdf(pdf_bytes, "test_lpo.pdf")
        msg = email.message_from_bytes(raw_email)

        config = EmailIngestConfig()
        service = EmailIngestService(config=config)
        pdfs = service._extract_pdf_attachments(msg)

        assert len(pdfs) == 1
        assert pdfs[0]["filename"] == "test_lpo.pdf"
        assert pdfs[0]["content"] == pdf_bytes

    def test_extract_no_pdf_attachments(self):
        """Should return empty list when no PDFs attached."""
        raw_email = _make_email_no_attachment()
        msg = email.message_from_bytes(raw_email)

        config = EmailIngestConfig()
        service = EmailIngestService(config=config)
        pdfs = service._extract_pdf_attachments(msg)

        assert len(pdfs) == 0

    @pytest.mark.asyncio
    async def test_poll_processes_pdfs(self):
        """Should process PDF attachments through the extraction pipeline."""
        pdf_bytes = _sample_pdf_bytes()
        raw_email = _make_email_with_pdf(pdf_bytes, "hotel_order.pdf")

        config = EmailIngestConfig()
        config.enabled = True
        config.email_address = "test@gmail.com"
        config.email_password = "password"
        service = EmailIngestService(config=config)

        # Mock IMAP connection
        mock_conn = MagicMock()
        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        mock_conn.fetch.return_value = ("OK", [(b"1", raw_email)])
        mock_conn.store.return_value = ("OK", [])
        mock_conn.logout.return_value = ("OK", [])

        with patch.object(service, "_connect", return_value=mock_conn):
            # Also patch async_session to use a test db
            engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
            test_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            with patch("backend.services.email_ingest.async_session", test_session_factory):
                result = await service.poll()

            assert result["emails_found"] == 1
            assert result["pdfs_processed"] == 1

            # Verify document was stored in db
            async with test_session_factory() as session:
                docs = (await session.execute(select(LPODocument))).scalars().all()
                assert len(docs) == 1
                assert "[email]" in docs[0].filename
                assert docs[0].status == "completed"

                items = (await session.execute(select(LPOLineItem))).scalars().all()
                assert len(items) > 0

            await engine.dispose()

    @pytest.mark.asyncio
    async def test_emails_marked_as_read(self):
        """Processed emails should be marked as read (Seen flag)."""
        pdf_bytes = _sample_pdf_bytes()
        raw_email = _make_email_with_pdf(pdf_bytes)

        config = EmailIngestConfig()
        config.enabled = True
        config.email_address = "test@gmail.com"
        config.email_password = "password"
        service = EmailIngestService(config=config)

        mock_conn = MagicMock()
        mock_conn.login.return_value = ("OK", [])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        mock_conn.fetch.return_value = ("OK", [(b"1", raw_email)])
        mock_conn.store.return_value = ("OK", [])
        mock_conn.logout.return_value = ("OK", [])

        with patch.object(service, "_connect", return_value=mock_conn):
            engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
            test_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            with patch("backend.services.email_ingest.async_session", test_session_factory):
                await service.poll()

            await engine.dispose()

        # Verify store was called with \\Seen flag
        mock_conn.store.assert_called_with(b"1", "+FLAGS", "\\Seen")

    @pytest.mark.asyncio
    async def test_poll_handles_connection_error(self):
        """Should handle IMAP connection errors gracefully."""
        config = EmailIngestConfig()
        config.enabled = True
        config.email_address = "test@gmail.com"
        config.email_password = "password"
        service = EmailIngestService(config=config)

        with patch.object(service, "_connect", side_effect=Exception("Connection refused")):
            result = await service.poll()

        assert len(result["errors"]) > 0
        assert "Connection refused" in result["errors"][0]
        assert len(service.recent_errors) > 0


class TestEmailEndpoints:
    """Tests for the email API endpoints."""

    @pytest.mark.asyncio
    async def test_get_status(self, client):
        """GET /api/email/status should return service status."""
        response = await client.get("/api/email/status")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "last_poll_time" in data
        assert "emails_processed_today" in data
        assert "recent_errors" in data

    @pytest.mark.asyncio
    async def test_poll_when_disabled(self, client):
        """POST /api/email/poll should return disabled message when not enabled."""
        response = await client.post("/api/email/poll")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"
