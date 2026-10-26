# Captain's Projects Tab — DRY Refactor

## Goal

Extract the shared projects table (search box + table structure) into a single
reusable partial so both `crew.html` (other roles) and `captain.html` (Captain's
Projects tab) use the same source. Change the layout once, and every role updates.

Also fixes: colorful pencil emoji everywhere, no icon backgrounds on Captain's
page (by using the `crew-table` class that forms.css targets), and matching row
heights across all forms.

---

## Partial Hierarchy

```
_projects_table.html   ← NEW: search box + table shell (the reusable piece)
  └── _crew_rows.html        ← existing: the {% for record %} loop
        └── _crew_row_display.html   ← existing: one display row
```

`crew.html` and `captain.html` both include `_projects_table.html`.

---

## File Changes Summary

| File | Action | Purpose |
|------|--------|---------|
| `templates/_projects_table.html` | Create | Shared search + table shell |
| `templates/crew.html` | Modify | Replace inline table with include |
| `templates/captain.html` | Modify | Replace Projects tab inline table with include; fix script vars |
| `templates/_crew_row_display.html` | Modify | Colorful pencil emoji (✏ → ✏️) |

---

## 1. Create `src/curator/templates/_projects_table.html`

This is the shared piece — the search box and table that both crew.html and
captain.html were duplicating.

```html
<div class="crew-content">
    <input
        type="search"
        name="search"
        placeholder="Search projects..."
        value="{{ search }}"
        hx-get="/crew"
        hx-trigger="keyup changed delay:300ms"
        hx-target="#crew-rows"
        hx-include="[name='search']"
        hx-vals='{"role": "{{ role }}"}'
    >

    <table class="crew-table">
        <thead>
            <tr>
                <th class="icon-col"></th>
                <th>
                    <button
                        class="add-icon"
                        hx-get="/crew/projects/new?role={{ role }}"
                        hx-target="#crew-rows"
                        hx-swap="afterbegin"
                        title="Add project"
                    >+</button>
                    Name
                </th>
                <th>Type</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody id="crew-rows">
            {% include "_crew_rows.html" %}
        </tbody>
    </table>
</div>
```

---

## 2. Modify `src/curator/templates/crew.html`

### BEFORE

```html
{% extends "base.html" %}

{% block title %}{{ role_title }} — Curator{% endblock %}

{% block content %}
<section class="crew-section {{ role }}">

    <div class="crew-header crew-card {{ role }}">
        <h1>{{ role_title }}</h1>
        <a href="/" class="btn-back">← Back to Crew</a>
    </div>

    <div class="crew-content">
        <input
            type="search"
            name="search"
            placeholder="Search projects..."
            value="{{ search }}"
            hx-get="/crew"
            hx-trigger="keyup changed delay:300ms"
            hx-target="#crew-rows"
            hx-include="[name='search']"
            hx-vals='{"role": "{{ role }}"}'
        >

        <table class="crew-table">
            <thead>
                <tr>
                    <th class="icon-col"></th>
                    <th>
                        <button
                            class="add-icon"
                            hx-get="/crew/projects/new?role={{ role }}"
                            hx-target="#crew-rows"
                            hx-swap="afterbegin"
                            title="Add project"
                        >+</button>
                        Name
                    </th>
                    <th>Type</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="crew-rows">
                {% include "_crew_rows.html" %}
            </tbody>
        </table>
    </div>

</section>

<!-- Embed lookups as data for access in partials -->
<script>
    window.projectTypes = {{ project_types | tojson }};
    window.projectStatuses = {{ project_statuses | tojson }};
</script>
{% endblock %}
```

### AFTER

```html
{% extends "base.html" %}

{% block title %}{{ role_title }} — Curator{% endblock %}

{% block content %}
<section class="crew-section {{ role }}">

    <div class="crew-header crew-card {{ role }}">
        <h1>{{ role_title }}</h1>
        <a href="/" class="btn-back">← Back to Crew</a>
    </div>

    {% include "_projects_table.html" %}

</section>

<!-- Embed lookups as data for access in partials -->
<script>
    window.projectTypes = {{ project_types | tojson }};
    window.projectStatuses = {{ project_statuses | tojson }};
</script>
{% endblock %}
```

### What Changed

- Replaced the entire `<div class="crew-content">...</div>` block (search + table)
  with a single `{% include "_projects_table.html" %}`
- Everything else unchanged

---

## 3. Modify `src/curator/templates/captain.html`

Two changes: replace the Projects tab inline table with the include, and fix the
script variables to use `window.` prefix (so partials can read them, matching
crew.html).

### Change 3a — Projects Tab

#### BEFORE

