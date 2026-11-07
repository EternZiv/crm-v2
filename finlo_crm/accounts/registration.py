"""
Feature registration for Accounts app.
"""

# First-party / Finlo apps
from calls.registration import register_callable_model
from finlo.contrib.cadences.registration import register_cadence_tab

# First-party / Finlo apps
from finlo.registry.feature import register_model_for_feature

register_model_for_feature(
    app_label="accounts",
    model_name="Account",
    all=True,
    features=[
        "duplicate_models",
        "approval_models",
        "reviews_models",
        "workflow_models",
        "scoring",
        "activity_related_models",
        "custom_calendar_models",
    ],
)

register_cadence_tab(
    app_label="accounts",
    model_name="Account",
    url_prefix="account-cadences-tab/<int:pk>/",
    url_name="account_cadences_tab",
)

register_callable_model("accounts", "Account", "account_number")
