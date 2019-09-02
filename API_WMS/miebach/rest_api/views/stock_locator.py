from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import json
from django.db.models import Q, F
from itertools import chain
from collections import OrderedDict, defaultdict
from itertools import groupby
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
from common import *
from miebach_utils import *
from utils import *

log = init_logger('logs/stock_locator.log')


@csrf_exempt
@fn_timer
def get_stock_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    is_excel = request.POST.get('excel', 'false')
    lis = ['sku__wms_code', 'sku__sku_desc', 'sku__sku_brand', 'sku__sku_category', 'total', 'total', 'total', 'total',
           'sku__measurement_type', 'stock_value', 'sku__wms_code']
    lis1 = ['product_code__wms_code', 'product_code__sku_desc', 'product_code__sku_brand', 'product_code__sku_category',
            'total',
            'total', 'total', 'total', 'product_code__measurement_type', 'stock_value', 'product_code__wms_code']
    sort_cols = ['WMS Code', 'Product Description', 'SKU Brand', 'SKU Category', 'Quantity', 'Reserved Quantity',
                 'Total Quantity',
                 'Unit of Measurement', 'Stock Value']
    lis2 = ['wms_code', 'sku_desc', 'sku_brand', 'sku_category', 'threshold_quantity', 'threshold_quantity',
            'threshold_quantity', 'measurement_type', 'measurement_type', 'wms_code']
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

    picklist_reserved = dict(PicklistLocation.objects.filter(status=1, stock__sku__user=user.id).values_list(
        'stock__sku__wms_code'). \
        distinct().annotate(reserved=Sum('reserved')))
    raw_reserved = dict(RMLocation.objects.filter(status=1, stock__sku__user=user.id). \
        values_list('material_picklist__jo_material__material_code__wms_code').distinct(). \
        annotate(rm_reserved=Sum('reserved')))

    #reserveds = map(lambda d: d['stock__sku__wms_code'], reserved_instances)
    #reserved_quantities = map(lambda d: d['reserved'], reserved_instances)
    #raw_reserveds = map(lambda d: d['material_picklist__jo_material__material_code__wms_code'], raw_res_instances)
    #raw_reserved_quantities = map(lambda d: d['rm_reserved'], raw_res_instances)
    temp_data['totalQuantity'] = 0
    temp_data['totalReservedQuantity'] = 0
    temp_data['totalAvailableQuantity'] = 0
    if search_term:
        master_data = StockDetail.objects.exclude(receipt_number=0).values_list('sku__wms_code', 'sku__sku_desc',
                                                                                'sku__sku_category',
                                                                                'sku__sku_brand'). \
            distinct().annotate(total=Sum('quantity'), stock_value=Sum(F('quantity') * F('unit_price'))).filter(Q(sku__wms_code__icontains=search_term) |
                                                              Q(sku__sku_desc__icontains=search_term) | Q(
            sku__sku_category__icontains=search_term) |
                                                              Q(total__icontains=search_term) | Q(stock_value__icontains=search_term), sku__user=user.id,
                                                              status=1, **search_params).order_by(order_data)
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
            annotate(total=Sum('quantity'), stock_value=Sum(F('quantity') * F('unit_price'))).filter(sku__user=user.id, **search_params). \
            order_by(order_data)
        wms_codes = map(lambda d: d[0], master_data)
        quantity_master_data = master_data.aggregate(Sum('total'))
        if 'stock_value__icontains' in search_params1.keys():
            del search_params1['stock_value__icontains']
        master_data1 = job_order.exclude(product_code__wms_code__in=wms_codes).filter(**search_params1).values_list(
            'product_code__wms_code',
            'product_code__sku_desc', 'product_code__sku_category', 'product_code__sku_brand').distinct()
        master_data = list(chain(master_data, master_data1))
    if 'stock_value__icontains' in search_params1.keys():
        del search_params1['stock_value__icontains']
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

    if not is_excel == 'true':
        for data in master_data:
            total_available_quantity = 0
            total_reserved = 0
            total = 0
            diff = 0

            if data[0] in picklist_reserved.keys():
                total_reserved = float(picklist_reserved[data[0]])
                temp_data['totalReservedQuantity'] += total_reserved
            if data[0] in raw_reserved.keys():
                total_reserved = float(raw_reserved[data[0]])
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

    sku_type_qty = dict(OrderDetail.objects.filter(user=user.id, quantity__gt=0, status=1).values_list('sku__sku_code').distinct().annotate(Sum('quantity')))
    sku_pack_config = get_misc_value('sku_pack_config', user.id)
    for ind, data in enumerate(master_data[start_index:stop_index]):
        total_stock_value = 0
        reserved = 0
        # total = data[4] if len(data) > 4 else 0
        total = 0
        if len(data) >= 5:
            if data[4] != None:
                if len(data) > 4:
                    total = data[4]

        sku = sku_master.get(user=user.id, sku_code=data[0])
        if data[0] in picklist_reserved.keys():
            reserved += float(picklist_reserved[data[0]])
        if data[0] in raw_reserved.keys():
            reserved += float(raw_reserved[data[0]])
        quantity = total - reserved
        if quantity < 0:
            quantity = 0

        total_stock_value = 0
        sku_packs = 0
        if quantity:
            wms_code_obj = StockDetail.objects.exclude(receipt_number=0).filter(sku__wms_code = data[0], sku__user=user.id)
            wms_code_obj_unit_price = wms_code_obj.filter(unit_price__gt=0).only('quantity', 'unit_price')
            total_wms_qty_unit_price = sum(wms_code_obj_unit_price.annotate(stock_value=Sum(F('quantity') * F('unit_price'))).values_list('stock_value',flat=True))
            wms_code_obj_sku_unit_price = wms_code_obj.filter(unit_price=0).only('quantity', 'sku__cost_price')
            total_wms_qty_sku_unit_price = sum(wms_code_obj_sku_unit_price.annotate(stock_value=Sum(F('quantity') * F('sku__cost_price'))).values_list('stock_value',flat=True))
            total_stock_value = total_wms_qty_unit_price + total_wms_qty_sku_unit_price
            if sku_pack_config == 'true':
                sku_pack_obj = sku.skupackmaster_set.filter().only('pack_quantity')
                if sku_pack_obj.exists() and sku_pack_obj[0].pack_quantity:
                    sku_packs = int(quantity / sku_pack_obj[0].pack_quantity)
        open_order_qty = sku_type_qty.get(data[0], 0)
        temp_data['aaData'].append(OrderedDict((('WMS Code', data[0]), ('Product Description', data[1]),
                                                ('SKU Category', data[2]), ('SKU Brand', data[3]),
                                                ('sku_packs',sku_packs),
                                                ('Available Quantity', quantity),
                                                ('Reserved Quantity', reserved), ('Total Quantity', total),
						 ('Open Order Quantity', open_order_qty),
                                                ('Unit of Measurement', sku.measurement_type), ('Stock Value', total_stock_value ),
                                                ('DT_RowId', data[0]) )))


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
def get_quantity_data(user_groups, sku_codes_list,asn_true=False):
    ret_list = []

    stock_user_dict, purch_dict = {}, {}
    stock_qty_qs = StockDetail.objects.filter(sku__user__in=user_groups).exclude(location__zone__zone='DAMAGED_ZONE').only(
        'sku__sku_code').values_list('sku__user', 'sku__sku_code').distinct().annotate(total=Sum('quantity'))
    for user, sku_code, qty in stock_qty_qs:
        stock_user_dict.setdefault(str(user), {})
        stock_user_dict[str(user)][sku_code] = qty

    purch_sku_qty_qs = PurchaseOrder.objects.filter(open_po__sku__user__in=user_groups).\
        exclude(status__in=['location-assigned', 'confirmed-putaway']). \
        only('open_po__sku__user', 'open_po__sku__sku_code').values('open_po__sku__user', 'open_po__sku__sku_code'). \
        annotate(total_order=Sum('open_po__order_quantity'), total_received=Sum('received_quantity'))
    for purch_map in purch_sku_qty_qs:
        user = purch_map['open_po__sku__user']
        sku_code = purch_map['open_po__sku__sku_code']
        total_order = purch_map['total_order']
        total_received = purch_map['total_received']
        purch_dict.setdefault(str(user), {})
        purch_dict[str(user)][sku_code] = {'total_order': total_order, 'total_received': total_received}

    enq_block_stock_map = {}
    enq_block_stock_qs = EnquiredSku.objects.filter(sku__user__in=user_groups).exclude(warehouse_level=3).filter(
        ~Q(enquiry__extend_status='rejected')).only('sku_code').values_list('sku__user', 'sku_code').annotate(Sum('quantity'))
    for user, sku_code, qty in enq_block_stock_qs:
        enq_block_stock_map.setdefault(str(user), {})
        enq_block_stock_map[str(user)][sku_code] = qty

    for user in user_groups:
        user_sku_codes = SKUMaster.objects.filter(user=user)
        ware = User.objects.filter(id=user).values_list('username', flat=True)[0]
        pick_reserved_dict = dict(PicklistLocation.objects.filter(stock__sku__user=user, status=1, reserved__gt=0).
                                only('stock__sku__sku_code').
                                  values_list('stock__sku__sku_code').annotate(Sum('reserved')))
        raw_reserved_dict = dict(
            RMLocation.objects.filter(status=1, material_picklist__jo_material__material_code__user=user). \
            only('material_picklist__jo_material__material_code__wms_code').\
            values_list('material_picklist__jo_material__material_code__wms_code').distinct(). \
            annotate(rm_reserved=Sum('reserved')))
        # enq_block_stock = dict(EnquiredSku.objects.filter(sku__user=user).exclude(warehouse_level=3).filter(
        #     ~Q(enquiry__extend_status='rejected')).only('sku_code').values_list('sku_code').annotate(Sum('quantity')))

        # ASN Stock Related to SM
        today_filter = datetime.datetime.today()
        #hundred_day_filter = today_filter + datetime.timedelta(days=100)
        ints_filters = {'quantity__gt': 0, 'sku__user': user, 'status': 'open'}
        asn_qs = ASNStockDetail.objects.filter(**ints_filters)
        intr_obj_100days_qs = asn_qs
        intr_obj_100days_ids = intr_obj_100days_qs.values_list('id', flat=True)
        asnres_det_qs = ASNReserveDetail.objects.filter(asnstock__in=intr_obj_100days_ids)
        asn_res_100days_qs = asnres_det_qs.filter(orderdetail__isnull=False)  # Reserved Quantity
        asn_res_100days_qty = dict(
            asn_res_100days_qs.only('asnstock__sku__sku_code').values_list('asnstock__sku__sku_code').annotate(in_res=Sum('reserved_qty')))
        asn_blk_100days_qs = asnres_det_qs.filter(orderdetail__isnull=True, enquirydetail__warehouse_level=3)  # Blocked Quantity
        asn_blk_100days_qty = dict(
            asn_blk_100days_qs.only('asnstock__sku__sku_code').values_list('asnstock__sku__sku_code').annotate(in_res=Sum('reserved_qty')))

        asn_avail_stock = dict(
            intr_obj_100days_qs.only('sku__sku_code').values_list('sku__sku_code').distinct().annotate(in_asn=Sum('quantity')))
        non_kitted_stock = dict(asn_qs.filter(asn_po_num='NON_KITTED_STOCK').only('sku__sku_code').values_list('sku__sku_code').
                                distinct().annotate(non_kitted_qty=Sum('quantity')))
        for single_sku in sku_codes_list:
            exist = user_sku_codes.filter(sku_code=single_sku)
            asn_stock_qty = asn_avail_stock.get(single_sku, 0)
            asn_res_qty = asn_res_100days_qty.get(single_sku, 0)
            asn_blk_qty = asn_blk_100days_qty.get(single_sku, 0)
            non_kitted_qty = non_kitted_stock.get(single_sku, 0)
            if not exist:
                available = 'No SKU'
                reserved = 0
                ret_list.append({'available': available, 'name': ware, 'transit': 0, 'reserved': reserved, 'user': user,
                                 'sku_code': single_sku, 'asn': asn_stock_qty, 'blocked': 0, 'asn_res': asn_res_qty,
                                 'asn_blocked': asn_blk_qty, 'non_kitted': 0})
                continue
            trans_quantity = 0
            if single_sku in purch_dict.get(str(user), []):
                trans_quantity = purch_dict[str(user)][single_sku]['total_order'] - purch_dict[str(user)][single_sku]['total_received']
            quantity = stock_user_dict.get(str(user), {}).get(single_sku, 0)
            pic_reserved = pick_reserved_dict.get(single_sku, 0)
            raw_reserved = raw_reserved_dict.get(single_sku, 0)
            enq_reserved = enq_block_stock_map.get(str(user), {}).get(single_sku, 0)
            if not asn_true:
                available = quantity - pic_reserved
            else:
                available = quantity
            if available < 0:
                available = 0
            ret_list.append({'available': available, 'name': ware, 'transit': trans_quantity, 'reserved': pic_reserved,
                             'user': user, 'sku_code': single_sku, 'asn': asn_stock_qty, 'blocked': enq_reserved,
                             'asn_res': asn_res_qty, 'asn_blocked': asn_blk_qty, 'non_kitted': non_kitted_qty})
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


