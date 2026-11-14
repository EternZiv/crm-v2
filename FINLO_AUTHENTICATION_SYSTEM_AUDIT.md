# FINLONEXA CRM v2 — Authentication System Audit

Date: 2026-11-14. Scope: read-only source review and bounded database connectivity probe. No account, role, permission, session, business data, or setting was changed.

## Status

| Area | Status | Evidence |
|---|---|---|
| Authentication architecture | PASS (static review) | Custom Django user, Django sessions, ModelBackend reviewed. |
| Password storage and validation | PASS (static review) | Django hashers/validators configured; missing-password creation uses unusable passwords. |
| Six-role identities/hierarchy in source | PASS (static review) | Canonical keys and parent-chain validation exist. Current DB configuration is unverified. |
| Requested BDO lead-create denial | FAIL / NEEDS APPROVAL | Current policy and focused test allow BDO lead creation, conflicting with the requested matrix. |
| Current database account/role inventory | BLOCKED | Supabase pooler hostname failed DNS before a connection. |
| Runtime/MCP acceptance | BLOCKED | No isolated authenticated environment. MCP implementation was not inspected because Antigravity owns it. |

## Authentication architecture

- AUTH_USER_MODEL is core.FinloUser; the configured backend is Django ModelBackend.
- Login authenticates username/password, rejects inactive users, uses a generic failure response, delegates session creation to Django login, and validates next redirects.
- Logout is POST-only and uses Django logout. CSRF middleware is enabled.
- Password reset uses Django's token generator, a configured 24-hour timeout, generic request responses, and a configured site URL/host allowlist. Real mailbox delivery was not tested.
- FinloUser.has_perm delegates to FINLO's effective permission evaluator. Company and sales hierarchy scopes use the existing authorization services and SalesAssignment.

## Password and lifecycle findings

- FinloUser.save sets an unusable password for a new user without an explicit password; it does not derive credentials from profile data. Existing hashes are not replaced merely by saving the user.
- The multistep user form excludes password and username; the normal creation path derives username from email and leaves the account unable to log in until secure setup.
- The single-step form validates an explicit password with Django validators and calls set_password.
- The API serializer treats password as write-only, validates supplied passwords, and makes staff/superuser and Django group/permission fields read-only. Runtime API behavior was not exercised.
- Activation/reset email delivery and owner handoff remain unverified. Use single-use, expiring setup links; never distribute plaintext passwords.

## Login, throttling, sessions, recovery

- Validators include user-attribute similarity, minimum length, common-password, and numeric-only checks. PBKDF2 is first in the configured hasher list; Argon2 and other compatible hashers are also configured.
- Login throttling is cache-backed and uses REMOTE_ADDR rather than trusting arbitrary forwarded headers. Local default is process-local LocMemCache, so it is not shared across workers. Vercel Redis is not runtime-verified.
- The reviewed login path fails closed on rate-limit cache errors. Redis outage behavior was not tested here.
- Local development uses database sessions, 14-day session age, HttpOnly and SameSite=Lax session cookies, and non-Secure cookies. Vercel settings enable Secure cookies. No setting was changed.
- Password reset returns a generic response for unknown identifiers and applies throttling. Static edge to test: email of one user plus username of another may make the combined lookup ambiguous; exception handling appears generic, but focused isolated testing is needed.
- Browser history cleanup after logout, channel invalidation, actual session expiry, and cross-worker throttling were not tested.

## Roles and authorization

The source defines the six-role chain: SUPER_ADMIN → HEAD_OF_SALES → RSM → SSM → ASM → BDO. SalesAssignment is one-to-one per user and carries region, team, and manager. Model validation requires a sales role, same-company assignment, role-specific territory constraints, and blocks self-management. Source structure does not verify current database assignments.

FINLO SUPER_ADMIN is not Django is_superuser. Do not grant Django superuser based only on the FINLO role name. Live role decisions and assignments could not be read.

### Confirmed requested-policy conflict

sales_role_permission_decision currently grants the built-in leads add action to sales roles, including BDO. Existing test test_fixed_sales_role_permission_ceilings_remain_in_order also expects lead creation for non-SUPER_ADMIN sales roles, including BDO. The requested matrix says BDO must be denied.

