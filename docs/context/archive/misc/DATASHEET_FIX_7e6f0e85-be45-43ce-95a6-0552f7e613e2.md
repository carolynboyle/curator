# Datasheet Fix — Remove Pico, Fix Layout, Add Row Selection

**Date:** 2026-06-26  
**Goal:** Remove Pico CSS entirely, fix the black-background layout problem,
add checkbox row selection with clipboard copy, pin `⋯` to the right.

**Files changed:**
1. `templates/base.html` — remove Pico, add baseline.css
2. `static/css/components/baseline.css` — NEW: minimal replacement for what Pico provided
3. `static/css/components/tabulator-overrides.css` — add checkbox + row-selected styles
4. `templates/_projects_table.html` — add checkbox column left, `⋯` column right, double-click to edit

---

## 1. `templates/base.html`

**WHY:** Pico CSS is a classless framework that styles every native HTML element
globally. It was fighting Tabulator's internal `<div>` structure and making the
search input oversized. Removing it and replacing with a 30-line baseline gives
us full control.

**BEFORE** (lines 7–11):
```html
    <!-- Pico CSS (base layer) -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.classless.min.css">

    <!-- Curator base styles -->
    <link rel="stylesheet" href="/static/css/base.css">
    <link rel="stylesheet" href="/static/css/layout.css">
```

**AFTER:**
```html
    <!-- Curator base styles -->
    <link rel="stylesheet" href="/static/css/base.css">
    <link rel="stylesheet" href="/static/css/layout.css">
    <link rel="stylesheet" href="/static/css/components/baseline.css">
```

---

## 2. `static/css/components/baseline.css` — NEW FILE

**WHY:** Pico was providing sensible defaults for `box-sizing`, `font-family`,
`button` resets, and `input` resets. This file replaces exactly those defaults
with nothing extra.

**Create this file:**
```css
/* =============================================================================
   baseline.css — Minimal element resets
   Replaces Pico CSS. Styles only what Pico was providing that we actually need.
   No classless global styling. No framework opinions.
   ============================================================================= */

*, *::before, *::after {
    box-sizing: border-box;
}

html {
    font-size: 16px;
    -webkit-text-size-adjust: 100%;
}

body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    font-size: 0.9rem;
    line-height: 1.5;
}

/* Remove default button styles so our .btn-* classes start clean */
button {
    font-family: inherit;
    font-size: inherit;
    cursor: pointer;
    border: none;
    background: none;
    padding: 0;
    margin: 0;
}

/* Remove default input/select styling so Tabulator and our forms start clean */
input, select, textarea {
    font-family: inherit;
    font-size: inherit;
    border: 1px solid var(--color-border, #dde1e7);
    border-radius: 3px;
    padding: 0.35rem 0.5rem;
    background: var(--color-surface, #fff);
    color: var(--color-text, #1a1a1a);
}

input:focus, select:focus, textarea:focus {
    outline: 2px solid var(--color-primary, #0f766e);
    outline-offset: -1px;
    border-color: var(--color-primary, #0f766e);
}

/* Remove list styling */
ul, ol {
    margin: 0;
    padding: 0;
    list-style: none;
}

/* Remove heading margins */
h1, h2, h3, h4, h5, h6 {
    margin: 0 0 0.5rem 0;
    line-height: 1.2;
    font-weight: 600;
}

p {
    margin: 0 0 0.75rem 0;
}

a {
    color: var(--color-primary, #0f766e);
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}
```

---

## 3. `static/css/components/tabulator-overrides.css`

**WHY:** Add styles for the checkbox column (row selection) and the
row-selected highlight. Also add the right-pinned `⋯` column styles.
The existing compact grid styles are unchanged.

