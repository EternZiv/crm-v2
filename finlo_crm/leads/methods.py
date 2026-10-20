"""Lead helper methods (e.g. lead conversion into account, contact, opportunity)."""

# Third-party imports (other)
from dateutil.relativedelta import relativedelta

# First party imports (Finlo)
from finlo.core.exceptions import ValidationError
from finlo.db import transaction
from finlo.utils import timezone

# Local imports
from finlo_crm.accounts.models import Account
from finlo_crm.contacts.models import Contact, ContactAccountRelationship
from finlo_crm.opportunities.models import (
    Opportunity,
    OpportunityContactRole,
    OpportunityStage,
)


def convert_lead(
    lead,
    company,
    account_name=None,
    first_name=None,
    last_name=None,
    opportunity_name=None,
    create_account=False,
):
    """
    Convert a Lead into a Contact and an Opportunity (and optionally an Account),
    linked via source_lead, contact, and OpportunityContactRole.

    Runs atomically with select_for_update to prevent duplicate conversion.
    Returns (account, contact, opportunity).
    """
    first_name = first_name or lead.first_name
    last_name = last_name or lead.last_name
    contact_display = f"{first_name or ''} {last_name or ''}".strip()
    opportunity_name = (
        opportunity_name
        or (f"{contact_display} Opportunity" if contact_display else f"{lead.title} Opportunity")
    )

    first_stage = (
        OpportunityStage.objects.filter(company=company).order_by("order").first()
    )
    if not first_stage:
        raise ValidationError(
            "Cannot convert lead: no Opportunity Stage is configured for this company."
        )

    LeadModel = lead.__class__
    with transaction.atomic():
        locked_lead = LeadModel.objects.select_for_update().get(pk=lead.pk)
        if locked_lead.is_convert:
            raise ValidationError("This lead has already been converted.")

        account = None
        if create_account or account_name:
            acc_name = (
                account_name
                or locked_lead.lead_company
                or contact_display
                or locked_lead.title
            )
            account = Account.objects.create(
                name=acc_name,
                contact_number=locked_lead.contact_number,
                annual_revenue=locked_lead.annual_revenue,
                industry=locked_lead.industry,
                number_of_employees=locked_lead.no_of_employees,
                fax=locked_lead.fax,
                account_source=locked_lead.lead_source,
                company=company,
            )

        contact = Contact.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=locked_lead.email,
            contact_number=locked_lead.contact_number,
            contact_owner=locked_lead.lead_owner,
            company=company,
        )
        if account:
            ContactAccountRelationship.objects.get_or_create(
                contact=contact, account=account, company=company
            )

        campaign_member = locked_lead.lead_campaign_members.first()
        closed_date = timezone.now().date() + relativedelta(months=1)
        opportunity = Opportunity.objects.create(
            name=opportunity_name,
            account=account,
            contact=contact,
            source_lead=locked_lead,
            owner=locked_lead.lead_owner,
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

        locked_lead.is_convert = True
        locked_lead.updated_at = timezone.now()
        locked_lead._skip_conversion_signal = True
        locked_lead.save()

    return account, contact, opportunity


# Define your leads helper methods here
