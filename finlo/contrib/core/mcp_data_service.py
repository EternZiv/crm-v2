"""
FINLONEXA CRM v2 — Dynamic Permission-Aware MCP Data Service.

Provides a unified, secure data layer for Model Context Protocol (MCP) interactions,
reusing FINLO's native authentication, multi-tenant company isolation, sales hierarchy
scoping, dynamic role data scopes, and field-level permissions.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import date, datetime

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Avg, Count, F, Max, Min, Q, Sum

from finlo.api.mixins import scope_queryset_to_company, scope_queryset_to_permission
from finlo.contrib.core.sales_authorization import (
    has_effective_permission,
    scope_queryset_to_custom_role,
    scope_queryset_to_sales_hierarchy,
)
from finlo.contrib.core.utils import (
    filter_hidden_fields,
    get_field_permissions_for_model,
)

logger = logging.getLogger(__name__)

# Blacklist of sensitive field names that MUST NEVER be serialized or exposed via MCP
SENSITIVE_FIELD_PATTERNS = {
    "password",
    "token",
    "secret",
    "salt",
    "api_key",
    "session_key",
    "credentials",
    "otp",
    "totp",
    "auth_token",
    "refresh_token",
    "access_token",
}

# Controlled registry of exposable CRM modules
def _get_module_registry():
    from finlo_crm.leads.models import Lead
    from finlo_crm.opportunities.models import Opportunity
    from finlo_crm.accounts.models import Account
    from finlo_crm.contacts.models import Contact
    from finlo_crm.campaigns.models import Campaign
    from finlo.contrib.activity.models import Activity

    return {
        "leads": {
            "title": "Leads",
            "model": Lead,
            "app_label": "leads",
            "model_name": "lead",
            "description": "Sales leads, prospective customers, lead sources, and conversion status.",
            "search_fields": ["title", "email", "lead_company", "contact_number"],
            "default_sort": "-created_at",
        },
        "opportunities": {
            "title": "Deals & Opportunities",
            "model": Opportunity,
            "app_label": "opportunities",
            "model_name": "opportunity",
            "description": "Sales deals, pipelines, deal values, stages, and probabilities.",
            "search_fields": ["name", "account__name"],
            "default_sort": "-created_at",
        },
        "accounts": {
            "title": "Accounts / Companies",
            "model": Account,
            "app_label": "accounts",
            "model_name": "account",
            "description": "Client accounts, organizations, industry segments, and websites.",
            "search_fields": ["name", "website", "contact_number"],
            "default_sort": "-created_at",
        },
        "contacts": {
            "title": "Contacts",
            "model": Contact,
            "app_label": "contacts",
            "model_name": "contact",
            "description": "Individual business contacts, phone numbers, emails, and job titles.",
            "search_fields": ["first_name", "last_name", "email", "contact_number"],
            "default_sort": "-created_at",
        },
        "campaigns": {
            "title": "Campaigns",
            "model": Campaign,
            "app_label": "campaigns",
            "model_name": "campaign",
            "description": "Marketing campaigns, types, budgets, and expected revenues.",
            "search_fields": ["campaign_name"],
            "default_sort": "-created_at",
        },
        "activities": {
            "title": "Activities & Tasks",
            "model": Activity,
            "app_label": "activity",
            "model_name": "activity",
            "description": "Customer activities, meetings, calls, tasks, and follow-ups.",
            "search_fields": ["title", "subject"],
            "default_sort": "-created_at",
        },
    }


def is_sensitive_field(field_name: str) -> bool:
    """Return True if field name matches any known sensitive credential pattern."""
    fn_lower = field_name.lower()
    return any(pattern in fn_lower for pattern in SENSITIVE_FIELD_PATTERNS)


def get_authorized_queryset(user, module_name: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Build a strictly authorized queryset for a module enforcing:
    1. Active user authentication.
    2. Multi-tenant company isolation.
    3. Model view permissions (view_* vs view_own_*).
    4. Sales hierarchy scoping (SUPER_ADMIN, HEAD_OF_SALES, RSM, SSM, ASM, BDO).
    5. Dynamic custom role data scopes (company, owned, assigned, deny_all).
    """
    if not user or not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return None, "Authentication required: Active user session is required."

    registry = _get_module_registry()
    cfg = registry.get(module_name.lower().strip())
    if not cfg:
        return None, f"Module '{module_name}' is not supported or permitted for MCP access."

    model = cfg["model"]
    app_label = cfg["app_label"]
    model_name = cfg["model_name"]

    # Check effective permission
    has_global = has_effective_permission(user, f"{app_label}.view_{model_name}")
    has_own = has_effective_permission(user, f"{app_label}.view_own_{model_name}")

    if not has_global and not has_own:
        return None, f"Access denied: Your account lacks permission to view {cfg['title']}."

    # Base QuerySet with company isolation
    qs = model.objects.all()
    qs = scope_queryset_to_company(qs, user)

    # Superusers see full tenant scope
    if getattr(user, "is_superuser", False):
        return qs, None

    # Base permission scope (view vs view_own with OWNER_FIELDS and granted_access_filter)
    qs = scope_queryset_to_permission(qs, user, "view")

    # Sales hierarchy scoping (Head of Sales, RSM, SSM, ASM, BDO)
    qs = scope_queryset_to_sales_hierarchy(qs, user)

    # Custom role data scope
    qs = scope_queryset_to_custom_role(qs, user)

    return qs, None


