"""
Finlo generics app configuration.

This module defines the AppLauncher for the finlo.contrib.generics application and performs
application startup tasks such as URL registration and signal imports.
"""

# First party imports (Finlo)
from finlo.apps import AppLauncher


class GenericsConfig(AppLauncher):
    """App configuration for finlo.contrib.generics application."""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.generics"
    label = "generics"

    url_prefix = "generics/"
    url_module = "finlo.contrib.generics.urls"
    url_namespace = "generics"

    auto_import_modules = ["signals"]
