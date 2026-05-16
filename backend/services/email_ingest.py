"""Email ingestion service for polling Gmail inbox for PDF LPO attachments.

Connects via IMAP to a configured Gmail inbox, downloads PDF attachments
from unread emails, and processes them through the existing AI extraction
pipeline (same as /api/lpo/upload).

Configuration is via environment variables. The service is completely optional
and disabled unless EMAIL_ENABLED=true is set.
"""

import email
import imaplib
import logging
import os
from datetime import date, datetime
from email.message import Message
from typing import Any, Dict, List, Optional

from backend.database import async_session
from backend.models import LPODocument, LPOLineItem
from backend.services.ai_extractor import extract_lpo_data
from backend.services.pdf_parser import extract_text_from_pdf

logger = logging.getLogger(__name__)


class EmailIngestConfig:
    """Configuration for email ingestion, sourced from environment variables."""

    def __init__(self):
        self.enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.imap_host = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
        self.imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
        self.email_address = os.getenv("EMAIL_ADDRESS", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")
        self.poll_interval = int(os.getenv("EMAIL_POLL_INTERVAL", "5"))

    @property
    def is_configured(self) -> bool:
        """Check if all required credentials are provided."""
        return bool(self.email_address and self.email_password)


class EmailIngestService:
    """Service for polling a Gmail inbox and processing PDF attachments."""

    def __init__(self, config: Optional[EmailIngestConfig] = None):
        self.config = config or EmailIngestConfig()
        self.last_poll_time: Optional[datetime] = None
        self.emails_processed_today: int = 0
        self.last_poll_date: Optional[date] = None
        self.recent_errors: List[str] = []
        self._max_errors = 10

    def get_status(self) -> Dict[str, Any]:
        """Return current status of the email ingestion service."""
        # Reset daily counter if date changed
        if self.last_poll_date and self.last_poll_date != date.today():
            self.emails_processed_today = 0

        return {
            "enabled": self.config.enabled,
            "configured": self.config.is_configured,
            "last_poll_time": self.last_poll_time.isoformat() if self.last_poll_time else None,
            "emails_processed_today": self.emails_processed_today,
            "poll_interval_minutes": self.config.poll_interval,
            "recent_errors": self.recent_errors[-5:],
        }

    def _add_error(self, error_msg: str):
        """Add an error to the recent errors list, keeping only the last N."""
        timestamp = datetime.utcnow().isoformat()
        self.recent_errors.append(f"[{timestamp}] {error_msg}")
        if len(self.recent_errors) > self._max_errors:
            self.recent_errors = self.recent_errors[-self._max_errors:]

    async def poll(self) -> Dict[str, Any]:
        """Poll the inbox for unread emails with PDF attachments.

        Returns:
            Dict with poll results: emails_found, pdfs_processed, errors
        """
        if not self.config.enabled:
            return {"status": "disabled", "message": "Email ingestion is not enabled"}

        if not self.config.is_configured:
            return {"status": "error", "message": "Email credentials not configured"}

        logger.info(
            f"Starting email poll for {self.config.email_address} "
            f"via {self.config.imap_host}:{self.config.imap_port}"
        )

        results = {
            "emails_found": 0,
            "pdfs_processed": 0,
            "errors": [],
        }

        connection = None
        try:
            connection = self._connect()
            email_ids = self._fetch_unread_email_ids(connection)
            results["emails_found"] = len(email_ids)

            if not email_ids:
                logger.info("No unread emails found")
            else:
                logger.info(f"Found {len(email_ids)} unread email(s)")

            for email_id in email_ids:
                try:
                    pdfs_processed = await self._process_email(connection, email_id)
                    results["pdfs_processed"] += pdfs_processed
                    self._mark_as_read(connection, email_id)
                except Exception as e:
                    error_msg = f"Error processing email {email_id}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    self._add_error(error_msg)
                    # Continue processing other emails
                    continue

        except Exception as e:
            error_msg = f"Email poll failed: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
            self._add_error(error_msg)
        finally:
            if connection:
                try:
                    connection.logout()
                except Exception:
                    pass

        # Update status tracking
        self.last_poll_time = datetime.utcnow()
        if self.last_poll_date != date.today():
            self.emails_processed_today = 0
            self.last_poll_date = date.today()
        self.emails_processed_today += results["pdfs_processed"]

        logger.info(
            f"Email poll complete: {results['emails_found']} emails found, "
            f"{results['pdfs_processed']} PDFs processed"
        )

        return results

    def _connect(self) -> imaplib.IMAP4_SSL:
        """Establish IMAP connection to the email server."""
        connection = imaplib.IMAP4_SSL(
            self.config.imap_host, self.config.imap_port
        )
        connection.login(self.config.email_address, self.config.email_password)
        connection.select("INBOX")
        return connection

    def _fetch_unread_email_ids(self, connection: imaplib.IMAP4_SSL) -> List[bytes]:
        """Fetch IDs of all unread emails in the inbox."""
        status, data = connection.search(None, "UNSEEN")
        if status != "OK":
            raise RuntimeError(f"IMAP search failed with status: {status}")

        email_ids = data[0].split() if data[0] else []
        return email_ids

    def _get_email_message(self, connection: imaplib.IMAP4_SSL, email_id: bytes) -> Message:
        """Fetch and parse a single email message."""
        status, data = connection.fetch(email_id, "(RFC822)")
        if status != "OK":
            raise RuntimeError(f"Failed to fetch email {email_id}")

        raw_email = data[0][1]
        return email.message_from_bytes(raw_email)

    def _extract_pdf_attachments(self, msg: Message) -> List[Dict[str, Any]]:
        """Extract PDF attachments from an email message.

        Returns:
            List of dicts with 'filename' and 'content' (bytes) keys.
        """
        pdfs = []

        if not msg.is_multipart():
            return pdfs

        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Check for PDF attachments
            if content_type == "application/pdf" or (
                "attachment" in content_disposition
                and part.get_filename()
                and part.get_filename().lower().endswith(".pdf")
            ):
                filename = part.get_filename() or "attachment.pdf"
                content = part.get_payload(decode=True)
                if content:
                    pdfs.append({"filename": filename, "content": content})

        return pdfs

    async def _process_email(self, connection: imaplib.IMAP4_SSL, email_id: bytes) -> int:
        """Process a single email: extract PDF attachments and run them through the pipeline.

        Returns:
            Number of PDFs successfully processed.
        """
        msg = self._get_email_message(connection, email_id)
        subject = msg.get("Subject", "No Subject")
        sender = msg.get("From", "Unknown")
        logger.info(f"Processing email from {sender}: {subject}")

        pdfs = self._extract_pdf_attachments(msg)
        if not pdfs:
            logger.info(f"No PDF attachments in email from {sender}: {subject}")
            return 0

        processed_count = 0
        for pdf_info in pdfs:
            try:
                await self._process_pdf(pdf_info["filename"], pdf_info["content"])
                processed_count += 1
            except Exception as e:
                error_msg = f"Failed to process PDF '{pdf_info['filename']}': {e}"
                logger.error(error_msg)
                self._add_error(error_msg)

        return processed_count

    async def _process_pdf(self, filename: str, file_bytes: bytes):
        """Process a single PDF through the extraction pipeline.

        This mirrors the logic in the /api/lpo/upload endpoint.
        """
        # Check file size (10 MB limit)
        if len(file_bytes) > 10 * 1024 * 1024:
            raise ValueError(f"PDF '{filename}' exceeds 10MB size limit")

        async with async_session() as db:
            # Create document record
            doc = LPODocument(
                filename=f"[email] {filename}",
                status="processing",
            )
            db.add(doc)
            await db.flush()

            # Extract text from PDF
            text = extract_text_from_pdf(file_bytes)

            if not text:
                doc.status = "error"
                await db.commit()
                logger.warning(f"No text extracted from PDF: {filename}")
                return

            # Extract structured data using AI or fallback
            try:
                extracted = await extract_lpo_data(text)
                doc.customer_name = extracted.get("customer_name", "Unknown")
                doc.status = "completed"

                # Create line items
                for item in extracted.get("line_items", []):
                    line_item = LPOLineItem(
                        document_id=doc.id,
                        item_name=item["item_name"],
                        quantity=float(item["quantity"]),
                        unit=item["unit"],
                        date_extracted=date.today(),
                    )
                    db.add(line_item)
            except Exception as e:
                doc.status = "error"
                logger.error(f"Extraction failed for {filename}: {e}")

            await db.commit()
            logger.info(f"Successfully processed PDF: {filename} -> {doc.customer_name}")

    def _mark_as_read(self, connection: imaplib.IMAP4_SSL, email_id: bytes):
        """Mark an email as read (add \\Seen flag)."""
        connection.store(email_id, "+FLAGS", "\\Seen")


# Module-level singleton instance
email_service = EmailIngestService()
