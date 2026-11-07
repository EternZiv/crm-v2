"""Django admin configuration for mail models."""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import (
    FinloMail,
    FinloMailAttachment,
    FinloMailConfiguration,
    FinloMailTemplate,
    IncomingMail,
)

# Register your mail models here.

admin.site.register(FinloMailConfiguration)
admin.site.register(FinloMail)
admin.site.register(FinloMailAttachment)
admin.site.register(FinloMailTemplate)
admin.site.register(IncomingMail)
