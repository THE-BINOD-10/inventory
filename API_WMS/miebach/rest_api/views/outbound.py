from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import json
from itertools import chain
from decimal import Decimal
from django.db.models import Q, F, DateField
from collections import OrderedDict
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
from django.template import loader, Context
from django.db.models.functions import Cast
from django.core.files.storage import FileSystemStorage
from mail_server import send_mail, send_mail_attachment
from common import *
from miebach_utils import *
from operator import itemgetter
from django.db.models import Sum
from django.db.models import Max
from itertools import groupby
import datetime
import shutil
from utils import *

log = init_logger('logs/outbound.log')


@csrf_exempt
def get_batch_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters,
                   user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_dict = eval(user_dict)
    lis = ['sku__sku_code', 'sku__sku_code', 'title', 'total']
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}

    if user_dict.get('market_places', ''):
        marketplace = user_dict['market_places'].split(',')
        data_dict['marketplace__in'] = marketplace
    if user_dict.get('customer_id', ''):
        data_dict['customer_id'], data_dict['customer_name'] = user_dict['customer_id'].split(':')
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_params = get_filtered_params(filters, ['sku__sku_code', 'title', 'total'])
    search_params['sku_id__in'] = sku_master_ids

    if search_term:
        mapping_results = OrderDetail.objects.filter(**data_dict).values('sku__sku_code', 'title',
                                                                         'sku_code').distinct(). \
            annotate(total=Sum('quantity')).filter(Q(sku__sku_code__icontains=search_term) |
                                                   Q(title__icontains=search_term) | Q(total__icontains=search_term),
                                                   **search_params) \
            .exclude(order_code="CO").order_by(order_data)
    else:
        mapping_results = OrderDetail.objects.filter(**data_dict).values('sku__sku_code', 'title',
                                                                         'sku_code').distinct(). \
            annotate(total=Sum('quantity')).filter(**search_params).exclude(order_code="CO") \
            .order_by(order_data)

    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    index = 0
    for dat in mapping_results[start_index:stop_index]:

        sku_code = dat['sku__sku_code']
        if sku_code == 'TEMP':
            sku_code = dat['sku_code']

        check_values = dat['sku__sku_code'] + '<>' + sku_code + '<>' + dat['title']
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (check_values, dat['total'])

        temp_data['aaData'].append(
            OrderedDict((('data_value', check_values), ('SKU Code', sku_code), ('Title', dat['title']),
                         ('Total Quantity', dat['total']), ('id', index), ('DT_RowClass', 'results'))))
        index += 1


@csrf_exempt
def get_order_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters={},
                      user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    if user_dict:
        user_dict = eval(user_dict)
    lis = ['id', 'order_id', 'sku__sku_code', 'title', 'quantity', 'shipment_date', 'city', 'status']
    unsorted_dict = {6: 'Order Taken By', 7: 'Status'}
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}

    if user_dict.get('market_places', ''):
        marketplace = user_dict['market_places'].split(',')
        data_dict['marketplace__in'] = marketplace
    if user_dict.get('customer_id', ''):
        data_dict['customer_id'], data_dict['customer_name'] = user_dict['customer_id'].split(':')

    search_params = get_filtered_params(filters, lis[1:])
    if 'shipment_date__icontains' in search_params.keys():
        search_params['shipment_date__regex'] = search_params['shipment_date__icontains']
        del search_params['shipment_date__icontains']
    if 'order_id__icontains' in search_params.keys():
        order_search = search_params['order_id__icontains']
        search_params['order_id__icontains'] = ''.join(re.findall('\d+', order_search))
        search_params['order_code__icontains'] = ''.join(re.findall('\D+', order_search))

    search_params['sku_id__in'] = sku_master_ids

    if 'city__icontains' in search_params.keys():
        order_taken_val_user = CustomerOrderSummary.objects.filter(
            order_taken_by__icontains=search_params['city__icontains'],
            order__user=user.id)
        search_params['id__in'] = order_taken_val_user.values_list('order_id', flat=True)
        del (search_params['city__icontains'])
    if 'status__icontains' in search_params.keys():
        stat_search = {}
        if search_params.has_key('id__in'):
            stat_search['order_id__in'] = search_params['id__in']
        order_taken_val_user = CustomerOrderSummary.objects.filter(status__icontains=search_params['status__icontains'],
                                                                   order__user=user.id, **stat_search)
        search_params['id__in'] = order_taken_val_user.values_list('order_id', flat=True)
        del (search_params['status__icontains'])

    if search_term:
        master_data = OrderDetail.objects.filter(
            Q(sku__sku_code__icontains=search_term, status=1) | Q(order_id__icontains=search_term,
                                                                  status=1) | Q(title__icontains=search_term,
                                                                                status=1) | Q(
                quantity__icontains=search_term,
                status=1), user=user.id, quantity__gt=0).filter(**search_params).exclude(order_code="CO")

    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = OrderDetail.objects.filter(**data_dict).filter(**search_params).exclude(order_code="CO").order_by(
            order_data)
    else:
        master_data = OrderDetail.objects.filter(**data_dict).filter(**search_params).exclude(order_code="CO").order_by(
            'shipment_date')

    custom_search = False
    if col_num in unsorted_dict.keys():
        custom_search = True

    if stop_index and not custom_search:
        master_data = master_data[start_index:stop_index]

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    count = 0

    order_summary_objs = CustomerOrderSummary.objects.filter(order__user=user.id).values('order__order_id', \
                                                                                         'shipment_time_slot', 'status',
                                                                                         'order_taken_by').distinct()

    all_seller_orders = SellerOrder.objects.filter(order__user=user.id, status=0)
    for data in master_data:
        sku_code = data.sku.sku_code
        order_id = data.order_code + str(int(data.order_id))
        if data.original_order_id:
            order_id = data.original_order_id
        cust_status_obj = order_summary_objs.filter(order_id=data.id, order__user=user.id)
        cust_status = ''
        time_slot = ''
        order_taken_val = ''
        if cust_status_obj:
            cust_status = cust_status_obj[0]['status']
            time_slot = cust_status_obj[0]['shipment_time_slot']
            order_taken_val = cust_status_obj[0]['order_taken_by']

        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data.id, data.sku.sku_code)
        shipment_data = get_local_date(request.user, data.shipment_date, True).strftime("%d %b, %Y")
        if time_slot:
            if "-" in time_slot:
                time_slot = time_slot.split("-")[0]

            shipment_data = shipment_data + ', ' + time_slot

        try:
            order_id = int(float(order_id))
        except:
            order_id = str(xcode(order_id))
        quantity = float(data.quantity)
        seller_order = all_seller_orders.filter(order_id=data.id).aggregate(Sum('quantity'))['quantity__sum']
        if seller_order:
            quantity = quantity - seller_order

        temp_data['aaData'].append(OrderedDict((('', checkbox), ('Order ID', order_id), ('SKU Code', sku_code),
                                                ('Title', data.title), ('id', count), ('Product Quantity', quantity),
                                                ('Shipment Date', shipment_data),
                                                ('Marketplace', data.marketplace), ('DT_RowClass', 'results'),
                                                ('DT_RowAttr', {'data-id': str(data.order_id)}),
                                                ('Order Taken By', order_taken_val), ('Status', cust_status))))
        count = count + 1

    col_val = ['Order ID', 'Order ID', 'SKU Code', 'Title', 'Product Quantity', 'Shipment Date', 'Order Taken By',
               'Status']
    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(col_val, temp_data['aaData'], order_term, '', col_num, exact=False)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


@csrf_exempt
def get_stock_transfer_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['id', 'st_po__open_st__warehouse__username', 'order_id', 'sku__sku_code', 'quantity']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = StockTransfer.objects.filter(sku__user=user.id, status=1).order_by(order_data)
    if search_term:
        master_data = StockTransfer.objects.filter(Q(st_po__open_st__warehouse__username__icontains=search_term) |
                                                   Q(quantity__icontains=search_term) | Q(
            order_id__icontains=search_term) |
                                                   Q(sku__sku_code__icontains=search_term), sku__user=user.id,
                                                   status=1).order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    count = 0
    for data in master_data[start_index:stop_index]:
        checkbox = '<input type="checkbox" name="id" value="%s">' % data.id
        w_user = User.objects.get(id=data.st_po.open_st.sku.user)
        temp_data['aaData'].append({'': checkbox, 'Warehouse Name': w_user.username, 'Stock Transfer ID': data.order_id,
                                    'SKU Code': data.sku.sku_code, 'Quantity': data.quantity, 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'id': data.id}, 'id': count})
        count = count + 1


@csrf_exempt
def open_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, status=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    status_dict = eval(status)
    filter_params = {}
    if isinstance(status_dict, dict):
        status = status_dict['status']
        if status_dict.get('market_place', ''):
            filter_params['order__marketplace'] = status_dict['market_place']
        filter_params['status__icontains'] = status
    if 'open' in status:
        filter_params['status__icontains'] = "open"
        filter_params['reserved_quantity__gt'] = 0
    else:
        if not status == 'batch_picked':
            del filter_params['status__icontains']
        filter_params['picked_quantity__gt'] = 0
    log.info(status)
    if status == 'batch_picked':
        col_num = col_num - 1
        header = BATCH_PICK_LIST_HEADERS
    elif status == 'picked':
        header = PICKED_PICK_LIST_HEADERS
    else:
        header = OPEN_PICK_LIST_HEADERS

    all_picks = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id), **filter_params)

    if search_term:
        master_data = all_picks.filter(
            Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids)).filter(
            Q(picklist_number__icontains=search_term) | Q(remarks__icontains=search_term) | Q(
                order__marketplace__icontains=search_term) | Q(order__customer_name__icontains=search_term))

    elif order_term:
        # col_num = col_num - 1
        order_data = header.values()[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data

        master_data = all_picks.filter(
            Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids)).order_by(order_data)
    else:
        master_data = all_picks.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids))

    total_reserved_quantity = master_data.aggregate(Sum('reserved_quantity'))['reserved_quantity__sum']
    total_picked_quantity = master_data.aggregate(Sum('picked_quantity'))['picked_quantity__sum']
    master_data = master_data.values('picklist_number').distinct()
    if order_term:
        master_data = [key for key, _ in groupby(master_data)]

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if not total_picked_quantity:
        total_picked_quantity = 0
    else:
        temp_data['totalPickedQuantity'] = int(total_picked_quantity)

    if not total_reserved_quantity:
        temp_data['totalReservedQuantity'] = 0
    else:
        temp_data['totalReservedQuantity'] = int(total_reserved_quantity)

    count = 0
    od_id, od_order_id = '', ''
    for data in master_data[start_index:stop_index]:
        prepare_str = ''
        shipment_date = ''
        create_date_value, order_marketplace, order_customer_name, picklist_id, remarks = '', [], [], '', ''
        picklist_obj = all_picks.filter(picklist_number=data['picklist_number'])
        reserved_quantity_sum_value = picklist_obj.aggregate(Sum('reserved_quantity'))['reserved_quantity__sum']
        if not reserved_quantity_sum_value:
            reserved_quantity_sum_value = 0
        picked_quantity_sum_value = picklist_obj.aggregate(Sum('picked_quantity'))['picked_quantity__sum']
        if not picked_quantity_sum_value:
            picked_quantity_sum_value = 0
        if picklist_obj:
            order_marketplace = list(
                picklist_obj.exclude(order__marketplace__in='').filter(order_id__isnull=False).values_list(
                    'order__marketplace', flat=True))
            order_customer_name = list(
                picklist_obj.exclude(order__customer_name='').filter(order_id__isnull=False).values_list(
                    'order__customer_name', flat=True))

            order_marketplace1 = [str(x).upper() for x in order_marketplace]
            if 'OFFLINE' in order_marketplace1 and len(set(order_marketplace1)) == 1:
                prepare_str = ','.join(list(set(order_customer_name)))
            else:
                prepare_str = ','.join(list(set(order_marketplace)))

            create_date_value = ""
            if picklist_obj[0].creation_date:
                create_date_value = get_local_date(request.user, picklist_obj[0].creation_date)

            remarks = picklist_obj[0].remarks
            if remarks == 'Auto-generated Picklist':
                od_id = int(picklist_obj[0].order.id)
                od_order_id = str(picklist_obj[0].order.order_code) + str(picklist_obj[0].order.order_id)
            picklist_id = picklist_obj[0].picklist_number

            first_ord_obj = picklist_obj.exclude(order__shipment_date__isnull=True).values_list('order__id',
                                                                                                flat=True).order_by(
                'order__shipment_date')
            shipment_date = ""
            if first_ord_obj:
                ship_date = OrderDetail.objects.get(id=first_ord_obj[0]).shipment_date
                shipment_date = get_local_date(user, ship_date, True)
                shipment_date = shipment_date.strftime("%d %b, %Y")

                time_slot = get_shipment_time(first_ord_obj[0], user)
                if time_slot:
                    shipment_date = shipment_date + ', ' + time_slot

        result_data = OrderedDict((('DT_RowAttr', {'data-id': picklist_id}), ('picklist_note', remarks),
                                   ('reserved_quantity', reserved_quantity_sum_value),
                                   ('picked_quantity', picked_quantity_sum_value),
                                   ('customer', prepare_str), ('shipment_date', shipment_date),
                                   ('date', create_date_value), ('id', count), ('DT_RowClass', 'results'),
                                   ('od_id', od_id), ('od_order_id', od_order_id)))
        dat = 'picklist_id'
        count += 1
        if status == 'batch_picked':
            dat = 'picklist_id'

            checkbox = "<input type='checkbox' name='%s' value='%s'>" % (
            data['picklist_number'], data['picklist_number'])
            result_data['checkbox'] = checkbox
        result_data[dat] = picklist_id
        temp_data['aaData'].append(result_data)


@csrf_exempt
def get_customer_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    gateout = request.POST.get('gateout', '')
    if gateout:
        gateout = int(gateout)
    lis = ['Shipment Number', 'Customer ID', 'Customer Name', 'Total Quantity']
    all_data = OrderedDict()
    if search_term:
        results = ShipmentInfo.objects.filter(order__sku_id__in=sku_master_ids). \
            filter(Q(order_shipment__shipment_number__icontains=search_term) |
                   Q(order__customer_id__icontains=search_term) | Q(order__customer_name__icontains=search_term),
                   order_shipment__user=user.id).order_by('order_id')
    else:
        results = ShipmentInfo.objects.filter(order__sku_id__in=sku_master_ids). \
            filter(order_shipment__user=user.id).order_by('order_id')
    for result in results:
        tracking = ShipmentTracking.objects.filter(shipment_id=result.id, shipment__order__user=user.id).order_by(
            '-creation_date'). \
            values_list('ship_status', flat=True)

        if gateout:
            if tracking and tracking[0] != 'Out for Delivery':
                continue
        else:
            if tracking and tracking[0] in ['Delivered', 'Out for Delivery']:
                continue

        cond = (result.order_shipment.shipment_number, result.order.customer_id, result.order.customer_name)
        all_data.setdefault(cond, 0)
        all_data[cond] += result.shipping_quantity

    temp_data['recordsTotal'] = len(all_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for key, value in all_data.iteritems():
        temp_data['aaData'].append(
            {'DT_RowId': key[0], 'Shipment Number': key[0], 'Customer ID': key[1], 'Customer Name': key[2],
             'Total Quantity': value, 'DT_RowClass': 'results'})
    sort_col = lis[col_num]

    if order_term == 'asc':
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
    else:
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


def create_temp_stock(sku_code, zone, quantity, stock_detail, user):
    if not quantity:
        quantity = 0
    inventory = StockDetail.objects.filter(sku__sku_code=sku_code, location__zone__zone=zone, sku__user=user)
    if inventory:
        inventory = inventory[0]
        for stock in stock_detail:
            if stock.id == inventory.id:
                setattr(stock, 'quantity', float(stock.quantity) + float(quantity))
                stock.save()
                break
        else:
            setattr(inventory, 'quantity', float(inventory.quantity) + float(quantity))
            inventory.save()
            stock_detail.append(inventory)
    else:
        location_id = LocationMaster.objects.filter(zone__zone=zone, zone__user=user)
        sku_id = SKUMaster.objects.filter(sku_code=sku_code, user=user)
        if sku_id and location_id:
            stock_dict = {'location_id': location_id[0].id, 'receipt_number': 0,
                          'receipt_date': datetime.datetime.now(),
                          'sku_id': sku_id[0].id, 'quantity': quantity, 'status': 1,
                          'creation_date': datetime.datetime.now()}
            stock = StockDetail(**stock_dict)
            stock.save()
            stock_detail.append(stock)
    return stock_detail


def get_picklist_locations(data_dict, user):
    exclude_dict = {'location__lock_status__in': ['Outbound', 'Inbound and Outbound'],
                    'location__zone__zone__in': ['TEMP_ZONE', 'DAMAGED_ZONE']}
    back_order = get_misc_value('back_order', user.id)
    fifo_switch = get_misc_value('fifo_switch', user.id)

    if fifo_switch == 'true':
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0,
                                                                           **data_dict). \
            order_by('receipt_date', 'location__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0, **data_dict). \
            order_by('receipt_date', 'location__pick_sequence')
        data_dict['location__zone__zone'] = 'TEMP_ZONE'
        # del exclude_dict['location__zone__zone']
        stock_detail3 = StockDetail.objects.exclude(**exclude_dict).filter(**data_dict).order_by('receipt_date',
                                                                                                 'location__pick_sequence')
        stock_detail = list(chain(stock_detail1, stock_detail2, stock_detail3))
    else:
        # del exclude_dict['location__zone__zone']
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0,
                                                                           **data_dict). \
            order_by('location_id__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0,
                                                                           **data_dict).order_by('receipt_date')
        stock_detail = list(chain(stock_detail1, stock_detail2))
        if back_order == 'true':
            data_dict['location__zone__zone'] = 'BAY_AREA'
            back_stock = StockDetail.objects.filter(**data_dict)
            stock_detail = list(chain(back_stock, stock_detail))
    return stock_detail


@csrf_exempt
@login_required
@get_admin_user
def generate_picklist(request, user=''):
    remarks = request.POST['ship_reference']
    filters = request.POST.get('filters', '')
    order_filter = {'status': 1, 'user': user.id, 'quantity__gt': 0}
    seller_order_filter = {'order__status': 1, 'order__user': user.id, 'order__quantity__gt': 0}
    if filters:
        filters = eval(filters)
        if filters['market_places']:
            order_filter['marketplace__in'] = (filters['market_places']).split(',')
            seller_order_filter['order__marketplace__in'] = order_filter['marketplace__in']
        if filters.get('customer_id', ''):
            customer_id = ''.join(re.findall('\d+', filters['customer_id']))
            order_filter['customer_id'] = customer_id
            seller_order_filter['order__customer_id'] = customer_id
    data = []
    stock_status = ''
    out_of_stock = []
    single_order = ''
    picklist_number = get_picklist_number(user)

    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
        location__zone__zone='DAMAGED_ZONE').filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(**order_filter)
    all_seller_orders = SellerOrder.objects.prefetch_related('order__sku').filter(**seller_order_filter)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
            'receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
            'location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    all_sku_stocks = stock_detail1 | stock_detail2
    log.info("Generate Picklist params " + str(request.POST.dict()))
    seller_stocks = SellerStock.objects.filter(seller__user=user.id).values('stock_id', 'seller_id')
    for key, value in request.POST.iteritems():
        if key in ('sortingTable_length', 'fifo-switch', 'ship_reference', 'remarks', 'filters'):
            continue

        order_data = OrderDetail.objects.get(id=key, user=user.id)
        seller_orders = all_seller_orders.filter(order_id=key, status=1).order_by('order__shipment_date')
        try:
            if seller_orders:
                for seller_order in seller_orders:
                    sku_stocks = all_sku_stocks
                    seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(seller_order.seller_id),
                                               seller_stocks)
                    if seller_stock_dict:
                        sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
                        sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
                    else:
                        sku_stocks = sku_stocks.filter(id=0)
                    stock_status, picklist_number = picklist_generation([seller_order], request, picklist_number, user,
                                                                        sku_combos, sku_stocks, status='open',
                                                                        remarks=remarks, is_seller_order=True)
            else:
                stock_status, picklist_number = picklist_generation([order_data], request, picklist_number, user,
                                                                    sku_combos, sku_stocks, status='open',
                                                                    remarks=remarks)
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Generate Picklist order view failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))
            stock_status = ['Internal Server Error']
        if stock_status:
            out_of_stock = out_of_stock + stock_status

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    show_image = 'false'
    use_imei = 'false'
    order_status = ''

    data, sku_total_quantities = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']
        if order_status == 'open':
            order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
            order_count_len = len(filter(lambda x: len(str(x)) > 0, order_count))
            if order_count_len == 1:
                single_order = str(order_count[0])

    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status,
                                    'order_status': order_status, 'single_order': single_order,
                                    'sku_total_quantities': sku_total_quantities}))


@csrf_exempt
@login_required
@get_admin_user
def batch_generate_picklist(request, user=''):
    remarks = request.POST.get('ship_reference', '')
    filters = request.POST.get('filters', '')
    order_filter = {'status': 1, 'user': user.id, 'quantity__gt': 0}
    if filters:
        filters = eval(filters)
        if filters['market_places']:
            order_filter['marketplace__in'] = (filters['market_places']).split(',')
        if filters.get('customer_id', ''):
            customer_id = ''.join(re.findall('\d+', filters['customer_id']))
            order_filter['customer_id'] = customer_id

    data = []
    order_data = []
    stock_status = ''
    out_of_stock = []

    try:
        picklist_number = get_picklist_number(user)

        sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
        sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
            location__zone__zone='DAMAGED_ZONE').filter(sku__user=user.id, quantity__gt=0)
        all_orders = OrderDetail.objects.prefetch_related('sku').filter(**order_filter)

        fifo_switch = get_misc_value('fifo_switch', user.id)
        if fifo_switch == 'true':
            stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
                'receipt_date')
            data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
            stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
        else:
            stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
                'location_id__pick_sequence')
            stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by(
                'receipt_date')
        sku_stocks = stock_detail1 | stock_detail2

        for key, value in request.POST.iteritems():
            if key in PICKLIST_SKIP_LIST or key in ['filters']:
                continue

            key = key.split('<>')
            sku_code, marketplace_sku_code, title = key
            order_filter = {'sku__sku_code': sku_code, 'quantity__gt': 0, 'title': title}

            if sku_code != marketplace_sku_code:
                order_filter['sku_code'] = marketplace_sku_code

            if request.POST.get('selected'):
                order_filter['marketplace__in'] = request.POST.get('selected').split(',')

            order_detail = all_orders.filter(**order_filter).order_by('shipment_date')

            stock_status, picklist_number = picklist_generation(order_detail, request, picklist_number, user,
                                                                sku_combos, sku_stocks, remarks=remarks)

            if stock_status:
                out_of_stock = out_of_stock + stock_status
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Generate Picklist SKU View failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse(json.dumps({'message': 'Picklist Generation Failed'}))

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    order_status = ''
    data, sku_total_quantities = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']

    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status, \
                                    'order_status': order_status, 'user': request.user.id, \
                                    'sku_total_quantities': sku_total_quantities}))


def get_sku_location_stock(wms_code, location, user_id, stock_skus, reserved_skus, stocks, reserved_instances):
    stock_left = 0
    if wms_code in stock_skus and not location == 'NO STOCK':
        if location in map(lambda d: d['location__location'],
                           filter(lambda person: person['sku__wms_code'] == wms_code, stocks)):
            stock_left = float(
                filter(lambda person: person['sku__wms_code'] == wms_code and person['location__location'] == location, \
                       stocks)[0]['quantity'])
        if wms_code in reserved_skus:
            if location in map(lambda d: d['stock__location__location'], \
                               filter(lambda person: person['stock__sku__wms_code'] == wms_code, reserved_instances)):
                st_res_quan = filter(lambda person: person['stock__sku__wms_code'] == wms_code and \
                                                    person['stock__location__location'] == location,
                                     reserved_instances)[0]['reserved']
                stock_left -= float(st_res_quan)
        if stock_left < 0:
            stock_left = 0
    return stock_left


def get_picklist_data(data_id, user_id):
    sku_total_quantities = {}
    picklist_orders = Picklist.objects.filter(Q(order__sku__user=user_id) | Q(stock__sku__user=user_id),
                                              picklist_number=data_id)
    pick_stocks = StockDetail.objects.filter(sku__user=user_id)
    stocks = pick_stocks.filter(quantity__gt=0).values('sku__wms_code', 'location__location').distinct().annotate(
        quantity=Sum('quantity'))
    reserved_instances = PicklistLocation.objects.filter(status=1, picklist__order__user=user_id).values(
        'stock__sku__wms_code',
        'stock__location__location'). \
        distinct().annotate(reserved=Sum('reserved'))
    stock_skus = map(lambda d: d['sku__wms_code'], stocks)
    reserved_skus = map(lambda d: d['stock__sku__wms_code'], reserved_instances)
    data = []
    if not picklist_orders:
        return data, sku_total_quantities
    order_status = ''
    for orders in picklist_orders:
        if 'open' in orders.status:
            order_status = orders.status
    if not order_status:
        order_status = 'picked'
    if order_status == "batch_open":
        batch_data = {}
        for order in picklist_orders:
            stock_id = ''
            wms_code = order.sku_code
            customer_name = ''
            remarks = ''
            load_unit_handle = ''
            category = ''
            if order.stock:
                stock_id = pick_stocks.get(id=order.stock_id)
            if order.order:
                sku_code = order.order.sku_code
                title = order.order.title
                invoice = order.order.invoice_amount
                customer_name = order.order.customer_name
                marketplace = order.order.marketplace
                remarks = order.order.remarks
                order_id = str(order.order.order_id)
                load_unit_handle = order.order.sku.load_unit_handle
                category = order.order.sku.sku_category
            else:
                st_order = STOrder.objects.filter(picklist_id=order.id)
                sku_code = ''
                title = st_order[0].stock_transfer.sku.sku_desc
                invoice = st_order[0].stock_transfer.invoice_amount
                load_unit_handle = st_order[0].stock_transfer.sku.load_unit_handle
                category = st_order[0].stock_transfer.sku.sku_category
                marketplace = ""
                order_id = ''

            pallet_code = ''
            pallet_detail = ''
            if stock_id and stock_id.pallet_detail:
                pallet_code = stock_id.pallet_detail.pallet_code
                pallet_detail = stock_id.pallet_detail

            zone = 'NO STOCK'
            st_id = 0
            sequence = 0
            location = 'NO STOCK'
            image = ''
            if order.order and order.order.sku:
                image = order.order.sku.image_url
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = stock_id.sku.image_url
                wms_code = stock_id.sku.wms_code
                load_unit_handle = stock_id.sku.load_unit_handle
                category = stock_id.sku.sku_category

            match_condition = (location, pallet_detail, wms_code, sku_code, title)
            if match_condition not in batch_data:
                if order.reserved_quantity == 0:
                    continue
                stock_left = get_sku_location_stock(wms_code, location, user_id, stock_skus, reserved_skus, stocks,
                                                    reserved_instances)
                last_picked_locs = ''
                if location == 'NO STOCK':
                    last_picked = pick_stocks.exclude(location__zone__zone='DAMAGED_ZONE').filter(
                        sku__wms_code=wms_code). \
                                      order_by('-updation_date').values_list('location__location',
                                                                             flat=True).distinct()[:2]
                    last_picked_locs = ','.join(last_picked)

                batch_data[match_condition] = {'wms_code': wms_code, 'zone': zone, 'sequence': sequence,
                                               'location': location, 'reserved_quantity': order.reserved_quantity,
                                               'picklist_number': data_id, 'stock_id': st_id,
                                               'picked_quantity': order.reserved_quantity, 'id': order.id,
                                               'invoice_amount': invoice, 'price': invoice * order.reserved_quantity,
                                               'image': image, 'order_id': str(order.order_id), 'status': order.status,
                                               'pallet_code': pallet_code, 'sku_code': sku_code, 'title': title,
                                               'stock_left': stock_left, 'last_picked_locs': last_picked_locs,
                                               'customer_name': customer_name, 'marketplace': marketplace,
                                               'order_no': order_id, 'remarks': remarks,
                                               'load_unit_handle': load_unit_handle, 'category': category}
            else:
                batch_data[match_condition]['reserved_quantity'] += order.reserved_quantity
                batch_data[match_condition]['picked_quantity'] += order.reserved_quantity
                batch_data[match_condition]['invoice_amount'] += invoice
                if batch_data[match_condition]['marketplace'].find(marketplace) == -1:
                    batch_data[match_condition]['marketplace'] += "," + marketplace
            if wms_code in sku_total_quantities.keys():
                sku_total_quantities[wms_code] += float(order.reserved_quantity)
            else:
                sku_total_quantities[wms_code] = float(order.reserved_quantity)
        data = batch_data.values()

        if get_misc_value('picklist_sort_by', user_id) == 'true':
            data = sorted(data, key=itemgetter('order_id'))
        else:
            data = sorted(data, key=itemgetter('sequence'))
        return data, sku_total_quantities

    elif order_status == "open":
        for order in picklist_orders:
            stock_id = ''
            customer_name = ''
            remarks = ''
            load_unit_handle = ''
            category = ''
            if order.order:
                wms_code = order.order.sku.wms_code
                if order.order_type == 'combo' and order.sku_code:
                    wms_code = order.sku_code
                invoice_amount = order.order.invoice_amount
                order_id = str(order.order.order_id)
                sku_code = order.order.sku_code
                title = order.order.title
                customer_name = order.order.customer_name
                marketplace = order.order.marketplace
                remarks = order.order.remarks
                load_unit_handle = order.order.sku.load_unit_handle
                category = order.order.sku.sku_category
            else:
                wms_code = order.stock.sku.wms_code
                invoice_amount = 0
                order_id = ''
                sku_code = order.stock.sku.sku_code
                title = order.stock.sku.sku_desc
                marketplace = ""
                load_unit_handle = order.stock.sku.load_unit_handle
                category = order.stock.sku.sku_category
            if order.stock_id:
                stock_id = pick_stocks.get(id=order.stock_id)
            if order.reserved_quantity == 0:
                continue
            pallet_code = ''
            if stock_id and stock_id.pallet_detail:
                pallet_code = stock_id.pallet_detail.pallet_code

            zone = 'NO STOCK'
            st_id = 0
            sequence = 0
            location = 'NO STOCK'
            image = ''
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = stock_id.sku.image_url
                wms_code = stock_id.sku.wms_code

            stock_left = get_sku_location_stock(wms_code, location, user_id, stock_skus, reserved_skus, stocks,
                                                reserved_instances)
            last_picked_locs = ''
            if location == 'NO STOCK':
                last_picked = pick_stocks.exclude(location__zone__zone='DAMAGED_ZONE').filter(sku__wms_code=wms_code). \
                                  order_by('-updation_date').values_list('location__location',
                                                                         flat=True).distinct()[:2]
                last_picked_locs = ','.join(last_picked)

            data.append(
                {'wms_code': wms_code, 'zone': zone, 'location': location, 'reserved_quantity': order.reserved_quantity,
                 'picklist_number': data_id, 'stock_id': st_id, 'order_id': str(order.order_id),
                 'picked_quantity': order.reserved_quantity, 'id': order.id, 'sequence': sequence,
                 'invoice_amount': invoice_amount, 'price': invoice_amount * order.reserved_quantity, 'image': image,
                 'status': order.status, 'order_no': order_id, 'pallet_code': pallet_code, 'sku_code': sku_code,
                 'title': title, 'stock_left': stock_left, 'last_picked_locs': last_picked_locs,
                 'customer_name': customer_name, 'marketplace': marketplace, 'remarks': remarks,
                 'load_unit_handle': load_unit_handle, 'category': category})

            if wms_code in sku_total_quantities.keys():
                sku_total_quantities[wms_code] += float(order.reserved_quantity)
            else:
                sku_total_quantities[wms_code] = float(order.reserved_quantity)

        if get_misc_value('picklist_sort_by', user_id) == 'true':
            data = sorted(data, key=itemgetter('order_id'))
        else:
            data = sorted(data, key=itemgetter('sequence'))
        return data, sku_total_quantities
    else:
        for order in picklist_orders:
            stock_id = ''
            wms_code = order.order.sku.wms_code
            marketplace = order.order.marketplace
            remarks = order.order.remarks
            if order.stock_id:
                stock_id = pick_stocks.get(id=order.stock_id)

            zone = 'NO STOCK'
            st_id = 0
            sequence = 0
            location = 'NO STOCK'
            pallet_code = ''
            image = ''
            load_unit_handle = ''
            category = ''
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = stock_id.sku.image_url
                load_unit_handle = stock_id.sku.load_unit_handle
                category = stock_id.sku.sku_category

            customer_name = ''
            if order.order:
                customer_name = order.order.customer_name

            pallet_code = ""
            if order.reserved_quantity == 0:
                continue
            stock_left = get_sku_location_stock(wms_code, location, user_id, stock_skus, reserved_skus, stocks,
                                                reserved_instances)
            last_picked_locs = ''
            if location == 'NO STOCK':
                last_picked = pick_stocks.exclude(location__zone__zone='DAMAGED_ZONE').filter(sku__wms_code=wms_code). \
                                  order_by('-updation_date').values_list('location__location',
                                                                         flat=True).distinct()[:2]
                last_picked_locs = ','.join(last_picked)

            data.append(
                {'wms_code': wms_code, 'zone': zone, 'location': location, 'reserved_quantity': order.reserved_quantity,
                 'picklist_number': data_id, 'order_id': str(order.order_id), 'stock_id': st_id,
                 'picked_quantity': order.reserved_quantity, 'id': order.id, 'sequence': sequence,
                 'invoice_amount': order.order.invoice_amount,
                 'price': order.order.invoice_amount * order.reserved_quantity,
                 'image': image, 'status': order.status, 'pallet_code': pallet_code, 'sku_code': order.order.sku_code,
                 'title': order.order.title, 'stock_left': stock_left, 'last_picked_locs': last_picked_locs,
                 'customer_name': customer_name, 'remarks': remarks, 'load_unit_handle': load_unit_handle,
                 'category': category,
                 'marketplace': marketplace})

            if wms_code in sku_total_quantities.keys():
                sku_total_quantities[wms_code] += float(order.reserved_quantity)
            else:
                sku_total_quantities[wms_code] = float(order.reserved_quantity)
        data = sorted(data, key=itemgetter('sequence'))
        return data, sku_total_quantities


def confirm_no_stock(picklist, request, user, picks_all, picklists_send_mail, merge_flag, user_profile,
                     seller_pick_number, val={}, p_quantity=0):
    if float(picklist.reserved_quantity) - p_quantity >= 0:
        picklist.reserved_quantity = float(picklist.reserved_quantity) - p_quantity
        picklist.picked_quantity = float(picklist.picked_quantity) + p_quantity
    else:
        picklist.reserved_quantity = 0
        picklist.picked_quantity = p_quantity
    pi_status = 'picked'
    if 'batch_open' in picklist.status:
        pi_status = 'batch_picked'

    if picklist.order:
        check_and_update_order(picklist.order.user, picklist.order.original_order_id)
    if 'labels' in val.keys() and val['labels'] and picklist.order:
        update_order_labels(picklist, val)
    if float(picklist.reserved_quantity) <= 0:
        picklist.status = pi_status
        if picklist.order and picklist.order.order_type == 'Transit':
            serial_order_mapping(picklist, user)
    picklist.save()
    if not seller_pick_number:
        seller_pick_number = get_seller_pick_id(picklist, user)
    if user_profile.user_type == 'marketplace_user' and picklist.order:
        create_seller_order_summary(picklist, p_quantity, seller_pick_number, picks_all)
    else:
        create_order_summary(picklist, p_quantity, seller_pick_number, picks_all)
    if picklist.picked_quantity > 0 and picklist.order:
        if merge_flag:
            quantity = picklist.picked_quantity
        else:
            quantity = p_quantity
        if picklist.order.order_id in picklists_send_mail.keys():
            if picklist.order.sku.sku_code in picklists_send_mail[picklist.order.order_id].keys():
                qty = float(picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code])
                picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code] = qty + float(quantity)
            else:
                picklists_send_mail[picklist.order.order_id].update({picklist.order.sku.sku_code: float(quantity)})

        else:
            picklists_send_mail.update({picklist.order.order_id: {picklist.order.sku.sku_code: float(quantity)}})
            # picklists_send_mail.append({'order_id': picklist.order.order_id})
            # picklists_send_mail.append(data_count)
            # picklists_send_mail = [{'order_id': str(picklist.order.order_id)}, data_count]
    return seller_pick_number


def validate_location_stock(val, all_locations, all_skus, user):
    status = []
    wms_check = all_skus.filter(wms_code=val['wms_code'], user=user.id)
    loc_check = all_locations.filter(location=val['location'], zone__user=user.id)
    if not loc_check:
        status.append("Invalid Location %s" % val['location'])
    pic_check_data = {'sku__wms_code': val['wms_code'], 'location__location': val['location'], 'sku__user': user.id,
                      'quantity__gt': 0}
    if 'pallet' in val and val['pallet']:
        pic_check_data['pallet_detail__pallet_code'] = val['pallet']
    pic_check = StockDetail.objects.filter(**pic_check_data)
    if not pic_check:
        status.append("Insufficient Stock in given location")
    location = all_locations.filter(location=val['location'], zone__user=user.id)
    if not location:
        if error_string:
            error_string += ', %s' % val['order_id']
        else:
            error_string += "Zone, location match doesn't exists"
        status.append(error_string)
    return pic_check_data, ', '.join(status)


def insert_order_serial(picklist, val, order='', shipped_orders_dict={}):
    if ',' in val['imei']:
        imei_nos = list(set(val['imei'].split(',')))
    else:
        imei_nos = list(set(val['imei'].split('\r\n')))
    user_id = None
    for imei in imei_nos:
        imei_filter = {}
        if order:
            order_id = order.id
        else:
            order_id = picklist.order.id
            order = picklist.order
        if order:
            user_id = order.user
        po_mapping, status, imei_data = check_get_imei_details(imei, val['wms_code'], user_id,
                                                               check_type='order_mapping', order=order)
        # po_mapping = POIMEIMapping.objects.filter(purchase_order__open_po__sku__sku_code=val['wms_code'], imei_number=imei, status=1,
        #                                          purchase_order__open_po__sku__user=user_id)
        imei_mapping = None
        all_seller_pos = SellerPO.objects.filter(seller__user=user_id)
        all_seller_orders = SellerOrder.objects.filter(seller__user=user_id)
        sor_id = ''
        if imei and po_mapping:
            order_mapping = {'order_id': order_id, 'po_imei_id': po_mapping[0].id, 'imei_number': ''}
            if po_mapping[0].purchase_order.open_po_id:
                seller_po = all_seller_pos.filter(open_po_id=po_mapping[0].purchase_order.open_po_id)
                if seller_po:
                    seller_id = seller_po[0].seller_id
                    seller_order_obj = all_seller_orders.filter(order_id=order_id, seller_id=seller_id)
                    if seller_order_obj:
                        sor_id = seller_order_obj[0].sor_id

            order_mapping_ins = OrderIMEIMapping.objects.filter(po_imei_id=po_mapping[0].id, order_id=order_id)
            if order_mapping_ins:
                imei_mapping = order_mapping_ins[0]
                imei_mapping.sor_id = sor_id
                imei_mapping.status = 1
                imei_mapping.save()
                po_imei = order_mapping_ins[0].po_imei
            else:
                order_mapping['sor_id'] = sor_id
                imei_mapping = OrderIMEIMapping(**order_mapping)
                imei_mapping.save()
                po_imei = po_mapping[0]
                log.info('%s imei code is mapped for %s and for id %s' % (str(imei), val['wms_code'], str(order_id)))
            if po_imei:
                po_imei.status = 0
                po_imei.save()
        elif imei and not po_mapping:
            order_mapping = {'order_id': order_id, 'po_imei_id': None, 'imei_number': imei, 'sor_id': sor_id}
            imei_mapping = OrderIMEIMapping(**order_mapping)
            imei_mapping.save()
            log.info('%s imei code is mapped for %s and for id %s' % (str(imei), val['wms_code'], str(order_id)))
        if imei_mapping:
            if shipped_orders_dict.has_key(int(order_id)):
                shipped_orders_dict[int(order_id)]['imeis'].append(imei_mapping)
            else:
                shipped_orders_dict[int(order_id)] = {}
                shipped_orders_dict[int(order_id)]['imeis'] = [imei_mapping]
        ReturnsIMEIMapping.objects.filter(order_return__sku__user=user_id, order_imei__po_imei__imei_number=imei,
                                          imei_status=1).update(imei_status=0)
    return shipped_orders_dict


