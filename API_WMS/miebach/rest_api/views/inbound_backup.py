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
from common import *
from miebach_utils import *
from mail_server import send_mail, send_mail_attachment
from django.core import serializers
from django.template import loader, Context
import dicttoxml

@csrf_exempt
def get_po_suggestions(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    lis = ['supplier__id', 'supplier__id', 'supplier__name', 'total']

    search_params = get_filtered_params(filters, lis[1:])
    print search_params
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    if search_term:
        results = OpenPO.objects.exclude(status = 0).values('supplier_id', 'supplier__name').distinct().annotate(total=Sum('order_quantity')).\
                                 filter(Q(supplier__id__icontains = search_term ) | Q( supplier__name__icontains = search_term ) |
                                        Q(total__icontains = search_term ), sku__user=user.id, **search_params).order_by(order_data)

    elif order_term:
        results = OpenPO.objects.exclude(status = 0).values('supplier_id', 'supplier__name').distinct().annotate(total=Sum('order_quantity')).\
                                 filter(sku__user=user.id, **search_params).order_by(order_data)
    else:
        results = OpenPO.objects.exclude(status = 0).values('supplier_id', 'supplier__name').distinct().annotate(total=Sum('order_quantity')).\
                                 filter(sku__user=user.id, **search_params)

    temp_data['recordsTotal'] = results.count()
    temp_data['recordsFiltered'] = results.count()

    count = 0
    for result in results[start_index: stop_index]:
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (result['supplier_id'], result['supplier__name'])
        temp_data['aaData'].append({ '': checkbox, 'Supplier ID': result['supplier_id'], 'Supplier Name': result['supplier__name'],
                                     'Total Quantity': result['total'], 'id': count, 'DT_RowClass': 'results'})
        count += 1

@csrf_exempt
def get_raised_stock_transfer(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
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
    lis = ['PO Number', 'Order Date', 'Supplier ID', 'Supplier Name', 'Order Type', 'Receive Status']
    data_list = []
    data = []
    supplier_data = {}
    col_num1 = 0
    if search_term:
        results = PurchaseOrder.objects.filter(Q(open_po__supplier_id__id = search_term) | Q(open_po__supplier__name__icontains = search_term)
                                               |Q( order_id__icontains = search_term ) | Q(creation_date__regex=search_term),
                                              open_po__sku__user=user.id).exclude(status__in=['location-assigned','confirmed-putaway']).\
                                        values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                                filter(Q(open_st__warehouse__id__icontains = search_term) |
                                                       Q(open_st__warehouse__username__icontains = search_term) |
                                                       Q(po__order_id__icontains = search_term ) | Q(po__creation_date__regex=search_term),
                                                       open_st__sku__user=user.id,
                                                       po__open_po= None).values_list('po__order_id', flat=True).distinct()
        rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                                filter(Q(rwo__vendor__id__icontains = search_term) |
                                                       Q(rwo__vendor__name__icontains = search_term) |
                                                       Q(purchase_order__creation_date__regex=search_term) |
                                                       Q(purchase_order__order_id__icontains = search_term ), rwo__vendor__user=user.id,
                                                       purchase_order__open_po= None).values_list('purchase_order__order_id', flat=True).\
                                                distinct()
        results = list(chain(results, stock_results, rw_results))
        results.sort()

    elif order_term:
        results = PurchaseOrder.objects.filter(open_po__sku__user = user.id).exclude(status__in=['location-assigned', 'confirmed-putaway'],
                                              open_po=None).values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                                filter(open_st__sku__user = user.id).values_list('po__order_id', flat=True).distinct()
        rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                        filter(rwo__vendor__user = user.id).values_list('purchase_order__order_id', flat=True).distinct()
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
                                                  open_po__sku__user = user.id).exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                           values_list('id', flat=True)
            stock_results = STPurchaseOrder.objects.exclude(po__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                                    filter(Q(po__order_id__icontains = col_val) | Q(creation_date__regex = col_val),
                                                           open_st__sku__user=user.id, po__open_po= None).\
                                                    values_list('po_id', flat=True).distinct()
            rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                            filter(Q(purchase_order__order_id__icontains = col_val) | Q(creation_date__regex = col_val),
                                                   rwo__vendor__user = user.id).values_list('purchase_order_id', flat=True).distinct()
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
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                                filter(**search_params1).values_list('po__order_id', flat=True).distinct()
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
            supplier_data = get_purchase_order_data(supplier)
            if not int(supplier_data['order_quantity']) - int(supplier.received_quantity) <= 0:
                data.append(supplier)

    temp_data['recordsTotal'] = len(data)
    temp_data['recordsFiltered'] = len(data)
    for supplier in data:
        order_type = 'Purchase Order'
        receive_status = 'Yet To Receive'
        order_data = get_purchase_order_data(supplier)
        if RWPurchase.objects.filter(purchase_order_id=supplier.id):
            order_type = 'Returnable Work Order'
        elif STPurchaseOrder.objects.filter(po_id=supplier.id):
            order_type = 'Stock Transfer'
        if supplier.received_quantity and not int(order_data['order_quantity']) == int(supplier.received_quantity):
            receive_status = 'Partially Receive'
        po_reference = '%s%s_%s' % (supplier.prefix, str(supplier.creation_date).split(' ')[0].replace('-', ''), supplier.order_id)
        data_list.append({'DT_RowId': supplier.order_id, 'PO Number': po_reference, 'Order Date': str(supplier.creation_date).split('+')[0],
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
    lis = ['Purchase Order ID', 'Supplier ID', 'Supplier Name', 'Order Type', 'Total Quantity']
    all_data = OrderedDict()
    
    qc_list = ['purchase_order__order_id', 'purchase_order__open_po__supplier__id', 'purchase_order__open_po__supplier__name']
    st_list = ['po__order_id', 'open_st__warehouse__id', 'open_st__warehouse__username']
    rw_list = ['purchase_order__order_id', 'rwo__vendor__id', 'rwo__vendor__name']
    
    del filters['search_3']
    qc_filters = get_filtered_params(filters, qc_list)
    st_filters = get_filtered_params(filters, st_list)
    rw_filters = get_filtered_params(filters, rw_list)

    if search_term:
        results = QualityCheck.objects.filter(Q(purchase_order__order_id__icontains=search_term) |
                                              Q(purchase_order__open_po__supplier__id__icontains=search_term) |
                                              Q(purchase_order__open_po__supplier__name__icontains=search_term),
                                              purchase_order__open_po__sku__user = user.id, status='qc_pending', **qc_filters)
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['confirmed-putaway', 'stock-transfer']).\
                                                filter(Q(open_st__warehouse__username__icontains = search_term) |
                                                       Q(po__order_id__icontains = search_term ), open_st__sku__user=user.id, **st_filters).\
                                                 values_list('po_id', flat=True)
        rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['confirmed-putaway', 'stock-transfer']).\
                                        filter(Q(rwo__vendor__name__icontains = search_term) | Q(rwo__vendor__id__icontains = search_term) |
                                               Q(purchase_order__order_id__icontains = search_term ), rwo__vendor__user=user.id, **rw_filters).\
                                        values_list('purchase_order_id', flat=True)
        stock_results = list(chain(stock_results, rw_results))
        qc_results = QualityCheck.objects.filter(purchase_order_id__in=stock_results, status='qc_pending', po_location__location__zone__user = user.id)

        results = list(chain(results, qc_results))
    else:
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['confirmed-putaway', 'stock-transfer']).\
                                                filter(open_st__sku__user=user.id, **st_filters).values_list('po_id', flat=True)
        rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['confirmed-putaway', 'stock-transfer']).\
                                        filter(rwo__vendor__user=user.id, **rw_filters).\
                                        values_list('purchase_order_id', flat=True)
        stock_results = list(chain(stock_results, rw_results))
        qc_results = QualityCheck.objects.filter(purchase_order_id__in=stock_results, status='qc_pending', po_location__location__zone__user = user.id)
        results = QualityCheck.objects.filter(status='qc_pending', putaway_quantity__gt=0, po_location__location__zone__user = user.id,
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
        order = PurchaseOrder.objects.filter(order_id=key[0], open_po__sku__user=user.id)
        if not order:
            order = STPurchaseOrder.objects.filter(po_id__order_id=key[0], open_st__sku__user=user.id)
            if order:
                order = [order[0].po]
            else:
                order = [RWPurchase.objects.filter(purchase_order__order_id=key[0], rwo__vendor__user=user.id)[0].purchase_order]
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
    supplier_data = {}
    if search_term:
        results = PurchaseOrder.objects.filter(Q(open_po__supplier__name__icontains=search_term) | Q(open_po__supplier__id__icontains=search_term) | Q(order_id__icontains=search_term) | Q(creation_date__regex=search_term), open_po__sku__user = user.id).exclude(status__in=['', 'confirmed-putaway']).values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['','confirmed-putaway', 'stock-transfer']).\
                                                filter(Q(open_st__warehouse__id__icontains = search_term) |
                                                       Q(open_st__warehouse__username__icontains = search_term) |
                                                       Q(po__order_id__icontains = search_term) | Q(po__creation_date__regex=search_term),
                                                       open_st__sku__user=user.id).\
                                                 values_list('po__order_id', flat=True).distinct()
        results = list(chain(results, stock_results))
    elif order_term:
        order_data = PUT_AWAY.values()[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        results = PurchaseOrder.objects.filter(open_po__sku__user = user.id).exclude(status__in=['', 'confirmed-putaway']).order_by(order_data).values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['','confirmed-putaway', 'stock-transfer']).\
                                                filter(open_st__sku__user = user.id).values_list('po__order_id', flat=True).\
                                                values_list('po__order_id', flat=True).distinct()
        results = list(chain(results, stock_results))
    else:
        results = PurchaseOrder.objects.filter(open_po__sku__user = user.id).exclude(status__in=['', 'confirmed-putaway']).values('order_id').distinct()
    data = []
    temp = []
    for result in results:
        suppliers = PurchaseOrder.objects.filter(order_id=result, open_po__sku__user = user.id).exclude(status__in=['', 'confirmed-putaway'])
        if not suppliers:
            st_order_ids = STPurchaseOrder.objects.filter(po__order_id=result, open_st__sku__user = user.id).values_list('po_id', flat=True)
            suppliers = PurchaseOrder.objects.filter(id__in=st_order_ids)
        for supplier in suppliers:
            po_loc = POLocation.objects.filter(purchase_order_id=supplier.id, status=1, location__zone__user = user.id)
            if po_loc and result not in temp:
                temp.append(result)
                data.append(supplier)

    temp_data['recordsTotal'] = len(data)
    temp_data['recordsFiltered'] = len(data)
    for supplier in data[start_index:stop_index]:
        order_data = get_purchase_order_data(supplier)
        po_reference = '%s%s_%s' % (supplier.prefix, str(supplier.creation_date).split(' ')[0].replace('-', ''), supplier.order_id)
        temp_data['aaData'].append({'DT_RowId': supplier.order_id, 'Supplier ID': order_data['supplier_id'],
                                    'Supplier Name': order_data['supplier_name'],
                                    ' Order ID': supplier.order_id, 'Order Date': str(supplier.creation_date).split('+')[0],
                                    'DT_RowClass': 'results', 'PO Number': po_reference,
                                    'DT_RowAttr': {'data-id': supplier.order_id}})


