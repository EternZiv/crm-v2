"""
URL patterns for finlo_crm.campaigns API
"""

# Third-party imports (other)
from rest_framework.routers import DefaultRouter

# First party imports (Finlo)
from finlo.urls import include, path

# Local imports
from finlo_crm.campaigns.api.views import CampaignViewSet

router = DefaultRouter()
router.register(r"campaigns", CampaignViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
