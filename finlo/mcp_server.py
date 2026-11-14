"""
Finlo CRM Read-Only Model Context Protocol (MCP) Server.

Provides AI assistants (Claude, ChatGPT, Cursor, etc.) with secure, read-only
access to Finlo CRM data, user-scoped permissions, and aggregated analytics
formatted specifically for charting, visualizations, and dashboards.
"""

import os
import sys

# Ensure root workspace directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import json
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

# Bootstrap Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finlo.settings")
import django

django.setup()

from django.db.models import Avg, Count, F, Q, Sum

try:
    from mcp.server.fastmcp import FastMCP as MCPServer
except ImportError:
    try:
        from mcp.server.mcpserver import MCPServer  # type: ignore
    except ImportError:
        import inspect

        class MCPServer:  # type: ignore
            """Production-grade fallback STDIO MCP server when 'mcp' package is not installed."""
            def __init__(self, name: str, instructions: str = "", version: str = "1.0.0"):
                self.name = name
                self.instructions = instructions
                self.version = version
                self.tools: Dict[str, Dict[str, Any]] = {}

            def tool(self, name: Optional[str] = None, description: Optional[str] = None):
                def decorator(fn: Callable):
                    tool_name = name or fn.__name__
                    doc = description or (inspect.getdoc(fn) or "").strip()
                    sig = inspect.signature(fn)
                    properties = {}
                    required = []

                    type_map = {
                        str: "string",
                        int: "integer",
                        float: "number",
                        bool: "boolean",
                        list: "array",
                        dict: "object",
                    }

                    for p_name, param in sig.parameters.items():
                        p_type = "string"
                        if param.annotation != inspect.Parameter.empty:
                            p_type = type_map.get(param.annotation, "string")
                        p_prop = {"type": p_type}
                        if param.default is inspect.Parameter.empty:
                            required.append(p_name)
                        else:
                            p_prop["default"] = param.default
                        properties[p_name] = p_prop

                    input_schema = {
                        "type": "object",
                        "properties": properties,
                    }
                    if required:
                        input_schema["required"] = required

                    self.tools[tool_name] = {
                        "fn": fn,
                        "schema": {
                            "name": tool_name,
                            "description": doc,
                            "inputSchema": input_schema,
                        },
                    }
                    return fn
                return decorator

            def run(self, transport: str = "stdio"):
                if hasattr(sys.stdin, "reconfigure"):
                    try:
                        sys.stdin.reconfigure(encoding="utf-8")
                    except Exception:
                        pass
                if hasattr(sys.stdout, "reconfigure"):
                    try:
                        sys.stdout.reconfigure(encoding="utf-8")
                    except Exception:
                        pass

                for raw_line in sys.stdin:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except Exception:
                        resp = {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {"code": -32700, "message": "Parse error: Invalid JSON"},
                        }
                        sys.stdout.write(json.dumps(resp) + "\n")
                        sys.stdout.flush()
                        continue

                    if not isinstance(msg, dict):
                        resp = {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {"code": -32600, "message": "Invalid Request: expected JSON object"},
                        }
                        sys.stdout.write(json.dumps(resp) + "\n")
                        sys.stdout.flush()
                        continue

                    req_id = msg.get("id")
                    method = msg.get("method")
                    params = msg.get("params") or {}

                    # JSON-RPC 2.0: If id is missing, the request is a notification. Server MUST NOT reply.
                    if req_id is None:
                        continue

                    if method == "initialize":
                        resp = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                                "serverInfo": {"name": self.name, "version": self.version},
                                "instructions": self.instructions,
                            },
                        }
                    elif method == "ping":
                        resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
                    elif method == "tools/list":
                        resp = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"tools": [t["schema"] for t in self.tools.values()]},
                        }
                    elif method == "resources/list":
                        resp = {"jsonrpc": "2.0", "id": req_id, "result": {"resources": []}}
                    elif method == "prompts/list":
                        resp = {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []}}
                    elif method == "tools/call":
                        t_name = params.get("name")
                        t_args = params.get("arguments") or {}
                        if t_name not in self.tools:
                            resp = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {
                                    "content": [{"type": "text", "text": f"Error: Tool '{t_name}' not found."}],
                                    "isError": True,
                                },
                            }
                        else:
                            try:
                                target_fn = self.tools[t_name]["fn"]
                                sig = inspect.signature(target_fn)
                                coerced_args = {}
                                for k, v in t_args.items():
                                    param = sig.parameters.get(k)
                                    if param and param.annotation in (int, float, bool, str) and v is not None:
                                        try:
                                            if param.annotation == bool and isinstance(v, str):
                                                coerced_args[k] = v.lower() in ("true", "1", "yes")
                                            else:
                                                coerced_args[k] = param.annotation(v)
                                        except (ValueError, TypeError):
                                            coerced_args[k] = v
                                    else:
                                        coerced_args[k] = v

                                res = target_fn(**coerced_args)
                                res_str = json.dumps(res, default=str, indent=2) if isinstance(res, (dict, list)) else str(res)
                                resp = {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "result": {
                                        "content": [{"type": "text", "text": res_str}],
                                        "isError": False,
                                    },
                                }
                            except Exception as err:
                                resp = {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "result": {
                                        "content": [{"type": "text", "text": f"Error: {type(err).__name__}: {err}"}],
                                        "isError": True,
                                    },
                                }
                    else:
                        resp = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"code": -32601, "message": f"Method '{method}' not found"},
                        }

                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()

