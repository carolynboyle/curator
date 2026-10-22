/**
 * detail-panel.js
 *
 * Handles detail panel interactions:
 * - Opening detail panel for existing records (⋯ button)
 * - Opening detail panel for new records (+ Add button)
 * - Closing panel on × / Alt+X / Escape
 * - Tab switching
 * - Save (Alt+S) — save and close
 * - New  (Alt+N) — save current, clear form, focus Name
 * - Discard (Alt+X) — discard and close
 *
 * Hero image and detail panel occupy the same spot. Opening the panel
 * hides the hero (display:none) and shows the panel (display:flex).
 *
 * Field rendering is fetch-and-swap: opening a record fetches the
 * whole panel body — tab bar, form, everything — from
 * /panel/{entity}/{id} (or /panel/{entity}/new), built by fieldkit from
 * the entity's actual schema, and swaps it into .detail-panel wholesale.
 * There is no client-side knowledge of what fields or tabs any entity
 * has. Adding a new /crew entity requires no JS change; an entity whose
 * routes live elsewhere needs one line in ENTITY_ROUTES.
 */

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function getPanel() {
  return document.querySelector('#detail-panel-container .detail-panel');
}

function getForm() {
  return document.getElementById('detail-form');
}

function getHero() {
  return document.querySelector('.crew-header');
}

function showPanel() {
  const panel = getPanel();
  const hero  = getHero();
  if (panel) panel.classList.add('active');
  if (hero)  hero.classList.add('hidden');
}

function hidePanel() {
  const panel = getPanel();
  const hero  = getHero();
  if (panel) panel.classList.remove('active');
  if (hero)  hero.classList.remove('hidden');
}

function resetToDetailsTab() {
  const panel = getPanel();
  if (!panel) return;
  panel.querySelectorAll('.detail-tab-button').forEach(b => b.classList.remove('active'));
  panel.querySelectorAll('.detail-tab-panel').forEach(p => p.classList.remove('active'));
  const firstBtn   = panel.querySelector('.detail-tab-button');
  const detailsTab = panel.querySelector('.detail-tab-panel[data-tab="details"]');
  if (firstBtn)   firstBtn.classList.add('active');
  if (detailsTab) detailsTab.classList.add('active');
}

function clearForm() {
  const form = getForm();
  if (!form) return;
  form.dataset.id = '';
  form.querySelectorAll('input, textarea').forEach(el => el.value = '');
  form.querySelectorAll('select').forEach(el => el.selectedIndex = 0);
}

function focusName() {
  const nameField = document.getElementById('detail-name');
  if (nameField) {
    nameField.focus();
    nameField.select();
  }
}

/**
 * Fetch the full panel body HTML for one entity + record (or 'new')
 * and swap it into .detail-panel — tab bar, form, everything. Swapping
 * the whole thing (not just the field inputs) is what lets opening a
 * different entity show the *right* tab set (e.g. contacts' Emails/
 * Phones/URLs/Organizations, not projects' Tasks/Links/Contacts left
 * over from whatever entity the page originally rendered with).
 *
 * Returns true on success, false on failure (network error, 404 —
 * caller decides whether to proceed with showing the panel).
 */
async function fetchAndSwapPanel(entity, recordIdOrNew) {
  const panel = getPanel();
  if (!panel) return false;

  try {
    const res = await fetch(`/panel/${entity}/${recordIdOrNew}`);
    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
    panel.innerHTML = await res.text();
    return true;
  } catch (err) {
    console.error('Could not fetch panel content:', err);
    return false;
  }
}

// ---------------------------------------------------------------------------
// Per-entity routing
//
// Most entities live under /crew/{entity}/... and the projects grid is
// the one to refresh after a save. Entities that live elsewhere (the
// seanchaí ledger) are listed here with their own save base URL and the
// window-level refresh hook their grid registers. Anything not listed
// falls back to the /crew default, so existing entities are unaffected.
// ---------------------------------------------------------------------------

const ENTITY_ROUTES = {
  records:  { base: '/seanchai/records',  refresh: '_refreshRecordsGrid' },
  searches: { base: '/seanchai/searches', refresh: '_refreshSearchesGrid' },
};

function saveBaseFor(entity) {
  return ENTITY_ROUTES[entity]?.base ?? `/crew/${entity}`;
}

function refreshGridFor(entity) {
  const hook = ENTITY_ROUTES[entity]?.refresh ?? '_refreshProjectsGrid';
  if (typeof window[hook] === 'function') window[hook]();
}

// ---------------------------------------------------------------------------
// Save to server
// Returns the saved record on success, null on failure.
// ---------------------------------------------------------------------------

// Guard against double-saves from rapid clicks or accesskey + click firing together
let _saving = false;

