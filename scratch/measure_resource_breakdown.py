import concurrent.futures
import os, sys
sys.path.insert(0, os.path.abspath("."))
import psutil
import time
import urllib.request
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finlo.settings.base")
django.setup()
from django.db import connection

# Find the server process on port 8000
server_proc = None
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = " ".join(p.info['cmdline'] or [])
        if "manage.py runserver" in cmd and p.pid != os.getpid():
            server_proc = p
            break
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"Target Server PID: {server_proc.pid if server_proc else 'NOT FOUND'}")

# Warm up CPU measurement
if server_proc:
    server_proc.cpu_percent(interval=None)
current_proc = psutil.Process()
current_proc.cpu_percent(interval=None)
psutil.cpu_percent(interval=None)

# 1. Measure SQL execution time vs connection wait time
print("\n--- Measuring PostgreSQL Timing (Port 6543) ---")
sql_times = []
conn_times = []
for _ in range(5):
    t_conn_0 = time.time()
    with connection.cursor() as cur:
        t_conn_1 = time.time()
        t_query_0 = time.time()
        cur.execute("SELECT count(*) FROM leads_lead")
        cur.fetchone()
        t_query_1 = time.time()
    conn_times.append((t_conn_1 - t_conn_0) * 1000)
    sql_times.append((t_query_1 - t_query_0) * 1000)

print(f"Connection acquire time: mean={sum(conn_times)/len(conn_times):.1f}ms, min={min(conn_times):.1f}ms, max={max(conn_times):.1f}ms")
print(f"SQL execute time (SELECT count(*) leads): mean={sum(sql_times)/len(sql_times):.1f}ms, min={min(sql_times):.1f}ms, max={max(sql_times):.1f}ms")

# 2. Run a small controlled concurrent probe (5 parallel clients, 20 requests total)
print("\n--- Running Controlled Concurrency Probe (5 clients, 20 reqs to /login/) ---")
urls = ["http://127.0.0.1:8000/login/"] * 20

def fetch(u):
    t0 = time.time()
    try:
        req = urllib.request.Request(u)
        with urllib.request.urlopen(req, timeout=10) as r:
            return True, (time.time() - t0) * 1000
    except Exception as e:
        print(f"fetch error: {e}")
        return False, (time.time() - t0) * 1000

t_start = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    results = list(pool.map(fetch, urls))
t_end = time.time()

# Process CPU sampling
server_cpu = server_proc.cpu_percent(interval=None) if server_proc else 0.0
client_cpu = current_proc.cpu_percent(interval=None)
sys_cpu = psutil.cpu_percent(interval=None)

durations = [r[1] for r in results if r[0]]
fails = [r for r in results if not r[0]]
print(f"Completed {len(durations)}/{len(urls)} requests in {t_end - t_start:.2f}s (RPS: {len(durations)/(t_end - t_start):.2f})")
print(f"Response Times: mean={sum(durations)/len(durations):.1f}ms, min={min(durations):.1f}ms, max={max(durations):.1f}ms")
print(f"Daphne/Server CPU: {server_cpu:.1f}%")
print(f"Client Process CPU: {client_cpu:.1f}%")
print(f"System Total CPU: {sys_cpu:.1f}%")
print(f"System Available Memory: {psutil.virtual_memory().available / (1024*1024):.1f} MB")
