# Changedoc: Identities tab redesign — shared selection box, single-field rows, dblclick-to-detail

**Files:** `templates/partials/_tab_identities.html`, `static/css/identity.css`
**Type:** UI/UX restructure — layout, markup, and JS wiring. No backend changes
(those are covered separately in the crew.py contacts/organizations routes
changedoc).

**Reason:** Mobile-first redesign of the Captain's Identities tab.
- `⋯` detail buttons are redundant now that double-click opens the detail
  form directly (mirrors the `⋯` behavior on projects datasheet rows) —
  removed.
- Listbox rows drop the email hint line — name only, per decision that
  detail comes from double-click, not from a denser row.
- A single full-width "current selection" readout replaces the previous
  pattern of writing the selected name into the search `<input>` — fixes
  both the truncation problem (long names) and the confusing overload of
  the search box doubling as a selection display.
- `+ Contact` / `+ Organization` buttons wired to `openNewRecordPanel()`
  (already exists in `detail-panel.js`, entity-agnostic, no JS changes
  needed there).
- Columns stay 50/50 side-by-side at all widths — no stacking breakpoint —
  since the selection box already solves the "can't see the full name"
  problem the two-column width was creating.

---

## BEFORE — `templates/partials/_tab_identities.html`

```html
<div class="identity-panels">

    <!-- Organizations panel (left) -->
    <div class="identity-panel">
        <div class="identity-panel-header">
            <input
                type="text"
                id="org-search"
                class="identity-search"
                placeholder="Organization..."
                autocomplete="off"
            >
            <button
                id="org-detail-btn"
                class="identity-detail-btn"
                title="Organization details"
                disabled
            >⋯</button>
        </div>
        <button class="identity-add-btn" id="org-add-btn" title="Add organization">+ Organization</button>
        <div class="identity-listbox" id="org-listbox">
            {% for org in organizations %}
            <div class="identity-item"
                 data-id="{{ org.id }}"
                 data-contact-ids="{{ org.contact_ids | join(',') }}">
                {{ org.name }}
            </div>
            {% else %}
            <div class="identity-empty">No organizations found.</div>
            {% endfor %}
        </div>
    </div>

    <!-- Contacts panel (right) -->
    <div class="identity-panel">
        <div class="identity-panel-header">
            <input
                type="text"
                id="contact-search"
                class="identity-search"
                placeholder="Contact..."
                autocomplete="off"
            >
            <button
                id="contact-detail-btn"
                class="identity-detail-btn"
                title="Contact details"
                disabled
            >⋯</button>
        </div>
        <button class="identity-add-btn" id="contact-add-btn" title="Add contact">+ Contact</button>
        <div class="identity-listbox" id="contact-listbox">
            {% for contact in contacts %}
            <div class="identity-item"
                 data-id="{{ contact.id }}"
                 data-org-ids="{{ contact.org_ids | join(',') }}">
                <span class="identity-item-name">{{ contact.name or "—" }}</span>
                {% if contact.email %}
                <span class="identity-item-hint">{{ contact.email }}</span>
                {% endif %}
            </div>
            {% else %}
            <div class="identity-empty">No contacts found.</div>
            {% endfor %}
        </div>
    </div>

</div>

<script>
// -------------------------------------------------------------------------
// Identity panel — bidirectional filtering
// -------------------------------------------------------------------------
(function () {
    let selectedOrgId     = null;
    let selectedContactId = null;

    const orgListbox       = document.getElementById('org-listbox');
    const contactListbox   = document.getElementById('contact-listbox');
    const orgSearch        = document.getElementById('org-search');
    const contactSearch    = document.getElementById('contact-search');
    const orgDetailBtn     = document.getElementById('org-detail-btn');
    const contactDetailBtn = document.getElementById('contact-detail-btn');

    function getOrgItems()     { return orgListbox.querySelectorAll('.identity-item'); }
    function getContactItems() { return contactListbox.querySelectorAll('.identity-item'); }

    function showClearPill(inputEl, onClear) {
        const existing = inputEl.parentElement.querySelector('.identity-clear');
        if (existing) existing.remove();
        const pill = document.createElement('button');
        pill.className = 'identity-clear';
        pill.textContent = '×';
        pill.title = 'Clear filter';
        pill.addEventListener('click', onClear);
        inputEl.parentElement.insertBefore(pill, inputEl.nextSibling);
    }

    function removeClearPill(inputEl) {
        const existing = inputEl.parentElement.querySelector('.identity-clear');
        if (existing) existing.remove();
    }

    function setItemVisible(el, visible) {
        el.style.display = visible ? '' : 'none';
    }

    // -- Org selection --------------------------------------------------------

    function selectOrg(item) {
        getOrgItems().forEach(i => i.classList.remove('selected'));
        selectedOrgId = item.dataset.id;
        item.classList.add('selected');
        orgSearch.value = item.textContent.trim();
        orgDetailBtn.disabled = false;

        const contactIds = item.dataset.contactIds
            ? item.dataset.contactIds.split(',').filter(Boolean)
            : [];
        getContactItems().forEach(c => {
            setItemVisible(c, contactIds.includes(c.dataset.id));
        });

        showClearPill(orgSearch, clearOrgSelection);
        selectedContactId = null;
        contactSearch.value = '';
        contactDetailBtn.disabled = true;
        removeClearPill(contactSearch);
    }

    function clearOrgSelection() {
        selectedOrgId = null;
        orgSearch.value = '';
        orgDetailBtn.disabled = true;
        removeClearPill(orgSearch);
        getOrgItems().forEach(i => {
            i.classList.remove('selected');
            setItemVisible(i, true);
        });
        applyContactSearch(contactSearch.value);
    }

    // -- Contact selection ----------------------------------------------------

    function selectContact(item) {
        getContactItems().forEach(i => i.classList.remove('selected'));
        selectedContactId = item.dataset.id;
        item.classList.add('selected');
        const name = item.querySelector('.identity-item-name');
        contactSearch.value = name ? name.textContent.trim() : item.textContent.trim();
        contactDetailBtn.disabled = false;

        const orgIds = item.dataset.orgIds
            ? item.dataset.orgIds.split(',').filter(Boolean)
            : [];
        getOrgItems().forEach(o => {
            setItemVisible(o, orgIds.length === 0 ? false : orgIds.includes(o.dataset.id));
        });

        showClearPill(contactSearch, clearContactSelection);
        selectedOrgId = null;
        orgSearch.value = '';
        orgDetailBtn.disabled = true;
        removeClearPill(orgSearch);
    }

    function clearContactSelection() {
        selectedContactId = null;
        contactSearch.value = '';
        contactDetailBtn.disabled = true;
        removeClearPill(contactSearch);
        getContactItems().forEach(i => {
            i.classList.remove('selected');
            setItemVisible(i, true);
        });
        applyOrgSearch(orgSearch.value);
    }

    // -- Search filtering -----------------------------------------------------

    function applyOrgSearch(term) {
        const t = term.toLowerCase();
        getOrgItems().forEach(item => {
            setItemVisible(item, item.textContent.toLowerCase().includes(t));
        });
    }

    function applyContactSearch(term) {
        const t = term.toLowerCase();
        getContactItems().forEach(item => {
            setItemVisible(item, item.textContent.toLowerCase().includes(t));
        });
    }

    // -- Event listeners ------------------------------------------------------

    orgListbox.addEventListener('click', e => {
        const item = e.target.closest('.identity-item');
        if (!item) return;
        if (item.dataset.id === selectedOrgId) {
            clearOrgSelection();
        } else {
            selectOrg(item);
        }
    });

    contactListbox.addEventListener('click', e => {
        const item = e.target.closest('.identity-item');
        if (!item) return;
        if (item.dataset.id === selectedContactId) {
            clearContactSelection();
        } else {
            selectContact(item);
        }
    });

    orgSearch.addEventListener('input', e => {
        if (selectedOrgId) clearOrgSelection();
        applyOrgSearch(e.target.value);
    });

    contactSearch.addEventListener('input', e => {
        if (selectedContactId) clearContactSelection();
        applyContactSearch(e.target.value);
    });

    // Detail buttons — deferred
    orgDetailBtn.addEventListener('click', () => {
        // Future: open org detail panel for selectedOrgId
    });

    contactDetailBtn.addEventListener('click', () => {
        // Future: open contact detail panel for selectedContactId
    });

    // Add buttons — deferred
    document.getElementById('org-add-btn').addEventListener('click', () => {
        // Future: open new org form
    });

    document.getElementById('contact-add-btn').addEventListener('click', () => {
        // Future: open new contact form
    });
}());
</script>
```

