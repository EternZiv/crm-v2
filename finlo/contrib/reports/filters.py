"""Filter definitions for the `finlo.contrib.reports` app."""

# First party imports (Finlo)
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from .models import Report  # Ensure your Report model is imported


class ReportFilter(FinloFilterSet):
    """Filter set for filtering reports by various fields."""

    class Meta:
        """Meta options for ReportFilter."""

        model = Report
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]
