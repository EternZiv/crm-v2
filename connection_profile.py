"""Bounded read-only connection lifecycle experiment. Never prints credentials."""
import os
import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings')
from django.conf import settings
settings.INSTALLED_APPS = [a for a in settings.INSTALLED_APPS if a != 'daphne']
import django
django.setup()
from django.db import connection
from django.test import Client
import psycopg2

cfg = connection.settings_dict
host, port = cfg['HOST'], int(cfg['PORT'] or 5432)
print('SETTINGS', dict(backend=cfg['ENGINE'], host_type='supabase pooler' if 'pooler.supabase' in host else 'other', port=port, sslmode=cfg['OPTIONS'].get('sslmode'), max_age=cfg['CONN_MAX_AGE'], health_checks=cfg['CONN_HEALTH_CHECKS'], driver='psycopg2', worker='Daphne ASGI'), flush=True)
params = connection.get_connection_params()
params['connect_timeout'] = 8
def summary(label, values):
    print(label, dict(n=len(values), minimum=round(min(values),4), median=round(statistics.median(values),4), maximum=round(max(values),4)), flush=True)
dns=[]; tcp=[]; fresh=[]; first=[]; reused=[]
for i in range(5):
    start=time.perf_counter(); socket.getaddrinfo(host,port); dns.append(time.perf_counter()-start)
    start=time.perf_counter()
    with socket.create_connection((host,port),timeout=8): pass
    tcp.append(time.perf_counter()-start)
    start=time.perf_counter(); conn=psycopg2.connect(**params); fresh.append(time.perf_counter()-start)
    conn.autocommit=True
    with conn.cursor() as cur:
        start=time.perf_counter(); cur.execute('SELECT 1'); cur.fetchone(); first.append(time.perf_counter()-start)
        for j in range(3):
            start=time.perf_counter(); cur.execute('SELECT 1'); cur.fetchone(); reused.append(time.perf_counter()-start)
    conn.close()
for label, values in [('DNS',dns),('TCP',tcp),('CONNECT_TLS_AUTH_COMBINED',fresh),('FIRST_SQL',first),('REUSED_SQL',reused)]: summary(label,values)
def probe(_):
    start=time.perf_counter()
    with psycopg2.connect(**params) as conn:
        with conn.cursor() as cur: cur.execute('SELECT 1'); cur.fetchone()
    conn.close()
    return time.perf_counter()-start
with ThreadPoolExecutor(max_workers=2) as executor: summary('CONCURRENT_TWO',list(executor.map(probe,range(4))))
for age in [0,60]:
    connection.close(); cfg['CONN_MAX_AGE']=age
    timings=[]; counts=[]
    for i in range(10):
        # Test Client disconnects close_old_connections; emulate the actual
        # request boundary explicitly for the no-reuse control.
        if age == 0:
            connection.close()
        count=[0]
        def sql(execute,statement,params,many,context):
            count[0]+=1
            return execute(statement,params,many,context)
        start=time.perf_counter()
        with connection.execute_wrapper(sql): response=Client().get('/login/',HTTP_HOST='localhost')
        timings.append(time.perf_counter()-start); counts.append(count[0])
        print('LOGIN',age,i,response.status_code,round(timings[-1],4),count[0],flush=True)
    summary('LOGIN_MAX_AGE_'+str(age),timings)
connection.close()
