"""Contact routes — CRUD for identity.contacts via api.save_contact /
api.delete_contact.

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


async def _fetch_contacts(db: AsyncDBConnection) -> list:
    """Fetch all contacts with their first email address.

    Returns list of dicts: id, name, title, email, org_ids.
    org_ids is a list of organization IDs this contact belongs to.
    email is the first address from contact_emails, or None.
    """
    sql = """
        SELECT
            c.id,
            c.name::text,
            c.title::text,
            (
                SELECT ce.address::text
                FROM identity.contact_emails ce
                WHERE ce.contact_id = c.id
                ORDER BY ce.id
                LIMIT 1
            ) AS email,
            COALESCE(
                ARRAY_AGG(oc.organization_id) FILTER (WHERE oc.organization_id IS NOT NULL),
                '{}'
            ) AS org_ids
        FROM identity.contacts c
        LEFT JOIN identity.organization_contacts oc ON oc.contact_id = c.id
        GROUP BY c.id, c.name, c.title
        ORDER BY c.name
    """
    rows = await db.fetch_all(sql)
    result = []
    for r in rows:
        d = dict(r)
        # org_ids comes back as a PostgreSQL array — ensure it's a plain list
        d["org_ids"] = list(d["org_ids"]) if d["org_ids"] else []
        result.append(d)
    return result


async def _fetch_contact_for_display(db: AsyncDBConnection, contact_id: int) -> dict:
    """Fetch a contact via api.get_contact_detail() for the detail panel.

    Returns dict with id, name, title, notes keys — matches the old
    direct query's shape exactly, since identity.v_contact_detail has no
    extra joined columns to lose — or None if not found.
    """
    return await _fetch_json_scalar(
        db, "SELECT api.get_contact_detail(%s)", (contact_id,)
    )


# -- Single contact fetch (for detail panel) -----------------------------------

@router.get("/crew/contacts/{contact_id}")
async def get_contact(
    contact_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Fetch a single contact as JSON for the detail panel."""
    return await get_detail_or_404(
        db, _fetch_contact_for_display, contact_id, "Contact not found"
    )


# -- Contact save routes --------------------------------------------------------
# /crew/contacts/save must be declared before /crew/contacts/{contact_id}/save
# to prevent "save" matching as a contact_id integer.

@router.post("/crew/contacts/save")
async def save_new_contact(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new contact via api.save_contact().

    Accepts JSON body: {name, title, notes}
    Returns the new contact record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    title = body.get("title") or None
    notes = body.get("notes") or None  # pylint: disable=duplicate-code
    # Matches organizations.py's save routes: both entities have a
    # "notes" field and call require_name/get_user_id in the same
    # order. Coincidental overlap between unrelated field sets — not a
    # shared concept worth extracting into a helper.

    rejection = require_name(name)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {"name": name, "title": title, "notes": notes}

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_contact(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_contact_for_display,
        None,
        "Insert succeeded but fetch failed",
    )


@router.post("/crew/contacts/{contact_id}/save")
async def save_contact(
    contact_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing contact via api.save_contact().

    Accepts JSON body: {name, title, notes}
    Returns the updated contact record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} (200) on
    failure — e.g. missing name, contact not found.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    title = body.get("title") or None
    notes = body.get("notes") or None

    rejection = require_name(name)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {"id": contact_id, "name": name, "title": title, "notes": notes}

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_contact(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_contact_for_display,
        contact_id,
        "Save succeeded but fetch failed",
    )


@router.delete("/crew/contacts/{contact_id}")
async def delete_contact(
    contact_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Delete a contact by id via api.delete_contact().

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. not found, or blocked by dependent records (foreign key violation).
    """
    user_id = get_user_id(request)
    return await delete_via_proc(
        db, "SELECT api.delete_contact(%s, %s)", (contact_id, user_id)
    )
