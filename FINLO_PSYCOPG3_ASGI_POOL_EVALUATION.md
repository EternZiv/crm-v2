# psycopg3 ASGI pool evaluation

## Latest acceptance continuation

- SQLite authorization run with isolated psycopg3 imports: 33/33 PASS in 226.983s. This is not PostgreSQL transaction compatibility evidence.
- Authenticated read-only requests used existing active test_superadmin with an ephemeral signed-cookie session, no live session creation, and an SQL guard blocking non-SELECT/SHOW/SET statements.
- Initial 302 samples omitted required section query parameters and are INVALID for page performance; canonical query parameters corrected this.
- Pooled canonical Dashboard: 200, median 3.421s/max 14.400s, queries 52 cold and 11 warm.
- Pooled canonical Leads: 200, median 1.804s/max 2.224s, 21 queries each.
- Pooled canonical Accounts: 200, median 2.429s/max 2.437s, 20 queries each.
- Pooled canonical Opportunities: first two samples 200 at 3.588s and 3.955s, 30 queries each. Third did not complete within the observation period. Driver-matched baseline also stopped producing output. Only these experiment sessions were interrupted; active CRM was untouched. No completed equivalent route comparison is claimed.
- The asyncio request timeout did not provide a reliable whole-process bound for synchronous database work/cancellation. A future harness needs an external process deadline and per-statement bounds. Root cause of this stall is not established.
- ASGI health-under-saturation, idle expiry, company/session isolation and browser comparison remain NOT RUN/BLOCKED. Disposable PostgreSQL fixture remains unavailable for write/rollback acceptance.

Decision remains NO-GO. Anonymous performance improvement is insufficient and authenticated routes still exceed one second in these samples.

## Additional adoption checks

`pool_acceptance.py` held two connections and attempted a third acquisition with a 0.5-second deadline. It raised PoolTimeout after 0.508 seconds: PASS for bounded synchronous admission. This is not proof that an ASGI health request remains responsive during saturation.

A deliberately closed client connection was discarded and a following SELECT 1 succeeded: PASS for closed-connection recovery. This does not simulate a half-open TCP connection or remote idle termination. Cumulative connections_num=3 includes a replacement, not three simultaneous slots; configured pool_max remained 2. A snapshot immediately after return showed one available connection while background processing was ongoing, so leak-free cleanup is not certified from this snapshot.

No PostgreSQL/psql/Docker executable was discovered. Disposable PostgreSQL write/rollback and session-isolation tests are BLOCKED pending an isolated PostgreSQL fixture. No live writes were attempted. A focused 33-test authorization run with psycopg3 import path and isolated SQLite settings was started; final result is pending and must be collected before launching another run.

Authenticated ASGI comparisons and browser acceptance remain NOT RUN. The final adoption decision remains NO-GO until all required gates complete. No application integration changes are proposed for immediate adoption.

## Recommendation: NO-GO for adoption; GO for further isolated validation

Anonymous ASGI performance improved, but authenticated route, browser, security regression and transaction state cleanup acceptance are incomplete. No active server configuration or environment dependencies were changed.

## Configuration and isolation

Installed psycopg 3.3.8, psycopg-binary 3.3.8 and psycopg-pool 3.3.3 under `.pool-eval-deps`, outside `.venv` site-packages. Only the experiment prepends this directory to its import path. Django version: 6.0.4.

`pool_asgi_evaluation.py` invokes Django's actual ASGI handler with fresh anonymous request scopes, all configured middleware, real login templates, and the existing database. There is no additional network server. Daphne is omitted from app initialization to avoid its Windows import side effect; ASGI HTTP handling is still exercised. No authentication or database records are created.

Pool: min_size=1, max_size=2, timeout=8s, max_waiting=4, max_idle=30s, max_lifetime=120s. CONN_MAX_AGE=0; DISABLE_SERVER_SIDE_CURSORS=True; prepare_threshold=None; SSL=require; connect_timeout=8s. Supabase transaction pooler port 6543.

## Measured ASGI results, seconds

| Measurement | psycopg2 no pool | psycopg3 pool |
|---|---:|---:|
| Sequential requests | 10 | 10 |
| Minimum completion | .603 | .287 |
| Median completion | 1.075 | .434 |
| Maximum / first request | 1.868 | 1.846 |
| Two concurrent requests | 1.086 / 1.087 | .699 / .331 |
| HTTP failures | 0 | 0 |

Median reduction approximately 60%. Response-start timestamps were within about 1–2ms of completion in these samples. This is ASGI response-start latency, not network/browser TTFB. No claim of browser cold/warm or click-to-usable timing is made. SQL counts were not instrumented in this ASGI comparison; previous synchronous login profiling measured four queries.

Pool stats after 12 requests: requests_num=12, requests_queued=1, connections_num=2, connections_ms=1171, requests_wait_ms=531, pool_size=2, pool_available=2, requests_waiting=0. No checked-out connection remained at the sample boundary. Pool explicitly closed at process exit. Longer idle/lifetime behavior and failure recovery remain untested. Project-wide Supabase headroom/limits were not accessible; the experiment capped its own connections at two.

## Compatibility

Django 6 supports OPTIONS.pool with psycopg3 and requires CONN_MAX_AGE=0. Supabase transaction pooling requires disabling automatic prepared statements and server-side cursors. Both are disabled in the experiment. No manual PREPARE, session SET, temporary tables, advisory locks or write transactions were used. Transaction state contamination, rollback-on-error and company/timezone state isolation still require explicit acceptance tests; returning both connections does not prove these properties.

Official references:

- https://docs.djangoproject.com/en/6.0/ref/databases/
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/kb/troubleshooting/disabling-prepared-statements-qL8lEL
- https://www.psycopg.org/psycopg3/docs/advanced/prepare.html

## Remaining acceptance

Authenticated Dashboard, Leads, Accounts, Opportunities, browser metrics and psycopg3 RBAC regression execution are NOT RUN. Existing psycopg2 RBAC baseline remains 33/33; it is not evidence of psycopg3 authorization acceptance. An isolated identity/database fixture is required for mutation/security scenarios. No live browser session was overwritten.

## Files and rollback

Added `pool_asgi_evaluation.py`, isolated dependency directory `.pool-eval-deps`, and this report. No requirements, .env, production settings or active development server changes. Rollback: stop invoking the experiment; ordinary commands still import psycopg2 from the unchanged .venv. The isolated files can be removed after review. No database rollback is needed.
