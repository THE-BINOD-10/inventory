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
from utils import *

log = init_logger('logs/stock_locator.log')


@csrf_exempt
def get_stock_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['sku__wms_code', 'sku__sku_desc', 'sku__sku_brand', 'sku__sku_category', 'total', 'total', 'total',
           'sku__measurement_type']
    lis1 = ['product_code__wms_code', 'product_code__sku_desc', 'product_code__sku_brand', 'product_code__sku_category',
            'total',
            'total', 'total', 'product_code__measurement_type']
    sort_cols = ['WMS Code', 'Product Description', 'SKU Brand', 'SKU Category', 'Quantity', 'Reserved Quantity',
                 'Total Quantity',
                 'Unit of Measurement']
    lis2 = ['wms_code', 'sku_desc', 'sku_brand', 'sku_category', 'threshold_quantity', 'threshold_quantity',
            'threshold_quantity', 'measurement_type']
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
    extra_headers = list(
        ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    status_track = StatusTracking.objects.filter(status_type='JO', status_id__in=job_ids,
                                                 status_value__in=extra_headers, quantity__gt=0). \
        values('status_value', 'status_id').distinct().annotate(total=Sum('quantity'))
    status_ids = map(lambda d: d.get('status_id', ''), status_track)

    search_params['sku_id__in'] = sku_master_ids
    search_params1['product_code_id__in'] = sku_master_ids

    reserved_instances = PicklistLocation.objects.filter(status=1, stock__sku__user=user.id).values(
        'stock__sku__wms_code'). \
        distinct().annotate(reserved=Sum('reserved'))
    raw_res_instances = RMLocation.objects.filter(status=1, stock__sku__user=user.id). \
        values('material_picklist__jo_material__material_code__wms_code').distinct(). \
        annotate(rm_reserved=Sum('reserved'))

    reserveds = map(lambda d: d['stock__sku__wms_code'], reserved_instances)
    reserved_quantities = map(lambda d: d['reserved'], reserved_instances)
    raw_reserveds = map(lambda d: d['material_picklist__jo_material__material_code__wms_code'], raw_res_instances)
    raw_reserved_quantities = map(lambda d: d['rm_reserved'], raw_res_instances)
    temp_data['totalQuantity'] = 0
    temp_data['totalReservedQuantity'] = 0
    temp_data['totalAvailableQuantity'] = 0

    if search_term:
        master_data = StockDetail.objects.exclude(receipt_number=0).values_list('sku__wms_code', 'sku__sku_desc',
                                                                                'sku__sku_category',
                                                                                'sku__sku_brand'). \
            distinct().annotate(total=Sum('quantity')).filter(Q(sku__wms_code__icontains=search_term) |
                                                              Q(sku__sku_desc__icontains=search_term) | Q(
            sku__sku_category__icontains=search_term) |
                                                              Q(total__icontains=search_term), sku__user=user.id,
                                                              status=1, **search_params)
        wms_codes = map(lambda d: d[0], master_data)
        master_data1 = job_order.exclude(product_code__wms_code__in=wms_codes).filter(
            Q(product_code__wms_code__icontains=search_term) |
            Q(product_code__sku_desc__icontains=search_term) | Q(product_code__sku_category__icontains=search_term),
            **search_params1).values_list('product_code__wms_code',
                                          'product_code__sku_desc', 'product_code__sku_category',
                                          'product_code__sku_brand').distinct()
        quantity_master_data = master_data.aggregate(Sum('total'))
        master_data = list(chain(master_data, master_data1))


    else:
        master_data = StockDetail.objects.exclude(receipt_number=0).values_list('sku__wms_code', 'sku__sku_desc',
                                                                                'sku__sku_category',
                                                                                'sku__sku_brand').distinct(). \
            annotate(total=Sum('quantity')).filter(sku__user=user.id, **search_params). \
            order_by(order_data)
        wms_codes = map(lambda d: d[0], master_data)
        quantity_master_data = master_data.aggregate(Sum('total'))
        master_data1 = job_order.exclude(product_code__wms_code__in=wms_codes).filter(**search_params1).values_list(
            'product_code__wms_code',
            'product_code__sku_desc', 'product_code__sku_category', 'product_code__sku_brand').distinct()
        master_data = list(chain(master_data, master_data1))
    zero_quantity = sku_master.exclude(wms_code__in=wms_codes).filter(user=user.id)
    if search_params2:
        zero_quantity = zero_quantity.filter(**search_params2)
    if search_term:
        zero_quantity = zero_quantity.filter(
            Q(wms_code__icontains=search_term) | Q(sku_desc__icontains=search_term) | Q(
                sku_category__icontains=search_term))

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
            diff = total - total_reserved
        if not diff < 0:
            total_available_quantity = diff
        temp_data['totalAvailableQuantity'] += total_available_quantity

    temp_data['totalReservedQuantity'] = int(temp_data['totalReservedQuantity'])

    temp_data['totalAvailableQuantity'] = int(temp_data['totalAvailableQuantity'])

    reserveds = map(lambda d: d['stock__sku__wms_code'], reserved_instances)
    reserved_quantities = map(lambda d: d['reserved'], reserved_instances)
    raw_reserveds = map(lambda d: d['material_picklist__jo_material__material_code__wms_code'], raw_res_instances)
    raw_reserved_quantities = map(lambda d: d['rm_reserved'], raw_res_instances)
    # temp_data['totalQuantity'] = sum([data[4] for data in master_data])
    for ind, data in enumerate(master_data[start_index:stop_index]):
        reserved = 0
        # total = data[4] if len(data) > 4 else 0
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
        temp_data['aaData'].append(OrderedDict((('WMS Code', data[0]), ('Product Description', data[1]),
                                                ('SKU Category', data[2]), ('SKU Brand', data[3]),
                                                ('Available Quantity', quantity),
                                                ('Reserved Quantity', reserved), ('Total Quantity', total),
                                                ('Unit of Measurement', sku.measurement_type),
                                                ('DT_RowId', data[0]))))

        # sort_col = sort_cols[col_num]
        # if order_term == 'asc':
        #    temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
        # else:
        #    temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)
        # temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


@csrf_exempt
def get_stock_summary_size(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters,
                           user_dict={}):
    """ This function delivers the alternate view of stock summary page """
    log.info(" ------------stock summary alternate view started ------------------")
    st_time = datetime.datetime.now()
    default_size = ['S', 'M', 'L', 'XL', 'XXL']
    size_master_objs = SizeMaster.objects.filter(user=user.id)

    size_names = size_master_objs.values_list('size_name', flat=True)
    size_name = request.POST.get("size_name", 'Default')
    lis = ['sku_class', 'style_name', 'sku_brand', 'sku_category']
    all_dat = ['SKU Class', 'Style Name', 'Brand', 'SKU Category']
    search_params = get_filtered_params(filters, lis)
    all_sizes = size_master_objs.filter(size_name=size_name)
    sizes = []

    if all_sizes:
        sizes = all_sizes[0].size_value.split("<<>>")
    else:
        sizes = default_size

    all_dat.extend(sizes)
    sort_col = all_dat[col_num]
    log.info(sort_col)
    log.info(sizes)
    try:
        if search_term:
            sku_classes = SKUMaster.objects.values('sku_class', 'style_name', 'sku_brand',
                                                   'sku_category').distinct().filter(
                Q(sku_class__icontains=search_term) | Q(style_name__icontains=search_term) | Q(
                    sku_brand__icontains=search_term) | Q(sku_category__icontains=search_term), user=user.id,
                sku_size__in=sizes, **search_params)

        else:
            sku_classes = SKUMaster.objects.filter(user=user.id, sku_size__in=sizes, **search_params).values(
                'sku_class', 'style_name', 'sku_brand', 'sku_category').distinct()
        stock_detail_objs = StockDetail.objects.exclude(receipt_number=0).filter(sku__user=user.id,
                                                                                 sku__sku_size__in=sizes).values(
            'sku__sku_class', 'sku__sku_size'). \
            distinct().annotate(total_sum=Sum('quantity'))
        stock_detail_dict = {}
        for obj in stock_detail_objs:
            if obj['sku__sku_class'] in stock_detail_dict.keys():
                if obj['sku__sku_size'] in stock_detail_dict[obj['sku__sku_class']].keys():
                    stock_detail_dict[obj['sku__sku_class']][obj['sku__sku_size']].append(obj['total_sum'])
                else:
                    stock_detail_dict[obj['sku__sku_class']].update({obj['sku__sku_size']: [obj['total_sum']]})
            else:
                stock_detail_dict.update({obj['sku__sku_class']: {obj['sku__sku_size']: [obj['total_sum']]}})

        temp_data['recordsTotal'] = sku_classes.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']

        all_data = []
        for sku_class in sku_classes:
            size_dict = {}
            st_stock_objs = stock_detail_dict.get(sku_class['sku_class'], {})
            for size in sizes:
                log.info(st_stock_objs)
                log.info(size)
                qty = st_stock_objs.get(size, [])
                if qty:
                    quant = sum(qty)
                else:
                    quant = 0
                size_dict.update({size: quant})

            data = OrderedDict((('SKU Class', sku_class['sku_class']), ('Style Name', sku_class['style_name']),
                                ('SKU Category', sku_class['sku_category']), ('Brand', sku_class['sku_brand'])))

            data.update(size_dict)
            all_data.append(data)

        if order_term == 'asc':
            data_list = sorted(all_data, key=itemgetter(sort_col))
        else:
            data_list = sorted(all_data, key=itemgetter(sort_col), reverse=True)

        data_list = data_list[start_index: stop_index]

        log.info(data_list)
        temp_data['aaData'].extend(data_list)

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(e)

    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("total time -- %s" % (duration))
    log.info("process completed")


@csrf_exempt
def get_stock_summary_size_excel(filter_params, temp_data, headers, user, request):
    """ This function delivers the excel of alternate view of stock summary page """
    log.info(" ------------Stock Summary Alternate view excel started ------------------")
    st_time = datetime.datetime.now()
    import xlsxwriter
    default_size = ['S', 'M', 'L', 'XL', 'XXL']
    # all_dat = ['SKU Class', 'Style Name', 'Brand', 'SKU Category']
    stock_detail_objs = StockDetail.objects.exclude(receipt_number=0).filter(sku__user=user.id)
    stock_detail_dict = {}

    stock_detail_objs = StockDetail.objects.exclude(receipt_number=0).filter(sku__user=user.id).values('sku__sku_class',
                                                                                                       'sku__sku_size'). \
        distinct().annotate(total_sum=Sum('quantity'))

    for obj in stock_detail_objs:
        if obj['sku__sku_class'] in stock_detail_dict.keys():
            if obj['sku__sku_size'] in stock_detail_dict[obj['sku__sku_class']].keys():
                stock_detail_dict[obj['sku__sku_class']][obj['sku__sku_size']].append(obj['total_sum'])
            else:
                stock_detail_dict[obj['sku__sku_class']].update({obj['sku__sku_size']: [obj['total_sum']]})
        else:
            stock_detail_dict.update({obj['sku__sku_class']: {obj['sku__sku_size']: [obj['total_sum']]}})

    all_sizes_obj = SizeMaster.objects.filter(user=user.id)
    all_size_names = list(all_sizes_obj.values_list('size_name', flat=True))
    all_size_names.append('DEFAULT')
    try:
        path = 'static/excel_files/' + str(user.id) + 'Stock_Summary_Alternative.xlsx'
        if not os.path.exists('static/excel_files/'):
            os.makedirs('static/excel_files/')
        workbook = xlsxwriter.Workbook(path)
        for i, siz_nam in enumerate(all_size_names):

            worksheet = workbook.add_worksheet(siz_nam)
            bold = workbook.add_format({'bold': True})

            all_dat = ['SKU Class', 'Style Name', 'Brand', 'SKU Category']
            sizes = []
            all_sizes = all_sizes_obj.filter(size_name=siz_nam)
            if all_sizes:
                sizes = all_sizes[0].size_value.split("<<>>")
            else:
                sizes = default_size

            all_dat.extend(sizes)
            # sort_col = all_dat[col_num]
            log.info(sizes)
            for n, header in enumerate(all_dat):
                worksheet.write(0, n, header, bold)
            sku_classes = SKUMaster.objects.filter(user=user.id, sku_size__in=sizes).values('sku_class', 'style_name',
                                                                                            'sku_brand',
                                                                                            'sku_category').distinct()

            for row, sku_class in enumerate(sku_classes, 1):
                size_dict = {}
                st_stock_objs = stock_detail_dict.get(sku_class['sku_class'], {})
                data = [sku_class['sku_class'], sku_class['style_name'], sku_class['sku_brand'],
                        sku_class['sku_category']]
                for size in sizes:
                    log.info(st_stock_objs)
                    log.info(size)
                    qty = st_stock_objs.get(size, [])
                    if qty:
                        quant = sum(qty)
                    else:
                        quant = 0
                    # size_dict.update({size : quant})

                    data.append(quant)

                for col, data in enumerate(data):
                    worksheet.write(row, col, data)

        workbook.close()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(e)

    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("total time -- %s" % (duration))
    log.info("process completed")
    return '../' + path


def get_stock_counts(quantity, single_sku):
    stock_count = []
    for single_data in quantity:
        purch = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(
            open_po__sku__user=single_data['user'], open_po__sku__sku_code=single_sku).values(
            'open_po__sku__sku_code').annotate(total_order=Sum('open_po__order_quantity'),
                                               total_received=Sum('received_quantity'))
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
                reserved_da = PicklistLocation.objects.filter(stock__sku__sku_code=single_data['sku_code'],
                                                              stock__sku__user=single_data['user'], status=1).aggregate(
                    Sum('reserved'))['reserved__sum']
                if not reserved_da:
                    available = single_data['quantity']
                    reserved = 0
                else:
                    available = single_data['quantity'] - reserved_da
                    reserved = reserved_da
        stock_count.append(
            {'available': available, 'name': single_data['name'], 'transit': trans_quantity, 'reserved': reserved})
    return stock_count


@fn_timer
def get_quantity_data(user_groups, sku_codes_list):
    ret_list = []

    for user in user_groups:
        user_sku_codes = SKUMaster.objects.filter(user=user)
        ware = User.objects.filter(id=user).values_list('username', flat=True)[0]
        stock_user_dict = dict(StockDetail.objects.filter(sku__user=user). \
                               exclude(location__zone__zone='DAMAGED_ZONE').values_list('sku__sku_code').distinct(). \
                               annotate(total=Sum('quantity')))
        purch_dict = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).values(
            'open_po__sku__sku_code'). \
            annotate(total_order=Sum('open_po__order_quantity'), total_received=Sum('received_quantity'))
        pick_reserved_dict = dict(PicklistLocation.objects.filter(stock__sku__user=user, status=1, reserved__gt=0). \
                                  values_list('stock__sku__sku_code').annotate(Sum('reserved')))
        raw_reserved_dict = dict(
            RMLocation.objects.filter(status=1, material_picklist__jo_material__material_code__user=user). \
            values_list('material_picklist__jo_material__material_code__wms_code').distinct(). \
            annotate(rm_reserved=Sum('reserved')))
        purchases = map(lambda d: d['open_po__sku__sku_code'], purch_dict)
        total_order_dict = dict(zip(purchases, map(lambda d: d['total_order'], purch_dict)))
        total_received_dict = dict(zip(purchases, map(lambda d: d['total_received'], purch_dict)))
        for single_sku in sku_codes_list:
            exist = user_sku_codes.filter(sku_code=single_sku)
            if not exist:
                available = 'No SKU'
                reserved = 0
                ret_list.append({'available': available, 'name': ware, 'transit': 0, 'reserved': reserved, 'user': user,
                                 'name': ware,
                                 'sku_code': single_sku})
                continue
            trans_quantity = 0
            if single_sku in purchases:
                trans_quantity = total_order_dict[single_sku] - total_received_dict[single_sku]
            quantity = stock_user_dict.get(single_sku, 0)
            pic_reserved = pick_reserved_dict.get(single_sku, 0)
            raw_reserved = raw_reserved_dict.get(single_sku, 0)
            available = quantity - pic_reserved
            ret_list.append({'available': available, 'name': ware, 'transit': trans_quantity, 'reserved': pic_reserved,
                             'user': user,
                             'name': ware, 'sku_code': single_sku})
    return ret_list


