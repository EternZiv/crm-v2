"""
AppLauncher for the finlo.contrib.keys app
"""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class KeysConfig(AppLauncher):
    """App configuration class for finlo.contrib.keys."""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.keys"
    label = "keys"
    verbose_name = _("Keyboard Shortcuts")

    js_files = "keys/assets/js/short_key.js"

    url_prefix = "shortkeys/"
    url_module = "finlo.contrib.keys.urls"
    url_namespace = "keys"

    auto_import_modules = [
        "menu",
        "signals",
    ]

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "keys/",
                "view_or_include": "finlo.contrib.keys.api.urls",
                "name": "keys_api",
                "namespace": "keys",
            }
        ]
