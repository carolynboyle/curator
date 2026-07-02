# Changedoc: Identities tab — extract bidirectional filter into shared module

**Supersedes:** `CHANGEDOC_IDENTITY_PANEL_REDESIGN.md` (not yet applied —
this replaces it, don't apply both)

**Files:**
- **New:** `static/js/bidirectional-filter.js` (see separate file —
  `initBidirectionalFilter()`, generic two-listbox cross-filter module)
- `templates/partials/_tab_identities.html` — now consumes the shared
  module instead of containing its own inline state machine
- `static/css/identity.css` — unchanged from the prior changedoc (shared
  selection box, single-field rows, no detail buttons); not repeated here

**Reason:** The org↔contact cross-filter logic (select one list, filter
the other, shared selection readout, dblclick-to-detail, add button) is a
general pattern — any two entities connected by a relationship could reuse
it (e.g. a future Projects ↔ Contacts tab). Extracting now, before a second
consumer exists, on the reasoning that retrofitting this generalization
later risks breaking a working Identities tab; building the reusable shape
in now with only one real consumer costs a bit of upfront design (config
object shape) but zero regression risk.

The generalization required one markup change: `data-contact-ids` /
`data-org-ids` (attribute names specific to which side they're on) become
a single `data-related-ids` on both sides, since the shared module doesn't
know or care which side is "organizations" and which is "contacts" — it
just needs each item to point at related ids in the *other* list.

---

## BEFORE — `templates/partials/_tab_identities.html`

*(This is the AFTER version from `CHANGEDOC_IDENTITY_PANEL_REDESIGN.md` —
the target state that changedoc produced, now being replaced before it was
ever applied.)*

```html
<div class="identity-selection" id="identity-selection">
    <span class="identity-selection-placeholder">No selection</span>
</div>

<div class="identity-panels">

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
// [~140 lines of inline state machine — selectOrg/selectContact,
//  clearOrgSelection/clearContactSelection, applyOrgSearch/applyContactSearch,
//  event listeners — see CHANGEDOC_IDENTITY_PANEL_REDESIGN.md for full text]
</script>
```

## AFTER — `templates/partials/_tab_identities.html`

```html
{#
  _tab_identities.html

  Identities tab content — visibility controlled by _ROLE_TABS (currently captain only; adding a role here means adding its entry there, full org-wide list, no filtering).

  Add/edit vs. delete permission is a separate, finer-grained check planned for the RLS implementation (based on identity.user_role, not crew_role) — not yet built. When that lands, delete controls should not render for non-admin users, and the underlying proc should reject unauthorized deletes quietly (standard {"success": false, ...} envelope, no special handling).

  Two-panel bidirectional org/contact filtering layout. Cross-filter behavior delegated to the shared bidirectional-filter.js module — see that file for the reusable pattern.

  Variables available from crew.html context:
    - organizations (list): list of dicts with id, name, contact_ids
    - contacts (list): list of dicts with id, name, title, email, org_ids
#}

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
                 data-related-ids="{{ org.contact_ids | join(',') }}">
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
                 data-related-ids="{{ contact.org_ids | join(',') }}">
                {{ contact.name or "—" }}
            </div>
            {% else %}
            <div class="identity-empty">No contacts found.</div>
            {% endfor %}
        </div>
    </div>

</div>

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

---

## Verify the static JS path

`crew.html` and other templates reference static assets under `/static/js/`
(e.g. `detail-panel.js` is presumably served from there, given `_tab_identities.html`'s
prior module-free inline script never needed an import path). Confirm
`bidirectional-filter.js` should land at `static/js/bidirectional-filter.js`
to match — if your static mount point differs, the `import` path in the
`<script type="module">` block above needs to match it exactly.

---

## Notes
- `identity.css` changes from the prior changedoc still apply as-is —
  nothing about the CSS changes with this extraction, only the JS
  structure and one HTML attribute name (`data-related-ids`).
- `left`/`right` in the config object are just labels for "the two sides" —
  no directional meaning, the module treats them symmetrically. Naming
  them `left`/`right` (rather than e.g. `primary`/`secondary`) was chosen
  to map intuitively to the visual layout, but a future consumer isn't
  required to think about it that way.
- If a Projects ↔ Contacts tab gets built later, it reuses this same
  module — just a new `initBidirectionalFilter({...})` call with different
  ids/entities, and the `project_contacts` junction data shaped into the
  same `data-related-ids` convention on both sides.