## AFTER — `templates/partials/_tab_identities.html`

```html
<!-- Shared selection readout — fills with whichever org or contact was
     just clicked. Full-width sibling above the two-column grid so it
     works identically at any viewport width; no breakpoint variant needed. -->
<div class="identity-selection" id="identity-selection">
    <span class="identity-selection-placeholder">No selection</span>
</div>

<div class="identity-panels">

    <!-- Organizations panel (left) -->
    <div class="identity-panel">
        <input
            type="text"
            id="org-search"
            class="identity-search"
            placeholder="Organization..."
            autocomplete="off"
        >
        <button class="identity-add-btn" id="org-add-btn" title="Add organization">+ Organization</button>
        <div class="identity-listbox" id="org-listbox">
            {% for org in organizations %}
            <div class="identity-item"
                 data-id="{{ org.id }}"
                 data-name="{{ org.name }}"
                 data-contact-ids="{{ org.contact_ids | join(',') }}">
                {{ org.name }}
            </div>
            {% else %}
            <div class="identity-empty">No organizations found.</div>
            {% endfor %}
        </div>
    </div>

    <!-- Contacts panel (right) -->
    <div class="identity-panel">
        <input
            type="text"
            id="contact-search"
            class="identity-search"
            placeholder="Contact..."
            autocomplete="off"
        >
        <button class="identity-add-btn" id="contact-add-btn" title="Add contact">+ Contact</button>
        <div class="identity-listbox" id="contact-listbox">
            {% for contact in contacts %}
            <div class="identity-item"
                 data-id="{{ contact.id }}"
                 data-name="{{ contact.name or '—' }}"
                 data-org-ids="{{ contact.org_ids | join(',') }}">
                {{ contact.name or "—" }}
            </div>
            {% else %}
            <div class="identity-empty">No contacts found.</div>
            {% endfor %}
        </div>
    </div>

</div>

<script>
// -------------------------------------------------------------------------
// Identity panel — bidirectional filtering + selection readout + dblclick
// -------------------------------------------------------------------------
(function () {
    let selectedOrgId     = null;
    let selectedContactId = null;

    const orgListbox       = document.getElementById('org-listbox');
    const contactListbox   = document.getElementById('contact-listbox');
    const orgSearch        = document.getElementById('org-search');
    const contactSearch    = document.getElementById('contact-search');
    const selectionBox     = document.getElementById('identity-selection');

    function getOrgItems()     { return orgListbox.querySelectorAll('.identity-item'); }
    function getContactItems() { return contactListbox.querySelectorAll('.identity-item'); }

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

    // -- Org selection --------------------------------------------------------

    function selectOrg(item) {
        getOrgItems().forEach(i => i.classList.remove('selected'));
        selectedOrgId = item.dataset.id;
        item.classList.add('selected');
        showSelection(item.dataset.name);

        const contactIds = item.dataset.contactIds
            ? item.dataset.contactIds.split(',').filter(Boolean)
            : [];
        getContactItems().forEach(c => {
            setItemVisible(c, contactIds.includes(c.dataset.id));
        });

        selectedContactId = null;
        getContactItems().forEach(i => i.classList.remove('selected'));
    }

    function clearOrgSelection() {
        selectedOrgId = null;
        clearSelectionBox();
        getOrgItems().forEach(i => {
            i.classList.remove('selected');
            setItemVisible(i, true);
        });
        applyContactSearch(contactSearch.value);
    }

    // -- Contact selection ----------------------------------------------------

    function selectContact(item) {
        getContactItems().forEach(i => i.classList.remove('selected'));
        selectedContactId = item.dataset.id;
        item.classList.add('selected');
        showSelection(item.dataset.name);

        const orgIds = item.dataset.orgIds
            ? item.dataset.orgIds.split(',').filter(Boolean)
            : [];
        getOrgItems().forEach(o => {
            setItemVisible(o, orgIds.length === 0 ? false : orgIds.includes(o.dataset.id));
        });

        selectedOrgId = null;
        getOrgItems().forEach(i => i.classList.remove('selected'));
    }

    function clearContactSelection() {
        selectedContactId = null;
        clearSelectionBox();
        getContactItems().forEach(i => {
            i.classList.remove('selected');
            setItemVisible(i, true);
        });
        applyOrgSearch(orgSearch.value);
    }

    // -- Search filtering -----------------------------------------------------

    function applyOrgSearch(term) {
        const t = term.toLowerCase();
        getOrgItems().forEach(item => {
            setItemVisible(item, item.textContent.toLowerCase().includes(t));
        });
    }

    function applyContactSearch(term) {
        const t = term.toLowerCase();
        getContactItems().forEach(item => {
            setItemVisible(item, item.textContent.toLowerCase().includes(t));
        });
    }

    // -- Event listeners ------------------------------------------------------

    orgListbox.addEventListener('click', e => {
        const item = e.target.closest('.identity-item');
        if (!item) return;
        if (item.dataset.id === selectedOrgId) {
            clearOrgSelection();
        } else {
            selectOrg(item);
        }
    });

    orgListbox.addEventListener('dblclick', e => {
        const item = e.target.closest('.identity-item');
        if (!item) return;
        window.openDetailPanel('organizations', item.dataset.id);
    });

    contactListbox.addEventListener('click', e => {
        const item = e.target.closest('.identity-item');
        if (!item) return;
        if (item.dataset.id === selectedContactId) {
            clearContactSelection();
        } else {
            selectContact(item);
        }
    });

    contactListbox.addEventListener('dblclick', e => {
        const item = e.target.closest('.identity-item');
        if (!item) return;
        window.openDetailPanel('contacts', item.dataset.id);
    });

    orgSearch.addEventListener('input', e => {
        if (selectedOrgId) clearOrgSelection();
        applyOrgSearch(e.target.value);
    });

    contactSearch.addEventListener('input', e => {
        if (selectedContactId) clearContactSelection();
        applyContactSearch(e.target.value);
    });

    // Add buttons
    document.getElementById('org-add-btn').addEventListener('click', () => {
        window.openNewRecordPanel('organizations');
    });

    document.getElementById('contact-add-btn').addEventListener('click', () => {
        window.openNewRecordPanel('contacts');
    });
}());
</script>
```

