# FINLONEXA CRM v2 — Unified Smart Cache Results

Date: 2026-11-14

## Outcome

The Lead cache pilot has focused hardening for cache-key scope, revision loss, permission checks, mutation invalidation, active-view freshness checks, and browser snapshot memory bounds. It is **not production accepted**: no disposable shared Redis or isolated authenticated browser/Channels runtime was available, so cross-worker behavior, Redis limits, WebSocket invalidation, browser timing, and performance gains remain **BLOCKED/NOT TESTED**.

## Phase status

| Phase / gate | Status | Result |
|---|---|---|
| Existing-system cache audit | **PASS (focused code review)** | Local settings use LocMemCache; Vercel settings use Django RedisCache with TLS URL validation, `CACHE_REDIS_URL`, configurable key prefix (default `finlo-vercel`), and a 300-second default timeout. Channels and Celery use separately configured Redis URLs. |
| Shared Lead aggregate cache | **PASS in isolated backend / BLOCKED on Redis** | Existing `LeadDataService` remains the single service for KPI, stage and source aggregates. Data results are compact values, user and company scoped, and have a bounded 300-second TTL. Development LocMemCache is process-local and is not evidence of cross-worker reuse. |
| Cache key and authorization scope | **PASS in code/tests** | Keys include user, company, global and company revisions, user authorization revision, and hashes of filters/date parameters. All-company requests without a single explicit company are left uncached. Current Lead read permission is checked before returning any cached result. |
| Revision loss/reinitialization | **PASS in unit tests** | Missing revision keys are initialized with random tokens, preventing an old result key from becoming current after metadata eviction/restart. Revision metadata has bounded seven-day retention; result generations expire within five minutes. Cache access failure bypasses shared results and executes the authorized query. |
| Lead/LeadStatus invalidation | **PASS in focused tests/code** | Lead create/edit/delete, reassignment, and company transfer bump revisions after commit; transfers cover old and new companies. LeadStatus changes invalidate affected tenant revisions. |
| Role, user, and hierarchy invalidation | **PASS in focused tests/code** | Existing role, role-data-scope, direct permission/group, and user role/company hooks remain. Added SalesRegion/SalesTeam/SalesAssignment invalidation after commit, including old/new company on transfers, because these rows affect sales hierarchy scopes. |
| Bulk mutation invalidation | **PASS in focused test** | Lead API bulk updates use queryset `.update()` and bypass model signals. Successful bulk updates now schedule revision invalidation after commit; bulk deletes continue through Django delete signals. |
| Shared cross-browser reuse | **PASS by key design / BLOCKED at runtime** | Entries are user-scoped, not browser-session scoped, so a new session for the same user can reuse data when backed by shared Redis. No Redis instance was used to prove this. |
| Cross-worker stampede prevention | **NOT TESTED / NOT IMPLEMENTED** | Request-local deduplication remains. No distributed lock was added without a safe Redis test because a lock outage/expiry race could stall requests or duplicate work. |
| Active 30-second revalidation | **PASS in code / BLOCKED in browser** | A single visible-tab scheduler runs at 30 seconds, pauses while hidden/offline, checks on focus/visibility/online, and backs off after failures. Dashboard/Leads use an authenticated, private/no-store revision endpoint and fetch full content only after a revision changes. Other eligible views use existing SWR behavior. |
| Channels resource-change events | **BLOCKED / NOT IMPLEMENTED** | Existing authenticated notification Channels behavior is unchanged. No company-wide resource event was added without an isolated Redis/Channels acceptance environment. The 30-second revision polling is the current fallback. |
| FinloViewCache bounds | **PASS in static/syntax checks** | Snapshots remain in-memory only, with existing user/company scope checks and skeleton guards. Added a 20-entry LRU and approximate 8 MiB budget. Age is a freshness/SWR threshold, not an age-based eviction. |
| Skeleton and charts | **NOT TESTED in browser** | Existing skeleton guards and chart lifecycle were not rewritten. No browser session was available for Dashboard/Leads chart, filter, restoration, layout-shift, or stuck-skeleton acceptance. |
| Performance acceptance | **BLOCKED** | No comparable before/after Redis hits, SQL counts, timings, payload sizes, browser click-to-skeleton/usable timing, or eviction/memory metrics were available. No performance improvement is claimed. |
| Broader Accounts/Opportunities/Reports rollout | **NOT TESTED** | The implementation remains limited to the existing Lead data service pilot; no additional modules were migrated. |

## Cache architecture and configuration

### Previous state

- `LeadDataService` already aggregated KPI, stage, and source data and cached results through Django's configured cache interface.
- Keys were already user-oriented and mutations already used `transaction.on_commit()` for the primary Lead/LeadStatus signals.
- Local development/test settings use `LocMemCache` with `MAX_ENTRIES=10000`, culling, and a one-day default timeout. It is not shared across workers.
- Vercel settings select Django's `RedisCache` using `CACHE_REDIS_URL`, require `rediss://`, allow a `CACHE_KEY_PREFIX` (default `finlo-vercel`), and set a 300-second default timeout. Channels and Celery have separate Redis URLs.
- `FinloViewCache` was a tab-memory `Map`, limited to 20 pages and protected by session-scope checks/skeleton guards, but it had no approximate byte budget. Its 20–30 second “TTL” was used as an SWR refresh threshold; entries were not removed by age in `get()`.