def get_availasn_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    data, temp_data, other, da = get_warehouses_stock(start_index, stop_index, temp_data, search_term, order_term,
                                                      col_num, request, user, filters, asn_true=True)

    list_da = {}
    for i in da:
        if i['available'] is None:
            i['available'] = 0
        list_da[i['ware']] = i['available']

    temp_data['ware_list'] = list_da
    for one_data, sku_det in zip(data, other['rem']):
        header = other['header']
        var = OrderedDict()
        var[header[0]] = sku_det['single_sku']
        for wh in one_data:
            stats = ['-Total', '-Res', '-Blocked', '-Open', '-NK']
            for stat in stats:
                var[wh['name'] + stat] = 0
        var['ASN Total'] = 0
        var['ASN Res'] = 0
        var['ASN Blocked'] = 0
        var['ASN Open'] = 0
        var['NON_KITTED'] = 0
        for single in one_data:
            if single['name']:
                wh_name = single['name']
                var[wh_name + '-Total'] = single['available']
                fg_stock = single['available'] - single['non_kitted']
                var[wh_name + '-Stock'] = fg_stock
                var[wh_name + '-Res'] = single['reserved']
                var[wh_name + '-Blocked'] = single['blocked']
                var[wh_name + '-NK'] = single['non_kitted']
                if not isinstance(single['available'], float):
                    single['available'] = 0
                net_amt = single['available'] - single['blocked'] - single['reserved'] - single['non_kitted']
                if net_amt < 0:
                    net_amt = 0
                var[wh_name + '-Open'] = net_amt
                wh_level_stock_map = {'WH Net Open': net_amt, 'Total WH': single['available'],
                                      'Total WH Res': single['reserved'], 'Total WH Blocked': single['blocked'],
                                      'ASN Total': single['asn'], 'ASN Res': single['asn_res'],
                                      'ASN Blocked': single['asn_blocked'], 'NON_KITTED': single['non_kitted'],
                                      'Total Stock': fg_stock}

                for header, val in wh_level_stock_map.items():
                    if header in var:
                        var[header] += val
                    else:
                        var[header] = val
                net_open = var['Total Stock'] - var['Total WH Res'] - var['Total WH Blocked']
                var['WH Net Open'] = net_open
                asn_open = var['ASN Total'] - var['ASN Res'] - var['ASN Blocked']
                var['ASN Open'] = asn_open
        var['Net Open'] = var['WH Net Open'] + var['ASN Open']

        temp_data['aaData'].append(var)


