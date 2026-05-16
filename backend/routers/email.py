"""API endpoints for email ingestion status and manual trigger."""

from fastapi import APIRouter

from backend.services.email_ingest import email_service

router = APIRouter(prefix="/api/email", tags=["Email Ingestion"])


@router.get("/status")
async def email_status():
    """Get the current status of the email ingestion service.

    Returns:
        - enabled: Whether email ingestion is enabled
        - configured: Whether credentials are set
        - last_poll_time: ISO timestamp of last poll
        - emails_processed_today: Count of emails processed today
        - poll_interval_minutes: Configured polling interval
        - recent_errors: Last 5 errors (if any)
    """
    return email_service.get_status()


@router.post("/poll")
async def trigger_poll():
    """Manually trigger an immediate email poll.

    Useful for testing without waiting for the scheduled interval.

    Returns:
        Poll results including emails_found, pdfs_processed, and any errors.
    """
    if not email_service.config.enabled:
        return {
            "status": "disabled",
            "message": "Email ingestion is not enabled. Set EMAIL_ENABLED=true to activate.",
        }

    results = await email_service.poll()
    return results
