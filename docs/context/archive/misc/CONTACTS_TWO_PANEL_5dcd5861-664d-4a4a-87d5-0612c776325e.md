# Contacts Two-Panel Layout

**Date:** 2026-06-26  
**Scope:** Identities tab — two-panel org/contact listboxes with bidirectional
filtering, search, and Faker seed script. Detail edit form deferred.

**Files changed:**
1. `curator/web/routes/crew.py` — add contact/org fetch functions, pass to template
2. `templates/captain.html` — replace Identities tab with two-panel layout
3. `static/css/components/identity.css` — NEW: two-panel layout styles
4. `templates/base.html` — add identity.css link
5. `scripts/fake_contacts.py` — NEW: Faker seed script

---

## 1. `curator/web/routes/crew.py`

**WHY:** Add two fetch functions for contacts and organizations, and pass them
to the captain template. Contacts include their first email as a display hint.
Organizations include a list of their contact IDs for client-side filtering.

**BEFORE** (the `_fetch_lookups` function and everything above `crew_dashboard`):
```python
async def _fetch_lookups(db: AsyncDBConnection) -> dict:
    """Fetch project type and status lookup tables.

    Returns dict with 'types' and 'statuses' lists of dicts.
    Each dict has 'id' and 'name' keys.
    """
    types_sql = "SELECT id, name::text FROM projects.project_type ORDER BY name"
    statuses_sql = "SELECT id, name::text FROM projects.project_status ORDER BY name"

    types = await db.fetch_all(types_sql)
    statuses = await db.fetch_all(statuses_sql)

    return {
        "types": [dict(r) for r in types],
        "statuses": [dict(r) for r in statuses],
    }
```

**AFTER:**
```python
async def _fetch_lookups(db: AsyncDBConnection) -> dict:
    """Fetch project type and status lookup tables.

    Returns dict with 'types' and 'statuses' lists of dicts.
    Each dict has 'id' and 'name' keys.
    """
    types_sql = "SELECT id, name::text FROM projects.project_type ORDER BY name"
    statuses_sql = "SELECT id, name::text FROM projects.project_status ORDER BY name"

    types = await db.fetch_all(types_sql)
    statuses = await db.fetch_all(statuses_sql)

    return {
        "types": [dict(r) for r in types],
        "statuses": [dict(r) for r in statuses],
    }


async def _fetch_contacts(db: AsyncDBConnection) -> list:
    """Fetch all contacts with their first email address.

    Returns list of dicts: id, name, title, email, org_ids.
    org_ids is a list of organization IDs this contact belongs to.
    email is the first address from contact_emails, or None.
    """
    sql = """
        SELECT
            c.id,
            c.name::text,
            c.title::text,
            (
                SELECT ce.address::text
                FROM identity.contact_emails ce
                WHERE ce.contact_id = c.id
                ORDER BY ce.id
                LIMIT 1
            ) AS email,
            COALESCE(
                ARRAY_AGG(oc.organization_id) FILTER (WHERE oc.organization_id IS NOT NULL),
                '{}'
            ) AS org_ids
        FROM identity.contacts c
        LEFT JOIN identity.organization_contacts oc ON oc.contact_id = c.id
        GROUP BY c.id, c.name, c.title
        ORDER BY c.name
    """
    rows = await db.fetch_all(sql)
    result = []
    for r in rows:
        d = dict(r)
        # org_ids comes back as a PostgreSQL array — ensure it's a plain list
        d["org_ids"] = list(d["org_ids"]) if d["org_ids"] else []
        result.append(d)
    return result


async def _fetch_organizations(db: AsyncDBConnection) -> list:
    """Fetch all organizations with their contact IDs.

    Returns list of dicts: id, name, contact_ids.
    contact_ids is a list of contact IDs belonging to this org.
    """
    sql = """
        SELECT
            o.id,
            o.name::text,
            COALESCE(
                ARRAY_AGG(oc.contact_id) FILTER (WHERE oc.contact_id IS NOT NULL),
                '{}'
            ) AS contact_ids
        FROM identity.organizations o
        LEFT JOIN identity.organization_contacts oc ON oc.organization_id = o.id
        GROUP BY o.id, o.name
        ORDER BY o.name
    """
    rows = await db.fetch_all(sql)
    result = []
    for r in rows:
        d = dict(r)
        d["contact_ids"] = list(d["contact_ids"]) if d["contact_ids"] else []
        result.append(d)
    return result
```

