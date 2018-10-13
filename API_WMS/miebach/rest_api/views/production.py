from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import json
from operator import itemgetter
from django.db.models import Q, F
from itertools import chain
from collections import OrderedDict
from itertools import groupby
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
from common import *
from miebach_utils import *
from inbound import *

log = init_logger('logs/production.log')


@csrf_exempt
def get_open_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['id', 'jo_reference', 'creation_date', 'order_type']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id, status='open',
                                              product_code_id__in=sku_master_ids). \
            order_by(order_data).values_list('jo_reference', 'order_type').distinct()
    if search_term:
        search_term1 = 'none'
        if (str(search_term).lower() in "self produce"):
            search_term1 = 'SP'
        elif (str(search_term).lower() in "vendor produce"):
            search_term1 = 'VP'
        master_data = JobOrder.objects.filter(product_code_id__in=sku_master_ids).filter(
            Q(job_code__icontains=search_term) |
            Q(order_type__icontains=search_term1) |
            Q(creation_date__regex=search_term), status='open', product_code__user=user.id). \
            values_list('jo_reference', 'order_type').distinct().order_by(order_data)
    master_data = [key for key, _ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    index = 1
    status_dict = {'SP': 'Self Produce', 'VP': 'Vendor Produce'}
    for data_id in master_data[start_index:stop_index]:
        data = JobOrder.objects.filter(jo_reference=data_id[0], product_code__user=user.id, status='open',
                                       order_type=data_id[1])[0]
        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id[0]
        temp_data['aaData'].append({'': checkbox, 'JO Reference': data.jo_reference,
                                    'Creation Date': get_local_date(request.user, data.creation_date),
                                    'Order Type': status_dict[data_id[1]], 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'data-id': data.jo_reference}, 'id': index})
        index = index + 1


@csrf_exempt
def get_generated_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['material_picklist__jo_material__job_order__job_code', 'material_picklist__creation_date',
           'material_picklist__jo_material__job_order__order_type', 'quantity']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = RMLocation.objects.filter(material_picklist__jo_material__material_code_id__in=sku_master_ids). \
            filter(material_picklist__jo_material__material_code__user=user.id, material_picklist__status='open',
                   status=1).order_by(order_data)
        total_pick_quantity = master_data.aggregate(Sum('reserved'))
        master_data = master_data.values_list('material_picklist__jo_material__job_order__job_code', flat=True)
    if search_term:
        master_data = RMLocation.objects.filter(material_picklist__jo_material__material_code_id__in=sku_master_ids). \
            filter(Q(material_picklist__jo_material__job_order__job_code__icontains=search_term,
                     material_picklist__status='open'),
                   material_picklist__jo_material__material_code__user=user.id, status=1)

        total_pick_quantity = master_data.aggregate(Sum('reserved'))
        master_data = master_data.values_list('material_picklist__jo_material__job_order__job_code', flat=True)
    master_data = list(OrderedDict.fromkeys(master_data))
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    temp_data['totalPicklistQuantity'] = int(total_pick_quantity['reserved__sum']) if total_pick_quantity[
        'reserved__sum'] else "No Data"
    for data_id in master_data[start_index:stop_index]:
        data = MaterialPicklist.objects.filter(jo_material__material_code_id__in=sku_master_ids). \
            filter(jo_material__job_order__job_code=data_id, jo_material__material_code__user=user.id,
                   status='open')
        mat_picklist_ids = data.values_list('id', flat=True)
        data = data[0]
        order_type = 'Job Order'
        rw_purchase = RWOrder.objects.filter(job_order_id=data.jo_material.job_order.id)
        if rw_purchase:
            order_type = 'Returnable Work Order'

        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        job_order_quantity = RMLocation.objects.filter(material_picklist_id__in=mat_picklist_ids, status=1)
        p_quantity = 0
        pro_quantity = 0
        for obj in job_order_quantity:
            p_quantity = obj.reserved
            if p_quantity:
                pro_quantity += p_quantity

        temp_data['aaData'].append({'': checkbox, 'Job Code': data.jo_material.job_order.job_code,
                                    'Creation Date': get_local_date(request.user, data.creation_date),
                                    'Order Type': order_type,
                                    'DT_RowClass': 'results',
                                    'DT_RowAttr': {'data-id': data.jo_material.job_order.job_code},
                                    'Quantity': get_decimal_limit(user.id, pro_quantity)})
    col_val = ['Job Code', 'Creation Date', 'Order Type', 'Quantity']
    if order_term and col_num == 3:
        order_data = col_val[col_num]
        if order_term == "asc":
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data])
        else:
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data], reverse=True)


def get_user_stages(user, sub_user):
    stages = list(ProductionStages.objects.filter(user=user.id).values_list('stage_name', flat=True).order_by('order'))

    if not sub_user.is_staff:
        group_ids = list(sub_user.groups.all().exclude(name=user.username).values_list('id', flat=True))
        stages = list(
            GroupStages.objects.filter(group_id__in=group_ids).values_list('stages_list__stage_name', flat=True))
        # stages_objs = GroupStages.objects.all()
        # for obj in stages_objs:
        #    name = sub_user.groups.filter(name=obj.group.name)
        #    if name:
        #        group_obj = name[0]
        # stages = GroupStages.objects.get(group=group_obj).stages_list.values_list('stage_name',flat=True)

    return stages


@csrf_exempt
def get_confirmed_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    parent_stages = get_user_stages(user, user)
    lis = ['job_code', 'creation_date', 'received_quantity', 'saved_quantity']
    filter_params = {'product_code_id__in': sku_master_ids, 'product_code__user': user.id,
                     'status__in': ['grn-generated', 'pick_confirm', 'partial_pick'],
                     'product_quantity__gt': F('received_quantity')}
    if not request.user.is_staff and parent_stages:
        stages = get_user_stages(user, request.user)
        status_ids = StatusTracking.objects.filter(status_value__in=stages, status_type='JO',
                                                   quantity__gt=0).values_list('status_id', flat=True)
        filter_params['id__in'] = status_ids

    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(**filter_params).order_by(order_data)
        total_quantity = master_data.aggregate(Sum('product_quantity'))['product_quantity__sum']
        partial_quantity = master_data.aggregate(Sum('received_quantity'))['received_quantity__sum']
        master_data = master_data.values_list('job_code', flat=True)
    if search_term:
        master_data = JobOrder.objects.filter(Q(job_code__icontains=search_term), **filter_params)
        total_quantity = master_data.aggregate(Sum('product_quantity'))['product_quantity__sum']
        partial_quantity = master_data.aggregate(Sum('received_quantity'))['received_quantity__sum']
        master_data = master_data.values_list('job_code', flat=True).order_by(order_data)

    master_data = [key for key, _ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if not total_quantity:
        temp_data['totalReceivedQuantity'] = 0
    if not partial_quantity:
        partial_quantity = 0
    if total_quantity:
        temp_data['totalReceivedQuantity'] = int(total_quantity) - int(partial_quantity)
    for data_id in master_data[start_index:stop_index]:
        receive_status = 'Yet to Receive'
        data = JobOrder.objects.filter(job_code=data_id, product_code__user=user.id,
                                       status__in=['grn-generated', 'pick_confirm', 'partial_pick'])
        total_quantity = 0
        for dat in data:
            total_quantity += dat.product_quantity
            if dat.received_quantity:
                receive_status = 'Partially Received'
                total_quantity = total_quantity - dat.received_quantity
                break
        data = data[0]
        temp_data['aaData'].append(
            {'Job Code': data.job_code, 'Creation Date': get_local_date(request.user, data.creation_date),
             'Receive Status': receive_status, 'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.job_code},
             'Quantity': total_quantity})


@csrf_exempt
def get_confirmed_jo_all(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    parent_stages = get_user_stages(user, user)
    lis = ['job_code', 'product_code__sku_code', 'product_code__sku_brand', 'product_code__sku_category',
           'creation_date', 'received_quantity', 'product_quantity']
    filter_params = {'product_code_id__in': sku_master_ids, 'product_code__user': user.id,
                     'status__in': ['grn-generated', 'pick_confirm', 'partial_pick'],
                     'product_quantity__gt': F('received_quantity')}
    if not request.user.is_staff and parent_stages:
        stages = get_user_stages(user, request.user)
        status_ids = StatusTracking.objects.filter(status_value__in=stages, status_type='JO',
                                                   quantity__gt=0).values_list('status_id', flat=True)
        filter_params['id__in'] = status_ids

    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(**filter_params).order_by(order_data)
        total_quantity = master_data.aggregate(Sum('product_quantity'))['product_quantity__sum']
        partial_quantity = master_data.aggregate(Sum('received_quantity'))['received_quantity__sum']
        master_data = master_data.values('job_code', 'product_code__sku_code', 'product_code__sku_category',
                                         'product_code__sku_brand')

    if search_term:
        master_data = JobOrder.objects.filter(Q(job_code__icontains=search_term), **filter_params)
        total_quantity = master_data.aggregate(Sum('product_quantity'))['product_quantity__sum']
        partial_quantity = master_data.aggregate(Sum('received_quantity'))['received_quantity__sum']
        master_data = master_data.values('job_code', 'product_code__sku_code', \
                                         'product_code__sku_category').order_by(order_data)
    master_data = [key for key, _ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)

    if not total_quantity:
        temp_data['totalReceivedQuantity'] = 0
    if not partial_quantity:
        partial_quantity = 0
    if total_quantity:
        temp_data['totalReceivedQuantity'] = int(total_quantity) - int(partial_quantity)

    for data_id in master_data[start_index:stop_index]:
        receive_status = 'Yet to Receive'
        data = JobOrder.objects.filter(job_code=data_id['job_code'],
                                       product_code__sku_code=data_id['product_code__sku_code'],
                                       product_code__user=user.id,
                                       status__in=['grn-generated', 'pick_confirm', 'partial_pick'])
        total_quantity = 0
        for dat in data:
            total_quantity += dat.product_quantity
            if dat.received_quantity:
                receive_status = 'Partially Received'
                total_quantity = total_quantity - dat.received_quantity
                break
        data = data[0]
        if not "product_code__sku_brand" in data_id.keys():
            sku_brand = ''
        else:
            sku_brand = data_id['product_code__sku_brand']

        temp_data['aaData'].append(
            {'Job Code': data.job_code, 'Creation Date': get_local_date(request.user, data.creation_date),
             'SKU Code': data_id['product_code__sku_code'], 'SKU Category': data_id['product_code__sku_category'],
             'SKU Brand': sku_brand, 'Receive Status': receive_status, 'DT_RowClass': 'results',
             'DT_RowAttr': {'data-id': data.id}, 'Quantity': total_quantity})


@csrf_exempt
def get_jo_confirmed(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['job_code', 'creation_date', 'order_type', 'product_quantity']
    master_data = JobOrder.objects.filter(product_code__user=user.id, status='order-confirmed',
                                          product_code_id__in=sku_master_ids)
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = master_data.order_by(order_data)
    if search_term:
        master_data = master_data.filter(
            Q(job_code__icontains=search_term) | Q(product_quantity__icontains=search_term))
    total_jo_quantity = master_data.aggregate(Sum('product_quantity'))['product_quantity__sum']
    master_data = master_data.values_list('job_code', flat=True).distinct()
    master_data = [key for key, _ in groupby(master_data)]
    if col_num == 3:
        master_data = list(set(master_data))
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    temp_data['totalJOQuantity'] = total_jo_quantity if total_jo_quantity else "No Data"

    for data_id in master_data[start_index:stop_index]:
        data = JobOrder.objects.filter(job_code=data_id, product_code__user=user.id, status='order-confirmed')
        pro_quantity = 0
        for obj in data:
            jo_id = 0
            created_date = ''
            p_quantity = 0
            p_quantity = obj.product_quantity
            created_date = obj.creation_date
            jo_id = obj.id
            jo_order_type = obj.order_type
            if p_quantity:
                pro_quantity += p_quantity

        order_type = 'Job Order'
        rw_purchase = RWOrder.objects.filter(job_order_id=jo_id)
        if rw_purchase:
            order_type = 'Returnable Work Order'
        if jo_order_type == 'VP':
            order_type = 'Vendor Produce'

        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        temp_data['aaData'].append({'': checkbox, 'Job Code': data_id,
                                    'Creation Date': get_local_date(request.user, created_date),
                                    'Order Type': order_type, 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'data-id': data_id}, 'Quantity': pro_quantity})

    col_val = ['Job Code', 'Creation Date', 'Order Type', 'Quantity']
    if order_term and col_num == 3:
        order_data = col_val[col_num]
        if order_term == "asc":
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data])
        else:
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data], reverse=True)


@csrf_exempt
def get_received_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    datatable_name = request.POST.get('datatable')
    if datatable_name == "PutawayConfirmationSKU":
        lis = ['job_code', 'product_code__sku_code', 'product_code__sku_brand', 'product_code__sku_category',
               'creation_date']
    else:
        lis = ['job_code', 'creation_date']

    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id,
                                              status__in=['location-assigned', 'grn-generated'],
                                              product_code_id__in=sku_master_ids).order_by(order_data).values_list(
            'job_code', flat=True)
    if search_term:
        if datatable_name == "PutawayConfirmation":
            master_data = JobOrder.objects.filter(Q(job_code__icontains=search_term),
                                                  status__in=['location-assigned', 'grn-generated'],
                                                  product_code__user=user.id, product_code_id__in=sku_master_ids). \
                values_list('job_code', flat=True).order_by(order_data)
        else:
            master_data = JobOrder.objects.filter((Q(job_code__icontains=search_term) | Q(
                product_code__sku_code=search_term) | Q(product_code__sku_brand=search_term) | Q(
                product_code__sku_category=search_term)), status__in=['location-assigned', 'grn-generated'],
                                                  product_code__user=user.id,
                                                  product_code_id__in=sku_master_ids).values_list('job_code',
                                                                                                  flat=True).order_by(
                order_data)

    master_data = [key for key, _ in groupby(master_data)]
    for data_id in master_data:
        po_location = POLocation.objects.filter(job_order__job_code=data_id, status=1,
                                                job_order__product_code__user=user.id)
        if po_location:
            data = JobOrder.objects.filter(job_code=data_id, product_code__user=user.id,
                                           status__in=['location-assigned', 'grn-generated'])
            data = data[0]
            temp_data['aaData'].append(
                {'Job Code': data.job_code, 'Creation Date': get_local_date(request.user, data.creation_date),
                 'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.job_code},
                 'SKU Code': data.product_code.sku_code, 'SKU Brand': data.product_code.sku_brand,
                 'SKU Category': data.product_code.sku_category})
    temp_data['recordsTotal'] = len(temp_data['aaData'])
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


@csrf_exempt
def get_rm_picklist_confirmed_sku(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['job_code', 'product_code__sku_code', 'product_code__sku_brand', 'product_code__sku_category',
           'product_quantity', 'order_type', 'creation_date']
    table_name = request.POST.get('datatable')
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id, status='order-confirmed',
                                              product_code_id__in=sku_master_ids). \
            order_by(order_data)
        total_jo_quantity = master_data.aggregate(Sum('product_quantity'))['product_quantity__sum']
        master_data = master_data.values_list('job_code', 'product_code__wms_code')
    if search_term:
        if table_name == "RawMaterialPicklist":
            master_data = JobOrder.objects.filter(product_code_id__in=sku_master_ids).filter((Q(
                job_code__icontains=search_term, status='order-confirmed') | Q(product_quantity__icontains=search_term,
                                                                               status='order-confirmed')),
                                                                                             product_code__user=user.id)
        else:
            master_data = JobOrder.objects.filter(product_code_id__in=sku_master_ids, product_code__user=user.id,
                                                  status='order-confirmed').filter((Q(
                job_code__icontains=search_term) | Q(product_quantity__icontains=search_term) | Q(
                product_code__sku_code__icontains=search_term) | Q(product_code__sku_brand__icontains=search_term) | Q(
                product_code__sku_category__icontains=search_term) | Q(order_type__icontains=search_term)))

        total_jo_quantity = master_data.aggregate(Sum('product_quantity'))['product_quantity__sum']
        master_data = master_data.values_list('job_code', 'product_code__wms_code').order_by(order_data)
    # master_data = [ key for key,_ in groupby(master_data)]
    # master_data = list(set(master_data))
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    temp_data['totalJOQuantity'] = total_jo_quantity if total_jo_quantity else "No Data"

    for data_id in master_data[start_index:stop_index]:
        data = JobOrder.objects.filter(job_code=data_id[0], product_code__wms_code=data_id[1],
                                       product_code__user=user.id, status='order-confirmed')
        pro_sku_code, pro_sku_brand, pro_sku_cat, pro_created_date, pro_order_type, pro_id = '', '', '', '', '', ''
        pro_quantity = 0
        for obj in data:
            pro_sku_code = obj.product_code.sku_code
            pro_sku_brand = obj.product_code.sku_brand
            pro_sku_cat = obj.product_code.sku_category
            pro_created_date = obj.creation_date
            pro_order_type = obj.order_type
            pro_id = obj.id
            p_quantity = obj.product_quantity
            if p_quantity:
                pro_quantity += p_quantity
                # emp_data['totalJOQuantity'] += pro_quantity

        order_type = 'Job Order'
        rw_purchase = RWOrder.objects.filter(job_order_id=pro_id)
        if rw_purchase:
            order_type = 'Returnable Work Order'
        if pro_order_type == 'VP':
            order_type = 'Vendor Produce'

        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id[0]
        ids_value = {}
        if table_name == "RawMaterialPicklistSKU":
            ids_value = {'id': data[0].id}
        else:
            ids_value = {'data-id': data_id[0]}

        temp_data['aaData'].append({'': checkbox, 'Job Code': data_id[0], 'SKU Code': pro_sku_code,
                                    'SKU Brand': pro_sku_brand, 'SKU Category': pro_sku_cat,
                                    'Creation Date': get_local_date(request.user, pro_created_date),
                                    'Order Type': order_type, 'DT_RowClass': 'results', 'DT_RowAttr': ids_value,
                                    'Quantity': pro_quantity})
    col_val = ['Job Code', 'SKU Code', 'SKU Brand', 'SKU Category', 'Quantity', 'Order Type', 'Creation Date']
    if order_term:
        order_data = col_val[col_num]
        if order_term == "asc":
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data])
        else:
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data], reverse=True)


