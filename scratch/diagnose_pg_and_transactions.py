import os
import sys
import time
import psycopg2

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings.base')

from django.conf import settings

db_conf = settings.DATABASES['default']
db_params = {
    'dbname': db_conf['NAME'],
    'user': db_conf['USER'],
    'password': db_conf['PASSWORD'],
    'host': db_conf['HOST'],
    'port': db_conf['PORT'],
    'sslmode': 'require'
}

print("--- TASK 2 & 3: POSTGRESQL STATS & TRANSACTION DURATION ---")
conn = psycopg2.connect(**db_params)
conn.autocommit = True

try:
    with conn.cursor() as cur:
        # Check pg_stat_activity
        cur.execute("""
            SELECT pid, client_addr, client_port, backend_start, xact_start, query_start, 
                   state, wait_event_type, wait_event, query
            FROM pg_stat_activity
            WHERE datname = current_database()
        """)
        rows = cur.fetchall()
        print(f"\nTotal pg_stat_activity rows for DB '{db_conf['NAME']}': {len(rows)}")
        for r in rows:
            xact_duration = (time.time() - r[4].timestamp()) if r[4] else None
            query_duration = (time.time() - r[5].timestamp()) if r[5] else None
            q_clean = (r[9] or '').replace('\n', ' ')[:60]
            print(f"PID {r[0]}: state={r[6]}, wait_type={r[7]}, wait_event={r[8]}, "
                  f"xact_age={'None' if xact_duration is None else f'{xact_duration:.3f}s'}, "
                  f"query_age={'None' if query_duration is None else f'{query_duration:.3f}s'}, "
                  f"query={q_clean}")

        # Check max_connections
        cur.execute("SHOW max_connections;")
        max_conn = cur.fetchone()[0]
        print(f"\nPostgreSQL max_connections: {max_conn}")

        # Measure individual autocommit transaction duration vs explicit transaction block
        print("\n--- MEASURING INDIVIDUAL TRANSACTION DURATIONS ---")
        # 1. Single autocommit SELECT
        times_autocommit = []
        for _ in range(10):
            t0 = time.perf_counter()
            cur.execute("SELECT count(*) FROM leads_lead;")
            cur.fetchone()
            t1 = time.perf_counter()
            times_autocommit.append((t1 - t0) * 1000)

        mean_ac = sum(times_autocommit) / len(times_autocommit)
        print(f"Autocommit SELECT count(*) leads: mean={mean_ac:.2f}ms, min={min(times_autocommit):.2f}ms, max={max(times_autocommit):.2f}ms")

        # 2. Explicit BEGIN ... COMMIT block with 1 query
        times_explicit = []
        for _ in range(10):
            t0 = time.perf_counter()
            cur.execute("BEGIN;")
            cur.execute("SELECT count(*) FROM leads_lead;")
            cur.fetchone()
            cur.execute("COMMIT;")
            t1 = time.perf_counter()
            times_explicit.append((t1 - t0) * 1000)

        mean_ex = sum(times_explicit) / len(times_explicit)
        print(f"Explicit BEGIN...COMMIT with 1 query: mean={mean_ex:.2f}ms, min={min(times_explicit):.2f}ms, max={max(times_explicit):.2f}ms")

        # 3. Explicit BEGIN ... COMMIT with 15 queries simulating a request
        times_15_queries = []
        for _ in range(5):
            t0 = time.perf_counter()
            cur.execute("BEGIN;")
            for _ in range(15):
                cur.execute("SELECT count(*) FROM leads_lead;")
                cur.fetchone()
            cur.execute("COMMIT;")
            t1 = time.perf_counter()
            times_15_queries.append((t1 - t0) * 1000)

        mean_15 = sum(times_15_queries) / len(times_15_queries)
        print(f"Explicit BEGIN...COMMIT with 15 queries: mean={mean_15:.2f}ms, min={min(times_15_queries):.2f}ms, max={max(times_15_queries):.2f}ms")
finally:
    conn.close()
