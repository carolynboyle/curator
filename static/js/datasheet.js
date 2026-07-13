/**
 * datasheet.js
 *
 * Generic Tabulator child-datasheet engine for Curator.
 * Called by _datasheet.html's <script type="module"> block on every
 * panel tab that includes a child datasheet (Tasks, Emails, Phones,
 * URLs, Contacts, etc.).
 *
 * Usage (from _datasheet.html's generated module script):
 *
 *   import { initDatasheet } from '/static/js/datasheet.js';
 *
 *   initDatasheet({
 *     containerId:  'tasks-datasheet',
 *     entity:       'tasks',
 *     queryName:    'for_project',
 *     queryParams:  '12',
 *     columns:      [...],
 *     parentField:  'project_id',   // explicit FK — never guessed
 *   });
 *
 * Save/delete routes live under /crew/{entity}/... (see
 * CHANGEDOC_DATASHEET_URL_AND_SUCCESS_FLAG_FIX.md). Save success is
 * read from body.success !== false (not HTTP status — the API returns
 * failures as HTTP 200 with a success:false envelope). Delete success
 * is a bare HTTP 204; failure is HTTP 200 with a success:false envelope.
 *
 * Known gap: + Add button wiring is deferred to the Tasks UI wiring
 * changedoc (see nested_master_detail_design.md) — Add for Tasks opens
 * the nested detail form, not an inline Tabulator row.
 */

export function initDatasheet(config) {
    const {
        containerId,
        entity,
        queryName,
        queryParams,
        columns,
        parentField,  // explicit parent FK field name — required for INSERT
                      // to include the correct parent id in the payload.
                      // Pass '' or omit if this datasheet has no parent FK.
    } = config;

    const container = document.getElementById(containerId);
    if (!container) return;

    const ajaxUrl = `/api/query/${entity}/${queryName}?params=${queryParams}`;

    // -------------------------------------------------------------------------
    // Save a row to the server
    //
    // Error response contract (see projects.py save_new_project /
    // save_project): success = flat record at HTTP 200; failure =
    // {"success": false, "message": "...", "data": ...} ALSO at HTTP 200.
    // This means resp.ok is true in both cases — the only reliable success
    // check is body.success !== false. Matches detail-panel.js's saveForm();
    // keep both in sync if this contract ever changes.
    // -------------------------------------------------------------------------
    async function saveRow(row) {
        const data = row.getData();
        const isNew = !data.id;

        // Don't save a new row with no content — just delete it
        const firstEditable = columns.find(c => c.editor);
        if (isNew && firstEditable && !data[firstEditable.field]) {
            row.delete();
            return true;
        }

        const url = isNew
            ? `/crew/${entity}/save`
            : `/crew/${entity}/${data.id}/save`;

        // Only send editable columns
        const editableFields = columns
            .filter(c => c.editor && c.field !== 'id')
            .map(c => c.field);

        const payload = {};
        editableFields.forEach(f => { payload[f] = data[f] ?? null; });

        // For new rows, include the parent FK with its explicit field name.
        // parentField replaces the old string-guessing heuristic that produced
        // task_id instead of project_id for the Tasks entity.
        if (isNew && parentField && queryParams) {
            payload[parentField] = queryParams;
        }

        let body;
        try {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            body = await resp.json();
        } catch (err) {
            alert('Save error: ' + err.message);
            return false;
        }

        if (body.success === false) {
            alert(body.message || 'Save failed');
            return false;
        }

        row.update(body);
        return true;
    }

    // -------------------------------------------------------------------------
    // Delete a row from the server
    //
    // Error response contract (see projects.py delete_project): success =
    // bare HTTP 204, no body; failure = {"success": false, "message": "..."}
    // at HTTP 200. Unlike save, there's no body to check on success (204
    // has none) — so delete's check is on status code, not body.success.
    // -------------------------------------------------------------------------
    async function deleteRow(row) {
        const id = row.getData().id;
        if (!id) { row.delete(); return; }

        if (!confirm('Delete this row?')) return;

        let resp;
        try {
            resp = await fetch(`/crew/${entity}/${id}`, { method: 'DELETE' });
        } catch (err) {
            alert('Delete error: ' + err.message);
            return;
        }

        if (resp.status === 204) {
            row.delete();
            return;
        }

        const body = await resp.json().catch(() => ({ message: resp.statusText }));
        alert(body.message || 'Delete failed');
    }

    // -------------------------------------------------------------------------
    // Tabulator init — uses global Tabulator loaded by base.html via CDN
    // -------------------------------------------------------------------------
    const table = new Tabulator(container, {  // eslint-disable-line no-undef
        height: '100%',
        layout: 'fitColumns',
        ajaxURL: ajaxUrl,
        ajaxConfig: { headers: { 'Accept': 'application/json' } },
        ajaxResponse: (url, params, response) => response.records || [],
        editTriggerEvent: 'dblclick',
        columns: columns,

        cellEdited: async function(cell) {
            await saveRow(cell.getRow());
        },

        rowContextMenu: [
            {
                label: 'Delete row',
                action: (e, row) => deleteRow(row),
            }
        ],

        dataLoadError: (error) => {
            console.error(`Failed to load ${entity}/${queryName}:`, error);
        },
    });

    // Escape — delete empty new row, or cancel edit
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const newRow = table.getRows().find(r => !r.getData().id);
            if (newRow) newRow.delete();
        }
    });

    // Store reference on window for parent access (e.g. refresh after save)
    window[`tabulator_${containerId}`] = table;
    window[`refresh_${containerId}`]   = () => table.setData(ajaxUrl);
}
