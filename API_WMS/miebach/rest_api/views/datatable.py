from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import json
from django.db.models import Q, F
from collections import OrderedDict
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
from common import *
from masters import *
from inbound import *
from production import *
from outbound import *
from stock_locator import *
from miebach_utils import *
from retailone import *
from uploaded_pos import *
from targets import *
from myntra_generate_barcode import *

@fn_timer
def sku_excel_download(search_params, temp_data, headers, user, request):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_profile = UserProfile.objects.get(user=user.id)
    headers = copy.deepcopy(USER_SKU_EXCEL[user_profile.user_type])
    excel_mapping = copy.deepcopy(USER_SKU_EXCEL_MAPPING[user_profile.user_type])
    attributes = get_user_attributes(user, 'sku')
    attr_count = max(excel_mapping.values()) + 1
    sku_attr_list = []
    for attr in attributes:
        sku_attr_list.append(attr['attribute_name'])
        excel_mapping[attr['attribute_name']] = attr_count
        headers += [attr['attribute_name']]
        attr_count += 1
    status_dict = {'1': 'Active', '0': 'Inactive'}
    combo_flag_dict = {'combo': 'Yes', '': 'No'}
    # marketplace_list = Marketplaces.objects.filter(user=user.id).values_list('name').distinct()
    marketplace_list = MarketplaceMapping.objects.filter(sku__user=user.id).values_list('sku_type',
                                                                                        flat=True).distinct()
    search_terms = {}
    if search_params.get('search_0', ''):
        search_terms["wms_code__icontains"] = search_params.get('search_0', '')
    if search_params.get('search_1', ''):
        search_terms["ean_number__icontains"] = search_params.get('search_1', '')
    if search_params.get('search_2', ''):
        search_terms["sku_desc__icontains"] = search_params.get('search_2', '')
    if search_params.get('search_3', ''):
        search_terms["sku_type__icontains"] = search_params.get('search_3', '')
    if search_params.get('search_4', ''):
        search_terms["sku_category__icontains"] = search_params.get('search_4', '')
    if search_params.get('search_5', ''):
        search_terms["sku_class__icontains"] = search_params.get('search_5', '')
    if search_params.get('search_6', ''):
        search_terms["color__icontains"] = search_params.get('search_6', '')
    if search_params.get('search_7', ''):
        search_terms["zone__zone__icontains"] = search_params.get('search_7', '')
    if search_params.get('search_8', ''):
        search_terms["creation_date__iregex"] = search_params.get('search_8', '')
    if search_params.get('search_9', ''):
        search_terms["updation_date__iregex"] = search_params.get('search_9', '')
    if str(search_params.get('search_10', '')).lower():
        if (str(search_params.get('search_10', '')).lower() in "yes"):
            search_terms["relation_type__icontains"] = 'combo'
        elif (str(search_params.get('search_10', '')).lower() in "no"):
            search_terms["relation_type"] = ''
    if search_params.get('search_11', ''):
        if (str(search_params.get('search_11', '')).lower() in "active"):
            search_terms["status__icontains"] = 1
        elif (str(search_params.get('search_11', '')).lower() in "inactive"):
            search_terms["status__icontains"] = 0
        else:
            search_terms["status__icontains"] = "none"
    search_terms["user"] = user.id
    sku_master = sku_master.prefetch_related('skuattributes_set').filter(**search_terms)
    sku_ids = sku_master.values_list('id', flat=True)
    master_data = MarketplaceMapping.objects.exclude(sku_type='').select_related('sku').filter(sku_id__in=sku_ids,
                                                                         sku_type__in=marketplace_list)
    marketplaces = master_data.values_list('sku_type', flat=True).distinct()
    if master_data.count():
        for market in marketplaces:
            headers = headers + [market + ' SKU', market + ' Description']
    excel_headers = headers

    data_count = 0
    rev_load_units = dict(zip(LOAD_UNIT_HANDLE_DICT.values(), LOAD_UNIT_HANDLE_DICT.keys()))
    sku_fields = dict(
        SKUFields.objects.filter(sku__user=user.id, field_type='size_type').values_list('sku_id', 'field_value'))
    hot_releases = dict(
        SKUFields.objects.filter(sku__user=user.id, field_type='hot_release').values_list('sku_id', 'field_value'))
    file_type = 'xls'
    wb, ws = get_work_sheet('skus', excel_headers)
    file_name = "%s.%s" % (user.id, 'SKU Master')
    folder_path = 'static/excel_files/'
    folder_check(folder_path)
    if sku_master.count() > 65535:
        file_type = 'csv'
        wb = open(folder_path + file_name + '.' + file_type, 'w')
        ws = ''
        for head in excel_headers:
            ws = ws + str(head).replace(',', '  ') + ','
        ws = ws[:-1] + '\n'
        wb.write(ws)
        ws = ''
    path = folder_path + file_name + '.' + file_type

    for data in sku_master:
        data_count += 1
        zone = ''
        if data.zone:
            zone = data.zone.zone
        ws = write_excel(ws, data_count, excel_mapping['wms_code'], data.wms_code, file_type)
        ws = write_excel(ws, data_count, excel_mapping['sku_desc'], data.sku_desc, file_type)
        ws = write_excel(ws, data_count, excel_mapping['product_type'], data.product_type, file_type)
        ws = write_excel(ws, data_count, excel_mapping['sku_group'], data.sku_group, file_type)
        ws = write_excel(ws, data_count, excel_mapping['sku_type'], data.sku_type, file_type)
        ws = write_excel(ws, data_count, excel_mapping['sku_category'], data.sku_category, file_type)
        if excel_mapping.has_key('primary_category'):
            ws = write_excel(ws, data_count, excel_mapping['primary_category'], data.primary_category, file_type)
        ws = write_excel(ws, data_count, excel_mapping['sku_class'], data.sku_class, file_type)
        ws = write_excel(ws, data_count, excel_mapping['sku_brand'], data.sku_brand, file_type)
        ws = write_excel(ws, data_count, excel_mapping['style_name'], data.style_name, file_type)
        if excel_mapping.has_key('sku_size'):
            ws = write_excel(ws, data_count, excel_mapping['sku_size'], data.sku_size, file_type)
        if excel_mapping.has_key('size_type'):
            ws = write_excel(ws, data_count, excel_mapping['size_type'], sku_fields.get(data.id, ''), file_type)
        if excel_mapping.has_key('hot_release'):
            hot_release = 'Enable' if (hot_releases.get(data.id, '') not in ['', '0']) else 'Disable'
            ws = write_excel(ws, data_count, excel_mapping['hot_release'], hot_release, file_type)
        if excel_mapping.has_key('mix_sku'):
            ws = write_excel(ws, data_count, excel_mapping['mix_sku'], MIX_SKU_ATTRIBUTES.get(data.mix_sku, ''), file_type)
        ws = write_excel(ws, data_count, excel_mapping['zone_id'], zone, file_type)
        ws = write_excel(ws, data_count, excel_mapping['price'], data.price, file_type)
        ws = write_excel(ws, data_count, excel_mapping['mrp'], data.mrp, file_type)
        ws = write_excel(ws, data_count, excel_mapping['sequence'], data.sequence, file_type)
        ws = write_excel(ws, data_count, excel_mapping['image_url'], data.image_url, file_type)
        ws = write_excel(ws, data_count, excel_mapping['threshold_quantity'], data.threshold_quantity, file_type)
        ws = write_excel(ws, data_count, excel_mapping['measurement_type'], data.measurement_type, file_type)
        ws = write_excel(ws, data_count, excel_mapping['sale_through'], data.sale_through, file_type)
        ws = write_excel(ws, data_count, excel_mapping['color'], data.color, file_type)
        ean_list = []
        ean_objs = data.eannumbers_set.filter()
        if data.ean_number:
            ean_list.append(str(data.ean_number))
        if ean_objs.exists():
            ean_list = ean_list + list(ean_objs.annotate(str_eans=Cast('ean_number', CharField())).
                          values_list('str_eans', flat=True))
        ean_number = ','.join(ean_list)
        ws = write_excel(ws, data_count, excel_mapping['ean_number'], ean_number, file_type)
        if excel_mapping.has_key('load_unit_handle'):
            ws = write_excel(ws, data_count, excel_mapping['load_unit_handle'],
                     rev_load_units.get(data.load_unit_handle, '').capitalize(), file_type)
        ws = write_excel(ws, data_count, excel_mapping['hsn_code'], data.hsn_code, file_type)
        if excel_mapping.has_key('sub_category'):
            ws = write_excel(ws, data_count, excel_mapping['sub_category'], data.sub_category, file_type)
        if excel_mapping.has_key('cost_price'):
            ws = write_excel(ws, data_count, excel_mapping['cost_price'], data.cost_price, file_type)
        ws = write_excel(ws, data_count, excel_mapping['combo_flag'], combo_flag_dict[str(data.relation_type)], file_type)
        ws = write_excel(ws, data_count, excel_mapping['status'], status_dict[str(int(data.status))], file_type)
        '''for attr in attributes:
            attr_val = ''
            if data.skuattributes_set.filter(attribute_name=attr['attribute_name']):
                attr_val = data.skuattributes_set.filter(attribute_name=attr['attribute_name'])[0].attribute_value
            ws = write_excel(ws, data_count, excel_mapping[attr['attribute_name']], attr_val,
                             file_type)'''
        att_data = data.skuattributes_set.filter(attribute_name__in=sku_attr_list).values('attribute_name', 'attribute_value')
        for attr in att_data:
            if excel_mapping.get(attr['attribute_name'], ''):
                ws = write_excel(ws, data_count, excel_mapping[attr['attribute_name']], attr['attribute_value'],
                                 file_type)
        sku_types = data.marketplacemapping_set.exclude(sku_type='').filter().\
                                                values_list('sku_type', flat=True).distinct()
        for sku_type in sku_types:
            map_dat = data.marketplacemapping_set.filter(sku_type=sku_type).\
                                values('marketplace_code', 'description')
            market_codes = map(operator.itemgetter('marketplace_code'), map_dat)
            market_desc = map(operator.itemgetter('description'), map_dat)
            indices = [i for i, s in enumerate(headers) if sku_type in s]
            try:
                ws = write_excel(ws, data_count, indices[0], ', '.join(market_codes), file_type)
                ws = write_excel(ws, data_count, indices[1], ', '.join(market_desc), file_type)
            except:
                pass


        '''market_map = master_data.filter(sku_id=data.id).values('sku_id', 'sku_type').distinct()
        for dat in market_map:
            # map_dat = market_map.values('marketplace_code', 'description')
            map_dat = market_map.filter(sku_type=dat['sku_type']).values('marketplace_code', 'description')
            market_codes = map(operator.itemgetter('marketplace_code'), map_dat)
            market_desc = map(operator.itemgetter('description'), map_dat)
            indices = [i for i, s in enumerate(headers) if dat['sku_type'] in s]
            try:
                ws = write_excel(ws, data_count, indices[0], ', '.join(market_codes), file_type)
                ws = write_excel(ws, data_count, indices[1], ', '.join(market_desc), file_type)
            except:
                pass'''
        if file_type == 'csv':
            ws = ws[:-1] + '\n'
            wb.write(ws)
            ws = ''

    if file_type == 'xls':
        wb.save(path)
    else:
        wb.close()
    path_to_file = '../' + path
    return path_to_file


