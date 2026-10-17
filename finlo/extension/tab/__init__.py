"""
Finlo _inherit_tab — compose FinloTabView subclasses from extension apps.

Resolution hooks live on ``FinloTabView.as_view`` so concrete tab views
(e.g. ``CompanyInformationTabView``) pick up extensions automatically.
"""

from finlo.extension.tab.bootstrap import apply_tab_extensions
from finlo.extension.tab.metaclass import TabExtension
from finlo.extension.tab.registry import TAB_COMPOSED_MAP, TAB_EXTENSION_REGISTRY
from finlo.extension.tab.resolve import (
    clear_tab_extension_cache,
    resolve_tab_view_class,
)

__all__ = [
    "TabExtension",
    "TAB_EXTENSION_REGISTRY",
    "TAB_COMPOSED_MAP",
    "apply_tab_extensions",
    "resolve_tab_view_class",
    "clear_tab_extension_cache",
]
