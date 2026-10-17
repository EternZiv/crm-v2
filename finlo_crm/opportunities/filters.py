"""
Filters for the Opportunities module.

Provides filtering and search capabilities for Opportunity-related models
using FinloFilterSet. Each filter class allows filtering all fields
(except 'additional_info') and provides specific search fields.
"""

# First party imports (Finlo)
from finlo.contrib.core.mixins import OwnerFiltersetMixin
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from finlo_crm.opportunities.models import (
    DefaultOpportunityMember,
    Opportunity,
    OpportunityStage,
    OpportunityTeam,
)


class OpportunityFilter(OwnerFiltersetMixin, FinloFilterSet):
    """Filter for Opportunity model with search on 'name'."""

    class Meta:
        """Meta options for OpportunityFilter."""

        model = Opportunity
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]


class OpportunityStageFilter(FinloFilterSet):
    """Filter for OpportunityStage model with search on 'name'."""

    class Meta:
        """Meta options for OpportunityStageFilter."""

        model = OpportunityStage
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]


class OpportunityTeamFilter(FinloFilterSet):
    """Filter for OpportunityTeam model with search on 'team_name'."""

    class Meta:
        """Meta options for OpportunityTeamFilter."""

        model = OpportunityTeam
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["team_name"]


class OpportunityTeamMembersFilter(FinloFilterSet):
    """Filter for DefaultOpportunityMember model with search on user names."""

    class Meta:
        """Meta options for OpportunityTeamMembersFilter."""

        model = DefaultOpportunityMember
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["user__first_name", "user__last_name"]
