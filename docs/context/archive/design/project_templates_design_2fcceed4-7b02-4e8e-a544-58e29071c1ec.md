# Design Doc: Project Templates

**Status:** Sketch / not started — revisit after Contacts & Tasks forms are working
**Target milestone:** Before Felipe demo (nice-to-have, not blocking)

---

## Problem

Recurring project types (starting with refurb) involve the same standard set of
tasks every time. Currently every new project starts blank, requiring the
Captain or Mechanic to manually recreate the same task list each time.

## Concept

A template is not a separate entity — it's just a regular project flagged as
reusable. "Creating a project from a template" copies that project's task list
onto a new project record.

This keeps the data model simple: no new template-editing UI, no separate
template table. Captain builds out a project's tasks the normal way, then
flags it as a template. Any project can be designated a template at any time.

## Schema Changes

Two additive columns on `projects.projects`, no migration logic required:

```sql
ALTER TABLE projects.projects
    ADD COLUMN is_template BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE projects.projects
    ADD COLUMN source_template_id BIGINT REFERENCES projects.projects(id) ON DELETE SET NULL;
```

- `is_template` — marks a project as available for use as a template.
- `source_template_id` — provenance only; records which template a project was
  created from. Not a live link; safe to leave dangling if the template is
  later un-flagged or deleted (`ON DELETE SET NULL`).

No changes needed to `projects.tasks` — task/subtask hierarchy via `parent_id`
already supports whatever depth a template's workflow needs.

> Note: `projects.projects.parent_id` (sub-projects) is intentionally not part
> of this design. Carolyn doesn't expect to use sub-projects in practice —
> `type_id` covers categorization, and templates operate purely at the
> project + tasks level.

## UI Changes

**Designating a template**
- Add an `is_template` checkbox/toggle to the project edit form.
- Captain-only — Scribe/Mechanic/Envoy should not see or set this field.
- No constraints on which projects are eligible (no "must be top-level"
  restriction, since sub-projects aren't in active use).

**Creating from a template**
- Add a "Start from template" picker to the new-project (add) form.
- Populated from `projects.projects WHERE is_template = true`, optionally
  filtered by `type_id` (e.g. only show refurb templates when type=refurb is
  selected).
- Selecting a template does not pre-fill the form — the copy happens
  server-side after the new project record is created.

## Behavior Rules

- **The template itself is never modified by a copy.** It remains a normal,
  editable project for as long as it's flagged `is_template`.
- **All copied tasks have their status reset.** `status_id` → default
  "not started" status, `completed_at` → NULL, regardless of what state
  those tasks were in on the source template. A template represents the
  standard workflow, not a snapshot of someone's progress.
- All other task fields (description, notes, priority_id, sort_order,
  parent/child structure) are copied as-is.

## Stored Procedure: `api.create_project_from_template`

Inputs: new project fields (name, slug, description, type_id, target_date,
etc.) + `template_project_id`.

Logic:
1. Insert the new `projects.projects` row from the submitted form data,
   with `source_template_id` set to `template_project_id`.
2. Select all `projects.tasks` rows where `project_id = template_project_id`,
   ordered parent-first (so parent tasks are inserted — and have a new id —
   before any children that reference them).
3. For each task, insert a copy into the new project:
   - `status_id` forced to the default "not started" status
   - `completed_at` forced to NULL
   - `parent_id` remapped through an old-task-id → new-task-id map built up
     as rows are inserted (NULL stays NULL for top-level tasks)
4. Return the new project record, matching the existing contract used by
   `api.save_project`.

## Open Items for Later

- Confirm whether role-filtered views (Scribe/Mechanic/Envoy boards) need an
  explicit `WHERE is_template = false` so templates don't show up in normal
  task lists.
- Decide default "not started" status id/name to hardcode (or look up) in
  the proc.
- Once Contacts/Tasks forms are stable, draft the actual changedoc (BEFORE/
  AFTER code blocks) for: the two `ALTER TABLE` statements, the stored proc,
  the project edit form (template checkbox), and the add-project form
  (template picker).
