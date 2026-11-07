import os, sys, django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings')
django.setup()
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.db import connection, reset_queries
from scratch.test_optimized_tasks import OptimizedGlobalTaskListView

User = get_user_model()
user = User.objects.filter(username='test_bdo').first() or User.objects.filter(is_active=True).first()
rf = RequestFactory()
req = rf.get('/activity/global-task-list/', HTTP_HX_REQUEST='true')
req.user = user
req.session = {'active_company': user.company.pk} if getattr(user, 'company', None) else {}

reset_queries()
resp = OptimizedGlobalTaskListView.as_view()(req)
if hasattr(resp, 'render'):
    resp.render()

for i, q in enumerate(connection.queries):
    t_ms = float(q.get("time", 0)) * 1000
    sql = q.get("sql", "").strip()[:140].replace("\n", " ")
    print(f"{i+1}. [{t_ms:.1f}ms] {sql}...")

