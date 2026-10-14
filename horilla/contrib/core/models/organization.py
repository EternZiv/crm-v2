"""
This module defines the organizational models for the Horilla platform
"""

# Standard library imports
import logging

# Django imports
# Third-party imports (Django)
from django.conf import settings
from django.contrib.auth.models import Permission

# First party imports (Horilla)
from horilla.core.exceptions import ValidationError
from horilla.db import models
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# Local imports
from .base import HorillaCoreModel

logger = logging.getLogger(__name__)


class Department(HorillaCoreModel):
    """
    Department model
    """

    department_name = models.CharField(
        max_length=50, blank=False, verbose_name=_("Department Name")
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    class Meta:
        """
        Meta options for the Department model.
        """

        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        unique_together = (("department_name", "company"),)

    def __str__(self):
        return str(self.department_name)

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("core:department_update_form", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        This method to get delete url
        """

        return reverse_lazy("core:department_delete_view", kwargs={"pk": self.pk})


class Role(HorillaCoreModel):
    """
    Role model
    """

    SALES_ROLE_CHOICES = [
        ("SUPER_ADMIN", _("Super Admin")),
        ("HEAD_OF_SALES", _("Head of Sales")),
        ("RSM", _("Regional Sales Manager")),
        ("SSM", _("Senior Sales Manager")),
        ("ASM", _("Area Sales Manager")),
        ("BDO", _("Business Development Officer")),
    ]

    role_name = models.CharField(max_length=255, verbose_name=_("Role"))
    system_key = models.CharField(
        max_length=32,
        choices=SALES_ROLE_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("System Role Key"),
    )
    parent_role = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subroles",
        verbose_name=_("Parent Role"),
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    permissions = models.ManyToManyField(
        Permission, blank=True, related_name="roles", verbose_name=_("Permissions")
    )

    class Meta:
        """
        Meta options for the Role model.
        """

        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        constraints = [
            models.UniqueConstraint(
                fields=("company", "system_key"),
                condition=models.Q(system_key__isnull=False),
                name="core_role_company_system_key_unique",
            )
        ]

    def clean(self):
        """Keep role-tree links within a company and reject cycles."""
        super().clean()
        expected_parent_key = {
            "SUPER_ADMIN": None,
            "HEAD_OF_SALES": "SUPER_ADMIN",
            "RSM": "HEAD_OF_SALES",
            "SSM": "RSM",
            "ASM": "SSM",
            "BDO": "ASM",
        }.get(self.system_key)
        if self.system_key and self.system_key != "SUPER_ADMIN":
            if not self.parent_role_id:
                raise ValidationError(
                    {"parent_role": _("A sales role must have its parent role set.")}
                )
            if self.parent_role.company_id != self.company_id:
                raise ValidationError(
                    {"parent_role": _("A parent role must belong to the same company.")}
                )
            if self.parent_role.system_key != expected_parent_key:
                raise ValidationError(
                    {
                        "parent_role": _(
                            "A sales role must have the immediately higher sales role as its parent."
                        )
                    }
                )
        elif self.system_key == "SUPER_ADMIN" and self.parent_role_id:
            raise ValidationError(
                {"parent_role": _("Super Admin cannot have a parent role.")}
            )

        if not self.parent_role_id:
            return
        if self.parent_role.company_id != self.company_id:
            raise ValidationError(
                {"parent_role": _("A parent role must belong to the same company.")}
            )

        parent = self.parent_role
        while parent is not None:
            if parent.pk == self.pk:
                raise ValidationError(
                    {"parent_role": _("Role hierarchy cannot contain a cycle.")}
                )
            parent = parent.parent_role

    def delete(self, *args, **kwargs):
        """Protect canonical sales roles from cascading deletion of their users."""
        if self.system_key:
                raise ValidationError(_("Canonical sales roles cannot be deleted."))
        return super().delete(*args, **kwargs)

    def __str__(self):
        return str(self.role_name)

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy("core:delete_role", kwargs={"pk": self.pk})

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("core:edit_roles_view", kwargs={"pk": self.pk})


class TeamRole(HorillaCoreModel):
    """
    Team Role model
    """

    team_role_name = models.CharField(
        max_length=50, blank=False, verbose_name=_("Team Role Name")
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    class Meta:
        """
        Meta options for the Team Role model.
        """

        verbose_name = _("Team Role")
        verbose_name_plural = _("Team Roles")

    def __str__(self):
        return str(self.team_role_name)

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("core:team_role_update_form", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        This method to get delete url
        """

        return reverse_lazy("core:team_role_delete_view", kwargs={"pk": self.pk})


class CustomerRole(HorillaCoreModel):
    """
    Customer Role model
    """

    customer_role_name = models.CharField(
        max_length=50, blank=False, verbose_name=_("Customer Role Name")
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    class Meta:
        """
        Meta options for the Customer Role model.
        """

        verbose_name = _("Customer Role")
        verbose_name_plural = _("Customer Roles")

    def __str__(self):
        return str(self.customer_role_name)

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("core:customer_role_update_form", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        This method to get delete url
        """

        return reverse_lazy("core:customer_role_delete_view", kwargs={"pk": self.pk})


class PartnerRole(HorillaCoreModel):
    """
    Partner Role model
    """

    partner_role_name = models.CharField(
        max_length=50, blank=False, verbose_name=_("Partner Role Name")
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    class Meta:
        """
        Meta options for the Partner Role model.
        """

        verbose_name = _("Partner Role")
        verbose_name_plural = _("Partner Roles")

    def __str__(self):
        return str(self.partner_role_name)

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("core:partner_role_update_form", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy("core:partner_role_delete_view", kwargs={"pk": self.pk})


class SalesRegion(HorillaCoreModel):
    """Geographic sales region within a company."""

    name = models.CharField(max_length=120, verbose_name=_("Region Name"))
    code = models.CharField(max_length=32, verbose_name=_("Region Code"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Sales Region")
        verbose_name_plural = _("Sales Regions")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=("company", "code"), name="core_salesregion_company_code_unique"
            ),
            models.UniqueConstraint(
                fields=("company", "name"), name="core_salesregion_company_name_unique"
            ),
        ]

    def clean(self):
        super().clean()
        if not self.company_id:
            raise ValidationError({"company": _("A company is required for a region.")})

    def __str__(self):
        return self.name


class SalesTeam(HorillaCoreModel):
    """Sales team managed by an SSM and optionally an ASM."""

    name = models.CharField(max_length=120, verbose_name=_("Team Name"))
    code = models.CharField(max_length=32, verbose_name=_("Team Code"))
    region = models.ForeignKey(
        SalesRegion,
        on_delete=models.PROTECT,
        related_name="teams",
        verbose_name=_("Region"),
    )
    senior_sales_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="senior_sales_teams",
        verbose_name=_("Senior Sales Manager"),
    )
    area_sales_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="area_sales_teams",
        null=True,
        blank=True,
        verbose_name=_("Area Sales Manager"),
    )

    class Meta:
        verbose_name = _("Sales Team")
        verbose_name_plural = _("Sales Teams")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=("company", "code"), name="core_salesteam_company_code_unique"
            ),
            models.UniqueConstraint(
                fields=("company", "name"), name="core_salesteam_company_name_unique"
            ),
        ]

    def clean(self):
        """Ensure team managers are valid employees in the team's region."""
        super().clean()
        if not self.region_id or not self.senior_sales_manager_id:
            return
        if not self.company_id:
            self.company_id = self.region.company_id
        if self.region.company_id != self.company_id:
            raise ValidationError(
                {"region": _("A team region must belong to the same company.")}
            )

        senior_assignment = (
            SalesAssignment.objects.filter(
                user_id=self.senior_sales_manager_id, is_active=True
            )
            .select_related("user__role")
            .first()
        )
        if (
            senior_assignment is None
            or senior_assignment.user.role_id is None
            or not senior_assignment.user.is_active
            or senior_assignment.user.role.system_key != "SSM"
            or senior_assignment.region_id != self.region_id
            or senior_assignment.company_id != self.company_id
        ):
            raise ValidationError(
                {
                    "senior_sales_manager": _(
                        "The senior manager must be an active SSM assigned to this region."
                    )
                }
            )

        if self.area_sales_manager_id:
            area_assignment = (
                SalesAssignment.objects.filter(
                    user_id=self.area_sales_manager_id, is_active=True
                )
                .select_related("user__role")
                .first()
            )
            if (
                area_assignment is None
                or area_assignment.user.role_id is None
                or not area_assignment.user.is_active
                or area_assignment.user.role.system_key != "ASM"
                or area_assignment.manager_id != self.senior_sales_manager_id
                or area_assignment.region_id != self.region_id
                or area_assignment.company_id != self.company_id
            ):
                raise ValidationError(
                    {
                        "area_sales_manager": _(
                            "The area manager must report to this team's SSM and share its region."
                        )
                    }
                )


class SalesAssignment(HorillaCoreModel):
    """Single active reporting and territory assignment for a sales employee."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sales_assignment",
        verbose_name=_("Employee"),
    )
    region = models.ForeignKey(
        SalesRegion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assignments",
        verbose_name=_("Region"),
    )
    team = models.ForeignKey(
        SalesTeam,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assignments",
        verbose_name=_("Team"),
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_reports",
        verbose_name=_("Reports To"),
    )

    class Meta:
        verbose_name = _("Sales Assignment")
        verbose_name_plural = _("Sales Assignments")
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(user=models.F("manager")),
                name="core_salesassignment_not_self_managed",
            )
        ]

    def clean(self):
        """Validate company, role-level, region, team and manager relationships."""
        super().clean()
        if not self.user_id or not self.user.role_id:
            raise ValidationError(
                {
                    "user": _(
                        "Assign a Horilla sales role before creating this assignment."
                    )
                }
            )
        if not self.company_id:
            self.company_id = self.user.company_id
        role_key = self.user.role.system_key
        if role_key not in {key for key, _label in Role.SALES_ROLE_CHOICES}:
            raise ValidationError(
                {"user": _("The employee must have one of the six sales roles.")}
            )
        if self.user.company_id != self.company_id:
            raise ValidationError(
                {"company": _("The assignment and employee must share a company.")}
            )
        if role_key == "BDO" and self.user.is_active and not self.is_active:
            raise ValidationError(
                {
                    "is_active": _(
                        "An active BDO must have an active sales assignment."
                    )
                }
            )

        if role_key == "SUPER_ADMIN":
            if self.region_id or self.team_id or self.manager_id:
                raise ValidationError(
                    _(
                        "A Super Admin assignment cannot be attached to a sales territory."
                    )
                )
            return
        if role_key == "HEAD_OF_SALES":
            if self.region_id or self.team_id or self.manager_id:
                raise ValidationError(
                    _("Head of Sales cannot be assigned a region, team or manager.")
                )
            return

        if not self.region_id:
            raise ValidationError({"region": _("A region is required.")})
        if self.region.company_id != self.company_id:
            raise ValidationError(
                {"region": _("The region must belong to the employee's company.")}
            )

        if not self.manager_id:
            raise ValidationError(
                {"manager": _("A direct reporting manager is required.")}
            )
        manager_assignment = (
            SalesAssignment.objects.filter(
                user_id=self.manager_id, is_active=True
            )
            .select_related("user__role")
            .first()
        )
        expected_manager = {
            "RSM": "HEAD_OF_SALES",
            "SSM": "RSM",
            "ASM": "SSM",
            "BDO": "ASM",
        }.get(role_key)
        if (
            manager_assignment is None
            or manager_assignment.user.role_id is None
            or not manager_assignment.user.is_active
            or manager_assignment.user.role.system_key != expected_manager
            or manager_assignment.company_id != self.company_id
        ):
            raise ValidationError(
                {
                    "manager": _(
                        "The reporting manager must be an active employee at the immediately higher sales level."
                    )
                }
            )
        if (
            expected_manager != "HEAD_OF_SALES"
            and manager_assignment.region_id != self.region_id
        ):
            raise ValidationError(
                {"manager": _("The employee and manager must share a region.")}
            )

        if role_key in {"RSM", "SSM", "ASM"} and self.team_id:
            raise ValidationError(
                {"team": _("Only a BDO may be assigned directly to one sales team.")}
            )
        if role_key == "BDO":
            if not self.team_id:
                raise ValidationError(
                    {"team": _("A BDO must belong to one sales team.")}
                )
            if (
                self.team.company_id != self.company_id
                or self.team.region_id != self.region_id
                or self.team.area_sales_manager_id != self.manager_id
            ):
                raise ValidationError(
                    {
                        "team": _(
                            "A BDO's team must be in the assigned region and managed by the assigned ASM."
                        )
                    }
                )

        if self.pk and role_key not in {"SUPER_ADMIN", "HEAD_OF_SALES"}:
            incompatible_reports = SalesAssignment.objects.filter(
                manager_id=self.user_id, is_active=True
            ).exclude(pk=self.pk).exclude(region_id=self.region_id)
            if incompatible_reports.exists():
                raise ValidationError(
                    {
                        "region": _(
                            "Transfer subordinate employees before moving this manager to another region."
                        )
                    }
                )

        ancestor_ids = {self.user_id}
        parent_id = self.manager_id
        while parent_id:
            if parent_id in ancestor_ids:
                raise ValidationError(
                    {"manager": _("Reporting relationships cannot contain a cycle.")}
                )
            ancestor_ids.add(parent_id)
            parent_id = (
                SalesAssignment.objects.filter(
                    user_id=parent_id, is_active=True
                )
                .values_list("manager_id", flat=True)
                .first()
            )

    def save(self, *args, **kwargs):
        """Validate every assignment save, including non-form write paths."""
        self.full_clean()
        return super().save(*args, **kwargs)
