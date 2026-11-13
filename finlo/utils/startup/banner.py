"""
Replace only the runserver ``Django version …`` banner line with Finlo CRM's version.

Installed from ``manage.py`` — no extra INSTALLED_APPS entry required.
"""

from __future__ import annotations

import sys

_installed = False


def install() -> None:
    """Patch Daphne runserver to show the Finlo CRM version."""
    global _installed
    if _installed:
        return

    # Importing Daphne's runserver command creates an asyncio event loop. On
    # Windows that initializes a socketpair, which can block ordinary Django
    # management commands (including check/test) even though they do not use
    # Daphne. Only load the command when it is actually being invoked.
    if len(sys.argv) < 2 or sys.argv[1] != "runserver":
        return

    _installed = True

    from daphne.management.commands.runserver import Command as DaphneCommand

    from finlo.__version__ import __version__ as FINLO_VERSION

    original_inner_run = DaphneCommand.inner_run

    def get_version(self):
        return FINLO_VERSION

    def inner_run(self, *args, **options):
        original_write = self.stdout.write

        def write(msg="", *a, **kw):
            if isinstance(msg, str) and msg.startswith("Django version "):
                msg = "Finlo CRM version " + msg[len("Django version ") :]
            return original_write(msg, *a, **kw)

        self.stdout.write = write
        try:
            return original_inner_run(self, *args, **options)
        finally:
            self.stdout.write = original_write

    DaphneCommand.get_version = get_version
    DaphneCommand.inner_run = inner_run
