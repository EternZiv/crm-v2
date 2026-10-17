"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the automations app
"""

from finlo.menu import settings_menu

# First party imports (Finlo)
from finlo.urls import reverse_lazy
from finlo.utils.translation import gettext_lazy as _

# Define your menu registration logic here


@settings_menu.register
class AutomationSettings:
    """Settings menu entries for the automation module."""

    title = _("Automations")
    icon = "/assets/icons/automation.svg"
    order = 4
    items = [
        {
            "label": _("Mail & Notifications"),
            "url": reverse_lazy("automations:automation_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#automation-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "automations.view_finloautomation",
            "order": 1,
        },
    ]
