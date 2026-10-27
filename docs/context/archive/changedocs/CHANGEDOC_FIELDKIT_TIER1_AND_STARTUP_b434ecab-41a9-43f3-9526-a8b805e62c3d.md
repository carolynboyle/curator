# Changedoc: `fieldkit.py` — Tier-1 type map + override merge + startup wiring

**Date:** 2026-07-04
**Reason:** Second foundation piece of the schema-driven form system,
following `api.get_field_schema()` (verified in pgAdmin). This piece
turns that function's raw column list into `viewkit.FieldDef` objects —
applying the Tier-1 type map automatically, falling back to a YAML
override file for anything Tier-1 can't decide, and crashing the app at
startup if a `*_id`/integer column has no override. No template/detail-
panel wiring yet — that's a later step, once contacts/organizations/
projects can actually be rendered through this instead of their current
hand-coded forms.

**Source verified:** `app.py`, `deps.py`, `config.py`, `exceptions.py`
viewed directly from your latest uploads before writing this. An earlier
draft of this plan assumed a `views_path`/`queries_path` on `ConfigManager`
that doesn't actually exist in your current `config.py` — corrected here;
this changedoc does not depend on that assumption anywhere.

**Scope check against `project_rules.md`:** single canonical
implementation (`fieldkit` populates `viewkit.FieldDef`, doesn't define a
competing model); no hardcoded values (Tier-1 map is an algorithmic
constant, exceptions live in YAML); override-file merge reuses
`ConfigManager._merge()` rather than duplicating that logic a second
time; tests included. One exception to flag: **entity → view-name
wiring lives as an explicit dict in `app.py`** (`_FIELDKIT_VIEWS`), not
in `curator.yaml` — reasoned about below, flagging it up front rather
than burying the decision.

---

## Decisions made this pass

**1. File location: `src/curator/web/fieldkit.py`.**
`fieldkit` needs `AsyncDBConnection` and `deps._fetch_json_scalar` —
both `curator.web` concerns. `config.py`/`exceptions.py` sit one level up
because they're framework-agnostic; `fieldkit` isn't (it's inherently
tied to rendering forms for the FastAPI app), so it belongs next to
`deps.py`, not next to `config.py`. Flagging this placement explicitly —
correct me if you pictured it elsewhere.

**2. Exception: `FieldSchemaError(CuratorError)`.**
Added directly to `curator/exceptions.py`'s existing flat hierarchy — no
separate exceptions module for `fieldkit`, since it's one exception class
next to the one module that raises it.

