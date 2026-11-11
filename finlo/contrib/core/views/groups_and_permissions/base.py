"""
Views and utilities for managing groups and permissions in Finlo.
"""

# Standard library imports
from functools import cached_property
from urllib.parse import urlencode

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Paginator

# First party imports (Finlo)
from finlo.apps import apps
from finlo.auth.models import User
from finlo.contrib.generics.views import FinloListView, FinloTabView
from finlo.contrib.core.sales_authorization import (
    ROLE_RECOVERY_PERMISSIONS,
    role_permission_grant_allowed,
)
from finlo.registry.permission_registry import is_permission_exempt
from finlo.shortcuts import get_object_or_404, redirect, render
from finlo.urls import reverse_lazy
from finlo.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from finlo.utils.html import escapejs
from finlo.utils.translation import gettext_lazy as _
from finlo.views.generic import TemplateView, View
from finlo.web import HttpResponse, JsonResponse, ScriptResponse

from ...models import FieldPermission, FinloContentType, Role, RoleDataScope

# Local imports
from .permission_utils import PermissionUtils


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class ModelFieldsModalView(LoginRequiredMixin, TemplateView):
    """
    View to display model fields in a modal for field-level permissions
    Supports both role-based and user-based contexts
    """

    template_name = "permissions/field_permissions_modal.html"

    def get(self, request, app_label, model_name, *args, **kwargs):
        """Load field permissions modal for role or user context; support bulk selected users."""
        role_id = kwargs.get("role_id")
        user_id = kwargs.get("user_id")
        context_type = request.GET.get("context", "role")

        selected_user_ids = None
        selected_users_count = 0
        if context_type == "bulk":
            user_ids_str = request.GET.get("selected_user_ids", "")
            if user_ids_str:
                try:
                    selected_user_ids = [
                        int(uid.strip())
                        for uid in user_ids_str.split(",")
                        if uid.strip()
                    ]
                    selected_users_count = len(selected_user_ids)
                except (ValueError, AttributeError):
                    selected_user_ids = None

        role = None
        user = None

        if role_id:
            try:
                role = get_object_or_404(Role, id=role_id)
            except Exception:
                messages.error(request, _("Role does not exist"))
                return ScriptResponse(reload=True)

        if user_id:
            try:
                user = get_object_or_404(User, id=user_id)
            except Exception:
                messages.error(request, _("User does not exist"))
                return ScriptResponse(reload=True)

        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            messages.error(request, _("Model not found"))
            return HttpResponse("")

        if not model._meta.managed:
            messages.info(
                request, _("Field-level permissions are not available for this model.")
            )
            return ScriptResponse(close=True, reload=True, msgs=True)

        content_type = FinloContentType.objects.get_for_model(model)

        existing_permissions = {}
        role_inherited_permissions = {}

        if role:
            field_perms = FieldPermission.objects.filter(
                role=role, content_type=content_type
            )
            for perm in field_perms:
                existing_permissions[perm.field_name] = perm.permission_type

        elif user:
            user_field_perms = FieldPermission.objects.filter(
                user=user, content_type=content_type
            )
            for perm in user_field_perms:
                existing_permissions[perm.field_name] = perm.permission_type

            if hasattr(user, "role") and user.role:
                role_field_perms = FieldPermission.objects.filter(
                    role=user.role, content_type=content_type
                )
                for perm in role_field_perms:
                    role_inherited_permissions[perm.field_name] = perm.permission_type
                    if perm.field_name not in existing_permissions:
                        existing_permissions[perm.field_name] = perm.permission_type

        excluded_fields = getattr(model, "field_permissions_exclude", None)
        if not isinstance(excluded_fields, (list, tuple, set)):
            excluded_fields = set()
        else:
            excluded_fields = set(excluded_fields)

        globally_excluded_fields = {"id", "pk"}
        excluded_fields.update(globally_excluded_fields)

        model_defaults = getattr(model, "default_field_permissions", {})

        fields = []

        for field in model._meta.get_fields():
            if field.many_to_many or field.one_to_many or field.one_to_one:
                continue

            field_name = field.name

            if field_name in excluded_fields:
                continue

            verbose_name = (
                getattr(field, "verbose_name", None)
                or field_name.replace("_", " ").title()
            )

            if field_name in existing_permissions:
                current_permission = existing_permissions[field_name]
            elif field_name in model_defaults:
                current_permission = model_defaults[field_name]
            else:
                current_permission = "readwrite"

            # Check if field is mandatory (required)
            is_mandatory = False
            try:
                # Field is mandatory if it doesn't allow null and doesn't allow blank
                is_mandatory = not field.null and not field.blank
            except AttributeError:
                # Some field types might not have null/blank attributes
                pass

            # current_permission = existing_permissions.get(field_name, "readwrite")

            fields.append(
                {
                    "name": field_name,
                    "verbose_name": verbose_name,
                    "field_type": field.__class__.__name__,
                    "current_permission": current_permission,
                    "is_mandatory": is_mandatory,
                }
            )

        context = {
            "role": role,
            "user": user,
            "model": model,
            "model_name": model_name,
            "app_label": app_label,
            "verbose_name": model._meta.verbose_name,
            "fields": fields,
            "context_type": context_type,
            "role_id": role_id,
            "user_id": user_id,
            "is_bulk": context_type == "bulk",
            "selected_user_ids": (
                ",".join(map(str, selected_user_ids)) if selected_user_ids else ""
            ),
            "selected_users_count": selected_users_count,
        }

        return render(request, self.template_name, context)


