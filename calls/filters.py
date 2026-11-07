"""Filters for the Finlo Calls Integration app."""

# First party imports (Finlo)
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from .models import AgentMapping, CallLog, CallProvider


class CallProviderFilter(FinloFilterSet):
    """Filter for CallProvider list view."""

    class Meta:
        """Meta options for CallProviderFilter."""

        model = CallProvider
        fields = "__all__"
        exclude = [
            "additional_info",
            "api_key",
            "api_secret",
            "webhook_secret",
            "extra_config",
        ]
        search_fields = ["name", "account_sid", "caller_id"]


class AgentMappingFilter(FinloFilterSet):
    """Filter for AgentMapping list view."""

    class Meta:
        """Meta options for AgentMappingFilter."""

        model = AgentMapping
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["extension", "agent_id"]


class CallLogFilter(FinloFilterSet):
    """Filter for CallLog list view."""

    class Meta:
        """Meta options for CallLogFilter."""

        model = CallLog
        fields = "__all__"
        exclude = [
            "additional_info",
            "provider_call_id",
            "recording_url",
            "related_model_name",
            "related_object_id",
        ]
        search_fields = ["from_number", "to_number"]
