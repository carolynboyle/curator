"""
viewkit.models - Data structures for view definitions.

Framework-agnostic dataclasses representing parsed view configuration.
Callers receive these objects from ViewBuilder and use them however
their rendering layer requires — Jinja2, a REST response, a CLI table,
or anything else.

FieldDef  — one field on a create/edit form
ColumnDef — one column in a list/table view
ViewDef   — a named view containing its columns and fields
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FieldDef:
    """
    Definition of a single form field.

    Attributes:
        name:       Column name in the database / key in a data dict.
        label:      Human-readable label for display.
        field_type: Input type. One of: text, textarea, select, date,
                    number, checkbox. Defaults to 'text'.
        required:   Whether the field must have a value on submit.
        readonly:   Whether the field is displayed but not editable.
        source:     For select fields — the lookup table or data source
                    that provides the options. The caller is responsible
                    for fetching options; viewkit only records the name.
        placeholder: Optional placeholder text for text inputs.
        help_text:  Optional descriptive text shown below the field.
    """

    name: str
    label: str
    field_type: str = "text"
    required: bool = False
    readonly: bool = False
    source: Optional[str] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None

    def __post_init__(self):
        valid_types = {"text", "textarea", "select", "date", "number", "checkbox"}
        if self.field_type not in valid_types:
            raise ValueError(
                f"FieldDef '{self.name}': invalid field_type '{self.field_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )
        if self.field_type == "select" and self.source is None:
            raise ValueError(
                f"FieldDef '{self.name}': field_type 'select' requires a 'source'."
            )


@dataclass
class ColumnDef:
    """
    Definition of a single column in a list or table view.

    Attributes:
        name:      Key in the data dict that provides this column's value.
        label:     Human-readable column header.
        link:      Whether this column should be rendered as a link to
                   the detail view for the row. Typically true for the
                   primary display column (e.g. name, title).
        sortable:  Whether the column header should offer sort controls.
        truncate:  Maximum display length before truncation. None = no limit.
    """

    name: str
    label: str
    link: bool = False
    sortable: bool = False
    truncate: Optional[int] = None


@dataclass
class ViewDef:
    """
    A named view definition containing its column and field configuration.

    Attributes:
        name:    The key used to look up this view in views.yaml.
        title:   Human-readable title for the view (page heading, etc.).
        columns: Ordered list of ColumnDef for list/table rendering.
        fields:  Ordered list of FieldDef for form rendering.
    """

    name: str
    title: str
    columns: list[ColumnDef] = field(default_factory=list)
    fields: list[FieldDef] = field(default_factory=list)
