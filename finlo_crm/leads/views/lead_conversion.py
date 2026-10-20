"""Lead Conversion View for Finlo CRM"""

# Third-party imports (other)
from dateutil.relativedelta import relativedelta

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from finlo.contrib.core.utils import get_allowed_user_ids
from finlo.contrib.core.sales_authorization import has_effective_permission

# First party imports (Finlo)
from finlo.db import transaction
from finlo.shortcuts import get_object_or_404, render
from finlo.urls import reverse
from finlo.utils import timezone
from finlo.utils.decorators import htmx_required, method_decorator
from finlo.utils.translation import gettext_lazy as _
from finlo.views.generic import FormView
from finlo.web import Http404, ScriptResponse

# Local imports
from finlo_crm.accounts.models import Account
from finlo_crm.contacts.models import Contact, ContactAccountRelationship
from finlo_crm.leads.forms import LeadConversionForm
from finlo_crm.leads.models import Lead, LeadStatus
from finlo_crm.opportunities.models import (
    Opportunity,
    OpportunityContactRole,
    OpportunityStage,
)


@method_decorator(htmx_required, name="dispatch")
class LeadConversionView(LoginRequiredMixin, FormView):
    """View to handle lead conversion to account, contact, and opportunity."""

    template_name = "lead_convert.html"
    form_class = LeadConversionForm

    def dispatch(self, request, *args, **kwargs):
        """Load the lead and short-circuit with an HTMX error response if missing."""
        try:
            self.lead = Lead.objects.get(pk=self.kwargs["pk"])
        except Exception as e:
            messages.error(self.request, str(e))
            return ScriptResponse(reload=True, extra="closeContentModal();")

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Return redirect target after successful conversion."""
        return reverse("leads:leads_detail", kwargs={"pk": self.lead.pk})

    def get_form_kwargs(self):
        """Inject lead and optional selected account into form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["lead"] = self.lead

        # Get selected account for filtering opportunities
        selected_account_id = self.request.GET.get("existing_account")
        if selected_account_id:
            try:
                kwargs["selected_account"] = Account.objects.get(pk=selected_account_id)
            except Account.DoesNotExist:
                pass

        return kwargs

    def get_context_data(self, **kwargs):
        """Populate template context with lead and selected conversion actions."""
        context = super().get_context_data(**kwargs)
        context["lead"] = self.lead
        context["account_action"] = self.request.GET.get(
            "account_action", "none"
        )
        context["contact_action"] = self.request.GET.get(
            "contact_action", "create_new"
        )
        context["opportunity_action"] = self.request.GET.get(
            "opportunity_action",
            "create_new",
        )
        context["selected_account_id"] = self.request.GET.get("existing_account")
        return context

    def get(self, request, *args, **kwargs):
        """Handle permission checks and HTMX partial rendering for conversion form."""
        pk = self.kwargs.get("pk")
        if pk:
            try:
                lead = get_object_or_404(Lead, pk=pk)
            except Http404:
                messages.error(request, _("Lead not found or no longer exists."))
                return ScriptResponse(reload=True, close=True)

            if not has_effective_permission(request.user, "leads.convert_lead") and not (
                lead.lead_owner == request.user
                and has_effective_permission(request.user, "leads.convert_own_lead")
            ):
                return render(request, "403.html")

        if "HTTP_HX_REQUEST" in request.META:
            hx_target = request.META.get("HTTP_HX_TARGET", "").replace("#", "")

            if "existing_account" in request.GET and hx_target == "opportunity-field":
                context = self.get_context_data()
                return render(request, "lead_convert_opportunity.html", context)

            if hx_target:
                action = request.GET.get(f"{hx_target}_action", "create_new")
                context = self.get_context_data()
                context[f"{hx_target}_action"] = action
                if hx_target == "account-field":
                    return render(request, "lead_convert_account.html", context)
                if hx_target == "contact-field":
                    return render(request, "lead_convert_contact.html", context)
                if hx_target == "opportunity-field":
                    return render(request, "lead_convert_opportunity.html", context)

        return super().get(request, *args, **kwargs)

    def _has_perm(self, perm, own_perm, owner):
        """Return True if the user holds `perm`, or `own_perm` scoped to `owner`."""
        user = self.request.user
        if has_effective_permission(user, perm):
            return True
        if owner is not None and owner.pk in get_allowed_user_ids(user):
            return has_effective_permission(user, own_perm)
        return False

    def _check_conversion_permissions(self, form):
        """
        Verify the user can create/update the Account, Contact, and
        Opportunity this conversion would touch. Returns a list of
        human-readable reasons for any missing permission (empty if allowed).
        """
        owner = form.cleaned_data.get("owner")
        errors = []

        if not self._has_perm(
            "leads.convert_lead", "leads.convert_own_lead", self.lead.lead_owner
        ):
            errors.append(_("convert this lead"))

        account_action = form.cleaned_data.get("account_action") or "none"
        if account_action == "create_new":
            if not self._has_perm(
                "accounts.add_account", "accounts.add_own_account", owner
            ):
                errors.append(_("create an account"))
        elif account_action == "select_existing":
            existing_account = form.cleaned_data.get("existing_account")
            account_owner = getattr(existing_account, "account_owner", None)
            if not self._has_perm(
                "accounts.change_account", "accounts.change_own_account", account_owner
            ):
                errors.append(_("link the selected account"))

        if form.cleaned_data["contact_action"] == "create_new":
            if not self._has_perm(
                "contacts.add_contact", "contacts.add_own_contact", owner
            ):
                errors.append(_("create a contact"))
        else:
            existing_contact = form.cleaned_data.get("existing_contact")
            contact_owner = getattr(existing_contact, "contact_owner", None)
            if not self._has_perm(
                "contacts.change_contact", "contacts.change_own_contact", contact_owner
            ):
                errors.append(_("link the selected contact"))

        if form.cleaned_data["opportunity_action"] == "create_new":
            if not self._has_perm(
                "opportunities.add_opportunity",
                "opportunities.add_own_opportunity",
                owner,
            ):
                errors.append(_("create an opportunity"))
        else:
            existing_opportunity = form.cleaned_data.get("existing_opportunity")
            opportunity_owner = getattr(existing_opportunity, "owner", None)
            if not self._has_perm(
                "opportunities.change_opportunity",
                "opportunities.change_own_opportunity",
                opportunity_owner,
            ):
                errors.append(_("link the selected opportunity"))

        # BDO role restriction
        role_key = getattr(
            getattr(self.request.user, "role", None), "system_key", None
        )
        if role_key == "BDO":
            from finlo_crm.opportunities.authorization import (
                is_valid_bdo_opportunity_source,
            )

            if not is_valid_bdo_opportunity_source(
                self.request.user, self.lead, self.request
            ):
                errors.append(
                    _("create an opportunity (BDO must be assigned to this qualified lead)")
                )

        return errors

    def form_valid(self, form):
        """Convert lead entities in a transaction and return success response."""
        missing = self._check_conversion_permissions(form)
        if missing:
            messages.error(
                self.request,
                _("You don't have permission to %(actions)s.")
                % {"actions": ", ".join(missing)},
            )
            return self.form_invalid(form)

        with transaction.atomic():
            lead = Lead.objects.select_for_update().get(pk=self.lead.pk)
            if lead.is_convert:
                messages.error(self.request, _("This lead has already been converted."))
                return ScriptResponse(reload=True, close=True)

            try:
                lead_status = LeadStatus.objects.filter(
                    company=lead.company, is_final=True
                ).first()
                if not lead_status:
                    lead_status = (
                        LeadStatus.objects.filter(company=lead.company)
                        .order_by("-order")
                        .first()
                    )
                company = (
                    getattr(self.request, "active_company", None) or lead.company
                )
                account = self._process_account(form, company)
                contact = self._process_contact(form, account, company)
                opportunity = self._process_opportunity(
                    form, account, contact, company
                )

                # Update only the Lead's conversion status.
                lead.is_convert = True
                lead.updated_at = timezone.now()
                if lead_status:
                    lead.lead_status = lead_status
                lead._skip_conversion_signal = True
                lead.save()

                messages.success(
                    self.request,
                    f'Lead "{lead.title}" has been successfully converted!',
                )
                self.conversion_data = {
                    "account": account,
                    "contact": contact,
                    "opportunity": opportunity,
                    "lead": lead,
                }
            except Exception as e:
                messages.error(self.request, f"Error converting lead: {str(e)}")
                return self.form_invalid(form)

        response = super().form_valid(form)
        if "HTTP_HX_REQUEST" in self.request.META:
            return self._render_success_modal()
        return response

    def _render_success_modal(self):
        """Render the success modal with conversion data"""
        context = {
            "account": self.conversion_data["account"],
            "contact": self.conversion_data["contact"],
            "opportunity": self.conversion_data["opportunity"],
            "lead": self.conversion_data["lead"],
        }
        return render(self.request, "lead_convert_success_modal.html", context)

    def _process_account(self, form, company):
        action = form.cleaned_data.get("account_action")
        if action == "create_new":
            return Account.objects.create(
                name=form.cleaned_data["account_name"],
                account_owner=form.cleaned_data.get("owner"),
                contact_number=self.lead.contact_number,
                annual_revenue=self.lead.annual_revenue,
                industry=self.lead.industry,
                number_of_employees=self.lead.no_of_employees,
                fax=self.lead.fax,
                account_source=self.lead.lead_source,
                company=company,
            )
        elif action == "select_existing":
            return form.cleaned_data.get("existing_account")
        return None

    def _process_contact(self, form, account, company):
        owner = form.cleaned_data.get("owner") or self.lead.lead_owner
        if form.cleaned_data["contact_action"] == "create_new":
            contact = Contact.objects.create(
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=self.lead.email,
                contact_number=self.lead.contact_number,
                contact_owner=owner,
                company=company,
            )
            if account:
                ContactAccountRelationship.objects.get_or_create(
                    contact=contact, account=account, company=company
                )
            return contact
        contact = form.cleaned_data["existing_contact"]
        if account:
            relationship, created = ContactAccountRelationship.objects.get_or_create(
                contact=contact, defaults={"account": account}, company=company
            )
            if not created and relationship.account != account:
                relationship.account = account
                relationship.save()
        return contact

    def _process_opportunity(self, form, account, contact, company):
        owner = form.cleaned_data.get("owner") or self.lead.lead_owner
        if form.cleaned_data["opportunity_action"] == "create_new":
            first_stage = (
                OpportunityStage.objects.filter(company=company)
                .order_by("order")
                .first()
            )
            campaign_member = self.lead.lead_campaign_members.first()
            closed_date = timezone.now().date() + relativedelta(months=1)
            opportunity = Opportunity.objects.create(
                name=form.cleaned_data["opportunity_name"],
                account=account,
                contact=contact,
                source_lead=self.lead,
                owner=owner,
                stage=first_stage,
                primary_campaign_source=(
                    campaign_member.campaign if campaign_member else None
                ),
                close_date=closed_date,
                company=company,
            )
            OpportunityContactRole.objects.get_or_create(
                opportunity=opportunity,
                contact=contact,
                defaults={"is_primary": True},
                company=company,
            )
            return opportunity
        opportunity = form.cleaned_data["existing_opportunity"]
        if account and opportunity.account != account:
            opportunity.account = account
        if contact and not opportunity.contact:
            opportunity.contact = contact
        if not opportunity.source_lead:
            opportunity.source_lead = self.lead
        role, created = OpportunityContactRole.objects.get_or_create(
            opportunity=opportunity,
            contact=contact,
            defaults={"is_primary": True},
            company=company,
        )
        if not created and role.contact != contact:
            role.contact = contact
            role.save()
        opportunity.save()
        return opportunity

    def get_initial(self):
        """Provide default create-new options for conversion sections."""
        return {
            "account_action": "none",
            "contact_action": "create_new",
            "opportunity_action": "create_new",
        }

    def form_invalid(self, form):
        """Re-render form with validation errors, including HTMX responses."""
        if "HTTP_HX_REQUEST" in self.request.META:
            # Re-render the entire form with errors for HTMX requests
            context = self.get_context_data(form=form)
            return render(self.request, self.template_name, context)
        return super().form_invalid(form)