def get_warehouses_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters,
                         asn_true=False):
    data_to_send = []
    other_data = {}
    if asn_true:
        lis = ['sku_code']
    else:
        lis = ['sku_code', 'sku_brand', 'sku_desc', 'sku_category']

    if len(filters) <= 4:
        search_params = get_filtered_params(filters, lis)
    else:
        search_params = {}

    if col_num <= 3:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data

    warehouses = UserGroups.objects.filter(admin_user_id=user.id,
                                           user__userprofile__warehouse_level=1).values_list('user_id', flat=True)
    ware_list = list(User.objects.filter(id__in=warehouses).values_list('username', flat=True))
    ware_list.append(user.username)
    if asn_true:
        header = ["SKU Code"]
    else:
        header = ["SKU Code", "SKU Brand", "SKU Description", "SKU Category"]
        # headers = header + ware_list

    user_groups = UserGroups.objects.filter(Q(admin_user_id=user.id) | Q(user_id=user.id))
    if user_groups:
        admin_user_id = user_groups[0].admin_user_id
    else:
        admin_user_id = user.id
    if asn_true:
        user_group_filters = {'admin_user_id': admin_user_id, 'user__userprofile__warehouse_level': 1}
    else:
        user_group_filters = {'admin_user_id': admin_user_id}
    user_groups = list(UserGroups.objects.filter(**user_group_filters).values_list('user_id', flat=True))
    user_groups.append(admin_user_id)
    permissions = get_user_permissions(request, request.user)
    if request.user.userprofile.warehouse_type == 'CENTRAL_ADMIN' and permissions['permissions']['add_networkmaster'] :
        sku_master = SKUMaster.objects.filter(user__in=user_groups, status=1, **search_params)
    else:
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

    if asn_true:
        user_quantity_dict = get_quantity_data(user_groups, sku_codes[start_index:stop_index], asn_true=True)
        for single_sku in sku_codes[start_index:stop_index]:
            quantity = filter(lambda d: d['sku_code'] == single_sku, user_quantity_dict)
            data_to_send.append(quantity)
            other_data['rem'].append({'single_sku': single_sku})
    else:
        user_quantity_dict = get_quantity_data(user_groups, sku_codes[start_index:stop_index])
        sku_master_dat = sku_master.values('sku_code', 'sku_desc', 'sku_brand', 'sku_category').distinct()
        sku_descs = dict(zip(map(lambda d: d['sku_code'], sku_master_dat), map(lambda d: d['sku_desc'], sku_master_dat)))
        sku_brands = dict(zip(map(lambda d: d['sku_code'], sku_master_dat), map(lambda d: d['sku_brand'], sku_master_dat)))
        sku_categorys = dict(
            zip(map(lambda d: d['sku_code'], sku_master_dat), map(lambda d: d['sku_category'], sku_master_dat)))
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
    stock_qty_map = dict(StockDetail.objects.exclude(receipt_number=0).filter(sku__wms_code__in=sku_list,
                                                                         sku__user__in=user_groups).only(
        'quantity').values_list('sku__user').annotate(Sum('quantity')))
    res_qty_map = dict(PicklistLocation.objects.filter(stock__sku__sku_code__in=sku_list, stock__sku__user__in=user_groups,
                                                   status=1).only('stock__sku__user').values_list('stock__sku__user').annotate(Sum('reserved')))
    raw_res_qty_map = dict(RMLocation.objects.filter(status=1, stock__sku__user__in=user_groups).
                           only('stock__sku__user').values_list('stock__sku__user').annotate(Sum('reserved')))
    enq_block_stock_map = dict(EnquiredSku.objects.filter(sku__user__in=users_objs, sku__sku_code__in=sku_list).filter(
        ~Q(enquiry__extend_status='rejected')).only('sku__user').values_list('sku__user').annotate(Sum('quantity')))

    for user in users_objs:
        available = 0
        total = stock_qty_map.get(user.id, 0)
        reserved = res_qty_map.get(user.id, 0)
        raw_reserved = raw_res_qty_map.get(user.id, 0)
        enq_block_stock = enq_block_stock_map.get(user.id, 0)
        purch = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).filter(
            open_po__sku__user=user.id, open_po__sku__sku_code__in=sku_list).only('open_po__sku__sku_code').\
            values('open_po__sku__sku_code').annotate(total_order=Sum('open_po__order_quantity'),
                                                      total_received=Sum('received_quantity'))

        today_filter = datetime.datetime.today()
        hundred_day_filter = today_filter + datetime.timedelta(days=100)
        ints_filters = {'quantity__gt': 0, 'sku__sku_code__in': sku_list, 'sku__user': user.id, 'status': 'open'}
        asn_qs = ASNStockDetail.objects.filter(**ints_filters)
        intr_obj_100days_qs = asn_qs.exclude(arriving_date__lte=today_filter).filter(
            arriving_date__lte=hundred_day_filter)
        intr_obj_100days_ids = intr_obj_100days_qs.values_list('id', flat=True)
        asn_res_100days_qs = ASNReserveDetail.objects.filter(asnstock__in=intr_obj_100days_ids)
        asn_res_100days_qty = asn_res_100days_qs.only('asnstock__sku__sku_code').values_list('asnstock__sku__sku_code').aggregate(Sum('reserved_qty'))['reserved_qty__sum']

        asn_total_qty = intr_obj_100days_qs.only('sku__sku_code').values_list('sku__sku_code').distinct().aggregate(Sum('quantity'))['quantity__sum']
        if not asn_res_100days_qty:
            asn_res_100days_qty = 0
        if not asn_total_qty:
            asn_total_qty = 0
        asn_avail_stock = asn_total_qty - asn_res_100days_qty
        total_order = sum(map(lambda d: d['total_order'], purch))
        total_received = sum(map(lambda d: d['total_received'], purch))
        trans_quantity = float(total_order) - float(total_received)
        trans_quantity = round(trans_quantity, 2)
        if total:
            available = total
        if asn_avail_stock:
            available = available + asn_avail_stock
        if not reserved:
            reserved = 0
        if raw_reserved:
            reserved += raw_reserved
        if enq_block_stock:
            reserved += enq_block_stock
        available -= reserved
        if available < 0:
            available = 0
        available = round(available, 2)
        reserved = round(reserved, 2)
        ware_name = user.username
        data.append({'ware': ware_name, 'available': available, 'reserved': reserved, 'transit': trans_quantity,
                     'asn': asn_avail_stock})
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
           'receipt_type', 'stock_value', 'pallet_detail__pallet_code']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_params = get_filtered_params(filters, lis)
    if 'receipt_date__icontains' in search_params:
        search_params['receipt_date__regex'] = search_params['receipt_date__icontains']
        del search_params['receipt_date__icontains']
    search_params['sku_id__in'] = sku_master_ids
    if search_term:
        master_data = StockDetail.objects.filter(quantity__gt=0).exclude(receipt_number=0).select_related('sku', 'location',
                                                'location__zone', 'pallet_detail').\
            annotate(stock_value=Sum(F('quantity') * F('sku__cost_price')) ).\
            filter(Q(receipt_number__icontains=search_term) | Q(sku__wms_code__icontains=search_term) |
                   Q(quantity__icontains=search_term) | Q(location__zone__zone__icontains=search_term) |
                   Q(sku__sku_code__icontains=search_term) | Q(sku__sku_desc__icontains=search_term) |
                   Q(location__location__icontains=search_term) | Q(stock_value__icontains=search_term),
                   sku__user=user.id).filter(**search_params).order_by(order_data)
    else:
        master_data = StockDetail.objects.filter(quantity__gt=0).exclude(receipt_number=0).select_related('sku', 'location',
                                                'location__zone', 'pallet_detail').\
                            annotate( stock_value=Sum(F('quantity') * F('sku__cost_price')) ).\
                            filter(sku__user=user.id, **search_params).order_by(order_data)

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    pallet_switch = get_misc_value('pallet_switch', user.id)
    for data in master_data[start_index:stop_index]:
        _date = get_local_date(user, data.receipt_date, True)
        _date = _date.strftime("%d %b, %Y")
        stock_quantity = get_decimal_limit(user.id, data.quantity)
        taken_unit_price = data.unit_price
        if not taken_unit_price:
            taken_unit_price = data.sku.cost_price
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
                                                    ('Quantity', stock_quantity),
                                                    ('Pallet Code', pallet_code), ('Receipt Type', data.receipt_type),
                                                    ('Stock Value', taken_unit_price * stock_quantity)
                                                    )))
        else:
            temp_data['aaData'].append(OrderedDict((('Receipt ID', data.receipt_number), ('DT_RowClass', 'results'),
                                                    ('Receipt Date', _date), ('SKU Code', data.sku.sku_code),
                                                    ('WMS Code', data.sku.wms_code),
                                                    ('Product Description', data.sku.sku_desc),
                                                    ('Zone', data.location.zone.zone),
                                                    ('Location', data.location.location),
                                                    ('Quantity', stock_quantity),
                                                    ('Receipt Type', data.receipt_type),
                                                    ('Stock Value', taken_unit_price * stock_quantity)
                                                    )))


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
    batch_no = request.GET.get('batch_number', '')
    mrp =request.GET.get('mrp', '')
    weight = request.GET.get('weight', '')
    status = move_stock_location(cycle_id, wms_code, source_loc, dest_loc, quantity, user, seller_id, batch_no=batch_no, mrp=mrp,
                                 weight=weight)
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
    size_list = []
    market_places = []
    level = request.GET.get('level', '')
    alternative_view = request.GET.get('alternate_view', 'false')
    warehouse_name = request.GET.get('warehouse_name', '')
    price_band_flag = get_misc_value('priceband_sync', user.id)
    size_name = request.GET.get("size_type_value", '')
    marketplace = request.GET.get("marketplace", '')
    size_list, user_list = [], []
    default_size = ['S', 'M', 'L', 'XL', 'XXL']
    user_id = user.id
    if price_band_flag == 'true':
        user = get_admin(user)
    if user.userprofile.warehouse_type == 'CENTRAL_ADMIN':
        header = ["SKU Code"]
    else:
        header = ["SKU Code", "SKU Brand", "SKU Description", "SKU Category"]
    if alternative_view == 'true':
        header = ["SKU Class", "Style Name", "Brand", "SKU Category"]
        if not warehouse_name:
            user_list = [user.username]
            admin_user = UserGroups.objects.filter(Q(admin_user__username__iexact=user.username) | Q(user__username__iexact=user.username)). \
                values_list('admin_user_id', flat=True)
            user_groups = UserGroups.objects.filter(admin_user_id__in=admin_user).values('user__username',
                'admin_user__username')
            for users in user_groups:
                for key, value in users.iteritems():
                    if user.username != value and value not in user_list:
                        user_list.append(value)
            warehouse_name = user_list[0]
        user_id = User.objects.get(username = warehouse_name).id
        #get marketplace
        market_places = OrderDetail.objects.filter(user=user_id).values_list('marketplace', flat=True).distinct()
        market_places = [item for item in market_places]

        size_master_objs = SizeMaster.objects.filter(user=user_id)
        size_names = size_master_objs.values_list('size_name', flat=True)
        all_sizes = size_master_objs
        if size_name:
            all_sizes = size_master_objs.filter(size_name=size_name)
        sizes = []
        if all_sizes:
            sizes = all_sizes[0].size_value.split("<<>>")
        else:
            sizes = default_size
        if not len(size_names):
            size_names = ['Default']
        size_list = list(size_names)
        #each_sizes for each names
        string = 'Sales - '
        size_for_each_names = sizes
        '''
        warehouses = UserGroups.objects.filter(admin_user_id=user.id).values_list('user_id', flat=True)
        if level:
            warehouses = UserProfile.objects.filter(user__in=warehouses,warehouse_level=int(level)).values_list('user_id',flat=True)
        ware_list = list(User.objects.filter(id__in=warehouses).values_list('username', flat=True))

        user_groups = UserGroups.objects.filter(Q(admin_user_id=user.id) | Q(user_id=user.id))
        if user_groups:
            admin_user_id = user_groups[0].admin_user_id
            admin_user_name = user_groups[0].admin_user.username
        else:
            admin_user_id = user.id
            admin_user_name = user.username
        if level:
            headers = header + ware_list
        else:
            headers = header + [admin_user_name] + ware_list
        '''
        normal_size_list = sizes + ['Total']
        sales_prefix_size_for_each_names = [string + x for x in sizes] + ['Sales - Total']
        headers = header + normal_size_list + sales_prefix_size_for_each_names
    else:
        warehouses = UserGroups.objects.filter(admin_user_id=user_id).values_list('user_id', flat=True)
        if level:
            warehouses = UserProfile.objects.filter(user__in=warehouses,warehouse_level=int(level)).values_list('user_id',flat=True)
        ware_list = list(User.objects.filter(id__in=warehouses).values_list('username', flat=True))
        user_groups = UserGroups.objects.filter(Q(admin_user_id=user_id) | Q(user_id=user_id))
        if user_groups:
            admin_user_id = user_groups[0].admin_user_id
            admin_user_name = user_groups[0].admin_user.username
        else:
            admin_user_id = user_id
            admin_user_name = user.username
        if level:
            warehouse_suffixes = ['Total', 'Stock', 'NK', 'Res', 'Blocked', 'Open']
            wh_list = []
            for wh in ware_list:
                wh_list.extend(list(map(lambda x: wh+'-'+x, warehouse_suffixes)))
            total_wh_dets = ['Total WH', 'Total WH Res', 'Total WH Blocked']
            wh_list.extend(total_wh_dets)
            wh_list.append('WH Net Open')
            intr_headers = ['ASN Total', 'ASN Res', 'ASN Blocked', 'ASN Open', 'Net Open']
            wh_list.extend(intr_headers)
            wh_list.append('NON_KITTED')
            headers = header + wh_list
        else:
            headers = header + [admin_user_name] + ware_list
    return HttpResponse(json.dumps({'table_headers': headers, 'size_types': size_list,
                                    'warehouse_names': user_list, 'market_places': market_places }))

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
    industry_type = user.userprofile.industry_type
    pallet_switch = get_misc_value('pallet_switch', user.id)
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
        location = stock.location.location
        zone = stock.location.zone.zone
        pallet_number, batch, mrp = ['']*3
        if pallet_switch == 'true' and stock.pallet_detail:
            pallet_number = stock.pallet_detail.pallet_code
        if industry_type == "FMCG" and stock.batch_detail:
            batch_detail = stock.batch_detail
            batch = batch_detail.batch_no
            mrp = batch_detail.mrp
        cond = str((zone, location, pallet_number, batch, mrp))
        zones_data.setdefault(cond, {'zone': zone, 'location': location,
                                                         'pallet_number': pallet_number, 'total_quantity': 0,
                                                        'reserved_quantity': 0, 'batch': batch, 'mrp': mrp})
        zones_data[cond]['total_quantity'] += seller_stock.quantity
        zones_data[cond]['reserved_quantity'] += res_qty
        #zones_data[stock.location.zone.zone][stock.location.location][0] += seller_stock.quantity

    return HttpResponse(json.dumps({'zones_data': zones_data.values()}))


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
        user_dict ={}
        users_list = []
        user_dict['user_id'] = user.id
        user_dict['user__username'] = user.username
        users_list.append(user_dict)
        if request.POST.get('datatable','') == 'SerialNumberSKU':
            sister_warehouses = get_sister_warehouse(user)
            sister_warehouse_list = []
            sister_warehouses = sister_warehouses.values('user_id','user__username')
            sister_warehouse_list = list(sister_warehouses)
            sister_warehouse_list.insert(0,user_dict)
            users_list = sister_warehouse_list
        workbook = xlsxwriter.Workbook(path)
        for user_obj in users_list :
            worksheet = workbook.add_worksheet(user_obj['user__username'])
            bold = workbook.add_format({'bold': True})
            exc_headers = ['SKU Code', 'Product Description', 'SKU Brand', 'SKU Category', 'Serial Number', 'Status',
                           'Reason']
            for n, header in enumerate(exc_headers):
                worksheet.write(0, n, header, bold)
            dict_list = ['sku__sku_code', 'sku__sku_desc',
                         'sku__sku_brand', 'sku__sku_category',
                         'status', 'imei_number']

            filter_params = get_filtered_params(filters, dict_list)
            dispatched_imeis = OrderIMEIMapping.objects.filter(status=1, order__user=user_obj['user_id'], po_imei__isnull=False).values_list('po_imei_id', flat=True)
            damaged_returns = dict(ReturnsIMEIMapping.objects.filter(status='damaged', order_imei__order__user=user_obj['user_id']). \
                                   values_list('order_imei__po_imei__imei_number', 'reason'))
            qc_damaged = dict(QCSerialMapping.objects.filter(serial_number__purchase_order__open_po__sku__user=user_obj['user_id'],
                                                             status='rejected').values_list('serial_number__imei_number',
                                                                                            'reason'))
            qc_damaged.update(damaged_returns)
            accepted_imeis = list(POIMEIMapping.objects.filter(status=1, sku__user=user_obj['user_id'],
                                                         **filter_params).exclude(id__in=dispatched_imeis).values_list('id', flat=True))
            po_rejected_imeis = list(QCSerialMapping.objects.filter(serial_number__purchase_order__open_po__sku__user=user_obj['user_id'],
                                                             status='rejected').values_list('serial_number_id', flat=True))
            picklist_rejected_imeis = list(DispatchIMEIChecklist.objects.filter(final_status=0, po_imei_num__sku__user=user_obj['user_id'],
                                                             qc_type='sales_order').values_list('po_imei_num_id', flat=True).distinct())
            common_list = accepted_imeis + po_rejected_imeis + picklist_rejected_imeis
            filter_params['id__in'] = common_list
            if search_term:
                imei_data = POIMEIMapping.objects.filter(Q(sku__sku_code__icontains=search_term) |
                                                         Q(sku__sku_desc__icontains=search_term) |
                                                         Q(sku__sku_brand__icontains=search_term) |
                                                         Q(sku__sku_category__icontains=search_term),
                                                         sku__user=user_obj['user_id'],
                                                         **filter_params). \
                    exclude(id__in=dispatched_imeis).values_list(*dict_list)
            else:
                imei_data = POIMEIMapping.objects.filter(sku__user=user_obj['user_id'],
                                                         **filter_params). \
                    exclude(id__in=dispatched_imeis).values_list(*dict_list)
            row = 1
            for imei in imei_data:
                col_count = 0
                for col, data in enumerate(imei):
                    if col == 4: continue
                    worksheet.write(row, col_count, data)
                    col_count += 1
                imei_status = 'Accepted'
                reason = ''
                if imei[4] != 1:
                    imei_status = 'Rejected'
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

    data_dict = dict(request.POST.iterlists())
    src_sku = request.POST.get('src_sku_code', '')
    src_qty = request.POST.get('src_quantity', '')
    src_loc = request.POST.get('src_location', '')
    src_batch_no = request.POST.get('src_batch_number', '')
    src_mrp = request.POST.get('src_mrp', 0)
    seller_id = request.POST.get('seller_id', '')
    weight = request.POST.get('src_weight', '')
    if user.userprofile.user_type == 'marketplace_user' and not seller_id:
        return HttpResponse('Seller ID is Mandatory')
    if not src_sku and not dest_sku and not src_qty and not dest_qty and not src_loc and not dest_loc:
        return HttpResponse('Please Send Required Field')
    if seller_id:
        seller = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
        if not seller:
            return HttpResponse('Invalid Seller Id')
        else:
            seller_id = seller[0].id
    src_sku = SKUMaster.objects.filter(user=user.id, sku_code=src_sku)
    if not src_sku:
        return HttpResponse('Source SKU Code Not Found')
    source_sku = src_sku[0]
    src_loc = LocationMaster.objects.filter(zone__user=user.id, location=src_loc)
    if not src_loc:
        return HttpResponse('Source Location Not Found')
    source_location = src_loc[0]
    try:
        src_qty = float(src_qty)
    except ValueError:
        log.info("Substitution: Source Quantity Should Be Number ," + src_qty)
        return HttpResponse('Source Quantity Should Be Number')
    if float(src_qty) <= 0:
        return HttpResponse('Source Quantity Should Greater Than Zero')
    stock_dict = {"sku_id": source_sku.id, "location_id": source_location.id,
                  "sku__user": user.id, "quantity__gt": 0}
    if seller_id:
        stock_dict['sellerstock__seller_id'] = seller_id
    if src_batch_no:
        stock_dict['batch_detail__batch_no'] = src_batch_no
    if src_mrp:
        stock_dict['batch_detail__mrp'] = src_mrp
    if weight :
        stock_dict['batch_detail__weight'] = weight
    src_stocks = StockDetail.objects.filter(**stock_dict)
    src_stock_count = src_stocks.aggregate(Sum('quantity'))['quantity__sum']
    if not src_stock_count:
        return HttpResponse('Source SKU Code Don\'t Have Stock')
    elif src_stock_count < src_qty:
        return HttpResponse('Source SKU Code Have Stock, ' + str(src_stock_count))

    dest_list = []
    for ind in range(0, len(data_dict['dest_sku_code'])):
        dest_sku = SKUMaster.objects.filter(user=user.id, sku_code=data_dict['dest_sku_code'][ind])
        if not dest_sku:
            return HttpResponse('Destination SKU Code Not Found')
        dest_loc = LocationMaster.objects.filter(zone__user=user.id, location=data_dict['dest_location'][ind])
        if not dest_loc:
            return HttpResponse('Destination Location Not Found')
        dest_qty = data_dict['dest_quantity'][ind]
        try:
            dest_qty = float(dest_qty)
        except ValueError:
            log.info("Substitution: Destination Quantity Should Be Number ," + dest_qty)
            return HttpResponse('Destination Quantity Should Be Number')
        if float(dest_qty) <= 0:
            return HttpResponse('Destination Quantity Should Greater Than Zero')
        dest_filter = {'sku_id': dest_sku[0].id, 'location_id': dest_loc[0].id,
                       'sku__user': user.id}
        mrp_dict = {}
        if 'dest_batch_number' in data_dict.keys():
            mrp_dict['batch_no'] = data_dict['dest_batch_number'][ind]
            dest_filter['batch_detail__batch_no'] = data_dict['dest_batch_number'][ind]
            if data_dict['dest_mrp'][ind]:
                mrp_dict['mrp'] = data_dict['dest_mrp'][ind]
                dest_filter['batch_detail__mrp'] = data_dict['dest_mrp'][ind]
            if data_dict['dest_weight'][ind]:
                mrp_dict['weight'] = data_dict['dest_weight'][ind]
                dest_filter['batch_detail__weight'] = data_dict['dest_weight'][ind]


        if seller_id:
            dest_filter['sellerstock__seller_id'] = seller_id
        dest_stocks = StockDetail.objects.filter(**dest_filter)
        dest_list.append({'dest_sku': dest_sku[0], 'dest_loc': dest_loc[0], 'dest_qty': dest_qty,
                          'dest_stocks': dest_stocks, 'mrp_dict': mrp_dict})
    source_updated = False
    transact_number = get_max_substitute_allocation_id(user)
    for dest_dict in dest_list:
        update_substitution_data(src_stocks, dest_stocks, source_sku, source_location, src_qty, dest_dict['dest_sku'],
                                 dest_dict['dest_loc'], dest_dict['dest_qty'], user, seller_id,
                                 source_updated, dest_dict['mrp_dict'], transact_number)
        source_updated = True
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
            annotate(total=Sum('quantity')).filter(sku__user=user.id, status=1). \
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
                                                (' ', '<button type="button" name="submit" ng-click="showCase.inv_adj_save_qty('+"'"+str(ind)+"'"+', showCase.available_qty_val_'+str(ind)+', '+"'"+str(int(quantity))+"'"+', showCase.add_qty_val_'+str(ind)+', showCase.sub_qty_val_'+str(ind)+')" ng-disabled="showCase.button_edit" disabled class="btn btn-primary ng-click-active" >Save</button>'))))


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
            save_sku_stats(user, sku_id, inventory_create_new.id, 'inventory-adjustment', stock_new_create['quantity'], inventory_create_new)
        if old_available_qty != available_qty or sub_qty:
            stock_qty_update = {}
            if location_id:
                stock_qty_update['location_id'] = location_id
            if sku_id:
                stock_qty_update['sku_id'] = sku_id
            if pallet_id:
                stock_qty_update['pallet_detail_id'] = pallet_id
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
                        save_reduced_qty = obj_qty
                        if save_reduced_qty >= sub_qty:
                            diff_qty = int(save_reduced_qty)-int(sub_qty)
                            stock_obj = StockDetail.objects.filter(id=ob.id)
                            stock_obj.update(quantity=diff_qty)
                            save_sku_stats(user, sku_id, ob.id, 'inventory-adjustment', diff_qty, stock_obj)
                            update_cycle_count_inventory_adjustment(user, sku_id, location_id, old_available_qty, available_qty, pallet_id)
                            sub_qty = 0
                        elif save_reduced_qty:
                            sub_qty = int(sub_qty)-int(save_reduced_qty)
                            stock_obj = StockDetail.objects.filter(id=ob.id)
                            stock_obj.update(quantity=0)
                            save_sku_stats(user, sku_id, ob.id, 'inventory-adjustment', 0, stock_obj)
                            update_cycle_count_inventory_adjustment(user, sku_id, location_id, old_available_qty, available_qty, pallet_id)
                            continue
                        if not sub_qty:
                            break
            elif sub_qty and inventory_update_adj:
                for ob in inventory_update_adj:
                    reserve_qty = 0
                    raw_reserve_qty = 0
                    save_reduced_qty = 0
                    picklist_location_stock_query_list = ['stock__sku__wms_code', 'stock__location__location']
                    if pallet_code_enabled=='true':
                        picklist_location_stock_query_list.append('stock__pallet_detail__pallet_code')
                    rm_location_query_list = ['material_picklist__jo_material__material_code__wms_code', 'stock__location__location']
                    if pallet_code_enabled=='true':
                        rm_location_query_list.append('stock__pallet_detail__pallet_code')
                    reserved_instances = PicklistLocation.objects.filter(status=1, stock__sku__user=user.id, stock__sku__wms_code = ob.sku.wms_code, stock__location__location = ob.location.location).values(*picklist_location_stock_query_list).distinct().annotate(reserved=Sum('reserved'))
                    raw_res_instances = RMLocation.objects.filter(status=1, stock__sku__user=user.id, stock__sku__wms_code = ob.sku.wms_code, stock__location__location = ob.location.location).values(*rm_location_query_list).distinct().annotate(rm_reserved=Sum('reserved'))
                    reserve = map(lambda d: d['reserved'], reserved_instances)
                    if reserve:
                        reserve_qty = reserve[0]
                    raw_reserve = map(lambda d: d['rm_reserved'], raw_res_instances)
                    if raw_reserve:
                        raw_reserve_qty = raw_reserve[0]
                    total_reserve_qty = reserve_qty + raw_reserve_qty
                    obj_qty = ob.quantity
                    save_reduced_qty = obj_qty
                    if save_reduced_qty >= sub_qty:
                        diff_qty = int(save_reduced_qty)-int(sub_qty)
                        ob.quantiy = diff_qty
                        stock_obj = StockDetail.objects.filter(id=ob.id)
                        stock_obj.update(quantity=diff_qty)
                        save_sku_stats(user, sku_id, ob.id, 'inventory-adjustment', diff_qty, stock_obj)
                        update_cycle_count_inventory_adjustment(user, sku_id, location_id, old_available_qty, available_qty, pallet_id)
                        sub_qty = 0
                    elif save_reduced_qty:
                        sub_qty = int(sub_qty)-int(save_reduced_qty)
                        stock_obj = StockDetail.objects.filter(id=ob.id)
                        stock_obj.update(quantity=0)
                        save_sku_stats(user, sku_id, ob.id, 'inventory-adjustment', 0, stock_obj)
                        update_cycle_count_inventory_adjustment(user, sku_id, location_id, old_available_qty, available_qty, pallet_id)
                        continue
                    if not sub_qty:
                        break
    return HttpResponse(json.dumps({'status': True, 'message':message}))

