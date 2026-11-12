# Deployment checklist

Production decision: NO-GO pending preview and infrastructure approval.

1. Approve isolated Vercel preview/account linkage, external worker/scheduler, Redis and private storage provider.
2. Provision disposable PostgreSQL with sanitized fixtures; do not give preview write access to live business data.
3. Configure environment variables listed in configuration report; isolate Redis namespaces and queues from production.
4. Confirm supported Python version, Mumbai compute availability, function duration, concurrent instance caps and package size under actual plan. Native Python binary wheels/system dependencies require Linux build validation.
5. Run Django deploy checks and automatic collectstatic with deployment settings. Verify private storage credentials/read/write/retention/access checks using disposable files only.
6. Review/apply staging migrations only with authorization; never import-time migrations.
7. Verify login, signed sessions, CSRF, all six roles, role Allow/Deny/Default, company scopes, HTMX/header restoration and browser caches.
8. Verify websocket handshake/auth/reconnect/revocation across instances with TLS Redis; bound reconnect/lifetimes to platform policy.
9. Test Celery delivery/retries/idempotency, singleton periodic scheduler, incoming/outgoing email with mocks, and calendar push durable delivery.
10. Test imports/exports/file sizes and long jobs; verify audit logs and failure observability.
11. Measure browser TTFB/click-to-usable and connection concurrency before production approval.

Rollback: redeploy prior approved artifact and environment selection; new settings are opt-in. Restore previous entrypoint file if necessary. No schema/data rollback required for these code changes. Stop preview workers and isolate queues before rollback. Retain existing uploads and keys. No production traffic switching is authorized.

