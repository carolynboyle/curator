"""Project routes — CRUD for projects.projects via api.save_project /
api.delete_project.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, Request
from dbkit.connection import AsyncDBConnection
from curator.web.deps import (
    get_db,
    call_proc_and_refetch,
    delete_via_proc,
    get_detail_or_404,
    get_user_id,
    require_name,
    _fetch_json_scalar,
)

router = APIRouter()


async def _fetch_project_for_display(db: AsyncDBConnection, project_id: int) -> dict:
    """Fetch a project via api.get_project_detail() for the detail panel.

    Returns dict with id, name, description, type_id, status_id keys —
    the columns in projects.v_project_detail — or None if not found.

    No longer returns joined type/status *name* strings (the old direct
    query's `type`/`status` columns) or `slug`: v_project_detail is a
    whitelist of editable fields only. Nothing downstream reads those —
    detail-panel.js's populateForm() only maps name/type_id/status_id/
    description/title.
    """
    return await _fetch_json_scalar(
        db, "SELECT api.get_project_detail(%s)", (project_id,)
    )


async def _resolve_type_status_names(
    db: AsyncDBConnection, type_id, status_id
) -> tuple:
    """Look up type and status name strings from their ids.

    api.save_project() takes name strings, not ids, so the browser's
    type_id/status_id selections are translated here before the proc call.
    Either id may be None; returns (type_name, status_name), each possibly
    None if not found or not provided.
    """
    type_name = None
    if type_id:
        row = await db.fetch_one(
            "SELECT name FROM projects.project_type WHERE id = %s", (type_id,)
        )
        type_name = row["name"] if row else None

    status_name = None
    if status_id:
        row = await db.fetch_one(
            "SELECT name FROM projects.project_status WHERE id = %s", (status_id,)
        )
        status_name = row["name"] if row else None

    return type_name, status_name


async def _fetch_records(db: AsyncDBConnection, role: str, search: str) -> list:
    """Fetch role-filtered projects, optionally filtered by search term.

    Returns list of dicts with id, name, type, type_id, status, status_id.

    One query handles both the filtered and unfiltered case: when search
    is empty, "%s = ''" is true and every row matches regardless of the
    ILIKE clause; when search is non-empty, that first comparison is
    false and the ILIKE clause does the actual filtering. Avoids
    duplicating the SELECT/JOIN body for a difference that's really just
    one WHERE condition.
    """
    view_name = f"projects.{role}_view"

    sql = f"""
        SELECT
            p.id,
            p.name::text,
            p.slug::text,
            p.description::text,
            ps.name::text  AS status,
            pt.name::text  AS type,
            p.type_id,
            p.status_id
        FROM {view_name} p
        LEFT JOIN projects.project_status ps ON ps.id = p.status_id
        LEFT JOIN projects.project_type   pt ON pt.id = p.type_id
        WHERE %s = '' OR p.name ILIKE %s
        ORDER BY p.name
    """
    rows = await db.fetch_all(sql, (search, f"%{search}%"))

    return [dict(r) for r in rows]

# -- Single project fetch (for detail panel) ----------------------------------

@router.get("/crew/projects/{project_id}")
async def get_project(
    project_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Fetch a single project as JSON for the detail panel."""
    return await get_detail_or_404(
        db, _fetch_project_for_display, project_id, "Project not found"
    )


# -- Project save routes ------------------------------------------------------
# /crew/projects/save must be declared before /crew/projects/{project_id}/save
# to prevent "save" matching as a project_id integer.

@router.post("/crew/projects/save")
async def save_new_project(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new project via api.save_project().

    Accepts JSON body: {name, type_id, status_id, description, crew_role_id}
    Returns the new project record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name, duplicate name. The message is
    proc-supplied and safe to display directly in the UI. data is None
    for most failures but may carry extra context (e.g. conflicting_id
    on a duplicate-name rejection) for future UI features to consume.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None
    description = body.get("description") or None

    rejection = require_name(name)
    if rejection:
        return rejection

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = get_user_id(request)

    payload = {
        "name": name,
        "type": type_name,
        "status": status_name,
        # Owning crew role; api.save_project defaults to the Captain
        "crew_role_id": body.get("crew_role_id") or None,
    }
    # Only send description when the caller sent it — the grid doesn't,
    # and an absent key leaves the stored value alone.
    if "description" in body:
        payload["description"] = description

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_project_for_display,
        None,
        "Insert succeeded but fetch failed",
    )


@router.post("/crew/projects/{project_id}/save")
async def save_project(
    project_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing project via api.save_project().

    Accepts JSON body: {name, type_id, status_id, description, crew_role_id}
    — description and crew_role_id are optional and left unchanged if absent.
    Returns the updated project record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name, duplicate name, project not found. data
    is None for most failures but may carry extra context (e.g.
    conflicting_id on a duplicate-name rejection) for future UI features
    to consume.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None
    description = body.get("description") or None

    rejection = require_name(name)
    if rejection:
        return rejection

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = get_user_id(request)

    payload = {
        "id": project_id,
        "name": name,
        "type": type_name,
        "status": status_name,
    }
    # Only send fields the caller sent: api.save_project leaves absent
    # fields unchanged. The projects grid sends name/type/status only;
    # sending description=None from there used to blank it.
    if "description" in body:
        payload["description"] = description
    if body.get("crew_role_id"):
        payload["crew_role_id"] = body["crew_role_id"]

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_project_for_display,
        project_id,
        "Save succeeded but fetch failed",
    )


@router.delete("/crew/projects/{project_id}")
async def delete_project(
    project_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Delete a project by id via api.delete_project().

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. not found, or blocked by dependent records (foreign key violation).
    """
    user_id = get_user_id(request)
    return await delete_via_proc(
        db, "SELECT api.delete_project(%s, %s)", (project_id, user_id)
    )
