from miebach_admin.models import *
from common import *
from masters import *
from uploads import *
from dateutil import parser
import traceback
import ConfigParser
import datetime

LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read('rest_api/views/configuration.cfg')

def check_and_add_dict(grouping_key, key_name, adding_dat, final_data_dict={}, is_list=False):
    final_data_dict.setdefault(grouping_key, {})
    final_data_dict[grouping_key].setdefault(key_name, {})
    if is_list:
        final_data_dict[grouping_key].setdefault(key_name, [])
        final_data_dict[grouping_key][key_name] = copy.deepcopy(list(chain(final_data_dict[grouping_key][key_name], adding_dat)))

    elif grouping_key in final_data_dict.keys() and final_data_dict[grouping_key][key_name].has_key('quantity'):
        final_data_dict[grouping_key][key_name]['quantity'] = final_data_dict[grouping_key][key_name]['quantity'] +\
                                                                  adding_dat.get('quantity', 0)
    elif grouping_key in final_data_dict.keys() and final_data_dict[grouping_key][key_name].has_key('invoice_amount'):
        final_data_dict[grouping_key][key_name]['quantity'] = final_data_dict[grouping_key][key_name]['invoice_amount'] +\
                                                                  adding_dat.get('invoice_amount', 0)
    else:
        final_data_dict[grouping_key][key_name] = copy.deepcopy(adding_dat)

    return final_data_dict


