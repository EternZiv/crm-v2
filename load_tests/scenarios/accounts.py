"""
Accounts Module Load Testing Scenarios for Finlo CRM.
"""

from typing import Optional
from load_tests.data.synthetic import SyntheticDataGenerator


def view_accounts_shell(user):
    """Simulates navigating to Accounts module shell."""
    user.get_full(
        "/crm/accounts/accounts-view/?section=people",
        name="[ACCOUNTS] GET /crm/accounts/accounts-view/ (Full Shell)",
    )


def view_accounts_list_htmx(user, page: int = 1):
    """Simulates HTMX table rendering and pagination for accounts."""
    url = f"/crm/accounts/accounts-list-view/?page={page}" if page > 1 else "/crm/accounts/accounts-list-view/"
    user.get_htmx(
        url,
        target="#accounts-table-container",
        current_url="/crm/accounts/accounts-view/?section=people",
        name="[ACCOUNTS] GET /crm/accounts/accounts-list-view/ (HTMX Table)",
    )


def filter_accounts_htmx(user, search_term: str = "corp"):
    """Simulates searching or filtering accounts via HTMX."""
    user.get_htmx(
        f"/crm/accounts/accounts-list-view/?search={search_term}",
        target="#accounts-table-container",
        current_url="/crm/accounts/accounts-view/?section=people",
        name="[ACCOUNTS] GET /crm/accounts/accounts-list-view/?search=... (HTMX Filter)",
    )


def view_account_detail(user, account_id: int):
    """Simulates viewing account detail view."""
    user.get_htmx(
        f"/crm/accounts/account-detail-view/{account_id}/",
        target="#mainContent",
        current_url=f"/crm/accounts/account-detail-view/{account_id}/",
        name="[ACCOUNTS] GET /crm/accounts/account-detail-view/:id/ (HTMX Detail)",
    )


def create_account_safe(user, user_id: str = "1") -> Optional[int]:
    """Submits a new synthetic Account with strict LOADTEST_ prefix."""
    payload = SyntheticDataGenerator.generate_account(user_id=user_id)
    resp = user.post_htmx(
        "/crm/accounts/account-single-create-form-view/",
        data=payload,
        target="#dbmodal",
        current_url="/crm/accounts/accounts-view/?section=people",
        name="[ACCOUNTS] POST /crm/accounts/account-single-create-form-view/ (HTMX Create)",
    )
    return resp.status_code in (200, 201, 302)
