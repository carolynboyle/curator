# Change: Board Type Filter (Scribe & Mechanic)

**Commit type:** `trim`  
**Commit message:** `trim: add type filter to project board for Scribe and Mechanic views`

---

## Why

The Scribe card links to `/projects/board?type=writing` and the Mechanic
card links to `/projects/board?type=refurb`. The board route currently
ignores the `type` query parameter — it always loads all projects.

This change wires up the filter so each crew card shows only the relevant
project type.

---

## Prerequisites

Before deploying this change:

1. `refurb` project type must exist in the database:
```sql
INSERT INTO project_type (name) VALUES ('refurb');
```

2. WCYJ refurb projects must be updated to type `refurb`:
```sql
UPDATE projects
SET type_id = (SELECT id FROM project_type WHERE name = 'refurb')
WHERE type_id = (SELECT id FROM project_type WHERE name = 'other')
AND id IN (
    SELECT id FROM projects WHERE parent_id = (
        SELECT id FROM projects WHERE slug = 'wcyj-refurbs-wcyj-store'
    )
    UNION
    SELECT id FROM projects WHERE slug = 'wcyj-refurbs-wcyj-store'
);
```

Check the slug first — it may differ:
```sql
SELECT slug FROM projects WHERE name ILIKE '%refurb%';
```

3. Update `curator.yaml` — change the Mechanic card URL:

```yaml
    - title: "The Mechanic"
      subtitle: "Hardware management · Refurb · Inventory"
      url: "/projects/board?type=refurb"
      color: "amber"
```

---

## Code changes

### 1. src/curator/db/projects.py

#### BEFORE

```python
    async def get_tree(self) -> list[dict]:
        """
        Return all projects with full ancestry from v_project_tree.

        Returns:
            List of project tree dicts ordered by depth then name.
        """
        return await self.fetch_all(
            "SELECT * FROM v_project_tree ORDER BY path"
        )
```

#### AFTER

```python
    async def get_tree(self, project_type: str | None = None) -> list[dict]:
        """
        Return all projects with full ancestry from v_project_tree,
        optionally filtered by project type name.

        Args:
            project_type: Optional type name to filter by (e.g. "writing",
                          "refurb"). Only root-level projects of this type
                          and their children are returned.

        Returns:
            List of project tree dicts ordered by path.
        """
        if project_type:
            return await self.fetch_all(
                """
                SELECT * FROM v_project_tree
                WHERE path[1] IN (
                    SELECT slug FROM projects
                    WHERE type_id = (
                        SELECT id FROM project_type WHERE name = %s
                    )
                )
                ORDER BY path
                """,
                (project_type,),
            )
        return await self.fetch_all(
            "SELECT * FROM v_project_tree ORDER BY path"
        )
```

---

### 2. src/curator/web/routes/projects.py

#### BEFORE

```python
@router.get("/board", response_class=HTMLResponse)
async def project_board(
    request: Request,
    db: AsyncDBConnection = Depends(get_db),
):
    repo = ProjectRepository(db)
    tree = await repo.get_tree()
    return templates.TemplateResponse(
        request=request,
        name="projects/board.html",
        context={"tree": tree},
    )
```

#### AFTER

```python
@router.get("/board", response_class=HTMLResponse)
async def project_board(
    request: Request,
    project_type: str | None = None,
    db: AsyncDBConnection = Depends(get_db),
):
    repo = ProjectRepository(db)
    tree = await repo.get_tree(project_type=project_type)
    return templates.TemplateResponse(
        request=request,
        name="projects/board.html",
        context={"tree": tree, "project_type": project_type},
    )
```

---

## Notes

- The filter works by finding root-level projects of the requested type,
  then returning all tree rows whose path starts with one of those root
  slugs. This ensures subprojects are included even if the subproject
  itself has no type set.
- `project_type` is passed to the template so the board can show a
  heading or indicator of the active filter if desired in future.
- No template changes are required for basic filtering to work.