def validate_orders(orders, user='', company_name='', is_cancelled=False):
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'order_mapping_dict', ''))
    NOW = datetime.datetime.now()

    #insert_status = {'Seller Master does not exists': [], 'SOR ID not found': [], 'Order Status not Matched': [],
    #                 'Order Exists already': [], 'Invalid SKU Codes': [], 'Invalid Delivery Rescheduled Order': []}
    insert_status = []

    final_data_dict = OrderedDict()
    try:
        seller_masters = SellerMaster.objects.filter(user=user.id)
        user_profile = UserProfile.objects.get(user_id=user.id)
        seller_master_dict = {}
        sku_ids = []
        if not orders:
            orders = {}
        orders = eval(order_mapping['items'])
        if order_mapping.get('is_dict', False):
            orders = [orders]
        for ind, orders in enumerate(orders):

            can_fulfill = orders.get('can_fulfill', '1')
            channel_name = eval(order_mapping['channel'])
            if can_fulfill == '0':
                continue

            order_details = copy.deepcopy(ORDER_DATA)
            data = orders
            original_order_id = str(data[order_mapping['order_id']])
            order_code = ''.join(re.findall('\D+', original_order_id))
            order_id = ''.join(re.findall('\d+', original_order_id))
            filter_params = {'user': user.id, 'order_id': order_id}
            filter_params1 = {'user': user.id, 'original_order_id': original_order_id}
            if order_mapping.has_key('customer_id'):
                order_details['customer_id'] = eval(order_mapping['customer_id'])
                order_details['customer_name'] = eval(order_mapping['customer_name'])
                order_details['telephone'] = eval(order_mapping['telephone'])
                order_details['city'] = eval(order_mapping['city'])
                order_details['address'] = eval(order_mapping['address'])
            if order_code:
                filter_params['order_code'] = order_code
            order_items = [orders]
            if order_mapping.get('order_items', ''):
                order_items = eval(order_mapping['order_items'])

            if not order_items:
                print "order_items doesn't exists" + original_order_id

            for order in order_items:
                try:
                    shipment_date = eval(order_mapping['shipment_date'])
                    shipment_date = datetime.datetime.fromtimestamp(shipment_date)
                except:
                    shipment_date = NOW
                if not order_mapping.get('line_items'):
                    sku_items = [order]
                else:
                    sku_items = eval(order_mapping['line_items'])
                for sku_item in sku_items:
                    order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
                    seller_order_dict = copy.deepcopy(SELLER_ORDER_FIELDS)
                    sku_code = eval(order_mapping['sku'])

                    swx_mappings = []
                    seller_item_id = ''
                    seller_parent_id = ''
                    if order_mapping.has_key('seller_item_id'):
                        seller_item_id = eval(order_mapping['seller_item_id'])
                        swx_mappings.append({'app_host': 'shotang', 'swx_id': seller_item_id,
                                             'swx_type': 'seller_item_id'})
                    if order_mapping.has_key('seller_parent_item_id'):
                        seller_parent_id = eval(order_mapping['seller_parent_item_id'])
                        swx_mappings.append({'app_host': 'shotang', 'swx_id': seller_parent_id,
                                             'swx_type': 'seller_parent_item_id'})
                    seller_master = []
                    if order_mapping.get('seller_id', ''):
                        seller_id = eval(order_mapping['seller_id'])
                        seller_master = seller_masters.filter(seller_id=seller_id)
                        order_status = eval(order_mapping['order_status'])

                        if not seller_master:
                            insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': seller_item_id,
                                                  'error': 'Seller Master does not exists'})
                            continue
                        else:
                            seller_master_dict[seller_id] = seller_master[0].id
                    if not eval(order_mapping['sor_id']):
                        insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': seller_item_id,
                                              'error': 'SOR ID not found'})
                        continue

                    if order.has_key('currentStatus') and not order_status in ['PENDING', 'DELIVERY_RESCHEDULED']:
                        insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': seller_item_id,
                                              'error': 'Order Status not Matched'})
                        continue
                    seller_order = SellerOrder.objects.filter(Q(order__original_order_id=original_order_id)|Q(order__order_id=order_id,
                                                 order__order_code=order_code),sor_id=eval(order_mapping['sor_id']), seller__user=user.id)
                    if seller_order and not order_status == 'DELIVERY_RESCHEDULED':
                        if not is_cancelled:
                            insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': seller_item_id,
                                                  'error': 'Order Exists already'})
                            continue
                    sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                    if sku_master:
                        filter_params['sku_id'] = sku_master[0].id
                        filter_params1['sku_id'] = sku_master[0].id
                    else:
                        reason = ''
                        insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': seller_item_id,
                                              'error': 'Invalid SKU Codes'})
                        channel_sku = eval(order_mapping['channel_sku'])
                        if sku_code:
                            insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': seller_item_id,
                                                  'error': "SKU Mapping doesn't exists"})
                        else:
                            insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': seller_item_id,
                                                  'error': "SKU Code missing"})
                        continue

                    order_sor_id = ''
                    if order_mapping.get('sor_id', ''):
                        order_sor_id = eval(order_mapping['sor_id'])
                    grouping_key = str(original_order_id) + '<<>>' + str(sku_master[0].sku_code) + '<<>>' +str(order_sor_id)
                    final_data_dict = check_and_add_dict(grouping_key, 'swx_mappings', swx_mappings, final_data_dict=final_data_dict, is_list=True)
                    order_det = OrderDetail.objects.filter(**filter_params)
                    order_det1 = OrderDetail.objects.filter(**filter_params1)
                    invoice_amount = float(data.get('total_price', 0))

                    if 'unit_price' in order_mapping:
                        invoice_amount = float(eval(order_mapping['unit_price'])) * float(eval(order_mapping['quantity']))
                        order_details['unit_price'] = float(eval(order_mapping['unit_price']))
                    if order_mapping.has_key('cgst_tax'):
                        order_summary_dict['cgst_tax'] = eval(order_mapping['cgst_tax'])
                        order_summary_dict['sgst_tax'] = eval(order_mapping['sgst_tax'])
                        order_summary_dict['igst_tax'] = eval(order_mapping['igst_tax'])
                        order_summary_dict['inter_state'] = 0
                        if order_summary_dict['igst_tax']:
                            order_summary_dict['inter_state'] = 1
                        tot_invoice = (float(invoice_amount)/100) * (float(order_summary_dict['cgst_tax']) + float(order_summary_dict['sgst_tax'])\
                                                                      + float(order_summary_dict['igst_tax']))
                        invoice_amount += float(tot_invoice)

                    if not order_det:
                        order_det = order_det1

                    order_create = True
                    if (order_det and filter_params['sku_id'] in sku_ids) or (order_det and seller_id in seller_master_dict.keys())\
                        and not order_status == 'DELIVERY_RESCHEDULED':
                        order_det = order_det[0]
                        #order_det.quantity += float(eval(order_mapping['quantity']))
                        #order_det.invoice_amount += invoice_amount
                        #order_det.save()
                        #final_data_dict = check_and_add_dict(grouping_key, 'order_detail_obj', order_det, final_data_dict=final_data_dict)
                        if order_det and seller_id in seller_master_dict.keys():
                            order_create = False
                        elif is_cancelled:
                            final_data_dict = check_and_add_dict(grouping_key, 'order_details', order_details, final_data_dict=final_data_dict)
                        else:
                            insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': seller_item_id,
                                                  'error': 'Order Exists already'})
                            continue
                    elif order_det and order_status == 'DELIVERY_RESCHEDULED':
                        seller_order_ins = seller_order.filter(order_status='PROCESSED', order__sku_id=sku_master[0].id)
                        if not seller_order_ins or not (int(seller_order_ins[0].order.status) in [2, 4, 5]):
                            insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': seller_item_id,
                                                  'error': 'Invalid Delivery Rescheduled Order'})
                        continue
                    elif not order_det and order_status == 'DELIVERY_RESCHEDULED':
                        insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': seller_item_id,
                                              'error': 'Invalid Delivery Rescheduled Order'})
                        continue

                    if order_create or is_cancelled:
                        order_details['original_order_id'] = original_order_id
                        order_details['order_id'] = order_id
                        order_details['order_code'] = order_code

                        order_details['sku_id'] = sku_master[0].id
                        order_details['title'] = eval(order_mapping['title'])
                        order_details['user'] = user.id
                        order_details['quantity'] = eval(order_mapping['quantity'])
                        order_details['shipment_date'] = shipment_date
                        order_details['marketplace'] = channel_name
                        order_details['invoice_amount'] = float(invoice_amount)

                        final_data_dict = check_and_add_dict(grouping_key, 'order_details', order_details, final_data_dict=final_data_dict)

                        if order_mapping.has_key('cgst_tax'):
                            customerorder = CustomerOrderSummary(**order_summary_dict)
                            final_data_dict = check_and_add_dict(grouping_key, 'order_summary_dict', order_summary_dict,
                                                                 final_data_dict=final_data_dict)
                    else:
                        order_detail = order_det

                    if order_mapping.has_key('sor_id'):
                        seller_order_dict['seller_id'] = seller_master_dict[seller_id]
                        seller_order_dict['sor_id'] = eval(order_mapping['sor_id'])
                        seller_order_dict['order_status'] = eval(order_mapping['order_status'])
                        seller_order_dict['quantity'] = eval(order_mapping['quantity'])
                        final_data_dict = check_and_add_dict(grouping_key, 'seller_order_dict', seller_order_dict, final_data_dict=final_data_dict)

        return insert_status, final_data_dict

    except:
        traceback.print_exc()
        return insert_status, final_data_dict

