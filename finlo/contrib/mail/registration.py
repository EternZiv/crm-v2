"""
Feature registration for Finlo Mail app.
"""

# First party imports (Finlo)
from finlo.registry.feature import register_feature, register_model_for_feature

register_feature("mail_template", "mail_template_models")

register_model_for_feature(
    app_label="mail",
    model_name="FinloMail",
    features=["export_data"],
)
