"""
Dashboard Load Testing Scenarios for Finlo CRM.
"""

def view_dashboard_full(user):
    """Simulates a user opening the Dashboard for the first time or doing a hard reload."""
    user.get_full(
        "/dashboard/?section=home",
        name="[DASHBOARD] GET /dashboard/?section=home (Full Shell)",
    )


def view_dashboard_htmx(user):
    """Simulates an in-app HTMX navigation returning to the Dashboard."""
    user.get_htmx(
        "/dashboard/?section=home",
        target="#mainContent",
        current_url="/dashboard/?section=home",
        name="[DASHBOARD] GET /dashboard/?section=home (HTMX Partial)",
    )