def update_orders(orders, user='', company_name=''):
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'order_mapping_dict', ''))
    NOW = datetime.datetime.now()

    insert_status = {'Orders Inserted': 0, 'Seller Master does not exists': 0, 'SOR ID not found': 0, 'Order Status not Matched': 0,
                     'Order Exists already': 0, 'Invalid SKU Codes': 0, 'Invalid Delivery Rescheduled Order': 0}

    try:
        seller_masters = SellerMaster.objects.filter(user=user.id)
        user_profile = UserProfile.objects.get(user_id=user.id)
        seller_master_dict = {}
        sku_ids = []
        if not orders:
            orders = {}
        #orders = orders.get(order_mapping['items'], [])
        orders = eval(order_mapping['items'])
        if order_mapping.get('is_dict', False):
            orders = [orders]
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
            if order_mapping.has_key('customer_id'):
                order_details['customer_id'] = eval(order_mapping['customer_id'])
                order_details['customer_name'] = eval(order_mapping['customer_name'])
                order_details['telephone'] = eval(order_mapping['telephone'])
                order_details['city'] = eval(order_mapping['city'])
                order_details['address'] = eval(order_mapping['address'])
            if order_code:
                filter_params['order_code'] = order_code
            order_items = [orders]
            if order_mapping.get('order_items', ''):
                order_items = eval(order_mapping['order_items'])

            if not order_items:
                print "order_items doesn't exists" + original_order_id

            for order in order_items:
                if order_mapping.get('seller_id', ''):
                    seller_id = eval(order_mapping['seller_id'])
                    seller_master = seller_masters.filter(seller_id=seller_id)
                    order_status = eval(order_mapping['order_status'])
                    if not seller_master:
                        insert_status['Seller Master does not exists'] += 1
                        continue
                    if not eval(order_mapping['sor_id']):
                        insert_status['SOR ID not found'] += 1
                        continue

                    if order.has_key('currentStatus') and not order_status in ['PENDING', 'DELIVERY_RESCHEDULED']:
                        insert_status['Order Status not Matched'] += 1
                        continue

                    seller_master_dict[seller_id] = seller_master[0].id
                    seller_order = SellerOrder.objects.filter(Q(order__original_order_id=original_order_id)|Q(order__order_id=order_id,
                                                 order__order_code=order_code),sor_id=eval(order_mapping['sor_id']), seller__user=user.id)
                    if seller_order and not order_status == 'DELIVERY_RESCHEDULED':
                        insert_status['Order Exists already'] += 1
                        continue
                try:
                    shipment_date = eval(order_mapping['shipment_date'])
                    shipment_date = datetime.datetime.fromtimestamp(shipment_date)
                except:
                    shipment_date = NOW
                if not order_mapping.get('line_items'):
                    sku_items = [order]
                else:
                    sku_items = eval(order_mapping['line_items'])
                for sku_item in sku_items:
                    order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
                    seller_order_dict = copy.deepcopy(SELLER_ORDER_FIELDS)
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
                        insert_status['Invalid SKU Codes'] += 1
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
                                        channel_sku= channel_sku, shipment_date = shipment_date,
                                                    quantity = eval(order_mapping['quantity']),
                                                   reason = reason, creation_date = NOW)
                        continue

                    order_det = OrderDetail.objects.filter(**filter_params)
                    order_det1 = OrderDetail.objects.filter(**filter_params1)
                    invoice_amount = float(data.get('total_price', 0))

                    if 'unit_price' in order_mapping:
                        invoice_amount = float(eval(order_mapping['unit_price'])) * float(eval(order_mapping['quantity']))
                        order_details['unit_price'] = float(eval(order_mapping['unit_price']))
                    if order_mapping.has_key('cgst_tax'):
                        order_summary_dict['cgst_tax'] = eval(order_mapping['cgst_tax'])
                        order_summary_dict['sgst_tax'] = eval(order_mapping['sgst_tax'])
                        order_summary_dict['igst_tax'] = eval(order_mapping['igst_tax'])
                        order_summary_dict['inter_state'] = 0
                        if order_summary_dict['igst_tax']:
                            order_summary_dict['inter_state'] = 1
                        tot_invoice = (float(invoice_amount)/100) * (float(order_summary_dict['cgst_tax']) + float(order_summary_dict['sgst_tax'])\
                                                                      + float(order_summary_dict['igst_tax']))
                        invoice_amount += float(tot_invoice)

                    if not order_det:
                        order_det = order_det1

                    order_create = True
                    if (order_det and filter_params['sku_id'] in sku_ids) or (order_det and seller_id in seller_master_dict.keys())\
                        and not order_status == 'DELIVERY_RESCHEDULED':
                        order_det = order_det[0]
                        order_det.quantity += float(eval(order_mapping['quantity']))
                        order_det.invoice_amount += invoice_amount

                        #order_det.save()
                        if order_det and seller_id in seller_master_dict.keys():
                            order_create = False
                        else:
                            insert_status['Order Exists already'] += 1
                            continue
                    elif order_det and order_status == 'DELIVERY_RESCHEDULED':
                        seller_order_ins = seller_order.filter(order_status='PROCESSED', order__sku_id=sku_master[0].id)
                        if not seller_order_ins or not (int(seller_order_ins[0].order.status) in [2, 4, 5]):
                            insert_status['Invalid Delivery Rescheduled Order'] += 1
                        elif int(seller_order_ins[0].order.status) in [2, 4, 5]:
                            order_obj = seller_order_ins[0].order
                            order_obj.status = 1
                            seller_order_dict['sor_id'] = eval(order_mapping['sor_id'])
                            seller_order_dict['order_status'] = eval(order_mapping['order_status'])
                            update_seller_order(seller_order_dict, order_obj, user)
                            order_obj.save()
                            insert_status['Orders Inserted'] += 1
                        continue
                    elif not order_det and order_status == 'DELIVERY_RESCHEDULED':
                        insert_status['Invalid Delivery Rescheduled Order'] += 1
                        continue

                    if order_create:
                        order_details['original_order_id'] = original_order_id
                        order_details['order_id'] = order_id
                        order_details['order_code'] = order_code

                        order_details['sku_id'] = sku_master[0].id
                        order_details['title'] = eval(order_mapping['title'])
                        order_details['user'] = user.id
                        order_details['quantity'] = eval(order_mapping['quantity'])
                        order_details['shipment_date'] = shipment_date
                        order_details['marketplace'] = channel_name
                        order_details['invoice_amount'] = float(invoice_amount)

                        order_detail = OrderDetail(**order_details)
                        order_detail.save()

                        if order_mapping.has_key('cgst_tax'):
                            order_summary_dict['order_id'] = order_detail.id
                            customerorder = CustomerOrderSummary(**order_summary_dict)
                            customerorder.save()
                    else:
                        order_detail = order_det

                    swx_mappings = []
                    if order_mapping.has_key('seller_item_id'):
                        swx_mappings.append({'app_host': 'shotang', 'swx_id': eval(order_mapping['seller_item_id']),
                                             'swx_type': 'seller_item_id'})
                    if order_mapping.has_key('seller_parent_item_id'):
                        swx_mappings.append({'app_host': 'shotang', 'swx_id': eval(order_mapping['seller_parent_item_id']),
                                             'swx_type': 'seller_parent_item_id'})
                    if order_mapping.has_key('sor_id'):
                        seller_order_dict['seller_id'] = seller_master_dict[seller_id]
                        seller_order_dict['sor_id'] = eval(order_mapping['sor_id'])
                        seller_order_dict['order_status'] = eval(order_mapping['order_status'])
                        seller_order_dict['order_id'] = order_detail.id
                        seller_order_dict['quantity'] = eval(order_mapping['quantity'])

                    check_create_seller_order(seller_order_dict, order_detail, user, swx_mappings)
                    insert_status['Orders Inserted'] += 1

                    order_issue_objs = OrdersTrack.objects.filter(user = user.id, order_id = original_order_id, sku_code = sku_code).exclude(mapped_sku_code = "", channel_sku = "")

                    if not order_issue_objs:
                        order_issue_objs = OrdersTrack.objects.filter(user = user.id, order_id = original_order_id, channel_sku= eval(order_mapping['channel_sku'])).exclude(mapped_sku_code = "", sku_code = "")

                    if order_issue_objs:
                        order_issue_objs = order_issue_objs[0]
                        order_issue_objs.mapped_sku_code = sku_code
                        order_issue_objs.status = 0
                        order_issue_objs.save()
        return insert_status

    except:
        traceback.print_exc()
        return insert_status

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

