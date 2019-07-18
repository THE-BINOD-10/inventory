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
from common import *
from miebach_utils import *
from inbound import generate_grn_pagination
from dateutil.relativedelta import *


@csrf_exempt
@login_required
@get_admin_user
def get_report_data(request, user=''):
    data = {}
    report_name = request.GET.get('report_name', '')
    if report_name:
        data = REPORT_DATA_NAMES.get(report_name, {})
    filter_keys = map(lambda d: d.get('name', ''), data.get('filters', ''))
    filter_params = {'user': user.id}
    sku_master = SKUMaster.objects.filter(**filter_params)
    if report_name == 'open_jo_report':
        if 'marketplace' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'marketplace' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = list(
                OrderDetail.objects.exclude(marketplace='').filter(quantity__gt=0))
        if 'brand' in filter_keys:
            data_index = data['filters'].index(filter(lambda person: 'brand' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = list(
                sku_master.exclude(sku_brand='').values_list('sku_brand', flat=True).distinct())
        if 'category' in filter_keys:
            data_index = data['filters'].index(filter(lambda person: 'category' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = list(sku_master.exclude(sku_category='').filter(**filter_params)
                                                         .values_list('sku_category', flat=True).distinct())
        if 'stage' in filter_keys:
            data_index = data['filters'].index(filter(lambda person: 'stage' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = list(ProductionStages.objects.filter(user=user.id).order_by('order')
                                                         .values_list('stage_name', flat=True))
            data['filters'][data_index]['values'].extend(
                ['Picked', 'Putaway pending', 'Picklist Generated', 'Created', 'Partially Picked'])
    elif report_name in ['order_summary_report','po_report','open_order_report','stock_cover_report']  :
        if report_name == 'order_summary_report' :
            from common import get_misc_value
            extra_order_fields = get_misc_value('extra_order_fields', user.id)
            data = copy.deepcopy(data)
            milkbasket_users = copy.deepcopy(MILKBASKET_USERS)
            if user.username in milkbasket_users :
                data['dt_headers'].append("Cost Price")
            if extra_order_fields == 'false' :
                extra_order_fields = []
            else:
                extra_order_fields = extra_order_fields.split(',')
                for header in extra_order_fields :
                    if header not in data['dt_headers'] :
                        data['dt_headers'].append(header)
        if 'marketplace' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'marketplace' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = list(
                OrderDetail.objects.exclude(marketplace='').filter(user=user.id).values_list('marketplace',
                                                                                             flat=True).distinct())
        if 'sku_category' in filter_keys:
            data_index = data['filters'].index(filter(lambda person: 'category' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = list(
                OrderDetail.objects.exclude(sku__sku_category='').filter(user=user.id).values_list('sku__sku_category',
                                                                                                   flat=True).distinct())
        if 'sister_warehouse' in filter_keys :
            sister_wh = get_sister_warehouse(user)
            data_index = data['filters'].index(filter(lambda person: 'sister_warehouse' in person['name'], data['filters'])[0])
            sister_warehouses = [user.username]
            sister_warehouses1 = list(
                UserGroups.objects.filter(Q(admin_user=user) | Q(user=user)).values_list('user__username',flat=True).distinct())
            data['filters'][data_index]['values'] = list(chain(sister_warehouses, sister_warehouses1))
        if 'order_report_status' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'order_report_status' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = ORDER_SUMMARY_REPORT_STATUS
    elif report_name in ('dist_sales_report', 'reseller_sales_report', 'enquiry_status_report',
                         'zone_target_summary_report', 'zone_target_detailed_report',
                         'corporate_reseller_mapping_report', ''):
        if 'order_report_status' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'order_report_status' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = ORDER_SUMMARY_REPORT_STATUS
        if 'enquiry_status' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'enquiry_status' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = ENQUIRY_REPORT_STATUS
        if 'zone_code' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'zone_code' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = ZONE_CODES
        if 'sku_category' in filter_keys:
            data_index = data['filters'].index(filter(lambda person: 'category' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = list(sku_master.exclude(sku_category='').filter(**filter_params)
                                                         .values_list('sku_category', flat=True).distinct())
    return HttpResponse(json.dumps({'data': data}))


@csrf_exempt
@login_required
@get_admin_user
def get_sku_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_sku_filter_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_sku(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_sku_filter_data(search_params, user, request.user)

    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_location_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data, total_quantity = get_location_stock_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_stock_location(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    report_data, total_quantity = get_location_stock_data(search_params, user, request.user)

    data = '<div>Total Stock: %s<br/><br/></div>' % total_quantity

    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(data + html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_po_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_po_filter_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_grn_edit_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_grn_edit_filter_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_sku_wise_po_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_sku_wise_po_filter_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_receipt_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_receipt_filter_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_receipt_summary(request, user=''):
    html_data = ''
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_receipt_filter_data(search_params, user, request.user)

    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_dispatch_filter(request, user=''):
    serial_view, customer_view = False, False
    if request.GET.get('datatable', '') == 'customerView':
        customer_view = True
    elif request.GET.get('datatable', '') == 'serialView':
        serial_view = True
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_dispatch_data(search_params, user, request.user, serial_view=serial_view, customer_view=customer_view)

    return HttpResponse(json.dumps(temp_data, cls=DjangoJSONEncoder), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_order_summary_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_order_summary_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_openjo_report_details(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_openjo_details(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_jostatus_report_details(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_jostatus_details(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_stock_summary_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_stock_summary_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@get_admin_user
def print_stock_summary_report(request, user=''):
    search_parameters = {}

    headers, search_params, filter_params = get_search_params(request)
    report_data = get_stock_summary_data(search_params, user, request.user)
    report_data = report_data['aaData']

    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@get_admin_user
def print_order_summary_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_order_summary_data(search_params, user, request.user)
    report_data = report_data['aaData']

    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@get_admin_user
def print_jo_status_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_order_summary_data(search_params, user, request.user)
    report_data = report_data['aaData']

    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def print_open_jo_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    search_params.update({'start': 0, 'draw': 1, 'length': 10, 'order_index': 0, 'order_term': u'asc'})
    report_data = get_openjo_details(search_params, user, request.user)
    report_data = report_data['aaData']

    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_daily_production_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_daily_production_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@get_admin_user
def print_daily_production_report(request, user=''):
    search_parameters = {}

    headers, search_params, filter_params = get_search_params(request)
    search_params.update({'start': 0, 'draw': 1, 'length': 10, 'order_index': 0, 'order_term': u'asc'})
    report_data = get_daily_production_data(search_params, user, request.user)
    report_data = report_data['aaData']

    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@get_admin_user
def print_dispatch_summary(request, user=''):
    search_parameters = {}
    serial_view = False
    if request.GET.get('datatable', '') == 'serialView':
        serial_view = True
    if request.GET.get('datatable', '') == 'customerView':
        customer_view = True
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_dispatch_data(search_params, user, request.user, serial_view=serial_view, customer_view=customer_view)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_sku_stock_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = print_sku_wise_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_sku_wise_stock(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    report_data = print_sku_wise_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_sku_purchase_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = sku_wise_purchase_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_sku_wise_purchase(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    report_data = sku_wise_purchase_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


def get_supplier_details_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    order_term = search_params.get('order_term', 'asc')
    order_index = search_params.get('order_index', 0)
    search_parameters = {}
    search_parameters['open_po__sku_id__in'] = sku_master_ids
    supplier_data = {'aaData': []}
    supplier_name = search_params.get('supplier')
    lis = ['order_id', 'order_id', 'open_po__supplier__name', 'total_ordered', 'total_received', 'order_id',
           'order_id']
    order_val = lis[order_index]
    if order_term == 'desc':
        order_val = '-%s' % lis[order_index]

    if supplier_name:
        suppliers = PurchaseOrder.objects.select_related('open_po').exclude(status='location-assigned').filter(
            open_po__supplier__id=supplier_name, received_quantity__lt=F('open_po__order_quantity'),
            open_po__sku__user=user.id, **search_parameters)
    else:
        suppliers = PurchaseOrder.objects.select_related('open_po').exclude(status='location-assigned').filter(
            received_quantity__lt=F('open_po__order_quantity'), open_po__sku__user=user.id, **search_parameters)
    purchase_orders = suppliers.values('order_id').distinct().annotate(total_ordered=Sum('open_po__order_quantity'),
                                                                       total_received=Sum('received_quantity')). \
                                                            order_by(order_val)

    supplier_data['recordsTotal'] = suppliers.count()
    supplier_data['recordsFiltered'] = suppliers.count()
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    #all_amount = [(supplier.open_po.order_quantity * supplier.open_po.price) for supplier in suppliers]
    #total_charge = sum(all_amount)
    if stop_index:
        purchase_orders = purchase_orders[start_index:stop_index]

    for purchase_order in purchase_orders:
        po_data = suppliers.filter(order_id=purchase_order['order_id'])
        total_amt = 0
        for po in po_data:
            price, quantity = po.open_po.price, po.open_po.order_quantity
            taxes = po.open_po.cgst_tax + po.open_po.sgst_tax + po.open_po.igst_tax + po.open_po.utgst_tax
            amt = price * quantity
            total_amt += amt + ((amt/100)*taxes)
        total_amt = truncate_float(total_amt, 2)
        po_obj = po_data[0]
        design_codes = SKUSupplier.objects.filter(supplier=po_obj.open_po.supplier, sku=po_obj.open_po.sku,
                                                  sku__user=user.id)
        supplier_code = ''
        if design_codes:
            supplier_code = design_codes[0].supplier_code
        status = ''
        if purchase_order['total_received'] == 0:
            status = 'Yet to Receive'
        elif purchase_order['total_ordered'] - purchase_order['total_received'] <= 0:
            status = 'Received'
        else:
            status = 'Partially Received'
        supplier_data['aaData'].append(OrderedDict((('Order Date', get_local_date(user, po_obj.po_date)),
                                                    ('PO Number', get_po_reference(po_obj)),
                                                    ('Supplier Name', po_obj.open_po.supplier.name),
                                                    ('WMS Code', po_obj.open_po.sku.wms_code),
                                                    ('Design', supplier_code),
                                                    ('Ordered Quantity', purchase_order['total_ordered']),
                                                    ('Amount', total_amt),
                                                    ('Received Quantity', purchase_order['total_received']),
                                                    ('Status', status), ('order_id', po_obj.order_id))))
    #supplier_data['total_charge'] = total_charge
    return supplier_data


@csrf_exempt
@login_required
@get_admin_user
def get_supplier_details(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    supplier_data = get_supplier_details_data(search_params, user, request.user)
    return HttpResponse(json.dumps(supplier_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_supplier_pos(request, user=''):
    html_data = ''
    headers, search_params, filter_params = get_search_params(request)
    supplier_pos = get_supplier_details_data(search_params, user, request.user)
    supplier_pos = supplier_pos['aaData']
    user_profile = UserProfile.objects.filter(user_id=request.user.id)

    if supplier_pos:
        html_data = create_po_reports_table(supplier_pos[0].keys(), supplier_pos, user_profile[0], '')
    return HttpResponse(html_data)


def get_sales_return_filter_data(search_params, user, request_user, is_excel=False):
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    status_dict = {'0': 'Inactive', '1': 'Active'}
    temp_data['draw'] = search_params.get('draw')
    marketplace = ''
    if 'creation_date' in search_params:
        search_parameters['creation_date__gt'] = search_params['creation_date']
    if 'to_date' in search_params:
        search_parameters['creation_date__lte'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code'].upper()
    if 'wms_code' in search_params:
        search_parameters['sku__wms_code'] = search_params['wms_code'].upper()
    if 'order_id' in search_params:
        value = search_params['order_id'].strip('OD').strip('MN').strip('SR')
        search_parameters['order__order_id'] = value
    if 'customer_id' in search_params:
        search_parameters['order__customer_id'] = search_params['customer_id']
    if 'marketplace' in search_params:
        marketplace = search_params['marketplace']
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['sku__user'] = user.id
    sales_return = OrderReturns.objects.filter(**search_parameters).exclude(quantity=0, damaged_quantity=0)
    if marketplace:
        sales_return = OrderReturns.objects.filter(Q(order__marketplace=marketplace) | Q(marketplace=marketplace),
                                                   **search_parameters).exclude(quantity=0, damaged_quantity=0)
    temp_data['recordsTotal'] = len(sales_return)
    temp_data['recordsFiltered'] = len(sales_return)
    if stop_index:
        sales_return = sales_return[start_index:stop_index]
    for data in sales_return:
        order_id = ''
        customer_id = ''
        marketplace = ''
        customer_name = ''
        if data.order:
            order_id = str(data.order.order_code) + str(data.order.order_id)
            customer_id = data.order.customer_id
            customer_name = data.order.customer_name
            marketplace = data.order.marketplace
            if not marketplace:
                marketplace = data.marketplace
        else:
            marketplace = data.marketplace

        reasons = OrderReturnReasons.objects.filter(order_return=data.id)
        reasons_data = []
        return_date = get_local_date(user, data.creation_date)

        if is_excel:
            if reasons:
                for reason in reasons:
                    temp_data['aaData'].append(OrderedDict((('SKU Code', data.sku.sku_code), ('Order ID', order_id),
                                                            ('Customer ID', customer_id),
                                                            ('Return Date', return_date),
                                                            ('Market Place', marketplace),
                                                            ('Quantity', reason.quantity), ('Reason', reason.reason),
                                                            ('Status', reason.status)
                                                            )))
            else:
                temp_data['aaData'].append(OrderedDict((('SKU Code', data.sku.sku_code), ('Order ID', order_id),
                                                        ('Customer ID', customer_id),
                                                        ('Return Date', return_date),
                                                        ('Market Place', marketplace), ('Quantity', data.quantity),
                                                        ('Reason', data.reason),
                                                        ('Status', data.status)
                                                        )))
        else:
            if reasons:
                for reason in reasons:
                    reasons_data.append({'quantity': reason.quantity, 'reason': reason.reason, 'status': reason.status})
            else:
                reasons_data.append({'quantity': data.quantity, 'reason': data.reason, 'status': data.status})

            temp_data['aaData'].append(
                OrderedDict((('sku_code', data.sku.sku_code), ('order_id', order_id), ('id', data.id),
                             ('customer_id', customer_id), ('return_date', return_date),
                             ('status', status_dict[str(data.status)]), ('marketplace', marketplace),
                             ('quantity', data.quantity), ('reasons_data', reasons_data),
                             ('customer_name', customer_name),
                             ('description', data.sku.sku_desc))))
    return temp_data


@csrf_exempt
@login_required
@get_admin_user
def get_sales_return_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_sales_return_filter_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data, cls=DjangoJSONEncoder), content_type='application/json')


@get_admin_user
def print_sales_returns(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_sales_return_filter_data(search_params, user, request.user, is_excel=True)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


def get_adjust_filter_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    warehouse_users = {}
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['cycle__creation_date__gte'] = search_params['from_date']
    else:
        search_parameters['cycle__creation_date__gte'] = date.today()+relativedelta(months=-1)
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['cycle__creation_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['cycle__sku__sku_code'] = search_params['sku_code'].upper()
    if 'wms_code' in search_params:
        search_parameters['cycle__sku__wms_code'] = search_params['wms_code'].upper()
    if 'location' in search_params:
        search_parameters['cycle__location__location'] = search_params['location'].upper()
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['cycle__sku__user'] = user.id
    search_parameters['cycle__sku_id__in'] = sku_master_ids
    if search_parameters:
        adjustments = InventoryAdjustment.objects.filter(**search_parameters)
    temp_data['recordsTotal'] = len(adjustments)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if stop_index:
        adjustments = adjustments[start_index:stop_index]
    for data in adjustments:
        quantity = int(data.cycle.seen_quantity) - int(data.cycle.quantity)
        temp_data['aaData'].append(OrderedDict(( ('SKU Code', data.cycle.sku.sku_code),
                                                 ('Location', data.cycle.location.location),
                                                 ('Quantity', quantity),
                                                 ('Pallet Code', data.pallet_detail.pallet_code if data.pallet_detail else ''),
                                                 ('Date', str(data.creation_date).split('+')[0]),
                                                 ('Remarks', data.reason)
                                              )))
    return temp_data


def get_aging_filter_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
    all_data = OrderedDict()
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['receipt_date__gte'] = search_params['from_date']
    else:
        search_parameters['receipt_date__gte'] = date.today()+relativedelta(months=-1)
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['receipt_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code'].upper()
    if 'sku_category' in search_params:
        search_parameters['sku__sku_category'] = search_params['sku_category']
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    if central_order_mgmt == 'true':
        if 'sister_warehouse' in search_params:
            sister_warehouse_name = search_params['sister_warehouse']
            user = User.objects.get(username=sister_warehouse_name)
            warehouses = UserGroups.objects.filter(user_id=user.id)
        else:
            warehouses = UserGroups.objects.filter(admin_user_id=user.id)
        warehouse_users = dict(warehouses.values_list('user_id', 'user__username'))
        sku_master = SKUMaster.objects.filter(user__in=warehouse_users.keys())
        sku_master_ids = sku_master.values_list('id', flat=True)
    else:
        search_parameters['sku__user'] = user.id
    search_parameters['quantity__gt'] = 0
    search_parameters['sku_id__in'] = sku_master_ids
    filtered = StockDetail.objects.filter(**search_parameters). \
        values('receipt_date', 'sku__sku_code', 'sku__sku_desc', 'sku__sku_category', 'location__location', 'sku__user'). \
        annotate(total=Sum('quantity'))

    for stock in filtered:
        cond = (stock['sku__sku_code'], stock['sku__sku_desc'], stock['sku__sku_category'],
                (datetime.datetime.now().date() - stock['receipt_date'].date()).days, stock['location__location'], stock['sku__user'])
        all_data.setdefault(cond, 0)
        all_data[cond] += stock['total']
    temp_data['recordsTotal'] = len(all_data)
    temp_data['recordsFiltered'] = len(all_data)
    temp = all_data
    all_data = all_data.keys()
    if stop_index:
        all_data = all_data[start_index:stop_index]
    for data in all_data:
        temp_data['aaData'].append(
            OrderedDict((('SKU Code', data[0]), ('SKU Description', data[1]), ('SKU Category', data[2]),
                         ('Location', data[4]), ('Quantity', temp[data]), ('As on Date(Days)', data[3]), ('Warehouse', warehouse_users.get(data[5])))))
    return temp_data


@csrf_exempt
@get_admin_user
def get_inventory_aging_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_aging_filter_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def sku_category_list(request, user=''):
    categories = list(SKUMaster.objects.exclude(sku_category='').filter(user=user.id).values_list('sku_category',
                                                                                                  flat=True).distinct())
    sister_warehouses1 = list(
                UserGroups.objects.filter(Q(admin_user=user) | Q(user=user)).values_list('user__username',flat=True).distinct())
    return HttpResponse(json.dumps({'categories': categories, 'sister_warehouses': sister_warehouses1}))


@csrf_exempt
@login_required
@get_admin_user
def print_po_reports(request, user=''):
    receipt_type = ''
    po_id = request.GET.get('po_id', '')
    po_summary_id = request.GET.get('po_summary_id', '')
    receipt_no = request.GET.get('receipt_no', '')
    data_dict = ''
    bill_no = ''
    bill_date = ''
    sr_number = ''
    #po_data = []
    headers = (
    'WMS CODE', 'Order Quantity', 'Received Quantity', 'Measurement', 'Unit Price', 'CSGT(%)', 'SGST(%)', 'IGST(%)',
    'UTGST(%)', 'Amount', 'Description')
    po_data = {headers: []}
    oneassist_condition = get_misc_value('dispatch_qc_check', user.id)
    if po_id:
        results = PurchaseOrder.objects.filter(order_id=po_id, open_po__sku__user=user.id)
        if receipt_no:
            results = results.distinct().filter(sellerposummary__receipt_number=receipt_no)
    elif po_summary_id:
        results = SellerPOSummary.objects.filter(id=po_summary_id, purchase_order__open_po__sku__user=user.id)
    total = 0
    total_qty = 0
    total_tax = 0
    overall_discount = 0
    for data in results:
        receipt_type = ''
        if po_id:
            quantity = data.received_quantity
            bill_date = data.updation_date
            if receipt_no:
                seller_summary_objs = data.sellerposummary_set.filter(receipt_number=receipt_no)
                open_data = data.open_po
                grouped_data = OrderedDict()
                if seller_summary_objs[0].overall_discount :
                    overall_discount = seller_summary_objs[0].overall_discount
                else:
                    overall_discount = 0
                for seller_summary_obj in seller_summary_objs:
                    quantity = seller_summary_obj.quantity
                    bill_no = seller_summary_obj.invoice_number if seller_summary_obj.invoice_number else ''
                    bill_date = seller_summary_obj.invoice_date if seller_summary_obj.invoice_date else data.updation_date
                    price = open_data.price
                    cgst_tax = open_data.cgst_tax
                    sgst_tax = open_data.sgst_tax
                    igst_tax = open_data.igst_tax
                    utgst_tax = open_data.utgst_tax
                    cess_tax = open_data.cess_tax
                    apmc_tax = seller_summary_obj.apmc_tax
                    if seller_summary_obj.cess_tax:
                        cess_tax = seller_summary_obj.cess_tax
                    gst_tax = cgst_tax + sgst_tax + igst_tax + utgst_tax + cess_tax + apmc_tax
                    discount = seller_summary_obj.discount_percent
                    if seller_summary_obj.batch_detail:
                        price = seller_summary_obj.batch_detail.buy_price
                        temp_tax_percent = seller_summary_obj.batch_detail.tax_percent
                        if seller_summary_obj.purchase_order.open_po.supplier.tax_type == 'intra_state':
                            temp_tax_percent = temp_tax_percent / 2
                            cgst_tax = truncate_float(temp_tax_percent, 1)
                            sgst_tax = truncate_float(temp_tax_percent, 1)
                            igst_tax = 0
                        else:
                            igst_tax = temp_tax_percent
                            cgst_tax = 0
                            sgst_tax = 0
                        gst_tax = cgst_tax + sgst_tax + igst_tax + utgst_tax + cess_tax + apmc_tax
                    grouping_key = '%s:%s' % (str(open_data.sku.sku_code), str(price))
                    amount = float(quantity) * float(price)
                    if discount:
                        amount = amount - (amount * float(discount)/100)
                    if gst_tax:
                        amount += (amount / 100) * gst_tax
                    grouped_data.setdefault(grouping_key, [open_data.sku.wms_code, open_data.order_quantity, 0,
                                             open_data.measurement_unit,
                                             price, cgst_tax, sgst_tax, igst_tax, utgst_tax,
                                             0, open_data.sku.sku_desc])
                    grouped_data[grouping_key][2] += quantity
                    grouped_data[grouping_key][9] += amount
                    total += amount
                    total_qty += quantity
                    total_tax += gst_tax
                po_data[headers] = list(chain(po_data[headers], grouped_data.values()))
            else:
                open_data = data.open_po
                amount = float(quantity) * float(data.open_po.price)
                gst_tax = open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + open_data.utgst_tax + open_data.apmc_tax
                if gst_tax:
                    amount += (amount / 100) * gst_tax
                po_data[headers].append((open_data.sku.wms_code, open_data.order_quantity, quantity,
                                open_data.measurement_unit,
                                open_data.price, open_data.cgst_tax, open_data.sgst_tax, open_data.igst_tax,
                                open_data.utgst_tax, amount, open_data.sku.sku_desc))
                total += amount
                total_qty += quantity
                total_tax += (open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + open_data.utgst_tax + open_data.cess_tax + open_data.apmc_tax)
        else:
            bill_date = data.invoice_date if data.invoice_date else data.creation_date
            bill_no = data.invoice_number if data.invoice_number else ''
            po_order = data.purchase_order
            open_data = po_order.open_po
            amount = float(data.quantity) * float(open_data.price)
            gst_tax = open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + open_data.utgst_tax
            if gst_tax:
                amount += (amount / 100) * gst_tax

            po_data[headers].append(
                (open_data.sku.wms_code, open_data.order_quantity, data.quantity, open_data.measurement_unit,
                 open_data.price, open_data.cgst_tax, open_data.sgst_tax, open_data.igst_tax,
                 open_data.utgst_tax, amount, open_data.sku.sku_desc))
            total += amount
            total_qty += po_order.received_quantity
            receipt_type = data.seller_po.receipt_type
            total_tax += (open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + open_data.utgst_tax)

    if results:
        purchase_order = results[0]
        if not po_id:
            purchase_order = results[0].purchase_order
        address = purchase_order.open_po.supplier.address
        address = '\n'.join(address.split(','))
        telephone = purchase_order.open_po.supplier.phone_number
        name = purchase_order.open_po.supplier.name
        supplier_id = purchase_order.open_po.supplier.id
        tin_number = purchase_order.open_po.supplier.tin_number
        order_id = purchase_order.order_id
        po_reference = '%s%s_%s' % (
        purchase_order.prefix, str(purchase_order.creation_date).split(' ')[0].replace('-', ''),
        purchase_order.order_id)
        if receipt_no:
            po_reference = '%s/%s' % (po_reference, receipt_no)
        order_date = datetime.datetime.strftime(purchase_order.open_po.creation_date, "%d-%m-%Y")
        bill_date = datetime.datetime.strftime(bill_date, "%d-%m-%Y")
        user_profile = UserProfile.objects.get(user_id=user.id)
        w_address, company_address = get_purchase_company_address(user_profile)#user_profile.address
        data_dict = (('Order ID', order_id), ('Supplier ID', supplier_id),
                     ('Order Date', order_date), ('Supplier Name', name), ('GST NO', tin_number))
    if results and oneassist_condition == 'true':
        purchase_order = results[0]
        customer_data = OrderMapping.objects.filter(mapping_id=purchase_order.id, mapping_type='PO')
        if customer_data:
            admin_user = get_admin(user)
            interorder_data = IntermediateOrders.objects.filter(order_id=customer_data[0].order_id, user_id=admin_user.id)
            if interorder_data:
                inter_order_id  = interorder_data[0].interm_order_id
                courtesy_sr_number = OrderFields.objects.filter(original_order_id = inter_order_id, user = admin_user.id, name = 'original_order_id')
                if courtesy_sr_number:
                    sr_number = courtesy_sr_number[0].value
    sku_list = po_data[po_data.keys()[0]]
    sku_slices = generate_grn_pagination(sku_list)
    table_headers = (
    'WMS CODE', 'Order Quantity', 'Received Quantity', 'Measurement', 'Unit Price', 'CSGT(%)', 'SGST(%)', 'IGST(%)',
    'UTGST(%)', 'Amount', 'Description')

    title = 'Purchase Order'
    #if receipt_type == 'Hosted Warehouse':
    #    title = 'Stock Transfer Note'
    net_amount = total - overall_discount
    return render(request, 'templates/toggle/c_putaway_toggle.html',
                  {'table_headers': table_headers, 'data': po_data, 'data_slices': sku_slices, 'address': address,
                   'order_id': order_id, 'telephone': str(telephone), 'name': name, 'order_date': order_date,
                   'total_price': total, 'data_dict': data_dict, 'bill_no': bill_no,
                   'po_number': po_reference, 'company_address': w_address, 'company_name': user_profile.company_name,
                   'display': 'display-none', 'receipt_type': receipt_type, 'title': title,'overall_discount':overall_discount,
                   'total_received_qty': total_qty, 'bill_date': bill_date, 'total_tax': total_tax,'net_amount':net_amount,
                   'company_address': company_address, 'sr_number': sr_number})


@csrf_exempt
@get_admin_user
def excel_sales_return_report(request, user=''):
    excel_name = ''
    func_name = ''
    file_type = 'xls'
    headers, search_params, filter_params = get_search_params(request)
    if '&' in request.POST['serialize_data']:
        form_data = request.POST['serialize_data'].split('&')
    else:
        form_data = request.POST['serialize_data'].split('<>')
    for dat in form_data:
        temp = dat.split('=')
        if 'excel_name' in dat:
            excel_name = dat
            func_name = eval(EXCEL_REPORT_MAPPING[temp[1]])
            continue
        if len(temp) > 1 and temp[1]:
            if 'date' in dat:
                temp[1] = datetime.datetime.strptime(temp[1], '%m/%d/%Y')
            search_params[temp[0]] = temp[1]
    params = [search_params, user, request.user, True]
    headers = ['SKU Code', 'Order ID', 'Customer ID', 'Return Date', 'Market Place', 'Quantity', 'Reason', 'Status']
    report_data = get_sales_return_filter_data(*params)
    if isinstance(report_data, tuple):
        report_data = report_data[0]
    if temp[1] in ['grn_inventory_addition', 'sales_returns_addition', 'seller_stock_summary_replace'] and len(
            report_data['aaData']) > 0:
        headers = report_data['aaData'][0].keys()
        file_type = 'csv'
    excel_data = print_excel(request, report_data, headers, excel_name, file_type=file_type)
    return excel_data


@csrf_exempt
@get_admin_user
def excel_reports(request, user=''):
    excel_name = ''
    func_name = ''
    file_type = 'xls'
    headers, search_params, filter_params = get_search_params(request, user)
    if '&' in request.POST['serialize_data']:
        form_data = request.POST['serialize_data'].split('&')
    else:
        form_data = request.POST['serialize_data'].split('<>')
    for dat in form_data:
        temp = dat.split('=')
        if 'excel_name' in dat:
            excel_name = dat
            func_name = eval(EXCEL_REPORT_MAPPING[temp[1]])
            continue
        if len(temp) > 1 and temp[1]:
            if 'date' in dat:
                temp[1] = datetime.datetime.strptime(temp[1], '%m/%d/%Y')
            search_params[temp[0]] = temp[1]
    params = [search_params, user, request.user]
    if 'datatable=serialView' in form_data:
        params.append(True)
    if 'datatable=customerView' in form_data:
        params.append(False)
        params.append(True)
    report_data = func_name(*params)
    if isinstance(report_data, tuple):
        report_data = report_data[0]
    if temp[1] in ['grn_inventory_addition', 'sales_returns_addition', 'seller_stock_summary_replace'] and len(
            report_data['aaData']) > 0:
        headers = report_data['aaData'][0].keys()
        file_type = 'csv'
    if temp[1] in ['dispatch_summary'] and len(report_data['aaData']) > 0:
        headers = report_data['aaData'][0].keys()
    excel_data = print_excel(request, report_data, headers, excel_name, file_type=file_type)
    return excel_data


@csrf_exempt
@login_required
@get_admin_user
def get_inventory_adjust_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_adjust_filter_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_adjust_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_adjust_filter_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def print_aging_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_aging_filter_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_marketplaces_list_reports(request, user=''):
    sales_marketplace = list(OrderReturns.objects.exclude(marketplace='').filter(status=1, sku__user=user.id). \
                             values_list('marketplace', flat=True).distinct())
    order_marketplace = list(OrderDetail.objects.exclude(marketplace='').filter(status=1, user=user.id, quantity__gt=0). \
                             values_list('marketplace', flat=True).distinct())

    marketplace = list(set(sales_marketplace) | set(order_marketplace))

    return HttpResponse(json.dumps({'marketplaces': marketplace}))


@csrf_exempt
@login_required
@get_admin_user
def get_seller_invoices_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_seller_invoices_filter_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_seller_invoice_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_seller_invoices_filter_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def print_rm_picklist_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_rm_picklist_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_rm_picklist_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_rm_picklist_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_stock_ledger_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_stock_ledger_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_stock_ledger_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_stock_ledger_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_dist_sales_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_dist_sales_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_dist_sales_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_dist_sales_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_reseller_sales_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_reseller_sales_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_reseller_sales_report(request, user=''):
    html_data = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_reseller_sales_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_zone_target_summary_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_zone_target_summary_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_zone_target_summary_report(request, user=''):
    html_data = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_zone_target_summary_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_zone_target_detailed_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_zone_target_detailed_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_zone_target_detailed_report(request, user=''):
    html_data = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_zone_target_detailed_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_dist_target_summary_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_dist_target_summary_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_dist_target_summary_report(request, user=''):
    html_data = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_dist_target_summary_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_dist_target_detailed_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_dist_target_detailed_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_dist_target_detailed_report(request, user=''):
    html_data = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_dist_target_detailed_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_reseller_target_summary_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_reseller_target_summary_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_reseller_target_summary_report(request, user=''):
    html_data = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_reseller_target_summary_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_reseller_target_detailed_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_reseller_target_detailed_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_reseller_target_detailed_report(request, user=''):
    html_data = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_reseller_target_detailed_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_corporate_target_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_corporate_target_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_corporate_target_report(request, user=''):
    html_data = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_corporate_target_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_corporate_reseller_mapping_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_corporate_reseller_mapping_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_corporate_reseller_mapping_report(request, user=''):
    html_data = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_corporate_reseller_mapping_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_enquiry_status_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_enquiry_status_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_stock_transfer_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_stock_transfer_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def print_enquiry_status_report(request, user=''):
    html_data = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_enquiry_status_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_shipment_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_shipment_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_po_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_po_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_open_order_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_open_order_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_stock_cover_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_stock_cover_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def print_shipment_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_shipment_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def print_po_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_po_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

@csrf_exempt
@login_required
@get_admin_user
def print_open_order_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_open_order_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

@csrf_exempt
@login_required
@get_admin_user
def print_stock_cover_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_stock_cover_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def print_purchase_order_form(request, user=''):
    po_id = request.GET.get('po_id', '')
    total_qty = 0
    total = 0
    if not po_id:
        return HttpResponse("Purchase Order Id is missing")
    purchase_orders = PurchaseOrder.objects.filter(open_po__sku__user=user.id, order_id=po_id)
    po_sku_ids = purchase_orders.values_list('open_po__sku_id', flat=True)
    ean_flag = False
    ean_data = SKUMaster.objects.filter(Q(ean_number__gt=0) | Q(eannumbers__ean_number__gt=0),
                                        id__in=po_sku_ids, user=user.id)
    if ean_data:
        ean_flag = True
    show_cess_tax = purchase_orders.filter(open_po__cess_tax__gt=0).exists()
    show_apmc_tax = purchase_orders.filter(open_po__apmc_tax__gt=0).exists()
    display_remarks = get_misc_value('display_remarks_mail', user.id)
    po_data = []
    if user.userprofile.industry_type == 'FMCG':
        table_headers = ['WMS Code', 'Supplier Code', 'Desc', 'Qty', 'UOM', 'Unit Price', 'MRP',
                         'Amt', 'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'Total']
        if user.username in MILKBASKET_USERS:
            table_headers.insert(4, 'Weight')
    else:
        table_headers = ['WMS Code', 'Supplier Code', 'Desc', 'Qty', 'UOM', 'Unit Price',
                         'Amt', 'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'Total']
    if ean_flag:
        table_headers.insert(1, 'EAN')
    if display_remarks == 'true':
        table_headers.append('Remarks')
    if show_cess_tax:
        table_headers.insert(table_headers.index('Total'), 'CESS (%)')
    if show_apmc_tax:
        table_headers.insert(table_headers.index('Total'), 'APMC (%)')
    for order in purchase_orders:
        open_po = order.open_po
        total_qty += open_po.order_quantity
        amount = open_po.order_quantity * open_po.price
        tax = open_po.cgst_tax + open_po.sgst_tax + open_po.igst_tax + open_po.utgst_tax + open_po.cess_tax + open_po.apmc_tax
        total += amount + ((amount / 100) * float(tax))
        total_tax_amt = (open_po.utgst_tax + open_po.sgst_tax + open_po.cgst_tax + open_po.igst_tax + open_po.cess_tax
            + open_po.utgst_tax + open_po.apmc_tax) * (amount/100)
        total_sku_amt = total_tax_amt + amount
        if user.userprofile.industry_type == 'FMCG':
            po_temp_data = [open_po.sku.sku_code, open_po.supplier_code, open_po.sku.sku_desc,
                            open_po.order_quantity, open_po.measurement_unit, open_po.price, open_po.mrp,amount,
                            open_po.sgst_tax, open_po.cgst_tax, open_po.igst_tax,
                            open_po.utgst_tax, total_sku_amt]
            if user.username in MILKBASKET_USERS:
                weight_obj = open_po.sku.skuattributes_set.filter(attribute_name='weight'). \
                    only('attribute_value')
                weight = ''
                if weight_obj.exists():
                    weight = weight_obj[0].attribute_value
                po_temp_data.insert(4, weight)
        else:
            po_temp_data = [open_po.sku.sku_code, open_po.supplier_code, open_po.sku.sku_desc,
                            open_po.order_quantity, open_po.measurement_unit, open_po.price, amount,
                            open_po.sgst_tax, open_po.cgst_tax, open_po.igst_tax,
                            open_po.utgst_tax, total_sku_amt]

        if ean_flag:
            ean_number = ''
            eans = get_sku_ean_list(open_po.sku)
            if eans:
                ean_number = eans[0]
            po_temp_data.insert(1, ean_number)
        if show_cess_tax:
            po_temp_data.insert(table_headers.index('CESS (%)'), open_po.cess_tax)
        if show_apmc_tax:
            po_temp_data.insert(table_headers.index('APMC (%)'), open_po.apmc_tax)
        if display_remarks == 'true':
            po_temp_data.append(open_po.remarks)
        # if show_cess_tax:
        #     po_temp_data.insert(table_headers.index('CESS (%)'), open_po.cess_tax)
        po_data.append(po_temp_data)
    order = purchase_orders[0]
    open_po = order.open_po
    address = open_po.supplier.address
    address = '\n'.join(address.split(','))
    vendor_name = ''
    vendor_address = ''
    vendor_telephone = ''
    if open_po.order_type == 'VR':
        vendor_address = open_po.vendor.address
        vendor_address = '\n'.join(vendor_address.split(','))
        vendor_name = open_po.vendor.name
        vendor_telephone = open_po.vendor.phone_number
    telephone = open_po.supplier.phone_number
    name = open_po.supplier.name
    order_id = order.order_id
    gstin_no = open_po.supplier.tin_number
    if open_po:
        address = open_po.supplier.address
        address = '\n'.join(address.split(','))
        if open_po.ship_to:
            ship_to_address = open_po.ship_to
            company_address = user.userprofile.address
        else:
            ship_to_address, company_address = get_purchase_company_address(user.userprofile)
        ship_to_address = '\n'.join(ship_to_address.split(','))
        telephone = open_po.supplier.phone_number
        name = open_po.supplier.name
        supplier_email = open_po.supplier.email_id
        gstin_no = open_po.supplier.tin_number
        if open_po.order_type == 'VR':
            vendor_address = open_po.vendor.address
            vendor_address = '\n'.join(vendor_address.split(','))
            vendor_name = open_po.vendor.name
            vendor_telephone = open_po.vendor.phone_number
        terms_condition = open_po.terms
    wh_telephone = user.userprofile.wh_phone_number
    order_date = get_local_date(request.user, order.creation_date)
    po_reference = '%s%s_%s' % (order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order_id)
    total_amt_in_words = number_in_words(round(total)) + ' ONLY'
    round_value = float(round(total) - float(total))
    profile = user.userprofile
    company_name = profile.company_name
    title = 'Purchase Order'
    receipt_type = request.GET.get('receipt_type', '')
    left_side_logo = get_po_company_logo(user, LEFT_SIDE_COMPNAY_LOGO , request)

    # if receipt_type == 'Hosted Warehouse':
    #if request.POST.get('seller_id', ''):
    #    title = 'Stock Transfer Note'
    if request.POST.get('seller_id', '') and 'shproc' in str(request.POST.get('seller_id').split(":")[1]).lower():
        company_name = 'SHPROC Procurement Pvt. Ltd.'
        title = 'Purchase Order'
    data_dict = {
                 'table_headers': table_headers,
                 'data': po_data,
                 'address': address,
                 'order_id': order_id,
                 'telephone': str(telephone),
                 'name': name,
                 'order_date': order_date,
                 'total': round(total),
                 'total_qty': total_qty,
                 'vendor_name': vendor_name,
                 'vendor_address': vendor_address,
                 'vendor_telephone': vendor_telephone,
                 'gstin_no': gstin_no,
                 'w_address': ship_to_address,#get_purchase_company_address(profile),
                 'ship_to_address': ship_to_address,
                 'wh_telephone': wh_telephone,
                 'wh_gstin': profile.gst_number,
                 'terms_condition' : terms_condition,
                 'total_amt_in_words' : total_amt_in_words,
                 'show_cess_tax': show_cess_tax,
                 'company_name': profile.company_name,
                 'location': profile.location,
                 'po_reference': po_reference,
                 'industry_type': profile.industry_type,
                 'left_side_logo':left_side_logo,
                 'company_address': company_address
                }
    if round_value:
        data_dict['round_total'] = "%.2f" % round_value
    return render(request, 'templates/toggle/po_template.html', data_dict)

@csrf_exempt
@login_required
@get_admin_user
def get_rtv_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_rtv_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_rtv_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_rtv_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def print_debit_note(request, user=''):
    from rest_api.views.inbound import get_debit_note_data
    receipt_type = ''
    rtv_number = request.GET.get('rtv_number', '')
    if rtv_number:
        show_data_invoice = get_debit_note_data(rtv_number, user)
        return render(request, 'templates/toggle/milk_basket_print.html', {'show_data_invoice': [show_data_invoice]})
    else:
        return HttpResponse("No Data")


@csrf_exempt
@login_required
@get_admin_user
def get_sku_wise_rtv_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_sku_wise_rtv_filter_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_current_stock_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_current_stock_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_inventory_value_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_inventory_value_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_current_stock_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_current_stock_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def print_inventory_value_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_inventory_value_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_bulk_to_retail_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_bulk_to_retail_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_bulk_to_retail_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_bulk_to_retail_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_stock_reconciliation_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_stock_reconciliation_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_margin_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_margin_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@get_admin_user
def print_stock_reconciliation_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_stock_reconciliation_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


def print_margin_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_margin_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)
