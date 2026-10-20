"""
Serializers for finlo_crm.opportunities models
"""

# Third-party imports (other)
from rest_framework import serializers

# First party imports (Finlo)
from finlo.api.mixins import CompanyScopedSerializerMixin
from finlo.contrib.core.api.serializers import FinloUserSerializer
from finlo.contrib.generics.views.details import check_record_change_access
from finlo_crm.leads.models import Lead
from finlo_crm.opportunities.authorization import is_valid_bdo_opportunity_source

# Local imports
from finlo_crm.opportunities.models import (
    DefaultOpportunityMember,
    Opportunity,
    OpportunityStage,
    OpportunityTeam,
    OpportunityTeamMember,
)


class OpportunityStageSerializer(
    CompanyScopedSerializerMixin, serializers.ModelSerializer
):
    """Serializer for OpportunityStage model"""

    class Meta:
        """Meta options for OpportunityStageSerializer."""

        model = OpportunityStage
        fields = "__all__"


class OpportunitySerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for Opportunity model"""

    owner_details = FinloUserSerializer(source="owner", read_only=True)
    stage_details = OpportunityStageSerializer(source="stage", read_only=True)
    source_lead_id = serializers.PrimaryKeyRelatedField(
        source="source_lead",
        queryset=Lead.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        """Meta options for OpportunitySerializer."""

        model = Opportunity
        fields = "__all__"
        read_only_fields = ["source_lead"]

    def get_fields(self):
        fields = super().get_fields()
        fields["owner"].required = False
        return fields

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        role_key = getattr(getattr(user, "role", None), "system_key", None)

        if self.instance is not None and "source_lead" in attrs:
            if attrs["source_lead"] != self.instance.source_lead:
                raise serializers.ValidationError(
                    {"source_lead_id": "The source lead cannot be changed."}
                )

        if self.instance is None and role_key == "BDO":
            source_lead = attrs.get("source_lead")
            if not is_valid_bdo_opportunity_source(user, source_lead, request):
                raise serializers.ValidationError(
                    {
                        "source_lead_id": (
                            "Select a qualified lead currently assigned to you."
                        )
                    }
                )
            requested_owner = attrs.get("owner")
            if requested_owner is not None and requested_owner.pk != user.pk:
                raise serializers.ValidationError(
                    {"owner": "A BDO must own the opportunity they create."}
                )
            attrs["owner"] = user

        return attrs


class OpportunityTeamSerializer(
    CompanyScopedSerializerMixin, serializers.ModelSerializer
):
    """Serializer for OpportunityTeam model"""

    owner_details = FinloUserSerializer(source="owner", read_only=True)

    class Meta:
        """Meta options for OpportunityTeamSerializer."""

        model = OpportunityTeam
        fields = "__all__"


class OpportunityTeamMemberSerializer(
    CompanyScopedSerializerMixin, serializers.ModelSerializer
):
    """Serializer for OpportunityTeamMember model"""

    user_details = FinloUserSerializer(source="user", read_only=True)
    opportunity_details = OpportunitySerializer(source="opportunity", read_only=True)

    class Meta:
        """Meta options for OpportunityTeamMemberSerializer."""

        model = OpportunityTeamMember
        fields = "__all__"

    def validate(self, attrs):
        """
        Require the requester to already have change access on the target
        Opportunity before they can add/modify a team-member row.

        opportunity_access="owner" (or "edit") on OpportunityTeamMember
        grants full change/delete rights on the linked Opportunity via
        Opportunity.has_granted_access/TEAM_ACCESS_LEVELS_FOR_ACTION.
        Without this check, a user holding only add_opportunityteammember
        (not change_opportunity/add_opportunity) could self-escalate by
        adding themselves as an "owner"-level member of any opportunity,
        including ones they have no other authorization to touch.
        """
        attrs = super().validate(attrs)
        opportunity = attrs.get("opportunity") or getattr(
            self.instance, "opportunity", None
        )
        request = self.context.get("request")
        if opportunity is not None and request is not None:
            user = request.user
            if not user.is_superuser and not check_record_change_access(
                user, opportunity
            ):
                raise serializers.ValidationError(
                    {
                        "opportunity": "You do not have permission to manage "
                        "team members for this opportunity."
                    }
                )
        return attrs


class DefaultOpportunityMemberSerializer(
    CompanyScopedSerializerMixin, serializers.ModelSerializer
):
    """Serializer for DefaultOpportunityMember model"""

    user_details = FinloUserSerializer(source="user", read_only=True)
    team_details = OpportunityTeamSerializer(source="team", read_only=True)

    class Meta:
        """Meta options for DefaultOpportunityMemberSerializer."""

        model = DefaultOpportunityMember
        fields = "__all__"
