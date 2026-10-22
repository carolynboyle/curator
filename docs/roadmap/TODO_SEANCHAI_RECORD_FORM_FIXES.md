# Seanchaí Records Form — Known Issues

Logged 2026-10-22 during initial data import work. Neither issue blocks import;
both must be resolved before the records form is usable for adding new records.

---

## 1. `record_id` must be auto-generated, not manually entered

**Current behaviour:** The "Record ID" field is a free-text input. Users must
type in the identifier (e.g. `PR-001`) themselves.

**Required behaviour:** `record_id` should be generated automatically on the
backend when a new record is saved. The prefix comes from the selected
`record_type` code (PR, WL, MG, etc.); the number is the next available
in that series.

**Suggested approach:**
- After type selection the route (or a dedicated endpoint) calls something like
  `api.next_record_id(record_type_id)` to determine the next ID.
- The field is displayed read-only in the form so the user can see what ID will
  be assigned, but cannot edit it.
- On save, the route generates the final ID server-side (not trusting the
  client value) to avoid race conditions.

**Schema impact:** None — `record_id VARCHAR(20) UNIQUE` stays as-is.

---

## 2. `type_code` and `record_type` are showing as editable inputs

**Current behaviour:** The detail form exposes `type_code` and `record_type`
as editable text fields. These columns come from the `v_record_detail` view
join to `seanchai.record_type` and are not columns on the `records` table.
They cannot be saved and should not be editable.

**Required behaviour:** Mark both fields read-only in `fieldkit_overrides.yaml`
(or exclude them from the form entirely — the Type dropdown already handles
type selection via `record_type_id`).

**Schema impact:** None.

---

## Fix together

These are both seanchaí form / fieldkit_overrides changes and belong in the
same pass. Suggested branch: `seanchai-form-fixes` off `seanchai-fieldkit-overrides`.
