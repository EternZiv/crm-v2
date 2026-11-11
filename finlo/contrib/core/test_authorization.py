"""Negative tests for tenant and privilege boundaries."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.http import HttpRequest
from django.test import Client, RequestFactory, TestCase
from django.utils.module_loading import import_module
from rest_framework.test import APIRequestFactory, force_authenticate


class UserAgentClient(Client):
    """Provide realistic request metadata for login_history signal receivers."""

    def _login(self, user, backend=None):
        request = HttpRequest()
        if self.session:
            request.session = self.session
        else:
            engine = import_module(settings.SESSION_ENGINE)
            request.session = engine.SessionStore()
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"
        login(request, user, backend)
        request.session.save()
        self._set_login_cookies(request)

from finlo.api.mixins import scope_queryset_to_permission
from finlo.auth.models import User
from finlo.contrib.core.api.views import DepartmentViewSet, FinloUserViewSet
from finlo.contrib.core.authorization import (
    can_access_company_record,
    scope_queryset_to_company,
)
from finlo.contrib.core.models import (
    Company,
    Department,
    Role,
    RoleDataScope,
)
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

    def test_owner_api_scope_uses_allowed_user_ids(self):
        request = SimpleNamespace(
            user=self.actor, session={}, active_company=self.company
        )
        self.actor.user_permissions.add(
            Permission.objects.get(
                content_type__app_label=Lead._meta.app_label,
                codename=f"view_own_{Lead._meta.model_name}",
            )
        )

        with (
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

    def test_super_admin_role_has_full_settings_menu_and_tag_access_without_is_superuser(self):
        from finlo.contrib.generics.templatetags.finlo_tags.permission_tags import (
            has_perm,
            has_super_user,
        )
        from finlo.menu.settings_menu import get_settings_menu

        super_admin_role = Role.all_objects.create(
            role_name="Super Admin",
            system_key="SUPER_ADMIN",
            company=self.company,
        )
        self.actor.role = super_admin_role
        self.actor.save(update_fields=["role"])
        self.assertFalse(self.actor.is_superuser)

        request = RequestFactory().get("/settings-view/")
        request.user = self.actor
        request.active_company = self.company

        menu = get_settings_menu(request)
        self.assertTrue(len(menu) > 0)
        self.assertTrue(self.actor.has_any_perms(["core.can_view_finlo_settings"]))
        self.assertTrue(has_perm({"request": request}, "core.can_view_finlo_settings"))
        self.assertTrue(has_super_user(self.actor, "core.view_finlouser"))

    def test_role_maker_toggle_updates_live_role_grants_without_copying(self):
        custom_role = Role.all_objects.create(
            role_name="Custom Analyst",
            company=self.company,
        )
        self.colleague.role = custom_role
        self.colleague.save(update_fields=["role"])

        perm = Permission.objects.get(
            content_type__app_label="leads",
            codename="view_lead",
        )
        custom_role.permissions.remove(perm)
        self.colleague.user_permissions.remove(perm)

        admin = User.objects.create_superuser(
            username="rm-admin",
            email="rm-admin@example.test",
            password="test-password",
            company=self.company,
            country="US",
        )
        client = UserAgentClient()
        client.force_login(admin)
        response = client.post(
            f"/roles-update-permissions/{custom_role.pk}/",
            {"permission_id": str(perm.pk), "checked": "true"},
            HTTP_HX_REQUEST="true",
            HTTP_HOST="localhost:8000",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(custom_role.permissions.filter(pk=perm.pk).exists())
        self.assertFalse(self.colleague.user_permissions.filter(pk=perm.pk).exists())
        self.assertTrue(self.colleague.has_perm("leads.view_lead"))

    def test_custom_role_permissions_support_explicit_deny_and_recovery(self):
        custom_role = Role.all_objects.create(
            role_name="Restricted Analyst",
            company=self.company,
        )
        self.actor.role = custom_role
        self.actor.save(update_fields=["role"])
        view_permission = Permission.objects.get(
            content_type__app_label="leads",
            codename="view_lead",
        )
        recovery_permission = Permission.objects.get(
            content_type__app_label="auth",
            codename="change_permission",
        )
        self.actor.user_permissions.add(view_permission, recovery_permission)
        custom_role.denied_permissions.add(view_permission, recovery_permission)

        self.assertFalse(self.actor.has_perm("leads.view_lead"))
        self.assertTrue(self.actor.has_perm("auth.change_permission"))

    def test_role_permission_mutation_requires_write_permission(self):
        custom_role = Role.all_objects.create(
            role_name="View-only role",
            company=self.company,
        )
        view_permission = Permission.objects.get(
            content_type__app_label="auth",
            codename="view_permission",
        )
        self.actor.user_permissions.add(view_permission)
        self.assertFalse(self.actor.is_superuser)
        self.assertFalse(self.actor.has_perm("auth.change_permission"))
        client = UserAgentClient()
        client.force_login(self.actor)

        response = client.post(
            f"/roles-update-permissions/{custom_role.pk}/",
            {"permission_id": str(view_permission.pk), "decision": "allow"},
            HTTP_HX_REQUEST="true",
            HTTP_HOST="localhost:8000",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["permissions"], ["auth.change_permission"])
        self.assertFalse(custom_role.permissions.filter(pk=view_permission.pk).exists())

    def test_role_assignment_endpoint_requires_change_role_permission(self):
        custom_role = Role.all_objects.create(
            role_name="Protected assignment role",
            company=self.company,
        )
        client = UserAgentClient()
        client.force_login(self.actor)

        response = client.post(
            "/add-user-to-roles-view/",
            {"role": custom_role.pk, "users": [self.colleague.pk]},
            HTTP_HX_REQUEST="true",
            HTTP_HOST="localhost:8000",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["permissions"], ["core.change_role"])
        self.colleague.refresh_from_db()
        self.assertIsNone(self.colleague.role_id)

    def test_role_data_scope_endpoint_validates_role_and_supported_scope(self):
        custom_role = Role.all_objects.create(
            role_name="Scope editor role",
            company=self.company,
        )
        admin = User.objects.create_superuser(
            username="scope-admin",
            email="scope-admin@example.test",
            password="Test-only-RoleScope-Password-987!",
            company=self.company,
            country="US",
        )
        client = UserAgentClient()
        client.force_login(admin)

        valid_response = client.post(
            f"/roles-update-data-scope/{custom_role.pk}/",
            {
                "app_label": "core",
                "model_name": "role",
                "scope": RoleDataScope.COMPANY,
            },
            HTTP_HX_REQUEST="true",
            HTTP_HOST="localhost:8000",
        )
        invalid_response = client.post(
            f"/roles-update-data-scope/{custom_role.pk}/",
            {
                "app_label": "core",
                "model_name": "role",
                "scope": RoleDataScope.OWNED,
            },
            HTTP_HX_REQUEST="true",
            HTTP_HOST="localhost:8000",
        )

        self.assertEqual(valid_response.status_code, 200)
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(
            RoleDataScope.all_objects.get(
                role=custom_role,
                content_type=ContentType.objects.get_for_model(Role),
            ).scope,
            RoleDataScope.COMPANY,
        )

        super_admin_role = Role.all_objects.create(
            role_name="Super Admin",
            system_key="SUPER_ADMIN",
            company=self.company,
        )
        protected_response = client.post(
            f"/roles-update-data-scope/{super_admin_role.pk}/",
            {
                "app_label": "core",
                "model_name": "role",
                "scope": RoleDataScope.COMPANY,
            },
            HTTP_HX_REQUEST="true",
            HTTP_HOST="localhost:8000",
        )
        self.assertEqual(protected_response.status_code, 400)

    def test_role_manager_page_renders_permission_decisions_and_custom_scopes(self):
        custom_role = Role.all_objects.create(
            role_name="Role page analyst",
            company=self.company,
        )
        admin = User.objects.create_superuser(
            username="role-page-admin",
            email="role-page-admin@example.test",
            password="Test-only-RolePage-Password-987!",
            company=self.company,
            country="US",
        )
        admin.role = custom_role
        admin.save(update_fields=["role"])
        client = UserAgentClient()
        client.force_login(admin)

        response = client.get(
            f"/roles-permissions/{custom_role.pk}/",
            HTTP_HX_REQUEST="true",
            HTTP_HOST="localhost:8000",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Default")
        self.assertContains(response, "Allow")
        self.assertContains(response, "Deny")
        self.assertContains(response, "No records")
        self.assertContains(response, "roles-update-data-scope/")
        self.assertContains(
            response,
            "Django superuser members bypass role permissions",
        )

    def test_custom_role_data_scope_defaults_to_deny_and_company_scope_is_tenant_bound(self):
        custom_role = Role.all_objects.create(
            role_name="Scoped Analyst",
            company=self.company,
        )
        self.actor.role = custom_role
        self.actor.save(update_fields=["role"])
        model_type = ContentType.objects.get_for_model(User)
        self.assertFalse(
            scope_queryset_to_company(
                User.objects.all(), self.actor
            ).exists()
        )

        RoleDataScope.all_objects.create(
            role=custom_role,
            content_type=model_type,
            scope=RoleDataScope.COMPANY,
        )
        request = SimpleNamespace(
            user=self.actor,
            session={"show_all_companies": True},
            active_company=self.other_company,
        )
        scoped_ids = set(
            scope_queryset_to_company(User.objects.all(), self.actor, request)
            .values_list("pk", flat=True)
        )
        self.assertEqual(scoped_ids, {self.actor.pk, self.colleague.pk})
        self.assertFalse(
            can_access_company_record(self.actor, self.foreign_user, request)
        )

    def test_custom_role_owned_scope_filters_querysets_and_object_access(self):
        custom_role = Role.all_objects.create(
            role_name="Owner Analyst",
            company=self.company,
        )
        self.actor.role = custom_role
        self.actor.save(update_fields=["role"])
        actor_department = Department.objects.create(
            department_name="Actor department",
            company=self.company,
            created_by=self.actor,
        )
        colleague_department = Department.objects.create(
            department_name="Colleague department",
            company=self.company,
            created_by=self.colleague,
        )
        RoleDataScope.all_objects.create(
            role=custom_role,
            content_type=ContentType.objects.get_for_model(Department),
            scope=RoleDataScope.OWNED,
        )

        with patch.object(Department, "OWNER_FIELDS", ["created_by"], create=True):
            queryset = scope_queryset_to_company(
                Department.objects.all(), self.actor
            )
            returned_ids = set(queryset.values_list("pk", flat=True))
            own_access = can_access_company_record(self.actor, actor_department)
            colleague_access = can_access_company_record(
                self.actor, colleague_department
            )

        self.assertEqual(returned_ids, {actor_department.pk})
        self.assertTrue(own_access)
        self.assertFalse(colleague_access)

    def test_fixed_sales_role_permission_ceilings_remain_in_order(self):
        parent = None
        roles = []
        for system_key, role_name in Role.SALES_ROLE_CHOICES:
            role = Role.all_objects.create(
                role_name=role_name,
                system_key=system_key,
                parent_role=parent,
                company=self.company,
            )
            roles.append(role)
            parent = role

        view_permission = Permission.objects.get(
            content_type__app_label="leads",
            codename="view_lead",
        )
        add_permission = Permission.objects.get(
            content_type__app_label="leads",
            codename="add_lead",
        )
        change_permission = Permission.objects.get(
            content_type__app_label="leads",
            codename="change_lead",
        )
        delete_permission = Permission.objects.get(
            content_type__app_label="leads",
            codename="delete_lead",
        )
        other_module_add = Permission.objects.get(
            content_type__app_label="accounts",
            codename="add_account",
        )
        self.actor.user_permissions.add(
            view_permission,
            add_permission,
            change_permission,
            delete_permission,
            other_module_add,
        )

        for role in roles:
            self.actor.role = role
            self.actor.save(update_fields=["role"])
            if role.system_key == "SUPER_ADMIN":
                self.assertTrue(self.actor.has_perm("leads.delete_lead"))
                self.assertTrue(self.actor.has_perm("accounts.add_account"))
                continue
            self.assertTrue(self.actor.has_perm("leads.view_lead"))
            self.assertTrue(self.actor.has_perm("leads.add_lead"))
            self.assertFalse(self.actor.has_perm("leads.delete_lead"))
            self.assertFalse(self.actor.has_perm("accounts.add_account"))
            self.assertEqual(
                self.actor.has_perm("leads.change_lead"),
                role.system_key in {"RSM", "SSM", "ASM", "BDO"},
            )

        self.actor.role = roles[2]
        self.actor.save(update_fields=["role"])
        roles[2].denied_permissions.add(view_permission)
        self.assertFalse(self.actor.has_perm("leads.view_lead"))

        self.actor.user_permissions.remove(add_permission)
        roles[2].permissions.add(add_permission)
        roles[2].denied_permissions.remove(view_permission)
        self.assertTrue(self.actor.has_perm("leads.add_lead"))

        head_role = roles[1]
        head_role.parent_role = None
        with self.assertRaises(ValidationError):
            head_role.save()
        with self.assertRaises(ValidationError):
            Role.all_objects.filter(pk=head_role.pk).update(parent_role=None)
        with self.assertRaises(ValidationError):
            Role.all_objects.filter(pk=head_role.pk).delete()

    def test_explicit_role_grants_and_denials_apply_to_all_six_builtin_roles(self):
        parent = None
        roles = []
        for system_key, role_name in Role.SALES_ROLE_CHOICES:
            role = Role.all_objects.create(
                role_name=role_name,
                system_key=system_key,
                parent_role=parent,
                company=self.company,
            )
            roles.append(role)
            parent = role

        permission = Permission.objects.get(
            content_type__app_label="leads",
            codename="delete_lead",
        )
        for role in roles:
            self.actor.role = role
            self.actor.save(update_fields=["role"])
            role.denied_permissions.add(permission)
            self.assertFalse(self.actor.has_perm("leads.delete_lead"))

            role.denied_permissions.remove(permission)
            role.permissions.add(permission)
            self.assertTrue(self.actor.has_perm("leads.delete_lead"))

    def test_builtin_role_grants_cannot_expand_protected_admin_or_hierarchy_access(self):
        parent = Role.all_objects.create(
            role_name="Super Admin",
            system_key="SUPER_ADMIN",
            company=self.company,
        )
        head_role = Role.all_objects.create(
            role_name="Head of Sales",
            system_key="HEAD_OF_SALES",
            parent_role=parent,
            company=self.company,
        )
        self.actor.role = head_role
        self.actor.save(update_fields=["role"])

        protected_permissions = Permission.objects.filter(
            content_type__app_label="auth",
            codename="change_permission",
        ) | Permission.objects.filter(
            content_type__app_label="core",
            codename="change_salesassignment",
        )
        head_role.permissions.add(*protected_permissions)

        self.assertFalse(self.actor.has_perm("auth.change_permission"))
        self.assertFalse(self.actor.has_perm("core.change_salesassignment"))

        custom_role = Role.all_objects.create(
            role_name="Protected custom role",
            company=self.company,
        )
        self.actor.role = custom_role
        self.actor.save(update_fields=["role"])
        custom_role.permissions.add(*protected_permissions)

        self.assertFalse(self.actor.has_perm("auth.change_permission"))
        self.assertFalse(self.actor.has_perm("core.change_salesassignment"))

    def test_role_manager_rejects_builtin_allow_blocked_by_role_policy(self):
        parent = Role.all_objects.create(
            role_name="Super Admin",
            system_key="SUPER_ADMIN",
            company=self.company,
        )
        head_role = Role.all_objects.create(
            role_name="Head of Sales",
            system_key="HEAD_OF_SALES",
            parent_role=parent,
            company=self.company,
        )
        admin = User.objects.create_superuser(
            username="policy-admin",
            email="policy-admin@example.test",
            password="Test-only-Policy-Password-987!",
            company=self.company,
            country="US",
        )
        permission = Permission.objects.get(
            content_type__app_label="auth",
            codename="change_permission",
        )
        client = UserAgentClient()
        client.force_login(admin)

        response = client.post(
            f"/roles-update-permissions/{head_role.pk}/",
            {"permission_id": str(permission.pk), "decision": "allow"},
            HTTP_HX_REQUEST="true",
            HTTP_HOST="localhost:8000",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(head_role.permissions.filter(pk=permission.pk).exists())

    def test_role_permission_changes_are_visible_to_other_loaded_users(self):
        role = Role.all_objects.create(
            role_name="Live permission role",
            company=self.company,
        )
        member = User.objects.create_user(
            username="live-permission-member",
            password="Test-only-Live-Permission-Password-987!",
            company=self.company,
            country="US",
            role=role,
        )
        permission = Permission.objects.get(
            content_type__app_label="leads",
            codename="view_lead",
        )

        self.assertFalse(member.has_perm("leads.view_lead"))
        role.permissions.add(permission)
        self.assertTrue(member.has_perm("leads.view_lead"))

        role.denied_permissions.add(permission)
        self.assertFalse(member.has_perm("leads.view_lead"))
        role.denied_permissions.remove(permission)
        role.permissions.remove(permission)
        self.assertFalse(member.has_perm("leads.view_lead"))

    def test_assigned_custom_role_cannot_be_deleted(self):
        role = Role.all_objects.create(
            role_name="Assigned role",
            company=self.company,
        )
        self.actor.role = role
        self.actor.save(update_fields=["role"])

        with self.assertRaises(ValidationError):
            role.delete()
        with self.assertRaises(ProtectedError):
            Role.all_objects.filter(pk=role.pk).delete()