def get_authorized_fields(user, model) -> List[str]:
    """
    Return a list of non-sensitive, visible field names for a model,
    enforcing FieldPermission 'hidden' restrictions for the given user.
    """
    all_fields = []
    for field in model._meta.get_fields():
        if field.is_relation and (field.many_to_many or field.one_to_many):
            continue
        fname = getattr(field, "name", None)
        if not fname or is_sensitive_field(fname):
            continue
        all_fields.append(fname)

    if getattr(user, "is_superuser", False):
        return all_fields

    # Apply field-level permissions filter
    visible_fields = filter_hidden_fields(user, model, all_fields)
    return visible_fields


def serialize_value(val: Any) -> Any:
    """Safely convert database and model values into JSON-serializable types."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if hasattr(val, "pk"):
        return str(val)
    return val


def get_user_accessible_modules(user) -> List[Dict[str, Any]]:
    """
    Return a comprehensive list of modules accessible to the user,
    their effective permission scopes, and total visible record counts.
    """
    registry = _get_module_registry()
    modules_summary = []

    for mod_key, cfg in registry.items():
        app_label = cfg["app_label"]
        model_name = cfg["model_name"]
        has_global = has_effective_permission(user, f"{app_label}.view_{model_name}")
        has_own = has_effective_permission(user, f"{app_label}.view_own_{model_name}")

        is_accessible = has_global or has_own or getattr(user, "is_superuser", False)
        if is_accessible:
            qs, err = get_authorized_queryset(user, mod_key)
            record_count = qs.count() if qs is not None else 0
            if getattr(user, "is_superuser", False) or has_global:
                scope_label = "All Company Records"
            elif has_own:
                scope_label = "Assigned & Hierarchy Records"
            else:
                scope_label = "Role Scoped"
        else:
            record_count = 0
            scope_label = "No Access"

        modules_summary.append({
            "key": mod_key,
            "title": cfg["title"],
            "description": cfg["description"],
            "is_accessible": is_accessible,
            "scope": scope_label,
            "record_count": record_count,
        })

    # Add Dashboard and Reports as advisory modules
    can_view_dash = has_effective_permission(user, "dashboard.view_dashboard") or getattr(user, "is_superuser", False)
    modules_summary.append({
        "key": "dashboard",
        "title": "Dashboard Analytics",
        "description": "Executive KPI cards, lead conversion statistics, and pipeline metrics.",
        "is_accessible": can_view_dash,
        "scope": "Authorized Metrics" if can_view_dash else "No Access",
        "record_count": 1 if can_view_dash else 0,
    })

    can_view_rep = has_effective_permission(user, "reports.view_report") or getattr(user, "is_superuser", False)
    modules_summary.append({
        "key": "reports",
        "title": "Reports & Funnels",
        "description": "Monthly revenue trends, stage conversion funnels, and performance reporting.",
        "is_accessible": can_view_rep,
        "scope": "Authorized Reports" if can_view_rep else "No Access",
        "record_count": 1 if can_view_rep else 0,
    })

    return modules_summary


def query_module_records(
    user,
    module_name: str,
    search: str = "",
    filters: Optional[Dict[str, Any]] = None,
    sort_by: str = "",
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Execute an authorized, bounded, field-filtered query on an exposable CRM module.
    Enforces tenant isolation, sales hierarchy, and field-level permissions.
    """
    qs, err = get_authorized_queryset(user, module_name)
    if err:
        raise PermissionError(err)

    registry = _get_module_registry()
    cfg = registry[module_name.lower().strip()]
    model = cfg["model"]

    # 1. Get allowed non-hidden, non-sensitive fields first
    allowed_fields = get_authorized_fields(user, model)
    allowed_fields_set = set(allowed_fields)

    # 2. Filter by search string if provided, restricting search to visible fields
    if search:
        search_q = Q()
        for sf in cfg.get("search_fields", []):
            try:
                base_f = sf.split("__")[0]
                if base_f in allowed_fields_set:
                    search_q |= Q(**{f"{sf}__icontains": search.strip()})
            except Exception:
                continue
        if search_q:
            qs = qs.filter(search_q)

    # 3. Apply strict sorting (only allow sorting on visible fields)
    sort_field = sort_by.strip() or cfg.get("default_sort", "-created_at")
    clean_sort = sort_field.lstrip("-")
    if clean_sort in allowed_fields_set:
        qs = qs.order_by(sort_field)
    else:
        qs = qs.order_by("-id")

    # 4. Clamped pagination
    clamped_limit = min(max(1, int(limit)), 100)
    clamped_offset = max(0, int(offset))
    total_count = qs.count()

    records = []
    for obj in qs[clamped_offset : clamped_offset + clamped_limit]:
        row = {}
        for f in allowed_fields:
            val = getattr(obj, f, None)
            row[f] = serialize_value(val)
        records.append(row)

    return {
        "module": module_name,
        "title": cfg["title"],
        "total_count": total_count,
        "offset": clamped_offset,
        "limit": clamped_limit,
        "visible_fields": allowed_fields,
        "records": records,
    }


