# FINLONEXA CRM v2 — Isolated Smart Cache Acceptance

Date: 2026-11-14

## Result

**Overall: BLOCKED at environment preflight. Production acceptance remains NO-GO.** The required disposable Redis and PostgreSQL infrastructure is not available in the current environment. Per the safety requirements, no service was installed or provisioned, no migrations or integration tests were started, and production Supabase/Upstash were not contacted.

## Phase 0 — Environment preflight

| Item | Status | Finding |
|---|---|---|
| Docker Desktop / Docker Compose | **BLOCKED** | `docker` and `docker-compose` are unavailable on PATH. |
| Podman | **BLOCKED** | `podman` is unavailable on PATH. |
| Local Redis server/client | **BLOCKED** | `redis-server` and `redis-cli` are unavailable on PATH. `fakeredis` is not installed. The Python `redis` client is installed, but a client library alone does not provide an isolated Redis service. |
| PostgreSQL server/client | **BLOCKED** | `postgres` and `psql` are unavailable on PATH. No disposable PostgreSQL endpoint was provided. Port inspection could not establish listener state in this sandbox; no endpoint was assumed safe. |
| Project Python environment | **PASS (availability only)** | `.venv\Scripts\python.exe` exists; psycopg2 is installed. This does not establish safe database connectivity. |
| Django isolated settings | **PASS for prior unit tests; insufficient for runtime integration** | `finlo.settings.security_test` pins the database to in-memory SQLite and omits Daphne. Base settings still use `LocMemCache`; this cannot prove Redis sharing or PostgreSQL transaction semantics. It is not a Redis/PostgreSQL integration profile. |
| Browser automation | **BLOCKED** | Playwright is not installed. No isolated authenticated browser context was established. Existing CRM sessions were not accessed or changed. |
| Safe test identities and data | **BLOCKED** | No disposable PostgreSQL database exists in which to create synthetic users and CRM fixtures. No live identities or records were used. |

### Isolation assessment

The existing security-test settings safely isolate prior authorization/unit tests from Supabase by using SQLite `:memory:`. However, they do not configure a disposable Redis cache, isolated Channels/Celery endpoints, or a test email backend. They inherit the base LocMemCache and application integration settings. Therefore they cannot be repurposed for this task's runtime tests without a dedicated, explicit test configuration and verified local/approved services.

The preflight did not inspect, print, or use production credentials. It did not connect to production Supabase or Upstash. No isolated infrastructure definition or Django settings module was created because no permitted local runtime was available to validate it against.

## Runtime acceptance gates

| Gate | Status | Reason |
|---|---|---|
| Real Redis serialization, TTL, revision keys, restart/reconnect, eviction | **BLOCKED** | No disposable Redis service. |
| Two-process cache reuse and SQL avoided | **BLOCKED** | No Redis service to share between independent Django workers. |
| User/company/effective-scope isolation against Redis | **BLOCKED** | Prior 27 focused tests provide unit-level evidence only; no shared backend or synthetic database fixtures. |
| New browser session reuse | **BLOCKED** | Requires both isolated identity/session and shared Redis. |
| PostgreSQL commit, rollback, concurrency, assignment/company transfer, and permission invalidation | **BLOCKED** | No disposable PostgreSQL service. The SQLite unit settings are not evidence of PostgreSQL transaction behavior. |
| Redis outage/recovery reproduction | **BLOCKED** | Requires disposable Redis plus PostgreSQL. The known best-effort invalidation gap remains confirmed by code inspection from prior acceptance. |
| 30-second scheduler and navigation cache browser tests | **BLOCKED** | No isolated browser context or runtime endpoints. No existing browser session was disturbed. |
| Comparable backend/browser performance measurements | **BLOCKED** | No safe runtime; no cache-hit, SQL, payload, or browser timings were collected. |

The prior 27 focused Lead cache tests remain the only test evidence. They were not rerun because the environment gate prevents the requested real-service acceptance and no application code changed.

## Existing design limits retained

- Lead aggregate TTL remains **300 seconds**; revision metadata remains bounded at seven days.
- Local development cache is `LocMemCache`, which is process-local. Vercel's configured Django Redis cache was not contacted.
- The all-company Dashboard scope is not represented by the current single-company revision token; the browser scheduler stops when it receives `enabled: false` for that scope.
- Resource-change Channels broadcasts remain unimplemented; 30-second polling is the current Lead/Dashboard freshness path.
- If a database mutation commits while Redis revision invalidation is unavailable, the failed invalidation is not durably queued. After Redis recovers, a prior aggregate may be addressable until its five-minute TTL expires.

No code or configuration was changed to mask these limitations.

## Safe next step

Provide an already available disposable PostgreSQL database and Redis service, or make approved local container tooling available. Before any test run, establish and record:

1. PostgreSQL host is loopback or explicitly approved, with a separate database and test-only credentials.
2. Redis host is loopback or explicitly approved, using DB 0 and a unique test key prefix.
3. Dedicated Django test settings explicitly point the database, cache, Channels, and Celery to isolated services; email uses an in-memory/local backend; outbound integrations are disabled.
4. The application test process cannot inherit production service endpoints or secrets.
5. Synthetic fixtures are created only in the disposable PostgreSQL database.

Only after those checks should existing migrations be applied to that disposable database and the bounded Redis/PostgreSQL tests be run. No such setup was attempted here.

## Files and cleanup

- Added: `FINLO_SMART_CACHE_ISOLATED_ACCEPTANCE.md`.
- No application files, settings, dependencies, environment variables, database records, Redis keys, browser sessions, or running services were modified.
- No cleanup or rollback is required because no infrastructure was created.

**Final decision: BLOCKED / NO-GO.** Real Redis, PostgreSQL transaction, cross-worker, browser, and performance acceptance must remain unclaimed until isolated infrastructure is available and the corresponding tests pass.
