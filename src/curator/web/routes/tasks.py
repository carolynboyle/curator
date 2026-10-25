"""Task routes — CRUD for projects.tasks via api.save_task /
api.delete_task.

Mirrors contacts.py/organizations.py's structure exactly — same
deps.py helpers, same route shapes, same save/delete error contract.
Tasks have no "name" field (they use "description" instead), so the
blank-field guard is a local check rather than deps.py's require_name()
— see _require_description() below.
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from dbkit.connection import AsyncDBConnection
from curator.web.deps import (
    get_db,
    call_proc_and_refetch,
    delete_via_proc,
    get_detail_or_404,
    get_user_id,
    _fetch_json_scalar,
)

router = APIRouter()


async def _fetch_task_for_display(db: AsyncDBConnection, task_id: int) -> dict:
    """Fetch a task via api.get_task_detail() for the detail panel.

    Returns dict with id, project_id, parent_id, description, notes,
    status_id, priority_id keys — matches projects.v_task_detail's
    whitelist — or None if not found.
    """
    return await _fetch_json_scalar(
        db, "SELECT api.get_task_detail(%s)", (task_id,)
    )


def _require_description(description: str):
    """Return a rejection response if description is blank, else None.

    Tasks don't have a "name" field — deps.py's require_name() is
    name-specific in both the field it checks and its message text, so
    this is a small local equivalent rather than a forced reuse. If a
    third entity ever needs the same "required text field, different
    name" shape, that's the point to extract a generic version into
    deps.py — two occurrences doesn't yet justify it.

    NOTE — this is a cheap early-exit for the single most common blank
    submission, not a complete mirror of api.save_task()'s validation.
    Confirmed against the live function body (2026-07-10):
    api.save_task() itself also rejects a missing/null project_id
    ("A project is required.") and a missing/null status_id ("Task
    status is required."), each returning its own
    {"success": false, ...} envelope. Those two are deliberately NOT
    re-checked here — project_id always arrives via the hidden field
    (set from context, never user-typed, so effectively always
    present), and status_id's presence depends on the form having a
    sensible default value (see the default-status discussion —
    unresolved as of this changedoc). This function only exists to
    save a round trip on the one rejection a person can trivially
    cause themselves (leaving description blank); the proc remains the
    real authority for project_id/status_id, and call_proc_and_refetch
    already forwards its rejection message straight through to the UI
    if either is somehow missing.
    """
    if not description:
        return JSONResponse({
            "success": False,
            "message": "Description is required.",
            "data": None,
        })
    return None


# -- Single task fetch (for detail panel) -------------------------------------

@router.get("/crew/tasks/{task_id}/linked-records")
async def get_task_linked_records(
    task_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Return seanchai records linked to a task via seanchai.task_records.

    Calls api.get_task_linked_records(task_id) — returns a JSON array of
    [{id, record_id, type_code, record_type, year, subject, county,
      source_citation, source_url}] ordered by display_order then record_id.
    Returns [] when the task has no linked records.

    Used by the task detail panel to surface source records (and their
    clickable source_url links) without requiring navigation to the Records
    tab. Route must be declared before /crew/tasks/{task_id} so the path
    segment 'linked-records' is not parsed as a task_id integer.
    """
    result = await _fetch_json_scalar(
        db, "SELECT api.get_task_linked_records(%s)", (task_id,)
    )
    # api function returns a JSONB array; _fetch_json_scalar returns it as
    # a Python list/None. Normalise to list so the JS always gets an array.
    if result is None:
        result = []
    return JSONResponse(result)


@router.get("/crew/tasks/{task_id}")
async def get_task(
    task_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Fetch a single task as JSON for the detail panel."""
    return await get_detail_or_404(
        db, _fetch_task_for_display, task_id, "Task not found"
    )


# -- Task save routes ----------------------------------------------------------
# /crew/tasks/save must be declared before /crew/tasks/{task_id}/save to
# prevent "save" matching as a task_id integer.

@router.post("/crew/tasks/save")
async def save_new_task(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new task via api.save_task().

    Accepts JSON body: {description, notes, status_id, priority_id,
    project_id, parent_id}. project_id arrives from the form's hidden
    field (pre-filled by panel.py's panel_new() from the ?project_id=
    query param — see nested_master_detail_design.md). parent_id is
    '' for a top-level task.

    Returns the new task record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure. api.save_task() enforces, in order: description required,
    project_id required and must reference an existing project,
    status_id required and must reference an existing task_status,
    parent_id (if given) must belong to the same project and not equal
    the task's own id. Only the description check is duplicated in
    Python (see _require_description) — the rest are the proc's alone.
    """
    body = await request.json()
    description = (body.get("description") or "").strip()
    notes = body.get("notes") or None
    status_id = body.get("status_id") or None
    priority_id = body.get("priority_id") or None
    project_id = body.get("project_id") or None
    parent_id = body.get("parent_id") or None

    rejection = _require_description(description)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {
        "description": description,
        "notes": notes,
        "status_id": status_id,
        "priority_id": priority_id,
        "project_id": project_id,
        "parent_id": parent_id,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_task(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_task_for_display,
        None,
        "Insert succeeded but fetch failed",
    )


@router.post("/crew/tasks/{task_id}/save")
async def save_task(
    task_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing task via api.save_task().

    Accepts JSON body: {description, notes, status_id, priority_id,
    project_id, parent_id}.

    Returns the updated task record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — task not found, plus the same description/project_id/
    status_id/parent_id validation api.save_task() enforces on insert
    (see save_new_task's docstring above for the full list).
    """
    body = await request.json()
    description = (body.get("description") or "").strip()
    notes = body.get("notes") or None
    status_id = body.get("status_id") or None
    priority_id = body.get("priority_id") or None
    project_id = body.get("project_id") or None
    parent_id = body.get("parent_id") or None

    rejection = _require_description(description)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {
        "id": task_id,
        "description": description,
        "notes": notes,
        "status_id": status_id,
        "priority_id": priority_id,
        "project_id": project_id,
        "parent_id": parent_id,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_task(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_task_for_display,
        task_id,
        "Save succeeded but fetch failed",
    )


@router.delete("/crew/tasks/{task_id}")
async def delete_task(
    task_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Delete a task by id via api.delete_task().

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. not found, or blocked by undeleted child tasks (per
    api.delete_task()'s explicit child-task detection,
    CHANGEDOC_TASKS_SQL_LAYER.md).
    """
    user_id = get_user_id(request)
    return await delete_via_proc(
        db, "SELECT api.delete_task(%s, %s)", (task_id, user_id)
    )
