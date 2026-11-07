"""Filters for finlo.contrib.dashboard app."""

# First party imports (Finlo)
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from .models import Dashboard


class DashboardFilter(FinloFilterSet):
    """Dashboard Filter"""

    class Meta:
        """Meta class for DashboardFilter"""

        model = Dashboard
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]
