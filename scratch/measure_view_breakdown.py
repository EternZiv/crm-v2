import os
import sys
import time

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings.base')

import django
django.setup()

from django.test import Client
from django.db import connection, reset_queries
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
try:
    from login_history.models import post_login
    user_logged_in.disconnect(post_login)
except Exception:
    pass

# Enable DEBUG query logging and allow testserver in this script process only
settings.DEBUG = True
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

User = get_user_model()
user = User.objects.filter(is_active=True).first()
print(f"Testing with user: {user.username if user else 'None'}")

client = Client(HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) FinloLoadTest/1.0")
client.force_login(user)

endpoints = [
    ("Dashboard Partial", "/dashboard/?section=home", {"HTTP_HX_REQUEST": "true"}),
    ("Accounts Table", "/crm/accounts/accounts-list-view/", {"HTTP_HX_REQUEST": "true"}),
    ("Leads Table", "/crm/leads/leads-list/", {"HTTP_HX_REQUEST": "true"}),
    ("Contacts Table", "/crm/contacts/contact-list-view/", {"HTTP_HX_REQUEST": "true"}),
    ("Opportunities Table", "/crm/opportunities/opportunities-list/", {"HTTP_HX_REQUEST": "true"}),
]

print("\n--- MEASURING DETAILED PER-REQUEST TIME BREAKDOWN ---")
print(f"{'Endpoint':<22} | {'HTTP':<4} | {'Total(ms)':<9} | {'SQL(ms)':<8} | {'Py+Tpl(ms)':<10} | {'SQL Queries':<11} | {'Avg SQL/q(ms)':<12}")
print("-" * 90)

for name, path, extra in endpoints:
    # Ensure connection timing
    t_conn_0 = time.perf_counter()
    connection.ensure_connection()
    t_conn_1 = time.perf_counter()
    conn_time = (t_conn_1 - t_conn_0) * 1000

    reset_queries()
    t0 = time.perf_counter()
    resp = client.get(path, **extra)
    t1 = time.perf_counter()
    
    total_time = (t1 - t0) * 1000
    queries = connection.queries
    sql_time = sum(float(q.get('time', 0)) for q in queries) * 1000
    py_time = max(0.0, total_time - sql_time)
    num_queries = len(queries)
    avg_sql = (sql_time / num_queries) if num_queries > 0 else 0

    print(f"{name:<22} | {resp.status_code:<4} | {total_time:<9.1f} | {sql_time:<8.1f} | {py_time:<10.1f} | {num_queries:<11} | {avg_sql:<12.1f}")

settings.DEBUG = False
