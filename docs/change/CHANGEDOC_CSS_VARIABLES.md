# Changedoc: CSS Theme Variables — Form & Button Colors

**Date:** 2026-06-27  
**Files affected:** `static/css/themes/light.css`, `static/css/themes/dark.css`  
**Reason:** Add form input and button color variables to support detail panel and future form components

---

## File 1: `static/css/themes/light.css`

### BEFORE

```css
/* =============================================================================
   Light Theme (default)
   App shell colors — WCYJ teal identity
   Crew workspace colors are in static/css/crew/{role}.css
   ============================================================================= */

:root {
    /* App shell — WCYJ teal */
    --color-primary:      #0f766e;
    --color-primary-dark: #0d6460;
    --color-primary-light:#ccebe9;

    /* Neutrals */
    --color-bg:           #f5f7fa;
    --color-surface:      #ffffff;
    --color-border:       #dde1e7;
    --color-text:         #1a1a1a;
    --color-text-light:   #6b7280;

    /* Semantic */
    --color-danger:       #dc2626;
    --color-danger-bg:    #fef2f2;
    --color-success:      #166534;
    --color-warning:      #b45309;
}
```

### AFTER

```css
/* =============================================================================
   Light Theme (default)
   App shell colors — WCYJ teal identity
   Crew workspace colors are in static/css/crew/{role}.css
   ============================================================================= */

:root {
    /* App shell — WCYJ teal */
    --color-primary:      #0f766e;
    --color-primary-dark: #0d6460;
    --color-primary-light:#ccebe9;

    /* Neutrals */
    --color-bg:           #f5f7fa;
    --color-surface:      #ffffff;
    --color-border:       #dde1e7;
    --color-text:         #1a1a1a;
    --color-text-light:   #6b7280;

    /* Semantic */
    --color-danger:       #dc2626;
    --color-danger-bg:    #fef2f2;
    --color-success:      #166534;
    --color-warning:      #b45309;

    /* Form inputs */
    --color-input-bg:     #ffffff;
    --color-input-border: #dde1e7;
    --color-input-text:   #1a1a1a;

    /* Buttons */
    --color-button-primary-bg:    #0f766e;
    --color-button-primary-text:  #ffffff;
    --color-button-secondary-bg:  #dde1e7;
    --color-button-secondary-text:#1a1a1a;
}
```

---

## File 2: `static/css/themes/dark.css`

### BEFORE

```css
/* =============================================================================
   Dark Theme
   Overrides light.css variables for dark mode readability
   ============================================================================= */

:root {
    /* App shell — dark backgrounds, light text */
    --color-primary:      #0f766e;  /* teal stays same for accent */
    --color-primary-dark: #0d6460;
    --color-primary-light:#20b2aa;  /* Lighter teal for dark theme contrast */

    /* Neutrals — inverted */
    --color-bg:           #1a1a1a;
    --color-surface:      #2a2a2a;
    --color-border:       #404040;
    --color-text:         #e5e5e5;
    --color-text-light:   #a0a0a0;

    /* Semantic */
    --color-danger:       #dc2626;
    --color-danger-bg:    #3a1a1a;
    --color-success:      #166534;
    --color-warning:      #b45309;
}
```

### AFTER

```css
/* =============================================================================
   Dark Theme
   Overrides light.css variables for dark mode readability
   ============================================================================= */

:root {
    /* App shell — dark backgrounds, light text */
    --color-primary:      #0f766e;  /* teal stays same for accent */
    --color-primary-dark: #0d6460;
    --color-primary-light:#20b2aa;  /* Lighter teal for dark theme contrast */

    /* Neutrals — inverted */
    --color-bg:           #1a1a1a;
    --color-surface:      #2a2a2a;
    --color-border:       #404040;
    --color-text:         #e5e5e5;
    --color-text-light:   #a0a0a0;

    /* Semantic */
    --color-danger:       #dc2626;
    --color-danger-bg:    #3a1a1a;
    --color-success:      #166534;
    --color-warning:      #b45309;

    /* Form inputs */
    --color-input-bg:     #3a3a3a;
    --color-input-border: #404040;
    --color-input-text:   #e5e5e5;

    /* Buttons */
    --color-button-primary-bg:    #0f766e;
    --color-button-primary-text:  #ffffff;
    --color-button-secondary-bg:  #3a3a3a;
    --color-button-secondary-text:#e5e5e5;
}
```

---

## Why These Changes

**Form inputs:** Light backgrounds with borders and dark text make form fields readable in both light and dark themes. In dark theme, the input background is slightly lighter than the page background so the input stands out.

**Buttons:** Primary button uses the teal accent color in both themes. Secondary buttons match the current background so they feel de-emphasized.

These variables will be used in `detail-panel.css` and any future form components, ensuring consistent theming without hardcoding colors.