@login_required
@get_admin_user
def generated_jo_data(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    jo_reference = request.GET['data_id']
    all_data = {'results': []}
    title = "Update Job Order"
    status_dict = {'SP': 'Self Produce', 'VP': 'Vendor Produce'}
    record = JobOrder.objects.filter(jo_reference=jo_reference, product_code__user=user.id, status='open',
                                     product_code_id__in=sku_master_ids)
    for rec in record:
        record_data = {}
        jo_material = JOMaterial.objects.filter(job_order_id=rec.id, status=1)
        record_data['product_code'] = rec.product_code.sku_code
        record_data['product_description'] = rec.product_quantity
        record_data['description'] = rec.product_code.sku_desc
        record_data['data'] = []
        for jo_mat in jo_material:
            dict_data = {'material_code': jo_mat.material_code.sku_code, 'material_quantity': jo_mat.material_quantity,
                         'id': jo_mat.id, 'measurement_type': jo_mat.unit_measurement_type}
            record_data['data'].append(dict_data)
        all_data['results'].append(record_data)
    all_data['jo_reference'] = jo_reference
    all_data['title'] = title
    all_data['order_type'] = status_dict[record[0].order_type]
    vendor_id = ''
    if record[0].vendor:
        vendor_id = record[0].vendor.vendor_id
    all_data['vendor_id'] = vendor_id
    return HttpResponse(json.dumps(all_data))


@csrf_exempt
@login_required
@get_admin_user
def save_jo(request, user=''):
    log.info('Request params for Save Job Order are ' + str(request.POST.dict()))
    try:
        all_data = {}
        jo_reference = request.POST.get('jo_reference', '')
        vendor_id = request.POST.get('vendor_id', '')
        order_type = 'SP'
        if not jo_reference:
            jo_reference = get_jo_reference(user.id)
        if vendor_id:
            order_type = 'VP'
        data_dict = dict(request.POST.iterlists())
        for i in range(len(data_dict['product_code'])):
            if not data_dict['product_code'][i] or not data_dict['material_code'][i]:
                continue
            data_id = ''
            if data_dict['id'][i]:
                data_id = data_dict['id'][i]
            cond = (data_dict['product_code'][i])
            all_data.setdefault(cond, [])
            measurement_type = ''
            if 'measurement_type' in request.POST.keys() and data_dict['measurement_type'][i]:
                measurement_type = data_dict['measurement_type'][i]
            all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i],
                                                                      data_dict['material_quantity'][i], data_id, '',
                                                                      measurement_type]})
        status = validate_jo(all_data, user.id, jo_reference='', vendor_id=vendor_id)
        if not status:
            all_data = insert_jo(all_data, user.id, jo_reference, vendor_id=vendor_id, order_type=order_type)
            status = "Added Successfully"
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Save Job Order failed for %s and params are %s and error statement is %s' % \
                 (str(user.username), str(request.POST.dict()), str(e)))
        status = 'Job order creation failed'
    return HttpResponse(status)


def validate_jo(all_data, user, jo_reference, vendor_id=''):
    _user = User.objects.get(id=user)
    sku_status = ''
    other_status = ''
    if vendor_id:
        vendor_master = VendorMaster.objects.filter(vendor_id=vendor_id, user=user)
        if not vendor_id:
            other_status = "Invalid Vendor ID " + vendor_id
    for key, value in all_data.iteritems():
        if not value:
            continue

        key_id = check_and_return_mapping_id(key, "", _user, False)
        product_sku = SKUMaster.objects.filter(id=key_id, user=user)
        if not product_sku:
            if not sku_status:
                sku_status = "Invalid SKU Code " + key
            else:
                sku_status += ', ' + key
        product_quantity = value[0].keys()[0]
        if not product_quantity:
            if not other_status:
                other_status = "Quantity missing for " + key
            else:
                other_status += ', ' + key
        for val in value:
            for data in val.values():
                _id = check_and_return_mapping_id(data[0], "", _user, False)
                material_sku = SKUMaster.objects.filter(id=_id, user=user)
                if not material_sku:
                    if not sku_status:
                        sku_status = "Invalid SKU Code " + data[0]
                    else:
                        sku_status += ', ' + data[0]
                if not data[1]:
                    if not other_status:
                        other_status = "Quantity missing for " + data[0]
                    else:
                        other_status += ', ' + data[0]

    if other_status:
        sku_status = sku_status + " " + other_status
    return sku_status


def create_order_mapping(user, mapping_id, order_id, mapping_type=''):
    order_ids = str(order_id).split(",")
    for order in order_ids:
        order_mapping = OrderMapping.objects.filter(mapping_id=mapping_id, mapping_type=mapping_type, order_id=order)
        if not order_mapping:
            OrderMapping.objects.create(mapping_id=mapping_id, mapping_type=mapping_type, order_id=order,
                                        creation_date=datetime.datetime.now())


def insert_jo(all_data, user, jo_reference, vendor_id='', order_type=''):
    for key, value in all_data.iteritems():
        job_order_dict = copy.deepcopy(JO_PRODUCT_FIELDS)
        if not value:
            continue
        product_sku = SKUMaster.objects.get(wms_code=key, user=user)
        job_instance = JobOrder.objects.filter(jo_reference=jo_reference, product_code__sku_code=key,
                                               product_code__user=user)
        if not job_instance:
            product_quantity = float(value[0].keys()[0])
            job_order_dict['product_code_id'] = product_sku.id
            job_order_dict['product_quantity'] = product_quantity
            job_order_dict['jo_reference'] = jo_reference
            job_order = JobOrder(**job_order_dict)
            job_order.save()
            if vendor_id and not order_type == 'VP':
                vendor_master = VendorMaster.objects.filter(vendor_id=vendor_id, user=user)
                if vendor_master:
                    insert_rwo(job_order.id, vendor_master[0].id)
                    job_order.status = 'RWO'
                    job_order.save()
            elif vendor_id and order_type == 'VP':
                vendor_master = VendorMaster.objects.filter(vendor_id=vendor_id, user=user)
                if vendor_master:
                    job_order.vendor_id = vendor_master[0].id
                    job_order.order_type = order_type
                    job_order.save()
        else:
            job_order = job_instance[0]
            job_order.product_quantity = float(value[0].keys()[0])
            job_order.save()
        for idx, val in enumerate(value):
            for k, data in val.iteritems():
                material_sku = SKUMaster.objects.get(wms_code=data[0], user=user)
                jo_material = JOMaterial.objects.filter(job_order_id=job_order.id, material_code_id=material_sku.id,
                                                        material_code__user=user)
                if jo_material and not data[2]:
                    data[2] = jo_material[0].id
                    all_data[key][idx][k][2] = jo_material[0].id
                if data[2]:
                    sku = SKUMaster.objects.get(sku_code=data[0], user=user)
                    jo_material = JOMaterial.objects.get(id=data[2])
                    jo_material.material_quantity = float(data[1])
                    jo_material.material_code_id = sku.id
                    jo_material.unit_measurement_type = data[4]
                    jo_material.save()
                    continue
                jo_material_dict = copy.deepcopy(JO_MATERIAL_FIELDS)
                jo_material_dict['material_code_id'] = material_sku.id
                jo_material_dict['job_order_id'] = job_order.id
                jo_material_dict['material_quantity'] = float(data[1])
                jo_material_dict['unit_measurement_type'] = data[4]
                jo_material = JOMaterial(**jo_material_dict)
                jo_material.save()
                if data[3]:
                    create_order_mapping(user, job_order.id, data[3], mapping_type='JO')
                all_data[key][idx][k][2] = jo_material.id
    return all_data


def delete_jo_list(job_order):
    for order in job_order:
        jo_material = JOMaterial.objects.filter(job_order_id=order.id)
        for mat in jo_material:
            mat.delete()
        order.delete()


@csrf_exempt
@login_required
@get_admin_user
def delete_jo(request, user=''):
    log.info('Request params for Delete Job Order are ' + str(request.POST.dict()))
    try:
        data_id = request.POST.get('rem_id', '')
        jo_reference = request.POST.get('jo_reference', '')
        wms_code = request.POST.get('wms_code', '')
        if jo_reference and wms_code:
            job_order = JobOrder.objects.filter(jo_reference=jo_reference, product_code__wms_code=wms_code,
                                                product_code__user=user.id)
            delete_jo_list(job_order)
        else:
            JOMaterial.objects.filter(id=data_id).delete()
        return HttpResponse("Deleted Successfully")
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Delete Job Order failed for %s and params are %s and error statement is %s' % (str(user.username),
                                                                                                 str(
                                                                                                     request.POST.dict()),
                                                                                                 str(e)))
        return HttpResponse("Delete Job Order Failed")


@csrf_exempt
@login_required
@get_admin_user
def confirm_jo(request, user=''):
    log.info('Request params for Confirm Job Order are ' + str(request.POST.dict()))
    try:
        all_data = {}
        sku_list = []
        tot_mat_qty = 0
        tot_pro_qty = 0
        jo_reference = request.POST.get('jo_reference', '')
        if not jo_reference:
            jo_reference = get_jo_reference(user.id)
        vendor_id = request.POST.get('vendor_id', '')
        order_type = 'SP'
        if vendor_id:
            order_type = 'VP'

        data_dict = dict(request.POST.iterlists())
        for i in range(len(data_dict['product_code'])):
            p_quantity = data_dict['product_quantity'][i]
            if data_dict['product_code'][i] not in sku_list and p_quantity:
                sku_list.append(data_dict['product_code'][i])
                tot_pro_qty += float(p_quantity)
            if not data_dict['product_code'][i]:
                continue
            data_id = ''
            if data_dict['id'][i]:
                data_id = data_dict['id'][i]
            order_id = ''
            if 'order_id' in request.POST.keys() and data_dict['order_id'][i]:
                order_id = data_dict['order_id'][i]
            measurement_type = ''
            if 'measurement_type' in request.POST.keys() and data_dict['measurement_type'][i]:
                measurement_type = data_dict['measurement_type'][i]
            tot_mat_qty += float(data_dict['material_quantity'][i])
            cond = (data_dict['product_code'][i])
            all_data.setdefault(cond, [])
            all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i],
                                                                      data_dict['material_quantity'][i], data_id,
                                                                      order_id, measurement_type,
                                                                      data_dict['description'][i]]})

        status = validate_jo(all_data, user.id, jo_reference=jo_reference)
        if not status:
            all_data = insert_jo(all_data, user.id, jo_reference=jo_reference, vendor_id=vendor_id,
                                 order_type=order_type)
            job_code = get_job_code(user.id)
            confirm_job_order(all_data, user.id, jo_reference, job_code)
        # save_jo_locations(all_data, user, job_code)
        if status:
            return HttpResponse(status)

        # Send Job Order Mail
        send_job_order_mail(request, user, job_code)

        creation_date = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id)[0].creation_date
        creation_date = get_local_date(user, creation_date)
        user_profile = UserProfile.objects.get(user_id=user.id)
        user_data = {'company_name': user_profile.company_name, 'username': user.first_name,
                     'location': user_profile.location}
        _vendor_id = ""
        _vendor_name = ""
        if order_type == "VP":
            vend_objs = VendorMaster.objects.filter(user=user.id, vendor_id=vendor_id)
            if vend_objs:
                _vendor_id = vendor_id
                _vendor_name = vend_objs[0].name

        return render(request, 'templates/toggle/jo_template.html',
                      {'tot_mat_qty': tot_mat_qty, 'tot_pro_qty': tot_pro_qty,
                       'all_data': all_data, 'creation_date': creation_date, 'job_code': job_code,
                       'user_data': user_data, 'headers': RAISE_JO_HEADERS,
                       'vendor_id': _vendor_id, 'vendor_name': _vendor_name})
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Confirm Job Order failed for %s and params are %s and error statement is %s' % (str(user.username),
                                                                                                  str(
                                                                                                      request.POST.dict()),
                                                                                                  str(e)))
        return HttpResponse("Confirm Job Order Failed")


def get_job_code(user):
    jo_code = JobOrder.objects.filter(product_code__user=user).order_by('-job_code')
    if jo_code:
        job_code = int(jo_code[0].job_code) + 1
    else:
        job_code = 1
    return job_code


def confirm_job_order(all_data, user, jo_reference, job_code):
    for key, value in all_data.iteritems():
        job_order = JobOrder.objects.filter(jo_reference=jo_reference, product_code__wms_code=key,
                                            product_code__user=user)
        for order in job_order:
            order.job_code = job_code
            order.status = 'order-confirmed'
            order.save()


@csrf_exempt
@login_required
@get_admin_user
def get_material_codes(request, user=''):
    sku_code = request.POST.get('sku_code', '')
    all_data = [];
    bom_master = BOMMaster.objects.filter(product_sku__sku_code=sku_code, product_sku__user=user.id)
    if not bom_master:
        return HttpResponse("No Data Found")
    for bom in bom_master:
        cond = (bom.material_sku.sku_code)
        material_quantity = bom.material_quantity
        if bom.wastage_percent:
            material_quantity = float(bom.material_quantity) + (
                (float(bom.material_quantity) / 100) * float(bom.wastage_percent))
        all_data.append({'material_quantity': material_quantity, 'material_code': cond,
                         'measurement_type': (bom.unit_of_measurement).upper()})
    product_data = {'sku_code': bom_master[0].product_sku.sku_code, 'description': bom_master[0].product_sku.sku_desc}
    return HttpResponse(json.dumps({'product': product_data, 'materials': all_data}), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def view_confirmed_jo(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    job_code_data_id = request.POST.get('data_id', '')
    job_code = request.POST.get('id', '')

    filter_params = {'product_code__user': user.id, 'status': 'order-confirmed', 'product_code_id__in': sku_master_ids}
    if job_code_data_id:
        filter_params.update({'job_code': job_code_data_id})
    else:
        filter_params.update({'id': job_code})

    all_data = {'results': []}
    order_ids = []
    status_dict = {'SP': 'Self Produce', 'VP': 'Vendor Produce'}
    record = JobOrder.objects.filter(**filter_params)

    for rec in record:
        record_data = {}
        jo_material = JOMaterial.objects.filter(job_order_id=rec.id, status=1)
        record_data['product_code'] = rec.product_code.sku_code
        record_data['product_description'] = rec.product_quantity

        record_data['sku_extra_data'], record_data['product_images'], order_ids = get_order_json_data(user,
                                                                                                      mapping_id=rec.id,
                                                                                                      mapping_type='JO',
                                                                                                      sku_id=rec.product_code_id,
                                                                                                      order_ids=order_ids)

        record_data['data'] = []
        for jo_mat in jo_material:
            dict_data = {'material_code': jo_mat.material_code.sku_code, 'material_quantity': jo_mat.material_quantity,
                         'id': jo_mat.id, 'measurement_type': jo_mat.unit_measurement_type}
            record_data['data'].append(dict_data)
        all_data['results'].append(record_data)
    all_data['jo_reference'] = job_code
    all_data['order_type'] = status_dict[record[0].order_type]
    vendor_id = ''
    if record[0].vendor:
        vendor_id = record[0].vendor.vendor_id
    all_data['vendor_id'] = vendor_id
    all_data['order_ids'] = list(set(order_ids))
    return HttpResponse(json.dumps(all_data))


@csrf_exempt
@login_required
@get_admin_user
def jo_generate_picklist(request, user=''):
    all_data = {}
    job_code = request.POST.get('job_code', '')
    temp = get_misc_value('pallet_switch', user.id)
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['product_code'])):
        if not data_dict['product_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        cond = (data_dict['product_code'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i],
                                                                  data_dict['material_quantity'][i], data_id]})

    if get_misc_value('no_stock_switch', user.id) == 'false':
        status = validate_jo_stock(all_data, user.id, job_code)
        if status:
            return HttpResponse(status)
    save_jo_locations(all_data, user, job_code)
    # data = get_raw_picklist_data(job_code, user)
    # show_image = get_misc_value('show_image', user.id)
    # if show_image == 'true':
    #    headers.insert(0, 'Image')
    # if get_misc_value('pallet_switch', user.id) == 'true' and 'Pallet Code' not in headers:
    #    headers.insert(headers.index('Location') + 1, 'Pallet Code')

    # return render(request, 'templates/toggle/view_raw_picklist.html', {'data': data, 'headers': headers, 'job_code': job_code, 'show_image': show_image, 'user': user})
    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def view_rm_picklist(request, user=''):
    data_id = request.POST['data_id']
    headers = list(PRINT_PICKLIST_HEADERS)
    data = get_raw_picklist_data(data_id, user)
    all_stock_locs = map(lambda d: d['location'], data)
    display_update = False
    if 'NO STOCK' in all_stock_locs:
        display_update = True
    show_image = get_misc_value('show_image', user.id)
    if show_image == 'true':
        headers.insert(0, 'Image')
    if get_misc_value('pallet_switch', user.id) == 'true' and 'Pallet Code' not in headers:
        headers.insert(headers.index('Location') + 1, 'Pallet Code')
    return HttpResponse(
        json.dumps({'data': data, 'job_code': data_id, 'show_image': show_image, 'user': request.user.id,
                    'display_update': display_update}))


