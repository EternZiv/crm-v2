"""
Unit and integration tests for LeadDataService, aggregate charts, and skeleton templates.
"""

from unittest.mock import MagicMock, call, patch
from django.test import SimpleTestCase, TestCase, RequestFactory
from django.core.cache import cache
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from finlo_crm.leads.services import (
    LeadDataService,
    get_lead_cache_version,
    bump_lead_user_cache_version,
    bump_lead_cache_version,
)
from finlo_crm.leads.models import Lead, LeadStatus
from finlo.contrib.generics.views.chart import FinloChartView
from finlo.db.models.signals import post_delete, post_save

User = get_user_model()


class LeadDataServiceUnitTests(SimpleTestCase):
    """Isolated unit tests for LeadDataService logic, versioning, and cache mechanics."""

    def setUp(self):
        cache.clear()

    def test_version_initialization_and_bump(self):
        """Cache revision initializes and changes when invalidated."""
        v1 = get_lead_cache_version("compA", 10)
        self.assertEqual(v1, 1)

        bump_lead_cache_version("compA", 10)
        v2 = get_lead_cache_version("compA", 10)
        self.assertNotEqual(v2, v1)

    def test_company_mutation_invalidates_each_user_scoped_key(self):
        user_a = MagicMock(pk=101, company=MagicMock(pk=5))
        user_b = MagicMock(pk=102, company=MagicMock(pk=5))

        key_a_before = LeadDataService._build_cache_key(user_a, "stage_counts")
        key_b_before = LeadDataService._build_cache_key(user_b, "stage_counts")
        self.assertNotEqual(key_a_before, key_b_before)

        bump_lead_cache_version(company_id=5, user_id=101)

        self.assertNotEqual(
            key_a_before, LeadDataService._build_cache_key(user_a, "stage_counts")
        )
        self.assertNotEqual(
            key_b_before, LeadDataService._build_cache_key(user_b, "stage_counts")
        )

    @patch("finlo_crm.leads.signals.transaction.on_commit")
    @patch("finlo_crm.leads.signals.bump_lead_cache_version")
    def test_company_transfer_invalidates_both_tenant_revisions(self, bump, on_commit):
        from finlo_crm.leads.signals import invalidate_lead_data_caches_on_mutation

        lead = MagicMock(pk=77, company_id=20)
        lead._lead_cache_company_id = 10
        on_commit.side_effect = lambda callback: callback()

        invalidate_lead_data_caches_on_mutation(
            sender=Lead, instance=lead, signal=post_save, created=False
        )

        self.assertCountEqual([call.args[0] for call in bump.call_args_list], [10, 20])

    @patch("finlo_crm.leads.signals.transaction.on_commit")
    @patch("finlo_crm.leads.signals.bump_lead_cache_version")
    def test_lead_deletion_invalidates_company_after_commit(self, bump, on_commit):
        from finlo_crm.leads.signals import invalidate_lead_data_caches_on_mutation

        lead = MagicMock(pk=88, company_id=20)
        lead._lead_cache_company_id = 20
        on_commit.side_effect = lambda callback: callback()

        invalidate_lead_data_caches_on_mutation(
            sender=Lead, instance=lead, signal=post_delete
        )

        bump.assert_called_once_with(20)

    @patch("finlo.contrib.core.signals.transaction.on_commit")
    @patch("finlo_crm.leads.services.bump_lead_cache_version")
    def test_role_data_scope_change_invalidates_company_after_commit(self, bump, on_commit):
        from finlo.contrib.core.signals import invalidate_lead_caches_for_role_scope
        from finlo.contrib.core.models import RoleDataScope

        scope = MagicMock(company_id=5, role_id=4)
        on_commit.side_effect = lambda callback: callback()
        invalidate_lead_caches_for_role_scope(
            sender=RoleDataScope, instance=scope
        )
        bump.assert_called_once_with(5)

    def test_user_scope_revision_does_not_change_other_users_key(self):
        user_a = MagicMock(pk=101, company=MagicMock(pk=5))
        user_b = MagicMock(pk=102, company=MagicMock(pk=5))
        key_a_before = LeadDataService._build_cache_key(user_a, "summary")
        key_b_before = LeadDataService._build_cache_key(user_b, "summary")

        bump_lead_user_cache_version(101)

        self.assertNotEqual(
            key_a_before, LeadDataService._build_cache_key(user_a, "summary")
        )
        self.assertEqual(key_b_before, LeadDataService._build_cache_key(user_b, "summary"))

    @patch("finlo.contrib.core.signals.transaction.on_commit")
    @patch("finlo.contrib.core.sales_authorization.invalidate_role_permission_cache")
    @patch("finlo_crm.leads.services.bump_lead_cache_version")
    def test_role_permission_change_invalidates_tenant_after_commit(
        self, bump, _invalidate_permission_cache, on_commit
    ):
        from finlo.contrib.core.signals import invalidate_role_permission_snapshots

        role = MagicMock(company_id=5)
        invalidate_role_permission_snapshots(
            action="post_add", instance=role, pk_set={8}
        )
        bump.assert_not_called()
        on_commit.call_args.args[0]()
        bump.assert_called_once_with(5)

    @patch("finlo.contrib.core.signals.transaction.on_commit")
    @patch("finlo_crm.leads.services.bump_lead_user_cache_version")
    def test_direct_user_permission_change_invalidates_only_that_user(
        self, bump_user, on_commit
    ):
        from finlo.contrib.core.signals import invalidate_lead_caches_for_user_scope

        user = User(pk=101)
        on_commit.side_effect = lambda callback: callback()
        invalidate_lead_caches_for_user_scope(
            sender=User.user_permissions.through,
            instance=user,
            action="post_add",
            reverse=False,
            pk_set={4},
        )
        bump_user.assert_called_once_with(101)

    @patch("finlo_crm.leads.services.get_queryset_for_module")
    def test_get_lead_kpi_summary_single_aggregation(self, mock_get_qs):
        """Ensure get_lead_kpi_summary executes a single aggregate query and caches result."""
        mock_qs = MagicMock()
        mock_qs.aggregate.return_value = {
            "total": 50,
            "open": 35,
            "converted": 15,
        }
        mock_get_qs.return_value = mock_qs

        user = MagicMock(pk=101, company=MagicMock(pk=5))
        
        # Cold call
        res1 = LeadDataService.get_lead_kpi_summary(user)
        self.assertEqual(res1, {"total": 50, "open": 35, "converted": 15})
        self.assertEqual(mock_qs.aggregate.call_count, 1)

        # Warm call - should hit cache and not re-run aggregate
        res2 = LeadDataService.get_lead_kpi_summary(user)
        self.assertEqual(res2, {"total": 50, "open": 35, "converted": 15})
        self.assertEqual(mock_qs.aggregate.call_count, 1)

        # Invalidate via bump
        bump_lead_cache_version(company_id=5, user_id=101)
        res3 = LeadDataService.get_lead_kpi_summary(user)
        self.assertEqual(res3, {"total": 50, "open": 35, "converted": 15})
        self.assertEqual(mock_qs.aggregate.call_count, 2)

    @patch("finlo_crm.leads.services.get_queryset_for_module")
    def test_get_lead_counts_by_stage_caching(self, mock_get_qs):
        """Ensure get_lead_counts_by_stage caches and returns stage-grouped tuples."""
        mock_qs = MagicMock()
        mock_filter = MagicMock()
        mock_values = MagicMock()
        mock_annotate = MagicMock()
        mock_annotate.order_by.return_value = [
            {"lead_status_id": 1, "lead_status__name": "New", "count": 12},
            {"lead_status_id": 2, "lead_status__name": "Contacted", "count": 8},
        ]
        mock_values.annotate.return_value = mock_annotate
        mock_filter.values.return_value = mock_values
        mock_qs.filter.return_value = mock_filter
        mock_get_qs.return_value = mock_qs

        user = MagicMock(pk=102, company=MagicMock(pk=5))

        rows1 = LeadDataService.get_lead_counts_by_stage(user)
        self.assertEqual(len(rows1), 2)
        self.assertEqual(rows1[0]["count"], 12)
        self.assertEqual(mock_filter.values.call_count, 1)

        # Warm call
        rows2 = LeadDataService.get_lead_counts_by_stage(user)
        self.assertEqual(len(rows2), 2)
        self.assertEqual(mock_filter.values.call_count, 1)


