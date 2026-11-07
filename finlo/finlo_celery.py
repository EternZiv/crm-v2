"""Celery application configuration for the Finlo project."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finlo.settings")

app = Celery("finlo")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
