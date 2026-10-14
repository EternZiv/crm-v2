"""
Serializers for horilla_crm.leads models
"""

# Third-party imports (other)
from rest_framework import serializers

# First party imports (Horilla)
from horilla.api.mixins import CompanyScopedSerializerMixin

# Local imports
from horilla_crm.leads.models import Lead, LeadStatus


class LeadSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for Lead model"""

    class Meta:
        """Meta options for LeadSerializer."""

        model = Lead
        fields = "__all__"
        read_only_fields = ["lead_owner", "sub_owner"]

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            validated_data["lead_owner"] = user
            validated_data["sub_owner"] = None
        return super().create(validated_data)


class LeadStatusSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for LeadStatus model"""

    class Meta:
        """Meta options for LeadStatusSerializer."""

        model = LeadStatus
        fields = "__all__"
