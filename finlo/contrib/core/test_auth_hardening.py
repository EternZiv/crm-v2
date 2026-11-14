"""Focused, database-free regression checks for authentication hardening."""

from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.test import RequestFactory, SimpleTestCase, override_settings

from finlo.contrib.core.auth_rate_limit import cache_key, count, increment
from finlo.contrib.core.models.user import FinloUser
from finlo.contrib.core.views.core import LoginUserView, LogoutView
from finlo.contrib.core.views.forgot_password import _password_reset_link
from finlo.contrib.core.management.commands.create_finlo_user import Command as CreateFinloUserCommand
from django.core.management.base import CommandError


class PasswordlessUserTests(SimpleTestCase):
    def test_new_user_without_password_gets_unusable_password(self):
        user = FinloUser(email="person@example.test", contact_number="03001234567")

        with patch.object(models.Model, "save"):
            user.save()

        self.assertEqual(user.username, "person@example.test")
        self.assertFalse(user.has_usable_password())

    def test_explicit_hashed_password_is_preserved(self):
        user = FinloUser(username="person")
        user.set_password("AValid-Test-Password-49!")
        encoded_password = user.password

        with patch.object(models.Model, "save"):
            user.save()

        self.assertEqual(user.password, encoded_password)
        self.assertTrue(user.check_password("AValid-Test-Password-49!"))

    def test_existing_password_is_not_changed_by_save(self):
        user = FinloUser(username="legacy")
        user._state.adding = False
        user.password = "existing-encoded-hash"

        with patch.object(models.Model, "save"):
            user.save()

        self.assertEqual(user.password, "existing-encoded-hash")

    def test_user_creation_command_requires_policy_valid_password(self):
        command = CreateFinloUserCommand()
        base_options = {
            "first_name": "Example",
            "last_name": "User",
            "username": "example",
            "email": "example@example.test",
            "phone": "03001234567",
        }
        with patch("finlo.contrib.core.management.commands.create_finlo_user.User.objects.filter") as query:
            with self.assertRaises(CommandError):
                command.handle(**base_options, password=None)
            with self.assertRaises(CommandError):
                command.handle(**base_options, password="12345678")
        query.assert_not_called()


