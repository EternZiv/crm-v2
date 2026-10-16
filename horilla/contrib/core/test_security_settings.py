"""Ensure the dedicated security test settings never target configured databases."""

import os
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import Client, SimpleTestCase, override_settings
from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie

from horilla.settings.base import _get_vercel_deployment_hostnames


@ensure_csrf_cookie
def csrf_probe(_request):
    return HttpResponse(_request.method)


def csrf_probe_failure(_request, reason=""):
    return HttpResponse(_request.method, status=403 if reason else 400)


urlpatterns = [path("csrf-probe/", csrf_probe)]


class SecurityTestDatabaseSettingsTests(SimpleTestCase):
    def test_database_is_ephemeral_sqlite(self):
        self.assertTrue(settings.DATABASES)
        for alias, database in settings.DATABASES.items():
            with self.subTest(alias=alias):
                self.assertEqual(
                    database["ENGINE"], "django.db.backends.sqlite3"
                )
                self.assertIn(
                    database["NAME"],
                    {
                        ":memory:",
                        f"file:memorydb_{alias}?mode=memory&cache=shared",
                    },
                )
                self.assertEqual(database["TEST"]["NAME"], ":memory:")


class VercelHostnameSettingsTests(SimpleTestCase):
    def test_project_production_domain_is_added_to_django_settings(self):
        if not settings.IS_VERCEL:
            self.skipTest("Requires a Vercel settings import.")

        production_hostname = os.environ["VERCEL_PROJECT_PRODUCTION_URL"]
        self.assertIn(production_hostname, settings.ALLOWED_HOSTS)
        self.assertIn(
            f"https://{production_hostname}", settings.CSRF_TRUSTED_ORIGINS
        )

    def test_vercel_hostnames_are_limited_to_supplied_project_aliases(self):
        with mock.patch.dict(
            os.environ,
            {
                "VERCEL_URL": "deployment-abc.vercel.app",
                "VERCEL_BRANCH_URL": "crm-v2-git-main.vercel.app",
                "VERCEL_PROJECT_PRODUCTION_URL": "crm-v2-ochre.vercel.app",
            },
            clear=False,
        ):
            self.assertEqual(
                _get_vercel_deployment_hostnames(),
                [
                    "deployment-abc.vercel.app",
                    "crm-v2-git-main.vercel.app",
                    "crm-v2-ochre.vercel.app",
                ],
            )

    def test_invalid_vercel_hostname_is_rejected(self):
        with mock.patch.dict(
            os.environ,
            {"VERCEL_PROJECT_PRODUCTION_URL": "https://untrusted.example/path"},
            clear=False,
        ):
            with self.assertRaises(ImproperlyConfigured):
                _get_vercel_deployment_hostnames()

    def test_deployment_alias_must_use_vercel_app_domain(self):
        with mock.patch.dict(
            os.environ,
            {"VERCEL_URL": "untrusted.example"},
            clear=False,
        ):
            with self.assertRaises(ImproperlyConfigured):
                _get_vercel_deployment_hostnames()

    def test_only_configured_vercel_hostname_and_origin_are_accepted(self):
        hostname = "crm-v2-ochre.vercel.app"
        with override_settings(
            ROOT_URLCONF=__name__,
            ALLOWED_HOSTS=[hostname],
            CSRF_TRUSTED_ORIGINS=[f"https://{hostname}"],
            CSRF_FAILURE_VIEW="horilla.contrib.core.test_security_settings.csrf_probe_failure",
        ):
            client = Client(enforce_csrf_checks=True)
            response = client.get(
                "/csrf-probe/", HTTP_HOST=hostname, secure=True
            )
            self.assertEqual(response.status_code, 200)

            token = client.cookies["csrftoken"].value
            response = client.post(
                "/csrf-probe/",
                data={},
                HTTP_HOST=hostname,
                HTTP_ORIGIN=f"https://{hostname}",
                HTTP_X_CSRFTOKEN=token,
                secure=True,
            )
            self.assertEqual(response.status_code, 200)

            response = client.post(
                "/csrf-probe/",
                data={},
                HTTP_HOST=hostname,
                HTTP_ORIGIN="https://untrusted.example",
                HTTP_X_CSRFTOKEN=token,
                secure=True,
            )
            self.assertEqual(response.status_code, 403)

            response = client.get(
                "/csrf-probe/", HTTP_HOST="untrusted.example", secure=True
            )
            self.assertEqual(response.status_code, 400)
