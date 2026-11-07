"""
General Navigation & Browser Virtual User Persona.
Represents ~10% of the virtual user load.
Focuses on reading, paginating, searching, and navigating across all modules.
Tests database SELECT queries, index utilization, and template rendering cache.
"""

from locust import HttpUser, between, task
from load_tests.common.auth import CREDENTIAL_POOL, FinloAuthenticator
from load_tests.common.client import FinloClientMixin
from load_tests.scenarios import accounts, activities, contacts, dashboard, leads, opportunities


class BrowserUser(HttpUser, FinloClientMixin):
    """Simulates a user navigating across tables, pagination, and tabs."""

    weight = 10
    wait_time = between(2.0, 6.0)

    def on_start(self):
        user_idx = getattr(self, "_locust_user_id", id(self) % 500)
        self.credential = CREDENTIAL_POOL.lease_credential(user_idx)
        FinloAuthenticator.authenticate_session(self, self.credential)

    @task(4)
    def browse_leads_pages(self):
        leads.view_leads_list_htmx(self, page=1)
        leads.view_leads_list_htmx(self, page=2)

    @task(3)
    def browse_accounts_pages(self):
        accounts.view_accounts_list_htmx(self, page=1)
        accounts.view_accounts_list_htmx(self, page=2)

    @task(3)
    def browse_contacts_pages(self):
        contacts.view_contacts_list_htmx(self, page=1)

    @task(2)
    def browse_opportunities_pages(self):
        opportunities.view_opportunities_list_htmx(self, page=1)

    @task(2)
    def browse_tasks(self):
        activities.view_global_task_list_htmx(self)

    @task(2)
    def return_to_dashboard(self):
        dashboard.view_dashboard_htmx(self)

