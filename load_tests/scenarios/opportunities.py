"""
Opportunities Module Load Testing Scenarios for Finlo CRM.
"""

from typing import Optional
from load_tests.data.synthetic import SyntheticDataGenerator


def view_opportunities_shell(user):
    """Simulates navigating to Opportunities module shell."""
    user.get_full(
        "/crm/opportunities/opportunities-view/?section=sales",
        name="[OPPORTUNITIES] GET /crm/opportunities/opportunities-view/ (Full Shell)",
    )


def view_opportunities_list_htmx(user, page: int = 1):
    """Simulates HTMX table rendering and pagination for opportunities."""
    url = f"/crm/opportunities/opportunities-list/?page={page}" if page > 1 else "/crm/opportunities/opportunities-list/"
    user.get_htmx(
        url,
        target="#opportunities-table-container",
        current_url="/crm/opportunities/opportunities-view/?section=sales",
        name="[OPPORTUNITIES] GET /crm/opportunities/opportunities-list/ (HTMX Table)",
    )


def filter_opportunities_htmx(user, search_term: str = "deal"):
    """Simulates searching or filtering opportunities via HTMX."""
    user.get_htmx(
        f"/crm/opportunities/opportunities-list/?search={search_term}",
        target="#opportunities-table-container",
        current_url="/crm/opportunities/opportunities-view/?section=sales",
        name="[OPPORTUNITIES] GET /crm/opportunities/opportunities-list/?search=... (HTMX Filter)",
    )


def view_opportunities_chart_htmx(user):
    """Simulates viewing pipeline chart partial."""
    user.get_htmx(
        "/crm/opportunities/opportunities-chart/",
        target="#chart-container",
        current_url="/crm/opportunities/opportunities-view/?section=sales",
        name="[OPPORTUNITIES] GET /crm/opportunities/opportunities-chart/ (HTMX Chart)",
    )


def view_opportunity_detail(user, opp_id: int):
    """Simulates viewing opportunity detail view."""
    user.get_htmx(
        f"/crm/opportunities/opportunity-detail-view/{opp_id}/",
        target="#mainContent",
        current_url=f"/crm/opportunities/opportunity-detail-view/{opp_id}/",
        name="[OPPORTUNITIES] GET /crm/opportunities/opportunity-detail-view/:id/ (HTMX Detail)",
    )


def create_opportunity_safe(user, user_id: str = "1", account_id: str = "") -> Optional[int]:
    """Submits a new synthetic Opportunity with strict LOADTEST_ prefix."""
    payload = SyntheticDataGenerator.generate_opportunity(user_id=user_id, account_id=account_id)
    resp = user.post_htmx(
        "/crm/opportunities/opportunity-single-create/",
        data=payload,
        target="#dbmodal",
        current_url="/crm/opportunities/opportunities-view/?section=sales",
        name="[OPPORTUNITIES] POST /crm/opportunities/opportunity-single-create/ (HTMX Create)",
    )
    return resp.status_code in (200, 201, 302)

