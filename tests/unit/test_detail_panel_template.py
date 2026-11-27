"""
tests.unit.test_detail_panel_template - Rendering of the detail panel's tabs.

Covers partials/_detail_panel_content.html for fields that fieldkit moves
into their own tab (the "tab" layout hint), and for the list-and-edit tabs
(a record's Documents, a project's Links):
  - a tab button and a panel per FieldKit.tab_panes entry, after Details
  - tabbed controls sit outside <form id="detail-form"> and carry
    form="detail-form", so the browser still submits them with the form
  - the Details form no longer holds the tabbed fields
  - list-and-edit tabs exist only for a saved record
  - an entity with no tab hints keeps its old tab bar
  - field tabs hide the footer's New button; Documents leaves Save/New to
    the footer (no in-form add/save/cancel buttons)
"""

import json
import re
from pathlib import Path
from types import SimpleNamespace

import yaml
from jinja2 import Environment, FileSystemLoader

from curator.list_edit import list_edit_tabs_for

TEMPLATES_DIR = Path(__file__).parents[2] / "src" / "curator" / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

_CONFIG = yaml.safe_load(
    (Path(__file__).parents[2] / "src" / "curator" / "data" / "curator.yaml")
    .read_text(encoding="utf-8")
)


def _shipped_tabs(entity):
    """The list-and-edit tabs curator.yaml ships for an entity, resolved."""
    return list_edit_tabs_for(
        entity,
        _CONFIG["list_edit_tabs"],
        lambda dotted: _CONFIG[dotted.split(".", 1)[0]][dotted.split(".", 1)[1]],
    )


def _field(name, label, field_type="text", **extra):
    return SimpleNamespace(
        name=name, label=label, field_type=field_type, required=False,
        readonly=False, source=None, placeholder=None, help_text=None,
        **extra,
    )


YEAR = _field("year", "Year")
NOTES = _field("notes", "Notes", "textarea")
NOTES_PANE = {"label": "Notes", "slug": "notes", "fields": [NOTES]}


def _render(entity="records", record_id="7", tab_panes=None, **extra):
    template = env.get_template("partials/_detail_panel_content.html")
    extra.setdefault("list_edit_tabs", _shipped_tabs(entity))
    return template.render(
        entity=entity,
        record_id=record_id,
        record={"year": "ca.1820", "notes": "Long text"},
        fields=[YEAR, NOTES],
        field_rows=[[YEAR]],
        tab_panes=tab_panes if tab_panes is not None else [],
        layout={},
        actions=[],
        **extra,
    )


def _tab_buttons(html):
    return re.findall(r'<button class="detail-tab-button[^"]*" data-tab="([^"]+)"', html)


class TestFieldTabs:
    def test_tab_button_follows_details(self):
        html = _render(tab_panes=[NOTES_PANE])

        assert _tab_buttons(html)[:2] == ["details", "notes"]

    def test_tabbed_field_has_its_own_panel(self):
        html = _render(tab_panes=[NOTES_PANE])

        assert 'class="detail-tab-panel detail-tab-fill" data-tab="notes"' in html

    def test_tabbed_control_is_outside_the_form_but_tied_to_it(self):
        html = _render(tab_panes=[NOTES_PANE])

        form_end = html.index("</form>")
        notes_at = html.index('id="detail-notes"')
        assert notes_at > form_end
        tag_start = html.rindex("<textarea", 0, notes_at)
        tag_end = html.index(">", notes_at)
        assert 'form="detail-form"' in html[tag_start:tag_end]

    def test_details_form_does_not_hold_the_tabbed_field(self):
        html = _render(tab_panes=[NOTES_PANE])

        form = html[html.index('<form id="detail-form"'):html.index("</form>")]
        assert 'name="year"' in form
        assert 'name="notes"' not in form

    def test_form_controls_carry_no_form_attribute(self):
        html = _render(tab_panes=[NOTES_PANE])

        form = html[html.index('<form id="detail-form"'):html.index("</form>")]
        assert 'form="detail-form"' not in form

    def test_entity_without_tab_hints_keeps_its_tab_bar(self):
        html = _render(entity="contacts", tab_panes=[])

        assert _tab_buttons(html) == ["details", "emails", "phones", "urls", "organizations"]
        assert "detail-tab-fill" not in html


