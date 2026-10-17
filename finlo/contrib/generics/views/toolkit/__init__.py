"""
Finlo generics view toolkit.

Bulk delete, bulk export, bulk update, quick filter mixins/helpers for list views,
and form_common mixin for single-form and multi-form views.
"""

from finlo.contrib.generics.views.toolkit.bulk_delete import FinloBulkDeleteMixin
from finlo.contrib.generics.views.toolkit.bulk_export import FinloBulkExportMixin
from finlo.contrib.generics.views.toolkit.bulk_update import FinloBulkUpdateMixin
from finlo.contrib.generics.views.toolkit.quick_filter import (
    get_available_quick_filter_fields,
    get_quick_filters,
    get_quick_filter_choices,
    is_valid_quick_filter_value,
    apply_quick_filters,
    handle_quick_filter_post,
    handle_quick_filter_get,
    update_quick_filter_context,
)
from finlo.contrib.generics.views.toolkit.form_mixin import FormViewCommonMixin

__all__ = [
    # Bulk Delete
    "FinloBulkDeleteMixin",
    # Bulk Export
    "FinloBulkExportMixin",
    # Bulk Update
    "FinloBulkUpdateMixin",
    # Quick Filter
    "get_available_quick_filter_fields",
    "get_quick_filters",
    "get_quick_filter_choices",
    "is_valid_quick_filter_value",
    "apply_quick_filters",
    "handle_quick_filter_post",
    "handle_quick_filter_get",
    "update_quick_filter_context",
    # Form Mixin
    "FormViewCommonMixin",
]
