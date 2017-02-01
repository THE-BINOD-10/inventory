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


@csrf_exempt
def get_open_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['id', 'jo_reference', 'creation_date', 'order_type']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id, status='open', product_code_id__in=sku_master_ids).\
                                      order_by(order_data).values_list('jo_reference', 'order_type').distinct()
    if search_term:
        search_term1 = 'none'
        if (str(search_term).lower() in "self produce"):
            search_term1 = 'SP'
        elif (str(search_term).lower() in "vendor produce"):
            search_term1 = 'VP'
        master_data = JobOrder.objects.filter(product_code_id__in=sku_master_ids).filter(Q(job_code__icontains=search_term) |
                                              Q(order_type__icontains=search_term1) |
                                              Q(creation_date__regex=search_term), status='open', product_code__user=user.id).\
                                       values_list('jo_reference', 'order_type').distinct().order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    index = 1
    status_dict = {'SP': 'Self Produce', 'VP': 'Vendor Produce'}
    for data_id in master_data[start_index:stop_index]:
        data = JobOrder.objects.filter(jo_reference=data_id[0], product_code__user=user.id, status='open', order_type=data_id[1])[0]
        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id[0]
        temp_data['aaData'].append({'': checkbox, 'JO Reference': data.jo_reference,
                                    'Creation Date': get_local_date(request.user, data.creation_date),
                                    'Order Type': status_dict[data_id[1]], 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'data-id': data.jo_reference}, 'id': index})
        index = index + 1

@csrf_exempt
def get_generated_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['material_picklist__jo_material__job_order__job_code', 'material_picklist__creation_date', 'material_picklist__jo_material__job_order__order_type']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = RMLocation.objects.filter(material_picklist__jo_material__material_code_id__in=sku_master_ids).\
                                         filter(material_picklist__jo_material__material_code__user=user.id, material_picklist__status='open',
                                                status=1).order_by(order_data).\
                                         values_list('material_picklist__jo_material__job_order__job_code', flat=True)
    if search_term:
        master_data = RMLocation.objects.filter(material_picklist__jo_material__material_code_id__in=sku_master_ids).\
                                         filter(Q(material_picklist__jo_material__job_order__job_code__icontains=search_term,
                                                material_picklist__status='open'),
                                                material_picklist__jo_material__material_code__user=user.id, status=1).\
                                         values_list('material_picklist__jo_material__job_order__job_code', flat=True).order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        data = MaterialPicklist.objects.filter(jo_material__material_code_id__in=sku_master_ids).\
                                        filter(jo_material__job_order__job_code=data_id, jo_material__material_code__user=user.id,
                                               status='open')[0]
        order_type = 'Job Order'
        rw_purchase = RWOrder.objects.filter(job_order_id=data.jo_material.job_order.id)
        if rw_purchase:
            order_type = 'Returnable Work Order'

        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        temp_data['aaData'].append({'': checkbox, 'Job Code': data.jo_material.job_order.job_code,
                                    'Creation Date': get_local_date(request.user, data.creation_date), 'Order Type': order_type,
                                    'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.jo_material.job_order.job_code}})

def get_user_stages(user, sub_user):
    stages = list(ProductionStages.objects.filter(user=user.id).values_list('stage_name',flat=True))
    
    if not sub_user.is_staff:
        group_ids = list(sub_user.groups.all().exclude(name=user.username).values_list('id', flat=True))
        stages = list(GroupStages.objects.filter(group_id__in=group_ids).values_list('stages_list__stage_name',flat=True))
        #stages_objs = GroupStages.objects.all()
        #for obj in stages_objs:
        #    name = sub_user.groups.filter(name=obj.group.name)
        #    if name:
        #        group_obj = name[0]	
        #stages = GroupStages.objects.get(group=group_obj).stages_list.values_list('stage_name',flat=True)

    return stages


@csrf_exempt
def get_confirmed_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    parent_stages = get_user_stages(user, user)
    lis = ['job_code', 'creation_date', 'received_quantity']
    filter_params = {'product_code_id__in': sku_master_ids, 'product_code__user': user.id,
                     'status__in': ['grn-generated', 'pick_confirm', 'partial_pick'], 'product_quantity__gt': F('received_quantity')}
    if not request.user.is_staff and parent_stages:
        stages = get_user_stages(user, request.user)
        status_ids = StatusTracking.objects.filter(status_value__in=stages,status_type='JO', quantity__gt=0).values_list('status_id',flat=True)
        filter_params['id__in'] = status_ids

    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(**filter_params).order_by(order_data).\
                                       values_list('job_code', flat=True)
    if search_term:
        master_data = JobOrder.objects.filter(Q(job_code__icontains=search_term), **filter_params).values_list('job_code', flat=True).\
                                       order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        receive_status = 'Yet to Receive'
        data = JobOrder.objects.filter(job_code=data_id, product_code__user=user.id, status__in=['grn-generated', 'pick_confirm', 'partial_pick'])
        for dat in data:
            if dat.received_quantity:
                receive_status = 'Partially Received'
                break
        data = data[0]
        temp_data['aaData'].append({'Job Code': data.job_code, 'Creation Date': get_local_date(request.user, data.creation_date),
                                    'Receive Status': receive_status, 'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.job_code}})

@csrf_exempt
def get_confirmed_jo_all(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    parent_stages = get_user_stages(user, user)
    lis = ['job_code', 'product_code__sku_code', 'product_code__sku_brand', 'product_code__sku_category', 'creation_date', 'received_quantity']
    filter_params = {'product_code_id__in': sku_master_ids, 'product_code__user': user.id,
                     'status__in': ['grn-generated', 'pick_confirm', 'partial_pick'], 'product_quantity__gt': F('received_quantity')}
    if not request.user.is_staff and parent_stages:
        stages = get_user_stages(user, request.user)
        status_ids = StatusTracking.objects.filter(status_value__in=stages,status_type='JO', quantity__gt=0).values_list('status_id',flat=True)
        filter_params['id__in'] = status_ids

    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(**filter_params).order_by(order_data).\
                                       values('job_code', 'product_code__sku_code', 'product_code__sku_category', 'product_code__sku_brand')
    if search_term:
        master_data = JobOrder.objects.filter(Q(job_code__icontains=search_term), **filter_params).values('job_code', 'product_code__sku_code',\
		 			'product_code__sku_category').order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        receive_status = 'Yet to Receive'
        data = JobOrder.objects.filter(job_code=data_id['job_code'], product_code__sku_code=data_id['product_code__sku_code'], product_code__user=user.id, status__in=['grn-generated', 'pick_confirm', 'partial_pick'])
        for dat in data:
            if dat.received_quantity:
                receive_status = 'Partially Received'
                break
        data = data[0]
        temp_data['aaData'].append({'Job Code': data.job_code, 'Creation Date': get_local_date(request.user, data.creation_date),
				    'SKU Code': data_id['product_code__sku_code'], 'SKU Category': data_id['product_code__sku_category'],
				    'SKU Brand': data_id['product_code__sku_brand'], 'Receive Status': receive_status, 'DT_RowClass': 'results', 
				    'DT_RowAttr': {'data-id': data.id}})


@csrf_exempt
def get_jo_confirmed(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['job_code', 'creation_date', 'order_type']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id, status='order-confirmed', product_code_id__in=sku_master_ids).\
                                               order_by(order_data).values_list('job_code', flat=True)
    if search_term:
        master_data = JobOrder.objects.filter(product_code_id__in=sku_master_ids).filter(Q(job_code__icontains=search_term,
                                              status='order-confirmed'), product_code__user=user.id).values_list('job_code', flat=True).\
                                       order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        data = JobOrder.objects.filter(job_code=data_id, product_code__user=user.id, status='order-confirmed')[0]
        order_type = 'Job Order'
        rw_purchase = RWOrder.objects.filter(job_order_id=data.id)
        if rw_purchase:
            order_type = 'Returnable Work Order'
        if data.order_type == 'VP':
            order_type = 'Vendor Produce'

        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        temp_data['aaData'].append({'': checkbox, 'Job Code': data.job_code,
                                    'Creation Date': get_local_date(request.user, data.creation_date), 'Order Type': order_type, 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'data-id': data.job_code}})


@csrf_exempt
def get_received_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['job_code', 'creation_date']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id, status__in=['location-assigned', 'grn-generated'],
                                              product_code_id__in=sku_master_ids).order_by(order_data).values_list('job_code', flat=True)
    if search_term:
        master_data = JobOrder.objects.filter(Q(job_code__icontains=search_term),status__in=['location-assigned', 'grn-generated'],
                                              product_code__user=user.id, product_code_id__in=sku_master_ids).\
                                       values_list('job_code', flat=True).order_by(order_data)

    master_data = [ key for key,_ in groupby(master_data)]
    for data_id in master_data:
        po_location = POLocation.objects.filter(job_order__job_code=data_id, status=1, job_order__product_code__user=user.id)
        if po_location:
            data = JobOrder.objects.filter(job_code=data_id, product_code__user=user.id, status__in=['location-assigned', 'grn-generated'])
            data = data[0]
            temp_data['aaData'].append({'Job Code': data.job_code, 'Creation Date': get_local_date(request.user, data.creation_date),
                                        'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.job_code}})
    temp_data['recordsTotal'] = len(temp_data['aaData'])
    temp_data['recordsFiltered'] = len(temp_data['aaData'])
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]

@csrf_exempt
def get_rm_picklist_confirmed_sku(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    lis = ['job_code', 'product_code__sku_code', 'product_code__sku_brand', 'product_code__sku_category','creation_date', 'order_type']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id, status='order-confirmed', product_code_id__in=sku_master_ids).\
                                               order_by(order_data).values_list('job_code', flat=True)
    if search_term:
        master_data = JobOrder.objects.filter(product_code_id__in=sku_master_ids).filter(Q(job_code__icontains=search_term,
                                              status='order-confirmed'), product_code__user=user.id).values_list('job_code', flat=True).\
                                       order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        data = JobOrder.objects.filter(job_code=data_id, product_code__user=user.id, status='order-confirmed')[0]
        order_type = 'Job Order'
        rw_purchase = RWOrder.objects.filter(job_order_id=data.id)
        if rw_purchase:
            order_type = 'Returnable Work Order'
        if data.order_type == 'VP':
            order_type = 'Vendor Produce'

        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        temp_data['aaData'].append({'': checkbox, 'Job Code': data.job_code, 'SKU Code': data.product_code.sku_code,
                                    'SKU Brand': data.product_code.sku_brand, 'SKU Category': data.product_code.sku_category,
                                    'Creation Date': get_local_date(request.user, data.creation_date), 'Order Type': order_type, 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'data-id': data.job_code}})

@login_required
@get_admin_user
def generated_jo_data(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    jo_reference = request.GET['data_id']
    all_data = {'results': []}
    title = "Update Job Order"
    status_dict = {'SP': 'Self Produce', 'VP': 'Vendor Produce'}
    record = JobOrder.objects.filter(jo_reference=jo_reference, product_code__user=user.id, status='open', product_code_id__in=sku_master_ids)
    for rec in record:
        record_data = {}
        jo_material = JOMaterial.objects.filter(job_order_id= rec.id,status=1)
        record_data['product_code'] = rec.product_code.sku_code
        record_data['product_description'] = rec.product_quantity
        record_data['data'] = []
        for jo_mat in jo_material:
            dict_data = {'material_code': jo_mat.material_code.sku_code, 'material_quantity': jo_mat.material_quantity, 'id': jo_mat.id}
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
    all_data = {}
    jo_reference = request.POST.get('jo_reference','')
    vendor_id = request.POST.get('vendor_id','')
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
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i], data_dict['material_quantity'][i],
                               data_id, '' ]})
    status = validate_jo(all_data, user.id, jo_reference='', vendor_id=vendor_id)
    if not status:
        all_data = insert_jo(all_data, user.id, jo_reference, vendor_id=vendor_id, order_type=order_type)
        status = "Added Successfully"
    return HttpResponse(status)


