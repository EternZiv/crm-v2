# FINLONEXA CRM v2 — Six-Role Account Setup Plan

Status: NEEDS APPROVAL / BLOCKED for execution. Source inspection only; no account or role changes were made.

## Intended canonical roles

| Level | Role key | Display name | Parent |
|---:|---|---|---|
| 1 | SUPER_ADMIN | Super Administrator | None |
| 2 | HEAD_OF_SALES | Head of Sales | SUPER_ADMIN |
| 3 | RSM | Regional Sales Manager | HEAD_OF_SALES |
| 4 | SSM | Senior Sales Manager | RSM |
| 5 | ASM | Area Sales Manager | SSM |
| 6 | BDO | Business Development Officer | ASM |

The role model already defines protected canonical keys and validates the parent chain. Reconcile existing roles in the approved company scope; do not create duplicates. The live DB could not be checked.

## Proposed account names

These are proposals, not confirmed available usernames. Check collisions and existing ownership before creating or reusing accounts.

| Role | Proposed login ID |
|---|---|
| SUPER_ADMIN | finlo_superadmin |
| HEAD_OF_SALES | finlo_head_sales |
| RSM | finlo_rsm |
| SSM | finlo_ssm |
| ASM | finlo_asm |
| BDO | finlo_bdo |

Each account must belong to the approved company. The reporting links should use the existing SalesAssignment.manager relationship, with the BDO assigned to exactly one ASM. Region/team assignments must satisfy company and role validation. A role's parent does not itself assign users to one another.

## Permission and privilege rules

- Preserve the Dynamic Role Manager and explicit Allow/Deny/Default decisions.
- Required lead-create rule: allow SUPER_ADMIN, HEAD_OF_SALES, RSM, SSM, ASM; deny BDO.
- Current source and a focused existing test allow BDO lead creation. This conflicts with the requested matrix and needs an approved policy decision before implementation. Live Dynamic Role Manager state is unknown.
- Enforce existing company and hierarchy scopes.
- Keep Django is_superuser false unless a separately documented operational need justifies it. FINLO SUPER_ADMIN alone is not a reason to grant Django superuser.
- Grant is_staff only where an existing admin workflow requires it.
- Activate accounts only after owner setup and administrator verification.

## Credential setup and handoff

Do not use a shared password or derive one from personal information. After approval, generate independent high-entropy credentials. Prefer unusable passwords until each owner completes a single-use, time-limited Django setup/reset flow. Apply Django validators and set passwords through set_password.

Do not put plaintext credentials in source, Markdown, logs, MCP configuration, or chat. If secure one-time handoff is unavailable, use an administrator-operated interactive local setup command and deliver links through the approved email channel. Test email delivery with a disposable mailbox; do not message real users during acceptance.

## Execution gates

1. Establish an approved isolated database and confirm company scope.
2. Read current users, role keys, assignments, permissions, and username collisions without exposing hashes or tokens.
3. Decide which accounts are appropriate replacements; do not assume any account is disposable.
4. Resolve the BDO lead-create policy conflict and update focused tests only after approval.
5. Present the exact role/account/company/assignment/permission change list.
6. Obtain explicit approval for those changes before database writes.
7. Apply only in the approved environment and verify with isolated credentials.

Current blocker: development settings point to a remote Supabase pooler whose hostname did not resolve. No current account, role, assignment, or permission state is verified. No setup was executed.

## Updated verification status — 2026-11-14

The current configuration still points to the development-labeled settings with a remote Supabase transaction pooler. The host has the documented shared-pooler shape, but its project-specific pooler index was not verified. Windows denied both system DNS and direct public-resolver lookup, so current DNS failure cannot be attributed conclusively to an invalid project host or to this execution environment alone. Supabase says to copy the exact host from the project Connect dialog rather than compose it from region; see [connection documentation](https://supabase.com/docs/guides/database/connecting-to-postgres).

No username collision check, account lookup, role lookup, or assignment check was performed. The six proposed login IDs remain unverified for availability. The permission matrix remains NEEDS APPROVAL because current policy/test source allows BDO lead creation; the proposed code/test correction is documented in the authentication audit and has not been applied.

## Final preparation update — 2026-11-14

No local Django server is listening on port 8000. The only inspected isolated diagnostic settings use an in-memory SQLite database and are suitable for synthetic tests, not for discovering current Supabase accounts or username collisions. No authorized current-data connection is available in this session, so setup remains BLOCKED. DNS was not retried. The proposed BDO policy correction and focused test expectation are recorded in the authentication audit; no implementation or test change was made.
