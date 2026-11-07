"""
Finlo CRM v2 — Staging Telemetry & Resource Monitor.
Collects and logs real-time system, process, database, and Redis/Celery metrics
during load tests to correlate with Locust client-side latencies.
"""

import argparse
import csv
import datetime
import os
import sys
import time
from typing import Any, Dict

try:
    import psutil
except ImportError:
    psutil = None


def get_system_metrics() -> Dict[str, Any]:
    """Captures host CPU and Memory utilization."""
    if not psutil:
        return {"cpu_percent": 0.0, "memory_percent": 0.0, "memory_used_mb": 0.0}
    mem = psutil.virtual_memory()
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": mem.percent,
        "memory_used_mb": round(mem.used / (1024 * 1024), 1),
    }


def get_database_metrics(db_url: str) -> Dict[str, Any]:
    """Queries pg_stat_activity for active connections and running query counts."""
    if not db_url:
        return {"db_active_conns": 0, "db_idle_tx": 0, "db_slow_queries": 0}
    try:
        import psycopg2
        conn = psycopg2.connect(db_url, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    count(*) as total_conns,
                    count(*) FILTER (WHERE state = 'active') as active_conns,
                    count(*) FILTER (WHERE state = 'idle in transaction') as idle_tx,
                    count(*) FILTER (WHERE state = 'active' AND query_start < now() - interval '2 seconds') as slow_queries
                FROM pg_stat_activity;
            """)
            row = cur.fetchone()
        conn.close()
        return {
            "db_total_conns": row[0] or 0,
            "db_active_conns": row[1] or 0,
            "db_idle_tx": row[2] or 0,
            "db_slow_queries": row[3] or 0,
        }
    except Exception:
        return {"db_total_conns": -1, "db_active_conns": -1, "db_idle_tx": -1, "db_slow_queries": -1}


def get_redis_metrics(redis_url: str) -> Dict[str, Any]:
    """Queries Redis for connected clients, memory, and Celery queue backlog."""
    if not redis_url:
        return {"redis_clients": 0, "redis_used_mb": 0.0, "celery_backlog": 0}
    try:
        import redis
        client = redis.from_url(redis_url, socket_timeout=3)
        info = client.info()
        # Check standard Celery queue length
        celery_len = client.llen("celery")
        return {
            "redis_clients": info.get("connected_clients", 0),
            "redis_used_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
            "celery_backlog": celery_len,
        }
    except Exception:
        return {"redis_clients": -1, "redis_used_mb": -1, "celery_backlog": -1}


def monitor_loop(interval: int = 5, output_csv: str = None, duration: int = None):
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url and os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DATABASE_URL="):
                        db_url = line.split("=", 1)[1].strip("'\"")
                        break
        except Exception:
            pass
    redis_url = os.environ.get("REDIS_URL", "")
    out_file = output_csv or f"reports/telemetry_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    os.makedirs(os.path.dirname(out_file) or ".", exist_ok=True)

    print("=" * 70)
    print("FINLO CRM v2 — STAGING TELEMETRY MONITOR")
    print(f"Sampling Interval: {interval}s")
    print(f"Output CSV: {out_file}")
    print("=" * 70)

    fieldnames = [
        "timestamp",
        "cpu_percent",
        "memory_percent",
        "memory_used_mb",
        "db_total_conns",
        "db_active_conns",
        "db_idle_tx",
        "db_slow_queries",
        "redis_clients",
        "redis_used_mb",
        "celery_backlog",
    ]

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        start_time = time.time()
        try:
            while True:
                now = datetime.datetime.now().isoformat()
                sys_m = get_system_metrics()
                db_m = get_database_metrics(db_url)
                red_m = get_redis_metrics(redis_url)

                row = {
                    "timestamp": now,
                    **sys_m,
                    **db_m,
                    **red_m,
                }
                writer.writerow(row)
                f.flush()

                print(
                    f"[{now.split('T')[1][:8]}] CPU: {sys_m['cpu_percent']:>4.1f}% | "
                    f"RAM: {sys_m['memory_used_mb']:>6.1f} MB | "
                    f"DB Conns: {db_m.get('db_total_conns', 0):>3} (Act: {db_m.get('db_active_conns', 0)}) | "
                    f"Redis Clients: {red_m.get('redis_clients', 0):>2} | "
                    f"Celery Backlog: {red_m.get('celery_backlog', 0)}"
                )

                if duration and (time.time() - start_time) >= duration:
                    break

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[STOPPED] Telemetry monitoring completed.")


def main():
    parser = argparse.ArgumentParser(description="Collect staging telemetry during load tests.")
    parser.add_argument("--interval", type=int, default=5, help="Sampling interval in seconds (default: 5).")
    parser.add_argument("--duration", type=int, default=None, help="Stop after duration seconds.")
    parser.add_argument("--output", default=None, help="Path to write CSV telemetry log.")
    args = parser.parse_args()

    monitor_loop(interval=args.interval, output_csv=args.output, duration=args.duration)


if __name__ == "__main__":
    main()

