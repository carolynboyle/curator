# List-and-Edit Widget — Design Doc

**Status:** Implemented 2026-11-27 (Documents and Links). Notes on what was built are at the end.
**Goal:** One reusable, config-driven "list on the left, edit form on the
right" widget, used first by the project **Links** tab and by the existing
record **Documents** tab, and later by anything else that needs it (searches'
Records tab, Captain settings).

Logged 2026-11-27. Replaces the "Links list and layout" part of
`docs/roadmap/TODO_PROJECT_FORM_LINKS.md`.

---

## Why

- **Links (project form):** the add form sits open under the fields, the saved
  list is at the bottom of the Details tab, and nothing confirms a save, so one
  link got entered five times. Links can also grow long, and the Details tab
  should not need a scrollbar.
- **Documents (record form):** already solves this well. It is a master-detail
  tab: searchable list on the left, edit form on the right, greyed out until
  something is picked, list refreshed after each save, warning before unsaved
  edits are thrown away.
- The two widgets do the same job with different fields, so the shared part
  should exist once.

## Decisions already made

1. Links moves to **its own "Links" tab** on the project panel (not at the
   bottom of Details).
2. It uses the **Documents layout**: list always visible (even when empty),
   fields on the right.
3. The common code becomes **one generic module** that each tab calls with
   settings. The settings live in **YAML**, not in the JavaScript
   (project_rules: no hard-coded config).

## The generic widget

`static/js/list-edit-widget.js` (name open to change) exports
`initListEditWidget(root, definition, context)`.

It knows nothing about links or documents. It does:

- load the list for the current parent (project or record),
- search-as-you-type over named fields,
- show the list always, with an empty-state message,
- pick an item → fill the form; **New** → blank form; otherwise form greyed out,
- Save (create or update) then **reload the list and keep the saved item
  selected**, so the save is visible,
- Delete with confirmation,
- registers the footer **Save / New** buttons and Alt+S / Alt+N for the active
  tab (the existing `registerFooterHandlers` contract),
- remembers a snapshot of the form so it can warn before discarding edits.

### The definition (what the caller fills in)

| Setting | Meaning | Links example | Documents example |
|---|---|---|---|
| `id` | tab slug | `links` | `documents` |
| `label` | tab label | Links | Documents |
| `list_url` | GET, `{parent_id}` placeholder | `/api/query/project_links/for_project?params={parent_id}` | `/seanchai/records/{parent_id}/documents` |
| `save_new_url` | POST for a new item | `/crew/project_links/save` | `/seanchai/record_documents/save` |
| `save_url` | POST for an existing item, `{id}` | `/crew/project_links/{id}/save` | `/seanchai/record_documents/{id}/save` |
| `delete_url` | DELETE, `{id}` | `/crew/project_links/{id}` | `/seanchai/record_documents/{id}` |
| `parent_key` | field name the server expects for the parent | `project_id` | `record_id` |
| `title_field` | what the list shows as the name | `label` | `label` (fallback "Document N") |
| `search_fields` | what the search box looks through | `label`, `url` | `label`, `source_url`, `md_path` |
| `fields` | the right-hand form: name, label, control, placeholder, required | Label (required), URL | Label, Source URL, Transcription path, Status |
| `open_buttons` | optional "open in new tab" buttons using `open-url.js` | URL | image, transcription |
| `empty_text` | message for an empty list | "No links yet." | "No documents yet." |
| `dirty_message` | "discard changes?" text | … | … |

The server routes stay as they are. Only the browser side changes.

Where the definition lives: a `list_edit_tabs:` block in `curator.yaml`,
keyed by entity (`projects:` → links, `records:` → documents), passed to the
template the same way `search_summary` and `popups` are. Anything that does
not fit YAML (Documents' transcription-link building from the repo base)
is supplied by a small named hook, not copied into the widget.

## What changes, in order

1. **Extract** the shared behaviour out of `record-documents.js` into the generic
   module, with the Documents definition in YAML. Documents must behave
   **identically** afterwards; I check this in a headless browser against the
   current behaviour before touching Links.
2. **Add the Links tab** to the project panel using the same module and a Links
   definition. Remove the old Details-tab Links block and retire
   `project-links.js`'s embedded widget (keep `loadProjectLinks` if the task
   panel still needs it).
3. **Tests:** config shape test (every definition has the required keys), template
   test (tab present for projects with an id, absent for new records), and
   headless-browser checks (list shown when empty, save refreshes list and keeps
   selection, delete, search, discard warning, footer buttons).
4. Docs: update `TODO_PROJECT_FORM_LINKS.md` (done / remaining items).

No database change. No new server routes.

## Edge cases to decide while building

- **Duplicates:** warn (not block) when a new item has the same label and URL as
  an existing one. This is the actual cause of the five Ancestry entries.
- **New project (no id yet):** Links tab shows "Save the project first", as the
  current widget does.
- **Label auto-fill from the page title** (Carolyn's `copy(document.title)`
  workaround): a separate follow-up. The server can fetch a page's title; the
  browser cannot read it from other sites.

## Risks

- Refactoring Documents could break a feature that works today. Mitigation:
  the browser-check script written first, run before and after.
- Links' save routes return a slightly different response than Documents'.
  The widget needs one small adapter for the response shape rather than
  assuming they match.

## Not in scope

Role permissions (Captain work), and moving the widget into the shared
form library. Both wait until it has been proven on two real uses.

---

## As built (2026-11-27)

- `src/curator/list_edit.py` reads and checks the definitions; bad entries are
  skipped with a warning. `options_from` / `repo_base_from` use dotted
  `section.key` names so lists and URLs are not repeated.
- `templates/partials/_list_edit_widget.html` draws the markup from the
  definition; `static/js/list-edit-widget.js` is the engine;
  `static/css/components/list-edit-widget.css` the styles (theme variables only).
- Replaced and deleted: `record-documents.js`, `record-documents.css`,
  `project-links.js` and the old links CSS in `detail-panel.css`.
- A **new** record or project has no list-and-edit tabs at all (the same as
  Documents always did) rather than a "save first" placeholder.
- The Links tab sits after Tasks and Contacts.
- Documents was checked before and after the move with the same 50 browser
  checks (identical results); Links has 41 of its own.
- Not done: sharing code with the dashboard popup's links list (`popup-links.js`).