def get_jo_reference(user):
    jo_code = JobOrder.objects.filter(product_code__user=user).order_by('-jo_reference')
    if jo_code:
        jo_reference = int(jo_code[0].jo_reference) + 1
    else:
        jo_reference = 1
    return jo_reference

def validate_jo(all_data, user, jo_reference, vendor_id=''):
    sku_status = ''
    other_status = ''
    if vendor_id:
        vendor_master = VendorMaster.objects.filter(vendor_id=vendor_id, user=user)
        if not vendor_id:
            other_status = "Invalid Vendor ID " + vendor_id
    for key,value in all_data.iteritems():
        if not value:
            continue
        product_sku = SKUMaster.objects.filter(wms_code = key, sku_type__in=['FG', 'RM', 'CS'],user=user)
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
                material_sku = SKUMaster.objects.filter(wms_code = data[0], sku_type__in=['RM', 'CS'],user=user)
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
    order_mapping = OrderMapping.objects.filter(mapping_id=mapping_id, mapping_type=mapping_type, order_id=order_id)
    if not order_mapping:
        OrderMapping.objects.create(mapping_id=mapping_id, mapping_type=mapping_type, order_id=order_id, creation_date=datetime.datetime.now())

def insert_jo(all_data, user, jo_reference, vendor_id='', order_type=''):
    for key,value in all_data.iteritems():
        job_order_dict = copy.deepcopy(JO_PRODUCT_FIELDS)
        if not value:
            continue
        product_sku = SKUMaster.objects.get(wms_code = key, user=user)
        job_instance = JobOrder.objects.filter(jo_reference=jo_reference, product_code__sku_code=key, product_code__user=user)
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
        for idx,val in enumerate(value):
            for k,data in val.iteritems():
                if data[2]:
                    sku = SKUMaster.objects.get(sku_code=data[0], user=user)
                    jo_material = JOMaterial.objects.get(id=data[2])
                    jo_material.material_quantity = float(data[1])
                    jo_material.material_code_id = sku.id
                    jo_material.save()
                    continue
                jo_material_dict = copy.deepcopy(JO_MATERIAL_FIELDS)
                material_sku = SKUMaster.objects.get(wms_code = data[0], user=user)
                jo_material_dict['material_code_id'] = material_sku.id
                jo_material_dict['job_order_id'] = job_order.id
                jo_material_dict['material_quantity'] = float(data[1])
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
    data_id = request.POST.get('rem_id', '')
    jo_reference = request.POST.get('jo_reference', '')
    wms_code = request.POST.get('wms_code', '')
    if jo_reference and wms_code:
        job_order = JobOrder.objects.filter(jo_reference=jo_reference, product_code__wms_code=wms_code, product_code__user=user.id)
        delete_jo_list(job_order)
    else:
        JOMaterial.objects.filter(id=data_id).delete()
    return HttpResponse("Deleted Successfully")

@csrf_exempt
@login_required
@get_admin_user
def confirm_jo(request, user=''):
    all_data = {}
    sku_list = []
    tot_mat_qty = 0
    tot_pro_qty = 0
    jo_reference = request.POST.get('jo_reference','')
    if not jo_reference:
        jo_reference = get_jo_reference(user.id)
    vendor_id = request.POST.get('vendor_id','')
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
        tot_mat_qty += float(data_dict['material_quantity'][i])
        cond = (data_dict['product_code'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i], data_dict['material_quantity'][i], data_id,
                               order_id ]})

    status = validate_jo(all_data, user.id, jo_reference=jo_reference)
    if not status:
        all_data = insert_jo(all_data, user.id, jo_reference=jo_reference, vendor_id=vendor_id, order_type=order_type)
        job_code = get_job_code(user.id)
        confirm_job_order(all_data, user.id, jo_reference, job_code)
        #save_jo_locations(all_data, user, job_code)
    if status:
        return HttpResponse(status)
    creation_date = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id)[0].creation_date
    creation_date = get_local_date(user, creation_date)
    user_profile = UserProfile.objects.get(user_id=user.id)
    user_data = {'company_name': user_profile.company_name, 'username': user.first_name, 'location': user_profile.location}

    return render(request, 'templates/toggle/jo_template.html', {'tot_mat_qty': tot_mat_qty, 'tot_pro_qty': tot_pro_qty, 'all_data': all_data,
                                                                 'creation_date': creation_date, 'job_code': job_code, 'user_data': user_data,
                                                                 'headers': RAISE_JO_HEADERS})    

def get_job_code(user):
    jo_code = JobOrder.objects.filter(product_code__user=user).order_by('-job_code')
    if jo_code:
        job_code = int(jo_code[0].job_code) + 1
    else:
        job_code = 1
    return job_code

def confirm_job_order(all_data, user, jo_reference, job_code):
    for key,value in all_data.iteritems():
        job_order = JobOrder.objects.filter(jo_reference=jo_reference, product_code__wms_code=key, product_code__user=user)
        for order in job_order:
            order.job_code = job_code
            order.status = 'order-confirmed'
            order.save()

