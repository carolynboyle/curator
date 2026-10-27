# Changedoc: `api.get_field_schema()`

**Date:** 2026-07-04
**Reason:** First foundation piece of the generalized schema-driven form
system (`fieldkit`). Everything else in that system — the Tier-1
type-to-control map, the YAML override merge, eventually the fetch-and-swap
detail panel rendering — reads its column list from this one function.
SQL-only pass, per the database-first rule: verify in pgAdmin before any
Python is written against it.

**Scope check against `project_rules.md`:** single canonical
implementation (one function, all entities call through it — no
per-entity introspection code), no hardcoded values (view name is a
parameter, not baked in), database-first. No exceptions to flag.

**New numbered file, not an edit to an already-applied one** — per the
convention in `sql_conventions.md` ("already-applied files are not edited
retroactively for new work").

---

## Decisions made before writing this

1. **View name is schema-qualified.** Callers pass
   `'projects.v_project_detail'`, not `'v_project_detail'` — avoids any
   future ambiguity if two schemas ever have a same-named view.
2. **`STABLE`, not `VOLATILE`.** This only reads catalog metadata within
   a single call — appropriate for fieldkit's startup cache to treat as
   safe to call once and hold.
3. **No dynamic SQL.** `p_view_name` is compared against
   `table_schema || '.' || table_name` as an ordinary predicate value —
   not interpolated into a query string via `format()`/`EXECUTE`. Same
   principle already applied to `api.get_lookup()`'s planned dispatch
   design in `sql_conventions.md`: avoid dynamic SQL built from a
   caller-supplied identifier on principle, even when the immediate
   source is a YAML file under your own control, not attacker input.
4. **`NULL`/empty result on an unrecognized view name is a hard failure,
   not a silent skip.** This function itself just returns `NULL` (it has
   no way to know if that means "view doesn't exist" vs. "view exists
   with zero columns," which can't actually happen) — the "fail loudly
   at startup" behavior belongs in `fieldkit.py`, which will treat a
   `NULL`/empty result for any view name in its own config as a
   configuration error, not silently render an empty form.

---

## 1. `08_field_schema.sql` (new file)

**Anchor:** new file, runs after `07_detail_api.sql` (depends on the
`v_*_detail` views existing, though technically this function would work
against any view — the dependency is really "there's something worth
introspecting yet," not a hard SQL dependency).

```sql
-- =============================================================================
-- 08_field_schema.sql — API schema: get_field_schema() introspection function
-- =============================================================================
--
-- Foundation for fieldkit's schema-driven form rendering. Given a
-- schema-qualified view name, returns each column's name, Postgres data
-- type, and ordinal position as a JSONB array, ordered by position.
--
-- fieldkit calls this once per entity at startup (cached — this is
-- STABLE catalog metadata, not per-request data), then:
--   1. Applies the Tier-1 type-to-control map (varchar -> text,
--      text -> textarea, boolean -> checkbox, date -> date) to every
--      column this function reports.
--   2. Falls back to the YAML override file for anything Tier-1 can't
--      handle alone (all *_id columns, any bare integer, any field
--      whose default Tier-1 control is wrong for that specific field).
--   3. Fails loudly at startup if a *_id or bare-integer column has no
--      matching override — this function does not decide that; it just
--      reports what's in the view. fieldkit owns the "loud failure"
--      behavior.
--
-- View name is schema-qualified (e.g. 'projects.v_project_detail'), not
-- bare, to avoid ambiguity if two schemas ever have a same-named view.
--
-- No dynamic SQL — p_view_name is compared as an ordinary predicate
-- value against information_schema.columns, never interpolated into a
-- query string. Same principle as api.get_lookup()'s planned explicit
-- dispatch: caller-supplied identifiers don't get built into SQL text,
-- even from a trusted source.
--
-- Column order in the returned array is the column order in the view's
-- CREATE VIEW statement (ordinal_position) — this is what drives field
-- order on the rendered form, per the existing v_*_detail convention in
-- sql_conventions.md.
--
-- Depends on: nothing structurally — works against any existing view.
-- In practice used against 07_detail_views.sql's v_*_detail views.
-- GRANTs: web_app_user needs 06d_api_grants.sql re-run after this file —
-- the existing wildcard GRANT is a snapshot, it does not retroactively
-- cover functions created after it ran. See bottom of this file.
-- =============================================================================

CREATE OR REPLACE FUNCTION api.get_field_schema(p_view_name TEXT)
RETURNS JSONB
LANGUAGE sql
STABLE
AS $$
    SELECT jsonb_agg(
        jsonb_build_object(
            'name',      column_name,
            'data_type', data_type,
            'position',  ordinal_position
        )
        ORDER BY ordinal_position
    )
    FROM information_schema.columns
    WHERE table_schema || '.' || table_name = p_view_name;
$$;


-- =============================================================================
-- GRANTs — re-run, don't skip
-- The wildcard grant in 06d_api_grants.sql only covered functions that
-- existed in the api schema at the moment it ran. This function is new,
-- so without re-running this, web_app_user gets a permission error on
-- this function specifically, while every other api.* call keeps working
-- — an easy thing to chase as a mysterious bug if this step is skipped.
-- =============================================================================

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO web_app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO steward;
```

---

## Verification steps (pgAdmin, before any Python)

Run against `wcyj` as `steward` or `PG_Super`:

1. **Apply the file:**
   ```sql
   \i 08_field_schema.sql
   ```
   (or paste/run directly in the query tool)

2. **Verify against a known-good view:**
   ```sql
   SELECT api.get_field_schema('projects.v_project_detail');
   ```
   Expected: a JSONB array, one object per column in `v_project_detail`,
   in the same order the view's `SELECT` list defines them, each with
   `name`/`data_type`/`position`.

3. **Verify against the other two entities:**
   ```sql
   SELECT api.get_field_schema('identity.v_contact_detail');
   SELECT api.get_field_schema('identity.v_organization_detail');
   ```

4. **Verify the null case behaves as expected (not an error):**
   ```sql
   SELECT api.get_field_schema('projects.v_does_not_exist');
   ```
   Expected: `NULL`, no exception raised. This confirms fieldkit's
   startup-time check is the only thing standing between a typo'd view
   name and a silent failure — worth seeing this return `NULL` with your
   own eyes now, so there's no surprise later about what "misconfigured"
   looks like at the SQL layer.

5. **Confirm grants took effect:**
   ```sql
   SELECT * FROM information_schema.routine_privileges
   WHERE routine_name = 'get_field_schema';
   ```
   Expected: rows showing `EXECUTE` for both `web_app_user` and
   `steward`.

---

## What this does *not* do yet

- Doesn't touch Python at all — no `fieldkit.py` yet, nothing calls this
  function from the app.
- Doesn't decide control types — that's the Tier-1 map, next piece.
- Doesn't know about the YAML override file — that's also next.
- Doesn't change any existing entity's form rendering — projects,
  contacts, and organizations keep working exactly as they do today
  until fieldkit is built and actually wired in to replace their
  hand-coded templates.

Once you've verified all five steps above in pgAdmin, that's this piece
done — next step is the Tier-1 type map + the start of `fieldkit.py`
itself, reading this function's output.
