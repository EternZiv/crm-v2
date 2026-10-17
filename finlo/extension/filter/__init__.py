"""
Finlo _inherit_filter — compose concrete target filtersets from extension apps.
"""

from finlo.extension.filter.bootstrap import apply_filter_extensions
from finlo.extension.filter.debug import get_filter_extensions, print_filter_mro
from finlo.extension.filter.metaclass import FilterExtension
from finlo.extension.filter.registry import (
    FILTER_COMPOSED_MAP,
    FILTER_EXTENSION_REGISTRY,
)
from finlo.extension.filter.resolve import (
    clear_filter_extension_cache,
    resolve_filterset_class,
)


def _register_checks() -> None:
    import importlib

    importlib.import_module("finlo.extension.filter.checks")


_register_checks()

__all__ = [
    "FilterExtension",
    "FILTER_EXTENSION_REGISTRY",
    "FILTER_COMPOSED_MAP",
    "apply_filter_extensions",
    "resolve_filterset_class",
    "clear_filter_extension_cache",
    "get_filter_extensions",
    "print_filter_mro",
]
