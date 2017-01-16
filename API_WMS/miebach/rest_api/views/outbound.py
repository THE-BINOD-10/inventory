from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import json
from itertools import chain
from django.db.models import Q, F
from collections import OrderedDict
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
from django.template import loader, Context
from mail_server import send_mail, send_mail_attachment
from common import *
from miebach_utils import *
from operator import itemgetter
from itertools import groupby
import datetime
from utils import *
log = init_logger('logs/outbound.log')

@csrf_exempt
def get_batch_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters, user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_dict = eval(user_dict)
    lis = ['id', 'sku__sku_code', 'title', 'total']
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
        mapping_results = OrderDetail.objects.filter(**data_dict).values('sku__sku_code', 'title', 'sku_code').distinct().\
                                              annotate(total=Sum('quantity')).filter(Q(sku__sku_code__icontains=search_term) |
                                              Q(title__icontains=search_term) | Q(total__icontains=search_term), **search_params).\
                                              order_by(order_data)
    else:
        mapping_results = OrderDetail.objects.filter(**data_dict).values('sku__sku_code', 'title', 'sku_code').distinct().\
                                              annotate(total=Sum('quantity')).filter(**search_params).order_by(order_data)


    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    index = 0
    for dat in mapping_results[start_index:stop_index]:

        sku_code = dat['sku__sku_code']
        if sku_code == 'TEMP':
            sku_code = dat['sku_code']

        check_values = dat['sku__sku_code'] + '<>' + sku_code
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (check_values, dat['total'])

        temp_data['aaData'].append(OrderedDict(( ('data_value', check_values), ('sku_code', sku_code), ('title', dat['title']),
                                                 ('total_quantity', dat['total']), ('id', index), ('DT_RowClass', 'results') )))
        index += 1

@csrf_exempt
def get_order_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters, user_dict={}):

    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_dict = eval(user_dict)
    lis = ['id', 'order_id', 'sku__sku_code', 'title', 'quantity', 'shipment_date', 'marketplace']
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

    if search_term:
        master_data = OrderDetail.objects.filter(Q(sku__sku_code__icontains = search_term, status=1) | Q(order_id__icontains = search_term,
                                                 status=1) | Q(title__icontains = search_term, status=1) | Q(quantity__icontains = search_term,
                                                 status=1),user=user.id, quantity__gt=0).filter(**search_params)

    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = OrderDetail.objects.filter(**data_dict).filter(**search_params).order_by(order_data)
    else:
        master_data = OrderDetail.objects.filter(**data_dict).filter(**search_params).order_by('shipment_date')

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    count = 0
    for data in master_data[start_index:stop_index]:
        sku = SKUMaster.objects.get(sku_code=data.sku.sku_code,user=user.id)
        sku_code = sku.sku_code
        order_id = data.order_code + str(data.order_id)
        if data.original_order_id:
            order_id = data.original_order_id
        if sku_code == 'TEMP':
            sku_code = data.sku_code
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data.id, data.sku.sku_code)

        temp_data['aaData'].append(OrderedDict(( ('', checkbox), ('Order ID', order_id), ('SKU Code', sku_code),
                                                 ('Title', data.title),('id', count), ('Product Quantity', data.quantity),
                                                 ('Shipment Date', get_local_date(request.user, data.shipment_date)),
                                                 ('Marketplace', data.marketplace), ('DT_RowClass', 'results'),
                                                 ('DT_RowAttr', {'data-id': str(data.order_id)} )) ) )
        count = count+1

  
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
                                                   Q(quantity__icontains=search_term) | Q(order_id__icontains=search_term) |
                                                   Q(sku__sku_code__icontains=search_term), sku__user=user.id, status=1).order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
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
        filter_params['reserved_quantity__gt'] = 0
    else:
        del filter_params['status__icontains']
        filter_params['picked_quantity__gt'] = 0
    if status == 'batch_picked':
        col_num = col_num - 1

    if search_term:
        master_data = Picklist.objects.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids)).\
                                       filter( Q(picklist_number__icontains = search_term) | Q( remarks__icontains = search_term ),
                                               Q(order__sku__user = user.id) | Q(stock__sku__user=user.id), **filter_params).\
                                       values('picklist_number', 'remarks').distinct()

    elif order_term:
        order_data = PICK_LIST_HEADERS.values()[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = Picklist.objects.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids)).\
                                       filter(Q(order__sku__user = user.id) | Q(stock__sku__user=user.id), **filter_params).\
                                       values('picklist_number', 'remarks').distinct().order_by(order_data)
        master_data = [ key for key,_ in groupby(master_data)]
    else:
        master_data = Picklist.objects.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids)).\
                                       filter( Q(order__sku__user = user.id) | Q(stock__sku__user=user.id), **filter_params).\
                                       values('picklist_number', 'remarks').distinct()

    temp_data['recordsTotal'] = len( master_data )
    temp_data['recordsFiltered'] = len( master_data )

    all_picks = Picklist.objects.filter(Q(order__sku__user = user.id) | Q(stock__sku__user=user.id))
    count = 0
    for data in master_data[start_index:stop_index]:
        create_date = all_picks.filter(picklist_number=data['picklist_number'])[0].creation_date
        result_data = OrderedDict(( ('DT_RowAttr', { 'data-id': data['picklist_number'] }), ('picklist_note', data['remarks']),
                                    ('date', get_local_date(request.user, create_date)), ('id', count), ('DT_RowClass', 'results') ))

        dat = 'picklist_id'
        count += 1
        if status == 'batch_picked':                                    
            dat = 'picklist_id'

            checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data['picklist_number'], data['picklist_number'])
            result_data['checkbox'] = checkbox
        result_data[dat] = data['picklist_number']
        temp_data['aaData'].append(result_data)

@csrf_exempt
def get_customer_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['Shipment Number', 'Customer ID', 'Customer Name', 'Total Quantity']
    all_data = OrderedDict()
    if search_term:
        results = ShipmentInfo.objects.filter(order__sku_id__in=sku_master_ids).\
                                       filter(Q(order_shipment__shipment_number__icontains=search_term) |
                                              Q(order__customer_id__icontains=search_term) | Q(order__customer_name__icontains=search_term),
                                              order_shipment__user=user.id).order_by('order_id')
    else:
        results = ShipmentInfo.objects.filter(order__sku_id__in=sku_master_ids).\
                                       filter(order_shipment__user=user.id).order_by('order_id')
    for result in results:
        tracking = ShipmentTracking.objects.filter(shipment_id=result.id, shipment__order__user=user.id).order_by('-creation_date').\
                                            values_list('ship_status', flat=True)
        if tracking and tracking[0] == 'Delivered':
            continue
        cond = (result.order_shipment.shipment_number, result.order.customer_id, result.order.customer_name)
        all_data.setdefault(cond, 0)
        all_data[cond] += result.shipping_quantity

    temp_data['recordsTotal'] = len(all_data)
    temp_data['recordsFiltered'] = len(all_data)
    for key, value in all_data.iteritems():
        temp_data['aaData'].append({'DT_RowId': key[0], 'Shipment Number': key[0], 'Customer ID': key[1], 'Customer Name': key[2],
                                    'Total Quantity': value, 'DT_RowClass': 'results' })
    sort_col = lis[col_num]

    if order_term == 'asc':
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
    else:
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)




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
           stock_dict = {'location_id': location_id[0].id, 'receipt_number': 0, 'receipt_date': datetime.datetime.now(),
                         'sku_id':sku_id[0].id, 'quantity': quantity, 'status': 1, 'creation_date': datetime.datetime.now()}
           stock = StockDetail(**stock_dict)
           stock.save()
           stock_detail.append(stock)
    return stock_detail

def get_picklist_locations(data_dict, user):
    exclude_dict = {'location__lock_status__in': ['Outbound', 'Inbound and Outbound'], 'location__zone__zone__in':['TEMP_ZONE', 'DAMAGED_ZONE']}
    back_order = get_misc_value('back_order', user.id)
    fifo_switch = get_misc_value('fifo_switch', user.id)

    if fifo_switch == 'true':
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0, **data_dict).\
                                                                    order_by('receipt_date', 'location__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0, **data_dict).\
                                                                    order_by('receipt_date', 'location__pick_sequence')
        data_dict['location__zone__zone'] = 'TEMP_ZONE'
        #del exclude_dict['location__zone__zone']
        stock_detail3 = StockDetail.objects.exclude(**exclude_dict).filter(**data_dict).order_by('receipt_date', 'location__pick_sequence')
        stock_detail = list(chain(stock_detail1, stock_detail2, stock_detail3))
    else:
        #del exclude_dict['location__zone__zone']
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0, **data_dict).\
                                                                    order_by('location_id__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0, **data_dict).order_by('receipt_date')
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
    data = []
    stock_status = ''
    out_of_stock = []
    single_order = ''
    picklist_number = get_picklist_number(user)

    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(status=1, user=user.id, quantity__gt=0)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by('receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by('location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    sku_stocks = stock_detail1 | stock_detail2
    for key, value in request.POST.iteritems():
        if key in ('sortingTable_length', 'fifo-switch', 'ship_reference', 'remarks'):
            continue

        order_data = OrderDetail.objects.get(id=key,user=user.id)
        stock_status, picklist_number = picklist_generation([order_data], request, picklist_number, user, sku_combos, sku_stocks, status = 'open', remarks=remarks)

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
    if not stock_status:
        order_status = data[0]['status']
        if order_status == 'open':
            headers.insert(headers.index('WMS Code'),'Order ID')
            order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
            order_count_len = len(filter(lambda x: len(str(x))>0, order_count))
            if order_count_len == 1:
                single_order = str(order_count[0])

    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status, 'show_image': show_image,
                                    'use_imei': use_imei, 'order_status': order_status, 'single_order': single_order}))


def get_picklist_number(user):
    picklist_obj = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id)).values_list('picklist_number',
                                           flat=True).distinct().order_by('-picklist_number')
    if not picklist_obj:
        picklist_number = 1000
    else:
        picklist_number = picklist_obj[0]
    return picklist_number

@fn_timer
def get_sku_stock(request, sku, sku_stocks, user, val_dict, sku_id_stocks=''):
    data_dict = {'sku_id': sku.id, 'quantity__gt': 0}
    stock_detail = sku_stocks.filter(**data_dict)

    stock_count = 0
    if sku.id in val_dict['sku_ids']:
        indices = [i for i, x in enumerate(sku_id_stocks) if x['sku_id'] == sku.id]
        for index in indices:
            stock_count += val_dict['stock_totals'][index]
        if sku.id in val_dict['pic_res_ids']:
            stock_count = stock_count - val_dict['pic_res_quans'][val_dict['pic_res_ids'].index(sku.id)]

    return stock_detail, stock_count, sku.wms_code


