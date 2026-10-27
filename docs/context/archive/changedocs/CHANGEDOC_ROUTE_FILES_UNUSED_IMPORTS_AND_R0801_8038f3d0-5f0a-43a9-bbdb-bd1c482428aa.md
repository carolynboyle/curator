# Changedoc: fix unused imports, address remaining R0801 in route files

**Date:** 2026-07-04
**Reason:** Two issues from the last `pylint` run, both caused by the
route-helpers extraction:

1. **Real bug — unused imports.** `JSONResponse`/`Response` are now only
   constructed inside `deps.py`'s `get_detail_or_404`/`delete_via_proc`;
   the route files just call those helpers and return what comes back,
   so they never need `JSONResponse`/`Response` directly anymore. Left
   over from copying the old files' import lists without re-checking
   them — my mistake in the previous changedoc, not something to keep.
2. **Not a real bug — residual `R0801`.** `contacts.py`/`organizations.py`
   both have an identical 5-line stretch in their save routes:
   `notes = body.get("notes") or None` / `require_name` guard /
   `get_user_id`. This is three unrelated things landing next to each
   other by coincidence — both entities happen to have a `notes` field,
   both call the two helpers in the same order — not a shared concept
   worth its own extraction. Projects has no `notes` field at all and
   contacts additionally has `title`, so forcing this into a combined
   helper would couple unrelated field sets together for a
   five-line match. Documented `pylint` disable instead, same precedent
   as the existing `too-few-public-methods` disable on `formkit.py`'s
   `FormAction`/`FormActions` and `fieldkit.py`'s `FieldKit`.

---

## 1. `src/curator/web/routes/contacts.py`

### BEFORE

```python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

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
```

### AFTER

```python
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
```

### BEFORE

```python
    body = await request.json()
    name = (body.get("name") or "").strip()
    title = body.get("title") or None
    notes = body.get("notes") or None

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
```

### AFTER

```python
    body = await request.json()
    name = (body.get("name") or "").strip()
    title = body.get("title") or None
    notes = body.get("notes") or None  # pylint: disable=duplicate-code
    # Matches organizations.py's save routes: both entities have a
    # "notes" field and call require_name/get_user_id in the same
    # order. Coincidental overlap between unrelated field sets
    # (contacts also has title; projects has none of these three at
    # all) — not a shared concept worth extracting into a helper.

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
```

**Same pattern in `save_contact` (the edit route)** — add the identical
`# pylint: disable=duplicate-code` comment and note to its
`notes = body.get("notes") or None` line as well; the flagged block
covers both the new and edit routes.

---

## 2. `src/curator/web/routes/organizations.py`

### BEFORE

```python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

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
```

### AFTER

```python
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
```

### BEFORE

```python
    body = await request.json()
    name = (body.get("name") or "").strip()
    notes = body.get("notes") or None

    rejection = require_name(name)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {"name": name, "notes": notes}

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_organization(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_organization_for_display,
        None,
        "Insert succeeded but fetch failed",
    )
```

### AFTER

```python
    body = await request.json()
    name = (body.get("name") or "").strip()
    notes = body.get("notes") or None  # pylint: disable=duplicate-code
    # Matches contacts.py's save routes: both entities have a "notes"
    # field and call require_name/get_user_id in the same order.
    # Coincidental overlap between unrelated field sets — not a shared
    # concept worth extracting into a helper.

    rejection = require_name(name)
    if rejection:
        return rejection

    user_id = get_user_id(request)

    payload = {"name": name, "notes": notes}

    return await call_proc_and_refetch(
        db,
        "SELECT api.save_organization(%s, %s)",
        (json.dumps(payload), user_id),
        _fetch_organization_for_display,
        None,
        "Insert succeeded but fetch failed",
    )
```

**Same pattern in `save_organization` (the edit route)** — same disable
comment and note on its `notes = body.get("notes") or None` line.

---

## 3. `src/curator/web/routes/projects.py`

### BEFORE

```python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

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
```

### AFTER

```python
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
```

*(No `R0801` finding was reported against `projects.py` itself — it
doesn't share the "notes" field, so it isn't part of that duplicate
block. Only the unused-import fix applies here.)*

---

## Apply and verify

1. Remove the `from fastapi.responses import JSONResponse, Response`
   line from all three files (the `fastapi` import line itself, for
   `APIRouter`/`Depends`/`Request`, stays).
2. Add the `# pylint: disable=duplicate-code` comment + explanatory note
   to the `notes = body.get("notes") or None` line in all four affected
   routes (`save_new_contact`, `save_contact`, `save_new_organization`,
   `save_organization`).
3. `pylint src/` — should return to 10.00/10.
4. `pytest` — no behavior changed, should be unaffected by either fix.
