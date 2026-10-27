# Design Doc — `api` Schema Function Export Tool

**Status:** Parked. Not scheduled — captured so the idea and the
review notes aren't lost before it's picked up.

## Problem

The `steward` repo's numbered `.sql` files (`06b_api_projects.sql`,
`06c_api_identity.sql`, etc.) have drifted out of sync with what's
actually live in `wcyj` — confirmed directly during Tasks UI wiring
(2026-07-10): `06b_api_projects.sql` doesn't contain `api.save_task()`
or `api.delete_task()` at all, even though both exist and work in the
live database. This is already a flagged gap from the 2026-07-08
handoff ("steward repo `.sql` files may be out of sync").

Separately, having each `api.*` function in its own file (rather than
only inside the large numbered files) would make it easier to:
- see at a glance everything that exists in `api.*`
- spot functions written for one entity that could be reused or
  patterned after for another
- diff a single function's history in git, rather than diffing a
  1000+-line numbered file every time one function changes

## Direction decided (2026-07-10)

This is a **documentation tool**, not a migration/DevOps tool —
`pgschema` (https://github.com/pgplex/pgschema, actively maintained,
Apache-2.0, Terraform-style declarative schema migration) was
evaluated and ruled out for this purpose: its dump step is oriented
around producing one consolidated, hand-editable `schema.sql` for a
plan/apply migration workflow, not one clean file per function for
browsing/reuse-spotting/diffing. Adopting it would mean taking on its
whole opinionated migration workflow for a feature (extraction) that's
a side effect of its actual purpose, not its core design.

`pg_extractor` remains the right direction — narrower in scope, closer
to the original need, permissively licensed, worth forking and
patching for current Postgres compatibility (see below).

**New idea, worth pursuing together:** integrate the forked
`pg_extractor` output with the existing "Dr. Filewalker" Project Crew
member (Carolyn's doc-gen package that walks a repo and produces
syntax-highlighted code documentation). Rather than the fork producing
a standalone folder of `.sql` files as its own separate artifact,
structure its output so Dr. Filewalker's existing walker picks up the
per-function files as just another set of source files in the tree —
giving `api.*` functions the same syntax-highlighted, browsable
treatment as the rest of the codebase, in the same place, rather than
a second disconnected place to remember to look. Open question when
this is picked up: does Dr. Filewalker walk a single repo tree today,
or would it need to pull from two sources (the repo tree, plus a
live-DB extraction step) as part of one run? That's the one piece of
new plumbing this idea actually needs — the fork's job is getting the
file naming/structure right so the handoff is clean, not building a
second presentation layer.

## Prior art — evaluate before building

Before writing a custom tool, check existing options:

