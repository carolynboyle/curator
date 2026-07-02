# Changedoc: Add `is_template` column to `projects.projects`

**Files:** `03_projects.sql` (canonical source), `steward` DB (`wcyj`, live migration)
**Type:** Additive column, `NOT NULL DEFAULT FALSE` — safe against existing rows
**Reason:** Groundwork for the future Project Templates feature
(`docs/design/project_templates_design.md`). Scope trimmed from the original
two-column design: `source_template_id` dropped as unnecessary at this
stage (no consumer, soft/unreliable lineage due to `ON DELETE SET NULL`,
trivially addable later if a concrete "created from template" feature
emerges). Just `is_template` for now.

---

## BEFORE — `03_projects.sql`

```sql
CREATE TABLE projects.projects (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    notes       TEXT,
    status_id   BIGINT       NOT NULL REFERENCES projects.project_status (id),
    type_id     BIGINT       REFERENCES projects.project_type (id),
    parent_id   BIGINT       REFERENCES projects.projects (id) ON DELETE SET NULL,
    target_date DATE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by  BIGINT       REFERENCES identity.app_user (id) ON DELETE SET NULL,
    updated_by  BIGINT       REFERENCES identity.app_user (id) ON DELETE SET NULL
);
```

## AFTER — `03_projects.sql`

```sql
CREATE TABLE projects.projects (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    notes       TEXT,
    status_id   BIGINT       NOT NULL REFERENCES projects.project_status (id),
    type_id     BIGINT       REFERENCES projects.project_type (id),
    parent_id   BIGINT       REFERENCES projects.projects (id) ON DELETE SET NULL,
    target_date DATE,
    is_template BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by  BIGINT       REFERENCES identity.app_user (id) ON DELETE SET NULL,
    updated_by  BIGINT       REFERENCES identity.app_user (id) ON DELETE SET NULL
);
```

---

## Live migration (run in pgAdmin against `wcyj`)

```sql
ALTER TABLE projects.projects
    ADD COLUMN is_template BOOLEAN NOT NULL DEFAULT FALSE;
```

---

## Notes
- No index added — `is_template` isn't yet used in a `WHERE` clause anywhere.
  Add `idx_projects_is_template` later if/when role-filtered views start
  filtering on it (the open question flagged in the design doc: whether
  role views need `WHERE is_template = false`).
- No proc or Python changes required by this changedoc alone — `api.save_project`
  doesn't touch this column, and no UI currently sets or reads it. This is
  pure groundwork; the "mark as template" UI and `api.create_project_from_template`
  proc are separate, later work.
- `source_template_id` intentionally omitted from this pass per discussion —
  add via a future one-line `ALTER TABLE` if a concrete provenance/stats
  feature is designed.
