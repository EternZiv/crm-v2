"""App configuration for the forecast module."""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class ForecastConfig(AppLauncher):
    """Forecast App Configuration"""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo_crm.forecast"
    verbose_name = _("Forecast")

    url_prefix = "crm/forecast/"
    url_module = "finlo_crm.forecast.urls"
    url_namespace = "forecast"

    auto_import_modules = [
        "registration",
        "signals",
        "menu",
    ]

    demo_data = {
        "files": [
            (7, "load_data/forecast_type.json"),
        ],
        "order": 4,
    }

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/forecast/",
                "view_or_include": "finlo_crm.forecast.api.urls",
                "name": "finlo_crm_forecast_api",
                "namespace": "finlo_crm_forecast",
            }
        ]
