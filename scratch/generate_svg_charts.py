import os

def generate_charts():
    output_dir = 'load_tests/reports/local_mumbai'
    os.makedirs(output_dir, exist_ok=True)

    # 1. Concurrency vs Response Time (ms)
    # Stages: 1, 10, 25, 50 users
    stages = ['1 User', '10 Users', '25 Users', '50 Users*']
    med = [1800, 1900, 2100, 1900]
    p95 = [3800, 5200, 5900, 4400]
    p99 = [4500, 27000, 14000, 8700]
    max_t = [4471, 28785, 30127, 31219]

    svg1 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%" style="background:#0f172a; font-family:system-ui, -apple-system, sans-serif;">
  <style>
    .title {{ font-size: 18px; font-weight: 700; fill: #f8fafc; }}
    .subtitle {{ font-size: 12px; fill: #94a3b8; }}
    .axis {{ stroke: #334155; stroke-width: 1; }}
    .grid {{ stroke: #1e293b; stroke-dasharray: 4,4; }}
    .label {{ font-size: 12px; fill: #94a3b8; text-anchor: middle; }}
    .y-label {{ font-size: 11px; fill: #64748b; text-anchor: end; }}
    .legend {{ font-size: 12px; fill: #e2e8f0; }}
  </style>
  
  <text x="40" y="35" class="title">Finlo CRM v2 — Concurrency vs Latency Progression</text>
  <text x="40" y="55" class="subtitle">*At 50 users, 40.7% of requests failed instantly with 500, skewing response percentiles downwards.</text>
  
  <!-- Y Grid & Labels (0 to 35,000 ms) -->
  <line x1="80" y1="360" x2="740" y2="360" class="axis" />
  <line x1="80" y1="360" x2="80" y2="80" class="axis" />
  
  <!-- 0s -->
  <text x="70" y="364" class="y-label">0s</text>
  <!-- 10s -->
  <line x1="80" y1="280" x2="740" y2="280" class="grid" />
  <text x="70" y="284" class="y-label">10s</text>
  <!-- 20s -->
  <line x1="80" y1="200" x2="740" y2="200" class="grid" />
  <text x="70" y="204" class="y-label">20s</text>
  <!-- 30s -->
  <line x1="80" y1="120" x2="740" y2="120" class="grid" />
  <text x="70" y="124" class="y-label">30s</text>
  <!-- Threshold Red Line (10s Stop Gate) -->
  <line x1="80" y1="280" x2="740" y2="280" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="6,4" />
  <text x="735" y="272" fill="#ef4444" font-size="11px" text-anchor="end" font-weight="600">10s Safety Limit</text>

  <!-- X Points: 160, 320, 480, 640 -->
  <!-- Max line: red -->
  <polyline fill="none" stroke="#f43f5e" stroke-width="2.5" points="160,324 320,130 480,119 640,110" />
  <!-- p99 line: purple -->
  <polyline fill="none" stroke="#a855f7" stroke-width="2.5" points="160,324 320,144 480,248 640,290" />
  <!-- p95 line: amber -->
  <polyline fill="none" stroke="#f59e0b" stroke-width="2.5" points="160,330 320,318 480,313 640,325" />
  <!-- Median line: teal -->
  <polyline fill="none" stroke="#06b6d4" stroke-width="2.5" points="160,346 320,345 480,343 640,345" />

  <!-- Data Points -->
  <!-- 1 User -->
  <circle cx="160" cy="346" r="4" fill="#06b6d4" />
  <circle cx="160" cy="330" r="4" fill="#f59e0b" />
  <circle cx="160" cy="324" r="4" fill="#f43f5e" />
  <text x="160" y="380" class="label">1 User</text>
  
  <!-- 10 Users -->
  <circle cx="320" cy="345" r="4" fill="#06b6d4" />
  <circle cx="320" cy="318" r="4" fill="#f59e0b" />
  <circle cx="320" cy="144" r="4" fill="#a855f7" />
  <circle cx="320" cy="130" r="4" fill="#f43f5e" />
  <text x="320" y="380" class="label">10 Users</text>

  <!-- 25 Users -->
  <circle cx="480" cy="343" r="4" fill="#06b6d4" />
  <circle cx="480" cy="313" r="4" fill="#f59e0b" />
  <circle cx="480" cy="248" r="4" fill="#a855f7" />
  <circle cx="480" cy="119" r="4" fill="#f43f5e" />
  <text x="480" y="380" class="label">25 Users</text>

  <!-- 50 Users -->
  <circle cx="640" cy="345" r="4" fill="#06b6d4" />
  <circle cx="640" cy="325" r="4" fill="#f59e0b" />
  <circle cx="640" cy="290" r="4" fill="#a855f7" />
  <circle cx="640" cy="110" r="4" fill="#f43f5e" />
  <text x="640" y="380" class="label">50 Users (FAILED)</text>

  <!-- Legend -->
  <rect x="180" y="410" width="12" height="12" fill="#06b6d4" rx="2" />
  <text x="200" y="421" class="legend">Median (p50)</text>
  <rect x="310" y="410" width="12" height="12" fill="#f59e0b" rx="2" />
  <text x="330" y="421" class="legend">p95 Latency</text>
  <rect x="440" y="410" width="12" height="12" fill="#a855f7" rx="2" />
  <text x="460" y="421" class="legend">p99 Latency</text>
  <rect x="560" y="410" width="12" height="12" fill="#f43f5e" rx="2" />
  <text x="580" y="421" class="legend">Max Latency</text>
</svg>"""

    with open(os.path.join(output_dir, 'chart_concurrency_vs_latency.svg'), 'w', encoding='utf-8') as f:
        f.write(svg1)

    # 2. Concurrency vs Throughput & Error Rate
    svg2 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%" style="background:#0f172a; font-family:system-ui, -apple-system, sans-serif;">
  <style>
    .title {{ font-size: 18px; font-weight: 700; fill: #f8fafc; }}
    .subtitle {{ font-size: 12px; fill: #94a3b8; }}
    .axis {{ stroke: #334155; stroke-width: 1; }}
    .grid {{ stroke: #1e293b; stroke-dasharray: 4,4; }}
    .label {{ font-size: 12px; fill: #94a3b8; text-anchor: middle; }}
    .y-label-l {{ font-size: 11px; fill: #38bdf8; text-anchor: end; }}
    .y-label-r {{ font-size: 11px; fill: #ef4444; text-anchor: start; }}
    .legend {{ font-size: 12px; fill: #e2e8f0; }}
  </style>

  <text x="40" y="35" class="title">Finlo CRM v2 — Throughput Saturation &amp; Error Rate Spike</text>
  <text x="40" y="55" class="subtitle">System throughput capped at ~2.2 req/s before catastrophic pool collapse at 50 users.</text>

  <!-- Left Y Axis: Throughput (0 to 3 req/s) -->
  <line x1="80" y1="360" x2="80" y2="80" class="axis" />
  <!-- Right Y Axis: Error % (0 to 50%) -->
  <line x1="720" y1="360" x2="720" y2="80" class="axis" />

  <!-- Y Grid (0, 1, 2, 3 req/s <-> 0, 16.7, 33.3, 50%) -->
  <line x1="80" y1="360" x2="720" y2="360" class="axis" />
  <text x="70" y="364" class="y-label-l">0.0</text>
  <text x="730" y="364" class="y-label-r">0%</text>

  <line x1="80" y1="267" x2="720" y2="267" class="grid" />
  <text x="70" y="271" class="y-label-l">1.0</text>
  <text x="730" y="271" class="y-label-r">16.7%</text>

  <line x1="80" y1="173" x2="720" y2="173" class="grid" />
  <text x="70" y="177" class="y-label-l">2.0</text>
  <text x="730" y="177" class="y-label-r">33.3%</text>

  <line x1="80" y1="80" x2="720" y2="80" class="grid" />
  <text x="70" y="84" class="y-label-l">3.0</text>
  <text x="730" y="84" class="y-label-r">50.0%</text>

  <!-- Error Threshold 5% line (at y = 360 - (5/50)*280 = 332) -->
  <line x1="80" y1="332" x2="720" y2="332" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="4,4" />
  <text x="715" y="325" fill="#ef4444" font-size="11px" text-anchor="end">5% Error Limit</text>

  <!-- Throughput Bars (Blue) -->
  <!-- 1 User: 0.20 req/s -> height = 0.20/3 * 280 = 18.6 -> y = 341.4 -->
  <rect x="135" y="341" width="30" height="19" fill="#0284c7" rx="3" />
  <text x="150" y="335" fill="#38bdf8" font-size="11px" text-anchor="middle">0.20</text>

  <!-- 10 Users: 1.65 req/s -> height = 1.65/3 * 280 = 154 -> y = 206 -->
  <rect x="295" y="206" width="30" height="154" fill="#0284c7" rx="3" />
  <text x="310" y="200" fill="#38bdf8" font-size="11px" text-anchor="middle">1.65</text>

  <!-- 25 Users: 2.19 req/s -> height = 2.19/3 * 280 = 204.4 -> y = 155.6 -->
  <rect x="455" y="156" width="30" height="204" fill="#0284c7" rx="3" />
  <text x="470" y="150" fill="#38bdf8" font-size="11px" text-anchor="middle">2.19</text>

  <!-- 50 Users: 2.16 req/s -> height = 2.16/3 * 280 = 201.6 -> y = 158.4 -->
  <rect x="615" y="158" width="30" height="202" fill="#0284c7" rx="3" />
  <text x="630" y="152" fill="#38bdf8" font-size="11px" text-anchor="middle">2.16</text>

  <!-- Error Rate Line (Red) -->
  <!-- 1 User: 0% -> y = 360 -->
  <!-- 10 Users: 0% -> y = 360 -->
  <!-- 25 Users: 2.15% -> y = 360 - (2.15/50)*280 = 348 -->
  <!-- 50 Users: 40.68% -> y = 360 - (40.68/50)*280 = 132 -->
  <polyline fill="none" stroke="#ef4444" stroke-width="3" points="150,360 310,360 470,348 630,132" />
  <circle cx="150" cy="360" r="5" fill="#ef4444" />
  <circle cx="310" cy="360" r="5" fill="#ef4444" />
  <circle cx="470" cy="348" r="5" fill="#ef4444" />
  <text x="470" y="340" fill="#ef4444" font-size="11px" text-anchor="middle">2.1%</text>
  <circle cx="630" cy="132" r="6" fill="#ef4444" />
  <text x="630" y="122" fill="#ef4444" font-size="12px" font-weight="700" text-anchor="middle">40.7% (SPIKE)</text>

  <!-- X Labels -->
  <text x="150" y="380" class="label">1 User</text>
  <text x="310" y="380" class="label">10 Users</text>
  <text x="470" y="380" class="label">25 Users</text>
  <text x="630" y="380" class="label">50 Users</text>

  <!-- Legend -->
  <rect x="250" y="415" width="14" height="14" fill="#0284c7" rx="2" />
  <text x="272" y="427" class="legend">Throughput (req/s)</text>
  <line x1="430" y1="422" x2="460" y2="422" stroke="#ef4444" stroke-width="3" />
  <circle cx="445" cy="422" r="4" fill="#ef4444" />
  <text x="472" y="427" class="legend">Error Rate (%)</text>
</svg>"""

    with open(os.path.join(output_dir, 'chart_concurrency_vs_throughput_errors.svg'), 'w', encoding='utf-8') as f:
        f.write(svg2)

    # 3. Endpoint Latency Ranking (p95 latency in Stage 3)
    ep_data = [
        ('[ACTIVITY] Global Tasks (HTMX)', 15000, 30127, '#f43f5e'),
        ('[AUTH] POST /login/', 8700, 8728, '#fb7185'),
        ('[DASHBOARD] Home (HTMX Partial)', 5600, 6238, '#f59e0b'),
        ('[LEADS] Leads List (HTMX Table)', 4800, 5167, '#38bdf8'),
        ('[ACCOUNTS] Accounts List (HTMX Table)', 4200, 5192, '#38bdf8'),
        ('[CONTACTS] Contacts List (HTMX Table)', 3700, 5004, '#38bdf8'),
        ('[DASHBOARD] Home (Full Shell)', 3600, 3625, '#06b6d4'),
        ('[OPPORTUNITIES] Opps List (HTMX Table)', 2600, 4455, '#38bdf8'),
        ('[OPPORTUNITIES] Opps Chart (HTMX)', 2900, 3077, '#10b981'),
        ('[LEADS] Leads Chart (HTMX)', 2300, 3991, '#10b981'),
        ('[LEADS] Shell / Search Filter', 2200, 2578, '#10b981'),
        ('[AUTH] GET /login/', 1700, 1942, '#10b981'),
    ]

    svg3 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 500" width="100%" height="100%" style="background:#0f172a; font-family:system-ui, -apple-system, sans-serif;">
  <style>
    .title {{ font-size: 18px; font-weight: 700; fill: #f8fafc; }}
    .subtitle {{ font-size: 12px; fill: #94a3b8; }}
    .axis {{ stroke: #334155; stroke-width: 1; }}
    .ep-label {{ font-size: 12px; fill: #cbd5e1; text-anchor: end; }}
    .val-label {{ font-size: 11px; fill: #94a3b8; }}
    .grid {{ stroke: #1e293b; stroke-dasharray: 4,4; }}
  </style>

  <text x="40" y="35" class="title">Finlo CRM v2 — Endpoint Latency Breakdown (Stage 3: 25 Users)</text>
  <text x="40" y="55" class="subtitle">p95 Latency by Endpoint. The Global Tasks endpoint constitutes a severe 15.0s – 30.1s system bottleneck.</text>

  <!-- Y axis line at x=310 -->
  <line x1="310" y1="80" x2="310" y2="450" class="axis" />
  <!-- X Grid: 0, 5s, 10s, 15s (scale: 30px per 1,000ms -> 15s = 450px + 310 = 760) -->
  <line x1="460" y1="80" x2="460" y2="450" class="grid" />
  <text x="460" y="468" fill="#64748b" font-size="11px" text-anchor="middle">5s</text>
  <line x1="610" y1="80" x2="610" y2="450" class="grid" />
  <text x="610" y="468" fill="#64748b" font-size="11px" text-anchor="middle">10s</text>
  <line x1="760" y1="80" x2="760" y2="450" class="grid" />
  <text x="760" y="468" fill="#64748b" font-size="11px" text-anchor="middle">15s</text>

  <!-- Bars (y starts at 90, step=30) -->
"""
    y = 90
    for name, p95_val, max_val, color in ep_data:
        width = min(int((p95_val / 15000.0) * 450), 450)
        svg3 += f"""  <text x="300" y="{y+14}" class="ep-label">{name}</text>
  <rect x="310" y="{y}" width="{width}" height="18" fill="{color}" rx="3" />
  <text x="{315 + width}" y="{y+14}" class="val-label">{p95_val}ms (max {max_val}ms)</text>
"""
        y += 30

    svg3 += """</svg>"""

    with open(os.path.join(output_dir, 'chart_endpoint_p95_latency.svg'), 'w', encoding='utf-8') as f:
        f.write(svg3)

    # 4. Response Payload Sizes
    payload_data = [
        ('[LEADS] Leads List (HTMX Table)', 696.8, '#f43f5e'),
        ('[ACTIVITY] Global Tasks (HTMX Tasks)', 512.3, '#f43f5e'),
        ('[OPPORTUNITIES] Opps List (HTMX Table)', 367.2, '#f59e0b'),
        ('[DASHBOARD] Home (HTMX Partial)', 312.9, '#f59e0b'),
        ('[DASHBOARD] Home (Full Shell)', 312.2, '#f59e0b'),
        ('[CONTACTS] Contacts List (HTMX Table)', 273.6, '#38bdf8'),
        ('[ACCOUNTS] Accounts List (HTMX Table)', 200.7, '#38bdf8'),
        ('[AUTH] GET /login/', 74.6, '#10b981'),
        ('[OPPORTUNITIES] Filter / Shell', 64.1, '#10b981'),
        ('[ACCOUNTS] Accounts View (Shell)', 51.7, '#10b981'),
    ]

    svg4 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 450" width="100%" height="100%" style="background:#0f172a; font-family:system-ui, -apple-system, sans-serif;">
  <style>
    .title {{ font-size: 18px; font-weight: 700; fill: #f8fafc; }}
    .subtitle {{ font-size: 12px; fill: #94a3b8; }}
    .axis {{ stroke: #334155; stroke-width: 1; }}
    .ep-label {{ font-size: 12px; fill: #cbd5e1; text-anchor: end; }}
    .val-label {{ font-size: 11px; fill: #94a3b8; }}
    .grid {{ stroke: #1e293b; stroke-dasharray: 4,4; }}
  </style>

  <text x="40" y="35" class="title">Finlo CRM v2 — Response Payload Size Comparison</text>
  <text x="40" y="55" class="subtitle">HTMX table partials transmit up to 696 KB of uncompressed HTML per request over WAN.</text>

  <!-- Y axis line at x=310 -->
  <line x1="310" y1="80" x2="310" y2="400" class="axis" />
  <!-- X Grid: 0, 200KB, 400KB, 600KB (scale: 0.65px per KB -> 700KB = 455px) -->
  <line x1="440" y1="80" x2="440" y2="400" class="grid" />
  <text x="440" y="420" fill="#64748b" font-size="11px" text-anchor="middle">200 KB</text>
  <line x1="570" y1="80" x2="570" y2="400" class="grid" />
  <text x="570" y="420" fill="#64748b" font-size="11px" text-anchor="middle">400 KB</text>
  <line x1="700" y1="80" x2="700" y2="400" class="grid" />
  <text x="700" y="420" fill="#64748b" font-size="11px" text-anchor="middle">600 KB</text>

  <!-- Bars (y starts at 90, step=30) -->
"""
    y = 90
    for name, size_kb, color in payload_data:
        width = int((size_kb / 700.0) * 455)
        svg4 += f"""  <text x="300" y="{y+14}" class="ep-label">{name}</text>
  <rect x="310" y="{y}" width="{width}" height="18" fill="{color}" rx="3" />
  <text x="{315 + width}" y="{y+14}" class="val-label">{size_kb:.1f} KB</text>
"""
        y += 30

    svg4 += """</svg>"""

    with open(os.path.join(output_dir, 'chart_payload_sizes.svg'), 'w', encoding='utf-8') as f:
        f.write(svg4)

    print("Successfully generated 4 SVG performance charts in " + output_dir)

if __name__ == '__main__':
    generate_charts()

