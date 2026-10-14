"""Isolated tests for FINLONEXA's sales hierarchy and lead assignment rules."""

import secrets
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from horilla.auth.models import User
from horilla.contrib.core.authorization import can_access_company_record
from horilla.contrib.core.models import (
    Company,
    Role,
    SalesAssignment,
    SalesRegion,
    SalesTeam,
)
from horilla.contrib.core.sales_authorization import (
    has_effective_permission,
    get_sales_scope_region_ids,
    get_sales_scope_user_ids,
)
from horilla.contrib.utils.middlewares import _thread_local
from horilla.core.exceptions import PermissionDenied
from horilla_crm.leads.api.views import LeadViewSet
from horilla_crm.leads.authorization import assign_lead_to_bdo
from horilla.contrib.core.views.export_data import get_export_queryset
from horilla.api.permissions import HorillaModelPermissions
from horilla.contrib.dashboard.views.component import DashboardComponentFormView
from horilla.contrib.generics.views.details import (
    check_record_access,
    check_record_change_access,
    check_record_delete_access,
)
from horilla_crm.leads.forms import LeadSubOwnerForm
from horilla_crm.leads.models import Lead, LeadStatus
from horilla_crm.leads.signals import apply_assignment_rules
from horilla.contrib.reports.views.export_views import ReportExportView
from horilla.contrib.dashboard.views.dashboard_helper import get_kpi_data


