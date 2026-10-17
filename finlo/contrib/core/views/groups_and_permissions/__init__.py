"""
This module contains views related to groups and permissions in the Finlo Core application.
"""

from finlo.contrib.core.views.groups_and_permissions.base import (
    ModelFieldsModalView,
    RolePermissionView,
    RolePermissionTabView,
    GroupTab,
    RolePermissionsView,
    RoleMembersView,
    PermissionTab,
    UpdateRolePermissionsView,
    AssignUsersView,
    UpdateRoleModelPermissionsView,
    UpdateRoleAllPermissionsView,
)
from finlo.contrib.core.views.groups_and_permissions.permission_utils import (
    PermissionUtils,
)
from finlo.contrib.core.views.groups_and_permissions.search import (
    SearchRoleModelsView,
    SearchUserModelsView,
    SearchAssignModelsView,
    LoadUserPermissionsView,
    LoadMoreUsersView,
)
from finlo.contrib.core.views.groups_and_permissions.super_user_tab import (
    SuperUserView,
    SuperUserNavbar,
    SuperUserTab,
    AddSuperUsersView,
    ToggleSuperuserView,
)
from finlo.contrib.core.views.groups_and_permissions.field_permission_actions import (
    SaveBulkFieldPermissionsView,
    UpdateFieldPermissionView,
    SaveAllFieldPermissionsView,
)
from finlo.contrib.core.views.groups_and_permissions.user_permissions_actions import (
    UpdateUserPermissionsView,
    UpdateUserModelPermissionsView,
    UpdateUserAllPermissionsView,
    BulkUpdateUserModelPermissionsView,
    BulkUpdateUserAllPermissionsView,
)

__all__ = [
    "ModelFieldsModalView",
    "RolePermissionView",
    "RolePermissionTabView",
    "GroupTab",
    "RolePermissionsView",
    "RoleMembersView",
    "PermissionTab",
    "UpdateRolePermissionsView",
    "AssignUsersView",
    "UpdateRoleModelPermissionsView",
    "UpdateRoleAllPermissionsView",
    "PermissionUtils",
    "SearchRoleModelsView",
    "SearchUserModelsView",
    "SearchAssignModelsView",
    "LoadUserPermissionsView",
    "LoadMoreUsersView",
    "SuperUserView",
    "SuperUserNavbar",
    "SuperUserTab",
    "AddSuperUsersView",
    "ToggleSuperuserView",
    "SaveBulkFieldPermissionsView",
    "UpdateFieldPermissionView",
    "SaveAllFieldPermissionsView",
    "UpdateUserPermissionsView",
    "UpdateUserModelPermissionsView",
    "UpdateUserAllPermissionsView",
    "BulkUpdateUserModelPermissionsView",
    "BulkUpdateUserAllPermissionsView",
]