@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class RolePermissionView(LoginRequiredMixin, TemplateView):
    """
    View to display role and permission management interface
    """

    template_name = "permissions/group_perm_view.html"


@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class RolePermissionTabView(LoginRequiredMixin, FinloTabView):
    """
    Tab view for permission
    """

    view_id = "group-permission-view"
    background_class = "bg-primary-100 rounded-md"

    @cached_property
    def tabs(self):
        """Define tabs for groups and permissions."""
        from finlo.contrib.core.sales_authorization import (
            is_super_admin_or_superuser,
        )

        if is_super_admin_or_superuser(self.request.user) or self.request.user.has_perm(
            "core.view_company"
        ):
            return [
                {
                    "title": _("Roles"),
                    "url": reverse_lazy("core:role_tab"),
                    "target": "group-view-content",
                    "id": "group-detail-view",
                },
                {
                    "title": _("Permissions"),
                    "url": reverse_lazy("core:permission_tab"),
                    "target": "permission-view-content",
                    "id": "permission-detail-view",
                },
                {
                    "title": _("Super Users"),
                    "url": reverse_lazy("core:super_user_tab"),
                    "target": "super-user-view-content",
                    "id": "super-user-detail-view",
                },
            ]
        return []


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class GroupTab(LoginRequiredMixin, TemplateView):
    """
    Tab view for groups
    """

    template_name = "permissions/group.html"

    def get_context_data(self, **kwargs):
        """Add roles and all_models (permission data) to context."""
        context = super().get_context_data(**kwargs)
        context["roles"] = Role.objects.all().order_by("role_name")
        context["all_models"] = PermissionUtils.get_all_models_data()
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class RolePermissionsView(LoginRequiredMixin, TemplateView):
    """
    View to display and manage permissions for a specific role
    """

    template_name = "permissions/group_role_detail.html"

    def get(self, request, *args, **kwargs):
        """Validate role_id and return reload script on error; otherwise delegate to parent."""
        role_id = kwargs.get("role_id")
        try:
            _role = get_object_or_404(Role, id=role_id)
        except Exception:
            messages.error(request, _("Role does not exist"))
            return HttpResponse(
                "<div id=\"followup-contents\"><script>$('#reloadButton').click();</script></div>"
            )

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add role and all_models (permission data for role) to context."""
        context = super().get_context_data(**kwargs)
        role_id = self.kwargs.get("role_id")

        role = get_object_or_404(Role, id=role_id)

        context["role"] = role
        context["role_id"] = role_id
        context["role_has_superuser_members"] = role.users.filter(
            is_superuser=True
        ).exists()
        all_models = PermissionUtils.get_all_models_data(role=role)
        configured_scopes = {
            (scope.content_type.app_label, scope.content_type.model): scope.scope
            for scope in RoleDataScope.all_objects.filter(role=role, is_active=True)
            .select_related("content_type")
        }
        for model in all_models:
            model["data_scope"] = configured_scopes.get(
                (model["app_label"], model["model_name"].lower()),
                RoleDataScope.DENY_ALL,
            )
            model_class = apps.get_model(
                model["app_label"], model["model_name"]
            )
            scope_labels = dict(RoleDataScope.SCOPE_CHOICES)
            scope_choices = [
                (RoleDataScope.DENY_ALL, scope_labels[RoleDataScope.DENY_ALL])
            ]
            if getattr(model_class, "OWNER_FIELDS", ()):
                scope_choices.append(
                    (RoleDataScope.OWNED, scope_labels[RoleDataScope.OWNED])
                )
                scope_choices.append(
                    (RoleDataScope.ASSIGNED, scope_labels[RoleDataScope.ASSIGNED])
                )
            elif callable(getattr(model_class, "granted_access_filter", None)):
                scope_choices.append(
                    (RoleDataScope.ASSIGNED, scope_labels[RoleDataScope.ASSIGNED])
                )
            try:
                model_class._meta.get_field("company")
            except FieldDoesNotExist:
                pass
            else:
                scope_choices.append(
                    (RoleDataScope.COMPANY, scope_labels[RoleDataScope.COMPANY])
                )
            model["data_scope_choices"] = scope_choices
        context["all_models"] = all_models

        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class RoleMembersView(LoginRequiredMixin, TemplateView):
    """View to display members of a specific role"""

    template_name = "permissions/role_members.html"

    def get(self, request, *args, **kwargs):
        """Validate role_id and return reload script on error; otherwise delegate to parent."""
        role_id = kwargs.get("role_id")
        try:
            _role = get_object_or_404(Role, id=role_id)
        except Exception:
            messages.error(request, _("Role does not exist"))
            return ScriptResponse(reload=True)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add role, members list view context, and column/action config to context."""
        context = super().get_context_data(**kwargs)
        role_id = self.kwargs.get("role_id")
        role = get_object_or_404(Role, id=role_id)

        columns = [
            ("Employee", "get_avatar_with_name"),
            ("Email", "email"),
        ]

        confirm_msg = escapejs(
            _("Are you sure you want to delete the user from this role?")
        )
        actions = [
            {
                "action": "Delete",
                "src": "assets/icons/a4.svg",
                "img_class": "w-4 h-4",
                "attrs": f"""
                    hx-post="{{get_delete_user_from_role}}"
                    hx-target="#deleteModeBox"
                    hx-swap="innerHTML"
                    hx-trigger="confirmed"
                    hx-on:click="hxConfirm(this,'{confirm_msg}')"
                    hx-on::after-request="$('#reloadMessagesButton').click();"
                """,
            }
        ]

        list_view = FinloListView(
            model=User,
            view_id=f"role-members-{role_id}",
            search_url=reverse_lazy(
                "core:role_members_view", kwargs={"role_id": role_id}
            ),
            main_url=reverse_lazy(
                "core:role_members_view", kwargs={"role_id": role_id}
            ),
            columns=columns,
            table_width=False,
            table_height_as_class="h-[calc(100vh-460px)]",
            bulk_select_option=False,
            bulk_export_option=False,
            bulk_update_option=False,
            bulk_delete_enabled=False,
            list_column_visibility=False,
            enable_sorting=True,
            save_to_list_option=False,
            actions=actions,
        )

        list_view.request = self.request
        list_view.kwargs = self.kwargs
        list_view.get_queryset = lambda: User.objects.filter(role=role).select_related(
            "role"
        )
        list_view.object_list = list_view.get_queryset()

        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        list_view.col_attrs = [
            {
                "get_avatar_with_name": {
                    "hx-get": f"{{get_detail_view_url}}?{query_string}",
                    "hx-target": "#permission-view",
                    "hx-swap": "innerHTML",
                    "hx-push-url": "true",
                    "hx-select": "#users-view",
                    "permission": f"{User._meta.app_label}.view_{User._meta.model_name}",
                }
            }
        ]

        context.update(list_view.get_context_data())
        context["role"] = role
        context["model_verbose_name"] = f"{role.role_name} Role Members"
        context["no_record_msg"] = _(
            f'No members found in the "{role.role_name}" role.'
        )
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class PermissionTab(LoginRequiredMixin, TemplateView):
    """
    Template view for permission tab
    """

    template_name = "permissions/permission.html"

    def get_context_data(self, **kwargs):
        """Add paginated non-superuser users for current company to context."""
        context = super().get_context_data(**kwargs)
        company = (
            getattr(self.request, "active_company", None) or self.request.user.company
        )
        users = User.objects.filter(is_superuser=False, company=company)
        paginator = Paginator(users, 10)
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        context["users"] = page_obj
        context["page_obj"] = page_obj
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("auth.change_permission"),
    name="dispatch",
)
class UpdateRolePermissionsView(LoginRequiredMixin, View):
    """
    Toggle permission for a role and its members when checkbox is clicked.
    """

    def post(self, request, role_id):
        """Toggle permission for a specific role."""
        role = get_object_or_404(Role, id=role_id)
        perm_id = request.POST.get("permission_id")
        decision = request.POST.get("decision")
        if decision is None:
            decision = (
                "allow" if request.POST.get("checked") == "true" else "deny"
            )
        if decision not in {"allow", "deny", "inherit"}:
            return JsonResponse(
                {"success": False, "message": "Invalid permission decision"},
                status=400,
            )

        try:
            permission = Permission.objects.select_related("content_type").get(
                id=perm_id
            )
        except Permission.DoesNotExist:
            return JsonResponse({"success": False, "message": "Permission not found"})

        permission_key = (
            f"{permission.content_type.app_label}.{permission.codename}"
        )
        if decision == "deny" and permission_key in ROLE_RECOVERY_PERMISSIONS:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Recovery permissions cannot be denied",
                },
                status=400,
            )
        if decision == "allow" and not role_permission_grant_allowed(
            role, permission
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": "This role cannot grant the selected permission",
                },
                status=400,
            )
        if decision == "allow":
            role.permissions.add(permission)
            role.denied_permissions.remove(permission)
            messages.success(request, _("Permission added successfully."))
        elif decision == "deny":
            role.permissions.remove(permission)
            role.denied_permissions.add(permission)
            messages.success(request, _("Permission denied for this role."))
        else:
            role.permissions.remove(permission)
            role.denied_permissions.remove(permission)
            messages.success(request, _("Role permission override cleared."))

        return ScriptResponse(msgs=True)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("auth.change_permission"),
    name="dispatch",
)
class UpdateRoleDataScopeView(LoginRequiredMixin, View):
    """Set an explicit, supported data scope for a custom role and model."""

    def post(self, request, role_id):
        role = get_object_or_404(Role, id=role_id)
        if role.system_key:
            return JsonResponse(
                {"success": False, "message": "Built-in role scopes are fixed"},
                status=400,
            )

        app_label = request.POST.get("app_label")
        model_name = request.POST.get("model_name")
        scope = request.POST.get("scope")
        if scope not in {choice[0] for choice in RoleDataScope.SCOPE_CHOICES}:
            return JsonResponse(
                {"success": False, "message": "Invalid data scope"},
                status=400,
            )
        try:
            model = apps.get_model(app_label, model_name)
        except (LookupError, ValueError):
            return JsonResponse(
                {"success": False, "message": "Model not found"}, status=400
            )
        if not model or is_permission_exempt(model):
            return JsonResponse(
                {"success": False, "message": "Model is not configurable"},
                status=400,
            )

        owner_fields = getattr(model, "OWNER_FIELDS", ())
        if scope == RoleDataScope.COMPANY:
            try:
                model._meta.get_field("company")
            except FieldDoesNotExist:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "This model has no company boundary",
                    },
                    status=400,
                )
        elif scope == RoleDataScope.OWNED and not owner_fields:
            return JsonResponse(
                {"success": False, "message": "This model has no owner fields"},
                status=400,
            )
        elif scope == RoleDataScope.ASSIGNED and not (
            owner_fields or callable(getattr(model, "granted_access_filter", None))
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": "This model has no supported assignment filter",
                },
                status=400,
            )

        content_type = ContentType.objects.get_for_model(model)
        role_scope, created = RoleDataScope.all_objects.get_or_create(
            role=role,
            content_type=content_type,
            defaults={
                "scope": scope,
                "is_active": True,
                "created_by": request.user,
                "updated_by": request.user,
            },
        )
        if not created:
            role_scope.scope = scope
            role_scope.is_active = True
            role_scope.updated_by = request.user
            role_scope.save()
        return JsonResponse(
            {
                "success": True,
                "scope": role_scope.scope,
                "message": "Data scope updated",
            }
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class AssignUsersView(LoginRequiredMixin, View):
    """
    Optimized view to handle assigning permissions to users.
    """

    template_name = "permissions/assign_perm_form.html"

    def get(self, request, *args, **kwargs):
        """Render the assign permissions form."""
        context = {
            "all_models": PermissionUtils.get_all_models_data(
                user=None,
            )
        }
        if request.headers.get("HX-Request"):
            return render(request, self.template_name, context)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """Handle assigning permissions to selected users."""
        user_ids = request.POST.getlist("users")
        permission_ids = request.POST.getlist("permissions")

        if not user_ids or not permission_ids:
            errors = {}
            if not user_ids:
                errors["users"] = [_("Please select at least one user.")]
            if not permission_ids:
                errors["permissions"] = [_("Please select at least one permission.")]
            context = {
                "all_models": PermissionUtils.get_all_models_data(),
                "form": {"errors": errors},
            }
            return render(request, self.template_name, context)

        users = User.objects.filter(id__in=user_ids, is_superuser=False)
        permissions = Permission.objects.filter(id__in=permission_ids)

        try:
            for user in users:
                user.user_permissions.add(*permissions)

            messages.success(
                request,
                _(
                    "Successfully assigned {permissions_count} permission(s) to {users_count} user(s)."
                ).format(
                    permissions_count=permissions.count(),
                    users_count=users.count(),
                ),
            )

            if request.headers.get("HX-Request"):
                return HttpResponse(
                    "<script>closeContentModal(); location.reload();</script>"
                )
            return redirect("core:permission_tab")

        except Exception as e:
            messages.error(
                request, _("Error assigning permissions: {error}").format(error=str(e))
            )
            return self.get(request, *args, **kwargs)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["auth.change_permission", "auth.change_group"]
    ),
    name="dispatch",
)
class UpdateRoleModelPermissionsView(LoginRequiredMixin, View):
    """
    Toggle all permissions for a specific model for a role when select all checkbox is clicked.
    """

    def post(self, request, role_id):
        """Toggle all permissions for a specific model for a role."""
        try:
            role = get_object_or_404(Role, id=role_id)
        except Exception:
            messages.error(self.request, _("Role Does not Exist"))
            return ScriptResponse(reload=True)

        model_name = request.POST.get("model_name")
        app_label = request.POST.get("app_label")
        checked = request.POST.get("checked") == "true"

        if not model_name or not app_label:
            return JsonResponse(
                {"success": False, "message": "Model information not provided"}
            )

        try:
            permissions = PermissionUtils.get_model_permissions(app_label, model_name)
            if not permissions:
                return JsonResponse(
                    {"success": False, "message": "No permissions found for this model"}
                )

            permission_objects = Permission.objects.filter(
                id__in=[p["id"] for p in permissions]
            ).select_related("content_type")
            grantable_permissions = [
                permission
                for permission in permission_objects
                if role_permission_grant_allowed(role, permission)
            ]
            if not checked:
                permission_objects = [
                    permission
                    for permission in permission_objects
                    if f"{permission.content_type.app_label}.{permission.codename}"
                    not in ROLE_RECOVERY_PERMISSIONS
                ]
            if checked:
                if not grantable_permissions:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "No permissions for this model can be granted by this role",
                        },
                        status=400,
                    )
                role.permissions.add(*grantable_permissions)
                role.denied_permissions.remove(*grantable_permissions)
                messages.success(
                    request,
                    f"Granted {len(grantable_permissions)} configurable permission(s) for {model_name}.",
                )
            else:
                role.permissions.remove(*permission_objects)
                role.denied_permissions.add(*permission_objects)
                messages.success(request, f"All permissions denied for {model_name}.")

            return ScriptResponse(msgs=True)

        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"Error updating permissions: {str(e)}"}
            )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["auth.change_permission", "auth.change_group"]
    ),
    name="dispatch",
)
class UpdateRoleAllPermissionsView(LoginRequiredMixin, View):
    """
    Toggle ALL permissions for a role when master select all checkbox is clicked.
    """

    def post(self, request, role_id):
        """Toggle ALL permissions for a role."""
        try:
            role = get_object_or_404(Role, id=role_id)
        except Exception:
            messages.error(self.request, _("Role Does not Exist"))
            return ScriptResponse(reload=True)
        checked = request.POST.get("checked") == "true"

        try:
            all_permissions = []
            for model in apps.get_models():
                model_name = model.__name__
                if is_permission_exempt(model):
                    continue
                permissions = PermissionUtils.get_model_permissions(
                    model._meta.app_label, model_name
                )
                all_permissions.extend(
                    Permission.objects.filter(
                        id__in=[p["id"] for p in permissions]
                    ).select_related("content_type")
                )

            if not all_permissions:
                return JsonResponse(
                    {"success": False, "message": "No permissions found"}
                )

            grantable_permissions = [
                permission
                for permission in all_permissions
                if role_permission_grant_allowed(role, permission)
            ]
            if not checked:
                all_permissions = [
                    permission
                    for permission in all_permissions
                    if f"{permission.content_type.app_label}.{permission.codename}"
                    not in ROLE_RECOVERY_PERMISSIONS
                ]
            if checked:
                role.permissions.add(*grantable_permissions)
                role.denied_permissions.remove(*grantable_permissions)
                messages.success(
                    request,
                    f"Granted {len(grantable_permissions)} configurable permission(s) to {role.role_name}.",
                )
            else:
                role.permissions.remove(*all_permissions)
                role.denied_permissions.add(*all_permissions)
                messages.success(
                    request, f"All permissions denied to {role.role_name} role."
                )

            return ScriptResponse(msgs=True)

        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"Error updating permissions: {str(e)}"}
            )
