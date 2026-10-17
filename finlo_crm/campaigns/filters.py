"""
Defines filters for the Campaign model, enabling search and exclusion of specific fields.
"""

# First party imports (Finlo)
from finlo.contrib.core.mixins import OwnerFiltersetMixin
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from .models import Campaign


class CampaignFilter(OwnerFiltersetMixin, FinloFilterSet):
    """
    Campaign Filter
    """

    class Meta:
        """
        Meta class for CampaignFilter
        """

        model = Campaign
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["campaign_name"]
