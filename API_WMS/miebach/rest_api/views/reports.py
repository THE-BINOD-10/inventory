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
    elif report_name == 'order_summary_report':
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

        if 'order_report_status' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'order_report_status' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = ORDER_SUMMARY_REPORT_STATUS

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
    serial_view = False
    if request.GET.get('datatable', '') == 'serialView':
        serial_view = True
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_dispatch_data(search_params, user, request.user, serial_view=serial_view)

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
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_dispatch_data(search_params, user, request.user, serial_view=serial_view)
    report_data = report_data['aaData']

    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


def print_sku_wise_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    cmp_data = ('sku_code', 'wms_code', 'sku_category', 'sku_type', 'sku_class')
    for data in cmp_data:
        if data in search_params:
            search_parameters['%s__%s' % (data, 'iexact')] = search_params[data]

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['user'] = user.id

    sku_master = sku_master.filter(**search_parameters)
    temp_data['recordsTotal'] = len(sku_master)
    temp_data['recordsFiltered'] = len(sku_master)

    if stop_index:
        sku_master = sku_master[start_index:stop_index]

    for data in sku_master:
        total_quantity = 0
        stock_data = StockDetail.objects.exclude(location__zone__zone='DEFAULT').filter(sku_id=data.id)
        for stock in stock_data:
            total_quantity += int(stock.quantity)

        temp_data['aaData'].append(OrderedDict((('SKU Code', data.sku_code), ('WMS Code', data.wms_code),
                                                ('Product Description', data.sku_desc),
                                                ('SKU Category', data.sku_category),
                                                ('Total Quantity', total_quantity))))
    return temp_data


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
    search_parameters = {}
    search_parameters['open_po__sku_id__in'] = sku_master_ids
    supplier_data = {'aaData': []}
    supplier_name = search_params.get('supplier')
    if supplier_name:
        suppliers = PurchaseOrder.objects.exclude(status='location-assigned').filter(
            open_po__supplier__id=supplier_name, received_quantity__lt=F('open_po__order_quantity'),
            open_po__sku__user=user.id, **search_parameters)
    else:
        suppliers = PurchaseOrder.objects.exclude(status='location-assigned').filter(
            received_quantity__lt=F('open_po__order_quantity'), open_po__sku__user=user.id, **search_parameters)

    supplier_data['recordsTotal'] = len(suppliers)
    supplier_data['recordsFiltered'] = len(suppliers)
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    all_amount = [(supplier.open_po.order_quantity * supplier.open_po.price) for supplier in suppliers]
    total_charge = sum(all_amount)
    if stop_index:
        suppliers = suppliers[start_index:stop_index]

    for supplier in suppliers:
        price, quantity = supplier.open_po.price, supplier.open_po.order_quantity

        amount = price * quantity
        design_codes = SKUSupplier.objects.filter(supplier=supplier.open_po.supplier, sku=supplier.open_po.sku,
                                                  sku__user=user.id)
        supplier_code = ''
        if design_codes:
            supplier_code = design_codes[0].supplier_code
        status = ''
        if supplier.received_quantity == 0:
            status = 'Yet to Receive'
        elif (supplier.open_po.order_quantity - supplier.received_quantity) == 0:
            status = 'Received'
        else:
            status = 'Partially Received'
        supplier_data['aaData'].append(OrderedDict((('Order Date', str(supplier.po_date).split(' ')[0]),
                                                    ('PO Number', '%s%s_%s' % (supplier.prefix,
                                                                               str(supplier.po_date).split(' ')[
                                                                                   0].replace('-', ''),
                                                                               supplier.order_id)),
                                                    ('Supplier Name', supplier.open_po.supplier.name),
                                                    ('WMS Code', supplier.open_po.sku.wms_code),
                                                    ('Design', supplier_code),
                                                    ('Ordered Quantity', supplier.open_po.order_quantity),
                                                    ('Amount', amount),
                                                    ('Received Quantity', supplier.received_quantity),
                                                    ('Status', status))))
    supplier_data['total_charge'] = total_charge
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
    if 'from_date' in search_params:
        from_date = search_params['from_date'].split('/')
        search_parameters['creation_date__startswith'] = datetime.date(int(from_date[2]), int(from_date[0]),
                                                                       int(from_date[1]))
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
    sales_return = OrderReturns.objects.filter(**search_parameters)
    if marketplace:
        sales_return = OrderReturns.objects.filter(Q(order__marketplace=marketplace) | Q(marketplace=marketplace),
                                                   **search_parameters)
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

        if is_excel:
            if reasons:
                for reason in reasons:
                    temp_data['aaData'].append(OrderedDict((('SKU Code', data.sku.sku_code), ('Order ID', order_id),
                                                            ('Customer ID', customer_id),
                                                            ('Return Date', str(data.creation_date).split('+')[0]),
                                                            ('Market Place', marketplace),
                                                            ('Quantity', reason.quantity), ('Reason', reason.reason),
                                                            ('Status', reason.status)
                                                            )))
            else:
                temp_data['aaData'].append(OrderedDict((('SKU Code', data.sku.sku_code), ('Order ID', order_id),
                                                        ('Customer ID', customer_id),
                                                        ('Return Date', str(data.creation_date).split('+')[0]),
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
                             ('customer_id', customer_id), ('return_date', str(data.creation_date).split('+')[0]),
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
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    if 'creation_date' in search_params:
        from_date = search_params['creation_date'].split('/')
        search_parameters['creation_date__startswith'] = datetime.date(int(from_date[2]), int(from_date[0]),
                                                                       int(from_date[1]))
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code'].upper()
    if 'wms_code' in search_params:
        search_parameters['sku__wms_code'] = search_params['wms_code'].upper()
    if 'order_id' in search_params:
        value = search_params['order_id'].strip('OD').strip('MN').strip('SR')
        search_parameters['order_id'] = value
    if 'customer_id' in search_params:
        search_parameters['order__customer_id'] = value
    search_parameters['sku__user'] = user.id
    if search_parameters:
        sales_return = OrderReturns.objects.filter(**search_parameters)
    else:
        sales_return = OrderReturns.objects.filter(user=user.id)
    report_data = []
    for data in sales_return:
        order_id = ''
        customer_id = ''
        if data.order:
            order_id = data.order.order_id
            customer_id = data.order.customer_id
        reasons = OrderReturnReasons.objects.filter(order_return=data.id)
        if reasons:
            for reason in reasons:
                report_data.append((data.sku.sku_code, order_id, customer_id, str(data.creation_date).split('+')[0],
                                    data.quantity, reason.reason, reason.status))
            continue
        report_data.append((data.sku.sku_code, order_id, customer_id, str(data.creation_date).split('+')[0],
                            data.quantity, data.reason, data.status))

    headers = ('SKU Code', 'Order ID', 'Customer ID', 'Return Date', 'Quantity', 'Reason', 'Status')
    html_data = create_reports_table(headers, report_data)
    return HttpResponse(html_data)


def get_adjust_filter_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['cycle__creation_date__gt'] = search_params['from_date']
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
    temp_data['recordsFiltered'] = len(adjustments)
    if stop_index:
        adjustments = adjustments[start_index:stop_index]
    for data in adjustments:
        quantity = int(data.cycle.seen_quantity) - int(data.cycle.quantity)

        temp_data['aaData'].append(
            OrderedDict((('SKU Code', data.cycle.sku.sku_code), ('Location', data.cycle.location.location),
                         ('Quantity', quantity), ('Date', str(data.creation_date).split('+')[0]),
                         ('Remarks', data.reason))))

    return temp_data


def get_aging_filter_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    all_data = OrderedDict()
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['receipt_date__gt'] = search_params['from_date']
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
    search_parameters['sku__user'] = user.id
    search_parameters['quantity__gt'] = 0
    search_parameters['sku_id__in'] = sku_master_ids
    filtered = StockDetail.objects.filter(**search_parameters). \
        values('receipt_date', 'sku__sku_code', 'sku__sku_desc', 'sku__sku_category', 'location__location'). \
        annotate(total=Sum('quantity'))

    for stock in filtered:
        cond = (stock['sku__sku_code'], stock['sku__sku_desc'], stock['sku__sku_category'],
                (datetime.datetime.now().date() - stock['receipt_date'].date()).days, stock['location__location'])
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
                         ('Location', data[4]), ('Quantity', temp[data]), ('As on Date(Days)', data[3]))))
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
    return HttpResponse(json.dumps({'categories': categories}))


