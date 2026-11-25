"""
tests.unit.test_search_summary_config - The search summary line and the
search field layout shipped in curator.yaml / fieldkit_overrides.yaml.
"""

from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parents[2] / "src" / "curator" / "data"

# The columns of seanchai.v_search_detail after steward 10m, in form order.
VIEW_COLUMNS = [
    "source", "search_url", "search_id", "search_terms", "county_scope",
    "year_filter", "result_count", "status", "notes", "searched_at",
]


def _load(name):
    return yaml.safe_load((DATA_DIR / name).read_text(encoding="utf-8"))


class TestSearchSummaryConfig:
    def _summary(self):
        return _load("curator.yaml")["seanchai"]["search_summary"]

    def test_parts_name_columns_of_the_search_view(self):
        for part in self._summary()["parts"]:
            assert part["field"] in VIEW_COLUMNS

    def test_summary_names_what_was_searched(self):
        fields = [part["field"] for part in self._summary()["parts"]]

        assert fields == ["source", "search_terms", "county_scope", "year_filter"]

    def test_county_scope_shows_only_the_last_segment(self):
        parts = {p["field"]: p for p in self._summary()["parts"]}

        assert parts["county_scope"]["last_segment"] == "→"

    def test_separator_is_set(self):
        assert self._summary()["separator"].strip() != ""


class TestSearchFieldLayout:
    def _overrides(self):
        return _load("fieldkit_overrides.yaml")["seanchai.v_search_detail"]

    def test_every_override_is_a_column_of_the_view(self):
        assert set(self._overrides()) <= set(VIEW_COLUMNS)

    def test_new_fields_are_plain_text_controls(self):
        overrides = self._overrides()

        assert overrides["source"]["control"] == "text"
        assert overrides["search_url"]["control"] == "text"

    def test_source_and_url_share_the_first_line(self):
        overrides = self._overrides()

        assert overrides["source"]["row"] == overrides["search_url"]["row"]
        assert VIEW_COLUMNS[:2] == ["source", "search_url"]

    def test_notes_still_has_its_own_tab(self):
        assert self._overrides()["notes"]["tab"] == "Notes"

    def test_integer_and_id_columns_have_explicit_controls(self):
        # fieldkit refuses to start without one for any *_id or integer column
        overrides = self._overrides()

        assert "control" in overrides["search_id"]
        assert "control" in overrides["result_count"]
