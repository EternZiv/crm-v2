"""Sales hierarchy scope helpers shared by HTML views, APIs and exports."""

from functools import reduce
from operator import or_

from finlo.db.models import Q


SALES_ROLE_KEYS = {
    "SUPER_ADMIN",
    "HEAD_OF_SALES",
    "RSM",
    "SSM",
    "ASM",
    "BDO",
}

_SALES_MODULES = {"accounts", "contacts", "leads", "opportunities", "activity"}
_READ_ONLY_MODULES = {"dashboard", "reports"}
_HIERARCHY_MODELS = {"salesregion", "salesteam", "salesassignment"}


def _role_key(user):
    role = getattr(user, "role", None)
    return getattr(role, "system_key", None)


def sales_role_permission_decision(user, permission):
    """Return a sales-role permission ceiling, or ``None`` for other users."""
    role_key = _role_key(user)
    if role_key not in SALES_ROLE_KEYS:
        return None
    if getattr(user, "is_superuser", False) or role_key == "SUPER_ADMIN":
        return True

    try:
        app_label, codename = permission.split(".", 1)
    except (AttributeError, ValueError):
        return False

    action = next(
        (
            action
            for action in ("view", "add", "change", "delete")
            if codename.startswith(f"{action}_")
        ),
        None,
    )
    if action is None:
        return False

    model_name = codename[len(action) + 1 :]
    if model_name.startswith("own_"):
        model_name = model_name[4:]

    if app_label == "core":
        if model_name in _HIERARCHY_MODELS or model_name == "finlouser":
            return action == "view"
        return False

    if app_label in _READ_ONLY_MODULES:
        return action == "view"

    if app_label not in _SALES_MODULES:
        return False

    if action == "view":
        return True
    if action == "add":
        return app_label in {"leads", "activity"}
    if action == "change":
        return role_key in {"RSM", "SSM", "ASM", "BDO"}
    return False


def has_effective_permission(user, permission):
    """Check the user's assigned permission without exceeding the sales-role ceiling."""
    decision = sales_role_permission_decision(user, permission)
    if getattr(user, "is_superuser", False) or _role_key(user) == "SUPER_ADMIN":
        return True
    if decision is False:
        return False
    return user.has_perm(permission)


def get_sales_scope_user_ids(user):
    """Return scoped employee IDs, or ``None`` for non-sales roles."""
    role_key = _role_key(user)

    from finlo.contrib.utils.middlewares import get_current_request

    request = get_current_request()
    cache = None
    if request is not None and getattr(request, "method", None) in {"GET", "HEAD"}:
        cache = getattr(request, "_sales_scope_user_ids_cache", None)
        if cache is None:
            cache = {}
            request._sales_scope_user_ids_cache = cache
        cache_key = (user.pk, getattr(user, "company_id", None), role_key)
        if cache_key in cache:
            cached_scope = cache[cache_key]
            return set(cached_scope) if cached_scope is not None else None
    else:
        cache_key = None

    def remember(scope):
        if cache is not None:
            cache[cache_key] = frozenset(scope) if scope is not None else None
        return scope

    if role_key not in SALES_ROLE_KEYS:
        return remember(None)

    from finlo.contrib.core.models import SalesAssignment

    assignments = SalesAssignment.all_objects.filter(
        is_active=True, user__is_active=True
    )
    if role_key != "SUPER_ADMIN":
        assignments = assignments.filter(company_id=user.company_id)
    assignments = assignments.values_list("user_id", "region_id", "manager_id")
    assignment_rows = list(assignments)
    by_user = {user_id: (region_id, manager_id) for user_id, region_id, manager_id in assignment_rows}
    if role_key in {"SUPER_ADMIN", "HEAD_OF_SALES"}:
        return remember(set(by_user))
    own = by_user.get(user.pk)
    if own is None:
        return remember(set())

    if role_key == "RSM":
        return remember(
            {
                user_id
                for user_id, (region_id, _manager_id) in by_user.items()
                if region_id == own[0]
            }
        )
    if role_key == "BDO":
        return remember({user.pk} if own[1] is not None else set())

    children_by_manager = {}
    for user_id, (_region_id, manager_id) in by_user.items():
        if manager_id is not None:
            children_by_manager.setdefault(manager_id, []).append(user_id)

    allowed = {user.pk}
    pending = list(children_by_manager.get(user.pk, ()))
    while pending:
        report_id = pending.pop()
        if report_id in allowed:
            continue
        allowed.add(report_id)
        pending.extend(children_by_manager.get(report_id, ()))
    return remember(allowed)


