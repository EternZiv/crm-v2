"""
ASGI config for finlo project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

# import os

# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings')

# application = get_asgi_application()

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finlo.settings")

from django.core.asgi import get_asgi_application

# Initialize models before importing consumer/routing modules.
django_asgi_application = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import calls.routing
import finlo.contrib.notifications.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finlo.settings")

application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                finlo.contrib.notifications.routing.websocket_urlpatterns
                + calls.routing.websocket_urlpatterns
            )
        ),
    }
)