@csrf_exempt
def get_order_returns_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['returns__return_id', 'returns__return_date', 'returns__sku__wms_code', 'returns__sku__sku_desc',
           'location__zone__zone', 'location__location', 'quantity']
    if search_term:
        master_data = ReturnsLocation.objects.filter(Q(returns__return_id__icontains=search_term) |
                                                     Q(returns__sku__sku_desc__icontains=search_term) |
                                                       Q(returns__sku__wms_code__icontains=search_term) | Q(quantity__icontains=search_term),
                                                       returns__sku__user = user.id , status=1)
    elif order_term:
        col_num = col_num - 1
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = ReturnsLocation.objects.filter(returns__sku__user = user.id, status=1).order_by(order_data)
    else:
        master_data = ReturnsLocation.objects.filter(returns__sku__user = user.id, status=1).order_by('returns__return_date')
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        order_id = ''
        if data.returns.order:
            order_id = data.returns.order.id
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data.id, order_id)
        zone = "<input type='text' name='zone' value='%s' class='smallbox'>" % data.location.zone.zone
        location = "<input type='text' name='location' value='%s' class='smallbox'>" % data.location.location
        quantity = "<input type='text' name='quantity' value='%s' class='smallbox numvalid'><input type='hidden' name='hide_quantity' value='%s'>" % (data.quantity, data.quantity)
        temp_data['aaData'].append({'': checkbox, 'Return ID': data.returns.return_id,
                                    'Return Date': str(data.returns.return_date).split('+')[0], 'WMS Code': data.returns.sku.wms_code,
                                    'Product Description': data.returns.sku.sku_desc, ' Zone': zone, 'Location': location,
                                    'Quantity': quantity, 'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.id}})

@csrf_exempt
def get_order_returns(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['return_id', 'return_date', 'order__sku__sku_code', 'order__sku__sku_desc',  'order__marketplace', 'quantity']
    if search_term:
        master_data = OrderReturns.objects.filter(Q(return_id__icontains=search_term) | Q(quantity__icontains=search_term) | Q(order__sku__sku_code=search_term) | Q(order__sku__sku_desc__icontains=search_term), status=1, order__user=user.id)
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
        temp_data['aaData'].append({'Return ID': data.return_id, 'Return Date': str(data.return_date).split('+')[0],
                                    'SKU Code': data.order.sku.sku_code, 'Product Description': data.order.sku.sku_desc,
                                    'Market Place': data.order.marketplace, 'Quantity': data.quantity})

@csrf_exempt
@login_required
def generated_po_data(request, user=''):
    send_message = 'true'
    data = MiscDetail.objects.filter(user = request.user.id, misc_type='send_message')
    if data:
        send_message = data[0].misc_value

    generated_id = request.GET['data_id']
    record = OpenPO.objects.filter(Q(supplier_id=generated_id, status='Manual') | Q(supplier_id=generated_id, status='Automated'),
                                     sku__user = request.user.id)

    total_data = []
    ser_data = json.loads(serializers.serialize("json", record, indent=3, use_natural_foreign_keys=True, fields = ('supplier_code', 'sku', 'order_quantity', 'price')))
    return HttpResponse(json.dumps({'send_message': send_message, 'supplier_id': record[0].supplier_id, 'po_name': record[0].po_name, 'ship_to': '', 'data': ser_data}))

@csrf_exempt
def validate_wms(request, user=''):
    myDict = dict(request.GET.iterlists())
    wms_list = ''
    for i in range(0, len(myDict['wms_code'])):
        if not myDict['wms_code'][i]:
            continue
        sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user= 3)
        if not sku_master:
            if not wms_list:
                wms_list = 'Invalid WMS Codes are ' + myDict['wms_code'][i].upper()
            else:
                wms_list += ',' + myDict['wms_code'][i].upper()

    if not wms_list:
        wms_list = 'success'
    return HttpResponse(wms_list)

@csrf_exempt
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
            record = OpenPO.objects.get(id=data_id,sku__user=3)
            setattr(record, 'order_quantity', myDict['order_quantity'][i] )
            setattr(record, 'price', myDict['price'][i] )
            record.save()
            continue

        sku_id = SKUMaster.objects.filter(wms_code=wms_code.upper(),user=3)
        po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
        if not sku_id:
            sku_id = sku_id = SKUMaster.objects.filter(wms_code='TEMP',user=3)
            po_suggestions['wms_code'] = wms_code.upper()
        if not sku_id[0].wms_code == 'TEMP':
            supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=myDict['supplier_id'][0], sku__user=3)
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

        data = OpenPO(**po_suggestions)
        data.save()

    status_msg="Updated Successfully"
    return HttpResponse(status_msg)

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
                    'pos_switch': request.GET.get('pos_switch', ''),}


    for key, value in toggle_data.iteritems():
        if not value:
            continue

        toggle_field = key
        selection = value
        break

    user_id = 3
    if toggle_field != 'invoice_prefix':
        data = MiscDetail.objects.filter(misc_type=toggle_field, user=user_id)
        if not data:
            misc_detail = MiscDetail(user=user_id, misc_type=toggle_field, misc_value=selection, creation_date=NOW, updation_date=NOW)
            misc_detail.save()
        else:
            setattr(data[0], 'misc_value', selection)
            data[0].save()
    else:
        user_profile = UserProfile.objects.filter(user_id=user_id)
        if user_profile and selection:
            setattr(user_profile[0], 'prefix', selection)
            user_profile[0].save()
    return HttpResponse('Success')

