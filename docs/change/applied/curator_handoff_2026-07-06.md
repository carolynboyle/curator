# Curator Handoff — 2026-07-06

## Session summary

Picked up from the 2026-07-04 session's detail-view read path work.
This session built the entire schema-driven form system end to end
(`fieldkit`), wired it into a real fetch-and-swap detail panel replacing
the old hardcoded per-entity form, deduplicated route code across all
three entities, and fixed a real gap in the Identities tab. Also
surfaced — but did not yet fix — a significant pre-existing gap: there
is no way in the live app to associate a contact with an organization,
or to enter emails/phones/URLs for a contact.

---

## Completed and verified this session

**`api.get_field_schema()` — SQL, applied and verified in pgAdmin**
- `08_field_schema.sql`: introspects `information_schema.columns` for a
  given schema-qualified view name, returns JSONB array of
  `{name, data_type, position}`, ordered by column position.
- `STABLE`, no `SECURITY DEFINER` needed (catalog metadata is globally
  readable). Grants re-run and confirmed for `web_app_user`/`steward`.
- Verified against all three `v_*_detail` views; unknown-view-name
  case confirmed to return `NULL`, not an error.

**`api.get_lookup()` — SQL, applied and verified in pgAdmin**
- `08b_api_lookup.sql`: explicit `CASE` dispatch (no dynamic SQL) on a
  fixed set of source names — `project_types`, `project_statuses` are
  the only two right now. `SECURITY DEFINER` (unlike `get_field_schema`,
  this reads `projects.project_type`/`project_status` directly, and
  `web_app_user` has no direct table grants at all).
- Returns `[{"value": id, "label": name}, ...]`, ordered by label.
  `NULL` for an unrecognized source name — same "let the caller check
  for None" contract as `get_field_schema()`.
- Verified: both known sources return real data, unknown source returns
  `NULL` with no error, grants confirmed.

**`fieldkit.py` — the core engine, fully built and verified**
- `FieldKit.create(db, view_name, overrides_path=None)`: async factory.
  Calls `get_field_schema()`, applies the Tier-1 Postgres-type-to-control
  map (`character varying`→text, `text`→textarea, `boolean`→checkbox,
  `date`→date), merges in `fieldkit_overrides.yaml` for anything Tier-1
  can't decide (every `*_id`/integer column).
- **Fails loudly (`FieldSchemaError`) at construction** — i.e. at
  FastAPI startup, via `app.py`'s `lifespan` — in three cases: view has
  no columns (bad name), a `*_id`/integer column has no override entry,
  or a declared `source:` doesn't resolve via `get_lookup()`. A real bug
  was caught this way during development: the `id` column itself is
  `bigint` and was incorrectly triggering the override-required check
  before a fix explicitly excluded it (it's never rendered as a field —
  it identifies the record).
- Caches resolved select-field options (`FieldKit.options`, keyed by
  source name, deduplicated across fields sharing a source) so the
  render step never re-queries `get_lookup()` per request.
- Override file: shipped default `curator/data/fieldkit_overrides.yaml`,
  optional user override `~/.config/curator/fieldkit_overrides.yaml`,
  merged via `ConfigManager._merge()` (reused, not duplicated). Currently
  declares `type_id`/`status_id` on projects only — contacts/
  organizations have no `*_id` columns at all (confirmed via pgAdmin).
- 16 unit tests, all mocked (no real DB/YAML), covering the Tier-1 map,
  override-required enforcement, source validation, `id` exclusion,
  missing-view handling, column-order preservation, and options caching.

