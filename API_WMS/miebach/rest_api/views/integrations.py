from miebach_admin.models import *
from common import *
from masters import *
from uploads import *
from miebach.settings import INTEGRATIONS_CFG_FILE
from dateutil import parser
import traceback
import ConfigParser
import datetime
import unicodedata
from rest_api.views.mail_server import send_mail

LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read(INTEGRATIONS_CFG_FILE)
log = init_logger('logs/integrations.log')
log_err = init_logger('logs/integration_errors.log')

def check_and_add_dict(grouping_key, key_name, adding_dat, final_data_dict={}, is_list=False):
    final_data_dict.setdefault(grouping_key, {})
    final_data_dict[grouping_key].setdefault(key_name, {})
    if is_list:
        final_data_dict[grouping_key].setdefault(key_name, [])
        final_data_dict[grouping_key][key_name] = copy.deepcopy(
            list(chain(final_data_dict[grouping_key][key_name], adding_dat)))

    elif grouping_key in final_data_dict.keys() and final_data_dict[grouping_key][key_name].has_key('quantity'):
        final_data_dict[grouping_key][key_name]['quantity'] = final_data_dict[grouping_key][key_name]['quantity'] + \
                                                              adding_dat.get('quantity', 0)
    # elif grouping_key in final_data_dict.keys() and final_data_dict[grouping_key][key_name].has_key('invoice_amount'):
        final_data_dict[grouping_key][key_name]['invoice_amount'] = final_data_dict[grouping_key][key_name][
                                                                  'invoice_amount'] + \
                                                              adding_dat.get('invoice_amount', 0)
    else:
        final_data_dict[grouping_key][key_name] = copy.deepcopy(adding_dat)

    return final_data_dict


def validate_orders(orders, user='', company_name='', is_cancelled=False):
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'order_mapping_dict', ''))
    NOW = datetime.datetime.now()
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
                        seller_parent_id = order_mapping['seller_parent_item_id']
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
                    seller_order = SellerOrder.objects.filter(
                        Q(order__original_order_id=original_order_id) | Q(order__order_id=order_id,
                                                                          order__order_code=order_code),
                        sor_id=eval(order_mapping['sor_id']), seller__user=user.id)
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
                    grouping_key = str(original_order_id) + '<<>>' + str(sku_master[0].sku_code) + '<<>>' + str(
                        order_sor_id)
                    final_data_dict = check_and_add_dict(grouping_key, 'swx_mappings', swx_mappings,
                                                         final_data_dict=final_data_dict, is_list=True)
                    order_det = OrderDetail.objects.filter(**filter_params)
                    order_det1 = OrderDetail.objects.filter(**filter_params1)
                    invoice_amount = float(data.get('total_price', 0))

                    if 'unit_price' in order_mapping:
                        invoice_amount = float(eval(order_mapping['unit_price'])) * float(
                            eval(order_mapping['quantity']))
                        order_details['unit_price'] = float(eval(order_mapping['unit_price']))
                    if order_mapping.has_key('cgst_tax'):
                        order_summary_dict['cgst_tax'] = eval(order_mapping['cgst_tax'])
                        order_summary_dict['sgst_tax'] = eval(order_mapping['sgst_tax'])
                        order_summary_dict['igst_tax'] = eval(order_mapping['igst_tax'])
                        order_summary_dict['inter_state'] = 0
                        if order_summary_dict['igst_tax']:
                            order_summary_dict['inter_state'] = 1
                        tot_invoice = (float(invoice_amount) / 100) * (
                        float(order_summary_dict['cgst_tax']) + float(order_summary_dict['sgst_tax']) \
                        + float(order_summary_dict['igst_tax']))
                        invoice_amount += float(tot_invoice)

                    if not order_det:
                        order_det = order_det1

                    order_create = True
                    if (order_det and filter_params['sku_id'] in sku_ids) or (
                        order_det and seller_id in seller_master_dict.keys()) \
                            and not order_status == 'DELIVERY_RESCHEDULED':
                        order_det = order_det[0]
                        # order_det.quantity += float(eval(order_mapping['quantity']))
                        # order_det.invoice_amount += invoice_amount
                        # order_det.save()
                        # final_data_dict = check_and_add_dict(grouping_key, 'order_detail_obj', order_det, final_data_dict=final_data_dict)
                        if order_det and seller_id in seller_master_dict.keys():
                            order_create = False
                        elif is_cancelled:
                            final_data_dict = check_and_add_dict(grouping_key, 'order_details', order_details,
                                                                 final_data_dict=final_data_dict)
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

                        final_data_dict = check_and_add_dict(grouping_key, 'order_details', order_details,
                                                             final_data_dict=final_data_dict)

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
                        final_data_dict = check_and_add_dict(grouping_key, 'seller_order_dict', seller_order_dict,
                                                             final_data_dict=final_data_dict)

        return insert_status, final_data_dict

    except:
        traceback.print_exc()
        return insert_status, final_data_dict


def validate_ingram_orders(orders, user='', company_name='', is_cancelled=False):
    order_status_dict = {'NEW': 1, 'RETURN': 3, 'CANCEL': 4}
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'order_mapping_dict', ''))
    NOW = datetime.datetime.now()
    seller_id = ''
    seller_master = []
    insert_status = []
    final_data_dict = OrderedDict()
    try:
        seller_masters = SellerMaster.objects.filter(user=user.id)
        user_profile = UserProfile.objects.get(user_id=user.id)
        seller_master_dict, valid_order, query_params = {}, {}, {}
        sku_ids = []
        failed_status = OrderedDict()
        if not orders:
            orders = {}
        orders = eval(order_mapping['items'])
        if order_mapping.get('is_dict', False):
            orders = [orders]

        for ind, orders in enumerate(orders):
            order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
            can_fulfill = orders.get('can_fulfill', '1')
            channel_name = eval(order_mapping['channel'])
            if can_fulfill == '0':
                continue

            order_details = copy.deepcopy(ORDER_DATA)
            data = orders
            ingram_order_id = str(data[order_mapping['order_id']])
            original_order_id = channel_name + '_' + ingram_order_id
            order_code = ''.join(re.findall('\D+', original_order_id))
            order_id = ''.join(re.findall('\d+', original_order_id))
            filter_params = {'user': user.id, 'order_id': order_id}
            filter_params1 = {'user': user.id, 'original_order_id': original_order_id}

            order_status = eval(order_mapping['order_status'])
            if order_status in order_status_dict.keys():
                order_details['status'] = order_status_dict[order_status]
            else:
                failed_status.append({"OrderId": ingram_order_id,
                                      "result": {"errors": [
                                          {
                                              "ErrorCode": "5024",
                                              "ErrorMessage": 'Invalid Order Status - Should be ' + ','.join(
                                                  order_status_dict.keys())
                                          }
                                      ]
                                      }
                                      })

                break;

            if order_mapping.has_key('customer_id'):
                order_details['customer_id'] = int(eval(order_mapping['customer_id']))
                order_details['customer_name'] = eval(order_mapping['customer_name'])
                order_details['telephone'] = eval(order_mapping['telephone'])
                order_details['city'] = eval(order_mapping['city'])
                order_details['address'] = eval(order_mapping['address'])

            if order_code:
                filter_params['order_code'] = order_code
            order_items = [orders]
            if order_mapping.get('order_items', ''):
                order_items = eval(order_mapping['order_items'])

            valid_order['user'] = user.id
            valid_order['marketplace'] = channel_name
            valid_order['original_order_id'] = original_order_id
            if order_details['status'] in [1]:
                valid_order['status__in'] = [1, 2, 3, 4, 5]
            elif order_details['status'] in [3, 4]:
                valid_order['status__in'] = [3, 4]
            order_detail_present = OrderDetail.objects.filter(**valid_order)
            if order_detail_present:
                if int(order_detail_present[0].status) == 1:
                    error_code = "5001"
                    message = 'Duplicate Order, ignored at Stockone'
                elif int(order_detail_present[0].status) == 3:
                    error_code = "5002"
                    message = 'Order is already returned at Stockone'
                elif int(order_detail_present[0].status) == 4:
                    error_code = "5003"
                    message = 'Order is already cancelled at Stockone'
                failed_status.append({"OrderId": ingram_order_id,
                                      "Result": {"Errors": [
                                          {
                                              "ErrorCode": error_code, "ErrorMessage": message
                                          }
                                      ]
                                      }
                                      })
                break;
            for order in order_items:
                try:
                    shipment_date = NOW  # by default shipment date assigned as NOW
                    # shipment_date = eval(order_mapping['shipment_date'])
                except:
                    shipment_date = NOW
                if not order_mapping.get('line_items'):
                    sku_items = [order]
                else:
                    sku_items = eval(order_mapping['line_items'])
                failed_sku_status = []
                for sku_item in sku_items:
                    sku_code = eval(order_mapping['sku'])
                    swx_mappings = []
                    seller_item_id = ''
                    seller_parent_id = ''
                    sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                    if sku_master:
                        filter_params['sku_id'] = sku_master[0].id
                        filter_params1['sku_id'] = sku_master[0].id
                    else:
                        failed_sku_status.append({
                            "ErrorCode": "5020",
                            "ErrorMessage": "SKU Not found in Stockone",
                            "SKUId": sku_code
                        })

                    if sku_master:
                        order_sor_id = ''
                        grouping_key = str(original_order_id) + '<<>>' + str(sku_master[0].sku_code)
                        order_det = OrderDetail.objects.filter(**filter_params)
                        order_det1 = OrderDetail.objects.filter(**filter_params1)

                        invoice_amount = float(eval(order_mapping['total_price']))
                        unit_price = float(eval(order_mapping['unit_price']))
                        if not order_det:
                            order_det = order_det1

                        order_create = True

                        if order_create:
                            order_details['original_order_id'] = original_order_id
                            order_details['order_id'] = order_id
                            order_details['order_code'] = order_code

                            order_details['sku_id'] = sku_master[0].id
                            order_details['title'] = eval(order_mapping['title'])
                            order_details['user'] = user.id
                            order_details['quantity'] = float(eval(order_mapping['quantity']))
                            order_details['shipment_date'] = shipment_date
                            order_details['marketplace'] = channel_name
                            order_details['payment_mode'] = eval(order_mapping['payment_method'])
                            order_details['invoice_amount'] = float(invoice_amount)
                            order_details['unit_price'] = float(unit_price)
                            order_details['creation_date'] = eval(order_mapping['created_at'])
                            order_details['updation_date'] = eval(order_mapping['created_at'])

                            final_data_dict = check_and_add_dict(grouping_key, 'order_details', order_details,
                                                                 final_data_dict=final_data_dict)

                        if not failed_status and not insert_status:
                            order_summary_dict['cgst_tax'] = float(eval(order_mapping['cgst_tax'])) if eval(
                                order_mapping['cgst_tax']) else 0
                            order_summary_dict['sgst_tax'] = float(eval(order_mapping['sgst_tax'])) if eval(
                                order_mapping['sgst_tax']) else 0
                            order_summary_dict['igst_tax'] = float(eval(order_mapping['igst_tax'])) if eval(
                                order_mapping['igst_tax']) else 0
                            order_summary_dict['order_taken_by'] = order_details['customer_name']
                            order_summary_dict['consignee'] = order_details['address']
                            order_summary_dict['status'] = ''
                            order_summary_dict['invoice_date'] = order_details['creation_date']
                            order_summary_dict['inter_state'] = 0
                            if order_summary_dict['igst_tax']:
                                order_summary_dict['inter_state'] = 1
                            final_data_dict = check_and_add_dict(grouping_key, 'order_summary_dict',
                                                                 order_summary_dict, final_data_dict=final_data_dict)

                if len(failed_sku_status):
                    failed_status = {
                        "OrderId": ingram_order_id,
                        "Result": {
                            "Errors": failed_sku_status
                        }
                    }
                    break;

                if not failed_status and not insert_status and order_details['customer_id']:
                    query_params['customer_id'] = order_details['customer_id']
                    query_params['user'] = user.id
                    try:
                        customer_obj = CustomerMaster.objects.filter(**query_params)
                    except:
                        customer_obj = []
                    if not customer_obj:
                        query_params['name'] = order_details['customer_name']
                        query_params['city'] = order_details['city']
                        query_params['phone_number'] = order_details['telephone']
                        query_params['address'] = order_details['address']
                        query_params['last_name'] = eval(order_mapping['last_name'])
                        query_params['pincode'] = eval(order_mapping['pin_code'])
                        query_params['country'] = eval(order_mapping['country'])
                        CustomerMaster.objects.create(**query_params)

                if not failed_status and not insert_status and eval(order_mapping.get('seller_name', '')):
                    seller_name = eval(order_mapping.get('seller_name', ''))
                    seller_address = eval(order_mapping.get('seller_address', ''))
                    seller_city = eval(order_mapping.get('seller_city', ''))
                    seller_region = eval(order_mapping.get('seller_region', ''))
                    seller_country = eval(order_mapping.get('seller_country', ''))
                    seller_postal = eval(order_mapping.get('seller_postal', ''))
                    seller_tax_id = eval(order_mapping.get('seller_tax_id', ''))

                    seller_master_obj = SellerMaster.objects.filter(user=user.id)
                    seller_master = seller_master_obj.filter(name=seller_name)
                    if not seller_master:
                        try:
                            seller_max_value = seller_master_obj.order_by('-seller_id')[0]
                            seller_id = seller_max_value.id + 1
                        except:
                            seller_id = 1
                        seller_master = SellerMaster.objects.create(user=user.id, name=seller_name,
                                                                    seller_id=seller_id, email_id='', phone_number='',
                                                                    address=seller_address,
                                                                    vat_number='', tin_number='', price_type='',
                                                                    margin='', supplier=None,
                                                                    status=1, creation_date=datetime.datetime.now(),
                                                                    updation_date=datetime.datetime.now())

                final_data_dict[grouping_key]['shipping_tax'] = eval(order_mapping.get('shipping_tax', ''))
                final_data_dict[grouping_key]['status_type'] = order_status

        return insert_status, failed_status.values(), final_data_dict, seller_master
    except:
        traceback.print_exc()
        return insert_status, failed_status.values(), final_data_dict, seller_master


