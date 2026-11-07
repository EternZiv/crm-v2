"""
Feature registration for the field requirements app.
"""

# First party imports (Finlo)
from finlo.registry.feature import register_feature

register_feature(
    "field_requirements",
    "field_requirement_models",
    auto_register_all=False,
)
