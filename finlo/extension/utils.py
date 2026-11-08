"""Shared utility functions for Finlo extension system."""

from django.apps import apps as django_apps
from django.core.exceptions import AppRegistryNotReady


def resolve_extension_app_label(module_name: str) -> str:
    """
    Resolve the containing app label for an extension module.
    Falls back to the top-level module prefix if the app registry is not ready.
    """
    if not module_name:
        return ""
    try:
        config = django_apps.get_containing_app_config(module_name)
        if config:
            return config.label
    except AppRegistryNotReady:
        pass
    return module_name.split(".")[0]

