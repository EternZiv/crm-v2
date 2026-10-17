"""
This module defines the FinloAttachment model,
"""

# Standard library imports
import logging

# First party imports (Finlo)
from finlo.contrib.utils.methods import sanitize_html, sanitize_plain_text
from finlo.db import models
from finlo.urls import reverse_lazy
from finlo.utils.translation import gettext_lazy as _
from finlo.utils.upload import upload_path

# Local imports
from .base import FinloContentType, FinloCoreModel

logger = logging.getLogger(__name__)


class FinloAttachment(FinloCoreModel):
    """
    Model representing a generic attachment in the Finlo system.

    This model allows attaching files or notes to any model instance using
    Django's GenericForeignKey mechanism.
    """

    title = models.CharField(max_length=255, verbose_name=_("Title"))
    content_type = models.ForeignKey(
        FinloContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Related Object Type"),
        help_text=_("The type of object this attachment is related to."),
    )
    object_id = models.PositiveIntegerField(
        verbose_name=_("Related Object ID"),
        help_text=_("The ID of the object this attachment is related to."),
    )
    related_object = models.GenericForeignKey("content_type", "object_id")
    file = models.FileField(
        _("File"),
        upload_to=upload_path,
        null=True,
        blank=True,
        help_text=_("Optional file attached to this record."),
    )
    description = models.TextField(
        _("Notes"),
        blank=True,
        null=True,
        help_text=_("Optional description or notes about the attachment."),
    )

    class Meta:
        db_table = "core_horillaattachment"
        """
        Metadata for FinloAttachment model.
        """

        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def clean(self):
        """Sanitize rich-text notes and plain-text title to prevent XSS."""
        if self.title:
            self.title = sanitize_plain_text(self.title)
        if self.description:
            self.description = sanitize_html(self.description)

    def save(self, *args, **kwargs):
        """Ensure clean() runs on every save path, including admin and API."""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Returns a human-readable string representation of the attachment.
        """
        return str(self.title)

    def get_detail_view_url(self):
        """
        Returns the URL for viewing the details of this attachment.

        Returns:
            str: URL for the detail view of the attachment.
        """
        return reverse_lazy("generics:notes_attachment_view", kwargs={"pk": self.pk})

    def get_edit_url(self):
        """
        Returns the URL for editing this attachment.

        Returns:
            str: URL for the edit view of the attachment.
        """
        return reverse_lazy("generics:notes_attachment_edit", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        Returns the URL for deleting this attachment.

        Returns:
            str: URL for the delete view of the attachment.
        """
        return reverse_lazy("generics:notes_attachment_delete", kwargs={"pk": self.pk})


# Backwards compatibility alias
HorillaAttachment = FinloAttachment
