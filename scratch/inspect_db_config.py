import os
import sys
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings.base')
django.setup()

from django.conf import settings
from django.db import connection

print("--- TASK 1: DJANGO DATABASE SETTINGS ---")
db_conf = settings.DATABASES['default']
print(f"ENGINE: {db_conf.get('ENGINE')}")
print(f"ATOMIC_REQUESTS: {db_conf.get('ATOMIC_REQUESTS', False)}")
print(f"AUTOCOMMIT: {db_conf.get('AUTOCOMMIT', True)}")
print(f"CONN_MAX_AGE: {db_conf.get('CONN_MAX_AGE')}")
print(f"DISABLE_SERVER_SIDE_CURSORS: {db_conf.get('DISABLE_SERVER_SIDE_CURSORS')}")
print(f"PORT: {db_conf.get('PORT')}")
print(f"HOST: {db_conf.get('HOST')}")
