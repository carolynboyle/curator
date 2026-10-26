# Curator Handoff — 2026-06-26

## What Was Accomplished Today

### Datasheet — Projects Grid
- Replaced the two-row HTMX inline-edit pattern with a proper Tabulator
  datasheet grid
- Removed Pico CSS entirely — replaced with `baseline.css` (minimal resets)
- Grid is always light-themed regardless of app theme setting
- Compact 26px rows (pgAdmin-style)
- Checkbox column (left) for row selection with blue highlight
- `⋯` column (right) — wired, detail form deferred
- Double-click to edit cells
- Ctrl+C copies selected rows as tab-separated values (works on HTTP via
  execCommand fallback)
- Local filtering (filterMode: 'local') — search works instantly in browser
- `tabulator-overrides.css` — all colors hardcoded light, theme-proof

### Identities Tab — Two-Panel Layout
- Replaced sub-selector buttons (Contacts / Organizations / Users) with
  side-by-side org and contact listboxes
- Bidirectional filtering: click an org → contacts filter to that org;
  click a contact → orgs filter to that contact's orgs
- Search boxes above each panel double as selected-record display
- × clear pill resets both panels
- `⋯` detail button activates on selection (form deferred)
- `+ Organization` / `+ Contact` buttons (forms deferred)
- `identity.css` — new component CSS file for two-panel layout

### Fake Test Data
- `scripts/fake_contacts.py` — Faker seed script
- Generates 15 organizations, 40 contacts, emails, phones, org relationships
- Run with venv active: `source ~/projects/curator/.venv/bin/activate`
  then `python scripts/fake_contacts.py`

### Database
- `02_identity.sql` confirmed: organizations has `id, name, notes` only —
  no `type` or `website` columns (those were phantom fields, now removed)
- `identity.organization_contacts` junction table confirmed working

---

## Current State

- App runs at `localhost:8080`
- Theme: `dark` in `curator.yaml` (page is dark, grid is always light)
- Test data: 15 orgs, 40 contacts in database
- "Curator asdfasd" is a dirty test record in `projects.projects` —
  clean up in pgAdmin before next session

---

## Cleanup Items (not urgent, do in a batch)

1. Merge duplicate `if role == "captain":` blocks in `crew.py`
2. Fix text colors on Captain's page in dark theme (black on dark background)
3. Clipboard copy button — small button above grid, lower left, visible only
   when rows are selected
4. Dirty state Save/Discard dialog not firing correctly — likely timing issue
   introduced when switching from single-click to double-click to edit
5. Move `+` button above the projects grid, outside Tabulator header —
   currently inside column header, Tabulator intercepts click as sort trigger

---

## Next Session — Implementation Order

### 1. Reusable `_datasheet.html` partial (do this first)
Build before any detail forms. Parameterized Tabulator instance that accepts:
- `container_id` — div ID to mount to
- `columns` — column definitions
- `ajax_url` — data fetch endpoint
- `save_url` — POST save endpoint
- `add_url` — POST new row endpoint (optional)

CSS already works for any instance — `tabulator-overrides.css` applies
globally. No per-instance styling needed.

### 2. Project detail panel
See `detail_panel_design.md` for full spec. Summary:
- `⋯` on a project row → hero image fades out, detail panel fades in
- Fixed height (matches hero image ~420px)
- Tabbed interface within the panel:
  - **Details tab** — name, type, status, target date, description, notes
  - **Tasks tab** — child datasheet (reusable partial)
  - **Links tab** — deferred
  - **Contacts tab** — deferred
- Escape or × Close → panel closes, hero fades back in
- Datasheet always visible and interactive below panel

### 3. Contact detail panel
Same fixed-height tabbed panel pattern:
- **Details tab** — name, title, notes
- **Emails tab** — child datasheet
- **Phones tab** — child datasheet
- **URLs tab** — child datasheet
- **Organizations tab** — child datasheet (org name, role)

### 4. Org detail panel
- **Details tab** — name, notes
- **Contacts tab** — child datasheet (contact name, title, role)

### 5. Add forms
- `+` buttons for new project, contact, org
- Same panel area as detail forms

### 6. Users & DB Auth
- Flat table, simpler than contacts
- User must be a contact first (per schema constraint)
- `identity.app_user`: username, password_hash, role_id, is_active

### 7. Authentication
- Signed session cookies (stateless, no server-side session store)
- `bcrypt` for password hashing
- One login `<dialog>` triggered from landing page crew cards
- "Remember me" checkbox → 30-day cookie vs session-only
- Role-based routing: login → server looks up role → redirects to correct
  crew page
- Middleware intercepts unauthenticated requests, shows login dialog
- Headscale mesh handles network-level access; Curator handles app-level auth

### 8. Mobile layout pass (do once, after all forms exist)
- Identity panel: toggle buttons for orgs/contacts on small screens
- Detail panel: already works (replaces hero, list below)
- Breakpoint: 768px

### 9. Configuration tab
- Project types and statuses management
- Crew role management
- Deferred until after auth (Captain-only feature)

---

## Key Design Decisions Made

### Detail Panel
- Lives in the hero image area — fades out hero, fades in form
- Fixed height (~420px), content scrolls within
- Tabbed interface for grouped content
- Child datasheets (tasks, emails, etc.) scroll within their tab panel
- No page navigation — URL does not change on record open
- Dirty state dialog before close/switch (currently broken — cleanup item)

### Authentication
- Single login dialog for all roles
- Role determined server-side from `identity.app_user.role_id`
- Signed session cookies, stateless
- Remember me → 30-day expiry vs browser session
- Mesh (Headscale) provides network-level access control separately
- Felipe gets a mesh node with ACLs limiting him to port 8080 only

### Datasheet
- Always light theme regardless of app theme
- Double-click to edit, single-click to select row
- Ctrl+C copies selected rows as TSV
- Local filtering (not remote) — adequate for expected data volumes
- `+` to add new record lives above the grid, not inside Tabulator header

---

## File Locations

| File | Purpose |
|------|---------|
| `curator/web/routes/crew.py` | Dashboard routes, project + identity queries |
| `templates/captain.html` | Captain page — tabs, projects grid, identity panels |
| `templates/crew.html` | Non-captain crew pages |
| `templates/_projects_table.html` | Tabulator projects datasheet |
| `templates/_crew_header.html` | Hero image partial |
| `static/css/components/tabulator-overrides.css` | Tabulator compact grid styles |
| `static/css/components/identity.css` | Two-panel identity layout |
| `static/css/components/baseline.css` | Minimal element resets (replaces Pico) |
| `static/css/themes/dark.css` | Dark theme variables |
| `static/css/themes/light.css` | Light theme variables |
| `scripts/fake_contacts.py` | Faker seed script for test data |
| `docs/changes/` | All changedocs from this session |

---

## Reference Docs Produced This Session

- `DATASHEET_ALL_FIXES.md` — complete datasheet implementation
- `CONTACTS_TWO_PANEL.md` — identity two-panel layout
- `detail_panel_design.md` — detail panel design spec (read before next session)
