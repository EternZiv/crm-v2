"""Extension of INSTALLED_APPS with Finlo modules."""

from finlo.settings.base import INSTALLED_APPS

INSTALLED_APPS.extend(
    [
        "finlo_crm.accounts",
        "finlo_crm.contacts",
        "finlo_crm.leads",
        "finlo_crm.scoring_rules",
        "finlo_crm.campaigns",
        "finlo_crm.opportunities",
        "finlo_crm.forecast",
        "booking",
        "calls",
        "custom_fields",
    ]
)
