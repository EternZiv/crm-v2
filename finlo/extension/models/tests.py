"""
Tests for the Finlo _inherit_model extension system.
"""

from django.test import SimpleTestCase

from finlo.contrib.core.models import FinloCoreModel
from finlo.db import models
from finlo.extension.models.metaclass import ExtensionModelBase


class ExtensionMetaclassTests(SimpleTestCase):
    """Metaclass and API surface tests (no target-model injection)."""

    def test_invalid_inherit_model_format_raises(self):
        """_inherit_model must use app_label.ModelName syntax."""
        with self.assertRaises(ValueError):
            type(
                "BadExtension",
                (FinloCoreModel,),
                {
                    "_inherit_model": "invalid-no-dot",
                    "marker": models.CharField(max_length=1),
                },
            )

    def test_extension_class_is_placeholder(self):
        """Extension classes with _inherit_model are not registered Django models."""

        class SampleExtension(FinloCoreModel):
            """Placeholder extension; fields inject onto core.Department."""

            _inherit_model = "core.Department"
            marker = models.CharField(max_length=1, null=True)

        self.assertTrue(getattr(SampleExtension, "_is_finlo_extension", False))
        self.assertFalse(hasattr(SampleExtension, "_meta"))

    def test_metaclass_is_on_finlo_core_model(self):
        """FinloCoreModel uses ExtensionModelBase as its metaclass."""
        self.assertIs(FinloCoreModel.__class__, ExtensionModelBase)