def get_available_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    data, temp_data, other, da = get_warehouses_stock(start_index, stop_index, temp_data, search_term, order_term,
                                                      col_num, request, user, filters)

    list_da = {}

    for i in da:
        if i['available'] is None:
            i['available'] = 0
        list_da[i['ware']] = i['available']

    temp_data['ware_list'] = list_da
    for one_data, sku_det in zip(data, other['rem']):
        header = other['header']
        single_sku = sku_det['single_sku']
        sku_desc = sku_det['sku_desc']
        sku_brand = sku_det['sku_brand']
        sku_category = sku_det['sku_category']
        var = (OrderedDict(
            ((header[0], single_sku), (header[1], sku_brand), (header[2], sku_desc), (header[3], sku_category))))
        for single in one_data:
            available = single['available']
            name = single['name']
            var[name] = available
        temp_data['aaData'].append(var)


def get_availintra_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    data, temp_data, other, da = get_warehouses_stock(start_index, stop_index, temp_data, search_term, order_term,
                                                      col_num, request, user, filters)

    list_da = {}
    for i in da:
        if i['available'] is None:
            i['available'] = 0
        if i['transit'] is None:
            i['transit'] = 0
        list_da[i['ware']] = i['available'] + i['transit']

    temp_data['ware_list'] = list_da
    for one_data, sku_det in zip(data, other['rem']):
        header = other['header']
        single_sku = sku_det['single_sku']
        sku_desc = sku_det['sku_desc']
        sku_brand = sku_det['sku_brand']
        sku_category = sku_det['sku_category']
        var = (OrderedDict(
            ((header[0], single_sku), (header[1], sku_brand), (header[2], sku_desc), (header[3], sku_category))))
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
    data, temp_data, other, da = get_warehouses_stock(start_index, stop_index, temp_data, search_term, order_term,
                                                      col_num, request, user, filters)

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
    for one_data, sku_det in zip(data, other['rem']):
        header = other['header']
        single_sku = sku_det['single_sku']
        sku_desc = sku_det['sku_desc']
        sku_brand = sku_det['sku_brand']
        sku_category = sku_det['sku_category']
        var = (OrderedDict(
            ((header[0], single_sku), (header[1], sku_brand), (header[2], sku_desc), (header[3], sku_category))))
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

    warehouses = UserGroups.objects.filter(admin_user_id=user.id).values_list('user_id', flat=True)
    ware_list = list(User.objects.filter(id__in=warehouses).values_list('username', flat=True))
    ware_list.append(user.username)
    header = ["SKU Code", "SKU Brand", "SKU Description", "SKU Category"]
    headers = header + ware_list

    user_groups = UserGroups.objects.filter(Q(admin_user_id=user.id) | Q(user_id=user.id))
    if user_groups:
        admin_user_id = user_groups[0].admin_user_id
    else:
        admin_user_id = user.id
    user_groups = list(UserGroups.objects.filter(admin_user_id=admin_user_id).values_list('user_id', flat=True))
    user_groups.append(admin_user_id)
    sku_master = SKUMaster.objects.filter(user__in=user_groups, **search_params)
    if col_num <= 3:
        sku_master = sku_master.order_by(order_data)
    if search_term:
        sku_master = sku_master.filter(Q(sku_code__icontains=search_term) | Q(sku_desc__icontains=search_term) | Q(
            sku_brand__icontains=search_term), user__in=user_groups)
    sku_codes = sku_master.values_list('sku_code', flat=True).distinct()
    temp_data['ware_list'] = ''
    temp_data['recordsTotal'] = sku_codes.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    other_data['header'] = header
    other_data['rem'] = []
    data = get_aggregate_data(user_groups, list(sku_codes)[0:temp_data['recordsTotal']])

    sku_master_dat = sku_master.values('sku_code', 'sku_desc', 'sku_brand', 'sku_category').distinct()
    sku_descs = dict(zip(map(lambda d: d['sku_code'], sku_master_dat), map(lambda d: d['sku_desc'], sku_master_dat)))
    sku_brands = dict(zip(map(lambda d: d['sku_code'], sku_master_dat), map(lambda d: d['sku_brand'], sku_master_dat)))
    sku_categorys = dict(
        zip(map(lambda d: d['sku_code'], sku_master_dat), map(lambda d: d['sku_category'], sku_master_dat)))
    user_quantity_dict = get_quantity_data(user_groups, sku_codes[start_index:stop_index])
    for single_sku in sku_codes[start_index:stop_index]:
        sku_brand = sku_brands.get(single_sku, '')
        sku_desc = sku_descs.get(single_sku, '')
        sku_category = sku_categorys.get(single_sku, '')
        quantity = filter(lambda d: d['sku_code'] == single_sku, user_quantity_dict)
        data_to_send.append(quantity)
        other_data['rem'].append(
            {'single_sku': single_sku, 'sku_brand': sku_brand, 'sku_desc': sku_desc, 'sku_category': sku_category})
    return data_to_send, temp_data, other_data, data


