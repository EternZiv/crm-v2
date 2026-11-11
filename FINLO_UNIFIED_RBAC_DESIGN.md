# FINLONEXA CRM v2 — Unified RBAC Design

Date: 2026-11-11
Status: Local implementation and pre-migration readiness review complete; production migration is blocked pending approval gates. Migration 0014 is unapplied to the configured PostgreSQL database.

> The architecture and risk sections below include historical pre-implementation findings. Current verification, browser evidence, data dry-run, rollback results, and remaining approval gates are in [FINLO_UNIFIED_RBAC_PRE_MIGRATION_READINESS.md](./FINLO_UNIFIED_RBAC_PRE_MIGRATION_READINESS.md).

## Decision summary

Keep `finlo.contrib.core.models.organization.Role` as the sole role identity. It already represents both the six fixed sales roles and company-associated configurable roles. Do not introduce a second role model.

The existing model is not sufficient for the full requested behavior without structural changes:

1. The permission evaluator has hard-coded feature/action ceilings for the six sales keys, so editing `Role.permissions` cannot reliably configure built-in feature access.
2. Custom roles have no explicit record-scope policy. The existing company boundary applies only to models with a `company` field; custom roles receive no additional sales-hierarchy restriction.
3. There is no durable role-level explicit-deny representation, and role permissions are copied into user permissions, obscuring grant provenance.
4. `User.role` uses `on_delete=CASCADE`, so deleting a role can delete its assigned users.

The requested implementation therefore requires authorization and database changes. Following approval to implement in application code and isolated tests, those changes are present in the worktree and migration 0014 was generated. It has not been applied to the configured PostgreSQL database, and no production records, roles, permissions, or schema were changed. See the implementation status and pre-migration readiness report for current evidence and remaining decisions.

## Phase 1 baseline

Command:

```powershell
C:\Users\izhar\Desktop\crm-v2\.venv\Scripts\python.exe manage.py test finlo.contrib.core.test_authorization --settings=finlo.settings.security_test
```

Result: **18 tests run, 18 passed, 0 failed, 0 blocked.** Django reported no system-check issues. It emitted a warning that the local `staticfiles` directory is absent; the test suite still completed successfully.

The test uses the existing `UserAgentClient` fixture to provide `HTTP_USER_AGENT`. The test-fixture change and the Super Admin regression test were already present in the worktree before this Phase 1 design. No application authorization code was changed for this phase.

## Current architecture and evidence

### Role and membership data

- [`Role`](./finlo/contrib/core/models/organization.py) stores `role_name`, nullable `system_key`, nullable `parent_role`, `description`, and a many-to-many relation to Django `Permission`.
- Through [`FinloCoreModel`](./finlo/contrib/core/models/base.py), a role also has `company`, `is_active`, `additional_info`, and audit-history fields.
- The six sales keys are `SUPER_ADMIN`, `HEAD_OF_SALES`, `RSM`, `SSM`, `ASM`, and `BDO`. A conditional uniqueness constraint prevents duplicate non-null keys per company.
- `Role.clean()` validates the fixed built-in parent chain and rejects cycles, but normal model `save()` does not itself call `full_clean()`. The role serializer exposes all model fields while marking `system_key` read-only; `parent_role` remains an API field.
- `Role.delete()` rejects deletion when `system_key` is set. Separately, [`FinloUser.role`](./finlo/contrib/core/models/user.py) has `on_delete=CASCADE`; a custom role deletion can therefore cascade to users unless the deletion path is protected. A queryset-level deletion can also bypass an instance `delete()` override.
- No explicit custom-role data-scope field or role-permission denial relation exists in the inspected model/migration path. The current schema already includes a generic `additional_info` JSON field, but using it as authorization policy storage would avoid typed constraints and validation; it is not recommended as the authoritative scope store.

### Current permission precedence and duplication