def get_single_record(user, module_name: str, record_id: int) -> Dict[str, Any]:
    """
    Retrieve a single record detail view strictly scoped to the user's permissions.
    """
    qs, err = get_authorized_queryset(user, module_name)
    if err:
        raise PermissionError(err)

    registry = _get_module_registry()
    cfg = registry[module_name.lower().strip()]
    model = cfg["model"]

    record = qs.filter(id=record_id).first()
    if not record:
        raise ValueError(
            f"{cfg['title']} with ID {record_id} does not exist or you lack permission to view it."
        )

    allowed_fields = get_authorized_fields(user, model)
    data = {}
    for f in allowed_fields:
        val = getattr(record, f, None)
        data[f] = serialize_value(val)

    return {
        "module": module_name,
        "id": record.id,
        "data": data,
    }


def aggregate_module_data(
    user,
    module_name: str,
    group_by: str,
    metric: str = "count",
    metric_field: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform safe aggregated queries (counts, sums, averages) on authorized data.
    """
    qs, err = get_authorized_queryset(user, module_name)
    if err:
        raise PermissionError(err)

    registry = _get_module_registry()
    cfg = registry[module_name.lower().strip()]
    model = cfg["model"]

    allowed_fields = get_authorized_fields(user, model)
    clean_group = group_by.strip()
    if clean_group not in allowed_fields and not any(clean_group.startswith(f"{af}__") for af in allowed_fields):
        raise ValueError(f"Field '{group_by}' is not an authorized or exposable field for {cfg['title']}.")

    metric_lower = metric.lower().strip()
    if metric_lower == "count":
        agg_kwargs = {"metric_val": Count("id")}
    elif metric_lower == "sum" and metric_field:
        if metric_field not in allowed_fields:
            raise ValueError(f"Metric field '{metric_field}' is not authorized.")
        agg_kwargs = {"metric_val": Sum(metric_field)}
    elif metric_lower == "avg" and metric_field:
        if metric_field not in allowed_fields:
            raise ValueError(f"Metric field '{metric_field}' is not authorized.")
        agg_kwargs = {"metric_val": Avg(metric_field)}
    else:
        agg_kwargs = {"metric_val": Count("id")}

    records = (
        qs.values(category=F(clean_group) if hasattr(qs, "annotate") else clean_group)
        .annotate(**agg_kwargs)
        .order_by("-metric_val")
    )

    total_records = qs.count()
    categories = []
    values = []

    for r in records:
        cat = str(r["category"]) if r["category"] is not None else "Unassigned"
        v = r["metric_val"]
        categories.append(cat)
        values.append(float(v) if isinstance(v, (Decimal, int, float)) else v)

    return {
        "module": module_name,
        "title": f"{cfg['title']} Aggregation by {clean_group}",
        "total_records": total_records,
        "metric": metric_lower,
        "group_by": clean_group,
        "categories": categories,
        "series": values,
    }