@csrf_exempt
@login_required
@get_admin_user
def inventory_adj_reasons(request, user=''):
    reasons = ''
    reasons = get_misc_value(request.POST['key'],user.id)

    return HttpResponse(json.dumps({"data": {'reasons': reasons.split(',')}}))


def get_batch_level_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                             filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['receipt_number', 'receipt_date', 'sku_id__wms_code', 'sku_id__sku_desc', 'batch_detail__batch_no',
           'batch_detail__mrp', 'batch_detail__weight', 'batch_detail__manufactured_date', 'batch_detail__expiry_date',
           'location__zone__zone', 'location__location', 'pallet_detail__pallet_code',
           'quantity', 'receipt_type']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_params = get_filtered_params(filters, lis)
    if 'receipt_date__icontains' in search_params:
        search_params['receipt_date__regex'] = search_params['receipt_date__icontains']
        del search_params['receipt_date__icontains']
    search_params['sku_id__in'] = sku_master_ids

    stock_detail_objs = StockDetail.objects.select_related('sku', 'location', 'location__zone', 'pallet_detail',
                                                           'batch_detail').prefetch_related('sku', 'location',
                                                                                            'location__zone').\
                                            exclude(receipt_number=0).filter(sku__user=user.id, quantity__gt=0,
                                                                             **search_params)
    if search_term:
        master_data = stock_detail_objs.filter(Q(receipt_number__icontains=search_term) |
                                                Q(sku__wms_code__icontains=search_term) |
                                               Q(quantity__icontains=search_term) |
                                                Q(location__zone__zone__icontains=search_term) |
                                               Q(sku__sku_code__icontains=search_term) |
                                               Q(sku__sku_desc__icontains=search_term) |
                                               Q(location__location__icontains=search_term)).order_by(order_data)

    else:
        master_data = stock_detail_objs.order_by(order_data)

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    counter = 1
    pallet_switch = get_misc_value('pallet_switch', user.id)
    for data in master_data[start_index:stop_index]:
        _date = get_local_date(user, data.receipt_date, True)
        _date = _date.strftime("%d %b, %Y")
        batch_no = manufactured_date = expiry_date = ''
        mrp = 0
        weight = ''
        if data.batch_detail:
            batch_no = data.batch_detail.batch_no
            mrp = data.batch_detail.mrp
            weight = data.batch_detail.weight
            manufactured_date = data.batch_detail.manufactured_date.strftime("%d %b %Y") if data.batch_detail.manufactured_date else ''
            expiry_date = data.batch_detail.expiry_date.strftime("%d %b %Y") if data.batch_detail.expiry_date else ''
        if pallet_switch == 'true':
            pallet_code = ''
            if data.pallet_detail:
                pallet_code = data.pallet_detail.pallet_code
            temp_data['aaData'].append(OrderedDict((('Receipt Number', data.receipt_number), ('DT_RowClass', 'results'),
                                                    ('Receipt Date', _date), ('SKU Code', data.sku.sku_code),
                                                    ('WMS Code', data.sku.wms_code),
                                                    ('Product Description', data.sku.sku_desc),
                                                    ('Batch Number', batch_no),
                                                    ('MRP', mrp), ('Weight', weight),
                                                    ('Manufactured Date', manufactured_date), ('Expiry Date', expiry_date),
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
                                                    ('MRP', mrp), ('Weight', weight), ('Manufactured Date', manufactured_date),
                                                    ('Expiry Date', expiry_date),
                                                    ('Zone', data.location.zone.zone),
                                                    ('Location', data.location.location),
                                                    ('Quantity', get_decimal_limit(user.id, data.quantity)),
                                                    ('Receipt Type', data.receipt_type))))