def sku_master_insert_update(sku_data, user, sku_mapping, insert_status, parent_sku=None):
    sku_master = None
    sku_code = sku_data.get(sku_mapping['sku_code'], '')
    if not sku_code:
        insert_status['SKU Code should not be empty'].append(sku_data.get(sku_mapping['sku_desc'], ''))
        return sku_master, insert_status
    sku_ins = SKUMaster.objects.filter(user=user.id, sku_code=sku_code)
    if sku_ins:
        sku_master = sku_ins[0]
    sku_master_dict = {'user': user.id, 'creation_date': datetime.datetime.now()}
    exclude_list = ['skus', 'child_skus']
    number_fields = ['threshold_quantity', 'ean_number', 'hsn_code', 'price', 'mrp', 'status', 'sku_size']
    sku_size = ''
    size_type = ''
    sku_options = []
    for key, val in sku_mapping.iteritems():
        if key in exclude_list:
            continue
        value = sku_data.get(val, '')
        if key in number_fields:
            try:
                value = float(value)
            except:
                value = 0
        elif key == 'size_type':
            sku_size = sku_data.get('sku_size', '')
            if sku_size and not value:
                insert_status['Size Type empty'].append(sku_code)
                continue
            elif sku_size and value:
                size_master = SizeMaster.objects.filter(user=user.id, size_name=value)
                if not size_master:
                    insert_status['Size Type Invalid'].append(sku_code)
                else:
                    sizes = size_master[0].size_value.split("<<>>")
                    if sku_size not in sizes:
                        insert_status['Size type and Size not matching'].append(sku_code)
                    else:
                        size_type = value
            continue
        elif key == 'mix_sku':
            if not value:
                continue
            if not str(value).lower() in MIX_SKU_MAPPING.keys():
                insert_status['Invalid Mix SKU Attribute'].append(sku_code)
                continue
            else:
                value = MIX_SKU_MAPPING[value.lower()]
        elif key == 'sku_type':
            if not value:
                continue
            elif str(value).upper() not in ['RM', 'FG', 'CS']:
                insert_status['SKU Type Invalid'].append(sku_code)
                continue
        elif key == 'attributes':
            if value and isinstance(value, list):
                sku_options = value
            continue
        sku_master_dict[key] = value
        if sku_master:
            setattr(sku_master, key, value)

    if sku_code in sum(insert_status.values(), []):
        return sku_master, insert_status
    if sku_master:
        sku_master.save()
        insert_status['SKUS updated'].append(sku_code)
    else:
        sku_master_dict['wms_code'] = sku_master_dict['sku_code']
        if sku_master_dict.has_key('sku_type'):
            sku_master_dict['sku_type'] = 'FG'
        sku_master = SKUMaster(**sku_master_dict)
        sku_master.save()
        insert_status['New SKUS Created'].append(sku_code)
    if sku_size and size_type:
        check_update_size_type(sku_master, size_type)
        sku_master.size_type = sku_size
        sku_master.save()

    if sku_master and sku_options:
        for option in sku_options:
            sku_attributes = SKUAttributes.objects.filter(sku_id=sku_master.id, attribute_name=option['name'])
            if sku_attributes:
                sku_attributes = sku_attributes[0]
                sku_attributes.attribute_value = option['value']
                sku_attributes.save()
            else:
                SKUAttributes.objects.create(sku_id=sku_master.id, attribute_name=option['name'], attribute_value=option['value'],
                                             creation_date=datetime.datetime.now())
    if sku_master and parent_sku:
        sku_relation = SKURelation.objects.filter(member_sku_id=sku_master.id, parent_sku_id=parent_sku.id)
        if not sku_relation:
            parent_sku.relation_type = 'combo'
            parent_sku.save()
            SKURelation.objects.create(member_sku_id=sku_master.id, parent_sku_id=parent_sku.id, relation_type='combo',
                                       creation_date=datetime.datetime.now())
            insert_status['Child SKUS Created'].append(sku_code)

    return sku_master, insert_status


