"""
tests.unit.test_dashboard_popups_template - Rendering of the navbar popup
buttons (partials/_dashboard_popups.html).

  - one button per popup, carrying its definition as JSON in data-popup
  - nothing rendered for a role with no popups, or with no popups variable
  - the JSON round-trips and cannot break out of its attribute
"""

import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parents[2] / "src" / "curator" / "templates"
# Same environment shape as routes/crew.py: no autoescape.
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

RESOURCES = {
    "id": "resources",
    "label": "Resources",
    "type": "links",
    "shortcut": "alt+r",
    "project": "genealogy-resources",
}


def _render(**context):
    return env.get_template("partials/_dashboard_popups.html").render(**context)


def _definitions(html):
    """The data-popup JSON of every button, parsed."""
    return [json.loads(raw) for raw in re.findall(r"data-popup='([^']*)'", html)]


class TestPopupButtons:
    def test_one_button_per_popup(self):
        second = {"id": "settings", "label": "Settings", "type": "settings"}

        html = _render(popups=[RESOURCES, second])

        assert html.count('class="nav-popup-button"') == 2

    def test_button_carries_the_whole_definition(self):
        html = _render(popups=[RESOURCES])

        assert _definitions(html) == [RESOURCES]

    def test_label_is_the_button_text(self):
        html = _render(popups=[RESOURCES])

        assert "↗ Resources" in html

    def test_shortcut_shows_in_the_tooltip(self):
        html = _render(popups=[RESOURCES])

        assert 'title="Resources (alt+r)"' in html

    def test_no_tooltip_without_a_shortcut(self):
        popup = {"id": "r", "label": "Resources", "type": "links"}

        assert "title=" not in _render(popups=[popup])

    def test_button_starts_collapsed(self):
        assert 'aria-expanded="false"' in _render(popups=[RESOURCES])

    def test_no_popups_renders_nothing(self):
        assert _render(popups=[]).strip() == ""

    def test_missing_popups_variable_renders_nothing(self):
        assert _render().strip() == ""


class TestAttributeSafety:
    def test_quote_in_a_value_cannot_end_the_attribute(self):
        popup = dict(RESOURCES, label="Bob's \"links\" <b>")

        html = _render(popups=[popup])

        assert _definitions(html) == [popup]

    def test_label_markup_is_escaped_in_the_visible_text(self):
        popup = dict(RESOURCES, label="<script>x</script>")

        html = _render(popups=[popup])

        assert "<script>" not in html
