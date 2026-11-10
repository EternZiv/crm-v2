"""
Custom runserver management command for Finlo CRM.

Subclasses Daphne's ASGI runserver command and sets `use_static_handler=False`
by default so that WhiteNoiseMiddleware handles static files in local development.
This ensures proper Cache-Control, ETag, Last-Modified, and HTTP 304 revalidation
headers are sent instead of Daphne's un-cached ASGIStaticFilesHandler.
"""

from daphne.management.commands.runserver import Command as DaphneRunserverCommand


class Command(DaphneRunserverCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.set_defaults(use_static_handler=False)

