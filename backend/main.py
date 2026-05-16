import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import init_db
from backend.routers.lpo import router as lpo_router

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


@app.on_event("startup")
async def startup_event():
    await init_db()


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


# Serve static frontend files in production (when built frontend exists)
# This must come AFTER API routes so /api/* takes priority
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
