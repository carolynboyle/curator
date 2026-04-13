# curator.css

**Path:** static/curator.css
**Syntax:** css
**Generated:** 2026-04-12 14:34:39

```css
/*
 * curator.css - The Curator UI theme
 *
 * Layers WCYJ brand colors on top of Pico CSS.
 * Pico is loaded from CDN in base.html.
 *
 * Palette:
 *   Teal:       #0f766e  — primary actions, links, active states
 *   Near-black: #171717  — nav, footer, strong contrast
 *   Background: #e5e5e5  — page background
 *   White:      #ffffff  — cards, form surfaces
 */

/* -- CSS variables -------------------------------------------------------- */

:root {
    --color-teal:       #0f766e;
    --color-teal-dark:  #0d6460;
    --color-teal-light: #ccebe9;
    --color-dark:       #171717;
    --color-bg:         #e5e5e5;
    --color-surface:    #ffffff;
    --color-text:       #1a1a1a;
    --color-muted:      #6b7280;
    --color-border:     #d1d5db;
    --color-danger:     #dc2626;
    --color-danger-bg:  #fef2f2;

    --pico-primary:             var(--color-teal);
    --pico-primary-hover:       var(--color-teal-dark);
    --pico-background-color:    var(--color-bg);
    --pico-card-background-color: var(--color-surface);
}

/* -- Base ----------------------------------------------------------------- */

body {
    background-color: var(--color-bg);
    color: var(--color-text);
}

/* -- Navigation ----------------------------------------------------------- */

nav.curator-nav {
    background-color: var(--color-dark);
    padding: 0.75rem 1.5rem;
    display: flex;
    align-items: center;
    gap: 2rem;
}

nav.curator-nav .nav-brand {
    color: var(--color-surface);
    font-weight: 700;
    font-size: 1.1rem;
    text-decoration: none;
    letter-spacing: 0.02em;
}

nav.curator-nav a {
    color: #d1d5db;
    text-decoration: none;
    font-size: 0.9rem;
    transition: color 0.15s;
}

nav.curator-nav a:hover,
nav.curator-nav a.active {
    color: var(--color-teal-light);
}

/* -- Main content --------------------------------------------------------- */

main.curator-main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem;
}

/* -- Page header ---------------------------------------------------------- */

.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    padding-bottom: 0.75rem;
    border-bottom: 2px solid var(--color-teal);
}

.page-header h1 {
    margin: 0;
    font-size: 1.5rem;
    color: var(--color-dark);
}

/* -- Buttons -------------------------------------------------------------- */

.btn-primary {
    background-color: var(--color-teal);
    color: var(--color-surface);
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    text-decoration: none;
    display: inline-block;
    transition: background-color 0.15s;
}

.btn-primary:hover {
    background-color: var(--color-teal-dark);
    color: var(--color-surface);
}

.btn-secondary {
    background-color: transparent;
    color: var(--color-teal);
    border: 1px solid var(--color-teal);
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    text-decoration: none;
    display: inline-block;
    transition: all 0.15s;
}

.btn-secondary:hover {
    background-color: var(--color-teal-light);
}

.btn-danger {
    background-color: var(--color-danger);
    color: var(--color-surface);
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: opacity 0.15s;
}

.btn-danger:hover {
    opacity: 0.85;
}

.btn-sm {
    padding: 0.25rem 0.6rem;
    font-size: 0.8rem;
}

/* -- Tables --------------------------------------------------------------- */

.curator-table {
    width: 100%;
    border-collapse: collapse;
    background-color: var(--color-surface);
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.curator-table th {
    background-color: var(--color-dark);
    color: var(--color-surface);
    padding: 0.65rem 1rem;
    text-align: left;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}

.curator-table td {
    padding: 0.6rem 1rem;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.9rem;
    vertical-align: middle;
}

.curator-table tr:last-child td {
    border-bottom: none;
}

.curator-table tr:hover td {
    background-color: #f3f4f6;
}

.curator-table a {
    color: var(--color-teal);
    text-decoration: none;
    font-weight: 500;
}

.curator-table a:hover {
    text-decoration: underline;
}

/* -- Forms ---------------------------------------------------------------- */

.curator-form {
    background-color: var(--color-surface);
    padding: 1.5rem;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    max-width: 680px;
}

.form-actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--color-border);
}

.field-help {
    font-size: 0.8rem;
    color: var(--color-muted);
    margin-top: 0.2rem;
}

/* -- Cards ---------------------------------------------------------------- */

.curator-card {
    background-color: var(--color-surface);
    border-radius: 6px;
    padding: 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    margin-bottom: 1rem;
}

.curator-card h3 {
    margin: 0 0 0.75rem 0;
    font-size: 1rem;
    color: var(--color-dark);
    border-bottom: 1px solid var(--color-border);
    padding-bottom: 0.5rem;
}

/* -- Status badges -------------------------------------------------------- */

.badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    font-size: 0.78rem;
    font-weight: 600;
    font-family: monospace;
}

.badge-open     { background-color: #dbeafe; color: #1e40af; }
.badge-progress { background-color: #fef9c3; color: #92400e; }
.badge-hold     { background-color: #fee2e2; color: #991b1b; }
.badge-complete { background-color: #dcfce7; color: #166534; }

/* -- Section headers ------------------------------------------------------ */

.section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 1.5rem 0 0.75rem;
}

.section-header h2 {
    font-size: 1.1rem;
    margin: 0;
    color: var(--color-dark);
}

/* -- Export link ---------------------------------------------------------- */

.export-link {
    color: var(--color-muted);
    font-size: 0.82rem;
    text-decoration: none;
}

.export-link:hover {
    color: var(--color-teal);
}

/* -- Confirm delete ------------------------------------------------------- */

.confirm-delete {
    background-color: var(--color-danger-bg);
    border: 1px solid var(--color-danger);
    border-radius: 4px;
    padding: 1rem;
    margin-top: 0.5rem;
}

/* -- Footer --------------------------------------------------------------- */

footer.curator-footer {
    background-color: var(--color-dark);
    color: #9ca3af;
    text-align: center;
    padding: 1rem;
    font-size: 0.8rem;
    margin-top: 3rem;
}

/* -- Task tree indentation ------------------------------------------------ */

.task-depth-0 { padding-left: 0; }
.task-depth-1 { padding-left: 1.5rem; }
.task-depth-2 { padding-left: 3rem; }
.task-depth-3 { padding-left: 4.5rem; }

.task-indent-marker {
    color: var(--color-muted);
    margin-right: 0.4rem;
}

/* -- Empty state ---------------------------------------------------------- */

.empty-state {
    text-align: center;
    color: var(--color-muted);
    padding: 2rem;
    font-size: 0.9rem;
}
```
