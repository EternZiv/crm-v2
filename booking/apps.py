"""
App configuration for the booking app.
"""

from finlo.apps import AppLauncher
from finlo.utils.translation import gettext_lazy as _


class BookingConfig(AppLauncher):
    """
    Configuration class for the booking app in Finlo.
    """

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "booking"
    verbose_name = _("Booking")

    url_prefix = "booking/"
    url_module = "booking.urls"
    url_namespace = "booking"

    auto_import_modules = [
        "registration",
        "signals",
        "menu",
    ]

    celery_schedule_module = "celery_schedules"
    celery_schedule_variable = "FINLO_BEAT_SCHEDULE"
