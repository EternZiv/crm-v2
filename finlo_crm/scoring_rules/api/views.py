"""API views for the scoring_rules app."""

from rest_framework import permissions, viewsets

from finlo.api.mixins import BulkOperationsMixin, SearchFilterMixin
from finlo.api.permissions import FinloModelPermissions, IsCompanyMember
from finlo_crm.scoring_rules.api.serializers import (
    ScoringCriterionSerializer,
    ScoringRuleSerializer,
)
from finlo_crm.scoring_rules.models import ScoringCriterion, ScoringRule


class ScoringRuleViewSet(SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet):
    """ViewSet for ScoringRule model."""

    queryset = ScoringRule.objects.all()
    serializer_class = ScoringRuleSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsCompanyMember,
        FinloModelPermissions,
    ]
    scope_list_to_view_permission = True
    search_fields = ["name", "description"]
    filterset_fields = ["module", "is_active"]


class ScoringCriterionViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for ScoringCriterion model."""

    queryset = ScoringCriterion.objects.all()
    serializer_class = ScoringCriterionSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsCompanyMember,
        FinloModelPermissions,
    ]
    scope_list_to_view_permission = True
    search_fields = ["name"]
    filterset_fields = ["rule"]
