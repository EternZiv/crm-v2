"""
Feature registration for Finlo duplicates app.
"""

# First party imports (Finlo)
from finlo.registry.feature import register_feature

register_feature(
    "duplicate_data",
    "duplicate_models",
    auto_register_all=False,
)