def get_raw_picklist_data(data_id, user):
    data = []
    batch_data = {}
    material_picklist = MaterialPicklist.objects.filter(jo_material__job_order__job_code=data_id,
                                                        jo_material__job_order__product_code__user=user.id,
                                                        status='open')
    for picklist in material_picklist:
        picklist_locations = RMLocation.objects.filter(material_picklist_id=picklist.id, status=1)
        for location in picklist_locations:
            location_name = 'NO STOCK'
            pallet_detail = None
            zone = 'NO STOCK'
            sequence = 0
            stock_id = ''
            if location.stock:
                location_name = location.stock.location.location
                pallet_detail = location.stock.pallet_detail
                zone = location.stock.location.zone.zone
                sequence = location.stock.location.pick_sequence
                stock_id = location.stock_id
            match_condition = (location_name, pallet_detail, picklist.jo_material.material_code.sku_code)
            if match_condition not in batch_data:
                if pallet_detail:
                    pallet_code = location.stock.pallet_detail.pallet_code
                else:
                    pallet_code = ''
                if picklist.reserved_quantity == 0:
                    continue
                batch_data[match_condition] = {
                    'wms_code': location.material_picklist.jo_material.material_code.sku_code,
                    'zone': zone, 'sequence': sequence, 'location': location_name,
                    'reserved_quantity': get_decimal_limit(user.id, location.reserved),
                    'job_code': picklist.jo_material.job_order.job_code,
                    'stock_id': stock_id, 'picked_quantity': get_decimal_limit(user.id, location.reserved),
                    'pallet_code': pallet_code, 'id': location.id,
                    'title': location.material_picklist.jo_material.material_code.sku_desc,
                    'image': picklist.jo_material.material_code.image_url,
                    'measurement_type': picklist.jo_material.unit_measurement_type,
                    'show_imei': location.material_picklist.jo_material.material_code.enable_serial_based
                }
            else:
                batch_data[match_condition]['reserved_quantity'] = get_decimal_limit(user.id, float(
                    float(batch_data[match_condition]['reserved_quantity']) + float(location.reserved)))
                batch_data[match_condition]['picked_quantity'] = get_decimal_limit(user.id, float(
                    float(batch_data[match_condition]['picked_quantity']) + float(location.reserved)))
                batch_data[match_condition]['show_imei'] = location.material_picklist.jo_material.material_code.enable_serial_based
    data = batch_data.values()
    data = sorted(data, key=itemgetter('sequence'))
    return data


def insert_rwo_po(rw_order, request, user):
    total = 0
    total_qty = 0
    job_code = rw_order.job_order.job_code
    job_order = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id)
    po_data = []
    if job_order.filter(status='order-confirmed'):
        return
    po_id = get_purchase_order_id(user)
    for order in job_order:
        total_qty += order.product_quantity
        prefix = UserProfile.objects.get(user_id=rw_order.vendor.user).prefix
        po_dict = {'order_id': po_id, 'received_quantity': 0, 'saved_quantity': 0, 'po_date': datetime.datetime.now(),
                   'ship_to': '',
                   'status': '', 'prefix': prefix, 'creation_date': datetime.datetime.now()}
        po_order = PurchaseOrder(**po_dict)
        po_order.save()
        rw_purchase_dict = copy.deepcopy(RWO_PURCHASE_FIELDS)
        rw_purchase_dict['purchase_order_id'] = po_order.id
        rw_purchase_dict['rwo_id'] = rw_order.id
        rw_purchase = RWPurchase(**rw_purchase_dict)
        rw_purchase.save()
        po_data.append((order.product_code.wms_code, '', order.product_code.sku_desc, order.product_quantity, 0, 0))

    order_date = get_local_date(user, po_order.creation_date)
    table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Unit Price', 'Amount')

    profile = UserProfile.objects.get(user=user.id)
    phone_no = str(rw_order.vendor.phone_number)
    po_reference = '%s%s_%s' % (prefix, str(po_order.creation_date).split(' ')[0].replace('-', ''), po_order.order_id)
    w_address, company_address = get_purchase_company_address(profile)
    data_dict = {'table_headers': table_headers, 'data': po_data, 'address': rw_order.vendor.address,
                 'order_id': po_order.order_id,
                 'telephone': phone_no, 'name': rw_order.vendor.name, 'order_date': order_date,
                 'total': total, 'user_name': user.username, 'total_qty': total_qty,
                 'location': profile.location, 'w_address': w_address,
                 'company_name': profile.company_name, 'company_address': company_address}

    check_purchase_order_created(user, po_id)
    t = loader.get_template('templates/toggle/po_download.html')
    rendered = t.render(data_dict)
    if get_misc_value('raise_po', user.id) == 'true':
        write_and_mail_pdf(po_reference, rendered, request, user, rw_order.vendor.email_id, phone_no, po_data,
                           str(order_date).split(' ')[0])


def reduce_putaway_stock(stock, quantity, user):
    sku_code = stock.sku.sku_code
    purchase_orders = PurchaseOrder.objects.filter(open_po__sku__sku_code=sku_code, open_po__sku__user=user,
                                                   status__in=['grn-generated', 'location-assigned'])
    for order in purchase_orders:
        po_locations = POLocation.objects.filter(purchase_order_id=order.id, status=1)
        for po_loc in po_locations:
            if quantity == 0:
                break
            if quantity > po_loc.quantity:
                quantity -= po_loc.quantity
                po_loc.quantity = 0
                po_loc.status = 0
                po_loc.save()
            else:
                po_loc.quantity -= quantity
                quantity = 0
                if po_loc.quantity == 0:
                    po_loc.status = 0
                po_loc.save()

        active_po_loc = POLocation.objects.filter(purchase_order_id=order.id, status=1)
        if float(order.open_po.order_quantity) - float(order.received_quantity) <= 0 and not active_po_loc:
            order.status = 'confirmed-putaway'
        order.save()


def confirm_rm_no_stock(picklist, picking_count, count, raw_loc, request, user):
    stages = get_user_stages(user, request.user)
    if float(picklist.reserved_quantity) - picking_count >= 0:
        picklist.reserved_quantity = float(picklist.reserved_quantity) - picking_count
        picklist.picked_quantity = float(picklist.picked_quantity) + picking_count
        raw_loc.reserved = float(raw_loc.reserved) - picking_count
    else:
        picklist.reserved_quantity = 0
        raw_loc.reserved = 0
        picklist.picked_quantity = picking_count
    if picklist.picked_quantity > 0 and picklist.jo_material.job_order.status in ['order-confirmed', 'picklist_gen']:
        if stages:
            stat_obj = StatusTracking(status_id=picklist.jo_material.job_order.id, status_value=stages[0],
                                      status_type='JO',
                                      quantity=picklist.jo_material.job_order.product_quantity,
                                      original_quantity=picklist.jo_material.job_order.product_quantity)
            stat_obj.save()
        picklist.jo_material.job_order.status = 'partial_pick'
        picklist.jo_material.job_order.save()
    count -= picking_count
    picklist.save()
    raw_loc.save()
    if raw_loc.reserved == 0:
        raw_loc.status = 0
        raw_loc.save()
        raw_loc_obj = RMLocation.objects.filter(material_picklist__jo_material_id=picklist.jo_material_id,
                                                material_picklist__jo_material__material_code__user=user.id, status=1)
        if not raw_loc_obj:
            raw_loc.material_picklist.jo_material.status = 2
            raw_loc.material_picklist.jo_material.save()
            if picklist.reserved_quantity < 0:
                picklist.reserved_quantity = 0
            if picklist.reserved_quantity == 0:
                picklist.status = 'picked'
            picklist.save()
            material = MaterialPicklist.objects.filter(jo_material__job_order_id=picklist.jo_material.job_order_id,
                                                       status='open',
                                                       jo_material__material_code__user=user.id)
            if not material:
                if not picklist.jo_material.job_order.status in ['grn-generated', 'location-assigned',
                                                                 'confirmed-putaway']:
                    picklist.jo_material.job_order.status = 'pick_confirm'
                picklist.jo_material.job_order.save()
                rw_order = RWOrder.objects.filter(job_order_id=picklist.jo_material.job_order_id, vendor__user=user.id)
                if rw_order:
                    rw_order = rw_order[0]
                    picklist.jo_material.job_order.status = 'confirmed-putaway'
                    picklist.jo_material.job_order.save()
                    insert_rwo_po(rw_order, request, user)
    picklist.save()
    return count


def insert_jo_material_serial(picklist, val, user):
    if ',' in val['imei_numbers']:
        imei_nos = list(set(val['imei_numbers'].split(',')))
    else:
        imei_nos = list(set(val['imei_numbers'].split('\r\n')))
    for imei in imei_nos:
        imei_filter = {}
        job_order = picklist.jo_material.job_order
        sku_id = picklist.jo_material.material_code_id
        po_mapping, status, imei_data = check_get_imei_details(imei, val['wms_code'], user.id,
                                                               check_type='order_mapping',
                                                               job_order=job_order)
        # po_mapping = POIMEIMapping.objects.filter(purchase_order__open_po__sku__sku_code=val['wms_code'], imei_number=imei, status=1,
        #                                          purchase_order__open_po__sku__user=user_id)
        imei_mapping = None
        if imei and po_mapping:
            order_mapping = {'jo_material_id': picklist.jo_material_id, 'po_imei_id': po_mapping[0].id,
                             'imei_number': '',
                             'sku_id': sku_id}
            order_mapping_ins = OrderIMEIMapping.objects.filter(po_imei_id=po_mapping[0].id,
                                                                jo_material_id=picklist.jo_material_id)
            if not order_mapping_ins:
                if po_mapping[0].seller_id:
                    order_mapping['seller_id'] = seller_id
                imei_mapping = OrderIMEIMapping(**order_mapping)
                imei_mapping.save()
                po_imei = po_mapping[0]
                log.info('%s imei code is mapped for %s and for id %s' %
                         (str(imei), val['wms_code'], str(picklist.jo_material.job_order.job_code)))
                if po_imei:
                    po_imei.status = 0
                    po_imei.save()
    return 'success'


@csrf_exempt
@login_required
@get_admin_user
def rm_picklist_confirmation(request, user=''):
    try:
        log.info('Request params Confirm RM Picklist for user %s are %s' % (user.username,
                                                                       str(dict(request.POST.iterlists()))))
        stages = get_user_stages(user, user)
        status_ids = StatusTracking.objects.filter(status_value__in=stages, status_type='JO').values_list('status_id',
                                                                                                          flat=True)
        data = {}
        all_data = {}
        auto_skus = []
        mod_locations = []
        for key, value in request.POST.iterlists():
            name, picklist_id = key.rsplit('_', 1)
            data.setdefault(picklist_id, [])
            for index, val in enumerate(value):
                if len(data[picklist_id]) < index + 1:
                    data[picklist_id].append({})
                data[picklist_id][index][name] = val

        status = validate_picklist(data, user.id)
        if status:
            return HttpResponse(status)

        decimal_limit = get_decimal_value(user.id)
        for key, value in data.iteritems():
            if key == 'code':
                continue
            raw_locs = RMLocation.objects.get(id=key)
            picklist = raw_locs.material_picklist
            filter_params = {
                'material_picklist__jo_material__material_code__wms_code': picklist.jo_material.material_code.wms_code,
                'material_picklist__jo_material__job_order__product_code__user': user.id,
                'material_picklist__jo_material__job_order__job_code': picklist.jo_material.job_order.job_code, 'status': 1}
            if raw_locs.stock:
                filter_params['stock__location__location'] = value[0]['orig_location']
            else:
                filter_params['stock__isnull'] = True
            batch_raw_locs = RMLocation.objects.filter(**filter_params)
            count = 0
            for val in value:
                if val['picked_quantity']:
                    count += float(val['picked_quantity'])
            for val in value:
                if not val['picked_quantity'] or float(val['picked_quantity']) == 0:
                    continue
                picked_quantity_val = float(val['picked_quantity'])
                for raw_loc in batch_raw_locs:
                    if count == 0:
                        continue
                    picklist = raw_loc.material_picklist
                    sku = picklist.jo_material.material_code
                    if float(picklist.reserved_quantity) > picked_quantity_val:
                        picking_count = picked_quantity_val
                    else:
                        picking_count = float(picklist.reserved_quantity)
                    picking_count1 = picking_count
                    if not raw_loc.stock:
                        count = confirm_rm_no_stock(picklist, picking_count, count, raw_loc, request, user)
                        continue
                    location = LocationMaster.objects.filter(location=val['location'], zone__user=user.id)
                    if not location:
                        return HttpResponse("Invalid Location")
                    if 'imei_numbers' in val.keys():
                        insert_jo_material_serial(picklist, val, user)
                    stock_dict = {'sku_id': sku.id, 'location_id': location[0].id, 'sku__user': user.id}
                    stock_detail = StockDetail.objects.filter(**stock_dict)
                    for stock in stock_detail:
                        if picking_count == 0:
                            break
                        if picking_count > stock.quantity:
                            picking_count = truncate_float(picking_count - stock.quantity, decimal_limit)
                            picklist.reserved_quantity = truncate_float(picklist.reserved_quantity - stock.quantity,
                                                                        decimal_limit)
                            stock.quantity = 0
                        else:
                            stock.quantity = truncate_float(stock.quantity - picking_count, decimal_limit)
                            picklist.reserved_quantity = truncate_float(picklist.reserved_quantity - picking_count,
                                                                        decimal_limit)
                            picking_count = 0

                            if float(stock.location.filled_capacity) - picking_count1 >= 0:
                                filled_capacity = float(stock.location.filled_capacity) - picking_count1
                                filled_capacity = truncate_float(filled_capacity, decimal_limit)
                                setattr(stock.location, 'filled_capacity', filled_capacity)
                                stock.location.save()

                            pick_loc = RMLocation.objects.filter(material_picklist_id=picklist.id,
                                                                 stock__location_id=stock.location_id,
                                                                 material_picklist__jo_material__material_code__user=user.id,
                                                                 status=1)
                            picking_count1 = truncate_float(picking_count1, decimal_limit)
                            update_picked = picking_count1
                            # SKU Stats
                            save_sku_stats(user, stock.sku_id, picklist.id, 'rm_picklist', update_picked)
                            if pick_loc:
                                update_picklist_locations(pick_loc, picklist, update_picked, '', decimal_limit)
                            else:
                                data = RMLocation(material_picklist_id=picklist.id, stock=stock, quantity=picking_count1,
                                                  reserved=0,
                                                  status=0, creation_date=datetime.datetime.now(),
                                                  updation_date=datetime.datetime.now())
                                data.save()
                                exist_pics = RMLocation.objects.exclude(id=data.id).filter(material_picklist_id=picklist.id,
                                                                                           status=1, reserved__gt=0)
                                update_picklist_locations(exist_pics, picklist, update_picked, 'true', decimal_limit)

                            picklist.picked_quantity = float(picklist.picked_quantity) + picking_count1

                        raw_loc = RMLocation.objects.get(id=raw_loc.id)
                        stock.quantity = truncate_float(stock.quantity, decimal_limit)
                        stock.save()
                        mod_locations.append(stock.location.location)
                        if stock.location.zone.zone == 'BAY_AREA':
                            reduce_putaway_stock(stock, picking_count1, user.id)
                        if raw_loc.reserved == 0:
                            raw_loc.status = 0
                            raw_loc_obj = RMLocation.objects.filter(
                                material_picklist__jo_material_id=picklist.jo_material_id,
                                material_picklist__jo_material__material_code__user=user.id, status=1)
                            if not raw_loc_obj:
                                raw_loc.material_picklist.jo_material.status = 2
                                raw_loc.material_picklist.jo_material.save()
                        auto_skus.append(sku.sku_code)
                    picked_quantity_val -= picking_count1
                    picked_quantity_val = truncate_float(picked_quantity_val, decimal_limit)
                    if picklist.reserved_quantity < 0:
                        picklist.reserved_quantity = 0
                    if picklist.reserved_quantity == 0:
                        picklist.status = 'picked'
                    if picklist.picked_quantity > 0 and picklist.jo_material.job_order.status in ['order-confirmed',
                                                                                                  'picklist_gen']:
                        if stages:
                            stat_obj = StatusTracking(status_id=picklist.jo_material.job_order.id, status_value=stages[0],
                                                      status_type='JO',
                                                      quantity=picklist.jo_material.job_order.product_quantity,
                                                      original_quantity=picklist.jo_material.job_order.product_quantity)
                            stat_obj.save()
                        picklist.jo_material.job_order.status = 'partial_pick'
                        picklist.jo_material.job_order.save()
                    picklist.save()

                    material = MaterialPicklist.objects.filter(jo_material__job_order_id=picklist.jo_material.job_order_id,
                                                               status='open',
                                                               jo_material__material_code__user=user.id)
                    if not material:
                        if not picklist.jo_material.job_order.status in ['grn-generated', 'location-assigned',
                                                                         'confirmed-putaway']:
                            picklist.jo_material.job_order.status = 'pick_confirm'
                        picklist.jo_material.job_order.save()
                        rw_order = RWOrder.objects.filter(job_order_id=picklist.jo_material.job_order_id,
                                                          vendor__user=user.id)
                        if rw_order:
                            rw_order = rw_order[0]
                            picklist.jo_material.job_order.status = 'confirmed-putaway'
                            picklist.jo_material.job_order.save()
                            insert_rwo_po(rw_order, request, user)

                if auto_skus:
                    auto_po(list(set(auto_skus)), user.id)

        if mod_locations:
            update_filled_capacity(list(set(mod_locations)), user.id)

        return HttpResponse('Picklist Confirmed')
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Confirm RM Picklist failed for %s and params are %s and error statement is %s' %
                                                                    (str(user.username),
                                                                     str(dict(request.POST.iterlists())),
                                                                    str(e)))


