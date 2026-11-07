"""
Celery Beat schedule for finlo_booking.
"""

from datetime import timedelta

FINLO_BEAT_SCHEDULE = {
    "send-booking-reminders-every-15min": {
        "task": "booking.tasks.send_booking_reminders",
        "schedule": timedelta(minutes=15),
    },
}
