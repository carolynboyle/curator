"""
formkit.py

Form utility module for Curator. Handles building reusable form action specifications
that can be rendered by Jinja2 templates.

Usage:
    from formkit import FormActions

    actions = FormActions.load_yaml('config/forms.yaml')
    detail_panel_actions = actions.get('detail_panel')

Or:
    from formkit import action_save, action_cancel

    actions = [
        action_save(form_id='detail-form'),
        action_cancel(),
    ]
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class FormAction:  # pylint: disable=too-few-public-methods
    # FormAction is a data holder — it stores button attributes and
    # exposes one conversion method (to_dict). Having only one public
    # method is correct by design, not a gap.
    """Represents a single form action button."""

    def __init__(self, attrs: Dict[str, Any]):
        """
        Initialize a form action from a dict of attributes.

        Args:
            attrs: Dict with the following keys, all optional except label:
                label       (str):  Button text (e.g., "Save", "Cancel")
                button_type (str):  HTML button type: "submit", "reset",
                                    "button" (default: "button")
                css_class   (str):  Additional CSS class for styling
                                    (e.g., "btn-primary")
                button_id   (str):  HTML id attribute
                title       (str):  Hover tooltip text
                form_id     (str):  Form ID for submit buttons (uses
                                    form= attribute)
                data_attrs  (dict): data-* attributes to add to the button
        """
        self.label = attrs.get("label", "")
        self.button_type = attrs.get("button_type", "button")
        self.css_class = attrs.get("css_class", "")
        self.button_id = attrs.get("button_id", "")
        self.title = attrs.get("title", "")
        self.form_id = attrs.get("form_id")
        self.data_attrs = attrs.get("data_attrs") or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Jinja2 template."""
        return {
            "label": self.label,
            "type": self.button_type,
            "class": self.css_class,
            "id": self.button_id,
            "title": self.title,
            "form_id": self.form_id,
            "data_attrs": self.data_attrs,
        }


class FormActions:  # pylint: disable=too-few-public-methods
    # Pylint miscounts public methods here — this class has eleven public
    # @staticmethods (save, new, discard, cancel, delete, custom,
    # detail_panel_actions, crud_create_actions, crud_edit_actions,
    # to_dicts, from_yaml). Disabled rather than restructured.
    """Builder for form action specifications."""

    @staticmethod
    def save(form_id: Optional[str] = None, label: str = "Save") -> FormAction:
        """Create a Save button."""
        return FormAction({
            "label": label,
            "button_type": "submit",
            "css_class": "btn-save",
            "form_id": form_id,
            "title": "Save (Alt+S)",
        })

    @staticmethod
    def new(label: str = "New") -> FormAction:
        """Create a New button."""
        return FormAction({
            "label": label,
            "button_type": "button",
            "css_class": "btn-new",
            "title": "New (Alt+N)",
            "data_attrs": {"action": "new"},
        })

    @staticmethod
    def discard(label: str = "Discard") -> FormAction:
        """Create a Discard button."""
        return FormAction({
            "label": label,
            "button_type": "button",
            "css_class": "btn-discard",
            "title": "Discard (Alt+X)",
            "data_attrs": {"action": "discard"},
        })

    @staticmethod
    def cancel(label: str = "Cancel") -> FormAction:
        """Create a Cancel button (alias for Discard)."""
        return FormAction({
            "label": label,
            "button_type": "button",
            "css_class": "btn-cancel",
            "title": "Cancel (Escape)",
            "data_attrs": {"action": "cancel"},
        })

    @staticmethod
    def delete(label: str = "Delete", confirm: bool = True) -> FormAction:
        """Create a Delete button."""
        data_attrs = {"action": "delete"}
        if confirm:
            data_attrs["confirm"] = "true"

        return FormAction({
            "label": label,
            "button_type": "button",
            "css_class": "btn-delete",
            "title": "Delete (permanent)",
            "data_attrs": data_attrs,
        })

    @staticmethod
    def custom(
        label: str,
        button_type: str = "button",
        css_class: str = "",
        **kwargs
    ) -> FormAction:
        """Create a custom button with arbitrary parameters."""
        attrs = {
            "label": label,
            "button_type": button_type,
            "css_class": css_class,
        }
        attrs.update(kwargs)
        return FormAction(attrs)

    @staticmethod
    def detail_panel_actions(form_id: str = "detail-form") -> List[FormAction]:
        """
        Preset: Detail panel action buttons (Save, New, Discard).
        Used in _detail_panel.html.
        """
        return [
            FormActions.save(form_id=form_id),
            FormActions.new(),
            FormActions.discard(),
        ]

    @staticmethod
    def crud_create_actions(form_id: str = "form") -> List[FormAction]:
        """Preset: Create form actions (Save, Cancel)."""
        return [
            FormActions.save(form_id=form_id),
            FormActions.cancel(),
        ]

    @staticmethod
    def crud_edit_actions(form_id: str = "form") -> List[FormAction]:
        """Preset: Edit form actions (Save, Delete, Cancel)."""
        return [
            FormActions.save(form_id=form_id),
            FormActions.delete(),
            FormActions.cancel(),
        ]

    @staticmethod
    def to_dicts(actions: List[FormAction]) -> List[Dict[str, Any]]:
        """Convert list of FormAction objects to list of dicts for Jinja2."""
        return [action.to_dict() for action in actions]

    @staticmethod
    def from_yaml(forms_path: Path, preset: str) -> Dict[str, Any]:
        """Load a button preset from forms.yaml.

        Looks up each action's button definition from the buttons: section,
        then merges any preset-level overrides (e.g. form_id).

        Returns dict with keys:
            container_class (str):  CSS class for the button container div
            actions         (list): Action dicts ready for _form_actions.html

        Each action dict has keys:
            label, type, class, id, title, form_id, data_attrs

        Args:
            forms_path: Path to forms.yaml
            preset:     Name of the preset to load (e.g. 'detail_panel')

        Raises:
            KeyError:          If preset or a referenced button is not found
            FileNotFoundError: If forms.yaml does not exist
        """
        with open(forms_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        button_defs = config.get("buttons", {})
        preset_cfg  = config.get("presets", {}).get(preset)

        if preset_cfg is None:
            raise KeyError(f"Preset '{preset}' not found in {forms_path}")

        container_class = preset_cfg.get("container_class", "form-actions")

        actions = []
        for action_cfg in preset_cfg.get("actions", []):
            btn_name = action_cfg.get("button")
            if btn_name not in button_defs:
                raise KeyError(
                    f"Button '{btn_name}' referenced in preset '{preset}' "
                    f"is not defined in buttons: section of {forms_path}"
                )

            # Start from the button definition, then apply preset overrides
            btn = dict(button_defs[btn_name])
            if "form_id" in action_cfg:
                btn["form_id"] = action_cfg["form_id"]

            actions.append({
                "label":      btn.get("label", ""),
                "type":       btn.get("type", "button"),
                "class":      btn.get("class", ""),
                "id":         btn.get("id", ""),
                "title":      btn.get("title", ""),
                "form_id":    btn.get("form_id", ""),
                "data_attrs": btn.get("data_attrs", {}),
            })

        return {
            "container_class": container_class,
            "actions":         actions,
        }
