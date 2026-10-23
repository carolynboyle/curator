"""Seanchaí research ledger routes.

GET  /seanchai/                         → redirect to /crew?role=seanchai
GET  /seanchai/records                  → JSON list (Tabulator ajax source)
GET  /seanchai/searches                 → JSON list (Tabulator ajax source)

GET  /seanchai/records/{record_id}      → record detail JSON (for detail panel)
POST /seanchai/records/save             → insert new record
POST /seanchai/records/{record_id}/save → update record
DELETE /seanchai/records/{record_id}    → soft-delete (sets status=excluded)

GET  /seanchai/searches/{search_id}      → search detail JSON (for detail panel)
POST /seanchai/searches/save             → insert new search
POST /seanchai/searches/{search_id}/save → update search
DELETE /seanchai/searches/{search_id}    → hard-delete

Route-ordering note: /save and /records (literal) are declared before
/{record_id} and /{search_id} (parameterized) so FastAPI matches the
literals first and doesn't attempt to parse "save" as an integer.
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from dbkit.connection import AsyncDBConnection
from curator.web.deps import (
    _fetch_json_scalar,
    call_proc_and_refetch,
    delete_via_proc,
    get_db,
    get_detail_or_404,
    get_user_id,
)

router = APIRouter()


# =============================================================================
# Fetch helpers — export these so panel.py can import them into _FETCH_FUNCTIONS
# =============================================================================

async def _fetch_record_for_display(db: AsyncDBConnection, record_id: int) -> dict:
    """Fetch a seanchaí record via api.get_record_detail() for the detail panel.

    Returns a dict with the v_record_detail whitelist columns:
    record_id, record_type_id, type_code, record_type, record_status_id,
    status, display_order, year, subject, county, state, source_citation,
    source_url, notes — or None if not found.
    """
    return await _fetch_json_scalar(
        db, "SELECT api.get_record_detail(%s)", (record_id,)
    )


async def _fetch_search_for_display(db: AsyncDBConnection, search_id: int) -> dict:
    """Fetch a seanchaí search via api.get_search_detail() for the detail panel.

    Returns a dict with the v_search_detail whitelist columns:
    search_id, search_terms, county_scope, year_filter, result_count,
    status, notes, searched_at — or None if not found.
    """
    return await _fetch_json_scalar(
        db, "SELECT api.get_search_detail(%s)", (search_id,)
    )


# =============================================================================
# Local guards
# =============================================================================

def _require_subject(subject: str):
    """Return a rejection response if subject is blank, else None.

    Records don't have a "name" field — deps.py's require_name() is
    name-specific, so this is the seanchaí equivalent. Same reasoning
    as tasks.py's _require_description: cheap early-exit for the most
    common blank submission; the proc remains the real validation authority
    for required FKs (record_type_id, record_status_id).
    """
    if not subject:
        return JSONResponse({
            "success": False,
            "message": "Subject is required.",
            "data": None,
        })
    return None


def _require_search_terms(search_terms: str):
    """Return a rejection response if search_terms is blank, else None."""
    if not search_terms:
        return JSONResponse({
            "success": False,
            "message": "Search terms are required.",
            "data": None,
        })
    return None


# =============================================================================
# Page route — HTML
# =============================================================================

@router.get("/seanchai/")
async def seanchai_page():
    """The research ledger now lives on the Seanchaí's crew dashboard
    (Records and Searches tabs). Redirect so existing bookmarks work."""
    return RedirectResponse("/crew?role=seanchai", status_code=307)


# =============================================================================
# List routes — JSON for Tabulator ajax
# =============================================================================

@router.get("/seanchai/records")
async def list_records(
    db: AsyncDBConnection = Depends(get_db),
):
    """Return all seanchaí records as JSON for the Tabulator grid.

    Tabulator hits this with Accept: application/json. api.list_records()
    is a SECURITY DEFINER function — see 07c_seanchai_list_api.sql.
    Includes record_type_id and record_status_id FK integers alongside the
    resolved type/status names so Tabulator's inline list editors work.
    """
    records = await _fetch_json_scalar(db, "SELECT api.list_records()", ())
    return JSONResponse({"records": records or []})


@router.get("/seanchai/searches")
async def list_searches(
    db: AsyncDBConnection = Depends(get_db),
):
    """Return all seanchaí searches as JSON for the Tabulator grid."""
    searches = await _fetch_json_scalar(db, "SELECT api.list_searches()", ())
    return JSONResponse({"records": searches or []})


# =============================================================================
# Records — detail, save, delete
# /seanchai/records/save must be declared before /seanchai/records/{record_id}
# and /seanchai/records/{record_id}/save.
# =============================================================================

@router.get("/seanchai/records/{record_id}")
async def get_record(
    record_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Fetch a single record as JSON for the detail panel."""
    return await get_detail_or_404(
        db, _fetch_record_for_display, record_id, "Record not found"
    )


