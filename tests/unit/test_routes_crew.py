"""
Unit tests for curator.web.routes.crew

Scope: pure-logic tests for the proc-calling pattern established this
session — _call_proc's envelope unwrapping, and the save routes' guard
clauses (empty name) that return before ever touching the database.

These are unit tests, not integration tests: the database connection is
mocked throughout. Nothing here makes a real connection to PostgreSQL.
Integration tests against the real wcyj database are deferred until the
Contacts/Tasks forms are designed and their procs exist (see
curator_handoff notes from this session) — see tests/integration/ for
where those will eventually live.

Note: importing curator.web.routes.crew triggers module-level reads of
queries.yaml and forms.yaml (via QueryBuilder/QueryLoader construction
at import time) — these tests are not fully filesystem-isolated, only
database-isolated. If those YAML files are ever missing or malformed,
these tests will fail at import/collection time, not at the assertion
they're actually about.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web.routes import crew


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


def make_mock_db_for_proc(envelope) -> SimpleNamespace:
    """Build a fake db whose fetch_one() returns a single-key dict wrapping
    the given envelope — matching the real shape dbkit returns for
    `SELECT api.some_proc(...)` (e.g. {"save_project": {...}}).

    envelope may be a dict (simulating dbkit already having decoded JSONB
    to a Python dict) or a JSON string (simulating the case where it comes
    back as a raw string and _call_proc must json.loads() it itself).
    """
    return SimpleNamespace(
        fetch_one=AsyncMock(return_value={"some_proc_name": envelope})
    )


# ---------------------------------------------------------------------------
# _call_proc — envelope unwrapping
# ---------------------------------------------------------------------------

class TestCallProc:
    """_call_proc must correctly unwrap a proc's JSONB envelope regardless
    of whether dbkit hands it back as an already-decoded dict or as a raw
    JSON string — this ambiguity was flagged as unverified during the
    original crew.py -> api schema migration this session and is exactly
    the kind of thing that should be pinned down by a test rather than
    left as an assumption.
    """

    @pytest.mark.asyncio
    async def test_unwraps_dict_envelope(self):
        """When dbkit already returns a decoded dict, _call_proc should
        pass it through unchanged, not double-parse it."""
        envelope = {"success": True, "data": {"id": 42}, "message": None}
        db = make_mock_db_for_proc(envelope)

        result = await crew._call_proc(db, "SELECT api.fake_proc(%s)", (1,))

        assert result == envelope
        assert result["success"] is True
        assert result["data"]["id"] == 42

    @pytest.mark.asyncio
    async def test_unwraps_json_string_envelope(self):
        """When dbkit returns the envelope as a raw JSON string (the
        encoding-dependent case noted in _call_proc's docstring),
        _call_proc must json.loads() it before returning."""
        envelope_dict = {"success": False, "data": None, "message": "Not found."}
        envelope_str = json.dumps(envelope_dict)
        db = make_mock_db_for_proc(envelope_str)

        result = await crew._call_proc(db, "SELECT api.fake_proc(%s)", (1,))

        assert result == envelope_dict
        assert result["success"] is False
        assert result["message"] == "Not found."

    @pytest.mark.asyncio
    async def test_passes_sql_and_params_through_unchanged(self):
        """_call_proc shouldn't alter the SQL or params it was given —
        confirms it's a thin pass-through to fetch_one, not doing any
        SQL construction of its own."""
        db = make_mock_db_for_proc({"success": True, "data": None, "message": None})
        sql = "SELECT api.save_project(%s, %s)"
        params = ('{"name": "Test"}', 7)

        await crew._call_proc(db, sql, params)

        db.fetch_one.assert_awaited_once_with(sql, params)


# ---------------------------------------------------------------------------
# save_new_project — empty-name guard
# ---------------------------------------------------------------------------

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

        response = await crew.save_new_project(request, db)

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

        response = await crew.save_new_project(request, db)

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

        response = await crew.save_new_project(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


# ---------------------------------------------------------------------------
# save_project (update route) — same empty-name guard
# ---------------------------------------------------------------------------

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

        response = await crew.save_project(project_id=22, request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


# ---------------------------------------------------------------------------
# save_new_project / save_project — proc rejection passthrough
# ---------------------------------------------------------------------------

class TestProcRejectionPassthrough:
    """Confirms the route correctly forwards a proc's full rejection
    envelope (including the new "data" field added for the conflicting_id
    feature) without dropping or reshaping any of it. This is the bug
    class that caused the silent duplicate-name failure earlier this
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

        # First fetch_one call (inside _call_proc) returns the rejection.
        # _resolve_type_status_names won't call fetch_one at all here since
        # both type_id and status_id are None in this payload.
        db = SimpleNamespace(fetch_one=AsyncMock(return_value={
            "save_project": rejection_envelope
        }))

        print("DIAGNOSTIC: db =", db, "type:", type(db))
        response = await crew.save_new_project(request, db)

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
        #   1. inside _call_proc, for the SELECT api.save_project(...) call
        #   2. inside _fetch_project_for_display, for the re-fetch by id
        db = SimpleNamespace(fetch_one=AsyncMock(side_effect=[
            {"save_project": save_envelope},
            display_record,
        ]))

        response = await crew.save_new_project(request, db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 123
        assert body["name"] == "New Project"
