# Temporary Vercel UAT deployment

This guide is for a short-lived, access-restricted preview deployment to test
the existing synthetic UAT data. It is not the recommended permanent hosting
architecture; the long-term handoff target is an Oracle Cloud VPS.

## Vercel project configuration

Import `EternZiv/crm-v2` from GitHub and set the project root to the repository
root. Keep framework detection, build command, and output directory on their
defaults. **Do not add `vercel.json` for this project:** Vercel detects Django
from root `manage.py`, uses the configured ASGI application
(`horilla.asgi.application`), and runs `collectstatic` because `STATIC_ROOT` is
configured. No persistent web-server `start` command is used; requests run as
Vercel Functions. Do not add migration or seeding commands to build or startup.

The `.python-version` file selects Python 3.12, supported by Vercel and
required by this project's Django dependency. Include this file in the Git
deployment commit. Static files are built for the deployment and served from
Vercel's CDN.

## Environment variables

Set these in the **Preview** environment only for the temporary UAT deployment.
Use newly generated credentials after rotating the previously exposed Supabase
database password. Do not reuse a privileged database role for application
runtime.

| Variable | Required value / purpose |
| --- | --- |
| `DEBUG` | `0` |
| `SECRET_KEY` | A new, unique Django secret (at least 50 characters); store only in Vercel. |
| `DATABASE_URL` | Supabase PostgreSQL transaction-pooler URL on port `6543`, with TLS required. Obtain a fresh URL after password rotation; URL-encode reserved password characters. |
| `VERCEL_UAT_MODE` | Set to `1` only for the temporary, limited UAT mode described below. Omit it for normal deployments. |
| `REDIS_URL` | Required for normal Vercel deployments. A real, managed Redis URL reachable from Vercel; it configures Channels and is the default Celery broker/result backend. Not required in the limited UAT mode. |
| `ENVIRONMENT` | `production` |
| `DB_CONN_MAX_AGE` | `0` for short-lived serverless database connections. |
| `DISABLE_SERVER_SIDE_CURSORS` | `1` for transaction-pooler compatibility. |

Vercel supplies `VERCEL`, `VERCEL_URL`, `VERCEL_BRANCH_URL`, and
`VERCEL_PROJECT_PRODUCTION_URL` as system environment variables. The settings
add only the exact hostnames Vercel supplies for the deployment, branch, and
project production domain to `ALLOWED_HOSTS`, and add their HTTPS origins to
`CSRF_TRUSTED_ORIGINS`. This allows the stable project domain
(`crm-v2-ochre.vercel.app`) as well as the current deployment URL without
allowing arbitrary Vercel or external domains. Do not override system variables.
Only set `ALLOWED_HOSTS` or `CSRF_TRUSTED_ORIGINS` if additional, explicitly
owned hostnames/origins are needed. `CHANNEL_REDIS_URL` and `SITE_URL` are
optional; the former can point Channels to a separate Redis service and the
latter is relevant to calendar webhooks.

### Redis-free UAT mode

For a short, access-restricted core CRM smoke test only, set
`VERCEL_UAT_MODE=1` in the Vercel **Preview** environment and omit `REDIS_URL`.
The flag is rejected outside Vercel and is disabled by default. In this mode,
Django Channels uses its in-memory channel layer, and asynchronous automation
and scoring dispatch are disabled in favor of their existing synchronous
execution paths. Django authentication, sessions, CSRF, role permissions, and
the PostgreSQL database configuration are unchanged. Celery workers and
schedulers are not started.

This mode is not full CRM compatibility:

- CRM notification records remain database-backed and visible in the
  application inbox. Real-time delivery is process-local and not reliable
  across Vercel Functions or WebSocket reconnects.
- Scheduled mail, scheduled exports, workflow time triggers, and any other
  Celery task that requires a worker are unsupported. No worker or scheduler
  runs in this mode; attempts to enqueue a task may fail because no broker is
  available, and queued work is not guaranteed to execute. Do not invoke those
  operations during UAT.
- Synchronous automation and scoring can run during writes. Audit active
  automation rules before write-based testing; automation actions may send
  email or change CRM records. Do not use this mode if those effects cannot be
  safely controlled.
- Channels and Celery retain the Redis-backed production configuration when
  this flag is absent. Use a real managed Redis service for normal operation.

The database URL must use the intended UAT database, not a production database.
Confirm the credential was rotated and the target URL was reviewed before
adding it to Vercel. No database connection or credential rotation is performed
by this guide.

## Deployment access gate

Do not deploy or share a public preview until all of these are true:

- The Supabase password shown in the earlier editor selection has been rotated
  through Supabase, and the old credential is no longer accepted.
- The new runtime credential is least-privilege and scoped to the intended UAT
  project. Backup/recovery readiness and the current migration state have been
  reviewed; no migration is performed by Vercel.
- Preview-only environment variables are set without exposing values in Git,
  build logs, browser code, or this document.
- Vercel Deployment Protection (or an equivalent access restriction available
  on the selected plan) is enabled and verified before the preview is shared.
- The owner has explicitly approved the deployment and use of the live UAT
  database.

