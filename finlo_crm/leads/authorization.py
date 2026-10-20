"""Lead ownership and BDO assignment rules."""

from finlo.contrib.core.authorization import can_access_company_record
from finlo.contrib.core.models import SalesAssignment
from finlo.contrib.core.sales_authorization import has_effective_permission
from finlo.core.exceptions import PermissionDenied, ValidationError
from finlo.db import transaction
from finlo.utils.translation import gettext_lazy as _


def assign_lead_to_bdo(lead, actor, bdo):
    """Assign a lead to a directly reporting BDO without changing its owner."""
    if (
        not actor
        or not actor.is_authenticated
        or getattr(getattr(actor, "role", None), "system_key", None) != "ASM"
    ):
        raise PermissionDenied(_("Only an Area Sales Manager may assign a lead to a BDO."))
    if not has_effective_permission(actor, "leads.change_lead"):
        raise PermissionDenied(_("You do not have permission to update this lead."))
    if lead.company_id != actor.company_id or bdo.company_id != actor.company_id:
        raise PermissionDenied(_("Lead and BDO must belong to your company."))
    if not can_access_company_record(actor, lead):
        raise PermissionDenied(_("You cannot assign a lead outside your sales scope."))

    with transaction.atomic():
        locked_lead = type(lead).all_objects.select_for_update().get(pk=lead.pk)
        assignment = (
            SalesAssignment.all_objects.select_for_update()
            .filter(user_id=bdo.pk, company_id=actor.company_id, is_active=True)
            .select_related("user__role", "team")
            .first()
        )
        if (
            assignment is None
            or assignment.user.role_id is None
            or assignment.user.role.system_key != "BDO"
            or assignment.manager_id != actor.pk
            or assignment.team is None
            or assignment.team.area_sales_manager_id != actor.pk
        ):
            raise PermissionDenied(
                _("You may assign leads only to an active BDO directly assigned to you.")
            )
        if not can_access_company_record(actor, locked_lead):
            raise PermissionDenied(_("You cannot assign a lead outside your sales scope."))

        owner_id = locked_lead.lead_owner_id
        locked_lead.sub_owner = assignment.user
        locked_lead.full_clean()
        locked_lead.save(update_fields=["sub_owner"])
        if locked_lead.lead_owner_id != owner_id:
            raise ValidationError(_("Lead ownership must remain with its creator."))
        lead.sub_owner = assignment.user
        lead.sub_owner_id = assignment.user.pk
        return locked_lead
