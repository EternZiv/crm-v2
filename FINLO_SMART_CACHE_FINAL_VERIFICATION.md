# FINLONEXA CRM v2 — Smart Cache Final Verification

Date: 2026-11-14

## Outcome

**Overall: BLOCKED for runtime acceptance; NO-GO for production acceptance.** The Lead Smart Cache pilot remains limited to Leads and retains its current five-minute aggregate TTL. Prior focused tests and code review support the design, but no disposable Redis service or isolated authenticated browser was available to prove cross-process reuse, runtime invalidation, or browser freshness behavior. No application code, settings, database, Redis instance, or user data was changed for this verification.

## Acceptance matrix

| Gate | Status | Evidence / limitation |
|---|---|---|
| Lead cache implementation and existing focused tests | **PASS (prior code-level evidence)** | The prior isolated run passed 27 focused tests in `finlo_crm.leads.tests.test_analytics_service` using `finlo.settings.security_test`. The tests cover scoped keys, permission rechecks, revision loss/reinitialization, invalidation scheduling, bulk-update hooks, and endpoint authorization. They do not prove real Redis or PostgreSQL transaction behavior. The suite was not rerun in this acceptance. |
| Disposable Redis availability | **BLOCKED** | No Docker/Podman or Redis server/client executable was available on PATH; `fakeredis` is not installed. A loopback connection probe was denied by the sandbox (`10013`), so that probe cannot establish whether a local Redis listener exists. No disposable Redis endpoint was available. Production Upstash was not contacted. |
| Redis serialization, shared keys, TTL, atomic revisions, interruption and reconnect | **BLOCKED** | No real Redis was available. The application uses random revision tokens with cache `set`/`add`, rather than an atomic monotonic increment; concurrency, expiration, and reconnection semantics have not been exercised against a real backend. |
| Cross-worker aggregate reuse | **BLOCKED** | No two independent Django processes shared a disposable Redis backend. Cache hits, misses, SQL avoided, and exact result reuse across workers were not measured. |
| Cross-browser/session reuse | **BLOCKED** | The user-scoped key design permits a new session for the same identity to reuse a valid Redis entry after normal authentication and permission checks. No isolated browser identity or Redis runtime was available to demonstrate this. Existing CRM browser sessions were left untouched. |
| User/company/effective-scope isolation | **PASS in prior focused unit coverage; runtime BLOCKED** | Keys include user, effective company, global/company revisions, user authorization revision, and hashed query parameters. The service rechecks current Lead read permission before returning cached results; all-company aggregate requests without a single company scope are not cached. Prior unit coverage is not a Redis isolation test. |
| Cross-user mutation invalidation and transaction behavior | **PASS in prior focused tests/code review; PostgreSQL integration BLOCKED** | Lead and LeadStatus hooks use `transaction.on_commit`; Lead transfer invalidation covers old and new companies. Role, user, hierarchy, direct-permission, and bulk-update paths have targeted coverage. Real commit/rollback ordering, cross-worker visibility, and concurrent mutations were not exercised on disposable PostgreSQL + Redis. |
| Redis outage recovery | **FAIL — known durability gap** | Revision bump errors are logged and swallowed so business writes are not failed by cache downtime. The failed revision is not durably recorded. After Redis returns, an old aggregate can remain addressable under its old revision until its 300-second TTL expires. Cache reads bypass while Redis is currently unavailable, but this does not recover an invalidation lost during the outage. |
| 30-second active-view revalidation | **PASS by source inspection; browser runtime BLOCKED** | One scheduler is configured at 30,000 ms, pauses while hidden/offline, checks on focus/visibility/online, coalesces an in-flight revision request, times out after five seconds, and applies bounded backoff. Dashboard/Leads use the authenticated no-store revision endpoint; unchanged revisions do not trigger full data refresh. No browser run verified timer count, request counts, focus restoration, selective refresh, or session-expiry behavior. |
| All-company Dashboard revalidation | **BLOCKED / known limitation** | The current single-company Lead revision endpoint returns `enabled: false` for an all-company scope, and the scheduler stops. This avoids treating one tenant revision as authoritative for a cross-company aggregate, but leaves active all-company views without this revision poll. No new endpoint was added. |
| FinloViewCache size, LRU and guards | **PASS by source inspection; browser runtime BLOCKED** | The cache is tab-memory only, capped at 20 entries and approximately 8 MiB, uses LRU eviction, rejects oversized entries, and retains skeleton/incomplete-content guards. Runtime eviction, URL/content alignment, scroll, Back/Forward, chart lifecycle, logout cleanup, and permission-context invalidation were not browser-tested. |
| Channels resource-change notifications | **NOT IMPLEMENTED** | No resource-change broadcast was added. Existing notification Channels behavior remains unchanged; 30-second polling is the current Lead/Dashboard freshness mechanism. |
| Cold/warm performance, SQL, payload and memory | **BLOCKED** | No equivalent disposable Redis-backed application requests or browser measurements were collected. There are no verified hit/miss counts, Redis command counts, SQL deltas, response sizes, memory headroom, or click-to-usable timings. No performance gain is claimed. |
| Production provider metadata | **PASS for redacted configuration shape only; account policy BLOCKED** | The prior redacted inspection found a `rediss://` Upstash TCP URL, no explicit DB path (thus default DB 0), and Vercel's Django Redis cache prefix fallback `finlo-vercel`. No raw URL or credential was displayed and no connection was attempted. The actual Upstash database's configured eviction policy and memory use were not inspected. |

