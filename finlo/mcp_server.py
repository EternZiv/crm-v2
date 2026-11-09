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

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

# Bootstrap Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finlo.settings")
import django

django.setup()

from django.db.models import Avg, Count, F, Q, Sum
from mcp.server.mcpserver import MCPServer

from finlo.auth.models import User
from finlo.contrib.activity.models import Activity
from finlo_crm.accounts.models import Account
from finlo_crm.campaigns.models import Campaign
from finlo_crm.contacts.models import Contact
from finlo_crm.leads.models import Lead
from finlo_crm.opportunities.models import Opportunity

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
    if _ACTIVE_USER and _ACTIVE_USER.is_active:
        return _ACTIVE_USER

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
    qs = Lead.objects.all().select_related("lead_status", "lead_owner", "company")
    if user.company:
        qs = qs.filter(company=user.company)
    if not user.is_superuser:
        if not user.has_perm("leads.view_lead") and user.has_perm("leads.view_own_lead"):
            qs = qs.filter(lead_owner=user)
        elif not user.has_perm("leads.view_lead") and not user.has_perm("leads.view_own_lead"):
            return Lead.objects.none()
    return qs


def _get_scoped_opportunities(user: User):
    qs = Opportunity.objects.all().select_related("stage", "owner", "account", "company")
    if user.company:
        qs = qs.filter(company=user.company)
    if not user.is_superuser:
        if not user.has_perm("opportunities.view_opportunity") and user.has_perm("opportunities.view_own_opportunity"):
            qs = qs.filter(owner=user)
        elif not user.has_perm("opportunities.view_opportunity") and not user.has_perm("opportunities.view_own_opportunity"):
            return Opportunity.objects.none()
    return qs


def _get_scoped_contacts(user: User):
    qs = Contact.objects.all().select_related("contact_owner", "company")
    if user.company:
        qs = qs.filter(company=user.company)
    if not user.is_superuser:
        if not user.has_perm("contacts.view_contact") and user.has_perm("contacts.view_own_contact"):
            qs = qs.filter(contact_owner=user)
        elif not user.has_perm("contacts.view_contact") and not user.has_perm("contacts.view_own_contact"):
            return Contact.objects.none()
    return qs


def _get_scoped_accounts(user: User):
    qs = Account.objects.all().select_related("account_owner", "company")
    if user.company:
        qs = qs.filter(company=user.company)
    if not user.is_superuser:
        if not user.has_perm("accounts.view_account") and user.has_perm("accounts.view_own_account"):
            qs = qs.filter(account_owner=user)
        elif not user.has_perm("accounts.view_account") and not user.has_perm("accounts.view_own_account"):
            return Account.objects.none()
    return qs


def _get_scoped_campaigns(user: User):
    qs = Campaign.objects.all().select_related("campaign_owner", "company")
    if user.company:
        qs = qs.filter(company=user.company)
    if not user.is_superuser:
        if not user.has_perm("campaigns.view_campaign") and user.has_perm("campaigns.view_own_campaign"):
            qs = qs.filter(campaign_owner=user)
        elif not user.has_perm("campaigns.view_campaign") and not user.has_perm("campaigns.view_own_campaign"):
            return Campaign.objects.none()
    return qs


