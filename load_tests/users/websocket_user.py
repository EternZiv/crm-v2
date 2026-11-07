"""
Dedicated WebSocket Virtual User Persona for Django Channels Notifications.
Simulates persistent real-time connections to 'ws/notifications/'.
Measures connection handshake latency, message throughput, and connection dropouts.
"""

import time
import websocket
from locust import User, between, events, task

from load_tests.common.auth import CREDENTIAL_POOL, FinloAuthenticator
from load_tests.common.client import FinloClientMixin


class NotificationWebSocketUser(User, FinloClientMixin):
    """
    Maintains a persistent WebSocket connection to Finlo's notification channel.
    Tests Daphne ASGI worker and Channels layer capacity under concurrent real-time connections.
    """

    weight = 5
    wait_time = between(5.0, 15.0)

    def on_start(self):
        """Authenticates HTTP session first, then establishes WebSocket connection."""
        from locust.clients import HttpSession
        self.client = HttpSession(base_url=self.host)

        user_idx = getattr(self, "_locust_user_id", id(self) % 500)
        self.credential = CREDENTIAL_POOL.lease_credential(user_idx)
        FinloAuthenticator.authenticate_session(self, self.credential)

        # Build WS URL from base host
        base_ws_url = self.host.replace("https://", "wss://").replace("http://", "ws://")
        self.ws_url = f"{base_ws_url}/ws/notifications/"

        # Extract session cookie to authenticate the WebSocket handshake
        cookies = self.client.cookies.get_dict()
        cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        self.headers = {"Cookie": cookie_header}

        self.ws = None
        self._connect_websocket()

    def _connect_websocket(self):
        """Establishes WebSocket connection and records handshake timing."""
        start_time = time.perf_counter()
        try:
            self.ws = websocket.create_connection(
                self.ws_url,
                header=self.headers,
                timeout=10,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            events.request.fire(
                request_type="[WS] CONNECT",
                name="[WS] /ws/notifications/ Handshake",
                response_time=elapsed_ms,
                response_length=0,
                exception=None,
                context={},
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            events.request.fire(
                request_type="[WS] CONNECT",
                name="[WS] /ws/notifications/ Handshake",
                response_time=elapsed_ms,
                response_length=0,
                exception=exc,
                context={},
            )
            self.ws = None

    @task
    def keep_alive_ping(self):
        """Maintains persistent connection and checks for incoming notification frames."""
        if not self.ws:
            self._connect_websocket()
            return

        start_time = time.perf_counter()
        try:
            # Set non-blocking socket timeout to poll for incoming messages
            self.ws.settimeout(0.5)
            try:
                msg = self.ws.recv()
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                events.request.fire(
                    request_type="[WS] RECV",
                    name="[WS] /ws/notifications/ Message",
                    response_time=elapsed_ms,
                    response_length=len(msg) if msg else 0,
                    exception=None,
                    context={},
                )
            except websocket.WebSocketTimeoutException:
                # Normal when no notifications pending
                pass
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            events.request.fire(
                request_type="[WS] ERROR",
                name="[WS] /ws/notifications/ Disconnect",
                response_time=elapsed_ms,
                response_length=0,
                exception=exc,
                context={},
            )
            self.ws = None

    def on_stop(self):
        """Cleanly closes WebSocket connection upon test completion."""
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

