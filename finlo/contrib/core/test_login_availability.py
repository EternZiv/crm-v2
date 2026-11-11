"""Login outage handling without connecting to the CRM database."""

from unittest.mock import patch

from django.db import OperationalError
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from finlo.contrib.core.views.core import LoginUserView


class LoginAvailabilityTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_database_outage_returns_retryable_response_for_get_and_post(self):
        for method in ("get", "post"):
            with self.subTest(method=method):
                request = getattr(self.factory, method)("/login/")
                with patch.object(
                    LoginUserView, method,
                    side_effect=OperationalError("private connection details"),
                ):
                    response = LoginUserView.as_view()(request)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response["Retry-After"], "30")
                self.assertEqual(response["Cache-Control"], "no-store")
                self.assertNotIn(b"private connection details", response.content)

    def test_authentication_outage_does_not_count_as_failed_credentials(self):
        request = self.factory.post(
            "/login/", {"username": "example", "password": "secret"},
            REMOTE_ADDR="192.0.2.123",
        )
        with patch("finlo.contrib.core.views.core.cache") as login_cache:
            login_cache.get.return_value = None
            with patch(
                "finlo.contrib.core.views.core.authenticate",
                side_effect=OperationalError("DNS lookup failed"),
            ):
                response = LoginUserView.as_view()(request)
            self.assertEqual(response.status_code, 503)
            login_cache.set.assert_not_called()

    def test_normal_response_is_preserved(self):
        expected = HttpResponse(status=302)
        expected["Location"] = "/dashboard/"
        with patch.object(LoginUserView, "post", return_value=expected):
            response = LoginUserView.as_view()(self.factory.post("/login/"))
        self.assertIs(response, expected)

    def test_unrelated_errors_are_not_hidden(self):
        with patch.object(LoginUserView, "get", side_effect=ValueError("bug")):
            with self.assertRaises(ValueError):
                LoginUserView.as_view()(self.factory.get("/login/"))
