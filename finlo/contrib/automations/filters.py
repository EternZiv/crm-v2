"""
Filters for the automations app
"""

# First party imports (Finlo)
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from .models import FinloAutomation

# Define your automations filters here


class FinloAutomationFilter(FinloFilterSet):
    """Filter set for FinloMailConfiguration model."""

    class Meta:
        """Meta class for FinloMailServerFilter."""

        model = FinloAutomation
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["title"]
