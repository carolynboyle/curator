"""Project link routes — CRUD for projects.project_links via
api.save_project_link / api.delete_project_link.

Mirrors tasks.py's structure exactly — same deps.py helpers, same
route shapes, same save/delete error contract.

Links have no "name" field (they use "label" instead), so the
blank-field guard is a local check rather than deps.py's require_name()
— see _require_label() below.

Unlike the entity routes (projects.py, contacts.py, etc.), there is no
GET /crew/project_links/{id} route: the detail panel never opens a
link in a full panel — links are managed through the embedded links
widget in the project Details tab. Reads go through
/api/query/project_links/for_project (crew.py's generic query endpoint),
and the fetch function here is used only by call_proc_and_refetch after
a save.
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from dbkit.connection import AsyncDBConnection
from curator.web.deps import (
    get_db,
    call_proc_and_refetch,
    delete_via_proc,
    get_user_id,
    _fetch_json_scalar,
)

router = APIRouter()


async def _fetch_link_for_display(db: AsyncDBConnection, link_id: int) -> dict:
    """Fetch a single project_link row as a plain dict.

    Used by call_proc_and_refetch after a save — re-fetches the saved
    row so the widget can update its local state without a full list
    reload from the server. Returns None if not found.

    Unlike the entity fetch functions (which call a dedicated
    api.get_*_detail() proc), links are simple enough that a direct
    row_to_json query avoids the proc overhead — the same JSON envelope
    contract applies either way.
    """
    return await _fetch_json_scalar(
        db,
        """SELECT row_to_json(r)
           FROM (
               SELECT id, project_id, label::text, url::text, sort_order
               FROM projects.project_links
               WHERE id = %s
           ) r""",
        (link_id,),
    )


def _require_label(label: str):
    """Return a rejection response if label is blank, else None.

    Same reasoning as tasks.py's _require_description(): label is the
    one field the user can trivially leave blank; the early-exit here
    saves a round trip. api.save_project_link() remains the real
    authority for all other validation.
    """
    if not label:
        return JSONResponse({
            "success": False,
            "message": "Label is required.",
            "data": None,
        })
    return None


# -- Save routes ---------------------------------------------------------------
# /crew/project_links/save must be declared before
# /crew/project_links/{link_id}/save to prevent "save" matching as an integer.

@router.post("/crew/project_links/save")
async def save_new_link(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new project link via api.save_project_link().

    Accepts JSON body: {project_id, label, url}. url is optional and
    may be omitted or sent as null/"" — a link with no URL yet is valid
    (the label can serve as a placeholder note like "Find this thing").

    Returns the new link record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": null} (200) on
    failure — blank label, missing project_id, or proc-level validation.
    """
    body = await request.json()
    label      = (body.get("label") or "").strip()
    project_id = body.get("project_id") or None
    url        = (body.get("url") or "").strip() or None

    rejection = _require_label(label)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {
        "project_id": project_id,
        "label":      label,
        "url":        url,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_project_link(%s::jsonb, %s)",
        (json.dumps(payload), user_id),
        _fetch_link_for_display,
        None,
        "Insert succeeded but link fetch failed",
    )


@router.post("/crew/project_links/{link_id}/save")
async def save_link(
    link_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Update an existing project link via api.save_project_link().

    Accepts JSON body: {label, url}. project_id is not required for an
    update — the proc looks up the row by id.

    Returns the updated link record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": null} (200) on
    failure — blank label, link not found, or proc-level rejection.
    """
    body = await request.json()
    label = (body.get("label") or "").strip()
    url   = (body.get("url") or "").strip() or None

    rejection = _require_label(label)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {
        "id":    link_id,
        "label": label,
        "url":   url,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_project_link(%s::jsonb, %s)",
        (json.dumps(payload), user_id),
        _fetch_link_for_display,
        link_id,
        "Save succeeded but link fetch failed",
    )


@router.delete("/crew/project_links/{link_id}")
async def delete_link(
    link_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Delete a project link by id via api.delete_project_link().

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. link not found.
    """
    user_id = get_user_id(request)
    return await delete_via_proc(
        db,
        "SELECT api.delete_project_link(%s, %s)",
        (link_id, user_id),
    )