@csrf_exempt
@login_required
@get_admin_user
def get_material_codes(request, user=''):
    sku_code = request.POST.get('sku_code','')
    all_data = [];
    bom_master = BOMMaster.objects.filter(product_sku__sku_code=sku_code, product_sku__user=user.id)
    if not bom_master:
        return HttpResponse("No Data Found")
    for bom in bom_master:
        cond = (bom.material_sku.sku_code)
        material_quantity = bom.material_quantity
        if bom.wastage_percent:
            material_quantity = float(bom.material_quantity) + ((float(bom.material_quantity)/100) * float(bom.wastage_percent))
        all_data.append({'material_quantity': material_quantity, 'material_code': cond})
    return HttpResponse(json.dumps(all_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def view_confirmed_jo(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    job_code = request.POST['data_id']
    all_data = {'results': []}
    order_ids = []
    status_dict = {'SP': 'Self Produce', 'VP': 'Vendor Produce'}
    record = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id, status='order-confirmed', product_code_id__in=sku_master_ids)
    for rec in record:
        record_data = {}
        jo_material = JOMaterial.objects.filter(job_order_id= rec.id,status=1)
        record_data['product_code'] = rec.product_code.sku_code
        record_data['product_description'] = rec.product_quantity

        record_data['sku_extra_data'], record_data['product_images'], order_ids = get_order_json_data(user, mapping_id=rec.id,
                                                                           mapping_type='JO', sku_id=rec.product_code_id, order_ids=order_ids)

        record_data['data'] = []
        for jo_mat in jo_material:
            dict_data = {'material_code': jo_mat.material_code.sku_code, 'material_quantity': jo_mat.material_quantity, 'id': jo_mat.id}
            record_data['data'].append(dict_data)
        all_data['results'].append(record_data)
    all_data['jo_reference'] = job_code
    all_data['order_type'] = status_dict[record[0].order_type]
    vendor_id = ''
    if record[0].vendor:
        vendor_id = record[0].vendor.vendor_id
    all_data['vendor_id'] = vendor_id
    all_data['order_ids'] = order_ids
    return HttpResponse(json.dumps(all_data))

@csrf_exempt
@login_required
@get_admin_user
def jo_generate_picklist(request, user=''):
    all_data = {}
    job_code = request.POST.get('job_code','')
    headers = list(PICKLIST_HEADER1)
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
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i], data_dict['material_quantity'][i], data_id ]})

    if get_misc_value('no_stock_switch', user.id) == 'false':
        status = validate_jo_stock(all_data, user.id, job_code)
        if status:
            return HttpResponse(status)
    save_jo_locations(all_data, user, job_code)
    #data = get_raw_picklist_data(job_code, user)
    #show_image = get_misc_value('show_image', user.id)
    #if show_image == 'true':
    #    headers.insert(0, 'Image')
    #if get_misc_value('pallet_switch', user.id) == 'true' and 'Pallet Code' not in headers:
    #    headers.insert(headers.index('Location') + 1, 'Pallet Code')

    #return render(request, 'templates/toggle/view_raw_picklist.html', {'data': data, 'headers': headers, 'job_code': job_code, 'show_image': show_image, 'user': user})
    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def view_rm_picklist(request, user=''):
    data_id = request.POST['data_id']
    headers = list(PICKLIST_HEADER1)
    data = get_raw_picklist_data(data_id, user)
    show_image = get_misc_value('show_image', user.id)
    if show_image == 'true':
        headers.insert(0, 'Image')
    if get_misc_value('pallet_switch', user.id) == 'true' and 'Pallet Code' not in headers:
        headers.insert(headers.index('Location') + 1, 'Pallet Code')

    return HttpResponse(json.dumps({'data': data, 'job_code': data_id, 'show_image': show_image, 'user': request.user.id}))

def get_raw_picklist_data(data_id, user):
    data = []
    batch_data = {}
    material_picklist = MaterialPicklist.objects.filter(jo_material__job_order__job_code=data_id,
                                                        jo_material__job_order__product_code__user=user.id, status='open')
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
                batch_data[match_condition] = {'wms_code': location.material_picklist.jo_material.material_code.sku_code,
                                               'zone': zone, 'sequence': sequence, 'location': location_name,
                                               'reserved_quantity': location.reserved, 'job_code': picklist.jo_material.job_order.job_code,
                                               'stock_id': stock_id, 'picked_quantity': location.reserved,
                                               'pallet_code': pallet_code, 'id': location.id,
                                               'title': location.material_picklist.jo_material.material_code.sku_desc,
                                               'image': picklist.jo_material.material_code.image_url}
            else:
                batch_data[match_condition]['reserved_quantity'] += float(location.reserved)
                batch_data[match_condition]['picked_quantity'] += float(location.reserved)

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
        po_dict = {'order_id': po_id, 'received_quantity': 0, 'saved_quantity': 0, 'po_date': datetime.datetime.now(), 'ship_to': '',
                   'status': '', 'prefix': prefix, 'creation_date': datetime.datetime.now()}
        po_order = PurchaseOrder(**po_dict)
        po_order.save()
        rw_purchase_dict = copy.deepcopy(RWO_PURCHASE_FIELDS)
        rw_purchase_dict['purchase_order_id'] = po_order.id
        rw_purchase_dict['rwo_id'] = rw_order.id
        rw_purchase = RWPurchase(**rw_purchase_dict)
        rw_purchase.save()
        po_data.append(( order.product_code.wms_code, '', order.product_code.sku_desc, order.product_quantity, 0, 0))

    order_date = get_local_date(user, po_order.creation_date)
    table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Unit Price', 'Amount')

    profile = UserProfile.objects.get(user=user.id)
    phone_no = str(rw_order.vendor.phone_number)
    po_reference = '%s%s_%s' % (prefix, str(po_order.creation_date).split(' ')[0].replace('-', ''), po_order.order_id)
    data_dict = {'table_headers': table_headers, 'data': po_data, 'address': rw_order.vendor.address, 'order_id': po_order.order_id,
                 'telephone': phone_no, 'name': rw_order.vendor.name, 'order_date': order_date,
                 'total': total, 'user_name': user.username, 'total_qty': total_qty,
                 'location': profile.location, 'w_address': profile.address, 'company_name': profile.company_name}

    t = loader.get_template('templates/toggle/po_download.html')
    c = Context(data_dict)
    rendered = t.render(c)
    send_message = 'false'
    data = MiscDetail.objects.filter(user=user.id, misc_type='send_message')
    if data:
        send_message = data[0].misc_value
    if send_message == 'true':
        write_and_mail_pdf(po_reference, rendered, request, rw_order.vendor.email_id, phone_no, po_data, str(order_date).split(' ')[0])

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
            stat_obj = StatusTracking(status_id=picklist.jo_material.job_order.id, status_value=stages[0], status_type='JO')
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
                                                material_picklist__jo_material__material_code__user=user.id,status=1)
        if not raw_loc_obj:
            raw_loc.material_picklist.jo_material.status = 2
            raw_loc.material_picklist.jo_material.save()
            if picklist.reserved_quantity < 0:
                picklist.reserved_quantity = 0
            if picklist.reserved_quantity == 0:
                picklist.status = 'picked'
            picklist.save()
            material = MaterialPicklist.objects.filter(jo_material__job_order_id=picklist.jo_material.job_order_id, status='open',
                                                       jo_material__material_code__user=user.id)
            if not material:
                if not picklist.jo_material.job_order.status in ['grn-generated', 'location-assigned', 'confirmed-putaway']:
                    picklist.jo_material.job_order.status = 'pick_confirm'
                picklist.jo_material.job_order.save()
                rw_order = RWOrder.objects.filter(job_order_id=picklist.jo_material.job_order_id, vendor__user=user.id)
                if rw_order:
                    rw_order = rw_order[0]
                    picklist.jo_material.job_order.status = 'confirmed-putaway'
                    picklist.jo_material.job_order.save()
    picklist.save()
    return count

