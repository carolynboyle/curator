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

## Phase III idea: themes and form settings in Postgres

Logged 2026-11-27. Not for now.

Move theme and form definitions (theme values, field layouts, widget
definitions) from YAML into database tables, and give the Captain role forms
to design them, in the spirit of the old MS Access form wizards.

Motivation: a sales demo. Ship Curator with one professional business skin,
then switch to the customer's own theme with a click ("Acme Corporation,
Wile E. Coyote, CEO"). Customers customise to their corporate colours without
touching files.

Notes for when it happens:
- Keep the YAML files as the default/seed; the database holds overrides.
- Needs change history (who changed what, rollback), since git no longer covers it.
- Needs validation before save and a fallback to the default files, so a bad
  theme or layout cannot break every form (or the form that edits forms).
- Depends on the Captain role and its permissions existing first.
- Until then, keep new settings in plain data shapes (named fields, simple
  values, no logic) so they map to tables later.
