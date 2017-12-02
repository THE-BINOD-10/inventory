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
        results = OpenPO.objects.exclude(status = 0).values('supplier_id', 'supplier__name', 'order_type').distinct().annotate(total=Sum('order_quantity')).\
                                 filter(Q(supplier__id__icontains = search_term ) | Q( supplier__name__icontains = search_term ) |
                                        Q(total__icontains = search_term ), sku__user=user.id, **search_params).order_by(order_data)

    elif order_term:
        results = OpenPO.objects.exclude(status = 0).values('supplier_id', 'supplier__name', 'order_type').distinct().annotate(total=Sum('order_quantity')).\
                                 filter(sku__user=user.id, **search_params).order_by(order_data)
    else:
        results = OpenPO.objects.exclude(status = 0).values('supplier_id', 'supplier__name', 'order_type').distinct().annotate(total=Sum('order_quantity')).\
                                 filter(sku__user=user.id, **search_params)

    temp_data['recordsTotal'] = results.count()
    temp_data['recordsFiltered'] = results.count()

    count = 0
    status_dict = PO_ORDER_TYPES
    for result in results[start_index: stop_index]:
        order_type = status_dict[result['order_type']]
        #if order_type in PO_RECEIPT_TYPES.keys():
        #    order_type = PO_RECEIPT_TYPES.get(order_type, '')
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (result['supplier_id'], result['supplier__name'])
        temp_data['aaData'].append(OrderedDict(( ( '', checkbox), ('Supplier ID', result['supplier_id']),
                                                 ('Supplier Name', result['supplier__name']), ('Total Quantity', result['total']),
                                                 ('Order Type', order_type), ('id', count),
                                                 ('DT_RowClass', 'results') )))
        count += 1

@csrf_exempt
def get_raised_stock_transfer(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters=''):
    lis = ['warehouse__username', 'total']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if order_term:
        master_data = OpenST.objects.filter(sku__user=user.id, status=1).values('warehouse__username').\
                                     annotate(total=Sum('order_quantity')).order_by(order_data).distinct()
    if search_term:
        master_data = OpenST.objects.filter(Q(warehouse__username__icontains=search_term) | Q(order_quantity__icontains=search_term),
                                        sku__user=user.id, status=1).values('warehouse__username').\
                                        annotate(total=Sum('order_quantity')).order_by(order_data).distinct()
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append({'Warehouse Name': data['warehouse__username'], 'Total Quantity': data['total'], 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'id': data['warehouse__username']}})


@csrf_exempt
def get_confirmed_po(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['PO Number', 'Order Date', 'Supplier ID', 'Supplier Name', 'Order Type', 'Receive Status']
    data_list = []
    data = []
    supplier_data = {}
    col_num1 = 0
    if search_term:
        creation_search = search_term.replace('(', '\(')
        results = PurchaseOrder.objects.filter(open_po__sku_id__in=sku_master_ids).filter(Q(open_po__supplier_id__id = search_term) |
                                                Q(open_po__supplier__name__icontains = search_term)
                                               |Q( order_id__icontains = search_term ) | Q(creation_date__regex=creation_search),
                                              open_po__sku__user=user.id, received_quantity__lt=F('open_po__order_quantity')).\
                                        exclude(status__in=['location-assigned','confirmed-putaway']).\
                                        values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__open_po__isnull=True).exclude(po__status__in=['location-assigned',
                                                        'confirmed-putaway', 'stock-transfer']).filter(open_st__sku_id__in=sku_master_ids).\
                                                filter(Q(open_st__warehouse__id__icontains = search_term) |
                                                       Q(open_st__warehouse__username__icontains = search_term) |
                                                       Q(po__order_id__icontains = search_term ) | Q(po__creation_date__regex=creation_search),
                                                       open_st__sku__user=user.id,
                                                       po__received_quantity__lt=F('open_st__order_quantity')).\
                                                values_list('po__order_id', flat=True).distinct()
        rw_results = RWPurchase.objects.exclude(purchase_order__open_po__isnull=True).exclude(purchase_order__status__in=['location-assigned',
                                                'confirmed-putaway', 'stock-transfer']).filter(rwo__job_order__product_code_id__in=sku_master_ids).\
                                                filter(Q(rwo__vendor__id__icontains = search_term) |
                                                       Q(rwo__vendor__name__icontains = search_term) |
                                                       Q(purchase_order__creation_date__regex=creation_search) |
                                                       Q(purchase_order__order_id__icontains = search_term ), rwo__vendor__user=user.id,
                                                       purchase_order__received_quantity__lt=F('rwo__job_order__product_quantity')).\
                                                values_list('purchase_order__order_id', flat=True).\
                                                distinct()
        results = list(chain(results, stock_results, rw_results))
        results.sort()

    elif order_term:
        results = PurchaseOrder.objects.filter(open_po__sku_id__in=sku_master_ids).filter(open_po__sku__user = user.id, received_quantity__lt=F('open_po__order_quantity')).\
                                        exclude(status__in=['location-assigned', 'confirmed-putaway']).values_list('order_id',
                                                flat=True).distinct()

        stock_results = STPurchaseOrder.objects.filter(open_st__sku_id__in=sku_master_ids).exclude(po__status__in=['location-assigned', 'confirmed-putaway', 'stock-transfer']).\
                                                filter(po__open_po__isnull=True, open_st__sku__user = user.id,
                                                       po__received_quantity__lt=F('open_st__order_quantity')).\
                                                values_list('po__order_id', flat=True).distinct()
        rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['location-assigned',
                                                'confirmed-putaway', 'stock-transfer']).filter(rwo__job_order__product_code_id__in=sku_master_ids).\
                                        filter(rwo__vendor__user = user.id, purchase_order__open_po__isnull=True,
                                               purchase_order__received_quantity__lt=F('rwo__job_order__product_quantity')).\
                                        values_list('purchase_order__order_id', flat=True).distinct()
        results = list(set(list(chain(results, stock_results, rw_results))))

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
            po_ids = PurchaseOrder.objects.filter(Q(order_id__icontains = col_val) | Q(creation_date__regex = col_val),
                                                  open_po__sku__user = user.id, received_quantity__lt=F('open_po__order_quantity')).\
                                           exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                           values_list('id', flat=True)
            stock_results = STPurchaseOrder.objects.exclude(po__open_po__isnull=True).exclude(po__status__in=['location-assigned',
                                                            'confirmed-putaway', 'stock-transfer']).\
                                                    filter(Q(po__order_id__icontains = col_val) | Q(creation_date__regex = col_val),
                                                           open_st__sku__user=user.id,
                                                           po__received_quantity__lt=F('open_st__order_quantity')).\
                                                    values_list('po_id', flat=True).distinct()
            rw_results = RWPurchase.objects.exclude(purchase_order__open_po__isnull=True).\
                                            exclude(purchase_order__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                            filter(Q(purchase_order__order_id__icontains = col_val) | Q(creation_date__regex = col_val),
                                                   rwo__vendor__user = user.id,
                                                   purchase_order__received_quantity__lt=F('rwo__job_order__product_quantity')).\
                                            values_list('purchase_order_id', flat=True).distinct()
            search_params['id__in'] = list(chain(po_ids, stock_results, rw_results))
            search_params1['po_id__in'] = search_params['id__in']
    if filters['search_1']:
        search_params['creation_date__regex']  = filters['search_1']
    if filters['search_2']:
        search_params['open_po__supplier__id__icontains'] = filters['search_2']
        search_params1['open_st__warehouse__id__icontains'] = filters['search_2']
        search_params2['rwo__vendor__id__icontains'] = filters['search_2']
    if filters['search_3']:
        search_params['open_po__supplier__name__icontains'] = filters['search_3']
        search_params1['open_st__warehouse__username__icontains'] = filters['search_3']
        search_params2['rwo__vendor__name__icontains'] = filters['search_3']
    if search_params:
        search_params['open_po__sku__user'] = user.id
        search_params1['open_st__sku__user'] = user.id
        results = PurchaseOrder.objects.filter(**search_params).exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                        values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__open_po__isnull=True).exclude(po__status__in=['location-assigned',
                                                        'confirmed-putaway', 'stock-transfer']).\
                                                filter(po__received_quantity__lt=F('open_st__order_quantity'), **search_params1).values_list('po__order_id', flat=True).distinct()
        results = list(chain(results, stock_results))


    for result in results:
        suppliers = PurchaseOrder.objects.filter(order_id=result, open_po__sku__user = user.id).exclude(status__in=['location-assigned', 'confirmed-putaway'])
        if not suppliers:
            st_order_ids = STPurchaseOrder.objects.filter(po__order_id=result, open_st__sku__user = user.id).values_list('po_id', flat=True)
            suppliers = PurchaseOrder.objects.filter(id__in=st_order_ids)
        if not suppliers:
            rw_ids = RWPurchase.objects.filter(purchase_order__order_id=result, rwo__vendor__user=user.id).\
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
        if RWPurchase.objects.filter(purchase_order_id=supplier.id):
            order_type = 'Returnable Work Order'
        elif STPurchaseOrder.objects.filter(po_id=supplier.id):
            order_type = 'Stock Transfer'
        if supplier.received_quantity and not float(order_data['order_quantity']) == float(supplier.received_quantity):
            receive_status = 'Partially Receive'
        po_reference = '%s%s_%s' % (supplier.prefix, str(supplier.creation_date).split(' ')[0].replace('-', ''), supplier.order_id)
        _date = get_local_date(user, supplier.po_date, True)
        _date = _date.strftime("%d %b, %Y")
        data_list.append({'DT_RowId': supplier.order_id, 'PO Number': po_reference,
                          'Order Date': _date,
                          'Supplier ID': order_data['supplier_id'], 'Supplier Name': order_data['supplier_name'], 'Order Type': order_type,
                          'Receive Status': receive_status})
    sort_col = lis[col_num]

    if order_term == 'asc':
        data_list = sorted(data_list, key=itemgetter(sort_col))
    else:
        data_list = sorted(data_list, key=itemgetter(sort_col), reverse=True)
    temp_data['aaData'] = list(chain(temp_data['aaData'], data_list[start_index:stop_index]))

@csrf_exempt
def get_quality_check_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['Purchase Order ID', 'Supplier ID', 'Supplier Name', 'Order Type', 'Total Quantity']
    all_data = OrderedDict()

    qc_list = ['purchase_order__order_id', 'purchase_order__open_po__supplier__id', 'purchase_order__open_po__supplier__name',
               'id', 'putaway_quantity']
    st_list = ['po__order_id', 'open_st__warehouse__id', 'open_st__warehouse__username', 'id', 'id']
    rw_list = ['purchase_order__order_id', 'rwo__vendor__id', 'rwo__vendor__name', 'id', 'id']

    del filters['search_3']
    del filters['search_4']
    qc_filters = get_filtered_params(filters, qc_list)
    st_filters = get_filtered_params(filters, st_list)
    rw_filters = get_filtered_params(filters, rw_list)

    if search_term:
        results = QualityCheck.objects.filter(purchase_order__open_po__sku_id__in=sku_master_ids).\
                                       filter(Q(purchase_order__order_id__icontains=search_term) |
                                              Q(purchase_order__open_po__supplier__id__icontains=search_term) |
                                              Q(purchase_order__open_po__supplier__name__icontains=search_term),
                                              purchase_order__open_po__sku__user = user.id, status='qc_pending', putaway_quantity__gt=0,
                                              **qc_filters)
        stock_results = STPurchaseOrder.objects.filter(open_st__sku_id__in=sku_master_ids).\
                                                exclude(po__status__in=['confirmed-putaway', 'stock-transfer']).\
                                                filter(Q(open_st__warehouse__username__icontains = search_term) |
                                                       Q(po__order_id__icontains = search_term ), open_st__sku__user=user.id, **st_filters).\
                                                 values_list('po_id', flat=True)
        rw_results = RWPurchase.objects.filter(rwo__job_order__product_code_id__in=sku_master_ids).\
                                        exclude(purchase_order__status__in=['confirmed-putaway', 'stock-transfer']).\
                                        filter(Q(rwo__vendor__name__icontains = search_term) | Q(rwo__vendor__id__icontains = search_term) |
                                               Q(purchase_order__order_id__icontains = search_term ), rwo__vendor__user=user.id, **rw_filters).\
                                        values_list('purchase_order_id', flat=True)
        stock_results = list(chain(stock_results, rw_results))
        result_ids = results.values_list('id', flat=True)
        qc_results = QualityCheck.objects.exclude(id__in=result_ids).filter(purchase_order_id__in=stock_results, status='qc_pending',
                                                  putaway_quantity__gt=0, po_location__location__zone__user = user.id)

        results = list(chain(results, qc_results))
    else:
        stock_results = STPurchaseOrder.objects.filter(open_st__sku_id__in=sku_master_ids).exclude(po__status__in=['confirmed-putaway',
                                                       'stock-transfer']).filter(open_st__sku__user=user.id, **st_filters).\
                                                values_list('po_id', flat=True)
        rw_results = RWPurchase.objects.filter(rwo__job_order__product_code_id__in=sku_master_ids).\
                                        exclude(purchase_order__status__in=['confirmed-putaway', 'stock-transfer']).\
                                        filter(rwo__vendor__user=user.id, **rw_filters).\
                                        values_list('purchase_order_id', flat=True)
        stock_results = list(chain(stock_results, rw_results))
        qc_results = QualityCheck.objects.filter(Q(purchase_order__open_po__sku_id__in=sku_master_ids) | Q(purchase_order_id__in=stock_results),
                                                 status='qc_pending', putaway_quantity__gt=0, po_location__location__zone__user = user.id)
        qc_result_ids = qc_results.values_list('id', flat=True)
        results = QualityCheck.objects.filter(Q(purchase_order__open_po__sku_id__in=sku_master_ids) | Q(purchase_order_id__in=stock_results)).\
                                       filter(status='qc_pending', putaway_quantity__gt=0, po_location__location__zone__user = user.id,
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
        order = PurchaseOrder.objects.filter(order_id=key[0], open_po__sku__user=user.id, open_po__sku_id__in=sku_master_ids)
        if not order:
            order = STPurchaseOrder.objects.filter(po_id__order_id=key[0], open_st__sku__user=user.id, open_st__sku_id__in=sku_master_ids)
            if order:
                order = [order[0].po]
            else:
                order = [RWPurchase.objects.filter(purchase_order__order_id=key[0], rwo__vendor__user=user.id,
                                                   rwo__job_order__product_code_id__in=sku_master_ids)[0].purchase_order]
        order = order[0]
        order_type = 'Purchase Order'
        if RWPurchase.objects.filter(purchase_order_id=order.id):
            order_type = 'Returnable Work Order'
        elif STPurchaseOrder.objects.filter(po_id=order.id):
            order_type = 'Stock Transfer'
        po_reference = '%s%s_%s' % (order.prefix,str(order.creation_date).split(' ')[0].replace('-', ''), order.order_id)
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
    if search_term:
        results = PurchaseOrder.objects.filter(open_po__sku_id__in=sku_master_ids).filter(Q(open_po__supplier__name__icontains=search_term) |
                                               Q(open_po__supplier__id__icontains=search_term) | Q(order_id__icontains=search_term) |
                                               Q(creation_date__regex=search_term), open_po__sku__user = user.id).exclude(status__in=['',
                                               'confirmed-putaway']).values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.filter(open_st__sku_id__in=sku_master_ids).exclude(po__status__in=['','confirmed-putaway',
                                                'stock-transfer']).filter(Q(open_st__warehouse__id__icontains = search_term) |
                                                       Q(open_st__warehouse__username__icontains = search_term) |
                                                       Q(po__order_id__icontains = search_term) | Q(po__creation_date__regex=search_term),
                                                       open_st__sku__user=user.id).\
                                                 values_list('po__order_id', flat=True).distinct()
        rw_results = RWPurchase.objects.filter(rwo__job_order__product_code_id__in=sku_master_ids).exclude(purchase_order__status__in=['',
                                               'confirmed-putaway', 'stock-transfer']).filter(Q(rwo__vendor__id__icontains = search_term) |
                                                       Q(rwo__vendor__name__icontains = search_term) |
                                                       Q(purchase_order__order_id__icontains = search_term) |
                                                       Q(purchase_order__creation_date__regex=search_term),
                                                       rwo__vendor__user=user.id).\
                                                 values_list('purchase_order__order_id', flat=True).distinct()
        results = list(chain(results, stock_results, rw_results))
    elif order_term:
        results = PurchaseOrder.objects.filter(open_po__sku__user = user.id, open_po__sku_id__in=sku_master_ids).exclude(status__in=['',
                                               'confirmed-putaway']).values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['','confirmed-putaway', 'stock-transfer']).\
                                                filter(open_st__sku__user = user.id, open_st__sku_id__in=sku_master_ids).\
                                                values_list('po__order_id', flat=True).distinct()
        rw_results = RWPurchase.objects.filter(rwo__job_order__product_code_id__in=sku_master_ids).exclude(purchase_order__status__in=['',
                                        'confirmed-putaway', 'stock-transfer']).\
                                        filter(rwo__vendor__user = user.id).values_list('purchase_order__order_id', flat=True)
        results = list(chain(results, stock_results, rw_results))
    else:
        results = PurchaseOrder.objects.filter(open_po__sku__user = user.id, open_po__sku_id__in=sku_master_ids).exclude(status__in=['',
                                               'confirmed-putaway']).values('order_id').distinct()
    data = []
    temp = []
    for result in results:
        suppliers = PurchaseOrder.objects.filter(order_id=result, open_po__sku__user = user.id, open_po__sku_id__in=sku_master_ids).\
                                          exclude(status__in=['', 'confirmed-putaway'])
        if not suppliers:
            st_order_ids = STPurchaseOrder.objects.filter(po__order_id=result, open_st__sku__user = user.id,
                                                          open_st__sku_id__in=sku_master_ids).values_list('po_id', flat=True)
            suppliers = PurchaseOrder.objects.filter(id__in=st_order_ids)
        if not suppliers:
            rw_ids = RWPurchase.objects.filter(purchase_order__order_id=result, rwo__vendor__user = user.id,
                                               rwo__job_order__product_code_id__in=sku_master_ids).values_list('purchase_order_id', flat=True)
            suppliers = PurchaseOrder.objects.filter(id__in=rw_ids)
        for supplier in suppliers:
            po_loc = POLocation.objects.filter(purchase_order_id=supplier.id, status=1, location__zone__user = user.id, quantity__gt=0)
            if po_loc and result not in temp:
                temp.append(result)
                data.append(supplier)

    temp_data['recordsTotal'] = len(data)
    temp_data['recordsFiltered'] = len(data)
    for supplier in data:
        order_data = get_purchase_order_data(supplier)
        order_type = 'Purchase Order'
        if RWPurchase.objects.filter(purchase_order_id=supplier.id):
            order_type = 'Returnable Work Order'
        elif STPurchaseOrder.objects.filter(po_id=supplier.id):
            order_type = 'Stock Transfer'
        po_reference = '%s%s_%s' % (supplier.prefix, str(supplier.creation_date).split(' ')[0].replace('-', ''), supplier.order_id)
        temp_data['aaData'].append({'DT_RowId': supplier.order_id, 'Supplier ID': order_data['supplier_id'],
                                    'Supplier Name': order_data['supplier_name'], 'Order Type': order_type,
                                    ' Order ID': supplier.order_id, 'Order Date': get_local_date(request.user, supplier.creation_date),
                                    'DT_RowClass': 'results', 'PO Number': po_reference,
                                    'DT_RowAttr': {'data-id': supplier.order_id}})

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
        master_data = ReturnsLocation.objects.filter(returns__sku_id__in=sku_master_ids).filter(Q(returns__return_id__icontains=search_term) |
                                                     Q(returns__sku__sku_desc__icontains=search_term) |
                                                       Q(returns__sku__wms_code__icontains=search_term) | Q(quantity__icontains=search_term),
                                                       returns__sku__user = user.id , status=1, quantity__gt=0)
    elif order_term:
        col_num = col_num - 1
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = ReturnsLocation.objects.filter(returns__sku__user = user.id, status=1, quantity__gt=0,
                                                     returns__sku_id__in=sku_master_ids).order_by(order_data)
    else:
        master_data = ReturnsLocation.objects.filter(returns__sku__user = user.id, status=1, quantity__gt=0,
                                                     returns__sku_id__in=sku_master_ids).order_by('returns__return_date')
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
                                    'Product Description': data.returns.sku.sku_desc, 'Zone': zone, 'Location': location,
                                    'Quantity': quantity, 'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.id}, 'id':count})
        count = count+1

