# Datasheet — All Fixes

**Date:** 2026-06-26  
**Apply in this order. Browser reload only — no uvicorn restart needed except for step 1.**

---

## Files changed

| # | File | What changes |
|---|------|-------------|
| 1 | `templates/base.html` | Remove Pico, add baseline.css |
| 2 | `static/css/components/baseline.css` | NEW FILE — minimal element resets |
| 3 | `static/css/components/tabulator-overrides.css` | Replace entire file |
| 4 | `templates/_projects_table.html` | Replace entire file |

---

## 1. `templates/base.html`

**WHY:** Remove Pico CSS entirely. It styles native HTML elements globally and
was fighting Tabulator's internal divs. Replace with a minimal baseline.css
that only resets what we actually need.

**BEFORE:**
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

**WHY:** Replaces the handful of useful things Pico was doing (box-sizing,
font resets, button/input normalization) with nothing extra. No classless
global styling, no framework opinions.

**Create this file at `static/css/components/baseline.css`:**
```css
/* =============================================================================
   baseline.css — Minimal element resets
   Replaces Pico CSS. Only resets what we actually need.
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

button {
    font-family: inherit;
    font-size: inherit;
    cursor: pointer;
    border: none;
    background: none;
    padding: 0;
    margin: 0;
}

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

ul, ol {
    margin: 0;
    padding: 0;
    list-style: none;
}

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

## 3. `static/css/components/tabulator-overrides.css` — REPLACE ENTIRE FILE

**WHY:** 
- All CSS variable references replaced with hardcoded light values so the
  datasheet always looks light regardless of the app theme
- Row height fixed: `!important` needed because Tabulator's simple theme sets
  min-height inline on row elements, which beats external CSS without it
- Checkbox column and right-pinned `⋯` column styles added
- Row selected highlight (blue) added

**REPLACE THE ENTIRE FILE WITH:**
```css
/* ============================================================
   tabulator-overrides.css — Compact pgAdmin-style datasheet
   Loaded AFTER tabulator_simple.min.css to win specificity.
   
   All colors are hardcoded light values — the datasheet is
   always light regardless of the app theme (dark.css, etc).
   ============================================================ */

/* ---- Grid container ----------------------------------------------- */

.tabulator {
    border: 1px solid #dde1e7;
    font-size: 0.875rem;
    background: #ffffff;
    color: #1a1a1a;
}

/* ---- Header row ---------------------------------------------------- */

.tabulator .tabulator-header {
    border-bottom: 2px solid #dde1e7;
    background: #f3f4f6;
    color: #374151;
    font-weight: 600;
}

.tabulator .tabulator-header .tabulator-col {
    background: #f3f4f6;
    border-right: 1px solid #dde1e7;
}

.tabulator .tabulator-header .tabulator-col .tabulator-col-content {
    padding: 4px 8px;
}

/* ---- Data rows — compact ------------------------------------------ */

.tabulator .tabulator-row {
    min-height: 0 !important;
    max-height: 26px !important;
    border-bottom: 1px solid #e5e7eb;
}

.tabulator .tabulator-row .tabulator-cell {
    padding: 3px 8px;
    border-right: 1px solid #e5e7eb;
    height: 26px;
    line-height: 20px;
    overflow: hidden;
}

.tabulator .tabulator-row:hover {
    background: #f0faf9;
}

/* Alternating row stripes — pgAdmin style */
.tabulator .tabulator-row.tabulator-row-even {
    background: #ffffff;
}

.tabulator .tabulator-row.tabulator-row-odd {
    background: #fafafa;
}

/* ---- Row selected (checkbox selection) ---------------------------- */

.tabulator .tabulator-row.row-selected,
.tabulator .tabulator-row.row-selected:hover {
    background: #dbeafe !important;
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
    border: 1px solid #dde1e7;
    border-radius: 0;
    font-size: 0.85rem;
    font-family: inherit;
    height: auto;
    box-shadow: none;
    background: #ffffff;
    color: #1a1a1a;
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
    background: #ffffff;
    color: #1a1a1a;
    outline: 2px solid #0f766e;
    outline-offset: -2px;
}

/* ---- Editing cell highlight --------------------------------------- */

.tabulator .tabulator-cell.tabulator-editing {
    border: none;
    padding: 0;
}

/* ---- Checkbox column (left) --------------------------------------- */

.tabulator .tabulator-col.col-select,
.tabulator .tabulator-cell.col-select {
    padding: 0;
    text-align: center;
    border-right: 2px solid #dde1e7;
}

.tabulator .col-select input[type="checkbox"] {
    margin: 0;
    cursor: pointer;
    width: 14px;
    height: 14px;
    accent-color: #0f766e;
}

/* ---- Detail icon column (right) ----------------------------------- */

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
    color: #6b7280;
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
    color: #0f766e;
    opacity: 0.7;
}

