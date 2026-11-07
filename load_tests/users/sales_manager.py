"""
Sales Manager / Regional Sales Manager (RSM) Virtual User Persona.
Represents ~20% of the virtual user load.
Focuses on analytics, dashboard review, opportunity pipeline, and team performance.
"""

from locust import HttpUser, between, task
from load_tests.common.auth import CREDENTIAL_POOL, FinloAuthenticator
from load_tests.common.client import FinloClientMixin
from load_tests.scenarios import dashboard, leads, opportunities


class SalesManagerUser(HttpUser, FinloClientMixin):
    """Simulates a sales manager or regional executive reviewing CRM performance."""

    weight = 20
    wait_time = between(4.0, 10.0)  # Analytical think time

    def on_start(self):
        """Authenticates with a leased manager credential from the user pool."""
        user_idx = getattr(self, "_locust_user_id", id(self) % 500)
        self.credential = CREDENTIAL_POOL.lease_credential(user_idx)
        FinloAuthenticator.authenticate_session(self, self.credential)

    @task(6)
    def inspect_dashboard(self):
        """Review dashboard charts, KPIs, and metrics tables."""
        dashboard.view_dashboard_full(self)

    @task(5)
    def review_opportunity_pipeline(self):
        """Inspect pipeline charts and active opportunity deals."""
        opportunities.view_opportunities_shell(self)
        opportunities.view_opportunities_list_htmx(self, page=1)
        opportunities.view_opportunities_chart_htmx(self)

    @task(3)
    def inspect_leads_analytics(self):
        """Review lead generation analytics and conversion charts."""
        leads.view_leads_chart_htmx(self)

    @task(2)
    def view_high_value_deal(self):
        """Drill into an opportunity detail view."""
        opportunities.view_opportunity_detail(self, opp_id=1)

