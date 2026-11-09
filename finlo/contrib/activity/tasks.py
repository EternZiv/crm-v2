"""Celery tasks for activity reminders."""

# Standard library imports
import logging
from datetime import timedelta

# Third-party imports (Django)
from celery import shared_task

# First party imports (Finlo)
from finlo.utils import timezone
from finlo.utils.branding import load_branding

logger = logging.getLogger(__name__)


@shared_task
def send_meeting_reminders(force=False, upcoming_hours=None):
    """
    Periodic task: find meetings whose reminder time has arrived and send reminder emails.
    Supports upcoming_hours window or standard reminder intervals, with cache deduplication.
    """
    from django.core.cache import cache
    from finlo.contrib.activity.models import Activity

    now = timezone.now()

    if upcoming_hours:
        meetings = Activity.objects.filter(
            activity_type="meeting",
            start_datetime__gte=now,
            start_datetime__lte=now + timedelta(hours=upcoming_hours),
            status__in=["not_started", "scheduled"],
        )
    else:
        # Find all scheduled/not-started meetings with a reminder set and a start time
        meetings = Activity.objects.filter(
            activity_type="meeting",
            reminder__isnull=False,
            start_datetime__isnull=False,
            status__in=["not_started", "scheduled"],
        ).exclude(reminder="")

    sent_count = 0
    for meeting in meetings:
        cache_key = f"meeting_reminder_sent_{meeting.pk}"
        if not force and cache.get(cache_key):
            continue

        if not upcoming_hours:
            try:
                reminder_minutes = int(meeting.reminder)
            except (ValueError, TypeError):
                continue

            remind_at = meeting.start_datetime - timedelta(minutes=reminder_minutes)

            # Fire if we have reached remind_at and meeting has not passed start time by > 5 min
            if not (remind_at <= now <= meeting.start_datetime + timedelta(minutes=5)):
                continue

        _send_reminder_for_meeting(meeting)
        cache.set(cache_key, True, timeout=86400 * 7)
        sent_count += 1

    logger.info("Meeting reminders sent: %d", sent_count)
    return f"Sent {sent_count} meeting reminders"


def _localtime_for_meeting(dt, meeting):
    """Convert a UTC-aware datetime using user.time_zone → company.time_zone → UTC."""
    if dt is None:
        return None
    try:
        from zoneinfo import ZoneInfo

        host_user = meeting.meeting_host or meeting.owner
        tz_name = (
            getattr(host_user, "time_zone", None) if host_user else None
        ) or getattr(meeting.company, "time_zone", None)
        if tz_name:
            return dt.astimezone(ZoneInfo(tz_name))
    except Exception:
        pass
    return dt  # return as-is (UTC) rather than silently wrong local time


