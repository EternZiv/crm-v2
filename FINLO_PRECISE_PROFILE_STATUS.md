# Precise request attribution status

## Outcome

No application fix or pooling integration was applied. psycopg3 adoption remains NO-GO. The expanded diagnostic harness did not produce valid completed stage/query summaries.

## Bounded observations

- Cold/warm pooled Dashboard child reached the external 50-second deadline; supervisor killed only its owned child. Stack samples included campaign table ORM loading waiting in psycopg socket handling. No response summary completed.
- Pooled Opportunities child exited 3221225477 (Windows 0xC0000005 access violation). Its final truncated stack reached inspect.py while collecting query sources. This is a diagnostic-process crash; it cannot be attributed to CRM business logic or the database.
- Replaced inspect.stack() with a lightweight frame walk to reduce instrumentation overhead. A bounded psycopg2 Dashboard control still exited 3221225477; the last stack reached Django template variable lookup. The replacement did not resolve the native crash, and no root cause is established.

Logs are retained separately as pool_diagnostic_dashboard_*, pool_diagnostic_opportunities_* and pool_diagnostic_baseline_*. They contain stack paths and redacted SQL patterns, never SQL parameter values.

## Evidence limits

No new top-five query, exclusive stage, duplicate-query, or equivalent cold/warm comparison result can honestly be reported from these failed samples. Previous completed Dashboard result (9.473s, 52 queries, 6.108s driver execution) and Opportunities result (7.434s, 47 queries) remain historical evidence only. SQL execute duration combines network/pooler/database waits and does not establish lock contention.

## Next safe diagnostic step

Isolate the native crash by disabling cProfile and periodic faulthandler in separate read-only diagnostic subprocesses, retaining the external wall-clock supervisor. Then instrument selected Python call boundaries directly with inclusive/exclusive timers, and collect source fingerprints with the lightweight frame walk. Complete one valid control before collecting more route samples. Do not change ORM/context behavior on the basis of the current failed measurements.

Disposable PostgreSQL write/rollback tests remain BLOCKED. Active server, credentials, authorization, records, migrations and application settings remain untouched.
