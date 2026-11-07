"""Forms for Lead model and Lead conversion process."""

# Standard library imports
import logging

# Third-party imports (Django)
from django import forms

# First party imports (Finlo)
from finlo.auth.models import User
from finlo.contrib.core.mixins import OwnerQuerysetMixin
from finlo.contrib.generics.forms import FinloModelForm, FinloMultiStepForm
from finlo.contrib.mail.models import FinloMailConfiguration, FinloMailTemplate
from finlo.contrib.notifications.models import NotificationTemplate
from finlo.core.exceptions import ValidationError
from finlo.db.models import Q
from finlo.urls import reverse, reverse_lazy
from finlo.utils.choices import get_subdivision_choices, resolve_subdivision_choice
from finlo.utils.translation import gettext_lazy as _

# Local imports
from finlo_crm.accounts.models import Account
from finlo_crm.contacts.models import Contact
from finlo_crm.opportunities.models import Opportunity

from .models import (
    EmailToLeadConfig,
    Lead,
    LeadAssignmentCondition,
    LeadAssignmentMatchCriteria,
    LeadStatus,
)

logger = logging.getLogger(__name__)


class LeadFormClass(OwnerQuerysetMixin, FinloMultiStepForm):
    """Form class for Lead model"""

    class Meta:
        """Meta class for LeadFormClass"""

        model = Lead
        fields = "__all__"
        exclude = ["lead_score", "sub_owner"]

    step_fields = {
        1: [
            "lead_owner",
            "title",
            "first_name",
            "last_name",
            "email",
            "contact_number",
            "fax",
            "lead_source",
            "lead_status",
        ],
        2: ["lead_company", "no_of_employees", "industry", "annual_revenue"],
        3: ["country", "state", "city", "zip_code"],
        4: ["requirements"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock_lead_owner()
        self.fields["lead_status"].queryset = LeadStatus.objects.filter(is_final=False)
        self.fields["country"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("core:get_country_subdivisions"),
                "hx-target": "#id_state",
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
            }
        )
        self.fields["state"] = forms.ChoiceField(
            choices=[],
            required=False,
            widget=forms.Select(
                attrs={"id": "id_state", "class": "js-example-basic-single headselect"}
            ),
        )

        if "country" in self.data:
            country_code = self.data.get("country")
            self.fields["state"].choices = get_subdivision_choices(country_code)
        elif self.instance.pk and self.instance.country:
            self.fields["state"].choices = get_subdivision_choices(
                self.instance.country.code
            )
            self.fields["state"].initial = resolve_subdivision_choice(
                self.fields["state"].choices, self.instance.state
            )
        if "no_of_employees" in self.fields:
            self.fields["no_of_employees"].widget.attrs.setdefault("min", "0")

    def clean_no_of_employees(self):
        val = self.cleaned_data.get("no_of_employees")
        if val is not None and val < 0:
            raise ValidationError(_("Total Employees must be greater than or equal to 0."))
        return val

    def _lock_lead_owner(self):
        owner_field = self.fields.get("lead_owner")
        if owner_field is None:
            return
        owner_field.disabled = True
        owner_field.initial = (
            self.instance.lead_owner
            if self.instance.pk
            else getattr(self.request, "user", None)
        )


class LeadSingleForm(OwnerQuerysetMixin, FinloModelForm):
    """
    Custom form for Lead to add HTMX attributes
    Inherits from FinloModelForm to preserve all existing behavior.
    """

    field_order = [
        "lead_owner",
        "title",
        "first_name",
        "last_name",
        "email",
        "contact_number",
        "lead_source",
        "lead_status",
        "lead_company",
        "no_of_employees",
        "industry",
        "annual_revenue",
        "country",
        "state",
        "city",
        "zip_code",
        "fax",
        "requirements",
    ]

    class Meta:
        """Meta class for LeadStatusForm"""

        model = Lead
        fields = "__all__"
        exclude = ["lead_score", "sub_owner"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        owner_field = self.fields.get("lead_owner")
        if owner_field is not None:
            owner_field.disabled = True
            owner_field.initial = (
                self.instance.lead_owner
                if self.instance.pk
                else getattr(self.request, "user", None)
            )
        self.fields["lead_status"].queryset = LeadStatus.objects.filter(is_final=False)
        self.fields["country"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("core:get_country_subdivisions"),
                "hx-target": "#id_state",
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
            }
        )
        self.fields["state"] = forms.ChoiceField(
            choices=[],
            required=False,
            widget=forms.Select(
                attrs={"id": "id_state", "class": "js-example-basic-single headselect"}
            ),
        )

        if "country" in self.data:
            country_code = self.data.get("country")
            self.fields["state"].choices = get_subdivision_choices(country_code)
        elif self.instance.pk and self.instance.country:
            self.fields["state"].choices = get_subdivision_choices(
                self.instance.country.code
            )
            self.fields["state"].initial = resolve_subdivision_choice(
                self.fields["state"].choices, self.instance.state
            )
        if "no_of_employees" in self.fields:
            self.fields["no_of_employees"].widget.attrs.setdefault("min", "0")

    def clean_no_of_employees(self):
        val = self.cleaned_data.get("no_of_employees")
        if val is not None and val < 0:
            raise ValidationError(_("Total Employees must be greater than or equal to 0."))
        return val


class LeadSubOwnerForm(FinloModelForm):
    """Select active BDO reports for a lead assignment."""

    class Meta:
        model = Lead
        fields = ["sub_owner"]

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if request is None or not request.user.is_authenticated:
            self.fields["sub_owner"].queryset = User.objects.none()
            return
        user = request.user
        is_super = (
            getattr(user, "is_superuser", False)
            or getattr(getattr(user, "role", None), "name", None) == "Super Admin"
            or getattr(getattr(user, "role", None), "system_key", None) != "ASM"
        )
        if is_super:
            self.fields["sub_owner"].queryset = User.objects.filter(
                is_active=True,
                company_id=user.company_id,
                role__system_key="BDO",
                sales_assignment__is_active=True,
            )
        else:
            self.fields["sub_owner"].queryset = User.objects.filter(
                is_active=True,
                company_id=user.company_id,
                role__system_key="BDO",
                sales_assignment__is_active=True,
                sales_assignment__manager_id=user.pk,
                sales_assignment__team__area_sales_manager_id=user.pk,
            )
        self.fields["sub_owner"].required = True


class LeadConversionForm(forms.Form):
    """Form for converting a Lead into Account, Contact, and Opportunity"""

    # Account fields
    account_action = forms.ChoiceField(
        choices=[("create_new", "Create New"), ("select_existing", "Select Existing")],
        widget=forms.RadioSelect(
            attrs={
                "class": "border border-[#cbcbcb] w-3 h-3 text-[#e54f38] bg-white focus:ring-[#e54f38] cursor-pointer"
            }
        ),
        initial="create_new",
    )
    account_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs  w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": _("Enter Account Name"),
            }
        ),
    )
    existing_account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        required=False,
        empty_label=_("Select Account"),
        widget=forms.Select(
            attrs={
                "class": "select2-pagination w-full text-sm",
                "hx-get": "",  # Will be set dynamically
                "hx-target": "#opportunity-field",
                "hx-swap": "innerHTML",
                "hx-trigger": "change",
            }
        ),
    )

    # Contact fields
    contact_action = forms.ChoiceField(
        choices=[("create_new", "Create New"), ("select_existing", "Select Existing")],
        widget=forms.RadioSelect(
            attrs={
                "class": "border border-[#cbcbcb] w-3 h-3 text-[#e54f38] bg-white focus:ring-[#e54f38] cursor-pointer"
            }
        ),
        initial="create_new",
    )
    first_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": _("Enter First Name"),
            }
        ),
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": _("Enter Last Name"),
            }
        ),
    )
    existing_contact = forms.ModelChoiceField(
        queryset=Contact.objects.all(),
        required=False,
        empty_label=_("Select Contact"),
        widget=forms.Select(attrs={"class": "normal-seclect"}),
    )

    # Opportunity fields
    opportunity_action = forms.ChoiceField(
        choices=[("create_new", "Create New"), ("select_existing", "Select Existing")],
        widget=forms.RadioSelect(
            attrs={
                "class": "border border-[#cbcbcb] w-3 h-3 text-[#e54f38] bg-white focus:ring-[#e54f38] cursor-pointer"
            }
        ),
        initial="create_new",
    )
    opportunity_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": _("Enter Opportunity Name"),
            }
        ),
    )
    existing_opportunity = forms.ModelChoiceField(
        queryset=Opportunity.objects.none(),  # Start with empty queryset
        required=False,
        empty_label=_("Select Opportunity"),
        widget=forms.Select(attrs={"class": "normal-seclect"}),
    )

    # Owner field
    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=True,
        empty_label=_("Select Owner"),
        widget=forms.Select(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600"
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.lead = kwargs.pop("lead", None)
        self.selected_account = kwargs.pop("selected_account", None)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        req = self.request
        if not req:
            from finlo.contrib.utils.middlewares import get_current_request

            req = get_current_request()
        user = getattr(req, "user", None) if req else None
        company = getattr(req, "active_company", None) or (
            self.lead and getattr(self.lead, "company", None)
        )

        from finlo.contrib.core.sales_authorization import (
            _role_key,
            scope_queryset_to_sales_hierarchy,
        )

        acc_qs = Account.objects.all()
        cnt_qs = Contact.objects.all()
        usr_qs = User.objects.filter(is_active=True)
        if company:
            acc_qs = acc_qs.filter(company=company)
            cnt_qs = cnt_qs.filter(company=company)
            usr_qs = usr_qs.filter(company=company)

        if user and not getattr(user, "is_superuser", False):
            acc_qs = scope_queryset_to_sales_hierarchy(acc_qs, user)
            cnt_qs = scope_queryset_to_sales_hierarchy(cnt_qs, user)
            usr_qs = scope_queryset_to_sales_hierarchy(usr_qs, user)

        self.fields["existing_account"].queryset = acc_qs
        self.fields["existing_contact"].queryset = cnt_qs
        self.fields["owner"].queryset = usr_qs

        if self.lead:
            # Pre-populate fields with lead data
            self.fields["account_name"].initial = self.lead.lead_company
            self.fields["first_name"].initial = self.lead.first_name
            self.fields["last_name"].initial = self.lead.last_name
            self.fields["opportunity_name"].initial = (
                f"{self.lead.lead_company} - Opportunity"
            )
            self.fields["owner"].initial = self.lead.lead_owner

            # Set HTMX URL for account selection
            self.fields["existing_account"].widget.attrs["hx-get"] = reverse(
                "leads:convert_lead", kwargs={"pk": self.lead.pk}
            )

        # Filter opportunities based on selected account
        if self.selected_account:
            opp_qs = Opportunity.objects.filter(account=self.selected_account)
            if company:
                opp_qs = opp_qs.filter(company=company)
            if user and not getattr(user, "is_superuser", False):
                opp_qs = scope_queryset_to_sales_hierarchy(opp_qs, user)
            self.fields["existing_opportunity"].queryset = opp_qs
        else:
            self.fields["existing_opportunity"].queryset = Opportunity.objects.none()

    def clean(self):
        """Validate account, contact, and opportunity selections for conversion."""
        cleaned_data = super().clean()

        # Validate account
        account_action = cleaned_data.get("account_action")
        if account_action == "create_new":
            if not cleaned_data.get("account_name"):
                self.add_error(
                    "account_name",
                    _("Account name is required when creating new account."),
                )
        elif account_action == "select_existing":
            if not cleaned_data.get("existing_account"):
                self.add_error(
                    "existing_account", _("Please select an existing account.")
                )

        # Validate contact
        contact_action = cleaned_data.get("contact_action")
        if contact_action == "create_new":
            if not cleaned_data.get("first_name"):
                self.add_error(
                    "first_name", _("First name is required when creating new contact.")
                )
            if not cleaned_data.get("last_name"):
                self.add_error(
                    "last_name", _("Last name is required when creating new contact.")
                )
        elif contact_action == "select_existing":
            if not cleaned_data.get("existing_contact"):
                self.add_error(
                    "existing_contact", _("Please select an existing contact.")
                )

        # Validate opportunity
        opportunity_action = cleaned_data.get("opportunity_action")
        if opportunity_action == "create_new":
            if not cleaned_data.get("opportunity_name"):
                self.add_error(
                    "opportunity_name",
                    _("Opportunity name is required when creating new opportunity."),
                )
        elif opportunity_action == "select_existing":
            if not cleaned_data.get("existing_opportunity"):
                self.add_error(
                    "existing_opportunity", _("Please select an existing opportunity.")
                )

        req = self.request
        if not req:
            from finlo.contrib.utils.middlewares import get_current_request

            req = get_current_request()
        user = getattr(req, "user", None) if req else None

        if user and not getattr(user, "is_superuser", False):
            from finlo.contrib.core.sales_authorization import (
                _role_key,
                can_access_sales_record,
            )

            role_key = _role_key(user)
            if account_action == "select_existing":
                acc = cleaned_data.get("existing_account")
                if acc and not can_access_sales_record(user, acc):
                    self.add_error(
                        "existing_account",
                        _("You do not have permission to link this account."),
                    )

            if contact_action == "select_existing":
                cnt = cleaned_data.get("existing_contact")
                if cnt and not can_access_sales_record(user, cnt):
                    self.add_error(
                        "existing_contact",
                        _("You do not have permission to link this contact."),
                    )

            if opportunity_action == "select_existing":
                opp = cleaned_data.get("existing_opportunity")
                if opp and not can_access_sales_record(user, opp):
                    self.add_error(
                        "existing_opportunity",
                        _("You do not have permission to link this opportunity."),
                    )

            owner = cleaned_data.get("owner")
            if owner:
                if role_key == "BDO" and owner != user:
                    self.add_error(
                        "owner",
                        _("BDO can only assign converted records to themselves."),
                    )
                elif not can_access_sales_record(user, owner):
                    self.add_error(
                        "owner",
                        _("You do not have permission to assign to this owner."),
                    )

        return cleaned_data


class LeadStatusForm(FinloModelForm):
    """
    Custom form for LeadStatus to add HTMX attributes to is_final field.
    Inherits from FinloModelForm to preserve all existing behavior.
    """

    field_order = ["name", "probability", "order", "is_final"]

    class Meta:
        """Meta class for LeadStatusForm"""

        model = LeadStatus
        fields = "__all__"
        exclude = ["color"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add HTMX attributes to is_final field to toggle order field visibility
        if "is_final" in self.fields:
            self.fields["is_final"].widget.attrs.update(
                {
                    "hx-post": reverse_lazy("leads:toggle_order_field"),
                    "hx-target": "#order_container",
                    "hx-swap": "outerHTML",
                    "hx-trigger": "change",
                }
            )
        if "order" in self.fields:
            # The order field is hidden client-side when "is_final" is checked,
            # so it may be submitted blank. LeadStatus.save() auto-assigns the
            # next available order when left unset.
            self.fields["order"].required = False


class EmailToLeadForm(FinloModelForm):
    """
    Inherits from FinloModelForm to preserve all existing behavior.
    """

    field_order = [
        "mail",
        "create_as",
        "lead_owner",
        "accept_emails_from",
        "keywords",
    ]

    class Meta:
        """Meta class for LeadStatusForm"""

        model = EmailToLeadConfig
        fields = "__all__"
        exclude = ["last_fetched"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mail"].queryset = FinloMailConfiguration.objects.filter(
            mail_channel="incoming", is_active=True
        )


class AssignmentRuleConditionForm(FinloModelForm):
    """Form for creating and editing lead assignment rule conditions."""

    field_order = [
        "rule",
        "assign_to_type",
        "assign_to_users",
        "assign_to_roles",
        "notify_method",
        "mail_template",
        "notification_template",
    ]

    def __init__(self, *args, **kwargs):
        kwargs["condition_model"] = LeadAssignmentMatchCriteria
        super().__init__(*args, **kwargs)

        current_type = "user"
        if self.instance and self.instance.pk:
            current_type = self.instance.assign_to_type or "user"
        elif self.data.get("assign_to_type"):
            current_type = self.data["assign_to_type"]

        self.fields["assign_to_type"].widget.attrs.update(
            {
                "hx-post": reverse_lazy("leads:toggle_assign_to_field"),
                "hx-target": "#assign_to_users_container",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
            }
        )
        self.fields["assign_to_users"].widget.attrs["container_style"] = (
            "" if current_type == "user" else "display:none"
        )
        self.fields["assign_to_roles"].widget.attrs["container_style"] = (
            "" if current_type == "role" else "display:none"
        )

        # --- notify_method conditional fields ---
        current_notify = ""
        if self.instance and self.instance.pk:
            current_notify = self.instance.notify_method or ""
        elif self.data.get("notify_method"):
            current_notify = self.data["notify_method"]

        lead_template_qs = Q(content_type__isnull=True) | Q(
            content_type__app_label="leads", content_type__model="lead"
        )
        self.fields["mail_template"].queryset = FinloMailTemplate.objects.filter(
            lead_template_qs
        )
        self.fields["notification_template"].queryset = (
            NotificationTemplate.objects.filter(lead_template_qs)
        )

        self.fields["notify_method"].widget.attrs.update(
            {
                "hx-post": reverse_lazy("leads:toggle_notify_method_field"),
                "hx-target": "#mail_template_container",
                "hx-swap": "outerHTML",
                "hx-trigger": "change",
                "hx-include": "[name='mail_template'],[name='notification_template']",
            }
        )
        show_mail = current_notify in ("email", "both")
        show_notification = current_notify in ("notification", "both")
        self.fields["mail_template"].widget.attrs["container_style"] = (
            "" if show_mail else "display:none"
        )
        self.fields["notification_template"].widget.attrs["container_style"] = (
            "" if show_notification else "display:none"
        )

    def clean(self):
        cleaned_data = super().clean()
        condition_rows = self._extract_condition_rows()
        if not condition_rows:
            raise ValidationError("At least one matching criterion must be provided.")
        cleaned_data["condition_rows"] = condition_rows
        return cleaned_data

    class Meta:
        """
        Meta options for AssignmentRuleConditionForm. Specifies the model and fields to include in the form.
        """

        model = LeadAssignmentCondition
        fields = "__all__"
