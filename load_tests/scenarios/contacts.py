"""
Contacts Module Load Testing Scenarios for Finlo CRM.
"""

from typing import Optional
from load_tests.data.synthetic import SyntheticDataGenerator


def view_contacts_shell(user):
    """Simulates navigating to Contacts module shell."""
    user.get_full(
        "/crm/contacts/contacts-view/?section=people",
        name="[CONTACTS] GET /crm/contacts/contacts-view/ (Full Shell)",
    )


def view_contacts_list_htmx(user, page: int = 1):
    """Simulates HTMX table rendering and pagination for contacts."""
    url = f"/crm/contacts/contact-list-view/?page={page}" if page > 1 else "/crm/contacts/contact-list-view/"
    user.get_htmx(
        url,
        target="#contacts-table-container",
        current_url="/crm/contacts/contacts-view/?section=people",
        name="[CONTACTS] GET /crm/contacts/contact-list-view/ (HTMX Table)",
    )


def filter_contacts_htmx(user, search_term: str = "john"):
    """Simulates searching or filtering contacts via HTMX."""
    user.get_htmx(
        f"/crm/contacts/contact-list-view/?search={search_term}",
        target="#contacts-table-container",
        current_url="/crm/contacts/contacts-view/?section=people",
        name="[CONTACTS] GET /crm/contacts/contact-list-view/?search=... (HTMX Filter)",
    )


def view_contact_detail(user, contact_id: int):
    """Simulates viewing contact detail view."""
    user.get_htmx(
        f"/crm/contacts/contact-detail-view/{contact_id}/",
        target="#mainContent",
        current_url=f"/crm/contacts/contact-detail-view/{contact_id}/",
        name="[CONTACTS] GET /crm/contacts/contact-detail-view/:id/ (HTMX Detail)",
    )


def create_contact_safe(user, user_id: str = "1", account_id: str = "") -> Optional[int]:
    """Submits a new synthetic Contact with strict LOADTEST_ prefix."""
    payload = SyntheticDataGenerator.generate_contact(user_id=user_id, account_id=account_id)
    resp = user.post_htmx(
        "/crm/contacts/contact-single-create-form/",
        data=payload,
        target="#dbmodal",
        current_url="/crm/contacts/contacts-view/?section=people",
        name="[CONTACTS] POST /crm/contacts/contact-single-create-form/ (HTMX Create)",
    )
    return resp.status_code in (200, 201, 302)