**BEFORE** (the data dict inside `crew_dashboard`, captain branch):
```python
    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
    }
```

**AFTER:**
```python
    if role == "captain":
        contacts = await _fetch_contacts(db)
        organizations = await _fetch_organizations(db)
    else:
        contacts = []
        organizations = []

    data = {
        "role": role,
        "role_title": role_meta["title"] if role_meta else role.title(),
        "theme": config.get("ui", "theme"),
        "records": records,
        "search": search,
        "project_types": lookups["types"],
        "project_statuses": lookups["statuses"],
        "contacts": contacts,
        "organizations": organizations,
    }
```

---

## 2. `templates/captain.html` — REPLACE ENTIRE FILE

**WHY:** Replace the Identities tab sub-selector buttons and three separate
panels with a two-panel layout (orgs left, contacts right). Add bidirectional
filtering, search, and `⋯` detail button. Remove phantom `type` and `website`
fields from organizations (not in schema). Light background on all tab panels.

**REPLACE THE ENTIRE FILE WITH:**
```html
{% extends "base.html" %}

{% block title %}{{ role_title }} — Curator{% endblock %}

{% block content %}
<section class="crew-section">
    {% with
        role=role,
        hero_image="captain.png",
        title=role_title,
        show_back=true
    %}
        {% include "_crew_header.html" %}
    {% endwith %}

    <!-- Tab Navigation -->
    <div class="tabs">
        <button class="tab-btn active" data-tab="tab-projects">Projects</button>
        <button class="tab-btn" data-tab="tab-identities">Identities</button>
        <button class="tab-btn" data-tab="tab-configuration">Configuration</button>
    </div>

    <!-- Projects Tab -->
    <div id="tab-projects" class="tab-panel active">
        {% include "_projects_table.html" %}
    </div>

    <!-- Identities Tab -->
    <div id="tab-identities" class="tab-panel">
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
    </div>

    <!-- Configuration Tab -->
    <div id="tab-configuration" class="tab-panel">
        <div class="crew-content">
            <div class="empty-state">
                <p>Configuration options coming soon.</p>
            </div>
        </div>
    </div>
</section>

<!-- Embed data for Tabulator and identity panels -->
<script>
    window.projectTypes   = {{ project_types  | tojson }};
    window.projectStatuses = {{ project_statuses | tojson }};

    // -------------------------------------------------------------------------
    // Tab switching
    // -------------------------------------------------------------------------
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(this.dataset.tab).classList.add('active');
            this.classList.add('active');
        });
    });

    // -------------------------------------------------------------------------
    // Identity panel — bidirectional filtering
    // -------------------------------------------------------------------------
    let selectedOrgId      = null;
    let selectedContactId  = null;

    const orgListbox     = document.getElementById('org-listbox');
    const contactListbox = document.getElementById('contact-listbox');
    const orgSearch      = document.getElementById('org-search');
    const contactSearch  = document.getElementById('contact-search');
    const orgDetailBtn   = document.getElementById('org-detail-btn');
    const contactDetailBtn = document.getElementById('contact-detail-btn');

    // -- Helpers --------------------------------------------------------------

    function getOrgItems()     { return orgListbox.querySelectorAll('.identity-item'); }
    function getContactItems() { return contactListbox.querySelectorAll('.identity-item'); }

    function showClearPill(inputEl, onClear) {
        // Remove any existing pill
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
        // Deselect previous
        getOrgItems().forEach(i => i.classList.remove('selected'));

        selectedOrgId = item.dataset.id;
        item.classList.add('selected');
        orgSearch.value = item.textContent.trim();
        orgDetailBtn.disabled = false;

        // Filter contacts to this org's contacts
        const contactIds = item.dataset.contactIds
            ? item.dataset.contactIds.split(',').filter(Boolean)
            : [];

        getContactItems().forEach(c => {
            setItemVisible(c, contactIds.includes(c.dataset.id));
        });

        showClearPill(orgSearch, clearOrgSelection);

        // Clear contact selection
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
        // Reapply contact search if any
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

        // Filter orgs to this contact's orgs
        const orgIds = item.dataset.orgIds
            ? item.dataset.orgIds.split(',').filter(Boolean)
            : [];

        getOrgItems().forEach(o => {
            setItemVisible(o, orgIds.length === 0 ? false : orgIds.includes(o.dataset.id));
        });

        showClearPill(contactSearch, clearContactSelection);

        // Clear org selection
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
        // Reapply org search if any
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

    // Detail buttons — wired up but form deferred
    orgDetailBtn.addEventListener('click', () => {
        // Future: open org detail form for selectedOrgId
    });

    contactDetailBtn.addEventListener('click', () => {
        // Future: open contact detail form for selectedContactId
    });

    // Add buttons — wired up but form deferred
    document.getElementById('org-add-btn').addEventListener('click', () => {
        // Future: open new org form
    });

    document.getElementById('contact-add-btn').addEventListener('click', () => {
        // Future: open new contact form
    });

</script>
{% endblock %}
```

