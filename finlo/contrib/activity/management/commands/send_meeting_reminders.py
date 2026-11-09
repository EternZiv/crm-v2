"""
Management command to send reminders for upcoming meetings.
"""

from django.core.management.base import BaseCommand
from finlo.contrib.activity.tasks import send_meeting_reminders


class Command(BaseCommand):
    help = "Send meeting reminder emails to clients, hosts, and participants for upcoming meetings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force sending reminders even if already cached as sent.",
        )
        parser.add_argument(
            "--upcoming-hours",
            type=int,
            default=None,
            help="Scan all upcoming meetings starting in the next N hours.",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        upcoming_hours = options.get("upcoming_hours")

        self.stdout.write(
            self.style.NOTICE(
                f"Checking upcoming meetings (force={force}, upcoming_hours={upcoming_hours})..."
            )
        )
        result = send_meeting_reminders(force=force, upcoming_hours=upcoming_hours)
        self.stdout.write(self.style.SUCCESS(result))
