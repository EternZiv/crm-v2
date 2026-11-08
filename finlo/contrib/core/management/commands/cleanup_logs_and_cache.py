"""
Management command to clean up logs and expired cache entries older than 24 hours.
"""

from django.core.management.base import BaseCommand
from finlo.contrib.core.scheduler import cleanup_expired_logs_and_cache


class Command(BaseCommand):
    help = "Deletes all audit logs, login history, and admin logs older than 24 hours, and prunes cache."

    def handle(self, *args, **options):
        self.stdout.write("Running 24-hour log and cache cleanup...")
        purged = cleanup_expired_logs_and_cache()
        self.stdout.write(self.style.SUCCESS(f"Successfully purged {purged} log entries older than 24 hours."))

