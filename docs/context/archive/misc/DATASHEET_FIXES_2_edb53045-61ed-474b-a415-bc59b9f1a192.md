# Datasheet Fixes — Clipboard, Row Padding, Grid Colors

**Date:** 2026-06-26  
**Files changed:**
1. `static/css/components/tabulator-overrides.css` — fix row padding, hardcode grid colors
2. `templates/_projects_table.html` — clipboard fallback for HTTP

---

## 1. `static/css/components/tabulator-overrides.css`

**WHY:** Two fixes in one:
- Row height: Tabulator's simple theme adds internal padding that fights our
  `height: 26px`. Setting `max-height` and removing padding from the row level
  (keeping it only on cells) fixes the bloated rows.
- Grid colors: replace all `var(--color-*)` references inside the grid with
  hardcoded light values so dark theme can never touch the datasheet.

**BEFORE** (lines 34–57, the row/cell section):
```css
/* ---- Data rows — compact ------------------------------------------ */

.tabulator .tabulator-row {
    min-height: 26px;
    border-bottom: 1px solid #e5e7eb;
}

.tabulator .tabulator-row .tabulator-cell {
    padding: 3px 8px;
    border-right: 1px solid #e5e7eb;
    height: 26px;
    line-height: 20px;
}

.tabulator .tabulator-row:hover {
    background: #f0faf9;
}

/* Alternating row stripes — pgAdmin style */
.tabulator .tabulator-row.tabulator-row-even {
    background: var(--color-surface, #fff);
}

.tabulator .tabulator-row.tabulator-row-odd {
    background: #fafafa;
}
```

**AFTER:**
```css
/* ---- Data rows — compact ------------------------------------------ */

.tabulator .tabulator-row {
    min-height: 0 !important;
    max-height: 26px !important;
    border-bottom: 1px solid #e5e7eb;
}

.tabulator .tabulator-row .tabulator-cell {
    padding: 3px 8px;
    border-right: 1px solid #e5e7eb;
    height: 26px;
    line-height: 20px;
    overflow: hidden;
}

.tabulator .tabulator-row:hover {
    background: #f0faf9;
}

/* Alternating row stripes — pgAdmin style */
.tabulator .tabulator-row.tabulator-row-even {
    background: #ffffff;
}

.tabulator .tabulator-row.tabulator-row-odd {
    background: #fafafa;
}
```

**BEFORE** (grid container and header, lines 9–31):
```css
.tabulator {
    border: 1px solid var(--color-border, #dde1e7);
    font-size: 0.875rem;
    background: var(--color-surface, #fff);
}

.tabulator .tabulator-header {
    border-bottom: 2px solid var(--color-border, #dde1e7);
    background: #f3f4f6;
    font-weight: 600;
}

.tabulator .tabulator-header .tabulator-col {
    background: #f3f4f6;
    border-right: 1px solid var(--color-border, #dde1e7);
}

.tabulator .tabulator-header .tabulator-col .tabulator-col-content {
    padding: 4px 8px;
}
```

**AFTER:**
```css
.tabulator {
    border: 1px solid #dde1e7;
    font-size: 0.875rem;
    background: #ffffff;
    color: #1a1a1a;
}

.tabulator .tabulator-header {
    border-bottom: 2px solid #dde1e7;
    background: #f3f4f6;
    color: #374151;
    font-weight: 600;
}

.tabulator .tabulator-header .tabulator-col {
    background: #f3f4f6;
    border-right: 1px solid #dde1e7;
}

.tabulator .tabulator-header .tabulator-col .tabulator-col-content {
    padding: 4px 8px;
}
```

**BEFORE** (header filter, lines 59–73):
```css
.tabulator .tabulator-header-filter input,
.tabulator .tabulator-header-filter select {
    width: 100%;
    padding: 2px 6px;
    margin: 0;
    border: 1px solid var(--color-border, #dde1e7);
    border-radius: 0;
    font-size: 0.85rem;
    font-family: inherit;
    height: auto;
    box-shadow: none;
    background: var(--color-surface, #fff);
    color: var(--color-text, #1a1a1a);
}
```