@csrf_exempt
def get_order_returns(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['return_id', 'order_id', 'return_date', 'order__sku__sku_code', 'order__sku__sku_desc',  'order__marketplace', 'quantity']
    if search_term:
        order_id_search = ''.join(re.findall('\d+', search_term))
        master_data = OrderReturns.objects.filter(Q(return_id__icontains=search_term) | Q(quantity__icontains=search_term) |
                                                  Q(order__sku__sku_code=search_term) | Q(order__sku__sku_desc__icontains=search_term) |
                                                  Q(order__order_id__icontains=order_id_search), status=1, order__user=user.id, quantity__gt=0)
    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            master_data = OrderReturns.objects.filter(order__user=user.id, status=1, quantity__gt=0).order_by(lis[col_num])
        else:
            master_data = OrderReturns.objects.filter(order__user=user.id, status=1, quantity__gt=0).order_by('-%s' % lis[col_num])
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
def get_seller_invoice_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    lis = ['seller_po__open_po_id', 'seller_po__open_po_id', 'seller_po__seller__name', 'creation_date', 'seller_po__seller_quantity', 'quantity', 'id']
    seller_po_summary = SellerPOSummary.objects.filter(seller_po__seller__user=user.id).exclude(seller_po__receipt_type='Hosted Warehouse')
    if search_term:
        order_id_search = ''
        if '_' in search_term:
           order_id_search = ''.join(re.findall('\d+', search_term.split('_')[-1]))
        open_po_ids = []
        if order_id_search:
            open_po_ids = PurchaseOrder.objects.filter(open_po__sku__user=user.id, order_id__icontains=order_id_search).\
                                                values_list('open_po__id', flat=True)
        master_data = seller_po_summary.filter(Q(quantity__icontains=search_term) |
                                                     Q(seller_po__seller__name__icontains=search_term) |
                                                     Q(seller_po__seller_quantity__icontains=search_term) |
                                                     Q(seller_po__open_po_id__in=open_po_ids),
                                                     seller_po__seller__user=user.id).values('purchase_order__order_id',
                                                     'receipt_number', 'seller_po__seller__name').distinct().\
                                              annotate(total_quantity=Sum('quantity'))
    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            master_data = seller_po_summary.order_by(lis[col_num]).values('purchase_order__order_id', 'seller_po__seller__name', 'receipt_number').distinct().annotate(total_quantity=Sum('quantity'))
        else:
            master_data = seller_po_summary.order_by('-%s' % lis[col_num]).values('purchase_order__order_id', 'seller_po__seller__name', 'receipt_number').distinct().annotate(total_quantity=Sum('quantity'))
    else:
        master_data = seller_po_summary.order_by('-%s' % lis[col_num]).values('purchase_order__order_id', 'seller_po__seller__name', 'receipt_number').distinct().annotate(total_quantity=Sum('quantity'))

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    po_summaries = seller_po_summary
    for data in master_data[start_index:stop_index]:
        summary = po_summaries.filter(purchase_order__order_id=data['purchase_order__order_id'], seller_po__seller__name=data['seller_po__seller__name'])[0]
        purchase_order = PurchaseOrder.objects.get(open_po_id=summary.seller_po.open_po_id)
        po_number = '%s%s_%s' % (purchase_order.prefix, str(purchase_order.creation_date).split(' ')[0].replace('-', ''), purchase_order.order_id)
        temp_data['aaData'].append(OrderedDict(( ('PO Number', po_number), ('Seller Name', summary.seller_po.seller.name),
                                    ('Receipt Date', get_local_date(user, summary.creation_date)),
                                    ('Order Quantity', summary.seller_po.seller_quantity),
                                    ('Received Quantity', data['total_quantity']),
                                    ('Invoice Number', ''), ('id', str(data['purchase_order__order_id']) +\
                                     ":" + str(data['receipt_number']) + ":" + data['seller_po__seller__name'])
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
    #if order_type_val in PO_RECEIPT_TYPES.values():
    #    rev_receipt_types = dict(zip(PO_RECEIPT_TYPES.values(), PO_RECEIPT_TYPES.keys()))
    #    order_type_val = rev_receipt_types.get(order_type_val, '')
    order_type = rev_order_types.get(order_type_val, '')
    record = OpenPO.objects.filter(Q(supplier_id=generated_id, status='Manual') | Q(supplier_id=generated_id, status='Automated'),
                                     sku__user = user.id, order_type=order_type, sku_id__in=sku_master_ids)

    total_data = []
    status_dict = PO_ORDER_TYPES
    ser_data = []
    #ser_data = json.loads(serializers.serialize("json", record, indent=3, use_natural_foreign_keys=True, fields = ('supplier_code', 'sku', 'order_quantity', 'price', 'remarks', 'measurement_unit')))
    for rec in record:
        seller = ''
        seller_po = SellerPO.objects.filter(open_po__sku__user=user.id, open_po_id=rec.id)
        if seller_po:
            for sell_po in seller_po:
                if not receipt_type:
                    receipt_type = sell_po.receipt_type
                ser_data.append({'fields': {'sku': {'wms_code': rec.sku.sku_code}, 'description': rec.sku.sku_desc,
                                 'order_quantity': sell_po.seller_quantity,
                                 'price': rec.price, 'supplier_code': rec.supplier_code, 'measurement_unit': rec.measurement_unit,
                                 'remarks': rec.remarks, 'dedicated_seller': str(sell_po.seller.seller_id) + ':' + sell_po.seller.name,
                                 'sgst_tax': rec.sgst_tax, 'cgst_tax': rec.cgst_tax, 'igst_tax': rec.igst_tax, 'utgst_tax': rec.utgst_tax},
                                 'pk': rec.id, 'seller_po_id': sell_po.id})
        else:
            ser_data.append({'fields': {'sku': {'wms_code': rec.sku.sku_code}, 'description': rec.sku.sku_desc,
                             'order_quantity': rec.order_quantity,
                             'price': rec.price, 'supplier_code': rec.supplier_code, 'measurement_unit': rec.measurement_unit,
                             'remarks': rec.remarks, 'dedicated_seller': '', 'sgst_tax': rec.sgst_tax, 'cgst_tax': rec.cgst_tax,
                             'igst_tax': rec.igst_tax, 'utgst_tax': rec.utgst_tax}, 'pk': rec.id})
    vendor_id = ''
    if record[0].vendor:
        vendor_id = record[0].vendor.vendor_id
    return HttpResponse(json.dumps({'supplier_id': record[0].supplier_id, 'vendor_id': vendor_id,
                                    'Order Type': status_dict[record[0].order_type], 'po_name': record[0].po_name, 'ship_to': '',
                                    'data': ser_data, 'receipt_type': receipt_type, 'receipt_types': PO_RECEIPT_TYPES}))

@login_required
@get_admin_user
def validate_wms(request, user=''):
    myDict = dict(request.POST.iterlists())
    wms_list = ''
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
            sku_master = SKUMaster.objects.filter(Q(ean_number=myDict['wms_code'][i]) | Q(wms_code=myDict['wms_code'][i]), user=user.id)
        else:
            sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user=user.id)
        if not sku_master:
            if not wms_list:
                wms_list = 'Invalid WMS Codes are ' + myDict['wms_code'][i].upper()
            else:
                wms_list += ',' + myDict['wms_code'][i].upper()

    if not wms_list:
        wms_list = 'success'
    return HttpResponse(wms_list)

@csrf_exempt
@login_required
@get_admin_user
def modify_po_update(request, user=''):
    myDict = dict(request.POST.iterlists())
    wrong_wms = []

    all_data = get_raisepo_group_data(user, myDict)

    for key, value in all_data.iteritems():

        wms_code = key
        if not wms_code:
            continue

        data_id = value['data_id']
        if data_id:
            record = OpenPO.objects.get(id=data_id,sku__user=user.id)
            setattr(record, 'order_quantity', value['order_quantity'] )
            setattr(record, 'price', value['price'] )
            setattr(record, 'remarks', value['remarks'])
            setattr(record, 'sgst_tax', value['sgst_tax'])
            setattr(record, 'cgst_tax', value['cgst_tax'])
            setattr(record, 'igst_tax', value['igst_tax'])
            setattr(record, 'utgst_tax', value['utgst_tax'])
            record.save()
            if value['sellers']:
                for k, val in value['sellers'].iteritems():
                    if val[1]:
                        seller_po = SellerPO.objects.get(id=val[1], open_po__sku__user=user.id)
                        seller_po.seller_quantity = val[0]
                        seller_po.save()
                    else:
                        SellerPO.objects.create(seller_id=k, open_po_id=record.id, seller_quantity=val[0],
                                         creation_date=datetime.datetime.now(), status=1, receipt_type=value['receipt_type'])
            continue

        sku_id = SKUMaster.objects.filter(wms_code=wms_code.upper(),user=user.id)
        po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
        if not sku_id:
            sku_id = sku_id = SKUMaster.objects.filter(wms_code='TEMP',user=user.id)
            po_suggestions['wms_code'] = wms_code.upper()
        if not sku_id[0].wms_code == 'TEMP':
            supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=myDict['supplier_id'][0], sku__user=user.id)
            sku_mapping = {'supplier_id': value['supplier_id'], 'sku': sku_id[0], 'preference': 1, 'moq': 0,
                           'supplier_code': value['supplier_code'], 'price': value['price'], 'creation_date': datetime.datetime.now(),
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
        po_suggestions['status'] = 'Manual'
        po_suggestions['remarks'] = value['remarks']
        po_suggestions['sgst_tax'] = value['sgst_tax']
        po_suggestions['cgst_tax'] = value['cgst_tax']
        po_suggestions['igst_tax'] = value['igst_tax']
        po_suggestions['utgst_tax'] = value['utgst_tax']

        data = OpenPO(**po_suggestions)
        data.save()
        if value['sellers']:
            for seller, seller_quan in value['sellers'].iteritems():
                SellerPO.objects.create(seller_id=seller, open_po_id=data.id, seller_quantity=seller_quan[0],
                                        creation_date=datetime.datetime.now(), status=1, receipt_type=value['receipt_type'])

    status_msg="Updated Successfully"
    return HttpResponse(status_msg)

@csrf_exempt
@get_admin_user
def switches(request, user=''):
    log.info('Request params for ' + user.username + ' on ' + str(get_local_date(user, datetime.datetime.now())) + ' is ' + str(request.GET.dict()))
    try:
        toggle_data = { 'fifo_switch': 'fifo_switch',
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
                        'order_headers' : 'order_headers',
                        'detailed_invoice' : 'detailed_invoice',
                        'scan_picklist_option' : 'scan_picklist_option',
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
                        'display_remarks_mail': 'display_remarks_mail',
                        'create_seller_order': 'create_seller_order',
                        'invoice_remarks': 'invoice_remarks',
                        'show_disc_invoice': 'show_disc_invoice',
                        'serial_limit': 'serial_limit',
                        'increment_invoice': 'increment_invoice',
                        'auto_allocate_stock': 'auto_allocate_stock'
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
                misc_detail = MiscDetail(user=user_id, misc_type=toggle_field, misc_value=selection, creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now())
                misc_detail.save()
            else:
                setattr(data[0], 'misc_value', selection)
                data[0].save()
            if toggle_field == 'sku_sync' and value == 'true':
                insert_skus(user.id)
            elif toggle_field == 'increment_invoice' and value == 'true':
                InvoiceSequence.objects.get_or_create(user_id=user.id, marketplace='', defaults={'status': 1, 'prefix': '',
                                                        'creation_date': datetime.datetime.now(), 'value': 1})
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Update Configurations failed for params " + str(request.GET.dict()) + " on " +\
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

    data = MiscDetail.objects.filter(misc_type='tax_'+tax_name, user=user.id)
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
    po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).order_by('-order_id')
    if not po_data:
        po_id = 0
    else:
        po_id = po_data[0].order_id
    ids_dict = {}
    po_data = []
    total = 0
    total_qty = 0
    myDict = dict(request.POST.iterlists())
    display_remarks = get_misc_value('display_remarks_mail', user.id)
    ean_data = SKUMaster.objects.filter(wms_code__in=myDict['wms_code'],user=user.id).values_list('ean_number').exclude(ean_number=0)
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
            setattr(purchase_order, 'po_name', value['po_name'])
            setattr(purchase_order, 'supplier_code', value['supplier_code'])
            setattr(purchase_order, 'remarks', value['remarks'])
            setattr(purchase_order, 'sgst_tax', value['sgst_tax'])
            setattr(purchase_order, 'cgst_tax', value['cgst_tax'])
            setattr(purchase_order, 'igst_tax', value['igst_tax'])
            setattr(purchase_order, 'utgst_tax', value['utgst_tax'])
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
                                         creation_date=datetime.datetime.now(), status=1, receipt_type=value['receipt_type'])
        else:
            sku_id = SKUMaster.objects.filter(wms_code=key.upper(), user=user.id)
            po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
            if not sku_id:
                sku_id = SKUMaster.objects.filter(wms_code='TEMP', user=user.id)
                po_suggestions['wms_code'] = key.upper()
                po_suggestions['supplier_code'] = value['supplier_code']
                if not sku_id[0].wms_code == 'TEMP':
                    supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=value['supplier_id'], sku__user=user.id)
                    sku_mapping = {'supplier_id': value['supplier_id'], 'sku': sku_id[0], 'preference': 1, 'moq': 0,
                                   'supplier_code': value['supplier_code'], 'price': price, 'creation_date': datetime.datetime.now(),
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
            po_suggestions['order_quantity'] = float(value['order_quantity'])
            po_suggestions['price'] = float(price)
            po_suggestions['status'] = 'Manual'
            po_suggestions['remarks'] = value['remarks']
            po_suggestions['measurement_unit'] = "UNITS"
            po_suggestions['sgst_tax'] = value['sgst_tax']
            po_suggestions['cgst_tax'] = value['cgst_tax']
            po_suggestions['igst_tax'] = value['igst_tax']
            po_suggestions['utgst_tax'] = value['utgst_tax']
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
                                        creation_date=datetime.datetime.now(), status=1, receipt_type=value['receipt_type'])

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
        if not tax:
            total += amount
        else:
            total += amount + ((amount/100) * float(tax))

        total_qty += float(purchase_order.order_quantity)

        if purchase_order.sku.wms_code == 'TEMP':
            wms_code = purchase_order.wms_code
        else:
            wms_code = purchase_order.sku.wms_code

        po_temp_data = [wms_code, value['supplier_code'], purchase_order.sku.sku_desc, purchase_order.order_quantity,
                        value['measurement_unit'], purchase_order.price, amount, purchase_order.sgst_tax, purchase_order.cgst_tax,
                        purchase_order.igst_tax, purchase_order.utgst_tax]
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
    if receipt_type == 'Hosted Warehouse':
        title = 'Stock Transfer Note'
    if request.POST.get('seller_id', '') and str(request.POST.get('seller_id').split(":")[1]).lower() == 'shproc':
        company_name = 'SHPROC Procurement Pvt. Ltd.'

    table_headers = ['WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Measurement Type', 'Unit Price', 'Amount',
                     'SGST(%)' , 'CGST(%)', 'IGST(%)', 'UTGST(%)']
    if ean_flag:
        table_headers.insert(1, 'EAN Number')
    if display_remarks == 'true':
        table_headers.append('Remarks')

    data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id, 'telephone': str(telephone),
                 'name': name, 'order_date': order_date, 'total': total, 'po_reference': po_reference, 'company_name': company_name,
                 'location': profile.location, 'vendor_name': vendor_name, 'vendor_address': vendor_address,
                 'vendor_telephone': vendor_telephone, 'total_qty': total_qty, 'receipt_type': receipt_type, 'title': title,
                 'gstin_no': gstin_no}
    t = loader.get_template('templates/toggle/po_download.html')
    rendered = t.render(data_dict)
    if get_misc_value('raise_po', user.id) == 'true':
        write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, telephone, po_data, str(order_date).split(' ')[0],ean_flag=ean_flag)

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
    data = SupplierMaster.objects.filter(Q(id__icontains = data_id) | Q(name__icontains = data_id), user=user.id)
    suppliers = []
    if data:
        for supplier in data:
            suppliers.append(str(supplier.id)+":"+str(supplier.name))
    return HttpResponse(json.dumps(suppliers))