def update_skus(skus, user='', company_name=''):
    sku_mapping = eval(LOAD_CONFIG.get(company_name, 'sku_mapping_dict', ''))
    NOW = datetime.datetime.now()

    insert_status = {'New SKUS Created': [], 'SKUS updated': [], 'Child SKUS Created': [], 'Size Type empty': [], 'Size Type Invalid': [],
                     'Size Type Invalid': [], 'Size type and Size not matching': [], 'Invalid Mix SKU Attribute': [],
                     'SKU Code should not be empty': [], 'SKU Type Invalid': []}

    try:
        user_profile = UserProfile.objects.get(user_id=user.id)
        sku_ids = []
        all_sku_masters = []
        if not skus:
            skus = {}
        skus = skus.get(sku_mapping['skus'], [])
        for sku_data in skus:
            sku_master, insert_status = sku_master_insert_update(sku_data, user, sku_mapping, insert_status)
            all_sku_masters.append(sku_master)
            if sku_data.has_key('child_skus'):
                for child_data in sku_data['child_skus']:
                    sku_master1, insert_status = sku_master_insert_update(child_data, user, sku_mapping, insert_status, parent_sku=sku_master)
                    all_sku_masters.append(sku_master1)

        insert_update_brands(user)

        all_users = get_related_users(user.id)
        sync_sku_switch = get_misc_value('sku_sync', user.id)
        if all_users and sync_sku_switch == 'true' and all_sku_masters:
            create_sku(all_sku_masters, all_users)
        final_status = {}
        for key, value in insert_status.iteritems():
            if not value:
                continue
            final_status[key] = ','.join(value)
        return final_status

    except:
        traceback.print_exc()
        return insert_status

