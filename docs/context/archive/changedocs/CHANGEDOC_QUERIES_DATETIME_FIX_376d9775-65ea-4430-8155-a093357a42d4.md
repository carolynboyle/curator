# Changedoc: Fix `datetime` not JSON serializable in `/api/query`

**Date:** 2026-07-04
**Reason:** `GET /api/query/tasks/for_project?params=1` 500s with
`TypeError: Object of type datetime is not JSON serializable`.
`queries.yaml`'s `tasks.for_project` query selects `t.created_at` with no
`::text` cast, unlike every other column in the same query
(`description::text`, `notes::text`, `status::text`, `priority::text` are
all cast). Postgres hands back a native `datetime` for an uncast
`timestamptz`, and Starlette's plain `json.dumps()` (used internally by
`JSONResponse`) has no default handling for it.

**Two fixes, both applied:**
1. **`queries.yaml`** — cast `created_at` to text in both `tasks.for_project`
   and `tasks.for_task`, matching the casting convention every other
   column in the file already follows. `tasks.for_task` has the identical
   uncast `created_at` and would crash the same way the moment a subtask
   fetch happens — nothing's called it yet, but it's the same bug waiting
   to fire.
2. **`crew.py`'s `run_query()`** — swap `JSONResponse({...})` for
   `JSONResponse(jsonable_encoder({...}))`. `run_query()` is a generic
   endpoint meant to serve *any* future entry added to `queries.yaml`, not
   just today's five — `jsonable_encoder()` handles `datetime`, `Decimal`,
   `UUID`, etc. automatically, so a future query that forgets the
   `::text` convention degrades gracefully instead of 500ing. This is
   belt-and-suspenders on top of fix 1, not a replacement for it —
   `queries.yaml` should still follow its own casting convention
   consistently; this just stops a single missed cast from taking down
   the whole generic endpoint.

---

## 1. `src/curator/data/queries.yaml`

### BEFORE (complete file)

```yaml
# queries.yaml
# QueryLoader query definitions for Curator
# Location: src/curator/data/queries.yaml
#
# Structure: entity → query_name → { type, sql }
# Used by: /api/query/{entity}/{query_name}?params=X
#
# Parameter binding uses %s placeholders (psycopg style).
# params are passed as comma-separated string in the query string.

# =============================================================================
# TASKS
# =============================================================================

tasks:
  # Fetch all tasks for a project (detail panel Tasks tab)
  for_project:
    type: select_all
    sql: >
      SELECT
          t.id,
          t.description::text,
          t.notes::text,
          t.status_id,
          ts.name::text AS status,
          t.priority_id,
          p.name::text  AS priority,
          t.sort_order,
          t.created_at
      FROM projects.tasks t
      LEFT JOIN projects.task_status ts ON ts.id = t.status_id
      LEFT JOIN projects.priority    p  ON p.id  = t.priority_id
      WHERE t.project_id = %s
        AND t.parent_id IS NULL
      ORDER BY t.sort_order, t.created_at

  # Fetch sub-tasks for a parent task
  for_task:
    type: select_all
    sql: >
      SELECT
          t.id,
          t.description::text,
          t.notes::text,
          t.status_id,
          ts.name::text AS status,
          t.priority_id,
          p.name::text  AS priority,
          t.sort_order,
          t.created_at
      FROM projects.tasks t
      LEFT JOIN projects.task_status ts ON ts.id = t.status_id
      LEFT JOIN projects.priority    p  ON p.id  = t.priority_id
      WHERE t.parent_id = %s
      ORDER BY t.sort_order, t.created_at

# =============================================================================
# CONTACT EMAILS
# =============================================================================

contact_emails:
  # Fetch all emails for a contact (detail panel Emails tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          address::text,
          label::text
      FROM identity.contact_emails
      WHERE contact_id = %s
      ORDER BY id

# =============================================================================
# CONTACT PHONES
# =============================================================================

contact_phones:
  # Fetch all phones for a contact (detail panel Phones tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          number::text,
          label::text
      FROM identity.contact_phones
      WHERE contact_id = %s
      ORDER BY id
      
# =============================================================================
# CONTACT URLS
# =============================================================================

contact_urls:
  # Fetch all URLs for a contact (detail panel URLs tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          cu.id,
          ut.name::text AS url_type,
          cu.value::text
      FROM identity.contact_urls cu
      JOIN identity.url_type ut ON ut.id = cu.url_type_id
      WHERE cu.contact_id = %s
      ORDER BY cu.id

# =============================================================================
# ORGANIZATION CONTACTS
# =============================================================================

organization_contacts:
  # Fetch all contacts in an organization (detail panel Contacts tab on org)
  for_organization:
    type: select_all
    sql: >
      SELECT
          c.id,
          c.name::text,
          c.title::text,
          ocr.name::text AS role
      FROM identity.contacts c
      JOIN identity.organization_contacts oc
          ON oc.contact_id = c.id
      LEFT JOIN identity.organization_contact_role ocr
          ON ocr.id = oc.role_id
      WHERE oc.organization_id = %s
      ORDER BY c.name

  # Fetch all organizations for a contact (detail panel Organizations tab on contact)
  for_contact:
    type: select_all
    sql: >
      SELECT
          o.id,
          o.name::text,
          ocr.name::text AS role
      FROM identity.organizations o
      JOIN identity.organization_contacts oc
          ON oc.organization_id = o.id
      LEFT JOIN identity.organization_contact_role ocr
          ON ocr.id = oc.role_id
      WHERE oc.contact_id = %s
      ORDER BY o.name
```