def get_stock_count(request, order, stock, stock_diff, user, order_quantity):
    reserved_quantity = PicklistLocation.objects.filter(stock_id=stock.id, status=1, picklist__order__user=user.id).aggregate(Sum('reserved'))['reserved__sum']
    if not reserved_quantity:
        reserved_quantity = 0

    stock_quantity = float(stock.quantity) - reserved_quantity
    if stock_quantity <= 0:
        return '', stock_diff

    if stock_diff:
        if stock_quantity >= stock_diff:
            stock_count = stock_diff
            stock_diff = 0
        else:
            stock_count = stock_quantity
            stock_diff -= stock_quantity
    else:
        if stock_quantity >= order_quantity:
            stock_count = order_quantity
        else:
            stock_count = stock_quantity
            stock_diff = order_quantity - stock_quantity

    return stock_count, stock_diff

def picklist_headers(request, user):
    show_image = 'false'
    use_imei = 'false'
    headers = list(PROCESSING_HEADER)

    data1 = MiscDetail.objects.filter(user=user, misc_type='show_image')
    if data1:
        show_image = data1[0].misc_value
    if show_image == 'true':
        headers.insert(0, 'Image')

    imei_data = MiscDetail.objects.filter(user=user, misc_type='use_imei')
    if imei_data:
        use_imei = imei_data[0].misc_value
    if use_imei == 'true':
        headers.insert(-1, 'Serial Number')

    if get_misc_value('pallet_switch', user) == 'true':
        headers.insert(headers.index('Location') + 1, 'Pallet Code')

    return headers, show_image, use_imei

@fn_timer
def picklist_generation(order_data, request, picklist_number, user, sku_combos, sku_stocks, status='', remarks=''):
    stock_status = []
    if not status:
        status = 'batch_open'
    for order in order_data:
        picklist_data = copy.deepcopy(PICKLIST_FIELDS)
        picklist_data['picklist_number'] = picklist_number + 1
        if remarks:
            picklist_data['remarks'] = remarks
        else:
            picklist_data['remarks'] = 'Picklist_' + str(picklist_number + 1)

        sku_id_stocks = sku_stocks.values('id', 'sku_id').annotate(total=Sum('quantity'))
        pick_res_locat = PicklistLocation.objects.prefetch_related('picklist', 'stock').filter(status=1).\
                                          filter(picklist__order__user=user.id).values('stock__sku_id').annotate(total=Sum('reserved'))
        val_dict = {}
        val_dict['pic_res_ids'] = map(lambda d: d['stock__sku_id'], pick_res_locat)
        val_dict['pic_res_quans'] = map(lambda d: d['total'], pick_res_locat)

        val_dict['sku_ids'] = map(lambda d: d['sku_id'], sku_id_stocks)
        val_dict['stock_ids'] = map(lambda d: d['id'], sku_id_stocks)
        val_dict['stock_totals'] = map(lambda d: d['total'], sku_id_stocks)


        members = [ order.sku ]
        if order.sku.relation_type == 'combo':
            picklist_data['order_type'] = 'combo'
            members = []
            combo_data = sku_combos.filter(parent_sku_id=order.sku.id)
            for combo in combo_data:
                members.append(combo.member_sku)

        for member in members:
            stock_detail, stock_quantity, sku_code = get_sku_stock(request, member, sku_stocks, user, val_dict, sku_id_stocks)
            if order.sku.relation_type=='member':
                parent = sku_combos.filter(member_sku_id=member.id).filter(relation_type='member')
                stock_detail1, stock_quantity1, sku_code = get_sku_stock(request, parent[0].parent_sku, sku_stocks, user, val_dict, sku_id_stocks)
                stock_detail = list(chain(stock_detail, stock_detail1))
                stock_quantity += stock_quantity1
            elif order.sku.relation_type=='combo':
                stock_detail, stock_quantity, sku_code = get_sku_stock(request, member, sku_stocks, user, val_dict, sku_id_stocks)

            order_quantity = float(order.quantity)
            if stock_quantity < float(order.quantity):
                if get_misc_value('no_stock_switch', user.id) == 'false':
                    stock_status.append(str(member.sku_code))
                    continue

                order_diff = order_quantity - stock_quantity
                order_quantity -= order_diff
                #stock_detail = []
                #stock_detail = create_temp_stock(member.sku_code, 'DEFAULT', int(order.quantity) - stock_quantity, stock_detail, user.id)
                picklist_data['reserved_quantity'] = order_diff
                picklist_data['stock_id'] =  ''
                picklist_data['order_id'] = order.id
                picklist_data['status'] = status
                if sku_code:
                    picklist_data['sku_code'] = sku_code
                if 'st_po' not in dir(order):
                    new_picklist = Picklist(**picklist_data)
                    new_picklist.save()

                    order.status = 0
                    order.save()
                if stock_quantity <= 0:
                    continue

            stock_diff = 0

            for stock in stock_detail:
                stock_count, stock_diff = get_stock_count(request, order, stock, stock_diff, user, order_quantity)
                if not stock_count:
                    continue

                picklist_data['reserved_quantity'] = stock_count
                picklist_data['stock_id'] = stock.id
                if 'st_po' in dir(order):
                    picklist_data['order_id'] = None
                else:
                    picklist_data['order_id'] = order.id
                picklist_data['status'] = status

                new_picklist = Picklist(**picklist_data)
                new_picklist.save()

                picklist_loc_data = {'picklist_id': new_picklist.id , 'status': 1, 'quantity': stock_count, 'creation_date':   datetime.datetime.now(),
                                     'stock_id': new_picklist.stock_id, 'reserved': stock_count}
                po_loc = PicklistLocation(**picklist_loc_data)
                po_loc.save()
                if 'st_po' in dir(order):
                    st_order_dict = copy.deepcopy(ST_ORDER_FIELDS)
                    st_order_dict['picklist_id'] = new_picklist.id
                    st_order_dict['stock_transfer_id'] = order.id
                    st_order = STOrder(**st_order_dict)
                    st_order.save()

                if not stock_diff:
                    setattr(order, 'status', 0)
                    break

            order.save()
    return stock_status, picklist_number