---

## BEFORE — `static/css/identity.css`

```css
/* ---- Panel header — search box + detail button ---------------------------- */

.identity-panel-header {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    position: relative;
}

.identity-search {
    flex: 1;
    padding: 4px 8px;
    border: 1px solid #dde1e7;
    border-radius: 3px;
    font-size: 0.875rem;
    font-family: inherit;
    background: #ffffff;
    color: #1a1a1a;
}

.identity-search:focus {
    outline: 2px solid #0f766e;
    outline-offset: -1px;
    border-color: #0f766e;
}

.identity-detail-btn {
    padding: 2px 8px;
    border: 1px solid #dde1e7;
    border-radius: 3px;
    background: #f3f4f6;
    color: #6b7280;
    font-size: 1rem;
    cursor: pointer;
    opacity: 0.5;
    transition: opacity 0.15s;
}

.identity-detail-btn:not(:disabled) {
    opacity: 1;
    color: #0f766e;
    border-color: #0f766e;
    background: #f0faf9;
    cursor: pointer;
}

.identity-detail-btn:disabled {
    cursor: default;
}

/* ---- Clear filter pill ---------------------------------------------------- */

.identity-clear {
    position: absolute;
    right: 44px;  /* sits just inside the search box, left of detail btn */
    background: #e5e7eb;
    border: none;
    border-radius: 10px;
    padding: 1px 7px;
    font-size: 0.8rem;
    color: #374151;
    cursor: pointer;
    line-height: 1.4;
}

.identity-clear:hover {
    background: #dc2626;
    color: #ffffff;
}
```