@csrf_exempt
@login_required
@get_admin_user
def rm_picklist_confirmation(request, user=''):
    stages = get_user_stages(user, user)
    status_ids = StatusTracking.objects.filter(status_value__in=stages,status_type='JO').values_list('status_id',flat=True)
    data = {}
    all_data = {}
    auto_skus = []
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

    for key, value in data.iteritems():
        raw_locs = RMLocation.objects.get(id=key)
        picklist = raw_locs.material_picklist
        filter_params = {'material_picklist__jo_material__material_code__wms_code': picklist.jo_material.material_code.wms_code,
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
            for raw_loc in batch_raw_locs:
                if count == 0:
                    continue
                picklist = raw_loc.material_picklist

                sku = picklist.jo_material.material_code
                if float(picklist.reserved_quantity) > float(val['picked_quantity']):
                    picking_count = float(val['picked_quantity'])
                else:
                    picking_count = float(picklist.reserved_quantity)
                picking_count1 = picking_count
                if not raw_loc.stock:
                    count = confirm_rm_no_stock(picklist, picking_count, count, raw_loc, request, user)
                    continue
                location = LocationMaster.objects.filter(location=val['location'], zone__zone=val['zone'], zone__user=user.id)
                if not location:
                    return HttpResponse("Invalid Location and Zone combination")
                stock_dict = {'sku_id': sku.id, 'location_id': location[0].id, 'sku__user': user.id}
                stock_detail = StockDetail.objects.filter(**stock_dict)
                for stock in stock_detail:
                    if picking_count == 0:
                        break
                    if picking_count > stock.quantity:
                        picking_count -= stock.quantity
                        picklist.reserved_quantity -= stock.quantity
                        stock.quantity = 0
                    else:
                        stock.quantity -= picking_count
                        picklist.reserved_quantity -= picking_count
                        picking_count = 0

                        if float(stock.location.filled_capacity) - picking_count1 >= 0:
                            setattr(stock.location, 'filled_capacity', float(stock.location.filled_capacity) - picking_count1)
                            stock.location.save()

                        pick_loc = RMLocation.objects.filter(material_picklist_id=picklist.id, stock__location_id=stock.location_id,
                                                             material_picklist__jo_material__material_code__user=user.id, status=1)
                        update_picked = picking_count1
                        if pick_loc:
                            update_picklist_locations(pick_loc, picklist, update_picked)
                        else:
                            data = RMLocation(material_picklist_id=picklist.id, stock=stock, quantity=picking_count1, reserved=0,
                                              status = 0, creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now())
                            data.save()
                            exist_pics = RMLocation.objects.exclude(id=data.id).filter(material_picklist_id=picklist.id, status=1, reserved__gt=0)
                            update_picklist_locations(exist_pics, picklist, update_picked, 'true')

                    

                        picklist.picked_quantity = float(picklist.picked_quantity) + picking_count1

                    raw_loc = RMLocation.objects.get(id=raw_loc.id)

                    stock.save()
                    if stock.location.zone.zone == 'BAY_AREA':
                        reduce_putaway_stock(stock, picking_count1, user.id)
                    if raw_loc.reserved == 0:
                        raw_loc.status = 0
                        raw_loc_obj = RMLocation.objects.filter(material_picklist__jo_material_id=picklist.jo_material_id,
                                                                material_picklist__jo_material__material_code__user=user.id,status=1)
                        if not raw_loc_obj:
                            raw_loc.material_picklist.jo_material.status = 2
                            raw_loc.material_picklist.jo_material.save()
                    auto_skus.append(sku.sku_code)
                if picklist.reserved_quantity < 0:
                    picklist.reserved_quantity = 0
                if picklist.reserved_quantity == 0:
                    picklist.status = 'picked'
                if picklist.picked_quantity > 0 and picklist.jo_material.job_order.status in ['order-confirmed', 'picklist_gen']:
                    if stages:
                        stat_obj = StatusTracking(status_id=picklist.jo_material.job_order.id, status_value=stages[0], status_type='JO')
                        stat_obj.save()
                    picklist.jo_material.job_order.status = 'partial_pick'
                    picklist.jo_material.job_order.save()
                picklist.save()

                material = MaterialPicklist.objects.filter(jo_material__job_order_id=picklist.jo_material.job_order_id, status='open',
                                                           jo_material__material_code__user=user.id)
                if not material:
                    if not picklist.jo_material.job_order.status in ['grn-generated', 'location-assigned', 'confirmed-putaway']:
                        picklist.jo_material.job_order.status = 'pick_confirm'
                    picklist.jo_material.job_order.save()
                    rw_order = RWOrder.objects.filter(job_order_id=picklist.jo_material.job_order_id, vendor__user=user.id)
                    if rw_order:
                        rw_order = rw_order[0]
                        picklist.jo_material.job_order.status = 'confirmed-putaway'
                        picklist.jo_material.job_order.save()
                        insert_rwo_po(rw_order, request, user)

            if get_misc_value('auto_po_switch', user.id) == 'true' and auto_skus:
                auto_po(list(set(auto_skus)) ,user.id)

    return HttpResponse('Picklist Confirmed')

def validate_jo_stock(all_data, user, job_code):
    status = ''
    for key,value in all_data.iteritems():
        for val in value:
            for data in val.values():
                stock_quantity = StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE').filter(sku__wms_code=data[0],
                                                             quantity__gt=0, sku__user=user).aggregate(Sum('quantity'))['quantity__sum']
                reserved_quantity = PicklistLocation.objects.filter(stock__sku__wms_code=data[0], status=1,
                                                                        picklist__order__user=user).aggregate(Sum('reserved'))['reserved__sum']

                raw_reserved = RMLocation.objects.filter(status=1, material_picklist__jo_material__material_code__user=user,
                                                         stock__sku__wms_code=data[0]).aggregate(Sum('reserved'))['reserved__sum']
                if not stock_quantity:
                    stock_quantity = 0
                if not reserved_quantity:
                    reserved_quantity = 0
                if raw_reserved:
                    reserved_quantity += float(raw_reserved)
                diff = stock_quantity - reserved_quantity
                if diff < float(data[1]):
                    if not status:
                        status = "Insufficient stock for " + data[0]
                    else:
                        status += ', ' + data[0]

    return status

def save_jo_locations(all_data, user, job_code):
    for key,value in all_data.iteritems():
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
                                                                  material_picklist__jo_material__material_code__user=user.id).\
                                                           aggregate(Sum('reserved'))['reserved__sum']
                    picklist_reserved = PicklistLocation.objects.filter(stock_id=stock.id, status=1, picklist__order__user=user.id).\
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

                material_picklist_dict = copy.deepcopy(MATERIAL_PICKLIST_FIELDS)
                material_picklist_dict['jo_material_id'] = jo_material.id
                material_picklist_dict['reserved_quantity'] = float(jo_material.material_quantity)
                material_picklist = MaterialPicklist(**material_picklist_dict)
                material_picklist.save()

                if stock_total < rem_stock_quantity:
                    no_stock_quantity = rem_stock_quantity - stock_total
                    rem_stock_quantity -= no_stock_quantity
                    RMLocation.objects.create(material_picklist_id=material_picklist.id, stock=None, quantity=no_stock_quantity,
                                              reserved=no_stock_quantity, creation_date=datetime.datetime.now(), status=1)

                
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
                    rm_locations_dict['material_picklist_id'] = material_picklist.id
                    rm_locations_dict['stock_id'] = stock.id
                    rm_locations_dict['quantity'] = stock_count
                    rm_locations_dict['reserved'] = stock_count
                    rm_locations = RMLocation(**rm_locations_dict)
                    rm_locations.save()
                    if not stock_diff:
                        break
                jo_material.status = 0
                jo_material.save()
                for order in job_order:
                    order.status = 'picklist_gen'
                    order.save()
    return "Confirmed Successfully"


