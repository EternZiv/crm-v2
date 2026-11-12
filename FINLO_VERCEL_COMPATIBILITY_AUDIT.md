# Vercel compatibility audit

| Component | Existing | Compatibility / changes | Risk |
|---|---|---|---|
| HTTP/auth/HTMX | Django 6 ASGI | Supported framework detection from manage.py; ASGI wins when both entrypoints exist | Preview unverified |
| Realtime | Channels consumers | Current official Django guide supports WebSockets; enable Fluid, shared Redis and verify lifecycle | High pending account limits/tests |
| Celery/beat | Redis workers and periodic schedules | Ordinary request functions cannot substitute for workers; external worker + single beat | High |
| Daemons | None | Public Beta; entitlement and Celery suitability unverified | Do not assume available |
| Calendar push | process thread / Vercel branch | Audit dispatch path; durable delivery not accepted | High |
| Cache/RBAC | LocMem + request snapshots | Opt-in shared Redis; batched request permission queries preserved | Cross-session revocation unverified |
| Media | local files | Durable private storage required; provider unresolved | Blocked |
| Static | legacy storage setting | Deployment STORAGES uses compressed manifest; CDN collects static automatically | Build untested |
| DB | psycopg2 transaction pooler | max_age=0, server cursors disabled, regional placement | Capacity/latency unverified |
| Reports/imports | request file processing | Temporary /tmp only; long jobs on workers; request/file limits need preview | High |

Sources checked: https://vercel.com/docs/frameworks/full-stack/django ; https://vercel.com/blog/backends-on-vercel-python-containers-and-daemons ; https://vercel.com/docs/functions/limitations ; https://vercel.com/docs/functions/runtimes/python . Current Django guide supports ASGI Channels and automatic collectstatic. Python GA announcement supersedes older runtime pages calling it Beta. Function duration/bundle limits vary by plan/runtime; verify actual dashboard before setting them. No deployment occurred.

