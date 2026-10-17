"""
AppConfig for the duplicates app
"""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class DuplicatesConfig(AppLauncher):
    """App configuration class for duplicates."""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.duplicates"
    label = "duplicates"
    verbose_name = _("Clone Management")

    url_prefix = "duplicates/"
    url_module = "finlo.contrib.duplicates.urls"

    auto_import_modules = ["menu", "registration", "view_extensions"]
