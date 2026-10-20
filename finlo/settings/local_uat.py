"""Settings for local UAT browser testing isolated from configured development/production databases."""

import os
from pathlib import Path

os.environ["DJANGO_SETTINGS_MODULE"] = "finlo.settings.local_uat"

from finlo.settings import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

UAT_DB_PATH = Path(BASE_DIR) / "uat_disposable.sqlite3"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(UAT_DB_PATH),
    }
}

# In-memory email backend for UAT testing
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
