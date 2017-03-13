from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import json
from django.db.models import Q, F
from itertools import chain
from collections import OrderedDict
from itertools import groupby
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
from common import *
from miebach_utils import *

@csrf_exempt
def get_stock_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['sku__wms_code', 'sku__sku_desc', 'sku__sku_brand', 'sku__sku_category', 'total', 'total', 'total', 'sku__measurement_type']
    lis1 = ['product_code__wms_code', 'product_code__sku_desc', 'product_code__sku_brand', 'product_code__sku_category', 'total',
            'total', 'total', 'product_code__measurement_type']
    sort_cols = ['WMS Code', 'Product Description', 'SKU Brand', 'SKU Category', 'Quantity', 'Reserved Quantity', 'Total Quantity',
                'Unit of Measurement']
    lis2 = ['wms_code', 'sku_desc', 'sku_brand', 'sku_category', 'threshold_quantity', 'threshold_quantity', 'threshold_quantity', 'measurement_type']
    search_params = get_filtered_params(filters, lis)
    search_params1 = get_filtered_params(filters, lis1)
    search_params2 = get_filtered_params(filters, lis2)


    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if 'total__icontains' in search_params1.keys():
        if search_params1['total__icontains']:
            search_params1['status__icontains'] = search_params1['total__icontains']
        del search_params1['total__icontains']

    job_order = JobOrder.objects.filter(product_code__user=user.id, status__in=['grn-generated', 'pick_confirm'])
    job_ids = job_order.values_list('id', flat=True)
    extra_headers =  list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    status_track = StatusTracking.objects.filter(status_type='JO', status_id__in=job_ids,status_value__in=extra_headers, quantity__gt=0).\
                                          values('status_value', 'status_id').distinct().annotate(total=Sum('quantity'))
    status_ids = map(lambda d: d.get('status_id', ''), status_track)

    search_params['sku_id__in'] = sku_master_ids
    search_params1['product_code_id__in'] = sku_master_ids

    reserved_instances = PicklistLocation.objects.filter(status=1, picklist__order__user=user.id).values('stock__sku__wms_code').\
                             distinct().annotate(reserved=Sum('reserved'))
    raw_res_instances = RMLocation.objects.filter(status=1, material_picklist__jo_material__material_code__user=user.id).\
                                           values('material_picklist__jo_material__material_code__wms_code').distinct().\
                                           annotate(rm_reserved=Sum('reserved'))

    reserveds = map(lambda d: d['stock__sku__wms_code'], reserved_instances)
    reserved_quantities = map(lambda d: d['reserved'], reserved_instances)
    raw_reserveds = map(lambda d: d['material_picklist__jo_material__material_code__wms_code'], raw_res_instances)
    raw_reserved_quantities = map(lambda d: d['rm_reserved'], raw_res_instances)
    temp_data['totalQuantity']  = 0
    temp_data['totalReservedQuantity']  = 0
    temp_data['totalAvailableQuantity']  = 0

    if search_term:
        master_data = StockDetail.objects.exclude(receipt_number=0).values_list('sku__wms_code', 'sku__sku_desc', 'sku__sku_category',
                                           'sku__sku_brand').\
                                          distinct().annotate(total=Sum('quantity')).filter(Q(sku__wms_code__icontains=search_term) |
                                          Q(sku__sku_desc__icontains=search_term) | Q(sku__sku_category__icontains=search_term) |
                                          Q(total__icontains=search_term), sku__user=user.id, status=1,**search_params)
        wms_codes = map(lambda d: d[0], master_data)
        master_data1 = job_order.exclude(product_code__wms_code__in=wms_codes).filter(Q(product_code__wms_code__icontains=search_term) |
                                      Q(product_code__sku_desc__icontains=search_term) | Q(product_code__sku_category__icontains=search_term),
                                      **search_params1).values_list('product_code__wms_code',
                                         'product_code__sku_desc', 'product_code__sku_category', 'product_code__sku_brand').distinct()
        quantity_master_data = master_data.aggregate(Sum('total'))
        master_data = list(chain(master_data, master_data1))


    else:
        master_data = StockDetail.objects.exclude(receipt_number=0).values_list('sku__wms_code', 'sku__sku_desc', 'sku__sku_category',
                                          'sku__sku_brand').distinct().\
                                          annotate(total=Sum('quantity')).filter(sku__user = user.id, **search_params).\
                                          order_by(order_data)
        wms_codes = map(lambda d: d[0], master_data)
        quantity_master_data = master_data.aggregate(Sum('total'))
        master_data1 = job_order.exclude(product_code__wms_code__in=wms_codes).filter(**search_params1).values_list('product_code__wms_code',
                                         'product_code__sku_desc', 'product_code__sku_category', 'product_code__sku_brand').distinct()
        master_data = list(chain(master_data, master_data1))
    zero_quantity = sku_master.exclude(wms_code__in = wms_codes).filter(user=user.id)
    if search_params2:
        zero_quantity = zero_quantity.filter(**search_params2)
    if search_term:
        zero_quantity = zero_quantity.filter( Q(wms_code__icontains=search_term)| Q(sku_desc__icontains=search_term) | Q(sku_category__icontains=search_term) )

    zero_quantity = zero_quantity.values_list('wms_code', 'sku_desc', 'sku_category', 'sku_brand', 'skuquantity')
    master_data = list(chain(master_data, zero_quantity))
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if quantity_master_data['total__sum'] == None:
        quantity_master_data['total__sum'] = 0
    temp_data['totalQuantity'] = int(quantity_master_data['total__sum'])

    for data in master_data:
        total_available_quantity = 0
        total_reserved = 0
        total = 0
        diff = 0

        if data[0] in reserveds:
            total_reserved = float(reserved_quantities[reserveds.index(data[0])])
            temp_data['totalReservedQuantity'] += total_reserved
        if data[0] in raw_reserveds:
            total_reserved = float(raw_reserved_quantities[raw_reserveds.index(data[0])])
            temp_data['totalReservedQuantity'] += total_reserved
        if len(data) >= 5:
            if data[4] != None:
                if len(data) > 4:
                    total = data[4]
            diff = total-total_reserved
        if diff > 0:
            total_available_quantity = diff
        temp_data['totalAvailableQuantity'] += total_available_quantity

    temp_data['totalReservedQuantity'] = int(temp_data['totalReservedQuantity'])

    temp_data['totalAvailableQuantity'] = int(temp_data['totalAvailableQuantity'])

    reserveds = map(lambda d: d['stock__sku__wms_code'], reserved_instances)
    reserved_quantities = map(lambda d: d['reserved'], reserved_instances)
    raw_reserveds = map(lambda d: d['material_picklist__jo_material__material_code__wms_code'], raw_res_instances)
    raw_reserved_quantities = map(lambda d: d['rm_reserved'], raw_res_instances)
    #temp_data['totalQuantity'] = sum([data[4] for data in master_data])
    for ind, data in enumerate(master_data[start_index:stop_index]):
        reserved = 0
        #total = data[4] if len(data) > 4 else 0
        total = 0
        if len(data) >= 5:
            if data[4] != None:
                if len(data) > 4:
                    total = data[4]

        sku = sku_master.get(wms_code=data[0], user=user.id)
        if data[0] in reserveds:
            reserved += float(reserved_quantities[reserveds.index(data[0])])
        if data[0] in raw_reserveds:
            reserved += float(raw_reserved_quantities[raw_reserveds.index(data[0])])

        quantity = total - reserved
        if quantity < 0:
            quantity = 0
        temp_data['aaData'].append(OrderedDict(( ('WMS Code', data[0]), ('Product Description', data[1]),
                                                 ('SKU Category', data[2]), ('SKU Brand', data[3]), ('Available Quantity', quantity),
                                                 ('Reserved Quantity', reserved), ('Total Quantity', total),
                                                 ('Unit of Measurement', sku.measurement_type),
                                                 ('DT_RowId', data[0]) )))

    #sort_col = sort_cols[col_num]
    #if order_term == 'asc':
    #    temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
    #else:
    #    temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)
    #temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]

