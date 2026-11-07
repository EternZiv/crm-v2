"""
Feature registration for Finlo Automations app.
"""

# First party imports (Finlo)
from finlo.registry.feature import register_feature

register_feature("automation", "automation_models")
