"""
Unit tests for curator.web.routes.organizations

Scope: mirrors test_routes_projects.py's guard/success-shape/rejection
coverage, applied to the organization save/delete routes. Split out of
test_routes_crew_identities.py as part of the crew.py route split
(2026-07-01) — organizations.py is now its own module.

Same conventions as test_routes_contacts.py. organizations.name IS
UNIQUE (unlike contacts.name), so this file carries the duplicate-name
rejection coverage that contacts doesn't need.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from curator.web.routes import organizations


def make_mock_request(body: dict, user_id: int = 1) -> SimpleNamespace:
    """Build a minimal fake Request with just what the save routes read."""
    return SimpleNamespace(
        json=AsyncMock(return_value=body),
        state=SimpleNamespace(user={"user_id": user_id}),
    )


class TestSaveNewOrganizationGuard:
    """Same empty-name short-circuit, applied to organizations. Payload
    shape is name/notes only — no title field on organizations."""

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await organizations.save_new_organization(request=request, db=db)

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

        response = await organizations.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "Name is required."
        db.fetch_one.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_name_key_entirely_is_treated_as_empty(self):
        request = make_mock_request({"notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await organizations.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        db.fetch_one.assert_not_awaited()


class TestSaveOrganizationGuard:
    """Same guard applied to the update route."""

    @pytest.mark.asyncio
    async def test_empty_name_returns_without_touching_db(self):
        request = make_mock_request({"name": "", "notes": None})
        db = AsyncMock()
        db.fetch_one = AsyncMock()

        response = await organizations.save_organization(
            organization_id=10, request=request, db=db
        )

        body = json.loads(response.body)
        assert body == {
            "success": False,
            "message": "Name is required.",
            "data": None,
        }
        db.fetch_one.assert_not_awaited()


class TestOrganizationDuplicateNameRejection:
    """organizations.name IS UNIQUE, unlike contacts.name — this is the
    one place contact and organization route coverage genuinely diverges,
    not just a mechanical copy.
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

        response = await organizations.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert body["success"] is False
        assert body["message"] == "An organization with that name already exists."


class TestOrganizationSuccessResponseShape:
    """Success returns the flat record, no "success" key."""

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

        response = await organizations.save_new_organization(request=request, db=db)

        body = json.loads(response.body)
        assert "success" not in body
        assert body["id"] == 301
        assert body["name"] == "New Vendor Co"


class TestGetOrganizationNotFound:
    @pytest.mark.asyncio
    async def test_missing_organization_raises_404(self):
        from fastapi import HTTPException

        db = AsyncMock()
        db.fetch_one = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await organizations.get_organization(organization_id=9999, db=db)

        assert exc_info.value.status_code == 404