async function saveForm() {
  const form = getForm();
  if (!form) return null;

  const entity   = form.dataset.entity;
  const recordId = form.dataset.id;
  const isNew    = !recordId;

  const formData = new FormData(form);
  const data     = Object.fromEntries(formData);

  const base = saveBaseFor(entity);
  const url  = isNew
    ? `${base}/save`
    : `${base}/${recordId}/save`;

  try {
    const res  = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const body = await res.json();

    // FOUND BUG (fixed here): this used to check res.ok, but crew.py's
    // proc-backed save routes return failures as {"success": false,
    // "message": "...", "data": ...} at HTTP 200 — not a non-2xx status.
    // res.ok was always true, so a rejected save (duplicate name, etc.)
    // was silently treated as successful: form.dataset.id got set to
    // undefined (saved.id on a failure body), and the caller proceeded
    // as if the record had saved. The only reliable check is
    // body.success !== false, matching datasheet.js's saveRow().
    if (body.success === false) {
      alert(body.message || 'Save failed');
      return null;
    }

    // Update form id to the newly saved record's id
    form.dataset.id = body.id;
    const panel = getPanel();
    if (panel) panel.dataset.id = body.id;
    return body;
  } catch (err) {
    console.error('Save error:', err);
    alert('Save error: ' + err.message);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Button handlers
// ---------------------------------------------------------------------------

async function handleSave() {
  if (_saving) return;
  _saving = true;
  try {
    const saved = await saveForm();
    if (saved) {
      refreshGridFor(getForm()?.dataset.entity);
      hidePanel();
    }
  } finally {
    _saving = false;
  }
}

async function handleNew() {
  if (_saving) return;
  _saving = true;
  try {
    const saved = await saveForm();
    if (!saved) return;
    const entity = getForm()?.dataset.entity;
    clearForm();
    resetToDetailsTab();
    focusName();
    refreshGridFor(entity);
  } finally {
    _saving = false;
  }
}

function handleDiscard() {
  hidePanel();
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Open detail panel for an existing record.
 * Fetches the whole panel body from /panel/{entity}/{id} and swaps it
 * in wholesale — tab bar included — rather than fetching JSON and
 * manually populating known field names.
 */
export async function openDetailPanel(entity, recordId) {
  const panel = getPanel();
  if (!panel) return;

  const ok = await fetchAndSwapPanel(entity, recordId);
  if (!ok) return;

  panel.dataset.entity = entity;
  panel.dataset.id     = recordId;

  const form = getForm();
  if (form) {
    form.dataset.entity = entity;
    form.dataset.id     = recordId;
  }

  resetToDetailsTab();
  showPanel();
}

/**
 * Open detail panel in new-record mode.
 * Fetches the whole panel body from /panel/{entity}/new (empty values)
 * and swaps it in. Save will POST to {base}/save — /crew/{entity} by
 * default, or the entity's entry in ENTITY_ROUTES.
 */
export async function openNewRecordPanel(entity) {
  const panel = getPanel();
  if (!panel) return;

  const ok = await fetchAndSwapPanel(entity, 'new');
  if (!ok) return;

  panel.dataset.entity = entity;
  panel.dataset.id     = '';

  const form = getForm();
  if (form) {
    form.dataset.entity = entity;
    form.dataset.id     = '';
  }

  resetToDetailsTab();
  showPanel();
  focusName();
}

/**
 * Close the detail panel and restore the hero image.
 */
export function closeDetailPanel() {
  hidePanel();
}

// ---------------------------------------------------------------------------
// Init — wire up all event listeners
// ---------------------------------------------------------------------------

export function initDetailPanel() {
  // Tab switching
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('detail-tab-button')) {
      const panel = e.target.closest('.detail-panel');
      if (!panel) return;
      const targetTab = e.target.dataset.tab;
      panel.querySelectorAll('.detail-tab-button').forEach(b => b.classList.remove('active'));
      panel.querySelectorAll('.detail-tab-panel').forEach(p => p.classList.remove('active'));
      e.target.classList.add('active');
      const tabPanel = panel.querySelector(`.detail-tab-panel[data-tab="${targetTab}"]`);
      if (tabPanel) tabPanel.classList.add('active');
    }

    if (e.target.classList.contains('detail-close-button')) handleDiscard();

    // btn-save is type="submit" with form="detail-form" (see forms.yaml) so
    // clicking it also triggers native form submission. Without preventDefault
    // here, the browser's native GET-to-current-URL submission races the
    // fetch() in handleSave() and wins, since nothing else stops it.
    if (e.target.classList.contains('btn-save')) {
      e.preventDefault();
      handleSave();
    }
    if (e.target.classList.contains('btn-new'))             handleNew();
    if (e.target.classList.contains('btn-discard'))         handleDiscard();
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    const panel = getPanel();
    if (!panel?.classList.contains('active')) return;

    // Alt+S — Save and close
    if (e.altKey && e.key === 's') { e.preventDefault(); handleSave(); }
    // Alt+N — Save and new
    if (e.altKey && e.key === 'n') { e.preventDefault(); handleNew(); }
    // Alt+X or Escape — Discard and close
    if ((e.altKey && e.key === 'x') || e.key === 'Escape') { e.preventDefault(); handleDiscard(); }
  });

  // Safety net: catch any native form submission (e.g. pressing Enter in a
  // text input, which submits the nearest form by default browser behavior)
  // that isn't already intercepted by the btn-save click handler above.
  // Without this, Enter-to-submit falls back to a GET on the current URL
  // with form fields as query params, identical to the btn-save race bug.
  document.addEventListener('submit', (e) => {
    if (e.target.id === 'detail-form') {
      e.preventDefault();
      handleSave();
    }
  });
}

// ---------------------------------------------------------------------------
// Expose for non-module scripts (e.g. _projects_table.html)
// ---------------------------------------------------------------------------
window.openDetailPanel    = openDetailPanel;
window.openNewRecordPanel = openNewRecordPanel;
window.closeDetailPanel   = closeDetailPanel;

// Initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDetailPanel);
} else {
  initDetailPanel();
}
