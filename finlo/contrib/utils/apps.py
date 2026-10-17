"""
App configuration for the Finlo utilities module.

This file defines the configuration class for the Finlo utilities
application, specifying its metadata and settings.
"""

# First party imports (Finlo)
from finlo.apps import AppLauncher


class UtilsConfig(AppLauncher):
    """
    Configuration class for the Finlo utilities application.

    This class specifies the default auto field type and the name of
    the application, which is used by Django to identify the app.
    """

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.utils"
    label = "utils"
