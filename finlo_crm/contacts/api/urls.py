"""
URL patterns for finlo_crm.contacts API
"""

# Third-party imports (other)
from rest_framework.routers import DefaultRouter

# First party imports (Finlo)
from finlo.urls import include, path

# Local imports
from finlo_crm.contacts.api.views import ContactViewSet

router = DefaultRouter()
router.register(r"contacts", ContactViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
