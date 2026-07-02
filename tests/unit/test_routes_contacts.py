"""
Unit tests for curator.web.routes.contacts

Scope: mirrors test_routes_projects.py's guard/success-shape coverage,
applied to the contact save/delete routes. Split out of
test_routes_crew_identities.py as part of the crew.py route split
(2026-07-01) — contacts.py is now its own module.

Same conventions as test_routes_projects.py:
- Unit tests only, database connection mocked throughout.
- make_mock_request is duplicated here rather than imported (see note
  below the imports) — pytest does not resolve cross-file bare imports
  in tests/unit/ under this project's discovery setup.
- Keyword arguments used for every route call, per project convention.

api.save_contact has no duplicate-name check (contacts.name is not
UNIQUE), so there is no contact-side equivalent of
TestOrganizationDuplicateNameRejection in test_routes_organizations.py.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web.routes import contacts


def make_mock_request(body: dict, user_id: int = 1) -> SimpleNamespace:
    """Build a minimal fake Request with just what the save routes read."""
    return SimpleNamespace(
        json=AsyncMock(return_value=body),
        state=SimpleNamespace(user={"user_id": user_id}),
    )


class TestSaveNewContactGuard:
    """Same empty-name short-circuit as TestSaveNewProjectGuard, applied to
    contacts. Contacts have no type_id/status_id/description fields —
    payload shape is name/title/notes instead.
    """

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "title": None, "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()  # should never be called

        response = await contacts.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_name_is_treated_as_empty(self):
        request = make_mock_request({"name": "   ", "title": None, "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await contacts.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Name is required."
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_name_key_entirely_is_treated_as_empty(self):
        request = make_mock_request({"title": None, "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await contacts.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


class TestSaveContactGuard:
    """Same guard applied to the update route — save_contact takes
    contact_id as a parameter the new-contact route doesn't have."""

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "title": None, "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await contacts.save_contact(contact_id=5, request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


class TestContactSuccessResponseShape:
    """Pins down that a successful save returns the flat contact record
    with no "success" key, which is what saveForm() in detail-panel.js
    relies on to tell success from failure.
    """

    @pytest.mark.asyncio
    async def test_success_response_has_no_success_key(self):
        request = make_mock_request({
            "name": "Andrea Flores", "title": "Purchasing Manager", "notes": None,
        })

        save_envelope = {
            "success": True,
            "data": {"id": 200},
            "message": "Contact created.",
        }
        display_record = {
            "id": 200, "name": "Andrea Flores",
            "title": "Purchasing Manager", "notes": None,
        }

        # fetch_one is called twice in the success path:
        #   1. inside call_proc, for the SELECT api.save_contact(...) call
        #   2. inside _fetch_contact_for_display, for the re-fetch by id
        db = AsyncMock()
        db.fetch_one = AsyncMock(side_effect=[
            {"save_contact": save_envelope},
            display_record,
        ])

        response = await contacts.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 200
        assert body["name"] == "Andrea Flores"
        assert body["title"] == "Purchasing Manager"


class TestGetContactNotFound:
    """_fetch_contact_for_display returning None (record doesn't exist)
    should raise a 404, matching get_project's existing behavior — not
    silently return an empty/null body."""

    @pytest.mark.asyncio
    async def test_missing_contact_raises_404(self):
        from fastapi import HTTPException

        db = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await contacts.get_contact(contact_id=9999, db=db)

        assert exc_info.value.status_code == 404