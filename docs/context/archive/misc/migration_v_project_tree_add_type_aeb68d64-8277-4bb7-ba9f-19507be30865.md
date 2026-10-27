# Schema Migration: Add project_type to v_project_tree

**Commit type:** `chart`  
**Commit message:** `chart: add project_type to v_project_tree for type filtering`

---

## Why

The Scribe card on the landing page links to `/projects/board?type=writing`.
The board route filters the project tree by type, but `v_project_tree` had
no `project_type` column — it only joined `projects` with no reference to
the `project_type` lookup table. This migration adds the join so type
filtering is available to the board and any future filtered views.

---

## Changes

### 1. Apply to database (run on steward via pgAdmin or psql)

```sql
CREATE OR REPLACE VIEW v_project_tree AS
WITH RECURSIVE tree AS (
    SELECT projects.id,
           projects.parent_id,
           projects.name,
           projects.slug,
           projects.type_id,
           0 AS depth,
           ARRAY[projects.slug::character varying] AS path
    FROM projects
    WHERE projects.parent_id IS NULL

    UNION ALL

    SELECT p.id,
           p.parent_id,
           p.name,
           p.slug,
           p.type_id,
           t.depth + 1,
           t.path || p.slug
    FROM projects p
    JOIN tree t ON t.id = p.parent_id
)
SELECT tree.id,
       tree.parent_id,
       tree.name,
       tree.slug,
       tree.depth,
       tree.path,
       pt.name AS project_type
FROM tree
LEFT JOIN project_type pt ON pt.id = tree.type_id;
```

### 2. Update schema.sql in the curator repo

Find the existing `v_project_tree` definition and replace it with the
version above. It will look like this in the file:

#### BEFORE

```sql
CREATE OR REPLACE VIEW v_project_tree AS
WITH RECURSIVE tree AS (
    SELECT projects.id,
           projects.parent_id,
           projects.name,
           projects.slug,
           0 AS depth,
           ARRAY[projects.slug::character varying] AS path
    FROM projects
    WHERE projects.parent_id IS NULL

    UNION ALL

    SELECT p.id,
           p.parent_id,
           p.name,
           p.slug,
           t.depth + 1,
           t.path || p.slug
    FROM projects p
    JOIN tree t ON t.id = p.parent_id
)
SELECT tree.id,
       tree.parent_id,
       tree.name,
       tree.slug,
       tree.depth,
       tree.path
FROM tree;
```

#### AFTER

```sql
CREATE OR REPLACE VIEW v_project_tree AS
WITH RECURSIVE tree AS (
    SELECT projects.id,
           projects.parent_id,
           projects.name,
           projects.slug,
           projects.type_id,
           0 AS depth,
           ARRAY[projects.slug::character varying] AS path
    FROM projects
    WHERE projects.parent_id IS NULL

    UNION ALL

    SELECT p.id,
           p.parent_id,
           p.name,
           p.slug,
           p.type_id,
           t.depth + 1,
           t.path || p.slug
    FROM projects p
    JOIN tree t ON t.id = p.parent_id
)
SELECT tree.id,
       tree.parent_id,
       tree.name,
       tree.slug,
       tree.depth,
       tree.path,
       pt.name AS project_type
FROM tree
LEFT JOIN project_type pt ON pt.id = tree.type_id;
```

---

## Verification

After applying, confirm the new column is present:

```sql
SELECT id, name, project_type FROM v_project_tree ORDER BY path;
```

Projects with a type assigned should show the type name. Projects with
no type should show NULL.

---

## Notes

- `CREATE OR REPLACE VIEW` is safe to run on a live database — no data
  is affected, only the view definition changes.
- No application code changes are needed for this migration alone.
- The `get_tree()` repository method and board route changes to use the
  new column are tracked in a separate changedoc.
