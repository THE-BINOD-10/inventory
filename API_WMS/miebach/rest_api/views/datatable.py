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

@fn_timer
def sku_excel_download(search_params, temp_data, headers, user, request):
    sku_master, sku_master_ids = get_sku_master(user,request.user)
    user_profile = UserProfile.objects.get(user=user.id)
    headers = USER_SKU_EXCEL[user_profile.user_type]
    excel_mapping = USER_SKU_EXCEL_MAPPING[user_profile.user_type]
    status_dict = {'1': 'Active', '0': 'Inactive'}
    #marketplace_list = Marketplaces.objects.filter(user=user.id).values_list('name').distinct()
    marketplace_list = MarketplaceMapping.objects.filter(sku__user=user.id).values_list('sku_type', flat=True).distinct()
    search_terms = {}
    if search_params.get('search_0',''):
        search_terms["wms_code__icontains"] = search_params.get('search_0','')
    if search_params.get('search_1',''):
        search_terms["sku_desc__icontains"] = search_params.get('search_1','')
    if search_params.get('search_2',''):
        search_terms["sku_type__icontains"] = search_params.get('search_2','')
    if search_params.get('search_3',''):
        search_terms["sku_category__icontains"] = search_params.get('search_3','')
    if search_params.get('search_4',''):
        search_terms["sku_class__icontains"] = search_params.get('search_4','')
    if search_params.get('search_5',''):
        search_terms["color__icontains"] = search_params.get('search_5','')
    if search_params.get('search_6',''):
        search_terms["zone__zone__icontains"] = search_params.get('search_6','')
    if search_params.get('search_7',''):
        if (str(search_params.get('search_7','')).lower() in "active"):
            search_terms["status__icontains"] = 1
        elif (str(search_params.get('search_7','')).lower() in "inactive"):
            search_terms["status__icontains"] = 0
        else:
            search_terms["status__icontains"] = "none"
    search_terms["user"] =  user.id
    sku_master = sku_master.filter(**search_terms)
    sku_ids = sku_master.values_list('id', flat=True)
    master_data = MarketplaceMapping.objects.exclude(sku_type='').filter(sku_id__in=sku_ids, sku_type__in=marketplace_list)
    marketplaces = master_data.values_list('sku_type', flat=True).distinct()
    if master_data.count():
        for market in marketplaces:
            headers = headers + [market +' SKU', market + ' Description']
    excel_headers = headers
    wb, ws = get_work_sheet('skus', excel_headers)
    data_count = 0
    rev_load_units = dict(zip(LOAD_UNIT_HANDLE_DICT.values(), LOAD_UNIT_HANDLE_DICT.keys()))
    sku_fields = dict(SKUFields.objects.filter(sku__user=user.id, field_type='size_type').values_list('sku_id', 'field_value'))
    for data in sku_master:
        data_count += 1
        zone = ''
        if data.zone:
            zone = data.zone.zone
        ws.write(data_count, excel_mapping['wms_code'], data.wms_code)
        ws.write(data_count, excel_mapping['sku_desc'], data.sku_desc)
        ws.write(data_count, excel_mapping['sku_group'], data.sku_group)
        ws.write(data_count, excel_mapping['sku_type'], data.sku_type)
        ws.write(data_count, excel_mapping['sku_category'], data.sku_category)
        ws.write(data_count, excel_mapping['sku_class'], data.sku_class)
        ws.write(data_count, excel_mapping['sku_brand'], data.sku_brand)
        ws.write(data_count, excel_mapping['style_name'], data.style_name)
        if excel_mapping.has_key('sku_size'):
            ws.write(data_count, excel_mapping['sku_size'], data.sku_size)
        if excel_mapping.has_key('size_type'):
            ws.write(data_count, excel_mapping['size_type'], sku_fields.get(data.id, ''))
        if excel_mapping.has_key('mix_sku'):
            ws.write(data_count, excel_mapping['mix_sku'], MIX_SKU_ATTRIBUTES.get(data.mix_sku, ''))
        ws.write(data_count, excel_mapping['zone_id'], zone)
        ws.write(data_count, excel_mapping['price'], data.price)
        ws.write(data_count, excel_mapping['mrp'], data.mrp)
        ws.write(data_count, excel_mapping['sequence'], data.sequence)
        ws.write(data_count, excel_mapping['image_url'], data.image_url)
        ws.write(data_count, excel_mapping['threshold_quantity'], data.threshold_quantity)
        ws.write(data_count, excel_mapping['measurement_type'], data.measurement_type)
        ws.write(data_count, excel_mapping['sale_through'], data.sale_through)
        ws.write(data_count, excel_mapping['color'], data.color)
        ean_number = ''
        if data.ean_number:
            ean_number = data.ean_number
        ws.write(data_count, excel_mapping['ean_number'], ean_number)
        if excel_mapping.has_key('load_unit_handle'):
            ws.write(data_count, excel_mapping['load_unit_handle'], rev_load_units.get(data.load_unit_handle, '').capitalize())
        ws.write(data_count, excel_mapping['hsn_code'], data.hsn_code)
        ws.write(data_count, excel_mapping['status'], status_dict[str(int(data.status))])
        market_map = master_data.filter(sku_id=data.id).values('sku_id', 'sku_type').distinct()
        for dat in market_map:
            #map_dat = market_map.values('marketplace_code', 'description')
            map_dat = market_map.filter(sku_type = dat['sku_type']).values('marketplace_code', 'description')
            market_codes = map(operator.itemgetter('marketplace_code'), map_dat)
            market_desc = map(operator.itemgetter('description'), map_dat)
            indices = [i for i, s in enumerate(headers) if dat['sku_type'] in s]
            try:
                ws.write(data_count, indices[0], ', '.join(market_codes))
                ws.write(data_count, indices[1], ', '.join(market_desc))
            except:
                pass


    #return "daya pata karo"
    file_name = "%s.%s" % (user.id, 'SKU Master')
    folder_path = 'static/excel_files/'
    folder_check(folder_path)
    path = folder_path + file_name + '.xls'
    wb.save(path)
    path_to_file = '../' + path
    return path_to_file

