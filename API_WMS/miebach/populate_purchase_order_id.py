import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from django.db.models import Q
from itertools import chain
from miebach_admin.models import *
import datetime
from rest_api.views.utils import *
log = init_logger('logs/update_po_ids.log')

def update_user_purchase_orders():
    users = User.objects.exclude(userprofile__user_type='customer')
    for user in users:
        print user.id, user.username
        po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).values_list('order_id', flat=True).order_by(
            "-order_id")
        st_order = STPurchaseOrder.objects.filter(open_st__sku__user=user.id).values_list('po__order_id',
                                                                                          flat=True).order_by(
            "-po__order_id")
        order_ids = list(chain(po_data, st_order))
        order_ids = sorted(order_ids, reverse=True)
        if not order_ids:
            po_id = 0
        else:
            po_id = int(order_ids[0])
        if po_id:
            inc_check = IncrementalTable.objects.filter(user=user.id, type_name='po')
            if not inc_check:
                IncrementalTable.objects.create(user_id=user.id, type_name='po', value=po_id,
                                                creation_date=datetime.datetime.now())
            else:
                inc_check = inc_check[0]
                inc_check.value = po_id
                inc_check.save()
                log.info("User %s and Purchase Order id is %s" % (user.username, str(po_id)))
update_user_purchase_orders()
