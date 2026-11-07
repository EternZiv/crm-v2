"""
Menu registration for the Finlo CRM Scoring Rules app.
"""

from finlo.contrib.core.menu import BaseSettings
from finlo.urls import reverse_lazy
from finlo_crm.scoring_rules.models import ScoringRule

BaseSettings.items.append(
    {
        "label": ScoringRule()._meta.verbose_name,
        "url": reverse_lazy("scoring_rules:scoring_rule_view"),
        "hx-target": "#settings-content",
        "hx-push-url": "true",
        "hx-select": "#scoring-rule-view",
        "hx-select-oob": "#settings-sidebar",
        "perm": "scoring_rules.view_scoringrule",
    },
)
