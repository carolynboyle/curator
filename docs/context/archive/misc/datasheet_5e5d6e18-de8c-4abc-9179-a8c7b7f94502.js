/**
 * datasheet.js — Generic inline-edit datasheet engine for Curator
 *
 * Behaviour:
 *   - Click any editable cell → row enters edit mode
 *   - All exits from a dirty row → Save/Discard dialog
 *   - Clean row exits → silent, no dialog
 *   - One row in edit mode at a time
 *   - Tab moves between editable cells within the row
 *   - Escape → dialog (if dirty)
 *   - ⋯ detail button is ignored by edit machinery
 *
 * Column definitions are read from data attributes on <th> elements:
 *   data-field="name"      — field name, matched to td[data-field]
 *   data-type="text"       — input type: text | select
 *
 * Row data is read from data attributes on <tr> elements:
 *   data-id="123"          — record ID, used in save URL
 *
 * Cell display vs stored value:
 *   For select cells, td[data-value] holds the ID, text content is the label.
 *   For text cells, text content is both display and value.
 *
 * Save endpoint:
 *   POST /crew/projects/{id}/save  (JSON body)
 *   Response: updated <tr> HTML to swap in
 *
 * Add endpoint:
 *   POST /crew/projects/save  (JSON body, no ID)
 *   Response: new <tr> HTML to prepend
 */

