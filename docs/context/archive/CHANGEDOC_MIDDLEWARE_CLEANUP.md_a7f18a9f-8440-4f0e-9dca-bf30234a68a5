# Changedoc: middleware.py — move logging import, document too-few-public-methods

**File:** `src/curator/web/middleware.py`
**Date:** 2026-06-29
**Source verified:** Viewed directly from Carolyn's upload before writing
this changedoc.

## Summary

Two pylint warnings, both purely structural — no logic changes:

1. **`C0415: Import outside toplevel`** — `import logging` was inside the
   `except` block at the bottom of `dispatch()`, the only place it's used.
   Moved to the top-level imports. No circular-import or lazy-loading
   reason for it to be local — it was just placed where it's used. As a
   minor side benefit, this also means the very first authentication
   error doesn't pay the (small) cost of resolving the `logging` module
   at the moment something's already going wrong.

2. **`R0903: Too few public methods (1/2)`** — unlike the same warning on
   `formkit.py` (which was a miscount), this one is accurate:
   `SessionMiddleware` genuinely has only one method, `dispatch()`. But
   that's correct by design, not a gap — `BaseHTTPMiddleware`'s entire
   contract from Starlette is a single `dispatch()` method. Resolved with
   an inline `# pylint: disable` comment explaining why, not by adding
   methods that don't belong here.

No other line in this file changed.

---

## BEFORE (complete file, as uploaded)

```python
"""
curator.web.middleware - Session authentication middleware.

Validates the curator_session cookie on every request.
Injects user context into request.state.user for authenticated requests.
Redirects unauthenticated requests to /auth/login.

Public paths bypass authentication entirely:
    /auth/login
    /auth/logout
    /static/
    /health

Usage (in app.py):
    from curator.web.middleware import SessionMiddleware
    app.add_middleware(SessionMiddleware)
"""

import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from curator.web.deps import get_db_direct

# Paths that never require authentication
PUBLIC_PATHS = {"/auth/login", "/auth/logout", "/health"}
PUBLIC_PREFIXES = ("/static/",)

COOKIE_NAME = "curator_session"


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Validate session cookie on every request.

    Sets request.state.user to the user context dict on success.
    Sets request.state.user to None for public paths.
    Redirects to /auth/login if cookie is missing or invalid.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Public paths — no auth check needed
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            request.state.user = None
            return await call_next(request)

        # Read session token from cookie
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return RedirectResponse(url="/auth/login", status_code=302)

        # Validate session against the database
        try:
            db = await get_db_direct()
            result = await db.fetch_one(
                "SELECT api.validate_session(%s, %s)",
                (token, str(request.client.host) if request.client else None),
            )
            await db.__aexit__(None, None, None)

            if result is None:
                return RedirectResponse(url="/auth/login", status_code=302)

            # fetch_one returns a dict; the proc result is under the function name key
            envelope = list(result.values())[0]
            if isinstance(envelope, str):
                envelope = json.loads(envelope)

            if not envelope.get("success"):
                response = RedirectResponse(url="/auth/login", status_code=302)
                response.delete_cookie(COOKIE_NAME)
                return response

            # Inject user context into request state
            request.state.user = envelope["data"]

        except Exception as exc:  # pylint: disable=broad-except
            # Log and fail safe — never crash on auth middleware error
            import logging
            logging.getLogger(__name__).error("Session middleware error: %s", exc)
            return RedirectResponse(url="/auth/login", status_code=302)

        return await call_next(request)
```

## AFTER (complete file — replace the whole thing with this)

```python
"""
curator.web.middleware - Session authentication middleware.

Validates the curator_session cookie on every request.
Injects user context into request.state.user for authenticated requests.
Redirects unauthenticated requests to /auth/login.

Public paths bypass authentication entirely:
    /auth/login
    /auth/logout
    /static/
    /health

Usage (in app.py):
    from curator.web.middleware import SessionMiddleware
    app.add_middleware(SessionMiddleware)
"""

import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from curator.web.deps import get_db_direct

# Paths that never require authentication
PUBLIC_PATHS = {"/auth/login", "/auth/logout", "/health"}
PUBLIC_PREFIXES = ("/static/",)

COOKIE_NAME = "curator_session"


class SessionMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    # BaseHTTPMiddleware's entire contract is a single dispatch() method —
    # this is not a design gap, it's how Starlette middleware is meant to
    # look. Disabled rather than restructured.
    """
    Validate session cookie on every request.

    Sets request.state.user to the user context dict on success.
    Sets request.state.user to None for public paths.
    Redirects to /auth/login if cookie is missing or invalid.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Public paths — no auth check needed
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            request.state.user = None
            return await call_next(request)

        # Read session token from cookie
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return RedirectResponse(url="/auth/login", status_code=302)

        # Validate session against the database
        try:
            db = await get_db_direct()
            result = await db.fetch_one(
                "SELECT api.validate_session(%s, %s)",
                (token, str(request.client.host) if request.client else None),
            )
            await db.__aexit__(None, None, None)

            if result is None:
                return RedirectResponse(url="/auth/login", status_code=302)

            # fetch_one returns a dict; the proc result is under the function name key
            envelope = list(result.values())[0]
            if isinstance(envelope, str):
                envelope = json.loads(envelope)

            if not envelope.get("success"):
                response = RedirectResponse(url="/auth/login", status_code=302)
                response.delete_cookie(COOKIE_NAME)
                return response

            # Inject user context into request state
            request.state.user = envelope["data"]

        except Exception as exc:  # pylint: disable=broad-except
            # Log and fail safe — never crash on auth middleware error
            logging.getLogger(__name__).error("Session middleware error: %s", exc)
            return RedirectResponse(url="/auth/login", status_code=302)

        return await call_next(request)
```

---

## What did NOT change

- No logic in `dispatch()` changed — same flow, same checks, same
  redirects, same cookie handling.
- The `# pylint: disable=broad-except` on the `except Exception` line is
  pre-existing and untouched — that one's already justified by the
  surrounding comment ("never crash on auth middleware error").
- `json` import position unchanged — it was already at the top.

## Verification steps

1. Replace the file as shown above.
2. Run `pylint src/curator/web/middleware.py` — should show zero warnings.
3. This file can't be meaningfully unit-tested in isolation (it depends on
   Starlette's request/response cycle and a live DB connection via
   `get_db_direct()`), so verification is restarting the app and
   confirming the full auth flow still works:
   - Visiting any protected route while logged out redirects to
     `/auth/login`.
   - Logging in successfully lands on `/crew?role=<your role>`.
   - An invalid/expired session cookie redirects to login and clears the
     cookie.
   - A request to `/static/...` or `/health` does not trigger a DB call
     (public path bypass still works).
