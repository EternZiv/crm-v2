# FINLO COMPLETE FEATURE INVENTORY

Date: 2026-11-11
Scope: Read-only audit of the FINLONEXA CRM v2 codebase. No application code, permission records, or database data were modified.

## Executive summary

The platform contains a substantial CRM surface area with a clear canonical sales hierarchy and multiple cross-cutting modules. The strongest evidence is in the core authorization and sales scope code, which enforces a fixed six-role sales model and company-scoped filtering. However, the codebase also shows duplicated or overlapping systems for roles, permissions, configuration, and workflow patterns, which makes the feature inventory incomplete from a single canonical source.

## Inventory by domain

| Domain | Evidence | Status | Notes |
|---|---|---:|---|
| Core company / user / role management | [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py), [finlo/contrib/core/forms/users.py](./finlo/contrib/core/forms/users.py), [finlo/contrib/core/views/users.py](./finlo/contrib/core/views/users.py), [finlo/contrib/core/views/roles.py](./finlo/contrib/core/views/roles.py) | Implemented | Strong RBAC model and user management controls exist. |
| Sales hierarchy / assignment | [finlo/contrib/core/sales_authorization.py](./finlo/contrib/core/sales_authorization.py), [finlo/contrib/core/authorization.py](./finlo/contrib/core/authorization.py) | Implemented | Scope checks are explicit and design-driven. |
| Leads | [finlo_crm/leads/authorization.py](./finlo_crm/leads/authorization.py), [finlo_crm/leads/views/lead_actions.py](./finlo_crm/leads/views/lead_actions.py) | Implemented but with edge-case risk | BDO lead assignment and create/edit policies are defined. |
| Accounts, contacts, opportunities | directory evidence in [finlo_crm](./finlo_crm) and [finlo/contrib](./finlo/contrib) | Present | These modules exist in the codebase, but direct end-to-end audit coverage was limited to the canonical enforcement points and docs. |
| Activities / calendar / calls / bookings | [finlo/contrib/activity](./finlo/contrib/activity), [finlo/contrib/calendar](./finlo/contrib/calendar), [booking](./booking), [calls](./calls) | Present | Feature modules exist with matching views, forms, and templates. |
| Mail / messaging / templates | [finlo/contrib/mail/models.py](./finlo/contrib/mail/models.py), [finlo/contrib/mail/services.py](./finlo/contrib/mail/services.py), [finlo/contrib/mail/backends.py](./finlo/contrib/mail/backends.py), [finlo/contrib/mail/tasks.py](./finlo/contrib/mail/tasks.py) | Partially implemented / partially audited | Complex sender selection, tracking pixel, scheduling, Outlook token refresh, and incoming-mail infrastructure are present. |
| Dashboard / reports / exports | [finlo/contrib/dashboard](./finlo/contrib/dashboard), [finlo/contrib/reports](./finlo/contrib/reports) | Implemented | Audit evidence suggests company and sales-level scoping is intended. |
| Duplicates / workflow / automations | [finlo/contrib/duplicates](./finlo/contrib/duplicates), [finlo/contrib/workflow](./finlo/contrib/workflow), [finlo/contrib/automations](./finlo/contrib/automations) | Present but overlapping | Multiple duplicated or adjacent features exist alongside core CRM modules. |
| Field requirements / form layouts | [finlo/contrib/field_requirements](./finlo/contrib/field_requirements), [finlo/contrib/form_layouts](./finlo/contrib/form_layouts) | Present | Configuration-driven behavior is likely used across screens. |
| Coverage states | docs and canonical enforcement files | Partial | Some modules are implemented, but full business-flow validation was not completed within this read-only audit scope. |

## Confirmed feature implementations

1. Canonical six-role hierarchy is implemented in [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py).
   - `Role.SALES_ROLE_CHOICES` includes `SUPER_ADMIN`, `HEAD_OF_SALES`, `RSM`, `SSM`, `ASM`, and `BDO`.
   - `Role.clean()` enforces parent-role mapping and rejects cycles.
   - `Role.delete()` blocks deletion of canonical system roles.

2. Permission ceiling and hierarchy scoping are implemented in [finlo/contrib/core/sales_authorization.py](./finlo/contrib/core/sales_authorization.py).
   - `sales_role_permission_decision()` applies the effective permission ceiling.
   - `has_effective_permission()` is used to check effective permission without exceeding the ceiling.
   - `scope_queryset_to_sales_hierarchy()` reduces querysets based on role scope.

3. Company scoping is implemented in [finlo/contrib/core/authorization.py](./finlo/contrib/core/authorization.py).
   - `get_company_scope()` resolves the active company boundary.
   - `scope_queryset_to_company()` filters by company.
   - `can_access_company_record()` refuses record access outside the user’s permitted company scope.

4. User management and role restrictions are implemented in [finlo/contrib/core/forms/users.py](./finlo/contrib/core/forms/users.py) and [finlo/contrib/core/views/users.py](./finlo/contrib/core/views/users.py).
   - Non-superadmins cannot reassign roles to arbitrary higher-level roles.
   - Creation is restricted to expected sales-role boundaries.

5. Mail system is implemented in [finlo/contrib/mail](./finlo/contrib/mail).
   - `FinloMailManager.send_mail()` validates recipient domains with MX/A checks.
   - `FinloDefaultMailBackend` dynamically chooses sender configuration.
   - Celery tasks exist for scheduled sends and token refresh, showing operational support for asynchronous dispatch.

## Incomplete or partially implemented areas

- The codebase appears to have multiple overlapping configuration surfaces, especially around role management and permission configuration. This creates a feature inventory challenge because the canonical hierarchy is explicit, while the generic role configuration UI still exists.
- Some modules are present but not fully validated in this audit: workflow automation, duplicates, reports, calendar, email receiving, and cross-module synchronisation pathways.
- The project contains enough infrastructure to support mail sending and asynchronous processing, but full end-to-end mail synchronization with inbound message ingestion and CRM object linking was not fully evidenced in this read-only review.

## Severity assessment

- High: Feature surface is large but duplicate control planes introduce drift risk.
- Medium: Some modules are present but not fully validated end-to-end.
- Medium: Mail receive/sync integration was not fully proven from code alone.

## Conclusion

The CRM has a mature set of exposed modules and a fairly strong canonical RBAC implementation, but the inventory is best understood as a platform with a sound core enforcement layer plus additional partial or nested feature systems that may not be harmonized. That architecture is the main reason the audit is still focused on RBAC conflicts, duplicate systems, and admin access integrity.
