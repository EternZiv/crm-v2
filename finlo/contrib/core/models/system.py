"""
This module defines the system models for the Finlo platform,
including settings and about system information.
"""

# Standard library imports
import logging

# First party imports (Finlo)
from finlo.db import models
from finlo.registry.permission_registry import permission_exempt_model
from finlo.utils.translation import gettext_lazy as _

# Local imports
from .base import FinloCoreModel

logger = logging.getLogger(__name__)


class FinloSettings(models.Model):
    """
    Finlo Settings model for permission management
    """

    class Meta:
        """
        Meta options for the FinloSettings model.
        """

        managed = False
        default_permissions = ()
        permissions = (("can_view_finlo_settings", _("Can View Global Settings")),)
        verbose_name = _("Global Settings")


class FinloAboutSystem(models.Model):
    """
    Finlo About System model for permission management
    """

    class Meta:
        """
        Meta options for the FinloAboutSystem model.
        """

        managed = False
        default_permissions = ()
        permissions = (("can_view_finlo_about_system", _("Can View About System")),)
        verbose_name = _("About System")


@permission_exempt_model
class ActiveTab(FinloCoreModel):
    """
    ActiveTab
    """

    path = models.CharField(max_length=256)
    tab_target = models.CharField(max_length=256)


# Backwards compatibility aliases
FinloSettings = FinloSettings
FinloAboutSystem = FinloAboutSystem