**AFTER:**
```css
.tabulator .tabulator-header-filter input,
.tabulator .tabulator-header-filter select {
    width: 100%;
    padding: 2px 6px;
    margin: 0;
    border: 1px solid #dde1e7;
    border-radius: 0;
    font-size: 0.85rem;
    font-family: inherit;
    height: auto;
    box-shadow: none;
    background: #ffffff;
    color: #1a1a1a;
}
```

**BEFORE** (cell editors, lines 75–92):
```css
.tabulator .tabulator-cell.tabulator-editing input,
.tabulator .tabulator-cell.tabulator-editing select {
    border: none;
    border-radius: 0;
    padding: 2px 6px;
    margin: 0;
    font-size: 0.85rem;
    font-family: inherit;
    width: 100%;
    box-shadow: none;
    background: var(--color-surface, #fff);
    color: var(--color-text, #1a1a1a);
    outline: 2px solid var(--color-primary, #0f766e);
    outline-offset: -2px;
}
```

**AFTER:**
```css
.tabulator .tabulator-cell.tabulator-editing input,
.tabulator .tabulator-cell.tabulator-editing select {
    border: none;
    border-radius: 0;
    padding: 2px 6px;
    margin: 0;
    font-size: 0.85rem;
    font-family: inherit;
    width: 100%;
    box-shadow: none;
    background: #ffffff;
    color: #1a1a1a;
    outline: 2px solid #0f766e;
    outline-offset: -2px;
}
```

---

## 2. `templates/_projects_table.html`

**WHY:** `navigator.clipboard.writeText()` is blocked on HTTP (localhost).
Replace the single clipboard call with a function that tries the modern API
first and falls back to the legacy `execCommand` method which works on HTTP,
HTTPS, and localhost with no permission dialog.

**BEFORE** (the `copySelectionToClipboard` function):
```javascript
    // Copy selected rows to clipboard as tab-separated values
    function copySelectionToClipboard() {
        if (selectedRows.size === 0) return;
        const lines = [];
        // Use table row order, not Set insertion order
        table.getRows().forEach(row => {
            if (!selectedRows.has(row)) return;
            const d = row.getData();
            const name      = d.name      || '';
            const type      = typeValues[d.type_id]   || '';
            const status    = statusValues[d.status_id] || '';
            lines.push([name, type, status].join('\t'));
        });
        navigator.clipboard.writeText(lines.join('\n')).catch(() => {
            // Clipboard API unavailable (non-HTTPS) — silently ignore
        });
    }
```

**AFTER:**
```javascript
    // Copy selected rows to clipboard as tab-separated values.
    // Tries the modern Clipboard API first (requires HTTPS or localhost with
    // permissions), falls back to the legacy execCommand method which works
    // on plain HTTP with no permission dialog.
    function copySelectionToClipboard() {
        if (selectedRows.size === 0) return;
        const lines = [];
        table.getRows().forEach(row => {
            if (!selectedRows.has(row)) return;
            const d = row.getData();
            const name   = d.name                    || '';
            const type   = typeValues[d.type_id]     || '';
            const status = statusValues[d.status_id] || '';
            lines.push([name, type, status].join('\t'));
        });
        const text = lines.join('\n');

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).catch(() => {
                _execCommandCopy(text);
            });
        } else {
            _execCommandCopy(text);
        }
    }

    // Legacy clipboard fallback — works on HTTP and localhost
    function _execCommandCopy(text) {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.top = '-9999px';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        try {
            document.execCommand('copy');
        } catch (err) {
            // execCommand also unavailable — nothing we can do
        }
        document.body.removeChild(ta);
    }
```

---

## Summary

| Fix | File | Lines changed |
|-----|------|---------------|
| Row height — 26px compact, no bloat | tabulator-overrides.css | ~6 |
| Grid colors hardcoded — theme-proof | tabulator-overrides.css | ~12 |
| Clipboard works on HTTP | _projects_table.html | ~20 |

No Python changes. No template structure changes. Restart uvicorn not required
— CSS and JS changes take effect on browser reload.
