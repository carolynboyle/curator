"""
curator.web.app - FastAPI application entry point.

Creates and configures the FastAPI app instance, mounts static files,
and registers route modules. Imported by uvicorn as the ASGI entry point.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dbkit.connection import AsyncDBConnection
from curator.web.fieldkit import FieldKit
from curator.web.middleware import SessionMiddleware


# ---------------------------------------------------------------------------
# Fieldkit cache — entity name -> schema-qualified view name.
#
# Explicit here rather than in curator.yaml: this is a small, fixed set
# of wiring decisions (which view backs which entity's form), similar in
# spirit to the router registrations below, not user-facing deployment
# config. Adding an entity means adding routes/templates alongside it
# regardless, so there's no scenario where this list changes without a
# code change happening at the same time.
# ---------------------------------------------------------------------------

from curator.web.routes import (
    auth, landing, crew, panel, projects, contacts, organizations, tasks,
    project_links, seanchai,
)

_FIELDKIT_VIEWS = {
    "projects": "projects.v_project_detail",
    "contacts": "identity.v_contact_detail",
    "organizations": "identity.v_organization_detail",
    "tasks": "projects.v_task_detail",
    "records": "seanchai.v_record_detail",
    "searches": "seanchai.v_search_detail",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Build the fieldkit cache once at startup, before serving any request.

    Opens its own connection — this runs outside any request context, so
    the per-request get_db dependency isn't available here.

    Deliberately does NOT catch FieldSchemaError. A misconfigured view or
    a *_id/integer column with no override entry must crash uvicorn
    immediately, not surface later as a broken form in front of Felipe.
    See fieldkit.py and curator/exceptions.py's FieldSchemaError
    docstring for the full reasoning.
    """
    async with AsyncDBConnection() as db:
        _app.state.fieldkit = {
            entity: await FieldKit.create(db, view_name)
            for entity, view_name in _FIELDKIT_VIEWS.items()
        }
    yield
    # No teardown — app.state.fieldkit holds FieldDef data only, no open
    # resources to release.


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
    lifespan=lifespan,
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
app.include_router(panel.router)
app.include_router(projects.router)
app.include_router(contacts.router)
app.include_router(organizations.router)
app.include_router(tasks.router)
app.include_router(project_links.router)
app.include_router(seanchai.router)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