@csrf_exempt
@login_required
@get_admin_user
def search_vendor(request, user=''):
    data_id = request.GET['q']
    data = VendorMaster.objects.filter(Q(vendor_id__icontains = data_id) | Q(name__icontains = data_id), user=user.id)
    vendors = []
    if data:
        for vendor in data:
            vendors.append(str(vendor.vendor_id)+":"+str(vendor.name))
    return HttpResponse(json.dumps(vendors))

@csrf_exempt
@login_required
@get_admin_user
def get_mapping_values(request, user=''):
    wms_code = request.GET['wms_code']
    supplier_id = request.GET['supplier_id']
    if wms_code.isdigit():
        ean_number = wms_code
        sku_supplier = SKUSupplier.objects.filter(Q(sku__ean_number=wms_code) | Q(sku__wms_code=wms_code), supplier_id=supplier_id, sku__user=user.id)
    else:
        ean_number = 0
        sku_supplier = SKUSupplier.objects.filter(sku__wms_code=wms_code, supplier_id=supplier_id, sku__user=user.id)
    data = {}
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
        max_sup_id = SupplierMaster.objects.count()
        run_iterator = 1
        while run_iterator:
            supplier_obj = SupplierMaster.objects.filter(id=max_sup_id)
            if not supplier_obj:
                supplier_master, created = SupplierMaster.objects.get_or_create(id=max_sup_id, user=user.id, name=seller_master.name,
                                                     email_id=seller_master.email_id,
                                                     phone_number=seller_master.phone_number, address=seller_master.address,
                                                     tin_number=seller_master.tin_number, status=1)
                seller_master.supplier_id = supplier_master.id
                seller_master.save()
                run_iterator = 0
                supplier_id = supplier_master.id
            else:
                max_sup_id += 1
    return supplier_id

def get_raisepo_group_data(user, myDict):
    all_data = OrderedDict()
    for i in range(0,len(myDict['wms_code'])):
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
        order_type = 'SR'
        sgst_tax = 0
        cgst_tax = 0
        igst_tax = 0
        utgst_tax = 0
        if 'remarks' in myDict.keys():
            remarks = myDict['remarks'][i]
        if 'supplier_code' in myDict.keys():
            supplier_code = myDict['supplier_code'][i]
        if 'po_name' in myDict.keys():
            po_name = myDict['po_name'][0]
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
        if 'sgst_tax' in myDict.keys():
            if myDict['sgst_tax'][i]:
                sgst_tax = float(myDict['sgst_tax'][i])
        if 'cgst_tax' in myDict.keys():
            if myDict['cgst_tax'][i]:
                cgst_tax = float(myDict['cgst_tax'][i])
        if 'igst_tax' in myDict.keys():
            if myDict['igst_tax'][i]:
                igst_tax = float(myDict['igst_tax'][i])
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
                                   'order_type': order_type, 'sgst_tax': sgst_tax, 'cgst_tax': cgst_tax, 'igst_tax': igst_tax,
                                   'utgst_tax': utgst_tax})
        all_data[cond]['order_quantity'] += float(myDict['order_quantity'][i])
        if 'dedicated_seller' in myDict:
            seller = myDict['dedicated_seller'][i]
            if ':' in seller:
                seller = seller.split(':')[0]
            seller_master = SellerMaster.objects.get(user=user.id, seller_id=seller)
            if not seller in all_data[cond]['sellers'].keys():
                all_data[cond]['sellers'][seller_master.id] = [float(myDict['order_quantity'][i]), seller_po_id]
            else:
                all_data[cond]['sellers'][seller_master.id][0] += float(myDict['order_quantity'][i])
    return all_data


@csrf_exempt
@login_required
@get_admin_user
def add_po(request, user=''):
    status = 'Failed to Add PO'
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

        #sku_id = SKUMaster.objects.filter(wms_code=wms_code.upper(),user=user.id)
        if not sku_id:
            status = 'Invalid WMS CODE'
            return HttpResponse(status)

        po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)

        supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=value['supplier_id'],sku__user=user.id)
        sku_mapping = {'supplier_id': value['supplier_id'], 'sku': sku_id[0], 'preference': 1, 'moq': 0,
                       'supplier_code': value['supplier_code'], 'price': value['price'], 'creation_date': datetime.datetime.now(),
                       'updation_date': datetime.datetime.now()}

        if supplier_mapping:
            supplier_mapping = supplier_mapping[0]
            if sku_mapping['supplier_code'] and supplier_mapping.supplier_code != sku_mapping['supplier_code']:
                supplier_mapping.supplier_code = sku_mapping['supplier_code']
                supplier_mapping.save()
        else:
            new_mapping = SKUSupplier(**sku_mapping)
            new_mapping.save()

        suggestions_data = OpenPO.objects.exclude(status__exact='0').filter(sku_id=sku_id, supplier_id = value['supplier_id'],
                                                  order_quantity = value['order_quantity'],sku__user=user.id)
        if not suggestions_data:
            po_suggestions['sku_id'] = sku_id[0].id
            po_suggestions['supplier_id'] = value['supplier_id']
            try:
                po_suggestions['order_quantity'] = float(value['order_quantity'])
            except:
                po_suggestions['order_quantity'] = 0
            po_suggestions['price'] = float(value['price'])
            po_suggestions['status'] = 'Manual'
            po_suggestions['po_name'] = value['po_name']
            po_suggestions['remarks'] = value['remarks']
            po_suggestions['sgst_tax'] = value['sgst_tax']
            po_suggestions['cgst_tax'] = value['cgst_tax']
            po_suggestions['igst_tax'] = value['igst_tax']
            po_suggestions['utgst_tax'] = value['utgst_tax']
            po_suggestions['order_type'] = value['order_type']
            if value.get('vendor_id', ''):
                vendor_master = VendorMaster.objects.get(vendor_id=value['vendor_id'], user=user.id)
                po_suggestions['vendor_id'] = vendor_master.id
                po_suggestions['order_type'] = 'VR'

            data = OpenPO(**po_suggestions)
            data.save()
            if value['sellers']:
                for seller, seller_quan in value['sellers'].iteritems():
                    SellerPO.objects.create(seller_id=seller, open_po_id=data.id, seller_quantity=seller_quan[0],
                                            creation_date=datetime.datetime.now(), status=1, receipt_type=value['receipt_type'])
            status = 'Added Successfully'
        else:
            status = 'Entry Already Exists'

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
    wmscode  = request.GET['wms_code']
    quantity = request.GET['quantity']
    reason = request.GET['reason']
    loc = request.GET['location']
    status = adjust_location_stock(cycle_id, wmscode, loc, quantity, reason, user)
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
            open_po = OpenPO.objects.get(id=seller_po.open_po_id, sku__user = user.id)
            open_po.order_quantity = float(open_po.order_quantity) - float(seller_po.seller_quantity)
            open_po.save()
            if open_po.order_quantity <= 0:
                open_po.delete()
            seller_po.delete()
        else:
            purchase_order = OpenPO.objects.filter(id=value, sku__user = user.id).delete()

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
    purchase_orders = PurchaseOrder.objects.filter(order_id=order_id, open_po__sku__user = user.id, open_po__sku_id__in=sku_master_ids,
                                                   received_quantity__lt=F('open_po__order_quantity')).exclude(status='location-assigned')
    if not purchase_orders:
        st_orders = STPurchaseOrder.objects.filter(po__order_id=order_id, open_st__sku__user = user.id, open_st__sku_id__in=sku_master_ids).\
                                exclude(po__status__in=['location-assigned', 'stock-transfer']).values_list('po_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=st_orders)
    if not purchase_orders:
        rw_orders = RWPurchase.objects.filter(purchase_order__order_id=order_id, rwo__vendor__user=user.id,
                                              rwo__job_order__product_code_id__in=sku_master_ids).\
                                       exclude(purchase_order__status__in=['location-assigned', 'stock-transfer']).\
                                       values_list('purchase_order_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=rw_orders)
    po_reference = '%s%s_%s' % (purchase_orders[0].prefix, str(purchase_orders[0].creation_date).split(' ')[0].replace('-', ''), order_id)
    orders = []
    for order in purchase_orders:
        order_data = get_purchase_order_data(order)
        po_quantity = float(order_data['order_quantity']) - float(order.received_quantity)
        sku_details = json.loads(serializers.serialize("json", [order_data['sku']], indent=1, use_natural_foreign_keys=True, fields = ('sku_code', 'wms_code', 'sku_desc', 'color', 'sku_class', 'sku_brand', 'sku_category', 'image_url', 'load_unit_handle')))
        if po_quantity > 0:
            sku_extra_data, product_images, order_ids = get_order_json_data(user, mapping_id=order.id, mapping_type='PO',
                                                                         sku_id=order_data['sku_id'], order_ids=order_ids)
            orders.append([{'order_id': order.id, 'wms_code': order_data['wms_code'],
                            'po_quantity': float(order_data['order_quantity']) - float(order.received_quantity),
                            'name': str(order.order_id) + '-' + str(re.sub(r'[^\x00-\x7F]+','', order_data['wms_code'])),
                            'value': get_decimal_limit(user.id, order.saved_quantity),
                            'receive_quantity': get_decimal_limit(user.id, order.received_quantity), 'price': order_data['price'],
                            'temp_wms': order_data['temp_wms'],'order_type': order_data['order_type'], 'unit': order_data['unit'],
                            'dis': True,
                            'sku_extra_data': sku_extra_data, 'product_images': product_images, 'sku_details': sku_details}])

    return HttpResponse(json.dumps({'data': orders, 'po_id': order_id, 'options': REJECT_REASONS,
        'supplier_id': order_data['supplier_id'], 'use_imei': use_imei, 'temp': temp, 'po_reference': po_reference, 'order_ids': order_ids}))


@csrf_exempt
@login_required
@get_admin_user
def update_putaway(request, user=''):
    for key, value in request.GET.iteritems():
        po = PurchaseOrder.objects.get(id=key)
        total_count = float(value)
        if not po.open_po:
            st_order = STPurchaseOrder.objects.filter(po_id=key, open_st__sku__user = user.id)
            order_quantity = st_order[0].open_st.order_quantity
        else:
            order_quantity = po.open_po.order_quantity
        if total_count > order_quantity:
            return HttpResponse('Given quantity is greater than expected quantity')
        setattr(po, 'saved_quantity', float(value))
        po.save()

    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def close_po(request, user=''):
    if not request.GET:
        return HttpResponse('Updated Successfully')
    status = ''
    myDict = dict(request.GET.iterlists())
    reason = request.GET.get('remarks', '')
    for i in range(0, len(myDict['id'])):
        if myDict['id'][i]:
            if myDict['new_sku'][i] == 'true':
                sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user = user.id)
                if not sku_master or not myDict['id'][0]:
                    continue
                po_order = PurchaseOrder.objects.filter(id=myDict['id'][0])
                if po_order:
                    po_order_id = po_order[0].order_id
                new_data = {'supplier_id': [myDict['supplier_id'][i]], 'wms_code': [myDict['wms_code'][i]],
                            'order_quantity': [myDict['po_quantity'][i]], 'price': [myDict['price'][i]], 'po_order_id': po_order_id}
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
    all_stocks = StockDetail.objects.filter(sku__user=user, quantity__gt=0, location__max_capacity__gt=F('location__filled_capacity'))
    only_sku_locs = list(all_stocks.exclude(location__zone__zone='DEFAULT').exclude(sku__wms_code=wms_code).
                                      values_list('location_id', flat=True))
    stock_detail1 = all_stocks.exclude(location__zone__zone='DEFAULT').exclude(location_id__in=only_sku_locs).filter(sku__wms_code=wms_code).\
                                       values('location_id', 'location__max_capacity').distinct().annotate(total=Sum('quantity'))
    if sku and not sku.mix_sku == 'no_mix':
        only_locs = map(lambda d: d['location_id'], stock_detail1)
        stock_detail2 = all_stocks.exclude(location__zone__zone='DEFAULT').exclude(location_id__in=only_locs).filter(sku__wms_code=wms_code).\
                                       values('location_id', 'location__max_capacity').distinct().annotate(total=Sum('quantity'))
        stock_detail = list(chain(stock_detail1, stock_detail2))
    else:
        stock_detail = stock_detail1
    location_ids = map(lambda d: d['location_id'], stock_detail)
    loc1 = LocationMaster.objects.exclude(fill_sequence=0).exclude(get_dictionary_query(exc_dict)).exclude(zone__zone__in=exclude_zones_list).\
                                  filter(id__in=location_ids).order_by('fill_sequence')
    if 'pallet_capacity' in exc_dict.keys():
        del exc_dict['pallet_capacity']
    loc2 = LocationMaster.objects.exclude(get_dictionary_query(exc_dict)).exclude(zone__zone__in=exclude_zones_list).filter(id__in=location_ids, fill_sequence=0)
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
    location_masters = LocationMaster.objects.filter(zone__user=user).exclude(lock_status__in=['Inbound', 'Inbound and Outbound'])
    exclude_zones_list = ['QC_ZONE', 'DAMAGED_ZONE', 'RTO_ZONE']
    if put_zone in exclude_zones_list:
        location = location_masters.filter(zone__zone=put_zone, zone__user=user)
        if location:
            return location
    if data:
        order_data = get_purchase_order_data(data)
    else:
        order_data = {'sku_group': temp_dict['sku_group'], 'wms_code':temp_dict['wms_code'], 'sku': temp_dict.get('sku', '')}
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
        #Get locations with same sku only
        sku_locs = stock_detail.filter(quantity__gt=0, sku__wms_code=order_data['wms_code']).\
                                       values_list('location_id', flat=True).distinct()
        not_empty_locs = stock_detail.filter(quantity__gt=0, location_id__in=list(sku_locs)).\
                                             values_list('location_id', flat=True).distinct().\
                                             annotate(sku_count=Count('sku_id', distinct=True)).filter(sku_count=1)
        #Get locations with same only in suggested data
        sku_po_locs = po_locations.filter(quantity__gt=0, purchase_order__open_po__sku__wms_code=order_data['wms_code']).\
                                         values_list('location_id', flat=True).distinct()
        suggested_locs = po_locations.filter(quantity__gt=0, location_id__in=list(sku_po_locs)).\
                                            values_list('location_id', flat=True).distinct().\
                                            annotate(sku_count=Count('purchase_order__open_po__sku_id', distinct=True)).\
                                            filter(sku_count=1)
        stock_non_empty = stock_detail.filter(quantity__gt=0).exclude(location_id__in=list(not_empty_locs)).\
                                                              values_list('location_id', flat=True).distinct()
        suggestion_non_empty = po_locations.filter(quantity__gt=0).exclude(location_id__in=list(suggested_locs)).values_list('location_id',
                                                   flat=True).distinct()

        exc_group_dict['location_id__in'] = list(chain(stock_non_empty, suggestion_non_empty))
        exclude_dict['id__in'] = list(chain(stock_non_empty, suggestion_non_empty))
    #elif order_data['sku'].mix_sku == 'mix_group':
    else:
        no_mix_locs = list(StockDetail.objects.filter(sku__user=user, quantity__gt=0, sku__mix_sku='no_mix').\
                                              values_list('location_id', flat=True))
        no_mix_sugg = list(POLocation.objects.filter(location__zone__user=user, status=1, quantity__gt=0,
                                              purchase_order__open_po__sku__mix_sku='no_mix').\
                                              values_list('location_id', flat=True))
        exc_group_dict['location_id__in'] = list(chain(no_mix_locs, no_mix_sugg))
        exclude_dict['id__in'] = list(chain(no_mix_locs, no_mix_sugg))

    if seller_id:
        #Other Seller Locations
        other_seller_locs = SellerStock.objects.filter(seller__user=user, quantity__gt=0).exclude(seller_id=seller_id).values_list('stock__location_id', flat=True)
        other_seller_locs_suggested = SellerPOSummary.objects.filter(seller_po__seller__user=user, putaway_quantity__gt=0, location__isnull=False).\
                                                      exclude(seller_po__seller_id=seller_id).values_list('location_id', flat=True)

        exc_group_dict['location_id__in'] = list(chain(exc_group_dict['location_id__in'], other_seller_locs, other_seller_locs_suggested))
        exclude_dict['id__in'] = list(chain(exclude_dict['id__in'], other_seller_locs, other_seller_locs_suggested))
    if sku_group:
        locations = LocationGroups.objects.exclude(get_dictionary_query(exc_group_dict)).filter(location__zone__user=temp_dict['user'], group=sku_group).\
                                           values_list('location_id',flat=True)
        all_locations = LocationGroups.objects.exclude(get_dictionary_query(exc_group_dict)).filter(location__zone__user=temp_dict['user'], group='ALL').\
                                           values_list('location_id',flat=True)
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

    stock_locations, location_ids, min_max = get_stock_locations(order_data['wms_code'], exclude_dict, user, exclude_zones_list, sku=order_data['sku'])
    if 'id__in' in exclude_dict.keys():
        location_ids = list(chain(location_ids, exclude_dict['id__in']))
    exclude_dict['id__in'] = location_ids

    location1 = location_masters.exclude(get_dictionary_query(exclude_dict)).filter(fill_sequence__gt=min_max[0], **filter_params).order_by('fill_sequence')
    location11 = location_masters.exclude(get_dictionary_query(exclude_dict)).filter(fill_sequence__lt=min_max[0], **filter_params).order_by('fill_sequence')
    location2 = location_masters.exclude(get_dictionary_query(exclude_dict)).filter(**cond1).order_by('fill_sequence')
    if put_zone not in ['QC_ZONE', 'DAMAGED_ZONE']:
        location1 = list(chain(stock_locations,location1))
    location2 = list(chain(location1, location11, location2))

    if 'pallet_capacity' in exclude_dict.keys():
        del exclude_dict['pallet_capacity']

    location3 = location_masters.exclude(get_dictionary_query(exclude_dict)).filter(**cond2)
    del exclude_dict['location__exact']
    del filter_params['zone__zone']
    location4 = location_masters.exclude(Q(location__exact='') | Q(zone__zone=put_zone) | get_dictionary_query(exclude_dict)).\
                                       exclude(zone__zone__in=exclude_zones_list).filter(**filter_params).order_by('fill_sequence')
    if sku_group:
        if 'id__in' in filter_params.keys():
            del filter_params['id__in']
        group_locs = list(LocationGroups.objects.filter(location__zone__user=user).values_list('location_id', flat=True).distinct())
        exclude_dict['id__in'] = group_locs
        location5 = location_masters.exclude(Q(location__exact='') | Q(zone__zone=put_zone) | get_dictionary_query(exclude_dict)).\
                                     exclude(zone__zone__in=exclude_zones_list).filter(**filter_params).order_by('fill_sequence')
        location4 = list(chain(location4, location5))

    location = list(chain(location2, location3, location4))

    location = list(chain(location, location_masters.filter(zone__zone='DEFAULT')))

    return location

def get_remaining_capacity(loc, received_quantity, put_zone, pallet_number, user):
    if loc.zone.zone in ['DEFAULT', 'QC_ZONE', 'DAMAGED_ZONE']:
        return received_quantity, 0
    total_quantity = POLocation.objects.filter(location_id=loc.id, status=1, location__zone__user=user).\
                                        aggregate(Sum('quantity'))['quantity__sum']
    if not total_quantity:
        total_quantity = 0

    if not put_zone == 'QC_ZONE':
        pallet_count = len(PalletMapping.objects.filter(po_location__location_id=loc.id, po_location__location__zone__user=user,status=1))
        if pallet_number:
            if pallet_count >= float(loc.pallet_capacity):
                return '', received_quantity
    filled_capacity = StockDetail.objects.filter(location_id=loc.id, quantity__gt=0, sku__user=user).aggregate(Sum('quantity'))['quantity__sum']
    if not filled_capacity:
        filled_capacity = 0

    filled_capacity = float(total_quantity) + float(filled_capacity)
    remaining_capacity = float(loc.max_capacity) - float(filled_capacity)
    remaining_capacity = float(get_decimal_limit(user, remaining_capacity))
    if remaining_capacity <= 0:
        return '',received_quantity
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
    location_data['creation_date'] =  datetime.datetime.now()
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
                                                         receipt_number=seller_summary.receipt_number, quantity=quantity,
                                                         putaway_quantity=quantity, location_id=location.id,
                                                         purchase_order_id=data.id, creation_date=datetime.datetime.now())
    po_received['quantity'] = po_received['quantity'] - quantity
    return po_received