.tabulator .add-icon:hover {
    opacity: 1;
}
```

---

## 4. `templates/_projects_table.html` — REPLACE ENTIRE FILE

**WHY:**
- Checkbox column on left, `⋯` column on right
- Double-click to edit cells (single-click is for row selection)
- Row selection with blue highlight
- Clipboard copy via Ctrl+C with HTTP fallback (works on localhost,
  Tailscale HTTP, and future HTTPS without any code changes)

**REPLACE THE ENTIRE FILE WITH:**
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
    // Row selection
    // -------------------------------------------------------------------------
    let selectedRows = new Set();

    function setRowSelected(row, selected) {
        const el = row.getElement();
        if (selected) {
            selectedRows.add(row);
            el.classList.add('row-selected');
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

    // -------------------------------------------------------------------------
    // Clipboard copy — tries modern API first, falls back to execCommand.
    // Works on HTTP, HTTPS, and localhost with no permission dialog.
    // -------------------------------------------------------------------------
    function copySelectionToClipboard() {
        if (selectedRows.size === 0) return;
        const lines = [];
        table.getRows().forEach(row => {
            if (!selectedRows.has(row)) return;
            const d = row.getData();
            const name   = d.name                    || '';
            const type   = typeValues[d.type_id]     || '';
            const status = statusValues[d.status_id] || '';
            lines.push([name, type, status].join('\t'));
        });
        const text = lines.join('\n');

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).catch(() => _execCommandCopy(text));
        } else {
            _execCommandCopy(text);
        }
    }

    function _execCommandCopy(text) {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.top = '-9999px';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); } catch (err) { /* nothing we can do */ }
        document.body.removeChild(ta);
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
            async () => { const saved = await saveRow(dirtyRow); if (saved) onProceed(); },
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
        ajaxConfig: { headers: { 'Accept': 'application/json' } },
        filterMode: 'remote',
        ajaxResponse: function(url, params, response) {
            return response.records || response;
        },
        layout: 'fitColumns',
        height: 'auto',
        placeholder: 'No projects found.',
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

        rowClick: function(e, row) {
            if (e.target.classList.contains('row-checkbox')) return;
            if (e.target.classList.contains('detail-icon')) return;
            if (dirtyRow && dirtyRow !== row) {
                attemptLeave(dirtyRow, () => {});
                return;
            }
            if (selectedRows.has(row)) {
                setRowSelected(row, false);
            } else {
                setRowSelected(row, true);
            }
        },

        columns: [
            // Checkbox column (left)
            {
                field: 'select',
                title: '<input type="checkbox" id="select-all-checkbox" title="Select all">',
                width: 32,
                minWidth: 32,
                resizable: false,
                headerSort: false,
                cssClass: 'col-select',
                headerClick: function() {
                    const allCb = document.getElementById('select-all-checkbox');
                    if (allCb && allCb.checked) {
                        clearSelection();
                    } else {
                        table.getRows().forEach(r => setRowSelected(r, true));
                        copySelectionToClipboard();
                    }
                },
                formatter: function() {
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

            // Name column
            {
                field: 'name',
                title: 'Name',
                editor: 'input',
                headerFilter: 'input',
                headerFilterPlaceholder: 'Search projects...',
                headerFilterLiveFilter: true,
                headerFilterFunc: 'like',
                titleFormatter: function() {
                    const btn = document.createElement('button');
                    btn.className = 'add-icon';
                    btn.title = 'Add project';
                    btn.textContent = '+';
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const addRow = () => table.addRow(
                            { id: null, name: '', type_id: null, status_id: null }, true
                        );
                        if (dirtyRow) { attemptLeave(dirtyRow, addRow); } else { addRow(); }
                    });
                    return btn.outerHTML + ' Name';
                },
                widthGrow: 3,
            },

            // Type column
            {
                field: 'type_id',
                title: 'Type',
                editor: 'list',
                editorParams: { values: typeValues, clearable: true },
                formatter: function(cell) {
                    const val = cell.getValue();
                    return val ? (typeValues[val] || '—') : '—';
                },
                widthGrow: 1,
            },

            // Status column
            {
                field: 'status_id',
                title: 'Status',
                editor: 'list',
                editorParams: { values: statusValues, clearable: true },
                formatter: function(cell) {
                    const val = cell.getValue();
                    return val ? (statusValues[val] || '—') : '—';
                },
                widthGrow: 1,
            },

            // Detail icon column (right)
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
                    // Future: open detail panel for cell.getRow().getData().id
                },
            },
        ],
    });

    // Ctrl+C — copy selected rows
    // Escape — clear selection or discard dirty row
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'c' && selectedRows.size > 0) {
            e.preventDefault();
            copySelectionToClipboard();
        }
        if (e.key === 'Escape') {
            if (selectedRows.size > 0) {
                clearSelection();
            } else if (dirtyRow) {
                e.preventDefault();
                attemptLeave(dirtyRow, () => {});
            }
        }
    });

    // Click outside grid — dirty check + clear selection
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

## Behavior after all fixes applied

| Action | Result |
|--------|--------|
| Page background | Light grey (`#f5f7fa`) regardless of theme setting |
| Grid background | Always white with light grey header |
| Row height | 26px compact — pgAdmin style |
| Single-click row | Selects / deselects (blue highlight) |
| Ctrl+C with rows selected | Copies tab-separated values to clipboard |
| Double-click a data cell | Opens cell for editing |
| Escape while editing | Save/Discard dialog if dirty |
| Click `⋯` (right column) | Future: opens detail form |
| Dark theme | Page goes dark, grid stays light |
