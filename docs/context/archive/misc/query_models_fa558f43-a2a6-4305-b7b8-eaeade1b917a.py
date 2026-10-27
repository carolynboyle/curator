"""
viewkit.query_models - Data structures for query definitions.

Framework-agnostic dataclasses representing parsed query configuration.
Callers receive these objects from QueryBuilder and use them however
their data layer requires — async repositories, sync DAOs, CLI tools,
or anything else.

QueryDef — a named SQL query with its type and SQL string.
"""

from dataclasses import dataclass


# Valid query types, mapping to BaseRepository method names:
#   select_all    → fetch_all()    → list[dict]
#   select_one    → fetch_one()    → dict | None
#   select_scalar → fetch_scalar() → single value
#   execute       → execute()      → None
VALID_QUERY_TYPES = {"select_all", "select_one", "select_scalar", "execute"}


@dataclass
class QueryDef:
    """
    Definition of a single named SQL query.

    Attributes:
        name:       Query name within its entity (e.g. "get_all", "create").
        entity:     Entity/section this query belongs to (e.g. "projects").
        query_type: One of: select_all, select_one, select_scalar, execute.
                    Indicates which repository method should run this query.
        sql:        The SQL string, ready to pass to a database driver.
                    May contain %s placeholders for parameterised queries.
    """

    name: str
    entity: str
    query_type: str
    sql: str

    def __post_init__(self):
        if self.query_type not in VALID_QUERY_TYPES:
            raise ValueError(
                f"QueryDef '{self.entity}.{self.name}': invalid query_type "
                f"'{self.query_type}'. Must be one of: "
                f"{', '.join(sorted(VALID_QUERY_TYPES))}"
            )