@login_required
@get_admin_user
def get_sku_batches(request, user=''):
    sku_batches = defaultdict(list)
    sku_weights = defaultdict(list)
    sku_batch_details = {}
    sku_weight_details = {}
    sku_code = request.GET.get('sku_code')
    sku_id = SKUMaster.objects.filter(user=user.id, sku_code=sku_code).only('id')
    if sku_id:
        sku_id = sku_id[0].id
        batch_obj = BatchDetail.objects.filter(stockdetail__sku=sku_id).values('batch_no', 'mrp', 'buy_price', 'manufactured_date', 'expiry_date', 'tax_percent', 'transact_type', 'transact_id', 'weight').distinct()
        for batch in batch_obj:
            sku_batches[batch['batch_no']].append(batch['mrp'])
            sku_batches[batch['batch_no']] = list(set(sku_batches[batch['batch_no']]))
            sku_weights[batch['batch_no']].append(batch['weight'])
            sku_weights[batch['batch_no']] = list(set(sku_weights[batch['batch_no']]))
            batch['manufactured_date'] = str(batch['manufactured_date'])
            batch['expiry_date'] = str(batch['expiry_date'])
            sku_batch_details.setdefault("%s_%s" % (batch['batch_no'], str(int(batch['mrp']))), []).append(batch)
            sku_weight_details.setdefault("%s_%s" % (batch['batch_no'], batch['weight']), []).append(batch)

    return HttpResponse(json.dumps({"sku_batches": sku_batches, "sku_batch_details": sku_batch_details,
                                    'sku_weights': sku_weights, 'sku_weight_details': sku_weight_details }))


@csrf_exempt
def get_alternative_warehouse_stock(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                                    filters={}, user_dict={}):
    """ This function delivers the alternate view of warehouse stock page """
    log.info(" ------------warehouse stock alternate view started ------------------")
    size_type_value = request.POST.get('size_type_value', '')
    warehouse_name = request.POST.get('warehouse_name', '')
    marketplace = request.POST.get('marketplace', '')
    view_type = request.POST.get('view_type', '')
    from_date = request.POST.get('from_date', '')
    to_date = request.POST.get('to_date', '')
    is_excel = request.POST.get('excel', 'false')
    st_time = datetime.datetime.now()
    warehouse = User.objects.get(username=warehouse_name)
    size_filter_params = {'user': warehouse.id}
    if not is_excel == 'true':
        size_filter_params['size_name'] = size_type_value
    size_master_objs = SizeMaster.objects.filter(**size_filter_params)
    sizes = ['S', 'M', 'L', 'XL', 'XXL']
    size_names = ['Default']
    if size_master_objs.exists():
        size_names = size_master_objs.values_list('size_name', flat=True)
        sizes = size_master_objs[0].size_value.split("<<>>")
    lis = ['sku_class', 'style_name', 'sku_brand', 'sku_category']
    all_dat = ['SKU Class', 'Style Name', 'Brand', 'SKU Category']
    keys_mapping =dict(zip(all_dat, lis))
    search_params = get_filtered_params(filters, all_dat)
    all_dat.extend(sizes)
    all_dat.extend(['Total'])
    for size_obj_name in sizes:
        all_dat.extend(['%s - %s' % ('Sales', size_obj_name)])
    all_dat.extend(['Sales - Total'])
    sort_col = all_dat[col_num]
    order_data = 'sku_class'
    if sort_col in keys_mapping.keys():
        order_data = lis[col_num]
        sort_col = ''
    if order_term == 'desc':
        order_data = '-%s' % order_data
    try:
        sku_master_objs = SKUMaster.objects.exclude(sku_class='').filter(user=warehouse.id,
                                                            sku_size__in=sizes, **search_params). \
                                            values('sku_class', 'style_name', 'sku_brand',
                                            'sku_category').distinct()
        if marketplace:
            sku_ids = OrderDetail.objects.filter(marketplace=marketplace, user=warehouse.id)\
                                 .values_list('sku_id', flat=True)
            sku_master_objs = sku_master_objs.filter(id__in=sku_ids)
        if search_term:
            sku_classes = sku_master_objs.filter(Q(sku_class__icontains=search_term) |
                                                 Q(style_name__icontains=search_term) |
                                                 Q(sku_brand__icontains=search_term) |
                                                 Q(sku_category__icontains=search_term)).order_by(order_data)

        else:
            sku_classes = sku_master_objs.order_by(order_data)
        sku_class_list = sku_classes.values_list('sku_class', flat=True).distinct()
        stock_detail_vals = {}
        pick_reserved_vals = {}
        raw_reserved_vals = {}
        if view_type in ['Available', 'Total']:
            stock_detail_vals = dict(StockDetail.objects.exclude(receipt_number=0).\
                                                filter(sku__user=warehouse.id, sku__sku_size__in=sizes,
                                                        sku__sku_class__in=sku_class_list,
                                                       quantity__gt=0).\
                                                annotate(sku_class_size=Concat('sku__sku_class', Value('<<>>'),
                                                        'sku__sku_size', output_field=CharField())).\
                                                values_list('sku_class_size').distinct().\
                                                annotate(total_sum=Sum('quantity')))
        if view_type in ['Reserved', 'Available']:
            pick_reserved_vals = dict(PicklistLocation.objects.filter(status=1, stock__sku__user=warehouse.id,
                                                                      stock__sku__sku_size__in=sizes,
                                                                      stock__sku__sku_class__in=sku_class_list). \
                                      annotate(sku_class_size=Concat('stock__sku__sku_class', Value('<<>>'),
                                                                'stock__sku__sku_size', output_field=CharField())). \
                                      values_list('sku_class_size').distinct().\
                                      annotate(reserved=Sum('reserved')))
            raw_reserved_vals = dict(RMLocation.objects.filter(status=1, stock__sku__user=warehouse.id,
                                                               stock__sku__sku_size__in=sizes,
                                                               stock__sku__sku_class__in=sku_class_list). \
                                     annotate(sku_class_size=Concat('stock__sku__sku_class', Value('<<>>'),
                                                                    'stock__sku__sku_size', output_field=CharField())).\
                                     values_list('sku_class_size').distinct(). \
                                     annotate(reserved=Sum('reserved')))
        order_filter_params = {'user': warehouse.id, 'quantity__gt': 0}
        if from_date:
            from_date = from_date.split('/')
            order_filter_params['creation_date__gt'] = datetime.date(int(from_date[2]), int(from_date[0]),
                                                                           int(from_date[1]))
        if to_date:
            to_date = to_date.split('/')
            to_date = datetime.date(int(to_date[2]), int(to_date[0]), int(to_date[1]))
            order_filter_params['creation_date__lt'] = datetime.datetime.combine(to_date + datetime.timedelta(1),
                                                                 datetime.time())
        if marketplace:
            order_filter_params['marketplace'] = marketplace

        order_detail_objs = OrderDetail.objects.filter(**order_filter_params).\
                                 exclude(status__in=[3,5])
        order_detail_vals = dict(order_detail_objs.filter(sku__sku_size__in=sizes,
                                                        sku__sku_class__in=sku_class_list).\
                                                annotate(sku_class_size=Concat('sku__sku_class', Value('<<>>'),
                                                        'sku__sku_size', output_field=CharField())).\
                                                values_list('sku_class_size').distinct().\
                                                annotate(total_sum=Sum('quantity')))
        temp_data['recordsTotal'] = sku_class_list.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']

        all_data = []
        looped_sku_class = []
        if not sort_col:
            sku_classes = sku_classes[start_index:stop_index]
        for sku_class in sku_classes:
            if sku_class['sku_class'] not in looped_sku_class:
                looped_sku_class.append(sku_class['sku_class'])
            else:
                continue
            size_dict = {}
            sales_dict = {}
            total = 0
            sale_total = 0
            for size in sizes:
                group_key = sku_class['sku_class'] + '<<>>' + size
                reserved = pick_reserved_vals.get(group_key, 0)
                reserved += raw_reserved_vals.get(group_key, 0)
                quant = stock_detail_vals.get(group_key, 0)
                if view_type == 'Available':
                    quant = quant - reserved
                    if quant < 0:
                        quant = 0
                elif view_type == 'Reserved':
                    quant = reserved
                total += quant
                size_dict.update({size: quant})
                order_qty = order_detail_vals.get(group_key, 0)
                sales_dict.update({'%s - %s' % ('Sales', size): order_qty})
                sale_total += order_qty

            data = OrderedDict((('SKU Class', sku_class['sku_class']), ('Style Name', sku_class['style_name']),
                                ('SKU Category', sku_class['sku_category']), ('Brand', sku_class['sku_brand']),
                                ('Total', total)))

            data.update(size_dict)
            data.update(sales_dict)
            data.update({'Sales - Total': sale_total})
            all_data.append(data)

        if sort_col:
            if order_term == 'asc':
                data_list = sorted(all_data, key=itemgetter(sort_col))
            else:
                data_list = sorted(all_data, key=itemgetter(sort_col), reverse=True)
            data_list = data_list[start_index: stop_index]
        else:
            data_list = all_data

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


def get_auto_sellable_suggestion_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, status):
    user_profile = UserProfile.objects.get(user_id=user.id)
    lis = ['stock__sku__sku_code', 'stock__sku__sku_desc', 'stock__location__location', 'quantity',
           'location__location', 'quantity']
    if user.userprofile.user_type == 'marketplace_user':
        lis.insert(1, 'seller__seller_id')
        lis.insert(2, 'seller__name')
    if user.userprofile.industry_type == 'FMCG':
        lis.insert(3, 'stock__batch_detail__batch_no')
        lis.insert(4, 'stock__batch_detail__mrp')
    master_data = SellableSuggestions.objects.filter(stock__sku__user=user.id, status=1)
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(lis, search_term)
        master_data = master_data.filter(search_query)
    master_data = master_data.order_by(order_data)
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    for data in master_data[start_index:stop_index]:
        data_dict = OrderedDict()
        if user_profile.user_type == 'marketplace_user':
            data_dict['Seller ID'] = data.seller.seller_id
            data_dict['Seller Name'] = data.seller.name
        data_dict['SKU Code'] = data.stock.sku.sku_code
        data_dict['Product Description'] = data.stock.sku.sku_desc
        if user_profile.industry_type == 'FMCG':
            batch_no, mrp = '', 0
            if data.stock.batch_detail:
                batch_no = data.stock.batch_detail.batch_no
                mrp = data.stock.batch_detail.mrp
            data_dict['Batch No'] = batch_no
            data_dict['MRP'] = mrp
        data_dict['Source Location'] = data.stock.location.location
        data_dict['Suggested Quantity'] = data.quantity
        data_dict['Destination Location'] = data.location.location
        data_dict['Quantity'] = data.quantity
        data_dict['data_id'] = data.id
        temp_data['aaData'].append(data_dict)


