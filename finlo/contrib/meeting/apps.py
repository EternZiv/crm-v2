"""Configuration for the meeting integration app in Finlo."""

from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class MeetingConfig(AppLauncher):
    """App configuration for the Finlo Meeting Integration app."""

    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.meeting"
    label = "meeting"
    verbose_name = _("Meeting Integration")

    url_prefix = "meeting/"
    url_module = "finlo.contrib.meeting.urls"
    url_namespace = "meeting"

    auto_import_modules = [
        "menu",
        "signals",
    ]
