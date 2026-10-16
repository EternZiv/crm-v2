"""Branding configuration utilities for Finlo CRM."""

from importlib import import_module

from django.conf import settings
from django.utils.translation import gettext_lazy as _

DEFAULTS = {
    "TITLE": _("Finlo CRM"),
    "LOGIN_WELCOME_LINE": _("Welcome to Finlo CRM"),
    "LOGIN_TAG_LINE": _("Please sign in to access your dashboard"),
    "SIGNUP_TAG_LINE": _("Please sign up to access Finlo CRM"),
    "LOGO_PATH": "assets/img/finlo-crm-logo.png",
    "FAVICON_PATH": "assets/img/finlo-favicon.ico",
    "PAGE_HEADER": _("Finlo CRM"),
}


def load_branding():
    """
    Loads branding values from an optional module defined in settings.
    Falls back to DEFAULTS when not defined.
    """

    branding = DEFAULTS.copy()

    module_path = getattr(settings, "BRANDING_MODULE", None)

    if not module_path:
        return branding

    try:
        module = import_module(module_path)
    except Exception as e:
        print(e)
        return branding

    for key in DEFAULTS.keys():
        if hasattr(module, key):
            branding[key] = getattr(module, key)

    return branding
