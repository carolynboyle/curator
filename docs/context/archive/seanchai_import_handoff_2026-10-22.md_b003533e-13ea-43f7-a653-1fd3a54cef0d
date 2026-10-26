# Seanchaí ledger import — handoff (2026-10-22)

Paste-able prompt for a fresh conversation. State as of 2026-10-22.

## Working style
- Discuss approach first; write no scripts/files until Carolyn says go.
- Always request project_rules.md if it isn't attached, and follow it.
- Carolyn runs commands on the VPS herself, ONE step at a time, and pastes output back. Small steps, with a check per step.
- Claude can read/push to GitHub repos carolynboyle/steward and carolynboyle/curator (add them to the session). Tell her whenever a repo changes. Use branches, not main. Provide complete files, not snippets.

## Where things stand
Curator (FastAPI + Postgres + Jinja2 + Tabulator; database-first, api.* stored procedures are the write path) runs as Docker containers on the Hetzner VPS wcyj-meet, mesh-only (Headscale/Tailscale IP 100.64.0.1):
- URL from the Mac: http://100.64.0.1:8090 (turn off Proton VPN or it returns 503).
- Login: user "carolyn" (admin/captain). Seanchaí page: /seanchai/ — works, empty (Records and Searches tabs).
- Stack in ~/projects/curator on the VPS (docker-compose: db = postgres:16, user steward, database wcyj; app). SQL is applied manually:

      cd ~/projects/curator
      DB="docker compose exec -T db psql -U steward -d wcyj -v ON_ERROR_STOP=1"
      S=~/projects/steward/databases/wcyj/sql
      $DB < $S/<file>.sql

- The app currently connects as steward (a superuser in the container) because list routes query views directly. Temporary — see docs/roadmap/TODO_LEAST_PRIVILEGE_DB_USER.md in the curator repo. Must be reversed before business data returns.

## Repos / branches (NOT yet merged to main)
- steward, branch `recovered-core-sql`: 7 added files in databases/wcyj/sql — 03b, 06c, 06e, 07_detail_views, 07_detail_api, 08_field_schema (made SECURITY DEFINER), 08b_api_lookup (includes record_types/record_statuses). Rebuilt from applied changedocs because the repo lagged the live DB.
- curator, branch `seanchai-fieldkit-overrides`: fieldkit_overrides.yaml entries for seanchai record_id/search_id, docker-compose using the steward login, the least-privilege TODO doc. Both branches are checked out on the VPS.
- The Dockerfile on the VPS is modified but uncommitted (copies README.md, src/, static/; installs git; editable pip install). Needs committing.
- Seanchaí SQL files are still named 07_seanchai / 07b / 07c; plan is rename to 10a/10b/10c (module block starts at 10; todos would be 10d). Do later, not now. Never alter anything the old instance (wcyjv20, offline) depends on; new SQL is additive numbered files only.

## Existing seanchai schema (07_seanchai.sql, applied)
Schema seanchai: record_type (code, name; seeded PR, WL, MG, GV, BIO, FB, MR, NR, PT, ROM, EX), record_status (active, excluded, needs_review, duplicate), records (id, record_id VARCHAR(20) unique e.g. PR-001, record_type_id, record_status_id, display_order, year VARCHAR(20), subject, county, state default 'PA', source_citation, source_url, notes, audit cols), searches (search_id e.g. SRCH-001, search_terms, county_scope, year_filter, result_count, status, notes, searched_at), record_links.
Write path: api.save_record / api.save_search (JSONB payload, ids not names); delete is a soft delete (status excluded). Reads: api.list_records, api.get_record_detail, api.list_searches, api.get_search_detail.

## The job
1. Source: research ledger artifact in the "seanchaí" Claude Project (~102 records, 12+ searches, 20+ todos). Structure doc saved at ~/projects/seanchaí/docs on the Mac (Carolyn will attach). The artifact/Project cannot be reached from the coding session; she supplies the data.
2. Decide the mapping from ledger fields to existing tables, and what the ledger has that the schema lacks. Known gaps: a todos table/routes/API (planned 10d); the richer model noted earlier (persons, parcels, ark_id, search<->record junction, sub-documents). Decide what's needed now vs later. Nothing may conflict with the old schema.
3. Choose the import path (through api.save_* vs direct SQL as steward for a one-time load), with a dry run, row counts to verify (102 records, 12+ searches, 20+ todos), and an easy undo.
4. Quick UI check after import.

## Parked (not part of the import conversation)
Landing-page card for seanchaí (proposed: a `modules:` list in curator.yaml rendered after the crew cards); header filters (Type/Status/Year/County) on the records grid (only Subject has one today); whether to keep the County column; merging the two branches; renaming SQL to 10a/10b/10c; writing docs/deployment.md (requirements incl. git/curl in the image, port 8090, README/static copies); committing the Dockerfile.