def get_sales_scope_region_ids(user):
    """Return visible sales-region IDs, or ``None`` for non-sales roles."""
    role_key = _role_key(user)
    if role_key not in SALES_ROLE_KEYS:
        return None

    from finlo.contrib.core.models import SalesAssignment, SalesRegion

    if role_key == "SUPER_ADMIN":
        return set(SalesRegion.all_objects.values_list("pk", flat=True))
    if role_key == "HEAD_OF_SALES":
        return set(
            SalesRegion.all_objects.filter(company_id=user.company_id).values_list(
                "pk", flat=True
            )
        )
    assignment = (
        SalesAssignment.all_objects.filter(
            user_id=user.pk, company_id=user.company_id, is_active=True
        )
        .values_list("region_id", flat=True)
        .first()
    )
    return {assignment} if assignment else set()


def get_sales_scope_team_ids(user):
    """Return visible sales-team IDs, or ``None`` for non-sales roles."""
    role_key = _role_key(user)
    if role_key not in SALES_ROLE_KEYS:
        return None

    from finlo.contrib.core.models import SalesAssignment, SalesTeam

    company_teams = SalesTeam.all_objects.all()
    if role_key == "SUPER_ADMIN":
        return set(company_teams.values_list("pk", flat=True))
    company_teams = company_teams.filter(company_id=user.company_id)
    if role_key == "HEAD_OF_SALES":
        return set(company_teams.values_list("pk", flat=True))
    if role_key == "RSM":
        region_ids = get_sales_scope_region_ids(user) or set()
        return set(
            company_teams.filter(region_id__in=region_ids).values_list("pk", flat=True)
        )
    if role_key == "SSM":
        user_ids = get_sales_scope_user_ids(user) or set()
        return set(
            company_teams.filter(
                Q(senior_sales_manager_id__in=user_ids)
                | Q(area_sales_manager_id__in=user_ids)
            ).values_list("pk", flat=True)
        )
    if role_key == "ASM":
        return set(
            company_teams.filter(area_sales_manager_id=user.pk).values_list(
                "pk", flat=True
            )
        )
    return set(
        SalesAssignment.all_objects.filter(
            user_id=user.pk, company_id=user.company_id, is_active=True
        )
        .exclude(team_id__isnull=True)
        .values_list("team_id", flat=True)
    )


def scope_queryset_to_sales_hierarchy(queryset, user):
    """Narrow sales records and hierarchy rows to the caller's assigned scope."""
    role_key = _role_key(user)
    if role_key not in SALES_ROLE_KEYS:
        return queryset
    if role_key == "SUPER_ADMIN" or getattr(user, "is_superuser", False):
        return queryset

    model = queryset.model
    if model._meta.app_label == "core":
        if model._meta.model_name == "salesregion":
            return queryset.filter(pk__in=get_sales_scope_region_ids(user) or set())
        if model._meta.model_name == "salesteam":
            return queryset.filter(pk__in=get_sales_scope_team_ids(user) or set())
        if model._meta.model_name == "salesassignment":
            return queryset.filter(user_id__in=get_sales_scope_user_ids(user) or set())
        if model._meta.model_name == "finlouser":
            return queryset.filter(pk__in=get_sales_scope_user_ids(user) or set())

    owner_fields = getattr(model, "OWNER_FIELDS", ())
    if not owner_fields:
        return queryset

    user_ids = get_sales_scope_user_ids(user) or set()
    owner_queries = [Q(**{f"{field}__in": user_ids}) for field in owner_fields]
    return queryset.filter(reduce(or_, owner_queries)).distinct()


def can_access_sales_record(user, record):
    """Return whether a sales-role user may access this record's hierarchy scope."""
    if _role_key(user) not in SALES_ROLE_KEYS or _role_key(user) == "SUPER_ADMIN":
        return True

    model = record._meta
    if model.app_label == "core" and model.model_name == "salesregion":
        return record.pk in (get_sales_scope_region_ids(user) or set())
    if model.app_label == "core" and model.model_name == "salesteam":
        return record.pk in (get_sales_scope_team_ids(user) or set())
    if model.app_label == "core" and model.model_name == "salesassignment":
        return record.user_id in (get_sales_scope_user_ids(user) or set())
    if model.app_label == "core" and model.model_name == "finlouser":
        return record.pk in (get_sales_scope_user_ids(user) or set())

    owner_fields = getattr(record.__class__, "OWNER_FIELDS", ())
    if not owner_fields:
        return True

    allowed_ids = get_sales_scope_user_ids(user) or set()
    for field_name in owner_fields:
        value = getattr(record, field_name, None)
        if value is None:
            continue
        if hasattr(value, "all"):
            if value.filter(pk__in=allowed_ids).exists():
                return True
        elif getattr(value, "pk", None) in allowed_ids:
            return True
    return False
