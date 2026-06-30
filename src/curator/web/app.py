"""
curator.web.app - FastAPI application entry point.

Creates and configures the FastAPI app instance, mounts static files,
and registers route modules. Imported by uvicorn as the ASGI entry point.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from curator.web.middleware import SessionMiddleware
from curator.web.routes import landing, crew
from curator.web.routes import auth

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
)

# ---------------------------------------------------------------------------
# Middleware
# Must be added before routers are registered.
# SessionMiddleware validates curator_session cookie on every request.
# ---------------------------------------------------------------------------

app.add_middleware(SessionMiddleware)

# ---------------------------------------------------------------------------
# Static files — resolved relative to this file: src/curator/web/ -> static/
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parents[3] / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Routers
# Auth must be registered first — /auth/login is the public entry point.
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(landing.router)
app.include_router(crew.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