### AFTER (complete file)

```yaml
# queries.yaml
# QueryLoader query definitions for Curator
# Location: src/curator/data/queries.yaml
#
# Structure: entity → query_name → { type, sql }
# Used by: /api/query/{entity}/{query_name}?params=X
#
# Parameter binding uses %s placeholders (psycopg style).
# params are passed as comma-separated string in the query string.

# =============================================================================
# TASKS
# =============================================================================

tasks:
  # Fetch all tasks for a project (detail panel Tasks tab)
  for_project:
    type: select_all
    sql: >
      SELECT
          t.id,
          t.description::text,
          t.notes::text,
          t.status_id,
          ts.name::text AS status,
          t.priority_id,
          p.name::text  AS priority,
          t.sort_order,
          t.created_at::text
      FROM projects.tasks t
      LEFT JOIN projects.task_status ts ON ts.id = t.status_id
      LEFT JOIN projects.priority    p  ON p.id  = t.priority_id
      WHERE t.project_id = %s
        AND t.parent_id IS NULL
      ORDER BY t.sort_order, t.created_at

  # Fetch sub-tasks for a parent task
  for_task:
    type: select_all
    sql: >
      SELECT
          t.id,
          t.description::text,
          t.notes::text,
          t.status_id,
          ts.name::text AS status,
          t.priority_id,
          p.name::text  AS priority,
          t.sort_order,
          t.created_at::text
      FROM projects.tasks t
      LEFT JOIN projects.task_status ts ON ts.id = t.status_id
      LEFT JOIN projects.priority    p  ON p.id  = t.priority_id
      WHERE t.parent_id = %s
      ORDER BY t.sort_order, t.created_at

# =============================================================================
# CONTACT EMAILS
# =============================================================================

contact_emails:
  # Fetch all emails for a contact (detail panel Emails tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          address::text,
          label::text
      FROM identity.contact_emails
      WHERE contact_id = %s
      ORDER BY id

# =============================================================================
# CONTACT PHONES
# =============================================================================

contact_phones:
  # Fetch all phones for a contact (detail panel Phones tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          id,
          number::text,
          label::text
      FROM identity.contact_phones
      WHERE contact_id = %s
      ORDER BY id
      
# =============================================================================
# CONTACT URLS
# =============================================================================

contact_urls:
  # Fetch all URLs for a contact (detail panel URLs tab)
  for_contact:
    type: select_all
    sql: >
      SELECT
          cu.id,
          ut.name::text AS url_type,
          cu.value::text
      FROM identity.contact_urls cu
      JOIN identity.url_type ut ON ut.id = cu.url_type_id
      WHERE cu.contact_id = %s
      ORDER BY cu.id

# =============================================================================
# ORGANIZATION CONTACTS
# =============================================================================

organization_contacts:
  # Fetch all contacts in an organization (detail panel Contacts tab on org)
  for_organization:
    type: select_all
    sql: >
      SELECT
          c.id,
          c.name::text,
          c.title::text,
          ocr.name::text AS role
      FROM identity.contacts c
      JOIN identity.organization_contacts oc
          ON oc.contact_id = c.id
      LEFT JOIN identity.organization_contact_role ocr
          ON ocr.id = oc.role_id
      WHERE oc.organization_id = %s
      ORDER BY c.name

  # Fetch all organizations for a contact (detail panel Organizations tab on contact)
  for_contact:
    type: select_all
    sql: >
      SELECT
          o.id,
          o.name::text,
          ocr.name::text AS role
      FROM identity.organizations o
      JOIN identity.organization_contacts oc
          ON oc.organization_id = o.id
      LEFT JOIN identity.organization_contact_role ocr
          ON ocr.id = oc.role_id
      WHERE oc.contact_id = %s
      ORDER BY o.name
```

