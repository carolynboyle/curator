"""
tests.test_view_builder - Unit tests for viewkit.

Tests cover:
  - ViewBuilder loading a valid views.yaml
  - get_view() returning correct ViewDef, ColumnDef, FieldDef objects
  - get_all_views() and list_view_names()
  - ViewNotFoundError on missing view name
  - ViewConfigError on missing file, bad YAML, missing required keys,
    invalid field_type, select without source
"""

import textwrap
from pathlib import Path

import pytest
import yaml

from viewkit import (
    ViewBuilder,
    ColumnDef,
    FieldDef,
    ViewDef,
    ViewNotFoundError,
    ViewConfigError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_YAML = Path(__file__).parent / "fixtures" / "views.yaml"


@pytest.fixture()
def builder():
    """ViewBuilder loaded from the test fixture YAML."""
    return ViewBuilder(FIXTURE_YAML)


@pytest.fixture()
def tmp_yaml(tmp_path):
    """Helper: write a YAML string to a temp file and return its Path."""
    def _write(content: str) -> Path:
        p = tmp_path / "views.yaml"
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return p
    return _write


# ---------------------------------------------------------------------------
# ViewBuilder construction
# ---------------------------------------------------------------------------

class TestViewBuilderInit:
    def test_loads_valid_file(self, builder):
        assert builder is not None

    def test_missing_file_raises(self):
        with pytest.raises(ViewConfigError, match="not found"):
            ViewBuilder(Path("/nonexistent/views.yaml"))

    def test_invalid_yaml_raises(self, tmp_yaml):
        path = tmp_yaml(": bad: yaml: [unclosed")
        with pytest.raises(ViewConfigError, match="Could not read"):
            ViewBuilder(path)

    def test_empty_file_raises(self, tmp_yaml):
        path = tmp_yaml("")
        with pytest.raises(ViewConfigError, match="empty or not a valid mapping"):
            ViewBuilder(path)

    def test_non_mapping_raises(self, tmp_yaml):
        path = tmp_yaml("- just\n- a\n- list\n")
        with pytest.raises(ViewConfigError, match="empty or not a valid mapping"):
            ViewBuilder(path)


# ---------------------------------------------------------------------------
# list_view_names
# ---------------------------------------------------------------------------

class TestListViewNames:
    def test_returns_all_names(self, builder):
        names = builder.list_view_names()
        assert "projects" in names
        assert "tasks" in names

    def test_order_matches_yaml(self, builder):
        names = builder.list_view_names()
        assert names.index("projects") < names.index("tasks")


# ---------------------------------------------------------------------------
# get_all_views
# ---------------------------------------------------------------------------

class TestGetAllViews:
    def test_returns_dict_of_view_defs(self, builder):
        views = builder.get_all_views()
        assert isinstance(views, dict)
        assert all(isinstance(v, ViewDef) for v in views.values())

    def test_contains_expected_keys(self, builder):
        views = builder.get_all_views()
        assert "projects" in views
        assert "tasks" in views


# ---------------------------------------------------------------------------
# get_view — ViewDef
# ---------------------------------------------------------------------------

class TestGetView:
    def test_returns_view_def(self, builder):
        view = builder.get_view("projects")
        assert isinstance(view, ViewDef)

    def test_view_name(self, builder):
        view = builder.get_view("projects")
        assert view.name == "projects"

    def test_view_title(self, builder):
        view = builder.get_view("projects")
        assert view.title == "Projects"

    def test_missing_view_raises(self, builder):
        with pytest.raises(ViewNotFoundError, match="not found"):
            builder.get_view("nonexistent")

    def test_missing_title_raises(self, tmp_yaml):
        path = tmp_yaml("""
            myview:
              columns: []
              fields: []
        """)
        with pytest.raises(ViewConfigError, match="missing required key 'title'"):
            ViewBuilder(path).get_view("myview")

    def test_view_with_no_columns(self, tmp_yaml):
        path = tmp_yaml("""
            myview:
              title: "Empty"
              fields: []
        """)
        view = ViewBuilder(path).get_view("myview")
        assert view.columns == []

    def test_view_with_no_fields(self, tmp_yaml):
        path = tmp_yaml("""
            myview:
              title: "Empty"
              columns: []
        """)
        view = ViewBuilder(path).get_view("myview")
        assert view.fields == []


# ---------------------------------------------------------------------------
# ColumnDef
# ---------------------------------------------------------------------------

class TestColumnDef:
    def test_columns_are_column_defs(self, builder):
        view = builder.get_view("projects")
        assert all(isinstance(c, ColumnDef) for c in view.columns)

    def test_column_count(self, builder):
        view = builder.get_view("projects")
        assert len(view.columns) == 4

    def test_first_column_name_and_label(self, builder):
        col = builder.get_view("projects").columns[0]
        assert col.name == "name"
        assert col.label == "Project"

    def test_link_flag(self, builder):
        col = builder.get_view("projects").columns[0]
        assert col.link is True

    def test_sortable_flag(self, builder):
        col = builder.get_view("projects").columns[0]
        assert col.sortable is True

    def test_truncate(self, builder):
        # open_tasks column has truncate: 6
        col = builder.get_view("projects").columns[3]
        assert col.truncate == 6

    def test_defaults_not_link_not_sortable(self, builder):
        col = builder.get_view("projects").columns[1]   # status
        assert col.link is False
        assert col.sortable is False

    def test_missing_name_raises(self, tmp_yaml):
        path = tmp_yaml("""
            myview:
              title: "Test"
              columns:
                - label: "No Name"
        """)
        with pytest.raises(ViewConfigError, match="missing required key 'name'"):
            ViewBuilder(path).get_view("myview")

    def test_missing_label_raises(self, tmp_yaml):
        path = tmp_yaml("""
            myview:
              title: "Test"
              columns:
                - name: thing
        """)
        with pytest.raises(ViewConfigError, match="missing required key 'label'"):
            ViewBuilder(path).get_view("myview")


# ---------------------------------------------------------------------------
# FieldDef
# ---------------------------------------------------------------------------

class TestFieldDef:
    def test_fields_are_field_defs(self, builder):
        view = builder.get_view("projects")
        assert all(isinstance(f, FieldDef) for f in view.fields)

    def test_field_count(self, builder):
        view = builder.get_view("projects")
        assert len(view.fields) == 7

    def test_text_field(self, builder):
        fld = builder.get_view("projects").fields[0]   # name
        assert fld.name == "name"
        assert fld.label == "Name"
        assert fld.field_type == "text"
        assert fld.required is True
        assert fld.placeholder == "My Project"

    def test_readonly_field(self, builder):
        fld = builder.get_view("projects").fields[1]   # slug
        assert fld.readonly is True
        assert fld.help_text is not None

    def test_textarea_field(self, builder):
        fld = builder.get_view("projects").fields[2]   # description
        assert fld.field_type == "textarea"
        assert fld.required is False

    def test_select_field_with_source(self, builder):
        fld = builder.get_view("projects").fields[3]   # status_id
        assert fld.field_type == "select"
        assert fld.source == "project_status"
        assert fld.required is True

    def test_date_field(self, builder):
        fld = builder.get_view("projects").fields[6]   # target_date
        assert fld.field_type == "date"

    def test_default_field_type_is_text(self, tmp_yaml):
        path = tmp_yaml("""
            myview:
              title: "Test"
              fields:
                - name: thing
                  label: "Thing"
        """)
        fld = ViewBuilder(path).get_view("myview").fields[0]
        assert fld.field_type == "text"

    def test_invalid_field_type_raises(self, tmp_yaml):
        path = tmp_yaml("""
            myview:
              title: "Test"
              fields:
                - name: thing
                  label: "Thing"
                  type: rainbow
        """)
        with pytest.raises(ViewConfigError, match="invalid field_type"):
            ViewBuilder(path).get_view("myview")

    def test_select_without_source_raises(self, tmp_yaml):
        path = tmp_yaml("""
            myview:
              title: "Test"
              fields:
                - name: thing
                  label: "Thing"
                  type: select
        """)
        with pytest.raises(ViewConfigError, match="requires a 'source'"):
            ViewBuilder(path).get_view("myview")

    def test_missing_field_name_raises(self, tmp_yaml):
        path = tmp_yaml("""
            myview:
              title: "Test"
              fields:
                - label: "No Name"
        """)
        with pytest.raises(ViewConfigError, match="missing required key 'name'"):
            ViewBuilder(path).get_view("myview")

    def test_missing_field_label_raises(self, tmp_yaml):
        path = tmp_yaml("""
            myview:
              title: "Test"
              fields:
                - name: thing
        """)
        with pytest.raises(ViewConfigError, match="missing required key 'label'"):
            ViewBuilder(path).get_view("myview")
