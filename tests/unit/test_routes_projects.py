"""
Unit tests for curator.web.routes.projects

Scope: the save routes' guard clauses (empty name) that return before
ever touching the database, and the proc-rejection passthrough contract.
Split out of test_routes_crew.py as part of the crew.py route split
(2026-07-01) — projects.save_new_project / save_project moved to their
own module, and _call_proc's envelope-unwrapping tests moved to
test_deps.py alongside call_proc itself.

These are unit tests, not integration tests: the database connection is
mocked throughout. Nothing here makes a real connection to PostgreSQL.
Integration tests against the real wcyj database are deferred until the
Contacts/Tasks forms are designed and their procs exist — see
tests/integration/ for where those will eventually live.

Note: importing curator.web.routes.projects triggers no module-level
YAML reads (unlike the old crew.py, which read queries.yaml/forms.yaml
at import time for the /api/query endpoint and dashboard rendering —
those stayed in crew.py). projects.py has no import-time filesystem
dependency.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web.routes import projects


def make_mock_request(body: dict, user_id: int = 1) -> SimpleNamespace:
    """Build a minimal fake Request with just what the save routes read.

    The real save routes only touch request.json() and
    request.state.user["user_id"] — nothing else about the real Starlette
    Request object is needed for these tests, so a SimpleNamespace stands
    in rather than constructing or mocking the full Request class.
    """
    return SimpleNamespace(
        json=AsyncMock(return_value=body),
        state=SimpleNamespace(user={"user_id": user_id}),
    )


class TestSaveNewProjectGuard:
    """The empty-name check in save_new_project is meant to short-circuit
    before any database call. These tests confirm that guard actually
    fires and that the database is never touched when it does — if a
    future edit accidentally moves the check after the proc call, or
    removes it, these should fail.
    """

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "type_id": None,
                                      "status_id": None, "description": None})
        db = SimpleNamespace(fetch_one=AsyncMock())  # should never be called

        response = await projects.save_new_project(request, db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_name_is_treated_as_empty(self):
        """The route does name.strip() before checking — a name of only
        spaces should be rejected the same as a truly empty string."""
        request = make_mock_request({"name": "   ", "type_id": None,
                                      "status_id": None, "description": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await projects.save_new_project(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Name is required."
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_name_key_entirely_is_treated_as_empty(self):
        """body.get("name") on a payload with no "name" key at all should
        behave the same as an explicit empty string, not raise a KeyError."""
        request = make_mock_request({"type_id": None, "status_id": None,
                                      "description": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await projects.save_new_project(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


class TestSaveProjectGuard:
    """Same guard, same reasoning, applied to the update route — kept as
    a separate test class since save_project takes project_id as a
    parameter the new-project route doesn't have, so the call shape
    differs slightly even though the guard logic is identical.
    """

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "type_id": None,
                                      "status_id": None, "description": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await projects.save_project(project_id=22, request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


class TestProcRejectionPassthrough:
    """Confirms the route correctly forwards a proc's full rejection
    envelope (including the "data" field used for the conflicting_id
    feature) without dropping or reshaping any of it. This is the bug
    class that caused the silent duplicate-name failure in an earlier
    session (saveForm() couldn't tell success from failure because the
    route's response shape was inconsistent) — a regression here should
    fail loudly, not silently.
    """

    @pytest.mark.asyncio
    async def test_duplicate_name_rejection_forwards_data_and_message(self):
        request = make_mock_request({
            "name": "Existing Project", "type_id": None,
            "status_id": None, "description": None,
        })

        rejection_envelope = {
            "success": False,
            "data": {"conflicting_id": 99},
            "message": "A project with that name already exists.",
        }

        # First fetch_one call (inside call_proc) returns the rejection.
        # _resolve_type_status_names won't call fetch_one at all here since
        # both type_id and status_id are None in this payload.
        db = SimpleNamespace(fetch_one=AsyncMock(return_value={
            "save_project": rejection_envelope
        }))

        response = await projects.save_new_project(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "A project with that name already exists."
        assert body["data"] == {"conflicting_id": 99}

    @pytest.mark.asyncio
    async def test_success_response_has_no_success_key(self):
        """On success, the route returns the flat project record with no
        "success" key at all — this is the exact distinction saveForm()
        in detail-panel.js relies on (body.success === False, not
        res.ok) to tell success from failure. A test pinning this down
        protects that contract from an accidental future change."""
        request = make_mock_request({
            "name": "New Project", "type_id": None,
            "status_id": None, "description": None,
        })

        save_envelope = {
            "success": True,
            "data": {"id": 123},
            "message": None,
        }
        display_record = {
            "id": 123, "name": "New Project", "slug": "new-project",
            "description": None, "type_id": None, "status_id": None,
            "status": None, "type": None,
        }

        # fetch_one is called twice in the success path:
        #   1. inside call_proc, for the SELECT api.save_project(...) call
        #   2. inside _fetch_project_for_display, for the re-fetch by id
        db = SimpleNamespace(fetch_one=AsyncMock(side_effect=[
            {"save_project": save_envelope},
            display_record,
        ]))

        response = await projects.save_new_project(request, db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 123
        assert body["name"] == "New Project"