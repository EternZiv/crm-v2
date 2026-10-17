"""
Feature registration for Finlo Core app.
"""

# First party imports (Finlo)
from finlo.auth.models import User
from finlo.registry.asset_registry import register_html
from finlo.registry.feature import register_feature, register_models_for_feature

# Local imports
from .models import Company, Department, Role

register_html(
    "inject_html/rtl_assets.html",
    slot="head_end",
    priority=90,
)

register_html(
    "inject_html/rtl_assets.html",
    slot="head_end",
    priority=90,
    page="login",
)


register_models_for_feature(
    models=[
        Company,
        Department,
        Role,
        User,
    ],
    all=True,
    exclude=["dashboard_component", "report_choices"],
)


register_feature(
    "template_reverse",
    "template_reverse_models",
)
