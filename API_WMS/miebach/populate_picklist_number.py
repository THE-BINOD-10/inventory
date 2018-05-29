import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from django.db.models import Q
from miebach_admin.models import *
import datetime
from rest_api.views.utils import *
log = init_logger('logs/update_picklists.log')

def update_user_picklists():
    users = User.objects.exclude(userprofile__user_type='customer')
    for user in users:
        print user.id, user.username
        picklist_obj1 = list(Picklist.objects.filter(order__user=user.id).only('picklist_number').order_by('-picklist_number').values_list('picklist_number', flat=True)[:1])
        picklist_obj2 = list(Picklist.objects.filter(stock__sku__user=user.id).only('picklist_number').order_by('-picklist_number').values_list('picklist_number', flat=True)[:1])
        picklist_obj = picklist_obj1 + picklist_obj2
        if picklist_obj:
            max_pick = max(picklist_obj)
            inc_check = IncrementalTable.objects.filter(user=user.id, type_name='picklist')
            if not inc_check:
                IncrementalTable.objects.create(user_id=user.id, type_name='picklist', value=max_pick, creation_date=datetime.datetime.now())
                log.info("User %s and picklist id is %s" % (user.username, str(max_pick)))
update_user_picklists()