### Current Lead pilot

- Aggregate data remains user-scoped. The key includes the effective company, global and tenant data revisions, per-user authorization revision, resource name, and a hash of filter/date parameters.
- All-company results without an explicit tenant are not cached, avoiding a single-company invalidation scheme being mistaken for a global one.
- Revision tokens are random; missing/evicted metadata creates a new generation. Metadata retention is seven days, while aggregate values remain bounded to 300 seconds. Old revision generations therefore age out without indefinite value-key accumulation.
- A cache read/write/revision error degrades to an authorized database query rather than failing the CRM request or trusting an unknown generation.
- Before a cached aggregate is returned, the service checks that the current user remains active and has an effective Lead read permission. The scoped queryset still applies company and sales hierarchy rules on cache misses.
- The revision endpoint exposes only a small token for the authenticated user's authorized company scope; it is `private, no-store`, checks Lead view permission, returns 401/403 where appropriate, and does not return record data. All-company scope is explicitly unsupported by this single-company token and is not cached by the service.
- The browser scheduler only checks the active visible view. It coalesces requests, pauses on hidden/offline tabs, times out checks after five seconds, applies bounded backoff, and revalidates the current route when the token changes. A 401 clears protected view snapshots and reloads so the server handles session expiry.
- The browser snapshot cache stays tab-memory only, evicts least-recently-used entries above 20 pages or approximately 8 MiB, and skips an individual snapshot larger than the budget.

## Exact files modified

- `finlo_crm/leads/services.py`
- `finlo_crm/leads/signals.py`
- `finlo/contrib/core/signals.py`
- `finlo_crm/leads/api/views.py`
- `finlo_crm/leads/views/core.py`
- `finlo_crm/leads/views/__init__.py`
- `finlo_crm/leads/urls.py`
- `static/assets/js/navigation_history.js`
- `finlo_crm/leads/tests/test_analytics_service.py`
- `FINLO_UNIFIED_SMART_CACHE_RESULTS.md`

No settings, credentials, database schema, migrations, business data, Celery configuration, or Channels configuration were changed.

## Targeted verification

- `manage.py test finlo_crm.leads.tests.test_analytics_service --settings=finlo.settings.security_test`: **27 passed**. Uses the isolated security-test configuration and local-memory cache; no live database writes.
- `manage.py shell ... reverse('leads:cache_revision')`: **PASS**, resolved to `/crm/leads/cache-revision/`.
- `manage.py check --settings=finlo.settings.security_test`: **PASS**, no issues.
- `node --check static/assets/js/navigation_history.js`: **PASS**.
- `py_compile` for the modified Python modules: **PASS**.
- `git diff --check`: run in the final verification; line-ending warnings may be reported for pre-existing modified files.

The focused tests cover user/company key separation, revision reinitialization, global and company invalidation, cache outage fallback, current permission revocation before a cache hit, Lead company transfer/deletion, role and scope invalidation, hierarchy company transfers, bulk-update revision scheduling, and authorized/denied revision endpoint responses.

## Measurement and production acceptance limits

There is no valid Redis hit/miss or before/after performance comparison from this environment. The SQLite security test configuration uses LocMemCache; it does not demonstrate Redis serialization, shared state between processes, Upstash DB-index behavior, TLS connectivity, eviction policy, memory headroom, or concurrent contention. The production Upstash instance was not used because no disposable Redis namespace/service was established.

No authenticated isolated browser was used. Therefore, no 30-second refresh, Chart/ECharts restoration, repeated-request count, click-to-skeleton, click-to-usable, or protected-content behavior is claimed as browser-verified. Resource-change WebSocket broadcasts are not wired; polling is the implemented fallback. The cache outage path bypasses shared reads, but an invalidation callback that fails while Redis is unavailable cannot durably record the new revision. Since the database remains authoritative and no durable revision table exists, that exceptional outage window remains a production risk until tested/mitigated with the actual cache infrastructure.

The Redis URL parser does not enforce a provider DB number. Confirm the deployed Upstash endpoint uses its supported database (normally DB 0) and configure a unique key prefix per environment. Do not assume the Upstash REST URL/token is a Django Redis protocol URL; Django `RedisCache` needs a compatible Redis connection URL. No secrets were read or printed in this task.

## Rollback

To roll back this pilot, revert only the changes in the nine code/test files listed above, preserving unrelated worktree changes. Remove the `cache-revision/` route and its JavaScript polling together. Keep existing Django cache settings and any other in-progress user changes untouched. Do not clear shared Redis or reset any data as part of rollback; old aggregate values expire within five minutes, and revision metadata expires within seven days.

## Production decision

**NO-GO for production acceptance.** The code-level Lead pilot and focused tests pass, but shared Redis, multi-worker invalidation, Channels events, browser behavior, and comparable performance remain unverified. Keep the broader module rollout paused until those runtime gates are exercised with dedicated non-production infrastructure and an isolated browser identity.
