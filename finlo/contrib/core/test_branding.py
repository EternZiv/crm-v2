"""Tests for Finlo CRM product branding."""

from django.test import SimpleTestCase, override_settings

from finlo.utils.branding import load_branding


class FinloBrandingTests(SimpleTestCase):
    @override_settings(BRANDING_MODULE="finlo_crm.__branding__")
    def test_product_branding_uses_finlo_crm_name(self):
        branding = load_branding()

        self.assertEqual(branding["TITLE"], "Finlo CRM")
        self.assertEqual(branding["LOGIN_WELCOME_LINE"], "Welcome to Finlo CRM")
        self.assertEqual(
            branding["SIGNUP_TAG_LINE"], "Please sign up to access Finlo CRM"
        )
        self.assertEqual(branding["PAGE_HEADER"], "Finlo CRM")
