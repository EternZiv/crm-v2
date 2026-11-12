# Performance readiness

No Vercel browser/function measurements exist. Historical local evidence: anonymous psycopg2 median 1.075s versus experimental psycopg3 pool .434s; adoption remains NO-GO. Pooled authenticated cold Dashboard 9.473s/52 queries and Opportunities 7.434s/47 queries; these are not Vercel timings. Driver waits combine network/pooler/database execution. Expanded diagnostic processes encountered native crashes; no root-cause performance fix can be claimed.

Policy: preserve psycopg2 and max_age=0, transaction pooler, disabled server cursors. Colocate approved preview compute with Supabase Mumbai. Bound instance count/concurrency against measured database/pooler headroom, including workers and realtime auth; no capacity value is known. No arbitrary instance limit or client pool was silently introduced.

Measure cold/warm login, Dashboard, Leads, Accounts, Contacts, Opportunities, Calendar, Role Manager; capture connection time, SQL duration/count, response start, HTMX request count, browser usable content, function init/duration/memory/timeouts and websocket limits. Under-one-second target is NOT VERIFIED. Production GO is blocked by functional/infrastructure/performance acceptance.

