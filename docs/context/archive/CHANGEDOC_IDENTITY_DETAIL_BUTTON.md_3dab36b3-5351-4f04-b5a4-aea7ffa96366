# Changedoc: `⋯` detail button on the Identities selection readout

**Date:** 2026-07-05
**Reason:** Double-click-to-open on the Identities listboxes is wired
correctly (confirmed via DevTools' Event Listeners panel — the
`dblclick` handler is attached and points at the right line) but isn't
reliably firing in practice, and chasing that down further isn't worth
the time right now. This sidesteps the question entirely by reusing the
exact same `⋯` button pattern already proven working on the Projects
datasheet (`detail-icon` class, `window.openDetailPanel(entity, id)` on
click) — single-click select, then click `⋯` to open, no dblclick
reliability involved at all.

**Scope check against `project_rules.md`:** reuses an existing pattern
rather than inventing a new one; `openDetailPanel` itself is untouched.

---

## 1. `src/curator/templates/partials/_tab_identities.html` (edit)

### BEFORE

```html
<!-- Shared selection readout — fills with whichever org or contact was
     just clicked. Full-width sibling above the two-column grid so it
     works identically at any viewport width; no breakpoint variant needed. -->
<div class="identity-selection" id="identity-selection">
    <span class="identity-selection-placeholder">No selection</span>
</div>
```

### AFTER

```html
<!-- Shared selection readout — fills with whichever org or contact was
     just clicked. Full-width sibling above the two-column grid so it
     works identically at any viewport width; no breakpoint variant needed.

     The ⋯ button reuses the same detail-icon pattern already working on
     the Projects datasheet (see _projects_table.html) — click a row to
     select it, then click ⋯ to open its detail panel. Added as an
     alternative to double-click, which is wired correctly but wasn't
     reliably firing; rather than chase that down, this reuses a pattern
     already known to work. Hidden until something is selected — see
     bidirectional-filter.js's selectItem()/clearSelection(). -->
<div class="identity-selection" id="identity-selection">
    <span class="identity-selection-placeholder">No selection</span>
    <button
        class="detail-icon"
        id="identity-detail-btn"
        title="Open details"
        style="display:none;"
    >⋯</button>
</div>
```

### BEFORE (script block, config passed to `initBidirectionalFilter`)

```html
<script type="module">
    import { initBidirectionalFilter } from '/static/js/bidirectional-filter.js';

    initBidirectionalFilter({
        selectionBoxId: 'identity-selection',
        left: {
            listboxId: 'org-listbox',
            searchId:  'org-search',
            addBtnId:  'org-add-btn',
            entity:    'organizations',
        },
        right: {
            listboxId: 'contact-listbox',
            searchId:  'contact-search',
            addBtnId:  'contact-add-btn',
            entity:    'contacts',
        },
    });
</script>
```

### AFTER

```html
<script type="module">
    import { initBidirectionalFilter } from '/static/js/bidirectional-filter.js';

    initBidirectionalFilter({
        selectionBoxId: 'identity-selection',
        detailBtnId:    'identity-detail-btn',
        left: {
            listboxId: 'org-listbox',
            searchId:  'org-search',
            addBtnId:  'org-add-btn',
            entity:    'organizations',
        },
        right: {
            listboxId: 'contact-listbox',
            searchId:  'contact-search',
            addBtnId:  'contact-add-btn',
            entity:    'contacts',
        },
    });
</script>
```

---

## 2. `src/curator/static/js/bidirectional-filter.js` (edit — complete file)

**What changed:** accepts a new `detailBtnId` config key, shows/hides
and populates that button's entity/id whenever selection changes, and
wires its click to `window.openDetailPanel` — the same call the
(unreliable) `dblclick` handler already makes. The `dblclick` handler
itself is left in place, untouched — no harm in keeping it, and it may
simply start working reliably on its own another day; this changedoc
doesn't chase that question further.

### BEFORE (complete file, as uploaded)