def _send_reminder_for_meeting(meeting):
    """Send reminder email to all participants and external participants."""
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives, get_connection

    title = meeting.title or meeting.subject or "Meeting"
    meeting_url = meeting.meeting_url or ""
    start = meeting.start_datetime
    reminder_minutes = int(meeting.reminder)
    host_user = meeting.meeting_host or meeting.owner
    host_name = str(host_user or "")

    local_start = _localtime_for_meeting(start, meeting)
    start_str = (
        local_start.strftime("%A, %B %d, %Y at %I:%M %p") if local_start else "TBD"
    )

    if reminder_minutes >= 1440:
        reminder_label = "1 day"
    elif reminder_minutes >= 60:
        reminder_label = f"{reminder_minutes // 60} hour(s)"
    else:
        reminder_label = f"{reminder_minutes} minutes"

    # Collect recipients: internal participants + external + client (related_object: Lead/Contact)
    recipient_emails = list(
        meeting.participants.exclude(email="").values_list("email", flat=True)
    )
    external = meeting.external_participants or []
    if isinstance(external, list):
        recipient_emails += [e for e in external if isinstance(e, str) and e.strip()]

    related = getattr(meeting, "related_object", None)
    if related:
        r_email = getattr(related, "email", None)
        if r_email and str(r_email).strip():
            recipient_emails.append(str(r_email).strip())

    all_recipients = list(dict.fromkeys(recipient_emails))  # dedup

    if not all_recipients:
        return

    # Resolve outgoing mail config
    mail_config = None
    try:
        from finlo.contrib.mail.models import FinloMailConfiguration

        company = meeting.company
        mail_config = (
            FinloMailConfiguration.objects.filter(
                company=company, mail_channel="outgoing", is_primary=True
            ).first()
            or FinloMailConfiguration.objects.filter(
                mail_channel="outgoing", is_primary=True
            ).first()
            or FinloMailConfiguration.objects.filter(mail_channel="outgoing").first()
        )
    except Exception:
        pass

    company_name = (
        str(meeting.company) if meeting.company else str(load_branding()["TITLE"])
    )

    html_body = f"""
<div style="max-width:650px;margin:auto;background:white;border-radius:12px;padding:35px;box-shadow:0 4px 12px rgba(0,0,0,0.08);font-family:Inter,Arial,sans-serif">
  <h2 style="color:#1e293b;text-align:center;font-size:24px;margin-bottom:20px;font-weight:700">
    Meeting Reminder
  </h2>

  <p style="font-size:15px;color:#334155;line-height:1.6">
    Your meeting with <strong>{host_name}</strong> is starting soon.
  </p>

  <div style="margin:20px 0;padding:16px 20px;background:#f8fafc;border-left:4px solid #6366f1;border-radius:8px">
    <p style="margin:6px 0;font-size:15px;color:#1e293b">
      &#128197; <strong>Topic:</strong> {title}
    </p>
    <p style="margin:6px 0;font-size:15px;color:#1e293b">
      &#128336; <strong>Scheduled Time:</strong> <span style="color:#4338ca;font-weight:600">{start_str}</span> (starts in {reminder_label})
    </p>
    <p style="margin:6px 0;font-size:15px;color:#1e293b">
      &#128100; <strong>Host:</strong> {host_name}
    </p>
    {f'<p style="margin:6px 0;font-size:15px;color:#1e293b">&#128279; <strong>Join Link:</strong> <a href="{meeting_url}" style="color:#4f46e5;font-weight:500;">{meeting_url}</a></p>' if meeting_url else ""}
  </div>

  <div style="margin:20px 0;padding:14px 18px;background:#fef3c7;border-left:4px solid #f59e0b;border-radius:8px">
    <p style="margin:0;font-size:14px;color:#92400e;font-weight:600">
      &#9888; Upcoming Meeting Alert — Please be ready!
    </p>
    <p style="margin:6px 0 0 0;font-size:13px;color:#78350f;line-height:1.5">
      Your meeting starts in <strong>{reminder_label}</strong> ({start_str}). Please ensure you have your notes and connection ready to join promptly.
    </p>
  </div>

  {f'<div style="text-align:center;margin-top:25px"><a href="{meeting_url}" style="display:inline-block;padding:12px 28px;background-color:#4f46e5;color:white;text-decoration:none;border-radius:6px;font-weight:600;font-size:15px">Join Meeting</a></div>' if meeting_url else ""}

  <hr style="margin:30px 0;border:none;border-top:1px solid #e2e8f0">

  <p style="font-size:12px;color:#64748b;text-align:center;line-height:1.5">
    This reminder was sent via <strong>{company_name}</strong>.<br>
    If you were not expecting this, please ignore this email.
  </p>
</div>"""

    plain_body = (
        f"Upcoming Meeting Reminder: {title}\n\n"
        f"Your meeting with {host_name} starts in {reminder_label}.\n\n"
        f"Scheduled Time: {start_str}\n"
        f"Host: {host_name}\n"
        + (f"Join Link: {meeting_url}\n\n" if meeting_url else "\n")
        + f"PLEASE BE READY: Your meeting starts in {reminder_label} ({start_str}). Please ensure your connection and setup are ready to join promptly.\n\n"
        f"Sent via {company_name}."
    )

    from_email = (
        mail_config.from_email
        if mail_config and mail_config.from_email
        else getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", "noreply@example.com")
    )

    try:
        connection = (
            get_connection("finlo.contrib.mail.backends.FinloDefaultMailBackend")
            if mail_config
            else get_connection()
        )
        for recipient in all_recipients:
            try:
                msg = EmailMultiAlternatives(
                    subject=f"Reminder: {title} starts in {reminder_label} - Please get ready",
                    body=plain_body,
                    from_email=from_email,
                    to=[recipient],
                    connection=connection,
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send(fail_silently=False)
            except Exception as single_err:
                logger.error("Failed to send reminder for meeting %d to %s: %s", meeting.pk, recipient, single_err)
        logger.info("Reminder sent for meeting %d to %s", meeting.pk, all_recipients)
    except Exception as e:
        logger.error("Failed to process reminders for meeting %d: %s", meeting.pk, e)