def update_picklist_pallet(stock, picking_count1):
    pallet = stock.pallet_detail
    if float(pallet.quantity) - picking_count1 >= 0:
        pallet.quantity -= picking_count1
    if pallet.quantity == 0:
        stock.pallet_detail_id = None
        pallet.status = 0
        stock.location.pallet_filled -= 1
        if stock.location.pallet_filled < 0:
            stock.location.pallet_filled = 0
        stock.location.save()
        pallet_mapping = PalletMapping.objects.filter(pallet_detail_id=pallet.id)
        if pallet_mapping:
            pallet_mapping[0].status = 1
            pallet_mapping[0].save()
    pallet.save()


def send_picklist_mail(picklists, request, user, pdf_file, misc_detail, data_qt=""):
    picklist_order_ids_list = []
    reciever = []
    internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='Internal Emails')
    misc_internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='internal_mail', misc_value='true')
    if misc_internal_mail and internal_mail:
        internal_mail = internal_mail[0].misc_value.split(",")
        if 'false' in internal_mail:
            internal_mail.remove('false')
        reciever.extend(internal_mail)
    headers = ['Product Details', 'Ordered Quantity', 'Total']
    items = []
    for picklist in picklists:
        if {picklist.order.order_id: picklist.order.sku.sku_code} in picklist_order_ids_list:
            continue
        if data_qt:
            qty = data_qt.get(picklist.order.sku.sku_code, 0)
            if not qty:
                continue
        else:
            qty = picklist.picked_quantity
        picklist_order_ids_list.append({picklist.order.order_id: picklist.order.sku.sku_code})
        unit_price = float(picklist.order.invoice_amount) / float(picklist.order.quantity)
        items.append([picklist.order.sku.sku_desc, qty, float(qty) * unit_price])
    picklist = picklists[0]

    user_data = UserProfile.objects.get(user_id=user.id);
    data_dict = {'customer_name': picklist.order.customer_name, 'order_id': picklist.order.order_id,
                 'address': picklist.order.address, 'phone_number': picklist.order.telephone, 'all_items': items,
                 'headers': headers, 'query_contact': user_data.phone_number, 'company_name': user_data.company_name}

    t = loader.get_template('templates/dispatch_mail.html')
    rendered = t.render(data_dict)

    if misc_detail:
        email = picklist.order.email_id
        reciever.append(email)
    if reciever:
        try:
            send_mail_attachment(reciever, '%s : Invoice No.%s' % (
            user_data.company_name, 'TI/1116/' + str(picklist.order.order_id)), rendered, files=[pdf_file])
        except:
            log.info('mail issue')


def get_picklist_batch(picklist, value, all_picklists):
    title = value[0]['title']
    if '\r' in title:
        title = str(title).replace('\r', '')
    if picklist.order and picklist.stock:
        picklist_batch = all_picklists.filter(stock__location__location=value[0]['orig_loc'],
                                              stock__sku__wms_code=value[0]['wms_code'],
                                              status__icontains='open', order__title=title)
    elif not picklist.stock:
        picklist_batch = all_picklists.filter(order__sku__sku_code=value[0]['wms_code'], order__title=title,
                                              stock__isnull=True,
                                              picklist_number=picklist.picklist_number)
        if not picklist_batch:
            picklist_batch = all_picklists.filter(sku_code=value[0]['wms_code'], order__title=title, stock__isnull=True,
                                                  picklist_number=picklist.picklist_number)
    else:
        picklist_batch = all_picklists.filter(Q(stock__sku__wms_code=value[0]['wms_code']) | Q(order_type="combo",
                                                                                               sku_code=value[0][
                                                                                                   'wms_code']),
                                              stock__location__location=value[0]['orig_loc'],
                                              status__icontains='open')
    return picklist_batch


def check_and_send_mail(request, user, picklist, picks_all, picklists_send_mail):
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='dispatch', misc_value='true')

    # order_ids = list(set(map(lambda d: d['order_id'], picklists_send_mail[0])))
    order_ids = picklists_send_mail.keys()
    if picklist.order:
        for order_id in order_ids:
            all_picked_items = picks_all.filter(order__order_id=order_id, picked_quantity__gt=0)
            order_ids_list = all_picked_items.values_list('order_id', flat=True)
            if order_ids_list:
                order_ids = [str(int(i)) for i in order_ids_list]
                order_ids = ','.join(order_ids)

            nv_data = get_invoice_data(order_ids, user, picklists_send_mail[order_id])
            nv_data = modify_invoice_data(nv_data, user)
            ord_ids = order_ids.split(",")
            nv_data = add_consignee_data(nv_data, ord_ids, user)
            nv_data.update({'user': user})
            if nv_data['detailed_invoice']:
                t = loader.get_template('../miebach_admin/templates/toggle/detail_generate_invoice.html')
                rendered = t.render(nv_data)
            else:
                # t = loader.get_template('../miebach_admin/templates/toggle/generate_invoice.html')
                nv_data["customer_invoice"] = True
                rendered = build_invoice(nv_data, user, True)
            # rendered = t.render(nv_data)
            file_name = str(user.id) + '_' + 'dispatch_invoice.html'
            pdf_file = '%s_%s.pdf' % (str(user.id), "dispatch_invoice")
            file_ = open(file_name, "w+b")
            file_.write(rendered)
            file_.close()
            os.system("./phantom/bin/phantomjs ./phantom/examples/rasterize.js ./%s ./%s A4" % (file_name, pdf_file))

            send_picklist_mail(all_picked_items, request, user, pdf_file, misc_detail, picklists_send_mail[order_id])
            if picklist.picked_quantity > 0 and picklist.order and misc_detail:
                if picklist.order.telephone:
                    order_dispatch_message(picklist.order, user, picklists_send_mail[order_id])
                else:
                    log.info("No telephone no for this order")


def create_seller_order_summary(picklist, picked_count, pick_number, picks_all, stocks=[]):
    # seller_orders = SellerOrder.objects.filter(order_id=picklist.order_id, order__user=picklist.order.user, status=1)
    seller_order_details = SellerOrderDetail.objects.filter(picklist_id=picklist.id,
                                                            picklist__order__user=picklist.order.user)
    for seller_detail in seller_order_details:
        insert_quan = 0
        if not picked_count:
            break
        if seller_detail.reserved > picked_count:
            insert_quan = picked_count
            picked_count = 0
        elif seller_detail.reserved <= picked_count:
            insert_quan = seller_detail.reserved
            picked_count = picked_count - int(seller_detail.reserved)
        seller_detail.reserved = seller_detail.reserved - insert_quan
        if seller_detail.reserved <= 0:
            seller_detail.status = 0
        seller_detail.save()
        if not picklist.order_type == 'combo':
            SellerOrderSummary.objects.create(picklist_id=picklist.id, pick_number=pick_number, quantity=insert_quan,
                                              seller_order_id=seller_detail.seller_order.id,
                                              creation_date=datetime.datetime.now())
        else:
            combo_picks = picks_all.filter(order_id=picklist.order.id, order_type='combo').values(
                'order__sku__sku_code', 'order_id',
                'stock__sku_id', 'sku_code').distinct().annotate(total_reserved_sum=Sum('reserved_quantity'),
                                                                 total_picked_sum=Sum('picked_quantity'))
            final_picked = []
            seller_order_summary = SellerOrderSummary.objects.filter(picklist__order_id=picklist.order.id,
                                                                     picklist__order__user=picklist.order.user)
            for combo_pick in combo_picks:
                seller_picks = \
                seller_order_summary.filter(picklist__order__sku__sku_code=combo_pick['order__sku__sku_code']). \
                    aggregate(Sum('quantity'))['quantity__sum']
                if not seller_picks:
                    seller_picks = 0
                picked_sum = float(combo_pick['total_picked_sum']) - seller_picks
                final_picked.append(picked_sum)
            if final_picked:
                insert_picked = min(final_picked)
                if insert_picked:
                    SellerOrderSummary.objects.create(picklist_id=picklist.id, pick_number=pick_number,
                                                      quantity=insert_picked,
                                                      seller_order_id=seller_detail.seller_order.id,
                                                      creation_date=datetime.datetime.now())

        for stock in stocks:
            seller_stocks = SellerStock.objects.filter(seller_id=seller_detail.seller_order.seller_id,
                                                       stock_id=stock.id, seller__user=picklist.order.user)
            for seller_stock in seller_stocks:
                if insert_quan <= 0:
                    break
                if float(seller_stock.quantity) < insert_quan:
                    update_quan = float(seller_stock.quantity)
                    insert_quan -= update_quan
                    seller_stock.quantity = 0
                else:
                    update_quan = insert_quan
                    seller_stock.quantity = float(seller_stock.quantity) - insert_quan
                    insert_quan = 0
                seller_stock.save()


def create_order_summary(picklist, picked_count, pick_number, picks_all):
    # seller_orders = SellerOrder.objects.filter(order_id=picklist.order_id, order__user=picklist.order.user, status=1)
    order = picklist.order
    if not order or not picked_count:
        return
    insert_quan = 0
    if order.quantity > picked_count:
        insert_quan = picked_count
        picked_count = 0
    elif order.quantity <= picked_count:
        insert_quan = order.quantity
        picked_count = picked_count - int(order.quantity)
    if not picklist.order_type == 'combo':
        SellerOrderSummary.objects.create(picklist_id=picklist.id, pick_number=pick_number, quantity=insert_quan,
                                          order_id=order.id, creation_date=datetime.datetime.now())
    else:
        combo_picks = picks_all.filter(order_id=picklist.order.id, order_type='combo').values('order__sku__sku_code',
                                                                                              'order_id',
                                                                                              'stock__sku_id',
                                                                                              'sku_code').distinct().annotate(
            total_reserved_sum=Sum('reserved_quantity'),
            total_picked_sum=Sum('picked_quantity'))
        final_picked = []
        seller_order_summary = SellerOrderSummary.objects.filter(picklist__order_id=picklist.order.id,
                                                                 picklist__order__user=picklist.order.user)
        for combo_pick in combo_picks:
            seller_picks = \
            seller_order_summary.filter(picklist__order__sku__sku_code=combo_pick['order__sku__sku_code']). \
                aggregate(Sum('quantity'))['quantity__sum']
            if not seller_picks:
                seller_picks = 0
            picked_sum = float(combo_pick['total_picked_sum']) - seller_picks
            final_picked.append(picked_sum)
        if final_picked:
            insert_picked = min(final_picked)
            if insert_picked:
                SellerOrderSummary.objects.create(picklist_id=picklist.id, pick_number=pick_number,
                                                  quantity=insert_picked,
                                                  order_id=order.id, creation_date=datetime.datetime.now())


def get_seller_pick_id(picklist, user):
    pick_number = 1
    if not picklist.order:
        return ''
    summary = SellerOrderSummary.objects.filter(Q(seller_order__order__order_id=picklist.order.order_id) |
                                                Q(order__order_id=picklist.order.order_id),
                                                picklist__order__user=user.id). \
        order_by('-creation_date')
    if summary:
        pick_number = int(summary[0].pick_number) + 1
    return pick_number


def update_no_stock_to_location(request, user, picklist, val, picks_all, picklist_batch):
    new_update_ids = []
    for picklist in picklist_batch:
        if not picklist.stock:
            pc_upd_ids = update_exist_picklists(picklist.picklist_number, request, user, sku_code=val['wms_code'],
                                                location=val['location'], \
                                                picklist_obj=picklist)
            new_update_ids = list(chain(new_update_ids, pc_upd_ids))
    if new_update_ids:
        picklist_batch = picks_all.filter(id__in=new_update_ids)
    return picklist_batch


def update_order_labels(picklist, val):
    if ',' in val['labels']:
        label_codes = list(set(val['labels'].split(',')))
    else:
        label_codes = list(set(val['labels'].split('\r\n')))
    for label in label_codes:
        order_labels = OrderLabels.objects.filter(order__user=picklist.order.user, label=label)
        for order_label in order_labels:
            order_label.status = 0
            order_label.save()
            log.info('Order Label ' + str(label) + ' is mapped to ' + str(picklist.order.order_id))


@csrf_exempt
@login_required
@get_admin_user
def picklist_confirmation(request, user=''):
    st_time = datetime.datetime.now()
    data = {}
    all_data = {}
    auto_skus = []
    picklists_send_mail = {}
    mod_locations = []
    seller_pick_number = ''
    for key, value in request.POST.iterlists():
        name, picklist_id = key.rsplit('_', 1)
        data.setdefault(picklist_id, [])
        for index, val in enumerate(value):
            if len(data[picklist_id]) < index + 1:
                data[picklist_id].append({})
            data[picklist_id][index][name] = val

    log.info('Request params for ' + user.username + ' is ' + str(data))
    try:
        data = OrderedDict(sorted(data.items(), reverse=True))
        error_string = ''
        picklist_number = request.POST['picklist_number']
        single_order = request.POST.get('single_order', '')
        user_profile = UserProfile.objects.get(user_id=user.id)

        all_picklists = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id),
                                                picklist_number=picklist_number,
                                                status__icontains="open")

        merge_flag = request.POST.get('merge_invoice', '')
        if merge_flag == 'true':
            merge_flag = True
        elif merge_flag == 'false':
            merge_flag = False
        picks_all = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id),
                                            picklist_number=picklist_number)
        all_skus = SKUMaster.objects.filter(user=user.id)
        all_locations = LocationMaster.objects.filter(zone__user=user.id)
        all_pick_ids = all_picklists.values_list('id', flat=True)
        all_pick_locations = PicklistLocation.objects.filter(picklist__picklist_number=picklist_number, status=1,
                                                             picklist_id__in=all_pick_ids)

        for key, value in data.iteritems():
            if key in ('name', 'number', 'order', 'sku', 'invoice'):
                continue
            picklist_batch = ''
            picklist_order_id = value[0]['order_id']
            if picklist_order_id:
                picklist = all_picklists.get(order__order_id=picklist_order_id,
                                             order__sku__sku_code=value[0]['wms_code'])
            elif not key:
                scan_wms_codes = map(lambda d: d['wms_code'], value)
                picklist_batch = picks_all.filter(
                    Q(stock__sku__wms_code__in=scan_wms_codes) | Q(order__sku__wms_code=scan_wms_codes),
                    reserved_quantity__gt=0, status__icontains='open')

            else:
                picklist = picks_all.get(id=key)
            count = 0
            if not picklist_batch:
                picklist_batch = get_picklist_batch(picklist, value, all_picklists)
            for i in range(0, len(value)):
                if value[i]['picked_quantity']:
                    count += float(value[i]['picked_quantity'])

            for val in value:
                if not val['picked_quantity']:
                    continue
                else:
                    count = float(val['picked_quantity'])

                if picklist_order_id:
                    picklist_batch = list(set([picklist]))
                if not val['location'] == 'NO STOCK':
                    picklist_batch = update_no_stock_to_location(request, user, picklist, val, picks_all,
                                                                 picklist_batch)
                for picklist in picklist_batch:
                    if count == 0:
                        continue

                    if val['wms_code'] == 'TEMP' and val.get('wmscode', ''):
                        if picklist.order:
                            map_status = create_market_mapping(picklist.order, val)
                        if map_status == 'true':
                            val['wms_code'] = val['wmscode']
                        elif map_status == 'Invalid WMS Code':
                            return HttpResponse(map_status)
                    status = ''
                    if not val['location'] == 'NO STOCK':
                        pic_check_data, status = validate_location_stock(val, all_locations, all_skus, user)
                    if status:
                        continue
                    if not picklist.stock:
                        if val['location'] == 'NO STOCK':
                            seller_pick_number = confirm_no_stock(picklist, request, user, picks_all,
                                                                  picklists_send_mail, merge_flag, user_profile,
                                                                  seller_pick_number, val=val,
                                                                  p_quantity=float(val['picked_quantity']))
                            continue
                    if float(picklist.reserved_quantity) > float(val['picked_quantity']):
                        picking_count = float(val['picked_quantity'])
                    else:
                        picking_count = float(picklist.reserved_quantity)
                    picking_count1 = 0  # picking_count
                    wms_id = all_skus.exclude(sku_code='').get(wms_code=val['wms_code'], user=user.id)
                    total_stock = StockDetail.objects.filter(**pic_check_data)

                    if 'imei' in val.keys() and val['imei'] and picklist.order:
                        insert_order_serial(picklist, val)
                    if 'labels' in val.keys() and val['labels'] and picklist.order:
                        update_order_labels(picklist, val)
                    reserved_quantity1 = picklist.reserved_quantity
                    tot_quan = 0
                    for stock in total_stock:
                        tot_quan += float(stock.quantity)
                        # if tot_quan < reserved_quantity1:
                        # total_stock = create_temp_stock(picklist.stock.sku.sku_code, picklist.stock.location.zone, abs(reserved_quantity1 - tot_quan), list(total_stock), user.id)

                    seller_stock_objs = []
                    for stock in total_stock:

                        update_picked = 0
                        pre_stock = float(stock.quantity)
                        if picking_count == 0:
                            break

                        if picking_count > stock.quantity:
                            update_picked = float(stock.quantity)
                            picking_count -= stock.quantity
                            picklist.reserved_quantity -= stock.quantity

                            stock.quantity = 0
                        else:
                            update_picked = picking_count
                            stock.quantity -= picking_count
                            picklist.reserved_quantity -= picking_count
                            picking_count = 0

                        if float(stock.location.filled_capacity) - update_picked >= 0:
                            setattr(stock.location, 'filled_capacity',
                                    (float(stock.location.filled_capacity) - update_picked))
                            stock.location.save()

                        pick_loc = all_pick_locations.filter(picklist_id=picklist.id,
                                                             stock__location_id=stock.location_id, status=1)
                        # update_picked = picking_count1
                        if pick_loc:
                            update_picklist_locations(pick_loc, picklist, update_picked)
                        else:
                            data = PicklistLocation(picklist_id=picklist.id, stock=stock, quantity=update_picked,
                                                    reserved=0, status=0,
                                                    creation_date=datetime.datetime.now(),
                                                    updation_date=datetime.datetime.now())
                            data.save()
                            exist_pics = all_pick_locations.exclude(id=data.id).filter(picklist_id=picklist.id,
                                                                                       status=1, reserved__gt=0)
                            update_picklist_locations(exist_pics, picklist, update_picked, 'true')
                        if stock.location.zone.zone == 'BAY_AREA':
                            reduce_putaway_stock(stock, update_picked, user.id)
                        dec_quantity = pre_stock - float(stock.quantity)
                        if stock.pallet_detail:
                            update_picklist_pallet(stock, update_picked)
                        stock.save()
                        seller_stock_objs.append(stock)
                        mod_locations.append(stock.location.location)
                        picking_count1 += update_picked
                    picklist.picked_quantity = float(picklist.picked_quantity) + picking_count1
                    if not seller_pick_number:
                        seller_pick_number = get_seller_pick_id(picklist, user)
                    if user_profile.user_type == 'marketplace_user' and picklist.order:
                        create_seller_order_summary(picklist, picking_count1, seller_pick_number, picks_all,
                                                    seller_stock_objs)
                    else:
                        create_order_summary(picklist, picking_count1, seller_pick_number, picks_all)
                    if picklist.reserved_quantity == 0:

                        # Auto Shipment check and Mapping the serial Number
                        if picklist.order and picklist.order.order_type == 'Transit':
                            serial_order_mapping(picklist, user)
                        if picklist.status == 'batch_open':
                            picklist.status = 'batch_picked'
                        else:
                            picklist.status = 'picked'

                        if picklist.order:
                            check_and_update_order(user.id, picklist.order.original_order_id)
                        all_pick_locations.filter(picklist_id=picklist.id, status=1).update(status=0)

                    picklist.save()
                    picked_status = ""
                    if picklist.picked_quantity > 0 and picklist.order:
                        if merge_flag:
                            quantity = picklist.picked_quantity
                        else:
                            quantity = picking_count1
                        if picklist.order.order_id in picklists_send_mail.keys():
                            if picklist.order.sku.sku_code in picklists_send_mail[picklist.order.order_id].keys():
                                qty = float(picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code])
                                picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code] = qty + float(
                                    quantity)
                            else:
                                picklists_send_mail[picklist.order.order_id].update(
                                    {picklist.order.sku.sku_code: float(quantity)})

                        else:
                            picklists_send_mail.update(
                                {picklist.order.order_id: {picklist.order.sku.sku_code: float(quantity)}})

                            # picklists_send_mail.append({'order_id': picklist.order.order_id})
                            # picklists_send_mail.append(data_count)

                    count = count - picking_count1
                    auto_skus.append(val['wms_code'])

        if get_misc_value('auto_po_switch', user.id) == 'true' and auto_skus:
            auto_po(list(set(auto_skus)), user.id)

        detailed_invoice = get_misc_value('detailed_invoice', user.id)
        if (detailed_invoice == 'false' and picklist.order and picklist.order.marketplace == "Offline"):
            check_and_send_mail(request, user, picklist, picks_all, picklists_send_mail)
        order_ids = picks_all.values_list('order_id', flat=True).distinct()
        if get_misc_value('automate_invoice', user.id) == 'true' and single_order:
            order_ids = picks_all.filter(order__order_id=single_order, picked_quantity__gt=0).values_list('order_id',
                                                                                                          flat=True).distinct()
            order_id = picklists_send_mail.keys()
            if order_ids and order_id:
                ord_id = order_id[0]
                order_ids = [str(int(i)) for i in order_ids]
                order_ids = ','.join(order_ids)
                invoice_data = get_invoice_data(order_ids, user, picklists_send_mail[ord_id])
                invoice_data = modify_invoice_data(invoice_data, user)
                # invoice_data['invoice_no'] = 'TI/1116/' + invoice_data['order_no']
                # invoice_data['invoice_date'] = get_local_date(user, datetime.datetime.now())
                offline_flag = False
                if picklist.order.marketplace == "Offline":
                    offline_flag = True
                invoice_data['offline_flag'] = offline_flag
                invoice_data['picklist_id'] = picklist.id
                invoice_data['picklists_send_mail'] = str(picklists_send_mail)

                invoice_data['order_id'] = invoice_data['order_id']
                user_profile = UserProfile.objects.get(user_id=user.id)
                if not invoice_data['detailed_invoice'] and invoice_data['is_gst_invoice']:
                    invoice_data = build_invoice(invoice_data, user, False)
                    return HttpResponse(invoice_data)
                return HttpResponse(json.dumps({'data': invoice_data, 'status': 'invoice'}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Picklist Confirmation failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(data), str(e)))
        return HttpResponse('Picklist Confirmation Failed')

    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("process completed")
    log.info("total time -- %s" % (duration))

    if mod_locations:
        update_filled_capacity(list(set(mod_locations)), user.id)
    return HttpResponse('Picklist Confirmed')


def serial_order_mapping(picklist, user):
    try:
        order = picklist.order
        original_order_id = order.original_order_id
        if not original_order_id:
            original_order_id = str(order.order_code) + str(order.order_id)
        order_po_mapping = OrderPOMapping.objects.filter(sku__user=user.id, order_id=original_order_id,
                                                         sku_id=order.sku_id, status=1)
        if not order_po_mapping:
            log.info(
                "Order PO Mapping doesn't exists for user %s and for order_id %s" % (user.username, original_order_id))
            return "Mapping not done"
        order_po_mapping = order_po_mapping[0]
        imeis = list(POIMEIMapping.objects.filter(purchase_order__order_id=order_po_mapping.purchase_order_id,
                                                  purchase_order__open_po__sku_id=order_po_mapping.sku_id,
                                                  purchase_order__open_po__sku__user=user.id,
                                                  status=1).values_list('imei_number', flat=True))

        val = {}
        val['wms_code'] = order.sku.wms_code
        val['imei'] = ','.join(imeis)

        # Map Serial Number with Order
        insert_order_serial(picklist, val)

        # Create Shipment automatically
        create_shipment_entry(picklist)

        order_po_mapping.status = 0
        order_po_mapping.save()

        return "Success"

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Something went wrong")
        return "Failed"


def create_shipment_entry(picklist):
    """ create shipment data """
    order = picklist.order
    status = 1
    order_shipment = {}
    shipment_info = {}
    order_packaging = {}
    order_shipment['user'] = order.user
    shipment_number = OrderShipment.objects.filter(user=order.user).aggregate(Max('shipment_number'))[
        'shipment_number__max']
    if not shipment_number:
        shipment_number = 0
    order_shipment['shipment_number'] = shipment_number + 1
    order_shipment['shipment_date'] = datetime.datetime.now()
    order_shipment['shipment_reference'] = 'Auto Generated'
    order_shipment['status'] = status

    order_shipment_obj = OrderShipment(**order_shipment)
    order_shipment_obj.save()

    order_packaging['order_shipment'] = order_shipment_obj
    order_packaging['status'] = status
    order_packaging_obj = OrderPackaging(**order_packaging)
    order_packaging_obj.save()

    shipment_info['order_shipment'] = order_shipment_obj
    shipment_info['order_packaging'] = order_packaging_obj
    shipment_info['order'] = order
    shipment_info['shipping_quantity'] = order.quantity
    shipment_info['status'] = status
    shipment_info_obj = ShipmentInfo(**shipment_info)
    shipment_info_obj.save()
    picklist.status = 'dispatched'
    picklist.save()
    picklist.order.status = 2
    picklist.order.save()


@csrf_exempt
@login_required
@get_admin_user
def update_invoice(request, user=''):
    """ update invoice data """

    try:
        log.info('Request params for Update Invoice for ' + user.username + ' is ' + str(request.POST.dict()))
        resp = {"msg": "success", "data": {}}
        order_ids = request.POST.get("order_id", "")
        consignee = request.POST.get("ship_to", "")
        invoice_date = request.POST.get("invoice_date", "")
        invoice_number = request.POST.get("invoice_number", "")
        increment_invoice = get_misc_value('increment_invoice', user.id)
        marketplace = request.POST.get("marketplace", "")
        order_reference = request.POST.get("order_reference", "")
        order_reference_date = request.POST.get("order_reference_date", "")

        myDict = dict(request.POST.iterlists())
        if invoice_date:
            invoice_date = datetime.datetime.strptime(invoice_date, "%m/%d/%Y").date()
        order_id_val = ''.join(re.findall('\d+', order_ids))
        order_code = ''.join(re.findall('\D+', order_ids))
        ord_ids = OrderDetail.objects.filter(
            Q(order_id=order_id_val, order_code=order_code) | Q(original_order_id=order_ids),
            user=user.id)

        if ord_ids:
            update_dict = {}
            if order_reference:
                update_dict['order_reference'] = order_reference
            if order_reference_date:
                update_dict['order_reference_date'] = datetime.datetime.strptime(order_reference_date,
                                                                                 "%m/%d/%Y").date()
            if update_dict:
                ord_ids.update(**update_dict)

        if increment_invoice == 'true' and invoice_number:
            invoice_sequence = InvoiceSequence.objects.filter(user_id=user.id, marketplace=marketplace)
            if not invoice_sequence:
                invoice_sequence = InvoiceSequence.objects.filter(user_id=user.id, marketplace='')
            seller_orders = SellerOrderSummary.objects.filter(order_id__in=ord_ids, order__user=user.id)
            if seller_orders and int(seller_orders[0].invoice_number) != int(invoice_number):
                if int(invoice_number) >= int(invoice_sequence[0].value) - 1:
                    seller_orders.update(invoice_number=str(invoice_number).zfill(3))
                    invoice_sequence = invoice_sequence[0]
                    invoice_sequence.value = int(invoice_number) + 1
                    invoice_sequence.save()
                else:
                    resp['msg'] = "Invoice number already Exist"
                    return HttpResponse(json.dumps(resp))

        # Updating the Unit Price
        for order_id in ord_ids:
            if not str(order_id.id) in myDict['id']:
                continue

            unit_price_index = myDict['id'].index(str(order_id.id))
            if order_id.unit_price != float(myDict['unit_price'][unit_price_index]):
                order_id.unit_price = float(myDict['unit_price'][unit_price_index])
                order_id.invoice_amount = float(myDict['invoice_amount'][unit_price_index])
                order_id.save()
            cust_objs = CustomerOrderSummary.objects.filter(order__user=user.id, order__id=order_id.id)
            if cust_objs:
                cust_obj = cust_objs[0]
                cust_obj.consignee = consignee
                if invoice_date:
                    cust_obj.invoice_date = invoice_date
                cust_obj.save()

        # Updating or Creating Order other charges Table
        for i in range(0, len(myDict.get('charge_name', []))):
            if myDict.get('charge_id') and myDict['charge_id'][i]:
                order_charges = OrderCharges.objects.filter(id=myDict['charge_id'][i], user_id=user.id)
                if order_charges:
                    if not myDict['charge_amount'][i]:
                        myDict['charge_amount'][i] = 0
                    order_charges.update(charge_name=myDict['charge_name'][i], charge_amount=myDict['charge_amount'][i])
            else:
                OrderCharges.objects.create(order_id=order_ids, charge_name=myDict['charge_name'][i],
                                            charge_amount=myDict['charge_amount'][i],
                                            creation_date=datetime.datetime.now(),
                                            user_id=user.id)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Invoice failed for params for user %s for params %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))
        resp = {"msg": "Failed", "data": {}}

    return HttpResponse(json.dumps(resp))


@csrf_exempt
@login_required
@get_admin_user
def edit_invoice(request, user=''):
    """ The view to edit the invoice """
    order_ids = request.POST.get("order_id", "")
    picklist_id = request.POST.get("picklist_id", "")
    consignee = request.POST.get("consignee", "")
    payment_terms = request.POST.get("credit_period", "")
    dispatch_through = request.POST.get("dispatch_through", "")
    picklists_send_mail = request.POST.get("picklists_send_mail", "")
    invoice_date = request.POST.get("invoice_date", "")
    if invoice_date:
        invoice_date = datetime.datetime.strptime(invoice_date, "%m/%d/%Y").date()
    if picklists_send_mail:
        picklists_send_mail = eval(picklists_send_mail)
    order_id_val = ''.join(re.findall('\d+', order_ids))
    order_code = ''.join(re.findall('\D+', order_ids))
    ord_ids = OrderDetail.objects.filter(
        Q(order_id=order_id_val, order_code=order_code) | Q(original_order_id=order_ids),
        user=user.id).values_list('id', flat=True)
    for order_id in ord_ids:
        cust_objs = CustomerOrderSummary.objects.filter(order__user=user.id, order__id=order_id)
        if cust_objs:
            cust_obj = cust_objs[0]
            cust_obj.consignee = consignee
            cust_obj.payment_terms = payment_terms
            cust_obj.dispatch_through = dispatch_through
            if invoice_date:
                cust_obj.invoice_date = invoice_date
            cust_obj.save()

    picklist_obj = Picklist.objects.filter(order_id__in=ord_ids, order__user=user.id)
    check_and_send_mail(request, user, picklist_obj[0], picklist_obj, picklists_send_mail)

    return HttpResponse('Success')


def add_consignee_data(invoice_data, order_ids, user):
    """ Add Ship to Address and Payment terms"""

    cust_ord_objs = CustomerOrderSummary.objects.filter(order__id__in=order_ids)
    if not cust_ord_objs:
        return invoice_data
    for obj in cust_ord_objs:
        if obj.consignee:
            invoice_data['consignee'] = obj.consignee
        if obj.payment_terms:
            if invoice_data['customer_details']:
                invoice_data['customer_details'][0]['credit_period'] = obj.payment_terms
            else:
                invoice_data['customer_details'] = [{'credit_period': obj.payment_terms}]
        if obj.dispatch_through:
            invoice_data['dispatch_through'] = obj.dispatch_through
            break

    return invoice_data


@csrf_exempt
@login_required
@get_admin_user
def view_picklist(request, user=''):
    show_image = 'false'
    use_imei = 'false'
    data_id = request.GET['data_id']
    single_order = ''
    headers = list(PRINT_OUTBOUND_PICKLIST_HEADERS)
    misc_detail = MiscDetail.objects.filter(user=user.id)
    data = misc_detail.filter(misc_type='show_image')
    if data:
        show_image = data[0].misc_value
    if show_image == 'true':
        headers.insert(0, 'Image')
    imei_data = misc_detail.filter(misc_type='use_imei')
    if imei_data:
        use_imei = imei_data[0].misc_value
    if use_imei == 'true':
        headers.insert(-1, 'Serial Number')
    pallet_switch = get_misc_value('pallet_switch', user.id)
    if pallet_switch == 'true':
        headers.insert(headers.index('Location') + 1, 'Pallet Code')
    data, sku_total_quantities = get_picklist_data(data_id, user.id)
    if data[0]['status'] == 'open':
        headers.insert(headers.index('WMS Code'), 'Order ID')
        order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
        order_count_len = len(filter(lambda x: len(str(x)) > 0, order_count))
        if order_count_len == 1:
            single_order = str(order_count[0])

    return HttpResponse(json.dumps({'data': data, 'picklist_id': data_id,
                                    'show_image': show_image, 'use_imei': use_imei,
                                    'order_status': data[0]['status'], 'user': request.user.id,
                                    'single_order': single_order,
                                    'sku_total_quantities': sku_total_quantities}))


@csrf_exempt
@login_required
@get_admin_user
def view_picked_orders(request, user=''):
    data_id = request.GET['data_id']
    marketplace = request.GET.get('market_place', '')
    data = get_picked_data(data_id, user.id, marketplace)
    headers = PICKLIST_HEADER
    show_image = get_misc_value('show_image', user.id)
    if show_image == 'true' and 'Image' not in headers:
        headers = list(headers)
        headers.insert(0, 'Image')
    return HttpResponse(
        json.dumps({'data': data, 'picklist_id': data_id, 'show_image': show_image}, cls=DjangoJSONEncoder))


def get_picked_data(data_id, user, marketplace=''):
    pick_filter = {'picklist_number': data_id, 'picked_quantity__gt': 0}
    if marketplace:
        pick_filter['order__marketplace'] = marketplace

    picklist_orders = Picklist.objects.filter(Q(order__sku__user=user) | Q(stock__sku__user=user), **pick_filter). \
        exclude(picked_quantity=0, reserved_quantity=0)
    data = []
    for order in picklist_orders:
        if not order.stock:
            wms_code = order.order.sku.wms_code
            if order.order_type == 'combo' and order.sku_code:
                wms_code = order.sku_code
            data.append({'wms_code': wms_code, 'zone': 'NO STOCK', 'location': 'NO STOCK',
                         'reserved_quantity': order.reserved_quantity, 'picked_quantity': order.picked_quantity,
                         'stock_id': 0, 'picklist_number': data_id, 'id': order.id, 'order_id': order.order.order_id,
                         'image': '', 'title': order.order.title, 'order_detail_id': order.order_id,
                         'image': order.order.sku.image_url})
            continue

        picklist_location = PicklistLocation.objects.filter(
            Q(picklist__order__sku__user=user) | Q(stock__sku__user=user), picklist_id=order.id).exclude(reserved=0,
                                                                                                         quantity=0)
        for loc in picklist_location:
            if order.picked_quantity > 0:
                stock_detail = StockDetail.objects.get(id=loc.stock_id, sku__user=user)
                if order.picked_quantity == 0:
                    continue
                wms_code = order.stock.sku.wms_code
                if order.order:
                    order_id = order.order.order_id
                    title = order.order.title
                else:
                    st_order = STOrder.objects.filter(picklist_id=order.id)
                    order_id = st_order[0].stock_transfer.order_id
                    title = st_order[0].stock_transfer.sku.sku_desc
                if wms_code == 'TEMP':
                    wms_code = order.order.sku_code

                loc_quantity = loc.quantity - loc.reserved
                data.append({'wms_code': wms_code, 'zone': stock_detail.location.zone.zone,
                             'location': stock_detail.location.location, 'reserved_quantity': loc.reserved,
                             'picked_quantity': loc_quantity, 'stock_id': loc.stock_id, 'picklist_number': data_id,
                             'id': order.id, 'order_id': order_id, 'image': order.stock.sku.image_url, 'title': title,
                             'order_detail_id': order.order_id})
    return data


@csrf_exempt
@get_admin_user
def get_awb_marketplaces(request, user=''):
    api_status = False
    marketplace = ''
    courier_name = ''
    status = int(request.GET.get('status', 0))
    awb_marketplace = OrderAwbMap.objects.exclude(marketplace='').filter(status=status, user_id=user.id)
    if awb_marketplace:
        marketplace = list(awb_marketplace.values_list('marketplace', flat=True).distinct())
        courier_name = list(awb_marketplace.values_list('courier_name', flat=True).distinct())
        api_status = True
    return HttpResponse(json.dumps({'status': api_status, 'marketplaces': marketplace,
                                    'courier_name': courier_name}))


@csrf_exempt
@get_admin_user
def get_courier_name_for_marketplaces(request, user=''):
    api_status = False
    marketplace = request.GET.get('marketplace', '')
    status = int(request.GET.get('status', 0))
    if not marketplace:
        awb_marketplace = OrderAwbMap.objects.exclude(marketplace='').filter(status=status, user_id=user.id)
    else:
        awb_marketplace = OrderAwbMap.objects.filter(marketplace=marketplace, status=status, user_id=user.id)
    if awb_marketplace:
        courier_name = list(awb_marketplace.values_list('courier_name', flat=True).distinct())
        api_status = True
    return HttpResponse(json.dumps({'status': api_status, 'courier_name': courier_name}))