def update_orders(orders, user='', company_name=''):
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'order_mapping_dict', ''))
    NOW = datetime.datetime.now()

    insert_status = {'Orders Inserted': 0, 'Seller Master does not exists': 0, 'SOR ID not found': 0,
                     'Order Status not Matched': 0,
                     'Order Exists already': 0, 'Invalid SKU Codes': 0, 'Invalid Delivery Rescheduled Order': 0}

    try:
        seller_masters = SellerMaster.objects.filter(user=user.id)
        user_profile = UserProfile.objects.get(user_id=user.id)
        seller_master_dict = {}
        sku_ids = []
        if not orders:
            orders = {}
        # orders = orders.get(order_mapping['items'], [])
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
                    seller_order = SellerOrder.objects.filter(
                        Q(order__original_order_id=original_order_id) | Q(order__order_id=order_id,
                                                                          order__order_code=order_code),
                        sor_id=eval(order_mapping['sor_id']), seller__user=user.id)
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
                        # SKUMaster.objects.create(sku_code=sku_code, wms_code=sku_code,user=user.id, status=1, creation_date=NOW,
                        #                                      online_percentage=0)
                        # sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                        # filter_params['sku_id'] = sku_master[0].id
                        # filter_params1['sku_id'] = sku_master[0].id
                        reason = ''
                        insert_status['Invalid SKU Codes'] += 1
                        channel_sku = eval(order_mapping['channel_sku'])
                        if sku_code:
                            reason = "SKU Mapping doesn't exists"
                            orders_track = OrdersTrack.objects.filter(order_id=original_order_id, sku_code=sku_code,
                                                                      user=user.id)
                        else:
                            reason = "SKU Code missing"
                            orders_track = OrdersTrack.objects.filter(order_id=original_order_id,
                                                                      channel_sku=channel_sku, user=user.id)
                        if not orders_track:
                            OrdersTrack.objects.create(order_id=original_order_id, sku_code=sku_code, status=1,
                                                       user=user.id,
                                                       marketplace=channel_name, title=eval(order_mapping['title']),
                                                       company_name=company_name,
                                                       channel_sku=channel_sku, shipment_date=shipment_date,
                                                       quantity=eval(order_mapping['quantity']),
                                                       reason=reason, creation_date=NOW)
                        continue

                    order_det = OrderDetail.objects.filter(**filter_params)
                    order_det1 = OrderDetail.objects.filter(**filter_params1)
                    invoice_amount = float(data.get('total_price', 0))

                    if 'unit_price' in order_mapping:
                        invoice_amount = float(eval(order_mapping['unit_price'])) * float(
                            eval(order_mapping['quantity']))
                        order_details['unit_price'] = float(eval(order_mapping['unit_price']))
                    if order_mapping.has_key('cgst_tax'):
                        order_summary_dict['cgst_tax'] = eval(order_mapping['cgst_tax'])
                        order_summary_dict['sgst_tax'] = eval(order_mapping['sgst_tax'])
                        order_summary_dict['igst_tax'] = eval(order_mapping['igst_tax'])
                        order_summary_dict['inter_state'] = 0
                        if order_summary_dict['igst_tax']:
                            order_summary_dict['inter_state'] = 1
                        tot_invoice = (float(invoice_amount) / 100) * (
                        float(order_summary_dict['cgst_tax']) + float(order_summary_dict['sgst_tax']) \
                        + float(order_summary_dict['igst_tax']))
                        invoice_amount += float(tot_invoice)

                    if not order_det:
                        order_det = order_det1

                    order_create = True
                    if (order_det and filter_params['sku_id'] in sku_ids) or (
                        order_det and seller_id in seller_master_dict.keys()) \
                            and not order_status == 'DELIVERY_RESCHEDULED':
                        order_det = order_det[0]
                        order_det.quantity += float(eval(order_mapping['quantity']))
                        order_det.invoice_amount += invoice_amount

                        # order_det.save()
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
                        swx_mappings.append(
                            {'app_host': 'shotang', 'swx_id': eval(order_mapping['seller_parent_item_id']),
                             'swx_type': 'seller_parent_item_id'})
                    if order_mapping.has_key('sor_id'):
                        seller_order_dict['seller_id'] = seller_master_dict[seller_id]
                        seller_order_dict['sor_id'] = eval(order_mapping['sor_id'])
                        seller_order_dict['order_status'] = eval(order_mapping['order_status'])
                        seller_order_dict['order_id'] = order_detail.id
                        seller_order_dict['quantity'] = eval(order_mapping['quantity'])

                    check_create_seller_order(seller_order_dict, order_detail, user, swx_mappings)
                    insert_status['Orders Inserted'] += 1

                    order_issue_objs = OrdersTrack.objects.filter(user=user.id, order_id=original_order_id,
                                                                  sku_code=sku_code).exclude(mapped_sku_code="",
                                                                                             channel_sku="")

                    if not order_issue_objs:
                        order_issue_objs = OrdersTrack.objects.filter(user=user.id, order_id=original_order_id,
                                                                      channel_sku=eval(
                                                                          order_mapping['channel_sku'])).exclude(
                            mapped_sku_code="", sku_code="")

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

                    sku_obj = SKUMaster.objects.filter(user=user.id, sku_code=sku_code)

                    if not sku_obj:
                        continue
                    qty = eval(order_mapping['return_quantity']) + eval(order_mapping['damaged_quantity'])
                    order_data = OrderDetail.objects.create(user=user.id, order_id=_order_id, order_code=_order_code,
                                                            status=4, original_order_id=original_order_id,
                                                            marketplace=eval(order_mapping['marketplace']),
                                                            quantity=qty, sku=sku_obj[0], shipment_date=NOW.date())

                else:
                    order_data = order_data[0]
                return_instance = OrderReturns.objects.filter(return_id=return_id, order_id=order_data.id,
                                                              order__user=user.id)
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
                                cancel_location = CancelledLocation.objects.filter(picklist_id=picklist.id,
                                                                                   picklist__order__user=user.id)
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
                        order_det.status = 3
                        order_det.save()
    except:
        traceback.print_exc()


def sku_master_insert_update(sku_data, user, sku_mapping, insert_status, failed_status, user_attr_list, sizes_dict,
                             new_ean_objs, load_file, columns, exist_sku_eans, exist_ean_list):
    sku_master = None
    sku_code = sku_data.get(sku_mapping['sku_code'], '')
    if sku_data.get(sku_mapping['sku_desc'], ''):
        if isinstance(sku_data[sku_mapping['sku_desc']], unicode):
            sku_data[sku_mapping['sku_desc']] = sku_data[sku_mapping['sku_desc']].encode('ascii', 'ignore')
    if not sku_code:
        error_message = 'SKU Code should not be empty'
        update_error_message(failed_status, 5022, error_message, sku_data[sku_mapping['sku_desc']],
                             field_key='sku_desc')
        return sku_master, insert_status, new_ean_objs
    sku_ins = SKUMaster.objects.filter(user=user.id, sku_code=sku_code)
    if sku_ins.exists():
        sku_master = sku_ins[0]
    sku_master_dict = {'user': user.id, 'creation_date': datetime.datetime.now()}
    exclude_list = ['skus', 'child_skus']
    number_fields = ['threshold_quantity', 'max_norm_quantity', 'price', 'mrp', 'status', 'shelf_life', 'cost_price']
    sku_size = ''
    size_type = ''
    sku_options = []
    ean_numbers = ''
    taxes_mapping = {'cgst': 'cgst_tax', 'sgst': 'sgst_tax', 'igst': 'igst_tax', 'cess': 'cess_tax'}
    taxes_dict = {}
    option_not_created = []
    for key, val in sku_mapping.iteritems():
        if key in exclude_list:
            continue
        if val not in sku_data.keys():
            continue
        value = sku_data.get(val, '')
        if key in number_fields:
            try:
                value = float(value)
            except:
                value = 0
        elif key == 'hsn_code':
            try:
                if isinstance(value, unicode):
                    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
                else:
                    value = str(value)
            except:
                value = ''
        elif key == 'size_type':
            sku_size = sku_data.get('sku_size', '')
            if sku_size and not value:
                error_message = 'Size Type empty'
                update_error_message(failed_status, 5026, error_message, sku_code,
                                     field_key='sku_code')
                continue
            elif sku_size and value:
                if not value in sizes_dict.keys():
                # size_master = SizeMaster.objects.filter(user=user.id, size_name=value)
                # if not size_master:
                    error_message = 'Size Type Invalid'
                    update_error_message(failed_status, 5027, error_message, sku_code,
                                         field_key='sku_code')
                else:
                    #sizes = size_master[0].size_value.split("<<>>")
                    sizes = sizes_dict[value].split('<<>>')
                    if sku_size not in sizes:
                        error_message = 'Size type and Size not matching'
                        update_error_message(failed_status, 5023, error_message, sku_code,
                                             field_key='sku_code')
                    else:
                        size_type = value
            continue
        elif key == 'mix_sku':
            if not value:
                continue
            if not str(value).lower() in MIX_SKU_MAPPING.keys():
                error_message = 'Invalid Mix SKU Attribute'
                update_error_message(failed_status, 5024, error_message, sku_code,
                                     field_key='sku_code')
                continue
            else:
                value = MIX_SKU_MAPPING[value.lower()]
        elif key == 'sku_type':
            if not value:
                continue
            elif str(value).upper() not in ['RM', 'FG', 'CS']:
                error_message = 'SKU Type Invalid'
                update_error_message(failed_status, 5025, error_message, sku_code,
                                     field_key='sku_code')
                continue
        elif key == 'attributes':
            if value and isinstance(value, list):
                sku_options = value
                option_names = map(operator.itemgetter('name'), sku_options)
                option_not_created = list(set(option_names) - set(user_attr_list))
                if option_not_created:
                    error_message = 'SKU Options %s are not created' % (','.join(option_not_created))
                    update_error_message(failed_status, 5030, error_message, sku_code,
                                         field_key='sku_code')
            continue
        elif key in ["cgst", "sgst", "igst", "cess"]:
            if value or value == '0':
                try:
                    taxes_dict[taxes_mapping[key]] = float(value)
                except:
                    taxes_dict[taxes_mapping[key]] = 0
            continue
        elif key == 'image_url':
            if value and 'http' not in value:
                error_message = 'Full Image URL Needed'
                update_error_message(failed_status, 5029, error_message, sku_code,
                                     field_key='sku_code')
        elif key == 'ean_number':
            if value:
                try:
                    ean_numbers = str(value.encode('utf-8').replace('\xc2\xa0', '').replace('\\xE2\\x80\\x8B', ''))
                except:
                    ean_numbers = ''
                for temp_ean in ean_numbers.split(','):
                    if not temp_ean:
                        continue
                    if len(str(temp_ean)) > 20:
                        error_message = 'EAN Number Length should be less than 20'
                        update_error_message(failed_status, 5032, error_message, sku_code,
                                            field_key='sku_code')
                    if temp_ean in exist_ean_list:
                        if not str(exist_ean_list[temp_ean]) == str(sku_code):
                            error_message = str(temp_ean) + ' EAN Number already mapped to SKU ' + str(exist_ean_list[temp_ean])
                            update_error_message(failed_status, 5031, error_message, sku_code,
                                                 field_key='sku_code')
                    elif temp_ean in exist_sku_eans:
                        if not str(exist_sku_eans[temp_ean]) == str(sku_code):
                            error_message = str(temp_ean) + ' EAN Number already mapped to SKU ' + str(exist_sku_eans[temp_ean])
                            update_error_message(failed_status, 5031, error_message, sku_code,
                                                 field_key='sku_code')
            elif sku_master:
                EANNumbers.objects.filter(sku_id=sku_master.id).delete()
                sku_obj = sku_master
                sku_obj.ean_number = ''
                sku_obj.save()

            continue
        if value is None:
            value = ''
        sku_master_dict[key] = value
        if sku_master:
            setattr(sku_master, key, value)

    if sku_code in sum(insert_status.values(), []):
        return sku_master, insert_status, new_ean_objs
    product_type = ''
    if taxes_dict :
        product_type_dict = {}
        cgst_check = True
        if taxes_dict.get('cgst_tax', 0) or taxes_dict.get('sgst_tax', 0):
            tax_master_obj = TaxMaster.objects.filter(cgst_tax=taxes_dict.get('cgst_tax', 0),
                                                    sgst_tax=taxes_dict.get('sgst_tax', 0), igst_tax=0,
                                                  cess_tax=taxes_dict.get('cess_tax', 0), user=user.id).\
                                        values_list('product_type', flat=True).distinct()
            if tax_master_obj.exists():
                product_type_dict['product_type__in'] = tax_master_obj
                product_type = tax_master_obj[0]
            else:
                cgst_check = False
        if taxes_dict.get('igst_tax', 0) and cgst_check:
            tax_master_obj = TaxMaster.objects.filter(igst_tax=taxes_dict.get('igst_tax', 0),
                                                        cess_tax=taxes_dict.get('cess_tax', 0), user=user.id,
                                                       **product_type_dict). \
                                            values_list('product_type', flat=True)
            if not tax_master_obj.exists():
                product_type = ''
            else:
                product_type = tax_master_obj[0]
        if not product_type and sum(taxes_dict.values()) > 0:
            error_message = 'Tax Master not found'
            update_error_message(failed_status, 5028, error_message, sku_code,
                                 field_key='sku_code')
    if '%s:%s' % ('sku_code', str(sku_code)) in failed_status.keys():
        return sku_master, insert_status, new_ean_objs
    update_sku_obj = False
    if sku_master:
        update_sku_obj = True
        #sku_master.save()
        insert_status['SKUS updated'].append(sku_code)
    else:
        sku_master_dict['wms_code'] = sku_master_dict['sku_code']
        if sku_master_dict.has_key('sku_type'):
            sku_master_dict['sku_type'] = 'FG'
        sku_master = SKUMaster(**sku_master_dict)
        sku_master.save()
        insert_status['SKUS Created'].append(sku_code)
    if sku_size and size_type:
        check_update_size_type(sku_master, size_type)
        sku_master.sku_size = sku_size
        sku_master.size_type = size_type
        update_sku_obj = True
        #sku_master.save()
    if sku_master and sku_options:
        for option in sku_options:
            if not option.get('value', ''):
                continue
            if option['name'] in option_not_created:
                continue
            try:
                if isinstance(option['name'], unicode):
                    option['name'] = unicodedata.normalize('NFKD', option['name']).encode('ascii', 'ignore')
                else:
                    option['name'] = str(option['name'])
            except:
                log.info(option['name'])
                log.info("Ascii Code Error Name for %s" % str(sku_master.sku_code))
                error_message = 'Ascii code characters Name found'
                update_error_message(failed_status, 5033, error_message, sku_code,
                                     field_key='sku_code')
            try:
                if isinstance(option['value'], unicode):
                    option['value'] = unicodedata.normalize('NFKD', option['value']).encode('ascii', 'ignore')
                else:
                    option['value'] = str(option['value'])
            except:
                log.info(option['value'])
                log.info("Ascii Code Error Value for %s" % str(sku_master.sku_code))
                error_message = 'Ascii code characters Value found'
                update_error_message(failed_status, 5033, error_message, sku_code,
                                     field_key='sku_code')
            column_vals = [str(sku_master.id), option['name'], option['value']]
            update_string = "sku_id=%s, attribute_name='%s',updation_date=NOW()" % (str(sku_master.id), str(option['name']))
            date_string = 'NOW(), NOW()'
            mysql_query_to_file(load_file, 'SKU_ATTRIBUTES', columns,
                                column_vals, date_string=date_string, update_string=update_string)
            # sku_attributes = sku_master.skuattributes_set.filter(attribute_name=option['name'])
            # if sku_attributes.exists():
            #     sku_attributes = sku_attributes[0]
            #     sku_attributes.attribute_value = option['value']
            #     sku_attributes.save()
            # else:
            #     SKUAttributes.objects.create(sku_id=sku_master.id, attribute_name=option['name'],
            #                                  attribute_value=option['value'],
            #                                  creation_date=datetime.datetime.now())
    if sku_master and taxes_dict :
        sku_master.product_type = product_type
        update_sku_obj = True
        #sku_master.save()
    if sku_master and ean_numbers:
        try:
            ean_numbers = ean_numbers.split(',')
            exist_eans = list(sku_master.eannumbers_set.exclude(ean_number='').\
                              annotate(str_eans=Cast('ean_number', CharField())).\
                          values_list('str_eans', flat=True))
            if sku_master.ean_number:
                exist_eans.append(str(sku_master.ean_number))
            rem_eans = set(exist_eans) - set(ean_numbers)
            create_eans = set(ean_numbers) - set(exist_eans)
            if rem_eans:
                rem_ean_objs = sku_master.eannumbers_set.filter(ean_number__in=rem_eans)
                if rem_ean_objs.exists():
                    rem_ean_objs.delete()
                for rem_ean in rem_eans:
                    if exist_ean_list.get(rem_ean, ''):
                        del exist_ean_list[rem_ean]
                    if exist_sku_eans.get(rem_ean, ''):
                        del exist_sku_eans[rem_ean]
            if str(sku_master.ean_number) in rem_eans:
                sku_master.ean_number = ''
                update_sku_obj = True
                #sku_master.save()
            for ean in create_eans:
                if not ean:
                    continue
                try:
                    ean = ean
                    new_ean_objs.append(EANNumbers(**{'ean_number': ean, 'sku_id': sku_master.id}))
                    ean_found = False
                    if exist_ean_list.get(ean, ''):
                        exist_ean_list[ean] = sku_master.sku_code
                        ean_found = True
                    elif exist_sku_eans.get(ean, ''):
                        exist_sku_eans[ean] = sku_master.sku_code
                        ean_found = True
                    if not ean_found:
                        exist_ean_list[ean] = sku_master.sku_code
                except:
                    pass
            #update_ean_sku_mapping(user, ean_numbers, sku_master, True)
        except:
            pass
    if update_sku_obj:
        sku_master.save()
    return sku_master, insert_status, new_ean_objs