@router.post("/seanchai/records/save")
async def save_new_record(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new seanchaí record via api.save_record().

    Accepts JSON body: {subject, record_type_id, record_status_id,
    display_order, year, county, state, source_citation, source_url, notes}.
    Any record_id in the body is ignored — the proc assigns it.

    Returns the new record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} on failure.
    api.save_record() assigns record_id and requires record_type_id.
    Only the subject check is duplicated here — the proc handles the rest.
    """
    body = await request.json()
    subject = (body.get("subject") or "").strip()

    rejection = _require_subject(subject)
    if rejection:
        return rejection

    user_id = get_user_id(request)
    # record_id is deliberately not forwarded: api.save_record assigns
    # <type code>-NNN on insert (steward 10f_seanchai_autonumber.sql).
    payload = {
        "subject":          subject,
        "record_type_id":   body.get("record_type_id") or None,
        "record_status_id": body.get("record_status_id") or None,
        "display_order":    body.get("display_order") or None,
        "year":             body.get("year") or None,
        "county":           body.get("county") or None,
        "state":            body.get("state") or None,
        "source_citation":  body.get("source_citation") or None,
        "source_url":       body.get("source_url") or None,
        "notes":            body.get("notes") or None,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_record(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_record_for_display,
        None,
        "Insert succeeded but fetch failed",
    )


@router.post("/seanchai/records/{record_id}/save")
async def save_record(
    record_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing seanchaí record via api.save_record().

    Returns the updated record as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} on failure.
    """
    body = await request.json()
    subject = (body.get("subject") or "").strip()

    rejection = _require_subject(subject)
    if rejection:
        return rejection

    user_id = get_user_id(request)
    payload = {
        "id":               record_id,
        "record_id":        body.get("record_id") or None,
        "subject":          subject,
        "record_type_id":   body.get("record_type_id") or None,
        "record_status_id": body.get("record_status_id") or None,
        "display_order":    body.get("display_order") or None,
        "year":             body.get("year") or None,
        "county":           body.get("county") or None,
        "state":            body.get("state") or None,
        "source_citation":  body.get("source_citation") or None,
        "source_url":       body.get("source_url") or None,
        "notes":            body.get("notes") or None,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_record(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_record_for_display,
        record_id,
        "Save succeeded but fetch failed",
    )


@router.delete("/seanchai/records/{record_id}")
async def delete_record(
    record_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Soft-delete a record via api.delete_record() (sets status=excluded).

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} on failure.
    The record remains in the database and visible in the grid with
    status='excluded' — soft-delete is intentional for the research ledger.
    """
    user_id = get_user_id(request)
    return await delete_via_proc(
        db, "SELECT api.delete_record(%s, %s)", (record_id, user_id)
    )


# =============================================================================
# Searches — detail, save, delete
# /seanchai/searches/save must be declared before /seanchai/searches/{search_id}
# and /seanchai/searches/{search_id}/save.
# =============================================================================

@router.get("/seanchai/searches/{search_id}")
async def get_search(
    search_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Fetch a single search as JSON for the detail panel."""
    return await get_detail_or_404(
        db, _fetch_search_for_display, search_id, "Search not found"
    )


@router.post("/seanchai/searches/save")
async def save_new_search(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new seanchaí search via api.save_search().

    Accepts JSON body: {search_terms, county_scope, year_filter,
    result_count, status, notes, searched_at}.
    Any search_id in the body is ignored — the proc assigns SRCH-NNN.

    Returns the new search as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} on failure.
    """
    body = await request.json()
    search_terms = (body.get("search_terms") or "").strip()

    rejection = _require_search_terms(search_terms)
    if rejection:
        return rejection

    user_id = get_user_id(request)
    # search_id is deliberately not forwarded: api.save_search assigns
    # SRCH-NNN on insert (steward 10f_seanchai_autonumber.sql).
    payload = {
        "search_terms": search_terms,
        "county_scope": body.get("county_scope") or None,
        "year_filter":  body.get("year_filter") or None,
        "result_count": body.get("result_count") or None,
        "status":       body.get("status") or None,
        "notes":        body.get("notes") or None,
        "searched_at":  body.get("searched_at") or None,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_search(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_search_for_display,
        None,
        "Insert succeeded but fetch failed",
    )


@router.post("/seanchai/searches/{search_id}/save")
async def save_search(
    search_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing seanchaí search via api.save_search().

    Returns the updated search as JSON on success (200).
    Returns {"success": false, "message": "...", "data": ...} on failure.
    """
    body = await request.json()
    search_terms = (body.get("search_terms") or "").strip()

    rejection = _require_search_terms(search_terms)
    if rejection:
        return rejection

    user_id = get_user_id(request)
    payload = {
        "id":           search_id,
        "search_id":    body.get("search_id") or None,
        "search_terms": search_terms,
        "county_scope": body.get("county_scope") or None,
        "year_filter":  body.get("year_filter") or None,
        "result_count": body.get("result_count") or None,
        "status":       body.get("status") or None,
        "notes":        body.get("notes") or None,
        "searched_at":  body.get("searched_at") or None,
    }

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_search(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_search_for_display,
        search_id,
        "Save succeeded but fetch failed",
    )


@router.delete("/seanchai/searches/{search_id}")
async def delete_search(
    search_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Hard-delete a search via api.delete_search().

    Returns 204 No Content on success.
    Returns {"success": false, "message": "..."} on failure.
    Searches are log entries with no historical value — hard delete is correct.
    """
    user_id = get_user_id(request)
    return await delete_via_proc(
        db, "SELECT api.delete_search(%s, %s)", (search_id, user_id)
    )
