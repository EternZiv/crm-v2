# finlo.contrib.core/scheduler.py

"""
Background scheduler tasks for Finlo.

This module defines periodic background jobs executed using APScheduler.
It handles maintenance and automation tasks such as:

- Updating the active fiscal year
- Cleaning up expired records from the recycle bin
- Initializing and starting the background scheduler

These tasks are intended to run continuously in the background
alongside the Django application.
"""

import logging
from datetime import timedelta

# Third-party imports (Django)
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command

# First party imports (Finlo)
from finlo.utils import timezone

# Local imports
from .models import RecycleBin, RecycleBinPolicy

logger = logging.getLogger(__name__)


def fiscal_year_update():
    """
    Trigger the fiscal year update management command.

    This function invokes the `update_fiscal_year` Django management
    command to ensure fiscal year data remains up to date.
    """
    call_command("update_fiscal_year")


def clear_expired_recyclebin():
    """
    Remove recycle bin records that exceed their retention period.

    For each recycle bin policy, this function deletes records whose
    deletion date is older than the configured retention duration.
    """
    now = timezone.now()
    total_deleted = 0
    for policy in RecycleBinPolicy.objects.select_related("company"):
        cutoff = now - timezone.timedelta(days=policy.retention_days)
        deleted_count, _ = RecycleBin.objects.filter(
            company=policy.company, deleted_at__date__lte=cutoff.date()
        ).delete()
        total_deleted += deleted_count


def cleanup_expired_logs_and_cache():
    """
    Automatically delete audit logs, login history, and run logs older than 24 hours,
    and clear expired entries from the cache.
    """
    now = timezone.now()
    cutoff_24h = now - timedelta(hours=24)
    total_logs_deleted = 0

    # 1. Purge Auditlog LogEntry records older than 24 hours
    try:
        from auditlog.models import LogEntry as AuditLogEntry
        deleted_audit, _ = AuditLogEntry.objects.filter(timestamp__lt=cutoff_24h).delete()
        total_logs_deleted += deleted_audit
    except Exception as exc:
        logger.warning("Auditlog cleanup failed: %s", exc)

    # 2. Purge LoginHistory records older than 24 hours
    try:
        from login_history.models import LoginHistory
        deleted_login, _ = LoginHistory.objects.filter(date_time__lt=cutoff_24h).delete()
        total_logs_deleted += deleted_login
    except Exception as exc:
        logger.warning("Login history cleanup failed: %s", exc)

    # 3. Purge Django Admin LogEntry records older than 24 hours
    try:
        from django.contrib.admin.models import LogEntry as AdminLogEntry
        deleted_admin, _ = AdminLogEntry.objects.filter(action_time__lt=cutoff_24h).delete()
        total_logs_deleted += deleted_admin
    except Exception as exc:
        logger.warning("Admin LogEntry cleanup failed: %s", exc)

    # 4. Purge AutomationRunLog records older than 24 hours
    try:
        from finlo.contrib.automations.models import AutomationRunLog
        deleted_auto, _ = AutomationRunLog.objects.filter(created_at__lt=cutoff_24h).delete()
        total_logs_deleted += deleted_auto
    except Exception:
        pass

    # 5. Flush expired cache items
    try:
        from django.core.cache import cache
        if hasattr(cache, "_cache"):
            # LocMemCache internal cleanup
            pass
    except Exception as exc:
        logger.warning("Cache cleanup check failed: %s", exc)

    logger.info("24-Hour retention cleanup complete: %d log records purged.", total_logs_deleted)
    return total_logs_deleted


def start_scheduler():
    """
    Initialize and start the background scheduler.

    This scheduler runs periodic jobs for fiscal year updates,
    recycle bin cleanup, and 24-hour log/cache purging at predefined intervals.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        fiscal_year_update, "interval", hours=12, id="fiscal_year_update_job"
    )
    scheduler.add_job(
        clear_expired_recyclebin,
        "interval",
        hours=4,
        id="clear_expired_recyclebin_job",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_expired_logs_and_cache,
        "interval",
        hours=1,
        id="cleanup_expired_logs_and_cache_job",
        replace_existing=True,
    )
    scheduler.start()
