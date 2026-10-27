# Changedoc: crew.py — forward proc's `data` field on save failure

**File:** `src/curator/web/routes/crew.py`
**Date:** 2026-06-29
**Source verified:** Viewed directly from Carolyn's upload immediately
before writing this changedoc — full file, not reconstructed from memory.

## Purpose

Companion change to the `api.save_project` update (see
`CHANGEDOC_SAVE_PROJECT_CONFLICT_ID.md`) that adds `conflicting_id` to the
proc's `data` field on a duplicate-name rejection. Right now `crew.py`
discards `data` entirely on failure and only ever sends `message` to the
browser. This change forwards `data` through unchanged, so when the proc
starts populating it, the frontend will have access to it.

Two functions change: `save_new_project` and `save_project`. Each is
provided here as a complete function — find the function by its `async def`
line, select from `@router.post(...)` through the final `return
JSONResponse(dict(record))`, and replace the whole block. No need to locate
or match individual lines inside it.

`delete_project` is unaffected — see the proc changedoc for why.

---

## Function 1 — `save_new_project`

### BEFORE (complete function, as it exists in your uploaded file, lines 361–409)

```python
@router.post("/crew/projects/save")
async def save_new_project(
    request: Request,
    role: str = Query("captain"),
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new project via api.save_project().

    Accepts JSON body: {name, type_id, status_id, description}
    Returns the new project record as JSON on success (200).
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. missing name, duplicate name. The message is proc-supplied and
    safe to display directly in the UI.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None
    description = body.get("description") or None

    if not name:
        return JSONResponse({"success": False, "message": "Name is required."})

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {
        "name": name,
        "description": description,
        "type": type_name,
        "status": status_name,
    }

    envelope = await _call_proc(
        db,
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    new_id = envelope["data"]["id"]
    record = await _fetch_project_for_display(db, new_id)
    if not record:
        raise HTTPException(status_code=500, detail="Insert succeeded but fetch failed")

    return JSONResponse(dict(record))
```

### AFTER (complete function — replace the whole thing with this)

```python
@router.post("/crew/projects/save")
async def save_new_project(
    request: Request,
    role: str = Query("captain"),
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new project via api.save_project().

    Accepts JSON body: {name, type_id, status_id, description}
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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {
        "name": name,
        "description": description,
        "type": type_name,
        "status": status_name,
    }

    envelope = await _call_proc(
        db,
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({
            "success": False,
            "message": envelope.get("message"),
            "data": envelope.get("data"),
        })

    new_id = envelope["data"]["id"]
    record = await _fetch_project_for_display(db, new_id)
    if not record:
        raise HTTPException(status_code=500, detail="Insert succeeded but fetch failed")

    return JSONResponse(dict(record))
```

### What changed, specifically

- The `if not name:` early-return now includes `"data": None` explicitly,
  for response-shape consistency with the proc-failure branch below it
  (both failure paths now always include all three keys).
- The proc-failure branch now includes `"data": envelope.get("data")`
  alongside `success` and `message`.
- Docstring updated to mention `data`.
- Nothing else changed — same imports, same signature, same success path.

---

## Function 2 — `save_project`

### BEFORE (complete function, as it exists in your uploaded file, lines 412–459)

```python
@router.post("/crew/projects/{project_id}/save")
async def save_project(
    project_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing project via api.save_project().

    Accepts JSON body: {name, type_id, status_id, description}
    Returns the updated project record as JSON on success (200).
    Returns {"success": false, "message": "..."} (200) on failure —
    e.g. missing name, duplicate name, project not found.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None
    description = body.get("description") or None

    if not name:
        return JSONResponse({"success": False, "message": "Name is required."})

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {
        "id": project_id,
        "name": name,
        "description": description,
        "type": type_name,
        "status": status_name,
    }

    envelope = await _call_proc(
        db,
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    record = await _fetch_project_for_display(db, project_id)
    if not record:
        raise HTTPException(status_code=500, detail="Save succeeded but fetch failed")

    return JSONResponse(dict(record))
```

### AFTER (complete function — replace the whole thing with this)

```python
@router.post("/crew/projects/{project_id}/save")
async def save_project(
    project_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing project via api.save_project().

    Accepts JSON body: {name, type_id, status_id, description}
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

    if not name:
        return JSONResponse({"success": False, "message": "Name is required.", "data": None})

    type_name, status_name = await _resolve_type_status_names(db, type_id, status_id)

    user_id = request.state.user["user_id"] if request.state.user else None

    payload = {
        "id": project_id,
        "name": name,
        "description": description,
        "type": type_name,
        "status": status_name,
    }

    envelope = await _call_proc(
        db,
        "SELECT api.save_project(%s, %s)",
        (json.dumps(payload), user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({
            "success": False,
            "message": envelope.get("message"),
            "data": envelope.get("data"),
        })

    record = await _fetch_project_for_display(db, project_id)
    if not record:
        raise HTTPException(status_code=500, detail="Save succeeded but fetch failed")

    return JSONResponse(dict(record))
```

### What changed, specifically

Same pattern as Function 1: `"data": None` added to the early-return,
`"data": envelope.get("data")` added to the proc-failure branch, docstring
updated. Nothing else in the function changed.

---

## What this does NOT include

- No changes to `delete_project` (not applicable — see proc changedoc).
- No frontend changes — `saveForm()` in `detail-panel.js` still only reads
  `body.message` for the alert. It will silently ignore the new `data` key
  until the future "open existing / rename" dialog is built to use it.
- No changes to any other function in this file.

## Verification steps

1. Replace both functions in `crew.py` as shown above.
2. Apply the `api.save_project` proc change from
   `CHANGEDOC_SAVE_PROJECT_CONFLICT_ID.md` first (or this has nothing new
   to forward).
3. Reload the app, try creating a duplicate-named project.
4. In DevTools Network tab, inspect the response body for
   `POST /crew/projects/save` — confirm `"data": {"conflicting_id": N}` is
   now present alongside `"success": false` and the message.
5. Confirm normal create/update/delete still work exactly as before — this
   change only affects the shape of failure responses, nothing else.
