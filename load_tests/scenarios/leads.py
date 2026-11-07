"""
Leads Module Load Testing Scenarios for Finlo CRM.
Covers list view, filtering, chart partials, detail views, and safe synthetic lead creation.
"""

from typing import Optional
from load_tests.data.synthetic import SyntheticDataGenerator


def view_leads_shell(user):
    """Simulates navigating to the Leads module shell."""
    user.get_full(
        "/crm/leads/leads-view/?section=sales",
        name="[LEADS] GET /crm/leads/leads-view/ (Full Shell)",
    )


def view_leads_list_htmx(user, page: int = 1):
    """Simulates HTMX table rendering and pagination."""
    url = f"/crm/leads/leads-list/?page={page}" if page > 1 else "/crm/leads/leads-list/"
    user.get_htmx(
        url,
        target="#leads-table-container",
        current_url="/crm/leads/leads-view/?section=sales",
        name="[LEADS] GET /crm/leads/leads-list/ (HTMX Table)",
    )


def filter_leads_htmx(user, search_term: str = "LOADTEST"):
    """Simulates searching or filtering leads via HTMX."""
    url = f"/crm/leads/leads-list/?search={search_term}"
    user.get_htmx(
        url,
        target="#leads-table-container",
        current_url="/crm/leads/leads-view/?section=sales",
        name="[LEADS] GET /crm/leads/leads-list/?search=... (HTMX Filter)",
    )


def view_leads_chart_htmx(user):
    """Simulates rendering the Leads analytics chart partial."""
    user.get_htmx(
        "/crm/leads/leads-chart/",
        target="#chart-container",
        current_url="/crm/leads/leads-view/?section=sales",
        name="[LEADS] GET /crm/leads/leads-chart/ (HTMX Chart)",
    )


def view_lead_detail(user, lead_id: int):
    """Simulates viewing a specific Lead's record details."""
    user.get_htmx(
        f"/crm/leads/leads-detail/{lead_id}/",
        target="#mainContent",
        current_url=f"/crm/leads/leads-detail/{lead_id}/",
        name="[LEADS] GET /crm/leads/leads-detail/:id/ (HTMX Detail)",
    )


def create_lead_safe(user, user_id: str = "1") -> Optional[int]:
    """
    Submits a new synthetic Lead with strict LOADTEST_ prefix.
    Simulates modal form submission via HTMX POST.
    """
    payload = SyntheticDataGenerator.generate_lead(user_id=user_id)
    resp = user.post_htmx(
        "/crm/leads/leads-create-single/",
        data=payload,
        target="#dbmodal",
        current_url="/crm/leads/leads-view/?section=sales",
        name="[LEADS] POST /crm/leads/leads-create-single/ (HTMX Create)",
    )
    if resp.status_code in (200, 201, 302):
        return True
    return False
