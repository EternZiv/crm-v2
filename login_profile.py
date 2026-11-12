"""Read-only anonymous login profiling; no server or database writes."""
import os
import time
import faulthandler
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings')
from django.conf import settings
settings.INSTALLED_APPS = [a for a in settings.INSTALLED_APPS if a != 'daphne']
import django
django.setup()
from django.test import Client
from django.db import connection
from django.db.backends.base.base import BaseDatabaseWrapper

original_connect = BaseDatabaseWrapper.connect
def connect(self):
    start = time.perf_counter()
    try:
        return original_connect(self)
    finally:
        print('CONNECT', round(time.perf_counter() - start, 4), flush=True)

def sql(execute, statement, params, many, context):
    start = time.perf_counter()
    try:
        return execute(statement, params, many, context)
    finally:
        print('SQL', round(time.perf_counter() - start, 4), statement[:180], flush=True)

faulthandler.dump_traceback_later(8, repeat=True)
with patch.object(BaseDatabaseWrapper, 'connect', connect), connection.execute_wrapper(sql):
    for i in range(10):
        start = time.perf_counter()
        response = Client().get('/login/', HTTP_HOST='localhost')
        print('TOTAL', i, response.status_code, round(time.perf_counter()-start, 4), flush=True)
        connection.close()
faulthandler.cancel_dump_traceback_later()