@csrf_exempt
def save_po_location(put_zone, temp_dict, seller_received_list=[]):
    data = temp_dict['data']
    user = temp_dict['user']
    pallet_number = 0
    if 'pallet_number' in temp_dict.keys():
        pallet_number = temp_dict['pallet_number']
    #location = get_purchaseorder_locations(put_zone, temp_dict)
    received_quantity = float(temp_dict['received_quantity'])
    data.status = 'grn-generated'
    data.save()
    purchase_data = get_purchase_order_data(data)
    if not seller_received_list:
        seller_received_list.append({'seller_id': '', 'sku_id': (purchase_data['sku']).id, 'quantity': received_quantity, 'id': ''})
    for po_received in seller_received_list:
        temp_dict['seller_id'] = po_received.get('seller_id', '')
        location = get_purchaseorder_locations(put_zone, temp_dict)
        received_quantity = po_received['quantity']
        for loc in location:
            location_quantity, received_quantity = get_remaining_capacity(loc, received_quantity, put_zone, pallet_number, user)
            if not location_quantity:
                continue
            if po_received.get('seller_id', '') and not loc.zone.zone == 'QC_ZONE':
                po_received = update_seller_summary_locs(data, loc, location_quantity, po_received)
            if not 'quality_check' in temp_dict.keys():
                location_data = {'purchase_order_id': data.id, 'location_id': loc.id, 'status': 1}
                user_check = 'location__zone__user'
                if data.open_po:
                    user_check = 'purchase_order__open_po__sku__user'
                po_loc = save_update_order(location_quantity, location_data, temp_dict, user_check, user)
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
                po_location = POLocation.objects.filter(location_id=loc.id, purchase_order_id=data.id, location__zone__user=user)
                if po_location and not pallet_number:
                    if po_location[0].status == '1':
                        setattr(po_location[0], 'quantity', float(po_location[0].quantity) + location_quantity)
                    else:
                        setattr(po_location[0], 'quantity', float(location_quantity))
                        setattr(po_location[0], 'status', '1')
                    po_location[0].save()
                    po_location_id = po_location[0].id
                else:
                    location_data = {'purchase_order_id': data.id, 'location_id': loc.id, 'status': 1, 'quantity': location_quantity,
                                     'original_quantity': location_quantity, 'creation_date': datetime.datetime.now()}
                    po_loc = POLocation(**location_data)
                    po_loc.save()
                    po_location_id = po_loc.id
                if pallet_number:
                    if not put_zone == 'DAMAGED_ZONE':
                        pallet_data = temp_dict['pallet_data']
                        setattr(pallet_data, 'po_location_id', po_loc)
                        pallet_data.save()
                quality_checked_data = QualityCheck.objects.filter(purchase_order_id=data.id, purchase_order__open_po__sku__user=user)
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
        lr_details = LRDetail(lr_number=lr_number, carrier_name=carrier_name, quantity=data.received_quantity, creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now(), purchase_order_id=data.id)
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
        supplier_mapping = SKUSupplier.objects.filter(sku__wms_code=myDict['wms_code'][i].upper(), supplier_id=data.open_po.supplier_id,
                                                      sku__user=user.id)
        if supplier_mapping:
            supplier_mapping = supplier_mapping[0]
            setattr(supplier_mapping, 'supplier_code', data.open_po.supplier_code)
            supplier_mapping.save()
        else:
            sku_mapping = {'supplier_id': data.open_po.supplier_id, 'sku': data.open_po.sku, 'preference': 1, 'moq': 0,
                           'supplier_code': data.open_po.supplier_code, 'price': data.open_po.price, 'creation_date': datetime.datetime.now(),
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
        pallet_map = {'pallet_detail_id': save_pallet.id, 'po_location_id': po_location_id.id,'creation_date': datetime.datetime.now(), 'status': status}
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
           stock_dict = {'location_id': location_id[0].id, 'receipt_number': 0, 'receipt_date': datetime.datetime.now(),
                         'sku_id':sku_id[0].id, 'quantity': quantity, 'status': 1, 'creation_date': datetime.datetime.now()}
           stock = StockDetail(**stock_dict)
           stock.save()
           mod_location.append(location_id[0].location)
    if mod_location:
        update_filled_capacity(list(set(mod_location)), user_id)

def get_seller_receipt_id(open_po):
    receipt_number = 1
    summary = SellerPOSummary.objects.filter(seller_po__open_po_id=open_po.id, seller_po__seller__user=open_po.sku.user).order_by('-creation_date')
    if summary:
        receipt_number = int(summary[0].receipt_number) + 1
    return receipt_number

def update_seller_po(data, value, user, receipt_id=''):
    if not receipt_id:
        return
    seller_pos = SellerPO.objects.filter(seller__user=user.id, open_po_id=data.open_po_id, status=1)
    seller_received_list = []
    for sell_po in seller_pos:
        if not value:
            break
        unit_price = data.open_po.price
        if not sell_po.unit_price:
            margin_percent = get_misc_value('seller_margin', user.id)
            if sell_po.seller.margin:
                margin_percent = sell_po.seller.margin
            seller_mapping = SellerMarginMapping.objects.filter(seller_id=sell_po.seller_id, sku_id=data.open_po.sku_id, seller__user=user.id)
            if seller_mapping:
                margin_percent = seller_mapping[0].margin
            if margin_percent:
                try:
                    margin_percent = float(margin_percent)
                except:
                    margin_percent = 0
                price = float(data.open_po.price)
                tax = data.open_po.cgst_tax + data.open_po.sgst_tax + data.open_po.igst_tax + data.open_po.utgst_tax
                price = price + ((price/100)*float(tax))
                unit_price = float(price)/(1-(margin_percent/100))
                sell_po.unit_price = float(("%."+ str(2) +"f") % (unit_price))
                sell_po.margin_percent = margin_percent
        seller_quantity = sell_po.seller_quantity
        sell_quan = value
        if seller_quantity < value:
            sell_quan = seller_quantity
            value -= seller_quantity
        elif seller_quantity >= value:
            sell_quan = value
            value = 0
        sell_po.received_quantity += sell_quan
        if sell_po.seller_quantity <= sell_po.received_quantity:
            sell_po.status = 0
        sell_po.save()

        #seller_received_list.append({'seller_id': sell_po.seller_id, 'sku_id': data.open_po.sku_id, 'quantity': sell_quan})
        seller_po_summary, created = SellerPOSummary.objects.get_or_create(seller_po_id=sell_po.id, receipt_number=receipt_id,
                                                         quantity=sell_quan, putaway_quantity=sell_quan, purchase_order_id=data.id,
                                                         creation_date=datetime.datetime.now())
        seller_received_list.append({'seller_id': sell_po.seller_id, 'sku_id': data.open_po.sku_id, 'quantity': sell_quan, 'id': seller_po_summary.id})
    return seller_received_list

def generate_grn(myDict, request, user, is_confirm_receive=False):
    order_quantity_dict = {}
    all_data = {}
    seller_receipt_id = {}
    po_data = []
    status_msg = ''
    data_dict = ''
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
            if myDict['wms_code'][i] and myDict['po_quantity'][i] and myDict['quantity'][i]:
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
        purchase_data = get_purchase_order_data(data)
        temp_quantity = data.received_quantity
        unit = ''
        if 'unit' in myDict.keys():
            unit = myDict['unit'][i]
        cond = (data.id, purchase_data['wms_code'], unit, purchase_data['price'], purchase_data['cgst_tax'], purchase_data['sgst_tax'], purchase_data['igst_tax'], purchase_data['utgst_tax'])
        all_data.setdefault(cond, 0)
        all_data[cond] += float(value)

        if data.id not in order_quantity_dict:
            order_quantity_dict[data.id] = float(purchase_data['order_quantity']) - temp_quantity
        data.received_quantity = float(data.received_quantity) + float(value)
        data.saved_quantity = 0

        seller_received_list = []
        if data.open_po:
            if not seller_receipt_id:
                seller_receipt_id = get_seller_receipt_id(data.open_po)
            seller_received_list = update_seller_po(data, value, user, receipt_id=seller_receipt_id)
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

        if is_confirm_receive or (get_permission(request.user,'add_qualitycheck') and purchase_data['qc_check'] == 1):
            put_zone = 'QC_ZONE'
            qc_data = copy.deepcopy(QUALITY_CHECK_FIELDS)
            qc_data['purchase_order_id'] = data.id
            temp_dict['qc_data'] = qc_data
            save_po_location(put_zone, temp_dict, seller_received_list=seller_received_list)
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
        save_po_location(put_zone, temp_dict, seller_received_list=seller_received_list)
        create_bayarea_stock(purchase_data['wms_code'], 'BAY_AREA', temp_dict['received_quantity'], user.id)
        data_dict = (('Order ID', data.order_id), ('Supplier ID', purchase_data['supplier_id']),
                     ('Order Date', get_local_date(request.user, data.creation_date)),
                     ('Supplier Name', purchase_data['supplier_name']),
                     ('GSTIN No', purchase_data['gstin_number']))

        price = float(value) * float(purchase_data['price'])
        gst_taxes = purchase_data['cgst_tax'] + purchase_data['sgst_tax'] + purchase_data['igst_tax'] + purchase_data['utgst_tax']
        if gst_taxes:
            price += (price/100) * gst_taxes
        po_data.append((purchase_data['wms_code'], purchase_data['supplier_code'], purchase_data['sku_desc'], purchase_data['order_quantity'],
                        value, price))
    return po_data, status_msg, all_data, order_quantity_dict, purchase_data, data, data_dict

@csrf_exempt
@login_required
@get_admin_user
def confirm_grn(request, confirm_returns = '', user=''):
    data_dict = ''
    headers = ('WMS CODE', 'Order Quantity', 'Received Quantity', 'Measurement', 'Unit Price', 'CSGT(%)', 'SGST(%)', 'IGST(%)', 'UTGST(%)', 'Amount')
    putaway_data = {headers: []}
    total_received_qty = 0
    total_order_qty = 0
    total_price = 0
    pallet_number = ''
    is_putaway = ''
    purchase_data = ''
    seller_name = user.username
    if not confirm_returns:
        request_data = request.POST
        myDict = dict(request_data.iterlists())
    else:
        myDict = confirm_returns

    log.info('Request params for ' + user.username + ' is ' + str(myDict))
    try:
        po_data, status_msg, all_data, order_quantity_dict, purchase_data, data, data_dict = generate_grn(myDict, request, user)

        for key, value in all_data.iteritems():
            entry_price = float(key[3]) * float(value)
            entry_tax = float(key[4]) + float(key[5]) + float(key[6]) + float(key[7])
            if entry_tax:
                entry_price += (float(entry_price)/100) * entry_tax
            putaway_data[headers].append((key[1], order_quantity_dict[key[0]], value, key[2], key[3], key[4], key[5], key[6], key[7], entry_price))
            total_order_qty += order_quantity_dict[key[0]]
            total_received_qty += value
            total_price += entry_price

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

            profile = UserProfile.objects.get(user=user.id)
            po_reference = '%s%s_%s' % (data.prefix, str(data.creation_date).split(' ')[0].replace('-', ''), order_id)
            table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Ordered Quantity', 'Received Quantity', 'Amount')
            '''report_data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                                'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total_price,
                                'po_reference': po_reference, 'total_qty': total_received_qty,
                                'report_name': 'Goods Receipt Note', 'company_name': profile.company_name, 'location': profile.location}'''
            report_data_dict = {'data': putaway_data, 'data_dict': data_dict,
                                   'total_received_qty': total_received_qty, 'total_order_qty': total_order_qty, 'total_price': total_price,
                                   'seller_name': seller_name, 'company_name': profile.company_name,
                                   'po_number': str(data.prefix) + str(data.creation_date).split(' ')[0] + '_' + str(data.order_id),
                                   'order_date': get_local_date(request.user, data.creation_date), 'order_id': order_id, 'btn_class': btn_class}

            misc_detail = get_misc_value('receive_po', user.id)
            if misc_detail == 'true':
                t = loader.get_template('templates/toggle/grn_form.html')
                rendered = t.render(report_data_dict)
                write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, telephone, po_data, order_date, internal=True, report_type="Goods Receipt Note")
            return render(request, 'templates/toggle/putaway_toggle.html', report_data_dict)
        else:
            return HttpResponse(status_msg)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Check Generating GRN failed for params " + str(myDict) + " and error statement is " + str(e))
        return HttpResponse("Generate GRN Failed")

