import time
import psycopg2
from concurrent.futures import ThreadPoolExecutor

db_url = None
with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip().startswith('DATABASE_URL='):
            db_url = line.strip().split('DATABASE_URL=', 1)[1].strip("'\"")
            break

def probe_conn(conn_id, hold_sec=1.0):
    t0 = time.perf_counter()
    try:
        conn = psycopg2.connect(db_url, connect_timeout=5)
        t_conn = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute("SELECT pg_backend_pid();")
            pid = cur.fetchone()[0]
        time.sleep(hold_sec)
        conn.close()
        t_end = time.perf_counter()
        return {
            "id": conn_id,
            "success": True,
            "pid": pid,
            "connect_ms": (t_conn - t0) * 1000,
            "total_ms": (t_end - t0) * 1000
        }
    except Exception as e:
        t_end = time.perf_counter()
        # Sanitize exception message so password/user isn't leaked
        msg = str(e)
        if "@" in msg:
            msg = msg.split("@")[-1]
        return {
            "id": conn_id,
            "success": False,
            "error": msg,
            "total_ms": (t_end - t0) * 1000
        }

for concurrency in [5, 15, 30]:
    print(f"\n--- Testing concurrency = {concurrency} (holding 1s) ---")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(probe_conn, i) for i in range(concurrency)]
        results = [f.result() for f in futures]
    
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    print(f"Concurrency {concurrency}: Successes={len(successes)}, Failures={len(failures)}")
    if successes:
        conn_times = [r["connect_ms"] for r in successes]
        print(f"  Connect times: min={min(conn_times):.1f}ms, avg={sum(conn_times)/len(conn_times):.1f}ms, max={max(conn_times):.1f}ms")
    if failures:
        print(f"  Sample failure error: {failures[0]['error']}")
    time.sleep(1)

