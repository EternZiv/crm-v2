"""
Finlo generics views package.

Aggregates generic list, detail, form, kanban, group-by, and helper views.
Import order is significant to avoid circular imports.
"""

from finlo.contrib.generics.views.core import (
    FinloView,
    FinloTabView,
    FinloHistorySectionView,
    FinloDynamicCreateView,
)
from finlo.contrib.generics.views.delete import FinloSingleDeleteView
from finlo.contrib.generics.views.details import (
    FinloDetailView,
    FinloModalDetailView,
    resolves_within_settings_shell,
)
from finlo.contrib.generics.views.list import FinloListView
from finlo.contrib.generics.views.card import FinloCardView
from finlo.contrib.generics.views.split_view import FinloSplitView
from finlo.contrib.generics.views.detail_tabs import (
    FinloDetailTabView,
    FinloDetailSectionView,
)
from finlo.contrib.generics.views.groupby import FinloGroupByView
from finlo.contrib.generics.views.chart import (
    ChartConfigJSONEncoder,
    FinloChartView,
)
from finlo.contrib.generics.views.kanban import FinloKanbanView
from finlo.contrib.generics.views.timeline import FinloTimelineView
from finlo.contrib.generics.views.attachments import (
    AttachmentListView,
    FinloNotesAttachementSectionView,
    FinloNotesAttachementDetailView,
    FinloNotesAttachmentCreateView,
    FinloNotesAttachmentDeleteView,
)
from finlo.contrib.generics.views.global_search import GlobalSearchView
from finlo.contrib.generics.views.related_list import (
    FinloRelatedListSectionView,
    FinloRelatedListContentView,
)
from finlo.contrib.generics.views.single_form import FinloSingleFormView
from finlo.contrib.generics.views.multi_form import FinloMultiStepFormView
from finlo.contrib.generics.views.navbar import FinloNavView

__all__ = [
    # Core Views
    "FinloView",
    "FinloTabView",
    "FinloHistorySectionView",
    "FinloDynamicCreateView",
    # Delete View
    "FinloSingleDeleteView",
    # Detail Views
    "FinloDetailView",
    "FinloModalDetailView",
    # List View
    "FinloListView",
    # Card View
    "FinloCardView",
    # Split View
    "FinloSplitView",
    # Detail Tabs
    "FinloDetailTabView",
    "FinloDetailSectionView",
    # GroupBy Views
    "FinloGroupByView",
    # Chart Views
    "ChartConfigJSONEncoder",
    "FinloChartView",
    # Kanban Views
    "FinloKanbanView",
    # Timeline Views
    "FinloTimelineView",
    # Attachment Views
    "AttachmentListView",
    "FinloNotesAttachementSectionView",
    "FinloNotesAttachementDetailView",
    "FinloNotesAttachmentCreateView",
    "FinloNotesAttachmentDeleteView",
    # Global Search
    "GlobalSearchView",
    # Related List
    "FinloRelatedListSectionView",
    "FinloRelatedListContentView",
    # Single Form View
    "FinloSingleFormView",
    # Multi Form Views
    "FinloMultiStepFormView",
    # Navbar View
    "FinloNavView",
]
