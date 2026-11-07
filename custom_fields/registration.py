"""
Feature registration for the custom_fields app.

Mirrors finlo.contrib.duplicates: custom_fields declares a feature here,
and any app opts its model in with a plain
``register_model_for_feature(..., features=["custom_fields_models"])``
call from its own ``registration.py`` (see ``finlo_crm/leads/registration.py``).
No form/view classes are registered by name — ``custom_fields/extensions/forms.py``
and ``custom_fields/extensions/detail.py`` discover opted-in models from
this registry at runtime and register real ``FormExtension``/
``DetailExtension``/``DetailSectionExtension`` classes for them.
"""

# First party imports (Finlo)
from finlo.registry.feature import register_feature

register_feature(
    "custom_fields",
    "custom_fields_models",
    auto_register_all=False,
)
