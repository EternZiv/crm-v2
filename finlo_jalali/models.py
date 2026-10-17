"""
``_inherit_model`` — add calendar_system on FinloUser without core migrations.
"""

from finlo.contrib.core.models import FinloCoreModel
from finlo.db import models
from finlo.utils.translation import gettext_lazy as _
from finlo_jalali.calendar import CALENDAR_SYSTEM_CHOICES


class FinloUserJalaliExtension(FinloCoreModel):
    """Inject Shamsi/Gregorian preference onto the user model."""

    _inherit_model = "core.FinloUser"

    calendar_system = models.CharField(
        max_length=20,
        choices=CALENDAR_SYSTEM_CHOICES,
        default="jalali",
        help_text=_(
            "Choose Shamsi (Jalali) or Gregorian dates when your language is Persian."
        ),
        verbose_name=_("Calendar System"),
    )


# Backwards compatibility alias
HorillaUserJalaliExtension = FinloUserJalaliExtension
