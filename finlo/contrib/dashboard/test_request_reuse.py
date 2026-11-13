from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import SimpleTestCase
from .utils import DefaultDashboardGenerator
from .views import dashboard_helper


class DashboardRequestReuseTests(SimpleTestCase):
    def generator(self):
        generator = DefaultDashboardGenerator.__new__(DefaultDashboardGenerator)
        generator._scoped_queryset_cache = {}
        generator._model_permission_cache = {}
        generator.user = Mock()
        return generator

    def test_scoped_query_built_once_and_cloned_for_each_consumer(self):
        generator = self.generator()
        model = object()
        scoped = Mock()
        generator.apply_date_range_filter = Mock(return_value=scoped)
        with patch('finlo.contrib.generics.views.helpers.queryset_utils.get_queryset_for_module') as scope:
            generator.get_queryset(model)
            generator.get_queryset(model)
        scope.assert_called_once_with(generator.user, model)
        self.assertEqual(scoped.all.call_count, 2)

    def test_permission_result_never_shared_between_generators(self):
        model = Mock(_meta=SimpleNamespace(app_label='leads', model_name='lead'))
        first = self.generator()
        first.user.has_perm.return_value = False
        self.assertFalse(first.has_model_permission(model))
        self.assertFalse(first.has_model_permission(model))
        self.assertEqual(first.user.has_perm.call_count, 2)
        second = self.generator()
        second.user.has_perm.return_value = True
        self.assertTrue(second.has_model_permission(model))


class DashboardAggregateQueryTests(SimpleTestCase):
    def test_numeric_kpi_uses_aggregate_without_preceding_count(self):
        model = Mock()
        model._meta.get_field.return_value.verbose_name = "Amount"
        queryset = Mock()
        queryset.aggregate.return_value = {"result": 125}
        queryset.count.side_effect = AssertionError("unexpected count query")
        component = SimpleNamespace(
            module=SimpleNamespace(model="Lead"),
            conditions=Mock(),
            metric_type="sum__amount",
        )
        request = SimpleNamespace(user=Mock())

        with (
            patch.object(
                dashboard_helper.apps,
                "get_app_configs",
                return_value=[SimpleNamespace(label="leads")],
            ),
            patch.object(dashboard_helper.apps, "get_model", return_value=model),
            patch.object(
                dashboard_helper,
                "get_queryset_for_module",
                return_value=queryset,
            ) as scoped,
            patch.object(dashboard_helper, "apply_conditions", return_value=queryset),
            patch.object(
                dashboard_helper,
                "get_section_info_for_model",
                return_value={"url": "/leads/", "section": "sales"},
            ),
        ):
            result = dashboard_helper.get_kpi_data(component, request)

        self.assertEqual(result["value"], 125.0)
        queryset.aggregate.assert_called_once()
        queryset.count.assert_not_called()
        scoped.assert_called_once_with(request.user, model)

    def test_report_chart_evaluates_grouped_query_once_without_count_or_exists(self):
        class GroupedQuery:
            def __init__(self):
                self.iterations = 0

            def values(self, *fields):
                self.value_fields = fields
                return self

            def annotate(self, **kwargs):
                return self

            def order_by(self, *fields):
                return self

            def __iter__(self):
                self.iterations += 1
                return iter([{"status": "qualified", "value": 3}])

            def count(self):
                raise AssertionError("unexpected count query")

            def exists(self):
                raise AssertionError("unexpected exists query")

        model = Mock()
        model._meta.get_field.return_value = SimpleNamespace(is_relation=False, choices=[])
        queryset = GroupedQuery()
        component = SimpleNamespace(
            id=42,
            module=SimpleNamespace(model="Lead"),
            reports=SimpleNamespace(name="Lead summary"),
            grouping_field="status",
            chart_type="column",
            name="Leads by status",
        )
        request = SimpleNamespace(user=Mock())

        with (
            patch.object(
                dashboard_helper.apps,
                "get_app_configs",
                return_value=[SimpleNamespace(label="leads")],
            ),
            patch.object(dashboard_helper.apps, "get_model", return_value=model),
            patch.object(
                dashboard_helper,
                "get_queryset_for_module",
                return_value=queryset,
            ),
            patch.object(
                dashboard_helper,
                "get_section_info_for_model",
                return_value={"url": "/leads/", "section": "sales"},
            ),
        ):
            result = dashboard_helper.get_report_chart_data(component, request)

        self.assertEqual(result["data"]["labels"], ["qualified"])
        self.assertEqual(result["data"]["data"], [3.0])
        self.assertEqual(queryset.iterations, 1)
