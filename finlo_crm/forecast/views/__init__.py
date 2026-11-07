"""Aggregate view modules for the `finlo_crm.forecast.views` package."""

# Local imports
from finlo_crm.forecast.views.core import (
    ForecastChartsModalView,
    ForecastView,
    ForecastNavbarView,
    ForecastTabView,
    ForecastTypeTabView,
    ForecastOpportunitiesView,
)

from finlo_crm.forecast.views.forecast_target import (
    ForecastTargetView,
    ForecastTargetFiltersView,
    ForecastTargetNavbar,
    ForecastTargetListView,
    ForecastTargetFormView,
    ToggleRoleBasedView,
    ToggleConditionFieldsView,
    UpdateTargetHelpTextView,
    UpdateForecastTarget,
    ForecastTargetDeleteView,
)

from finlo_crm.forecast.views.forecast_type import (
    ForecastTypeView,
    ForecastTypeNavbar,
    ForecastTypeListView,
    ForecastTypeFormView,
    ForecastTypeDeleteView,
)

__all__ = [
    # core
    "ForecastView",
    "ForecastNavbarView",
    "ForecastTabView",
    "ForecastTypeTabView",
    "ForecastChartsModalView",
    "ForecastOpportunitiesView",
    # forecast_target
    "ForecastTargetView",
    "ForecastTargetFiltersView",
    "ForecastTargetNavbar",
    "ForecastTargetListView",
    "ForecastTargetFormView",
    "ToggleRoleBasedView",
    "ToggleConditionFieldsView",
    "UpdateTargetHelpTextView",
    "UpdateForecastTarget",
    "ForecastTargetDeleteView",
    # forecast_type
    "ForecastTypeView",
    "ForecastTypeNavbar",
    "ForecastTypeListView",
    "ForecastTypeFormView",
    "ForecastTypeDeleteView",
]
