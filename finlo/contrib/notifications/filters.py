"""Filter classes for notification template models."""

# First party imports (Finlo)
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from .models import NotificationTemplate

# Define your notifications filters here


class NotificationTemplateFilter(FinloFilterSet):
    """Filter set for FinloMailTemplate model."""

    class Meta:
        """Meta class for FinloMailTemplateFilter."""

        model = NotificationTemplate
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["title"]
