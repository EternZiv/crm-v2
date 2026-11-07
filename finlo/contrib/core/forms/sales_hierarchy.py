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

    def clean(self):
        cleaned_data = super().clean()
        role = getattr(cleaned_data.get("user"), "role", None)
        if role and role.system_key in {key for key, _label in Role.SALES_ROLE_CHOICES}:
            return cleaned_data
        if cleaned_data.get("user"):
            self.add_error("user", "Select an employee with one of the six sales roles.")
        return cleaned_data