def update_skus (skus, user='', company_name=''):
    sku_mapping = eval(LOAD_CONFIG.get(company_name, 'sku_mapping_dict', ''))
    NOW = datetime.datetime.now()
    insert_status = {'SKUS Created': [], 'SKUS updated': []}
    failed_status = OrderedDict()
    try:
        token_user = user
        sister_whs1 = list(get_sister_warehouse(user).values_list('user__username', flat=True))
        if 'warehouse' not in skus.keys() and sister_whs1:
            error_message = 'User %s have multiple warehouses. Please specify the warehouse.'% (str(user.username))
            update_error_message(failed_status, 5021, error_message, '', field_key='warehouse')
        if 'warehouse' in skus.keys():
        #     error_message = 'warehouse key missing'
        #     update_error_message(failed_status, 5020, error_message, '', field_key='warehouse')
        # else:
            warehouse = skus['warehouse']
            sister_whs1.append(token_user.username)
            sister_whs = []
            for sister_wh1 in sister_whs1:
                sister_whs.append(str(sister_wh1).lower())
            if warehouse.lower() in sister_whs:
                user = User.objects.get(username=warehouse)
            else:
                error_message = 'Invalid Warehouse Name'
                update_error_message(failed_status, 5021, error_message, warehouse, field_key='warehouse')
        if failed_status:
            return insert_status, failed_status.values()
        user_attr_list = get_user_attributes(user, 'sku')
        user_attr_list = list(user_attr_list.values_list('attribute_name', flat=True))
        user_profile = user.userprofile
        sku_ids = []
        added_sku_eans = []
        all_sku_masters = []
        if not skus:
            skus = {}
        skus = skus.get(sku_mapping['skus'], [])
        sizes_dict = dict(SizeMaster.objects.filter(user=user.id).values_list('size_name', 'size_value'))
        mysql_file_path = 'static/mysql_files'
        folder_check(mysql_file_path)
        file_time_stamp = str(datetime.datetime.now()).replace(':','_').replace('.', '_').replace(' ', '_')
        load_file_path = '%s/%s' % (mysql_file_path, 'sku_attr_' + file_time_stamp + '.txt')
        load_file = open(load_file_path, 'w')
        columns = ['sku_id', 'attribute_name', 'attribute_value']
        new_ean_objs = []

        exist_sku_eans = dict(SKUMaster.objects.filter(user=user.id, status=1).exclude(ean_number='').\
                              only('ean_number', 'sku_code').values_list('ean_number', 'sku_code'))
        exist_ean_list = dict(EANNumbers.objects.filter(sku__user=user.id, sku__status=1).\
                              only('ean_number', 'sku__sku_code').values_list('ean_number', 'sku__sku_code'))
        for sku_data in skus:
            sku_master, insert_status, new_ean_objs = sku_master_insert_update(sku_data, user, sku_mapping, insert_status,
                                                                 failed_status, user_attr_list, sizes_dict,
                                                                 new_ean_objs, load_file, columns, exist_sku_eans,
                                                                               exist_ean_list)
            all_sku_masters.append(sku_master)
            if sku_data.has_key('child_skus') and sku_data['child_skus'] and isinstance(sku_data['child_skus'], list):
                exist_member_ids = list(SKURelation.objects.filter(parent_sku_id=sku_master.id, relation_type='combo').\
                                            values_list('member_sku_id', flat=True))
                for child_data in sku_data['child_skus']:
                    child_sku_master = SKUMaster.objects.filter(user=user.id, sku_code=child_data['sku_code']).only('id', 'sku_code')
                    if not child_sku_master.exists():
                        child_obj = SKUMaster.objects.create(sku_code=child_data['sku_code'],
                                                             wms_code=child_data['sku_code'],
                                                             status=1, user=user.id, creation_date=NOW)
                    else:
                        child_obj = child_sku_master[0]
                    try:
                        quantity = float(child_data['quantity'])
                    except:
                        quantity = 1
                    NOW = datetime.datetime.now()
                    if child_obj.id in exist_member_ids:
                        exist_member_ids.remove(child_obj.id)
                    if child_obj and sku_master:
                        sku_relation = SKURelation.objects.filter(parent_sku_id=sku_master.id, member_sku_id=child_obj.id)
                        if not sku_relation.exists():
                            sku_master.relation_type = 'combo'
                            sku_master.save()
                            SKURelation.objects.create(member_sku_id=child_obj.id, parent_sku_id=sku_master.id,
                                                       relation_type='combo', quantity=quantity,
                                                       creation_date=NOW)
                            insert_status['SKUS Created'].append(child_obj.sku_code)
                        else:
                            sku_relation = sku_relation[0]
                            sku_relation.quantity = quantity
                            sku_relation.save()
                        all_sku_masters.append(child_obj)
                if exist_member_ids:
                    SKURelation.objects.filter(parent_sku_id=sku_master.id, relation_type='combo',
                                               member_sku_id__in=exist_member_ids).delete()
            elif sku_data.has_key('child_skus') and sku_master:
                sku_rel_check = SKURelation.objects.filter(parent_sku_id=sku_master.id, relation_type='combo')
                if sku_rel_check.exists():
                    sku_rel_check.delete()
                    sku_master.relation_type = ''
                    sku_master.save()
        if new_ean_objs:
            try:
                EANNumbers.objects.bulk_create(new_ean_objs)
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info("Ean Numbers update failed")
        insert_update_brands(user)

        all_users = get_related_users(user.id)
        sync_sku_switch = get_misc_value('sku_sync', user.id)
        load_by_file(load_file_path, 'SKU_ATTRIBUTES', columns)
        if all_users and sync_sku_switch == 'true' and all_sku_masters:
            create_update_sku(all_sku_masters, all_users)
        return insert_status, failed_status.values()

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.debug("Update SKU Failed")
        return insert_status, failed_status.values()


def update_customers(customers, user='', company_name=''):
    customer_mapping = eval(LOAD_CONFIG.get(company_name, 'customer_mapping_dict', ''))
    NOW = datetime.datetime.now()
    failed_status = OrderedDict()
    UIN = 0

    insert_status = {'Newly Created customer ids': [], 'Data updated for customer ids': [],
                     'Customer ID should not be empty for customer names': [],
                     'Invalid Tax types for customer ids': [], 'Invalid Price types for customer ids': [],
                     'Customer ID should be number for customer names': []}
    token_user = user
    sister_whs1 = list(get_sister_warehouse(user).values_list('user__username', flat=True))

    try:
        if customers.has_key('warehouse'):
            warehouse = customers['warehouse']
            sister_whs1.append(token_user.username)
            sister_whs = []
            for sister_wh1 in sister_whs1:
                sister_whs.append(str(sister_wh1).lower())
            if warehouse.lower() in sister_whs:
                user = User.objects.get(username=warehouse)
            else:
                error_message = 'Invalid Warehouse Name'
                update_error_message(failed_status, 5021, error_message, warehouse, field_key='warehouse')
        if failed_status:
            return UIN, failed_status.values()
        user_profile = UserProfile.objects.get(user_id=user.id)
        customer_ids = []
        if not customers:
            customers = {}
        customers = customers.get(customer_mapping['customers'], [])
        if isinstance(customers, dict):
            customers = [customers]
        price_types = list(PriceMaster.objects.filter(sku__user=user.id).values_list('price_type', flat=True).distinct())
        for customer_data in customers:
            customer_master = None
            customer_id = customer_data.get(customer_mapping['customer_id'], '')
            if not customer_id:
                # error_message = 'Customer ID should not be empty for customer name %s' % str(customer_data.get(customer_mapping['first_name'], ''))
                # update_error_message(failed_status, 5024, error_message, '', field_key='customer_id')
                # break
                customer_obj = CustomerMaster.objects.filter(user=user.id).values_list('customer_id', flat=True).\
                                                        order_by('-customer_id')
                if customer_obj:
                    customer_id = customer_obj[0] + 1
            try:
                customer_id = int(customer_id)
            except:
                error_message = 'Customer ID should be a number for customer name %s' % str(customer_data.get(customer_mapping['first_name'], ''))
                update_error_message(failed_status, 5024, error_message, customer_id, field_key='customer_id')
            customer_ins = CustomerMaster.objects.filter(user=user.id, customer_id=customer_id)
            if customer_ins:
                customer_master = customer_ins[0]
            customer_master_dict = {'user': user.id, 'creation_date': datetime.datetime.now()}
            exclude_list = ['customers']
            number_fields = {'credit_period': 'Credit Period', 'status': 'Status', 'customer_id': 'Customer ID',
                             'pincode': 'Pin Code','phone_number': 'Phone Number','discount_percentage':'discount_percentage'}
            for key, val in customer_mapping.iteritems():
                if key in exclude_list:
                    continue
                value = customer_data.get(key, '')
                if key in number_fields.keys():
                    if key == 'customer_id':
                        value = customer_id
                    if key == 'pincode':
                        value = customer_data.get('shipping_pincode', '')
                    if not value:
                        value = 0
                    try:
                        value = int(value)
                    except:
                        error_message = '%s should be number for customer id %s' % (str(number_fields[key]), str(customer_id))
                        update_error_message(failed_status, 5024, error_message, customer_id, field_key='customer_id')
                        break
                elif key == 'tax_type':
                    if not value:
                        continue
                    if not value in TAX_TYPE_ATTRIBUTES.values():
                        error_message = 'Invalid tax type for customer id %s' % str(customer_id)
                        update_error_message(failed_status, 5024, error_message, customer_id, field_key='customer_id')
                        break
                    rev_taxes = dict(zip(TAX_TYPE_ATTRIBUTES.values(), TAX_TYPE_ATTRIBUTES.keys()))
                    value = rev_taxes.get(value, '')
                elif key == 'price_type':
                    if not value:
                        continue
                    if not value in price_types:
                        error_message = 'Invalid price type for Customer id %s' % str(customer_id)
                        update_error_message(failed_status, 5024, error_message, customer_id, field_key='customer_id')
                        break
                elif key == 'customer_aux_info':
                    value = json.dumps(customer_data.get('customer_info', ''))
                elif key == 'name':
                    value = customer_data.get('first_name', '')
                elif key =='address':
                    value = customer_data.get('billing_address', '')
                elif key =='tin_number':
                    value = customer_data.get('gst_number', '')
                elif key =='state':
                    value = customer_data.get('shipping_state', '')
                elif key =='city':
                    value = customer_data.get('shipping_city', '')
                elif key =='country':
                    value = customer_data.get('shipping_country', '')
                customer_master_dict[key] = value
                if customer_master and value:
                    setattr(customer_master, key, value)

            if str(customer_id) in sum(insert_status.values(), []):
                continue
            if not failed_status:
                if customer_master:
                    customer_master.save()
                    insert_status['Data updated for customer ids'].append(str(customer_id))
                else:
                    customer_master = CustomerMaster(**customer_master_dict)
                    customer_master.save()
                    insert_status['Newly Created customer ids'].append(str(customer_id))
            if customer_master:
                UIN = customer_master.id

        # final_status = {}
        # for key, value in insert_status.iteritems():
        #     if not value:
        #         continue
        #     final_status[key] = ','.join(value)
        return UIN, failed_status.values(),customer_id

    except:
        traceback.print_exc()
        return UIN, failed_status.values(), customer_id