from finlo.auth.models import User
from finlo.contrib.activity.models import Activity
from finlo_crm.accounts.models import Account
from finlo_crm.campaigns.models import Campaign
from finlo_crm.contacts.models import Contact
from finlo_crm.leads.models import Lead
from finlo_crm.opportunities.models import Opportunity

from finlo.contrib.core.mcp_data_service import (
    aggregate_module_data,
    get_authorized_fields,
    get_authorized_queryset,
    get_single_record,
    get_user_accessible_modules,
    query_module_records,
)

# Initialize MCP Server
server = MCPServer(
    name="finlo-crm-readonly",
    instructions=(
        "You are an intelligent enterprise CRM analytics assistant connected to Finlo CRM. "
        "This MCP server is STRICTLY READ-ONLY and STRICTLY AUTHENTICATED. "
        "You cannot access any CRM data without logging in with your account ID (username/email) and password. "
        "Use the 'login_crm(username_or_email, password)' tool to authenticate, or configure "
        "FINLO_USERNAME and FINLO_PASSWORD in your MCP server settings. "
        "Once authenticated, all queries are locked to that specific user account and tenant. "
        "Access to any other account's private data is strictly restricted."
    ),
    version="1.1.0",
)


# ---------------------------------------------------------------------------
# Security & Account Scoping Helpers
# ---------------------------------------------------------------------------

_ACTIVE_USER: Optional[User] = None


def _authenticate_credentials(username_or_email: str, password: str) -> Optional[User]:
    """Validate username or email with password against Django auth."""
    if not username_or_email or not password:
        return None
    ident = username_or_email.strip()
    user = User.objects.filter(
        Q(username__iexact=ident) | Q(email__iexact=ident)
    ).first()
    if user and user.check_password(password) and user.is_active:
        return user
    return None


def _get_scoped_user() -> User:
    """
    Retrieve the strictly authenticated user for permission and tenant scoping.
    If not already logged in, checks environment variables FINLO_USERNAME & FINLO_PASSWORD.
    Throws PermissionError if unauthenticated.
    """
    global _ACTIVE_USER
    if _ACTIVE_USER:
        try:
            _ACTIVE_USER.refresh_from_db()
            if not _ACTIVE_USER.is_active:
                _ACTIVE_USER = None
                raise PermissionError("Authentication required: Active user session is required.")
            # Invalidate all cached user permissions, role scopes, and sales hierarchy caches
            # to guarantee that role revocations, reassignments, or field permission updates
            # immediately take effect without serving stale data.
            for cache_attr in (
                "_sales_scope_user_ids_cache",
                "_sales_scope_region_ids_cache",
                "_sales_scope_team_ids_cache",
                "_custom_role_scope_cache",
                "_field_perms_model_cache",
                "_effective_permissions_cache",
            ):
                if hasattr(_ACTIVE_USER, cache_attr):
                    delattr(_ACTIVE_USER, cache_attr)
            return _ACTIVE_USER
        except User.DoesNotExist:
            _ACTIVE_USER = None
            raise PermissionError("Authentication required: Active user session is required.")

    env_user = (
        os.environ.get("FINLO_USERNAME", "").strip()
        or os.environ.get("FINLO_USER", "").strip()
        or os.environ.get("FINLO_ACCOUNT_EMAIL", "").strip()
    )
    env_pass = os.environ.get("FINLO_PASSWORD", "").strip()

    if env_user and env_pass:
        authenticated = _authenticate_credentials(env_user, env_pass)
        if authenticated:
            _ACTIVE_USER = authenticated
            return _ACTIVE_USER
        raise PermissionError(
            f"Authentication failed: Invalid credentials provided in environment for '{env_user}'. "
            "Please check FINLO_USERNAME and FINLO_PASSWORD, or call login_crm(username_or_email, password)."
        )

    raise PermissionError(
        "Authentication required: You must log in with your Finlo CRM ID/email and password. "
        "Please call the 'login_crm(username_or_email, password)' tool, or configure "
        "FINLO_USERNAME and FINLO_PASSWORD in your MCP server settings."
    )


