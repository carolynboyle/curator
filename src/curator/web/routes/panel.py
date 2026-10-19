"""Detail panel content routes.

Serves a single entity's full panel content (tab bar, fieldkit-driven
form, child-tab placeholders, action buttons), rendered via
_detail_panel_content.html, for detail-panel.js to fetch-and-swap into
.detail-panel on every panel open (new record or existing).

Previously rendered only _detail_form_fields.html — the bare field
<div>s, no tab bar or form wrapper — which silently wiped out the tab
bar on every open, since detail-panel.js replaces .detail-panel's
entire innerHTML. Fixed by rendering the same content template
_detail_panel.html's (now-empty, invisible) initial render delegates
to. See CHANGEDOC_DETAIL_PANEL_CONTENT_SPLIT.md for the full diagnosis.

Mirrors crew.py's raw jinja2.Environment setup rather than introducing
FastAPI's Jinja2Templates as a second templating convention.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from dbkit.connection import AsyncDBConnection
from curator.formkit import FormActions
from curator.web.deps import get_db
from curator.web.routes.contacts import _fetch_contact_for_display
from curator.web.routes.organizations import _fetch_organization_for_display
from curator.web.routes.projects import _fetch_project_for_display
from curator.web.routes.tasks import _fetch_task_for_display
from curator.web.routes.seanchai import _fetch_record_for_display, _fetch_search_for_display

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
_FORMS_PATH = Path(__file__).parent.parent.parent / "data" / "forms.yaml"
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
    "tasks": _fetch_task_for_display,
    "records": _fetch_record_for_display,
    "searches": _fetch_search_for_display,
}


def _render_panel_content(
    request: Request, entity: str, record: dict, record_id
) -> HTMLResponse:
    """Render the full panel-content template for one entity + record.

    Args:
        request:   Current request — used to reach app.state.fieldkit,
                   the FieldKit cache built once at FastAPI startup.
        entity:    One of "projects", "contacts", "organizations".
        record:    Field values dict, or {} for a new record.
        record_id: The record's id, or '' for a new record — set on
                   the <form> data attributes JS reads.

    Returns:
        HTMLResponse — the rendered content (tab bar, form, child-tab
        placeholders, action buttons), ready to be swapped into
        .detail-panel's innerHTML by detail-panel.js.
    """
    kit = request.app.state.fieldkit[entity]
    detail_panel_actions = FormActions.from_yaml(_FORMS_PATH, "detail_panel")
    template = env.get_template("partials/_detail_panel_content.html")
    return HTMLResponse(
        template.render(
            entity=entity,
            record_id=record_id,
            record=record,
            fields=kit.fields,
            options=kit.options,
            actions=detail_panel_actions["actions"],
            container_class=detail_panel_actions["container_class"],
        )
    )


# /panel/{entity}/new must be declared before /panel/{entity}/{record_id}
# — same route-ordering rule as the save routes (literal before
# parameterized), otherwise FastAPI tries to parse "new" as an int and
# 422s instead of matching this route.

@router.get("/panel/{entity}/new")
async def panel_new(entity: str, request: Request):
    """Render the full panel content for a new, empty record.

    Any query parameters on the request are forwarded into the record
    dict verbatim — e.g. /panel/tasks/new?project_id=12 pre-fills the
    Tasks form's hidden project_id field with '12'. This is the only
    mechanism for prefilling a new-record panel; it stays entity-
    agnostic on purpose (panel.py never checks entity to decide which
    query params are meaningful — that's fieldkit_overrides.yaml's
    job, via which fields exist and are marked hidden). A query param
    with no matching field name is simply ignored by
    _detail_form_fields.html's record.get(field.name) lookups.
    """
    if entity not in _FETCH_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")
    record = dict(request.query_params)
    return _render_panel_content(request, entity, record, "")


@router.get("/panel/{entity}/{record_id}")
async def panel_existing(
    entity: str,
    record_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Render the full panel content for an existing record."""
    if entity not in _FETCH_FUNCTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")

    fetch_fn = _FETCH_FUNCTIONS[entity]
    record = await fetch_fn(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"{entity.title()} not found")

    return _render_panel_content(request, entity, record, record_id)
