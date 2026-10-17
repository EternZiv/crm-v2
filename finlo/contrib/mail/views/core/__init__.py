"""
Views for Finlo Mail app.

This package provides mail form, recipients, preview, draft, delete and schedule views.
Submodules: base, form, recipients, preview_draft, delete_schedule.
"""

from finlo.contrib.mail.views.core.base import (
    extract_inline_images_with_cid,
    parse_email_pills_context,
)
from finlo.contrib.mail.views.core.schedule import (
    FinloMailtDeleteView,
    ScheduleMailModallView,
    ScheduleMailView,
)
from finlo.contrib.mail.views.core.form import FinloMailFormView
from finlo.contrib.mail.views.core.preview_draft import (
    CheckDraftChangesView,
    DiscardDraftView,
    FinloMailPreviewView,
    SaveDraftView,
)
from finlo.contrib.mail.views.core.recipients import (
    AddEmailView,
    EmailSuggestionView,
    FinloMailFieldSelectionView,
    RemoveEmailView,
)
from finlo.contrib.mail.views.core.track import TrackOpenView

__all__ = [
    "parse_email_pills_context",
    "extract_inline_images_with_cid",
    "FinloMailFormView",
    "AddEmailView",
    "RemoveEmailView",
    "EmailSuggestionView",
    "FinloMailFieldSelectionView",
    "FinloMailPreviewView",
    "CheckDraftChangesView",
    "SaveDraftView",
    "DiscardDraftView",
    "FinloMailtDeleteView",
    "ScheduleMailView",
    "ScheduleMailModallView",
    "TrackOpenView",
]