```html
        <!-- Projects Tab -->
        <div id="tab-projects" class="tab-panel active">
            <div class="crew-content">
                <div style="margin-bottom: 1.5rem;">
                    <input type="text" id="search-input" placeholder="Search projects..." 
                           hx-get="/crew" 
                           hx-target="#crew-rows" 
                           hx-include="[name='role']"
                           hx-trigger="input changed delay:300ms"
                           value="{{ search }}"
                           style="width: 100%;">
                    <input type="hidden" name="role" value="{{ role }}">
                </div>

                {% if records %}
                    <table class="records-table">
                        <thead>
                            <tr>
                                <th></th>
                                <th>Name
                                    <button class="add-icon" 
                                            hx-get="/crew/projects/new?role={{ role }}" 
                                            hx-target="#crew-rows" 
                                            hx-swap="afterbegin"
                                            title="Add project">+</button>
                                </th>
                                <th>Type</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="crew-rows">
                            {% for record in records %}
                            <tr class="project-row" id="display-row-{{ record['id'] }}">
                                <td class="icon-col">
                                    <button class="edit-icon" 
                                            hx-get="/crew/projects/{{ record['id'] }}/edit-form" 
                                            hx-target="#display-row-{{ record['id'] }}" 
                                            hx-swap="outerHTML"
                                            title="Edit">✏️</button>
                                    <button class="detail-icon" title="Details" disabled>⋯</button>
                                </td>
                                <td>{{ record["name"] }}</td>
                                <td>{{ record["type"] or "—" }}</td>
                                <td>{{ record["status"] }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <div class="empty-state">
                        <p>No projects found.</p>
                    </div>
                {% endif %}
            </div>
        </div>
```

#### AFTER

```html
        <!-- Projects Tab -->
        <div id="tab-projects" class="tab-panel active">
            {% include "_projects_table.html" %}
        </div>
```

### Change 3b — Script Variables

#### BEFORE

```html
<script>
    // Embed lookup tables for inline edit/add forms
    const projectTypes = {{ project_types | tojson }};
    const projectStatuses = {{ project_statuses | tojson }};

    // Main tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
```

#### AFTER

```html
<script>
    // Embed lookup tables for inline edit/add forms
    window.projectTypes = {{ project_types | tojson }};
    window.projectStatuses = {{ project_statuses | tojson }};

    // Main tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
```

### What Changed

- **3a:** Replaced the entire custom Projects table (~45 lines) with a single
  `{% include "_projects_table.html" %}`. This makes Captain's Projects tab use
  the `crew-table` class (so forms.css applies — no backgrounds, hover works,
  correct row height) and the same row partials (consistent icons on load and
  after edit/cancel).
- **3b:** Changed `const` to `window.` so the lookup variables are globally
  accessible to partials, matching crew.html's pattern.

---

## 4. Modify `src/curator/templates/_crew_row_display.html`

Use the colorful pencil emoji (with variation selector) instead of the plain one.

### BEFORE

```html
        <button
            class="edit-icon"
            hx-get="/crew/projects/{{ record.id }}/edit-form"
            hx-target="closest tr"
            hx-swap="outerHTML"
            title="Edit project"
        >✏</button>
```

### AFTER

```html
        <button
            class="edit-icon"
            hx-get="/crew/projects/{{ record.id }}/edit-form"
            hx-target="closest tr"
            hx-swap="outerHTML"
            title="Edit project"
        >✏️</button>
```

### What Changed

- `✏` → `✏️` (added the emoji variation selector U+FE0F for the colorful
  rendering). Since every role renders rows through this partial, the colorful
  pencil now appears everywhere consistently.

---

## Why This Is Better (DRY)

**Before:** The search box and table markup lived in two places — crew.html and
captain.html — and they had drifted (different class names, different icon
emoji, different search wiring). That drift is exactly what caused the
background/row-height/icon inconsistencies.

**After:** One source of truth — `_projects_table.html`. Both templates include
it. Change the layout once and every role (plus Captain's Projects tab) updates
together. No drift possible.

**The nesting also stays DRY:**
```
_projects_table.html   (search + table shell)
  └── _crew_rows.html        (the loop)
        └── _crew_row_display.html   (one row, with the colorful pencil)
```

Each layer is independently reusable.

---

## Testing Checklist

- [ ] Captain's Projects tab: icons have NO backgrounds (match other roles)
- [ ] Captain's Projects tab: row heights match other roles
- [ ] Captain's Projects tab: colorful pencil ✏️ on load
- [ ] Captain's Projects tab: colorful pencil ✏️ still there after edit→cancel
- [ ] Captain's Projects tab: pencil opens edit form, Save writes, Cancel reverts
- [ ] Captain's Projects tab: + button adds a new row
- [ ] Captain's Projects tab: search filters rows
- [ ] Other roles (scribe/mechanic/envoy): everything still works unchanged
- [ ] Icons hidden until row hover (desktop), always visible on touch
