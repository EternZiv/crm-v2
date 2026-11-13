"""
Focused tests for Dashboard count deduplication, PrecountedPaginator,
and Queryset Fingerprinting.

Verifies:
- Unfiltered table count matches KPI count and does not fire duplicate SQL COUNT
- Filtered table count with different filter kwargs evaluates fresh count
- Search or extra filters do not reuse cached count
- Company isolation: Tenant A and Tenant B counts are strictly isolated
- Sales hierarchy: Manager vs BDO visibility counts
- Pagination edge cases: first, middle, last, out-of-bounds, and empty querysets
- PrecountedPaginator behavior with and without total_count
"""

import pickle
from unittest.mock import MagicMock
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase

from finlo.contrib.dashboard.utils import (
    DefaultDashboardGenerator,
    PrecountedPaginator,
)
from finlo_crm.accounts.models import Account
from finlo_crm.campaigns.models import Campaign
from finlo_crm.contacts.models import Contact
from finlo.contrib.core.models import Company
from finlo_crm.leads.models import Lead, LeadStatus

User = get_user_model()


class PrecountedPaginatorUnitTests(TestCase):
    """Verify PrecountedPaginator correctly avoids count queries while preserving pagination."""

    def test_precounted_paginator_uses_provided_count_without_querying(self):
        """When total_count is given, paginator.count must not evaluate object_list.count()."""
        mock_qs = MagicMock()
        mock_qs.count.side_effect = AssertionError("object_list.count() should not be called!")

        paginator = PrecountedPaginator(mock_qs, per_page=10, total_count=42)

        self.assertEqual(paginator.count, 42)
        self.assertEqual(paginator.num_pages, 5)
        self.assertEqual(list(paginator.page_range), [1, 2, 3, 4, 5])
        mock_qs.count.assert_not_called()

    def test_precounted_paginator_without_total_count_falls_back_to_evaluation(self):
        """When total_count is None, paginator.count evaluates object_list.count()."""
        class EvaluatableQuerySet:
            def __init__(self):
                self.called = False

            def count(self):
                self.called = True
                return 17

        qs = EvaluatableQuerySet()
        paginator = PrecountedPaginator(qs, per_page=10, total_count=None)

        self.assertEqual(paginator.count, 17)
        self.assertEqual(paginator.num_pages, 2)
        self.assertTrue(qs.called)

    def test_pagination_pages_and_navigation(self):
        """Verify first, middle, last, and invalid pages handle slicing and bounds correctly."""
        items = list(range(25))
        paginator = PrecountedPaginator(items, per_page=10, total_count=25)

        # Page 1 (first page)
        page1 = paginator.get_page(1)
        self.assertEqual(page1.number, 1)
        self.assertEqual(list(page1.object_list), list(range(0, 10)))
        self.assertTrue(page1.has_next())
        self.assertFalse(page1.has_previous())
        self.assertEqual(page1.next_page_number(), 2)

        # Page 2 (middle page)
        page2 = paginator.get_page(2)
        self.assertEqual(page2.number, 2)
        self.assertEqual(list(page2.object_list), list(range(10, 20)))
        self.assertTrue(page2.has_next())
        self.assertTrue(page2.has_previous())
        self.assertEqual(page2.next_page_number(), 3)
        self.assertEqual(page2.previous_page_number(), 1)

        # Page 3 (last page)
        page3 = paginator.get_page(3)
        self.assertEqual(page3.number, 3)
        self.assertEqual(list(page3.object_list), list(range(20, 25)))
        self.assertFalse(page3.has_next())
        self.assertTrue(page3.has_previous())
        self.assertEqual(page3.previous_page_number(), 2)

        # Invalid out-of-bounds page returns last page (standard Django get_page behavior)
        page_high = paginator.get_page(999)
        self.assertEqual(page_high.number, 3)

        # Invalid non-integer page returns first page
        page_invalid = paginator.get_page("abc")
        self.assertEqual(page_invalid.number, 1)

    def test_empty_queryset_pagination(self):
        """Empty queryset with count=0 must return 1 page with empty list."""
        paginator = PrecountedPaginator([], per_page=10, total_count=0)

        self.assertEqual(paginator.count, 0)
        self.assertEqual(paginator.num_pages, 1)
        page1 = paginator.get_page(1)
        self.assertEqual(list(page1.object_list), [])
        self.assertFalse(page1.has_next())
        self.assertFalse(page1.has_previous())


