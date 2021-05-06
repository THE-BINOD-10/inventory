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
from inbound_common_operations import generate_grn_pagination
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
    elif report_name in ['order_summary_report', 'po_report', 'open_order_report', 'stock_cover_report', 'open_po_aprroval_report', 'aprroval_po_summary_report', 'aprroval_po_detail_report']:
        if report_name == 'order_summary_report':
            from common import get_misc_value
            extra_order_fields = get_misc_value('extra_order_fields', user.id)
            data = copy.deepcopy(data)
            milkbasket_users = copy.deepcopy(MILKBASKET_USERS)
            if user.username in milkbasket_users:
                data['dt_headers'].append("Cost Price")
            if extra_order_fields == 'false':
                extra_order_fields = []
            else:
                extra_order_fields = extra_order_fields.split(',')
                for header in extra_order_fields:
                    if header not in data['dt_headers']:
                        data['dt_headers'].append(header)
                    if header not in data['mk_dt_headers']:
                        data['mk_dt_headers'].append(header)
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
        if 'sister_warehouse' in filter_keys:
            sister_wh = get_sister_warehouse(user)
            data_index = data['filters'].index(
                filter(lambda person: 'sister_warehouse' in person['name'], data['filters'])[0])
            sister_warehouses = [user.username]
            sister_warehouses1 = list(
                UserGroups.objects.filter(Q(admin_user=user) | Q(user=user)).values_list('user__username',flat=True).distinct())
            data['filters'][data_index]['values'] = list(set(chain(sister_warehouses, sister_warehouses1)))
        if 'order_report_status' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'order_report_status' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = ORDER_SUMMARY_REPORT_STATUS
    elif report_name in ['st_grn_report']:
        admin_user=get_admin(user)
        if 'sister_warehouse' in filter_keys:
            sister_wh = get_sister_warehouse(admin_user)
            data_index = data['filters'].index(
                filter(lambda person: 'sister_warehouse' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = list(sister_wh.values_list('user__username', flat=True))

    elif report_name in ['pr_report', 'pr_detail_report','metro_po_report', 'metro_po_detail_report', 'rtv_report',
                         'sku_wise_rtv_report', 'cancel_grn_report', 'sku_wise_cancel_grn_report', 'metropolis_po_report',
                         'metropolis_po_detail_report', 'pr_po_grn_dict', 'integration_report', 'grn_report', 'sku_wise_grn_report', 'supplier_wise_po_report',
                         'sku_wise_consumption_report', 'closing_stock_report', 'consumption_data', 'get_consumption_data']:
        if 'sister_warehouse' in filter_keys:
            '''if user.userprofile.warehouse_type == 'ADMIN':
                user_data = get_all_department_data(user)
                sister_wh = user_data.keys()
            else:
                sister_wh =UserGroups.objects.filter((Q(admin_user=user) | Q(user=user))).values_list('user_id', flat=True)

            data_index = data['filters'].index(
                 filter(lambda person: 'sister_warehouse' in person['name'], data['filters'])[0])
            sister_warehouses = []
            # sister_warehouses1 = list(UserProfile.objects.filter(user_id__in=sister_warehouses, warehouse_type="DEPT").\
            #                           values_list('user__username',flat=True).distinct())

            sister_warehouses1 = list(UserProfile.objects.filter(user_id__in=sister_wh, warehouse_type="DEPT").\
                values_list('user__first_name', flat=True))

            data['filters'][data_index]['values'] = list(set(chain(sister_warehouses, sister_warehouses1)))'''
            users = [user.id]
            sub_user = request.user
            if sub_user.is_staff and user.userprofile.warehouse_type == 'ADMIN':
                users = get_related_users_filters(user.id, warehouse_types=['DEPT'])
            else:
                users = [user.id]
                users = check_and_get_plants_depts_wo_request(sub_user, user, users)
                users = users.filter(userprofile__warehouse_type='DEPT')
            depts = users.values_list('first_name', flat=True).distinct()
            data_index = data['filters'].index(filter(lambda person: 'sister_warehouse' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = list(depts)

        if 'final_status' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'final_status' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = PR_REPORT_PR_STATUS
        if 'po_status' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'po_status' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = PO_REPORT_PO_STATUS

        if 'status' in filter_keys:
            data_index = data['filters'].index(filter(lambda person: 'status' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = PURCHASE_ORDER_REPORT_STATUS
        if 'priority_type' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'priority_type' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = PR_REPORT_PRIORITY_STATUS

        if 'product_category' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'product_category' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = PRODUCT_CATEGORIES

        if 'po_view' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'po_view' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = PO_REPORT_VIEW
        if 'zone_code' in filter_keys:
            data_index = data['filters'].index(filter(lambda person: 'zone_code' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = ZONE_CODES
        if 'consumption_type' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'consumption_type' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = CONSUMPTION_TYPE

        if 'integration_status' in filter_keys:
            data_index = data['filters'].index(
                filter(lambda person: 'integration_status' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = INTEGRATION_STATUS
        if 'integration_type' in filter_keys:
            data_index = data['filters'].index(filter(lambda person: 'integration_type' in person['name'], data['filters'])[0])
            data['filters'][data_index]['values'] = INTEGRATION_TYPES

    elif report_name in ('dist_sales_report', 'reseller_sales_report', 'enquiry_status_report',
                         'zone_target_summary_report', 'zone_target_detailed_report',
                         'corporate_reseller_mapping_report', 'financial_report', ''):
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
    temp_data = get_po_filter_data(request, search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_integration_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_integration_report_data(request, search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_pr_po_grn_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_pr_po_grn_filter_data(request, search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_st_po_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_st_po_filter_data(search_params, user, request.user)
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
    temp_data = get_sku_wise_po_filter_data(request, search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_sku_wise_st_po_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_sku_wise_st_po_filter_data(search_params, user, request.user)
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
    temp_data = get_dispatch_data(search_params, user, request.user, serial_view=serial_view,
                                  customer_view=customer_view)

    return HttpResponse(json.dumps(temp_data, cls=DjangoJSONEncoder), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_allocation_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_allocation_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data, cls=DjangoJSONEncoder), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_deallocation_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_deallocation_report_data(search_params, user, request.user)

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
def get_po_approval_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_po_approval_report_data(search_params, user, request.user)

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


@csrf_exempt
@login_required
@get_admin_user
def get_bulk_stock_update(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_bulk_stock_update_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@get_admin_user
def print_bulk_stock_update(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_bulk_stock_update_data(search_params, user, request.user)
    report_data = report_data['aaData']

    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

@csrf_exempt
@login_required
@get_admin_user
def get_order_flow_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_orderflow_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@get_admin_user
def print_order_flow_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_orderflow_data(search_params, user, request.user)
    report_data = report_data['aaData']

    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@get_admin_user
def print_stock_summary_report(request, user=''):
    search_parameters = {}

    headers, search_params, filter_params = get_search_params(request)
    report_data = get_stock_summary_data(search_params, user, request.user)
    report_data = report_data['aaData']

    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_financial_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_financial_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@get_admin_user
def print_financial_report_report(request, user=''):
    search_parameters = {}

    headers, search_params, filter_params = get_search_params(request)
    report_data = get_financial_report_data(search_params, user, request.user)
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
    report_data = get_dispatch_data(search_params, user, request.user, serial_view=serial_view,
                                    customer_view=customer_view)
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
def get_ageing_data_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_ageing_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_expired_stock_data_filter(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_expired_stock_data(search_params, user, request.user)

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
    users = [user.id]
    if sub_user.is_staff and user.userprofile.warehouse_type == 'ADMIN':
        users = get_related_users_filters(user.id)
    else:
        users = check_and_get_plants_wo_request(sub_user, user, users)
    #user_ids = list(users.values_list('id', flat=True))
    # sku_master, sku_master_ids = get_sku_master(user, sub_user)
    order_term = search_params.get('order_term', 'asc')
    order_index = search_params.get('order_index', 0)
    # search_parameters = {'open_po__sku_id__in': sku_master_ids}
    search_parameters = {}
    supplier_data = {'aaData': []}
    supplier_name = search_params.get('supplier')
    lis = ['created_date', 'open_po__sku__user', 'open_po__sku__user', 'open_po__sku__user', 'order_id', 'open_po__supplier__name', 'total_ordered', 'total_received', 'order_id',
           'order_id', 'created_date']
    order_val = lis[order_index]
    if order_term == 'desc':
        order_val = '-%s' % lis[order_index]
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['creation_date__gte'] = search_params['from_date']
    else:
        search_parameters['creation_date__gte'] = date.today() + relativedelta(months=-1)
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['creation_date__lt'] = search_params['to_date']
    print search_params
    if 'status' in search_params:
        status = search_params.get('status')
        if status == 'Yet To Receive':
            search_parameters['status'] = ''
        elif status == 'Partially Received':
            search_parameters['status'] = 'grn-generated'
        elif status == 'Received':
            search_parameters['status'] = 'location-assigned'
        elif status == 'Putaway Completed':
            search_parameters['status'] = 'confirmed-putaway'
    if 'po_number' in search_params:
        order_id = search_params.get('po_number')
        search_parameters['po_number'] = order_id
    if 'plant_code' in search_params:
        plant_code = search_params['plant_code']
        plant_users = list(users.filter(userprofile__stockone_code=plant_code,
                                    userprofile__warehouse_type__in=['STORE', 'SUB_STORE']).values_list('username', flat=True))
        if plant_users:
            users = get_related_users_filters(user.id, warehouse_types=['DEPT'], warehouse=plant_users, send_parent=True)
        else:
            users = User.objects.none()
    if 'plant_name' in search_params.keys():
        plant_name = search_params['plant_name']
        plant_users = list(users.filter(first_name=plant_name, userprofile__warehouse_type__in=['STORE', 'SUB_STORE']).\
                        values_list('username', flat=True))
        if plant_users:
            users = get_related_users_filters(user.id, warehouse_types=['DEPT'], warehouse=plant_users, send_parent=True)
        else:
            users = User.objects.none()
    if 'sister_warehouse' in search_params:
        dept_mapping = copy.deepcopy(DEPARTMENT_TYPES_MAPPING)
        dept_mapping_res = dict(zip(dept_mapping.values(), dept_mapping.keys()))
        dept_type = search_params['sister_warehouse']
        if dept_type.lower() != 'na':
            users = users.filter(userprofile__stockone_code=dept_mapping_res.get(dept_type, ''))
        else:
            users = users.filter(userprofile__warehouse_type__in=['STORE', 'SUB_STORE'])
    if 'zone_code' in search_params:
        zone_code = search_params['zone_code']
        users = users.filter(userprofile__zone=zone_code)
    user_ids = list(users.values_list('id', flat=True))
    if supplier_name:
        if ':' in supplier_name:
            supplier_name = supplier_name.split(':')[0]
        search_parameters['open_po__supplier__supplier_id'] = supplier_name
        suppliers = PurchaseOrder.objects.select_related('open_po').filter(
            open_po__sku__user__in=user_ids, **search_parameters).exclude(status='deleted')
    else:
        suppliers = PurchaseOrder.objects.select_related('open_po').exclude(status='deleted').filter(open_po__sku__user__in=user_ids, **search_parameters)
    purchase_orders = suppliers.values('order_id', 'status', 'prefix', 'po_number', 'open_po__sku__user').distinct().annotate(
        total_ordered=Sum('open_po__order_quantity'),
        total_received=Sum('received_quantity'),
        created_date=Cast('creation_date', DateField())). \
        order_by(order_val)

    supplier_data['recordsTotal'] = purchase_orders.count()
    supplier_data['recordsFiltered'] = purchase_orders.count()
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    # all_amount = [(supplier.open_po.order_quantity * supplier.open_po.price) for supplier in suppliers]
    # total_charge = sum(all_amount)
    if stop_index:
        purchase_orders = purchase_orders[start_index:stop_index]

    for purchase_order in purchase_orders:
        plant_code, plant_name, zone = [''] * 3
        pending_days = 0
        po_data = suppliers.filter(po_number=purchase_order['po_number'], open_po__sku__user=purchase_order['open_po__sku__user'])
        total_amt = 0
        total_ordered= 0
        for po in po_data:
            price, quantity = po.open_po.price, po.open_po.order_quantity
            taxes = po.open_po.cgst_tax + po.open_po.sgst_tax + po.open_po.igst_tax + po.open_po.utgst_tax + po.open_po.cess_tax
            amt = price * quantity
            total_amt += amt + ((amt / 100) * taxes)
            total_ordered += quantity
        total_amt = truncate_float(total_amt, 2)
        po_obj = po_data[0]
        design_codes = SKUSupplier.objects.filter(supplier=po_obj.open_po.supplier, sku=po_obj.open_po.sku,
                                                  sku__user=user.id)
        supplier_code = ''
        if design_codes:
            supplier_code = design_codes[0].supplier_code
        status_var = ''
        if purchase_order['status'] == '':
            status_var = 'Yet to Receive'
        elif purchase_order['status'] == 'location-assigned':
            status_var = 'Received'
        elif purchase_order['status'] == 'confirmed-putaway':
            status_var = 'Putaway Confirmed'
        else:
            status_var = 'Partially Received'
        if status_var not in  ['Received', 'Putaway Confirmed']:
            pending_days = (datetime.datetime.now() - po_obj.creation_date.replace(tzinfo=None)).days
        user_obj = users.get(id=po_obj.open_po.sku.user)
        if user_obj.userprofile.warehouse_type == 'DEPT':
            user_obj = get_admin(user_obj)
        plant_code = user_obj.userprofile.stockone_code
        plant_name = user_obj.first_name
        zone = user_obj.userprofile.zone
        supplier_data['aaData'].append(OrderedDict((('Order Date', get_local_date(user, po_obj.creation_date)),
                                                    ('Plant Code', plant_code),
                                                    ('Plant Name', plant_name),
                                                    ('Zone', zone),
                                                    ('PO Number', po_obj.po_number), #get_po_reference(po_obj)),
                                                    ('Supplier Name', po_obj.open_po.supplier.name),
                                                    ('SKU Code', po_obj.open_po.sku.wms_code),
                                                    ('Design', supplier_code),
                                                    ('Ordered Quantity', total_ordered),
                                                    ('Amount', total_amt),('prefix', purchase_order['prefix']),
                                                    ('Received Quantity', purchase_order['total_received']),
                                                    ('Status', status_var), ('order_id', po_obj.order_id),
                                                    ('PO Pending Days', pending_days))))
    # supplier_data['total_charge'] = total_charge
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
    order_code = get_order_prefix(user.id)
    if 'creation_date' in search_params:
        search_parameters['creation_date__gt'] = search_params['creation_date']
    if 'to_date' in search_params:
        search_parameters['creation_date__lte'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code'].upper()
    if 'wms_code' in search_params:
        search_parameters['sku__wms_code'] = search_params['wms_code'].upper()
    if 'order_id' in search_params:
        value = search_params['order_id'].strip('OD').strip(order_code).strip('SR')
        search_parameters['order__order_id'] = value
    if 'customer_id' in search_params:
        search_parameters['order__customer_id'] = search_params['customer_id']
    if 'sku_category' in search_params:
        search_parameters['sku__sku_category'] = search_params['sku_category']
    if 'sub_category' in search_params:
        search_parameters['sku__sub_category'] = search_params['sub_category']
    if 'sku_brand' in search_params:
        search_parameters['sku__sku_brand'] = search_params['sku_brand']
    if 'marketplace' in search_params:
        marketplace = search_params['marketplace']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

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
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in sales_return:
        order_id, order_date = '', ''
        customer_id, customer_name = '', ''
        invoice_number, invoice_date, credit_note_number = '', '', ''
        credit_wo_tax_amount, credit_tax_amount, tax_percent = 0, 0, 0
        state, city, customer_gst_no, unit_price, gst_number, hsn_code = '', '', '', '', '', ''
        manufacturer, searchable, bundle, marketplace = '', '', '', ''
        attributes_obj = SKUAttributes.objects.filter(sku_id=data.sku.id, attribute_name__in=attributes_list)
        if attributes_obj.exists():
            for attribute in attributes_obj:
                if attribute.attribute_name == 'Manufacturer':
                    manufacturer = attribute.attribute_value
                if attribute.attribute_name == 'Searchable':
                    searchable = attribute.attribute_value
                if attribute.attribute_name == 'Bundle':
                    bundle = attribute.attribute_value
        if data.order:
            order_id = str(data.order.order_code) + str(data.order.order_id)
            order_date = get_local_date(user, data.order.creation_date)
            customer_id = data.order.customer_id
            customer_name = data.order.customer_name
            marketplace = data.order.marketplace
            credit_note_number = data.credit_note_number
            unit_price = data.sku.price
            hsn_code = data.sku.hsn_code
            customer_data = CustomerMaster.objects.filter(user=user.id,customer_id=data.order.customer_id)
            if customer_data:
                state = customer_data[0].state
                customer_gst_no = customer_data[0].tin_number
                city = customer_data[0].city
            cod = data.order.customerordersummary_set.filter()
            invoice_number = data.invoice_number
            invoice_data = SellerOrderSummary.objects.filter(full_invoice_number=data.invoice_number)
            invoice_date = get_local_date(user, invoice_data[0].creation_date)
            if cod:
                cgst_tax = cod[0].cgst_tax
                sgst_tax = cod[0].sgst_tax
                igst_tax = cod[0].igst_tax
                credit_tax_amount = (credit_wo_tax_amount) * (cgst_tax + sgst_tax + igst_tax)/100
                tax_percent = cgst_tax + sgst_tax + igst_tax
            user_data = UserProfile.objects.filter(user=user.id)
            if user_data:
                gst_number = user_data[0].gst_number
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
                    temp_data['aaData'].append(OrderedDict((('SKU Code', data.sku.sku_code),
                                                            ('SKU Description',data.sku.sku_desc),
                                                            ('SKU Category', data.sku.sku_category),
                                                            ('SKU Sub Category', data.sku.sub_category),
                                                            ('SKU Brand', data.sku.sku_brand),
                                                            ('Order ID', order_id),
                                                            ('Order Date', order_date),
                                                            ('Credit Note Number', credit_note_number),
                                                            ('Credit Note Date', return_date),
                                                            ('Customer ID', customer_id),
                                                            ('Customer Name', customer_name),
                                                            ('Invoice Number', invoice_number),
                                                            ('Invoice Date', invoice_date),
                                                            # ('Return Date', return_date),
                                                            ('Unit Price', unit_price),
                                                            ('HSN Code', hsn_code),
                                                            ('Market Place', marketplace),
                                                            ('City', city),
                                                            ('Quantity', reason.quantity), ('Reason', reason.reason),
                                                            ('Status', reason.status)
                                                            )))
            else:
                temp_data['aaData'].append(OrderedDict((('SKU Code', data.sku.sku_code),
                                                        ('SKU Category', data.sku.sku_category),
                                                        ('SKU Description', data.sku.sku_desc),
                                                        ('SKU Sub Category', data.sku.sub_category),
                                                        ('SKU Brand', data.sku.sku_brand),
                                                        ('Order ID', order_id),
                                                        ('Order Date', order_date),
                                                        ('Credit Note Number', credit_note_number),
                                                        ('Credit Note Date', return_date),
                                                        ('Customer ID', customer_id),
                                                        ('Customer Name', customer_name),
                                                        ('Invoice Number', invoice_number),
                                                        ('Invoice Date', invoice_date),
                                                        # ('Return Date', return_date),
                                                        ('City', city),
                                                        ('Unit Price', unit_price),
                                                        ('Market Place', marketplace), ('Quantity', reasons.quantity),
                                                        ('Reason', reasons.reason),
                                                        ('Status', reasons.status)
                                                        )))
        else:
            if reasons:
                for reason in reasons:
                    credit_wo_tax_amount = reason.quantity * data.sku.price
                    reasons_data.append({'quantity': reason.quantity, 'reason': reason.reason, 'status': reason.status, 'credit_wo_tax_amount': credit_wo_tax_amount})
            else:
                credit_wo_tax_amount = data.quantity * data.sku.price
                reasons_data.append({'quantity': data.quantity, 'reason': data.reason, 'status': data.status, 'credit_wo_tax_amount': credit_wo_tax_amount})

            temp = OrderedDict((('sku_code', data.sku.sku_code),('sku_desc', data.sku.sku_desc),
                         ('sku_category', data.sku.sku_category),
                         ('sub_category', data.sku.sub_category),
                         ('sku_brand', data.sku.sku_brand),
                         ('order_id', order_id), ('id', data.id),('order_date', order_date),
                         ('customer_id', customer_id), ('customer_name', customer_name),
                         ('status', reasons_data[0]['status']), ('marketplace', marketplace),
                         ('quantity', reasons_data[0]['quantity']), ('reasons_data', reasons_data),
                         ('credit_note_number', credit_note_number), ('credit_note_date', return_date),
                         ('invoice_number', invoice_number),('invoice_date', invoice_date), ('unit_price', unit_price),
                         ('hsn_code', hsn_code),('credit_wo_tax_amount', reasons_data[0]['credit_wo_tax_amount']),
                         ('credit_tax_amount',round((reasons_data[0]['credit_wo_tax_amount'] * tax_percent)/100, 2)), ('total_credit_note_amount', round(reasons_data[0]['credit_wo_tax_amount'] + credit_tax_amount, 2)),
                         ('customer_gst_no', customer_gst_no), ('gst_number', gst_number),
                         ('city', city),('state',state),('reason', reasons_data[0]['reason']),('tax_percent', tax_percent)))
            if user.userprofile.industry_type == 'FMCG':
                temp['manufactured_date'], temp['expiry_date'], temp['batch_no'], temp['mrp'] = '', '', '', ''
                batch_detail_list = list(ReturnsLocation.objects.filter(returns_id=data.id).values_list('id', flat=True))
                if batch_detail_list:
                    batch_data = BatchDetail.objects.filter(transact_id__in=batch_detail_list, transact_type='return_loc')
                    if batch_data.exists():
                        batch_data = batch_data[0]
                        temp['manufactured_date'] = batch_data.manufactured_date
                        temp['expiry_date'] = batch_data.expiry_date
                        temp['batch_no'] = batch_data.batch_no
                        temp['mrp'] = batch_data.mrp
            if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
                temp['Manufacturer'] = manufacturer
                temp['Searchable'] = searchable
                temp['Bundle'] = bundle
            temp_data['aaData'].append(temp)
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
    from rest_api.views.common import get_sku_master, get_utc_start_date
    users = [user.id]
    if sub_user.is_staff and user.userprofile.warehouse_type == 'ADMIN':
        users = get_related_users_filters(user.id)
    else:
        users = [user.id]
        users = check_and_get_plants_depts_wo_request(sub_user, user, users)
    user_ids = list(users.values_list('id', flat=True))
    #sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    warehouse_users = {}
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_params['from_date'] = get_utc_start_date(search_params['from_date'])
        search_parameters['cycle__creation_date__gte'] = search_params['from_date']
    else:
        search_parameters['cycle__creation_date__gte'] = date.today() + relativedelta(months=-1)
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_params['to_date'] = get_utc_start_date(search_params['to_date'])
        search_parameters['cycle__creation_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['cycle__sku__sku_code'] = search_params['sku_code'].upper()
    if 'wms_code' in search_params:
        search_parameters['cycle__sku__wms_code'] = search_params['wms_code'].upper()
    if 'location' in search_params:
        search_parameters['cycle__location__location'] = search_params['location'].upper()
    if 'sku_brand' in search_params:
        if search_params['sku_brand']:
            search_parameters['cycle__sku__sku_brand__icontains'] = search_params['sku_brand']
    if 'sku_category' in search_params:
        if search_params['sku_category']:
            search_parameters['cycle__sku__sku_category__icontains'] = search_params['sku_category']
    if 'sub_category' in search_params:
        if search_params['sku_category']:
            search_parameters['cycle__sku__sub_category__icontains'] = search_params['sub_category']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['cycle__sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['cycle__sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['cycle__sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    order_term = search_params.get('order_term', 'asc')
    order_index = search_params.get('order_index', 0)
    search_parameters['cycle__sku__user__in'] = user_ids
    #search_parameters['cycle__sku_id__in'] = sku_master_ids
    if search_parameters:
        adjustments = InventoryAdjustment.objects.filter(**search_parameters)
    grouping_data = OrderedDict()
    industry_type = user.userprofile.industry_type
    user_type = user.userprofile.user_type
    if industry_type == 'FMCG' and user_type == 'marketplace_user':
        lis = ['cycle__sku__sku_code', 'cycle__sku__sku_desc', 'stock__batch_detail__weight',
               'stock__batch_detail__mrp', 'cycle__sku__sku_code', 'cycle__sku__sku_code', 'cycle__sku__sku_code',
               'cycle__sku__sku_brand', 'cycle__sku__sku_category', 'cycle__sku__sub_category',
               'cycle__sku__sku_code', 'cycle__location__location',
               'adjusted_quantity', 'cycle__sku__sku_code', 'cycle__sku__sku_code', 'reason', 'cycle__sku__sku_code',
               'cycle__sku__sku_code', 'cycle__sku__sku_code', 'cycle__sku__sku_code', 'cycle__sku__sku_code']
        order_data = lis[order_index]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        adjustments = adjustments.only('id', 'creation_date', 'stock__batch_detail__mrp',
                                       'stock__batch_detail__buy_price',
                                       'stock__batch_detail__weight', 'stock__batch_detail__tax_percent',
                                       'cycle__location__location', 'reason').order_by(order_data)
        for adjustment in adjustments:
            mrp = 0
            weight = ''
            amount = 0
            price = 0
            if adjustment.stock and adjustment.stock.batch_detail:
                batch_detail = adjustment.stock.batch_detail
                mrp = batch_detail.mrp
                weight = batch_detail.weight
                price = batch_detail.buy_price
                amount = adjustment.adjusted_quantity * batch_detail.buy_price
                if batch_detail.tax_percent:
                    amount = amount + ((amount / 100) * batch_detail.tax_percent)
            creation_date = adjustment.creation_date.strftime('%Y-%m-%d')
            group_key = (adjustment.cycle.sku.sku_code, mrp, weight, adjustment.cycle.location.location,
                         adjustment.reason, creation_date)
            grouping_data.setdefault(group_key, {'mrp': mrp, 'weight': weight,
                                                 'sku': adjustment.cycle.sku,
                                                 'location': adjustment.cycle.location.location,
                                                 'reason': adjustment.reason,
                                                 'creation_date': creation_date,
                                                 'quantity': 0,
                                                 'cycle_quantity':0,
                                                 'prices_list': [], 'amount': 0,
                                                 'cycle': adjustment.cycle})
            grouping_data[group_key]['quantity'] += adjustment.adjusted_quantity
            grouping_data[group_key]['cycle_quantity'] +=adjustment.cycle.seen_quantity
            grouping_data[group_key]['amount'] += amount
            grouping_data[group_key]['prices_list'].append(price)
        adjustments = grouping_data.values()
        temp_data['recordsTotal'] = len(adjustments)
        temp_data['recordsFiltered'] = temp_data['recordsTotal']
        if stop_index:
            adjustments = adjustments[start_index:stop_index]
        attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
        for data in adjustments:
            sku = data['sku']
            attributes_data = dict(sku.skuattributes_set.filter().values_list('attribute_name', 'attribute_value'))
            mrp = data['mrp']
            weight = data['weight']
            amount = '%.2f' % (data['amount'])
            qty = data['quantity']
            updated_user_name = user.username
            avg_cost = 0
            version_obj = Version.objects.using('reversion').get_for_object(data['cycle'])
            if version_obj.exists():
                updated_user_name = version_obj.order_by('-revision__date_created')[0].revision.user.username
            if amount and qty:
                avg_cost = '%.2f' % (float(amount) / qty)
            manufacturer, searchable, bundle = '', '', ''
            attributes_obj = SKUAttributes.objects.filter(sku_id=sku.id, attribute_name__in=attributes_list)
            if attributes_obj.exists():
                for attribute in attributes_obj:
                    if attribute.attribute_name == 'Manufacturer':
                        manufacturer = attribute.attribute_value
                    if attribute.attribute_name == 'Searchable':
                        searchable = attribute.attribute_value
                    if attribute.attribute_name == 'Bundle':
                        bundle = attribute.attribute_value
            if data['quantity'] < 0 :
                initial_quantity = abs(data['quantity'])
            else:
                initial_quantity = data['cycle_quantity'] - data['quantity']

            temp_data['aaData'].append(OrderedDict((('SKU Code', sku.sku_code),
                                                    ('Name', sku.sku_desc),
                                                    ('Weight', weight),
                                                    ('MRP', mrp),
                                                    ('Manufacturer', attributes_data.get('Manufacturer', '')),
                                                    ('Vendor', attributes_data.get('Vendor', '')),
                                                    ('Sheet', attributes_data.get('Sheet', '')),
                                                    ('Brand', sku.sku_brand),
                                                    ('Category', sku.sku_category),
                                                    ('Sub Category', sku.sub_category),
                                                    ('Manufacturer', manufacturer),
                                                    ('Searchable', searchable),
                                                    ('Bundle', bundle),
                                                    ('Sub Category type', attributes_data.get('Sub Category type', '')),
                                                    ('Location', data['location']),
                                                    ('Quantity', data['quantity']),
                                                    ('Average Cost', avg_cost),
                                                    ('Value', amount),
                                                    ('changed_qty', data['quantity']),
                                                    ('post_adjustment_qty', data['cycle_quantity']),
                                                    ('initial_quantity', initial_quantity),
                                                    ('changed_unit_value', avg_cost),
                                                    ('changed_total_value', amount),
                                                    ('Reason', data['reason']),
                                                    ('User', updated_user_name),
                                                    ('Transaction Date', data['creation_date']),
                                                    )))
    else:
        temp_data['recordsTotal'] = len(adjustments)
        temp_data['recordsFiltered'] = temp_data['recordsTotal']
        if stop_index:
            adjustments = adjustments[start_index:stop_index]
        for data in adjustments:
            #quantity = int(data.cycle.seen_quantity) - int(data.cycle.quantity)
            base_quantity = data.adjusted_quantity
            uom_dict = get_uom_with_sku_code(user, data.cycle.sku.sku_code, uom_type='purchase')
            pcf = uom_dict['sku_conversion']
            #if data.stock.batch_detail:
            #    pcf = data.stock.batch_detail.pcf
            quantity = base_quantity/pcf
            user_obj = User.objects.get(id=data.cycle.sku.user)
            dept_name = ''
            store_name = user_obj.first_name
            if user_obj.userprofile.warehouse_type == 'DEPT':
                dept_name = user_obj.first_name
                store_name = get_admin(user_obj).first_name
            temp_data['aaData'].append(OrderedDict((('SKU Code', data.cycle.sku.sku_code),
                                                    ('Brand', data.cycle.sku.sku_brand),
                                                    ('Category', data.cycle.sku.sku_category),
                                                    ('Sub Category', data.cycle.sku.sub_category),
                                                    ('Location', data.cycle.location.location),
                                                    ('Quantity', quantity),
                                                    ('Adjustment Value', '%.2f' % float(quantity*data.cycle.sku.average_price)),
                                                    ('Base Uom Quantity', base_quantity),
                                                    ('Pallet Code',
                                                     data.pallet_detail.pallet_code if data.pallet_detail else ''),
                                                    ('Date', get_local_date(user, data.creation_date)),
                                                    ('Remarks', data.reason),
                                                    ('Store', store_name),
                                                    ('Department', dept_name)
                                                    )))

    return temp_data


def get_aging_filter_data(search_params, user, sub_user):
    from rest_api.views.common import get_sku_master
    sku_master, sku_master_ids = get_sku_master(user, sub_user)
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    warehouse_users = {}
    central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
    all_data = OrderedDict()
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['receipt_date__gte'] = search_params['from_date']
    else:
        search_parameters['receipt_date__gte'] = date.today() + relativedelta(months=-1)
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_parameters['receipt_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code'].upper()
    if 'sku_category' in search_params:
        search_parameters['sku__sku_category'] = search_params['sku_category']
    if 'sku_brand' in search_params:
        if search_params['sku_brand']:
            search_parameters['sku__sku_brand__icontains'] = search_params['sku_brand']
    if 'sub_category' in search_params:
        if search_params['sub_category']:
            search_parameters['sku__sub_category__icontains'] = search_params['sub_category']
    if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
        if 'manufacturer' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['manufacturer']
        if 'searchable' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['searchable']
        if 'bundle' in search_params:
            search_parameters['sku__skuattributes__attribute_value__iexact'] = search_params['bundle']

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    if user.userprofile.warehouse_type == 'admin':
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
        values('receipt_date', 'sku__sku_code', 'sku__sku_desc', 'sku__sku_category', 'location__location', 'sku__user',
               'sku__sub_category', 'sku__sku_brand', 'sku_id',
               'receipt_type', 'receipt_number').annotate(total=Sum('quantity'))

    for stock in filtered:
        stock_date = get_stock_starting_date(stock['receipt_number'], stock['receipt_type'], stock['sku__user'],
                                             stock['receipt_date'])
        age_days = (datetime.datetime.now().date() - stock_date.date()).days
        cond = (stock['sku__sku_code'], stock['sku__sku_desc'], stock['sku__sku_category'],
                age_days, stock['location__location'], stock['sku__user'], stock['sku__sub_category'],
                stock['sku__sub_category'], stock['sku__sku_brand'], stock['sku_id'])
        all_data.setdefault(cond, 0)
        all_data[cond] += stock['total']
    temp_data['recordsTotal'] = len(all_data)
    temp_data['recordsFiltered'] = len(all_data)
    temp = all_data
    all_data = all_data.keys()
    if stop_index:
        all_data = all_data[start_index:stop_index]
    attributes_list = ['Manufacturer', 'Searchable', 'Bundle']
    for data in all_data:
        if data[9]:
            manufacturer, searchable, bundle = '', '', ''
            attributes_obj = SKUAttributes.objects.filter(sku_id=data[9], attribute_name__in=attributes_list)
            if attributes_obj.exists():
                for attribute in attributes_obj:
                    if attribute.attribute_name == 'Manufacturer':
                        manufacturer = attribute.attribute_value
                    if attribute.attribute_name == 'Searchable':
                        searchable = attribute.attribute_value
                    if attribute.attribute_name == 'Bundle':
                        bundle = attribute.attribute_value
        ord_dict = OrderedDict((('SKU Code', data[0]), ('SKU Description', data[1]), ('SKU Category', data[2]),
                                ('SKU Sub Category', data[6]), ('Sku Brand', data[7]),
                                ('Location', data[4]), ('Quantity', temp[data]), ('As on Date(Days)', data[3]),
                                ('Warehouse Name', warehouse_users.get(data[5]))))
        if user.userprofile.industry_type == 'FMCG' and user.userprofile.user_type == 'marketplace_user':
            ord_dict['Manufacturer'] = manufacturer
            ord_dict['Searchable'] = searchable
            ord_dict['Bundle'] = bundle
        temp_data['aaData'].append(ord_dict)
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
        UserGroups.objects.filter(Q(admin_user=user) | Q(user=user)).values_list('user__username',
                                                                                 flat=True).distinct())
    return HttpResponse(json.dumps({'categories': categories, 'sister_warehouses': sister_warehouses1}))


@csrf_exempt
@login_required
@get_admin_user
def department_warehouse(request, user=''):
    # categories = list(SKUMaster.objects.exclude(sku_category='').filter(user=user.id).values_list('sku_category',
    #                                                                                               flat=True).distinct())
    sister_warehouses1 = list(
        UserGroups.objects.filter(Q(admin_user=user) | Q(user=user)).values_list('user__username',
                                                                                 flat=True).distinct())
    return HttpResponse(json.dumps({'sister_warehouses': sister_warehouses1}))


@csrf_exempt
@login_required
@get_admin_user
def print_po_reports(request, user=''):
    receipt_type = ''
    po_id = request.GET.get('po_id', '')
    user = User.objects.get(id=request.GET['warehouse_id'])
    po_summary_id = request.GET.get('po_summary_id', '')
    receipt_no = request.GET.get('receipt_no', '')
    st_grn = request.GET.get('st_grn', '')
    po_pre = request.GET.get('prefix', '')
    grn_num = request.GET.get('grn_number', '')
    utgst_tax , cess_tax , apmc_tax,measurement_unit = 0, 0, 0,''
    data_dict = ''
    bill_no = ''
    bill_date = ''
    sr_number = ''
    warehouse_store = ''
    # po_data = []
    headers = (
        'WMS CODE', 'Order Quantity', 'Received Quantity', 'Measurement', 'Unit Price', 'CSGT(%)', 'SGST(%)', 'IGST(%)',
        'UTGST(%)', 'Amount', 'Description')
    po_data = {headers: []}
    filter_params = {}
    oneassist_condition = get_misc_value('dispatch_qc_check', user.id)
    if st_grn:
        filter_params['stpurchaseorder__open_st__sku__user'] = user.id
    else:
        filter_params['open_po__sku__user'] = user.id
    if po_id:
        results = PurchaseOrder.objects.filter(order_id=po_id, prefix=po_pre, **filter_params)
        if receipt_no:
            results = results.distinct().filter(sellerposummary__receipt_number=receipt_no, sellerposummary__grn_number=grn_num)
    elif po_summary_id:
        results = SellerPOSummary.objects.filter(id=po_summary_id, purchase_order__open_po__sku__user=user.id)
    total = 0
    total_qty = 0
    total_tax = 0
    total_tax_value = 0
    tax_value = 0
    overall_discount = 0
    tcs_val = 0
    for data in results:
        receipt_type = ''
        lr_number = ''
        lr_number_obj = LRDetail.objects.filter(purchase_order_id=data.id, purchase_order__open_po__sku__user=user.id, purchase_order__prefix=data.prefix)
        if lr_number_obj.exists():
            lr_number = lr_number_obj[0].lr_number
        if po_id:
            quantity = data.received_quantity
            bill_date = data.updation_date
            if receipt_no:
                seller_summary_objs = data.sellerposummary_set.filter(receipt_number=receipt_no, grn_number=grn_num)
                if st_grn:
                    open_data = data.stpurchaseorder_set.filter()[0].open_st
                else:
                    open_data = data.open_po
                grouped_data = OrderedDict()
                if seller_summary_objs[0].overall_discount:
                    overall_discount = seller_summary_objs[0].overall_discount
                else:
                    overall_discount = 0
                for seller_summary_obj in seller_summary_objs:
                    quantity = seller_summary_obj.quantity
                    bill_no = seller_summary_obj.invoice_number if seller_summary_obj.invoice_number else ''
                    bill_date = seller_summary_obj.invoice_date if seller_summary_obj.invoice_date else data.updation_date
                    if seller_summary_obj.price:
                        price = seller_summary_obj.price
                    else:
                        price = open_data.price

                    cgst_tax = open_data.cgst_tax
                    sgst_tax = open_data.sgst_tax
                    igst_tax = open_data.igst_tax
                    if not st_grn:
                        utgst_tax = open_data.utgst_tax
                        cess_tax = open_data.cess_tax
                        apmc_tax = seller_summary_obj.apmc_tax
                    if seller_summary_obj.cess_tax:
                        cess_tax = seller_summary_obj.cess_tax
                    gst_tax = cgst_tax + sgst_tax + igst_tax + utgst_tax + cess_tax + apmc_tax
                    discount = seller_summary_obj.discount_percent
                    mrp = 0
                    if user.userprofile.user_type == 'warehouse_user':
                        mrp = open_data.sku.mrp
                    sku_batch_no, expiry_date = '', ''
                    if seller_summary_obj.batch_detail:
                        sku_batch_no = seller_summary_obj.batch_detail.batch_no
                        expiry_date = seller_summary_obj.batch_detail.expiry_date
                        if expiry_date:
                            expiry_date = datetime.datetime.strftime(expiry_date, '%d/%m/%Y')
                        else:
                            expiry_date = ''
                        price = seller_summary_obj.batch_detail.buy_price
                        mrp = seller_summary_obj.batch_detail.mrp
                        temp_tax_percent = seller_summary_obj.batch_detail.tax_percent
                        if not st_grn:
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
                    grouping_key = '%s:%s:%s' % (str(open_data.sku.sku_code), str(price), str(seller_summary_obj.batch_detail_id))
                    amount = float(quantity) * float(price)
                    if discount:
                        amount = amount - (amount * float(discount) / 100)
                    if gst_tax:
                        total_tax_value += (amount / 100) * gst_tax
                        amount += (amount / 100) * gst_tax
                    if not st_grn:
                        measurement_unit = open_data.measurement_unit
                    grouped_data.setdefault(grouping_key, {'wms_code': open_data.sku.wms_code,
                                                           'order_quantity': open_data.order_quantity,
                                                           'received_quantity': 0,
                                                           'measurement_unit': measurement_unit,
                                                           'price': price, 'cgst_tax': cgst_tax, 'sgst_tax': sgst_tax,
                                                           'igst_tax': igst_tax, 'utgst_tax': utgst_tax,
                                                           'amount': 0, 'sku_desc': open_data.sku.sku_desc,
                                                           'mrp': mrp, 'batch_no': sku_batch_no, 'exp_date':expiry_date})
                    grouped_data[grouping_key]['received_quantity'] += quantity
                    grouped_data[grouping_key]['amount'] += float("%.2f" % amount)
                    total += amount
                    total_qty += quantity
                    total_tax += gst_tax
                po_data[headers] = list(chain(po_data[headers], grouped_data.values()))
            else:
                open_data = data.open_po
                amount = float(quantity) * float(data.open_po.price)
                gst_tax = open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + open_data.utgst_tax + open_data.apmc_tax
                if gst_tax:
                    total_tax_value += (amount / 100) * gst_tax
                    amount += (amount / 100) * gst_tax
                mrp = open_data.mrp
                if user.userprofile.user_type == 'warehouse_user':
                    mrp = open_data.sku.mrp
                # po_data[headers].append((open_data.sku.wms_code, open_data.order_quantity, quantity,
                #                 open_data.measurement_unit,
                #                 open_data.price, open_data.cgst_tax, open_data.sgst_tax, open_data.igst_tax,
                #                 open_data.utgst_tax, amount, open_data.sku.sku_desc))
                po_data[headers].append({'wms_code': open_data.sku.wms_code, 'order_quantity': open_data.order_quantity,
                                         'received_quantity': quantity, 'measurement_unit': open_data.measurement_unit,
                                         'price': open_data.price, 'cgst_tax': open_data.cgst_tax,
                                         'sgst_tax': open_data.sgst_tax, 'igst_tax': open_data.igst_tax,
                                         'utgst_tax': open_data.utgst_tax, 'amount': float("%.2f" % amount),
                                         'sku_desc': open_data.sku.sku_desc, 'mrp': mrp})
                total += amount
                total_qty += quantity
                total_tax += (
                        open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + open_data.utgst_tax + open_data.cess_tax + open_data.apmc_tax)
        else:
            bill_date = data.invoice_date if data.invoice_date else data.creation_date
            bill_no = data.invoice_number if data.invoice_number else ''
            po_order = data.purchase_order
            open_data = po_order.open_po
            amount = float(data.quantity) * float(open_data.price)
            gst_tax = open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + open_data.utgst_tax
            if gst_tax:
                total_tax_value += (amount / 100) * gst_tax
                amount += (amount / 100) * gst_tax
            mrp = open_data.mrp
            if user.userprofile.user_type == 'warehouse_user':
                mrp = open_data.sku.mrp
            po_data[headers].append({'wms_code': open_data.sku.wms_code, 'order_quantity': open_data.order_quantity,
                                     'received_quantity': data.quantity, 'measurement_unit': open_data.measurement_unit,
                                     'price': open_data.price, 'cgst_tax': open_data.cgst_tax,
                                     'sgst_tax': open_data.sgst_tax,
                                     'igst_tax': open_data.igst_tax, 'utgst_tax': open_data.utgst_tax,
                                     'amount': float("%.2f" % amount), 'sku_desc': open_data.sku.sku_desc,
                                     'mrp': mrp})
            total += amount
            total_qty += po_order.received_quantity
            receipt_type = data.seller_po.receipt_type
            total_tax += (open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + open_data.utgst_tax)
    if results:
        purchase_order = results[0]
        if not po_id:
            purchase_order = results[0].purchase_order
        if st_grn:
            user_profile = UserProfile.objects.filter(user_id=purchase_order.stpurchaseorder_set.filter()[0].stocktransfer_set.filter()[0].sku.user)
            address = user_profile[0].address
            telephone = user_profile[0].phone_number
            name = user_profile[0].user.username
            supplier_id = user_profile[0].user.id
            tin_number = user_profile[0].gst_number

        else:
            address = purchase_order.open_po.supplier.address
            address = '\n'.join(address.split(','))
            telephone = purchase_order.open_po.supplier.phone_number
            name = purchase_order.open_po.supplier.name
            supplier_id = purchase_order.open_po.supplier.supplier_id
            tin_number = purchase_order.open_po.supplier.tin_number
        remarks = purchase_order.remarks
        order_id = purchase_order.order_id
        invoice_file_user = purchase_order.open_po.sku.user
        grn_numbers=results.values('sellerposummary__grn_number', 'sellerposummary__receipt_number').get()
        grn_number=grn_numbers["sellerposummary__grn_number"]
        grn_receipt_number = grn_numbers['sellerposummary__receipt_number']
        po_reference = '%s%s_%s' % (
            purchase_order.prefix, str(purchase_order.creation_date).split(' ')[0].replace('-', ''),
            purchase_order.order_id)
        grn_po_number = purchase_order.po_number
        warehouse_store = User.objects.get(id=purchase_order.open_po.sku.user).first_name
        if receipt_no:
            po_reference = '%s/%s' % (po_reference, receipt_no)
        if purchase_order.sellerposummary_set.filter().exists():
            tcs_val = purchase_order.sellerposummary_set.filter(grn_number=grn_number).order_by('-creation_date')[0].tcs_value
            seller_po_summary_date = purchase_order.sellerposummary_set.filter().order_by('-creation_date')[0].creation_date
            order_date = get_local_date(request.user, seller_po_summary_date)
        else:
            order_date = get_local_date(request.user, purchase_order.creation_date)
        order_date = datetime.datetime.strftime(datetime.datetime.strptime(order_date, "%d %b, %Y %I:%M %p"), "%d-%m-%Y")
        bill_date = datetime.datetime.strftime(bill_date, "%d-%m-%Y")
        user_profile = UserProfile.objects.get(user_id=user.id)
        w_address, company_address = get_purchase_company_address(user_profile)  # user_profile.address
        data_dict = (('Order ID', order_id), ('Supplier ID', supplier_id),
                     ('Order Date', order_date), ('Supplier Name', name), ('GST NO', tin_number))
    sku_list = po_data[po_data.keys()[0]]
    sku_slices = generate_grn_pagination(sku_list)
    table_headers = (
        'WMS CODE', 'Order Quantity', 'Received Quantity', 'Measurement', 'Unit Price', 'CSGT(%)', 'SGST(%)', 'IGST(%)',
        'UTGST(%)', 'Amount', 'Description')

    title = 'Purchase Order'
    # if receipt_type == 'Hosted Warehouse':
    #    title = 'Stock Transfer Note'
    net_amount = total - overall_discount
    net_amount = net_amount + float(tcs_val)
    if total:
        tax_value = (total * total_tax) / (100 + total_tax)
        tax_value = float("%.2f" % total_tax_value)
    try:
        url_request, invoice_file_name = "", ""
        invoice_data = MasterDocs.objects.filter(master_id=grn_po_number,
                                                     user=invoice_file_user,
                                                     extra_flag=grn_receipt_number)

        if invoice_data.exists():
            invoice_details = invoice_data[0].uploaded_file
            invoice_file_name = (invoice_data[0].uploaded_file.file.name).split('/')[-1]
            http_data = "%s%s%s" % (request.META.get('HTTP_HOST'), "/", invoice_details)
            url_request = '<button type="button" class="btn btn-success" style="min-width: 75px;height: 26px;padding: 2px 5px;" ng-click="showCase.FileDownload(' + http_data + ')" ">Download</button>'

    except IOError:
        pass
    return render(request, 'templates/toggle/c_putaway_toggle.html',
                  {'table_headers': table_headers, 'data': po_data, 'data_slices': sku_slices, 'address': address,
                   'order_id': order_id, 'telephone': str(telephone), 'name': name, 'order_date': order_date,
                   'total_price': float("%.2f" % total), 'data_dict': data_dict, 'bill_no': bill_no, 'tax_value': tax_value,
                   'po_number': grn_number, 'company_address': w_address, 'company_name': user_profile.company.company_name,
                   'display': 'display-none', 'receipt_type': receipt_type, 'title': title,'file_url':invoice_file_name,
                   'overall_discount': overall_discount, 'grn_po_number': grn_po_number, 'tcs_val':tcs_val,
                   'st_grn':st_grn, 'warehouse_store': warehouse_store, 'total_gross_value': float("%.2f" % total) - tax_value,
                   'total_received_qty': total_qty, 'bill_date': bill_date, 'total_tax': int(total_tax),
                   'net_amount': float("%.2f" % net_amount),
                   'company_address': company_address, 'sr_number': sr_number, 'lr_number': lr_number,
                   'remarks': remarks, 'show_mrp_grn': get_misc_value('show_mrp_grn', user.id)})

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
    admin_user = get_admin(user)
    excel_name = ''
    func_name = ''
    file_type = 'xls'
    tally_report = 0
    headers, search_params, filter_params = get_search_params(request, user)
    if '&' in request.POST['serialize_data']:
        form_data = request.POST['serialize_data'].split('&')
    else:
        form_data = request.POST['serialize_data'].split('<>')
    for dat in form_data:
        temp = dat.split('=')
        if 'excel_name' in dat:
            excel_name = dat
            if temp[1] == 'tally_report':
                temp[1] = 'order_summary_report'
            func_name = eval(EXCEL_REPORT_MAPPING[temp[1]])
            continue
        if len(temp) > 1 and temp[1]:
            temp[1] = str(temp[1]).replace('%26', '&')
            if 'date' in dat:
                if '%2F' in temp[1]:
                    temp[1] = temp[1].replace('%2F', '/')
                temp[1] = datetime.datetime.strptime(temp[1], '%m/%d/%Y')
            search_params[temp[0]] = temp[1]
    if 'tally_report' in excel_name:
        search_params['tally_report'] = True
        tally_report =1
    params = [search_params, user, request.user]
    if 'excel_name=goods_receipt' in excel_name:
        params = [request, search_params, user, request.user]
    if 'excel_name=integration_report' in excel_name:
        params = [request, search_params, user, request.user]
    if 'excel_name=pr_po_grn_dict' in excel_name:
        params = [request, search_params, user, request.user]
    if 'excel_name=sku_wise_goods_receipt' in excel_name:
        params = [request, search_params, user, request.user]
    if excel_name in ['excel_name=get_material_request_report', 'excel_name=get_stock_transfer_report', 'excel_name=get_stock_transfer_report_main']:
        params = [request, search_params, user, request.user]
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
    if temp[1] in ['order_summary_report'] or 'tally_report' in excel_name:
        headers.extend(["Billing Address" ,"Shipping Address"])
        headers.extend(["Payment Cash", "Payment Card","Payment PhonePe","Payment GooglePay","Payment Paytm"])
        if search_params.get('tally_report'):
            headers = ['Voucher Type', 'Invoice Number','Invoice Date','Party Name','Address1','Address2','Address3','State Name',
                        'GSTIN','Main Location','Stock item','Qty','Rate','Disc%','Discount Amount','Sales Ledger',
                        'Sgst Ledger','SGST Amt','CGST Ledger','CGST Amount','Igst Ledger','IGST Amount','Invoice Amount',
                        'Part Number','Unit','Group','MRP','Selling price(inc Tax)','Cost price (Inc Tax)','HSN Code','GST']
        extra_fields_obj = MiscDetail.objects.filter(user=user.id, misc_type__icontains="pos_extra_fields")
        for field in extra_fields_obj:
            tmp = field.misc_value.split(',')
            for i in tmp:
                headers.append(str(i))
    if temp[1] in ['expired_stock_data'] and len(report_data['aaData']) > 0:
        headers = report_data['aaData'][0].keys()
    if temp[1] in ['get_credit_note_form_report'] and len(report_data['aaData']) > 0:
            squareBracketCols = ['**Supplier', '*Supplier Site', 'Legal Entity Name', 'Prepayment Number',
                'Liability Distribution', 'Context Value', 'Additional Information', 'Regional Context Value ',
                'Regional Information ', 'Purchase Order', 'Purchase Order Line', 'Purchase Order Schedule',
                'Purchase Order Distribution', 'Receipt', 'Receipt Line', 'Consumption Advice',
                'Consumption Advice Line Number', 'Distribution Combination', 'Distribution Set', 'Ship-to Location',
                'Ship-from Location', 'Location of Final Discharge', 'Context Value_1', 'Additional Information_1',
                'Project Information', 'Multiperiod Accounting Accrual Account'
                ]
            report_data['New_aaData'] = []
            sortedData = OrderedDict()
            for row in report_data['aaData']:
                ordList = []
                for k, v in row.items():
                    if k in squareBracketCols:
                        ordList.append((k+'[..]', v),)
                    else:
                        ordList.append((k, v),)
                sortedData.setdefault(row['*Invoice Header Identifier'], []).append(OrderedDict(ordList))
                #report_data['New_aaData'].append(OrderedDict(ordList))
            #report_data['aaData'] = report_data['New_aaData']
            for k, v in sortedData.items():
                if len(v) > 1:
                    for x in v:
                        report_data['New_aaData'].append(x)
                else:
                    report_data['New_aaData'].append(v[0])
            report_data['aaData'] = report_data['New_aaData']
            headers = report_data['aaData'][0].keys()
    if temp[1] in ['expired_stock_data'] and len(report_data['aaData']) > 0:
        headers = report_data['aaData'][0].keys()
    excel_data = print_excel(request, report_data, headers, excel_name, file_type=file_type, tally_report=tally_report)
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
def get_material_request_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_material_request_report_data(request, search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_stock_transfer_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_stock_transfer_report_data(request, search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_stock_transfer_report_main(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_stock_transfer_report_data_main(request, search_params, user, request.user)
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
def get_pr_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_pr_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_pr_detail_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_pr_detail_report_data(search_params, user, request.user)

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


def format_printing_datam(datum, order, purchase_order, wms_code, supplier_code, measurement_unit, table_headers, display_remarks, show_cess_tax, show_apmc_tax):
    amount = 0
    delivery_date = ''
    if order.currency_rate > 1:
        current_price = round(float(purchase_order.price) / order.currency_rate, 2)
    else:
        current_price = float(purchase_order.price)
    amount = float(datum.quantity) * current_price
    amount = float("%.2f" % amount)
    total_tax_amt = (purchase_order.utgst_tax + purchase_order.sgst_tax + purchase_order.cgst_tax + purchase_order.igst_tax + purchase_order.cess_tax + purchase_order.apmc_tax + purchase_order.utgst_tax) * (amount/100)
    total_sgst = purchase_order.sgst_tax * (amount/100)
    total_cgst = purchase_order.cgst_tax * (amount/100)
    total_igst = purchase_order.igst_tax * (amount/100)
    total_tax_amt = float("%.2f" % total_tax_amt)
    total_sku_amt = total_tax_amt + amount
    try:
        delivery_date = datetime.datetime.strftime(datum.delivery_date, '%d-%m-%Y')
    except Exception as e:
        pass
    po_temp_data = [wms_code, purchase_order.sku.hsn_code, supplier_code, purchase_order.sku.sku_desc, delivery_date, float(datum.quantity),
                measurement_unit,
                current_price, round(purchase_order.mrp/ order.currency_rate, 2), amount, purchase_order.sgst_tax, total_sgst, purchase_order.cgst_tax, total_cgst,
                purchase_order.igst_tax, total_igst,
                total_sku_amt
                ]
    if show_cess_tax:
        po_temp_data.insert(table_headers.index('CESS (%)'), purchase_order.cess_tax)
    if show_apmc_tax:
        po_temp_data.insert(table_headers.index('APMC (%)'), purchase_order.apmc_tax)
    if display_remarks == 'true':
        po_temp_data.append(purchase_order.remarks)
    return po_temp_data


@csrf_exempt
@login_required
@get_admin_user
def print_purchase_order_form(request, user=''):
    po_id = request.GET.get('po_id', '')
    po_prefix = request.GET.get('prefix', '')
    po_num= request.GET.get('po_number', '')
    total_qty = 0
    total = 0
    remarks = ''
    pending_po_line_entries = ''
    if not po_id:
        return HttpResponse("Purchase Order Id is missing")
    sub_user= request.user
    users=[user.id]
    if sub_user.is_staff and user.userprofile.warehouse_type == 'ADMIN':
        users = get_related_users_filters(user.id)
    else:
        users = check_and_get_plants_wo_request(sub_user, user, users)
    purchase_orders = PurchaseOrder.objects.filter(open_po__sku__user__in=users, order_id=po_id, prefix=po_prefix, po_number=po_num).exclude(status='deleted')
    supplier_currency, supplier_payment_terms, delivery_date = '', '', ''
    if purchase_orders.exists():
        pm_order = purchase_orders[0]
        po_user_id= purchase_orders[0].open_po.sku.user
        if po_user_id:
            user=User.objects.get(id=po_user_id)
        if PendingPO.objects.filter(full_po_number=pm_order.po_number).exists():
            pending_po_data = PendingPO.objects.filter(full_po_number=pm_order.po_number)[0]
            #remarks = pending_po_data.remarks
            if pending_po_data.pending_polineItems.filter().exists():
                pending_po_line_entries=pending_po_data.pending_polineItems.filter()
            if pending_po_data.supplier_payment:
                supplier_payment_terms = pending_po_data.supplier_payment.payment_description
            delivery_date = pending_po_data.delivery_date.strftime('%d-%m-%Y')
        if pm_order.open_po.supplier.currency_code:
            supplier_currency = pm_order.open_po.supplier.currency_code
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
        table_headers = ['SKU Code', 'HSN Code', 'Supplier Code', 'Desc', 'Delivery Schedule', 'Qty', 'UOM', 'Unit Price', 'MRP', 'Amt',
                         'SGST (%)', 'SGST Amt', 'CGST (%)', 'CGST Amt', 'IGST (%)', 'IGST Amt', 'Total']
        if user.username in MILKBASKET_USERS:
            table_headers.insert(4, 'Weight')
    else:
        table_headers = ['SKU Code', 'HSN Code', 'Supplier Code', 'Desc', 'Delivery Schedule', 'Qty', 'UOM', 'Unit Price', 'Amt',
                         'SGST (%)', 'SGST Amt', 'CGST (%)', 'CGST Amt', 'IGST (%)', 'IGST Amt', 'Total']
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
        remarks = order.remarks
        total_qty += open_po.order_quantity
        if order.currency_rate > 1:
            currency_rate = round(open_po.price / order.currency_rate, 2)
        else:
            currency_rate = open_po.price
        amount = open_po.order_quantity * currency_rate
        tax = open_po.cgst_tax + open_po.sgst_tax + open_po.igst_tax + open_po.utgst_tax + open_po.cess_tax + open_po.apmc_tax
        total += amount + ((amount / 100) * float(tax))
        if user.userprofile.industry_type == 'FMCG':
            po_temp_data = []
            if pending_po_line_entries:
                sku_pending_line = pending_po_line_entries.filter(sku__sku_code=open_po.sku.sku_code)
                if sku_pending_line.exists():
                    delivery_schedule_data = sku_pending_line[0].purchasedeliveryschedule_set.filter(status=1)
                    for delivery_data in delivery_schedule_data:
                        po_temp_data = format_printing_datam(delivery_data, order, open_po, open_po.sku.sku_code, open_po.supplier_code, open_po.measurement_unit, table_headers, display_remarks, show_cess_tax, show_apmc_tax)
                        po_data.append(po_temp_data)
            if not po_temp_data:
                total_tax_amt = (open_po.utgst_tax + open_po.sgst_tax + open_po.cgst_tax + open_po.igst_tax + open_po.cess_tax
                         + open_po.utgst_tax + open_po.apmc_tax) * (amount / 100)
                total_sgst = open_po.sgst_tax * (amount/100)
                total_cgst = open_po.cgst_tax * (amount/100)
                total_igst = open_po.igst_tax * (amount/100)
                total_tax_amt = float("%.2f" % total_tax_amt)
                total_sku_amt = total_tax_amt + amount
                po_temp_data = [open_po.sku.sku_code, open_po.sku.hsn_code,open_po.supplier_code, open_po.sku.sku_desc, '',
                            open_po.order_quantity, open_po.measurement_unit, currency_rate, round(open_po.mrp/order.currency_rate, 2), amount,
                            open_po.sgst_tax, total_sgst, open_po.cgst_tax, total_cgst, open_po.igst_tax, total_igst, total_sku_amt]
                po_data.append(po_temp_data)

        else:
            total_tax_amt = (open_po.utgst_tax + open_po.sgst_tax + open_po.cgst_tax + open_po.igst_tax + open_po.cess_tax
                         + open_po.utgst_tax + open_po.apmc_tax) * (amount / 100)
            total_sgst = open_po.sgst_tax * (amount/100)
            total_cgst = open_po.cgst_tax * (amount/100)
            total_igst = open_po.igst_tax * (amount/100)
            total_tax_amt = float("%.2f" % total_tax_amt)
            total_sku_amt = total_tax_amt + amount
            po_temp_data = [open_po.sku.sku_code, open_po.supplier_code, open_po.sku.sku_desc, '',
                            open_po.order_quantity, open_po.measurement_unit, currency_rate, amount,
                            open_po.sgst_tax, open_po.cgst_tax, open_po.igst_tax,
                            open_po.utgst_tax, total_sku_amt]

            if show_cess_tax:
                po_temp_data.insert(table_headers.index('CESS (%)'), open_po.cess_tax)
            if show_apmc_tax:
                po_temp_data.insert(table_headers.index('APMC (%)'), open_po.apmc_tax)
            if display_remarks == 'true':
                po_temp_data.append(open_po.remarks)
            po_data.append(po_temp_data)
        # if ean_flag:
        #     ean_number = ''
        #     eans = get_sku_ean_list(open_po.sku)
        #     if eans:
        #         ean_number = eans[0]
        #     po_temp_data.insert(1, ean_number)
                # if show_cess_tax:
        #     po_temp_data.insert(table_headers.index('CESS (%)'), open_po.cess_tax)
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
    code = open_po.supplier.supplier_id
    order_id = order.order_id
    gstin_no = open_po.supplier.tin_number
    if open_po:
        address = open_po.supplier.address
        address = '\n'.join(address.split(','))
        if open_po.ship_to and  get_utc_start_date(datetime.datetime.strptime('2021-02-12', '%Y-%m-%d')) < open_po.creation_date:
            ship_to_address = open_po.ship_to
            if user.userprofile.wh_address:
                company_address = user.userprofile.wh_address
            else:
                company_address = user.userprofile.address
        else:
            ship_to_address, company_address = get_purchase_company_address(user.userprofile)
        if not ship_to_address:
            wh_ship_to = UserAddresses.objects.filter(address_type = 'Shipment Address', user=user.id).order_by('creation_date')
            if wh_ship_to.exists():
                wh_ship_to = wh_ship_to[0]
                ship_to_address = "%s - %s" % (wh_ship_to.address, wh_ship_to.pincode)
        # ship_to_address = '\n'.join(ship_to_address.split(','))
        telephone = open_po.supplier.phone_number
        name = open_po.supplier.name
        code = open_po.supplier.supplier_id
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
    po_number = order.po_number #'%s%s_%s' % (order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order_id)
    po_reference = order.open_po.po_name
    total_amt_in_words = str(supplier_currency) + ' '+ number_in_words(round(total)) + ' ONLY'
    round_value = float(round(total) - float(total))
    profile = user.userprofile
    company_name = profile.company.company_name
    title = 'Purchase Order'
    receipt_type = request.GET.get('receipt_type', '')
    company_details = {}
    company_logo=""
    if profile.company.logo:
        try:
            _logo_url = profile.company.logo.url.replace('/static/', 'static/')
            _logo_url =  urllib.url2pathname(_logo_url)
            with open(_logo_url, "rb") as image_file:
                company_logo = base64.b64encode(image_file.read())
        except:
            company_logo = 'http://' + request.get_host() +'/'+ profile.company.logo.url
    if profile.company:
        company_details['company_address'] = ''
        if profile.company.address:
            company_details['company_address'] = profile.company.address.encode('ascii', 'ignore')
        company_details['phone'] = profile.company.phone_number
        company_details['email'] = profile.company.email_id
        company_details['gstin_number'] = profile.company.gstin_number
        company_details['cin_number'] = profile.company.cin_number
        company_details['pan_number'] = profile.company.pan_number
    left_side_logo = get_po_company_logo(user, LEFT_SIDE_COMPNAY_LOGO, request)
    user_company_id = get_company_id(user)
    tc_master = UserTextFields.objects.filter(company_id=user_company_id, field_type='terms_conditions')
    if tc_master.exists():
        terms_condition = tc_master[0].text_field
    if open_po.supplier.lead_time:
        lead_time_days = open_po.supplier.lead_time
        replace_date = get_local_date(request.user,
                                      open_po.creation_date + datetime.timedelta(days=int(lead_time_days)),
                                      send_date='true')
        date_replace_terms = replace_date.strftime("%d-%m-%Y")
        terms_condition = terms_condition.replace("%^PO_DATE^%", date_replace_terms)
    else:
        terms_condition = terms_condition.replace("%^PO_DATE^%", '')
    # if receipt_type == 'Hosted Warehouse':
    # if request.POST.get('seller_id', ''):
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
        'code': code,
        'remarks': remarks,
        'order_date': order_date,
        'total': round(total),
        'total_qty': total_qty,
        'vendor_name': vendor_name,
        'vendor_address': vendor_address,
        'vendor_telephone': vendor_telephone,
        'gstin_no': gstin_no,
        'w_address': ship_to_address,  # get_purchase_company_address(profile),
        'ship_to_address': ship_to_address,
        'wh_telephone': wh_telephone,
        'wh_gstin': profile.gst_number,
        'terms_condition': terms_condition,
        'total_amt_in_words': total_amt_in_words,
        'show_cess_tax': show_cess_tax,
        'company_name': profile.company.company_name,
        'location': profile.location,
        'po_reference': po_reference,
        'po_number': po_number,
        'industry_type': profile.industry_type,
        'left_side_logo': left_side_logo,
        'company_details': company_details,
        'company_logo': company_logo,
        'supplier_currency': supplier_currency,
        'delivery_date': delivery_date,
        'supplier_payment_terms': supplier_payment_terms,
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
def print_descrepancy_note(request, user=''):
    from inbound_descrepancy import generate_discrepancy_data
    disp_number = request.GET.get('discrepancy_number', '')
    po_new_data = OrderedDict()
    updated_discrepancy = False
    profile = UserProfile.objects.get(user=user.id)
    report_data_dict ={}
    if disp_number:
        discrepancy_objects = Discrepancy.objects.filter(user=user.id, discrepancy_number=disp_number)
        for obj in discrepancy_objects:
            if obj.purchase_order:
                open_po = obj.purchase_order.open_po
                filter_params = {'purchase_order__order_id': obj.purchase_order.order_id, 'purchase_order__open_po__sku__user': user.id}
                if obj.receipt_number:
                    filter_params['receipt_number'] = obj.receipt_number
                seller_po_summary = SellerPOSummary.objects.filter(**filter_params)
                price = obj.purchase_order.open_po.price
                mrp = 0
                if seller_po_summary.exists():
                    seller_po_obj = seller_po_summary[0]
                    if seller_po_obj.batch_detail:
                        price = seller_po_obj.batch_detail.buy_price
                        mrp = seller_po_obj.batch_detail.mrp
                if not updated_discrepancy:
                    updated_discrepancy = True
                    invoice_number, invoice_date = '', ''
                    order_date = obj.purchase_order.creation_date
                    if seller_po_summary.exists():
                        invoice_number = seller_po_summary[0].invoice_number
                        invoice_date =  seller_po_summary[0].invoice_date.strftime('%d/%m/%y')
                        order_date = seller_po_summary[0].creation_date
                    supplier = obj.purchase_order.open_po.supplier
                    order_date = get_local_date(request.user, order_date)
                    order_date = datetime.datetime.strftime(
                        datetime.datetime.strptime(order_date, "%d %b, %Y %I:%M %p"), "%d-%m-%Y")
                    if not invoice_number and obj.new_data:
                        data_dict = json.loads(obj.new_data)
                        invoice_number = data_dict.get('invoice_number', '')
                        invoice_date = data_dict.get('invoice_date', '')
                    report_data_dict = {'supplier_id':supplier.id, 'address':supplier.address,
                                        'supplier_name':supplier.name, 'supplier_gst':supplier.tin_number,
                                        'company_name': profile.company_name, 'company_address': profile.address,
                                        'po_number': obj.po_number, 'bill_no': invoice_number,'full_discrepancy_number':disp_number,
                                        'order_date': order_date, 'bill_date': invoice_date,
                                        }

                cond = ('', open_po.sku.wms_code, '', price, open_po.cgst_tax, open_po.sgst_tax, open_po.igst_tax,
                        '', open_po.sku.sku_desc, 0, 0, 0, 0, mrp)
                po_new_data.setdefault(cond, {'discrepency_quantity': 0,
                                              'discrepency_reason': ''})
                po_new_data[cond]['discrepency_quantity'] += obj.quantity
                po_new_data[cond]['discrepency_reason'] = obj.return_reason
            else:
                data_dict =json.loads(obj.new_data)
                cond = ('', data_dict['wms_code'], '', data_dict['price'], data_dict['cgst_tax'], data_dict['sgst_tax'], data_dict['igst_tax'],
                        '', data_dict['sku_desc'], 0, 0, 0, 0, data_dict['mrp'])
                po_new_data.setdefault(cond, {'discrepency_quantity': 0,
                                              'discrepency_reason': ''})
                po_new_data[cond]['discrepency_quantity'] += obj.quantity
                po_new_data[cond]['discrepency_reason'] = obj.return_reason
        discrepency_rendered = generate_discrepancy_data(user, po_new_data, print_des=True, **report_data_dict)
        return HttpResponse(discrepency_rendered)

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


@csrf_exempt
@login_required
@get_admin_user
def get_basa_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_basa_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_discrepancy_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_discrepancy_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_move_inventory_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_move_inventory_report_data(search_params, user, request.user)
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


@get_admin_user
def print_margin_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_margin_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@get_admin_user
def print_basa_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_basa_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)


@csrf_exempt
@login_required
@get_admin_user
def get_credit_note_form_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_credit_note_form_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_cancel_invoice_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_cancel_invoice_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_credit_note_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_credit_note_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def reprint_credit_note_report(request, user=''):
    html_data = {}
    search_parameters = {}
    headers, search_params, filter_params = get_search_params(request)
    report_data = get_credit_note_report_data(search_params, user, request.user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

@login_required
@get_admin_user
def print_credit_note_report(request, user=''):
    from inbound import get_sales_return_print_json
    credit_note_number = request.GET.get('credit_note_number')
    return_ids = list(OrderReturns.objects.filter(order__user=user.id, credit_note_number=credit_note_number)\
        .values_list('return_id', flat=True))
    final_data = get_sales_return_print_json(return_ids, user)
    return_sales_print = []
    return_sales_print.append(final_data)

    return render(request, 'templates/toggle/sales_return_print.html',
                  {'show_data_invoice': return_sales_print})

@csrf_exempt
@login_required
@get_admin_user
def get_approval_summary_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_approval_summary_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_approval_detail_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_approval_detail_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_metro_po_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_metro_po_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_metropolis_po_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_metropolis_po_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_metro_po_detail_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_metro_po_detail_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_metropolis_po_detail_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_metropolis_po_detail_report_data(search_params, user, request.user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_cancel_grn_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_cancel_grn_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_sku_wise_cancel_grn_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_sku_wise_cancel_grn_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_sku_wise_consumption_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_sku_wise_consumption_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def get_consumption_data(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_consumption_data_(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_closing_stock_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_closing_stock_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_praod_report(request, user=''):
    headers, search_params, filter_params = get_search_params(request)
    temp_data = get_praod_report_data(search_params, user, request.user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


def download_invoice_file(request, user=''):
    receipt_type, http_data = '', ''
    po_id = request.GET.get('po_id', '')
    user = User.objects.get(id=request.GET['warehouse_id'])
    po_summary_id = request.GET.get('po_summary_id', '')
    receipt_no = request.GET.get('receipt_no', '')
    st_grn = request.GET.get('st_grn', '')
    po_pre = request.GET.get('prefix', '')
    po_number = request.GET.get('po_number', '')
    grn_num = request.GET.get('grn_number', '')
    warehouse_id = request.GET.get('warehouse_id', '')
    if po_id:
        results = PurchaseOrder.objects.filter(po_number=po_number, open_po__sku__user=user.id)
        if receipt_no:
            results = results.distinct().filter(sellerposummary__receipt_number=receipt_no, sellerposummary__grn_number=grn_num)
            if results:
                purchase_order = results[0]
                order_id = purchase_order.order_id
                invoice_file_user = purchase_order.open_po.sku.user
                grn_numbers = results.values('sellerposummary__grn_number', 'sellerposummary__receipt_number', 'po_number').get()
                grn_number = grn_numbers["sellerposummary__grn_number"]
                grn_receipt_number = grn_numbers['sellerposummary__receipt_number']
                grn_po_number = purchase_order.po_number
                try:
                    url_request, invoice_file_name = "", ""
                    invoice_data = MasterDocs.objects.filter(master_id=po_number,
                                                             master_type='GRN_PO_NUMBER',
                                                             extra_flag=grn_receipt_number).order_by('-creation_date')
                    if not invoice_data:
                        invoice_data = MasterDocs.objects.filter(master_id=po_id,
                                                                 user=invoice_file_user,
                                                                 extra_flag=grn_receipt_number).order_by('-creation_date')

                    if invoice_data.exists():
                        if len(invoice_data) > 1:
                            files_list=list(invoice_data.values_list('uploaded_file', flat=True))
                            http_data = json.dumps(files_list)
                        else:
                            invoice_details = invoice_data[0].uploaded_file.url
                            http_data = invoice_details

                except IOError:
                    pass
    return HttpResponse(http_data)
