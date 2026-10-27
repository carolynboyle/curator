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

function populateForm(record) {
  const form = getForm();
  if (!form) return;
  form.dataset.id = record.id ?? '';

  const nameField   = form.querySelector('[name="name"]');
  const typeField   = form.querySelector('[name="type_id"]');
  const statusField = form.querySelector('[name="status_id"]');
  const descField   = form.querySelector('[name="description"]');

  if (nameField)   nameField.value   = record.name        ?? '';
  if (typeField)   typeField.value   = record.type_id     ?? '';
  if (statusField) statusField.value = record.status_id   ?? '';
  if (descField)   descField.value   = record.description ?? '';
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

  const url = isNew
    ? `/crew/${entity}/save`
    : `/crew/${entity}/${recordId}/save`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (res.ok) {
      const saved = await res.json();
      // Update form id to the newly saved record's id
      form.dataset.id = saved.id;
      const panel = getPanel();
      if (panel) panel.dataset.id = saved.id;
      return saved;
    } else {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      alert(err.detail || 'Save failed');
      return null;
    }
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
      if (window._refreshProjectsGrid) window._refreshProjectsGrid();
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
    clearForm();
    resetToDetailsTab();
    focusName();
    if (window._refreshProjectsGrid) window._refreshProjectsGrid();
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
 * Fetches record from server and populates the form.
 */
export async function openDetailPanel(entity, recordId) {
  let record;
  try {
    const res = await fetch(`/crew/${entity}/${recordId}`);
    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
    record = await res.json();
  } catch (err) {
    console.error('Could not fetch record:', err);
    return;
  }

  const panel = getPanel();
  const form  = getForm();
  if (!panel || !form) return;

  panel.dataset.entity = entity;
  panel.dataset.id     = recordId;
  form.dataset.entity  = entity;

  populateForm(record);
  resetToDetailsTab();
  showPanel();
}

/**
 * Open detail panel in new-record mode.
 * Form is empty, save will POST to /crew/{entity}/save.
 */
export function openNewRecordPanel(entity) {
  const panel = getPanel();
  const form  = getForm();
  if (!panel || !form) return;

  panel.dataset.entity = entity;
  panel.dataset.id     = '';
  form.dataset.entity  = entity;

  clearForm();
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
    if (e.target.classList.contains('btn-save'))            handleSave();
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
