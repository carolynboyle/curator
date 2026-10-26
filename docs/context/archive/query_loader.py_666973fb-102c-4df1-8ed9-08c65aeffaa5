"""
viewkit.query_loader - Runtime query lookup for repositories.

QueryLoader is the interface that repository classes use to retrieve
SQL at runtime. It takes the parsed QueryDef objects from QueryBuilder
and provides simple lookups by entity and query name.

QueryLoader does not touch the filesystem or parse YAML — that is
QueryBuilder's job. QueryLoader only works with already-parsed
QueryDef objects.

Usage:
    from pathlib import Path
    from viewkit.query_builder import QueryBuilder
    from viewkit.query_loader import QueryLoader

    builder = QueryBuilder(Path("/path/to/queries.yaml"))
    loader = QueryLoader(builder)

    qdef = loader.get("projects", "get_all")
    # qdef.sql        → "SELECT * FROM v_projects ORDER BY name"
    # qdef.query_type → "select_all"

    sql = loader.sql("projects", "get_all")
    # "SELECT * FROM v_projects ORDER BY name"
"""

from viewkit.query_builder import QueryBuilder
from viewkit.query_models import QueryDef


class QueryLoader:
    """
    Runtime query lookup for repository classes.

    Builds an internal cache of all QueryDef objects from a
    QueryBuilder at construction time. Repositories call get()
    for the full QueryDef or sql() for just the SQL string.

    Args:
        builder: A QueryBuilder instance loaded with a queries.yaml.
    """

    def __init__(self, builder: QueryBuilder):
        self._queries = builder.get_all_queries()

    def get(self, entity: str, name: str) -> QueryDef:
        """
        Return a QueryDef by entity and query name.

        Args:
            entity: Entity key (e.g. "projects", "tasks").
            name:   Query name within the entity (e.g. "get_all").

        Returns:
            The QueryDef for this entity and name.

        Raises:
            QueryNotFoundError: If entity or name is not present.
        """
        entity_queries = self._queries.get(entity)
        if entity_queries is None:
            available = ", ".join(self._queries.keys())
            raise KeyError(
                f"Entity '{entity}' not found in query loader. "
                f"Available entities: {available}"
            )

        query = entity_queries.get(name)
        if query is None:
            available = ", ".join(entity_queries.keys())
            raise KeyError(
                f"Query '{entity}.{name}' not found in query loader. "
                f"Available queries for '{entity}': {available}"
            )

        return query

    def sql(self, entity: str, name: str) -> str:
        """
        Return just the SQL string for an entity and query name.

        Convenience method for the common case where repositories
        only need the SQL string to pass to fetch_all / execute.

        Args:
            entity: Entity key (e.g. "projects", "tasks").
            name:   Query name within the entity (e.g. "get_all").

        Returns:
            The SQL string for this query.

        Raises:
            QueryNotFoundError: If entity or name is not present.
        """
        return self.get(entity, name).sql

    def list_entities(self) -> list[str]:
        """
        Return the names of all entities available in the loader.

        Returns:
            List of entity name strings.
        """
        return list(self._queries.keys())

    def list_query_names(self, entity: str) -> list[str]:
        """
        Return the names of all queries for an entity.

        Args:
            entity: Entity key.

        Returns:
            List of query name strings.

        Raises:
            KeyError: If entity is not present.
        """
        entity_queries = self._queries.get(entity)
        if entity_queries is None:
            raise KeyError(f"Entity '{entity}' not found in query loader.")
        return list(entity_queries.keys())