def update_customers(customers, user='', company_name=''):
    customer_mapping = eval(LOAD_CONFIG.get(company_name, 'customer_mapping_dict', ''))
    NOW = datetime.datetime.now()

    insert_status = {'Newly Created customer ids': [], 'Data updated for customer ids': [],
                     'Customer ID should not be empty for customer names': [],
                     'Invalid Tax types for customer ids': [], 'Invalid Price types for customer ids': [],
                     'Customer ID should be number for customer names': []}

    try:
        user_profile = UserProfile.objects.get(user_id=user.id)
        customer_ids = []
        if not customers:
            customers = {}
        customers = customers.get(customer_mapping['customers'], [])
        price_types = list(PriceMaster.objects.filter(sku__user=user.id).values_list('price_type', flat=True).distinct())
        for customer_data in customers:
            customer_master = None
            customer_id = customer_data.get(customer_mapping['customer_id'], '')
            if not customer_id:
                insert_status['Customer ID should not be empty for customer names'].append(str(customer_data.get(customer_mapping['name'], '')))
                continue
            elif not isinstance(customer_id, int):
                insert_status['Customer ID should be number for customer names'].append(str(customer_data.get(customer_mapping['name'], '')))
                continue
            customer_ins = CustomerMaster.objects.filter(user=user.id, customer_id=customer_id)
            if customer_ins:
                customer_master = customer_ins[0]
            customer_master_dict = {'user': user.id, 'creation_date': datetime.datetime.now()}
            exclude_list = ['customers']
            number_fields = {'credit_period': 'Credit Period', 'status': 'Status', 'customer_id': 'Customer ID', 'pincode': 'Pin Code',
                             'phone_number': 'Phone Number'}
            for key, val in customer_mapping.iteritems():
                if key in exclude_list:
                    continue
                value = customer_data.get(key, '')
                if key in number_fields.keys():
                    if not value:
                        value = 0
                    try:
                        value = int(value)
                    except:
                        if insert_status.has_key(number_fields[key] + " should be number for Customer ids"):
                            insert_status[number_fields[key] + " should be number for Customer ids"].append(str(customer_id))
                        else:
                            insert_status[number_fields[key] + " should be number for Customer ids"] = [str(customer_id)]
                elif key == 'tax_type':
                    if not value:
                        continue
                    if not value in TAX_TYPE_ATTRIBUTES.values():
                        insert_status['Invalid Tax types for customer ids'].append(str(customer_id))
                        continue
                    rev_taxes = dict(zip(TAX_TYPE_ATTRIBUTES.values(), TAX_TYPE_ATTRIBUTES.keys()))
                    value = rev_taxes.get(value, '')
                elif key == 'price_type':
                    if not value:
                        continue
                    if not value in price_types:
                        insert_status['Invalid Price types for customer ids'].append(str(customer_id))
                customer_master_dict[key] = value
                if customer_master:
                    setattr(customer_master, key, value)

            if str(customer_id) in sum(insert_status.values(), []):
                continue
            if customer_master:
                customer_master.save()
                insert_status['Data updated for customer ids'].append(str(customer_id))
            else:
                customer_master = CustomerMaster(**customer_master_dict)
                customer_master.save()
                insert_status['Newly Created customer ids'].append(str(customer_id))

        final_status = {}
        for key, value in insert_status.iteritems():
            if not value:
                continue
            final_status[key] = ','.join(value)
        return final_status

    except:
        traceback.print_exc()
        return insert_status

