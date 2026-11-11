# FINLO DUPLICATE FEATURE AUDIT

Date: 2026-11-11
Scope: Read-only review of duplicate or overlapping systems, especially around roles, permissions, and CRM feature surfaces.

## Executive summary

The project contains both a strong canonical model and a set of duplicate or overlapping management features. The largest duplicate risk is the coexistence of:
- a fixed six-role hierarchy (`SUPER_ADMIN -> HEAD_OF_SALES -> RSM -> SSM -> ASM -> BDO`), and
- a generic role-management stack that includes more configurable role objects and permissions screens.

This is not a minor naming issue. It creates architectural drift risk because two systems are likely to compete for authority without a single source of truth.

## Primary duplicate/conflicting systems

### 1) Fixed six-role hierarchy vs generic role manager
Evidence:
- [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py)
- [finlo/contrib/core/views/roles.py](./finlo/contrib/core/views/roles.py)
- [finlo/contrib/core/menu.py](./finlo/contrib/core/menu.py)

Findings:
- `Role.SALES_ROLE_CHOICES` and `Role.clean()` define a strict fixed sales-role system.
- The role-management UI (`AddRole`, `RolesView`) exposes a more generic `Role` creation pattern that does not clearly enforce the same fixed chain if used outside the canonical role assignments.
- The settings menu exposes `Role`, `TeamRole`, `CustomerRole`, and `PartnerRole` as a single admin space, which is structurally different from the fixed sales-role model.

Severity: High

### 2) Different feature domains share overlapping admin routes and permission logic
Evidence:
- [finlo/contrib/core/menu.py](./finlo/contrib/core/menu.py)
- [finlo/contrib/core/views/users.py](./finlo/contrib/core/views/users.py)
- [finlo/contrib/core/views/roles.py](./finlo/contrib/core/views/roles.py)

Findings:
- User management, company settings, role management, and permission configuration all live in the same "settings" paradigm.
- The project seems to blend model-level permissions with custom role helper logic, making it easy for one administrative screen to behave differently from another.

Severity: Medium

### 3) Sales hierarchy and general role metadata overlap in the same domain object
Evidence:
- [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py)

Findings:
- A `Role` model has both a freeform `role_name` and a constrained `system_key` for fixed sales roles.
- That means the same table is used for both canonical sales roles and custom role objects.
- This increases the chance of inconsistent rules during role assignment, role deletion, or UI rendering.

Severity: High

## Duplicate workflow and feature surfaces

The current codebase suggests additional duplicate or adjacent functionality across domain areas:

- Core company/user management and role management are in [finlo/contrib/core](./finlo/contrib/core).
- Sales-specific implementation logic sits in [finlo_crm/leads](./finlo_crm/leads).
- Generic workflow, duplicates, and automations exist under [finlo/contrib](./finlo/contrib).
- Calendar, activity, booking, and calls have separate app modules even though they overlap in CRM operations.

This indicates a broader pattern: several feature domains exist, but some are implemented in parallel instead of as one unified workflow system. This is not necessarily wrong, but it increases maintenance and permission drift risk.

## Severity findings

| # | Severity | Finding | Evidence | Status |
|---|---|---|---|---|
| 1 | 🟠 HIGH | Fixed sales-role hierarchy and generic role management are competing sources of truth. | [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py), [finlo/contrib/core/views/roles.py](./finlo/contrib/core/views/roles.py) | Confirmed |
| 2 | 🟠 HIGH | Role metadata supports both system-controlled keys and arbitrary custom role records in the same model. | [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py) | Confirmed |
| 3 | 🟡 MEDIUM | Settings and permissions screens are split across multiple generic views and menu entries without a single canonical access model. | [finlo/contrib/core/menu.py](./finlo/contrib/core/menu.py) | Architectural risk |
| 4 | ⚪ LOW | Feature overlaps exist between CRM, activity, calendar, booking, and automation modules. This is not necessarily broken, but it complicates full QA coverage. | [finlo/contrib](./finlo/contrib), [booking](./booking), [calls](./calls) | Present |

## Conclusion

The biggest audit issue is not that the project lacks RBAC; it is that the project contains more than one RBAC/control plane. The canonical six-role hierarchy is real and carefully enforced, but the existence of generic role and permission configuration surfaces undermines clarity and increases the risk that users, admins, or future developers will work against the wrong authority model.
