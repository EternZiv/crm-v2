"""
``_inherit_detail`` — show calendar_system on the user detail Localization section.
"""

from finlo.extension.detail import DetailExtension


class UserDetailJalaliExtension(DetailExtension):
    """Insert calendar system after date format on user detail."""

    _inherit_detail = "finlo.contrib.core.views.users.UserDetailView"

    fieldsets_insert = [
        ("date_format", "calendar_system"),
    ]
