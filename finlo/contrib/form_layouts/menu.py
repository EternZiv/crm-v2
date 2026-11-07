"""
Settings menu entries for the form layouts app.
"""

from finlo.menu import settings_menu

# First party imports (Finlo)
from finlo.urls import reverse_lazy
from finlo.utils.translation import gettext_lazy as _


@settings_menu.register
class FormLayoutSettings:
    """Settings menu entries for configurable form layouts."""

    title = _("Form Layouts")
    icon = "/assets/icons/form-layout.svg"
    order = 6
    items = [
        {
            "label": _("Form Layout"),
            "url": reverse_lazy("form_layouts:form_layout_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#form-layout-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "form_layouts.view_formlayoutfield",
            "order": 1,
        },
    ]
