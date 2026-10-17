"""
Finlo _inherit_formatter — compose DateTimeFormatter from extension apps.
"""

from finlo.extension.formatting.bootstrap import apply_formatter_extensions
from finlo.extension.formatting.metaclass import DateTimeFormatterExtension
from finlo.extension.formatting.registry import (
    FORMATTER_COMPOSED_MAP,
    FORMATTER_EXTENSION_REGISTRY,
)
from finlo.extension.formatting.resolve import (
    clear_formatter_extension_cache,
    get_datetime_formatter,
    resolve_datetime_formatter_class,
)

__all__ = [
    "DateTimeFormatterExtension",
    "FORMATTER_EXTENSION_REGISTRY",
    "FORMATTER_COMPOSED_MAP",
    "apply_formatter_extensions",
    "resolve_datetime_formatter_class",
    "get_datetime_formatter",
    "clear_formatter_extension_cache",
]
