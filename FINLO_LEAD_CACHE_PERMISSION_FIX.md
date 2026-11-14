# FINLONEXA CRM v2 — Lead Cache Permission Fix

Date: 2026-11-14

## Result

**PASS for the focused permission regression tests; BLOCKED for authenticated PostgreSQL/browser performance verification.** This was an actual missing cache-hit permission guard, not merely a stale test. The test also referenced the intended `_can_read_leads` method, which did not exist in the current implementation.

## Root cause and behavior

`LeadDataService` built an authorization-scoped queryset with `get_queryset_for_module(user, Lead)` only when computing an aggregate on a cache miss. KPI, stage-count, and source-count cache hits returned before that queryset and its company/owner scope were evaluated. Signal-based revision invalidation was intended to invalidate permission changes, but cache-hit correctness relied on those invalidations having already succeeded; it did not independently recheck the current effective Lead read permission.

The failing `test_permission_revocation_prevents_returning_cached_kpi` attempted to patch `LeadDataService._can_read_leads`, but the method was absent. That `AttributeError` prevented the test from evaluating the security behavior.

## Fix implemented

Added `LeadDataService._can_read_leads()` and invoked it before request-local or shared cache access for all three Lead aggregate methods. It denies unauthenticated and inactive users, allows active Django superusers, and otherwise checks the existing effective permissions `leads.view_lead` and `leads.view_own_lead` through `has_effective_permission`.

Denied calls return the existing empty-data shapes: zero KPI values or an empty aggregate list. The cached entry is not deleted; it simply cannot be returned to a caller who no longer has read permission. Authorized cache misses still use `get_queryset_for_module`, preserving company and sales-hierarchy filtering. Cache/revision failures continue to fall back to that authorized queryset path. The guard does not depend on the browser's 30-second scheduler.

## Files changed

- `finlo_crm/leads/services.py` — current effective permission guard before KPI, stage and source cache lookups.
- `finlo_crm/leads/tests/test_analytics_service.py` — replaced the broken patch-only case with observable cache-hit/revocation coverage and added authorized-hit, cross-company separation, stage/source denial, and cache-error fallback cases.
- `FINLO_LEAD_CACHE_PERMISSION_FIX.md` — this report.

No cache TTL, revision scheme, database schema, frontend behavior, or production setting was changed.

## Verification

Requested focused suite:

```text
.venv\Scripts\python.exe manage.py test finlo_crm.leads.tests.test_analytics_service finlo.contrib.dashboard.test_request_reuse finlo.contrib.core.test_auth_hardening --settings=finlo.settings.security_test
```

**PASS: 49 tests in 4.291 seconds; Django system checks reported no issues.** Coverage verifies:

- An authorized caller receives the cached KPI without rebuilding the queryset or re-running the aggregate.
- A caller who loses effective read permission receives zero values while the old cache entry remains physically present.
- Another company/user scope gets a different key and computes its own result rather than reading the first user's value.
- Denied callers cannot receive cached stage/source aggregates.
- Cache revision errors fall back to an authorized scoped queryset.
- Existing Lead cache, dashboard request-reuse, and authentication/RBAC unit tests pass.

`py_compile` passed for both modified Python files. `git diff --check` reported no whitespace errors (Git emitted only line-ending normalization warnings).

The separate Dashboard query-count integration tests were attempted under `security_test`, but the test runner remained at `Creating test database for alias 'default'...` for about one minute without reaching test execution. Only that test process was stopped. Therefore current SQL counts and database-level performance impact are **BLOCKED**. The earlier Dashboard/Leads measurements remain historical; this authorization guard adds a permission evaluation before cache hits, and its SQL cost was not measured here. The authorized-hit test confirms it does not re-run the aggregate itself.

Authenticated browser verification and live PostgreSQL/Redis checks were not performed. No server, browser session, production database, or Redis service was touched.

## Remaining risks

- The guard prevents serving cached aggregates when current effective Lead read permission is denied. Company and sales-hierarchy data scope on cache misses remains enforced by the existing scoped queryset; invalidation for a still-authorized user's scope change still depends on revision updates. The previously documented Redis-outage invalidation durability gap remains unresolved.
- Measure the permission guard's query cost with an approved authenticated runtime and compare cache-hit SQL counts before/after. Preserve the permission guard even if that requires targeted batching/caching of permission evaluation.
- The dashboard integration test database-creation stall needs a separate focused diagnosis if SQL-count acceptance is required.

## Rollback

To revert this specific fix, remove `_can_read_leads()` and its three pre-cache guards from `finlo_crm/leads/services.py`, then restore the original failing test only if intentionally abandoning this security coverage. Do not revert unrelated existing worktree changes. The recommended operational choice is to retain the guard; no migration or data rollback is needed.