Until those gates are met, keep the project undeployed. Vercel Hobby is suitable
only for non-commercial personal use under Vercel's current fair-use guidance;
confirm that this temporary UAT qualifies before using that plan.

Vercel documents **Vercel Authentication** and **All Deployments** protection
as available on all plans. Before adding the live `DATABASE_URL`, enable
Deployment Protection for **All Deployments** with **Vercel Authentication**
and verify an unauthenticated browser is blocked. Access to Vercel-protected
deployments is separate from Django login. Hobby accounts can grant access to
only one external Vercel user; that is sufficient only if one person performs
the six CRM-role tests. Vercel **Password Protection** is available only on Pro
and Enterprise. The current account plan and settings must be checked directly
in the Vercel Dashboard; they are not visible from this repository.

## Local checks

The following command checks Django's connection using the rotated credential
stored in the ignored local `.env`. It executes only `SELECT 1`; it does not
read or change CRM records, run migrations, or contact Redis:

```powershell
& .\.venv\Scripts\python.exe manage.py shell -c "from django.db import connection; connection.ensure_connection(); cursor = connection.cursor(); cursor.execute('SELECT 1'); assert cursor.fetchone() == (1,); print('Read-only database connectivity passed.')"
```

This does not prove a Vercel build or deployment works. The isolated
`check --deploy` and `collectstatic --dry-run` checks previously completed
locally; `check --deploy` reported only the HSTS subdomain/preload
recommendations (`security.W005` and `security.W021`). No fake Redis endpoint
is required for these local checks.

## GitHub-to-Vercel checklist

- Push only reviewed source and deployment documentation to the intended
  GitHub branch.
- Confirm `.env`, SQLite database files, media, and local virtual environments
  are ignored; never add credentials to Git.
- Confirm `.python-version` is tracked and contains `3.12`.
- Import the repository into Vercel at the repository root; use automatic
  Django framework/build detection and the default output directory.
- Add the preview environment variables above only after credential rotation
  and explicit approval.
- Enable and verify access protection before using the generated preview URL.
- Do not run `migrate`, `flush`, seed commands, or destructive test suites as
  part of a Vercel build or against Supabase.

## UAT test plan

Use only the existing six test accounts, unchanged hierarchy, and synthetic
records in the approved UAT company. Do not create, edit, or delete business
records as part of the initial smoke test.

1. Open the protected preview over HTTPS and verify login page and static assets.
2. Log in separately with each of the six approved accounts; verify sessions
   remain valid across navigation and logout clears the session.
3. Open Leads, Accounts, Contacts, Opportunities, pipeline, dashboards, and
   reports; confirm expected synthetic UAT data is returned.
4. Verify each account can see only its authorized company, region, team, owner,
   and assignment scope. Check denied access with direct URLs/API requests, not
   only hidden menu items.
5. Confirm no test account gains Django superuser privileges and no UAT user or
   hierarchy records are changed.
6. Record failures and request authorization before any write-based follow-up
   tests. Do not use Django's test runner against Supabase.

## Temporary deployment limitations

- **Celery and Redis:** In Redis-free UAT mode no Celery worker or Celery Beat
  service is started. Scheduled mail, exports, workflow time triggers, and
  worker-dependent tasks are unsupported. Automation and scoring use
  synchronous execution, which can increase request time; audit configured
  automations for external side effects before any writes.
- **WebSockets:** Vercel documents Python WebSocket support, but a connection is
  tied to a Function instance and closes at its maximum duration. Reconnects can
  reach another instance. Treat live notifications and calls as best-effort and
  verify separately; do not use them as a UAT gate for core CRUD.
- **Uploads and imports:** Django currently uses local media storage, and import
  flows require local filesystem paths. Serverless local files are not durable.
  Avoid uploads/imports until durable object storage and compatible import
  handling are configured.
- **Calendar and email:** External providers, credentials, callbacks, delivery,
  and related background behavior have not been verified. Calendar signal work
  uses a daemon thread in this deployment commit; serverless functions may stop
  it when the invocation ends. Do not rely on calendar synchronization during
  this UAT.
- **Long-running work:** Reports, exports, imports, and other synchronous work
  must finish within the Function duration/memory limits. Large workloads are
  out of scope for this temporary smoke test.

## Oracle Cloud VPS handoff

- Provision a supported Oracle Linux/Ubuntu VM, restrict SSH, enable firewall
  rules, apply security updates, and configure monitoring and backups.
- Deploy the same reviewed application commit behind a TLS-terminating reverse
  proxy; run Django via a production ASGI server because the CRM uses Channels.
- Run Celery worker and beat/scheduler as supervised persistent processes, with
  a private Redis service or managed Redis.
- Move media to durable object storage or a backed-up persistent volume; test
  restore and upload/download permissions.
- Set production secrets through a protected secret manager/environment, use a
  least-privilege database account, and verify Supabase TLS certificate
  validation and connection mode from the VPS.
- Review Supabase backups, migration state, permissions, and rollback plan.
  Apply only approved migrations from a trusted release environment; never
  migrate automatically at application startup.
- Re-run six-role isolation, API authorization, session/CSRF, WebSocket,
  background-task, upload, export, and backup-restore acceptance tests before
  making the VPS the production endpoint.