@csrf_exempt
@get_admin_user
def get_awb_view_shipment_info(request, user=''):
    sku_grouping = request.GET.get('sku_grouping', 'false')
    datatable_view = request.GET.get('view', '')
    search_params = {'user': user.id}
    awb_no = request.GET.get('awb_no', '')
    marketplace = request.GET.get('marketplace', [])
    courier_name = request.GET.get('courier_name', [])
    message = ''
    if awb_no:
        order_awb_map = OrderAwbMap.objects.filter(awb_no=awb_no, status=2, user=user).values('original_order_id')
        if courier_name:
            order_awb_map = order_awb_map.filter(courier_name=courier_name)
        if marketplace:
            order_awb_map = order_awb_map.filter(marketplace=marketplace)
            if not order_awb_map:
                message = 'Invalid AWB No. for this Marketplace'
        if order_awb_map.count():
            order_id_val = order_awb_map[0]['original_order_id']
        else:
            if not message:
                message = 'Incorrect AWB No.'
            return HttpResponse(json.dumps({'status': False, 'message': message}))
        order_id_search = ''.join(re.findall('\d+', order_id_val))
        order_code_search = ''.join(re.findall('\D+', order_id_val))
        all_orders = OrderDetail.objects.filter(
            Q(order_id=order_id_search, order_code=order_code_search) | Q(original_order_id=order_id_val), user=user.id,
            status=1)
        if not all_orders:
            return HttpResponse(json.dumps({'status': status, 'message': message}))
        tracking = ShipmentTracking.objects.filter(shipment__order__in=all_orders,
                                                   ship_status__in=['Dispatched', 'In Transit'],
                                                   shipment__order__user=user.id).values_list('shipment_id')
        if tracking.count():
            ship_info_id = ShipmentInfo.objects.filter(order__in=all_orders, order__user=user.id,
                                                       id__in=tracking)
            for ship_info in ship_info_id:
                try:
                    ShipmentTracking.objects.create(shipment_id=ship_info.id, ship_status='Out for Delivery',
                                                    creation_date=datetime.datetime.now())
                except:
                    import traceback
                    log.debug(traceback.format_exc())
                    log.info('Duplicate Entry %s for Shipment Tracking' % (str(user.username)))
                    return HttpResponse(json.dumps({'status': False, 'message': 'Error Occured'}))
                orig_ship_ref = ship_info.order_packaging.order_shipment.shipment_reference
                order_shipment = ship_info.order_packaging.order_shipment
                order_shipment.shipment_reference = orig_ship_ref
                order_shipment.save()
                order_awb_map.update(status=3)
        else:
            return HttpResponse(json.dumps({'status': False, 'message': 'AWB No. Not Found'}))
    return HttpResponse(json.dumps({'status': True, 'message': 'Shipped - Out for Delivery Successfully'}))


@csrf_exempt
@get_admin_user
def get_awb_shipment_details(request, user=''):
    data = {}
    sku_grouping = request.GET.get('sku_grouping', 'false')
    datatable_view = request.GET.get('view', '')
    search_params = {'user': user.id}
    awb_no = request.GET.get('awb_no', '');
    marketplace = request.GET.get('marketplace', '')
    courier_name = request.GET.get('courier_name', '')
    message = ''
    if awb_no:
        order_awb_map = OrderAwbMap.objects.filter(awb_no=awb_no, status=1, user=user).values('original_order_id')
        if courier_name:
            order_awb_map = order_awb_map.filter(courier_name=courier_name)
        if marketplace:
            order_awb_map = order_awb_map.filter(marketplace=marketplace)
            if not order_awb_map:
                message = 'Invalid AWB No. for this Marketplace'
        if order_awb_map.count():
            data['order_id'] = order_awb_map[0]['original_order_id']
        else:
            if not message:
                message = 'Incorrect AWB No.'
            return HttpResponse(json.dumps({'status': False, 'message': 'Incorrect AWB No.'}))
        result_data = 'No Orders found'
        status = False
        order_id_val = data['order_id']
        order_id_search = ''.join(re.findall('\d+', data['order_id']))
        order_code_search = ''.join(re.findall('\D+', data['order_id']))
        all_orders = OrderDetail.objects.filter(
            Q(order_id=order_id_search, order_code=order_code_search) | Q(original_order_id=order_id_val), user=user.id,
            status=0)
        if not all_orders:
            return HttpResponse(json.dumps({'status': status, 'message': message}))
        ship_no = get_shipment_number(user)
        ship_orders_data = get_shipment_quantity_for_awb(user, all_orders)
        if ship_orders_data:
            result = {'data': ship_orders_data, 'shipment_id': '', 'display_fields': '', 'marketplace': '',
                      'shipment_number': ship_no}
            result_data = awb_direct_insert_shipment_info(result, order_awb_map, user)
            status = result_data['status']
            message = result_data['message']
    return HttpResponse(json.dumps({'status': status, 'message': message}))


def awb_create_shipment(request, user):
    data_dict = copy.deepcopy(ORDER_SHIPMENT_DATA)
    for key, value in request.iteritems():
        if key in ('customer_id', 'marketplace'):
            continue
        elif key in ORDER_SHIPMENT_DATA.keys():
            data_dict[key] = value
    data_dict['user'] = user.id
    data_dict['shipment_date'] = datetime.datetime.now()
    data = OrderShipment(**data_dict)
    data.save()
    return data


def awb_direct_insert_shipment_info(data_params, order_awb_obj, user=''):
    ''' Create Shipment Code '''
    ship_data = data_params['data'];
    user_profile = UserProfile.objects.filter(user_id=user.id)
    try:
        order_shipment = awb_create_shipment(data_params, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create shipment failed for params ' + str(data) + ' error statement is ' + str(e))
        return 'Create shipment Failed'
    status = False
    message = 'Shipment Creation Failed'
    try:
        shipped_orders_dict = {}
        for i in range(0, len(ship_data)):
            if not ship_data[i]['shipping_quantity']:
                continue
            order_ids = ship_data[i]['id']
            if not isinstance(order_ids, list):
                order_ids = [order_ids]
            received_quantity = int(ship_data[i]['shipping_quantity'])
            for order_id in order_ids:
                if received_quantity <= 0:
                    break
                invoice_number = ''
                data_dict = copy.deepcopy(ORDER_PACKAGING_FIELDS)
                shipment_data = copy.deepcopy(SHIPMENT_INFO_FIELDS)
                order_detail = OrderDetail.objects.get(id=order_id, user=user.id, status=0)

                for key, value in ship_data[i].iteritems():
                    if key in data_dict:
                        data_dict[key] = value
                    if key in shipment_data and key != 'id':
                        shipment_data[key] = value

                # Need to comment below 3 lines if shipment scan is ready
                if 'imei_number' in ship_data[i].keys() and ship_data[i]['imei_number']:
                    shipped_orders_dict = insert_order_serial([], {'wms_code': order_detail.sku.wms_code,
                                                                   'imei': ship_data[i]['imei_number']},
                                                              order=order_detail,
                                                              shipped_orders_dict=shipped_orders_dict)
                # Until Here
                order_pack_instance = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id,
                                                                    order_shipment__user=user.id)
                if not order_pack_instance:
                    data_dict['order_shipment_id'] = order_shipment.id
                    data = OrderPackaging(**data_dict)
                    data.save()
                else:
                    data = order_pack_instance[0]
                picked_orders = Picklist.objects.filter(order_id=order_id, status__icontains='picked',
                                                        order__user=user.id)
                order_quantity = int(order_detail.quantity)
                if order_quantity == 0:
                    continue
                elif order_quantity < received_quantity:
                    shipped_quantity = order_quantity
                    received_quantity -= order_quantity
                elif order_quantity >= received_quantity:
                    shipped_quantity = received_quantity
                    received_quantity = 0

                shipment_data['order_shipment_id'] = order_shipment.id
                shipment_data['order_packaging_id'] = data.id
                shipment_data['order_id'] = order_id
                shipment_data['shipping_quantity'] = shipped_quantity
                shipment_data['invoice_number'] = invoice_number
                ship_data = ShipmentInfo(**shipment_data)
                ship_data.save()

                default_ship_track_status = 'Dispatched'
                tracking = ShipmentTracking.objects.filter(shipment_id=ship_data.id, shipment__order__user=user.id,
                                                           ship_status=default_ship_track_status)
                if not tracking:
                    ShipmentTracking.objects.create(shipment_id=ship_data.id, ship_status=default_ship_track_status,
                                                    creation_date=datetime.datetime.now())

                # Need to comment below lines if shipment scan is ready
                if shipped_orders_dict.has_key(int(order_id)):
                    shipped_orders_dict[int(order_id)].setdefault('quantity', 0)
                    shipped_orders_dict[int(order_id)]['quantity'] += float(shipped_quantity)
                else:
                    shipped_orders_dict[int(order_id)] = {}
                    shipped_orders_dict[int(order_id)]['quantity'] = float(shipped_quantity)
                # Until Here

                log.info('Shipemnt Info dict is ' + str(shipment_data))
                ship_quantity = ShipmentInfo.objects.filter(order_id=order_id). \
                    aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
                if not ship_quantity:
                    ship_quantity = 0
                if order_quantity == ship_quantity:
                    order_awb_map = OrderAwbMap.objects.filter(original_order_id=order_detail.original_order_id,
                                                               user=user)
                    if order_awb_map.count():
                        order_awb_map.update(status=2)
                    else:
                        original_order_id = str(order_detail.order_code) + str(order_detail.order_id)
                        order_awb_map = OrderAwbMap.objects.filter(original_order_id=original_order_id, user=user)
                        if order_awb_map.count():
                            order_awb_map.update(status=2)
                if ship_quantity >= int(order_detail.quantity):
                    order_detail.status = 2
                    order_detail.save()
                    for pick_order in picked_orders:
                        setattr(pick_order, 'status', 'dispatched')
                        pick_order.save()
        # Need to comment below lines if shipment scan is ready
        if shipped_orders_dict:
            log.info('Order Status update call for user ' + str(user.username) + ' is ' + str(shipped_orders_dict))
            check_and_update_order_status(shipped_orders_dict, user)
            message = 'Shipment Created Successfully'
            status = True
            # Until Here
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Shipment info saving is failed for params ' + str(data) + ' error statement is ' + str(e))

    return {'status': status, 'message': message}


@csrf_exempt
@get_admin_user
def get_customer_sku(request, user=''):
    data = []
    sku_grouping = request.GET.get('sku_grouping', 'false')
    datatable_view = request.GET.get('view', '')
    search_params = {'user': user.id}
    headers = ('', 'SKU Code', 'Order Quantity', 'Shipping Quantity', 'Pack Reference', '')
    request_data = dict(request.GET.iterlists())
    if 'order_id' in request_data.keys() and not datatable_view == 'ShipmentPickedAlternative':
        search_params['id__in'] = request_data['order_id']
    elif 'order_id' in request_data.keys() and request_data['order_id']:
        filter_order_ids = []
        for order_ids in request_data['order_id']:
            order_id_val = order_ids
            order_id_search = ''.join(re.findall('\d+', order_id_val))
            order_code_search = ''.join(re.findall('\D+', order_id_val))
            fil_ids = list(OrderDetail.objects.filter(Q(order_id=order_id_search, order_code=order_code_search) |
                                                      Q(original_order_id=order_id_val), user=user.id).values_list('id',
                                                                                                                   flat=True))
            filter_order_ids = list(chain(filter_order_ids, fil_ids))
        if filter_order_ids:
            search_params['id__in'] = filter_order_ids
    ship_no = get_shipment_number(user)

    all_orders = OrderDetail.objects.filter(**search_params)
    data = get_shipment_quantity(user, all_orders, sku_grouping)

    if data:
        return HttpResponse(json.dumps({'data': data,
                                        'shipment_id': '',
                                        'display_fields': '',
                                        'marketplace': '', 'shipment_number': ship_no}, cls=DjangoJSONEncoder))
    return HttpResponse(json.dumps({'status': 'No Orders found'}))


@login_required
@get_admin_user
def check_imei(request, user=''):
    ''' Check IMEI status and serial number mapping with order if it is shipment '''
    status = ''
    sku_code = ''
    quantity = 0
    shipped_orders_dict = {}
    is_shipment = request.GET.get('is_shipment', False)
    order_id = request.GET.get('order_id', '')
    groupby = request.GET.get('groupby', '')
    log.info('Request params for Check IMEI ' + user.username + ' is ' + str(request.GET.dict()))
    shipping_quantity = 0
    try:
        for key, value in request.GET.iteritems():
            if key in ['is_shipment', 'order_id', 'groupby']:
                continue
            sku_code = ''
            order = None
            imei_filter = {'imei_number': value, 'purchase_order__open_po__sku__user': user.id}
            if not is_shipment and not key == 'serial':
                picklist = Picklist.objects.get(id=key)
                if not picklist.order:
                    continue
                sku_code = picklist.order.sku.sku_code
                order = picklist.order
                # imei_filter['purchase_order__open_po__sku__sku_code'] = sku_code

            po_mapping, status, imei_data = check_get_imei_details(value, sku_code, user.id, check_type='order_mapping',
                                                                   order=order)
            if imei_data.get('wms_code', ''):
                sku_code = imei_data['wms_code']

            if not sku_code and po_mapping and po_mapping[0].purchase_order.open_po:
                sku_code = po_mapping[0].purchase_order.open_po.sku.sku_code
            if not po_mapping:
                status = str(value) + ' is invalid Imei number'
            order_mapping = OrderIMEIMapping.objects.filter(po_imei__imei_number=value, order__user=user.id, status=1)
            if order_mapping:
                if order and order_mapping[0].order_id == order.id:
                    status = str(value) + ' is already mapped with this order'
                else:
                    status = str(value) + ' is already mapped with another order'
            if is_shipment and po_mapping:
                seller_id = ''
                seller_po = SellerPO.objects.filter(open_po_id=po_mapping[0].purchase_order.open_po_id)
                if seller_po:
                    seller_id = seller_po[0].seller_id
                order_detail_objs = get_order_detail_objs(order_id, user, search_params={}, all_order_objs=[])
                order_details = order_detail_objs.filter(sku__sku_code=sku_code)
                if order_detail_objs and seller_id:
                    seller_order = SellerOrder.objects.filter(seller__user=user.id,
                                                              order_id__in=order_detail_objs.values_list('id'),
                                                              seller_id=seller_id)
                    if not seller_order:
                        status = 'IMEI Mapped to another Seller'
                if order_details:
                    # qty_data = get_shipment_quantity(user, order_details, False)
                    # if qty_data:
                    #    quantity = qty_data[0]['picked']
                    #    shipping_quantity = qty_data[0].get('shipping_quantity', 0)
                    #    if (float(shipping_quantity) + 1) > quantity:
                    #        status = 'Scanned Quantity exceeding the Picked quantity'

                    if not int(order_details[0].sku_id) == int(po_mapping[0].purchase_order.open_po.sku_id):
                        status = 'IMEI Mapped to the another SKU ' + str(
                            po_mapping[0].purchase_order.open_po.sku.sku_code)
                        # if not status:
                        #    order = order_details[0]
                        #    shipped_orders_dict = insert_order_serial([], {'wms_code': order.sku.wms_code,
                        #                                                   'imei': po_mapping[0].imei_number}, order=order,
                        #                                                   shipped_orders_dict=shipped_orders_dict)
                        #    shipped_orders_dict.setdefault(int(order.id), {}).setdefault('quantity', 0)
                        #    shipped_orders_dict[int(order.id)]['quantity'] += 1
                        #    shipping_quantity += 1
                if not status:
                    status = 'Success'

        if shipped_orders_dict:
            log.info('Order Status update call for user ' + str(user.username) + ' is ' + str(shipped_orders_dict))
            check_and_update_order_status(shipped_orders_dict, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Check IMEI failed for params ' + str(request.POST.dict()) + ' error statement is ' + str(e))
    return HttpResponse(json.dumps({'status': status, 'data': {'sku_code': sku_code, 'quantity': quantity,
                                                               'shipping_quantity': shipping_quantity}}))


@get_admin_user
def print_picklist_excel(request, user=''):
    headers = copy.deepcopy(PICKLIST_EXCEL)
    data_id = request.GET['data_id']
    data, sku_total_quantities = get_picklist_data(data_id, user.id)
    all_data = []
    for dat in data:
        val = itemgetter(*headers.values())(dat)
        temp = OrderedDict(zip(headers.keys(), val))
        all_data.append(temp)
    path = print_excel(request, {'aaData': all_data}, headers.keys(), str(data_id))
    return HttpResponse(path)


@get_admin_user
def print_picklist(request, user=''):
    temp = []
    title = 'Picklist ID'
    data_id = request.GET['data_id']
    data, sku_total_quantities = get_picklist_data(data_id, user.id)
    date_data = {}
    picklist_orders = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id),
                                              picklist_number=data_id)
    if picklist_orders:
        date = get_local_date(request.user, picklist_orders[0].creation_date, True)
        date_data['date'] = date.strftime("%d/%m/%Y")
        date_data['time'] = date.strftime("%I:%M%p")
    all_data = {}
    customer_name = ''
    customer_data = list(set(map(lambda d: d.get('customer_name', ''), data)))
    customer_data = filter(lambda x: len(x) > 0, customer_data)
    if customer_data:
        customer_name = ','.join(customer_data)
    order_ids = ''
    order_data = list(set(map(lambda d: d.get('order_no', ''), data)))
    order_data = filter(lambda x: len(x) > 0, order_data)

    remarks_data = ''
    remarks_data = list(set(map(lambda d: d.get('remarks', ''), data)))
    remarks_data = filter(lambda x: len(x) > 0, remarks_data)
    if remarks_data:
        remarks_data = ','.join(remarks_data)
    market_place = list(set(map(lambda d: d.get('marketplace', ''), data)))
    filtered_market = filter(lambda a: a != "Offline", market_place)
    if not filtered_market:
        marketplace = ""
    else:
        marketplace = ','.join(market_place)

    if order_data:
        order_ids = ','.join(order_data)
    total = 0
    total_price = 0
    type_mapping = SkuTypeMapping.objects.filter(user=user.id)
    for record in data:
        for mapping in type_mapping:
            if mapping.prefix in record['wms_code']:
                cond = (mapping.item_type)
                all_data.setdefault(cond, [0, 0])
                all_data[cond][0] += record['reserved_quantity']
                if not record['order_id'] in temp:
                    all_data[cond][1] += record['invoice_amount']
                    temp.append(record['order_id'])
                break
        else:
            total += record['reserved_quantity']
            if not record['order_id'] in temp:
                total_price += record['invoice_amount']
                temp.append(record['order_id'])

    for key, value in all_data.iteritems():
        total += float(value[0])
        total_price += float(value[1])
    return render(request, 'templates/toggle/print_picklist.html',
                  {'data': data, 'all_data': all_data, 'headers': PRINT_OUTBOUND_PICKLIST_HEADERS,
                   'picklist_id': data_id, 'total_quantity': total,
                   'total_price': total_price, 'picklist_id': data_id,
                   'customer_name': customer_name, 'order_ids': order_ids,
                   'marketplace': marketplace, 'date_data': date_data, 'remarks': remarks_data})


@csrf_exempt
def get_batch_picked(data_ids, user_id):
    data = {}
    batch_data = {}
    for data_id in data_ids:
        picklist_orders = Picklist.objects.filter(Q(stock__sku__user=user_id) | Q(order__user=user_id),
                                                  picklist_number=data_id)
        if picklist_orders[0].status != 'batch_picked':
            return data

        for order in picklist_orders:
            wms_code = ''
            if order.stock:
                wms_code = order.stock.sku.wms_code
            elif order.order:
                wms_code = order.order.sku.wms_code
            if order.order:
                marketplace = order.order.marketplace
                invoice_amount = order.order.invoice_amount
            else:
                st_order = STOrder.objects.filter(picklist_id=order.id)
                marketplace = ''
                invoice_amount = st_order[0].stock_transfer.invoice_amount
            if order.picked_quantity <= 0:
                continue
            match_condition = (marketplace, wms_code)
            if match_condition not in batch_data:

                batch_data[match_condition] = {'wms_code': wms_code, 'picked_quantity': order.picked_quantity,
                                               'invoice_amount': invoice_amount}
            else:
                batch_data[match_condition]['invoice_amount'] += invoice_amount
                batch_data[match_condition]['picked_quantity'] += order.picked_quantity

    for key, value in batch_data.iteritems():
        data.setdefault(key[0], [])
        data[key[0]].append(value)

    return data


@csrf_exempt
@login_required
@get_admin_user
def marketplace_segregation(request, user=''):
    data_id = request.GET.get('data_id', [])
    data = get_batch_picked(data_id.split(','), user.id)
    return render(request, 'templates/toggle/print_segregation.html', {'data': data, 'picklist_number': data_id,
                                                                       'headers': ('WMS Code', 'Picked Quantity',
                                                                                   'invoice_amount')})


@get_admin_user
def get_orders(request, orders, user=''):
    data = []
    users = ''
    user_list = []
    options = {}
    for order in orders:
        admin_user = UserGroups.objects.filter(Q(admin_user_id=user.id) | Q(user_id=user.id))
        if not admin_user:
            break
        admin_user = admin_user[0].admin_user
        user_list.append(admin_user)
        wms_users = UserGroups.objects.filter(admin_user_id=user.id)
        for u in wms_users:
            user_list.append(u.user)
        for w_user in user_list:
            if user.id == w_user.id:
                continue
            total_quantity = 0
            order_quantity = 0
            reserved_quantity = 0
            sku_master = SKUMaster.objects.filter(sku_code=order.sku.sku_code, user=w_user.id)
            stock_data = StockDetail.objects.filter(sku__user=w_user.id, sku__sku_code=order.sku.sku_code).aggregate(
                Sum('quantity'))
            order_data = OrderDetail.objects.filter(user=w_user.id, sku__sku_code=order.sku.sku_code,
                                                    status=1).aggregate(Sum('quantity'))
            reserved = PicklistLocation.objects.filter(picklist__status__icontains='open',
                                                       picklist__order__user=w_user.id,
                                                       picklist__order__sku__sku_code=order.sku.sku_code).aggregate(
                Sum('reserved'))
            if None not in stock_data.values():
                total_quantity = stock_data['quantity__sum']
            if None not in order_data.values():
                order_quantity = order_data['quantity__sum']
            if None not in reserved.values():
                reserved_quantity = reserved['reserved__sum']
            quantity = total_quantity - order_quantity - reserved_quantity
            if sku_master:
                options[w_user.username] = quantity

        data.append({'order_id': order.order_id, 'wms_code': order.sku.wms_code, 'title': order.sku.sku_desc,
                     'quantity': order.quantity, 'id': order.id})

    return (data, options)


@csrf_exempt
@login_required
@get_admin_user
def transfer_order(request, user=''):
    headers = ['Order ID', 'WMS Code', 'Title', 'Quantity', 'Transfer To']
    orders = []
    for key, value in request.POST.iteritems():
        order = OrderDetail.objects.get(id=key, user=user.id, status=1)
        orders.append(order)

    data, options = get_orders(request, orders)
    if not data:
        return HttpResponse("No Users Found")
    return HttpResponse(json.dumps({'data': data, 'options': options}))


@csrf_exempt
@login_required
@get_admin_user
def batch_transfer_order(request, user=''):
    orders = []
    headers = ['Order ID', 'WMS Code', 'Title', 'Quantity', 'Transfer To']
    for key, value in request.POST.iteritems():
        batch_orders = OrderDetail.objects.filter(sku__sku_code=key, user=user.id, status=1)
        for order in batch_orders:
            orders.append(order)

    data, options = get_orders(request, orders)
    if not data:
        return HttpResponse("No Users Found")

    return HttpResponse(json.dumps({'data': data, 'options': options}))


@csrf_exempt
@login_required
@get_admin_user
def confirm_transfer(request, user=''):
    for key, value in request.POST.iteritems():
        stock = re.findall('\\d+', value)[-1]
        username = value.split('(')[0].strip()
        order = OrderDetail.objects.filter(id=key, user=user.id)
        if not order:
            continue
        order = order[0]
        user = User.objects.get(username=username)
        sku_master = SKUMaster.objects.get(sku_code=order.sku.sku_code, user=user.id)
        setattr(order, 'user', user.id)
        setattr(order, 'sku_id', sku_master.id)
        order.save()

    return HttpResponse('Order Transferred Successfully')


@csrf_exempt
@login_required
@get_admin_user
def st_generate_picklist(request, user=''):
    out_of_stock = []
    picklist_number = get_picklist_number(user)

    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
        location__zone__zone='DAMAGED_ZONE').filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(status=1, user=user.id, quantity__gt=0)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
            'receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
            'location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    sku_stocks = stock_detail1 | stock_detail2
    for key, value in request.POST.iteritems():
        order_data = StockTransfer.objects.filter(id=value)
        stock_status, picklist_number = picklist_generation(order_data, request, picklist_number, user, sku_combos,
                                                            sku_stocks)

        if stock_status:
            out_of_stock = out_of_stock + stock_status

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    order_status = ''
    data, sku_total_quantities = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']

    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status,
                                    'order_status': order_status}))


@csrf_exempt
@get_admin_user
def get_customer_data(request, user=''):
    data_id = request.GET['id']
    try:
        data_id = int(data_id)
    except:
        return HttpResponse('')
    cust_details = CustomerMaster.objects.filter(customer_id=data_id, user=user.id)
    if cust_details:
        data = cust_details[0]
        return HttpResponse(json.dumps({'name': data.name, 'phone_number': data.phone_number, 'email_id': data.email_id,
                                        'address': data.address}))
    else:
        return HttpResponse('')


@fn_timer
def validate_order_form(myDict, request, user):
    invalid_skus = []
    invalid_quantities = []
    less_stocks = []

    # Purchase Order checks
    po_status = ''
    po_imeis = []

    status = ''
    direct_dispatch = request.POST.get('direct_dispatch', '')
    if not myDict['shipment_date'][0]:
        status = 'Shipment Date should not be empty'
    seller_id = request.POST.get('seller_id', '')
    seller_status = ""
    sor_id_status = ""
    if request.POST.has_key('seller_id'):
        if not seller_id:
            seller_status = 'Seller should not be emtpy'
        else:
            seller_data = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
            if not seller_data:
                seller_status = 'Seller not found'
        sor_id = request.POST.get('sor_id', '')
        if not sor_id:
            sor_id_status = 'SOR ID should not be emtpy'
        else:
            seller_order = SellerOrder.objects.filter(order__user=user.id, sor_id=sor_id)
            if seller_order:
                sor_id_status = 'SOR ID already userd'
    sku_masters = SKUMaster.objects.filter(user=user.id).values('sku_code', 'wms_code', 'id', 'sku_desc')
    all_sku_codes = {}
    if myDict.get('po_number', '') and myDict['po_number'][0]:
        po_number = myDict['po_number'][0]
        if '_' in po_number:
            po_number = po_number.split('_')[-1]
            po_imei_objs = POIMEIMapping.objects.filter(purchase_order__order_id=po_number,
                                                        purchase_order__open_po__sku__user=user.id)
            po_imeis = dict(po_imei_objs.values_list('purchase_order__open_po__sku__sku_code').annotate(Count('id')))

            if not po_imeis:
                po_status = "Purchase Order does not exists"

            elif seller_id:
                seller_po = SellerPO.objects.filter(seller__user=user.id,
                                                    open_po_id=po_imei_objs[0].purchase_order.open_po_id)
                if seller_po and str(seller_po[0].seller.seller_id) != str(seller_id):
                    po_status = "Purchase Order Mapped to another Seller"
        else:
            po_status = "Invalid Purchase Order Number"

    for i in range(0, len(myDict['sku_id'])):
        if not myDict['sku_id'][i]:
            continue
        stock_check = True
        sku_master = sku_masters.filter(Q(sku_code=myDict['sku_id'][i]) | Q(wms_code=myDict['sku_id'][i]))
        if not sku_master:
            invalid_skus.append(myDict['sku_id'][i])
            stock_check = False
        else:
            all_sku_codes[i] = sku_master[0]
        try:
            value = float(myDict['quantity'][i])
        except:
            stock_check = False
            if myDict['sku_id'][i]:
                invalid_quantities.append(myDict['sku_id'][i])

        if not po_status and po_imeis and stock_check:
            po_qty = po_imeis.get(myDict['sku_id'][i], '')
            if po_qty:
                if float(po_qty) != float(value):
                    po_status = "Order Quantity is not matching with PO quantity"
                else:
                    del po_imeis[myDict['sku_id'][i]]

        if stock_check and myDict.get('location', ''):
            avail_stock = get_sku_available_dict(user, sku_code=sku_master[0]['sku_code'],
                                                 location=myDict['location'][i], available=True)
            if float(avail_stock) < float(value):
                less_stocks.append(str(myDict['sku_id'][i]) + '-' + str(myDict['location'][i]))

    if invalid_skus:
        status = " Invalid sku codes are " + ",".join(invalid_skus)
    if invalid_quantities:
        status += " Quantities missing sku codes are " + ",".join(invalid_quantities)
    if less_stocks:
        status += " Insufficient stock combindations are " + ",".join(less_stocks)

    if po_status:
        status += " " + po_status
    if not po_status and po_imeis:
        status += " Number of Order SKUS is not matching with Number of PO SKUS"
    if seller_status:
        status += " " + seller_status
    if sor_id_status:
        status += " " + sor_id_status

    return status, all_sku_codes


def create_order_json(order_detail, json_dat={}, ex_image_url={}):
    for key, value in json_dat.get('vendors_list', {}).iteritems():
        OrderMapping.objects.create(mapping_id=value, mapping_type=key, order_id=order_detail.id)
    keys_list = ['vendors_list', 'remarks', 'sku_code', 'quantity', 'description']
    for key in keys_list:
        if json_dat.get(key, ''):
            del json_dat[key]

    if json_dat.get('image_url', ''):
        temp_url = json_dat['image_url']
        if ex_image_url.get(json_dat['image_url'], ''):
            json_dat['image_url'] = ex_image_url[json_dat['image_url']]
        elif os.path.exists(json_dat['image_url'][1:]):
            new_path = 'static/images/co_images/' + str(order_detail.user)
            if not os.path.exists(new_path):
                os.makedirs(new_path)
            extension = json_dat['image_url'].split('.')[-1]
            new_file_path = new_path + str(order_detail.id) + '.' + extension
            shutil.move(json_dat['image_url'][1:], new_file_path)
            if os.path.exists(json_dat['image_url'][1:]):
                os.remove(json_dat['image_url'][1:])
            json_dat['image_url'] = '/' + new_file_path
            ex_image_url[temp_url] = json_dat['image_url']
        else:
            json_dat['image_url'] = ''
    if json_dat:
        OrderJson.objects.create(order_id=order_detail.id, json_data=json.dumps(json_dat),
                                 creation_date=datetime.datetime.now())
    return ex_image_url


def get_order_customer_details(order_data, request):
    customer_user = CustomerUserMapping.objects.filter(user_id=request.user.id)
    if customer_user:
        order_data['customer_id'] = customer_user[0].customer.customer_id
        order_data['customer_name'] = customer_user[0].customer.name
        order_data['telephone'] = customer_user[0].customer.phone_number
        order_data['email_id'] = customer_user[0].customer.email_id
        order_data['address'] = customer_user[0].customer.address
    return order_data


def check_and_raise_po(generic_order_id, cm_id):
    ''' it will create purchese order in warehouse '''
    generic_data = GenericOrderDetailMapping.objects.filter(generic_order_id=generic_order_id, customer_id=cm_id)
    if not generic_data:
        log.info("No Order Found")
        return "No Order Found"
    mapping = WarehouseCustomerMapping.objects.filter(customer=cm_id, status=1)
    if not mapping:
        return "Customer Don't Have Warehouse"
    mapping = mapping[0]
    wh_list = list(generic_data.values_list('cust_wh_id', flat=True).distinct())
    user_profile = UserProfile.objects.filter(user_id=mapping.warehouse.id)
    for wh in wh_list:
        po_data = generic_data.filter(cust_wh_id=wh)
        supplier = NetworkMaster.objects.filter(dest_location_code_id=mapping.warehouse.id, source_location_code_id=wh)
        if not supplier:
            continue
        supplier = supplier[0]
        if not supplier.supplier:
            continue
        po_id = get_purchase_order_id(mapping.warehouse)
        for data in po_data:
            purchase_data = copy.deepcopy(PO_DATA)
            po_sku_data = copy.deepcopy(PO_SUGGESTIONS_DATA)
            sku_data = OrderDetail.objects.get(id=data.orderdetail.id)
            sku = SKUMaster.objects.get(wms_code=sku_data.sku.sku_code, user=mapping.warehouse.id)
            po_sku_data['supplier_id'] = supplier.supplier.id
            po_sku_data['wms_code'] = sku.sku_code
            po_sku_data['sku_id'] = sku.id
            po_sku_data['order_quantity'] = data.quantity
            po_sku_data['price'] = sku_data.unit_price
            po_sku_data['measurement_unit'] = 'UNITS'
            po_sku_data['status'] = 0
            create_po = OpenPO(**po_sku_data)
            create_po.save()
            purchase_data['open_po_id'] = create_po.id
            purchase_data['order_id'] = po_id
            if user_profile:
                purchase_data['prefix'] = user_profile[0].prefix
            order = PurchaseOrder(**purchase_data)
            order.save()


def split_orders(**order_data):
    stock_wh_map = {}
    warehouse_level = order_data['warehouse_level']
    customer_id = order_data['customer_id']
    user_id = order_data['user']
    cm_id = CustomerMaster.objects.filter(customer_id=customer_id, user=user_id)
    dist_mapping = WarehouseCustomerMapping.objects.filter(customer_id=cm_id, status=1)
    if dist_mapping:
        dist_user_id = dist_mapping[0].warehouse
    else:
        log.info("No DIST id map::Order_DATA::" + repr(order_data))
        dist_user_id = user_id  # Parent of the Reseller is Distributor.

    req_stock = order_data['quantity']
    sku_id = order_data['sku_id']

    sku_code = SKUMaster.objects.get(id=sku_id).sku_code

    source_whs = list(NetworkMaster.objects.filter(dest_location_code_id=dist_user_id).filter(
        source_location_code__userprofile__warehouse_level=warehouse_level).values_list(
        'source_location_code_id', flat=True).order_by('lead_time', 'priority'))
    # source_whs = list(NetworkMaster.objects.filter(dest_location_code_id=dist_user_id).values_list(
    #     'source_location_code_id', flat=True).order_by('lead_time', 'priority'))
    # if user_id in source_whs and source_whs.index(user_id) != 0:
    #     source_whs.remove(user_id)
    #     source_whs.insert(0, user_id)
    # elif user_id not in source_whs:
    #     log.info("No Mapping Between WH and DIST in Network Master:: %s, %s" % (user_id, source_whs))
    #     source_whs.insert(0, user_id)
    if warehouse_level == 0 and user_id not in source_whs:  # Resellers wont have NETWORK MASTER
        source_whs.insert(0, user_id)

    stk_dtl_obj = dict(StockDetail.objects.filter(
        sku__user__in=source_whs, sku__wms_code=sku_code, quantity__gt=0).values_list(
        'sku__user').distinct().annotate(in_stock=Sum('quantity')))

    log.info("Stock Avail for SKU Code (%s)::%s" % (sku_code, repr(stk_dtl_obj)))
    for source_wh in source_whs:
        avail_stock = stk_dtl_obj.get(source_wh, 0)
        if not avail_stock:
            continue
        req_qty = req_stock - avail_stock
        if req_qty < avail_stock and req_qty < 0:
            stock_wh_map[source_wh] = avail_stock - abs(req_qty)
            break
        if req_qty >= 0:
            stock_wh_map[source_wh] = avail_stock
        else:
            break
        req_stock = req_qty
    log.info("Stock assigning Map for SKU Code (%s):: %s" % (sku_code, repr(stk_dtl_obj)))
    return stock_wh_map


def construct_order_data_dict(request, i, order_data, myDict, all_sku_codes, custom_order):
    continue_list = ['payment_received', 'charge_name', 'charge_amount', 'custom_order', 'user_type', 'invoice_amount',
                     'description', 'extra_data', 'location', 'serials', 'direct_dispatch', 'seller_id', 'sor_id',
                     'ship_to', 'client_name', 'po_number', 'corporate_po_number']
    inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
    order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
    for key, value in request.POST.iteritems():
        if key in continue_list:
            continue
        if key == 'sku_id':
            if not myDict[key][i]:
                continue
            sku_master = all_sku_codes[i]

            if custom_order == 'true':
                _sku_mas = sku_master
                if "Custom" in _sku_mas['sku_desc']:
                    _sku_mas = SKUMaster.objects.get(id=sku_master['id'])
                    _sku_mas.sku_desc = myDict['description'][i]
                    _sku_mas.save()

            order_data['sku_id'] = sku_master['id']
            order_data['title'] = sku_master['sku_desc']
        elif key == 'quantity' or key == 'pin_code':
            try:
                value = float(myDict[key][i])
            except:
                value = 0
            order_data[key] = value
        elif key == 'shipment_date':
            if value:
                ship_date = value.split('/')
                order_data[key] = datetime.date(int(ship_date[2]), int(ship_date[0]), int(ship_date[1]))
        elif key == 'total_amount':
            try:
                value = float(myDict[key][i])
            except:
                value = 0
            order_data['invoice_amount'] = value
        elif key == 'customer_id':
            if not value:
                value = 0
            order_data[key] = value
        elif key == 'unit_price':
            value = myDict[key][i]
            if not value:
                value = 0
            order_data[key] = value
        elif key in ['cgst_tax', 'sgst_tax', 'igst_tax']:
            value = myDict[key][i]
            try:
                invoice = float(myDict['invoice_amount'][i])
            except:
                invoice = 0
            if not value:
                value = 0
            order_summary_dict[key] = value
        elif key == 'tax_type':
            order_summary_dict['inter_state'] = inter_state_dict.get(value, 2)
        elif key == 'order_taken_by':
            order_summary_dict['order_taken_by'] = value
        elif key == 'shipment_time_slot':
            order_summary_dict['shipment_time_slot'] = value
        elif key == 'discount':
            try:
                discount = float(myDict[key][i])
            except:
                discount = 0
            order_summary_dict['discount'] = discount
        elif key == 'warehouse_level':
            order_data[key] = int(myDict[key][i])
        elif key == 'el_price':
            value = float(myDict[key][i])
            if not value:
                value = 0
            order_data[key] = value
        elif key == 'del_date':
            if value:
                order_data[key] = datetime.datetime.strptime(myDict[key][i], '%m/%d/%Y')
        else:
            order_data[key] = value

    return order_data, order_summary_dict, sku_master


def get_syncedusers_mapped_sku(wh, sku_id):
    sku_code = SKUMaster.objects.get(id=sku_id).sku_code
    sku_qs = SKUMaster.objects.filter(user=wh, sku_code=sku_code)
    if sku_qs:
        sku_id = sku_qs[0].id
    else:
        sku_id = None
    return sku_id


def custom_order_data(request, order_detail, ex_image_url, custom_order):
    extra_data = request.POST.get('extra_data', '')
    from_custom_order = request.POST.get('from_custom_order', '')
    if from_custom_order == 'true':
        if extra_data:
            OrderJson.objects.create(order_id=order_detail.id, json_data=extra_data,
                                     creation_date=datetime.datetime.now())
    elif custom_order == 'true' and extra_data:
        ex_image_url = create_order_json(order_detail, json.loads(extra_data), ex_image_url)


def construct_other_charge_amounts_map(created_order_id, myDict, creation_date, other_charge_amounts):
    if created_order_id and 'charge_name' in myDict.keys():
        for i in range(0, len(myDict['charge_name'])):
            if myDict['charge_name'][i] and myDict['charge_amount'][i]:
                OrderCharges.objects.create(user_id=user.id, order_id=created_order_id,
                                            charge_name=myDict['charge_name'][i],
                                            charge_amount=myDict['charge_amount'][i],
                                            creation_date=creation_date)
                other_charge_amounts += float(myDict['charge_amount'][i])
    return other_charge_amounts


def send_mail_ordered_report(order_detail, telephone, items, other_charge_amounts, order_data, user):
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='order', misc_value='true')
    if misc_detail and order_detail:
        company_name = UserProfile.objects.filter(user=user.id)[0].company_name
        headers = ['Product Details', 'Ordered Quantity', 'Total']
        data_dict = {'customer_name': order_data['customer_name'], 'order_id': order_detail.order_id,
                     'address': order_data['address'], 'phone_number': order_data['telephone'], 'items': items,
                     'headers': headers, 'company_name': company_name, 'user': user}

        t = loader.get_template('templates/order_confirmation.html')
        rendered = t.render(data_dict)

        email = order_data['email_id']
        if email:
            send_mail([email], 'Order Confirmation: %s' % order_detail.order_id, rendered)
        if not telephone:
            telephone = order_data.get('telephone', "")
        if telephone:
            order_creation_message(items, telephone, (order_detail.order_code) + str(order_detail.order_id),
                                   other_charges=other_charge_amounts)


