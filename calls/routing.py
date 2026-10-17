"""WebSocket URL routing for the Finlo Calls Integration app."""

from finlo.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/calls/$", consumers.IncomingCallConsumer.as_asgi()),
]
