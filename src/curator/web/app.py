"""
curator.web.app - FastAPI application factory.

Creates and configures the FastAPI app instance, registers routers,
and sets up Jinja2 templating.

The app instance is imported by route modules to access the templates
object, and by uvicorn as the ASGI entry point.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from curator import plugin

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

templates = Jinja2Templates(
    directory=Path(__file__).parent.parent / "templates"
)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title=plugin["name"],
        version=plugin["version"],
        description=plugin["description"],
    )

    # Static files
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parents[3] / "static"),
        name="static",
    )

    # Routers
    from curator.web.routes import files, projects, tags, tasks
    app.include_router(projects.router)
    app.include_router(tags.router)
    app.include_router(files.router)
    app.include_router(tasks.router)

    return app


app = create_app()
from fastapi import Request
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")