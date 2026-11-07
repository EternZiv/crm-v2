"""
Strict Local Read-Only Virtual User Persona.
Used exclusively for safe local load testing against the existing Mumbai database.

Enforces:
- 100% GET and HEAD requests only (Zero POST/PUT/PATCH/DELETE).
- No detail view requests to avoid triggering RecentlyViewedMixin database writes.
- Real browser-like session persistence (authenticates once in on_start, retains sessionid).
- Realistic think times between actions (between 2.0 and 5.0 seconds).
- Read-only table browsing, search filters, module shells, and ECharts analytics partials.
"""

import logging
from locust import HttpUser, between, task
from load_tests.common.auth import CREDENTIAL_POOL, FinloAuthenticator
from load_tests.common.client import FinloClientMixin
from load_tests.scenarios import accounts, activities, contacts, dashboard, leads, opportunities

logger = logging.getLogger("finlo_loadtest")


class LocalReadOnlyUser(HttpUser, FinloClientMixin):
    """
    Simulates realistic read-only CRM navigation:
    Dashboard -> Leads -> Accounts -> Contacts -> Opportunities -> Activities.
    """

    weight = 100
    wait_time = between(2.0, 5.0)

    def on_start(self):
        """Authenticates once per user lifecycle and establishes persistent session."""
        user_idx = getattr(self, "_locust_user_id", id(self) % 500)
        self.credential = CREDENTIAL_POOL.lease_credential(user_idx)
        FinloAuthenticator.authenticate_session(self, self.credential)

    # -------------------------------------------------------------------------
    # Dashboard Scenarios
    # -------------------------------------------------------------------------

    @task(5)
    def view_dashboard_full_shell(self):
        """Full Dashboard shell navigation."""
        dashboard.view_dashboard_full(self)

    @task(10)
    def view_dashboard_htmx_partial(self):
        """In-app HTMX return to Dashboard."""
        dashboard.view_dashboard_htmx(self)

    # -------------------------------------------------------------------------
    # Leads Scenarios (Read-Only)
    # -------------------------------------------------------------------------

    @task(8)
    def browse_leads_list(self):
        """Browse leads table."""
        leads.view_leads_list_htmx(self, page=1)

    @task(4)
    def browse_leads_shell(self):
        """Browse leads full shell."""
        leads.view_leads_shell(self)

    @task(4)
    def filter_leads_search(self):
        """Search leads with read-only filter term."""
        leads.filter_leads_htmx(self, search_term="tech")

    @task(5)
    def view_leads_analytics_chart(self):
        """Load leads analytics chart partial."""
        leads.view_leads_chart_htmx(self)

    # -------------------------------------------------------------------------
    # Accounts Scenarios (Read-Only)
    # -------------------------------------------------------------------------

    @task(7)
    def browse_accounts_list(self):
        """Browse accounts table."""
        accounts.view_accounts_list_htmx(self, page=1)

    @task(4)
    def browse_accounts_shell(self):
        """Browse accounts full shell."""
        accounts.view_accounts_shell(self)

    @task(4)
    def filter_accounts_search(self):
        """Search accounts with read-only filter term."""
        accounts.filter_accounts_htmx(self, search_term="corp")

    # -------------------------------------------------------------------------
    # Contacts Scenarios (Read-Only)
    # -------------------------------------------------------------------------

    @task(7)
    def browse_contacts_list(self):
        """Browse contacts table."""
        contacts.view_contacts_list_htmx(self, page=1)

    @task(4)
    def browse_contacts_shell(self):
        """Browse contacts full shell."""
        contacts.view_contacts_shell(self)

    @task(4)
    def filter_contacts_search(self):
        """Search contacts with read-only filter term."""
        contacts.filter_contacts_htmx(self, search_term="john")

    # -------------------------------------------------------------------------
    # Opportunities Scenarios (Read-Only)
    # -------------------------------------------------------------------------

    @task(7)
    def browse_opportunities_list(self):
        """Browse opportunities table."""
        opportunities.view_opportunities_list_htmx(self, page=1)

    @task(4)
    def browse_opportunities_shell(self):
        """Browse opportunities full shell."""
        opportunities.view_opportunities_shell(self)

    @task(4)
    def filter_opportunities_search(self):
        """Search opportunities with read-only filter term."""
        opportunities.filter_opportunities_htmx(self, search_term="deal")

    @task(5)
    def view_opportunities_pipeline_chart(self):
        """Load opportunities pipeline chart partial."""
        opportunities.view_opportunities_chart_htmx(self)

    # -------------------------------------------------------------------------
    # Activities / Tasks Scenarios (Read-Only)
    # -------------------------------------------------------------------------

    @task(5)
    def browse_tasks_list(self):
        """Browse global task list."""
        activities.view_global_task_list_htmx(self)
