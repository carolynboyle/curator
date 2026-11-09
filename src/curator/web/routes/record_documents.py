"""Record document routes — the parts of a seanchaí ledger record.

A record (a deed, a will...) can span many pages. Each part has up to two
links: the original image (source_url, e.g. FamilySearch) and a markdown
transcription kept in the seanchai repo (md_path, repo-relative). Parts
live in seanchai.record_documents (steward 10k_seanchai_record_documents.sql).

GET    /seanchai/records/{record_id}/documents → JSON list, in reading order
POST   /seanchai/record_documents/save         → add a part to a record
POST   /seanchai/record_documents/{doc_id}/save → edit a part
DELETE /seanchai/record_documents/{doc_id}     → remove a part

{record_id} here is the record's internal id (the same id the detail panel
uses), not the visible PR-033 style ledger ID.

Reads and writes go through api.* functions only (web_app_user has no
table grants). The save procs return the saved part in their envelope, so
unlike the entity routes there is no separate re-fetch step.

Route-ordering note: /save is declared before /{doc_id}/save so FastAPI
matches the literal first.
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from dbkit.connection import AsyncDBConnection
from curator.web.deps import (
    _fetch_json_scalar,
    call_proc,
    delete_via_proc,
    get_db,
    get_user_id,
)

router = APIRouter()

# Payload keys forwarded to api.save_record_document. record_id is only
# meaningful on insert; seq is deliberately absent — the proc assigns it.
_PART_FIELDS = ("label", "source_url", "md_path", "status")


def _require_target(body: dict):
    """Return a rejection response if the part has neither link, else None.

    A part needs a source URL or a transcription path (the table has the
    same CHECK). Early exit saves a round trip; the proc stays the real
    authority for path and status validation.
    """
    if not (body.get("source_url") or "").strip() and not (body.get("md_path") or "").strip():
        return JSONResponse({
            "success": False,
            "message": "Enter a source URL, a transcription path, or both.",
            "data": None,
        })
    return None


def _payload_from(body: dict) -> dict:
    """Build the proc payload from a request body.

    Every part field present in the body is forwarded, blank strings
    included — api.save_record_document treats a blank on update as
    "clear this field".
    """
    return {key: body[key] for key in _PART_FIELDS if key in body}


async def _save(db: AsyncDBConnection, request: Request, payload: dict) -> JSONResponse:
    """Call api.save_record_document and return the part, or the rejection."""
    envelope = await call_proc(
        db,
        "SELECT api.save_record_document(%s::jsonb, %s)",
        (json.dumps(payload), get_user_id(request)),
    )
    if not envelope.get("success"):
        return JSONResponse({
            "success": False,
            "message": envelope.get("message"),
            "data": envelope.get("data"),
        })
    return JSONResponse(dict(envelope["data"]))


@router.get("/seanchai/records/{record_id}/documents")
async def list_documents(
    record_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Return a record's parts as a JSON list, in reading order."""
    documents = await _fetch_json_scalar(
        db, "SELECT api.list_record_documents(%s)", (record_id,)
    )
    return JSONResponse(documents or [])


@router.post("/seanchai/record_documents/save")
async def save_new_document(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Add a part to a record.

    Accepts JSON body: {record_id, label, source_url, md_path, status}.
    seq is assigned by the proc (the record's highest + 1).

    Returns the new part as JSON on success (200), or
    {"success": false, "message": "...", "data": ...} on failure.
    """
    body = await request.json()

    rejection = _require_target(body)
    if rejection:
        return rejection

    payload = _payload_from(body)
    payload["record_id"] = body.get("record_id")
    return await _save(db, request, payload)


@router.post("/seanchai/record_documents/{doc_id}/save")
async def save_document(
    doc_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Edit a part. Accepts the same body as the insert, minus record_id.

    Returns the updated part as JSON on success (200), or
    {"success": false, "message": "...", "data": ...} on failure.
    """
    body = await request.json()

    rejection = _require_target(body)
    if rejection:
        return rejection

    payload = _payload_from(body)
    payload["id"] = doc_id
    return await _save(db, request, payload)


@router.delete("/seanchai/record_documents/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Remove one part of a record (the audit log keeps a copy).

    Returns 204 No Content on success, or
    {"success": false, "message": "..."} on failure.
    """
    return await delete_via_proc(
        db, "SELECT api.delete_record_document(%s)", (doc_id,)
    )
