# FINLONEXA CRM v2 — Old Account Cleanup Plan

Status: BLOCKED; no accounts were classified for deletion and none were changed. A safe read-only inventory could not be completed.

## Inventory limitation

Active development settings point to a remote Supabase PostgreSQL transaction pooler (database postgres, port 6543). DNS failed before a connection. Project identity and whether this database contains only test data could not be established. No account rows, assignments, owned records, sessions, audit references, workflows, scheduled tasks, or MCP/integration dependencies were queried.

Historical conversation context mentioned IDs/usernames 33/superadmin, 5/test_rsm, 6/test_asm, 7/test_sm, 8/test_se, and 9/admin. These are user-reported historical details only, not verified against the current database. They are not classified as obsolete or disposable and are not deletion candidates.

## Required read-only inventory before proposing removals

For each account in the explicitly approved environment, collect only necessary metadata (never password hashes, tokens, or session cookies):

- ID, username, active/staff/superuser flags, company and canonical/custom role.
- Service/bot/integration ownership and last-login metadata where relevant.
- Sales assignment, manager, region and team relationships.
- Counts of owned Leads, Accounts, Contacts, Opportunities, Activities, and other protected records.
- Foreign-key and generic-history/audit references, including cascade behavior.
- Workflow, scheduler/task, notification, and external integration references.
- Active session count/expiry and dependencies.
- Whether a replacement administrator and verified recovery path exist.

A test_ prefix or old account list is not proof that an account is disposable.

## Deletion impact and approval checkpoint

An exact deletion set cannot be proposed until inventory is available. Before any destructive operation, provide the administrator:

1. Exact environment/project identity and IDs/usernames.
2. Reason for each removal and evidence it is not a service or sole administrator account.
3. Dependent-record counts and cascade/protection consequences.
4. Approved reassignment or archival plan; preserve audit history.
5. Verified recoverable database backup and restoration procedure.
6. Replacement administrator access and tested recovery path.
7. Session revocation and integration impact plan.

Then request explicit approval naming the exact accounts. The current task requires stopping at this checkpoint; no disable, reassignment, session revocation, or deletion occurred.

## Safe cleanup sequence after separate approval

1. Reconfirm database identity and backup immediately before execution.
2. Reconfirm replacement administrator access and company-scoped role permissions.
3. Disable only explicitly approved obsolete accounts first, if approved, and revoke only their sessions.
4. Reassign or archive owned records exactly as approved; preserve audit records.
5. Check protected/cascade relationships and external integrations.
6. Permanently delete only named, approved accounts if soft retirement is insufficient.
7. Verify referential integrity, hierarchy, permissions, core records, and administrator recovery.
8. Record affected IDs without credentials.

No database writes, account changes, migrations, or cleanup actions were performed.

## Updated verification status — 2026-11-14

No deletion candidate can be named from current evidence. The database target is still not independently confirmed: configured development settings point at a remote Supabase transaction pooler, while system and public DNS requests were denied by Windows in this execution environment. Supabase documents this hostname pattern but says the exact shared-pooler host/index must be copied from the project Connect dialog; see [Supabase connection documentation](https://supabase.com/docs/guides/database/connecting-to-postgres). No DB connection, row query, session count, or dependency count was made.

The historical IDs/usernames above remain unverified leads only. Exact proposed deletion set: none at this stage. Account reset and cleanup remain BLOCKED until the project environment is confirmed, an authorized read-only inventory is completed, and the administrator approves an exact list after reviewing dependencies and backup/recovery evidence.

## Final preparation update — 2026-11-14

No local Django server is listening on port 8000. The repository's isolated security-test settings point to an in-memory SQLite database, which contains no authoritative current-account or dependency inventory. No authorized connection to the current Supabase project is available; no deletion candidate can be named. DNS was not retried. Cleanup remains BLOCKED and no account was disabled or deleted.
