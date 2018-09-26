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
    po_imeis = POIMEIMapping.objects.filter(Q(sku__isnull=True) | Q(seller__isnull=True))
    users_updated = []
    for po in po_imeis:
        if po.purchase_order and po.purchase_order.open_po:
            open_po = po.purchase_order.open_po
            po.sku_id = open_po.sku_id
            if open_po.sellerpo_set.filter():
                po.seller_id = open_po.sellerpo_set.filter()[0].seller_id
            po.save()
            users_updated.append(po.purchase_order.open_po.sku.user)
    order_imeis = OrderIMEIMapping.objects.filter()
    for order_imei in order_imeis:
        order_imei.sku_id = order_imei.order.sku_id
        if order_imei.po_imei and order_imei.po_imei.purchase_order.open_po and order_imei.po_imei.purchase_order.open_po.sellerpo_set.filter():
            order_imei.seller_id = order_imei.po_imei.purchase_order.open_po.sellerpo_set.filter()[0].id
        order_imei.save()
    log.info("Updating Users List %s" % (str(list(set(users_updated)))))
update_user_imeis()
