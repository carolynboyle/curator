"""
Unit tests for curator.web.deps

Scope: call_proc()'s envelope unwrapping — moved here from
test_routes_crew.py's TestCallProc class as part of the crew.py route
split (2026-07-01). call_proc itself also moved, from crew.py to deps.py,
and was renamed from _call_proc (see deps.py changedoc entry for why).

These are unit tests, not integration tests: the database connection is
mocked throughout. Nothing here makes a real connection to PostgreSQL.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web import deps


def make_mock_db_for_proc(envelope) -> SimpleNamespace:
    """Build a fake db whose fetch_one() returns a single-key dict wrapping
    the given envelope — matching the real shape dbkit returns for
    `SELECT api.some_proc(...)` (e.g. {"save_project": {...}}).

    envelope may be a dict (simulating dbkit already having decoded JSONB
    to a Python dict) or a JSON string (simulating the case where it comes
    back as a raw string and call_proc must json.loads() it itself).
    """
    return SimpleNamespace(
        fetch_one=AsyncMock(return_value={"some_proc_name": envelope})
    )


class TestCallProc:
    """call_proc must correctly unwrap a proc's JSONB envelope regardless
    of whether dbkit hands it back as an already-decoded dict or as a raw
    JSON string — this ambiguity was flagged as unverified during the
    original crew.py -> api schema migration and is exactly the kind of
    thing that should be pinned down by a test rather than left as an
    assumption.
    """

    @pytest.mark.asyncio
    async def test_unwraps_dict_envelope(self):
        """When dbkit already returns a decoded dict, call_proc should
        pass it through unchanged, not double-parse it."""
        envelope = {"success": True, "data": {"id": 42}, "message": None}
        db = make_mock_db_for_proc(envelope)

        result = await deps.call_proc(db, "SELECT api.fake_proc(%s)", (1,))

        assert result == envelope
        assert result["success"] is True
        assert result["data"]["id"] == 42

    @pytest.mark.asyncio
    async def test_unwraps_json_string_envelope(self):
        """When dbkit returns the envelope as a raw JSON string (the
        encoding-dependent case noted in call_proc's docstring),
        call_proc must json.loads() it before returning."""
        envelope_dict = {"success": False, "data": None, "message": "Not found."}
        envelope_str = json.dumps(envelope_dict)
        db = make_mock_db_for_proc(envelope_str)

        result = await deps.call_proc(db, "SELECT api.fake_proc(%s)", (1,))

        assert result == envelope_dict
        assert result["success"] is False
        assert result["message"] == "Not found."

    @pytest.mark.asyncio
    async def test_passes_sql_and_params_through_unchanged(self):
        """call_proc shouldn't alter the SQL or params it was given —
        confirms it's a thin pass-through to fetch_one, not doing any
        SQL construction of its own."""
        db = make_mock_db_for_proc({"success": True, "data": None, "message": None})
        sql = "SELECT api.save_project(%s, %s)"
        params = ('{"name": "Test"}', 7)

        await deps.call_proc(db, sql, params)

        db.fetch_one.assert_awaited_once_with(sql, params)