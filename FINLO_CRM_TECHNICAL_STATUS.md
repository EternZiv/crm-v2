# FINLONEXA CRM v2 — Consolidated Technical Status

Updated: 2026-11-13

This file consolidates the root-level audit, performance, navigation, CSP, pooling, focused repair and Vercel reports. Status refers to the evidence captured in those bounded investigations; a passing static check is not browser or production acceptance.

## Executive status

| Area | Status | What is established |
|---|---|---|
| Core application and six-role RBAC | **PARTIAL / historical PASS** | A 33-test isolated SQLite RBAC suite passed historically. Later focused cache/CSP coverage passed 18/18 in isolated settings. These are not PostgreSQL or production acceptance. |
| Navigation/cache ownership | **PARTIAL** | A Leads/Dashboard URL-content race was corrected and a local sample passed. Focused cache hardening tests passed; broad browser Back/Forward, permission revocation and multi-instance Redis behavior remain incomplete. |
| Shared Lead aggregates | **IMPLEMENTED, acceptance partial** | `LeadDataService` adds request-local/shared cache reuse and aggregate counts with user/company scope and revisions. Focused tests cover invalidation and isolation; no matched runtime benchmark establishes a production gain. |
| Generic list CSP path | **SOURCE CHECK PASS; strict-policy runtime BLOCKED** | Target list/delete templates use external delegated behavior. No active strict CSP was present in the local browser. Other CRM templates still contain HTMX evaluation patterns. |
| Export Data lazy metadata | **IMPLEMENTED; browser/runtime BLOCKED** | Initial module metadata avoids building every module's fields; requested fields are loaded after module selection and authorization is rechecked. Four focused tests passed. No valid after SQL/timing or authenticated browser comparison exists. |
| Dashboard lazy widgets/skeletons | **PARTIAL / NOT ACCEPTED** | Skeleton templates and snapshot guards exist. Dashboard still computes chart/table data together on cache miss; no safe deferral was accepted. Browser timing, duplicate fragment counts, and chart lifecycle under restore are incomplete. |
| Performance target (<1s) | **NOT VERIFIED** | No comparable cold-before/cold-after and warm-before/warm-after measurements or complete click-to-usable data. Intermittent slow requests remain unexplained. |
| psycopg3 pool | **NO-GO** | Anonymous/reused-connection benchmarks improved, but authenticated request stalls and transaction-pooler acceptance were incomplete. Keep active psycopg2 configuration. |
| Vercel production readiness | **NO-GO** | Compatibility configuration exists, but preview, database, Redis, worker, storage, WebSocket and browser acceptance gates remain. |

## Functional and performance evidence

### Historical request observations

These are individual investigation measurements, not a comparable optimization benchmark:

- Initial Export Data audit: 9.004 s / 55 SQL calls cold and 3.239 s / 30 warm. Twenty custom-field metadata lookups and ContentType lookups were observed. Lazy field metadata was implemented, but no valid after measurement was captured.
- Dashboard audit: 5.769 s / 38 SQL calls cold and 1.363 s / 10 warm. `generate_table_data` and campaign-table generation were identified in the server path. No Dashboard deferral was implemented in the focused Export task.
- Authenticated pooled profiling: Dashboard 9.473 s / 52 queries, Opportunities 7.434 s / 47 queries. Psycopg cursor wall time was dominated by socket waiting in the sample; this did not prove query execution or pool acquisition as the sole cause. No permanent stall reproduced.
- A separate local browser sample reported Dashboard ~3.45 s and earlier single samples for Leads, Accounts, Contacts, Opportunities and Reports in roughly 2.5–3.5 s. These are not standardized click-to-usable benchmarks.
- A prior report compared Dashboard cold 3.478 s / 38 queries with warm-after 0.988 s / 14 queries and called that a 71.6% optimization. This compares different cache states and is **not valid before/after evidence**; do not use the percentage as a claimed gain.
- Connection lifecycle experiment: psycopg2 fresh connection login median 1.181 s vs reused 0.428 s (four queries), but it was not a matched authenticated ASGI benchmark. Another bounded harness reported psycopg2 1.075 s vs psycopg3 pooled 0.434 s for anonymous login. Neither alone establishes safe application adoption.

### Known implementation areas