```css
.identity-item-name {
    font-weight: 500;
}

.identity-item-hint {
    font-size: 0.78rem;
    color: #6b7280;
}

.identity-item.selected .identity-item-hint {
    color: #3b6ea5;
}
```

## AFTER — `static/css/identity.css`

```css
/* ---- Shared selection readout ---------------------------------------------
   Full-width sibling above .identity-panels. Distinct background/border
   from the (unlabeled) search inputs so it reads as a display, not an
   input. Same markup works at every viewport width — no breakpoint. */

.identity-selection {
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.75rem;
    border: 1px solid #0f766e;
    border-radius: 4px;
    background: #f0faf9;
    color: #1a1a1a;
    font-size: 0.9rem;
    font-weight: 500;
}

.identity-selection-placeholder {
    color: #9ca3af;
    font-weight: 400;
    font-style: italic;
}

/* ---- Panel search box ------------------------------------------------------
   No longer wrapped in .identity-panel-header — the detail button that
   lived there is gone (double-click on a row replaces it), so the search
   input is now a direct child of .identity-panel. */

.identity-search {
    width: 100%;
    box-sizing: border-box;
    padding: 4px 8px;
    border: 1px solid #dde1e7;
    border-radius: 3px;
    font-size: 0.875rem;
    font-family: inherit;
    background: #ffffff;
    color: #1a1a1a;
}

.identity-search:focus {
    outline: 2px solid #0f766e;
    outline-offset: -1px;
    border-color: #0f766e;
}
```