**3. Override file location mirrors `curator.yaml`'s existing pattern.**
Shipped default: `curator/data/fieldkit_overrides.yaml`. User override:
`~/.config/curator/fieldkit_overrides.yaml`. Merged with
`ConfigManager._merge()` — reused directly rather than copy-pasted, per
DRY. (Calling a `_`-prefixed staticmethod from another module is a little
unusual; flagging it rather than hiding it. Alternative would be
promoting `_merge` to a public method on `ConfigManager` — happy to do
that instead if you'd rather not reach across the underscore.)

**4. Entity → view-name mapping lives in `app.py`, not YAML.**
`_FIELDKIT_VIEWS = {"projects": "projects.v_project_detail", ...}` is a
small, fixed list of wiring decisions — closer to how routers get
registered explicitly in `app.py` than to user-facing config like
`curator.yaml`'s `crew.roles`. There's no deployment-time reason this
list would change without a code change alongside it (adding an entity
means adding routes, templates, etc. regardless). Flagging this as a
judgment call, not a certainty — if you'd rather this lived in
`curator.yaml` for consistency with how `views_path`-style config is
headed, easy to move later.

**5. Startup failure is unhandled, not caught-and-logged.**
Per your call — no logging infrastructure exists yet (tracked as its own
future piece), so `FieldSchemaError`'s message has to be self-explanatory
on its own: it names the exact view, the exact column, and where to add
the override. `lifespan()` does not catch it; an unhandled exception
during `lifespan` startup prevents `uvicorn` from serving requests at
all, with the exception's own traceback as the diagnostic.

**6. Unverified column assumptions in the shipped override defaults —
flagged, not guessed silently.** I could not find the actual `07_detail_
views.sql`/`v_project_detail` column list in what's been shared this
session — only that `type_id`/`status_id` are project fields (from
`06b_api_projects.sql`'s `save_project` payload shape) and that `notes`
is included on contacts/organizations views per the 07-01 changedoc.
I have **not** confirmed whether `v_project_detail` includes `parent_id`,
or whether `v_contact_detail`/`v_organization_detail` have any `*_id`
columns of their own. The shipped default file below only declares
overrides for `type_id`/`status_id` on projects — **you'll need to
verify this against `\d+ projects.v_project_detail` (etc.) in pgAdmin
before relying on it**, and add any missing `*_id` overrides yourself,
or the app will crash-at-startup exactly as designed the first time it
tries to build the projects `FieldKit` — which is actually the correct
behavior, just want you to expect it rather than be surprised by it.

---

## 1. `src/curator/exceptions.py` (edit — complete file)

**Why:** One new exception, following the existing flat style exactly
(no `pass`, docstring-only bodies, per the `CHANGEDOC_EXCEPTIONS_CLEANUP`
convention already established in this file).

### BEFORE (complete file, as uploaded)

```python
"""Curator exceptions."""


class CuratorError(Exception):
    """Base exception for Curator."""


class ConfigError(CuratorError):
    """Configuration error."""


class DatabaseError(CuratorError):
    """Database connection or query error."""
```

### AFTER (complete file — replace the whole thing with this)

```python
"""Curator exceptions."""


class CuratorError(Exception):
    """Base exception for Curator."""


class ConfigError(CuratorError):
    """Configuration error."""


class DatabaseError(CuratorError):
    """Database connection or query error."""


class FieldSchemaError(CuratorError):
    """
    Raised when fieldkit cannot build a valid field list for a view.

    Two cases:
      - api.get_field_schema(view_name) returned no columns (bad or
        misspelled view name).
      - A *_id or integer column has no matching entry in the fieldkit
        override YAML file. These columns are never defaulted to a
        plain control — see sql_conventions.md's *_id / bare-integer
        rule. Raised at app startup (fieldkit's cache is built during
        FastAPI's lifespan), by design: a misconfigured form should
        crash the app immediately, not render a broken control later.
    """
```

---

## 2. `src/curator/web/fieldkit.py` (new file)

```python
"""
curator.web.fieldkit - Schema-driven form field generation.

Introspects a v_*_detail view via api.get_field_schema(), applies a
Tier-1 Postgres-type-to-control map, and merges a YAML override file for
anything Tier-1 can't decide alone. Produces viewkit.models.FieldDef
objects directly — fieldkit does not define its own field model, it
populates the one viewkit already has (single canonical implementation,
per project_rules.md).

Fails loudly (FieldSchemaError) at construction time if any *_id column
or integer column has no matching override entry. This is deliberate:
fieldkit's cache is built once during FastAPI's lifespan startup (see
app.py), so a misconfigured view/override crashes uvicorn before it ever
serves a request, rather than rendering a broken control in front of
Felipe. See sql_conventions.md's *_id / bare-integer rule for why these
columns are never defaulted.

Override file location follows the same shipped-default / user-override
pattern as curator.yaml (see config.py):
    Shipped default:  curator/data/fieldkit_overrides.yaml
    User override:    ~/.config/curator/fieldkit_overrides.yaml
Merged with ConfigManager._merge() — reused directly rather than
duplicating that merge logic a second time.

Usage:
    from curator.web.fieldkit import FieldKit

    kit = await FieldKit.create(db, "projects.v_project_detail")
    kit.fields  # list[FieldDef], in view column order
"""

from pathlib import Path
from typing import Optional

import yaml

from dbkit.connection import AsyncDBConnection
from viewkit.models import FieldDef

from curator.config import ConfigManager
from curator.exceptions import FieldSchemaError
from curator.web.deps import _fetch_json_scalar


# Tier-1 map: information_schema.columns "data_type" string -> viewkit
# FieldDef.field_type. Algorithmic constant, not user-facing config —
# exceptions to this default (every *_id column, any bare integer, any
# field where this default is wrong for that specific column) go in the
# override YAML file, not here.
_TIER1_TYPE_MAP = {
    "character varying": "text",
    "text": "textarea",
    "boolean": "checkbox",
    "date": "date",
}

# Postgres integer types always require an explicit override — see
# sql_conventions.md's *_id / bare-integer rule. Never defaulted, even
# if a future bare (non-FK) integer column shows up.
_INTEGER_TYPES = {"bigint", "integer", "smallint"}

# Shipped default lives in curator/data/ — same directory curator.yaml
# ships from. fieldkit.py is one level deeper (curator/web/) than
# config.py (curator/), hence parents[1] rather than parent.
_DATA_DIR = Path(__file__).parents[1] / "data"
_DEFAULT_OVERRIDES = _DATA_DIR / "fieldkit_overrides.yaml"

_USER_CONFIG_DIR = Path.home() / ".config" / "curator"
_USER_OVERRIDES = _USER_CONFIG_DIR / "fieldkit_overrides.yaml"


class FieldKit:
    """
    A built list of FieldDef objects for one entity's detail view.

    Construction requires a DB call (api.get_field_schema()), so this
    class is built via the async FieldKit.create() factory rather than
    a synchronous __init__.
    """

    def __init__(self, view_name: str, fields: list[FieldDef]):
        self.view_name = view_name
        self.fields = fields

    @classmethod
    async def create(
        cls,
        db: AsyncDBConnection,
        view_name: str,
        overrides_path: Optional[Path] = None,
    ) -> "FieldKit":
        """
        Build a FieldKit for a single schema-qualified view.

        Args:
            db:             Open AsyncDBConnection.
            view_name:      Schema-qualified view name, e.g.
                            'projects.v_project_detail'.
            overrides_path: Explicit override file path — bypasses the
                            shipped-default/user-override resolution
                            entirely. Intended for tests; leave None in
                            application code.

        Returns:
            Populated FieldKit, fields in view column order.

        Raises:
            FieldSchemaError: If the view has no columns (bad or
                              misspelled view name), or any *_id /
                              integer column has no matching override.
        """
        columns = await cls._fetch_schema(db, view_name)
        if not columns:
            raise FieldSchemaError(
                f"api.get_field_schema('{view_name}') returned no "
                f"columns. Check the view name is correct and "
                f"schema-qualified, e.g. 'projects.v_project_detail'."
            )

        overrides = cls._load_overrides(overrides_path)
        entity_overrides = overrides.get(view_name, {})

        fields = [
            cls._build_field(view_name, column, entity_overrides)
            for column in columns
        ]

        return cls(view_name, fields)

    # -- Internal ---------------------------------------------------------

    @staticmethod
    async def _fetch_schema(db: AsyncDBConnection, view_name: str) -> list:
        """Call api.get_field_schema() and return the column list."""
        result = await _fetch_json_scalar(
            db, "SELECT api.get_field_schema(%s)", (view_name,)
        )
        return result or []

    @staticmethod
    def _load_overrides(overrides_path: Optional[Path]) -> dict:
        """
        Load and merge the fieldkit override YAML files.

        Args:
            overrides_path: Explicit path (tests), or None to use the
                            shipped-default/user-override resolution.

        Returns:
            Merged dict: {view_name: {column_name: {override attrs}}}.
        """
        if overrides_path is not None:
            return FieldKit._read_yaml(overrides_path)

        defaults = FieldKit._read_yaml(_DEFAULT_OVERRIDES)
        if _USER_OVERRIDES.exists():
            user = FieldKit._read_yaml(_USER_OVERRIDES)
            return ConfigManager._merge(  # pylint: disable=protected-access
                defaults, user
            )
        return defaults

    @staticmethod
    def _read_yaml(path: Path) -> dict:
        """Read a single override YAML file. Empty dict if absent."""
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data or {}

    @classmethod
    def _build_field(
        cls, view_name: str, column: dict, entity_overrides: dict
    ) -> FieldDef:
        """
        Build one FieldDef from a column dict + any override entry.

        Args:
            view_name:        Parent view name, used in error messages.
            column:           One item from api.get_field_schema()'s
                              result: {"name", "data_type", "position"}.
            entity_overrides: This view's slice of the override file:
                              {column_name: {control, label, source, ...}}.

        Returns:
            Populated FieldDef.

        Raises:
            FieldSchemaError: If the column needs an override (*_id or
                              integer type) and none is declared.
        """
        name = column["name"]
        data_type = column["data_type"]
        override = entity_overrides.get(name)

        if override is not None:
            return FieldDef(
                name=name,
                label=override.get("label", cls._default_label(name)),
                field_type=override.get("control", "text"),
                required=bool(override.get("required", False)),
                readonly=bool(override.get("readonly", False)),
                source=override.get("source"),
                placeholder=override.get("placeholder"),
                help_text=override.get("help_text"),
            )

        if name.endswith("_id") or data_type in _INTEGER_TYPES:
            raise FieldSchemaError(
                f"View '{view_name}', column '{name}' ({data_type}): "
                f"no override declared. *_id and integer columns always "
                f"require an explicit control — add an entry under "
                f"'{view_name}:' / '{name}:' in "
                f"curator/data/fieldkit_overrides.yaml (or the user "
                f"override at ~/.config/curator/fieldkit_overrides.yaml)."
            )

        return FieldDef(
            name=name,
            label=cls._default_label(name),
            field_type=_TIER1_TYPE_MAP.get(data_type, "text"),
        )

    @staticmethod
    def _default_label(name: str) -> str:
        """'target_date' -> 'Target Date'. Used when no override supplies one."""
        return name.replace("_", " ").title()
```

---

## 3. `src/curator/data/fieldkit_overrides.yaml` (new file)

**Verify this against pgAdmin before trusting it** — see point 6 above.
`type_id`/`status_id` are confirmed project fields; `source` values below
are guesses at a reasonable lookup name and are **not** wired to anything
yet (`api.get_lookup()` doesn't exist yet — that's the next piece after
this one). Treat `source` as a placeholder to revisit, not as functioning
today.

```yaml
# fieldkit_overrides.yaml - shipped defaults for fieldkit's schema-driven
# form field generation.
#
# Every *_id or integer column in a v_*_detail view MUST have an entry
# here (or in the user override at ~/.config/curator/fieldkit_overrides.yaml)
# or the app will refuse to start — see FieldSchemaError.
#
# Structure:
#   <schema-qualified view name>:
#     <column name>:
#       control:  select | text | textarea | date | number | checkbox
#       label:    Human-readable label (optional — defaults to Title Case)
#       source:   Lookup name for select controls (not yet wired to
#                 anything — api.get_lookup() doesn't exist yet)
#       required: true/false (optional, default false)
#
# UNVERIFIED as of 2026-07-04 — confirmed only that type_id/status_id
# are project fields. Check \d+ projects.v_project_detail in pgAdmin for
# the full column list (including whether parent_id is present) before
# relying on this file, and add any missing *_id entries for contacts/
# organizations if their views turn out to have FK columns of their own.

projects.v_project_detail:
  type_id:
    control: select
    label: Type
    source: project_types
  status_id:
    control: select
    label: Status
    source: project_statuses
```

---

## 4. `src/curator/web/app.py` (edit — complete file)

**Why:** Adds a FastAPI `lifespan` context manager that builds the
fieldkit cache once at startup, before any request is served, and stores
it on `app.state.fieldkit`. Nothing reads `app.state.fieldkit` yet — no
route or template changes in this pass — this step only proves the
system crashes correctly (or doesn't) at startup.

### BEFORE (complete file, as uploaded)

```python
"""
curator.web.app - FastAPI application entry point.

Creates and configures the FastAPI app instance, mounts static files,
and registers route modules. Imported by uvicorn as the ASGI entry point.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from curator.web.middleware import SessionMiddleware
from curator.web.routes import auth, landing, crew, projects, contacts, organizations

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
)

# ---------------------------------------------------------------------------
# Middleware
# Must be added before routers are registered.
# SessionMiddleware validates curator_session cookie on every request.
# ---------------------------------------------------------------------------

app.add_middleware(SessionMiddleware)

# ---------------------------------------------------------------------------
# Static files — resolved relative to this file: src/curator/web/ -> static/
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parents[3] / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Routers
# Auth must be registered first — /auth/login is the public entry point.
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(landing.router)
app.include_router(crew.router)
app.include_router(projects.router)
app.include_router(contacts.router)
app.include_router(organizations.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

### AFTER (complete file — replace the whole thing with this)

```python
"""
curator.web.app - FastAPI application entry point.

Creates and configures the FastAPI app instance, mounts static files,
and registers route modules. Imported by uvicorn as the ASGI entry point.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from dbkit.connection import AsyncDBConnection
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from curator.web.fieldkit import FieldKit
from curator.web.middleware import SessionMiddleware
from curator.web.routes import auth, landing, crew, projects, contacts, organizations

# ---------------------------------------------------------------------------
# Fieldkit cache — entity name -> schema-qualified view name.
#
# Explicit here rather than in curator.yaml: this is a small, fixed set
# of wiring decisions (which view backs which entity's form), similar in
# spirit to the router registrations below, not user-facing deployment
# config. Adding an entity means adding routes/templates alongside it
# regardless, so there's no scenario where this list changes without a
# code change happening at the same time.
# ---------------------------------------------------------------------------

_FIELDKIT_VIEWS = {
    "projects": "projects.v_project_detail",
    "contacts": "identity.v_contact_detail",
    "organizations": "identity.v_organization_detail",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Build the fieldkit cache once at startup, before serving any request.

    Opens its own connection — this runs outside any request context, so
    the per-request get_db dependency isn't available here.

    Deliberately does NOT catch FieldSchemaError. A misconfigured view or
    a *_id/integer column with no override entry must crash uvicorn
    immediately, not surface later as a broken form in front of Felipe.
    See fieldkit.py and curator/exceptions.py's FieldSchemaError
    docstring for the full reasoning.
    """
    async with AsyncDBConnection() as db:
        _app.state.fieldkit = {
            entity: await FieldKit.create(db, view_name)
            for entity, view_name in _FIELDKIT_VIEWS.items()
        }
    yield
    # No teardown — app.state.fieldkit holds FieldDef data only, no open
    # resources to release.


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# Must be added before routers are registered.
# SessionMiddleware validates curator_session cookie on every request.
# ---------------------------------------------------------------------------

app.add_middleware(SessionMiddleware)

# ---------------------------------------------------------------------------
# Static files — resolved relative to this file: src/curator/web/ -> static/
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parents[3] / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Routers
# Auth must be registered first — /auth/login is the public entry point.
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(landing.router)
app.include_router(crew.router)
app.include_router(projects.router)
app.include_router(contacts.router)
app.include_router(organizations.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

**Note on the `_app` parameter name:** FastAPI's `lifespan` signature
requires accepting the `FastAPI` instance as the sole parameter, but
inside the function it reads `_app.state...` rather than the module-level
`app` — using the parameter rather than the module global is correct
here (it's what FastAPI actually passes in), the leading underscore just
signals "this shadows nothing, it's the real one to use" since `app` as
a global also exists in this same module and could otherwise look like a
naming collision.

---

## 5. `tests/unit/test_fieldkit.py` (new file)

Follows this codebase's established unit-test conventions
(`SimpleNamespace`/`AsyncMock`, keyword arguments, one docstring per test
method, `match=` on every `pytest.raises`).

```python
"""
tests.unit.test_fieldkit - Unit tests for curator.web.fieldkit.FieldKit.

Covers:
  - Tier-1 type map applied correctly for each supported Postgres type
  - *_id columns require an override, raise FieldSchemaError if absent
  - Integer columns (non-*_id) also require an override
  - Override entries take precedence over Tier-1 defaults
  - Empty/missing schema result raises FieldSchemaError
  - Column order from api.get_field_schema() is preserved in fields

All tests mock the DB — no real connection, no real YAML file on disk
(overrides passed as an explicit dict-backed path via tmp_path).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import yaml

from curator.exceptions import FieldSchemaError
from curator.web.fieldkit import FieldKit


def _mock_db(columns: list[dict]):
    """Build a mock AsyncDBConnection whose get_field_schema() call
    returns the given column list, matching _fetch_json_scalar's
    unwrap contract: fetch_one() returns {"get_field_schema": [...]}."""
    return SimpleNamespace(
        fetch_one=AsyncMock(return_value={"get_field_schema": columns})
    )


def _write_overrides(tmp_path, data: dict):
    """Write an overrides dict to a temp YAML file and return its path."""
    path = tmp_path / "fieldkit_overrides.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tier-1 type map
# ---------------------------------------------------------------------------

class TestTier1TypeMap:
    """Columns with no override fall through to the Tier-1 map."""

    @pytest.mark.asyncio
    async def test_varchar_becomes_text(self, tmp_path):
        db = _mock_db([
            {"name": "name", "data_type": "character varying", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "text"
        assert kit.fields[0].label == "Name"

    @pytest.mark.asyncio
    async def test_text_becomes_textarea(self, tmp_path):
        db = _mock_db([
            {"name": "description", "data_type": "text", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "textarea"

    @pytest.mark.asyncio
    async def test_boolean_becomes_checkbox(self, tmp_path):
        db = _mock_db([
            {"name": "is_active", "data_type": "boolean", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "checkbox"

    @pytest.mark.asyncio
    async def test_date_becomes_date(self, tmp_path):
        db = _mock_db([
            {"name": "target_date", "data_type": "date", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "date"


# ---------------------------------------------------------------------------
# *_id / integer columns require an override
# ---------------------------------------------------------------------------

class TestRequiresOverride:
    """*_id columns and bare integer columns never get a Tier-1 default —
    they must have an explicit override entry or construction fails."""

    @pytest.mark.asyncio
    async def test_id_column_without_override_raises(self, tmp_path):
        db = _mock_db([
            {"name": "type_id", "data_type": "bigint", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        with pytest.raises(FieldSchemaError, match="type_id.*no override declared"):
            await FieldKit.create(db, "projects.v_project_detail", overrides_path)

    @pytest.mark.asyncio
    async def test_bare_integer_without_override_raises(self, tmp_path):
        db = _mock_db([
            {"name": "quantity", "data_type": "integer", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {})

        with pytest.raises(FieldSchemaError, match="quantity.*no override declared"):
            await FieldKit.create(db, "projects.v_project_detail", overrides_path)

    @pytest.mark.asyncio
    async def test_id_column_with_override_succeeds(self, tmp_path):
        db = _mock_db([
            {"name": "type_id", "data_type": "bigint", "position": 1}
        ])
        overrides_path = _write_overrides(tmp_path, {
            "projects.v_project_detail": {
                "type_id": {"control": "select", "label": "Type", "source": "project_types"}
            }
        })

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert kit.fields[0].field_type == "select"
        assert kit.fields[0].label == "Type"
        assert kit.fields[0].source == "project_types"


# ---------------------------------------------------------------------------
# Empty / missing schema result
# ---------------------------------------------------------------------------

class TestMissingView:
    """A bad or misspelled view name (api.get_field_schema returns
    NULL/empty) must fail loudly, not silently produce an empty form."""

    @pytest.mark.asyncio
    async def test_empty_columns_raises(self, tmp_path):
        db = _mock_db([])
        overrides_path = _write_overrides(tmp_path, {})

        with pytest.raises(FieldSchemaError, match="no columns"):
            await FieldKit.create(db, "projects.v_does_not_exist", overrides_path)


# ---------------------------------------------------------------------------
# Column order preserved
# ---------------------------------------------------------------------------

class TestColumnOrder:
    """Field order in kit.fields matches the order api.get_field_schema()
    returned — which itself reflects the view's CREATE VIEW column order."""

    @pytest.mark.asyncio
    async def test_fields_preserve_schema_order(self, tmp_path):
        db = _mock_db([
            {"name": "name", "data_type": "character varying", "position": 1},
            {"name": "description", "data_type": "text", "position": 2},
            {"name": "target_date", "data_type": "date", "position": 3},
        ])
        overrides_path = _write_overrides(tmp_path, {})

        kit = await FieldKit.create(db, "projects.v_project_detail", overrides_path)

        assert [f.name for f in kit.fields] == ["name", "description", "target_date"]
```

---

## Apply and verify

1. Replace `src/curator/exceptions.py` with the AFTER block above.
2. Create `src/curator/web/fieldkit.py` as shown.
3. Create `src/curator/data/fieldkit_overrides.yaml` as shown — **then
   verify its contents against pgAdmin** (`\d+ projects.v_project_detail`,
   `\d+ identity.v_contact_detail`, `\d+ identity.v_organization_detail`)
   before trusting it. Add any missing `*_id` override entries you find.
4. Replace `src/curator/web/app.py` with the AFTER block above.
5. Create `tests/unit/test_fieldkit.py` as shown.
6. `pytest tests/unit/test_fieldkit.py -v` — all new tests should pass
   without touching a real database (fully mocked).
7. `pylint src/` — should stay clean; flag anything new (the
   `protected-access` disable on `ConfigManager._merge()` is deliberate
   and documented inline, not a leftover warning).
8. **Restart uvicorn for real** — this is the actual test that matters.
   If `fieldkit_overrides.yaml` is missing an entry for a real `*_id`
   column in one of the three views, the app should refuse to start and
   the traceback should clearly name the view, the column, and where to
   add the fix. That crash — assuming it happens — is success, not a
   bug: confirm the message is actually legible before treating it as
   done.
9. If step 8 doesn't crash: manually double check that means the
   override file genuinely covers every `*_id`/integer column in all
   three views, not that something silently swallowed the check.

---

## What's still not done after this

- `api.get_lookup()` doesn't exist — the `source:` values in the override
  file are placeholders, not functioning lookups yet.
- Nothing renders through `fieldkit` yet — `_detail_panel.html`/
  `detail-panel.js` are unchanged, still the old hand-coded projects-
  shaped form. `app.state.fieldkit` is built and available, but unused.
- Tasks still has no view, no override entries, no api functions — this
  piece proves the *engine* works against the three existing entities;
  Tasks joining it is a later, separate step.