## Existing cache behavior confirmed by focused inspection

- `LeadDataService` uses compact aggregate results, request-local reuse, Django's configured cache interface, a five-minute result TTL, and keys containing user/company/data and authorization revisions plus filter/date parameters.
- The local base settings use process-local `LocMemCache`; that backend cannot demonstrate cross-worker sharing. Vercel settings select Django `RedisCache`, require the configured Redis URL, use the `finlo-vercel` key-prefix fallback, and default to 300 seconds.
- Lead/LeadStatus and relevant user/role/hierarchy changes schedule invalidation after transaction commit. The Lead API's queryset bulk-update path has explicit invalidation because it bypasses model save signals.
- Current read permission is checked before returning cached Lead data. Cache errors cause an authorized query path rather than trusting an unavailable revision.
- Revision metadata uses a bounded seven-day lifetime and random tokens. Missing metadata is initialized with a new random token so a prior result generation does not become current merely because a revision key disappeared.
- The browser snapshot store is in-memory only; protected HTML is not persisted in localStorage, sessionStorage, or IndexedDB.

## Redis provider and retention notes

The inspected cache URL uses the Redis TCP protocol with TLS (`rediss://`), not Upstash's HTTPS REST interface. The configured URL has no logical database path, so it selects DB 0. Keep DB 0 and isolate environments with distinct application key prefixes; nonzero logical DB support was not tested. Upstash documents native Redis TCP and REST as separate interfaces ([TCP connection example](https://upstash.com/docs/redis/quickstarts/render), [protocol compatibility](https://upstash.com/docs/redis/overall/compatibility)).

Upstash documents eviction as disabled by default, with writes rejected when configured storage is full; where enabled, its documented policy can evict TTL and non-TTL keys ([eviction documentation](https://upstash.com/docs/redis/features/eviction)). This does not establish the policy or headroom of FINLO's configured instance. Check those in the provider console before depending on retained revision keys. Do not run stress or eviction tests against production Upstash.

Keep the aggregate TTL at **300 seconds**. It bounds normal result retention and limits accumulation of old revision generations. Longer or indefinite retention would reduce recomputation but magnify the impact of missed invalidations and increase memory pressure. It is not justified until mutation invalidation, Redis restart/eviction behavior, and memory limits pass isolated runtime tests. The TTL is not a correctness substitute for durable invalidation.

## Minimal durable Redis-outage recovery proposal

No migration or code change was made. The smallest robust direction is an authoritative database revision row updated in the same database transaction as each affected Lead/resource mutation. Redis remains a disposable projection/cache.

1. Add a table keyed by company and resource (or a narrowly scoped transactional outbox row) with a monotonic revision. Update it in the same transaction as Lead, assignment, company-transfer, hierarchy, and relevant authorization-scope changes.
2. Ensure cache reads cannot trust a stale Redis generation while the projection is behind. The straightforward safe option is to read the small authoritative revision before choosing the aggregate cache key. An outbox worker can project/replay revisions to Redis idempotently, but a request must fail closed or consult the DB if pending work exists.
3. For company transfers, advance both old and new affected company scopes. Keep user authorization revisions covered by the authoritative mechanism or ensure their changes invalidate the relevant shared scope.
4. On Redis recovery, replay pending projections idempotently. A missing Redis revision must be rebuilt from the database revision; it must never make an old aggregate trusted.
5. Validate concurrency, commit/rollback, bulk updates, worker restart, Redis outage/recovery, and permission revocation with disposable PostgreSQL and Redis before adoption.

This requires a schema migration and adds a small database read or projection-consistency check to cache lookups, plus worker/replay operational responsibility if an outbox is selected. The migration and production behavior require separate approval. A shorter TTL only shortens the stale window; it does not make invalidation durable.

## Remaining acceptance steps

1. Provide a disposable Redis service or endpoint on DB 0 with a unique test prefix; do not use production Upstash.
2. Provide a disposable PostgreSQL database for commit/rollback and mutation integration tests.
3. Run bounded two-process tests for serialization, cache reuse, key isolation, revision updates, worker restart, Redis interruption/recovery, and SQL avoided.
4. Provide an isolated authenticated browser context to test the 30-second scheduler, hidden/focus/offline behavior, unchanged and changed revisions, session expiry, cache bounds, skeleton guards, charts, history and logout cleanup.
5. Verify the configured Upstash database's actual memory and eviction policy in its console without exposing credentials.
6. Decide separately whether to approve a database-backed revision/outbox migration. Keep the current five-minute TTL until both durable invalidation and memory bounds are verified.

## Safety and rollback

This acceptance made **no source/configuration changes** and ran no test suite. No database, live Redis, accounts, roles, permissions, migrations, browser sessions, or running server were modified. There is no code rollback to perform. The proposed durable revision change remains unimplemented and must not be applied without migration approval.

If a later change is approved, keep rollback limited to that change: revert its application/service updates and migration only under an approved database rollback plan. Do not clear shared Redis or delete cache keys as a generic rollback step; existing aggregate keys expire within five minutes and revision metadata within seven days.

## Final decision

**NO-GO for production acceptance.** Code-level Lead cache behavior and prior focused tests are encouraging, but cross-worker Redis reuse, Redis outage recovery, PostgreSQL transaction semantics, active browser revalidation, browser-cache lifecycle, provider memory/eviction state, and performance remain unverified. Keep the pilot scoped to Leads and preserve the five-minute TTL while the isolated runtime gates are completed.
