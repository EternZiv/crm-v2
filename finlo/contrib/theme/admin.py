"""
Admin registration for the theme app
"""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import CompanyTheme, FinloColorTheme

# Register your theme models here.
admin.site.register(FinloColorTheme)
admin.site.register(CompanyTheme)
