"""
URL patterns for Finlo Calendar API
"""

# Third-party imports (Django)
from rest_framework.routers import DefaultRouter

# First party imports (Finlo)
from finlo.urls import include, path

# Local imports
from .views import UserAvailabilityViewSet, UserCalendarPreferenceViewSet

router = DefaultRouter()
router.register(r"user-calendar-preferences", UserCalendarPreferenceViewSet)
router.register(r"user-availabilities", UserAvailabilityViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