@csrf_exempt
@login_required
@get_admin_user
def auto_sellable_confirm(request, user=''):
    try:
        request_data = request.POST.dict()
        log.info('Request Params for Confirm Sellable Suggestions for user %s is %s' %
                 (user.username, str(request_data)))
        data_dict = {}
        for key, value in request_data.iteritems():
            group_key = key.split(']')[0].replace('data[', '')
            data_dict.setdefault(group_key, {})
            data_dict[group_key][key.split('[')[-1].strip(']')] = value
        data_list = data_dict.values()
        for index, data in enumerate(data_list):
            suggestions = SellableSuggestions.objects.filter(id=data['data_id'], status=1)
            if not suggestions.exists():
                continue
            suggestion = suggestions[0]
            destination = LocationMaster.objects.filter(zone__user=user.id, location=data['Destination Location'])
            if not destination:
                return HttpResponse(json.dumps({'message': 'Invalid Destination Location', 'status': 0}))
            data_list[index]['dest_location'] = destination[0].location
            try:
                quantity = float(data['Quantity'])
            except:
                return HttpResponse(json.dumps({'message': 'Invalid Quantity', 'status': 0}))
            seller_master = SellerMaster.objects.filter(user=user.id, seller_id=data['Seller ID'])
            if not seller_master:
                return HttpResponse(json.dumps({'message': 'Invalid Seller ID', 'status': 0}))
            if quantity > float(suggestion.quantity):
                return HttpResponse(json.dumps({'message': 'Quantity exceeding the Suggested quantity', 'status': 0}))
            if quantity > float(suggestion.stock.quantity):
                return HttpResponse(json.dumps({'message': 'Quantity exceeding the stock quantity', 'status': 0}))
            data_list[index]['seller_id'] = seller_master[0].id
            data_list[index]['quantity'] = quantity
            data_list[index]['suggestion_obj'] = suggestion
        cycle_count = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
        if not cycle_count:
            cycle_id = 1
        else:
            cycle_id = cycle_count[0].cycle + 1
        for data in data_list:
            suggestion = data['suggestion_obj']
            seller_id, batch_no, mrp = '', '', 0
            if data.get('Seller ID', ''):
                seller_id = data['Seller ID']
            if data.get('Batch No', ''):
                batch_no = ''
            if data.get('MRP', 0):
                mrp = float(data['MRP'])
            status = move_stock_location(cycle_id, suggestion.stock.sku.wms_code, suggestion.stock.location.location,
                                         data['dest_location'], data['quantity'], user, seller_id,
                                         batch_no=batch_no, mrp=mrp)
            if 'success' in status.lower():
                update_filled_capacity([suggestion.stock.location.location, data['dest_location']], user.id)
                suggestion.quantity = float(suggestion.quantity) - data['quantity']
                if suggestion.quantity <= 0:
                    suggestion.status = 0
                suggestion.save()
        return HttpResponse(json.dumps({'message': 'Success', 'status': 1}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        result_data = []
        log.info('Confirm Sellable Suggestions failed for user %s' % (str(user.username)))
        return HttpResponse(json.dumps({'message': 'Failed', 'status': 0}))


@csrf_exempt
@login_required
@get_admin_user
def update_sellable_suggestions(request, user=''):
    update_auto_sellable_data(user)
    return HttpResponse("Success")


def get_all_sellable_zones(user):
    sellable_zones = ZoneMaster.objects.filter(user=user.id, segregation='sellable').exclude(zone__in=['DAMAGED_ZONE', 'QC_ZONE']).values_list('zone', flat=True)
    if sellable_zones:
        sellable_zones = get_all_zones(user, zones=sellable_zones)
    return sellable_zones


@csrf_exempt
@login_required
@get_admin_user
def get_combo_sku_codes(request, user=''):
    sku_code = request.POST.get('sku_code', '')
    all_data = []
    seller_id = request.POST.get('seller_id', '').split(':')[0]
    seller_master = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
    if not seller_master:
        return HttpResponse(json.dumps({"status": False, "message":"Invalid Seller ID"}))
    seller_master_id = seller_master[0].id
    parent_mrp = 0
    sellable_zones = get_all_sellable_zones(user)
    get_sku_id = SKUMaster.objects.filter(user=request.user.id, sku_code=sku_code)
    if get_sku_id.exists():
        parent_sku_id = get_sku_id[0].id
        parent_mrp = get_sku_id[0].mrp
        stock_detail = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0, sellerstock__seller_id=seller_master_id,
                                                            sku_id=parent_sku_id, location__zone__zone__in=sellable_zones,
                                                            batch_detail__isnull=False).only('batch_detail__mrp')
    combo_skus = SKURelation.objects.filter(parent_sku__user=user.id, parent_sku__sku_code=sku_code)
    if not combo_skus:
        return HttpResponse(json.dumps({"status": False, "message":"No Data Found"}))
    for combo in combo_skus:
        cond = (combo.member_sku.sku_code)
        child_quantity = combo.quantity
        stock_detail = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0, sellerstock__seller_id=seller_master_id,
                                                            sku_id=combo.member_sku_id, location__zone__zone__in=sellable_zones,
                                                            batch_detail__isnull=False).only('batch_detail__mrp')
        child_mrp = 0
        if stock_detail.exists():
            child_mrp = stock_detail[0].batch_detail.mrp
        all_data.append({'child_sku_qty': child_quantity, 'child_sku_code': cond, 'child_sku_batch':'', 'child_sku_desc': combo.member_sku.sku_desc,
                        'child_sku_location': '', 'child_sku_mrp': child_mrp, 'child_qty': child_quantity,
                         'child_sku_weight': get_sku_weight(combo.member_sku)})
    parent_data = {'combo_sku_code': combo_skus[0].parent_sku.sku_code, 'combo_sku_desc': combo_skus[0].parent_sku.sku_desc,
                   'quantity':1, 'mrp': parent_mrp, 'weight': get_sku_weight(combo_skus[0].parent_sku)}
    return HttpResponse(json.dumps({"status": True, 'parent': parent_data, 'childs': all_data}), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def confirm_combo_allocation(request, user=''):
    data_dict = dict(request.POST.iterlists())
    try:
        log.info('Request Params for Confirm Combo Allocation for user %s is %s' %
                 (user.username, str(data_dict)))
        seller_id = request.POST.get('seller_id', '').split(':')[0]
        if seller_id:
            seller = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
            if not seller:
                return HttpResponse(json.dumps({'status':False, 'message':'Invalid Seller Id'}))
            else:
                seller_id = seller[0].id
        final_data = OrderedDict()
        for ind in range(0, len(data_dict['combo_sku_code'])):
            combo_batch_no = data_dict['batch'][ind]
            combo_mrp = data_dict['mrp'][ind]
            combo_weight = data_dict['weight'][ind]
            combo_qty = data_dict['quantity'][ind]
            child_batch_no = data_dict['child_batch'][ind]
            child_mrp = data_dict['child_mrp'][ind]
            child_weight = data_dict['child_weight'][ind]
            child_qty = data_dict['child_quantity'][ind]
            if not combo_qty:
                return HttpResponse(json.dumps({'status':False, 'message':'Child Quantity should be number'}))
            combo_qty = float(combo_qty)
            if not child_qty:
                return HttpResponse(json.dumps({'status':False, 'message':'Child Quantity should be number'}))
            child_qty = float(child_qty)
            try:
                child_mrp = float(child_mrp)
            except:
                if user.username in MILKBASKET_USERS:
                    return HttpResponse(json.dumps({'status':False, 'message':'Child MRP should be number'}))
                else:
                    child_mrp = 0
            try:
                combo_mrp = float(combo_mrp)
            except:
                if user.username in MILKBASKET_USERS:
                    return HttpResponse(json.dumps({'status':False, 'message':'Combo MRP should be number'}))
                else:
                    combo_mrp = 0
            if user.username in MILKBASKET_USERS and not child_weight:
                return HttpResponse(json.dumps({'status': False, 'message': 'Child Weight is Mandatory'}))
            if user.username in MILKBASKET_USERS and not combo_weight:
                return HttpResponse(json.dumps({'status': False, 'message': 'Combo Weight is Mandatory'}))
            combo_sku = SKUMaster.objects.filter(user=user.id, sku_code=data_dict['combo_sku_code'][ind])
            if not combo_sku:
                return HttpResponse(json.dumps({'status':False, 'message':'Combo SKU Code Not Found'}))
            child_sku = SKUMaster.objects.filter(user=user.id, sku_code=data_dict['child_sku_code'][ind])
            if not child_sku:
                return HttpResponse(json.dumps({'status':False, 'message':'Child SKU Code Not Found'}))
            combo_loc = LocationMaster.objects.filter(zone__user=user.id, location=data_dict['location'][ind])
            if not combo_loc:
                return HttpResponse(json.dumps({'status':False, 'message':'Combo Location Not Found'}))
            child_loc = LocationMaster.objects.filter(zone__user=user.id, location=data_dict['child_location'][ind])
            if not child_loc:
                return HttpResponse(json.dumps({'status':False, 'message':'Child Location Not Found'}))
            stock_dict = {"sku_id": child_sku[0].id, "location_id": child_loc[0].id,
                          "sku__user": user.id, "quantity__gt": 0}
            if seller_id:
                stock_dict['sellerstock__seller_id'] = seller_id
            if child_batch_no:
                stock_dict['batch_detail__batch_no'] = child_batch_no
            if child_mrp:
                stock_dict['batch_detail__mrp'] = child_mrp
            if child_weight:
                stock_dict['batch_detail__weight'] = child_weight
            child_stocks = StockDetail.objects.filter(**stock_dict)
            child_stock_count = child_stocks.aggregate(Sum('quantity'))['quantity__sum']
            if not child_stock_count:
                return HttpResponse(json.dumps({'status':False, 'message':'Child SKU Code Don\'t Have Stock'}))
            elif child_stock_count < child_qty:
                return HttpResponse(json.dumps({'status':False, 'message':'Child SKU Code Have Stock, ' + str(child_stock_count) }))
            combo_filter = {'sku_id': combo_sku[0].id, 'location_id': combo_loc[0].id,
                           'sku__user': user.id}
            mrp_dict = {}
            mrp_dict['batch_no'] = combo_batch_no
            combo_filter['batch_detail__batch_no'] = combo_batch_no
            if combo_mrp:
                mrp_dict['mrp'] = combo_mrp
                combo_filter['batch_detail__mrp'] = combo_mrp
            if combo_weight:
                mrp_dict['weight'] = combo_weight
                combo_filter['batch_detail__weight'] = combo_weight
            add_ean_weight_to_batch_detail(combo_sku[0], mrp_dict)
            if seller_id:
                combo_filter['sellerstock__seller_id'] = seller_id
            combo_stocks = StockDetail.objects.filter(**combo_filter)
            group_key = '%s<<>>%s<<>>%s<<>>%s<<>>%s' % (str(combo_sku[0].sku_code), str(combo_loc[0].location),
                                                  str(combo_batch_no), str(combo_mrp), str(combo_weight))
            final_data.setdefault(group_key, {'combo_sku': combo_sku[0], 'combo_loc': combo_loc[0],
                                              'combo_batch_no': combo_batch_no, 'combo_mrp': combo_mrp,
                                              'combo_qty': combo_qty, 'combo_mrp_dict': mrp_dict,
                                              'combo_stocks': combo_stocks, 'combo_weight': combo_weight,
                                              'childs': []})
            final_data[group_key]['childs'].append({'child_sku': child_sku[0], 'child_loc': child_loc[0],
                                                    'child_batch_no': child_batch_no, 'child_mrp': child_mrp,
                                                    'child_qty': child_qty, 'child_stocks': child_stocks,
                                                    'child_mrp': child_mrp})
        final_data = final_data.values()
        source_updated=False

        for row_data in final_data:
            transact_number = get_max_combo_allocation_id(user)
            dest_updated = False
            for data in row_data['childs']:
                desc_batch_obj = update_stocks_data(data['child_stocks'], float(data['child_qty']), row_data['combo_stocks'],
                                                    float(row_data['combo_qty']), user, [row_data['combo_loc']],
                                                    row_data['combo_sku'].id,
                                                    src_seller_id=seller_id, dest_seller_id=seller_id,
                                                    source_updated=source_updated,
                                                    mrp_dict=row_data['combo_mrp_dict'], dest_updated=dest_updated)
                sub_data = {'source_sku_code_id': data['child_sku'].id, 'source_location': data['child_loc'].location, 'source_quantity': data['child_qty'],
                            'destination_sku_code_id': row_data['combo_sku'].id, 'destination_location': row_data['combo_loc'].location,
                            'destination_quantity': row_data['combo_qty'], 'summary_type': 'combo_allocation'}
                if data['child_stocks'] and data['child_stocks'][0].batch_detail:
                    sub_data['source_batch_id'] = data['child_stocks'][0].batch_detail_id
                if desc_batch_obj:
                    sub_data['dest_batch_id'] = desc_batch_obj.id
                if seller_id:
                    sub_data['seller_id'] = seller_id
                sub_data['transact_number'] = transact_number
                SubstitutionSummary.objects.create(**sub_data)
                dest_updated = True
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Combo allocate stock failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(data_dict), str(e)))

    return HttpResponse(json.dumps({'status':True, 'message' : 'Success'}))


