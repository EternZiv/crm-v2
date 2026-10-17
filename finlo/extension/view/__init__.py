"""
Finlo _inherit_view — compose concrete View subclasses from extension apps.

Resolution hooks live on ``finlo.views.generic.View.as_view`` so any subclass
(e.g. ``EditFieldView``) picks up extensions automatically.
"""

from finlo.extension.view.bootstrap import apply_view_extensions
from finlo.extension.view.metaclass import ViewExtension
from finlo.extension.view.registry import VIEW_COMPOSED_MAP, VIEW_EXTENSION_REGISTRY
from finlo.extension.view.resolve import (
    clear_view_extension_cache,
    resolve_view_class,
)

__all__ = [
    "ViewExtension",
    "VIEW_EXTENSION_REGISTRY",
    "VIEW_COMPOSED_MAP",
    "apply_view_extensions",
    "resolve_view_class",
    "clear_view_extension_cache",
]