def get_picklist_locations(data_dict, user):
    exclude_dict = {'location__lock_status__in': ['Outbound', 'Inbound and Outbound'], 'location__zone__zone': 'TEMP_ZONE'}
    back_order = get_misc_value('back_order', user.id)
    fifo_switch = get_misc_value('fifo_switch', user.id)

    if fifo_switch == 'true':
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0, **data_dict).\
                                                                    order_by('receipt_date', 'location__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0, **data_dict).\
                                                                    order_by('receipt_date', 'location__pick_sequence')
        data_dict['location__zone__zone'] = 'TEMP_ZONE'
        del exclude_dict['location__zone__zone']
        stock_detail3 = StockDetail.objects.exclude(**exclude_dict).filter(**data_dict).order_by('receipt_date', 'location__pick_sequence')
        stock_detail = list(chain(stock_detail1, stock_detail2, stock_detail3))
    else:
        del exclude_dict['location__zone__zone']
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0, **data_dict).\
                                                                    order_by('location_id__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0, **data_dict).order_by('receipt_date')
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
        raw_loc = RMLocation.objects.get(id=key)
        sku = raw_loc.material_picklist.jo_material.material_code
        for val in value:
            location = val['location']
            zone = val['zone']
            if location == 'NO STOCK':
                continue
            loc_obj = LocationMaster.objects.filter(location=location, zone__zone=zone, zone__user=user)
            if not loc_obj:
                if not loc_status:
                    loc_status = 'Invalid Location and Zone combination (%s,%s)' % (zone, location)
                else:
                    loc_status += ', (%s,%s)' % (zone, location)
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
    creation_date = ''
    headers = copy.deepcopy(RECEIVE_JO_TABLE_HEADERS)
    stages = list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    temp = get_misc_value('pallet_switch', user.id)
    
    filter_params = {'product_code__user': user.id, 'product_code_id__in': sku_master_ids, 'status__in': ['grn-generated', 'pick_confirm',
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
        pallet_mapping = PalletMapping.objects.filter(pallet_detail__user=user.id,po_location__job_order__job_code=rec.job_code,
                                                      po_location__job_order__product_code__wms_code=rec.product_code.wms_code, status=2)
        pallet_ids = list(pallet_mapping.values_list('id', flat=True))
        status_track = StatusTracking.objects.order_by('creation_date').filter(Q(status_id=rec.id, status_type='JO') |
                                                       Q(status_id__in=pallet_ids, status_type='JO-PALLET'), quantity__gt=0)

        sku_extra_data, product_images, order_ids = get_order_json_data(user, mapping_id=rec.id, mapping_type='JO', sku_id=rec.product_code_id,
                                                                        order_ids=order_ids)

        sku_cat = rec.product_code.sku_category
        stages_list = copy.deepcopy(stages)

        if rec.product_code.sku_brand and rec.product_code.sku_brand not in sku_brands:
            sku_brands.append(rec.product_code.sku_brand)

        if rec.product_code.sku_category and rec.product_code.sku_category not in sku_categories:
            sku_categories.append(rec.product_code.sku_category)

        if rec.product_code.sku_class and rec.product_code.sku_class not in sku_classes:
            sku_classes.append(rec.product_code.sku_class)

        for tracking in status_track:
            rem_stages = stages_list
            if tracking.status_value in stages_list:
                rem_stages = stages_list[stages_list.index(tracking.status_value):]
            cond = (rec.id)
            jo_quantity = tracking.quantity
            stage_quantity += float(tracking.quantity)

            if tracking.status_type == 'JO-PALLET':
                pallet = pallet_mapping.get(id=tracking.status_id)
                all_data.append({'id': rec.id, 'wms_code': rec.product_code.wms_code,
                                 'product_quantity': jo_quantity, 'received_quantity': pallet.pallet_detail.quantity,
                                 'pallet_number': pallet.pallet_detail.pallet_code, 'stages_list': rem_stages,
                                 'sub_data': [{'received_quantity': jo_quantity,
                                 'pallet_number': pallet.pallet_detail.pallet_code, 'stages_list': rem_stages, 'pallet_id': pallet.id,
                                 'status_track_id': tracking.id}], 'sku_extra_data': sku_extra_data, 'product_images': product_images })
            else:
                all_data.append({'id': rec.id, 'wms_code': rec.product_code.wms_code,
                                 'product_quantity': jo_quantity, 'received_quantity': tracking.quantity, 'pallet_number': '',
                                 'stages_list': rem_stages, 'sub_data': [{'received_quantity': jo_quantity, 'pallet_number': '',
                                 'stages_list': rem_stages, 'pallet_id': '', 'status_track_id': tracking.id}],
                                 'sku_extra_data': sku_extra_data, 'product_images': product_images })
        else:
            cond = (rec.id)
            jo_quantity = float(rec.product_quantity) - float(rec.received_quantity) - stage_quantity
            if jo_quantity <= 0:
                continue

            pallet_mapping = PalletMapping.objects.filter(pallet_detail__user=user.id,po_location__job_order__job_code=rec.job_code,
                                                          po_location__job_order__product_code__wms_code=rec.product_code.wms_code, status=2)

            if pallet_mapping:
                for pallet in pallet_mapping:
                    all_data.append({'id': rec.id, 'wms_code': rec.product_code.wms_code,
                                     'product_quantity': jo_quantity, 'received_quantity': pallet.pallet_detail.quantity,
                                     'pallet_number': pallet.pallet_detail.pallet_code, 'stages_list': stages_list, 'pallet_id': pallet.id,
                                     'status_track_id': '', 'sub_data': [{'received_quantity': jo_quantity,
                                     'pallet_number': pallet.pallet_detail.pallet_code,
                                     'stages_list': stages_list, 'pallet_id': pallet.id, 'status_track_id': ''}],
                                     'sku_extra_data': sku_extra_data, 'product_images': product_images })
            else:
                all_data.append({'id': rec.id, 'wms_code': rec.product_code.wms_code,
                                 'product_quantity': jo_quantity, 'received_quantity': jo_quantity, 'pallet_number': '',
                                 'stages_list': stages_list, 'status_track_id': '', 'sub_data': [{'received_quantity': jo_quantity,
                                 'pallet_number': '', 'stages_list': stages_list, 'pallet_id': '', 'status_track_id': ''}],
                                 'sku_extra_data': sku_extra_data, 'product_images': product_images })

    return HttpResponse(json.dumps({'data': all_data, 'job_code': job_code, 'temp': temp, 'order_ids': order_ids,
                                    'sku_brands': ','.join(sku_brands), 'sku_categories': ','.join(sku_categories),
                                    'sku_classes': ','.join(sku_classes),
                                    'creation_date': creation_date }))

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
    status_dict['status_id'] =  status_id
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
                                            processed_quantity=processed_quantity, creation_date=datetime.datetime.now())

def save_receive_pallet(all_data,user, is_grn=False):
    for key,value in all_data.iteritems():
        job_order = JobOrder.objects.get(id=key)
        for val_ind, val in enumerate(value):
            if not val[0]:
                continue
            status_type = 'JO'
            stages = list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
            if val[1].get('pallet_id') or val[1].get('pallet_number', ''):
                status_type = 'JO-PALLET'
                if val[1]['pallet_id']:
                    update_pallet_data(val[1], val[0])
                    pallet_id = val[1]['pallet_id']
                else:
                    status = 2
                    location_data = {'job_order_id': job_order.id, 'location_id': None, 'status': status, 'quantity': float(val[0]),
                                     'original_quantity': float(val[0]), 'creation_date': datetime.datetime.now()}
                    po_location = POLocation(**location_data)
                    po_location.save()
                    pallet_dict = {'pallet_number': val[1]['pallet_number'], 'received_quantity': float(val[0]), 'user': user.id}
                    pallet_id = insert_pallet_data(pallet_dict, po_location, 2)
                    all_data[key][val_ind][1]['pallet_id'] = pallet_id

            else:
                job_order.saved_quantity = float(val[0])
                job_order.save()
            if val[3]:
                processed_stage, processed_quantity = '', 0
                prev_status = StatusTracking.objects.get(id=val[3])
                if not (prev_status.status_type == status_type):
                    prev_status.original_quantity = float(prev_status.original_quantity) - float(val[0])
                prev_status.status_type = status_type
                if not (prev_status.status_value == val[2]):
                    processed_stage = prev_status.status_value
                    processed_quantity = prev_status.quantity
                elif not (prev_status.quantity == float(val[0])):
                    processed_stage = prev_status.status_value
                    processed_quantity = prev_status.quantity - float(val[0])

                if processed_stage:
                    save_status_track_summary(prev_status, user, processed_quantity, processed_stage=processed_stage)
                prev_status.quantity = float(val[0])
                prev_status.status_value = val[2]
                prev_status.save()
                if is_grn and stages and stages[-1] == val[2]:
                    save_status_track_summary(prev_status, user, float(val[0]), processed_stage=val[2])
                continue
                
            if val[2]:
                status_id = key
                if status_type=='JO-PALLET':
                    status_id = pallet_id

                stats_track = StatusTracking.objects.filter(status_id=status_id, status_type__in=['JO', 'JO-PALLET'], status_value=val[2])
                if not stats_track:
                    stats_track = save_status_tracking(status_id, status_type, val[2], float(val[0]))
                else:
                    stats_track = stats_track[0]
                    stats_track.quantity = float(stats_track.quantity) + float(val[0])
                    stats_track.original_quantity = float(stats_track.original_quantity) + float(val[0])
                    stats_track.save()
                if is_grn and stages and stages[-1] == val[2]:
                    save_status_track_summary(stats_track, user, float(val[0]), processed_stage=val[2])
                all_data[key][val_ind][3] = stats_track.id
    return all_data

@csrf_exempt
@login_required
@get_admin_user
def save_receive_jo(request, user=''):
    all_data = {}
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['id'])):
        pallet_dict = {}
        if 'pallet_number' in data_dict.keys():
            pallet_dict = {'pallet_number': data_dict['pallet_number'][i], 'pallet_id': data_dict['pallet_id'][i]}
        cond = (data_dict['id'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['received_quantity'][i], pallet_dict, data_dict['stage'][i], data_dict['status_track_id'][i] ])
    save_receive_pallet(all_data, user)

    return HttpResponse("Saved Successfully")

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
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['id'])):
        pallet_dict = {}
        if 'pallet_number' in data_dict.keys():
            pallet_dict = {'pallet_number': data_dict['pallet_number'][i], 'pallet_id': data_dict['pallet_id'][i]}
        cond = (data_dict['id'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['received_quantity'][i], pallet_dict, data_dict['stage'][i], data_dict['status_track_id'][i] ])

    all_data = save_receive_pallet(all_data,user, is_grn=True)

    for key,value in all_data.iteritems():
        count = 0
        job_order = JobOrder.objects.get(id=key)
        #pre_product = int(job_order.product_quantity) - int(job_order.received_quantity)
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
            temp_dict = {'user': user.id}
            if val[1].get('pallet_number', ''):
                temp_dict['pallet_number'] = val[1]['pallet_number']
            temp_dict['data'] = job_order
            locations = get_purchaseorder_locations(put_zone, temp_dict)
            job_order.received_quantity = float(job_order.received_quantity) + float(val[0])
            received_quantity = float(val[0])
            for loc in locations:
                if loc.zone.zone != 'DEFAULT':
                    location_quantity, received_quantity = get_remaining_capacity(loc, received_quantity, put_zone, val[1], user.id)
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
        return HttpResponse(json.dumps({'status': "Complete the production process to generate GRN for wms codes " + ", ".join(list(set(stage_status))), 'data': all_data}))
    return render(request, 'templates/toggle/jo_grn.html', {'data': putaway_data, 'job_code': job_order.job_code,
                                                            'total_received_qty': total_received_qty, 'total_order_qty': total_order_qty,
                                                            'order_date': job_order.creation_date})

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
    record = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id, status__in=['location-assigned', 'grn-generated'],
                                     product_code_id__in=sku_master_ids)
    if temp == 'true' and 'Pallet Number' not in headers:
        headers.insert(2, 'Pallet Number')
    for rec in record:
        po_location = POLocation.objects.exclude(location__isnull=True).filter(job_order_id=rec.id, status=1,
                                                 job_order__product_code__user=user.id)
        sku_extra_data, product_images, order_ids = get_order_json_data(user, mapping_id=rec.id,
                                                                           mapping_type='JO', sku_id=rec.product_code_id, order_ids=order_ids)
        for location in po_location:
            pallet_mapping = PalletMapping.objects.filter(pallet_detail__user=user.id, po_location_id=location.id, status=1)

            if pallet_mapping:
                for pallet in pallet_mapping:
                    all_data.append({'id': location.id, 'wms_code': rec.product_code.wms_code, 'location': location.location.location,
                                     'product_quantity': location.quantity, 'putaway_quantity': location.quantity,
                                     'sku_extra_data': sku_extra_data, 'product_images': product_images,
                                     'pallet_code': pallet.pallet_detail.pallet_code, 'sub_data': [{'putaway_quantity': location.quantity,
                                     'location': location.location.location}] })
            else:
                all_data.append({'id': location.id, 'wms_code': rec.product_code.wms_code, 'location': location.location.location,
                                 'product_quantity': location.quantity, 'putaway_quantity': location.quantity, 'pallet_code': '',
                                 'sku_extra_data': sku_extra_data, 'product_images': product_images,
                                 'sub_data': [{'putaway_quantity': location.quantity, 'location': location.location.location}] })
    return HttpResponse(json.dumps({'data': all_data,  'job_code': job_code, 'temp': temp, 'order_ids': order_ids}))