---

## 3. `static/css/components/identity.css` — NEW FILE

**WHY:** Styles for the two-panel identity layout. Kept separate from
tabulator-overrides.css and tabs.css so each file has one clear job.

**Create this file:**
```css
/* =============================================================================
   identity.css — Two-panel org/contact layout for Identities tab
   ============================================================================= */

/* ---- Two-panel container -------------------------------------------------- */

.identity-panels {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    padding: 1rem 0;
    background: #f5f7fa;
}

/* ---- Individual panel ----------------------------------------------------- */

.identity-panel {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    background: #ffffff;
    border: 1px solid #dde1e7;
    border-radius: 4px;
    padding: 0.75rem;
}

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

/* ---- Add button ----------------------------------------------------------- */

.identity-add-btn {
    align-self: flex-start;
    padding: 3px 10px;
    border: 1px solid #0f766e;
    border-radius: 3px;
    background: none;
    color: #0f766e;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.15s;
}

.identity-add-btn:hover {
    background: #0f766e;
    color: #ffffff;
}

/* ---- Listbox -------------------------------------------------------------- */

.identity-listbox {
    border: 1px solid #dde1e7;
    border-radius: 3px;
    overflow-y: auto;
    max-height: 400px;
    background: #ffffff;
    font-size: 0.875rem;
}

/* ---- List items ----------------------------------------------------------- */

.identity-item {
    display: flex;
    flex-direction: column;
    padding: 4px 8px;
    border-bottom: 1px solid #f0f0f0;
    cursor: pointer;
    line-height: 1.3;
    color: #1a1a1a;
}

.identity-item:last-child {
    border-bottom: none;
}

.identity-item:hover {
    background: #f0faf9;
}

.identity-item.selected {
    background: #dbeafe;
    color: #1e3a5f;
}

.identity-item.selected:hover {
    background: #bfdbfe;
}

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

/* ---- Empty state ---------------------------------------------------------- */

.identity-empty {
    padding: 1rem;
    color: #9ca3af;
    font-size: 0.875rem;
    text-align: center;
}

/* ---- Tab panel light background ------------------------------------------ */

.tab-panel {
    background: #f5f7fa;
}

.tab-panel .crew-content {
    background: #ffffff;
    padding: 1rem;
}

/* ---- Responsive ----------------------------------------------------------- */

@media (max-width: 768px) {
    .identity-panels {
        grid-template-columns: 1fr;
    }
}
```

---

## 4. `templates/base.html`

**WHY:** Add the new identity.css link.

**BEFORE:**
```html
    <link rel="stylesheet" href="/static/css/components/datasheet.css">
```

**AFTER:**
```html
    <link rel="stylesheet" href="/static/css/components/datasheet.css">
    <link rel="stylesheet" href="/static/css/components/identity.css">
```

---

## 5. `scripts/fake_contacts.py` — NEW FILE

**WHY:** Generate realistic test data for contacts, organizations, and their
relationships using Faker. Run once against the dev database.

**Install Faker first:**
```bash
pip install faker --break-system-packages
```

