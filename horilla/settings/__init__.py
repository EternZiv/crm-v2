"""Django settings aggregation for the Horilla project."""

import os as _os
from pathlib import Path as _Path

from django.core.exceptions import ImproperlyConfigured as _ImproperlyConfigured

from horilla.settings.base import *
from horilla.settings import horilla_apps

if _Path(__file__).with_name("local_settings.py").is_file():
    from horilla.settings.local_settings import *

if IS_VERCEL and not _os.environ.get("REDIS_URL"):
    raise _ImproperlyConfigured(
        "Set REDIS_URL to a managed Redis service for Vercel Channels and Celery."
    )
