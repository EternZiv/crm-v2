"""HTML administration pages for FINLONEXA sales hierarchy records."""

from horilla.contrib.generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla.contrib.core.forms.sales_hierarchy import (
    SalesAssignmentForm,
    SalesRegionForm,
    SalesTeamForm,
)
from horilla.contrib.core.models import SalesAssignment, SalesRegion, SalesTeam
from horilla.db import transaction
from horilla.urls import reverse_lazy
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required,
    permission_required_or_denied,
)
from horilla.utils.functional import cached_property
from horilla.utils.translation import gettext_lazy as _
from horilla.web import HxTriggerResponse
from django.contrib.auth.mixins import LoginRequiredMixin


class _SalesHierarchyHome(LoginRequiredMixin, HorillaView):
    template_name = "settings/settings_list_shell.html"
    nav_url = None
    list_url = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view_id"] = self.view_id
        context["nav_url"] = self.nav_url
        context["list_url"] = self.list_url
        return context


class _SalesHierarchyNavbar(LoginRequiredMixin, HorillaNavView):
    filterset_class = None
    one_view_only = True
    all_view_types = False
    reload_option = False
    nav_width = False

    @cached_property
    def new_button(self):
        if self.request.user.has_perm(f"core.add_{self.model._meta.model_name}"):
            return {
                "url": f"{self.create_url}?new=true",
                "attrs": {"id": f"{self.model._meta.model_name}-create"},
            }
        return None


class _SalesHierarchyList(LoginRequiredMixin, HorillaListView):
    filterset_class = None
    bulk_update_option = False
    bulk_delete_enabled = False

    @cached_property
    def no_record_add_button(self):
        if self.request.user.has_perm(f"core.add_{self.model._meta.model_name}"):
            return {
                "url": f"{self.create_url}?new=true",
                "attrs": f'id="{self.model._meta.model_name}-create"',
            }
        return None


class _SalesHierarchyForm(LoginRequiredMixin, HorillaSingleFormView):
    modal_height = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            return super().form_valid(form)


@method_decorator(
    permission_required_or_denied("core.view_salesregion", wrapper_id="sales-regions"),
    name="dispatch",
)
class SalesRegionView(_SalesHierarchyHome):
    view_id = "sales-regions"
    nav_url = reverse_lazy("core:sales_region_nav")
    list_url = reverse_lazy("core:sales_region_list")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("core.view_salesregion"), name="dispatch")
class SalesRegionNavbar(_SalesHierarchyNavbar):
    model = SalesRegion
    nav_description = _("Manage geographic sales regions.")
    search_url = reverse_lazy("core:sales_region_list")
    main_url = reverse_lazy("core:sales_region_view")
    create_url = reverse_lazy("core:sales_region_create")
    url_name = "sales_region_list"
    model_name = "SalesRegion"
    model_app_label = "core"


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("core.view_salesregion"), name="dispatch")
class SalesRegionList(_SalesHierarchyList):
    model = SalesRegion
    view_id = "sales-region-list"
    search_url = reverse_lazy("core:sales_region_list")
    main_url = reverse_lazy("core:sales_region_view")
    create_url = reverse_lazy("core:sales_region_create")
    columns = ["name", "code", "description"]
    actions = [
        {
            "action": "Edit",
            "src": "assets/icons/edit.svg",
            "img_class": "w-4 h-4",
            "permission": "core.change_salesregion",
            "attrs": 'hx-get="{get_edit_url}?new=true" hx-target="#modalBox" hx-swap="innerHTML" onclick="openModal()"',
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "core.delete_salesregion",
            "attrs": 'hx-post="{get_delete_url}" hx-target="#deleteModeBox" hx-swap="innerHTML" onclick="openDeleteModeModal()"',
        },
    ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("core.add_salesregion"), name="dispatch")
class SalesRegionFormView(_SalesHierarchyForm):
    model = SalesRegion
    form_class = SalesRegionForm
    fields = ["company", "name", "code", "description"]
    full_width_fields = ["company", "name", "code", "description"]
    form_title = _("Sales Region")

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        return (
            reverse_lazy("core:sales_region_update", kwargs={"pk": pk})
            if pk
            else reverse_lazy("core:sales_region_create")
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("core.delete_salesregion", modal=True), name="dispatch")
class SalesRegionDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = SalesRegion

    def get_post_delete_response(self):
        return HxTriggerResponse()


@method_decorator(
    permission_required_or_denied("core.view_salesteam", wrapper_id="sales-teams"),
    name="dispatch",
)
class SalesTeamView(_SalesHierarchyHome):
    view_id = "sales-teams"
    nav_url = reverse_lazy("core:sales_team_nav")
    list_url = reverse_lazy("core:sales_team_list")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("core.view_salesteam"), name="dispatch")