Status: FAIL against requested policy; NEEDS APPROVAL before code or database policy changes. A live Dynamic Role Manager denial might exist, but it is unverified and cannot be used as acceptance evidence. After approval, amend the fixed policy and focused test, then verify effective decisions/endpoints with isolated fixtures before any live reconciliation.

## Database target and inventory

Active settings: finlo.settings, environment label development, PostgreSQL database name postgres, Supabase Mumbai transaction pooler on port 6543, CONN_MAX_AGE=0, local LocMemCache. DNS resolution failed before connection; no query succeeded.

The database is remote and its project identity/disposability could not be established. No users, roles, companies, owned records, sessions, workflow references, or integration dependencies were queried. No credentials or hashes were printed. No migrations or writes were performed.

## Test evidence

No tests were started; the configured database is not demonstrably isolated and test setup may create/migrate databases. Earlier reports record 18/18 focused authentication tests and 31/31 isolated authorization tests passing; these are historical, not rerun. The current BDO expectation conflict is static source evidence.

## Next safe actions

1. Provide an approved disposable database and confirm it is non-production.
2. Approve whether BDO lead-create denial supersedes current policy/test expectations.
3. Run focused auth, role, company-scope tests on isolated fixtures.
4. After read-only inventory, present exact account/dependency impact before separate deletion approval.
5. Coordinate MCP review with Antigravity; no MCP files were read or edited.

No live account, role, permission, credential, session, business record, or database setting was changed.

## Updated connectivity and policy evidence — 2026-11-14

A fresh settings inspection still resolves to finlo.settings / development, PostgreSQL database postgres, configured pooler host aws-0-ap-south-1.pooler.supabase.com, port 6543, sslmode=require, and CONN_MAX_AGE=0. Credential values were not printed. The configured host matches the general shared transaction-pooler shape documented by Supabase, but the pooler index is project-specific and cannot be validated from the region. Supabase explicitly says to copy the complete host from the project Connect dialog; aws-0 must not be assumed to be correct. Reference: [Supabase database connection docs](https://supabase.com/docs/guides/database/connecting-to-postgres) and [Supavisor terminology](https://supabase.com/kb/troubleshooting/supavisor-and-connection-terminology-explained-9pr_ZO).

The system DNS query and a direct query to public resolver 1.1.1.1 both returned Windows “Access is denied” from this execution environment. This does not establish that the hostname is invalid, nor that the database is empty or missing. It also does not establish that the problem is specific to this environment; the actual host must be copied from the Supabase project Connect dialog and checked in an environment permitted to resolve DNS. No DB query was attempted because target project identity and authorization remain unconfirmed.

Current source locations for the policy conflict: finlo/contrib/core/sales_authorization.py, function sales_role_permission_decision(), where add permission returns true for leads for all non-SUPER_ADMIN sales roles; finlo/contrib/core/test_authorization.py, test_fixed_sales_role_permission_ceilings_remain_in_order(), where leads.add_lead is asserted true for every non-SUPER_ADMIN sales role. Proposed minimal correction only after approval: exclude BDO from the lead-add ceiling and revise that focused test to expect false for BDO while preserving the other five roles' existing behavior. No code or test was changed.

## Final preparation update — 2026-11-14

No Django server is listening on local port 8000. The repository's existing finlo.settings.security_test uses an in-memory SQLite database and excludes Daphne for isolated authorization tests. It is a safe synthetic test environment, not a connection to the configured Supabase database and cannot inventory real accounts. No authorized current-data diagnostic path was found; database inventory remains BLOCKED. DNS was not retried.

BDO correction proposal (not applied): in sales_role_permission_decision(), replace the add-action return with a rule that preserves existing activity creation and allows lead creation for every canonical sales role except BDO. Suggested expression: return app_label == "activity" or (app_label == "leads" and role_key != "BDO"). SUPER_ADMIN and Django superusers remain handled by the existing earlier allow. The focused test should change its add-lead expectation from unconditional true for non-SUPER_ADMIN roles to role.system_key != "BDO"; it already grants the actor the permission, so this also checks the role ceiling. No code/test was edited and no test was run.