@csrf_exempt
@login_required
@get_admin_user
def batch_generate_picklist(request, user=''):
    remarks = request.POST.get('remarks', '')

    data = []
    order_data = []
    stock_status = ''
    out_of_stock = []
    picklist_number = get_picklist_number(user)

    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(status=1, user=user.id, quantity__gt=0)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by('receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by('location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    sku_stocks = stock_detail1 | stock_detail2
    for key, value in request.POST.iteritems():
        if key in PICKLIST_SKIP_LIST:
            continue

        key = key.split('<>')
        sku_code, marketplace_sku_code = key
        order_filter = {'sku__sku_code': sku_code, 'quantity__gt': 0 }

        if sku_code != marketplace_sku_code:
            order_filter['sku_code'] = marketplace_sku_code

        if request.POST.get('selected'):
            order_filter['marketplace__in'] = request.POST.get('selected').split(',')

        order_detail = all_orders.filter(**order_filter).order_by('shipment_date')

        stock_status, picklist_number = picklist_generation(order_detail, request, picklist_number, user, sku_combos, sku_stocks, remarks=remarks)

        if stock_status:
            out_of_stock = out_of_stock + stock_status

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    headers, show_image, use_imei = picklist_headers(request, user.id)

    order_status = ''
    data, sku_total_quantities = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']
        if order_status == 'open':
            headers.insert(headers.index('WMS Code'),'Order ID')

    return HttpResponse(json.dumps({'data': data, 'headers': headers,
                           'picklist_id': picklist_number + 1,'stock_status': stock_status, 'show_image': show_image,
                           'use_imei': use_imei, 'order_status': order_status, 'user': request.user.id}))


def get_picklist_data(data_id,user_id):

    sku_total_quantities = {}
    picklist_orders = Picklist.objects.filter(Q(order__sku__user=user_id) | Q(stock__sku__user=user_id), picklist_number=data_id)
    pick_stocks = StockDetail.objects.filter(sku__user=user_id)
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
            if order.stock:
                stock_id = pick_stocks.get(id=order.stock_id)
            if order.order:
                sku_code = order.order.sku_code
                title = order.order.title
                invoice = order.order.invoice_amount
            else:
                st_order = STOrder.objects.filter(picklist_id=order.id)
                sku_code = ''
                title = st_order[0].stock_transfer.sku.sku_desc
                invoice = st_order[0].stock_transfer.invoice_amount

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

            match_condition = (location, pallet_detail, wms_code, sku_code, title)
            if match_condition not in batch_data:
                if order.reserved_quantity == 0:
                    continue

                batch_data[match_condition] = {'wms_code': wms_code, 'zone': zone, 'sequence': sequence, 'location': location, 'reserved_quantity': order.reserved_quantity, 'picklist_number': data_id, 'stock_id': st_id, 'picked_quantity': order.reserved_quantity, 'id': order.id, 'invoice_amount': invoice, 'price': invoice * order.reserved_quantity, 'image': image, 'order_id': order.order_id, 'status': order.status, 'pallet_code': pallet_code, 'sku_code': sku_code, 'title': title}
            else:
                batch_data[match_condition]['reserved_quantity'] += order.reserved_quantity
                batch_data[match_condition]['picked_quantity'] += order.reserved_quantity
                batch_data[match_condition]['invoice_amount'] += invoice
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
            if order.order:
                wms_code = order.order.sku.wms_code
                if order.order_type == 'combo' and order.sku_code:
                    wms_code = order.sku_code
                invoice_amount = order.order.invoice_amount
                order_id = order.order.order_id
                sku_code = order.order.sku_code
                title = order.order.title
            else:
                wms_code = order.stock.sku.wms_code
                invoice_amount = 0
                order_id = ''
                sku_code = order.stock.sku.sku_code
                title = order.stock.sku.sku_desc
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

            data.append({'wms_code': wms_code, 'zone': zone, 'location': location, 'reserved_quantity': order.reserved_quantity, 'picklist_number': data_id, 'stock_id': st_id, 'order_id': order.order_id, 'picked_quantity': order.reserved_quantity, 'id': order.id, 'sequence': sequence, 'invoice_amount': invoice_amount, 'price': invoice_amount * order.reserved_quantity, 'image': image, 'status': order.status, 'order_no': order_id,'pallet_code': pallet_code, 'sku_code': sku_code, 'title': title})

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
            if order.stock_id:
                stock_id = pick_stocks.get(id=order.stock_id)

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

            if order.reserved_quantity == 0:
                continue

            data.append({'wms_code': wms_code, 'zone': zone, 'location': location, 'reserved_quantity': order.reserved_quantity, 'picklist_number': data_id, 'order_id': order.order_id, 'stock_id': st_id, 'picked_quantity':order.reserved_quantity, 'id': order.id, 'sequence': sequence, 'invoice_amount': order.order.invoice_amount, 'price': order.order.invoice_amount * order.reserved_quantity, 'image': image, 'status': order.status, 'pallet_code': pallet_code, 'sku_code': order.order.sku_code, 'title': order.order.title })

            if wms_code in sku_total_quantities.keys():
                sku_total_quantities[wms_code] += float(order.reserved_quantity)
            else:
                sku_total_quantities[wms_code] = float(order.reserved_quantity)
        data = sorted(data, key=itemgetter('sequence'))
        return data, sku_total_quantities


def confirm_no_stock(picklist, request, user, p_quantity=0):
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
    if float(picklist.reserved_quantity) <= 0:
        picklist.status = pi_status
        if picklist.order:
            misc_detail = MiscDetail.objects.filter(user=picklist.order.user, misc_type='dispatch', misc_value='true')

            if misc_detail:
                send_picklist_mail(picklist, request)
                if picklist.picked_quantity > 0 and picklist.order.telephone:
                    order_dispatch_message(picklist.order, user)
                else:
                    log.info("No telephone no for this order")
    picklist.save()

def validate_location_stock(val, all_locations, all_skus, user):
    status = []
    wms_check = all_skus.filter(wms_code = val['wms_code'],user=user.id)
    loc_check = all_locations.filter(location = val['location'],zone__user=user.id )
    if not loc_check:
        status.append("Invalid Location %s" % val['location'])
    pic_check_data = {'sku_id': wms_check[0].id, 'location_id': loc_check[0].id, 'sku__user': user.id, 'quantity__gt': 0}
    if 'pallet' in val and val['pallet']:
        pic_check_data['pallet_detail__pallet_code'] = val['pallet']
    pic_check = StockDetail.objects.filter(**pic_check_data)
    if not pic_check:
        status.append("Insufficient Stock in given location")
    location = all_locations.filter(location=val['location'],zone__user=user.id)
    if not location:
        if error_string:
            error_string += ', %s' % val['order_id']
        else:
            error_string += "Zone, location match doesn't exists"
        status.append(error_string)
    return pic_check_data, ', '.join(status)

def insert_order_serial(picklist, val):
    imei_nos = list(set(val['imei'].split('\r\n')))
    for imei in imei_nos:
        po_mapping = POIMEIMapping.objects.filter(purchase_order__open_po__sku__sku_code=val['wms_code'], imei_number=imei)
        if imei and po_mapping:
            order_mapping = {'order_id': picklist.order.id, 'po_imei_id': po_mapping[0].id, 'imei_number': ''}
            imei_mapping = OrderIMEIMapping(**order_mapping)
            imei_mapping.save()
        elif imei and not po_mapping:
            order_mapping = {'order_id': picklist.order.id, 'po_imei_id': None, 'imei_number': imei}
            imei_mapping = OrderIMEIMapping(**order_mapping)
            imei_mapping.save()

def update_picklist_locations(pick_loc, picklist, update_picked, update_quantity=''):
    for pic_loc in pick_loc:
        if float(pic_loc.reserved) >= update_picked:
            pic_loc.reserved = float(pic_loc.reserved) - update_picked
            if update_quantity:
                pic_loc.quantity = float(pic_loc.quantity) - update_picked
            update_picked = 0
        elif float(pic_loc.reserved) < update_picked:
            update_picked = update_picked - pic_loc.reserved
            if update_quantity:
                pic_loc.quantity = 0
            pic_loc.reserved = 0
        if pic_loc.reserved <= 0:
            pic_loc.status = 0
        pic_loc.save()
        if not update_picked:
            break

def update_picklist_pallet(stock, picking_count1):
    pallet = stock.pallet_detail
    if float(pallet.quantity) - picking_count1 >=0:
        pallet.quantity -= picking_count1
    if pallet.quantity == 0:
        stock.pallet_detail_id = None
        pallet.status = 0
        stock.location.pallet_filled -= 1
        if stock.location.pallet_filled < 0:
            stock.location.pallet_filled = 0
        stock.location.save()
        pallet_mapping = PalletMapping.objects.filter(pallet_detail_id = pallet.id)
        if pallet_mapping:
            pallet_mapping[0].status=1
            pallet_mapping[0].save()
    pallet.save()

def send_picklist_mail(picklist, request):
    headers = ['Product Details', 'Seller Details', 'Ordered Quantity', 'Total']
    items = [picklist.order.sku.sku_desc, request.user.username, picklist.order.quantity, picklist.order.invoice_amount]

    data_dict = {'customer_name': picklist.order.customer_name, 'order_id': picklist.order.order_id,
                 'address': picklist.order.address, 'phone_number': picklist.order.telephone, 'items': items,
                 'headers': headers}

    t = loader.get_template('templates/dispatch_mail.html')
    c = Context(data_dict)
    rendered = t.render(c)

    email = picklist.order.email_id
    if email:
        try:
            send_mail([email], 'Order %s on %s is ready to be shipped by the seller' % (picklist.order.order_id, request.user.username), rendered)
        except:
            print 'mail issue'

def get_picklist_batch(picklist, value, all_picklists):
    if picklist.order and picklist.stock:
        picklist_batch = all_picklists.filter(stock__location__location=value[0]['orig_loc'], stock__sku__wms_code=value[0]['wms_code'],
                                              status__icontains='open', order__title=value[0]['title'])
    elif not picklist.stock:
        picklist_batch = all_picklists.filter(order__sku__sku_code=value[0]['wms_code'], order__title=value[0]['title'], stock__isnull=True,
                                              picklist_number=picklist.picklist_number)
        if not picklist_batch:
            picklist_batch = all_picklists.filter(sku_code=value[0]['wms_code'], order__title=value[0]['title'], stock__isnull=True,
                                                  picklist_number=picklist.picklist_number)
    else:
        picklist_batch = all_picklists.filter(Q(stock__sku__wms_code=value[0]['wms_code']) | Q(order_type="combo",
                                              sku_code=value[0]['wms_code']), stock__location__location=value[0]['orig_loc'],
                                              status__icontains='open')
    return picklist_batch

@csrf_exempt
@login_required
@get_admin_user
def picklist_confirmation(request, user=''):
    st_time = datetime.datetime.now()
    data = {}
    all_data = {}
    auto_skus = []
    for key, value in request.POST.iterlists():
        name, picklist_id = key.rsplit('_', 1)
        data.setdefault(picklist_id, [])
        for index, val in enumerate(value):
            if len(data[picklist_id]) < index + 1:
                data[picklist_id].append({})
            data[picklist_id][index][name] = val

    data = OrderedDict(sorted(data.items(), reverse=True))
    error_string = ''
    picklist_number = request.POST['picklist_number']
    single_order = request.POST.get('single_order', '')
    all_picklists = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id), picklist_number=picklist_number,
                                            status__icontains="open")
    picks_all = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id), picklist_number=picklist_number)
    all_skus = SKUMaster.objects.filter(user=user.id)
    all_locations = LocationMaster.objects.filter(zone__user=user.id)
    all_pick_ids = all_picklists.values_list('id', flat=True)
    all_pick_locations = PicklistLocation.objects.filter(picklist__picklist_number=picklist_number, status=1, picklist_id__in=all_pick_ids)

    for key, value in data.iteritems():
        if key in ('name', 'number', 'order', 'sku'):
            continue
        picklist_batch = ''
        picklist_order_id = value[0]['order_id']
        if picklist_order_id:
            picklist = all_picklists.get(order_id=picklist_order_id)
        elif not key:
            scan_wms_codes = map(lambda d: d['wms_code'], value)
            picklist_batch = picks_all.filter(Q(stock__sku__wms_code__in=scan_wms_codes) | Q(order__sku__wms_code=scan_wms_codes),
                                        reserved_quantity__gt=0, status__icontains='open')

        else:
            picklist = picks_all.get(id=key)
        count = 0
        if not picklist_batch:
            picklist_batch = get_picklist_batch(picklist, value, all_picklists)
        for i in range(0,len(value)):
            if value[i]['picked_quantity']:
                count += float(value[i]['picked_quantity'])

        for val in value:
            if not val['picked_quantity']:
                continue
            else:
                count = float(val['picked_quantity'])

            if picklist_order_id:
                picklist_batch = [picklist]
            for picklist in picklist_batch:
                if count == 0:
                    continue
                if not picklist.stock:
                    confirm_no_stock(picklist, request, user, float(val['picked_quantity']))
                    continue

                if val['wms_code'] == 'TEMP' and val.get('wmscode', ''):
                    if picklist.order:
                        map_status = create_market_mapping(picklist.order, val)
                    if map_status == 'true':
                        val['wms_code'] = val['wmscode']
                    elif map_status == 'Invalid WMS Code':
                        return HttpResponse(map_status)
                pic_check_data, status = validate_location_stock(val, all_locations, all_skus, user)
                if status:
                    continue
                if float(picklist.reserved_quantity) > float(val['picked_quantity']):
                    picking_count = float(val['picked_quantity'])
                else:
                    picking_count = float(picklist.reserved_quantity)
                picking_count1 = picking_count
                wms_id = all_skus.exclude(sku_code='').get(wms_code=val['wms_code'],user=user.id)
                total_stock = StockDetail.objects.filter(**pic_check_data)

                if 'imei' in val.keys() and val['imei'] and picklist.order:
                    insert_order_serial(picklist, val)
                reserved_quantity1 = picklist.reserved_quantity
                tot_quan = 0
                for stock in total_stock:
                    tot_quan += float(stock.quantity)
                if tot_quan < reserved_quantity1:
                    total_stock = create_temp_stock(picklist.stock.sku.sku_code, picklist.stock.location.zone, abs(reserved_quantity1 - tot_quan), list(total_stock), user.id)

                for stock in total_stock:

                    pre_stock = float(stock.quantity)
                    if picking_count == 0:
                        break

                    if picking_count > stock.quantity:
                        picking_count -= stock.quantity
                        picklist.reserved_quantity -= stock.quantity

                        stock.quantity = 0
                    else:
                        stock.quantity -= picking_count
                        picklist.reserved_quantity -= picking_count

                        if float(stock.location.filled_capacity) - picking_count >= 0:
                            setattr(stock.location,'filled_capacity',(float(stock.location.filled_capacity) - picking_count))
                            stock.location.save()

                        pick_loc = all_pick_locations.filter(picklist_id=picklist.id,stock__location_id=stock.location_id,status=1)
                        update_picked = picking_count1
                        if pick_loc:
                            update_picklist_locations(pick_loc, picklist, update_picked)
                        else:
                            data = PicklistLocation(picklist_id=picklist.id, stock=stock, quantity=picking_count1, reserved=0, status = 0,
                                                    creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now())
                            data.save()
                            exist_pics = all_pick_locations.exclude(id=data.id).filter(picklist_id=picklist.id, status=1, reserved__gt=0)
                            update_picklist_locations(exist_pics, picklist, update_picked, 'true')
                        picking_count = 0
                    if stock.location.zone.zone == 'BAY_AREA':
                        reduce_putaway_stock(stock, picking_count1, user.id)
                    dec_quantity = pre_stock - float(stock.quantity)
                    if stock.pallet_detail:
                        update_picklist_pallet(stock, picking_count1)
                    stock.save()
                picklist.picked_quantity = float(picklist.picked_quantity) + picking_count1
                if picklist.reserved_quantity == 0:
                    if picklist.status == 'batch_open':
                        picklist.status = 'batch_picked'
                    else:
                        picklist.status = 'picked'

                    if picklist.order:
                        check_and_update_order(user.id, picklist.order.original_order_id)
                    all_pick_locations.filter(picklist_id=picklist.id, status=1).update(status=0)

                    misc_detail = MiscDetail.objects.filter(user=request.user.id, misc_type='dispatch', misc_value='true')

                    if misc_detail and picklist.order:
                        send_picklist_mail(picklist, request)
                        if picklist.picked_quantity > 0 and picklist.order.telephone:
                            order_dispatch_message(picklist.order, user)
                        else:
                            log.info("No telephone no for this order")


                picklist.save()
                count = count - picking_count1
                auto_skus.append(val['wms_code'])

    if get_misc_value('auto_po_switch', user.id) == 'true' and auto_skus:
        auto_po(list(set(auto_skus)), user.id)

    if get_misc_value('automate_invoice', user.id) == 'true' and single_order:
        order_ids = picks_all.filter(order__order_id=single_order, picked_quantity__gt=0).values_list('order_id', flat=True)
        if order_ids:
            order_ids = [str(int(i)) for i in order_ids]
            order_ids = ','.join(order_ids)
            invoice_data = get_invoice_data(order_ids, user)
            #invoice_data['invoice_no'] = 'TI/1116/' + invoice_data['order_no']
            #invoice_data['invoice_date'] = get_local_date(user, datetime.datetime.now())
            return HttpResponse(json.dumps({'data': invoice_data, 'status': 'invoice'}))

    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("process completed")
    log.info("total time -- %s" %(duration))
    return HttpResponse('Picklist Confirmed')