@csrf_exempt
@login_required
@get_admin_user
def print_po_reports(request, user=''):
    receipt_type = ''
    for key, data_id in request.GET.iteritems():
        data_id = int(data_id)
        po_data = []
        if key == 'po_id':
            results = PurchaseOrder.objects.filter(order_id=data_id, open_po__sku__user=user.id)
        else:
            results = SellerPOSummary.objects.filter(id=data_id, purchase_order__open_po__sku__user=user.id)
        total = 0
        total_qty = 0
        for data in results:
            receipt_type = ''
            if key == 'po_id':
                open_data = data.open_po
                amount = float(data.received_quantity) * float(data.open_po.price)
                gst_tax = open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + open_data.utgst_tax
                if gst_tax:
                    amount += (amount / 100) * gst_tax
                po_data.append([open_data.sku.wms_code, open_data.order_quantity, data.received_quantity,
                                open_data.measurement_unit,
                                open_data.price, open_data.cgst_tax, open_data.sgst_tax, open_data.igst_tax,
                                open_data.utgst_tax, amount])
                total += amount
                total_qty += data.received_quantity
            else:
                po_order = data.purchase_order
                open_data = po_order.open_po
                amount = float(data.quantity) * float(open_data.price)
                gst_tax = open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + open_data.utgst_tax
                if gst_tax:
                    amount += (amount / 100) * gst_tax

                po_data.append(
                    [open_data.sku.wms_code, open_data.order_quantity, data.quantity, open_data.measurement_unit,
                     open_data.price,
                     open_data.cgst_tax, open_data.sgst_tax, open_data.igst_tax, open_data.utgst_tax, amount])
                total += amount
                total_qty += po_order.received_quantity
                receipt_type = data.seller_po.receipt_type

        if results:
            purchase_order = results[0]
            if not key == 'po_id':
                purchase_order = results[0].purchase_order
            address = purchase_order.open_po.supplier.address
            address = '\n'.join(address.split(','))
            telephone = purchase_order.open_po.supplier.phone_number
            name = purchase_order.open_po.supplier.name
            order_id = purchase_order.order_id
            po_reference = '%s%s_%s' % (
            purchase_order.prefix, str(purchase_order.creation_date).split(' ')[0].replace('-', ''),
            purchase_order.order_id)
            order_date = str(purchase_order.open_po.creation_date).split('+')[0]
            user_profile = UserProfile.objects.get(user_id=user.id)
            w_address = user_profile.address
        table_headers = (
        'WMS CODE', 'Order Quantity', 'Received Quantity', 'Measurement', 'Unit Price', 'CSGT(%)', 'SGST(%)', 'IGST(%)',
        'UTGST(%)', 'Amount')

    title = 'Purchase Order'
    if receipt_type == 'Hosted Warehouse':
        title = 'Stock Transfer Note'
    return render(request, 'templates/toggle/po_template.html',
                  {'table_headers': table_headers, 'data': po_data, 'address': address,
                   'order_id': order_id, 'telephone': str(telephone), 'name': name, 'order_date': order_date,
                   'total': total,
                   'po_reference': po_reference, 'w_address': w_address, 'company_name': user_profile.company_name,
                   'display': 'display-none', 'receipt_type': receipt_type, 'title': title, 'total_qty': total_qty})


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
    params = [search_params, user, request.user]
    if 'datatable=serialView' in form_data:
        params.append(True)
    report_data = func_name(*params)
    if isinstance(report_data, tuple):
        report_data = report_data[0]
    if temp[1] in ['grn_inventory_addition', 'sales_returns_addition', 'seller_stock_summary_replace'] and len(
            report_data['aaData']) > 0:
        headers = report_data['aaData'][0].keys()
        file_type = 'csv'
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
