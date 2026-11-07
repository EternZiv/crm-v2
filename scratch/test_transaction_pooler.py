import time
import psycopg2
from concurrent.futures import ThreadPoolExecutor

db_url = None
with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip().startswith('DATABASE_URL='):
            db_url = line.strip().split('DATABASE_URL=', 1)[1].strip("'\"")
            break

# Change port from 5432 to 6543 for test
tx_url = db_url.replace(':5432/', ':6543/')

def probe_tx_conn(conn_id):
    t0 = time.perf_counter()
    try:
        conn = psycopg2.connect(tx_url, connect_timeout=5)
        t_conn = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            val = cur.fetchone()[0]
        time.sleep(0.1)
        conn.close()
        t_end = time.perf_counter()
        return {
            "id": conn_id,
            "success": True,
            "connect_ms": (t_conn - t0) * 1000,
            "total_ms": (t_end - t0) * 1000
        }
    except Exception as e:
        t_end = time.perf_counter()
        msg = str(e)
        if "@" in msg:
            msg = msg.split("@")[-1]
        return {
            "id": conn_id,
            "success": False,
            "error": msg,
            "total_ms": (t_end - t0) * 1000
        }

print("\n--- Isolated Test: Port 6543 (Transaction Mode) at Concurrency = 30 ---")
with ThreadPoolExecutor(max_workers=30) as executor:
    futures = [executor.submit(probe_tx_conn, i) for i in range(30)]
    results = [f.result() for f in futures]

successes = [r for r in results if r["success"]]
failures = [r for r in results if not r["success"]]
print(f"Concurrency 30 on Port 6543: Successes={len(successes)}, Failures={len(failures)}")
if successes:
    conn_times = [r["connect_ms"] for r in successes]
    print(f"  Connect times: min={min(conn_times):.1f}ms, avg={sum(conn_times)/len(conn_times):.1f}ms, max={max(conn_times):.1f}ms")
if failures:
    print(f"  Failures sample: {failures[0]['error']}")

