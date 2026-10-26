"""
dbkit.connection - Database connection management.

Provides synchronous and asynchronous context managers for database
connections, with consistent query methods and exception wrapping.

Loads connection config from ~/.config/dev-utils/config.yaml under
the 'dbkit:' key. Passwords are handled by ~/.pgpass — no credentials
in config files.

Sync usage:
    from dbkit.connection import DBConnection

    with DBConnection() as db:
        row = db.fetch_one("SELECT * FROM projects WHERE slug = %s", ("my-project",))

Async usage:
    from dbkit.connection import AsyncDBConnection

    async with AsyncDBConnection() as db:
        row = await db.fetch_one("SELECT * FROM projects WHERE slug = %s", ("my-project",))

Config (~/.config/dev-utils/config.yaml):
    dbkit:
      host: 192.168.x.x
      port: 5432
      dbname: projects
      user: carolyn
"""

from pathlib import Path
from typing import Any, Optional
import os
import yaml
import psycopg
from psycopg.rows import dict_row

from dbkit.exceptions import ConfigError, DBConnectionError, QueryError
# pylint: disable=no-member

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path.home() / ".config" / "dev-utils" / "config.yaml"

_REQUIRED_KEYS = ("host", "port", "dbname", "user")



_ENV_KEYS = {
    "host":   "DBKIT_HOST",
    "port":   "DBKIT_PORT",
    "dbname": "DBKIT_DBNAME",
    "user":   "DBKIT_USER",
}

def _load_config(config_path: Optional[Path] = None) -> dict:
    """
    Load dbkit connection config from environment variables or config file.

    Environment variables are checked first. If all four are present,
    the config file is not read. If any are missing, falls back to
    ~/.config/dev-utils/config.yaml (or config_path if provided).

    Args:
        config_path: Override config file path. Defaults to
                     ~/.config/dev-utils/config.yaml.

    Returns:
        Dict of connection parameters.

    Raises:
        ConfigError: If neither env vars nor config file provide
                     all required keys.
    """
    # Try environment variables first
    env_cfg = {k: os.environ.get(env) for k, env in _ENV_KEYS.items()}
    if all(env_cfg.values()):
        env_cfg["port"] = int(env_cfg["port"])
        return env_cfg

    # Fall back to config file
    path = config_path or _CONFIG_PATH
    if not path.exists():
        missing_env = [v for v in _ENV_KEYS.values() if not os.environ.get(v)]
        raise ConfigError(
            f"No config file found at {path} and missing environment variables: "
            f"{', '.join(missing_env)}. "
            f"Run the dbkit setup script or set the environment variables."
        )

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        raise ConfigError(f"Could not read config file {path}: {exc}") from exc

    if not data or "dbkit" not in data:
        raise ConfigError(f"No 'dbkit' section found in {path}")

    cfg = data["dbkit"]
    missing = [k for k in _REQUIRED_KEYS if k not in cfg]
    if missing:
        raise ConfigError(f"Missing required dbkit config keys: {', '.join(missing)}")

    return cfg


# ---------------------------------------------------------------------------
# Synchronous connection
# ---------------------------------------------------------------------------

