"""Shared company-boundary policy for request-scoped record access."""

from dataclasses import dataclass

from django.core.exceptions import FieldDoesNotExist

from .sales_authorization import has_effective_permission


@dataclass(frozen=True)
class CompanyScope:
    """Company boundary granted to an authenticated user for one request."""

    company_id: int | None
    all_companies: bool = False


def get_company_scope(user, request=None):
    """Resolve the active company boundary without trusting session flags alone."""
    if not user or not user.is_authenticated:
        return CompanyScope(company_id=None)

    role = getattr(user, "role", None)
    if user.is_superuser:
        return CompanyScope(company_id=None, all_companies=True)
    if role and not role.is_active:
        return CompanyScope(company_id=None)
    if getattr(role, "system_key", None) == "SUPER_ADMIN":
        return CompanyScope(company_id=None, all_companies=True)
    if role and not role.system_key:
        return CompanyScope(company_id=getattr(user, "company_id", None))

    can_switch_company = has_effective_permission(user, "core.can_switch_company")
    session = getattr(request, "session", None)
    if can_switch_company and session is not None:
        if session.get("show_all_companies", False):
            return CompanyScope(company_id=None, all_companies=True)

        active_company = getattr(request, "active_company", None)
        active_company_id = getattr(active_company, "pk", None)
        if active_company_id is None:
            active_company_id = session.get("active_company_id")
        if active_company_id is not None:
            return CompanyScope(company_id=active_company_id)

    return CompanyScope(company_id=getattr(user, "company_id", None))


def scope_queryset_to_company(queryset, user, request=None):
    """Apply tenant, sales-hierarchy, and custom-role data-scope boundaries."""
    try:
        queryset.model._meta.get_field("company")
    except FieldDoesNotExist:
        scoped_queryset = queryset
    else:
        scope = get_company_scope(user, request)
        if scope.all_companies:
            scoped_queryset = queryset
        elif scope.company_id is None:
            scoped_queryset = queryset.none()
        else:
            scoped_queryset = queryset.filter(company_id=scope.company_id)

    from .sales_authorization import (
        scope_queryset_to_custom_role,
        scope_queryset_to_sales_hierarchy,
    )

    scoped_queryset = scope_queryset_to_sales_hierarchy(scoped_queryset, user)
    return scope_queryset_to_custom_role(scoped_queryset, user)


def can_access_company_record(user, record, request=None):
    """Return whether a user may access a record's company boundary."""
    try:
        record._meta.get_field("company")
    except (AttributeError, FieldDoesNotExist):
        company_access = True
    else:
        scope = get_company_scope(user, request)
        company_access = scope.all_companies or (
            scope.company_id is not None and record.company_id == scope.company_id
        )
    if not company_access:
        return False

    from .sales_authorization import (
        can_access_custom_role_record,
        can_access_sales_record,
    )

    return can_access_sales_record(user, record) and can_access_custom_role_record(
        user, record
    )
