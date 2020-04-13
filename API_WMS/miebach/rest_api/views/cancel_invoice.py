from django.views.decorators.csrf import csrf_exempt
from miebach_admin.models import *
from utils import *
from common import *
from outbound import *

log = init_logger('logs/cancel_invoice.log')


@csrf_exempt
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def cancel_invoice(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("cancel_invoice")
    user_profile = UserProfile.objects.get(user_id=user.id)
    log.info('Canceling  Invoice: Request params for ' + user.username + ' are ' + str(request.GET.dict()))
    market_place = False
    if user_profile.user_type == 'marketplace_user':
        market_place = True
    try:
        inc_obj = IncrementalTable.objects.filter(user=user.id, type_name='cancel_invoice')
        if not inc_obj.exists():
            inc_obj = IncrementalTable.objects.create(user_id=user.id, type_name='cancel_invoice', value=1)
            cancel_invoice_serial = 1
        else:
            cancel_invoice_serial = IncrementalTable.objects.filter(user=user.id, type_name='cancel_invoice')[0].value
            inc_obj = inc_obj[0]
        sell_ids = construct_sell_ids(request, user, cancel_inv=True)
        if request.GET.get('delivery_challan', ''):
            if market_place:
                sell_ids['seller_order__order__order_id__in'] = sell_ids['invoice_number__in']
            else:
                sell_ids['order__order_id__in'] = sell_ids['invoice_number__in']
            del sell_ids['invoice_number__in']
        seller_orders_summaries = SellerOrderSummary.objects.filter(**sell_ids)
        for order in seller_orders_summaries:
            cancelled_quantity = order.quantity
            if market_place:
                order_detail = order.seller_order.order
            else:
                order_detail = order.order
            if order_detail.status == 3:
                order_detail.quantity = order_detail.quantity + cancelled_quantity
            else:
                order_detail.quantity = cancelled_quantity
                order_detail.status = 3
            order_detail.save()
            picklist = order.picklist
            picklist.cancelled_quantity = picklist.cancelled_quantity + cancelled_quantity
            picklist.save()
            if picklist.stock:
                cancel_params = {'picklist' : picklist, 'quantity': cancelled_quantity,
                                 'cancel_invoice_serial': cancel_invoice_serial,
                                 'status': 1, 'location': picklist.stock.location}
                if market_place:
                    if picklist.stock.sellerstock_set.filter():
                        cancel_params['seller_id'] = picklist.stock.sellerstock_set.filter()[0].seller.id
                CancelledLocation.objects.create(**cancel_params)
        seller_orders_summaries.update(order_status_flag='cancelled')
        inc_object = inc_obj
        inc_object.value = float(cancel_invoice_serial) + 1
        inc_object.save()

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Cancel Invoice failed for params for user %s for params %s and error statement is %s' % (
            str(user.username), str(request.GET.dict()), str(e)))
        return HttpResponse('Failed To Cancel the Invoice')

    return HttpResponse('Succuess Fully Cancelled the Invoice')