class DBConnection:
    """
    Synchronous database connection context manager.

    Wraps psycopg connection and cursor lifecycle. All query methods
    return rows as dicts. psycopg exceptions are wrapped in dbkit
    exceptions so callers do not need to import psycopg directly.

    Usage:
        with DBConnection() as db:
            rows = db.fetch_all("SELECT * FROM projects")
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialise with connection config.

        Args:
            config_path: Override config file path (useful for testing).
        """
        self._config = _load_config(config_path)
        self._conn = None

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

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn is None:
            return False
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._conn.close()
        self._conn = None
        return False

    # -- Query methods --------------------------------------------------------

    def execute(self, sql: str, params: tuple = ()) -> None:
        """
        Execute a statement with no return value.

        Use for INSERT, UPDATE, DELETE.

        Args:
            sql:    Parameterized SQL string. Use %s for placeholders.
            params: Query parameters. Always pass as a tuple, even for
                    a single value: ("value",)

        Raises:
            QueryError: If the statement fails to execute.
        """
        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, params)
        except psycopg.Error as exc:
            raise QueryError(f"Query failed: {exc}") from exc

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """
        Fetch a single row as a dict.

        Args:
            sql:    Parameterized SQL string.
            params: Query parameters.

        Returns:
            Dict of column name → value, or None if no row matched.

        Raises:
            QueryError: If the query fails to execute.
        """
        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()
        except psycopg.Error as exc:
            raise QueryError(f"Query failed: {exc}") from exc

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        """
        Fetch all matching rows as a list of dicts.

        Args:
            sql:    Parameterized SQL string.
            params: Query parameters.

        Returns:
            List of dicts. Empty list if no rows matched.

        Raises:
            QueryError: If the query fails to execute.
        """
        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        except psycopg.Error as exc:
            raise QueryError(f"Query failed: {exc}") from exc

    def fetch_scalar(self, sql: str, params: tuple = ()) -> Any:
        """
        Fetch a single value from the first column of the first row.

        Use for COUNT queries, existence checks, or single-column lookups.

        Args:
            sql:    Parameterized SQL string.
            params: Query parameters.

        Returns:
            The value, or None if no row matched.

        Raises:
            QueryError: If the query fails to execute.
        """
        try:
            with self._conn.cursor(row_factory=psycopg.rows.scalar_row) as cur:
                cur.execute(sql, params)
                return cur.fetchone()
        except psycopg.Error as exc:
            raise QueryError(f"Query failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Asynchronous connection
# ---------------------------------------------------------------------------

class AsyncDBConnection:
    """
    Asynchronous database connection context manager.

    Same interface as DBConnection but all query methods are coroutines.
    Requires an async runtime (e.g. asyncio, FastAPI).

    Usage:
        async with AsyncDBConnection() as db:
            rows = await db.fetch_all("SELECT * FROM projects")
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialise with connection config.

        Args:
            config_path: Override config file path (useful for testing).
        """
        self._config = _load_config(config_path)
        self._conn = None

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

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._conn is None:
            return False
        if exc_type is None:
            await self._conn.commit()
        else:
            await self._conn.rollback()
        await self._conn.close()
        self._conn = None
        return False

    # -- Query methods --------------------------------------------------------

    async def execute(self, sql: str, params: tuple = ()) -> None:
        """
        Execute a statement with no return value.

        Use for INSERT, UPDATE, DELETE.

        Args:
            sql:    Parameterized SQL string. Use %s for placeholders.
            params: Query parameters.

        Raises:
            QueryError: If the statement fails to execute.
        """
        try:
            async with self._conn.cursor() as cur:
                await cur.execute(sql, params)
        except psycopg.Error as exc:
            raise QueryError(f"Query failed: {exc}") from exc

    async def fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """
        Fetch a single row as a dict.

        Args:
            sql:    Parameterized SQL string.
            params: Query parameters.

        Returns:
            Dict of column name → value, or None if no row matched.

        Raises:
            QueryError: If the query fails to execute.
        """
        try:
            async with self._conn.cursor() as cur:
                await cur.execute(sql, params)
                return await cur.fetchone()
        except psycopg.Error as exc:
            raise QueryError(f"Query failed: {exc}") from exc

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        """
        Fetch all matching rows as a list of dicts.

        Args:
            sql:    Parameterized SQL string.
            params: Query parameters.

        Returns:
            List of dicts. Empty list if no rows matched.

        Raises:
            QueryError: If the query fails to execute.
        """
        try:
            async with self._conn.cursor() as cur:
                await cur.execute(sql, params)
                return await cur.fetchall()
        except psycopg.Error as exc:
            raise QueryError(f"Query failed: {exc}") from exc

    async def fetch_scalar(self, sql: str, params: tuple = ()) -> Any:
        """
        Fetch a single value from the first column of the first row.

        Args:
            sql:    Parameterized SQL string.
            params: Query parameters.

        Returns:
            The value, or None if no row matched.

        Raises:
            QueryError: If the query fails to execute.
        """
        try:
            async with self._conn.cursor(row_factory=psycopg.rows.scalar_row) as cur:
                await cur.execute(sql, params)
                return await cur.fetchone()
        except psycopg.Error as exc:
            raise QueryError(f"Query failed: {exc}") from exc