class AuthenticationRateLimitTests(SimpleTestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def test_rate_limit_keys_do_not_contain_identifiers_and_increment(self):
        key = cache_key("login-user", "employee@example.test")
        self.assertNotIn("employee@example.test", key)
        self.assertEqual(increment(key, 60), 1)
        self.assertEqual(increment(key, 60), 2)
        self.assertEqual(count(key), 2)

    def test_user_throttle_scope_is_separated_by_client_address(self):
        first = cache_key(
            "login-user-ip", "employee@example.test" + "\0" + "192.0.2.1"
        )
        second = cache_key(
            "login-user-ip", "employee@example.test" + "\0" + "192.0.2.2"
        )
        self.assertNotEqual(first, second)

    def test_login_fails_closed_when_throttle_cache_is_unavailable(self):
        request = RequestFactory().post(
            "/login/", {"username": "employee", "password": "not-logged"}
        )
        request.user = AnonymousUser()
        with patch(
            "finlo.contrib.core.views.core.auth_rate_count",
            side_effect=RuntimeError("cache outage"),
        ), patch("finlo.contrib.core.views.core.authenticate") as authenticate:
            response = LoginUserView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Cache-Control"], "no-store")
        authenticate.assert_not_called()

    def test_throttled_login_is_rejected_before_password_authentication(self):
        request = RequestFactory().post(
            "/login/",
            {"username": "employee", "password": "never-logged"},
            REMOTE_ADDR="192.0.2.10",
            HTTP_X_FORWARDED_FOR="198.51.100.77",
        )
        request.user = AnonymousUser()
        with patch(
            "finlo.contrib.core.views.core.auth_rate_count", side_effect=[20]
        ), patch(
            "finlo.contrib.core.views.core.auth_rate_key", wraps=cache_key
        ) as rate_key_builder, patch(
            "finlo.contrib.core.views.core.messages.error"
        ), patch(
            "finlo.contrib.core.views.core.authenticate"
        ) as authenticate:
            response = LoginUserView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        authenticate.assert_not_called()
        self.assertEqual(
            rate_key_builder.call_args_list[0].args,
            ("login-user-ip", "employee\0" + "192.0.2.10"),
        )
        self.assertEqual(
            rate_key_builder.call_args_list[1].args,
            ("login-ip", "192.0.2.10"),
        )

    def test_inactive_and_unknown_user_get_the_same_login_response(self):
        responses = []
        inactive_user = type("User", (), {"is_active": False})()
        for result in (None, inactive_user):
            request = RequestFactory().post(
                "/login/",
                {"username": "employee", "password": "not-logged"},
                REMOTE_ADDR="192.0.2.11",
                HTTP_X_FORWARDED_FOR="198.51.100.77",
            )
            request.user = AnonymousUser()
            with patch(
                "finlo.contrib.core.views.core.auth_rate_count", return_value=0
            ), patch(
                "finlo.contrib.core.views.core.increment_auth_rate", return_value=1
            ), patch("finlo.contrib.core.views.core.messages.error"), patch(
                "finlo.contrib.core.views.core.authenticate", return_value=result
            ):
                response = LoginUserView.as_view()(request)
            responses.append((response.status_code, response["Location"]))

        self.assertEqual(responses[0], responses[1])


class LogoutMethodTests(SimpleTestCase):
    def test_get_does_not_log_out(self):
        request = RequestFactory().get("/logout/")
        request.user = AnonymousUser()

        with patch("finlo.contrib.core.views.core.logout") as logout:
            response = LogoutView.as_view()(request)

        self.assertEqual(response.status_code, 405)
        logout.assert_not_called()

    def test_post_logs_out_and_csrf_middleware_rejects_missing_token(self):
        view = LogoutView.as_view()
        middleware = CsrfViewMiddleware(lambda request: None)
        request = RequestFactory().post("/logout/")
        request.user = AnonymousUser()
        rejected = middleware.process_view(request, view, (), {})
        self.assertEqual(rejected.status_code, 403)

        request = RequestFactory().post("/logout/")
        request.user = AnonymousUser()
        masked_token = get_token(request)
        request.COOKIES["csrftoken"] = request.META["CSRF_COOKIE"]
        request.META["HTTP_X_CSRFTOKEN"] = masked_token
        self.assertIsNone(middleware.process_view(request, view, (), {}))

        from types import SimpleNamespace

        request.user = SimpleNamespace(is_authenticated=True)
        with patch("finlo.contrib.core.views.core.logout") as logout:
            response = view(request)
        self.assertEqual(response.status_code, 200)
        logout.assert_called_once_with(request)


class PasswordResetOriginTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/forgot-password/", HTTP_HOST="crm.example.test")

    @override_settings(
        IS_PRODUCTION=True,
        SITE_URL="https://crm.example.test",
        ALLOWED_HOSTS=["crm.example.test"],
    )
    def test_uses_allowlisted_configured_https_origin(self):
        url = _password_reset_link("uid", "token", self.request)
        self.assertEqual(
            url,
            "https://crm.example.test/reset-password/uid/token/",
        )

    @override_settings(
        IS_PRODUCTION=True,
        SITE_URL="https://attacker.example",
        ALLOWED_HOSTS=["crm.example.test"],
    )
    def test_rejects_unallowlisted_reset_origin(self):
        with self.assertRaises(ImproperlyConfigured):
            _password_reset_link("uid", "token", self.request)


class PasswordResetTemplateTests(SimpleTestCase):
    def test_passwords_are_not_reflected_back_into_reset_markup(self):
        from pathlib import Path

        template = Path(
            "finlo/contrib/core/templates/forgot_password/password_reset_confirm.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn('value="{{ new_password', template)
        self.assertNotIn('value="{{ confirm_password', template)
        self.assertEqual(template.count('autocomplete="new-password"'), 2)
