activate_this = 'setup/MIEBACH/bin/activate_this.py'
execfile(activate_this, dict(__file__ = activate_this))
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()

from miebach_admin.models import *
from rest_api.views.common import *
from rest_api.views.utils import *
log = init_logger('logs/integrations.log')


def update_order_status(company_name):
    integration_users = Integrations.objects.filter(name = company_name).values_list('user', flat=True)
    for user_id in integration_users:
        user = User.objects.get(id = user_id)
        open_orders = OrderDetail.objects.filter(user = user_id, status = 1).values_list('original_order_id', flat=True).distinct()
        resp = order_status_update(open_orders, user)
        log.info(resp)
        if resp["Status"].lower() == "success":
            dispatched_orders = resp["Result"].get("Dispatched", [])
            picked_orders = resp["Result"].get("Picked", [])
            cancelled_orders = resp["Result"].get("Cancelled", [])
            order_update(dispatched_orders, '2')
            order_update(cancelled_orders, '3')
    return "Success"

def order_update(orders, status):
    for order in orders:
        order_detail = OrderDetail.objects.filter(original_order_id = order["OrderId"])
        for item in order_detail:
            item.status = status
            #picklist confirmation
            if status == '2':
                picklist_obj = Picklist.objects.filter(order_id = item.id)
                if picklist_obj:
                    picklist_obj = picklist_obj[0]
                    stock_id = picklist_obj.stock_id
                    picklist_location = PicklistLocation.objects.filter(picklist_id=picklist_obj.id)
                    if picklist_location:
                        picklist_location = picklist_location[0]
                        picklist_location.quantity -= picklist_location.reserved
                        picklist_location.reserved = 0
                        picklist_location.status = '0'
                        picklist_location.save()
                        stock_id = picklist_location.stock_id
                    stock_obj = StockDetail.objects.filter(id=stock_id)
                    if stock_obj:
                        stock_obj = stock_obj[0]
                        stock_obj.quantity -= picklist_obj.reserved_quantity
                        picklist_obj.picked_quantity = picklist_obj.reserved_quantity
                        picklist_obj.reserved_quantity = 0
                        picklist_obj.status = "picked"
                        picklist_obj.save()
                        stock_obj.save()
                    seller_order_summary = SellerOrderSummary.objects.create(pick_number = 1,\
                                                seller_order = None,\
                                                order = item,\
                                                picklist = picklist_obj,\
                                                quantity = item.quantity)
            item.save()
    return "Status Updated"

if __name__ == '__main__':
    company_name = sys.argv[1]
    update_order_status(company_name)