@fn_timer
def central_orders_excel_download(filter_params, user, request):
    data_dict = {'user': user.id, 'quantity__gt': 0}
    status_map = {'1': 'Accept', '0': 'Reject', '2': 'Pending'}
    search_term = request.POST.get("search[value]", '')
    all_orders = IntermediateOrders.objects.filter(**data_dict)
    if search_term:
        all_orders = all_orders.filter(
            Q(sku__sku_code__icontains=search_term) | Q(sku__sku_desc__icontains=search_term) |
            Q(quantity__icontains=search_term) | Q(shipment_date__regex=search_term) |
            Q(project_name__icontains=search_term) | Q(order_assigned_wh__username__icontains=search_term) |
            Q(interm_order_id__icontains=search_term) | Q(creation_date__regex=search_term) |
            Q(order__original_order_id__icontains=search_term)
        )

    file_type = 'xls'
    excel_headers = copy.deepcopy(CENTRAL_ORDER_EXCEL)
    status_index = len(CENTRAL_ORDER_EXCEL)
    excel_headers['status'] = status_index
    wb, ws = get_work_sheet('central_orders', excel_headers)
    file_name = "%s.%s" % (user.id, 'Central_Orders')
    folder_path = 'static/excel_files/'
    folder_check(folder_path)
    if all_orders.count() > 65535:
        file_type = 'csv'
        wb = open(folder_path + file_name + '.' + file_type, 'w')
        ws = ''
        for head in excel_headers:
            ws = ws + str(head).replace(',', '  ') + ','
        ws = ws[:-1] + '\n'
        wb.write(ws)

    path = folder_path + file_name + '.' + file_type
    data_count = 0

    ord_items = all_orders.values_list('interm_order_id', 'order__original_order_id', 'order_assigned_wh__username',
                                       'status', 'sku__sku_code', 'sku__sku_desc', 'quantity', 'shipment_date', 'id',
                                       'creation_date', 'project_name', 'remarks', 'unit_price', 'cgst_tax', 'sgst_tax',
                                       'igst_tax', 'user_id', 'customer_name')
    line_items_map = {}
    line_ord_fields_map = {}
    for item in ord_items:
        interm_order_id = item[0]
        original_order_id = item[1]
        line_items_map.setdefault(interm_order_id, []).append(item[1:])
        ord_fields_map = dict(OrderFields.objects.filter(user=user.id,
                                                         original_order_id=original_order_id).
                              only('name', 'value').values_list('name', 'value'))
        line_ord_fields_map.setdefault(interm_order_id, {}).update(ord_fields_map)

    for order_id, dat in line_items_map.items():
        data_count += 1
        loan_proposal_id, assigned_wh, status, sku_code, sku_desc, quantity, shipment_date, \
        id, creation_date, project_name, remarks, unit_price, cgst_tax, sgst_tax, igst_tax, user_id, \
        customer_name = dat[0]
        if status:
            status = status_map.get(status)
        else:
            status = 'Pending'
        batch_number = line_ord_fields_map.get(order_id, {}).get('batch_number')
        batch_date = line_ord_fields_map.get(order_id, {}).get('batch_date', '')
        branch_id = line_ord_fields_map.get(order_id, {}).get('branch_id', '')
        branch_name = line_ord_fields_map.get(order_id, {}).get('branch_name', '')
        loan_proposal_code = line_ord_fields_map.get(order_id, {}).get('loan_proposal_code')
        client_code = line_ord_fields_map.get(order_id, {}).get('client_code')
        client_id = line_ord_fields_map.get(order_id, {}).get('client_id')
        address1 = line_ord_fields_map.get(order_id, {}).get('address1')
        address2 = line_ord_fields_map.get(order_id, {}).get('address2')
        total_price = line_ord_fields_map.get(order_id, {}).get('total_price')
        village = line_ord_fields_map.get(order_id, {}).get('village')
        landmark = line_ord_fields_map.get(order_id, {}).get('landmark')
        district = line_ord_fields_map.get(order_id, {}).get('district')
        state = line_ord_fields_map.get(order_id, {}).get('state')
        pincode = line_ord_fields_map.get(order_id, {}).get('pincode')
        mobile_no = line_ord_fields_map.get(order_id, {}).get('mobile_no')
        alternative_mobile_no = line_ord_fields_map.get(order_id, {}).get('alternative_mobile_no')

        ws = write_excel(ws, data_count, excel_headers['original_order_id'], loan_proposal_id, file_type)
        ws = write_excel(ws, data_count, excel_headers['batch_number'], batch_number, file_type)
        ws = write_excel(ws, data_count, excel_headers['batch_date'], batch_date, file_type)
        ws = write_excel(ws, data_count, excel_headers['branch_id'], branch_id, file_type)
        ws = write_excel(ws, data_count, excel_headers['branch_name'], branch_name, file_type)
        ws = write_excel(ws, data_count, excel_headers['loan_proposal_id'], loan_proposal_id, file_type)
        ws = write_excel(ws, data_count, excel_headers['loan_proposal_code'], loan_proposal_code, file_type)
        ws = write_excel(ws, data_count, excel_headers['client_code'], client_code, file_type)
        ws = write_excel(ws, data_count, excel_headers['client_id'], client_id, file_type)
        ws = write_excel(ws, data_count, excel_headers['customer_name'], customer_name, file_type)
        ws = write_excel(ws, data_count, excel_headers['address1'], address1, file_type)
        ws = write_excel(ws, data_count, excel_headers['address2'], address2, file_type)
        ws = write_excel(ws, data_count, excel_headers['landmark'], landmark, file_type)
        ws = write_excel(ws, data_count, excel_headers['village'], village, file_type)
        ws = write_excel(ws, data_count, excel_headers['sku_code'], sku_code, file_type)
        ws = write_excel(ws, data_count, excel_headers['model'], sku_desc, file_type)
        ws = write_excel(ws, data_count, excel_headers['unit_price'], unit_price, file_type)
        ws = write_excel(ws, data_count, excel_headers['cgst'], cgst_tax, file_type)
        ws = write_excel(ws, data_count, excel_headers['sgst'], sgst_tax, file_type)
        ws = write_excel(ws, data_count, excel_headers['igst'], igst_tax, file_type)
        ws = write_excel(ws, data_count, excel_headers['total_price'], total_price, file_type)
        ws = write_excel(ws, data_count, excel_headers['location'], assigned_wh, file_type)
        ws = write_excel(ws, data_count, excel_headers['district'], district, file_type)
        ws = write_excel(ws, data_count, excel_headers['state'], state, file_type)
        ws = write_excel(ws, data_count, excel_headers['pincode'], pincode, file_type)
        ws = write_excel(ws, data_count, excel_headers['mobile_no'], mobile_no, file_type)
        ws = write_excel(ws, data_count, excel_headers['alternative_mobile_no'], alternative_mobile_no, file_type)
        ws = write_excel(ws, data_count, status_index, status, file_type)

    if file_type == 'xls':
        wb.save(path)
    else:
        wb.close()
    path_to_file = '../' + path
    return path_to_file


