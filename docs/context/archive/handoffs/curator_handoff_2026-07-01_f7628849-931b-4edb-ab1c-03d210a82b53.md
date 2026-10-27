# Curator Handoff — 2026-07-01

## Session summary

This session covered two threads: (1) closing out the contacts/organizations
backend work that was left mid-stream from a prior session, and (2) surfacing
a real gap in the detail panel that blocks contacts/organizations from being
usable yet, discovered while testing.

---

## Completed and verified this session

**SQL — `06a`/`06b`/`06c`/`06d` (replaces old `06_api.sql`)**
- Split `06_api.sql` into four files by concern: `06a_api_auth.sql` (session/login),
  `06b_api_projects.sql` (save/delete_project), `06c_api_identity.sql` (new:
  save/delete_contact, save/delete_organization), `06d_api_grants.sql` (shared
  wildcard grant for both `web_app_user` and `steward`).
- Applied in pgAdmin against `wcyj`. Verified via `information_schema.routines`
  — all 11 functions present. Verified via `information_schema.routine_privileges`
  — both roles have EXECUTE on all 11.
- Old `06_api.sql` should be deleted from the repo now that these four replace it.

**`crew.py` — contacts/organizations routes**
- Added `_fetch_contact_for_display`, `_fetch_organization_for_display`, and
  eight routes: `GET/POST /crew/contacts/*`, `GET/POST /crew/organizations/*`,
  plus DELETE for both. Mirrors the existing project route pattern exactly
  (`_call_proc`, JSON envelope check, re-fetch after write).
- Full corrected file was regenerated and applied directly (not a changedoc)
  after a prior partial-apply attempt.

**`detail-panel.js` — title field bug fix**
- `populateForm()` was missing a `title` field mapping — editing an existing
  contact would silently blank its title on save. Fixed: added `titleField`
  alongside the existing `nameField`/`typeField`/`statusField`/`descField`.

**`forms.yaml` — button class fix**
- Save/New/Discard buttons all had only `btn-secondary`, no entity-specific
  class (`btn-save`/`btn-new`/`btn-discard`), which `detail-panel.js`'s click
  handler requires. Fixed: both classes now present on each button
  (e.g. `"btn-secondary btn-save"`). Confirmed working — Save, New (rapid
  data-entry: save current + clear for next), and Exit all work by click now,
  not just by Alt-key.

**Tests**
- New file: `tests/unit/test_routes_crew_identities.py` — 13 tests mirroring
  the existing `test_routes_crew.py` conventions (empty/whitespace/missing-name
  guards, success-response-shape contract, organization-only duplicate-name
  rejection, 404 on missing record). All passing.
- Full suite: 22/22 passing (`tests/unit/test_routes_crew.py` +
  `tests/unit/test_routes_crew_identities.py`).

**Manually confirmed in browser**
- New project via `+ Add Project`: works.
- New/Save/Exit buttons inside an open project's detail panel: all work by
  click now.

---

## The real gap found this session — not yet fixed

**Problem:** `_detail_panel.html` is rendered once, server-side, when
`crew.html` loads — always with `entity='projects'`. `openNewRecordPanel()`/
`openDetailPanel()` in `detail-panel.js` don't re-render the panel; they just
relabel `data-entity` on the already-rendered DOM and clear input values.
Result: clicking `+ Organization` or `+ Contact` (or double-clicking an
existing org/contact in the Identities two-panel list) opens the **Projects**
form — same fields (Name/Type/Status/Description), same child tabs
(Tasks/Links/Contacts) — with only an invisible `data-entity` attribute
distinguishing it. Visually and functionally indistinguishable from clicking
`+ Add Project`.

**This was initially mistaken for a routes/backend problem** but it isn't —
the contacts/organizations routes, procs, and JS save logic are all correctly
built and unit-tested. The panel simply never shows the right form to save
in the first place, so the working backend has no way to be exercised
correctly through the UI yet.

**Two candidate fixes discussed, neither built yet:**
1. **Fetch-and-swap** — `openNewRecordPanel`/`openDetailPanel` fetch a
   server-rendered Details-tab fragment for the requested entity and replace
   the panel's HTML wholesale, instead of just clearing inputs. One extra
   round-trip per open. Keeps `_detail_panel.html`'s entity branches as the
   single source of truth.
2. **Pre-render all three, toggle visibility** — `crew.html` renders all
   three entities' Details-tab field sets into the DOM up front (hidden via
   CSS), JS shows/hides based on `data-entity`. Rejected as a kluge — doesn't
   scale if a fourth entity or more fields get added, duplicates markup.

**Leaning toward fetch-and-swap**, but this wasn't designed in detail — needs
a fresh, clear-headed session rather than a bolt-on at the end of a long one.

---

## Next steps (for the new conversation)

1. Design and build the fetch-and-swap panel fix — this blocks everything
   else identities-related, so it's the necessary first task, not optional
   scope.
2. Once the panel actually shows the right form: manually verify contacts
   Save (add + edit) and organizations Save (add + edit, including the
   duplicate-name rejection message actually displaying) end-to-end through
   the browser. This has never been confirmed working end-to-end — only the
   routes/procs in isolation.
3. Design the actual Contacts and Organizations Details-tab field layouts
   (contacts: name/title/notes — notes field not yet added to the form;
   organizations: name/notes — same gap).
4. Child datasheets (Emails/Phones/URLs on contacts, Contacts on
   organizations) are still "coming soon" placeholders — out of scope until
   the above is solid.

---

## Someday / cleanup list (unrelated, lower priority, not blocking)

- `crew.py`: the pylint-exception comment for `_render_crew_dashboard_html`'s
  6-parameter signature is attached to the wrong function (`crew_dashboard`
  instead of `_render_crew_dashboard_html` itself) — cosmetic, pylint still
  flags it. Should already be logged in the dev-utils roadmap someday list.
- Old `06_api.sql` should be deleted from the repo now that `06a`-`06d`
  replace it.
