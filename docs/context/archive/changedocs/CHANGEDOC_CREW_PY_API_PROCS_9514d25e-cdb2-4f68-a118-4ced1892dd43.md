# Changedoc: crew.py — Route project save/delete through api schema procs

**File:** `src/curator/web/routes/crew.py`
**Date:** 2026-06-29
**Source verified:** Pasted directly by Carolyn (not fetched from GitHub — branch/URL caching confusion earlier in session made fetched copies unreliable for this file).

## Summary

Three routes — `save_new_project`, `save_project`, `delete_project` — currently
build SQL directly in Python (slug generation, deduplication, status
defaulting, INSERT/UPDATE/DELETE). This changedoc replaces that logic with
calls to the `api.save_project()` and `api.delete_project()` stored
procedures, which already implement all of that logic on the PostgreSQL
side (see `06_api.sql`).

Python's job shrinks to: unwrap the JSON body, look up type/status **names**
from their **ids** (the procs take name strings, not ids — see "Payload
translation" below), call the proc, check `success`, and either return the
freshly-fetched display record (success) or a `{success, message}` envelope
the browser can show directly to the user (failure).

`_make_slug()` is removed — it has no remaining callers once both save
routes stop building INSERT/UPDATE statements themselves.

## Payload translation (id → name)

The browser sends `type_id` / `status_id` as integers (dropdowns are
populated with id/name pairs). `api.save_project()` expects `type` / `status`
as name strings, which it looks up internally. Per Carolyn's instruction to
expose the least data possible, the **lookup happens in Python**, not by
changing what the browser sends and not by changing the proc's accepted
payload shape. Two cheap `SELECT name FROM ... WHERE id = %s` calls per save,
done with the connection already open for the request.

## Error envelope (decided this session)

On proc failure (duplicate name, not found, etc.), the route returns
**HTTP 200** with body `{"success": false, "message": "<proc's message>"}`.
Rationale (Carolyn): Felipe will be using this app and should see a plain
description of what went wrong without anyone needing to check logs. The
proc already produces a human-readable `message` string — passing it straight
through is the simplest way to satisfy that without inventing new wording.

On success, the route returns the flat project record as JSON, same shape as
before this change — no envelope, no `success` key. This preserves the
current contract for any JS that reads the success path today; only the
failure path is new.

---

## Change 1 — Imports

### BEFORE

```python
"""Crew role dashboard routes."""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader

from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.formkit import FormActions
from curator.web.deps import get_config, get_db
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader
```

### AFTER

```python
"""Crew role dashboard routes."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader

from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager
from curator.formkit import FormActions
from curator.web.deps import get_config, get_db
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader
```

### Why

`re` was only used by `_make_slug()`, which is being removed — the proc
generates slugs now. `json` is added because proc results come back as a
JSONB column; depending on what `dbkit` hands back (str vs already-parsed
dict), the routes need to safely parse it. See the new `_call_proc` helper
below.

---

## Change 2 — Remove `_make_slug()`

### BEFORE

```python
def _make_slug(name: str) -> str:
    """Generate a URL-safe slug from a project name.

    Lowercases, replaces non-alphanumeric runs with hyphens,
    strips leading/trailing hyphens.

    Example: "WCYJ Store Website" -> "wcyj-store-website"
    """
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
```

### AFTER

*(removed entirely)*

### Why

Slug generation, including deduplication, now happens inside
`api.save_project()`. No remaining caller in this file once the two save
routes stop building INSERT/UPDATE statements themselves.

---

## Change 3 — New helper: call a proc and unwrap its JSONB envelope

### BEFORE

*(no equivalent helper exists)*

### AFTER

```python
async def _call_proc(db: AsyncDBConnection, sql: str, params: tuple) -> dict:
    """Call a stored proc that returns a single JSONB envelope and unwrap it.

    Every api.* proc returns {"success": bool, "data": ..., "message": str}.
    fetch_one() gives back a dict keyed by the proc's column name (e.g.
    {"save_project": {...}}); this pulls out that single value and parses
    it if dbkit returned it as a JSON string rather than an already-decoded
    dict (encoding-dependent — see dbkit client_encoding note in handoff).

    Returns the envelope dict: {"success": ..., "data": ..., "message": ...}
    """
    result = await db.fetch_one(sql, params)
    envelope = list(result.values())[0]
    if isinstance(envelope, str):
        envelope = json.loads(envelope)
    return envelope


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
```

### Why

Both save routes need the same two things: call a proc and safely unwrap
its JSONB result, and translate id → name for type/status. Pulling these
into helpers keeps the route bodies short and keeps the id→name lookup
logic in exactly one place, since contacts and tasks routes will need the
same `_call_proc` pattern soon.

---

## Change 4 — `save_new_project` (insert)

### BEFORE

```python
@router.post("/crew/projects/save")
async def save_new_project(
    request: Request,
    role: str = Query("captain"),
    db: AsyncDBConnection = Depends(get_db),
):
    """Insert a new project.

    Accepts JSON body: {name, type_id, status_id, description}
    Returns the new project record as JSON on success.
    Returns 409 text on duplicate name, 422 text on missing name.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None
    description = body.get("description") or None

    if not name:
        return JSONResponse({"detail": "Name is required"}, status_code=422)

    # Default to "active" status if none selected — status_id is NOT NULL
    if not status_id:
        active = await db.fetch_one(
            "SELECT id FROM projects.project_status WHERE name = 'active'"
        )
        if active:
            status_id = active["id"]
        else:
            return JSONResponse({"detail": "Status is required"}, status_code=422)

    # If slug already exists, append incrementing suffix until unique
    slug = _make_slug(name)
    base_slug = slug
    counter = 1
    while True:
        existing = await db.fetch_one(
            "SELECT id FROM projects.projects WHERE slug = %s",
            (slug,)
        )
        if not existing:
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    result = await db.fetch_one(
        """
        INSERT INTO projects.projects (name, slug, type_id, status_id, description)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (name, slug, type_id, status_id, description)
    )
    new_id = result["id"]

    record = await _fetch_project_for_display(db, new_id)
    if not record:
        raise HTTPException(status_code=500, detail="Insert succeeded but fetch failed")

    return JSONResponse(dict(record))
```

### AFTER

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

### Why

Slug generation, deduplication, and status defaulting all move into
`api.save_project()`. Python's only remaining logic is the id→name lookup
and the empty-name guard (kept here so the route doesn't make a wasted
round-trip to the proc for an obviously-empty form field). `user_id` is
read from `request.state.user`, set by `SessionMiddleware` on every
authenticated request; the `if request.state.user else None` guard exists
because `request.state.user` is `None` on public paths, even though `/crew`
itself is never a public path today — defensive, costs nothing.

---

## Change 5 — `save_project` (update)

### BEFORE

```python
@router.post("/crew/projects/{project_id}/save")
async def save_project(
    project_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save edits to an existing project.

    Accepts JSON body: {name, type_id, status_id, description}
    Returns the updated project record as JSON on success.
    Returns 422 text on missing name.
    """
    body = await request.json()
    name = (body.get("name") or "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None
    description = body.get("description") or None

    if not name:
        return JSONResponse({"detail": "Name is required"}, status_code=422)

    await db.execute(
        """
        UPDATE projects.projects
        SET name = %s, type_id = %s, status_id = %s, description = %s
        WHERE id = %s
        """,
        (name, type_id, status_id, description, project_id)
    )

    record = await _fetch_project_for_display(db, project_id)
    if not record:
        raise HTTPException(status_code=500, detail="Save succeeded but fetch failed")

    return JSONResponse(dict(record))
```

### AFTER

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

### Why

Same proc as insert — `api.save_project()` branches on whether `payload.id`
is present. Including `"id": project_id` in the payload is what selects the
UPDATE path inside the proc. The direct `UPDATE ... WHERE id = %s` is gone;
conflict detection (another project already using that name) is now handled
inside the proc instead of being silently allowed as it was before.

---

## Change 6 — `delete_project`

### BEFORE

```python
@router.delete("/crew/projects/{project_id}")
async def delete_project(
    project_id: int,
    db: AsyncDBConnection = Depends(get_db),
):
    """Delete a project by id.

    Returns 204 No Content on success.
    Returns 404 if project not found.
    """
    from fastapi.responses import Response

    existing = await db.fetch_one(
        "SELECT id FROM projects.projects WHERE id = %s",
        (project_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.execute(
        "DELETE FROM projects.projects WHERE id = %s",
        (project_id,)
    )
    return Response(status_code=204)
```

### AFTER

```python
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
    user_id = request.state.user["user_id"] if request.state.user else None

    envelope = await _call_proc(
        db,
        "SELECT api.delete_project(%s, %s)",
        (project_id, user_id),
    )

    if not envelope.get("success"):
        return JSONResponse({"success": False, "message": envelope.get("message")})

    return Response(status_code=204)
```

### Why

`request: Request` is added as a parameter — it wasn't needed before since
the route did its own existence check and raw DELETE. The local
`from fastapi.responses import Response` import is replaced with a
module-level one (see Change 7) since it's now used on both the success and
no-op-failure-but-204 path... actually only on the success path; failure
returns `JSONResponse`. The existence check that used to raise a 404 is now
handled by the proc itself (`"message": "Project not found."`), and the
foreign-key-violation case the proc already catches (project has dependent
records) is now surfaced with a real message instead of bubbling up as an
unhandled exception, which is strictly better than what existed before.

---

## Change 7 — Module-level `Response` import

### BEFORE

`Response` was imported locally inside `delete_project`:

```python
from fastapi.responses import Response
```

### AFTER

Move to the top-level import block (Change 1), alongside `HTMLResponse` and
`JSONResponse`:

```python
from fastapi.responses import HTMLResponse, JSONResponse, Response
```

### Why

No functional difference, just cleanup — there's no longer a reason for it
to be a function-local import once it's the only thing in that line.

---

## Net effect

- `_make_slug()` deleted.
- Two new small helpers (`_call_proc`, `_resolve_type_status_names`) shared
  by all three routes, and reusable as-is for the contacts and tasks routes
  coming next.
- All SQL-construction logic (slug, dedup, status default, INSERT/UPDATE/
  DELETE) moves to PostgreSQL inside `api.save_project()` /
  `api.delete_project()`.
- All three routes now thread `user_id` from `request.state.user` into the
  proc calls, satisfying the `created_by` / `updated_by` stamping the procs
  already support but that nothing was supplying before.
- Failure responses are uniformly `{"success": false, "message": "..."}` at
  HTTP 200, with the proc's own human-readable message — no log-diving
  required for Felipe to understand what went wrong.
- Success responses are unchanged in shape (flat record JSON) — no required
  changes to whatever JS currently reads the save response.

## Deferred — not part of this change

**Row-Level Security.** `crew.py` has no server-side check that the logged-in
user's `crew_role` matches the `role` query param they're requesting — the
landing page (`landing.py`) filters which role *cards* are shown, but
`/crew?role=captain` typed directly into the URL bar is not currently
blocked for a non-captain user. Carolyn has explicitly deprioritized this
until after Contacts and Tasks CRUD are wired (Felipe demo first), but it
must be addressed — via RLS policies keyed off
`current_setting('app.current_user_id')`, set with `SET LOCAL` per
transaction — before any non-trusted user has access. Tracked, not
forgotten.