def validate_locations(all_data, user):
    status = ''
    for key,value in all_data.iteritems():
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
def jo_putaway_data(request, user=''):
    all_data = {}
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['id'])):
        cond = (data_dict['id'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['location'][i], data_dict['putaway_quantity'][i], data_dict['pallet_number'][i]])

    status = validate_locations(all_data, user.id)
    if status:
        return HttpResponse(status)
    for key,value in all_data.iteritems():
        data = POLocation.objects.get(id=key)
        for val in value:
            location = LocationMaster.objects.get(location=val[0], zone__user=user.id)
            if not val[1] or val[1] == '0':
                continue
            putaway_location(data, float(val[1]), location.id, user, 'job_order_id', data.job_order_id)
            filter_params = {'location_id': location.id, 'receipt_number': data.job_order.job_code,
                             'sku_id': data.job_order.product_code_id, 'sku__user': user.id, 'receipt_type': 'job order'}
            stock_data = StockDetail.objects.filter(**filter_params)
            pallet_mapping = PalletMapping.objects.filter(po_location_id=data.id,status=1)
            if pallet_mapping:
                stock_data = StockDetail.objects.filter(pallet_detail_id=pallet_mapping[0].pallet_detail.id,**filter_params)
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
            else:
                record_data = {'location_id': location.id, 'receipt_number': data.job_order.job_code,
                               'receipt_date': str(data.job_order.creation_date).split('+')[0], 'sku_id': data.job_order.product_code_id,
                               'quantity': val[1], 'status': 1, 'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now(), 'receipt_type': 'job order'}
                if pallet_mapping:
                    record_data['pallet_detail_id'] = pallet_mapping[0].pallet_detail.id
                    pallet_mapping[0].status = 0
                    pallet_mapping[0].save()
                stock_detail = StockDetail(**record_data)
                stock_detail.save()

        putaway_quantity = POLocation.objects.filter(job_order_id=data.job_order_id,
                                                     job_order__product_code__user = user.id, status=0).\
                                                     aggregate(Sum('original_quantity'))['original_quantity__sum']
        if not putaway_quantity:
            putaway_quantity = 0
        diff_quantity = float(data.job_order.received_quantity) - float(putaway_quantity)
        if (float(data.job_order.received_quantity) >= float(data.job_order.product_quantity)) and (diff_quantity <= 0):
            data.job_order.status = 'confirmed-putaway'

        data.job_order.save()

    return HttpResponse('Updated Successfully')

def validate_locations(all_data, user):
    status = ''
    for key,value in all_data.iteritems():
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
def delete_jo_group(request, user=''):
    data_dict = dict(request.POST.iterlists())
    status_dict = {'Self Produce': 'SP', 'Vendor Produce': 'VP'}
    for key, value in request.POST.iteritems():
        jo_reference = value
        job_order = JobOrder.objects.filter(jo_reference=jo_reference, order_type=status_dict[key], product_code__user=user.id)
        delete_jo_list(job_order)
    return HttpResponse("Deleted Successfully")

@csrf_exempt
@login_required
@get_admin_user
def confirm_jo_group(request, user=''):
    job_data = {}
    data_dict = dict(request.POST.iterlists())
    status_dict = {'Self Produce': 'SP', 'Vendor Produce': 'VP'}
    for key, value in request.POST.iteritems():
        tot_mat_qty = 0
        tot_pro_qty = 0
        all_data = {}
        sku_list = []
        jo_reference = value
        job_order = JobOrder.objects.filter(jo_reference=jo_reference, order_type=status_dict[key], product_code__user=user.id)
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
                all_data[cond].append({order.product_quantity: [material.material_code.wms_code, material.material_quantity, data_id ]})
                tot_mat_qty += float(material.material_quantity)
        c_date = JobOrder.objects.filter(job_code=job_code, order_type=status_dict[key], product_code__user=user.id)
        if c_date:
            creation_date = get_local_date(user, c_date[0].creation_date)
        else:
            creation_date = get_local_date(user, datetime.datetime.now())
        job_data[job_code] = { 'all_data': all_data, 'tot_pro_qty': tot_pro_qty, 'tot_mat_qty': tot_mat_qty, 'creation_date': creation_date}
        status = validate_jo(all_data, user.id, jo_reference=jo_reference)
    if not status:
        confirm_job_order(all_data, user.id, jo_reference, job_code)
        #status = save_jo_locations(all_data, user, job_code)
        status = "Confirmed Successfully"
    else:
        return HttpResponse(status)
    user_profile = UserProfile.objects.get(user_id=user.id)
    user_data = {'company_name': user_profile.company_name, 'username': user.username, 'location': user_profile.location}

    return render(request, 'templates/toggle/jo_template_group.html', {'job_data': job_data, 'user_data': user_data, 'headers': RAISE_JO_HEADERS})

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
                all_data.setdefault(cond, [0,0])
                all_data[cond][0] += record['reserved_quantity']
                break
        else:
            total += record['reserved_quantity']

    for key,value in all_data.iteritems():
        total += float(value[0])
        total_price += float(value[1])

    return render(request, 'templates/toggle/print_picklist.html', {'data': data, 'all_data': all_data, 'headers': PRINT_PICKLIST_HEADERS,
                                                                    'picklist_id': data_id,'total_quantity': total, 'total_price': total_price,
                                                                    'title': title})

@csrf_exempt
def get_rm_back_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters='', special_key=''):
    search_params = {'material_code__user': user.id, 'status': 1}
    purchase_dict = {'open_po__sku__user': user.id }
    if special_key == 'Self Produce':
        search_params['job_order__order_type'] = 'SP'
    else:
        search_params['job_order__order_type'] = 'VP'
        search_params['job_order__vendor__vendor_id'] = special_key
    order_detail = JOMaterial.objects.filter(**search_params).values('material_code__wms_code', 'material_code__sku_code',
                                      'material_code__sku_desc', 'job_order__order_type', 'material_code_id').distinct()

    if search_params['job_order__order_type'] == 'SP':
        purchase_dict['open_po__vendor_id__isnull'] = True
        purchase_dict['open_po__order_type'] = 'SR'
        stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values('sku_id').distinct().\
                                         annotate(in_stock=Sum('quantity'))
        reserved_objs = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1, reserved__gt=0).values('stock__sku_id').distinct().\
                                                        annotate(reserved=Sum('reserved'))
        reserveds = map(lambda d: d['stock__sku_id'], reserved_objs)
    else:
        purchase_dict['open_po__vendor_id__isnull'] = False
        purchase_dict['open_po__order_type'] = 'VR'
        purchase_dict['open_po__vendor__vendor_id'] = special_key
        stock_objs = VendorStock.objects.filter(sku__user=user.id, quantity__gt=0, vendor__vendor_id=special_key).\
                                         values('sku_id').distinct().annotate(in_stock=Sum('quantity'))
        reserved_objs = VendorPicklist.objects.filter(jo_material__job_order__vendor__vendor_id=special_key,
                                                      jo_material__material_code__user=user.id,
                                                      reserved_quantity__gt=0, status='open').values('jo_material__material_code_id').\
                                               distinct().annotate(reserved=Sum('reserved_quantity'))
        reserveds = map(lambda d: d['jo_material__material_code_id'], reserved_objs)

    purchase_objs = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                          filter(**purchase_dict).values('open_po__sku_id').\
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
        filter_params = {'material_code__wms_code': wms_code, 'material_code__user': user.id, 'status': 1, 'job_order__order_type': 'SP'}
        if order['job_order__order_type'] == 'VP':
            filter_params['job_order__order_type'] = 'VP'
            filter_params['job_order__vendor__vendor_id'] = special_key

        rw_orders = RWOrder.objects.filter(job_order__product_code__sku_code=sku_code, vendor__user=user.id).\
                                    values_list('job_order_id', flat=True)
        if rw_orders:
            filter_params['job_order_id__in'] = rw_orders
        order_quantity = JOMaterial.objects.filter(**filter_params).\
                                            aggregate(Sum('material_quantity'))['material_quantity__sum']
        if not order_quantity:
            order_quantity = 0
        if order['material_code_id'] in stocks:
            stock_quantity = map(lambda d: d['in_stock'], stock_objs)[stocks.index(order['material_code_id'])]
        if order['material_code_id'] in reserveds:
            reserved_quantity = map(lambda d: d['reserved'], reserved_objs)[reserveds.index(order['material_code_id'])]
        if order['material_code_id'] in purchases:
            total_order = map(lambda d: d['total_order'], purchase_objs)[purchases.index(order['material_code_id'])]
            total_received = map(lambda d: d['total_received'], purchase_objs)[purchases.index(order['material_code_id'])]
            diff_quantity = float(total_order) - float(total_received)
            if diff_quantity > 0:
                transit_quantity = diff_quantity
        procured_quantity = order_quantity - stock_quantity - transit_quantity
        if procured_quantity > 0:
            checkbox = "<input type='checkbox' id='back-checked' name='%s'>" % title
            master_data.append({'': checkbox, 'WMS Code': wms_code, 'Ordered Quantity': order_quantity,
                                'Stock Quantity': get_decimal_limit(user.id, stock_quantity),
                                'Transit Quantity': get_decimal_limit(user.id, transit_quantity),
                                'Procurement Quantity': get_decimal_limit(user.id, procured_quantity), 'DT_RowClass': 'results'})
    if search_term:
        master_data = filter(lambda person: search_term in person['WMS Code'] or search_term in str(person['Ordered Quantity']) or\
               search_term in str(person['Stock Quantity']) or search_term in str(person['Transit Quantity']) or \
               search_term in str(person[' Procurement Quantity']), master_data)
    elif order_term:
        if order_term == 'asc':
            master_data = sorted(master_data, key = lambda x: x[BACK_ORDER_RM_TABLE[col_num-1]])
        else:
            master_data = sorted(master_data, key = lambda x: x[BACK_ORDER_RM_TABLE[col_num-1]], reverse=True)
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
    for key,value in request.POST.iteritems():
        price = 0
        key = key.split(":")
        selected_item = ''
        sku_supplier = SKUSupplier.objects.filter(sku__wms_code=key[0], sku__user=user.id)
        if sku_supplier:
            selected_item = {'id': sku_supplier[0].supplier_id, 'name': sku_supplier[0].supplier.name}
            price = sku_supplier[0].price
        data_dict.append({'wms_code': key[0], 'title': key[1] , 'quantity': value, 'selected_item': selected_item, 'price': price})
    return HttpResponse(json.dumps({'data_dict': data_dict, 'supplier_list': supplier_list}))

