"""Detail panel field-fragment routes.

Serves a single entity's field-input fragment, rendered via fieldkit,
for detail-panel.js to fetch-and-swap into the form container on every
panel open (new record or existing). Replaces the old approach of one
static per-entity form baked into _detail_panel.html at page load.

Mirrors crew.py's raw jinja2.Environment setup rather than introducing
FastAPI's Jinja2Templates as a second templating convention.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from dbkit.connection import AsyncDBConnection
from curator.web.deps import get_db
from curator.web.routes.contacts import _fetch_contact_for_display
from curator.web.routes.organizations import _fetch_organization_for_display
from curator.web.routes.projects import _fetch_project_for_display

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

router = APIRouter()

# Entity name -> its _fetch_*_for_display function. Small, fixed set of
# wiring decisions, same reasoning as app.py's _FIELDKIT_VIEWS: adding
# an entity means adding routes/templates alongside it regardless, so
# there's no scenario where this changes without a code change too.
_FETCH_FUNCTIONS = {
    "projects": _fetch_project_for_display,
    "contacts": _fetch_contact_for_display,
    "organizations": _fetch_organization_for_display,
}


def _render_fields(request: Request, entity: str, record: dict) -> HTMLResponse:
    """Render the field-fragment template for one entity + record.

    Args:
        request: Current request — used to reach app.state.fieldkit,
                 the FieldKit cache built once at FastAPI startup.
        entity:  One of "projects", "contacts", "organizations".
        record:  Field values dict, or {} for a new record.

    Returns:
        HTMLResponse — the rendered fragment, ready to be swapped into
        #detail-form-fields by detail-panel.js.
    """
    kit = request.app.state.fieldkit[entity]
    template = env.get_template("partials/_detail_form_fields.html")
    return HTMLResponse(
        template.render(fields=kit.fields, record=record, options=kit.options)
    )


# /panel/{entity}/new must be declared before /panel/{entity}/{record_id}
# — same route-ordering rule as the save routes (literal before
# parameterized), otherwise FastAPI tries to parse "new" as an int and
# 422s instead of matching this route.

@router.get("/panel/{entity}/new")
async def panel_new(entity: str, request: Request):
    """Render the field fragment for a new, empty record."""
    if entity not in _FETCH_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")
    return _render_fields(request, entity, {})


@router.get("/panel/{entity}/{record_id}")
async def panel_existing(
    entity: str,
    record_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Render the field fragment for an existing record."""
    if entity not in _FETCH_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")

    fetch_fn = _FETCH_FUNCTIONS[entity]
    record = await fetch_fn(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"{entity.title()} not found")

    return _render_fields(request, entity, record)
