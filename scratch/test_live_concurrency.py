import concurrent.futures
import json
import time
import urllib.request

url = "http://127.0.0.1:8000/diag/concurrency/"

def fetch(i):
    t_req_start = time.time()
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            data["req_index"] = i
            data["client_wall_time_ms"] = (time.time() - t_req_start) * 1000
            return data
    except Exception as e:
        return {"req_index": i, "error": str(e), "client_wall_time_ms": (time.time() - t_req_start) * 1000}

print("Firing 10 simultaneous requests to http://127.0.0.1:8000/diag/concurrency/...")
t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
    results = list(pool.map(fetch, range(10)))
t1 = time.time()

print(f"\nCompleted 10 requests in {t1 - t0:.3f} seconds total wall time.")
thread_ids = set()
pids = set()
errors = []

for r in results:
    if "error" in r:
        errors.append(r)
    else:
        thread_ids.add(r["thread_id"])
        pids.add(r["pid"])
        print(f"Req {r['req_index']}: PID={r['pid']}, Thread={r['thread_id']} ({r['thread_name']}), "
              f"ActiveStart={r['active_at_start']}, ActiveEnd={r['active_at_end']}, "
              f"DB={r['db_time_ms']:.1f}ms, ServerTotal={r['total_time_ms']:.1f}ms, "
              f"ClientTotal={r['client_wall_time_ms']:.1f}ms")

print(f"\nSummary:")
print(f"  PIDs observed: {pids}")
print(f"  Unique Thread IDs observed: {len(thread_ids)} out of {len(results)}")
print(f"  Errors: {len(errors)}")

# Check temporal overlap
starts = [r["start_time"] for r in results if "start_time" in r]
ends = [r["end_time"] for r in results if "end_time" in r]
if starts and ends:
    min_start, max_start = min(starts), max(starts)
    min_end, max_end = min(ends), max(ends)
    print(f"  Start time span: {max_start - min_start:.3f}s")
    print(f"  Overlapping span: {min_end - max_start:.3f}s (Positive means true concurrent overlap)")

