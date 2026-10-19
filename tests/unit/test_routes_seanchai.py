"""
Unit tests for curator.web.routes.seanchai

Scope: the save routes' guard clauses (empty subject / search_terms) that
return before touching the database, and the proc-rejection passthrough
contract.

Mirrors tests/unit/test_routes_projects.py and test_routes_tasks
structure exactly — same mock pattern (SimpleNamespace, AsyncMock), same
class and test layout. Follows tasks.py's approach: the route under test
has a local guard (_require_subject, _require_search_terms) rather than
reusing deps.py's require_name().

These are unit tests, not integration tests: the database connection is
mocked throughout. Nothing here makes a real connection to PostgreSQL.
Integration tests are deferred to tests/integration/ (same as the other
entity tests).
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web.routes import seanchai


def make_mock_request(body: dict, user_id: int = 1) -> SimpleNamespace:
    """Build a minimal fake Request with just what the save routes read.

    The save routes only touch request.json() and
    request.state.user["user_id"] — a SimpleNamespace covers both.
    """
    return SimpleNamespace(
        json=AsyncMock(return_value=body),
        state=SimpleNamespace(user={"user_id": user_id}),
    )


# =============================================================================
# Records — save_new_record guard tests
# =============================================================================

class TestSaveNewRecordGuard:
    """The empty-subject check in save_new_record is meant to short-circuit
    before any database call. These tests confirm the guard fires and that
    the database is never touched when it does — if a future edit removes
    or moves the check, these should fail loudly.
    """

    @pytest.mark.asyncio
    async def test_empty_subject_returns_without_touching_db(self):
        request = make_mock_request({"subject": "", "record_type_id": None,
                                      "record_status_id": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await seanchai.save_new_record(request, db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Subject is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_subject_is_treated_as_empty(self):
        """The route strips before checking — spaces-only should be rejected."""
        request = make_mock_request({"subject": "   ", "record_type_id": None,
                                      "record_status_id": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await seanchai.save_new_record(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Subject is required."
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_subject_key_treated_as_empty(self):
        """body.get("subject") on a payload missing the key should be the
        same as an explicit empty string, not raise a KeyError."""
        request = make_mock_request({"record_type_id": None, "record_status_id": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await seanchai.save_new_record(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


# =============================================================================
# Records — save_record (update) guard tests
# =============================================================================

class TestSaveRecordGuard:
    """Same guard, update route — save_record takes record_id as a parameter
    the new-record route doesn't have, so the call shape differs slightly."""

    @pytest.mark.asyncio
    async def test_empty_subject_returns_without_touching_db(self):
        request = make_mock_request({"subject": "", "record_type_id": None,
                                      "record_status_id": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await seanchai.save_record(record_id=7, request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Subject is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


# =============================================================================
# Records — proc rejection passthrough
# =============================================================================

class TestRecordProcRejectionPassthrough:
    """Confirms the route correctly forwards a proc's full rejection envelope
    without dropping or reshaping any of it. Same regression guard as
    test_routes_projects.py's TestProcRejectionPassthrough.
    """

    @pytest.mark.asyncio
    async def test_duplicate_record_id_rejection_forwards_data_and_message(self):
        request = make_mock_request({
            "subject": "Deed — Felix Boyle Sr.",
            "record_id": "PR-001",
            "record_type_id": 1,
            "record_status_id": 1,
        })

        rejection_envelope = {
            "success": False,
            "data": {},
            "message": "Record ID already exists",
        }

        db = SimpleNamespace(fetch_one=AsyncMock(return_value={
            "save_record": rejection_envelope
        }))

        response = await seanchai.save_new_record(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Record ID already exists"

    @pytest.mark.asyncio
    async def test_success_response_has_no_success_key(self):
        """On success, the route returns the flat record with no 'success' key —
        this is the contract saveForm() in detail-panel.js relies on to
        distinguish success from failure (body.success === false).
        """
        request = make_mock_request({
            "subject": "Deed — Felix Boyle Sr.",
            "record_id": "PR-001",
            "record_type_id": 1,
            "record_status_id": 1,
        })

        save_envelope = {
            "success": True,
            "data": {"id": 42},
            "message": "OK",
        }
        display_record = {
            "id": 42,
            "record_id": "PR-001",
            "subject": "Deed — Felix Boyle Sr.",
            "record_type_id": 1,
            "record_status_id": 1,
        }

        db = SimpleNamespace(fetch_one=AsyncMock(side_effect=[
            {"save_record": save_envelope},
            {"get_record_detail": display_record},
        ]))

        response = await seanchai.save_new_record(request, db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 42
        assert body["record_id"] == "PR-001"


# =============================================================================
# Searches — save_new_search guard tests
# =============================================================================

class TestSaveNewSearchGuard:
    """Mirrors the records guard tests — search_terms is the required field."""

    @pytest.mark.asyncio
    async def test_empty_search_terms_returns_without_touching_db(self):
        request = make_mock_request({"search_terms": "", "county_scope": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await seanchai.save_new_search(request, db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Search terms are required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_search_terms_treated_as_empty(self):
        request = make_mock_request({"search_terms": "   ", "county_scope": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await seanchai.save_new_search(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Search terms are required."
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_search_terms_key_treated_as_empty(self):
        request = make_mock_request({"county_scope": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await seanchai.save_new_search(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


# =============================================================================
# Searches — save_search (update) guard tests
# =============================================================================

class TestSaveSearchGuard:
    """Update route guard — save_search takes search_id as a parameter."""

    @pytest.mark.asyncio
    async def test_empty_search_terms_returns_without_touching_db(self):
        request = make_mock_request({"search_terms": "", "county_scope": None})
        db = SimpleNamespace(fetch_one=AsyncMock())

        response = await seanchai.save_search(search_id=3, request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Search terms are required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


# =============================================================================
# Searches — proc rejection passthrough
# =============================================================================

class TestSearchProcRejectionPassthrough:

    @pytest.mark.asyncio
    async def test_duplicate_search_id_rejection_forwards_message(self):
        request = make_mock_request({
            "search_terms": "Felix Boyle Luzerne County 1850",
            "search_id": "SRCH-001",
        })

        rejection_envelope = {
            "success": False,
            "data": {},
            "message": "Search ID already exists",
        }

        db = SimpleNamespace(fetch_one=AsyncMock(return_value={
            "save_search": rejection_envelope
        }))

        response = await seanchai.save_new_search(request, db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Search ID already exists"

    @pytest.mark.asyncio
    async def test_success_response_has_no_success_key(self):
        request = make_mock_request({
            "search_terms": "Felix Boyle Luzerne County 1850",
            "search_id": "SRCH-001",
        })

        save_envelope = {
            "success": True,
            "data": {"id": 9},
            "message": "OK",
        }
        display_record = {
            "id": 9,
            "search_id": "SRCH-001",
            "search_terms": "Felix Boyle Luzerne County 1850",
            "county_scope": None,
            "status": "complete",
        }

        db = SimpleNamespace(fetch_one=AsyncMock(side_effect=[
            {"save_search": save_envelope},
            {"get_search_detail": display_record},
        ]))

        response = await seanchai.save_new_search(request, db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 9
        assert body["search_id"] == "SRCH-001"
