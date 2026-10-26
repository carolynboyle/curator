# Changedoc: `api.get_lookup()`

**Date:** 2026-07-04
**Reason:** Makes `fieldkit_overrides.yaml`'s `source: project_types`/
`source: project_statuses` placeholders actually functional — the last
SQL piece needed before fetch-and-swap can render real `<select>` options
instead of empty dropdowns. Database-first, per convention: verify in
pgAdmin before any Python touches it.

**Scope check against `project_rules.md`:** single canonical
implementation (one function, every select field's options go through
it); no hardcoded values (source name is a parameter); no dynamic SQL
built from a caller-supplied identifier — explicit `CASE` dispatch on a
known set of source names, per the design already stated in
`sql_conventions.md` for this exact function ("Lookups... go through
`api.get_lookup(name)` with explicit dispatch... not a generic `EXECUTE
format(...)`... avoided on principle even when the immediate source (a
YAML file under your own control) isn't attacker-controlled input").

---

## Decisions made before writing this

**1. `SECURITY DEFINER` is required here, unlike `get_field_schema()`.**
`get_field_schema()` only reads `information_schema.columns`, which is
globally readable regardless of role — no elevation needed.
`get_lookup()` reads `projects.project_type`/`projects.project_status`
directly, and `web_app_user` has no direct table grants at all (`api.*`
EXECUTE only, per `06a_api_auth.sql`'s security model) — so this
function must run as the owner (`SECURITY DEFINER`) or `web_app_user`
gets a permission error the moment it's called.

**2. Return shape: `[{"value": id, "label": name}, ...]`, ordered by
`label`.** Matches the "no `sort_order` on lookup tables — `ORDER BY
name`" convention already in `sql_conventions.md`. `value`/`label` names
chosen to map directly onto an HTML `<option value="...">label</option>`
without any renaming step in the Jinja layer.

**3. Unknown source name returns `NULL`, matching `get_field_schema()`'s
contract — not a raised exception.** Both are "plain read" functions
(as opposed to the enveloped `save_*`/`delete_*` pattern), so they
should behave the same way on a miss. This does mean a typo'd `source:`
value in `fieldkit_overrides.yaml` won't be caught until something
actually tries to render that field and gets an empty dropdown — **not**
caught at app startup the way a missing override entry is. Flagging this
as a real gap, not a hidden one: closing it would mean `fieldkit` calling
`get_lookup()` once per declared `source:` at startup and failing loudly
if any comes back `NULL`, mirroring the existing pattern exactly. Worth
doing, but it's a `fieldkit.py` change, not part of this SQL-only pass —
your call whether to fold it in now or as its own follow-up.

**4. Only two known sources for now: `project_types`, `project_statuses`.**
Matches the two `source:` values already sitting in
`fieldkit_overrides.yaml`. Adding a new source later means adding one
`WHEN` branch — small, obvious, matches the file-numbering convention of
"new work gets a new numbered file" if it happens later rather than
editing this one retroactively... though for `CASE` branches specifically,
editing this same function with `CREATE OR REPLACE` is normal and
expected (unlike a numbered schema-migration file, a function's `CASE`
list isn't "already applied and frozen" in the same sense — it's meant
to grow).

---

## `08b_api_lookup.sql` (new file)

Numbered to follow `08_field_schema.sql` without renumbering anything —
same "foundation pieces" group, next available number.

```sql
-- =============================================================================
-- 08b_api_lookup.sql — API schema: get_lookup() explicit-dispatch function
-- =============================================================================
--
-- Populates select-field options for fieldkit-rendered forms. Every
-- FieldDef with a "source" value (declared in fieldkit_overrides.yaml)
-- gets its options from this one function, keyed by that source name.
--
-- Explicit CASE dispatch on a known, fixed set of source names — NOT
-- dynamic SQL built from p_source (no format()/EXECUTE with an
-- interpolated identifier). Per sql_conventions.md: this principle
-- applies even though the only caller of p_source is fieldkit reading
-- a YAML file under your own control, not attacker-supplied input.
--
-- SECURITY DEFINER required (unlike get_field_schema, which only reads
-- information_schema): this function reads projects.project_type /
-- projects.project_status directly, and web_app_user has no direct
-- table grants at all — EXECUTE on api.* only, per 06a_api_auth.sql.
--
-- Return shape: JSONB array of {"value": id, "label": name}, ordered by
-- label — matches "no sort_order on lookup tables, ORDER BY name"
-- (sql_conventions.md). NULL for an unrecognized source name, same
-- "let the caller check for None" contract as get_field_schema() — see
-- this changedoc's point 3 for the tradeoff that implies.
--
-- Adding a new source later: add one WHEN branch below and re-run this
-- file (CREATE OR REPLACE) — unlike numbered schema-migration files,
-- this function's CASE list is expected to grow in place, not be
-- superseded by a new numbered file each time.
--
-- Depends on: 03_projects.sql (projects.project_type, projects.project_status)
-- GRANTs: web_app_user needs 06d_api_grants.sql re-run after this file —
-- the existing wildcard GRANT is a snapshot, it does not retroactively
-- cover functions created after it ran. See bottom of this file.
-- =============================================================================

CREATE OR REPLACE FUNCTION api.get_lookup(p_source TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSONB;
BEGIN
    CASE p_source
        WHEN 'project_types' THEN
            SELECT jsonb_agg(
                       jsonb_build_object('value', id, 'label', name)
                       ORDER BY name
                   )
            INTO v_result
            FROM projects.project_type;

        WHEN 'project_statuses' THEN
            SELECT jsonb_agg(
                       jsonb_build_object('value', id, 'label', name)
                       ORDER BY name
                   )
            INTO v_result
            FROM projects.project_status;

        ELSE
            v_result := NULL;
    END CASE;

    RETURN v_result;
END;
$$;


-- =============================================================================
-- GRANTs — re-run, don't skip
-- The wildcard grant in 06d_api_grants.sql only covered functions that
-- existed in the api schema at the moment it ran. This function is new,
-- so without re-running this, web_app_user gets a permission error on
-- this function specifically, while every other api.* call keeps
-- working — an easy thing to chase as a mysterious bug if skipped.
-- =============================================================================

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO web_app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO steward;
```

---

## Verification steps (pgAdmin, before any Python)

1. **Apply the file**, then verify each known source:
   ```sql
   SELECT api.get_lookup('project_types');
   SELECT api.get_lookup('project_statuses');
   ```
   Expected: a JSONB array of `{"value": ..., "label": ...}` objects,
   ordered alphabetically by `label`, one entry per row in
   `projects.project_type`/`projects.project_status`.

2. **Confirm the unknown-source case returns NULL, not an error:**
   ```sql
   SELECT api.get_lookup('nonexistent_source');
   ```
   Expected: `NULL`, no exception. Worth seeing this with your own eyes
   given point 3 above — this is the gap that means a typo'd `source:`
   in the YAML file won't crash the app at startup the way a missing
   `*_id` override does.

3. **Confirm grants took effect:**
   ```sql
   SELECT * FROM information_schema.routine_privileges
   WHERE routine_name = 'get_lookup';
   ```
   Expected: `EXECUTE` rows for both `web_app_user` and `steward`.

---

## What this does *not* do yet

- Doesn't touch Python — `fieldkit.py`'s `source:` values still aren't
  wired to anything; that's the render-step work (fetch-and-swap)
  itself, next.
- Doesn't validate `fieldkit_overrides.yaml`'s `source:` values at
  startup — see point 3. If you want that closed before moving on, say
  so and I'll draft the small `fieldkit.py` addition for it; otherwise
  it's a known, flagged gap going into fetch-and-swap.
