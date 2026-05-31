# Database Login Design

## Overview
Multi-database card-based authentication system. Each database (PostgreSQL, SQLite, etc.) has its own card on the index. Users log in per-database; login state is tracked via session cookies. No mid-session role switching. One database at a time.

---

## Decided

### Architecture & Security
- **Server-side only** — Backend handles all credentials. Frontend never sees passwords.
- **Session cookies** — FastAPI session management (implementation TBD).
- **Active logout** — Button in database UI clears session and `.pgpass` entry.
- **Idle timeout** — Automatic logout after N minutes of inactivity (configurable, TBD how tracked).
- **No role switching** — Users log out and back in to change roles.
- **Container-ready** — Design assumes future migration from uvicorn → nginx + containers.

### User Experience
- **Card-based index** — Database cards live on index; clicking reveals inline login form.
- **Inline expansion** — Login form appears inline on card (not modal, not separate page).
- **No simultaneous logins** — One database at a time.
- **Card state indicators**:
  - Not logged in: Card shows login interface when clicked.
  - Logged in: Card displays database name as a clickable button → enter that database.
- **Post-login feedback** — Toast notification: "Login successful" + button becomes visible on card.
- **Failed login** — Error message displayed in form (standard CRUD security practices, expert review needed).
- **Logout** — Clears session cookie and removes `.pgpass` entry; user returns to index.

### Documentation & Transparency
- **Cookie disclosure** — Transparent explanation for all users (not conditional on jurisdiction).
  - Info icon or banner on index explaining: "Session cookies required to maintain login. Not tracking cookies."
  - Link to `COOKIES_AND_PRIVACY.md` for details.
  - Explain why blocking all cookies will prevent database access.
- **Rationale** — Linux users are cookie-averse; transparency is essential.

### Configuration
- **Card configuration** — YAML file(s) per database type (PostgreSQL, SQLite, etc.).
  - Connection info (host, port, database name, available roles) in YAML, not hardcoded.
  - Structure varies by database type (PG YAML ≠ SQLite YAML).
- **Separate config files** — User authentication config separate from connection/card config.

---

## Deferred / TBD

### Session Management (TBD)
1. **Implementation choice:**
   - FastAPI `Depends(get_session)` pattern, or middleware?
   - Signed opaque cookie vs. JWT?
   - Session storage: in-memory (bare metal), Redis/database (containers)?

2. **Idle timeout tracking:**
   - Server-side last-request timestamp, or just expiry time?
   - Silent 401 + redirect, or proactive warning banner?

3. **`.pgpass` lifecycle:**
   - Entry format: single line per database (host/port/database/user/password)?
   - Collision handling: what if `.pgpass` already has manual entries?
   - On logout: remove entry from `.pgpass` or just clear session?
   - On container start: how is `.pgpass` seeded/mounted?

### Brute Force Protection (Expert Review Needed)
1. **Rate limiting:**
   - fail2ban-like approach for HTTP endpoints?
   - Are there Python-native fail2ban alternatives (e.g., Flask-Limiter, but for FastAPI)?
   - Guidance on implementing account lockout / exponential backoff?

2. **Failed login handling:**
   - Standard CRUD security practices (timing attack resistance, error message specificity).
   - This is not Carolyn's expertise; needs external review.

### Card State Queries (TBD)
1. **Index page startup:**
   - How does index know which databases user is logged into?
   - Fetch from backend on page load?
   - Check session cookies directly?

2. **Logged-in indicator:**
   - Database name as button text is sufficient (decided).
   - No additional "logged in as role X" text needed.

### Container & Multi-instance (TBD)
1. **`.pgpass` location abstraction:**
   - Bare metal: `~/.pgpass`
   - Container: mounted volume or different path?
   - Single `.pgpass` for all databases, or separate files?

2. **Session persistence across container restarts:**
   - Acceptable to log users out on restart?
   - Or move session storage to Redis/database?

3. **`.pgpass` seeding in containerized environment:**
   - How are credentials injected into container at startup?
   - Environment variables? Mounted secrets? Init script?

### Database Configuration (TBD)
1. **YAML structure for cards:**
   - Example: PostgreSQL card (`name`, `slug`, `description`, `available_roles`, `connection_params`)?
   - Example: SQLite card (different fields)?
   - Required vs. optional fields per database type?

2. **Connection info storage:**
   - Single central config file, or per-database YAML?
   - How are credentials (password hash?) stored separately from connection info?

---

## Next Steps (When Ready to Code)

1. **Nail down session implementation** — decide on FastAPI session pattern, storage mechanism, and cookie signing strategy.
2. **Brute force protection research** — investigate fail2ban alternatives for Python/FastAPI; document approach.
3. **Define YAML structures** — create example configs for PostgreSQL and SQLite cards.
4. **Write `.pgpass` handler** — abstraction layer for reading/writing `.pgpass` across bare metal and containerized environments.
5. **Build auth endpoint** — `POST /auth/database/{db_slug}` with credential validation, session creation, `.pgpass` entry writing.
6. **Build index page** — card grid with inline login form reveal; session state detection.
7. **Implement idle timeout** — background tracking of last-request timestamp; redirect on timeout.
8. **Test container readiness** — verify design assumptions hold in containerized environment.


**Future consideration:** Multi-database simultaneous login may be necessary for some workflows (e.g., data comparison, multi-project access). Current design enforces one-at-a-time; 
supporting simultaneous logins would require:
- Separate session cookies per database (or namespaced cookie storage).
- Card state tracking for multiple databases.
- Potential UX complexity (which database is "active"?).
- Session cleanup on logout (remove all vs. per-database).
Defer until requirement surfaces.
---

## Files to Create When Ready

- `login_design.md` (this file, for reference during implementation)
- `COOKIES_AND_PRIVACY.md` (user-facing privacy policy)
- `login_implementation_guide.md` (step-by-step when coding starts)
- Example YAML structures for database cards (PG + SQLite templates)
