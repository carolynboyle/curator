# SQL Conventions — wcyj / steward repo

Living document. Add to it as new patterns get established; don't try to
anticipate every future case up front.

---

## Primary keys

- `BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`, column named `id`.
- No exceptions across `audit`, `identity`, `projects`, `infrastructure`.

## Foreign keys

Two suffix conventions, and they mean different things to application code
— this distinction matters for anything (like `fieldkit`) that introspects
a table/view and needs to decide what to do with a column automatically:

- **`*_id`** — a real foreign key, always with a `REFERENCES` clause.
  User-facing (a project's `type_id`, a device's `node_id`, etc.). Any
  tool that auto-generates a form control from a column must treat every
  `*_id` column as "needs an explicit control declaration" — never
  default it to a plain number box. There are no bare, non-key
  integer/bigint columns anywhere in the current schema; if one is ever
  added (e.g. a quantity or integer-cents price for a future commerce
  schema), it should be treated the same way — explicit, not defaulted.

- **`*_by`** (`created_by`, `updated_by`) — also a `BIGINT` FK to
  `identity.app_user`, but server-stamped on save, never user-entered.
  These should not appear in any view meant to back a data-entry form —
  exclude them at the view layer, not by relying on downstream code to
  know to skip them.

- **`id`** itself — excluded from anything downstream the same way `*_by`
  is: it's identity, not a field a user fills in.

## Timestamps

- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` on every mutable table.
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, maintained by the
  shared `public.set_updated_at()` trigger — never set manually in
  application code.

## Ordering

- No `sort_order` columns on lookup tables — `ORDER BY name` in queries.
  Stated in `01_audit.sql`'s header and followed consistently across
  `identity.*` and `projects.*` lookup tables.
- `projects.tasks.sort_order` is the one exception, and it's slated for
  removal (confirmed zero live call sites as of 2026-07-01) — manual
  task ordering is handled by naming convention instead (`01_first
  task`, `02_second task`, sorted by description) rather than a
  dedicated column.

## Views

- `v_` prefix for any view, e.g. `v_project_detail`.
- **Detail views** (`v_project_detail`, `v_contact_detail`,
  `v_organization_detail`, ...) are a deliberate whitelist of exactly the
  columns a data-entry form should expose — not "everything on the
  table minus a few exclusions." `id` and `*_by` columns are never
  included. Server-generated fields the user shouldn't edit directly
  (e.g. `projects.projects.slug`) are also left out, even though nothing
  about their data type would otherwise flag them for exclusion.
- Column order in a detail view's `SELECT` list is meaningful — it's the
  order fields render in on the form. Reordering a form's fields means
  reordering the view's `CREATE VIEW` statement, not touching Python or
  template code.
- Role-filtered list views (`captain_view`, `scribe_view`, etc.) are a
  separate, older pattern — `SELECT p.*` plus role-mapping joins — not
  subject to the whitelist rule above, since they're not form-backing.

## Read/write path through `api.*`

- `web_app_user` has `EXECUTE` on `api.*` only — no direct table or view
  grants. This was stated as the intended model from the start
  (`06a_api_auth.sql`'s header) but wasn't actually true in practice for
  a while (`crew.py`'s detail-panel fetch functions queried
  `projects.projects` etc. directly). As of the 2026-07-01 detail-panel
  work, reads go through `api.get_*_detail()` functions the same way
  writes go through `api.save_*()` — no exceptions, no "just this one
  read is fine to do directly" carve-outs.
- `api.get_*_detail(id)` functions return `JSONB` (via `row_to_json`),
  `NULL` if the id doesn't exist — same "let Python check for None and
  404" contract the old direct-query fetch functions used, so callers
  didn't need to change their error handling.
- Lookups (`project_types`, `project_statuses`, future ones) go through
  `api.get_lookup(name)` with explicit dispatch (`CASE`/`IF-ELSIF` on a
  known set of names) — not a generic `EXECUTE format('SELECT ... FROM
  %s', p_view_name)`. Dynamic SQL built from a caller-supplied identifier
  is avoided on principle even when the immediate source (a YAML file
  under your own control) isn't an attacker-controlled input.
- **New functions need `06d_api_grants.sql` re-run.** The wildcard
  `GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api` is a snapshot at the
  time it executes, not a standing policy — it does not automatically
  cover functions created afterward. Any changedoc that adds new `api.*`
  functions must end with re-running the two `GRANT` lines from
  `06d_api_grants.sql`.

## Numbered migration files

- Already-applied files (`01`–`06d`) are not edited retroactively for
  new work — new schema changes get a new numbered file
  (`07_...`, `06e_...`) even if conceptually they'd sit naturally inside
  an earlier file. Keeps "what's actually been run against `wcyj`"
  unambiguous from the file list alone.
