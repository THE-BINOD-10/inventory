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

def update_orders(orders, user='', company_name=''):
    order_mapping = eval(LOAD_CONFIG.get(company_name, 'order_mapping_dict', ''))
    NOW = datetime.datetime.now()

    insert_status = {'Orders Inserted': 0, 'Seller Master does not exists': 0, 'SOR ID not found': 0, 'Order Status not Matched': 0,
                     'Order Exists already': 0, 'Invalid SKU Codes': 0}

    try:
        seller_masters = SellerMaster.objects.filter(user=user.id)
        user_profile = UserProfile.objects.get(user_id=user.id)
        seller_master_dict = {}
        sku_ids = []
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
                    if not order_status == 'PROCESSED':
                        insert_status['Order Status not Matched'] += 1
                        continue
                    seller_master_dict[seller_id] = seller_master[0].id
                    seller_order = SellerOrder.objects.filter(Q(order__original_order_id=original_order_id)|Q(order__order_id=order_id,
                                                 order__order_code=order_code),sor_id=eval(order_mapping['sor_id']), seller__user=user.id)
                    if seller_order:
                        insert_status['Order Exists already'] += 1
                        continue
                try:
                    shipment_date = eval(order_mapping['shipment_date'])
                    shipment_date = datetime.datetime.fromtimestamp(shipment_date)
                except:
                    shipment_date = NOW
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
                    invoice_amount = float(eval(order_mapping['unit_price']) * eval(order_mapping['quantity']))
                    order_details['unit_price'] = eval(order_mapping['unit_price'])
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
                if (order_det and filter_params['sku_id'] in sku_ids) or (order_det and seller_id in seller_master_dict.keys()):
                    order_det = order_det[0]
                    order_det.quantity += eval(order_mapping['quantity'])
                    order_det.invoice_amount += invoice_amount
                    order_det.save()
                    if order_det and seller_id in seller_master_dict.keys():
                        order_create = False
                    else:
                        insert_status['Order Exists already'] += 1
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

                if order_mapping.has_key('sor_id'):
                    seller_order_dict['seller_id'] = seller_master_dict[seller_id]
                    seller_order_dict['sor_id'] = eval(order_mapping['sor_id'])
                    seller_order_dict['order_status'] = eval(order_mapping['order_status'])
                    seller_order_dict['order_id'] = order_detail.id
                    seller_order_dict['quantity'] = eval(order_mapping['quantity'])

                check_create_seller_order(seller_order_dict, order_detail, user)
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
    for key, val in sku_mapping.iteritems():
        if key in exclude_list:
            continue
        value = sku_data.get(key, '')
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
                     'SKU Code should not be empty': []}

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

