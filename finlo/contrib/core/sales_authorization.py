"""Sales hierarchy scope helpers shared by HTML views, APIs and exports."""

from functools import reduce
from operator import or_

from django.core.exceptions import FieldDoesNotExist

from finlo.db.models import Q


SALES_ROLE_KEYS = {
    "SUPER_ADMIN",
    "HEAD_OF_SALES",
    "RSM",
    "SSM",
    "ASM",
    "BDO",
}
ROLE_RECOVERY_PERMISSIONS = {
    "core.view_role",
    "core.add_role",
    "core.change_role",
    "core.delete_role",
    "auth.view_permission",
    "auth.add_permission",
    "auth.change_permission",
    "auth.delete_permission",
    "auth.view_group",
    "auth.add_group",
    "auth.change_group",
    "auth.delete_group",
}

_SALES_MODULES = {"accounts", "contacts", "leads", "opportunities", "activity"}
_READ_ONLY_MODULES = {"dashboard", "reports"}
_HIERARCHY_MODELS = {"salesregion", "salesteam", "salesassignment"}
_ROLE_PERMISSION_VERSION = 0


def invalidate_role_permission_cache(**_kwargs):
    """Invalidate request-local role permission snapshots after M2M changes."""
    global _ROLE_PERMISSION_VERSION
    _ROLE_PERMISSION_VERSION += 1


def _role_key(user):
    role = getattr(user, "role", None)
    return getattr(role, "system_key", None)


def is_super_admin_or_superuser(user):
    """Return True for active Django or protected application Super Admins."""
    if (
        not user
        or not getattr(user, "is_authenticated", False)
        or not getattr(user, "is_active", False)
    ):
        return False
    if getattr(user, "is_superuser", False):
        return True
    role = getattr(user, "role", None)
    return bool(
        role
        and getattr(role, "is_active", False)
        and getattr(role, "system_key", None) == "SUPER_ADMIN"
    )


def sales_role_permission_decision(user, permission):
    """Return a sales-role permission ceiling, or ``None`` for other users."""
    role_key = _role_key(user)
    if role_key not in SALES_ROLE_KEYS:
        return None
    if not getattr(getattr(user, "role", None), "is_active", False):
        return False
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
        if model_name in {
            "finlouser",
            "company",
            *_HIERARCHY_MODELS,
        }:
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


def role_permission_grant_allowed(role, permission):
    """Return whether a role may explicitly grant this permission."""
    permission_key = (
        f"{permission.content_type.app_label}.{permission.codename}"
    )
    if permission_key in ROLE_RECOVERY_PERMISSIONS:
        return role.system_key == "SUPER_ADMIN"
    if role.system_key == "SUPER_ADMIN":
        return True
    app_label = permission.content_type.app_label
    model_name = permission.content_type.model
    codename = permission.codename
    if app_label == "auth":
        return False
    if app_label == "core":
        if model_name in {
            "company",
            "finlouser",
            *_HIERARCHY_MODELS,
        }:
            return codename.startswith("view_")
        if model_name in {"role", "role_datascope", "fieldpermission"}:
            return False
    if role.system_key not in SALES_ROLE_KEYS:
        return True
    if app_label not in _SALES_MODULES:
        return False
    model = permission.content_type.model_class()
    return bool(model and getattr(model, "OWNER_FIELDS", ()))


def _get_role_permission_sets(user, role):
    """Load role grants and denials once for the lifetime of this request."""
    cache_key = getattr(role, "pk", None)
    cached = getattr(user, "_finlo_role_permission_sets", None)
    if cached and cached[0] == cache_key and cached[1] == _ROLE_PERMISSION_VERSION:
        return cached[2], cached[3]

    denied_permissions = {
        f"{permission.content_type.app_label}.{permission.codename}"
        for permission in role.denied_permissions.select_related("content_type").all()
    }
    granted_permissions = set()
    for permission in role.permissions.select_related("content_type").all():
        permission_key = f"{permission.content_type.app_label}.{permission.codename}"
        if role_permission_grant_allowed(role, permission):
            granted_permissions.add(permission_key)

    user._finlo_role_permission_sets = (
        cache_key,
        _ROLE_PERMISSION_VERSION,
        denied_permissions,
        granted_permissions,
    )
    return denied_permissions, granted_permissions


def has_effective_permission(user, permission, obj=None):
    """Apply role denials and grants before the existing user permission fallback."""
    if not getattr(user, "is_authenticated", False) or not getattr(
        user, "is_active", False
    ):
        return False
    if getattr(user, "is_superuser", False):
        return True

    role = getattr(user, "role", None)
    if role and not role.is_active:
        return False

    role_key = _role_key(user)
    role_grant = False
    if role:
        if not isinstance(permission, str) or "." not in permission:
            return False
        denied_permissions, granted_permissions = _get_role_permission_sets(
            user, role
        )
        if (
            permission in denied_permissions
            and permission not in ROLE_RECOVERY_PERMISSIONS
        ):
            return False
        role_grant = permission in granted_permissions

    decision = sales_role_permission_decision(user, permission)
    if decision is False and not role_grant:
        return False
    if role_key == "SUPER_ADMIN":
        return True

    if role_grant:
        if obj is None:
            return True
        if not getattr(obj, "pk", None):
            return False
        from finlo.contrib.core.authorization import can_access_company_record

        return can_access_company_record(user, obj)

    base_permission_checker = getattr(user, "_has_base_permission", None)
    if base_permission_checker:
        return base_permission_checker(permission, obj)
    return user.has_perm(permission, obj)


