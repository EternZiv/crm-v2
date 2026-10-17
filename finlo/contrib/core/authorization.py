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

    if user.is_superuser or getattr(getattr(user, "role", None), "system_key", None) == "SUPER_ADMIN":
        return CompanyScope(company_id=None, all_companies=True)

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
    """Apply the user's company boundary to models with a ``company`` field."""
    try:
        queryset.model._meta.get_field("company")
    except FieldDoesNotExist:
        return queryset

    scope = get_company_scope(user, request)
    if scope.all_companies:
        scoped_queryset = queryset
    elif scope.company_id is None:
        scoped_queryset = queryset.none()
    else:
        scoped_queryset = queryset.filter(company_id=scope.company_id)

    from .sales_authorization import scope_queryset_to_sales_hierarchy

    return scope_queryset_to_sales_hierarchy(scoped_queryset, user)


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

    from .sales_authorization import can_access_sales_record

    return can_access_sales_record(user, record)