def fetch_order_ids(stock_wh_map, user_order_ids_map):
    for usr, qty in stock_wh_map.iteritems():
        order_id = get_order_id(usr)
        if usr not in user_order_ids_map:
            user_order_ids_map[usr] = order_id


def sku_level_total_qtys(myDict, sku_total_qty_map):
    for i in range(0, len(myDict['sku_id'])):
        sku_id, quantity = myDict['sku_id'][i], myDict['quantity'][i]
        if sku_id in sku_total_qty_map:
            sku_total_qty_map[sku_id] += int(quantity)
        else:
            sku_total_qty_map[sku_id] = int(quantity)


@csrf_exempt
@login_required
@get_admin_user
@fn_timer
def insert_order_data(request, user=''):
    myDict = dict(request.POST.iterlists())
    order_id = ''
    # Sending mail and message
    items = []

    other_charge_amounts = 0

    # Picklist generation
    order_user_sku = {}
    order_user_objs = {}
    order_sku = {}
    order_objs = []

    # Initialize creation date
    creation_date = datetime.datetime.now()

    # Intialize to stored saved skus and dispatch data
    created_skus = []
    dispatch_orders = {}
    direct_dispatch = request.POST.get('direct_dispatch', '')
    dispatch_orders = OrderedDict()

    # Validate sku, quantity, stock
    valid_status, all_sku_codes = validate_order_form(myDict, request, user)

    payment_mode = request.POST.get('payment_mode', '')
    payment_received = request.POST.get('payment_received', '')
    tax_percent = request.POST.get('tax', '')
    telephone = request.POST.get('telephone', '')
    custom_order = request.POST.get('custom_order', '')
    user_type = request.POST.get('user_type', '')
    seller_id = request.POST.get('seller_id', '')
    sor_id = request.POST.get('sor_id', '')
    ship_to = request.POST.get('ship_to', '')
    po_number = request.POST.get('po_number', '')
    client_name = request.POST.get('client_name', '')
    corporate_po_number = request.POST.get('corporate_po_number', '')

    created_order_id = ''
    ex_image_url = {}
    inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
    po_data = []
    if valid_status:
        return HttpResponse(valid_status)

    log.info('Request params for ' + user.username + ' is ' + str(myDict))

    is_distributor = False
    cm_id = 0
    generic_order_id = 0
    admin_user = get_priceband_admin_user(user)
    if admin_user:
        # get_order_customer_details
        user_order_ids_map = {}
        sku_total_qty_map = {}
        sku_level_total_qtys(myDict, sku_total_qty_map)
        if user_type == 'customer':
            customer_user = CustomerUserMapping.objects.filter(user_id=request.user.id)

            customer_obj = CustomerMaster.objects.filter(customer_id=customer_user[0].customer.customer_id,
                                                         user=user.id)
            if customer_obj:
                is_distributor = customer_obj[0].is_distributor
                cm_id = customer_obj[0].id
                generic_order_id = get_generic_order_id(cm_id)
    try:
        for i in range(0, len(myDict['sku_id'])):
            order_data = copy.deepcopy(UPLOAD_ORDER_DATA)
            #order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
            # order_data['order_id'] = order_id
            order_data['order_code'] = 'MN'
            order_data['marketplace'] = 'Offline'
            if custom_order == 'true':
                order_data['order_code'] = 'CO'
            order_data['user'] = user.id

            order_data['unit_price'] = 0
            order_data['sku_code'] = myDict['sku_id'][i]
            vendor_items = ['printing_vendor', 'embroidery_vendor', 'production_unit']

            # Written a separate function to make the code simpler
            order_data, order_summary_dict, sku_master = construct_order_data_dict(
                request, i, order_data, myDict, all_sku_codes, custom_order)

            if not order_data['sku_id'] or not order_data['quantity']:
                continue

            if admin_user:
                if user_type == 'customer':
                    order_data = get_order_customer_details(order_data, request)
                else:
                    order_data['warehouse_level'] = 0
                stock_wh_map = split_orders(**order_data)
                fetch_order_ids(stock_wh_map, user_order_ids_map)
                if not is_distributor and user_order_ids_map.has_key(user.id):
                    order_data['order_id'] = user_order_ids_map[user.id]
                    order_data['user'] = user.id
                    mapped_sku_id = get_syncedusers_mapped_sku(user.id, order_data['sku_id'])
                    order_obj = OrderDetail.objects.filter(order_id=user_order_ids_map[user.id], user=user.id,
                                                           sku_id=mapped_sku_id, order_code=order_data['order_code'])
                    if not order_obj:
                        el_price = order_data['el_price']
                        del_date = order_data['del_date']
                        if 'warehouse_level' in order_data:
                            order_data.pop('warehouse_level')
                        if 'margin_data' in order_data:
                            order_data.pop('margin_data')
                        if 'el_price' in order_data:
                            order_data.pop('el_price')
                        if 'del_date' in order_data:
                            order_data.pop('del_date')
                        order_data['sku_id'] = mapped_sku_id
                        order_obj = OrderDetail(**order_data)
                        order_obj.save()

                        # Collecting needed data for Picklist generation
                        order_user_sku.setdefault(user.id, {})
                        order_user_sku[user.id].setdefault(order_obj.sku, 0)
                        order_user_sku[user.id][order_obj.sku] += order_data['quantity']

                        # Collecting User order objs for picklist generation
                        order_user_objs.setdefault(user.id, [])
                        order_user_objs[user.id].append(order_obj)

                        create_grouping_order_for_generic(generic_order_id, order_obj, cm_id, user.id,
                                                          order_data['quantity'], corporate_po_number, client_name,
                                                          order_data['unit_price'], el_price, del_date)
                        create_ordersummary_data(order_summary_dict, order_obj, ship_to)
                for usr, qty in stock_wh_map.iteritems():
                    order_data['order_id'] = user_order_ids_map[usr]
                    order_data['user'] = usr
                    if not qty:
                        continue
                    order_data['quantity'] = qty
                    order_data['creation_date'] = creation_date
                    mapped_sku_id = get_syncedusers_mapped_sku(usr, order_data['sku_id'])
                    if not order_data.get('original_order_id', ''):
                        order_data['original_order_id'] = str(order_data['order_code']) + str(order_data['order_id'])
                    order_obj = OrderDetail.objects.filter(order_id=order_data['order_id'], user=usr,
                                                           sku_id=mapped_sku_id, order_code=order_data['order_code'])
                    if not order_obj:
                        order_data['sku_id'] = mapped_sku_id
                        create_generic_order(order_data, cm_id, user.id, generic_order_id, order_objs, is_distributor,
                                             order_summary_dict, ship_to, corporate_po_number, client_name, admin_user,
                                             sku_total_qty_map, order_user_sku, order_user_objs)
                    else:
                        created_skus.append(order_data['sku_id'])
                        items.append(
                            [sku_master['sku_desc'], order_data['quantity'], order_data.get('invoice_amount', 0)])

            else:
                if not order_id:
                    order_id = get_order_id(user.id)
                order_data['order_id'] = order_id

                if po_number:
                    order_data['order_type'] = 'Transit'

                order_obj = OrderDetail.objects.filter(order_id=order_data['order_id'], user=user.id,
                                                       sku_id=order_data['sku_id'], order_code=order_data['order_code'])
                if not order_obj:
                    if user_type == 'customer':
                        order_data = get_order_customer_details(order_data, request)
                    if payment_received:
                        order_payment = 0
                        if float(order_data['invoice_amount']) < float(payment_received):
                            payment_received = float(payment_received) - float(order_data['invoice_amount'])
                            order_payment = float(order_data['invoice_amount'])
                        else:
                            payment_received = float(payment_received)
                            order_payment = float(payment_received)
                        order_data['payment_received'] = order_payment

                    order_data['creation_date'] = creation_date
                    if not order_data.get('original_order_id', ''):
                        order_data['original_order_id'] = str(order_data['order_code']) + str(order_data['order_id'])
                    if 'warehouse_level' in order_data:
                        order_data.pop('warehouse_level')
                    if 'margin_data' in order_data:
                        order_data.pop('margin_data')
                    if 'el_price' in order_data:
                        order_data.pop('el_price')
                    if 'del_date' in order_data:
                        order_data.pop('del_date')
                    order_detail = OrderDetail(**order_data)
                    order_detail.save()
                    if seller_id:
                        seller_master_id = SellerMaster.objects.filter(seller_id=seller_id, user=user.id)
                        SellerOrder.objects.create(seller_id=seller_master_id[0].id, sor_id=sor_id,
                                                   order_id=order_detail.id,
                                                   quantity=order_detail.quantity, order_status='PENDING',
                                                   creation_date=datetime.datetime.now())

                    order_objs.append(order_detail)
                    order_sku.update({order_detail.sku: order_data['quantity']})
                    created_order_id = order_detail.order_code + str(order_detail.order_id)

                    create_ordersummary_data(order_summary_dict, order_detail, ship_to)

                    created_skus.append(order_data['sku_id'])
                    if myDict.get('location', '') and myDict['location'][i]:
                        serials = ''
                        if myDict.get('serials'):
                            serials = myDict['serials'][i]
                        dispatch_orders[order_detail.id] = {'order_instance': order_detail,
                                                            'data': [{'quantity': order_data['quantity'],
                                                                      'location': myDict['location'][i],
                                                                      'serials': serials}]}
                    custom_order_data(request, order_detail, ex_image_url, custom_order)
                elif order_obj and order_data['sku_id'] in created_skus:
                    order_det = order_obj[0]
                    order_det.quantity += float(order_data['quantity'])
                    order_det.invoice_amount += order_data['invoice_amount']
                    order_det.save()
                    order_sku[order_det.sku] += order_data['quantity']
                    if dispatch_orders.has_key(order_det.id):
                        serials = ''
                        if myDict.get('serials'):
                            serials = myDict['serials'][i]
                        dispatch_orders[order_det.id]['order_instance'] = order_det
                        dispatch_orders[order_det.id]['data'].append(
                            {'quantity': order_data['quantity'], 'location': myDict['location'][i],
                             'serials': serials})

                items.append([sku_master['sku_desc'], order_data['quantity'], order_data.get('invoice_amount', 0)])

                if po_number:
                    OrderPOMapping.objects.create(order_id=order_data['original_order_id'], sku_id=order_data['sku_id'],
                                                  purchase_order_id=po_number.split('_')[-1], status=1,
                                                  creation_date=datetime.datetime.now())
                other_charge_amounts = construct_other_charge_amounts_map(created_order_id, myDict,
                                                                          creation_date, other_charge_amounts)
        if generic_order_id:
            check_and_raise_po(generic_order_id, cm_id)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create order failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(myDict), str(e)))
        return HttpResponse("Order Creation Failed")

    try:
        if not admin_user:
            send_mail_ordered_report(order_detail, telephone, items, other_charge_amounts, order_data, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create order mail sending failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(myDict), str(e)))

    message = "Success"
    if not admin_user:
        auto_picklist_signal = get_misc_value('auto_generate_picklist', user.id)
        if direct_dispatch == 'true':
            message = direct_dispatch_orders(user, dispatch_orders)
        elif auto_picklist_signal == 'true':
            message = check_stocks(order_sku, user, request, order_objs)
    else:
        for user_id, order_user_data in order_user_sku.iteritems():
            auto_picklist_signal = get_misc_value('auto_generate_picklist', user_id)
            order_objs = order_user_objs.get(user_id, [])
            log.info("Picklist checking for user %s and order id is %s" % (str(user_id), str(order_user_data)))
            if auto_picklist_signal == 'true':
                log.info("Entered")
                message = check_stocks(order_user_data, User.objects.get(id=user_id), request, order_objs)
        #qssi push order api call
        generic_orders = GenericOrderDetailMapping.objects.filter(generic_order_id=generic_order_id,
                                                                   customer_id=cm_id).\
                                        values('orderdetail__original_order_id', 'orderdetail__user').distinct()
        for generic_order in generic_orders:
            original_order_id = generic_order['orderdetail__original_order_id']
            order_detail_user = User.objects.get(id=generic_order['orderdetail__user'])
            resp = order_push(original_order_id, order_detail_user, "NEW")
            log.info('New Order Push Status: %s' %(str(resp)))
        if user_type == 'customer':
            # Creating Uploading POs object with file upload pending.
            upload_po_map = {'uploaded_user_id': request.user.id, 'po_number': corporate_po_number,
                             'uploaded_date': datetime.datetime.today(), 'customer_name': client_name}
            pending_po_obj = OrderUploads(**upload_po_map)
            pending_po_obj.save()

    # Deleting Customer Cart data after successful order creation
    CustomerCartData.objects.filter(customer_user=request.user.id).delete()

    return HttpResponse(message)


@fn_timer
def direct_dispatch_orders(user, dispatch_orders, creation_date=datetime.datetime.now()):
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(location__zone__zone='DAMAGED_ZONE'). \
        filter(sku__user=user.id, quantity__gt=0)
    picklist_number = int(get_picklist_number(user)) + 1
    mod_locations = []

    for order_id, orders in dispatch_orders.iteritems():
        order = orders['order_instance']
        for data in orders.get('data', []):
            order_stocks = sku_stocks.filter(sku_id=order.sku_id, location__location=data['location'], quantity__gt=0)
            needed_quantity = float(data['quantity'])
            val = {}
            val['wms_code'] = order.sku.wms_code
            val['imei'] = data['serials']
            insert_order_serial(None, val, order=order)

            for stock in order_stocks:
                picked_quantity = 0
                if float(stock.quantity) <= needed_quantity:
                    picked_quantity = stock.quantity
                    stock.quantity = 0
                else:
                    picked_quantity = needed_quantity
                    stock.quantity = float(stock.quantity) - picked_quantity
                if stock.quantity < 0:
                    stock.quantity = 0
                stock.save()

                mod_locations.append(stock.location.location)

                new_picklist = Picklist.objects.create(picklist_number=picklist_number, reserved_quantity=0,
                                                       picked_quantity=picked_quantity,
                                                       remarks='Direct-Dispatch Orders', status='dispatched',
                                                       creation_date=creation_date,
                                                       order_id=order.id, stock_id=stock.id)
                pick_loc = PicklistLocation.objects.create(quantity=picked_quantity, status=0,
                                                           creation_date=creation_date,
                                                           updation_date=creation_date, picklist_id=new_picklist.id,
                                                           stock_id=stock.id,
                                                           reserved=0)
                order_summary = SellerOrderSummary.objects.create(picklist_id=new_picklist.id, pick_number=1,
                                                                  quantity=picked_quantity,
                                                                  order_id=order.id, creation_date=creation_date)
                needed_quantity -= picked_quantity
                if needed_quantity <= 0:
                    break
            order.status = 2
            order.save()

    if mod_locations:
        update_filled_capacity(list(set(mod_locations)), user.id)

    return 'Order Created and Dispatched Successfully'


def check_stocks(order_sku, user, request, order_objs):
    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
        location__zone__zone='DAMAGED_ZONE').filter(sku__user=user.id, quantity__gt=0)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
            'receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
            'location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    sku_stocks = stock_detail1 | stock_detail2

    sku_id_stocks = sku_stocks.values('id', 'sku_id').annotate(total=Sum('quantity'))
    pick_res_locat = PicklistLocation.objects.prefetch_related('picklist', 'stock').filter(status=1). \
        filter(Q(picklist__order__user=user.id) | Q(picklist__stock__sku__user=user.id)).values(
        'stock__sku_id').annotate(total=Sum('reserved'))
    val_dict = {}
    members = []
    val_dict['pic_res_ids'] = map(lambda d: d['stock__sku_id'], pick_res_locat)
    val_dict['pic_res_quans'] = map(lambda d: d['total'], pick_res_locat)

    val_dict['sku_ids'] = map(lambda d: d['sku_id'], sku_id_stocks)
    val_dict['stock_ids'] = map(lambda d: d['id'], sku_id_stocks)
    val_dict['stock_totals'] = map(lambda d: d['total'], sku_id_stocks)

    for sku in order_sku.keys():
        if sku.relation_type == 'combo':
            combo_data = sku_combos.filter(parent_sku_id=sku.id)
            for combo in combo_data:
                stock_detail, stock_count, sku.wms_code = get_sku_stock(request, combo.member_sku, sku_stocks, user,
                                                                        val_dict, sku_id_stocks)
                if stock_count < order_sku[sku]:
                    return "Order created Successfully"
        else:
            stock_detail, stock_count, sku.wms_code = get_sku_stock(request, sku, sku_stocks, user, val_dict,
                                                                    sku_id_stocks)
            if stock_count < order_sku[sku]:
                return "Order created Successfully"

    picklist_number = get_picklist_number(user)
    for order_obj in order_objs:
        picklist_generation([order_obj], request, picklist_number, user, sku_combos, sku_stocks, status='open',
                            remarks='Auto-generated Picklist')

    return "Order created, Picklist generated Successfully"


@csrf_exempt
@login_required
@get_admin_user
def get_warehouses_list(request, user=''):
    user_list = []
    admin_user = UserGroups.objects.filter(
        Q(admin_user__username__iexact=user.username) | Q(user__username__iexact=user.username)). \
        values_list('admin_user_id', flat=True)
    user_groups = UserGroups.objects.filter(admin_user_id__in=admin_user).values('user__username',
                                                                                 'admin_user__username')
    for users in user_groups:
        for key, value in users.iteritems():
            if user.username != value and value not in user_list:
                user_list.append(value)

    return HttpResponse(json.dumps({'warehouses': user_list}))


def validate_st(all_data, user):
    sku_status = ''
    other_status = ''
    price_status = ''
    wh_status = ''

    for key, value in all_data.iteritems():
        warehouse = User.objects.get(username=key)
        if not value:
            continue
        for val in value:
            sku = SKUMaster.objects.filter(wms_code=val[0], user=warehouse.id)
            if not sku:
                if not sku_status:
                    sku_status = "Invalid SKU Code " + val[0]
                else:
                    sku_status += ', ' + val[0]
            order_quantity = val[1]
            if not order_quantity:
                if not other_status:
                    other_status = "Quantity missing for " + val[0]
                else:
                    other_status += ', ' + val[0]
            try:
                price = float(val[2])
            except:
                if not price_status:
                    price_status = "Price missing for " + val[0]
                else:
                    price_status += ', ' + val[0]
            code = val[0]
            sku_code = SKUMaster.objects.filter(wms_code__iexact=val[0], user=user.id)
            if not sku_code:
                if not wh_status:
                    wh_status = "SKU Code %s doesn't exists in given warehouse" % code
                else:
                    wh_status += ", " + code

    if other_status:
        sku_status += ", " + other_status
    if price_status:
        sku_status += ", " + price_status
    if wh_status:
        sku_status += ", " + wh_status

    return sku_status.strip(", ")


def insert_st(all_data, user):
    for key, value in all_data.iteritems():
        for val in value:
            if val[3]:
                open_st = OpenST.objects.get(id=val[3])
                open_st.warehouse_id = User.objects.get(username__iexact=key).id
                open_st.sku_id = SKUMaster.objects.get(wms_code=val[0], user=user.id).id
                open_st.price = float(val[2])
                open_st.order_quantity = float(val[1])
                open_st.save()
                continue
            stock_dict = copy.deepcopy(OPEN_ST_FIELDS)
            stock_dict['warehouse_id'] = User.objects.get(username__iexact=key).id
            stock_dict['sku_id'] = SKUMaster.objects.get(wms_code=val[0], user=user.id).id
            stock_dict['order_quantity'] = float(val[1])
            stock_dict['price'] = float(val[2])
            stock_transfer = OpenST(**stock_dict)
            stock_transfer.save()
            all_data[key][all_data[key].index(val)][3] = stock_transfer.id
    return all_data


def confirm_stock_transfer(all_data, user, warehouse_name):
    for key, value in all_data.iteritems():
        po_id = get_purchase_order_id(user)
        warehouse = User.objects.get(username__iexact=warehouse_name)
        stock_transfer_obj = StockTransfer.objects.filter(sku__user=warehouse.id).order_by('-order_id')
        if stock_transfer_obj:
            order_id = int(stock_transfer_obj[0].order_id) + 1
        else:
            order_id = 1001

        for val in value:
            open_st = OpenST.objects.get(id=val[3])
            sku_id = SKUMaster.objects.get(wms_code__iexact=val[0], user=warehouse.id).id
            user_profile = UserProfile.objects.filter(user_id=user.id)
            prefix = ''
            if user_profile:
                prefix = user_profile[0].prefix

            po_dict = {'order_id': po_id, 'received_quantity': 0, 'saved_quantity': 0,
                       'po_date': datetime.datetime.now(), 'ship_to': '',
                       'status': '', 'prefix': prefix, 'creation_date': datetime.datetime.now()}
            po_order = PurchaseOrder(**po_dict)
            po_order.save()
            st_purchase_dict = {'po_id': po_order.id, 'open_st_id': open_st.id,
                                'creation_date': datetime.datetime.now()}
            st_purchase = STPurchaseOrder(**st_purchase_dict)
            st_purchase.save()
            st_dict = copy.deepcopy(STOCK_TRANSFER_FIELDS)
            st_dict['order_id'] = order_id
            st_dict['invoice_amount'] = float(val[1]) * float(val[2])
            st_dict['quantity'] = float(val[1])
            st_dict['st_po_id'] = st_purchase.id
            st_dict['sku_id'] = sku_id
            stock_transfer = StockTransfer(**st_dict)
            stock_transfer.save()
            open_st.status = 0
            open_st.save()
    return HttpResponse("Confirmed Successfully")


@csrf_exempt
@login_required
@get_admin_user
def create_stock_transfer(request, user=''):
    all_data = {}
    warehouse_name = request.POST.get('warehouse_name', '')
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['wms_code'])):
        if not data_dict['wms_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        cond = (user.username)
        all_data.setdefault(cond, [])
        all_data[cond].append(
            [data_dict['wms_code'][i], data_dict['order_quantity'][i], data_dict['price'][i], data_id])
    warehouse = User.objects.get(username=warehouse_name)

    status = validate_st(all_data, warehouse)
    if not status:
        all_data = insert_st(all_data, warehouse)
        status = confirm_stock_transfer(all_data, warehouse, user.username)
    return HttpResponse(status)


def get_purchase_order_id(user):
    po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).values_list('order_id', flat=True).order_by(
        "-order_id")
    st_order = STPurchaseOrder.objects.filter(open_st__sku__user=user.id).values_list('po__order_id',
                                                                                      flat=True).order_by(
        "-po__order_id")
    rw_order = RWPurchase.objects.filter(rwo__vendor__user=user.id).values_list('purchase_order__order_id', flat=True). \
        order_by("-purchase_order__order_id")
    order_ids = list(chain(po_data, st_order, rw_order))
    order_ids = sorted(order_ids, reverse=True)
    if not order_ids:
        po_id = 1
    else:
        po_id = int(order_ids[0]) + 1
    return po_id


@csrf_exempt
@login_required
@get_admin_user
def get_marketplaces_list(request, user=''):
    status_type = request.GET.get('status', '')
    marketplace = get_marketplace_names(user, status_type)
    '''if status_type == 'picked':
        marketplace = list(Picklist.objects.exclude(order__marketplace='').filter(picked_quantity__gt=0, order__user = user.id).\
                                            values_list('order__marketplace', flat=True).distinct())
    elif status_type == 'all_marketplaces':
        marketplace = list(OrderDetail.objects.exclude(marketplace='').filter(user = user.id, quantity__gt=0).values_list('marketplace', flat=True).\
                                                       distinct())
    else:
        marketplace = list(OrderDetail.objects.exclude(marketplace='').filter(status=1, user = user.id, quantity__gt=0).values_list('marketplace', flat=True).\
                                               distinct())'''
    return HttpResponse(json.dumps({'marketplaces': marketplace}))


@csrf_exempt
def get_back_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    is_production = get_misc_value('production_switch', user.id)
    user = user
    order_detail = OrderDetail.objects.filter(user=user.id, status=1, quantity__gt=0).values('sku_id', 'sku__wms_code',
                                                                                             'sku__sku_code',
                                                                                             'sku__sku_desc').distinct()
    master_data = []

    stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values('sku_id').distinct(). \
        annotate(in_stock=Sum('quantity'))
    reserved_objs = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1, reserved__gt=0).values(
        'stock__sku_id').distinct(). \
        annotate(reserved=Sum('reserved'))
    order_quantity_objs = OrderDetail.objects.filter(status=1, user=user.id).values('sku_id').distinct(). \
        annotate(order_quantity=Sum('quantity'))

    purchase_objs = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']). \
        filter(open_po__sku__user=user.id). \
        values('open_po__sku_id').annotate(total_order=Sum('open_po__order_quantity'),
                                           total_received=Sum('received_quantity'))

    stocks = map(lambda d: d['sku_id'], stock_objs)
    purchases = map(lambda d: d['open_po__sku_id'], purchase_objs)
    reserveds = map(lambda d: d['stock__sku_id'], reserved_objs)
    order_quantities = map(lambda d: d['sku_id'], order_quantity_objs)

    table_headers = ['WMS Code', 'WMS Code', 'Product Description', 'Ordered Quantity', 'Stock Quantity',
                     'Transit Quantity', 'Procurement Quantity']
    for order in order_detail:
        temp = {}
        production_quantity = 0
        transit_quantity = 0
        stock_quantity = 0
        order_quantity = 0
        if order['sku_id'] in stocks:
            stock_quantity = map(lambda d: d['in_stock'], stock_objs)[stocks.index(order['sku_id'])]
        if order['sku_id'] in reserveds:
            stock_quantity = map(lambda d: d['reserved'], reserved_objs)[reserveds.index(order['sku_id'])]
        if order['sku_id'] in order_quantities:
            order_quantity = map(lambda d: d['order_quantity'], order_quantity_objs)[
                order_quantities.index(order['sku_id'])]

        if order['sku_id'] in purchases:
            total_order = map(lambda d: d['total_order'], purchase_objs)[purchases.index(order['sku_id'])]
            total_received = map(lambda d: d['total_received'], purchase_objs)[purchases.index(order['sku_id'])]
            diff_quantity = float(total_order) - float(total_received)
            if diff_quantity > 0:
                transit_quantity = diff_quantity

        if is_production == 'true':
            production_orders = JobOrder.objects.filter(product_code__sku_code=order['sku__sku_code'],
                                                        product_code__user=user.id). \
                exclude(status__in=['open', 'confirmed-putaway']).values('product_code__sku_code'). \
                annotate(total_order=Sum('product_quantity'), total_received=Sum('received_quantity'))
            if production_orders:
                production_order = production_orders[0]
                diff_quantity = float(production_order['total_order']) - float(production_order['total_received'])
                if diff_quantity > 0:
                    production_quantity = diff_quantity
        procured_quantity = order_quantity - stock_quantity - transit_quantity - production_quantity
        if procured_quantity > 0:
            checkbox = "<input type='checkbox' id='back-checked' name='%s'>" % order['sku__sku_desc']
            temp = OrderedDict(
                (('', checkbox), ('WMS Code', order['sku__wms_code']), ('Product Description', order['sku__sku_desc']),
                 ('Ordered Quantity', order_quantity), ('Stock Quantity', stock_quantity),
                 ('Transit Quantity', transit_quantity), ('Procurement Quantity', procured_quantity),
                 ('DT_RowClass', 'results')
                 ))
            if is_production == 'true':
                temp['In Production Quantity'] = production_quantity
                if not 'In Production Quantity' in table_headers:
                    table_headers.insert(6, 'In Production Quantity')
            master_data.append(temp)
    if search_term:
        master_data = filter(lambda person: search_term in person['WMS Code'] or \
                                            str(search_term).lower() in str(person['Product Description']).lower() or \
                                            search_term in str(person['Ordered Quantity']) or \
                                            search_term in str(person['Stock Quantity']) or search_term in str(
            person['Transit Quantity']) or \
                                            search_term in str(person['Procurement Quantity']), master_data)
    elif order_term:
        if order_term == 'asc':
            master_data = sorted(master_data, key=lambda x: x[table_headers[col_num]])
        else:
            master_data = sorted(master_data, key=lambda x: x[table_headers[col_num]], reverse=True)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    temp_data['aaData'] = master_data[start_index:stop_index]


@csrf_exempt
@get_admin_user
def generate_po_data(request, user=''):
    data_dict = []
    supplier_list = []
    suppliers = SupplierMaster.objects.filter(user=user.id)
    for supplier in suppliers:
        supplier_list.append({'id': supplier.id, 'name': supplier.name})
    for key, value in request.POST.iteritems():
        price = 0
        key = key.split(":")
        selected_item = ''
        sku_supplier = SKUSupplier.objects.filter(sku__wms_code=key[0], sku__user=user.id)
        if sku_supplier:
            selected_item = {'id': sku_supplier[0].supplier_id, 'name': sku_supplier[0].supplier.name}
            price = sku_supplier[0].price
        data_dict.append(
            {'wms_code': key[0], 'title': key[1], 'quantity': value, 'selected_item': selected_item, 'price': price})
    return HttpResponse(json.dumps({'data_dict': data_dict, 'supplier_list': supplier_list}))


@csrf_exempt
@get_admin_user
def generate_jo_data(request, user=''):
    all_data = []
    title = 'Raise Job Order'
    for key, value in request.POST.iteritems():
        data = []
        key = key.split(':')[0]
        bom_master = BOMMaster.objects.filter(product_sku__sku_code=key, product_sku__user=user.id)
        description = ''
        if bom_master:
            for bom in bom_master:
                data.append(
                    {'material_code': bom.material_sku.sku_code, 'material_quantity': float(bom.material_quantity),
                     'id': '', 'measurement_type': bom.unit_of_measurement})
            description = bom.product_sku.sku_desc
        all_data.append({'product_code': key, 'product_description': value,
                         'sub_data': data, 'description': description})
    return HttpResponse(json.dumps({'data': all_data}))


@csrf_exempt
@get_admin_user
def create_stock_transfer_data(request, user=''):
    all_data = []
    title = 'Create Stock Transfer'
    data = []
    key = request.POST.get('WMS Code')
    quantity = int(request.POST.get('Ordered Quantity', 0))
    supplier_data = SKUSupplier.objects.filter(sku__wms_code=key, sku__user=user.id)
    if supplier_data:
        price = supplier_data[0].price * quantity;
    else:
        price = 0

    return HttpResponse(json.dumps({'price': price}))


def get_shipment_number(user):
    order_shipment = OrderShipment.objects.filter(user=user.id).order_by('-shipment_number')
    if order_shipment:
        shipment_number = int(order_shipment[0].shipment_number) + 1
    else:
        shipment_number = 1
    return shipment_number


@csrf_exempt
@get_admin_user
def shipment_info(request, user=''):
    shipment_number = get_shipment_number(user)
    market_place = list(Picklist.objects.filter(order__user=user.id, status__icontains='picked'). \
                        values_list('order__marketplace', flat=True).distinct())
    return HttpResponse(json.dumps({'shipment_number': shipment_number, 'market_places': market_place}))


def create_shipment(request, user):
    data_dict = copy.deepcopy(ORDER_SHIPMENT_DATA)
    for key, value in request.POST.iteritems():
        if key in ('customer_id', 'marketplace'):
            continue
        elif key == 'shipment_date':
            ship_date = value.split('/')
            data_dict[key] = datetime.date(int(ship_date[2]), int(ship_date[0]), int(ship_date[1]))
        elif key in ORDER_SHIPMENT_DATA.keys():
            data_dict[key] = value

    data_dict['user'] = user.id
    data = OrderShipment(**data_dict)
    data.save()
    return data


@csrf_exempt
@get_admin_user
def insert_shipment_info(request, user=''):
    ''' Create Shipment Code '''
    myDict = dict(request.POST.iterlists())
    log.info('Request params are ' + str(request.POST.dict()))
    user_profile = UserProfile.objects.filter(user_id=user.id)
    try:
        order_shipment = create_shipment(request, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create shipment failed for params ' + str(request.POST.dict()) + ' error statement is ' + str(e))
        return HttpResponse('Create shipment Failed')
    try:
        shipped_orders_dict = {}
        for i in range(0, len(myDict['sku_code'])):

            if not myDict['shipping_quantity'][i]:
                continue

            order_ids = eval(myDict['id'][i])
            if not isinstance(order_ids, list):
                order_ids = [order_ids]
            received_quantity = int(myDict['shipping_quantity'][i])
            for order_id in order_ids:
                if received_quantity <= 0:
                    break
                invoice_number = ''
                data_dict = copy.deepcopy(ORDER_PACKAGING_FIELDS)
                shipment_data = copy.deepcopy(SHIPMENT_INFO_FIELDS)
                order_detail = OrderDetail.objects.get(id=order_id, user=user.id)

                for key, value in myDict.iteritems():
                    if key in data_dict:
                        data_dict[key] = value[i]
                    if key in shipment_data and key != 'id':
                        shipment_data[key] = value[i]

                # Need to comment below 3 lines if shipment scan is ready
                if 'imei_number' in myDict.keys() and myDict['imei_number'][i]:
                    shipped_orders_dict = insert_order_serial([], {'wms_code': order_detail.sku.wms_code,
                                                                   'imei': myDict['imei_number'][i]},
                                                              order=order_detail,
                                                              shipped_orders_dict=shipped_orders_dict)
                # Until Here
                order_pack_instance = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id,
                                                                    package_reference=myDict['package_reference'][i],
                                                                    order_shipment__user=user.id)
                if not order_pack_instance:
                    data_dict['order_shipment_id'] = order_shipment.id
                    data = OrderPackaging(**data_dict)
                    data.save()
                else:
                    data = order_pack_instance[0]
                picked_orders = Picklist.objects.filter(order_id=order_id, status__icontains='picked',
                                                        order__user=user.id)
                order_quantity = int(order_detail.quantity)
                if order_quantity == 0:
                    continue
                elif order_quantity < received_quantity:
                    shipped_quantity = order_quantity
                    received_quantity -= order_quantity
                elif order_quantity >= received_quantity:
                    shipped_quantity = received_quantity
                    received_quantity = 0

                shipment_data['order_shipment_id'] = order_shipment.id
                shipment_data['order_packaging_id'] = data.id
                shipment_data['order_id'] = order_id
                shipment_data['shipping_quantity'] = shipped_quantity
                shipment_data['invoice_number'] = invoice_number
                ship_data = ShipmentInfo(**shipment_data)
                ship_data.save()

                default_ship_track_status = 'Dispatched'
                tracking = ShipmentTracking.objects.filter(shipment_id=ship_data.id, shipment__order__user=user.id,
                                                           ship_status=default_ship_track_status)
                if not tracking:
                    ShipmentTracking.objects.create(shipment_id=ship_data.id, ship_status=default_ship_track_status,
                                                    creation_date=datetime.datetime.now())
                order_awb_map = OrderAwbMap.objects.filter(original_order_id=order_detail.original_order_id, user=user)
                if order_awb_map.count():
                    order_awb_map.update(status=2)
                else:
                    original_order_id = str(order_detail.order_code) + str(order_detail.order_id)
                    order_awb_map = OrderAwbMap.objects.filter(original_order_id=original_order_id, user=user)
                    if order_awb_map.count():
                        order_awb_map.update(status=2)

                # Need to comment below lines if shipment scan is ready
                if shipped_orders_dict.has_key(int(order_id)):
                    shipped_orders_dict[int(order_id)].setdefault('quantity', 0)
                    shipped_orders_dict[int(order_id)]['quantity'] += float(shipped_quantity)
                else:
                    shipped_orders_dict[int(order_id)] = {}
                    shipped_orders_dict[int(order_id)]['quantity'] = float(shipped_quantity)
                # Until Here

                log.info('Shipemnt Info dict is ' + str(shipment_data))
                ship_quantity = ShipmentInfo.objects.filter(order_id=order_id). \
                    aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
                if ship_quantity >= int(order_detail.quantity):
                    order_detail.status = 2
                    order_detail.save()
                    for pick_order in picked_orders:
                        setattr(pick_order, 'status', 'dispatched')
                        pick_order.save()
        # Need to comment below lines if shipment scan is ready
        if shipped_orders_dict:
            log.info('Order Status update call for user ' + str(user.username) + ' is ' + str(shipped_orders_dict))
            check_and_update_order_status(shipped_orders_dict, user)
            # Until Here
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(
            'Shipment info saving is failed for params ' + str(request.POST.dict()) + ' error statement is ' + str(e))

    return HttpResponse(json.dumps({'status': True, 'message': 'Shipment Created Successfully'}))


@csrf_exempt
@login_required
@get_admin_user
def shipment_info_data(request, user=''):
    headers = ('Order ID', 'SKU Code', 'Shipping Quantity', 'Shipment Reference', 'Pack Reference', 'Status')
    data = []
    customer_id = request.GET['customer_id']
    shipment_number = request.GET['shipment_number']
    gateout = request.GET.get('gateout', '')
    if gateout:
        gateout = int(gateout)
    ship_reference = ''
    shipment_orders = ShipmentInfo.objects.filter(order__customer_id=customer_id,
                                                  order_shipment__shipment_number=shipment_number,
                                                  order_shipment__user=user.id)
    for orders in shipment_orders:
        ship_status = copy.deepcopy(SHIPMENT_STATUS)
        status = 'Dispatched'
        tracking = ShipmentTracking.objects.filter(shipment_id=orders.id, shipment__order__user=user.id).order_by(
            '-creation_date'). \
            values_list('ship_status', flat=True)
        if tracking:
            status = tracking[0]
            if gateout:
                if status != 'Delivered' and status != 'Out for Delivery':
                    continue
            else:
                if not (status != 'Delivered' and status != 'Out for Delivery'):
                    continue
        ship_status = ship_status[ship_status.index(status):]
        data.append({'id': orders.id, 'order_id': orders.order.order_id, 'sku_code': orders.order.sku.sku_code,
                     'ship_quantity': orders.shipping_quantity,
                     'pack_reference': orders.order_packaging.package_reference,
                     'ship_status': ship_status, 'status': status})
        if not ship_reference:
            ship_reference = orders.order_packaging.order_shipment.shipment_reference

    return HttpResponse(json.dumps({'data': data, 'customer_id': customer_id, 'ship_status': SHIPMENT_STATUS,
                                    'ship_reference': ship_reference}, cls=DjangoJSONEncoder))


@csrf_exempt
@get_admin_user
def update_shipment_status(request, user=''):
    data_dict = dict(request.GET.iterlists())
    ship_reference = request.GET.get('ship_reference', '')
    for i in range(len(data_dict['id'])):
        shipment_info = ShipmentInfo.objects.get(id=data_dict['id'][i])
        tracking = ShipmentTracking.objects.filter(shipment_id=shipment_info.id, shipment__order__user=user.id,
                                                   ship_status=data_dict['status'][i])
        if not tracking:
            ShipmentTracking.objects.create(shipment_id=shipment_info.id, ship_status=data_dict['status'][i],
                                            creation_date=datetime.datetime.now())
        else:
            tracking.update(ship_status=data_dict['status'][i])

        orig_ship_ref = shipment_info.order_packaging.order_shipment.shipment_reference
        if ship_reference:
            if not ship_reference == orig_ship_ref:
                order_shipment = shipment_info.order_packaging.order_shipment
                order_shipment.shipment_reference = ship_reference
                order_shipment.save()

    return HttpResponse(json.dumps({'status': True, 'message': "Updated Successfully"}));