def _get_scoped_leads(user: User):
    qs, err = get_authorized_queryset(user, "leads")
    if err or qs is None:
        return Lead.objects.none()
    return qs.select_related("lead_status", "lead_owner", "company")


def _get_scoped_opportunities(user: User):
    qs, err = get_authorized_queryset(user, "opportunities")
    if err or qs is None:
        return Opportunity.objects.none()
    return qs.select_related("stage", "owner", "account", "company")


def _get_scoped_contacts(user: User):
    qs, err = get_authorized_queryset(user, "contacts")
    if err or qs is None:
        return Contact.objects.none()
    return qs.select_related("contact_owner", "company")


def _get_scoped_accounts(user: User):
    qs, err = get_authorized_queryset(user, "accounts")
    if err or qs is None:
        return Account.objects.none()
    return qs.select_related("account_owner", "company")


def _get_scoped_campaigns(user: User):
    qs, err = get_authorized_queryset(user, "campaigns")
    if err or qs is None:
        return Campaign.objects.none()
    return qs.select_related("campaign_owner", "company")


def _get_scoped_activities(user: User):
    qs, err = get_authorized_queryset(user, "activities")
    if err or qs is None:
        return Activity.objects.none()
    return qs.select_related("owner", "company")


def _compute_user_scopes(user: User) -> Dict[str, str]:
    """Compute accurate permission scopes based on effective permissions and role hierarchy."""
    modules = get_user_accessible_modules(user)
    scope_dict = {}
    for m in modules:
        key = m["key"]
        if not m["is_accessible"]:
            scope_dict[key] = "none"
        elif user.is_superuser:
            scope_dict[key] = "all"
        elif m["scope"] == "All Company Records":
            scope_dict[key] = "all"
        elif m["scope"] == "Assigned & Hierarchy Records":
            scope_dict[key] = "hierarchy"
        else:
            scope_dict[key] = "role_scoped"
    return scope_dict


# ---------------------------------------------------------------------------
# MCP Authentication & Read-Only Tools
# ---------------------------------------------------------------------------

@server.tool()
def login_crm(username_or_email: str, password: str) -> Dict[str, Any]:
    """
    Authenticate into Finlo CRM using your account username/email and password.
    Once authenticated, all queries are strictly locked to your account permissions and company tenant.
    Access to any other account's private data is strictly restricted.
    """
    global _ACTIVE_USER
    user = _authenticate_credentials(username_or_email, password)
    if not user:
        raise PermissionError("Authentication failed: Invalid username/email or password.")

    _ACTIVE_USER = user
    company_name = user.company.name if user.company else "Global / Multi-tenant"
    roles = list(user.groups.values_list("name", flat=True))
    role_name = str(getattr(user, "role", "Standard User"))

    return {
        "status": "authenticated",
        "message": f"Successfully authenticated as {user.username} ({user.email}).",
        "username": user.username,
        "email": user.email,
        "full_name": user.get_full_name() or user.username,
        "is_superuser": user.is_superuser,
        "company": company_name,
        "role": role_name,
        "roles": roles,
        "scopes": _compute_user_scopes(user),
        "isolation_policy": (
            "Superuser: Full Company Tenant Access"
            if user.is_superuser
            else f"Role-Scoped: Strictly scoped to {role_name} sales hierarchy & company isolation."
        ),
    }


