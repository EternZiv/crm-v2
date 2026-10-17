"""
AppLauncher for the finlo.contrib.theme app
"""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class ThemeConfig(AppLauncher):
    """App configuration class for finlo.contrib.theme."""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.theme"
    label = "theme"
    verbose_name = _("Theme Manager")

    auto_import_modules = [
        "menu",
        "signals",
        "registration",
    ]

    url_prefix = "theme/"
    url_module = "finlo.contrib.theme.urls"
    url_namespace = "theme"