def confirm_po(request, user=''):
    sku_id = ''
    data = copy.deepcopy(PO_DATA)
    po_data = PurchaseOrder.objects.filter(open_po__sku__user=3).order_by('-order_id')
    if not po_data:
        po_id = 0
    else:
        po_id = po_data[0].order_id
    ids_dict = {}
    po_data = []
    total = 0
    myDict = dict(request.GET.iterlists())
    for i in range(0, len(myDict['wms_code'])):
        price = 0
        if myDict['price'][i]:
            price = myDict['price'][i]
        if i < len(myDict['data-id']):
            purchase_order = OpenPO.objects.get(id=myDict['data-id'][i], sku__user=3)
            sup_id = myDict['data-id'][i]
            setattr(purchase_order, 'order_quantity', myDict['order_quantity'][i])
            setattr(purchase_order, 'price', myDict['price'][i])
            setattr(purchase_order, 'po_name', myDict['po_name'][0])
            setattr(purchase_order, 'supplier_code', myDict['supplier_code'][i])
            purchase_order.save()
        else:
            sku_id = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user=3)
            po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
            if not sku_id:
                sku_id = SKUMaster.objects.filter(wms_code='TEMP', user=3)
                po_suggestions['wms_code'] = myDict['wms_code'][i].upper()
                po_suggestions['supplier_code'] = myDict['supplier_code'][i]
                if not sku_id[0].wms_code == 'TEMP':
                    supplier_mapping = SKUSupplier.objects.filter(sku=sku_id[0], supplier_id=myDict['supplier_id'][0], sku__user=3)
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
            po_suggestions['order_quantity'] = myDict['order_quantity'][i]
            po_suggestions['price'] = float(price)
            po_suggestions['status'] = 'Manual'

            data1 = OpenPO(**po_suggestions)
            data1.save()
            purchase_order = OpenPO.objects.get(id=data1.id, sku__user=3)
            sup_id = purchase_order.id
        supplier = purchase_order.supplier_id
        if supplier not in ids_dict:
            po_id = po_id + 1
            ids_dict[supplier] = po_id
        data['open_po_id'] = sup_id
        data['order_id'] = ids_dict[supplier]
        data['ship_to'] = myDict['ship_to'][0]
        user_profile = UserProfile.objects.filter(user_id=3)
        if user_profile:
            data['prefix'] = user_profile[0].prefix
        order = PurchaseOrder(**data)
        order.save()

        amount = float(purchase_order.order_quantity) * float(purchase_order.price)
        total += amount
        if purchase_order.sku.wms_code == 'TEMP':
            wms_code = purchase_order.wms_code
        else:
            wms_code = purchase_order.sku.wms_code
        po_data.append((wms_code, myDict['supplier_code'][i], purchase_order.sku.sku_desc, purchase_order.order_quantity,
                        purchase_order.price, amount))
        suggestion = OpenPO.objects.get(id=sup_id, sku__user=3)
        setattr(suggestion, 'status', 0)
        suggestion.save()

    address = purchase_order.supplier.address
    address = '\n'.join(address.split(','))
    telephone = purchase_order.supplier.phone_number
    name = purchase_order.supplier.name
    supplier_email = purchase_order.supplier.email_id
    order_id = ids_dict[supplier]
    order_date = data['creation_date']
    po_reference = '%s%s_%s' % (order.prefix, str(order_date).split(' ')[0].replace('-', ''), order_id)

    profile = UserProfile.objects.get(user=request.user.id)
    table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Unit Price', 'Amount')
    data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id, 'telephone': str(telephone),
            'name': name, 'order_date': str(order_date), 'total': total, 'po_reference': po_reference, 'company_name': profile.company_name, 'location': profile.location}
    send_message = 'false'
    data = MiscDetail.objects.filter(user=3, misc_type='send_message')
    if data:
        send_message = data[0].misc_value

    return HttpResponse(json.dumps(data_dict))

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
    return HttpResponse(json.dumps(suppliers));

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
        sku_mapping = {'supplier_id': myDict['supplier_id'][0], 'sku': sku_id[0], 'preference': 1, 'moq': 0, 'supplier_code': myDict['supplier_code'][i], 'price': myDict['price'][i], 'creation_date':     datetime.datetime.now(), 'updation_date': datetime.datetime.now()}

        if supplier_mapping:
            supplier_mapping = supplier_mapping[0]
            if sku_mapping['supplier_code'] and supplier_mapping.supplier_code != sku_mapping['supplier_code']:
                supplier_mapping.supplier_code = sku_mapping['supplier_code']
                supplier_mapping.save()
        else:
            new_mapping = SKUSupplier(**sku_mapping)
            new_mapping.save()

        suggestions_data = OpenPO.objects.exclude(status__exact='0').filter(sku_id=sku_id, supplier_id = myDict['supplier_id'][0], order_quantity = myDict['order_quantity'][i],sku__user=request.user.id)
        if not suggestions_data:
            po_suggestions['sku_id'] = sku_id[0].id
            po_suggestions['supplier_id'] = myDict['supplier_id'][0]
            try:
                po_suggestions['order_quantity'] = myDict['order_quantity'][i]
            except:
                po_suggestions['order_quantity'] = 0
            po_suggestions['price'] = float(myDict['price'][i])
            po_suggestions['status'] = 'Manual'
            po_suggestions['po_name'] = myDict['po_name'][0]
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

    return HttpResponse(status)