@csrf_exempt
@login_required
@get_admin_user
def view_picklist(request, user=''):
    show_image = 'false'
    use_imei = 'false'
    data_id = request.GET['data_id']
    single_order = ''
    headers = list(PICKLIST_HEADER1)
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
        headers.insert(headers.index('WMS Code'),'Order ID')
        order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
        order_count_len = len(filter(lambda x: len(str(x))>0, order_count))
        if order_count_len == 1:
            single_order = str(order_count[0])

    return HttpResponse(json.dumps({'data': data, 'picklist_id': data_id,
                                    'show_image': show_image, 'use_imei': use_imei,
                                    'order_status': data[0]['status'], 'user': request.user.id, 'single_order': single_order,
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
    return HttpResponse(json.dumps({'data': data, 'picklist_id': data_id, 'show_image': show_image}))

def get_picked_data(data_id, user, marketplace=''):
    pick_filter = {'picklist_number': data_id, 'picked_quantity__gt': 0}
    if marketplace:
        pick_filter['order__marketplace'] = marketplace

    picklist_orders = Picklist.objects.filter(Q(order__sku__user=user) | Q(stock__sku__user=user), **pick_filter)
    data = []
    for order in picklist_orders:
        if not order.stock:
            wms_code = order.order.sku.wms_code
            if order.order_type == 'combo' and order.sku_code:
                wms_code = order.sku_code
            data.append({'wms_code': wms_code, 'zone': 'NO STOCK', 'location': 'NO STOCK', 'reserved_quantity': order.reserved_quantity, 'picked_quantity': order.picked_quantity, 'stock_id': 0, 'picklist_number': data_id, 'id': order.id, 'order_id': order.order.order_id, 'image': '', 'title': order.order.title, 'order_detail_id': order.order_id, 'image': order.order.sku.image_url})
            continue

        picklist_location = PicklistLocation.objects.filter(Q(picklist__order__sku__user=user) | Q(stock__sku__user=user), picklist_id=order.id)
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
                data.append({'wms_code': wms_code, 'zone': stock_detail.location.zone.zone, 'location': stock_detail.location.location, 'reserved_quantity': loc.reserved, 'picked_quantity':loc_quantity, 'stock_id': loc.stock_id, 'picklist_number': data_id, 'id': order.id, 'order_id': order_id, 'image': order.stock.sku.image_url, 'title': title, 'order_detail_id': order.order_id})
    return data

@csrf_exempt
@get_admin_user
def get_customer_sku(request, user=''):
    temp1 = []
    order_shipments = []
    all_data = {}
    data = []
    sku_grouping = request.GET.get('sku_grouping', 'false')
    search_params = {'user': user.id}
    headers = ('', 'SKU Code', 'Order Quantity', 'Shipping Quantity', 'Pack Reference', '')
    #c_id = request.GET['customer_id']
    #marketplace = request.GET['marketplace']
    #if c_id:
    #    c_id = c_id.split(':')
    #    search_params['customer_id'] = c_id[0]
    #    search_params['customer_name'] = c_id[1]
    #if marketplace:
    #    search_params['marketplace'] = marketplace.replace('Default','')

    request_data = dict(request.GET.iterlists())
    if 'order_id' in request_data.keys():
        search_params['id__in'] = request_data['order_id']
    ship_no = get_shipment_number(user)
    data_dict = copy.deepcopy(ORDER_SHIPMENT_DATA)
    data_dict['shipment_number'] = ship_no
    order_shipment = OrderShipment.objects.filter(shipment_number = ship_no)
    all_orders = OrderDetail.objects.filter(**search_params)
    customer_dict = all_orders.values('customer_id', 'customer_name').distinct()
    filter_list = ['sku__sku_code', 'id', 'order_id']
    if sku_grouping == 'true':
        filter_list = ['sku__sku_code']

    for customer in customer_dict:
        customer_picklists = Picklist.objects.filter(order__customer_id=customer['customer_id'], order__customer_name=customer['customer_name'],
                                                     status__icontains='picked',
                                                     order__user=user.id)
        picklist_order_ids = list(customer_picklists.values_list('order_id', flat=True))
        customer_orders = all_orders.filter(id__in=picklist_order_ids)

        all_data = list(customer_orders.values(*filter_list).distinct().annotate(picked=Sum('quantity')))

        for ind,dat in enumerate(all_data):
            if sku_grouping == 'true':
                ship_dict = {'order__sku__sku_code': dat['sku__sku_code'], 'order__sku__user': user.id,
                             'order__customer_id': customer['customer_id'], 'order__customer_name': customer['customer_name']}
                all_data[ind]['id'] = list(customer_picklists.filter(**ship_dict).values_list('order_id', flat=True).distinct())
            else:
                ship_dict = {'order_id': dat['id']}
            shipped = ShipmentInfo.objects.filter(**ship_dict).aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
            if shipped:
                all_data[ind]['picked'] = float(dat['picked']) - shipped
                if all_data[ind]['picked'] < 0:
                    del all_data[ind]

        data = list(chain(data, all_data))
        '''if not order_shipment and all_data:
            for key, value in request.GET.iteritems():
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
            order_shipment = [data]
            order_shipments.append(data)'''
    if data:
        #order_data = all_data
        #display_fields = ['Customer ID', 'Customer Name']
        #if not c_id:
        #    display_fields = ['Market Place']
        #    customer_dict = {'marketplace': marketplace}
        return HttpResponse(json.dumps({'data': data,
                                  'shipment_id': '',#order_shipment[0].id,
                                  'display_fields': '',
                                  'marketplace': '', 'shipment_number': ship_no}))
    return HttpResponse(json.dumps({'status': 'No Orders found'}))

@login_required
@get_admin_user
def check_imei(request, user=''):
    status = ''
    for key, value in request.GET.iteritems():
        picklist = Picklist.objects.get(id=key)
        if not picklist.order:
            continue
        po_mapping = POIMEIMapping.objects.filter(imei_number=value, purchase_order__open_po__sku__user=user.id, purchase_order__open_po__sku__sku_code=picklist.order.sku.sku_code)
        if not po_mapping:
            status = str(value) + ' is invalid for this sku'
        order_mapping = OrderIMEIMapping.objects.filter(po_imei__imei_number=value, order__user=user.id)
        if order_mapping:
            status = str(value) + ' is already mapped with another order'

    return HttpResponse(status)

@get_admin_user
def print_picklist_excel(request, user=''):
    headers = copy.deepcopy(PICKLIST_EXCEL)
    data_id = request.GET['data_id']
    data, sku_total_quantities = get_picklist_data(data_id, user.id)
    all_data = []
    for dat in data:
        val = itemgetter(*headers.values())(dat)
        temp = OrderedDict(zip(headers.keys(),val))
        all_data.append(temp)
    path = print_excel(request, {'aaData': all_data}, headers.keys(), str(data_id))
    return HttpResponse(path)

@get_admin_user
def print_picklist(request, user=''):
    temp = []
    title = 'Picklist ID'
    data_id = request.GET['data_id']
    data, sku_total_quantities = get_picklist_data(data_id, user.id)
    all_data = {}
    total = 0
    total_price = 0
    type_mapping = SkuTypeMapping.objects.filter(user=user.id)
    for record in data:
        for mapping in type_mapping:
            if mapping.prefix in record['wms_code']:
                cond = (mapping.item_type)
                all_data.setdefault(cond, [0,0])
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

    for key,value in all_data.iteritems():
        total += float(value[0])
        total_price += float(value[1])

    return render(request, 'templates/toggle/print_picklist.html', {'data': data, 'all_data': all_data, 'headers': PRINT_PICKLIST_HEADERS,
                                                                    'picklist_id': data_id,'total_quantity': total, 'total_price': total_price})
@csrf_exempt
def get_batch_picked(data_ids, user_id):
    data = {}
    batch_data = {}
    for data_id in data_ids:
        picklist_orders = Picklist.objects.filter(Q(stock__sku__user=user_id) | Q(order__user=user_id), picklist_number=data_id)
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

                batch_data[match_condition] = {'wms_code': wms_code, 'picked_quantity':order.picked_quantity,
                                               'invoice_amount': invoice_amount }
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
    return render(request, 'templates/toggle/print_segregation.html', {'data': data, 'picklist_number': data_id, 'headers': ('WMS Code', 'Picked Quantity', 'invoice_amount')})

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
            stock_data = StockDetail.objects.filter(sku__user=w_user.id, sku__sku_code=order.sku.sku_code).aggregate(Sum('quantity'))
            order_data = OrderDetail.objects.filter(user=w_user.id, sku__sku_code=order.sku.sku_code, status=1).aggregate(Sum('quantity'))
            reserved = PicklistLocation.objects.filter(picklist__status__icontains='open', picklist__order__user=w_user.id, picklist__order__sku__sku_code=order.sku.sku_code).aggregate(Sum('reserved'))
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
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(status=1, user=user.id, quantity__gt=0)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by('receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by('location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    sku_stocks = stock_detail1 | stock_detail2
    for key, value in request.POST.iteritems():
        order_data = StockTransfer.objects.filter(id=value)
        stock_status, picklist_number = picklist_generation(order_data, request, picklist_number, user, sku_combos, sku_stocks)

        if stock_status:
            out_of_stock = out_of_stock + stock_status

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    headers, show_image, use_imei = picklist_headers(request, user.id)

    order_status = ''
    data, sku_total_quantities = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']
        if order_status == 'open':
            headers.insert(headers.index('WMS Code'),'Order ID')

    return HttpResponse(json.dumps({'data': data, 'headers': headers,
                           'picklist_id': picklist_number + 1,'stock_status': stock_status, 'show_image': show_image,
                           'use_imei': use_imei, 'order_status': order_status }))

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
        return HttpResponse(json.dumps({'name': data.name , 'phone_number': data.phone_number, 'email_id': data.email_id,
                                        'address': data.address}))
    else:
        return HttpResponse('')

def validate_order_form(myDict, request, user):
    invalid_skus = []
    invalid_quantities = []
    status = ''
    if not myDict['shipment_date'][0]:
        status = 'Shipment Date should not be empty'
    for i in range(0, len(myDict['sku_id'])):
        if not myDict['sku_id'][i]:
            continue
        sku_master = SKUMaster.objects.filter(sku_code=myDict['sku_id'][i].upper(), user=user.id)
        if not sku_master:
            sku_master = SKUMaster.objects.filter(wms_code=myDict['sku_id'][i].upper(), user=user.id)
            if not sku_master:
                invalid_skus.append(myDict['sku_id'][i])
        try:
            value = float(myDict['quantity'][i])
        except:
            if myDict['sku_id'][i]:
                invalid_quantities.append(myDict['sku_id'][i])
    if invalid_skus:
        status = " Invalid sku codes are " + ",".join(invalid_skus)
    if invalid_quantities:
        status += " Quantities missing sku codes are " + ",".join(invalid_quantities)
    return status

def create_order_json(order_detail, json_dat={}):
    sku_fields = SKUFields.objects.filter(sku_id=order_detail.sku_id, field_type='product_attribute')
    json_data = []
    for sku_field in sku_fields:
        product_attributes = ProductAttributes.objects.filter(id=sku_field.field_id)
        for product_attribute in product_attributes:
            json_data.append({'attribute_name': product_attribute.attribute_name, 'attribute_value': sku_field.field_value})
    if json_data:
        OrderJson.objects.create(order_id=order_detail.id, json_data=json.dumps(json_data), creation_date=datetime.datetime.now())

@csrf_exempt
@login_required
@get_admin_user
def insert_order_data(request, user=''):
    myDict = dict(request.GET.iterlists())
    order_id = get_order_id(user.id)

    invalid_skus = []
    items = []
    valid_status = validate_order_form(myDict, request, user)
    payment_mode = request.GET.get('payment_mode', '')
    payment_received = request.GET.get('payment_received', '')
    tax_percent = request.GET.get('tax', '')
    telephone = request.GET.get('telephone', '')
    custom_order = request.GET.get('custom_order', '')
    user_type = request.GET.get('user_type', '')
    created_order_id = ''
    if valid_status:
        return HttpResponse(valid_status)

    for i in range(0, len(myDict['sku_id'])):
        order_data = copy.deepcopy(UPLOAD_ORDER_DATA)
        order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
        order_data['order_id'] = order_id
        order_data['order_code'] = 'MN'
        order_data['marketplace'] = 'Offline'
        if custom_order == 'true':
            order_data['order_code'] = 'CO'
        order_data['user'] = user.id

        for key, value in request.GET.iteritems():
            if key in ['payment_received', 'charge_name', 'charge_amount', 'custom_order', 'user_type']:
                continue
            if key == 'sku_id':
                if not myDict[key][i]:
                    continue
                sku_master = SKUMaster.objects.filter(sku_code=myDict[key][i].upper(), user=user.id)
                if not sku_master:
                    sku_master = SKUMaster.objects.filter(wms_code=myDict[key][i].upper(), user=user.id)

                if not sku_master:
                    invalid_skus.append(myDict[key][i])
                    continue

                order_data['sku_id'] = sku_master[0].id
                order_data['title'] = sku_master[0].sku_desc
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
            elif key == 'invoice_amount':
                try:
                    value = float(myDict[key][i])
                except:
                    value = 0
                order_data[key] = value
            elif key == 'customer_id':
                if not value:
                    value = 0
                order_data[key] = value
            elif key == 'tax':
                try:
                    invoice = float(myDict['invoice_amount'][i])
                except:
                    invoice = 0
                if invoice and value:
                    amount = float(invoice)
                    tax_value = (amount/100) * float(value)
                    vat = value
                    order_summary_dict['issue_type'] = 'order'
                    order_summary_dict['vat'] = vat
                    order_summary_dict['tax_value'] = "%.2f" % tax_value
            elif key == 'order_taken_by':
                order_summary_dict['order_taken_by'] = value
            elif key == 'tax_type':
                order_summary_dict['tax_type'] = value
            else:
                order_data[key] = value

        if not order_data['sku_id'] or invalid_skus or not order_data['quantity']:
            continue

        order_obj = OrderDetail.objects.filter(order_id=order_data['order_id'], user=user.id, sku_id=order_data['sku_id'], order_code=order_data['order_code'])
        if not order_obj:
            if payment_received:
                order_payment = 0
                if float(order_data['invoice_amount']) < float(payment_received):
                    payment_received = float(payment_received) - float(order_data['invoice_amount'])
                    order_payment = float(order_data['invoice_amount'])
                else:
                    payment_received = float(order_data['invoice_amount']) - float(payment_received)
                    order_payment = float(payment_received)
                order_data['payment_received'] = order_payment

            order_data['creation_date'] = datetime.datetime.now()
            order_detail = OrderDetail(**order_data)
            order_detail.save()

            created_order_id = order_detail.order_code + str(order_detail.order_id)
            if order_summary_dict.get('vat', '') or order_summary_dict.get('tax_value', ) or order_summary_dict.get('order_taken_by', '') or \
               order_summary_dict.get('tax_type', ''):
                order_summary_dict['order_id'] = order_detail.id
                order_summary = CustomerOrderSummary(**order_summary_dict)
                order_summary.save()

            if sku_master[0].sku_type == 'CS':
                create_order_json(order_detail)

        items.append([sku_master[0].sku_desc, request.user.username, order_data['quantity'], order_data.get('invoice_amount', 0)])

    if invalid_skus:
        return HttpResponse("Invalid SKU: %s" % ', '.join(invalid_skus))
    if created_order_id and 'charge_name' in myDict.keys():
        for i in range(0, len(myDict['charge_name'])):
            if myDict['charge_name'][i] and myDict['charge_amount'][i]:
                OrderCharges.objects.create(user_id=user.id, order_id=created_order_id, charge_name=myDict['charge_name'][i],
                                            charge_amount=myDict['charge_amount'][i], creation_date=datetime.datetime.now())

    misc_detail = MiscDetail.objects.filter(user=request.user.id, misc_type='order', misc_value='true')
    if misc_detail and order_detail:
        headers = ['Product Details', 'Seller Details', 'Ordered Quantity', 'Total']
        data_dict = {'customer_name': order_data['customer_name'], 'order_id': order_detail.order_id,
                                    'address': order_data['address'], 'phone_number': order_data['telephone'], 'items': items,
                                     'headers': headers}

        t = loader.get_template('templates/order_confirmation.html')
        c = Context(data_dict)
        rendered = t.render(c)

        email = order_data['email_id']
        if email:
            send_mail([email], 'Order Confirmation: %s' % order_detail.order_id, rendered)
        if telephone:
            order_creation_message(items, telephone, (order_detail.order_code) + str(order_detail.order_id))

    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def get_warehouses_list(request, user=''):
    user_list = []
    admin_user = UserGroups.objects.filter(Q(admin_user__username__iexact=user.username) | Q(user__username__iexact=user.username)).\
                 values_list('admin_user_id', flat=True)
    user_groups = UserGroups.objects.filter(admin_user_id__in=admin_user).values('user__username', 'admin_user__username')
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

    for key,value in all_data.iteritems():
        warehouse = User.objects.get(username=key)
        if not value:
            continue
        for val in value:
            sku = SKUMaster.objects.filter(wms_code = val[0], user=warehouse.id)
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
    for key,value in all_data.iteritems():
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

            po_dict = {'order_id': po_id, 'received_quantity': 0, 'saved_quantity': 0, 'po_date': datetime.datetime.now(), 'ship_to': '',
                       'status': '', 'prefix': prefix, 'creation_date': datetime.datetime.now()}
            po_order = PurchaseOrder(**po_dict)
            po_order.save()
            st_purchase_dict = {'po_id': po_order.id, 'open_st_id': open_st.id, 'creation_date': datetime.datetime.now()}
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
    warehouse_name = request.POST.get('warehouse_name','')
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['wms_code'])):
        if not data_dict['wms_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        cond = (user.username)
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['wms_code'][i], data_dict['order_quantity'][i], data_dict['price'][i], data_id ])
    warehouse = User.objects.get(username=warehouse_name)

    status = validate_st(all_data, warehouse)
    if not status:
        all_data = insert_st(all_data, warehouse)
        status = confirm_stock_transfer(all_data, warehouse, user.username)
    return HttpResponse(status)

def get_purchase_order_id(user):
    po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).values_list('order_id', flat=True).order_by("-order_id")
    st_order = STPurchaseOrder.objects.filter(open_st__sku__user=user.id).values_list('po__order_id', flat=True).order_by("-po__order_id")
    rw_order = RWPurchase.objects.filter(rwo__vendor__user=user.id).values_list('purchase_order__order_id', flat=True).\
                                  order_by("-purchase_order__order_id")
    order_ids = list(chain(po_data, st_order, rw_order))
    order_ids = sorted(order_ids,reverse=True)
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
    if status_type == 'picked':
        marketplace = list(Picklist.objects.exclude(order__marketplace='').filter(picked_quantity__gt=0, order__user = user.id).\
                                            values_list('order__marketplace', flat=True).distinct())
    else:
        marketplace = list(OrderDetail.objects.exclude(marketplace='').filter(status=1, user = user.id).values_list('marketplace', flat=True).\
                                               distinct())
    return HttpResponse(json.dumps({'marketplaces': marketplace}))

