# FINLONEXA Unified RBAC Pre-Migration Readiness

Date: 2026-11-11

## Decision

**NO-GO for applying migration 0014 to the configured PostgreSQL database until the approval gates below are resolved.** The current implementation passed the focused authorization regression suite and a real-browser Role Manager exercise on an isolated SQLite database. The remaining blockers are deployment/data-policy decisions, not a failed regression test. Migration 0014 has not been applied to PostgreSQL, and no production data was changed.

The configured PostgreSQL database was previously queried in explicit read-only transactions (`transaction_read_only = on`). That probe found core migration 0013 applied and 0014 unapplied. The migration rollback experiment in this report used only a temporary SQLite database under the session directory.

## Confirmed findings and risks

| Rank | Severity | Classification | Finding and evidence |
|---|---|---|---|
| 1 | HIGH | Confirmed data-policy risk | There are 2,280 direct `user_permissions` grants across 10 users. Of these, 1,892 overlap permissions on the user's assigned role and 388 do not. Overlap is not provenance: it cannot establish that a permission was copied from a role. A role-level Deny overrides direct grants for non-Django-superusers; Default removes the role override and falls back to the user's independent Django grants. Therefore, a copied-but-unidentified grant can survive a Default/revocation. Preserve all ambiguous grants until a reviewed reconciliation. |
| 2 | HIGH | Confirmed policy decision | Production users 3 and 35 are active Django `is_superuser` accounts assigned to SUPER_ADMIN role 7. `has_effective_permission()` returns `True` for Django superusers before evaluating role denials. Role Manager changes therefore do not constrain these two accounts. The Role Manager now displays a warning when a role has Django-superuser members; no production flags were changed. Decide whether this unconditional Django bypass is the intended policy. |
| 3 | HIGH | Confirmed rollback data loss | Migration 0014 has no data migration, but reversing it drops the denied-permission and `RoleDataScope` tables/data and restores `FinloUser.role` to `on_delete=CASCADE`. In the isolated rollback test, one denial and one scope row were present before downgrade; both tables were absent afterward, while both role members remained. The historical 0013 migration state reports `CASCADE`. Do not plan an unqualified rollback after these tables contain operational policy. |
| 4 | MEDIUM | Confirmed robustness risk | `django-login-history` directly indexes `request.META['HTTP_USER_AGENT']` in login and logout signal handlers (`.venv/Lib/site-packages/login_history/models.py`). Requests without that header can raise `KeyError`. The test client supplies a realistic header to prevent this test-execution blocker; this does not remove the production edge case. |
| 5 | MEDIUM | Confirmed HTTP semantics issue | In Chrome, the unauthorized Lead list rendered “Permission Denied” and exposed no list content, but its response status was HTTP 200. Authorization was enforced in the response body; clients and caches may still misinterpret the status. This behavior was observed, not changed in this readiness task. |
| 6 | MEDIUM | Untested outside configured backend | The security-test settings use Django `ModelBackend`. The shared evaluator avoids recursion by calling `_has_base_permission()`, which calls `super().has_perm()` rather than dispatching back through `FinloUser.has_perm()`. Alternate/custom authentication backends and every direct permission-check call site were not exhaustively exercised. |

## Production inventory and dry run

The six active built-in roles are in company 3 and retain the required chain:

| Role ID | Role | Parent | Members |
|---:|---|---|---:|
| 7 | SUPER_ADMIN | — | 2 |
| 8 | HEAD_OF_SALES | SUPER_ADMIN | 1 |
| 9 | RSM | HEAD_OF_SALES | 0 |
| 10 | SSM | RSM | 1 |
| 11 | ASM | SSM | 1 |
| 12 | BDO | ASM | 1 |

No custom roles were found. No custom-role scope rows need a compatibility mapping for this database.

Read-only direct-grant dry run (count / overlap with current assigned role / non-overlap):

| User ID | Current role | Direct grants | Overlap | Non-overlap |
|---:|---|---:|---:|---:|
| 2 | None | 71 | 0 | 71 |
| 3 | SUPER_ADMIN (7) | 883 | 883 | 0 |
| 4 | HEAD_OF_SALES (8) | 24 | 24 | 0 |
| 5 | None | 10 | 0 | 10 |
| 6 | SSM (10) | 34 | 34 | 0 |
| 7 | ASM (11) | 34 | 34 | 0 |
| 8 | BDO (12) | 34 | 34 | 0 |
| 33 | None | 149 | 0 | 149 |
| 34 | None | 149 | 0 | 149 |
| 35 | SUPER_ADMIN (7) | 892 | 883 | 9 |
| **Total** |  | **2,280** | **1,892** | **388** |

The 379 direct grants on users with no role and the nine non-overlapping grants for user 35 must remain untouched. The other 1,892 overlaps are also ambiguous without grant provenance.

### Proposed reconciliation policy — approval required

