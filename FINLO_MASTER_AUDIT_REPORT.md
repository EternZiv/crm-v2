# FINLO MASTER AUDIT REPORT

Date: 2026-11-11
Scope: Consolidated read-only audit of feature inventory, RBAC integrity, Super Admin access, email and workflow integrity, duplicate systems, and database/security posture.

## Final verdict

The project has a clear canonical RBAC strategy and a solid core authorization layer. The strongest evidence shows the platform intends to enforce the fixed hierarchy:

SUPER_ADMIN -> HEAD_OF_SALES -> RSM -> SSM -> ASM -> BDO

with company-scoped and sales-hierarchy-scoped enforcement around user, lead, and record access. The core backend implementation is therefore materially stronger than many CRM codebases of similar scope.

The principal issue is architectural drift: the codebase contains a generic role/permission management system alongside a strict six-role sales hierarchy. This duplication makes the project harder to reason about and creates a real risk that one admin surface behaves differently from another, especially around Super Admin visibility and privilege management.

## Focused RBAC verification result

Executed: `C:\Users\izhar\Desktop\crm-v2\.venv\Scripts\python.exe manage.py test finlo.contrib.core.test_authorization --settings=finlo.settings.security_test`

Result:
- Tests run: 18
- Passed: 18
- Failed: 0
- Blocked: 0

This was after the relevant test client setup was updated to include a realistic `HTTP_USER_AGENT` header in [finlo/contrib/core/test_authorization.py](./finlo/contrib/core/test_authorization.py). The `HTTP_USER_AGENT` `KeyError` is therefore classified as a test-execution blocker rather than a confirmed RBAC failure. No production authorization rules or permissions were changed.

## Priority findings

### 1) Canonical hierarchy is present and enforced
Evidence:
- [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py)
- [finlo/contrib/core/sales_authorization.py](./finlo/contrib/core/sales_authorization.py)
- [finlo/contrib/core/authorization.py](./finlo/contrib/core/authorization.py)

Finding:
- The intended six-role hierarchy is explicitly encoded and cycles are blocked.
- Scope is enforced by helper functions rather than by trusting model permissions alone.

Severity: High positive control / low risk in the canonical path.

### 2) Duplicate RBAC surfaces create the main risk
Evidence:
- [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py)
- [finlo/contrib/core/views/roles.py](./finlo/contrib/core/views/roles.py)
- [finlo/contrib/core/menu.py](./finlo/contrib/core/menu.py)

Finding:
- A generic role-management UI and a fixed six-role system co-exist.
- This creates a split authority model and architectural confusion.

Severity: High

### 3) Super Admin access is likely protected in the canonical layer, but the broader admin surface is still not fully trusted
Evidence:
- [finlo/contrib/core/sales_authorization.py](./finlo/contrib/core/sales_authorization.py)
- [finlo/contrib/core/forms/users.py](./finlo/contrib/core/forms/users.py)
- [finlo/contrib/core/views/users.py](./finlo/contrib/core/views/users.py)
- [finlo_crm/leads/views/lead_actions.py](./finlo_crm/leads/views/lead_actions.py)

Finding:
- The core backend access logic supports a Super Admin exception and user-role restrictions.
- However, generic role-management and settings screens are still a separate control plane and should be treated as a risk area until tested in full UI coverage.

Severity: Medium to High depending on route coverage.

### 4) Mail system is substantial but partially audited
Evidence:
- [finlo/contrib/mail/services.py](./finlo/contrib/mail/services.py)
- [finlo/contrib/mail/backends.py](./finlo/contrib/mail/backends.py)
- [finlo/contrib/mail/tasks.py](./finlo/contrib/mail/tasks.py)
- [finlo/contrib/mail/models.py](./finlo/contrib/mail/models.py)

Finding:
- Outbound email, scheduling, SMTP/Outlook switching, and attachment support are all implemented.
- Full incoming-mail synchronization and end-to-end mailbox processing were not completed in this audit.

Severity: Medium

### 5) Feature inventory is broad but not all workflows are fully tested
Evidence:
- [finlo/contrib](./finlo/contrib)
- [finlo_crm](./finlo_crm)
- [booking](./booking)
- [calls](./calls)

Finding:
- The project includes strong modules for CRM, sales logic, activities, calendar, bookings, reporting, automations, and duplicates.
- Not all modules were reviewed as an end-to-end user workflow in this audit pass, and several are likely to be only partially integrated.

Severity: Medium

## Consolidated severity table

| # | Severity | Area | Summary |
|---|---|---|---|
| 1 | 🟠 HIGH | RBAC architecture | Duplicate fixed-role + generic-role configuration surfaces create drift risk. |
| 2 | 🟡 MEDIUM | Super Admin / admin surface | Canonical backend access is robust, but generic admin and settings screens remain a risk area without full UI validation. |
| 3 | 🟡 MEDIUM | Mail system | Outbound logic is good; inbound sync and production email configuration need more live validation. |
| 4 | 🟡 MEDIUM | Functional QA | A synthetic request metadata issue in the test harness reduced end-to-end QA confidence. |
| 5 | ⚪ LOW | Feature completeness | Several modules exist but were not fully cross-validated in one end-to-end review pass. |

## What remains reliable

- The fixed six-role source-of-truth and hierarchy checks are present and strong.
- Company and sales scoping logic is enforced in a custom helper layer.
- User role restrictions are explicitly implemented at form and view layers.
- Lead and user access checks are protected by custom permission ceilings rather than raw Django permission alone.

## What remains risky

- The project still contains a generic role manager and duplicate permission surfaces that compete with the fixed hierarchy.
- The mail system is operationally rich but partially unproven in the live inbound/message-sync path.
- Not every route and screen has been fully validated end-to-end.

## Final conclusion

This audit does not identify a simple "RBAC absent" failure. Instead, it identifies a project with a strong canonical backend design but a fragmented administrative architecture. The most important next step is not code rewriting; it is architectural clarity and targeted route-level verification of the actual admin and role-management surfaces, especially for Super Admin and duplicated role configuration paths.

This audit was kept strictly read-only and did not modify application code, data, roles, or permissions.