@csrf_exempt
def get_back_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    is_production = get_misc_value('production_switch', user.id)
    user = user
    order_detail = OrderDetail.objects.filter(user=user.id, status=1, quantity__gt=0).values('sku_id', 'sku__wms_code', 'sku__sku_code', 'title').distinct()
    master_data = []

    stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values('sku_id').distinct().\
                                     annotate(in_stock=Sum('quantity'))
    reserved_objs = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1, reserved__gt=0).values('stock__sku_id').distinct().\
                                                    annotate(reserved=Sum('reserved'))
    order_quantity_objs = OrderDetail.objects.filter(status=1, user=user.id).values('sku_id').distinct().\
                                              annotate(order_quantity=Sum('quantity'))

    purchase_objs = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                           filter(open_po__sku__user=user.id).\
                                           values('open_po__sku_id').annotate(total_order=Sum('open_po__order_quantity'),
                                           total_received=Sum('received_quantity'))

    stocks = map(lambda d: d['sku_id'], stock_objs)
    purchases = map(lambda d: d['open_po__sku_id'], purchase_objs)
    reserveds = map(lambda d: d['stock__sku_id'], reserved_objs)
    order_quantities = map(lambda d: d['sku_id'], order_quantity_objs)

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
            order_quantity = map(lambda d: d['order_quantity'], order_quantity_objs)[order_quantities.index(order['sku_id'])]

        if order['sku_id'] in purchases:
            total_order = map(lambda d: d['total_order'], purchase_objs)[purchases.index(order['sku_id'])]
            total_received = map(lambda d: d['total_received'], purchase_objs)[purchases.index(order['sku_id'])]
            diff_quantity = float(total_order) - float(total_received)
            if diff_quantity > 0:
                transit_quantity = diff_quantity

        if is_production == 'true':
            production_orders = JobOrder.objects.filter(product_code__sku_code=order['sku__sku_code'], product_code__user=user.id).\
                                                   exclude(status__in=['open', 'confirmed-putaway']).values('product_code__sku_code').\
                                                   annotate(total_order=Sum('product_quantity'), total_received=Sum('received_quantity'))
            if production_orders:
                production_order = production_orders[0]
                diff_quantity = float(production_order['total_order']) - float(production_order['total_received'])
                if diff_quantity > 0:
                    production_quantity = diff_quantity
        procured_quantity = order_quantity - stock_quantity - transit_quantity - production_quantity
        if procured_quantity > 0:
            checkbox = "<input type='checkbox' id='back-checked' name='%s'>" % order['title']
            temp  = {'': checkbox, 'WMS Code': order['sku__wms_code'], 'Ordered Quantity': order_quantity,
                                'Stock Quantity': stock_quantity, 'Transit Quantity': transit_quantity,
                                'Procurement Quantity': procured_quantity, 'DT_RowClass': 'results',}
            if is_production == 'true':
                temp['In Production Quantity'] = production_quantity
            master_data.append(temp)
    if search_term:
        master_data = filter(lambda person: search_term in person['WMS Code'] or search_term in str(person['Ordered Quantity']) or\
               search_term in str(person['Stock Quantity']) or search_term in str(person['Transit Quantity']) or \
               search_term in str(person['Procurement Quantity']), master_data)
    elif order_term:
        if order_term == 'asc':
            master_data = sorted(master_data, key = lambda x: x[BACK_ORDER_TABLE[col_num-1]])
        else:
            master_data = sorted(master_data, key = lambda x: x[BACK_ORDER_TABLE[col_num-1]], reverse=True)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    temp_data['aaData'] = master_data[start_index:stop_index]

