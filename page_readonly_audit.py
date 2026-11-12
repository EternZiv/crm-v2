"""Bounded page audit. Read-only PostgreSQL session, no persistent session/cache writes.

Parent mode runs each page in its own child with a 35-second wall-clock deadline.
Only explicitly registered menu GET destinations are included; no action crawler.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def child(route):
    import faulthandler
    faulthandler.dump_traceback_later(20)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'finlo.settings'
    from django.conf import settings
    settings.INSTALLED_APPS = [a for a in settings.INSTALLED_APPS if a != 'daphne']
    settings.SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    db = settings.DATABASES['default']
    db['CONN_MAX_AGE'] = 0
    db['OPTIONS']['connect_timeout'] = 6
    db['OPTIONS'].pop('pool', None)
    import django
    django.setup()
    from django.db import connection, connections
    from django.db.backends.utils import CursorWrapper
    groups = {}
    blocked_writes = []
    original = CursorWrapper.execute
    def execute(cursor, sql, params=None):
        if not sql.lstrip().upper().startswith(('SELECT', 'SHOW', 'SET ', 'SAVEPOINT ', 'RELEASE SAVEPOINT ', 'ROLLBACK TO SAVEPOINT ')):
            blocked_writes.append(sql.lstrip().split()[0].upper())
            raise RuntimeError('AUDIT_BLOCKED_NON_READ_SQL')
        import re
        pattern = re.sub(r"'[^']*'|\b\d+\b", '?', sql)
        frame = sys._getframe(1)
        site = 'framework'
        while frame:
            name = frame.f_code.co_filename.replace('\\', '/')
            if '/crm-v2/' in name and '/.venv/' not in name:
                site = name.split('/crm-v2/')[-1] + ':' + str(frame.f_lineno)
                break
            frame = frame.f_back
        start = time.perf_counter()
        try:
            return original(cursor, sql, params)
        finally:
            key = (pattern, site)
            row = groups.setdefault(key, {'sql': pattern[:300], 'site': site, 'count': 0, 'seconds': 0, 'max': 0})
            elapsed = time.perf_counter() - start
            row['count'] += 1
            row['seconds'] += elapsed
            row['max'] = max(row['max'], elapsed)
    CursorWrapper.execute = execute
    CursorWrapper.executemany = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('AUDIT_BLOCKED_BATCH_SQL'))
    from django.contrib.auth import get_user_model, SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
    from django.contrib.sessions.backends.signed_cookies import SessionStore
    from django.test import Client
    user = get_user_model().objects.get(username='test_superadmin', is_active=True)
    session = SessionStore()
    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session['active_company_id'] = user.company_id
    client = Client(raise_request_exception=True)
    client.cookies[settings.SESSION_COOKIE_NAME] = session._get_session_key()
    results = []
    fragment = False
    try:
        for temperature in ('cold', 'warm'):
            groups.clear()
            blocked_writes.clear()
            import cProfile
            import pstats
            profiler = cProfile.Profile()
            start = time.perf_counter()
            profiler.enable()
            try:
                from django.db import transaction
                # Transaction-local protection never persists on a pooler backend.
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('SET TRANSACTION READ ONLY')
                        cursor.execute("SET LOCAL statement_timeout = '6000ms'")
                    headers = {'HTTP_HX_REQUEST': 'true', 'HTTP_HX_TARGET': 'settings-content'} if fragment else {}
                    response = client.get(route, HTTP_HOST='localhost', **headers)
                status = response.status_code
                error = None
                body = response.content.decode('utf-8', errors='replace')
                body_flags = [marker for marker in ('Method Not Allowed', 'Traceback (most recent call last)', 'ProgrammingError at', 'OperationalError at') if marker in body]
            except Exception as exc:
                status = None
                error = 'ReadOnlyGuardBlockedWrite' if blocked_writes or 'AUDIT_BLOCKED' in str(exc) else type(exc).__name__
                body_flags = []
            if blocked_writes and not error:
                error = 'ReadOnlyGuardBlockedWrite'
            profiler.disable()
            stages = {}
            functions = []
            for (filename, line, function), (_, _, exclusive, _, _) in pstats.Stats(profiler).stats.items():
                functions.append({'file': filename.replace('\\', '/').split('/crm-v2/')[-1], 'function': function, 'exclusive_seconds': exclusive})
                category = 'other'
                if 'psycopg' in function and 'connect' in function: category = 'db_connect'
                elif 'psycopg' in filename or 'psycopg' in function or function == 'execute': category = 'sql_driver'
                elif 'context_processors' in filename: category = 'context_processors'
                elif 'authorization' in filename or 'permission' in filename: category = 'permissions'
                elif 'middleware' in filename: category = 'middleware'
                elif 'template' in filename: category = 'templates'
                elif 'dashboard' in filename: category = 'dashboard'
                stages[category] = stages.get(category, 0) + exclusive
            results.append({'temperature': 'fragment' if fragment else temperature, 'status': status, 'error': error, 'body_flags': body_flags,
                'total_seconds': time.perf_counter()-start, 'sql_count': sum(r['count'] for r in groups.values()),
                'sql_seconds': sum(r['seconds'] for r in groups.values()), 'exclusive_stages': stages,
                'top_functions': sorted(functions, key=lambda r: r['exclusive_seconds'], reverse=True)[:12],
                'top_sql': sorted(groups.values(), key=lambda r: r['seconds'], reverse=True)[:8]})
            if error: break
            if status == 302 or 'Method Not Allowed' in body_flags: fragment = True
        print('AUDIT_JSON ' + json.dumps({'route': route, 'results': results}), flush=True)
    finally:
        connections.close_all()


if __name__ == '__main__':
    if '--child' in sys.argv:
        child(sys.argv[-1])
    else:
        routes = sys.argv[1:]
        if routes == ['--menus']:
            os.environ['DJANGO_SETTINGS_MODULE'] = 'finlo.settings.security_test'
            import django
            django.setup()
            from finlo.menu.settings_menu import settings_registry
            from finlo.menu.my_settings_menu import my_settings_menu
            routes = ['/settings-view/', '/my-settings-view/']
            for cls in settings_registry + my_settings_menu:
                obj = cls()
                url = str(getattr(obj, 'url', '') or '')
                if url.startswith('/'): routes.append(url)
                for item in getattr(obj, 'items', []):
                    if isinstance(item, dict):
                        url = str(item.get('url', '') or '')
                        if url.startswith('/'): routes.append(url)
            routes += ['/crm/leads/leads-view/?section=sales', '/crm/accounts/accounts-view/?section=people',
                '/crm/contacts/contacts-view/?section=people', '/crm/opportunities/opportunities-view/?section=sales',
                '/reports/reports-list-view/?section=analytics', '/calendar/calendar-view/?section=schedule',
                '/dashboard/dashboard-list-view/?section=analytics']
        output_path = Path('FINLO_READONLY_PAGE_RESULTS.json')
        output = json.loads(output_path.read_text()) if output_path.exists() else []
        if '--menus' in sys.argv:
            done = {r['route'] for r in output}
            routes = [r for r in routes if r not in done]
        for route in routes:
            process = None
            try:
                process = subprocess.Popen([sys.executable, __file__, '--child', route], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(timeout=35)
                result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
                line = next((l[11:] for l in result.stdout.splitlines() if l.startswith('AUDIT_JSON ')), None)
                row = json.loads(line) if line else {'route': route, 'blocked': 'child exited without result', 'exit': result.returncode}
                # No exception text/locals/parameters are persisted from database errors.
                if not line:
                    row['exception_types'] = [l.split(':',1)[0] for l in result.stderr.splitlines() if l.startswith(('django.', 'psycopg', 'RuntimeError', 'ModuleNotFoundError'))]
            except subprocess.TimeoutExpired:
                if process is not None:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
                    else:
                        process.kill()
                    process.communicate(timeout=5)
                row = {'route': route, 'blocked': '35-second external deadline'}
            output = [r for r in output if r['route'] != route] + [row]
            Path('FINLO_READONLY_PAGE_RESULTS.json').write_text(json.dumps(output, indent=2))
            print(json.dumps({'route': route, 'blocked': row.get('blocked'), 'results': [
                {k: r[k] for k in ('temperature','status','error','total_seconds','sql_count','sql_seconds')}
                for r in row.get('results', [])]}), flush=True)
