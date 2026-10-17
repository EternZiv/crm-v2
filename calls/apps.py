"""App configuration for the Finlo Calls Integration app."""

from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class CallsConfig(AppLauncher):
    """App configuration for the Finlo Calls Integration app."""

    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "calls"
    label = "calls"
    verbose_name = _("Calls Integration")

    url_prefix = "calls/"
    url_module = "calls.urls"
    url_namespace = "calls"

    auto_import_modules = [
        "menu",
        "signals",
        "registration",
        "extensions",
    ]

    report_files = [
        "report_data/reports.json",
    ]

    def get_api_paths(self):
        return [
            {
                "pattern": "calls/",
                "view_or_include": "calls.api.urls",
                "name": "finlo_calls_api",
                "namespace": "finlo_calls",
            }
        ]
