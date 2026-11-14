# FINLONEXA CRM v2 — Smart Cache Runtime Acceptance

Date: 2026-11-14

## Executive result

**Overall status: BLOCKED.** No disposable Redis instance or isolated authenticated browser context was available. The configured Upstash Redis was not contacted or mutated. The previous Lead pilot's 27 focused tests are acknowledged as code-level evidence, but they do not establish Redis, multi-worker, browser, or performance acceptance.

No application code, cache settings, database data, server process, or Git history was changed for this acceptance pass. This report is the only new file.

## PASS / FAIL / BLOCKED matrix

| Gate | Result | Evidence |
|---|---|---|
| Disposable Redis availability | **BLOCKED** | No Docker, Podman, `redis-server`, or `redis-cli` executable was found on PATH; `fakeredis` is not installed. A loopback TCP probe was denied by the sandbox (`10013`), so it cannot establish whether a local listener exists. No approved disposable Redis endpoint was available. |
| Cross-worker reuse | **BLOCKED** | Requires a dedicated Redis cache and two independent Django processes. No Redis commands were run. |
| Cross-browser/session reuse | **BLOCKED** | Existing Chrome tabs include CRM sessions, but none is an isolated disposable context. They were left untouched. |
| User/company/effective-scope isolation | **PASS (static design and prior unit coverage); runtime BLOCKED** | Lead aggregate keys include user, company, revisions, and hashed query parameters. The previous focused 27-test suite covered key separation and revision invalidation, but no shared Redis isolation test ran in this task. |
| Committed mutation and cross-user invalidation | **BLOCKED at runtime** | Existing signals and bulk-update invalidation schedule revision bumps after commit. Cross-worker behavior, Redis persistence, and mutations made from another process were not exercised. |
| Redis outage invalidation recovery | **FAIL (durability gap confirmed in code)** | Revision bump callbacks catch/log cache errors. No durable record of a failed bump is written, so a cached result can become readable under the old revision after Redis returns, until the aggregate's five-minute TTL expires. |
| 30-second active-view scheduler | **BLOCKED in browser** | Source review shows a 30-second timer, visibility pause/resume, focus/online checks, request timeout, retry backoff, and revision-triggered page revalidation. No authenticated browser acceptance was performed. |
| FinloViewCache limits and lifecycle | **PASS (static inspection); runtime BLOCKED** | Source defines a 20-entry LRU cap and approximate 8 MiB budget, and retains skeleton guards. No browser test covered eviction, ECharts restoration, Back/Forward, or logout cleanup. |
| Cold/warm timings, SQL, payload, cache hit ratio | **BLOCKED** | No isolated Redis-backed application runtime or browser was available; no comparable measurements were collected. |
| Upstash TLS URL and namespace | **PASS (configuration metadata only)** | `.env` contains `CACHE_REDIS_URL`; a redacted parser confirmed `rediss`, an Upstash hostname, credentials present, and no database path. No values were printed. `CACHE_KEY_PREFIX` is absent, so the Vercel setting's `finlo-vercel` fallback applies. |
| Upstash logical DB index | **PASS for default DB 0 only; nonzero index BLOCKED** | The URL has no `/db` path, so the standard Redis URL default is DB 0. The application should keep using DB 0 and namespaces. No `SELECT` command or live connection was attempted; do not rely on a nonzero logical DB. |
| Upstash eviction/memory policy | **BLOCKED for the configured instance** | The instance's console policy and current usage were not inspected. Upstash documents that eviction is disabled by default and writes are rejected at the configured size limit; eviction can be enabled and uses its documented sampling policy. See [Upstash eviction documentation](https://upstash.com/docs/redis/features/eviction). |

## Infrastructure checks

