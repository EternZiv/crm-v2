"""
Shared constants for Finlo generics forms.

Kept in a leaf module with no internal imports so both
finlo.contrib.generics.forms and finlo.contrib.core.forms.helpers
can import from here without creating a circular dependency.
"""

FINLO_FORM_EXCLUDE = [
    "company",
    "is_active",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "additional_info",
]
