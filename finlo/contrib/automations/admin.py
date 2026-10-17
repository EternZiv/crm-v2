"""
Admin registration for the automations app
"""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import AutomationCondition, AutomationRunLog, FinloAutomation

# Register your automations models here.


@admin.register(FinloAutomation)
class FinloAutomationAdmin(admin.ModelAdmin):
    """Admin configuration for FinloAutomation."""

    filter_horizontal = ("also_sent_to",)


admin.site.register(AutomationCondition)
admin.site.register(AutomationRunLog)
