"""Filter classes for mail models."""

# First party imports (Finlo)
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from .models import (
    FinloMail,
    FinloMailConfiguration,
    FinloMailTemplate,
    IncomingMail,
)

# Define your mail filters here


class FinloMailServerFilter(FinloFilterSet):
    """Filter set for FinloMailConfiguration model."""

    class Meta:
        """Meta class for FinloMailServerFilter."""

        model = FinloMailConfiguration
        fields = "__all__"
        exclude = ["additional_info", "token"]
        search_fields = ["host", "username"]


class FinloMailTemplateFilter(FinloFilterSet):
    """Filter set for FinloMailTemplate model."""

    class Meta:
        """Meta class for FinloMailTemplateFilter."""

        model = FinloMailTemplate
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["title"]


class FinloMailHistoryFilter(FinloFilterSet):
    """Filter set for FinloMail history list."""

    class Meta:
        """Meta class for FinloMailHistoryFilter."""

        model = FinloMail
        fields = "__all__"
        exclude = [
            "body",
            "rendered_body",
            "rendered_subject",
            "tracking_uid",
            "mail_status_message",
            "content_type",
            "object_id",
            "additional_info",
        ]
        search_fields = ["subject", "to"]


class IncomingMailFilter(FinloFilterSet):
    """Filter set for IncomingMail list."""

    class Meta:
        """Meta class for IncomingMailFilter."""

        model = IncomingMail
        fields = "__all__"
        exclude = [
            "body",
            "cc",
            "message_id",
            "in_reply_to",
            "references",
            "additional_info",
        ]
        search_fields = ["sender_email", "sender_name", "subject"]
