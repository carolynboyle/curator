"""
repro.py — standalone reproduction, no pytest involved.

Run with: python3 repro.py

This calls crew.save_new_project() exactly the way the failing pytest
test does, but with no pytest, no pytest-asyncio, no fixtures, no test
collection — just asyncio.run() and a plain function call. If this
script ALSO shows the AttributeError, the bug is in crew.py or the
mock shapes, not in pytest/pytest-asyncio. If this script WORKS
correctly, the bug is specific to how pytest-asyncio is invoking the
test, and we've learned something important.
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from curator.web.routes import crew


def make_mock_request(body: dict, user_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        json=AsyncMock(return_value=body),
        state=SimpleNamespace(user={"user_id": user_id}),
    )


async def main():
    request = make_mock_request({
        "name": "Existing Project", "type_id": None,
        "status_id": None, "description": None,
    })

    rejection_envelope = {
        "success": False,
        "data": {"conflicting_id": 99},
        "message": "A project with that name already exists.",
    }

    db = SimpleNamespace(fetch_one=AsyncMock(return_value={
        "save_project": rejection_envelope
    }))

    print("Before call: db =", db)
    print("Before call: db.fetch_one =", db.fetch_one)
    print()

    response = await crew.save_new_project(request, db)

    print()
    print("SUCCESS — no exception raised")
    print("response.body =", response.body)
    body = json.loads(response.body)
    print("parsed body =", body)


if __name__ == "__main__":
    asyncio.run(main())
