import os
import sys
import unittest

os.environ["DJANGO_SETTINGS_MODULE"] = "finlo.settings.security_test"
import django

django.setup()
suite = unittest.defaultTestLoader.loadTestsFromName(
    "finlo.contrib.core.test_export_optimization"
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