def validate_supplier(supplier, user=''):
    failed_status = OrderedDict()
    sister_whs1 = list(get_sister_warehouse(user).values_list('user__username', flat=True))
    sister_whs1.append(user.username)
    sister_whs = []
    for sister_wh1 in sister_whs1:
        sister_whs.append(str(sister_wh1).lower())
    try:
        if supplier.has_key('warehouse'):
            warehouse = supplier['warehouse']
            if warehouse.lower() in sister_whs:
                user = User.objects.get(username=warehouse)
            else:
                error_message = 'Invalid Warehouse Name'
                update_error_message(failed_status, 5024, error_message, '')
        if supplier.has_key('supplier_id'):
            supplier_id = supplier.get('supplier_id')
            supplier_master = get_or_none(SupplierMaster, {'id': supplier_id, 'user':user.id})
        else:
            error_message = 'supplier id missing'
            update_error_message(failed_status, 5024, error_message, '')

        supplier_dict = supplier_dict = {'name': '', 'address': '', 'phone_number': '', 'email_id': '',
                         'tax_type': '', 'po_exp_duration': '',
                         'spoc_name': '', 'spoc_number': '', 'spoc_email_id': '',
                         'lead_time': 0, 'credit_period': 0, 'bank_name': '', 'ifsc_code': '',
                         'branch_name': '', 'account_number': 0, 'account_holder_name': '',
                         'pincode':'','city':'','state':'','pan_number':'','tin_number':'','status':1
                        }
        data_dict = {"id":supplier_id, "user":user.id, 'creation_date':datetime.datetime.now(), 'updation_date':datetime.datetime.now()}
        for key,val in supplier_dict.iteritems():
            value = supplier.get(key, val)
            if key == 'email_id' and value:
                if validate_supplier_email(value):
                    update_error_message(failed_status, 5024, 'Enter valid Email ID', '')
            data_dict[key] = value
            if supplier_master and value:
                setattr(supplier_master, key, value)
        secondary_email_id = supplier.get('secondary_email_id', '')
        if secondary_email_id:
            secondary_email_id = secondary_email_id.split(',')
            for mail in secondary_email_id:
                if validate_supplier_email(mail):
                    update_error_message(failed_status, 5024, 'Enter valid secondary Email ID', '')
        if not failed_status:
            if supplier_master:
                supplier_master.save()
            else:
                supplier_master = SupplierMaster(**data_dict)
                supplier_master.save()
            if secondary_email_id:
                for mail in secondary_email_id:
                    master_email_map = {}
                    master_email_map['user'] = user
                    master_email_map['master_id'] = supplier_master.id
                    master_email_map['master_type'] = 'supplier'
                    master_email_map['email_id'] = mail
                    master_email_map['creation_date'] = datetime.datetime.now()
                    master_email_map['updation_date'] = datetime.datetime.now()
                    master_email_map = MasterEmailMapping.objects.create(**master_email_map)
        return failed_status.values()

    except:
        traceback.print_exc()
        return failed_status.values()

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
            insert_message(messages, 'No ids', 'Seller ID should not be empty for ' + seller_data['name'])
            continue

        seller_master_dict = {'user': user.id, 'creation_date': datetime.datetime.now()}
        exclude_list = ['sellers']
        number_fields = {'status': 'Status', 'phone_number': 'Phone Number',
                         'seller_id': 'Seller Id', 'margin': 'Margin'}

        string_fields = {'name': 'Name', 'address': 'Address', 'gstin_no': 'GSTIN number'}

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
    messages = {}
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
        statuses.update({'seller_id': seller_id})
        statuses.setdefault(
            'messages', []).append(message)
    except Exception as e:
        return False
    return True


def update_lineitem_ids(seller_order, swx_mappings):
    for swx_mapping in swx_mappings:
        if not swx_mapping['swx_type'] == 'seller_item_id':
            continue
        mapping_obj = SWXMapping.objects.filter(swx_type=swx_mapping['swx_type'], app_host=swx_mapping['app_host'],
                                                swx_id=swx_mapping['swx_id'], imei='')
        if mapping_obj:
            mapping_obj.update(imei='None')
            line_item_objs = SWXMapping.objects.filter(local_id=seller_order.id, app_host=swx_mapping['app_host'],
                                                       swx_type='seller_item_id', imei='')
            if not line_item_objs:
                SWXMapping.objects.filter(local_id=seller_order.id, app_host=swx_mapping['app_host'],
                                          swx_type='seller_parent_item_id').update(imei='None')


def validate_lineitem_ids(swx_mappings, seller_parent_id, order_det, insert_status=[]):
    seller_id = 0
    seller_order_ins = SellerOrder.objects.filter(order_id__in=order_det.values_list('id', flat=True))
    if seller_order_ins:
        seller_id = seller_order_ins[0].id
    for swx_mapping in swx_mappings:
        if not swx_mapping['swx_type'] == 'seller_item_id':
            continue
        mapping_obj = SWXMapping.objects.filter(swx_type=swx_mapping['swx_type'], app_host=swx_mapping['app_host'],
                                                swx_id=swx_mapping['swx_id'], local_id=seller_id)
        if mapping_obj and mapping_obj[0].imei == 'None':
            insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': swx_mapping['swx_id'],
                                  'error': 'Order Cancelled already'})
        elif mapping_obj and mapping_obj[0].imei:
            insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': swx_mapping['swx_id'],
                                  'error': 'Order Dispatched'})
    return insert_status


def update_cancelled_quantity(order_det, seller_order, picklist, cancel_quantity, order_dict, user, field_name):
    if getattr(picklist, field_name) > 0:
        reduced_quantity = 0
        if float(getattr(picklist, field_name)) <= cancel_quantity:
            reduced_quantity = float(getattr(picklist, field_name))
            cancel_quantity -= reduced_quantity
        else:
            reduced_quantity = cancel_quantity
            cancel_quantity = 0
        setattr(picklist, field_name, float(getattr(picklist, field_name)) - reduced_quantity)
        order_det.quantity = float(order_det.quantity) - reduced_quantity
        if order_det.quantity <= 0:
            order_det.status = 3
        order_det.save()
        if seller_order:
            seller_order.quantity = float(seller_order.quantity) - reduced_quantity
            if seller_order.quantity <= 0:
                seller_order.status = 0
            seller_order.save()
        if picklist.reserved_quantity <= 0 and not picklist.picked_quantity:
            picklist.status = 'cancelled'
        elif picklist.reserved_quantity <= 0:
            pick_status = 'picked'
            if 'batch' in picklist.status:
                pick_status = 'batch_picked'
            picklist.status = pick_status
        picklist.save()
        if field_name == 'picked_quantity':
            if picklist.stock:
                seller_id = order_dict['seller_order_dict']['seller_id']
                cancel_location = CancelledLocation.objects.filter(picklist_id=picklist.id,
                                                                   picklist__order__user=user.id,
                                                                   seller_id=seller_id, status=1)
                if not cancel_location:
                    CancelledLocation.objects.create(picklist_id=picklist.id, quantity=reduced_quantity,
                                                     location_id=picklist.stock.location_id,
                                                     creation_date=datetime.datetime.now(), status=1,
                                                     seller_id=seller_id)
                else:
                    cancel_location = cancel_location[0]
                    cancel_location.quantity = float(cancel_location.quantity) + reduced_quantity
                    cancel_location.save()
        picklist_locations = PicklistLocation.objects.filter(picklist_id=picklist.id, picklist__order__user=user.id,
                                                             status=1)
        for pick_location in picklist_locations:
            if not reduced_quantity:
                break
            if float(pick_location.quantity) <= reduced_quantity:
                reduced_quantity -= float(pick_location.quantity)
                pick_location.quantity = 0
                if not field_name == 'picked_quantity':
                    pick_location.reserved = float(pick_location.reserved) - reduced_quantity
            else:
                pick_location.quantity = float(pick_location.quantity) - reduced_quantity
                reduced_quantity = 0
                if not field_name == 'picked_quantity':
                    pick_location.reserved = 0
            if pick_location.quantity <= 0:
                pick_location.status = 0
            pick_location.save()
    return cancel_quantity


def update_order_cancel(orders_data, user='', company_name=''):
    NOW = datetime.datetime.now()
    insert_status = []
    try:
        update_data_list = []
        for key, order_dict in orders_data.iteritems():
            seller_parent_id = ''
            for swx in order_dict.get('swx_mappings', []):
                if swx['swx_type'] == 'seller_parent_item_id':
                    seller_parent_id = swx['swx_id']
                    break
            original_order_id = order_dict['order_details']['original_order_id']
            filter_params = {'user': user.id, 'original_order_id': original_order_id,
                             'sku_id': order_dict['order_details']['sku_id'],
                             'order_id': order_dict['order_details']['order_id'],
                             'order_code': order_dict['order_details']['order_code']}

            order_det = OrderDetail.objects.exclude(status=3).filter(**filter_params)
            insert_status = validate_lineitem_ids(order_dict['swx_mappings'], seller_parent_id, order_det,
                                                  insert_status=insert_status)
            if not order_det:
                for swx_mapping in order_dict['swx_mappings']:
                    insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': swx_mapping['swx_id'],
                                          'error': 'Invalid Order'})
            elif Picklist.objects.filter(order_id=order_det[0].id, order__user=user.id, status=2):
                for swx_mapping in order_dict['swx_mappings']:
                    insert_status.append({'parentLineitemId': seller_parent_id, 'lineitemId': swx_mapping['swx_id'],
                                          'error': 'Order Dispatched'})
            else:
                update_data_list.append({'order_det': order_det, 'order_dict': order_dict})

        if insert_status:
            return insert_status, ''
        for update_data in update_data_list:
            order_det = update_data['order_det']
            order_dict = update_data['order_dict']
            order_det = order_det[0]
            seller_order = None
            if order_dict.get('seller_order_dict', {}):
                seller_orders = SellerOrder.objects.filter(sor_id=order_dict['seller_order_dict']['sor_id'],
                                                           order_id=order_det.id)
                if seller_orders:
                    seller_order = seller_orders[0]
            if int(order_det.status) == 1:
                if float(order_det.quantity) <= float(order_dict['order_details']['quantity']):
                    order_det.status = 3
                    order_det.save()
                    if seller_order:
                        seller_order.status = 0
                        seller_order.save()
                else:
                    cancel_quantity = float(order_dict['order_details']['quantity'])
                    order_det.quantity = float(order_det.quantity) - cancel_quantity
                    if order_det.quantity <= 0:
                        order_det.status = 3
                    order_det.save()
                    if seller_order:
                        seller_order.quantity = seller_order.quantity - cancel_quantity
                        seller_order.save()

            else:
                picklists = Picklist.objects.filter(order_id=order_det.id, order__user=user.id)
                cancel_quantity = float(order_dict['order_details']['quantity'])
                for picklist in picklists:
                    if not cancel_quantity:
                        break
                    if picklist.reserved_quantity > 0:
                        cancel_quantity = update_cancelled_quantity(order_det, seller_order, picklist, cancel_quantity,
                                                                    order_dict,
                                                                    user, 'reserved_quantity')
                    if cancel_quantity and picklist.picked_quantity > 0:
                        cancel_quantity = update_cancelled_quantity(order_det, seller_order, picklist, cancel_quantity,
                                                                    order_dict, user, 'picked_quantity')
            if seller_order and order_dict['swx_mappings']:
                update_lineitem_ids(seller_order, order_dict['swx_mappings'])
            save_order_tracking_data(order_det, quantity=order_dict['order_details'].get('quantity', 0),
                                     status='cancelled', imei='')
        return insert_status, "Success"
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        result_data = []
        log.info('Update Order Cancellation API failed for %s and params are %s and error statement is %s' % \
                 (str(user.username), str(orders_data), str(e)))
        return ['Internal Server Error'], ''


