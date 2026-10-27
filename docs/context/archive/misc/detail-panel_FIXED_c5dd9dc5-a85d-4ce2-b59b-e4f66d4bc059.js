/**
 * detail-panel.js
 *
 * Handles detail panel interactions:
 * - Opening detail panel when ⋯ is clicked on a datasheet row
 * - Closing detail panel on × button or Escape
 * - Tab switching
 * - Form save/new/discard on button click or keyboard shortcut
 * - Enter key moves to next field (like Tab) instead of submitting form
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

    // New button (Alt+N)
    if (e.target.classList.contains('btn-new')) {
      handleNewRecord(e);
    }

    // Discard button (Alt+X / Escape)
    if (e.target.classList.contains('btn-discard')) {
      closeDetailPanel();
    }
  });

  // Escape key to close detail panel
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && detailPanelContainer?.querySelector('.detail-panel.active')) {
      closeDetailPanel();
    }

    // Alt+S to save
    if (e.altKey && e.key === 's') {
      e.preventDefault();
      const detailPanel = detailPanelContainer?.querySelector('.detail-panel.active');
      if (detailPanel) {
        const form = detailPanel.querySelector('form.detail-form');
        if (form) form.dispatchEvent(new Event('submit'));
      }
    }

    // Alt+N to new
    if (e.altKey && e.key === 'n') {
      e.preventDefault();
      const detailPanel = detailPanelContainer?.querySelector('.detail-panel.active');
      if (detailPanel) {
        handleNewRecord(e);
      }
    }

    // Alt+X to discard
    if (e.altKey && e.key === 'x') {
      e.preventDefault();
      closeDetailPanel();
    }
  });

  // Enter key in form inputs: move to next field instead of submitting
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const form = e.target.closest('form.detail-form');
      if (!form) return;

      // Only handle Enter in input and textarea elements
      if (!['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

      e.preventDefault();

      // Get all focusable form elements (inputs, selects, textareas)
      const focusableElements = Array.from(form.querySelectorAll(
        'input:not([type="hidden"]), select, textarea'
      ));

      const currentIndex = focusableElements.indexOf(e.target);
      if (currentIndex !== -1 && currentIndex < focusableElements.length - 1) {
        // Move to next element
        focusableElements[currentIndex + 1].focus();
      } else if (currentIndex === focusableElements.length - 1) {
        // If at last field, blur to deselect
        e.target.blur();
      }
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
        // Update successful — close panel
        console.log(`${entity} ${recordId} saved`);
        closeDetailPanel();
        // TODO: Refresh datasheet grid
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
 * Handle "New" button: save current record and reset form for next entry.
 */
function handleNewRecord(e) {
  const detailPanel = e.target?.closest('.detail-panel') || document.querySelector('.detail-panel.active');
  if (!detailPanel) return;

  const form = detailPanel.querySelector('form.detail-form');
  if (!form) return;

  // Save current record first
  form.dispatchEvent(new Event('submit'));

  // Reset form and focus Name field
  form.reset();
  const nameField = form.querySelector('input[name="name"]');
  if (nameField) {
    nameField.focus();
  }
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

  // Focus Name field
  const nameField = detailPanel.querySelector('input[name="name"]');
  if (nameField) {
    nameField.focus();
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

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDetailPanel);
} else {
  initDetailPanel();
}