@server.tool()
def logout_crm() -> Dict[str, str]:
    """
    Log out from Finlo CRM and clear the active authenticated session.
    """
    global _ACTIVE_USER
    _ACTIVE_USER = None
    return {"status": "logged_out", "message": "Successfully logged out from Finlo CRM session."}


@server.tool()
def get_account_profile() -> Dict[str, Any]:
    """
    Get identity, tenant company, role permissions, and access scope for the currently authenticated CRM account.
    """
    user = _get_scoped_user()
    company_name = user.company.name if user.company else "Global / Multi-tenant"
    roles = list(user.groups.values_list("name", flat=True))
    role_name = str(getattr(user, "role", "Standard User"))

    return {
        "status": "authenticated",
        "username": user.username,
        "email": user.email,
        "full_name": user.get_full_name() or user.username,
        "is_superuser": user.is_superuser,
        "company": company_name,
        "role": role_name,
        "roles": roles,
        "scopes": _compute_user_scopes(user),
        "mode": "READ_ONLY",
        "scope_summary": (
            "Superuser access (All Company Data)"
            if user.is_superuser
            else f"Role-scoped access ({role_name}) within company: {company_name}"
        ),
    }


@server.tool()
def get_crm_kpis() -> Dict[str, Any]:
    """
    Get high-level executive KPI scorecards across Leads, Opportunities, Accounts, and Contacts.
    Returns metrics formatted for rendering KPI metric cards and executive dashboards.
    Enforces tenant isolation, sales hierarchy, and field-level permissions.
    """
    user = _get_scoped_user()
    accessible_modules = {m["key"]: m for m in get_user_accessible_modules(user) if m["is_accessible"]}
    if not accessible_modules:
        raise PermissionError("Access denied: Your account lacks permission to view any CRM modules.")

    leads_qs = _get_scoped_leads(user)
    opps_qs = _get_scoped_opportunities(user)
    contacts_qs = _get_scoped_contacts(user)
    accounts_qs = _get_scoped_accounts(user)

    total_leads = leads_qs.count()
    converted_leads = leads_qs.filter(is_convert=True).count()
    lead_conv_rate = round((converted_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

    total_opps = opps_qs.count()

    allowed_opp_fields = set(get_authorized_fields(user, Opportunity))
    can_view_amount = "amount" in allowed_opp_fields

    if can_view_amount and total_opps > 0:
        opp_stats = opps_qs.aggregate(
            total_val=Sum("amount"),
            avg_val=Avg("amount"),
        )
        total_val = float(opp_stats["total_val"] or 0.0)
        avg_val = round(float(opp_stats["avg_val"] or 0.0), 2)

        won_deals = opps_qs.filter(
            Q(stage__name__icontains="won") | Q(stage__name__icontains="closed won")
        )
        won_count = won_deals.count()
        won_val = float(won_deals.aggregate(v=Sum("amount"))["v"] or 0.0)
    else:
        total_val = 0.0
        avg_val = 0.0
        won_deals = opps_qs.filter(
            Q(stage__name__icontains="won") | Q(stage__name__icontains="closed won")
        )
        won_count = won_deals.count()
        won_val = 0.0

    win_rate = round((won_count / total_opps * 100), 1) if total_opps > 0 else 0.0

    total_accounts = accounts_qs.count()
    total_contacts = contacts_qs.count()

    return {
        "account_used": user.email or user.username,
        "company": str(user.company),
        "total_leads": total_leads,
        "converted_leads": converted_leads,
        "lead_conversion_rate": lead_conv_rate,
        "total_opportunities": total_opps,
        "total_pipeline_value": total_val,
        "total_pipeline_value_formatted": f"${total_val:,.2f}" if can_view_amount else "[RESTRICTED]",
        "total_closed_won_revenue": won_val,
        "total_closed_won_revenue_formatted": f"${won_val:,.2f}" if can_view_amount else "[RESTRICTED]",
        "win_rate_percent": win_rate,
        "average_deal_size": avg_val,
        "total_accounts": total_accounts,
        "total_contacts": total_contacts,
        "kpi_cards": [
            {
                "title": "Total Pipeline Value",
                "value": f"${total_val:,.2f}" if can_view_amount else "[RESTRICTED]",
                "metric": total_val,
                "subtext": f"{total_opps} Active Deals",
            },
            {
                "title": "Closed Won Revenue",
                "value": f"${won_val:,.2f}" if can_view_amount else "[RESTRICTED]",
                "metric": won_val,
                "subtext": f"{won_count} Closed Won Deals",
            },
            {
                "title": "Opportunity Win Rate",
                "value": f"{win_rate}%",
                "metric": win_rate,
                "subtext": f"{won_count} of {total_opps} deals won",
            },
            {
                "title": "Average Deal Size",
                "value": f"${avg_val:,.2f}" if can_view_amount else "[RESTRICTED]",
                "metric": avg_val,
                "subtext": "Per opportunity",
            },
            {
                "title": "Total Leads",
                "value": str(total_leads),
                "metric": total_leads,
                "subtext": f"{converted_leads} Converted ({lead_conv_rate}%)",
            },
            {
                "title": "Total Accounts",
                "value": str(total_accounts),
                "metric": total_accounts,
                "subtext": f"{total_contacts} Contacts registered",
            },
        ],
    }


@server.tool()
def get_leads_chart_data(group_by: str = "status") -> Dict[str, Any]:
    """
    Get aggregated Lead analytics data structured for generating charts (Bar, Pie, or Donut).
    group_by options: 'status', 'source', or 'industry'.
    Enforces sales hierarchy, company isolation, and field-level permissions.
    """
    user = _get_scoped_user()
    qs, err = get_authorized_queryset(user, "leads")
    if err or qs is None:
        raise PermissionError(err or "Access denied: Your account lacks permission to view Leads.")

    group_by_clean = (group_by or "status").lower().strip()
    group_field_map = {
        "status": ("lead_status__name", "lead_status"),
        "source": ("lead_source", "lead_source"),
        "industry": ("industry__name", "industry"),
    }
    if group_by_clean not in group_field_map:
        raise ValueError(
            f"Unsupported group_by '{group_by}'. Supported options: 'status', 'source', 'industry'."
        )

    field_path, base_field = group_field_map[group_by_clean]

    # Verify field-level permission: grouping on a hidden field is strictly forbidden
    allowed_fields = set(get_authorized_fields(user, Lead))
    if base_field not in allowed_fields:
        raise PermissionError(
            f"Access denied: Field '{base_field}' is hidden or restricted by administrator policy for your role."
        )

    leads_qs = qs.select_related("lead_status", "industry")
    total_leads = leads_qs.count()

    records = (
        leads_qs.values(category=F(field_path))
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    categories = []
    counts = []
    markdown_lines = [f"| {group_by.title()} | Lead Count | Share % |", "|---|---|---|"]

    for r in records:
        name = r["category"] or "Unassigned / None"
        cnt = r["count"]
        pct = round((cnt / total_leads * 100), 1) if total_leads > 0 else 0.0
        categories.append(name)
        counts.append(cnt)
        markdown_lines.append(f"| {name} | {cnt} | {pct}% |")

    return {
        "chart_type": "pie" if group_by_clean in ("status",) else "bar",
        "title": f"Leads Breakdown by {group_by.title()}",
        "total_records": total_leads,
        "categories": categories,
        "series": [
            {
                "name": "Leads",
                "data": counts,
            }
        ],
        "markdown_table": "\n".join(markdown_lines),
        "recommended_visual": (
            f"Use a Pie or Donut chart to display proportion of leads by {group_by}, "
            "or a Horizontal Bar chart if there are more than 5 categories."
        ),
    }


@server.tool()
def get_pipeline_funnel_chart() -> Dict[str, Any]:
    """
    Get Sales Pipeline Funnel chart data showing deal stages, deal volume, and conversion value.
    Structured for rendering Funnel charts or stacked stage progress bars.
    Enforces sales hierarchy, company isolation, and field-level permissions.
    """
    user = _get_scoped_user()
    qs, err = get_authorized_queryset(user, "opportunities")
    if err or qs is None:
        raise PermissionError(err or "Access denied: Your account lacks permission to view Opportunities.")

    allowed_fields = set(get_authorized_fields(user, Opportunity))
    if "stage" not in allowed_fields:
        raise PermissionError("Access denied: Opportunity stage is restricted for your account.")

    can_view_amount = "amount" in allowed_fields
    opps_qs = qs.select_related("stage")

    stages_data = (
        opps_qs.values(
            stage_name=F("stage__name"),
            stage_order=F("stage__order"),
            stage_prob=F("stage__probability"),
        )
        .annotate(
            count=Count("id"),
            total_amount=Sum("amount") if can_view_amount else Count("id"),
        )
        .order_by("stage_order", "stage_prob")
    )

    stages = []
    deal_counts = []
    deal_amounts = []
    markdown_lines = ["| Stage | Deals | Total Value ($) | Avg Probability |", "|---|---|---|---|"]

    total_pipeline_val = 0.0
    for s in stages_data:
        name = s["stage_name"] or "Unassigned"
        cnt = s["count"]
        amt = float(s["total_amount"] or 0.0) if can_view_amount else 0.0
        prob = s["stage_prob"] or 0
        total_pipeline_val += amt

        stages.append(name)
        deal_counts.append(cnt)
        deal_amounts.append(amt)
        amt_str = f"${amt:,.2f}" if can_view_amount else "[RESTRICTED]"
        markdown_lines.append(f"| {name} | {cnt} | {amt_str} | {prob}% |")

    return {
        "chart_type": "funnel",
        "title": "Sales Pipeline Stage Funnel",
        "total_deals": opps_qs.count(),
        "total_pipeline_value": f"${total_pipeline_val:,.2f}" if can_view_amount else "[RESTRICTED]",
        "stages": stages,
        "series": [
            {"name": "Deal Count", "data": deal_counts},
            {"name": "Total Value ($)", "data": deal_amounts},
        ],
        "markdown_table": "\n".join(markdown_lines),
        "recommended_visual": "Render as a multi-stage Sales Funnel chart or Step/Bar chart showing volume from top of funnel to closed deals.",
    }


@server.tool()
def get_revenue_trend_chart(months: int = 6) -> Dict[str, Any]:
    """
    Get Monthly Revenue and Opportunity trend data over the last N months.
    Structured for rendering Line or Area charts.
    Enforces sales hierarchy, company isolation, and field-level permissions.
    """
    user = _get_scoped_user()
    qs_opps, err_opps = get_authorized_queryset(user, "opportunities")
    qs_leads, err_leads = get_authorized_queryset(user, "leads")

    if (err_opps or qs_opps is None) and (err_leads or qs_leads is None):
        raise PermissionError("Access denied: Your account lacks permission to view both Opportunities and Leads.")

    opps_qs = qs_opps.select_related("stage") if qs_opps is not None else Opportunity.objects.none()
    leads_qs = qs_leads if qs_leads is not None else Lead.objects.none()

    allowed_opp_fields = set(get_authorized_fields(user, Opportunity)) if qs_opps is not None else set()
    can_view_amount = "amount" in allowed_opp_fields

    now = datetime.now()
    month_labels = []
    lead_trends = []
    won_revenue_trends = []
    pipeline_added_trends = []

    markdown_lines = ["| Month | New Leads | Deals Created | Won Revenue ($) |", "|---|---|---|---|"]

    for i in range(months - 1, -1, -1):
        target_date = now - timedelta(days=i * 30)
        year = target_date.year
        month = target_date.month
        label = target_date.strftime("%b %Y")
        month_labels.append(label)

        monthly_leads = leads_qs.filter(created_at__year=year, created_at__month=month).count()
        lead_trends.append(monthly_leads)

        monthly_opps = opps_qs.filter(created_at__year=year, created_at__month=month)
        if can_view_amount:
            opp_amt = float(monthly_opps.aggregate(s=Sum("amount"))["s"] or 0.0)
        else:
            opp_amt = 0.0
        pipeline_added_trends.append(opp_amt)

        monthly_won = monthly_opps.filter(
            Q(stage__name__icontains="won") | Q(stage__name__icontains="closed won")
        )
        if can_view_amount:
            won_amt = float(monthly_won.aggregate(s=Sum("amount"))["s"] or 0.0)
        else:
            won_amt = 0.0
        won_revenue_trends.append(won_amt)

        won_str = f"${won_amt:,.2f}" if can_view_amount else "[RESTRICTED]"
        markdown_lines.append(f"| {label} | {monthly_leads} | {monthly_opps.count()} | {won_str} |")

    return {
        "chart_type": "line",
        "title": f"CRM Performance Trends (Last {months} Months)",
        "timeline": month_labels,
        "series": [
            {"name": "New Leads", "data": lead_trends, "type": "bar"},
            {"name": "Won Revenue ($)", "data": won_revenue_trends, "type": "line"},
            {"name": "New Pipeline Added ($)", "data": pipeline_added_trends, "type": "line"},
        ],
        "markdown_table": "\n".join(markdown_lines),
        "recommended_visual": "Render as a combo Line/Bar chart with Months along X-axis and dual Y-axes for Lead volume and Revenue ($).",
    }


@server.tool()
def query_crm_table(
    entity_type: str,
    search: str = "",
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Browse and inspect tabular CRM records in read-only mode.
    entity_type: 'leads', 'opportunities', 'contacts', 'accounts', 'campaigns', or 'activities'.
    Enforces tenant isolation, sales hierarchy, and field-level permissions.
    """
    user = _get_scoped_user()
    entity = entity_type.lower().strip()
    if entity == "tasks":
        entity = "activities"

    valid_entities = ("leads", "opportunities", "contacts", "accounts", "campaigns", "activities")
    if entity not in valid_entities:
        raise ValueError(
            f"Entity '{entity_type}' is not supported. Use: leads, opportunities, contacts, accounts, campaigns, or activities."
        )

    # 1. Fetch authorized records using centralized mcp_data_service
    res = query_module_records(user, entity, search=search, limit=limit, offset=offset)
    total = res["total_count"]
    allowed_fields = set(res["visible_fields"])

    qs, _ = get_authorized_queryset(user, entity)
    if search:
        search_q = Q()
        search_fields_map = {
            "leads": ["title", "email", "lead_company", "contact_number"],
            "opportunities": ["name", "account__name"],
            "contacts": ["first_name", "last_name", "email", "contact_number"],
            "accounts": ["name", "website", "contact_number"],
            "campaigns": ["campaign_name"],
            "activities": ["title", "subject"],
        }
        for sf in search_fields_map.get(entity, []):
            base_f = sf.split("__")[0]
            if base_f in allowed_fields:
                search_q |= Q(**{f"{sf}__icontains": search.strip()})
        if search_q:
            qs = qs.filter(search_q)

    clamped_limit = min(max(1, int(limit)), 100)
    clamped_offset = max(0, int(offset))
    page_qs = qs.order_by("-created_at", "-id")[clamped_offset : clamped_offset + clamped_limit]

    # 2. Select columns strictly matching allowed_fields
    headers = []
    if entity == "leads":
        candidate_cols = [
            ("id", "ID", lambda x: x.id),
            ("title", "Name / Title", lambda x: x.title or "-"),
            ("lead_company", "Company", lambda x: x.lead_company or "-"),
            ("email", "Email", lambda x: x.email or "-"),
            ("contact_number", "Phone", lambda x: x.contact_number or "-"),
            ("lead_status", "Status", lambda x: str(x.lead_status) if x.lead_status else "-"),
            ("lead_owner", "Owner", lambda x: str(x.lead_owner) if x.lead_owner else "-"),
            ("created_at", "Created", lambda x: x.created_at.strftime("%Y-%m-%d") if x.created_at else "-"),
        ]
    elif entity == "opportunities":
        candidate_cols = [
            ("id", "ID", lambda x: x.id),
            ("name", "Deal Name", lambda x: x.name or "-"),
            ("account", "Account", lambda x: str(x.account) if x.account else "-"),
            ("amount", "Amount", lambda x: f"${float(x.amount or 0):,.2f}"),
            ("stage", "Stage", lambda x: str(x.stage) if x.stage else "-"),
            ("probability", "Prob %", lambda x: f"{x.probability}%" if x.probability else "-"),
            ("close_date", "Close Date", lambda x: str(x.close_date) if x.close_date else "-"),
            ("owner", "Owner", lambda x: str(x.owner) if x.owner else "-"),
        ]
    elif entity == "contacts":
        candidate_cols = [
            ("id", "ID", lambda x: x.id),
            ("first_name", "Name", lambda x: f"{x.first_name} {x.last_name}".strip()),
            ("email", "Email", lambda x: x.email or "-"),
            ("contact_number", "Phone", lambda x: x.contact_number or "-"),
            ("title", "Title", lambda x: x.title or "-"),
            ("contact_owner", "Owner", lambda x: str(x.contact_owner) if x.contact_owner else "-"),
        ]
    elif entity == "accounts":
        candidate_cols = [
            ("id", "ID", lambda x: x.id),
            ("name", "Account Name", lambda x: x.name or "-"),
            ("industry", "Industry", lambda x: str(x.industry) if x.industry else "-"),
            ("contact_number", "Phone", lambda x: x.contact_number or "-"),
            ("website", "Website", lambda x: x.website or "-"),
            ("account_owner", "Owner", lambda x: str(x.account_owner) if x.account_owner else "-"),
        ]
    elif entity == "campaigns":
        candidate_cols = [
            ("id", "ID", lambda x: x.id),
            ("campaign_name", "Campaign Name", lambda x: x.campaign_name or "-"),
            ("campaign_type", "Type", lambda x: x.campaign_type or "-"),
            ("status", "Status", lambda x: x.status or "-"),
            ("expected_revenue", "Exp. Revenue", lambda x: f"${float(x.expected_revenue or 0):,.2f}"),
            ("budget_cost", "Budget", lambda x: f"${float(x.budget_cost or 0):,.2f}"),
            ("campaign_owner", "Owner", lambda x: str(x.campaign_owner) if x.campaign_owner else "-"),
        ]
    else:  # activities
        candidate_cols = [
            ("id", "ID", lambda x: x.id),
            ("title", "Title / Subject", lambda x: x.title or x.subject or "-"),
            ("activity_type", "Type", lambda x: x.activity_type or "-"),
            ("status", "Status", lambda x: x.status or "-"),
            ("due_datetime", "Due Date", lambda x: x.due_datetime.strftime("%Y-%m-%d %H:%M") if x.due_datetime else "-"),
            ("owner", "Owner", lambda x: str(x.owner) if x.owner else "-"),
        ]

    active_cols = []
    for field_key, header_title, extractor in candidate_cols:
        if field_key == "id" or field_key in allowed_fields:
            active_cols.append((field_key, header_title, extractor))
            headers.append(header_title)

    rows = []
    for item in page_qs:
        row = {}
        for field_key, header_title, extractor in active_cols:
            row[field_key] = extractor(item)
        rows.append(row)

    md_lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in rows:
        md_lines.append("| " + " | ".join(str(v) for v in r.values()) + " |")

    return {
        "entity": entity,
        "total_count": total,
        "offset": clamped_offset,
        "limit": clamped_limit,
        "rows": rows,
        "markdown_table": "\n".join(md_lines),
    }


@server.tool()
def get_lead_details(lead_id: int) -> Dict[str, Any]:
    """
    Get a complete 360-degree read-only profile of a specific lead.
    Enforces record-level permission, sales hierarchy, and field-level permissions.
    """
    user = _get_scoped_user()
    record_info = get_single_record(user, "leads", int(lead_id))
    lead_data = record_info["data"]
    allowed_fields = set(get_authorized_fields(user, Lead))

    profile = {"id": lead_data.get("id", int(lead_id))}

    field_mappings = [
        ("title", "title"),
        ("first_name", "first_name"),
        ("last_name", "last_name"),
        ("email", "email"),
        ("contact_number", "contact_number"),
        ("lead_company", "company_name"),
        ("lead_status", "status"),
        ("lead_source", "source"),
        ("industry", "industry"),
        ("annual_revenue", "annual_revenue"),
        ("lead_owner", "lead_owner"),
        ("is_convert", "is_converted"),
        ("created_at", "created_at"),
        ("updated_at", "updated_at"),
    ]

    for model_field, output_key in field_mappings:
        if model_field in allowed_fields:
            val = lead_data.get(model_field)
            if model_field == "annual_revenue" and val is not None:
                try:
                    profile[output_key] = float(val)
                except (ValueError, TypeError):
                    profile[output_key] = val
            else:
                profile[output_key] = val

    return profile


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = "stdio"
    if len(sys.argv) > 1 and sys.argv[1] in ("sse", "streamable-http"):
        transport = sys.argv[1]
    server.run(transport=transport)
