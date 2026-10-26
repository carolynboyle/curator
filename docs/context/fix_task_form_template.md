# Change Doc: Fix Task Form Template — None Display and Select Pre-population

**Problem:** Three bugs in `src/curator/templates/tasks/form.html`:

1. `notes` field displays "None" instead of empty when the DB value is NULL.
2. `links` field has the same potential issue (NULL → "None").
3. Status and Priority dropdowns never pre-select the current value on edit,
   because they compare `task.status_id` and `task.priority_id` against option
   IDs — but `v_tasks` returns resolved names (`task.status`, `task.priority`),
   not IDs.

**File changed:** `src/curator/templates/tasks/form.html`

---

### `notes` textarea value — BEFORE
```html
        <textarea id="notes"
                  name="notes"
                  placeholder="{{ field.placeholder or '' }}">{{ task.notes if task else '' }}</textarea>
```

### `notes` textarea value — AFTER
```html
        <textarea id="notes"
                  name="notes"
                  placeholder="{{ field.placeholder or '' }}">{{ task.notes or '' }}</textarea>
```

**Why:** `task.notes if task else ''` renders Python `None` as the string
`"None"` when the column is NULL. `task.notes or ''` correctly returns empty
string for both NULL and a missing task.

---

### `links` input value — BEFORE
```html
               value="{{ task.links if task else '' }}"
```

### `links` input value — AFTER
```html
               value="{{ task.links or '' }}"
```

**Why:** Same NULL → "None" issue as notes. Consistent fix.

---

### Status select — BEFORE
```html
            <option value="{{ opt.id }}"
                {% if task and task.status_id == opt.id %}selected{% endif %}>
                {{ opt.display }} {{ opt.name }}
            </option>
```

### Status select — AFTER
```html
            <option value="{{ opt.id }}"
                {% if task and task.status == opt.name %}selected{% endif %}>
                {{ opt.display }} {{ opt.name }}
            </option>
```

**Why:** `v_tasks` does not expose `status_id` — it resolves the join and
returns `status` (the name string). Comparing by name matches correctly.

---

### Priority select — BEFORE
```html
            <option value="{{ opt.id }}"
                {% if task and task.priority_id == opt.id %}selected{% endif %}>
                {{ opt.name }}
            </option>
```

### Priority select — AFTER
```html
            <option value="{{ opt.id }}"
                {% if task and task.priority == opt.name %}selected{% endif %}>
                {{ opt.name }}
            </option>
```

**Why:** Same as status — `v_tasks` returns `priority` (name string), not
`priority_id`.

---

## Notes

- No Python changes required — all fixes are in the template.
- No database changes required.
- The `description` textarea uses `{{ task.description if task else '' }}`
  which is fine since description is NOT NULL in the schema, so it will
  never be None.