@csrf_exempt
def confirmation_location(record, data, total_quantity, temp_dict = ''):
    location_data = {'purchase_order_id': data.id, 'location_id': record.id, 'status': 1, 'quantity': '', 'creation_date': datetime.datetime.now()}
    if total_quantity < ( record.max_capacity - record.filled_capacity ):
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

@login_required
@get_admin_user
def check_returns(request, user=''):
    status = ''
    all_data = {}
    data = []
    request_order_id = request.GET.get('order_id', '')
    request_return_id = request.GET.get('return_id', '')
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
            cond = (picklist.order.order_id, wms_code, sku_desc)
            all_data.setdefault(cond, 0)
            all_data[cond] += picklist.picked_quantity
        for key, value in all_data.iteritems():
            data.append({'order_id': key[0], 'sku_code': key[1], 'sku_desc': key[2], 'ship_quantity': value, 'return_quantity': 0,
                         'damaged_quantity': 0 })
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
            data.append({'id': order_data.id, 'order_id': order_obj.order_id, 'return_id': order_data.return_id,
                         'sku_code': order_data.sku.sku_code,
                         'sku_desc': order_data.sku.sku_desc, 'ship_quantity': order_quantity,
                         'return_quantity': order_data.quantity, 'damaged_quantity': order_data.damaged_quantity})

    if not status:
        return HttpResponse(json.dumps(data, cls=DjangoJSONEncoder))
    return HttpResponse(status)

@csrf_exempt
@get_admin_user
def check_sku(request, user=''):
    sku_code = request.GET.get('sku_code')
    check = False
    sku_id = check_and_return_mapping_id(sku_code, '', user, check)
    if not sku_id:
        try:
            sku_id = SKUMaster.objects.filter(ean_number=sku_code, user=user.id)
        except:
            sku_id = ''
    if sku_id:
        sku_data = SKUMaster.objects.get(id = sku_id)
        data = {"status": 'confirmed', 'sku_code': sku_data.sku_code, 'description': sku_data.sku_desc}
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
    location1 = LocationMaster.objects.exclude(location__exact='', zone__zone=exclude_zone).filter(zone__zone=put_zone, fill_sequence__gt=0, max_capacity__gt=F('filled_capacity'), zone__user=user, pallet_filled=0).order_by('fill_sequence')
    location2 = LocationMaster.objects.exclude(location__exact='', zone__zone=exclude_zone).filter(zone__zone=put_zone, fill_sequence=0, max_capacity__gt=F('filled_capacity'), pallet_filled=0, zone__user=user)
    location3 = LocationMaster.objects.exclude(Q(location__exact='') | Q(zone__zone__in=[put_zone, exclude_zone])).filter(max_capacity__gt=F('filled_capacity'), zone__user=user, pallet_filled=0)
    location4 = LocationMaster.objects.filter(zone__zone = 'DEFAULT', zone__user = user)
    location = list(chain(location1, location2, location3, location4))
    return location


def create_return_order(data, user):
    seller_order_ids = []
    status = ''
    user_obj = User.objects.get(id=user)
    sku_id = SKUMaster.objects.filter(sku_code = data['sku_code'], user = user)
    if not sku_id:
        return "", "SKU Code doesn't exist"
    return_details = copy.deepcopy(RETURN_DATA)
    user_obj = User.objects.get(id=user)
    if (data['return'] or data['damaged']) and sku_id:
        #order_details = OrderReturns.objects.filter(return_id = data['return_id'][i])
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
            order_detail = get_order_detail_objs(data['order_id'], user_obj, search_params={'sku_id': sku_id[0].id, 'user': user})
            if order_detail:
                return_details['order_id'] = order_detail[0].id
                if order_detail[0].status == int(2):
                    order_detail[0].status = 4
                    order_detail[0].save()
                seller_order_id = get_returns_seller_order_id(return_details['order_id'], sku_id[0].sku_code, user_obj, sor_id=sor_id)
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
        new_zone,created = ZoneMaster.objects.get_or_create(user=user.id, zone=zone, creation_date=datetime.datetime.now())
        locations, loc_created = LocationMaster.objects.get_or_create(location=location, max_capacity=100000, fill_sequence=sequence,
                                                        pick_sequence=sequence, status=1, zone_id=new_zone.id,
                                                        creation_date=datetime.datetime.now())
        log.info('%s created for user %s' % (zone, user.username))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(e)
        return []
    return [locations]

def save_return_locations(order_returns, all_data, damaged_quantity, request, user, is_rto=False):
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
        temp_dict ={'received_quantity': float(order_returns.quantity), 'data': "", 'user': user.id, 'pallet_data': '', 'pallet_number': '',
                    'wms_code': order_returns.sku.wms_code, 'sku_group': order_returns.sku.sku_group, 'sku': order_returns.sku}
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
                                                       location__zone__user=user.id).aggregate(Sum('quantity'))['quantity__sum']
            if not total_quantity:
                total_quantity = 0
            filled_capacity = StockDetail.objects.filter(location_id=location.id, quantity__gt=0,
                                                         sku__user=user.id).aggregate(Sum('quantity'))['quantity__sum']
            if not filled_capacity:
                filled_capacity = 0
            filled_capacity = float(total_quantity) + float(filled_capacity)
            remaining_capacity = float(location.max_capacity) - float(filled_capacity)
            if remaining_capacity <= 0:
                continue
            elif remaining_capacity < received_quantity:
                location_quantity = remaining_capacity
                received_quantity -= remaining_capacity
            elif remaining_capacity >= received_quantity:
                location_quantity = received_quantity
                received_quantity = 0
            return_location = ReturnsLocation.objects.filter(returns_id=order_returns.id, location_id=location.id, status=1)
            if not return_location:
                location_data = {'returns_id': order_returns.id, 'location_id': location.id, 'quantity': location_quantity, 'status': 1}
                returns_data = ReturnsLocation(**location_data)
                returns_data.save()
            else:
                return_location = return_location[0]
                setattr(return_location, 'quantity', float(return_location.quantity) + location_quantity)
                return_location.save()
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
        order_imei = OrderIMEIMapping.objects.filter(po_imei__imei_number=imei, order__sku__user=user.id, status=1)
        if not order_imei:
            continue
        elif order_imei:
            order_imei[0].status = 0
            order_imei[0].save()
            po_imei = order_imei[0].po_imei
            po_imei.status = 1
            po_imei.save()

        returns_imei = ReturnsIMEIMapping.objects.filter(order_return__sku__user=user.id, order_imei_id=order_imei[0].id, status=1)
        if not returns_imei:
            ReturnsIMEIMapping.objects.create(order_imei_id=order_imei[0].id, status=status, reason=reason,
                                              creation_date=datetime.datetime.now(), order_return_id=returns.id)

def group_sales_return_data(data_dict, return_process):
    """ Group Sales Return Data """

    returns_dict = {}
    grouping_dict = {'order_id': '[str(data_dict["order_id"][ind]), str(data_dict["sku_code"][ind])]',
                     'sku_code': 'data_dict["sku_code"][ind]', 'return_id': 'data_dict["id"][ind]',
                     'scan_imei': 'data_dict["id"][ind]'}
    grouping_key = grouping_dict[return_process]
    zero_index_list = ['scan_order_id', 'return_process', 'return_type']
    number_fields = ['return', 'damaged']

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
                                              status='return', reason=reason_dict['reason'],creation_date=datetime.datetime.now())

