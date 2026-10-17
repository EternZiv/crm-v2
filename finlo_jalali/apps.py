"""
AppLauncher for the finlo_jalali extension.

Install via local_settings.py (do not add this app to finlo/settings/base.py):

    INSTALLED_APPS += ["finlo_jalali"]
"""

from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class FinloJalaliConfig(AppLauncher):
    """Jalali calendar extension — formatter, forms, views, and calendar assets."""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo_jalali"
    verbose_name = _("Jalali Calendar")

    auto_import_modules = [
        "models",
        "formatters",
        "forms",
        "details",
        "views",
        "registration",
    ]