def adjust_location_stock(cycle_id, wmscode, loc, quantity, reason, user):
    now = str(datetime.datetime.now())
    if wmscode:
        sku = SKUMaster.objects.filter(wms_code=wmscode, user=user.id)
        if not sku:
            return 'Invalid WMS Code'
        sku_id = sku[0].id
    if loc:
        location = LocationMaster.objects.filter(location=loc, zone__user=user.id)
        if not location:
            return 'Invalid Location'
    if not quantity:
        return 'Quantity should not be empty'

    quantity = int(quantity)
    total_stock_quantity = 0
    stocks = StockDetail.objects.filter(sku_id=sku_id, location_id=location[0].id, sku__user=user.id)
    for stock in stocks:
        total_stock_quantity += int(stock.quantity)

    remaining_quantity = total_stock_quantity - quantity
    for stock in stocks:
        if total_stock_quantity < quantity:
            stock.quantity += abs(remaining_quantity)
            stock.save()
            break
        else:
            stock_quantity = int(stock.quantity)
            if remaining_quantity == 0:
                break
            elif stock_quantity >= remaining_quantity:
                setattr(stock, 'quantity', stock_quantity - remaining_quantity)
                stock.save()
                remaining_quantity = 0
            elif stock_quantity < remaining_quantity:
                setattr(stock, 'quantity', 0)
                stock.save()
                remaining_quantity = remaining_quantity - stock_quantity
    if not stocks:
        dest_stocks = StockDetail(receipt_number=1, receipt_date=NOW, quantity=int(quantity), status=1,
                                  creation_date=NOW, updation_date=NOW, location_id=location[0].id,
                                  sku_id=sku_id)
        dest_stocks.save()

    data_dict = copy.deepcopy(CYCLE_COUNT_FIELDS)
    data_dict['cycle'] = cycle_id
    data_dict['sku_id'] = sku_id
    data_dict['location_id'] = location[0].id
    data_dict['quantity'] = total_stock_quantity
    data_dict['seen_quantity'] = quantity
    data_dict['status'] = 0
    data_dict['creation_date'] = now
    data_dict['updation_date'] = now
    cycle_obj = CycleCount.objects.filter(cycle=cycle_id, sku_id=sku_id, location_id=data_dict['location_id'])
    dat = CycleCount(**data_dict)
    dat.save()

    data = copy.deepcopy(INVENTORY_FIELDS)
    data['cycle_id'] = dat.id
    data['adjusted_quantity'] = quantity
    data['reason'] = reason
    data['adjusted_location'] = location[0].id
    data['creation_date'] = now
    data['updation_date'] = now

    dat = InventoryAdjustment(**data)
    dat.save()

    return 'Added Successfully'

@csrf_exempt
@login_required
@get_admin_user
def delete_po(request, user=''):
    for key, value in request.GET.iteritems():
        purchase_order = OpenPO.objects.get(id=key, sku__user = user.id).delete()

    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def get_supplier_data(request, user=''):
    temp = get_misc_value('pallet_switch', user.id)
    headers = ['WMS CODE', 'PO Quantity', 'Received Quantity', 'Unit Price', '']
    if temp == 'true':
        headers.insert(2, 'Pallet Number')
    use_imei = get_misc_value('use_imei', user.id)
    if use_imei == 'true':
        headers.insert(-2, 'Serial Number')
    data = {}
    order_id = request.GET['supplier_id']
    purchase_orders = PurchaseOrder.objects.filter(order_id=order_id, open_po__sku__user = user.id).exclude(status='location-assigned')
    if not purchase_orders:
        st_orders = STPurchaseOrder.objects.filter(po__order_id=order_id, open_st__sku__user = user.id).\
                                exclude(po__status__in=['location-assigned', 'stock-transfer']).values_list('po_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=st_orders)

    po_reference = '%s%s_%s' % (purchase_orders[0].prefix, str(purchase_orders[0].creation_date).split(' ')[0].replace('-', ''), order_id)
    orders = []
    for order in purchase_orders:
        order_data = get_purchase_order_data(order)
        po_quantity = int(order_data['order_quantity']) - int(order.received_quantity)
        if po_quantity > 0:
            orders.append([{'order_id': order.id, 'wms_code': order_data['wms_code'],'po_quantity': int(order_data['order_quantity'])-int(order.received_quantity),'name': str(order.order_id) + '-' + str(order_data['wms_code']), 'value': str(int(order.saved_quantity)),'receive_quantity': order.received_quantity, 'price': order_data['price'], 'temp_wms': order_data['wms_code'], 'dis': True}])

    return HttpResponse(json.dumps({'data': orders, 'po_id': order_id,
        'supplier_id': order_data['supplier_id'], 'use_imei': use_imei, 'temp': temp, 'po_reference': po_reference}))

@csrf_exempt
@login_required
@get_admin_user
def update_putaway(request, user=''):
    for key, value in request.GET.iteritems():
        po = PurchaseOrder.objects.get(id=key)
        total_count = int(value)
        if not po.open_po:
            st_order = STPurchaseOrder.objects.filter(po_id=key, open_st__sku__user = user.id)
            order_quantity = st_order[0].open_st.order_quantity
        else:
            order_quantity = po.open_po.order_quantity
        if total_count > order_quantity:
            return HttpResponse('Given quantity is greater than expected quantity')
        setattr(po, 'saved_quantity', int(value))
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
        if not value:
            continue
        if 'po_quantity' in myDict.keys() and 'price' in myDict.keys():
            if myDict['wms_code'][i] and myDict['po_quantity'][i] and myDict['quantity'][i]:
                sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user=user.id)
                if not sku_master or not myDict['id'][0]:
                    continue
                get_data = create_purchase_order(request, myDict, i)
                myDict['id'][i] = get_data
        data = PurchaseOrder.objects.get(id=myDict['id'][i])
        purchase_data = get_purchase_order_data(data)
        temp_quantity = data.received_quantity
        cond = (data.id, purchase_data['wms_code'], purchase_data['price'])
        all_data.setdefault(cond, 0)
        all_data[cond] += int(value)
        if data.id not in order_quantity_dict:
            order_quantity_dict[data.id] = int(purchase_data['order_quantity']) - temp_quantity
        data.received_quantity = int(data.received_quantity) + int(value)
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
        temp_dict = {'received_quantity': int(value), 'user': user.id, 'data': data, 'pallet_number': pallet_number,
                     'pallet_data': pallet_data}
        if get_permission(request.user,'add_qualitycheck') and purchase_data['qc_check'] == 1:
            put_zone = 'QC_ZONE'
            qc_data = copy.deepcopy(QUALITY_CHECK_FIELDS)
            qc_data['purchase_order_id'] = data.id
            temp_dict['qc_data'] = qc_data
            save_po_location(put_zone, temp_dict)
            data_dict = (('Order ID', data.order_id), ('Supplier ID', purchase_data['supplier_id']), ('Order Date', data.creation_date),
                         ('Supplier Name', purchase_data['supplier_name']))
            continue
        else:
            is_putaway = 'true'
        save_po_location(put_zone, temp_dict)
        create_bayarea_stock(purchase_data['wms_code'], 'BAY_AREA', temp_dict['received_quantity'], user.id)
        data_dict = (('Order ID', data.order_id), ('Supplier ID', purchase_data['supplier_id']), ('Order Date', data.creation_date),
                     ('Supplier Name', purchase_data['supplier_name']))

        price = int(data.received_quantity) * int(purchase_data['price'])
        po_data.append((purchase_data['wms_code'], purchase_data['supplier_name'], purchase_data['sku_desc'], purchase_data['order_quantity'],
                        purchase_data['price'], price))
    for key, value in all_data.iteritems():
        putaway_data[headers].append((key[1], order_quantity_dict[key[0]], value, key[2]))
        total_order_qty += order_quantity_dict[key[0]]
        total_received_qty += value
        total_price += key[2] * int(value)

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
        order_date = data.creation_date

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
                               'order_date': data.creation_date, 'order_id': order_id, 'btn_class': btn_class})
    else:
        return HttpResponse(status_msg)