def _get_scoped_activities(user: User):
    qs = Activity.objects.all().select_related("owner", "company")
    if user.company:
        qs = qs.filter(company=user.company)
    if not user.is_superuser:
        if not user.has_perm("activity.view_activity") and user.has_perm("activity.view_own_activity"):
            qs = qs.filter(owner=user)
        elif not user.has_perm("activity.view_activity") and not user.has_perm("activity.view_own_activity"):
            return Activity.objects.none()
    return qs


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

    return {
        "status": "authenticated",
        "message": f"Successfully authenticated as {user.username} ({user.email}).",
        "username": user.username,
        "email": user.email,
        "full_name": user.get_full_name() or user.username,
        "is_superuser": user.is_superuser,
        "company": company_name,
        "roles": roles,
        "scopes": {
            "leads": "all" if (user.is_superuser or user.has_perm("leads.view_lead")) else ("own" if user.has_perm("leads.view_own_lead") else "none"),
            "opportunities": "all" if (user.is_superuser or user.has_perm("opportunities.view_opportunity")) else ("own" if user.has_perm("opportunities.view_own_opportunity") else "none"),
            "contacts": "all" if (user.is_superuser or user.has_perm("contacts.view_contact")) else ("own" if user.has_perm("contacts.view_own_contact") else "none"),
            "accounts": "all" if (user.is_superuser or user.has_perm("accounts.view_account")) else ("own" if user.has_perm("accounts.view_own_account") else "none"),
            "campaigns": "all" if (user.is_superuser or user.has_perm("campaigns.view_campaign")) else ("own" if user.has_perm("campaigns.view_own_campaign") else "none"),
            "activities": "all" if (user.is_superuser or user.has_perm("activity.view_activity")) else ("own" if user.has_perm("activity.view_own_activity") else "none"),
        },
        "isolation_policy": (
            "Superuser: Full Company Tenant Access"
            if user.is_superuser
            else "Role-Scoped: Only your assigned records are visible; all other user accounts are restricted."
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

    return {
        "status": "authenticated",
        "username": user.username,
        "email": user.email,
        "full_name": user.get_full_name() or user.username,
        "is_superuser": user.is_superuser,
        "company": company_name,
        "roles": roles,
        "scopes": {
            "leads": "all" if (user.is_superuser or user.has_perm("leads.view_lead")) else ("own" if user.has_perm("leads.view_own_lead") else "none"),
            "opportunities": "all" if (user.is_superuser or user.has_perm("opportunities.view_opportunity")) else ("own" if user.has_perm("opportunities.view_own_opportunity") else "none"),
            "contacts": "all" if (user.is_superuser or user.has_perm("contacts.view_contact")) else ("own" if user.has_perm("contacts.view_own_contact") else "none"),
            "accounts": "all" if (user.is_superuser or user.has_perm("accounts.view_account")) else ("own" if user.has_perm("accounts.view_own_account") else "none"),
            "campaigns": "all" if (user.is_superuser or user.has_perm("campaigns.view_campaign")) else ("own" if user.has_perm("campaigns.view_own_campaign") else "none"),
            "activities": "all" if (user.is_superuser or user.has_perm("activity.view_activity")) else ("own" if user.has_perm("activity.view_own_activity") else "none"),
        },
        "mode": "READ_ONLY",
        "scope_summary": (
            "Superuser access (All Company Data)"
            if user.is_superuser
            else f"Role-scoped access within company: {company_name}"
        ),
    }


@server.tool()
def get_crm_kpis() -> Dict[str, Any]:
    """
    Get high-level executive KPI scorecards across Leads, Opportunities, Accounts, and Contacts.
    Returns metrics formatted for rendering KPI metric cards and executive dashboards.
    """
    user = _get_scoped_user()

    leads_qs = _get_scoped_leads(user)
    opps_qs = _get_scoped_opportunities(user)
    contacts_qs = _get_scoped_contacts(user)
    accounts_qs = _get_scoped_accounts(user)

    total_leads = leads_qs.count()
    converted_leads = leads_qs.filter(is_convert=True).count()
    lead_conv_rate = round((converted_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

    total_opps = opps_qs.count()
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
        "total_pipeline_value_formatted": f"{total_val:,.2f}",
        "total_closed_won_revenue": won_val,
        "total_closed_won_revenue_formatted": f"{won_val:,.2f}",
        "win_rate_percent": win_rate,
        "average_deal_size": avg_val,
        "total_accounts": total_accounts,
        "total_contacts": total_contacts,
        "kpi_cards": [
            {
                "title": "Total Pipeline Value",
                "value": f"${total_val:,.2f}",
                "metric": total_val,
                "subtext": f"{total_opps} Active Deals",
            },
            {
                "title": "Closed Won Revenue",
                "value": f"${won_val:,.2f}",
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
                "value": f"${avg_val:,.2f}",
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
    group_by options: 'status', 'source', or 'industry'
    """
    user = _get_scoped_user()
    leads_qs = _get_scoped_leads(user)
    total_leads = leads_qs.count()

    group_field_map = {
        "status": "lead_status__name",
        "source": "lead_source",
        "industry": "industry__name",
    }
    field = group_field_map.get(group_by.lower(), "lead_status__name")

    records = (
        leads_qs.values(category=F(field))
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
        "chart_type": "pie" if group_by.lower() in ("status",) else "bar",
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
    """
    user = _get_scoped_user()
    opps_qs = _get_scoped_opportunities(user)

    stages_data = (
        opps_qs.values(
            stage_name=F("stage__name"),
            stage_order=F("stage__order"),
            stage_prob=F("stage__probability"),
        )
        .annotate(
            count=Count("id"),
            total_amount=Sum("amount"),
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
        amt = float(s["total_amount"] or 0.0)
        prob = s["stage_prob"] or 0
        total_pipeline_val += amt

        stages.append(name)
        deal_counts.append(cnt)
        deal_amounts.append(amt)
        markdown_lines.append(f"| {name} | {cnt} | ${amt:,.2f} | {prob}% |")

    return {
        "chart_type": "funnel",
        "title": "Sales Pipeline Stage Funnel",
        "total_deals": opps_qs.count(),
        "total_pipeline_value": f"${total_pipeline_val:,.2f}",
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
    """
    user = _get_scoped_user()
    opps_qs = _get_scoped_opportunities(user)
    leads_qs = _get_scoped_leads(user)

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
        opp_amt = float(monthly_opps.aggregate(s=Sum("amount"))["s"] or 0.0)
        pipeline_added_trends.append(opp_amt)

        monthly_won = monthly_opps.filter(
            Q(stage__name__icontains="won") | Q(stage__name__icontains="closed won")
        )
        won_amt = float(monthly_won.aggregate(s=Sum("amount"))["s"] or 0.0)
        won_revenue_trends.append(won_amt)

        markdown_lines.append(f"| {label} | {monthly_leads} | {monthly_opps.count()} | ${won_amt:,.2f} |")

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
    entity_type: 'leads', 'opportunities', 'contacts', 'accounts', 'campaigns', or 'activities'
    """
    user = _get_scoped_user()
    limit = min(max(1, limit), 100)
    entity = entity_type.lower().strip()

    if entity == "leads":
        qs = _get_scoped_leads(user).order_by("-created_at", "-id")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(email__icontains=search) | Q(lead_company__icontains=search))
        total = qs.count()
        rows = [
            {
                "id": lead.id,
                "name": lead.title,
                "company": lead.lead_company or "-",
                "email": lead.email or "-",
                "phone": lead.contact_number or "-",
                "status": str(lead.lead_status) if lead.lead_status else "-",
                "owner": str(lead.lead_owner) if lead.lead_owner else "-",
                "created": lead.created_at.strftime("%Y-%m-%d") if lead.created_at else "-",
            }
            for lead in qs[offset : offset + limit]
        ]
        headers = ["ID", "Name / Title", "Company", "Email", "Phone", "Status", "Owner", "Created"]

    elif entity == "opportunities":
        qs = _get_scoped_opportunities(user).order_by("-created_at", "-id")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(account__name__icontains=search))
        total = qs.count()
        rows = [
            {
                "id": o.id,
                "name": o.name,
                "account": str(o.account) if o.account else "-",
                "amount": f"${float(o.amount or 0):,.2f}",
                "stage": str(o.stage) if o.stage else "-",
                "probability": f"{o.probability}%" if o.probability else "-",
                "close_date": str(o.close_date) if o.close_date else "-",
                "owner": str(o.owner) if o.owner else "-",
            }
            for o in qs[offset : offset + limit]
        ]
        headers = ["ID", "Deal Name", "Account", "Amount", "Stage", "Prob %", "Close Date", "Owner"]

    elif entity == "contacts":
        qs = _get_scoped_contacts(user).order_by("-created_at", "-id")
        if search:
            qs = qs.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search))
        total = qs.count()
        rows = [
            {
                "id": c.id,
                "name": f"{c.first_name} {c.last_name}".strip(),
                "email": c.email or "-",
                "phone": c.contact_number or "-",
                "title": c.title or "-",
                "owner": str(c.contact_owner) if c.contact_owner else "-",
            }
            for c in qs[offset : offset + limit]
        ]
        headers = ["ID", "Name", "Email", "Phone", "Title", "Owner"]

    elif entity == "accounts":
        qs = _get_scoped_accounts(user).order_by("-created_at", "-id")
        if search:
            qs = qs.filter(Q(name__icontains=search))
        total = qs.count()
        rows = [
            {
                "id": a.id,
                "name": a.name,
                "industry": str(a.industry) if a.industry else "-",
                "phone": a.contact_number or "-",
                "website": a.website or "-",
                "owner": str(a.account_owner) if a.account_owner else "-",
            }
            for a in qs[offset : offset + limit]
        ]
        headers = ["ID", "Account Name", "Industry", "Phone", "Website", "Owner"]

    elif entity == "campaigns":
        qs = _get_scoped_campaigns(user).order_by("-created_at", "-id")
        if search:
            qs = qs.filter(Q(campaign_name__icontains=search))
        total = qs.count()
        rows = [
            {
                "id": cmp.id,
                "name": cmp.campaign_name,
                "type": cmp.campaign_type or "-",
                "status": cmp.status or "-",
                "expected_revenue": f"${float(cmp.expected_revenue or 0):,.2f}",
                "budget_cost": f"${float(cmp.budget_cost or 0):,.2f}",
                "owner": str(cmp.campaign_owner) if cmp.campaign_owner else "-",
            }
            for cmp in qs[offset : offset + limit]
        ]
        headers = ["ID", "Campaign Name", "Type", "Status", "Exp. Revenue", "Budget", "Owner"]

    elif entity in ("activities", "tasks"):
        qs = _get_scoped_activities(user).order_by("-created_at", "-id")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(subject__icontains=search))
        total = qs.count()
        rows = [
            {
                "id": act.id,
                "title": act.title or act.subject or "-",
                "type": act.activity_type or "-",
                "status": act.status or "-",
                "due": act.due_datetime.strftime("%Y-%m-%d %H:%M") if act.due_datetime else "-",
                "owner": str(act.owner) if act.owner else "-",
            }
            for act in qs[offset : offset + limit]
        ]
        headers = ["ID", "Title / Subject", "Type", "Status", "Due Date", "Owner"]

    else:
        raise ValueError(
            f"Entity '{entity_type}' is not supported. Use: leads, opportunities, contacts, accounts, campaigns, or activities."
        )

    # Build Markdown table
    md_lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in rows:
        md_lines.append("| " + " | ".join(str(v) for v in r.values()) + " |")

    return {
        "entity": entity,
        "total_count": total,
        "offset": offset,
        "limit": limit,
        "rows": rows,
        "markdown_table": "\n".join(md_lines),
    }


@server.tool()
def get_lead_details(lead_id: int) -> Dict[str, Any]:
    """
    Get a complete 360-degree read-only profile of a specific lead.
    """
    user = _get_scoped_user()
    lead = _get_scoped_leads(user).filter(id=lead_id).first()
    if not lead:
        raise ValueError(f"Lead with ID {lead_id} does not exist or you lack permission to view it.")

    return {
        "id": lead.id,
        "title": lead.title,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "email": lead.email,
        "contact_number": lead.contact_number,
        "company_name": lead.lead_company,
        "status": str(lead.lead_status) if lead.lead_status else None,
        "source": str(lead.lead_source) if lead.lead_source else None,
        "industry": str(lead.industry) if lead.industry else None,
        "annual_revenue": float(lead.annual_revenue) if lead.annual_revenue else 0.0,
        "lead_owner": str(lead.lead_owner) if lead.lead_owner else None,
        "is_converted": lead.is_convert,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = "stdio"
    if len(sys.argv) > 1 and sys.argv[1] in ("sse", "streamable-http"):
        transport = sys.argv[1]
    server.run(transport=transport)
