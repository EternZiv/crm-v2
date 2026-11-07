"""
Data Entry / Active CRUD Virtual User Persona.
Represents ~10% of the virtual user load.
Focuses on safe synthetic write operations (Leads, Accounts, Contacts, Opportunities, Tasks).
Tests database transaction performance, lock contention, and signal handlers.
"""

from locust import HttpUser, between, task
from load_tests.common.auth import CREDENTIAL_POOL, FinloAuthenticator
from load_tests.common.client import FinloClientMixin
from load_tests.scenarios import accounts, activities, contacts, leads, opportunities


class DataEntryUser(HttpUser, FinloClientMixin):
    """Simulates an active operations clerk creating and updating CRM records."""

    weight = 10
    wait_time = between(2.0, 5.0)  # Faster entry pace

    def on_start(self):
        """Authenticates with a leased clerk credential."""
        user_idx = getattr(self, "_locust_user_id", id(self) % 500)
        self.credential = CREDENTIAL_POOL.lease_credential(user_idx)
        FinloAuthenticator.authenticate_session(self, self.credential)

    @task(3)
    def create_synthetic_lead(self):
        leads.create_lead_safe(self, user_id=self.credential.get("username", "1"))

    @task(3)
    def create_synthetic_account(self):
        accounts.create_account_safe(self, user_id=self.credential.get("username", "1"))

    @task(2)
    def create_synthetic_contact(self):
        contacts.create_contact_safe(self, user_id=self.credential.get("username", "1"))

    @task(2)
    def create_synthetic_deal(self):
        opportunities.create_opportunity_safe(self, user_id=self.credential.get("username", "1"))

    @task(2)
    def create_synthetic_task(self):
        activities.create_task_safe(self, user_id=self.credential.get("username", "1"))

