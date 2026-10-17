"""
App configuration for the cadences app.
"""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class CadencesConfig(AppLauncher):
    """
    Configuration class for the cadences app in Finlo.
    """

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.cadences"
    label = "cadences"
    verbose_name = _("Cadences")

    url_prefix = "cadences/"
    url_module = "finlo.contrib.cadences.urls"
    url_namespace = "cadences"

    auto_import_modules = [
        "registration",
        "signals",
        "menu",
        "view_extensions",
    ]
