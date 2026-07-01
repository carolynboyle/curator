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
