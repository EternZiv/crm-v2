"""
URL patterns for activity API
"""

from rest_framework.routers import DefaultRouter

from finlo.urls import include, path

from .views import ActivityViewSet

router = DefaultRouter()
router.register(r"activities", ActivityViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
