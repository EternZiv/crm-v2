"""
Forms for the Contacts app.

Includes:
- Multi-step form for creating and updating contacts.
- Form for assigning child contacts while preventing circular references.
- Validation logic for parent-child relationships between contacts.
"""

# Third-party imports (Django)
from django import forms

from finlo.contrib.core.mixins import OwnerQuerysetMixin
from finlo.contrib.generics.forms import FinloModelForm, FinloMultiStepForm

# First party imports (Finlo)
from finlo.core.exceptions import ValidationError
from finlo.urls import reverse_lazy
from finlo.utils.choices import get_subdivision_choices, resolve_subdivision_choice
from finlo.utils.translation import gettext_lazy as _

# Local imports
from .models import Contact


# Define your contacts forms here
def _would_create_cycle(contact_instance, new_parent):
    """Return True if setting new_parent as the parent of contact_instance creates a cycle."""
    ancestor = new_parent
    while ancestor is not None:
        if ancestor.pk == contact_instance.pk:
            return True
        ancestor = ancestor.parent_contact
    return False


class ContactFormClass(OwnerQuerysetMixin, FinloMultiStepForm):
    """
    Form class for contact
    """

    class Meta:
        """Meta options for the Contact form."""

        model = Contact
        fields = "__all__"

    step_fields = {
        1: [
            "contact_owner",
            "title",
            "first_name",
            "last_name",
            "contact_number",
            "email",
            "secondary_contact_number",
            "birth_date",
            "assistant",
            "assistant_contact_number",
            "contact_source",
            "parent_contact",
            "is_primary",
        ],
        2: ["address_country", "address_state", "address_city", "address_zip"],
        3: ["languages", "description"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "is_primary" in self.fields:
            self.fields["is_primary"].required = False

        self.fields["address_country"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("core:get_country_subdivisions"),
                "hx-target": "#id_state",
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
                "hx-vals": "js:{country: event.target.value}",
            }
        )
        self.fields["address_state"] = forms.ChoiceField(
            choices=[],
            required=False,
            widget=forms.Select(
                attrs={"id": "id_state", "class": "js-example-basic-single headselect"}
            ),
        )

        if "address_country" in self.data:
            country_code = self.data.get("address_country")
            self.fields["address_state"].choices = get_subdivision_choices(country_code)
        elif self.instance.pk and self.instance.address_country:
            self.fields["address_state"].choices = get_subdivision_choices(
                self.instance.address_country.code
            )
            self.fields["address_state"].initial = resolve_subdivision_choice(
                self.fields["address_state"].choices, self.instance.address_state
            )

    def clean_parent_contact(self):
        """Reject parent contacts that would create a circular hierarchy."""
        parent_contact = self.cleaned_data.get("parent_contact")
        if parent_contact and self.instance.pk:
            if _would_create_cycle(self.instance, parent_contact):
                raise ValidationError(
                    _(
                        "Invalid parent contact. This relationship would create a circular hierarchy."
                    )
                )
        return parent_contact


class ContactSingleForm(OwnerQuerysetMixin, FinloModelForm):
    """
    Custom form for Contact to add HTMX attributes
    Inherits from FinloModelForm to preserve all existing behavior.
    """

    field_order = [
        "contact_owner",
        "title",
        "first_name",
        "last_name",
        "contact_number",
        "email",
        "secondary_contact_number",
        "birth_date",
        "assistant",
        "assistant_contact_number",
        "contact_source",
        "parent_contact",
        "is_primary",
        "address_country",
        "address_state",
        "address_city",
        "address_zip",
        "languages",
        "description",
    ]

    class Meta:
        """Meta class for LeadStatusForm"""

        model = Contact
        fields = "__all__"
        exclude = ["contact_score"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["address_country"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("core:get_country_subdivisions"),
                "hx-target": "#id_state",
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
                "hx-vals": "js:{country: event.target.value}",
            }
        )
        self.fields["address_state"] = forms.ChoiceField(
            choices=[],
            required=False,
            widget=forms.Select(
                attrs={"id": "id_state", "class": "js-example-basic-single headselect"}
            ),
        )

        if "address_country" in self.data:
            country_code = self.data.get("address_country")
            self.fields["address_state"].choices = get_subdivision_choices(country_code)
        elif self.instance.pk and self.instance.address_country:
            self.fields["address_state"].choices = get_subdivision_choices(
                self.instance.address_country.code
            )
            self.fields["address_state"].initial = resolve_subdivision_choice(
                self.fields["address_state"].choices, self.instance.address_state
            )

    def clean_parent_contact(self):
        """Reject parent contacts that would create a circular hierarchy."""
        parent_contact = self.cleaned_data.get("parent_contact")
        if parent_contact and self.instance.pk:
            if _would_create_cycle(self.instance, parent_contact):
                raise ValidationError(
                    _(
                        "Invalid parent contact. This relationship would create a circular hierarchy."
                    )
                )
        return parent_contact


class ChildContactForm(forms.Form):
    """
    Form to select an existing Contact and assign it as a child camContactpaign.
    """

    contact = forms.ModelChoiceField(
        queryset=Contact.objects.none(),  # Will be set in __init__
        label=_("Select Contact"),
        widget=forms.Select(
            attrs={
                "class": "select2-pagination w-full text-sm",
                "data-placeholder": _("Select Contact"),
                "data-url": reverse_lazy(
                    "generics:model_select2",
                    kwargs={"app_label": "contacts", "model_name": "Contact"},
                ),
                "data-field-name": "contact",
                "id": "id_contact",
            }
        ),
        help_text=_("Select the contact to assign as a child contact."),
    )

    parent_contact = forms.ModelChoiceField(
        queryset=Contact.objects.none(),
        required=False,
        widget=forms.HiddenInput(),  # Make this a hidden field
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        # Remove any generic form attributes that might be passed
        generic_attrs = ["full_width_fields", "dynamic_create_fields", "hidden_fields"]
        for attr in generic_attrs:
            kwargs.pop(attr, None)

        super().__init__(*args, **kwargs)

        self.setup_contact_queryset()

    def setup_contact_queryset(self):
        """
        Set up the contact queryset based on company and sales hierarchy.
        """
        req = self.request
        if not req:
            from finlo.contrib.utils.middlewares import get_current_request

            req = get_current_request()
        user = getattr(req, "user", None) if req else None
        company = getattr(req, "active_company", None)

        from finlo.contrib.core.sales_authorization import (
            scope_queryset_to_sales_hierarchy,
        )

        base_qs = Contact.objects.all()
        if company:
            base_qs = base_qs.filter(company=company)
        if user and not getattr(user, "is_superuser", False):
            base_qs = scope_queryset_to_sales_hierarchy(base_qs, user)

        self.fields["parent_contact"].queryset = base_qs

        parent_id = req.GET.get("id") if req else None
        if not parent_id:
            self.fields["contact"].queryset = base_qs
            return

        try:
            parent_contact = base_qs.get(pk=parent_id)

            queryset = base_qs.exclude(id=parent_id).filter(parent_contact__isnull=True)
            descendant_ids = self.get_descendant_ids(parent_contact)
            if descendant_ids:
                queryset = queryset.exclude(id__in=descendant_ids)

            self.fields["contact"].queryset = queryset

        except Contact.DoesNotExist:
            self.fields["contact"].queryset = base_qs.filter(
                parent_contact__isnull=True
            )

    def clean(self):
        cleaned_data = super().clean()
        contact = cleaned_data.get("contact")
        parent_contact = cleaned_data.get("parent_contact")

        req = self.request
        if not req:
            from finlo.contrib.utils.middlewares import get_current_request

            req = get_current_request()
        user = getattr(req, "user", None) if req else None

        if user and not getattr(user, "is_superuser", False):
            from finlo.contrib.core.sales_authorization import can_access_sales_record

            if contact and not can_access_sales_record(user, contact):
                self.add_error(
                    "contact", _("You do not have permission to access this contact.")
                )
            if parent_contact and not can_access_sales_record(user, parent_contact):
                self.add_error(
                    "parent_contact",
                    _("You do not have permission to access the parent contact."),
                )

        return cleaned_data

    def get_descendant_ids(self, contact):
        """
        Get all descendant IDs of an Contact to prevent circular references.
        """
        descendant_ids = []
        children = Contact.objects.filter(parent_contact=contact)
        for child in children:
            descendant_ids.append(child.id)
            descendant_ids.extend(self.get_descendant_ids(child))
        return descendant_ids

    def clean_contact(self):
        """
        Validate the selected contact.
        """
        contact = self.cleaned_data.get("contact")
        if not contact:
            raise ValidationError(_("Please select contact."))

        # Check if contact already has a parent
        if contact.parent_contact:
            raise ValidationError(
                _("This contact already has a parent contact assigned.")
            )

        # Get parent from hidden field instead of request
        parent_contact = self.cleaned_data.get("parent_contact")
        if parent_contact and str(contact.id) == str(parent_contact.id):
            raise ValidationError(_("An contact cannot be its own parent."))

        return contact

    def clean(self):
        """Validate that a contact is selected for child-contact assignment."""
        cleaned_data = super().clean()
        contact = cleaned_data.get("contact")

        if not contact:
            raise ValidationError(_("Please select a valid contact."))

        return cleaned_data
