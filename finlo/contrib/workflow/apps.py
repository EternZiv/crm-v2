"""
App configuration for the workflow app.
"""

from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class WorkflowConfig(AppLauncher):
    """
    Configuration class for the workflow app in Finlo.
    """

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.workflow"
    label = "workflow"
    verbose_name = _("Workflow")

    url_prefix = "workflow/"
    url_module = "finlo.contrib.workflow.urls"
    url_namespace = "workflow"

    celery_schedule_module = "celery_schedules"

    auto_import_modules = [
        "registration",
        "signals",
        "menu",
    ]
