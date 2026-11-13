# FINLONEXA CRM v2 — Consolidated Project Guide

Updated: 2026-11-13

This is the current root-level reference for the CRM architecture, local operation, security boundaries and deployment direction. Detailed component and API manuals remain under `docs/`; release history remains in `CHANGELOG.md`.

## Product and runtime

FINLONEXA CRM is a Django 6 application using Django templates, HTMX, Alpine.js and JavaScript. The application includes CRM modules, dashboards and reports, a Unified Dynamic Role Manager, FinloViewCache, calendar/calls/bookings, notifications, email integrations, imports/exports and audit history. Daphne/ASGI is the local runtime entrypoint where Channels/WebSockets are needed. Do not replace the architecture with React as part of routine optimization.

Runtime source is primarily in `finlo/`, `finlo_crm/`, `booking/`, `calls/`, `custom_fields/`, `templates/` and `static/`. Preserve migrations, translations, uploaded media, encryption keys and app assets. `finlo_jalali/` is optional but must not be deleted merely because it is unused in a given configuration.

## Authentication, roles and data boundaries

The protected built-in hierarchy is:

`SUPER_ADMIN → HEAD_OF_SALES → RSM → SSM → ASM → BDO`

Built-in role identities and hierarchy relationships are protected. The Unified Dynamic Role Manager supports configurable feature permissions and custom roles subject to mandatory company, record and reporting scopes. Permission checks must remain server-side on every request; cached HTML or data cannot substitute for authorization. Preserve batched permission evaluation and the existing sales pipeline:

`Prospecting → Qualification → Needs Analysis → Proposal/Quote → Negotiation → Closed Won / Closed Lost`

Do not use process-local cache state as the only authority for cross-session permission revocation. Cache keys for authorized data must include the relevant user/company scope, filters and authorization/data revision. Invalidation should follow successful commits and must not clear unrelated tenants' data.

## Data, cache and files

- The configured local application uses Supabase PostgreSQL; it does not silently fall back to SQLite. Keep TLS enabled and verify the target project before running commands.
- The documented Supabase transaction-pooler configuration uses port `6543`, `CONN_MAX_AGE=0`, and disabled server-side cursors. Do not issue session-level `SET` commands through the transaction pooler.
- The active driver remains psycopg2. The psycopg3 pool experiment is **NO-GO** for adoption until authenticated route, transaction-pooler, cleanup, concurrency and browser acceptance gates pass.
- Supabase PostgreSQL is not Redis. Celery, distributed cache and multi-instance Channels need separately configured reachable Redis. Keep Redis URLs and tokens in environment configuration only.
- Local media is not durable on serverless platforms. Vercel deployment requires a private durable object-storage backend and explicit upload/download verification. The `crm_data` bucket name alone does not establish that the application backend or access policies are configured.
- Never expose `.env`, database URLs, Redis tokens, signing/encryption keys or private media through source control, logs, browser JavaScript or documentation.

## Local development safety

Use the repository virtual environment and development settings for local work. Check the current port/process before launching a server; do not start duplicate Daphne/runserver instances or terminate a process without identifying it. `/health/` is a useful liveness check but does not prove authenticated CRM routes are healthy.

Do not run `migrate`, `flush`, seed/bootstrap commands, or account creation against the existing Supabase database without explicit approval and a reviewed target/schema preflight. Do not use the Django test runner against live Supabase. Prefer isolated SQLite tests for pure authorization logic and a disposable PostgreSQL instance for transaction/pooler acceptance.

Generated `__pycache__`, Ruff caches and collected `staticfiles/` are reproducible, but do not remove or regenerate them while a build/server operation depends on them. Preserve `.venv/`, `.env`, encryption keys and media.

## Deployment direction

The current technical recommendation is a **hybrid Vercel architecture**, not a production-ready deployment:

| Component | Proposed location | Current readiness |
|---|---|---|
| Django HTTP/HTMX | Vercel Python Functions using Django ASGI detection | Preview not verified |
| PostgreSQL | Existing Supabase project, region/network path to be confirmed | Connection works locally; production capacity/latency not accepted |
| Cache and Channels layer | Managed TLS Redis shared by app instances | Provider/limits and cross-session behavior need acceptance |
| Celery worker and single Beat scheduler | Separate persistent worker host | Required for scheduled/long-running work; not provisioned/verified |
| User uploads and generated durable files | Private object storage | Backend integration and access policy need verification |
| WebSockets | Vercel Fluid Compute only if account limits/lifecycle pass; otherwise a compatible dedicated service | Authenticated lifecycle not accepted |

Vercel request functions do not replace persistent Celery workers or Beat. Do not assume Vercel Daemons are entitled or suitable without checking the actual account. Use a single scheduler and audit task idempotency/retries before enabling jobs. Place compute and external services near the database where available, then measure; proximity alone does not guarantee sub-second routes.

`finlo.settings.vercel` is opt-in and intentionally requires secure environment configuration. It uses Django's detected ASGI application, secure cookie/proxy configuration, transaction-pooler-safe DB settings, shared Redis configuration and a durable media backend. Set deployment secrets only in the appropriate Vercel environment. Do not add migrations to build/import/startup. Do not add a duplicate `api` entrypoint or catch-all `vercel.json` unless the verified platform setup requires it.

Before preview: use a disposable/staging database, isolated Redis namespace and queue, exact allowed host/CSRF origins, access protection, private storage credentials, and a tested rollback. Do not connect a write-capable preview to production CRM records. No deployment is authorized by this guide.

## CSP and frontend behavior

Do not add `unsafe-eval` or `unsafe-inline` to suppress browser messages. HTMX's `hx-on` and JavaScript-valued `hx-vals` expressions rely on evaluation; strict CSP requires migrating those patterns to static JSON, form controls/`hx-include`, and external delegated listeners before setting `htmx.config.allowEval = false`. The generic list paths have been statically hardened, but the whole CRM has not been validated under an active strict CSP.

Preserve `navigation_history.js`, FinloViewCache identity/scope behavior, HTMX request headers, chart cleanup/reinitialization and mutation invalidation. Do not cache a skeleton as a complete page. The five-second welcome overlay is intentional and was explicitly kept unchanged; report it separately from server and content timing.

## Canonical documentation

- `FINLO_CRM_TECHNICAL_STATUS.md` — consolidated investigation evidence, acceptance status and next safe steps.
- `WORKSPACE_GUIDE.md` — repository and generated-file preservation notes.
- `SUPABASE-MIGRATION.md` — Supabase connectivity and safety instructions; its bootstrap commands are not approval to migrate.
- `VERCEL-DEPLOYMENT.md` — temporary UAT constraints and access gates; it includes older hosting handoff notes that should be read alongside the current hybrid recommendation above.
- `CHANGELOG.md` — released product changes.
- `docs/` — detailed app/API/component manuals.