@csrf_exempt
@get_admin_user
def confirm_back_order(request, user=''):
    all_data = {}
    status = ''
    total = 0
    total_qty = 0
    customization = ''
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['wms_code'])):
        if not (data_dict['quantity'][i] and data_dict['supplier_id'][i]):
            continue
        cond = (data_dict['supplier_id'][i])
        all_data.setdefault(cond, [])
        order_id = ''
        if 'order_id' in request.POST.keys() and data_dict['order_id'][i]:
            order_id = data_dict['order_id'][i]
        all_data[cond].append(( data_dict['wms_code'][i], data_dict['quantity'][i], data_dict['title'][i], data_dict['price'][i],
                                data_dict['remarks'][i], order_id))

    for key,value in all_data.iteritems():
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

            sku_extra_data = ''
            if val[5]:
                create_order_mapping(user, purchase_order.id, val[5], mapping_type='PO')
                sku_extra_data, product_images, order_ids = get_order_json_data(user, mapping_id=purchase_order.id, mapping_type='PO',
                                                                                sku_id=sku_master.id, order_ids=[])
                if sku_extra_data:
                    customization = 'true'

            # Send Mail code
            supplier_code = ''
            supplier_mapping = SKUSupplier.objects.filter(sku_id=purchase_order.open_po.sku_id, supplier_id=purchase_order.open_po.supplier_id,
                                                          sku__user=user.id)
            if supplier_mapping:
                supplier_code = supplier_mapping[0].supplier_code

            amount = float(purchase_order.open_po.order_quantity) * float(purchase_order.open_po.price)
            total += amount
            supplier = purchase_order.open_po.supplier
            total_qty += purchase_order.open_po.order_quantity
            wms_code = purchase_order.open_po.sku.wms_code
            telephone = supplier.phone_number
            name = supplier.name
            order_id =  purchase_order.order_id
            supplier_email = supplier.email_id
            order_date = get_local_date(request.user, purchase_order.creation_date)
            address = '\n'.join(supplier.address.split(','))
            vendor_name = ''
            vendor_address = ''
            vendor_telephone = ''
            if purchase_order.open_po.order_type == 'VR':
                vendor_address = purchase_order.open_po.vendor.address
                vendor_address = '\n'.join(vendor_address.split(','))
                vendor_name = purchase_order.open_po.vendor.name
                vendor_telephone = purchase_order.open_po.vendor.phone_number

            po_reference = '%s%s_%s' % (purchase_order.prefix, str(purchase_order.creation_date).split(' ')[0].replace('-', ''), order_id)
            table_headers = ('WMS Code', 'Supplier Code', 'Description', 'Quantity', 'Unit Price', 'Amount', 'Remarks')

            po_data.append(( wms_code, supplier_code, purchase_order.open_po.sku.sku_desc, purchase_order.open_po.order_quantity,
                             purchase_order.open_po.price, amount, purchase_order.open_po.remarks, sku_extra_data))

            profile = UserProfile.objects.get(user=request.user.id)
            data_dictionary = {'table_headers': table_headers, 'data': po_data, 'address': address, 'order_id': order_id,
                         'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total, 'po_reference': po_reference,
                         'user_name': request.user.username, 'total_qty': total_qty, 'company_name': profile.company_name,
                         'location': profile.location, 'w_address': profile.address,
                         'company_name': profile.company_name, 'vendor_name': vendor_name, 'vendor_address': vendor_address,
                         'vendor_telephone': vendor_telephone, 'customization': customization}

        t = loader.get_template('templates/toggle/po_download.html')
        c = Context(data_dictionary)
        rendered = t.render(c)
        send_message = 'false'
        data = MiscDetail.objects.filter(user=user.id, misc_type='send_message')
        if data:
            send_message = data[0].misc_value
        if send_message == 'true':
            write_and_mail_pdf(po_reference, rendered, request, supplier_email, telephone, po_data, str(order_date).split(' ')[0])

        if not status:
            status = "Created PO Numbers are " + str(order_id)
        else:
            status += ", " + str(order_id)
    return HttpResponse(status)

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
                all_data.append({'product_code': key, 'product_quantity': value, 'material_code': bom.material_sku.sku_code,
                                 'material_quantity': float(bom.material_quantity), 'id': ''})
        else:
            all_data.append({'product_code': key, 'product_quantity': value, 'material_code': '', 'material_quantity': '', 'id': ''})
    vendors = list(VendorMaster.objects.filter(user=user.id).values('vendor_id', 'name'))
    return HttpResponse(json.dumps({'title': title, 'data': all_data, 'display': 'display-none', 'vendors': vendors}))

