# Authorization and Company Scope

This project uses Django authentication and permissions; Supabase Auth and
PostgreSQL RLS do not replace application authorization.

## Company boundary

- A normal authenticated user is scoped to the company on their user account.
- A user with `core.can_switch_company` may select a different active company.
  `show_all_companies` is honored only while that permission is present.
- A user without an assigned company receives no access to company-scoped
  records.
- Django superusers and users with the explicit `SUPER_ADMIN` system role are
  the platform-wide exceptions: they may access records across companies and
  administer organization configuration. `is_staff` alone does not grant
  cross-company access.
- A model's global `view`/`change`/`delete` permission applies only within the
  caller's company scope. `_own` permissions further restrict records to the
  user and users in subordinate Finlo roles.

## FINLONEXA sales-role permission ceiling

For the six system roles, `sales_role_permission_decision` is a permission
ceiling, not a permission grant. Every allowed action for
`HEAD_OF_SALES`, `RSM`, `SSM`, `ASM`, and `BDO` still requires the matching
Django permission; a denied action remains denied even if that permission was
assigned. `SUPER_ADMIN` and Django superusers are the documented full-access
exceptions.

| Role | Read sales data / reports / scoped employees | Create leads / activities | Update in scope | Delete | Organization/settings administration |
| --- | --- | --- | --- | --- | --- |
| SUPER_ADMIN | All companies | Yes | Yes | Yes | Yes |
| HEAD_OF_SALES | Company-wide sales scope | Yes | No | No | No |
| RSM | Assigned region and reporting tree | Yes | Yes | No | No |
| SSM | Assigned teams and reporting tree | Yes | Yes | No | No |
| ASM | Assigned BDOs and reporting tree | Yes | Yes | No | No |
| BDO | Own authorized records | Yes | Yes | No | No |

For ordinary sales roles, owner and sub-owner transfers are not an implicit
consequence of change permission. Lead BDO assignment must use the dedicated
ASM-authorized assignment flow; legacy automatic owner-assignment rules do
not replace the creator as lead owner. Exports require explicit export
permissions, and the current sales-role ceiling does not grant them.

The shared enforcement points are
`finlo.contrib.core.authorization.scope_queryset_to_company`,
`CompanyFilteredManager`, DRF queryset/object permissions, the user management
views, generic HTML form permission checks, and the export-queryset helper.
Dashboard KPI/table queries and report preview/export queries use the same
company and sales-hierarchy scope. APIs, bulk operations, and exports must not
rely on navigation visibility or a model permission alone.

## Writable user fields

The user API never accepts `is_superuser`, `is_staff`, `groups`, or
`user_permissions` as writable fields. Non-superusers cannot move users
between companies unless they have the explicit `SUPER_ADMIN` system role.
Assigning a Finlo role requires the effective role-administration access,
and the role, department, and currency must belong to the user's company
unless the caller has global administration access.
Company-scoped CRM serializers derive the company from the authorized request
scope and reject cross-company values.

## Safe authorization tests

Run authorization tests using the dedicated ephemeral SQLite settings, not
the configured Supabase target:

```powershell
.\.venv\Scripts\python.exe manage.py test finlo.contrib.core.test_authorization finlo.contrib.core.test_security_settings finlo_crm.leads.tests.test_sales_hierarchy --settings=finlo.settings.security_test
```

The test settings force SQLite `:memory:` even if a local `.env` contains a
PostgreSQL `DATABASE_URL`. Verify both `ENGINE` and `NAME` immediately before
starting a test run. Never run the Django test suite with the production
Supabase settings.

## Sales hierarchy validation status

The focused sales hierarchy tests cover the six-role permission ceiling,
reporting chain, region/team matching, company boundaries, BDO assignment by
the direct ASM, lead owner preservation, API/form assignment scope, permission
revocation, employee reassignment, legacy automatic assignment behavior, and
the existing lead-conversion endpoint behavior. They also check lead CRUD
permission policy through HTML record checks and DRF list/create/bulk action
checks, dashboard KPI/report export row scope, and dashboard-form denial when
a sales role has a conflicting Django grant. These tests run after locally
prepared core and leads migrations are applied to the ephemeral test database.
They do not exercise every route, screen, module/action combination, dashboard
aggregation, or custom permission implementation in every installed module.
The prepared migrations must not be applied to Supabase without explicit
approval of the exact schema operations.
