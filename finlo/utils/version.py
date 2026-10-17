"""
Version information utilities for Finlo modules.

This module provides functions to retrieve and collect version information
from installed Finlo modules, including version numbers, descriptions,
icons, and changelog (version-specific features).
"""

import re
from importlib import import_module

from django.conf import settings

from finlo import __version__ as finlo_version

# Pattern for changelog attributes: __1_2_0__ -> version "1.2.0"
CHANGELOG_ATTR_PATTERN = re.compile(r"^__(\d+)_(\d+)_(\d+)__$")


def _get_changelog_from_module(mod):
    """Collect changelog entries from a __version__ module. Returns list of {version, description}."""
    changelog = []
    for attr_name in dir(mod):
        match = CHANGELOG_ATTR_PATTERN.match(attr_name)
        if match:
            version = ".".join(match.groups())
            description = getattr(mod, attr_name, "")
            if description:
                changelog.append({"version": version, "description": description})
    # Sort by version descending (newest first)
    changelog.sort(key=lambda x: tuple(map(int, x["version"].split("."))), reverse=True)
    return changelog


def get_module_version_info(module_name):
    """Return module version info as a dict: {name, version, description, icon, changelog, release_date}."""
    try:
        mod = import_module(f"{module_name}.__version__")

        return {
            "name": getattr(mod, "__module_name__", module_name),
            "version": getattr(mod, "__version__", "Unknown"),
            "description": getattr(mod, "__description__", ""),
            "icon": getattr(mod, "__icon__", ""),
            "release_date": getattr(mod, "__release_date__", ""),
            "changelog": _get_changelog_from_module(mod),
        }

    except ModuleNotFoundError:
        return None


def collect_all_versions():
    """Collect version info for all Finlo modules (including nested ones)."""

    versions = [
        {
            "name": finlo_version.__module_name__,
            "version": finlo_version.__version__,
            "description": finlo_version.__description__,
            "icon": getattr(finlo_version, "__icon__", ""),
            "release_date": getattr(finlo_version, "__release_date__", ""),
            "changelog": _get_changelog_from_module(finlo_version),
        }
    ]

    seen = set()
    seen.add("finlo.contrib.core")
    seen.add("finlo")
    for app in settings.INSTALLED_APPS:
        module_parts = app.split(".")

        # Try progressively deeper module paths
        for i in range(len(module_parts), 0, -1):
            module_path = ".".join(module_parts[:i])

            if module_path in seen:
                continue

            info = get_module_version_info(module_path)

            if info:
                versions.append(info)
                seen.add(module_path)
                break  # stop once the most specific match is found
    return {
        "module_versions": versions,
    }