@csrf_exempt
@login_required
@get_admin_user
def confirm_sales_return(request, user=''):
    """ Creating and Confirming the Sales Returns"""

    data_dict = dict(request.POST.iterlists())
    return_type = request.POST.get('return_type', '')
    return_process = request.POST.get('return_process')
    mp_return_data = {}
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
            locations_status = save_return_locations(**return_loc_params)
            if not locations_status == 'Success':
                return HttpResponse(locations_status)
        if user.userprofile.user_type == 'marketplace_user':
            check_and_update_order_status_data(mp_return_data, user, status='RETURNED')
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Confirm Sales return for ' + str(user.username) + ' is failed for ' + str(
                    request.POST.dict()) + ' error statement is ' + str(e))

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
    purchase_orders = PurchaseOrder.objects.filter(order_id=supplier_id, open_po__sku__user = user.id, open_po__sku_id__in=sku_master_ids).\
                                            exclude(status__in=['', 'confirmed-putaway'])
    if not purchase_orders:
        st_orders = STPurchaseOrder.objects.filter(po__order_id=supplier_id, open_st__sku__user = user.id, open_st__sku_id__in=sku_master_ids).\
                                exclude(po__status__in=['', 'confirmed-putaway', 'stock-transfer']).values_list('po_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=st_orders)
    for order in purchase_orders:
        order_id = order.id
        order_data = get_purchase_order_data(order)
        po_location = POLocation.objects.filter(purchase_order_id=order_id, status=1, location__zone__user = user.id)
        total_sku_quantity = po_location.aggregate(Sum('quantity'))['quantity__sum']
        if not total_sku_quantity:
            total_sku_quantity = 0
        if order_data['wms_code'] in sku_total_quantities.keys():
            sku_total_quantities[order_data['wms_code']] += float(total_sku_quantity)
        else:
            sku_total_quantities[order_data['wms_code']] = float(total_sku_quantity)
        for location in po_location:
            pallet_number = ''
            if temp == "true":
                pallet_mapping = PalletMapping.objects.filter(po_location_id=location.id, status=1)
                if pallet_mapping:
                    pallet_number = pallet_mapping[0].pallet_detail.pallet_code
                    cond = (pallet_number, location.location.location)
                    all_data.setdefault(cond, [0, '',0, '', []])
                    if all_data[cond] == [0, '', 0, '', []]:
                        all_data[cond] = [all_data[cond][0] + float(location.quantity), order_data['wms_code'],
                                          float(location.quantity), location.location.fill_sequence, [{'orig_id': location.id,
                                          'orig_quantity': location.quantity}], order_data['unit'], order_data['sku_desc'],
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

    if temp == 'true' and all_data:
        for key, value in all_data.iteritems():
            data[key[0]] = {'wms_code': value[1], 'location': key[1], 'original_quantity': value[0], 'quantity': value[0],
                            'fill_sequence': value[3], 'id': '', 'pallet_number': key[0], 'pallet_group_data': value[4],
                            'unit': value[5], 'load_unit_handle': value[7],
                            'sub_data': [{'loc': key[1], 'quantity': value[0]}], 'sku_desc': value[6]}

    data_list = data.values()
    data_list.sort(key=lambda x: x['fill_sequence'])
    po_number = '%s%s_%s' % (order.prefix, str(order.po_date).split(' ')[0].replace('-', ''), order.order_id)
    return HttpResponse(json.dumps({'data': data_list, 'po_number': po_number,'order_id': order_id,'user': request.user.id,
                                    'sku_total_quantities': sku_total_quantities}))

def validate_putaway(all_data,user):
    status = ''
    back_order = 'false'
    misc_data = MiscDetail.objects.filter(user =  user.id, misc_type='back_order')
    if misc_data:
        back_order = misc_data[0].misc_value

    for key, value in all_data.iteritems():
        if not key[1]:
            status = 'Location is Empty, Enter Location'
        if key[1]:
            loc = LocationMaster.objects.filter(location=key[1], zone__user=user.id)
            if loc:
                loc = LocationMaster.objects.get(location = key[1],zone__user=user.id)
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
                                                                        picklist__order__user=user.id).\
                                                                        aggregate(Sum('reserved'))['reserved__sum']
                    po_loc_quantity = POLocation.objects.filter(purchase_order__open_po__sku__sku_code=sku_code, status=1,
                                                                purchase_order__open_po__sku__user=user.id).\
                                                         aggregate(Sum('quantity'))['quantity__sum']
                    if not pick_res_quantity:
                        pick_res_quantity = 0
                    if not po_loc_quantity:
                        po_loc_quantity = 0

                    diff = po_loc_quantity - pick_res_quantity
                    if diff and diff < value:
                        status = 'Bay Area Stock %s is reserved for %s in Picklist.You cannot putaway this stock.'% (pick_res_quantity,sku_code)

            else:
                status = 'Enter Valid Location'
    return status

def consume_bayarea_stock(sku_code, zone, quantity, user):
    back_order = 'false'
    data = MiscDetail.objects.filter(user =  user, misc_type='back_order')
    if data:
        back_order = data[0].misc_value

    location_master = LocationMaster.objects.filter(zone__zone=zone, zone__user=user)
    if not location_master or back_order == 'false':
        return
    location = location_master[0].location
    stock_detail = StockDetail.objects.filter(sku__sku_code = sku_code, location__location = location, sku__user=user)
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
        filter_params = {'location_id': exc_loc, 'location__zone__user':  user.id, order_id: po_id }
        po_obj = POLocation.objects.filter(**filter_params)
        if po_obj:
            add_po_quantity = float(po_obj[0].quantity) + float(value)
            po_obj[0].original_quantity = add_po_quantity
            po_obj[0].quantity = add_po_quantity
            po_obj[0].status = 0
            po_obj[0].save()
        else:
            location_data = {order_id: po_id, 'location_id': exc_loc, 'quantity': 0, 'original_quantity': value, 'status': 0,
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
    seller_po_summaries = SellerPOSummary.objects.filter(seller_po__seller__user=user.id, seller_po__open_po_id=data.purchase_order.open_po_id,
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
                                       creation_date=datetime.datetime.now(), status=1, stock_id=stock_obj.id)
        else:
            seller_stock[0].quantity = float(seller_stock[0].quantity) + float(sell_quan)
            seller_stock[0].save()
        if isinstance(seller_stock, QuerySet):
            seller_stock = seller_stock[0]

        if seller_stock:
            if seller_stock.stock.location.zone.zone not in ['DAMAGED_ZONE']:
                seller_stock_update_details.append({
                        'sku_code' : str(seller_stock.stock.sku.sku_code),
                        'seller_id' : int(seller_stock.seller.seller_id),
                        'quantity' : int(value)
                    })
    return seller_stock_update_details

@csrf_exempt
@login_required
@get_admin_user
def putaway_data(request, user=''):
    purchase_order_id= ''
    diff_quan = 0
    all_data = {}
    stock_detail = ''
    stock_data = ''
    putaway_stock_data = []
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
                    cond = (orig_data['orig_id'], myDict['loc'][i], myDict['po_id'][i], myDict['orig_loc_id'][i], myDict['wms_code'][i])
                    all_data.setdefault(cond, 0)
                    all_data[cond] += float(orig_data['orig_quantity'])
            else:
                cond = (myDict['id'][i], myDict['loc'][i], myDict['po_id'][i], myDict['orig_loc_id'][i], myDict['wms_code'][i])
                all_data.setdefault(cond, 0)
                if not myDict['quantity'][i]:
                    myDict['quantity'][i] = 0
                all_data[cond] += float(myDict['quantity'][i])

        all_data = OrderedDict(sorted(all_data.items(), reverse=True))
        status = validate_putaway(all_data,user)
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
                results = PurchaseOrder.objects.filter(open_po__sku__user = user.id, open_po__sku_id__in=sku_master_ids,
                                                       order_id=purchase_order_id, open_po__sku__wms_code=key[4]).exclude(status__in=['',
                                                       'confirmed-putaway']).values_list('id', flat=True).distinct()
                stock_results = STPurchaseOrder.objects.exclude(po__status__in=['','confirmed-putaway', 'stock-transfer']).\
                                                        filter(open_st__sku__user = user.id, open_st__sku_id__in=sku_master_ids,
                                                        open_st__sku__wms_code=key[4], po__order_id=purchase_order_id).\
                                                        values_list('po_id', flat=True).distinct()
                rw_results = RWPurchase.objects.filter(rwo__job_order__product_code_id__in=sku_master_ids,
                                                       rwo__job_order__product_code__wms_code=key[4]).exclude(purchase_order__status__in=['',
                                                'confirmed-putaway', 'stock-transfer'], purchase_order__order_id=purchase_order_id).\
                                                filter(rwo__vendor__user = user.id).values_list('purchase_order_id', flat=True)
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
                if float(data.quantity) < count:
                    value = count - float(data.quantity)
                    count -= float(data.quantity)
                else:
                    value = count
                    count = 0
                order_data = get_purchase_order_data(data.purchase_order)
                putaway_location(data, value, exc_loc, user, 'purchase_order_id', data.purchase_order_id)
                stock_data = StockDetail.objects.filter(location_id=exc_loc, receipt_number=data.purchase_order.order_id,
                                                        sku_id=order_data['sku_id'], sku__user=user.id)
                pallet_mapping = PalletMapping.objects.filter(po_location_id=data.id,status=1)
                if pallet_mapping:
                    stock_data = StockDetail.objects.filter(location_id=exc_loc, receipt_number=data.purchase_order.order_id,
                                                            sku_id=order_data['sku_id'], sku__user=user.id,
                                                            pallet_detail_id=pallet_mapping[0].pallet_detail.id)
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
                    update_details = create_update_seller_stock(data, value, user, stock_data, old_loc, use_value=True)
                    if update_details:
                        marketplace_data += update_details

                    #Collecting data for auto stock allocation
                    putaway_stock_data.append({'sku_id': stock_data.sku_id, 'mapping_id': data.purchase_order_id })

                else:
                    record_data = {'location_id': exc_loc, 'receipt_number': data.purchase_order.order_id,
                                   'receipt_date': str(data.purchase_order.creation_date).split('+')[0],'sku_id': order_data['sku_id'],
                                   'quantity': value, 'status': 1, 'receipt_type': 'purchase order', 'creation_date': datetime.datetime.now(),
                                   'updation_date': datetime.datetime.now()}
                    if pallet_mapping:
                        record_data['pallet_detail_id'] = pallet_mapping[0].pallet_detail.id
                        pallet_mapping[0].status = 0
                        pallet_mapping[0].save()
                    stock_detail = StockDetail(**record_data)
                    stock_detail.save()

                    #Collecting data for auto stock allocation
                    putaway_stock_data.append({'sku_id': stock_detail.sku_id, 'mapping_id': data.purchase_order_id})

                    update_details = create_update_seller_stock(data, value, user, stock_detail, old_loc)
                    if update_details:
                        marketplace_data += update_details
                consume_bayarea_stock(order_data['sku_code'], "BAY_AREA", float(value), user.id)

                if order_data['sku_code'] not in sku_codes:
                    sku_codes.append(order_data['sku_code'])

                putaway_quantity = POLocation.objects.filter(purchase_order_id=data.purchase_order_id,
                                                             location__zone__user = user.id, status=0).\
                                                             aggregate(Sum('original_quantity'))['original_quantity__sum']
                if not putaway_quantity:
                    putaway_quantity = 0
                if (float(order_data['order_quantity']) <= float(data.purchase_order.received_quantity)) and float(data.purchase_order.received_quantity) - float(putaway_quantity) <= 0:
                    data.purchase_order.status = 'confirmed-putaway'

                data.purchase_order.save()
        if user.userprofile.user_type == 'marketplace_user':
            check_and_update_marketplace_stock(marketplace_data, user)
        else:
            check_and_update_stock(sku_codes, user)

        updated_location = update_filled_capacity(list(set(mod_locations)), user.id)

        # Auto Allocate Stock
        order_allocate_stock(request, user, stock_data = putaway_stock_data, mapping_type='PO')

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
    po_reference = ''
    order_id = request.GET['order_id']
    purchase_orders = PurchaseOrder.objects.filter(order_id=order_id, open_po__sku__user = user.id, open_po__sku_id__in=sku_master_ids)
    if not purchase_orders:
        purchase_orders = []
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['confirmed-putaway', 'stock-transfer']).\
                                                filter(open_st__sku__user=user.id, open_st__sku_id__in=sku_master_ids).\
                                                values_list('po_id', flat=True)
        qc_results = QualityCheck.objects.filter(purchase_order_id__in=stock_results, status='qc_pending',
                                                 po_location__location__zone__user = user.id)
        for qc in qc_results:
            purchase_orders.append(qc.purchase_order)
    for order in purchase_orders:
        quality_check = QualityCheck.objects.filter(Q(purchase_order__open_po__sku_id__in=sku_master_ids) |
                                                    Q(purchase_order_id__in=stock_results),
                                                    purchase_order_id=order.id, status='qc_pending',
                                                    po_location__location__zone__user = user.id)
        for qc_data in quality_check:
            purchase_data = get_purchase_order_data(qc_data.purchase_order)
            po_reference = '%s%s_%s' % (qc_data.purchase_order.prefix, str(qc_data.purchase_order.creation_date).split(' ')[0].\
                                        replace('-', ''), qc_data.purchase_order.order_id)
            data.append({'id': qc_data.id, 'wms_code': purchase_data['wms_code'], 'location': qc_data.po_location.location.location,
                         'quantity': get_decimal_limit(user.id, qc_data.putaway_quantity), 'unit': purchase_data['unit'],
                         'accepted_quantity': get_decimal_limit(user.id, qc_data.accepted_quantity),
                         'rejected_quantity': get_decimal_limit(user.id, qc_data.rejected_quantity)})

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
    for key,value in request.POST.iteritems():
        if key == 'receive_po':
            continue
        order_id = ''
        if value and '_' in value:
            value = value.split('_')[-1]
            order_id = value
        if not is_receive_po:
            filter_params = {'purchase_order__open_po__sku__wms_code': key, 'po_location__status': 2,
                             'po_location__location__zone__user': user.id, 'status': 'qc_pending'}
            if order_id:
                filter_params['purchase_order__order_id'] = value
            model_name = QualityCheck
            field_mapping = {'purchase_order': 'data.purchase_order', 'prefix': 'data.purchase_order.prefix',
                             'creation_date': 'data.purchase_order.creation_date','order_id': 'data.purchase_order.order_id',
                             'quantity': 'data.po_location.quantity', 'accepted_quantity': 'data.accepted_quantity',
                             'rejected_quantity': 'data.rejected_quantity'}
        else:
            filter_params = {'open_po__sku__wms_code': key, 'open_po__sku__user': user.id, 'open_po__order_quantity__gt': F('received_quantity')}
            if order_id:
                filter_params['order_id'] = value
            model_name = PurchaseOrder
            field_mapping = {'purchase_order': 'data', 'prefix': 'data.prefix', 'creation_date': 'data.creation_date',
                             'order_id': 'data.order_id', 'quantity': '(data.open_po.order_quantity) - (data.received_quantity)',
                             'accepted_quantity': '0', 'rejected_quantity': '0'}
        st_purchase = STPurchaseOrder.objects.exclude(po__status__in=['confirmed-putaway', 'stock-transfer']).\
                                              filter(po__order_id=value, open_st__sku__wms_code=key, open_st__sku__user=user.id).\
                                              values_list('po_id', flat=True)
        if st_purchase and not is_receive_po:
            del filter_params['purchase_order__open_po__sku__wms_code']
            filter_params['purchase_order_id__in'] = st_purchase
        elif st_purchase:
            del filter_params['open_po__sku__wms_code']
            filter_params['id__in'] = st_purchase


        model_data = model_name.objects.filter(**filter_params)
        if not model_data:
            return HttpResponse("WMS Code not found")
        for data in model_data:
            purchase_data = get_purchase_order_data(eval(field_mapping['purchase_order']))
            sku = purchase_data['sku']
            image = sku.image_url
            po_reference = '%s%s_%s' % (eval(field_mapping['prefix']), str(eval(field_mapping['creation_date'])).\
                                        split(' ')[0].replace('-', ''), eval(field_mapping['order_id']))
            qc_data.append({'id': data.id,'order_id': po_reference,
                             'quantity': eval(field_mapping['quantity']), 'accepted_quantity': eval(field_mapping['accepted_quantity']),
                            'rejected_quantity': eval(field_mapping['rejected_quantity'])})
            sku_data = OrderedDict( ( ('SKU Code', sku.sku_code), ('Product Description', sku.sku_desc),
                                      ('SKU Brand', sku.sku_brand), ('SKU Category', sku.sku_category), ('SKU Class', sku.sku_class),
                                      ('Color', sku.color) ))
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

        temp_dict = {'received_quantity': float(myDict['accepted_quantity'][i]), 'original_quantity': float(quality_check.putaway_quantity),
                     'rejected_quantity': float(myDict['rejected_quantity'][i]), 'new_quantity': float(myDict['accepted_quantity'][i]),
                     'total_check_quantity': float(myDict['accepted_quantity'][i]) + float(myDict['rejected_quantity'][i]),
                     'user': user.id, 'data': data, 'quality_check': quality_check }
        if temp_dict['total_check_quantity'] == 0:
             continue
        seller_received_dict, seller_summary_dict = get_quality_check_seller(seller_received_dict, temp_dict, purchase_data)
        if get_misc_value('pallet_switch', user.id) == 'true':
            pallet_code = ''
            pallet = PalletMapping.objects.filter(po_location_id = quality_check.po_location_id)
            if pallet:
                pallet = pallet[0]
                pallet_code = pallet.pallet_detail.pallet_code
                if pallet and (not temp_dict['total_check_quantity'] == pallet.pallet_detail.quantity):
                    return HttpResponse('Partial quality check is not allowed for pallets')
                setattr(pallet.pallet_detail, 'quantity', temp_dict['new_quantity'])
                pallet.pallet_detail.save()
            temp_dict['pallet_number'] = pallet_code
            temp_dict['pallet_data'] = pallet
        save_po_location(put_zone, temp_dict, seller_received_list=seller_summary_dict)
        create_bayarea_stock(purchase_data['sku_code'], 'BAY_AREA', temp_dict['received_quantity'], user.id)
        if temp_dict['rejected_quantity']:
            put_zone = 'DAMAGED_ZONE'
            temp_dict['received_quantity'] = temp_dict['rejected_quantity']
            seller_received_dict, seller_summary_dict = get_quality_check_seller(seller_received_dict, temp_dict, purchase_data)
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
    '''for i in range(len(myDict['id'])):
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

        temp_dict = {'received_quantity': float(myDict['accepted_quantity'][i]), 'original_quantity': float(quality_check.putaway_quantity),
                     'rejected_quantity': float(myDict['rejected_quantity'][i]), 'new_quantity': float(myDict['accepted_quantity'][i]),
                     'total_check_quantity': float(myDict['accepted_quantity'][i]) + float(myDict['rejected_quantity'][i]),
                     'user': user.id, 'data': data, 'quality_check': quality_check }
        if temp_dict['total_check_quantity'] == 0:
             continue
        seller_received_dict, seller_summary_dict = get_quality_check_seller(seller_received_dict, temp_dict, purchase_data)
        if get_misc_value('pallet_switch', user.id) == 'true':
            pallet_code = ''
            pallet = PalletMapping.objects.filter(po_location_id = quality_check.po_location_id)
            if pallet:
                pallet = pallet[0]
                pallet_code = pallet.pallet_detail.pallet_code
                if pallet and (not temp_dict['total_check_quantity'] == pallet.pallet_detail.quantity):
                    return HttpResponse('Partial quality check is not allowed for pallets')
                setattr(pallet.pallet_detail, 'quantity', temp_dict['new_quantity'])
                pallet.pallet_detail.save()
            temp_dict['pallet_number'] = pallet_code
            temp_dict['pallet_data'] = pallet
        save_po_location(put_zone, temp_dict, seller_received_list=seller_summary_dict)
        create_bayarea_stock(purchase_data['sku_code'], 'BAY_AREA', temp_dict['received_quantity'], user.id)
        if temp_dict['rejected_quantity']:
            put_zone = 'DAMAGED_ZONE'
            temp_dict['received_quantity'] = temp_dict['rejected_quantity']
            seller_received_dict, seller_summary_dict = get_quality_check_seller(seller_received_dict, temp_dict, purchase_data)
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
            save_po_location(put_zone, temp_dict)'''

    use_imei = 'false'
    misc_data = MiscDetail.objects.filter(user=user.id, misc_type='use_imei')
    if misc_data:
        use_imei = misc_data[0].misc_value

    if myDict.get("accepted",''):
        save_qc_serials('accepted', myDict.get("accepted",''), user.id)
    if myDict.get("rejected",''):
        save_qc_serials('rejected', myDict.get("rejected",''), user.id)

    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def raise_st_toggle(request, user=''):
    user_list = []
    admin_user = UserGroups.objects.filter(Q(admin_user__username__iexact=user.username) | Q(user__username__iexact=user.username)).\
                 values_list('admin_user_id', flat=True)
    user_groups = UserGroups.objects.filter(admin_user_id__in=admin_user).values('user__username', 'admin_user__username')
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
    warehouse_name = request.POST.get('warehouse_name','')
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['wms_code'])):
        if not data_dict['wms_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        cond = (warehouse_name)
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['wms_code'][i], data_dict['order_quantity'][i], data_dict['price'][i],
                               data_id ])
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
                               'id': stock.id, 'warehouse_name': stock.warehouse.username })
    return HttpResponse(json.dumps({'data': all_data, 'warehouse': data_id}))

def validate_st(all_data, user):
    sku_status = ''
    other_status = ''
    price_status = ''
    wh_status = ''

    for key,value in all_data.iteritems():
        if not value:
            continue
        for val in value:
            sku = SKUMaster.objects.filter(wms_code = val[0], user=user.id)
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

@csrf_exempt
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
def confirm_st(request, user=''):
    all_data = {}
    warehouse_name = request.POST.get('warehouse_name','')
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['wms_code'])):
        if not data_dict['wms_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        cond = (warehouse_name)
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['wms_code'][i], data_dict['order_quantity'][i], data_dict['price'][i], data_id ])
    status = validate_st(all_data, user)
    if not status:
        all_data = insert_st(all_data, user)
        status = confirm_stock_transfer(all_data, user, warehouse_name)
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
    allowed_orders = list(OrdersAPI.objects.filter(order_type='po', user=user.id, status=0, engine_type=engine_type).\
                     values_list('order_id', flat=True)[:limit])

    all_pos = PurchaseOrder.objects.exclude(status='').filter(open_po__sku__user = user.id, order_id__in=allowed_orders)
    purchase_order = all_pos.values('order_id', 'open_po__creation_date', 'updation_date', 'open_po__supplier_id',
                                    'open_po__supplier__name').distinct().annotate(total=Sum('open_po__price'))
    for orders in purchase_order:
        po_data = OrderedDict(( ('order_id', orders['order_id']), ('order_date', str(orders['open_po__creation_date'].date()) ),
                                ('received_date', str(orders['updation_date'].date())), ('supplier_id', orders['open_po__supplier_id']),
                                ('supplier', orders['open_po__supplier__name']), ('total_invoice_amount', orders['total'])   ))


        del orders['total']
        orders_data = all_pos.filter(**orders)
        value = []
        for order in orders_data:
            po_reference = '%s%s_%s' %(order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order.order_id)
            value.append(OrderedDict(( ('sku_code', order.open_po.sku.sku_code),
                                    ('product_category', 'Electronic Item'), ('order_quantity', order.open_po.order_quantity),
                                    ('received_quantity', order.received_quantity), ('unit_price', order.open_po.price),
                                    ('status', order.status), ('received_date', str(order.updation_date.date())) )))

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

    allowed_orders = list(OrdersAPI.objects.filter(order_type='so', user=user.id, status=0, engine_type=engine_type).\
                     values_list('order_id', flat=True)[:limit])
    all_orders = OrderDetail.objects.filter(user=user.id, order_id__in=allowed_orders)
    order_detail = all_orders.order_by('-id').values('order_id', 'creation_date', 'shipment_date').distinct().\
                                              annotate(total_invoice_amount=Sum('invoice_amount'))
    OrdersAPI.objects.filter(order_type='so', user=user.id, order_id__in=allowed_orders).update(status=9)
    for order_dat in order_detail:
        orders_data = OrderedDict(( ('order_id', order_dat['order_id']), ('order_date', str(order_dat['creation_date'].date())),
                                         ('customer_name', 'Roopal Vegad'), ('ledger_name', 'Flipkart'), 
                                         ('shipment_date', str(order_dat['shipment_date'].date())), 
                                         ('total_invoice_amount', str(order_dat['total_invoice_amount']) )))
        del order_dat['total_invoice_amount']
        orders = all_orders.filter(**order_dat)
        value = []
        for order in orders:
            value.append(OrderedDict(( ('sku_code', order.sku.wms_code), ('title', order.title),
                                     ('quantity', order.quantity), ('shipment_date', order.shipment_date),
                                     ('invoice_amount', order.invoice_amount), ('tax_value', '10'), ('tax_percentage', '5.5'),
                                     ('order_date', str(order.creation_date.date()) ))))

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
        results.append(OrderedDict(( ('supplier_id', supplier.id), ('supplier_name', supplier.name), ('address', supplier.address),
                                     ('city', supplier.city), ('state', supplier.state) )))  
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
    for order_dat in order_data.get('ENVELOPE','').get('ORDERS', '').get('ORDER', ''):
        order_id = order_dat['ORDER_ID']['$']
        order_type = order_dat['ORDER_TYPE']['$'].lower()
        status = int(order_dat['STATUS']['$'])
        if order_id and order_type and status:
            OrdersAPI.objects.filter(engine_type=engine_type, order_type=order_type, order_id=order_id, user=user.id).update(status=status)
    return HttpResponse(json.dumps({'Status': 'Success', 'Message': 'Updated Successfully'}))

