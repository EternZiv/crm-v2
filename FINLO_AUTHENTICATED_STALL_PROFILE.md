# Focused authenticated request profile

Two separate read-only pooled ASGI child processes were run with external 50-second deadlines. Both exited 0, returned HTTP 200, and closed their pools. No active server or application configuration was changed.

| Request | Response start | Completion | Request queries | Pool cumulative wait |
|---|---:|---:|---:|---:|
| Dashboard cold | 9.471s | 9.473s | 52 | .530s |
| Opportunities cold | 7.432s | 7.434s | 47 | .750s |

Pool wait includes identity setup before the request and must not be added to request duration as an independent stage. Each pool created two connections. The initial identity query is logged separately from request query counts.

Dashboard cProfile: 6.108s in psycopg cursor execution, 6.077s in select.select waiting for sockets. Stack sample: psycopg.waiting.wait_select -> cursor.execute -> ORM iteration -> dashboard.utils.build_table_context:748 -> campaigns.dashboard.campaign_table_func:148 -> home.get_dynamic_default_context. This proves a SQL response wait at the sampled instant, not whether database computation, locks, pooler forwarding or network delay caused it.

Opportunities stack sample: psycopg.waiting.wait_select -> cursor.execute -> ContentType.objects.get_for_id -> context_processors.recently_viewed_items:90 -> template context binding. This identifies cold header-context database work as one contributor. It does not establish the cause of the earlier non-completing request.

Cold requests include theme, role/permission, dashboard widget, content-type, recently-viewed and notification queries. Warm cached header/widget context explains some reduction, but the precise 52-to-11 decomposition and N+1 classification remain unmeasured. SQL logs redact bound parameters and literals; driver execute duration combines server time and network waits. No server-side execution/lock timing was obtained.

Instrumentation added only to evaluation scripts: redacted per-query duration, periodic stack dumps, cProfile, external subprocess timeout and explicit exit reporting. Timer starts before setup, so a 15-second faulthandler label is process elapsed, not request elapsed. No permanent stall reproduced in these two samples. No application fix is justified yet.

Remaining: exclusive middleware/RBAC/context/template/fragment timing, exact duplicate query grouping, identical cold/warm psycopg2 comparison, and reproduction of the earlier stall. Write/rollback tests remain BLOCKED without disposable PostgreSQL. psycopg3 adoption remains NO-GO.
