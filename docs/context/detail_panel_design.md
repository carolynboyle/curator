# Curator Detail Panel Design

**Date:** 2026-06-26  
**Status:** Decided, not yet implemented  
**Scope:** Defines the detail form pattern used for projects, contacts, and
organizations throughout Curator.

---

## Core Concept

The hero image area at the top of each crew page is repurposed as a detail
panel when a record is selected. The datasheet below remains fully visible
and interactive at all times.

```
┌─────────────────────────────────────────────────────┐
│  DETAIL PANEL (replaces hero image when ... clicked) │
│  ┌──────────────────────────────────────────────────┐│
│  │ [Details] [Tasks] [Links] [Contacts]             ││  <- tabs
│  │                                                  ││
│  │  (tab content — fixed height, scrollable         ││
│  │   datasheets where needed)                       ││
│  │                                                  ││
│  │                              [× Close]           ││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  DATASHEET (always visible, always interactive)      │
│  [ ] + Name          ▲  Type       ▲  Status    ▲ ⋯ │
│      Search...                                       │
│  [ ] Accidental Mystic...    writing    in progress  │
│  [ ] Curator                 coding     active    ⋯  │  <- ⋯ clicked
│  [ ] WCYJ Refurbs            refurb     on hold      │
└─────────────────────────────────────────────────────┘
```

---

## Behavior

### Opening the detail panel
- User clicks `⋯` on any datasheet row
- Hero image fades out / slides up (CSS transition)
- Detail panel fades in at same fixed height
- Selected row gets a subtle highlight in the datasheet
- Datasheet remains fully interactive — user can scroll, search, select rows

### Closing the detail panel
- User clicks `× Close` button in top-right of panel
- Or clicks `⋯` on a different row (switches to that record's detail)
- Or presses Escape
- Detail panel fades out, hero image fades back in
- Row highlight clears

### Dirty state
- If unsaved changes exist in the detail form and user tries to close or
  switch records — same Save/Discard dialog already used by the datasheet

### No page navigation
- Detail panel is entirely client-side
- URL does not change (deep linking to a specific record is a future concern)
- No page load, no loss of datasheet scroll position

---

## Layout — Fixed Height

The detail panel occupies exactly the same vertical space as the hero image.
Content that exceeds this height scrolls within its container — the outer
page never moves.

Hero image height is currently approximately **420px** on desktop.
The detail panel matches this height exactly.

Tab panels within the detail form are `height: 100%` of the available space
below the tab bar, with `overflow-y: auto` so child datasheets scroll.

---

## Tab Structure Per Entity

### Project detail tabs

| Tab | Content |
|-----|---------|
| **Details** | Name (editable), Type (dropdown), Status (dropdown), Target date, Description (textarea), Notes (textarea) |
| **Tasks** | Scrollable child datasheet — task name, assignee, status, due date. Add row at top, inline edit |
| **Links** | Scrollable child datasheet — URL, label, type. Future. |
| **Contacts** | Scrollable child datasheet — linked contacts/orgs for this project. Future. |

### Contact detail tabs

| Tab | Content |
|-----|---------|
| **Details** | Name, Title, Notes |
| **Emails** | Child datasheet — label, address |
| **Phones** | Child datasheet — label, number |
| **URLs** | Child datasheet — type, value |
| **Organizations** | Child datasheet — org name, role |

### Organization detail tabs

| Tab | Content |
|-----|---------|
| **Details** | Name, Notes |
| **Contacts** | Child datasheet — contact name, title, role in org |

---

## Child Datasheets

All child datasheets inside detail panels use the same reusable
`_datasheet.html` partial (to be built before first detail form).

The partial accepts parameters:
- `container_id` — the div ID Tabulator mounts to
- `columns` — column definitions
- `ajax_url` — where to fetch rows
- `save_url` — where to POST saves
- `add_url` — where to POST new rows (optional)

CSS is inherited from `tabulator-overrides.css` — no additional styling
needed per child datasheet. Same compact 26px rows, same light grid colors,
same row selection and clipboard copy behavior.

---

## Implementation Order

1. **`_datasheet.html`** — reusable parameterized partial
2. **Project detail panel** — Details tab + Tasks child datasheet
3. **Contact detail panel** — Details tab + Emails/Phones child datasheets
4. **Org detail panel** — Details tab + Contacts child datasheet
5. **Links/Files tabs** — deferred
6. **Project→Contacts tab** — deferred

---

## CSS Approach

### Hero ↔ Panel transition
```css
.crew-hero {
    transition: opacity 0.2s ease;
}

.crew-hero.hidden {
    display: none;
}

.detail-panel {
    display: none;
    height: 420px;  /* matches hero height */
    overflow: hidden;
}

.detail-panel.active {
    display: flex;
    flex-direction: column;
}
```

Simple show/hide with fade. No complex animation needed.

### Detail panel tab panels
```css
.detail-tab-panel {
    flex: 1;
    overflow-y: auto;  /* scroll within fixed height */
    padding: 0.75rem;
}
```

### Child datasheet height
Child datasheets inside tab panels use `height: 100%` so Tabulator fills
the available space without pushing outside the panel.

---

## Mobile

Mobile layout deferred until all detail forms are working on desktop.
Expected behavior: hero area is already full-width on mobile, detail panel
replaces it in the same space, datasheet stacks below. No special handling
anticipated.

---

## Open Questions (decide before implementation)

1. **URL update on record open?** Currently decided: no. Revisit if deep
   linking becomes useful (e.g. sharing a link to a specific project).

2. **Detail panel for non-Captain roles?** Mechanic sees project details too.
   Same panel pattern, different tabs (no Contacts tab for Mechanic view).

3. **Keyboard navigation?** Arrow keys to move between rows in datasheet while
   detail panel is open? Nice to have, not required for MVP.
