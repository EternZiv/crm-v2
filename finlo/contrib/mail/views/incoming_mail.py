"""
mail incoming mail views.
"""

# Standard library imports
from functools import cached_property

# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin

from finlo.contrib.generics.views import (
    FinloListView,
    FinloNavView,
    FinloSingleFormView,
    FinloView,
)

# First party imports (Finlo)
from finlo.urls import reverse_lazy
from finlo.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from finlo.utils.translation import gettext_lazy as _
from finlo.views.generic import TemplateView
from finlo.web import ScriptResponse

# Local imports
from ..filters import FinloMailServerFilter
from ..forms import IncomingFinloMailConfigurationForm
from ..models import FinloMailConfiguration


@method_decorator(
    permission_required_or_denied(
        ["mail.view_finlomailconfiguration"], wrapper_id="mail-server-view"
    ),
    name="dispatch",
)
class IncomingMailServerView(LoginRequiredMixin, FinloView):
    """
    TemplateView for mail server page.
    """

    template_name = "settings/settings_list_shell.html"
    view_id = "mail-server-view"
    nav_url = reverse_lazy("mail:incoming_mail_server_navbar_view")
    list_url = reverse_lazy("mail:incoming_mail_server_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["mail.view_finlomailconfiguration"]),
    name="dispatch",
)
class IncomingMailServerNavbar(LoginRequiredMixin, FinloNavView):
    """
    navbar view for mail server
    """

    nav_title = _("Incoming Mail Configurations")
    nav_description = _("Configure the IMAP server used to receive incoming emails.")
    search_url = reverse_lazy("mail:incoming_mail_server_list_view")
    main_url = reverse_lazy("mail:incoming_mail_server_view")
    nav_width = False
    all_view_types = False
    filter_option = False
    reload_option = False
    one_view_only = True
    border_enabled = False

    @cached_property
    def new_button(self):
        """New button configuration for the navbar."""
        if self.request.user.has_perm("mail.create_finloemailconfiguration"):
            return {
                "url": f"""{reverse_lazy("mail:incoming_mail_server_type_selection")}?new=true""",
                "attrs": {"id": "mail-server-create"},
                "onclick": "openfinloModal()",
                "target": "#finloModalBox",
            }
        return None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["mail.view_finlomailconfiguration"]),
    name="dispatch",
)
class IncomingMailServerTypeSelectionView(LoginRequiredMixin, TemplateView):
    """
    View to show mail server type selection options
    """

    template_name = "incoming/incoming_mail_server_type_selection.html"


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["mail.view_finlomailconfiguration"]),
    name="dispatch",
)
class IncomingMailServerListView(LoginRequiredMixin, FinloListView):
    """
    List view of mail server
    """

    model = FinloMailConfiguration
    view_id = "mail-server-list"
    search_url = reverse_lazy("mail:incoming_mail_server_list_view")
    main_url = reverse_lazy("mail:incoming_mail_server_view")
    filterset_class = FinloMailServerFilter
    bulk_update_two_column = True
    bulk_delete_enabled = False
    bulk_select_option = False
    list_column_visibility = False
    action_method = "custom_actions"
    store_ordered_ids = True

    @cached_property
    def no_record_add_button(self):
        """
        Get the configuration for the "Add" button when no record exist.
        """
        if self.request.user.has_perm("mail.create_finloemailconfiguration"):
            return {
                "url": f"""{reverse_lazy("mail:incoming_mail_server_type_selection")}?new=true""",
                "attrs": 'id="mail-server-create"',
                "onclick": "openfinloModal()",
                "target": "#finloModalBox",
            }
        return None

    columns = ["username", "type"]

    @cached_property
    def col_attrs(self):
        """Open the detail modal when clicking the username column."""
        query_string = self.request.session.get(self.ordered_ids_key, [])
        attrs = {}
        if self.request.user.has_perm("mail.view_finlomailconfiguration"):
            attrs = {
                "hx-get": f"{{get_detail_url}}?instance_ids={query_string}",
                "hx-target": "#detailModalBox",
                "hx-swap": "innerHTML",
                "hx-push-url": "false",
                "hx-on:click": "openDetailModal();",
                "style": "cursor:pointer",
                "class": "hover:text-primary-600",
            }
        return [{"username": {**attrs}}]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(mail_channel="incoming")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "mail.view_finlomailconfiguration",
            "mail.add_finlomailconfiguration",
        ]
    ),
    name="dispatch",
)
class IncomingMailServerFormView(LoginRequiredMixin, FinloSingleFormView):
    """
    create and update from view for mail server
    """

    model = FinloMailConfiguration
    form_class = IncomingFinloMailConfigurationForm
    modal_height = False
    hidden_fields = ["company", "type", "mail_channel"]
    save_and_new = False

    def get_initial(self):
        """Set initial form data for incoming mail configuration (IMAP defaults)."""
        initial = super().get_initial()
        pk = self.kwargs.get("pk")
        company = getattr(self.request, "active_company", None)
        if not pk:
            initial["company"] = company
            initial["type"] = "mail"
            initial["host"] = "imap.gmail.com"
            initial["port"] = 993
            initial["mail_channel"] = "incoming"
        return initial

    @cached_property
    def form_url(self):
        """Get the URL for the form view."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "mail:incoming_mail_server_update_view", kwargs={"pk": pk}
            )
        return reverse_lazy("mail:incoming_mail_server_form_view")

    def form_valid(self, form):
        super().form_valid(form)
        return ScriptResponse(reload=True, close=True, extra="closefinloModal();")
