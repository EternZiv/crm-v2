import os, sys
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings.base')
import django
django.setup()

from finlo.contrib.core.models import FinloAttachment, FinloContentType
from finlo_crm.leads.models import Lead
from finlo.contrib.generics.views.attachments import AttachmentListView
from django.test import RequestFactory
from django.contrib.auth import get_user_model

u = get_user_model().objects.filter(username='test_superadmin').first()
lead = Lead.objects.get(pk=102)
ct = FinloContentType.objects.get_for_model(Lead)

qs = FinloAttachment.objects.filter(content_type=ct, object_id=102)
print("Direct filter count:", qs.count())
print("Direct filter items:", list(qs))

rf = RequestFactory()
req = rf.get('/crm/leads/102/notes-attachments/')
req.user = u
req.session = {}

lv = AttachmentListView()
lv.request = req
lv.queryset = qs

# Step by step execution of FinloListView.get_queryset()
from django.views.generic.list import MultipleObjectMixin
base_qs = MultipleObjectMixin.get_queryset(lv)
print("Step 1 (MultipleObjectMixin.get_queryset):", list(base_qs))

import finlo.contrib.generics.views.helpers.quick_filter as qf
qf_qs = qf.apply_quick_filters(base_qs, lv)
print("Step 2 (after apply_quick_filters):", list(qf_qs))

view_type = lv.request.GET.get("view_type") or lv.get_default_view_type()
print("view_type is:", view_type)

# Let's inspect get_queryset line by line
import inspect
lines, start = inspect.getsourcelines(lv.get_queryset)
print("Source lines of lv.get_queryset:")
print("".join(lines[:40]))