def update_order_returns(orders_data, user='', company_name=''):
    NOW = datetime.datetime.now()
    insert_status = []
    try:
        all_data_list = []
        for key, order_dict in orders_data.iteritems():
            original_order_id = order_dict['order_details']['original_order_id']
            filter_params = {'user': user.id, 'original_order_id': original_order_id,
                             'sku_id': order_dict['order_details']['sku_id'],
                             'order_id': order_dict['order_details']['order_id'],
                             'order_code': order_dict['order_details']['order_code']}
            order_objs = OrderDetail.objects.filter(**filter_params)
            seller_parent_item_id = ''
            for swx in order_dict.get('swx_mappings', []):
                if swx['swx_type'] == 'seller_parent_item_id':
                    seller_parent_item_id = swx['swx_id']
                    break
            if not order_objs:
                insert_status.append({'parentLineitemId': seller_parent_item_id, 'error': 'Order Does not exists'})
                continue
            order_obj = order_objs[0]
            if int(order_obj.status) == 4:
                insert_status.append({'parentLineitemId': seller_parent_item_id, 'error': 'Order Returned already'})
            return_total = OrderTracking.objects.filter(order_id=order_obj.id, order__user=user.id,
                                                        status='returned').aggregate(Sum('quantity'))['quantity__sum']
            if not return_total:
                return_total = 0
            if (float(order_obj.quantity) - float(return_total)) - float(order_dict['order_details']['quantity']) < 0:
                insert_status.append(
                    {'parentLineitemId': seller_parent_item_id, 'error': 'Return quantity exceeding order quantity'})
                continue
            seller_order = SellerOrder.objects.filter(order_id=order_obj.id,
                                                      sor_id=order_dict['seller_order_dict']['sor_id'])
            if not seller_order:
                insert_status.append(
                    {'parentLineitemId': seller_parent_item_id, 'error': 'Return quantity exceeding order quantity'})
                continue
            if not insert_status:
                returns_dict = {'quantity': order_dict['order_details']['quantity'],
                                'return_date': datetime.datetime.now(),
                                'sku_id': order_dict['order_details']['sku_id'], 'seller_order_id': seller_order[0].id,
                                'creation_date': datetime.datetime.now(), 'status': 1, 'order_id': order_obj.id,
                                'order_obj': order_obj
                                }
                all_data_list.append(returns_dict)

        if insert_status:
            return insert_status, ''
        for data_dict in all_data_list:
            order_obj = data_dict['order_obj']
            save_order_tracking_data(order_obj, quantity=data_dict['quantity'], status='returned', imei='')
            del data_dict['order_obj']
            tot_sum = OrderTracking.objects.filter(order_id=order_obj.id, order__user=user.id,
                                                   status='returned').aggregate(Sum('quantity'))['quantity__sum']
            if not tot_sum:
                tot_sum = 0
            if float(order_obj.quantity) <= tot_sum:
                order_obj.status = 4
                order_obj.save()
            order_return = OrderReturns(**data_dict)
            order_return.save()
            order_return.return_id = 'MN%s' % order_return.id
            order_return.save()

        return insert_status, "Success"
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        result_data = []
        log.info('Update Order Returns API failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(orders_data), str(e)))


def get_order(orig_order_id, user):
    customer_data, summary = {}, {}
    sku_data = []
    total_quantity, total_amount, total_gst, total_mrp = [0]*4
    customer_master = ''

    order_detail = OrderDetail.objects.filter(original_order_id = orig_order_id,\
                                              user = user.id)
    if order_detail:
        for order in order_detail:
            order_summary = CustomerOrderSummary.objects.get(order_id = order.id)
            sku_master = SKUMaster.objects.get(id = order.sku_id)
            selling_price = order.unit_price if order.unit_price != 0\
                                             else float(order.invoice_amount)/float(order.quantity)
            sku_data.append({'name': order.title,
                             'quantity': order.quantity,
                             'sku_code': order.sku.sku_code,
                             'cgst_tax': order_summary.cgst_tax,
                             'sgst_tax': order_summary.sgst_tax,
                             'igst_tax': order_summary.igst_tax,
                             'utgst_tax': order_summary.utgst_tax,
                             'discount': order_summary.discount,
                             'price': order.invoice_amount,
                             'unit_price': order.unit_price,
                             'selling_price': selling_price,
                             'id': order.id})
            total_quantity += int(order.quantity)
            total_gst += order_summary.cgst_tax + order_summary.sgst_tax + order_summary.igst_tax +\
                         order_summary.utgst_tax
            #total_amount += int(order.invoice_amount)
            tot = ((order.unit_price * order.quantity) - order_summary.discount)
            total_amount += tot + tot * (order_summary.cgst_tax + order_summary.sgst_tax)/100
            tot = ((sku_master.mrp * order.quantity) - order_summary.discount)
            total_mrp += tot + tot * (order_summary.cgst_tax + order_summary.sgst_tax)/100
        order = order_detail[0]
        order_date = order.creation_date.strftime("%Y-%m-%d %H:%M:%S")#get_local_date(user, order.creation_date)
        shipment_date = order.shipment_date.strftime("%d-%b-%Y")
        if order.customer_id:
            gen_obj = GenericOrderDetailMapping.objects.filter(orderdetail_id=order.id)
            if gen_obj:
                cm_id = gen_obj[0].customer_id
                customer_master = CustomerMaster.objects.filter(id=cm_id)
                if customer_master:
                    if customer_master[0].is_distributor == False:
                        log.info("user:%s" %(str(user.id)))
                        wh_customer_map = WarehouseCustomerMapping.objects.filter(warehouse_id=customer_master[0].user)
                        if wh_customer_map:
                            customer_master = [wh_customer_map[0].customer]
                        #customer_master = CustomerMaster.objects.filter(customer_id = order.customer_id,\
                                                        #name = order.customer_name,\
                                                        #user = user.id)
        customer_master = customer_master[0] if customer_master else None
        customer_data = {'Name': customer_master.name if customer_master else order.customer_name,
                         'Number': customer_master.phone_number if customer_master else order.telephone,
                         'ID': customer_master.id if customer_master else order.customer_id,
                         'address': customer_master.address if customer_master else order.address,
                         'zip': customer_master.pincode if customer_master else order.pin_code,
                         'city': customer_master.city if customer_master else order.city,
                         'state': customer_master.state if customer_master else order.state,
                         'Email': customer_master.email_id if customer_master else order.email_id}
        return {'data':
                       {'order_id': order.original_order_id if order.original_order_id\
                                    else '%s%s' % (order.order_code, order.order_id),
                       'order_date': order_date,
                       'total_quantity': total_quantity,
                       'total_amount': total_amount,
                       'total_mrp': total_mrp,
                       'total_gst': total_gst,
                       'customer_data': customer_data,
                       'sku_data': sku_data,
                       'remarks': order.remarks,
                       'shipment_date': shipment_date},
                'status': 'success'}
    else:
        return {'data':{}, 'status': 'failure'}


def update_error_message(failed_status, error_code, error_message, field_value, field_key='OrderId'):
    error_group_key = '%s:%s' % (field_key, field_value)
    failed_status.setdefault(error_group_key, {field_key: field_value, "errors": []})
    failed_status[error_group_key]["errors"].append(
        {
            "status": error_code,
            "message": error_message
        }
    )


def validate_seller_orders_format(orders, user='', company_name='', is_cancelled=False):
    order_status_dict = {'NEW': 1, 'RETURN': 3, 'CANCEL': 4}
    NOW = datetime.datetime.now()
    insert_status = []
    final_data_dict = OrderedDict()
    token_user = user
    sister_whs1 = list(get_sister_warehouse(user).values_list('user__username', flat=True))
    sister_whs1.append(token_user.username)
    sister_whs = []
    for sister_wh1 in sister_whs1:
        sister_whs.append(str(sister_wh1).lower())
    try:
        seller_master_dict, valid_order, query_params = {}, {}, {}
        failed_status = OrderedDict()
        if not orders:
            orders = {}
        if isinstance(orders, dict):
            orders = [orders]
        for ind, order in enumerate(orders):
            order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
            channel_name = order['source']
            order_details = copy.deepcopy(ORDER_DATA)
            data = order
            original_order_id = order['order_id']
            order_code = ''.join(re.findall('\D+', original_order_id))
            order_id = ''.join(re.findall('\d+', original_order_id))
            filter_params = {'user': user.id, 'order_id': order_id}
            filter_params1 = {'user': user.id, 'original_order_id': original_order_id}
            try:
                creation_date = datetime.datetime.strptime(order['order_date'], '%Y-%m-%d %H:%M:%S')
            except:
                update_error_message(failed_status, 5024, 'Invalid Order Date Format', original_order_id)
            try:
                shipment_date = datetime.datetime.strptime(order['shipment_date'], '%Y-%m-%d %H:%M:%S')
            except:
                update_error_message(failed_status, 5024, 'Invalid Shipment Date Format', original_order_id)
            order_status = order['order_status']
            if order_status not in order_status_dict.keys():
                error_message = 'Invalid Order Status - Should be ' + ','.join(order_status_dict.keys())
                update_error_message(failed_status, 5024, error_message, original_order_id)
                break
            if 'warehouse' not in order.keys():
                error_message = 'warehouse key missing'
                update_error_message(failed_status, 5021, error_message, original_order_id)
            else:
                warehouse = order['warehouse']
                if warehouse.lower() in sister_whs:
                    user = User.objects.get(username=warehouse)
                else:
                    error_message = 'Invalid Warehouse Name'
                    update_error_message(failed_status, 5020, error_message, original_order_id)

            if order.has_key('billing_address'):
                if order['billing_address'].get('customer_id', 0):
                    customer_id = order['billing_address']['customer_id']
                    try:
                        customer_master = CustomerMaster.objects.filter(user=user.id, customer_id=customer_id)
                        if customer_master:
                            order_details['customer_id'] = order['billing_address'].get('customer_id', 0)
                        else:
                            update_error_message(failed_status, 5024, 'Invalid Customer ID', original_order_id)
                    except:
                        update_error_message(failed_status, 5024, 'Customer ID should be Number',
                                             original_order_id)
                order_details['customer_name'] = order['billing_address'].get('name', '')
                order_details['telephone'] = order['billing_address'].get('phone_number', '')
                order_details['city'] = order['billing_address'].get('city', '')
                order_details['address'] = str(order['billing_address'].get('address', '')).encode('ascii', 'ignore')[:255]
                try:
                    order_details['pin_code'] = int(order['billing_address'].get('pincode', ''))
                except:
                    pass

            if not order.get('sub_orders', []):
                update_error_message(failed_status, 5024, 'Sub Orders Missing', original_order_id)
            if order_code:
                filter_params['order_code'] = order_code
            valid_order['user'] = user.id
            valid_order['marketplace'] = channel_name
            valid_order['original_order_id'] = original_order_id
            if order_details['status'] in [1]:
                valid_order['status__in'] = [1, 2, 3, 4, 5]
            elif order_details['status'] in [3, 4]:
                valid_order['status__in'] = [3, 4]
            order_detail_present = OrderDetail.objects.filter(**valid_order)
            if order_detail_present.exists():
                if int(order_detail_present[0].status) == 1:
                    error_code = "5001"
                    message = 'Duplicate Order, ignored at Stockone'
                elif int(order_detail_present[0].status) == 3:
                    error_code = "5002"
                    message = 'Order is already returned at Stockone'
                elif int(order_detail_present[0].status) == 4:
                    error_code = "5003"
                    message = 'Order is already cancelled at Stockone'
                update_error_message(failed_status, error_code, message, original_order_id)
            if order.has_key('extra_fields'):
                extra_fields_data = OrderedDict()
                extra_attributes = order['extra_fields']
                for key in extra_attributes:
                    extra_fields_data[key] = extra_attributes[key]
                if extra_fields_data:
                    create_extra_fields_for_order(original_order_id, extra_fields_data, user)
            for sub_order in order['sub_orders']:
                seller_order_dict = copy.deepcopy(SELLER_ORDER_FIELDS)
                seller_id = sub_order.get('seller_id', '')
                if not seller_id or not isinstance(seller_id, int):
                    update_error_message(failed_status, 5023, 'Invalid Seller ID', original_order_id)
                    continue
                seller_master = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
                if not seller_master.exists():
                    update_error_message(failed_status, 5023, 'Seller Id not found', original_order_id)
                    continue
                seller_master_id = seller_master[0].id
                seller_master = seller_master[0]
                sor_id = sub_order.get('seller_order_id', '')
                if not sor_id:
                    sor_id = '%s_%s' % (str(seller_id), str(original_order_id))
                seller_order = SellerOrder.objects.filter(order__original_order_id=original_order_id, sor_id=sor_id,
                                           order__user=user.id)
                if seller_order.exists():
                    update_error_message(failed_status, 5022, 'SOR Id exists already', original_order_id)
                sku_items = sub_order['items']
                sku_obj = None
                shipping_amt = 0
                for sku_item in sku_items:
                    failed_sku_status = []
                    sku_code = sku_item['sku']
                    sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                    if sku_master.exists():
                        filter_params['sku_id'] = sku_master[0].id
                        filter_params1['sku_id'] = sku_master[0].id
                    else:
                        update_error_message(failed_status, 5020, "SKU Not found in Stockone", original_order_id)
                        continue

                    if sku_master:
                        sku_obj = sku_master[0]
                        grouping_key = str(original_order_id) + '<<>>' + str(sku_master[0].sku_code)
                        order_det = OrderDetail.objects.filter(**filter_params)
                        order_det1 = OrderDetail.objects.filter(**filter_params1)

                        invoice_amount = 0
                        unit_price = sku_item['unit_price']
                        try:
                            mrp = float(sku_item['mrp'])
                        except:
                            mrp = 0
                        if mrp:
                            mrp = float('%.2f' % mrp)
                        if not order_det:
                            order_det = order_det1

                        order_create = True

                        if order_create:
                            order_details['original_order_id'] = original_order_id
                            order_details['order_id'] = order_id
                            order_details['order_code'] = order_code

                            order_details['sku_id'] = sku_master[0].id
                            try:
                                order_details['title'] = unicodedata.normalize('NFKD', sku_item['name']).encode('ascii', 'ignore')
                            except:
                                order_details['title'] = sku_obj.sku_desc
                            order_details['user'] = user.id
                            order_details['quantity'] = sku_item['quantity']
                            order_details['shipment_date'] = shipment_date
                            order_details['marketplace'] = channel_name
                            order_details['invoice_amount'] = float(invoice_amount)
                            order_details['unit_price'] = float(unit_price)
                            order_details['creation_date'] = creation_date
                            try:
                                invoice_amount = float(sku_item['quantity']) * float(unit_price)
                            except:
                                invoice_amount = 0

                            final_data_dict = check_and_add_dict(grouping_key, 'order_details', order_details,
                                                                 final_data_dict=final_data_dict)
                        if order_create:
                            order_summary_dict['mrp'] = mrp
                            order_summary_dict['cgst_tax'] = 0
                            order_summary_dict['sgst_tax'] = 0
                            order_summary_dict['igst_tax'] = 0
                            order_summary_dict['utgst_tax'] = 0
                            order_summary_dict['cess_tax'] = 0
                            if sku_item.get('tax_percent', {}):
                                # order_summary_dict['cgst_tax'] = float(sku_item['tax_percent'].get('CGST', 0))
                                # order_summary_dict['sgst_tax'] = float(sku_item['tax_percent'].get('SGST', 0))
                                # order_summary_dict['igst_tax'] = float(sku_item['tax_percent'].get('IGST', 0))
                                # order_summary_dict['utgst_tax'] = float(sku_item['tax_percent'].get('UTGST', 0))
                                # order_summary_dict['cess_tax'] = float(sku_item['tax_percent'].get('CESS', 0))
                                try:
                                    order_summary_dict['cgst_tax'] = float(sku_item['tax_percent'].get('CGST', 0))
                                except:
                                    order_summary_dict['cgst_tax'] = 0
                                try:
                                    order_summary_dict['sgst_tax'] = float(sku_item['tax_percent'].get('SGST', 0))
                                except:
                                    order_summary_dict['sgst_tax'] = 0
                                try:
                                    order_summary_dict['igst_tax'] = float(sku_item['tax_percent'].get('IGST', 0))
                                except:
                                    order_summary_dict['igst_tax'] = 0
                                try:
                                    order_summary_dict['utgst_tax'] = float(sku_item['tax_percent'].get('UTGST', 0))
                                except:
                                    order_summary_dict['utgst_tax'] = 0
                                try:
                                    order_summary_dict['cess_tax'] = float(sku_item['tax_percent'].get('CESS', 0))
                                except:
                                    order_summary_dict['cess_tax'] = 0
                            order_summary_dict['discount'] = 0
                            if sku_item.get('discount_amount', 0):
                                try:
                                    order_summary_dict['discount'] = float(sku_item['discount_amount'])
                                except:
                                    order_summary_dict['discount'] = 0
                            if order_summary_dict['discount']:
                                invoice_amount -= order_summary_dict['discount']
                            taxes = order_summary_dict['cgst_tax'] + order_summary_dict['sgst_tax'] + \
                                    order_summary_dict['igst_tax'] + order_summary_dict['utgst_tax'] + \
                                    order_summary_dict['cess_tax']
                            if taxes:
                                invoice_amount += (invoice_amount/100) * taxes
                            order_summary_dict['consignee'] = str(order_details.get('address', '')).encode('ascii', 'ignore')[:255]
                            #order_summary_dict['invoice_date'] = order_details['creation_date']
                            order_summary_dict['inter_state'] = 0
                            if order_summary_dict['igst_tax']:
                                order_summary_dict['inter_state'] = 1
                            final_data_dict = check_and_add_dict(grouping_key, 'order_summary_dict',
                                                                 order_summary_dict, final_data_dict=final_data_dict)
                        seller_order_dict['seller_id'] = seller_master_id
                        seller_order_dict['sor_id'] = sor_id
                        seller_order_dict['order_status'] = 'PROCESSED'
                        seller_order_dict['quantity'] = sku_item['quantity']
                        final_data_dict = check_and_add_dict(grouping_key, 'seller_order_dict', seller_order_dict,
                                                            final_data_dict=final_data_dict)
                        try:
                            sku_shipping = float(sku_item.get('shiping_charge', 0))
                        except:
                            sku_shipping = 0
                        shipping_amt += sku_shipping
                        final_data_dict[grouping_key]['order_details']['invoice_amount'] = invoice_amount

                final_data_dict[grouping_key]['shipping_charge'] = shipping_amt
                final_data_dict[grouping_key]['status_type'] = order_status
                final_data_dict[grouping_key]['sku_obj'] = sku_obj
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update MP Order API failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(orders), str(e)))
    return insert_status, failed_status.values(), final_data_dict

