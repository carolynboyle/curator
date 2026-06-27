# Datasheet Implementation

**Goal**: Replace the pencil/two-row HTMX edit pattern with a click-to-edit
datasheet grid. Generic JS engine handles all tables; dialog confirms saves.

---

## Files Created

| File | Location |
|------|----------|
| `datasheet.js` | `static/js/datasheet.js` |
| `datasheet.css` | `static/css/components/datasheet.css` |

Copy both from downloads to those paths.

---

## Files Modified

### 1. `static/css/components/forms.css`

Remove everything EXCEPT the icon column, detail icon, and add icon styles.
The edit/add input styles move to `datasheet.css`.

### BEFORE

```css
/* ============================================================
   forms.css — Crew table edit/add form component styles
   No color declarations — role colors live in crew CSS files
   ============================================================ */

/* Icon column */
table.crew-table .icon-col {
    width: 3.5rem;
    text-align: left;
    white-space: nowrap;
}

/* Pencil and detail icons — hidden until row hover */
table.crew-table .edit-icon,
table.crew-table .detail-icon {
    visibility: hidden;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.25rem 0.3rem;
    font-size: 1rem;
    color: currentColor;
}

table.crew-table tr:hover .edit-icon,
table.crew-table tr:hover .detail-icon {
    visibility: visible;
}

/* Touch devices: always show icons (no hover available) */
@media (hover: none) {
    table.crew-table .edit-icon,
    table.crew-table .detail-icon {
        visibility: visible;
    }
}

/* Add icon in header */
table.crew-table th .add-icon {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.1rem;
    font-weight: bold;
    padding: 0 0.3rem 0 0;
    color: currentColor;
    opacity: 0.6;
    vertical-align: middle;
}

table.crew-table th .add-icon:hover {
    opacity: 1;
}

/* Edit / add form fields */
tr.crew-row-edit fieldset.edit-fields,
tr.crew-row-add fieldset.edit-fields {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
    margin: 0.5rem 0;
    border: none;
    padding: 0;
}

tr.crew-row-edit .edit-input,
tr.crew-row-edit .edit-select,
tr.crew-row-add .edit-input,
tr.crew-row-add .edit-select {
    padding: 0.5rem;
    border: 1px solid var(--border-color, #ccc);
    border-radius: 0.25rem;
    font-size: 0.95rem;
    font-family: inherit;
    width: 100%;
    box-sizing: border-box;
}

/* Controls row */
tr.crew-row-edit-controls .edit-controls {
    display: flex;
    gap: 0.5rem;
    padding: 0.5rem 0;
    align-items: center;
}

/* Save and Cancel buttons */
.btn-save,
.btn-cancel {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color, #ccc);
    border-radius: 0.25rem;
    background: white;
    color: #111 !important;
    cursor: pointer;
    font-size: 0.95rem;
    transition: all 200ms ease;
}

.btn-save:hover {
    background: #e6f2ff;
    border-color: #0066cc;
}

.btn-cancel:hover {
    background: #f5f5f5;
    border-color: #666;
}

/* Inline error message on add */
.add-error {
    color: #9b1c1c;
    font-size: 0.9rem;
    margin-left: 0.5rem;
}

/* Responsive: stack fields on small screens */
@media (max-width: 640px) {
    .btn-save,
    .btn-cancel {
        flex: 1;
        text-align: center;
    }
}
```

### AFTER

```css
/* ============================================================
   forms.css — Icon and add button styles
   Edit/add field styles moved to datasheet.css
   ============================================================ */

/* Icon column */
table.crew-table .icon-col {
    width: 3rem;
    text-align: left;
    white-space: nowrap;
}

/* Add icon in header */
table.crew-table th .add-icon {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.1rem;
    font-weight: bold;
    padding: 0 0.3rem 0 0;
    color: currentColor;
    opacity: 0.6;
    vertical-align: middle;
}

table.crew-table th .add-icon:hover {
    opacity: 1;
}
```

---

### 2. `src/curator/templates/_projects_table.html`

Add `data-datasheet` and `data-role` to the table, `data-field` and
`data-type` to editable `<th>` elements, remove the HTMX `hx-get` from
the `+` button (JS handles add now).

### BEFORE

```html
<div class="crew-content">
    <input
        type="search"
        name="search"
        placeholder="Search projects..."
        value="{{ search }}"
        hx-get="/crew"
        hx-trigger="keyup changed delay:300ms"
        hx-target="#crew-rows"
        hx-include="[name='search']"
        hx-vals='{"role": "{{ role }}"}'
    >

    <table class="crew-table">
        <thead>
            <tr>
                <th class="icon-col"></th>
                <th>
                    <button
                        class="add-icon"
                        hx-get="/crew/projects/new?role={{ role }}"
                        hx-target="#crew-rows"
                        hx-swap="afterbegin"
                        title="Add project"
                    >+</button>
                    Name
                </th>
                <th>Type</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody id="crew-rows">
            {% include "_crew_rows.html" %}
        </tbody>
    </table>
</div>
```