def validate_jo_stock(all_data, user, job_code):
    status = []
    for key, value in all_data.iteritems():
        for val in value:
            for data in val.values():
                stock_quantity = \
                    StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE').filter(sku__wms_code=data[0],
                                                                                            quantity__gt=0,
                                                                                            sku__user=user).aggregate(
                        Sum('quantity'))['quantity__sum']
                reserved_quantity = PicklistLocation.objects.filter(stock__sku__wms_code=data[0], status=1,
                                                                    picklist__order__user=user).aggregate(
                    Sum('reserved'))['reserved__sum']

                raw_reserved = \
                    RMLocation.objects.filter(status=1, material_picklist__jo_material__material_code__user=user,
                                              stock__sku__wms_code=data[0]).aggregate(Sum('reserved'))['reserved__sum']
                if not stock_quantity:
                    stock_quantity = 0
                if not reserved_quantity:
                    reserved_quantity = 0
                if raw_reserved:
                    reserved_quantity += float(raw_reserved)
                diff = stock_quantity - reserved_quantity
                diff = get_decimal_limit(user, diff)
                if diff < float(data[1]):
                    if data[0] not in status:
                        status.append(data[0])

    if status:
        status = "Insufficient stock for " + ','.join(status)
    return status


def save_jo_locations(all_data, user, job_code):
    for key, value in all_data.iteritems():
        job_order = JobOrder.objects.filter(job_code=job_code, product_code__wms_code=key, product_code__user=user.id)
        for val in value:
            for data in val.values():
                jo_material = JOMaterial.objects.get(id=data[2])
                data_dict = {'sku_id': jo_material.material_code_id, 'quantity__gt': 0, 'sku__user': user.id}
                stock_detail = get_picklist_locations(data_dict, user)
                stock_diff = 0
                rem_stock_quantity = float(jo_material.material_quantity)
                stock_total = 0
                stock_detail_dict = []
                for stock in stock_detail:
                    reserved_quantity = RMLocation.objects.filter(stock_id=stock.id, status=1,
                                                                  material_picklist__jo_material__material_code__user=user.id). \
                        aggregate(Sum('reserved'))['reserved__sum']
                    picklist_reserved = \
                        PicklistLocation.objects.filter(stock_id=stock.id, status=1, picklist__order__user=user.id). \
                            aggregate(Sum('reserved'))['reserved__sum']
                    if not reserved_quantity:
                        reserved_quantity = 0
                    if picklist_reserved:
                        reserved_quantity += picklist_reserved

                    stock_quantity = float(stock.quantity) - reserved_quantity
                    stock_quantity = get_decimal_limit(user.id, stock_quantity)
                    if stock_quantity <= 0:
                        continue
                    stock_total += stock_quantity
                    stock_detail_dict.append({'stock': stock, 'stock_quantity': stock_quantity})

                material_picklist_dict = copy.deepcopy(MATERIAL_PICKLIST_FIELDS)
                material_picklist_dict['jo_material_id'] = jo_material.id
                material_picklist_dict['reserved_quantity'] = float(jo_material.material_quantity)
                material_picklist = MaterialPicklist(**material_picklist_dict)
                material_picklist.save()

                if stock_total < rem_stock_quantity:
                    no_stock_quantity = rem_stock_quantity - stock_total
                    rem_stock_quantity -= no_stock_quantity
                    RMLocation.objects.create(material_picklist_id=material_picklist.id, stock=None,
                                              quantity=no_stock_quantity,
                                              reserved=no_stock_quantity, creation_date=datetime.datetime.now(),
                                              status=1)

                for stock_dict in stock_detail_dict:
                    stock = stock_dict['stock']
                    stock_quantity = stock_dict['stock_quantity']
                    if rem_stock_quantity <= 0:
                        break

                    if stock_diff:
                        if stock_quantity >= stock_diff:
                            stock_count = stock_diff
                            stock_diff = 0
                        else:
                            stock_count = stock_quantity
                            stock_diff -= stock_quantity
                    else:
                        if stock_quantity >= rem_stock_quantity:
                            stock_count = rem_stock_quantity
                        else:
                            stock_count = stock_quantity
                            stock_diff = rem_stock_quantity - stock_quantity

                    rem_stock_quantity -= stock_count
                    rm_locations_dict = copy.deepcopy(MATERIAL_PICK_LOCATIONS)
                    rm_locations_dict['material_picklist_id'] = material_picklist.id
                    rm_locations_dict['stock_id'] = stock.id
                    stock_count = get_decimal_limit(user.id, stock_count)
                    rm_locations_dict['quantity'] = stock_count
                    rm_locations_dict['reserved'] = stock_count
                    rm_locations = RMLocation(**rm_locations_dict)
                    rm_locations.save()

                jo_material.status = 0
                jo_material.save()
                for order in job_order:
                    order.status = 'picklist_gen'
                    order.save()
    return "Confirmed Successfully"


def get_picklist_locations(data_dict, user):
    exclude_dict = {'location__lock_status__in': ['Outbound', 'Inbound and Outbound'],
                    'location__zone__zone': 'TEMP_ZONE'}
    back_order = get_misc_value('back_order', user.id)
    fifo_switch = get_misc_value('fifo_switch', user.id)

    if fifo_switch == 'true':
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0,
                                                                           **data_dict). \
            order_by('receipt_date', 'location__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0, **data_dict). \
            order_by('receipt_date', 'location__pick_sequence')
        data_dict['location__zone__zone'] = 'TEMP_ZONE'
        del exclude_dict['location__zone__zone']
        stock_detail3 = StockDetail.objects.exclude(**exclude_dict).filter(**data_dict).order_by('receipt_date',
                                                                                                 'location__pick_sequence')
        stock_detail = list(chain(stock_detail1, stock_detail2, stock_detail3))
    else:
        del exclude_dict['location__zone__zone']
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0,
                                                                           **data_dict). \
            order_by('location_id__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0,
                                                                           **data_dict).order_by('receipt_date')
        stock_detail = list(chain(stock_detail1, stock_detail2))
        if back_order == 'true':
            data_dict['location__zone__zone'] = 'BAY_AREA'
            back_stock = StockDetail.objects.filter(**data_dict)
            stock_detail = list(chain(back_stock, stock_detail))
    return stock_detail


def validate_picklist(data, user):
    loc_status = ''
    stock_status = ''
    for key, value in data.iteritems():
        if key == 'code':
            continue
        raw_loc = RMLocation.objects.get(id=key)
        sku = raw_loc.material_picklist.jo_material.material_code
        for val in value:
            location = val['location']
            if location == 'NO STOCK':
                continue
            loc_obj = LocationMaster.objects.filter(location=location, zone__user=user)
            if not loc_obj:
                if not loc_status:
                    loc_status = 'Invalid Location' % (location)
                else:
                    loc_status += ', (%s)' % (location)
            if not val['picked_quantity']:
                continue
            stock_dict = {'sku_id': sku.id, 'location__location': location, 'sku__user': user}
            stock_quantity = StockDetail.objects.filter(**stock_dict).aggregate(Sum('quantity'))['quantity__sum']
            if not stock_quantity:
                stock_quantity = 0
            if stock_quantity < float(val['picked_quantity']):
                if not stock_status:
                    stock_status = "Insufficient stock for " + sku.wms_code
                elif sku.wms_code not in stock_status:
                    stock_status += ', ' + sku.wms_code
    if stock_status:
        loc_status = loc_status + ' ' + stock_status
    return loc_status


@csrf_exempt
@login_required
@get_admin_user
def confirmed_jo_data(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    stages = get_user_stages(user, request.user)
    job_code = request.GET.get('data_id', '')
    job_id = request.GET.get('job_id', '')
    all_data = []
    order_ids = []
    sku_brands = []
    sku_categories = []
    sku_classes = []
    sku_styles = []
    creation_date = ''
    headers = copy.deepcopy(RECEIVE_JO_TABLE_HEADERS)
    stages = list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    temp = get_misc_value('pallet_switch', user.id)

    filter_params = {'product_code__user': user.id, 'product_code_id__in': sku_master_ids,
                     'status__in': ['grn-generated', 'pick_confirm',
                                    'partial_pick']}
    if job_code:
        filter_params['job_code'] = job_code
    else:
        filter_params['id'] = job_id

    record = JobOrder.objects.filter(**filter_params)
    if temp == 'true':
        headers.insert(2, 'Pallet Number')
        headers.append('')
    for rec in record:
        stage_quantity = 0
        if not job_code:
            job_code = rec.job_code
        if not creation_date:
            creation_date = get_local_date(user, rec.creation_date, send_date='true')
            creation_date = creation_date.strftime("%d %b %Y")
        pallet_mapping = PalletMapping.objects.filter(pallet_detail__user=user.id,
                                                      po_location__job_order__job_code=rec.job_code,
                                                      po_location__job_order__product_code__wms_code=rec.product_code.wms_code,
                                                      status=2)
        pallet_ids = list(pallet_mapping.values_list('id', flat=True))
        status_track = StatusTracking.objects.order_by('creation_date').filter(Q(status_id=rec.id, status_type='JO') |
                                                                               Q(status_id__in=pallet_ids,
                                                                                 status_type='JO-PALLET'),
                                                                               quantity__gt=0)

        sku_extra_data, product_images, order_ids = get_order_json_data(user, mapping_id=rec.id, mapping_type='JO',
                                                                        sku_id=rec.product_code_id,
                                                                        order_ids=order_ids)

        sku_cat = rec.product_code.sku_category
        stages_list = copy.deepcopy(stages)

        if rec.product_code.sku_brand and rec.product_code.sku_brand not in sku_brands:
            sku_brands.append(rec.product_code.sku_brand)

        if rec.product_code.sku_category and rec.product_code.sku_category not in sku_categories:
            sku_categories.append(rec.product_code.sku_category)

        if rec.product_code.sku_class and rec.product_code.sku_class not in sku_classes:
            sku_classes.append(rec.product_code.sku_class)

        if rec.product_code.style_name and rec.product_code.style_name not in sku_styles:
            sku_styles.append(rec.product_code.style_name)

        for tracking in status_track:
            rem_stages = stages_list
            if tracking.status_value in stages_list:
                rem_stages = stages_list[stages_list.index(tracking.status_value):]
            cond = (rec.id)
            jo_quantity = tracking.quantity
            stage_quantity += float(tracking.quantity)

            if tracking.status_type == 'JO-PALLET':
                pallet = pallet_mapping.get(id=tracking.status_id)
                all_data.append(
                    {'id': rec.id, 'wms_code': rec.product_code.wms_code, 'sku_desc': rec.product_code.sku_desc,
                     'product_quantity': jo_quantity, 'received_quantity': pallet.pallet_detail.quantity,
                     'pallet_number': pallet.pallet_detail.pallet_code, 'stages_list': rem_stages,
                     'sub_data': [{'received_quantity': jo_quantity,
                                   'pallet_number': pallet.pallet_detail.pallet_code, 'stages_list': rem_stages,
                                   'pallet_id': pallet.id,
                                   'status_track_id': tracking.id}], 'sku_extra_data': sku_extra_data,
                     'product_images': product_images,
                     'load_unit_handle': rec.product_code.load_unit_handle})
            else:
                all_data.append(
                    {'id': rec.id, 'wms_code': rec.product_code.wms_code, 'sku_desc': rec.product_code.sku_desc,
                     'product_quantity': jo_quantity, 'received_quantity': tracking.quantity, 'pallet_number': '',
                     'stages_list': rem_stages, 'sub_data': [{'received_quantity': jo_quantity, 'pallet_number': '',
                                                              'stages_list': rem_stages, 'pallet_id': '',
                                                              'status_track_id': tracking.id}],
                     'sku_extra_data': sku_extra_data, 'product_images': product_images,
                     'load_unit_handle': rec.product_code.load_unit_handle})
        else:
            cond = (rec.id)
            jo_quantity = float(rec.product_quantity) - float(rec.received_quantity) - stage_quantity
            if jo_quantity <= 0:
                continue

            pallet_mapping = PalletMapping.objects.filter(pallet_detail__user=user.id,
                                                          po_location__job_order__job_code=rec.job_code,
                                                          po_location__job_order__product_code__wms_code=rec.product_code.wms_code,
                                                          status=2)

            if pallet_mapping:
                for pallet in pallet_mapping:
                    all_data.append(
                        {'id': rec.id, 'wms_code': rec.product_code.wms_code, 'sku_desc': rec.product_code.sku_desc,
                         'product_quantity': jo_quantity, 'received_quantity': pallet.pallet_detail.quantity,
                         'pallet_number': pallet.pallet_detail.pallet_code, 'stages_list': stages_list,
                         'pallet_id': pallet.id,
                         'status_track_id': '', 'sub_data': [{'received_quantity': jo_quantity,
                                                              'pallet_number': pallet.pallet_detail.pallet_code,
                                                              'stages_list': stages_list, 'pallet_id': pallet.id,
                                                              'status_track_id': ''}],
                         'sku_extra_data': sku_extra_data, 'product_images': product_images,
                         'load_unit_handle': rec.product_code.load_unit_handle})
            else:
                all_data.append(
                    {'id': rec.id, 'wms_code': rec.product_code.wms_code, 'sku_desc': rec.product_code.sku_desc,
                     'product_quantity': jo_quantity, 'received_quantity': jo_quantity, 'pallet_number': '',
                     'stages_list': stages_list, 'status_track_id': '', 'sub_data': [{'received_quantity': jo_quantity,
                                                                                      'pallet_number': '',
                                                                                      'stages_list': stages_list,
                                                                                      'pallet_id': '',
                                                                                      'status_track_id': ''}],
                     'sku_extra_data': sku_extra_data, 'product_images': product_images,
                     'load_unit_handle': rec.product_code.load_unit_handle})

    return HttpResponse(json.dumps({'data': all_data, 'job_code': job_code, 'temp': temp, 'order_ids': order_ids,
                                    'sku_brands': ','.join(sku_brands), 'sku_categories': ','.join(sku_categories),
                                    'sku_classes': ','.join(sku_classes), 'sku_styles': ','.join(sku_styles),
                                    'creation_date': creation_date}))


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
    return pallet_mapping.id


def update_pallet_data(pallet_dict, received, status=''):
    pallet_mapping = PalletMapping.objects.get(id=pallet_dict['pallet_id'])
    pallet_mapping.pallet_detail.pallet_code = pallet_dict['pallet_number']
    pallet_mapping.pallet_detail.quantity = float(received)
    pallet_mapping.po_location.original_quantity = float(received)
    pallet_mapping.po_location.quantity = float(received)
    if not status == '':
        pallet_mapping.po_location.status = status
    pallet_mapping.pallet_detail.save()
    pallet_mapping.po_location.save()


def save_status_tracking(status_id, status_type, status_value, quantity):
    status_dict = copy.deepcopy(STATUS_TRACKING_FIELDS)
    status_dict['status_id'] = status_id
    status_dict['status_type'] = status_type
    status_dict['status_value'] = status_value
    status_dict['original_quantity'] = quantity
    status_dict['quantity'] = quantity
    status_save = StatusTracking(**status_dict)
    status_save.save()
    return status_save


def save_status_track_summary(stats_track, user, processed_quantity=0, processed_stage=''):
    if processed_stage and processed_quantity:
        StatusTrackingSummary.objects.create(status_tracking_id=stats_track.id, processed_stage=processed_stage,
                                             processed_quantity=processed_quantity,
                                             creation_date=datetime.datetime.now())


def group_stage_dict(all_data):
    new_dict = {}
    for key, value in all_data.iteritems():
        for data in value:
            new_dict.setdefault(key, {})
            pallet_number = ''
            grouping_key = data[2]
            if data[1].get('pallet_number', ''):
                grouping_key = str(data[2]) + '<<>>' + str(data[1]['pallet_number'])
            new_dict[key].setdefault(grouping_key, {'quantity': 0, 'pallet_list': [], 'exist_ids': [],
                                                    'imeis': ''})
            new_dict[key][grouping_key]['quantity'] = float(new_dict[key][grouping_key]['quantity']) + float(data[0])
            new_dict[key][grouping_key]['pallet_list'].append({'quantity': data[0], 'pallet_dict': data[1]})
            new_dict[key][grouping_key]['imeis'] = new_dict[key][grouping_key]['imeis'] + str(data[4])
            if data[3]:
                new_dict[key][grouping_key]['exist_ids'].append(data[3])
    return new_dict


def update_status_tracking(status_trackings, quantity, user, to_add=False, save_summary=True):
    processed_quantity = quantity
    for status_tracking in status_trackings:
        if not quantity:
            break
        if to_add:
            status_tracking.original_quantity = float(status_tracking.original_quantity) + quantity
            status_tracking.quantity = float(status_tracking.quantity) + quantity
            quantity = 0
        else:
            if float(status_tracking.original_quantity) <= quantity:
                temp_quantity = float(status_tracking.original_quantity)
                quantity -= temp_quantity
            else:
                temp_quantity = quantity
                quantity = 0
            status_tracking.original_quantity = float(status_tracking.original_quantity) - temp_quantity
            status_tracking.quantity = float(status_tracking.quantity) - temp_quantity
            if save_summary:
                save_status_track_summary(status_tracking, user, temp_quantity,
                                          processed_stage=status_tracking.status_value)
        status_tracking.save()


def build_jo_data(data_list):
    new_dict = {}
    for key, value in data_list.iteritems():
        job_order = JobOrder.objects.get(id=key)
        pallet_mapping = PalletMapping.objects.filter(pallet_detail__user=job_order.product_code.user,
                                                      po_location__job_order__job_code=job_order.job_code,
                                                      po_location__job_order__product_code__wms_code=job_order.product_code.wms_code,
                                                      status=2)
        pallet_ids = pallet_mapping.values_list('id', flat=True)
        status_trackings = StatusTracking.objects.filter(Q(status_id=key, status_type='JO') |
                                                         Q(status_id__in=pallet_ids, status_type='JO-PALLET'),
                                                         quantity__gt=0)
        for status_tracking in status_trackings:
            new_dict.setdefault(key, [])
            pallet_dict = {}
            imeis = value.get(status_tracking.status_value, {}).get('imeis', '')
            if status_tracking.status_type == 'JO-PALLET':
                pallet = pallet_mapping.get(id=status_tracking.status_id)
                pallet_dict = {'pallet_number': pallet.pallet_detail.pallet_code, 'pallet_id': pallet.id}
            new_dict[key].append(
                [float(status_tracking.quantity), pallet_dict, status_tracking.status_value, status_tracking.id,
                 imeis])
    return new_dict


def update_tracking_data(status_id, status_type, job_order, stage, stage_data, stages, is_grn, user,
                         final_update_data=[], updated_status_ids=[]):
    if status_type == 'JO-PALLET':
        jo_status_trackings = StatusTracking.objects.filter(status_id=job_order.id, status_type='JO',
                                                            status_value=stage, quantity__gt=0)
        to_reduce = jo_status_trackings.aggregate(Sum('quantity'))['quantity__sum']
        if jo_status_trackings:
            update_status_tracking(jo_status_trackings, abs(to_reduce), user, to_add=False, save_summary=False)
    status_trackings = StatusTracking.objects.filter(status_id=status_id, status_type=status_type, status_value=stage)
    exist_quantity = status_trackings.aggregate(Sum('quantity'))['quantity__sum']
    existing_objs = StatusTracking.objects.filter(id__in=stage_data['exist_ids']).exclude(id__in=updated_status_ids)
    processed_stage = ''
    if existing_objs:
        processed_stage = existing_objs[0].status_value
    if not exist_quantity:
        exist_quantity = 0
    if not float(exist_quantity) == float(stage_data['quantity']):
        to_reduce = float(exist_quantity) - float(stage_data['quantity'])
        if to_reduce < 0:
            if not status_trackings:
                status_trackings = save_status_tracking(status_id, status_type, stage, abs(to_reduce))
                status_trackings = StatusTracking.objects.filter(id=status_trackings.id)
            else:
                update_status_tracking(status_trackings, abs(to_reduce), user, to_add=True)
                updated_status_ids = list(
                    chain(list(status_trackings.values_list('id', flat=True)), updated_status_ids))
            if existing_objs.exclude(status_value=stage):
                update_status_tracking(existing_objs.exclude(status_value=stage), abs(to_reduce), user, to_add=False)
                updated_status_ids = list(
                    chain(list(status_trackings.values_list('id', flat=True)), updated_status_ids))
        else:
            update_status_tracking(status_trackings, abs(to_reduce), user, to_add=False)
            updated_status_ids = list(chain(list(status_trackings.values_list('id', flat=True)), updated_status_ids))
        if is_grn and stages and stages[-1] == stage and status_trackings.filter(quantity__gt=0):
            final_update_data.append([status_trackings.filter(quantity__gt=0), abs(to_reduce), user, False])
    return final_update_data, updated_status_ids


def save_receive_pallet(all_data, user, is_grn=False):
    all_data1 = copy.deepcopy(all_data)
    all_data = group_stage_dict(all_data)
    final_update_data = []
    stages = list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    updated_status_ids = []
    for key, value in all_data.iteritems():
        job_order = JobOrder.objects.get(id=key)
        for stage, stage_data in value.iteritems():
            grouping_key = stage
            pallet_num = ''
            if '<<>>' in stage:
                stage, pallet_num = stage.split('<<>>')
            for val_ind, pal_dict in enumerate(stage_data.get('pallet_list', [])):
                pallet_dict = pal_dict['pallet_dict']
                if pallet_dict.get('pallet_id') or (pallet_dict.get('pallet_number', '')):
                    status_type = 'JO-PALLET'
                    if pallet_dict['pallet_id']:
                        update_pallet_data(pallet_dict, pal_dict['quantity'])
                        pallet_id = pallet_dict['pallet_id']
                        final_update_data, updated_status_ids = update_tracking_data(pallet_id, 'JO-PALLET', job_order,
                                                                                     stage, stage_data,
                                                                                     stages, is_grn, user,
                                                                                     final_update_data=final_update_data,
                                                                                     updated_status_ids=updated_status_ids)
                    else:
                        status = 2
                        location_data = {'job_order_id': job_order.id, 'location_id': None, 'status': status,
                                         'quantity': float(pal_dict['quantity']),
                                         'original_quantity': float(pal_dict['quantity']),
                                         'creation_date': datetime.datetime.now()}
                        po_location = POLocation(**location_data)
                        po_location.save()
                        pallet_dict2 = {'pallet_number': pallet_dict['pallet_number'],
                                        'received_quantity': float(pal_dict['quantity']),
                                        'user': user.id}
                        pallet_id = insert_pallet_data(pallet_dict2, po_location, 2)
                        all_data[key][grouping_key]['pallet_list'][val_ind]['pallet_dict']['pallet_id'] = pallet_id
                        stage_data['quantity'] = float(pal_dict['quantity'])
                        stage_data['pallet_list'][val_ind]['pallet_dict']['pallet_id'] = pallet_id
                        final_update_data, updated_status_ids = update_tracking_data(pallet_id, 'JO-PALLET', job_order,
                                                                                     stage, stage_data,
                                                                                     stages, is_grn, user,
                                                                                     final_update_data=final_update_data,
                                                                                     updated_status_ids=updated_status_ids)

                else:
                    job_order.saved_quantity = float(stage_data['quantity'])
                    job_order.save()
                    final_update_data, updated_status_ids = update_tracking_data(key, 'JO', job_order, stage,
                                                                                 stage_data, stages,
                                                                                 is_grn, user,
                                                                                 final_update_data=final_update_data,
                                                                                 updated_status_ids=updated_status_ids)

    new_data = build_jo_data(all_data)
    for final_data in final_update_data:
        update_status_tracking(*final_data)
    return new_data


@csrf_exempt
@login_required
@get_admin_user
def save_receive_jo(request, user=''):
    all_data = {}
    try:
        log.info('Request params Save Receive JO for user %s are %s' % (user.username,
                                                                        str(dict(request.POST.iterlists()))))
        data_dict = dict(request.POST.iterlists())
        for i in range(len(data_dict['id'])):
            pallet_dict = {}
            if data_dict.get('pallet_number', '') and not data_dict['pallet_number'][0] == '':
                pallet_dict = {'pallet_number': data_dict['pallet_number'][i], 'pallet_id': data_dict['pallet_id'][i]}
            cond = (data_dict['id'][i])
            all_data.setdefault(cond, [])
            rec_quantity = data_dict['received_quantity'][i]
            if not rec_quantity:
                rec_quantity = 0
            imeis = ''
            all_data[cond].append(
                [rec_quantity, pallet_dict, data_dict['stage'][i], data_dict['status_track_id'][i],
                 imeis])
        save_receive_pallet(all_data, user)

        return HttpResponse("Saved Successfully")
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Save Receive JO failed for %s and params are %s and error statement is %s' %
                                                            (str(user.username), str(dict(request.POST.iterlists())),
                                                                    str(e)))
        return HttpResponse("Save Receive JO Failed")

