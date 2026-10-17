"""
This module is responsible for registering the notification template feature in the Finlo framework. It imports the necessary function to register the feature and then registers the "notification_template" feature with its corresponding models."
"""

# First party imports (Finlo)
from finlo.registry.feature import register_feature

register_feature("notification_template", "notification_template_models")