- Local tool availability: no Docker/Podman/Redis server/client executable found on PATH; `redis` Python driver is installed, `fakeredis` is not.
- Loopback probe to `127.0.0.1:6379` returned Windows access-denied code `10013`, which is a sandbox restriction and not evidence of a Redis server's presence or absence.
- Browser inventory showed pre-existing CRM tabs. No isolated browser context or disposable authenticated identity was available; those tabs and sessions were not navigated or changed.
- The project `.env` was parsed only for presence and URL metadata. The configured cache URL is a `rediss://` TCP endpoint, not an HTTPS REST URL. Upstash documents TCP client URLs in `rediss://default:<token>@<endpoint>:6379` form and supports both native Redis TCP and HTTPS REST; Django's `RedisCache` here is configured for the TCP URL. See [Upstash TCP connection example](https://upstash.com/docs/redis/quickstarts/render) and [protocol compatibility](https://upstash.com/docs/redis/overall/compatibility).
- Upstash's current pricing documentation lists the Free plan's storage, command and bandwidth limits; those plan limits can change and were not used as a substitute for inspecting the configured database. See [current Upstash Redis pricing](https://upstash.com/pricing/redis).

The report intentionally does not reproduce a host, port, username, password, token, or raw connection string.

## Cache policy and five-minute TTL tradeoff

The deployed Vercel settings use Django `RedisCache`, a `CACHE_KEY_PREFIX` default of `finlo-vercel`, and a 300-second default timeout. The Lead aggregate service also applies a five-minute timeout. Lead result keys are revisioned; revision metadata has a bounded seven-day lifetime. The local development settings use `LocMemCache` and are not shared between workers.

The five-minute aggregate TTL bounds routine stale data and limits old revision generations, while allowing repeated authorized requests to reuse compact aggregates. A longer or indefinite data TTL could lower recomputation, but would increase Redis storage pressure and make missed invalidations more consequential. It is not justified until committed-mutation invalidation, eviction/restart behavior, and memory headroom are verified in a disposable shared Redis environment. **Do not remove the current TTL.**

Upstash's docs state that eviction is off by default and that writes are rejected when the configured data-size limit is reached. If enabled for a cache database, Upstash describes its current eviction behavior as `optimistic-volatile`, which may also evict non-TTL keys when needed. This makes random revision reinitialization important, but it does not prove the actual configured instance has eviction enabled. Inspect the Upstash console and establish an alert/headroom policy before relying on indefinite revision entries.

## Confirmed correctness gap and minimal durable recovery design

Current `bump_lead_cache_version()` and per-user revision updates are best-effort cache writes. Their exception handling keeps the business mutation successful if Redis is unavailable, but it also loses the invalidation event. A later Redis recovery can expose a previous aggregate under an unchanged revision until the 300-second aggregate entry expires. The service bypasses cache while revision reads fail, but does not detect a prior failed bump once Redis is reachable again.

Recommended durable design, **not implemented**:

1. Add a small database-backed resource-revision/outbox record keyed by company and resource, incremented in the same database transaction as the relevant Lead, assignment, hierarchy, and permission-scope mutation.
2. Build Redis aggregate keys from the authoritative revision. Either read the small revision row on requests or have a worker project it to Redis while requests fail closed when the projection is behind.
3. Drain pending revisions idempotently after Redis recovery; keep the revision row as the source of truth and Redis as a disposable projection.
4. Add isolated PostgreSQL and Redis outage/recovery tests before enabling longer retention.

This design requires a schema migration, which is outside authorization for this task. Do not add or apply one without approval. A shorter aggregate TTL could reduce the outage window, but it would not close the durability gap and was not changed here.

## Browser scheduler and view-cache source review

Static inspection confirms:

- One active-view interval is configured at 30,000 ms.
- The interval stops when the tab becomes hidden and restarts/checks when visible; focus and online events also trigger a check.
- Dashboard and Leads views use the authenticated `/crm/leads/cache-revision/` endpoint. Unchanged revision tokens do not trigger a full page fetch; changed tokens invoke the existing revalidation path.
- Requests use same-origin credentials, `cache: "no-store"`, a five-second abort timeout, and bounded retry delay.
- All-company scope returns `enabled: false`; this scheduler stops when it receives that response. This avoids pretending a single-company token covers a cross-company aggregate, but requires a browser acceptance check for administrator navigation and freshness behavior.
- FinloViewCache remains in-memory only with a 20-entry maximum and approximate 8 MiB maximum; oversized entries are skipped. Skeleton guards remain in place.

These are source observations only. Hidden-tab pause, restoration, unchanged-revision request behavior, selective data refresh, charts, history, and logout purge remain **BLOCKED** until tested in an isolated browser.

## Measurements

| Measurement | Result |
|---|---|
| Cold/warm request duration | **BLOCKED — no isolated Redis-backed runtime** |
| SQL count/time on cache hit vs miss | **BLOCKED — no safe runtime baseline** |
| Cache hit/miss and Redis command counts | **BLOCKED — no disposable Redis metrics** |
| Cross-process request result | **BLOCKED — no two-worker Redis setup** |
| Response bytes/payload reduction | **BLOCKED — no comparable browser/server capture** |
| Click-to-skeleton / click-to-usable | **BLOCKED — no isolated browser identity** |
| Redis memory/eviction headroom | **BLOCKED — configured Upstash console state not inspected** |

No timings or performance improvements are claimed in this report.

## Minimal remediation and next acceptance steps

1. Provide a dedicated disposable Redis endpoint or local Redis service with a separate key prefix. Confirm it is not the production Upstash database. Keep DB 0 and set an isolated key namespace.
2. Provide an isolated authenticated browser identity/context and test database. Avoid the existing browser tabs.
3. Run bounded cross-worker/cross-session cache-hit and scope-isolation tests, including Lead assignment/company transfers, direct and role permission changes, bulk update, Redis restart/eviction, and outage recovery.
4. Check the configured Upstash database's eviction status, storage usage, and plan limits in its console without exposing credentials. Keep the aggregate TTL at 300 seconds for these tests.
5. For durable recovery, request approval for the minimal database revision/outbox migration described above; until then, treat Redis outage during revision writes as a known bounded-staleness risk.
6. Run the browser scheduler checks (30-second active poll, unchanged token, changed token, hidden pause, focus restore, session expiry, and all-company behavior), then test FinloViewCache entry/byte eviction, skeleton exclusion, chart disposal/reinitialization, Back/Forward, and logout cleanup.
7. Capture equivalent cold/warm TTFB, usable time, SQL count/time, response bytes, Redis commands/hits, and requests avoided. Do not compare a cold baseline against a warm hit as if it were an optimization delta.

## Safety record

- No production Upstash commands were run.
- No database records, accounts, credentials, roles, permissions, migrations, or settings were modified.
- No server was started or restarted.
- No CRM browser tab was navigated, logged out, or altered.
- No commit, push, deployment, or application-code change was made.
