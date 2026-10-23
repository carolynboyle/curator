"""Crew role dashboard routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader

from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.formkit import FormActions
from curator.web.deps import _fetch_json_scalar, get_config, get_db
from curator.web.routes.contacts import _fetch_contacts
from curator.web.routes.organizations import _fetch_organizations
from curator.web.routes.projects import _fetch_records

# Initialize QueryLoader for /api/query endpoint
_QUERIES_PATH = Path(__file__).parent.parent.parent / "data" / "queries.yaml"
_FORMS_PATH   = Path(__file__).parent.parent.parent / "data" / "forms.yaml"
_query_builder = QueryBuilder(_QUERIES_PATH)
_query_loader  = QueryLoader(_query_builder)

router = APIRouter()

# Initialize Jinja2 for crew dashboard
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

# Tab definitions per role — static, read-only, shared across all requests.
# Each tab references a partial in templates/partials/.
# Future: load from database (identity.landing_card).
_ROLE_TABS = {
    "captain": [
        {"id": "projects",      "label": "Projects",      "template": "_tab_projects.html"},
        {"id": "identities",    "label": "Identities",    "template": "_tab_identities.html"},
        {
            "id": "configuration",
            "label": "Configuration",
            "template": "_tab_configuration.html",
        },
    ],
    "scribe": [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
    ],
    "mechanic": [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
    ],
    "envoy": [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
    ],
    # The Seanchaí: projects plus the research ledger. The ledger tabs
    # reuse the grids that used to live on the standalone /seanchai/ page
    # (which now redirects here). Their element ids (tab-records,
    # tab-searches) are what those grids' scripts expect.
    "seanchai": [
        {"id": "projects", "label": "Projects", "template": "_tab_projects.html"},
        {"id": "records",  "label": "Records",  "template": "_records_table.html"},
        {"id": "searches", "label": "Searches", "template": "_searches_table.html"},
    ],
}

_IMG_DIR = Path(__file__).parent.parent.parent.parent.parent / "static" / "img"
_DEFAULT_TABS = [
    {"id": "projects", "label": "Projects", "template": "_tab_projects.html"}
]


async def _fetch_lookups(db: AsyncDBConnection) -> dict:
    """Fetch project type and status lookup tables.

    Returns dict with 'types' and 'statuses' lists of dicts.
    Each dict has 'id' and 'name' keys.
    """
    types_sql = "SELECT id, name::text FROM projects.project_type ORDER BY name"
    statuses_sql = "SELECT id, name::text FROM projects.project_status ORDER BY name"

    types = await db.fetch_all(types_sql)
    statuses = await db.fetch_all(statuses_sql)

    return {
        "types": [dict(r) for r in types],
        "statuses": [dict(r) for r in statuses],
    }


@router.get("/api/query/{entity}/{query_name}")
async def run_query(
    entity: str,
    query_name: str,
    params: str = Query(""),
    db: AsyncDBConnection = Depends(get_db),
):
    """Generic query endpoint driven by queries.yaml.

    Used by _datasheet_with_header.html's Tabulator instances for child
    datasheets (Tasks, Emails, Phones, URLs, Organizations tabs).

    Query parameters:
        params: comma-separated string of positional SQL params

    Response is passed through jsonable_encoder() rather than returned
    as a plain dict — this endpoint serves whatever queries.yaml defines,
    present and future, and jsonable_encoder() handles types plain
    json.dumps() can't (datetime, Decimal, UUID) without every query
    author needing to remember an explicit ::text cast. queries.yaml
    should still cast consistently (see its own convention) — this is a
    backstop, not a replacement for that.
    """
    params_list = params.split(",") if params else []
    try:
        sql = _query_loader.sql(entity, query_name)
        rows = await db.fetch_all(sql, params_list)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(jsonable_encoder({"records": [dict(r) for r in rows]}))


# -- Dashboard ----------------------------------------------------------------

async def _render_crew_dashboard_html(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    role: str,
    role_meta: dict,
    config: ConfigManager,
    db: AsyncDBConnection,
    records: list,
    search: str,
):
    """Render the full crew dashboard HTML page.

    Separated from crew_dashboard() so that route handles routing/param
    fetching, and the JSON-request short-circuit for Tabulator's Ajax
    calls. The two were previously one function; separated because they
    are genuinely different jobs (serve JSON vs. render a full page) that
    happened to share a route.

    Takes 6 parameters (one over pylint's default threshold of 5). All 6
    are genuinely needed — role/role_meta/search describe the current
    request context, config/db/records are runtime dependencies.
    Restructuring into a context object would add indirection without
    improving clarity. Left as-is by design, with the disable directive
    on the function that actually has 6 parameters — it used to sit as a
    prose-only comment above crew_dashboard (5 parameters, never needed
    it) and never suppressed anything, since pylint only responds to the
    real disable-comment syntax, not an explanation that reads like one.
    """
    lookups = await _fetch_lookups(db)

    # The role's own id — new projects created on this dashboard belong to
    # it (window.newRecordDefaults in crew.html).
    role_rows = await db.fetch_all(
        "SELECT id FROM identity.crew_role WHERE name = %s", (role,)
    )
    crew_role_id = role_rows[0]["id"] if role_rows else None

    # Research-ledger lookups for the Seanchaí's Records grid
    if role == "seanchai":
        record_types = await _fetch_json_scalar(db, "SELECT api.list_record_types()", ())
        record_statuses = await _fetch_json_scalar(
            db, "SELECT api.list_record_statuses()", ()
        )
    else:
        record_types = []
        record_statuses = []

    # Crew illustration; falls back to the Curator's until the role has one
    hero_image = f"{role}.png" if (_IMG_DIR / f"{role}.png").exists() else "curator.png"

    # Fetch captain-only data
    if role == "captain":
        contacts = await _fetch_contacts(db)
        organizations = await _fetch_organizations(db)
    else:
        contacts = []
        organizations = []

    template = env.get_template("crew.html")
    detail_panel_actions = FormActions.from_yaml(_FORMS_PATH, "detail_panel")

    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "crew_role_id": crew_role_id,
        "hero_image": hero_image,
        "record_types": record_types or [],
        "record_statuses": record_statuses or [],
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
        "contacts": contacts,
        "organizations": organizations,
        "tabs": _ROLE_TABS.get(role, _DEFAULT_TABS),
        "actions": detail_panel_actions["actions"],
        "container_class": detail_panel_actions["container_class"],
    }

    return HTMLResponse(template.render(**data))


@router.get("/crew")
async def crew_dashboard(
    request: Request,
    role: str = Query("captain"),
    search: str = Query(""),
    config: ConfigManager = Depends(get_config),
    db: AsyncDBConnection = Depends(get_db),
):
    """Crew dashboard — displays projects filtered by crew role.

    Query parameters:
        role:   One of the roles defined in curator.yaml
        search: Optional name filter (ILIKE match)

    JSON requests (Accept: application/json) return records for Tabulator.
    HTML requests return the full page template (see
    _render_crew_dashboard_html).
    """
    crew_roles = config.get("crew", "roles")
    valid_roles = [r["name"] for r in crew_roles]

    if role not in valid_roles:
        role = "captain"  # Safe fallback

    role_meta = next((r for r in crew_roles if r["name"] == role), None)

    records = await _fetch_records(db, role, search)

    # Tabulator Ajax requests — return JSON
    accept = request.headers.get("Accept", "")
    if "application/json" in accept:
        return JSONResponse({"records": records})

    return await _render_crew_dashboard_html(
        role, role_meta, config, db, records, search
    )
