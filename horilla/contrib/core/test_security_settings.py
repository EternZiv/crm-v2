"""Ensure the dedicated security test settings never target configured databases."""

from django.conf import settings
from django.test import SimpleTestCase


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
