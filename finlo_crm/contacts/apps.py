"""App configuration for the contacts module."""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class ContactsConfig(AppLauncher):
    """Contacts App Configuration"""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo_crm.contacts"
    verbose_name = _("Contacts")

    url_prefix = "crm/contacts/"
    url_module = "finlo_crm.contacts.urls"
    url_namespace = "contacts"

    auto_import_modules = [
        "registration",
        "signals",
        "menu",
        "dashboard",
    ]

    demo_data = [
        {
            "files": [
                (11, "load_data/contact.json"),
            ],
            "order": 6,
        },
        {
            "files": [
                (26, "load_data/duplicate_control.json"),
            ],
            "order": 7,
            "configurable": False,
        },
    ]

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "crm/contacts/",
                "view_or_include": "finlo_crm.contacts.api.urls",
                "name": "finlo_crm_contacts_api",
                "namespace": "finlo_crm_contacts",
            }
        ]
