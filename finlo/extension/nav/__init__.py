"""
Finlo _inherit_nav — compose concrete target nav views from extension apps.
"""

from finlo.extension.nav.bootstrap import apply_nav_extensions
from finlo.extension.nav.debug import get_nav_extensions, print_nav_view_mro
from finlo.extension.nav.metaclass import NavExtension
from finlo.extension.nav.registry import NAV_COMPOSED_MAP, NAV_EXTENSION_REGISTRY
from finlo.extension.nav.resolve import (
    clear_nav_extension_cache,
    resolve_nav_view_class,
)

__all__ = [
    "NavExtension",
    "NAV_EXTENSION_REGISTRY",
    "NAV_COMPOSED_MAP",
    "apply_nav_extensions",
    "resolve_nav_view_class",
    "clear_nav_extension_cache",
    "get_nav_extensions",
    "print_nav_view_mro",
]
