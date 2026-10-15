"""Django settings aggregation for the Horilla project."""

import os as _os
from pathlib import Path as _Path

from django.core.exceptions import ImproperlyConfigured as _ImproperlyConfigured

from horilla.settings.base import *
from horilla.settings import horilla_apps

if _Path(__file__).with_name("local_settings.py").is_file():
    from horilla.settings.local_settings import *

VERCEL_UAT_MODE = _os.environ.get("VERCEL_UAT_MODE", "").strip() == "1"

if VERCEL_UAT_MODE and not IS_VERCEL:
    raise _ImproperlyConfigured(
        "VERCEL_UAT_MODE=1 may only be used on a Vercel deployment."
    )

if IS_VERCEL and VERCEL_UAT_MODE:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }
    USE_ASYNC_AUTOMATIONS = False
    USE_ASYNC_SCORING = False

if IS_VERCEL and not VERCEL_UAT_MODE and not _os.environ.get("REDIS_URL"):
    raise _ImproperlyConfigured(
        "Set REDIS_URL to a managed Redis service for Vercel Channels and Celery."
    )