1. Snapshot role memberships, role grants/denials, group grants, direct user grants, and any available permission audit history before deployment.
2. Classify a direct grant as role-derived only when an audit event or other reliable provenance proves its origin. Similarity/overlap with current role permissions is not enough.
3. Keep unassigned-user grants and all ambiguous grants as direct user grants. Do not delete, move, or reinterpret them automatically.
4. For proven role-derived grants, stage the proposed role grant and compare each affected user's effective permissions before and after. Remove the direct copy only after approval and a successful dry-run diff.
5. Use explicit Deny for an approved role-wide revocation while independent direct grants remain; Default means “remove the role override,” not “revoke all sources.”

## Proposed data-scope mapping

New custom roles default to `deny_all`. Existing production custom roles: **none**. Built-in roles continue to use their fixed sales hierarchy and do not receive configurable `RoleDataScope` rows.

| Model/data category | Proposed custom-role scope | Guardrail / approval condition |
|---|---|---|
| `accounts.Account` (`account_owner`), `contacts.Contact` (`contact_owner`), `leads.Lead` (`lead_owner`, `sub_owner`), and `opportunities.Opportunity` (`owner`) | `assigned` | Require an explicit permission grant and enforce the user's company boundary in addition to owner/assignment filters. |
| `opportunities.OpportunityTeam` (`owner`) | `assigned` only after team-membership and company behavior is validated for the chosen actions | Keep `deny_all` until that validation is approved. |
| `campaigns.Campaign` (`campaign_owner`) and `campaigns.CampaignMember` (`created_by`) | `assigned` only after related-object/company paths are verified; otherwise `deny_all` | Ownership alone is not proof of same-company access. |
| `forecast.Forecast` (`owner`) | `assigned` only after forecast visibility/approval rules are verified; otherwise `deny_all` | Preserve forecast approval and hierarchy policy; do not infer scope from `OWNER_FIELDS` alone. |
| Models with a reliable `company` field but no approved owner/assignment rule | `company` only when same-company read/write access is intended | Scope is clamped to the role member's company; permission grants remain separately required. |
| Models without a reliable company, ownership, or assignment boundary; identity/access, role, company, user, and sales-hierarchy administration | `deny_all` or remain non-configurable | Require an explicit design and security review before enabling. |

The owner-field inventory above is based on current declarations in `finlo_crm`. The manager validates supported scopes and the runtime company wrapper clamps company-bearing querysets and object access. The more permissive categories remain conditional proposals, not approved defaults.

## Implementation and code evidence

