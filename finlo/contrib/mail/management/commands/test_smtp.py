"""
Management command to test SMTP connectivity and credentials.
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Send a test email to verify SMTP host, port, user, and app password."

    def add_arguments(self, parser):
        parser.add_argument("recipient", type=str, help="Recipient email address to test sending to.")

    def handle(self, *args, **options):
        recipient = options["recipient"]
        host = getattr(settings, "EMAIL_HOST", "not set")
        port = getattr(settings, "EMAIL_PORT", "not set")
        user = getattr(settings, "EMAIL_HOST_USER", "not set")

        self.stdout.write(
            self.style.NOTICE(
                f"Testing SMTP with host={host}:{port}, user={user} -> recipient={recipient}..."
            )
        )

        try:
            send_mail(
                subject="Finlo CRM - SMTP Test Email",
                message=(
                    "Congratulations! Your Finlo CRM SMTP email setup is working correctly.\n\n"
                    "Meeting invitations and reminders will now be dispatched automatically."
                ),
                from_email=None,
                recipient_list=[recipient],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully sent test email to {recipient}!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send test email: {e}"))

