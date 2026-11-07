import time
import psycopg2
import os

db_url = None
with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip().startswith('DATABASE_URL='):
            db_url = line.strip().split('DATABASE_URL=', 1)[1].strip("'\"")
            break

def test_single_conn():
    t0 = time.perf_counter()
    try:
        conn = psycopg2.connect(db_url, connect_timeout=10)
        t_connected = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            res = cur.fetchone()
        t_queried = time.perf_counter()
        conn.close()
        t_closed = time.perf_counter()
        return {
            "success": True,
            "handshake_time_ms": (t_connected - t0) * 1000,
            "query_time_ms": (t_queried - t_connected) * 1000,
            "total_time_ms": (t_closed - t0) * 1000
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

print("--- Measuring single connection baseline (3 samples) ---")
for i in range(3):
    res = test_single_conn()
    if res["success"]:
        print(f"Sample {i+1}: Handshake={res['handshake_time_ms']:.1f}ms, Query={res['query_time_ms']:.1f}ms, Total={res['total_time_ms']:.1f}ms")
    else:
        print(f"Sample {i+1} Failed: {res['error']}")
    time.sleep(0.5)
