"""Read-only pool admission/recovery checks; no writes or session SET."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent / '.pool-eval-deps'))
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','finlo.settings')
from django.conf import settings
settings.INSTALLED_APPS=[a for a in settings.INSTALLED_APPS if a!='daphne']
import django
django.setup()
from django.db import connection
from psycopg_pool import ConnectionPool, PoolTimeout
import time

params=connection.get_connection_params()
params.update(prepare_threshold=None,connect_timeout=8,autocommit=True)
pool=ConnectionPool(kwargs=params,min_size=0,max_size=2,timeout=1,max_waiting=2,check=ConnectionPool.check_connection)
try:
    a=pool.getconn(timeout=8); b=pool.getconn(timeout=8)
    start=time.perf_counter()
    try:
        pool.getconn(timeout=.5)
        raise AssertionError('pool exceeded limit')
    except PoolTimeout:
        print('ACQUISITION_TIMEOUT_PASS',round(time.perf_counter()-start,3),flush=True)
    pool.putconn(a); pool.putconn(b)
    with pool.connection(timeout=8) as conn:
        assert conn.prepare_threshold is None
        with conn.cursor() as cursor:
            cursor.execute('SELECT 1'); assert cursor.fetchone()==(1,)
        conn.close()
    with pool.connection(timeout=8) as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT 1'); assert cursor.fetchone()==(1,)
    print('CLOSED_CONNECTION_RECOVERY_PASS',flush=True)
    print('POOL_STATS',pool.get_stats(),flush=True)
finally:
    pool.close()
