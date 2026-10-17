"""Configuration for the calendar app in Finlo."""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class CalendarConfig(AppLauncher):
    """App configuration class for the Finlo Calendar app."""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.calendar"
    label = "calendar"
    verbose_name = _("Calendar")

    url_prefix = "calendar/"
    url_module = "finlo.contrib.calendar.urls"
    url_namespace = "calendar"

    auto_import_modules = [
        "registration",
        "menu",
        "signals",
    ]

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "/calendar/",
                "view_or_include": "finlo.contrib.calendar.api.urls",
                "name": "calendar_api",
                "namespace": "calendar",
            }
        ]