def validate_sellers(sellers, user=None, seller_mapping=None):

    if not sellers or not user or not seller_mapping:
        return [None, None, None]

    messages = {}
    sellers_update = []
    is_valid = True

    for seller_data in sellers:
        seller_id = seller_data.get(seller_mapping['seller_id'], '')

        if not seller_id:
            is_valid = is_valid and False
            insert_message(messages, 'No ids', 'Seller ID should not be empty for '+ seller_data['name'])
            continue

        seller_master_dict = {'user': user.id, 'creation_date': datetime.datetime.now()}
        exclude_list = ['sellers']
        number_fields = {'status': 'Status','phone_number': 'Phone Number',
         'seller_id': 'Seller Id', 'margin': 'Margin'}

        string_fields = {'name': 'Name', 'address': 'Address', 'gstin_no':'GSTIN number'}

        for key, val in seller_mapping.iteritems():
            if key in exclude_list:
                continue
            value = seller_data.get(seller_mapping[key], '')
            if key in number_fields.keys():
                value = value or 0
                try:
                    value = int(value)
                except:
                    is_valid = is_valid and False
                    insert_message(messages, seller_data['seller_id'], number_fields[key] + " should be number")

            if key in string_fields.keys():
                value = value or ''
                try:
                    assert isinstance(value, basestring) == True
                except:
                    is_valid = is_valid and False
                    insert_message(messages, seller_data['seller_id'], string_fields[key] + " should be string")

            seller_master_dict[key] = value
        sellers_update.append(seller_master_dict)
    return [is_valid, sellers_update, messages]


