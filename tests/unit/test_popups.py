"""
tests.unit.test_popups - Popup definitions read from curator.yaml.

Covers curator.popups.popups_for_role (what a role's entry yields, and how
bad entries are skipped) and the popup shipped in curator.yaml.
"""

import logging
from pathlib import Path

import yaml

from curator.popups import popups_for_role

SHIPPED_CONFIG = (
    Path(__file__).parents[2] / "src" / "curator" / "data" / "curator.yaml"
)

RESOURCES = {
    "id": "resources",
    "label": "Resources",
    "type": "links",
    "shortcut": "alt+r",
    "project": "genealogy-resources",
}


class TestPopupsForRole:
    def test_valid_entry_is_returned_with_every_key(self):
        role = {"name": "seanchai", "popups": [RESOURCES]}

        assert popups_for_role(role) == [RESOURCES]

    def test_returns_copies_not_the_config_dicts(self):
        role = {"popups": [RESOURCES]}

        result = popups_for_role(role)
        result[0]["label"] = "changed"

        assert RESOURCES["label"] == "Resources"

    def test_role_without_popups_gets_none(self):
        assert popups_for_role({"name": "scribe"}) == []

    def test_unconfigured_role_gets_none(self):
        assert popups_for_role(None) == []

    def test_empty_or_null_popups_key_gets_none(self):
        assert popups_for_role({"popups": None}) == []
        assert popups_for_role({"popups": []}) == []

    def test_order_follows_the_config(self):
        second = {"id": "settings", "label": "Settings", "type": "settings"}

        result = popups_for_role({"popups": [RESOURCES, second]})

        assert [p["id"] for p in result] == ["resources", "settings"]

    def test_entry_missing_a_required_key_is_skipped_with_a_warning(self, caplog):
        broken = {"id": "x", "type": "links"}   # no label

        with caplog.at_level(logging.WARNING):
            result = popups_for_role({"popups": [broken, RESOURCES]})

        assert result == [RESOURCES]
        assert "label" in caplog.text

    def test_entry_that_is_not_a_mapping_is_skipped(self):
        assert popups_for_role({"popups": ["resources", RESOURCES]}) == [RESOURCES]

    def test_duplicate_id_keeps_the_first(self):
        twin = dict(RESOURCES, label="Twin")

        assert popups_for_role({"popups": [RESOURCES, twin]}) == [RESOURCES]

    def test_extra_keys_pass_through_for_the_provider(self):
        entry = dict(RESOURCES, future_option=True)

        assert popups_for_role({"popups": [entry]})[0]["future_option"] is True


class TestShippedConfig:
    def _roles(self):
        config = yaml.safe_load(SHIPPED_CONFIG.read_text(encoding="utf-8"))
        return {r["name"]: r for r in config["crew"]["roles"]}

    def test_seanchai_has_the_resources_links_popup(self):
        popups = popups_for_role(self._roles()["seanchai"])

        assert popups == [RESOURCES]

    def test_every_shipped_popup_passes_validation(self):
        for name, role in self._roles().items():
            declared = role.get("popups") or []
            assert len(popups_for_role(role)) == len(declared), name
