# Connection lifecycle experiment

Read-only measurements; no credentials or records changed. Effective configuration: PostgreSQL/psycopg2, Supabase shared transaction pooler port 6543, sslmode=require, CONN_MAX_AGE=0, CONN_HEALTH_CHECKS=True, Daphne ASGI.

## Corrected bounded comparison (seconds)

| Operation | Samples | Min | Median | Max |
|---|---:|---:|---:|---:|
| DNS | 5 | .0007 | .0081 | .1668 |
| TCP including DNS | 5 | .0498 | .0654 | .1431 |
| PostgreSQL connect including TLS/auth | 5 | .3600 | .5065 | .8663 |
| First SELECT 1 | 5 | .0491 | .0521 | .0558 |
| Reused SELECT 1 | 15 | .0508 | .0549 | .2280 |
| Concurrent connect/query, two workers | 4 | .6853 | 1.0845 | 1.4846 |
| Login, explicitly fresh connection | 10 | .7480 | 1.1809 | 1.7814 |
| Login, single-process reuse experiment | 10 | .2927 | .4280 | .8713 |

All 20 login requests returned 200 and executed four queries. Reuse reduced the measured median by about 64%. These are synchronous in-process middleware/view/template measurements, not browser TTFB or ASGI load-test results. The test client disconnects normal connection cleanup signals, so the corrected control explicitly closes each connection. Earlier uncorrected client comparison is invalid as a lifecycle comparison.

An earlier independent sample had connect median 1.0419s/max 4.0812s, showing variability. DNS is not dominant in these samples. TLS and PostgreSQL authentication were measured together; neither can individually be identified as the dominant handshake phase. Pooler capacity/limit telemetry was unavailable. The experiment limited its own concurrency to two connections.

## Decision

No application database setting changed. Django advises CONN_MAX_AGE=0 under ASGI. Raising it based on a synchronous test-client benchmark would not verify ASGI lifecycle behavior. Current psycopg2 does not support Django's built-in psycopg3 pool option.

Recommended next implementation: evaluate psycopg3 plus a small bounded Django-managed client pool in an isolated ASGI configuration, with max_age=0, acquisition timeout, transaction-pooler compatible cursor/prepared-statement settings, connection cleanup tests, and authenticated route checks before adoption. An external transaction pooler reuses upstream database connections but does not eliminate the application's remote client handshake.

Authenticated Dashboard/Leads/Accounts/Opportunities and browser timing remain unverified for any new pool configuration because none was adopted. Existing running server and production environment were preserved.