- [`sales_authorization.py`](./finlo/contrib/core/sales_authorization.py#L55) retains the fixed six-role decision and at line 109 limits explicit role grants. For non-SUPER_ADMIN built-ins, Allow is available only for CRM models declaring `OWNER_FIELDS`; role denials are evaluated before the role-based SUPER_ADMIN allow path. Protected recovery, authentication, company, user, hierarchy, role, and scope capabilities cannot be expanded by ordinary role grants.
- [`sales_authorization.py`](./finlo/contrib/core/sales_authorization.py#L140) applies role Deny, then an eligible live role grant, then the existing fixed-role decision, and finally the base Django permission backend. The unconditional Django `is_superuser` bypass is first.
- [`user.py`](./finlo/contrib/core/models/user.py#L288) routes `FinloUser.has_perm()` to the shared evaluator; `_has_base_permission()` calls Django's parent implementation, avoiding recursive calls through the override.
- [`authorization.py`](./finlo/contrib/core/authorization.py#L18) and [`sales_authorization.py`](./finlo/contrib/core/sales_authorization.py#L483) keep company and fixed sales-hierarchy filters separate from feature permissions.
- [`base.py`](./finlo/contrib/core/views/groups_and_permissions/base.py#L560) validates Allow/Deny/Default writes; line 627 validates custom-role scope selections. Unsupported grants are rejected rather than shown as effective.
- [`group_role_detail.html`](./finlo/contrib/core/templates/permissions/group_role_detail.html#L30) displays the Django-superuser bypass warning. The UI disables unsupported Allow choices and leaves built-in hierarchy scopes fixed.
- [`test_authorization.py`](./finlo/contrib/core/test_authorization.py#L750) covers the fixed hierarchy/permission ceiling; lines 826 onward cover explicit decisions for all six built-in roles, protected permissions, Role Manager rejection, and live changes visible to an already-loaded user.
- [`0014_role_denied_permissions_alter_finlouser_role_and_more.py`](./finlo/contrib/core/migrations/0014_role_denied_permissions_alter_finlouser_role_and_more.py) contains only schema operations: add the role denial relation, change the role FK to PROTECT, and create `RoleDataScope` with a `deny_all` default. There is no `RunPython`/`RunSQL` data transformation.

## Verification results

### Automated tests

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe manage.py test finlo.contrib.core.test_authorization --settings=finlo.settings.security_test` | **31 passed, 0 failed, 0 errors, 0 blocked.** This full run preceded the final superuser-warning template assertion; the 7-test targeted rerun below covered that latest change. System check reported no issues. A missing local `staticfiles` directory warning was non-fatal. |
| `& .\.venv\Scripts\python.exe manage.py test finlo.contrib.core.test_authorization.CompanyAuthorizationTests.test_explicit_role_grants_and_denials_apply_to_all_six_builtin_roles finlo.contrib.core.test_authorization.CompanyAuthorizationTests.test_builtin_role_grants_cannot_expand_protected_admin_or_hierarchy_access finlo.contrib.core.test_authorization.CompanyAuthorizationTests.test_role_manager_rejects_builtin_allow_blocked_by_role_policy finlo.contrib.core.test_authorization.CompanyAuthorizationTests.test_role_permission_changes_are_visible_to_other_loaded_users finlo.contrib.core.test_authorization.CompanyAuthorizationTests.test_role_manager_page_renders_permission_decisions_and_custom_scopes finlo.contrib.core.test_authorization.CompanyAuthorizationTests.test_custom_role_data_scope_defaults_to_deny_and_company_scope_is_tenant_bound finlo.contrib.core.test_authorization.CompanyAuthorizationTests.test_role_data_scope_endpoint_validates_role_and_supported_scope --settings=finlo.settings.security_test` | **7 passed, 0 failed, 0 errors, 0 blocked**, after the latest UI warning/test change. |
| `& .\.venv\Scripts\python.exe manage.py check --settings=finlo.settings.security_test` | Passed: no issues. |
| `& .\.venv\Scripts\python.exe manage.py makemigrations core --check --dry-run --settings=finlo.settings.security_test` | Passed: no unrepresented core model changes. |
| `git diff --check` | Passed. Git emitted only existing LF-to-CRLF normalization warnings for worktree files. |

### Real-browser check

The integrated Chrome browser used a file-backed SQLite database migrated locally through core 0014. Fixtures were synthetic and isolated; the browser server was not connected to PostgreSQL.

| UI/action | Observed result |
|---|---|
| Opened the Role Manager as a scratch Django superuser assigned to the scratch role | Role detail loaded; the superuser-bypass warning was visible. |
| Selected Allow for `leads.view_lead` | UI showed Allow; a separate process observed `member.has_perm(...) == True`, role grant present, and no role denial. The protected Lead list returned a list partial (HTTP 200). |
| Selected Deny for `leads.view_lead` | UI showed Deny; a separate process observed `member.has_perm(...) == False`, role grant absent, and role denial present. The Lead list returned “Permission Denied” with no list content (HTTP 200). |
| Selected Default | UI showed Default; a separate process observed `member.has_perm(...) == False`, with neither role grant nor role denial. |

The Allow/Deny checks exercised the protected Lead list in Chrome as the assigned non-superuser member. The Deny response's HTTP 200 status is recorded above as a separate semantics issue, not an authorization bypass.

### Migration rollback experiment

On the isolated SQLite file, one denial row, one scope row, and two assigned role members existed before migration reversal. Migrating core back to `0013_rename_remaining_user_m2m_columns` completed successfully. Afterward, `core_role_denied_permissions` and `core_roledatascope` were absent, both users remained assigned, and the historical `FinloUser.role` field reported `on_delete=CASCADE`. This confirms the downgrade is technically executable but intentionally not data-preserving for new policy data.

### Not verified

- No live PostgreSQL migration, write, or production record modification was performed.
- No migration was tested against a production-sized PostgreSQL clone or under the deployment's actual lock/timeout policy.
- Alternate/custom authentication backends, every protected endpoint/action, and every permission-sensitive cache surface were not exhaustively exercised.
- No custom roles existed in the read-only database, so the proposed compatibility mapping is not a data migration plan for current custom-role records.

## Approval gates before applying 0014

1. Approve the Django-superuser bypass policy for the two current SUPER_ADMIN accounts; do not change either account's flags without explicit authorization.
2. Approve the legacy-grant reconciliation policy and the required provenance/audit evidence. Until then, preserve all 2,280 direct grants.
3. Approve the custom-role scope policy, especially the conditional Campaign, OpportunityTeam, and Forecast mappings. Keep unapproved scopes at `deny_all`.
4. Approve a forward deployment/rollback plan that snapshots role grants, denials, scopes, direct grants, and role memberships. Do not reverse 0014 after policy data is in use without a separately approved data export/recovery plan.
5. Decide whether to harden the login-history dependency's missing-User-Agent handling and whether permission-denied HTMX responses should return an HTTP 403 status.

The only application-facing change in this continuation is the visible Django-superuser bypass notice and its regression assertion. No authorization logic, database migration, production record, commit, push, or deployment was changed/performed here.