class ChartViewOptimizationTests(SimpleTestCase):
    """Test N+1 query elimination in FinloChartView via prefetch_map."""

    def test_label_for_group_key_uses_prefetch_map(self):
        view = FinloChartView()
        field = Lead._meta.get_field("lead_status")

        prefetch_map = {
            1: "Stage Alpha",
            2: "Stage Beta",
        }

        # Should retrieve from prefetch_map without calling related_model.objects.get
        label1 = view._label_for_group_key(field, 1, prefetch_map=prefetch_map)
        self.assertEqual(label1, "Stage Alpha")

        label2 = view._label_for_group_key(field, 2, prefetch_map=prefetch_map)
        self.assertEqual(label2, "Stage Beta")


class SkeletonTemplateRenderingTests(SimpleTestCase):
    """Verify skeleton partial templates render valid HTML with required guard classes."""

    def test_table_skeleton_renders_with_guard_classes(self):
        rendered = render_to_string("components/skeletons/table_skeleton.html")
        self.assertIn("finlo-skeleton", rendered)
        self.assertIn("id=\"finlo-skeleton-loader\"", rendered)
        self.assertIn("animate-pulse", rendered)

    def test_kpi_skeleton_renders_with_guard_classes(self):
        rendered = render_to_string("components/skeletons/kpi_skeleton.html")
        self.assertIn("finlo-skeleton", rendered)
        self.assertIn("animate-pulse", rendered)

    def test_chart_skeleton_renders_with_guard_classes(self):
        rendered = render_to_string("components/skeletons/chart_skeleton.html")
        self.assertIn("finlo-skeleton", rendered)
        self.assertIn("animate-pulse", rendered)

    def test_navbar_skeleton_renders_with_guard_classes(self):
        rendered = render_to_string("components/skeletons/navbar_skeleton.html")
        self.assertIn("finlo-skeleton", rendered)
        self.assertIn("animate-pulse", rendered)


