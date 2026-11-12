from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import SimpleTestCase
from .utils import DefaultDashboardGenerator


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
