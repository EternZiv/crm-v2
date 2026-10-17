"""Aggregate view modules for the  package."""

from finlo.contrib.mail.views.core import *
from finlo.contrib.mail.views.mail_template import (
    MailTemplateView,
    MailTemplateNavbar,
    MailTemplateListView,
    MailTemplateCreateUpdateView,
    MailTemplatePreviewView,
    TemplateContentView,
    MailTemplateSelectView,
    SaveAsMailTemplateView,
    MailTemplateDeleteView,
    MailTemplateDetailView,
)
from finlo.contrib.mail.views.outlook import (
    OutlookMailServerFormView,
    OutlookLoginView,
    OutlookCallbackView,
    refresh_outlook_token,
    OutlookRefreshTokenView,
    MailDisplayNameFieldView,
)
from finlo.contrib.mail.views.incoming_mail import (
    IncomingMailServerView,
    IncomingMailServerNavbar,
    IncomingMailServerTypeSelectionView,
    IncomingMailServerListView,
    IncomingMailServerFormView,
)
from finlo.contrib.mail.views.outgoing_mail import (
    MailServerView,
    MailServerNavbar,
    MailServerTypeSelectionView,
    MailServerListView,
    OutgoingMailServerFormView,
    MailServerTestEmailView,
    MailServerDeleteView,
)
from finlo.contrib.mail.views.mail_config_detail import MailConfigDetailView
from finlo.contrib.mail.views.mail_history import (
    MailHistoryView,
    MailHistoryNavbar,
    MailHistoryListView,
)
from finlo.contrib.mail.views.inbox import (
    InboxView,
    InboxNavbar,
    InboxListView,
    InboxRunActionView,
    InboxPreviewView,
    InboxDeleteView,
)

__all__ = [
    # Mail template views
    "MailTemplateView",
    "MailTemplateNavbar",
    "MailTemplateListView",
    "MailTemplateCreateUpdateView",
    "MailTemplatePreviewView",
    "TemplateContentView",
    "MailTemplateSelectView",
    "SaveAsMailTemplateView",
    "MailTemplateDeleteView",
    "MailTemplateDetailView",
    # Outlook views
    "OutlookMailServerFormView",
    "OutlookLoginView",
    "OutlookCallbackView",
    "refresh_outlook_token",
    "OutlookRefreshTokenView",
    "MailDisplayNameFieldView",
    # Incoming mail server views
    "IncomingMailServerView",
    "IncomingMailServerNavbar",
    "IncomingMailServerTypeSelectionView",
    "IncomingMailServerListView",
    "IncomingMailServerFormView",
    # Outgoing mail views
    "MailServerView",
    "MailServerNavbar",
    "MailServerTypeSelectionView",
    "MailServerListView",
    "OutgoingMailServerFormView",
    "MailServerTestEmailView",
    "MailServerDeleteView",
    # Mail config detail view
    "MailConfigDetailView",
    # Mail history views
    "MailHistoryView",
    "MailHistoryNavbar",
    "MailHistoryListView",
    # Inbox views
    "InboxView",
    "InboxNavbar",
    "InboxListView",
    "InboxRunActionView",
    "InboxPreviewView",
    "InboxDeleteView",
]