@fn_timer
def get_aggregate_data(user_groups, sku_list):
    data = []
    users_objs = User.objects.filter(id__in=user_groups)

    for user in users_objs:
        available = 0
        total = \
        StockDetail.objects.exclude(receipt_number=0).filter(sku__wms_code__in=sku_list, sku__user=user.id).aggregate(
            Sum('quantity'))['quantity__sum']
        reserved = PicklistLocation.objects.filter(stock__sku__sku_code__in=sku_list, stock__sku__user=user.id,
                                                   status=1).aggregate(Sum('reserved'))['reserved__sum']
        purch = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(
            open_po__sku__user=user.id, open_po__sku__sku_code__in=sku_list).values('open_po__sku__sku_code').annotate(
            total_order=Sum('open_po__order_quantity'), total_received=Sum('received_quantity'))
        raw_reserved = RMLocation.objects.filter(status=1, stock__sku__user=user.id). \
            aggregate(Sum('reserved'))['reserved__sum']
        total_order = sum(map(lambda d: d['total_order'], purch))
        total_received = sum(map(lambda d: d['total_received'], purch))
        trans_quantity = float(total_order) - float(total_received)
        trans_quantity = round(trans_quantity, 2)
        if total:
            available = total
        if not reserved:
            reserved = 0
        if raw_reserved:
            reserved += raw_reserved
        available -= reserved
        if available < 0:
            available = 0
        available = round(available, 2)
        reserved = round(reserved, 2)
        ware_name = user.username
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
        master_data = SKUStock.objects.filter(
            Q(sku__sku_code__icontains=search_term) | Q(total_quantity__icontains=search_term) | Q(
                online_quantity__icontains=search_term) | Q(offline_quantity__icontains=search_term))
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        reserved_quantity = \
        PicklistLocation.objects.filter(picklist__status__icontains='open', picklist__order__sku_id=data.sku_id,
                                        status=1).aggregate(Sum('quantity'))['quantity__sum']
        if not reserved_quantity:
            reserved_quantity = 0

        total_quantity = StockDetail.objects.filter(sku_id=data.sku_id, quantity__gt=0).aggregate(Sum('quantity'))[
            'quantity__sum']
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
        temp_data['aaData'].append(
            {'SKU Code': data.sku.sku_code, 'Total Quantity': quantity, 'Suggested Online Quantity': online_quantity,
             'Current Online Quantity': data.online_quantity, 'Offline Quantity': data.offline_quantity,
             'DT_RowAttr': {'data-id': data.id}})


