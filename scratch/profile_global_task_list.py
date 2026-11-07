import os
import sys
import time

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finlo.settings")

import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.db import connection, reset_queries
from finlo.contrib.activity.views.list_view.global_views import GlobalTaskListView

User = get_user_model()
user = User.objects.filter(username="test_bdo").first()
if not user:
    user = User.objects.filter(is_active=True).first()

print(f"Profiling GlobalTaskListView with user: {user.username} (id={user.pk})")

rf = RequestFactory()
request = rf.get("/activity/global-task-list/", HTTP_HX_REQUEST="true")
request.user = user
request.session = {'active_company': user.company.pk} if getattr(user, 'company', None) else {}

reset_queries()
t0 = time.perf_counter()

view = GlobalTaskListView.as_view()
response = view(request)
if hasattr(response, 'render'):
    response.render()

t1 = time.perf_counter()
total_time = (t1 - t0) * 1000

queries = connection.queries
sql_time = sum(float(q.get("time", 0)) for q in queries) * 1000
query_count = len(queries)

content_size = len(response.content) if hasattr(response, 'content') else 0

print(f"\n--- PROFILING RESULTS ---")
print(f"Total View Execution Time: {total_time:.2f} ms")
print(f"SQL Query Count:          {query_count}")
print(f"Total SQL Time (reported): {sql_time:.2f} ms")
print(f"Serialized Response Size: {content_size} bytes ({content_size / 1024:.2f} KB)")
print(f"HTTP Status:              {response.status_code}")

print(f"\n--- ALL QUERIES EXECUTED ---")
for i, q in enumerate(queries):
    q_time = float(q.get("time", 0)) * 1000
    sql_str = q.get("sql", "").strip()[:180].replace("\n", " ")
    print(f"{i+1}. [{q_time:.1f}ms] {sql_str}...")
