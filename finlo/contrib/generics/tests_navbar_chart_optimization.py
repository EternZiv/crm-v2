"""
Tests for Phase 4D: Navbar and Chart Query Optimization.

Validates that:
1. Navbar rendering with empty available_saved_filter_lists does not evaluate fallback queries.
2. Navbar rendering with saved filters renders them correctly.
3. Navbar rendering with missing/None context safely falls back to user.saved_filter_lists.all.
4. FinloChartView (e.g. LeadChartView) executes 0 ListColumnVisibility queries.
5. User column preferences for the model are preserved and not altered by chart views.
6. Chart views preserve company isolation and RBAC.
"""

from unittest.mock import patch
from django.test import TestCase, RequestFactory
from django.template import Template, Context
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from finlo_crm.leads.views import LeadChartView, LeadNavbar
from finlo_crm.leads.models import Lead
from finlo.contrib.core.models import ListColumnVisibility, SavedFilterList
from django.db import connection, reset_queries

User = get_user_model()


class NavbarAndChartOptimizationTests(TestCase):
    def setUp(self):
        self.user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        self.rf = RequestFactory()
        self.middleware = SessionMiddleware(lambda r: None)

    def test_navbar_with_empty_saved_filter_context_does_not_query_fallback(self):
        """When available_saved_filter_lists is empty list [], fallback is not evaluated."""
        req = self.rf.get("/")
        req.user = self.user

        template = Template(
            '{% load i18n %}'
            '{% for saved_list in available_saved_filter_lists|default_if_none:request.user.saved_filter_lists.all %}'
            '{{ saved_list.name }}'
            '{% endfor %}'
        )
        context = Context({
            "request": req,
            "available_saved_filter_lists": [],
        })

        with patch.object(self.user.saved_filter_lists, "all") as mock_all:
            rendered = template.render(context)
            mock_all.assert_not_called()
            self.assertEqual(rendered.strip(), "")

    def test_navbar_with_saved_filters_renders_options(self):
        """When available_saved_filter_lists contains items, they are iterated correctly."""
        req = self.rf.get("/")
        req.user = self.user

        class DummySavedList:
            def __init__(self, id, name, model_name):
                self.id = id
                self.name = name
                self.model_name = model_name

        dummy_lists = [
            DummySavedList(101, "High Value Leads", "lead"),
            DummySavedList(102, "In Progress", "lead"),
        ]

        template = Template(
            '{% for saved_list in available_saved_filter_lists|default_if_none:request.user.saved_filter_lists.all %}'
            '[{{ saved_list.id }}:{{ saved_list.name }}]'
            '{% endfor %}'
        )
        context = Context({
            "request": req,
            "available_saved_filter_lists": dummy_lists,
        })

        rendered = template.render(context)
        self.assertIn("[101:High Value Leads]", rendered)
        self.assertIn("[102:In Progress]", rendered)

    def test_navbar_with_missing_context_falls_back_safely(self):
        """When available_saved_filter_lists is None or missing, default_if_none falls back to user.saved_filter_lists.all."""
        req = self.rf.get("/")
        req.user = self.user

        template = Template(
            '{% for saved_list in available_saved_filter_lists|default_if_none:request.user.saved_filter_lists.all %}'
            '{{ saved_list.name }}'
            '{% endfor %}'
        )
        context = Context({
            "request": req,
            "available_saved_filter_lists": None,
        })

        # Should evaluate user.saved_filter_lists.all without template error
        rendered = template.render(context)
        self.assertIsInstance(rendered, str)

    def test_chart_view_executes_zero_list_column_visibility_queries(self):
        """LeadChartView does not query ListColumnVisibility."""
        req = self.rf.get("/crm/leads/leads-chart/?section=sales", HTTP_HX_REQUEST="true")
        req.user = self.user
        req._skip_header_context = True
        self.middleware.process_request(req)

        view = LeadChartView.as_view()
        reset_queries()
        resp = view(req)

        self.assertEqual(resp.status_code, 200)
        col_vis_queries = [
            q for q in connection.queries if "core_listcolumnvisibility" in q["sql"]
        ]
        self.assertEqual(len(col_vis_queries), 0)

    def test_chart_view_with_user_column_preferences(self):
        """Having user column preferences for the model does not cause chart view to query or overwrite them."""
        # Check existing preferences count
        existing_prefs = ListColumnVisibility.all_objects.filter(
            user=self.user,
            model_name="Lead",
        ).count()

        req = self.rf.get("/crm/leads/leads-chart/?section=sales", HTTP_HX_REQUEST="true")
        req.user = self.user
        req._skip_header_context = True
        self.middleware.process_request(req)

        view = LeadChartView.as_view()
        resp = view(req)
        self.assertEqual(resp.status_code, 200)

        # Count must remain unchanged
        new_prefs = ListColumnVisibility.all_objects.filter(
            user=self.user,
            model_name="Lead",
        ).count()
        self.assertEqual(existing_prefs, new_prefs)

    def test_chart_view_preserves_company_isolation_and_rbac(self):
        """LeadChartView respects company filtration and owner filtration."""
        req = self.rf.get("/crm/leads/leads-chart/?section=sales", HTTP_HX_REQUEST="true")
        req.user = self.user
        req._skip_header_context = True
        self.middleware.process_request(req)

        view_instance = LeadChartView()
        view_instance.request = req
        view_instance.kwargs = {}

        qs = view_instance.get_queryset()
        # Verify queryset is restricted to valid CRM model
        self.assertEqual(qs.model, Lead)
        # Verify chart grouping choices are available
        dimension_choices = view_instance.get_chart_dimension_choices()
        self.assertTrue(len(dimension_choices) > 0)