@csrf_exempt
def get_skuclassification(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    lis = ['sku__sku_code', 'sku__sku_code', 'sku__sku_code', 'sku__sku_desc','sku__sku_category',
           'sku__sku_code', 'sku__sku_code', 'sku__sku_code', 'sku__sku_code', 'sku__sku_code', 'sku__sku_code',
           'sku__sku_code', 'sku__relation_type', 'avg_sales_day', 'avg_sales_day_value',
           'cumulative_contribution', 'classification',
           'source_stock__batch_detail__mrp', 'source_stock__batch_detail__weight', 'replenushment_qty','sku_avail_qty',
           'avail_quantity', 'min_stock_qty', 'max_stock_qty', 'source_stock__location__location',
           'dest_location__location',
           'reserved__sum', 'remarks']
    grouping_data = OrderedDict()
    search_params = get_filtered_params(filters, lis)
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        master_data = SkuClassification.objects.filter(
                Q(sku__wms_code__icontains=search_term) | Q(sku__sku_desc__icontains=search_term) |
                Q(sku__sku_category__icontains=search_term) | Q(classification__icontains=search_term) |
                Q(source_stock__batch_detail__mrp__icontains=search_term) |
                Q(source_stock__batch_detail__weight__icontains=search_term),
                sku__user=user.id, status=1)
    else:
        master_data = SkuClassification.objects.filter(sku__user=user.id, status=1, **search_params)
    master_data = master_data.select_related('sku', 'source_stock', 'source_stock__batch_detail').values('sku__sku_code', 'sku__sku_desc', 'sku__sku_category',
                                     'source_stock__batch_detail__mrp', 'source_stock__batch_detail__weight',
                                     'avg_sales_day', 'avg_sales_day_value', 'cumulative_contribution', 'classification',
                                     'replenushment_qty', 'sku_avail_qty', 'avail_quantity',
                                     'min_stock_qty', 'max_stock_qty', 'status', 'remarks',
                       'source_stock__location__location', 'dest_location__location',
                                     'sku__relation_type', 'creation_date').distinct().\
                annotate(Sum('reserved')).order_by(order_data)
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if stop_index:
        master_data = master_data[start_index: stop_index]
    else:
        sku_attrs = SKUAttributes.objects.filter(sku__user=user.id)
        sku_sheet_dict = dict(sku_attrs.filter(attribute_name='Sheet').values_list('sku__sku_code', 'attribute_value'))
        sku_vendor_dict = dict(sku_attrs.filter(attribute_name='Vendor').values_list('sku__sku_code', 'attribute_value'))
        sku_searchable_dict = dict(sku_attrs.filter(attribute_name='Searchable').values_list('sku__sku_code', 'attribute_value'))
        sku_reset_dict = dict(
            sku_attrs.filter(attribute_name='Reset Stock').values_list('sku__sku_code', 'attribute_value'))
        sku_aisle_dict = dict(
            sku_attrs.filter(attribute_name='Aisle').values_list('sku__sku_code', 'attribute_value'))
        sku_rack_dict = dict(
            sku_attrs.filter(attribute_name='Rack').values_list('sku__sku_code', 'attribute_value'))
        sku_shelf_dict = dict(
            sku_attrs.filter(attribute_name='Shelf').values_list('sku__sku_code', 'attribute_value'))
    for data in master_data:
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data['sku__sku_code'], data['reserved__sum'])
        mrp = 0
        weight = ''
        source_location = ''
        dest_location = ''
        if data['source_stock__location__location']:
            source_location = data['source_stock__location__location']
        if data['source_stock__batch_detail__mrp']:
            mrp = data['source_stock__batch_detail__mrp']
        if data['source_stock__batch_detail__weight']:
            weight = data['source_stock__batch_detail__weight']
        if data['dest_location__location']:
            dest_location = data['dest_location__location']
        combo_flag = 'No'
        if data['sku__relation_type'] == 'combo':
            combo_flag = 'Yes'
        if stop_index:
            sheet, vendor, reset_stock, searchable, aisle, rack, shelf = '', '', '', '', '', '', ''
            sku_attr_obj = SKUAttributes.objects.filter(sku__user=user.id, sku__sku_code=data['sku__sku_code'], attribute_name='Sheet').only('attribute_value')
            if sku_attr_obj.exists():
                sheet = sku_attr_obj[0].attribute_value
            sku_attr_obj = SKUAttributes.objects.filter(sku__user=user.id, sku__sku_code=data['sku__sku_code'], attribute_name='Vendor').only('attribute_value')
            if sku_attr_obj.exists():
                vendor = sku_attr_obj[0].attribute_value
            sku_attr_obj = SKUAttributes.objects.filter(sku__user=user.id, sku__sku_code=data['sku__sku_code'],
                                                    attribute_name='Reset Stock').only('attribute_value')
            if sku_attr_obj.exists():
                reset_stock = sku_attr_obj[0].attribute_value
            sku_attr_obj = SKUAttributes.objects.filter(sku__user=user.id, sku__sku_code=data['sku__sku_code'],
                                                    attribute_name='Searchable').only('attribute_value')
            if sku_attr_obj.exists():
                searchable = sku_attr_obj[0].attribute_value
            sku_attr_obj = SKUAttributes.objects.filter(sku__user=user.id, sku__sku_code=data['sku__sku_code'],
                                                    attribute_name='Aisle').only('attribute_value')
            if sku_attr_obj.exists():
                aisle = sku_attr_obj[0].attribute_value
            sku_attr_obj = SKUAttributes.objects.filter(sku__user=user.id, sku__sku_code=data['sku__sku_code'],
                                                    attribute_name='Rack').only('attribute_value')
            if sku_attr_obj.exists():
                rack = sku_attr_obj[0].attribute_value
            sku_attr_obj = SKUAttributes.objects.filter(sku__user=user.id, sku__sku_code=data['sku__sku_code'],
                                                    attribute_name='Shelf').only('attribute_value')
            if sku_attr_obj.exists():
                shelf = sku_attr_obj[0].attribute_value
        else:
            sheet = sku_sheet_dict.get(data['sku__sku_code'], '')
            vendor = sku_vendor_dict.get(data['sku__sku_code'], '')
            reset_stock = sku_reset_dict.get(data['sku__sku_code'], '')
            searchable = sku_searchable_dict.get(data['sku__sku_code'], '')
            aisle = sku_aisle_dict.get(data['sku__sku_code'], '')
            rack = sku_rack_dict.get(data['sku__sku_code'], '')
            shelf = sku_shelf_dict.get(data['sku__sku_code'], '')
        temp_data['aaData'].append(
            OrderedDict((('', checkbox), ('generation_time', get_local_date(user, data['creation_date'])),
                         ('sku_code', data['sku__sku_code']),('sku_name', data['sku__sku_desc']),
                         ('sku_category', data['sku__sku_category']),
                         ('sheet', sheet),
                         ('vendor', vendor),
                         ('reset_stock', reset_stock),
                         ('searchable', searchable),
                         ('aisle', aisle),
                         ('rack', rack),
                         ('shelf', shelf),
                         ('combo_flag', combo_flag),
                         ('avg_sales_day', data['avg_sales_day']),
                         ('avg_sales_day_value', data['avg_sales_day_value']),
                         ('cumulative_contribution', data['cumulative_contribution']),
                         ('classification', data['classification']), ('mrp', mrp),
                         ('weight', weight),
                         ('replenushment_qty', data['replenushment_qty']),
                         ('sku_avail_qty', data['sku_avail_qty']),
                         ('avail_qty', data['avail_quantity']),
                         ('min_stock_qty', int(data['min_stock_qty'])),
                         ('max_stock_qty', int(data['max_stock_qty'])),
                         ('source_location', source_location),
                         ('dest_location', dest_location),
                         ('suggested_qty', data['reserved__sum']),
                         ('status', data['status']),
                         ('remarks', data['remarks']),
                         ('data_id', data['sku__sku_code']),
                         ('DT_RowAttr', {'data_id': data['sku__sku_code']}))))



