"""Views for managing dashboard, including list and detail views with component rendering."""

from finlo.contrib.dashboard.views.core import (
    DashboardNavbar,
    DashboardDetailView,
    DashboardListView,
)

from finlo.contrib.dashboard.views.home import (
    HomePageView,
    SaveDefaultHomeLayoutOrderView,
    ResetDefaultHomeLayoutOrderView,
)

from finlo.contrib.dashboard.views.component import (
    DashboardComponentTableDataView,
    DashboardComponentFormView,
    ComponentDeleteView,
    AddToDashboardForm,
    ReportToDashboardForm,
    ChartViewToDashboardForm,
    ReorderComponentsView,
)

from finlo.contrib.dashboard.views.folder import (
    DashboardFolderCreate,
    DashboardFolderFavoriteView,
    DashboardFolderListView,
    FolderDetailListView,
    FolderDeleteView,
    MoveDashboardView,
    MoveFolderView,
)

from finlo.contrib.dashboard.views.field_choices import (
    ModuleFieldChoicesView,
    ColumnFieldChoicesView,
    GroupingFieldChoicesView,
    SecondaryGroupingFieldChoicesView,
    MetricFieldChoicesView,
    YAxisMetricFieldChoicesView,
)

from finlo.contrib.dashboard.views.chart import (
    ChartPreviewView,
    DashboardComponentChartView,
)

from finlo.contrib.dashboard.views.dashboard_actions import (
    DashboardDefaultToggleView,
    DashboardFavoriteToggleView,
    DashboardCreateFormView,
    DashboardDeleteView,
    ResetDashboardLayoutOrderView,
)

from finlo.contrib.dashboard.views.favourite import (
    FavouriteDashboardListView,
    FavouriteFolderListView,
)

from finlo.contrib.generics.views.helpers.queryset_utils import (
    get_queryset_for_module,
    apply_conditions,
)


from finlo.contrib.dashboard.views.dashboard_helper import (
    get_kpi_data,
    get_report_chart_data,
    get_chart_data,
    get_table_data,
)

__all__ = [
    # core
    "DashboardNavbar",
    "DashboardDetailView",
    "DashboardListView",
    # home
    "HomePageView",
    "SaveDefaultHomeLayoutOrderView",
    "ResetDefaultHomeLayoutOrderView",
    # components
    "DashboardComponentTableDataView",
    "DashboardComponentFormView",
    "ComponentDeleteView",
    "AddToDashboardForm",
    "ReportToDashboardForm",
    "ChartViewToDashboardForm",
    "ReorderComponentsView",
    # folders
    "DashboardFolderCreate",
    "DashboardFolderFavoriteView",
    "DashboardFolderListView",
    "FolderDetailListView",
    "FolderDeleteView",
    "MoveDashboardView",
    "MoveFolderView",
    # field choices
    "ModuleFieldChoicesView",
    "ColumnFieldChoicesView",
    "GroupingFieldChoicesView",
    "SecondaryGroupingFieldChoicesView",
    "MetricFieldChoicesView",
    "YAxisMetricFieldChoicesView",
    # charts
    "ChartPreviewView",
    "DashboardComponentChartView",
    # dashboard actions
    "DashboardDefaultToggleView",
    "DashboardFavoriteToggleView",
    "DashboardCreateFormView",
    "DashboardDeleteView",
    "ResetDashboardLayoutOrderView",
    # favourites
    "FavouriteDashboardListView",
    "FavouriteFolderListView",
    # helpers (public)
    "get_queryset_for_module",
    "get_kpi_data",
    "get_report_chart_data",
    "get_chart_data",
    "apply_conditions",
    "get_table_data",
]
