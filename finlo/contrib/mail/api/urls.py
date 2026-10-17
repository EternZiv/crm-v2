"""
URL patterns for mail API, consistent with core
"""

# Third-party imports (Django)
from rest_framework.routers import DefaultRouter

# First party imports (Finlo)
from finlo.urls import include, path

# Local imports
from .views import (
    FinloMailAttachmentViewSet,
    FinloMailConfigurationViewSet,
    FinloMailTemplateViewSet,
    FinloMailViewSet,
)

router = DefaultRouter()
router.register(r"mail-configurations", FinloMailConfigurationViewSet)
router.register(r"mails", FinloMailViewSet)
router.register(r"mail-attachments", FinloMailAttachmentViewSet)
router.register(r"mail-templates", FinloMailTemplateViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