```javascript
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
```

### AFTER (complete file — replace the whole thing with this)

```javascript
/**
 * bidirectional-filter.js
 *
 * Reusable two-listbox cross-filter pattern: two lists of records connected
 * by a relationship (many-to-many or one-to-many). Selecting an item in
 * either list filters the other to only related items. A shared selection
 * readout shows whichever item was last clicked, alongside a ⋯ button
 * (same detail-icon pattern as the Projects datasheet) to open that
 * item's detail panel. Double-click also attempts to open it directly —
 * that handler is wired correctly but hasn't proven reliable in
 * practice; the ⋯ button is the dependable path and doesn't require
 * chasing that down. Each list has its own live-search input and an
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
 *     detailBtnId:    'identity-detail-btn',
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
 * @param {string} config.detailBtnId - id of the ⋯ button inside the readout
 *   that opens the currently selected item's detail panel
 * @param {Object} config.left  - { listboxId, searchId, addBtnId, entity }
 * @param {Object} config.right - { listboxId, searchId, addBtnId, entity }
 */
export function initBidirectionalFilter(config) {
  const { selectionBoxId, detailBtnId, left, right } = config;

  const selectionBox = document.getElementById(selectionBoxId);
  const detailBtn    = document.getElementById(detailBtnId);

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
    // Re-append here since textContent above wiped detailBtn out of the
    // readout along with the placeholder span — restore it as a sibling.
    if (detailBtn) selectionBox.appendChild(detailBtn);
  }

  function clearSelectionBox() {
    selectionBox.innerHTML = '<span class="identity-selection-placeholder">No selection</span>';
    selectionBox.classList.remove('has-selection');
    // innerHTML above destroys detailBtn's original DOM node along with
    // everything else in the readout — same restoration as showSelection.
    if (detailBtn) {
      detailBtn.style.display = 'none';
      selectionBox.appendChild(detailBtn);
    }
  }

  function selectItem(side, item) {
    getItems(side).forEach(i => i.classList.remove('selected'));
    side.selectedId = item.dataset.id;
    item.classList.add('selected');
    showSelection(item.dataset.name);

    if (detailBtn) {
      detailBtn.dataset.entity = side.entity;
      detailBtn.dataset.id     = item.dataset.id;
      detailBtn.style.display  = '';
    }

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

  if (detailBtn) {
    detailBtn.addEventListener('click', () => {
      const { entity, id } = detailBtn.dataset;
      if (entity && id) window.openDetailPanel(entity, id);
    });
  }

  wireSide(leftSide);
  wireSide(rightSide);
}
```

**Why `showSelection`/`clearSelectionBox` re-append `detailBtn`:** both
functions replace the readout's contents wholesale
(`textContent = ...` / `innerHTML = ...`), which would destroy the
button's DOM node (and its click listener) along with the placeholder
text it's replacing. Re-appending the same node after each replacement
keeps the one listener attached at init working indefinitely, rather
than needing to re-wire a click handler every time selection changes.

---

## Apply and verify

1. Update `_tab_identities.html` — add the button markup, add
   `detailBtnId: 'identity-detail-btn'` to the `initBidirectionalFilter`
   call.
2. Replace `bidirectional-filter.js` with the AFTER version.
3. No Python/SQL changes — `pylint src/`/`pytest` are unaffected either
   way, nothing to rerun there.
4. Restart `uvicorn` (template/static changes need a reload same as
   anything else).
5. **Manual test:**
   - Identities tab, single-click an organization. The `⋯` button
     should appear next to its name in the readout bar.
   - Click `⋯` — the detail panel should open showing that
     organization's fields (Name/Notes) and its own tab set
     (Details/Contacts only).
   - Click a contact, click `⋯` — same check, contact's fields
     (Name/Title/Notes) and its tab set (Details/Emails/Phones/URLs/
     Organizations).
   - Click elsewhere to clear selection — confirm `⋯` disappears again.
