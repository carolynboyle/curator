# Curator Handoff — 2026-06-28

## Session Summary
Built and stabilized the detail panel add/edit/delete flow for projects.
Primary accomplishment: new records can now be added, edited, and deleted
without page reload, with keyboard accelerators for rapid data entry.

---

## What Was Built This Session

### Detail Panel (add/edit mode)
- `+ Add Project` opens detail panel in new-record mode (empty form, focused Name field)
- `⋯` on a grid row opens detail panel in edit mode (populated from server)
- **Save** (Alt+S) — saves and closes panel, refreshes grid
- **New** (Alt+N) — saves current record, clears form, focuses Name (rapid entry)
- **Discard** (Alt+X / Escape) — closes without saving
- Status defaults to "active" if not selected on new records
- Duplicate slug handled gracefully with `-1`, `-2` suffix

### Grid
- `+ Add Project` button lives above Tabulator (not inside header — avoids sort trigger)
- Checkbox selection + Delete key deletes selected rows with confirmation
- `⋯` dimmed/disabled on unsaved rows
- `cellEdited` auto-saves inline edits to existing rows

### CSS / Asset Changes
- `buttons.css` created — site-wide button system (`.btn-primary`, `.btn-secondary`, etc.)
- `base.css` consolidated from `base.css` + `baseline.css` (baseline.css to be deleted)
- `detail-panel.css` cleaned of button styles (now in buttons.css)
- `base.html` updated: removed `baseline.css` link, added `buttons.css` link

### Backend (crew.py)
- `POST /crew/projects/save` — new project, defaults status to active, handles slug collisions
- `POST /crew/projects/{id}/save` — update existing project
- `DELETE /crew/projects/{id}` — delete project (required `GRANT DELETE ON projects.projects TO steward`)
- Generic `GET /api/query/{entity}/{query_name}` — powers child datasheets

---

## Current Known Issues / Cleanup

### Minor
- `baseline.css` still 404ing in some browser sessions — confirm `base.html` deployed correctly and `baseline.css` file deleted
- `tabulator.esm.js` 404 — harmless (Tabulator loads via CDN global), but noisy in console. Remove any remaining `import Tabulator from '...'` references if they exist
- All three action bar buttons (Save/New/Discard) should be same color — currently Save is teal, New/Discard are outlined. Fix: remove `.btn-save` from `.btn-primary` alias in `buttons.css`, make all three `.btn-secondary`

### Deferred
- Dropdown keyboard nav in Tabulator grid (type first letter to select from list editor)
- Dark theme text color issues on Captain page (black on black)
- Clipboard copy button above grid (visible only when rows selected)
- Dirty-state Save/Discard dialog timing for inline grid edits

---

## Next Build Sequence

### 1. Button color fix (5 min)
In `buttons.css`, change `.btn-save` to use secondary style same as `.btn-new` and `.btn-discard`.

### 2. Contacts / Identities detail panel
The Identities tab (Captain only) shows a two-panel org/contact filter view.
Clicking a contact should open the contact detail panel with:
- Details tab: name, title, notes
- Emails tab: child datasheet (identity.contact_emails — columns: label, address)
- Phones tab: child datasheet (identity.contact_phones — columns: label, number)
- URLs tab: child datasheet (identity.contact_urls — columns: url_type_id, value)
- Organizations tab: child datasheet (identity.organization_contacts — columns: org name, role)

Needs:
- `GET /crew/contacts/{contact_id}` route in crew.py
- `POST /crew/contacts/save` and `POST /crew/contacts/{id}/save` routes
- `DELETE /crew/contacts/{id}` route
- queries.yaml entries: `contact_emails.for_contact`, `contact_phones.for_contact`, etc.
- `openDetailPanel('contacts', id)` call from the Identities tab contact rows

### 3. Organizations detail panel
Similar to contacts:
- `GET /crew/organizations/{id}`, save, delete routes
- Contacts child datasheet

### 4. Tasks child datasheet (Projects detail panel)
The Tasks tab in the project detail panel is already stubbed.
Needs:
- `queries.yaml` entry: `tasks.for_project`
- `api-entities.yaml` already has tasks defined
- Test inline add/edit/delete in child datasheet

### 5. Auth
- bcrypt password hashing
- Signed session cookies (stateless)
- Single `<dialog>` login popup
- "Remember me" (30-day vs session cookie)
- Role-based routing server-side

---

## File Locations (current authoritative versions)

| File | Path |
|------|------|
| crew.py | src/curator/web/routes/crew.py |
| detail-panel.js | static/js/detail-panel.js |
| _detail_panel.html | src/curator/templates/partials/_detail_panel.html |
| _projects_table.html | src/curator/templates/partials/_projects_table.html |
| _datasheet.html | src/curator/templates/partials/_datasheet.html |
| buttons.css | static/css/components/buttons.css |
| base.css | static/css/base.css |
| detail-panel.css | static/css/components/detail-panel.css |
| base.html | src/curator/templates/base.html |

## DB Notes
- `steward` role now has SELECT, INSERT, UPDATE, DELETE on `projects.projects`
- `identity.contact_emails` column for email address is `address` (not `email`)
- `projects.status_id` is NOT NULL — always supply a value or default to active

## Infrastructure
- Dev: uvicorn on wcyjv20 localhost:8080
- DB: PostgreSQL on steward (100.64.0.7), database `wcyj`, role `steward`
- Repo: github.com/carolynboyle/curator
