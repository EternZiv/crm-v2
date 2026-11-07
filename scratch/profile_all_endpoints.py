import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finlo.settings")

import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.db import connection, reset_queries

from finlo.contrib.dashboard.views import HomePageView
from finlo_crm.leads.views.core import LeadView, LeadListView
from finlo_crm.accounts.views.core import AccountView, AccountListView
from finlo_crm.contacts.views.core import ContactView, ContactListView
from finlo_crm.opportunities import views as opp_views
from finlo.contrib.activity.views.list_view.global_views import GlobalTaskListView

User = get_user_model()
user = User.objects.filter(username="test_bdo").first()
if not user:
    user = User.objects.filter(is_active=True).first()

print(f"================================================================================")
print(f"  FINLO CRM v2 — ENDPOINT PERFORMANCE PROFILING SUITE")
print(f"  User: {user.username} | Role: {getattr(user, 'role', None)} | Company: {getattr(user, 'company', None)}")
print(f"================================================================================")

rf = RequestFactory()

def profile_view(name, path, view_class, get_params=None, is_htmx=True):
    params = get_params or {}
    extra = {"SERVER_NAME": "127.0.0.1"}
    if is_htmx:
        extra["HTTP_HX_REQUEST"] = "true"
    req = rf.get(path, params, **extra)
    req.user = user
    req.session = {'active_company': user.company.pk} if getattr(user, 'company', None) else {}

    reset_queries()
    t0 = time.perf_counter()
    view = view_class.as_view()
    response = view(req)
    if hasattr(response, 'render'):
        response.render()
    t1 = time.perf_counter()

    total_time_ms = (t1 - t0) * 1000
    queries = list(connection.queries)
    sql_time_ms = sum(float(q.get("time", 0)) for q in queries) * 1000
    python_time_ms = total_time_ms - sql_time_ms
    query_count = len(queries)
    content_size_bytes = len(response.content) if hasattr(response, 'content') else 0
    content_size_kb = content_size_bytes / 1024.0

    # Detect duplicate SQL patterns
    query_sql_prefixes = [q.get("sql", "").strip()[:80].replace('"', '').replace('\n', ' ') for q in queries]
    counts = Counter(query_sql_prefixes)
    duplicates = [(prefix, count) for prefix, count in counts.items() if count > 1]

    return {
        "name": name,
        "path": path,
        "is_htmx": is_htmx,
        "status_code": response.status_code,
        "total_ms": total_time_ms,
        "sql_ms": sql_time_ms,
        "python_ms": python_time_ms,
        "query_count": query_count,
        "size_kb": content_size_kb,
        "duplicates": duplicates,
        "slowest_query": max([float(q.get("time", 0))*1000 for q in queries], default=0)
    }

benchmarks = [
    ("Dashboard Shell", "/dashboard/?section=home", HomePageView, {"section": "home"}, False),
    ("Dashboard Partial (HTMX)", "/dashboard/?section=home", HomePageView, {"section": "home"}, True),
    ("Accounts Shell", "/crm/accounts/accounts-view/", AccountView, {}, False),
    ("Accounts Table (HTMX)", "/crm/accounts/accounts-list-view/", AccountListView, {}, True),
    ("Accounts Search (HTMX)", "/crm/accounts/accounts-list-view/?search=corp", AccountListView, {"search": "corp"}, True),
    ("Leads Shell", "/crm/leads/leads-view/", LeadView, {}, False),
    ("Leads Table (HTMX)", "/crm/leads/leads-list/", LeadListView, {}, True),
    ("Leads Search (HTMX)", "/crm/leads/leads-list/?search=corp", LeadListView, {"search": "corp"}, True),
    ("Contacts Shell", "/crm/contacts/contacts-view/", ContactView, {}, False),
    ("Contacts Table (HTMX)", "/crm/contacts/contact-list-view/", ContactListView, {}, True),
    ("Opportunities Shell", "/crm/opportunities/opportunities-view/", opp_views.OpportunityView, {}, False),
    ("Opportunities Table (HTMX)", "/crm/opportunities/opportunities-list/", opp_views.OpportunityListView, {}, True),
    ("Opportunities Chart (HTMX)", "/crm/opportunities/opportunities-chart/", opp_views.OpportunityChartView, {}, True),
    ("Global Tasks (HTMX)", "/activity/global-task-list/", GlobalTaskListView, {}, True),
]

results = []
print(f"\n{'Endpoint Name':<30} | {'Status':<6} | {'Total ms':<9} | {'SQL ms':<8} | {'Py ms':<8} | {'Queries':<7} | {'Size KB':<9} | {'Slow Q ms':<9}")
print("-" * 110)

for name, path, v_class, params, is_htmx in benchmarks:
    try:
        res = profile_view(name, path, v_class, params, is_htmx)
        results.append(res)
        print(f"{res['name']:<30} | {res['status_code']:<6} | {res['total_ms']:<9.1f} | {res['sql_ms']:<8.1f} | {res['python_ms']:<8.1f} | {res['query_count']:<7} | {res['size_kb']:<9.1f} | {res['slowest_query']:<9.1f}")
    except Exception as e:
        print(f"{name:<30} | ERROR  | {str(e)[:50]}")

print("\n--- N+1 / Duplicate Query Detection ---")
for res in results:
    if res["duplicates"]:
        print(f"\n[{res['name']}] (Total queries: {res['query_count']}):")
        for prefix, count in res["duplicates"]:
            if count >= 3:
                print(f"  - Repeated {count}x: {prefix}...")
