/**
 * detail-panel.js
 *
 * Handles detail panel interactions:
 * - Opening detail panel when ⋯ is clicked on a datasheet row
 * - Closing detail panel on × button or Escape
 * - Tab switching
 * - Form save on button click
 *
 * Hero image and detail panel occupy the same spot. Opening the panel
 * hides the hero (display:none) and shows the panel (display:flex).
 *
 * Usage: Include in base.html with <script type="module" src="/static/js/detail-panel.js"></script>
 */

export function initDetailPanel() {
  const detailPanelContainer = document.getElementById('detail-panel-container');

  // Tab switching
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('detail-tab-button')) {
      const panel = e.target.closest('.detail-panel');
      if (!panel) return;

      const targetTab = e.target.dataset.tab;

      panel.querySelectorAll('.detail-tab-button').forEach(btn => {
        btn.classList.remove('active');
      });
      panel.querySelectorAll('.detail-tab-panel').forEach(p => {
        p.classList.remove('active');
      });

      e.target.classList.add('active');
      panel.querySelector(`.detail-tab-panel[data-tab="${targetTab}"]`).classList.add('active');
    }

    // Close button
    if (e.target.classList.contains('detail-close-button')) {
      closeDetailPanel();
    }
  });

  // Escape key to close detail panel
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && detailPanelContainer?.querySelector('.detail-panel.active')) {
      closeDetailPanel();
    }
  });

  // Form save
  document.addEventListener('submit', async (e) => {
    if (!e.target.classList.contains('detail-form')) return;
    e.preventDefault();

    const form = e.target;
    const entity = form.dataset.entity;
    const recordId = form.dataset.id;

    const formData = new FormData(form);
    const data = Object.fromEntries(formData);

    const saveUrl = `/crew/${entity}/${recordId}/save`;

    try {
      const res = await fetch(saveUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (res.ok) {
        console.log(`${entity} ${recordId} saved`);
      } else {
        const errorText = await res.text();
        console.error(`Save failed: ${errorText}`);
      }
    } catch (err) {
      console.error('Save error:', err);
    }
  });
}

/**
 * Open detail panel for a specific row.
 *
 * Hides the hero image, shows the detail panel in the same spot,
 * and populates the Details form fields from the fetched record.
 */
export async function openDetailPanel(entity, recordId) {
  const heroImage = document.querySelector('.crew-header');
  const detailPanelContainer = document.getElementById('detail-panel-container');

  // Fetch full record data
  let record;
  try {
    const res = await fetch(`/crew/${entity}/${recordId}`);
    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
    record = await res.json();
  } catch (err) {
    console.error('Could not fetch record:', err);
    return;
  }

  const detailPanel = detailPanelContainer?.querySelector('.detail-panel');
  if (!detailPanel) {
    console.error('Detail panel not found in DOM');
    return;
  }

  // Update panel data attributes
  detailPanel.dataset.entity = entity;
  detailPanel.dataset.id = recordId;

  // Populate the Details form fields from the fetched record
  const form = detailPanel.querySelector('.detail-form');
  if (form) {
    form.dataset.id = recordId;
    const nameField = form.querySelector('[name="name"]');
    const typeField = form.querySelector('[name="type_id"]');
    const statusField = form.querySelector('[name="status_id"]');
    const descField = form.querySelector('[name="description"]');
    if (nameField)   nameField.value   = record.name        ?? '';
    if (typeField)   typeField.value   = record.type_id     ?? '';
    if (statusField) statusField.value = record.status_id   ?? '';
    if (descField)   descField.value   = record.description ?? '';
  }

  // Swap: hide hero, show panel
  if (heroImage) heroImage.classList.add('hidden');
  detailPanel.classList.add('active');

  // Reset to first tab (Details)
  const firstButton = detailPanel.querySelector('.detail-tab-button');
  const firstPanel = detailPanel.querySelector('.detail-tab-panel[data-tab="details"]');
  if (firstButton && firstPanel) {
    detailPanel.querySelectorAll('.detail-tab-button').forEach(b => b.classList.remove('active'));
    detailPanel.querySelectorAll('.detail-tab-panel').forEach(p => p.classList.remove('active'));
    firstButton.classList.add('active');
    firstPanel.classList.add('active');
  }
}

/**
 * Close the detail panel and show the hero image again.
 */
export function closeDetailPanel() {
  const heroImage = document.querySelector('.crew-header');
  const detailPanelContainer = document.getElementById('detail-panel-container');
  const detailPanel = detailPanelContainer?.querySelector('.detail-panel');

  if (detailPanel) detailPanel.classList.remove('active');
  if (heroImage) heroImage.classList.remove('hidden');
}

// Expose for non-module scripts (e.g. _projects_table.html)
window.openDetailPanel = openDetailPanel;
window.closeDetailPanel = closeDetailPanel;

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDetailPanel);
} else {
  initDetailPanel();
}
