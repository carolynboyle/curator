/**
 * bidirectional-filter.js
 *
 * Reusable two-listbox cross-filter pattern: two lists of records connected
 * by a relationship (many-to-many or one-to-many). Selecting an item in
 * either list filters the other to only related items. A shared selection
 * readout shows whichever item was last clicked. Double-click opens that
 * record's detail panel; each list has its own live-search input and an
 * "add new" button.
 *
 * Not specific to any entity pair — first consumer is Organizations ↔
 * Contacts (Identities tab), but this is written generically enough for
 * any two-list cross-reference UI (e.g. a future Projects ↔ Contacts tab).
 *
 * Markup contract for each list item:
 *   <div class="identity-item"
 *        data-id="123"
 *        data-name="Display Name"
 *        data-related-ids="4,7,9">
 *
 * data-related-ids holds the comma-separated ids of items in the *other*
 * list that this item is connected to. Both sides use the same attribute
 * name — the module doesn't care which side is "left" or "right".
 *
 * Depends on: window.openDetailPanel, window.openNewRecordPanel
 * (both exposed globally by detail-panel.js).
 *
 * Usage:
 *   import { initBidirectionalFilter } from './bidirectional-filter.js';
 *
 *   initBidirectionalFilter({
 *     selectionBoxId: 'identity-selection',
 *     left: {
 *       listboxId: 'org-listbox',
 *       searchId:  'org-search',
 *       addBtnId:  'org-add-btn',
 *       entity:    'organizations',
 *     },
 *     right: {
 *       listboxId: 'contact-listbox',
 *       searchId:  'contact-search',
 *       addBtnId:  'contact-add-btn',
 *       entity:    'contacts',
 *     },
 *   });
 */

/**
 * @param {Object} config
 * @param {string} config.selectionBoxId - id of the shared selection readout element
 * @param {Object} config.left  - { listboxId, searchId, addBtnId, entity }
 * @param {Object} config.right - { listboxId, searchId, addBtnId, entity }
 */
export function initBidirectionalFilter(config) {
  const { selectionBoxId, left, right } = config;

  const selectionBox = document.getElementById(selectionBoxId);

  function makeSide(side, other) {
    return {
      listbox: document.getElementById(side.listboxId),
      search:  document.getElementById(side.searchId),
      addBtn:  document.getElementById(side.addBtnId),
      entity:  side.entity,
      selectedId: null,
      // set after both sides constructed — see wiring below
      other: null,
    };
  }

  const leftSide  = makeSide(left, right);
  const rightSide = makeSide(right, left);
  leftSide.other  = rightSide;
  rightSide.other = leftSide;

  function getItems(side) {
    return side.listbox.querySelectorAll('.identity-item');
  }

  function setItemVisible(el, visible) {
    el.style.display = visible ? '' : 'none';
  }

  function showSelection(name) {
    selectionBox.textContent = name;
    selectionBox.classList.add('has-selection');
  }

  function clearSelectionBox() {
    selectionBox.innerHTML = '<span class="identity-selection-placeholder">No selection</span>';
    selectionBox.classList.remove('has-selection');
  }

  function selectItem(side, item) {
    getItems(side).forEach(i => i.classList.remove('selected'));
    side.selectedId = item.dataset.id;
    item.classList.add('selected');
    showSelection(item.dataset.name);

    const relatedIds = item.dataset.relatedIds
      ? item.dataset.relatedIds.split(',').filter(Boolean)
      : [];
    getItems(side.other).forEach(o => {
      setItemVisible(o, relatedIds.includes(o.dataset.id));
    });

    side.other.selectedId = null;
    getItems(side.other).forEach(i => i.classList.remove('selected'));
  }

  function clearSelection(side) {
    side.selectedId = null;
    clearSelectionBox();
    getItems(side).forEach(i => {
      i.classList.remove('selected');
      setItemVisible(i, true);
    });
    applySearch(side.other);
  }

  function applySearch(side) {
    const term = side.search.value.toLowerCase();
    getItems(side).forEach(item => {
      setItemVisible(item, item.textContent.toLowerCase().includes(term));
    });
  }

  function wireSide(side) {
    side.listbox.addEventListener('click', e => {
      const item = e.target.closest('.identity-item');
      if (!item) return;
      if (item.dataset.id === side.selectedId) {
        clearSelection(side);
      } else {
        selectItem(side, item);
      }
    });

    side.listbox.addEventListener('dblclick', e => {
      const item = e.target.closest('.identity-item');
      if (!item) return;
      window.openDetailPanel(side.entity, item.dataset.id);
    });

    side.search.addEventListener('input', () => {
      if (side.selectedId) clearSelection(side);
      applySearch(side);
    });

    if (side.addBtn) {
      side.addBtn.addEventListener('click', () => {
        window.openNewRecordPanel(side.entity);
      });
    }
  }

  wireSide(leftSide);
  wireSide(rightSide);
}