**BEFORE** (the entire file):
```css
/* ============================================================
   tabulator-overrides.css — Compact pgAdmin-style datasheet
   Loaded AFTER tabulator_simple.min.css to win specificity.
   Targets Tabulator's real DOM classes (divs, not <table>).
   ============================================================ */

/* ---- Grid container ----------------------------------------------- */

.tabulator {
    border: 1px solid var(--color-border, #d1d5db);
    font-size: 0.875rem;
    background: var(--color-surface, #fff);
}

/* ---- Header row ---------------------------------------------------- */

.tabulator .tabulator-header {
    border-bottom: 2px solid var(--color-border, #d1d5db);
    background: var(--color-lighter, #f3f4f6);
    font-weight: 600;
}

.tabulator .tabulator-header .tabulator-col {
    background: var(--color-lighter, #f3f4f6);
    border-right: 1px solid var(--color-border, #d1d5db);
}

.tabulator .tabulator-header .tabulator-col .tabulator-col-content {
    padding: 4px 8px;
}

/* ---- Data rows — compact ------------------------------------------ */

.tabulator .tabulator-row {
    min-height: 26px;
    border-bottom: 1px solid var(--color-light, #e5e7eb);
}

.tabulator .tabulator-row .tabulator-cell {
    padding: 3px 8px;
    border-right: 1px solid var(--color-light, #e5e7eb);
    height: 26px;
    line-height: 20px;
}

.tabulator .tabulator-row:hover {
    background: var(--color-lighter, #f3f4f6);
}

/* Alternating row stripes — pgAdmin style */
.tabulator .tabulator-row.tabulator-row-even {
    background: var(--color-surface, #fff);
}

.tabulator .tabulator-row.tabulator-row-odd {
    background: #fafafa;
}

/* ---- Header filter (search box) — flatten Pico's styling ---------- */

.tabulator .tabulator-header-filter input,
.tabulator .tabulator-header-filter select {
    width: 100%;
    padding: 2px 6px;
    margin: 0;
    border: 1px solid var(--color-border, #d1d5db);
    border-radius: 0;
    font-size: 0.85rem;
    font-family: inherit;
    height: auto;
    box-shadow: none;
    background: var(--color-surface, #fff);
}

/* ---- Cell editors — flat, flush with cell ------------------------- */

.tabulator .tabulator-cell .tabulator-cell-editing input,
.tabulator .tabulator-cell .tabulator-cell-editing select,
.tabulator .tabulator-cell input,
.tabulator .tabulator-cell select {
    border: none;
    border-radius: 0;
    padding: 2px 6px;
    margin: 0;
    font-size: 0.85rem;
    font-family: inherit;
    height: auto;
    box-shadow: none;
    background: var(--color-surface, #fff);
    outline: 2px solid var(--color-primary, #0f766e);
    outline-offset: -2px;
}

/* ---- Editing cell highlight --------------------------------------- */

.tabulator .tabulator-cell.tabulator-editing {
    border: none;
    padding: 0;
}

/* ---- Detail / add icon buttons ------------------------------------ */

.tabulator .detail-icon {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0 0.2rem;
    font-size: 1rem;
    color: currentColor;
    opacity: 0.5;
}

.tabulator .detail-icon:hover:not(:disabled) {
    opacity: 1;
}

.tabulator .add-icon {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.1rem;
    font-weight: bold;
    padding: 0 0.3rem 0 0;
    color: currentColor;
    opacity: 0.6;
}

.tabulator .add-icon:hover {
    opacity: 1;
}
```

