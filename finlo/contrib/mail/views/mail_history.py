"""
Mail History Views
"""

# Standard library imports
from functools import cached_property

# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin

from finlo.contrib.generics.views import FinloListView, FinloNavView, FinloView

# First party imports (Finlo)
from finlo.urls import reverse_lazy
from finlo.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from finlo.utils.translation import gettext_lazy as _

# Local imports
from ..filters import FinloMailHistoryFilter
from ..models import FinloMail


@method_decorator(
    permission_required_or_denied(
        ["mail.view_finlomail"], wrapper_id="mail-history-view"
    ),
    name="dispatch",
)
class MailHistoryView(LoginRequiredMixin, FinloView):
    """
    Settings page for mail history.
    """

    template_name = "settings/settings_list_shell.html"
    view_id = "mail-history-view"
    nav_url = reverse_lazy("mail:mail_history_navbar_view")
    list_url = reverse_lazy("mail:mail_history_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["mail.view_finlomail"]),
    name="dispatch",
)
class MailHistoryNavbar(LoginRequiredMixin, FinloNavView):
    """
    Navbar for mail history.
    """

    nav_title = _("Outbox")
    nav_description = _("Review emails sent through Finlo.")
    search_url = reverse_lazy("mail:mail_history_list_view")
    main_url = reverse_lazy("mail:mail_history_view")
    nav_width = False
    all_view_types = False
    one_view_only = True
    filter_option = False
    reload_option = False
    border_enabled = False
    new_button = None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["mail.view_finlomail"]),
    name="dispatch",
)
class MailHistoryListView(LoginRequiredMixin, FinloListView):
    """
    List view of all sent mails.
    """

    model = FinloMail
    view_id = "mail-history-list"
    search_url = reverse_lazy("mail:mail_history_list_view")
    main_url = reverse_lazy("mail:mail_history_view")
    filterset_class = FinloMailHistoryFilter
    list_column_visibility = False
    bulk_export_option = False

    columns = [
        "to",
        "subject",
        "mail_status",
        "sender",
        "send_by",
        "sent_at",
    ]

    actions = [
        {
            "action": "Send Email",
            "src": "assets/icons/email_black.svg",
            "img_class": "w-4 h-4",
            "permission": "mail.add_finlomail",
            "hidden_if": lambda obj: obj.mail_status != "draft",
            "attrs": """
                hx-get="{get_edit_url}"
                hx-target="#finloModalBox"
                hx-swap="innerHTML"
                onclick="openfinloModal()"
            """,
        },
        {
            "action": "Cancel",
            "src": "assets/icons/cancel.svg",
            "img_class": "w-4 h-4",
            "permission": "mail.add_finlomail",
            "hidden_if": lambda obj: obj.mail_status != "scheduled",
            "attrs": """
                hx-get="{get_edit_url}?cancel=true"
                hx-target="#finloModalBox"
                hx-swap="innerHTML"
                hx-trigger="click"
                onclick="openfinloModal()"
            """,
        },
        {
            "action": "Snooze",
            "src": "assets/icons/clock.svg",
            "img_class": "w-4 h-4",
            "permission": "mail.add_finlomail",
            "hidden_if": lambda obj: obj.mail_status != "scheduled",
            "attrs": """
                hx-get="{get_reschedule_url}"
                hx-target="#modalBox"
                hx-swap="innerHTML"
                hx-trigger="click"
                onclick="openModal()"
            """,
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "mail.delete_finlomail",
            "attrs": """
                hx-post="{get_delete_url}?from=mail_history"
                hx-target="#modalBox"
                hx-swap="innerHTML"
                hx-trigger="click"
                hx-vals='{{"check_dependencies": "false"}}'
                onclick="openModal()"
            """,
        },
    ]

    @cached_property
    def col_attrs(self):
        """Open snapshot on subject click for non-draft mails."""
        if self.request.user.has_perm("mail.view_finlomail"):
            return [
                {
                    "subject": {
                        "hx-get": "{get_view_url}",
                        "hx-target": "#contentModalBox",
                        "hx-swap": "innerHTML",
                        "hx-push-url": "false",
                        "hx-on:click": "openContentModal();",
                        "style": "cursor:pointer",
                        "class": "hover:text-primary-600",
                    }
                }
            ]
        return []

    def get_queryset(self):
        return super().get_queryset().order_by("-sent_at", "-created_at")
