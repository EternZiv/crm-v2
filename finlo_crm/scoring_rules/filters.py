"""Filters for ScoringRule model."""

from finlo.contrib.generics.filters import FinloFilterSet
from finlo_crm.scoring_rules.models import ScoringRule


class ScoringRuleFilter(FinloFilterSet):
    """Filter set for scoring rules."""

    class Meta:  # pylint: disable=missing-class-docstring
        model = ScoringRule
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]