### AFTER

```html
<div class="crew-content">
    <input
        type="search"
        name="search"
        placeholder="Search projects..."
        value="{{ search }}"
        hx-get="/crew"
        hx-trigger="keyup changed delay:300ms"
        hx-target="#crew-rows"
        hx-include="[name='search']"
        hx-vals='{"role": "{{ role }}"}'
    >

    <table class="crew-table" data-datasheet data-role="{{ role }}">
        <thead>
            <tr>
                <th class="icon-col"></th>
                <th data-field="name" data-type="text">
                    <button
                        class="add-icon"
                        title="Add project"
                    >+</button>
                    Name
                </th>
                <th data-field="type_id" data-type="select">Type</th>
                <th data-field="status_id" data-type="select">Status</th>
            </tr>
        </thead>
        <tbody id="crew-rows">
            {% include "_crew_rows.html" %}
        </tbody>
    </table>
</div>
```

### What Changed
- Added `data-datasheet` and `data-role` to `<table>`
- Added `data-field` and `data-type` to editable `<th>` elements
- Removed `hx-get`, `hx-target`, `hx-swap` from `+` button (JS handles it now)

---

### 3. `src/curator/templates/_crew_row_display.html`

Replace entire file. Removes pencil button, adds `data-` attributes for
datasheet engine, keeps `⋯` detail button.

### BEFORE

```html
<tr class="crew-row-display" data-project-id="{{ record.id }}">
    <td class="icon-col">
        <button
            class="edit-icon"
            hx-get="/crew/projects/{{ record.id }}/edit-form"
            hx-target="closest tr"
            hx-swap="outerHTML"
            title="Edit project"
        >✏️</button>
        <button
            class="detail-icon"
            title="Project details"
            disabled
        >⋯</button>
    </td>
    <td>{{ record["name"] }}</td>
    <td>{{ record["type"] or "—" }}</td>
    <td>{{ record["status"] }}</td>
</tr>
```

### AFTER

```html
<tr class="crew-row-display"
    data-id="{{ record.id }}"
    data-name="{{ record.name }}"
    data-type-id="{{ record.type_id or '' }}"
    data-status-id="{{ record.status_id or '' }}">
    <td class="icon-col">
        <button
            class="detail-icon"
            title="Project details"
            disabled
        >⋯</button>
    </td>
    <td data-field="name">{{ record["name"] }}</td>
    <td data-field="type_id" data-value="{{ record['type_id'] or '' }}">{{ record["type"] or "—" }}</td>
    <td data-field="status_id" data-value="{{ record['status_id'] or '' }}">{{ record["status"] or "—" }}</td>
</tr>
```

### What Changed
- `data-project-id` → `data-id` (generic, works for any entity)
- Removed pencil button and all HTMX attributes
- Added `data-field` to each editable `<td>`
- Added `data-value` to select cells (stores ID, display text stays as label)
- `⋯` button stays, still disabled

---

### 4. `src/curator/templates/base.html`

Add `datasheet.css` link and `datasheet.js` script tag.

### BEFORE (relevant lines)

```html
    <link rel="stylesheet" href="/static/css/components/tabs.css">

    <!-- Theme -->
```

```html
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
</body>
```

### AFTER

```html
    <link rel="stylesheet" href="/static/css/components/tabs.css">
    <link rel="stylesheet" href="/static/css/components/datasheet.css">

    <!-- Theme -->
```

```html
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
    <!-- Datasheet engine -->
    <script src="/static/js/datasheet.js" defer></script>
</body>
```

---

### 5. `src/curator/templates/base.html` — Add dialog

Add the `<dialog>` element just inside `<body>`, before `<nav>`.

### BEFORE

```html
<body>
    <nav class="navbar">
```

### AFTER

```html
<body>

    <!-- Save/Discard confirmation dialog — used by datasheet.js -->
    <dialog id="datasheet-dialog">
        <div class="ds-dialog-inner">
            <p class="ds-dialog-title">Unsaved Changes</p>
            <p class="ds-dialog-message">Save changes to this row before continuing?</p>
            <div class="ds-dialog-actions">
                <button class="ds-dialog-discard">Discard</button>
                <button class="ds-dialog-save">Save</button>
            </div>
        </div>
    </dialog>

    <nav class="navbar">
```

---

### 6. `src/curator/web/routes/crew.py`

Replace HTMX edit/add routes with JSON endpoints.
Remove: GET edit-form, POST new, POST new/save, POST new/cancel, POST save, POST cancel
Add: POST save (JSON), POST new save (JSON)

