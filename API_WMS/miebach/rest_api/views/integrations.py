from miebach_admin.models import *
from common import *
from dateutil import parser
import traceback
import ConfigParser
import datetime

LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read('rest_api/views/configuration.cfg')

def update_orders(orders, user='', company_name=''):
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'order_mapping_dict', ''))
    NOW = datetime.datetime.now()
    try:
        if not orders:
            orders = {}
        orders = orders.get(order_mapping['items'], [])
        order_details = {}
        for ind, orders in enumerate(orders):

            can_fulfill = orders.get('can_fulfill', '1')
            channel_name = eval(order_mapping['channel'])
            if can_fulfill == '0':
                continue

            order_details = copy.deepcopy(ORDER_DATA)
            data = orders
            original_order_id = data[order_mapping['order_id']]
            order_code = ''.join(re.findall('\D+', original_order_id))
            order_id = ''.join(re.findall('\d+', original_order_id))
            filter_params = {'user': user.id, 'order_id': order_id}
            filter_params1 = {'user': user.id, 'original_order_id': original_order_id}
            if order_code:
                filter_params['order_code'] = order_code
            order_items = [orders]
            if order_mapping.get('order_items', ''):
                order_items = eval(order_mapping['order_items'])

            if not order_items:
                print "order_items doesn't exists" + original_order_id
            for order in order_items:
                sku_code = eval(order_mapping['sku'])
                sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                if sku_master:
                    filter_params['sku_id'] = sku_master[0].id
                    filter_params1['sku_id'] = sku_master[0].id
                else:
                    #SKUMaster.objects.create(sku_code=sku_code, wms_code=sku_code,user=user.id, status=1, creation_date=NOW,
                    #                                      online_percentage=0)
                    #sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                    #filter_params['sku_id'] = sku_master[0].id
                    #filter_params1['sku_id'] = sku_master[0].id
                    reason = ''
                    channel_sku = eval(order_mapping['channel_sku'])
                    if sku_code:
                        reason = "SKU Mapping doesn't exists"
                        orders_track = OrdersTrack.objects.filter(order_id=original_order_id, sku_code=sku_code, user=user.id)
                    else:
                        reason = "SKU Code missing"
                        orders_track = OrdersTrack.objects.filter(order_id=original_order_id, channel_sku = channel_sku, user=user.id)
                    if not orders_track:
                        OrdersTrack.objects.create(order_id=original_order_id, sku_code=sku_code, status=1, user=user.id,
                                            marketplace = channel_name, title = eval(order_mapping['title']), company_name = company_name,
                                    channel_sku= channel_sku, shipment_date = eval(order_mapping['shipment_date']),
                                                quantity = eval(order_mapping['quantity']),
                                               reason = reason, creation_date = NOW)
                    continue

                order_det = OrderDetail.objects.filter(**filter_params)
                order_det1 = OrderDetail.objects.filter(**filter_params1)
                if not order_det:
                    order_det = order_det1

                if order_det and len(str(eval(order_mapping['id']))) < 10 and isinstance(eval(order_mapping['id']), int):
                    order_det = order_det[0]
                    swx_mapping = SWXMapping.objects.filter(local_id = order_det.id, swx_type='order', app_host=company_name)
                    if swx_mapping:
                        for mapping in swx_mapping:
                            mapping.swx_id = eval(order_mapping['id'])
                            mapping.updation_date = NOW
                            mapping.save()
                    else:
                        mapping = SWXMapping(local_id=order_det.id, swx_id=eval(order_mapping['id']), swx_type='order',
                                             creation_date=NOW,updation_date=NOW, app_host=company_name)
                        mapping.save()
                    continue

                if order_det:
                    continue

                order_details['original_order_id'] = original_order_id
                order_details['order_id'] = order_id
                order_details['order_code'] = order_code

                order_details['sku_id'] = sku_master[0].id
                order_details['title'] = eval(order_mapping['title'])
                order_details['user'] = user.id
                order_details['quantity'] = eval(order_mapping['quantity'])
                order_details['shipment_date'] = NOW
                if not order_details['shipment_date']:
                    order_details['shipment_date'] = eval(order_mapping['shipment_date'])
                order_details['marketplace'] = channel_name
                invoice_amount = data.get('total_price', 0)
                if 'unit_price' in order_mapping:
                    invoice_amount = eval(order_mapping['unit_price']) * order_details['quantity']
                order_details['invoice_amount'] = invoice_amount

                order_detail = OrderDetail(**order_details)
                order_detail.save()

                order_issue_objs = OrdersTrack.objects.filter(user = user.id, order_id = original_order_id, sku_code = sku_code).exclude(mapped_sku_code = "", channel_sku = "")

                if not order_issue_objs:
                    order_issue_objs = OrdersTrack.objects.filter(user = user.id, order_id = original_order_id, channel_sku= eval(order_mapping['channel_sku'])).exclude(mapped_sku_code = "", sku_code = "")

                if order_issue_objs:
                    order_issue_objs = order_issue_objs[0]
                    order_issue_objs.mapped_sku_code = sku_code
                    order_issue_objs.status = 0
                    order_issue_objs.save()

                swx_mapping = SWXMapping.objects.filter(local_id = order_detail.id, swx_type='order', app_host=company_name)
                if not swx_mapping and len(str(eval(order_mapping['id']))) < 10 and isinstance(eval(order_mapping['id']), int):
                    mapping = SWXMapping(local_id=order_detail.id, swx_id=eval(order_mapping['id']), swx_type='order', creation_date=NOW,
                                         updation_date=NOW, app_host=company_name)
                    mapping.save()
    except:
        traceback.print_exc()

