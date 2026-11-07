import csv

with open('load_tests/reports/local_mumbai/stage4_50users_stats.csv', mode='r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

endpoints = [r for r in rows if r['Name'] != 'Aggregated']
endpoints.sort(key=lambda x: int(x['Failure Count']), reverse=True)

print(f"{'Endpoint':<65} | {'Reqs':<5} | {'Fails':<5} | {'Err %':<7} | {'Med':<7} | {'Avg':<7} | {'p95':<7}")
print("-" * 115)
for ep in endpoints:
    name = ep['Name']
    reqs = int(ep['Request Count'])
    fails = int(ep['Failure Count'])
    err_pct = f"{(fails / reqs * 100):.1f}%" if reqs > 0 else "0%"
    med = f"{float(ep['Median Response Time']):.0f}ms"
    avg = f"{float(ep['Average Response Time']):.0f}ms"
    p95 = f"{float(ep.get('95%', 0)):.0f}ms"
    print(f"{name:<65} | {reqs:<5} | {fails:<5} | {err_pct:<7} | {med:<7} | {avg:<7} | {p95:<7}")

