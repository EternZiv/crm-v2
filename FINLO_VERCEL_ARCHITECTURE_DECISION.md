# Architecture decision

Select Option B: Vercel Django ASGI HTTP + WebSockets, external Celery worker and singleton beat, managed TLS Redis, Supabase Mumbai, durable private object storage. This preserves Celery/Channels without depending on beta worker entitlement. Vercel Daemons may be evaluated later if available and compatible.

Option A full Vercel is conditional on Daemon entitlement, scheduler behavior, durable job delivery and Channels lifecycle acceptance. Option C dedicated Django hosting is the fallback with the simplest runtime continuity but more server maintenance. Hybrid adds Redis/storage/network operations but avoids a worker rewrite. No paid services created.

Place compute near Mumbai (candidate bom1, confirm account availability); colocate Redis/workers/storage. Region changes do not remove SQL round trips or guarantee subsecond performance. Costs depend on function CPU/memory duration, websocket lifetime, Redis connections/commands, worker uptime, database capacity and object-storage transfer. Exact quotes require chosen plans.

Worker commands: celery -A finlo.finlo_celery:app worker --loglevel=INFO; celery -A finlo.finlo_celery:app beat --loglevel=INFO. Use one scheduler, external durable beat state or approved scheduler backend; these commands are proposals, not launched services. Audit retries/idempotency before enabling business jobs. Do not run preview workers against production queues.