**Create `scripts/fake_contacts.py`:**
```python
"""Seed script — generate fake contacts and organizations for development.

Usage:
    python scripts/fake_contacts.py

Reads database connection from ~/.config/dev-utils/config.yaml (same as app).
Inserts into identity.contacts, identity.organizations,
and identity.organization_contacts.

Safe to run multiple times — checks for existing data before inserting.
"""

import asyncio
import random
import sys
from pathlib import Path

from faker import Faker

# Add project root to path so curator imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from dbkit.connection import AsyncDBConnection
from curator.config import ConfigManager

fake = Faker()

NUM_ORGS     = 15
NUM_CONTACTS = 40


async def seed(db: AsyncDBConnection) -> None:
    """Insert fake orgs and contacts if tables are empty."""

    # -- Check existing data --------------------------------------------------
    existing_orgs = await db.fetch_one("SELECT COUNT(*) AS n FROM identity.organizations")
    existing_contacts = await db.fetch_one("SELECT COUNT(*) AS n FROM identity.contacts")

    if existing_orgs["n"] > 0 or existing_contacts["n"] > 0:
        print(f"Data already exists: {existing_orgs['n']} orgs, "
              f"{existing_contacts['n']} contacts. Skipping seed.")
        print("Delete existing rows first if you want to re-seed.")
        return

    # -- Insert organizations -------------------------------------------------
    org_ids = []
    for _ in range(NUM_ORGS):
        result = await db.fetch_one(
            """
            INSERT INTO identity.organizations (name, notes)
            VALUES (%s, %s)
            RETURNING id
            """,
            (fake.company(), fake.catch_phrase())
        )
        org_ids.append(result["id"])
        print(f"  org {result['id']} inserted")

    # -- Insert contacts ------------------------------------------------------
    contact_ids = []
    for _ in range(NUM_CONTACTS):
        result = await db.fetch_one(
            """
            INSERT INTO identity.contacts (name, title, notes)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (fake.name(), fake.job(), fake.sentence())
        )
        cid = result["id"]
        contact_ids.append(cid)
        print(f"  contact {cid} inserted")

        # Add a primary email
        await db.execute(
            """
            INSERT INTO identity.contact_emails (contact_id, label, address)
            VALUES (%s, %s, %s)
            """,
            (cid, "work", fake.email())
        )

        # Add a phone (70% of contacts)
        if random.random() < 0.7:
            await db.execute(
                """
                INSERT INTO identity.contact_phones (contact_id, label, number)
                VALUES (%s, %s, %s)
                """,
                (cid, "work", fake.phone_number())
            )

    # -- Link contacts to orgs (most contacts belong to one org) --------------
    used_pairs = set()
    for cid in contact_ids:
        # 80% of contacts belong to at least one org
        if random.random() < 0.8:
            org_id = random.choice(org_ids)
            pair = (org_id, cid)
            if pair not in used_pairs:
                used_pairs.add(pair)
                await db.execute(
                    """
                    INSERT INTO identity.organization_contacts (organization_id, contact_id)
                    VALUES (%s, %s)
                    """,
                    (org_id, cid)
                )

        # 20% of contacts belong to a second org
        if random.random() < 0.2:
            org_id = random.choice(org_ids)
            pair = (org_id, cid)
            if pair not in used_pairs:
                used_pairs.add(pair)
                await db.execute(
                    """
                    INSERT INTO identity.organization_contacts (organization_id, contact_id)
                    VALUES (%s, %s)
                    """,
                    (org_id, cid)
                )

    print(f"\nDone. {NUM_ORGS} organizations, {NUM_CONTACTS} contacts seeded.")


async def main() -> None:
    """Load config and run seed."""
    config = ConfigManager()
    db = AsyncDBConnection(config)
    await db.connect()
    try:
        await seed(db)
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Apply order

1. Edit `crew.py` — add two fetch functions, update data dict (restart uvicorn)
2. Create `static/css/components/identity.css`
3. Edit `templates/base.html` — add identity.css link
4. Replace `templates/captain.html`
5. Run `pip install faker --break-system-packages`
6. Run `python scripts/fake_contacts.py` to seed test data
7. Browser reload

---

## Behavior after changes

| Action | Result |
|--------|--------|
| Load Identities tab | All orgs left, all contacts right |
| Type in org search | Filters org list, clears any selection |
| Click an org | Org name fills search box, contacts filter to that org's contacts, × pill appears |
| Click × pill on org | Resets both panels to show all |
| Click same org again | Also resets (toggle deselect) |
| Click a contact | Contact name fills search box, org list filters to that contact's orgs (empty if none), × pill appears |
| Click × pill on contact | Resets both panels |
| ⋯ button | Disabled until selection made, then activates (detail form deferred) |
| + button | Wired but form deferred |
| No org selected, type in contact search | Filters contacts only |
