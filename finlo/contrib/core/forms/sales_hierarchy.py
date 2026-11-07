"""Forms for company-scoped sales hierarchy administration."""

from finlo.auth.models import User
from finlo.contrib.core.authorization import (
    get_company_scope,
    scope_queryset_to_company,
)
from finlo.contrib.core.models import Company, SalesAssignment, SalesRegion, SalesTeam
from finlo.contrib.core.models import Role
from finlo.contrib.core.sales_authorization import get_sales_scope_user_ids
from finlo.contrib.generics.forms import FinloModelForm


class SalesCompanyFormMixin:
    """Restrict organization selectors to the request's active company."""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if self.request is None or not self.request.user.is_authenticated:
            for name in ("company", "region", "team", "user", "manager", "senior_sales_manager", "area_sales_manager"):
                if name in self.fields:
                    self.fields[name].queryset = self.fields[name].queryset.none()
            return

        scope = get_company_scope(self.request.user, self.request)
        if "company" in self.fields:
            companies = Company.all_objects.all()
            if not scope.all_companies:
                companies = companies.filter(pk=scope.company_id)
                self.fields["company"].disabled = True
                self.fields["company"].initial = scope.company_id
            self.fields["company"].queryset = companies

        if "region" in self.fields:
            self.fields["region"].queryset = scope_queryset_to_company(
                SalesRegion.all_objects.all(), self.request.user, self.request
            )
        if "team" in self.fields:
            self.fields["team"].queryset = scope_queryset_to_company(
                SalesTeam.all_objects.all(), self.request.user, self.request
            )
        if "user" in self.fields:
            self.fields["user"].queryset = scope_queryset_to_company(
                User.objects.all(), self.request.user, self.request
            ).filter(is_active=True)
        if "manager" in self.fields:
            allowed_ids = get_sales_scope_user_ids(self.request.user)
            managers = scope_queryset_to_company(
                User.objects.all(), self.request.user, self.request
            ).filter(is_active=True)
            if allowed_ids is not None:
                managers = managers.filter(pk__in=allowed_ids)
            self.fields["manager"].queryset = managers
        for name in ("senior_sales_manager", "area_sales_manager"):
            if name in self.fields:
                self.fields[name].queryset = scope_queryset_to_company(
                    User.objects.all(), self.request.user, self.request
                ).filter(is_active=True)


class SalesRegionForm(SalesCompanyFormMixin, FinloModelForm):
    class Meta:
        model = SalesRegion
        fields = ["company", "name", "code", "description"]


class SalesTeamForm(SalesCompanyFormMixin, FinloModelForm):
    class Meta:
        model = SalesTeam
        fields = [
            "company",
            "name",
            "code",
            "region",
            "senior_sales_manager",
            "area_sales_manager",
        ]


class SalesAssignmentForm(SalesCompanyFormMixin, FinloModelForm):
    class Meta:
        model = SalesAssignment
        fields = ["company", "user", "region", "team", "manager", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get("request") or getattr(self, "request", None)
        if not request:
            from finlo.contrib.utils.middlewares import get_current_request

            request = get_current_request()
        actor = getattr(request, "user", None) if request else None
        if actor and not getattr(actor, "is_superuser", False):
            from finlo.contrib.core.sales_authorization import (
                _role_key,
                get_sales_scope_region_ids,
                get_sales_scope_team_ids,
                get_sales_scope_user_ids,
            )

            if _role_key(actor) == "RSM":
                if "region" in self.fields:
                    self.fields["region"].queryset = self.fields["region"].queryset.filter(
                        pk__in=get_sales_scope_region_ids(actor) or set()
                    )
                if "team" in self.fields:
                    self.fields["team"].queryset = self.fields["team"].queryset.filter(
                        pk__in=get_sales_scope_team_ids(actor) or set()
                    )
                if "manager" in self.fields:
                    self.fields["manager"].queryset = self.fields["manager"].queryset.filter(
                        pk__in=get_sales_scope_user_ids(actor) or set()
                    )

    def clean(self):
        cleaned_data = super().clean()
        user_val = cleaned_data.get("user")
        role = getattr(user_val, "role", None)
        if not role or role.system_key not in {key for key, _label in Role.SALES_ROLE_CHOICES}:
            if user_val:
                self.add_error("user", "Select an employee with one of the six sales roles.")

        request = getattr(self, "request", None)
        if not request:
            from finlo.contrib.utils.middlewares import get_current_request

            request = get_current_request()
        actor = getattr(request, "user", None) if request else None

        if actor and not getattr(actor, "is_superuser", False):
            from finlo.contrib.core.sales_authorization import (
                _role_key,
                get_sales_scope_region_ids,
                get_sales_scope_team_ids,
                get_sales_scope_user_ids,
            )

            actor_role = _role_key(actor)
            if actor_role == "RSM":
                region = cleaned_data.get("region")
                allowed_regions = get_sales_scope_region_ids(actor) or set()
                if region and region.pk not in allowed_regions:
                    self.add_error("region", _("You can only assign employees to your own region."))

                team = cleaned_data.get("team")
                allowed_teams = get_sales_scope_team_ids(actor) or set()
                if team and team.pk not in allowed_teams:
                    self.add_error("team", _("You can only assign employees to teams within your region."))

                manager = cleaned_data.get("manager")
                allowed_users = get_sales_scope_user_ids(actor) or set()
                if manager and manager.pk not in allowed_users:
                    self.add_error("manager", _("You can only assign managers within your region."))

        return cleaned_data