@csrf_exempt
@login_required
@get_admin_user
def print_shipment(request, user=''):
    data_dict = dict(request.GET.iterlists())
    report_data = []
    for i in range(0, len(data_dict['ship_id'])):
        for key, value in request.GET.iteritems():
            ship_id = data_dict[key][i]
            order_shipment1 = OrderShipment.objects.filter(shipment_number=ship_id, user=user.id)
            if order_shipment1:
                order_shipment = order_shipment1[0]
            else:
                return HttpResponse('No Records')
            order_package = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id).order_by(
                'package_reference')
            package_data = []
            all_data = {}
            total = {}
            report_data.append({'shipment_number': ship_id, 'date': datetime.datetime.now(),
                                'truck_number': order_shipment.truck_number})
            for package in order_package:
                shipment_info = ShipmentInfo.objects.filter(order_packaging_id=package.id)
                for data in shipment_info:
                    cond = data.order.customer_name
                    all_data.setdefault(cond, [])
                    all_data[cond].append({'pack_reference': str(data.order_packaging.package_reference),
                                           'sku_code': str(data.order.sku.sku_code),
                                           'quantity': str(data.shipping_quantity)})

    for key, value in all_data.iteritems():
        total[key] = 0
        for i in value:
            total[key] += float(i['quantity'])

    headers = ('Package Reference', 'SKU Code', 'Shipping Quantity')
    return render(request, 'templates/toggle/shipment_template.html',
                  {'table_headers': headers, 'report_data': report_data,
                   'package_data': all_data, 'total': total})


@csrf_exempt
@login_required
@get_admin_user
def get_sku_categories(request, user=''):
    price_band_flag = get_misc_value('priceband_sync', user.id)
    if price_band_flag == 'true':
        user = get_admin(user)
    brands, categories, sizes, colors, categories_details = get_sku_categories_data(request, user)
    stages_list = list(
        ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    sub_categories = list(SKUMaster.objects.filter(user=user.id).exclude(sub_category='').values_list('sub_category',
                                                                                                      flat=True).distinct())
    return HttpResponse(
        json.dumps({'categories': categories, 'brands': brands, 'size': sizes, 'stages_list': stages_list,
                    'sub_categories': sub_categories, 'colors': colors, \
                    'primary_details': categories_details['primary_details']}))


def fetch_unit_price_based_ranges(dest_loc_id, level, admin_id, wms_code):
    price_ranges_map = {}
    pricemaster_obj = PriceMaster.objects.filter(sku__user=admin_id,
                                                 sku__sku_code=wms_code)

    price_data = NetworkMaster.objects.filter(dest_location_code_id=dest_loc_id).filter(
        source_location_code_id__userprofile__warehouse_level=level). \
        values_list('source_location_code_id', 'price_type')
    nw_pricetypes = [j for i, j in price_data]
    pricemaster_obj = pricemaster_obj.filter(price_type__in=nw_pricetypes)

    if pricemaster_obj:
        for pm_obj in pricemaster_obj:
            pm_obj_map = {'min_unit_range': pm_obj.min_unit_range, 'max_unit_range': pm_obj.max_unit_range,
                          'price': pm_obj.price}
            price_ranges_map.setdefault('price_ranges', []).append(pm_obj_map)

    return price_ranges_map


def apply_margin_price(sku, each_sku_map, specific_margins, is_margin_percentage, default_margin):
    current_price = each_sku_map['price']
    if specific_margins:
        specific_margins = json.loads(specific_margins)
    specific_margin_skus = [(i['wms_code'], i['margin']) for i in specific_margins]
    spc_margin_sku_map = dict(specific_margin_skus)
    each_sku_map['margin'] = 0
    if is_margin_percentage == 'false':
        if sku in spc_margin_sku_map:
            each_sku_map['price'] = current_price + float(spc_margin_sku_map[sku])
            each_sku_map['margin'] = float(spc_margin_sku_map[sku])
        elif default_margin:
            each_sku_map['price'] = current_price + float(default_margin)
            each_sku_map['margin'] = float(default_margin)
    else:
        if sku in spc_margin_sku_map:
            raising_amt = (current_price * float(spc_margin_sku_map[sku])) / 100
            each_sku_map['price'] = current_price + raising_amt
            each_sku_map['margin'] = float(spc_margin_sku_map[sku])
        elif default_margin:
            raising_amt = (current_price * float(default_margin)) / 100
            each_sku_map['price'] = current_price + raising_amt
            each_sku_map['margin'] = float(default_margin)


def get_style_variants(sku_master, user, customer_id='', total_quantity=0, customer_data_id='',
                       prices_dict={}, levels_config=0, dist_wh_id=0, level=0, specific_margins=[],
                       is_margin_percentage=0, default_margin=0, price_type='', is_style_detail=''):
    stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0). \
        values('sku_id').distinct().annotate(in_stock=Sum('quantity'))

    purchase_orders = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']). \
        filter(open_po__sku__user=user.id).values('open_po__sku_id'). \
        annotate(total_order=Sum('open_po__order_quantity'), total_received=Sum('received_quantity'))

    reserved_quantities = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1). \
        values('stock__sku_id').distinct().annotate(in_reserved=Sum('reserved'))

    tax_master = TaxMaster.objects.filter(user_id=user.id)
    rev_inter_states = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))

    stocks = map(lambda d: d['sku_id'], stock_objs)
    intransit_skus = map(lambda d: d['open_po__sku_id'], purchase_orders)
    intransit_ordered = map(lambda d: d['total_order'], purchase_orders)
    intransit_received = map(lambda d: d['total_received'], purchase_orders)
    reserved_skus = map(lambda d: d['stock__sku_id'], reserved_quantities)
    reserved_quans = map(lambda d: d['in_reserved'], reserved_quantities)

    price_band_flag = get_misc_value('priceband_sync', user.id)
    if price_band_flag == 'true':
        central_admin = get_admin(user)
    else:
        central_admin = user

    for ind, sku in enumerate(sku_master):
        stock_quantity = 0
        if sku['id'] in stocks:
            data_value = map(lambda d: d['in_stock'], stock_objs)[stocks.index(sku['id'])]
            if data_value:
                stock_quantity = data_value
        intransit_quantity = 0
        if sku['id'] in intransit_skus:
            total_ordered = map(lambda d: d['total_order'], purchase_orders)[intransit_skus.index(sku['id'])]
            total_received = map(lambda d: d['total_received'], purchase_orders)[intransit_skus.index(sku['id'])]
            diff_quantity = float(total_ordered) - float(total_received)
            if diff_quantity > 0:
                intransit_quantity = diff_quantity
        if sku['id'] in reserved_skus and stock_quantity:
            res_value = reserved_quans[reserved_skus.index(sku['id'])]
            if res_value:
                stock_quantity = stock_quantity - res_value
        total_quantity = total_quantity + stock_quantity
        sku_master[ind]['physical_stock'] = stock_quantity
        sku_master[ind]['intransit_quantity'] = intransit_quantity
        sku_master[ind]['style_quantity'] = total_quantity
        sku_master[ind]['taxes'] = []
        customer_data = []
        sku_master[ind]['your_price'] = prices_dict.get(sku_master[ind]['id'], 0)
        if customer_id:
            customer_user = CustomerUserMapping.objects.filter(user=customer_id)[0].customer.customer_id
            customer_data = CustomerMaster.objects.filter(customer_id=customer_user, user=user.id)
        elif customer_data_id:
            customer_data = CustomerMaster.objects.filter(customer_id=customer_data_id, user=user.id)
        if customer_data:
            taxes = {}
            if customer_data[0].tax_type:
                taxes = list(tax_master.filter(product_type=sku['product_type'],
                                               inter_state=rev_inter_states.get(customer_data[0].tax_type, 2)). \
                             values('product_type', 'inter_state', 'cgst_tax', 'sgst_tax', 'igst_tax', 'min_amt',
                                    'max_amt'))
            sku_master[ind]['taxes'] = taxes
            if customer_data[0].price_type and levels_config != 'true':
                price_data = PriceMaster.objects.filter(sku__user=user.id, sku__sku_code=sku['wms_code'],
                                                        price_type=customer_data[0].price_type)
                if price_data:
                    sku_master[ind]['pricing_price'] = price_data[0].price
                    if price_data[0].price > 0:
                        sku_master[ind]['price'] = price_data[0].price
                else:
                    sku_master[ind]['pricing_price'] = 0
            else:
                is_distributor = customer_data[0].is_distributor
                pricemaster_obj = PriceMaster.objects.filter(sku__user=central_admin.id,
                                                             sku__sku_code=sku['wms_code'])
                if is_distributor:
                    price_data = NetworkMaster.objects.filter(dest_location_code_id=dist_wh_id).filter(
                        source_location_code_id__userprofile__warehouse_level=level). \
                        values_list('source_location_code_id', 'price_type')
                    sku_master[ind].setdefault('prices_map', {}).update(dict(price_data))
                    nw_pricetypes = [j for i, j in price_data]
                    pricemaster_obj = pricemaster_obj.filter(price_type__in=nw_pricetypes)
                    if pricemaster_obj:
                        sku_master[ind]['price'] = pricemaster_obj[0].price
                        sku_master[ind]['your_price'] = pricemaster_obj[0].price
                    else:
                        sku_master[ind]['your_price'] = 0
                else:
                    if is_style_detail != 'true':
                        price_type = 'R-C'
                    if price_type != 'R-C':
                        # Assuming Reseller, taking price type from Customer Master
                        price_type = customer_data[0].price_type
                        # Customer Level price types
                        price_type = update_level_price_type(customer_data[0], level, price_type)

                    pricemaster_obj = pricemaster_obj.filter(price_type=price_type)

                if pricemaster_obj:
                    sku_master[ind]['pricing_price'] = pricemaster_obj[0].price
                    sku_master[ind]['price'] = pricemaster_obj[0].price
                    sku_master[ind]['your_price'] = pricemaster_obj[0].price
                    apply_margin_price(sku['wms_code'], sku_master[ind], specific_margins, is_margin_percentage,
                                       default_margin)
                    for pm_obj in pricemaster_obj:
                        pm_obj_map = {'min_unit_range': pm_obj.min_unit_range, 'max_unit_range': pm_obj.max_unit_range,
                                      'price': pm_obj.price}
                        apply_margin_price(pm_obj.sku.sku_code, pm_obj_map, specific_margins, is_margin_percentage,
                                           default_margin)
                        sku_master[ind].setdefault('price_ranges', []).append(pm_obj_map)
                else:
                    apply_margin_price(sku['wms_code'], sku_master[ind], specific_margins, is_margin_percentage,
                                       default_margin)
                    # current_sku_price = sku_master[ind]['price']
                    # sku_master[ind]['price'] = current_sku_price + float(default_margin)

                    # sku_master[ind]['charge_remarks'] = pricemaster_obj[0].charge_remarks
    return sku_master


@get_admin_user
def get_levels(request, user=''):
    """
    API Call to display levels in Customer portal Dropdown
    :param request:
    :param user: Currently Not Used, But need to distinguish levels based on the User.
    :return:
    """
    is_distributor = ''
    cust_obj = CustomerMaster.objects.filter(user=user.id, name=request.user.first_name)
    if cust_obj:
        is_distributor = cust_obj[0].is_distributor
    if is_distributor:
        levels = list(UserProfile.objects.exclude(warehouse_level=0).values_list('warehouse_level',
                                                                                 flat=True).distinct())
    else:
        levels = list(UserProfile.objects.values_list('warehouse_level', flat=True).distinct())
    return HttpResponse(json.dumps(levels))


def get_leadtimes(user='', level=0):
    same_level_users = get_same_level_warehouses(level)
    lead_times = NetworkMaster.objects.filter(dest_location_code=user,
                                              source_location_code_id__in=same_level_users). \
        values_list('lead_time', 'source_location_code').distinct()
    return dict(lead_times)


def get_same_level_warehouses(level):
    warehouses = UserProfile.objects.filter(warehouse_level=level).values_list('user_id', flat=True)
    return warehouses


def get_stock_qty_leadtime(item, wh_code):
    wms_code = item['wms_code']
    if not isinstance(wh_code, list):
        wh_code = [wh_code]
    lt_stock = StockDetail.objects.filter(sku__user__in=wh_code,
                                          sku__sku_class=item['sku_class'],
                                          quantity__gt=0,
                                          sku__wms_code=wms_code).values_list('sku__wms_code').distinct(). \
        aggregate(Sum('quantity'))['quantity__sum']
    reserved_quantities = PicklistLocation.objects.filter(stock__sku__user__in=wh_code,
                                                          stock__sku__wms_code=wms_code,
                                                          status=1).values_list('stock__sku__wms_code'). \
        aggregate(Sum('reserved'))['reserved__sum']
    enquiry_res_quantities = EnquiredSku.objects.filter(sku__user__in=wh_code, sku_code=wms_code). \
        values_list('sku_code').aggregate(Sum('quantity'))['quantity__sum']
    if not reserved_quantities:
        reserved_quantities = 0
    if not enquiry_res_quantities:
        enquiry_res_quantities = 0
    if not lt_stock:
        lt_stock = 0
    avail_stock = int(lt_stock) - int(reserved_quantities) - int(enquiry_res_quantities)
    if avail_stock > 0:
        return avail_stock
    else:
        return None


def all_whstock_quant(sku_master, user, level=0, lead_times=None, dist_reseller_leadtime=0):
    stock_display_warehouse = get_misc_value('stock_display_warehouse', user.id)
    if stock_display_warehouse != "false":
        stock_display_warehouse = map(int, stock_display_warehouse.split(','))
    else:
        stock_display_warehouse = get_same_level_warehouses(level)
    stock_qty_all = dict(StockDetail.objects.filter(sku__user__in=stock_display_warehouse,
                                                    sku__sku_class=sku_master[0]['sku_class'],
                                                    quantity__gt=0).values_list('sku__wms_code').distinct().
                         annotate(in_stock=Sum('quantity')))

    purchase_orders_obj = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']). \
        filter(open_po__sku__user__in=stock_display_warehouse,
               open_po__sku__sku_class=sku_master[0]['sku_class'])

    ordered_qties = dict(purchase_orders_obj.values_list('open_po__sku__wms_code').
                         annotate(total_order=Sum('open_po__order_quantity')))
    recieved_qties = dict(purchase_orders_obj.values_list('open_po__sku__wms_code').
                          annotate(total_recieved=Sum('received_quantity')))

    reserved_quantities = dict(PicklistLocation.objects.filter(stock__sku__user__in=stock_display_warehouse,
                                                               stock__sku__sku_class=sku_master[0]['sku_class'],
                                                               status=1).values_list(
        'stock__sku__wms_code').distinct().annotate(in_reserved=Sum('reserved')))

    putaway_pending_job = dict(POLocation.objects.filter(location__zone__user__in=stock_display_warehouse, status=1,
                                                         job_order__product_code__sku_class=sku_master[0][
                                                             'sku_class']).values_list(
        'job_order__product_code__wms_code').distinct().annotate(Sum('quantity')))

    putaway_pending_purchase = dict(
        POLocation.objects.filter(location__zone__user__in=stock_display_warehouse, status=1,
                                  purchase_order__open_po__sku__sku_class=sku_master[0]['sku_class']).values_list(
            'purchase_order__open_po__sku__wms_code').distinct().annotate(Sum('quantity')))

    job_order_pro_qty = dict(JobOrder.objects.filter(product_code__user__in=stock_display_warehouse,
                                                     product_code__sku_class=sku_master[0]['sku_class']).values_list(
        'product_code__wms_code').distinct().annotate(Sum('product_quantity')))

    job_order_rec_qty = dict(JobOrder.objects.filter(product_code__user__in=stock_display_warehouse,
                                                     product_code__sku_class=sku_master[0]['sku_class']).values_list(
        'product_code__wms_code').distinct().annotate(Sum('received_quantity')))

    day_1_total = 0
    day_3_total = 0
    total_qty = {}
    for item in sku_master:
        ordered_qty = ordered_qties.get(item["wms_code"], 0)
        recieved_qty = recieved_qties.get(item["wms_code"], 0)

        putaway_pending_job_qty = putaway_pending_job.get(item["wms_code"], 0)
        putaway_pending_purchase_qty = putaway_pending_purchase.get(item["wms_code"], 0)

        job_order_product_qty = job_order_pro_qty.get(item["wms_code"], 0)
        job_order_recieved_qty = job_order_rec_qty.get(item["wms_code"], 0)

        intransit_qty = ordered_qty - recieved_qty

        reserved_qty = reserved_quantities.get(item["wms_code"], 0)
        stock_qty = stock_qty_all.get(item["wms_code"], 0)

        job_order_qty = job_order_product_qty - job_order_recieved_qty + putaway_pending_job_qty

        all_quantity = stock_qty - reserved_qty + intransit_qty + putaway_pending_purchase_qty + job_order_qty
        if user.id in stock_display_warehouse:
            all_quantity -= item['physical_stock']
        item['all_quantity'] = all_quantity
        if lead_times:
            for lead_time, wh_code in lead_times.items():
                output = get_stock_qty_leadtime(item, wh_code)
                if dist_reseller_leadtime and level:
                    item[lead_time + dist_reseller_leadtime] = output
                else:
                    item[lead_time] = output

        day_1_total += item['physical_stock']
        day_3_total += item['all_quantity']
    total_qty['physical_stock'] = day_1_total
    total_qty['all_quantity'] = day_3_total
    return sku_master, total_qty


@csrf_exempt
@login_required
@get_admin_user
def get_sku_catalogs(request, user=''):
    data, start, stop = get_sku_catalogs_data(request, user)
    download_pdf = request.POST.get('share', '')
    if download_pdf:
        remarks = ''
        remarks = MiscDetail.objects.filter(user=user.id, misc_type='customer_pdf_remarks')
        if remarks:
            remarks = remarks[0].misc_value
        display_stock = request.POST.get('display_stock', '')
        user_type = request.POST.get('user_type', '')
        admin = get_admin(user)
        image = get_company_logo(admin)
        date = get_local_date(user, datetime.datetime.now())
        if user_type in ['reseller', 'distributor']:
            t = loader.get_template('templates/reseller_search.html')
        else:
            t = loader.get_template('templates/customer_search.html')
        rendered = t.render({'data': data, 'user': request.user.first_name, 'date': date,
                             'remarks': remarks, 'display_stock': display_stock, 'image': image,
                             'style_quantities': eval(request.POST.get('required_quantity', '{}'))})

        if not os.path.exists('static/pdf_files/'):
            os.makedirs('static/pdf_files/')
        file_name = 'static/pdf_files/%s_customer_search.html' % str(request.user.id)
        name = str(request.user.id) + "_customer_search"
        pdf_file = 'static/pdf_files/%s.pdf' % name
        file_ = open(file_name, "w+b")
        file_.write(str(rendered))
        file_.close()
        os.system("./phantom/bin/phantomjs ./phantom/examples/rasterize.js ./%s ./%s A4" % (file_name, pdf_file))
        return HttpResponse("static/pdf_files/" + str(request.user.id) + "_customer_search.pdf")
    return HttpResponse(json.dumps({'data': data, 'next_index': str(start + 20) + ':' + str(stop + 20)}))


@csrf_exempt
@login_required
@get_admin_user
def get_sku_variants(request, user=''):
    filter_params = {'user': user.id}
    get_values = ['wms_code', 'sku_desc', 'image_url', 'sku_class', 'price', 'mrp', 'id', 'sku_category', 'sku_brand',
                  'sku_size', 'style_name', 'product_type']
    reseller_leadtimes = {}
    lead_times = {}
    sku_class = request.POST.get('sku_class', '')
    customer_id = request.POST.get('customer_id', '')
    customer_data_id = request.POST.get('customer_data_id', '')
    sku_code = request.POST.get('sku_code', '')
    is_catalog = request.POST.get('is_catalog', '')
    sale_through = request.POST.get('sale_through', '')
    level = request.POST.get('level', '')
    if level:
        level = int(level)
    else:
        level = 0
    is_style_detail = request.POST.get('is_style_detail', '')
    levels_config = get_misc_value('generic_wh_level', user.id)
    cust_obj = CustomerMaster.objects.filter(user=user.id, name=request.user.first_name)
    if cust_obj:
        is_distributor = cust_obj[0].is_distributor
        dist_reseller_leadtime = cust_obj[0].lead_time
    else:
        dist_reseller_leadtime = 0
        is_distributor = 0
    if sku_class:
        filter_params['sku_class'] = sku_class
    if sku_code:
        filter_params['sku_code'] = sku_code
    if is_catalog:
        filter_params['status'] = 1
    if sale_through:
        filter_params['sale_through__iexact'] = sale_through

    sku_master = list(SKUMaster.objects.filter(**filter_params).values(*get_values).order_by('sequence'))
    dist_userid = 0
    if levels_config == 'true':
        if is_distributor:
            customer_user = CustomerUserMapping.objects.filter(user=request.user.id)[0].customer.customer_id
            cm_id = CustomerMaster.objects.filter(customer_id=customer_user, user=user.id)
            if cm_id:
                dist_mapping = WarehouseCustomerMapping.objects.filter(customer_id=cm_id, status=1)
                dist_userid = dist_mapping[0].warehouse_id
                lead_times = get_leadtimes(dist_userid, level)
        else:
            if level:
                lead_times = get_leadtimes(user.id, level)
                reseller_leadtimes = map(lambda x: x + dist_reseller_leadtime, lead_times)
            else:
                lead_times = {dist_reseller_leadtime: user.id}
                reseller_leadtimes = [dist_reseller_leadtime]
    sku_master = get_style_variants(sku_master, user, customer_id=customer_id, customer_data_id=customer_data_id,
                                    levels_config=levels_config, dist_wh_id=dist_userid, level=level,
                                    is_style_detail=is_style_detail
                                    )
    if get_priceband_admin_user(user):
        wh_admin = get_priceband_admin_user(user)
        integration_obj = Integrations.objects.filter(user = user.id)
        if integration_obj:
            company_name = integration_obj[0].name
            integration_users = Integrations.objects.filter(name = company_name).values_list('user', flat=True)
            for user_id in integration_users:
                user = User.objects.get(id = user_id)
                #if qssi, update inventory first
                if company_name == "qssi":
                    sku_ids = [item['wms_code'] for item in sku_master]
                    api_resp = get_inventory(sku_ids, user)
                    if api_resp.get("Status", "").lower() == "success":
                        for warehouse in resp["Warehouses"]:
                            if warehouse["WarehouseId"] == user.username:
                                for item in warehouse["Result"]["InventoryStatus"]:
                                    sku_id = item["SKUId"]
                                    inventory = item["Inventory"]
                                    sku = SKUMaster.objects.filter(user = user_id, sku_code = sku_id)
                                    if sku:
                                        sku = sku[0]
                                        stock_detail = StockDetail.objects.filter(sku_id = sku.id)
                                        if stock_detail:
                                            stock_detail = stock_detail[0]
                                            stock_detail.quantity = inventory
                                            stock_detail.save()
                                            log.info("Stock updated for sku: %s" %(sku_id))
    sku_master, total_qty = all_whstock_quant(sku_master, user, level, lead_times, dist_reseller_leadtime)
    _data = {'data': sku_master, 'gen_wh_level_status': levels_config, 'total_qty': total_qty, }
    if not is_distributor:
        _data['lead_times'] = reseller_leadtimes
    else:
        _data['lead_times'] = lead_times.keys()
    if levels_config != 'true':
        _data.update({'style_headers': STYLE_DETAIL_HEADERS})
    else:
        _data.update({'style_headers': STYLE_DETAIL_WITHOUT_STATIC_LEADTIME})
    return HttpResponse(json.dumps(_data))


def modify_invoice_data(invoice_data, user):
    data = {}
    new_data = []
    detailed_invoice = get_misc_value('detailed_invoice', user.id)
    detailed_invoice = True if (detailed_invoice == 'true') else False
    invoice_data['detailed_invoice'] = detailed_invoice
    sku_class = []
    if detailed_invoice:
        mydata = sorted(invoice_data['data'], key=lambda item: item["sku_category"])
        for key, group in groupby(mydata, lambda item: item["sku_category"]):
            data[key] = list(group)

        for one in data.keys():
            category = one

            data_to = sorted(data[one], key=lambda item: item["unit_price"])
            for key2, group2 in groupby(data_to, lambda item: item["unit_price"]):
                price = key2
                discount, invoice_amount, quantity, tax, amount = 0, 0, 0, 0, 0
                sku_list = OrderedDict()
                styles_att = {'discount': 0, 'invoice_amount': 0, 'quantity': 0, 'tax': 0, 'amount': 0, 'sku_size': {},
                              'display_sizes': [], 'amt': 0}
                styles = {}
                sub_total = 0
                amt = 0
                base_price = 0
                taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'cgst_amt': 0, 'sgst_amt': 0, 'igst_amt': 0}
                for single_entry in group2:
                    if not single_entry['sku_class'] in styles:
                        styles[single_entry['sku_class']] = copy.deepcopy(styles_att)
                    styles[single_entry['sku_class']]['sku_size'][single_entry['sku_size']] = int(
                        single_entry['quantity'])
                    if not single_entry['sku_size'] in styles[single_entry['sku_class']]['display_sizes']:
                        styles[single_entry['sku_class']]['display_sizes'].append(single_entry['sku_size'])
                    if not styles[single_entry['sku_class']].has_key('hsn_code'):
                        styles[single_entry['sku_class']]['hsn_code'] = single_entry['hsn_code']
                    discount += float(single_entry['discount'])
                    invoice_amount += float(single_entry['invoice_amount'])
                    quantity += single_entry['quantity']
                    tax += float(single_entry['tax'])
                    amount += invoice_amount
                    main_class = single_entry['sku_class']
                    vat = single_entry['vat']
                    amt += single_entry['amt']
                    base_price = single_entry['base_price']
                    if single_entry.has_key('taxes') and single_entry['taxes'].has_key('cgst_tax'):
                        taxes['cgst_tax'] = single_entry['taxes']['cgst_tax']
                        taxes['sgst_tax'] = single_entry['taxes']['sgst_tax']
                        taxes['igst_tax'] = single_entry['taxes']['igst_tax']
                        taxes['cgst_amt'] += float(single_entry['taxes']['cgst_amt'])
                        taxes['sgst_amt'] += float(single_entry['taxes']['sgst_amt'])
                        taxes['igst_amt'] += float(single_entry['taxes']['igst_amt'])
                total = amount - tax
                new_data.append(
                    {'price': price, 'sku_class': sku_list, 'discount': discount, 'invoice_amount': invoice_amount,
                     'quantity': quantity, 'tax': tax, 'amount': amount, 'category': category, 'vat': vat,
                     'styles': styles, 'amt': amt, 'taxes': taxes, 'base_price': base_price})
        invoice_data['data'] = new_data
    return invoice_data


@csrf_exempt
@login_required
@get_admin_user
def generate_order_invoice(request, user=''):
    order_ids = request.GET.get('order_ids', '')
    invoice_data = get_invoice_data(order_ids, user)
    invoice_data = modify_invoice_data(invoice_data, user)
    ord_ids = order_ids.split(",")
    invoice_data = add_consignee_data(invoice_data, ord_ids, user)
    user_profile = UserProfile.objects.get(user_id=user.id)
    # invoice_data = build_invoice(invoice_data, user, False)
    if get_misc_value('show_imei_invoice', user.id) == 'true':
        invoice_data = build_marketplace_invoice(invoice_data, user, False)
    else:
        invoice_data = build_invoice(invoice_data, user, False)
    # invoice_data.update({'user': user})
    # if invoice_data['detailed_invoice']:
    #    t = loader.get_template('../miebach_admin/templates/toggle/detail_generate_invoice.html')
    # else:
    #    t = loader.get_template('../miebach_admin/templates/toggle/generate_invoice.html')
    # c = Context(invoice_data)
    # rendered = t.render(c)
    return HttpResponse(invoice_data)


@csrf_exempt
def get_shipment_picked(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                        user_dict={}, filters={}):
    '''Shipment Info datatable code '''

    sku_master, sku_master_ids = get_sku_master(user, request.user)
    if user_dict:
        user_dict = eval(user_dict)
    lis = ['id', 'order__order_id', 'order__sku__sku_code', 'order__title', 'order__customer_id',
           'order__customer_name',
           'order__marketplace', 'picked_quantity']
    data_dict = {'status__icontains': 'picked', 'order__user': user.id, 'picked_quantity__gt': 0}

    if user_dict.get('market_place', ''):
        marketplace = user_dict['market_place'].split(',')
        data_dict['order__marketplace__in'] = marketplace
    if user_dict.get('customer', ''):
        data_dict['order__customer_id'], data_dict['order__customer_name'] = user_dict['customer'].split(':')

    search_params = get_filtered_params(filters, lis[1:])

    if search_term:
        master_data = Picklist.objects.filter(
            Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids)). \
            filter(Q(order__order_id__icontains=search_term) |
                   Q(order__sku__sku_code__icontains=search_term) |
                   Q(order__title__icontains=search_term) | Q(order__customer_id__icontains=search_term) |
                   Q(order__customer_name__icontains=search_term) | Q(picked_quantity__icontains=search_term) |
                   Q(order__marketplace__icontains=search_term), **data_dict). \
            values_list('order_id', flat=True).distinct()

    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = Picklist.objects.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids),
                                              **data_dict). \
            filter(**search_params).order_by(order_data). \
            values_list('order_id', flat=True).distinct()
    else:
        master_data = Picklist.objects.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids),
                                              **data_dict). \
            filter(**search_params).order_by('updation_date'). \
            values_list('order_id', flat=True).distinct()

    master_data = list(OrderedDict.fromkeys(master_data))
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    count = 0
    for dat in master_data[start_index:stop_index]:
        data = OrderDetail.objects.get(id=dat)
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (dat, data.sku.sku_code)
        quantity = data.quantity
        shipped = ShipmentInfo.objects.filter(order_id=dat).aggregate(Sum('shipping_quantity'))[
            'shipping_quantity__sum']
        if shipped:
            quantity = float(quantity) - shipped
            if quantity < 0:
                continue

        temp_data['aaData'].append(
            OrderedDict((('', checkbox), ('Order ID', str(data.order_id)), ('SKU Code', data.sku.sku_code),
                         ('Title', data.title), ('id', count), ('Customer ID', data.customer_id),
                         ('Customer Name', data.customer_name), ('Marketplace', data.marketplace),
                         ('Picked Quantity', quantity),
                         ('DT_RowClass', 'results'), ('order_id', dat))))
        count = count + 1


@csrf_exempt
@get_admin_user
def generate_order_jo_data(request, user=''):
    all_data = []
    title = 'Raise Job Order'
    data_dict = dict(request.POST.iterlists())

    order_id = request.POST.get('order_id', '')
    order_details = OrderDetail.objects.none()
    if order_id:
        for i in range(0, len(data_dict['order_id'])):
            main_id = data_dict['order_id'][i]
            order_code = ''.join(re.findall('\D+', main_id))
            order_id = ''.join(re.findall('\d+', main_id))
            order_details = order_details | OrderDetail.objects.filter(Q(order_id=order_id, \
                                                                         order_code=order_code) | Q(
                original_order_id=main_id), user=user.id)
    else:
        order_details = OrderDetail.objects.filter(id__in=data_dict['id'], user=user.id)
    for sku_id in order_details.values('sku__id').distinct():
        order_detail = order_details.filter(sku__id=sku_id['sku__id'])
        data = []
        product_qty = order_detail.aggregate(Sum('quantity'))['quantity__sum']
        data_id = ','.join([str(order_id.id) for order_id in order_detail])
        order_detail = order_detail[0]
        bom_master = BOMMaster.objects.filter(product_sku__sku_code=order_detail.sku.sku_code,
                                              product_sku__user=user.id)
        if bom_master:
            for bom in bom_master:
                data.append(
                    {'material_code': bom.material_sku.sku_code, 'material_quantity': float(bom.material_quantity),
                     'id': '', 'measurement_type': bom.unit_of_measurement})
        all_data.append(
            {'order_id': data_id, 'product_code': order_detail.sku.sku_code, 'product_description': product_qty,
             'description': order_detail.sku.sku_desc, 'sub_data': data})

    return HttpResponse(json.dumps({'data': all_data}))


@get_admin_user
def search_customer_data(request, user=''):
    search_key = request.GET.get('q', '')
    total_data = []

    if not search_key:
        return HttpResponse(json.dumps(total_data))

    lis = ['name', 'email_id', 'phone_number', 'address', 'status', 'tax_type']
    master_data = CustomerMaster.objects.filter(Q(phone_number__icontains=search_key) | Q(name__icontains=search_key) |
                                                Q(customer_id__icontains=search_key), user=user.id)

    for data in master_data[:30]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        total_data.append({'customer_id': data.customer_id, 'name': data.name, 'phone_number': str(data.phone_number),
                           'email': data.email_id, 'address': data.address, 'tax_type': data.tax_type})
    return HttpResponse(json.dumps(total_data))


@csrf_exempt
@get_admin_user
def generate_order_po_data(request, user=''):
    data_dict = []
    supplier_list = []
    suppliers = SupplierMaster.objects.filter(user=user.id)
    for supplier in suppliers:
        supplier_list.append({'id': supplier.id, 'name': supplier.name})
    request_dict = dict(request.POST.iterlists())
    order_id = request.POST.get('order_id', '')
    order_details = OrderDetail.objects.none()
    if order_id:
        for i in range(0, len(request_dict['order_id'])):
            main_id = request_dict['order_id'][i]
            order_code = ''.join(re.findall('\D+', main_id))
            order_id = ''.join(re.findall('\d+', main_id))
            order_details = order_details | OrderDetail.objects.filter(Q(order_id=order_id, \
                                                                         order_code=order_code) | Q(
                original_order_id=main_id), user=user.id)
    else:
        order_details = OrderDetail.objects.filter(id__in=request_dict['id'], user=user.id)

    for sku_id in order_details.values('sku__id').distinct():
        order_detail = order_details.filter(sku__id=sku_id['sku__id'])
        product_qty = order_detail.aggregate(Sum('quantity'))['quantity__sum']
        data_id = ','.join([str(order_id.id) for order_id in order_detail])
        price = 0
        selected_item = ''
        order_detail = order_detail[0]
        sku_supplier = SKUSupplier.objects.filter(sku__wms_code=order_detail.sku.wms_code, sku__user=user.id)
        if sku_supplier:
            selected_item = {'id': sku_supplier[0].supplier_id, 'name': sku_supplier[0].supplier.name}
            price = sku_supplier[0].price
        else:
            selected_item = supplier_list[1]
        data_dict.append({'order_id': data_id, 'wms_code': order_detail.sku.wms_code, 'title': order_detail.title,
                          'quantity': product_qty, 'selected_item': selected_item, 'price': price})

    return HttpResponse(json.dumps({'data_dict': data_dict, 'supplier_list': supplier_list}))


@csrf_exempt
@get_admin_user
def get_stock_transfer_details(request, user=''):
    ids = request.GET.get('order_id', '')
    main_ids = []
    if ids:
        main_ids = ids.split(",")
    else:
        HttpResponse("Fail")

    total_data = {}
    order_details_data = []

    for order_id in main_ids:
        order_data = get_order_detail_objs(order_id, user)
        for sku_data in order_data:
            if total_data.has_key(sku_data.sku.sku_code):
                total_data[sku_data.sku.sku_code]['order_quantity'] += int(
                    total_data[sku_data.sku.sku_code]['order_quantity'])
            else:
                total_data[sku_data.sku.sku_code] = {'order_quantity': int(sku_data.quantity),
                                                     'wms_code': sku_data.sku.sku_code, 'price': 0}

    order_details_data = total_data.values()

    return HttpResponse(json.dumps({'data_dict': order_details_data}))


@csrf_exempt
@get_admin_user
def get_seller_order_details(request, user=''):
    sor_id = request.GET.get('sor_id', '')
    uor_id = request.GET.get('uor_id', '')
    if not sor_id and uor_id:
        return HttpResponse("Fail")

    order_code = ''.join(re.findall('\D+', uor_id))
    order_id = ''.join(re.findall('\d+', uor_id))
    seller_data = SellerOrder.objects.filter(Q(order__order_id=order_id, order__order_code=order_code) | \
                                             Q(order__original_order_id=order_id), order__user=user.id, sor_id=sor_id,
                                             status=1)

    order_details = seller_data
    seller_details = seller_data[0].seller.json()
    row_id = order_details[0].id

    custom_data = OrderJson.objects.filter(order_id=row_id)
    status_obj = ''
    central_remarks = ''
    customer_order_summary = CustomerOrderSummary.objects.filter(order_id=row_id)
    if customer_order_summary:
        status_obj = customer_order_summary[0].status
        central_remarks = customer_order_summary[0].central_remarks

    data_dict = []
    cus_data = []
    order_details_data = []
    sku_id_list = []
    attr_list = []
    if custom_data:
        attr_list = json.loads(custom_data[0].json_data)
        if isinstance(attr_list, dict):
            attr_list = attr_list.get('attribute_data', '')
        else:
            attr_list = []
    for attr in attr_list:
        tuple_data = (attr['attribute_name'], attr['attribute_value'])
        cus_data.append(tuple_data)
    for one_order in order_details:
        quantity = one_order.quantity
        one_order = one_order.order
        order_id = one_order.order_id
        _order_id = order_id
        order_code = one_order.order_code
        market_place = one_order.marketplace
        order_id = order_code + str(order_id)
        original_order_id = one_order.original_order_id
        if original_order_id:
            order_id = original_order_id
        customer_id = one_order.customer_id
        customer_name = one_order.customer_name
        shipment_date = get_local_date(request.user, one_order.shipment_date)
        phone = one_order.telephone
        email = one_order.email_id
        address = one_order.address
        city = one_order.city
        state = one_order.state
        pin = one_order.pin_code
        sku_id = one_order.sku_id
        sku_id_list.append(sku_id)
        product_title = one_order.title
        invoice_amount = one_order.invoice_amount
        remarks = one_order.remarks
        sku_code = one_order.sku.sku_code
        sku_type = one_order.sku.sku_type
        field_type = 'product_attribute'
        vend_dict = {'printing_vendor': "", 'embroidery_vendor': "", 'production_unit': ""}
        sku_extra_data = {}
        if str(order_code) == 'CO':
            vendor_list = ['printing_vendor', 'embroidery_vendor', 'production_unit']
            for item in vendor_list:
                var = ""
                map_obj = OrderMapping.objects.filter(order__order_id=_order_id, order__user=user.id, mapping_type=item)
                if map_obj:
                    var_id = map_obj[0].mapping_id
                    vend_obj = VendorMaster.objects.filter(id=var_id)
                    if vend_obj:
                        var = vend_obj[0].name
                        vend_dict[item] = var

            order_json = OrderJson.objects.filter(order_id=one_order.id)
            if order_json:
                sku_extra_data = eval(order_json[0].json_data)

        order_details_data.append(
            {'product_title': product_title, 'quantity': quantity, 'invoice_amount': invoice_amount, 'remarks': remarks,
             'cust_id': customer_id, 'cust_name': customer_name, 'phone': phone, 'email': email, 'address': address,
             'city': city,
             'state': state, 'pin': pin, 'shipment_date': str(shipment_date), 'item_code': sku_code,
             'order_id': order_id,
             'image_url': one_order.sku.image_url, 'market_place': one_order.marketplace,
             'order_id_code': one_order.order_code + str(one_order.order_id),
             'print_vendor': vend_dict['printing_vendor'],
             'embroidery_vendor': vend_dict['embroidery_vendor'], 'production_unit': vend_dict['production_unit'],
             'sku_extra_data': sku_extra_data})
    data_dict.append({'cus_data': cus_data, 'status': status_obj, 'ord_data': order_details_data,
                      'central_remarks': central_remarks, 'seller_details': seller_details})

    return HttpResponse(json.dumps({'data_dict': data_dict}))


