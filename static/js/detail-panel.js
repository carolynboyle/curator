/**
 * detail-panel.js
 *
 * Handles detail panel interactions:
 * - Opening detail panel when ⋯ is clicked on a datasheet row
 * - Closing detail panel on × button or Escape
 * - Tab switching
 * - Form save on button click
 *
 * Usage: Include in base.html with <script type="module" src="/static/js/detail-panel.js"></script>
 */

export function initDetailPanel() {
  // Get references to key elements
  const heroImage = document.querySelector('.crew-hero');
  const detailPanelContainer = document.getElementById('detail-panel-container');

  // Tab switching
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('detail-tab-button')) {
      const panel = e.target.closest('.detail-panel');
      if (!panel) return;

      const targetTab = e.target.dataset.tab;
      
      // Deactivate all buttons and panels in this detail panel
      panel.querySelectorAll('.detail-tab-button').forEach(btn => {
        btn.classList.remove('active');
      });
      panel.querySelectorAll('.detail-tab-panel').forEach(p => {
        p.classList.remove('active');
      });

      // Activate the clicked tab
      e.target.classList.add('active');
      panel.querySelector(`[data-tab="${targetTab}"]`).classList.add('active');
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
        // Update successful — could refresh datasheet or show toast
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
 * Called when user clicks ⋯ on a datasheet row.
 * Fetches full record, renders panel, fades hero/panel, attaches listeners.
 */
export async function openDetailPanel(entity, recordId) {
  const heroImage = document.querySelector('.crew-hero');
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

  // Render detail panel partial (deferred — will be rendered by template initially)
  // For now, just activate the panel if it exists

  const detailPanel = detailPanelContainer?.querySelector('.detail-panel');
  if (!detailPanel) {
    console.error('Detail panel not found in DOM');
    return;
  }

  // Update panel data attributes
  detailPanel.dataset.entity = entity;
  detailPanel.dataset.id = recordId;

  // Fade out hero, fade in detail panel
  if (heroImage) {
    heroImage.classList.add('hidden');
  }
  detailPanel.classList.add('active');

  // Reset form to first tab
  const firstButton = detailPanel.querySelector('.detail-tab-button');
  const firstPanel = detailPanel.querySelector('[data-tab="details"]');
  if (firstButton && firstPanel) {
    detailPanel.querySelectorAll('.detail-tab-button').forEach(b => b.classList.remove('active'));
    detailPanel.querySelectorAll('.detail-tab-panel').forEach(p => p.classList.remove('active'));
    firstButton.classList.add('active');
    firstPanel.classList.add('active');
  }
}

/**
 * Close the detail panel and fade hero back in.
 */
export function closeDetailPanel() {
  const heroImage = document.querySelector('.crew-hero');
  const detailPanelContainer = document.getElementById('detail-panel-container');
  const detailPanel = detailPanelContainer?.querySelector('.detail-panel');

  if (detailPanel) {
    detailPanel.classList.remove('active');
  }
  if (heroImage) {
    heroImage.classList.remove('hidden');
  }
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
