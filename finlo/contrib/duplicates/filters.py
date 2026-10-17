"""
Filters for the duplicates app
"""

# Third-party imports (Django)
import django_filters

# First party imports (Finlo)
from finlo.contrib.core.models import FinloContentType
from finlo.contrib.generics.filters import FinloFilterSet

# Local imports
from .models import DuplicateRule, MatchingRule


class MatchingRuleFilter(FinloFilterSet):
    """
    Filter for MatchingRule
    """

    content_type = django_filters.ModelChoiceFilter(
        queryset=FinloContentType.objects.all(),
        field_name="content_type",
    )

    class Meta:
        """Meta options for MatchingRuleFilter."""

        model = MatchingRule
        fields = ["content_type"]
        search_fields = ["name", "description"]


class DuplicateRuleFilter(FinloFilterSet):
    """
    Filter for DuplicateRule
    """

    content_type = django_filters.ModelChoiceFilter(
        queryset=FinloContentType.objects.all(),
        field_name="content_type",
    )
    matching_rule = django_filters.ModelChoiceFilter(
        queryset=MatchingRule.objects.all(),
        field_name="matching_rule",
    )

    class Meta:
        """Meta options for DuplicateRuleFilter."""

        model = DuplicateRule
        fields = ["content_type", "matching_rule"]
        search_fields = ["name", "description"]
