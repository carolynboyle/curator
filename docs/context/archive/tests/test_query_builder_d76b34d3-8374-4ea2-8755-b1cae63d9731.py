"""
tests.test_query_builder - Unit tests for viewkit query layer.

Tests cover:
  - QueryBuilder loading a valid queries.yaml
  - get_query() returning correct QueryDef objects
  - get_queries() and get_all_queries()
  - list_entities() and list_query_names()
  - QueryNotFoundError on missing entity or query name
  - QueryConfigError on missing file, bad YAML, missing required keys,
    invalid query type
  - QueryLoader runtime lookup via get() and sql()
  - QueryDef validation
"""

import textwrap
from pathlib import Path

import pytest

from viewkit import (
    QueryBuilder,
    QueryLoader,
    QueryDef,
    QueryNotFoundError,
    QueryConfigError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_YAML = Path(__file__).parent / "fixtures" / "queries.yaml"


@pytest.fixture()
def builder():
    """QueryBuilder loaded from the test fixture YAML."""
    return QueryBuilder(FIXTURE_YAML)


@pytest.fixture()
def loader(builder):
    """QueryLoader backed by the test fixture QueryBuilder."""
    return QueryLoader(builder)


@pytest.fixture()
def tmp_yaml(tmp_path):
    """Helper: write a YAML string to a temp file and return its Path."""
    def _write(content: str) -> Path:
        p = tmp_path / "queries.yaml"
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return p
    return _write


# ---------------------------------------------------------------------------
# QueryBuilder construction
# ---------------------------------------------------------------------------

class TestQueryBuilderInit:
    def test_loads_valid_file(self, builder):
        assert builder is not None

    def test_missing_file_raises(self):
        with pytest.raises(QueryConfigError, match="not found"):
            QueryBuilder(Path("/nonexistent/queries.yaml"))

    def test_invalid_yaml_raises(self, tmp_yaml):
        path = tmp_yaml(": bad: yaml: [unclosed")
        with pytest.raises(QueryConfigError, match="Could not read"):
            QueryBuilder(path)

    def test_empty_file_raises(self, tmp_yaml):
        path = tmp_yaml("")
        with pytest.raises(QueryConfigError, match="empty or not a valid mapping"):
            QueryBuilder(path)

    def test_non_mapping_raises(self, tmp_yaml):
        path = tmp_yaml("- just\n- a\n- list\n")
        with pytest.raises(QueryConfigError, match="empty or not a valid mapping"):
            QueryBuilder(path)


# ---------------------------------------------------------------------------
# list_entities
# ---------------------------------------------------------------------------

class TestListEntities:
    def test_returns_all_entities(self, builder):
        entities = builder.list_entities()
        assert "projects" in entities
        assert "tasks" in entities

    def test_order_matches_yaml(self, builder):
        entities = builder.list_entities()
        assert entities.index("projects") < entities.index("tasks")


# ---------------------------------------------------------------------------
# list_query_names
# ---------------------------------------------------------------------------

class TestListQueryNames:
    def test_returns_all_names_for_entity(self, builder):
        names = builder.list_query_names("projects")
        assert "get_all" in names
        assert "get_by_slug" in names
        assert "create" in names

    def test_missing_entity_raises(self, builder):
        with pytest.raises(QueryNotFoundError, match="not found"):
            builder.list_query_names("nonexistent")


# ---------------------------------------------------------------------------
# get_query — QueryDef
# ---------------------------------------------------------------------------

class TestGetQuery:
    def test_returns_query_def(self, builder):
        qdef = builder.get_query("projects", "get_all")
        assert isinstance(qdef, QueryDef)

    def test_query_name(self, builder):
        qdef = builder.get_query("projects", "get_all")
        assert qdef.name == "get_all"

    def test_query_entity(self, builder):
        qdef = builder.get_query("projects", "get_all")
        assert qdef.entity == "projects"

    def test_query_type(self, builder):
        qdef = builder.get_query("projects", "get_all")
        assert qdef.query_type == "select_all"

    def test_query_sql(self, builder):
        qdef = builder.get_query("projects", "get_all")
        assert "SELECT * FROM v_projects" in qdef.sql

    def test_select_one_type(self, builder):
        qdef = builder.get_query("projects", "get_by_slug")
        assert qdef.query_type == "select_one"

    def test_select_scalar_type(self, builder):
        qdef = builder.get_query("projects", "slug_exists")
        assert qdef.query_type == "select_scalar"

    def test_execute_type(self, builder):
        qdef = builder.get_query("projects", "create")
        assert qdef.query_type == "execute"

    def test_missing_entity_raises(self, builder):
        with pytest.raises(QueryNotFoundError, match="not found"):
            builder.get_query("nonexistent", "get_all")

    def test_missing_query_raises(self, builder):
        with pytest.raises(QueryNotFoundError, match="not found"):
            builder.get_query("projects", "nonexistent")

    def test_missing_type_raises(self, tmp_yaml):
        path = tmp_yaml("""
            things:
              bad_query:
                sql: "SELECT 1"
        """)
        with pytest.raises(QueryConfigError, match="missing required key 'type'"):
            QueryBuilder(path).get_query("things", "bad_query")

    def test_missing_sql_raises(self, tmp_yaml):
        path = tmp_yaml("""
            things:
              bad_query:
                type: select_all
        """)
        with pytest.raises(QueryConfigError, match="missing required key 'sql'"):
            QueryBuilder(path).get_query("things", "bad_query")

    def test_invalid_type_raises(self, tmp_yaml):
        path = tmp_yaml("""
            things:
              bad_query:
                type: rainbow
                sql: "SELECT 1"
        """)
        with pytest.raises(QueryConfigError, match="invalid type"):
            QueryBuilder(path).get_query("things", "bad_query")

    def test_non_mapping_entity_raises(self, tmp_yaml):
        path = tmp_yaml("""
            things: "not a mapping"
        """)
        with pytest.raises(QueryConfigError, match="must be a mapping"):
            QueryBuilder(path).get_query("things", "get_all")

    def test_non_mapping_query_raises(self, tmp_yaml):
        path = tmp_yaml("""
            things:
              bad_query: "not a mapping"
        """)
        with pytest.raises(QueryConfigError, match="must be a mapping"):
            QueryBuilder(path).get_query("things", "bad_query")

    def test_non_string_sql_raises(self, tmp_yaml):
        path = tmp_yaml("""
            things:
              bad_query:
                type: select_all
                sql:
                  - not
                  - a
                  - string
        """)
        with pytest.raises(QueryConfigError, match="must be a string"):
            QueryBuilder(path).get_query("things", "bad_query")


# ---------------------------------------------------------------------------
# get_queries (all queries for one entity)
# ---------------------------------------------------------------------------

class TestGetQueries:
    def test_returns_dict_of_query_defs(self, builder):
        queries = builder.get_queries("projects")
        assert isinstance(queries, dict)
        assert all(isinstance(q, QueryDef) for q in queries.values())

    def test_contains_expected_keys(self, builder):
        queries = builder.get_queries("projects")
        assert "get_all" in queries
        assert "get_by_slug" in queries
        assert "create" in queries

    def test_missing_entity_raises(self, builder):
        with pytest.raises(QueryNotFoundError, match="not found"):
            builder.get_queries("nonexistent")


# ---------------------------------------------------------------------------
# get_all_queries
# ---------------------------------------------------------------------------

class TestGetAllQueries:
    def test_returns_nested_dict(self, builder):
        all_q = builder.get_all_queries()
        assert isinstance(all_q, dict)
        assert "projects" in all_q
        assert "tasks" in all_q
        assert all(isinstance(q, QueryDef) for q in all_q["projects"].values())

    def test_query_count(self, builder):
        all_q = builder.get_all_queries()
        assert len(all_q["projects"]) == 6
        assert len(all_q["tasks"]) == 3


# ---------------------------------------------------------------------------
# QueryDef validation
# ---------------------------------------------------------------------------

class TestQueryDef:
    def test_valid_types(self):
        for qt in ("select_all", "select_one", "select_scalar", "execute"):
            qdef = QueryDef(name="test", entity="test", query_type=qt, sql="SELECT 1")
            assert qdef.query_type == qt

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="invalid query_type"):
            QueryDef(name="test", entity="test", query_type="rainbow", sql="SELECT 1")


