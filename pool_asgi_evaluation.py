"""Isolated read-only ASGI experiment; run with 'baseline' for psycopg2."""
import asyncio
import os
import statistics
import sys
import time
import faulthandler
import re
import hashlib
import inspect
from collections import defaultdict
sql_groups={}
faulthandler.dump_traceback_later(15, repeat=True)
from pathlib import Path

pooled = 'baseline' not in sys.argv
if pooled:
    sys.path.insert(0, str(Path(__file__).parent / '.pool-eval-deps'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings')
from django.conf import settings
settings.INSTALLED_APPS = [a for a in settings.INSTALLED_APPS if a != 'daphne']
db = settings.DATABASES['default']
db['CONN_MAX_AGE'] = 0
db['DISABLE_SERVER_SIDE_CURSORS'] = True
db['OPTIONS']['connect_timeout'] = 8
if pooled:
    db['OPTIONS'].update(prepare_threshold=None, pool={'min_size': 1, 'max_size': 2, 'timeout': 8, 'max_waiting': 4, 'max_idle': 30, 'max_lifetime': 120})
import django
django.setup()
from django.core.asgi import get_asgi_application
from django.db import connections
from django.db.backends.utils import CursorWrapper
from contextvars import ContextVar
query_count=ContextVar('query_count',default=None)
original_execute=CursorWrapper.execute
def readonly_execute(self,sql,params=None):
    if not sql.lstrip().upper().startswith(('SELECT','SHOW','SET ')):
        raise RuntimeError('Evaluation blocked a non-read SQL statement')
    count=query_count.get()
    if count is not None: count[0]+=1
    start=time.perf_counter()
    try:
        return original_execute(self,sql,params)
    finally:
        if 'diagnostic' in sys.argv:
            # Parameters are never printed; literals are redacted as well.
            pattern=re.sub(r"'[^']*'|\b\d+\b",'?',sql)
            site='unknown'
            frame=sys._getframe(1)
            while frame is not None:
                name=frame.f_code.co_filename.replace('\\','/')
                if ('/finlo/' in name or '/finlo_crm/' in name) and '/.venv/' not in name:
                    site=name.split('crm-v2/')[-1]+':'+str(frame.f_lineno)
                    break
                frame=frame.f_back
            fingerprint=hashlib.sha256(pattern.encode()).hexdigest()[:12]
            key=(fingerprint,site)
            row=sql_groups.setdefault(key,{'fingerprint':fingerprint,'site':site,'count':0,'seconds':0,'max':0,'pattern':pattern[:220]})
            duration=time.perf_counter()-start
            row['count']+=1; row['seconds']+=duration; row['max']=max(row['max'],duration)
CursorWrapper.execute=readonly_execute
cookie=b''
if 'authenticated' in sys.argv:
    from django.contrib.auth import get_user_model, SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
    from django.contrib.sessions.backends.signed_cookies import SessionStore
    settings.SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies'
    user=get_user_model().objects.get(username='test_superadmin',is_active=True)
    session=SessionStore()
    session[SESSION_KEY]=str(user.pk)
    session[BACKEND_SESSION_KEY]='django.contrib.auth.backends.ModelBackend'
    session[HASH_SESSION_KEY]=user.get_session_auth_hash()
    session['active_company_id']=user.company_id
    cookie=(settings.SESSION_COOKIE_NAME+'='+session._get_session_key()).encode()

application = get_asgi_application()
async def request(path='/login/'):
    section = {'/dashboard/': b'section=home', '/crm/leads/leads-view/': b'section=sales', '/crm/accounts/accounts-view/': b'section=people', '/crm/opportunities/opportunities-view/': b'section=sales'}.get(path,b'')
    count=[0]; query_count.set(count)
    queue = asyncio.Queue()
    await queue.put({'type':'http.request','body':b'','more_body':False})
    start=time.perf_counter(); status=None; first=None
    async def send(message):
        nonlocal status, first
        if message['type']=='http.response.start':
            status=message['status']; first=time.perf_counter()-start
            if status in (301,302):
                print('REDIRECT',[(k.decode(),v.decode()) for k,v in message.get('headers',[]) if k.lower()==b'location'],flush=True)
    async def receive(): return await queue.get()
    await asyncio.wait_for(application({'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':'GET','scheme':'http','path':path,'raw_path':path.encode(),'query_string':section,'headers':[(b'host',b'localhost'),(b'cookie',cookie)],'server':('localhost',8001),'client':('127.0.0.1',12345)},receive,send),20)
    elapsed=time.perf_counter()-start
    print('REQUEST',path,status,round(first or 0,4),round(elapsed,4),'SQL',count[0],flush=True)
    return elapsed
async def main():
    if 'diagnostic' in sys.argv:
        import cProfile
        import pstats
        for temperature in ['cold','warm']:
            sql_groups.clear()
            profiler=cProfile.Profile(); profiler.enable()
            await request('/crm/opportunities/opportunities-view/' if 'opportunities' in sys.argv else '/dashboard/')
            profiler.disable()
            stats=pstats.Stats(profiler)
            stages=defaultdict(float)
            for (filename,line,function),(_,_,exclusive,inclusive,_) in stats.stats.items():
                name=filename.replace('\\','/')
                category='other'
                if 'psycopg' in name or 'select.select' in function: category='driver/pool/socket'
                elif 'context_processors' in name: category='context_processors'
                elif 'sales_authorization' in name or 'permission' in name: category='authorization'
                elif 'middleware' in name: category='middleware'
                elif '/template/' in name: category='templates'
                elif function=='_render_subview': category='fragment_construction'
                elif 'dashboard' in name: category='dashboard/widgets'
                elif '/views/' in name: category='views'
                stages[category]+=exclusive
            print('STAGES_EXCLUSIVE',temperature,dict(stages),flush=True)
            print('SQL_GROUPS',temperature,sorted(sql_groups.values(),key=lambda r:r['seconds'],reverse=True),flush=True)
        return
    if 'authenticated' in sys.argv:
        for path in ['/dashboard/','/crm/leads/leads-view/','/crm/accounts/accounts-view/','/crm/opportunities/opportunities-view/']:
            times=[await request(path) for _ in range(3)]
            print('ROUTE',path,'median',statistics.median(times),'max',max(times),flush=True)
        return
    times=[]
    for _ in range(10): times.append(await request())
    print('SEQUENTIAL',dict(min=min(times),median=statistics.median(times),max=max(times)),flush=True)
    print('CONCURRENT_TWO',await asyncio.gather(request(),request()),flush=True)
asyncio.run(main())
if pooled:
    pool=connections['default'].pool
    print('POOL_STATS',pool.get_stats(),flush=True)
    connections['default'].close_pool()
faulthandler.cancel_dump_traceback_later()