@csrf_exempt
@login_required
@get_admin_user
def confirm_jo_grn(request, user=''):
    total_received_qty = 0
    total_order_qty = 0
    all_data = {}
    pre_product = 0
    stages = list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    stage_status = []
    putaway_data = {GRN_HEADERS: []}
    try:
        log.info('Request params Confirm JO GRN for user %s are %s' % (user.username,
                                                                       str(dict(request.POST.iterlists()))))
        data_dict = dict(request.POST.iterlists())
        for i in range(len(data_dict['id'])):
            pallet_dict = {}
            if data_dict.get('pallet_number', '') and not data_dict['pallet_number'][0] == '':
                pallet_dict = {'pallet_number': data_dict['pallet_number'][i], 'pallet_id': data_dict['pallet_id'][i]}
            cond = (data_dict['id'][i])
            all_data.setdefault(cond, [])
            rec_quantity = data_dict['received_quantity'][i]
            if not rec_quantity:
                rec_quantity = 0
            imeis = ''
            if 'imei_numbers' in data_dict.keys() and data_dict['imei_numbers'][i]:
                imeis = data_dict['imei_numbers'][i]
            all_data[cond].append(
                [rec_quantity, pallet_dict, data_dict['stage'][i], data_dict['status_track_id'][i],
                 imeis])

        all_data = save_receive_pallet(all_data, user, is_grn=True)

        for key, value in all_data.iteritems():
            count = 0
            job_order = JobOrder.objects.get(id=key)
            # pre_product = int(job_order.product_quantity) - int(job_order.received_quantity)
            sku_cat = job_order.product_code.sku_category
            stages_list = copy.deepcopy(stages)
            stats_track = ''
            for val in value:
                if stages_list:
                    if not val[3]:
                        stage_status.append(job_order.product_code.wms_code)
                        continue
                    stats_track = StatusTracking.objects.get(id=val[3])
                    if not stats_track.status_value == stages_list[-1]:
                        stage_status.append(job_order.product_code.wms_code)
                        continue
                count += float(val[0])
                pre_product = float(val[0])
                zone = job_order.product_code.zone
                if zone:
                    put_zone = zone.zone
                else:
                    put_zone = 'DEFAULT'
                temp_dict = {'user': user.id, 'sku': job_order.product_code}
                if val[1].get('pallet_number', ''):
                    temp_dict['pallet_number'] = val[1]['pallet_number']
                temp_dict['data'] = job_order
                locations = get_purchaseorder_locations(put_zone, temp_dict)
                job_order.received_quantity = float(job_order.received_quantity) + float(val[0])
                received_quantity = float(val[0])
                if val[4]:
                    insert_jo_mapping(val[4], job_order, user.id)
                for loc in locations:
                    if loc.zone.zone != 'DEFAULT':
                        location_quantity, received_quantity = get_remaining_capacity(loc, received_quantity, put_zone,
                                                                                      val[1], user.id)
                    else:
                        location_quantity = received_quantity
                        received_quantity = 0
                    if not location_quantity:
                        continue
                    job_order.status = 'grn-generated'
                    if val[1].get('pallet_id', ''):
                        pallet_mapping = PalletMapping.objects.get(id=val[1]['pallet_id'])
                        pallet_mapping.po_location.location_id = loc.id
                        pallet_mapping.po_location.status = 1
                        pallet_mapping.po_location.save()
                        pallet_mapping.status = 1
                        pallet_mapping.save()
                    else:
                        job_order.saved_quantity = 0
                        location_data = {'job_order_id': job_order.id, 'location_id': loc.id, 'status': 1}

                        save_update_order(location_quantity, location_data, {}, 'job_order__product_code__user', user.id)
                    if not received_quantity or received_quantity == 0:
                        break
                if stats_track:
                    stats_track.quantity = float(stats_track.quantity) - float(val[0])
                    stats_track.save()
                total_received_qty += float(val[0])
                total_order_qty += pre_product
            if count:
                putaway_data[GRN_HEADERS].append((job_order.product_code.wms_code, pre_product, count))
            if job_order.received_quantity >= job_order.product_quantity:
                job_order.status = 'location-assigned'
            job_order.save()
        if not putaway_data.values()[0]:
            return HttpResponse(json.dumps({
                'status': "Complete the production process to generate GRN for wms codes " + ", ".join(
                    list(set(stage_status))), 'data': all_data}))
        return render(request, 'templates/toggle/jo_grn.html', {'data': putaway_data, 'job_code': job_order.job_code,
                                                                'total_received_qty': total_received_qty,
                                                                'total_order_qty': total_order_qty,
                                                                'order_date': job_order.creation_date})
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Confirm JO GRN failed for %s and params are %s and error statement is %s' %
                                                                    (str(user.username),
                                                                     str(dict(request.POST.iterlists())),
                                                                    str(e)))
        return HttpResponse("Confirm JO GRN Failed")


@csrf_exempt
@login_required
@get_admin_user
def received_jo_data(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    job_code = request.GET['data_id']
    all_data = []
    headers = PUTAWAY_HEADERS
    order_ids = []
    temp = get_misc_value('pallet_switch', user.id)
    record = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id,
                                     status__in=['location-assigned', 'grn-generated'],
                                     product_code_id__in=sku_master_ids).order_by('id')
    if temp == 'true' and 'Pallet Number' not in headers:
        headers.insert(2, 'Pallet Number')
    for rec in record:
        po_location = POLocation.objects.exclude(location__isnull=True).filter(job_order_id=rec.id, status=1,
                                                                               job_order__product_code__user=user.id)
        sku_extra_data, product_images, order_ids = get_order_json_data(user, mapping_id=rec.id,
                                                                        mapping_type='JO', sku_id=rec.product_code_id,
                                                                        order_ids=order_ids)
        for location in po_location:
            pallet_mapping = PalletMapping.objects.filter(pallet_detail__user=user.id, po_location_id=location.id,
                                                          status=1)

            if pallet_mapping:
                for pallet in pallet_mapping:
                    all_data.append({'id': location.id, 'wms_code': rec.product_code.wms_code,
                                     'location': location.location.location,
                                     'product_quantity': location.quantity, 'putaway_quantity': location.quantity,
                                     'sku_extra_data': sku_extra_data, 'product_images': product_images,
                                     'pallet_code': pallet.pallet_detail.pallet_code,
                                     'sub_data': [{'putaway_quantity': location.quantity,
                                                   'location': location.location.location}],
                                     'load_unit_handle': rec.product_code.load_unit_handle})
            else:
                all_data.append(
                    {'id': location.id, 'wms_code': rec.product_code.wms_code, 'location': location.location.location,
                     'product_quantity': location.quantity, 'putaway_quantity': location.quantity, 'pallet_code': '',
                     'sku_extra_data': sku_extra_data, 'product_images': product_images,
                     'sub_data': [{'putaway_quantity': location.quantity, 'location': location.location.location}],
                     'load_unit_handle': rec.product_code.load_unit_handle})
    return HttpResponse(json.dumps({'data': all_data, 'job_code': job_code, 'temp': temp, 'order_ids': order_ids}))


def validate_locations(all_data, user):
    status = ''
    for key, value in all_data.iteritems():
        for val in value:
            location = LocationMaster.objects.filter(location=val[0], zone__user=user)
            if not location:
                if not status:
                    status = 'Invalid Locations ' + val[0]
                else:
                    status += ',' + val[0]
    return status


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