def check_and_update_payment(payment_info, order_details, user):
    NOW = datetime.datetime.now()
    original_order_id = order_details[0].original_order_id
    payment_summary = PaymentSummary.objects.filter(order__user=user.id, order__original_order_id = original_order_id)
    payment_date = payment_info.get('payment_date', '')
    if payment_date:
        payment_date = parser.parse(payment_date)
    else:
        payment_date = NOW
    transaction_id = payment_info.get('transaction_id', '')
    paid_amount = payment_info.get('paid_amount',  0)
    method_of_payment = payment_info.get('method', '')
    payment_mode = payment_info.get('payment_mode', '')
    payment_dict = {'method_of_payment':method_of_payment, 'payment_date':payment_date,
                    'paid_amount':paid_amount, 'payment_mode':payment_mode,'transaction_id':transaction_id}
    payment_dict['aux_info'] = json.dumps(payment_info)
    if payment_summary.exists():
        payment_ids = list(payment_summary.values_list('payment_info', flat=True))
        if payment_ids:
            payment_obj = PaymentInfo.objects.filter(id__in=payment_ids)
            payment_dict['payment_mode'] = payment_info.get('payment_mode', payment_obj[0].payment_mode)
            payment_date = payment_info.get('payment_date', '')
            if payment_date:
                payment_date = parser.parse(payment_date)
                payment_dict['payment_date'] = payment_date
            payment_dict['transaction_id'] = payment_info.get('transaction_id',  payment_obj[0].transaction_id)
            payment_dict['paid_amount'] = payment_info.get('paid_amount',  payment_obj[0].paid_amount)
            payment_dict['method_of_payment'] = payment_info.get('method',  payment_obj[0].method_of_payment)
            payment_obj.update(**payment_dict)
    else:
        for order in order_details:
            payment_id = get_incremental(user, "payment_summary", 1)
            payment = PaymentInfo.objects.create(**payment_dict)
            PaymentSummary.objects.create(order_id=order.id, payment_id=payment_id, payment_info=payment)

def cancel_order(order_details, original_order_id, user):
    from rest_api.views.common import order_cancel_functionality
    admin_user = get_admin(user)
    order_detail_ids = list(order_details.values_list('id', flat=True))
    IntermediateOrders.objects.filter(order__id__in=order_detail_ids).update(status = 3)
    # if order_detail_ids and not picklists:
    order_cancel_functionality(order_detail_ids, admin_user=admin_user)
        # for order_detail_id in order_detail_ids:
        #     order_obj = OrderDetail.objects.get(id=order_detail_id)
        #     order_obj.cancelled_quantity = order_obj.cancelled_quantity + order_obj.quantity
        #     if order_obj.original_quantity == order_obj.cancelled_quantity:
        #         order_obj.status = 3
        #     elif order_obj.shipmentinfo_set.filter().exists() and not order_obj.picklist_set.filter(reserved_quantity__gt=0).exists():
        #         order_obj.status = 2
        #     else:
        #         order_obj.status = 0
        #     order_obj.save()
        #     if admin_user:
        #         OrderFields.objects.filter(user=admin_user.id, original_order_id=original_order_id).delete()


def return_order(order_details, original_order_id, request, user, return_quantity=0, failed_status=''):
    from rest_api.views.inbound import create_return_order, save_return_locations, returns_order_tracking
    credit_note_number = ''
    admin_user = get_admin(user)
    order_detail_ids = order_details.values_list('id', flat=True)
    seller_orders = list(
        SellerOrder.objects.filter(order_id__in=order_detail_ids, order_status='DELIVERY_RESCHEDULED',
                                   status=1). \
        values_list('order_id', flat=True))
    order_detail_ids = list(order_detail_ids)
    #IntermediateOrders.objects.filter(order__id__in=order_detail_ids).update(status = 3)
    picklists = Picklist.objects.filter(order_id__in=order_detail_ids, order__user=user.id)
    if seller_orders:
        OrderDetail.objects.filter(id__in=seller_orders).update(status=5)
        SellerOrder.objects.filter(order_id__in=seller_orders).update(status=0, order_status='PROCESSED')
        order_detail_ids = list(set(order_detail_ids) - set(seller_orders))
    final_data = []
    for order in order_details:
        #order_quantity = order.original_quantity - order.cancelled_quantity
        order_returned = OrderTracking.objects.filter(order_id=order.id, status='returned').aggregate(Sum('quantity'))['quantity__sum']
        if not order_returned:
            order_returned = 0
        if get_permission(user, 'add_shipmentinfo'):
            shipping_qty = ShipmentInfo.objects.filter(order_id=order.id).\
                                                aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
        else:
            shipping_qty = picklists.filter(order_id=order.id).aggregate(Sum('picked_quantity'))['picked_quantity__sum']
        if not return_quantity:
            return_quantity = shipping_qty - order_returned
        if not return_quantity:
            continue
        if return_quantity > (shipping_qty - order_returned):
            error_message = "Return Quantity Exceeding the Shipping quantity for SKU %s" % str(order.sku.sku_code)
            update_error_message(failed_status, 5024, error_message, original_order_id)
        final_data.append({"order": order, "return_quantity": return_quantity, "order_returned": order_returned})
    updated_records = 0
    if not failed_status:
        for order_data in final_data:
            return_quantity = order_data['return_quantity']
            order = order_data['order']
            order_quantity = order.original_quantity - order.cancelled_quantity
            if str(order.status) == '4' or order_returned == order_quantity:
                continue
            if (order_returned + return_quantity) >= order_quantity:
                order.status = 4
            order.save()
            data_dict = {'sku_code': order.sku.sku_code, 'return': return_quantity, 'damaged': 0, 'order_imei_id': '',
                         'order_id': order.original_order_id, 'order_detail_id': order.id}
            data_dict['id'], status, seller_order_ids, credit_note_number = create_return_order(data_dict, user.id,
                                                                                                credit_note_number)
            order_returns = OrderReturns.objects.filter(id=data_dict['id'])
            if not order_returns:
                return HttpResponse("Failed")
            order_returns = order_returns[0]
            save_return_locations([order_returns], [], 0, request, user, locations='')
            returns_order_tracking(order_returns, user, return_quantity, 'returned', imei='', invoice_no='')
            updated_records += 1
    if not updated_records:
        error_message = "Record not found or returned already"
        update_error_message(failed_status, 5024, error_message, original_order_id)
    return failed_status


def validate_update_order(request_data, user='', company_name=''):
    search_params = {'user': user.id}
    sister_whs = []
    original_order_id = ''
    status = ''
    failed_status = OrderedDict()
    sister_whs1 = list(get_sister_warehouse(user).values_list('user__username', flat=True))
    for sister_wh1 in sister_whs1:
        sister_whs.append(str(sister_wh1).lower())
    if request_data.has_key('order_id'):
        original_order_id = str(request_data['order_id'])
    else:
        error_message = 'Order ID required'
        update_error_message(failed_status, 5024, error_message, original_order_id)
    if request_data.has_key('warehouse'):
        warehouse = request_data['warehouse']
        sister_whs.append(user.username)
        if warehouse.lower() in sister_whs:
            user = User.objects.get(username=warehouse)
        else:
            error_message = 'Invalid Warehouse Name'
            update_error_message(failed_status, 5024, error_message, original_order_id)
    search_params = {'user': user.id}
    if request_data.has_key('sku_code'):
        search_params['sku__sku_code'] = request_data['sku_code']
    if request_data.has_key('status'):
        status = request_data['status'].lower()
    return_quantity = request_data.get('return_quantity', 0)


    # else:
    #     error_message = 'Please mention status'
    #     update_error_message(failed_status, 5024, error_message, original_order_id)
    if not failed_status:
        order_details = OrderDetail.objects.filter(original_order_id=original_order_id, **search_params)
        if order_details:
            if request_data.has_key('payment_status'):
                payment_status = request_data.get('payment_status')
                if payment_status.lower() == 'paid':
                    for order in order_details:
                        invoice_amount = order.invoice_amount
                        order.payment_received = invoice_amount
                        order.save()
            if request_data.has_key('payment_info'):
                payment_info = request_data['payment_info']
                check_and_update_payment(payment_info, order_details, user)
            if status == 'cancel':
                cancel_order(order_details, original_order_id,user)
            elif status == 'return':
                failed_status = return_order(order_details, original_order_id, request_data, user,
                                       return_quantity=return_quantity, failed_status=failed_status)
        else:
            error_message = 'Please check the data'
            update_error_message(failed_status, 5024, error_message, original_order_id)
    return failed_status.values()

