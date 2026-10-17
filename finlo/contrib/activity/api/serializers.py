"""
Serializers for activity models
"""

from rest_framework import serializers

from finlo.api.mixins import CompanyScopedSerializerMixin
from finlo.contrib.core.api.serializers import FinloUserSerializer

from ..models import Activity


class ActivitySerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for Activity model"""

    owner_details = FinloUserSerializer(source="owner", read_only=True)
    meeting_host_details = FinloUserSerializer(source="meeting_host", read_only=True)
    assigned_to_details = FinloUserSerializer(
        source="assigned_to", many=True, read_only=True
    )
    participants_details = FinloUserSerializer(
        source="participants", many=True, read_only=True
    )

    class Meta:
        """Meta class for ActivitySerializer"""

        model = Activity
        fields = "__all__"
