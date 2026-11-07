"""
App configuration for the approvals app.
"""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class ApprovalsConfig(AppLauncher):
    """
    Configuration class for the approvals app in Finlo.
    """

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "finlo.contrib.process.approvals"
    label = "approvals"
    verbose_name = _("Approvals")

    url_prefix = "approvals/"
    url_module = "finlo.contrib.process.approvals.urls"
    url_namespace = "approvals"

    auto_import_modules = [
        "registration",
        "signals",
        "mixin_extensions",
        "view_extensions",
        "menu",
    ]