- `finlo_crm/leads/services.py`: shared lead count/stage aggregate service with user/company-scoped cache keys and data/authorization revisions.
- `finlo_crm/leads/signals.py`, `finlo/contrib/core/signals.py`: cache invalidation after successful commits for relevant Lead, status, scope, role/permission and membership changes. Unit coverage exists; cross-worker shared-cache and disposable-PostgreSQL transaction tests are still needed.
- `finlo/contrib/generics/views/chart.py`: bulk related-object lookup for chart labels to reduce per-bucket ORM lookups. Chart browser acceptance is incomplete.
- `templates/components/skeletons/` and `navigation_history.js`: skeleton components and guards against snapshotting incomplete pages. Exact skeleton display timing and full restoration acceptance remain open.
- `finlo/contrib/core/views/export_data.py` and `finlo/contrib/core/templates/export/export_view.html`: lazy field metadata request after module selection, retaining authorization checks and POST field validation. Browser/runtime acceptance is pending.
- `finlo/contrib/generics/templates/chart_view.html`: duplicate messages include were removed in a prior focused change; current toast behavior needs browser confirmation where not already covered.

## Security, cache and CSP gates

### Cache authorization

Cache entries remain user-scoped and include company/data and per-user authorization revisions. Signals schedule revision changes with `transaction.on_commit`; tenant moves account for old/new company scopes. Eighteen focused isolated tests passed for cache scope/invalidation and target template behavior. Remaining risks: real database transaction behavior, shared Redis multi-process propagation, and the operational response if invalidation writes fail. Do not relax auth checks or share data based on role ID alone.

### Content Security Policy

Local responses tested did not have an active HTML CSP header; the original Chrome warning could not be reproduced. HTMX source uses `eval` for `hx-vals="js:..."` and `new Function` for `hx-on:*`. Generic list/delete paths were migrated to delegated handlers, but other core/lead templates retain these patterns. Do not set `allowEval=false` or enforce a strict policy until remaining rendered workflows are migrated and tested. Do not add unsafe directives.

## Vercel and external services

Recommended architecture: Vercel for Django HTTP/HTMX (and WebSockets only after lifecycle tests), Supabase PostgreSQL, managed TLS Redis shared across app/Channels/Celery as configured, one separate persistent Celery worker plus one Beat scheduler, and private durable object storage. Existing Celery tasks, email, scheduled work, Channels fan-out and file handling must not be silently disabled.

Deployment settings are opt-in. Required environment configuration includes Django secret/hosts/CSRF origins, staging `DATABASE_URL`, Redis URLs/namespaces, Celery URLs, and storage backend configuration. Never print or commit values. Keep Vercel preview isolated from production records and queues. Do not run migrations automatically. Verify actual Vercel plan/regions/duration/WebSocket limits and provider free-tier limits in their dashboards before planning capacity; no account entitlement or cost is established by repository evidence.

Vercel status by gate:

- Django static/system checks and isolated ASGI import: **PASS** under safe test settings only.
- Production build/collectstatic on Vercel: **NOT TESTED**.
- Production settings startup: **BLOCKED** pending real preview environment services.
- Authenticated routes, browser, HTMX/history and six-role isolation on preview: **NOT TESTED/BLOCKED**.
- WebSocket auth/reconnect across instances: **BLOCKED**.
- Celery worker/Beat, retries/idempotency, email/calendar delivery: **BLOCKED**.
- Durable private storage and import/export: **BLOCKED**.
- Production deployment: **NO-GO**.

## Reports consolidated and caveats

This status incorporates the root reports on: authenticated stalls, DB connection lifecycle, precise profiler limits, psycopg3 pool evaluation, page audit, shared aggregate/skeleton work, focused Export repair, navigation cache hardening, performance acceptance, CSP, MES navigation proposal and Vercel compatibility/configuration/functional/performance/deployment.

The MES retained-DOM document is a proposal and explicitly advises against implementation until justified; it is not current architecture. The older Vercel guide describes temporary UAT constraints and an Oracle handoff; the current recommendation is the hybrid Vercel + external worker/Redis/storage plan, still subject to approval and acceptance. Do not treat either document as proof that a deployment occurred.

## Safe next steps

1. Confirm the current local server process and port before using it; distinguish a refused connection from application route errors. Do not start a duplicate server.
2. Complete Export Data acceptance with an authorized isolated browser/session: initial GET, allowed `fields=1`, denied metadata, checkbox submission contract, request count, console/network errors and separate SQL/timing counts. Do not use live writes.
3. Only after that gate passes, consider a Dashboard pilot with a dedicated authorized fragment endpoint; preserve edit, filters, drag/drop, PDF, chart lifecycle and cache invalidation. Measure actual initial SQL reduction first.
4. Run matched cold and warm comparisons with same identity, URL/filters, cache reset state, instrumentation and payload size. Separate server response, browser TTFB, skeleton visibility and click-to-usable.
5. For CSP, capture the actual failing origin's document response header and violation stack; then migrate remaining expression-based patterns workflow by workflow under report-only/isolated preview.
6. For deployment, provision isolated staging services and pass the Vercel, worker, Redis, storage, Channels and RBAC acceptance matrix before seeking production approval.

No production readiness, sub-second performance or full functional acceptance is claimed. No migration, production data change, commit, push or deployment is recorded by these investigations.

