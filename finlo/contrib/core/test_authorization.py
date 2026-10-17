"""Negative tests for tenant and privilege boundaries."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from finlo.api.mixins import scope_queryset_to_permission
from finlo.auth.models import User
from finlo.contrib.core.api.views import DepartmentViewSet, FinloUserViewSet
from finlo.contrib.core.authorization import (
    can_access_company_record,
    scope_queryset_to_company,
)
from finlo.contrib.core.models import Company, Department, Role
from finlo.contrib.utils.middlewares import _thread_local
from finlo.contrib.core.views.export_data import get_export_queryset
from finlo.contrib.core.views.users import ChangeUserCompanyView, UserDetailView
from finlo_crm.leads.models import Lead


class CompanyAuthorizationTests(TestCase):
    """Company, owner, user API, and export scopes fail closed."""

    def setUp(self):
        self.company = Company.objects.create(
            name="Alpha", email="alpha@example.test", country="US"
        )
        self.other_company = Company.objects.create(
            name="Beta", email="beta@example.test", country="US"
        )
        self.unassigned = User.objects.create_user(
            username="unassigned", password="test-password"
        )
        self.actor = User.objects.create_user(
            username="actor",
            password="test-password",
            company=self.company,
            country="US",
        )
        self.colleague = User.objects.create_user(
            username="colleague",
            password="test-password",
            company=self.company,
            country="US",
        )
        self.foreign_user = User.objects.create_user(
            username="foreign",
            password="test-password",
            company=self.other_company,
            country="US",
        )

    def grant(self, user, *actions):
        app_label = User._meta.app_label
        model_name = User._meta.model_name
        permissions = [
            Permission.objects.get(
                content_type__app_label=app_label,
                codename=f"{action}_{model_name}",
            )
            for action in actions
        ]
        user.user_permissions.add(*permissions)

    def call_user_api(self, action, method, data=None, pk=None, user=None):
        factory = APIRequestFactory()
        request = getattr(factory, method)("/api/core/users/", data, format="json")
        request.session = {}
        force_authenticate(request, user=user or self.actor)
        view = FinloUserViewSet.as_view({method: action})
        if pk is None:
            return view(request)
        return view(request, pk=pk)

    def test_user_api_list_is_company_scoped_even_with_global_view_permission(self):
        self.grant(self.actor, "view")

        response = self.call_user_api("list", "get")

        self.assertEqual(response.status_code, 200)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(self.actor.pk, returned_ids)
        self.assertIn(self.colleague.pk, returned_ids)
        self.assertNotIn(self.foreign_user.pk, returned_ids)

    def test_user_api_detail_update_and_delete_reject_foreign_company_idor(self):
        self.actor.is_staff = True
        self.actor.save(update_fields=["is_staff"])
        self.grant(self.actor, "view", "change", "delete")

        read_response = self.call_user_api(
            "retrieve", "get", pk=self.foreign_user.pk
        )
        update_response = self.call_user_api(
            "partial_update",
            "patch",
            data={"first_name": "Changed"},
            pk=self.foreign_user.pk,
        )
        delete_response = self.call_user_api(
            "destroy", "delete", pk=self.foreign_user.pk
        )

        self.assertEqual(read_response.status_code, 404)
        self.assertEqual(update_response.status_code, 404, update_response.data)
        self.assertEqual(delete_response.status_code, 404)
        self.foreign_user.refresh_from_db()
        self.assertEqual(self.foreign_user.first_name, "")

    def test_user_api_create_rejects_other_company_and_role_escalation(self):
        self.grant(self.actor, "add")
        foreign_role = Role.all_objects.create(
            role_name="Foreign role", company=self.other_company
        )
        payload = {
            "username": "created-cross-company",
            "password": "Some-safe-test-password-987",
            "company": self.other_company.pk,
        }
        company_response = self.call_user_api("create", "post", data=payload)

        self.assertEqual(company_response.status_code, 400)
        self.assertFalse(
            User.objects.filter(username="created-cross-company").exists()
        )

        payload["company"] = self.company.pk
        payload["username"] = "created-with-foreign-role"
        payload["role"] = foreign_role.pk
        role_response = self.call_user_api("create", "post", data=payload)

        self.assertEqual(role_response.status_code, 400)
        self.assertFalse(
            User.objects.filter(username="created-with-foreign-role").exists()
        )

    def test_company_scoped_api_serializer_rejects_company_spoofing(self):
        department_permission = Permission.objects.get(
            content_type__app_label=Department._meta.app_label,
            codename=f"add_{Department._meta.model_name}",
        )
        self.actor.user_permissions.add(department_permission)
        request = APIRequestFactory().post(
            "/api/core/departments/",
            {
                "department_name": "Foreign department",
                "company": self.other_company.pk,
            },
            format="json",
        )
        request.session = {}
        force_authenticate(request, user=self.actor)
        response = DepartmentViewSet.as_view({"post": "create"})(request)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            Department.all_objects.filter(
                department_name="Foreign department", company=self.other_company
            ).exists()
        )

    def test_user_api_update_cannot_escalate_staff_or_permission_flags(self):
        self.grant(self.actor, "change")
        response = self.call_user_api(
            "partial_update",
            "patch",
            data={
                "is_staff": True,
                "is_superuser": True,
                "groups": [],
                "user_permissions": [],
            },
            pk=self.colleague.pk,
        )

        self.assertEqual(response.status_code, 200)
        self.colleague.refresh_from_db()
        self.assertFalse(self.colleague.is_staff)
        self.assertFalse(self.colleague.is_superuser)
        self.assertFalse(self.colleague.groups.exists())
        self.assertFalse(self.colleague.user_permissions.exists())

    def test_user_api_cannot_change_company_or_assign_role_without_authority(self):
        self.grant(self.actor, "change")
        company_response = self.call_user_api(
            "partial_update",
            "patch",
            data={"company": self.other_company.pk},
            pk=self.colleague.pk,
        )
        self.colleague.refresh_from_db()
        self.assertEqual(company_response.status_code, 400)
        self.assertEqual(self.colleague.company_id, self.company.pk)

        same_company_role = Role.all_objects.create(
            role_name="Restricted role", company=self.company
        )
        role_response = self.call_user_api(
            "partial_update",
            "patch",
            data={"role": same_company_role.pk},
            pk=self.colleague.pk,
        )
        self.assertEqual(role_response.status_code, 400)
        self.colleague.refresh_from_db()
        self.assertIsNone(self.colleague.role_id)

    def test_html_company_transfer_requires_superuser(self):
        view = ChangeUserCompanyView()
        view.request = SimpleNamespace(user=self.actor)
        form = SimpleNamespace(
            cleaned_data={"company": self.other_company},
            instance=self.colleague,
            add_error=Mock(),
        )
        view.form_invalid = Mock(return_value="rejected")

        response = view.form_valid(form)

        self.assertEqual(response, "rejected")
        form.add_error.assert_called_once()

        form.cleaned_data["company"] = None
        response = view.form_valid(form)

        self.assertEqual(response, "rejected")
        self.assertEqual(form.add_error.call_count, 2)

    def test_superuser_can_update_user_across_company(self):
        administrator = User.objects.create_superuser(
            username="platform-admin",
            email="admin@example.test",
            password="test-password",
            company=self.company,
            country="US",
        )

        response = self.call_user_api(
            "partial_update",
            "patch",
            data={"company": self.other_company.pk},
            pk=self.colleague.pk,
            user=administrator,
        )

        self.assertEqual(response.status_code, 200)
        self.colleague.refresh_from_db()
        self.assertEqual(self.colleague.company_id, self.other_company.pk)

    def test_bulk_update_and_delete_cannot_target_foreign_company_users(self):
        self.grant(self.actor, "change", "delete")
        update_response = self.call_user_api(
            "bulk_update",
            "post",
            data={
                "ids": [self.foreign_user.pk],
                "data": {
                    "is_active": False,
                    "username": "bulk-changed",
                    "company": self.company.pk,
                    "role": None,
                    "country": "US",
                    "password": "Some-safe-test-password-987",
                },
            },
        )
        delete_response = self.call_user_api(
            "bulk_delete", "post", data={"ids": [self.foreign_user.pk]}
        )

        self.assertEqual(update_response.status_code, 404, update_response.data)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(User.objects.filter(pk=self.foreign_user.pk).exists())
        self.foreign_user.refresh_from_db()
        self.assertTrue(self.foreign_user.is_active)

    def test_user_export_is_company_scoped_with_global_export_permission(self):
        self.grant(self.actor, "export")
        request = RequestFactory().get("/export/")
        request.user = self.actor
        request.session = {}

        queryset = get_export_queryset(self.actor, User, request=request)

        self.assertIsNotNone(queryset)
        self.assertEqual(
            set(queryset.values_list("pk", flat=True)),
            {self.actor.pk, self.colleague.pk},
        )

    def test_html_user_detail_queryset_is_company_scoped(self):
        request = RequestFactory().get("/users/")
        request.user = self.actor
        request.session = {}
        request.active_company = self.company
        view = UserDetailView()
        view.request = request

        returned_ids = set(view.get_queryset().values_list("pk", flat=True))

        self.assertIn(self.colleague.pk, returned_ids)
        self.assertNotIn(self.foreign_user.pk, returned_ids)

    def test_company_filtered_manager_uses_the_same_company_boundary(self):
        Role.all_objects.create(role_name="Alpha role", company=self.company)
        Role.all_objects.create(role_name="Beta role", company=self.other_company)
        request = RequestFactory().get("/roles/")
        request.user = self.actor
        request.session = {}
        request.active_company = self.company
        _thread_local.request = request
        self.addCleanup(delattr, _thread_local, "request")

        company_ids = set(Role.objects.values_list("company_id", flat=True))

        self.assertEqual(company_ids, {self.company.pk})

    def test_session_flags_cannot_expand_scope_without_switch_permission(self):
        request = SimpleNamespace(
            user=self.actor,
            session={"show_all_companies": True},
            active_company=self.other_company,
        )
        queryset = scope_queryset_to_company(User.objects.all(), self.actor, request)

        self.assertEqual(
            set(queryset.values_list("pk", flat=True)),
            {self.actor.pk, self.colleague.pk},
        )
        self.assertFalse(
            can_access_company_record(self.actor, self.foreign_user, request)
        )

    def test_company_switch_permission_can_select_one_company_or_all(self):
        switch_permission = Permission.objects.get(
            content_type__app_label=User._meta.app_label,
            codename="can_switch_company",
        )
        self.actor.user_permissions.add(switch_permission)
        request = SimpleNamespace(
            user=self.actor,
            session={"active_company_id": self.other_company.pk},
            active_company=None,
        )

        selected_company_ids = set(
            scope_queryset_to_company(
                User.objects.all(), self.actor, request
            ).values_list("pk", flat=True)
        )
        request.session["show_all_companies"] = True
        all_company_ids = set(
            scope_queryset_to_company(
                User.objects.all(), self.actor, request
            ).values_list("pk", flat=True)
        )

        self.assertEqual(selected_company_ids, {self.foreign_user.pk})
        self.assertEqual(
            all_company_ids,
            {
                self.unassigned.pk,
                self.actor.pk,
                self.colleague.pk,
                self.foreign_user.pk,
            },
        )

    def test_django_superuser_has_explicit_all_company_access(self):
        administrator = User.objects.create_superuser(
            username="platform-admin",
            email="admin@example.test",
            password="test-password",
            company=self.company,
            country="US",
        )
        request = SimpleNamespace(user=administrator, session={})

        queryset = scope_queryset_to_company(
            User.objects.all(), administrator, request
        )

        self.assertEqual(
            set(queryset.values_list("pk", flat=True)),
            {
                self.unassigned.pk,
                self.actor.pk,
                self.colleague.pk,
                self.foreign_user.pk,
                administrator.pk,
            },
        )

    def test_owner_api_scope_includes_subordinate_role_users(self):
        parent_role = Role.all_objects.create(
            role_name="Parent", company=self.company
        )
        child_role = Role.all_objects.create(
            role_name="Child", parent_role=parent_role, company=self.company
        )
        self.actor.role = parent_role
        self.actor.save(update_fields=["role"])
        self.colleague.role = child_role
        self.colleague.save(update_fields=["role"])
        request = SimpleNamespace(
            user=self.actor, session={}, active_company=self.company
        )
        owner_permission = (
            f"{Lead._meta.app_label}.view_own_{Lead._meta.model_name}"
        )

        with (
            patch.object(
                self.actor,
                "has_perm",
                side_effect=lambda permission: permission == owner_permission,
            ),
            patch(
                "finlo.api.mixins.get_granted_access_filter", return_value=None
            ),
            patch(
                "finlo.api.mixins.get_allowed_user_ids",
                return_value={self.actor.pk, self.colleague.pk},
            ),
        ):
            queryset = scope_queryset_to_permission(
                Lead.objects.all(), self.actor, "view", request=request
            )
            _, params = queryset.query.sql_with_params()

        self.assertIn(self.company.pk, params)
        self.assertIn(self.actor.pk, params)
        self.assertIn(self.colleague.pk, params)
