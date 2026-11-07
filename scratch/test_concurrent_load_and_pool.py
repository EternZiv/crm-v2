import os
import sys
import time
import threading
import requests
import psycopg2
import concurrent.futures

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

base_url = "http://127.0.0.1:8000"

# 1. Login to obtain session cookie
session = requests.Session()
login_page = session.get(f"{base_url}/login/")
import re
csrf = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', login_page.text).group(1)
session.post(
    f"{base_url}/login/",
    data={"username": "test_bdo", "password": "FinloTest2026!", "csrfmiddlewaretoken": csrf},
    headers={"Referer": f"{base_url}/login/"}
)
cookies = session.cookies.get_dict()
headers = {"HX-Request": "true", "User-Agent": "FinloLoadTest/1.0"}

print(f"Logged in successfully. Session cookie: {cookies.get('sessionid')[:10]}...")

# Poller for pg_stat_activity
pg_samples = []
stop_polling = threading.Event()

def poll_pg():
    try:
        conn = psycopg2.connect(**db_params)
        conn.autocommit = True
        with conn.cursor() as cur:
            while not stop_polling.is_set():
                cur.execute("""
                    SELECT count(*),
                           count(*) FILTER (WHERE state = 'active'),
                           count(*) FILTER (WHERE state = 'idle in transaction'),
                           count(*) FILTER (WHERE state = 'idle'),
                           count(*) FILTER (WHERE wait_event IS NOT NULL)
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                """)
                row = cur.fetchone()
                pg_samples.append((time.perf_counter(), row))
                time.sleep(0.05)
        conn.close()
    except Exception as e:
        print(f"Poll error: {e}")

poller_thread = threading.Thread(target=poll_pg, daemon=True)
poller_thread.start()

# Controlled concurrency: 10 parallel requests to Leads Table
print("\n--- SENDING 10 CONCURRENT REQUESTS TO LEADS TABLE ---")
t_start = time.perf_counter()

in_flight = 0
in_flight_lock = threading.Lock()
max_in_flight = 0
latencies = []

def send_req(i):
    global in_flight, max_in_flight
    with in_flight_lock:
        in_flight += 1
        if in_flight > max_in_flight:
            max_in_flight = in_flight
    
    t0 = time.perf_counter()
    r = requests.get(f"{base_url}/crm/leads/leads-list/", headers=headers, cookies=cookies)
    t1 = time.perf_counter()

    with in_flight_lock:
        in_flight -= 1

    dur = (t1 - t0) * 1000
    latencies.append(dur)
    return r.status_code, dur

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(send_req, i) for i in range(10)]
    results = [f.result() for f in futures]

t_end = time.perf_counter()
stop_polling.set()
poller_thread.join(timeout=2.0)

wall_time = t_end - t_start
rps = len(results) / wall_time

print(f"Total Wall Time for 10 requests: {wall_time:.3f}s")
print(f"Throughput: {rps:.2f} RPS")
print(f"Max Concurrent In-Flight in Daphne: {max_in_flight}")
print(f"Mean Latency: {sum(latencies)/len(latencies):.1f}ms (min={min(latencies):.1f}ms, max={max(latencies):.1f}ms)")

# Analyze pg_stat_activity samples
print(f"\n--- PG_STAT_ACTIVITY ANALYSIS DURING RUN ({len(pg_samples)} samples) ---")
max_total = max(s[1][0] for s in pg_samples) if pg_samples else 0
max_active = max(s[1][1] for s in pg_samples) if pg_samples else 0
max_idle_in_tx = max(s[1][2] for s in pg_samples) if pg_samples else 0
max_waiting = max(s[1][4] for s in pg_samples) if pg_samples else 0

print(f"Max Total Backends in pg_stat_activity: {max_total}")
print(f"Max Active Backends (executing query concurrently): {max_active}")
print(f"Max Idle in Transaction: {max_idle_in_tx}")
print(f"Max Backends with Wait Events: {max_waiting}")

