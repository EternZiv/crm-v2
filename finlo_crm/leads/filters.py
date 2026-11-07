"""Filters for Lead and LeadStatus models."""

# First party imports (Finlo)
from finlo.contrib.core.mixins import OwnerFiltersetMixin
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from .models import Lead, LeadAssignmentRule, LeadStatus


class LeadFilter(OwnerFiltersetMixin, FinloFilterSet):
    """Lead Filter"""

    class Meta:
        """Meta class for LeadFilter"""

        model = Lead
        fields = "__all__"
        exclude = ["additional_info", "is_convert", "message_id"]
        search_fields = ["first_name", "email", "title"]


class LeadStatusFilter(FinloFilterSet):
    """LeadStatus Filter"""

    class Meta:
        """Meta class for LeadStatusFilter"""

        model = LeadStatus
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]


class LeadAssignmentFilter(FinloFilterSet):
    """Lead Assignment Filter"""

    class Meta:
        """Meta class for Lead Assignment Filter"""

        model = LeadAssignmentRule
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]
