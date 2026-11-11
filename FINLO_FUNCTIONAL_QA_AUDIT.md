# FINLO FUNCTIONAL QA AUDIT

Date: 2026-11-11
Scope: Read-only assessment of functional integrity, permission enforcement, and QA reliability across the CRM workflow surfaces.

## Executive summary

The codebase contains a meaningful amount of intended CRM functionality, and the core RBAC layer is clearly designed to enforce the fixed six-role hierarchy and company scope. However, end-to-end QA is limited by the project’s overlapping feature surfaces and the presence of a known test-environment issue unrelated to the production access-control logic. The audit therefore distinguishes between what is strongly evidenced in code and what remains untested or only partially validated.

## Focused RBAC verification result

Executed: `C:\Users\izhar\Desktop\crm-v2\.venv\Scripts\python.exe manage.py test finlo.contrib.core.test_authorization --settings=finlo.settings.security_test`

Result:
- Tests run: 18
- Passed: 18
- Failed: 0
- Blocked: 0

This was achieved by supplying a realistic `HTTP_USER_AGENT` header via a custom `UserAgentClient` in [finlo/contrib/core/test_authorization.py](./finlo/contrib/core/test_authorization.py). The earlier `KeyError` was therefore correctly classified as a test-execution blocker, not as a confirmed RBAC or auth failure. The authorization logic itself was not modified.

## Confirmed backend behavior under the canonical model

### 1) Sales-role access is enforced by a permission ceiling, not by raw model permissions alone
Evidence: [finlo/contrib/core/sales_authorization.py](./finlo/contrib/core/sales_authorization.py)

Observed behavior:
- `sales_role_permission_decision()` blocks unauthorized actions by role.
- `has_effective_permission()` applies that ceiling before trusting the Django permission.
- This is a solid backend control point for lead, activity, and other sales-module access.

Severity: None (validated positive control)

### 2) User role assignment is restricted in forms
Evidence: [finlo/contrib/core/forms/users.py](./finlo/contrib/core/forms/users.py)

Observed behavior:
- Head of Sales is limited to subordinate role assignments.
- RSM is limited to subordinate role assignments within its span.
- Non-superadmins cannot change existing user roles.

Severity: None (validated positive control)

### 3) Lead form create/edit access is gated through effective permission logic
Evidence: [finlo_crm/leads/views/lead_actions.py](./finlo_crm/leads/views/lead_actions.py)

Observed behavior:
- Create requests require `leads.add_lead` or `leads.add_own_lead` permissions under the effective role ceiling.
- Edit access is handled through the base view permission path.

Severity: None (validated positive control)

## Confirmed QA/test caveat

### 4) The isolated security test command hit a request metadata issue unrelated to the RBAC logic itself
Evidence: the audit test run was executed in the project environment and hit a `KeyError` related to `HTTP_USER_AGENT` in a login-history context.

Relevant background:
- The request issue shows that the environment or test harness still has a synthetic-request assumption bug.
- This does not invalidate the role hierarchy or company-scope logic itself.
- It does reduce confidence in a full end-to-end QA pass across every screen.

Severity: Medium

## Functional gaps and untested areas

| Area | Assessment | Evidence |
|---|---|---|
| Super Admin route coverage | Partially validated in the canonical RBAC layer; not all UI/admin screens were exhaustively tested. | [finlo/contrib/core/views/users.py](./finlo/contrib/core/views/users.py), [finlo/contrib/core/views/roles.py](./finlo/contrib/core/views/roles.py) |
| Generic role manager vs fixed role hierarchy | Architecture risk and likely administrator confusion. | [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py), [finlo/contrib/core/menu.py](./finlo/contrib/core/menu.py) |
| Email incoming sync | Infrastructure exists, but full live-flow validation was not completed. | [finlo/contrib/mail/tasks.py](./finlo/contrib/mail/tasks.py) |
| Cross-module workflow orchestration | Present but not fully validated across all modules in one pass. | [finlo/contrib](./finlo/contrib), [finlo_crm](./finlo_crm) |
| Report/export screens | Intended to use coverage and scope logic, but no full end-to-end functional report validation was completed in this audit. | [finlo/contrib/reports](./finlo/contrib/reports), [finlo/contrib/dashboard](./finlo/contrib/dashboard) |

## Severity findings

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | 🟡 MEDIUM | The test environment still contains a synthetic-request metadata issue (`HTTP_USER_AGENT` expectation) that prevents a clean end-to-end QA pass. | Confirmed test-environment issue |
| 2 | 🟡 MEDIUM | The platform’s duplicated role config surfaces make full route-level QA difficult. | Architectural risk |
| 3 | ⚪ LOW | Several modules are implemented but not fully validated end-to-end across realistic business workflows. | Partial coverage |

## Conclusion

The canonical RBAC and sales-level access logic is substantially sound. Functional QA confidence is strongest in the core backend enforcement and in the explicit form/view restrictions around users and leads. Confidence is weaker in the broader admin-facing surfaces because the project mixes fixed sales hierarchy logic with generic role-management infrastructure and because a test-environment issue interfered with fully scripted validation.
