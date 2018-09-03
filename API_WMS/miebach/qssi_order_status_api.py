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
log = init_logger('logs/qssi_order_status_update.log')


def update_order_status(company_name):
    integration_users = Integrations.objects.filter(name = company_name).values_list('user', flat=True)
    for user_id in integration_users:
        user = User.objects.get(id = user_id)
        open_orders = OrderDetail.objects.filter(user = user_id, status = 0,\
                      picklist__status__icontains = 'open').values_list('original_order_id', flat=True).distinct()
        log.info(str(open_orders.count()))
        log.info(str(list(open_orders)))
        resp = order_status_update(open_orders, user)
        log.info(resp)
        if resp["Status"].lower() in ["success", "partial"]:
            dispatched_orders = resp["Result"].get("Dispatched", [])
            picked_orders = resp["Result"].get("Picked", [])
            cancelled_orders = resp["Result"].get("Cancelled", [])
            order_update(dispatched_orders, user, '2')
            order_update(cancelled_orders, user, '3')
    return "Success"

def order_update(orders, user, status):
    for order in orders:
        # WarehouseId = ''.join(filter(str.isdigit, str(user.username)))
        WarehouseId = str(user.userprofile.order_prefix)
        temp_order_id = str(order["OrderId"]).replace(WarehouseId, '', 1)
        order_detail = OrderDetail.objects.filter(original_order_id = temp_order_id, user=user.id)
        for item in order_detail:
            item.status = status
            log.info("Status changed to %s for order %s, user %s" % (str(status), str(item.id), str(user.username)))
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
                        log.info("Updated stock in Picklist location obj %s : quantity=%s" %
                                 (str(picklist_location.id), str(picklist_location.quantity)))
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
                        log.info("Picklist id %s confirmed and Stock id %s quantity \
                                  reduced to %s; user : %s" %
                                  (str(picklist_obj.id), str(stock_obj.id), str(stock_obj.quantity),\
                                   str(user.username)))
                    seller_order_summary = SellerOrderSummary.objects.create(pick_number = 1,\
                                                seller_order = None,\
                                                order = item,\
                                                picklist = picklist_obj,\
                                                quantity = item.quantity)
                    log.info("Seller Order Summary created: id = %s, order_id = %s, picklist_id = %s,\
                             quantity = %s" % (str(seller_order_summary.id), str(item.id),\
                             str(picklist_obj.id), str(item.quantity)))
            elif status == '3':
                picklists = Picklist.objects.filter(order_id=item.id)
                for picklist in picklists:
                    if picklist.picked_quantity <= 0:
                        picklist.delete()
                    elif picklist.stock:
                        cancel_location = CancelledLocation.objects.filter(picklist_id=picklist.id)
                        if not cancel_location:
                            CancelledLocation.objects.create(picklist_id=picklist.id,
                                                             quantity=picklist.picked_quantity,
                                                             location_id=picklist.stock.location_id,
                                                             creation_date=datetime.datetime.now(), status=1)
                            picklist.status = 'cancelled'
                            picklist.save()
                    else:
                        picklist.status = 'cancelled'
                        picklist.save()
            item.save()
    return "Status Updated"

if __name__ == '__main__':
    company_name = sys.argv[1]
    update_order_status(company_name)
