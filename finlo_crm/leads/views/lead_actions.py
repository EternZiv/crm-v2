"""Lead Actions Views for Finlo CRM"""

# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin

from finlo.contrib.generics.views import (
    FinloMultiStepFormView,
    FinloSingleDeleteView,
    FinloSingleFormView,
)
from finlo.db import transaction
from finlo.urls import reverse_lazy
from finlo.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from finlo.utils.functional import cached_property
from finlo.utils.translation import gettext_lazy as _
from finlo.core.exceptions import PermissionDenied

# First party imports (Finlo)
from finlo.web import HxTriggerResponse

# Local imports
from finlo_crm.leads.authorization import assign_lead_to_bdo
from finlo_crm.leads.forms import LeadFormClass, LeadSingleForm, LeadSubOwnerForm
from finlo_crm.leads.models import Lead, LeadStatus


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.delete_lead", modal=True), name="dispatch"
)
class LeadDeleteView(LoginRequiredMixin, FinloSingleDeleteView):
    """Lead Delete View"""

    model = Lead

    def get_post_delete_response(self):
        return HxTriggerResponse()


@method_decorator(htmx_required, name="dispatch")
# Keeps instance.save() and form.save_m2m() (which persists custom field
# values) in one transaction, so the post_save assignment-rule signal's
# on_commit callback fires only after custom fields are readable.
@method_decorator(transaction.atomic, name="form_valid")
class LeadFormView(LoginRequiredMixin, FinloMultiStepFormView):
    """Lead Create/Update View"""

    form_class = LeadFormClass
    model = Lead
    fullwidth_fields = ["requirements"]
    dynamic_create_fields = ["lead_status"]
    detail_url_name = "leads:leads_detail"
    dynamic_create_field_mapping = {
        "lead_status": {
            "fields": ["name", "order", "color", "probability"],
            "initial": {
                "order": LeadStatus.get_next_order_for_company,
            },
        },
    }

    form_mode = [
        {
            "title": _("Single-Step Form"),
            "url_name": {
                "create": "leads:leads_create_single",
                "edit": "leads:leads_edit_single",
            },
            "active": False,
        },
        {
            "title": _("Multi-Step Form"),
            "url_name": {"create": "leads:leads_create", "edit": "leads:leads_edit"},
            "active": True,
        },
    ]

    @cached_property
    def form_url(self):
        """Form URL for lead"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("leads:leads_edit", kwargs={"pk": pk})
        return reverse_lazy("leads:leads_create")

    step_titles = {
        "1": _("Basic Information"),
        "2": _("Company Details"),
        "3": _("Location"),
        "4": _("Requirements"),
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


@method_decorator(htmx_required, name="dispatch")
# See LeadFormView above: keeps custom field persistence and the
# assignment-rule signal in the same transaction.
@method_decorator(transaction.atomic, name="form_valid")
class LeadsSingleFormView(LoginRequiredMixin, FinloSingleFormView):
    """Lead Create/Update Single Page View"""

    model = Lead
    form_class = LeadSingleForm
    full_width_fields = ["requirements"]
    dynamic_create_fields = ["lead_status"]
    dynamic_create_field_mapping = {
        "lead_status": {
            "fields": ["name", "order", "color", "probability", "is_final"],
            "initial": {
                "order": LeadStatus.get_next_order_for_company,
            },
        },
    }

    detail_url_name = "leads:leads_detail"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    form_mode = [
        {
            "title": _("Single-Step Form"),
            "url_name": {
                "create": "leads:leads_create_single",
                "edit": "leads:leads_edit_single",
            },
            "active": True,
        },
        {
            "title": _("Multi-Step Form"),
            "url_name": {"create": "leads:leads_create", "edit": "leads:leads_edit"},
            "active": False,
        },
    ]

    @cached_property
    def form_url(self):
        """Form URL for lead"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("leads:leads_edit_single", kwargs={"pk": pk})
        return reverse_lazy("leads:leads_create_single")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("leads.change_lead"), name="dispatch"
)
class LeadChangeOwnerForm(LoginRequiredMixin, FinloSingleFormView):
    """
    Assign a lead to a BDO without changing its original owner.
    """

    model = Lead
    form_class = LeadSubOwnerForm
    full_width_fields = ["sub_owner"]
    modal_height = False
    form_title = _("Assign BDO")

    @cached_property
    def form_url(self):
        """Form URL for lead change owner"""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("leads:lead_change_owner", kwargs={"pk": pk})
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        """Apply the explicit ASM-to-BDO policy before persisting the form."""
        try:
            assign_lead_to_bdo(
                form.instance, self.request.user, form.cleaned_data["sub_owner"]
            )
        except PermissionDenied as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        return super().form_valid(form)
