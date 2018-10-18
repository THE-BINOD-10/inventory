from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import os
import json, ast
from django.db.models import Q, F
from itertools import chain
from collections import OrderedDict
from django.contrib.auth import authenticate
from django.contrib import auth
from django.db.models.query import QuerySet
from miebach_admin.models import *
from miebach_utils import *
from mail_server import send_mail, send_mail_attachment
from django.core import serializers
from django.template import loader, Context
import dicttoxml
from operator import itemgetter
from common import *
from xmljson import badgerfish as bf
from xml.etree.ElementTree import fromstring
from sync_sku import insert_skus
from utils import *

log = init_logger('logs/inbound.log')

NOW = datetime.datetime.now()


def get_filtered_params(filters, data_list):
    filter_params = {}
    for key, value in filters.iteritems():
        col_num = int(key.split('_')[-1])
        if value:
            filter_params[data_list[col_num] + '__icontains'] = value
    return filter_params


@csrf_exempt
def get_po_suggestions(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['supplier__id', 'supplier__id', 'supplier__name', 'total', 'order_type']

    search_params = get_filtered_params(filters, lis[1:])
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    search_params['sku_id__in'] = sku_master_ids

    if search_term:
        results = OpenPO.objects.exclude(status=0).values('supplier_id', 'supplier__name', 'supplier__tax_type',
                                                          'order_type').distinct().annotate(
            total=Sum('order_quantity')). \
            filter(Q(supplier__id__icontains=search_term) | Q(supplier__name__icontains=search_term) |
                   Q(total__icontains=search_term), sku__user=user.id, **search_params).order_by(order_data)

    elif order_term:
        results = OpenPO.objects.exclude(status=0).values('supplier_id', 'supplier__name', 'supplier__tax_type',
                                                          'order_type').distinct().annotate(
            total=Sum('order_quantity')). \
            filter(sku__user=user.id, **search_params).order_by(order_data)
    else:
        results = OpenPO.objects.exclude(status=0).values('supplier_id', 'supplier__name', 'supplier__tax_type',
                                                          'order_type').distinct().annotate(
            total=Sum('order_quantity')). \
            filter(sku__user=user.id, **search_params)

    temp_data['recordsTotal'] = results.count()
    temp_data['recordsFiltered'] = results.count()

    count = 0
    status_dict = PO_ORDER_TYPES
    for result in results[start_index: stop_index]:
        order_type = status_dict[result['order_type']]
        # if order_type in PO_RECEIPT_TYPES.keys():
        #    order_type = PO_RECEIPT_TYPES.get(order_type, '')
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (result['supplier_id'], result['supplier__name'])
        temp_data['aaData'].append(OrderedDict((('', checkbox), ('Supplier ID', result['supplier_id']),
                                                ('Supplier Name', result['supplier__name']),
                                                ('Tax Type', result['supplier__tax_type']),
                                                ('Total Quantity', result['total']),
                                                ('Order Type', order_type), ('id', count),
                                                ('DT_RowClass', 'results'))))
        count += 1


@csrf_exempt
def get_raised_stock_transfer(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              filters=''):
    lis = ['warehouse__username', 'total']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if order_term:
        master_data = OpenST.objects.filter(sku__user=user.id, status=1).values('warehouse__username'). \
            annotate(total=Sum('order_quantity')).order_by(order_data).distinct()
    if search_term:
        master_data = OpenST.objects.filter(
            Q(warehouse__username__icontains=search_term) | Q(order_quantity__icontains=search_term),
            sku__user=user.id, status=1).values('warehouse__username'). \
            annotate(total=Sum('order_quantity')).order_by(order_data).distinct()
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append(
            {'Warehouse Name': data['warehouse__username'], 'Total Quantity': data['total'], 'DT_RowClass': 'results',
             'DT_RowAttr': {'id': data['warehouse__username']}})


def get_intransit_orders(start_index, stop_index, temp_data, search_term, order_term, col_num,
                             request, user, filters):
    lis = ['sku__sku_code', 'quantity', 'invoice_amount']
    order_data = lis[col_num]
    if user.userprofile.warehouse_type == 'CENTRAL_ADMIN':
        filter_dict = {'status': 1}
        values_list = ['id', 'sku__sku_code', 'quantity', 'invoice_amount', 'customer_id']
    else:
        filter_dict = {'customer_id': user.id, 'status': 1}
        values_list = ['id', 'sku__sku_code', 'quantity', 'invoice_amount']
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if order_term:
        master_data = IntransitOrders.objects.filter(**filter_dict).\
            values(*values_list).annotate(total=Sum('invoice_amount')).order_by(order_data).distinct()
    if search_term:
        master_data = IntransitOrders.objects.filter(
            Q(sku__sku_code__icontains=search_term) | Q(quantity__icontains=search_term),
            **filter_dict).values('warehouse__username'). \
            annotate(total=Sum('invoice_amount')).order_by(order_data).distinct()
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    temp_data['min_order_val'] = user.userprofile.min_order_val
    for data in master_data[start_index:stop_index]:
        cust_id = data.get('customer_id', '')
        if cust_id:
            user_obj = UserProfile.objects.get(user=cust_id)
            username = user_obj.user.username
            min_order_val = user_obj.min_order_val
        else:
            username = ''
            min_order_val = 0
        data_dict = {'SKU': data['sku__sku_code'], 'Quantity': data['quantity'], 'Amount': data['invoice_amount'],
             'Total Quantity': data['total'], 'DT_RowClass': 'results',
             'DT_RowAttr': {'id': data['id']}}
        if username and min_order_val:
            data_dict['Distributor Name'] = username
            data_dict['Minimum Order Value'] = min_order_val
        temp_data['aaData'].append(data_dict)


def get_receive_po_datatable_filters(user, filters, request):
    search_params = {}
    search_params1 = {}
    search_params2 = {}
    if filters['search_0']:
        cols = re.findall('\d+', filters['search_0'])
        string = re.findall('\D+', filters['search_0'])
        if string:
            if len(cols) == 1:
                param_date = cols[0]
                if len(param_date) > 4:
                    param_date = list(param_date)
                    param_date.insert(4, '-')
                    param_date = ''.join(param_date)
                if len(param_date) > 7:
                    param_date = list(param_date)
                    param_date.insert(7, '-')
                    param_date = ''.join(param_date)
                search_params['creation_date__regex'] = param_date

            elif len(cols) == 2:
                search_params['order_id__icontains'] = cols[1]
                search_params1['po__order_id__icontains'] = cols[1]
            if string:
                search_params['prefix__icontains'] = string[0]
        else:
            col_val = re.findall('\d+', filters['search_0'])[0]
            po_ids = PurchaseOrder.objects.filter(Q(order_id__icontains=col_val) | Q(creation_date__regex=col_val),
                                                  open_po__sku__user=user.id,
                                                  received_quantity__lt=F('open_po__order_quantity')). \
                exclude(status__in=['location-assigned', 'confirmed-putaway']). \
                values_list('id', flat=True)
            stock_results = STPurchaseOrder.objects.exclude(po__open_po__isnull=True).exclude(
                po__status__in=['location-assigned',
                                'confirmed-putaway', 'stock-transfer']). \
                filter(Q(po__order_id__icontains=col_val) | Q(creation_date__regex=col_val),
                       open_st__sku__user=user.id,
                       po__received_quantity__lt=F('open_st__order_quantity')). \
                values_list('po_id', flat=True).distinct()
            rw_results = RWPurchase.objects.exclude(purchase_order__open_po__isnull=True). \
                exclude(purchase_order__status__in=['location-assigned', 'confirmed-putaway', 'stock-transfer']). \
                filter(Q(purchase_order__order_id__icontains=col_val) | Q(creation_date__regex=col_val),
                       rwo__vendor__user=user.id,
                       purchase_order__received_quantity__lt=F('rwo__job_order__product_quantity')). \
                values_list('purchase_order_id', flat=True).distinct()
            search_params['id__in'] = list(chain(po_ids, stock_results, rw_results))
            search_params1['po_id__in'] = search_params['id__in']
    if filters['search_1']:
        search_params['open_po__po_name__icontains'] = filters['search_1']
        search_params1['po__open_po__po_name__icontains'] = filters['search_1']
        search_params2['purchase_order__open_po__po_name__icontains'] = filters['search_1']
    if filters['search_3']:
        search_params['creation_date__regex'] = filters['search_3']
    if request.POST.get('style_view', '') == 'true':
        supplier_search = 'search_10'
    else:
        supplier_search = 'search_9'
    if filters[supplier_search]:
        search_params['open_po__supplier__id__icontains'] = filters[supplier_search]
        search_params1['open_st__warehouse__id__icontains'] = filters[supplier_search]
        search_params2['rwo__vendor__id__icontains'] = filters[supplier_search]
    if filters['search_3']:
        search_params['open_po__supplier__name__icontains'] = filters['search_3']
        search_params1['open_st__warehouse__username__icontains'] = filters['search_3']
        search_params2['rwo__vendor__name__icontains'] = filters['search_3']
    '''
    if search_params:
        search_params['open_po__sku__user'] = user.id
        search_params1['open_st__sku__user'] = user.id
        results = PurchaseOrder.objects.filter(**search_params).exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                        values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__open_po__isnull=True).exclude(po__status__in=['location-assigned',
                                                        'confirmed-putaway', 'stock-transfer']).\
                                                filter(po__received_quantity__lt=F('open_st__order_quantity'), **search_params1).values_list('po__order_id', flat=True).distinct()
        results = list(chain(results, stock_results))'''

    return search_params, search_params1, search_params2


def get_filtered_purchase_order_ids(request, user, search_term, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    purchase_order_list = ['open_po__supplier__id', 'open_po__supplier__name', 'order_id',
                           'creation_date', 'open_po__po_name']
    st_purchase_list = ['open_st__warehouse__id', 'open_st__warehouse__username', 'po__order_id', 'po__creation_date']
    rw_purchase_list = ['rwo__vendor__id', 'rwo__vendor__name', 'purchase_order__creation_date',
                        'purchase_order__order_id']

    purchase_order_query = build_search_term_query(purchase_order_list, search_term)
    st_search_query = build_search_term_query(st_purchase_list, search_term)
    rw_purchase_query = build_search_term_query(rw_purchase_list, search_term)

    search_params, search_params1, search_params2 = get_receive_po_datatable_filters(user, filters, request)

    # Stock Transfer Purchase Records
    stock_results_objs = STPurchaseOrder.objects.exclude(po__status__in=['location-assigned', 'confirmed-putaway',
                                                                         'stock-transfer']).filter(
        open_st__sku_id__in=sku_master_ids). \
        filter(st_search_query, po__open_po__isnull=True,
               open_st__sku__user=user.id, **search_params1)
    order_qtys_dict = dict(stock_results_objs.values_list('po__order_id'). \
                           annotate(total_order_qty=Sum('open_st__order_quantity')))
    receive_qtys_dict = dict(stock_results_objs.values_list('po__order_id'). \
                             annotate(total_received_qty=Sum('po__received_quantity')))
    st_order_ids_list = stock_results_objs.filter(po__received_quantity__lt=F('open_st__order_quantity')). \
        values_list('po__order_id', flat=True).distinct()
    rw_results_objs = RWPurchase.objects.exclude(purchase_order__status__in=['location-assigned', 'confirmed-putaway',
                                                                             'stock-transfer']). \
        filter(purchase_order__open_po__isnull=True, rwo__job_order__product_code_id__in=sku_master_ids,
               **search_params2).filter(rw_purchase_query, rwo__vendor__user=user.id)
    order_qtys_dict.update(dict(rw_results_objs.values_list('purchase_order__order_id').distinct(). \
                                annotate(total_order_qty=Sum('rwo__job_order__product_quantity'))))
    receive_qtys_dict.update(dict(rw_results_objs.values_list('purchase_order__order_id').distinct(). \
                                  annotate(total_received_qty=Sum('purchase_order__received_quantity'))))
    rw_order_ids_list = rw_results_objs.filter(
        purchase_order__received_quantity__lt=F('rwo__job_order__product_quantity')). \
        values_list('purchase_order__order_id', flat=True).distinct()

    results_objs = PurchaseOrder.objects.filter(open_po__sku_id__in=sku_master_ids).filter(**search_params). \
        filter(purchase_order_query, open_po__sku__user=user.id)

    order_qtys_dict.update(dict(results_objs.values_list('order_id').distinct(). \
                                annotate(total_order_qty=Sum('open_po__order_quantity'))))
    receive_qtys_dict.update(dict(results_objs.values_list('order_id').distinct(). \
                                  annotate(total_received_qty=Sum('received_quantity'))))

    po_order_ids_list = results_objs.exclude(status__in=['location-assigned', 'confirmed-putaway']). \
        filter(received_quantity__lt=F('open_po__order_quantity')).values_list('order_id',
                                                                               flat=True).distinct()
    results = list(set((chain(po_order_ids_list, rw_order_ids_list, st_order_ids_list))))
    return results, order_qtys_dict, receive_qtys_dict

@csrf_exempt
def get_confirmed_po(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    # sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['PO No', 'PO No', 'PO Reference', 'Customer Name', 'Order Date', 'Expected Date',
           'Total Qty', 'Receivable Qty', 'Received Qty',
           'Remarks', 'Supplier ID/Name', 'Order Type', 'Receive Status']
    data_list = []
    data = []
    supplier_data = {}
    col_num1 = 0
    po_reference_no = ''
    supplier_status, supplier_user, supplier, supplier_parent = get_supplier_info(request)
    if supplier_status:
        request.user.id = supplier.user
        user.id = supplier.user
        filters['search_9'] = supplier.id
    results, order_qtys_dict, receive_qtys_dict = get_filtered_purchase_order_ids(request, user, search_term, filters)

    for result in results:
        suppliers = PurchaseOrder.objects.filter(order_id=result, open_po__sku__user=user.id).exclude(
            status__in=['location-assigned', 'confirmed-putaway'])
        if not suppliers:
            st_order_ids = STPurchaseOrder.objects.filter(po__order_id=result, open_st__sku__user=user.id).values_list(
                'po_id', flat=True)
            suppliers = PurchaseOrder.objects.filter(id__in=st_order_ids)
        if not suppliers:
            rw_ids = RWPurchase.objects.filter(purchase_order__order_id=result, rwo__vendor__user=user.id). \
                values_list('purchase_order_id', flat=True)
            suppliers = PurchaseOrder.objects.filter(id__in=rw_ids)
        for supplier in suppliers[:1]:
            data.append(supplier)

    temp_data['recordsTotal'] = len(data)
    temp_data['recordsFiltered'] = len(data)

    for supplier in data:
        order_type = 'Purchase Order'
        receive_status = 'Yet To Receive'
        order_data = get_purchase_order_data(supplier)
        if supplier.open_po and supplier.open_po.order_type == 'VR':
            order_type = 'Vendor Receipt'
        if supplier.rwpurchase_set.filter():
            order_type = 'Returnable Work Order'
        elif supplier.stpurchaseorder_set.filter():
            order_type = 'Stock Transfer'
        po_reference = '%s%s_%s' % (
        supplier.prefix, str(supplier.creation_date).split(' ')[0].replace('-', ''), supplier.order_id)
        _date = get_local_date(user, supplier.po_date, True)
        _date = _date.strftime("%d %b, %Y")
        supplier_id_name = '%s/%s' % (str(xcode(order_data['supplier_id'])), str(xcode(order_data['supplier_name'])))

        columns = ['PO No', 'PO Reference', 'Order Date', 'Supplier ID/Name', 'Total Qty', 'Receivable Qty', 'Received Qty',
                   'Expected Date', 'Remarks', 'Order Type', 'Receive Status']

        total_order_qty = order_qtys_dict.get(supplier.order_id, 0)
        total_received_qty = receive_qtys_dict.get(supplier.order_id, 0)
        total_receivable_qty = total_order_qty - total_received_qty
        if total_received_qty:
            receive_status = 'Partially Receive'
        expected_date = ''
        if supplier.expected_date:
            expected_date = supplier.expected_date.strftime("%d %b, %Y")
        customer_data = OrderMapping.objects.filter(mapping_id=supplier.id, mapping_type='PO')
        customer_name = ''
        if customer_data:
            customer_name = customer_data[0].order.customer_name
        else:
            if supplier_parent:
                customer_name = supplier_parent.username
        if supplier.open_po:
            po_reference_no = supplier.open_po.po_name
        data_list.append(OrderedDict((('DT_RowId', supplier.order_id), ('PO No', po_reference),
                                      ('PO Reference', po_reference_no), ('Order Date', _date),
                                      ('Supplier ID/Name', supplier_id_name), ('Total Qty', total_order_qty),
                                      ('Receivable Qty', total_receivable_qty),
                                      ('Received Qty', total_received_qty), ('Expected Date', expected_date),
                                      ('Remarks', supplier.remarks), ('Order Type', order_type),
                                      ('Receive Status', receive_status), ('Customer Name', customer_name),
                                      ('Style Name', '')
                                      )))
    sort_col = lis[col_num]

    if order_term == 'asc':
        data_list = sorted(data_list, key=itemgetter(sort_col))
    else:
        data_list = sorted(data_list, key=itemgetter(sort_col), reverse=True)
    temp_data['aaData'] = list(chain(temp_data['aaData'], data_list[start_index:stop_index]))


@csrf_exempt
def get_quality_check_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                           filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['Purchase Order ID', 'Supplier ID', 'Supplier Name', 'Order Type', 'Total Quantity']
    all_data = OrderedDict()

    qc_list = ['purchase_order__order_id', 'purchase_order__open_po__supplier__id',
               'purchase_order__open_po__supplier__name',
               'id', 'putaway_quantity']
    st_list = ['po__order_id', 'open_st__warehouse__id', 'open_st__warehouse__username', 'id', 'id']
    rw_list = ['purchase_order__order_id', 'rwo__vendor__id', 'rwo__vendor__name', 'id', 'id']

    del filters['search_3']
    del filters['search_4']
    qc_filters = get_filtered_params(filters, qc_list)
    st_filters = get_filtered_params(filters, st_list)
    rw_filters = get_filtered_params(filters, rw_list)

    if search_term:
        results = QualityCheck.objects.filter(purchase_order__open_po__sku_id__in=sku_master_ids). \
            filter(Q(purchase_order__order_id__icontains=search_term) |
                   Q(purchase_order__open_po__supplier__id__icontains=search_term) |
                   Q(purchase_order__open_po__supplier__name__icontains=search_term),
                   purchase_order__open_po__sku__user=user.id, status='qc_pending', putaway_quantity__gt=0,
                   **qc_filters)
        stock_results = STPurchaseOrder.objects.filter(open_st__sku_id__in=sku_master_ids). \
            exclude(po__status__in=['confirmed-putaway', 'stock-transfer']). \
            filter(Q(open_st__warehouse__username__icontains=search_term) |
                   Q(po__order_id__icontains=search_term), open_st__sku__user=user.id, **st_filters). \
            values_list('po_id', flat=True)
        rw_results = RWPurchase.objects.filter(rwo__job_order__product_code_id__in=sku_master_ids). \
            exclude(purchase_order__status__in=['confirmed-putaway', 'stock-transfer']). \
            filter(Q(rwo__vendor__name__icontains=search_term) | Q(rwo__vendor__id__icontains=search_term) |
                   Q(purchase_order__order_id__icontains=search_term), rwo__vendor__user=user.id, **rw_filters). \
            values_list('purchase_order_id', flat=True)
        stock_results = list(chain(stock_results, rw_results))
        result_ids = results.values_list('id', flat=True)
        qc_results = QualityCheck.objects.exclude(id__in=result_ids).filter(purchase_order_id__in=stock_results,
                                                                            status='qc_pending',
                                                                            putaway_quantity__gt=0,
                                                                            po_location__location__zone__user=user.id)

        results = list(chain(results, qc_results))
    else:
        stock_results = STPurchaseOrder.objects.filter(open_st__sku_id__in=sku_master_ids).exclude(
            po__status__in=['confirmed-putaway',
                            'stock-transfer']).filter(open_st__sku__user=user.id, **st_filters). \
            values_list('po_id', flat=True)
        rw_results = RWPurchase.objects.filter(rwo__job_order__product_code_id__in=sku_master_ids). \
            exclude(purchase_order__status__in=['confirmed-putaway', 'stock-transfer']). \
            filter(rwo__vendor__user=user.id, **rw_filters). \
            values_list('purchase_order_id', flat=True)
        stock_results = list(chain(stock_results, rw_results))
        qc_results = QualityCheck.objects.filter(
            Q(purchase_order__open_po__sku_id__in=sku_master_ids) | Q(purchase_order_id__in=stock_results),
            status='qc_pending', putaway_quantity__gt=0, po_location__location__zone__user=user.id)
        qc_result_ids = qc_results.values_list('id', flat=True)
        results = QualityCheck.objects.filter(
            Q(purchase_order__open_po__sku_id__in=sku_master_ids) | Q(purchase_order_id__in=stock_results)). \
            filter(status='qc_pending', putaway_quantity__gt=0, po_location__location__zone__user=user.id,
                   **qc_filters).exclude(id__in=qc_result_ids)
        results = list(chain(results, qc_results))

    for result in results:
        p_data = get_purchase_order_data(result.purchase_order)
        cond = (result.purchase_order.order_id, p_data['supplier_id'], p_data['supplier_name'])
        all_data.setdefault(cond, 0)
        all_data[cond] += result.putaway_quantity

    temp_data['recordsTotal'] = len(all_data)
    temp_data['recordsFiltered'] = len(all_data)
    for key, value in all_data.iteritems():
        order = PurchaseOrder.objects.filter(order_id=key[0], open_po__sku__user=user.id,
                                             open_po__sku_id__in=sku_master_ids)
        if not order:
            order = STPurchaseOrder.objects.filter(po_id__order_id=key[0], open_st__sku__user=user.id,
                                                   open_st__sku_id__in=sku_master_ids)
            if order:
                order = [order[0].po]
            else:
                order = [RWPurchase.objects.filter(purchase_order__order_id=key[0], rwo__vendor__user=user.id,
                                                   rwo__job_order__product_code_id__in=sku_master_ids)[
                             0].purchase_order]
        order = order[0]
        order_type = 'Purchase Order'
        if RWPurchase.objects.filter(purchase_order_id=order.id):
            order_type = 'Returnable Work Order'
        elif STPurchaseOrder.objects.filter(po_id=order.id):
            order_type = 'Stock Transfer'
        po_reference = '%s%s_%s' % (
        order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order.order_id)
        temp_data['aaData'].append({'DT_RowId': key[0], 'Purchase Order ID': po_reference, 'Supplier ID': key[1],
                                    'Supplier Name': key[2], 'Order Type': order_type, 'Total Quantity': value})

    sort_col = lis[col_num]
    if order_term == 'asc':
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
    else:
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


@csrf_exempt
def get_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    supplier_data = {}
    lis = ['PO Number', 'Order Date', 'Supplier ID', 'Supplier Name', 'Order Type']
    po_lis = ['order_id', 'order_id', 'open_po__supplier_id', 'open_po__supplier__name', 'order_id']
    st_lis = ['order_id', 'order_id', 'stpurchaseorder__open_st__warehouse_id',
              'stpurchaseorder__open_st__warehouse__username', 'order_id']
    rw_lis = ['order_id', 'order_id', 'rwpurchase__rwo__vendor_id', 'rwpurchase__rwo__vendor__name', 'order_id']
    po_col = po_lis[col_num]
    st_col = st_lis[col_num]
    rw_col = rw_lis[col_num]
    if order_term == 'desc':
        po_col = '-%s' % po_col
        st_col = '-%s' % st_col
        rw_col = '-%s' % rw_col
    purchase_order_objs = PurchaseOrder.objects.filter(Q(open_po__sku__user=user.id, open_po__sku_id__in=sku_master_ids) |
                                               Q(stpurchaseorder__open_st__sku__user=user.id,
                                                 stpurchaseorder__open_st__sku_id__in=sku_master_ids) |
                                               Q(rwpurchase__rwo__job_order__product_code_id__in=sku_master_ids,
                                                 rwpurchase__rwo__vendor__user=user.id), polocation__status=1,
                                                       polocation__quantity__gt=0).\
            exclude(status__in=['', 'confirmed-putaway', 'stock-transfer'])
    if search_term:
        results = purchase_order_objs.filter(Q(open_po__supplier__name__icontains=search_term) |
            Q(open_po__supplier__id__icontains=search_term) | Q(order_id__icontains=search_term) |
            Q(creation_date__regex=search_term) | Q(stpurchaseorder__open_st__warehouse__id__icontains=search_term) |
            Q(stpurchaseorder__open_st__warehouse__username__icontains=search_term) |
            Q(rwpurchase__rwo__vendor__id__icontains=search_term) |
            Q(rwpurchase__rwo__vendor__name__icontains=search_term)).values(
            'order_id').distinct().order_by(po_col, st_col, rw_col)
    else:
        results = purchase_order_objs.values('order_id').\
            distinct().order_by(po_col, st_col, rw_col)

    temp_data['recordsTotal'] = results.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if lis[col_num] == 'Order Type':
        custom_sort = True
    else:
        custom_sort = False
        results = results[start_index:stop_index]
    for result in results:
        purchase_orders = purchase_order_objs.filter(order_id=result['order_id'])
        supplier = purchase_orders[0]
        order_data = get_purchase_order_data(supplier)
        order_type = 'Purchase Order'

        if not supplier.open_po:
            if supplier.rwpurchase_set.filter():
                order_type = 'Returnable Work Order'
            elif supplier.stpurchaseorder_set.filter():
                order_type = 'Stock Transfer'
        po_reference = '%s%s_%s' % (
        supplier.prefix, str(supplier.creation_date).split(' ')[0].replace('-', ''), supplier.order_id)
        temp_data['aaData'].append({'DT_RowId': supplier.order_id, 'Supplier ID': order_data['supplier_id'],
                                    'Supplier Name': order_data['supplier_name'], 'Order Type': order_type,
                                    ' Order ID': supplier.order_id,
                                    'Order Date': get_local_date(request.user, supplier.creation_date),
                                    'DT_RowClass': 'results', 'PO Number': po_reference,
                                    'DT_RowAttr': {'data-id': supplier.order_id}})

    if custom_sort:
        order_data = lis[col_num]
        if order_term == 'asc':
            temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(order_data))
        else:
            temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(order_data), reverse=True)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


@csrf_exempt
def get_order_returns_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['returns__return_id', 'returns__return_date', 'returns__sku__wms_code', 'returns__sku__sku_desc',
           'location__zone__zone', 'location__location', 'quantity']
    if search_term:
        master_data = ReturnsLocation.objects.filter(returns__sku_id__in=sku_master_ids).filter(
            Q(returns__return_id__icontains=search_term) |
            Q(returns__sku__sku_desc__icontains=search_term) |
            Q(returns__sku__wms_code__icontains=search_term) | Q(quantity__icontains=search_term),
            returns__sku__user=user.id, status=1, quantity__gt=0)
    elif order_term:
        col_num = col_num - 1
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = ReturnsLocation.objects.filter(returns__sku__user=user.id, status=1, quantity__gt=0,
                                                     returns__sku_id__in=sku_master_ids).order_by(order_data)
    else:
        master_data = ReturnsLocation.objects.filter(returns__sku__user=user.id, status=1, quantity__gt=0,
                                                     returns__sku_id__in=sku_master_ids).order_by(
            'returns__return_date')
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    count = 0;
    for data in master_data[start_index:stop_index]:
        order_id = ''
        if data.returns.order:
            order_id = data.returns.order.id
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data.id, order_id)
        zone = data.location.zone.zone
        location = data.location.location
        quantity = data.quantity
        temp_data['aaData'].append({'': checkbox, 'Return ID': data.returns.return_id,
                                    'Return Date': get_local_date(request.user, data.returns.return_date),
                                    'WMS Code': data.returns.sku.wms_code,
                                    'Product Description': data.returns.sku.sku_desc, 'Zone': zone,
                                    'Location': location,
                                    'Quantity': quantity, 'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.id},
                                    'id': count})
        count = count + 1


@csrf_exempt
def get_order_returns(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['return_id', 'order_id', 'return_date', 'order__sku__sku_code', 'order__sku__sku_desc', 'order__marketplace',
           'quantity']
    if search_term:
        order_id_search = ''.join(re.findall('\d+', search_term))
        master_data = OrderReturns.objects.filter(
            Q(return_id__icontains=search_term) | Q(quantity__icontains=search_term) |
            Q(order__sku__sku_code=search_term) | Q(order__sku__sku_desc__icontains=search_term) |
            Q(order__order_id__icontains=order_id_search), status=1, order__user=user.id, quantity__gt=0)
    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            master_data = OrderReturns.objects.filter(order__user=user.id, status=1, quantity__gt=0).order_by(
                lis[col_num])
        else:
            master_data = OrderReturns.objects.filter(order__user=user.id, status=1, quantity__gt=0).order_by(
                '-%s' % lis[col_num])
    else:
        master_data = OrderReturns.objects.filter(order__user=user.id, status=1).order_by('return_date')
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data in master_data[start_index:stop_index]:
        ord_id = ''
        if data.order and data.order.original_order_id:
            ord_id = data.order.original_order_id
        elif data.order:
            ord_id = str(data.order.order_code) + str(data.order.order_id)

        temp_data['aaData'].append({'Return ID': data.return_id, 'Order ID': ord_id,
                                    'Return Date': get_local_date(user, data.return_date),
                                    'SKU Code': data.order.sku.sku_code, 'Product Description': data.order.sku.sku_desc,
                                    'Market Place': data.order.marketplace, 'Quantity': data.quantity})


@csrf_exempt
def get_seller_invoice_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                            filters):
    lis = ['seller_po__open_po_id', 'seller_po__open_po_id', 'seller_po__seller__name', 'creation_date',
           'seller_po__seller_quantity', 'quantity', 'id']
    seller_po_summary = SellerPOSummary.objects.filter(seller_po__seller__user=user.id).exclude(
        seller_po__receipt_type='Hosted Warehouse')
    if search_term:
        order_id_search = ''
        if '_' in search_term:
            order_id_search = ''.join(re.findall('\d+', search_term.split('_')[-1]))
        open_po_ids = []
        if order_id_search:
            open_po_ids = PurchaseOrder.objects.filter(open_po__sku__user=user.id, order_id__icontains=order_id_search). \
                values_list('open_po__id', flat=True)
        master_data = seller_po_summary.filter(Q(quantity__icontains=search_term) |
                                               Q(seller_po__seller__name__icontains=search_term) |
                                               Q(seller_po__seller_quantity__icontains=search_term) |
                                               Q(seller_po__open_po_id__in=open_po_ids),
                                               seller_po__seller__user=user.id).values('purchase_order__order_id',
                                                                                       'receipt_number',
                                                                                       'seller_po__seller__name').distinct(). \
            annotate(total_quantity=Sum('quantity'))
    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            master_data = seller_po_summary.order_by(lis[col_num]).values('purchase_order__order_id',
                                                                          'seller_po__seller__name',
                                                                          'receipt_number').distinct().annotate(
                total_quantity=Sum('quantity'))
        else:
            master_data = seller_po_summary.order_by('-%s' % lis[col_num]).values('purchase_order__order_id',
                                                                                  'seller_po__seller__name',
                                                                                  'receipt_number').distinct().annotate(
                total_quantity=Sum('quantity'))
    else:
        master_data = seller_po_summary.order_by('-%s' % lis[col_num]).values('purchase_order__order_id',
                                                                              'seller_po__seller__name',
                                                                              'receipt_number').distinct().annotate(
            total_quantity=Sum('quantity'))

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    po_summaries = seller_po_summary
    for data in master_data[start_index:stop_index]:
        summary = po_summaries.filter(purchase_order__order_id=data['purchase_order__order_id'],
                                      seller_po__seller__name=data['seller_po__seller__name'])[0]
        purchase_order = PurchaseOrder.objects.get(open_po_id=summary.seller_po.open_po_id)
        po_number = '%s%s_%s' % (
        purchase_order.prefix, str(purchase_order.creation_date).split(' ')[0].replace('-', ''),
        purchase_order.order_id)
        temp_data['aaData'].append(
            OrderedDict((('PO Number', po_number), ('Seller Name', summary.seller_po.seller.name),
                         ('Receipt Date', get_local_date(user, summary.creation_date)),
                         ('Order Quantity', summary.seller_po.seller_quantity),
                         ('Received Quantity', data['total_quantity']),
                         ('Invoice Number', ''), ('id', str(data['purchase_order__order_id']) + \
                                                  ":" + str(data['receipt_number']) + ":" + data[
                                                      'seller_po__seller__name'])
                         )))


@csrf_exempt
@login_required
@get_admin_user
def generated_po_data(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    status_dict = {'Self Receipt': 'SR', 'Vendor Receipt': 'VR'}
    receipt_type = ''
    generated_id = request.GET['supplier_id']
    order_type_val = request.GET['order_type']
    rev_order_types = dict(zip(PO_ORDER_TYPES.values(), PO_ORDER_TYPES.keys()))
    # if order_type_val in PO_RECEIPT_TYPES.values():
    #    rev_receipt_types = dict(zip(PO_RECEIPT_TYPES.values(), PO_RECEIPT_TYPES.keys()))
    #    order_type_val = rev_receipt_types.get(order_type_val, '')
    order_type = rev_order_types.get(order_type_val, '')
    record = OpenPO.objects.filter(
        Q(supplier_id=generated_id, status='Manual') | Q(supplier_id=generated_id, status='Automated'),
        sku__user=user.id, order_type=order_type, sku_id__in=sku_master_ids)

    total_data = []
    status_dict = PO_ORDER_TYPES
    ser_data = []
    terms_condition = ''
    for rec in record:
        seller = ''
        terms_condition = rec.terms
        seller_po = SellerPO.objects.filter(open_po__sku__user=user.id, open_po_id=rec.id)
        if seller_po:
            for sell_po in seller_po:
                if not receipt_type:
                    receipt_type = sell_po.receipt_type
                ser_data.append({'fields': {'sku': {'wms_code': rec.sku.sku_code}, 'description': rec.sku.sku_desc,
                                            'order_quantity': sell_po.seller_quantity,
                                            'price': rec.price, 'mrp': rec.mrp, 'supplier_code': rec.supplier_code,
                                            'measurement_unit': rec.measurement_unit,
                                            'remarks': rec.remarks, 'dedicated_seller': str(
                        sell_po.seller.seller_id) + ':' + sell_po.seller.name,
                                            'sgst_tax': rec.sgst_tax, 'cgst_tax': rec.cgst_tax,
                                            'igst_tax': rec.igst_tax, 'cess_tax': rec.cess_tax, 'utgst_tax': rec.utgst_tax},
                                 'pk': rec.id, 'seller_po_id': sell_po.id})
        else:
            ser_data.append({'fields': {'sku': {'wms_code': rec.sku.sku_code}, 'description': rec.sku.sku_desc,
                                        'order_quantity': rec.order_quantity,
                                        'price': rec.price, 'mrp': rec.mrp, 'supplier_code': rec.supplier_code,
                                        'measurement_unit': rec.measurement_unit,
                                        'remarks': rec.remarks, 'dedicated_seller': '', 'sgst_tax': rec.sgst_tax,
                                        'cgst_tax': rec.cgst_tax,
                                        'igst_tax': rec.igst_tax, 'cess_tax': rec.cess_tax, 'utgst_tax': rec.utgst_tax}, 'pk': rec.id})
    vendor_id = ''
    po_delivery_date = ''
    if len(record):
        if record[0].vendor:
            vendor_id = record[0].vendor.vendor_id
        if record[0].delivery_date:
            po_delivery_date = record[0].delivery_date.strftime('%m/%d/%Y')
    return HttpResponse(json.dumps({'supplier_id': record[0].supplier_id, 'supplier_name': record[0].supplier.name,
                                    'vendor_id': vendor_id,
                                    'Order Type': status_dict[record[0].order_type], 'po_name': record[0].po_name,
                                    'ship_to': record[0].ship_to, 'po_delivery_date': po_delivery_date,
                                    'data': ser_data, 'receipt_type': receipt_type, 'receipt_types': PO_RECEIPT_TYPES,
                                    'terms_condition' : terms_condition}))


@login_required
@get_admin_user
def validate_wms(request, user=''):
    myDict = dict(request.POST.iterlists())
    wms_list = ''
    tax_list = []
    receipt_type = request.POST.get('receipt_type', '')
    supplier_master = SupplierMaster.objects.filter(id=myDict['supplier_id'][0], user=user.id)
    if not supplier_master and not receipt_type == 'Hosted Warehouse':
        return HttpResponse("Invalid Supplier " + myDict['supplier_id'][0])
    if myDict.get('vendor_id', ''):
        vendor_master = VendorMaster.objects.filter(vendor_id=myDict['vendor_id'][0], user=user.id)
        if not vendor_master:
            return HttpResponse("Invalid Vendor " + myDict['vendor_id'][0])
    for i in range(0, len(myDict['wms_code'])):
        if not myDict['wms_code'][i]:
            continue
        if myDict['wms_code'][i].isdigit():
            sku_master = SKUMaster.objects.filter(
                Q(ean_number=myDict['wms_code'][i]) | Q(wms_code=myDict['wms_code'][i]), user=user.id)
        else:
            sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user=user.id)
        if not sku_master:
            if not wms_list:
                wms_list = 'Invalid WMS Codes are ' + myDict['wms_code'][i].upper()
            else:
                wms_list += ',' + myDict['wms_code'][i].upper()
        if 'cgst_tax' in myDict.keys():
            try:
                cgst_tax = float(myDict['cgst_tax'][i])
            except:
                cgst_tax = 0
            try:
                igst_tax = float(myDict['igst_tax'][i])
            except:
                igst_tax = 0
            if cgst_tax and igst_tax:
                tax_list.append(myDict['wms_code'][i])

    message = 'success'
    if wms_list:
        message = wms_list
    if tax_list:
        tax_list = 'Multiple Taxes mentioned for SKU Code %s' % (', '.join(tax_list))
        if message == 'success':
            message = tax_list
        else:
            message = '%s and %s' % (message, tax_list)
    return HttpResponse(message)


@csrf_exempt
@login_required
@get_admin_user
def modify_po_update(request, user=''):
    myDict = dict(request.POST.iterlists())
    terms_condition = request.POST.get('terms_condition','')
    wrong_wms = []
    all_data = get_raisepo_group_data(user, myDict)
    for key, value in all_data.iteritems():
        wms_code = key
        if not wms_code:
            continue
        data_id = value['data_id']
        if data_id:
            record = OpenPO.objects.get(id=data_id, sku__user=user.id)
            setattr(record, 'order_quantity', value['order_quantity'])
            setattr(record, 'price', value['price'])
            setattr(record, 'mrp', value['mrp'])
            setattr(record, 'remarks', value['remarks'])
            setattr(record, 'sgst_tax', value['sgst_tax'])
            setattr(record, 'cgst_tax', value['cgst_tax'])
            setattr(record, 'igst_tax', value['igst_tax'])
            setattr(record, 'cess_tax', value['cess_tax'])
            setattr(record, 'utgst_tax', value['utgst_tax'])
            setattr(record, 'ship_to', value['ship_to'])
            setattr(record, 'terms', terms_condition)
            if value['po_delivery_date']:
                setattr(record, 'delivery_date', value['po_delivery_date'])
            if record.mrp:
                setattr(record, 'mrp', value['mrp'])
            record.save()
            if value['sellers']:
                for k, val in value['sellers'].iteritems():
                    if val[1]:
                        seller_po = SellerPO.objects.get(id=val[1], open_po__sku__user=user.id)
                        seller_po.seller_quantity = val[0]
                        seller_po.save()
                    else:
                        SellerPO.objects.create(seller_id=k, open_po_id=record.id, seller_quantity=val[0],
                                                creation_date=datetime.datetime.now(), status=1,
                                                receipt_type=value['receipt_type'])
            continue

        sku_id = SKUMaster.objects.filter(wms_code=wms_code.upper(), user=user.id)
        po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
        if not sku_id:
            sku_id = sku_id = SKUMaster.objects.filter(wms_code='TEMP', user=user.id)
            po_suggestions['wms_code'] = wms_code.upper()
        if not sku_id[0].wms_code == 'TEMP':
            supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=myDict['supplier_id'][0],
                                                          sku__user=user.id)
            sku_mapping = {'supplier_id': value['supplier_id'], 'sku': sku_id[0], 'preference': 1, 'moq': 0,
                           'supplier_code': value['supplier_code'], 'price': value['price'],
                           'creation_date': datetime.datetime.now(),
                           'updation_date': datetime.datetime.now()}
            if supplier_mapping:
                supplier_mapping = supplier_mapping[0]
                if sku_mapping['supplier_code'] and supplier_mapping.supplier_code != sku_mapping['supplier_code']:
                    supplier_mapping.supplier_code = sku_mapping['supplier_code']
                    supplier_mapping.save()
            else:
                new_mapping = SKUSupplier(**sku_mapping)
                new_mapping.save()
        po_suggestions['sku_id'] = sku_id[0].id
        po_suggestions['supplier_id'] = value['supplier_id']
        po_suggestions['order_quantity'] = value['order_quantity']
        if not value['price']:
            value['price'] = 0
        po_suggestions['price'] = float(value['price'])
        if not value['mrp']:
            value['mrp'] = 0
        po_suggestions['mrp'] = float(value['mrp'])
        po_suggestions['status'] = 'Manual'
        po_suggestions['remarks'] = value['remarks']
        po_suggestions['sgst_tax'] = value['sgst_tax']
        po_suggestions['cgst_tax'] = value['cgst_tax']
        po_suggestions['igst_tax'] = value['igst_tax']
        po_suggestions['cess_tax'] = value['cess_tax']
        po_suggestions['utgst_tax'] = value['utgst_tax']
        po_suggestions['ship_to'] = value['ship_to']
        if value['po_delivery_date']:
            po_suggestions['delivery_date'] = value['po_delivery_date']
        data = OpenPO(**po_suggestions)
        data.save()
        if value['sellers']:
            for seller, seller_quan in value['sellers'].iteritems():
                SellerPO.objects.create(seller_id=seller, open_po_id=data.id, seller_quantity=seller_quan[0],
                                        creation_date=datetime.datetime.now(), status=1,
                                        receipt_type=value['receipt_type'])
    if all_data and user.username == 'bluecatpaper':
        t = loader.get_template('templates/save_po_data.html')
        data_dict = {'sku_data' : dict(all_data), 'sku_ids' : all_data.keys(), 'headers' : ['SKU Code', 'Qty', 'Unit Price'], 'supplier_name' : request.POST['supplier_id_name'].split(':')[1]}
        rendered = t.render(data_dict)
        email = user.email
        if email:
            send_mail([email], 'BluecatPaper Saved PO Details', rendered)
    return HttpResponse("Updated Successfully")

@csrf_exempt
@get_admin_user
def switches(request, user=''):
    
    log.info('Request params for ' + user.username + ' on ' + str(
        get_local_date(user, datetime.datetime.now())) + ' is ' + str(request.GET.dict()))
    try:
        toggle_data = {'fifo_switch': 'fifo_switch',
                       'batch_switch': 'batch_switch',
                       'send_message': 'send_message',
                       'show_image': 'show_image',
                       'back_order': 'back_order',
                       'online_percentage': 'online_percentage',
                       'use_imei': 'use_imei',
                       'pallet_switch': 'pallet_switch',
                       'production_switch': 'production_switch',
                       'mail_alerts': 'mail_alerts',
                       'invoice_prefix': 'invoice_prefix',
                       'pos_switch': 'pos_switch',
                       'auto_po_switch': 'auto_po_switch',
                       'no_stock_switch': 'no_stock_switch',
                       'float_switch': 'float_switch',
                       'automate_invoice': 'automate_invoice',
                       'show_mrp': 'show_mrp',
                       'decimal_limit': 'decimal_limit',
                       'picklist_sort_by': 'picklist_sort_by',
                       'stock_sync': 'stock_sync',
                       'sku_sync': 'sku_sync',
                       'auto_generate_picklist': 'auto_generate_picklist',
                       'order_headers': 'order_headers',
                       'detailed_invoice': 'detailed_invoice',
                       'scan_picklist_option': 'scan_picklist_option',
                       'stock_display_warehouse': 'stock_display_warehouse',
                       'view_order_status': 'view_order_status',
                       'style_headers': 'style_headers',
                       'seller_margin': 'seller_margin',
                       'receive_process': 'receive_process',
                       'tally_config': 'tally_config',
                       'tax_details': 'tax_details',
                       'hsn_summary': 'hsn_summary',
                       'display_customer_sku': 'display_customer_sku',
                       'label_generation': 'label_generation',
                       'marketplace_model': 'marketplace_model',
                       'barcode_generate_opt': 'barcode_generate_opt',
                       'grn_scan_option': 'grn_scan_option',
                       'invoice_titles': 'invoice_titles',
                       'show_imei_invoice': 'show_imei_invoice',
                       'priceband_sync': 'priceband_sync',
                       'display_remarks_mail': 'display_remarks_mail',
                       'create_seller_order': 'create_seller_order',
                       'invoice_remarks': 'invoice_remarks',
                       'show_disc_invoice': 'show_disc_invoice',
                       'serial_limit': 'serial_limit',
                       'increment_invoice': 'increment_invoice',
                       'create_shipment_type': 'create_shipment_type',
                       'dashboard_order_level': 'dashboard_order_level',
                       'auto_allocate_stock': 'auto_allocate_stock',
                       'generic_wh_level': 'generic_wh_level',
                       'auto_confirm_po': 'auto_confirm_po',
                       'customer_pdf_remarks': 'customer_pdf_remarks',
                       'tax_inclusive' : 'tax_inclusive',
                       'create_order_po': 'create_order_po',
                       'calculate_customer_price': 'calculate_customer_price',
                       'shipment_sku_scan': 'shipment_sku_scan',
                       'extra_view_order_status':'extra_view_order_status',
                       'disable_brands_view':'disable_brands_view',
                       'invoice_types': 'invoice_types',
                       'sellable_segregation': 'sellable_segregation',
                       'display_styles_price': 'display_styles_price',
                       'picklist_display_address': 'picklist_display_address',
                       'shelf_life_ratio': 'shelf_life_ratio',
                       'mode_of_transport': 'mode_of_transport',
                       'show_purchase_history': 'show_purchase_history',
                       'display_sku_cust_mapping': 'display_sku_cust_mapping',
                       'disable_categories_view': 'disable_categories_view',
                       'is_portal_lite': 'is_portal_lite',
                       'auto_raise_stock_transfer': 'auto_raise_stock_transfer',
                       'inbound_supplier_invoice': 'inbound_supplier_invoice',
                       'invoice_based_payment_tracker': 'invoice_based_payment_tracker',
                       'customer_dc': 'customer_dc',
                       'auto_expire_enq_limit': 'auto_expire_enq_limit',
                       'sales_return_reasons': 'sales_return_reasons',
                       'central_order_mgmt': 'central_order_mgmt',
                       'receive_po_invoice_check': 'receive_po_invoice_check',
                       'mark_as_delivered': 'mark_as_delivered',
                       'order_exceed_stock': 'order_exceed_stock',
                       'receive_po_mandatory_fields': 'receive_po_mandatory_fields'
                       }
        toggle_field, selection = "", ""
        for key, value in request.GET.iteritems():
            toggle_field = toggle_data.get(key, '')
            selection = value
        user_id = user.id
        if toggle_field == 'invoice_prefix':
            user_profile = UserProfile.objects.filter(user_id=user_id)
            if user_profile and selection:
                setattr(user_profile[0], 'prefix', selection)
                user_profile[0].save()
        else:
            if toggle_field == 'tax_details':
                tax_name = eval(selection)
                toggle_field = tax_name.keys()[0]
                selection = tax_name[toggle_field]
            data = MiscDetail.objects.filter(misc_type=toggle_field, user=user_id)
            if not data:
                misc_detail = MiscDetail(user=user_id, misc_type=toggle_field, misc_value=selection,
                                         creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now())
                misc_detail.save()
            else:
                setattr(data[0], 'misc_value', selection)
                data[0].save()
            if toggle_field == 'sku_sync' and value == 'true':
                insert_skus(user.id)
            elif toggle_field == 'increment_invoice' and value == 'true':
                InvoiceSequence.objects.get_or_create(user_id=user.id, marketplace='',
                                                      defaults={'status': 1, 'prefix': '',
                                                                'creation_date': datetime.datetime.now(), 'value': 1})
            elif toggle_field == 'extra_view_order_status' and selection:
                update_created_extra_status(user, selection)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Update Configurations failed for params " + str(request.GET.dict()) + " on " + \
                 str(get_local_date(user, datetime.datetime.now())) + "and error statement is " + str(e))
        return HttpResponse("Updation Failed")

    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def delete_tax(request, user=''):
    tax_name = request.GET.get('tax_name', '')

    if not tax_name:
        return HttpResponse('Tax Name Not Found')

    data = MiscDetail.objects.filter(misc_type='tax_' + tax_name, user=user.id)
    if not data:
        return HttpResponse('Tax Name Not Found')

    data = data[0]
    data.delete()
    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def confirm_po(request, user=''):
    sku_id = ''
    ean_flag = False
    data = copy.deepcopy(PO_DATA)
    po_id = get_purchase_order_id(user)
    terms_condition = request.POST.get('terms_condition', '')
    ids_dict = {}
    po_data = []
    total = 0
    total_qty = 0
    show_cess_tax = False
    myDict = dict(request.POST.iterlists())
    display_remarks = get_misc_value('display_remarks_mail', user.id)
    ean_data = SKUMaster.objects.filter(wms_code__in=myDict['wms_code'], user=user.id).values_list(
        'ean_number').exclude(ean_number=0)
    if ean_data:
        ean_flag = True
    all_data = get_raisepo_group_data(user, myDict)
    for key, value in all_data.iteritems():
        price = value['price']
        if value['data_id']:
            purchase_order = OpenPO.objects.get(id=value['data_id'], sku__user=user.id)
            sup_id = value['data_id']
            setattr(purchase_order, 'order_quantity', value['order_quantity'])
            if not value['price']:
                value['price'] = 0
            setattr(purchase_order, 'price', value['price'])
            setattr(purchase_order, 'mrp', value['mrp'])
            setattr(purchase_order, 'po_name', value['po_name'])
            setattr(purchase_order, 'supplier_code', value['supplier_code'])
            setattr(purchase_order, 'remarks', value['remarks'])
            setattr(purchase_order, 'sgst_tax', value['sgst_tax'])
            setattr(purchase_order, 'cgst_tax', value['cgst_tax'])
            setattr(purchase_order, 'igst_tax', value['igst_tax'])
            setattr(purchase_order, 'cess_tax', value['cess_tax'])
            setattr(purchase_order, 'utgst_tax', value['utgst_tax'])
            setattr(purchase_order, 'ship_to', value['ship_to'])
            setattr(purchase_order, 'terms', terms_condition)
            if value['po_delivery_date']:
                setattr(purchase_order, 'delivery_date', value['po_delivery_date'])
            if myDict.get('vendor_id', ''):
                vendor_master = VendorMaster.objects.get(vendor_id=value['vendor_id'], user=user.id)
                setattr(purchase_order, 'vendor_id', vendor_master.id)
                setattr(purchase_order, 'order_type', 'VR')
            purchase_order.save()
            if value['sellers']:
                for k, val in value['sellers'].iteritems():
                    if val[1]:
                        seller_po = SellerPO.objects.get(id=val[1], open_po__sku__user=user.id)
                        seller_po.seller_quantity = val[0]
                        seller_po.save()
                    else:
                        SellerPO.objects.create(seller_id=k, open_po_id=purchase_order.id, seller_quantity=val[0],
                                                creation_date=datetime.datetime.now(), status=1,
                                                receipt_type=value['receipt_type'])
        else:
            sku_id = SKUMaster.objects.filter(wms_code=key.upper(), user=user.id)
            po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
            if not sku_id:
                sku_id = SKUMaster.objects.filter(wms_code='TEMP', user=user.id)
                po_suggestions['wms_code'] = key.upper()
                po_suggestions['supplier_code'] = value['supplier_code']
                if not sku_id[0].wms_code == 'TEMP':
                    supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=value['supplier_id'],
                                                                  sku__user=user.id)
                    sku_mapping = {'supplier_id': value['supplier_id'], 'sku': sku_id[0], 'preference': 1, 'moq': 0,
                                   'supplier_code': value['supplier_code'], 'price': price,
                                   'creation_date': datetime.datetime.now(),
                                   'updation_date': datetime.datetime.now()}
                    if supplier_mapping:
                        supplier_mapping = supplier_mapping[0]
                        if sku_mapping['supplier_code'] and supplier_mapping.supplier_code != sku_mapping[
                            'supplier_code']:
                            supplier_mapping.supplier_code = sku_mapping['supplier_code']
                            supplier_mapping.save()
                    else:
                        new_mapping = SKUSupplier(**sku_mapping)
                        new_mapping.save()
            po_suggestions['sku_id'] = sku_id[0].id
            po_suggestions['supplier_id'] = value['supplier_id']
            po_suggestions['order_quantity'] = float(value['order_quantity'])
            po_suggestions['price'] = float(price)
            po_suggestions['status'] = 'Manual'
            po_suggestions['remarks'] = value['remarks']
            po_suggestions['measurement_unit'] = "UNITS"
            po_suggestions['sgst_tax'] = value['sgst_tax']
            po_suggestions['cgst_tax'] = value['cgst_tax']
            po_suggestions['igst_tax'] = value['igst_tax']
            po_suggestions['cess_tax'] = value['cess_tax']
            po_suggestions['utgst_tax'] = value['utgst_tax']
            po_suggestions['ship_to'] = value['ship_to']
            po_suggestions['terms'] = terms_condition
            if value['po_delivery_date']:
                po_suggestions['delivery_date'] = value['po_delivery_date']
            if value['measurement_unit']:
                if value['measurement_unit'] != "":
                    po_suggestions['measurement_unit'] = value['measurement_unit']

            if myDict.get('vendor_id', ''):
                vendor_master = VendorMaster.objects.get(vendor_id=value['vendor_id'], user=user.id)
                po_suggestions['vendor_id'] = vendor_master.id
                po_suggestions['order_type'] = 'VR'

            data1 = OpenPO(**po_suggestions)
            data1.save()
            if value['sellers']:
                for seller, seller_quan in value['sellers'].iteritems():
                    SellerPO.objects.create(seller_id=seller, open_po_id=data1.id, seller_quantity=seller_quan[0],
                                            creation_date=datetime.datetime.now(), status=1,
                                            receipt_type=value['receipt_type'])
            purchase_order = OpenPO.objects.get(id=data1.id, sku__user=user.id)
            sup_id = purchase_order.id
        supplier = purchase_order.supplier_id
        if supplier not in ids_dict:
            po_id = po_id + 1
            ids_dict[supplier] = po_id
        data['open_po_id'] = sup_id
        data['order_id'] = ids_dict[supplier]
        data['ship_to'] = value['ship_to']
        user_profile = UserProfile.objects.filter(user_id=user.id)
        if user_profile:
            data['prefix'] = user_profile[0].prefix
        order = PurchaseOrder(**data)
        order.save()

        amount = float(purchase_order.order_quantity) * float(purchase_order.price)
        tax = value['sgst_tax'] + value['cgst_tax'] + value['igst_tax'] + value['utgst_tax']
        if value['cess_tax']:
            show_cess_tax = True
            tax += value['cess_tax']
        if not tax:
            total += amount
        else:
            total += amount + ((amount / 100) * float(tax))
        total_qty += float(purchase_order.order_quantity)
        if purchase_order.sku.wms_code == 'TEMP':
            wms_code = purchase_order.wms_code
        else:
            wms_code = purchase_order.sku.wms_code

        total_tax_amt = (purchase_order.utgst_tax + purchase_order.sgst_tax + purchase_order.cgst_tax + purchase_order.igst_tax + purchase_order.cess_tax + purchase_order.utgst_tax) * (amount/100)
        total_sku_amt = total_tax_amt + amount
        po_temp_data = [
                        wms_code, value['supplier_code'], purchase_order.sku.sku_desc, purchase_order.order_quantity,
                        value['measurement_unit'], purchase_order.price, amount, purchase_order.sgst_tax,
                        purchase_order.cgst_tax,
                        purchase_order.igst_tax, purchase_order.cess_tax, purchase_order.utgst_tax, total_sku_amt]
        if ean_flag:
            po_temp_data.insert(1, purchase_order.sku.ean_number)
        if display_remarks == 'true':
            po_temp_data.append(purchase_order.remarks)

        po_data.append(po_temp_data)
        suggestion = OpenPO.objects.get(id=sup_id, sku__user=user.id)
        setattr(suggestion, 'status', 0)
        suggestion.save()

    address = purchase_order.supplier.address
    address = '\n'.join(address.split(','))
    if purchase_order.ship_to:
        ship_to_address = purchase_order.ship_to
        company_address = user.userprofile.address
    else:
        ship_to_address, company_address = get_purchase_company_address(user.userprofile)
    ship_to_address = '\n'.join(ship_to_address.split(','))
    wh_telephone = user.userprofile.wh_phone_number
    telephone = purchase_order.supplier.phone_number
    name = purchase_order.supplier.name
    supplier_email = purchase_order.supplier.email_id
    gstin_no = purchase_order.supplier.tin_number
    order_id = ids_dict[supplier]
    order_date = get_local_date(request.user, order.creation_date)
    vendor_name = ''
    vendor_address = ''
    vendor_telephone = ''
    if purchase_order.order_type == 'VR':
        vendor_address = purchase_order.vendor.address
        vendor_address = '\n'.join(vendor_address.split(','))
        vendor_name = purchase_order.vendor.name
        vendor_telephone = purchase_order.vendor.phone_number

    po_reference = '%s%s_%s' % (order.prefix, str(order_date).split(' ')[0].replace('-', ''), order_id)

    profile = UserProfile.objects.get(user=user.id)

    company_name = profile.company_name
    title = 'Purchase Order'
    receipt_type = request.POST.get('receipt_type', '')
    #if request.POST.get('seller_id', ''):
    #    title = 'Stock Transfer Note'
    if request.POST.get('seller_id', '') and str(request.POST.get('seller_id').split(":")[1]).lower() == 'shproc':
        company_name = 'SHPROC Procurement Pvt. Ltd.'

    table_headers = ['WMS Code', 'Supplier Code', 'Desc', 'Qty', 'UOM', 'Unit Price', 'Amt',
                     'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'Total']
    if ean_flag:
        table_headers.insert(1, 'EAN')
    if display_remarks == 'true':
        table_headers.append('Remarks')
    if show_cess_tax:
        table_headers.insert(10, 'CESS (%)')
    company_logo = get_po_company_logo(user, COMPANY_LOGO_PATHS, request)
    iso_company_logo = get_po_company_logo(user, ISO_COMPANY_LOGO_PATHS, request)
    total_amt_in_words = number_in_words(round(total)) + ' ONLY'
    round_value = float(round(total) - float(total))
    data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 
                 'order_id': order_id, 'telephone': str(telephone),
                 'name': name, 'order_date': order_date, 'total': round(total), 
                 'po_reference': po_reference, 'company_name': company_name,
                 'location': profile.location, 'vendor_name': vendor_name, 
                 'vendor_address': vendor_address, 'vendor_telephone': vendor_telephone, 
                 'total_qty': total_qty, 'receipt_type': receipt_type,
                 'title': title, 'ship_to_address': ship_to_address,
                 'gstin_no': gstin_no, 'w_address': ship_to_address, 
                 'wh_telephone': wh_telephone, 'terms_condition' : terms_condition, 
                 'total_amt_in_words' : total_amt_in_words, 'show_cess_tax': show_cess_tax,
                 'company_address': company_address, 'wh_gstin': profile.gst_number,
                 'company_logo': company_logo, 'iso_company_logo': iso_company_logo}
    if round_value:
        data_dict['round_total'] = "%.2f" % round_value
    t = loader.get_template('templates/toggle/po_download.html')
    rendered = t.render(data_dict)
    if get_misc_value('raise_po', user.id) == 'true':
        write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, telephone, po_data,
                           str(order_date).split(' ')[0], ean_flag=ean_flag)
    check_purchase_order_created(user, po_id)
    return render(request, 'templates/toggle/po_template.html', data_dict)

@csrf_exempt
@login_required
@get_admin_user
def raise_po_toggle(request, user=''):
    filter_params = {'user': user.id}
    suppliers = filter_by_values(SupplierMaster, filter_params, ['id', 'name'])
    supplier_data = [];
    for supplier in suppliers:
        supplier_data.append(ast.literal_eval(json.dumps(supplier)))
    return HttpResponse(json.dumps({'suppliers': supplier_data}))


@csrf_exempt
@login_required
@get_admin_user
def search_supplier(request, user=''):
    data_id = request.GET['q']
    data = SupplierMaster.objects.filter(Q(id__icontains=data_id) | Q(name__icontains=data_id), user=user.id)
    suppliers = []
    if data:
        for supplier in data:
            suppliers.append(str(supplier.id) + ":" + str(supplier.name))
    return HttpResponse(json.dumps(suppliers))


@csrf_exempt
@login_required
@get_admin_user
def search_vendor(request, user=''):
    data_id = request.GET['q']
    data = VendorMaster.objects.filter(Q(vendor_id__icontains=data_id) | Q(name__icontains=data_id), user=user.id)
    vendors = []
    if data:
        for vendor in data:
            vendors.append(str(vendor.vendor_id) + ":" + str(vendor.name))
    return HttpResponse(json.dumps(vendors))


@csrf_exempt
@login_required
@get_admin_user
def get_mapping_values(request, user=''):
    wms_code = request.GET['wms_code']
    supplier_id = request.GET['supplier_id']
    if wms_code.isdigit():
        ean_number = wms_code
        sku_supplier = SKUSupplier.objects.filter(Q(sku__ean_number=wms_code) | Q(sku__wms_code=wms_code),
                                                  supplier_id=supplier_id, sku__user=user.id)
    else:
        ean_number = 0
        sku_supplier = SKUSupplier.objects.filter(sku__wms_code=wms_code, supplier_id=supplier_id, sku__user=user.id)
    sku_master = SKUMaster.objects.get(wms_code=wms_code, user=user.id)
    data = {'supplier_code': '', 'price': sku_master.cost_price, 'sku': sku_master.sku_code,
            'ean_number': 0, 'measurement_unit': sku_master.measurement_type}
    if sku_supplier:
        data['supplier_code'] = sku_supplier[0].supplier_code
        data['price'] = sku_supplier[0].price
        data['sku'] = sku_supplier[0].sku.sku_code
        data['ean_number'] = ean_number
        data['measurement_unit'] = sku_supplier[0].sku.measurement_type

    return HttpResponse(json.dumps(data), content_type='application/json')


def check_and_create_supplier(seller_id, user):
    seller_master = SellerMaster.objects.get(user=user.id, seller_id=seller_id)
    if seller_master.supplier_id:
        supplier_id = seller_master.supplier_id
    else:
        supplier_id = create_new_supplier(user, seller_master.name, seller_master.email_id, seller_master.phone_number,
                            seller_master.address, seller_master.tin_number)
        if supplier_id:
            seller_master.supplier_id = supplier_id
            seller_master.save()
    return supplier_id


def get_raisepo_group_data(user, myDict):
    all_data = OrderedDict()
    for i in range(0, len(myDict['wms_code'])):
        remarks = ''
        supplier_code = ''
        po_name = ''
        ship_to = ''
        measurement_unit = ''
        vendor_id = ''
        price = 0
        seller = ''
        receipt_type = ''
        data_id = ''
        seller_po_id = ''
        supplier_id = ''
        po_delivery_date = ''
        order_type = 'SR'
        sgst_tax = 0
        mrp = 0
        cgst_tax = 0
        igst_tax = 0
        cess_tax = 0
        utgst_tax = 0
        if 'remarks' in myDict.keys():
            remarks = myDict['remarks'][i]
        if 'supplier_code' in myDict.keys():
            supplier_code = myDict['supplier_code'][i]
        if 'po_name' in myDict.keys():
            po_name = myDict['po_name'][0]
        if 'po_delivery_date' in myDict.keys() and myDict['po_delivery_date'][0]:
            po_delivery_date = datetime.datetime.strptime(str(myDict['po_delivery_date'][0]), "%m/%d/%Y")
        if 'ship_to' in myDict.keys():
            ship_to = myDict['ship_to'][0]
        if 'measurement_unit' in myDict.keys():
            measurement_unit = myDict['measurement_unit'][i]
        if 'vendor_id' in myDict.keys():
            vendor_id = myDict['vendor_id'][0]
            order_type = 'VR'
        if 'price' in myDict.keys():
            price = myDict['price'][i]
            if not price:
                price = 0
        if 'receipt_type' in myDict.keys():
            receipt_type = myDict['receipt_type'][0]
        if 'data-id' in myDict.keys():
            data_id = myDict['data-id'][i]
        if 'seller_po_id' in myDict.keys():
            seller_po_id = myDict['seller_po_id'][i]
        if 'mrp' in myDict.keys():
            if myDict['mrp'][i]:
                mrp = float(myDict['mrp'][i])
        if 'sgst_tax' in myDict.keys():
            if myDict['sgst_tax'][i]:
                sgst_tax = float(myDict['sgst_tax'][i])
        if 'cgst_tax' in myDict.keys():
            if myDict['cgst_tax'][i]:
                cgst_tax = float(myDict['cgst_tax'][i])
        if 'igst_tax' in myDict.keys():
            if myDict['igst_tax'][i]:
                igst_tax = float(myDict['igst_tax'][i])
        if 'cess_tax' in myDict.keys():
            if myDict['cess_tax'][i]:
                cess_tax = float(myDict['cess_tax'][i])
        if 'utgst_tax' in myDict.keys():
            if myDict['utgst_tax'][i]:
                utgst_tax = float(myDict['utgst_tax'][i])

        if receipt_type:
            order_types = dict(zip(PO_ORDER_TYPES.values(), PO_ORDER_TYPES.keys()))
            order_type = order_types.get(receipt_type, 'SR')
        if not myDict['supplier_id'][0] and receipt_type == 'Hosted Warehouse' and myDict['dedicated_seller'][0]:
            seller_id = myDict['dedicated_seller'][0].split(':')[0]
            myDict['supplier_id'][0] = check_and_create_supplier(seller_id, user)

        if not myDict['wms_code'][i]:
            continue
        cond = (myDict['wms_code'][i])
        all_data.setdefault(cond, {'order_quantity': 0, 'price': price, 'supplier_id': myDict['supplier_id'][0],
                                   'supplier_code': supplier_code, 'po_name': po_name, 'receipt_type': receipt_type,
                                   'remarks': remarks, 'measurement_unit': measurement_unit,
                                   'vendor_id': vendor_id, 'ship_to': ship_to, 'sellers': {}, 'data_id': data_id,
                                   'order_type': order_type, 'mrp': mrp, 'sgst_tax': sgst_tax, 'cgst_tax': cgst_tax,
                                   'igst_tax': igst_tax, 'cess_tax': cess_tax,
                                   'utgst_tax': utgst_tax, 'po_delivery_date': po_delivery_date})
        order_qty = myDict['order_quantity'][i]
        if not order_qty:
            order_qty = 0
        all_data[cond]['order_quantity'] += float(order_qty)
        if 'dedicated_seller' in myDict:
            seller = myDict['dedicated_seller'][i]
            if ':' in seller:
                seller = seller.split(':')[0]
            seller_master = SellerMaster.objects.get(user=user.id, seller_id=seller)
            if not seller in all_data[cond]['sellers'].keys():
                all_data[cond]['sellers'][seller_master.id] = [float(order_qty), seller_po_id]
            else:
                all_data[cond]['sellers'][seller_master.id][0] += float(order_qty)
    return all_data


@csrf_exempt
@login_required
@get_admin_user
def add_po(request, user=''):
    status = 'Failed to Add PO'
    terms_condition = request.POST.get('terms_condition','')
    myDict = dict(request.POST.iterlists())
    all_data = get_raisepo_group_data(user, myDict)
    for key, value in all_data.iteritems():
        wms_code = key
        if not wms_code:
            continue
        if wms_code.isdigit():
            sku_id = SKUMaster.objects.filter(Q(ean_number=wms_code) | Q(wms_code=wms_code), user=user.id)
        else:
            sku_id = SKUMaster.objects.filter(wms_code=wms_code.upper(), user=user.id)

        # sku_id = SKUMaster.objects.filter(wms_code=wms_code.upper(),user=user.id)
        if not sku_id:
            status = 'Invalid WMS CODE'
            return HttpResponse(status)

        po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)

        supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=value['supplier_id'],
                                                      sku__user=user.id)
        sku_mapping = {'supplier_id': value['supplier_id'], 'sku': sku_id[0], 'preference': 1, 'moq': 0,
                       'supplier_code': value['supplier_code'], 'price': value['price'],
                       'creation_date': datetime.datetime.now(),
                       'updation_date': datetime.datetime.now()}

        if supplier_mapping:
            supplier_mapping = supplier_mapping[0]
            if sku_mapping['supplier_code'] and supplier_mapping.supplier_code != sku_mapping['supplier_code']:
                supplier_mapping.supplier_code = sku_mapping['supplier_code']
                supplier_mapping.save()
        else:
            new_mapping = SKUSupplier(**sku_mapping)
            new_mapping.save()

        suggestions_data = OpenPO.objects.exclude(status__exact='0').filter(sku_id=sku_id,
                                                                            supplier_id=value['supplier_id'],
                                                                            order_quantity=value['order_quantity'],
                                                                            sku__user=user.id)
        if not suggestions_data:
            po_suggestions['sku_id'] = sku_id[0].id
            po_suggestions['supplier_id'] = value['supplier_id']
            try:
                po_suggestions['order_quantity'] = float(value['order_quantity'])
            except:
                po_suggestions['order_quantity'] = 0

            if not value['mrp']:
                value['mrp'] = 0
            po_suggestions['price'] = float(value['price'])
            po_suggestions['mrp'] = float(value['mrp'])
            po_suggestions['status'] = 'Manual'
            po_suggestions['po_name'] = value['po_name']
            po_suggestions['remarks'] = value['remarks']
            po_suggestions['sgst_tax'] = value['sgst_tax']
            po_suggestions['cgst_tax'] = value['cgst_tax']
            po_suggestions['igst_tax'] = value['igst_tax']
            po_suggestions['cess_tax'] = value['cess_tax']
            po_suggestions['utgst_tax'] = value['utgst_tax']
            po_suggestions['order_type'] = value['order_type']
            po_suggestions['ship_to'] = value['ship_to']
            po_suggestions['terms'] = terms_condition
            if value['po_delivery_date']:
                po_suggestions['delivery_date'] = value['po_delivery_date']
            if value.get('vendor_id', ''):
                vendor_master = VendorMaster.objects.get(vendor_id=value['vendor_id'], user=user.id)
                po_suggestions['vendor_id'] = vendor_master.id
                po_suggestions['order_type'] = 'VR'

            data = OpenPO(**po_suggestions)
            data.save()
            if value['sellers']:
                for seller, seller_quan in value['sellers'].iteritems():
                    SellerPO.objects.create(seller_id=seller, open_po_id=data.id, seller_quantity=seller_quan[0],
                                            creation_date=datetime.datetime.now(), status=1,
                                            receipt_type=value['receipt_type'])
            status = 'Added Successfully'
    if all_data and user.username == 'bluecatpaper':
        t = loader.get_template('templates/save_po_data.html')
        data_dict = {'sku_data' : dict(all_data), 'sku_ids' : all_data.keys(), 'headers' : ['SKU Code', 'Qty', 'Unit Price'], 'supplier_name' : request.POST['supplier_id_name'].split(':')[1]}
        rendered = t.render(data_dict)
        email = user.email
        if email:
            send_mail([email], 'BluecatPaper Saved PO Details', rendered)
    return HttpResponse(status)


@csrf_exempt
@login_required
@get_admin_user
def insert_inventory_adjust(request, user=''):
    data = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not data:
        cycle_id = 1
    else:
        cycle_id = data[0].cycle + 1
    wmscode = request.GET['wms_code']
    quantity = request.GET['quantity']
    reason = request.GET['reason']
    loc = request.GET['location']
    pallet_code = request.GET.get('pallet', '')
    batch_no = request.GET.get('batch_no', '')
    mrp = request.GET.get('mrp', '')
    seller_id = request.GET.get('seller_id', '')
    reduce_stock = request.GET.get('inv_shrinkage', 'false')
    seller_master_id = ''
    if seller_id:
        seller_master = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
        if not seller_master:
            return HttpResponse("Invalid Seller ID")
        seller_master_id = seller_master[0].id
    if reduce_stock == 'true':
        status = reduce_location_stock(cycle_id, wmscode, loc, quantity, reason, user, pallet_code, batch_no, mrp,
                                       seller_master_id=seller_master_id)
    else:
        status = adjust_location_stock(cycle_id, wmscode, loc, quantity, reason, user, pallet_code, batch_no, mrp,
                                       seller_master_id=seller_master_id)
    update_filled_capacity([loc], user.id)
    check_and_update_stock([wmscode], user)

    return HttpResponse(status)


@csrf_exempt
@login_required
@get_admin_user
def delete_po(request, user=''):
    for key, value in request.GET.iteritems():
        if key == 'seller_po_id':
            seller_po = SellerPO.objects.get(id=value)
            open_po = OpenPO.objects.get(id=seller_po.open_po_id, sku__user=user.id)
            open_po.order_quantity = float(open_po.order_quantity) - float(seller_po.seller_quantity)
            open_po.save()
            if open_po.order_quantity <= 0:
                open_po.delete()
            seller_po.delete()
        else:
            purchase_order = OpenPO.objects.filter(id=value, sku__user=user.id).delete()

    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def get_supplier_data(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    temp = get_misc_value('pallet_switch', user.id)
    order_ids = []
    headers = ['WMS CODE', 'PO Quantity', 'Received Quantity', 'Unit Price', '']
    if temp == 'true':
        headers.insert(2, 'Pallet Number')
    use_imei = get_misc_value('use_imei', user.id)
    if use_imei == 'true':
        headers.insert(-2, 'Serial Number')
    data = {}
    order_id = request.GET['supplier_id']
    remainder_mail = 0
    purchase_orders = PurchaseOrder.objects.filter(order_id=order_id, open_po__sku__user=user.id,
                                                   open_po__sku_id__in=sku_master_ids,
                                                   received_quantity__lt=F('open_po__order_quantity')).exclude(
        status='location-assigned')
    if not purchase_orders:
        st_orders = STPurchaseOrder.objects.filter(po__order_id=order_id, open_st__sku__user=user.id,
                                                   open_st__sku_id__in=sku_master_ids). \
            exclude(po__status__in=['location-assigned', 'stock-transfer']).values_list('po_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=st_orders)
    if not purchase_orders:
        rw_orders = RWPurchase.objects.filter(purchase_order__order_id=order_id, rwo__vendor__user=user.id,
                                              rwo__job_order__product_code_id__in=sku_master_ids). \
            exclude(purchase_order__status__in=['location-assigned', 'stock-transfer']). \
            values_list('purchase_order_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=rw_orders)
    po_reference = '%s%s_%s' % (
    purchase_orders[0].prefix, str(purchase_orders[0].creation_date).split(' ')[0].replace('-', ''), order_id)
    orders = []
    order_data = {}
    for order in purchase_orders:
        order_data = get_purchase_order_data(order)
        po_quantity = float(order_data['order_quantity']) - float(order.received_quantity)
        sku_details = json.loads(
            serializers.serialize("json", [order_data['sku']], indent=1, use_natural_foreign_keys=True, fields=(
            'sku_code', 'wms_code', 'sku_desc', 'color', 'sku_class', 'sku_brand', 'sku_category', 'image_url',
            'load_unit_handle', 'shelf_life')))
        if po_quantity > 0:
            sku_extra_data, product_images, order_ids = get_order_json_data(user, mapping_id=order.id,
                                                                            mapping_type='PO',
                                                                            sku_id=order_data['sku_id'],
                                                                            order_ids=order_ids)
            skuattributes = SKUAttributes.objects.filter(sku_id=order_data['sku_id'], attribute_name = 'weight' )
            weight = ''
            if skuattributes:
                weight = skuattributes[0].attribute_value
            tax_percent = order_data['cgst_tax'] + order_data['sgst_tax'] + order_data['igst_tax'] +\
                          order_data['utgst_tax']
            orders.append([{ 'order_id': order.id, 'wms_code': order_data['wms_code'],
                            'sku_desc': order_data['sku_desc'], 'weight': weight,
                            'po_quantity': float(order_data['order_quantity']) - float(order.received_quantity),
                            'name': str(order.order_id) + '-' + str(
                                re.sub(r'[^\x00-\x7F]+', '', order_data['wms_code'])),
                            'value': get_decimal_limit(user.id, order.saved_quantity),
                            'receive_quantity': get_decimal_limit(user.id, order.received_quantity),
                            'price': order_data['price'],
                            'mrp': order_data['mrp'],
                            'temp_wms': order_data['temp_wms'], 'order_type': order_data['order_type'],
                            'unit': order_data['unit'],
                            'dis': True,
                            'sku_extra_data': sku_extra_data, 'product_images': product_images,
                            'sku_details': sku_details, 'shelf_life': order_data['shelf_life'],
                            'tax_percent': tax_percent, 'cess_percent': order_data['cess_tax'], 
                            'total_amt': 0, 'show_imei': order_data['sku'].enable_serial_based }])
    supplier_name, order_date, expected_date, remarks = '', '', '', ''
    if purchase_orders:
        purchase_order = purchase_orders[0]
        supplier_name = order_data['supplier_name']
        order_date = get_local_date(user, purchase_order.creation_date)
        remarks = purchase_order.remarks
        remainder_mail = purchase_order.remainder_mail
        if purchase_order.expected_date:
            purchase_order = purchase_orders.latest('expected_date')
            expected_date = datetime.datetime.strftime(purchase_order.expected_date, "%m/%d/%Y")

    return HttpResponse(json.dumps({'data': orders, 'po_id': order_id, 'options': REJECT_REASONS, \
                                    'supplier_id': order_data['supplier_id'], 'use_imei': use_imei, \
                                    'temp': temp, 'po_reference': po_reference, 'order_ids': order_ids, \
                                    'supplier_name': supplier_name, 'order_date': order_date, \
                                    'expected_date': expected_date, 'remarks': remarks,
                                    'remainder_mail': remainder_mail}))


@csrf_exempt
@login_required
@get_admin_user
def update_putaway(request, user=''):
    try:
        log.info("Update Receive PO data for user %s and request params are %s" % (
            user.username, str(request.GET.dict())))
        remarks = request.GET.get('remarks', '')
        expected_date = request.GET.get('expected_date', '')
        remainder_mail = request.GET.get('remainder_mail', '')
        mrp = request.GET.get('mrp','')
        _expected_date = ''
        if expected_date:
            _expected_date = expected_date
            expected_date = expected_date.split('/')
            expected_date = datetime.date(int(expected_date[2]), int(expected_date[0]), int(expected_date[1]))
        for key, value in request.GET.iteritems():
            if key in ['remarks', 'expected_date', 'remainder_mail', 'invoice_date', 'round_off_total', 'invoice_number']:
                continue
            po = PurchaseOrder.objects.get(id=key)
            total_count = float(value)
            order_quantity = 0
            if remarks != po.remarks:
                po.remarks = remarks
            if expected_date:
                if po.expected_date and expected_date.strftime('%d/%m/%Y') != po.expected_date.strftime('%d/%m/%Y'):
                    po.expected_date = expected_date
                else:
                    po.expected_date = expected_date
            if po.open_po:
                order_quantity = po.open_po.order_quantity
            elif po.stpurchaseorder_set.filter():
                st_order = po.stpurchaseorder_set.filter()
                order_quantity = st_order[0].open_st.order_quantity
            elif po.rwpurchase_set.filter():
                rw_purchase = po.rwpurchase_set.filter()
                order_quantity = rw_purchase[0].rwo.job_order.product_quantity
            if total_count > order_quantity:
                return HttpResponse('Given quantity is greater than expected quantity')
            if remainder_mail:
                po.remainder_mail = remainder_mail
            setattr(po, 'saved_quantity', float(value))
            po.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(
            "Update Receive PO data failed for params " + str(request.GET.dict()) + " and error statement is " + str(e))
        return HttpResponse('Updated Failed')
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def close_po(request, user=''):
    if not request.POST:
        return HttpResponse('Updated Successfully')
    status = ''
    myDict = dict(request.POST.iterlists())
    reason = request.POST.get('remarks', '')
    log.info("Close PO data for user %s and request params are %s" % (
        user.username, str(request.POST.dict())))
    for i in range(0, len(myDict['id'])):
        if myDict['id'][i]:
            if myDict['new_sku'][i] == 'true':
                sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user=user.id)
                if not sku_master or not myDict['id'][0]:
                    continue
                po_order = PurchaseOrder.objects.filter(id=myDict['id'][0])
                if po_order:
                    po_order_id = po_order[0].order_id
                new_data = {'supplier_id': [myDict['supplier_id'][i]], 'wms_code': [myDict['wms_code'][i]],
                            'order_quantity': [myDict['po_quantity'][i]], 'price': [myDict['price'][i]],
                            'po_order_id': po_order_id}
                if po_order.open_po:
                    get_data = confirm_add_po(request, new_data)
                    get_data = get_data.content
                    myDict['id'][i] = get_data.split(',')[0]
            if myDict['quantity'][i] and myDict['id'][i]:
                status = confirm_grn(request, {'id': [myDict['id'][i]], 'quantity': [myDict['quantity'][i]]})
                status = status.content
            if 'Invalid' not in status:
                status = ''
                po = PurchaseOrder.objects.get(id=myDict['id'][i])
                setattr(po, 'status', 'location-assigned')
                if reason:
                    po.reason = reason
                po.save()

    if status:
        return HttpResponse(status)
    return HttpResponse('Updated Successfully')


def get_stock_locations(wms_code, exc_dict, user, exclude_zones_list, sku=''):
    all_stocks = StockDetail.objects.filter(sku__user=user, quantity__gt=0,
                                            location__max_capacity__gt=F('location__filled_capacity'))
    only_sku_locs = list(all_stocks.exclude(location__zone__zone='DEFAULT').exclude(sku__wms_code=wms_code).
                         values_list('location_id', flat=True))
    stock_detail1 = all_stocks.exclude(location__zone__zone='DEFAULT').exclude(location_id__in=only_sku_locs).filter(
        sku__wms_code=wms_code). \
        values('location_id', 'location__max_capacity').distinct().annotate(total=Sum('quantity'))
    if sku and not sku.mix_sku == 'no_mix':
        only_locs = map(lambda d: d['location_id'], stock_detail1)
        stock_detail2 = all_stocks.exclude(location__zone__zone='DEFAULT').exclude(location_id__in=only_locs).filter(
            sku__wms_code=wms_code). \
            values('location_id', 'location__max_capacity').distinct().annotate(total=Sum('quantity'))
        stock_detail = list(chain(stock_detail1, stock_detail2))
    else:
        stock_detail = stock_detail1
    location_ids = map(lambda d: d['location_id'], stock_detail)
    loc1 = LocationMaster.objects.exclude(fill_sequence=0).exclude(get_dictionary_query(exc_dict)).exclude(
        zone__zone__in=exclude_zones_list). \
        filter(id__in=location_ids).order_by('fill_sequence')
    if 'pallet_capacity' in exc_dict.keys():
        del exc_dict['pallet_capacity']
    loc2 = LocationMaster.objects.exclude(get_dictionary_query(exc_dict)).exclude(
        zone__zone__in=exclude_zones_list).filter(id__in=location_ids, fill_sequence=0)
    stock_locations = list(chain(loc1, loc2))
    min_max = (0, 0)
    if stock_locations:
        location_sequence = [stock_location.fill_sequence for stock_location in stock_locations]
        min_max = (min(location_sequence), max(location_sequence))
    return stock_locations, location_ids, min_max


def get_purchaseorder_locations(put_zone, temp_dict):
    data = temp_dict['data']
    user = temp_dict['user']
    seller_id = temp_dict.get('seller_id', '')
    location_masters = LocationMaster.objects.filter(zone__user=user).exclude(
        lock_status__in=['Inbound', 'Inbound and Outbound'])
    exclude_zones_list = ['QC_ZONE', 'DAMAGED_ZONE', 'RTO_ZONE', 'Non Sellable Zone']
    if put_zone in exclude_zones_list:
        location = location_masters.filter(zone__zone=put_zone, zone__user=user)
        if location:
            return location
    if data:
        order_data = get_purchase_order_data(data)
    else:
        order_data = {'sku_group': temp_dict['sku_group'], 'wms_code': temp_dict['wms_code'],
                      'sku': temp_dict.get('sku', '')}
    sku_group = order_data['sku_group']
    if sku_group == 'undefined':
        sku_group = ''

    locations = ''
    exc_group_dict = {}
    filter_params = {'zone__zone': put_zone, 'zone__user': user}
    exclude_dict = {'location__exact': '', 'lock_status__in': ['Inbound', 'Inbound and Outbound']}
    stock_detail = StockDetail.objects.filter(sku__user=user)
    po_locations = POLocation.objects.filter(location__zone__user=user, status=1)
    if order_data['sku'].mix_sku == 'no_mix':
        # Get locations with same sku only
        sku_locs = stock_detail.filter(quantity__gt=0, sku__wms_code=order_data['wms_code']). \
            values_list('location_id', flat=True).distinct()
        not_empty_locs = stock_detail.filter(quantity__gt=0, location_id__in=list(sku_locs)). \
            values_list('location_id', flat=True).distinct(). \
            annotate(sku_count=Count('sku_id', distinct=True)).filter(sku_count=1)
        # Get locations with same only in suggested data
        sku_po_locs = po_locations.filter(quantity__gt=0,
                                          purchase_order__open_po__sku__wms_code=order_data['wms_code']). \
            values_list('location_id', flat=True).distinct()
        suggested_locs = po_locations.filter(quantity__gt=0, location_id__in=list(sku_po_locs)). \
            values_list('location_id', flat=True).distinct(). \
            annotate(sku_count=Count('purchase_order__open_po__sku_id', distinct=True)). \
            filter(sku_count=1)
        stock_non_empty = stock_detail.filter(quantity__gt=0).exclude(location_id__in=list(not_empty_locs)). \
            values_list('location_id', flat=True).distinct()
        suggestion_non_empty = po_locations.filter(quantity__gt=0).exclude(
            location_id__in=list(suggested_locs)).values_list('location_id',
                                                              flat=True).distinct()

        exc_group_dict['location_id__in'] = list(chain(stock_non_empty, suggestion_non_empty))
        exclude_dict['id__in'] = list(chain(stock_non_empty, suggestion_non_empty))
    # elif order_data['sku'].mix_sku == 'mix_group':
    else:
        no_mix_locs = list(StockDetail.objects.filter(sku__user=user, quantity__gt=0, sku__mix_sku='no_mix'). \
                           values_list('location_id', flat=True))
        no_mix_sugg = list(POLocation.objects.filter(location__zone__user=user, status=1, quantity__gt=0,
                                                     purchase_order__open_po__sku__mix_sku='no_mix'). \
                           values_list('location_id', flat=True))
        exc_group_dict['location_id__in'] = list(chain(no_mix_locs, no_mix_sugg))
        exclude_dict['id__in'] = list(chain(no_mix_locs, no_mix_sugg))

    if seller_id:
        # Other Seller Locations
        other_seller_locs = SellerStock.objects.filter(seller__user=user, quantity__gt=0).exclude(
            seller_id=seller_id).values_list('stock__location_id', flat=True)
        other_seller_locs_suggested = SellerPOSummary.objects.filter(seller_po__seller__user=user,
                                                                     putaway_quantity__gt=0, location__isnull=False). \
            exclude(seller_po__seller_id=seller_id).values_list('location_id', flat=True)

        exc_group_dict['location_id__in'] = list(
            chain(exc_group_dict['location_id__in'], other_seller_locs, other_seller_locs_suggested))
        exclude_dict['id__in'] = list(chain(exclude_dict['id__in'], other_seller_locs, other_seller_locs_suggested))
    if sku_group:
        locations = LocationGroups.objects.exclude(get_dictionary_query(exc_group_dict)).filter(
            location__zone__user=temp_dict['user'], group=sku_group). \
            values_list('location_id', flat=True)
        all_locations = LocationGroups.objects.exclude(get_dictionary_query(exc_group_dict)).filter(
            location__zone__user=temp_dict['user'], group='ALL'). \
            values_list('location_id', flat=True)
        locations = list(chain(locations, all_locations))
    pallet_number = 0
    if 'pallet_number' in temp_dict.keys():
        pallet_number = temp_dict['pallet_number']
    if sku_group and locations and not put_zone in ['QC_ZONE', 'DAMAGED_ZONE']:
        filter_params['id__in'] = locations
    if put_zone not in exclude_zones_list:
        exclude_dict['zone__zone__in'] = exclude_zones_list
        if pallet_number:
            filter_params['pallet_capacity__gt'] = F('pallet_filled')
            exclude_dict['pallet_capacity'] = 0
        else:
            filter_params['max_capacity__gt'] = F('filled_capacity')
    cond1 = {'fill_sequence__gt': 0}
    cond2 = {'fill_sequence': 0}
    cond1.update(filter_params)
    cond2.update(filter_params)

    stock_locations, location_ids, min_max = get_stock_locations(order_data['wms_code'], exclude_dict, user,
                                                                 exclude_zones_list, sku=order_data['sku'])
    if 'id__in' in exclude_dict.keys():
        location_ids = list(chain(location_ids, exclude_dict['id__in']))
    exclude_dict['id__in'] = location_ids

    location1 = location_masters.exclude(get_dictionary_query(exclude_dict)).filter(fill_sequence__gt=min_max[0],
                                                                                    **filter_params).order_by(
        'fill_sequence')
    location11 = location_masters.exclude(get_dictionary_query(exclude_dict)).filter(fill_sequence__lt=min_max[0],
                                                                                     **filter_params).order_by(
        'fill_sequence')
    location2 = location_masters.exclude(get_dictionary_query(exclude_dict)).filter(**cond1).order_by('fill_sequence')
    if put_zone not in ['QC_ZONE', 'DAMAGED_ZONE']:
        location1 = list(chain(stock_locations, location1))
    location2 = list(chain(location1, location11, location2))

    if 'pallet_capacity' in exclude_dict.keys():
        del exclude_dict['pallet_capacity']

    location3 = location_masters.exclude(get_dictionary_query(exclude_dict)).filter(**cond2)
    del exclude_dict['location__exact']
    del filter_params['zone__zone']
    location4 = location_masters.exclude(
        Q(location__exact='') | Q(zone__zone=put_zone) | get_dictionary_query(exclude_dict)). \
        exclude(zone__zone__in=exclude_zones_list).filter(**filter_params).order_by('fill_sequence')
    if sku_group:
        if 'id__in' in filter_params.keys():
            del filter_params['id__in']
        group_locs = list(
            LocationGroups.objects.filter(location__zone__user=user).values_list('location_id', flat=True).distinct())
        exclude_dict['id__in'] = group_locs
        location5 = location_masters.exclude(
            Q(location__exact='') | Q(zone__zone=put_zone) | get_dictionary_query(exclude_dict)). \
            exclude(zone__zone__in=exclude_zones_list).filter(**filter_params).order_by('fill_sequence')
        location4 = list(chain(location4, location5))

    location = list(chain(location2, location3, location4))

    location = list(chain(location, location_masters.filter(zone__zone='DEFAULT')))

    return location


def get_remaining_capacity(loc, received_quantity, put_zone, pallet_number, user):
    if loc.zone.zone in ['DEFAULT', 'QC_ZONE', 'DAMAGED_ZONE']:
        return received_quantity, 0
    total_quantity = POLocation.objects.filter(location_id=loc.id, status=1, location__zone__user=user). \
        aggregate(Sum('quantity'))['quantity__sum']
    if not total_quantity:
        total_quantity = 0

    if not put_zone == 'QC_ZONE':
        pallet_count = len(
            PalletMapping.objects.filter(po_location__location_id=loc.id, po_location__location__zone__user=user,
                                         status=1))
        if pallet_number:
            if pallet_count >= float(loc.pallet_capacity):
                return '', received_quantity
    filled_capacity = \
    StockDetail.objects.filter(location_id=loc.id, quantity__gt=0, sku__user=user).aggregate(Sum('quantity'))[
        'quantity__sum']
    if not filled_capacity:
        filled_capacity = 0

    filled_capacity = float(total_quantity) + float(filled_capacity)
    remaining_capacity = float(loc.max_capacity) - float(filled_capacity)
    remaining_capacity = float(get_decimal_limit(user, remaining_capacity))
    if remaining_capacity <= 0:
        return '', received_quantity
    elif remaining_capacity < received_quantity:
        location_quantity = remaining_capacity
        received_quantity -= remaining_capacity
    elif remaining_capacity >= received_quantity:
        location_quantity = received_quantity
        received_quantity = 0

    return location_quantity, received_quantity


def save_update_order(location_quantity, location_data, temp_dict, user_check, user):
    location_data[user_check] = user
    po_loc = POLocation.objects.filter(**location_data)
    del location_data[user_check]
    location_data['creation_date'] = datetime.datetime.now()
    location_data['quantity'] = location_quantity
    if 'qc_data' not in temp_dict.keys():
        if not po_loc or user_check == 'purchase_order__open_po__sku__user':
            location_data['original_quantity'] = location_quantity
            po_loc = POLocation(**location_data)
            po_loc.save()
        else:
            po_loc = po_loc[0]
            po_loc.quantity = float(po_loc.quantity) + location_quantity
            po_loc.original_quantity = float(po_loc.original_quantity) + location_quantity
            po_loc.save()
    else:
        location_data['status'] = 2
        po_loc = POLocation(**location_data)
        po_loc.save()
        if temp_dict.get('qc_po_loc_id', ''):
            batch_detail = BatchDetail.objects.filter(transact_type='po_loc', transact_id=temp_dict['qc_po_loc_id'])
            if batch_detail:
                batch_detail.update(transact_id=po_loc.id)
        qc_data = temp_dict['qc_data']
        qc_data['putaway_quantity'] = location_quantity
        qc_data['po_location_id'] = po_loc.id
        qc_saved_data = QualityCheck(**qc_data)
        qc_saved_data.save()
    return po_loc


def update_seller_summary_locs(data, location, quantity, po_received):
    if not po_received['quantity']:
        return po_received
    seller_summary = SellerPOSummary.objects.get(id=po_received['id'])
    if not seller_summary.location:
        if seller_summary.quantity != quantity:
            rem_quantity = float(seller_summary.quantity) - float(quantity)
            rem_putaway_quantity = float(seller_summary.putaway_quantity) - float(quantity)
            seller_po_summary = SellerPOSummary.objects.create(seller_po_id=seller_summary.seller_po.id,
                                                                               receipt_number=seller_summary.receipt_number,
                                                                               quantity=rem_quantity,
                                                                               putaway_quantity=rem_putaway_quantity,
                                                                               location_id=None,
                                                                               purchase_order_id=data.id,
                                                                               creation_date=seller_summary.creation_date)
        seller_summary.location_id = location.id
        seller_summary.quantity = quantity
        seller_summary.putaway_quantity = quantity
        seller_summary.save()
    else:
        if seller_summary.location_id == location.id:
            seller_summary.quantity = float(seller_summary.quantity) + quantity
            seller_summary.putaway_quantity = float(seller_summary.putaway_quantity) + quantity
            seller_summary.save()
        else:
            seller_po_summary, created = SellerPOSummary.objects.get_or_create(seller_po_id=seller_summary.seller_po.id,
                                                                               receipt_number=seller_summary.receipt_number,
                                                                               quantity=quantity,
                                                                               putaway_quantity=quantity,
                                                                               location_id=location.id,
                                                                               purchase_order_id=data.id,
                                                                               creation_date=datetime.datetime.now())
    po_received['quantity'] = po_received['quantity'] - quantity
    return po_received


@csrf_exempt
def save_po_location(put_zone, temp_dict, seller_received_list=[], run_segregation=False, batch_dict=None):
    if not batch_dict:
        batch_dict = {}
    data = temp_dict['data']
    user = temp_dict['user']
    pallet_number = 0
    sellable_segregation = get_misc_value('sellable_segregation', user)
    if 'pallet_number' in temp_dict.keys():
        pallet_number = temp_dict['pallet_number']
    # location = get_purchaseorder_locations(put_zone, temp_dict)
    received_quantity = float(temp_dict['received_quantity'])
    data.status = 'grn-generated'
    data.save()
    purchase_data = get_purchase_order_data(data)
    if not seller_received_list:
        seller_received_list = [{'seller_id': '', 'sku_id': (purchase_data['sku']).id,
                                'quantity': received_quantity, 'id': ''}]
    for po_received in seller_received_list:
        temp_dict['seller_id'] = po_received.get('seller_id', '')
        batch_dict['transact_type'] = 'po'
        batch_dict['transact_id'] = data.id
        batch_obj = get_or_create_batch_detail(batch_dict, temp_dict)
        if sellable_segregation == 'true' and run_segregation:
            if batch_obj and po_received.get('id', ''):
                SellerPOSummary.objects.filter(id=po_received['id']).update(batch_detail_id=batch_obj.id)
            create_update_primary_segregation(data, po_received['quantity'], temp_dict, batch_obj=batch_obj)
            continue
        location = get_purchaseorder_locations(put_zone, temp_dict)
        received_quantity = po_received['quantity']
        for loc in location:
            location_quantity, received_quantity = get_remaining_capacity(loc, received_quantity, put_zone,
                                                                          pallet_number, user)
            if not location_quantity:
                continue
            if po_received.get('seller_id', '') and not loc.zone.zone == 'QC_ZONE':
                po_received = update_seller_summary_locs(data, loc, location_quantity, po_received)
            if not 'quality_check' in temp_dict.keys():
                location_data = {'purchase_order_id': data.id, 'location_id': loc.id, 'status': 1,
                                 'quantity': location_quantity,
                                 'original_quantity': location_quantity,
                                 }
                user_check = 'location__zone__user'
                if data.open_po:
                    user_check = 'purchase_order__open_po__sku__user'
                po_loc = save_update_order(location_quantity, location_data, temp_dict, user_check, user)
                #Batch Details Creation
                batch_dict['transact_type'] = 'po_loc'
                batch_dict['transact_id'] = po_loc.id
                create_update_batch_data(batch_dict)
                if pallet_number:
                    if temp_dict['pallet_data'] == 'true':
                        insert_pallet_data(temp_dict, po_loc)
                if received_quantity == 0:
                    if float(purchase_data['order_quantity']) - float(temp_dict['received_quantity']) <= 0:
                        data.status = 'location-assigned'
                    data.save()
                    break
            else:
                quality_check = temp_dict['quality_check']
                po_location = POLocation.objects.filter(location_id=loc.id, purchase_order_id=data.id,
                                                        location__zone__user=user)
                if po_location and not pallet_number:
                    if po_location[0].status == '1':
                        setattr(po_location[0], 'quantity', float(po_location[0].quantity) + location_quantity)
                    else:
                        setattr(po_location[0], 'quantity', float(location_quantity))
                        setattr(po_location[0], 'status', '1')
                    po_location[0].save()
                    po_location_id = po_location[0].id
                else:
                    location_data = {'purchase_order_id': data.id, 'location_id': loc.id, 'status': 1,
                                     'quantity': location_quantity,
                                     'original_quantity': location_quantity, 'creation_date': datetime.datetime.now()}
                    po_loc = POLocation(**location_data)
                    po_loc.save()
                    po_location_id = po_loc.id
                if pallet_number:
                    if not put_zone == 'DAMAGED_ZONE':
                        pallet_data = temp_dict['pallet_data']
                        setattr(pallet_data, 'po_location_id', po_loc)
                        pallet_data.save()
                #Batch Details Creation
                batch_dict['transact_type'] = 'po_loc'
                batch_dict['transact_id'] = po_location_id
                create_update_batch_data(batch_dict)
                quality_checked_data = QualityCheck.objects.filter(purchase_order_id=data.id,
                                                                   purchase_order__open_po__sku__user=user)
                data_checked = 0
                for checked_data in quality_checked_data:
                    data_checked += float(checked_data.accepted_quantity) + float(checked_data.rejected_quantity)

                if float(data.received_quantity) - data_checked == 0:
                    quality_check.po_location.delete()
                    data.status = 'location-assigned'
                    data.save()
                if not received_quantity or received_quantity == 0:
                    break
        else:
            location = LocationMaster.objects.filter(zone__zone='DEFAULT', zone__user=user)
            for record in location:
                if pallet_number:
                    if temp_dict['pallet_data'] == 'true':
                        received_quantity = confirmation_location(record, data, received_quantity, temp_dict)
                else:
                    received_quantity = confirmation_location(record, data, received_quantity)
                if received_quantity == 0:
                    break


@csrf_exempt
@get_admin_user
def add_lr_details(request, user=''):
    lr_number = request.GET['lr_number']
    carrier_name = request.GET['carrier_name']
    po_id = request.GET['po_id']
    po_data = PurchaseOrder.objects.filter(order_id=po_id, open_po__sku__user=user.id)
    for data in po_data:
        lr_details = LRDetail(lr_number=lr_number, carrier_name=carrier_name, quantity=data.received_quantity,
                              creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now(),
                              purchase_order_id=data.id)
        lr_details.save()

    return HttpResponse('success')


@csrf_exempt
@get_admin_user
def supplier_code_mapping(request, myDict, i, data, user=''):
    if not user:
        user = request.user
    sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user=user.id)
    if sku_master and data.open_po:
        data.open_po.sku_id = sku_master[0].id
        data.open_po.save()
        supplier_mapping = SKUSupplier.objects.filter(sku__wms_code=myDict['wms_code'][i].upper(),
                                                      supplier_id=data.open_po.supplier_id,
                                                      sku__user=user.id)
        if supplier_mapping:
            supplier_mapping = supplier_mapping[0]
            setattr(supplier_mapping, 'supplier_code', data.open_po.supplier_code)
            supplier_mapping.save()
        else:
            sku_mapping = {'supplier_id': data.open_po.supplier_id, 'sku': data.open_po.sku, 'preference': 1, 'moq': 0,
                           'supplier_code': data.open_po.supplier_code, 'price': data.open_po.price,
                           'creation_date': datetime.datetime.now(),
                           'updation_date': datetime.datetime.now()}
            if supplier_mapping:
                supplier_mapping = supplier_mapping[0]
                if sku_mapping['supplier_code'] and supplier_mapping.supplier_code != sku_mapping['supplier_code']:
                    supplier_mapping.supplier_code = sku_mapping['supplier_code']
                    supplier_mapping.save()
            else:
                new_mapping = SKUSupplier(**sku_mapping)
                new_mapping.save()


def insert_pallet_data(temp_dict, po_location_id, status=''):
    if not status:
        status = 1
    pallet_data = copy.deepcopy(PALLET_FIELDS)
    pallet_data['pallet_code'] = temp_dict['pallet_number']
    pallet_data['quantity'] = temp_dict['received_quantity']
    pallet_data['user'] = temp_dict['user']
    save_pallet = PalletDetail(**pallet_data)
    save_pallet.save()
    if save_pallet:
        pallet_map = {'pallet_detail_id': save_pallet.id, 'po_location_id': po_location_id.id,
                      'creation_date': datetime.datetime.now(), 'status': status}
        pallet_mapping = PalletMapping(**pallet_map)
        pallet_mapping.save()


def create_bayarea_stock(sku_code, zone, quantity, user):
    back_order = get_misc_value('back_order', user)
    mod_location = []
    if back_order == 'false' or not quantity:
        return
    inventory = StockDetail.objects.filter(sku__sku_code=sku_code, location__zone__zone=zone, sku__user=user)
    if inventory:
        inventory = inventory[0]
        setattr(inventory, 'quantity', float(inventory.quantity) + float(quantity))
        inventory.save()
        mod_location.append(inventory.location.location)
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
            mod_location.append(location_id[0].location)
    if mod_location:
        update_filled_capacity(list(set(mod_location)), user_id)


def get_seller_receipt_id(purchase_order):
    receipt_number = 1
    summary = SellerPOSummary.objects.filter(purchase_order__open_po__sku__user=purchase_order.open_po.sku.user,
                                             purchase_order__order_id = purchase_order.order_id).\
                                        order_by('-creation_date')
    if summary:
        receipt_number = int(summary[0].receipt_number) + 1
    return receipt_number


def create_update_primary_segregation(data, quantity, temp_dict, batch_obj=None):
    if not batch_obj and not 'quality_check' in temp_dict.keys():
        segregation_obj = PrimarySegregation.objects.filter(purchase_order_id=data.id)
        if segregation_obj:
            segregation_obj = segregation_obj[0]
            segregation_obj.quantity = float(segregation_obj.quantity) + quantity
            if segregation_obj.status == 0:
                segregation_obj.status = 1
            segregation_obj.save()
        else:
            segregation_obj = PrimarySegregation.objects.create(purchase_order_id=data.id, quantity=quantity,status=1,
                                              creation_date=datetime.datetime.now())
    else:
        if batch_obj:
            segregation_obj = PrimarySegregation.objects.filter(purchase_order_id=data.id,
                                                                batch_detail_id=batch_obj.id)
            if segregation_obj:
                segregation_obj = segregation_obj[0]
                segregation_obj.quantity = float(segregation_obj.quantity) + quantity
                if segregation_obj.status == 0:
                    segregation_obj.status = 1
                segregation_obj.save()
            else:
                segregation_obj = PrimarySegregation.objects.create(purchase_order_id=data.id, quantity=quantity, status=1,
                                                                    creation_date=datetime.datetime.now(),
                                                                    batch_detail_id=batch_obj.id)

def update_seller_po(data, value, user, myDict, i, receipt_id='', invoice_number='', invoice_date=None,
                     challan_number='', challan_date=None, dc_level_grn='', round_off_total=0):
    if not receipt_id:
        return
    seller_pos = SellerPO.objects.filter(seller__user=user.id, open_po_id=data.open_po_id)
    seller_received_list = []
    #invoice_number = int(invoice_number)
    if not invoice_date and not dc_level_grn:
        invoice_date = datetime.datetime.now().date()
    elif dc_level_grn:
        invoice_date = None
    if invoice_number:
        order_status_flag = 'supplier_invoices'
    if challan_number:
        order_status_flag = 'po_challans'
    if not invoice_number and not challan_number:
        order_status_flag = 'processed_pos'
    discount_percent = 0
    if 'discount_percentage' in myDict.keys() and myDict['discount_percentage'][i]:
        discount_percent = myDict['discount_percentage'][i]
    if user.userprofile.user_type == 'warehouse_user':
        seller_po_summary, created = SellerPOSummary.objects.get_or_create(receipt_number=receipt_id,
                                                                           invoice_number=invoice_number,
                                                                           quantity=value,
                                                                           putaway_quantity=value,
                                                                           purchase_order_id=data.id,
                                                                           creation_date=datetime.datetime.now(),
                                                                           invoice_date=invoice_date,
                                                                           challan_number=challan_number,
                                                                           challan_date=challan_date,
                                                                           order_status_flag=order_status_flag,
                                                                           discount_percent=discount_percent,
                                                                           round_off_total=round_off_total)
        seller_received_list.append(
            {'seller_id': '', 'sku_id': data.open_po.sku_id, 'quantity': value,
             'id': seller_po_summary.id})
    else:
        for sell_po in seller_pos:
            if not value:
                break
            unit_price = data.open_po.price
            if not sell_po.unit_price:
                margin_percent = get_misc_value('seller_margin', user.id)
                if sell_po.seller.margin:
                    margin_percent = sell_po.seller.margin
                seller_mapping = SellerMarginMapping.objects.filter(seller_id=sell_po.seller_id, sku_id=data.open_po.sku_id,
                                                                    seller__user=user.id)
                if seller_mapping:
                    margin_percent = seller_mapping[0].margin
                if margin_percent:
                    try:
                        margin_percent = float(margin_percent)
                    except:
                        margin_percent = 0
                    price = float(data.open_po.price)
                    tax = data.open_po.cgst_tax + data.open_po.sgst_tax + data.open_po.igst_tax + data.open_po.cess_tax + data.open_po.utgst_tax
                    price = price + ((price / 100) * float(tax))
                    unit_price = float(price) / (1 - (margin_percent / 100))
                    sell_po.unit_price = float(("%." + str(2) + "f") % (unit_price))
                    sell_po.margin_percent = margin_percent
            # seller_quantity = sell_po.seller_quantity
            # sell_quan = value
            # if seller_quantity < value:
            #     sell_quan = seller_quantity
            #     value -= seller_quantity
            # elif seller_quantity >= value:
            #     sell_quan = value
            #     value = 0
            sell_po.received_quantity += value
            if sell_po.seller_quantity <= sell_po.received_quantity:
                sell_po.status = 0
            sell_po.save()

            # seller_received_list.append({'seller_id': sell_po.seller_id, 'sku_id': data.open_po.sku_id, 'quantity': sell_quan})
            seller_po_summary, created = SellerPOSummary.objects.get_or_create(seller_po_id=sell_po.id,
                                                                               receipt_number=receipt_id,
                                                                               quantity=value,
                                                                               putaway_quantity=value,
                                                                               purchase_order_id=data.id,
                                                                               creation_date=datetime.datetime.now(),
                                                                               discount_percent=discount_percent,
                                                                               challan_number=challan_number,
                                                                               challan_date=challan_date,
                                                                               invoice_number=invoice_number,
                                                                               order_status_flag=order_status_flag,
                                                                               invoice_date=invoice_date,
                                                                               round_off_total=round_off_total)
            seller_received_list.append(
                {'seller_id': sell_po.seller_id, 'sku_id': data.open_po.sku_id, 'quantity': value,
                 'id': seller_po_summary.id})
    return seller_received_list


def generate_grn(myDict, request, user, is_confirm_receive=False):
    order_quantity_dict = {}
    all_data = OrderedDict()
    seller_receipt_id = 0
    po_data = []
    status_msg = ''
    data_dict = ''
    remarks = request.POST.get('remarks', '')
    expected_date = request.POST.get('expected_date', '')
    remainder_mail = request.POST.get('remainder_mail', '')
    invoice_number = request.POST.get('invoice_number', '')
    dc_level_grn = request.POST.get('dc_level_grn', '')
    round_off_checkbox = request.POST.get('round_off', '')
    round_off_total = request.POST.get('round_off_total', 0) if round_off_checkbox=='on' else 0
    bill_date = None if dc_level_grn=='on' else datetime.datetime.now().date()
    challan_number = request.POST.get('dc_number', '')
    challan_date = request.POST.get('dc_date', '')
    if challan_date:
        challan_date = datetime.datetime.strptime(challan_date, "%m/%d/%Y").date()
    else:
        challan_date = None
    if request.POST.get('invoice_date', ''):
        bill_date = datetime.datetime.strptime(request.POST.get('invoice_date', ''), "%m/%d/%Y").date()
    _expected_date = ''
    if expected_date:
        _expected_date = expected_date
        expected_date = expected_date.split('/')
        expected_date = datetime.date(int(expected_date[2]), int(expected_date[0]), int(expected_date[1]))
    for i in range(len(myDict['id'])):
        temp_dict = {}
        value = myDict['quantity'][i]
        try:
            value = float(value)
        except:
            value = 0

        if not value:
            continue

        if 'po_quantity' in myDict.keys() and 'price' in myDict.keys() and not myDict['id'][i]:
            if myDict['wms_code'][i] and myDict['quantity'][i]:
                sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user=user.id)
                if not sku_master or not myDict['id'][0]:
                    if not status_msg:
                        status_msg = 'Invalid WMS Code ' + myDict['wms_code'][i]
                    else:
                        status_msg += ',' + myDict['wms_code'][i]
                    continue
                get_data = create_purchase_order(request, myDict, i)
                myDict['id'][i] = get_data
        data = PurchaseOrder.objects.get(id=myDict['id'][i])
        if remarks != data.remarks:
            data.remarks = remarks
        if expected_date:
            data.expected_date = expected_date
        if remainder_mail:
            data.remainder_mail = remainder_mail

        #Create Batch Detail entry
        batch_dict = {}
        if 'batch_no' in myDict.keys():
            batch_dict = {'transact_type': 'po_loc', 'batch_no': myDict['batch_no'][i],
                          'expiry_date': myDict['exp_date'][i],
                          'manufactured_date': myDict['mfg_date'][i],
                          'tax_percent': myDict['tax_percent'][i],
                          'mrp': myDict['mrp'][i], 'buy_price': myDict['buy_price'][i]
                         }
        purchase_data = get_purchase_order_data(data)
        temp_quantity = data.received_quantity
        unit = ''
        sku_row_buy_price = 0
        sku_row_cess_percent = 0
        sku_row_tax_percent = 0
        sku_row_discount_percent = 0
        if 'unit' in myDict.keys():
            unit = myDict['unit'][i]
        if 'buy_price' in myDict:
            sku_row_buy_price = myDict['buy_price'][i]
        if 'cess_percent' in myDict:
            sku_row_cess_percent = myDict['cess_percent'][i]
        if 'tax_percent' in myDict:
            sku_row_tax_percent = myDict['tax_percent'][i]
        if sku_row_buy_price:
            purchase_data['price'] = float(sku_row_buy_price)
        if sku_row_cess_percent:
            purchase_data['cess_tax'] = float(sku_row_cess_percent)
        if 'discount_percentage' in myDict and myDict['discount_percentage'][i]:
            sku_row_discount_percent = float(myDict['discount_percentage'][i])
        if sku_row_tax_percent:
            if purchase_data['igst_tax']:
                purchase_data['igst_tax'] = float(sku_row_tax_percent)
            else:
                purchase_data['sgst_tax'] = float(sku_row_tax_percent)/2
                purchase_data['cgst_tax'] = float(sku_row_tax_percent)/2
        cond = (data.id, purchase_data['wms_code'], unit, purchase_data['price'], purchase_data['cgst_tax'],
                purchase_data['sgst_tax'], purchase_data['igst_tax'], purchase_data['utgst_tax'],
                purchase_data['sku_desc'], purchase_data['cess_tax'], sku_row_discount_percent)
        all_data.setdefault(cond, 0)
        all_data[cond] += float(value)

        if data.id not in order_quantity_dict:
            order_quantity_dict[data.id] = float(purchase_data['order_quantity']) - temp_quantity
        data.received_quantity = float(data.received_quantity) + float(value)
        if  data.intransit_quantity >= float(value):
            data.intransit_quantity = float(data.intransit_quantity) - float(value)
        else:
            data.intransit_quantity = 0
        data.saved_quantity = 0

        seller_received_list = []
        if data.open_po:
            if not seller_receipt_id:
                seller_receipt_id = get_seller_receipt_id(data)
            seller_received_list = update_seller_po(data, value, user, myDict, i, receipt_id=seller_receipt_id,
                                                    invoice_number=invoice_number, invoice_date=bill_date,
                                                    challan_number=challan_number, challan_date=challan_date,
                                                    dc_level_grn=dc_level_grn, round_off_total=round_off_total)
        if 'wms_code' in myDict.keys():
            if myDict['wms_code'][i]:
                sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user=user.id)
                if sku_master:
                    supplier_code_mapping(request, myDict, i, data)
                else:
                    if not status_msg:
                        status_msg = 'Invalid WMS Code ' + myDict['wms_code'][i]
                    else:
                        status_msg += ',' + myDict['wms_code'][i]
                    continue

        pallet_number = ''
        pallet_data = ''
        if 'pallet_number' in myDict.keys() and get_misc_value('pallet_switch', user.id) == 'true':
            if myDict['pallet_number'][i]:
                pallet_number = myDict['pallet_number'][i]
                pallet_data = 'true'
        if 'imei_number' in myDict.keys() and myDict['imei_number'][i]:
            insert_po_mapping(myDict['imei_number'][i], data, user.id)

        put_zone = purchase_data['zone']

        if put_zone:
            put_zone = put_zone.zone
        else:
            put_zone = ZoneMaster.objects.filter(zone='DEFAULT', user=user.id)
            if not put_zone:
                create_default_zones(user, 'DEFAULT', 'DFLT1', 9999)
                put_zone = ZoneMaster.objects.filter(zone='DEFAULT', user=user.id)[0]
            else:
                put_zone = put_zone[0]

            put_zone = put_zone.zone

        temp_dict = {'received_quantity': float(value), 'user': user.id, 'data': data, 'pallet_number': pallet_number,
                     'pallet_data': pallet_data}

        if (get_permission(request.user, 'add_qualitycheck') and purchase_data['qc_check'] == 1):
            put_zone = 'QC_ZONE'
            qc_data = copy.deepcopy(QUALITY_CHECK_FIELDS)
            qc_data['purchase_order_id'] = data.id
            temp_dict['qc_data'] = qc_data
            save_po_location(put_zone, temp_dict, seller_received_list=seller_received_list,
                             batch_dict=batch_dict)
            data_dict = (('Order ID', data.order_id), ('Supplier ID', purchase_data['supplier_id']),
                         ('Order Date', get_local_date(request.user, data.creation_date)),
                         ('Supplier Name', purchase_data['supplier_name']),
                         ('GSTIN No', purchase_data['gstin_number']))

            price = float(value) * float(purchase_data['price'])
            po_data.append((purchase_data['wms_code'], purchase_data['supplier_code'], purchase_data['sku_desc'],
                            purchase_data['order_quantity'], value, price))
            continue
        else:
            is_putaway = 'true'
        save_po_location(put_zone, temp_dict, seller_received_list=seller_received_list, run_segregation=True,
                         batch_dict=batch_dict)
        create_bayarea_stock(purchase_data['wms_code'], 'BAY_AREA', temp_dict['received_quantity'], user.id)
        data_dict = (('Order ID', data.order_id), ('Supplier ID', purchase_data['supplier_id']),
                     ('Order Date', get_local_date(request.user, data.creation_date)),
                     ('Supplier Name', purchase_data['supplier_name']),
                     ('GSTIN No', purchase_data['gstin_number']))

        price = float(value) * float(purchase_data['price'])
        gst_taxes = purchase_data['cgst_tax'] + purchase_data['sgst_tax'] + purchase_data['igst_tax'] + purchase_data[
            'utgst_tax']
        if gst_taxes:
            price += (price / 100) * gst_taxes
        po_data.append((purchase_data['wms_code'], purchase_data['supplier_code'], purchase_data['sku_desc'],
                        purchase_data['order_quantity'],
                        value, price))
    return po_data, status_msg, all_data, order_quantity_dict, purchase_data, data, data_dict, seller_receipt_id


@csrf_exempt
@login_required
@get_admin_user
def confirm_grn(request, confirm_returns='', user=''):
    data_dict = ''
    headers = (
    'WMS CODE', 'Order Quantity', 'Received Quantity', 'Measurement', 'Unit Price', 'CSGT(%)', 'SGST(%)', 'IGST(%)',
    'UTGST(%)', 'Amount', 'Description', 'CESS(%)')
    putaway_data = {headers: []}
    total_received_qty = 0
    total_order_qty = 0
    total_price = 0
    total_tax = 0
    pallet_number = ''
    is_putaway = ''
    purchase_data = ''
    seller_name = user.username
    seller_address = user.userprofile.address
    seller_receipt_id = 0
    if user.username=='milkbasket' and (not request.POST.get('invoice_number', '') and not request.POST.get('dc_number', '')):
        return HttpResponse("Invoice/DC Number  is Mandatory")
    if user.username == 'milkbasket' and (not request.POST.get('invoice_date', '') and not request.POST.get('dc_date', '')):
        return HttpResponse("Invoice/DC Date is Mandatory")
    invoice_num = request.POST.get('invoice_number', '')
    if invoice_num:
        supplier_id = ''
        if request.POST.get('supplier_id', ''):
            supplier_id = request.POST['supplier_id']
        inv_status = po_invoice_number_check(user, invoice_num, supplier_id)
        if inv_status:
            return HttpResponse(inv_status)
    challan_date = request.POST.get('dc_date', '')
    challan_date = datetime.datetime.strptime(challan_date, "%m/%d/%Y").date() if challan_date else ''
    bill_date = datetime.datetime.now().date().strftime('%d-%m-%Y')
    round_off_checkbox = request.POST.get('round_off', '')
    round_off_total = request.POST.get('round_off_total', 0)
    if request.POST.get('invoice_date', ''):
        bill_date = datetime.datetime.strptime(str(request.POST.get('invoice_date', '')), "%m/%d/%Y").strftime('%d-%m-%Y')
    if not confirm_returns:
        request_data = request.POST
        myDict = dict(request_data.iterlists())
    else:
        myDict = confirm_returns

    log.info('Request params for ' + user.username + ' is ' + str(myDict))
    try:
        po_data, status_msg, all_data, order_quantity_dict, \
        purchase_data, data, data_dict, seller_receipt_id = generate_grn(myDict, request, user)

        for key, value in all_data.iteritems():
            entry_price = float(key[3]) * float(value)
            if key[10]:
                entry_price -= (entry_price * (float(key[10])/100))
            entry_tax = float(key[4]) + float(key[5]) + float(key[6]) + float(key[7] + float(key[9]))
            if entry_tax:
                entry_price += (float(entry_price) / 100) * entry_tax
            putaway_data[headers].append((key[1], order_quantity_dict[key[0]], value, key[2], key[3], key[4], key[5],
                                          key[6], key[7], entry_price, key[8], key[9]))
            total_order_qty += order_quantity_dict[key[0]]
            total_received_qty += value
            total_price += entry_price
            total_tax += (key[4] + key[5] + key[6] + key[7] + key[9])
        if round_off_checkbox=='on':
            total_price = round_off_total

        if is_putaway == 'true':
            btn_class = 'inb-putaway'
        else:
            btn_class = 'inb-qc'

        if not status_msg:
            if not purchase_data:
                return HttpResponse('Success')
            address = purchase_data['address']
            address = '\n'.join(address.split(','))
            telephone = purchase_data['phone_number']
            name = purchase_data['supplier_name']
            supplier_email = purchase_data['email_id']
            gstin_number = purchase_data['gstin_number']
            order_id = data.order_id
            order_date = get_local_date(request.user, data.creation_date)
            order_date = datetime.datetime.strftime(datetime.datetime.strptime(order_date, "%d %b, %Y %I:%M %p"), "%d-%m-%Y")

            profile = UserProfile.objects.get(user=user.id)
            po_reference = '%s%s_%s' % (data.prefix, str(data.creation_date).split(' ')[0].replace('-', ''), order_id)
            table_headers = (
            'WMS Code', 'Supplier Code', 'Description', 'Ordered Quantity', 'Received Quantity', 'Amount')
            '''report_data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                                'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total_price,
                                'po_reference': po_reference, 'total_qty': total_received_qty,
                                'report_name': 'Goods Receipt Note', 'company_name': profile.company_name, 'location': profile.location}'''
            sku_list = putaway_data[putaway_data.keys()[0]]
            sku_slices = generate_grn_pagination(sku_list)
            if seller_receipt_id:
                po_number = str(data.prefix) + str(data.creation_date).split(' ')[0] + '_' + str(data.order_id) \
                            + '/' + str(seller_receipt_id)
            else:
                po_number = str(data.prefix) + str(data.creation_date).split(' ')[0] + '_' + str(data.order_id)
            dc_level_grn = request.POST.get('dc_level_grn', '')
            if dc_level_grn == 'on':
                bill_no = request.POST.get('dc_number', '')
                bill_date = challan_date.strftime('%d-%m-%Y') if challan_date else ''
            else:
                bill_no = request.POST.get('invoice_number', '')
            report_data_dict = {'data': putaway_data, 'data_dict': data_dict, 'data_slices': sku_slices,
                                'total_received_qty': total_received_qty, 'total_order_qty': total_order_qty,
                                'total_price': total_price, 'total_tax': total_tax,
                                'address': address,
                                'company_name': profile.company_name, 'company_address': profile.address,
                                'po_number': po_number, 'bill_no': bill_no,
                                'order_date': order_date, 'order_id': order_id,
                                'btn_class': btn_class, 'bill_date': bill_date }
            misc_detail = get_misc_value('receive_po', user.id)
            if misc_detail == 'true':
                t = loader.get_template('templates/toggle/grn_form.html')
                rendered = t.render(report_data_dict)
                write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, telephone, po_data, order_date, internal=True, report_type="Goods Receipt Note")
            return render(request, 'templates/toggle/c_putaway_toggle.html', report_data_dict)
        else:
            return HttpResponse(status_msg)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Check Generating GRN failed for params " + str(myDict) + " and error statement is " + str(e))
        return HttpResponse("Generate GRN Failed")


def generate_grn_pagination(sku_list):
    # header 220
    # footer 125
    # table header 44
    # row 46
    # total 1358
    # default 24 items
    # last page 21 items
    sku_len = len(sku_list)
    sku_list1 = []
    for index, sku in enumerate(sku_list):
        sku += (index+1,)
        sku_list1.append(sku)
    sku_list = sku_list1
    t = sku_list[0]
    #for i in range(47): sku_list.append(t)#remove it
    sku_slices = [sku_list[i: i+24] for i in range(0, len(sku_list), 24)]
    extra_tuple = ('', '', '', '', '', '', '', '', '', '', '', '')
    if len(sku_slices[-1]) == 24:
        temp = sku_slices[-1]
        sku_slices[-1] = temp[:23]
        temp = [temp[-1]]
        for i in range(20): temp.append(extra_tuple)
        sku_slices.append(temp)
    else:
        for i in range((21 - len(sku_slices[-1]))): sku_slices[-1].append(extra_tuple)
    return sku_slices


@csrf_exempt
def confirmation_location(record, data, total_quantity, temp_dict=''):
    location_data = {'purchase_order_id': data.id, 'location_id': record.id, 'status': 1, 'quantity': '',
                     'creation_date': datetime.datetime.now()}
    if total_quantity < (record.max_capacity - record.filled_capacity):
        location_data['quantity'] = total_quantity
        location_data['original_quantity'] = total_quantity
        loc = POLocation(**location_data)
        loc.save()

        total_quantity = 0
    else:
        if float(record.max_capacity) - float(record.filled_capacity) > 0:
            difference = record.max_capacity - record.filled_capacity
        else:
            record.max_capacity += total_quantity
            record.filled_capacity += total_quantity
            difference = total_quantity
        location_data['quantity'] = difference
        location_data['original_quantity'] = difference
        loc = POLocation(**location_data)
        loc.save()
        total_quantity = float(total_quantity) - float(difference)
    if temp_dict:
        insert_pallet_data(temp_dict, loc)
    return total_quantity


def returns_order_tracking(order_returns, user, quantity, status='', imei=''):
    now = datetime.datetime.now()
    try:
        if order_returns.order_id:
            log.info('Order Tracking Data Request Params %s, %s, %s, %s' % (str(order_returns.order_id), str(quantity),
                                                                            str(status), str(imei)))
            OrderTracking.objects.create(order_id=order_returns.order_id, status=status, imei=imei, quantity=quantity,
                                         creation_date=now, updation_date=now)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(
            'Order Tracking Insert failed for %s and params are %s and error statement is %s' % (user.username,
                                                                                                 str(order_returns.id),
                                                                                                 str(e)))
    return True


@login_required
@get_admin_user
def check_returns(request, user=''):
    from django.core.exceptions import ObjectDoesNotExist
    status = ''
    all_data = {}
    data = []
    request_order_id = request.GET.get('order_id', '')
    request_return_id = request.GET.get('return_id', '')
    request_awb = request.GET.get('awb_no', '')
    if request_awb:
        try:
            request_order_id = OrderAwbMap.objects.get(awb_no=request_awb, user=user.id).original_order_id
        except ObjectDoesNotExist:
            request_order_id = None
    if request_order_id:
        filter_params = {}
        order_id = re.findall('\d+', request_order_id)
        order_code = re.findall('\D+', request_order_id)
        if order_id:
            filter_params['order__order_id'] = ''.join(order_id[0])
        if order_code:
            filter_params['order__order_code'] = ''.join(order_code[0])

        picklists = Picklist.objects.filter(Q(order__user=user.id) | Q(stock__sku__user=user.id),
                                            Q(order__original_order_id=request_order_id) | Q(**filter_params),
                                            status__in=['picked', 'batch_picked', 'dispatched'], picked_quantity__gt=0)
        if not picklists:
            status = 'Order Id is invalid'
        for picklist in picklists:
            wms_code = picklist.order.sku.wms_code
            sku_desc = picklist.order.sku.sku_desc
            if picklist.stock:
                wms_code = picklist.stock.sku.wms_code
                sku_desc = picklist.stock.sku.sku_desc
            order_id = picklist.order.original_order_id
            if not order_id:
                order_id = picklist.order.order_code + str(picklist.order.order_id)
            cond = (order_id, wms_code, sku_desc, picklist.order.id)
            all_data.setdefault(cond, 0)
            all_data[cond] += picklist.picked_quantity
        for key, value in all_data.iteritems():
            order_track_obj = OrderTracking.objects.filter(order_id=key[3], status='returned')
            if order_track_obj:
                order_track_quantity = int(order_track_obj.aggregate(Sum('quantity'))['quantity__sum'])
                if value == order_track_quantity:
                    continue
                else:
                    remaining_return = int(value) - int(order_track_quantity)
                    data.append({'order_id': key[0], 'sku_code': key[1], 'sku_desc': key[2],
                                 'ship_quantity': remaining_return, 'return_quantity': remaining_return,
                                 'damaged_quantity': 0})
            else:
                data.append({'order_id': key[0], 'sku_code': key[1], 'sku_desc': key[2],
                             'ship_quantity': value, 'return_quantity': value, 'damaged_quantity': 0})
        if not data:
            status = str(key[0]) + ' Order ID Already Returned'
            return HttpResponse(status)
    elif request_return_id:
        order_returns = OrderReturns.objects.filter(return_id=request_return_id, sku__user=user.id)
        if not order_returns:
            status = str(request_return_id) + ' is invalid'
        elif order_returns[0].status == '0':
            status = str(request_return_id) + ' is already confirmed'
        else:
            order_data = order_returns[0]
            order_obj = order_data.order
            if order_obj:
                order_quantity = order_data.order.quantity
            else:
                order_quantity = order_data.quantity
            order_id = order_obj.original_order_id
            if not order_id:
                order_id = order_obj.order_code + str(order_obj.order_id)
            data.append({'id': order_data.id, 'order_id': order_id, 'return_id': order_data.return_id,
                         'sku_code': order_data.sku.sku_code,
                         'sku_desc': order_data.sku.sku_desc, 'ship_quantity': order_quantity,
                         'return_quantity': order_data.quantity, 'damaged_quantity': order_data.damaged_quantity})
    else:
        status = 'AWB No. is Invalid'
    if not status:
        return HttpResponse(json.dumps(data, cls=DjangoJSONEncoder))
    return HttpResponse(status)


@csrf_exempt
@get_admin_user
def check_sku(request, user=''):
    data = {}
    sku_code = request.GET.get('sku_code')
    allocate_order = request.GET.get('allocate_order', 'false')
    check = False
    sku_id = check_and_return_mapping_id(sku_code, '', user, check)
    if not sku_id:
        try:
            sku_id = SKUMaster.objects.filter(Q(ean_number=sku_code) | Q(eannumbers__ean_number=sku_code),
                                              user=user.id)
        except:
            sku_id = ''
    if sku_id:
        sku_data = SKUMaster.objects.get(id=sku_id)
        if allocate_order == 'true':
            data = allocate_order_returns(user, sku_data, request)
        if not data:
            data = {"status": 'confirmed', 'sku_code': sku_data.sku_code, 'description': sku_data.sku_desc,
                    'order_id': '', 'ship_quantity': '', 'unit_price': '', 'return_quantity': 1,'cgst':'',
                    'sgst':'', 'igst':''}
        return HttpResponse(json.dumps(data))

    """
    sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
    if sku_master:
        return HttpResponse("confirmed")

    """
    return HttpResponse("%s not found" % sku_code)


@csrf_exempt
def get_returns_location(put_zone, request, user):
    user = user.id
    if put_zone == 'DAMAGED_ZONE':
        exclude_zone = ''
    else:
        exclude_zone = 'DAMAGED_ZONE'
    location1 = LocationMaster.objects.exclude(location__exact='', zone__zone=exclude_zone).filter(zone__zone=put_zone,
                                                                                                   fill_sequence__gt=0,
                                                                                                   max_capacity__gt=F(
                                                                                                       'filled_capacity'),
                                                                                                   zone__user=user,
                                                                                                   pallet_filled=0).order_by(
        'fill_sequence')
    location2 = LocationMaster.objects.exclude(location__exact='', zone__zone=exclude_zone).filter(zone__zone=put_zone,
                                                                                                   fill_sequence=0,
                                                                                                   max_capacity__gt=F(
                                                                                                       'filled_capacity'),
                                                                                                   pallet_filled=0,
                                                                                                   zone__user=user)
    location3 = LocationMaster.objects.exclude(
        Q(location__exact='') | Q(zone__zone__in=[put_zone, exclude_zone])).filter(
        max_capacity__gt=F('filled_capacity'), zone__user=user, pallet_filled=0)
    location4 = LocationMaster.objects.filter(zone__zone='DEFAULT', zone__user=user)
    location = list(chain(location1, location2, location3, location4))
    return location


def create_return_order(data, user):
    seller_order_ids = []
    status = ''
    user_obj = User.objects.get(id=user)
    sku_id = SKUMaster.objects.filter(sku_code=data['sku_code'], user=user)
    if not sku_id:
        return "", "SKU Code doesn't exist"
    return_details = copy.deepcopy(RETURN_DATA)
    user_obj = User.objects.get(id=user)
    if (data['return'] or data['damaged']) and sku_id:
        # order_details = OrderReturns.objects.filter(return_id = data['return_id'][i])
        quantity = data['return']
        if not quantity:
            quantity = data['damaged']
        return_type = ''
        if data.get('return_type', ''):
            return_type = data['return_type']
        marketplace = ''
        if data.get('marketplace', ''):
            marketplace = data['marketplace']
        sor_id = ''
        if data.get('sor_id', ''):
            sor_id = data['sor_id']

        if data.get('order_imei_id', ''):
            order_map_ins = OrderIMEIMapping.objects.get(id=data['order_imei_id'])
            data['order_id'] = order_map_ins.order.original_order_id
            if not data['order_id']:
                data['order_id'] = str(order_map_ins.order.order_code) + str(order_map_ins.order.order_id)

        return_details = {'return_id': '', 'return_date': datetime.datetime.now(), 'quantity': quantity,
                          'sku_id': sku_id[0].id, 'status': 1, 'marketplace': marketplace, 'return_type': return_type}
        if data.get('order_id', ''):
            order_detail = get_order_detail_objs(data['order_id'], user_obj,
                                                 search_params={'sku_id': sku_id[0].id, 'user': user})
            if order_detail:
                return_details['order_id'] = order_detail[0].id
                if order_detail[0].status == int(2):
                    order_detail[0].status = 4
                    order_detail[0].save()
                seller_order_id = get_returns_seller_order_id(return_details['order_id'], sku_id[0].sku_code, user_obj,
                                                              sor_id=sor_id)
                if seller_order_id:
                    return_details['seller_order_id'] = seller_order_id
                    seller_order_ids.append(seller_order_id)
        returns = OrderReturns(**return_details)
        returns.save()

        if not returns.return_id:
            returns.return_id = 'MN%s' % returns.id
        returns.save()
    else:
        status = 'Missing Required Fields'
    if not status:
        return returns.id, status, seller_order_ids
    else:
        return "", status, seller_order_ids


def create_default_zones(user, zone, location, sequence):
    try:
        new_zone, created = ZoneMaster.objects.get_or_create(user=user.id, zone=zone,
                                                             creation_date=datetime.datetime.now())
        locations, loc_created = LocationMaster.objects.get_or_create(location=location, max_capacity=100000,
                                                                      fill_sequence=sequence,
                                                                      pick_sequence=sequence, status=1,
                                                                      zone_id=new_zone.id,
                                                                      creation_date=datetime.datetime.now())
        log.info('%s created for user %s' % (zone, user.username))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(e)
        return []
    return [locations]


def get_return_segregation_locations(order_returns, batch_dict, data):
    picklist_exclude_zones = get_exclude_zones(User.objects.get(id=order_returns.sku.user))
    stock_objs = StockDetail.objects.exclude(Q(location__location__in=picklist_exclude_zones) |
                                             Q(batch_detail__mrp=batch_dict['mrp'])). \
                                    filter(sku__user=order_returns.sku.user,
                                            sku__sku_code=order_returns.sku.sku_code, quantity__gt=0)
    if stock_objs:
        put_zone = ZoneMaster.objects.filter(zone='Non Sellable Zone', user=order_returns.sku.user)
        if not put_zone:
            create_default_zones(user, 'Non Sellable Zone', 'Non-Sellable1', 10001)
            put_zone = ZoneMaster.objects.filter(zone='Non Sellable Zone', user=order_returns.sku.user)[0]
        else:
            put_zone = put_zone[0]
        data['put_zone'] = put_zone.zone
    return data

def save_return_locations(order_returns, all_data, damaged_quantity, request, user, is_rto=False,
                          batch_dict=None):
    order_returns = order_returns[0]
    zone = order_returns.sku.zone
    if zone:
        put_zone = zone.zone
    else:
        put_zone = 'DEFAULT'

    all_data.append({'received_quantity': float(order_returns.quantity), 'put_zone': put_zone})
    if damaged_quantity:
        all_data.append({'received_quantity': float(damaged_quantity), 'put_zone': 'DAMAGED_ZONE'})
        all_data[0]['received_quantity'] = all_data[0]['received_quantity'] - float(damaged_quantity)
    for data in all_data:
        temp_dict = {'received_quantity': float(order_returns.quantity), 'data': "", 'user': user.id, 'pallet_data': '',
                     'pallet_number': '',
                     'wms_code': order_returns.sku.wms_code, 'sku_group': order_returns.sku.sku_group,
                     'sku': order_returns.sku}
        if batch_dict and not data['put_zone'] == 'DAMAGED_ZONE':
            data = get_return_segregation_locations(order_returns, batch_dict, data)
        if is_rto and not data['put_zone'] == 'DAMAGED_ZONE':
            locations = LocationMaster.objects.filter(zone__user=user.id, zone__zone='RTO_ZONE')
            if not locations:
                locations = create_default_zones(user, 'RTO_ZONE', 'RTO-R1', 10000)
        else:
            locations = get_purchaseorder_locations(data['put_zone'], temp_dict)

        if not locations:
            return 'Locations not Found'
        received_quantity = data['received_quantity']
        if not received_quantity:
            continue
        for location in locations:
            total_quantity = POLocation.objects.filter(location_id=location.id, status=1,
                                                       location__zone__user=user.id).aggregate(Sum('quantity'))[
                'quantity__sum']
            if not total_quantity:
                total_quantity = 0
            filled_capacity = StockDetail.objects.filter(location_id=location.id, quantity__gt=0,
                                                         sku__user=user.id).aggregate(Sum('quantity'))['quantity__sum']
            if not filled_capacity:
                filled_capacity = 0
            filled_capacity = float(total_quantity) + float(filled_capacity)
            remaining_capacity = float(location.max_capacity) - float(filled_capacity)
            if location.zone.zone in ['DEFAULT', 'DAMAGED_ZONE', 'QC_ZONE', 'Non Sellable Zone']:
                remaining_capacity = received_quantity
            if remaining_capacity <= 0:
                continue
            elif remaining_capacity < received_quantity:
                location_quantity = remaining_capacity
                received_quantity -= remaining_capacity
            elif remaining_capacity >= received_quantity:
                location_quantity = received_quantity
                received_quantity = 0
            return_location = ReturnsLocation.objects.filter(returns_id=order_returns.id, location_id=location.id,
                                                             status=1)
            if not return_location:
                location_data = {'returns_id': order_returns.id, 'location_id': location.id,
                                 'quantity': location_quantity, 'status': 1}
                returns_data = ReturnsLocation(**location_data)
                returns_data.save()
                if batch_dict:
                    batch_dict1 = copy.deepcopy(batch_dict)
                    batch_dict1['transact_id'] = returns_data.id
                    batch_dict1['transact_type'] = 'return_loc'
                    create_update_batch_data(batch_dict1)
            else:
                return_location = return_location[0]
                setattr(return_location, 'quantity', float(return_location.quantity) + location_quantity)
                return_location.save()
                if batch_dict:
                    batch_dict1 = copy.deepcopy(batch_dict)
                    batch_dict1['transact_id'] = return_location.id
                    batch_dict1['transact_type'] = 'return_loc'
                    create_update_batch_data(batch_dict1)
            if received_quantity == 0:
                order_returns.status = 0
                order_returns.save()
                break
    return 'Success'


def save_return_imeis(user, returns, status, imei_numbers):
    imei_numbers = imei_numbers.split(',')
    for imei in imei_numbers:
        if not imei:
            continue
        reason = ''
        if status == 'damaged' and '<<>>' in imei:
            dam_imei = imei.split('<<>>')
            imei = dam_imei[0]
            reason = dam_imei[1]
        order_imei = OrderIMEIMapping.objects.filter(po_imei__imei_number=imei, sku__user=user.id, status=1)
        if not order_imei:
            continue
        elif order_imei:
            order_imei[0].status = 0
            order_imei[0].save()
            po_imei = order_imei[0].po_imei
            po_imei.status = 1
            po_imei.save()

        returns_imei = ReturnsIMEIMapping.objects.filter(order_return__sku__user=user.id,
                                                         order_imei_id=order_imei[0].id, status=1)
        if not returns_imei:
            ReturnsIMEIMapping.objects.create(order_imei_id=order_imei[0].id, status=status, reason=reason,
                                              creation_date=datetime.datetime.now(), order_return_id=returns.id)


def group_sales_return_data(data_dict, return_process):
    """ Group Sales Return Data """

    returns_dict = {}
    grouping_dict = {'order_id': '[str(data_dict["order_id"][ind]), str(data_dict["sku_code"][ind])]',
                     'sku_code': 'data_dict["sku_code"][ind]', 'return_id': 'data_dict["id"][ind]',
                     'scan_imei': 'data_dict["id"][ind]',
                     'scan_awb': '[str(data_dict["order_id"][ind]), str(data_dict["sku_code"][ind])]'}
    grouping_key = grouping_dict[return_process]
    zero_index_list = ['scan_order_id', 'return_process', 'return_type']
    number_fields = ['return', 'damaged', 'mrp']

    for ind in range(0, len(data_dict['sku_code'])):
        temp_key = ':'.join(eval(grouping_key))
        if not temp_key:
            temp_key = ':'.join(eval(grouping_dict['order_id']))
        if returns_dict.get(temp_key, ''):
            # Adding quantity and reasons if grouping data exists

            if not data_dict['return'][ind]:
                data_dict['return'][ind] = 0
            if not data_dict['damaged'][ind]:
                data_dict['damaged'][ind] = 0
            returns_dict[temp_key]['return'] = int(returns_dict[temp_key]['return']) + int(data_dict['return'][ind])
            returns_dict[temp_key]['damaged'] = int(returns_dict[temp_key]['damaged']) + int(data_dict['damaged'][ind])
            returns_dict[temp_key]['reason'].append({'return': int(data_dict['return'][ind]),
                                                     'damaged': int(data_dict['damaged'][ind]),
                                                     'reason': data_dict['reason'][ind]})
            continue

        # Creating the Returns Dictionary
        for key, value in data_dict.iteritems():
            if key in ['reason', 'return_imei']:
                continue
            returns_dict.setdefault(temp_key, {})
            returns_dict[temp_key].setdefault('reason', [])
            if key in zero_index_list:
                returns_dict[temp_key][key] = data_dict[key][0]
            else:
                if key in number_fields and not data_dict[key][ind]:
                    data_dict[key][ind] = 0
                returns_dict[temp_key][key] = data_dict[key][ind]
        if data_dict['reason'][ind]:
            returns_dict[temp_key]['reason'].append({'return': int(returns_dict[temp_key]['return']),
                                                     'damaged': int(returns_dict[temp_key]['damaged']),
                                                     'reason': data_dict['reason'][ind]})

    return returns_dict.values()


def update_return_reasons(order_return, reasons_list=[]):
    """ Creating Multiple reasons For Sales Return """

    for reason_dict in reasons_list:
        if reason_dict.get('damaged', 0):
            OrderReturnReasons.objects.create(order_return_id=order_return.id, quantity=reason_dict['damaged'],
                                              status='damaged', reason=reason_dict['reason'],
                                              creation_date=datetime.datetime.now())
            reason_dict['return'] -= reason_dict['damaged']
        if reason_dict['return']:
            OrderReturnReasons.objects.create(order_return_id=order_return.id, quantity=reason_dict['return'],
                                              status='return', reason=reason_dict['reason'],
                                              creation_date=datetime.datetime.now())


@csrf_exempt
@login_required
@get_admin_user
def confirm_sales_return(request, user=''):
    """ Creating and Confirming the Sales Returns"""

    data_dict = dict(request.POST.iterlists())
    return_type = request.POST.get('return_type', '')
    return_process = request.POST.get('return_process')
    mp_return_data = {}
    created_return_ids = []
    log.info('Request params for Confirm Sales Return for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        # Group the Input Data Based on the Group Type
        final_data_list = group_sales_return_data(data_dict, return_process)
        for return_dict in final_data_list:
            all_data = []
            check_seller_order = True
            if not return_dict['id']:
                return_dict['id'], status, seller_order_ids = create_return_order(return_dict, user.id)
                if seller_order_ids:
                    imeis = (return_dict['returns_imeis']).split(',')
                    for imei in imeis:
                        mp_return_data.setdefault(seller_order_ids[0], {}).setdefault(
                            'imeis', []).append(imei)
                    check_seller_order = False
                if status:
                    return HttpResponse(status)

            order_returns = OrderReturns.objects.filter(id=return_dict['id'], status=1)
            if not order_returns:
                continue
            if order_returns[0].order:
                created_return_ids.append(order_returns[0].return_id)
            if return_dict.get('reason', ''):
                update_return_reasons(order_returns[0], return_dict['reason'])
            if data_dict.get('returns_imeis', ''):
                save_return_imeis(user, order_returns[0], 'return', return_dict['returns_imeis'])
                if check_seller_order and order_returns[0].seller_order:
                    imeis = (return_dict['returns_imeis']).split(',')
                    for imei in imeis:
                        mp_return_data.setdefault(order_returns[0].seller_order_id, {}).setdefault(
                            'imeis', []).append(imei)
            if data_dict.get('damaged_imeis_reason', ''):
                save_return_imeis(user, order_returns[0], 'damaged', return_dict['damaged_imeis_reason'])
                if check_seller_order and order_returns[0].seller_order:
                    imeis = (return_dict['damaged_imeis_reason']).split(',')
                    for imei in imeis:
                        imei = imei.split('<<>>')
                        if imei:
                            imei = imei[0]
                            mp_return_data.setdefault(order_returns[0].seller_order_id, {}).setdefault(
                                'imeis', []).append(imei)
            return_loc_params = {'order_returns': order_returns, 'all_data': all_data,
                                 'damaged_quantity': return_dict['damaged'],
                                 'request': request, 'user': user}
            if return_type:
                return_type = RETURNS_TYPE_MAPPING.get(return_type.lower(), '')
            if return_type == 'rto':
                return_loc_params.update({'is_rto': True})
            if return_dict.get('mrp') or return_dict.get('manufactured_date') or \
                    return_dict.get('expiry_date', ''):
                batch_dict = {'mrp': float(return_dict.get('mrp', 0)),
                              'manufactured_date': return_dict.get('manufactured_date', ''),
                              'expiry_date': return_dict.get('expiry_date', ''),
                              'batch_no': ''}
                return_loc_params['batch_dict'] = batch_dict
            locations_status = save_return_locations(**return_loc_params)
            if not locations_status == 'Success':
                return HttpResponse(locations_status)
            else:
                total_quantity = int(return_dict['return'])
                if total_quantity:
                    returns_order_tracking(order_returns[0], user, total_quantity, 'returned', '')
        if user.userprofile.user_type == 'marketplace_user':
            check_and_update_order_status_data(mp_return_data, user, status='RETURNED')
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Confirm Sales return for ' + str(user.username) + ' is failed for ' + str(
            request.POST.dict()) + ' error statement is ' + str(e))

    created_return_ids = list(set(created_return_ids))
    if created_return_ids:
        return_sales_print = []
        for created_return_id in created_return_ids:
            return_json = get_sales_return_print_json(created_return_id, user)
            return_sales_print.append(return_json)

        return render(request, 'templates/toggle/sales_return_print.html',
            {'show_data_invoice': return_sales_print})
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def get_received_orders(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    all_data = {}
    temp = get_misc_value('pallet_switch', user.id)
    headers = ('WMS CODE', 'Location', 'Pallet Number', 'Original Quantity', 'Putaway Quantity', '')
    data = {}
    sku_total_quantities = OrderedDict()
    supplier_id = request.GET['supplier_id']
    purchase_orders = PurchaseOrder.objects.filter(order_id=supplier_id, open_po__sku__user=user.id,
                                                   open_po__sku_id__in=sku_master_ids). \
        exclude(status__in=['', 'confirmed-putaway'])
    if not purchase_orders:
        st_orders = STPurchaseOrder.objects.filter(po__order_id=supplier_id, open_st__sku__user=user.id,
                                                   open_st__sku_id__in=sku_master_ids). \
            exclude(po__status__in=['', 'confirmed-putaway', 'stock-transfer']).values_list('po_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=st_orders)
    if not purchase_orders:
        rw_orders = RWPurchase.objects.filter(purchase_order__order_id=supplier_id, rwo__vendor__user=user.id,
                                              rwo__job_order__product_code_id__in=sku_master_ids).\
                                        exclude(purchase_order__status__in=['', 'confirmed-putaway']).\
            values_list('purchase_order_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=rw_orders)
    for order in purchase_orders:
        order_id = order.id
        order_data = get_purchase_order_data(order)
        po_location = POLocation.objects.filter(purchase_order_id=order_id, status=1, location__zone__user=user.id)
        total_sku_quantity = po_location.aggregate(Sum('quantity'))['quantity__sum']
        if not total_sku_quantity:
            total_sku_quantity = 0
        if order_data['wms_code'] in sku_total_quantities.keys():
            sku_total_quantities[order_data['wms_code']] += float(total_sku_quantity)
        else:
            sku_total_quantities[order_data['wms_code']] = float(total_sku_quantity)
        for location in po_location:
            batch_dict = get_batch_dict(location.id, 'po_loc')
            pallet_number = ''
            if temp == "true":
                pallet_mapping = PalletMapping.objects.filter(po_location_id=location.id, status=1)
                if pallet_mapping:
                    pallet_number = pallet_mapping[0].pallet_detail.pallet_code
                    cond = (pallet_number, location.location.location)
                    all_data.setdefault(cond, [0, '', 0, '', []])
                    if all_data[cond] == [0, '', 0, '', []]:
                        all_data[cond] = [all_data[cond][0] + float(location.quantity), order_data['wms_code'],
                                          float(location.quantity), location.location.fill_sequence,
                                          [{'orig_id': location.id,
                                            'orig_quantity': location.quantity}], order_data['unit'],
                                          order_data['sku_desc'],
                                          order_data['load_unit_handle']]
                    else:
                        if all_data[cond][2] < float(location.quantity):
                            all_data[cond][2] = float(location.quantity)
                            all_data[cond][1] = order_data['wms_code']
                        all_data[cond][0] += float(location.quantity)
                        all_data[cond][3] = location.location.fill_sequence
                        all_data[cond][4].append({'orig_id': location.id, 'orig_quantity': location.quantity})
            if temp == 'false' or (temp == 'true' and not pallet_mapping):
                data[location.id] = {'wms_code': order_data['wms_code'], 'sku_desc': order_data['sku_desc'],
                                     'location': location.location.location,
                                     'original_quantity': location.quantity, 'quantity': location.quantity,
                                     'fill_sequence': location.location.fill_sequence, 'id': location.id,
                                     'pallet_number': pallet_number, 'unit': order_data['unit'],
                                     'load_unit_handle': order_data['load_unit_handle'],
                                     'sub_data': [{'loc': location.location.location, 'quantity': location.quantity}]}
                data[location.id].update(batch_dict)

    if temp == 'true' and all_data:
        for key, value in all_data.iteritems():
            data[key[0]] = {'wms_code': value[1], 'location': key[1], 'original_quantity': value[0],
                            'quantity': value[0],
                            'fill_sequence': value[3], 'id': '', 'pallet_number': key[0], 'pallet_group_data': value[4],
                            'unit': value[5], 'load_unit_handle': value[7],
                            'sub_data': [{'loc': key[1], 'quantity': value[0]}], 'sku_desc': value[6]}

    data_list = data.values()
    data_list.sort(key=lambda x: x['fill_sequence'])
    po_number = '%s%s_%s' % (order.prefix, str(order.po_date).split(' ')[0].replace('-', ''), order.order_id)
    return HttpResponse(
        json.dumps({'data': data_list, 'po_number': po_number, 'order_id': order_id, 'user': request.user.id,
                    'sku_total_quantities': sku_total_quantities}))


def validate_putaway(all_data, user):
    status = ''
    back_order = 'false'
    misc_data = MiscDetail.objects.filter(user=user.id, misc_type='back_order')
    if misc_data:
        back_order = misc_data[0].misc_value

    for key, value in all_data.iteritems():
        if not key[1]:
            status = 'Location is Empty, Enter Location'
        if key[1]:
            loc = LocationMaster.objects.filter(location=key[1], zone__user=user.id)
            if loc:
                loc = LocationMaster.objects.get(location=key[1], zone__user=user.id)
                if 'Inbound' in loc.lock_status or 'Inbound and Outbound' in loc.lock_status:
                    status = 'Entered Location is locked for %s operations' % loc.lock_status

                if key[0]:
                    data = POLocation.objects.get(id=key[0], location__zone__user=user.id)
                    order_data = get_purchase_order_data(data.purchase_order)

                    if (float(data.purchase_order.received_quantity) - value) < 0:
                        status = 'Putaway quantity should be less than the Received Quantity'

                if back_order == "true":
                    sku_code = key[4]
                    pick_res_quantity = PicklistLocation.objects.filter(picklist__order__sku__sku_code=sku_code,
                                                                        stock__location__zone__zone="BAY_AREA",
                                                                        status=1, picklist__status__icontains='open',
                                                                        picklist__order__user=user.id). \
                        aggregate(Sum('reserved'))['reserved__sum']
                    po_loc_quantity = \
                    POLocation.objects.filter(purchase_order__open_po__sku__sku_code=sku_code, status=1,
                                              purchase_order__open_po__sku__user=user.id). \
                        aggregate(Sum('quantity'))['quantity__sum']
                    if not pick_res_quantity:
                        pick_res_quantity = 0
                    if not po_loc_quantity:
                        po_loc_quantity = 0

                    diff = po_loc_quantity - pick_res_quantity
                    if diff and diff < value:
                        status = 'Bay Area Stock %s is reserved for %s in Picklist.You cannot putaway this stock.' % (
                        pick_res_quantity, sku_code)

            else:
                status = 'Enter Valid Location'
    return status


def consume_bayarea_stock(sku_code, zone, quantity, user):
    back_order = 'false'
    data = MiscDetail.objects.filter(user=user, misc_type='back_order')
    if data:
        back_order = data[0].misc_value

    location_master = LocationMaster.objects.filter(zone__zone=zone, zone__user=user)
    if not location_master or back_order == 'false':
        return
    location = location_master[0].location
    stock_detail = StockDetail.objects.filter(sku__sku_code=sku_code, location__location=location, sku__user=user)
    if stock_detail:
        stock = stock_detail[0]
        if float(stock.quantity) > quantity:
            setattr(stock, 'quantity', float(stock.quantity) - quantity)
            stock.save()
        else:
            setattr(stock, 'quantity', 0)
            stock.save()
        update_filled_capacity([stock.location.location], user_id)


def putaway_location(data, value, exc_loc, user, order_id, po_id):
    diff_quan = 0
    if float(data.quantity) >= float(value):
        diff_quan = float(data.quantity) - float(value)
        data.quantity = diff_quan
    if diff_quan == 0:
        data.status = 0
    if not data.location_id == exc_loc:
        if float(data.original_quantity) - value >= 0:
            data.original_quantity = float(data.original_quantity) - value
        filter_params = {'location_id': exc_loc, 'location__zone__user': user.id, order_id: po_id}
        po_obj = POLocation.objects.filter(**filter_params)
        if po_obj:
            add_po_quantity = float(po_obj[0].quantity) + float(value)
            po_obj[0].original_quantity = add_po_quantity
            po_obj[0].quantity = add_po_quantity
            po_obj[0].status = 0
            po_obj[0].save()
        else:
            location_data = {order_id: po_id, 'location_id': exc_loc, 'quantity': 0, 'original_quantity': value,
                             'status': 0,
                             'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}
            loc = POLocation(**location_data)
            loc.save()
    data.save()


def create_update_seller_stock(data, value, user, stock_obj, exc_loc, use_value=False):
    if not data.purchase_order.open_po:
        return
    seller_stock_update_details = []
    received_quantity = float(stock_obj.quantity)
    if use_value:
        received_quantity = value
    seller_po_summaries = SellerPOSummary.objects.filter(seller_po__seller__user=user.id,
                                                         seller_po__open_po_id=data.purchase_order.open_po_id,
                                                         putaway_quantity__gt=0, location_id=exc_loc)
    for sell_summary in seller_po_summaries:
        if received_quantity <= 0:
            continue
        if received_quantity < float(sell_summary.putaway_quantity):
            sell_quan = float(received_quantity)
            sell_summary.putaway_quantity = float(sell_summary.putaway_quantity) - float(received_quantity)
        elif received_quantity >= float(sell_summary.putaway_quantity):
            sell_quan = float(sell_summary.putaway_quantity)
            received_quantity -= float(sell_summary.putaway_quantity)
            sell_summary.putaway_quantity = 0
        sell_summary.save()
        seller_stock = SellerStock.objects.filter(seller_id=sell_summary.seller_po.seller_id, stock_id=stock_obj.id,
                                                  stock__sku__user=user.id, seller_po_summary_id=sell_summary.id)
        if not seller_stock:
            seller_stock = SellerStock.objects.create(seller_id=sell_summary.seller_po.seller_id, quantity=sell_quan,
                                                      seller_po_summary_id=sell_summary.id,
                                                      creation_date=datetime.datetime.now(), status=1,
                                                      stock_id=stock_obj.id)
        else:
            seller_stock[0].quantity = float(seller_stock[0].quantity) + float(sell_quan)
            seller_stock[0].save()
        if isinstance(seller_stock, QuerySet):
            seller_stock = seller_stock[0]

        if seller_stock:
            if seller_stock.stock.location.zone.zone not in ['DAMAGED_ZONE']:
                seller_stock_update_details.append({
                    'sku_code': str(seller_stock.stock.sku.sku_code),
                    'seller_id': int(seller_stock.seller.seller_id),
                    'quantity': int(value)
                })
    return seller_stock_update_details


@csrf_exempt
@login_required
@get_admin_user
def putaway_data(request, user=''):
    purchase_order_id = ''
    diff_quan = 0
    all_data = {}
    stock_detail = ''
    stock_data = ''
    putaway_stock_data = {}
    try:
        myDict = dict(request.POST.iterlists())
        sku_codes = []
        marketplace_data = []
        mod_locations = []
        for i in range(0, len(myDict['id'])):
            po_data = ''
            if myDict['orig_data'][i]:
                myDict['orig_data'][i] = eval(myDict['orig_data'][i])
                for orig_data in myDict['orig_data'][i]:
                    cond = (orig_data['orig_id'], myDict['loc'][i], myDict['po_id'][i], myDict['orig_loc_id'][i],
                            myDict['wms_code'][i])
                    all_data.setdefault(cond, 0)
                    all_data[cond] += float(orig_data['orig_quantity'])
            else:
                cond = (
                myDict['id'][i], myDict['loc'][i], myDict['po_id'][i], myDict['orig_loc_id'][i], myDict['wms_code'][i])
                all_data.setdefault(cond, 0)
                if not myDict['quantity'][i]:
                    myDict['quantity'][i] = 0
                all_data[cond] += float(myDict['quantity'][i])

        all_data = OrderedDict(sorted(all_data.items(), reverse=True))
        status = validate_putaway(all_data, user)
        if status:
            return HttpResponse(status)
        for key, value in all_data.iteritems():
            loc = LocationMaster.objects.get(location=key[1], zone__user=user.id)
            loc1 = loc
            exc_loc = loc.id
            if key[0]:
                po_loc_data = POLocation.objects.filter(id=key[0], location__zone__user=user.id)
                purchase_order_id = po_loc_data[0].purchase_order.order_id
            else:
                sku_master, sku_master_ids = get_sku_master(user, request.user)
                results = PurchaseOrder.objects.filter(open_po__sku__user=user.id, open_po__sku_id__in=sku_master_ids,
                                                       order_id=purchase_order_id,
                                                       open_po__sku__wms_code=key[4]).exclude(status__in=['',
                                                                                                          'confirmed-putaway']).values_list(
                    'id', flat=True).distinct()
                stock_results = STPurchaseOrder.objects.exclude(
                    po__status__in=['', 'confirmed-putaway', 'stock-transfer']). \
                    filter(open_st__sku__user=user.id, open_st__sku_id__in=sku_master_ids,
                           open_st__sku__wms_code=key[4], po__order_id=purchase_order_id). \
                    values_list('po_id', flat=True).distinct()
                rw_results = RWPurchase.objects.filter(rwo__job_order__product_code_id__in=sku_master_ids,
                                                       rwo__job_order__product_code__wms_code=key[4]).exclude(
                    purchase_order__status__in=['',
                                                'confirmed-putaway', 'stock-transfer'],
                    purchase_order__order_id=purchase_order_id). \
                    filter(rwo__vendor__user=user.id).values_list('purchase_order_id', flat=True)
                results = list(chain(results, stock_results, rw_results))
                po_loc_data = POLocation.objects.filter(location__zone__user=user.id, purchase_order_id__in=results)

            old_loc = ""
            if po_loc_data:
                old_loc = po_loc_data[0].location_id

            if not value:
                continue
            count = value
            for data in po_loc_data:
                if not count:
                    break
                batch_obj = BatchDetail.objects.filter(transact_id=data.id, transact_type='po_loc')
                if float(data.quantity) < count:
                    value = count - float(data.quantity)
                    count -= float(data.quantity)
                else:
                    value = count
                    count = 0
                order_data = get_purchase_order_data(data.purchase_order)
                putaway_location(data, value, exc_loc, user, 'purchase_order_id', data.purchase_order_id)
                stock_check_params = {'location_id': exc_loc, 'receipt_number':data.purchase_order.order_id,
                                     'sku_id': order_data['sku_id'], 'sku__user': user.id,
                                      'unit_price': order_data['price']}
                if batch_obj:
                    stock_check_params['batch_detail_id'] = batch_obj[0].id
                    stock_check_params['unit_price'] = batch_obj[0].buy_price
                pallet_mapping = PalletMapping.objects.filter(po_location_id=data.id, status=1)
                if pallet_mapping:
                    stock_check_params['pallet_detail_id'] = pallet_mapping[0].pallet_detail.id
                stock_data = StockDetail.objects.filter(**stock_check_params)
                if pallet_mapping:
                    setattr(loc1, 'pallet_filled', float(loc1.pallet_filled) + 1)
                else:
                    mod_locations.append(loc1.location)
                if loc1.pallet_filled > loc1.pallet_capacity:
                    setattr(loc1, 'pallet_capacity', loc1.pallet_filled)
                loc1.save()
                if stock_data:
                    stock_data = stock_data[0]
                    add_quan = float(stock_data.quantity) + float(value)
                    setattr(stock_data, 'quantity', add_quan)
                    if pallet_mapping:
                        pallet_detail = pallet_mapping[0].pallet_detail
                        setattr(stock_data, 'pallet_detail_id', pallet_detail.id)
                    stock_data.save()

                    # SKU Stats
                    save_sku_stats(user, stock_data.sku_id, data.id, 'po', float(value))
                    update_details = create_update_seller_stock(data, value, user, stock_data, old_loc, use_value=True)
                    if update_details:
                        marketplace_data += update_details

                    # Collecting data for auto stock allocation
                    putaway_stock_data.setdefault(stock_data.sku_id, [])
                    putaway_stock_data[stock_data.sku_id].append(data.purchase_order_id)

                else:
                    record_data = {'location_id': exc_loc, 'receipt_number': data.purchase_order.order_id,
                                   'receipt_date': str(data.purchase_order.creation_date).split('+')[0],
                                   'sku_id': order_data['sku_id'],
                                   'quantity': value, 'status': 1, 'receipt_type': 'purchase order',
                                   'creation_date': datetime.datetime.now(),
                                   'updation_date': datetime.datetime.now(), 'unit_price': order_data['price']}
                    if batch_obj:
                        record_data['batch_detail_id'] = batch_obj[0].id
                        record_data['unit_price'] = batch_obj[0].buy_price
                    if pallet_mapping:
                        record_data['pallet_detail_id'] = pallet_mapping[0].pallet_detail.id
                        pallet_mapping[0].status = 0
                        pallet_mapping[0].save()
                    stock_detail = StockDetail(**record_data)
                    stock_detail.save()

                    # SKU Stats
                    save_sku_stats(user, stock_detail.sku_id, data.id, 'PO', float(value))
                    # Collecting data for auto stock allocation
                    putaway_stock_data.setdefault(stock_detail.sku_id, [])
                    putaway_stock_data[stock_detail.sku_id].append(data.purchase_order_id)

                    update_details = create_update_seller_stock(data, value, user, stock_detail, old_loc)
                    if update_details:
                        marketplace_data += update_details
                consume_bayarea_stock(order_data['sku_code'], "BAY_AREA", float(value), user.id)

                if order_data['sku_code'] not in sku_codes:
                    sku_codes.append(order_data['sku_code'])

                putaway_quantity = POLocation.objects.filter(purchase_order_id=data.purchase_order_id,
                                                             location__zone__user=user.id, status=0). \
                    aggregate(Sum('original_quantity'))['original_quantity__sum']
                if not putaway_quantity:
                    putaway_quantity = 0
                if (float(order_data['order_quantity']) <= float(data.purchase_order.received_quantity)) and float(
                        data.purchase_order.received_quantity) - float(putaway_quantity) <= 0:
                    data.purchase_order.status = 'confirmed-putaway'

                data.purchase_order.save()
        if user.userprofile.user_type == 'marketplace_user':
            check_and_update_marketplace_stock(marketplace_data, user)
        else:
            check_and_update_stock(sku_codes, user)

        update_filled_capacity(list(set(mod_locations)), user.id)

        # Auto Allocate Stock
        order_allocate_stock(request, user, stock_data=putaway_stock_data, mapping_type='PO')

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Putaway Confirmation failed for ' + str(request.POST.dict()) + ' error statement is ' + str(e))
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def quality_check_data(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    headers = ('WMS CODE', 'Location', 'Quantity', 'Accepted Quantity', 'Rejected Quantity', 'Reason')
    data = []
    stock_results = []
    rw_orders = []
    po_reference = ''
    order_id = request.GET['order_id']
    purchase_orders = PurchaseOrder.objects.filter(order_id=order_id, open_po__sku__user=user.id,
                                                   open_po__sku_id__in=sku_master_ids)
    if not purchase_orders:
        purchase_orders = []
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['confirmed-putaway', 'stock-transfer']). \
            filter(open_st__sku__user=user.id, open_st__sku_id__in=sku_master_ids). \
            values_list('po_id', flat=True)
        qc_results = QualityCheck.objects.filter(purchase_order_id__in=stock_results, status='qc_pending',
                                                 po_location__location__zone__user=user.id)
        for qc in qc_results:
            purchase_orders.append(qc.purchase_order)
    if not purchase_orders:
        rw_orders = RWPurchase.objects.filter(purchase_order__order_id=order_id, rwo__vendor__user=user.id,
                                              rwo__job_order__product_code_id__in=sku_master_ids). \
            values_list('purchase_order_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=rw_orders)
    for order in purchase_orders:
        quality_check = QualityCheck.objects.filter(Q(purchase_order__open_po__sku_id__in=sku_master_ids) |
                                                    Q(purchase_order_id__in=stock_results) |
                                                    Q(purchase_order_id__in=rw_orders),
                                                    purchase_order_id=order.id, status='qc_pending',
                                                    po_location__location__zone__user=user.id)
        for qc_data in quality_check:
            batch_dict = get_batch_dict(qc_data.po_location_id, 'po_loc')
            purchase_data = get_purchase_order_data(qc_data.purchase_order)
            po_reference = '%s%s_%s' % (
            qc_data.purchase_order.prefix, str(qc_data.purchase_order.creation_date).split(' ')[0]. \
            replace('-', ''), qc_data.purchase_order.order_id)
            data.append({'id': qc_data.id, 'wms_code': purchase_data['wms_code'],
                         'location': qc_data.po_location.location.location,
                         'quantity': get_decimal_limit(user.id, qc_data.putaway_quantity),
                         'unit': purchase_data['unit'],
                         'accepted_quantity': get_decimal_limit(user.id, qc_data.accepted_quantity),
                         'rejected_quantity': get_decimal_limit(user.id, qc_data.rejected_quantity),
                         'batch_no': batch_dict.get('batch_no', ''), 'mrp': batch_dict.get('mrp', 0),
                         'po_unit': batch_dict.get('buy_price', ''),
                         'exp_date': batch_dict.get('expiry_date', ''),
                         'mfg_date': batch_dict.get('manufactured_date', '')})

    return HttpResponse(json.dumps({'data': data, 'po_reference': po_reference, 'order_id': order_id}))


@csrf_exempt
@get_admin_user
def check_wms_qc(request, user=''):
    qc_data = []
    sku_data = {}
    image = ''
    use_imei = 'false'
    data = MiscDetail.objects.filter(user=user.id, misc_type='use_imei')
    if data:
        use_imei = data[0].misc_value

    is_receive_po = request.POST.get('receive_po', False)
    for key, value in request.POST.iteritems():
        if key == 'receive_po':
            continue
        order_id = ''
        if value and '_' in value:
            value = value.split('_')[-1]
            order_id = value
        ean_number = ''
        try:
            ean_number = int(key)
        except:
            pass
        if not is_receive_po:
            sku_query_dict = {'purchase_order__open_po__sku__wms_code': key}
            if ean_number:
                sku_query_dict['purchase_order__open_po__sku__ean_number'] = ean_number
            sku_query = get_dictionary_query(sku_query_dict)
            filter_params = {'po_location__status': 2,
                             'po_location__location__zone__user': user.id, 'status': 'qc_pending'}
            if order_id:
                filter_params['purchase_order__order_id'] = value
            model_name = QualityCheck
            field_mapping = {'purchase_order': 'data.purchase_order', 'prefix': 'data.purchase_order.prefix',
                             'creation_date': 'data.purchase_order.creation_date',
                             'order_id': 'data.purchase_order.order_id',
                             'quantity': 'data.po_location.quantity', 'accepted_quantity': 'data.accepted_quantity',
                             'rejected_quantity': 'data.rejected_quantity'}
        else:
            sku_query_dict = {'open_po__sku__wms_code': key}
            if ean_number:
                sku_query_dict['open_po__sku__ean_number'] = ean_number
            sku_query = get_dictionary_query(sku_query_dict)
            filter_params = {'open_po__sku__wms_code': key, 'open_po__sku__user': user.id,
                             'open_po__order_quantity__gt': F('received_quantity')}
            if order_id:
                filter_params['order_id'] = value
            model_name = PurchaseOrder
            field_mapping = {'purchase_order': 'data', 'prefix': 'data.prefix', 'creation_date': 'data.creation_date',
                             'order_id': 'data.order_id',
                             'quantity': '(data.open_po.order_quantity) - (data.received_quantity)',
                             'accepted_quantity': '0', 'rejected_quantity': '0'}
        st_purchase = STPurchaseOrder.objects.exclude(po__status__in=['confirmed-putaway', 'stock-transfer']). \
            filter(po__order_id=value, open_st__sku__wms_code=key, open_st__sku__user=user.id). \
            values_list('po_id', flat=True)
        if st_purchase and not is_receive_po:
            del filter_params['purchase_order__open_po__sku__wms_code']
            filter_params['purchase_order_id__in'] = st_purchase
        elif st_purchase:
            del filter_params['open_po__sku__wms_code']
            filter_params['id__in'] = st_purchase

        model_data = model_name.objects.filter(sku_query, **filter_params)
        if not model_data:
            return HttpResponse("WMS Code not found")
        for data in model_data:
            purchase_data = get_purchase_order_data(eval(field_mapping['purchase_order']))
            sku = purchase_data['sku']
            image = sku.image_url
            po_reference = '%s%s_%s' % (eval(field_mapping['prefix']), str(eval(field_mapping['creation_date'])). \
                                        split(' ')[0].replace('-', ''), eval(field_mapping['order_id']))
            qc_data.append({'id': data.id, 'order_id': po_reference,
                            'quantity': eval(field_mapping['quantity']),
                            'accepted_quantity': eval(field_mapping['accepted_quantity']),
                            'rejected_quantity': eval(field_mapping['rejected_quantity'])})
            sku_data = OrderedDict((('SKU Code', sku.sku_code), ('Product Description', sku.sku_desc),
                                    ('SKU Brand', sku.sku_brand), ('SKU Category', sku.sku_category),
                                    ('SKU Class', sku.sku_class),
                                    ('Color', sku.color)))
    return HttpResponse(json.dumps({'data_dict': qc_data, 'sku_data': sku_data, 'image': image,
                                    'options': REJECT_REASONS, 'use_imei': use_imei}))


def get_seller_received_list(data, user):
    seller_po_summary = SellerPOSummary.objects.filter(Q(location_id__isnull=True) | Q(location__zone__zone='QC_ZONE'),
                                                       seller_po__seller__user=user.id, putaway_quantity__gt=0,
                                                       seller_po__open_po_id=data.open_po_id)
    seller_received_list = []
    for summary in seller_po_summary:
        seller_received_list.append({'seller_id': summary.seller_po.seller_id, 'sku': summary.seller_po.open_po.sku,
                                     'quantity': summary.putaway_quantity, 'id': summary.id})
    return seller_received_list


def get_quality_check_seller(seller_received_list, temp_dict, purchase_data):
    seller_summary_dict = []
    temp_received_quantity = temp_dict['received_quantity']
    for index, seller_received in enumerate(seller_received_list):
        if not temp_received_quantity:
            break
        if seller_received['sku'].id == purchase_data['sku'].id:
            seller_temp = copy.deepcopy(seller_received)
            temp_quan = 0
            if seller_received['quantity'] > temp_received_quantity:
                temp_quan = temp_received_quantity
                temp_received_quantity = 0
            else:
                temp_quan = seller_received['quantity']
                temp_received_quantity -= seller_received['quantity']
            seller_temp['quantity'] = temp_quan
            seller_summary_dict.append(seller_temp)
            seller_received_list[index]['quantity'] -= temp_quan
    return seller_received_list, seller_summary_dict


def update_quality_check(myDict, request, user):
    for i in range(len(myDict['id'])):
        temp_dict = {}
        q_id = myDict['id'][i]
        if not myDict['accepted_quantity'][i]:
            myDict['accepted_quantity'][i] = 0
        if not myDict['rejected_quantity'][i]:
            myDict['rejected_quantity'][i] = 0
        quality_check = QualityCheck.objects.get(id=q_id, po_location__location__zone__user=user.id)
        data = PurchaseOrder.objects.get(id=quality_check.purchase_order_id)
        purchase_data = get_purchase_order_data(data)
        seller_received_dict = get_seller_received_list(data, user)
        put_zone = purchase_data['zone']
        if put_zone:
            put_zone = put_zone.zone
        else:
            put_zone = 'DEFAULT'

        temp_dict = {'received_quantity': float(myDict['accepted_quantity'][i]),
                     'original_quantity': float(quality_check.putaway_quantity),
                     'rejected_quantity': float(myDict['rejected_quantity'][i]),
                     'new_quantity': float(myDict['accepted_quantity'][i]),
                     'total_check_quantity': float(myDict['accepted_quantity'][i]) + float(
                         myDict['rejected_quantity'][i]),
                     'user': user.id, 'data': data, 'quality_check': quality_check}
        if temp_dict['total_check_quantity'] == 0:
            continue
        seller_received_dict, seller_summary_dict = get_quality_check_seller(seller_received_dict, temp_dict,
                                                                             purchase_data)
        if get_misc_value('pallet_switch', user.id) == 'true':
            pallet_code = ''
            pallet = PalletMapping.objects.filter(po_location_id=quality_check.po_location_id)
            if pallet:
                pallet = pallet[0]
                pallet_code = pallet.pallet_detail.pallet_code
                if pallet and (not temp_dict['total_check_quantity'] == pallet.pallet_detail.quantity):
                    return HttpResponse('Partial quality check is not allowed for pallets')
                setattr(pallet.pallet_detail, 'quantity', temp_dict['new_quantity'])
                pallet.pallet_detail.save()
            temp_dict['pallet_number'] = pallet_code
            temp_dict['pallet_data'] = pallet
        save_po_location(put_zone, temp_dict, seller_received_list=seller_summary_dict, run_segregation=True)
        create_bayarea_stock(purchase_data['sku_code'], 'BAY_AREA', temp_dict['received_quantity'], user.id)
        if temp_dict['rejected_quantity']:
            put_zone = 'DAMAGED_ZONE'
            temp_dict['received_quantity'] = temp_dict['rejected_quantity']
            seller_received_dict, seller_summary_dict = get_quality_check_seller(seller_received_dict, temp_dict,
                                                                                 purchase_data)
            save_po_location(put_zone, temp_dict, seller_received_list=seller_summary_dict)
        setattr(quality_check, 'accepted_quantity', temp_dict['new_quantity'])
        setattr(quality_check, 'rejected_quantity', temp_dict['rejected_quantity'])
        setattr(quality_check, 'reason', myDict['reason'][i])
        setattr(quality_check, 'status', 'qc_cleared')
        quality_check.save()
        if not temp_dict['total_check_quantity'] == temp_dict['original_quantity']:
            put_zone = 'QC_ZONE'
            not_checked = float(quality_check.putaway_quantity) - temp_dict['total_check_quantity']
            temp_dict = {}
            temp_dict['received_quantity'] = not_checked
            temp_dict['user'] = user.id
            temp_dict['data'] = data
            qc_data = copy.deepcopy(QUALITY_CHECK_FIELDS)
            qc_data['purchase_order_id'] = data.id
            temp_dict['qc_data'] = qc_data
            temp_dict['qc_po_loc_id'] = quality_check.po_location_id
            save_po_location(put_zone, temp_dict)


@csrf_exempt
@login_required
@get_admin_user
def confirm_quality_check(request, user=''):
    myDict = dict(request.POST.iterlists())
    total_sum = sum(float(i) for i in myDict['accepted_quantity'] + myDict['rejected_quantity'])
    if total_sum < 1:
        return HttpResponse('Update Quantities')

    update_quality_check(myDict, request, user)

    use_imei = 'false'
    misc_data = MiscDetail.objects.filter(user=user.id, misc_type='use_imei')
    if misc_data:
        use_imei = misc_data[0].misc_value

    if myDict.get("accepted", ''):
        save_qc_serials('accepted', myDict.get("accepted", ''), user.id)
    if myDict.get("rejected", ''):
        save_qc_serials('rejected', myDict.get("rejected", ''), user.id)

    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def raise_st_toggle(request, user=''):
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

    return HttpResponse(json.dumps({'user_list': user_list}))


@csrf_exempt
@login_required
@get_admin_user
def save_st(request, user=''):
    all_data = {}
    warehouse_name = request.POST.get('warehouse_name', '')
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['wms_code'])):
        if not data_dict['wms_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        if not data_dict['price'][i]:
            data_dict['price'][i] = 0
        cond = (warehouse_name)
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['wms_code'][i], data_dict['order_quantity'][i], 
            data_dict['price'][i], data_id])
    status = validate_st(all_data, user)
    if not status:
        all_data = insert_st(all_data, user)
        status = "Added Successfully"
    return HttpResponse(status)


@csrf_exempt
@login_required
@get_admin_user
def update_raised_st(request, user=''):
    all_data = []
    data_id = request.GET['warehouse_name']
    open_st = OpenST.objects.filter(warehouse__username=data_id, sku__user=user.id, status=1)
    for stock in open_st:
        all_data.append({'wms_code': stock.sku.wms_code, 'order_quantity': stock.order_quantity, 'price': stock.price,
                         'id': stock.id, 'warehouse_name': stock.warehouse.username})
    return HttpResponse(json.dumps({'data': all_data, 'warehouse': data_id}))


def validate_st(all_data, user):
    sku_status = ''
    other_status = ''
    price_status = ''
    wh_status = ''

    for key, value in all_data.iteritems():
        if not value:
            continue
        for val in value:
            sku = SKUMaster.objects.filter(wms_code=val[0], user=user.id)
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
            # try:
            #     price = float(val[2])
            # except:
            #     if not price_status:
            #         price_status = "Price missing for " + val[0]
            #     else:
            #         price_status += ', ' + val[0]
            warehouse = User.objects.get(username=key)
            code = val[0]
            sku_code = SKUMaster.objects.filter(wms_code__iexact=val[0], user=warehouse.id)
            if not sku_code:
                if not wh_status:
                    wh_status = "SKU Code %s doesn't exists in given warehouse" % code
                else:
                    wh_status += ", " + code

    if other_status:
        sku_status += ", " + other_status
    # if price_status:
    #     sku_status += ", " + price_status
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
            if val[2]:
                stock_dict['price'] = float(val[2])
            else:
                stock_dict['price'] = 0
            stock_transfer = OpenST(**stock_dict)
            stock_transfer.save()
            all_data[key][all_data[key].index(val)][3] = stock_transfer.id
    return all_data


@csrf_exempt
def confirm_stock_transfer(all_data, user, warehouse_name):
    for key, value in all_data.iteritems():
        po_id = get_purchase_order_id(user) + 1
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
        check_purchase_order_created(user, po_id)
    return HttpResponse("Confirmed Successfully")


@csrf_exempt
@login_required
@get_admin_user
def confirm_st(request, user=''):
    all_data = {}
    warehouse_name = request.POST.get('warehouse_name', '')
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['wms_code'])):
        if not data_dict['wms_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        if not data_dict['price'][i]:
            data_dict['price'][i] = 0
        cond = (warehouse_name)
        all_data.setdefault(cond, [])
        all_data[cond].append(
            [data_dict['wms_code'][i], data_dict['order_quantity'][i], data_dict['price'][i], data_id])
    status = validate_st(all_data, user)
    if not status:
        all_data = insert_st(all_data, user)
        status = confirm_stock_transfer(all_data, user, warehouse_name)
        warehouse = User.objects.get(username=warehouse_name)
        f_name = 'stock_transfer_' + warehouse_name + '_'
        rendered_html_data = render_st_html_data(request, user, warehouse, all_data)
        stock_transfer_mail_pdf(request, f_name, rendered_html_data, warehouse)
    return HttpResponse(status)


@csrf_exempt
def get_po_data(request):
    engine_type = request.GET.get('engine_type', 'Tally')
    limit = int(request.GET.get('limit', 100))

    results = []
    all_results = {}
    error_status = {'status': 'Fail', 'reason': 'User Authentication Failed'}
    user = request.user
    if not user.is_authenticated():
        token = request.GET.get('token', '')
        if not token:
            return HttpResponse(json.dumps(error_status))

        user = UserProfile.objects.filter(api_hash=token)
        if not user:
            return HttpResponse(json.dumps(error_status))

        user = user[0].user
    allowed_orders = list(OrdersAPI.objects.filter(order_type='po', user=user.id, status=0, engine_type=engine_type). \
                          values_list('order_id', flat=True)[:limit])

    all_pos = PurchaseOrder.objects.exclude(status='').filter(open_po__sku__user=user.id, order_id__in=allowed_orders)
    purchase_order = all_pos.values('order_id', 'open_po__creation_date', 'updation_date', 'open_po__supplier_id',
                                    'open_po__supplier__name').distinct().annotate(total=Sum('open_po__price'))
    for orders in purchase_order:
        po_data = OrderedDict(
            (('order_id', orders['order_id']), ('order_date', str(orders['open_po__creation_date'].date())),
             ('received_date', str(orders['updation_date'].date())), ('supplier_id', orders['open_po__supplier_id']),
             ('supplier', orders['open_po__supplier__name']), ('total_invoice_amount', orders['total'])))

        del orders['total']
        orders_data = all_pos.filter(**orders)
        value = []
        for order in orders_data:
            po_reference = '%s%s_%s' % (
            order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order.order_id)
            value.append(OrderedDict((('sku_code', order.open_po.sku.sku_code),
                                      ('product_category', 'Electronic Item'),
                                      ('order_quantity', order.open_po.order_quantity),
                                      ('received_quantity', order.received_quantity),
                                      ('unit_price', order.open_po.price),
                                      ('status', order.status), ('received_date', str(order.updation_date.date())))))

        po_data['results'] = value
        results.append({'orders': po_data})

    OrdersAPI.objects.filter(order_type='po', user=user.id, order_id__in=allowed_orders).update(status=9)

    results = dicttoxml.dicttoxml(results, attr_type=False)

    return HttpResponse(results, content_type='text/xml')


@csrf_exempt
def get_so_data(request):
    results = []
    engine_type = request.GET.get('engine_type', 'Tally')
    limit = int(request.GET.get('limit', 100))
    all_results = OrderedDict()
    error_status = {'status': 'Fail', 'reason': 'User Authentication Failed'}

    user = request.user
    if not request.user.is_authenticated():
        token = request.GET.get('token', '')
        if not token:
            return HttpResponse(json.dumps(error_status))

        user = UserProfile.objects.filter(api_hash=token)
        if not user:
            return HttpResponse(json.dumps(error_status))

        user = user[0].user

    if not engine_type:
        error_status['reason'] = 'Missing Engine Type'
        return HttpResponse(json.dumps(error_status))

    allowed_orders = list(OrdersAPI.objects.filter(order_type='so', user=user.id, status=0, engine_type=engine_type). \
                          values_list('order_id', flat=True)[:limit])
    all_orders = OrderDetail.objects.filter(user=user.id, order_id__in=allowed_orders)
    order_detail = all_orders.order_by('-id').values('order_id', 'creation_date', 'shipment_date').distinct(). \
        annotate(total_invoice_amount=Sum('invoice_amount'))
    OrdersAPI.objects.filter(order_type='so', user=user.id, order_id__in=allowed_orders).update(status=9)
    for order_dat in order_detail:
        orders_data = OrderedDict(
            (('order_id', order_dat['order_id']), ('order_date', str(order_dat['creation_date'].date())),
             ('customer_name', 'Roopal Vegad'), ('ledger_name', 'Flipkart'),
             ('shipment_date', str(order_dat['shipment_date'].date())),
             ('total_invoice_amount', str(order_dat['total_invoice_amount']))))
        del order_dat['total_invoice_amount']
        orders = all_orders.filter(**order_dat)
        value = []
        for order in orders:
            value.append(OrderedDict((('sku_code', order.sku.wms_code), ('title', order.title),
                                      ('quantity', order.quantity), ('shipment_date', order.shipment_date),
                                      ('invoice_amount', order.invoice_amount), ('tax_value', '10'),
                                      ('tax_percentage', '5.5'),
                                      ('order_date', str(order.creation_date.date())))))

        orders_data['items'] = value
        results.append({'orders': orders_data})

    results = dicttoxml.dicttoxml(results, attr_type=False)

    return HttpResponse(results, content_type='text/xml')


@csrf_exempt
def get_suppliers_data(request):
    results = []
    search_params = {}
    error_status = {'status': 'Fail', 'reason': 'User Authentication Failed'}
    supp_list = request.GET.get('supplier_id', '')

    user = request.user
    if not request.user.is_authenticated():
        token = request.GET.get('token', '')
        if not token:
            return HttpResponse(json.dumps(error_status))

        user = UserProfile.objects.filter(api_hash=token)
        if not user:
            return HttpResponse(json.dumps(error_status))

        user = user[0].user

    search_params['user'] = user.id
    if supp_list:
        supp_list = supp_list.split(',')
        search_params['id__in'] = supp_list
    supplier_master = SupplierMaster.objects.filter(**search_params)
    for supplier in supplier_master:
        results.append(
            OrderedDict((('supplier_id', supplier.id), ('supplier_name', supplier.name), ('address', supplier.address),
                         ('city', supplier.city), ('state', supplier.state))))
    results = dicttoxml.dicttoxml(results, attr_type=False)

    return HttpResponse(results, content_type='text/xml')


@csrf_exempt
def order_status(request):
    error_status = {'status': 'Fail', 'reason': 'User Authentication Failed'}

    order_data = request.POST.get('order_data', '')
    user = request.user
    if not request.user.is_authenticated():
        token = request.GET.get('token', '')
        if not token:
            return HttpResponse(json.dumps(error_status))

        user = UserProfile.objects.filter(api_hash=token)
        if not user:
            return HttpResponse(json.dumps(error_status))

        user = user[0].user
    engine_type = request.GET.get('engine_type', '')
    if not order_data:
        return HttpResponse(json.dumps({'Status': 'Fail', 'Message': 'No Data Received'}))
    order_data = bf.data(fromstring(request.POST['order_data']))
    for order_dat in order_data.get('ENVELOPE', '').get('ORDERS', '').get('ORDER', ''):
        order_id = order_dat['ORDER_ID']['$']
        order_type = order_dat['ORDER_TYPE']['$'].lower()
        status = int(order_dat['STATUS']['$'])
        if order_id and order_type and status:
            OrdersAPI.objects.filter(engine_type=engine_type, order_type=order_type, order_id=order_id,
                                     user=user.id).update(status=status)
    return HttpResponse(json.dumps({'Status': 'Success', 'Message': 'Updated Successfully'}))


@csrf_exempt
@login_required
@get_admin_user
def confirm_add_po(request, sales_data='', user=''):
    ean_flag = False
    po_order_id = ''
    status = ''
    suggestion = ''
    show_cess_tax = False
    terms_condition = request.POST.get('terms_condition', '')
    if not request.POST:
        return HttpResponse('Updated Successfully')
    sku_id = ''
    data = copy.deepcopy(PO_DATA)
    display_remarks = get_misc_value('display_remarks_mail', user.id)
    if not sales_data:
        po_id = get_purchase_order_id(user)
    else:
        if sales_data['po_order_id'] == '':
            po_id = get_purchase_order_id(user)
        else:
            po_id = int(sales_data['po_order_id'])
            po_order_id = int(sales_data['po_order_id'])

    ids_dict = {}
    po_data = []
    total = 0
    total_qty = 0
    supplier_code = ''
    if not sales_data:
        myDict = dict(request.POST.iterlists())
    else:
        myDict = sales_data
    ean_data = SKUMaster.objects.filter(wms_code__in=myDict['wms_code'], user=user.id).values_list(
        'ean_number').exclude(ean_number=0)
    if ean_data:
        ean_flag = True

    all_data = get_raisepo_group_data(user, myDict)

    for key, value in all_data.iteritems():
        po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
        sku_id = SKUMaster.objects.filter(wms_code=key.upper(), user=user.id)

        ean_number = 0
        if sku_id:
            ean_number = int(sku_id[0].ean_number)

        if not sku_id:
            sku_id = SKUMaster.objects.filter(wms_code='TEMP', user=user.id)
            po_suggestions['wms_code'] = key.upper()

        if not value['order_quantity']:
            continue

        price = value['price']
        if not price:
            price = 0

        mrp = value['mrp']
        if not mrp:
            mrp = 0

        if not 'supplier_code' in myDict.keys() and value['supplier_id']:
            supplier = SKUSupplier.objects.filter(supplier_id=value['supplier_id'], sku__user=user.id)
            if supplier:
                supplier_code = supplier[0].supplier_code
        elif value['supplier_code']:
            supplier_code = value['supplier_code']
        supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=value['supplier_id'],
                                                      sku__user=user.id)
        sku_mapping = {'supplier_id': value['supplier_id'], 'sku': sku_id[0], 'preference': 1, 'moq': 0,
                       'supplier_code': supplier_code, 'price': price, 'creation_date': datetime.datetime.now(),
                       'updation_date': datetime.datetime.now()}

        if supplier_mapping:
            supplier_mapping = supplier_mapping[0]
            if sku_mapping['supplier_code'] and supplier_mapping.supplier_code != sku_mapping['supplier_code']:
                supplier_mapping.supplier_code = sku_mapping['supplier_code']
                supplier_mapping.save()
        else:
            new_mapping = SKUSupplier(**sku_mapping)
            new_mapping.save()
        po_suggestions['sku_id'] = sku_id[0].id
        po_suggestions['supplier_id'] = value['supplier_id']
        po_suggestions['order_quantity'] = value['order_quantity']
        po_suggestions['po_name'] = value['po_name']
        po_suggestions['supplier_code'] = value['supplier_code']
        po_suggestions['price'] = float(price)
        po_suggestions['status'] = 'Manual'
        po_suggestions['remarks'] = value['remarks']
        po_suggestions['measurement_unit'] = "UNITS"
        po_suggestions['mrp'] = float(mrp)
        po_suggestions['sgst_tax'] = value['sgst_tax']
        po_suggestions['cgst_tax'] = value['cgst_tax']
        po_suggestions['igst_tax'] = value['igst_tax']
        po_suggestions['cess_tax'] = value['cess_tax']
        po_suggestions['utgst_tax'] = value['utgst_tax']
        po_suggestions['ship_to'] = value['ship_to']
        po_suggestions['terms'] = terms_condition
        if value['po_delivery_date']:
            po_suggestions['delivery_date'] = value['po_delivery_date']
        if value['measurement_unit']:
            if value['measurement_unit'] != "":
                po_suggestions['measurement_unit'] = value['measurement_unit']
        if value.get('vendor_id', ''):
            vendor_master = VendorMaster.objects.get(vendor_id=value['vendor_id'], user=user.id)
            po_suggestions['vendor_id'] = vendor_master.id
            po_suggestions['order_type'] = 'VR'

        data1 = OpenPO(**po_suggestions)
        data1.save()
        purchase_order = OpenPO.objects.get(id=data1.id, sku__user=user.id)
        sup_id = purchase_order.id

        supplier = purchase_order.supplier_id
        if supplier not in ids_dict and not po_order_id:
            po_id = po_id + 1
            ids_dict[supplier] = po_id
        if po_order_id:
            ids_dict[supplier] = po_id
        data['open_po_id'] = sup_id
        data['order_id'] = ids_dict[supplier]
        #data['ship_to'] = value['ship_to']
        user_profile = UserProfile.objects.filter(user_id=user.id)
        industry_type = user_profile[0].industry_type
        if user_profile:
            data['prefix'] = user_profile[0].prefix
        order = PurchaseOrder(**data)
        order.save()
        if value['sellers']:
            for seller, seller_quan in value['sellers'].iteritems():
                SellerPO.objects.create(seller_id=seller, open_po_id=data1.id, seller_quantity=seller_quan[0],
                                        creation_date=datetime.datetime.now(), status=1,
                                        receipt_type=value['receipt_type'])

        amount = float(purchase_order.order_quantity) * float(purchase_order.price)
        tax = value['sgst_tax'] + value['cgst_tax'] + value['igst_tax'] + value['utgst_tax']
        if value['cess_tax']:
            show_cess_tax = True
            tax += value['cess_tax']
        if not tax:
            total += amount
        else:
            total += amount + ((amount / 100) * float(tax))
        total_qty += purchase_order.order_quantity
        if purchase_order.sku.wms_code == 'TEMP':
            wms_code = purchase_order.wms_code
        else:
            wms_code = purchase_order.sku.wms_code

        if industry_type == 'FMCG':
            total_tax_amt = (purchase_order.utgst_tax + purchase_order.sgst_tax + purchase_order.cgst_tax + purchase_order.igst_tax + purchase_order.cess_tax + purchase_order.utgst_tax) * (amount/100)
            total_sku_amt = total_tax_amt + amount
            po_temp_data = [wms_code, supplier_code, purchase_order.sku.sku_desc, purchase_order.order_quantity,
                        po_suggestions['measurement_unit'],
                        purchase_order.price, purchase_order.mrp, amount, purchase_order.sgst_tax, purchase_order.cgst_tax,
                        purchase_order.igst_tax,
                        purchase_order.cess_tax,
                        purchase_order.utgst_tax,
                        total_sku_amt
                        ]
        else:
            total_tax_amt = (purchase_order.utgst_tax + purchase_order.sgst_tax + purchase_order.cgst_tax + purchase_order.igst_tax + purchase_order.cess_tax + purchase_order.utgst_tax) * (amount/100)
            total_sku_amt = total_tax_amt + amount
            po_temp_data = [wms_code, supplier_code, purchase_order.sku.sku_desc, purchase_order.order_quantity,
                        po_suggestions['measurement_unit'],
                        purchase_order.price, amount, purchase_order.sgst_tax, purchase_order.cgst_tax,
                        purchase_order.igst_tax,
                        purchase_order.cess_tax,
                        purchase_order.utgst_tax,
                        total_sku_amt
                        ]
        if ean_flag:
            po_temp_data.insert(1, ean_number)
        if display_remarks == 'true':
            po_temp_data.append(purchase_order.remarks)
        po_data.append(po_temp_data)
        suggestion = OpenPO.objects.get(id=sup_id, sku__user=user.id)
        setattr(suggestion, 'status', 0)
        suggestion.save()
        if sales_data and not status:
            check_purchase_order_created(user, po_id)
            return HttpResponse(str(order.id) + ',' + str(order.order_id))
    if status and not suggestion:
        check_purchase_order_created(user, po_id)
        return HttpResponse(status)
    address = purchase_order.supplier.address
    address = '\n'.join(address.split(','))
    if purchase_order.ship_to:
        ship_to_address = purchase_order.ship_to
        company_address = user.userprofile.address
    else:
        ship_to_address, company_address = get_purchase_company_address(user.userprofile)
    wh_telephone = user.userprofile.wh_phone_number
    ship_to_address = '\n'.join(ship_to_address.split(','))
    vendor_name = ''
    vendor_address = ''
    vendor_telephone = ''
    if purchase_order.order_type == 'VR':
        vendor_address = purchase_order.vendor.address
        vendor_address = '\n'.join(vendor_address.split(','))
        vendor_name = purchase_order.vendor.name
        vendor_telephone = purchase_order.vendor.phone_number
    telephone = purchase_order.supplier.phone_number
    name = purchase_order.supplier.name
    order_id = ids_dict[supplier]
    supplier_email = purchase_order.supplier.email_id
    phone_no = purchase_order.supplier.phone_number
    gstin_no = purchase_order.supplier.tin_number
    po_exp_duration = purchase_order.supplier.po_exp_duration
    order_date = get_local_date(request.user, order.creation_date)
    if po_exp_duration:
        expiry_date = order.creation_date + datetime.timedelta(days=po_exp_duration)
    else:
        expiry_date = ''
    po_reference = '%s%s_%s' % (order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order_id)
    if industry_type == 'FMCG':
        table_headers = ['WMS Code', 'Supplier Code', 'Desc', 'Qty', 'UOM', 'Unit Price', 'MRP', 'Amt',
                     'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'Total']
        if show_cess_tax:
            table_headers.insert(11, 'CESS (%)')
    else:
        table_headers = ['WMS Code', 'Supplier Code', 'Desc', 'Qty', 'UOM', 'Unit Price', 'Amt',
                     'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'Total']
        if show_cess_tax:
            table_headers.insert(10, 'CESS (%)')
    if ean_flag:
        table_headers.insert(1, 'EAN')
    if display_remarks == 'true':
        table_headers.append('Remarks')
    profile = UserProfile.objects.get(user=user.id)
    company_name = profile.company_name
    title = 'Purchase Order'
    receipt_type = request.GET.get('receipt_type', '')
    if request.POST.get('seller_id', '') and 'shproc' in str(request.POST.get('seller_id').split(":")[1]).lower():
        company_name = 'SHPROC Procurement Pvt. Ltd.'
        title = 'Purchase Order'
    total_amt_in_words = number_in_words(round(total)) + ' ONLY'
    round_value = float(round(total) - float(total))
    company_logo = get_po_company_logo(user, COMPANY_LOGO_PATHS, request)
    iso_company_logo = get_po_company_logo(user, ISO_COMPANY_LOGO_PATHS, request)
    data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                 'telephone': str(telephone), 'ship_to_address': ship_to_address,
                 'name': name, 'order_date': order_date, 'total': round(total), 'po_reference': po_reference,
                 'user_name': request.user.username, 'total_amt_in_words': total_amt_in_words,
                 'total_qty': total_qty, 'company_name': company_name, 'location': profile.location,
                 'w_address': ship_to_address,
                 'vendor_name': vendor_name, 'vendor_address': vendor_address,
                 'vendor_telephone': vendor_telephone, 'receipt_type': receipt_type, 'title': title,
                 'gstin_no': gstin_no, 'industry_type': industry_type, 'expiry_date': expiry_date,
                 'wh_telephone': wh_telephone, 'wh_gstin': profile.gst_number, 'wh_pan': profile.pan_number,
                 'terms_condition': terms_condition, 'show_cess_tax' : show_cess_tax,
                 'company_address': company_address, 
                 'company_logo': company_logo, 'iso_company_logo': iso_company_logo}
    if round_value:
        data_dict['round_total'] = "%.2f" % round_value
    t = loader.get_template('templates/toggle/po_download.html')
    rendered = t.render(data_dict)
    if get_misc_value('raise_po', user.id) == 'true':
        write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, phone_no, po_data,
                           str(order_date).split(' ')[0], ean_flag=ean_flag)
    check_purchase_order_created(user, po_id)
    return render(request, 'templates/toggle/po_template.html', data_dict)


def create_mail_attachments(f_name, html_data):
    from random import randint
    attachments = []
    if not isinstance(html_data, list):
        html_data = [html_data]
    for data in html_data:
        temp_name = f_name + str(randint(100, 9999))
        file_name = '%s.html' % temp_name
        pdf_file = '%s.pdf' % temp_name
        path = 'static/temp_files/'
        folder_check(path)
        file = open(path + file_name, "w+b")
        file.write(data)
        file.close()
        os.system(
            "./phantom/bin/phantomjs ./phantom/examples/rasterize.js ./%s ./%s A4" % (path + file_name, path + pdf_file))
        attachments.append({'path': path + pdf_file, 'name': pdf_file})
    return attachments


def write_and_mail_pdf(f_name, html_data, request, user, supplier_email, phone_no, po_data, order_date, ean_flag=False,
                       internal=False, report_type='Purchase Order'):
    receivers = []
    attachments = ''
    if html_data:
        attachments = create_mail_attachments(f_name, html_data)
    internal_mail = MiscDetail.objects.filter(user=request.user.id, misc_type='Internal Emails')
    misc_internal_mail = MiscDetail.objects.filter(user=request.user.id, misc_type='internal_mail', misc_value='true')
    if misc_internal_mail and internal_mail:
        internal_mail = internal_mail[0].misc_value.split(",")
        receivers.extend(internal_mail)

    if supplier_email:
        receivers.append(supplier_email)

    username = user.username
    if username == 'shotang':
        username = 'SHProc'
    company_name = username
    if not user.username == 'shotang':
        cmp_name = UserProfile.objects.get(user_id=user.id).company_name
        if cmp_name:
            company_name = cmp_name

    # Email Subject based on report type name
    email_body = 'Please find the %s with PO Reference: <b>%s</b> in the attachment' % (report_type, f_name)
    email_subject = '%s %s' % (company_name, report_type)
    if report_type == 'Job Order':
        email_body = 'Please find the %s with Job Code: <b>%s</b> in the attachment' % (report_type, f_name)
        email_subject = '%s %s with Job Code %s' % (company_name, report_type, f_name)
    if report_type == 'Save PO':
        email_body = 'Saved PO Data'
        email_subject = po_data
    if supplier_email or internal or internal_mail:
        send_mail_attachment(receivers, email_subject, email_body, files=attachments)
    if phone_no:
        if report_type == 'Purchase Order':
            po_message(po_data, phone_no, username, f_name, order_date, ean_flag)
        elif report_type == 'Goods Receipt Note':
            grn_message(po_data, phone_no, username, f_name, order_date)
        elif report_type == 'Job Order':
            jo_message(po_data, phone_no, company_name, f_name, order_date)


@csrf_exempt
@login_required
@get_admin_user
def confirm_po1(request, user=''):
    data = copy.deepcopy(PO_DATA)
    po_id = get_purchase_order_id(user)
    ids_dict = {}
    po_data = []
    total = 0
    total_qty = 0
    show_cess_tax = False
    status_dict = {'Self Receipt': 'SR', 'Vendor Receipt': 'VR', 'Hosted Warehouse': 'HW'}
    myDict = dict(request.POST.iterlists())
    ean_flag = False
    display_remarks = get_misc_value('display_remarks_mail', user.id)
    for key, value in myDict.iteritems():
        for val in value:
            address = ''
            wh_address = ''
            ship_to_address = ''
            supplier_email = ''
            gstin_no = ''
            telephone = ''
            purchase_orders = OpenPO.objects.filter(supplier_id=val, status__in=['Manual', 'Automated', ''],
                                                    order_type=status_dict[key],
                                                    sku__user=user.id)
            if list(purchase_orders.exclude(sku__ean_number=0).values_list('sku__ean_number', flat=True)):
                ean_flag = True
            for purchase_order in purchase_orders:
                data_id = purchase_order.id
                supplier = val
                if supplier not in ids_dict:
                    po_id = po_id + 1
                    ids_dict[supplier] = po_id
                data['open_po_id'] = data_id
                data['order_id'] = ids_dict[supplier]
                user_profile = UserProfile.objects.filter(user_id=user.id)
                if user_profile:
                    data['prefix'] = user_profile[0].prefix
                order = PurchaseOrder(**data)
                order.save()

                amount = float(purchase_order.order_quantity) * float(purchase_order.price)
                tax = purchase_order.sgst_tax + purchase_order.cgst_tax + purchase_order.igst_tax + purchase_order.utgst_tax
                if purchase_order.cess_tax:
                    tax += purchase_order.cess_tax
                if not tax:
                    total += amount
                else:
                    total += amount + ((amount / 100) * float(tax))
                total_qty += float(purchase_order.order_quantity)

                if purchase_order.sku.wms_code == 'TEMP':
                    wms_code = purchase_order.wms_code
                else:
                    wms_code = purchase_order.sku.wms_code

                supplier_code = ''
                sku_supplier = SKUSupplier.objects.filter(sku__user=user.id, supplier_id=purchase_order.supplier_id,
                                                          sku_id=purchase_order.sku_id)
                if sku_supplier:
                    supplier_code = sku_supplier[0].supplier_code

                total_tax_amt = (purchase_order.utgst_tax + purchase_order.sgst_tax + purchase_order.cgst_tax + purchase_order.igst_tax + purchase_order.cess_tax + purchase_order.utgst_tax) * (amount/100)
                total_sku_amt = total_tax_amt + amount
                po_temp_data = [wms_code, supplier_code, purchase_order.sku.sku_desc, purchase_order.order_quantity,
                                purchase_order.sku.measurement_type, purchase_order.price, amount,
                                purchase_order.sgst_tax,
                                purchase_order.cgst_tax, purchase_order.igst_tax, purchase_order.cess_tax, purchase_order.utgst_tax,
                                total_sku_amt
                                ]
                if purchase_order.cess_tax:
                    show_cess_tax = True
                if ean_flag:
                    po_temp_data.insert(1, purchase_order.sku.ean_number)
                if display_remarks == 'true':
                    po_temp_data.append(purchase_order.remarks)
                po_data.append(po_temp_data)

                suggestion = OpenPO.objects.get(id=data_id, sku__user=user.id)
                setattr(suggestion, 'status', 0)
                suggestion.save()
            if len(purchase_orders):
                address = purchase_orders[0].supplier.address
                address = '\n'.join(address.split(','))
                if purchase_orders[0].ship_to:
                    ship_to_address = purchase_orders[0].ship_to
                    company_address = user.userprofile.address
                else:
                    ship_to_address, company_address = get_purchase_company_address(user.userprofile)
                ship_to_address = '\n'.join(ship_to_address.split(','))
                telephone = purchase_orders[0].supplier.phone_number
                name = purchase_orders[0].supplier.name
                supplier_email = purchase_orders[0].supplier.email_id
                gstin_no = purchase_orders[0].supplier.tin_number
                if purchase_orders[0].order_type == 'VR':
                    vendor_address = purchase_orders[0].vendor.address
                    vendor_address = '\n'.join(vendor_address.split(','))
                    vendor_name = purchase_orders[0].vendor.name
                    vendor_telephone = purchase_orders[0].vendor.phone_number
                terms_condition = purchase_orders[0].terms
            wh_telephone = user.userprofile.wh_phone_number
            order_id = ids_dict[supplier]
            order_date = get_local_date(request.user, order.creation_date)
            vendor_name = ''
            vendor_address = ''
            vendor_telephone = ''
            profile = UserProfile.objects.get(user=user.id)
            po_reference = '%s%s_%s' % (str(profile.prefix), str(order_date).split(' ')[0].replace('-', ''), order_id)
            # table_headers = ('WMS CODE', 'Supplier Name', 'Description', 'Quantity', 'Unit Price', 'Amount')
            table_headers = ['WMS Code', 'Supplier Code', 'Desc', 'Qty', 'UOM', 'Unit Price',
                             'Amt', 'SGST (%)', 'CGST (%)', 'IGST (%)', 'UTGST (%)', 'Total']
            if ean_flag:
                table_headers.insert(1, 'EAN')
            if display_remarks == 'true':
                table_headers.append('Remarks')
            if show_cess_tax:
                table_headers.insert(10, 'CESS (%)')
            total_amt_in_words = number_in_words(round(total)) + ' ONLY'
            round_value = float(round(total) - float(total))
            company_logo = get_po_company_logo(user, COMPANY_LOGO_PATHS, request)
            iso_company_logo = get_po_company_logo(user, ISO_COMPANY_LOGO_PATHS, request)
            data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                         'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': round(total),             
                         'company_name': profile.company_name, 'location': profile.location,
                         'po_reference': po_reference,
                         'total_qty': total_qty, 'vendor_name': vendor_name, 'vendor_address': vendor_address,
                         'vendor_telephone': vendor_telephone, 'gstin_no': gstin_no,
                         'w_address': ship_to_address, 'ship_to_address': ship_to_address,
                         'wh_telephone': wh_telephone, 'wh_gstin': profile.gst_number,
                         'terms_condition' : terms_condition, 'total_amt_in_words' : total_amt_in_words,
                         'show_cess_tax': show_cess_tax, 'company_address': company_address,
                         'company_logo': company_logo, 'iso_company_logo': iso_company_logo}
            if round_value:
                data_dict['round_total'] = "%.2f" % round_value
            t = loader.get_template('templates/toggle/po_download.html')
            rendered = t.render(data_dict)
            if get_misc_value('raise_po', user.id) == 'true':
                write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, telephone, po_data,
                                   str(order_date).split(' ')[0], ean_flag=ean_flag)
    check_purchase_order_created(user, po_id)
    return render(request, 'templates/toggle/po_template.html', data_dict)


@csrf_exempt
@login_required
@get_admin_user
def delete_po_group(request, user=''):
    status_dict = dict(zip(PO_ORDER_TYPES.values(), PO_ORDER_TYPES.keys()))

    myDict = dict(request.GET.iterlists())
    for key, value in myDict.iteritems():
        for val in value:
            purchase_order = OpenPO.objects.filter(supplier_id=val, status__in=['Manual', 'Automated', ''],
                                                   order_type=status_dict[key],
                                                   sku__user=user.id).delete()

    return HttpResponse('Updated Successfully')


def get_misc_value(misc_type, user):
    misc_value = 'false'
    data = MiscDetail.objects.filter(user=user, misc_type=misc_type)
    if data:
        misc_value = data[0].misc_value
    return misc_value


@csrf_exempt
@get_admin_user
def check_serial_exists(request, user=''):
    status = ''
    serial = request.POST.get('serial', '')
    data_id = request.POST.get('id', '')
    if serial:
        filter_params = {"imei_number": serial, "sku__user": user.id}
        if data_id:
            quality_check = QualityCheck.objects.filter(id=data_id)
            if quality_check:
                filter_params['sku__sku_code'] = quality_check[
                    0].purchase_order.open_po.sku.sku_code
        po_mapping = POIMEIMapping.objects.filter(**filter_params)
        if not po_mapping:
            status = "imei does not exists"
    return HttpResponse(status)


def save_qc_serials(key, scan_data, user, qc_id=''):
    try:
        for scan_value in scan_data:
            scan_value = scan_value.split(',')
            scan_value = list(filter(None, scan_value))
            if not scan_value:
                continue
            for value in scan_value:
                if qc_id:
                    imei = value
                    reason = ''
                    if '<<>>' in value:
                        imei, reason = value.split('<<>>')
                else:
                    imei, qc_id, reason = value.split('<<>>')
                if not value:
                    continue
                po_mapping = POIMEIMapping.objects.filter(imei_number=imei, sku__user=user)
                if po_mapping:
                    qc_serial_dict = copy.deepcopy(QC_SERIAL_FIELDS)
                    qc_serial_dict['quality_check_id'] = qc_id
                    qc_serial_dict['serial_number_id'] = po_mapping[0].id
                    qc_serial_dict['status'] = key
                    qc_serial_dict['reason'] = reason
                    qc_serial = QCSerialMapping(**qc_serial_dict)
                    qc_serial.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Save QC Serial failed for ' + str(scan_data) + ' error statement is ' + str(e))


def get_return_seller_id(returns, user):
    ''' Returns Seller Master ID'''
    return_imei = ReturnsIMEIMapping.objects.filter(order_return_id=returns.id, order_return__sku__user=user.id)
    seller_id = ''
    if return_imei:
        order_imei = return_imei[0].order_imei
        if order_imei.po_imei and order_imei.po_imei.purchase_order and order_imei.po_imei.purchase_order.open_po:
            open_po_id = order_imei.po_imei.purchase_order.open_po_id
            seller_po = SellerPO.objects.filter(open_po_id=open_po_id, open_po__sku__user=user.id)
            if seller_po:
                seller_id = seller_po[0].seller_id
    else:
        if returns.seller_order:
            seller_id = returns.seller_order.seller_id
    return seller_id


@csrf_exempt
@login_required
@get_admin_user
def returns_putaway_data(request, user=''):
    return_wms_codes = []
    user_profile = UserProfile.objects.get(user_id=user.id)
    stock = StockDetail.objects.filter(sku__user=user.id).order_by('-receipt_number')
    if stock:
        receipt_number = int(stock[0].receipt_number) + 1
    else:
        receipt_number = 1
    myDict = dict(request.POST.iterlists())
    mod_locations = []
    marketplace_data = []
    for i in range(0, len(myDict['id'])):
        status = ''
        data_id = myDict['id'][i]
        zone = myDict['zone'][i]
        location = myDict['location'][i]
        quantity = float(myDict['quantity'][i])
        returns_data = ReturnsLocation.objects.filter(id=data_id, status=1)
        if not returns_data:
            continue
        returns_data = returns_data[0]
        if location and zone and quantity:
            location_id = LocationMaster.objects.filter(location=location, zone__zone=zone, zone__user=user.id)
            if not location_id:
                status = "Zone, location match doesn't exists"
        else:
            status = 'Missing zone or location or quantity'
        if not status:
            sku_id = returns_data.returns.sku_id
            return_wms_codes.append(returns_data.returns.sku.wms_code)
            seller_id = get_return_seller_id(returns_data.returns, user)
            stock_data = StockDetail.objects.filter(location_id=location_id[0].id, receipt_number=receipt_number,
                                                    sku_id=sku_id,
                                                    sku__user=user.id)
            batch_detail = BatchDetail.objects.filter(transact_type='return_loc', transact_id=returns_data.id)
            if stock_data:
                stock_data = stock_data[0]
                setattr(stock_data, 'quantity', float(stock_data.quantity) + quantity)
                if batch_detail:
                    stock_data.batch_detail_id = batch_detail[0].id
                stock_data.save()
                stock_id = stock_data.id
                mod_locations.append(stock_data.location.location)
            else:
                stock_dict = {'location_id': location_id[0].id, 'receipt_number': receipt_number,
                              'receipt_date': datetime.datetime.now(),
                              'sku_id': sku_id, 'quantity': quantity, 'status': 1,
                              'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}
                if batch_detail:
                    stock_dict['batch_detail_id'] = batch_detail[0].id
                new_stock = StockDetail(**stock_dict)
                new_stock.save()
                stock_id = new_stock.id
                mod_locations.append(new_stock.location.location)
            if stock_id and seller_id:
                seller_stock = SellerStock.objects.filter(stock_id=stock_id, seller_id=seller_id, seller__user=user.id)
                if seller_stock:
                    seller_stock = seller_stock[0]
                    setattr(seller_stock, 'quantity', float(seller_stock.quantity) + quantity)
                    seller_stock.save()
                else:
                    seller_stock_dict = {'seller_id': seller_id, 'stock_id': stock_id, 'quantity': quantity,
                                         'status': 1,
                                         'creation_date': datetime.datetime.now()}
                    seller_stock = SellerStock(**seller_stock_dict)
                    seller_stock.save()
                if seller_stock.stock.location.zone.zone not in ['DAMAGED_ZONE']:
                    marketplace_data.append({'sku_code': str(seller_stock.stock.sku.sku_code),
                                             'seller_id': int(seller_stock.seller.seller_id),
                                             'quantity': int(quantity)})
            returns_data.quantity = float(returns_data.quantity) - float(quantity)

            # Save SKU Level stats
            save_sku_stats(user, returns_data.returns.sku_id, returns_data.returns.id, 'return', quantity)
            if returns_data.quantity <= 0:
                returns_data.status = 0
            if not returns_data.location_id == location_id[0].id:
                setattr(returns_data, 'location_id', location_id[0].id)
            returns_data.save()
            status = 'Updated Successfully'

    return_wms_codes = list(set(return_wms_codes))
    if user_profile.user_type == 'marketplace_user':
        if marketplace_data:
            check_and_update_marketplace_stock(marketplace_data, user)
    else:
        check_and_update_stock(return_wms_codes, user)
    update_filled_capacity(mod_locations, user.id)
    return HttpResponse(status)


@login_required
@get_admin_user
def check_imei_exists(request, user=''):
    status = ''
    imei = request.GET.get('imei', '')
    sku_code = request.GET.get('sku_code', '')
    if imei and sku_code:
        po_mapping, status, imei_data = check_get_imei_details(imei, sku_code, user.id, check_type='purchase_check')
    else:
        status = "Missing Serial or SKU Code"

    return HttpResponse(status)


@csrf_exempt
@get_admin_user
def create_purchase_order(request, myDict, i, user=''):
    po_order = PurchaseOrder.objects.filter(id=myDict['id'][0], open_po__sku__user=user.id)
    purchase_order = PurchaseOrder.objects.filter(order_id=po_order[0].order_id,
                                                  open_po__sku__wms_code=myDict['wms_code'][i],
                                                  open_po__sku__user=user.id)
    if purchase_order:
        myDict['id'][i] = purchase_order[0].id
    else:
        if po_order:
            po_order_id = po_order[0].order_id
        sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i], user=user.id)
        supplier_master = SupplierMaster.objects.filter(id=myDict['supplier_id'][i], user=user.id)
        price = myDict['price'][i]
        if not price:
            price = 0
        try:
            po_quantity = float(myDict['po_quantity'][i])
        except:
            po_quantity = 0
        if not po_quantity:
            po_quantity = float(myDict['quantity'][i])
        new_data = {'supplier_id': supplier_master[0].id, 'sku_id': sku_master[0].id,
                    'order_quantity': po_quantity, 'price': price,
                    'po_name': po_order[0].open_po.po_name,
                    'order_type': po_order[0].open_po.order_type, 'tax_type': po_order[0].open_po.tax_type,
                    'measurement_unit': sku_master[0].measurement_type,
                    'creation_date': datetime.datetime.now()}
        if 'mrp' in myDict.keys():
            new_data['mrp'] = myDict['mrp'][i]
        if 'tax_percent' in myDict.keys() and myDict['tax_percent'][i]:
            if supplier_master[0].tax_type == 'intra_state':
                new_data['cgst_tax'] = float(myDict['tax_percent'][i])/2
                new_data['sgst_tax'] = float(myDict['tax_percent'][i])/2
            else:
                new_data['igst_tax'] = float(myDict['tax_percent'][i])
        if 'cess_percent' in myDict.keys() and myDict['cess_percent'][i]:
            new_data['cess_tax'] = float(myDict['cess_percent'][i])
        open_po = OpenPO.objects.create(**new_data)
        purchase_order = PurchaseOrder.objects.create(order_id=po_order_id, open_po_id=open_po.id,
                                    received_quantity=myDict['quantity'][i], po_date=po_order[0].po_date,
                                    ship_to=po_order[0].ship_to, prefix=user.userprofile.prefix,
                                    creation_date=datetime.datetime.now())
        #get_data = confirm_add_po(request, new_data)
        #get_data = get_data.content
        myDict['id'][i] = purchase_order.id
        if po_order[0].open_po and po_order[0].open_po.sellerpo_set.filter():
            seller_po = po_order[0].open_po.sellerpo_set.filter()
            temp_purchase_obj = PurchaseOrder.objects.get(id=myDict['id'][i])
            exist_seller_po = SellerPO.objects.filter(seller_id=seller_po[0].seller_id,
                                                      open_po_id=open_po.id)
            if not exist_seller_po:
                SellerPO.objects.create(seller_id=seller_po[0].seller_id, open_po_id=open_po.id,
                                    seller_quantity=po_quantity,
                                    received_quantity=myDict['quantity'][i],
                                    receipt_type=seller_po[0].receipt_type, unit_price=price,
                                    status=1)
    return myDict['id'][i]


@csrf_exempt
@login_required
@get_admin_user
def delete_st(request, user=''):
    data_id = request.GET.get('data_id')
    OpenST.objects.get(id=data_id).delete()
    return HttpResponse("Deleted Successfully")


@csrf_exempt
@login_required
@get_admin_user
def confirm_vendor_received(request, user=''):
    myDict = dict(request.GET.iterlists())
    stock = VendorStock.objects.filter(sku__user=user.id).order_by('-receipt_number')
    if stock:
        receipt_number = int(stock[0].receipt_number) + 1
    else:
        receipt_number = 1
    for i in range(len(myDict['id'])):
        if myDict['quantity'][i]:
            value = float(myDict['quantity'][i])
        else:
            continue
        if not value:
            continue
        data = PurchaseOrder.objects.get(id=myDict['id'][i])
        sku_master = SKUMaster.objects.get(wms_code=myDict['wms_code'][i], user=user.id)
        stock_instance = VendorStock.objects.filter(sku_id=sku_master.id, receipt_number=receipt_number,
                                                    vendor_id=data.open_po.vendor_id)
        if not stock_instance:
            stock_dict = {'receipt_number': receipt_number, 'receipt_date': datetime.datetime.now(),
                          'quantity': float(value), 'status': 1, 'creation_date': datetime.datetime.now(),
                          'sku_id': sku_master.id, 'vendor_id': data.open_po.vendor_id}
            vendor_stock = VendorStock(**stock_dict)
            vendor_stock.save()
        else:
            stock_instance = stock_instance[0]
            stock_instance.quantity = float(stock_instance.quantity) + float(value)
            stock_instance.save()
        data.received_quantity = float(data.received_quantity) + float(value)
        if float(data.received_quantity) >= float(data.open_po.order_quantity):
            data.status = 'confirmed-putaway'
        data.save()
    return HttpResponse("Updated Successfully")


@login_required
@csrf_exempt
@get_admin_user
def track_orders(request, user=''):
    order_id = request.GET.get('order_id', '')
    o_index = request.GET.get('orders', 0)
    p_index = request.GET.get('purchase-orders', 0)
    search = request.GET.get('search', 0)
    po_sku = request.GET.get('po_sku_code', '')
    order_sku = request.GET.get('order_sku_code', '')
    marketplace = request.GET.get('marketplace', '')
    supplier = request.GET.get('supplier', '')
    is_db = request.GET.get('db', '')
    open_po = [];
    open_orders = []
    orders_data = OrderedDict()
    if request.GET.get('po_order_id', ''):
        order_id = request.GET.get('po_order_id', '')
    search_params = {'status__in': ['', 'location-assigned', 'grn-generated'], 'open_po__sku__user': user.id}
    if supplier:
        search_params['open_po__supplier__name'] = supplier
    if po_sku:
        search_params['open_po__sku__sku_code'] = po_sku
    if order_id:
        temp = re.findall('\d+', order_id)
        if temp:
            search_params['order_id'] = temp[-1]
    if p_index:
        search_params['order_id__gt'] = p_index

    stages = OrderedDict((('', 'PO Raised'), ('grn-generated', 'Goods Received'), ('qc', 'Quality Check'),
                          ('location-assigned', 'Putaway')))
    order_stages = OrderedDict(
        (('confirmed', 'Order Confirmed'), ('open', 'Picklist Generated'), ('picked', 'Ready to Ship')))
    if not get_permission(request.user, 'add_qualitycheck'):
        del stages['qc']
    open_po_ids = PurchaseOrder.objects.filter(**search_params).order_by('order_id').values_list('order_id', flat=True)
    for open_po_id in open_po_ids[:20]:
        total = 0
        temp_data = []
        ind = len(stages) - 1
        po_data = PurchaseOrder.objects.exclude(status='confirmed-putaway').filter(order_id=open_po_id,
                                                                                   open_po__sku__user=user.id)
        for dat in po_data:
            total += int(dat.open_po.order_quantity) * float(dat.open_po.price)
            if dat.status in stages.keys():
                temp = int(stages.values().index(stages[dat.status])) + 1
                if dat.status == 'grn-generated':
                    qc_check = QualityCheck.objects.filter(purchase_order__order_id=open_po_id,
                                                           purchase_order__open_po__sku__user=user.id,
                                                           status='qc_pending')
                    if qc_check:
                        temp = 2 + 1
            if temp < ind:
                ind = temp
            temp_data.append({'name': dat.open_po.supplier.name, 'image_url': dat.open_po.sku.image_url,
                              'order': dat.prefix + '_' + str(dat.creation_date.strftime("%d%m%Y")) + '_' + str(
                                  dat.order_id),
                              'sku_desc': dat.open_po.sku.sku_desc, 'sku_code': dat.open_po.sku.wms_code,
                              'quantity': dat.open_po.order_quantity,
                              'price': dat.open_po.price, 'order_date': str(dat.creation_date.strftime("%d %B %Y"))})
        stage = get_stage_index(stages, ind)
        open_po.append({'open_po_id': open_po_id, 'total': total, 'order_data': temp_data, 'stage': stage,
                        'index': po_data[0].order_id})

    search_params = {'user': user.id, 'status': 1}
    search_params1 = {'order__user': user.id}
    if marketplace:
        search_params['marketplace'] = marketplace
        search_params1['order__marketplace'] = marketplace
    if order_sku:
        search_params['sku__sku_code'] = order_sku
        search_params1['order__sku__sku_code'] = order_sku
    if order_id:
        temp = re.findall('\d+', order_id)
        if temp:
            search_params['order_id'] = ''.join(temp)
            search_params1['order__order_id'] = ''.join(temp)
        temp = re.findall('\D+', order_id)
        if temp:
            search_params['order_code'] = temp[0]
            search_params1['order__order_code'] = temp[0]
    if o_index:
        search_params['order_id__lt'] = o_index
        search_params1['order__order_id__lt'] = o_index

    con_orders = OrderDetail.objects.order_by('-order_id').filter(**search_params).values_list('order_id', flat=True)
    pic_orders = Picklist.objects.order_by('-order__order_id').exclude(status__icontains='picked').filter(
        **search_params1). \
        distinct().values_list('order__order_id', flat=True)
    orders = list(chain(con_orders, pic_orders))[:20]
    for order in orders:
        temp_data = []
        ind = ''
        view_order = OrderDetail.objects.filter(order_id=order, user=user.id)
        invoice = OrderDetail.objects.filter(user=user.id, order_id=order). \
            aggregate(Sum('invoice_amount'))['invoice_amount__sum']
        if not invoice:
            invoice = 0
        for dat in view_order:
            temp_data.append({'name': dat.customer_name, 'image_url': dat.sku.image_url,
                              'order': dat.order_code + str(dat.order_id),
                              'sku_desc': dat.sku.sku_desc, 'sku_code': dat.sku.wms_code,
                              'quantity': dat.quantity,
                              'price': dat.invoice_amount, 'order_date': str(dat.creation_date.strftime("%d %B %Y"))})
            if str(dat.status) == '1':
                ind = 1
                continue
            else:
                picklist = Picklist.objects.filter(order__user=user.id, order__order_id=order, status__icontains='open')
                ind = 3
                if picklist:
                    ind = 2
                continue

        stage = get_stage_index(order_stages, ind)
        open_orders.append(
            {'order': order, 'invoice': invoice, 'order_data': temp_data, 'stage': stage, 'index': order})
    if (search and not p_index) or not search:
        orders_data['orders'] = open_orders
    if (search and not o_index) or not search:
        orders_data['purchase-orders'] = open_po
    if (order_id or o_index or p_index) and not is_db:
        return HttpResponse(json.dumps(orders_data, cls=DjangoJSONEncoder))

    return HttpResponse(json.dumps(orders_data, cls=DjangoJSONEncoder))


def get_stage_index(stages, ind):
    stage = OrderedDict()
    for i in range(0, len(stages.values())):
        if i < ind:
            stage[stages.values()[i]] = 'done'
        elif i == ind:
            stage[stages.values()[i]] = 'current'
        else:
            stage[stages.values()[i]] = 'not-done'
    return stage


@csrf_exempt
def get_cancelled_putaway(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['id', 'picklist__order__order_id', 'picklist__order__sku__wms_code', 'picklist__order__sku__sku_desc',
           'location__zone__zone', 'location__location', 'quantity']
    if search_term:
        master_data = CancelledLocation.objects.filter(picklist__order__sku_id__in=sku_master_ids). \
            filter(Q(picklist__order__order_id__icontains=search_term) |
                   Q(picklist__order__sku__sku_desc__icontains=search_term) |
                   Q(picklist__order__sku__wms_code__icontains=search_term) |
                   Q(quantity__icontains=search_term) |
                   Q(location__zone__zone__icontains=search_term) |
                   Q(location__location__icontains=search_term),
                   picklist__order__user=user.id, status=1, quantity__gt=0)
    elif order_term:
        col_num = col_num - 1
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = CancelledLocation.objects.filter(picklist__order__sku__user=user.id, status=1, quantity__gt=0,
                                                       picklist__order__sku_id__in=sku_master_ids).order_by(order_data)
    else:
        master_data = CancelledLocation.objects.filter(picklist__order__sku__user=user.id, status=1, quantity__gt=0,
                                                       picklist__order__sku_id__in=sku_master_ids).order_by(
            '-creation_date')
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    count = 0;
    for data in master_data[start_index:stop_index]:
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data.id, data.picklist.order_id)
        zone = data.location.zone.zone
        location = data.location.location
        quantity = data.quantity
        order_id = data.picklist.order.original_order_id
        if not order_id:
            order_id = str(data.picklist.order.order_code) + str(data.picklist.order.order_id)
        temp_data['aaData'].append({'': checkbox, 'Order ID': order_id,
                                    'WMS Code': data.picklist.stock.sku.wms_code,
                                    'Product Description': data.picklist.order.sku.sku_desc, 'Zone': zone,
                                    'Location': location,
                                    'Quantity': quantity, 'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.id},
                                    'id': count})
        count = count + 1


@csrf_exempt
@login_required
@get_admin_user
def cancelled_putaway_data(request, user=''):
    stock = StockDetail.objects.filter(sku__user=user.id).order_by('-receipt_number')
    if stock:
        receipt_number = int(stock[0].receipt_number) + 1
    else:
        receipt_number = 1
    myDict = dict(request.GET.iterlists())
    mod_locations = []
    for i in range(0, len(myDict['id'])):
        status = ''
        data_id = myDict['id'][i]
        zone = myDict['zone'][i]
        location = myDict['location'][i]
        quantity = float(myDict['quantity'][i])
        cancelled_data = CancelledLocation.objects.filter(id=data_id, status=1)
        if not cancelled_data:
            continue
        cancelled_data = cancelled_data[0]
        if location and zone and quantity:
            location_id = LocationMaster.objects.filter(location=location, zone__zone=zone)
            if not location_id:
                status = "Zone, location match doesn't exists"
        else:
            status = 'Missing zone or location or quantity'
        if not status:
            sku_id = cancelled_data.picklist.stock.sku_id
            stock_data = StockDetail.objects.filter(location_id=location_id[0].id, receipt_number=receipt_number,
                                                    sku_id=sku_id,
                                                    sku__user=user.id)
            if stock_data:
                stock_data = stock_data[0]
                setattr(stock_data, 'quantity', float(stock_data.quantity) + quantity)
                stock_data.save()
                new_stock = stock_data
                mod_locations.append(stock_data.location.location)
            else:
                stock_dict = {'location_id': location_id[0].id, 'receipt_number': receipt_number,
                              'receipt_date': datetime.datetime.now(),
                              'sku_id': sku_id, 'quantity': quantity, 'status': 1,
                              'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}
                new_stock = StockDetail(**stock_dict)
                new_stock.save()
                mod_locations.append(new_stock.location.location)
            if cancelled_data.seller_id:
                seller_stock_obj = SellerStock.objects.filter(stock_id=new_stock.id, seller_id=cancelled_data.seller_id)
                if seller_stock_obj:
                    seller_stock_obj = seller_stock_obj[0]
                    seller_stock_obj.quantity += quantity
                else:
                    SellerStock.objects.create(stock_id=new_stock.id, seller_id=cancelled_data.seller_id,
                                               quantity=quantity, status=1, creation_date=datetime.datetime.now())
            cancelled_data.quantity = float(cancelled_data.quantity) - float(quantity)
            if cancelled_data.quantity <= 0:
                cancelled_data.status = 0
            if not cancelled_data.location_id == location_id[0].id:
                setattr(cancelled_data, 'location_id', location_id[0].id)
            cancelled_data.save()
            status = 'Updated Successfully'

    if mod_locations:
        update_filled_capacity(mod_locations, user.id)
    return HttpResponse(status)


@csrf_exempt
@get_admin_user
def get_location_capacity(request, user=''):
    wms_code = request.GET.get('wms_code')
    location = request.GET.get('location')
    filter_params = {'sku__user': user.id}
    capacity = 0
    if wms_code:
        sku_master = SKUMaster.objects.filter(user=user.id, wms_code=wms_code)
        if not sku_master:
            return HttpResponse(json.dumps({'message': 'Invalid WMS code'}))

    if location:
        location_master = LocationMaster.objects.filter(zone__user=user.id, location=location)
        if not location_master:
            return HttpResponse(json.dumps({'message': 'Invalid Location'}))
        filled_capacity = int(location_master[0].filled_capacity)
        max_capacity = int(location_master[0].max_capacity)
        capacity = max_capacity - filled_capacity
        if capacity < 0:
            location_master[0].max_capacity = int(location_master[0].max_capacity) + int(abs(capacity))
            location_master[0].save()
            capacity = 0

    return HttpResponse(json.dumps({'capacity': capacity, 'message': 'Success'}))


@csrf_exempt
@get_admin_user
def generate_seller_invoice(request, user=''):
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
    seller_address = []
    buyer_address = []
    total_taxes = {'cgst_amt': 0, 'sgst_amt': 0, 'igst_amt': 0, 'cess_amt': 0, 'utgst_amt': 0}
    data_dict = dict(request.GET.iterlists())
    seller_summary_dat = data_dict.get('seller_summary_id', '')
    if data_dict.get('po_number', ''):
        seller_summary_dat = seller_summary_dat[0]
    po_number = ''
    if data_dict.get('po_number', ''):
        po_number = data_dict.get('po_number', '')[0]
    seller_summary_dat = seller_summary_dat.split(',')
    all_data = OrderedDict()
    seller_po_ids = []
    sell_ids = {}
    gstin_no = user_profile.gst_number
    taxes_dict = {}
    total_taxable_amt = 0
    for data_id in seller_summary_dat:
        splitted_data = data_id.split(':')
        sell_ids.setdefault('purchase_order__order_id__in', [])
        sell_ids.setdefault('receipt_number__in', [])
        # sell_ids.setdefault('seller_po__seller__name', [])
        sell_ids['purchase_order__order_id__in'].append(splitted_data[0])
        sell_ids['receipt_number__in'].append(splitted_data[1])
        # sell_ids['seller_po__seller__name'].append(splitted_data[2])
    seller_summary = SellerPOSummary.objects.filter(seller_po__seller__user=user.id, **sell_ids)
    seller_summary_ids = seller_summary.values_list('id', flat=True)
    if seller_summary:
        invoice_date = seller_summary.order_by('-creation_date')[0].creation_date
        seller_po_ids = seller_summary.values_list('id', flat=True)
    else:
        invoice_date = datetime.datetime.now()

    invoice_date = get_local_date(user, invoice_date, send_date='true')
    inv_month_year = invoice_date.strftime("%m-%y")
    invoice_date = invoice_date.strftime("%d %b %Y")
    company_name = user_profile.company_name
    if user.username == 'shotang':
        company_name = 'SHProc'

    for summary_id in seller_summary_ids:
        seller_po_summary = SellerPOSummary.objects.get(seller_po__seller__user=user.id, id=summary_id)
        if not order_date:
            order_date = seller_po_summary.seller_po.open_po.creation_date
            order_date = get_local_date(user, order_date, send_date='true')
            order_date = order_date.strftime("%d %b %Y")
        seller = seller_po_summary.seller_po.seller
        open_po = seller_po_summary.seller_po.open_po
        if not seller_address:
            seller_address = company_name + '\n' + user_profile.address + "\nCall: " \
                             + user_profile.phone_number + "\nEmail: " + user.email
        if not buyer_address:
            buyer_address = seller.name + '\n' + seller.address + "\nCall: " \
                            + seller.phone_number + "\nEmail: " + seller.email_id
        discount = 0
        quantity = seller_po_summary.quantity
        mrp_price = seller_po_summary.seller_po.open_po.price
        if seller_po_summary.seller_po.unit_price:
            mrp_price = seller_po_summary.seller_po.unit_price
        amt = float(mrp_price) * float(quantity)

        base_price = "%.2f" % amt
        cgst_tax = seller_po_summary.seller_po.open_po.cgst_tax
        sgst_tax = seller_po_summary.seller_po.open_po.sgst_tax
        igst_tax = seller_po_summary.seller_po.open_po.igst_tax
        cess_tax = seller_po_summary.seller_po.open_po.cess_tax
        utgst_tax = seller_po_summary.seller_po.open_po.utgst_tax
        cgst_amt = cgst_tax * (float(amt) / 100)
        sgst_amt = sgst_tax * (float(amt) / 100)
        igst_amt = igst_tax * (float(amt) / 100)
        cess_amt = cess_tax * (float(amt) / 100)
        utgst_amt = utgst_tax * (float(amt) / 100)
        total_taxes['cgst_amt'] += cgst_amt
        total_taxes['sgst_amt'] += sgst_amt
        total_taxes['igst_amt'] += igst_amt
        total_taxes['cess_amt'] += cess_amt
        total_taxes['utgst_amt'] += utgst_amt
        tax = cgst_amt + sgst_amt + igst_amt + utgst_amt
        taxes_dict = {'cgst_tax': cgst_tax, 'sgst_tax': sgst_tax, 'igst_tax': igst_tax, 'cess_tax': cess_tax,  'utgst_tax': utgst_tax,
                      'cgst_amt': '%.2f' % cgst_amt, 'sgst_amt': '%.2f' % sgst_amt, 'igst_amt': '%.2f' % igst_amt,
                      'cess_amt': cess_amt, 'utgst_amt': utgst_amt}
        invoice_amount = amt + tax - discount

        total_tax += float(tax)
        total_mrp += float(mrp_price)

        unit_price = mrp_price
        unit_price = "%.2f" % unit_price

        # Adding Totals for Invoice
        total_invoice += invoice_amount
        total_quantity += quantity
        total_taxable_amt += amt

        cond = (open_po.sku.sku_code)

        hsn_code = ''
        if open_po.sku.hsn_code:
            hsn_code = str(open_po.sku.hsn_code)
        all_data.setdefault(cond,
                            {'order_id': po_number, 'sku_code': open_po.sku.sku_code, 'title': open_po.sku.sku_desc,
                             'invoice_amount': 0, 'quantity': 0, 'tax': 0, 'unit_price': unit_price, 'amt': 0,
                             'mrp_price': mrp_price, 'discount': discount, 'sku_class': open_po.sku.sku_class,
                             'sku_category': open_po.sku.sku_category, 'sku_size': open_po.sku.sku_size,
                             'hsn_code': hsn_code,
                             'taxes': taxes_dict, 'base_price': base_price})
        all_data[cond]['quantity'] += quantity
        all_data[cond]['invoice_amount'] += invoice_amount
        all_data[cond]['amt'] += amt
        all_data[cond]['tax'] += tax

    for key, value in all_data.iteritems():
        data.append(value)

    order_charges = {}
    total_amt = "%.2f" % (float(total_invoice) - float(total_tax))

    invoice_no = user_profile.prefix + '/' + str(inv_month_year) + '/' + 'A-' + po_number.split('_')[-1]
    if not len(set(sell_ids.get('receipt_number__in', ''))) > 1:
        invoice_no = invoice_no + '/' + str(max(map(int, sell_ids.get('receipt_number__in', ''))))

    detailed_invoice = get_misc_value('detailed_invoice', user.id)

    invoice_data = {'data': data, 'company_name': company_name, 'company_address': user_profile.address,
                    'order_date': order_date, 'email': user.email, 'total_amt': total_amt,
                    'total_quantity': total_quantity, 'total_invoice': "%.2f" % total_invoice, 'order_id': po_number,
                    'order_no': po_number, 'total_tax': "%.2f" % total_tax, 'total_mrp': total_mrp,
                    'invoice_no': invoice_no, 'invoice_date': invoice_date,
                    'price_in_words': number_in_words(total_invoice),
                    'total_invoice_amount': "%.2f" % total_invoice, 'seller_address': seller_address,
                    'customer_address': buyer_address, 'gstin_no': gstin_no,
                    'total_taxable_amt': "%.2f" % total_taxable_amt, 'rounded_invoice_amount': round(total_invoice),
                    'total_taxes': total_taxes, 'detailed_invoice': False, 'is_gst_invoice': True,
                    'order_charges': [], 'hsn_summary': {}}

    invoice_data = build_invoice(invoice_data, user, False)

    return HttpResponse(invoice_data)


@csrf_exempt
@get_admin_user
def check_imei_qc(request, user=''):
    order_id = request.GET['order_id']
    imei = request.GET['imei']
    qc_data = []
    sku_data = {}
    image = ''
    status = ''
    log.info(request.GET.dict())
    try:
        if imei:
            filter_params = {"imei_number": imei, "sku__user": user.id, "status": 1}
            po_mapping = {}
            quality_check = {}
            if order_id:
                quality_check_data = QualityCheck.objects.filter(purchase_order__order_id=order_id,
                                                                 purchase_order__open_po__sku__user=user.id)
                if quality_check_data:
                    for data in quality_check_data:
                        filter_params[
                            'sku__sku_code'] = data.purchase_order.open_po.sku.sku_code
                        filter_params['purchase_order__order_id'] = order_id
                        po_mapping = POIMEIMapping.objects.filter(**filter_params)
                        if po_mapping:
                            quality_check = data
                            break;
                else:
                    status = "imei does not exists"
            if not po_mapping:
                status = "imei does not exists"

            qc_mapping = QCSerialMapping.objects.filter(serial_number__imei_number=imei,
                                                        quality_check__purchase_order__open_po__sku__user=user.id,
                                                        serial_number__status=1)
            if qc_mapping:
                status = "Quality Check completed for imei number " + str(imei)
            if quality_check:
                purchase_data = get_purchase_order_data(quality_check.purchase_order)
                sku = purchase_data['sku']
                image = sku.image_url
                po_reference = '%s%s_%s' % (
                quality_check.purchase_order.prefix, str(quality_check.purchase_order.creation_date). \
                split(' ')[0].replace('-', ''), quality_check.purchase_order.order_id)
                qc_data.append({'id': quality_check.id, 'order_id': po_reference,
                                'quantity': quality_check.po_location.quantity,
                                'accepted_quantity': quality_check.accepted_quantity,
                                'rejected_quantity': quality_check.rejected_quantity})
                sku_data = OrderedDict((('SKU Code', sku.sku_code), ('Product Description', sku.sku_desc),
                                        ('SKU Brand', sku.sku_brand), ('SKU Category', sku.sku_category),
                                        ('SKU Class', sku.sku_class),
                                        ('Color', sku.color)))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(e)
        return HttpResponse("Internal Server Error")
    return HttpResponse(json.dumps({'data_dict': qc_data, 'sku_data': sku_data, 'image': image,
                                    'options': REJECT_REASONS, 'status': status}))


@login_required
@get_admin_user
def check_return_imei(request, user=''):
    return_data = {'status': '', 'data': {}}
    user_profile = UserProfile.objects.get(user_id=user.id)
    try:
        for key, value in request.GET.iteritems():
            sku_code = ''
            order = None
            order_imei_id = ''
            order_imei = OrderIMEIMapping.objects.filter(po_imei__imei_number=value, sku__user=user.id, status=1)
            if not order_imei:
                return_data['status'] = 'Imei Number is invalid'
            else:
                return_mapping = ReturnsIMEIMapping.objects.filter(order_imei_id=order_imei[0].id,
                                                                   order_return__sku__user=user.id, status=1)
                if return_mapping:
                    return_data['status'] = 'Imei number is mapped with the return id %s' % str(
                        return_mapping[0].order_return.return_id)
                    break
                return_data['status'] = 'Success'
                invoice_number = ''
                if not order_imei[0].order:
                    return HttpResponse("IMEI Mapped to Job order")
                order_id = order_imei[0].order.original_order_id
                if not order_id:
                    order_id = order_imei[0].order.order_code + str(order_imei[0].order.order_id)
                if order_imei[0].order_reference:
                    order_id = order_imei[0].order_reference
                    order_imei_id = order_imei[0].id
                shipment_info = ShipmentInfo.objects.filter(order_id=order_imei[0].order_id, order__user=user.id)
                if shipment_info:
                    invoice_number = shipment_info[0].invoice_number
                return_data['data'] = {'sku_code': order_imei[0].order.sku.sku_code, 'invoice_number': invoice_number,
                                       'order_id': order_id, 'sku_desc': order_imei[0].order.title,
                                       'shipping_quantity': 1,
                                       'sor_id': order_imei[0].sor_id, 'quantity': 0, 'order_imei_id': order_imei_id}
                order_return = OrderReturns.objects.filter(order_id=order_imei[0].order.id, sku__user=user.id, status=1)
                if order_return:
                    return_data['data'].update({'id': order_return[0].id, 'return_id': order_return[0].return_id,
                                                'return_type': order_return[0].return_type, 'sor_id': '',
                                                'quantity': order_return[0].quantity})
                log.info(return_data)
                # if user_profile.user_type == 'marketplace_user' and not return_data['data'].get('id', ''):
                #    return_data['status'] = 'Return is not initiated'
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Check Return Imei failed for params " + str(request.GET.dict()) + " and error statement is " + str(e))

    return HttpResponse(json.dumps(return_data))


@csrf_exempt
@login_required
@get_admin_user
def confirm_receive_qc(request, user=''):
    data_dict = ''
    headers = (
    'WMS CODE', 'Order Quantity', 'Received Quantity', 'Measurement', 'Unit Price', 'CSGT(%)', 'SGST(%)', 'IGST(%)',
    'UTGST(%)', 'Amount', 'Description', 'CESS(%)')
    putaway_data = {headers: []}
    total_received_qty = 0
    total_order_qty = 0
    total_price = 0
    total_tax = 0
    pallet_number = ''
    is_putaway = ''
    purchase_data = ''
    btn_class = ''
    seller_receipt_id = 0
    seller_name = user.username
    seller_address = user.userprofile.address
    myDict = dict(request.POST.iterlists())
    if user.username=='milkbasket' and (not request.POST.get('invoice_number', '') and not request.POST.get('dc_number', '')):
        return HttpResponse("Invoice/DC Number  is Mandatory")
    if user.username == 'milkbasket' and (not request.POST.get('invoice_date', '') and not request.POST.get('dc_date', '')):
        return HttpResponse("Invoice/DC Date is Mandatory")
    bill_date = datetime.datetime.now().date().strftime('%d-%m-%Y')
    if request.POST.get('invoice_date', ''):
        bill_date = datetime.datetime.strptime(str(request.POST.get('invoice_date', '')), "%m/%d/%Y").strftime('%d-%m-%Y')
    invoice_num = request.POST.get('invoice_number', '')
    if invoice_num:
        supplier_id = ''
        if request.POST.get('supplier_id', ''):
            supplier_id = request.POST['supplier_id']
        inv_status = po_invoice_number_check(user, invoice_num, supplier_id)
        if inv_status:
            return HttpResponse(inv_status)
    log.info('Request params for ' + user.username + ' is ' + str(myDict))
    try:
        for ind in range(0, len(myDict['id'])):
            myDict.setdefault('imei_number', [])
            imeis_list = [im.split('<<>>')[0] for im in (myDict['rejected'][ind]).split(',')] + myDict['accepted'][
                ind].split(',')
            myDict['imei_number'].append(','.join(imeis_list))
        po_data, status_msg, all_data, order_quantity_dict, \
        purchase_data, data, data_dict, seller_receipt_id = generate_grn(myDict, request, user, is_confirm_receive=True)
        for i in range(0, len(myDict['id'])):
            if not myDict['id'][i]:
                continue
            quality_checks = QualityCheck.objects.filter(purchase_order_id=myDict['id'][i],
                                                         po_location__location__zone__user=user.id,
                                                         status='qc_pending')

            for quality_check in quality_checks:
                qc_dict = {'id': [quality_check.id], 'unit': [myDict['unit'][i]], 'accepted': [myDict['accepted'][i]],
                           'rejected': [myDict['rejected'][i]], 'accepted_quantity': [myDict['accepted_quantity'][i]],
                           'rejected_quantity': [myDict['rejected_quantity'][i]], 'reason': ['']}
                update_quality_check(qc_dict, request, user)

                if myDict.get("accepted", ''):
                    save_qc_serials('accepted', [myDict.get("accepted", '')[i]], user.id, qc_id=quality_check.id)
                if myDict.get("rejected", ''):
                    save_qc_serials('rejected', [myDict.get("rejected", '')[i]], user.id, qc_id=quality_check.id)

        for key, value in all_data.iteritems():
            entry_price = float(key[3]) * float(value)
            if key[10]:
                entry_price -= (entry_price * (float(key[10])/100))
            entry_tax = float(key[4]) + float(key[5]) + float(key[6]) + float(key[7] + float(key[9]))
            if entry_tax:
                entry_price += (float(entry_price) / 100) * entry_tax
            putaway_data[headers].append((key[1], order_quantity_dict[key[0]], value, key[2], key[3], key[4], key[5],
                                          key[6], key[7], entry_price, key[8], key[9]))
            total_order_qty += order_quantity_dict[key[0]]
            total_received_qty += value
            total_price += entry_price
            total_tax += (key[4] + key[5] + key[6] + key[7] + key[9])

        if not status_msg:
            if not purchase_data:
                return HttpResponse('Success')
            address = purchase_data['address']
            address = '\n'.join(address.split(','))
            telephone = purchase_data['phone_number']
            name = purchase_data['supplier_name']
            supplier_email = purchase_data['email_id']
            order_id = data.order_id
            order_date = get_local_date(request.user, data.creation_date)
            order_date = datetime.datetime.strftime(datetime.datetime.strptime(order_date, "%d %b, %Y %I:%M %p"), "%d-%m-%Y")

            profile = UserProfile.objects.get(user=user.id)
            po_reference = '%s%s_%s' % (data.prefix, str(data.creation_date).split(' ')[0].replace('-', ''), order_id)
            table_headers = (
            'WMS Code', 'Supplier Code', 'Description', 'Ordered Quantity', 'Received Quantity', 'Amount')
            '''report_data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                                'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total_price,
                                'po_reference': po_reference, 'total_qty': total_received_qty,
                                'report_name': 'Goods Receipt Note', 'company_name': profile.company_name, 'location': profile.location}'''
            sku_list = putaway_data[putaway_data.keys()[0]]
            sku_slices = generate_grn_pagination(sku_list)
            if seller_receipt_id:
                po_number = str(data.prefix) + str(data.creation_date).split(' ')[0] + '_' + str(data.order_id) \
                            + '/' + str(seller_receipt_id)
            else:
                po_number = str(data.prefix) + str(data.creation_date).split(' ')[0] + '_' + str(data.order_id)
            dc_level_grn = request.POST.get('dc_level_grn', '')
            if dc_level_grn == 'on':
                bill_no = request.POST.get('dc_number', '')
                bill_date = challan_date
            else:
                bill_no = request.POST.get('invoice_number', '')
            report_data_dict = {'data': putaway_data, 'data_dict': data_dict, 'data_slices': sku_slices,
                                'total_received_qty': total_received_qty, 'total_order_qty': total_order_qty,
                                'total_price': total_price, 'total_tax': total_tax, 'address': address,
                                'seller_name': seller_name, 'company_name': profile.company_name,
                                'company_address': profile.address, 'bill_no': bill_no,
                                'po_number': str(data.prefix) + str(data.creation_date).split(' ')[0] + '_' + str(
                                    data.order_id),
                                'order_date': order_date, 'order_id': order_id,
                                'btn_class': btn_class, 'bill_date': str(bill_date)}
            misc_detail = get_misc_value('receive_po', user.id)
            if misc_detail == 'true':
                t = loader.get_template('templates/toggle/grn_form.html')
                rendered = t.render(report_data_dict)
                write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, telephone, po_data,
                                   str(order_date), internal=True, report_type="Goods Receipt Note")
            return render(request, 'templates/toggle/c_putaway_toggle.html', report_data_dict)
        else:
            return HttpResponse(status_msg)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Check Generating GRN failed for params " + str(myDict) + " and error statement is " + str(e))
        return HttpResponse("Generate GRN Failed")


@csrf_exempt
@login_required
@get_admin_user
def generate_po_labels(request, user=''):
    data_dict = dict(request.POST.iterlists())
    order_id = request.POST.get('order_id', '')
    pdf_format = request.POST.get('pdf_format', '')
    data = {}
    data['pdf_format'] = [pdf_format]
    if not order_id:
        return HttpResponse(json.dumps({'message': 'Please send Purchase Order Id', 'data': []}))
    log.info('Request params for Generate PO Labels for ' + user.username + ' is ' + str(data_dict))
    try:
        serial_number = 1
        max_serial = POLabels.objects.filter(sku__user=user.id, custom_label=0).aggregate(Max('serial_number'))['serial_number__max']
        if max_serial:
            serial_number = int(max_serial) + 1
        all_st_purchases = STPurchaseOrder.objects.filter(po__order_id=order_id, open_st__sku__user=user.id)
        all_rw_orders = RWPurchase.objects.filter(purchase_order__order_id=order_id, rwo__vendor__user=user.id)
        po_ids = all_st_purchases.values_list('po_id', flat=True)
        rw_po_ids = all_rw_orders.values_list('purchase_order_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(
            Q(id__in=po_ids) | Q(id__in=rw_po_ids) | Q(open_po__sku__user=user.id), order_id=order_id)
        creation_date = datetime.datetime.now()
        all_po_labels = POLabels.objects.filter(sku__user=user.id, purchase_order__order_id=order_id, status=1)
        for ind in range(0, len(data_dict['wms_code'])):
            order = purchase_orders.filter(open_po__sku__wms_code=data_dict['wms_code'][ind])
            if not order:
                st_purchase = all_st_purchases.filter(open_st__sku__wms_code=data_dict['wms_code'][ind])
                rw_purchase = all_rw_orders.filter(rwo__job_order__product_code__wms_code=data_dict['wms_code'][ind])
                if st_purchase:
                    order = st_purchase[0].po
                    sku = st_purchase[0].open_st.sku
                elif rw_purchase:
                    order = rw_purchase[0].purchase_order
                    sku = rw_purchase[0].rwo.job_order.product_code
            else:
                order = order[0]
                sku = order.open_po.sku
            needed_quantity = int(data_dict['quantity'][ind])
            po_labels = all_po_labels.filter(purchase_order_id=order.id).order_by('serial_number')
            data.setdefault('label', [])
            data.setdefault('wms_code', [])
            data.setdefault('quantity', [])
            for labels in po_labels:
                data['label'].append(labels.label)
                data['quantity'].append(1)
                data['wms_code'].append(labels.sku.wms_code)
                needed_quantity -= 1
            for quantity in range(0, needed_quantity):
                label = str(user.username[:2]).upper() + (str(serial_number).zfill(5))
                data['label'].append(label)
                data['quantity'].append(1)
                label_dict = {'purchase_order_id': order.id, 'serial_number': serial_number, 'label': label,
                              'status': 1,
                              'creation_date': creation_date}
                label_dict['sku_id'] = sku.id
                data['wms_code'].append(sku.wms_code)
                POLabels.objects.create(**label_dict)

                serial_number += 1

        barcodes_list = generate_barcode_dict(pdf_format, data, user)
        return HttpResponse(json.dumps(barcodes_list))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Generating Labels failed for params " + str(data_dict) + " and error statement is " + str(e))
        return HttpResponse("Generate Labels Failed")


@login_required
@get_admin_user
def check_generated_label(request, user=''):
    status = {}
    order_id = request.GET.get('order_id', '')
    label = request.GET.get('label', '')
    log.info('Request params for Check Labels for ' + user.username + ' is ' + str(request.GET.dict()))
    try:
        if order_id and label:
            po_labels = POLabels.objects.filter(sku__user=user.id, label=label)
            if not po_labels:
                status = {'message': 'Invalid Serial Number', 'data': {}}
            elif po_labels[0].purchase_order and not int(po_labels[0].purchase_order.order_id) == int(order_id):
                status = {'message': 'Serial Number is mapped with PO Number ' + get_po_reference(
                    po_labels[0].purchase_order), 'data': {}}
            elif po_labels[0].job_order and not int(po_labels[0].job_order.job_code) == int(order_id):
                status = {'message': 'Serial Number is mapped with JO Number ' + \
                                     str(po_labels[0].job_order.job_code), 'data': {}}
            elif int(po_labels[0].status) == 0:
                if po_labels[0].purchase_order:
                    status = {
                        'message': 'Serial Number already mapped with ' + get_po_reference(po_labels[0].purchase_order),
                        'data': {}}
                elif po_labels[0].job_order:
                    status = {
                        'message': 'Serial Number already mapped with ' + str(po_labels[0].job_order.job_code),
                        'data': {}}
            else:
                po_label = po_labels[0]
                data = {'sku_code': po_label.sku.sku_code, 'label': po_label.label}
                status = {'message': 'Success', 'data': data}
        else:
            status = {'message': 'Missing required parameters', 'data': {}}
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Check Labels failed for params " + str(request.GET.dict()) + " and error statement is " + str(e))
        status = {'message': 'Check Labels Failed', 'data': {}}

    return HttpResponse(json.dumps(status))


@csrf_exempt
@login_required
@get_admin_user
def get_receive_po_style_view(request, user=''):
    try:
        log.info("Request Params for Get Receive PO Style View for user %s is %s" % (
            user.username, str(request.GET.dict())))
        order_id = request.GET.get('order_id', '')
        supplier_status, supplier_user, supplier, supplier_parent = get_supplier_info(request)
        if supplier_status:
            request.user.id = supplier.user
            user.id = supplier.user
        sku_master, sku_master_ids = get_sku_master(user, request.user)
        stpurchase_filter = {'stpurchaseorder__open_st__sku_id__in': sku_master_ids,
                             'stpurchaseorder__po__open_po__isnull': True,
                             'stpurchaseorder__open_st__sku__user': user.id, 'stpurchaseorder__po__order_id': order_id
                             }
        rwpurchase_filter = {'rwpurchase__purchase_order__open_po__isnull': True,
                             'rwpurchase__rwo__job_order__product_code_id__in': sku_master_ids,
                             'rwpurchase__rwo__vendor__user': user.id, 'rwpurchase__purchase_order__order_id': order_id}
        purchase_filter = {'open_po__sku_id__in': sku_master_ids, 'order_id': order_id}
        order_by_list = ['stpurchaseorder__open_st__sku__sequence',
                         'rwpurchase__rwo__job_order__product_code__sequence',
                         'open_po__sku__sequence']
        purchase_orders = PurchaseOrder.objects.filter(Q(**stpurchase_filter) | Q(**rwpurchase_filter) |
                                                       Q(**purchase_filter)).order_by(*order_by_list)
        data_dict = OrderedDict()
        default_po_dict = {'total_order_quantity': 0, 'total_received_quantity': 0, 'total_receivable_quantity': 0}
        for order in purchase_orders:
            order_data = get_purchase_order_data(order)
            sku = order_data['sku']
            sku_class = sku.sku_class
            sku_size = sku.sku_size
            size_type = ''
            size_type_obj = sku.skufields_set.filter(field_type='size_type')
            all_sizes = []
            if size_type_obj:
                size_type = size_type_obj[0].field_value
                size_master = SizeMaster.objects.filter(size_name=size_type, user=user.id)
                if size_master:
                    all_sizes = size_master[0].size_value.split('<<>>')
            receivable_quantity = float(order_data['order_quantity']) - float(order.received_quantity)
            if receivable_quantity < 0:
                receivable_quantity = 0
            data_dict.setdefault(size_type, {'sizes_list': [], 'styles': {}, 'all_sizes': all_sizes})
            if sku_size not in data_dict[size_type]['sizes_list']:
                data_dict[size_type]['sizes_list'].append(sku_size)
	    if not data_dict[size_type]['all_sizes']:
                data_dict[size_type]['all_sizes'] = data_dict[size_type]['sizes_list']
            style_data = {'style_code': sku_class, 'style_name': sku.style_name, 'brand': sku.sku_brand,
                          'category': sku.sku_category}
            data_dict[size_type]['styles'].setdefault(sku_class, {'style_data': style_data, 'sizes': {},
                                                                  'po_data': copy.deepcopy(default_po_dict)})
            order_quantity = order_data['order_quantity']
            if supplier_status:
                order_quantity = order_quantity - order_data['intransit_quantity'] - order.received_quantity
                if order_quantity < 0:
                    order_quantity = 0
            data_dict[size_type]['styles'][sku_class]['sizes'][sku_size] = order_quantity
            data_dict[size_type]['styles'][sku_class]['po_data']['total_order_quantity'] += order_quantity
            data_dict[size_type]['styles'][sku_class]['po_data']['total_received_quantity'] += order.received_quantity
            data_dict[size_type]['styles'][sku_class]['po_data']['total_receivable_quantity'] += receivable_quantity
        order_detail_id = ''
        if purchase_orders:
            order_mapping = OrderMapping.objects.filter(mapping_type='PO',mapping_id=purchase_orders[0].id)
            if order_mapping and order_mapping[0].order.order_code == 'CO':
                order_detail_id = order_mapping[0].order.original_order_id
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Get Receive PO Style View failed for params %s on %s and error statement is %s" % (
            str(request.GET.dict()), str(get_local_date(user, datetime.datetime.now())), str(e)))
        return HttpResponse(json.dumps({'data_dict': {}, 'status': 0, 'message': 'Failed'}))
    return HttpResponse(json.dumps({'data_dict': data_dict, 'order_detail_id': order_detail_id, 'status': 1}, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def save_supplier_po(request, user=''):

    supplier_status, supplier_user, supplier, supplier_parent = get_supplier_info(request)
    if not supplier_status:
        return HttpResponse("Fail")
    request.user.id = supplier.user
    user.id = supplier.user
    myDict = json.loads(request.POST.get('data', '{}'))
    po_data = {}
    expected_date = request.POST.get('expected_date', '')
    po_number = request.POST.get('po_number', '')
    for size_type, styles in myDict.iteritems():
        for style_name, style_data in styles["styles"].iteritems():
            qty_status = False
            dt_status = False
            temp_po_data = {'sizes':{}, 'remarks': ''}
            for size, quantity in style_data["sizes"].iteritems():
                if quantity:
                    temp_po_data['sizes'][size] = quantity
                    qty_status = True
            if qty_status and style_data.get('expected_date', ''):
                temp_po_data['expected_date'] = style_data['expected_date']
                dt_status = True
            elif qty_status and expected_date:
                temp_po_data['expected_date']  = expected_date
                dt_status = True
            if style_data.get('remarks', ''):
                temp_po_data['remarks'] = style_data['remarks']
            if qty_status and not dt_status:
                return HttpResponse("Please Select Date")
            elif qty_status:
                po_data[style_name] = temp_po_data

    print po_data
    if not po_data:
        return HttpResponse("Please Enter Quantity")
    pos =  PurchaseOrder.objects.filter(open_po__sku__user=user.id, order_id=po_number)
    for style, po in po_data.iteritems():
        style_po = pos.filter(open_po__sku__sku_class=style)
        for size, quantity in po['sizes'].iteritems():
            size_po = style_po.filter(open_po__sku__sku_size=size)
            if not size_po or not quantity:
                continue
            size_po = size_po[0]
            size_po.intransit_quantity = size_po.intransit_quantity + float(quantity)
            size_po.save()
        if po['remarks']:
            style_po.update(remarks=po['remarks'])
        if po['expected_date']:
            date = po['expected_date'].split('/')
            style_po.update(expected_date=datetime.date(int(date[2]), int(date[0]), int(date[1])))
    return HttpResponse("Success")


def get_primary_suggestions(request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    purchase_filter = {'open_po__sku_id__in': sku_master_ids, 'open_po__sku__user': user.id,
                       'primarysegregation__status': 1}
    stpurchase_filter = {'stpurchaseorder__open_st__sku_id__in': sku_master_ids,
                         'stpurchaseorder__open_st__sku__user': user.id, 'primarysegregation__status': 1}
    rwpurchase_filter = {'rwpurchase__rwo__job_order__product_code_id__in': sku_master_ids,
                             'rwpurchase__rwo__vendor__user': user.id, 'primarysegregation__status': 1}
    purchase_orders = PurchaseOrder.objects.filter(Q(**stpurchase_filter) | Q(**rwpurchase_filter) |
                                                   Q(**purchase_filter))
    return purchase_orders


def get_primary_suggestions_data(request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    purchase_filter = {'purchase_order__open_po__sku_id__in': sku_master_ids, 'purchase_order__open_po__sku__user': user.id,
                       'status': 1}
    stpurchase_filter = {'purchase_order__stpurchaseorder__open_st__sku_id__in': sku_master_ids,
                         'purchase_order__stpurchaseorder__open_st__sku__user': user.id, 'status': 1}
    rwpurchase_filter = {'purchase_order__rwpurchase__rwo__job_order__product_code_id__in': sku_master_ids,
                         'purchase_order__rwpurchase__rwo__vendor__user': user.id, 'status': 1}
    segregations = PrimarySegregation.objects.filter(Q(**stpurchase_filter) | Q(**rwpurchase_filter) |
                                                   Q(**purchase_filter))
    return segregations


@csrf_exempt
def get_segregation_pos(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    lis = ['PO Number', 'Order Date', 'Supplier ID', 'Supplier Name', 'Order Type']
    purchase_orders = get_primary_suggestions(request, user)
    if search_term:
        orders = purchase_orders.filter(Q(open_po__supplier__name__icontains=search_term) |
            Q(open_po__supplier__id__icontains=search_term) | Q(order_id__icontains=search_term) |
            Q(creation_date__regex=search_term) | Q(stpurchaseorder__open_st__warehouse__id__icontains=search_term) |
            Q(stpurchaseorder__open_st__warehouse__username__icontains=search_term) |
            Q(rwpurchase__rwo__vendor__id__icontains=search_term) | Q(rwpurchase__rwo__vendor__name__icontains=search_term))
    elif order_term:
        orders = purchase_orders
    primary_segregations = PrimarySegregation.objects.filter(status=1,
                                 purchase_order_id__in=list(orders.values_list('id', flat=True))). \
                                 annotate(proc_sum=F('sellable') + F('non_sellable')).\
                                 filter(quantity__gt=F('proc_sum')).values_list('purchase_order_id', flat=True)
    orders = orders.filter(id__in=primary_segregations)
    order_ids = orders.values_list('order_id', flat=True).distinct()
    temp_data['recordsTotal'] = order_ids.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for order_id in order_ids:
        order = orders.filter(order_id=order_id)[0]
        order_data = get_purchase_order_data(order)
        order_type = 'Purchase Order'
        if RWPurchase.objects.filter(purchase_order_id=order.id):
            order_type = 'Returnable Work Order'
        elif STPurchaseOrder.objects.filter(po_id=order.id):
            order_type = 'Stock Transfer'
        po_reference = '%s%s_%s' % (
        order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order.order_id)
        temp_data['aaData'].append({'DT_RowId': order.order_id, 'Supplier ID': order_data['supplier_id'],
                                    'Supplier Name': order_data['supplier_name'], 'Order Type': order_type,
                                    ' Order ID': order.order_id,
                                    'Order Date': get_local_date(request.user, order.creation_date),
                                    'DT_RowClass': 'results', 'PO Number': po_reference,
                                    'DT_RowAttr': {'data-id': order.order_id}})

    order_data = lis[col_num]
    if order_term == 'asc':
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(order_data))
    else:
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(order_data), reverse=True)
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


@csrf_exempt
@login_required
@get_admin_user
def get_po_segregation_data(request, user=''):
    segregations = get_primary_suggestions_data(request, user)
    order_id = request.GET['order_id']
    segregations = segregations.select_related('purchase_order', 'batch_detail').\
                                filter(purchase_order__order_id=order_id)
    if not segregations:
        return HttpResponse("No Data found")
    po_reference = get_po_reference(segregations[0].purchase_order)
    orders = []
    order_data = {}
    order_ids = []
    shelf_life_ratio = get_misc_value('shelf_life_ratio', user.id)
    for segregation_obj in segregations:
        #deviation_remarks = {'Price Deviation': False, 'MRP Deviation': False, 'Shelf Life Ratio Exceeded': False,
        #                     'Tax Rate Deviation': False}
        deviation_remarks = []
        if segregation_obj.batch_detail:
            if segregation_obj.batch_detail.buy_price != segregation_obj.purchase_order.open_po.price:
                #deviation_remarks['Price Deviation'] = True
                deviation_remarks.append('Price Deviation')
            if segregation_obj.batch_detail.mrp != segregation_obj.purchase_order.open_po.mrp:
                #deviation_remarks['MRP Deviation'] = True
                deviation_remarks.append('MRP Deviation')
            if segregation_obj.batch_detail.expiry_date and segregation_obj.purchase_order.open_po.sku.shelf_life\
                    and shelf_life_ratio:
                sku_days = int(segregation_obj.purchase_order.open_po.sku.shelf_life * (float(shelf_life_ratio)/100))
                stock_days = (segregation_obj.batch_detail.expiry_date - \
                              segregation_obj.batch_detail.creation_date.date()).days
                if sku_days > stock_days:
                    deviation_remarks.append('Shelf Life Ratio Exceeded')
                    #deviation_remarks['Shelf Life Ratio Exceeded'] = True
            if segregation_obj.batch_detail.tax_percent:
                open_po = segregation_obj.purchase_order.open_po
                seg_tax = segregation_obj.batch_detail.tax_percent
                po_tax = open_po.cgst_tax + open_po.sgst_tax + open_po.igst_tax + open_po.cess_tax + open_po.utgst_tax
                if seg_tax != po_tax:
                    deviation_remarks.append('Tax Rate Deviation')

        order = segregation_obj.purchase_order
        order_data = get_purchase_order_data(order)
        quantity = float(segregation_obj.quantity) - float(segregation_obj.sellable) - float(segregation_obj.non_sellable)
        sku_details = json.loads(
            serializers.serialize("json", [order_data['sku']], indent=1, use_natural_foreign_keys=True, fields=(
            'sku_code', 'wms_code', 'sku_desc', 'color', 'sku_class', 'sku_brand', 'sku_category', 'image_url',
            'load_unit_handle')))
        if quantity > 0:
            sku_extra_data, product_images, order_ids = get_order_json_data(user, mapping_id=order.id,
                                                                            mapping_type='PO',
                                                                            sku_id=order_data['sku_id'],
                                                                            order_ids=order_ids)
            data_dict = {'segregation_id': segregation_obj.id,'order_id': order.id, 'wms_code': order_data['wms_code'],
                            'sku_desc': order_data['sku_desc'],
                            'quantity': quantity, 'sellable': quantity,
                            'non_sellable': 0,
                            'name': str(order.order_id) + '-' + str(
                                re.sub(r'[^\x00-\x7F]+', '', order_data['wms_code'])),
                            'price': order_data['price'], 'order_type': order_data['order_type'],
                            'unit': order_data['unit'],
                            'sku_extra_data': sku_extra_data, 'product_images': product_images,
                            'sku_details': sku_details, 'deviation_remarks': '\n'.join(deviation_remarks)}
            if segregation_obj.batch_detail:
                batch_detail = segregation_obj.batch_detail
                data_dict['batch_no'] = batch_detail.batch_no
                data_dict['mrp'] = batch_detail.mrp
                data_dict['buy_price'] = batch_detail.buy_price
                data_dict['mfg_date'] = ''
                if batch_detail.manufactured_date:
                    data_dict['mfg_date'] = batch_detail.manufactured_date.strftime('%m/%d/%Y')
                data_dict['exp_date'] = ''
                if batch_detail.expiry_date:
                    data_dict['exp_date'] = batch_detail.expiry_date.strftime('%m/%d/%Y')
                data_dict['tax_percent'] = batch_detail.tax_percent
            orders.append([data_dict])
    supplier_name, order_date, expected_date, remarks = '', '', '', ''
    if segregations:
        purchase_order = segregations[0].purchase_order
        supplier_name = order_data['supplier_name']
        order_date = get_local_date(user, purchase_order.creation_date)
        remarks = purchase_order.remarks
    return HttpResponse(json.dumps({'data': orders, 'order_id': order_id, \
                                    'supplier_id': order_data['supplier_id'],\
                                    'po_reference': po_reference, 'order_ids': order_ids,
                                    'supplier_name': supplier_name, 'order_date': order_date,
                                    'remarks': remarks
                        }))


@csrf_exempt
@login_required
@get_admin_user
def confirm_primary_segregation(request, user=''):
    data_dict = dict(request.POST.iterlists())
    log.info('Request params for ' + user.username + ' is ' + str(data_dict))
    try:
        for ind in range(0, len(data_dict['segregation_id'])):
            segregation_obj = PrimarySegregation.objects.select_related('batch_detail', 'purchase_order').\
                                                            filter(id=data_dict['segregation_id'][ind])
            if not segregation_obj:
                continue
            segregation_obj = segregation_obj[0]
            batch_dict = {}
            if segregation_obj.batch_detail:
                batch_detail = segregation_obj.batch_detail
                manufactured_date = ''
                if batch_detail.manufactured_date:
                    manufactured_date = batch_detail.manufactured_date.strftime('%m/%d/%Y')
                expiry_date = ''
                if batch_detail.expiry_date:
                    expiry_date = batch_detail.expiry_date.strftime('%m/%d/%Y')
                batch_dict = {'transact_type': 'po_loc', 'batch_no': batch_detail.batch_no,
                              'expiry_date': expiry_date,
                              'manufactured_date': manufactured_date,
                              'tax_percent': batch_detail.tax_percent,
                              'mrp': batch_detail.mrp, 'buy_price': batch_detail.buy_price
                              }
            sellable = data_dict['sellable'][ind]
            non_sellable = data_dict['non_sellable'][ind]
            if not sellable:
                sellable = 0
            if not non_sellable:
                non_sellable = 0
            sellable = float(sellable)
            non_sellable = float(non_sellable)
            purchase_data = get_purchase_order_data(segregation_obj.purchase_order)
            seller_received_dict = get_seller_received_list(segregation_obj.purchase_order, user)
            if sellable:
                put_zone = purchase_data['zone']
                if put_zone:
                    put_zone = put_zone.zone
                else:
                    put_zone = ZoneMaster.objects.filter(zone='DEFAULT', user=user.id)
                    if not put_zone:
                        create_default_zones(user, 'DEFAULT', 'DFLT1', 9999)
                        put_zone = ZoneMaster.objects.filter(zone='DEFAULT', user=user.id)[0]
                    else:
                        put_zone = put_zone[0]
                    put_zone = put_zone.zone
                temp_dict = {'received_quantity': sellable, 'user': user.id, 'data': segregation_obj.purchase_order,
                             'pallet_number': '', 'pallet_data': {}}
                seller_received_dict, seller_summary_dict = get_quality_check_seller(seller_received_dict, temp_dict,
                                                                                     purchase_data)
                save_po_location(put_zone, temp_dict, seller_received_list=seller_summary_dict, run_segregation=False,
                                 batch_dict=batch_dict)
            sellable_qty = get_decimal_limit(user.id, (float(segregation_obj.sellable) + sellable))
            segregation_obj.sellable = sellable_qty
            if non_sellable:
                put_zone = ZoneMaster.objects.filter(zone='Non Sellable Zone', user=user.id)
                if not put_zone:
                    create_default_zones(user, 'Non Sellable Zone', 'Non-Sellable1', 10001)
                    put_zone = ZoneMaster.objects.filter(zone='Non Sellable Zone', user=user.id)[0]
                else:
                    put_zone = put_zone[0]
                put_zone = put_zone.zone
                temp_dict = {'received_quantity': non_sellable, 'user': user.id, 'data': segregation_obj.purchase_order,
                             'pallet_number': '', 'pallet_data': {}}
                seller_received_dict, seller_summary_dict = get_quality_check_seller(seller_received_dict, temp_dict,
                                                                                     purchase_data)
                save_po_location(put_zone, temp_dict, seller_received_list=seller_summary_dict, run_segregation=False,
                                 batch_dict=batch_dict)
            non_sellable_qty = get_decimal_limit(user.id, (float(segregation_obj.non_sellable) + non_sellable))
            segregation_obj.non_sellable = non_sellable_qty
            if (sellable_qty + non_sellable_qty) >= float(segregation_obj.quantity):
                segregation_obj.status = 0
            segregation_obj.save()
        return HttpResponse("Updated Successfully")
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Add Primary Segregation failed for params " + str(data_dict) + " and error statement is " + str(e))
        return HttpResponse("Add Segregation Failed")

@csrf_exempt
@login_required
@get_admin_user
def last_transaction_details(request, user=''):
    get_supplier_each_seller_list = []
    check_supplier = ''
    seller_id = 0
    wms_code_list = request.POST.getlist('wms_code', [])
    supplier_name_list = request.POST.getlist('supplier_id', [])
    seller_id_list = request.POST.getlist('seller_id', [])
    if seller_id_list:
        seller_id = seller_id_list[0].split(':')[0]
    get_supplier_each_seller_list = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
    if get_supplier_each_seller_list:
        check_supplier = get_supplier_each_seller_list[0].supplier
    sku_wise_obj = PurchaseOrder.objects.filter(open_po__sku__wms_code__in=wms_code_list, open_po__sku__user=user.id).order_by('-creation_date')
    if check_supplier:
        supplier_wise_obj = sku_wise_obj.filter(open_po__supplier__id__in = get_supplier_each_seller_list).order_by('-creation_date')
    else:
        supplier_wise_obj = sku_wise_obj.filter(open_po__supplier__id__in = supplier_name_list).order_by('-creation_date')
    sku_wise_list = []
    supplier_wise_list = []
    for data in sku_wise_obj[0:3]:
        data_dict = {}
        data_dict['total_tax'] = data.open_po.sgst_tax + data.open_po.igst_tax + data.open_po.cess_tax + data.open_po.cgst_tax + data.open_po.utgst_tax
        data_dict['po_date'] = str(data.po_date)
        data_dict['supplier_name'] = data.open_po.supplier.name
        data_dict['received_quantity'] = data.received_quantity
        data_dict['price'] = data.open_po.price
        data_dict['po_number'] = get_po_reference(data)
        sku_wise_list.append(data_dict)
    for data in supplier_wise_obj[0:3]:
        supplier_data_dict = {}
        supplier_data_dict['total_tax'] = data.open_po.sgst_tax + data.open_po.igst_tax + data.open_po.cess_tax + data.open_po.cgst_tax + data.open_po.utgst_tax
        supplier_data_dict['po_date'] = str(data.po_date)
        supplier_data_dict['supplier_name'] = data.open_po.supplier.name
        supplier_data_dict['received_quantity'] = data.received_quantity
        supplier_data_dict['price'] = data.open_po.price
        supplier_data_dict['po_number'] = get_po_reference(data)
        supplier_wise_list.append(supplier_data_dict)
    data_resp = {}
    data_resp['sku_wise_table_data'] = sku_wise_list
    data_resp['wms_code_list'] = wms_code_list
    data_resp['supplier_wise_table_data'] = supplier_wise_list
    return HttpResponse(json.dumps(data_resp))


@csrf_exempt
@login_required
@get_admin_user
def supplier_invoice_data(request, user=''):
    user_profile = UserProfile.objects.get(user_id=user.id)
    tab_type = request.GET.get('tabType', '')
    if user_profile.warehouse_type == 'DIST':
        headers = DIST_SUPPLIER_INVOICE_HEADERS
    else:
        if tab_type == 'POChallans':
            headers = ['Challan ID'] + WH_SUPPLIER_PO_CHALLAN_HEADERS
        elif tab_type == 'SupplierInvoices':
            headers = ["Invoice ID"] + WH_SUPPLIER_INVOICE_HEADERS
        else:
            headers = WH_SUPPLIER_PO_CHALLAN_HEADERS
    return HttpResponse(json.dumps({'headers': headers}))


@csrf_exempt
def get_supplier_invoice_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
			      filters):
    ''' Supplier Invoice datatable code '''

    user_profile = UserProfile.objects.get(user_id=user.id)
    admin_user = get_priceband_admin_user(user)
    lis = ['purchase_order__open_po__supplier__name', 'purchase_order__open_po__supplier__name',
           'purchase_order__open_po__order_quantity', 'quantity', 'id', 'invoice_number']
    user_filter = {'purchase_order__open_po__sku__user': user.id, 'order_status_flag': 'supplier_invoices'}
    #result_values = ['receipt_number', 'purchase_order__order_id',
    result_values = ['purchase_order__open_po__supplier__name', 'invoice_number']
                     #'purchase_order__creation_date', 'id', 'invoice_number']
    field_mapping = {'date_only': 'purchase_order__creation_date'}
    is_marketplace = False

    rtv_filter = {}
    for key, val in user_filter.iteritems():
        rtv_filter['seller_po_summary__%s' % key] = val
    return_ids = ReturnToVendor.objects.filter(**rtv_filter).values_list('seller_po_summary_id').distinct().\
                                annotate(tot_proc=Sum('quantity'), tot=Sum('seller_po_summary__quantity'),\
                                tot_count=Count('seller_po_summary__quantity')).\
                                annotate(final_val=F('tot')/Cast(F('tot_count'), FloatField())).\
                                filter(tot_proc__gte=F('final_val')).\
                                values_list('seller_po_summary_id', flat=True)

    if search_term:
        #if 'date_only' in lis:
            #lis1 = copy.deepcopy(lis)
            #lis1 = map(lambda x: x if x not in ['date_only'] else field_mapping['date_only'], lis1)

        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(lis, search_term)
        master_data = SellerPOSummary.objects.exclude(id__in=return_ids).filter(search_query, **user_filter)\
                            .values(*result_values).distinct().annotate(total_received=Sum('quantity'),\
                            total_ordered=Sum('purchase_order__open_po__order_quantity'))

    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            master_data = SellerPOSummary.objects.exclude(id__in=return_ids).filter(**user_filter).values(*result_values).distinct()\
                                         .annotate(total_received=Sum('quantity'),\
                                         total_ordered=Sum('purchase_order__open_po__order_quantity')).order_by(lis[col_num])
        else:
            master_data = SellerPOSummary.objects.exclude(id__in=return_ids).filter(**user_filter).values(*result_values).distinct()\
                                         .annotate(total_received=Sum('quantity'),\
                                         total_ordered=Sum('purchase_order__open_po__order_quantity'))\
                                         .order_by('-%s' % lis[col_num])

    else:
        master_data = SellerPOSummary.objects.exclude(id__in=return_ids).filter(**user_filter)\
                                     .values(*result_values).distinct().annotate(total_received=Sum('quantity'),\
                                     total_ordered=Sum('purchase_order__open_po__order_quantity'))

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data in master_data[start_index:stop_index]:

        #po = PurchaseOrder.objects.filter(order_id=data['purchase_order__order_id'])
        #grn_number = "%s/%s" %(get_po_reference(po[0]), data['receipt_number'])
        #po_date = str(data['date_only'])
        #seller_summary_obj = SellerPOSummary.objects.filter(receipt_number=data['receipt_number'],\
                                            #purchase_order__order_id=data['purchase_order__order_id'],\
                                            #purchase_order__open_po__supplier__name=data['purchase_order__open_po__supplier__name'])
        seller_summary_obj = SellerPOSummary.objects.exclude(id__in=return_ids).filter(**user_filter)\
                                            .filter(invoice_number=data['invoice_number'],\
                                             purchase_order__open_po__supplier__name=data['purchase_order__open_po__supplier__name'])
        tot_amt, rem_quantity = 0, 0
        for seller_sum in seller_summary_obj:
            rem_quantity = 0
            price = seller_sum.purchase_order.open_po.price
            temp_qty = float(seller_sum.quantity)
            processed_val = seller_sum.returntovendor_set.filter().aggregate(Sum('quantity'))['quantity__sum']
            if processed_val:
                temp_qty -= processed_val
            rem_quantity += temp_qty
            quantity = rem_quantity
            tot_tax_perc = seller_sum.purchase_order.open_po.cgst_tax +\
                           seller_sum.purchase_order.open_po.sgst_tax + seller_sum.purchase_order.open_po.igst_tax
            if seller_sum.batch_detail:
                price = seller_sum.batch_detail.buy_price
                tot_tax_perc = seller_sum.batch_detail.tax_percent
            tot_price = price * quantity
            tot_tax = float(tot_price * tot_tax_perc) / 100
            tot_amt += (tot_price + tot_tax)

        data_dict = OrderedDict((('GRN No', ''),
                                 ('Supplier Name', data['purchase_order__open_po__supplier__name']),
                                 ('check_field', 'Supplier Name'),
                                 ('PO Quantity', data['total_ordered']),
                                 ('Received Quantity', quantity),
                                 ('Order Date', ''),
                                 ('Total Amount', tot_amt), ('id', data.get('id', 0)),
                                 ('Invoice ID', data['invoice_number']),
                                 ('receipt_number', ''),
                                 ('purchase_order__order_id', '')
                               ))
        temp_data['aaData'].append(data_dict)


@csrf_exempt
def get_po_challans_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                         filters):
    ''' Supplier Invoice datatable code '''

    user_profile = UserProfile.objects.get(user_id=user.id)
    admin_user = get_priceband_admin_user(user)
    #lis = ['purchase_order__id', 'purchase_order__id', 'purchase_order__open_po__supplier__name',
           #'purchase_order__open_po__order_quantity', 'quantity', 'date_only', 'id', 'challan_number']
    lis = ['challan_number', 'challan_number', 'purchase_order__open_po__supplier__name', 'challan_number',
           'challan_number', 'challan_number', 'challan_number', 'challan_number']
    filt_lis = ['challan_number', 'purchase_order__order_id', 'purchase_order__open_po__supplier__name']
    user_filter = {'purchase_order__open_po__sku__user': user.id, 'order_status_flag': 'po_challans'}
    result_values = ['challan_number', 'receipt_number', 'purchase_order__order_id', 'purchase_order__open_po__supplier__name']
                     #'purchase_order__creation_date', 'id']
    field_mapping = {'date_only': 'purchase_order__creation_date'}
    is_marketplace = False

    rtv_filter = {}
    for key, val in user_filter.iteritems():
        rtv_filter['seller_po_summary__%s' % key] = val
    return_ids = ReturnToVendor.objects.filter(**rtv_filter).values_list('seller_po_summary_id').distinct().\
                                annotate(tot_proc=Sum('quantity'), tot=Sum('seller_po_summary__quantity'),\
                                tot_count=Count('seller_po_summary__quantity')).\
                                annotate(final_val=F('tot')/Cast(F('tot_count'), FloatField())).\
                                filter(tot_proc__gte=F('final_val')).\
                                values_list('seller_po_summary_id', flat=True)

    if search_term:
        lis1 = copy.deepcopy(filt_lis)
        if 'date_only' in lis:
            lis1 = map(lambda x: x if x not in ['date_only'] else field_mapping['date_only'], lis1)

        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(lis1, search_term)
        master_data = SellerPOSummary.objects.exclude(id__in=return_ids).filter(search_query, **user_filter)\
                            .values(*result_values).distinct().annotate(total_received=Sum('quantity'),\
                            total_ordered=Sum('purchase_order__open_po__order_quantity'),\
                            date_only=Cast(field_mapping['date_only'], DateField()))

    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            master_data = SellerPOSummary.objects.exclude(id__in=return_ids).filter(**user_filter).values(*result_values).distinct()\
                                         .annotate(total_received=Sum('quantity'),\
                                         total_ordered=Sum('purchase_order__open_po__order_quantity'),\
                                         date_only=Cast(field_mapping['date_only'], DateField())).order_by(lis[col_num])
        else:
            master_data = SellerPOSummary.objects.exclude(id__in=return_ids).filter(**user_filter).values(*result_values).distinct()\
                                         .annotate(total_received=Sum('quantity'),\
                                         total_ordered=Sum('purchase_order__open_po__order_quantity'),\
                                         date_only=Cast(field_mapping['date_only'], DateField()))\
                                         .order_by('-%s' % lis[col_num])

    else:
        master_data = SellerPOSummary.objects.exclude(id__in=return_ids).filter(**user_filter)\
                                     .values(*result_values).distinct().annotate(total_received=Sum('quantity'),\
                                     total_ordered=Sum('purchase_order__open_po__order_quantity'),\
                                     date_only=Cast(field_mapping['date_only'], DateField()))

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data in master_data[start_index:stop_index]:

        po = PurchaseOrder.objects.filter(order_id=data['purchase_order__order_id'])[0]
        grn_number = "%s/%s" %(get_po_reference(po), data['receipt_number'])
        po_date = str(data['date_only'])
        seller_summary_obj = SellerPOSummary.objects.exclude(id__in=return_ids).filter(receipt_number=data['receipt_number'],\
                                            purchase_order__order_id=data['purchase_order__order_id'],\
                                            purchase_order__open_po__supplier__name=data['purchase_order__open_po__supplier__name'])
 
        tot_amt, rem_quantity = 0, 0
        for seller_sum in seller_summary_obj:
            rem_quantity = 0
            temp_qty = float(seller_sum.quantity)
            processed_val = seller_sum.returntovendor_set.filter().aggregate(Sum('quantity'))['quantity__sum']
            if processed_val:
                temp_qty -= processed_val
            rem_quantity += temp_qty
            price = seller_sum.purchase_order.open_po.price
            quantity = rem_quantity
            tot_tax_perc = seller_sum.purchase_order.open_po.cgst_tax +\
                           seller_sum.purchase_order.open_po.sgst_tax + seller_sum.purchase_order.open_po.igst_tax
            if seller_sum.batch_detail:
                price = seller_sum.batch_detail.buy_price
                tot_tax_perc = seller_sum.batch_detail.tax_percent
            tot_price = price * quantity
            tot_tax = float(tot_price * tot_tax_perc) / 100
            tot_amt += (tot_price + tot_tax)

        data_dict = OrderedDict((('GRN No', grn_number),
                                 ('Supplier Name', data['purchase_order__open_po__supplier__name']),
                                 ('check_field', 'Supplier Name'),
                                 ('PO Quantity', data['total_ordered']),
                                 ('Received Quantity', quantity),
                                 ('Order Date', po_date),
                                 ('Total Amount', tot_amt), ('id', data.get('id', 0)),
                                 ('Challan ID', data['challan_number']),
                                 ('receipt_number', data['receipt_number']),
                                 ('purchase_order__order_id', data['purchase_order__order_id'])
                               ))
        temp_data['aaData'].append(data_dict)


@csrf_exempt
def get_processed_po_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                         filters):
    ''' Supplier Invoice datatable code '''

    user_profile = UserProfile.objects.get(user_id=user.id)
    admin_user = get_priceband_admin_user(user)
    lis = ['purchase_order__id', 'purchase_order__order_id', 'purchase_order__open_po__supplier__name',
           'purchase_order__open_po__order_quantity', 'quantity', 'date_only', 'id']
    user_filter = {'purchase_order__open_po__sku__user': user.id, 'order_status_flag': 'processed_pos'}
    result_values = ['receipt_number', 'purchase_order__order_id', 'purchase_order__open_po__supplier__name']
                     #'purchase_order__creation_date', 'id']
    field_mapping = {'date_only': 'purchase_order__creation_date'}
    is_marketplace = False

    if search_term:
        if 'date_only' in lis:
            lis1 = copy.deepcopy(lis)
            lis1 = map(lambda x: x if x not in ['date_only'] else field_mapping['date_only'], lis1)

        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(lis1[1:5], search_term)
        master_data = SellerPOSummary.objects.filter(search_query, **user_filter)\
                            .values(*result_values).distinct().annotate(total_received=Sum('quantity'),\
                            total_ordered=Sum('purchase_order__open_po__order_quantity'),\
                            date_only=Cast(field_mapping['date_only'], DateField()))

    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            master_data = SellerPOSummary.objects.filter(**user_filter).values(*result_values).distinct()\
                                         .annotate(total_received=Sum('quantity'),\
                                         total_ordered=Sum('purchase_order__open_po__order_quantity'),\
                                         date_only=Cast(field_mapping['date_only'], DateField())).order_by(lis[col_num])
        else:
            master_data = SellerPOSummary.objects.filter(**user_filter).values(*result_values).distinct()\
                                         .annotate(total_received=Sum('quantity'),\
                                         total_ordered=Sum('purchase_order__open_po__order_quantity'),\
                                         date_only=Cast(field_mapping['date_only'], DateField()))\
                                         .order_by('-%s' % lis[col_num])

    else:
        master_data = SellerPOSummary.objects.filter(**user_filter)\
                                     .values(*result_values).distinct().annotate(total_received=Sum('quantity'),\
                                     total_ordered=Sum('purchase_order__open_po__order_quantity'),\
                                     date_only=Cast(field_mapping['date_only'], DateField()))

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data in master_data[start_index:stop_index]:

        po = PurchaseOrder.objects.filter(order_id=data['purchase_order__order_id'])[0]
        grn_number = "%s/%s" %(get_po_reference(po), data['receipt_number'])
        po_date = str(data['date_only'])
        seller_summary_obj = SellerPOSummary.objects.filter(receipt_number=data['receipt_number'],\
                                            purchase_order__order_id=data['purchase_order__order_id'],\
                                            purchase_order__open_po__supplier__name=data['purchase_order__open_po__supplier__name'])
 
        tot_amt = 0
        for seller_sum in seller_summary_obj:
            price = seller_sum.purchase_order.open_po.price
            quantity = seller_sum.quantity
            tot_tax_perc = seller_sum.purchase_order.open_po.cgst_tax +\
                           seller_sum.purchase_order.open_po.sgst_tax + seller_sum.purchase_order.open_po.igst_tax
            if seller_sum.batch_detail:
                price = seller_sum.batch_detail.buy_price
                tot_tax_perc = seller_sum.batch_detail.tax_percent
            tot_price = price * quantity
            tot_tax = float(tot_price * tot_tax_perc) / 100
            tot_amt += (tot_price + tot_tax)

        data_dict = OrderedDict((('GRN No', grn_number),
                                 ('Supplier Name', data['purchase_order__open_po__supplier__name']),
                                 ('check_field', 'Supplier Name'),
                                 ('PO Quantity', data['total_ordered']),
                                 ('Received Quantity', data['total_received']),
                                 ('Order Date', po_date),
                                 ('Total Amount', tot_amt), ('id', data.get('id', 0)),
                                 ('receipt_number', data['receipt_number']),
                                 ('purchase_order__order_id', data['purchase_order__order_id'])
                               ))
        temp_data['aaData'].append(data_dict)


@csrf_exempt
@get_admin_user
def move_to_poc(request, user=''):
    sell_ids = {}
    seller_summary = SellerPOSummary.objects.none()
    req_data = request.GET.get('data', '')
    if req_data:
        req_data = eval(req_data)
        req_data = [req_data] if isinstance(req_data,dict) else req_data
        for item in req_data:
            cancel_flag = item.get('cancel', '')
            sell_ids['purchase_order__order_id'] = item['purchase_order__order_id']
            sell_ids['receipt_number'] = item['receipt_number']
            seller_summary = seller_summary | SellerPOSummary.objects.filter(**sell_ids)
        if cancel_flag == 'true':
            status_flag = 'processed_pos'
            chn_no, chn_sequence = '', ''
        else:
            status_flag = 'po_challans'
    if cancel_flag != 'true':
        chn_no, chn_sequence = get_po_challan_number(user, seller_summary)
    try:
        seller_summary.update(challan_number=chn_no, order_status_flag=status_flag)
        return HttpResponse(json.dumps({'message': 'success'}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Exception raised wile updating status of Seller Order Summary: %s" %str(e))
        return HttpResponse(json.dumps({'message': 'failed'}))


@csrf_exempt
@get_admin_user
def move_to_invoice(request, user=''):
    sell_ids = {}
    seller_summary = SellerPOSummary.objects.none()
    req_data = request.GET.get('data', '')
    invoice_number = request.GET.get('inv_number', '')
    invoice_date = request.GET.get('inv_date', '')
    invoice_date = datetime.datetime.strptime(invoice_date, "%m/%d/%Y") if invoice_date else None
    if req_data:
        req_data = eval(req_data)
        req_data = [req_data] if isinstance(req_data,dict) else req_data
        if invoice_number:
            supplier_id = ''
            if req_data and req_data[0].get('purchase_order__order_id', ''):
                purchase_order_obj = PurchaseOrder.objects.filter(open_po__sku__user=user.id,
                                                                  order_id=req_data[0]['purchase_order__order_id'])
                if purchase_order_obj:
                    supplier_id = purchase_order_obj[0].open_po.supplier_id
            inv_status = po_invoice_number_check(user, invoice_number, supplier_id)
            if inv_status:
                return HttpResponse(json.dumps({'message': inv_status}))
        for item in req_data:
            cancel_flag = item.get('cancel', '')
            if invoice_number:
                sell_ids['purchase_order__order_id'] = item['purchase_order__order_id']
                sell_ids['receipt_number'] = item['receipt_number']
            else:
                sell_ids['invoice_number'] = item.get('invoice_number', '')
            seller_summary = seller_summary | SellerPOSummary.objects.filter(**sell_ids)
    try:
        for sel_obj in seller_summary:
            if cancel_flag == 'true':
                if sel_obj.challan_number:
                    status_flag = 'po_challans'
                else:
                    status_flag = 'processed_pos'
            else:
                status_flag = 'supplier_invoices'
            sel_obj.order_status_flag = status_flag
            if invoice_number:
                sel_obj.invoice_number = invoice_number
                sel_obj.invoice_date = invoice_date
            sel_obj.save()
        return HttpResponse(json.dumps({'message': 'success'}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Exception raised wile updating status of Seller Order Summary: %s" %str(e))
        return HttpResponse(json.dumps({'message': 'failed'}))



@csrf_exempt
@get_admin_user
def generate_supplier_invoice(request, user=''):
    sell_summary_param = {}
    result_data = {}
    log.info('Request params for ' + user.username + ' is ' + str(request.GET.dict()))
    admin_user = get_priceband_admin_user(user)
    try:
        true, false = ["true", "false"]
        req_data = request.GET.get('data', '')
        if req_data:
            request_data = eval(req_data)
            request_data = (request_data,) if isinstance(request_data,dict) else request_data
            result_data["data"] = []
            result_data["total_amt"], result_data["total_invoice_amount"], result_data["rounded_invoice_amount"],\
            result_data["total_quantity"], result_data["total_tax"] = [0]*5
            tot_cgst, tot_sgst, tot_igst, tot_utgst = [0]*4
            for req_data in request_data:
                #sell_summary_param['purchase_order__order_id'] = req_data.get('purchase_order__order_id', '')
                #sell_summary_param['receipt_number'] = req_data.get('receipt_number', '')
                sell_summary_param['purchase_order__open_po__sku__user'] = user.id
                inv_no = req_data.get('invoice_number', '')
                if inv_no:
                    sell_summary_param['invoice_number'] = inv_no
                else:
                    sell_summary_param['purchase_order__order_id'] = req_data.get('purchase_order__order_id', '')
                    sell_summary_param['receipt_number'] = req_data.get('receipt_number', '') 
                    sell_summary_param['challan_number'] = req_data.get('challan_id', '')
                #sell_summary_param['invoice_number'] = req_data.get('invoice_number', '')
                seller_summary = SellerPOSummary.objects.filter(**sell_summary_param)
                if seller_summary:
                    up = user.userprofile
                    supplier = seller_summary[0].purchase_order.open_po.supplier
                    order_date = get_local_date(user, seller_summary[0].purchase_order.creation_date, send_date=True)\
                                 .date().strftime("%d %b %Y")
                    company_details = {"name": up.company_name,
                                       "address": up.address,
                                       "phone_number": up.phone_number,
                                       "email": user.email
                                      }
                    supplier_details = {"address": supplier.address,
                                        "id": supplier.id,
                                        "name": supplier.name,
                                        "phone_number": supplier.phone_number,
                                        "tin_number": supplier.tin_number}
                    result_data.update({"company_details": company_details,
                                   "supplier_details": supplier_details,
                                   "challan_no": seller_summary[0].challan_number,
                                   "inv_date": seller_summary[0].invoice_date.strftime("%d %b %Y") if seller_summary[0].invoice_date else '',
                                   "invoice_header": "Tax Invoice",
                                   "invoice_no": seller_summary[0].invoice_number,
                                   "order_date": order_date,
                                   "order_id": seller_summary[0].purchase_order.order_id,
                                   "receipt_number": seller_summary[0].receipt_number,
                                   "price_in_words": "",
                                   "total_tax_words": ''

                                  })

                    result_data["challan_date"] = seller_summary[0].challan_date
                    result_data["challan_date"] = result_data["challan_date"].strftime("%m/%d/%Y") if result_data["challan_date"] else ''
                    #result_data["data"] = []
                    tot_amt, tot_invoice, tot_qty, tot_tax = [0]*4
                    for seller_sum in seller_summary:
                        rem_quantity = 0
                        temp_qty = float(seller_sum.quantity)
                        processed_val = seller_sum.returntovendor_set.filter().aggregate(Sum('quantity'))['quantity__sum']
                        if processed_val:
                            temp_qty -= processed_val
                        rem_quantity += temp_qty

                        po = seller_sum.purchase_order
                        open_po = po.open_po
                        sku = open_po.sku
                        unit_price = open_po.price
                        qty = rem_quantity
                        cgst_tax = open_po.cgst_tax
                        sgst_tax = open_po.sgst_tax
                        igst_tax = open_po.igst_tax
                        utgst_tax = open_po.utgst_tax
                        if seller_sum.batch_detail:
                            unit_price = seller_sum.batch_detail.buy_price
                            temp_tax_percent = seller_sum.batch_detail.tax_percent
                            if open_po.supplier.tax_type == 'intra_state':
                                temp_tax_percent = temp_tax_percent / 2
                                cgst_tax = truncate_float(temp_tax_percent, 1)
                                sgst_tax = truncate_float(temp_tax_percent, 1)
                                igst_tax = 0
                                utgst_tax = 0
                            else:
                                igst_tax = temp_tax_percent
                                cgst_tax = 0
                                sgst_tax = 0
                                utgst_tax = 0
                        cgst_amt = float((unit_price * qty * cgst_tax) / 100)
                        sgst_amt = float((unit_price * qty * sgst_tax) / 100)
                        igst_amt = float((unit_price * qty * igst_tax) / 100)
                        utgst_amt = float((unit_price * qty * utgst_tax) / 100)
                        tot_cgst += cgst_amt
                        tot_sgst += sgst_tax
                        tot_igst += igst_tax
                        tot_utgst += utgst_tax
                        amt = unit_price * qty
                        invoice_amt = amt + cgst_amt + sgst_amt + igst_amt + utgst_amt
                        tot_tax += (cgst_amt + sgst_amt + igst_amt + utgst_amt)
                        tot_qty += qty
                        tot_amt += amt
                        tot_invoice += invoice_amt
                        taxes = {"cgst_tax": cgst_tax, "sgst_tax": sgst_tax,
                                 "igst_tax": igst_tax, "utgst_tax": utgst_tax,
                                 "cgst_amt": cgst_amt, "sgst_amt": sgst_amt,
                                 "igst_amt": igst_amt, "utgst_amt": utgst_amt}
                        sku_data = {"id": sku.id,
                                    "seller_summary_id": seller_sum.id,
                                    "open_po_id": open_po.id,
                                    "sku_code": sku.wms_code,
                                    "title": sku.sku_desc,
                                    "unit_price": unit_price,
                                    "tax_type": open_po.tax_type,
                                    "invoice_amount": invoice_amt,
                                    "hsn_code": '',
                                    "amt": amt,
                                    "quantity": qty,
                                    "shipment_date": '',
                                    "taxes": taxes
                                    }
                        result_data["data"].append(sku_data)
                        result_data["sequence_number"] = sku.sequence
                    result_data["total_amt"] += tot_amt
                    result_data["total_invoice_amount"] += tot_invoice
                    result_data["rounded_invoice_amount"] += round(tot_invoice)
                    result_data["total_quantity"] += tot_qty
                    result_data["total_tax"] += tot_tax
                    result_data["total_taxes"] = {"cgst_amt": tot_cgst, "igst_amt": tot_igst,
                                                  "sgst_amt": tot_sgst, "utgst_amt": tot_utgst}


    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        return HttpResponse(json.dumps({'message': 'failed'}))
    po_challan = request.GET.get('po_challan', '')
    if po_challan == 'true':
        result_data['total_items'] = len(result_data['data'])
        result_data['data'] = pagination(result_data['data'])
        result_data['username'] = user.username
        return render(request, 'templates/toggle/po_challan.html', result_data)

    return HttpResponse(json.dumps(result_data))


def pagination(sku_list):
    # header 220
    # footer 125
    # table header 44
    # row 46
    # total 1358
    # default 24 items
    # last page 21 items
    mx = 24
    mn = 22
    #t = sku_list[0]
    #for i in range(33): sku_list.append(copy.deepcopy(t))#remove it
    sku_len = len(sku_list)
    index = 1
    for sku in sku_list:
        sku['index'] = index
        index = index + 1
    temp = {"sku_code": "", "title": "", "quantity": ""}
    sku_slices = [sku_list[i: i+mx] for i in range(0, len(sku_list), mx)] 
    #extra_tuple = ('', '', '', '', '', '', '', '', '', '', '', '')
    if len(sku_slices[-1]) == mx:
        temp = sku_slices[-1]
        sku_slices[-1] = temp[:mx-1]
        temp = [temp[-1]]
        for i in range(mn-1): temp.append(temp)
        sku_slices.append(temp)
    else:
        for i in range((mn - len(sku_slices[-1]))): sku_slices[-1].append(temp)
    return sku_slices


@get_admin_user
def update_poc(request, user=''):
    form_dict = dict(request.POST.iterlists())
    address = form_dict['form_data[address]'][0]
    challan_number = form_dict['form_data[challan_no]'][0]
    #receipt_number = form_dict['form_data[receipt_number]'][0]
    rep_id = form_dict['form_data[rep]']
    challan_date = form_dict.get("form_data[challan_date]", [''])[0]
    lr_no = form_dict['form_data[lr_no]']
    carrier = form_dict['form_data[carrier]']
    sku_id = form_dict['form_data[wms_code]']
    pkgs = form_dict['form_data[pkgs]']
    terms = form_dict['form_data[terms]']
    skus_data = form_dict['data']
    order_id = form_dict['form_data[order_no]'][0]
    pick_number = form_dict['form_data[pick_number]'][0]
    supp_id = form_dict['form_data[supplier_id]'][0]
    invoice_number = form_dict.get('form_data[invoice_no]', [''])[0]
    invoice_date = ''
    if not supp_id:
        log.info("No  Supplier Id found")
        return HttpResponse(json.dumps({'message': 'failed'}))
    else:
        supp_obj = SupplierMaster.objects.filter(id=supp_id)
        if not supp_obj:
            log.info('No Proper Supplier Object')
            return HttpResponse(json.dumps({'message': 'failed'}))
        else:
            supp_obj = supp_obj[0]
        supplier_id = supp_obj.id
        supplier_name = supp_obj.name
    challan_date = datetime.datetime.strptime(challan_date, "%m/%d/%Y") if challan_date else None
    for sku_data in skus_data:
        sku_data = eval(sku_data)
        shipment_date = sku_data[0].get('shipment_date', '')
        for each_sku in sku_data:
            seller_summary_id = each_sku.get('seller_summary_id', '')
            open_po_id = each_sku.get('open_po_id', '')
            quantity = each_sku.get('quantity', '')
            unit_price = float(each_sku.get('unit_price', 0))
            sgst_tax = float(each_sku['taxes'].get('sgst_tax', 0))
            cgst_tax = float(each_sku['taxes'].get('cgst_tax', 0))
            igst_tax = float(each_sku['taxes'].get('igst_tax', 0))
            utgst_tax = float(each_sku['taxes'].get('utgst_tax', 0))
            invoice_amount = float(each_sku.get('invoice_amount', 0))

            if not int(quantity):
                #if seller_summary_id:
                    #seller_po_summary_obj = SellerPOSummary.objects.filter(id=seller_summary_id)
                    #if seller_po_summary_obj:
                        #seller_po_summary_obj = seller_po_summary_obj[0]
                        #seller_po_summary_obj.delete()
                if open_po_id:
                    open_po_obj = OpenPO.objects.filter(id=open_po_id)
                    if open_po_obj:
                        open_po_obj = open_po_obj[0]
                        open_po_obj.delete()
                continue
            if seller_summary_id:
                seller_po_summary_obj = SellerPOSummary.objects.filter(id=seller_summary_id)
                if seller_po_summary_obj:
                    seller_po_summary_obj[0].quantity = quantity
                    seller_po_summary_obj[0].challan_date = challan_date
                    seller_po_summary_obj[0].invoice_number
                    seller_po_summary_obj[0].save()

                if open_po_id:
                    open_po_obj = OpenPO.objects.filter(id=open_po_id)
                    if open_po_obj:
                        open_po_obj[0].price = unit_price
                        if cgst_tax:
                            open_po_obj[0].cgst_tax = cgst_tax
                        if sgst_tax:
                            open_po_obj[0].sgst_tax = sgst_tax
                        if igst_tax:
                            open_po_obj[0].igst_tax = igst_tax
                        open_po_obj[0].save()

            else:
                sku_qs = SKUMaster.objects.filter(sku_code=each_sku['sku_code'], user=user.id)
                if not sku_qs:
                    continue
                else:
                    sku_id = sku_qs[0].id
                    open_po_dict = {'sku_id': sku_id, 'order_quantity': seller_po_summary_obj[0].purchase_order.open_po.order_quantity,
                                    'supplier_id': supplier_id, 'status': 0,
                                    'order_type': seller_po_summary_obj[0].purchase_order.open_po.order_type,
                                    'price': unit_price,
                                    'measurement_unit': sku_qs[0].measurement_type, 'cgst_tax': cgst_tax,
                                    'igst_tax': igst_tax, 'sgst_tax': sgst_tax, 'utgst_tax': utgst_tax}
                    open_po_obj = OpenPO(**open_po_dict)
                    open_po_obj.save()

                    purchase_dict = {"order_id": order_id, "received_quantity": quantity,
                                     "saved_quantity": 0, "po_date": datetime.datetime.now(),
                                     "status": seller_po_summary_obj[0].purchase_order.status,
                                     "open_po_id": open_po_obj.id}
                    purchase_order_obj = PurchaseOrder(**purchase_dict)
                    purchase_order_obj.save()

                    po_summary_dict = {"receipt_number": seller_po_summary_obj[0].receipt_number,
                                       "quantity": quantity, "purchase_order_id": purchase_order_obj.id,
                                       "invoice_number": invoice_number, #"invoice_date": invoice_date,
                                       "challan_number": challan_number, "order_status_flag": seller_po_summary_obj[0].order_status_flag,
                                       "putaway_quantity": 0}
                    po_summary_obj = SellerPOSummary(**po_summary_dict)
                    po_summary_obj.save()


                    """sos_dict = {'quantity': quantity, 'pick_number': pick_number,
                                'creation_date': datetime.datetime.now(), 'order_id': ord_obj.id,
                                'challan_number': challan_number, 'order_status_flag': 'delivery_challans'}
                    sos_obj = SellerOrderSummary(**sos_dict)
                    sos_obj.save()"""

    return HttpResponse(json.dumps({'message': 'success'}))


@csrf_exempt
@login_required
@get_admin_user
def update_po_invoice(request, user=''):
    """ update invoice data """

    true, false = ["true", "false"]
    form_dict = dict(request.POST.iterlists())
    address = form_dict['form_data[address]'][0]
    challan_number = form_dict.get('form_data[challan_no]', [''])[0]
    #receipt_number = form_dict['form_data[receipt_number]'][0]
    rep_id = form_dict.get('form_data[rep]', '')
    lr_no = form_dict.get('form_data[lr_no]', '')
    carrier = form_dict.get('form_data[carrier]', '')
    sku_id = form_dict.get('form_data[wms_code]', '')
    pkgs = form_dict.get('form_data[pkgs]', '')
    terms = form_dict.get('form_data[terms]', '')
    skus_data = form_dict.get('data','')
    order_id = form_dict.get('form_data[order_id]', [''])[0]
    pick_number = form_dict.get('form_data[pick_number]', [''])[0]
    supp_id = form_dict.get('form_data[supplier_id]', [''])[0]
    invoice_number = form_dict.get('form_data[invoice_no]', [''])[0]
    invoice_date = form_dict.get('form_data[invoice_date]', [''])[0]
    if not supp_id:
        log.info("No  Supplier Id found")
        return HttpResponse(json.dumps({'message': 'failed'}))
    else:
        supp_obj = SupplierMaster.objects.filter(id=supp_id)
        if not supp_obj:
            log.info('No Proper Supplier Object')
            return HttpResponse(json.dumps({'message': 'failed'}))
        else:
            supp_obj = supp_obj[0]
        supplier_id = supp_obj.id
        supplier_name = supp_obj.name
    invoice_date = datetime.datetime.strptime(invoice_date, "%m/%d/%Y").date() if invoice_date else None
    for sku_data in skus_data:
        sku_data = eval(sku_data)
        shipment_date = sku_data[0].get('shipment_date', '')
        for each_sku in sku_data:
            seller_summary_id = each_sku.get('seller_summary_id', '')
            open_po_id = each_sku.get('open_po_id', '')
            quantity = each_sku.get('quantity', '')
            unit_price = float(each_sku.get('unit_price', 0))
            sgst_tax = float(each_sku['taxes'].get('sgst_tax', 0))
            cgst_tax = float(each_sku['taxes'].get('cgst_tax', 0))
            igst_tax = float(each_sku['taxes'].get('igst_tax', 0))
            utgst_tax = float(each_sku['taxes'].get('utgst_tax', 0))
            invoice_amount = float(each_sku.get('invoice_amount', 0))

            if not int(quantity):
                #if seller_summary_id:
                    #seller_po_summary_obj = SellerPOSummary.objects.filter(id=seller_summary_id)
                    #if seller_po_summary_obj:
                        #seller_po_summary_obj = seller_po_summary_obj[0]
                        #seller_po_summary_obj.delete()
                if open_po_id:
                    open_po_obj = OpenPO.objects.filter(id=open_po_id)
                    if open_po_obj:
                        open_po_obj = open_po_obj[0]
                        open_po_obj.delete()
                continue
            if seller_summary_id:
                seller_po_summary_obj = SellerPOSummary.objects.filter(id=seller_summary_id)
                if seller_po_summary_obj:
                    seller_po_summary_obj[0].quantity = quantity
                    seller_po_summary_obj[0].invoice_number = invoice_number
                    seller_po_summary_obj[0].invoice_date = invoice_date
                    seller_po_summary_obj[0].save()

                if open_po_id:
                    open_po_obj = OpenPO.objects.filter(id=open_po_id)
                    if open_po_obj:
                        open_po_obj[0].price = unit_price
                        if cgst_tax:
                            open_po_obj[0].cgst_tax = cgst_tax
                        if sgst_tax:
                            open_po_obj[0].sgst_tax = sgst_tax
                        if igst_tax:
                            open_po_obj[0].igst_tax = igst_tax
                        open_po_obj[0].save()

            else:
                sku_qs = SKUMaster.objects.filter(sku_code=each_sku['sku_code'], user=user.id)
                if not sku_qs:
                    continue
                else:
                    sku_id = sku_qs[0].id
                    open_po_dict = {'sku_id': sku_id, 'order_quantity': seller_po_summary_obj[0].purchase_order.open_po.order_quantity,
                                    'supplier_id': supplier_id, 'status': 0,
                                    'order_type': seller_po_summary_obj[0].purchase_order.open_po.order_type,
                                    'price': unit_price,
                                    'measurement_unit': sku_qs[0].measurement_type, 'cgst_tax': cgst_tax,
                                    'igst_tax': igst_tax, 'sgst_tax': sgst_tax, 'utgst_tax': utgst_tax}
                    open_po_obj = OpenPO(**open_po_dict)
                    open_po_obj.save()

                    purchase_dict = {"order_id": order_id, "received_quantity": quantity,
                                     "saved_quantity": 0, "po_date": datetime.datetime.now(),
                                     "status": seller_po_summary_obj[0].purchase_order.status,
                                     "open_po_id": open_po_obj.id}
                    purchase_order_obj = PurchaseOrder(**purchase_dict)
                    purchase_order_obj.save()

                    po_summary_dict = {"receipt_number": seller_po_summary_obj[0].receipt_number,
                                       "quantity": quantity, "purchase_order_id": purchase_order_obj.id,
                                       "invoice_number": invoice_number, #"invoice_date": invoice_date,
                                       "challan_number": challan_number, "order_status_flag": seller_po_summary_obj[0].order_status_flag,
                                       "putaway_quantity": 0}
                    po_summary_obj = SellerPOSummary(**po_summary_dict)
                    po_summary_obj.save()


                    """sos_dict = {'quantity': quantity, 'pick_number': pick_number,
                                'creation_date': datetime.datetime.now(), 'order_id': ord_obj.id,
                                'challan_number': challan_number, 'order_status_flag': 'delivery_challans'}
                    sos_obj = SellerOrderSummary(**sos_dict)
                    sos_obj.save()"""

    return HttpResponse(json.dumps({'message': 'success'}))


@csrf_exempt
def get_inv_based_po_payment_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                         filters):
    ''' Invoice Based PO Payment Tracker datatable code '''
    user_profile = UserProfile.objects.get(user_id=user.id)
    admin_user = get_priceband_admin_user(user)
    lis = ['invoice_number', 'purchase_order__open_po__supplier__name', 'invoice_number', 'invoice_number',
           'invoice_number', 'invoice_number', 'invoice_number']#for filter purpose
    user_filter = {'purchase_order__open_po__sku__user': user.id, 'order_status_flag': 'supplier_invoices'}
    result_values = ['invoice_number', 'purchase_order__open_po__supplier__name',
                     'purchase_order__open_po__supplier__id']#to make distinct grouping
    if search_term:
        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(lis, search_term)
        master_data = SellerPOSummary.objects.filter(search_query, **user_filter)\
                                     .values(*result_values).distinct()\
                                     .annotate(payment_received=Sum('purchase_order__payment_received'))
    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            order_by = '%s' % lis[col_num]
        else:
            order_by = '-%s' % lis[col_num]
        master_data = SellerPOSummary.objects.filter(**user_filter).values(*result_values).distinct()\
                                     .annotate(payment_received=Sum('purchase_order__payment_received'))\
                                     .order_by('-%s' % lis[col_num])
    else:
        master_data = SellerPOSummary.objects.filter(**user_filter)\
                                 .values(*result_values).distinct().annotate(payment_received=Sum('purchase_order__payment_received'))

    #master_data = master_data.exclude(invoice_amount=F('payment_received'))
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    for data in master_data[start_index:stop_index]:
        seller_summary_obj = SellerPOSummary.objects.filter(invoice_number=data['invoice_number'],\
                                             purchase_order__open_po__supplier__name=data['purchase_order__open_po__supplier__name'])
        invoice_date = seller_summary_obj.order_by('-invoice_date').values_list('invoice_date', flat=True)[0]
        if not invoice_date:
            invoice_date = seller_summary_obj.order_by('updation_date')[0].updation_date
        tot_amt = 0
        for seller_sum in seller_summary_obj:
            price = seller_sum.purchase_order.open_po.price
            quantity = seller_sum.quantity
            tot_price = price * quantity
            tot_tax_perc = seller_sum.purchase_order.open_po.cgst_tax +\
                           seller_sum.purchase_order.open_po.sgst_tax + seller_sum.purchase_order.open_po.igst_tax
            tot_tax = float(tot_price * tot_tax_perc) / 100
            tot_amt += (tot_price + tot_tax)

        payment_receivable = tot_amt - data['payment_received']
        if payment_receivable != 0:
            credit_period, due_date = 0, ''
            due_date = (invoice_date + datetime.timedelta(days=credit_period)).strftime("%d %b %Y")
            invoice_date = invoice_date.strftime("%d %b %Y")
            data_dict = OrderedDict((('invoice_number', data['invoice_number']),
                                     ('invoice_date', invoice_date), ('due_date', due_date),
                                     ('supplier_name', data['purchase_order__open_po__supplier__name']),
                                     ('supplier_id', data['purchase_order__open_po__supplier__id']),
                                     ('invoice_amount', "%.2f" % tot_amt),
                                     ('payment_received', "%.2f" % data['payment_received']),
                                     ('payment_receivable', "%.2f" % payment_receivable)
                                   ))
            temp_data['aaData'].append(data_dict)


@login_required
@csrf_exempt
@get_admin_user
def po_get_invoice_payment_tracker(request, user=''):
    response = {}
    invoice_number = request.GET.get('invoice_number', '')
    supplier_id = request.GET.get('supplier_id', '')
    supplier_name = request.GET.get('supplier_name', '')
    if not invoice_number:
        return "Invoice number is missing"
    user_filter = {'purchase_order__open_po__sku__user': user.id, "invoice_number": invoice_number, "purchase_order__open_po__supplier__id": supplier_id}
    result_values = ['purchase_order__order_id', 'purchase_order__open_po__supplier__name', 'purchase_order__open_po__supplier__id']
    master_data = SellerPOSummary.objects.filter(**user_filter).values(*result_values).distinct()\
                                 .annotate(tot_price = Sum(F('purchase_order__open_po__price')*F('quantity')),\
                                 tot_tax_perc = Sum(F('purchase_order__open_po__cgst_tax') +\
                                 F('purchase_order__open_po__sgst_tax') + F('purchase_order__open_po__igst_tax')),\
                                 paynemt_received = Sum('purchase_order__payment_received'))
    order_data = []
    for data in master_data:
        order_data.append(
                {'order_id': data['purchase_order__order_id'],
                 'display_order': data['purchase_order__order_id'],
                 'inv_amount': data['tot_price']+(data['tot_price']*data['tot_tax_perc']),
                 'received': data['paynemt_received'],
                 'receivable': (data['tot_price']+(data['tot_price']*data['tot_tax_perc'])) - data['paynemt_received']})
    response["data"] = order_data
    return HttpResponse(json.dumps(response))


@login_required
@csrf_exempt
@get_admin_user
def po_update_payment_status(request, user=''):
    data_dict = dict(request.GET.iterlists())
    invoice_number = request.GET.get('invoice_number', '')
    if invoice_number:
        sell_ids = {}
        sell_ids['purchase_order__open_po__sku__user'] = user.id
        sell_ids['invoice_number'] = invoice_number
        seller_summary = SellerPOSummary.objects.filter(**sell_ids)
        order_ids = list(set(seller_summary.values_list('purchase_order__order_id', flat=True)))
        order_ids = map(lambda x: str(x), order_ids)
        data_dict['order_id'] = order_ids

    for i in range(0, len(data_dict['order_id'])):
        if not data_dict['amount'][i]:
            continue
        payment = float(data_dict['amount'][i])
        seller_summary_obj = SellerPOSummary.objects.filter(purchase_order__open_po__sku__user=user.id,\
                                                    purchase_order__order_id=data_dict['order_id'][i])
        invoice_amt = 0
        for seller_sum in seller_summary_obj:
            price = seller_sum.purchase_order.open_po.price
            quantity = seller_sum.quantity
            tot_price = price * quantity
            tot_tax_perc = seller_sum.purchase_order.open_po.cgst_tax +\
                           seller_sum.purchase_order.open_po.sgst_tax + seller_sum.purchase_order.open_po.igst_tax
            tot_tax = float(tot_price * tot_tax_perc) / 100
            invoice_amt += (tot_price + tot_tax)
        po_objs = PurchaseOrder.objects.filter(order_id=data_dict['order_id'][i],\
                                              open_po__sku__user=user.id,\
                                              payment_received__lt=invoice_amt)
        for order in po_objs:
            if not payment:
                break
            sel_po_sum = order.sellerposummary_set.all()[0]
            price = order.open_po.price
            quantity = sel_po_sum.quantity
            tot_price = price * quantity
            tot_tax_perc = order.open_po.cgst_tax + order.open_po.sgst_tax + order.open_po.igst_tax
            tot_tax = float(tot_price * tot_tax_perc) / 100
            invoice_amt = tot_price + tot_tax

            if float(invoice_amt) > float(order.payment_received):
                diff = float(invoice_amt) - float(order.payment_received)
                bank = request.GET.get('bank', '')
                mode_of_pay = request.GET.get('mode_of_payment', '')
                remarks = request.GET.get('remarks', '')
                if payment > diff:
                    order.payment_received = diff
                    payment -= diff
                    POPaymentSummary.objects.create(order_id=order.id, creation_date=datetime.datetime.now(),\
                                                  payment_received=diff, bank=bank, mode_of_pay=mode_of_pay,\
                                                  remarks=remarks)
                else:
                    POPaymentSummary.objects.create(order_id=order.id, creation_date=datetime.datetime.now(),\
                                                  payment_received=payment, bank=bank,\
                                                  mode_of_pay=mode_of_pay, remarks=remarks)
                    order.payment_received = float(order.payment_received) + float(payment)
                    payment = 0
                order.save()
    return HttpResponse("Success")


def get_po_putaway_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, col_filters={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    search_params = {}
    search_params['purchase_order__open_po__sku_id__in'] = sku_master_ids
    lis = ['purchase_order__open_po__supplier_id', 'purchase_order__open_po__supplier_id', 'purchase_order__open_po__supplier__name',
            'purchase_order__order_id', 'purchase_order_date', 'invoice_number', 'invoice_date', 'total', 'total']

    headers1, filters, filter_params1 = get_search_params(request)
    enable_dc_returns = request.POST.get("enable_dc_returns", "")
    inv_or_dc_number = 'invoice_number'
    if enable_dc_returns == 'true':
        headers1[headers1.index('Invoice Number')]='Challan Number'
        inv_or_dc_number = 'challan_number'
    if 'from_date' in filters:
        search_params['purchase_order__creation_date__gt'] = filters['from_date']
    if 'to_date' in filters:
        to_date = datetime.datetime.combine(filters['to_date'] + datetime.timedelta(1),
                                                             datetime.time())
        search_params['purchase_order__creation_date__lt'] = to_date
    if 'sku_code' in filters:
        search_params['purchase_order__open_po__sku__sku_code'] = filters['sku_code'].upper()
    if 'supplier_id' in filters:
        search_params['purchase_order__open_po__supplier_id'] = filters['supplier_id']
    if 'open_po' in filters and filters['open_po']:
        temp = re.findall('\d+', filters['open_po'])
        if temp:
            search_params['purchase_order__order_id'] = temp[-1]
    if 'invoice_number' in filters and enable_dc_returns != 'true':
        search_params['invoice_number'] = filters['invoice_number']
    if 'challan_number' in filters and enable_dc_returns == 'true':
        search_params['challan_number'] = filters['challan_number']

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    ret_params = {}
    for key, value in search_params.iteritems():
        ret_params['seller_po_summary__%s' % key] = value
    return_ids = ReturnToVendor.objects.filter(**ret_params).values_list('seller_po_summary_id').distinct().\
                                        annotate(tot_proc=Sum('quantity'), tot=Sum('seller_po_summary__quantity'),
                                                 tot_count=Count('seller_po_summary__quantity')).\
                                        annotate(final_val=F('tot')/Cast(F('tot_count'), FloatField())).\
                                        filter(tot_proc__gte=F('final_val')).\
                                        values_list('seller_po_summary_id', flat=True)
    if search_term:
        results = SellerPOSummary.objects.exclude(id__in=return_ids).filter(purchase_order__polocation__status=0,
                                            purchase_order__open_po__sku__user=user.id, **search_params).\
            values('purchase_order__open_po__supplier_id', 'purchase_order__open_po__supplier__name',
                   'purchase_order__order_id', inv_or_dc_number, 'invoice_date', 'challan_date',).distinct().annotate(
            total=Sum('quantity'), purchase_order_date=Cast('purchase_order__creation_date', DateField())).order_by(order_data)

    elif order_term:
        results = SellerPOSummary.objects.exclude(id__in=return_ids).select_related('purchase_order__open_po__supplier', 'purchase_order').\
                                            filter(purchase_order__polocation__status=0, purchase_order__open_po__sku__user=user.id, **search_params).\
            values('purchase_order__open_po__supplier_id', 'purchase_order__open_po__supplier__name',
                   'purchase_order__order_id', inv_or_dc_number, 'invoice_date', 'challan_date',).distinct().annotate(
            total=Sum('quantity'), purchase_order_date=Cast('purchase_order__creation_date', DateField())).order_by(order_data)

    temp_data['recordsTotal'] = results.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    count = 0
    for result in results[start_index: stop_index]:
        rem_quantity = 0
        seller_summarys = SellerPOSummary.objects.exclude(id__in=return_ids).\
                                            select_related('purchase_order__open_po__sku', 'purchase_order').\
                                                    filter(purchase_order__open_po__sku__user=user.id,
                                                        purchase_order__order_id=result['purchase_order__order_id']).\
                                                    filter(**{inv_or_dc_number: result[inv_or_dc_number]})
        order_reference = get_po_reference(seller_summarys[0].purchase_order)
        open_po = seller_summarys[0].purchase_order.open_po
        data_id = '%s:%s' % (result['purchase_order__order_id'], result.get('invoice_number', ''))
        checkbox = "<input type='checkbox' name='data_id' value='%s'>" % (data_id)
        po_date = get_local_date(request.user, seller_summarys[0].purchase_order.creation_date,
                                 send_date=True).strftime("%d %b, %Y")
        invoice_number = ''
        if result.get('invoice_number', ''):
            invoice_number = result.get('invoice_number', '')
        challan_number = ''
        if result.get('challan_number', ''):
            challan_number = result.get('challan_number', '')
        invoice_date = po_date
        if result['invoice_date']:
            invoice_date = result['invoice_date'].strftime("%d %b, %Y")
        challan_date = None
        if result['challan_date']:
            challan_date = result['challan_date'].strftime("%d %b, %Y")
        total_amt = 0
        tax = open_po.cgst_tax + open_po.sgst_tax + open_po.igst_tax + open_po.utgst_tax
        for seller_summary in seller_summarys:
            temp_qty = float(seller_summary.quantity)
            processed_val = seller_summary.returntovendor_set.filter().aggregate(Sum('quantity'))['quantity__sum']
            if processed_val:
                temp_qty -= processed_val
            if seller_summary.batch_detail:
                total_amt += temp_qty * seller_summary.batch_detail.buy_price
            else:
                total_amt += temp_qty * seller_summary.purchase_order.open_po.price
            rem_quantity += temp_qty
        total_amt = total_amt + ((total_amt/100) * tax)
        temp_data['aaData'].append(OrderedDict((('', checkbox),('data_id', data_id),
                                                ('Supplier ID', result['purchase_order__open_po__supplier_id']),
                                                ('Supplier Name', result['purchase_order__open_po__supplier__name']),
                                                ('PO Number', order_reference), ('PO Date', po_date),
                                                ('Invoice Number', invoice_number), ('Challan Number', challan_number),
                                                ('Invoice Date', invoice_date), ('Challan Date', challan_date),
                                                ('Total Quantity', rem_quantity), ('Total Amount', total_amt),
                                                ('id', count),
                                                ('DT_RowClass', 'results'))))
        count += 1


@csrf_exempt
@login_required
@get_admin_user
def get_po_putaway_summary(request, user=''):
    order_id, invoice_num = request.GET['data_id'].split(':')
    summary_filter = {'purchase_order__open_po__sku__user': user.id, 'purchase_order__order_id': order_id}
    if invoice_num:
        summary_filter['invoice_number'] = invoice_num
    seller_summary_objs = SellerPOSummary.objects.filter(**summary_filter)
    if not seller_summary_objs:
        return HttpResponse("No Data found")
    po_reference = get_po_reference(seller_summary_objs[0].purchase_order)
    invoice_number = seller_summary_objs[0].invoice_number
    invoice_date = get_local_date(user, seller_summary_objs[0].creation_date, send_date=True).strftime("%d %b, %Y")
    if seller_summary_objs[0].invoice_date:
        invoice_date = seller_summary_objs[0].invoice_date.strftime("%d %b, %Y")
    orders = []
    order_data = {}
    order_ids = []
    seller_details = {}
    for seller_summary in seller_summary_objs:
        order = seller_summary.purchase_order
        open_po = seller_summary.purchase_order.open_po
        order_data = get_purchase_order_data(order)
        quantity = seller_summary.quantity
        sku = open_po.sku
        processed_val = seller_summary.returntovendor_set.filter().aggregate(Sum('quantity'))['quantity__sum']
        if processed_val:
            quantity -= processed_val
        if quantity <= 0:
            continue
        data_dict = {'summary_id': seller_summary.id, 'order_id': order.id, 'sku_code': sku.sku_code,
                     'sku_desc': sku.sku_desc, 'quantity': quantity, 'price': order_data['price']}
        data_dict['tax_percent'] = open_po.cgst_tax + open_po.sgst_tax + open_po.igst_tax + open_po.utgst_tax + open_po.cess_tax
        if seller_summary.batch_detail:
            batch_detail = seller_summary.batch_detail
            data_dict['batch_no'] = batch_detail.batch_no
            data_dict['mrp'] = batch_detail.mrp
            data_dict['price'] = batch_detail.buy_price
            data_dict['mfg_date'] = ''
            if batch_detail.manufactured_date:
                data_dict['mfg_date'] = batch_detail.manufactured_date.strftime('%m/%d/%Y')
            data_dict['exp_date'] = ''
            if batch_detail.manufactured_date:
                data_dict['exp_date'] = batch_detail.expiry_date.strftime('%m/%d/%Y')
            data_dict['tax_percent'] = batch_detail.tax_percent
        data_dict['amount'] = data_dict['quantity'] * data_dict['price']
        data_dict['tax_value'] = (data_dict['amount']/100) * data_dict['tax_percent']
        orders.append([data_dict])
    supplier_name, order_date, expected_date, remarks = '', '', '', ''
    if seller_summary_objs.exists():
        purchase_order = seller_summary_objs[0].purchase_order
        supplier_name = purchase_order.open_po.supplier.name
        order_date = get_local_date(user, purchase_order.creation_date, send_date=True).strftime("%d %b, %Y")
        remarks = purchase_order.remarks
        if seller_summary_objs[0].seller_po:
            seller = seller_summary_objs[0].seller_po.seller
            seller_details = {'seller_id': seller.seller_id, 'name': seller.name}
    return HttpResponse(json.dumps({'data': orders, 'order_id': order_id, \
                                    'supplier_id': order_data['supplier_id'],\
                                    'po_reference': po_reference, 'order_ids': order_ids,
                                    'supplier_name': supplier_name, 'order_date': order_date,
                                    'remarks': remarks, 'seller_details': seller_details,
                                    'invoice_number': invoice_number, 'invoice_date': invoice_date}))

def get_debit_note_data(rtv_number, user):
    return_to_vendor = ReturnToVendor.objects.select_related('seller_po_summary__purchase_order__open_po__sku').\
                                                        filter(rtv_number=rtv_number,
                                                     seller_po_summary__purchase_order__open_po__sku__user=user.id)
    data_dict = {}
    total_invoice_value = 0
    total_qty = 0
    total_with_gsts = 0
    total_qty = 0
    total_invoice_value = 0
    total_without_discount = 0
    total_only_discount = 0
    total_taxable_value = 0
    total_cgst_value = 0
    total_sgst_value = 0
    total_igst_value = 0
    total_utgst_value = 0
    total_cess_value = 0
    ware_house = UserProfile.objects.filter(user = user).values('company_name', 'cin_number', 'location', 'city',\
                                                                'state', 'country', 'phone_number', 'pin_code',\
                                                                'gst_number', 'address', 'pan_number')
    data_dict.setdefault('warehouse_details', [])
    if len(ware_house):
        data_dict['warehouse_details'] = ware_house[0]
    for obj in return_to_vendor:
        get_po = obj.seller_po_summary.purchase_order.open_po
        data_dict['supplier_name'] = get_po.supplier.name
        data_dict['supplier_address'] = get_po.supplier.address
        data_dict['city'] = get_po.supplier.city
        data_dict['state'] = get_po.supplier.state
        data_dict['pincode'] = get_po.supplier.pincode
        data_dict['pan'] = get_po.supplier.pan_number
        data_dict.setdefault('item_details', [])
        data_dict_item = {}
        data_dict_item['sku_code'] = get_po.sku.sku_code
        data_dict_item['sku_desc'] = get_po.sku.sku_desc
        data_dict_item['hsn_code'] = str(get_po.sku.hsn_code)
        data_dict_item['order_qty'] = obj.quantity
        #data_dict_item['price'] = get_po.price
        data_dict_item['price'] = 0
        data_dict_item['measurement_unit'] = get_po.sku.measurement_type
        data_dict_item['discount'] = get_po.sku.discount_percentage
        data_dict['invoice_num'] = obj.seller_po_summary.invoice_number
        data_dict_item['cgst'] = get_po.cgst_tax
        data_dict_item['sgst'] = get_po.sgst_tax
        data_dict_item['igst'] = get_po.igst_tax
        data_dict_item['utgst'] = get_po.utgst_tax
        data_dict_item['cess'] = get_po.cess_tax
        batch_detail = obj.seller_po_summary.batch_detail
        if batch_detail:
            if batch_detail.buy_price:
                data_dict_item['price'] = batch_detail.buy_price
            if batch_detail.tax_percent:
                temp_tax_percent = batch_detail.tax_percent
                if get_po.supplier.tax_type == 'intra_state':
                    temp_tax_percent = temp_tax_percent/ 2
                    data_dict_item['cgst'] = truncate_float(temp_tax_percent, 1)
                    data_dict_item['sgst'] = truncate_float(temp_tax_percent, 1)
                    data_dict_item['igst'] = 0
                else:
                    data_dict_item['igst'] = temp_tax_percent
                    data_dict_item['sgst'] = 0
                    data_dict_item['cgst'] = 0
        data_dict_item['total_amt'] = data_dict_item['price'] * data_dict_item['order_qty']
        data_dict_item['discount_amt'] = ((data_dict_item['total_amt'] * data_dict_item['discount'])/100)
        data_dict_item['taxable_value'] = data_dict_item['total_amt'] - data_dict_item['discount_amt']
        data_dict_item['cgst_value'] = ((data_dict_item['taxable_value'] * data_dict_item['cgst'])/100)
        data_dict_item['igst_value'] = ((data_dict_item['taxable_value'] * data_dict_item['igst'])/100)
        data_dict_item['sgst_value'] = ((data_dict_item['taxable_value'] * data_dict_item['sgst'])/100)
        data_dict_item['utgst_value'] = ((data_dict_item['taxable_value'] * data_dict_item['utgst'])/100)
        data_dict_item['cess_value'] = ((data_dict_item['taxable_value'] * data_dict_item['cess'])/100)
        data_dict_item['total_with_gsts'] = data_dict_item['taxable_value'] + data_dict_item['cgst_value'] + \
                                            data_dict_item['igst_value'] + data_dict_item['sgst_value'] + data_dict_item['utgst_value'] + \
                                            data_dict_item['cess_value']
        data_dict['rtv_creation_date'] = get_local_date(user, obj.creation_date)
        data_dict['grn_date'] = get_local_date(user, obj.seller_po_summary.creation_date)
        data_dict['date_of_issue_of_original_invoice'] = ''
        if obj.seller_po_summary.invoice_date:
            data_dict['date_of_issue_of_original_invoice'] = obj.seller_po_summary.invoice_date.strftime("%d %b, %Y")
        total_with_gsts = total_with_gsts + data_dict_item['total_with_gsts']
        total_qty = total_qty + data_dict_item['order_qty']
        total_invoice_value = total_invoice_value + data_dict_item['total_with_gsts']
        total_without_discount = total_without_discount + data_dict_item['total_amt']
        total_only_discount = total_only_discount + data_dict_item['discount']
        total_taxable_value = total_taxable_value + data_dict_item['taxable_value']
        total_cgst_value = total_cgst_value + data_dict_item['cgst_value']
        total_sgst_value = total_sgst_value + data_dict_item['sgst_value']
        total_igst_value = total_igst_value + data_dict_item['igst_value']
        total_utgst_value = total_utgst_value + data_dict_item['utgst_value']
        total_cess_value = total_cess_value + data_dict_item['cess_value']
        data_dict['grn_no'] = get_po_reference(obj.seller_po_summary.purchase_order) + '/' + str(obj.seller_po_summary.receipt_number)
        data_dict['item_details'].append(data_dict_item)
    data_dict['total_qty'] = total_qty
    data_dict['total_without_discount'] = total_without_discount
    data_dict['total_only_discount'] = total_only_discount
    data_dict['total_taxable_value'] = total_taxable_value
    data_dict['total_cgst_value'] = total_cgst_value
    data_dict['total_sgst_value'] = total_sgst_value
    data_dict['total_igst_value'] = total_igst_value
    data_dict['total_utgst_value'] = total_utgst_value
    data_dict['total_cess_value'] = total_cess_value
    data_dict['total_with_gsts'] = total_with_gsts
    data_dict['total_invoice_value'] = total_invoice_value
    data_dict['rtv_number'] = rtv_number
    return data_dict


def prepare_rtv_json_data(request_data, user):
    data_list = []
    for ind in range(0, len(request_data['summary_id'])):
        data_dict = {}
        if 'rtv_id' in request_data:
            data_dict['rtv_id'] = request_data['rtv_id'][ind]
        if request_data['location'][ind] and request_data['return_qty'][ind]:
            quantity = request_data['return_qty'][ind]
            seller_summary = SellerPOSummary.objects.get(id=request_data['summary_id'][ind])
            data_dict['summary_id'] = request_data['summary_id'][ind]
            data_dict['quantity'] = quantity
            stock_filter = {'sku__user': user.id, 'quantity__gt': 0,
                            'sku_id': seller_summary.purchase_order.open_po.sku_id}
            reserved_dict = {'stock__sku_id': seller_summary.purchase_order.open_po.sku_id,
                             'stock__sku__user': user.id, 'status': 1}
            location_master = LocationMaster.objects.filter(location=request_data['location'][ind],
                                                            zone__user=user.id)
            if location_master:
                data_dict['location'] = location_master[0]
                stock_filter['location_id'] = location_master[0].id
                reserved_dict['stock__location_id'] = location_master[0].id
            else:
                return data_list, "%s is Invalid Location" % (request_data['location'][ind])
            if seller_summary.batch_detail:
                if seller_summary.batch_detail.batch_no:
                    stock_filter['batch_detail__batch_no'] = seller_summary.batch_detail.batch_no
                    reserved_dict['stock__batch_detail__batch_no'] = seller_summary.batch_detail.batch_no
                if seller_summary.batch_detail.mrp:
                    stock_filter['batch_detail__mrp'] = seller_summary.batch_detail.mrp
                    reserved_dict['stock__batch_detail__mrp'] = seller_summary.batch_detail.mrp
                if seller_summary.seller_po:
                    stock_filter['sellerstock__seller_id'] = seller_summary.seller_po.seller_id
                    reserved_dict["stock__sellerstock__seller_id"] = seller_summary.seller_po.seller_id
            stocks = StockDetail.objects.filter(**stock_filter)
            if not stocks:
                return data_list, 'No Stocks Found'
            data_dict['stocks'] = stocks
            stock_count = stocks.aggregate(Sum('quantity'))['quantity__sum']
            reserved_quantity = \
                PicklistLocation.objects.exclude(stock=None).filter(**reserved_dict).aggregate(Sum('reserved'))[
                    'reserved__sum']
            if reserved_quantity:
                stock_count = stock_count - reserved_quantity
            if stock_count < float(quantity):
                return data_list, 'Return Quantity Exceeded available quantity'
            data_list.append(data_dict)
        elif request_data['location'][ind] or request_data['return_qty'][ind]:
            return data_list, 'Location or Quantity Missing'
    return data_list, ''


def save_update_rtv(data_list, return_type=''):
    updated_rtvs = []
    for ind, final_dict in enumerate(data_list):
        if final_dict.get('rtv_id', '') and final_dict['rtv_id'] not in updated_rtvs:
            rtv_obj = ReturnToVendor.objects.get(id=final_dict['rtv_id'])
            rtv_obj.location_id = final_dict['location'].id
            if return_type:
                rtv_obj.return_type = return_type
            rtv_obj.quantity = final_dict['quantity']
            rtv_obj.save()
            updated_rtvs.append(final_dict['rtv_id'])
        else:
            rtv_obj = ReturnToVendor.objects.create(seller_po_summary_id=final_dict['summary_id'],
                                                    quantity=final_dict['quantity'], status=1,
                                                    location_id=final_dict['location'].id,
                                                    return_type=return_type,
                                                    creation_date=datetime.datetime.now())
            data_list[ind]['rtv_id'] = rtv_obj.id
    return data_list
@csrf_exempt
@login_required
@get_admin_user
def save_rtv(request, user=''):
    request_data = dict(request.POST.iterlists())
    enable_dc_returns = request.POST.get('enable_dc_returns', '')
    if enable_dc_returns == 'true':
        return_type = 'DC'
    else:
        return_type = 'Invoice'
    try:
        data_list, status = prepare_rtv_json_data(request_data, user)
        if status:
            return HttpResponse(status)
        if data_list:
            data_list = save_update_rtv(data_list, return_type)
        return HttpResponse("Saved Successfully")
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Exception raised while saving RTV for user %s and request data is %s and error is %s" %
                 (str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Save RTV Failed")


@csrf_exempt
@login_required
@get_admin_user
def create_rtv(request, user=''):
    request_data = dict(request.POST.iterlists())
    enable_dc_returns = request.POST.get('enable_dc_returns', '')
    if enable_dc_returns == 'true':
        return_type = 'DC'
    else:
        return_type = 'Invoice'
    data_list = []
    try:
        data_list, status = prepare_rtv_json_data(request_data, user)
        if status:
            return HttpResponse(status)
        if data_list:
            data_list = save_update_rtv(data_list)
            rtv_no = get_incremental(user, 'rtv')
            date_val = datetime.datetime.now().strftime('%Y%m%d')
            rtv_number = '%s-%s-%s' % ('RTV', date_val, rtv_no)
            for final_dict in data_list:
                update_stock_detail(final_dict['stocks'], float(final_dict['quantity']), user)
                #ReturnToVendor.objects.create(rtv_number=rtv_number, seller_po_summary_id=final_dict['summary_id'],
                #                              quantity=final_dict['quantity'], status=0, creation_date=datetime.datetime.now())
                rtv_obj = ReturnToVendor.objects.get(id=final_dict['rtv_id'])
                rtv_obj.rtv_number = rtv_number
                rtv_obj.return_type = return_type
                rtv_obj.status=0
                rtv_obj.save()
            report_data_dict = {}
            show_data_invoice = get_debit_note_data(rtv_number, user)

            return render(request, 'templates/toggle/milk_basket_print.html', {'show_data_invoice' : [show_data_invoice]})
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Exception raised while creating RTV for user %s and request data is %s and error is %s" %
                 (str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Create RTV Failed")


def get_saved_rtvs(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, col_filters={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    search_params = {}
    search_params['status'] = 1
    search_params['seller_po_summary__purchase_order__open_po__sku_id__in'] = sku_master_ids
    lis = ['seller_po_summary__purchase_order__open_po__supplier_id',
           'seller_po_summary__purchase_order__open_po__supplier_id',
           'seller_po_summary__purchase_order__open_po__supplier__name',
           'seller_po_summary__invoice_number', 'seller_po_summary__challan_number',
           'seller_po_summary__purchase_order__order_id', 'purchase_order_date',
           'seller_po_summary__invoice_date', 'seller_po_summary__challan_date', 'total', 'total']
    #enable_dc_returns = request.POST.get("enable_dc_returns", "")
    #if enable_dc_returns:
        #lis.append('seller_po_summary__challan_number')
        #dc_or_inv_number = 'seller_po_summary__challan_number'
    #else:
        #lis.append('seller_po_summary__invoice_number')
        #dc_or_inv_number = 'seller_po_summary__invoice_number'

    headers1, filters, filter_params1 = get_search_params(request)
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    if search_term:
        results = ReturnToVendor.objects.values('seller_po_summary__purchase_order__open_po__supplier_id',
                   'seller_po_summary__purchase_order__open_po__supplier__name',
                   'seller_po_summary__purchase_order__order_id',
                   'seller_po_summary__invoice_number', 'seller_po_summary__invoice_date',
                   'seller_po_summary__challan_number', 'seller_po_summary__challan_date').distinct().annotate(
            total=Sum('quantity'), purchase_order_date=Cast('seller_po_summary__purchase_order__creation_date', DateField())). \
            filter(seller_po_summary__purchase_order__open_po__sku__user=user.id, **search_params).order_by(order_data)

    else:
        results = ReturnToVendor.objects.values('seller_po_summary__purchase_order__open_po__supplier_id',
                   'seller_po_summary__purchase_order__open_po__supplier__name',
                   'seller_po_summary__purchase_order__order_id',
                   'seller_po_summary__invoice_number', 'seller_po_summary__invoice_date',
                   'seller_po_summary__challan_number', 'seller_po_summary__challan_date').distinct().annotate(
            total=Sum('quantity'), purchase_order_date=Cast('seller_po_summary__purchase_order__creation_date', DateField())). \
            filter(seller_po_summary__purchase_order__open_po__sku__user=user.id, **search_params).order_by(order_data)

    temp_data['recordsTotal'] = results.count()
    temp_data['recordsFiltered'] = results.count()

    count = 0
    for result in results[start_index: stop_index]:
        rem_quantity = result['total']
        rtvs = ReturnToVendor.objects.select_related('seller_po_summary__purchase_order__open_po__sku',
                                                                'seller_po_summary__purchase_order').\
                                                    filter(seller_po_summary__purchase_order__open_po__sku__user=user.id,
                                                           seller_po_summary__purchase_order__order_id=result['seller_po_summary__purchase_order__order_id'],
                                                           seller_po_summary__invoice_number=result['seller_po_summary__invoice_number'],
                                                           seller_po_summary__challan_number=result['seller_po_summary__challan_number'])
        seller_summary = rtvs[0].seller_po_summary
        order_reference = get_po_reference(seller_summary.purchase_order)
        open_po = seller_summary.purchase_order.open_po
        data_id = '%s:%s' % (result['seller_po_summary__purchase_order__order_id'], result.get('seller_po_summary__invoice_number', ''))
        checkbox = "<input type='checkbox' name='data_id' value='%s'>" % (data_id)
        po_date = get_local_date(request.user, seller_summary.purchase_order.creation_date,
                                 send_date=True).strftime("%d %b, %Y")
        invoice_number = ''
        if result.get('seller_po_summary__invoice_number', ''):
            invoice_number = result.get('seller_po_summary__invoice_number', '')
        dc_number = ''
        if result.get('seller_po_summary__challan_number', ''):
            dc_number = result.get('seller_po_summary__challan_number', '')
        invoice_date = po_date
        if result['seller_po_summary__invoice_date']:
            invoice_date = result['seller_po_summary__invoice_date'].strftime("%d %b, %Y")
        challan_date = ''
        if result['seller_po_summary__challan_date']:
            challan_date = result['seller_po_summary__challan_date'].strftime("%d %b, %Y")
        total_amt = 0
        tax = open_po.cgst_tax + open_po.sgst_tax + open_po.igst_tax + open_po.utgst_tax
        for rtv in rtvs:
            if rtv.seller_po_summary.batch_detail:
                total_amt += rtv.quantity * rtv.seller_po_summary.batch_detail.buy_price
            else:
                total_amt += rtv.quantity * rtv.seller_po_summary.purchase_order.open_po.price
        total_amt = total_amt + ((total_amt/100) * tax)
        temp_data['aaData'].append(OrderedDict((('', checkbox),('data_id', data_id),
                                                ('Supplier ID', result['seller_po_summary__purchase_order__open_po__supplier_id']),
                                                ('Supplier Name', result['seller_po_summary__purchase_order__open_po__supplier__name']),
                                                ('PO Number', order_reference), ('PO Date', po_date),
                                                ('Invoice Number', invoice_number), ('Invoice Date', invoice_date),
                                                ('Total Quantity', rem_quantity), ('Total Amount', total_amt),
                                                ('id', count), ('Challan Number', dc_number),
                                                ('Challan Date', challan_date),
                                                ('DT_RowClass', 'results'))))
        count += 1


@csrf_exempt
@login_required
@get_admin_user
def get_saved_rtv_data(request, user=''):
    order_id, invoice_num = request.GET['data_id'].split(':')
    rtv_filter = {'seller_po_summary__purchase_order__open_po__sku__user': user.id,
                    'seller_po_summary__purchase_order__order_id': order_id,
                  'status': 1}
    if invoice_num:
        rtv_filter['seller_po_summary__invoice_number'] = invoice_num
    rtv_objs = ReturnToVendor.objects.filter(**rtv_filter)
    if not rtv_objs:
        return HttpResponse("No Data found")
    seller_summary = rtv_objs[0].seller_po_summary
    po_reference = get_po_reference(seller_summary.purchase_order)
    invoice_number = seller_summary.invoice_number
    invoice_date = get_local_date(user, seller_summary.creation_date, send_date=True).strftime("%d %b, %Y")
    if seller_summary.invoice_date:
        invoice_date = seller_summary.invoice_date.strftime("%d %b, %Y")
    orders = []
    order_data = {}
    order_ids = []
    seller_details = {}
    for rtv_obj in rtv_objs:
        seller_summary = rtv_obj.seller_po_summary
        order = seller_summary.purchase_order
        open_po = order.open_po
        order_data = get_purchase_order_data(order)
        quantity = rtv_obj.quantity
        sku = open_po.sku
        if quantity <= 0:
            continue
        data_dict = {'summary_id': seller_summary.id, 'order_id': order.id, 'sku_code': sku.sku_code,
                     'sku_desc': sku.sku_desc, 'quantity': quantity, 'price': order_data['price'],
                     'rtv_id': rtv_obj.id, 'location': rtv_obj.location.location,
                     'return_qty': rtv_obj.quantity}
        data_dict['tax_percent'] = open_po.cgst_tax + open_po.sgst_tax + open_po.igst_tax + \
                                   open_po.utgst_tax + open_po.cess_tax
        if seller_summary.batch_detail:
            batch_detail = seller_summary.batch_detail
            data_dict['batch_no'] = batch_detail.batch_no
            data_dict['mrp'] = batch_detail.mrp
            data_dict['price'] = batch_detail.buy_price
            data_dict['mfg_date'] = ''
            if batch_detail.manufactured_date:
                data_dict['mfg_date'] = batch_detail.manufactured_date.strftime('%m/%d/%Y')
            data_dict['exp_date'] = ''
            if batch_detail.manufactured_date:
                data_dict['exp_date'] = batch_detail.expiry_date.strftime('%m/%d/%Y')
            data_dict['tax_percent'] = batch_detail.tax_percent
        data_dict['amount'] = data_dict['quantity'] * data_dict['price']
        data_dict['tax_value'] = (data_dict['amount']/100) * data_dict['tax_percent']
        orders.append([data_dict])
    supplier_name, order_date, expected_date, remarks = '', '', '', ''
    if rtv_objs.exists():
        purchase_order = rtv_objs[0].seller_po_summary.purchase_order
        supplier_name = purchase_order.open_po.supplier.name
        order_date = get_local_date(user, purchase_order.creation_date, send_date=True).strftime("%d %b, %Y")
        remarks = purchase_order.remarks
        if rtv_objs[0].seller_po_summary.seller_po:
            seller = rtv_objs[0].seller_po_summary.seller_po.seller
            seller_details = {'seller_id': seller.seller_id, 'name': seller.name}
    return HttpResponse(json.dumps({'data': orders, 'order_id': order_id, \
                                    'supplier_id': order_data['supplier_id'],\
                                    'po_reference': po_reference, 'order_ids': order_ids,
                                    'supplier_name': supplier_name, 'order_date': order_date,
                                    'remarks': remarks, 'seller_details': seller_details,
                                    'invoice_number': invoice_number, 'invoice_date': invoice_date}))

def stock_transfer_mail_pdf(request, f_name, html_data, warehouse):
    receivers = []
    attachments = create_mail_attachments(f_name, html_data)
    company_name = warehouse.first_name
    internal_mail = MiscDetail.objects.filter(user=request.user.id, misc_type='Internal Emails')
    misc_internal_mail = MiscDetail.objects.filter(user=request.user.id, misc_type='internal_mail', misc_value='true')
    if misc_internal_mail and internal_mail:
        internal_mail = internal_mail[0].misc_value.split(",")
        receivers.extend(internal_mail)
    misc_stock_transfer_type = MiscDetail.objects.filter(user=request.user.id, misc_type='stock_transfer_note', misc_value='true')
    if misc_stock_transfer_type:
        destination_warehouse = User.objects.filter(username=warehouse.username)
        if destination_warehouse:
            destination_wh_email = destination_warehouse[0].email
            receivers.append(destination_wh_email)
    email_body = 'Please find the Stock Transfer Order in the attachment'
    email_subject = '%s %s' % (company_name, 'Stock Transfer Note')
    if len(receivers):
        send_mail_attachment(receivers, email_subject, email_body, files=attachments)

def render_st_html_data(request, user, warehouse, all_data):
    user_profile = UserProfile.objects.filter(user = user).values('phone_number', 'company_name', 'location',
        'city', 'state', 'country', 'pin_code', 'address', 'wh_address', 'wh_phone_number', 'gst_number')
    destination_user_profile = UserProfile.objects.filter(user = warehouse).values('phone_number', 
        'company_name', 'location', 'city', 'state', 'country', 'pin_code', 'address', 'wh_address', 'wh_phone_number', 'gst_number')
    po_skus_list = []
    po_skus_dict = OrderedDict()
    total_order_qty = 0
    total_amount = 0
    stock_transfer_id = 0
    for key, value in all_data.iteritems():
        for obj in value:
            po_skus_dict = {}
            st_id = obj[3]
            stock_transfer_obj = OpenST.objects.get(id=st_id)
            po_skus_list.append( OrderedDict( ( ('sku', stock_transfer_obj.sku), 
                ('sku_desc', stock_transfer_obj.sku.sku_desc), ( 'order_qty', int(stock_transfer_obj.order_quantity)), 
                ('measurement_type', stock_transfer_obj.sku.measurement_type), ('price', float(stock_transfer_obj.price)),
                ('amount', stock_transfer_obj.price * stock_transfer_obj.order_quantity), ('sgst', 0), ('cgst', 0), 
                ('igst', 0), ('utgst', 0) )) )
            total_order_qty += int(stock_transfer_obj.order_quantity)
            total_amount += float(stock_transfer_obj.price) * int(stock_transfer_obj.order_quantity)
            stock_transfer_date = stock_transfer_obj.creation_date
    table_headers = ['WMS Code', 'Description', 'Quantity', 'Measurement Type', 'Unit Price',
    'Amount', 'SGST(%)', 'CGST(%)', 'IGST(%)', 'UTGST(%)']
    stock_transfer_id_obj = StockTransfer.objects.filter(st_po__open_st = st_id)
    if stock_transfer_id_obj:
        stock_transfer_id = stock_transfer_id_obj[0].order_id
    data_dict = {
        'current_company_name' : user_profile[0]['company_name'], 'current_wh_address' : user_profile[0]['address'],
        'stock_transfer_id' : stock_transfer_id, 'stock_transfer_date' : stock_transfer_date,
        'current_wh_gstin' : user_profile[0]['gst_number'],
        'current_wh_ship_to_address' : user_profile[0]['address'], 'current_telephone' : user_profile[0]['phone_number'],
        'destination_company_name' : warehouse.username,
        'destination_wh_address' : destination_user_profile[0]['address'],
        'destination_gst_number' : destination_user_profile[0]['gst_number'],
        'destination_telephone' : destination_user_profile[0]['phone_number'],
        'current_pan_number' : '', 'destination_pan_number' : '',
        'total_order_qty' : total_order_qty, 'total_amount' : total_amount, 'st_transfer_data' : po_skus_list,
        'table_headers' : table_headers
    }
    t = loader.get_template('templates/toggle/stock_transfer_mail.html')
    html_data = t.render(data_dict)
    return html_data

def get_sales_return_print_json(return_id, user):
    sales_returns = OrderReturns.objects.select_related('sku', 'order', 'seller_order').\
                                                        filter(return_id=return_id, sku__user=user.id)
    data_dict = {}
    total_invoice_value = 0
    total_qty = 0
    total_with_gsts = 0
    total_qty = 0
    total_invoice_value = 0
    total_without_discount = 0
    total_only_discount = 0
    total_taxable_value = 0
    total_cgst_value = 0
    total_sgst_value = 0
    total_igst_value = 0
    total_utgst_value = 0
    total_cess_value = 0
    ware_house = UserProfile.objects.filter(user = user).values('company_name', 'cin_number', 'location', 'city',\
                                                                'state', 'country', 'phone_number', 'pin_code',\
                                                                'gst_number', 'address', 'pan_number')
    data_dict.setdefault('warehouse_details', [])
    if len(ware_house):
        data_dict['warehouse_details'] = ware_house[0]
    for obj in sales_returns:
        if not obj.order:
            continue
        data_dict['order_id'] = obj.order.original_order_id
        data_dict['return_id'] = obj.return_id
        customer_master = CustomerMaster.objects.filter(user=user.id, customer_id=obj.order.customer_id)
        if customer_master:
            customer_master = customer_master[0]
            data_dict['customer_name'] = customer_master.name
            data_dict['supplier_address'] = customer_master.address
            data_dict['city'] = customer_master.city
            data_dict['state'] = customer_master.state
            data_dict['pincode'] = customer_master.pincode
            data_dict['pan'] = customer_master.pan_number
        else:
            data_dict['customer_name'] = obj.order.customer_name
            data_dict['supplier_address'] = obj.order.address
            data_dict['city'] = obj.order.city
            data_dict['state'] = obj.order.state
            data_dict['pincode'] = obj.order.pin_code
            data_dict['pan'] = ''
        data_dict.setdefault('item_details', [])
        data_dict_item = {}
        data_dict_item['sku_code'] = obj.sku.sku_code
        data_dict_item['sku_desc'] = obj.sku.sku_desc
        data_dict_item['hsn_code'] = str(obj.sku.hsn_code)
        data_dict_item['order_qty'] = obj.quantity
        #data_dict_item['price'] = get_po.price
        data_dict_item['price'] = obj.order.unit_price
        data_dict_item['measurement_unit'] = obj.sku.measurement_type
        data_dict_item['discount'] = 0
        data_dict['invoice_num'] = ''
        cust_order_obj = obj.order.customerordersummary_set.filter().values('cgst_tax', 'sgst_tax',
                                                                    'igst_tax', 'utgst_tax')
        order_summary = {}
        if cust_order_obj:
            order_summary = cust_order_obj[0]
        data_dict_item['cgst'] = order_summary.get('cgst_tax', 0)
        data_dict_item['sgst'] = order_summary.get('sgst_tax',0)
        data_dict_item['igst'] = order_summary.get('igst_tax',0)
        data_dict_item['utgst'] = order_summary.get('utgst_tax',0)
        data_dict_item['total_amt'] = data_dict_item['price'] * data_dict_item['order_qty']
        data_dict_item['discount_amt'] = ((data_dict_item['total_amt'] * data_dict_item['discount'])/100)
        data_dict_item['taxable_value'] = data_dict_item['total_amt'] - data_dict_item['discount_amt']
        data_dict_item['cgst_value'] = ((data_dict_item['taxable_value'] * data_dict_item['cgst'])/100)
        data_dict_item['igst_value'] = ((data_dict_item['taxable_value'] * data_dict_item['igst'])/100)
        data_dict_item['sgst_value'] = ((data_dict_item['taxable_value'] * data_dict_item['sgst'])/100)
        data_dict_item['utgst_value'] = ((data_dict_item['taxable_value'] * data_dict_item['utgst'])/100)
        data_dict_item['total_with_gsts'] = data_dict_item['taxable_value'] + data_dict_item['cgst_value'] + \
                                            data_dict_item['igst_value'] + data_dict_item['sgst_value'] + data_dict_item['utgst_value']
        data_dict['creation_date'] = get_local_date(user, obj.creation_date)
        data_dict['date_of_issue_of_original_invoice'] = get_local_date(user, obj.order.creation_date)#change required
        total_with_gsts = total_with_gsts + data_dict_item['total_with_gsts']
        total_qty = total_qty + data_dict_item['order_qty']
        total_invoice_value = total_invoice_value + data_dict_item['total_with_gsts']
        total_without_discount = total_without_discount + data_dict_item['total_amt']
        total_only_discount = total_only_discount + data_dict_item['discount']
        total_taxable_value = total_taxable_value + data_dict_item['taxable_value']
        total_cgst_value = total_cgst_value + data_dict_item['cgst_value']
        total_sgst_value = total_sgst_value + data_dict_item['sgst_value']
        total_igst_value = total_igst_value + data_dict_item['igst_value']
        total_utgst_value = total_utgst_value + data_dict_item['utgst_value']
        data_dict['item_details'].append(data_dict_item)
    data_dict['total_qty'] = total_qty
    data_dict['total_without_discount'] = total_without_discount
    data_dict['total_only_discount'] = total_only_discount
    data_dict['total_taxable_value'] = total_taxable_value
    data_dict['total_cgst_value'] = total_cgst_value
    data_dict['total_sgst_value'] = total_sgst_value
    data_dict['total_igst_value'] = total_igst_value
    data_dict['total_utgst_value'] = total_utgst_value
    data_dict['total_with_gsts'] = total_with_gsts
    data_dict['total_invoice_value'] = total_invoice_value
    data_dict['return_id'] = return_id
    return data_dict


@csrf_exempt
@login_required
@get_admin_user
def map_ean_sku_code(request, user=''):
    sku_code = request.GET.get('map_sku_code')
    ean_number = request.GET.get('ean_number')
    try:
        ean_number = int(ean_number)
    except:
        return HttpResponse(json.dumps({'message': 'EAN Number should be Number', 'status': 0}))
    sku_master = SKUMaster.objects.filter(user=user.id, sku_code=sku_code)
    if not sku_master.exists():
        return HttpResponse(json.dumps({'message': 'Invalid SKU Code', 'status': 0}))
    ean_number_obj = EANNumbers.objects.filter(sku__user=user.id, ean_number=ean_number)
    sku_master_ean = SKUMaster.objects.filter(ean_number=ean_number, user=user.id)
    if not (ean_number_obj or sku_master_ean):
        EANNumbers.objects.create(sku_id=sku_master[0].id, ean_number=ean_number,
                                  creation_date=datetime.datetime.now())
    else:
        return HttpResponse(json.dumps({'message': 'EAN Number already mapped', 'status': 0}))
    return HttpResponse(json.dumps({'message': 'Success', 'status': 1}))


@csrf_exempt
@login_required
@get_admin_user
def get_grn_level_data(request, user=''):
    data_dict = ''
    invoice_no = ''
    invoice_date = ''
    dc_number = ''
    dc_date = ''
    po_data = []
    try:
        po_number = request.GET['po_number']
        temp = po_number.split('_')[1]
        temp1 = temp.split('/')
        receipt_no = ''
        if len(temp1) > 1:
            po_order_id = temp1[0]
            receipt_no = temp1[1]
        else:
            po_order_id = temp1[0]
        results = PurchaseOrder.objects.filter(order_id=po_order_id, open_po__sku__user=user.id)
        if receipt_no:
            results = results.distinct().filter(sellerposummary__receipt_number=receipt_no)
        total = 0
        total_qty = 0
        total_tax = 0
        for data in results:
            receipt_type = ''
            quantity = data.received_quantity
            #invoice_date = data.updation_date
            if receipt_no:
                po_data_dict = {}
                seller_summary_objs = data.sellerposummary_set.filter(receipt_number=receipt_no)
                open_data = data.open_po
                for seller_summary_obj in seller_summary_objs:
                    if seller_summary_obj.invoice_date:
                        invoice_date = seller_summary_obj.invoice_date
                    if seller_summary_obj.challan_date:
                        dc_date = seller_summary_obj.challan_date
                    po_data_dict['sku_code'] = data.open_po.sku.sku_code
                    po_data_dict['sku_desc'] = data.open_po.sku.sku_desc
                    po_data_dict['quantity'] = seller_summary_obj.quantity
                    invoice_no = seller_summary_obj.invoice_number
                    dc_number = seller_summary_obj.challan_number
                    po_data_dict['price'] = open_data.price
                    po_data_dict['cgst_tax'] = open_data.cgst_tax
                    po_data_dict['sgst_tax'] = open_data.sgst_tax
                    po_data_dict['igst_tax'] = open_data.igst_tax
                    po_data_dict['utgst_tax'] = open_data.utgst_tax
                    po_data_dict['cess_tax'] = open_data.cess_tax
                    po_data_dict['tax_percent'] = open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + \
                                                    open_data.utgst_tax
                    po_data_dict['confirm_key'] = 'seller_po_summary_id'
                    po_data_dict['confirm_id'] = seller_summary_obj.id
                    po_data_dict['buy_price'] = 0
                    po_data_dict['batch_no'] = ''
                    po_data_dict['mrp'] = 0
                    po_data_dict['mfg_date'] = ''
                    po_data_dict['exp_date'] = ''
                    po_data_dict['discount_percentage'] = seller_summary_obj.discount_percent
                    if seller_summary_obj.batch_detail:
                        po_data_dict['buy_price'] = seller_summary_obj.batch_detail.buy_price
                        po_data_dict['batch_no'] = seller_summary_obj.batch_detail.batch_no
                        po_data_dict['mrp'] = seller_summary_obj.batch_detail.mrp
                        po_data_dict['mfg_date'] = ''
                        po_data_dict['exp_date'] = ''
                        if seller_summary_obj.batch_detail.manufactured_date:
                            po_data_dict['mfg_date'] = seller_summary_obj.batch_detail.manufactured_date.strftime('%m/%d/%Y')
                        if seller_summary_obj.batch_detail.expiry_date:
                            po_data_dict['exp_date'] = seller_summary_obj.batch_detail.expiry_date.strftime('%m/%d/%Y')
                        temp_tax_percent = seller_summary_obj.batch_detail.tax_percent
                        po_data_dict['tax_percent'] = temp_tax_percent
                        if seller_summary_obj.purchase_order.open_po.supplier.tax_type == 'intra_state':
                            temp_tax_percent = temp_tax_percent / 2
                            po_data_dict['cgst_tax'] = truncate_float(temp_tax_percent, 1)
                            po_data_dict['sgst_tax'] = truncate_float(temp_tax_percent, 1)
                            po_data_dict['igst_tax'] = 0
                        else:
                            po_data_dict['igst_tax'] = temp_tax_percent
                            po_data_dict['cgst_tax'] = 0
                            po_data_dict['sgst_tax'] = 0
                    amount = float(po_data_dict['quantity']) * float(po_data_dict['price'])
                    total += amount
                    total_qty += quantity
                    po_data.append([po_data_dict])

            else:
                open_data = data.open_po
                po_data_dict = {}
                po_data_dict['sku_code'] = data.open_po.sku.sku_code
                po_data_dict['sku_desc'] = data.open_po.sku.sku_desc
                po_data_dict['quantity'] = data.received_quantity
                po_data_dict['price'] = open_data.price
                po_data_dict['cgst_tax'] = open_data.cgst_tax
                po_data_dict['sgst_tax'] = open_data.sgst_tax
                po_data_dict['igst_tax'] = open_data.igst_tax
                po_data_dict['utgst_tax'] = open_data.utgst_tax
                po_data_dict['cess_tax'] = open_data.cess_tax
                po_data_dict['tax_percent'] = open_data.cgst_tax + open_data.sgst_tax + open_data.igst_tax + \
                                              open_data.utgst_tax
                po_data_dict['confirm_key'] = 'purchase_order_id'
                po_data_dict['confirm_id'] = data.id
                amount = float(po_data_dict['quantity']) * float(po_data_dict['price'])
                po_data.append([po_data_dict])
        if results:
            purchase_order = results[0]
            address = purchase_order.open_po.supplier.address
            address = '\n'.join(address.split(','))
            telephone = purchase_order.open_po.supplier.phone_number
            name = purchase_order.open_po.supplier.name
            supplier_id = purchase_order.open_po.supplier.id
            supplier_name = purchase_order.open_po.supplier.name
            order_id = purchase_order.order_id
            po_reference = '%s%s_%s' % (
            purchase_order.prefix, str(purchase_order.creation_date).split(' ')[0].replace('-', ''),
            purchase_order.order_id)
            if receipt_no:
                po_reference = '%s/%s' % (po_reference, receipt_no)
            order_date = datetime.datetime.strftime(purchase_order.open_po.creation_date, "%d-%m-%Y")
            if invoice_date:
                invoice_date = datetime.datetime.strftime(invoice_date, "%m/%d/%Y")
            if dc_date:
                dc_date = datetime.datetime.strftime(dc_date, "%m/%d/%Y")
            user_profile = UserProfile.objects.get(user_id=user.id)
            w_address, company_address = get_purchase_company_address(user_profile)#user_profile.address

        title = 'Purchase Order'
        #if receipt_type == 'Hosted Warehouse':
        #    title = 'Stock Transfer Note'
        return HttpResponse(json.dumps({'data': po_data, 'address': address,
                       'order_id': order_id, 'telephone': str(telephone), 'name': name, 'order_date': order_date,
                       'total_price': total, 'data_dict': data_dict, 'invoice_number': invoice_no,
                       'po_number': po_reference, 'company_address': w_address, 'company_name': user_profile.company_name,
                       'display': 'display-none', 'receipt_type': receipt_type, 'title': title,
                       'total_received_qty': total_qty, 'invoice_date': invoice_date, 'total_tax': total_tax,
                       'company_address': company_address, 'supplier_id': supplier_id,
                       'supplier_name': supplier_name, 'dc_number': dc_number,
                        'dc_date': dc_date
                    }))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Get GRN data failed for request user %s user %s and request data is %s and error is %s" %
                 (str(request.user.username), str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Get GRN Data Failed")


@csrf_exempt
@login_required
@get_admin_user
def update_existing_grn(request, user=''):
    data_dict = ''
    headers = (
    'WMS CODE', 'Order Quantity', 'Received Quantity', 'Measurement', 'Unit Price', 'CSGT(%)', 'SGST(%)', 'IGST(%)',
    'UTGST(%)', 'Amount', 'Description', 'CESS(%)')
    putaway_data = {headers: []}
    total_received_qty = 0
    total_order_qty = 0
    total_price = 0
    total_tax = 0
    is_putaway = ''
    if user.username=='milkbasket' and (not request.POST.get('invoice_number', '') and not request.POST.get('dc_number', '')):
        return HttpResponse("Invoice/DC Number  is Mandatory")
    if user.username == 'milkbasket' and (not request.POST.get('invoice_date', '') and not request.POST.get('dc_date', '')):
        return HttpResponse("Invoice/DC Date is Mandatory")
    invoice_num = request.POST.get('invoice_number', '')
    if invoice_num:
        supplier_id = ''
        if request.POST.get('supplier_id', ''):
            supplier_id = request.POST['supplier_id']
        inv_status = po_invoice_number_check(user, invoice_num, supplier_id)
        if inv_status:
            req_po_number = request.POST['po_number']
            temp_inv_status = inv_status.replace('Invoice Number already Mapped to ', '')
            if temp_inv_status != req_po_number:
                return HttpResponse(inv_status)
    request_data = request.POST
    myDict = dict(request_data.iterlists())

    log.info('Request params for Update GRN for request user ' + request.user.username +' user ' + user.username + ' is ' + str(myDict))
    try:
        field_mapping = {'exp_date': 'expiry_date', 'mfg_date': 'manufactured_date', 'quantity': 'quantity',
                         'discount_percentage': 'discount_percent', 'batch_no': 'batch_no',
                         'mrp': 'mrp', 'buy_price': 'buy_price', 'invoice_number': 'invoice_number',
                         'invoice_date': 'invoice_date', 'dc_date': 'challan_date', 'dc_number': 'challan_number'}
        zero_index_keys = ['invoice_number', 'invoice_date', 'dc_number', 'dc_date']
        for ind in range(0, len(myDict['confirm_key'])):
            model_name = myDict['confirm_key'][ind].strip('_id')
            if myDict['confirm_key'][ind] == 'seller_po_summary_id':
                model_obj = SellerPOSummary.objects.get(id=myDict['confirm_id'][ind])
            else:
                model_obj = PurchaseOrder.objects.get(id=myDict['confirm_id'][ind])
            batch_dict = {}
            for key, value in myDict.iteritems():
                if not key in field_mapping.keys():
                    continue
                if key in zero_index_keys:
                    value = value[0]
                else:
                    value = value[ind]
                if not myDict['confirm_key'][ind] == 'seller_po_summary_id':
                    continue
                if key in ['exp_date', 'mfg_date']:
                    if model_obj.batch_detail:
                        if getattr(model_obj.batch_detail, field_mapping[key]):
                            prev_val = datetime.datetime.strftime(getattr(model_obj.batch_detail, field_mapping[key]), '%m/%d/%Y')
                            if myDict[key][ind] != prev_val and value:
                                setattr(model_obj.batch_detail, field_mapping[key],
                                        datetime.datetime.strptime(value, '%m/%d/%Y'))
                                model_obj.batch_detail.save()
                                create_update_table_history(user, model_obj.id, model_name, field_mapping[key],
                                                            prev_val, value)
                            elif not value:
                                setattr(model_obj.batch_detail, field_mapping[key], None)
                                model_obj.batch_detail.save()
                                create_update_table_history(user, model_obj.id, model_name, field_mapping[key], prev_val, value)
                        elif value:
                            setattr(model_obj.batch_detail, field_mapping[key],
                                    datetime.datetime.strptime(value, '%m/%d/%Y'))
                            model_obj.batch_detail.save()
                            create_update_table_history(user, model_obj.id, model_name, field_mapping[key],
                                                        '', value)
                    else:
                        batch_dict[field_mapping[key]] = value
                elif key in ['mrp', 'buy_price', 'tax_percnet']:
                    try:
                        value = float(value)
                    except:
                        value = 0
                    if model_obj.batch_detail:
                        prev_val = float(getattr(model_obj.batch_detail, field_mapping[key]))
                        if prev_val != value:
                            setattr(model_obj.batch_detail, field_mapping[key], value)
                            model_obj.batch_detail.save()
                            create_update_table_history(user, model_obj.id, model_name, field_mapping[key], prev_val, value)
                    else:
                        batch_dict[field_mapping[key]] = value
                elif key in ['quantity', 'discount_percentage']:
                    try:
                        value = float(value)
                    except:
                        value = 0
                    prev_val = float(getattr(model_obj, field_mapping[key]))
                    if prev_val != value:
                        setattr(model_obj, field_mapping[key], value)
                        model_obj.save()
                        create_update_table_history(user, model_obj.id, model_name, field_mapping[key],
                                                    prev_val, value)
                elif key == 'batch_no':
                    if model_obj.batch_detail:
                        prev_val = getattr(model_obj.batch_detail, field_mapping[key])
                        if prev_val != value:
                            setattr(model_obj.batch_detail, field_mapping[key], value)
                            model_obj.batch_detail.save()
                            create_update_table_history(user, model_obj.id, model_name, field_mapping[key],
                                                        prev_val, value)
                    else:
                        batch_dict[field_mapping[key]] = value
                elif key in ['invoice_date', 'dc_date']:
                    if getattr(model_obj, field_mapping[key]):
                        prev_val = datetime.datetime.strftime(getattr(model_obj, field_mapping[key]), '%m/%d/%Y')
                        if value != prev_val and value:
                            setattr(model_obj, field_mapping[key],
                                    datetime.datetime.strptime(value, '%m/%d/%Y'))
                            model_obj.save()
                            create_update_table_history(user, model_obj.id, model_name, field_mapping[key],
                                                        prev_val, value)
                        elif not value:
                            setattr(model_obj, field_mapping[key], None)
                            model_obj.save()
                            create_update_table_history(user, model_obj.id, model_name, field_mapping[key], prev_val, value)
                    elif value:
                        setattr(model_obj, field_mapping[key], datetime.datetime.strptime(value, '%m/%d/%Y'))
                        model_obj.save()
                        create_update_table_history(user, model_obj.id, model_name, field_mapping[key], '', value)
                elif key in ['invoice_number', 'dc_number']:
                    prev_val = getattr(model_obj, field_mapping[key])
                    if prev_val != value:
                        setattr(model_obj, field_mapping[key], value)
                        model_obj.save()
                        create_update_table_history(user, model_obj.id, model_name, field_mapping[key],
                                                    prev_val, value)
            if batch_dict and not model_obj.batch_detail:
                batch_dict['transact_id'] = model_obj.id
                batch_dict['transact_type'] = 'seller_po_summary'
                batch_obj = create_update_batch_data(batch_dict)
                model_obj.batch_detail_id = batch_obj.id
                model_obj.save()
        return HttpResponse("Success")
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Update GRN failed for params " + str(myDict) + " and error statement is " + str(e))
        return HttpResponse("Update GRN Failed")
