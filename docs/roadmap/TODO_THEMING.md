# Theming — Skinnable Forms

Logged 2026-11-27. **Not started, deliberately.** Get everything working first;
make it pretty later. This file exists so we keep the goal in mind meanwhile.

## Goal

Pick a theme for Curator and have every form, grid and popup change through CSS
alone, with no changes to the forms themselves.

## Where things stand

- `static/css/themes/light.css` and `dark.css` exist; `base.html` loads
  `themes/{{ theme | default('light') }}.css`.
- A theme is a set of CSS variables (`--color-bg`, `--color-input-bg`, ...);
  `dark.css` overrides the light values.
- Most component CSS already uses the variables.
- Roughly 90 raw colour values remain (counted 2026-11-27):
  `tabulator-overrides.css` ~26, `identity.css` ~27, `datasheet.css` ~17,
  `base.css` ~13, a few elsewhere.
- JavaScript has not been audited for inline colours.

## Rule while building (applies now)

New CSS uses theme variables only. No hex or rgb() values in new component CSS.

## What the project would involve

1. Replace remaining hard-coded colours with variables (grids first).
2. Define the full variable list: colours plus spacing, radius, fonts, shadows,
   control sizes, so a theme can change the look and not only the palette.
3. Make the Tabulator grid overrides use the variables.
4. Audit JavaScript for inline styles/colours; move them to classes.
5. A theme picker; remember the choice per user (user config first, database
   once the Captain role exists).
6. Tests: every theme defines every variable; flag new hard-coded colours.

## Limits

A theme changes appearance only. Rearranging layout (tab order, list/edit
arrangement) is a separate piece of work.