def validate_create_orders(orders, user='', company_name='', is_cancelled=False):
    order_status_dict = {'NEW': 1, 'RETURN': 3, 'CANCEL': 4}
    NOW = datetime.datetime.now()
    insert_status = []
    final_data_dict = OrderedDict()
    payment_dict = OrderedDict()
    sister_whs1 = list(get_sister_warehouse(user).values_list('user__username', flat=True))
    sister_whs1.append(user.username)
    sister_whs = []
    inter_state = 0
    payment_info = {}
    cgst_tax, igst_tax, sgst_tax = 0,0,0
    for sister_wh1 in sister_whs1:
        sister_whs.append(str(sister_wh1).lower())
    customer_name, customer_city, customer_telephone, customer_address, customer_pincode, shipping_address, customer_email = '','','','',0,'',''
    try:
        seller_master_dict, valid_order, query_params = {}, {}, {}
        failed_status = OrderedDict()
        if not orders:
            orders = {}
        if isinstance(orders, dict):
            orders = [orders]
        for ind, order in enumerate(orders):
            try:
                if order.has_key('order_date'):
                    creation_date = parser.parse(order['order_date'])
                else:
                    creation_date = NOW
            except:
                update_error_message(failed_status, 5024, 'Invalid Order Date Format', '')
            try:
                if order.has_key('shipment_date'):
                    shipment_date = parser.parse(order['shipment_date'])
                else:
                    shipment_date = NOW
            except:
                update_error_message(failed_status, 5024, 'Invalid Shipment Date Format', '')

            if order.has_key('warehouse'):
                warehouse = order['warehouse']
                if warehouse.lower() in sister_whs:
                    user = User.objects.get(username=warehouse)
                else:
                    error_message = 'Invalid Warehouse Name'
                    update_error_message(failed_status, 5024, error_message, '')

            order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
            channel_name = order.get('source', 'offline')
            order_details = copy.deepcopy(ORDER_DATA)
            data = order
            if order.has_key('order_reference'):
                order_reference = str(order['order_reference'])
                order_details['order_reference'] = order_reference

            if not order.get('order_id', ''):
                generate_order_id = get_order_id(user.id)
                order_code = get_order_prefix(user.id)
                order['order_id'] = order_code+str(generate_order_id)
            original_order_id = str(order['order_id'])
            order_code = ''.join(re.findall('\D+', original_order_id))
            order_id = ''.join(re.findall('\d+', original_order_id))
            filter_params = {'user': user.id, 'order_id': order_id}
            filter_params1 = {'user': user.id, 'original_order_id': original_order_id}

            order_status = order.get('order_status', 'NEW')
            if order_status not in order_status_dict.keys():
                error_message = 'Invalid Order Status - Should be ' + ','.join(order_status_dict.keys())
                update_error_message(failed_status, 5024, error_message, original_order_id)
                break

            if order.has_key('customer_id'):
                order_details['customer_id'] = str(order.get('customer_id', 0))
                if order_details['customer_id']:
                    customer = order_details['customer_id'].split('_')
                    order_details['customer_id'] = customer[-1]
                    try:
                        customer_master = CustomerMaster.objects.filter(user=user.id, customer_id=order_details['customer_id'])
                        if customer_master:
                            customer_name = customer_master[0].name
                            customer_telephone = customer_master[0].phone_number
                            customer_email= customer_master[0].email_id
                            customer_city = customer_master[0].city
                            customer_address = customer_master[0].address
                            customer_tax_type = customer_master[0].tax_type
                            if customer_tax_type == "inter_state":
                                inter_state = 1
                            try:
                                customer_pincode = int(customer_master[0].pincode)
                            except:
                                customer_pincode = 0
                    except:
                        customer_master = []
                    if not customer_master:
                        error_message = 'Invalid Customer ID %s' % str(order_details['customer_id'])
                        update_error_message(failed_status, 5024, error_message, original_order_id)
                        break
                order_details['customer_name'] =  customer_name
                order_details['telephone'] = customer_telephone
                order_details['email_id'] = customer_email
                order_details['city'] = customer_city
                order_details['address'] = customer_address
                order_details['pin_code'] = customer_pincode
            if order.has_key('shipping_address'):
                shipping_address = order['shipping_address'].get('name','') + '\n' + order['shipping_address'].get('address','')
                if order['shipping_address'].get('city'):
                    shipping_address += ("\n" + order['shipping_address'].get('city'))
                if order['shipping_address'].get('state'):
                    shipping_address += (", " + order['shipping_address'].get('state'))
                if order['shipping_address'].get('country'):
                    shipping_address += (", " + order['shipping_address'].get('country'))
                if order['shipping_address'].get('pincode'):
                    shipping_address += ("\nPincode: " + str(order['shipping_address'].get('pincode')))
                if order['shipping_address'].get('email'):
                    shipping_address += ("\nEmail: " + order['shipping_address'].get('email'))
                if order['shipping_address'].get('phone_number'):
                    shipping_address += ("\nPhone.No: " + str(order['shipping_address'].get('phone_number')))

            if order_code:
                filter_params['order_code'] = order_code
            sku_items = order['items']
            valid_order['user'] = user.id
            valid_order['marketplace'] = channel_name
            valid_order['original_order_id'] = original_order_id
            if order_details['status'] in [1]:
                valid_order['status__in'] = [1, 2, 3, 4, 5]
            elif order_details['status'] in [3, 4]:
                valid_order['status__in'] = [3, 4]
            order_detail_present = OrderDetail.objects.filter(**valid_order)
            if order_detail_present:
                if int(order_detail_present[0].status) == 1:
                    error_code = "5001"
                    message = 'Duplicate Order, ignored at Stockone'
                elif int(order_detail_present[0].status) == 3:
                    error_code = "5002"
                    message = 'Order is already returned at Stockone'
                elif int(order_detail_present[0].status) == 4:
                    error_code = "5003"
                    message = 'Order is already cancelled at Stockone'
                update_error_message(failed_status, error_code, message, original_order_id)
                break
            if order.has_key('payment_info'):
                payment_info['payment_mode'] = order['payment_info'].get('payment_mode', '')
                payment_info['transaction_id'] = order['payment_info'].get('transaction_id', '')
                payment_info['paid_amount'] = order['payment_info'].get('paid_amount', 0)
                payment_info['payment_date'] = order['payment_info'].get('payment_date', '')
                payment_info['method_of_payment'] = order['payment_info'].get('method', '')
                payment_info['aux_info'] = json.dumps(order['payment_info'])
                try:
                    if payment_info['payment_date']:
                        payment_info['payment_date'] = parser.parse(payment_info['payment_date'])
                    else:
                        payment_info['payment_date'] = NOW
                except:
                    update_error_message(failed_status, 5024, 'Invalid Payment Date Format', '')
                grouping_key = str(original_order_id)
                payment_dict = check_and_add_dict(grouping_key, 'payment_info',
                                                             payment_info, final_data_dict=payment_dict)
            for sku_item in sku_items:
                failed_sku_status = []
                sku_code = sku_item['sku']
                sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                if sku_master:
                    filter_params['sku_id'] = sku_master[0].id
                    filter_params1['sku_id'] = sku_master[0].id
                else:
                    update_error_message(failed_status, 5020, "SKU Not found in Stockone", original_order_id)
                    continue

                if sku_master:
                    grouping_key = str(original_order_id) + '<<>>' + str(sku_master[0].sku_code)
                    order_det = OrderDetail.objects.filter(**filter_params)
                    order_det1 = OrderDetail.objects.filter(**filter_params1)
                    tax_obj = TaxMaster.objects.filter(product_type=sku_master[0].product_type, user=user.id,
                                                        max_amt__gte=sku_master[0].price, min_amt__lte=sku_master[0].price, inter_state=inter_state)

                    invoice_amount = 0
                    unit_price = sku_item.get('unit_price', '')
                    discount_amount = sku_item.get('discount_amount', '')
                    if discount_amount:
                        try:
                            order_summary_dict['discount'] = float(discount_amount)
                        except:
                            order_summary_dict['discount'] = 0
                    if unit_price == '':
                        unit_price, discount, price_bands_list = get_order_sku_price(customer_master, sku_master[0], user)
                        if discount_amount == '':
                            if sku_item.has_key('quantity'):
                                order_summary_dict['discount'] = ((float(sku_item['quantity']) * unit_price)/100) * discount
                            else:
                                update_error_message(failed_status, 5020, "quantity Field missing", original_order_id)
                                break
                    if not order_det:
                        order_det = order_det1

                    order_create = True
                    if tax_obj:
                        cgst_tax = float(tax_obj[0].cgst_tax)
                        sgst_tax = float(tax_obj[0].sgst_tax)
                        igst_tax = float(tax_obj[0].igst_tax)

                    if order_create:
                        order_details['original_order_id'] = original_order_id
                        order_details['order_id'] = order_id
                        order_details['order_code'] = order_code

                        order_details['sku_id'] = sku_master[0].id
                        order_details['title'] = sku_item.get('name', sku_master[0].sku_desc)
                        order_details['user'] = user.id
                        if sku_item.has_key('quantity'):
                            order_details['quantity'] = sku_item['quantity']
                        else:
                            update_error_message(failed_status, 5020, "quantity Field missing", original_order_id)
                            break
                        order_details['shipment_date'] = shipment_date
                        order_details['marketplace'] = channel_name
                        order_details['invoice_amount'] = float(invoice_amount)
                        order_details['unit_price'] = float(unit_price)
                        order_details['creation_date'] = creation_date
                        tax = cgst_tax + sgst_tax
                        if not tax and igst_tax:
                            tax = igst_tax
                        if order_create and not invoice_amount:
                            amt = (float(order_details['quantity']) * order_details['unit_price']) -\
                                  order_summary_dict['discount']
                            order_details['invoice_amount'] = amt + ((amt/100)*tax)

                        if order.has_key('payment_status'):
                            if order['payment_status'].lower() == 'paid':
                                order_details['payment_received'] = order_details['invoice_amount']
                        final_data_dict = check_and_add_dict(grouping_key, 'order_details', order_details,
                                                             final_data_dict=final_data_dict)
                    if not failed_status and not insert_status:
                        order_summary_dict['cgst_tax'] = cgst_tax
                        order_summary_dict['sgst_tax'] = sgst_tax
                        order_summary_dict['igst_tax'] = igst_tax
                        order_summary_dict['utgst_tax'] = 0
                        if shipping_address:
                            order_summary_dict['consignee'] = shipping_address
                        order_summary_dict['invoice_date'] = order_details['creation_date']
                        order_summary_dict['inter_state'] = inter_state
                        order_summary_dict['mrp'] = sku_master[0].mrp
                        final_data_dict = check_and_add_dict(grouping_key, 'order_summary_dict',
                                                             order_summary_dict, final_data_dict=final_data_dict)

                if len(failed_sku_status):
                    failed_status = {
                        "OrderId": original_order_id,
                        "Result": {
                            "Errors": failed_sku_status
                        }
                    }
                    break
                final_data_dict[grouping_key]['status_type'] = order_status
                if order.has_key('payment_status'):
                    final_data_dict[grouping_key]['payment_status'] = order['payment_status'].lower()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Order API failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(orders), str(e)))
    return insert_status, failed_status.values(), final_data_dict, payment_dict