@csrf_exempt
@get_admin_user
def generate_po_data(request, user=''):
    data_dict = []
    supplier_list = []
    suppliers = SupplierMaster.objects.filter(user=user.id)
    for supplier in suppliers:
        supplier_list.append({'id': supplier.id, 'name': supplier.name})
    for key,value in request.POST.iteritems():
        price = 0
        key = key.split(":")
        selected_item = ''
        sku_supplier = SKUSupplier.objects.filter(sku__wms_code=key[0], sku__user=user.id)
        if sku_supplier:
            selected_item = {'id': sku_supplier[0].supplier_id, 'name': sku_supplier[0].supplier.name}
            price = sku_supplier[0].price
        data_dict.append({'wms_code': key[0], 'title': key[1] , 'quantity': value, 'selected_item': selected_item, 'price': price})
    return HttpResponse(json.dumps({'data_dict': data_dict, 'supplier_list': supplier_list}))


@csrf_exempt
@get_admin_user
def generate_jo_data(request, user=''):
    all_data = []
    title = 'Raise Job Order'
    data = []
    for key, value in request.POST.iteritems():
        key = key.split(':')[0]
        bom_master = BOMMaster.objects.filter(product_sku__sku_code=key, product_sku__user=user.id)
        if bom_master:
            for bom in bom_master:
                data.append({'material_code': bom.material_sku.sku_code, 'material_quantity': float(bom.material_quantity),
                             'id': ''})
        all_data.append({'product_code': key, 'product_description': value,
                         'sub_data': data})
    return HttpResponse(json.dumps({'data': all_data}))

def get_shipment_number(user):
    order_shipment = OrderShipment.objects.filter(user = user.id).order_by('-shipment_number')
    if order_shipment:
        shipment_number = int(order_shipment[0].shipment_number) + 1
    else:
        shipment_number = 1
    return shipment_number

@csrf_exempt
@get_admin_user
def shipment_info(request, user=''):
    shipment_number = get_shipment_number(user)
    market_place = list(Picklist.objects.filter(order__user = user.id, status__icontains='picked').\
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
    myDict = dict(request.POST.iterlists())
    order_shipment = create_shipment(request, user)
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
            data_dict = copy.deepcopy(ORDER_PACKAGING_FIELDS)
            shipment_data = copy.deepcopy(SHIPMENT_INFO_FIELDS)
            order_detail = OrderDetail.objects.get(id=order_id)
            for key, value in myDict.iteritems():
                if key in data_dict:
                    data_dict[key] = value[i]
                if key in shipment_data and key !='id':
                    shipment_data[key] = value[i]

            order_pack_instance = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id,
                                                                package_reference=myDict['package_reference'][i], order_shipment__user=user.id)
            if not order_pack_instance:
                data_dict['order_shipment_id'] = order_shipment.id
                data = OrderPackaging(**data_dict)
                data.save()
            else:
                data = order_pack_instance[0]
            picked_orders = Picklist.objects.filter(order_id=order_id, status__icontains='picked', order__user=user.id)
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
            ship_data = ShipmentInfo(**shipment_data)
            ship_data.save()
            ship_quantity = ShipmentInfo.objects.filter(order_id=order_id).\
                                                 aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
            if ship_quantity >= int(order_detail.quantity):
                order_detail.status = 2
                order_detail.save()
                for pick_order in picked_orders:
                    setattr(pick_order, 'status', 'dispatched')
                    pick_order.save()

    return HttpResponse('Shipment Created Successfully')


@csrf_exempt
@login_required
@get_admin_user
def shipment_info_data(request, user=''):
    headers = ('Order ID', 'SKU Code', 'Shipping Quantity', 'Shipment Reference', 'Pack Reference', 'Status')
    data = []
    customer_id = request.GET['customer_id']
    shipment_number = request.GET['shipment_number']
    ship_reference = ''
    shipment_orders = ShipmentInfo.objects.filter(order__customer_id=customer_id, order_shipment__shipment_number=shipment_number,
                                                  order_shipment__user=user.id)
    for orders in shipment_orders:
        ship_status = copy.deepcopy(SHIPMENT_STATUS)
        status = 'Dispatched'
        tracking = ShipmentTracking.objects.filter(shipment_id=orders.id, shipment__order__user=user.id).order_by('-creation_date').\
                                            values_list('ship_status', flat=True)
        if tracking:
            status = tracking[0]
            if status == 'Delivered':
                continue
        ship_status =  ship_status[ship_status.index(status):]
        data.append({'id': orders.id, 'order_id': orders.order.order_id, 'sku_code': orders.order.sku.sku_code,
                     'ship_quantity': orders.shipping_quantity, 'pack_reference': orders.order_packaging.package_reference,
                     'ship_status': ship_status, 'status': status})
        if not ship_reference:
            ship_reference = orders.order_packaging.order_shipment.shipment_reference

    return HttpResponse(json.dumps({'data': data, 'customer_id': customer_id, 'ship_status': SHIPMENT_STATUS,
                                    'ship_reference': ship_reference}))

@csrf_exempt
@get_admin_user
def update_shipment_status(request, user=''):
    data_dict = dict(request.GET.iterlists())
    ship_reference = request.GET.get('ship_reference', '')
    for i in range(len(data_dict['id'])):
        shipment_info = ShipmentInfo.objects.get(id=data_dict['id'][i])
        tracking = ShipmentTracking.objects.filter(shipment_id=shipment_info.id, shipment__order__user=user.id, ship_status=data_dict['status'][i])
        if not tracking:
            ShipmentTracking.objects.create(shipment_id=shipment_info.id, ship_status=data_dict['status'][i],
                                            creation_date=datetime.datetime.now())

        orig_ship_ref = shipment_info.order_packaging.order_shipment.shipment_reference
        if ship_reference:
            if not ship_reference == orig_ship_ref:
                order_shipment = shipment_info.order_packaging.order_shipment
                order_shipment.shipment_reference = ship_reference
                order_shipment.save()
                
    return HttpResponse("Updated Successfully")

@csrf_exempt
@login_required
@get_admin_user
def print_shipment(request, user=''):
    data_dict = dict(request.GET.iterlists())
    report_data = []
    for i in range(0, len(data_dict['ship_id'])):
        for key, value in request.GET.iteritems():
            ship_id = data_dict[key][i]
            order_shipment1 = OrderShipment.objects.filter(shipment_number=ship_id)
            if order_shipment1:
                order_shipment = order_shipment1[0]
            else:
                return HttpResponse('No Records')
            order_package = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id).order_by('package_reference')
            package_data = []
            all_data = {}
            total = {}
            report_data.append({'shipment_number': ship_id, 'date': datetime.datetime.now(), 'truck_number': order_shipment.truck_number})
            for package in order_package:
                shipment_info = ShipmentInfo.objects.filter(order_packaging_id=package.id)
                for data in shipment_info:
                    cond = data.order.customer_name
                    all_data.setdefault(cond, [])
                    all_data[cond].append({'pack_reference': str(data.order_packaging.package_reference),
                                           'sku_code': str(data.order.sku.sku_code), 'quantity': str(data.shipping_quantity)})


    for key, value in all_data.iteritems():
        total[key] = 0
        for i in value:
            total[key] += float(i['quantity'])

    headers = ('Package Reference', 'SKU Code', 'Shipping Quantity')
    return render(request, 'templates/toggle/shipment_template.html', {'table_headers': headers, 'report_data': report_data,
                                                                       'package_data': all_data, 'total': total})

