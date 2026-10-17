"""
Feature registration for custom calendars.
"""

# First party imports (Finlo)
from finlo.registry.feature import register_feature

register_feature("custom_calendar", "custom_calendar_models", auto_register_all=False)
