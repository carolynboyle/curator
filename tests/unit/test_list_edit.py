"""
tests.unit.test_list_edit - curator.list_edit and the shipped list_edit_tabs.

The loader checks each tab definition and resolves its dotted references, so
one bad entry in curator.yaml skips that tab with a warning instead of
breaking a panel.
"""

import copy
import logging
from pathlib import Path

import yaml

from curator.list_edit import list_edit_tabs_for

CONFIG = yaml.safe_load(
    (Path(__file__).parents[2] / "src" / "curator" / "data" / "curator.yaml")
    .read_text(encoding="utf-8")
)


def _lookup(dotted):
    section, key = dotted.split(".", 1)
    return CONFIG[section][key]


def _tab(**overrides):
    tab = {
        "id": "things", "label": "Things", "noun": "thing", "parent_key": "owner_id",
        "list_url": "/t/{parent_id}", "save_new_url": "/t/save",
        "save_url": "/t/{id}/save", "delete_url": "/t/{id}", "title_field": "name",
        "search_fields": ["name"],
        "fields": [{"name": "name", "label": "Name", "control": "text"}],
    }
    tab.update(overrides)
    return tab


def _load(*tabs, lookup=_lookup):
    return list_edit_tabs_for("owners", {"owners": list(tabs)}, lookup)


class TestShippedDefinitions:
    def test_records_ship_documents(self):
        tabs = list_edit_tabs_for("records", CONFIG["list_edit_tabs"], _lookup)

        assert [t["id"] for t in tabs] == ["documents"]

    def test_projects_ship_links(self):
        tabs = list_edit_tabs_for("projects", CONFIG["list_edit_tabs"], _lookup)

        assert [t["id"] for t in tabs] == ["links"]

    def test_entities_without_tabs_get_none(self):
        assert list_edit_tabs_for("searches", CONFIG["list_edit_tabs"], _lookup) == []

    def test_documents_status_choices_come_from_seanchai_config(self):
        tab = list_edit_tabs_for("records", CONFIG["list_edit_tabs"], _lookup)[0]
        status = next(f for f in tab["fields"] if f["name"] == "status")

        assert [o["value"] for o in status["options"]] == CONFIG["seanchai"]["document_statuses"]
        assert {"value": "not_transcribed", "label": "not transcribed"} in status["options"]

    def test_documents_repo_base_comes_from_seanchai_config(self):
        tab = list_edit_tabs_for("records", CONFIG["list_edit_tabs"], _lookup)[0]

        assert tab["repo_base"] == CONFIG["seanchai"]["repo_blob_base"]

    def test_links_have_no_repo_base(self):
        tab = list_edit_tabs_for("projects", CONFIG["list_edit_tabs"], _lookup)[0]

        assert tab["repo_base"] == ""

    def test_urls_have_their_placeholders(self):
        for entity in ("records", "projects"):
            tab = list_edit_tabs_for(entity, CONFIG["list_edit_tabs"], _lookup)[0]
            assert "{parent_id}" in tab["list_url"]
            assert "{id}" in tab["save_url"]
            assert "{id}" in tab["delete_url"]
            assert "{" not in tab["save_new_url"]

    def test_title_and_search_fields_are_fields_of_the_tab(self):
        for entity in ("records", "projects"):
            tab = list_edit_tabs_for(entity, CONFIG["list_edit_tabs"], _lookup)[0]
            names = {f["name"] for f in tab["fields"]}
            assert tab["title_field"] in names
            assert set(tab["search_fields"]) <= names

    def test_links_require_a_label_and_warn_on_duplicates(self):
        tab = list_edit_tabs_for("projects", CONFIG["list_edit_tabs"], _lookup)[0]
        label = next(f for f in tab["fields"] if f["name"] == "label")

        assert label["required"] is True
        assert tab["duplicate_of"] == ["label", "url"]

    def test_documents_need_a_url_or_a_path(self):
        tab = list_edit_tabs_for("records", CONFIG["list_edit_tabs"], _lookup)[0]

        assert tab["require_one_of"]["fields"] == ["source_url", "md_path"]

    def test_shipped_tabs_do_not_mutate_the_config(self):
        before = copy.deepcopy(CONFIG["list_edit_tabs"])
        list_edit_tabs_for("records", CONFIG["list_edit_tabs"], _lookup)

        assert CONFIG["list_edit_tabs"] == before


class TestValidation:
    def test_a_valid_tab_passes_through(self):
        tabs = _load(_tab())

        assert [t["id"] for t in tabs] == ["things"]

    def test_missing_required_key_skips_the_tab(self, caplog):
        broken = _tab()
        del broken["delete_url"]

        with caplog.at_level(logging.WARNING):
            tabs = _load(broken, _tab(id="ok"))

        assert [t["id"] for t in tabs] == ["ok"]
        assert "delete_url" in caplog.text

    def test_duplicate_id_keeps_the_first(self):
        tabs = _load(_tab(label="First"), _tab(label="Second"))

        assert [t["label"] for t in tabs] == ["First"]

    def test_non_mapping_entry_is_skipped(self):
        assert _load("nonsense", _tab()) != []
        assert [t["id"] for t in _load("nonsense", _tab())] == ["things"]

    def test_unknown_control_skips_the_tab(self):
        bad = _tab(fields=[{"name": "name", "label": "Name", "control": "wizard"}])

        assert _load(bad) == []

    def test_field_missing_a_label_skips_the_tab(self):
        bad = _tab(fields=[{"name": "name", "control": "text"}])

        assert _load(bad) == []

    def test_duplicate_field_names_skip_the_tab(self):
        field = {"name": "name", "label": "Name", "control": "text"}

        assert _load(_tab(fields=[field, dict(field)])) == []

    def test_unknown_open_kind_skips_the_tab(self):
        bad = _tab(fields=[{"name": "name", "label": "Name", "control": "text", "open": "teleport"}])

        assert _load(bad) == []

    def test_select_without_choices_skips_the_tab(self):
        bad = _tab(fields=[{"name": "name", "label": "Name", "control": "select"}])

        assert _load(bad) == []

    def test_select_with_unresolvable_options_from_skips_the_tab(self):
        bad = _tab(fields=[{
            "name": "name", "label": "Name", "control": "select", "options_from": "nowhere.nothing"}])

        assert _load(bad, lookup=lambda dotted: None) == []

    def test_inline_select_options_are_resolved(self):
        tab = _tab(fields=[{
            "name": "name", "label": "Name", "control": "select", "options": ["a_b", "c"]}])

        options = _load(tab)[0]["fields"][0]["options"]

        assert options == [{"value": "a_b", "label": "a b"}, {"value": "c", "label": "c"}]

    def test_search_field_naming_an_unknown_field_skips_the_tab(self):
        assert _load(_tab(search_fields=["nope"])) == []

    def test_duplicate_rule_naming_an_unknown_field_skips_the_tab(self):
        assert _load(_tab(duplicate_of=["name", "nope"])) == []

    def test_require_one_of_naming_an_unknown_field_skips_the_tab(self):
        assert _load(_tab(require_one_of={"fields": ["nope"], "message": "x"})) == []

    def test_no_config_section_gives_no_tabs(self):
        assert list_edit_tabs_for("records", None, _lookup) == []
        assert list_edit_tabs_for("records", {}, _lookup) == []
