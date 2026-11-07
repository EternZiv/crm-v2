import os, sys, re, django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from finlo_crm.leads.views import LeadListView

User = get_user_model()
user = User.objects.filter(username="test_bdo").first() or User.objects.filter(is_active=True).first()

rf = RequestFactory()
req = rf.get("/crm/leads/leads-list/", HTTP_HX_REQUEST="true")
req.user = user
req.session = {'active_company': user.company.pk} if getattr(user, 'company', None) else {}
resp = LeadListView.as_view()(req)
if hasattr(resp, 'render'):
    resp.render()
html = resp.content.decode('utf-8', errors='ignore')

rows = re.findall(r'<tr.*?>.*?</tr>', html, re.DOTALL)
if len(rows) > 1:
    sample_row = rows[1] # row 1 is data row
    print(f"Sample row length: {len(sample_row)} bytes")
    # Print tags breakdown
    cells = re.findall(r'<td.*?>.*?</td>', sample_row, re.DOTALL)
    print(f"Number of <td> cells: {len(cells)}")
    for i, c in enumerate(cells):
        print(f"Cell {i+1} size: {len(c)} bytes. Preview: {c[:120].strip()}...")
        if len(c) > 1000:
            print(f"   Cell {i+1} detailed content preview: {c[:500]}...")

