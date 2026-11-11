# FINLO RBAC CONFLICT AUDIT

Date: 2026-11-11
Scope: Read-only audit of hierarchical sales authorization, user management, and conflicting role-management surfaces.

## Executive summary

The canonical RBAC model in this project is explicit and professional: it enforces a fixed six-role hierarchy and uses a permission ceiling to prevent sales-role users from exceeding their intended scope. The main conflict is that the code also contains a generic role manager and multiple role-related screens, which create an alternate configuration plane that is not obviously aligned with the canonical sales hierarchy.

This leaves the platform in a state where the backend enforcement path is relatively disciplined, while the broader administrative UI and role-configuration layer still contains avenue for confusion, duplication, and drift.

## Focused verification result

Executed in the project’s isolated security-test settings:
`C:\Users\izhar\Desktop\crm-v2\.venv\Scripts\python.exe manage.py test finlo.contrib.core.test_authorization --settings=finlo.settings.security_test`

Observed result:
- 18 tests run
- 18 passed
- 0 failed
- 0 blocked

This confirms the fixed hierarchy and permission rules remain intact under the project’s intended validation path after the test fixture was updated to provide a realistic `HTTP_USER_AGENT` header. The earlier KeyError was a harness issue, not evidence of permission bypass.

## Evidence of the canonical hierarchy

### 1) Canonical six-role hierarchy is enforced at the model layer
Evidence: [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py)

Key code evidence:
- `SALES_ROLE_CHOICES` includes `SUPER_ADMIN`, `HEAD_OF_SALES`, `RSM`, `SSM`, `ASM`, `BDO`.
- `Role.clean()` validates the exact parent-child chain: `SUPER_ADMIN -> HEAD_OF_SALES -> RSM -> SSM -> ASM -> BDO`.
- `Role.delete()` explicitly protects canonical sales roles from deletion.

Conclusion:
- There is a deliberate and explicit fixed sales hierarchy in the platform.
- This is the strongest evidence of the intended corporate RBAC structure.

### 2) Sales-role permission ceilings are enforced in the authorization helper
Evidence: [finlo/contrib/core/sales_authorization.py](./finlo/contrib/core/sales_authorization.py)

Key code evidence:
- `is_super_admin_or_superuser()` treats `SUPER_ADMIN` role and Django superuser as a global access exception.
- `sales_role_permission_decision()` implements a permission ceiling for each role.
- `has_effective_permission()` checks both the role ceiling and the user’s actual Django permission.

Conclusion:
- The platform is designed to enforce a permission ceiling rather than trust raw Django permission assignment alone.

### 3) Company-scope enforcement exists separately from role scope
Evidence: [finlo/contrib/core/authorization.py](./finlo/contrib/core/authorization.py)

Key code evidence:
- `get_company_scope()` returns a company boundary that cannot be assumed from the session alone.
- `scope_queryset_to_company()` applies the company boundary before any module-specific permission checks.
- `can_access_company_record()` blocks cross-company record access in addition to role scope.

Conclusion:
- Canonical backend access control is intentionally layered across company and sales-hierarchy boundaries.

## Evidence of the conflict surface

### 4) Generic Role management is still a separate feature surface
Evidence: [finlo/contrib/core/views/roles.py](./finlo/contrib/core/views/roles.py), [finlo/contrib/core/menu.py](./finlo/contrib/core/menu.py)

Key code evidence:
- `AddRole` allows generic role creation/editing.
- `RolesView` and related menu entries expose a role-management interface under settings.
- The same settings menu also exposes `Role`, `TeamRole`, `CustomerRole`, and `PartnerRole` as distinct objects.

Conflict:
- The system contains a fixed, canonical sales hierarchy and a generic configurable role feature.
- Those are not the same thing, yet they appear coexisting in the same admin surface.

### 5) User-level role restrictions are exist, but they are not a complete defense against conflicting configuration surfaces
Evidence: [finlo/contrib/core/forms/users.py](./finlo/contrib/core/forms/users.py)

Key code evidence:
- `_restrict_user_role_field()` reduces the role options based on caller role.
- `_validate_user_role_assignment()` blocks non-superadmins from changing existing user roles.
- `UserFormClass.clean_role()` rejects assignment of unauthorized role keys.

Conclusion:
- This form layer is good protection for normal flows, but it does not eliminate the broader architecture conflict between fixed hierarchy and generic role configuration.

## Severity findings

| # | Severity | Finding | Evidence | Status |
|---|---|---|---|---|
| 1 | 🟠 HIGH | Duplicate authorization planes: fixed canonical sales hierarchy and generic role management coexist. | [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py), [finlo/contrib/core/views/roles.py](./finlo/contrib/core/views/roles.py) | Confirmed architectural risk |
| 2 | 🟠 HIGH | Super Admin privilege may be confused with generic role configuration surfaces if a non-canonical role is introduced or assigned. | [finlo/contrib/core/sales_authorization.py](./finlo/contrib/core/sales_authorization.py), [finlo/contrib/core/forms/users.py](./finlo/contrib/core/forms/users.py) | Potential / configuration risk |
| 3 | 🟡 MEDIUM | The generic role manager allows additional role objects such as team/customer/partner roles, creating drift from the six-role sales hierarchy. | [finlo/contrib/core/menu.py](./finlo/contrib/core/menu.py), [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py) | Confirmed design duplication |
| 4 | 🟡 MEDIUM | Not all modules were fully validated end-to-end against every role and route, so UI-level failures cannot be ruled out in all screens. | [finlo/contrib/core/views/users.py](./finlo/contrib/core/views/users.py), [finlo_crm/leads/views/lead_actions.py](./finlo_crm/leads/views/lead_actions.py) | Untested scope |

## Super Admin access analysis

The core backend model and helper layer support a strong Super Admin exception and broad access boundary. Evidence:
- [finlo/contrib/core/sales_authorization.py](./finlo/contrib/core/sales_authorization.py): `is_super_admin_or_superuser()` allows global access for Django superusers and `SUPER_ADMIN` role users.
- [finlo/contrib/core/authorization.py](./finlo/contrib/core/authorization.py): `get_company_scope()` explicitly recognizes global access for `SUPER_ADMIN`.

However, there is a remaining audit gap:
- the project still has multiple admin surfaces and role-related configuration paths, so a Super Admin may be blocked or confused depending on which route is used.
- The canonical backend enforcement does not automatically guarantee every generic admin screen behaves consistently.

## Conclusion

The strongest, validated layer is the canonical hierarchy and scope helper set. The main RBAC issue is not a simple failure to implement the hierarchy; it is the existence of competing configuration surfaces that can create conflicting admin expectations and duplicate role semantics. That is the primary risk area for the project.
