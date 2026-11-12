"""Opt-in Vercel settings. Select with DJANGO_SETTINGS_MODULE; never imports migrations."""
import json
import os
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from finlo.settings import *  # noqa: F403

if not IS_PRODUCTION or DEBUG:
    raise ImproperlyConfigured('Vercel settings require production mode and DEBUG=False.')
if VERCEL_UAT_MODE:
    raise ImproperlyConfigured('Vercel deployment settings do not allow UAT in-memory services.')

def required_service(name):
    value = os.environ.get(name, '')
    parsed = urlsplit(value)
    if parsed.scheme != 'rediss' or not parsed.hostname or parsed.hostname in {'localhost', '127.0.0.1', '::1'}:
        raise ImproperlyConfigured(f'{name} must be an external TLS Redis URL.')
    return value

CHANNEL_LAYERS = {'default': {'BACKEND': 'channels_redis.core.RedisChannelLayer', 'CONFIG': {'hosts': [required_service('CHANNEL_REDIS_URL')]}}}
CELERY_BROKER_URL = required_service('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = required_service('CELERY_RESULT_BACKEND')
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': required_service('CACHE_REDIS_URL'), 'KEY_PREFIX': os.environ.get('CACHE_KEY_PREFIX', 'finlo-vercel'), 'TIMEOUT': 300}}

DATABASES['default']['CONN_MAX_AGE'] = 0
DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
DATABASES['default'].setdefault('OPTIONS', {})['connect_timeout'] = 8

# Django 6 uses STORAGES, not the legacy STATICFILES_STORAGE setting.
# Storage provider/dependencies are supplied only after provider approval.
media_backend = os.environ.get('FINLO_MEDIA_STORAGE_BACKEND', '')
if not media_backend or media_backend == 'django.core.files.storage.FileSystemStorage':
    raise ImproperlyConfigured('Configure durable private media storage before deployment.')
STORAGES = {
    'default': {'BACKEND': media_backend, 'OPTIONS': json.loads(os.environ.get('FINLO_MEDIA_STORAGE_OPTIONS', '{}'))},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
FILE_UPLOAD_TEMP_DIR = '/tmp'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
