# FINLO DATABASE SECURITY AUDIT

Date: 2026-11-11
Scope: Read-only review of database-layer behavior, access scope, session company logic, secret handling, and risk areas not yet resolved by the core RBAC design.

## Executive summary

The most important audit outcome is that the canonical sales role and company-scope controls are implemented with clear backend enforcement rather than relying entirely on Django’s raw model permissions. The database/security posture is therefore stronger than the generic role architecture suggests. The main residual risks are architectural drift, duplicated permission surfaces, session-driven cross-company access flags, and the operational risks of a custom mail system with custom token and password handling.

## Positive controls found

### 1) Canonical six-role hierarchy is enforced with a cycle guard and protected system roles
Evidence: [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py)

Findings:
- `Role.clean()` prevents cycles and enforces the immediate-parent rule.
- `Role.delete()` prevents deletion of canonical sales-role records.
- This is a meaningful protection at the model layer and greatly reduces the chance of accidental hierarchy corruption.

### 2) Company and sales scope are applied to all querysets and record access paths
Evidence: [finlo/contrib/core/authorization.py](./finlo/contrib/core/authorization.py), [finlo/contrib/core/sales_authorization.py](./finlo/contrib/core/sales_authorization.py)

Findings:
- `scope_queryset_to_company()` restricts querysets by company.
- `can_access_company_record()` blocks cross-company record access.
- `scope_queryset_to_sales_hierarchy()` further restricts access by sales scope.

This is strong evidence of a deliberate database access-control layer.

### 3) Sensitive mail credentials are encrypted before storage
Evidence: [finlo/contrib/mail/models.py](./finlo/contrib/mail/models.py)

Findings:
- `FinloMailConfiguration.password` and `outlook_client_secret` are stored via encrypted field wrappers.
- The model intentionally provides a `get_decrypted_password()` and `get_decrypted_client_secret()` path.

This is a positive operational security control.

## Risk areas and potential vulnerabilities

### 4) Duplicate role and permission surfaces remain the principal security architecture risk
Evidence: [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py), [finlo/contrib/core/views/roles.py](./finlo/contrib/core/views/roles.py), [finlo/contrib/core/menu.py](./finlo/contrib/core/menu.py)

Findings:
- The project has a strict fixed sales-role model and a generic role management UI.
- This creates room for contradictory permission assumptions across screens.
- In a large project, this is a real risk: future role assignment or custom permission changes can bypass the intended hierarchy unless all surfaces remain aligned.

Severity: High

### 5) Session-driven company access flags can widen scope if the active company/session state is manipulated
Evidence: [finlo/contrib/core/authorization.py](./finlo/contrib/core/authorization.py)

Findings:
- `get_company_scope()` checks `session.get("show_all_companies")` and `session.get("active_company_id")` when the user has a company-switch permission.
- This is intentionally designed, but it means an attacker with the necessary permission and a manipulated session could widen company scope.
- The risk is controlled by the permission check and role scope, but it is a real session-driven access surface that must be monitored.

Severity: Medium

### 6) Mail system fallback logic can mask infrastructure errors during delivery attempts
Evidence: [finlo/contrib/mail/services.py](./finlo/contrib/mail/services.py)

Findings:
- `_has_mx_record()` returns `True` when DNS lookup fails in some unexpected exception path.
- This means the system may attempt sending to domains whose validation could not be computed.
- This is a best-effort validation design, but it weakens the guarantee that undeliverable addresses are blocked before sending.

Severity: Medium

## Severity findings

| # | Severity | Finding | Evidence | Status |
|---|---|---|---|---|
| 1 | 🟠 HIGH | The project mixes a fixed sales hierarchy with a generic role-management plane, creating RBAC drift risk. | [finlo/contrib/core/models/organization.py](./finlo/contrib/core/models/organization.py), [finlo/contrib/core/views/roles.py](./finlo/contrib/core/views/roles.py) | Confirmed architectural issue |
| 2 | 🟡 MEDIUM | Session-driven company scope expansion remains a possible privilege surface if authorization is misused or permission is granted incorrectly. | [finlo/contrib/core/authorization.py](./finlo/contrib/core/authorization.py) | Potential risk |
| 3 | 🟡 MEDIUM | Mail DNS validation falls back to allowance when exceptions occur, so invalid recipients may still be attempted. | [finlo/contrib/mail/services.py](./finlo/contrib/mail/services.py) | Potential risk |
| 4 | ⚪ LOW | Secret storage is improved by encryption, but operational security still depends on token rotation and configuration hygiene. | [finlo/contrib/mail/models.py](./finlo/contrib/mail/models.py) | Operational consideration |

## Conclusion

No confirmed SQL injection, direct database-escape failure, or obvious raw-query privilege escalation was identified in the canonical RBAC path. The security posture is strongest where the platform enforces company and sales-role scoping through custom queryset and record helpers. The main outstanding database/security risk is architectural drift between the fixed six-role hierarchy and the generic role-management infrastructure, plus a few operational risks in the custom mail flow and session-scoped company logic.
