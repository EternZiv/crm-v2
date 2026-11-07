"""
URL configuration for finlo_crm.leads API

This module mirrors the URL structure of finlo_crm.accounts API
using DefaultRouter for consistent endpoint patterns.
"""

# Third-party imports (other)
from rest_framework.routers import DefaultRouter

# First party imports (Finlo)
from finlo.urls import include, path

# Local imports
from finlo_crm.leads.api.views import LeadStatusViewSet, LeadViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r"leads", LeadViewSet, basename="lead")
router.register(r"lead-statuses", LeadStatusViewSet, basename="leadstatus")

urlpatterns = [
    path("", include(router.urls)),
]