@fn_timer
def easyops_stock_excel_download(search_params, temp_data, headers, user, request):
    headers = EASYOPS_STOCK_HEADERS.keys()
    search_term = request.POST.get("search[value]", '')
    search_terms = {}
    if search_params.get('search_0',''):
        search_terms["sku__wms_code__icontains"] = search_params.get('search_0','')
    if search_params.get('search_1',''):
        search_terms["sku__sku_desc__icontains"] = search_params.get('search_1','')
    if search_params.get('search_2',''):
        search_terms["sku__sku_category__icontains"] = search_params.get('search_2','')
    if search_params.get('search_3',''):
        search_terms["total__icontains"] = search_params.get('search_3','')
    master_data = StockDetail.objects.exclude(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'], receipt_number=0).\
                                      values_list('sku__wms_code', 'sku__sku_desc').distinct().\
                                          annotate(total=Sum('quantity')).filter(sku__user = user.id, quantity__gt=0, **search_terms).\
                                          order_by('sku__wms_code')
    if search_term:
        master_data = StockDetail.objects.exclude(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'], receipt_number=0).\
                                          values_list('sku__wms_code', 'sku__sku_desc').distinct().\
                                          annotate(total=Sum('quantity')).filter(Q(sku__wms_code__icontains=search_term) |
                                          Q(sku__sku_desc__icontains=search_term) | Q(sku__sku_category__icontains=search_term) |
                                          Q(total__icontains=search_term), sku__user = user.id, quantity__gt=0, **search_terms).\
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
    temp_data = copy.deepcopy( AJAX_DATA )
    if excel == 'true':
        special_keys = search_params
        search_params = {'start': 0, 'draw': 1, 'length': 0, 'order_index': 0, 'order_term': u'asc',
                        'search_term' : request.POST.get('search[value]','')}
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
        headers = {}
        for key, value in request_data.iteritems():
            if not ('search' in key or key in ['datatable', 'excel']):
                headers[key] = value
        excel_data = print_excel(request,temp_data, headers, excel_name=request_data.get('datatable'))
        return excel_data

    return HttpResponse(json.dumps(temp_data), content_type='application/json')