- [`has_effective_permission()`](./finlo/contrib/core/sales_authorization.py) applies the hard-coded `sales_role_permission_decision()` for the six fixed sales keys. Its decision can deny a permission even when Django grants it. Superusers and `SUPER_ADMIN` receive the current global permission bypass. Other roles fall through to `user.has_perm()`.
- [`Role.permissions`](./finlo/contrib/core/models/organization.py) is not consistently evaluated live. [`AddUsersToRoleForm.save()`](./finlo/contrib/core/forms/permission.py), role permission update views, and [`sync_role_permissions_on_role_change`](./finlo/contrib/core/signals.py) copy role permissions into `User.user_permissions`. The database does not record whether an overlapping user permission originated from a role, a group, or an administrator.
- The [`permission_required` decorators](./finlo/utils/decorators/wrapper.py), API permission classes and queryset mixins use `has_effective_permission()`. Template permission tags and some action/menu rendering paths use `user.has_perm()` directly, with separate Super Admin exceptions. These paths must converge on the same permission result without removing independent object-scope checks.
- The role hierarchy screen in [`views/roles.py`](./finlo/contrib/core/views/roles.py) and the Role/Permissions tab under [`views/groups_and_permissions/base.py`](./finlo/contrib/core/views/groups_and_permissions/base.py) are separate management surfaces. Permission mutations currently accept any one of `auth.view_permission`, `auth.view_group`, `auth.change_permission`, or `auth.change_group` because the decorator uses its default `require_all=False`; read and write authority should be separated.
- The role permission update view mutates both `Role.permissions` and member `user_permissions`. The role permission template invokes it through HTMX. It is not marked `htmx_required`, unlike adjacent role permission endpoints.
- The Add User to Role form is gated by the generic user-add permission through its form view, but [`AddUsersToRoleForm`](./finlo/contrib/core/forms/permission.py) only checks for duplicate membership before saving. It does not apply the role-assignment restrictions in [`forms/users.py`](./finlo/contrib/core/forms/users.py) or reject `SUPER_ADMIN`. An actor who can use this form may assign an available built-in privileged role unless the role/user queryset or an outer policy prevents it.

### Scope and Super Admin

- [`get_company_scope()` and `scope_queryset_to_company()`](./finlo/contrib/core/authorization.py) establish company scope independently from feature permission. The current Super Admin/superuser exception is cross-company; users with an eligible company-switch permission may select an active company through request/session state.
- [`scope_queryset_to_sales_hierarchy()` and `can_access_sales_record()`](./finlo/contrib/core/sales_authorization.py) enforce the existing reporting/ownership boundaries for the fixed sales roles. For a custom role whose `system_key` is null, those helpers return without additional sales-hierarchy filtering.
- Models without a `company` field are not narrowed by `scope_queryset_to_company()`. Consequently, an explicit custom-role scope cannot be inferred merely from the existing company filter.
- The pending worktree includes a Super Admin bypass enhancement and regression test in the permission template tags and permission tabs. The baseline confirms the test for the non-`is_superuser` `SUPER_ADMIN` case passes. These existing changes were not created or modified by this Phase 1 work.

### Cache and UI

- [`FinloViewCache`](./static/assets/js/navigation_history.js) is an in-memory browser cache. Its key includes active user ID, active company scope, and normalized URL; mutation requests clear the current browser's cache. A role change initiated in a different browser/session cannot directly clear that cache, so permission-sensitive cached content needs a policy-version check or server revalidation before it is treated as current.
- Existing view/queryset checks remain the security boundary. Hiding a menu item or button is not a substitute for authorization on its HTMX endpoint, direct URL, API, or object lookup.

## Proposed unified design

### 1. One role identity model

Continue using `Role`; distinguish built-ins by the immutable `system_key`, and custom roles by `system_key IS NULL`. Keep the fixed built-in parent chain and never use a display name to infer role identity. Do not make custom roles children of the built-in sales hierarchy or interpret their `parent_role` as reporting authority.

For built-ins, enforce system-key and parent immutability in every supported write path (model/service, HTML forms, REST serializer, admin and bulk operations). Keep the key out of editable UI/API inputs. Keep the existing per-company uniqueness guarantee. Add a preflight that reports missing built-ins per company; do not silently create, rename, or re-key existing production roles.

### 2. A single permission policy

Extend the existing `has_effective_permission()` contract rather than adding a second evaluator. All decorators, API permission classes, template tags, action/menu checks and module views should use the same evaluator. Preserve public signatures and response behavior where practical.

Recommended order:

1. Reject unauthenticated or inactive users.
2. Enforce protected security invariants, including built-in role identity, assignment restrictions, and role-management privilege checks. These are not configurable feature grants.
3. Apply an explicit role-level denial before ordinary role, user, or group grants.
4. Require a valid feature/action grant from an actual Django `Permission` record; unrecognized or missing grants deny by default.
5. Independently enforce company, reporting, ownership, assignment, and object-level scope. A feature grant never widens these boundaries.
6. Preserve the existing Super Admin recovery/admin exception only for the protected built-in identity; custom roles must never inherit it. Preserve the existing Super Admin company behavior only as an explicit policy exception, not as a permission-matrix toggle.

