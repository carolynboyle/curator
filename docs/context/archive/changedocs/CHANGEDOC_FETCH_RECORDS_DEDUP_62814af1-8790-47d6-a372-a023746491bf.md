# Changedoc: `projects.py` — collapse `_fetch_records`'s search/no-search duplication

**Date:** 2026-07-04
**Reason:** `_fetch_records` currently branches into two nearly-identical
SQL blocks — one with a `WHERE p.name ILIKE %s` clause, one without —
that differ only in that one line. A single query with a conditional
`WHERE` clause covers both cases without duplicating the `SELECT`/`JOIN`
body.

**Applies on top of** the `CHANGEDOC_ROUTE_HELPERS_DEDUP.md` changes —
the BEFORE block below is `_fetch_records` as it exists in that
changedoc's AFTER version of `projects.py` (unchanged by that pass,
since it was explicitly flagged as out of scope there). If you haven't
applied that changedoc yet, apply it first; this one assumes it's
already in place.

**Scope check against `project_rules.md`:** DRY — same reasoning as the
cross-file extraction, applied within a single function this time.

---

## `src/curator/web/routes/projects.py`

### BEFORE

```python
async def _fetch_records(db: AsyncDBConnection, role: str, search: str) -> list:
    """Fetch role-filtered projects, optionally filtered by search term.

    Returns list of dicts with id, name, type, type_id, status, status_id.
    """
    view_name = f"projects.{role}_view"

    if search:
        sql = f"""
            SELECT
                p.id,
                p.name::text,
                p.slug::text,
                p.description::text,
                ps.name::text  AS status,
                pt.name::text  AS type,
                p.type_id,
                p.status_id
            FROM {view_name} p
            LEFT JOIN projects.project_status ps ON ps.id = p.status_id
            LEFT JOIN projects.project_type   pt ON pt.id = p.type_id
            WHERE p.name ILIKE %s
            ORDER BY p.name
        """
        rows = await db.fetch_all(sql, (f"%{search}%",))
    else:
        sql = f"""
            SELECT
                p.id,
                p.name::text,
                p.slug::text,
                p.description::text,
                ps.name::text  AS status,
                pt.name::text  AS type,
                p.type_id,
                p.status_id
            FROM {view_name} p
            LEFT JOIN projects.project_status ps ON ps.id = p.status_id
            LEFT JOIN projects.project_type   pt ON pt.id = p.type_id
            ORDER BY p.name
        """
        rows = await db.fetch_all(sql)

    return [dict(r) for r in rows]
```

### AFTER

```python
async def _fetch_records(db: AsyncDBConnection, role: str, search: str) -> list:
    """Fetch role-filtered projects, optionally filtered by search term.

    Returns list of dicts with id, name, type, type_id, status, status_id.

    One query handles both the filtered and unfiltered case: when search
    is empty, "%s = ''" is true and every row matches regardless of the
    ILIKE clause; when search is non-empty, that first comparison is
    false and the ILIKE clause does the actual filtering. Avoids
    duplicating the SELECT/JOIN body for a difference that's really just
    one WHERE condition.
    """
    view_name = f"projects.{role}_view"

    sql = f"""
        SELECT
            p.id,
            p.name::text,
            p.slug::text,
            p.description::text,
            ps.name::text  AS status,
            pt.name::text  AS type,
            p.type_id,
            p.status_id
        FROM {view_name} p
        LEFT JOIN projects.project_status ps ON ps.id = p.status_id
        LEFT JOIN projects.project_type   pt ON pt.id = p.type_id
        WHERE %s = '' OR p.name ILIKE %s
        ORDER BY p.name
    """
    rows = await db.fetch_all(sql, (search, f"%{search}%"))

    return [dict(r) for r in rows]
```

**Why the parameter order is `(search, f"%{search}%")`, not
`(search, search)`:** the first `%s` is compared against the literal
empty string check (`%s = ''`), so it needs the raw `search` value
unmodified. The second `%s` is the actual `ILIKE` pattern, which needs
the `%...%` wrapping. Passing the same raw value to both would silently
break the pattern match (a raw `search` string with no wildcards only
matches an exact name, not a substring).

---

## Apply and verify

1. Replace `_fetch_records` with the AFTER version — one function body
   instead of an `if`/`else` with two near-identical blocks.
2. `pytest` — any existing test covering `_fetch_records` (search and
   no-search cases) should still pass unchanged; the function's
   observable behavior is identical, only its internal shape changed.
3. `pylint src/` — should stay at 10.00/10.
4. Manual spot-check in the browser: load the crew dashboard with no
   search term (should show all role-filtered projects, same as
   before), then type a search term (should filter as before). Confirms
   the `WHERE %s = '' OR ...` logic behaves the same as the old
   `if search:` branch in practice, not just in theory.