@csrf_exempt
@get_admin_user
def get_view_order_details(request, user=''):
    view_order_status = get_misc_value('view_order_status', user.id)

    view_order_status = view_order_status.split(',')

    all_status = [key for key, value in CUSTOM_ORDER_STATUS.iteritems() if value in view_order_status]

    data_dict = []
    main_id = request.GET.get('order_id', '')
    row_id = request.GET.get('id', '')
    sor_id = request.GET.get('sor_id', '')
    if sor_id:
        order_id = request.GET.get('uor_id', '')
        order_code = ''.join(re.findall('\D+', order_id))
        order_id = ''.join(re.findall('\d+', order_id))
        # seller_data = SellerOrder.objects.filter(sor_id = seller, order__order_id = float(order_id[2:]), order__user=user.id)
        seller_data = SellerOrder.objects.filter(Q(order__order_id=order_id, order__order_code=order_code) | \
                                                 Q(order__original_order_id=order_id), order__user=user.id,
                                                 sor_id=sor_id)
        order_details = seller_data[0].order
        row_id = order_details.id
        order_details = [order_details]
    else:
        order_code = ''.join(re.findall('\D+', main_id))
        order_id = ''.join(re.findall('\d+', main_id))
        order_details = OrderDetail.objects.filter(
            Q(order_id=order_id, order_code=order_code) | Q(original_order_id=main_id), user=user.id)
        if not row_id:
            row_id = order_details[0].id
    custom_data = OrderJson.objects.filter(order_id=row_id)
    status_obj = ''
    central_remarks = ''
    customer_order_summary = CustomerOrderSummary.objects.filter(order_id=row_id)
    if customer_order_summary:
        status_obj = customer_order_summary[0].status
        central_remarks = customer_order_summary[0].central_remarks

    cus_data = []
    order_details_data = []
    sku_id_list = []
    attr_list = []
    if custom_data:
        attr_list = json.loads(custom_data[0].json_data)
        if isinstance(attr_list, dict):
            attr_list = attr_list.get('attribute_data', '')
        else:
            attr_list = []

    tax_type = ''
    inter_state = 2
    if customer_order_summary:
        inter_state = customer_order_summary[0].inter_state
        if customer_order_summary[0].inter_state == 0:
            tax_type = 'intra_state'
        elif customer_order_summary[0].inter_state == 1:
            tax_type = 'inter_state'

    for attr in attr_list:
        tuple_data = (attr['attribute_name'], attr['attribute_value'])
        cus_data.append(tuple_data)
    for one_order in order_details:
        order_id = one_order.order_id
        _order_id = order_id
        order_code = one_order.order_code
        market_place = one_order.marketplace
        order_id = order_code + str(order_id)
        original_order_id = one_order.original_order_id
        if original_order_id:
            order_id = original_order_id
        customer_id = one_order.customer_id
        customer_name = one_order.customer_name
        shipment_date = get_local_date(request.user, one_order.shipment_date)
        phone = one_order.telephone
        email = one_order.email_id
        address = one_order.address
        city = one_order.city
        state = one_order.state
        pin = one_order.pin_code
        sku_id = one_order.sku_id
        sku_id_list.append(sku_id)
        product_title = one_order.title
        quantity = one_order.quantity
        unit_price = one_order.unit_price
        invoice_amount = one_order.invoice_amount
        remarks = one_order.remarks
        sku_code = one_order.sku.sku_code
        sku_type = one_order.sku.sku_type
        field_type = 'product_attribute'
        vend_dict = {'printing_vendor': "", 'embroidery_vendor': "", 'production_unit': ""}
        sku_extra_data = {}
        if str(order_code) == 'CO':
            vendor_list = ['printing_vendor', 'embroidery_vendor', 'production_unit']
            for item in vendor_list:
                var = ""
                map_obj = OrderMapping.objects.filter(order__order_id=_order_id, order__user=user.id, mapping_type=item)
                if map_obj:
                    var_id = map_obj[0].mapping_id
                    vend_obj = VendorMaster.objects.filter(id=var_id)
                    if vend_obj:
                        var = vend_obj[0].name
                        vend_dict[item] = var

            order_json = OrderJson.objects.filter(order_id=one_order.id)
            if order_json:
                sku_extra_data = json.loads(order_json[0].json_data)
                if sku_extra_data.get('image_data', ''):
                    for key, value in sku_extra_data['image_data'].iteritems():
                        sku_extra_data['image_data'][key] = resize_image(value, user)

        customer_order = CustomerOrderSummary.objects.filter(order_id=one_order.id)
        sgst_tax = 0
        cgst_tax = 0
        igst_tax = 0
        discount_percentage = 0
        if customer_order:
            sgst_tax = customer_order[0].sgst_tax
            cgst_tax = customer_order[0].cgst_tax
            igst_tax = customer_order[0].igst_tax
            discount_percentage = 0
            if (quantity * unit_price):
                discount_percentage = float(
                    "%.1f" % (float((customer_order[0].discount * 100) / (quantity * unit_price))))

        tax_masters = TaxMaster.objects.filter(user_id=user.id, product_type=one_order.sku.product_type,
                                               inter_state=inter_state)
        taxes_data = []
        for tax_master in tax_masters:
            taxes_data.append(tax_master.json())

        order_details_data.append(
            {'product_title': product_title, 'quantity': quantity, 'invoice_amount': invoice_amount, 'remarks': remarks,
             'cust_id': customer_id, 'cust_name': customer_name, 'phone': phone, 'email': email, 'address': address,
             'city': city,
             'state': state, 'pin': pin, 'shipment_date': str(shipment_date), 'item_code': sku_code,
             'order_id': order_id,
             'image_url': one_order.sku.image_url, 'market_place': one_order.marketplace,
             'order_id_code': one_order.order_code + str(one_order.order_id),
             'print_vendor': vend_dict['printing_vendor'],
             'embroidery_vendor': vend_dict['embroidery_vendor'], 'production_unit': vend_dict['production_unit'],
             'sku_extra_data': sku_extra_data, 'sgst_tax': sgst_tax, 'cgst_tax': cgst_tax, 'igst_tax': igst_tax,
             'unit_price': unit_price, 'discount_percentage': discount_percentage, 'taxes': taxes_data,
             'sku_status': one_order.status})

    data_dict.append({'cus_data': cus_data, 'status': status_obj, 'ord_data': order_details_data,
                      'central_remarks': central_remarks, 'all_status': all_status, 'tax_type': tax_type})

    return HttpResponse(json.dumps({'data_dict': data_dict}))


def get_stock_location_quantity_data(wms_code, location, user):
    filter_params = {'sku__user': user.id}
    picklist_filter = {'stock__sku__user': user.id, 'status': 1}
    rm_filter = {'material_picklist__jo_material__material_code__user': user.id, 'status': 1}
    if wms_code:
        sku_master = SKUMaster.objects.filter(user=user.id, wms_code=wms_code)
        if not sku_master:
            return 0, 'Invalid SKU Code'
        filter_params['sku__wms_code'] = wms_code
        picklist_filter['stock__sku__wms_code'] = wms_code
        rm_filter['stock__sku__wms_code'] = wms_code

    if location:
        location_master = LocationMaster.objects.filter(zone__user=user.id, location=location)
        if not location_master:
            return 0, 'Invalid Location'
        filter_params['location__location'] = location
        picklist_filter['stock__location__location'] = location
        rm_filter['stock__location__location'] = location

    stock_quantity = StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE').filter(**filter_params). \
        aggregate(Sum('quantity'))['quantity__sum']

    reserved_quantity = PicklistLocation.objects.filter(**picklist_filter).aggregate(Sum('reserved'))['reserved__sum']

    raw_reserved = RMLocation.objects.filter(**rm_filter).aggregate(Sum('reserved'))['reserved__sum']
    if not stock_quantity:
        stock_quantity = 0
    if not reserved_quantity:
        reserved_quantity = 0
    if raw_reserved:
        reserved_quantity += float(raw_reserved)
    diff = stock_quantity - reserved_quantity

    if diff < 0:
        diff = 0

    return diff, ''


@csrf_exempt
@get_admin_user
def get_stock_location_quantity(request, user=''):
    wms_code = request.GET.get('wms_code')
    location = request.GET.get('location')
    diff, message = get_stock_location_quantity_data(wms_code, location, user)
    if message:
        return HttpResponse(json.dumps({'message': message}))

    return HttpResponse(json.dumps({'stock': diff, 'message': 'Success'}))


@login_required
@csrf_exempt
@get_admin_user
def payment_tracker(request, user=''):
    response = {}
    total_payment_received = 0
    total_invoice_amount = 0
    total_payment_receivable = 0
    status_filter = request.GET.get('filter', '')
    all_picklists = Picklist.objects.filter(order__user=user.id)
    invoiced = all_picklists.filter(order__user=user.id, status__in=['picked', 'batch_picked', 'dispatched']). \
        values_list('order__order_id', flat=True).distinct()
    partial_invoiced = all_picklists.filter(order__user=user.id, picked_quantity__gt=0,
                                            status__icontains='open').values_list('order__order_id',
                                                                                  flat=True).distinct()
    total_data = OrderDetail.objects.filter(user=user.id, marketplace__iexact='offline').annotate(
        total_invoice=Sum('invoice_amount'),
        total_received=Sum('payment_received')).filter(total_received__lt=F('total_invoice'))
    if status_filter == 'Partially Invoiced':
        total_data = total_data.filter(order_id__in=partial_invoiced)
    if status_filter == 'Invoiced':
        total_data = total_data.filter(order_id__in=invoiced)
    if status_filter == 'Order Created':
        total_data = total_data.exclude(order_id__in=list(chain(invoiced, partial_invoiced)))

    orders = total_data.values('order_id', 'order_code', 'original_order_id', 'payment_mode').distinct()
    total_customer_data = total_data.values('customer_id', 'customer_name', 'marketplace').distinct()
    customer_data = []
    for data in total_customer_data:
        sum_data = total_data.filter(customer_id=data['customer_id'], customer_name=data['customer_name']).aggregate(
            Sum('payment_received'),
            Sum('invoice_amount'))
        receivable = sum_data['invoice_amount__sum'] - sum_data['payment_received__sum']
        total_payment_received += sum_data['payment_received__sum']
        total_invoice_amount += sum_data['invoice_amount__sum']
        total_payment_receivable += receivable
        customer_data.append({'channel': data['marketplace'], 'customer_id': data['customer_id'],
                              'customer_name': data['customer_name'],
                              'payment_received': "%.2f" % sum_data['payment_received__sum'],
                              'payment_receivable': "%.2f" % receivable,
                              'invoice_amount': "%.2f" % sum_data['invoice_amount__sum']})
    response["data"] = customer_data
    response.update({'total_payment_received': "%.2f" % total_payment_received,
                     'total_invoice_amount': "%.2f" % total_invoice_amount,
                     'total_payment_receivable': "%.2f" % total_payment_receivable})
    return HttpResponse(json.dumps(response))


@login_required
@csrf_exempt
@get_admin_user
def get_customer_payment_tracker(request, user=''):
    response = {}
    customer_id = request.GET['id']
    customer_name = request.GET['name']
    channel = request.GET['channel']
    status_filter = request.GET.get('filter', '')
    all_picklists = Picklist.objects.filter(order__user=user.id)
    invoiced = all_picklists.filter(order__user=user.id, status__in=['picked', 'batch_picked', 'dispatched']). \
        values_list('order__order_id', flat=True).distinct()
    partial_invoiced = all_picklists.filter(order__user=user.id, picked_quantity__gt=0,
                                            status__icontains='open').values_list('order__order_id',
                                                                                  flat=True).distinct()
    total_data1 = OrderDetail.objects.filter(user=user.id, customer_id=customer_id, customer_name=customer_name,
                                             marketplace=channel).annotate(total_invoice=Sum('invoice_amount'),
                                                                           total_received=Sum('payment_received'))
    total_data = total_data1.filter(total_received__lt=F('total_invoice'))
    if status_filter == 'Partially Invoiced':
        total_data = total_data.filter(order_id__in=partial_invoiced)
    if status_filter == 'Invoiced':
        total_data = total_data.filter(order_id__in=invoiced)
    if status_filter == 'Order Created':
        total_data = total_data.exclude(order_id__in=list(chain(invoiced, partial_invoiced)))
    orders = total_data.values('order_id', 'order_code', 'original_order_id', 'payment_mode', 'customer_id',
                               'customer_name').distinct()
    order_data = []
    for data in orders:
        order_status = 'Order Created'
        expected_date = ''
        if data['order_id'] in invoiced:
            order_status = 'Invoiced'
        if data['order_id'] in partial_invoiced:
            order_status = 'Partially Invoiced'
        order_id = str(data['order_code']) + str(data['order_id'])
        if data['original_order_id']:
            order_id = data['original_order_id']

        if order_status == 'Invoiced':
            picklist = all_picklists.filter(order__order_id=data['order_id'], order__order_code=data['order_code']). \
                order_by('-updation_date')
            picked_date = get_local_date(user, picklist[0].updation_date, send_date=True)
            customer_master = CustomerMaster.objects.filter(customer_id=data['customer_id'], name=data['customer_name'],
                                                            user=user.id)
            if customer_master:
                if customer_master[0].credit_period:
                    expected_date = picked_date + datetime.timedelta(days=customer_master[0].credit_period)
                    expected_date = expected_date.strftime("%d %b, %Y")
            if not expected_date:
                expected_date = picked_date.strftime("%d %b, %Y")

        sum_data = total_data1.filter(order_id=data['order_id']).aggregate(Sum('invoice_amount'),
                                                                           Sum('payment_received'))
        order_data.append(
            {'order_id': str(data['order_id']), 'display_order': order_id, 'account': data['payment_mode'],
             'inv_amount': "%.2f" % sum_data['invoice_amount__sum'],
             'receivable': "%.2f" % (sum_data['invoice_amount__sum'] - sum_data['payment_received__sum']),
             'received': '%.2f' % sum_data['payment_received__sum'], 'order_status': order_status,
             'expected_date': expected_date})
    response["data"] = order_data
    return HttpResponse(json.dumps(response))


@login_required
@csrf_exempt
@get_admin_user
def get_customer_master_id(request, user=''):
    customer_id = 1
    reseller_price_type = ''
    customer_master = CustomerMaster.objects.filter(user=user.id).values_list('customer_id', flat=True).order_by(
        '-customer_id')
    if customer_master:
        customer_id = customer_master[0] + 1

    price_band_flag = get_misc_value('priceband_sync', user.id)
    level_2_price_type = ''
    if price_band_flag == 'true':
        admin_user = get_admin(user)
        level_2_price_type = 'D1-R'
    if user.userprofile.warehouse_type == 'DIST':
        reseller_price_type = 'D-R'

    price_types = list(PriceMaster.objects.exclude(price_type__in=["", 'D1-R', 'R-C']).
                       filter(sku__user=admin_user.id).values_list('price_type', flat=True).
                       distinct())

    return HttpResponse(json.dumps({'customer_id': customer_id, 'tax_data': TAX_VALUES, 'price_types': price_types,
                                    'level_2_price_type': level_2_price_type, 'price_type': reseller_price_type}))


@login_required
@csrf_exempt
@get_admin_user
def update_payment_status(request, user=''):
    data_dict = dict(request.GET.iterlists())
    for i in range(0, len(data_dict['order_id'])):
        if not data_dict['amount'][i]:
            continue
        payment = float(data_dict['amount'][i])
        order_details = OrderDetail.objects.filter(order_id=data_dict['order_id'][i], user=user.id,
                                                   payment_received__lt=F('invoice_amount'))
        for order in order_details:
            if not payment:
                break
            if float(order.invoice_amount) > float(order.payment_received):
                diff = float(order.invoice_amount) - float(order.payment_received)
                if payment > diff:
                    order.payment_received = diff
                    payment -= diff
                    PaymentSummary.objects.create(order_id=order.id, creation_date=datetime.datetime.now(),
                                                  payment_received=diff)
                else:
                    PaymentSummary.objects.create(order_id=order.id, creation_date=datetime.datetime.now(),
                                                  payment_received=payment)
                    order.payment_received = float(order.payment_received) + float(payment)
                    payment = 0
                order.save()
    return HttpResponse("Success")


@login_required
@csrf_exempt
@get_admin_user
def create_orders_data(request, user=''):
    tax_types = copy.deepcopy(TAX_VALUES)
    tax_types.append({'tax_name': 'DEFAULT', 'tax_value': ''})

    return HttpResponse(json.dumps({'payment_mode': PAYMENT_MODES, 'taxes': tax_types}))


@csrf_exempt
def get_order_category_view_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                                 filters={}, user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_dict = eval(user_dict)
    lis = ['id', 'customer_name', 'order_id', 'sku__sku_category', 'total', 'city', 'status']
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}

    if user_dict.get('market_places', ''):
        marketplace = user_dict['market_places'].split(',')
        data_dict['marketplace__in'] = marketplace
    if user_dict.get('customer_id', ''):
        data_dict['customer_id'], data_dict['customer_name'] = user_dict['customer_id'].split(':')

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_params = get_filtered_params(filters, lis[1:])

    if 'order_id__icontains' in search_params.keys():
        order_search = search_params['order_id__icontains']
        search_params['order_id__icontains'] = ''.join(re.findall('\d+', order_search))
        search_params['order_code__icontains'] = ''.join(re.findall('\D+', order_search))
    search_params['sku_id__in'] = sku_master_ids
    order_taken_val_user = CustomerOrderSummary.objects.filter(order__user=user.id)
    single_search = "no"
    if 'city__icontains' in search_params.keys():
        single_search = "yes"
        order_taken_val_user = CustomerOrderSummary.objects.filter(
            Q(order_taken_by__icontains=search_params['city__icontains']))
        del (search_params['city__icontains'])

    if search_term:
        mapping_results = OrderDetail.objects.filter(**data_dict).values('customer_name', 'order_id',
                                                                         'sku__sku_category',
                                                                         'order_code', 'original_order_id').distinct(). \
            annotate(total=Sum('quantity')).filter(Q(customer_name__icontains=search_term) |
                                                   Q(order_id__icontains=search_term) | Q(
            sku__sku_category__icontains=search_term),
                                                   **search_params).exclude(order_code="CO").order_by(order_data)
    else:
        mapping_results = OrderDetail.objects.filter(**data_dict).exclude(order_code="CO").values('customer_name',
                                                                                                  'order_id',
                                                                                                  'sku__sku_category',
                                                                                                  'order_code',
                                                                                                  'original_order_id').distinct(). \
            annotate(total=Sum('quantity')).filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    index = 0
    for dat in mapping_results[start_index:stop_index]:
        cust_status_obj = CustomerOrderSummary.objects.filter(order__order_id=dat['order_id'])
        if cust_status_obj:
            cust_status = cust_status_obj[0].status
        else:
            cust_status = ""

        order_id = dat['order_code'] + str(dat['order_id'])
        check_values = order_id + '<>' + dat['sku__sku_category']
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (check_values, dat['total'])
        order_taken_val = ''
        if order_taken_val_user:
            order_taken_val = order_taken_val_user.filter(order__order_id=dat['order_id'])
            if order_taken_val:
                order_taken_val = order_taken_val[0].order_taken_by
            else:
                order_taken_val = ''
        if single_search == "yes" and order_taken_val == '':
            continue

        temp_data['aaData'].append(OrderedDict((('data_value', check_values), ('Customer Name', dat['customer_name']),
                                                ('Order ID', order_id), ('Category', dat['sku__sku_category']),
                                                ('Total Quantity', dat['total']), ('Order Taken By', order_taken_val),
                                                ('Status', cust_status),
                                                ('id', index), ('DT_RowClass', 'results'))))
        index += 1
    col_val = ['Customer Name', 'Customer Name', 'Order ID', 'Category', 'Total Quantity', 'Order Taken By', 'Status']
    if order_term:
        order_data = col_val[col_num]
        if order_term == "asc":
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data])
        else:
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data], reverse=True)


@csrf_exempt
def get_order_view_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters,
                        user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_dict = eval(user_dict)
    lis = ['order_id', 'customer_name', 'order_id', 'marketplace', 'total', 'shipment_date', 'creation_date', 'city',
           'status']
    # unsort_lis = ['Customer Name', 'Order ID', 'Market Place ', 'Total Quantity']
    unsorted_dict = {7: 'Order Taken By', 8: 'Status'}
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    if user_dict.get('market_places', ''):
        marketplace = user_dict['market_places'].split(',')
        data_dict['marketplace__in'] = marketplace
    if user_dict.get('customer_id', ''):
        data_dict['customer_id'], data_dict['customer_name'] = user_dict['customer_id'].split(':')
    search_params = get_filtered_params(filters, lis[1:])

    if 'shipment_date__icontains' in search_params.keys():
        search_params['shipment_date__regex'] = search_params['shipment_date__icontains']
        del search_params['shipment_date__icontains']
    if 'order_id__icontains' in search_params.keys():
        order_search = search_params['order_id__icontains']
        search_params['order_id__icontains'] = ''.join(re.findall('\d+', order_search))
        search_params['order_code__icontains'] = ''.join(re.findall('\D+', order_search))
    search_params['sku_id__in'] = sku_master_ids

    if 'city__icontains' in search_params.keys():
        order_taken_val_user = CustomerOrderSummary.objects.filter(
            order_taken_by__icontains=search_params['city__icontains'],
            order__user=user.id)
        search_params['id__in'] = order_taken_val_user.values_list('order_id', flat=True)
        del (search_params['city__icontains'])
    if 'status__icontains' in search_params.keys():
        stat_search = {}
        if search_params.has_key('id__in'):
            stat_search['order_id__in'] = search_params['id__in']
        order_taken_val_user = CustomerOrderSummary.objects.filter(status__icontains=search_params['status__icontains'],
                                                                   order__user=user.id, **stat_search)
        search_params['id__in'] = order_taken_val_user.values_list('order_id', flat=True)
        del (search_params['status__icontains'])

    custom_search = False
    if col_num in unsorted_dict.keys():
        custom_search = True

    all_orders = OrderDetail.objects.filter(**data_dict).exclude(order_code="CO")
    if search_term:
        mapping_results = all_orders.values('customer_name', 'order_id', 'order_code', 'original_order_id',
                                            'marketplace'). \
            distinct().annotate(total=Sum('quantity')).filter(Q(customer_name__icontains=search_term) |
                                                              Q(order_id__icontains=search_term) | Q(
            sku__sku_category__icontains=search_term),
                                                              **search_params).order_by(order_data)
    else:
        mapping_results = all_orders.values('customer_name', 'order_id', 'order_code', 'original_order_id',
                                            'marketplace'). \
            distinct().annotate(total=Sum('quantity')).filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    index = 0
    all_seller_orders = SellerOrder.objects.filter(order__user=user.id)
    order_summary_objs = CustomerOrderSummary.objects.filter(order__user=user.id).values('order__order_id', \
                                                                                         'shipment_time_slot', 'status',
                                                                                         'order_taken_by').distinct()

    if stop_index and not custom_search:
        mapping_results = mapping_results[start_index:stop_index]
    for dat in mapping_results:
        cust_status_obj = order_summary_objs.filter(order__order_id=dat['order_id'])
        cust_status = ''
        time_slot = ''
        order_taken_val = ''
        if cust_status_obj:
            cust_status = cust_status_obj[0]['status']
            time_slot = cust_status_obj[0]['shipment_time_slot']
            order_taken_val = cust_status_obj[0]['order_taken_by']

        order_id = dat['order_code'] + str(dat['order_id'])
        if dat['original_order_id']:
            order_id = dat['original_order_id']
        check_values = order_id
        # name = all_orders.filter(order_id=dat['order_id'], order_code=dat['order_code'], user=user.id)[0].id
        name = ''
        order_dates = all_orders.filter(order_id=dat['order_id'], order_code=dat['order_code'], user=user.id).order_by(
            '-shipment_date')
        creation_date = order_dates[0].creation_date
        creation_data = get_local_date(request.user, creation_date, True).strftime("%d %b, %Y")
        shipment_date = order_dates[0].shipment_date
        shipment_data = get_local_date(request.user, shipment_date, True).strftime("%d %b, %Y")
        if time_slot:
            if "-" in time_slot:
                time_slot = time_slot.split("-")[0]

            shipment_data = shipment_data + ', ' + time_slot
        # if time_slot:
        #    shipment_data = shipment_data + ', ' + time_slot

        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (name, dat['total'])
        tot_quantity = dat['total']
        seller_order = all_seller_orders.filter(order__order_id=dat['order_id'], order__order_code=dat['order_code'],
                                                order__user=user.id, status=1).aggregate(Sum('quantity'))[
            'quantity__sum']
        if seller_order:
            tot_quantity = seller_order

        temp_data['aaData'].append(OrderedDict((('', checkbox), ('Customer Name', dat['customer_name']),
                                                ('Order ID', order_id), ('Market Place', dat['marketplace']),
                                                ('Total Quantity', tot_quantity), ('Creation Date', creation_data),
                                                ('Shipment Date', shipment_data), ('Order Taken By', order_taken_val),
                                                ('Status', cust_status), ('id', index), ('DT_RowClass', 'results'),
                                                ('data_value', check_values))))
        index += 1

    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(temp_data['aaData'][0].keys(), temp_data['aaData'], order_term, '',
                                                    col_num, exact=False)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


@csrf_exempt
def get_custom_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                          filters={}, user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    # user_dict = eval(user_dict)
    lis = ['id', 'customer_name', 'order_id', 'total', 'shipment_date', 'creation_date', 'production_unit',
           'printing_vendor', 'embroidery_unit', 'order_taken_by', 'status']
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0, 'order_code': "CO"}

    order_taken_val_user = CustomerOrderSummary.objects.filter(order__user=user.id)

    all_orders = OrderDetail.objects.filter(**data_dict)
    mapping_results = all_orders.values('customer_name', 'order_id', 'order_code', 'original_order_id',
                                        'shipment_date'). \
        distinct().annotate(total=Sum('quantity'))

    index = 0
    vendor_list = ['printing_vendor', 'embroidery_vendor', 'production_unit']
    for dat in mapping_results:
        vend_dict = {'printing_vendor': "", 'embroidery_vendor': "", 'production_unit': ""}
        cust_status, time_slot, order_taken_val = "", "", ""
        if order_taken_val_user:
            cust_status_obj = order_taken_val_user.filter(order__order_id=dat['order_id'])
            if cust_status_obj:
                cust_status = cust_status_obj[0].status
                time_slot = cust_status_obj[0].shipment_time_slot
                order_taken_val = cust_status_obj[0].order_taken_by

        for item in vendor_list:
            var = ""
            map_obj = OrderMapping.objects.filter(order__order_id=dat['order_id'], order__user=user.id,
                                                  mapping_type=item)
            if map_obj:
                var_id = map_obj[0].mapping_id
                vend_obj = VendorMaster.objects.filter(id=var_id)
                if vend_obj:
                    var = vend_obj[0].name
                    vend_dict[item] = var

        order_id = dat['order_code'] + str(dat['order_id'])
        check_values = order_id
        name = all_orders.filter(order_id=dat['order_id'], order_code=dat['order_code'], user=user.id)[0].id
        creation_date = all_orders.filter(order_id=dat['order_id'], order_code=dat['order_code'], user=user.id)[
            0].creation_date
        creation_data = get_local_date(request.user, creation_date, True).strftime("%d %b, %Y")

        shipment_data = get_local_date(request.user, dat['shipment_date'], True).strftime("%d %b, %Y")
        if time_slot:
            if "-" in time_slot:
                time_slot = time_slot.split("-")[0]

            shipment_data = shipment_data + ', ' + time_slot

        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (name, dat['total'])

        temp_data['aaData'].append(
            OrderedDict((('', checkbox), ('data_value', check_values), ('Customer Name', dat['customer_name']),
                         ('Order ID', order_id), ('Production Unit', vend_dict['production_unit']),
                         ('Printing Unit', vend_dict['printing_vendor']),
                         ('Embroidery Unit', vend_dict['embroidery_vendor']),
                         ('Total Quantity', dat['total']), ('Order Taken By', order_taken_val),
                         ('Creation Date', creation_data), ('Shipment Date', shipment_data),
                         ('id', index), ('DT_RowClass', 'results'), ('Status', cust_status))))
        index += 1

    col_val = ['id', 'Customer Name', 'Order ID', 'Total Quantity', 'Shipment Date', 'Creation Date', 'Production Unit',
               'Printing Unit', 'Embroidery Unit', 'Order Taken By', 'Status']

    temp_data['aaData'] = apply_search_sort(col_val, temp_data['aaData'], order_term, search_term, col_num)
    temp_data['recordsTotal'] = len(temp_data['aaData'])
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


@csrf_exempt
@login_required
@get_admin_user
def order_category_generate_picklist(request, user=''):
    filters = request.POST.get('filters', '')
    order_filter = {'status': 1, 'user': user.id, 'quantity__gt': 0}
    seller_order_filter = {'order__status': 1, 'order__user': user.id, 'order__quantity__gt': 0}
    if filters:
        filters = eval(filters)
        if filters['market_places']:
            order_filter['marketplace__in'] = (filters['market_places']).split(',')
            seller_order_filter['order__marketplace__in'] = order_filter['marketplace__in']
        if filters.get('customer_id', ''):
            customer_id = ''.join(re.findall('\d+', filters['customer_id']))
            order_filter['customer_id'] = customer_id
            seller_order_filter['order__customer_id'] = customer_id
    data = []
    order_data = []
    stock_status = ''
    out_of_stock = []
    picklist_number = get_picklist_number(user)

    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
        location__zone__zone='DAMAGED_ZONE').filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(**order_filter)
    all_seller_orders = SellerOrder.objects.prefetch_related('order__sku').filter(**seller_order_filter)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
            'receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
            'location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    all_sku_stocks = stock_detail1 | stock_detail2

    seller_stocks = SellerStock.objects.filter(seller__user=user.id).values('stock_id', 'seller_id')
    for key, value in request.POST.iteritems():
        if key in PICKLIST_SKIP_LIST or key in ['filters']:
            continue

        order_filter = {'quantity__gt': 0}
        if '<>' in key:
            key = key.split('<>')
            order_id, sku_category = key
            order_filter['sku__sku_category'] = sku_category
        else:
            order_id = key
        order_code = ''.join(re.findall('\D+', order_id))
        order_id = ''.join(re.findall('\d+', order_id))
        order_filter['order_id'] = order_id
        order_filter['order_code'] = order_code

        order_detail = all_orders.filter(**order_filter).order_by('shipment_date')
        seller_orders = all_seller_orders.filter(order_id__in=order_detail.values_list('id', flat=True), status=1). \
            order_by('order__shipment_date')
        try:
            if seller_orders:
                for seller_order in seller_orders:
                    sku_stocks = all_sku_stocks
                    seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(seller_order.seller_id),
                                               seller_stocks)
                    if seller_stock_dict:
                        sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
                        sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
                    else:
                        sku_stocks = sku_stocks.filter(id=0)
                    stock_status, picklist_number = picklist_generation([seller_order], request, picklist_number, user,
                                                                        sku_combos, sku_stocks, status='open',
                                                                        remarks='', is_seller_order=True)
                    if stock_status:
                        out_of_stock = out_of_stock + stock_status
            else:
                stock_status, picklist_number = picklist_generation(order_detail, request, picklist_number, user,
                                                                    sku_combos, sku_stocks, \
                                                                    status='open', remarks='')
                if stock_status:
                    out_of_stock = out_of_stock + stock_status
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Generate Picklist order view failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    order_status = ''

    data, sku_total_quantities = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']
        if order_status == 'open':
            order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
            order_count_len = len(filter(lambda x: len(str(x)) > 0, order_count))
            if order_count_len == 1:
                single_order = str(order_count[0])

    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status,
                                    'order_status': order_status, 'user': request.user.id,
                                    'sku_total_quantities': sku_total_quantities}))


@csrf_exempt
@login_required
@get_admin_user
def delete_order_data(request, user=""):
    """ This code is used to delete the orders when that coloumn in deleted from view order """
    complete_id = request.GET.get('order_id_code', '')
    sku_code = request.GET.get("item_code", "")

    if complete_id:
        order_id = ''.join(re.findall('\d+', complete_id))
        order_code = ''.join(re.findall('\D+', complete_id))
        ord_obj = OrderDetail.objects.filter(order_id=order_id, order_code=order_code, sku__sku_code=sku_code,
                                             user=user.id, status=1)
        if ord_obj:
            seller_order = SellerOrder.objects.filter(order_id=ord_obj[0].id, order_status='DELIVERY_RESCHEDULED',
                                                      status=1)
            if not seller_order:
                ord_obj.delete()
            else:
                seller_order_ids = list(ord_obj.values_list('id', flat=True))
                OrderDetail.objects.filter(id__in=seller_order_ids).update(status=5)
                SellerOrder.objects.filter(order_id__in=seller_order_ids).update(status=0, order_status='PROCESSED')

    return HttpResponse("Order Deleted")


@csrf_exempt
@login_required
@get_admin_user
def update_order_data(request, user=""):
    """ This code will update data if order is updated """
    st_time = datetime.datetime.now()
    log.info("updation of order process started")
    myDict = dict(request.POST.iterlists())
    log.info('Order update request params for ' + user.username + ' is ' + str(request.GET.dict()))
    try:
        complete_id = myDict['order_id'][0]
        order_id = ''.join(re.findall('\d+', complete_id))
        order_code = ''.join(re.findall('\D+', complete_id))
        older_objs = OrderDetail.objects.filter(
            Q(order_id=order_id, order_code=order_code) | Q(original_order_id=complete_id),
            user=user.id)
        old_cust_obj = ""
        order_creation_date = datetime.datetime.now()
        tax_type = 2
        tax_name = request.POST.get('tax_type', '')
        if tax_name == 'intra_state':
            tax_type = 0
        elif tax_name == 'inter_state':
            tax_type = 1

        if older_objs:
            older_order = older_objs[0]
            order_creation_date = older_order.creation_date
        else:
            return HttpResponse("Order Creation Failed")
        for i in range(0, len(myDict['item_code'])):
            s_date = datetime.datetime.strptime(myDict['shipment_date'][0], '%d %b, %Y %H:%M %p')
            if not myDict['item_code'][i] or not myDict['quantity'][i]:
                continue
            sku_id = SKUMaster.objects.get(sku_code=myDict['item_code'][i], user=user.id)

            if not myDict['invoice_amount'][i]:
                myDict['invoice_amount'][i] = 0
            default_dict = {'title': myDict['product_title'][i], 'quantity': myDict['quantity'][i],
                            'invoice_amount': myDict['invoice_amount'][i],
                            'user': user.id, 'customer_id': older_order.customer_id,
                            'customer_name': older_order.customer_name,
                            'telephone': older_order.telephone, 'email_id': older_order.email_id,
                            'address': older_order.address,
                            'shipment_date': older_order.shipment_date, "marketplace": older_order.marketplace,
                            'remarks': myDict['remarks'][i], 'original_order_id': older_order.original_order_id,
                            'unit_price': myDict['unit_price'][i]}
            sku_order = older_objs.filter(order_id=order_id, order_code=order_code, sku=sku_id)
            if not sku_order:
                default_dict['status'] = 1
            elif int(sku_order[0].status) == 0:
                continue
            order_obj, created = OrderDetail.objects.update_or_create(
                order_id=order_id, order_code=order_code, sku=sku_id, defaults=default_dict
            )
            sgst_tax = myDict['sgst'][i]
            cgst_tax = myDict['cgst'][i]
            igst_tax = myDict['igst'][i]
            discount = myDict['discount'][i]
            if not sgst_tax:
                sgst_tax = 0
            if not cgst_tax:
                cgst_tax = 0
            if not igst_tax:
                igst_tax = 0
            if not discount:
                discount = 0

            old_cust_obj = CustomerOrderSummary.objects.filter(order=order_obj.id)
            if created:
                order_obj.creation_date = order_creation_date
                order_obj.save()
                if old_cust_obj:
                    CustomerOrderSummary.objects.create(order=order_obj, discount=discount, vat=old_cust_obj[0].vat,
                                                        tax_value=old_cust_obj[0].tax_value,
                                                        order_taken_by=old_cust_obj[0].order_taken_by,
                                                        mrp=old_cust_obj[0].mrp, tax_type=old_cust_obj[0].tax_type,
                                                        status=old_cust_obj[0].status,
                                                        central_remarks=old_cust_obj[0].central_remarks,
                                                        sgst_tax=sgst_tax, cgst_tax=cgst_tax, igst_tax=igst_tax)
                else:
                    CustomerOrderSummary.objects.create(order=order_obj, status=myDict['status_type'][0],
                                                        central_remarks=myDict['central_remarks'][0], sgst_tax=sgst_tax,
                                                        cgst_tax=cgst_tax, igst_tax=igst_tax, discount=discount,
                                                        tax_type=tax_type)
            else:
                status_obj = old_cust_obj
                if not status_obj:
                    status_obj = CustomerOrderSummary.objects.create(order=order_obj, status=myDict['status_type'][0])
                else:
                    status_obj = status_obj[0]
                status_obj.status = myDict['status_type'][0]
                status_obj.central_remarks = myDict['central_remarks'][0]
                status_obj.sgst_tax = sgst_tax
                status_obj.cgst_tax = cgst_tax
                status_obj.igst_tax = igst_tax
                status_obj.discount = discount
                status_obj.tax_type = tax_type
                status_obj.save()

                vendor_list = ['printing_vendor', 'embroidery_vendor', 'production_unit']
                for item in vendor_list:
                    if myDict.has_key(item):
                        if not myDict[item][0]:
                            OrderMapping.objects.filter(order__id=order_obj.id, order__user=user.id,
                                                        mapping_type=item).delete()
                        else:
                            ord_map_obj = OrderMapping.objects.filter(order__id=order_obj.id, order__user=user.id,
                                                                      mapping_type=item)
                            vend_obj = VendorMaster.objects.filter(vendor_id=myDict[item][0], user=user.id)
                            if vend_obj:
                                vendor_id = vend_obj[0].id
                                if ord_map_obj:
                                    ord_map_obj = ord_map_obj[0]
                                    ord_map_obj.mapping_id = vendor_id
                                    ord_map_obj.save()
                                else:
                                    OrderMapping.objects.create(mapping_id=vendor_id, mapping_type=item,
                                                                order_id=order_obj.id)

        end_time = datetime.datetime.now()
        duration = end_time - st_time
        log.info("process completed")
        log.info("total time -- %s" % (duration))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Order failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
        return HttpResponse("Update Order Failed")
    return HttpResponse("Success")


