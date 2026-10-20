"""Authorization helpers for opportunity creation from qualified leads."""

from finlo.contrib.core.authorization import get_company_scope
from finlo.contrib.core.models import SalesAssignment
from finlo_crm.leads.models import Lead


def get_qualified_assigned_leads(user, request=None):
    """Return qualified leads currently assigned to an active BDO."""
    if (
        not user
        or not getattr(user, "is_authenticated", False)
        or getattr(getattr(user, "role", None), "system_key", None) != "BDO"
        or not user.is_active
    ):
        return Lead.objects.none()

    scope = get_company_scope(user, request)
    company_id = scope.company_id
    if company_id is None:
        return Lead.objects.none()

    has_active_assignment = SalesAssignment.all_objects.filter(
        user_id=user.pk,
        company_id=company_id,
        is_active=True,
        user__is_active=True,
        user__role__system_key="BDO",
    ).exists()
    if not has_active_assignment:
        return Lead.objects.none()

    from finlo.db.models import Q

    return Lead.objects.filter(
        company_id=company_id,
        sub_owner_id=user.pk,
    ).filter(
        Q(lead_status__name__iexact="qualified") | Q(qualified_at__isnull=False)
    ).select_related("lead_status")


def is_valid_bdo_opportunity_source(user, lead, request=None):
    """Check that a BDO is actively assigned to the qualified source lead."""
    if lead is None:
        return False
    return get_qualified_assigned_leads(user, request).filter(pk=lead.pk).exists()