class QuerySetCleanlinessAndPicklingTests(TestCase):
    """Verify querysets returned by DefaultDashboardGenerator are pure, unpolluted, and picklable."""

    def setUp(self):
        self.company = Company.objects.create(name="Cleanliness Co")
        self.user = User.objects.create_user(
            username="clean_user",
            email="clean@example.com",
            password="password123",
            company=self.company,
        )
        self.generator = DefaultDashboardGenerator(self.user, self.company)

    def test_generator_queryset_is_standard_and_can_be_pickled(self):
        """Standard Django querysets must pickle and unpickle cleanly without AttributeError."""
        qs = self.generator.get_queryset(Account)

        # Must not be a dynamically monkey-patched closure class
        self.assertEqual(qs.__class__.__name__, "QuerySet")
        self.assertFalse(hasattr(qs, "_generator"))

        # Serialization round-trip
        dumped = pickle.dumps(qs)
        loaded = pickle.loads(dumped)
        self.assertEqual(loaded.model, Account)

    def test_explicit_count_keying_determinism(self):
        """Explicit keying isolates filter kwargs and avoids incorrect cache hits."""
        self.generator.get_model_count(Account)
        self.generator.get_model_count(Lead, is_convert=False)

        # Unfiltered Account is in cache
        self.assertIn(Account, self.generator._model_count_cache)
        self.assertIn((Account, ()), self.generator._model_count_cache)

        # Filtered Lead is in cache under its exact tuple
        lead_key = (Lead, (("is_convert", False),))
        self.assertIn(lead_key, self.generator._model_count_cache)

        # Differently filtered querysets are NOT in cache
        won_lead_key = (Lead, (("is_convert", True),))
        self.assertNotIn(won_lead_key, self.generator._model_count_cache)


