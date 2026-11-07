"""
Finlo _inherit_kanban — compose FinloKanbanView from extension apps.
"""

from finlo.extension.kanban.bootstrap import apply_kanban_extensions
from finlo.extension.kanban.debug import get_kanban_extensions, print_kanban_view_mro
from finlo.extension.kanban.metaclass import KanbanExtension
from finlo.extension.kanban.registry import (
    KANBAN_COMPOSED_MAP,
    KANBAN_EXTENSION_REGISTRY,
)
from finlo.extension.kanban.resolve import (
    clear_kanban_extension_cache,
    get_resolved_kanban_view_path,
    resolve_kanban_view_class,
)

__all__ = [
    "KanbanExtension",
    "KANBAN_EXTENSION_REGISTRY",
    "KANBAN_COMPOSED_MAP",
    "apply_kanban_extensions",
    "resolve_kanban_view_class",
    "get_resolved_kanban_view_path",
    "clear_kanban_extension_cache",
    "get_kanban_extensions",
    "print_kanban_view_mro",
]
