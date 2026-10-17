"""
Finlo _inherit_model extension system (_inherit_model on FinloCoreModel).
"""

from finlo.extension.models.autodetect import FinloAutodetector
from finlo.extension.models.metaclass import EXTENSION_REGISTRY, ExtensionModelBase
from finlo.extension.models.migration_ops import (
    AlterInjectedField,
    InjectField,
    RemoveInjectedField,
)
from finlo.extension.models.registry import INJECTION_MAP, lookup_injection_owner

__all__ = [
    "FinloAutodetector",
    "ExtensionModelBase",
    "EXTENSION_REGISTRY",
    "INJECTION_MAP",
    "lookup_injection_owner",
    "InjectField",
    "AlterInjectedField",
    "RemoveInjectedField",
]
