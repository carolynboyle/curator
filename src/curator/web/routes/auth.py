"""
curator.web.routes.auth - Authentication routes.

GET  /auth/login  — renders landing page with login dialog open
POST /auth/login  — validates credentials, sets session cookie, redirects
GET  /auth/logout — invalidates session, clears cookie, redirects to login
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader

from curator.web.deps import get_db_direct

logger = logging.getLogger(__name__)

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

COOKIE_NAME = "curator_session"
COOKIE_MAX_AGE_REMEMBER = 60 * 60 * 24 * 30   # 30 days in seconds
COOKIE_MAX_AGE_SESSION  = 60 * 60 * 8          # 8 hours in seconds


# ---------------------------------------------------------------------------
# GET /auth/login
# Renders the landing page with the login <dialog> forced open.
# The landing page sits behind the dialog — user sees it but can't interact.
# ---------------------------------------------------------------------------

@router.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):  # pylint: disable=unused-argument
    # request is required in the FastAPI route signature even though this
    # handler doesn't read from it directly — FastAPI uses it for request
    # context injection. Removing it would break the route.
    """Render login dialog over landing page."""
    template = env.get_template("auth/login.html")
    return HTMLResponse(template.render(
        site_title="Curator",
        site_icon="🎭",
        theme="light",
        error=error,
    ))


# ---------------------------------------------------------------------------
# POST /auth/login
# Receives form submission, calls api.login(), sets cookie on success.
# ---------------------------------------------------------------------------

@router.post("/auth/login")
async def login_submit(  # pylint: disable=too-many-locals
    # 11 local variables are all genuinely needed to process the login
    # response and construct the redirect with cookie — extracting them
    # into helpers would obscure rather than clarify this flow.
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
):
    """Process login form submission."""
    client_ip = str(request.client.host) if request.client else None
    user_agent = request.headers.get("user-agent", "")[:500]

    try:
        db = await get_db_direct()
        result = await db.fetch_one(
            "SELECT api.login(%s, %s, %s, %s, %s)",
            (username, password, remember_me, client_ip, user_agent),
        )
        await db.__aexit__(None, None, None)

        if result is None:
            return _login_error("Login failed. Please try again.")

        envelope = list(result.values())[0]
        if isinstance(envelope, str):
            envelope = json.loads(envelope)

        if not envelope.get("success"):
            return _login_error(envelope.get("message", "Login failed."))

        # Success — set cookie and redirect to crew dashboard
        data        = envelope["data"]
        token       = data["session_token"]
        crew_role   = data.get("crew_role")
        max_age     = COOKIE_MAX_AGE_REMEMBER if remember_me else COOKIE_MAX_AGE_SESSION

        # Route based on crew role — null crew_role = customer portal (future)
        redirect_url = f"/crew?role={crew_role}" if crew_role else "/"

        response = RedirectResponse(url=redirect_url, status_code=303)
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            max_age=max_age,
            httponly=True,          # JS cannot read this cookie
            samesite="strict",      # CSRF protection
            secure=False,           # Set to True when behind HTTPS (production)
        )
        return response

    except Exception as exc:  # pylint: disable=broad-except
        # Catch-all — login errors must never surface a stack trace to the
        # browser; always return a safe error message instead.
        logger.error("Login error for user %s: %s", username, exc)
        return _login_error("An unexpected error occurred. Please try again.")


# ---------------------------------------------------------------------------
# GET /auth/logout
# Invalidates server-side session, clears cookie, redirects to login.
# ---------------------------------------------------------------------------

@router.get("/auth/logout")
async def logout(request: Request):
    """Invalidate session and clear cookie."""
    token = request.cookies.get(COOKIE_NAME)

    if token:
        try:
            db = await get_db_direct()
            await db.fetch_one("SELECT api.invalidate_session(%s)", (token,))
            await db.__aexit__(None, None, None)
        except Exception as exc:  # pylint: disable=broad-except
            # Always clear the cookie even if the DB call fails — a broken
            # logout that leaves the cookie in place is worse than one that
            # silently eats a DB error.
            logger.error("Logout error: %s", exc)

    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _login_error(message: str) -> HTMLResponse:
    """Re-render login page with error message."""
    template = env.get_template("auth/login.html")
    return HTMLResponse(
        template.render(
            site_title="Curator",
            site_icon="🎭",
            theme="light",
            error=message,
        ),
        status_code=401,
    )