```css
.identity-item-name {
    font-weight: 500;
}
```

---

## Notes
- `.identity-panel-header`, `.identity-detail-btn`, `.identity-clear`,
  `.identity-item-hint` rules removed entirely — no longer referenced by
  the new markup. `#org-detail-btn` / `#contact-detail-btn` and their
  `deferred` click handlers are also gone from the JS; double-click now
  does that job.
- `.identity-panels` (the 2-column grid) and its `@media (max-width: 768px)`
  stacking rule are **unchanged** — per this session's decision, columns
  stay 50/50 at all widths since the selection box solves the visibility
  problem the stacking rule existed to work around. If you want to verify
  that stacking rule is now genuinely dead code, grep for it before
  deleting; not removed here since it does no harm left in place and this
  changedoc's scope is additive/replacement, not cleanup.
- `data-name` added to each `.identity-item` so the JS doesn't need to
  re-read `textContent` (which previously included the now-removed hint
  span) — cleaner separation between what's displayed and what's read
  programmatically.
- `openDetailPanel` / `openNewRecordPanel` are called via `window.` since
  `_tab_identities.html`'s script is a plain inline `<script>`, not a
  module — matches how `detail-panel.js` already exposes them
  (`window.openDetailPanel = ...` at the bottom of that file).
- **Not addressed here:** `_detail_panel.html`'s `contacts` branch on the
  Details tab still only has `name` and `title` fields — `notes` still
  needs adding, and the whole thing still depends on the `crew.py`
  contacts/organizations routes existing, which is the separate Python
  changedoc still to come.