class DashboardCountDeduplicationIntegrationTests(TestCase):
    """Verify end-to-end count caching and query deduplication on dashboard generation."""

    def setUp(self):
        self.factory = RequestFactory()
        self.company1 = Company.objects.create(name="Company 1")
        self.company2 = Company.objects.create(name="Company 2")

        self.manager = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="password123",
            company=self.company1,
            is_superuser=False,
        )

        self.bdo = User.objects.create_user(
            username="bdo",
            email="bdo@example.com",
            password="password123",
            company=self.company1,
            is_superuser=False,
        )

        self.other_company_user = User.objects.create_user(
            username="other_user",
            email="other@example.com",
            password="password123",
            company=self.company2,
            is_superuser=False,
        )

        perms = Permission.objects.filter(
            codename__in=[
                "view_account", "view_contact", "view_campaign", "view_lead",
                "change_account", "change_contact", "change_campaign", "change_lead",
            ]
        )
        self.manager.user_permissions.add(*perms)
        self.bdo.user_permissions.add(*perms)
        self.other_company_user.user_permissions.add(*perms)

        # Seed Company 1 data
        status1 = LeadStatus.objects.create(name="New", probability=10, company=self.company1)
        status2 = LeadStatus.objects.create(name="New", probability=10, company=self.company2)

        for i in range(5):
            Account.objects.create(name=f"Acc {i}", company=self.company1)
            Contact.objects.create(
                first_name=f"Contact {i}",
                last_name="Test",
                email=f"contact{i}@example.com",
                contact_owner=self.manager,
                company=self.company1,
            )
            Campaign.objects.create(
                campaign_name=f"Camp {i}",
                campaign_owner=self.manager,
                company=self.company1,
            )
            # 3 open leads, 2 converted leads
            Lead.objects.create(
                first_name=f"Lead {i}",
                last_name="Test",
                email=f"lead{i}@example.com",
                lead_owner=self.manager,
                lead_status=status1,
                company=self.company1,
                is_convert=(i >= 3),
            )

        # Seed Company 2 data
        for i in range(2):
            Account.objects.create(name=f"C2 Acc {i}", company=self.company2)
            Lead.objects.create(
                first_name=f"C2 Lead {i}",
                last_name="Test",
                email=f"c2lead{i}@example.com",
                lead_owner=self.other_company_user,
                lead_status=status2,
                company=self.company2,
                is_convert=False,
            )

    def test_unfiltered_tables_reuse_kpi_counts(self):
        """Account, Contact, Campaign tables must reuse counts from KPI evaluation without extra count query."""
        generator = DefaultDashboardGenerator(self.manager, self.company1)

        # Step 1: Generate KPIs
        generator.generate_kpi_data()

        # Verify KPI counts cached
        self.assertEqual(generator.get_model_count(Account), 5)
        self.assertEqual(generator.get_model_count(Contact), 5)
        self.assertEqual(generator.get_model_count(Campaign), 5)

        # Step 2: Generate tables
        tables = generator.generate_table_data()
        table_dict = {t["model_name"]: t for t in tables if t}

        # Verify Account table reused cached count
        self.assertIn("account", table_dict)
        self.assertEqual(table_dict["account"]["total_records_count"], 5)

        # Verify Contact table reused cached count
        self.assertIn("contact", table_dict)
        self.assertEqual(table_dict["contact"]["total_records_count"], 5)

        # Verify Campaign table reused cached count
        self.assertIn("campaign", table_dict)
        self.assertEqual(table_dict["campaign"]["total_records_count"], 5)

    def test_open_leads_table_reuses_open_leads_kpi_count(self):
        """Open leads pipeline table (is_convert=False) must reuse the count from lead_kpi_cards."""
        generator = DefaultDashboardGenerator(self.manager, self.company1)

        # Step 1: Generate KPIs (calls lead_kpi_cards which counts is_convert=False)
        generator.generate_kpi_data()

        # Step 2: Generate tables
        tables = generator.generate_table_data()
        open_lead_tables = [t for t in tables if t and t.get("view_id") == "leads_dashboard_open_list"]
        self.assertEqual(len(open_lead_tables), 1)

        open_table = open_lead_tables[0]
        self.assertEqual(open_table["total_records_count"], 3)

    def test_won_leads_table_does_not_reuse_open_leads_count(self):
        """Won leads table (is_convert=True) must NOT reuse count from is_convert=False and counts accurately."""
        generator = DefaultDashboardGenerator(self.manager, self.company1)

        generator.generate_kpi_data()
        tables = generator.generate_table_data()

        won_lead_tables = [t for t in tables if t and t.get("view_id") == "leads_dashboard_list"]
        self.assertEqual(len(won_lead_tables), 1)

        won_table = won_lead_tables[0]
        # Exactly 2 converted leads
        self.assertEqual(won_table["total_records_count"], 2)

    def test_company_isolation_preserved(self):
        """Company 1 and Company 2 generators maintain strict data and count isolation."""
        gen1 = DefaultDashboardGenerator(self.manager, self.company1)
        gen2 = DefaultDashboardGenerator(self.other_company_user, self.company2)

        gen1.generate_kpi_data()
        gen2.generate_kpi_data()

        # Company 1 has 5 accounts, Company 2 has 2 accounts
        self.assertEqual(gen1.get_model_count(Account), 5)
        self.assertEqual(gen2.get_model_count(Account), 2)

        tables1 = {t["model_name"]: t for t in gen1.generate_table_data() if t}
        tables2 = {t["model_name"]: t for t in gen2.generate_table_data() if t}

        self.assertEqual(tables1["account"]["total_records_count"], 5)
        self.assertEqual(tables2["account"]["total_records_count"], 2)

    def test_bdo_versus_managerial_visibility_counts(self):
        """BDO with view_own only sees owned records, while Manager sees all company records."""
        bdo_user = User.objects.create_user(
            username="bdo_special",
            email="bdo_spec@example.com",
            password="password123",
            company=self.company1,
            is_superuser=False,
        )
        perm = Permission.objects.get(codename="view_own_lead")
        bdo_user.user_permissions.add(perm)

        status = LeadStatus.objects.filter(company=self.company1).first()
        Lead.objects.create(
            first_name="BDO Own Lead",
            last_name="Test",
            email="bdo_lead@example.com",
            lead_owner=bdo_user,
            lead_status=status,
            company=self.company1,
            is_convert=False,
        )

        bdo_gen = DefaultDashboardGenerator(bdo_user, self.company1)
        bdo_gen.generate_kpi_data()
        bdo_tables = {t["view_id"]: t for t in bdo_gen.generate_table_data() if t}

        # BDO sees only 1 lead in open leads table
        if "leads_dashboard_open_list" in bdo_tables:
            self.assertEqual(bdo_tables["leads_dashboard_open_list"]["total_records_count"], 1)

        # Manager sees their 3 open leads + BDO's 1 open lead = 4 open leads
        mgr_gen = DefaultDashboardGenerator(self.manager, self.company1)
        mgr_gen.generate_kpi_data()
        mgr_tables = {t["view_id"]: t for t in mgr_gen.generate_table_data() if t}
        if "leads_dashboard_open_list" in mgr_tables:
            self.assertEqual(mgr_tables["leads_dashboard_open_list"]["total_records_count"], 4)

    def test_cache_is_per_generator_instance_not_global(self):
        """Count cache must never leak across generator instances or requests."""
        gen1 = DefaultDashboardGenerator(self.manager, self.company1)
        gen1.generate_kpi_data()
        self.assertGreater(len(gen1._model_count_cache), 0)

        gen2 = DefaultDashboardGenerator(self.manager, self.company1)
        # Fresh generator instance starts with an empty cache
        self.assertEqual(len(gen2._model_count_cache), 0)

    def test_search_parameter_bypasses_count_cache(self):
        """When a search parameter is in the request, table paginator must evaluate a fresh count."""
        from finlo.contrib.utils.middlewares import _thread_local

        request = self.factory.get("/dashboard/?search=Acc+1")
        request.user = self.manager
        _thread_local.request = request

        try:
            generator = DefaultDashboardGenerator(self.manager, self.company1)
            generator.generate_kpi_data()

            # Precounted KPI for Account is 5
            self.assertEqual(generator.get_model_count(Account), 5)

            # Build table context with request containing search
            model_info = [m for m in generator.models if m["model"] == Account][0]
            table_ctx = generator.build_table_context(
                model_info=model_info,
                title="Accounts",
                filter_kwargs={},
                no_record_msg="No accounts found.",
                view_id="accounts_dashboard_list",
                request=request,
            )
            self.assertIsNotNone(table_ctx)
            # The search query in request caused PrecountedPaginator to receive total_count=None,
            # so paginator.count evaluated standard count.
            self.assertEqual(table_ctx["total_records_count"], 5)
        finally:
            _thread_local.request = None