@csrf_exempt
@login_required
@get_admin_user
def jo_putaway_data(request, user=''):
    all_data = {}
    putaway_stock_data = {}
    data_dict = dict(request.POST.iterlists())
    mod_locations = []
    for i in range(len(data_dict['id'])):
        cond = (data_dict['id'][i])
        all_data.setdefault(cond, [])
        cond_list = [data_dict['location'][i], data_dict['putaway_quantity'][i], data_dict['pallet_number'][i]]
        batch_no, mrp, mfg_date, exp_date = '','','',''
        if 'batch_no' in data_dict:
            batch_no = data_dict['batch_no'][i]
        if 'mrp' in data_dict:
            mrp = data_dict['mrp'][i]
        if 'mfg_date' in data_dict:
            mfg_date = data_dict['mfg_date'][i]
        if 'exp_date' in data_dict:
            exp_date = data_dict['exp_date'][i]
        cond_list.append(batch_no)
        cond_list.append(mrp)
        cond_list.append(mfg_date)
        cond_list.append(exp_date)
        all_data[cond].append(cond_list)

    status = validate_locations(all_data, user.id)
    if status:
        return HttpResponse(status)
    for key, value in all_data.iteritems():
        data = POLocation.objects.get(id=key)
        for val in value:
            location = LocationMaster.objects.get(location=val[0], zone__user=user.id)
            if not val[1] or val[1] == '0':
                continue
            putaway_location(data, float(val[1]), location.id, user, 'job_order_id', data.job_order_id)
            filter_params = {'location_id': location.id, 'receipt_number': data.job_order.job_code,
                             'sku_id': data.job_order.product_code_id, 'sku__user': user.id,
                             'receipt_type': 'job order'}
            create_batch_rec = False
            if val[3] or val[4] or val[5] or val[6]:
                create_batch_param = {'batch_no':val[3], 'mrp':val[4], 'manufactured_date':val[5],
                                        'expiry_date':val[6],'transact_id':data.job_order.id, 
                                        'transact_type':'jo'}
                create_batch_rec = create_update_batch_data(create_batch_param)
                if create_batch_rec:
                    filter_params['batch_detail_id'] = create_batch_rec.id
            stock_data = StockDetail.objects.filter(**filter_params)
            pallet_mapping = PalletMapping.objects.filter(po_location_id=data.id, status=1)
            if pallet_mapping:
                stock_data = StockDetail.objects.filter(pallet_detail_id=pallet_mapping[0].pallet_detail.id,
                                                        **filter_params)
            if pallet_mapping:
                setattr(location, 'pallet_filled', float(location.pallet_filled) + 1)
            else:
                setattr(location, 'filled_capacity', float(location.filled_capacity) + float(val[1]))
            if location.pallet_filled > location.pallet_capacity:
                setattr(location, 'pallet_capacity', location.pallet_filled)
            location.save()
            if stock_data:
                stock_data = stock_data[0]
                add_quan = float(stock_data.quantity) + float(val[1])
                setattr(stock_data, 'quantity', add_quan)
                if pallet_mapping:
                    pallet_detail = pallet_mapping[0].pallet_detail
                    setattr(stock_data, 'pallet_detail_id', pallet_detail.id)
                stock_data.save()
                stock_detail = stock_data
                mod_locations.append(stock_data.location.location)
            else:
                record_data = {'location_id': location.id, 'receipt_number': data.job_order.job_code,
                               'receipt_date': str(data.job_order.creation_date).split('+')[0],
                               'sku_id': data.job_order.product_code_id,
                               'quantity': val[1], 'status': 1, 'creation_date': datetime.datetime.now(),
                               'updation_date': datetime.datetime.now(), 'receipt_type': 'job order'}
                if create_batch_rec:
                    record_data['batch_detail_id'] = create_batch_rec.id
                if pallet_mapping:
                    record_data['pallet_detail_id'] = pallet_mapping[0].pallet_detail.id
                    pallet_mapping[0].status = 0
                    pallet_mapping[0].save()
                stock_detail = StockDetail(**record_data)
                stock_detail.save()
                mod_locations.append(stock_detail.location.location)

            # SKU Stats
            save_sku_stats(user, stock_detail.sku_id, data.job_order_id, 'jo', float(val[1]))
            # Collecting data for auto stock allocation
            putaway_stock_data.setdefault(stock_detail.sku_id, [])
            putaway_stock_data[stock_detail.sku_id].append(data.job_order_id)

        putaway_quantity = POLocation.objects.filter(job_order_id=data.job_order_id,
                                                     job_order__product_code__user=user.id, status=0). \
            aggregate(Sum('original_quantity'))['original_quantity__sum']
        if not putaway_quantity:
            putaway_quantity = 0
        diff_quantity = float(data.job_order.received_quantity) - float(putaway_quantity)
        if (float(data.job_order.received_quantity) >= float(data.job_order.product_quantity)) and (diff_quantity <= 0):
            data.job_order.status = 'confirmed-putaway'

        data.job_order.save()

    if mod_locations:
        update_filled_capacity(list(set(mod_locations)), user.id)

    # Auto Allocate Stock
    order_allocate_stock(request, user, stock_data=putaway_stock_data, mapping_type='JO')

    return HttpResponse('Updated Successfully')


def validate_locations(all_data, user):
    status = ''
    for key, value in all_data.iteritems():
        for val in value:
            location = LocationMaster.objects.filter(location=val[0], zone__user=user)
            if not location:
                if not status:
                    status = 'Invalid Locations ' + val[0]
                else:
                    status += ',' + val[0]
    return status


def putaway_location(data, value, exc_loc, user, order_id, po_id):
    diff_quan = 0
    if float(data.quantity) >= float(value):
        diff_quan = float(data.quantity) - float(value)
        data.quantity = diff_quan
    if diff_quan == 0:
        data.status = 0
    if not data.location_id == exc_loc:
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


@csrf_exempt
@login_required
@get_admin_user
def delete_jo_group(request, user=''):
    log.info('Request params Delete Job Order Group are ' + str(request.POST.dict()))
    try:
        data_dict = dict(request.POST.iterlists())
        status_dict = {'Self Produce': 'SP', 'Vendor Produce': 'VP'}
        for key, value in request.POST.iteritems():
            jo_reference = value
            job_order = JobOrder.objects.filter(jo_reference=jo_reference, order_type=status_dict[key],
                                                product_code__user=user.id)
            delete_jo_list(job_order)
        return HttpResponse("Deleted Successfully")
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(
            'Delete Job Order Group failed for %s and params are %s and error statement is %s' % (str(user.username),
                                                                                                  str(
                                                                                                      request.POST.dict()),
                                                                                                  str(e)))
        return HttpResponse("Deletion Failed")


@csrf_exempt
@login_required
@get_admin_user
def confirm_jo_group(request, user=''):
    log.info('Request params for Confirm JO Group are ' + str(request.POST.dict()))
    try:
        job_data = {}
        data_dict = dict(request.POST.iterlists())
        status_dict = {'Self Produce': 'SP', 'Vendor Produce': 'VP'}
        for key, value in request.POST.iteritems():
            tot_mat_qty = 0
            tot_pro_qty = 0
            all_data = {}
            sku_list = []
            jo_reference = value
            job_order = JobOrder.objects.filter(jo_reference=jo_reference, order_type=status_dict[key],
                                                product_code__user=user.id)
            job_code = get_job_code(user.id)
            for order in job_order:
                p_quantity = order.product_quantity
                if order.product_code.sku_code not in sku_list and p_quantity:
                    sku_list.append(order.product_code.sku_code)
                    tot_pro_qty += float(p_quantity)
                jo_material = JOMaterial.objects.filter(job_order__id=order.id, material_code__user=user.id)
                for material in jo_material:
                    data_id = material.id
                    cond = (order.product_code.wms_code)
                    all_data.setdefault(cond, [])
                    all_data[cond].append({order.product_quantity: [material.material_code.wms_code,
                                                                    material.material_quantity, data_id,
                                                                    material.unit_measurement_type,
                                                                    order.product_code.wms_code]})
                    tot_mat_qty += float(material.material_quantity)
            c_date = JobOrder.objects.filter(job_code=job_code, order_type=status_dict[key], product_code__user=user.id)
            if c_date:
                creation_date = get_local_date(user, c_date[0].creation_date)
            else:
                creation_date = get_local_date(user, datetime.datetime.now())
            job_data[job_code] = {'all_data': all_data, 'tot_pro_qty': tot_pro_qty, 'tot_mat_qty': tot_mat_qty,
                                  'creation_date': creation_date}
            status = validate_jo(all_data, user.id, jo_reference=jo_reference)
        if not status:
            confirm_job_order(all_data, user.id, jo_reference, job_code)
            # status = save_jo_locations(all_data, user, job_code)
            status = "Confirmed Successfully"
        else:
            return HttpResponse(status)

        # Send Job Order Mail
        send_job_order_mail(request, user, job_code)

        user_profile = UserProfile.objects.get(user_id=user.id)
        user_data = {'company_name': user_profile.company_name, 'username': user.username,
                     'location': user_profile.location}

        return render(request, 'templates/toggle/jo_template_group.html',
                      {'job_data': job_data, 'user_data': user_data, 'headers': RAISE_JO_HEADERS})

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(
            'Confirm Job Order Group failed for %s and params are %s and error statement is %s' % (str(user.username),
                                                                                                   str(
                                                                                                       request.POST.dict()),
                                                                                                   str(e)))
        return HttpResponse("Cofirm Job Order Failed")


@get_admin_user
def print_rm_picklist(request, user=''):
    temp = []
    title = 'Job Code'
    data_id = request.GET['data_id']
    data = get_raw_picklist_data(data_id, user)
    all_data = {}
    total = 0
    total_price = 0
    type_mapping = SkuTypeMapping.objects.filter(user=user.id)
    for record in data:
        for mapping in type_mapping:
            if mapping.prefix in record['wms_code']:
                cond = (mapping.item_type)
                all_data.setdefault(cond, [0, 0])
                all_data[cond][0] += record['reserved_quantity']
                break
        else:
            total += record['reserved_quantity']

    for key, value in all_data.iteritems():
        total += float(value[0])
        total_price += float(value[1])

    return render(request, 'templates/toggle/print_raw_material_picklist.html',
                  {'data': data, 'all_data': all_data, 'headers': PRINT_PICKLIST_HEADERS, 'job_id': data_id,
                   'total_quantity': total, 'total_price': total_price, 'title': title})


@csrf_exempt
def get_rm_back_order_data_alt(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                               filters='', special_key=''):
    search_params = {'material_code__user': user.id, 'status': 1}
    purchase_dict = {'open_po__sku__user': user.id}
    if special_key == 'Self Produce':
        search_params['job_order__order_type'] = 'SP'
    else:
        search_params['job_order__order_type'] = 'VP'
        search_params['job_order__vendor__vendor_id'] = special_key
    order_detail = JOMaterial.objects.filter(**search_params).values('material_code__wms_code',
                                                                     'material_code__sku_code',
                                                                     'job_order__job_code', 'material_quantity',
                                                                     'job_order_id',
                                                                     'material_code__sku_desc', 'job_order__order_type',
                                                                     'material_code_id').distinct()
    if search_params['job_order__order_type'] == 'SP':
        purchase_dict['open_po__vendor_id__isnull'] = True
        purchase_dict['open_po__order_type'] = 'SR'
        stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values('sku_id').distinct(). \
            annotate(in_stock=Sum('quantity'))
        reserved_objs = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1, reserved__gt=0).values(
            'stock__sku_id').distinct(). \
            annotate(reserved=Sum('reserved'))
        reserveds = map(lambda d: d['stock__sku_id'], reserved_objs)
    else:
        purchase_dict['open_po__vendor_id__isnull'] = False
        purchase_dict['open_po__order_type'] = 'VR'
        purchase_dict['open_po__vendor__vendor_id'] = special_key
        stock_objs = VendorStock.objects.filter(sku__user=user.id, quantity__gt=0, vendor__vendor_id=special_key). \
            values('sku_id').distinct().annotate(in_stock=Sum('quantity'))
        reserved_objs = VendorPicklist.objects.filter(jo_material__job_order__vendor__vendor_id=special_key,
                                                      jo_material__material_code__user=user.id,
                                                      reserved_quantity__gt=0, status='open').values(
            'jo_material__material_code_id'). \
            distinct().annotate(reserved=Sum('reserved_quantity'))
        reserveds = map(lambda d: d['jo_material__material_code_id'], reserved_objs)

    purchase_objs = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']). \
        filter(**purchase_dict).values('open_po__sku_id'). \
        annotate(total_order=Sum('open_po__order_quantity'), total_received=Sum('received_quantity'))
    purchases = map(lambda d: d['open_po__sku_id'], purchase_objs)

    stocks = map(lambda d: d['sku_id'], stock_objs)
    in_stocks = map(lambda d: d['in_stock'], stock_objs)
    reserved_quans = map(lambda d: d['reserved'], reserved_objs)
    purchase_total_order = map(lambda d: d['total_order'], purchase_objs)
    purchase_total_received = map(lambda d: d['total_received'], purchase_objs)

    master_data = []
    allocated_qty = {}
    all_rw_orders = RWOrder.objects.filter(vendor__user=user.id).values('job_order__product_code__sku_code',
                                                                        'job_order__job_code').distinct()
    rw_sku_codes = map(lambda d: d['job_order__product_code__sku_code'], all_rw_orders)
    for order in order_detail:
        remained_quantity = 0
        stock_quantity = 0
        reserved_quantity = 0
        transit_quantity = 0
        sku_code = order['material_code__sku_code']
        title = order['material_code__sku_desc']
        wms_code = order['material_code__wms_code']
        filter_params = {'material_code__wms_code': wms_code, 'material_code__user': user.id, 'status': 1,
                         'job_order__order_type': 'SP'}
        if order['job_order__order_type'] == 'VP':
            filter_params['job_order__order_type'] = 'VP'
            filter_params['job_order__vendor__vendor_id'] = special_key

        sku_rw_orders = filter(lambda person: sku_code == person['job_order__product_code__sku_code'], all_rw_orders)
        if sku_rw_orders:
            filter_params['job_order__job_code__in'] = map(lambda d: d['job_order__job_code'], sku_rw_orders)

        order_quantity = order['material_quantity']
        if not order_quantity:
            order_quantity = 0
        if order['material_code_id'] in stocks:
            stock_quantity = in_stocks[stocks.index(order['material_code_id'])]
            if order['material_code_id'] in allocated_qty.keys():
                if stock_quantity < allocated_qty[order['material_code_id']]:
                    # remained_quantity = order_quantity - stock_quantity + allocated_qty[order['material_code_id']]
                    remained_quantity = allocated_qty[order['material_code_id']] - stock_quantity
                    stock_quantity = 0
                else:
                    stock_quantity -= allocated_qty[order['material_code_id']]

        if order['material_code_id'] in allocated_qty.keys():
            allocated_qty[order['material_code_id']] += order_quantity
        else:
            allocated_qty[order['material_code_id']] = order_quantity
        if order['material_code_id'] in reserveds:
            reserved_quantity = reserved_quans[reserveds.index(order['material_code_id'])]
        if order['material_code_id'] in purchases:
            total_order = purchase_total_order[purchases.index(order['material_code_id'])]
            total_received = purchase_total_received[purchases.index(order['material_code_id'])]
            diff_quantity = float(total_order) - float(total_received)
            if diff_quantity > 0:
                transit_quantity = diff_quantity
                if remained_quantity > 0:
                    if transit_quantity > remained_quantity:
                        transit_quantity -= remained_quantity
                    else:
                        transit_quantity = 0

        procured_quantity = order_quantity - stock_quantity - transit_quantity
        if procured_quantity > 0:
            checkbox = "<input type='checkbox' id='back-checked' name='%s'>" % title
            master_data.append({'': checkbox, 'WMS Code': wms_code, 'Ordered Quantity': order_quantity,
                                'Job Code': str(order['job_order__job_code']), 'order_id': order['job_order_id'],
                                'Stock Quantity': get_decimal_limit(user.id, stock_quantity),
                                'Transit Quantity': get_decimal_limit(user.id, transit_quantity),
                                'Procurement Quantity': get_decimal_limit(user.id, procured_quantity),
                                'DT_RowClass': 'results'})
    if search_term:
        search_term = str(search_term).upper()
        master_data = filter(
            lambda person: search_term in person['Job Code'] or search_term in person['WMS Code'].upper() or \
                           search_term in str(person['Ordered Quantity']) or \
                           search_term in str(person['Stock Quantity']) or search_term in str(
                person['Transit Quantity']) or \
                           search_term in str(person['Procurement Quantity']), master_data)
    if order_term:
        if order_term == 'asc':
            master_data = sorted(master_data, key=lambda x: x[BACK_ORDER_RM_TABLE[col_num - 1]])
        else:
            master_data = sorted(master_data, key=lambda x: x[BACK_ORDER_RM_TABLE[col_num - 1]], reverse=True)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    temp_data['aaData'] = master_data[start_index:stop_index]


@csrf_exempt
def get_rm_back_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                           filters='', special_key=''):
    search_params = {'material_code__user': user.id, 'status': 1}
    purchase_dict = {'open_po__sku__user': user.id}
    if special_key == 'Self Produce':
        search_params['job_order__order_type'] = 'SP'
    else:
        search_params['job_order__order_type'] = 'VP'
        search_params['job_order__vendor__vendor_id'] = special_key
    order_detail = JOMaterial.objects.filter(**search_params).values('material_code__wms_code',
                                                                     'material_code__sku_code',
                                                                     'material_code__sku_desc', 'job_order__order_type',
                                                                     'material_code_id').distinct()

    if search_params['job_order__order_type'] == 'SP':
        purchase_dict['open_po__vendor_id__isnull'] = True
        purchase_dict['open_po__order_type'] = 'SR'
        stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values('sku_id').distinct(). \
            annotate(in_stock=Sum('quantity'))
        reserved_objs = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1, reserved__gt=0).values(
            'stock__sku_id').distinct(). \
            annotate(reserved=Sum('reserved'))
        reserveds = map(lambda d: d['stock__sku_id'], reserved_objs)
    else:
        purchase_dict['open_po__vendor_id__isnull'] = False
        purchase_dict['open_po__order_type'] = 'VR'
        purchase_dict['open_po__vendor__vendor_id'] = special_key
        stock_objs = VendorStock.objects.filter(sku__user=user.id, quantity__gt=0, vendor__vendor_id=special_key). \
            values('sku_id').distinct().annotate(in_stock=Sum('quantity'))
        reserved_objs = VendorPicklist.objects.filter(jo_material__job_order__vendor__vendor_id=special_key,
                                                      jo_material__material_code__user=user.id,
                                                      reserved_quantity__gt=0, status='open').values(
            'jo_material__material_code_id'). \
            distinct().annotate(reserved=Sum('reserved_quantity'))
        reserveds = map(lambda d: d['jo_material__material_code_id'], reserved_objs)

    purchase_objs = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']). \
        filter(**purchase_dict).values('open_po__sku_id'). \
        annotate(total_order=Sum('open_po__order_quantity'), total_received=Sum('received_quantity'))
    purchases = map(lambda d: d['open_po__sku_id'], purchase_objs)

    stocks = map(lambda d: d['sku_id'], stock_objs)

    master_data = []
    for order in order_detail:
        stock_quantity = 0
        reserved_quantity = 0
        transit_quantity = 0
        sku_code = order['material_code__sku_code']
        title = order['material_code__sku_desc']
        wms_code = order['material_code__wms_code']
        filter_params = {'material_code__wms_code': wms_code, 'material_code__user': user.id, 'status': 1,
                         'job_order__order_type': 'SP'}
        if order['job_order__order_type'] == 'VP':
            filter_params['job_order__order_type'] = 'VP'
            filter_params['job_order__vendor__vendor_id'] = special_key

        rw_orders = RWOrder.objects.filter(job_order__product_code__sku_code=sku_code, vendor__user=user.id). \
            values_list('job_order_id', flat=True)
        if rw_orders:
            filter_params['job_order_id__in'] = rw_orders
        order_quantity = JOMaterial.objects.filter(**filter_params). \
            aggregate(Sum('material_quantity'))['material_quantity__sum']
        if not order_quantity:
            order_quantity = 0
        if order['material_code_id'] in stocks:
            stock_quantity = map(lambda d: d['in_stock'], stock_objs)[stocks.index(order['material_code_id'])]
        if order['material_code_id'] in reserveds:
            reserved_quantity = map(lambda d: d['reserved'], reserved_objs)[reserveds.index(order['material_code_id'])]
        if order['material_code_id'] in purchases:
            total_order = map(lambda d: d['total_order'], purchase_objs)[purchases.index(order['material_code_id'])]
            total_received = map(lambda d: d['total_received'], purchase_objs)[
                purchases.index(order['material_code_id'])]
            diff_quantity = float(total_order) - float(total_received)
            if diff_quantity > 0:
                transit_quantity = diff_quantity
        procured_quantity = order_quantity - stock_quantity - transit_quantity
        if procured_quantity > 0:
            checkbox = "<input type='checkbox' id='back-checked' name='%s'>" % title
            master_data.append({'': checkbox, 'WMS Code': wms_code, 'Ordered Quantity': order_quantity,
                                'Stock Quantity': get_decimal_limit(user.id, stock_quantity), 'order_id': "",
                                'Transit Quantity': get_decimal_limit(user.id, transit_quantity),
                                'Procurement Quantity': get_decimal_limit(user.id, procured_quantity),
                                'DT_RowClass': 'results'})

    back_order_headers = ['WMS Code', 'WMS Code', 'Ordered Quantity', 'Stock Quantity', 'Transit Quantity',
                          'Procurement Quantity']
    if search_term:
        master_data = filter(
            lambda person: search_term in person['WMS Code'] or search_term in str(person['Ordered Quantity']) or \
                           search_term in str(person['Stock Quantity']) or search_term in str(
                person['Transit Quantity']) or \
                           search_term in str(person[' Procurement Quantity']), master_data)
    elif order_term:
        if order_term == 'asc':
            master_data = sorted(master_data, key=lambda x: x[back_order_headers[col_num]])
        else:
            master_data = sorted(master_data, key=lambda x: x[back_order_headers[col_num]], reverse=True)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    temp_data['aaData'] = master_data[start_index:stop_index]


