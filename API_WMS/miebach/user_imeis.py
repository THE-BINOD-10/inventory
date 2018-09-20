import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from django.db.models import Q
from miebach_admin.models import *
import datetime
from rest_api.views.utils import *
log = init_logger('logs/update_user_imeis.log')

def update_user_imeis():
    po_imeis = POIMEIMapping.objects.filter()
    users_updated = []
    for po in po_imeis:
        po.sku_id = po.purchase_order.open_po.sku_id
        po.save()
        users_updated.append(po.purchase_order.open_po.sku.user)
    log.info("Updating Users List %s" % (str(list(set(users_updated)))))
update_user_imeis()