class CspAndCacheSecurityTests(SimpleTestCase):
    """Verify CSP compliance and FinloViewCache skeleton safety."""

    def test_no_eval_patterns_in_list_view_templates(self):
        from pathlib import Path
        from django.conf import settings

        list_view_html = (
            Path(settings.BASE_DIR)
            / "finlo"
            / "contrib"
            / "generics"
            / "templates"
            / "list_view.html"
        ).read_text(encoding="utf-8")

        delete_mode_html = (
            Path(settings.BASE_DIR)
            / "finlo"
            / "contrib"
            / "generics"
            / "templates"
            / "partials"
            / "delete_mode_form.html"
        ).read_text(encoding="utf-8")

        self.assertNotIn('hx-vals="js:', list_view_html)
        self.assertNotIn("hx-vals='js:", list_view_html)
        self.assertNotIn('_="on click', list_view_html)
        self.assertNotRegex(list_view_html, r"\bonclick\s*=")
        self.assertNotRegex(list_view_html, r"\bonchange\s*=")
        self.assertNotRegex(list_view_html, r"\bhx-on(?::|\s*=)")
        self.assertNotIn('hx-vals="js:', delete_mode_html)
        self.assertNotIn("hx-vals='js:", delete_mode_html)
        self.assertNotRegex(delete_mode_html, r"\bonclick\s*=")
        self.assertNotRegex(delete_mode_html, r"\bonchange\s*=")
        self.assertNotRegex(delete_mode_html, r"\bhx-on(?::|\s*=)")
        self.assertIn('data-finlo-action="bulk-delete"', list_view_html)
        self.assertIn('data-confirm-message=', list_view_html)

    def test_generic_list_and_delete_templates_compile(self):
        from django.template.loader import get_template

        get_template("list_view.html")
        get_template("partials/delete_mode_form.html")

    def test_navigation_history_guards_against_caching_skeletons(self):
        from pathlib import Path
        from django.conf import settings

        nav_script = (
            Path(settings.BASE_DIR)
            / "static"
            / "assets"
            / "js"
            / "navigation_history.js"
        ).read_text(encoding="utf-8")

        self.assertIn('.querySelector(".finlo-skeleton")', nav_script)
        self.assertIn('tempTest.querySelector(".finlo-skeleton")', nav_script)