def get_stock_counts(quantity, single_sku):

    stock_count = []
    for single_data in quantity:
        purch = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(open_po__sku__user=single_data['user'],open_po__sku__sku_code=single_sku).values('open_po__sku__sku_code').annotate(total_order=Sum('open_po__order_quantity'),total_received=Sum('received_quantity'))
        purchases = map(lambda d: d['open_po__sku__sku_code'], purch)
        total_order = map(lambda d: d['total_order'], purch)
        total_received = map(lambda d: d['total_received'], purch)
        if (total_order or total_received):
            trans_quantity = float(total_order[0]) - float(total_received[0])
        else:
            trans_quantity = 0

        if single_data['quantity'] == '':
            available = 0
            reserved = 0
        else:
            if single_data['quantity'] == 'No SKU':
                available = 'No SKU'
                reserved = 0
            else:
                reserved_da = PicklistLocation.objects.filter(stock__sku__sku_code=single_data['sku_code'], stock__sku__user=single_data['user']).values_list('reserved', flat=True)
                if not reserved_da:
                    available = single_data['quantity']
                    reserved = 0
                else:
                    available = single_data['quantity'] - reserved_da[0]
                    reserved = reserved_da[0]
        stock_count.append({'available': available, 'name': single_data['name'], 'transit': trans_quantity, 'reserved': reserved})
    return stock_count

