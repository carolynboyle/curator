"""
tests.unit.test_detail_panel_template - Rendering of the detail panel's tabs.

Covers partials/_detail_panel_content.html for fields that fieldkit moves
into their own tab (the "tab" layout hint), and for the records Documents
tab:
  - a tab button and a panel per FieldKit.tab_panes entry, after Details
  - tabbed controls sit outside <form id="detail-form"> and carry
    form="detail-form", so the browser still submits them with the form
  - the Details form no longer holds the tabbed fields
  - the Documents tab exists only for a saved record
  - an entity with no tab hints keeps its old tab bar
"""

import re
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parents[2] / "src" / "curator" / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


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
        html = _render(entity="projects", tab_panes=[])

        assert _tab_buttons(html) == ["details", "tasks", "contacts"]
        assert "detail-tab-fill" not in html


class TestDocumentsTab:
    def test_saved_record_gets_a_documents_tab_after_notes(self):
        html = _render(tab_panes=[NOTES_PANE])

        assert _tab_buttons(html) == ["details", "notes", "documents"]

    def test_widget_lives_in_the_documents_panel_not_in_details(self):
        html = _render(tab_panes=[NOTES_PANE])

        details_start = html.index('class="detail-tab-panel active" data-tab="details"')
        docs_panel = html.index('class="detail-tab-panel" data-tab="documents"')
        assert docs_panel > details_start
        assert 'docs-widget' not in html[details_start:docs_panel]
        assert html.index('class="docs-widget"') > docs_panel

    def test_new_record_has_no_documents_tab_or_panel(self):
        html = _render(record_id="", tab_panes=[NOTES_PANE])

        assert _tab_buttons(html) == ["details", "notes"]
        assert 'data-tab="documents"' not in html
        assert "docs-widget" not in html

    def test_documents_tab_is_for_records_only(self):
        html = _render(entity="searches", tab_panes=[])

        assert "documents" not in _tab_buttons(html)