class TestSearchesNotesTab:
    def test_search_panel_gets_a_notes_tab_and_no_documents_tab(self):
        html = _render(entity="searches", tab_panes=[NOTES_PANE])

        assert _tab_buttons(html) == ["details", "notes"]
        assert 'data-tab="documents"' not in html

    def test_search_notes_panel_fills_the_pane(self):
        html = _render(entity="searches", tab_panes=[NOTES_PANE])

        assert 'class="detail-tab-panel detail-tab-fill" data-tab="notes"' in html


SUMMARY_CONFIG = {
    "separator": " · ",
    "parts": [
        {"field": "source"},
        {"field": "county_scope", "last_segment": "→"},
    ],
}


class TestSearchSummary:
    def test_search_panel_has_a_summary_line_before_the_form(self):
        html = _render(entity="searches", search_summary=SUMMARY_CONFIG)

        assert 'class="search-summary"' in html
        assert html.index('class="search-summary"') < html.index('<form id="detail-form"')

    def test_summary_sits_inside_the_details_tab(self):
        html = _render(entity="searches", search_summary=SUMMARY_CONFIG)

        details_at = html.index('data-tab="details">')
        assert details_at < html.index('class="search-summary"')

    def test_definition_travels_as_json_in_data_summary(self):
        html = _render(entity="searches", search_summary=SUMMARY_CONFIG)

        raw = re.search(r"data-summary='([^']*)'", html).group(1)
        assert json.loads(raw) == SUMMARY_CONFIG

    def test_summary_box_is_read_only_and_open_button_starts_disabled(self):
        html = _render(entity="searches", search_summary=SUMMARY_CONFIG)

        assert re.search(r'class="search-summary-box"\s+readonly', html)
        assert re.search(r'class="search-summary-open"[^>]*\sdisabled', html)

    def test_script_starts_the_summary(self):
        html = _render(entity="searches", search_summary=SUMMARY_CONFIG)

        assert "window.initSearchSummary" in html

    def test_other_entities_get_no_summary_line(self):
        for entity in ("records", "projects"):
            html = _render(entity=entity, search_summary=SUMMARY_CONFIG)
            assert "search-summary" not in html

    def test_no_summary_without_config(self):
        assert "search-summary" not in _render(entity="searches")
        assert "search-summary" not in _render(entity="searches", search_summary={})

    def test_quote_in_config_cannot_end_the_attribute(self):
        config = {"separator": " ' \" ", "parts": [{"field": "source"}]}

        html = _render(entity="searches", search_summary=config)

        raw = re.search(r"data-summary='([^']*)'", html).group(1)
        assert json.loads(raw) == config


