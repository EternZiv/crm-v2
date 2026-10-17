"""Admin registrations for the `finlo.contrib.reports.urls` app."""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from . import models

# Register your reports models here.

admin.site.register(models.ReportFolder)


@admin.register(models.Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin configuration for Report."""

    filter_horizontal = ("shared_with",)
