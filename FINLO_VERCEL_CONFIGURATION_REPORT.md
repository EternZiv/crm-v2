# Configuration report

Added opt-in finlo.settings.vercel with shared Redis caches/channel layer, explicit external TLS Celery URLs, CONN_MAX_AGE=0, disabled server cursors, 8s connect timeout, secure cookies/proxy HTTPS, and required durable media backend. No experimental psycopg3 integration. Django 6 STORAGES static backend explicitly uses compressed manifests.

ASGI now initializes Django before importing routing/consumers. Added .vercelignore to exclude local secrets, media, experiment packages and logs from CLI uploads. Existing working-tree changes and deleted reports were preserved. No .env or requirements edits.

Select DJANGO_SETTINGS_MODULE=finlo.settings.vercel and ENVIRONMENT=production/DEBUG=False through preview environment configuration. Supply SECRET_KEY, exact ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, SITE_URL, DATABASE_URL (staging), REDIS_URL, CHANNEL_REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CACHE_REDIS_URL, unique CACHE_KEY_PREFIX, FINLO_MEDIA_STORAGE_BACKEND and provider-specific FINLO_MEDIA_STORAGE_OPTIONS. Required backend dependency must be reviewed/installed once provider chosen. Never print values. Keep consistent signing/encryption keys across HTTP/worker services; do not lose existing encryption keys.

Native Django detection is used; no duplicate api entrypoint or legacy catch-all vercel.json created. Vercel currently prioritizes ASGI_APPLICATION. No automatic migration command. No deployment initiated.

