import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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
    # Mount static assets (JS, CSS bundles) at /assets
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Serve other static files (favicon, icons, etc.) at their paths
    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon():
        favicon_path = os.path.join(static_dir, "favicon.svg")
        if os.path.exists(favicon_path):
            with open(favicon_path, "r") as f:
                return HTMLResponse(content=f.read(), media_type="image/svg+xml")

    @app.get("/icons.svg", include_in_schema=False)
    async def icons():
        icons_path = os.path.join(static_dir, "icons.svg")
        if os.path.exists(icons_path):
            with open(icons_path, "r") as f:
                return HTMLResponse(content=f.read(), media_type="image/svg+xml")

    # SPA fallback: serve index.html for all non-API, non-static routes
    # This enables client-side routing (React Router, etc.)
    _index_html_path = os.path.join(static_dir, "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        with open(_index_html_path, "r") as f:
            return HTMLResponse(content=f.read())
