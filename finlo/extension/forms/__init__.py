"""
Finlo _inherit_form — compose concrete target forms from extension apps.
"""

from finlo.extension.forms.bootstrap import apply_form_extensions
from finlo.extension.forms.debug import get_form_extensions, print_form_mro
from finlo.extension.forms.metaclass import FormExtension
from finlo.extension.forms.registry import FORM_COMPOSED_MAP, FORM_EXTENSION_REGISTRY
from finlo.extension.forms.resolve import (
    clear_form_extension_cache,
    resolve_form_class,
)

__all__ = [
    "FormExtension",
    "FORM_EXTENSION_REGISTRY",
    "FORM_COMPOSED_MAP",
    "apply_form_extensions",
    "resolve_form_class",
    "clear_form_extension_cache",
    "get_form_extensions",
    "print_form_mro",
]