**AFTER** (replace entire file):
```css
/* ============================================================
   tabulator-overrides.css — Compact pgAdmin-style datasheet
   Loaded AFTER tabulator_simple.min.css to win specificity.
   Targets Tabulator's real DOM classes (divs, not <table>).
   ============================================================ */

/* ---- Grid container ----------------------------------------------- */

.tabulator {
    border: 1px solid var(--color-border, #dde1e7);
    font-size: 0.875rem;
    background: var(--color-surface, #fff);
}

/* ---- Header row ---------------------------------------------------- */

.tabulator .tabulator-header {
    border-bottom: 2px solid var(--color-border, #dde1e7);
    background: #f3f4f6;
    font-weight: 600;
}

.tabulator .tabulator-header .tabulator-col {
    background: #f3f4f6;
    border-right: 1px solid var(--color-border, #dde1e7);
}

.tabulator .tabulator-header .tabulator-col .tabulator-col-content {
    padding: 4px 8px;
}

/* ---- Data rows — compact ------------------------------------------ */

.tabulator .tabulator-row {
    min-height: 26px;
    border-bottom: 1px solid #e5e7eb;
}

.tabulator .tabulator-row .tabulator-cell {
    padding: 3px 8px;
    border-right: 1px solid #e5e7eb;
    height: 26px;
    line-height: 20px;
}

.tabulator .tabulator-row:hover {
    background: #f0faf9;
}

/* Alternating row stripes — pgAdmin style */
.tabulator .tabulator-row.tabulator-row-even {
    background: var(--color-surface, #fff);
}

.tabulator .tabulator-row.tabulator-row-odd {
    background: #fafafa;
}

/* ---- Row selected (checkbox selection) ---------------------------- */

.tabulator .tabulator-row.row-selected,
.tabulator .tabulator-row.row-selected:hover {
    background: #dbeafe !important;  /* light blue, Excel/pgAdmin style */
}

.tabulator .tabulator-row.row-selected .tabulator-cell {
    color: #1e3a5f;
}

/* ---- Header filter (search box) ----------------------------------- */

.tabulator .tabulator-header-filter input,
.tabulator .tabulator-header-filter select {
    width: 100%;
    padding: 2px 6px;
    margin: 0;
    border: 1px solid var(--color-border, #dde1e7);
    border-radius: 0;
    font-size: 0.85rem;
    font-family: inherit;
    height: auto;
    box-shadow: none;
    background: var(--color-surface, #fff);
    color: var(--color-text, #1a1a1a);
}

/* ---- Cell editors — flat, flush with cell ------------------------- */

.tabulator .tabulator-cell.tabulator-editing input,
.tabulator .tabulator-cell.tabulator-editing select {
    border: none;
    border-radius: 0;
    padding: 2px 6px;
    margin: 0;
    font-size: 0.85rem;
    font-family: inherit;
    width: 100%;
    box-shadow: none;
    background: var(--color-surface, #fff);
    color: var(--color-text, #1a1a1a);
    outline: 2px solid var(--color-primary, #0f766e);
    outline-offset: -2px;
}

/* ---- Editing cell highlight --------------------------------------- */

.tabulator .tabulator-cell.tabulator-editing {
    border: none;
    padding: 0;
}

/* ---- Checkbox column ---------------------------------------------- */

.tabulator .tabulator-col.col-select,
.tabulator .tabulator-cell.col-select {
    padding: 0;
    text-align: center;
    border-right: 2px solid var(--color-border, #dde1e7);
}

.tabulator .col-select input[type="checkbox"] {
    margin: 0;
    cursor: pointer;
    width: 14px;
    height: 14px;
    accent-color: var(--color-primary, #0f766e);
}

/* ---- Detail icon column (right-pinned) ---------------------------- */

.tabulator .tabulator-cell.col-detail {
    text-align: center;
    padding: 0;
    border-left: 1px solid #e5e7eb;
    border-right: none;
}

.tabulator .detail-icon {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0 0.2rem;
    font-size: 1rem;
    color: currentColor;
    opacity: 0.3;
}

.tabulator .detail-icon:hover:not(:disabled) {
    opacity: 1;
}

/* ---- Add button in Name header ------------------------------------ */

.tabulator .add-icon {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.1rem;
    font-weight: bold;
    padding: 0 0.3rem 0 0;
    color: currentColor;
    opacity: 0.6;
}

.tabulator .add-icon:hover {
    opacity: 1;
}
```

---

## 4. `templates/_projects_table.html`

**WHY:** Restructure Tabulator column definitions to put checkbox on the left,
`⋯` on the right, and switch from single-click editing to double-click editing
(so single-click can be used for row selection). Add clipboard copy logic.

