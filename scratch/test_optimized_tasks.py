import os, sys, time, django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.db import connection, reset_queries
from finlo.contrib.activity.views.list_view.global_views import GlobalTaskListView

User = get_user_model()
user = User.objects.filter(username="test_bdo").first() or User.objects.filter(is_active=True).first()

# Subclass to simulate the proposed targeted optimization
class OptimizedGlobalTaskListView(GlobalTaskListView):
    paginate_by = 25

    def get_queryset(self):
        return super().get_queryset().prefetch_related('related_object')

rf = RequestFactory()
req = rf.get("/activity/global-task-list/", HTTP_HX_REQUEST="true")
req.user = user
req.session = {'active_company': user.company.pk} if getattr(user, 'company', None) else {}

reset_queries()
t0 = time.perf_counter()

resp = OptimizedGlobalTaskListView.as_view()(req)
if hasattr(resp, 'render'):
    resp.render()

t1 = time.perf_counter()
total_time = (t1 - t0) * 1000

queries = connection.queries
sql_time = sum(float(q.get("time", 0)) for q in queries) * 1000
query_count = len(queries)
content_size = len(resp.content) if hasattr(resp, 'content') else 0

print(f"\n--- OPTIMIZED PROFILING RESULTS ---")
print(f"Total View Execution Time: {total_time:.2f} ms (Original was 7,172 ms)")
print(f"SQL Query Count:          {query_count} (Original was 104)")
print(f"Total SQL Time (reported): {sql_time:.2f} ms (Original was 5,668 ms)")
print(f"Serialized Response Size: {content_size} bytes ({content_size / 1024:.2f} KB) (Original was 788 KB)")
print(f"HTTP Status:              {resp.status_code}")

