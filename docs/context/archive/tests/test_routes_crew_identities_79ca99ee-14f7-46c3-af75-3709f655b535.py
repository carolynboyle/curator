"""
Unit tests for curator.web.routes.crew — contacts and organizations routes

Scope: mirrors the existing TestSaveNewProjectGuard / TestSaveProjectGuard /
TestProcRejectionPassthrough coverage in test_routes_crew.py, applied to
the new save_new_contact / save_contact / save_new_organization /
save_organization routes added alongside api.save_contact and
api.save_organization.

Same conventions as test_routes_crew.py:
- Unit tests only, database connection mocked throughout.
- make_mock_request is duplicated here rather than imported (see note
  below the imports) — pytest does not resolve cross-file bare imports
  in tests/unit/ under this project's discovery setup.
- Keyword arguments used for every route call, per project convention.

One real difference from the project tests: api.save_contact has no
duplicate-name check (contacts.name is not UNIQUE), so there is no
contact-side equivalent of TestProcRejectionPassthrough's duplicate-name
test — only organizations gets that coverage, matching organizations.name
being UNIQUE.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web.routes import crew


# ---------------------------------------------------------------------------
# Fixtures
#
# Duplicated from test_routes_crew.py rather than imported — pytest does
# not add tests/unit/ to the import path by bare module name in this
# project's discovery setup, so `from test_routes_crew import ...` fails
# at collection. Keeping these in sync by hand is a known tradeoff; if
# either helper's shape ever changes, both files need the same edit.
# ---------------------------------------------------------------------------

def make_mock_request(body: dict, user_id: int = 1) -> SimpleNamespace:
    """Build a minimal fake Request with just what the save routes read."""
    return SimpleNamespace(
        json=AsyncMock(return_value=body),
        state=SimpleNamespace(user={"user_id": user_id}),
    )


# ---------------------------------------------------------------------------
# save_new_contact — empty-name guard
# ---------------------------------------------------------------------------

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

        response = await crew.save_new_contact(request=request, db=db)

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

        response = await crew.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Name is required."
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_name_key_entirely_is_treated_as_empty(self):
        request = make_mock_request({"title": None, "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await crew.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


# ---------------------------------------------------------------------------
# save_contact (update route) — same empty-name guard
# ---------------------------------------------------------------------------

class TestSaveContactGuard:
    """Same guard applied to the update route — save_contact takes
    contact_id as a parameter the new-contact route doesn't have."""

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "title": None, "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await crew.save_contact(contact_id=5, request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


# ---------------------------------------------------------------------------
# save_new_contact / save_contact — success response shape
# ---------------------------------------------------------------------------

class TestContactSuccessResponseShape:
    """Same contract test as TestProcRejectionPassthrough.
    test_success_response_has_no_success_key — pins down that a successful
    save returns the flat contact record with no "success" key, which is
    what saveForm() in detail-panel.js relies on to tell success from
    failure.
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
        #   1. inside _call_proc, for the SELECT api.save_contact(...) call
        #   2. inside _fetch_contact_for_display, for the re-fetch by id
        db = AsyncMock()
        db.fetch_one = AsyncMock(side_effect=[
            {"save_contact": save_envelope},
            display_record,
        ])

        response = await crew.save_new_contact(request=request, db=db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 200
        assert body["name"] == "Andrea Flores"
        assert body["title"] == "Purchasing Manager"


# ---------------------------------------------------------------------------
# save_new_organization — empty-name guard
# ---------------------------------------------------------------------------

class TestSaveNewOrganizationGuard:
    """Same empty-name short-circuit, applied to organizations. Payload
    shape is name/notes only — no title field on organizations."""

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await crew.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_whitespace_only_name_is_treated_as_empty(self):
        request = make_mock_request({"name": "   ", "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await crew.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Name is required."
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_name_key_entirely_is_treated_as_empty(self):
        request = make_mock_request({"notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await crew.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


# ---------------------------------------------------------------------------
# save_organization (update route) — same empty-name guard
# ---------------------------------------------------------------------------

class TestSaveOrganizationGuard:
    """Same guard applied to the update route."""

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await crew.save_organization(
            organization_id=10, request=request, db=db
        )

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


# ---------------------------------------------------------------------------
# save_new_organization / save_organization — duplicate-name rejection
# ---------------------------------------------------------------------------

class TestOrganizationDuplicateNameRejection:
    """organizations.name IS UNIQUE, unlike contacts.name — this is the
    one place contact and organization route coverage genuinely diverges,
    not just a mechanical copy. Mirrors
    TestProcRejectionPassthrough.test_duplicate_name_rejection_forwards_data_and_message.
    """

    @pytest.mark.asyncio
    async def test_duplicate_name_rejection_forwards_message(self):
        request = make_mock_request({"name": "Bailey Ltd", "notes": None})

        rejection_envelope = {
            "success": False,
            "data": None,
            "message": "An organization with that name already exists.",
        }

        db = AsyncMock()
        db.fetch_one = AsyncMock(return_value={
            "save_organization": rejection_envelope
        })

        response = await crew.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "An organization with that name already exists."


# ---------------------------------------------------------------------------
# save_new_organization — success response shape
# ---------------------------------------------------------------------------

class TestOrganizationSuccessResponseShape:
    """Same contract as TestContactSuccessResponseShape — success returns
    the flat record, no "success" key."""

    @pytest.mark.asyncio
    async def test_success_response_has_no_success_key(self):
        request = make_mock_request({"name": "New Vendor Co", "notes": None})

        save_envelope = {
            "success": True,
            "data": {"id": 301},
            "message": "Organization created.",
        }
        display_record = {"id": 301, "name": "New Vendor Co", "notes": None}

        db = AsyncMock()
        db.fetch_one = AsyncMock(side_effect=[
            {"save_organization": save_envelope},
            display_record,
        ])

        response = await crew.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 301
        assert body["name"] == "New Vendor Co"


# ---------------------------------------------------------------------------
# get_contact / get_organization — 404 on not found
# ---------------------------------------------------------------------------

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
            await crew.get_contact(contact_id=9999, db=db)

        assert exc_info.value.status_code == 404


class TestGetOrganizationNotFound:
    @pytest.mark.asyncio
    async def test_missing_organization_raises_404(self):
        from fastapi import HTTPException

        db = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await crew.get_organization(organization_id=9999, db=db)

        assert exc_info.value.status_code == 404