def get_quantity_data(user_groups, single_sku):

    ret_list = []
    for user in user_groups:
        exist = SKUMaster.objects.filter(sku_code = single_sku,user=user)
        ware = User.objects.filter(id=user).values_list('username', flat=True)[0]
        if exist:
            quant = StockDetail.objects.filter(sku__user=user, sku__sku_code=single_sku).values('sku__user', 'sku__sku_code').\
                    annotate(total=Sum('quantity'))
            if quant:
                sku_code = quant[0]['sku__sku_code']
                user_id = quant[0]['sku__user']
                quantity = quant[0]['total']
                ret_list.append({'sku_code': sku_code, 'user': user_id, 'quantity': quantity, 'name': ware})
            else:
                sku_code = ''
                user_id = exist[0].user
                quantity = ''
                ret_list.append({'sku_code': sku_code, 'user': user_id, 'quantity': quantity, 'name': ware})
        else:
            quant = {'sku_code': '', 'user': 0, 'quantity': 'No SKU', 'name': ware}
            ret_list.append(quant)
    return ret_list

def get_available_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):

    data, temp_data, other, da = get_warehouses_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters)

    list_da = {}

    for i in da:
        if i['available'] is None:
            i['available'] = 0
        list_da[i['ware']] = i['available']

    temp_data['ware_list'] = list_da
    for one_data,sku_det in zip(data,other['rem']):
        header = other['header']
        single_sku = sku_det['single_sku']
        sku_desc = sku_det['sku_desc']
        sku_brand = sku_det['sku_brand']
        sku_category = sku_det['sku_category']
        var = (OrderedDict(( (header[0], single_sku), (header[1], sku_brand), (header[2], sku_desc),(header[3], sku_category) )) )
        for single in one_data:
            available = single['available']
            name = single['name']
            var[name] = available
        temp_data['aaData'].append(var)

def get_availintra_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):

    data, temp_data, other, da = get_warehouses_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters)

    list_da = {}
    for i in da:
        if i['available'] is None:
            i['available'] = 0
        if i['transit'] is None:
            i['transit'] = 0
        list_da[i['ware']] = i['available'] + i['transit']

    temp_data['ware_list'] = list_da
    for one_data,sku_det in zip(data,other['rem']):
        header = other['header']
        single_sku = sku_det['single_sku']
        sku_desc = sku_det['sku_desc']
        sku_brand = sku_det['sku_brand']
        sku_category = sku_det['sku_category']
        var = (OrderedDict(( (header[0], single_sku), (header[1], sku_brand), (header[2], sku_desc),(header[3], sku_category) )) )
        for single in one_data:
            avail = single['available']
            intra = single['transit']
            if isinstance(avail, str):
                available = avail
            else:
                available = avail + intra
            name = single['name']
            var[name] = available
        temp_data['aaData'].append(var)

def get_avinre_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):

    data, temp_data, other, da = get_warehouses_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters)

    list_da = {}
    for i in da:
        if i['available'] is None:
            i['available'] = 0
        if i['transit'] is None:
            i['transit'] = 0
        if (i['reserved'] is None) or (i['reserved'] < 0):
            i['reserved'] = 0
        list_da[i['ware']] = i['available'] + i['transit'] + i['reserved']

    temp_data['ware_list'] = list_da
    for one_data,sku_det in zip(data,other['rem']):
        header = other['header']
        single_sku = sku_det['single_sku']
        sku_desc = sku_det['sku_desc']
        sku_brand = sku_det['sku_brand']
        sku_category = sku_det['sku_category']
        var = (OrderedDict(( (header[0], single_sku), (header[1], sku_brand), (header[2], sku_desc),(header[3], sku_category) )) )
        for single in one_data:
            avail = single['available']
            intra = single['transit']
            reserv = single['reserved']
            if isinstance(avail, str):
                available = avail
            else:
                available = avail + intra + reserv
            name = single['name']
            var[name] = available
        temp_data['aaData'].append(var)

