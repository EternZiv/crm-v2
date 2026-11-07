import csv

with open('load_tests/reports/local_mumbai/stage3_25users_stats.csv', mode='r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

endpoints = [r for r in rows if r['Name'] != 'Aggregated']
endpoints.sort(key=lambda x: float(x.get('95%', 0)), reverse=True)

print(f"{'Endpoint':<65} | {'Reqs':<5} | {'Fails':<5} | {'Med':<7} | {'Avg':<7} | {'p95':<7} | {'Max':<7} | {'Payload (KB)':<12}")
print("-" * 125)
for ep in endpoints:
    name = ep['Name']
    reqs = ep['Request Count']
    fails = ep['Failure Count']
    med = f"{float(ep['Median Response Time']):.0f}ms"
    avg = f"{float(ep['Average Response Time']):.0f}ms"
    p95 = f"{float(ep.get('95%', 0)):.0f}ms"
    max_t = f"{float(ep['Max Response Time']):.0f}ms"
    size_kb = f"{float(ep['Average Content Size'])/1024:.1f} KB"
    print(f"{name:<65} | {reqs:<5} | {fails:<5} | {med:<7} | {avg:<7} | {p95:<7} | {max_t:<7} | {size_kb:<12}")