@fn_timer
def easyops_stock_excel_download(search_params, temp_data, headers, user, request):
    headers = EASYOPS_STOCK_HEADERS.keys()
    search_term = request.POST.get("search[value]", '')
    search_terms = {}
    if search_params.get('search_0', ''):
        search_terms["sku__wms_code__icontains"] = search_params.get('search_0', '')
    if search_params.get('search_1', ''):
        search_terms["sku__sku_desc__icontains"] = search_params.get('search_1', '')
    if search_params.get('search_2', ''):
        search_terms["sku__sku_category__icontains"] = search_params.get('search_2', '')
    if search_params.get('search_3', ''):
        search_terms["total__icontains"] = search_params.get('search_3', '')
    master_data = StockDetail.objects.exclude(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'], receipt_number=0). \
        values_list('sku__wms_code', 'sku__sku_desc').distinct(). \
        annotate(total=Sum('quantity')).filter(sku__user=user.id, quantity__gt=0, **search_terms). \
        order_by('sku__wms_code')
    if search_term:
        master_data = StockDetail.objects.exclude(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'],
                                                  receipt_number=0). \
            values_list('sku__wms_code', 'sku__sku_desc').distinct(). \
            annotate(total=Sum('quantity')).filter(Q(sku__wms_code__icontains=search_term) |
                                                   Q(sku__sku_desc__icontains=search_term) | Q(
            sku__sku_category__icontains=search_term) |
                                                   Q(total__icontains=search_term), sku__user=user.id, quantity__gt=0,
                                                   **search_terms). \
            order_by('sku__wms_code')
    excel_headers = headers
    wb, ws = get_work_sheet('inventory', excel_headers)
    data_count = 0
    for data in master_data:
        data_count += 1
        ws.write(data_count, 0, data[1])
        ws.write(data_count, 1, data[0])
        ws.write(data_count, 2, data[0])
        ws.write(data_count, 3, data[2])

    file_name = "%s.%s" % (user.id, 'Stock Custom Format-1')
    path = 'static/excel_files/' + file_name + '.xls'
    wb.save(path)
    path_to_file = '../' + path
    return path_to_file


@csrf_exempt
@login_required
@get_admin_user
def results_data(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    excel = request.POST.get('excel')
    temp_data = copy.deepcopy(AJAX_DATA)
    if excel == 'true':
        special_keys = search_params
        search_params = {'start': 0, 'draw': 1, 'length': 0, 'order_index': 0, 'order_term': u'asc',
                         'search_term': request.POST.get('search[value]', '')}
        for key, value in special_keys.iteritems():
            search_params[key] = value
        if request.POST.get('datatable', '') == 'SKUMaster':
            excel_data = sku_excel_download(filter_params, temp_data, headers, user, request)
            return HttpResponse(str(excel_data))
        if request.POST.get('datatable', '') == 'StockSummaryAlt':
            excel_data = get_stock_summary_size_excel(filter_params, temp_data, headers, user, request)
            return HttpResponse(str(excel_data))
        if request.POST.get('datatable', '') == 'StockSummaryEasyops':
            excel_data = easyops_stock_excel_download(filter_params, temp_data, headers, user, request)
            return HttpResponse(str(excel_data))
        if request.POST.get('datatable', '') == 'StockSummarySerials':
            excel_data = get_stock_summary_serials_excel(filter_params, temp_data, headers, user, request)
            return HttpResponse(str(excel_data))
        if request.POST.get('datatable', '') == 'CentralOrders' and request.user.username.lower() == '72networks':
            excel_data = central_orders_excel_download(filter_params, user, request)
            return HttpResponse(str(excel_data))
    temp_data['draw'] = search_params.get('draw')
    start_index = search_params.get('start')
    stop_index = start_index + search_params.get('length')
    if not stop_index:
        stop_index = None
    params = [start_index, stop_index, temp_data, search_params.get('search_term')]
    request_data = request.POST
    if not request_data:
        request_data = request.GET
    if request_data.get('datatable') in data_datatable.keys():
        fun = data_datatable[request_data.get('datatable')]
        params.extend([search_params.get('order_term'), search_params.get('order_index'), request, user])
        if filter_params:
            params.append(filter_params)
        if 'special_key' in search_params.keys():
            params.append(search_params.get('special_key'))
        eval(fun)(*params)
    else:
        temp_data = {"recordsTotal": 0, "recordsFiltered": 0, "draw": 2, "aaData": []}
    if excel == 'true':
        params = [temp_data, search_params.get('search_term'), search_params.get('order_term'), 
            search_params.get('order_index'), request, user, filter_params]
        if request.POST.get('datatable', '') == 'SupplierMaster':
            temp_data = {"recordsTotal": 0, "recordsFiltered": 0, "draw": 2, "aaData": []}
            excel_data = get_supplier_master_excel(*params)
            return HttpResponse(str(excel_data))
        headers = {}
        for key, value in request_data.iteritems():
            if not ('search' in key or key in ['datatable', 'excel']):
                headers[key] = value
        if request.POST.get('datatable', '') == 'Available+ASN' and request.POST.get('excel', '') == 'true':
            whs = map(lambda x: x.replace('-Total', ''), [i for i in headers.keys() if '-Total' in i])
            for wh in whs:
                headers[wh+'-NK'] = wh+'-NK'
        #excel_data = print_excel(request, temp_data, headers, excel_name=request_data.get('datatable'))
        file_type = 'xls'
        if len(temp_data['aaData']) > 65535:
            file_type = 'csv'
        excel_data = print_excel(request, temp_data, headers, excel_name=request_data.get('datatable'),
                                 file_type=file_type)
        return excel_data
    return HttpResponse(json.dumps(temp_data), content_type='application/json')
