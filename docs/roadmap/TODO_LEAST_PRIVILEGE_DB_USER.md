# TODO: Return the app to a least-privilege database login

**Date noted:** 2026-10-22
**Status:** Deferred. Must be done BEFORE real business data goes back into
this database.

## Current state (seanchaí-only deployment, VPS `wcyj-meet`)

`docker-compose.yml` sets the app's DB login to `steward`
(`DBKIT_USER: ${POSTGRES_USER:-steward}`, `PGPASSWORD: ${POSTGRES_PASSWORD}`).

In the container deployment `steward` is the Postgres **superuser**
(`POSTGRES_USER`), so the app currently runs with full database rights. This
is acceptable only because:

- the stack is mesh-only (Headscale, bound to 100.64.0.1), and
- the database holds only seanchaí research data, not business data.

## Why it was done

The intended model is `web_app_user`: EXECUTE on `api.*` only, no table
access. The app does not honor that yet. Dashboard/list routes query views
directly (e.g. `projects.captain_view` in `_fetch_records`), which fails with
"permission denied for schema projects" for `web_app_user`. The pre-container
instance connected as `steward`, so that is what was restored.

## What to do before business data returns

Pick one (or do both in order):

1. **Interim:** add a new numbered SQL file granting `web_app_user` USAGE on
   the schemas and SELECT only on the tables/views the routes read directly
   (mirror `steward`'s SELECT grants). Switch `DBKIT_USER` back to
   `web_app_user` / `WEB_APP_USER_PASSWORD`. Writes stay on `api.*`.
2. **Proper:** move every direct list/read query behind an `api.*` function,
   so `web_app_user` needs EXECUTE only. Then no direct grants are needed.

Also consider a non-superuser `steward` (separate bootstrap superuser vs.
application owner role) so the admin login is not the superuser either.

## Done when

- `DBKIT_USER` in `docker-compose.yml` is not a superuser.
- `psql` as the app's login cannot `SELECT` from `identity.app_user`
  (password hashes) directly.
