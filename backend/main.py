import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import init_db
from backend.routers.email import router as email_router
from backend.routers.lpo import router as lpo_router
from backend.services.email_ingest import email_service

logger = logging.getLogger(__name__)

app = FastAPI(title="LPO Consolidator API")

# CORS middleware - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(lpo_router)
app.include_router(email_router)

# Scheduler instance (initialized on startup if email ingestion is enabled)
_scheduler = None


@app.on_event("startup")
async def startup_event():
    global _scheduler
    await init_db()

    # Start email polling scheduler if enabled
    if email_service.config.enabled and email_service.config.is_configured:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.interval import IntervalTrigger

            _scheduler = AsyncIOScheduler()
            _scheduler.add_job(
                email_service.poll,
                trigger=IntervalTrigger(minutes=email_service.config.poll_interval),
                id="email_poll",
                name="Poll email inbox for LPO PDFs",
                replace_existing=True,
            )
            _scheduler.start()
            logger.info(
                f"Email polling scheduler started "
                f"(interval: {email_service.config.poll_interval} minutes)"
            )
        except ImportError:
            logger.warning(
                "apscheduler not installed. Email polling scheduler disabled. "
                "Install with: pip install apscheduler"
            )
        except Exception as e:
            logger.error(f"Failed to start email polling scheduler: {e}")
    else:
        logger.info("Email ingestion is disabled or not configured")


@app.on_event("shutdown")
async def shutdown_event():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Email polling scheduler stopped")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


# Serve static frontend files in production (when built frontend exists)
# This must come AFTER API routes so /api/* takes priority
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