Note: `ORDER BY t.sort_order, t.created_at` in both queries is left
**uncast** — sorting works fine against the native `timestamptz` type,
and it's never included in the returned columns, only used to order rows
that were already selected in the `SELECT` list above it. Only the
`SELECT`-list `created_at` needed the cast.

---

## 2. `src/curator/web/routes/crew.py`

**Why:** Belt-and-suspenders per the reasoning above — `run_query()`
serves any current or future `queries.yaml` entry, so it shouldn't be one
missed `::text` cast away from a 500.

### BEFORE (just the changed function and its import — see the
`CHANGEDOC_QUERY_LOADER_BUILD_FIX.md` you already applied for the
complete current file; only `run_query()` and the import block change
here)

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader
```

```python
@router.get("/api/query/{entity}/{query_name}")
async def run_query(
    entity: str,
    query_name: str,
    params: str = Query(""),
    db: AsyncDBConnection = Depends(get_db),
):
    """Generic query endpoint driven by queries.yaml.

    Used by _datasheet_with_header.html's Tabulator instances for child
    datasheets (Tasks, Emails, Phones, URLs, Organizations tabs).

    Query parameters:
        params: comma-separated string of positional SQL params
    """
    params_list = params.split(",") if params else []
    try:
        sql = _query_loader.sql(entity, query_name)
        rows = await db.fetch_all(sql, params_list)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse({"records": [dict(r) for r in rows]})
```

### AFTER

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader
```

```python
@router.get("/api/query/{entity}/{query_name}")
async def run_query(
    entity: str,
    query_name: str,
    params: str = Query(""),
    db: AsyncDBConnection = Depends(get_db),
):
    """Generic query endpoint driven by queries.yaml.

    Used by _datasheet_with_header.html's Tabulator instances for child
    datasheets (Tasks, Emails, Phones, URLs, Organizations tabs).

    Query parameters:
        params: comma-separated string of positional SQL params

    Response is passed through jsonable_encoder() rather than returned
    as a plain dict — this endpoint serves whatever queries.yaml defines,
    present and future, and jsonable_encoder() handles types plain
    json.dumps() can't (datetime, Decimal, UUID) without every query
    author needing to remember an explicit ::text cast. queries.yaml
    should still cast consistently (see its own convention) — this is a
    backstop, not a replacement for that.
    """
    params_list = params.split(",") if params else []
    try:
        sql = _query_loader.sql(entity, query_name)
        rows = await db.fetch_all(sql, params_list)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(jsonable_encoder({"records": [dict(r) for r in rows]}))
```

---

## Apply and verify

1. `queries.yaml` — add `::text` to both `t.created_at` occurrences in
   the `SELECT` lists (not the `ORDER BY` clauses).
2. `crew.py` — add the `jsonable_encoder` import, wrap `run_query()`'s
   return in it.
3. Restart uvicorn.
4. Re-test `http://localhost:8080/api/query/tasks/for_project?params=1`
   — should now return `{"records": [...]}` cleanly.
5. If that project has no tasks yet, this is a good moment to add one via
   pgAdmin directly (`INSERT INTO projects.tasks (project_id, description,
   status_id) VALUES (1, 'test task', <a real task_status id>)`) to
   confirm a non-empty result serializes correctly too, `created_at`
   included.