`Role.permissions` can remain the positive-grant relation. A typed role-denial relation (or equivalent through model) is required if the UI exposes explicit deny. The UI should distinguish “no role override” from “deny”; an unchecked checkbox must not ambiguously erase an independent user/group grant. Denials must be unable to remove protected recovery access.

### 3. Explicit custom-role data scope

Add a typed scope policy keyed by role and supported model/content type, with a uniqueness constraint on the role/model pair. The policy must use a server-owned registry of valid scope handlers rather than user-supplied ORM fields or arbitrary filter expressions.

Candidate scope values, subject to module inventory and product approval:

- `DENY_ALL`: safe default for a new custom role or an unsupported model.
- `OWNED`: only for models with a verified owner-field/access-grant implementation.
- `ASSIGNED`: only where a verified assignment relation exists.
- `COMPANY`: rows within the user's authorized company boundary.

Custom roles cannot select global or cross-company scope. Built-in roles continue to use their existing fixed sales hierarchy and company-scoping rules; do not replace those with custom scope configuration. Scope must be applied to lists, direct-object lookups, exports, APIs, HTMX and background/action paths.

The initial existing-custom-role scope backfill is a business-impacting decision. Before migration, produce a per-role/per-model dry-run showing current grants and proposed scope. Do not infer owner/team/region semantics from a role name. Any unsupported or ambiguous model remains denied until an administrator explicitly selects a supported scope.

### 4. Safe role lifecycle and assignment

- Change the user-to-role deletion behavior so deleting a custom role cannot delete users. Prefer a database `PROTECT` relationship plus explicit reassignment; deletion is allowed only after the role has no members and dependent scope/permission records can be safely removed.
- Deactivate roles using the inherited `is_active` field. Inactive roles cannot authorize members or receive assignments.
- Centralize create/edit/deactivate/delete, permission changes and user assignment in an atomic role-management service. Validate actual permissions server-side, constrain roles and users to the actor's company, and prohibit assigning protected built-ins to an actor who cannot manage privileged roles.
- Show affected members before a destructive or broad permission/scope change, and write an auditable before/after record with actor, company, role, permission/scope, and timestamp. Confirm whether current auditlog M2M tracking is sufficient before relying on it.
- Require dedicated role-management authorization for permission mutations. Read-only permissions must not authorize writes. Keep CSRF and HTMX method restrictions on write endpoints, but do not rely on an HTMX header as the authorization check.

### 5. Migration and compatibility strategy

1. **Preflight only:** inventory each company's six keys, role/user assignments, role and user/group permissions, field permissions, current grants, and custom-role records. Export a reviewed snapshot and report inconsistencies. No live database writes.
2. **Additive schema:** create typed role-scope and role-denial storage; add database protection against deleting assigned roles. Keep existing role IDs, M2M grants, user rows, and built-in keys intact.
3. **Provenance decision:** existing `user_permissions` may contain both direct grants and copies of role grants. There is no reliable provenance field. Do not bulk-remove or reinterpret overlapping grants without an approved migration policy. Preserve old behavior behind a compatibility step until the administrator reviews the dry-run.
4. **Backfill in isolated staging:** seed scope rows only from an approved mapping. New custom roles default to `DENY_ALL`; built-in scope remains in the current helper. Verify no stage changes the six-key parent chain or sales pipeline rules.
5. **Compatibility rollout:** centralize reads/writes first, add regression tests, then progressively route UI/API surfaces through the manager. Keep a feature flag or reversible switch for evaluator cutover if the project convention supports it.
6. **Production deployment:** generate and review migrations; apply only with explicit production authorization. No production migration is part of this phase.

### 6. Rollback

- Before rollout, snapshot role membership, `Role.permissions`, user/group permission links, scope rows and denial rows.
- Roll back the feature flag/evaluator switch first, restoring the prior permission evaluator and role permission mutation paths.
- Keep additive scope/deny rows inert during application rollback. Do not delete role/user data or reverse a `PROTECT` migration while assigned roles remain.
- Reverse schema migrations only after confirming dependent data is backed up and no deployed code uses the new fields/tables.
- Re-run the 18-test baseline plus the new role/scope security tests after rollback.

## Risks requiring approval before implementation

