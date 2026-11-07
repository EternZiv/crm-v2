"""
Sales Representative (BDO) Virtual User Persona.
Represents ~60% of the virtual user load in a real deployment.
Performs day-to-day sales workflows: browsing leads, filtering, viewing details,
creating tasks, and checking accounts and contacts.
"""

from locust import HttpUser, between, task
from load_tests.common.auth import CREDENTIAL_POOL, FinloAuthenticator
from load_tests.common.client import FinloClientMixin
from load_tests.scenarios import accounts, activities, contacts, dashboard, leads


class SalesRepUser(HttpUser, FinloClientMixin):
    """Simulates a field sales representative or BDO interacting with Finlo CRM."""

    weight = 60
    wait_time = between(3.0, 8.0)  # Realistic think time between clicks

    def on_start(self):
        """Authenticates with a leased staging credential from the user pool."""
        # Use user index based on object id
        user_idx = getattr(self, "_locust_user_id", id(self) % 500)
        self.credential = CREDENTIAL_POOL.lease_credential(user_idx)
        FinloAuthenticator.authenticate_session(self, self.credential)

    @task(5)
    def review_dashboard(self):
        """Review dashboard KPIs and recent widgets."""
        dashboard.view_dashboard_htmx(self)

    @task(10)
    def manage_leads(self):
        """Browse leads, view page 1, and apply a search filter."""
        leads.view_leads_shell(self)
        leads.view_leads_list_htmx(self, page=1)
        leads.filter_leads_htmx(self, search_term="Technology")

    @task(3)
    def view_lead_details(self):
        """Open a lead detail view (using synthetic baseline id)."""
        leads.view_lead_detail(self, lead_id=1)

    @task(2)
    def capture_new_lead(self):
        """Submit a new synthetic prospect into the CRM."""
        leads.create_lead_safe(self, user_id=self.credential.get("username", "1"))

    @task(4)
    def check_accounts_and_contacts(self):
        """Browse accounts and contacts lists."""
        accounts.view_accounts_list_htmx(self, page=1)
        contacts.view_contacts_list_htmx(self, page=1)

    @task(3)
    def schedule_task(self):
        """Create a follow-up task."""
        activities.create_task_safe(self, user_id=self.credential.get("username", "1"))