def update_shipped(orders, user='', company_name=''):
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'shipped_mapping_dict', ''))
    NOW = datetime.datetime.now()
    try:
        orders = orders.get(order_mapping['items'], [])
        order_details = {}
        for ind, orders in enumerate(orders):
            original_order_id = orders[order_mapping['order_id']]
            filter_params = {'order__user': user.id, 'order__original_order_id': original_order_id}
            order_items = [orders]
            if order_mapping.get('order_items', ''):
                order_items = eval(order_mapping['order_items'])

            for order in order_items:
                sku_code = eval(order_mapping['sku'])
                sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                if sku_master:
                    filter_params['order__sku_id'] = sku_master[0].id

                picklists = Picklist.objects.filter(**filter_params).exclude(status='dispatched')
                for picklist in picklists:
                    picklist.status = 'dispatched'
                    picklist.save()
                    picklist.order.status = 2
                    picklist.order.save()
    except:
        traceback.print_exc()

def update_returns(orders, user='', company_name=''):
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'returned_mapping_dict', ''))
    NOW = datetime.datetime.now()
    try:
        orders = orders.get(order_mapping['items'], [])
        order_details = {}
        for ind, orders in enumerate(orders):
            return_date = orders[order_mapping['return_date']]
            return_date = parser.parse(return_date)
            return_id = orders[order_mapping['return_id']]
            original_order_id = orders[order_mapping['order_id']]
            filter_params = {'user': user.id, 'original_order_id': original_order_id}
            order_items = [orders]
            if order_mapping.get('order_items', ''):
                order_items = eval(order_mapping['order_items'])

            for order in order_items:
                sku_code = eval(order_mapping['sku'])
                if not sku_code or not original_order_id:
                    continue
                filter_params['sku__sku_code'] = sku_code
                order_data = OrderDetail.objects.filter(**filter_params)
                if not order_data:
                    _order_id = re.findall("\d+", original_order_id)
                    if _order_id:
                        _order_id = "".join(_order_id)
                    else:
                        _order_id = ""
                    _order_code = re.findall("\D+", original_order_id)

                    if _order_code:
                        _order_code = "".join(_order_code)
                    else:
                        _order_code = ""

                    sku_obj = SKUMaster.objects.filter(user = user.id, sku_code = sku_code)

                    if not sku_obj:
                        continue
                    qty = eval(order_mapping['return_quantity']) + eval(order_mapping['damaged_quantity'])
                    order_data = OrderDetail.objects.create(user = user.id, order_id = _order_id, order_code = _order_code, status = 4, original_order_id = original_order_id, marketplace = eval(order_mapping['marketplace']), quantity = qty, sku = sku_obj[0], shipment_date = NOW.date())

                else:
                    order_data = order_data[0]
                return_instance = OrderReturns.objects.filter(return_id=return_id, order_id=order_data.id, order__user=user.id)
                if return_instance:
                    continue
                return_data = copy.deepcopy(RETURN_DATA)
                return_data['return_id'] = return_id
                return_data['damaged_quantity'] = eval(order_mapping['damaged_quantity'])
                return_data['quantity'] = eval(order_mapping['return_quantity'])
                return_data['return_type'] = eval(order_mapping['return_type'])
                return_data['return_date'] = return_date
                return_data['order_id'] = order_data.id
                return_data['reason'] = eval(order_mapping['reason'])
                return_data['sku_id'] = order_data.sku_id
                return_data['marketplace'] = eval(order_mapping['marketplace'])
                order_returns = OrderReturns(**return_data)
                order_returns.save()
    except:
        traceback.print_exc()

def update_cancelled(orders, user='', company_name=''):
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'cancelled_mapping_dict', ''))
    NOW = datetime.datetime.now()
    try:
        orders = orders.get(order_mapping['items'], [])
        order_details = {}
        for ind, orders in enumerate(orders):
            original_order_id = orders[order_mapping['order_id']]
            filter_params = {'user': user.id, 'original_order_id': original_order_id}
            order_items = [orders]
            if order_mapping.get('order_items', ''):
                order_items = eval(order_mapping['order_items'])

            for order in order_items:
                sku_code = eval(order_mapping['sku'])
                sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                if sku_master:
                    filter_params['sku_id'] = sku_master[0].id

                order_det = OrderDetail.objects.exclude(status=3).filter(**filter_params)
                if order_det:
                    order_det = order_det[0]
                    if order_det.status == 1:
                        order_det.status = 3
                        order_det.save()
                    else:
                        picklists = Picklist.objects.filter(order_id=order_det.id, order__user=user.id)
                        for picklist in picklists:
                            if picklist.picked_quantity <= 0:
                                picklist.delete()
                            elif picklist.stock:
                                cancel_location = CancelledLocation.objects.filter(picklist_id=picklist.id, picklist__order__user=user.id)
                                if not cancel_location:
                                    CancelledLocation.objects.create(picklist_id=picklist.id, quantity=picklist.picked_quantity,
                                                 location_id=picklist.stock.location_id, creation_date=datetime.datetime.now(), status=1)
                                    picklist.status = 'cancelled'
                                    picklist.save()
                            else:
                                picklist.status = 'cancelled'
                                picklist.save()
                        order_det.status = 3
                        order_det.save()
    except:
        traceback.print_exc()