- **`pg_extractor`** (https://github.com/omniti-labs/pg_extractor) —
  closest match to this need; purpose-built for dumping schema objects
  (including functions) to individual files with naming/directory
  conventions already worked out. Last commit ~5 years old as of
  2026-07-10. Licensed under the PostgreSQL License (permissive,
  BSD/MIT-equivalent, confirmed 2026-07-10) — no friction to fork,
  patch for current Postgres compatibility, and republish under the
  same license. Plan: fork, identify what's actually broken against a
  current Postgres version (likely candidates: renamed/shifted
  pg_catalog columns across major versions, deprecated pg_dump/psql
  flags, possible Python version drift if it's Python-based), fix, and
  either PR back to the original repo (worth trying even on a
  long-quiet repo) or maintain independently if it's abandoned for
  good.
- **`pglast`** (Postgres SQL parser via `libpg_query`) — solves a
  different problem (programmatic SQL analysis/transformation, not
  extraction-to-files). Not a fit for this specific need, but worth
  keeping in mind for potential future use (e.g. validating
  `queries.yaml`'s SQL syntactically before it hits the database).

## Starting point

A script (not originally written for this project) that uses
`pg_get_functiondef()` to export each function in a schema to its own
`.sql` file. The mechanism is sound — `pg_get_functiondef()` returns
a complete, correctly-delimited `CREATE OR REPLACE FUNCTION ...`
statement, which is much more reliable than trying to slice a
`pg_dump` schema dump apart by hand (e.g. via `awk` boundary-matching
on `$$;`, which is fragile the moment delimiter style isn't perfectly
consistent).

## Required changes before use in this project

1. **Connection config must go through `dbkit`, not raw
   `psycopg`/hardcoded credentials.** The original script's
   `DB_CONFIG` dict hardcodes `dbname`/`user`/`password`/`host`/`port`
   as literals — directly against this project's own convention
   (passwords in `~/.pgpass`, connection params in
   `~/.config/dev-utils/config.yaml`, never in code). Fix: use
   `dbkit.connection.DBConnection` directly instead of raw `psycopg`:

   ```python
   from dbkit.connection import DBConnection

   with DBConnection() as db:
       rows = db.fetch_all(
           """
           SELECT p.proname, pg_get_functiondef(p.oid)
           FROM pg_proc p
           JOIN pg_namespace n ON p.pronamespace = n.oid
           WHERE n.nspname = %s AND p.prokind = %s
           """,
           (SCHEMA_NAME, ...),
       )
   ```

   This also makes the script portable to any machine with
   `~/.pgpass`/`config.yaml` already set up, rather than tied to one
   hardcoded host.

2. **`prokind` filter should account for procedures, not just
   functions.** The original only selects `prokind = 'f'`. Every
   `api.*` object confirmed so far (`save_task`, `save_project`,
   `get_task_detail`, etc.) is a `FUNCTION`, so this is correct today
   — but if a real `PROCEDURE` (`prokind = 'p'`) is ever added to
   `api.*`, this filter would silently skip exporting it. Fix: either
   `prokind IN ('f', 'p')` from the start, or a code comment
   documenting the current all-functions assumption so a future
   `CREATE PROCEDURE` doesn't go missing from the export without
   anyone noticing.

3. **Overloaded functions would silently collide on filename.** Every
   function name in `api.*` is currently unique, so `{func_name}.sql`
   is safe as-is. If two functions ever share a name with different
   signatures, the second export would silently overwrite the first
   with no warning. Fix: use `pg_get_function_identity_arguments(p.oid)`
   to build a signature-qualified filename whenever more than one
   function shares a name (e.g. `save_task__jsonb_bigint.sql`), falling
   back to the plain name when there's no collision.

## Open question — where does this tool live?

This is a generic "dump any Postgres schema's functions to individual
files" utility, not specific to Curator's business logic. It likely
belongs alongside `dbkit`/`viewkit` in the `dev-utils` repo (as its own
small script or CLI entry point) rather than inside the `curator` repo
— consistent with `dbkit`/`viewkit` already being the home for
reusable, non-Curator-specific infrastructure. Not decided; revisit
when this is actually built.

## Open question — does this replace or supplement the numbered files?

Two different things this tool could produce, worth deciding
separately when it's actually built:

- **A reconciliation snapshot** — run once, diff by eye against
  `06b_api_projects.sql`/`06c_api_identity.sql`/etc., then manually
  update those numbered files to match reality. One-time use of the
  tool's output, not an ongoing artifact.
- **An ongoing parallel structure** — `.../api/functions/*.sql` living
  permanently alongside the numbered files, kept in sync going forward
  (e.g. regenerated after any Tasks-SQL-layer-style change). This adds
  a second place that needs updating every time a function changes —
  worth weighing against the "one canonical implementation" principle
  already applied elsewhere in this project (e.g. `_detail_panel_content.html`
  as the only panel renderer, `datasheet.js` as the only child-datasheet
  engine) before committing to it as a permanent parallel structure
  rather than a one-off tool.

## Not scoped yet

- Exact output directory structure (`steward/databases/wcyj/api/` vs.
  `scripts/` vs. something else) — Carolyn mentioned both `.../data`
  (seed files) and `.../sql` (numbered files) as existing conventions
  in the `steward` repo; where a new per-function folder fits alongside
  those isn't decided.
- Whether this becomes a one-off script or a proper CLI tool with
  options (schema name, output dir, dry-run, etc.).
- Any templating/header convention for the exported files (e.g. a
  comment noting "auto-generated, do not hand-edit — regenerate from
  wcyj" at the top of each file, to avoid someone editing the export
  and having it silently diverge from the live database again).
