"""
Activities & Tasks Module Load Testing Scenarios for Finlo CRM.
"""

from typing import Optional
from load_tests.data.synthetic import SyntheticDataGenerator


def view_activities_shell(user):
    """Simulates navigating to Activities module shell."""
    user.get_full(
        "/activity/activity-view/?section=activity",
        name="[ACTIVITY] GET /activity/activity-view/ (Full Shell)",
    )


def view_global_task_list_htmx(user):
    """Simulates loading global tasks HTMX partial."""
    user.get_htmx(
        "/activity/global-task-list/",
        target="#task-list-container",
        current_url="/activity/activity-view/?section=activity",
        name="[ACTIVITY] GET /activity/global-task-list/ (HTMX Tasks)",
    )


def create_task_safe(user, user_id: str = "1") -> Optional[int]:
    """Submits a new synthetic Task with strict LOADTEST_ prefix."""
    payload = SyntheticDataGenerator.generate_task(user_id=user_id)
    resp = user.post_htmx(
        "/activity/task-create-form/",
        data=payload,
        target="#dbmodal",
        current_url="/activity/activity-view/?section=activity",
        name="[ACTIVITY] POST /activity/task-create-form/ (HTMX Create Task)",
    )
    return resp.status_code in (200, 201, 302)

