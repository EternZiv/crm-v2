import os, sys, re, django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings')
django.setup()
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from finlo_crm.leads.views import LeadListView

user = get_user_model().objects.filter(is_active=True).first()
rf = RequestFactory()
req = rf.get('/crm/leads/leads-list/', HTTP_HX_REQUEST='true')
req.user = user
req.session = {'active_company': user.company.pk} if getattr(user, 'company', None) else {}
resp = LeadListView.as_view()(req)
raw_html = resp.content.decode('utf-8', errors='ignore')
collapsed = re.sub(r'>\s+<', '><', raw_html)
collapsed = re.sub(r'\s{2,}', ' ', collapsed)
print('Original size:', len(raw_html), f'({len(raw_html)/1024:.1f} KB)')
print('Whitespace-collapsed size:', len(collapsed), f'({len(collapsed)/1024:.1f} KB)')

