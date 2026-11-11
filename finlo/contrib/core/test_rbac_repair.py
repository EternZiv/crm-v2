from types import SimpleNamespace

from django.test import SimpleTestCase

from .sales_authorization import is_super_admin_or_superuser


class SuperAdminIdentityTests(SimpleTestCase):
    def test_active_protected_super_admin_role_is_privileged(self):
        user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_superuser=False,
            role=SimpleNamespace(is_active=True, system_key="SUPER_ADMIN"),
        )

        self.assertTrue(is_super_admin_or_superuser(user))

    def test_inactive_protected_super_admin_role_is_not_privileged(self):
        user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_superuser=False,
            role=SimpleNamespace(is_active=False, system_key="SUPER_ADMIN"),
        )

        self.assertFalse(is_super_admin_or_superuser(user))