class TestDocumentsTab:
    def test_saved_record_gets_a_documents_tab_after_notes(self):
        html = _render(tab_panes=[NOTES_PANE])

        assert _tab_buttons(html) == ["details", "notes", "documents"]

    def test_widget_lives_in_the_documents_panel_not_in_details(self):
        html = _render(tab_panes=[NOTES_PANE])

        details_start = html.index('class="detail-tab-panel active" data-tab="details"')
        docs_panel = html.index('class="detail-tab-panel detail-tab-fill" data-tab="documents"')
        assert docs_panel > details_start
        assert 'le-widget' not in html[details_start:docs_panel]
        assert html.index('class="le-widget"') > docs_panel

    def test_widget_is_a_searchable_list_beside_a_greyed_out_form(self):
        html = _render(tab_panes=[NOTES_PANE])
        widget = html[html.index('class="le-widget"'):]

        # list column: search box, list; form column after it
        assert widget.index('class="le-search"') < widget.index('class="le-list"')
        assert widget.index('class="le-list"') < widget.index('<fieldset class="le-edit"')
        # the form starts disabled (greyed out) until an item is picked
        fieldset = widget[widget.index('<fieldset class="le-edit"'):]
        assert fieldset[:fieldset.index(">")].endswith("disabled")
        for name in ("label", "source_url", "md_path", "status"):
            assert f'data-field="{name}"' in fieldset
        for name in ("source_url", "md_path"):
            assert f'data-open-for="{name}"' in fieldset
        assert "le-delete-btn" in fieldset

    def test_status_choices_come_from_the_config(self):
        html = _render(tab_panes=[NOTES_PANE])
        select = html[html.index('data-field="status"'):]
        select = select[:select.index("</select>")]

        for value in _CONFIG["seanchai"]["document_statuses"]:
            assert f'<option value="{value}">' in select

    def test_save_and_new_are_left_to_the_footer(self):
        html = _render(tab_panes=[NOTES_PANE])
        widget = html[html.index('class="le-widget"'):]
        widget = widget[:widget.index("</script>")]

        for gone in ("add-btn", "save-btn", "cancel-btn"):
            assert gone not in widget
        assert "le-delete-btn" in widget

    def test_field_tabs_hide_new_but_documents_does_not(self):
        html = _render(tab_panes=[NOTES_PANE])

        notes = html[html.index('data-tab="notes"\n'):]
        assert 'data-footer-hide="new"' in notes[:notes.index(">")]
        docs = html[html.index('data-tab="documents"'):]
        assert "data-footer-hide" not in docs[:docs.index(">")]

    def test_widget_says_document_not_part(self):
        html = _render(tab_panes=[NOTES_PANE])
        widget = html[html.index('class="le-widget"'):]
        widget = widget[:widget.index("</script>")]

        assert "Documents" in widget
        assert "part" not in widget.lower().replace("partial", "")

    def test_definition_travels_as_json_in_the_widget(self):
        html = _render(tab_panes=[NOTES_PANE])

        raw = re.search(r"data-definition='([^']*)'", html).group(1)
        definition = json.loads(raw)
        assert definition["id"] == "documents"
        assert definition["parent_key"] == "record_id"
        assert html.count("window.initListEditWidget") == 1

    def test_new_record_has_no_documents_tab_or_panel(self):
        html = _render(record_id="", tab_panes=[NOTES_PANE])

        assert _tab_buttons(html) == ["details", "notes"]
        assert 'data-tab="documents"' not in html
        assert "le-widget" not in html

    def test_documents_tab_is_for_records_only(self):
        html = _render(entity="searches", tab_panes=[])

        assert "documents" not in _tab_buttons(html)
        assert "le-widget" not in html


class TestLinksTab:
    def test_saved_project_gets_a_links_tab_after_its_child_tabs(self):
        html = _render(entity="projects")

        assert _tab_buttons(html) == ["details", "tasks", "contacts", "links"]

    def test_links_live_in_their_own_tab_not_in_details(self):
        html = _render(entity="projects")

        details_start = html.index('class="detail-tab-panel active" data-tab="details"')
        links_panel = html.index('class="detail-tab-panel detail-tab-fill" data-tab="links"')
        assert 'le-widget' not in html[details_start:links_panel]
        assert "links-widget" not in html

    def test_widget_has_label_and_url_fields_and_a_list(self):
        html = _render(entity="projects")
        widget = html[html.index('class="le-widget"'):]

        assert 'data-field="label"' in widget
        assert 'data-field="url"' in widget
        assert 'data-open-for="url"' in widget
        assert 'class="le-list"' in widget

    def test_definition_carries_the_duplicate_rule_and_urls(self):
        html = _render(entity="projects")

        definition = json.loads(re.search(r"data-definition='([^']*)'", html).group(1))
        assert definition["duplicate_of"] == ["label", "url"]
        assert definition["parent_key"] == "project_id"
        assert definition["save_new_url"] == "/crew/project_links/save"

    def test_new_project_has_no_links_tab(self):
        html = _render(entity="projects", record_id="")

        assert _tab_buttons(html) == ["details", "tasks", "contacts"]
        assert "le-widget" not in html

    def test_other_entities_keep_their_tab_bars(self):
        assert _tab_buttons(_render(entity="contacts")) == [
            "details", "emails", "phones", "urls", "organizations"]
        assert _tab_buttons(_render(entity="organizations")) == ["details", "contacts"]

    def test_definition_with_quote_cannot_end_the_attribute(self):
        tab = dict(_shipped_tabs("projects")[0], empty_text="It's \"empty\" <b>&")
        html = _render(entity="projects", list_edit_tabs=[tab])

        definition = json.loads(re.search(r"data-definition='([^']*)'", html).group(1))
        assert definition["empty_text"] == tab["empty_text"]
