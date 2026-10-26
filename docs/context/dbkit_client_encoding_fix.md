# Changedoc: dbkit — Add `client_encoding` to Connection Calls

**Date**: 2026-06-24  
**File**: `python/dbkit/dbkit/connection.py`  
**Type**: Bug fix  
**Git commit message**: `patch: set client_encoding utf-8 on all connections`

---

## Problem

psycopg 3.3.4 changed behavior for `SQL_ASCII` databases: text columns are
returned as `bytes` objects instead of `str` when no client encoding is
explicitly set. This caused Curator v2 (running psycopg 3.3.4 on Python 3.13)
to display `b'Project Name'` instead of `Project Name` in all template output.

Curator v1 (running psycopg 3.3.3 on Python 3.11) was unaffected because the
older psycopg decoded text automatically without requiring an explicit encoding.

The fix is to tell psycopg explicitly what encoding to use at connection time.
This makes dbkit's behavior consistent across psycopg versions and Python
versions regardless of the database's `server_encoding` setting.

---

## Changes

### `DBConnection.__enter__` (sync connection)

**BEFORE**:
```python
def __enter__(self) -> "DBConnection":
    try:
        self._conn = psycopg.connect(
            host=self._config["host"],
            port=self._config["port"],
            dbname=self._config["dbname"],
            user=self._config["user"],
            row_factory=dict_row,
        )
    except psycopg.OperationalError as exc:
        raise DBConnectionError(f"Could not connect to database: {exc}") from exc
    return self
```

**AFTER**:
```python
def __enter__(self) -> "DBConnection":
    try:
        self._conn = psycopg.connect(
            host=self._config["host"],
            port=self._config["port"],
            dbname=self._config["dbname"],
            user=self._config["user"],
            row_factory=dict_row,
            client_encoding="utf-8",
        )
    except psycopg.OperationalError as exc:
        raise DBConnectionError(f"Could not connect to database: {exc}") from exc
    return self
```

**Why**: Explicitly sets the client encoding so psycopg decodes text columns
to `str` regardless of the database's `server_encoding` setting or psycopg version.

---

### `AsyncDBConnection.__aenter__` (async connection)

**BEFORE**:
```python
async def __aenter__(self) -> "AsyncDBConnection":
    try:
        self._conn = await psycopg.AsyncConnection.connect(
            host=self._config["host"],
            port=self._config["port"],
            dbname=self._config["dbname"],
            user=self._config["user"],
            row_factory=dict_row,
        )
    except psycopg.OperationalError as exc:
        raise DBConnectionError(f"Could not connect to database: {exc}") from exc
    return self
```

**AFTER**:
```python
async def __aenter__(self) -> "AsyncDBConnection":
    try:
        self._conn = await psycopg.AsyncConnection.connect(
            host=self._config["host"],
            port=self._config["port"],
            dbname=self._config["dbname"],
            user=self._config["user"],
            row_factory=dict_row,
            client_encoding="utf-8",
        )
    except psycopg.OperationalError as exc:
        raise DBConnectionError(f"Could not connect to database: {exc}") from exc
    return self
```

**Why**: Same fix for the async path used by FastAPI/Curator.

---

## After Applying

1. Commit and push to `dev-utils` GitHub repo
2. On wcyjv20, update the curator v2 venv:
   ```bash
   cd ~/projects/curator
   source .venv/bin/activate
   pip install --force-reinstall git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/dbkit
   ```
   Or via setupkit if configured on this machine:
   ```bash
   setupkit install dbkit --force
   ```
3. Restart Curator and verify text columns display correctly
4. On any other machine running dbkit, run `setupkit install dbkit --force` to pick up the fix