@csrf_exempt
@login_required
@get_admin_user
def cal_ba_to_sa(request, user=''):
    """ Confirm BA to SA Stock Update"""
    data_dict = dict(request.POST.iterlists())
    confirm_data_list = []
    for ind in range(0, len(data_dict['data_id'])):
        classification_objs = SkuClassification.objects.filter(sku__sku_code=data_dict['sku_code'][ind],
                                                              source_stock__batch_detail__mrp=data_dict['mrp'][ind],
                                                              source_stock__batch_detail__weight=data_dict['weight'][ind],
                                                              source_stock__location__location=data_dict['source_location'][ind],
                                                              classification=data_dict['classification'][ind],
                                                              sku__user=user.id, status=1)
        if not classification_objs:
            continue
        try:
            total_reserved = classification_objs.aggregate(Sum('reserved'))['reserved__sum']
            dest_location = data_dict['dest_location'][ind]
            remarks = data_dict['remarks'][ind]
            if remarks:
                continue
            dest_loc_obj = LocationMaster.objects.filter(zone__user=user.id, location=dest_location)
            if not dest_loc_obj.exists():
                return HttpResponse("Invalid Location for SKU Code %s" % str(data_dict['sku_code'][ind]))
            try:
                suggested_qty = float(data_dict['suggested_qty'][ind])
            except:
                suggested_qty = 0
            if not suggested_qty:
                continue
            if total_reserved < suggested_qty:
                return HttpResponse("Entered Quantity exceeding the suggested quantity for SKU Code %s" % str(
                    data_dict['sku_code'][ind]))
            for classification_obj in classification_objs:
                if not suggested_qty:
                    continue
                seller = classification_obj.seller
                if suggested_qty > classification_obj.reserved:
                    reserved_quantity = classification_obj.reserved
                    suggested_qty -= reserved_quantity
                else:
                    reserved_quantity = suggested_qty
                    suggested_qty = 0
                confirm_data_list.append({'classification_obj': classification_obj, 'dest_loc': dest_loc_obj[0],
                                          'reserved_quantity': reserved_quantity, 'seller': seller})
            data = CycleCount.objects.filter(sku__user=user.id).aggregate(Max('cycle'))['cycle__max']
            if not data:
                cycle_id = 1
            else:
                cycle_id = data + 1
            for final_data in confirm_data_list:
                classification_obj = final_data['classification_obj']
                wms_code = classification_obj.source_stock.sku.sku_code
                source_loc = classification_obj.source_stock.location.location
                dest_loc = final_data['dest_loc'].location
                quantity = final_data['reserved_quantity']
                seller_id = classification_obj.seller.seller_id
                batch_no = ''
                mrp = 0
                weight = ''
                if classification_obj.source_stock.batch_detail:
                    batch_no = classification_obj.source_stock.batch_detail.batch_no
                    mrp = classification_obj.source_stock.batch_detail.mrp
                    weight = classification_obj.source_stock.batch_detail.weight
                status = move_stock_location(cycle_id, wms_code, source_loc, dest_loc, quantity, user, seller_id,
                                             batch_no=batch_no, mrp=mrp,
                                             weight=weight)
                if 'success' in status.lower():
                    update_filled_capacity([source_loc, dest_loc], user.id)
                    classification_obj.reserved = classification_obj.reserved - quantity
                    if classification_obj.reserved <= 0:
                        classification_obj.status = 0
                    classification_obj.save()
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('BA to SA Confirmation failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(data_dict), str(e)))

    return HttpResponse('Confirmed Successfully')


def save_ba_to_sa_remarks(sku_classification_dict1, sku_classification_objs, remarks_sku_ids):
    if sku_classification_dict1['sku_id'] not in remarks_sku_ids:
        exist_obj = SkuClassification.objects.filter(sku_id=sku_classification_dict1['sku_id'],
                                                     classification=sku_classification_dict1['classification'],
                                                     status=1)
        if not exist_obj.exists():
            sku_classification_objs.append(SkuClassification(**sku_classification_dict1))
            remarks_sku_ids.append(sku_classification_dict1['sku_id'])


@csrf_exempt
@login_required
@get_admin_user
def ba_to_sa_calculate_now(request, user=''):
    master_data = SKUMaster.objects.filter(user = user.id, status=1).order_by('id').only('id', 'sku_code')
    sellable_zones = get_all_sellable_zones(user)
    total_avg_sale_per_day_value = 0
    sku_avg_sale_mapping = OrderedDict()
    sku_avail_qty = OrderedDict()
    sku_res_qty = OrderedDict()
    ba_sku_avail_qty = OrderedDict()
    ba_sku_res_qty = OrderedDict()
    zones = get_all_sellable_zones(user)
    locations = LocationMaster.objects.filter(zone__user=user.id, zone__zone__in=zones)
    if not locations:
        return HttpResponse("Sellable Locations not found")
    seller_master = SellerMaster.objects.filter(seller_id=1, user=user.id)
    if not seller_master.exists():
        return HttpResponse("Seller id 1 not found")
    try:
        seller_master = seller_master[0]
        all_stocks = StockDetail.objects.exclude(receipt_number=0).\
                                            filter(sku__user=user.id, sku__status=1, quantity__gt=0,
                                            location__zone__zone__in=sellable_zones,
                                                   sellerstock__seller__seller_id=1).\
                                            values('sku_id', 'sellerstock__quantity')
        for sku_stock in all_stocks:
            sku_avail_qty.setdefault(sku_stock['sku_id'], 0)
            sku_avail_qty[sku_stock['sku_id']] += sku_stock['sellerstock__quantity']
        all_reserved = PicklistLocation.objects.filter(stock__sku__user=user.id, stock__sku__status=1,
                                                       stock__location__zone__zone__in=sellable_zones,
                                                       stock__sellerstock__seller__seller_id=1 ,status=1).\
                                                only('stock__sku_id', 'reserved')
        for all_res in all_reserved:
            sku_res_qty.setdefault(all_res.stock.sku_id, 0)
            sku_res_qty[all_res.stock.sku_id] += all_res.reserved
        all_ba_stocks = StockDetail.objects.exclude(receipt_number=0).\
                                            filter(sku__user=user.id, sku__status=1, quantity__gt=0,
                                            location__zone__zone='Bulk Zone',
                                                   sellerstock__seller__seller_id=1,
                                            sellerstock__quantity__gt=0).\
                                            values('sku_id', 'id','sellerstock__quantity').order_by('receipt_number')
        for ba_stock in all_ba_stocks:
            ba_sku_avail_qty.setdefault(ba_stock['sku_id'], {'total_quantity': 0, 'stock': OrderedDict()})
            ba_sku_avail_qty[ba_stock['sku_id']]['total_quantity'] += ba_stock['sellerstock__quantity']
            ba_sku_avail_qty[ba_stock['sku_id']]['stock'][ba_stock['id']] = ba_stock['sellerstock__quantity']
        all_ba_reserved = PicklistLocation.objects.filter(stock__sku__user=user.id, stock__sku__status=1,
                                                       stock__location__zone__zone='Bulk Zone',
                                                       stock__sellerstock__seller__seller_id=1 ,status=1).\
                                                only('stock__sku_id', 'stock_id', 'reserved')
        for ba_reserved in all_ba_reserved:
            temp_ba_avail = ba_sku_avail_qty.get(ba_reserved.stock.sku_id, {})
            if ba_reserved.stock_id in temp_ba_avail['stock'].keys():
                ba_sku_avail_qty[ba_reserved.stock.sku_id]['stock'][ba_reserved.stock_id] -= ba_reserved.reserved
                ba_sku_avail_qty[ba_reserved.stock.sku_id]['total_quantity'] -= ba_reserved.reserved

        log.info("BA to SA calculating segregation for user %s started at %s" % (
        user.username, str(datetime.datetime.now())))
        for data in master_data:
            stock_qty = sku_avail_qty.get(data.id, 0)
            res_qty = sku_res_qty.get(data.id, 0)
            avail_qty = stock_qty - res_qty
            no_stock_days = list(StockStats.objects.filter(sku_id = data.id, closing_stock=0).\
                                    annotate(creation_date_only=Cast('creation_date', DateField())).values('creation_date_only').distinct().\
                                    order_by('-creation_date_only').values_list('creation_date_only', flat=True)[:7])
            order_detail_objs = OrderDetail.objects.filter(user = user.id, sku_id = data.id).\
                                   annotate(creation_date_only=Cast('creation_date', DateField())).\
                                   exclude(creation_date_only__in=no_stock_days).values('creation_date_only').distinct().\
                                   order_by('-creation_date_only').annotate(quantity_sum=Sum('quantity'),
                                    value_sum=Sum(F('quantity') * F('unit_price')))[:7]
            sku_sales_value = 0
            sku_sales_units = 0
            for order_detail_obj in order_detail_objs:
                quantity_sum = order_detail_obj['quantity_sum']
                value_sum = order_detail_obj['value_sum']
                sku_sales_value += value_sum
                sku_sales_units += quantity_sum
            avg_sale_per_day_value = sku_sales_value/7
            avg_sale_per_day_units = sku_sales_units/7
            total_avg_sale_per_day_value += avg_sale_per_day_value
            sku_avg_sale_mapping[data.id] = {'avg_sale_per_day_value': avg_sale_per_day_value, 'avail_qty': avail_qty,
                                             'avg_sale_per_day_units': avg_sale_per_day_units}

        log.info("BA to SA calculating segregation for user %s ended at %s" % (user.username, str(datetime.datetime.now())))
        sku_classification_objs = []
        # Removing of older objects, change the datetime update while changing the below 3 lines
        older_objs = SkuClassification.objects.filter(sku__user=user.id, status=1)
        if older_objs.exists():
            older_objs.delete()
        remarks_sku_ids = []
        replenish_dict = {}
        replenishment_objs = ReplenushmentMaster.objects.filter(user_id=user.id)
        for replenishment_obj in replenishment_objs:
            rep_group = (replenishment_obj.size, replenishment_obj.classification)
            replenish_dict[rep_group] = {'min_days': replenishment_obj.min_days, 'max_days': replenishment_obj.max_days}
        log.info(
            "BA to SA calculating saving for user %s started at %s" % (user.username, str(datetime.datetime.now())))
        for data in master_data:
            if not total_avg_sale_per_day_value:
                break
            sku_avg_sale_mapping_data = sku_avg_sale_mapping[data.id]
            sku_avg_sale_per_day_units = sku_avg_sale_mapping_data['avg_sale_per_day_units']
            sku_avg_sale_per_day_value = sku_avg_sale_mapping_data['avg_sale_per_day_value']
            sku_avail_qty = sku_avg_sale_mapping_data['avail_qty']
            avg_more_sales = filter(lambda person: person['avg_sale_per_day_value'] >= sku_avg_sale_per_day_value, sku_avg_sale_mapping.values())
            sum_avg_more_sales = 0
            for avg_more_sale in avg_more_sales:
                sum_avg_more_sales += avg_more_sale['avg_sale_per_day_value']
            cumulative_contribution = (sum_avg_more_sales/total_avg_sale_per_day_value) * 100
            if cumulative_contribution <= 40:
                classification = 'Fast'
            elif cumulative_contribution > 80:
                classification = 'Slow'
            else:
                classification = 'Medium'
            #replenishment_obj = ReplenushmentMaster.objects.filter(user_id=user.id, classification=classification,
            #                                                       size=data.sku_size)
            remarks = ''
            sku_rep_dict = replenish_dict.get((data.sku_size, classification), {})
            if not sku_rep_dict:
            #if not replenishment_obj.exists():
                remarks = 'Replenushment Master Not Found'
                min_days, max_days, min_stock, max_stock = 0, 0, 0, 0
            else:
                min_days = sku_rep_dict['min_days'] #replenishment_obj[0].min_days
                max_days = sku_rep_dict['max_days'] #replenishment_obj[0].max_days
                min_stock = min_days * sku_avg_sale_per_day_units
                max_stock = max_days * sku_avg_sale_per_day_units
            sku_classification_dict1 = {'sku_id': data.id, 'avg_sales_day': sku_avg_sale_per_day_units,
                                        'avg_sales_day_value': sku_avg_sale_per_day_value,
                                        'cumulative_contribution': cumulative_contribution, 'classification': classification, 'source_stock': None,
                                        'replenushment_qty': 0, 'reserved': 0, 'suggested_qty': 0, 'avail_quantity': 0, 'sku_avail_qty': sku_avail_qty,
                                        'dest_location': None, 'seller_id': seller_master.id, 'min_stock_qty': min_stock,
                                        'max_stock_qty': max_stock, 'status': 1}

            if sku_avail_qty > min_stock:
                remarks = 'Available Quantity is more than Min Stock'
                replenishment_qty = 0
                ba_stock_objs = []
                needed_qty = 0
            else:
                replenishment_qty = max_stock - sku_avail_qty
                #ba_stock_objs = StockDetail.objects.filter(location__zone__zone='Bulk Zone', sku_id=data.id,
                #                                      sellerstock__seller__seller_id=1, quantity__gt=0,
                #                                      sellerstock__quantity__gt=0)
                replenishment_qty = int(replenishment_qty)
                needed_qty = replenishment_qty
            sku_classification_dict1['replenushment_qty'] = replenishment_qty
            # if not needed_qty:
            #     remarks = 'No Relenushment Quantity'
            if remarks:
                sku_classification_dict1['remarks'] = remarks
                save_ba_to_sa_remarks(sku_classification_dict1, sku_classification_objs,
                                                                remarks_sku_ids)
                continue
            ba_stock_dict = ba_sku_avail_qty.get(data.id, {})
            # ba_stock_objs = StockDetail.objects.filter(location__zone__zone='Bulk Zone', sku_id=data.id,
            #                                             sellerstock__seller__seller_id=1, quantity__gt=0,
            #                                             sellerstock__quantity__gt=0)
            #if ba_stock_objs.exists():
            if ba_stock_dict:
                total_ba_stock = ba_stock_dict['total_quantity'] #ba_stock_objs.aggregate(Sum('sellerstock__quantity'))['sellerstock__quantity__sum']
                if total_ba_stock < replenishment_qty:
                    needed_qty = total_ba_stock
                else:
                    needed_qty = replenishment_qty
                for ba_stock_id, ba_stock_qty in ba_stock_dict['stock'].iteritems():
                    if ba_stock_qty <= 0:
                        continue
                    if not needed_qty:
                        continue
                    if ba_stock_qty < needed_qty:
                        suggested_qty = ba_stock_qty
                        needed_qty -=  ba_stock_qty
                    else:
                        suggested_qty = needed_qty
                        needed_qty = 0
                    sku_classification_dict = {'sku_id': data.id, 'avg_sales_day': sku_avg_sale_per_day_units,
                                                'avg_sales_day_value': sku_avg_sale_per_day_value,
                                               'cumulative_contribution': cumulative_contribution,
                                               'classification': classification, 'source_stock_id': ba_stock_id,
                                               'replenushment_qty': replenishment_qty, 'reserved': suggested_qty,
                                               'suggested_qty': suggested_qty,
                                               'avail_quantity': total_ba_stock,
                                               'sku_avail_qty': sku_avail_qty,
                                               'dest_location_id': locations[0].id, 'seller_id': seller_master.id,
                                               'min_stock_qty': min_stock, 'max_stock_qty': max_stock,
                                               'status': 1}
                    #exist_obj = SkuClassification.objects.filter(sku_id=data.id, classification=classification,
                    #                                             source_stock_id=ba_stock_id, status=1,
                    #                                             seller_id=seller_master.id)
                    #if not exist_obj:
                    sku_classification_objs.append(SkuClassification(**sku_classification_dict))
            else:
                remarks = 'BA Stock Not Found'
                sku_classification_dict1['remarks'] = remarks
                save_ba_to_sa_remarks(sku_classification_dict1, sku_classification_objs,
                                                                remarks_sku_ids)
        if sku_classification_objs:
            SkuClassification.objects.bulk_create(sku_classification_objs)
            # Updating the same datetime for all the created objects
            creation_date = datetime.datetime.now()
            SkuClassification.objects.filter(sku__user=user.id, status=1).update(creation_date=creation_date)

        log.info(
            "BA to SA calculation ended for user %s at %s" % (user.username, str(datetime.datetime.now())))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('BA to SA Suggestion failed for %s and error statement is %s' % (
        str(user.username), str(e)))
        return HttpResponse("Calculate BA to SA Failed")

    return HttpResponse('Calculated Successfully')
