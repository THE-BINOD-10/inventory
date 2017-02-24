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
    status_dict = {'SR': 'Self Receipt', 'VR': 'Vendor Receipt'}
    for result in results[start_index: stop_index]:
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (result['supplier_id'], result['supplier__name'])
        temp_data['aaData'].append(OrderedDict(( ( '', checkbox), ('Supplier ID', result['supplier_id']),
                                                 ('Supplier Name', result['supplier__name']), ('Total Quantity', result['total']),
                                                 ('Order Type', status_dict[result['order_type']]), ('id', count),
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


def get_purchase_order_data(order):
    order_data = {}
    if 'job_code' in dir(order):
        order_data = {'wms_code': order.product_code.wms_code, 'sku_group': order.product_code.sku_group }
        return order_data
    elif order.open_po:
        open_data = order.open_po
        user_data = order.open_po.supplier
        address = user_data.address
        email_id = user_data.email_id
        username = user_data.name
        order_quantity = open_data.order_quantity
    else:
        st_order = STPurchaseOrder.objects.filter(po_id=order.id)
        st_picklist = STOrder.objects.filter(stock_transfer__st_po_id=st_order[0].id)
        open_data = st_order[0].open_st
        user_data = UserProfile.objects.get(user_id=st_order[0].open_st.warehouse_id)
        address = user_data.location
        email_id = user_data.user.email
        username = user_data.user.username
        order_quantity = open_data.order_quantity


    order_data = {'order_quantity': order_quantity, 'price': open_data.price, 'wms_code': open_data.sku.wms_code,
                  'sku_code': open_data.sku.wms_code, 'supplier_id': user_data.id, 'zone': open_data.sku.zone,
                  'qc_check': open_data.sku.qc_check, 'supplier_name': username,
                  'sku_desc': open_data.sku.sku_desc, 'address': address,
                  'phone_number': user_data.phone_number, 'email_id': email_id,
                  'sku_group': open_data.sku.sku_group, 'sku_id': open_data.sku.id, 'sku': open_data.sku }

    return order_data

@csrf_exempt
def get_confirmed_po(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['PO Number', 'Order Date', 'Supplier ID', 'Supplier Name', 'Order Type', 'Receive Status']
    data_list = []
    data = []
    supplier_data = {}
    col_num1 = 0
    if search_term:
        results = PurchaseOrder.objects.filter(open_po__sku_id__in=sku_master_ids).filter(Q(open_po__supplier_id__id = search_term) |
                                                Q(open_po__supplier__name__icontains = search_term)
                                               |Q( order_id__icontains = search_term ) | Q(creation_date__regex=search_term),
                                              open_po__sku__user=user.id, received_quantity__lt=F('open_po__order_quantity')).\
                                        exclude(status__in=['location-assigned','confirmed-putaway']).\
                                        values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__open_po__isnull=True).exclude(po__status__in=['location-assigned',
                                                        'confirmed-putaway', 'stock-transfer']).filter(open_st__sku_id__in=sku_master_ids).\
                                                filter(Q(open_st__warehouse__id__icontains = search_term) |
                                                       Q(open_st__warehouse__username__icontains = search_term) |
                                                       Q(po__order_id__icontains = search_term ) | Q(po__creation_date__regex=search_term),
                                                       open_st__sku__user=user.id,
                                                       po__received_quantity__lt=F('open_st__order_quantity')).\
                                                values_list('po__order_id', flat=True).distinct()
        rw_results = RWPurchase.objects.exclude(purchase_order__open_po__isnull=True).exclude(purchase_order__status__in=['location-assigned',
                                                'confirmed-putaway', 'stock-transfer']).filter(rwo__job_order__product_code_id__in=sku_master_ids).\
                                                filter(Q(rwo__vendor__id__icontains = search_term) |
                                                       Q(rwo__vendor__name__icontains = search_term) |
                                                       Q(purchase_order__creation_date__regex=search_term) |
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
        data_list.append({'DT_RowId': supplier.order_id, 'PO Number': po_reference,
                          'Order Date': get_local_date(request.user, supplier.creation_date),
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
        qc_results = QualityCheck.objects.filter(purchase_order_id__in=stock_results, status='qc_pending', putaway_quantity__gt=0,
                                                 po_location__location__zone__user = user.id)

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
        results = QualityCheck.objects.filter(Q(purchase_order__open_po__sku_id__in=sku_master_ids) | Q(purchase_order_id__in=stock_results)).\
                                       filter(status='qc_pending', putaway_quantity__gt=0, po_location__location__zone__user = user.id,
                                              **qc_filters)
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
                                                  Q(order__order_id__icontains=order_id_search), status=1, order__user=user.id)
    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            master_data = OrderReturns.objects.filter(order__user=user.id, status=1).order_by(lis[col_num])
        else:
            master_data = OrderReturns.objects.filter(order__user=user.id, status=1).order_by('-%s' % lis[col_num])
    else:
        master_data = OrderReturns.objects.filter(order__user=user.id, status=1).order_by('return_date')
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
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
@login_required
@get_admin_user
def generated_po_data(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    status_dict = {'Self Receipt': 'SR', 'Vendor Receipt': 'VR'}
    send_message = 'true'
    data = MiscDetail.objects.filter(user = request.user.id, misc_type='send_message')
    if data:
        send_message = data[0].misc_value

    generated_id = request.GET['supplier_id']
    record = OpenPO.objects.filter(Q(supplier_id=generated_id, status='Manual') | Q(supplier_id=generated_id, status='Automated'),
                                     sku__user = user.id, order_type=status_dict[request.GET['order_type']], sku_id__in=sku_master_ids)

    total_data = []
    status_dict = {'SR': 'Self Receipt', 'VR': 'Vendor Receipt'}
    ser_data = json.loads(serializers.serialize("json", record, indent=3, use_natural_foreign_keys=True, fields = ('supplier_code', 'sku', 'order_quantity', 'price', 'remarks')))
    vendor_id = ''
    if record[0].vendor:
        vendor_id = record[0].vendor.vendor_id
    return HttpResponse(json.dumps({'send_message': send_message, 'supplier_id': record[0].supplier_id, 'vendor_id': vendor_id,
                                    'Order Type': status_dict[record[0].order_type], 'po_name': record[0].po_name, 'ship_to': '',
                                    'data': ser_data}))

@login_required
@get_admin_user
def validate_wms(request, user=''):
    myDict = dict(request.GET.iterlists())
    wms_list = ''
    supplier_master = SupplierMaster.objects.filter(id=myDict['supplier_id'][0], user=user.id)
    if not supplier_master:
        return HttpResponse("Invalid Supplier " + myDict['supplier_id'][0])
    if myDict.get('vendor_id', ''):
        vendor_master = VendorMaster.objects.filter(vendor_id=myDict['vendor_id'][0], user=user.id)
        if not vendor_master:
            return HttpResponse("Invalid Vendor " + myDict['vendor_id'][0])
    for i in range(0, len(myDict['wms_code'])):
        if not myDict['wms_code'][i]:
            continue
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
    myDict = dict(request.GET.iterlists())
    wrong_wms = []
    for i in range(0,len(myDict['wms_code'])):

        wms_code = myDict['wms_code'][i]
        if not wms_code:
            continue

        data_id = ''
        if i < len(myDict['data-id']):
            data_id = myDict['data-id'][i]
        if data_id:
            record = OpenPO.objects.get(id=data_id,sku__user=user.id)
            setattr(record, 'order_quantity', myDict['order_quantity'][i] )
            setattr(record, 'price', myDict['price'][i] )
            setattr(record, 'remarks', myDict['remarks'][i])
            record.save()
            continue

        sku_id = SKUMaster.objects.filter(wms_code=wms_code.upper(),user=user.id)
        po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
        if not sku_id:
            sku_id = sku_id = SKUMaster.objects.filter(wms_code='TEMP',user=user.id)
            po_suggestions['wms_code'] = wms_code.upper()
        if not sku_id[0].wms_code == 'TEMP':
            supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=myDict['supplier_id'][0], sku__user=user.id)
            sku_mapping = {'supplier_id': myDict['supplier_id'][0], 'sku': sku_id[0], 'preference': 1, 'moq': 0,
                           'supplier_code': myDict['supplier_code'][i], 'price': myDict['price'][i], 'creation_date': datetime.datetime.now(),
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
        po_suggestions['supplier_id'] = myDict['supplier_id'][0]
        po_suggestions['order_quantity'] = myDict['order_quantity'][i]
        if not myDict['price'][i]:
            myDict['price'][i] = 0
        po_suggestions['price'] = float(myDict['price'][i])
        po_suggestions['status'] = 'Manual'
        po_suggestions['remarks'] = myDict['remarks'][i]

        data = OpenPO(**po_suggestions)
        data.save()

    status_msg="Updated Successfully"
    return HttpResponse(status_msg)

@csrf_exempt
@get_admin_user
def switches(request, user=''):

    toggle_data = { 'fifo_switch': request.GET.get('fifo_switch', ''),
                    'batch_switch': request.GET.get('batch_switch', ''),
                    'send_message': request.GET.get('send_message', ''),
                    'show_image': request.GET.get('show_image', ''),
                    'stock_sync': request.GET.get('sync_switch', ''),
                    'back_order': request.GET.get('back_order', ''),
                    'online_percentage': request.GET.get('online_percentage', ''),
                    'use_imei': request.GET.get('use_imei', ''),
                    'pallet_switch': request.GET.get('pallet_switch', ''),
                    'production_switch': request.GET.get('production_switch', ''),
                    'mail_alerts': request.GET.get('mail_alerts', ''),
                    'invoice_prefix': request.GET.get('invoice_prefix', ''),
                    'pos_switch': request.GET.get('pos_switch', ''),
                    'auto_po_switch': request.GET.get('auto_po_switch', ''),
                    'no_stock_switch': request.GET.get('no_stock_switch', ''),
                    'float_switch': request.GET.get('float_switch', ''),
                    'automate_invoice': request.GET.get('automate_invoice', ''),
                    'show_mrp': request.GET.get('show_mrp', ''),
                    'decimal_limit': request.GET.get('decimal_limit', ''),
                    'picklist_sort_by': request.GET.get('picklist_sort_by', ''),
                    'stock_sync': request.GET.get('stock_sync', ''),
                    'sku_sync': request.GET.get('sku_sync', ''),
                    'auto_generate_picklist': request.GET.get('auto_generate_picklist', ''),
                    'order_headers' : request.GET.get('order_headers', ''),
                    'detailed_invoice' : request.GET.get('detailed_invoice', '')
                  }

    toggle_field, selection = "", ""
    for key, value in toggle_data.iteritems():
        if not value:
            continue

        toggle_field = key
        selection = value
        break

    user_id = user.id
    if toggle_field == 'invoice_prefix':
        user_profile = UserProfile.objects.filter(user_id=user_id)
        if user_profile and selection:
            setattr(user_profile[0], 'prefix', selection)
            user_profile[0].save()
    else:
        data = MiscDetail.objects.filter(misc_type=toggle_field, user=user_id)
        if not data:
            misc_detail = MiscDetail(user=user_id, misc_type=toggle_field, misc_value=selection, creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now())
            misc_detail.save()
        else:
            setattr(data[0], 'misc_value', selection)
            data[0].save()
        if toggle_field == 'sku_sync' and value == 'true':
            insert_skus(user.id)

    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def confirm_po(request, user=''):
    sku_id = ''
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
    myDict = dict(request.GET.iterlists())
    for i in range(0, len(myDict['wms_code'])):
        price = 0
        if myDict['price'][i]:
            price = myDict['price'][i]
        if i < len(myDict['data-id']) and myDict['data-id'][i]:
            purchase_order = OpenPO.objects.get(id=myDict['data-id'][i], sku__user=user.id)
            sup_id = myDict['data-id'][i]
            setattr(purchase_order, 'order_quantity', myDict['order_quantity'][i])
            setattr(purchase_order, 'price', myDict['price'][i])
            setattr(purchase_order, 'po_name', myDict['po_name'][0])
            setattr(purchase_order, 'supplier_code', myDict['supplier_code'][i])
            setattr(purchase_order, 'remarks', myDict['remarks'][i])
            if myDict.get('vendor_id', ''):
                vendor_master = VendorMaster.objects.get(vendor_id=myDict['vendor_id'][0], user=user.id)
                setattr(purchase_order, 'vendor_id', vendor_master.id)
                setattr(purchase_order, 'order_type', 'VR')
            purchase_order.save()
        else:
            sku_id = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user=user.id)
            po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
            if not sku_id:
                sku_id = SKUMaster.objects.filter(wms_code='TEMP', user=user.id)
                po_suggestions['wms_code'] = myDict['wms_code'][i].upper()
                po_suggestions['supplier_code'] = myDict['supplier_code'][i]
                if not sku_id[0].wms_code == 'TEMP':
                    supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=myDict['supplier_id'][0], sku__user=user.id)
                    sku_mapping = {'supplier_id': myDict['supplier_id'][0], 'sku': sku_id[0], 'preference': 1, 'moq': 0,
                                   'supplier_code': myDict['supplier_code'][i], 'price': price, 'creation_date': datetime.datetime.now(),
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
            po_suggestions['supplier_id'] = myDict['supplier_id'][0]
            po_suggestions['order_quantity'] = float(myDict['order_quantity'][i])
            po_suggestions['price'] = float(price)
            po_suggestions['status'] = 'Manual'
            po_suggestions['remarks'] = myDict['remarks'][i]
            if myDict.get('vendor_id', ''):
                vendor_master = VendorMaster.objects.get(vendor_id=myDict['vendor_id'][0], user=user.id)
                po_suggestions['vendor_id'] = vendor_master.id
                po_suggestions['order_type'] = 'VR'

            data1 = OpenPO(**po_suggestions)
            data1.save()
            purchase_order = OpenPO.objects.get(id=data1.id, sku__user=user.id)
            sup_id = purchase_order.id
        supplier = purchase_order.supplier_id
        if supplier not in ids_dict:
            po_id = po_id + 1
            ids_dict[supplier] = po_id
        data['open_po_id'] = sup_id
        data['order_id'] = ids_dict[supplier]
        data['ship_to'] = myDict['ship_to'][0]
        user_profile = UserProfile.objects.filter(user_id=user.id)
        if user_profile:
            data['prefix'] = user_profile[0].prefix
        order = PurchaseOrder(**data)
        order.save()

        amount = float(purchase_order.order_quantity) * float(purchase_order.price)
        total += amount

        total_qty += float(purchase_order.order_quantity)

        if purchase_order.sku.wms_code == 'TEMP':
            wms_code = purchase_order.wms_code
        else:
            wms_code = purchase_order.sku.wms_code
        po_data.append((wms_code, myDict['supplier_code'][i], purchase_order.sku.sku_desc, purchase_order.order_quantity,
                        purchase_order.price, amount, purchase_order.remarks))
        suggestion = OpenPO.objects.get(id=sup_id, sku__user=user.id)
        setattr(suggestion, 'status', 0)
        suggestion.save()

    address = purchase_order.supplier.address
    address = '\n'.join(address.split(','))
    telephone = purchase_order.supplier.phone_number
    name = purchase_order.supplier.name
    supplier_email = purchase_order.supplier.email_id
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

    profile = UserProfile.objects.get(user=request.user.id)
    table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Unit Price', 'Amount', 'Remarks')
    data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id, 'telephone': str(telephone),
                 'name': name, 'order_date': order_date, 'total': total, 'po_reference': po_reference, 'company_name': profile.company_name,
                 'location': profile.location, 'vendor_name': vendor_name, 'vendor_address': vendor_address,
                 'vendor_telephone': vendor_telephone, 'total_qty': total_qty}
    t = loader.get_template('templates/toggle/po_download.html')
    c = Context(data_dict)
    rendered = t.render(c)
    send_message = 'false'
    data = MiscDetail.objects.filter(user=user.id, misc_type='send_message')
    if data:
        send_message = data[0].misc_value
    if send_message == 'true':
        write_and_mail_pdf(po_reference, rendered, request, supplier_email, telephone, po_data, str(order_date).split(' ')[0])

    return render(request, 'templates/toggle/po_template.html', data_dict)

@csrf_exempt
@login_required
@get_admin_user
def raise_po_toggle(request, user=''):
    send_message = 'true'
    data = MiscDetail.objects.filter(user=user.id, misc_type='send_message')
    if data:
        send_message = data[0].misc_value
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
    sku_supplier = SKUSupplier.objects.filter(sku__wms_code=wms_code, supplier_id=supplier_id, sku__user=user.id)
    data = {}
    if sku_supplier:
        data['supplier_code'] = sku_supplier[0].supplier_code
        data['price'] = sku_supplier[0].price

    return HttpResponse(json.dumps(data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def add_po(request, user=''):
    status = 'Failed to Add PO'
    myDict = dict(request.GET.iterlists())
    for i in range(0,len(myDict['wms_code'])):
        wms_code = myDict['wms_code'][i]
        if not wms_code:
            continue
        pri = myDict['price'][i]
        if not pri:
            myDict['price'][i] = 0

        sku_id = SKUMaster.objects.filter(wms_code=wms_code.upper(),user=user.id)
        if not sku_id:
            status = 'Invalid WMS CODE'
            return HttpResponse(status)

        po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)

        supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=myDict['supplier_id'][0],sku__user=user.id)
        sku_mapping = {'supplier_id': myDict['supplier_id'][0], 'sku': sku_id[0], 'preference': 1, 'moq': 0, 'supplier_code': myDict['supplier_code'][i], 'price': myDict['price'][i], 'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}

        if supplier_mapping:
            supplier_mapping = supplier_mapping[0]
            if sku_mapping['supplier_code'] and supplier_mapping.supplier_code != sku_mapping['supplier_code']:
                supplier_mapping.supplier_code = sku_mapping['supplier_code']
                supplier_mapping.save()
        else:
            new_mapping = SKUSupplier(**sku_mapping)
            new_mapping.save()

        suggestions_data = OpenPO.objects.exclude(status__exact='0').filter(sku_id=sku_id, supplier_id = myDict['supplier_id'][0], order_quantity = myDict['order_quantity'][i],sku__user=user.id)
        if not suggestions_data:
            po_suggestions['sku_id'] = sku_id[0].id
            po_suggestions['supplier_id'] = myDict['supplier_id'][0]
            try:
                po_suggestions['order_quantity'] = float(myDict['order_quantity'][i])
            except:
                po_suggestions['order_quantity'] = 0
            po_suggestions['price'] = float(myDict['price'][i])
            po_suggestions['status'] = 'Manual'
            po_suggestions['po_name'] = myDict['po_name'][0]
            po_suggestions['remarks'] = myDict['remarks'][i]
            if myDict.get('vendor_id', ''):
                vendor_master = VendorMaster.objects.get(vendor_id=myDict['vendor_id'][0], user=user.id)
                po_suggestions['vendor_id'] = vendor_master.id
                po_suggestions['order_type'] = 'VR'

            data = OpenPO(**po_suggestions)
            data.save()
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
    check_and_update_stock([wmscode], user)

    return HttpResponse(status)

@csrf_exempt
@login_required
@get_admin_user
def delete_po(request, user=''):
    for key, value in request.GET.iteritems():
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
        if po_quantity > 0:
            sku_extra_data, product_images, order_ids = get_order_json_data(user, mapping_id=order.id, mapping_type='PO',
                                                                         sku_id=order_data['sku_id'], order_ids=order_ids)
            orders.append([{'order_id': order.id, 'wms_code': order_data['wms_code'],
                            'po_quantity': float(order_data['order_quantity']) - float(order.received_quantity),
                            'name': str(order.order_id) + '-' + str(order_data['wms_code']),
                            'value': get_decimal_limit(user.id, order.saved_quantity),
                            'receive_quantity': get_decimal_limit(user.id, order.received_quantity), 'price': order_data['price'],
                            'temp_wms': order_data['temp_wms'],'order_type': order_data['order_type'], 'dis': True,
                            'sku_extra_data': sku_extra_data, 'product_images': product_images}])

    return HttpResponse(json.dumps({'data': orders, 'po_id': order_id,
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
                po = PurchaseOrder.objects.get(id=myDict['id'][i], open_po__sku__user = user.id)
                setattr(po, 'status', 'location-assigned')
                po.save()

    if status:
        return HttpResponse(status)
    return HttpResponse('Updated Successfully')

def get_stock_locations(wms_code, exc_dict, user, exclude_zones_list):
    stock_detail = StockDetail.objects.exclude(location__zone__zone='DEFAULT').filter(sku__wms_code=wms_code, sku__user=user, quantity__gt=0,
                                              location__max_capacity__gt=F('location__filled_capacity')).\
                                       values('location_id', 'location__max_capacity').distinct().annotate(total=Sum('quantity'))
    location_ids = map(lambda d: d['location_id'], stock_detail)
    loc1 = LocationMaster.objects.exclude(fill_sequence=0, **exc_dict).exclude(zone__zone__in=exclude_zones_list).\
                                  filter(id__in=location_ids).order_by('fill_sequence')
    if 'pallet_capacity' in exc_dict.keys():
        del exc_dict['pallet_capacity']
    loc2 = LocationMaster.objects.exclude(**exc_dict).exclude(zone__zone__in=exclude_zones_list).filter(id__in=location_ids, fill_sequence=0)
    stock_locations = list(chain(loc1, loc2))
    min_max = (0, 0)
    if stock_locations:
        location_sequence = [stock_location.fill_sequence for stock_location in stock_locations]
        min_max = (min(location_sequence), max(location_sequence))
    return stock_locations, location_ids, min_max


def get_purchaseorder_locations(put_zone, temp_dict):
    data = temp_dict['data']
    user = temp_dict['user']
    location_masters = LocationMaster.objects.filter(zone__user=user).exclude(lock_status__in=['Inbound', 'Inbound and Outbound'])
    exclude_zones_list = ['QC_ZONE', 'DAMAGED_ZONE']
    if put_zone in exclude_zones_list:
        location = location_masters.filter(zone__zone=put_zone)
        if location:
            return location
    order_data = get_purchase_order_data(data)
    sku_group = order_data['sku_group']

    locations = ''
    if sku_group:
        locations = LocationGroups.objects.filter(location__zone__user=temp_dict['user'], group=sku_group).values_list('location_id',flat=True)
        all_locations = LocationGroups.objects.filter(location__zone__user=temp_dict['user'], group='ALL').values_list('location_id',flat=True)
        locations = list(chain(locations, all_locations))
    pallet_number = 0
    if 'pallet_number' in temp_dict.keys():
        pallet_number = temp_dict['pallet_number']
    exclude_dict = {'location__exact': '', 'lock_status__in': ['Inbound', 'Inbound and Outbound']}
    filter_params = {'zone__zone': put_zone, 'zone__user': user}
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

    stock_locations, location_ids, min_max = get_stock_locations(order_data['wms_code'], exclude_dict, user, exclude_zones_list)
    exclude_dict['id__in'] = location_ids

    location1 = location_masters.exclude(**exclude_dict).filter(fill_sequence__gt=min_max[0], **filter_params).order_by('fill_sequence')
    location11 = location_masters.exclude(**exclude_dict).filter(fill_sequence__lt=min_max[0], **filter_params).order_by('fill_sequence')
    location2 = location_masters.exclude(**exclude_dict).filter(**cond1).order_by('fill_sequence')
    if put_zone not in ['QC_ZONE', 'DAMAGED_ZONE']:
        location1 = list(chain(stock_locations,location1))
    location2 = list(chain(location1, location11, location2))

    if 'pallet_capacity' in exclude_dict.keys():
        del exclude_dict['pallet_capacity']

    location3 = location_masters.exclude(**exclude_dict).filter(**cond2)
    del exclude_dict['location__exact']
    del filter_params['zone__zone']
    location4 = location_masters.exclude(Q(location__exact='') | Q(zone__zone=put_zone), **exclude_dict).\
                                       exclude(zone__zone__in=exclude_zones_list).filter(**filter_params).order_by('fill_sequence')

    location = list(chain(location2, location3, location4))

    location = list(chain(location, location_masters.filter(zone__zone='DEFAULT')))

    return location

def get_remaining_capacity(loc, received_quantity, put_zone, pallet_number, user):
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

@csrf_exempt
def save_po_location(put_zone, temp_dict):
    data = temp_dict['data']
    user = temp_dict['user']
    pallet_number = 0
    if 'pallet_number' in temp_dict.keys():
        pallet_number = temp_dict['pallet_number']
    location = get_purchaseorder_locations(put_zone, temp_dict)
    received_quantity = float(temp_dict['received_quantity'])
    data.status = 'grn-generated'
    data.save()
    purchase_data = get_purchase_order_data(data)
    for loc in location:
        location_quantity, received_quantity = get_remaining_capacity(loc, received_quantity, put_zone, pallet_number, user)
        if not location_quantity:
            continue
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

def get_purchase_order_data(order):
    order_data = {}
    status_dict = {'SR': 'Self Receipt', 'VR': 'Vendor Receipt'}
    rw_purchase = RWPurchase.objects.filter(purchase_order_id=order.id)
    st_order = STPurchaseOrder.objects.filter(po_id=order.id)
    temp_wms = ''
    if 'job_code' in dir(order):
        order_data = {'wms_code': order.product_code.wms_code, 'sku_group': order.product_code.sku_group }
        return order_data
    elif rw_purchase and not order.open_po:
        rw_purchase = rw_purchase[0]
        open_data = rw_purchase.rwo
        user_data = UserProfile.objects.get(user_id=open_data.vendor.user)
        address = open_data.vendor.address
        email_id = open_data.vendor.email_id
        username = open_data.vendor.name
        order_quantity = open_data.job_order.product_quantity
        sku = open_data.job_order.product_code
        order_type = ''
        price = 0
    elif order.open_po:
        open_data = order.open_po
        user_data = order.open_po.supplier
        address = user_data.address
        email_id = user_data.email_id
        username = user_data.name
        order_quantity = open_data.order_quantity
        sku = open_data.sku
        price = open_data.price
        order_type = status_dict[order.open_po.order_type]
        if sku.wms_code == 'TEMP':
            temp_wms = open_data.wms_code
    elif st_order and not order.open_po:
        st_picklist = STOrder.objects.filter(stock_transfer__st_po_id=st_order[0].id)
        open_data = st_order[0].open_st
        user_data = UserProfile.objects.get(user_id=st_order[0].open_st.warehouse_id)
        address = user_data.location
        email_id = user_data.user.email
        username = user_data.user.username
        order_quantity = open_data.order_quantity
        sku = open_data.sku
        price = open_data.price
        order_type = ''

    order_data = {'order_quantity': order_quantity, 'price': price, 'wms_code': sku.wms_code,
                  'sku_code': sku.sku_code, 'supplier_id': user_data.id, 'zone': sku.zone,
                  'qc_check': sku.qc_check, 'supplier_name': username,
                  'sku_desc': sku.sku_desc, 'address': address,
                  'phone_number': user_data.phone_number, 'email_id': email_id,
                  'sku_group': sku.sku_group, 'sku_id': sku.id, 'sku': sku, 'temp_wms': temp_wms, 'order_type': order_type}

    return order_data

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

@csrf_exempt
def insert_po_mapping(imei_nos, data, user_id):
    imei_list = []
    imei_nos = list(set(imei_nos.split(',')))
    order_data = get_purchase_order_data(data)
    for imei in imei_nos:
        po_mapping = POIMEIMapping.objects.filter(purchase_order__open_po__sku__wms_code=order_data['wms_code'], imei_number=imei,
                                                  purchase_order__open_po__sku__user=user_id)
        st_purchase = STPurchaseOrder.objects.filter(open_st__sku__user=user_id, open_st__sku__wms_code=order_data['wms_code']).\
                                              values_list('po_id', flat=True)
        mapping = POIMEIMapping.objects.filter(imei_number=imei, purchase_order_id__in=st_purchase)
        po_mapping = list(chain(po_mapping, mapping))
        if imei and not po_mapping and (imei not in imei_list):
            imei_mapping = {'purchase_order_id': data.id, 'imei_number': imei}
            po_imei = POIMEIMapping(**imei_mapping)
            po_imei.save()
        imei_list.append(imei)

def create_bayarea_stock(sku_code, zone, quantity, user):
    back_order = get_misc_value('back_order', user)
    if back_order == 'false' or not quantity:
        return
    inventory = StockDetail.objects.filter(sku__sku_code=sku_code, location__zone__zone=zone, sku__user=user)
    if inventory:
        inventory = inventory[0]
        setattr(inventory, 'quantity', float(inventory.quantity) + float(quantity))
        inventory.save()
    else:
       location_id = LocationMaster.objects.filter(zone__zone=zone, zone__user=user)
       sku_id = SKUMaster.objects.filter(sku_code=sku_code, user=user)
       if sku_id and location_id:
           stock_dict = {'location_id': location_id[0].id, 'receipt_number': 0, 'receipt_date': datetime.datetime.now(),
                         'sku_id':sku_id[0].id, 'quantity': quantity, 'status': 1, 'creation_date': datetime.datetime.now()}
           stock = StockDetail(**stock_dict)
           stock.save()

@csrf_exempt
@login_required
@get_admin_user
def confirm_grn(request, confirm_returns = '', user=''):
    status_msg = ''
    data_dict = ''
    pallet_data = ''
    all_data = {}
    headers = ('WMS CODE', 'Order Quantity', 'Received Quantity', 'Price')
    putaway_data = {headers: []}
    order_quantity_dict = {}
    total_received_qty = 0
    total_order_qty = 0
    total_price = 0
    pallet_number = ''
    po_data = []
    is_putaway = ''
    seller_name = user.username

    if not confirm_returns:
        request_data = request.GET
        myDict = dict(request_data.iterlists())
    else:
        myDict = confirm_returns

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
        cond = (data.id, purchase_data['wms_code'], purchase_data['price'])
        all_data.setdefault(cond, 0)
        all_data[cond] += float(value)

        if data.id not in order_quantity_dict:
            order_quantity_dict[data.id] = float(purchase_data['order_quantity']) - temp_quantity
        data.received_quantity = float(data.received_quantity) + float(value)
        data.saved_quantity = 0

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
            put_zone = ZoneMaster.objects.filter(zone='DEFAULT', user=user.id)[0]
            put_zone = put_zone.zone

        temp_dict = {'received_quantity': float(value), 'user': user.id, 'data': data, 'pallet_number': pallet_number,
                     'pallet_data': pallet_data}

        if get_permission(request.user,'add_qualitycheck') and purchase_data['qc_check'] == 1:
            put_zone = 'QC_ZONE'
            qc_data = copy.deepcopy(QUALITY_CHECK_FIELDS)
            qc_data['purchase_order_id'] = data.id
            temp_dict['qc_data'] = qc_data
            save_po_location(put_zone, temp_dict)
            data_dict = (('Order ID', data.order_id), ('Supplier ID', purchase_data['supplier_id']),
                         ('Order Date', get_local_date(request.user, data.creation_date)),
                         ('Supplier Name', purchase_data['supplier_name']))
            continue
        else:
            is_putaway = 'true'
        save_po_location(put_zone, temp_dict)
        create_bayarea_stock(purchase_data['wms_code'], 'BAY_AREA', temp_dict['received_quantity'], user.id)
        data_dict = (('Order ID', data.order_id), ('Supplier ID', purchase_data['supplier_id']),
                     ('Order Date', get_local_date(request.user, data.creation_date)),
                     ('Supplier Name', purchase_data['supplier_name']))

        price = float(data.received_quantity) * float(purchase_data['price'])
        po_data.append((purchase_data['wms_code'], purchase_data['supplier_name'], purchase_data['sku_desc'], purchase_data['order_quantity'],
                        purchase_data['price'], price))

    for key, value in all_data.iteritems():
        putaway_data[headers].append((key[1], order_quantity_dict[key[0]], value, key[2]))
        total_order_qty += order_quantity_dict[key[0]]
        total_received_qty += value
        total_price += float(key[2]) * float(value)

    if is_putaway == 'true':
        btn_class = 'inb-putaway'
    else:
        btn_class = 'inb-qc'

    if not status_msg:
        address = purchase_data['address']
        address = '\n'.join(address.split(','))
        telephone = purchase_data['phone_number']
        name = purchase_data['supplier_name']
        supplier_email = purchase_data['email_id']
        order_id = data.order_id
        order_date = get_local_date(request.user, data.creation_date)

        profile = UserProfile.objects.get(user=request.user.id)
        po_reference = '%s%s_%s' % (data.prefix, str(order_date).split(' ')[0].replace('-', ''), order_id)
        table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Ordered Quantity', 'Received Quantity')
        report_data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                            'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': '', 'po_reference': po_reference,
                            'report_name': 'Goods Receipt Note', 'company_name': profile.company_name, 'location': profile.location}

        misc_detail = get_misc_value('receive_po', user.id)
        if misc_detail == 'true':
            t = loader.get_template('templates/toggle/po_download.html')
            c = Context(report_data_dict)
            rendered = t.render(c)
            send_message = get_misc_value('send_message', user.id)
            if send_message == 'true':
                write_and_mail_pdf(po_reference, rendered, request, '', '', po_data, str(order_date).split(' ')[0], internal=True, report_type="Goods Receipt Note")
        return render(request, 'templates/toggle/putaway_toggle.html', {'data': putaway_data, 'data_dict': data_dict,
                               'total_received_qty': total_received_qty, 'total_order_qty': total_order_qty, 'total_price': total_price,
                               'seller_name': seller_name,
                               'po_number': str(data.prefix) + str(data.creation_date).split(' ')[0] + '_' + str(data.order_id),
                               'order_date': get_local_date(request.user, data.creation_date), 'order_id': order_id, 'btn_class': btn_class})
    else:
        return HttpResponse(status_msg)

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
            data.append({'order_id': key[0], 'sku_code': key[1], 'sku_desc': key[2], 'ship_quantity': value, 'return_quantity': value,
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
    sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
    if sku_master:
        return HttpResponse("confirmed")
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


def create_return_order(data, i, user):
    status = ''
    sku_id = SKUMaster.objects.filter(sku_code = data['sku_code'][i], user = user)
    if not sku_id:
        return "", "SKU Code doesn't exist"
    return_details = copy.deepcopy(RETURN_DATA)
    if (data['return'][i] or data['damaged'][i]) and sku_id:
        #order_details = OrderReturns.objects.filter(return_id = data['return_id'][i])
        quantity = data['return'][i]
        if not quantity:
            quantity = data['damaged'][i]
        return_details = {'return_id': '', 'return_date': datetime.datetime.now(), 'quantity': quantity,
                          'sku_id': sku_id[0].id, 'status': 1}
        returns = OrderReturns(**return_details)
        returns.save()

        if not returns.return_id:
            returns.return_id = 'MN%s' % returns.id
        returns.save()
    else:
        status = 'Missing Required Fields'
    if not status:
        return returns.id, status
    else:
        return "", status

def save_return_locations(order_returns, all_data, damaged_quantity, request, user):
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
        locations = get_returns_location(data['put_zone'], request, user)
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

@csrf_exempt
@login_required
@get_admin_user
def confirm_sales_return(request, user=''):
    data_dict = dict(request.GET.iterlists())
    for i in range(0, len(data_dict['id'])):
        all_data = []
        if not data_dict['id'][i]:
            data_dict['id'][i], status = create_return_order(data_dict, i , user.id)
            if status:
                return HttpResponse(status)
        order_returns = OrderReturns.objects.filter(id = data_dict['id'][i], status = 1)
        if not order_returns:
            continue
        save_return_locations(order_returns, all_data, data_dict['damaged'][i], request, user)

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
                                          'orig_quantity': location.quantity}]]
                    else:
                        if all_data[cond][2] < float(location.quantity):
                            all_data[cond][2] = float(location.quantity)
                            all_data[cond][1] = order_data['wms_code']
                        all_data[cond][0] += float(location.quantity)
                        all_data[cond][3] = location.location.fill_sequence
                        all_data[cond][4].append({'orig_id': location.id, 'orig_quantity': location.quantity})
            if temp == 'false' or (temp == 'true' and not pallet_mapping):
                data[location.id] = (order_data['wms_code'], location.location.location, location.quantity, location.quantity,
                                     location.location.fill_sequence, location.id, pallet_number)

    if temp == 'true' and all_data:
        for key, value in all_data.iteritems():
            data[key[0]] = (value[1], key[1], value[0], value[0], value[3], '', key[0], value[4])

    data_list = data.values()
    data_list.sort(key=lambda x: x[4])
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

@csrf_exempt
@login_required
@get_admin_user
def putaway_data(request, user=''):
    purchase_order_id= ''
    diff_quan = 0
    all_data = {}
    myDict = dict(request.GET.iterlists())
    sku_codes = []
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
                setattr(loc1, 'filled_capacity', float(loc1.filled_capacity) + float(value))
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
    check_and_update_stock(sku_codes, user)

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
                         'quantity': get_decimal_limit(user.id, qc_data.putaway_quantity),
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

    for key,value in request.POST.iteritems():
        filter_params = {'purchase_order__open_po__sku__wms_code': key, 'po_location__status': 2,
                         'po_location__location__zone__user': user.id, 'status': 'qc_pending'}
        if value and '_' in value:
            value = value.split('_')[-1]
            filter_params['purchase_order__order_id'] = value
        st_purchase = STPurchaseOrder.objects.exclude(po__status__in=['confirmed-putaway', 'stock-transfer']).\
                                              filter(po__order_id=value, open_st__sku__wms_code=key, open_st__sku__user=user.id).\
                                              values_list('po_id', flat=True)
        if st_purchase:
            del filter_params['purchase_order__open_po__sku__wms_code']
            filter_params['purchase_order_id__in'] = st_purchase


        quality_check_data = QualityCheck.objects.filter(**filter_params)
        if not quality_check_data:
            return HttpResponse("WMS Code not found")
        for quality_check in quality_check_data:
            purchase_data = get_purchase_order_data(quality_check.purchase_order)
            sku = purchase_data['sku']
            image = sku.image_url
            po_reference = '%s%s_%s' % (quality_check.purchase_order.prefix, str(quality_check.purchase_order.creation_date).\
                                        split(' ')[0].replace('-', ''), quality_check.purchase_order.order_id)
            qc_data.append({'id': quality_check.id,'order_id': po_reference,
                             'quantity': quality_check.po_location.quantity, 'accepted_quantity': quality_check.accepted_quantity,
                            'rejected_quantity': quality_check.rejected_quantity})
            sku_data = OrderedDict( ( ('SKU Code', sku.sku_code), ('WMS Code', sku.wms_code), ('Product Description', sku.sku_desc),
                                      ('SKU Group', sku.sku_group), ('SKU Type', sku.sku_type), ('SKU Class', sku.sku_class),
                                      ('SKU Category', sku.sku_category) ))
    return HttpResponse(json.dumps({'data_dict': qc_data, 'sku_data': sku_data, 'image': image,
                              'options': REJECT_REASONS, 'use_imei': use_imei}))

@csrf_exempt
@login_required
@get_admin_user
def confirm_quality_check(request, user=''):
    scan_data = request.POST.get("qc_scan",'')
    myDict = dict(request.POST.iterlists())
    total_sum = sum(float(i) for i in myDict['accepted_quantity'] + myDict['rejected_quantity'])
    if total_sum < 1:
        return HttpResponse('Update Quantities')
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
        save_po_location(put_zone, temp_dict)
        create_bayarea_stock(purchase_data['sku_code'], 'BAY_AREA', temp_dict['received_quantity'], user.id)
        if temp_dict['rejected_quantity']:
            put_zone = 'DAMAGED_ZONE'
            temp_dict['received_quantity'] = temp_dict['rejected_quantity']
            save_po_location(put_zone, temp_dict)
        setattr(quality_check, 'accepted_quantity', temp_dict['new_quantity'])
        setattr(quality_check, 'rejected_quantity', temp_dict['rejected_quantity'])
        setattr(quality_check, 'reason', myDict['reason'][i])
        setattr(quality_check, 'status', 'qc_cleared')
        quality_check.save()
        if not temp_dict['total_check_quantity'] == temp_dict['original_quantity']:
            not_checked = float(quality_check.putaway_quantity) - temp_dict['total_check_quantity']
            temp_dict = {}
            temp_dict['received_quantity'] = not_checked
            temp_dict['user'] = user.id
            temp_dict['data'] = data
            qc_data = copy.deepcopy(QUALITY_CHECK_FIELDS)
            qc_data['purchase_order_id'] = data.id
            temp_dict['qc_data'] = qc_data
            save_po_location(put_zone, temp_dict)

    use_imei = 'false'
    misc_data = MiscDetail.objects.filter(user=user.id, misc_type='use_imei')
    if misc_data:
        use_imei = misc_data[0].misc_value

    if scan_data and use_imei == "true":
        save_qc_serials(eval(scan_data), user.id)

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

def get_purchase_order_id(user):
    po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).values_list('order_id', flat=True).order_by("-order_id")
    st_order = STPurchaseOrder.objects.filter(open_st__sku__user=user.id).values_list('po__order_id', flat=True).order_by("-po__order_id")
    order_ids = list(chain(po_data, st_order))
    order_ids = sorted(order_ids,reverse=True)
    if not order_ids:
        po_id = 1
    else:
        po_id = int(order_ids[0]) + 1
    return po_id

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

    print request
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
    po_order_id = ''
    status = ''
    suggestion = ''
    if not request.GET:
        return HttpResponse('Updated Successfully')
    sku_id = ''
    data = copy.deepcopy(PO_DATA)
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
        myDict = dict(request.GET.iterlists())
    else:
        myDict = sales_data
    for i in range(0,len(myDict['wms_code'])):
        po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
        sku_id = SKUMaster.objects.filter(wms_code = myDict['wms_code'][i].upper(),user=user.id)

        if not sku_id:
            sku_id = SKUMaster.objects.filter(wms_code='TEMP',user=user.id)
            po_suggestions['wms_code'] = myDict['wms_code'][i].upper()

        if not myDict['order_quantity'][i]:
            continue

        if 'price' in myDict.keys() and myDict['price'][i]:
            price = myDict['price'][i]
        else:
            price = 0
        if not 'supplier_code' in myDict.keys() and myDict['supplier_id'][0]:
            supplier = SKUSupplier.objects.filter(supplier_id=myDict['supplier_id'][0], sku__user=user.id)
            if supplier:
                supplier_code = supplier[0].supplier_code
        elif myDict['supplier_code'][i]:
            supplier_code = myDict['supplier_code'][i]
        supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=myDict['supplier_id'][0], sku__user=user.id)
        sku_mapping = {'supplier_id': myDict['supplier_id'][0], 'sku': sku_id[0], 'preference': 1, 'moq': 0, 'supplier_code': supplier_code, 'price': price, 'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()} 

        if supplier_mapping:
            supplier_mapping = supplier_mapping[0]
            if sku_mapping['supplier_code'] and supplier_mapping.supplier_code != sku_mapping['supplier_code']:
                supplier_mapping.supplier_code = sku_mapping['supplier_code']
                supplier_mapping.save()
        else:
            new_mapping = SKUSupplier(**sku_mapping)
            new_mapping.save()

        po_suggestions['sku_id'] = sku_id[0].id
        po_suggestions['supplier_id'] = myDict['supplier_id'][0]
        po_suggestions['order_quantity'] = myDict['order_quantity'][i]
        po_suggestions['price'] = float(price)
        po_suggestions['status'] = 'Manual'
        po_suggestions['remarks'] = myDict['remarks'][i]
        if myDict.get('vendor_id', ''):
            vendor_master = VendorMaster.objects.get(vendor_id=myDict['vendor_id'][0], user=user.id)
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
        user_profile = UserProfile.objects.filter(user_id=user.id)
        if user_profile:
            data['prefix'] = user_profile[0].prefix
        order = PurchaseOrder(**data)
        order.save()

        amount = float(purchase_order.order_quantity) * float(purchase_order.price)
        total += amount
        total_qty += purchase_order.order_quantity
        if purchase_order.sku.wms_code == 'TEMP':
            wms_code = purchase_order.wms_code
        else:
            wms_code = purchase_order.sku.wms_code

        po_data.append(( wms_code, supplier_code, purchase_order.sku.sku_desc, purchase_order.order_quantity, purchase_order.price, amount,
                         purchase_order.remarks))
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
    order_date = get_local_date(request.user, order.creation_date)
    po_reference = '%s%s_%s' % (order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order_id)
    table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Unit Price', 'Amount', 'Remarks')

    profile = UserProfile.objects.get(user=request.user.id)

    data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id, 'telephone': str(telephone),
                 'name': name, 'order_date': order_date, 'total': total, 'po_reference': po_reference, 'user_name': request.user.username,
                 'total_qty': total_qty, 'company_name': profile.company_name, 'location': profile.location, 'w_address': profile.address,
                 'company_name': profile.company_name, 'vendor_name': vendor_name, 'vendor_address': vendor_address,
                 'vendor_telephone': vendor_telephone}

    t = loader.get_template('templates/toggle/po_download.html')
    c = Context(data_dict)
    rendered = t.render(c)
    send_message = 'false'
    data = MiscDetail.objects.filter(user=user.id, misc_type='send_message')
    if data:
        send_message = data[0].misc_value
    if send_message == 'true':
        write_and_mail_pdf(po_reference, rendered, request, supplier_email, phone_no, po_data, str(order_date).split(' ')[0])

    return render(request, 'templates/toggle/po_template.html', data_dict)

def write_and_mail_pdf(f_name, html_data, request, supplier_email, phone_no, po_data, order_date, internal=False, report_type='Purchase Order'):
    file_name = '%s.html' % f_name
    pdf_file = '%s.pdf' % f_name
    receivers = []
    internal_mail = MiscDetail.objects.filter(user=request.user.id, misc_type='Internal Emails')
    misc_internal_mail = MiscDetail.objects.filter(user=request.user.id, misc_type='internal_mail', misc_value='true')
    if misc_internal_mail and internal_mail:
        internal_mail = internal_mail[0].misc_value.split(",")
        receivers.extend(internal_mail)
    file = open(file_name, "w+b")
    file.write(html_data)
    file.close()
    os.system("./phantom/bin/phantomjs ./phantom/examples/rasterize.js ./%s ./%s A4" % (file_name, pdf_file))

    if supplier_email:
        receivers.append(supplier_email)

    if request.user.email:
        receivers.append(request.user.email)
    if supplier_email or internal or internal_mail:
        send_mail_attachment(receivers, '%s %s' % (request.user.username, report_type), 'Please find the %s with PO Reference: <b>%s</b> in the attachment' % (report_type, f_name), files=[pdf_file])

    if phone_no:
        po_message(po_data, phone_no, request.user.username, f_name, order_date)

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
    status_dict = {'Self Receipt': 'SR', 'Vendor Receipt': 'VR'}
    myDict = dict(request.GET.iterlists())
    for key, value in myDict.iteritems():
        for val in value:
            purchase_orders = OpenPO.objects.filter(supplier_id=val, status__in=['Manual', 'Automated'], order_type=status_dict[key],
                                                    sku__user=user.id)
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
                total += amount
                total_qty += float(purchase_order.order_quantity)

                if purchase_order.sku.wms_code == 'TEMP':
                    wms_code = purchase_order.wms_code
                else:
                    wms_code = purchase_order.sku.wms_code
                po_data.append((wms_code, purchase_order.supplier.name, purchase_order.sku.sku_desc, purchase_order.order_quantity, purchase_order.price, amount))
                suggestion = OpenPO.objects.get(id=data_id, sku__user=user.id)
                setattr(suggestion, 'status', 0)
                suggestion.save()

            address = purchase_orders[0].supplier.address
            address = '\n'.join(address.split(','))
            telephone = purchase_orders[0].supplier.phone_number
            name = purchase_orders[0].supplier.name
            supplier_email = purchase_orders[0].supplier.email_id
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
            profile = UserProfile.objects.get(user=request.user.id)
            po_reference = 'PAV%s_%s' %(str(order_date).split(' ')[0].replace('-', ''), order_id)
            table_headers = ('WMS CODE', 'Supplier Name', 'Description', 'Quantity', 'Unit Price', 'Amount')
            data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id, 'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total, 'company_name': profile.company_name, 'location': profile.location, 'po_reference': po_reference, 'total_qty': total_qty, 'vendor_name': vendor_name, 'vendor_address': vendor_address, 'vendor_telephone': vendor_telephone}

            t = loader.get_template('templates/toggle/po_download.html')
            c = Context(data_dict)
            rendered = t.render(c)
            send_message = 'false'
            misc_data = MiscDetail.objects.filter(user=request.user.id, misc_type='send_message')
            if misc_data:
                send_message = misc_data[0].misc_value
            if send_message == 'true':
                write_and_mail_pdf(po_reference, rendered, request, supplier_email, telephone, po_data, str(order_date).split(' ')[0])

    return render(request, 'templates/toggle/po_template.html', data_dict)

@csrf_exempt
@login_required
@get_admin_user
def delete_po_group(request, user=''):
    status_dict = {'Self Receipt': 'SR', 'Vendor Receipt': 'VR'}
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

def save_qc_serials(scan_data, user):
    for data in scan_data:
        for key,value in data.iteritems():
            value = value.split('<<>>')
            po_mapping = POIMEIMapping.objects.filter(imei_number=value[0], purchase_order__open_po__sku__user=user)
            if po_mapping:
                qc_serial_dict = copy.deepcopy(QC_SERIAL_FIELDS)
                qc_serial_dict['quality_check_id'] = value[1]
                qc_serial_dict['serial_number_id'] = po_mapping[0].id
                qc_serial_dict['status'] = key
                qc_serial_dict['reason'] = value[2]
                qc_serial = QCSerialMapping(**qc_serial_dict)
                qc_serial.save()

@csrf_exempt
@login_required
@get_admin_user
def returns_putaway_data(request, user=''):
    return_wms_codes = []
    stock = StockDetail.objects.filter(sku__user=user.id).order_by('-receipt_number')
    if stock:
        receipt_number = int(stock[0].receipt_number) + 1
    else:
        receipt_number = 1
    myDict = dict(request.GET.iterlists())
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
            location_id = LocationMaster.objects.filter(location=location, zone__zone=zone)
            if not location_id:
                status = "Zone, location match doesn't exists"
        else:
            status = 'Missing zone or location or quantity'
        if not status:
            sku_id = returns_data.returns.sku_id
            return_wms_codes.append(returns_data.returns.sku.wms_code)
            stock_data = StockDetail.objects.filter(location_id=location_id[0].id, receipt_number=receipt_number, sku_id=sku_id,
                                                    sku__user=user.id)
            if stock_data:
                stock_data = stock_data[0]
                setattr(stock_data, 'quantity', float(stock_data.quantity) + quantity)
                stock_data.save()
            else:
                stock_dict = {'location_id': location_id[0].id, 'receipt_number': receipt_number, 'receipt_date': datetime.datetime.now(),
                              'sku_id':sku_id, 'quantity': quantity, 'status': 1,
                              'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}
                new_stock = StockDetail(**stock_dict)
                new_stock.save()
            returns_data.quantity = float(returns_data.quantity) - float(quantity)
            if returns_data.quantity <= 0:
                returns_data.status = 0
            if not returns_data.location_id == location_id[0].id:
                setattr(returns_data, 'location_id', location_id[0].id)
            returns_data.save()
            status = 'Updated Successfully'

    return_wms_codes = list(set(return_wms_codes))
    check_and_update_stock(return_wms_codes, user)
    return HttpResponse(status)

@login_required
@get_admin_user
def check_imei_exists(request, user=''):
    status = ''
    for key, value in request.GET.iteritems():
        po_mapping = POIMEIMapping.objects.filter(imei_number=value, purchase_order__open_po__sku__user=user.id)
        if po_mapping:
            status = str(value) + ' is already exists'

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
        return HttpResponse(json.dumps(orders_data))

    return HttpResponse(json.dumps(orders_data))

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
        temp_data['aaData'].append({'': checkbox, 'Order ID': data.picklist.order.order_id,
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
            else:
                stock_dict = {'location_id': location_id[0].id, 'receipt_number': receipt_number, 'receipt_date': datetime.datetime.now(),
                              'sku_id':sku_id, 'quantity': quantity, 'status': 1,
                              'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}
                new_stock = StockDetail(**stock_dict)
                new_stock.save()
            cancelled_data.quantity = float(cancelled_data.quantity) - float(quantity)
            if cancelled_data.quantity <= 0:
                cancelled_data.status = 0
            if not cancelled_data.location_id == location_id[0].id:
                setattr(cancelled_data, 'location_id', location_id[0].id)
            cancelled_data.save()
            status = 'Updated Successfully'

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