def get_warehouses_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):

    data_to_send = []
    other_data = {}

    lis = ['sku_code', 'sku_brand', 'sku_desc', 'sku_category']

    if len(filters) <= 4:
        search_params = get_filtered_params(filters, lis)
    else:
        search_params = {}

    if col_num <= 3:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data

    warehouses = UserGroups.objects.filter(admin_user_id=user.id).values_list('user_id',flat=True)
    ware_list = list(User.objects.filter(id__in=warehouses).values_list('username', flat=True))
    ware_list.append(user.username)
    header = ["SKU Code", "SKU Brand", "SKU Description", "SKU Category"]
    headers = header + ware_list

    user_groups = UserGroups.objects.filter(Q(admin_user_id=user.id)|Q(user_id=user.id))
    if user_groups:
        admin_user_id = user_groups[0].admin_user_id
    else:
        admin_user_id = user.id
    user_groups = list(UserGroups.objects.filter(admin_user_id=admin_user_id).values_list('user_id',flat=True))
    user_groups.append(admin_user_id)
    sku_master = SKUMaster.objects.filter(user__in=user_groups, **search_params)
    if col_num <= 3:
        sku_master = sku_master.order_by(order_data)
    if search_term:
        sku_master = sku_master.filter(Q(sku_code__icontains = search_term)|Q(sku_desc__icontains = search_term)|Q(sku_brand__icontains = search_term), user__in=user_groups)
    sku_codes = sku_master.values_list('sku_code',flat=True).distinct()
    #sku_codes = StockDetail.objects.filter(sku__user__in=user_groups).values_list('sku__sku_code',flat=True).distinct()
    temp_data['ware_list'] = ''
    temp_data['recordsTotal'] = len(sku_codes)
    temp_data['recordsFiltered'] = len(sku_codes)
    #temp_data['ware_list'] = {}
    other_data['header'] = header
    other_data['rem'] = []
    data = get_aggregate_data(user_groups, list(sku_codes)[0:temp_data['recordsTotal']])

    for single_sku in sku_codes[start_index:stop_index]:
        sku_brand = sku_master.filter(sku_code = single_sku).values_list('sku_brand',flat=True)[0]
        sku_desc = sku_master.filter(sku_code = single_sku).values_list('sku_desc',flat=True)[0]
        sku_category = sku_master.filter(sku_code = single_sku).values_list('sku_category',flat=True)[0]
        quantity = get_quantity_data(user_groups, single_sku)
        available_quantity = get_stock_counts(quantity, single_sku)
        data_to_send.append(available_quantity)
        other_data['rem'].append({'single_sku': single_sku, 'sku_brand': sku_brand, 'sku_desc': sku_desc, 'sku_category': sku_category})
    return data_to_send, temp_data, other_data, data


def get_aggregate_data(user_groups, sku_list):

    data = []
    for user in user_groups:
        available = 0
        total = StockDetail.objects.filter(sku__wms_code__in = list(sku_list), sku__user=user).aggregate(Sum('quantity'))['quantity__sum']
        reserved = PicklistLocation.objects.filter(stock__sku__sku_code__in = list(sku_list)).aggregate(Sum('reserved'))['reserved__sum']
        purch = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(open_po__sku__user=user,open_po__sku__sku_code__in=sku_list).values('open_po__sku__sku_code').annotate(total_order=Sum('open_po__order_quantity'),total_received=Sum('received_quantity'))
        total_order = sum(map(lambda d: d['total_order'], purch))
        total_received = sum(map(lambda d: d['total_received'], purch))
        trans_quantity = float(total_order) - float(total_received)
        trans_quantity = round(trans_quantity, 2)
        if total:
            available = total
            available = round(available, 2)
        if reserved:
            reserved = available - reserved
            reserved = round(reserved, 2)
        if available < 0:
            available = 0
        ware_name = User.objects.filter(id=user).values_list('username', flat=True)[0]
        data.append({'ware': ware_name, 'available': available, 'reserved': reserved, 'transit': trans_quantity})
    return data

def get_sku_stock_data(start_index, stop_index, temp_data, search_term, order_term, col_num):
    if order_term:
        if col_num == 4:
            col_num = col_num - 1
        if order_term == 'asc':
            master_data = SKUStock.objects.filter().order_by(SKU_STOCK_HEADERS.values()[col_num])
        elif order_term == 'desc':
            master_data = SKUStock.objects.filter().order_by('-%s' % SKU_STOCK_HEADERS.values()[col_num])
        else:
            master_data = SKUStock.objects.filter()
    if search_term:
        master_data = SKUStock.objects.filter(Q(sku__sku_code__icontains=search_term) | Q(total_quantity__icontains=search_term) | Q(online_quantity__icontains=search_term) | Q(offline_quantity__icontains=search_term))
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        reserved_quantity = PicklistLocation.objects.filter(picklist__status__icontains='open', picklist__order__sku_id=data.sku_id, status=1).aggregate(Sum('quantity'))['quantity__sum']
        if not reserved_quantity:
            reserved_quantity = 0

        total_quantity = StockDetail.objects.filter(sku_id=data.sku_id, quantity__gt=0).aggregate(Sum('quantity'))['quantity__sum']
        if not total_quantity:
            total_quantity = 0
        quantity = total_quantity - reserved_quantity
        if quantity <= 0:
            continue
        sku_online = data.sku.online_percentage
        data = online_percentage_update(data, quantity, 'false', 4)
        if sku_online:
            online_quantity = int(round((float(quantity) * float(sku_online)) / 100))
        else:
            online_quantity = quantity
        if data.status == 0:
            online_quantity = data.online_quantity
        temp_data['aaData'].append({'SKU Code': data.sku.sku_code, 'Total Quantity': quantity, 'Suggested Online Quantity': online_quantity,
                                    'Current Online Quantity': data.online_quantity, 'Offline Quantity': data.offline_quantity,
                                    'DT_RowAttr': {'data-id': data.id}})