@csrf_exempt
@login_required
@get_admin_user
def confirm_add_po(request, sales_data = '', user=''):
    ean_flag = False
    po_order_id = ''
    status = ''
    suggestion = ''
    if not request.POST:
        return HttpResponse('Updated Successfully')
    sku_id = ''
    data = copy.deepcopy(PO_DATA)
    display_remarks = get_misc_value('display_remarks_mail', user.id)
    if not sales_data:
        po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).order_by("-order_id")
        if not po_data:
            po_id = 0
        else:
            po_id = po_data[0].order_id
    else:
        if sales_data['po_order_id'] == '':
            po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).order_by("-order_id")
            if not po_data:
                po_id = 0
            else:
                po_id = po_data[0].order_id
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
    ean_data = SKUMaster.objects.filter(wms_code__in=myDict['wms_code'],user=user.id).values_list('ean_number').exclude(ean_number=0)
    if ean_data:
        ean_flag = True

    all_data = get_raisepo_group_data(user, myDict)

    for key, value in all_data.iteritems():
        po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
        sku_id = SKUMaster.objects.filter(wms_code = key.upper(),user=user.id)

        ean_number = 0
        if sku_id:
            ean_number = int(sku_id[0].ean_number)

        if not sku_id:
            sku_id = SKUMaster.objects.filter(wms_code='TEMP',user=user.id)
            po_suggestions['wms_code'] = key.upper()

        if not value['order_quantity']:
            continue

        price = value['price']
        if not price:
            price = 0
        if not 'supplier_code' in myDict.keys() and value['supplier_id']:
            supplier = SKUSupplier.objects.filter(supplier_id=value['supplier_id'], sku__user=user.id)
            if supplier:
                supplier_code = supplier[0].supplier_code
        elif value['supplier_code']:
            supplier_code = value['supplier_code']
        supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=value['supplier_id'], sku__user=user.id)
        sku_mapping = {'supplier_id': value['supplier_id'], 'sku': sku_id[0], 'preference': 1, 'moq': 0, 'supplier_code': supplier_code, 'price': price, 'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}

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
        po_suggestions['sgst_tax'] = value['sgst_tax']
        po_suggestions['cgst_tax'] = value['cgst_tax']
        po_suggestions['igst_tax'] = value['igst_tax']
        po_suggestions['utgst_tax'] = value['utgst_tax']
        if value['measurement_unit']:
            if value['measurement_unit'] != "":
                po_suggestions['measurement_unit'] = value['measurement_unit']
        if value.get('vendor_id', ''):
            vendor_master = VendorMaster.objects.get(vendor_id=value['vendor_id'], user=user.id)
            po_suggestions['vendor_id'] = vendor_master.id
            po_suggestions['order_type'] = 'VR'

        data1 = OpenPO(**po_suggestions)
        data1.save()
        purchase_order = OpenPO.objects.get(id = data1.id,sku__user=user.id)
        sup_id = purchase_order.id

        supplier = purchase_order.supplier_id
        if supplier not in ids_dict and not po_order_id:
            po_id = po_id + 1
            ids_dict[supplier] = po_id
        if po_order_id:
            ids_dict[supplier] = po_id
        data['open_po_id'] = sup_id
        data['order_id'] = ids_dict[supplier]
        data['ship_to'] = value['ship_to']
        user_profile = UserProfile.objects.filter(user_id=user.id)
        if user_profile:
            data['prefix'] = user_profile[0].prefix
        order = PurchaseOrder(**data)
        order.save()
        if value['sellers']:
            for seller, seller_quan in value['sellers'].iteritems():
                SellerPO.objects.create(seller_id=seller, open_po_id=data1.id, seller_quantity=seller_quan[0],
                                        creation_date=datetime.datetime.now(), status=1, receipt_type=value['receipt_type'])

        amount = float(purchase_order.order_quantity) * float(purchase_order.price)
        tax = value['sgst_tax'] + value['cgst_tax'] + value['igst_tax'] + value['utgst_tax']
        if not tax:
            total += amount
        else:
            total += amount + ((amount/100) * float(tax))
        total_qty += purchase_order.order_quantity
        if purchase_order.sku.wms_code == 'TEMP':
            wms_code = purchase_order.wms_code
        else:
            wms_code = purchase_order.sku.wms_code

        po_temp_data = [wms_code, supplier_code, purchase_order.sku.sku_desc, purchase_order.order_quantity,po_suggestions['measurement_unit'],
                        purchase_order.price, amount, purchase_order.sgst_tax, purchase_order.cgst_tax, purchase_order.igst_tax,
                        purchase_order.utgst_tax]
        if ean_flag:
            po_temp_data.insert(1, ean_number)
        if display_remarks == 'true':
            po_temp_data.append(purchase_order.remarks)
        po_data.append(po_temp_data)
        suggestion = OpenPO.objects.get(id = sup_id,sku__user=user.id)
        setattr(suggestion, 'status', 0)
        suggestion.save()
        if sales_data and not status:
            return HttpResponse(str(order.id) + ',' + str(order.order_id) )
    if status and not suggestion:
        return HttpResponse(status)
    address = purchase_order.supplier.address
    address = '\n'.join(address.split(','))
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
    order_id =  ids_dict[supplier]
    supplier_email = purchase_order.supplier.email_id
    phone_no = purchase_order.supplier.phone_number
    gstin_no = purchase_order.supplier.tin_number
    order_date = get_local_date(request.user, order.creation_date)
    po_reference = '%s%s_%s' % (order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order_id)
    table_headers = ['WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Measurement Type', 'Unit Price', 'Amount',
                     'SGST(%)' , 'CGST(%)', 'IGST(%)', 'UTGST(%)']
    if ean_flag:
        table_headers.insert(1, 'EAN Number')
    if display_remarks == 'true':
        table_headers.append('Remarks')

    profile = UserProfile.objects.get(user=user.id)

    company_name = profile.company_name
    title = 'Purchase Order'
    receipt_type = request.GET.get('receipt_type', '')
    #if receipt_type == 'Hosted Warehouse':
    title = 'Stock Transfer Note'
    if request.POST.get('seller_id', '') and 'shproc' in str(request.POST.get('seller_id').split(":")[1]).lower():
        company_name = 'SHPROC Procurement Pvt. Ltd.'
        title = 'Purchase Order'

    data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id, 'telephone': str(telephone),
                 'name': name, 'order_date': order_date, 'total': total, 'po_reference': po_reference, 'user_name': request.user.username,
                 'total_qty': total_qty, 'company_name': company_name, 'location': profile.location, 'w_address': profile.address,
                 'company_name': company_name, 'vendor_name': vendor_name, 'vendor_address': vendor_address,
                 'vendor_telephone': vendor_telephone, 'receipt_type': receipt_type, 'title': title, 'gstin_no': gstin_no}

    t = loader.get_template('templates/toggle/po_download.html')
    rendered = t.render(data_dict)
    if get_misc_value('raise_po', user.id) == 'true':
        write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, phone_no, po_data, str(order_date).split(' ')[0], ean_flag=ean_flag)

    return render(request, 'templates/toggle/po_template.html', data_dict)

def write_and_mail_pdf(f_name, html_data, request, user, supplier_email, phone_no, po_data, order_date, ean_flag=False, internal=False, report_type='Purchase Order'):
    file_name = '%s.html' % f_name
    pdf_file = '%s.pdf' % f_name
    receivers = []
    internal_mail = MiscDetail.objects.filter(user=request.user.id, misc_type='Internal Emails')
    misc_internal_mail = MiscDetail.objects.filter(user=request.user.id, misc_type='internal_mail', misc_value='true')
    if misc_internal_mail and internal_mail:
        internal_mail = internal_mail[0].misc_value.split(",")
        receivers.extend(internal_mail)
    path = 'static/temp_files/'
    folder_check(path)
    file = open(path + file_name, "w+b")
    file.write(html_data)
    file.close()
    os.system("./phantom/bin/phantomjs ./phantom/examples/rasterize.js ./%s ./%s A4" % (path + file_name, path + pdf_file))

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
    if supplier_email or internal or internal_mail:
        send_mail_attachment(receivers, email_subject,email_body, files = [{'path': path + pdf_file, 'name': pdf_file}])

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
    po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).order_by('-order_id')
    if not po_data:
        po_id = 0
    else:
        po_id = po_data[0].order_id
    ids_dict = {}
    po_data = []
    total = 0
    total_qty = 0
    status_dict = {'Self Receipt': 'SR', 'Vendor Receipt': 'VR', 'Hosted Warehouse': 'HW'}
    myDict = dict(request.GET.iterlists())
    ean_flag = False
    display_remarks = get_misc_value('display_remarks_mail', user.id)
    for key, value in myDict.iteritems():
        for val in value:
            purchase_orders = OpenPO.objects.filter(supplier_id=val, status__in=['Manual', 'Automated'], order_type=status_dict[key],
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
                if not tax:
                    total += amount
                else:
                    total += amount + ((amount/100) * float(tax))
                total_qty += float(purchase_order.order_quantity)

                if purchase_order.sku.wms_code == 'TEMP':
                    wms_code = purchase_order.wms_code
                else:
                    wms_code = purchase_order.sku.wms_code

                supplier_code = ''
                sku_supplier = SKUSupplier.objects.filter(sku__user=user.id, supplier_id=purchase_order.supplier_id, sku_id=purchase_order.sku_id)
                if sku_supplier:
                    supplier_code = sku_supplier[0].supplier_code

                po_temp_data = [wms_code, supplier_code, purchase_order.sku.sku_desc, purchase_order.order_quantity,
                                purchase_order.sku.measurement_type, purchase_order.price, amount, purchase_order.sgst_tax,
                                purchase_order.cgst_tax, purchase_order.igst_tax,purchase_order.utgst_tax]
                if ean_flag:
                    po_temp_data.insert(1, purchase_order.sku.ean_number)
                if display_remarks == 'true':
                    po_temp_data.append(purchase_order.remarks)
                po_data.append(po_temp_data)

                suggestion = OpenPO.objects.get(id=data_id, sku__user=user.id)
                setattr(suggestion, 'status', 0)
                suggestion.save()

            address = purchase_orders[0].supplier.address
            address = '\n'.join(address.split(','))
            telephone = purchase_orders[0].supplier.phone_number
            name = purchase_orders[0].supplier.name
            supplier_email = purchase_orders[0].supplier.email_id
            gstin_no = purchase_orders[0].supplier.tin_number
            order_id =  ids_dict[supplier]
            order_date = get_local_date(request.user, order.creation_date)
            vendor_name = ''
            vendor_address = ''
            vendor_telephone = ''
            if purchase_order.order_type == 'VR':
                vendor_address = purchase_orders[0].vendor.address
                vendor_address = '\n'.join(vendor_address.split(','))
                vendor_name = purchase_orders[0].vendor.name
                vendor_telephone = purchase_orders[0].vendor.phone_number
            profile = UserProfile.objects.get(user=user.id)
            po_reference = '%s%s_%s' %(str(profile.prefix), str(order_date).split(' ')[0].replace('-', ''), order_id)
            #table_headers = ('WMS CODE', 'Supplier Name', 'Description', 'Quantity', 'Unit Price', 'Amount')

            table_headers = ['WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Measurement Type', 'Unit Price', 'Amount',
                                 'SGST(%)' , 'CGST(%)', 'IGST(%)', 'UTGST(%)']
            if ean_flag:
                table_headers.insert(1, 'EAN Number')
            if display_remarks == 'true':
                table_headers.append('Remarks')
            data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                         'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total,
                         'company_name': profile.company_name, 'location': profile.location, 'po_reference': po_reference,
                         'total_qty': total_qty, 'vendor_name': vendor_name, 'vendor_address': vendor_address,
                         'vendor_telephone': vendor_telephone, 'gstin_no': gstin_no}

            t = loader.get_template('templates/toggle/po_download.html')
            rendered = t.render(data_dict)
            if get_misc_value('raise_po', user.id) == 'true':
                write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, telephone, po_data, str(order_date).split(' ')[0], ean_flag=ean_flag)

    return render(request, 'templates/toggle/po_template.html', data_dict)

@csrf_exempt
@login_required
@get_admin_user
def delete_po_group(request, user=''):
    status_dict = dict(zip(PO_ORDER_TYPES.values(), PO_ORDER_TYPES.keys()))

    myDict = dict(request.GET.iterlists())
    for key, value in myDict.iteritems():
        for val in value:
            purchase_order = OpenPO.objects.filter(supplier_id=val, status__in=['Manual', 'Automated'], order_type=status_dict[key],
                                                   sku__user = user.id).delete()

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
        filter_params = {"imei_number": serial, "purchase_order__open_po__sku__user": user.id}
        if data_id:
            quality_check = QualityCheck.objects.filter(id=data_id)
            if quality_check:
                filter_params['purchase_order__open_po__sku__sku_code'] = quality_check[0].purchase_order.open_po.sku.sku_code
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
                po_mapping = POIMEIMapping.objects.filter(imei_number=imei, purchase_order__open_po__sku__user=user)
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

