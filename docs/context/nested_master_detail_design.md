# Nested Master-Detail Pattern — Design Doc

**Status:** Agreed design, not yet implemented.
**Scope:** Applies to Tasks tab first. Subtasks (recursive nesting) deferred — see "Deferred" below.

---

## Problem

Child datasheet tabs (Tasks, Emails, Phones, etc.) need a way to add and
edit records that have more fields than a Tabulator grid row can
reasonably show inline (e.g. Tasks: description, notes, status, priority,
parent/subtask relationships).

Three approaches were considered:

1. **Inline Tabulator row editing** (`table.addRow({}, true)` + edit in
   place) — tried previously for the top-level Projects grid
   (2026-06-28) and **abandoned**: `cellEdited` does not fire reliably
   for programmatically-added rows under `dblclick` edit-trigger mode.
   Not worth retrying for Tasks; same engine, same failure mode expected.
2. **Pop open a separate full detail panel** (`openNewRecordPanel`/
   `openDetailPanel`, same as Project/Contact/Organization Add today) —
   works, but visually disconnects the task list from the task form; the
   list and the thing being edited are in different UI locations.
3. **Nested master-detail within the same tab** (chosen) — Tabulator
   list on top, a real detail form below it, both inside the same tab
   panel. Selecting or adding a row shows/edits that record in the form
   directly underneath the list it came from.

## Chosen design

Within a child datasheet tab (e.g. the Tasks tab of a Project's detail
panel):

```
┌───────────────────────────────────────────┐
│  PROJECT detail form                       │  ← top-level panel
│  Name / Description / Type / Status        │
│  [Save] [New] [Exit]                       │
├─────────────────────────────────────────────┤
│  Tabs: Details | Tasks | Links | Contacts   │
├─────────────────────────────────────────────┤
│  ┌─ Tasks tab (subform of Project) ───────┐ │
│  │ Project: WCYJ Refurbs   ← context line │ │
│  │                                         │ │
│  │  Tabulator list (Tasks for Project)     │ │
│  │  [+ Add Task]                            │ │
│  │  name | status | priority | ⋯            │ │
│  ├───────────────────────────────────────────┤ │
│  │  Task detail form                        │ │
│  │  Name / Description / Status / ...       │ │
│  │  [Save] [New] [Exit]                     │ │
│  └───────────────────────────────────────────┘ │
└───────────────────────────────────────────────┘
```

The Tasks tab is a **subform of the Project**, not an independent
list-plus-form floating on its own. It needs a visible reminder at the
top of the tab of which project it belongs to — separate from the
hidden `project_id` field that actually powers the save. Two purposes,
two mechanisms:

- **Hidden `project_id` field** — powers the save payload, never
  rendered as an editable control (see "Add flow" below).
- **Project-context line** ("Project: WCYJ Refurbs") — presentational
  only, reminds the person what they're looking at.

**First implementation: static text label**, rendered once when the tab
loads (project name, not a link). A future version could make this a
link/button back to the Project's own Details tab, letting someone jump
back up a level directly — deliberately deferred; try the simple label
first and see whether the need for a jump-back link actually surfaces
in practice before building it.

- **Top:** existing Tabulator child-datasheet engine (`datasheet.js` /
  `initDatasheet()`), unchanged in its own right.
- **Bottom:** **the same generic detail-panel content** already used for
  the top-level Project/Contact/Organization panel —
  `_detail_panel_content.html`, fetched via `/panel/{entity}/{id}` (or
  `/panel/{entity}/new`), rendered by `panel.py`, driven by
  `detail-panel.js`. Not a new form, not a Tasks-specific form. A second
  instance of the exact same machinery, mounted in a different DOM
  container than the top-level one.

This is a direct extension of the existing Metadata-Driven UI + ABAC
architecture: `fieldkit.py` doesn't know or care whether it's
introspecting `v_task_detail`, `v_project_detail`, or (in a future,
different deployment) `v_inventory_item_detail`. Any entity with a
proper SQL layer (`v_*_detail` view, `api.get_*_detail()`,
`api.save_*()`, `api.delete_*()`) gets this same nested master-detail
treatment for free — no new template code, no new JS, no per-entity
form.

### Why this matters beyond Tasks

This is the same principle that keeps the whole app reusable across
different database-backed deployments (the original design goal for
Curator) — and it also solves a smaller, easy-to-miss problem: keeping
different views of the same data looking consistent. Without one
canonical rendering path, it's easy for e.g. a Contacts/Organizations
bulk-datasheet view and the Identities listbox view to visually drift
from each other over time. Reusing the same detail-panel machinery
everywhere makes that consistency the default, not something that has
to be maintained by discipline.

## Per-entity judgment call

Not every child datasheet needs this. The pattern applies when a child
entity has enough fields to warrant a real form (Tasks: yes). Simpler
child entities — a couple of inline-editable columns, nothing worth
opening a separate form for (e.g. possibly Emails, Phones, URLs) — can
stay as plain Tabulator rows with no lower form at all. This is decided
per entity, not architecturally forced one way or the other.

## Behavior details (agreed)

- **Save behavior:** After saving in the lower detail form, the
  Tabulator list above **must refresh** to reflect the change — a save
  that doesn't visibly update the list above it reads as "did that
  actually save?" to the user. Use the existing
  `refresh_{containerId}()` hook already stubbed in `datasheet.js`
  (`window[`refresh_${containerId}`] = () => table.setData(ajaxUrl)`)
  to reload the list after a successful save in the nested form.
- **Selection flow:** Clicking an existing row in the Tabulator list
  fetches and displays that record in the lower form via the same
  fetch-and-swap pattern `detail-panel.js` already uses
  (`/panel/{entity}/{id}`).
- **Add flow:** `+ Add Task` opens the lower form in new-record mode
  (`/panel/{entity}/new`), with the parent FK (`project_id`) pre-filled
  as a hidden field — not user-editable, not guessed, populated from
  context. This depends on the `hidden` field type already planned for
  `fieldkit.py` (see Tasks UI wiring, item 2 in the 2026-07-08 handoff).

## Deferred

**Recursive nesting for Subtasks.** The roadmap already calls for each
Task's own detail panel to have a Subtasks child section. Whether that
means the lower task-detail form itself contains a *second* nested
instance of this same list-plus-form pattern (making it genuinely
recursive, no depth limit) is explicitly deferred. Get the one-level
parent version (Project → Tasks) fully working first; revisit Subtasks
nesting as its own follow-on design pass once that's proven out.

## Relationship to prior architecture decisions

- Builds directly on "Metadata-Driven UI with Dynamic ABAC" — the same
  vocabulary and mechanism already established for the top-level panel.
- Consistent with "one canonical path per concern," already applied
  twice this project (`_detail_panel_content.html` as the only panel
  renderer; `datasheet.js` as the only child-datasheet implementation).
- Does **not** touch `_projects_table.html` (the richer, separate
  Tabulator implementation used for the top-level Projects list). That
  unification question remains its own separate, explicitly deferred
  decision.
