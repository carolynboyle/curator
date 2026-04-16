# curator.css

**Path:** static/curator.css
**Syntax:** css
**Generated:** 2026-04-16 11:00:26

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
/* ==========================================================================
   Board split view
   Append to curator.css
   ========================================================================== */

/* -- Layout ---------------------------------------------------------------- */

.board-layout {
    display: flex;
    height: calc(100vh - 110px);   /* full height minus nav + footer */
    gap: 0;
    background: var(--color-surface);
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

/* -- Left panel ------------------------------------------------------------ */

.board-left {
    width: 240px;
    min-width: 240px;
    border-right: 1px solid var(--color-border);
    display: flex;
    flex-direction: column;
    background: var(--color-surface);
}

.board-left-header {
    padding: 8px 12px;
    border-bottom: 1px solid var(--color-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-muted);
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.board-add-btn {
    font-size: 1.1rem;
    line-height: 1;
    color: var(--color-muted);
    text-decoration: none;
    padding: 0 2px;
}

.board-add-btn:hover {
    color: var(--color-teal);
}

.board-list {
    flex: 1;
    overflow-y: auto;
    padding: 4px 0;
}

.board-list-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    cursor: pointer;
    font-size: 0.85rem;
    color: var(--color-text);
    border-left: 2px solid transparent;
    user-select: none;
}

.board-list-item:hover {
    background: #f3f4f6;
}

.board-list-item--active {
    background: #f0faf9;
    border-left-color: var(--color-teal);
}

.board-list-item--active .board-item-name {
    color: var(--color-teal);
    font-weight: 500;
}

.board-item-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--color-teal);
    flex-shrink: 0;
}

.board-item-name {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.board-indent-marker {
    color: var(--color-muted);
    font-size: 0.75rem;
}

/* -- Right panel ----------------------------------------------------------- */

.board-right {
    position: relative;
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.board-detail {
    flex: 1;
    overflow-y: auto;
    padding: 0;
}

.board-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--color-muted);
    font-size: 0.9rem;
    padding: 2rem;
}

/* -- Panel content --------------------------------------------------------- */

.panel-wrap {
    padding: 0 0 2rem 0;
}

.panel-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: 12px 16px 10px;
    border-bottom: 1px solid var(--color-border);
    position: sticky;
    top: 0;
    background: var(--color-surface);
    z-index: 1;
}

.panel-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--color-dark);
}

.panel-meta {
    font-size: 0.78rem;
    color: var(--color-muted);
    margin-top: 2px;
}

.panel-header-actions {
    display: flex;
    gap: 6px;
    align-items: center;
}

.panel-section {
    padding: 10px 16px 0;
}

.panel-section-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--color-muted);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

/* -- Inline editing -------------------------------------------------------- */

.panel-field {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
}

.panel-field label {
    font-size: 0.72rem;
    color: var(--color-muted);
    font-weight: 500;
}

.panel-field-display {
    font-size: 0.85rem;
    color: var(--color-text);
    padding: 4px 6px;
    border-radius: 4px;
    cursor: text;
    border: 1px solid transparent;
    min-height: 28px;
}

.panel-field-display:hover {
    border-color: var(--color-border);
    background: #f9fafb;
}

.panel-field-input {
    font-size: 0.85rem;
    padding: 4px 6px;
    border: 1px solid var(--color-teal);
    border-radius: 4px;
    background: var(--color-surface);
    width: 100%;
}

.panel-fields-row {
    display: flex;
    gap: 12px;
    margin-top: 8px;
    flex-wrap: wrap;
}

.panel-save-bar {
    display: flex;
    gap: 6px;
    padding: 8px 16px;
    border-top: 1px solid var(--color-border);
    margin-top: 8px;
    background: #f9fafb;
}

/* -- Tags ------------------------------------------------------------------ */

.panel-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
}

.badge-tag {
    background: var(--color-teal-light);
    color: var(--color-teal-dark);
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 20px;
    font-weight: 500;
}

/* -- Subforms -------------------------------------------------------------- */

.subform-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 0;
    margin-top: 12px;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--color-muted);
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.subform-body {
    margin-bottom: 4px;
}

.subform-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 0;
    border-bottom: 1px solid #f3f4f6;
    font-size: 0.84rem;
}

.subform-row:last-child {
    border-bottom: none;
}

.subform-row-name {
    flex: 1;
    color: var(--color-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.subform-row-name a {
    color: var(--color-teal);
    text-decoration: none;
}

.subform-row-name a:hover {
    text-decoration: underline;
}

.subform-row-meta {
    font-size: 0.75rem;
    color: var(--color-muted);
    white-space: nowrap;
}

.subform-row-edit {
    font-size: 0.78rem;
    color: var(--color-muted);
    text-decoration: none;
    opacity: 0;
    transition: opacity 0.1s;
}

.subform-row:hover .subform-row-edit {
    opacity: 1;
}

.subform-empty {
    font-size: 0.82rem;
    color: var(--color-muted);
    padding: 8px 0;
}

/* -- Task status select ---------------------------------------------------- */

.task-status-select {
    font-family: monospace;
    font-size: 0.78rem;
    padding: 1px 2px;
    border: 1px solid var(--color-border);
    border-radius: 3px;
    background: var(--color-surface);
    cursor: pointer;
    width: auto;
    flex-shrink: 0;
}

.task-done {
    color: var(--color-muted);
    text-decoration: line-through;
}

.task-pri-high     { color: #b45309; font-size: 0.72rem; }
.task-pri-blocking { color: var(--color-danger); font-size: 0.72rem; font-weight: 600; }
.task-pri-normal   { color: var(--color-muted); font-size: 0.72rem; }
.task-pri-low      { color: #9ca3af; font-size: 0.72rem; }
.board-list-child {
    border-left: 2px solid var(--color-teal-light);
    margin-left: 20px;
    padding-left: 12px !important;
}
.board-toggle {
    cursor: pointer;
    font-size: 0.9rem;
    color: var(--color-muted);
    width: 14px;
    flex-shrink: 0;
    user-select: none;
}

.board-toggle-spacer {
    width: 14px;
    flex-shrink: 0;
}

/* -- Task status badge ---------------------------------------------------- */

.task-status-badge {
    font-size: 0.72rem;
    padding: 1px 6px;
    border-radius: 3px;
    white-space: nowrap;
    flex-shrink: 0;
}

.task-status-open        { background: #dbeafe; color: #1e40af; }
.task-status-in-progress { background: #fef9c3; color: #92400e; }
.task-status-on-hold     { background: #fee2e2; color: #991b1b; }
.task-status-complete    { background: #dcfce7; color: #166534; }

/* -- Task dialog ---------------------------------------------------------- */

.task-dialog-backdrop {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
}

.task-dialog {
    background: var(--color-surface);
    border-radius: 6px;
    padding: 1.25rem;
    min-width: 300px;
    max-width: 480px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.task-dialog-title {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--color-dark);
    margin-bottom: 1rem;
    line-height: 1.4;
}

.task-dialog-field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 0.75rem;
}

.task-dialog-field label {
    font-size: 0.75rem;
    color: var(--color-muted);
    font-weight: 500;
}

.task-dialog-actions {
    display: flex;
    gap: 8px;
    margin-top: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--color-border);
}

.subform-footnote-marker {
    color: var(--color-teal);
    font-size: 0.7rem;
    vertical-align: super;
}

.subform-footnote {
    font-size: 0.72rem;
    color: var(--color-muted);
    padding: 2px 0 6px 0;
    font-style: italic;
}
```