def get_return_seller_id(returns_id, user):
    ''' Returns Seller Master ID'''
    return_imei = ReturnsIMEIMapping.objects.filter(order_return_id=returns_id, order_return__sku__user=user.id)
    seller_id = ''
    if return_imei:
        order_imei = return_imei[0].order_imei
        if order_imei.po_imei and order_imei.po_imei.purchase_order and order_imei.po_imei.purchase_order.open_po:
            open_po_id = order_imei.po_imei.purchase_order.open_po_id
            seller_po = SellerPO.objects.filter(open_po_id=open_po_id, open_po__sku__user=user.id)
            if seller_po:
                seller_id = seller_po[0].seller_id
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
            seller_id = get_return_seller_id(returns_data.returns.id, user)
            stock_data = StockDetail.objects.filter(location_id=location_id[0].id, receipt_number=receipt_number, sku_id=sku_id,
                                                    sku__user=user.id)
            if stock_data:
                stock_data = stock_data[0]
                setattr(stock_data, 'quantity', float(stock_data.quantity) + quantity)
                stock_data.save()
                stock_id = stock_data.id
                mod_locations.append(stock_data.location.location)
            else:
                stock_dict = {'location_id': location_id[0].id, 'receipt_number': receipt_number, 'receipt_date': datetime.datetime.now(),
                              'sku_id':sku_id, 'quantity': quantity, 'status': 1,
                              'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}
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
                    seller_stock_dict = {'seller_id': seller_id, 'stock_id': stock_id, 'quantity': quantity, 'status': 1,
                                         'creation_date': datetime.datetime.now()}
                    seller_stock = SellerStock(**seller_stock_dict)
                    seller_stock.save()
                if seller_stock.stock.location.zone.zone not in ['DAMAGED_ZONE']:
                    marketplace_data.append({'sku_code' : str(seller_stock.stock.sku.sku_code),
                                             'seller_id': int(seller_stock.seller.seller_id), 'quantity' : int(quantity)})
            returns_data.quantity = float(returns_data.quantity) - float(quantity)
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
    purchase_order = PurchaseOrder.objects.filter(order_id=po_order[0].order_id, open_po__sku__wms_code=myDict['wms_code'][i], open_po__sku__user=user.id)
    if purchase_order:
        myDict['id'][i] = purchase_order[0].id
    else:
        if po_order:
            po_order_id = po_order[0].order_id
        new_data = {'supplier_id': [myDict['supplier_id'][i]], 'wms_code': [myDict['wms_code'][i]],
                     'order_quantity': [myDict['po_quantity'][i]], 'price': [myDict['price'][i]], 'po_order_id': po_order_id}
        get_data = confirm_add_po(request, new_data)
        get_data = get_data.content
        myDict['id'][i] = get_data.split(',')[0]
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
        stock_instance = VendorStock.objects.filter(sku_id=sku_master.id, receipt_number=receipt_number, vendor_id=data.open_po.vendor_id)
        if not stock_instance:
            stock_dict = {'receipt_number': receipt_number, 'receipt_date': datetime.datetime.now(), 'quantity': float(value), 'status': 1, 'creation_date': datetime.datetime.now(),
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
        temp = re.findall('\d+',order_id)
        if temp:
            search_params['order_id'] = temp[-1]
    if p_index:
        search_params['order_id__gt'] = p_index
    
    stages = OrderedDict(( ('', 'PO Raised'), ('grn-generated', 'Goods Received'), ('qc', 'Quality Check'), ('location-assigned', 'Putaway') ))   
    order_stages = OrderedDict(( ('confirmed', 'Order Confirmed'), ('open', 'Picklist Generated'), ('picked', 'Ready to Ship') ))
    if not get_permission(request.user,'add_qualitycheck'):
        del stages['qc']
    open_po_ids = PurchaseOrder.objects.filter(**search_params).order_by('order_id').values_list('order_id', flat=True)
    for open_po_id in open_po_ids[:20]:
        total = 0
        temp_data = []
        ind = len(stages) - 1
        po_data = PurchaseOrder.objects.exclude(status='confirmed-putaway').filter(order_id=open_po_id, open_po__sku__user=user.id)
        for dat in po_data:
            total += int(dat.open_po.order_quantity) * float(dat.open_po.price)
            if dat.status in stages.keys():
                temp = int(stages.values().index(stages[dat.status])) + 1
                if dat.status == 'grn-generated':
                    qc_check = QualityCheck.objects.filter(purchase_order__order_id=open_po_id,
                                                           purchase_order__open_po__sku__user=user.id, status='qc_pending')
                    if qc_check:
                        temp = 2 + 1
            if temp < ind:
                ind = temp
            temp_data.append({'name': dat.open_po.supplier.name, 'image_url': dat.open_po.sku.image_url,
                              'order': dat.prefix + '_' + str(dat.creation_date.strftime("%d%m%Y")) + '_' + str(dat.order_id),
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
    pic_orders = Picklist.objects.order_by('-order__order_id').exclude(status__icontains='picked').filter(**search_params1).\
                                  distinct().values_list('order__order_id', flat=True)
    orders = list(chain(con_orders, pic_orders))[:20]
    for order in orders:
        temp_data = []
        ind = ''
        view_order = OrderDetail.objects.filter(order_id=order, user=user.id)
        invoice = OrderDetail.objects.filter(user=user.id, order_id=order).\
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
                picklist = Picklist.objects.filter(order__user=user.id,order__order_id=order, status__icontains='open')
                ind = 3
                if picklist:
                    ind = 2
                continue

        stage = get_stage_index(order_stages, ind)
        open_orders.append({'order': order, 'invoice': invoice, 'order_data': temp_data, 'stage': stage, 'index': order})
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
        master_data = CancelledLocation.objects.filter(picklist__order__sku_id__in=sku_master_ids).\
                                                filter(Q(picklist__order__order_id__icontains=search_term) |
                                                       Q(picklist__order__sku__sku_desc__icontains=search_term) |
                                                       Q(picklist__order__sku__wms_code__icontains=search_term) |
                                                       Q(quantity__icontains=search_term) |
                                                       Q(location__zone__zone__icontains=search_term) |
                                                       Q(location__location__icontains=search_term),
                                                       picklist__order__user = user.id , status=1, quantity__gt=0)
    elif order_term:
        col_num = col_num - 1
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = CancelledLocation.objects.filter(picklist__order__sku__user = user.id, status=1, quantity__gt=0,
                                                       picklist__order__sku_id__in=sku_master_ids).order_by(order_data)
    else:
        master_data = CancelledLocation.objects.filter(picklist__order__sku__user = user.id, status=1, quantity__gt=0,
                                                       picklist__order__sku_id__in=sku_master_ids).order_by('-creation_date')
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
                                    'Product Description': data.picklist.order.sku.sku_desc, 'Zone': zone, 'Location': location,
                                    'Quantity': quantity, 'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.id}, 'id':count})
        count = count+1

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
        cancelled_data =cancelled_data[0]
        if location and zone and quantity:
            location_id = LocationMaster.objects.filter(location=location, zone__zone=zone)
            if not location_id:
                status = "Zone, location match doesn't exists"
        else:
            status = 'Missing zone or location or quantity'
        if not status:
            sku_id = cancelled_data.picklist.stock.sku_id
            stock_data = StockDetail.objects.filter(location_id=location_id[0].id, receipt_number=receipt_number, sku_id=sku_id,
                                                    sku__user=user.id)
            if stock_data:
                stock_data = stock_data[0]
                setattr(stock_data, 'quantity', float(stock_data.quantity) + quantity)
                stock_data.save()
                new_stock = stock_data
                mod_locations.append(stock_data.location.location)
            else:
                stock_dict = {'location_id': location_id[0].id, 'receipt_number': receipt_number, 'receipt_date': datetime.datetime.now(),
                              'sku_id':sku_id, 'quantity': quantity, 'status': 1,
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
    total_taxes = {'cgst_amt': 0, 'sgst_amt': 0, 'igst_amt': 0, 'utgst_amt': 0}
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
    gstin_no = GSTIN_USER_MAPPING.get(user.username, '')
    taxes_dict = {}
    total_taxable_amt = 0
    for data_id in seller_summary_dat:
        splitted_data = data_id.split(':')
        sell_ids.setdefault('purchase_order__order_id__in', [])
        sell_ids.setdefault('receipt_number__in', [])
        #sell_ids.setdefault('seller_po__seller__name', [])
        sell_ids['purchase_order__order_id__in'].append(splitted_data[0])
        sell_ids['receipt_number__in'].append(splitted_data[1])
        #sell_ids['seller_po__seller__name'].append(splitted_data[2])
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
        utgst_tax = seller_po_summary.seller_po.open_po.utgst_tax
        cgst_amt = cgst_tax * (float(amt)/100)
        sgst_amt = sgst_tax * (float(amt)/100)
        igst_amt = igst_tax * (float(amt)/100)
        utgst_amt = utgst_tax * (float(amt)/100)
        total_taxes['cgst_amt'] += cgst_amt
        total_taxes['sgst_amt'] += sgst_amt
        total_taxes['igst_amt'] += igst_amt
        total_taxes['utgst_amt'] += utgst_amt
        tax = cgst_amt + sgst_amt + igst_amt + utgst_amt
        taxes_dict = {'cgst_tax': cgst_tax, 'sgst_tax': sgst_tax, 'igst_tax': igst_tax, 'utgst_tax': utgst_tax,
                      'cgst_amt': '%.2f' % cgst_amt, 'sgst_amt': '%.2f' % sgst_amt, 'igst_amt': '%.2f' % igst_amt,
                      'utgst_amt': utgst_amt}
        invoice_amount = amt + tax - discount

        total_tax += float(tax)
        total_mrp += float(mrp_price)

        unit_price = mrp_price
        unit_price = "%.2f" % unit_price

        #Adding Totals for Invoice
        total_invoice += invoice_amount
        total_quantity += quantity
        total_taxable_amt += amt

        cond = (open_po.sku.sku_code)

        hsn_code = ''
        if open_po.sku.hsn_code:
            hsn_code = str(open_po.sku.hsn_code)
        all_data.setdefault(cond, {'order_id': po_number, 'sku_code': open_po.sku.sku_code, 'title': open_po.sku.sku_desc,
                                   'invoice_amount': 0, 'quantity': 0, 'tax': 0, 'unit_price': unit_price, 'amt': 0,
                                   'mrp_price': mrp_price, 'discount': discount, 'sku_class': open_po.sku.sku_class,
                                   'sku_category': open_po.sku.sku_category, 'sku_size': open_po.sku.sku_size, 'hsn_code': hsn_code,
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
                    'invoice_no': invoice_no, 'invoice_date': invoice_date, 'price_in_words': number_in_words(total_invoice),
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
    imei =  request.GET['imei']
    qc_data = []
    sku_data = {}
    image = ''
    status = ''
    log.info(request.GET.dict())
    try:
        if imei:
            filter_params = {"imei_number": imei, "purchase_order__open_po__sku__user": user.id, "status": 1}
            po_mapping = {}
            quality_check = {}
            if order_id:
                quality_check_data = QualityCheck.objects.filter(purchase_order__order_id=order_id,purchase_order__open_po__sku__user=user.id)
                if quality_check_data:
                    for data in quality_check_data:
                        filter_params['purchase_order__open_po__sku__sku_code'] = data.purchase_order.open_po.sku.sku_code
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
                                                         quality_check__purchase_order__open_po__sku__user=user.id, serial_number__status=1)
            if qc_mapping:
                status = "Quality Check completed for imei number " + str(imei)
            if quality_check:
                purchase_data = get_purchase_order_data(quality_check.purchase_order)
                sku = purchase_data['sku']
                image = sku.image_url
                po_reference = '%s%s_%s' % (quality_check.purchase_order.prefix, str(quality_check.purchase_order.creation_date).\
                                           split(' ')[0].replace('-', ''), quality_check.purchase_order.order_id)
                qc_data.append({'id': quality_check.id,'order_id': po_reference,
                                'quantity': quality_check.po_location.quantity, 'accepted_quantity': quality_check.accepted_quantity,
                                'rejected_quantity': quality_check.rejected_quantity})
                sku_data = OrderedDict( ( ('SKU Code', sku.sku_code), ('Product Description', sku.sku_desc),
                                          ('SKU Brand', sku.sku_brand), ('SKU Category', sku.sku_category), ('SKU Class', sku.sku_class),
                                          ('Color', sku.color) ))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(e)
        return HttpResponse("Internal Server Error")
    return HttpResponse(json.dumps({'data_dict': qc_data, 'sku_data': sku_data, 'image': image,
                                    'options': REJECT_REASONS, 'status':status}))

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
            order_imei = OrderIMEIMapping.objects.filter(po_imei__imei_number=value, order__user=user.id, status=1)
            if not order_imei:
                return_data['status'] = 'Imei Number is invalid'
            else:
                return_mapping = ReturnsIMEIMapping.objects.filter(order_imei_id=order_imei[0].id, order_return__sku__user=user.id, status=1)
                if return_mapping:
                    return_data['status'] = 'Imei number is mapped with the return id %s' % str(return_mapping[0].order_return.return_id)
                    break
                return_data['status'] = 'Success'
                invoice_number = ''
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
                                       'order_id': order_id, 'sku_desc': order_imei[0].order.title, 'shipping_quantity': 1,
                                       'sor_id': order_imei[0].sor_id, 'quantity': 0, 'order_imei_id': order_imei_id}
                order_return = OrderReturns.objects.filter(order_id=order_imei[0].order.id, sku__user=user.id, status=1)
                if order_return:
                    return_data['data'].update({'id': order_return[0].id, 'return_id': order_return[0].return_id,
                                                'return_type': order_return[0].return_type, 'sor_id': '', 'quantity': order_return[0].quantity})
                log.info(return_data)
        #if user_profile.user_type == 'marketplace_user' and not return_data['data'].get('id', ''):
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
    headers = ('WMS CODE', 'Order Quantity', 'Received Quantity', 'Measurement', 'Unit Price', 'CSGT(%)', 'SGST(%)', 'IGST(%)', 'UTGST(%)', 'Amount')
    putaway_data = {headers: []}
    total_received_qty = 0
    total_order_qty = 0
    total_price = 0
    pallet_number = ''
    is_putaway = ''
    purchase_data = ''
    btn_class = ''
    seller_name = user.username
    myDict = dict(request.POST.iterlists())

    log.info('Request params for ' + user.username + ' is ' + str(myDict))
    try:
        for ind in range(0, len(myDict['id'])):
            myDict.setdefault('imei_number', [])
            imeis_list = [im.split('<<>>')[0] for im in (myDict['rejected'][ind]).split(',')] + myDict['accepted'][ind].split(',')
            myDict['imei_number'].append(','.join(imeis_list))
        po_data, status_msg, all_data, order_quantity_dict, purchase_data, data, data_dict = generate_grn(myDict, request, user, is_confirm_receive=True)
        for i in range(0, len(myDict['id'])):
            quality_checks = QualityCheck.objects.filter(purchase_order_id=myDict['id'][i], po_location__location__zone__user=user.id,
                                                          status='qc_pending')

            for quality_check in quality_checks:
                qc_dict = {'id': [quality_check.id], 'unit': [myDict['unit'][i]], 'accepted': [myDict['accepted'][i]],
                           'rejected': [myDict['rejected'][i]], 'accepted_quantity': [myDict['accepted_quantity'][i]],
                           'rejected_quantity': [myDict['rejected_quantity'][i]], 'reason': ['']}
                update_quality_check(qc_dict, request, user)

                if myDict.get("accepted",''):
                    save_qc_serials('accepted', [myDict.get("accepted",'')[i]], user.id, qc_id=quality_check.id)
                if myDict.get("rejected",''):
                    save_qc_serials('rejected', [myDict.get("rejected",'')[i]], user.id, qc_id=quality_check.id)

        for key, value in all_data.iteritems():
            entry_price = float(key[3]) * float(value)
            entry_tax = float(key[4]) + float(key[5]) + float(key[6]) + float(key[7])
            if entry_tax:
                entry_price += (float(entry_price)/100) * entry_tax
            putaway_data[headers].append((key[1], order_quantity_dict[key[0]], value, key[2], key[3], key[4], key[5], key[6], key[7], entry_price))
            total_order_qty += order_quantity_dict[key[0]]
            total_received_qty += value
            total_price += entry_price

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

            profile = UserProfile.objects.get(user=user.id)
            po_reference = '%s%s_%s' % (data.prefix, str(data.creation_date).split(' ')[0].replace('-', ''), order_id)
            table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Ordered Quantity', 'Received Quantity', 'Amount')
            '''report_data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                                'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total_price,
                                'po_reference': po_reference, 'total_qty': total_received_qty,
                                'report_name': 'Goods Receipt Note', 'company_name': profile.company_name, 'location': profile.location}'''
            report_data_dict = {'data': putaway_data, 'data_dict': data_dict,
                                   'total_received_qty': total_received_qty, 'total_order_qty': total_order_qty, 'total_price': total_price,
                                   'seller_name': seller_name, 'company_name': profile.company_name,
                                   'po_number': str(data.prefix) + str(data.creation_date).split(' ')[0] + '_' + str(data.order_id),
                                   'order_date': get_local_date(request.user, data.creation_date), 'order_id': order_id, 'btn_class': btn_class}

            misc_detail = get_misc_value('receive_po', user.id)
            if misc_detail == 'true':
                t = loader.get_template('templates/toggle/grn_form.html')
                rendered = t.render(report_data_dict)
                write_and_mail_pdf(po_reference, rendered, request, user, supplier_email, telephone, po_data, str(order_date), internal=True, report_type="Goods Receipt Note")
            return render(request, 'templates/toggle/putaway_toggle.html', report_data_dict)
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
        max_serial = POLabels.objects.filter(sku__user=user.id).aggregate(Max('serial_number'))['serial_number__max']
        if max_serial:
            serial_number = int(max_serial) + 1
        all_st_purchases = STPurchaseOrder.objects.filter(po__order_id=order_id, open_st__sku__user=user.id)
        all_rw_orders = RWPurchase.objects.filter(purchase_order__order_id=order_id, rwo__vendor__user=user.id)
        po_ids = all_st_purchases.values_list('po_id', flat=True)
        rw_po_ids = all_rw_orders.values_list('purchase_order_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(Q(id__in=po_ids) | Q(id__in=rw_po_ids) | Q(open_po__sku__user=user.id), order_id=order_id)
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
                label_dict = {'purchase_order_id': order.id, 'serial_number': serial_number, 'label': label, 'status': 1,
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
            elif not int(po_labels[0].purchase_order.order_id) == int(order_id):
                status = {'message': 'Serial Number is mapped with PO Number ' + get_po_reference(po_labels[0].purchase_order), 'data': {}}
            elif int(po_labels[0].status) == 0:
                status = {'message': 'Serial Number already mapped with ' + get_po_reference(po_labels[0].purchase_order), 'data': {}}
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