class SalesTeamNavbar(_SalesHierarchyNavbar):
    model = SalesTeam
    nav_description = _("Manage teams within each sales region.")
    search_url = reverse_lazy("core:sales_team_list")
    main_url = reverse_lazy("core:sales_team_view")
    create_url = reverse_lazy("core:sales_team_create")
    url_name = "sales_team_list"
    model_name = "SalesTeam"
    model_app_label = "core"


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("core.view_salesteam"), name="dispatch")
class SalesTeamList(_SalesHierarchyList):
    model = SalesTeam
    view_id = "sales-team-list"
    search_url = reverse_lazy("core:sales_team_list")
    main_url = reverse_lazy("core:sales_team_view")
    create_url = reverse_lazy("core:sales_team_create")
    columns = ["name", "code", "region", "senior_sales_manager", "area_sales_manager"]
    actions = [
        {
            "action": "Edit",
            "src": "assets/icons/edit.svg",
            "img_class": "w-4 h-4",
            "permission": "core.change_salesteam",
            "attrs": 'hx-get="{get_edit_url}?new=true" hx-target="#modalBox" hx-swap="innerHTML" onclick="openModal()"',
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "core.delete_salesteam",
            "attrs": 'hx-post="{get_delete_url}" hx-target="#deleteModeBox" hx-swap="innerHTML" onclick="openDeleteModeModal()"',
        },
    ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("core.add_salesteam"), name="dispatch")
class SalesTeamFormView(_SalesHierarchyForm):
    model = SalesTeam
    form_class = SalesTeamForm
    fields = [
        "company",
        "name",
        "code",
        "region",
        "senior_sales_manager",
        "area_sales_manager",
    ]
    full_width_fields = fields
    form_title = _("Sales Team")

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        return (
            reverse_lazy("core:sales_team_update", kwargs={"pk": pk})
            if pk
            else reverse_lazy("core:sales_team_create")
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("core.delete_salesteam", modal=True), name="dispatch")
class SalesTeamDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = SalesTeam

    def get_post_delete_response(self):
        return HxTriggerResponse()


@method_decorator(
    permission_required_or_denied("core.view_salesassignment", wrapper_id="sales-assignments"),
    name="dispatch",
)
class SalesAssignmentView(_SalesHierarchyHome):
    view_id = "sales-assignments"
    nav_url = reverse_lazy("core:sales_assignment_nav")
    list_url = reverse_lazy("core:sales_assignment_list")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("core.view_salesassignment"), name="dispatch")
class SalesAssignmentNavbar(_SalesHierarchyNavbar):
    model = SalesAssignment
    nav_description = _("Manage sales employees, reporting relationships and transfers.")
    search_url = reverse_lazy("core:sales_assignment_list")
    main_url = reverse_lazy("core:sales_assignment_view")
    create_url = reverse_lazy("core:sales_assignment_create")
    url_name = "sales_assignment_list"
    model_name = "SalesAssignment"
    model_app_label = "core"


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("core.view_salesassignment"), name="dispatch")
class SalesAssignmentList(_SalesHierarchyList):
    model = SalesAssignment
    view_id = "sales-assignment-list"
    search_url = reverse_lazy("core:sales_assignment_list")
    main_url = reverse_lazy("core:sales_assignment_view")
    create_url = reverse_lazy("core:sales_assignment_create")
    columns = ["user", "region", "team", "manager", "is_active"]
    actions = [
        {
            "action": "Edit",
            "src": "assets/icons/edit.svg",
            "img_class": "w-4 h-4",
            "permission": "core.change_salesassignment",
            "attrs": 'hx-get="{get_edit_url}?new=true" hx-target="#modalBox" hx-swap="innerHTML" onclick="openModal()"',
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "core.delete_salesassignment",
            "attrs": 'hx-post="{get_delete_url}" hx-target="#deleteModeBox" hx-swap="innerHTML" onclick="openDeleteModeModal()"',
        },
    ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("core.add_salesassignment"), name="dispatch")
class SalesAssignmentFormView(_SalesHierarchyForm):
    model = SalesAssignment
    form_class = SalesAssignmentForm
    fields = ["company", "user", "region", "team", "manager", "is_active"]
    full_width_fields = fields
    form_title = _("Sales Assignment")

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        return (
            reverse_lazy("core:sales_assignment_update", kwargs={"pk": pk})
            if pk
            else reverse_lazy("core:sales_assignment_create")
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied("core.delete_salesassignment", modal=True), name="dispatch")
class SalesAssignmentDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = SalesAssignment

    def get_post_delete_response(self):
        return HxTriggerResponse()
