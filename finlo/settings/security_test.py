"""Settings for authorization tests isolated from configured development databases."""

from finlo.settings import *  # noqa: F403

from django.core.exceptions import ImproperlyConfigured

# Daphne is a server integration, not a model or authorization dependency.
# Importing it during Django app population creates an asyncio self-pipe on
# Windows, which can block indefinitely before isolated tests are discovered.
# Keep the production app list unchanged and omit only this server app from
# the dedicated in-memory security-test settings.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "daphne"]

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