def update_sellers(sellers, user='', company_name=''):
    seller_mapping = eval(LOAD_CONFIG.get(company_name, 'seller_mapping_dict', ''))
    NOW = datetime.datetime.now()
    status = {}
    messages= {}
    try:
        user_profile = UserProfile.objects.get(user_id=user.id)
        if not sellers:
            sellers = {}
        sellers = sellers.get(seller_mapping['sellers'], [])

        is_valid, sellers, messages = validate_sellers(sellers, user, seller_mapping)

        if is_valid:
            for seller in sellers:
                try:
                    seller_master, created = SellerMaster.objects.get_or_create(
                    user=seller['user'], seller_id=seller['seller_id'])

                    for key, value in seller.iteritems():
                        if key == 'tin_number':
                            value = str(value)
                        setattr(seller_master, key, value)
                    seller_master.save()
                except Exception as e:
                    traceback.print_exc()
                    is_valid = is_valid and False
                    print e.message
                    insert_message(messages, seller['seller_id'], e.message)

        if is_valid:
            status['status'] = 1
            status['messages'] = ['success']
        else:
            status['status'] = 0
            status['messages'] = messages.values()
        return status

    except Exception as e:
        traceback.print_exc()
        status['status'] = 0
        status['messages'] = [e.message]
        return status

def insert_message(messages, seller_id, message):
    try:
        statuses = messages.setdefault(
            seller_id, {})
        statuses.update({'seller_id':seller_id})
        statuses.setdefault(
            'messages', []).append(message)
    except Exception as e:
        return False
    return True

def update_order_cancel(orders_data, user='', company_name=''):
    NOW = datetime.datetime.now()
    try:
        for key, order_dict in orders_data.iteritems():
            original_order_id = order_dict['order_details']['original_order_id']
            filter_params = {'user': user.id, 'original_order_id': original_order_id, 'sku_id': order_dict['order_details']['sku_id'],
                             'order_id': order_dict['order_details']['order_id'], 'order_code': order_dict['order_details']['order_code']}

            order_det = OrderDetail.objects.exclude(status=3).filter(**filter_params)
            if order_det:
                order_det = order_det[0]
                if int(order_det.status) == 1:
                    order_det.status = 3
                    order_det.save()
                    if order_dict.get('seller_order_dict', {}):
                        seller_order = SellerOrder.objects.filter(sor_id=order_dict['seller_order_dict']['sor_id'], order_id=order_det.id)
                        if seller_order:
                            seller_order.update(status=0)
                else:
                    picklists = Picklist.objects.filter(order_id=order_det.id, order__user=user.id)
                    for picklist in picklists:
                        if picklist.picked_quantity <= 0:
                            picklist.delete()
                        elif picklist.stock:
                            cancel_location = CancelledLocation.objects.filter(picklist_id=picklist.id, picklist__order__user=user.id)
                            if not cancel_location:
                                seller_id = order_dict['seller_order_dict']['seller_id']
                                CancelledLocation.objects.create(picklist_id=picklist.id, quantity=picklist.picked_quantity,
                                             location_id=picklist.stock.location_id, creation_date=datetime.datetime.now(), status=1,
                                             seller_id=seller_id)
                                picklist.status = 'cancelled'
                                picklist.save()
                        else:
                            picklist.status = 'cancelled'
                            picklist.save()
                    order_det.status = 3
                    order_det.save()
                save_order_tracking_data(order_det, quantity=order_dict['order_details'].get('quantity', 0), status='cancelled', imei='')
        return "Success"
    except:
        traceback.print_exc()

def update_order_returns(orders_data, user='', company_name=''):
    NOW = datetime.datetime.now()
    try:
        for key, order_dict in orders_data.iteritems():
            original_order_id = order_dict['order_details']['original_order_id']
            filter_params = {'user': user.id, 'original_order_id': original_order_id, 'sku_id': order_dict['order_details']['sku_id'],
                             'order_id': order_dict['order_details']['order_id'], 'order_code': order_dict['order_details']['order_code']}

        return "Success"
    except:
        traceback.print_exc()