(function () {
    'use strict';

    // -------------------------------------------------------------------------
    // State
    // -------------------------------------------------------------------------

    let activeRow = null;       // the <tr> currently in edit mode
    let originalValues = null;  // snapshot of values before editing
    let isDirty = false;        // has anything changed?
    let pendingAction = null;   // action to run after dialog resolves

    // -------------------------------------------------------------------------
    // Dialog
    // -------------------------------------------------------------------------

    function getDialog() {
        return document.getElementById('datasheet-dialog');
    }

    function showDialog(onSave, onDiscard) {
        pendingAction = { onSave, onDiscard };
        getDialog().showModal();
    }

    function initDialog() {
        const dialog = document.getElementById('datasheet-dialog');
        if (!dialog) return;

        dialog.querySelector('.ds-dialog-save').addEventListener('click', () => {
            dialog.close();
            if (pendingAction) pendingAction.onSave();
            pendingAction = null;
        });

        dialog.querySelector('.ds-dialog-discard').addEventListener('click', () => {
            dialog.close();
            if (pendingAction) pendingAction.onDiscard();
            pendingAction = null;
        });

        // Click backdrop to dismiss = discard
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog) {
                dialog.close();
                if (pendingAction) pendingAction.onDiscard();
                pendingAction = null;
            }
        });
    }

    // -------------------------------------------------------------------------
    // Column definitions — read from <th data-field data-type>
    // -------------------------------------------------------------------------

    function getColumns(table) {
        const cols = [];
        table.querySelectorAll('thead th[data-field]').forEach(th => {
            cols.push({
                field: th.dataset.field,
                type: th.dataset.type || 'text',
            });
        });
        return cols;
    }

    // -------------------------------------------------------------------------
    // Lookup data — read from window.projectTypes / window.projectStatuses
    // Keyed by field name for generic access
    // -------------------------------------------------------------------------

    function getOptions(field) {
        if (field === 'type_id')   return window.projectTypes   || [];
        if (field === 'status_id') return window.projectStatuses || [];
        return [];
    }

    // -------------------------------------------------------------------------
    // Snapshot — capture current cell values before editing
    // -------------------------------------------------------------------------

    function snapshot(row, cols) {
        const values = {};
        cols.forEach(col => {
            const td = row.querySelector(`td[data-field="${col.field}"]`);
            if (!td) return;
            values[col.field] = col.type === 'select'
                ? (td.dataset.value || '')
                : td.textContent.trim();
        });
        return values;
    }

    // -------------------------------------------------------------------------
    // Dirty check — compare current inputs to snapshot
    // -------------------------------------------------------------------------

    function checkDirty(row, cols) {
        if (!originalValues) return false;
        return cols.some(col => {
            const input = row.querySelector(`[data-field="${col.field}"] input, [data-field="${col.field}"] select`);
            if (!input) return false;
            return String(input.value) !== String(originalValues[col.field] || '');
        });
    }

    // -------------------------------------------------------------------------
    // Enter edit mode — replace cell text with inputs
    // -------------------------------------------------------------------------

    function enterEditMode(row, cols, focusField) {
        if (activeRow === row) return;

        row.classList.add('ds-editing');
        originalValues = snapshot(row, cols);
        isDirty = false;

        cols.forEach(col => {
            const td = row.querySelector(`td[data-field="${col.field}"]`);
            if (!td) return;

            const currentValue = originalValues[col.field];
            const displayText = td.textContent.trim();

            if (col.type === 'select') {
                const options = getOptions(col.field);
                const sel = document.createElement('select');
                sel.className = 'ds-select';
                sel.dataset.field = col.field;

                // Blank option
                const blank = document.createElement('option');
                blank.value = '';
                blank.textContent = '— select —';
                sel.appendChild(blank);

                options.forEach(opt => {
                    const o = document.createElement('option');
                    o.value = opt.id;
                    o.textContent = opt.name;
                    if (String(opt.id) === String(currentValue)) o.selected = true;
                    sel.appendChild(o);
                });

                sel.addEventListener('change', () => { isDirty = checkDirty(row, cols); });
                td.dataset.originalText = displayText;
                td.textContent = '';
                td.appendChild(sel);

            } else {
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'ds-input';
                input.dataset.field = col.field;
                input.value = currentValue === '—' ? '' : currentValue;

                input.addEventListener('input', () => { isDirty = checkDirty(row, cols); });
                td.dataset.originalText = displayText;
                td.textContent = '';
                td.appendChild(input);
            }
        });

        activeRow = row;

        // Focus the clicked field or first editable field
        const focusTarget = focusField
            ? row.querySelector(`td[data-field="${focusField}"] input, td[data-field="${focusField}"] select`)
            : row.querySelector('.ds-input, .ds-select');
        if (focusTarget) focusTarget.focus();
    }

    // -------------------------------------------------------------------------
    // Exit edit mode — restore cell text from saved/discarded values
    // -------------------------------------------------------------------------

    function exitEditMode(row, cols, newValues) {
        cols.forEach(col => {
            const td = row.querySelector(`td[data-field="${col.field}"]`);
            if (!td) return;

            const input = td.querySelector('input, select');
            if (!input) return;

            if (newValues) {
                // Update display from saved values
                if (col.type === 'select') {
                    const options = getOptions(col.field);
                    const match = options.find(o => String(o.id) === String(newValues[col.field]));
                    td.textContent = match ? match.name : '—';
                    td.dataset.value = newValues[col.field] || '';
                } else {
                    td.textContent = newValues[col.field] || '—';
                }
            } else {
                // Restore original display
                td.textContent = td.dataset.originalText || '—';
                if (col.type === 'select') {
                    td.dataset.value = originalValues[col.field] || '';
                }
            }
        });

        row.classList.remove('ds-editing');
        activeRow = null;
        originalValues = null;
        isDirty = false;
    }

    // -------------------------------------------------------------------------
    // Save row — POST to server, update display from response
    // -------------------------------------------------------------------------

    async function saveRow(row, cols, table) {
        const id = row.dataset.id;
        const isNew = row.dataset.new === 'true';
        const role = table.dataset.role || '';

        const body = {};
        cols.forEach(col => {
            const input = row.querySelector(`td[data-field="${col.field}"] input, td[data-field="${col.field}"] select`);
            if (input) body[col.field] = input.value;
        });

        const url = isNew
            ? `/crew/projects/save?role=${role}`
            : `/crew/projects/${id}/save`;

        try {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            if (!resp.ok) {
                const err = await resp.text();
                showError(row, err);
                return false;
            }

            // Server returns updated row HTML
            const html = await resp.text();
            const tmp = document.createElement('tbody');
            tmp.innerHTML = html;
            const newRow = tmp.querySelector('tr');

            if (newRow) {
                // Re-attach click handlers before swapping in
                attachRowHandlers(newRow, cols, table);
                row.replaceWith(newRow);
            }

            activeRow = null;
            originalValues = null;
            isDirty = false;
            return true;

        } catch (err) {
            console.error('Save failed:', err);
            return false;
        }
    }

    // -------------------------------------------------------------------------
    // Add new row — insert empty editable row at top of tbody
    // -------------------------------------------------------------------------

    function insertNewRow(table, cols) {
        const tbody = table.querySelector('tbody');
        const role = table.dataset.role || '';

        const row = document.createElement('tr');
        row.classList.add('ds-editing', 'ds-new');
        row.dataset.new = 'true';
        row.dataset.id = '';

        // Icon column
        const iconTd = document.createElement('td');
        iconTd.className = 'icon-col';
        const detailBtn = document.createElement('button');
        detailBtn.className = 'detail-icon';
        detailBtn.textContent = '⋯';
        detailBtn.disabled = true;
        iconTd.appendChild(detailBtn);
        row.appendChild(iconTd);

        // Editable cells
        cols.forEach(col => {
            const td = document.createElement('td');
            td.dataset.field = col.field;

            if (col.type === 'select') {
                const options = getOptions(col.field);
                const sel = document.createElement('select');
                sel.className = 'ds-select';
                sel.dataset.field = col.field;

                const blank = document.createElement('option');
                blank.value = '';
                blank.textContent = '— select —';
                sel.appendChild(blank);

                options.forEach(opt => {
                    const o = document.createElement('option');
                    o.value = opt.id;
                    o.textContent = opt.name;
                    sel.appendChild(o);
                });

                sel.addEventListener('change', () => { isDirty = true; });
                td.appendChild(sel);
            } else {
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'ds-input';
                input.dataset.field = col.field;
                input.placeholder = col.field === 'name' ? 'Project name' : '';
                input.addEventListener('input', () => { isDirty = true; });
                td.appendChild(input);
            }

            row.appendChild(td);
        });

        tbody.insertBefore(row, tbody.firstChild);
        activeRow = row;
        originalValues = {};
        isDirty = false;

        // Focus first input
        const first = row.querySelector('.ds-input, .ds-select');
        if (first) first.focus();
    }

    // -------------------------------------------------------------------------
    // Error display
    // -------------------------------------------------------------------------

    function showError(row, message) {
        let err = row.querySelector('.ds-error');
        if (!err) {
            err = document.createElement('span');
            err.className = 'ds-error';
            const firstTd = row.querySelector('td:not(.icon-col)');
            if (firstTd) firstTd.appendChild(err);
        }
        err.textContent = message;
    }

    // -------------------------------------------------------------------------
    // Tab handling within a row
    // -------------------------------------------------------------------------

    function handleTab(e, row) {
        if (e.key !== 'Tab') return;
        const inputs = [...row.querySelectorAll('.ds-input, .ds-select')];
        if (!inputs.length) return;

        const current = document.activeElement;
        const idx = inputs.indexOf(current);

        if (!e.shiftKey && idx === inputs.length - 1) {
            e.preventDefault(); // Tab on last field — stay in row
        } else if (e.shiftKey && idx === 0) {
            e.preventDefault(); // Shift-Tab on first field — stay in row
        }
    }

    // -------------------------------------------------------------------------
    // Attempt to leave active row — dirty check gate
    // -------------------------------------------------------------------------

    function attemptLeave(cols, table, onProceed) {
        if (!activeRow) {
            onProceed();
            return;
        }

        isDirty = checkDirty(activeRow, cols);

        if (!isDirty) {
            // New unsaved row — just remove it cleanly
            if (activeRow.dataset.new === 'true') {
                activeRow.remove();
                activeRow = null;
                originalValues = null;
            } else {
                exitEditMode(activeRow, cols, null);
            }
            onProceed();
            return;
        }

        // Dirty — show dialog
        showDialog(
            // Save
            async () => {
                const saved = await saveRow(activeRow, cols, table);
                if (saved) onProceed();
            },
            // Discard
            () => {
                if (activeRow) {
                    if (activeRow.dataset.new === 'true') {
                        activeRow.remove();
                    } else {
                        exitEditMode(activeRow, cols, null);
                    }
                    activeRow = null;
                    originalValues = null;
                    isDirty = false;
                }
                onProceed();
            }
        );
    }

    // -------------------------------------------------------------------------
    // Attach handlers to a single display row
    // -------------------------------------------------------------------------

    function attachRowHandlers(row, cols, table) {
        // Click any editable cell
        cols.forEach(col => {
            const td = row.querySelector(`td[data-field="${col.field}"]`);
            if (!td) return;

            td.style.cursor = 'text';
            td.addEventListener('click', () => {
                if (activeRow === row) return; // already editing this row

                attemptLeave(cols, table, () => {
                    enterEditMode(row, cols, col.field);
                });
            });
        });

        // Keyboard handlers while row is active
        row.addEventListener('keydown', (e) => {
            if (activeRow !== row) return;

            handleTab(e, row);

            if (e.key === 'Escape') {
                isDirty = checkDirty(row, cols);
                attemptLeave(cols, table, () => {});
            }
        });
    }

    // -------------------------------------------------------------------------
    // Init a single datasheet table
    // -------------------------------------------------------------------------

    function initTable(table) {
        const cols = getColumns(table);
        if (!cols.length) return;

        // Attach handlers to existing display rows
        table.querySelectorAll('tbody tr:not(.ds-editing)').forEach(row => {
            if (row.dataset.id) attachRowHandlers(row, cols, table);
        });

        // + button
        const addBtn = table.querySelector('.add-icon');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                attemptLeave(cols, table, () => {
                    insertNewRow(table, cols);
                });
            });
        }

        // Click outside table — dirty check
        document.addEventListener('click', (e) => {
            if (!activeRow) return;
            if (table.contains(e.target)) return;
            if (getDialog().contains(e.target)) return;

            isDirty = checkDirty(activeRow, cols);
            attemptLeave(cols, table, () => {});
        });
    }

    // -------------------------------------------------------------------------
    // Public init — call on DOMContentLoaded
    // -------------------------------------------------------------------------

    function init() {
        initDialog();
        document.querySelectorAll('table.crew-table[data-datasheet]').forEach(initTable);
    }

    document.addEventListener('DOMContentLoaded', init);

    // Re-init after HTMX swaps (search results replace tbody)
    document.addEventListener('htmx:afterSwap', (e) => {
        const table = e.target.closest('table.crew-table[data-datasheet]');
        if (!table) return;
        const cols = getColumns(table);
        table.querySelectorAll('tbody tr').forEach(row => {
            if (row.dataset.id && !row._dsAttached) {
                attachRowHandlers(row, cols, table);
                row._dsAttached = true;
            }
        });
    });

})();