def _custom_role_scope(user, model):
    """Return a configured scope for a custom role, defaulting to deny."""
    role = getattr(user, "role", None)
    if (
        not role
        or role.system_key
        or getattr(user, "is_superuser", False)
        or not getattr(user, "is_authenticated", False)
    ):
        return None
    if not role.is_active:
        return "deny_all"

    from django.contrib.contenttypes.models import ContentType
    from finlo.contrib.core.models import RoleDataScope

    content_type = ContentType.objects.get_for_model(model)
    return (
        RoleDataScope.all_objects.filter(
            role=role, content_type=content_type, is_active=True
        )
        .values_list("scope", flat=True)
        .first()
        or RoleDataScope.DENY_ALL
    )


def _owned_record_filter(model, user):
    owner_fields = getattr(model, "OWNER_FIELDS", ())
    if not owner_fields:
        return None
    return reduce(
        or_,
        (Q(**{f"{field}__in": [user.pk]}) for field in owner_fields),
    )


def scope_queryset_to_custom_role(queryset, user):
    """Apply the explicit per-model scope for a configurable role."""
    scope = _custom_role_scope(user, queryset.model)
    if scope is None:
        return queryset
    if scope == "deny_all":
        return queryset.none()
    if scope == "company":
        try:
            queryset.model._meta.get_field("company")
        except FieldDoesNotExist:
            return queryset.none()
        if not getattr(user, "company_id", None):
            return queryset.none()
        return queryset.filter(company_id=user.company_id)

    owned_filter = _owned_record_filter(queryset.model, user)
    if scope == "owned":
        return queryset.filter(owned_filter).distinct() if owned_filter else queryset.none()
    if scope == "assigned":
        filters = [item for item in (owned_filter,) if item is not None]
        from finlo.contrib.generics.views.helpers.queryset_utils import (
            get_granted_access_filter,
        )

        granted_filter = get_granted_access_filter(queryset.model, user, "view")
        if granted_filter is not None:
            filters.append(granted_filter)
        if not filters:
            return queryset.none()
        access_filter = reduce(or_, filters)
        try:
            queryset.model._meta.get_field("company")
        except FieldDoesNotExist:
            pass
        else:
            if not getattr(user, "company_id", None):
                return queryset.none()
            access_filter &= Q(company_id=user.company_id)
        return queryset.filter(access_filter).distinct()
    return queryset.none()


def can_access_custom_role_record(user, record):
    """Check whether a custom role's configured model scope includes a record."""
    scope = _custom_role_scope(user, record.__class__)
    if scope is None:
        return True
    if scope == "deny_all":
        return False
    if scope == "company":
        try:
            record._meta.get_field("company")
        except FieldDoesNotExist:
            return False
        return bool(
            getattr(user, "company_id", None)
            and getattr(record, "company_id", None) == user.company_id
        )

    if scope == "owned":
        owner_filter = _owned_record_filter(record.__class__, user)
        if owner_filter is None:
            return False
        return record.__class__._base_manager.filter(pk=record.pk).filter(
            owner_filter
        ).exists()

    if scope == "assigned":
        if _record_matches_owner_filter(user, record):
            return True
        from finlo.contrib.generics.views.helpers.queryset_utils import (
            get_granted_access_filter,
        )

        granted_filter = get_granted_access_filter(
            record.__class__, user, "view"
        )
        if granted_filter is None:
            return False
        queryset = record.__class__._base_manager.filter(pk=record.pk).filter(
            granted_filter
        )
        try:
            record._meta.get_field("company")
        except FieldDoesNotExist:
            pass
        else:
            if not getattr(user, "company_id", None):
                return False
            queryset = queryset.filter(company_id=user.company_id)
        return queryset.exists()
    return False


def _record_matches_owner_filter(user, record):
    owner_filter = _owned_record_filter(record.__class__, user)
    return bool(
        owner_filter is not None
        and record.__class__._base_manager.filter(pk=record.pk)
        .filter(owner_filter)
        .exists()
    )


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
        frozen = frozenset(scope) if scope is not None else None
        if cache is not None:
            cache[cache_key] = frozen
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
    if not getattr(getattr(user, "role", None), "is_active", False):
        return queryset.none()
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
    if _role_key(user) not in SALES_ROLE_KEYS:
        return True
    if not getattr(getattr(user, "role", None), "is_active", False):
        return False
    if _role_key(user) == "SUPER_ADMIN" or getattr(user, "is_superuser", False):
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