@csrf_exempt
@login_required
@get_admin_user
def picklist_delete(request, user=""):
    """ This code will delete the picklist selected"""

    st_time = datetime.datetime.now()
    log.info("deletion of picklist process started")
    picklist_id = request.GET.get("picklist_id", "")
    key = request.GET.get("key", "")
    picklist_objs = Picklist.objects.filter(picklist_number=picklist_id, status__in=["open", "batch_open"],
                                            order_id__user=user.id)
    order_ids = picklist_objs.values_list('order_id', flat=True)
    order_objs = OrderDetail.objects.filter(id__in=order_ids, user=user.id)
    log.info('Cancel Picklist request params for ' + user.username + ' is ' + str(request.POST.dict()))
    cancelled_orders_dict = {}
    try:
        if key == "process":
            for order in order_objs:
                if picklist_objs.filter(order_type='combo', order_id=order.id):
                    is_picked = picklist_objs.filter(picked_quantity__gt=0, order_id=order.id)
                    remaining_qty = order.quantity
                    if is_picked:
                        return HttpResponse("Partial Picked Picklist not allowed to cancel")
                else:
                    remaining_qty = picklist_objs.filter(order_id=order).aggregate(Sum('reserved_quantity'))

                order.status, order.quantity = 1, remaining_qty['reserved_quantity__sum']
                order.save()
                seller_orders = SellerOrder.objects.filter(order__user=user.id, order_id=order.id)
                if seller_orders:
                    seller_orders.update(status=1)
            OrderLabels.objects.filter(order_id__in=order_ids, picklist__picklist_number=picklist_id).update(
                picklist=None)
            picklist_objs.delete()
            end_time = datetime.datetime.now()
            duration = end_time - st_time
            log.info("process completed")
            log.info("total time -- %s" % (duration))
            return HttpResponse("Picklist is saved for later use")

        elif key == "delete":
            for order in order_objs:
                if picklist_objs.filter(order_type='combo', order_id=order.id):
                    is_picked = picklist_objs.filter(picked_quantity__gt=0, order_id=order.id)
                    remaining_qty = order.quantity
                    if is_picked:
                        return HttpResponse("Partial Picked Picklist not allowed to cancel")
                else:
                    all_seller_orders = SellerOrder.objects.filter(order__user=user.id,
                                                                   order_id__in=order_objs.values_list('id', flat=True))
                    picked_qty = picklist_objs.filter(order_id=order).aggregate(Sum('picked_quantity'))[
                        'picked_quantity__sum']
                    pick_order = picklist_objs.filter(order_id=order)
                    remaining_qty = pick_order.aggregate(Sum('reserved_quantity'))['reserved_quantity__sum']
                    pick_status = 'picked'
                    if pick_order.filter(status__icontains='batch'):
                        pick_status = 'batch_picked'
                    seller_order = all_seller_orders.filter(order_id=order.id, order__user=user.id)
                    if seller_order:
                        cancelled_orders_dict.setdefault(seller_order[0].id, {})
                        cancelled_orders_dict[seller_order[0].id].setdefault('quantity', 0)
                        cancelled_orders_dict[seller_order[0].id]['quantity'] = float(
                            cancelled_orders_dict[seller_order[0].id]['quantity']) + \
                                                                                float(remaining_qty)

                    if picked_qty <= 0 and not seller_order:
                        order.delete()
                        continue
                    save_order_tracking_data(order, quantity=remaining_qty, status='cancelled', imei='')
                    temp_order_quantity = float(order.quantity) - float(remaining_qty)
                    if temp_order_quantity > 0:
                        order.quantity = temp_order_quantity
                    else:
                        order.status = 3
                    shipped = ShipmentInfo.objects.filter(order_id=order.id).aggregate(Sum('shipping_quantity'))[
                        'shipping_quantity__sum']
                    proc_pick_obj = Picklist.objects.filter(order_id=order.id, status='dispatched', order__user=user.id)
                    proc_pick_qty = 0
                    if proc_pick_obj and proc_pick_obj[0].order:
                        proc_pick_qty = float(proc_pick_obj[0].order.quantity)
                    if shipped:
                        shipped = float(shipped) - float(proc_pick_qty)
                        if float(shipped) == float(order.quantity):
                            order.status = 2
                            pick_status = 'dispatched'
                    del_seller_order = all_seller_orders.filter(order_id=order.id, order_status='DELIVERY_RESCHEDULED')
                    if del_seller_order and not pick_status == 'dispatched':
                        order.status = 5
                        del_seller_order = del_seller_order[0]
                        del_seller_order.status = 0
                        del_seller_order.order_status = 'PROCESSED'
                        del_seller_order.save()
                    order.save()
                    picklist_locations = PicklistLocation.objects.filter(picklist__order_id=order.id,
                                                                         picklist__picklist_number=picklist_id,
                                                                         picklist__status__in=["open", "batch_open"],
                                                                         picklist__order__user=user.id)
                    for pick_location in picklist_locations:
                        pick_location.quantity = float(pick_location.quantity) - float(pick_location.reserved)
                        pick_location.reserved = 0
                        pick_location.status = 0
                        pick_location.save()
                    pick_order.update(reserved_quantity=0, status=pick_status)

            end_time = datetime.datetime.now()
            duration = end_time - st_time
            log.info("process completed")
            log.info("total time -- %s" % (duration))
            if cancelled_orders_dict:
                check_and_update_order_status_data(cancelled_orders_dict, user, status='CANCELLED')
            return HttpResponse("Picklist is deleted")

        else:
            log.info("Invalid key")
            return HttpResponse("Something is wrong there, please check")
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Cancel Picklist failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
        return HttpResponse("Something is wrong there, please check")


@csrf_exempt
@login_required
@get_admin_user
def order_delete(request, user=""):
    """ This code will delete the order selected"""

    st_time = datetime.datetime.now()
    log.info('Request params for ' + user.username + ' is ' + str(request.POST.dict()))
    log.info("deletion of order process started")
    complete_id = request.GET.get("order_id", "")

    order_id = ''.join(re.findall('\d+', complete_id))
    order_code = ''.join(re.findall('\D+', complete_id))
    try:
        order_detail = OrderDetail.objects.filter(order_id=order_id, order_code=order_code, user=user.id, status=1)
        if not order_detail:
            complete_id = request.GET.get("order_id_code", "")
            order_id = ''.join(re.findall('\d+', complete_id))
            order_code = ''.join(re.findall('\D+', complete_id))
            order_detail = OrderDetail.objects.filter(order_id=order_id, order_code=order_code, user=user.id, status=1)
        if order_detail:
            order_detail_ids = order_detail.values_list('id', flat=True)
            seller_orders = list(
                SellerOrder.objects.filter(order_id__in=order_detail_ids, order_status='DELIVERY_RESCHEDULED',
                                           status=1). \
                values_list('order_id', flat=True))
            order_detail_ids = list(order_detail_ids)
            if seller_orders:
                OrderDetail.objects.filter(id__in=seller_orders).update(status=5)
                SellerOrder.objects.filter(order_id__in=seller_orders).update(status=0, order_status='PROCESSED')
                order_detail_ids = list(set(order_detail_ids) - set(seller_orders))
            if order_detail_ids:
                OrderDetail.objects.filter(id__in=order_detail_ids).delete()
                # else:
                #    order_detail.delete()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(e)

    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("process completed")
    log.info("total time -- %s" % (duration))
    return HttpResponse("Order is deleted")


def get_only_date(request, date):
    """" return only data like 01/01/17 """
    date = get_local_date(request.user, date, True)
    date = date.strftime("%m/%d/%Y")
    return date


@get_admin_user
def get_level_based_customer_orders(request, response_data, user=''):
    index = request.GET.get('index', '')
    start_index, stop_index = 0, 20
    if index:
        start_index = int(index.split(':')[0])
        stop_index = int(index.split(':')[1])
    user_profile = UserProfile.objects.get(user=request.user.id)
    if user_profile.warehouse_type == 'DIST':
        customer = WarehouseCustomerMapping.objects.filter(warehouse=request.user.id, status=1)
        if customer:
            cum_obj = CustomerUserMapping.objects.filter(customer=customer[0].customer.id)
        else:
            return response_data
    else:
        cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    if cum_obj:
        customer_id = cum_obj[0].customer.customer_id
        cm_id = cum_obj[0].customer_id
        picklist = Picklist.objects.filter(order__customer_id=customer_id, order__user=user.id)
        generic_orders = GenericOrderDetailMapping.objects.filter(customer_id=cm_id)
        response_data['data'] = list(generic_orders.values('generic_order_id', 'customer_id'). \
                                     annotate(total_quantity=Sum('quantity'),
                                              total_inv_amt=Sum('orderdetail__invoice_amount')). \
                                     order_by('-generic_order_id'))
        response_data['data'] = response_data['data'][start_index:stop_index]
        for record in response_data['data']:
            order_detail_ids = generic_orders.filter(generic_order_id=record['generic_order_id']).values_list(
                'orderdetail_id', flat=True)
            data = OrderDetail.objects.filter(id__in=order_detail_ids)
            data_status = data.filter(status=1)
            if data_status:
                status = 'open'
            else:
                status = 'closed'
                pick_status = picklist.filter(order_id__in=order_detail_ids,
                                              status__icontains='open')
                if pick_status:
                    status = 'open'
            picked_quantity = picklist.filter(order_id__in=order_detail_ids).aggregate(
                Sum('picked_quantity'))['picked_quantity__sum']
            if not picked_quantity:
                picked_quantity = 0
            record['status'] = status
            if data:
                record['date'] = get_only_date(request, data[0].creation_date)
            else:
                record['date'] = ''
            if record['generic_order_id']:
                record['order_id'] = record['generic_order_id']
            record['total_inv_amt'] = round(record['total_inv_amt'], 2)
            record['picked_quantity'] = picked_quantity
    return response_data


@login_required
@get_admin_user
def get_customer_orders(request, user=""):
    """ Return customer orders  """
    index = request.GET.get('index', '')
    start_index, stop_index = 0, 20
    if index:
        start_index = int(index.split(':')[0])
        stop_index = int(index.split(':')[1])
    response_data = {'data': []}
    admin_user = get_priceband_admin_user(user)
    if admin_user:
        get_level_based_customer_orders(request, response_data)

    else:
        customer = CustomerUserMapping.objects.filter(user=request.user.id)

        if customer:
            customer_id = customer[0].customer.customer_id
            orders = OrderDetail.objects.filter(customer_id=customer_id, user=user.id).order_by('-creation_date')
            picklist = Picklist.objects.filter(order__customer_id=customer_id, order__user=user.id)
            response_data['data'] = list(orders.values('order_id', 'order_code', 'original_order_id').distinct().
                                         annotate(total_quantity=Sum('quantity'), total_inv_amt=Sum('invoice_amount'),
                                                  date_only=Cast('creation_date', DateField())).order_by('-date_only'))

        response_data['data'] = response_data['data'][start_index:stop_index]
        for record in response_data['data']:
            data = orders.filter(order_id=int(record['order_id']), order_code=record['order_code'])
            data_status = data.filter(status=1)
            if data_status:
                status = 'open'
            else:
                status = 'closed'
                pick_status = picklist.filter(order__order_id=int(record['order_id']),
                                              order__order_code=record['order_code'], status__icontains='open')
                if pick_status:
                    status = 'open'
            picked_quantity = picklist.filter(order__order_id=int(record['order_id'])).aggregate(
                Sum('picked_quantity'))['picked_quantity__sum']
            if not picked_quantity:
                picked_quantity = 0
            record['status'] = status
            record['date'] = get_only_date(request, data[0].creation_date)
            record['total_inv_amt'] = round(record['total_inv_amt'], 2)
            record['picked_quantity'] = picked_quantity
            if record['original_order_id']:
                record['order_id'] = record['original_order_id']
            else:
                record['order_id'] = str(record['order_code']) + str(record['order_id'])
    return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder))


def construct_order_customer_order_detail(request, order, user):
    data_list = list(order.values('id', 'order_id', 'creation_date', 'status', 'quantity', 'invoice_amount',
                                  'sku__sku_code', 'sku__image_url', 'sku__sku_desc', 'sku__sku_brand',
                                  'sku__sku_category', 'sku__sku_class'))
    total_picked_quantity = 0
    for record in data_list:
        tax_data = CustomerOrderSummary.objects.filter(order__id=record['id'], order__user=user)
        picked_quantity = Picklist.objects.filter(order_id=record['id']).values(
            'picked_quantity').aggregate(Sum('picked_quantity'))['picked_quantity__sum']
        if not picked_quantity:
            picked_quantity = 0
        record['picked_quantity'] = picked_quantity
        total_picked_quantity += picked_quantity
        if tax_data:
            tax_data = tax_data[0]
            record['invoice_amount'] = record['invoice_amount'] - tax_data.tax_value
        gen_ord_obj = GenericOrderDetailMapping.objects.filter(orderdetail_id=record['id'])
        if gen_ord_obj:
            el_price = gen_ord_obj[0].el_price
            res_unit_price = gen_ord_obj[0].unit_price
            if el_price:
                record['el_price'] = el_price
            if res_unit_price:
                tax_inclusive_inv_amt = record['invoice_amount']
                tax_exclusive_inv_amt = float(res_unit_price) * int(record['quantity'])
                record['invoice_amount'] = tax_inclusive_inv_amt
                record['sku_tax_amt'] = round(tax_inclusive_inv_amt - tax_exclusive_inv_amt, 2)
            schedule_date = gen_ord_obj[0].schedule_date
            if schedule_date:
                record['schedule_date'] = schedule_date
    return data_list, total_picked_quantity


def prepare_your_orders_data(request, ord_id, usr_id, det_ids, order):
    response_data = {}
    tax = CustomerOrderSummary.objects.filter(order_id__in=det_ids,
                                              order__user=usr_id).aggregate(Sum('tax_value'))[
        'tax_value__sum']
    if not tax:
        tax = 0
    order_ids = det_ids
    data_status = order.filter(status=1)
    if data_status:
        status = 'open'
    else:
        status = 'closed'
        pick_status = Picklist.objects.filter(order_id__in=order_ids, status__icontains='open')
        if pick_status:
            status = 'open'
    response_data['status'] = status
    response_data['date'] = get_only_date(request, order[0].creation_date)
    response_data['order_id'] = order[0].order_id
    response_data['data'] = []
    res, total_picked_quantity = construct_order_customer_order_detail(request, order, usr_id)
    total_inv_amt = map(sum, [[x['invoice_amount'] for x in res]])
    total_qty = map(sum, [[x['quantity'] for x in res]])
    total_tax = map(sum, [[x['sku_tax_amt'] for x in res]])
    response_data['tax'] = round(total_tax[0], 2)
    sum_data = {'picked_quantity': total_picked_quantity, 'amount': total_inv_amt[0],
                'quantity': total_qty[0]}
    response_data['sum_data'] = sum_data
    response_data['data'].extend(res)

    return response_data, res


def get_level_based_customer_order_detail(request, user):
    whole_res_map = {}
    response_data_list = []
    sku_wise_details = {}
    generic_order_id = request.GET['order_id']
    user_profile = UserProfile.objects.get(user=request.user.id)
    cum_obj = ''
    if user_profile.warehouse_type == 'DIST':
        customer = WarehouseCustomerMapping.objects.filter(warehouse=request.user.id, status=1)
        if customer:
            cum_obj = CustomerUserMapping.objects.filter(customer=customer[0].customer.id)
    else:
        cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    if cum_obj:
        cm_id = cum_obj[0].customer_id
        generic_orders = GenericOrderDetailMapping.objects.filter(customer_id=cm_id)
        order_detail_ids = generic_orders.filter(generic_order_id=generic_order_id).values_list(
            'orderdetail_id', flat=True)
        ord_det_qs = OrderDetail.objects.filter(id__in=order_detail_ids).values_list('order_id', 'id', 'user')
        ord_det_map = {}
        for ord_id, det_id, usr_id in ord_det_qs:
            ord_det_map.setdefault(int(ord_id), {}).setdefault(usr_id, []).append(det_id)
        for ord_id, usr_det_ids in ord_det_map.items():
            for usr_id, det_ids in usr_det_ids.items():
                response_data, res = prepare_your_orders_data(request, ord_id, usr_id, det_ids,
                                                         OrderDetail.objects.filter(id__in=det_ids))
                response_data_list.append(response_data)
                for sku_rec in res:
                    sku_code = sku_rec['sku__sku_code']
                    if sku_code not in sku_wise_details:
                        sku_qty = sku_rec['quantity']
                        sku_el_price = sku_rec.get('el_price', 0)
                        sku_tax_amt = sku_rec.get('sku_tax_amt', 0)
                        sku_wise_details[sku_code] = {'quantity': sku_qty, 'el_price': sku_el_price,
                                                      'sku_tax_amt': sku_tax_amt}
                    else:
                        existing_map = sku_wise_details[sku_code]
                        existing_map['quantity'] = existing_map['quantity'] + sku_rec['quantity']
                        existing_map['sku_tax_amt'] = existing_map['sku_tax_amt'] + sku_rec['sku_tax_amt']
    sku_whole_map = {'data': [], 'totals': {}}
    sku_totals = {'sub_total': 0, 'total_amount': 0, 'tax': 0}
    for sku_code, sku_det in sku_wise_details.items():
        el_price = sku_det['el_price']
        qty = sku_det['quantity']
        tax_amt = sku_det['sku_tax_amt']
        total_amt = float(qty) * float(el_price)
        sku_map = {'sku_code': sku_code, 'quantity': qty, 'landing_price': el_price, 'total_amount': total_amt}
        sku_totals['sub_total'] = sku_totals['sub_total'] + total_amt
        sku_totals['tax'] = sku_totals['tax'] + tax_amt
        sku_totals['total_amount'] =  sku_totals['sub_total'] + sku_totals['tax']
        sku_whole_map['data'].append(sku_map)
        sku_whole_map['totals'] = sku_totals
    whole_res_map['data'] = response_data_list
    whole_res_map['sku_wise_details'] = sku_whole_map
    return whole_res_map


@login_required
@get_admin_user
def get_customer_order_detail(request, user=""):
    """ Return customer order detail """

    response_data = {'data': []}
    order_id = request.GET['order_id']
    if not order_id:
        return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder))

    admin_user = get_priceband_admin_user(user)
    if admin_user:
        response_data_list = get_level_based_customer_order_detail(request, user)
        final_data = response_data_list
    else:
        order = get_order_detail_objs(order_id, user)
        det_ids = order.values_list('id', flat=True)
        if not order:
            return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder))
        ord_id = order[0].original_order_id
        if not ord_id:
            ord_id = order[0].order_code + str(order[0].order_id)
        response_data, res = prepare_your_orders_data(request, order_id, user.id, det_ids, order)
        response_data_list = [response_data]
        final_data = {'data': response_data_list}
    return HttpResponse(json.dumps(final_data, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def generate_pdf_file(request, user=""):
    nv_data = request.POST['data']
    c = {'name': 'kanna'}
    if request.POST.get('css', '') == 'page':
        top = loader.get_template('../miebach_admin/templates/toggle/invoice/top.html')
    else:
        top = loader.get_template('../miebach_admin/templates/toggle/invoice/top1.html')
    top = top.render(c)
    nv_data = nv_data.encode('utf-8')
    html_content = str(top) + nv_data  # +"</div>"
    if not os.path.exists('static/pdf_files/'):
        os.makedirs('static/pdf_files/')
    file_name = 'static/pdf_files/%s_dispatch_invoice.html' % str(request.user.id)
    name = str(request.user.id) + "_dispatch_invoice"
    pdf_file = 'static/pdf_files/%s.pdf' % name
    file_ = open(file_name, "w+b")
    file_.write(html_content)
    file_.close()
    os.system("./phantom/bin/phantomjs ./phantom/examples/rasterize.js ./%s ./%s A4" % (file_name, pdf_file))
    return HttpResponse("../static/pdf_files/" + str(request.user.id) + "_dispatch_invoice.pdf")


def get_tax_value(user, record, product_type, tax_type):
    inter_state = False
    if tax_type == 'inter_state' or tax_type == 'Inter State':
        inter_state = True
    amt = record['price']
    tax_data = TaxMaster.objects.filter(user_id=user.id, product_type=product_type, inter_state=inter_state,
                                        min_amt__lte=amt, max_amt__gte=amt)
    if tax_data:
        tax_data = tax_data[0]
        if inter_state:
            record['igst_tax'] = tax_data.igst_tax
            record['cgst_tax'] = 0
            record['sgst_tax'] = 0
            return tax_data.igst_tax
        else:
            record['igst_tax'] = 0
            record['cgst_tax'] = tax_data.cgst_tax
            record['sgst_tax'] = tax_data.sgst_tax
            return tax_data.sgst_tax + tax_data.cgst_tax
    else:
        return 0


@login_required
@get_admin_user
def get_customer_cart_data(request, user=""):
    """  return customer cart data """

    response = {'data': [], 'msg': 0}
    cart_data = CustomerCartData.objects.filter(user_id=user.id, customer_user_id=request.user.id)

    if cart_data:
        cust_user_obj = CustomerUserMapping.objects.filter(user=request.user.id)
        tax_type = CustomerUserMapping.objects.filter(user_id=request.user.id).values_list('customer__tax_type',
                                                                                           flat=True)
        tax = 0
        if tax_type:
            tax_type = tax_type[0]
        price_band_flag = get_misc_value('priceband_sync', user.id)

        cm_obj = CustomerMaster.objects.get(id=cust_user_obj[0].customer_id)
        is_distributor = cm_obj.is_distributor
        for record in cart_data:
            del_date = ''
            if is_distributor:
                dist_mapping = WarehouseCustomerMapping.objects.get(customer_id=cm_obj.id, status=1)
                dist_wh_id = dist_mapping.warehouse.id
                price_type = NetworkMaster.objects.filter(dest_location_code_id=dist_wh_id,
                                                          source_location_code_id=user.id). \
                    values_list('price_type')
                dist_reseller_leadtime = 0
            else:
                price_type = cm_obj.price_type
                dist_reseller_leadtime = cm_obj.lead_time
            json_record = record.json()
            sku_obj = SKUMaster.objects.filter(user=user.id, sku_code=json_record['sku_id'])
            product_type = sku_obj[0].product_type
            if not tax_type and product_type:
                json_record['tax'] = 0
            else:
                json_record['tax'] = get_tax_value(user, json_record, product_type, tax_type)
            if price_band_flag == 'true':
                central_admin = get_admin(user)
                # level = json_record['warehouse_level']
                if is_distributor:
                    if price_type:
                        price_type = price_type[0]
                    if cm_obj:
                        dist_mapping = WarehouseCustomerMapping.objects.filter(customer_id=cm_obj, status=1)
                        dist_userid = dist_mapping[0].warehouse_id
                        lead_times = get_leadtimes(dist_userid, record.warehouse_level)
                        del_date = min(lead_times.keys())
                else:
                    price_type = update_level_price_type(cm_obj, record.warehouse_level, price_type)
                    if record.warehouse_level:
                        lead_times = get_leadtimes(user.id, record.warehouse_level)
                        reseller_leadtimes = map(lambda x: x + dist_reseller_leadtime, lead_times)
                        del_date = reseller_leadtimes[0]
                    else:
                        del_date = dist_reseller_leadtime
                price_master_objs = PriceMaster.objects.filter(price_type=price_type,
                                                               sku__user=central_admin.id,
                                                               sku__sku_code=json_record['sku_id'])
                if price_master_objs:
                    for pm_obj in price_master_objs:
                        pm_obj_map = {'min_unit_range': pm_obj.min_unit_range,
                                      'max_unit_range': pm_obj.max_unit_range,
                                      'price': pm_obj.price}
                        json_record.setdefault('prices', []).append(pm_obj_map)
                        if pm_obj.min_unit_range == 0:
                            json_record['price'] = pm_obj.price
            else:
                price_master_obj = PriceMaster.objects.filter(price_type=price_type,
                                                              sku__id=record.sku_id)
                if price_master_obj:
                    price_master_obj = price_master_obj[0]
                    json_record['price'] = price_master_obj.price
            if cm_obj.margin:
                json_record['price'] = float(json_record['price']) * (1 + (float(cm_obj.margin) / 100))
            json_record['invoice_amount'] = json_record['quantity'] * json_record['price']
            json_record['total_amount'] = ((json_record['invoice_amount'] * json_record['tax']) / 100) + \
                                          json_record['invoice_amount']
            if del_date:
                date = datetime.datetime.now()
                date += datetime.timedelta(days=del_date)
                del_date = date.strftime("%m/%d/%Y")
            json_record['del_date'] = del_date

            response['data'].append(json_record)
    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


@login_required
@get_admin_user
def insert_customer_cart_data(request, user=""):
    """ insert customer cart data """

    response = {'data': [], 'msg': 0}
    cart_data = request.GET.get('data', '')

    if cart_data:
        cart_data = eval(cart_data)
        for record in cart_data:
            sku = SKUMaster.objects.get(sku_code=record['sku_id'], user=user.id)
            cart = CustomerCartData.objects.filter(user_id=user.id, customer_user_id=request.user.id,
                                                   sku__sku_code=record['sku_id'], warehouse_level=record['level'])
            if not cart:
                data = {'user_id': user.id, 'customer_user_id': request.user.id, 'sku_id': sku.id,
                        'quantity': record['quantity'], 'tax': record['tax'], 'warehouse_level': record['level'],
                        'levelbase_price': record['price']}
                customer_cart_data = CustomerCartData(**data)
                customer_cart_data.save()
            else:
                cart = cart[0]
                cart.quantity = cart.quantity + record['quantity']
                cart.save()
        response['data'] = "Inserted Successfully"

    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


@login_required
@get_admin_user
def update_customer_cart_data(request, user=""):
    """ update customer cart data """

    response = {'data': [], 'msg': 0}
    sku_code = request.GET.get('sku_code', '')
    quantity = request.GET.get('quantity', '')
    price = request.GET.get('price', '')
    level = request.GET.get('level', '')

    if sku_code:
        cart = CustomerCartData.objects.filter(user_id=user.id, customer_user_id=request.user.id,
                                               sku__sku_code=sku_code, warehouse_level=level)
        if cart:
            cart = cart[0]
            cart.quantity = quantity
            cart.levelbase_price = price
            if float(quantity) == 0.0:
                cart.delete()
                response['data'] = "Deleted Successfully"
            else:
                cart.save()
                response['data'] = "Updated Successfully"
    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


@login_required
@get_admin_user
def delete_customer_cart_data(request, user=""):
    """ delete customer cart data """

    log.info('Request params for ' + user.username + ' is ' + str(request.GET.dict()))
    try:
        response = {'msg': 0}
        sku_level_map = request.GET.dict()

        if sku_level_map:
            sku_code, level = sku_level_map.items()[0]
            if level == '':
                level = 0
            CustomerCartData.objects.filter(user_id=user.id, customer_user_id=request.user.id,
                                            sku__sku_code=sku_code, warehouse_level=level).delete()
            response["msg"] = "Deleted Successfully"
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Deleting customer cart data failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


@csrf_exempt
def get_order_shipment_picked(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              user_dict={}, filters={}):
    '''Shipment Info Alternative datatable code '''

    log.info("Shipment Alternative view started")
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    if user_dict:
        user_dict = eval(user_dict)
    lis = ['order__order_id', 'order__order_id', 'order__customer_id', 'order__customer_name', 'order__marketplace',
           'total_picked',
           'total_ordered', 'order__creation_date']
    data_dict = {'status__in': ['picked', 'batch_picked', 'open', 'batch_open'], 'order__user': user.id,
                 'picked_quantity__gt': 0}

    if user_dict.get('market_place', ''):
        marketplace = user_dict['market_place'].split(',')
        data_dict['order__marketplace__in'] = marketplace
    if user_dict.get('customer', ''):
        # data_dict['order__customer_id'], data_dict['order__customer_name'] = user_dict['customer'].split(':')
        data_dict['order__customer_id'] = user_dict['customer']
    if user_dict.get('order_id', ''):
        order_id_filter = ''.join(re.findall('\d+', user_dict['order_id']))
        order_code_filter = ''.join(re.findall('\D+', user_dict['order_id']))
        data_dict['order_id__in'] = OrderDetail.objects.filter(Q(original_order_id__icontains=user_dict['order_id']) |
                                                               Q(order_id__icontains=order_id_filter,
                                                                 order_code__icontains=order_code_filter),
                                                               user=user.id)
    if user_dict.get('from_date', ''):
        from_date = user_dict['from_date'].split('/')
        user_dict['from_date'] = datetime.date(int(from_date[2]), int(from_date[0]), int(from_date[1]))
        user_dict['from_date'] = datetime.datetime.combine(user_dict['from_date'], datetime.time())
        data_dict['order__creation_date__gt'] = user_dict['from_date']
    if user_dict.get('to_date', ''):
        to_date = user_dict['to_date'].split('/')
        user_dict['to_date'] = datetime.date(int(to_date[2]), int(to_date[0]), int(to_date[1]))
        user_dict['to_date'] = datetime.datetime.combine(user_dict['to_date'] + datetime.timedelta(1), datetime.time())
        data_dict['order__creation_date__lt'] = user_dict['to_date']

    search_params = get_filtered_params(filters, lis[1:])

    ship = dict(ShipmentInfo.objects.filter(order__user=user.id).annotate(full_order=Concat('order__order_code',
                                                                                            'order__order_id',
                                                                                            output_field=CharField())).values_list(
        'full_order'). \
                annotate(tshipped=Sum('shipping_quantity')))
    pick = dict(
        Picklist.objects.filter(order__user=user.id, status__in=['open', 'batch_open', 'picked', 'batch_picked']). \
        annotate(full_order=Concat('order__order_code', 'order__order_id', output_field=CharField())). \
        values_list('full_order').distinct().annotate(tpicked=Sum('picked_quantity')))

    pick_diff = ({key: pick[key] - ship.get(key, 0) for key in pick.keys()})
    excl_order_ids = ({k: v for k, v in pick_diff.items() if v <= 0}).keys()

    if search_term:
        order_id_search = ''.join(re.findall('\d+', search_term))
        order_code_search = ''.join(re.findall('\D+', search_term))
        master_data = Picklist.objects.exclude(order__original_order_id__in=excl_order_ids).filter(
            Q(order__sku_id__in=sku_master_ids) |
            Q(stock__sku_id__in=sku_master_ids), **data_dict). \
            values('order__order_id', 'order__order_code', 'order__original_order_id', 'order__customer_id',
                   'order__customer_name', 'order__marketplace').distinct(). \
            annotate(total_picked=Sum('picked_quantity'), total_ordered=Sum('order__quantity')). \
            filter(Q(order__order_id__icontains=order_id_search) |
                   Q(order__sku__sku_code__icontains=search_term) |
                   Q(order__title__icontains=search_term) | Q(order__customer_id__icontains=search_term) |
                   Q(order__customer_name__icontains=search_term) | Q(picked_quantity__icontains=search_term) |
                   Q(order__marketplace__icontains=search_term) |
                   Q(order__original_order_id__icontains=search_term))

    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = Picklist.objects.exclude(order__original_order_id__in=excl_order_ids).filter(
            Q(order__sku_id__in=sku_master_ids) | \
            Q(stock__sku_id__in=sku_master_ids), **data_dict). \
            values('order__order_id', 'order__order_code', 'order__original_order_id', 'order__customer_id',
                   'order__customer_name', 'order__marketplace').distinct(). \
            annotate(total_picked=Sum('picked_quantity'), total_ordered=Sum('order__quantity')). \
            filter(**search_params).order_by(order_data)
    else:
        master_data = Picklist.objects.exclude(order__original_order_id__in=excl_order_ids).filter(
            Q(order__sku_id__in=sku_master_ids) | \
            Q(stock__sku_id__in=sku_master_ids), **data_dict). \
            values('order__order_id', 'order__order_code', 'order__original_order_id', 'order__customer_id',
                   'order__customer_name', 'order__marketplace').distinct(). \
            annotate(total_picked=Sum('picked_quantity'), total_ordered=Sum('order__quantity')). \
            filter(**search_params).order_by('updation_date')

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    count = 0
    picklist = Picklist.objects.filter(**data_dict).exclude(order__status__in=[1, 3, 5])
    # tot_order_qtys = OrderDetail.objects.filter(user=user.id, quantity__gt=0).values_list('order_id', 'quantity')
    tot_order_qtys = dict(
        OrderDetail.objects.filter(user=user.id, quantity__gt=0).values_list('order_id').distinct().annotate(
            ordered=Sum('quantity')))
    all_seller_orders = SellerOrder.objects.filter(seller__user=user.id, order_status='DELIVERY_RESCHEDULED')
    # all_shipment_orders = ShipmentInfo.objects.filter(order__user=user.id)

    order_dates = dict(OrderDetail.objects.filter(id__in=master_data.values_list('order_id').distinct(), user=user.id). \
                       annotate(full_order=Concat('order_code', 'order_id', output_field=CharField())). \
                       values_list('full_order').distinct().annotate(date=Min('creation_date')))
    for data in master_data[start_index:stop_index]:
        data1 = copy.deepcopy(data)
        del data1['total_ordered']
        del data1['total_picked']
        # order_pick = picklist.filter(**data1).prefetch_related('order')
        creation_date = datetime.datetime.now()
        if order_dates.get(data['order__order_code'] + str(data['order__order_id']), ''):
            creation_date = order_dates[data['order__order_code'] + str(data['order__order_id'])]
        # if order_pick:
        #    creation_date = order_pick[0].creation_date
        #    data['total_picked'] = order_pick.aggregate(Sum('picked_quantity'))['picked_quantity__sum']
        creation_date = get_local_date(user, creation_date)
        order_id = data['order__original_order_id']
        if not order_id:
            order_id = data['order__order_code'] + str(data['order__order_id'])
            data['order__original_order_id'] = order_id

        # shipped = all_shipment_orders.filter(order_id__in=order_pick.values_list('order_id', flat=True)).\
        #                               aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
        # shipped = all_shipment_orders.filter(Q(order__order_id=data['order__order_id'], order__order_code=data['order__order_code']) |
        #                                     Q(order__original_order_id=data['order__original_order_id']),
        #                                     order__customer_id=data['order__customer_id'], order__customer_name=data['order__customer_name'],
        #                                     order__marketplace=data['order__marketplace']).aggregate(Sum('shipping_quantity'))\
        #                                     ['shipping_quantity__sum']

        seller_order = all_seller_orders.filter(order__order_id=data['order__order_id'])
        dis_quantity = 0
        if seller_order:
            dis_pick = picklist.filter(order__order_id=data['order__order_id'], status='dispatched')
            if dis_pick:
                dis_quantity = dis_pick[0].order.quantity

        if ship.get(data['order__order_code'] + str(data['order__order_id']), 0):
            shipped = ship.get(data['order__order_code'] + str(data['order__order_id']), 0) - dis_quantity
            data['total_picked'] = float(data['total_picked']) - shipped
            if data['total_picked'] <= 0:
                continue

        total_quantity = tot_order_qtys.get(data['order__order_id'], 0)
        temp_data['aaData'].append(OrderedDict((('Order ID', str(order_id)), ('id', count),
                                                ('Customer ID', data['order__customer_id']),
                                                ('Customer Name', data['order__customer_name']),
                                                ('Marketplace', data['order__marketplace']),
                                                ('Picked Quantity', data['total_picked']),
                                                ('Total Quantity', total_quantity), ('Order Date', creation_date),
                                                ('DT_RowClass', 'results'), ('order_id', order_id))))
        count = count + 1
    log.info('Shipment info alternative view filtered ' + str(temp_data['recordsTotal']))


@csrf_exempt
def get_customer_invoice_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              filters):
    ''' Customer Invoice datatable code '''

    user_profile = UserProfile.objects.get(user_id=user.id)
    if user_profile.user_type == 'marketplace_user':
        lis = ['seller_order__order__order_id', 'seller_order__order__order_id', 'seller_order__sor_id',
               'seller_order__seller__seller_id',
               'seller_order__order__customer_name', 'quantity', 'quantity', 'date_only', 'id']
        user_filter = {'seller_order__seller__user': user.id}
        result_values = ['seller_order__order__order_id', 'seller_order__seller__name', 'pick_number',
                         'seller_order__sor_id']
        field_mapping = {'order_quantity_field': 'seller_order__quantity', 'date_only': 'seller_order__creation_date'}
        is_marketplace = True
    else:
        lis = ['order__order_id', 'order__order_id', 'order__customer_name', 'quantity', 'quantity', 'date_only']
        user_filter = {'order__user': user.id}
        result_values = ['order__order_id', 'pick_number']
        field_mapping = {'order_quantity_field': 'order__quantity', 'date_only': 'order__creation_date'}
        is_marketplace = False

    if search_term:
        if 'date_only' in lis:
            lis1 = copy.deepcopy(lis)
            lis1 = map(lambda x: x if x not in ['date_only', 'seller_order__order__order_id', 'order__order_id'] else
            field_mapping['date_only'], lis1)
        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(lis1, search_term)
        order_id_search = ''.join(re.findall('\d+', search_term))
        order_code_search = ''.join(re.findall('\D+', search_term))
        if not is_marketplace:
            master_data = SellerOrderSummary.objects.filter(Q(order__order_id__icontains=order_id_search,
                                                              order__order_code__icontains=order_code_search) |
                                                            Q(
                                                                order__original_order_id__icontains=search_term) | search_query,
                                                            **user_filter). \
                values(*result_values).distinct(). \
                annotate(total_quantity=Sum('quantity'),
                         total_order=Sum(field_mapping['order_quantity_field']))
        else:
            master_data = SellerOrderSummary.objects.filter(Q(seller_order__order__order_id__icontains=order_id_search,
                                                              seller_order__order__order_code__icontains=order_code_search) |
                                                            Q(
                                                                seller_order__order__original_order_id__icontains=search_term) |
                                                            search_query, **user_filter).values(
                *result_values).distinct(). \
                annotate(total_quantity=Sum('quantity'),
                         total_order=Sum(field_mapping['order_quantity_field']))

    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']),
                         date_only=Cast(field_mapping['date_only'], DateField())).order_by(lis[col_num])
        else:
            master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']),
                         date_only=Cast(field_mapping['date_only'], DateField())).order_by('-%s' % lis[col_num])
    else:
        master_data = SellerOrderSummary.objects.filter(**user_filter).order_by('-%s' % lis[col_num]).values(
            *result_values).distinct(). \
            annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']))

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    order_summaries = SellerOrderSummary.objects.filter(seller_order__seller__user=user.id)
    seller_orders = SellerOrder.objects.filter(seller__user=user.id)
    orders = OrderDetail.objects.filter(user=user.id)

    for data in master_data[start_index:stop_index]:
        if is_marketplace:
            summary = order_summaries.filter(seller_order__order__order_id=data['seller_order__order__order_id'],
                                             seller_order__seller__name=data['seller_order__seller__name'])[0]
            order = summary.seller_order.order
            ordered_quantity = seller_orders.filter(order__order_id=data['seller_order__order__order_id'],
                                                    sor_id=data['seller_order__sor_id']).aggregate(Sum('quantity'))[
                'quantity__sum']
            total_quantity = data['total_quantity']
        else:
            order = orders.filter(order_id=data['order__order_id'])[0]
            ordered_quantity = orders.filter(order_id=data['order__order_id']).aggregate(Sum('quantity'))[
                'quantity__sum']
        order_id = order.order_code + str(order.order_id)
        if order.original_order_id:
            order_id = order.original_order_id

        if not ordered_quantity:
            ordered_quantity = 0

        order_date = get_local_date(user, order.creation_date)

        if is_marketplace:
            data_dict = OrderedDict((('UOR ID', order_id), ('SOR ID', summary.seller_order.sor_id),
                                     ('Seller ID', summary.seller_order.seller.seller_id),
                                     ('id', str(data['seller_order__order__order_id']) + \
                                      ":" + str(data['pick_number']) + ":" + data['seller_order__seller__name']),
                                     ('check_field', 'SOR ID')
                                     ))
        else:
            data_dict = OrderedDict((('Order ID', order_id), ('id', str(data['order__order_id']) + ":" + \
                                                              str(data['pick_number'])), ('check_field', 'Order ID')))
        data_dict.update(OrderedDict((('Customer Name', order.customer_name), ('Customer Name', order.customer_name),
                                      ('Order Quantity', ordered_quantity), ('Picked Quantity', data['total_quantity']),
                                      ('Order Date&Time', order_date),
                                      ('Invoice Number', '')
                                      )))
        temp_data['aaData'].append(data_dict)
    log.info('Customer Invoice filtered %s for %s ' % (str(temp_data['recordsTotal']), user.username))


