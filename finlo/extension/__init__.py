"""
Finlo extension package: model _inherit_model and form _inherit_form.

Patches makemigrations and migrate to use FinloAutodetector so injected fields
generate migrations in the owning extension app, not in the target app.
"""

from finlo.extension.models import (
    EXTENSION_REGISTRY,
    INJECTION_MAP,
    AlterInjectedField,
    ExtensionModelBase,
    FinloAutodetector,
    InjectField,
    RemoveInjectedField,
)

__all__ = [
    "FinloAutodetector",
    "ExtensionModelBase",
    "EXTENSION_REGISTRY",
    "INJECTION_MAP",
    "InjectField",
    "AlterInjectedField",
    "RemoveInjectedField",
]


def _patch_migration_autodetectors():
    try:
        from django.core.management.commands.makemigrations import (
            Command as MakeMigrationsCommand,
        )
        from django.core.management.commands.migrate import Command as MigrateCommand

        MakeMigrationsCommand.autodetector = FinloAutodetector
        MigrateCommand.autodetector = FinloAutodetector
    except ImportError:
        pass


_patch_migration_autodetectors()
