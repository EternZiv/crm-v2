"""Views for the calendar app in Finlo"""

from finlo.contrib.calendar.views.calendar_events import GetCalendarEventsView, MarkCompletedView
from finlo.contrib.calendar.views.core import CalendarView, SaveCalendarPreferencesView
from finlo.contrib.calendar.views.custom_calendar import CustomCalendarDeleteView, CustomCalendarFormView
from finlo.contrib.calendar.views.helpers import (
    DEFAULT_CALENDAR_TYPE_COLORS,
    DEFAULT_STATUS_COLORS,
    DEFAULT_TEXT_COLOR,
    HEX_COLOR_RE,
    TEXT_COLOR_PREFIX,
    _requested_range,
    _team_members,
    events_for_custom_calendar,
)
from finlo.contrib.calendar.views.unavailability import UserAvailabilityDeleteView, UserAvailabilityFormView

__all__ = [
    "CalendarView",
    "SaveCalendarPreferencesView",
    "GetCalendarEventsView",
    "MarkCompletedView",
    "CustomCalendarFormView",
    "CustomCalendarDeleteView",
    "UserAvailabilityFormView",
    "UserAvailabilityDeleteView",
    "DEFAULT_CALENDAR_TYPE_COLORS",
    "DEFAULT_STATUS_COLORS",
    "DEFAULT_TEXT_COLOR",
    "HEX_COLOR_RE",
    "TEXT_COLOR_PREFIX",
    "_requested_range",
    "_team_members",
    "events_for_custom_calendar",
]
