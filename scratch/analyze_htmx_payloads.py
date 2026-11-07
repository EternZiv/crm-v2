import os, sys, django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from finlo_crm.leads.views import LeadListView
from finlo.contrib.activity.views.list_view.global_views import GlobalTaskListView

User = get_user_model()
user = User.objects.filter(username="test_bdo").first() or User.objects.filter(is_active=True).first()

rf = RequestFactory()

# 1. Leads
req_leads = rf.get("/crm/leads/leads-list/", HTTP_HX_REQUEST="true")
req_leads.user = user
req_leads.session = {'active_company': user.company.pk} if getattr(user, 'company', None) else {}
resp_leads = LeadListView.as_view()(req_leads)
if hasattr(resp_leads, 'render'):
    resp_leads.render()
html_leads = resp_leads.content.decode('utf-8', errors='ignore')

# 2. Tasks
req_tasks = rf.get("/activity/global-task-list/", HTTP_HX_REQUEST="true")
req_tasks.user = user
req_tasks.session = {'active_company': user.company.pk} if getattr(user, 'company', None) else {}
resp_tasks = GlobalTaskListView.as_view()(req_tasks)
if hasattr(resp_tasks, 'render'):
    resp_tasks.render()
html_tasks = resp_tasks.content.decode('utf-8', errors='ignore')

print(f"Leads HTML size: {len(html_leads)} bytes ({len(html_leads)/1024:.1f} KB)")
print(f"Tasks HTML size: {len(html_tasks)} bytes ({len(html_tasks)/1024:.1f} KB)")

# Analyze content of Leads HTML
import re
print("\n--- Leads HTML Breakdown ---")
svgs = re.findall(r'<svg.*?</svg>', html_leads, re.DOTALL)
print(f"SVG count: {len(svgs)}, Total SVG bytes: {sum(len(s) for s in svgs)} ({sum(len(s) for s in svgs)/1024:.1f} KB)")

modals = re.findall(r'<div[^>]*modal[^>]*>.*?</div>', html_leads, re.DOTALL | re.IGNORECASE)
print(f"Modal matches: {len(modals)}, bytes: {sum(len(m) for m in modals)} ({sum(len(m) for m in modals)/1024:.1f} KB)")

table_rows = re.findall(r'<tr.*?>.*?</tr>', html_leads, re.DOTALL)
print(f"Table rows count: {len(table_rows)}, avg bytes per row: {sum(len(r) for r in table_rows)/len(table_rows) if table_rows else 0:.1f} bytes")

tbody = re.findall(r'<tbody.*?>.*?</tbody>', html_leads, re.DOTALL)
if tbody:
    print(f"Tbody size: {len(tbody[0])} bytes ({len(tbody[0])/1024:.1f} KB)")

table_match = re.search(r'<table.*?>.*?</table>', html_leads, re.DOTALL)
if table_match:
    table_len = len(table_match.group(0))
    print(f"Table element size: {table_len} bytes ({table_len/1024:.1f} KB)")
    print(f"Outside table size: {len(html_leads) - table_len} bytes ({(len(html_leads) - table_len)/1024:.1f} KB)")

# What is outside table?
if table_match:
    outside = html_leads[:table_match.start()] + html_leads[table_match.end():]
    print(f"Outside table preview (first 500 chars):")
    print(outside[:500])
