"""Django app configuration for the Finlo mail system."""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class MailConfig(AppLauncher):
    """App configuration class for the Finlo mail system."""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.mail"
    label = "mail"
    verbose_name = _("Mail System")

    template_files = [
        "load_template/template.json",
    ]

    demo_data = {
        "files": [
            (17, "load_data/mail_template.json"),
        ],
        "order": 7,
        "configurable": False,
    }

    url_prefix = "mail/"
    url_module = "finlo.contrib.mail.urls"
    url_namespace = "mail"

    auto_import_modules = [
        "registration",
        "signals",
        "menu",
    ]

    celery_schedule_module = "celery_schedules"

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "mail/",
                "view_or_include": "finlo.contrib.mail.api.urls",
                "name": "mail_api",
                "namespace": "mail",
            }
        ]
