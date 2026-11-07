"""
Serializers for finlo_crm.contacts models
"""

# Third-party imports (other)
from rest_framework import serializers

# First party imports (Finlo)
from finlo.api.mixins import CompanyScopedSerializerMixin
from finlo.contrib.core.api.serializers import FinloUserSerializer

# Local imports
from finlo_crm.contacts.models import Contact


class ContactSerializer(CompanyScopedSerializerMixin, serializers.ModelSerializer):
    """Serializer for Contact model"""

    contact_owner_details = FinloUserSerializer(
        source="contact_owner", read_only=True
    )
    parent_contact_details = serializers.SerializerMethodField()

    class Meta:
        """Meta options for ContactSerializer."""

        model = Contact
        fields = "__all__"

    def get_parent_contact_details(self, obj):
        """Return minimal details of parent contact if present"""
        if obj.parent_contact:
            return {
                "id": obj.parent_contact.id,
                "first_name": obj.parent_contact.first_name,
                "last_name": obj.parent_contact.last_name,
                "email": obj.parent_contact.email,
            }
        return None
