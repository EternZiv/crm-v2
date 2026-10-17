"""App configuration for the Campaign module."""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class CampaignsConfig(AppLauncher):
    """Campaigns App Configuration"""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo_crm.campaigns"
    verbose_name = _("Campaigns")

    url_prefix = "crm/campaigns/"
    url_module = "finlo_crm.campaigns.urls"
    url_namespace = "campaigns"

    auto_import_modules = [
        "registration",
        "signals",
        "menu",
        "dashboard",
    ]

    demo_data = {
        "files": [
            (6, "load_data/campaign.json"),
        ],
        "order": 4,
    }

    report_files = [
        "report_data/reports.json",
    ]

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/campaigns/",
                "view_or_include": "finlo_crm.campaigns.api.urls",
                "name": "finlo_crm_campaigns_api",
                "namespace": "finlo_crm_campaigns",
            }
        ]
