# Changedoc: crew.py — Add Generic `/api/query` Endpoint

**Date:** 2026-06-27  
**File:** `curator/web/routes/crew.py`  
**Reason:** Implement generic query endpoint powered by QueryLoader to serve data for child datasheets in detail panels

---

## BEFORE (at module level, after imports)

```python
router = APIRouter()

# Initialize Jinja2 for crew dashboard
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
```

---

## AFTER (at module level, after imports)

```python
from viewkit.query_builder import QueryBuilder
from viewkit.query_loader import QueryLoader

router = APIRouter()

# Initialize Jinja2 for crew dashboard
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

# Initialize QueryLoader for /api/query endpoint
queries_path = Path(__file__).parent.parent.parent / "queries.yaml"
query_builder = QueryBuilder(queries_path)
query_loader = QueryLoader(query_builder)
```

---

## BEFORE (existing route)

The `crew_dashboard` route already exists. No changes to it.

---

## AFTER (add new route before `crew_dashboard`)

Add this new route **before the `@router.get("/crew")` dashboard route**:

```python
# -- Generic Query Endpoint for DataSheets -----------------------------------

@router.get("/api/query/{entity}/{query_name}")
async def run_query(
    entity: str,
    query_name: str,
    params: str = Query(""),
    db: AsyncDBConnection = Depends(get_db),
):
    """
    Generic query endpoint for fetching data via QueryLoader.
    
    Used by child datasheets in detail panels (e.g., tasks for a project,
    emails for a contact). Queries are defined in queries.yaml and loaded
    at startup via QueryLoader.
    
    Path parameters:
        entity:     Entity key in queries.yaml (e.g., "tasks", "contact_emails")
        query_name: Query name within the entity (e.g., "for_project")
    
    Query parameters:
        params: Comma-separated bind parameters as a single string
                (e.g., ?params=123 or ?params=123,456)
    
    Returns:
        JSON response: { "records": [...] }
        Each record is a dict with the columns returned by the query.
    
    Raises:
        HTTPException 404: If entity or query_name not found in queries.yaml
        HTTPException 500: If query execution fails
    """
    # Load query from QueryLoader
    try:
        sql = query_loader.sql(entity, query_name)
    except KeyError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Query not found: {entity}.{query_name}"
        )
    
    # Parse comma-separated parameters
    params_list = tuple(p.strip() for p in params.split(",")) if params else ()
    
    # Execute query
    try:
        rows = await db.fetch_all(sql, params_list)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query execution failed: {str(e)}"
        )
    
    # Return as JSON
    return JSONResponse({
        "records": [dict(r) for r in rows]
    })
```

---

## Why This Change

The `/api/query` endpoint is the bridge between Tabulator child datasheets and the database:

1. **`_datasheet.html`** calls `GET /api/query/tasks/for_project?params=123` to fetch tasks for project 123
2. The endpoint loads the SQL from `queries.yaml` via `QueryLoader`
3. Binds the parameters and executes
4. Returns JSON: `{ "records": [...] }`
5. Tabulator populates the grid from the response

This keeps queries centralized in `queries.yaml` (auditable, versionable) rather than scattered across route files. It also makes adding new child datasheets trivial — just add a query to `queries.yaml` and the endpoint already knows how to handle it.

**Route ordering note:** This route must be declared **before** any parameterized routes that might match `/api/...`. The dashboard route is at `/crew`, so there's no conflict, but this is a good place to document the ordering principle.
