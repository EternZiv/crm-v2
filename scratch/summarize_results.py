import csv
import glob
import os

stages = [
    ('Stage 1 (1 User)', 'load_tests/reports/local_mumbai/stage1_1user_baseline_stats.csv', 'load_tests/reports/local_mumbai/stage1_telemetry.csv'),
    ('Stage 2 (10 Users)', 'load_tests/reports/local_mumbai/stage2_10users_stats.csv', 'load_tests/reports/local_mumbai/stage2_telemetry.csv'),
    ('Stage 3 (25 Users)', 'load_tests/reports/local_mumbai/stage3_25users_stats.csv', 'load_tests/reports/local_mumbai/stage3_telemetry.csv'),
    ('Stage 4 (50 Users)', 'load_tests/reports/local_mumbai/stage4_50users_stats.csv', 'load_tests/reports/local_mumbai/stage4_telemetry.csv')
]

for name, stats_path, telem_path in stages:
    print('=== ' + name + ' ===')
    if os.path.exists(stats_path):
        with open(stats_path, mode='r', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))
            agg = [r for r in reader if r.get('Name') == 'Aggregated']
            if agg:
                a = agg[0]
                reqs = int(a['Request Count'])
                fails = int(a['Failure Count'])
                err_rate = (fails / reqs * 100) if reqs > 0 else 0
                rps = float(a['Requests/s'])
                med = float(a['Median Response Time'])
                avg = float(a['Average Response Time'])
                p95 = float(a.get('95%', 0))
                p99 = float(a.get('99%', 0))
                max_t = float(a['Max Response Time'])
                print(f"Requests: {reqs}, Fails: {fails} ({err_rate:.2f}%), RPS: {rps:.2f}, Med: {med:.0f}ms, Avg: {avg:.0f}ms, p95: {p95:.0f}ms, p99: {p99:.0f}ms, Max: {max_t:.0f}ms")
    if os.path.exists(telem_path):
        with open(telem_path, mode='r', encoding='utf-8') as f:
            t_reader = list(csv.DictReader(f))
            cpus = [float(r['cpu_percent']) for r in t_reader if float(r.get('cpu_percent', -1)) >= 0]
            mems = [float(r['memory_percent']) for r in t_reader if float(r.get('memory_percent', -1)) >= 0]
            conns = [int(r['db_total_conns']) for r in t_reader if int(r.get('db_total_conns', -1)) >= 0]
            active_conns = [int(r['db_active_conns']) for r in t_reader if int(r.get('db_active_conns', -1)) >= 0]
            print(f"CPU: avg={sum(cpus)/len(cpus):.1f}%, max={max(cpus):.1f}%; Mem: avg={sum(mems)/len(mems):.1f}%; DB Conns: max={max(conns) if conns else 'N/A'}, active_max={max(active_conns) if active_conns else 'N/A'}")
    print()

