"""Organization routes — CRUD for identity.organizations via
api.save_organization / api.delete_organization.

Split out of crew.py's route monolith (2026-07-01 changedoc).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from dbkit.connection import AsyncDBConnection
from curator.web.deps import get_db, call_proc, call_proc_and_refetch, _fetch_json_scalar

router = APIRouter()


async def _fetch_organizations(db: AsyncDBConnection) -> list:
    """Fetch all organizations with their contact IDs.

    Returns list of dicts: id, name, contact_ids.
    contact_ids is a list of contact IDs belonging to this org.
    """
    sql = """
        SELECT
            o.id,
            o.name::text,
            COALESCE(
                ARRAY_AGG(oc.contact_id) FILTER (WHERE oc.contact_id IS NOT NULL),
                '{}'
            ) AS contact_ids
        FROM identity.organizations o
        LEFT JOIN identity.organization_contacts oc ON oc.organization_id = o.id
        GROUP BY o.id, o.name
        ORDER BY o.name
    """
    rows = await db.fetch_all(sql)
    result = []
    for r in rows:
        d = dict(r)
        d["contact_ids"] = list(d["contact_ids"]) if d["contact_ids"] else []
        result.append(d)
    return result


async def _fetch_organization_for_display(db: AsyncDBConnection, organization_id: int) -> dict:
    """Fetch an organization via api.get_organization_detail() for the
    detail panel.

    Returns dict with id, name, notes keys — matches the old direct
    query's shape exactly — or None if not found.
    """
    return await _fetch_json_scalar(
        db, "SELECT api.get_organization_detail(%s)", (organization_id,)
    )


# -- Single organization fetch (for detail panel) ------------------------------

@router.get("/crew/organizations/{organization_id}")
async def get_organization(
    organization_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Fetch a single organization as JSON for the detail panel."""
    record = await _fetch_organization_for_display(db, organization_id)
    if not record:
        raise HTTPException(status_code=404, detail="Organization not found")
    return JSONResponse(dict(record))


# -- Organization save routes ---------------------------------------------------
# /crew/organizations/save must be declared before
# /crew/organizations/{organization_id}/save to prevent "save" matching as
# an organization_id integer.

@router.post("/crew/organizations/save")
async def save_new_organization(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new organization via api.save_organization().

    Accepts JSON body: {name, notes}
    Returns the new organization record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name, duplicate name.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    notes = body.get("notes") or None

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {"name": name, "notes": notes}

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_organization(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_organization_for_display,
        None,
        "Insert succeeded but fetch failed",
    )


@router.post("/crew/organizations/{organization_id}/save")
async def save_organization(
    organization_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing organization via api.save_organization().

    Accepts JSON body: {name, notes}
    Returns the updated organization record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name, duplicate name, organization not found.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    notes = body.get("notes") or None

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {"id": organization_id, "name": name, "notes": notes}

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_organization(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_organization_for_display,
        organization_id,
        "Save succeeded but fetch failed",
    )


@router.delete("/crew/organizations/{organization_id}")
async def delete_organization(
    organization_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Delete an organization by id via api.delete_organization().

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. not found, or blocked by dependent records (foreign key violation).
    """
    user_id = request.state.user["user_id"] if request.state.user else None

    envelope = await call_proc(
        db,
        "SELECT api.delete_organization(%s, %s)",
        (organization_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)