@csrf_exempt
@login_required
@get_admin_user
def save_rwo(request, user=''):
    all_data = {}
    jo_reference = request.POST.get('jo_reference','')
    vendor_id = request.POST.get('vendor','')
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
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i], data_dict['material_quantity'][i], data_id,
                               '' ]})
    status = validate_jo(all_data, user.id, jo_reference='')
    if not status:
        all_data = insert_jo(all_data, user.id, jo_reference, vendor_id)
        status = "Added Successfully"
    return HttpResponse(status)

@csrf_exempt
@login_required
@get_admin_user
def confirm_rwo(request, user=''):
    all_data = {}
    sku_list = []
    tot_mat_qty = 0
    tot_pro_qty = 0
    jo_reference = request.POST.get('jo_reference','')
    vendor_id = request.POST.get('vendor','')
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
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i], data_dict['material_quantity'][i], data_id,
                               '' ]})
    status = validate_jo(all_data, user.id, jo_reference='')
    if not status:
        all_data = insert_jo(all_data, user.id, jo_reference, vendor_id)
        job_code = get_job_code(user.id)
        confirm_job_order(all_data, user.id, jo_reference, job_code)
    if status:
        return HttpResponse(status)
    creation_date = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id)[0].creation_date
    user_profile = UserProfile.objects.get(user_id=user.id)
    user_data = {'company_name': user_profile.company_name, 'username': user.first_name, 'location': user_profile.location}
    rw_order = RWOrder.objects.filter(job_order__jo_reference=jo_reference, vendor__user=user.id)

    return render(request, 'templates/toggle/rwo_template.html', {'tot_mat_qty': tot_mat_qty, 'tot_pro_qty': tot_pro_qty, 'all_data': all_data,
                                                                 'creation_date': creation_date, 'job_code': job_code, 'user_data': user_data,
                                                                 'headers': RAISE_JO_HEADERS, 'name': rw_order[0].vendor.name,
                                                                 'address':rw_order[0].vendor.address,
                                                                 'telephone': rw_order[0].vendor.phone_number})

def insert_rwo(job_order_id, vendor_id):
    rwo_dict = copy.deepcopy(RWO_FIELDS)
    rwo_dict['job_order_id'] = job_order_id
    rwo_dict['vendor_id']  = vendor_id
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
                                             job_order__product_code_id__in=sku_master_ids).order_by(order_data).\
                                       values_list('job_order__jo_reference', flat=True)
    if search_term:
        master_data = RWOrder.objects.filter(job_order__product_code_id__in=sku_master_ids).\
                                      filter(Q(job_order__job_code__icontains=search_term) | Q(vendor__vendor_id__icontains=search_term) |
                                              Q(vendor__name__icontains=search_term) | Q(creation_date__regex=search_term),
                                              job_order__status='RWO', job_order__product_code__user=user.id).\
                                       values_list('job_order__jo_reference', flat=True).order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        data = RWOrder.objects.filter(job_order__jo_reference=data_id, job_order__product_code__user=user.id, job_order__status='RWO',
                                      job_order__product_code_id__in=sku_master_ids)[0]
        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        temp_data['aaData'].append({'': checkbox, 'RWO Reference': data.job_order.jo_reference, 'Vendor ID': data.vendor.vendor_id,
                                    'Vendor Name': data.vendor.name, 'Creation Date': str(data.creation_date).split('+')[0],
                                    'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.job_order.jo_reference}})

@csrf_exempt
@login_required
@get_admin_user
def saved_rwo_data(request, user=''):
    jo_reference = request.GET['data_id']
    all_data = []
    title = "Update Returnable Work Order"
    record = RWOrder.objects.filter(job_order__jo_reference=jo_reference, job_order__product_code__user=user.id, job_order__status='RWO')
    for rec in record:
        record_data = {}
        record_data['product_code'] = rec.job_order.product_code.sku_code
        record_data['product_description'] = rec.job_order.product_quantity
        record_data['sub_data'] = []
        jo_material = JOMaterial.objects.filter(job_order_id= rec.job_order.id,status=1)
        for jo_mat in jo_material:
            dict_data = {'material_code': jo_mat.material_code.sku_code, 'material_quantity': jo_mat.material_quantity, 'id': jo_mat.id}
            record_data['sub_data'].append(dict_data)
        all_data.append(record_data)
    return HttpResponse(json.dumps({'data': all_data, 'jo_reference': jo_reference, 'title': title, 'vendor': {'vendor_name': record[0].vendor.name, 'vendor_id': record[0].vendor_id}}))

def validate_jo_vendor_stock(all_data, user, job_code):
    status = ''
    for key,value in all_data.iteritems():
        job_order = JobOrder.objects.filter(job_code=job_code, product_code__wms_code=key, product_code__user=user)
        for val in value:
            for data in val.values():
                stock_quantity = VendorStock.objects.filter(vendor_id=job_order[0].vendor_id, sku__wms_code=data[0], quantity__gt=0,
                                                     sku__user=user).aggregate(Sum('quantity'))['quantity__sum']
                reserved_quantity = VendorPicklist.objects.filter(jo_material__material_code__wms_code=data[0],
                                                                  reserved_quantity__gt=0, jo_material__material_code__user=user,
                                                                  status='open').aggregate(Sum('reserved_quantity'))['reserved_quantity__sum']

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
    for key,value in all_data.iteritems():
        job_order = JobOrder.objects.filter(job_code=job_code, product_code__wms_code=key, product_code__user=user.id)
        for val in value:
            for data in val.values():
                jo_material = JOMaterial.objects.get(id=data[2])
                stock_detail = VendorStock.objects.filter(quantity__gt=0, sku_id=jo_material.material_code_id, sku__user=user.id,
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
    return "Confirmed Successfully"



@csrf_exempt
@login_required
@get_admin_user
def generate_vendor_picklist(request, user=''):
    all_data = {}
    job_code = request.POST.get('job_code','')
    headers = list(PICKLIST_HEADER1)
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
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i], data_dict['material_quantity'][i], data_id ]})
    status = validate_jo_vendor_stock(all_data, user.id, job_code)
    if status:
        return HttpResponse(status)
    consume_vendor_stock(all_data, user, job_code)
    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def get_vendor_types(request, user=''):
    vendor_names = list(JobOrder.objects.filter(product_code__user=user.id, status='order-confirmed', vendor_id__isnull=False).\
                        values('vendor__vendor_id', 'vendor__name').distinct())
    return HttpResponse(json.dumps({'data': vendor_names}))

