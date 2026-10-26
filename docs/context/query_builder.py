"""
viewkit.query_builder - YAML-driven query definition loader.

Loads a queries.yaml file and returns framework-agnostic QueryDef
objects describing the named SQL queries for each entity.

QueryBuilder knows nothing about what calls it, how the path was
found, or how the returned objects will be executed. That is the
caller's concern.

Usage:
    from pathlib import Path
    from viewkit.query_builder import QueryBuilder

    builder = QueryBuilder(Path("/path/to/queries.yaml"))

    queries = builder.get_queries("projects")
    # {"get_all": QueryDef(...), "get_by_slug": QueryDef(...), ...}

    query = builder.get_query("projects", "get_all")
    # QueryDef(name="get_all", entity="projects", ...)

    all_queries = builder.get_all_queries()
    # {"projects": {"get_all": QueryDef(...), ...}, "tasks": {...}, ...}
"""

from pathlib import Path

import yaml

from viewkit.exceptions import QueryConfigError, QueryNotFoundError
from viewkit.query_models import QueryDef, VALID_QUERY_TYPES


class QueryBuilder:
    """
    Loads queries.yaml and builds QueryDef objects on request.

    The YAML file is loaded once at construction time. Call get_query()
    to retrieve a single parsed QueryDef by entity and name, or
    get_queries() to retrieve all queries for an entity.

    Args:
        queries_path: Path to the queries.yaml file to load.

    Raises:
        QueryConfigError: If the file is missing, unreadable, or malformed.
    """

    def __init__(self, queries_path: Path):
        self._path = queries_path
        self._raw = self._load(queries_path)

    # -- Public interface -----------------------------------------------------

    def get_query(self, entity: str, name: str) -> QueryDef:
        """
        Return a single parsed QueryDef by entity and query name.

        Args:
            entity: Top-level key in queries.yaml (e.g. "projects").
            name:   Query name within the entity (e.g. "get_all").

        Returns:
            QueryDef with entity, name, query_type, and sql populated.

        Raises:
            QueryNotFoundError: If entity or name is not present.
            QueryConfigError:   If the query definition is malformed.
        """
        queries = self._get_entity_raw(entity)

        if name not in queries:
            raise QueryNotFoundError(
                f"Query '{entity}.{name}' not found in {self._path}. "
                f"Available queries for '{entity}': "
                f"{', '.join(queries.keys())}"
            )

        return self._parse_query(entity, name, queries[name])

    def get_queries(self, entity: str) -> dict[str, QueryDef]:
        """
        Return all parsed QueryDefs for an entity as a dict keyed by name.

        Args:
            entity: Top-level key in queries.yaml (e.g. "projects").

        Returns:
            Dict mapping query name → QueryDef.

        Raises:
            QueryNotFoundError: If entity is not present in queries.yaml.
            QueryConfigError:   If any query definition is malformed.
        """
        queries = self._get_entity_raw(entity)
        return {
            name: self._parse_query(entity, name, data)
            for name, data in queries.items()
        }

    def get_all_queries(self) -> dict[str, dict[str, QueryDef]]:
        """
        Return all queries from queries.yaml, nested by entity then name.

        Returns:
            Dict mapping entity → {query name → QueryDef}.

        Raises:
            QueryConfigError: If any query definition is malformed.
        """
        return {
            entity: {
                name: self._parse_query(entity, name, data)
                for name, data in queries.items()
            }
            for entity, queries in self._raw.items()
        }

    def list_entities(self) -> list[str]:
        """
        Return the names of all entities defined in queries.yaml.

        Returns:
            List of entity name strings in definition order.
        """
        return list(self._raw.keys())

    def list_query_names(self, entity: str) -> list[str]:
        """
        Return the names of all queries for an entity.

        Args:
            entity: Top-level key in queries.yaml.

        Returns:
            List of query name strings in definition order.

        Raises:
            QueryNotFoundError: If entity is not present.
        """
        queries = self._get_entity_raw(entity)
        return list(queries.keys())

    # -- Parsing --------------------------------------------------------------

    def _get_entity_raw(self, entity: str) -> dict:
        """
        Return the raw dict for an entity, raising if not found.

        Args:
            entity: Top-level key in queries.yaml.

        Returns:
            Raw dict of query definitions for this entity.

        Raises:
            QueryNotFoundError: If entity is not present.
        """
        if entity not in self._raw:
            raise QueryNotFoundError(
                f"Entity '{entity}' not found in {self._path}. "
                f"Available entities: {', '.join(self._raw.keys())}"
            )

        data = self._raw[entity]
        if not isinstance(data, dict):
            raise QueryConfigError(
                f"Entity '{entity}' in {self._path} must be a mapping, "
                f"got {type(data).__name__}."
            )

        return data

    def _parse_query(self, entity: str, name: str, data: dict) -> QueryDef:
        """
        Parse a single query definition dict into a QueryDef.

        Args:
            entity: Parent entity name.
            name:   Query name within the entity.
            data:   Raw query dict from YAML.

        Returns:
            Populated QueryDef.

        Raises:
            QueryConfigError: If required keys are missing or values invalid.
        """
        if not isinstance(data, dict):
            raise QueryConfigError(
                f"Query '{entity}.{name}' in {self._path} must be a "
                f"mapping, got {type(data).__name__}."
            )

        query_type = data.get("type")
        if not query_type:
            raise QueryConfigError(
                f"Query '{entity}.{name}' in {self._path} is missing "
                f"required key 'type'."
            )

        if query_type not in VALID_QUERY_TYPES:
            raise QueryConfigError(
                f"Query '{entity}.{name}' in {self._path}: invalid type "
                f"'{query_type}'. Must be one of: "
                f"{', '.join(sorted(VALID_QUERY_TYPES))}"
            )

        sql = data.get("sql")
        if not sql:
            raise QueryConfigError(
                f"Query '{entity}.{name}' in {self._path} is missing "
                f"required key 'sql'."
            )

        if not isinstance(sql, str):
            raise QueryConfigError(
                f"Query '{entity}.{name}' in {self._path}: 'sql' must "
                f"be a string, got {type(sql).__name__}."
            )

        try:
            return QueryDef(
                name=name,
                entity=entity,
                query_type=query_type,
                sql=sql,
            )
        except ValueError as exc:
            raise QueryConfigError(
                f"Query '{entity}.{name}': {exc}"
            ) from exc

    # -- File loading ---------------------------------------------------------

    @staticmethod
    def _load(path: Path) -> dict:
        """
        Load and parse a queries.yaml file.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed dict of entity → query definitions.

        Raises:
            QueryConfigError: If the file is missing, unreadable,
                              or invalid YAML.
        """
        if not path.exists():
            raise QueryConfigError(f"queries.yaml not found: {path}")

        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise QueryConfigError(
                f"Could not read queries.yaml at {path}: {exc}"
            ) from exc

        if not data or not isinstance(data, dict):
            raise QueryConfigError(
                f"queries.yaml at {path} is empty or not a valid mapping."
            )

        return data
