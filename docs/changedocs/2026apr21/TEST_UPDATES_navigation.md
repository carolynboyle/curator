# Curator — Test Updates for Navigation Fix

**Date:** 2026-04-21
**File changed:** `tests/unit/test_routes_projects.py`

These two tests need updating because `create_project` and `update_project` now
redirect to `next_url` from the form data instead of hardcoding the destination.
Without `next_url` in the POST data, the route falls back to `_BOARD`, so the
old location assertions fail.

---

## Change 1 — `TestCreateProject.test_redirects_to_detail_on_success`

**REPLACE THIS FUNCTION:**

```python
def test_redirects_to_detail_on_success(self, client):
    with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.create = AsyncMock(return_value="new-project")
        response = client.post(
            "/projects/new",
            data={"name": "New Project", "status_id": "1"},
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/projects/new-project"
```

**WITH THIS:**

```python
def test_redirects_on_success(self, client):
    with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.create = AsyncMock(return_value="new-project")
        response = client.post(
            "/projects/new",
            data={"name": "New Project", "status_id": "1", "next_url": "/projects/board"},
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/projects/board"
```

**WHY:** Route now redirects to `next_url` from form data. Test supplies it explicitly
and asserts the correct destination.

---

## Change 2 — `TestUpdateProject.test_redirects_to_detail_on_success`

**REPLACE THIS FUNCTION:**

```python
def test_redirects_to_detail_on_success(self, client):
    with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
        MockRepo.return_value.update = AsyncMock(return_value=None)
        response = client.post(
            "/projects/test-project/edit",
            data={"name": "Updated", "status_id": "1"},
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/projects/test-project"
```

**WITH THIS:**

```python
def test_redirects_on_success(self, client):
    with patch("curator.web.routes.projects.ProjectRepository") as MockRepo:
        MockRepo.return_value.update = AsyncMock(return_value=None)
        response = client.post(
            "/projects/test-project/edit",
            data={"name": "Updated", "status_id": "1", "next_url": "/projects/board"},
            follow_redirects=False,
        )
    assert response.status_code == 303
    assert response.headers["location"] == "/projects/board"
```

**WHY:** Same as above — route now redirects to `next_url` from form data.

---

## Verification

Run the unit tests after making these changes:

```bash
pytest tests/unit/test_routes_projects.py -v
```

All other tests in the file are unaffected by the navigation fix.
## Addendum — Additional Fix: id Builtin Shadowing in Test Factories
While updating the test file, a second builtin shadow was identified. The _option() factory function in three test files used id as a parameter name, shadowing Python's built-in id() function. Unlike next, this one carries real risk — id() is used internally by Python and mocking libraries, and a silent collision could produce misleading test failures. Fixed in the same pass. Renamed id → opt_id in _option() in test_routes_projects.py, test_routes_files.py, and test_routes_tags.py. No call sites required updating as all calls are positional.

claude conversation:
https://claude.ai/chat/4417465c-9024-40df-82c4-46b9e47dc24c