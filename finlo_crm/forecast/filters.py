"""
Filters for the forecast app.

This module defines filter classes used to search and filter forecast records.
"""

# First party imports (Finlo)
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from finlo_crm.forecast.models import ForecastTarget, ForecastType


class ForecastTargetFilter(FinloFilterSet):
    """
    Filter class for ForecastTarget model
    """

    class Meta:
        """Filter options for the ForecastTarget model."""

        model = ForecastTarget
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["target_amount"]


class ForecastTypeFilter(FinloFilterSet):
    """
    Filter class for ForecastType model
    """

    class Meta:
        """Filter options for the ForecastType model."""

        model = ForecastType
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]
