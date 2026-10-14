"""Settings for authorization tests isolated from configured development databases."""

from horilla.settings import *

from django.core.exceptions import ImproperlyConfigured

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {"NAME": ":memory:"},
    }
}

if any(
    config.get("ENGINE") != "django.db.backends.sqlite3"
    or config.get("NAME") != ":memory:"
    or config.get("TEST", {}).get("NAME") != ":memory:"
    for config in DATABASES.values()
):
    raise ImproperlyConfigured(
        "Security tests require SQLite in-memory databases for every database alias."
    )