@csrf_exempt
def save_po_location(put_zone, temp_dict):
    data = temp_dict['data']
    user = temp_dict['user']
    pallet_number = 0
    if 'pallet_number' in temp_dict.keys():
        pallet_number = temp_dict['pallet_number']
    location = get_purchaseorder_locations(put_zone, temp_dict)
    received_quantity = int(temp_dict['received_quantity'])
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
                if int(purchase_data['order_quantity']) - int(temp_dict['received_quantity']) <= 0:
                    data.status = 'location-assigned'
                data.save()
                break
        else:
            quality_check = temp_dict['quality_check']
            po_location = POLocation.objects.filter(location_id=loc.id, purchase_order_id=data.id, location__zone__user=user)
            if po_location and not pallet_number:
                if po_location[0].status == '1':
                    setattr(po_location[0], 'quantity', int(po_location[0].quantity) + location_quantity)
                else:
                    setattr(po_location[0], 'quantity', int(location_quantity))
                    setattr(po_location[0], 'status', '1')
                po_location[0].save()
                po_location_id = po_location[0].id
            else:
                location_data = {'purchase_order_id': data.id, 'location_id': loc.id, 'status': 1, 'quantity': location_quantity,
                                 'original_quantity': location_quantity, 'creation_date': NOW}
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
                data_checked += int(checked_data.accepted_quantity) + int(checked_data.rejected_quantity)

            if int(data.received_quantity) - data_checked == 0:
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

def get_purchaseorder_locations(put_zone, temp_dict):
    data = temp_dict['data']
    user = temp_dict['user']
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
    if put_zone == 'DAMAGED_ZONE':
        exclude_zone = ''
    else:
        exclude_zone = 'DAMAGED_ZONE'
    exclude_dict = {'location__exact': '', 'zone__zone': exclude_zone, 'lock_status__in': ['Inbound', 'Inbound and Outbound']}
    filter_params = {'zone__zone': put_zone, 'zone__user': user}
    if sku_group:
        filter_params['id__in'] = locations
    if pallet_number and not put_zone == 'DAMAGED_ZONE':
        filter_params['pallet_capacity__gt'] = F('pallet_filled')
        exclude_dict['pallet_capacity'] = 0
    else:
        filter_params['max_capacity__gt'] = F('filled_capacity')
    cond1 = {'fill_sequence__gt': 0}
    cond2 = {'fill_sequence': 0}
    cond1.update(filter_params)
    cond2.update(filter_params)

    stock_locations, location_ids, min_max = get_stock_locations(order_data['wms_code'], exclude_dict, user)
    exclude_dict['id__in'] = location_ids

    location1 = LocationMaster.objects.exclude(**exclude_dict).filter(fill_sequence__gt=min_max[0], **filter_params).order_by('fill_sequence')
    location11 = LocationMaster.objects.exclude(**exclude_dict).filter(fill_sequence__lt=min_max[0], **filter_params).order_by('fill_sequence')
    location2 = LocationMaster.objects.exclude(**exclude_dict).filter(**cond1).order_by('fill_sequence')
    location2 = list(chain(stock_locations, location1, location11, location2))

    if 'pallet_capacity' in exclude_dict.keys():
        del exclude_dict['pallet_capacity']

    location3 = LocationMaster.objects.exclude(**exclude_dict).filter(**cond2)
    del exclude_dict['location__exact']
    del filter_params['zone__zone']
    location4 = LocationMaster.objects.exclude(Q(location__exact='') | Q(zone__zone=put_zone), **exclude_dict).filter(**filter_params)

    if put_zone == 'QC_ZONE':
        location5 = LocationMaster.objects.filter(zone__zone='QC_ZONE', zone__user=user)
        location4 = list(chain(location4, location5))
    location = list(chain(location2, location3, location4))

    return location

def get_stock_locations(wms_code, exc_dict, user):
    stock_detail = StockDetail.objects.exclude(location__zone__zone='DEFAULT').filter(sku__wms_code=wms_code, sku__user=user, quantity__gt=0,
                                              location__max_capacity__gt=F('location__filled_capacity')).\
                                       values('location_id', 'location__max_capacity').distinct().annotate(total=Sum('quantity'))
    location_ids = map(lambda d: d['location_id'], stock_detail)
    loc1 = LocationMaster.objects.exclude(fill_sequence=0, **exc_dict).filter(id__in=location_ids).order_by('fill_sequence')
    if 'pallet_capacity' in exc_dict.keys():
        del exc_dict['pallet_capacity']
    loc2 = LocationMaster.objects.exclude(**exc_dict).filter(id__in=location_ids, fill_sequence=0)
    stock_locations = list(chain(loc1, loc2))
    min_max = (0, 0)
    if stock_locations:
        location_sequence = [stock_location.fill_sequence for stock_location in stock_locations]
        min_max = (min(location_sequence), max(location_sequence))
    return stock_locations, location_ids, min_max

def get_remaining_capacity(loc, received_quantity, put_zone, pallet_number, user):
    total_quantity = POLocation.objects.filter(location_id=loc.id, status=1, location__zone__user=user).\
                                        aggregate(Sum('quantity'))['quantity__sum']
    if not total_quantity:
        total_quantity = 0

    if not put_zone == 'QC_ZONE':
        pallet_count = len(PalletMapping.objects.filter(po_location__location_id=loc.id, po_location__location__zone__user=user,status=1))
        if pallet_number:
            if pallet_count >= int(loc.pallet_capacity):
                return '', received_quantity
    filled_capacity = StockDetail.objects.filter(location_id=loc.id, quantity__gt=0, sku__user=user).aggregate(Sum('quantity'))['quantity__sum']
    if not filled_capacity:
        filled_capacity = 0

    filled_capacity = int(total_quantity) + int(filled_capacity)
    remaining_capacity = int(loc.max_capacity) - int(filled_capacity)
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
    location_data['creation_date'] =  NOW
    location_data['quantity'] = location_quantity
    if 'qc_data' not in temp_dict.keys():
        if not po_loc or user_check == 'purchase_order__open_po__sku__user':
            location_data['original_quantity'] = location_quantity
            po_loc = POLocation(**location_data)
            po_loc.save()
        else:
            po_loc = po_loc[0]
            po_loc.quantity = int(po_loc.quantity) + location_quantity
            po_loc.original_quantity = int(po_loc.original_quantity) + location_quantity
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

def create_bayarea_stock(sku_code, zone, quantity, user):
    back_order = get_misc_value('back_order', user)
    if back_order == 'false' or not quantity:
        return
    inventory = StockDetail.objects.filter(sku__sku_code=sku_code, location__zone__zone=zone, sku__user=user)
    if inventory:
        inventory = inventory[0]
        setattr(inventory, 'quantity', int(inventory.quantity) + int(quantity))
        inventory.save()
    else:
       location_id = LocationMaster.objects.filter(zone__zone=zone, zone__user=user)
       sku_id = SKUMaster.objects.filter(sku_code=sku_code, user=user)
       if sku_id and location_id:
           stock_dict = {'location_id': location_id[0].id, 'receipt_number': 0, 'receipt_date': NOW,
                         'sku_id':sku_id[0].id, 'quantity': quantity, 'status': 1, 'creation_date': NOW}
           stock = StockDetail(**stock_dict)
           stock.save()

