# Functional verification

| Gate | Status | Evidence |
|---|---|---|
| Local static Python syntax | PASS | Deployment settings and ASGI compiled |
| Isolated ASGI initialization | PASS | security_test settings: ProtocolTypeRouter import and Django check completed, zero issues; this does not validate Vercel production settings |
| Production build / collectstatic | NOT TESTED | Provider/settings fixture not yet available |
| Django deployment startup | BLOCKED | External Redis/media provider/staging env missing |
| RBAC regression | PASS historical | 33/33 isolated SQLite, not Vercel acceptance |
| HTTP/auth/session/HTMX | NOT TESTED on Vercel | Preview absent |
| WebSockets | BLOCKED | Fluid/account limits/shared Redis preview acceptance absent |
| Celery/email/calendar/workflows | BLOCKED | Persistent worker/scheduler not provisioned; durable delivery and retries unverified |
| Storage/import/export | BLOCKED | Provider unresolved |
| Cross-session permissions | NOT TESTED | No distributed preview |
| CRUD/browser modules | BLOCKED | Disposable staging database absent |

No business-data mutations, migrations, account changes, commits or deployments. Success of syntax checks does not establish runtime acceptance. Deployment settings deliberately reject insecure/incomplete service configuration. Required tests remain explicit release gates.

