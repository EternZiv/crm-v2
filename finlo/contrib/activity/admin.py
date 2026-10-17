"""
Admin configuration for Activity models in Finlo.
"""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import Activity

# Register your activity models here.


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    """Admin configuration for Activity."""

    filter_horizontal = ("assigned_to", "participants")
