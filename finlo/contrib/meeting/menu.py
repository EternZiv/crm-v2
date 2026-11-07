"""
Registers Settings → Integrations and My Settings menu entries
for the Finlo Meeting Integration app.
"""

from finlo.contrib.core.menu import IntegrationsSettings
from finlo.menu import my_settings_menu

# First party imports (Finlo)
from finlo.urls import reverse_lazy
from finlo.utils.translation import gettext_lazy as _

# Local imports
from .models import MeetingIntegrationSetting

# Register Meeting Integration under Settings → Integrations
IntegrationsSettings.items.append(
    {
        "label": _("Meeting Integration"),
        "url": reverse_lazy("meeting:meeting_integration_settings"),
        "hx-target": "#settings-content",
        "hx-push-url": "true",
        "hx-select": "#meeting-integration-settings-view",
        "hx-select-oob": "#settings-sidebar",
        "perm": "meeting.change_meetingintegrationsetting",
    }
)


@my_settings_menu.register
class MeetingUserSettings:
    """Registers Meeting integration in the My Settings sidebar."""

    title = _("Meeting")
    url = reverse_lazy("meeting:meeting_user_settings")
    active_urls = "meeting:meeting_user_settings"
    order = 6
    attrs = {
        "hx-boost": "true",
        "hx-target": "#my-settings-content",
        "hx-push-url": "true",
        "hx-select": "#meeting-user-settings-view",
        "hx-select-oob": "#my-settings-sidebar",
    }
    condition = staticmethod(MeetingIntegrationSetting.user_has_menu_access)