@csrf_exempt
def get_stock_detail_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user,request.user)
    lis = ['receipt_number','receipt_date', 'sku_id__wms_code','sku_id__sku_desc','location__zone__zone','location__location', 'quantity',
           'receipt_type', 'pallet_detail__pallet_code']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_params = get_filtered_params(filters, lis)
    if 'receipt_date__icontains' in search_params:
        search_params['receipt_date__regex'] = search_params['receipt_date__icontains']
        del search_params['receipt_date__icontains']
    search_params['sku_id__in'] = sku_master_ids

    if search_term:
        master_data = StockDetail.objects.exclude(receipt_number=0).filter( Q(receipt_number__icontains = search_term) |
                                                  Q(sku__wms_code__icontains = search_term) |Q(quantity__icontains=search_term) |
                                                  Q(location__zone__zone__icontains = search_term) | Q(sku__sku_code__icontains = search_term) |
                                                  Q(sku__sku_desc__icontains = search_term) | Q(location__location__icontains = search_term),
                                                  sku__user=user.id).filter(**search_params).order_by(order_data)

    else:
        master_data = StockDetail.objects.exclude(receipt_number=0).filter(sku__user=user.id, **search_params).\
                                          order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        pallet_switch = get_misc_value('pallet_switch', user.id)
        if pallet_switch == 'true':
            pallet_code = ''
            if data.pallet_detail:
                pallet_code = data.pallet_detail.pallet_code
            temp_data['aaData'].append(OrderedDict(( ('Receipt ID', data.receipt_number), ('DT_RowClass', 'results'),
                                        ('Receipt Date', get_local_date(user, data.receipt_date)), ('SKU Code', data.sku.sku_code),
                                        ('WMS Code', data.sku.wms_code), ('Product Description', data.sku.sku_desc),
                                        ('Zone', data.location.zone.zone), ('Location', data.location.location),
                                        ('Quantity', get_decimal_limit(user.id, data.quantity)),
                                        ('Pallet Code', pallet_code), ('Receipt Type', data.receipt_type) )) )
        else:
            temp_data['aaData'].append(OrderedDict(( ('Receipt ID', data.receipt_number), ('DT_RowClass', 'results'),
                                        ('Receipt Date', get_local_date(user, data.receipt_date)), ('SKU Code', data.sku.sku_code),
                                        ('WMS Code', data.sku.wms_code), ('Product Description', data.sku.sku_desc),
                                        ('Zone', data.location.zone.zone), ('Location', data.location.location),
                                        ('Quantity', get_decimal_limit(user.id, data.quantity)), ('Receipt Type', data.receipt_type))))

@csrf_exempt
def get_cycle_confirmed(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters=''):
    sku_master, sku_master_ids = get_sku_master(user,request.user)
    lis = ['cycle', 'creation_date']
    if search_term:
        cycle_data = CycleCount.objects.filter(sku_id__in=sku_master_ids).filter(Q(cycle__icontains=search_term) | Q(creation_date__regex=search_term),
                                               sku__user=user.id,status=1).order_by(lis[col_num]).values('cycle').distinct()
    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        cycle_data = CycleCount.objects.filter(status='1',sku__user=user.id, sku_id__in=sku_master_ids).order_by(order_data).values('cycle').distinct()
    else:
        cycle_data = CycleCount.objects.filter(status='1',sku__user=user.id, sku_id__in=sku_master_ids).values('cycle').distinct()
    data = []

    for count in cycle_data:
        record = CycleCount.objects.filter(cycle=count['cycle'],sku__user=user.id)
        data.append(record[0])

    temp_data['recordsTotal'] = len(data)
    temp_data['recordsFiltered'] = len(data)

    for item in data[start_index:stop_index]:
        temp_data['aaData'].append(OrderedDict(( ('Cycle Count ID', item.cycle), ('Date', get_local_date(request.user, item.creation_date)),
                                                 ('DT_RowClass', 'results'), ('DT_RowId', item.cycle) )))

