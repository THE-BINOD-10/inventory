from miebach_admin.models import *
from common import *
import traceback
import ConfigParser

LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read('rest_api/views/configuration.cfg')

def update_orders(orders, user='', company_name=''):
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'order_mapping_dict', ''))
    NOW = datetime.datetime.now()
    try:
        orders = orders.get(order_mapping['items'], [])
        order_details = {}
        for ind, orders in enumerate(orders):

            can_fulfill = orders.get('can_fulfill', '1')
            channel_name = orders.get(order_mapping['channel'], '')
            if can_fulfill == '0':
                continue

            order_details = copy.deepcopy(ORDER_DATA)
            data = orders
            order_id = ''.join(re.findall('\d+', data[order_mapping['order_id']]))
            order_code = ''.join(re.findall('\D+', data[order_mapping['order_id']]))
            filter_params = {'user': user.id, 'order_id': order_id}
            if order_code:
                filter_params['order_code'] = order_code
            order_items = [orders]
            if order_mapping.get('order_items', ''):
                order_items = eval(order_mapping['order_items'])

            for order in order_items:
                sku_code = eval(order_mapping['sku'])
                sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                if sku_master:
                    filter_params['sku_id'] = sku_master[0].id

                order_det = OrderDetail.objects.filter(**filter_params)

                if order_det:
                    order_det = order_det[0]
                    swx_mapping = SWXMapping.objects.filter(local_id = order_det.id, swx_type='order', app_host=company_name)
                    if swx_mapping:
                        for mapping in swx_mapping:
                            mapping.swx_id = data[order_mapping['id']]
                            mapping.updation_date = NOW
                            mapping.save()
                    else:
                        mapping = SWXMapping(local_id=order_det.id, swx_id=data[order_mapping['id']], swx_type='order',
                                             creation_date=NOW,updation_date=NOW, app_host=company_name)
                        mapping.save()
                    continue

                if order_det:
                    continue

                order_details['original_order_id'] = data[order_mapping['order_id']]
                order_details['order_id'] = order_id
                order_details['order_code'] = order_code
                if not order_code:
                    order_details['order_code'] = 'OD'
                if not sku_master:
                    orders_track = OrdersTrack.objects.filter(order_id=order_details['order_id'], sku_code=sku_code, user=user.id)
                    if not orders_track:
                        OrdersTrack.objects.create(order_id=order_details['order_id'], sku_code=sku_code, status=1, user=user.id,
                                                   reason = "SKU Mapping doesn't exists", creation_date=NOW)
                    continue

                order_details['sku_id'] = sku_master[0].id
                order_details['title'] = eval(order_mapping['title'])
                order_details['user'] = user.id
                order_details['quantity'] = eval(order_mapping['quantity'])
                order_details['shipment_date'] = data.get('ship_by', '')
                if not order_details['shipment_date']:
                    order_details['shipment_date'] = eval(order_mapping['shipment_date'])
                order_details['marketplace'] = channel_name
                invoice_amount = data.get('total_price', 0)
                if 'unit_price' in order_mapping:
                    invoice_amount = eval(order_mapping['unit_price']) * order_details['quantity']
                order_details['invoice_amount'] = invoice_amount

                order_detail = OrderDetail(**order_details)
                order_detail.save()

                swx_mapping = SWXMapping.objects.filter(local_id = order_detail.id, swx_type='order', app_host=company_name)
                if not swx_mapping:
                    mapping = SWXMapping(local_id=order_detail.id, swx_id=data[order_mapping['id']], swx_type='order', creation_date=NOW,
                                         updation_date=NOW, app_host=company_name)
                    mapping.save()
    except:
        traceback.print_exc()