class SalesHierarchyTests(TestCase):
    """Validate hierarchy scope, transfers, and guarded lead assignment."""

    def setUp(self):
        self.company = Company.objects.create(
            name="Northstar", email="northstar@example.test", country="US"
        )
        self.other_company = Company.objects.create(
            name="Southstar", email="southstar@example.test", country="US"
        )

        self.roles = {}
        parent_role = None
        for key, label in Role.SALES_ROLE_CHOICES:
            self.roles[key] = Role.all_objects.create(
                role_name=str(label),
                system_key=key,
                parent_role=parent_role,
                company=self.company,
            )
            parent_role = self.roles[key]

        self.region = SalesRegion.all_objects.create(
            name="North", code="N", company=self.company
        )
        self.other_region = SalesRegion.all_objects.create(
            name="South", code="S", company=self.company
        )

        self.head = self.make_user("head", "SUPER_ADMIN")
        self.head_of_sales = self.make_user("sales-head", "HEAD_OF_SALES")
        self.rsm = self.make_user("rsm", "RSM")
        self.ssm = self.make_user("ssm", "SSM")
        self.asm = self.make_user("asm", "ASM")
        self.bdo = self.make_user("bdo", "BDO")
        self.other_rsm = self.make_user("other-rsm", "RSM")
        self.other_ssm = self.make_user("other-ssm", "SSM")
        self.other_asm = self.make_user("other-asm", "ASM")
        self.other_bdo = self.make_user("other-bdo", "BDO")
        self.unrelated_asm = self.make_user("unrelated-asm", "ASM")

        self.make_assignment(self.head, None, None)
        self.make_assignment(self.head_of_sales, None, None)
        self.make_assignment(
            self.rsm, self.region, self.head_of_sales
        )
        self.make_assignment(
            self.ssm, self.region, self.rsm
        )
        self.make_assignment(
            self.asm, self.region, self.ssm
        )
        self.make_assignment(
            self.other_rsm, self.other_region, self.head_of_sales
        )
        self.make_assignment(
            self.other_ssm, self.other_region, self.other_rsm
        )
        self.make_assignment(
            self.other_asm, self.other_region, self.other_ssm
        )
        self.make_assignment(
            self.unrelated_asm, self.region, self.ssm
        )

        self.team = self.make_team("North-A", self.region, self.ssm, self.asm)
        self.other_team = self.make_team(
            "South-A", self.other_region, self.other_ssm, self.other_asm
        )
        self.unrelated_team = self.make_team(
            "North-B", self.region, self.ssm, self.unrelated_asm
        )
        self.bdo_assignment = self.make_assignment(
            self.bdo, self.region, self.asm, self.team
        )
        self.other_bdo_assignment = self.make_assignment(
            self.other_bdo, self.other_region, self.other_asm, self.other_team
        )

        self.status = LeadStatus.all_objects.create(
            name="New", probability=0, company=self.company
        )
        self.grant(self.asm, "change_lead", "view_lead")
        self.grant(self.unrelated_asm, "change_lead", "view_lead")

    def make_user(self, username, role_key, company=None):
        return User.objects.create_user(
            username=username,
            password="Synthetic-test-password-41!",
            company=company or self.company,
            role=self.roles[role_key],
            country="US",
        )

    def make_assignment(self, user, region, manager, team=None):
        return SalesAssignment.all_objects.create(
            user=user,
            region=region,
            manager=manager,
            team=team,
            company=user.company,
            created_by=user,
            updated_by=user,
            is_active=True,
        )

    def make_team(self, code, region, ssm, asm):
        return SalesTeam.all_objects.create(
            name=code,
            code=code,
            company=self.company,
            region=region,
            senior_sales_manager=ssm,
            area_sales_manager=asm,
        )

    def make_lead(self, owner, company=None):
        previous_request = getattr(_thread_local, "request", None)
        _thread_local.request = SimpleNamespace(user=owner)
        try:
            return Lead.all_objects.create(
                company=company or owner.company,
                created_by=owner,
                lead_owner=owner,
                first_name=f"Synthetic-{Lead.all_objects.count() + 1}",
                last_name="Lead",
                email=f"{owner.username}@example.test",
                lead_source="website",
                lead_status=self.status,
                lead_company="Synthetic Co",
                industry="other",
                country="US",
            )
        finally:
            if previous_request is None:
                delattr(_thread_local, "request")
            else:
                _thread_local.request = previous_request

    @staticmethod
    def grant(user, *codenames):
        permissions = Permission.objects.filter(
            content_type__app_label="leads", codename__in=codenames
        )
        user.user_permissions.add(*permissions)

    def test_global_head_can_manage_regions_and_rsm_may_report_to_head(self):
        self.assertIsNone(self.head_of_sales.sales_assignment.region_id)
        self.assertEqual(self.rsm.sales_assignment.manager_id, self.head_of_sales.pk)
        self.assertEqual(
            get_sales_scope_user_ids(self.head_of_sales),
            {
                self.head_of_sales.pk,
                self.head.pk,
                self.rsm.pk,
                self.ssm.pk,
                self.asm.pk,
                self.bdo.pk,
                self.unrelated_asm.pk,
                self.other_rsm.pk,
                self.other_ssm.pk,
                self.other_asm.pk,
                self.other_bdo.pk,
            },
        )
        self.assertEqual(
            get_sales_scope_user_ids(self.head), get_sales_scope_user_ids(self.head_of_sales)
        )

    def test_six_role_scopes_respect_region_and_reporting_tree(self):
        self.assertEqual(
            get_sales_scope_user_ids(self.rsm),
            {self.rsm.pk, self.ssm.pk, self.asm.pk, self.bdo.pk, self.unrelated_asm.pk},
        )
        self.assertEqual(
            get_sales_scope_user_ids(self.ssm),
            {self.ssm.pk, self.asm.pk, self.bdo.pk, self.unrelated_asm.pk},
        )
        self.assertEqual(
            get_sales_scope_user_ids(self.asm), {self.asm.pk, self.bdo.pk}
        )
        self.assertEqual(get_sales_scope_user_ids(self.bdo), {self.bdo.pk})
        self.assertEqual(get_sales_scope_region_ids(self.rsm), {self.region.pk})
        self.assertEqual(
            get_sales_scope_region_ids(self.head_of_sales),
            {self.region.pk, self.other_region.pk},
        )

    def test_role_permission_matrix_is_a_ceiling_over_django_grants(self):
        modules = {
            "dashboard": ("dashboard", "dashboard"),
            "leads": ("leads", "lead"),
            "accounts": ("accounts", "account"),
            "contacts": ("contacts", "contact"),
            "opportunities": ("opportunities", "opportunity"),
            "activities": ("activity", "activity"),
            "reports": ("reports", "report"),
            "employees": ("core", "horillauser"),
            "regions": ("core", "salesregion"),
            "teams": ("core", "salesteam"),
            "settings": ("core", "company"),
        }
        role_users = {
            "SUPER_ADMIN": self.head,
            "HEAD_OF_SALES": self.head_of_sales,
            "RSM": self.rsm,
            "SSM": self.ssm,
            "ASM": self.asm,
            "BDO": self.bdo,
        }

        def expected(role, module, action):
            if role == "SUPER_ADMIN":
                return True
            if module in {"dashboard", "reports", "employees", "regions", "teams"}:
                return action == "view"
            if module == "settings":
                return False
            if action == "view":
                return True
            if action == "add":
                return module in {"leads", "activities"}
            if action == "change":
                return role in {"RSM", "SSM", "ASM", "BDO"}
            return False

        for role, user in role_users.items():
            for module, (app_label, model_name) in modules.items():
                for action in ("view", "add", "change", "delete"):
                    permission = f"{app_label}.{action}_{model_name}"
                    with patch.object(user, "has_perm", return_value=True):
                        self.assertEqual(
                            has_effective_permission(user, permission),
                            expected(role, module, action),
                            f"{role} {module} {action}",
                        )

        permission = "activity.add_activity"
        with patch.object(self.asm, "has_perm", return_value=False):
            self.assertFalse(has_effective_permission(self.asm, permission))
        with patch.object(self.asm, "has_perm", return_value=True):
            self.assertTrue(has_effective_permission(self.asm, permission))

    def test_drf_and_html_permission_checks_follow_lead_role_matrix(self):
        from types import SimpleNamespace

        users_by_role = {
            "SUPER_ADMIN": self.head,
            "HEAD_OF_SALES": self.head_of_sales,
            "RSM": self.rsm,
            "SSM": self.ssm,
            "ASM": self.asm,
            "BDO": self.bdo,
        }
        for user in users_by_role.values():
            self.grant(
                user,
                "view_lead",
                "add_lead",
                "change_lead",
                "delete_lead",
            )
        lead = self.make_lead(self.asm)
        lead.sub_owner = self.bdo
        lead.save(update_fields=["sub_owner"])
        api_permissions = HorillaModelPermissions()
        role_expectations = {
            "SUPER_ADMIN": (True, True, True, True),
            "HEAD_OF_SALES": (True, True, False, False),
            "RSM": (True, True, True, False),
            "SSM": (True, True, True, False),
            "ASM": (True, True, True, False),
            "BDO": (True, True, True, False),
        }

        for role_key, user in users_by_role.items():
            expected = role_expectations[role_key]
            for operation, method, expected_allowed in zip(
                ("list", "create", "bulk_update", "bulk_delete"),
                ("get", "post", "post", "post"),
                expected,
            ):
                request = getattr(APIRequestFactory(), method)(
                    "/api/leads/", {}, format="json"
                )
                request.user = user
                view = SimpleNamespace(
                    get_queryset=lambda: Lead.objects.all(),
                    action=operation,
                    change_actions=set(),
                    delete_actions=set(),
                    list_actions=set(),
                )
                with self.subTest(role=role_key, operation=operation):
                    self.assertEqual(
                        api_permissions.has_permission(request, view),
                        expected_allowed,
                    )

            with self.subTest(role=role_key, operation="html-record-policy"):
                self.assertEqual(check_record_access(user, lead), expected[0])
                self.assertEqual(check_record_change_access(user, lead), expected[2])
                self.assertEqual(check_record_delete_access(user, lead), expected[3])

    def test_sales_roles_cannot_export_even_when_django_export_grant_exists(self):
        permission = Permission.objects.filter(
            content_type__app_label="leads", codename="export_lead"
        ).first()
        if permission is not None:
            self.asm.user_permissions.add(permission)
            self.asm = User.objects.get(pk=self.asm.pk)
        self.assertIsNone(get_export_queryset(self.asm, Lead))

        foreign_lead = self.make_lead(self.head, self.other_company)
        self.assertIn(
            foreign_lead.pk,
            set(get_export_queryset(self.head, Lead).values_list("pk", flat=True)),
        )

    def test_six_dummy_accounts_exist_only_with_hashed_random_passwords(self):
        expected_roles = {
            "test_superadmin": "SUPER_ADMIN",
            "test_head_sales": "HEAD_OF_SALES",
            "test_rsm": "RSM",
            "test_ssm": "SSM",
            "test_asm": "ASM",
            "test_bdo": "BDO",
        }
        users = []
        for username, role_key in expected_roles.items():
            role = Role.all_objects.get(company=self.company, system_key=role_key)
            user = User.objects.create_user(
                username=username,
                password=secrets.token_urlsafe(32),
                company=self.company,
                role=role,
                country="US",
            )
            users.append(user)

        by_username = {user.username: user for user in users}
        superadmin = by_username["test_superadmin"]
        head = by_username["test_head_sales"]
        rsm = by_username["test_rsm"]
        ssm = by_username["test_ssm"]
        asm = by_username["test_asm"]
        bdo = by_username["test_bdo"]
        self.make_assignment(superadmin, None, None)
        self.make_assignment(head, None, None)
        self.make_assignment(rsm, self.region, head)
        self.make_assignment(ssm, self.region, rsm)
        self.make_assignment(asm, self.region, ssm)
        test_team = SalesTeam.all_objects.create(
            name="Test-South",
            code="TEST-SOUTH",
            company=self.company,
            region=self.region,
            senior_sales_manager=ssm,
            area_sales_manager=asm,
        )
        bdo_assignment = self.make_assignment(bdo, self.region, asm, test_team)

        self.assertEqual(len(users), 6)
        self.assertEqual(superadmin.sales_assignment.user_id, superadmin.pk)
        self.assertEqual(head.sales_assignment.user_id, head.pk)
        self.assertEqual(rsm.sales_assignment.manager_id, head.pk)
        self.assertEqual(ssm.sales_assignment.manager_id, rsm.pk)
        self.assertEqual(asm.sales_assignment.manager_id, ssm.pk)
        self.assertEqual(bdo_assignment.manager_id, asm.pk)
        self.assertEqual(
            SalesAssignment.all_objects.filter(user=bdo, is_active=True).count(), 1
        )
        self.assertEqual(
            {user.username for user in User.objects.filter(username__in=expected_roles)},
            set(expected_roles),
        )
        for user in users:
            with self.subTest(username=user.username):
                self.assertTrue(user.password.startswith("pbkdf2_"))
                self.assertEqual(
                    user.role.system_key, expected_roles[user.username]
                )
                self.assertFalse(user.is_staff)
                self.assertFalse(user.is_superuser)

    def test_inactive_users_are_not_in_manager_visibility_or_assignable_as_manager(self):
        self.asm.is_active = False
        self.asm.save(update_fields=["is_active"])

        self.assertNotIn(self.asm.pk, get_sales_scope_user_ids(self.ssm))
        self.assertNotIn(self.bdo.pk, get_sales_scope_user_ids(self.ssm))
        inactive_manager_bdo = self.make_user(
            "inactive-manager-check", "BDO"
        )
        invalid_assignment = SalesAssignment(
            user=inactive_manager_bdo,
            company=self.company,
            region=self.region,
            manager=self.asm,
            team=self.team,
            created_by=self.asm,
            updated_by=self.asm,
        )
        with self.assertRaises(ValidationError):
            invalid_assignment.full_clean()

    def test_staff_flag_does_not_exceed_sales_role_policy(self):
        self.bdo.is_staff = True
        self.bdo.save(update_fields=["is_staff"])
        self.bdo = User.objects.get(pk=self.bdo.pk)

        self.assertFalse(
            has_effective_permission(self.bdo, "core.add_salesregion")
        )
        self.assertFalse(
            has_effective_permission(self.bdo, "leads.delete_lead")
        )
        self.assertNotIn(
            self.other_bdo.pk, get_sales_scope_user_ids(self.bdo)
        )

    def test_html_dashboard_form_respects_sales_permission_ceiling(self):
        permission = Permission.objects.get(
            content_type__app_label="dashboard",
            codename="add_dashboardcomponent",
        )
        self.bdo.user_permissions.add(permission)
        self.bdo = User.objects.get(pk=self.bdo.pk)

        view = DashboardComponentFormView()
        view.request = SimpleNamespace(user=self.bdo)
        view.kwargs = {}

        self.assertFalse(view.has_permission())

    def test_report_data_and_totals_respect_sales_scope(self):
        allowed = self.make_lead(self.asm)
        out_of_team = self.make_lead(self.unrelated_asm)
        other_region = self.make_lead(self.other_asm)
        other_company = self.make_lead(self.asm, self.other_company)

        report = SimpleNamespace(
            model_class=Lead,
            aggregate_columns_dict=[],
            selected_columns_list=["first_name"],
            row_groups_list=[],
            column_groups_list=[],
            filters_dict={},
        )
        request = APIRequestFactory().get("/reports/export/")
        request.user = self.asm

        dataframe, context = ReportExportView().get_report_data(report, request)

        self.assertEqual(context["total_count"], 1)
        self.assertEqual(dataframe["first_name"].tolist(), [allowed.first_name])
        for excluded in (out_of_team, other_region, other_company):
            self.assertNotIn(excluded.first_name, dataframe["first_name"].tolist())

    def test_dashboard_kpi_uses_company_and_hierarchy_scoped_queryset(self):
        allowed = self.make_lead(self.asm)
        self.make_lead(self.unrelated_asm)
        self.make_lead(self.other_asm)
        self.make_lead(self.asm, self.other_company)

        component = SimpleNamespace(
            module=SimpleNamespace(model="lead"),
            conditions=Mock(),
            metric_type="count",
        )
        component.conditions.all.return_value.order_by.return_value = []
        request = SimpleNamespace(user=self.asm, GET={})

        result = get_kpi_data(component, request)

        self.assertEqual(result["value"], 1.0)
        self.assertEqual(result["label"], "Count of Lead")
        self.assertIsNotNone(allowed.pk)

        self.asm.user_permissions.remove(
            Permission.objects.get(
                content_type__app_label="leads", codename="view_lead"
            )
        )
        self.asm = User.objects.get(pk=self.asm.pk)
        request.user = self.asm
        denied_result = get_kpi_data(component, request)
        self.assertEqual(denied_result["value"], 0.0)

    def test_active_bdo_has_one_direct_asm_and_only_that_asm_may_assign(self):
        lead = self.make_lead(self.asm)

        assigned = assign_lead_to_bdo(lead, self.asm, self.bdo)

        assigned.refresh_from_db()
        self.assertEqual(assigned.lead_owner_id, self.asm.pk)
        self.assertEqual(assigned.sub_owner_id, self.bdo.pk)
        self.assertEqual(self.bdo_assignment.manager_id, self.asm.pk)
        self.assertGreater(assigned.histories.count(), 0)
        self.assertEqual(
            SalesAssignment.all_objects.filter(user_id=self.bdo.pk).count(), 1
        )
        with self.assertRaises(ValidationError):
            SalesAssignment(
                user=self.bdo,
                company=self.company,
                region=self.region,
                manager=self.unrelated_asm,
                team=self.unrelated_team,
                created_by=self.asm,
                updated_by=self.asm,
            ).full_clean()
        with self.assertRaises(ValidationError):
            inactive_bdo_assignment = SalesAssignment(
                user=self.bdo,
                company=self.company,
                region=self.region,
                manager=self.asm,
                team=self.team,
                is_active=False,
                created_by=self.asm,
                updated_by=self.asm,
            )
            inactive_bdo_assignment.full_clean()
        with self.assertRaises(PermissionDenied):
            assign_lead_to_bdo(lead, self.unrelated_asm, self.bdo)

    def test_automatic_assignment_rules_cannot_replace_finlonexa_lead_owner(self):
        lead = self.make_lead(self.asm)

        apply_assignment_rules(lead)

        lead.refresh_from_db()
        self.assertEqual(lead.lead_owner_id, self.asm.pk)
        self.assertIsNone(lead.sub_owner_id)

    def test_html_and_api_assignment_surfaces_reject_another_asms_bdo(self):
        lead = self.make_lead(self.asm)
        form = LeadSubOwnerForm(
            instance=lead,
            request=SimpleNamespace(user=self.asm),
        )
        selectable_bdo_ids = set(
            form.fields["sub_owner"].queryset.values_list("pk", flat=True)
        )
        self.assertIn(self.bdo.pk, selectable_bdo_ids)
        self.assertNotIn(self.other_bdo.pk, selectable_bdo_ids)

        request = APIRequestFactory().post(
            f"/api/leads/{lead.pk}/assign_bdo/",
            {"bdo_id": self.other_bdo.pk},
            format="json",
        )
        force_authenticate(request, user=self.asm)
        response = LeadViewSet.as_view({"post": "assign_bdo"})(
            request, pk=lead.pk
        )
        self.assertIn(response.status_code, {400, 403})
        lead.refresh_from_db()
        self.assertIsNone(lead.sub_owner_id)

    def test_assignment_requires_immediately_higher_role_and_matching_region(self):
        with self.assertRaises(ValidationError):
            SalesAssignment(
                user=self.bdo,
                company=self.company,
                region=self.region,
                manager=self.ssm,
                team=self.team,
                created_by=self.asm,
                updated_by=self.asm,
            ).full_clean()

        with self.assertRaises(ValidationError):
            SalesAssignment(
                user=self.bdo,
                company=self.company,
                region=self.other_region,
                manager=self.asm,
                team=self.team,
                created_by=self.asm,
                updated_by=self.asm,
            ).full_clean()

    def test_cross_company_manager_and_region_are_rejected(self):
        foreign_user = self.make_user("foreign-bdo", "BDO", self.other_company)
        with self.assertRaises(ValidationError):
            SalesAssignment(
                user=foreign_user,
                company=self.other_company,
                region=self.region,
                manager=self.asm,
                team=self.team,
                created_by=self.asm,
                updated_by=self.asm,
            ).full_clean()

        foreign_lead = self.make_lead(self.asm, company=self.other_company)
        self.assertFalse(can_access_company_record(self.asm, foreign_lead))

    def test_bdo_transfer_to_another_asm_requires_valid_team_and_succeeds(self):
        new_team = self.make_team("North-C", self.region, self.ssm, self.unrelated_asm)
        self.bdo_assignment.manager = self.unrelated_asm
        self.bdo_assignment.team = new_team
        self.bdo_assignment.save()

        self.bdo_assignment.refresh_from_db()
        self.assertEqual(self.bdo_assignment.manager_id, self.unrelated_asm.pk)
        self.assertEqual(self.bdo_assignment.team_id, new_team.pk)

    def test_assignment_denied_after_change_permission_is_revoked(self):
        lead = self.make_lead(self.asm)
        self.asm.user_permissions.remove(
            Permission.objects.get(
                content_type__app_label="leads", codename="change_lead"
            )
        )
        self.asm = User.objects.get(pk=self.asm.pk)

        with self.assertRaises(PermissionDenied):
            assign_lead_to_bdo(lead, self.asm, self.bdo)

    def test_api_list_and_record_policy_use_the_same_sales_scope(self):
        allowed_lead = self.make_lead(self.asm)
        out_of_scope_lead = self.make_lead(self.other_asm)
        sibling_team_lead = self.make_lead(self.unrelated_asm)
        request = APIRequestFactory().get("/api/leads/")
        force_authenticate(request, user=self.asm)
        response = LeadViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        returned_ids = {row["id"] for row in response.data["results"]}
        self.assertIn(allowed_lead.pk, returned_ids)
        self.assertNotIn(out_of_scope_lead.pk, returned_ids)
        self.assertNotIn(sibling_team_lead.pk, returned_ids)
        self.assertTrue(can_access_company_record(self.asm, allowed_lead))
        self.assertFalse(can_access_company_record(self.asm, out_of_scope_lead))

        foreign_company_lead = self.make_lead(self.asm, self.other_company)
        foreign_request = APIRequestFactory().get(
            f"/api/leads/{foreign_company_lead.pk}/"
        )
        force_authenticate(foreign_request, user=self.asm)
        foreign_response = LeadViewSet.as_view({"get": "retrieve"})(
            foreign_request, pk=foreign_company_lead.pk
        )
        self.assertEqual(foreign_response.status_code, 404)

    def test_bdo_api_visibility_is_limited_to_owned_or_subowned_leads(self):
        assigned = self.make_lead(self.asm)
        assigned.sub_owner = self.bdo
        assigned.save(update_fields=["sub_owner"])
        owner_only = self.make_lead(self.asm)
        out_of_company = self.make_lead(self.bdo, self.other_company)
        self.grant(self.bdo, "view_lead")

        request = APIRequestFactory().get("/api/leads/")
        force_authenticate(request, user=self.bdo)
        response = LeadViewSet.as_view({"get": "list"})(request)

        self.assertEqual(response.status_code, 200)
        returned_ids = {row["id"] for row in response.data["results"]}
        self.assertIn(assigned.pk, returned_ids)
        self.assertNotIn(owner_only.pk, returned_ids)
        self.assertNotIn(out_of_company.pk, returned_ids)

        detail_request = APIRequestFactory().get(f"/api/leads/{assigned.pk}/")
        force_authenticate(detail_request, user=self.bdo)
        allowed_detail = LeadViewSet.as_view({"get": "retrieve"})(
            detail_request, pk=assigned.pk
        )
        denied_request = APIRequestFactory().get(f"/api/leads/{owner_only.pk}/")
        force_authenticate(denied_request, user=self.bdo)
        denied_detail = LeadViewSet.as_view({"get": "retrieve"})(
            denied_request, pk=owner_only.pk
        )
        self.assertEqual(allowed_detail.status_code, 200)
        self.assertEqual(denied_detail.status_code, 404)

    def test_api_bulk_update_cannot_transfer_lead_ownership(self):
        lead = self.make_lead(self.asm)
        patch_request = APIRequestFactory().patch(
            f"/api/leads/{lead.pk}/",
            {"lead_owner": self.other_asm.pk},
            format="json",
        )
        force_authenticate(patch_request, user=self.asm)
        patch_response = LeadViewSet.as_view({"patch": "partial_update"})(
            patch_request, pk=lead.pk
        )
        self.assertEqual(patch_response.status_code, 400)

        request = APIRequestFactory().post(
            "/api/leads/bulk_update/",
            {
                "ids": [lead.pk],
                "data": {"lead_owner": self.other_asm.pk},
            },
            format="json",
        )
        force_authenticate(request, user=self.asm)

        response = LeadViewSet.as_view({"post": "bulk_update"})(request)

        self.assertEqual(response.status_code, 403)
        lead.refresh_from_db()
        self.assertEqual(lead.lead_owner_id, self.asm.pk)

    def test_existing_lead_conversion_flag_does_not_change_creator_owner(self):
        lead = self.make_lead(self.asm)
        request = APIRequestFactory().post(f"/api/leads/{lead.pk}/convert/")
        force_authenticate(request, user=self.asm)
        response = LeadViewSet.as_view({"post": "convert"})(request, pk=lead.pk)

        self.assertEqual(response.status_code, 200)
        lead.refresh_from_db()
        self.assertTrue(lead.is_convert)
        self.assertEqual(lead.lead_owner_id, self.asm.pk)
