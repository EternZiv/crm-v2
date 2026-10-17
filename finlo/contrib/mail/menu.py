"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Finlo Core app.
"""

from finlo.menu import settings_menu

# First party imports (Finlo)
from finlo.urls import reverse_lazy
from finlo.utils.translation import gettext_lazy as _


@settings_menu.register
class MailSettings:
    """Settings menu entries for the Mail module."""

    title = _("Mail")
    icon = "/assets/icons/email-orange.svg"
    order = 3
    items = [
        {
            "label": _("Outgoing Mail Server"),
            "url": reverse_lazy("mail:mail_server_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#mail-server-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "mail.view_finlomailconfiguration",
        },
        {
            "label": _("Incoming Mail Server"),
            "url": reverse_lazy("mail:incoming_mail_server_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#mail-server-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "mail.view_finlomailconfiguration",
        },
        {
            "label": _("Mail Template"),
            "url": reverse_lazy("mail:mail_template_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#mail-template-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "mail.view_finlomailtemplate",
        },
        {
            "label": _("Outbox"),
            "url": reverse_lazy("mail:mail_history_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#mail-history-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "mail.view_finlomail",
        },
        {
            "label": _("Inbox"),
            "url": reverse_lazy("mail:inbox_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#inbox-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "mail.view_incomingmail",
        },
    ]
