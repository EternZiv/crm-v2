"""Isolated database-backed acceptance checks for Django authentication."""

import re
from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.contrib.sessions.models import Session
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from finlo.auth.models import User
from finlo.contrib.core.views.forgot_password import default_token_generator


class DjangoAuthenticationAcceptanceTests(TestCase):
    password = "Violet!Ridge-Quartz-73-Cedar"

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="auth-acceptance",
            email="auth-acceptance@example.test",
            password=self.password,
            country="US",
        )

    def test_valid_login_rotates_session_and_invalid_or_inactive_login_is_denied(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get("/login/").status_code, 200)

        before = client.session
        before["prelogin-marker"] = "present"
        before.save()
        old_session_key = before.session_key
        csrf_token = client.cookies[settings.CSRF_COOKIE_NAME].value
        response = client.post(
            "/login/",
            {
                "username": self.user.username,
                "password": self.password,
                "next": "/dashboard/?section=home",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
            HTTP_USER_AGENT="FinloAuthAcceptance/1.0",
            REMOTE_ADDR="192.0.2.31",
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/dashboard/?section=home")
        self.assertEqual(client.session.get("_auth_user_id"), str(self.user.pk))
        self.assertNotEqual(client.session.session_key, old_session_key)

        Session.objects.filter(session_key=client.session.session_key).update(
            expire_date=timezone.now() - timedelta(seconds=1)
        )
        expired_session_response = client.get("/dashboard/?section=home")
        self.assertEqual(expired_session_response.status_code, 302)
        self.assertIn("/login/", expired_session_response["Location"])

        bad_client = Client()
        bad_response = bad_client.post(
            "/login/",
            {"username": self.user.username, "password": "incorrect"},
            REMOTE_ADDR="192.0.2.32",
        )
        self.assertEqual(bad_response.status_code, 302)
        self.assertNotIn("_auth_user_id", bad_client.session)

        inactive = User.objects.create_user(
            username="inactive-acceptance",
            email="inactive@example.test",
            password=self.password,
            country="US",
            is_active=False,
        )
        inactive_response = bad_client.post(
            "/login/",
            {"username": inactive.username, "password": self.password},
            REMOTE_ADDR="192.0.2.33",
        )
        unknown_response = bad_client.post(
            "/login/",
            {"username": "unknown-acceptance", "password": self.password},
            REMOTE_ADDR="192.0.2.34",
        )
        self.assertEqual(inactive_response["Location"], unknown_response["Location"])
        self.assertNotIn("_auth_user_id", bad_client.session)

    def test_logout_requires_csrf_post_and_protected_route_requires_session(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/login/")
        csrf_token = client.cookies[settings.CSRF_COOKIE_NAME].value
        client.post(
            "/login/",
            {"username": self.user.username, "password": self.password},
            HTTP_X_CSRFTOKEN=csrf_token,
            HTTP_USER_AGENT="FinloAuthAcceptance/1.0",
        )
        self.assertEqual(client.session.get("_auth_user_id"), str(self.user.pk))
        # Django rotates the CSRF secret when authentication succeeds.
        csrf_token = client.cookies[settings.CSRF_COOKIE_NAME].value

        get_response = client.get("/logout/")
        self.assertEqual(get_response.status_code, 405)
        self.assertEqual(client.session.get("_auth_user_id"), str(self.user.pk))

        csrf_failure = client.post("/logout/")
        self.assertEqual(csrf_failure.status_code, 403)
        self.assertEqual(client.session.get("_auth_user_id"), str(self.user.pk))

        logout_response = client.post(
            "/logout/",
            HTTP_X_CSRFTOKEN=csrf_token,
            HTTP_USER_AGENT="FinloAuthAcceptance/1.0",
        )
        self.assertEqual(logout_response.status_code, 200)
        self.assertNotIn("_auth_user_id", client.session)
        protected = client.get("/dashboard/?section=home")
        self.assertEqual(protected.status_code, 302)
        self.assertIn("/login/", protected["Location"])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SITE_URL="",
        ALLOWED_HOSTS=["testserver"],
        PASSWORD_RESET_TIMEOUT=86400,
    )
    def test_password_reset_email_token_sets_password_and_is_single_use(self):
        activation_user = User.objects.create(
            username="",
            email="new-owner@example.test",
            contact_number="03001234567",
            country="US",
        )
        self.assertEqual(activation_user.username, activation_user.email)
        self.assertFalse(activation_user.has_usable_password())
        self.assertFalse(activation_user.check_password("03001234567"))

        response = self.client.post(
            "/forgot-password/", {"email": activation_user.email}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        match = re.search(
            r"http://testserver/reset-password/([^/]+)/([^/]+)/",
            mail.outbox[0].body,
        )
        self.assertIsNotNone(match)
        uidb64, token = match.groups()
        reset_url = f"/reset-password/{uidb64}/{token}/"
        self.assertEqual(self.client.get(reset_url).status_code, 200)

        new_password = "Moss!Harbor-Saffron-82-Granite"
        reset_response = self.client.post(
            reset_url,
            {"new_password": new_password, "confirm_password": new_password},
        )
        self.assertEqual(reset_response.status_code, 302)
        activation_user.refresh_from_db()
        self.assertTrue(activation_user.check_password(new_password))
        self.assertFalse(default_token_generator.check_token(activation_user, token))

        reused_response = self.client.post(
            reset_url,
            {"new_password": new_password, "confirm_password": new_password},
        )
        self.assertEqual(reused_response.status_code, 200)
        self.assertFalse(reused_response.context["validlink"])
