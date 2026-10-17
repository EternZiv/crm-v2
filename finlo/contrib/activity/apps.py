"""App configuration for the activity module."""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class ActivityConfig(AppLauncher):
    """
    Configuration class for the Activity app in Finlo.
    """

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.activity"
    label = "activity"
    verbose_name = _("Activity")

    url_prefix = "activity/"
    url_module = "finlo.contrib.activity.urls"
    url_namespace = "activity"

    auto_import_modules = [
        "registration",
        "methods",
        "menu",
        "signals",
    ]

    celery_schedule_module = "celery_schedules"

    demo_data = {
        "files": [
            (29, "load_data/activity.json"),
        ],
        "order": 7,
        "configurable": False,
    }

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "/activity/",
                "view_or_include": "finlo.contrib.activity.api.urls",
                "name": "activity_api",
                "namespace": "activity",
            }
        ]