@csrf_exempt
@get_admin_user
def generate_customer_invoice(request, user=''):
    data = []
    user_profile = UserProfile.objects.get(user_id=user.id)
    order_date = ''
    order_id = ''
    total_quantity = 0
    total_amt = 0
    total_invoice = 0
    total_tax = 0
    total_mrp = 0
    order_no = ''
    merge_data = {}
    data_dict = dict(request.GET.iterlists())
    log.info('Request params for ' + user.username + ' is ' + str(request.GET.dict()))
    try:
        seller_summary_dat = data_dict.get('seller_summary_id', '')
        seller_summary_dat = seller_summary_dat[0]
        sor_id = ''
        sell_ids = {}
        field_mapping = {}
        if data_dict.get('sor_id', ''):
            is_marketplace = True
            sor_id = data_dict.get('sor_id', '')[0]
            sell_ids['seller_order__sor_id'] = sor_id
            field_mapping['order_id_in'] = 'seller_order__order__order_id__in'
            field_mapping['sku_code'] = 'seller_order__order__sku__sku_code'
            field_mapping['order_id'] = 'seller_order__order_id'
            sell_ids['seller_order__seller__user'] = user.id
        else:
            is_marketplace = False
            sell_ids['order__user'] = user.id
            field_mapping['order_id_in'] = 'order__order_id__in'
            field_mapping['sku_code'] = 'order__sku__sku_code'
            field_mapping['order_id'] = 'order_id'
        seller_summary_dat = seller_summary_dat.split(',')
        all_data = OrderedDict()
        seller_order_ids = []
        for data_id in seller_summary_dat:
            splitted_data = data_id.split(':')
            sell_ids.setdefault(field_mapping['order_id_in'], [])
            sell_ids.setdefault('pick_number__in', [])
            sell_ids[field_mapping['order_id_in']].append(splitted_data[0])
            sell_ids['pick_number__in'].append(splitted_data[1])
        seller_summary = SellerOrderSummary.objects.filter(**sell_ids)
        order_ids = list(seller_summary.values_list(field_mapping['order_id'], flat=True))
        order_ids = map(lambda x: str(x), order_ids)
        order_ids = ','.join(order_ids)
        summary_details = seller_summary.values(field_mapping['sku_code']).distinct().annotate(
            total_quantity=Sum('quantity'))
        for detail in summary_details:
            if not detail[field_mapping['sku_code']] in merge_data.keys():
                merge_data[detail[field_mapping['sku_code']]] = detail['total_quantity']
            else:
                merge_data[detail[field_mapping['sku_code']]] += detail['total_quantity']

        invoice_data = get_invoice_data(order_ids, user, merge_data=merge_data, is_seller_order=True, sell_ids=sell_ids)
        edit_invoice = request.GET.get('edit_invoice', '')
        if edit_invoice != 'true':
            invoice_data = modify_invoice_data(invoice_data, user)
        ord_ids = order_ids.split(",")
        invoice_data = add_consignee_data(invoice_data, ord_ids, user)
        invoice_date = datetime.datetime.now()
        if seller_summary:
            if seller_summary[0].seller_order:
                seller = seller_summary[0].seller_order.seller
                order = seller_summary[0].seller_order.order
            else:
                order = seller_summary[0].order

            invoice_date = seller_summary.order_by('-creation_date')[0].creation_date
        invoice_date = get_local_date(user, invoice_date, send_date='true')
        inv_month_year = invoice_date.strftime("%m-%y")
        invoice_date = invoice_date.strftime("%d %b %Y")
        invoice_no = invoice_data['invoice_no']
        if is_marketplace:
            # invoice_no = user_profile.prefix + '/' + str(inv_month_year) + '/' + 'A-' + str(order.order_id)
            # invoice_data['order_id'] = sor_id
            invoice_data['sor_id'] = sor_id
        if not len(set(sell_ids.get('pick_number__in', ''))) > 1:
            invoice_no = invoice_no + '/' + str(max(map(int, sell_ids.get('pick_number__in', ''))))
        invoice_data['invoice_no'] = invoice_no
        invoice_data = add_consignee_data(invoice_data, ord_ids, user)
        return_data = request.GET.get('data', '')
        if return_data:
            invoice_data = json.dumps(invoice_data)
        elif get_misc_value('show_imei_invoice', user.id) == 'true':
            invoice_data = build_marketplace_invoice(invoice_data, user, False)
        else:
            invoice_data = build_invoice(invoice_data, user, False)

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create customer invoice failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
        return HttpResponse(json.dumps({'message': 'failed'}))
    return HttpResponse(invoice_data)


@csrf_exempt
def get_seller_order_view(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters,
                          user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_dict = eval(user_dict)
    lis = ['sor_id', 'sor_id', 'order__order_id', 'seller__name', 'order__customer_name', 'order__marketplace', 'total',
           'order__creation_date', 'order__city', 'order__status']
    data_dict = {'order__status': 1, 'order__user': user.id, 'order__quantity__gt': 0, 'status': 1}

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    if user_dict.get('market_places', ''):
        marketplace = user_dict['market_places'].split(',')
        data_dict['order__marketplace__in'] = marketplace
    if user_dict.get('customer_id', ''):
        data_dict['order__customer_id'], data_dict['order__customer_name'] = user_dict['customer_id'].split(':')
    search_params = get_filtered_params(filters, lis[1:])

    if 'order__order_id__icontains' in search_params.keys():
        order_search = search_params['order__order_id__icontains']
        search_params['order__order_id__icontains'] = ''.join(re.findall('\d+', order_search))
        search_params['order__order_code__icontains'] = ''.join(re.findall('\D+', order_search))
    search_params['order__sku_id__in'] = sku_master_ids
    order_taken_val_user = CustomerOrderSummary.objects.filter(order__user=user.id)
    single_search = "no"
    if 'city__icontains' in search_params.keys():
        order_taken_val_user = CustomerOrderSummary.objects.filter(
            Q(order_taken_by__icontains=search_params['city__icontains']))
        single_search = "yes"
        del (search_params['city__icontains'])

    all_seller_orders = SellerOrder.objects.filter(**data_dict)
    if search_term:
        mapping_results = all_seller_orders.values('order__customer_name', 'order__order_id', 'order__order_code',
                                                   'order__original_order_id',
                                                   'order__marketplace', 'sor_id', 'seller__name', 'seller_id'). \
            distinct().annotate(total=Sum('quantity')).filter(Q(order__customer_name__icontains=search_term) |
                                                              Q(order__order_id__icontains=search_term) | Q(
            order__marketplace__icontains=search_term) |
                                                              Q(sor_id__icontains=search_term) | Q(
            seller__name__icontains=search_term) |
                                                              Q(total__icontains=search_term),
                                                              **search_params).order_by(order_data)
    else:
        mapping_results = all_seller_orders.values('order__customer_name', 'order__order_id', 'order__order_code',
                                                   'order__original_order_id',
                                                   'order__marketplace', 'sor_id', 'seller__name', 'seller_id'). \
            distinct().annotate(total=Sum('quantity')).filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    index = 0
    for dat in mapping_results[start_index:stop_index]:
        cust_status_obj = CustomerOrderSummary.objects.filter(order__order_id=dat['order__order_id'])
        if cust_status_obj:
            cust_status = cust_status_obj[0].status
            time_slot = cust_status_obj[0].shipment_time_slot
        else:
            cust_status = ""
            time_slot = ""

        order_taken_val = ''
        if order_taken_val_user:
            order_taken_val = order_taken_val_user.filter(order__order_id=dat['order__order_id'])
            if order_taken_val:
                order_taken_val = order_taken_val[0].order_taken_by
            else:
                order_taken_val = ''
        if single_search == "yes" and order_taken_val == '':
            continue

        order_id = dat['order__order_code'] + str(dat['order__order_id'])
        check_values = str(order_id) + '<>' + str(dat['sor_id']) + '<>' + str(dat['seller_id'])
        name = all_seller_orders.filter(order__order_id=dat['order__order_id'],
                                        order__order_code=dat['order__order_code'], order__user=user.id)
        creation_date = name[0].creation_date
        name = name[0].id
        creation_data = get_local_date(user, creation_date, True).strftime("%d %b, %Y")
        # if time_slot:
        #    shipment_data = shipment_data + ', ' + time_slot

        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (
        str(order_id) + '<>' + str(dat['sor_id']), dat['total'])

        temp_data['aaData'].append(OrderedDict((('', checkbox), ('data_value', check_values), ('SOR ID', dat['sor_id']),
                                                ('UOR ID', order_id), ('Seller Name', dat['seller__name']),
                                                ('Customer Name', dat['order__customer_name']),
                                                ('Market Place', dat['order__marketplace']),
                                                ('Total Quantity', dat['total']), ('Order Taken By', order_taken_val),
                                                ('Creation Date', creation_data),
                                                ('id', index), ('DT_RowClass', 'results'), ('Status', cust_status))))
        index += 1
    col_val = ['SOR ID', 'SOR ID', 'UOR ID', 'Seller Name', 'Customer Name', 'Market Place', 'Total Quantity',
               'Creation Date', 'Order Taken By', 'Status']
    if order_term:
        order_data = col_val[col_num]
        if order_term == "asc":
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data])
        else:
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data], reverse=True)


@csrf_exempt
@login_required
@get_admin_user
def seller_generate_picklist(request, user=''):
    filters = request.POST.get('filters', '')
    order_filter = {'order__status': 1, 'order__user': user.id, 'order__quantity__gt': 0}
    if filters:
        filters = eval(filters)
        if filters['market_places']:
            order_filter['order__marketplace__in'] = (filters['market_places']).split(',')
        if filters.get('customer_id', ''):
            customer_id = ''.join(re.findall('\d+', filters['customer_id']))
            order_filter['order__customer_id'] = customer_id
    data = []
    order_data = []
    stock_status = ''
    out_of_stock = []
    picklist_number = get_picklist_number(user)

    log.info('Request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
        sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
            location__zone__zone='DAMAGED_ZONE'). \
            filter(sku__user=user.id, quantity__gt=0)
        all_seller_orders = SellerOrder.objects.prefetch_related('order__sku').filter(**order_filter)

        fifo_switch = get_misc_value('fifo_switch', user.id)
        if fifo_switch == 'true':
            stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
                'receipt_date')
            data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
            stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
        else:
            stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
                'location_id__pick_sequence')
            stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by(
                'receipt_date')
        all_sku_stocks = stock_detail1 | stock_detail2
        seller_stocks = SellerStock.objects.filter(seller__user=user.id).values('stock_id', 'seller_id')
        for key, value in request.POST.iteritems():
            if key in PICKLIST_SKIP_LIST or key in ['filters']:
                continue

            sku_stocks = all_sku_stocks
            order_filter = {'quantity__gt': 0}
            seller_id = ''
            if '<>' in key:
                key = key.split('<>')
                order_id, sor_id, seller_id = key
                order_filter['sor_id'] = sor_id
                order_filter['seller_id'] = seller_id
            else:
                order_id = key
            if seller_id:
                seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(seller_id), seller_stocks)
                if seller_stock_dict:
                    sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
                    sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
                else:
                    sku_stocks = sku_stocks.filter(id=0)
            order_code = ''.join(re.findall('\D+', order_id))
            order_id = ''.join(re.findall('\d+', order_id))
            order_filter['order__order_id'] = order_id
            order_filter['order__order_code'] = order_code

            seller_orders = all_seller_orders.filter(**order_filter).order_by('order__shipment_date')

            stock_status, picklist_number = picklist_generation(seller_orders, request, picklist_number, user,
                                                                sku_combos, sku_stocks, \
                                                                status='open', remarks='', is_seller_order=True)

            if stock_status:
                out_of_stock = out_of_stock + stock_status

        if out_of_stock:
            stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
        else:
            stock_status = ''

        show_image = 'false'
        use_imei = 'false'
        order_status = ''
        headers = list(PROCESSING_HEADER)
        data1 = MiscDetail.objects.filter(user=user.id, misc_type='show_image')
        if data1:
            show_image = data1[0].misc_value
        if show_image == 'true':
            headers.insert(0, 'Image')
        imei_data = MiscDetail.objects.filter(user=user.id, misc_type='use_imei')
        if imei_data:
            use_imei = imei_data[0].misc_value
        if use_imei == 'true':
            headers.insert(-1, 'Serial Number')
        if get_misc_value('pallet_switch', user.id) == 'true':
            headers.insert(headers.index('Location') + 1, 'Pallet Code')

        data, sku_total_quantities = get_picklist_data(picklist_number + 1, user.id)
        if data:
            order_status = data[0]['status']
            if order_status == 'open':
                headers.insert(headers.index('WMS Code'), 'Order ID')
                order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
                order_count_len = len(filter(lambda x: len(str(x)) > 0, order_count))
                if order_count_len == 1:
                    single_order = str(order_count[0])
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Seller Order level Generate Picklist failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse(json.dumps({'stock_status': 'Generate Picklist Failed'}))

    return HttpResponse(json.dumps({'data': data, 'headers': headers,
                                    'picklist_id': picklist_number + 1, 'stock_status': stock_status,
                                    'show_image': show_image,
                                    'use_imei': use_imei, 'order_status': order_status, 'user': request.user.id, \
                                    'sku_total_quantities': sku_total_quantities}))


def update_exist_picklists(picklist_no, request, user, sku_code='', location='', picklist_obj=None):
    filter_param = {'reserved_quantity__gt': 0, 'picklist_number': picklist_no}
    if picklist_obj:
        picklist_objs = [picklist_obj]
    elif not sku_code:
        picklist_objs = Picklist.objects.filter(Q(stock__sku__user=user.id) | Q(order__user=user.id), **filter_param)
    else:
        picklist_objs = Picklist.objects.filter(Q(stock__sku__user=user.id) | Q(order__user=user.id),
                                                Q(stock__sku__sku_code=sku_code) |
                                                Q(order__sku__sku_code=sku_code) | Q(sku_code=sku_code), **filter_param)
    picklist_data = {}
    new_pc_locs_list = []
    for item in picklist_objs:
        _sku_code = ''
        if item.order:
            _sku_code = item.order.sku.sku_code
        elif item.stock:
            _sku_code = item.stock.sku.sku_code
        if item.sku_code:
            _sku_code = item.sku_code

        stock_params = {'sku__user': user.id, 'quantity__gt': 0, 'sku__sku_code': _sku_code}
        if location:
            stock_params['location__location'] = location
        stock_objs = StockDetail.objects.prefetch_related('sku', 'location').exclude(
            location__zone__zone='DAMAGED_ZONE').filter(**stock_params).order_by('location__pick_sequence')

        picklist_data['stock_id'] = 0
        stock_quan = 0
        if item.stock_id:
            picklist_data['stock_id'] = item.stock_id
            current_stock_objs = stock_objs.filter(id=item.stock_id)
            if current_stock_objs:
                current_stock_obj = current_stock_objs[0]
                stock_quan = current_stock_obj.quantity
                if current_stock_obj.quantity >= item.reserved_quantity:
                    continue

        needed_quantity = item.reserved_quantity
        if stock_quan:
            needed_quantity = needed_quantity - stock_quan
        if not needed_quantity:
            continue
        consumed_qty = 0

        if item.order:
            picklist_data['order_id'] = item.order.id
        picklist_data['sku_code'] = item.sku_code
        picklist_data['picklist_number'] = picklist_no
        picklist_data['reserved_quantity'] = 0
        picklist_data['picked_quantity'] = 0
        picklist_data['remarks'] = item.remarks
        picklist_data['order_type'] = item.order_type
        picklist_data['status'] = item.status

        consumed_qty, new_pc_locs = picklist_location_suggestion(request, item.order, stock_objs, user, needed_quantity,
                                                                 picklist_data)
        if new_pc_locs:
            new_pc_locs_list = list(chain(new_pc_locs_list, new_pc_locs))

        item.reserved_quantity -= float(consumed_qty)
        item.save()
        if consumed_qty:
            exist_pics = PicklistLocation.objects.filter(picklist_id=item.id, status=1, reserved__gt=0)
            update_picklist_locations(exist_pics, item, consumed_qty, 'true')
        if item.reserved_quantity == 0 and not item.picked_quantity:
            item.delete()
    return new_pc_locs_list


@csrf_exempt
@login_required
@get_admin_user
def update_picklist_loc(request, user=""):
    picklist_no = request.GET.get('picklist_id', "")
    if not picklist_no:
        return HttpResponse('PICKLIST ID missing')

    update_exist_picklists(picklist_no, request, user)
    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def customer_invoice_data(request, user=''):
    user_profile = UserProfile.objects.get(user_id=user.id)
    if user_profile.user_type == 'marketplace_user':
        headers = MP_CUSTOMER_INVOICE_HEADERS
    else:
        headers = WH_CUSTOMER_INVOICE_HEADERS
    return HttpResponse(json.dumps({'headers': headers}))


@csrf_exempt
@login_required
@get_admin_user
def search_template_names(request, user=''):
    template_names = []
    name = request.GET.get('q', '')

    if name:
        template_names = list(
            ProductProperties.objects.filter(user_id=user.id, name__icontains=name).values_list('name',
                                                                                                flat=True).distinct())

    return HttpResponse(json.dumps(template_names, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def get_custom_template_styles(request, user=''):
    request_data = request.GET
    filter_params = {'user': user.id, 'status': 1}
    sku_category = request_data.get('category', '')
    sku_brand = request_data.get('brand', '')
    customer_data_id = request_data.get('customer_data_id', '')
    name = request_data.get('name', '')
    customer_id = ''

    product_properties = ProductProperties.objects.filter(user=user.id, name=name)
    brands_list = product_properties.values_list('brand', flat=True)
    categories_list = product_properties.values_list('category', flat=True)
    sku_master = SKUMaster.objects.exclude(sku_class='').filter(user=user.id, sku_brand__in=brands_list,
                                                                sku_category__in=categories_list)
    if sku_brand and not sku_brand.upper() == 'ALL':
        filter_params['sku_brand'] = sku_brand
    if sku_category and not sku_category.upper() == 'ALL':
        filter_params['sku_category'] = sku_category
    start, stop = 0, None

    sku_master = sku_master.filter(**filter_params)
    size_dict = request_data.get('size_filter', '')
    query_string = 'sku__sku_code'
    if size_dict:
        size_dict = eval(size_dict)
        if size_dict:
            classes = get_sku_available_stock(user, sku_master, query_string, size_dict)
            sku_master = sku_master.filter(sku_class__in=classes)

    sku_master = sku_master.order_by('sequence')
    product_styles = sku_master.values_list('sku_class', flat=True).distinct()
    product_styles = list(OrderedDict.fromkeys(product_styles))
    data = get_styles_data(user, product_styles, sku_master, start, stop, customer_id='', customer_data_id='',
                           is_file='')
    return HttpResponse(json.dumps({'data': data}))


@csrf_exempt
@login_required
@get_admin_user
def get_order_labels(request, user=''):
    picklist_number = request.GET.get('picklist_number', 0)
    if not picklist_number:
        return HttpResponse(json.dumps({'message': 'Please send picklist number', 'data': []}))
    picklists = Picklist.objects.filter(Q(stock__sku__user=user.id) | Q(order__user=user.id),
                                        picklist_number=picklist_number,
                                        reserved_quantity__gt=0)

    data = []
    for picklist in picklists:
        if not picklist.order:
            continue
        labels = OrderLabels.objects.filter(order_id=picklist.order_id, status=1).exclude(
            picklist__picklist_number=picklist_number)
        label_count = 0
        mapped_labels = OrderLabels.objects.filter(picklist_id=picklist.id, status=1, order_id=picklist.order_id)
        for map_label in mapped_labels:
            data.append({'label': map_label.label, 'wms_code': map_label.order.sku.sku_code, 'quantity': 1})
            label_count += 1
            if int(picklist.reserved_quantity) == int(label_count):
                break

        for label in labels:
            if int(picklist.reserved_quantity) == int(label_count):
                break
            label.picklist_id = picklist.id
            label.save()
            data.append({'label': label.label, 'wms_code': label.order.sku.sku_code, 'quantity': 1})
            label_count += 1

    return HttpResponse(json.dumps({'message': 'Success', 'data': data}))


@csrf_exempt
@login_required
@get_admin_user
def get_sub_category_styles(request, user=''):
    resp = {'message': 'Success', 'data': []}
    sub_category = request.GET.get('sub_category', '')

    if not sub_category:
        resp['message'] = 'Fail'
        return HttpResponse(json.dumps(resp))
    product_styles = SKUMaster.objects.exclude(sku_class='').filter(user=user.id,
                                                                    sub_category=sub_category).values_list('sku_class',
                                                                                                           flat=True).distinct()

    if not product_styles:
        resp['message'] = 'date empty'
        return HttpResponse(json.dumps(resp))

    sku_data = []
    sku_master = SKUMaster.objects.filter(user=user.id)
    for product in product_styles:
        sku_object = sku_master.filter(sku_class=product)
        sku_styles = sku_object.values('image_url', 'sku_class', 'sku_desc', 'sequence', 'id'). \
            order_by('-image_url')
        sku_data.append(sku_styles[0])

    resp['data'] = sku_data
    return HttpResponse(json.dumps(resp))


def get_incremental(user, type_name):
    # custom sku counter
    default = 1000
    data = IncrementalTable.objects.filter(user=user.id, type_name=type_name)
    if data:
        data = data[0]
        count = data.value + 1
        data.value = data.value + 1
        data.save()
    else:
        IncrementalTable.objects.create(user_id=user.id, type_name=type_name, value=1001)
        count = default
    return count


def save_custom_order_images(user, request, sku_class):
    path = 'static/images/custom'
    if not os.path.exists(path):
        os.makedirs(path)
    folder = user.id
    if not os.path.exists(path + "/" + str(folder)):
        os.makedirs(path + "/" + str(folder))
    image_data = {}
    if len(request.FILES):
        for file_name, file_data in request.FILES.iteritems():
            extension = file_data.name.split('.')[-1]
            full_filename = os.path.join(path, str(folder), str(sku_class) + "_" + file_name + '.' + str(extension))
            fout = open(full_filename, 'wb+')
            file_content = ContentFile(file_data.read())

            try:
                # Iterate through the chunks.
                file_contents = file_content.chunks()
                for chunk in file_contents:
                    fout.write(chunk)
                fout.close()
                image_data[file_name] = "/" + full_filename
            except:
                print 'not saved'
            print file_name
    return image_data
    '''
    import base64
    for work_type, work_data in image_data.iteritems():
        for place, data in work_data.iteritems():
            with open(path + place + ".png", "wb") as fh:
                fh.write(base64.decodestring(data + "=="))
            #fh = open(path + place + ".png", "wb")
            #fh.write(data.decode('base64'))
            #fh.close()
    '''


@csrf_exempt
@login_required
@get_admin_user
def create_custom_skus(request, user=''):
    # it will create new skus and returns the data

    resp = {'message': 'Success', 'data': []}
    data = request.POST.get('model', '')

    if not data:
        resp['message'] = "Fail"
        return HttpResponse(json.dumps(resp))

    order_data = []

    image_data = {}
    image_status = True
    data = json.loads(json.loads(data))
    for size_name, value in data['sizeEnable'].iteritems():
        if value and data['sizeTotals'][size_name]:
            sku = get_incremental(user, "sku_code")
            if image_status:
                image_status = False
                image_data = save_custom_order_images(user, request, sku)
                ''''if data['printEmbroidery']:
                    for place, image in data['print']['places'].iteritems():
                        name = ""
                        if image:
                            name = str(sku)+"_print_"+place
                            image_data['print'][name] = data['print']['placeImgs'][place]
                        data['print']['placeImgs'][place] = name
                    for place, image in data['embroidery']['places'].iteritems():
                        name = ""
                        if image:
                            name = str(sku)+"_emboidery_"+place
                            image_data['embroidery'][name] = data['embroidery']['placeImgs'][place]
                        data['embroidery']['placeImgs'][place] = name
                else:
                    data['print']['placeImgs'] = {}
                    data['embroidery']['placeImgs'] = {}
                '''
                data['image_data'] = image_data
                data['sku_class'] = sku
            for size, quantity in data['sizeValues'][size_name].iteritems():
                if quantity:
                    data_dict = copy.deepcopy(SKU_DATA)
                    data_dict['user'] = user.id
                    data_dict['sku_code'] = "CS" + str(sku) + "-" + size
                    data_dict['wms_code'] = data_dict['sku_code']
                    data_dict['sku_class'] = str(sku) + "-" + size_name
                    data_dict['sku_size'] = size
                    data_dict['sku_type'] = "CS"

                    sku_desc = size_name + "_" + size
                    if data['bodyStyle'].get('sku_class', ''):
                        sku_desc = data['bodyStyle'].get('sku_class', '') + "_" + sku_desc
                        data_dict['image_url'] = data['bodyStyle'].get('image_url', '')

                    data_dict['sku_desc'] = sku_desc
                    sku_master = SKUMaster(**data_dict)
                    sku_master.save()
                    SKUJson.objects.create(sku_id=sku_master.id, json_data=json.dumps(data))
                    order_data.append({'sku_id': data_dict['sku_code'], 'sku_desc': data_dict['sku_desc'], \
                                       'quantity': quantity, 'extra': data})
    resp['data'] = order_data
    return HttpResponse(json.dumps(resp))


@csrf_exempt
@login_required
@get_admin_user
def insert_enquiry_data(request, user=''):
    message = 'Success'
    customer_id = request.user.id
    cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    if not cum_obj:
        return "No Customer User Mapping Object"
    cm_id = cum_obj[0].customer_id
    enquiry_id = get_enquiry_id(cm_id)
    cart_items = CustomerCartData.objects.filter(customer_user_id=customer_id)
    if not cart_items:
        return HttpResponse('No Data in Cart')
    try:
        customer_details = {}
        customer_details = get_order_customer_details(customer_details, request)
        customer_details['customer_id'] = cm_id  # Updating Customer Master ID
        enquiry_map = {'user': user.id, 'enquiry_id': enquiry_id}
        enquiry_map.update(customer_details)
        enq_master_obj = EnquiryMaster(**enquiry_map)
        enq_master_obj.save()
        for cart_item in cart_items:
            enquiry_data = {'customer_id': customer_id, 'warehouse_level': cart_item.warehouse_level,
                            'user': user.id, 'quantity': cart_item.quantity, 'sku_id': cart_item.sku.id}
            stock_wh_map = split_orders(**enquiry_data)
            for wh_code, qty in stock_wh_map.items():
                wh_sku_id = get_syncedusers_mapped_sku(wh_code, cart_item.sku.id)
                enq_sku_obj = EnquiredSku()
                enq_sku_obj.sku_id = wh_sku_id
                enq_sku_obj.title = cart_item.sku.style_name  # TODO Need to check
                enq_sku_obj.enquiry = enq_master_obj
                enq_sku_obj.quantity = cart_item.quantity
                enq_sku_obj.invoice_amount = cart_item.quantity * cart_item.levelbase_price
                enq_sku_obj.status = 1
                enq_sku_obj.sku_code = cart_item.sku.sku_code
                enq_sku_obj.levelbase_price = cart_item.levelbase_price
                enq_sku_obj.warehouse_level = cart_item.warehouse_level
                enq_sku_obj.save()
    except:
        import traceback
        log.debug(traceback.format_exc())
        message = 'Failed'
    else:
        CustomerCartData.objects.filter(customer_user=request.user.id).delete()
    return HttpResponse(message)


@get_admin_user
def get_enquiry_data(request, user=''):
    index = request.GET.get('index', '')
    start_index, stop_index = 0, 20
    if index:
        start_index = int(index.split(':')[0])
        stop_index = int(index.split(':')[1])
    response_data = {'data': []}
    cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    if not cum_obj:
        return HttpResponse("No Customer User Mapping Object")
    cm_id = cum_obj[0].customer_id
    em_qs = EnquiryMaster.objects.filter(customer_id=cm_id)
    em_vals = em_qs.values_list('enquiry_id', flat=True).distinct()
    total_qty = dict(em_qs.values_list('enquiry_id').distinct().annotate(quantity=Sum('enquiredsku__quantity')))
    total_inv_amt = dict(
        em_qs.values_list('enquiry_id').distinct().annotate(inv_amt=Sum('enquiredsku__invoice_amount')))
    for enq_id in em_vals[start_index:stop_index]:
        enq_id = int(enq_id)
        res_map = {'order_id': enq_id, 'customer_id': cm_id,
                   'total_quantity': total_qty[enq_id],
                   'date': get_only_date(request, em_qs.filter(enquiry_id=enq_id)[0].creation_date),
                   'total_inv_amt': round(total_inv_amt[enq_id], 2)}
        response_data['data'].append(res_map)
    return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder))


def get_tax_inclusive_invoice_amt(cm_id, unit_price, qty, usr, sku_code):
    usr_sku_master = SKUMaster.objects.get(user=usr, sku_code=sku_code)
    customer_master = CustomerMaster.objects.get(id=cm_id)
    taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0}
    if customer_master.tax_type:
        inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
        inter_state = inter_state_dict.get(customer_master.tax_type, 2)
        tax_master = TaxMaster.objects.filter(user_id=usr, inter_state=inter_state,
                                              product_type=usr_sku_master.product_type,
                                              min_amt__lte=unit_price, max_amt__gte=unit_price)
        if tax_master:
            tax_master = tax_master[0]
            taxes['cgst_tax'] = float(tax_master.cgst_tax)
            taxes['sgst_tax'] = float(tax_master.sgst_tax)
            taxes['igst_tax'] = float(tax_master.igst_tax)
            taxes['utgst_tax'] = float(tax_master.utgst_tax)
    invoice_amount = qty * unit_price
    invoice_amount = invoice_amount + ((invoice_amount / 100) * sum(taxes.values()))
    return invoice_amount


@get_admin_user
def get_customer_enquiry_detail(request, user=''):
    whole_res_map = {}
    response_data_list = []
    sku_wise_details = {}
    enquiry_id = request.GET['enquiry_id']
    cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    user_profile = UserProfile.objects.filter(user=request.user.id)
    filters = {'enquiry_id': float(enquiry_id)}
    if user_profile and user_profile[0].warehouse_type == 'DIST':
        if not request.GET.get('customer_id', ''):
            return HttpResponse("Please Send Customer ID")
        filters['customer_id'] = request.GET.get('customer_id', '')
    elif not cum_obj:
        return HttpResponse("No Customer User Mapping Object")
    else:
        filters['customer_id'] = cum_obj[0].customer_id
    em_qs = EnquiryMaster.objects.filter(**filters)
    if not em_qs:
        return HttpResponse("No Enquiry Data for Id")
    cm_id = em_qs[0].customer_id
    sku_lbprice_map = {}
    sku_tot_qty_map ={}
    sku_tot_inv_map = {}
    for em_obj in em_qs:
        data_vals = list(em_obj.enquiredsku_set.values('sku', 'sku__sku_code', 'sku__image_url',
                                                       'sku__sku_desc', 'quantity', 'levelbase_price',
                                                       'invoice_amount', 'warehouse_level'))
        for data_val in data_vals:
            sku_code = data_val['sku__sku_code']
            qty = data_val['quantity']
            inv_amt = data_val['invoice_amount']
            lb_price = data_val['levelbase_price']
            tot_amt = get_tax_inclusive_invoice_amt(cm_id, lb_price, qty, user.id, sku_code)
            data_val['invoice_amount'] = tot_amt
            if sku_code not in sku_tot_qty_map:
                sku_tot_qty_map[sku_code] = qty
            else:
                sku_tot_qty_map[sku_code] = sku_tot_qty_map[sku_code] + qty
            if sku_code not in sku_tot_inv_map:
                sku_tot_inv_map[sku_code] = inv_amt
            else:
                sku_tot_inv_map[sku_code] = sku_tot_inv_map[sku_code] + inv_amt

        for sku_code in sku_tot_qty_map:
            sku_lbprice_map[sku_code] = sku_tot_inv_map[sku_code] / sku_tot_qty_map[sku_code]
        total_inv_amt = map(sum, [[i['invoice_amount'] for i in em_obj.enquiredsku_set.values()]])[0]
        tot_amt_inc_taxes = map(sum, [[i['invoice_amount'] for i in data_vals]])[0]
        total_tax_amt = round(tot_amt_inc_taxes - total_inv_amt, 2)
        total_qty = map(sum, [[i['quantity'] for i in em_obj.enquiredsku_set.values()]])[0]
        sum_data = {'amount': round(tot_amt_inc_taxes, 2), 'quantity': total_qty}
        res_map = {'order_id': em_obj.enquiry_id, 'customer_id': cm_id,
                   'date': get_only_date(request, em_obj.creation_date),
                   'data': data_vals, 'sum_data': sum_data, 'tax': total_tax_amt}
        for sku_rec in data_vals:
            sku_code = sku_rec['sku__sku_code']
            if sku_code not in sku_wise_details:
                sku_qty = sku_rec['quantity']
                sku_el_price = sku_lbprice_map[sku_code]
                tot_amt = get_tax_inclusive_invoice_amt(cm_id, sku_el_price, sku_qty, user.id, sku_code)
                sku_wise_details[sku_code] = {'quantity': sku_qty, 'el_price': sku_el_price,
                                              'tot_inc_tax_inv_amt': tot_amt}
            else:
                existing_map = sku_wise_details[sku_code]
                existing_map['quantity'] = existing_map['quantity'] + sku_rec['quantity']
                existing_map['el_price'] = sku_lbprice_map[sku_code]
                tot_amt = get_tax_inclusive_invoice_amt(cm_id, sku_lbprice_map[sku_code], sku_rec['quantity'],
                                                        user.id, sku_code)
                existing_map['tot_inc_tax_inv_amt'] = tot_amt
        response_data_list.append(res_map)
    sku_whole_map = {'data': [], 'totals': {}}
    sku_totals = {'sub_total': 0, 'total_amount': 0, 'tax': 0}
    for sku_code, sku_det in sku_wise_details.items():
        el_price = sku_det['el_price']
        qty = sku_det['quantity']
        total_amt = float(qty) * float(el_price)
        tax_amt = sku_det['tot_inc_tax_inv_amt'] - total_amt
        sku_map = {'sku_code': sku_code, 'quantity': qty, 'landing_price': el_price, 'total_amount': total_amt}
        sku_totals['sub_total'] = sku_totals['sub_total'] + total_amt
        sku_totals['tax'] = sku_totals['tax'] + tax_amt
        sku_totals['total_amount'] = sku_totals['sub_total'] + sku_totals['tax']
        sku_whole_map['data'].append(sku_map)
        sku_whole_map['totals'] = sku_totals
    whole_res_map['data'] = response_data_list
    whole_res_map['sku_wise_details'] = sku_whole_map
    return HttpResponse(json.dumps(whole_res_map, cls=DjangoJSONEncoder))


@csrf_exempt
def get_enquiry_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                       filters={}, user_dict={}):
    em_qs = EnquiryMaster.objects.filter(user=user.id)
    for em_obj in em_qs:
        enq_id = int(em_obj.enquiry_id)
        total_qty = map(sum, [[i['quantity'] for i in em_obj.enquiredsku_set.values()]])[0]
        customer_name = CustomerMaster.objects.get(id=em_obj.customer_id).name
        date = em_obj.creation_date.strftime('%Y-%m-%d')
        temp_data['aaData'].append(OrderedDict((('Enquiry ID', enq_id), ('Customer Name', customer_name),
                                                ('Quantity', total_qty), ('Date', date),
                                                ('Customer ID', em_obj.customer_id))))
    temp_data['recordsTotal'] = len(temp_data['aaData'])
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


@get_admin_user
def move_enquiry_to_order(request, user=''):
    message = 'Success'
    enquiry_id = request.GET.get('enquiry_id', '')
    if not enquiry_id:
        return HttpResponse('No enquiry ID')
    cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    if not cum_obj:
        return "No Customer User Mapping Object"
    cm_id = cum_obj[0].customer_id
    em_qs = EnquiryMaster.objects.filter(enquiry_id=enquiry_id, customer_id=cm_id)
    try:
        for em_obj in em_qs:
            data_vals = em_obj.enquiredsku_set.values_list('sku', 'quantity', 'levelbase_price', 'warehouse_level')
            for data_val in data_vals:
                sku, quantity, lb_price, warehouse_level = data_val
                data = {'user_id': user.id, 'customer_user_id': request.user.id, 'sku_id': int(sku),
                        'quantity': quantity, 'tax': 0, 'warehouse_level': warehouse_level,
                        'levelbase_price': lb_price}
                customer_cart_data = CustomerCartData(**data)
                customer_cart_data.save()
    except:
        import traceback
        log.debug(traceback.format_exc())
        message = 'Failed'
    else:
        em_qs.delete()  # Removing item from Enquiry Table after converting it to Order
    return HttpResponse(message)


@csrf_exempt
@login_required
@get_admin_user
def delete_order_charges(request, user=''):
    # It Will delete the other charges for Order.

    status = 1
    message = 'Deleted Successfully'
    log.info('Request Params for Delete Order Charges for user %s is %s' % (user.username, str(request.GET.dict())))
    try:
        data_id = request.GET.get('id', '')
        if data_id:
            other_charges = OrderCharges.objects.filter(id=data_id, user_id=user.id)
            if other_charges:
                other_charges.delete()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Delete Order Charges failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.GET.dict()), str(e)))
        status = 0
        message = 'Order Charges Deletion failed'

    return HttpResponse(json.dumps({'status': status, 'message': message}))

@csrf_exempt
@login_required
@get_admin_user
def order_cancel(request, user=''):
    message = 'Success'
    customer_user = CustomerUserMapping.objects.filter(user_id=request.user.id)
    customer_obj = CustomerMaster.objects.filter(customer_id=customer_user[0].customer.customer_id, user=user.id)
    if not customer_obj:
        message = 'Failed'
        return HttpResponse(message)
    cm_id = customer_obj[0].id
    admin_user = get_priceband_admin_user(user)
    try:
        if admin_user:
            gen_ord_id = request.GET.get('order_id', '')
            if gen_ord_id:
                gen_qs = GenericOrderDetailMapping.objects.filter(generic_order_id=gen_ord_id, customer_id=cm_id)
                uploaded_po_details = gen_qs.values('po_number', 'client_name').distinct()
                if uploaded_po_details.count() == 1:
                    po_number = uploaded_po_details[0]['po_number']
                    client_name = uploaded_po_details[0]['client_name']
                    ord_upload_qs = OrderUploads.objects.filter(uploaded_user=request.user.id,
                                                                po_number=po_number, customer_name=client_name)
                    ord_upload_qs.delete()
                order_det_ids = gen_qs.values_list('orderdetail_id', flat=True)
                ord_det_qs = OrderDetail.objects.filter(id__in=order_det_ids)
                ord_det_qs.delete()
                gen_qs.delete()
            #qssi push order api call to cancel order
            order_detail_id = GenericOrderDetailMapping.objects.latest('id').orderdetail_id
            order_detail_obj = OrderDetail.objects.filter(id = order_detail_id)
            if order_detail_obj:
                original_order_id = order_detail_obj[0].original_order_id
                resp = order_push(original_order_id, user, "CANCEL")
                log.info('Cancel Order Push Status: %s, Order ID: %s' %(resp["Status"], resp["OrderId"]))

        else:
            ord_id = request.GET.get('order_id', '')
            ord_qs = OrderDetail.objects.filter(order_id=ord_id, user=user)
            ord_qs.delete()
    except:
        import traceback
        log.debug(traceback.format_exc())
        message = 'Failed'
    return HttpResponse(message)
