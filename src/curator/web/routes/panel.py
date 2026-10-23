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


def _render_task_fragment(
    request: Request, record: dict, record_id
) -> HTMLResponse:
    """Render the lightweight task form fragment for the nested Tasks tab.

    Unlike _render_panel_content(), which renders the full panel body
    (tab bar, all tabs, action buttons), this renders only a minimal
    task form + its own action buttons — swapped into #task-form-container
    inside the Tasks tab without touching the project panel around it.

    The fragment uses form id="task-form" (not "detail-form") so
    detail-panel.js's getForm() can distinguish task context from project
    context and branch Save/New/Discard behavior accordingly.
    """
    kit = request.app.state.fieldkit["tasks"]
    actions = FormActions.to_dicts(
        FormActions.detail_panel_actions(form_id="task-form")
    )
    template = env.get_template("partials/_task_form_fragment.html")
    return HTMLResponse(
        template.render(
            record_id=record_id,
            record=record,
            fields=kit.fields,
            options=kit.options,
            actions=actions,
            container_class="detail-panel-actions",
        )
    )


# /panel/tasks/new/nested and /panel/tasks/{task_id}/nested must be declared
# before /panel/{entity}/new and /panel/{entity}/{record_id} — more-specific
# literal paths before the parameterized catch-all, otherwise FastAPI would
# try to parse "tasks" as the record_id int and 422.

@router.get("/panel/tasks/new/nested")
async def panel_task_new_nested(request: Request):
    """Render a blank task form fragment for inline creation inside the Tasks tab."""
    record = dict(request.query_params)
    return _render_task_fragment(request, record, "")


@router.get("/panel/tasks/{task_id}/nested")
async def panel_task_nested(
    task_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Render an existing task's form fragment for inline editing inside the Tasks tab."""
    record = await _fetch_task_for_display(db, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    return _render_task_fragment(request, record, task_id)


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