@csrf_exempt
def get_stock_detail_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                             filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['receipt_number', 'receipt_date', 'sku_id__wms_code', 'sku_id__sku_desc', 'location__zone__zone',
           'location__location', 'quantity',
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
        master_data = StockDetail.objects.exclude(receipt_number=0).filter(Q(receipt_number__icontains=search_term) |
                                                                           Q(sku__wms_code__icontains=search_term) | Q(
            quantity__icontains=search_term) |
                                                                           Q(
                                                                               location__zone__zone__icontains=search_term) | Q(
            sku__sku_code__icontains=search_term) |
                                                                           Q(sku__sku_desc__icontains=search_term) | Q(
            location__location__icontains=search_term),
                                                                           sku__user=user.id).filter(
            **search_params).order_by(order_data)

    else:
        master_data = StockDetail.objects.exclude(receipt_number=0).filter(sku__user=user.id, **search_params). \
            order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        pallet_switch = get_misc_value('pallet_switch', user.id)
        _date = get_local_date(user, data.receipt_date, True)
        _date = _date.strftime("%d %b, %Y")
        if pallet_switch == 'true':
            pallet_code = ''
            if data.pallet_detail:
                pallet_code = data.pallet_detail.pallet_code
            temp_data['aaData'].append(OrderedDict((('Receipt ID', data.receipt_number), ('DT_RowClass', 'results'),
                                                    ('Receipt Date', _date), ('SKU Code', data.sku.sku_code),
                                                    ('WMS Code', data.sku.wms_code),
                                                    ('Product Description', data.sku.sku_desc),
                                                    ('Zone', data.location.zone.zone),
                                                    ('Location', data.location.location),
                                                    ('Quantity', get_decimal_limit(user.id, data.quantity)),
                                                    ('Pallet Code', pallet_code), ('Receipt Type', data.receipt_type))))
        else:
            temp_data['aaData'].append(OrderedDict((('Receipt ID', data.receipt_number), ('DT_RowClass', 'results'),
                                                    ('Receipt Date', _date), ('SKU Code', data.sku.sku_code),
                                                    ('WMS Code', data.sku.wms_code),
                                                    ('Product Description', data.sku.sku_desc),
                                                    ('Zone', data.location.zone.zone),
                                                    ('Location', data.location.location),
                                                    ('Quantity', get_decimal_limit(user.id, data.quantity)),
                                                    ('Receipt Type', data.receipt_type))))


@csrf_exempt
def get_cycle_confirmed(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                        filters=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['cycle', 'date_only']
    if search_term:
        cycle_data = CycleCount.objects.filter(sku_id__in=sku_master_ids).filter(Q(cycle__icontains=search_term) |
                                                                                 Q(creation_date__regex=search_term),
                                                                                 sku__user=user.id, status=1).order_by(
            lis[col_num]).values('cycle').distinct()
    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        cycle_data = CycleCount.objects.filter(status='1', sku__user=user.id, sku_id__in=sku_master_ids).values(
            'cycle').distinct(). \
            annotate(date_only=Cast('creation_date', DateField())).order_by(order_data)
    else:
        cycle_data = CycleCount.objects.filter(status='1', sku__user=user.id, sku_id__in=sku_master_ids).values(
            'cycle').distinct()

    temp_data['recordsTotal'] = cycle_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    all_cycle_counts = CycleCount.objects.filter(sku__user=user.id, status=1).values('cycle', 'creation_date')
    for item in cycle_data[start_index:stop_index]:
        creation_date = all_cycle_counts.filter(cycle=item['cycle'])[0]['creation_date']
        temp_data['aaData'].append(
            OrderedDict((('Cycle Count ID', item['cycle']), ('Date', get_local_date(request.user, creation_date)),
                         ('DT_RowClass', 'results'), ('DT_RowId', item['cycle']))))


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
            data_dict = {'cycle_id': positive.id, 'adjusted_location': '', 'adjusted_quantity': positive.seen_quantity,
                         'reason': '', 'creation_date': datetime.datetime.now(),
                         'updation_date': datetime.datetime.now()}
            data = InventoryAdjustment.objects.filter(cycle_id=positive.id)
            if not data:
                data = InventoryAdjustment(**data_dict)
                data.save()
            all_data.append(positive)
        temp_data['recordsTotal'] = len(all_data)
        temp_data['recordsFiltered'] = len(all_data)
        for positive in all_data[start_index:stop_index]:
            checkbox = "<input type='hidden' name='%s' value='%s'>" % (positive.id, positive.id)
            temp_data['aaData'].append(
                {'': checkbox, 'Location': positive.location.location, 'WMS Code': positive.sku.wms_code,
                 'Description': positive.sku.sku_desc, 'Total Quantity': positive.quantity,
                 'Physical Quantity': positive.seen_quantity, 'Reason': "<input type='text' name='reason'>",
                 'DT_RowClass': 'results', 'id': data_id})
            data_id += 1

    else:
        for items in move_items[start_index:stop_index]:
            data_dict = {'cycle_id': items[0].id, 'adjusted_location': items[1].location_id,
                         'adjusted_quantity': items[2], 'reason': '', 'creation_date': datetime.datetime.now(),
                         'updation_date': datetime.datetime.now()}
            data = InventoryAdjustment.objects.filter(cycle_id=items[0].id)
            if not data:
                data = InventoryAdjustment(**data_dict)
                data.save()
                data = InventoryAdjustment.objects.filter(cycle_id=items[0].id)

            checkbox = "<input type='checkbox' name='%s' value='%s'>" % (items[0].id, items[1].id)
            temp_data['aaData'].append(
                {'': checkbox, 'Source Location': items[0].location.location, 'WMS Code': items[0].sku.wms_code,
                 'Description': items[0].sku.sku_desc, 'Destination Location': items[1].location.location,
                 'Move Quantity': items[2], 'Reason': '', 'DT_RowClass': 'results', 'id': data_id})
            data_id += 1


@csrf_exempt
@login_required
@get_admin_user
def confirm_move_location_inventory(request, user=''):
    source_loc = request.POST['source_loc']
    dest_loc = request.POST['dest_loc']
    reason = request.POST.get('reason', '')
    source = LocationMaster.objects.filter(location=source_loc, zone__user=user.id)
    if not source:
        return HttpResponse('Invalid Source')
    dest = LocationMaster.objects.filter(location=dest_loc, zone__user=user.id)
    if not dest:
        return HttpResponse('Invalid Destination')
    log.info("Move location inventory:\nSource:%s, Dest: %s, Reason: %s"%(source_loc, dest_loc, reason))
    try:
        sku_dict = StockDetail.objects.filter(location_id=source[0].id, sku__user=user.id, quantity__gt=0)\
                                      .values("sku_id", "quantity")
        log.info("Moving SKUs: %s" %(str(list(sku_dict))))
        stocks = StockDetail.objects.filter(location_id=source[0].id, sku__user=user.id, quantity__gt=0)\
                                    .update(location_id=dest[0].id)
    except:
        import traceback
        log.debug(traceback.format_exc())

    """for stock in stocks:
        data = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
        if not data:
            cycle_id = 1
        else:
            cycle_id = data[0].cycle + 1
        stock.location = dest[0]
        stock.save()

        quantity = stock.quantity
        sku_id = stock.sku.id
        data_dict = copy.deepcopy(CYCLE_COUNT_FIELDS)
        data_dict['cycle'] = cycle_id
        data_dict['sku_id'] = sku_id
        data_dict['location_id'] = source[0].id
        data_dict['quantity'] = quantity
        data_dict['seen_quantity'] = 0
        data_dict['status'] = 0
        data_dict['creation_date'] = datetime.datetime.now()
        data_dict['updation_date'] = datetime.datetime.now()

        cycle_instance = CycleCount.objects.filter(cycle=cycle_id, location_id=source[0].id, sku_id=sku_id)
        if not cycle_instance:
            dat = CycleCount(**data_dict)
            dat.save()
        else:
            cycle_instance = cycle_instance[0]
            cycle_instance.quantity = float(cycle_instance.quantity) + quantity
            cycle_instance.save()
        data_dict['location_id'] = dest[0].id
        data_dict['quantity'] = quantity
        cycle_instance = CycleCount.objects.filter(cycle=cycle_id, location_id=dest[0].id, sku_id=sku_id)
        if not cycle_instance:
            dat = CycleCount(**data_dict)
            dat.save()
        else:
            cycle_instance = cycle_instance[0]
            cycle_instance.quantity = float(cycle_instance.quantity) + quantity
            cycle_instance.save()

        data = copy.deepcopy(INVENTORY_FIELDS)
	data['cycle_id'] = cycle_id
	data['adjusted_location'] = dest[0].id
	data['adjusted_quantity'] = quantity
        data['reason'] = reason
	data['creation_date'] = datetime.datetime.now()
	data['updation_date'] = datetime.datetime.now()

	inventory_instance = InventoryAdjustment.objects.filter(cycle_id=cycle_id, adjusted_location=dest[0].id)
	if not inventory_instance:
	    dat = InventoryAdjustment(**data)
	    dat.save()
	else:
	    inventory_instance = inventory_instance[0]
	    inventory_instance.adjusted_quantity += float(inventory_instance.adjusted_quantity) + quantity
	    inventory_instance.save()"""

    return HttpResponse('Moved Successfully')


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
    check = False
    sku_id = check_and_return_mapping_id(wms_code, "", user, check)

    if sku_id:
        wms_code = SKUMaster.objects.get(id=sku_id).wms_code

    source_loc = request.GET['source_loc']
    dest_loc = request.GET['dest_loc']
    quantity = request.GET['quantity']
    seller_id = request.GET.get('seller_id', '')
    status = move_stock_location(cycle_id, wms_code, source_loc, dest_loc, quantity, user, seller_id)
    if 'success' in status.lower():
        update_filled_capacity([source_loc, dest_loc], user.id)

    return HttpResponse(status)


@csrf_exempt
def get_cycle_count(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    search_params = {}
    lis = ['sku__wms_code', 'location__zone__zone', 'location__location', 'total']
    col_num = col_num - 1
    order_data = lis[col_num]
    search_parameters = get_filtered_params(filters, lis)
    for key, value in search_parameters.iteritems():
        # if key.replace('__icontains', '') in lis[:3]:
        # key = key.replace('contains', 'exact')
        search_params[key] = value

    search_params['sku_id__in'] = sku_master_ids
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        cycle_data = StockDetail.objects.values('sku__wms_code', 'location__location',
                                                'location__zone__zone').distinct(). \
            annotate(total=Sum('quantity')).filter(Q(sku__wms_code__icontains=search_term) |
                                                   Q(location__zone__zone__icontains=search_term) | Q(
            location__location__icontains=search_term) |
                                                   Q(total__icontains=search_term), sku__user=user.id, status=1,
                                                   quantity__gt=0).filter(**search_params)
    else:
        if 'quantity' in order_data:
            order_data = order_data.replace('quantity', 'total')
        cycle_data = StockDetail.objects.filter(status=1, sku__user=user.id, quantity__gt=0).values('sku__wms_code',
                                                                                                    'location__location',
                                                                                                    'location__zone__zone').distinct().annotate(
            total=Sum('quantity')).filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = len(cycle_data)
    temp_data['recordsFiltered'] = len(cycle_data)

    index = 1
    for data in cycle_data[start_index:stop_index]:
        quantity = data['total']
        temp_data['aaData'].append({'wms_code': data['sku__wms_code'], 'zone': data['location__zone__zone'],
                                    'location': data['location__location'],
                                    'quantity': get_decimal_limit(user.id, quantity), 'id': index})
        index = index + 1


@csrf_exempt
@login_required
@get_admin_user
def confirm_cycle_count(request, user=''):
    stocks = []
    total_data = []
    search_params = {}
    stock_data = []
    myDict = dict(request.GET.iterlists())
    for i in range(0, len(myDict['wms_code'])):
        search_params['sku__user'] = user.id
        search_params['status'] = 1
        search_params['quantity__gt'] = 0
        if myDict['wms_code'][i]:
            search_params['sku_id__wms_code__icontains'] = myDict['wms_code'][i]
        if myDict['zone'][i]:
            search_params['location__zone__zone__icontains'] = myDict['zone'][i]
        if myDict['location'][i]:
            search_params['location_id__location__icontains'] = myDict['location'][i]
        if myDict['quantity'][i]:
            search_params['total__contains'] = myDict['quantity'][i]

        if search_params:
            stock_values = StockDetail.objects.values('sku_id', 'location_id', 'location__zone_id').distinct().annotate(
                total=Sum('quantity')).filter(**search_params)
            for value in stock_values:
                del value['total']
                stocks = list(chain(stocks, (StockDetail.objects.filter(**value))))

    if 'search_term' in request.GET.keys():
        search_term = request.GET['search_term']
        if search_term:
            stocks = StockDetail.objects.filter(Q(sku__wms_code__icontains=search_term, status=1, quantity__gt=0) |
                                                Q(location__zone__zone__icontains=search_term, status=1,
                                                  quantity__gt=0) |
                                                Q(location__location__icontains=search_term, status=1, quantity__gt=0) |
                                                Q(quantity__icontains=search_term, status=1, quantity__gt=0),
                                                sku__user=user.id)

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
        data = CycleCount.objects.get(id=data_id, sku__user=user.id)
        data.seen_quantity = count
        data.status = 'checked'
        data.save()
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def get_id_cycle(request, user=''):
    cycle_data = CycleCount.objects.filter(cycle=request.GET['data_id'], sku__user=user.id)
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
    stock_data = StockDetail.objects.exclude(receipt_number=0).filter(sku_id__wms_code=wms_code, sku__user=user.id)
    production_stages = []
    load_unit_handle = ""
    if stock_data:
        load_unit_handle = stock_data[0].sku.load_unit_handle
    zones_data, available_quantity = get_sku_stock_summary(stock_data, load_unit_handle, user)

    job_order = JobOrder.objects.filter(product_code__user=user.id, product_code__wms_code=wms_code,
                                        status__in=['grn-generated', 'pick_confirm', 'partial_pick'])
    job_codes = job_order.values_list('job_code', flat=True).distinct()
    extra_headers = list(
        ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    for job_code in job_codes:
        job_ids = job_order.filter(job_code=job_code).values_list('id', flat=True)
        pallet_mapping = PalletMapping.objects.filter(po_location__job_order__job_code=job_code,
                                                      po_location__quantity__gt=0)
        pallet_ids = pallet_mapping.values_list('id', flat=True)
        status_track = StatusTracking.objects.filter(
            Q(status_type='JO', status_id__in=job_ids) | Q(status_type='JO-PALLET',
                                                           status_id__in=pallet_ids), status_value__in=extra_headers). \
            values('status_value', 'status_type').distinct().annotate(total=Sum('quantity'))

        tracking = dict(zip(map(lambda d: d.get('status_value', ''), status_track),
                            map(lambda d: d.get('total', '0'), status_track)))
        type_tracking = dict(zip(map(lambda d: d.get('status_value', ''), status_track),
                                 map(lambda d: d.get('status_type', 'JO'), status_track)))
        for head in extra_headers:
            quantity = tracking.get(head, 0)
            if type_tracking.get(head, '') == 'JO-PALLET' and pallet_mapping:
                for pallet in pallet_mapping:
                    pallet_code = pallet.pallet_detail.pallet_code
                    if quantity:
                        production_stages.append(
                            {'job_code': job_code, 'stage_name': head, 'stage_quantity': tracking.get(head, 0),
                             'pallet_code': pallet_code})
            elif quantity:
                production_stages.append(
                    {'job_code': job_code, 'stage_name': head, 'stage_quantity': tracking.get(head, 0)})

    return HttpResponse(json.dumps({'zones_data': zones_data.values(), 'production_stages': production_stages,
                                    'load_unit_handle': load_unit_handle}))


@csrf_exempt
@login_required
@get_admin_user
def confirm_move_inventory(request, user=''):
    for key, value in request.GET.iteritems():
        data1 = CycleCount.objects.get(id=key, sku__user=user.id)
        data1.status = 'completed'
        data1.save()
        data2 = CycleCount.objects.get(id=value, sku__user=user.id)
        data2.status = 'completed'
        data2.save()
        dat = InventoryAdjustment.objects.get(cycle_id=key, cycle__sku__user=user.id)
        dat.reason = 'Moved Successfully'
        dat.save()

    return HttpResponse('Moved Successfully')


@csrf_exempt
@login_required
@get_admin_user
def confirm_inventory_adjustment(request, user=''):
    mod_locations = []
    for key, value in request.GET.iteritems():
        data = CycleCount.objects.get(id=key, sku__user=user.id)
        data.status = 'completed'
        data.save()
        dat = InventoryAdjustment.objects.get(cycle_id=key, cycle__sku__user=user.id)
        dat.reason = value
        dat.save()
        location_count = StockDetail.objects.filter(location_id=dat.cycle.location_id, sku_id=dat.cycle.sku_id,
                                                    quantity__gt=0,
                                                    sku__user=user.id)
        difference = data.seen_quantity - data.quantity
        for count in location_count:
            mod_locations.append(count.location.location)
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

    if mod_locations:
        update_filled_capacity(mod_locations, user.id)
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
        master_data = VendorStock.objects.exclude(receipt_number=0).values('vendor__name', 'sku__wms_code',
                                                                           'sku__sku_desc',
                                                                           'sku__sku_category').distinct().annotate(
            total=Sum('quantity')). \
            filter(Q(sku__wms_code__icontains=search_term) | Q(sku__sku_desc__icontains=search_term) |
                   Q(sku__sku_category__icontains=search_term) | Q(total__icontains=search_term), sku__user=user.id,
                   status=1, quantity__gt=0, **search_params)

    else:
        master_data = VendorStock.objects.exclude(receipt_number=0).values('vendor__name', 'sku__wms_code',
                                                                           'sku__sku_desc',
                                                                           'sku__sku_category').distinct().annotate(
            total=Sum('quantity')).filter(quantity__gt=0,
                                          sku__user=user.id, **search_params).order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append(
            OrderedDict((('Vendor Name', data['vendor__name']), ('WMS Code', data['sku__wms_code']),
                         ('Product Description', data['sku__sku_desc']), ('SKU Category', data['sku__sku_category']),
                         ('Quantity', get_decimal_limit(user.id, data['total'])), ('DT_RowId', data['sku__wms_code'])
                         )))


@csrf_exempt
@get_admin_user
def warehouse_headers(request, user=''):
    admin_user_id = ''
    admin_user_name = ''
    level = request.GET.get('level', '')
    price_band_flag = get_misc_value('priceband_sync', user.id)
    if price_band_flag == 'true':
        user = get_admin(user)
    warehouses = UserGroups.objects.filter(admin_user_id=user.id).values_list('user_id', flat=True)
    if level:
        warehouses = UserProfile.objects.filter(user__in=warehouses,warehouse_level=int(level)).values_list('user_id',flat=True)
    ware_list = list(User.objects.filter(id__in=warehouses).values_list('username', flat=True))
    header = ["SKU Code", "SKU Brand", "SKU Description", "SKU Category"]
    user_groups = UserGroups.objects.filter(Q(admin_user_id=user.id) | Q(user_id=user.id))
    if user_groups:
        admin_user_id = user_groups[0].admin_user_id
        admin_user_name = user_groups[0].admin_user.username
    else:
        admin_user_id = user.id
        admin_user_name = user.username
    if level:
        headers = header + ware_list  #user_groups
    else:
        headers = header + [admin_user_name] + ware_list

    return HttpResponse(json.dumps(headers))


@csrf_exempt
def get_seller_stock_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                          filters={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['seller__seller_id', 'seller__name', 'stock__sku__sku_code', 'stock__sku__sku_desc', 'stock__sku__sku_class',
           'stock__sku__sku_brand', 'stock__sku__sku_category', 'stock__sku__sku_code', 'stock__sku__sku_code',
           'stock__sku__sku_code', 'stock__sku__sku_code', 'stock__sku__sku_code']
    unsorted_dict = {7: 'Available Qty', 8: 'Reserved Qty', 9: 'Damaged Qty', 10: 'Total Qty'}
    search_params = get_filtered_params(filters, lis)
    search_term_query = build_search_term_query(lis[:7], search_term)

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    search_params['stock__sku_id__in'] = sku_master_ids

    all_seller_stock = SellerStock.objects.filter(seller__user=user.id)
    dis_seller_ids = all_seller_stock.values_list('seller__seller_id', flat=True).distinct()
    sell_stock_ids = all_seller_stock.values('seller__seller_id', 'stock_id')

    reserved_dict, raw_reserved_dict = get_seller_reserved_stocks(dis_seller_ids, sell_stock_ids, user)
    '''reserved_dict = OrderedDict()
    raw_reserved_dict = OrderedDict()
    for seller in dis_seller_ids:
        pick_params = {'status': 1, 'picklist__order__user': user.id}
        rm_params = {'status': 1, 'material_picklist__jo_material__material_code__user': user.id}
        stock_id_dict = filter(lambda d: d['seller__seller_id'] == seller, sell_stock_ids)
        if stock_id_dict:
            stock_ids = map(lambda d: d['stock_id'], stock_id_dict)
            pick_params['stock_id__in'] = stock_ids
            rm_params['stock_id__in'] = stock_ids
        reserved_dict[seller] = dict(PicklistLocation.objects.filter(**pick_params).\
                                     values_list('stock__sku__wms_code').distinct().annotate(reserved=Sum('reserved')))
        raw_reserved_dict[seller] = dict(RMLocation.objects.filter(**rm_params).\
                                           values('material_picklist__jo_material__material_code__wms_code').distinct().\
                                           annotate(rm_reserved=Sum('reserved')))'''

    temp_data['totalQuantity'] = 0
    temp_data['totalReservedQuantity'] = 0
    temp_data['totalAvailableQuantity'] = 0

    categories = dict(SKUMaster.objects.filter(user=user.id).values_list('sku_code', 'sku_category'))
    if search_term:
        master_data = SellerStock.objects.exclude(stock__receipt_number=0).filter(quantity__gt=0).values_list(
            'seller__seller_id',
            'seller__name', 'stock__sku__sku_code', 'stock__sku__sku_desc', 'stock__sku__sku_class',
            'stock__sku__sku_brand').distinct(). \
            annotate(total=Sum('quantity')). \
            filter(search_term_query, stock__sku__user=user.id, **search_params).order_by(order_data)
        search_params['stock__location__zone__zone'] = 'DAMAGED_ZONE'
        damaged_stock = SellerStock.objects.exclude(stock__receipt_number=0).filter(quantity__gt=0). \
            values('seller__seller_id', 'seller__name',
                   'stock__sku__sku_code', 'stock__sku__sku_desc', 'stock__sku__sku_class',
                   'stock__sku__sku_brand').distinct(). \
            annotate(total=Sum('quantity')).filter(search_term_query, stock__sku__user=user.id,
                                                   **search_params)

    else:
        master_data = SellerStock.objects.exclude(stock__receipt_number=0).filter(quantity__gt=0).values_list(
            'seller__seller_id',
            'seller__name', 'stock__sku__sku_code', 'stock__sku__sku_desc', 'stock__sku__sku_class',
            'stock__sku__sku_brand').distinct(). \
            annotate(total=Sum('quantity')). \
            filter(stock__sku__user=user.id, **search_params).order_by(order_data)
        search_params['stock__location__zone__zone'] = 'DAMAGED_ZONE'
        damaged_stock = SellerStock.objects.exclude(stock__receipt_number=0).filter(quantity__gt=0). \
            values('seller__seller_id', 'seller__name',
                   'stock__sku__sku_code', 'stock__sku__sku_desc', 'stock__sku__sku_class',
                   'stock__sku__sku_brand').distinct(). \
            annotate(total=Sum('quantity')).filter(stock__sku__user=user.id, **search_params)
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    custom_search = False
    if col_num in unsorted_dict.keys():
        custom_search = True

    if stop_index and not custom_search:
        master_data = master_data[start_index:stop_index]

    for data in master_data:
        quantity = 0
        reserved = 0
        damaged_qty = 0
        total_qty = data[6]
        if data[0] in reserved_dict.keys():
            if data[2] in reserved_dict[data[0]].keys():
                reserved = reserved_dict[data[0]][data[2]]
        if data[0] in raw_reserved_dict.keys():
            if data[2] in raw_reserved_dict[data[0]].keys():
                reserved += raw_reserved_dict[data[0]][data[2]]
        quantity = total_qty - reserved
        damaged_dict = filter(
            lambda person: person['seller__seller_id'] == data[0] and person['stock__sku__sku_code'] == data[2],
            damaged_stock)
        if damaged_dict:
            damaged_qty = damaged_dict[0]['total']
            quantity -= damaged_qty
        if quantity < 0:
            quantity = 0
        stock_value = 0

        temp_data['aaData'].append(OrderedDict((('Seller ID', data[0]), ('Seller Name', data[1]),
                                                ('SKU Code', data[2]), ('SKU Desc', data[3]), ('SKU Class', data[4]),
                                                ('SKU Brand', data[5]), ('SKU Category', categories[data[2]]),
                                                ('Available Qty', quantity),
                                                ('Reserved Qty', reserved), ('Damaged Qty', damaged_qty),
                                                ('Total Qty', total_qty),
                                                ('Stock Value', stock_value),
                                                ('id', str(data[0]) + '<<>>' + str(data[2])))))

    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(temp_data['aaData'][0].keys(), temp_data['aaData'], order_term, '',
                                                    col_num, exact=False)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


@csrf_exempt
@login_required
@get_admin_user
def seller_stock_summary_data(request, user=''):
    data_id = request.GET['data_id']
    seller_id, wms_code = data_id.split('<<>>')
    seller_stock_data = SellerStock.objects.exclude(stock__receipt_number=0).filter(stock__sku__wms_code=wms_code,
                                                                                    seller__seller_id=seller_id,
                                                                                    seller__user=user.id)
    zones_data = {}
    for seller_stock in seller_stock_data:
        stock = seller_stock.stock
        res_qty = PicklistLocation.objects.filter(stock_id=stock.id, status=1, picklist__order__user=user.id). \
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
        zones_data[stock.location.zone.zone][stock.location.location][0] += seller_stock.quantity

    return HttpResponse(json.dumps({'zones_data': zones_data}))


@csrf_exempt
@login_required
@get_admin_user
def get_imei_details(request, user=''):
    # returns imei details
    imei = request.GET['imei']
    resp = {'result': 0, 'data': {}}

    if imei:

        imei_data = QCSerialMapping.objects.filter(serial_number__purchase_order__open_po__sku__user=user.id,
                                                   serial_number__imei_number=imei)
        if imei_data:

            imei_data = imei_data[0]
            resp['data'] = {'imei_data': {'id': imei_data.id, 'imei_number': imei_data.serial_number.imei_number,
                                          'status': imei_data.status, \
                                          'reason': imei_data.reason,
                                          'sku_code': imei_data.serial_number.purchase_order.open_po.sku.sku_code},
                            'options': REJECT_REASONS}
        else:

            resp['result'] = 1;
            resp['data'] = "IMEI Not Found"
    else:

        resp['result'] = 1;
        resp['data'] = "IMEI Not Found"

    return HttpResponse(json.dumps(resp))


@csrf_exempt
@login_required
@get_admin_user
def change_imei_status(request, user=''):
    # returns imei details
    request_data = request.POST
    resp = {'status': 0, 'message': 'No Data found'}
    log.info("Change Imei status params " + str(request.POST.dict()))
    try:
        data_id = request_data.get('id', '')
        qc_serial = QCSerialMapping.objects.get(id=data_id)
        resp = {'status': 1, 'message': 'No Data found'}
        if qc_serial:
            qc_serial.status = request_data.get('status', '')
            qc_serial.reason = request_data.get('reason', '')
            qc_serial.save()
            resp = {'status': 1, 'message': 'Updated Successfully'}
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Change Imei status failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request_data.dict()), str(e)))
    return HttpResponse(json.dumps(resp))


@csrf_exempt
def get_stock_summary_serials_excel(filter_params, temp_data, headers, user, request):
    """ This function delivers the excel of serial numbers which are in stock """
    log.info(" ------------Stock Summary Serials excel download started ------------------")
    st_time = datetime.datetime.now()
    import xlsxwriter
    try:
        headers, search_params, filters = get_search_params(request)
        search_term = search_params.get('search_term', '')
        path = 'static/excel_files/' + str(user.id) + '.Stock_Summary_Serials.xlsx'
        if not os.path.exists('static/excel_files/'):
            os.makedirs('static/excel_files/')
        workbook = xlsxwriter.Workbook(path)
        worksheet = workbook.add_worksheet("Stock Serials")
        bold = workbook.add_format({'bold': True})
        exc_headers = ['SKU Code', 'Product Description', 'SKU Brand', 'SKU Category', 'Serial Number', 'Status',
                       'Reason']
        for n, header in enumerate(exc_headers):
            worksheet.write(0, n, header, bold)
        dict_list = ['purchase_order__open_po__sku__sku_code', 'purchase_order__open_po__sku__sku_desc',
                     'purchase_order__open_po__sku__sku_brand', 'purchase_order__open_po__sku__sku_category',
                     'imei_number']

        filter_params = get_filtered_params(filters, dict_list)
        dispatched_imeis = OrderIMEIMapping.objects.filter(status=1, order__user=user.id).values_list('po_imei_id',
                                                                                                      flat=True)
        damaged_returns = dict(ReturnsIMEIMapping.objects.filter(status='damaged', order_imei__order__user=user.id). \
                               values_list('order_imei__po_imei__imei_number', 'reason'))
        qc_damaged = dict(QCSerialMapping.objects.filter(serial_number__purchase_order__open_po__sku__user=user.id,
                                                         status='rejected').values_list('serial_number__imei_number',
                                                                                        'reason'))
        qc_damaged.update(damaged_returns)
        if search_term:
            imei_data = POIMEIMapping.objects.filter(Q(purchase_order__open_po__sku__sku_code__icontains=search_term) |
                                                     Q(purchase_order__open_po__sku__sku_desc__icontains=search_term) |
                                                     Q(purchase_order__open_po__sku__sku_brand__icontains=search_term) |
                                                     Q(
                                                         purchase_order__open_po__sku__sku_category__icontains=search_term),
                                                     status=1, purchase_order__open_po__sku__user=user.id,
                                                     **filter_params). \
                exclude(id__in=dispatched_imeis).values_list(*dict_list)
        else:
            imei_data = POIMEIMapping.objects.filter(status=1, purchase_order__open_po__sku__user=user.id,
                                                     **filter_params). \
                exclude(id__in=dispatched_imeis).values_list(*dict_list)
        row = 1
        for imei in imei_data:
            col_count = 0
            for col, data in enumerate(imei):
                worksheet.write(row, col_count, data)
                col_count += 1
            imei_status = 'Accepted'
            reason = ''
            if imei[-1] in qc_damaged:
                imei_status = 'Damaged'
                reason = qc_damaged.get(imei[-1], '')
            worksheet.write(row, col_count, imei_status)
            col_count += 1
            worksheet.write(row, col_count, reason)
            row += 1

        workbook.close()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(e)

    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("total time -- %s" % (duration))
    log.info("process completed")
    return '../' + path


@csrf_exempt
@login_required
@get_admin_user
def confirm_sku_substitution(request, user=''):
    ''' Moving stock from one location to other location with SKU substitution '''

    src_sku = request.POST.get('src_sku_code', '')
    dest_sku = request.POST.get('dest_sku_code', '')
    src_qty = request.POST.get('src_quantity', '')
    dest_qty = request.POST.get('dest_quantity', '')
    src_loc = request.POST.get('src_location', '')
    dest_loc = request.POST.get('dest_location', '')

    if not src_sku and not dest_sku and not src_qty and not dest_qty and not src_loc and not dest_loc:
        return HttpResponse('Please Send Required Field')

    src_sku = SKUMaster.objects.filter(user=user.id, sku_code=src_sku)
    dest_sku = SKUMaster.objects.filter(user=user.id, sku_code=dest_sku)
    src_loc = LocationMaster.objects.filter(zone__user=user.id, location=src_loc)
    dest_loc = LocationMaster.objects.filter(zone__user=user.id, location=dest_loc)
    try:
        src_qty = float(src_qty)
    except ValueError:
        log.info("Substitution: Source Quantity Should Be Number ," + src_qty)
        return HttpResponse('Source Quantity Should Be Number')
    try:
        dest_qty = float(dest_qty)
    except ValueError:
        log.info("Substitution: Destination Quantity Should Be Number ," + dest_qty)
        return HttpResponse('Destination Quantity Should Be Number')
    if not src_sku:
        return HttpResponse('Source SKU Code Not Found')
    elif not dest_sku:
        return HttpResponse('Destination SKU Code Not Found')
    elif float(src_qty) <= 0:
        return HttpResponse('Source Quantity Should Greater Than Zero')
    elif float(dest_qty) <= 0:
        return HttpResponse('Destination Quantity Should Greater Than Zero')
    elif not src_loc:
        return HttpResponse('Source Location Not Found')
    elif not dest_loc:
        return HttpResponse('Destination Location Not Found')

    src_sku, dest_sku, src_loc, dest_loc = src_sku[0], dest_sku[0], src_loc[0], dest_loc[0]
    src_stocks = StockDetail.objects.filter(sku_id=src_sku.id, location_id=src_loc.id, sku__user=user.id)
    src_stock_count = src_stocks.aggregate(Sum('quantity'))['quantity__sum']
    if not src_stock_count:
        return HttpResponse('Source SKU Code Don\'t Have Stock')
    elif src_stock_count < src_qty:
        return HttpResponse('Source SKU Code Have Stock, ' + str(src_stock_count))
    dest_stocks = StockDetail.objects.filter(sku_id=dest_sku.id, location_id=dest_loc.id, sku__user=user.id)
    update_stocks_data(src_stocks, float(src_qty), dest_stocks, float(dest_qty), user, [dest_loc], dest_sku.id, '')
    sub_data = {'source_sku_code_id': src_sku.id, 'source_location': src_loc.location, 'source_quantity': src_qty,
                'destination_sku_code_id': dest_sku.id, 'destination_location': dest_loc.location,
                'destination_quantity': dest_qty}
    SubstitutionSummary.objects.create(**sub_data)
    log.info("Substitution Done For " + str(json.dumps(sub_data)))

    return HttpResponse('Successfully Updated')

@csrf_exempt
def get_inventory_modification(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['sku__wms_code', 'location', 'pallet_detail__pallet_code', 'sku__sku_desc', 'sku__sku_class', 'sku__sku_category' , 'sku__sku_brand']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    job_order = JobOrder.objects.filter(product_code__user=user.id, status__in=['grn-generated', 'pick_confirm'])
    job_ids = job_order.values_list('id', flat=True)
    extra_headers = list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    status_track = StatusTracking.objects.filter(status_type='JO', status_id__in=job_ids,status_value__in=extra_headers, quantity__gt=0). \
        values('status_value', 'status_id').distinct().annotate(total=Sum('quantity'))
    status_ids = map(lambda d: d.get('status_id', ''), status_track)
    pallet_misc_detail = get_misc_value('pallet_switch',user.id)
    picklist_location_stock_query_list = ['stock__sku__wms_code', 'stock__location__location']
    if pallet_misc_detail=='true':
        picklist_location_stock_query_list.append('stock__pallet_detail__pallet_code')
    reserved_instances = PicklistLocation.objects.filter(status=1, stock__sku__user=user.id).values(*picklist_location_stock_query_list). \
        distinct().annotate(reserved=Sum('reserved'))
    rm_location_query_list = ['material_picklist__jo_material__material_code__wms_code', 'stock__location__location']
    if pallet_misc_detail=='true':
        rm_location_query_list.append('stock__pallet_detail__pallet_code')
    raw_res_instances = RMLocation.objects.filter(status=1, stock__sku__user=user.id). \
        values(*rm_location_query_list).distinct(). \
        annotate(rm_reserved=Sum('reserved'))
    reserveds = map(lambda d: d['stock__sku__wms_code'], reserved_instances)
    reserveds_location = map(lambda d: d['stock__location__location'], reserved_instances)
    reserved_quantities = map(lambda d: d['reserved'], reserved_instances)
    raw_reserveds = map(lambda d: d['material_picklist__jo_material__material_code__wms_code'], raw_res_instances)
    raw_reserved_quantities = map(lambda d: d['rm_reserved'], raw_res_instances)
    raw_reserveds_location = map(lambda d: d['stock__location__location'], raw_res_instances)
    stock_detail_query_list = ['sku__wms_code', 'sku__sku_desc', 'sku__sku_category', 'sku__sku_brand', 'sku__sku_class', 'location__location']
    if pallet_misc_detail=='true':
        stock_detail_query_list.append('pallet_detail__pallet_code')
    if search_term:
        master_data = StockDetail.objects.exclude(receipt_number=0).values_list(*stock_detail_query_list). \
        distinct().annotate(total=Sum('quantity')).filter(Q(sku__wms_code__icontains=search_term) |Q(sku__sku_desc__icontains=search_term) | Q(sku__sku_category__icontains=search_term)|Q(total__icontains=search_term), sku__user=user.id,status=1)
        wms_codes = map(lambda d: d[0], master_data)
        master_data1 = job_order.exclude(product_code__wms_code__in=wms_codes).filter(
            Q(product_code__wms_code__icontains=search_term) |
            Q(product_code__sku_desc__icontains=search_term) | Q(product_code__sku_category__icontains=search_term),
        ).values_list('product_code__wms_code', 'product_code__sku_desc', 'product_code__sku_category', 'product_code__sku_brand', 'product_code__sku_class').distinct()
        master_data = list(chain(master_data, master_data1))
    else:
        master_data = StockDetail.objects.exclude(receipt_number=0).values_list(*stock_detail_query_list).distinct(). \
            annotate(total=Sum('quantity')).filter(sku__user=user.id). \
            order_by(order_data)
        wms_codes = map(lambda d: d[0], master_data)
        master_data1 = job_order.exclude(product_code__wms_code__in=wms_codes).values_list(
            'product_code__wms_code',
            'product_code__sku_desc', 'product_code__sku_category', 'product_code__sku_brand', 'product_code__sku_class').distinct()
        master_data = list(chain(master_data, master_data1))
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    pallet_code = ''
    for ind, data in enumerate(master_data[start_index:stop_index]):
        reserved = 0
        pallet_misc_detail = get_misc_value('pallet_switch',user.id)
        if pallet_misc_detail=='true':
            total = 0
            if len(data) >= 7:
                if data[7] != None:
                    if len(data) > 7:
                        total = data[7]
            pallet_code = data[6]
        else:
            total = 0
            if len(data) >= 6:
                if data[6] != None:
                    if len(data) > 6:
                        total = data[6]
        sku = sku_master.get(wms_code=data[0], user=user.id)
        if data[0] in reserveds and data[5] in reserveds_location:
            if reserveds_location[reserveds.index(data[0])] == data[5]:
                reserved += float(reserved_quantities[reserveds.index(data[0])])
        if data[0] in raw_reserveds and data[5] in raw_reserveds_location:
            if raw_reserveds_location[raw_reserveds.index(data[0])] == data[5]:
                reserved += float(raw_reserved_quantities[raw_reserveds.index(data[0])])
        total = total + reserved
        quantity = total - reserved
        if quantity < 0:
            quantity = 0
        if not pallet_code:
            pallet_code = ''
        temp_data['aaData'].append(OrderedDict((('WMS Code', data[0]), ('Product Description', data[1]),
                                                ('SKU Category', data[2]), ('SKU Brand', data[3]),
						('SKU Class', data[4]), ('Location', data[5]),
						('Pallet Code', pallet_code),
                                                ('Available Quantity', ('<input type="number" class="ng-hide form-control" name="available_qty" ng-hide="showCase.available_qty_edit" min="0" ng-model="showCase.available_qty_val_%s" ng-init="showCase.available_qty_val_%s=%s" limit-to-max><p ng-show="showCase.available_qty_edit">%s</p>')%(str(ind), str(ind), str(int(quantity)), str(int(quantity))) ), ('SKU Class', ''),
                                                ('Reserved Quantity', reserved), ('Total Quantity', total),
                                                ('Addition', ("<input type='number' class='form-control' name='addition' disabled='true' ng-disabled='showCase.addition_edit' value='0' min='0' ng-model='showCase.add_qty_val_%s' ng-init='showCase.add_qty_val_%s=0' limit-to-max>") % (str(ind), str(ind) )),
                                                ('Reduction', ("<input class='form-control' type='number' name='reduction' ng-disabled='showCase.reduction_edit' disabled='true' value='0' min='0' max='%s' ng-model='showCase.sub_qty_val_%s' ng-init='showCase.sub_qty_val_%s=0' limit-to-max>" )%(str(int(quantity)), str(ind), str(ind)) ),
                                                (' ', '<button type="button" name="submit" ng-click="showCase.inv_adj_save_qty('+"'"+str(ind)+"'"+', '+"'"+str(data[0])+"'"+', '+"'"+str(data[5])+"'"+', '+"'"+pallet_code+"'"+', showCase.available_qty_val_'+str(ind)+', '+"'"+str(int(quantity))+"'"+', showCase.add_qty_val_'+str(ind)+', showCase.sub_qty_val_'+str(ind)+')" ng-disabled="showCase.button_edit" disabled class="btn btn-primary ng-click-active" >Save</button>'))))


def update_cycle_count_inventory_adjustment(user, sku_id, location_id, old_qty, new_qty, pallet_id):
    data = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not data:
        cycle_id = 1
    else:
        cycle_id = data[0].cycle + 1
    data_dict = {}
    data_dict['cycle'] = cycle_id
    data_dict['sku_id'] = sku_id
    data_dict['location_id'] = location_id
    data_dict['quantity'] = old_qty
    data_dict['seen_quantity'] = new_qty
    data_dict['status'] = 0
    data_dict['creation_date'] = str(datetime.datetime.now())
    data_dict['updation_date'] = str(datetime.datetime.now())
    dat = CycleCount(**data_dict)
    dat.save()
    data = {}
    data['cycle_id'] = dat.id
    data['adjusted_quantity'] = new_qty - old_qty
    data['reason'] = ''
    data['adjusted_location'] = location_id
    data['creation_date'] = str(datetime.datetime.now())
    data['updation_date'] = str(datetime.datetime.now())
    inv_obj = InventoryAdjustment.objects.filter(cycle__cycle=dat.cycle, adjusted_location=location_id, cycle__sku__user=user.id)
    if pallet_id:
        data['pallet_detail_id'] = pallet_id
        inv_obj = inv_obj.filter(pallet_detail_id = pallet_id)
    if inv_obj:
        inv_obj = inv_obj[0]
        inv_obj.adjusted_quantity = quantity
        inv_obj.save()
        dat = inv_obj
    else:
        dat = InventoryAdjustment(**data)
        dat.save()

@csrf_exempt
@login_required
@get_admin_user
def inventory_adj_modify_qty(request, user=''):
    wms_code = request.POST.get('wms_code', '')
    sku_location = request.POST.get('location', '')
    pallet_code = request.POST.get('pallet_code', '')
    added_qty = int(request.POST.get('added_qty', 0))
    sub_qty = int(request.POST.get('sub_qty', 0))
    modify_qty = int(request.POST.get('mod_qty', 0))
    available_qty = int(request.POST.get('available_qty', 0))
    old_available_qty = int(request.POST.get('old_available_qty', 0))
    pallet_code_enabled = get_misc_value('pallet_switch', user.id)
    data_dict = {}
    data_dict['sku__wms_code']=wms_code
    data_dict['location__location']=sku_location
    if pallet_code_enabled == 'true' and pallet_code:
        data_dict['pallet_detail__pallet_code'] = pallet_code
    get_next_receipt_number = StockDetail.objects.filter(sku__user=user.id).aggregate(Max('receipt_number'))
    if get_next_receipt_number:
        new_receipt_number = get_next_receipt_number['receipt_number__max'] + 1
    else:
        new_receipt_number = 1
    message = ''
    qty_obj = StockDetail.objects.filter(**data_dict).order_by('-updation_date')
    if qty_obj:
        qty_obj = qty_obj[0]
        data_dict['receipt_number'] = new_receipt_number
        data_dict['receipt_date'] = qty_obj.receipt_date
        data_dict['receipt_type'] = qty_obj.receipt_type
        data_dict['quantity'] = added_qty
        data_dict['status']=1
        location_master = LocationMaster.objects.filter(location=data_dict['location__location'], zone__user=user.id)
        if location_master:
            location_id = location_master[0].id
        else:
            location_id = 0
        sku_master = SKUMaster.objects.filter(user=user.id, sku_code=data_dict['sku__wms_code'])
        if sku_master:
            sku_id = sku_master[0].id
        else:
            sku_id = 0
        if pallet_code:
            pallet_code = PalletDetail.objects.filter(user=user.id, pallet_code = data_dict['pallet_detail__pallet_code'])
            if pallet_code:
                pallet_id = pallet_code[0].id
        else:
            pallet_id = 0
        #For Add Qty and create new stock detail
        if added_qty:
            stock_new_create = {}
            if location_id:
                stock_new_create['location_id'] = location_id
            if sku_id:
                stock_new_create['sku_id'] = sku_id
            if pallet_id:
                stock_new_create['pallet_detail_id'] = pallet_id
            stock_new_create['quantity'] = data_dict['quantity']
            stock_new_create['status'] = 1
            stock_new_create['receipt_number'] = data_dict['receipt_number']
            stock_new_create['receipt_date'] = datetime.datetime.now()
            stock_new_create['receipt_type'] = ''
            message="Added Quantity Successfully"
            inventory_create_new = StockDetail.objects.create(**stock_new_create)
            save_sku_stats(user, sku_id, inventory_create_new.id, 'inventory-adjustment', stock_new_create['quantity'])
        #Modify Available Qty
	if old_available_qty != available_qty or sub_qty:
            stock_qty_update = {}
            if location_id:
                stock_qty_update['location_id'] = location_id
            if sku_id:
                stock_qty_update['sku_id'] = sku_id
            if pallet_id:
                stock_qty_update['pallet_detail_id'] = pallet_id
            stock_qty_update['receipt_date__regex'] = str(data_dict['receipt_date'].replace(tzinfo=None))
            stock_qty_update['receipt_type'] = data_dict['receipt_type']
            stock_qty_update['status'] = 1
            stock_qty_update['sku__user'] = user.id
            inventory_update_adj = StockDetail.objects.filter(**stock_qty_update)
            if old_available_qty != available_qty and inventory_update_adj:
                sub_qty = available_qty - old_available_qty
                message="Available Quantity Updated Successfully"
                for idx, ob in enumerate(inventory_update_adj):
                    reserve_qty = 0
                    raw_reserve_qty = 0
                    save_reduced_qty = 0
                    if (available_qty - old_available_qty) > 0:
                        if not idx:
                            ob.quantity = int(ob.quantity)+int(sub_qty)
                            ob.save()
                            save_sku_stats(user, sku_id, ob.id, 'inventory-adjustment', int(ob.quantity)+int(sub_qty))
                            update_cycle_count_inventory_adjustment(user, sku_id, location_id, old_available_qty, available_qty, pallet_id)
                            break
                    if (available_qty - old_available_qty) < 0:
                        sub_qty = abs(sub_qty)
                        reserved_instances = PicklistLocation.objects.filter(status=1, stock__sku__user=user.id, stock=ob).values('stock__sku__wms_code').distinct().annotate(reserved=Sum('reserved'))
                        raw_res_instances = RMLocation.objects.filter(status=1, stock__sku__user=user.id, stock=ob).values('stock__sku__wms_code').distinct().annotate(rm_reserved=Sum('reserved'))
                        reserve = map(lambda d: d['reserved'], reserved_instances)
                        if reserve:
                            reserve_qty = reserve[0]
                        raw_reserve = map(lambda d: d['rm_reserved'], raw_res_instances)
                        if raw_reserve:
                            raw_reserve_qty = raw_reserve[0]
                        total_reserve_qty = reserve_qty + raw_reserve_qty
                        obj_qty = ob.quantity
                        if obj_qty:
                            save_reduced_qty = abs(obj_qty - total_reserve_qty)
                        if save_reduced_qty >= sub_qty:
                            diff_qty = int(save_reduced_qty)-int(sub_qty)
                            StockDetail.objects.filter(id=ob.id).update(quantity=diff_qty)
                            save_sku_stats(user, sku_id, ob.id, 'inventory-adjustment', diff_qty)
                            update_cycle_count_inventory_adjustment(user, sku_id, location_id, old_available_qty, available_qty, pallet_id)
                            sub_qty = 0
                        elif save_reduced_qty:
                            sub_qty = int(sub_qty)-int(save_reduced_qty)
                            StockDetail.objects.filter(id=ob.id).update(quantity=0)
                            save_sku_stats(user, sku_id, ob.id, 'inventory-adjustment', 0)
                            update_cycle_count_inventory_adjustment(user, sku_id, location_id, old_available_qty, available_qty, pallet_id)
                            continue
                        if not sub_qty:
                            break
            elif sub_qty and inventory_update_adj:
                for ob in inventory_update_adj:
                    reserve_qty = 0
                    raw_reserve_qty = 0
                    save_reduced_qty = 0
                    reserved_instances = PicklistLocation.objects.filter(status=1, stock__sku__user=user.id, stock=ob).values('stock__sku__wms_code').distinct().annotate(reserved=Sum('reserved'))
                    raw_res_instances = RMLocation.objects.filter(status=1, stock__sku__user=user.id, stock=ob).values('stock__sku__wms_code').distinct().annotate(rm_reserved=Sum('reserved'))
                    reserve = map(lambda d: d['reserved'], reserved_instances)
                    if reserve:
                        reserve_qty = reserve[0]
                    raw_reserve = map(lambda d: d['rm_reserved'], raw_res_instances)
                    if raw_reserve:
                        raw_reserve_qty = raw_reserve[0]
                    total_reserve_qty = reserve_qty + raw_reserve_qty
                    obj_qty = ob.quantity
                    if obj_qty:
                        save_reduced_qty = abs(obj_qty - total_reserve_qty)
                    if save_reduced_qty >= sub_qty:
                        diff_qty = int(save_reduced_qty)-int(sub_qty)
                        ob.quantiy = diff_qty
                        StockDetail.objects.filter(id=ob.id).update(quantity=diff_qty)
                        save_sku_stats(user, sku_id, ob.id, 'inventory-adjustment', diff_qty)
                        update_cycle_count_inventory_adjustment(user, sku_id, location_id, old_available_qty, available_qty, pallet_id)
                        sub_qty = 0
                    elif save_reduced_qty:
                        sub_qty = int(sub_qty)-int(save_reduced_qty)
                        StockDetail.objects.filter(id=ob.id).update(quantity=0)
                        save_sku_stats(user, sku_id, ob.id, 'inventory-adjustment', 0)
                        update_cycle_count_inventory_adjustment(user, sku_id, location_id, old_available_qty, available_qty, pallet_id)
                        continue
                    if not sub_qty:
                        break
    return HttpResponse(json.dumps({'status': True, 'message':message}))


def get_batch_level_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                             filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['receipt_number', 'receipt_date', 'sku_id__wms_code', 'sku_id__sku_desc', 'batch_detail__batch_no',
           'batch_detail__mrp', 'location__zone__zone', 'location__location', 'pallet_detail__pallet_code',
           'quantity', 'receipt_type']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_params = get_filtered_params(filters, lis)
    if 'receipt_date__icontains' in search_params:
        search_params['receipt_date__regex'] = search_params['receipt_date__icontains']
        del search_params['receipt_date__icontains']
    search_params['sku_id__in'] = sku_master_ids

    if search_term:
        master_data = StockDetail.objects.exclude(receipt_number=0).filter(Q(receipt_number__icontains=search_term) |
                                                                           Q(sku__wms_code__icontains=search_term) | Q(
            quantity__icontains=search_term) |
                                                                           Q(
                                                                               location__zone__zone__icontains=search_term) | Q(
            sku__sku_code__icontains=search_term) |
                                                                           Q(sku__sku_desc__icontains=search_term) | Q(
            location__location__icontains=search_term),
                                                                           sku__user=user.id).filter(
            **search_params).order_by(order_data)

    else:
        master_data = StockDetail.objects.exclude(receipt_number=0).filter(sku__user=user.id, **search_params). \
            order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        pallet_switch = get_misc_value('pallet_switch', user.id)
        _date = get_local_date(user, data.receipt_date, True)
        _date = _date.strftime("%d %b, %Y")
        batch_no = data.batch_detail.batch_no if data.batch_detail else ''
        mrp = data.batch_detail.mrp if data.batch_detail else ''
        if pallet_switch == 'true':
            pallet_code = ''
            if data.pallet_detail:
                pallet_code = data.pallet_detail.pallet_code
            temp_data['aaData'].append(OrderedDict((('Receipt Number', data.receipt_number), ('DT_RowClass', 'results'),
                                                    ('Receipt Date', _date), ('SKU Code', data.sku.sku_code),
                                                    ('WMS Code', data.sku.wms_code),
                                                    ('Product Description', data.sku.sku_desc),
                                                    ('Batch Number', batch_no),
                                                    ('MRP', mrp),
                                                    ('Zone', data.location.zone.zone),
                                                    ('Location', data.location.location),
                                                    ('Quantity', get_decimal_limit(user.id, data.quantity)),
                                                    ('Pallet', pallet_code), ('Receipt Type', data.receipt_type))))
        else:
            temp_data['aaData'].append(OrderedDict((('Receipt Number', data.receipt_number), ('DT_RowClass', 'results'),
                                                    ('Receipt Date', _date), ('SKU Code', data.sku.sku_code),
                                                    ('WMS Code', data.sku.wms_code),
                                                    ('Product Description', data.sku.sku_desc),
                                                    ('Batch Number', batch_no),
                                                    ('MRP', mrp),
                                                    ('Zone', data.location.zone.zone),
                                                    ('Location', data.location.location),
                                                    ('Quantity', get_decimal_limit(user.id, data.quantity)),
                                                    ('Receipt Type', data.receipt_type))))