def get_move_inventory(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, status):
    cycle_count = CycleCount.objects.filter(status='checked', sku__user=user.id)
    ids_list = []
    negative_items = []
    positive_items = []
    move_items = []
    for count in cycle_count:
        if count.quantity > count.seen_quantity:
            negative_items.append(count)
        elif count.quantity < count.seen_quantity:
            positive_items.append(count)

    for positive in positive_items[:]:
        positive_difference = positive.seen_quantity - positive.quantity
        positive_sku = positive.sku_id
        for negative in negative_items[:]:
            negative_difference = negative.quantity - negative.seen_quantity
            negative_sku = negative.sku_id
            if positive_sku == negative_sku:
                if positive_difference >= negative_difference:
                    positive_difference -= negative_difference
                    move_items.append((positive, negative, negative_difference))
                    negative_items.remove(negative)

            if positive_difference == 0:
                positive_items.remove(positive)
                break

    all_data = []
    data_id = 1
    if status == 'adj':
        total_items = positive_items + negative_items
        for positive in total_items:
            data_dict = {'cycle_id': positive.id, 'adjusted_location': '', 'adjusted_quantity': positive.seen_quantity, 'reason': '', 'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}
            data = InventoryAdjustment.objects.filter(cycle_id=positive.id)
            if not data:
                data = InventoryAdjustment(**data_dict)
                data.save()
            all_data.append(positive)
        temp_data['recordsTotal'] = len(all_data)
        temp_data['recordsFiltered'] = len(all_data)
        for positive in all_data[start_index:stop_index]:
            checkbox = "<input type='hidden' name='%s' value='%s'>" % (positive.id, positive.id)
            temp_data['aaData'].append({'': checkbox, 'Location': positive.location.location, 'WMS Code': positive.sku.wms_code, 'Description': positive.sku.sku_desc, 'Total Quantity': positive.quantity, 'Physical Quantity': positive.seen_quantity, 'Reason': "<input type='text' name='reason'>", 'DT_RowClass': 'results', 'id': data_id})
            data_id += 1

    else:
        for items in move_items[start_index:stop_index]:
            data_dict = {'cycle_id': items[0].id, 'adjusted_location': items[1].location_id, 'adjusted_quantity': items[2], 'reason': '', 'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}
            data = InventoryAdjustment.objects.filter(cycle_id=items[0].id)
            if not data:
                data = InventoryAdjustment(**data_dict)
                data.save()
                data = InventoryAdjustment.objects.filter(cycle_id=items[0].id)

            checkbox = "<input type='checkbox' name='%s' value='%s'>" % (items[0].id, items[1].id)
            temp_data['aaData'].append({'': checkbox, 'Source Location': items[0].location.location, 'WMS Code': items[0].sku.wms_code,
                                        'Description': items[0].sku.sku_desc, 'Destination Location': items[1].location.location,
                                        'Move Quantity': items[2], 'Reason': '', 'DT_RowClass': 'results', 'id': data_id})
            data_id += 1

@csrf_exempt
@login_required
@get_admin_user
def insert_move_inventory(request, user=''):
    data = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not data:
        cycle_id = 1
    else:
        cycle_id = data[0].cycle + 1

    now = str(datetime.datetime.now())
    wms_code = request.GET['wms_code']
    source_loc = request.GET['source_loc']
    dest_loc = request.GET['dest_loc']
    quantity = request.GET['quantity']
    status = move_stock_location(cycle_id, wms_code, source_loc, dest_loc, quantity, user)

    return HttpResponse(status)

@csrf_exempt
def get_cycle_count(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user,request.user)
    search_params = {}
    lis = ['sku__wms_code', 'location__zone__zone', 'location__location', 'total']
    col_num = col_num - 1
    order_data = lis[col_num]
    search_parameters = get_filtered_params(filters, lis)
    for key, value in search_parameters.iteritems():
        if key.replace('__icontains', '') in lis[:3]:
            key = key.replace('contains', 'exact')
        search_params[key] = value

    search_params['sku_id__in'] = sku_master_ids
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        cycle_data = StockDetail.objects.values('sku__wms_code', 'location__location', 'location__zone__zone').distinct().\
                                         annotate(total=Sum('quantity')).filter(Q(sku__wms_code__icontains=search_term) |
                                         Q(location__zone__zone__icontains=search_term) | Q(location__location__icontains=search_term) |
                                         Q(total__icontains=search_term), sku__user=user.id, status=1, quantity__gt=0).filter(**search_params)
    else:
        if 'quantity' in order_data:
            order_data = order_data.replace('quantity', 'total')
        cycle_data = StockDetail.objects.filter(status=1,sku__user=user.id, quantity__gt=0).values('sku__wms_code', 'location__location',
                                                'location__zone__zone').distinct().annotate(total=Sum('quantity')).filter(**search_params).order_by(order_data)


    temp_data['recordsTotal'] = len(cycle_data)
    temp_data['recordsFiltered'] = len(cycle_data)

    index = 1
    for data in cycle_data[start_index:stop_index]:
        quantity = data['total']
        temp_data['aaData'].append({'wms_code': data['sku__wms_code'], 'zone': data['location__zone__zone'],
                                    'location': data['location__location'], 'quantity': get_decimal_limit(user.id, quantity), 'id': index})
        index = index+1

@csrf_exempt
@login_required
@get_admin_user
def confirm_cycle_count(request, user=''):
    stocks = []
    total_data = []
    search_params = {}
    stock_data = []
    myDict = dict(request.GET.iterlists())
    for i in range(0,len(myDict['wms_code'])):
        search_params['sku__user'] = user.id
        search_params['status'] = 1
        search_params['quantity__gt'] = 0
        if myDict['wms_code'][i]:
            search_params['sku_id__wms_code'] = myDict['wms_code'][i]
        if myDict['zone'][i]:
            search_params['location__zone__zone'] = myDict['zone'][i]
        if myDict['location'][i]:
            search_params['location_id__location'] = myDict['location'][i]
        if myDict['quantity'][i]:
            search_params['total'] = myDict['quantity'][i]

        if search_params:
            stock_values = StockDetail.objects.values('sku_id', 'location_id', 'location__zone_id').distinct().annotate(total=Sum('quantity')).filter(**search_params)
            for value in stock_values:
                del value['total']
                stocks = list(chain(stocks,(StockDetail.objects.filter(**value))))

    if 'search_term' in request.GET.keys():
        search_term = request.GET['search_term']
        if search_term:
            stocks = StockDetail.objects.filter(Q(sku__wms_code__icontains=search_term, status=1, quantity__gt=0) |
                                                Q(location__zone__zone__icontains=search_term, status=1, quantity__gt=0) |
                                                Q(location__location__icontains=search_term, status=1, quantity__gt=0) |
                                                Q(quantity__icontains=search_term, status=1, quantity__gt=0), sku__user=user.id)

    data = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not data:
        cycle_id = 1
    else:
        cycle_id = data[0].cycle + 1

    now = str(datetime.datetime.now())

    location_wise = {}
    saved_data = []
    for data in stocks:
        location_wise.setdefault(data.location_id, {})
        location_wise[data.location_id].setdefault(data.sku_id, 0)
        location_wise[data.location_id][data.sku_id] += data.quantity

    for location, sku_list in location_wise.iteritems():
        for sku, quantity in sku_list.iteritems():
            data_dict = copy.deepcopy(CYCLE_COUNT_FIELDS)
            data_dict['cycle'] = cycle_id
            data_dict['sku_id'] = sku
            data_dict['location_id'] = location
            data_dict['quantity'] = quantity
            data_dict['seen_quantity'] = 0
            data_dict['creation_date'] = now
            data_dict['updation_date'] = now

            dat = CycleCount(**data_dict)
            dat.save()

            total_data.append({'id': dat.id, 'wms_code': dat.sku.wms_code, 'zone': dat.location.zone.zone,
                               'location': dat.location.location, 'quantity': dat.quantity, 'seen_quantity': 0})
    return HttpResponse(json.dumps({'data': total_data, 'cycle_id': dat.cycle}))

@csrf_exempt
@login_required
@get_admin_user
def submit_cycle_count(request, user=''):
    for data_id, count in request.GET.iteritems():
        if not count:
            continue
        data = CycleCount.objects.get(id = data_id, sku__user = user.id)
        data.seen_quantity = count
        data.status = 'checked'
        data.save()
    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def get_id_cycle(request, user=''):
    cycle_data = CycleCount.objects.filter(cycle=request.GET['data_id'], sku__user = user.id)
    total_data = [];
    for dat in cycle_data:
      total_data.append({'id': dat.id, 'wms_code': dat.sku.wms_code, 'zone': dat.location.zone.zone,
                               'location': dat.location.location, 'quantity': dat.quantity, 'seen_quantity': 0})
    return HttpResponse(json.dumps({'data': total_data, 'cycle_id': cycle_data[0].cycle}))

@csrf_exempt
@login_required
@get_admin_user
def stock_summary_data(request, user=''):
    wms_code = request.GET['wms_code']
    stock_data = StockDetail.objects.exclude(receipt_number=0).filter(sku_id__wms_code=wms_code, sku__user = user.id)
    zones_data = {}
    production_stages = []
    for stock in stock_data:
        res_qty = PicklistLocation.objects.filter(stock_id=stock.id, status=1, picklist__order__user=user.id).\
                                           aggregate(Sum('reserved'))['reserved__sum']

        raw_reserved = RMLocation.objects.filter(status=1, material_picklist__jo_material__material_code__user=user.id,
                                                 stock_id=stock.id).aggregate(Sum('reserved'))['reserved__sum']

        if not res_qty:
            res_qty = 0
        if raw_reserved:
            res_qty = float(res_qty) + float(raw_reserved)
        zones_data.setdefault(stock.location.zone.zone, {})
        zones_data[stock.location.zone.zone].setdefault(stock.location.location, [0, 0])
        zones_data[stock.location.zone.zone][stock.location.location][1] += res_qty
        zones_data[stock.location.zone.zone][stock.location.location][0] += stock.quantity

    job_order = JobOrder.objects.filter(product_code__user=user.id, product_code__wms_code=wms_code,
                                        status__in=['grn-generated', 'pick_confirm', 'partial_pick'])
    job_codes = job_order.values_list('job_code', flat=True).distinct()
    extra_headers =  list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    for job_code in job_codes:
        job_ids = job_order.filter(job_code=job_code).values_list('id', flat=True)
        status_track = StatusTracking.objects.filter(status_type='JO', status_id__in=job_ids,status_value__in=extra_headers).\
                                          values('status_value').distinct().annotate(total=Sum('quantity'))

        tracking = dict(zip(map(lambda d: d.get('status_value', ''), status_track), map(lambda d: d.get('total', '0'), status_track)))
        for head in extra_headers:
            quantity = tracking.get(head, 0)
            if quantity:
                production_stages.append({'job_code': job_code, 'stage_name': head, 'stage_quantity': tracking.get(head, 0) })

    return HttpResponse(json.dumps({'zones_data': zones_data, 'production_stages': production_stages}))

@csrf_exempt
@login_required
@get_admin_user
def confirm_move_inventory(request, user=''):
    for key, value in request.GET.iteritems():
        data1 = CycleCount.objects.get(id=key, sku__user = user.id)
        data1.status = 'completed'
        data1.save()
        data2 = CycleCount.objects.get(id=value, sku__user = user.id)
        data2.status = 'completed'
        data2.save()
        dat = InventoryAdjustment.objects.get(cycle_id=key, cycle__sku__user = user.id)
        dat.reason = 'Moved Successfully'
        dat.save()

    return HttpResponse('Moved Successfully')

@csrf_exempt
@login_required
@get_admin_user
def confirm_inventory_adjustment(request, user=''):
    for key, value in request.GET.iteritems():
        data = CycleCount.objects.get(id = key, sku__user = user.id)
        data.status = 'completed'
        data.save()
        dat = InventoryAdjustment.objects.get(cycle_id = key, cycle__sku__user = user.id)
        dat.reason = value
        dat.save()
        location_count = StockDetail.objects.filter(location_id=dat.cycle.location_id, sku_id=dat.cycle.sku_id, quantity__gt=0,
                                                    sku__user = user.id)
        difference = data.seen_quantity - data.quantity
        for count in location_count:
            if difference > 0:
                count.quantity += difference
                count.save()
                break
            elif difference < 0:
                if (count.quantity + difference) >= 0:
                    count.quantity += difference
                    count.save()
                    break
                elif (count.quantity + difference) <= 0:
                    difference -= count.quantity
                    count.quantity = 0
                    count.save()

                if difference == 0:
                    break

    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def delete_inventory(request, user=''):
    for key, value in request.GET.iteritems():
        inventory = CycleCount.objects.get(id=key).delete()
    return HttpResponse('Updated Successfully')

@csrf_exempt
def get_vendor_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters=''):
    lis = ['vendor__name', 'sku__wms_code', 'sku__sku_desc', 'sku__sku_category', 'total']
    search_params = get_filtered_params(filters, lis)
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    if search_term:
        master_data = VendorStock.objects.exclude(receipt_number=0).values('vendor__name', 'sku__wms_code', 'sku__sku_desc',
                                         'sku__sku_category').distinct().annotate(total=Sum('quantity')).\
                                         filter(Q(sku__wms_code__icontains=search_term) | Q(sku__sku_desc__icontains=search_term) |
                                         Q(sku__sku_category__icontains=search_term) | Q(total__icontains=search_term), sku__user=user.id,
                                         status=1, quantity__gt=0, **search_params)

    else:
        master_data = VendorStock.objects.exclude(receipt_number=0).values('vendor__name', 'sku__wms_code', 'sku__sku_desc',
                                          'sku__sku_category').distinct().annotate(total=Sum('quantity')).filter(quantity__gt=0,
                                          sku__user = user.id, **search_params).order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append(OrderedDict(( ('Vendor Name', data['vendor__name']), ('WMS Code', data['sku__wms_code']),
                                                 ('Product Description', data['sku__sku_desc']), ('SKU Category', data['sku__sku_category']),
                                                 ('Quantity', get_decimal_limit(user.id, data['total'])), ('DT_RowId', data['sku__wms_code'])
                                              )))
@csrf_exempt
@get_admin_user
def warehouse_headers(request, user=''):
    admin_user_id = ''
    admin_user_name = ''
    warehouses = UserGroups.objects.filter(admin_user_id=user.id).values_list('user_id',flat=True)
    ware_list = list(User.objects.filter(id__in=warehouses).values_list('username', flat=True))
    ware_list.append(request.user.username)
    header = ["SKU Code", "SKU Brand", "SKU Description", "SKU Category"]
    user_groups = UserGroups.objects.filter(Q(admin_user_id=user.id)|Q(user_id=user.id))
    if user_groups:
        admin_user_id = user_groups[0].admin_user_id
        admin_user_name = user_groups[0].admin_user.username
    else:
        admin_user_id = user.id
        admin_user_name = user.username
    user_groups = list(UserGroups.objects.filter(admin_user_id=admin_user_id).values_list('user__username',flat=True))
    headers = header + [admin_user_name] + user_groups

    return HttpResponse(json.dumps(headers))