@csrf_exempt
@get_admin_user
def generate_rm_po_data(request, user=''):
    data_dict = []
    supplier_list = []
    suppliers = SupplierMaster.objects.filter(user=user.id)
    for supplier in suppliers:
        supplier_list.append({'id': supplier.id, 'name': supplier.name})
    for key, value in request.POST.iteritems():
        price = 0
        key = key.split(":")
        wms_code = key[0]
        job_order_id = ''
        title = key[1]
        if len(key) > 2:
            job_order_id = key[2]
        selected_item = ''
        sku_supplier = SKUSupplier.objects.filter(sku__wms_code=wms_code, sku__user=user.id)
        if sku_supplier:
            selected_item = {'id': sku_supplier[0].supplier_id, 'name': sku_supplier[0].supplier.name}
            price = sku_supplier[0].price
        data_dict.append(
            {'wms_code': wms_code, 'title': title, 'quantity': value, 'selected_item': selected_item, 'price': price,
             'job_order_id': job_order_id})
    return HttpResponse(json.dumps({'data_dict': data_dict, 'supplier_list': supplier_list}))


def get_grn_json_data(order, user, request):
    purchase_order_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id, order_id=order.order_id)
    total = 0
    total_qty = 0
    po_data = []
    for purchase_order in purchase_order_data:

        amount = float(purchase_order.open_po.order_quantity) * float(purchase_order.open_po.price)

        supplier_code = ''
        supplier_mapping = SKUSupplier.objects.filter(sku_id=purchase_order.open_po.sku_id,
                                                      supplier_id=purchase_order.open_po.supplier_id,
                                                      sku__user=user.id)
        if supplier_mapping:
            supplier_code = supplier_mapping[0].supplier_code

        tax = purchase_order.open_po.sgst_tax + purchase_order.open_po.cgst_tax + purchase_order.open_po.igst_tax + purchase_order.open_po.utgst_tax
        if not tax:
            total += amount
        else:
            total += amount + ((amount / 100) * float(tax))
            supplier = purchase_order.open_po.supplier
            total_qty += purchase_order.open_po.order_quantity

        po_data.append((purchase_order.open_po.sku.sku_code, supplier_code, purchase_order.open_po.sku.sku_desc,
                        purchase_order.open_po.order_quantity, purchase_order.open_po.price, amount,
                        purchase_order.open_po.sgst_tax, purchase_order.open_po.cgst_tax,
                        purchase_order.open_po.igst_tax, purchase_order.open_po.utgst_tax,
                        purchase_order.open_po.remarks))

    wms_code = order.open_po.sku.wms_code
    telephone = order.open_po.supplier.phone_number
    name = order.open_po.supplier.name
    order_id = order.order_id
    supplier_email = order.open_po.supplier.email_id
    gstin_no = order.open_po.supplier.tin_number
    order_date = get_local_date(request.user, order.creation_date)
    address = '\n'.join(order.open_po.supplier.address.split(','))
    vendor_name = ''
    vendor_address = ''
    vendor_telephone = ''
    if purchase_order.open_po.order_type == 'VR':
        vendor_address = order.open_po.vendor.address
        vendor_address = '\n'.join(vendor_address.split(','))
        vendor_name = order.open_po.vendor.name
        vendor_telephone = order.open_po.vendor.phone_number

    po_reference = '%s%s_%s' % (order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order.order_id)
    table_headers = (
        'WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Unit Price', 'Amount', 'SGST', 'CGST', 'IGST', 'UTGST',
        'Remarks')
    profile = UserProfile.objects.get(user=user.id)
    w_address, company_address = get_purchase_company_address(profile)
    data_dictionary = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                       'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total,
                       'po_reference': po_reference, 'user_name': request.user.username, 'total_qty': total_qty,
                       'company_name': profile.company_name, 'location': profile.location, 'w_address': profile.address,
                       'vendor_name': vendor_name, 'vendor_address': vendor_address,
                       'vendor_telephone': vendor_telephone,
                       'gstin_no': gstin_no, 'w_address': w_address, 'wh_gstin': profile.gst_number,
                       'supplier_email': supplier_email, 'company_address': company_address}
    return data_dictionary


@csrf_exempt
@login_required
@get_admin_user
def confirm_back_order(request, user=''):
    from outbound import get_view_order_details
    all_data = {}
    status = ''
    total = 0
    total_qty = 0
    customization = ''
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['wms_code'])):
        rendered1 = ''
        if not (data_dict['quantity'][i] and data_dict['supplier_id'][i]):
            continue
        cond = (data_dict['supplier_id'][i])
        all_data.setdefault(cond, [])
        order_id = ''
        if 'order_id' in request.POST.keys() and data_dict['order_id'][i]:
            order_id = data_dict['order_id'][i]
            custom_order_id = order_id
            order_detail_obj = OrderDetail.objects.filter(id=custom_order_id)
            if order_detail_obj:
                orig_order_id = order_detail_obj[0].original_order_id
                from django.http import QueryDict
                qdict = QueryDict('', mutable=True)
                qdict.update({"order_id": orig_order_id, 'id': custom_order_id})
                request.GET = qdict
                view_order_details = get_view_order_details(request)
                view_order_details = view_order_details.content
                true, false = True, False
                view_order_details = eval(view_order_details)
                temp_data = {}
                all_order_details = view_order_details['data_dict'][0]['ord_data'][0]
                for key, value in all_order_details.iteritems():
                    if key == "cust_id":
                        temp_data["customer_id"] = value
                    elif key in ["sgst_tax", "cgst_tax", "igst_tax"]:
                        temp_data[key.split("_")[0]] = value
                    elif key == "discount_percentage":
                        temp_data["discount_per"] = value
                    elif key == "sku_extra_data":
                        temp_data["customData"] = value
                    else:
                        temp_data[key] = value
                temp_data['image_url'] = request.META['HTTP_ORIGIN'] + '/images/fabricColors/' + temp_data['customData']['colorDataDict'][temp_data['customData']['bodyColor']]
                t = loader.get_template('templates/customOrderDetailsTwo.html')
                rendered1 = t.render(temp_data)
        job_order_id = ''
        if 'job_order_id' in request.POST.keys() and data_dict['job_order_id'][i]:
            job_order_id = data_dict['job_order_id'][i]
        sgst_tax = cgst_tax = igst_tax = utgst_tax = 0
        if 'sgst_tax' in request.POST.keys() and data_dict['sgst_tax'][i]:
            sgst_tax = float(data_dict['sgst_tax'][i])
        if 'cgst_tax' in request.POST.keys() and data_dict['cgst_tax'][i]:
            cgst_tax = float(data_dict['cgst_tax'][i])
        if 'igst_tax' in request.POST.keys() and data_dict['igst_tax'][i]:
            igst_tax = float(data_dict['igst_tax'][i])
        if 'utgst_tax' in request.POST.keys() and data_dict['utgst_tax'][i]:
            utgst_tax = float(data_dict['utgst_tax'][i])
        all_data[cond].append(
            (data_dict['wms_code'][i], data_dict['quantity'][i], data_dict['title'][i], data_dict['price'][i],
             data_dict['remarks'][i], order_id, job_order_id, sgst_tax, cgst_tax, igst_tax, utgst_tax))

    all_invoices = []
    all_invoice_data = []
    for key, value in all_data.iteritems():
        order_id = 1
        purchase_order_id = PurchaseOrder.objects.filter(open_po__sku__user=user.id).order_by('-order_id')
        if purchase_order_id:
            order_id = int(purchase_order_id[0].order_id) + 1

        po_data = []
        for val in value:
            price = 0
            if not float(val[1]):
                continue
            sku_master = SKUMaster.objects.get(wms_code=val[0], user=user.id)
            supplier_master = SupplierMaster.objects.get(id=key, user=user.id)
            prefix = UserProfile.objects.get(user_id=user.id).prefix
            sku_supplier = SKUSupplier.objects.filter(sku__wms_code=val[0], supplier_id=key, sku__user=user.id)
            if val[3]:
                price = float(val[3])
            open_po_dict = copy.deepcopy(PO_SUGGESTIONS_DATA)

            open_po_dict['sku_id'] = sku_master.id
            open_po_dict['supplier_id'] = supplier_master.id
            open_po_dict['order_quantity'] = float(val[1])
            open_po_dict['price'] = price
            open_po_dict['status'] = 0
            open_po_dict['remarks'] = val[4]
            open_po_dict['sgst_tax'] = val[7]
            open_po_dict['cgst_tax'] = val[8]
            open_po_dict['igst_tax'] = val[9]
            open_po_dict['utgst_tax'] = val[10]
            if data_dict.get('vendor_id', '') and data_dict['vendor_id'][0]:
                vendor_master = VendorMaster.objects.filter(vendor_id=data_dict['vendor_id'][0], user=user.id)
                open_po_dict['vendor_id'] = vendor_master[0].id
                open_po_dict['order_type'] = 'VR'
            open_po = OpenPO(**open_po_dict)
            open_po.save()

            purchase_order_dict = copy.deepcopy(PO_DATA)
            purchase_order_dict['order_id'] = order_id
            purchase_order_dict['open_po_id'] = open_po.id
            purchase_order_dict['po_date'] = datetime.datetime.now()
            purchase_order_dict['prefix'] = prefix
            purchase_order = PurchaseOrder(**purchase_order_dict)
            purchase_order.save()

            order_detail_id = ''
            if val[6]:
                create_order_mapping(user, purchase_order.id, val[6], mapping_type='JO-PO')
                order_detail_id = val[6]
                ord_objs = OrderDetail.objects.filter(id=val[6])
                if ord_objs:
                    if ord_objs[0].customer_name:
                        customer_name = ord_objs[0].customer_name
                    elif ord_objs[0].marketplace:
                        customer_name = ord_objs[0].marketplace

            sku_extra_data = ''
            if val[5]:
                create_order_mapping(user, purchase_order.id, val[5], mapping_type='PO')
                order_detail_id = val[5]
                sku_extra_data, product_images, order_ids = get_order_json_data(user, mapping_id=purchase_order.id,
                                                                                mapping_type='PO',
                                                                                sku_id=sku_master.id, order_ids=[])
                if sku_extra_data:
                    customization = 'true'

            customer_name = ''
            executive_name = ''
            if order_detail_id:
                order_detail_id = order_detail_id.split(',')[0]
                ord_objs = OrderDetail.objects.filter(id=order_detail_id)
                if ord_objs:
                    if ord_objs[0].customer_name:
                        customer_name = ord_objs[0].customer_name
                    elif ord_objs[0].marketplace:
                        customer_name = ord_objs[0].marketplace
                customer_order = CustomerOrderSummary.objects.filter(order_id=order_detail_id, order__user=user.id)
                if customer_order:
                    executive_name = customer_order[0].order_taken_by

        data_dictionary = get_grn_json_data(purchase_order, user, request)
        data_dictionary['executive_name'] = executive_name
        data_dictionary['customer_name'] = customer_name
        data_dictionary['customization'] = customization

        t = loader.get_template('templates/toggle/po_download.html')
        rendered = t.render(data_dictionary)
        if get_misc_value('raise_po', user.id) == 'true':
            rendered = [rendered, rendered1] if rendered1 else rendered
            write_and_mail_pdf(data_dictionary['po_reference'], rendered, request, user,
                               data_dictionary['supplier_email'], data_dictionary['telephone'], data_dictionary['data'],
                               str(data_dictionary['order_date']).split(' ')[0])

        if not status:
            status = "Created PO Numbers are " + str(order_id)
        else:
            status += ", " + str(order_id)

        all_invoice_data.append(data_dictionary)
    # t1 = loader.get_template('templates/toggle/po_template_order.html')
    t1 = loader.get_template('templates/print/po_multi_form.html')
    c1 = {'total_data': all_invoice_data}
    rendered1 = t1.render(c1)

    return HttpResponse(rendered1)


@csrf_exempt
@get_admin_user
def generate_rm_rwo_data(request, user=''):
    all_data = []
    title = 'Raise Returnable Order'
    for key, value in request.POST.iteritems():
        key = key.split(':')[0]
        cond = (key, value)
        bom_master = BOMMaster.objects.filter(product_sku__sku_code=key, product_sku__user=user.id)
        if bom_master:
            for bom in bom_master:
                all_data.append(
                    {'product_code': key, 'product_quantity': value, 'material_code': bom.material_sku.sku_code,
                     'material_quantity': float(bom.material_quantity), 'id': ''})
        else:
            all_data.append(
                {'product_code': key, 'product_quantity': value, 'material_code': '', 'material_quantity': '',
                 'id': ''})
    vendors = list(VendorMaster.objects.filter(user=user.id).values('vendor_id', 'name'))
    return HttpResponse(json.dumps({'title': title, 'data': all_data, 'display': 'display-none', 'vendors': vendors}))


@csrf_exempt
@login_required
@get_admin_user
def save_rwo(request, user=''):
    log.info('Request params for save RW Order are ' + str(request.POST.dict()))
    try:
        all_data = {}
        jo_reference = request.POST.get('jo_reference', '')
        vendor_id = request.POST.get('vendor', '')
        if not jo_reference:
            jo_reference = get_jo_reference(user.id)
        data_dict = dict(request.POST.iterlists())
        for i in range(len(data_dict['product_code'])):
            if not data_dict['product_code'][i]:
                continue
            data_id = ''
            if data_dict['id'][i]:
                data_id = data_dict['id'][i]
            cond = (data_dict['product_code'][i])
            all_data.setdefault(cond, [])
            all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i],
                                                                      data_dict['material_quantity'][i], data_id, '',
                                                                      '']})
        status = validate_jo(all_data, user.id, jo_reference='')
        if not status:
            all_data = insert_jo(all_data, user.id, jo_reference, vendor_id)
            status = "Added Successfully"
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Save RW Order failed for %s and params are %s and error statement is %s' % (str(user.username),
                                                                                              str(request.POST.dict()),
                                                                                              str(e)))
        status = 'Save Returnable Work Order Failed'
    return HttpResponse(status)