@csrf_exempt
@login_required
@get_admin_user
def get_sku_categories(request, user=''):
    brands, categories = get_sku_categories_data(request, user)
    stages_list = list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    return HttpResponse(json.dumps({'categories': categories, 'brands': brands, 'stages_list': stages_list}))

def get_style_variants(sku_master, user, customer_id=''):
    stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values('sku_id').distinct().annotate(in_stock=Sum('quantity'))
    purchase_orders = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(open_po__sku__user=user.id).\
                                           values('open_po__sku_id').annotate(total_order=Sum('open_po__order_quantity'),
                                           total_received=Sum('received_quantity'))
    reserved_quantities = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1).values('stock__sku_id').distinct().\
                                       annotate(in_reserved=Sum('reserved'))

    stocks = map(lambda d: d['sku_id'], stock_objs)
    intransit_skus = map(lambda d: d['open_po__sku_id'], purchase_orders)
    intransit_ordered = map(lambda d: d['total_order'], purchase_orders)
    intransit_received = map(lambda d: d['total_received'], purchase_orders)
    reserved_skus = map(lambda d: d['stock__sku_id'], reserved_quantities)
    reserved_quans = map(lambda d: d['in_reserved'], reserved_quantities)
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
        sku_master[ind]['physical_stock'] = stock_quantity
        sku_master[ind]['intransit_quantity'] = intransit_quantity
        if customer_id:
            customer_sku = CustomerSKU.objects.filter(sku__user=user.id, customer_name__customer_id=customer_id, sku__wms_code=sku['wms_code'])
            if customer_sku:
                sku_master[ind]['price'] = customer_sku[0].price
    return sku_master

@csrf_exempt
@login_required
@get_admin_user
def get_sku_catalogs(request, user=''):
    data, start, stop = get_sku_catalogs_data(request, user)
    return HttpResponse(json.dumps({'data': data, 'next_index': str(start + 20) + ':' + str(stop + 20)}))

@csrf_exempt
@login_required
@get_admin_user
def get_sku_variants(request, user=''):
    filter_params = {'user': user.id}
    get_values = ['wms_code', 'sku_desc', 'image_url', 'sku_class', 'price', 'mrp', 'id', 'sku_category', 'sku_brand', 'sku_size', 'style_name']
    sku_class = request.GET.get('sku_class', '')
    customer_id = request.GET.get('customer_id', '')
    sku_code = request.GET.get('sku_code', '')
    is_catalog = request.GET.get('is_catalog', '')
    sale_through = request.GET.get('sale_through', '')
    if sku_class:
        filter_params['sku_class'] = sku_class
    if sku_code:
        filter_params['sku_code'] = sku_code
    if is_catalog:
        filter_params['status'] = 1
    if sale_through:
        filter_params['sale_through__iexact'] = sale_through

    sku_master = list(SKUMaster.objects.filter(**filter_params).values(*get_values).order_by('sequence'))
    sku_master = [ key for key,_ in groupby(sku_master)]

    sku_master = get_style_variants(sku_master, user, customer_id)
        
    return HttpResponse(json.dumps({'data': sku_master}))

@csrf_exempt
@login_required
@get_admin_user
def generate_order_invoice(request, user=''):
    
    order_ids = request.GET.get('order_ids', '')
    invoice_data = get_invoice_data(order_ids, user)

    return HttpResponse(json.dumps(invoice_data))