### BEFORE (lines to remove — entire blocks)

```python
@router.get("/crew/projects/new", response_class=HTMLResponse)
async def add_project_form(...):
    ...

@router.post("/crew/projects/new/save", response_class=HTMLResponse)
async def save_new_project(...):
    ...

@router.post("/crew/projects/new/cancel", response_class=HTMLResponse)
async def cancel_new_project():
    ...

@router.get("/crew/projects/{project_id}/edit-form", response_class=HTMLResponse)
async def edit_project_form(...):
    ...

@router.post("/crew/projects/{project_id}/save", response_class=HTMLResponse)
async def save_project(...):
    ...

@router.post("/crew/projects/{project_id}/cancel", response_class=HTMLResponse)
async def cancel_edit(...):
    ...
```

### AFTER (replace all six with these two)

```python
@router.post("/crew/projects/save", response_class=HTMLResponse)
async def save_new_project(
    role: str = Query("captain"),
    db: AsyncDBConnection = Depends(get_db),
    request: Request = None,
):
    """Insert a new project from datasheet add row.

    Accepts JSON body: {name, type_id, status_id}
    Returns display row HTML.
    """
    body = await request.json()
    name = body.get("name", "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None

    if not name:
        return HTMLResponse("Name is required", status_code=422)

    slug = _make_slug(name)

    existing = await db.fetch_one(
        "SELECT id FROM projects.projects WHERE slug = %s", (slug,)
    )
    if existing:
        return HTMLResponse(
            f'A project named "{name}" already exists.',
            status_code=409
        )

    result = await db.fetch_one(
        """
        INSERT INTO projects.projects (name, slug, type_id, status_id)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (name, slug, type_id, status_id)
    )
    new_id = result["id"]
    record = await _fetch_project_for_display(db, new_id)
    if not record:
        raise HTTPException(status_code=500, detail="Insert succeeded but fetch failed")

    template = env.get_template("_crew_row_display.html")
    return HTMLResponse(template.render(record=record))


@router.post("/crew/projects/{project_id}/save", response_class=HTMLResponse)
async def save_project(
    project_id: int,
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    """Save project edits from datasheet row.

    Accepts JSON body: {name, type_id, status_id}
    Returns updated display row HTML.
    """
    body = await request.json()
    name = body.get("name", "").strip()
    type_id = body.get("type_id") or None
    status_id = body.get("status_id") or None

    if not name:
        return HTMLResponse("Name is required", status_code=422)

    await db.execute(
        """
        UPDATE projects.projects
        SET name = %s, type_id = %s, status_id = %s
        WHERE id = %s
        """,
        (name, type_id, status_id, project_id)
    )

    record = await _fetch_project_for_display(db, project_id)
    if not record:
        raise HTTPException(status_code=500, detail="Save succeeded but fetch failed")

    template = env.get_template("_crew_row_display.html")
    return HTMLResponse(template.render(record=record))
```

### What Changed
- Removed 6 HTMX routes (edit-form, new, new/save, new/cancel, save, cancel)
- Added 2 JSON routes (new save, update save)
- Both accept `request.json()` body instead of `Form()` params
- Both return `_crew_row_display.html` partial — datasheet JS swaps it in
- Removed `_collapse_edit_row()` helper (no longer needed)
- `_fetch_lookups()`, `_fetch_role_types()`, `_fetch_project_by_id()` helpers
  can also be removed from crew.py (no longer called)

---

## Files to Delete

These are no longer needed:

- `src/curator/templates/_crew_row_edit.html`
- `src/curator/templates/_crew_row_add.html`

---

## Testing Checklist

- [ ] Page loads, projects show as plain text rows (no pencil icon)
- [ ] Click Name cell → row highlights, name becomes text input
- [ ] Click Type cell → row highlights, type becomes dropdown (pre-selected)
- [ ] Click Status cell → row highlights, status becomes dropdown (pre-selected)
- [ ] Click different row while clean → first row exits silently, new row enters edit
- [ ] Edit a value, click different row → dialog appears
- [ ] Dialog: Discard → changes lost, other row enters edit mode
- [ ] Dialog: Save → POST fires, row updates, other row enters edit mode
- [ ] Escape on clean row → nothing
- [ ] Escape on dirty row → dialog
- [ ] Click + → new empty row at top, name field focused
- [ ] Fill new row, click different row → dialog
- [ ] Dialog: Save on new row → POST to /crew/projects/save, row appears
- [ ] Dialog: Discard on new row → row removed
- [ ] Search still works (HTMX, new rows get handlers via htmx:afterSwap)
- [ ] ⋯ button visible on hover, still disabled
- [ ] Works on Captain tab and other role pages
