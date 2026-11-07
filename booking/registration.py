"""
Feature registration for the finlo_booking app.
"""

# First party imports (Finlo)
from finlo.registry.feature import register_model_for_feature

register_model_for_feature(
    app_label="booking",
    model_name="Booking",
    features=["export_data"],
)