@csrf_exempt
@login_required
@get_admin_user
def confirm_rwo(request, user=''):
    log.info('Request params for Confirm RW Order are ' + str(request.POST.dict()))
    try:
        all_data = {}
        sku_list = []
        tot_mat_qty = 0
        tot_pro_qty = 0
        jo_reference = request.POST.get('jo_reference', '')
        vendor_id = request.POST.get('vendor', '')
        if not jo_reference:
            jo_reference = get_jo_reference(user.id)
        data_dict = dict(request.POST.iterlists())
        for i in range(len(data_dict['product_code'])):
            p_quantity = data_dict['product_quantity'][i]
            if data_dict['product_code'][i] not in sku_list and p_quantity:
                sku_list.append(data_dict['product_code'][i])
                tot_pro_qty += float(p_quantity)
            if not data_dict['product_code'][i]:
                continue
            data_id = ''
            if data_dict['id'][i]:
                data_id = data_dict['id'][i]
            tot_mat_qty += float(data_dict['material_quantity'][i])
            cond = (data_dict['product_code'][i])
            all_data.setdefault(cond, [])
            all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i],
                                                                      data_dict['material_quantity'][i], data_id, '',
                                                                      data_dict['measurement_type'][i],
                                                                      data_dict['description'][i]]})
        status = validate_jo(all_data, user.id, jo_reference='')
        if not status:
            all_data = insert_jo(all_data, user.id, jo_reference, vendor_id)
            job_code = get_job_code(user.id)
            confirm_job_order(all_data, user.id, jo_reference, job_code)
        if status:
            return HttpResponse(status)
        creation_date = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id)[0].creation_date
        user_profile = UserProfile.objects.get(user_id=user.id)
        user_data = {'company_name': user_profile.company_name, 'username': user.first_name,
                     'location': user_profile.location}
        rw_order = RWOrder.objects.filter(job_order__jo_reference=jo_reference, vendor__user=user.id)

        return render(request, 'templates/toggle/rwo_template.html',
                      {'tot_mat_qty': tot_mat_qty, 'tot_pro_qty': tot_pro_qty,
                       'all_data': all_data, 'creation_date': creation_date,
                       'job_code': job_code, 'user_data': user_data,
                       'headers': RAISE_JO_HEADERS, 'name': rw_order[0].vendor.name,
                       'address': rw_order[0].vendor.address,
                       'telephone': rw_order[0].vendor.phone_number})
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Confirm RW Order failed for %s and params are %s and error statement is %s' % (str(user.username),
                                                                                                 str(
                                                                                                     request.POST.dict()),
                                                                                                 str(e)))
        return HttpResponse("Confirm Returnable Work Order Failed")


def insert_rwo(job_order_id, vendor_id):
    rwo_dict = copy.deepcopy(RWO_FIELDS)
    rwo_dict['job_order_id'] = job_order_id
    rwo_dict['vendor_id'] = vendor_id
    rw_order = RWOrder(**rwo_dict)
    rw_order.save()


@csrf_exempt
def get_saved_rworder(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['job_order__jo_reference', 'vendor__vendor_id', 'vendor__name', 'creation_date']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = RWOrder.objects.filter(job_order__product_code__user=user.id, job_order__status='RWO',
                                             job_order__product_code_id__in=sku_master_ids).order_by(order_data). \
            values_list('job_order__jo_reference', flat=True)
    if search_term:
        master_data = RWOrder.objects.filter(job_order__product_code_id__in=sku_master_ids). \
            filter(Q(job_order__job_code__icontains=search_term) | Q(vendor__vendor_id__icontains=search_term) |
                   Q(vendor__name__icontains=search_term) | Q(creation_date__regex=search_term),
                   job_order__status='RWO', job_order__product_code__user=user.id). \
            values_list('job_order__jo_reference', flat=True).order_by(order_data)
    master_data = [key for key, _ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        data = RWOrder.objects.filter(job_order__jo_reference=data_id, job_order__product_code__user=user.id,
                                      job_order__status='RWO',
                                      job_order__product_code_id__in=sku_master_ids)[0]
        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        temp_data['aaData'].append(
            {'': checkbox, 'RWO Reference': data.job_order.jo_reference, 'Vendor ID': data.vendor.vendor_id,
             'Vendor Name': data.vendor.name, 'Creation Date': str(data.creation_date).split('+')[0],
             'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.job_order.jo_reference}})


@csrf_exempt
@login_required
@get_admin_user
def saved_rwo_data(request, user=''):
    jo_reference = request.GET['data_id']
    all_data = []
    title = "Update Returnable Work Order"
    record = RWOrder.objects.filter(job_order__jo_reference=jo_reference, job_order__product_code__user=user.id,
                                    job_order__status='RWO')
    for rec in record:
        record_data = {}
        record_data['product_code'] = rec.job_order.product_code.sku_code
        record_data['product_description'] = rec.job_order.product_quantity
        record_data['description'] = rec.job_order.product_code.sku_desc
        record_data['sub_data'] = []
        jo_material = JOMaterial.objects.filter(job_order_id=rec.job_order.id, status=1)
        for jo_mat in jo_material:
            dict_data = {'material_code': jo_mat.material_code.sku_code, 'material_quantity': jo_mat.material_quantity,
                         'id': jo_mat.id}
            record_data['sub_data'].append(dict_data)
        all_data.append(record_data)
    return HttpResponse(json.dumps({'data': all_data, 'jo_reference': jo_reference, 'title': title,
                                    'vendor': {'vendor_name': record[0].vendor.name,
                                               'vendor_id': record[0].vendor_id}}))


def validate_jo_vendor_stock(all_data, user, job_code):
    status = ''
    for key, value in all_data.iteritems():
        job_order = JobOrder.objects.filter(job_code=job_code, product_code__wms_code=key, product_code__user=user)
        for val in value:
            for data in val.values():
                stock_quantity = \
                    VendorStock.objects.filter(vendor_id=job_order[0].vendor_id, sku__wms_code=data[0], quantity__gt=0,
                                               sku__user=user).aggregate(Sum('quantity'))['quantity__sum']
                reserved_quantity = VendorPicklist.objects.filter(jo_material__material_code__wms_code=data[0],
                                                                  reserved_quantity__gt=0,
                                                                  jo_material__material_code__user=user,
                                                                  status='open').aggregate(Sum('reserved_quantity'))[
                    'reserved_quantity__sum']

                if not stock_quantity:
                    stock_quantity = 0
                if not reserved_quantity:
                    reserved_quantity = 0
                diff = stock_quantity - reserved_quantity
                if diff < float(data[1]):
                    if not status:
                        status = "Insufficient stock for " + data[0]
                    else:
                        status += ', ' + data[0]

    return status


def consume_vendor_stock(all_data, user, job_code):
    stages = get_user_stages(user, user)
    for key, value in all_data.iteritems():
        job_order = JobOrder.objects.filter(job_code=job_code, product_code__wms_code=key, product_code__user=user.id)
        for val in value:
            for data in val.values():
                jo_material = JOMaterial.objects.get(id=data[2])
                stock_detail = VendorStock.objects.filter(quantity__gt=0, sku_id=jo_material.material_code_id,
                                                          sku__user=user.id,
                                                          vendor_id=jo_material.job_order.vendor_id)
                picking_count = jo_material.material_quantity

                for stock in stock_detail:
                    if picking_count == 0:
                        break
                    if picking_count > stock.quantity:
                        picking_count -= stock.quantity
                        stock.quantity = 0
                    else:
                        stock.quantity -= picking_count
                        picking_count = 0
                    stock.save()
                vendor_picklist_dict = copy.deepcopy(VENDOR_PICKLIST_FIELDS)
                vendor_picklist_dict['jo_material_id'] = jo_material.id
                vendor_picklist_dict['reserved_quantity'] = 0
                vendor_picklist_dict['picked_quantity'] = float(jo_material.material_quantity)
                vendor_picklist_dict['status'] = 'picked'
                vendor_picklist = VendorPicklist(**vendor_picklist_dict)
                vendor_picklist.save()
                jo_material.status = 0
                jo_material.save()
                jo_material.job_order.status = 'pick_confirm'
                jo_material.job_order.save()
        if stages:
            stat_obj = StatusTracking(status_id=jo_material.job_order.id, status_value=stages[0], status_type='JO',
                                      quantity=jo_material.job_order.product_quantity,
                                      original_quantity=jo_material.job_order.product_quantity)
            stat_obj.save()
    return "Confirmed Successfully"


@csrf_exempt
@login_required
@get_admin_user
def generate_vendor_picklist(request, user=''):
    all_data = {}
    job_code = request.POST.get('job_code', '')
    temp = get_misc_value('pallet_switch', user.id)
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['product_code'])):
        if not data_dict['product_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        cond = (data_dict['product_code'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i],
                                                                  data_dict['material_quantity'][i], data_id]})
    status = validate_jo_vendor_stock(all_data, user.id, job_code)
    if status:
        return HttpResponse(status)
    consume_vendor_stock(all_data, user, job_code)
    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def get_vendor_types(request, user=''):
    vendor_names = list(
        JobOrder.objects.filter(product_code__user=user.id, status='order-confirmed', vendor_id__isnull=False). \
            values('vendor__vendor_id', 'vendor__name').distinct())
    return HttpResponse(json.dumps({'data': vendor_names}))


@csrf_exempt
@login_required
@get_admin_user
def update_rm_picklist(request, user=''):
    ''' Update Raw Material Picklist '''
    log.info('Request params for Update Raw Material Picklist are ' + str(request.POST.dict()))
    try:
        stages = get_user_stages(user, user)
        status_ids = StatusTracking.objects.filter(status_value__in=stages, status_type='JO').values_list('status_id',
                                                                                                          flat=True)
        data = {}
        all_data = {}
        auto_skus = []
        update_job_code = ''
        for key, value in request.POST.iterlists():
            name, picklist_id = key.rsplit('_', 1)
            data.setdefault(picklist_id, [])
            for index, val in enumerate(value):
                if len(data[picklist_id]) < index + 1:
                    data[picklist_id].append({})
                data[picklist_id][index][name] = val

        for key, value in data.iteritems():
            if key == 'code':
                continue
            raw_locs = RMLocation.objects.get(id=key)
            picklist = raw_locs.material_picklist
            filter_params = {
                'material_picklist__jo_material__material_code__wms_code': picklist.jo_material.material_code.wms_code,
                'material_picklist__jo_material__job_order__product_code__user': user.id,
                'material_picklist__jo_material__job_order__job_code': picklist.jo_material.job_order.job_code,
                'status': 1}
            if raw_locs.stock:
                filter_params['stock__location__location'] = value[0]['orig_location']
            else:
                filter_params['stock__isnull'] = True
            batch_raw_locs = RMLocation.objects.filter(**filter_params)
            count = 0
            for val in value:
                for raw_loc in batch_raw_locs:
                    picklist = raw_loc.material_picklist
                    if not update_job_code:
                        update_job_code = picklist.jo_material.job_order.job_code
                    if raw_loc.stock:
                        continue
                    jo_material = raw_loc.material_picklist.jo_material
                    data_dict = {'sku_id': jo_material.material_code_id, 'quantity__gt': 0, 'sku__user': user.id}
                    stock_detail = get_picklist_locations(data_dict, user)
                    stock_diff = 0
                    rem_stock_quantity = float(raw_loc.reserved)
                    stock_total = 0
                    stock_detail_dict = []
                    for stock in stock_detail:
                        reserved_quantity = RMLocation.objects.filter(stock_id=stock.id, status=1,
                                                                      material_picklist__jo_material__material_code__user=user.id). \
                            aggregate(Sum('reserved'))['reserved__sum']
                        picklist_reserved = \
                            PicklistLocation.objects.filter(stock_id=stock.id, status=1, picklist__order__user=user.id). \
                                aggregate(Sum('reserved'))['reserved__sum']
                        if not reserved_quantity:
                            reserved_quantity = 0
                        if picklist_reserved:
                            reserved_quantity += picklist_reserved

                        stock_quantity = float(stock.quantity) - reserved_quantity
                        if stock_quantity <= 0:
                            continue
                        stock_total += stock_quantity
                        stock_detail_dict.append({'stock': stock, 'stock_quantity': stock_quantity})
                        if stock_total >= rem_stock_quantity:
                            break

                    for stock_dict in stock_detail_dict:
                        stock = stock_dict['stock']
                        stock_quantity = stock_dict['stock_quantity']
                        if stock_diff:
                            if stock_quantity >= stock_diff:
                                stock_count = stock_diff
                                stock_diff = 0
                            else:
                                stock_count = stock_quantity
                                stock_diff -= stock_quantity
                        elif stock_quantity >= rem_stock_quantity:
                            stock_count = rem_stock_quantity
                        else:
                            stock_count = stock_quantity
                            stock_diff = rem_stock_quantity - stock_quantity

                        rm_locations_dict = copy.deepcopy(MATERIAL_PICK_LOCATIONS)
                        rm_locations_dict['material_picklist_id'] = picklist.id
                        rm_locations_dict['stock_id'] = stock.id
                        rm_locations_dict['quantity'] = stock_count
                        rm_locations_dict['reserved'] = stock_count
                        raw_loc.quantity -= stock_count
                        raw_loc.reserved -= stock_count
                        if raw_loc.reserved <= 0:
                            raw_loc.status = 0
                        rm_locations = RMLocation(**rm_locations_dict)
                        rm_locations.save()
                        raw_loc.save()
                        if not stock_diff:
                            break

        data_id = update_job_code
        headers = list(PRINT_PICKLIST_HEADERS)
        data = get_raw_picklist_data(data_id, user)
        all_stock_locs = map(lambda d: d['location'], data)
        display_update = False
        if 'NO STOCK' in all_stock_locs:
            display_update = True

        show_image = get_misc_value('show_image', user.id)
        if show_image == 'true':
            headers.insert(0, 'Image')
        if get_misc_value('pallet_switch', user.id) == 'true' and 'Pallet Code' not in headers:
            headers.insert(headers.index('Location') + 1, 'Pallet Code')

        return HttpResponse(
            json.dumps({'data': data, 'job_code': data_id, 'show_image': show_image, 'user': request.user.id,
                        'display_update': display_update}))

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Raw Material Picklist failed for %s and params are %s and error statement is %s' % (
            str(user.username),
            str(request.POST.dict()), str(e)))
        return HttpResponse(json.dumps({'message': 'Update Raw Material Picklist Failed', 'data': []}))


def send_job_order_mail(request, user, job_code):
    """ Check and Send Mail of Job Order to Vendor """
    try:
        log.info("Job Order Mail Notification for user %s and Job Order id is %s" % (user.username, str(job_code)))
        mail_data = {}
        user_profile = UserProfile.objects.get(user_id=user.id)
        mail_data['user_data'] = {'company_name': user_profile.company_name, 'username': user.username,
                                  'location': user_profile.location, 'company_address': user_profile.address,
                                  'company_telephone': user_profile.phone_number}
        mail_data['job_code'] = job_code
        job_orders = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id,
                                             vendor_id__isnull=False)
        if not job_orders:
            return "Vendor not found"
        vendor = job_orders[0].vendor
        mail_data['vendor'] = {'name': vendor.name, 'email_id': vendor.email_id, 'phone_number': vendor.phone_number,
                               'address': vendor.address}
        mail_data['creation_date'] = get_local_date(user, job_orders[0].creation_date, send_date=True)
        mail_data['tot_qty'] = 0
        for job_order in job_orders:
            mail_data.setdefault('material_data', [])
            mail_data['material_data'].append(OrderedDict((('SKU Code', job_order.product_code.sku_code),
                                                           ('Description', job_order.product_code.sku_desc),
                                                           ('UOM', job_order.product_code.measurement_type),
                                                           ('Quantity', job_order.product_quantity)
                                                           )))
            mail_data['tot_qty'] += float(job_order.product_quantity)

        template = loader.get_template('templates/toggle/jo_raise_mail.html')
        rendered = template.render(mail_data)

        if get_misc_value('raise_jo', user.id) == 'true':
            write_and_mail_pdf(job_code, rendered, request, user, mail_data['vendor']['email_id'],
                               mail_data['vendor']['phone_number'], mail_data,
                               str(mail_data['creation_date']).split(' ')[0], internal=False,
                               report_type='Job Order')
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Job Order Vendor Mail Notification failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))
        return "Mail Sending Failed"


@csrf_exempt
@login_required
@get_admin_user
def generate_jo_labels(request, user=''):
    data_dict = dict(request.POST.iterlists())
    order_id = request.POST.get('order_id', '')
    pdf_format = request.POST.get('pdf_format', '')
    data = {}
    data['pdf_format'] = [pdf_format]
    if not order_id:
        return HttpResponse(json.dumps({'message': 'Please send Job Order Id', 'data': []}))
    log.info('Request params for Generate JO Labels for ' + user.username + ' is ' + str(data_dict))
    try:
        serial_number = 1
        max_serial = POLabels.objects.filter(sku__user=user.id, custom_label=0).aggregate(Max('serial_number'))['serial_number__max']
        if max_serial:
            serial_number = int(max_serial) + 1
        job_orders = JobOrder.objects.filter(product_code__user=user.id, job_code=order_id)
        creation_date = datetime.datetime.now()
        all_po_labels = POLabels.objects.filter(sku__user=user.id, job_order__job_code=order_id, status=1)
        for ind in range(0, len(data_dict['wms_code'])):
            order = job_orders.filter(product_code__wms_code=data_dict['wms_code'][ind])
            if not order:
                continue
            else:
                order = order[0]
                sku = order.product_code
            needed_quantity = int(data_dict['quantity'][ind])
            po_labels = all_po_labels.filter(job_order_id=order.id).order_by('serial_number')
            data.setdefault('label', [])
            data.setdefault('wms_code', [])
            data.setdefault('quantity', [])
            for labels in po_labels:
                data['label'].append(labels.label)
                data['quantity'].append(1)
                data['wms_code'].append(labels.sku.wms_code)
                needed_quantity -= 1
            for quantity in range(0, needed_quantity):
                imei_numbers = data_dict.get('imei_numbers', '')
                if imei_numbers and imei_numbers[0] != '':
                    imei_numbers = imei_numbers[0].split(',')
                    label = imei_numbers[quantity]
                    data['custome_label'] = 1
                else:
                    label = str(user.username[:2]).upper() + (str(serial_number).zfill(5))
                data['label'].append(label)
                data['quantity'].append(1)
                label_dict = {'job_order_id': order.id, 'serial_number': serial_number, 'label': label,
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