@csrf_exempt
def confirmation_location(record, data, total_quantity, temp_dict = ''):
    location_data = {'purchase_order_id': data.id, 'location_id': record.id, 'status': 1, 'quantity': '', 'creation_date': NOW}
    if total_quantity < ( record.max_capacity - record.filled_capacity ):
        location_data['quantity'] = total_quantity
        location_data['original_quantity'] = total_quantity
        loc = POLocation(**location_data)
        loc.save()

        total_quantity = 0
    else:
        if int(record.max_capacity) - int(record.filled_capacity) > 0:
            difference = record.max_capacity - record.filled_capacity
        else:
            record.max_capacity += total_quantity
            record.filled_capacity += total_quantity
            difference = total_quantity
        location_data['quantity'] = difference
        location_data['original_quantity'] = difference
        loc = POLocation(**location_data)
        loc.save()
        total_quantity = int(total_quantity) - int(difference)
    if temp_dict:
        insert_pallet_data(temp_dict, loc)
    return total_quantity

@login_required
@get_admin_user
def check_returns(request, user=''):
    status = ''
    data = {}
    for key, value in request.GET.iteritems():
        order_returns = OrderReturns.objects.filter(return_id=value, sku__user=user.id)
        if not order_returns:
            status = str(value) + ' is invalid'
        elif order_returns[0].status == '0':
            status = str(value) + ' is already confirmed'
        else:
            order_data = order_returns[0]
            order_obj = order_data.order
            if order_obj:
                order_quantity = order_data.order.quantity
            else:
                order_quantity = order_data.quantity
            data = {'id': order_data.id, 'return_id': order_data.return_id, 'sku_code': order_data.sku.sku_code,
                    'sku_desc': order_data.sku.sku_desc, 'ship_quantity': order_quantity,
                    'return_quantity': order_data.quantity}

    if not status:
        return HttpResponse(json.dumps(data))
    return HttpResponse(status)

@csrf_exempt
def check_sku(request):
    sku_code = request.GET.get('sku_code')
    sku_master = SKUMaster.objects.filter(sku_code=sku_code)
    if sku_master:
        return HttpResponse("confirmed")
    return HttpResponse("%s not found" % sku_code)

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
        order_returns = order_returns[0]
        zone = order_returns.sku.zone
        if zone:
            put_zone = zone.zone
        else:
            put_zone = 'DEFAULT'
        all_data.append({'received_quantity': int(order_returns.quantity), 'put_zone': put_zone})
        if data_dict['damaged'][i]:
            all_data.append({'received_quantity': int(data_dict['damaged'][i]), 'put_zone': 'DAMAGED_ZONE'})
            all_data[0]['received_quantity'] = all_data[0]['received_quantity'] - int(data_dict['damaged'][i])
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
                filled_capacity = int(total_quantity) + int(filled_capacity)
                remaining_capacity = int(location.max_capacity) - int(filled_capacity)
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
                    setattr(return_location, 'quantity', int(return_location.quantity) + location_quantity)
                    return_location.save()
                if received_quantity == 0:
                    order_returns.status = 0
                    order_returns.save()
                    break

    return HttpResponse('Updated Successfully')

def create_return_order(data, i, user):
    status = ''
    sku_id = SKUMaster.objects.filter(sku_code = data['sku_code'][i], user = user)
    if not sku_id:
        status = "SKU Code doesn't exist"
    return_details = copy.deepcopy(RETURN_DATA)
    if (data['return'][i] or data['damaged'][i]) and sku_id:
        order_details = OrderReturns.objects.filter(return_id = data['track_id'][i])
        quantity = data['return'][i]
        if not quantity:
            quantity = data['damaged'][i]
        if not order_details:
            return_details = {'return_id': data['track_id'][i], 'return_date': NOW, 'quantity': quantity,
                              'sku_id': sku_id[0].id, 'status': 1}
            returns = OrderReturns(**return_details)

            if not data['track_id'][i]:
                returns.return_id = 'MN%s' % returns.id
                returns.save()
        else:
            status = 'Return Tracking ID already exists'
    else:
        status = 'Missing Required Fields'
    if not status:
        return returns.id, status
    else:
        return "", status

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