**BEFORE** (entire file):
```html
<div class="crew-content">
    <div id="projects-grid"></div>
</div>

<script>
window.addEventListener('load', function () {
    // -------------------------------------------------------------------------
    // Dirty row tracking
    // -------------------------------------------------------------------------
    let dirtyRow = null;        // Tabulator row component currently being edited
    let originalValues = {};    // snapshot before edits
    let pendingAction = null;   // callback to run after dialog resolves

    function snapshot(row) {
        const d = row.getData();
        return { name: d.name, type_id: d.type_id, status_id: d.status_id };
    }

    function isDirty(row) {
        if (!dirtyRow) return false;
        const d = row.getData();
        return (
            String(d.name      || '') !== String(originalValues.name      || '') ||
            String(d.type_id   || '') !== String(originalValues.type_id   || '') ||
            String(d.status_id || '') !== String(originalValues.status_id || '')
        );
    }

    // -------------------------------------------------------------------------
    // Save/Discard dialog
    // -------------------------------------------------------------------------
    const dialog = document.getElementById('datasheet-dialog');

    dialog.querySelector('.ds-dialog-save').addEventListener('click', () => {
        dialog.close();
        if (pendingAction) { pendingAction.onSave(); pendingAction = null; }
    });

    dialog.querySelector('.ds-dialog-discard').addEventListener('click', () => {
        dialog.close();
        if (pendingAction) { pendingAction.onDiscard(); pendingAction = null; }
    });

    dialog.addEventListener('click', (e) => {
        if (e.target === dialog) {
            dialog.close();
            if (pendingAction) { pendingAction.onDiscard(); pendingAction = null; }
        }
    });

    function showDialog(onSave, onDiscard) {
        pendingAction = { onSave, onDiscard };
        dialog.showModal();
    }

    // -------------------------------------------------------------------------
    // Save a row to the server
    // -------------------------------------------------------------------------
    async function saveRow(row) {
        const data = row.getData();
        const isNew = !data.id;
        const url = isNew
            ? `/crew/projects/save?role={{ role }}`
            : `/crew/projects/${data.id}/save`;

        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name:      data.name,
                type_id:   data.type_id   || null,
                status_id: data.status_id || null,
            }),
        });

        if (!resp.ok) {
            const msg = await resp.text();
            alert(msg); // simple error for now
            return false;
        }

        // Server returns updated row HTML — extract data attrs for Tabulator
        const html = await resp.text();
        const tmp = document.createElement('tbody');
        tmp.innerHTML = html;
        const tr = tmp.querySelector('tr');
        if (tr && isNew) {
            // Update the row id from the server response
            const newId = tr.dataset.id;
            if (newId) row.update({ id: parseInt(newId) });
        }

        dirtyRow = null;
        originalValues = {};
        return true;
    }

    // -------------------------------------------------------------------------
    // Attempt to leave a dirty row — gate all row changes through this
    // -------------------------------------------------------------------------
    function attemptLeave(row, onProceed) {
        if (!dirtyRow || !isDirty(row)) {
            if (dirtyRow) {
                // Clean — restore original values silently
                dirtyRow.update(originalValues);
            }
            dirtyRow = null;
            originalValues = {};
            onProceed();
            return;
        }

        showDialog(
            async () => {
                const saved = await saveRow(dirtyRow);
                if (saved) onProceed();
            },
            () => {
                if (dirtyRow) dirtyRow.update(originalValues);
                dirtyRow = null;
                originalValues = {};
                onProceed();
            }
        );
    }

    // -------------------------------------------------------------------------
    // Build lookup maps for select editors
    // -------------------------------------------------------------------------
    const typeValues = (window.projectTypes || []).reduce((acc, t) => {
        acc[t.id] = t.name; return acc;
    }, {});

    const statusValues = (window.projectStatuses || []).reduce((acc, s) => {
        acc[s.id] = s.name; return acc;
    }, {});

    // -------------------------------------------------------------------------
    // Tabulator init
    // -------------------------------------------------------------------------
    const table = new Tabulator('#projects-grid', {
        ajaxURL: '/crew',
        ajaxParams: { role: '{{ role }}' },
        ajaxConfig: {
            headers: { 'Accept': 'application/json' },
        },
        filterMode: 'remote',
        ajaxResponse: function(url, params, response) {
            // Server returns {records: [...]}
            return response.records || response;
        },
        layout: 'fitColumns',
        height: 'auto',
        placeholder: 'No projects found.',

        // Dirty row tracking — snapshot on cell edit start
        cellEditing: function(cell) {
            const row = cell.getRow();
            if (dirtyRow && dirtyRow !== row) {
                // Switching rows — gate through dirty check
                cell.cancelEdit();
                attemptLeave(dirtyRow, () => {
                    dirtyRow = row;
                    originalValues = snapshot(row);
                    // Re-trigger edit on the cell
                    setTimeout(() => cell.edit(), 50);
                });
                return;
            }
            if (!dirtyRow) {
                dirtyRow = row;
                originalValues = snapshot(row);
            }
        },

        // On edit complete — mark row dirty (Tabulator already updated its data)
        cellEdited: function(cell) {
            // Nothing extra needed — isDirty() compares live data to snapshot
        },

        columns: [
            {
                field: 'detail',
                title: '',
                width: 50,
                resizable: false,
                headerSort: false,
                frozen: true,
                formatter: function() {
                    return '<button class="detail-icon" disabled title="Project details">⋯</button>';
                },
            },
            {
                field: 'name',
                title: '+ Name',
                editor: 'input',
                headerFilter: 'input',
                headerFilterPlaceholder: 'Search projects...',
                headerFilterLiveFilter: true,
                headerFilterFunc: 'like',
                titleFormatter: function(cell) {
                    const btn = document.createElement('button');
                    btn.className = 'add-icon';
                    btn.title = 'Add project';
                    btn.textContent = '+';
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const addRow = () => {
                            table.addRow({
                                id: null,
                                name: '',
                                type_id: null,
                                status_id: null,
                                type: '',
                                status: '',
                            }, true); // true = add to top
                        };
                        if (dirtyRow) {
                            attemptLeave(dirtyRow, addRow);
                        } else {
                            addRow();
                        }
                    });
                    return btn.outerHTML + ' Name';
                },
                widthGrow: 3,
            },
            {
                field: 'type_id',
                title: 'Type',
                editor: 'list',
                editorParams: {
                    values: typeValues,
                    clearable: true,
                },
                formatter: function(cell) {
                    const val = cell.getValue();
                    return val ? (typeValues[val] || '—') : '—';
                },
                widthGrow: 1,
            },
            {
                field: 'status_id',
                title: 'Status',
                editor: 'list',
                editorParams: {
                    values: statusValues,
                    clearable: true,
                },
                formatter: function(cell) {
                    const val = cell.getValue();
                    return val ? (statusValues[val] || '—') : '—';
                },
                widthGrow: 1,
            },
        ],

        // Row click outside cells — dirty check
        rowClick: function(e, row) {
            if (dirtyRow && dirtyRow !== row) {
                attemptLeave(dirtyRow, () => {});
            }
        },
    });

    // Click outside table — dirty check
    document.addEventListener('click', (e) => {
        if (!dirtyRow) return;
        if (document.getElementById('projects-grid').contains(e.target)) return;
        if (dialog.contains(e.target)) return;
        attemptLeave(dirtyRow, () => {});
    });

    // Escape key — dirty check
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && dirtyRow) {
            e.preventDefault();
            attemptLeave(dirtyRow, () => {});
        }
    });

});
</script>
```