# ---------------------------------------------------------------------------
# QueryLoader
# ---------------------------------------------------------------------------

class TestQueryLoader:
    def test_get_returns_query_def(self, loader):
        qdef = loader.get("projects", "get_all")
        assert isinstance(qdef, QueryDef)
        assert qdef.name == "get_all"

    def test_sql_returns_string(self, loader):
        sql = loader.sql("projects", "get_all")
        assert isinstance(sql, str)
        assert "SELECT * FROM v_projects" in sql

    def test_sql_matches_get(self, loader):
        qdef = loader.get("projects", "get_by_slug")
        assert loader.sql("projects", "get_by_slug") == qdef.sql

    def test_missing_entity_raises(self, loader):
        with pytest.raises(KeyError, match="not found"):
            loader.get("nonexistent", "get_all")

    def test_missing_query_raises(self, loader):
        with pytest.raises(KeyError, match="not found"):
            loader.get("projects", "nonexistent")

    def test_sql_missing_entity_raises(self, loader):
        with pytest.raises(KeyError, match="not found"):
            loader.sql("nonexistent", "get_all")

    def test_list_entities(self, loader):
        entities = loader.list_entities()
        assert "projects" in entities
        assert "tasks" in entities

    def test_list_query_names(self, loader):
        names = loader.list_query_names("projects")
        assert "get_all" in names
        assert "create" in names

    def test_list_query_names_missing_entity_raises(self, loader):
        with pytest.raises(KeyError, match="not found"):
            loader.list_query_names("nonexistent")

    def test_cross_entity_isolation(self, loader):
        """Queries from one entity don't leak into another."""
        proj_names = loader.list_query_names("projects")
        task_names = loader.list_query_names("tasks")
        assert "get_by_slug" in proj_names
        assert "get_by_slug" not in task_names
        assert "get_child_count" in task_names
        assert "get_child_count" not in proj_names