@csrf_exempt
@login_required
@get_admin_user
def get_received_orders(request, user=''):
    all_data = {}
    temp = get_misc_value('pallet_switch', user.id)
    headers = ('WMS CODE', 'Location', 'Pallet Number', 'Original Quantity', 'Putaway Quantity', '')
    data = {}
    supplier_id = request.GET['supplier_id']
    purchase_orders = PurchaseOrder.objects.filter(order_id=supplier_id, open_po__sku__user = user.id).exclude(
                                                   status__in=['', 'confirmed-putaway'])
    if not purchase_orders:
        st_orders = STPurchaseOrder.objects.filter(po__order_id=supplier_id, open_st__sku__user = user.id).\
                                exclude(po__status__in=['', 'confirmed-putaway', 'stock-transfer']).values_list('po_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=st_orders)
    for order in purchase_orders:
        order_id = order.id
        order_data = get_purchase_order_data(order)
        po_location = POLocation.objects.filter(purchase_order_id=order_id, status=1, location__zone__user = user.id)
        for location in po_location:
            pallet_number = ''
            if temp == "true":
                pallet_mapping = PalletMapping.objects.filter(po_location_id=location.id, status=1)
                if pallet_mapping:
                    pallet_number = pallet_mapping[0].pallet_detail.pallet_code
                    cond = (pallet_number, location.location.location)
                    all_data.setdefault(cond, [0, '',0, '', []])
                    if all_data[cond] == [0, '', 0, '', []]:
                        all_data[cond] = [all_data[cond][0] + int(location.quantity), order_data['wms_code'],
                                          int(location.quantity), location.location.fill_sequence, [{'orig_id': location.id,
                                          'orig_quantity': location.quantity}]]
                    else:
                        if all_data[cond][2] < int(location.quantity):
                            all_data[cond][2] = int(location.quantity)
                            all_data[cond][1] = order_data['wms_code']
                        all_data[cond][0] += int(location.quantity)
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
    return HttpResponse(json.dumps({'data': data_list, 'po_number': po_number,'order_id': order_id,'user': request.user.id}))

@csrf_exempt
@login_required
@get_admin_user
def putaway_data(request, user=''):
    diff_quan = 0
    all_data = {}
    myDict = dict(request.GET.iterlists())
    for i in range(0, len(myDict['id'])):
        po_data = ''
        if myDict['orig_data'][i]:
            myDict['orig_data'][i] = eval(myDict['orig_data'][i])
            for orig_data in myDict['orig_data'][i]:
                cond = (orig_data['orig_id'], myDict['loc'][i], myDict['po_id'][i], myDict['orig_loc_id'][i])
                all_data.setdefault(cond, 0)
                all_data[cond] += int(orig_data['orig_quantity'])

        else:
            cond = (myDict['id'][i], myDict['loc'][i], myDict['po_id'][i], myDict['orig_loc_id'][i])
            all_data.setdefault(cond, 0)
            all_data[cond] += int(myDict['quantity'][i])


    status = validate_putaway(all_data,user)
    if status:
        return HttpResponse(status)

    for key, value in all_data.iteritems():
        loc = LocationMaster.objects.get(location=key[1], zone__user=user.id)
        loc1 = loc
        exc_loc = loc.id
        data = POLocation.objects.get(id=key[0], location__zone__user=user.id)
        if not value:
            continue
        order_data = get_purchase_order_data(data.purchase_order)
        putaway_location(data, value, exc_loc, user, 'purchase_order_id', data.purchase_order_id)
        stock_data = StockDetail.objects.filter(location_id=exc_loc, receipt_number=data.purchase_order.order_id, sku_id=order_data['sku_id'],
                                                sku__user=user.id)
        pallet_mapping = PalletMapping.objects.filter(po_location_id=key[0],status=1)
        if pallet_mapping:
            stock_data = StockDetail.objects.filter(location_id=exc_loc, receipt_number=data.purchase_order.order_id,
                                                    sku_id=order_data['sku_id'], sku__user=user.id,
                                                    pallet_detail_id=pallet_mapping[0].pallet_detail.id)
        if pallet_mapping:
            setattr(loc1, 'pallet_filled', int(loc1.pallet_filled) + 1)
        else:
            setattr(loc1, 'filled_capacity', int(loc1.filled_capacity) + int(value))
        if loc1.pallet_filled > loc1.pallet_capacity:
            setattr(loc1, 'pallet_capacity', loc1.pallet_filled)
        loc1.save()
        if stock_data:
            stock_data = stock_data[0]
            add_quan = int(stock_data.quantity) + int(value)
            setattr(stock_data, 'quantity', add_quan)
            if pallet_mapping:
                pallet_detail = pallet_mapping[0].pallet_detail
                setattr(stock_data, 'pallet_detail_id', pallet_detail.id)
            stock_data.save()
        else:
            record_data = {'location_id': exc_loc, 'receipt_number': data.purchase_order.order_id,
                           'receipt_date': str(data.purchase_order.creation_date).split('+')[0],'sku_id': order_data['sku_id'],
                           'quantity': value, 'status': 1, 'receipt_type': 'purchase order', 'creation_date': NOW, 'updation_date': NOW}
            if pallet_mapping:
                record_data['pallet_detail_id'] = pallet_mapping[0].pallet_detail.id
                pallet_mapping[0].status = 0
                pallet_mapping[0].save()
            stock_detail = StockDetail(**record_data)
            stock_detail.save()
        consume_bayarea_stock(order_data['sku_code'], "BAY_AREA", int(value), user.id)

        putaway_quantity = POLocation.objects.filter(purchase_order_id=data.purchase_order_id,
                                                     location__zone__user = request.user.id, status=0).\
                                                     aggregate(Sum('original_quantity'))['original_quantity__sum']
        if not putaway_quantity:
            putaway_quantity = 0
        if (int(order_data['order_quantity']) <= int(data.purchase_order.received_quantity)) and int(data.purchase_order.received_quantity) - int(putaway_quantity) <= 0:
            data.purchase_order.status = 'confirmed-putaway'

        data.purchase_order.save()

    return HttpResponse('Updated Successfully')

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
                data = POLocation.objects.get(id=key[0], location__zone__user=user.id)

                if (int(data.purchase_order.received_quantity) - value) < 0:
                    status = 'Putaway quantity should be less than the Received Quantity'

                if back_order == "true":
                    sku_code = data.purchase_order.open_po.sku.sku_code
                    pick_res_quantity = PicklistLocation.objects.filter(picklist__order__sku__sku_code=sku_code,
                                                                        stock__location__zone__zone="BAY_AREA",
                                                                        status=1, picklist__order__user=user.id).\
                                                                        aggregate(Sum('quantity'))['quantity__sum']
                    po_loc_quantity = POLocation.objects.filter(purchase_order__open_po__sku__sku_code=sku_code, status=1,
                                                                purchase_order__open_po__sku__user=user.id).\
                                                         aggregate(Sum('quantity'))['quantity__sum']
                    if not pick_res_quantity:
                        pick_res_quantity = 0
                    if not po_loc_quantity:
                        po_loc_quantity = 0

                    if po_loc_quantity - pick_res_quantity < value:
                        status = 'Bay Area Stock %s is reserved for %s in Picklist.You cannot putaway this stock.'% (pick_res_quantity,sku_code)

            else:
                status = 'Enter Valid Location'
    return status

def putaway_location(data, value, exc_loc, user, order_id, po_id):
    diff_quan = 0
    if int(data.quantity) >= int(value):
        diff_quan = int(data.quantity) - int(value)
        data.quantity = diff_quan
    if diff_quan == 0:
        data.status = 0
    if not data.location_id == exc_loc:
        data.original_quantity = int(data.original_quantity) - value
        filter_params = {'location_id': exc_loc, 'location__zone__user':  user.id, order_id: po_id }
        po_obj = POLocation.objects.filter(**filter_params)
        if po_obj:
            add_po_quantity = int(po_obj[0].quantity) + int(value)
            po_obj[0].original_quantity = add_po_quantity
            po_obj[0].quantity = add_po_quantity
            po_obj[0].status = 0
            po_obj[0].save()
        else:
            location_data = {order_id: po_id, 'location_id': exc_loc, 'quantity': 0, 'original_quantity': value, 'status': 0,
                             'creation_date': NOW, 'updation_date': NOW}
            loc = POLocation(**location_data)
            loc.save()
    data.save()

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
        if int(stock.quantity) > quantity:
            setattr(stock, 'quantity', int(stock.quantity) - quantity)
            stock.save()
        else:
            setattr(stock, 'quantity', 0)
            stock.save()

@csrf_exempt
@login_required
@get_admin_user
def quality_check_data(request, user=''):
    headers = ('WMS CODE', 'Location', 'Quantity', 'Accepted Quantity', 'Rejected Quantity', 'Reason')
    data = []
    order_id = request.GET['order_id']
    purchase_orders = PurchaseOrder.objects.filter(order_id=order_id, open_po__sku__user = user.id)
    if not purchase_orders:
        purchase_orders = []
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['confirmed-putaway', 'stock-transfer']).\
                                                filter(open_st__sku__user=user.id).values_list('po_id', flat=True)
        qc_results = QualityCheck.objects.filter(purchase_order_id__in=stock_results, status='qc_pending',
                                                 po_location__location__zone__user = user.id)
        for qc in qc_results:
            purchase_orders.append(qc.purchase_order)
    for order in purchase_orders:
        quality_check = QualityCheck.objects.filter(purchase_order_id=order.id, status='qc_pending',
                                                    po_location__location__zone__user = user.id)
        for qc_data in quality_check:
            purchase_data = get_purchase_order_data(qc_data.purchase_order)
            po_reference = '%s%s_%s' % (qc_data.purchase_order.prefix, str(qc_data.purchase_order.creation_date).split(' ')[0].replace('-', ''), qc_data.purchase_order.order_id)
            data.append({'id': qc_data.id, 'wms_code': purchase_data['wms_code'],
                                'location': qc_data.po_location.location.location, 'quantity': qc_data.putaway_quantity,
                                'accepted_quantity': qc_data.accepted_quantity, 'rejected_quantity': qc_data.rejected_quantity})

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

        temp_dict = {'received_quantity': int(myDict['accepted_quantity'][i]), 'original_quantity': int(quality_check.putaway_quantity),
                     'rejected_quantity': int(myDict['rejected_quantity'][i]), 'new_quantity': int(myDict['accepted_quantity'][i]),
                     'total_check_quantity': int(myDict['accepted_quantity'][i]) + int(myDict['rejected_quantity'][i]),
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
            not_checked = int(quality_check.putaway_quantity) - temp_dict['total_check_quantity']
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
                open_st.order_quantity = int(val[1])
                open_st.save()
                continue
            stock_dict = copy.deepcopy(OPEN_ST_FIELDS)
            stock_dict['warehouse_id'] = User.objects.get(username__iexact=key).id
            stock_dict['sku_id'] = SKUMaster.objects.get(wms_code=val[0], user=user.id).id
            stock_dict['order_quantity'] = int(val[1])
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

            po_dict = {'order_id': po_id, 'received_quantity': 0, 'saved_quantity': 0, 'po_date': NOW, 'ship_to': '',
                       'status': '', 'prefix': prefix, 'creation_date': NOW}
            po_order = PurchaseOrder(**po_dict)
            po_order.save()
            st_purchase_dict = {'po_id': po_order.id, 'open_st_id': open_st.id, 'creation_date': NOW}
            st_purchase = STPurchaseOrder(**st_purchase_dict)
            st_purchase.save()
            st_dict = copy.deepcopy(STOCK_TRANSFER_FIELDS)
            st_dict['order_id'] = order_id
            st_dict['invoice_amount'] = int(val[1]) * float(val[2])
            st_dict['quantity'] = int(val[1])
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

    purchase_order = PurchaseOrder.objects.exclude(status='').filter(open_po__sku__user = user.id)
    for order in purchase_order:
        po_reference = '%s%s_%s' %(order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order.order_id)
        all_results.setdefault(str(order.order_id), []).append(OrderedDict(( ('sku_code', order.open_po.sku.sku_code),
                                    ('supplier_id', order.open_po.supplier_id), ('supplier', order.open_po.supplier.name),
                                    ('product_category', 'Electronic Item'), ('order_quantity', order.open_po.order_quantity),
                                    ('received_quantity', order.received_quantity), ('unit_price', order.open_po.price),
                                    ('status', order.status), ('received_date', str(order.open_po.creation_date.date())) )))

    for key, value in all_results.iteritems():
        results.append({'order_id': key, 'results': value})
   
    results = dicttoxml.dicttoxml(results, attr_type=False) 

    return HttpResponse(results, content_type='text/xml')

@csrf_exempt
def get_so_data(request):
    results = []
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

    order_detail = OrderDetail.objects.filter(user=user.id).order_by('-id')
    for order in order_detail:
        results.append(OrderedDict(( ('order_id', order.order_id), ('order_code', order.order_code), ('sku_code', order.sku.wms_code), ('customer_name', 'Roopal Vegad'), ('ledger_name', 'Flipkart'), ('title', order.title), ('quantity', order.quantity), ('shipment_date', order.shipment_date), ('invoice_amount', order.invoice_amount), ('tax_value', '10'), ('tax_percentage', '5.5'), ('order_date', str(order.creation_date.date())) )))
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

        amount = int(purchase_order.order_quantity) * int(purchase_order.price)
        total += amount
        total_qty += purchase_order.order_quantity
        if purchase_order.sku.wms_code == 'TEMP':
            wms_code = purchase_order.wms_code
        else:
            wms_code = purchase_order.sku.wms_code

        po_data.append(( wms_code, supplier_code, purchase_order.sku.sku_desc, purchase_order.order_quantity, purchase_order.price, amount))
        suggestion = OpenPO.objects.get(id = sup_id,sku__user=request.user.id)
        setattr(suggestion, 'status', 0)
        suggestion.save()
        if sales_data and not status:
            return HttpResponse(str(order.id) + ',' + str(order.order_id) )
    if status and not suggestion:
        return HttpResponse(status)
    address = purchase_order.supplier.address
    address = '\n'.join(address.split(','))
    telephone = purchase_order.supplier.phone_number
    name = purchase_order.supplier.name
    order_id =  ids_dict[supplier]
    supplier_email = purchase_order.supplier.email_id
    phone_no = purchase_order.supplier.phone_number
    order_date = get_local_date(request.user, data['creation_date'])
    po_reference = '%s%s_%s' % (order.prefix, str(data['creation_date']).split(' ')[0].replace('-', ''), order_id)
    table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Unit Price', 'Amount')

    profile = UserProfile.objects.get(user=request.user.id)

    data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id, 'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total, 'po_reference': po_reference, 'user_name': request.user.username, 'total_qty': total_qty, 'company_name': profile.company_name, 'location': profile.location, 'w_address': profile.address, 'company_name': profile.company_name}

    t = loader.get_template('templates/toggle/po_download.html')
    c = Context(data_dict)
    rendered = t.render(c)
    send_message = 'false'
    data = MiscDetail.objects.filter(user=user.id, misc_type='send_message')
    if data:
        send_message = data[0].misc_value
    if send_message == 'true':
        write_and_mail_pdf(po_reference, rendered, request, supplier_email, phone_no, po_data, str(order_date).split(' ')[0])

    return HttpResponse("Successfully Confirmed")

def write_and_mail_pdf(f_name, html_data, request, supplier_email, phone_no, po_data, order_date, internal=False, report_type='Purchase Order'):
    file_name = '%s.html' % f_name
    pdf_file = '%s.pdf' % f_name
    file = open(file_name, "w+b")
    file.write(html_data)
    file.close()
    os.system("./phantom/bin/phantomjs ./phantom/examples/rasterize.js ./%s ./%s A4" % (file_name, pdf_file))

    receivers = []
    if supplier_email:
        receivers.append(supplier_email)

    if request.user.email:
        receivers.append(request.user.email)

    if supplier_email or internal:
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
    for key, value in request.GET.iteritems():
        purchase_orders = OpenPO.objects.filter(Q(supplier_id=key, status='Manual') | Q(supplier_id=key, status='Automated'), sku__user=user.id)
        for purchase_order in purchase_orders:
            data_id = purchase_order.id
            supplier = key
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

            amount = int(purchase_order.order_quantity) * int(purchase_order.price)
            total += amount
            total_qty += int(purchase_order.order_quantity)

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
        order_date = data['creation_date']
        profile = UserProfile.objects.get(user=request.user.id)
        po_reference = 'PAV%s_%s' %(str(order_date).split(' ')[0].replace('-', ''), order_id)
        table_headers = ('WMS CODE', 'Supplier Name', 'Description', 'Quantity', 'Unit Price', 'Amount')
        data_dict = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id, 'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total, 'company_name': profile.company_name, 'location': profile.location, 'po_reference': po_reference, 'total_qty': total_qty}

        t = loader.get_template('templates/toggle/po_download.html')
        c = Context(data_dict)
        rendered = t.render(c)
        send_message = 'false'
        data = MiscDetail.objects.filter(user=request.user.id, misc_type='send_message')
        if data:
            send_message = data[0].misc_value
        if send_message == 'true':
            write_and_mail_pdf(po_reference, rendered, request, supplier_email, telephone, po_data, str(order_date).split(' ')[0])

    return render(request, 'templates/toggle/po_template.html', data_dict)

@csrf_exempt
@login_required
@get_admin_user
def delete_po_group(request, user=''):
    for key, value in request.GET.iteritems():
        purchase_order = OpenPO.objects.filter(Q(supplier_id=key, status='Manual') | Q(supplier_id=key, status='Automated'),
                                                 sku__user = user.id).delete()

    return HttpResponse('Updated Successfully')
