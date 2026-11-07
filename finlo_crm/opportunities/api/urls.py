"""
URL patterns for finlo_crm.opportunities API
"""

# Third-party imports (other)
from rest_framework.routers import DefaultRouter

# First party imports (Finlo)
from finlo.urls import include, path

# Local imports
from finlo_crm.opportunities.api.views import (
    DefaultOpportunityMemberViewSet,
    OpportunityStageViewSet,
    OpportunityTeamMemberViewSet,
    OpportunityTeamViewSet,
    OpportunityViewSet,
)

router = DefaultRouter()
router.register(r"opportunities", OpportunityViewSet)
router.register(r"opportunity-stages", OpportunityStageViewSet)
router.register(r"opportunity-teams", OpportunityTeamViewSet)
router.register(r"opportunity-team-members", OpportunityTeamMemberViewSet)
router.register(r"default-opportunity-members", DefaultOpportunityMemberViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
