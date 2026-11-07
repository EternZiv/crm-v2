import psutil
import time

print(f"{'PID':<8} | {'Process Name':<25} | {'CPU%':<8} | {'Memory (MB)':<12}")
print("-" * 60)

# Warm up psutil
for p in psutil.process_iter(['pid', 'name']):
    try:
        p.cpu_percent(interval=None)
    except Exception:
        pass

time.sleep(1.0)

procs = []
for p in psutil.process_iter(['pid', 'name', 'memory_info']):
    try:
        cpu = p.cpu_percent(interval=None)
        mem = p.info['memory_info'].rss / (1024 * 1024)
        if cpu > 1.0 or 'python' in p.info['name'].lower() or 'daphne' in p.info['name'].lower():
            procs.append((p.pid, p.info['name'], cpu, mem))
    except Exception:
        pass

procs.sort(key=lambda x: x[2], reverse=True)
for pid, name, cpu, mem in procs[:15]:
    print(f"{pid:<8} | {name:<25} | {cpu:<8.1f} | {mem:<12.1f}")

print(f"\nTotal Host CPU: {psutil.cpu_percent(interval=None):.1f}%")

