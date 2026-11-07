"""
API views for mail models

Follows core architecture: ModelViewSets with SearchFilterMixin and BulkOperationsMixin,
permissions, and swagger documentation.
"""

# Third-party imports (Django)
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action

# First party imports (Finlo)
from finlo.api.mixins import BulkOperationsMixin, SearchFilterMixin
from finlo.api.permissions import (
    FinloModelPermissions,
    IsCompanyMember,
    IsOwnerOrAdmin,
)

from ..models import (
    FinloMail,
    FinloMailAttachment,
    FinloMailConfiguration,
    FinloMailTemplate,
)

# Local imports
from .docs import MAIL_BULK_DELETE_DOCS, MAIL_BULK_UPDATE_DOCS, MAIL_SEARCH_FILTER_DOCS
from .serializers import (
    FinloMailAttachmentSerializer,
    FinloMailConfigurationSerializer,
    FinloMailSerializer,
    FinloMailTemplateSerializer,
)

# Common search parameter
search_param = openapi.Parameter(
    "search",
    openapi.IN_QUERY,
    description="Search term for full-text search across relevant fields",
    type=openapi.TYPE_STRING,
)


class FinloMailConfigurationViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for FinloMailConfiguration model"""

    queryset = FinloMailConfiguration.objects.all().select_related(
        "company", "created_by"
    )
    serializer_class = FinloMailConfigurationSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsOwnerOrAdmin,
        FinloModelPermissions,
    ]
    scope_list_to_view_permission = True
    search_fields = [
        "type",
        "username",
        "from_email",
        "display_name",
        "host",
    ]
    filterset_fields = [
        "type",
        "is_primary",
        "company",
        "use_tls",
        "use_ssl",
        "mail_channel",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param], operation_description=MAIL_SEARCH_FILTER_DOCS
    )
    def list(self, request, *args, **kwargs):
        """List mail configurations with search and filter support."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_UPDATE_DOCS)
    @action(detail=False, methods=["post"])
    def bulk_update(self, request, *args, **kwargs):
        """Update multiple mail configurations."""
        return super().bulk_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_DELETE_DOCS)
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request, *args, **kwargs):
        """Delete multiple mail configurations."""
        return super().bulk_delete(request, *args, **kwargs)


class FinloMailViewSet(SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet):
    """ViewSet for FinloMail model"""

    queryset = FinloMail.objects.all().select_related(
        "sender", "content_type", "created_by", "company"
    )
    serializer_class = FinloMailSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsOwnerOrAdmin,
        FinloModelPermissions,
    ]
    scope_list_to_view_permission = True
    search_fields = ["subject", "to", "cc", "bcc", "mail_status"]
    filterset_fields = [
        "sender",
        "mail_status",
        "content_type",
        "object_id",
        "company",
        "created_by",
        "scheduled_at",
        "sent_at",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param], operation_description=MAIL_SEARCH_FILTER_DOCS
    )
    def list(self, request, *args, **kwargs):
        """List mail records with search and filter support."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_UPDATE_DOCS)
    @action(detail=False, methods=["post"])
    def bulk_update(self, request, *args, **kwargs):
        """Update multiple mail records."""
        return super().bulk_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_DELETE_DOCS)
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request, *args, **kwargs):
        """Delete multiple mail records."""
        return super().bulk_delete(request, *args, **kwargs)


class FinloMailAttachmentViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for FinloMailAttachment model"""

    queryset = FinloMailAttachment.objects.all().select_related(
        "mail", "created_by", "company"
    )
    serializer_class = FinloMailAttachmentSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsOwnerOrAdmin,
        FinloModelPermissions,
    ]
    scope_list_to_view_permission = True
    search_fields = ["mime_type"]
    filterset_fields = ["mail", "is_inline", "content_id", "company", "created_by"]

    @swagger_auto_schema(
        manual_parameters=[search_param], operation_description=MAIL_SEARCH_FILTER_DOCS
    )
    def list(self, request, *args, **kwargs):
        """List mail attachments with search and filter support."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_UPDATE_DOCS)
    @action(detail=False, methods=["post"])
    def bulk_update(self, request, *args, **kwargs):
        """Update multiple mail attachments."""
        return super().bulk_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_DELETE_DOCS)
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request, *args, **kwargs):
        """Delete multiple mail attachments."""
        return super().bulk_delete(request, *args, **kwargs)


class FinloMailTemplateViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for FinloMailTemplate model"""

    queryset = FinloMailTemplate.objects.all().select_related("company", "created_by")
    serializer_class = FinloMailTemplateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsCompanyMember,
        FinloModelPermissions,
    ]
    scope_list_to_view_permission = True
    search_fields = ["title", "body"]
    filterset_fields = ["company", "content_type", "created_by"]

    @swagger_auto_schema(
        manual_parameters=[search_param], operation_description=MAIL_SEARCH_FILTER_DOCS
    )
    def list(self, request, *args, **kwargs):
        """List mail templates with search and filter support."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_UPDATE_DOCS)
    @action(detail=False, methods=["post"])
    def bulk_update(self, request, *args, **kwargs):
        """Update multiple mail templates."""
        return super().bulk_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_DELETE_DOCS)
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request, *args, **kwargs):
        """Delete multiple mail templates."""
        return super().bulk_delete(request, *args, **kwargs)
