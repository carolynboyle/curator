"""
Unit tests for curator.web.routes.record_documents

Scope: the early-exit guard (a part needs a source URL or a transcription
path), the payload the save routes forward to api.save_record_document,
and how the proc's success / rejection envelopes come back out.

Same mock pattern as test_routes_seanchai.py (SimpleNamespace, AsyncMock).
These are unit tests: the database connection is mocked throughout.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web.routes import record_documents


def make_mock_request(body: dict, user_id: int = 1) -> SimpleNamespace:
    """Fake Request with just what the save routes read."""
    return SimpleNamespace(
        json=AsyncMock(return_value=body),
        state=SimpleNamespace(user={"user_id": user_id}),
    )


def make_mock_db(envelope: dict) -> SimpleNamespace:
    """Fake db whose single fetch_one returns the proc envelope."""
    return SimpleNamespace(
        fetch_one=AsyncMock(return_value={"save_record_document": envelope})
    )


PART = {
    "id": 5, "record_id": 12, "seq": 2, "label": "p. 341",
    "source_url": "https://www.familysearch.org/ark:/1", "md_path": None,
    "status": "not_transcribed",
}


# =============================================================================
# Guard — neither link given
# =============================================================================

class TestRequireTarget:
    """A part with no source URL and no md_path is rejected before the
    database is touched."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("body", [
        {"record_id": 12, "label": "x"},
        {"record_id": 12, "source_url": "", "md_path": ""},
        {"record_id": 12, "source_url": "   ", "md_path": "  "},
        {"record_id": 12, "source_url": None, "md_path": None},
    ])
    async def test_insert_without_any_link_is_rejected(self, body):
        db = make_mock_db({})

        response = await record_documents.save_new_document(
            make_mock_request(body), db
        )

        result = json.loads(response.body)
        assert result["success"] is False
        assert "source URL" in result["message"]
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_without_any_link_is_rejected(self):
        db = make_mock_db({})

        response = await record_documents.save_document(
            doc_id=5, request=make_mock_request({"label": "x"}), db=db
        )

        assert json.loads(response.body)["success"] is False
        db.fetch_one.assert_not_awaited()


# =============================================================================
# Save — payload and envelope handling
# =============================================================================

class TestSaveNewDocument:

    @pytest.mark.asyncio
    async def test_forwards_fields_and_returns_the_part(self):
        db = make_mock_db({"success": True, "data": PART, "message": "OK"})
        body = {
            "record_id": 12, "label": "p. 341",
            "source_url": "https://www.familysearch.org/ark:/1",
            "md_path": "", "status": "not_transcribed",
        }

        response = await record_documents.save_new_document(
            make_mock_request(body, user_id=9), db
        )

        assert json.loads(response.body) == PART
        sql, params = db.fetch_one.await_args.args
        assert "api.save_record_document" in sql
        payload = json.loads(params[0])
        assert payload["record_id"] == 12
        assert payload["md_path"] == ""          # blanks pass through
        assert "seq" not in payload              # the proc assigns it
        assert "id" not in payload
        assert params[1] == 9

    @pytest.mark.asyncio
    async def test_proc_rejection_is_forwarded(self):
        db = make_mock_db({
            "success": False, "message": "Record not found", "data": {},
        })

        response = await record_documents.save_new_document(
            make_mock_request({"record_id": 999, "md_path": "a.md"}), db
        )

        assert json.loads(response.body) == {
            "success": False, "message": "Record not found", "data": {},
        }


class TestSaveDocument:

    @pytest.mark.asyncio
    async def test_update_sends_the_part_id_not_a_record_id(self):
        db = make_mock_db({"success": True, "data": PART, "message": "OK"})

        response = await record_documents.save_document(
            doc_id=5,
            request=make_mock_request({"md_path": "docs/records/PR-001/02.md",
                                       "status": "raw"}),
            db=db,
        )

        assert json.loads(response.body) == PART
        payload = json.loads(db.fetch_one.await_args.args[1][0])
        assert payload["id"] == 5
        assert "record_id" not in payload

    @pytest.mark.asyncio
    async def test_keys_the_body_does_not_send_are_not_forwarded(self):
        """The proc only changes keys that are present; the route must not
        invent keys, or an edit would silently clear fields."""
        db = make_mock_db({"success": True, "data": PART, "message": "OK"})

        await record_documents.save_document(
            doc_id=5,
            request=make_mock_request({"source_url": "https://x.example/a"}),
            db=db,
        )

        payload = json.loads(db.fetch_one.await_args.args[1][0])
        assert set(payload) == {"id", "source_url"}


# =============================================================================
# List and delete
# =============================================================================

class TestListAndDelete:

    @pytest.mark.asyncio
    async def test_list_returns_the_proc_list(self):
        db = SimpleNamespace(
            fetch_one=AsyncMock(return_value={"list_record_documents": [PART]})
        )

        response = await record_documents.list_documents(record_id=12, db=db)

        assert json.loads(response.body) == [PART]

    @pytest.mark.asyncio
    async def test_list_of_nothing_is_an_empty_list(self):
        db = SimpleNamespace(
            fetch_one=AsyncMock(return_value={"list_record_documents": None})
        )

        response = await record_documents.list_documents(record_id=12, db=db)

        assert json.loads(response.body) == []

    @pytest.mark.asyncio
    async def test_delete_success_is_204(self):
        db = SimpleNamespace(fetch_one=AsyncMock(
            return_value={"delete_record_document": {"success": True}}
        ))

        response = await record_documents.delete_document(doc_id=5, db=db)

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_failure_returns_the_message(self):
        db = SimpleNamespace(fetch_one=AsyncMock(return_value={
            "delete_record_document": {
                "success": False, "message": "Document part not found",
            }
        }))

        response = await record_documents.delete_document(doc_id=5, db=db)

        assert json.loads(response.body) == {
            "success": False, "message": "Document part not found",
        }
