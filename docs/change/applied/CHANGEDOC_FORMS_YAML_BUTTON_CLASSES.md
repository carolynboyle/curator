# Changedoc: forms.yaml — add specific button classes alongside btn-secondary

**File:** `src/curator/data/forms.yaml`
**Type:** Bug fix — no visual change, fixes click handling
**Reason:** `detail-panel.js`'s click delegation checks for `btn-save` /
`btn-new` / `btn-discard` specifically:

```js
if (e.target.classList.contains('btn-save'))    { ... handleSave(); }
if (e.target.classList.contains('btn-new'))     handleNew();
if (e.target.classList.contains('btn-discard')) handleDiscard();
```

But `forms.yaml` currently gives all three buttons only the generic
`btn-secondary` class — none of the three specific classes ever land on
the rendered `<button>`. Result: **none** of Save/New/Discard work by
click (Alt+S/Alt+N/Alt+X still work, since the keyboard handler calls
`handleSave()`/`handleNew()`/`handleDiscard()` directly with no class
check). This was surfaced as "Exit button doesn't work" but affects all
three buttons identically — Exit was just the one tested by click first.

`buttons.css` already styles `.btn-save`, `.btn-new`, `.btn-discard` as
aliases of `.btn-secondary` (same selector list, same rules) — so adding
the second class changes nothing visually, it only gives the JS click
handler something to match.

---

## BEFORE

```yaml
buttons:
  save:
    label:   "<u>S</u>ave"
    type:    submit
    class:   btn-secondary
    title:   "Save (Alt+S)"

  new:
    label:   "<u>N</u>ew"
    type:    button
    class:   btn-secondary
    title:   "New (Alt+N)"
    data_attrs:
      action: new

  discard:
    label:   "E<u>x</u>it"
    type:    button
    class:   btn-secondary
    title:   "Exit (Alt+X)"
    data_attrs:
      action: discard
```

## AFTER

```yaml
buttons:
  save:
    label:   "<u>S</u>ave"
    type:    submit
    class:   "btn-secondary btn-save"
    title:   "Save (Alt+S)"

  new:
    label:   "<u>N</u>ew"
    type:    button
    class:   "btn-secondary btn-new"
    title:   "New (Alt+N)"
    data_attrs:
      action: new

  discard:
    label:   "E<u>x</u>it"
    type:    button
    class:   "btn-secondary btn-discard"
    title:   "Exit (Alt+X)"
    data_attrs:
      action: discard
```

---

## Notes
- This fixes Save/New/Exit everywhere `forms.yaml`'s `detail_panel` preset
  is used — not Identities-tab-specific. Projects' detail panel gets the
  same fix.
- No Python or JS changes needed — `formkit.py`'s `from_yaml()` just
  passes `class` straight through from the yaml, so the two-class string
  flows through unmodified to the rendered `class="..."` attribute.
