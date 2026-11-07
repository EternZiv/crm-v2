"""
Feature registration for Finlo Dashboard app.
"""

# First party imports (Finlo)
from finlo.registry.feature import register_feature, register_model_for_feature

register_feature("dashboard_component", "dashboard_component_models")

register_model_for_feature(
    app_label="dashboard",
    model_name="DashboardFolder",
    features=["global_search"],
)