@csrf_exempt
def get_shipment_picked(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, user_dict={}, filters={}):

    sku_master, sku_master_ids = get_sku_master(user, request.user)
    if user_dict:
        user_dict = eval(user_dict)
    lis = ['id', 'order__order_id', 'order__sku__sku_code', 'order__title', 'order__customer_id', 'order__customer_name',
           'picked_quantity', 'order__marketplace']
    data_dict = {'status__icontains': 'picked', 'order__user': user.id, 'picked_quantity__gt': 0}

    if user_dict.get('market_place', ''):
        marketplace = user_dict['market_place'].split(',')
        data_dict['order__marketplace__in'] = marketplace
    if user_dict.get('customer', ''):
        data_dict['order__customer_id'], data_dict['order__customer_name'] = user_dict['customer'].split(':')

    search_params = get_filtered_params(filters, lis[1:])

    if search_term:
        master_data = Picklist.objects.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids)).\
                                       filter(Q(order__order_id__icontains = search_term) |
                                              Q(order__sku__sku_code__icontains = search_term) |
                                              Q(order__title__icontains = search_term) | Q(order__customer_id__icontains = search_term) |
                                              Q(order__customer_name__icontains = search_term) | Q(picked_quantity__icontains = search_term) |
                                              Q(order__marketplace__icontains = search_term), **data_dict).\
                                       values_list('order_id', flat=True).distinct()

    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = Picklist.objects.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids), **data_dict).\
                                       filter(**search_params).order_by(order_data).\
                                       values_list('order_id', flat=True).distinct()
    else:
        master_data = Picklist.objects.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids), **data_dict).\
                                       filter(**search_params).order_by('updation_date').\
                                       values_list('order_id', flat=True).distinct()

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    count = 0
    for dat in master_data[start_index:stop_index]:
        data = OrderDetail.objects.get(id=dat)
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (dat, data.sku.sku_code)

        temp_data['aaData'].append(OrderedDict(( ('', checkbox), ('Order ID', str(data.order_id)), ('SKU Code', data.sku.sku_code),
                                                 ('Title', data.title),('id', count), ('Customer ID', data.customer_id),
                                                 ('Customer Name', data.customer_name), ('Marketplace', data.marketplace),
                                                 ('Picked Quantity', data.quantity),
                                                 ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': str(data.id)} )) ) )
        count = count+1

@csrf_exempt
@get_admin_user
def generate_order_jo_data(request, user=''):
    all_data = []
    title = 'Raise Job Order'
    data_dict = dict(request.POST.iterlists())
    for i in range(0, len(data_dict['id'])):
        data_id = data_dict['id'][i]
        order_detail = OrderDetail.objects.get(id=data_id, user=user.id)
        data = []
        bom_master = BOMMaster.objects.filter(product_sku__sku_code=order_detail.sku.sku_code, product_sku__user=user.id)
        value = order_detail.quantity
        if bom_master:
            for bom in bom_master:
                data.append({'material_code': bom.material_sku.sku_code, 'material_quantity': float(bom.material_quantity) * float(value),
                             'id': ''})
        all_data.append({'order_id': data_id, 'product_code': order_detail.sku.sku_code, 'product_description': order_detail.quantity,
                         'sub_data': data})
    return HttpResponse(json.dumps({'data': all_data}))

@get_admin_user
def search_customer_data(request, user=''):

    search_key = request.GET.get('q', '')
    total_data = []

    if not search_key:
      return HttpResponse(json.dumps(total_data))

    lis = ['name', 'email_id', 'phone_number', 'address', 'status']
    master_data = CustomerMaster.objects.filter(Q(phone_number__icontains = search_key) | Q(name__icontains = search_key) |
                                                Q(customer_id__icontains = search_key), user=user.id)

    for data in master_data[:30]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        total_data.append({'customer_id': data.customer_id, 'name': data.name, 'phone_number': str(data.phone_number),
                           'email': data.email_id, 'address': data.address})
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
    for i in range(0, len(request_dict['id'])):
        data_id = request_dict['id'][i]
        order_detail = OrderDetail.objects.get(id=data_id, user=user.id)
        price = 0
        selected_item = ''
        sku_supplier = SKUSupplier.objects.filter(sku__wms_code=order_detail.sku.wms_code, sku__user=user.id)
        if sku_supplier:
            selected_item = {'id': sku_supplier[0].supplier_id, 'name': sku_supplier[0].supplier.name}
            price = sku_supplier[0].price
        data_dict.append({'order_id': order_detail.id, 'wms_code': order_detail.sku.wms_code, 'title': order_detail.title ,
                          'quantity': order_detail.quantity, 'selected_item': selected_item, 'price': price})

    return HttpResponse(json.dumps({'data_dict': data_dict, 'supplier_list': supplier_list}))

@csrf_exempt
@get_admin_user
def get_view_order_details(request, user=''):
    data_dict = []
    main_id = request.GET['order_id']
    order_details = OrderDetail.objects.get(id=main_id, user=user.id)
    custom_data = OrderJson.objects.filter(order_id=main_id)
    cus_data = []
    if custom_data:
	attr_list = json.loads(custom_data[0].json_data)
	for attr in attr_list:
	    tuple_data = (attr['attribute_name'],attr['attribute_value'])
	    cus_data.append(tuple_data)
    order_id = order_details.order_id
    order_code = order_details.order_code
    order_id = order_code + str(order_id)
    original_order_id = order_details.original_order_id
    if original_order_id:
        order_id = original_order_id
    customer_id = order_details.customer_id
    customer_name = order_details.customer_name
    shipment_date = get_local_date(request.user, order_details.shipment_date)
    phone = order_details.telephone
    email = order_details.email_id
    address = order_details.address
    city = order_details.city
    state = order_details.state
    pin = order_details.pin_code
    sku_id = order_details.sku_id
    product_title = order_details.title
    quantity = order_details.quantity
    invoice_amount = order_details.invoice_amount
    remarks = order_details.remarks
    sku_code = order_details.sku.sku_code
    sku_type = order_details.sku.sku_type
    field_type = 'product_attribute'
    customization_data = []
    if str(sku_type) == 'CS':
	fields_list = SKUFields.objects.filter(sku_id=sku_id,field_type=field_type)
    	if fields_list:
	    for field in fields_list:
		field_id = field.field_id
		attr_id = field.id
		attr_values = ProductAttributes.objects.filter(id=attr_id)
		if attr_values:
		    attr_name = attr_values[0].attribute_name
		    attr_desc = attr_values[0].description
		    pro_pro_id = attr_values[0].product_property_id
		    img_data = ProductImages.objects.get(image_id=pro_pro_id).image_id
		    img_url = ProductImages.objects.get(image_id=pro_pro_id).image_url
		    custom_data = (attr_name,attr_desc,img_data,img_url)
	    	    customization_data.append(custom_data)
    data_dict.append({'product_title':product_title, 'quantity': quantity, 'invoice_amount': invoice_amount, 'remarks': remarks,
                      'customization_data': customization_data, 'cust_id': customer_id, 'cust_name': customer_name, 'phone': phone,
                      'email': email, 'address': address, 'city': city, 'state': state, 'pin': pin, 'shipment_date': str(shipment_date),
                      'cus_data': cus_data, 'item_code': sku_code, 'order_id': order_id,
                     'image_url': order_details.sku.image_url})
    return HttpResponse(json.dumps({'data_dict': data_dict}))

@csrf_exempt
@get_admin_user
def get_stock_location_quantity(request, user=''):
    wms_code = request.GET.get('wms_code')
    location = request.GET.get('location')
    filter_params = {'sku__user': user.id}
    picklist_filter = {'stock__sku__user': user.id, 'status': 1}
    rm_filter = {'material_picklist__jo_material__material_code__user': user.id, 'status': 1}
    if wms_code:
        sku_master = SKUMaster.objects.filter(user=user.id, wms_code=wms_code)
        if not sku_master:
            return HttpResponse(json.dumps({'message': 'Invalid Location'}))
        filter_params['sku__wms_code'] = wms_code
        picklist_filter['stock__sku__wms_code'] = wms_code
        rm_filter['stock__sku__wms_code'] = wms_code

    if location:
        location_master = LocationMaster.objects.filter(zone__user=user.id, location=location)
        if not location_master:
            return HttpResponse(json.dumps({'message': 'Invalid Location'}))
        filter_params['location__location'] = location
        picklist_filter['stock__location__location'] = location
        rm_filter['stock__location__location'] = location

    stock_quantity = StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE').filter(**filter_params).\
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
    invoiced = all_picklists.filter(order__user=user.id, status__in=['picked', 'batch_picked', 'dispatched']).\
                                            values_list('order__order_id', flat=True).distinct()
    partial_invoiced = all_picklists.filter(order__user=user.id, picked_quantity__gt=0, status__icontains='open').values_list('order__order_id', flat=True).distinct()
    total_data = OrderDetail.objects.filter(user = user.id, marketplace__iexact = 'offline').annotate(total_invoice=Sum('invoice_amount'),
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
        sum_data = total_data.filter(customer_id=data['customer_id'], customer_name=data['customer_name']).aggregate(Sum('payment_received'),
                                     Sum('invoice_amount'))
        receivable = sum_data['invoice_amount__sum']-sum_data['payment_received__sum']
        total_payment_received += sum_data['payment_received__sum']
        total_invoice_amount += sum_data['invoice_amount__sum']
        total_payment_receivable += receivable
        customer_data.append({'channel': data['marketplace'] ,'customer_id': data['customer_id'], 
                              'customer_name': data['customer_name'], 'payment_received': "%.2f" % sum_data['payment_received__sum'], 
                              'payment_receivable': "%.2f" % receivable,
                              'invoice_amount': "%.2f" % sum_data['invoice_amount__sum']  })
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
    invoiced = all_picklists.filter(order__user=user.id, status__in=['picked', 'batch_picked', 'dispatched']).\
                                            values_list('order__order_id', flat=True).distinct()
    partial_invoiced = all_picklists.filter(order__user=user.id, picked_quantity__gt=0, status__icontains='open').values_list('order__order_id', flat=True).distinct()
    total_data = OrderDetail.objects.filter(user = user.id, customer_id = customer_id, customer_name = customer_name,
                                            marketplace = channel).annotate(total_invoice=Sum('invoice_amount'),                                                                            total_received=Sum('payment_received')).filter(total_received__lt=F('total_invoice'))
    if status_filter == 'Partially Invoiced':
        total_data = total_data.filter(order_id__in=partial_invoiced)
    if status_filter == 'Invoiced':
        total_data = total_data.filter(order_id__in=invoiced)
    if status_filter == 'Order Created':
        total_data = total_data.exclude(order_id__in=list(chain(invoiced, partial_invoiced)))
    orders = total_data.values('order_id', 'order_code', 'original_order_id', 'payment_mode', 'customer_id', 'customer_name').distinct()
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
            picklist = all_picklists.filter(order__order_id=data['order_id'], order__order_code=data['order_code']).\
                                             order_by('-updation_date')
            picked_date = get_local_date(user, picklist[0].updation_date, send_date=True)
            customer_master = CustomerMaster.objects.filter(customer_id=data['customer_id'], name=data['customer_name'], user=user.id)
            if customer_master:
                if customer_master[0].credit_period:
                    expected_date = picked_date + datetime.timedelta(days = customer_master[0].credit_period)
                    expected_date = expected_date.strftime("%d %b, %Y")
            if not expected_date:
                expected_date = picked_date.strftime("%d %b, %Y")
        
        sum_data = total_data.filter(order_id = data['order_id']).aggregate(Sum('invoice_amount'), Sum('payment_received'))
        order_data.append({'order_id': data['order_id'], 'display_order': order_id, 'account': data['payment_mode'],
                           'inv_amount': "%.2f" % sum_data['invoice_amount__sum'],
                           'receivable': "%.2f" % (sum_data['invoice_amount__sum']-sum_data['payment_received__sum']),
                           'received': '%.2f' % sum_data['payment_received__sum'], 'order_status': order_status,
                           'expected_date': expected_date})
    response["data"] = order_data
    return HttpResponse(json.dumps(response))

@login_required
@csrf_exempt
@get_admin_user
def get_customer_master_id(request, user=''):
    customer_id = 1
    customer_master = CustomerMaster.objects.filter(user=user.id).values_list('customer_id', flat=True).order_by('-customer_id')
    if customer_master:
        customer_id = customer_master[0] + 1
    return HttpResponse(json.dumps({'customer_id': customer_id}))

@login_required
@csrf_exempt
@get_admin_user
def update_payment_status(request, user=''):
    data_dict = dict(request.GET.iterlists())
    for i in range(0, len(data_dict['order_id'])):
        if not data_dict['amount'][i]:
            continue
        payment = float(data_dict['amount'][i])
        order_details = OrderDetail.objects.filter(order_id=data_dict['order_id'][i], user=user.id)
        for order in order_details:
            if not payment:
                break
            if float(order.invoice_amount) > float(order.payment_received):
                diff = float(order.invoice_amount) - float(order.payment_received)
                if payment > diff:
                    order.payment_received = diff
                    payment -= diff
                    PaymentSummary.objects.create(order_id=order.id, creation_date=datetime.datetime.now(), payment_received=diff)
                else:
                    PaymentSummary.objects.create(order_id=order.id, creation_date=datetime.datetime.now(), payment_received=payment)
                    order.payment_received = payment
                    payment = 0
                order.save()
    return HttpResponse("Success")

@login_required
@csrf_exempt
@get_admin_user
def create_orders_data(request, user=''):
    return HttpResponse(json.dumps({'payment_mode': PAYMENT_MODES, 'taxes': TAX_TYPES}))

@csrf_exempt
def get_order_category_view_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['id', 'customer_name', 'order_id', 'sku__sku_category', 'total']
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_params = get_filtered_params(filters, lis[:1])
    search_params['sku_id__in'] = sku_master_ids

    if search_term:
        mapping_results = OrderDetail.objects.filter(**data_dict).values('customer_name', 'order_id', 'sku__sku_category',
                                              'order_code', 'original_order_id').distinct().\
                                              annotate(total=Sum('quantity')).filter(Q(customer_name__icontains=search_term) |
                                              Q(order_id__icontains=search_term) | Q(sku__sku_category__icontains=search_term),
                                              **search_params).order_by(order_data)
    else:
        mapping_results = OrderDetail.objects.filter(**data_dict).values('customer_name', 'order_id', 'sku__sku_category',
                                              'order_code', 'original_order_id').distinct().\
                                              annotate(total=Sum('quantity')).filter(**search_params).order_by(order_data)


    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    index = 0
    for dat in mapping_results[start_index:stop_index]:
        order_id = dat['order_code'] + str(dat['order_id'])
        check_values = order_id + '<>' + dat['sku__sku_category']
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (check_values, dat['total'])

        temp_data['aaData'].append(OrderedDict(( ('data_value', check_values), ('Customer Name', dat['customer_name']),
                                                 ('Order ID', order_id), ('Category', dat['sku__sku_category']),
                                                 ('Total Quantity', dat['total']),
                                                 ('id', index), ('DT_RowClass', 'results') )))
        index += 1

@csrf_exempt
def get_order_view_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['id', 'customer_name', 'order_id', 'marketplace', 'total', 'creation_date']
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_params = get_filtered_params(filters, lis[:1])
    search_params['sku_id__in'] = sku_master_ids

    all_orders = OrderDetail.objects.filter(**data_dict)
    if search_term:
        mapping_results = all_orders.values('customer_name', 'order_id', 'order_code', 'original_order_id', 'marketplace').\
                                              distinct().annotate(total=Sum('quantity')).filter(Q(customer_name__icontains=search_term) |
                                              Q(order_id__icontains=search_term) | Q(sku__sku_category__icontains=search_term),
                                              **search_params).order_by(order_data)
    else:
        mapping_results = all_orders.values('customer_name', 'order_id', 'order_code', 'original_order_id', 'marketplace').\
                                              distinct().annotate(total=Sum('quantity')).filter(**search_params).order_by(order_data)


    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    index = 0
    for dat in mapping_results[start_index:stop_index]:
        order_id = dat['order_code'] + str(dat['order_id'])
        check_values = order_id
        creation_date = all_orders.filter(order_id=dat['order_id'], order_code=dat['order_code'], user=user.id)[0].creation_date
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (check_values, dat['total'])

        temp_data['aaData'].append(OrderedDict(( ('data_value', check_values), ('Customer Name', dat['customer_name']),
                                                 ('Order ID', order_id), ('Market Place', dat['marketplace']),
                                                 ('Total Quantity', dat['total']),
                                                 ('Creation Date', get_local_date(request.user, creation_date)),
                                                 ('id', index), ('DT_RowClass', 'results') )))
        index += 1


@csrf_exempt
@login_required
@get_admin_user
def order_category_generate_picklist(request, user=''):
    data = []
    order_data = []
    stock_status = ''
    out_of_stock = []
    picklist_number = get_picklist_number(user)

    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(status=1, user=user.id, quantity__gt=0)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by('receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by('location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    sku_stocks = stock_detail1 | stock_detail2
    for key, value in request.POST.iteritems():
        if key in PICKLIST_SKIP_LIST:
            continue

        order_filter = {'quantity__gt': 0 }
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

        stock_status, picklist_number = picklist_generation(order_detail, request, picklist_number, user, sku_combos, sku_stocks,\
                                                            status = 'open', remarks='')

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
    if not stock_status:
        order_status = data[0]['status']
        if order_status == 'open':
            headers.insert(headers.index('WMS Code'),'Order ID')
            order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
            order_count_len = len(filter(lambda x: len(str(x))>0, order_count))
            if order_count_len == 1:
                single_order = str(order_count[0])

    return HttpResponse(json.dumps({'data': data, 'headers': headers,
                           'picklist_id': picklist_number + 1,'stock_status': stock_status, 'show_image': show_image,
                           'use_imei': use_imei, 'order_status': order_status, 'user': request.user.id}))


