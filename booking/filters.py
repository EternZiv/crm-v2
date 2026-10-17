"""
Filters for the finlo_booking app.
"""

from finlo.contrib.generics.filters import FinloFilterSet

from .models import Booking, BookingPage


class BookingPageFilter(FinloFilterSet):
    """Filter for BookingPage list view."""

    class Meta:
        """Meta options for BookingPageFilter."""

        model = BookingPage
        fields = "__all__"
        exclude = ["additional_info", "questions"]
        search_fields = [
            "title",
            "host__username",
            "host__first_name",
            "host__last_name",
        ]


class BookingFilter(FinloFilterSet):
    """Filter for Booking list view."""

    class Meta:
        """Meta options for BookingFilter."""

        model = Booking
        fields = "__all__"
        exclude = [
            "additional_info",
            "answers",
            "cancellation_token",
            "cancellation_reason",
        ]
        search_fields = ["booker_name", "booker_email"]
