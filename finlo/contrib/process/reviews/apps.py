"""App configuration for the `reviews` app."""

# First party imports (Finlo)
from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class ReviewProcessConfig(AppLauncher):
    """Review Process app configuration."""

    default = True
    default_auto_field = "django.db.models.BigAutoField"

    name = "finlo.contrib.process.reviews"
    label = "reviews"
    verbose_name = _("Review Process")

    # Mounted under this prefix by AppLauncher
    url_prefix = "review-process/"
    url_module = "finlo.contrib.process.reviews.urls"
    url_namespace = "reviews"

    auto_import_modules = [
        "registration",
        "signals",
        "list_visibility",
        "menu",
        "view_extensions",
    ]