def validate_orders_format(orders, user='', company_name='', is_cancelled=False):
    order_status_dict = {'NEW': 1, 'RETURN': 3, 'CANCEL': 4}
    NOW = datetime.datetime.now()
    insert_status = []
    inter_state = 0
    cgst_tax, igst_tax, sgst_tax, utgst_tax = 0,0,0,0
    final_data_dict = OrderedDict()
    sister_whs1 = list(get_sister_warehouse(user).values_list('user__username', flat=True))
    sister_whs1.append(user.username)
    sister_whs = []
    for sister_wh1 in sister_whs1:
        sister_whs.append(str(sister_wh1).lower())
    customer_name, customer_city, customer_telephone, customer_address, customer_pincode, shipping_address, customer_email = '','','','',0,'',''
    try:
        seller_master_dict, valid_order, query_params = {}, {}, {}
        failed_status = OrderedDict()
        if not orders:
            orders = {}
        if isinstance(orders, dict):
            orders = [orders]
        for ind, order in enumerate(orders):
            try:
                if order.has_key('order_date'):
                    creation_date = parser.parse(order['order_date'])
                else:
                    creation_date = NOW
            except:
                update_error_message(failed_status, 5024, 'Invalid Order Date Format', '')
            try:
                if order.has_key('shipment_date'):
                    shipment_date = parser.parse(order['shipment_date'])
                else:
                    shipment_date = NOW
            except:
                update_error_message(failed_status, 5024, 'Invalid Shipment Date Format', '')
            order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
            channel_name = order.get('source', 'offline')
            order_details = copy.deepcopy(ORDER_DATA)
            data = order
            if order.has_key('warehouse'):
                warehouse = order['warehouse']
                if warehouse.lower() in sister_whs:
                    user = User.objects.get(username=warehouse)
                else:
                    error_message = 'Invalid Warehouse Name'
                    update_error_message(failed_status, 5024, error_message, original_order_id)
            if order.has_key('order_reference'):
                order_reference = str(order['order_reference'])
                order_details['order_reference'] = order_reference

            if not order.get('order_id', ''):
                generate_order_id = get_order_id(user.id)
                order_code = get_order_prefix(user.id)
                order['order_id'] = order_code+str(generate_order_id)
            original_order_id = str(order['order_id'])
            order_code = ''.join(re.findall('\D+', original_order_id))
            order_id = ''.join(re.findall('\d+', original_order_id))
            filter_params = {'user': user.id, 'order_id': order_id}
            filter_params1 = {'user': user.id, 'original_order_id': original_order_id}

            order_status = order.get('order_status', 'NEW')
            if order_status not in order_status_dict.keys():
                error_message = 'Invalid Order Status - Should be ' + ','.join(order_status_dict.keys())
                update_error_message(failed_status, 5024, error_message, original_order_id)
                break

            customer_master = []
            if order.has_key('billing_address'):
                order_details['customer_id'] = order['billing_address'].get('customer_id', 0)
                if order_details['customer_id']:
                    try:
                        customer_master = CustomerMaster.objects.filter(user=user.id, customer_id=order_details['customer_id'])
                        if customer_master:
                            customer_name = customer_master[0].name
                            customer_telephone = customer_master[0].phone_number
                            customer_email= customer_master[0].email_id
                            customer_city = customer_master[0].city
                            customer_address = customer_master[0].address
                            customer_pincode = customer_master[0].pincode
                            customer_tax_type = customer_master[0].tax_type
                            if customer_tax_type == "inter_state":
                                inter_state = 1
                    except:
                        customer_master = []
                    if not customer_master:
                        error_message = 'Invalid Customer ID %s' % str(order_details['customer_id'])
                        update_error_message(failed_status, 5024, error_message, original_order_id)
                        break
                order_details['customer_name'] = order['billing_address'].get('name', customer_name)
                order_details['telephone'] = order['billing_address'].get('phone_number', customer_telephone)
                order_details['email_id'] = order['billing_address'].get('email', customer_email)
                order_details['city'] = order['billing_address'].get('city', customer_city)
                order_details['address'] = order['billing_address'].get('address', customer_address)
                try:
                    order_details['pin_code'] = int(order['billing_address'].get('pincode', customer_pincode))
                except:
                    order_details['pin_code'] = 0
            if order.has_key('shipping_address'):
                shipping_address = order['shipping_address'].get('name','') + '\n' + order['shipping_address'].get('address','')
                if order['shipping_address'].get('city'):
                    shipping_address += ("\n" + order['shipping_address'].get('city'))
                if order['shipping_address'].get('state'):
                    shipping_address += (", " + order['shipping_address'].get('state'))
                if order['shipping_address'].get('country'):
                    shipping_address += (", " + order['shipping_address'].get('country'))
                if order['shipping_address'].get('pincode'):
                    shipping_address += ("\nPincode: " + str(order['shipping_address'].get('pincode')))
                if order['shipping_address'].get('email'):
                    shipping_address += ("\nEmail: " + order['shipping_address'].get('email'))
                if order['shipping_address'].get('phone_number'):
                    shipping_address += ("\nPhone.No: " + str(order['shipping_address'].get('phone_number')))
            if order_code:
                filter_params['order_code'] = order_code
            sku_items = order['items']
            valid_order['user'] = user.id
            valid_order['marketplace'] = channel_name
            valid_order['original_order_id'] = original_order_id
            if order_details['status'] in [1]:
                valid_order['status__in'] = [1, 2, 3, 4, 5]
            elif order_details['status'] in [3, 4]:
                valid_order['status__in'] = [3, 4]
            order_detail_present = OrderDetail.objects.filter(**valid_order)
            if order_detail_present:
                if int(order_detail_present[0].status) == 1:
                    error_code = "5001"
                    message = 'Duplicate Order, ignored at Stockone'
                elif int(order_detail_present[0].status) == 3:
                    error_code = "5002"
                    message = 'Order is already returned at Stockone'
                elif int(order_detail_present[0].status) == 4:
                    error_code = "5003"
                    message = 'Order is already cancelled at Stockone'
                update_error_message(failed_status, error_code, message, original_order_id)
                break
            if order.has_key('attribute'):
                extra_fields_data = OrderedDict()
                extra_attributes = order['attribute']
                for key in extra_attributes:
                    extra_fields_data[key] = extra_attributes[key]
                if extra_fields_data:
                    create_extra_fields_for_order(original_order_id, extra_fields_data, user)
            for sku_item in sku_items:
                failed_sku_status = []
                sku_code = sku_item['sku']
                sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
                if sku_master:
                    filter_params['sku_id'] = sku_master[0].id
                    filter_params1['sku_id'] = sku_master[0].id
                else:
                    update_error_message(failed_status, 5020, "SKU Not found in Stockone", original_order_id)
                    continue

                if sku_master:
                    grouping_key = str(original_order_id) + '<<>>' + str(sku_master[0].sku_code)
                    order_det = OrderDetail.objects.filter(**filter_params)
                    order_det1 = OrderDetail.objects.filter(**filter_params1)
                    tax_obj = TaxMaster.objects.filter(product_type=sku_master[0].product_type, user=user.id,
                                                        max_amt__gte=sku_master[0].price, min_amt__lte=sku_master[0].price, inter_state=inter_state)

                    invoice_amount = 0
                    unit_price = sku_item.get('unit_price', '')
                    discount_amount = sku_item.get('discount_amount', '')
                    if discount_amount:
                        try:
                            order_summary_dict['discount'] = float(discount_amount)
                        except:
                            order_summary_dict['discount'] = 0
                    if unit_price == '':
                        unit_price, discount, price_bands_list = get_order_sku_price(customer_master, sku_master[0], user)
                        if discount_amount == '':
                            if sku_item.has_key('quantity'):
                                order_summary_dict['discount'] = ((float(sku_item['quantity']) * unit_price)/100) * discount
                                #unit_price = sku_item.get('unit_price', sku_master[0].price)
                            else:
                                update_error_message(failed_status, 5020, "quantity Field missing", original_order_id)
                                break
                    if not order_det:
                        order_det = order_det1

                    order_create = True

                    if tax_obj:
                        cgst_tax = float(tax_obj[0].cgst_tax)
                        sgst_tax = float(tax_obj[0].sgst_tax)
                        igst_tax = float(tax_obj[0].igst_tax)
                        utgst_tax = float(tax_obj[0].utgst_tax)

                    if sku_item.has_key('tax_percent'):
                        try:
                            cgst_tax = float(sku_item['tax_percent'].get('CGST', 0))
                        except:
                            cgst_tax = 0
                        try:
                            sgst_tax = float(sku_item['tax_percent'].get('SGST', 0))
                        except:
                            sgst_tax = 0
                        try:
                            igst_tax = float(sku_item['tax_percent'].get('IGST', 0))
                        except:
                            igst_tax = 0
                        try:
                            utgst_tax = float(sku_item['tax_percent'].get('UTGST', 0))
                        except:
                            utgst_tax = 0
                    if sku_item.has_key('sku_order_fields'):
                        sku_fields = sku_item['sku_order_fields']
                        for datum in sku_fields.keys():
                            sku_ord_dict = {'user': user.id, 'original_order_id': original_order_id, 'name': datum,
                                         'value': sku_fields[datum], 'order_type': 'order_sku', 'extra_fields': sku_master[0].id }
                            sku_attr_obj = OrderFields(**sku_ord_dict)
                            sku_attr_obj.save()
                    if order_create:
                        order_details['original_order_id'] = original_order_id
                        order_details['order_id'] = order_id
                        order_details['order_code'] = order_code

                        order_details['sku_id'] = sku_master[0].id
                        order_details['title'] = sku_item.get('name', sku_master[0].sku_desc)
                        order_details['user'] = user.id
                        if sku_item.has_key('quantity'):
                            order_details['quantity'] = sku_item['quantity']
                        else:
                            update_error_message(failed_status, 5020, "quantity Field missing", original_order_id)
                            break
                        order_details['shipment_date'] = shipment_date
                        order_details['marketplace'] = channel_name
                        order_details['invoice_amount'] = float(invoice_amount)
                        order_details['unit_price'] = float(unit_price)
                        tax = cgst_tax + sgst_tax
                        if not tax and igst_tax:
                            tax = igst_tax
                        if order_create and not invoice_amount:
                            amt = (float(order_details['quantity']) * order_details['unit_price']) -\
                                  order_summary_dict['discount']
                            order_details['invoice_amount'] = amt + ((amt/100)*tax)
                        order_details['creation_date'] = creation_date

                        if order.has_key('payment_status'):
                            if order['payment_status'].lower() == 'paid':
                                order_details['payment_received'] = order_details['invoice_amount']
                        final_data_dict = check_and_add_dict(grouping_key, 'order_details', order_details,
                                                             final_data_dict=final_data_dict)
                    if not failed_status and not insert_status:
                        order_summary_dict['cgst_tax'] = cgst_tax
                        order_summary_dict['sgst_tax'] = sgst_tax
                        order_summary_dict['igst_tax'] = igst_tax
                        order_summary_dict['utgst_tax'] = utgst_tax
                        if shipping_address:
                            order_summary_dict['consignee'] = shipping_address
                        order_summary_dict['invoice_date'] = order_details['creation_date']
                        order_summary_dict['inter_state'] = 0
                        order_summary_dict['mrp'] = sku_item.get('mrp', sku_master[0].mrp)
                        if order_summary_dict['igst_tax']:
                            order_summary_dict['inter_state'] = inter_state
                        final_data_dict = check_and_add_dict(grouping_key, 'order_summary_dict',
                                                             order_summary_dict, final_data_dict=final_data_dict)

                if len(failed_sku_status):
                    failed_status = {
                        "OrderId": original_order_id,
                        "Result": {
                            "Errors": failed_sku_status
                        }
                    }
                    break
                final_data_dict[grouping_key]['status_type'] = order_status
                if order.has_key('payment_status'):
                    final_data_dict[grouping_key]['payment_status'] = order['payment_status'].lower()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Order API failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(orders), str(e)))
    return insert_status, failed_status.values(), final_data_dict


def update_order_dicts_skip_errors(orders, failed_status, user='', company_name=''):
    from outbound import check_stocks
    trans_mapping = {}
    status = {'status': 0, 'messages': ['Something went wrong']}
    error_ids = map(lambda x: x.get('OrderId', ''), failed_status)
    # mysql_file_path = 'static/mysql_files'
    # folder_check(mysql_file_path)
    # file_time_stamp = str(datetime.datetime.now()).replace(' ', '_').replace(':', '_').split('.')[0]
    # cod_load_file_path = '%s/%s' % (mysql_file_path, 'customer_order_summary_' + file_time_stamp + '.txt')
    # cod_load_file = open(cod_load_file_path, 'w')
    # cod_columns = []
    # so_load_file_path = '%s/%s' % (mysql_file_path, 'seller_order_' + file_time_stamp + '.txt')
    # so_load_file = open(so_load_file_path, 'w')
    # so_columns = []
    # oc_load_file_path = '%s/%s' % (mysql_file_path, 'order_charges_' + file_time_stamp + '.txt')
    # oc_load_file = open(oc_load_file_path, 'w')
    # oc_columns = []
    cod_objs = []
    so_objs = []
    oc_objs = []
    for order_key, order in orders.iteritems():
        if not order.get('order_details', {}):
            continue
        order_det_dict = order['order_details']
        if order_det_dict['original_order_id'] in error_ids:
            continue
        if not order.get('order_detail_obj', None):
            order_obj = OrderDetail.objects.filter(original_order_id=order_det_dict['original_order_id'],
                                                   order_id=order_det_dict['order_id'],
                                                   order_code=order_det_dict['order_code'],
                                                   sku_id=order_det_dict['sku_id'],
                                                   user=order_det_dict['user'])
        else:
            order_obj = [order.get('order_detail_obj', None)]
        order_created = False
        if order_obj:
            order_obj = order_obj[0]
            order_obj.quantity = float(order_obj.quantity) + float(order_det_dict.get('quantity', 0))
            order_obj.invoice_amount = float(order_obj.invoice_amount) + float(order_det_dict.get('invoice_amount', 0))
            order_obj.save()
            order_detail = order_obj
        else:
            try:
                order_detail = OrderDetail.objects.create(**order['order_details'])
                order_detail.creation_date = order['order_details']['creation_date']
                order_detail.save()
                order_created = True
            except Exception as e:
                import traceback
                log_err.info(str(order['order_details']))
                log_err.debug(traceback.format_exc())

        try:
            if order.get('order_summary_dict', {}) and order_created:
                order['order_summary_dict']['order_id'] = order_detail.id

                cod_objs.append(CustomerOrderSummary(**order['order_summary_dict']))
                ## Disabling file load Feature
                #if order['order_summary_dict']['invoice_date']:
                #    order['order_summary_dict']['invoice_date'] = order['order_summary_dict']['invoice_date'].strftime("%Y-%m-%d %H:%M:%S")


                # cod_column_vals = order['order_summary_dict'].values()
                # cod_column_vals = map(str, cod_column_vals)
                # cod_columns = order['order_summary_dict'].keys()
                # update_string = "order_id=%s, updation_date=NOW()" % (order_detail.id)
                # date_string = 'NOW(), NOW()'
                # mysql_query_to_file(cod_load_file, 'CUSTOMER_ORDER_SUMMARY', cod_columns,
                #                     cod_column_vals, date_string=date_string, update_string=update_string)
        except Exception as e:
            import traceback
            log_err.info("COD Creation Failed for Order ID %s" % str(order['original_order_id']))
            log_err.debug(traceback.format_exc())
        try:
            if order.get('seller_order_dict', {}) and order_created:
                seller_order_dict = order['seller_order_dict']
                seller_order_dict['order_id'] = order_detail.id
                if seller_order_dict.get('seller_id', ''):
                    so_objs.append(SellerOrder(**seller_order_dict))
                    # so_column_vals = seller_order_dict.values()
                    # so_column_vals = map(str, so_column_vals)
                    # so_columns = seller_order_dict.keys()
                    # update_string = "order_id=%s, updation_date=NOW()" % (order_detail.id)
                    # date_string = 'NOW(), NOW()'
                    # mysql_query_to_file(so_load_file, 'SELLER_ORDER', so_columns,
                    #                     so_column_vals, date_string=date_string, update_string=update_string)
        except Exception as e:
            import traceback
            log_err.info("Seller Order Creation Failed for Order ID %s" % str(order['original_order_id']))
            log_err.debug(traceback.format_exc())
        try:
            if order.get('shipping_charge', 0) and order_created:
                oc_columns = ['order_id', 'user_id', 'charge_name', 'charge_amount']
                oc_column_vals = [str(order_detail.original_order_id), str(user.id), 'Shipping Charge', str(order['shipping_charge'])]
                oc_dict = dict(zip(oc_columns, oc_column_vals))
                oc_objs.append(oc_dict)
                # update_string = "order_id=%s, updation_date=NOW()" % (order_detail.original_order_id)
                # date_string = 'NOW(), NOW()'
                # mysql_query_to_file(oc_load_file, 'ORDER_CHARGES', oc_columns,
                #                     oc_column_vals, date_string=date_string, update_string=update_string)
        except Exception as e:
            import traceback
            log_err.info("Other Charges Creation Failed for Order ID %s" % str(order['original_order_id']))
            log_err.debug(traceback.format_exc())
        order_sku = {}
        #sku_obj = SKUMaster.objects.filter(id=order_det_dict['sku_id'])
        sku_obj = order.get('sku_obj', None)
        if not sku_obj:
            continue
        order_sku.update({sku_obj: order_det_dict['quantity']})
        auto_picklist_signal = get_misc_value('auto_generate_picklist', order_det_dict['user'])
        if auto_picklist_signal == 'true':
            message = check_stocks(order_sku, user, 'false', [order_detail])
        status = {'status': 1, 'messages': 'Success'}
    if cod_objs:
        try:
           CustomerOrderSummary.objects.bulk_create(cod_objs)
        except Exception as e:
            import traceback
            log_err.info("Customer Order Summary Bulk Creation Failed")
            log_err.debug(traceback.format_exc())
    if so_objs:
        try:
            SellerOrder.objects.bulk_create(so_objs)
        except Exception as e:
            import traceback
            log_err.info("Seller Order Bulk Creation Failed")
            log_err.debug(traceback.format_exc())
    if oc_objs:
        try:
            OrderCharges.objects.bulk_create(oc_objs)
        except Exception as e:
            import traceback
            log_err.info("Order Charges Bulk Creation Failed")
            log_err.debug(traceback.format_exc())
    # if cod_columns:
    #     try:
    #        load_by_file(cod_load_file_path, 'CUSTOMER_ORDER_SUMMARY', cod_columns)
    #     except Exception as e:
    #         import traceback
    #         log_err.info("Customer Order Summary Bulk Creation Failed")
    #         log_err.debug(traceback.format_exc())
    # if so_columns:
    #     try:
    #         load_by_file(so_load_file_path, 'SELLER_ORDER', so_columns)
    #     except Exception as e:
    #         import traceback
    #         log_err.info("Seller Order Bulk Creation Failed")
    #         log_err.debug(traceback.format_exc())
    # if oc_columns:
    #     try:
    #         load_by_file(oc_load_file_path, 'ORDER_CHARGES', oc_columns)
    #     except Exception as e:
    #         import traceback
    #         log_err.info("Order Charges Bulk Creation Failed")
    #         log_err.debug(traceback.format_exc())
    return status
