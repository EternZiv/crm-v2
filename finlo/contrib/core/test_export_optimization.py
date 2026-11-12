import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from finlo.contrib.core.views.export_data import ExportView


class ExportMetadataDeferralTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(is_authenticated=True, is_superuser=False, pk=1)

    def test_available_models_does_not_build_fields(self):
        model = SimpleNamespace(
            __name__="Lead",
            __module__="finlo_crm.leads.models",
            _meta=SimpleNamespace(verbose_name="lead", app_label="leads"),
        )
        view = ExportView()
        view.request = self.factory.get("/export-view/")
        view.request.user = self.user
        with patch("finlo.contrib.core.views.export_data.FEATURE_REGISTRY", {"export_models": [model]}), \
             patch("finlo.contrib.core.views.export_data.get_export_queryset", return_value=object()):
            result = view.get_available_models()
        self.assertEqual(result[0]["fields"], [])

    def test_field_endpoint_filters_unauthorized_modules(self):
        request = self.factory.get("/export-view/?fields=1&module=Lead&module=Secret")
        request.user = self.user
        view = ExportView.as_view()
        with patch.object(ExportView, "get_model_by_name", side_effect=lambda name: SimpleNamespace(
                _meta=SimpleNamespace(fields=[])
            ) if name == "Lead" else None), \
             patch("finlo.contrib.core.views.export_data.get_export_queryset", side_effect=lambda user, model, request=None: object() if model else None):
            response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["modules"]["Secret"], [])

    def test_field_endpoint_returns_authorized_exportable_metadata(self):
        class Field:
            name = "email"
            verbose_name = "Email"
            editable = True
            auto_now = False
            auto_now_add = False

        model = SimpleNamespace(
            _meta=SimpleNamespace(fields=[Field()]),
        )
        request = self.factory.get("/export-view/?fields=1&module=Lead")
        request.user = self.user
        view = ExportView.as_view()
        with patch.object(ExportView, "get_model_by_name", return_value=model), \
             patch("finlo.contrib.core.views.export_data.get_export_queryset", return_value=object()):
            response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["modules"]["Lead"], [{"name": "email", "label": "Email"}])

    def test_post_still_rejects_missing_module_or_format(self):
        request = self.factory.post(
            "/export-view/", {}
        )
        request.user = self.user
        view = ExportView()
        view.request = request
        with patch.object(view, "render_to_response", return_value="validation-response"), \
             patch("finlo.contrib.core.views.export_data.messages.error"), \
             patch("finlo.contrib.core.views.export_data.ExportSchedule.objects.filter", return_value=MagicMock(order_by=lambda *_: [])):
            self.assertEqual(view.post(request), "validation-response")