**Fetch-and-swap detail panel — fully wired and verified in-browser**
- `GET /panel/{entity}/new` and `GET /panel/{entity}/{record_id}`
  (`panel.py`, new route file) render the entire panel body — tab
  navigation, the fieldkit-driven Details form, and action buttons — as
  one HTML fragment, using the same raw `jinja2.Environment` pattern
  `crew.py` already uses (not FastAPI's `Jinja2Templates`).
- `_detail_panel.html` reduced to a bare shell; `_detail_panel_content.html`
  (new) holds the actual tab bar + form; `_detail_form_fields.html` (new)
  is the fieldkit-driven field loop, dispatching on `field_type`.
- `detail-panel.js`: `openDetailPanel`/`openNewRecordPanel` now fetch
  the whole panel body and swap it into `.detail-panel` wholesale,
  instead of fetching JSON and populating a hardcoded list of known
  field names (`type_id`/`status_id`/`description`/`title`). This was
  fixed twice this session — the first pass only swapped the field
  inputs, leaving the *tab bar* stuck showing whichever entity's tabs
  happened to be baked in at page load (e.g. a contact's panel showing
  Tasks/Links/Contacts instead of Emails/Phones/URLs/Organizations); the
  second pass extended the swap to cover the whole panel body.
- Manually verified in-browser: opening/creating projects, contacts, and
  organizations all show the correct fields, correct tab set, and
  correctly populated `<select>` options (real type/status data, not
  placeholders).

**Route deduplication — `deps.py` gained four shared helpers**
- `get_user_id(request)`, `require_name(name)`, `get_detail_or_404(...)`,
  `delete_via_proc(...)` — extracted from identical or near-identical
  code repeated across `projects.py`/`contacts.py`/`organizations.py`'s
  save/delete/get-single routes (9 copies of the user_id line, 6 copies
  of the name-required guard, 3 copies each of the get-or-404 and
  delete-or-fail patterns).
- `projects.py`'s `_fetch_records` also collapsed its search/no-search
  duplicate SQL blocks into one query with a conditional `WHERE`.
- A small residual `R0801` match (both `contacts.py`/`organizations.py`
  save routes share a 5-line `notes`/`require_name`/`get_user_id`
  sequence) was left in place with a documented `pylint` disable rather
  than forced into an artificial shared helper — it's coincidental
  overlap between unrelated field sets, not a real shared concept.

**Identities tab — real gap found and partially fixed**
- Double-click-to-open on the org/contact listboxes is wired correctly
  in `bidirectional-filter.js` (confirmed via DevTools' Event Listeners
  panel) but wasn't reliably firing in the browser — root cause not
  chased down (a UI reflow between the two clicks of a double-click was
  the leading theory, not confirmed).
- Fixed by adding a `⋯` button to the shared selection readout,
  reusing the exact same `detail-icon` pattern already working on the
  Projects datasheet — select a row, then click `⋯` to open it. No
  dblclick reliability involved. Verified working for both
  organizations and contacts.

**Pylint/pytest — clean throughout**
- `pylint src/` at 10.00/10, `pytest` at 40 passing, confirmed multiple
  times across the session as each piece landed.

---

## Real gaps found this session — not yet fixed

**No way to associate a contact with an existing organization.** The
Identities tab's two listboxes only show/filter the relationship
read-only — there is no save path anywhere in the app for
`identity.organization_contacts` (the join table). This surfaced
because the person tried to use it and found nothing happened. A
design for this already exists in `CONTACTS_TWO_PANEL.md` (a datasheet
with a Role column, `save_url: /crew/organizations/contacts/save`), and
the *read* side is further along than expected — `queries.yaml` already
has working `organization_contacts.for_organization`/`for_contact`
queries with the Role join. What's missing: the save/delete procs, the
route, and wiring the still-placeholder Contacts/Organizations child
tabs to a real datasheet.

Two design decisions were reached on this, not yet built against:
- **No "primary organization" field** — confirmed unnecessary; the
  bidirectional filter already shows the relationship adequately, adding
  a primary flag would be speculative clutter with no current consumer.
- **"+ Organization" (on a contact) needs a picker for an *existing*
  organization**, not a blank free-text row like Emails/Phones will use
  — this is a real UX difference from the other child-datasheet work,
  still undecided exactly how the picker should look/behave.
- Whether **Role** is free text or a `identity.organization_contact_role`-backed
  dropdown is also still undecided.

**No way to enter emails, phones, or URLs for a contact.** Same root
cause as above — `v_contact_detail` only has `name`/`title`/`notes`;
email/phone/URL are separate child tables
(`identity.contact_emails`/`contact_phones`/presumably a URLs
equivalent), and their tabs are still "coming soon" placeholders. This
is the same shape of work as the org/contact association (child
datasheet, Tabulator, save/delete proc pair) but structurally simpler —
no "pick an existing record" complexity, just add/edit/remove rows that
belong solely to one contact.

**`panel.py` has no unit tests.** Flagged, not fixed, in both panel
changedocs — testing it meaningfully requires mocking
`request.app.state.fieldkit`, a different shape than the `db`-mocking
pattern used everywhere else.

**Curator (the web app) still has no logging infrastructure.** Noted in
memory this session; deferred, matching `fletcher`/`contactkit`'s
eventual pattern when it gets built.

**Tasks — the thing that motivated the whole fieldkit detour — hasn't
been started yet.** No `v_task_detail` view, no `api.get_task_detail()`/
`save_task()`/`delete_task()`, no `tasks` entry in
`fieldkit_overrides.yaml`. With fieldkit and fetch-and-swap now fully
working, adding Tasks should mean: one new view, three new API
functions, one `_FIELDKIT_VIEWS`/`_FETCH_FUNCTIONS` entry each in
`app.py`/`panel.py`, and override entries only if Tasks turns out to
have `*_id` columns (`project_id`, possibly `parent_id` for subtasks) —
no new form-rendering code required at all, which was the entire point
of doing this work first.

---

## Current architecture state

- `fieldkit.py` (`curator/web/fieldkit.py`): schema introspection →
  Tier-1 type map → YAML override merge → startup validation → cached
  options. Fully generic across all three current entities.
- `panel.py` (`curator/web/routes/panel.py`): `GET /panel/{entity}/new`
  and `GET /panel/{entity}/{id}`, rendering the whole panel body via
  `_detail_panel_content.html`.
- `_detail_panel.html`: bare shell, no entity-specific markup.
- `_detail_panel_content.html` / `_detail_form_fields.html`: the actual
  rendered content, fetched per panel open.
- `detail-panel.js`: fetch-and-swap wholesale into `.detail-panel`;
  `clearForm()`/`focusName()` unchanged (already generic enough).
- `bidirectional-filter.js`: unchanged cross-filter logic, plus the new
  `⋯` detail button wiring.
- `deps.py`: `get_db`/`get_config`, `_fetch_json_scalar`/`call_proc`/
  `call_proc_and_refetch`, plus this session's
  `get_user_id`/`require_name`/`get_detail_or_404`/`delete_via_proc`.
- `curator/exceptions.py`: added `FieldSchemaError(CuratorError)`.
- `08_field_schema.sql`/`08b_api_lookup.sql`: applied, verified.

---

## Next session's priority

Two real candidates, both legitimate — worth an explicit choice rather
than defaulting:

1. **Close the Identities gaps** (contact↔organization association,
   emails/phones/URLs) — these are things a person actually tried to
   use this session and found missing. Emails/Phones is probably the
   simpler starting point (no picker-for-existing-record complexity);
   the org/contact association needs the two open design decisions
   above resolved first.
2. **Build Tasks** — the original motivation for all of this session's
   work, now genuinely unblocked. Likely the faster win given fieldkit
   and fetch-and-swap are proven, but leaves the Identities gaps open a
   while longer.

---

## Suggested commit

Everything above is applied and verified (pylint 10.00/10, pytest
40 passing as of the last check this session). One commit, or split by
logical chunk if preferred:

```
launch: fieldkit schema-driven forms + fetch-and-swap detail panel

- api.get_field_schema()/api.get_lookup(): SQL introspection and
  explicit-dispatch lookup functions, verified in pgAdmin
- fieldkit.py: Tier-1 type map, YAML override merge, id-column
  exclusion, source validation, cached select options — crashes loudly
  at startup on any misconfigured *_id/integer column or unrecognized
  lookup source
- panel.py: GET /panel/{entity}/{id} (and .../new) renders the full
  detail panel body per entity, replacing the old hardcoded per-entity
  template
- detail-panel.js: fetch-and-swap wholesale into .detail-panel instead
  of populating a fixed field-name list — same code works for any
  entity; fixed twice — first pass missed the tab bar, second pass
  covers the whole panel body
- deps.py: extracted get_user_id/require_name/get_detail_or_404/
  delete_via_proc, eliminating duplication across contacts/
  organizations/projects routes; collapsed _fetch_records' search/
  no-search branches
- Identities tab: added a ⋯ detail button (matches the Projects grid
  pattern), since dblclick-to-open wasn't reliably firing
- pylint 10.00/10, pytest 40 passing throughout

Known gaps, not addressed here: no save path for contact/organization
association, no email/phone/URL entry for contacts, panel.py has no
unit tests, Tasks not started.
```