| Severity | Finding | Evidence/status |
|---|---|---|
| HIGH | Role permission grants are copied into user permission records without grant provenance; a naive live-role switch or revocation migration can preserve stale grants or remove independently assigned grants. | Confirmed in `forms/permission.py`, `signals.py`, and `views/groups_and_permissions/base.py`. |
| HIGH | Role permission mutation accepts an OR-list containing view permissions, allowing a read permission to satisfy the mutation gate. | Confirmed in `UpdateRolePermissionsView` and `permission_required_or_denied()` default `require_all=False`. |
| HIGH | The Add User to Role form does not apply the per-user role-assignment validator and can assign any role in its validated choices, including a privileged built-in role if available. | Confirmed in `AddUsersToRoleForm.clean/save`; the form view's generic user permission does not express a protected-role rule. |
| HIGH | Custom roles have no configured record-scope policy; company filtering alone does not cover every model or object. | Confirmed in `authorization.py` and `sales_authorization.py`. |
| HIGH | Deleting a custom role may cascade-delete assigned users due to `FinloUser.role`'s `CASCADE` foreign key. | Confirmed in `models/user.py`; instance deletion guard only protects keyed roles. |
| HIGH | The built-in hierarchy is validated by `Role.clean()` but the key/parent are not universally immutable at the model/API boundary. | Confirmed by `Role.clean()`, generic form fields, and `RoleSerializer`. |
| MEDIUM | Permission results are not routed consistently through the shared evaluator; template/action paths use raw `user.has_perm()` with separate Super Admin handling. | Confirmed by the template tags/action helpers and evaluator references. |
| MEDIUM | Current-browser mutation invalidation does not notify other sessions that a role's permissions changed. | In-memory cache is user/company/URL keyed; external-session changes require revalidation/versioning. |

Specialist reviews completed:

- Backend Architect: confirmed reuse of the existing `Role` model; identified grant-provenance and scope-schema risks.
- Application Security Engineer: independently confirmed read-vs-write gate confusion, role assignment risk, and user-cascade risk.
- Test Automation Engineer: confirmed the baseline consists of 18 tests; recommended focused tests for identity protection, grants/revokes, tenant boundaries, and HTMX mutation behavior. Its default-interpreter attempt lacked Django; the project `.venv` run above is the authoritative successful baseline.

## Implementation status

The user approved implementation in code and isolated tests, with no production database writes. The initial Phase 2 implementation is present but is not production-ready until the legacy permission-provenance decision and deployment migration are reviewed.

- Added the `Role.denied_permissions` relation and `RoleDataScope` model. Custom-role scope defaults to deny; supported scopes are company, owner, or verified assigned access. Custom roles are pinned to the user's own company. Built-in roles continue to use their existing hierarchy.
- Routed `FinloUser.has_perm()` through the shared evaluator. Role denials override user/group grants except for protected recovery permissions; role grants are live and remain bounded by the fixed sales-role permission ceiling.
- Updated the Role Manager controls for explicit Allow / Deny / Default and per-model data scope. Permission mutation and role assignment require write permissions; generic Role API fields for system identity, parent, and permission relations are read-only.
- Prevented built-in role identity/hierarchy mutation through validated model saves and bulk ORM update/delete methods. Role assignment deletion now uses `PROTECT`; assigned custom roles cannot be deleted.
- Removed new copies of role grants into `user_permissions`. Existing user permission rows were intentionally not backfilled, deleted, or reinterpreted because grant provenance is unknown. As a result, legacy copied permissions may remain after role unassignment until an approved reconciliation policy is applied.
- Generated migration `0014_role_denied_permissions_alter_finlouser_role_and_more.py`; it has not been applied to any non-test database.
- No production records, roles, permissions, or schema were changed.

Validation completed:

| Command | Result |
|---|---|
| `C:\Users\izhar\Desktop\crm-v2\.venv\Scripts\python.exe manage.py test finlo.contrib.core.test_authorization --settings=finlo.settings.security_test` | Passed: 31 tests, 0 failures, 0 errors, 0 blocked. The final focused 7-test rerun also passed after the Super Admin UI warning change; see the readiness report for the exact command and browser evidence. |
| `C:\Users\izhar\Desktop\crm-v2\.venv\Scripts\python.exe manage.py check --settings=finlo.settings.security_test` | Passed: no issues. |
| `C:\Users\izhar\Desktop\crm-v2\.venv\Scripts\python.exe manage.py makemigrations core --check --dry-run --settings=finlo.settings.security_test` | Passed: no unrepresented core model changes. |
| `git diff --check` | Passed; Git emitted only line-ending normalization warnings for the dirty worktree. |

Remaining pre-production gates: approve the Django-superuser bypass policy, the legacy direct-grant reconciliation policy, the proposed custom-role scope policy, and a rollback/deployment plan for the loss of denial/scope data on reverse migration. Migration 0014 remains unapplied to the configured PostgreSQL database. The test runner also warns that the local `staticfiles` directory is absent; the Django system check and tests otherwise pass.