**AFTER** (replace entire file):
```html
<div class="crew-content">
    <div id="projects-grid"></div>
</div>

<script>
window.addEventListener('load', function () {

    // -------------------------------------------------------------------------
    // Dirty row tracking
    // -------------------------------------------------------------------------
    let dirtyRow = null;
    let originalValues = {};
    let pendingAction = null;

    function snapshot(row) {
        const d = row.getData();
        return { name: d.name, type_id: d.type_id, status_id: d.status_id };
    }

    function isDirty(row) {
        if (!dirtyRow) return false;
        const d = row.getData();
        return (
            String(d.name      || '') !== String(originalValues.name      || '') ||
            String(d.type_id   || '') !== String(originalValues.type_id   || '') ||
            String(d.status_id || '') !== String(originalValues.status_id || '')
        );
    }

    // -------------------------------------------------------------------------
    // Row selection tracking
    // -------------------------------------------------------------------------
    let selectedRows = new Set();   // Set of Tabulator row components
    let allSelected = false;

    function setRowSelected(row, selected) {
        const el = row.getElement();
        if (selected) {
            selectedRows.add(row);
            el.classList.add('row-selected');
            // Check the row checkbox
            const cb = el.querySelector('.row-checkbox');
            if (cb) cb.checked = true;
        } else {
            selectedRows.delete(row);
            el.classList.remove('row-selected');
            const cb = el.querySelector('.row-checkbox');
            if (cb) cb.checked = false;
        }
        updateSelectAllCheckbox();
    }

    function updateSelectAllCheckbox() {
        const allCb = document.getElementById('select-all-checkbox');
        if (!allCb) return;
        const rows = table.getRows();
        const allChecked = rows.length > 0 && rows.every(r => selectedRows.has(r));
        allCb.checked = allChecked;
        allCb.indeterminate = !allChecked && selectedRows.size > 0;
    }

    function clearSelection() {
        selectedRows.forEach(row => {
            const el = row.getElement();
            el.classList.remove('row-selected');
            const cb = el.querySelector('.row-checkbox');
            if (cb) cb.checked = false;
        });
        selectedRows.clear();
        updateSelectAllCheckbox();
    }

    // Copy selected rows to clipboard as tab-separated values
    function copySelectionToClipboard() {
        if (selectedRows.size === 0) return;
        const lines = [];
        // Use table row order, not Set insertion order
        table.getRows().forEach(row => {
            if (!selectedRows.has(row)) return;
            const d = row.getData();
            const name      = d.name      || '';
            const type      = typeValues[d.type_id]   || '';
            const status    = statusValues[d.status_id] || '';
            lines.push([name, type, status].join('\t'));
        });
        navigator.clipboard.writeText(lines.join('\n')).catch(() => {
            // Clipboard API unavailable (non-HTTPS) — silently ignore
        });
    }

    // -------------------------------------------------------------------------
    // Save/Discard dialog
    // -------------------------------------------------------------------------
    const dialog = document.getElementById('datasheet-dialog');

    dialog.querySelector('.ds-dialog-save').addEventListener('click', () => {
        dialog.close();
        if (pendingAction) { pendingAction.onSave(); pendingAction = null; }
    });

    dialog.querySelector('.ds-dialog-discard').addEventListener('click', () => {
        dialog.close();
        if (pendingAction) { pendingAction.onDiscard(); pendingAction = null; }
    });

    dialog.addEventListener('click', (e) => {
        if (e.target === dialog) {
            dialog.close();
            if (pendingAction) { pendingAction.onDiscard(); pendingAction = null; }
        }
    });

    function showDialog(onSave, onDiscard) {
        pendingAction = { onSave, onDiscard };
        dialog.showModal();
    }

    // -------------------------------------------------------------------------
    // Save a row to the server
    // -------------------------------------------------------------------------
    async function saveRow(row) {
        const data = row.getData();
        const isNew = !data.id;
        const url = isNew
            ? `/crew/projects/save?role={{ role }}`
            : `/crew/projects/${data.id}/save`;

        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name:      data.name,
                type_id:   data.type_id   || null,
                status_id: data.status_id || null,
            }),
        });

        if (!resp.ok) {
            const msg = await resp.text();
            alert(msg);
            return false;
        }

        const html = await resp.text();
        const tmp = document.createElement('tbody');
        tmp.innerHTML = html;
        const tr = tmp.querySelector('tr');
        if (tr && isNew) {
            const newId = tr.dataset.id;
            if (newId) row.update({ id: parseInt(newId) });
        }

        dirtyRow = null;
        originalValues = {};
        return true;
    }

    // -------------------------------------------------------------------------
    // Attempt to leave a dirty row
    // -------------------------------------------------------------------------
    function attemptLeave(row, onProceed) {
        if (!dirtyRow || !isDirty(row)) {
            if (dirtyRow) dirtyRow.update(originalValues);
            dirtyRow = null;
            originalValues = {};
            onProceed();
            return;
        }

        showDialog(
            async () => {
                const saved = await saveRow(dirtyRow);
                if (saved) onProceed();
            },
            () => {
                if (dirtyRow) dirtyRow.update(originalValues);
                dirtyRow = null;
                originalValues = {};
                onProceed();
            }
        );
    }

    // -------------------------------------------------------------------------
    // Lookup maps
    // -------------------------------------------------------------------------
    const typeValues = (window.projectTypes || []).reduce((acc, t) => {
        acc[t.id] = t.name; return acc;
    }, {});

    const statusValues = (window.projectStatuses || []).reduce((acc, s) => {
        acc[s.id] = s.name; return acc;
    }, {});

    // -------------------------------------------------------------------------
    // Tabulator init
    // -------------------------------------------------------------------------
    const table = new Tabulator('#projects-grid', {
        ajaxURL: '/crew',
        ajaxParams: { role: '{{ role }}' },
        ajaxConfig: {
            headers: { 'Accept': 'application/json' },
        },
        filterMode: 'remote',
        ajaxResponse: function(url, params, response) {
            return response.records || response;
        },
        layout: 'fitColumns',
        height: 'auto',
        placeholder: 'No projects found.',

        // Double-click to edit — single-click is used for row selection
        editTriggerEvent: 'dblclick',

        cellEditing: function(cell) {
            const row = cell.getRow();
            if (dirtyRow && dirtyRow !== row) {
                cell.cancelEdit();
                attemptLeave(dirtyRow, () => {
                    dirtyRow = row;
                    originalValues = snapshot(row);
                    setTimeout(() => cell.edit(), 50);
                });
                return;
            }
            if (!dirtyRow) {
                dirtyRow = row;
                originalValues = snapshot(row);
            }
        },

        cellEdited: function(cell) {
            // isDirty() compares live data to snapshot — nothing extra needed
        },

        rowClick: function(e, row) {
            // Ignore clicks on the checkbox cell itself (handled by its own listener)
            if (e.target.classList.contains('row-checkbox')) return;
            // Ignore clicks on the detail icon
            if (e.target.classList.contains('detail-icon')) return;

            // Dirty check when switching rows
            if (dirtyRow && dirtyRow !== row) {
                attemptLeave(dirtyRow, () => {});
                return;
            }

            // Toggle row selection on single click
            if (selectedRows.has(row)) {
                setRowSelected(row, false);
            } else {
                setRowSelected(row, true);
            }
        },

        columns: [
            // -- Checkbox column (left) ---------------------------------------
            {
                field: 'select',
                title: '<input type="checkbox" id="select-all-checkbox" title="Select all">',
                width: 32,
                minWidth: 32,
                resizable: false,
                headerSort: false,
                cssClass: 'col-select',
                headerClick: function(e) {
                    const allCb = document.getElementById('select-all-checkbox');
                    const rows = table.getRows();
                    if (allCb && allCb.checked) {
                        // Was checked — deselect all
                        clearSelection();
                        allSelected = false;
                    } else {
                        // Select all
                        rows.forEach(r => setRowSelected(r, true));
                        allSelected = true;
                        copySelectionToClipboard();
                    }
                },
                formatter: function(cell) {
                    return '<input type="checkbox" class="row-checkbox" title="Select row">';
                },
                cellClick: function(e, cell) {
                    e.stopPropagation();
                    const row = cell.getRow();
                    if (selectedRows.has(row)) {
                        setRowSelected(row, false);
                    } else {
                        setRowSelected(row, true);
                    }
                },
            },

            // -- Name column --------------------------------------------------
            {
                field: 'name',
                title: 'Name',
                editor: 'input',
                headerFilter: 'input',
                headerFilterPlaceholder: 'Search projects...',
                headerFilterLiveFilter: true,
                headerFilterFunc: 'like',
                titleFormatter: function(cell) {
                    const btn = document.createElement('button');
                    btn.className = 'add-icon';
                    btn.title = 'Add project';
                    btn.textContent = '+';
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const addRow = () => {
                            table.addRow({
                                id: null,
                                name: '',
                                type_id: null,
                                status_id: null,
                            }, true);
                        };
                        if (dirtyRow) {
                            attemptLeave(dirtyRow, addRow);
                        } else {
                            addRow();
                        }
                    });
                    return btn.outerHTML + ' Name';
                },
                widthGrow: 3,
            },

            // -- Type column --------------------------------------------------
            {
                field: 'type_id',
                title: 'Type',
                editor: 'list',
                editorParams: {
                    values: typeValues,
                    clearable: true,
                },
                formatter: function(cell) {
                    const val = cell.getValue();
                    return val ? (typeValues[val] || '—') : '—';
                },
                widthGrow: 1,
            },

            // -- Status column ------------------------------------------------
            {
                field: 'status_id',
                title: 'Status',
                editor: 'list',
                editorParams: {
                    values: statusValues,
                    clearable: true,
                },
                formatter: function(cell) {
                    const val = cell.getValue();
                    return val ? (statusValues[val] || '—') : '—';
                },
                widthGrow: 1,
            },

            // -- Detail icon column (right) -----------------------------------
            {
                field: 'detail',
                title: '',
                width: 36,
                minWidth: 36,
                resizable: false,
                headerSort: false,
                cssClass: 'col-detail',
                formatter: function() {
                    return '<button class="detail-icon" title="Project details">⋯</button>';
                },
                cellClick: function(e, cell) {
                    e.stopPropagation();
                    // Detail form — not yet implemented
                    // Will launch a detail panel for cell.getRow().getData().id
                },
            },
        ],
    });

    // Ctrl+C / Cmd+C — copy selected rows
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'c' && selectedRows.size > 0) {
            e.preventDefault();
            copySelectionToClipboard();
        }

        // Escape — clear selection or discard dirty row
        if (e.key === 'Escape') {
            if (selectedRows.size > 0) {
                clearSelection();
            } else if (dirtyRow) {
                e.preventDefault();
                attemptLeave(dirtyRow, () => {});
            }
        }
    });

    // Click outside table — dirty check + clear selection
    document.addEventListener('click', (e) => {
        const grid = document.getElementById('projects-grid');
        if (grid.contains(e.target)) return;
        if (dialog.contains(e.target)) return;

        if (dirtyRow) attemptLeave(dirtyRow, () => {});
        clearSelection();
    });

});
</script>
```

---

## Summary of behavior after this change

| Action | Result |
|--------|--------|
| Single-click a row | Selects / deselects it (blue highlight) |
| Click checkbox | Same as single-click row |
| Click select-all checkbox in header | Selects all rows + copies to clipboard |
| Ctrl+C / Cmd+C with rows selected | Copies tab-separated values to clipboard |
| Escape with rows selected | Clears selection |
| Double-click a data cell | Opens cell for editing |
| Escape while editing | Save/Discard dialog if dirty |
| Click `⋯` (right column) | Future: opens detail form |
| Page background | `--color-bg` from theme (light: `#f5f7fa`, not black) |
| Grid background | White with light grey header |
| Row height | 26px compact (pgAdmin style) |
