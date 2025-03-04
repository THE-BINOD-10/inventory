
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
import copy
import json
from itertools import chain
from decimal import Decimal
from django.db.models import Q, F, DateField
from collections import OrderedDict
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
from django.template import loader, Context
from django.db.models.functions import Cast
from django.core.files.storage import FileSystemStorage
from mail_server import send_mail, send_mail_attachment
from common import *
from common_operations import *
from miebach_utils import *
from operator import itemgetter
from django.db.models import Sum
from django.db.models import Max
from itertools import groupby
import datetime
import shutil
import requests
import httplib2
from utils import *
import os, math


log = init_logger('logs/outbound.log')
picklist_qc_log =  init_logger('logs/picklist_qc_log.log')
payment_log = init_logger('logs/payments.log')

today = datetime.datetime.now().strftime("%Y%m%d")

import itertools


@csrf_exempt
def get_batch_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters,
                   user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_dict = eval(user_dict)
    lis = ['sku__sku_code', 'sku__sku_code', 'title', 'total']
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}

    if user_dict.get('market_places', ''):
        marketplace = user_dict['market_places'].split(',')
        data_dict['marketplace__in'] = marketplace
    if user_dict.get('customer_id', ''):
        data_dict['customer_id'], data_dict['customer_name'] = user_dict['customer_id'].split(':')
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_params = get_filtered_params(filters, ['sku__sku_code', 'title', 'total'])
    search_params['sku_id__in'] = sku_master_ids
    if not request.user.is_staff:
        perm_status_list, check_ord_status = get_view_order_statuses(request, user)
        if check_ord_status:
            search_params['customerordersummary__status__in'] = perm_status_list

    if search_term:
        mapping_results = OrderDetail.objects.filter(**data_dict).values('sku__sku_code', 'title',
                                                                         'sku_code').distinct(). \
            annotate(total=Sum('quantity')).filter(Q(sku__sku_code__icontains=search_term) |
                                                   Q(title__icontains=search_term) | Q(total__icontains=search_term),
                                                   **search_params) \
            .exclude(order_code="CO").order_by(order_data)
    else:
        mapping_results = OrderDetail.objects.filter(**data_dict).values('sku__sku_code', 'title',
                                                                         'sku_code').distinct(). \
            annotate(total=Sum('quantity')).filter(**search_params).exclude(order_code="CO") \
            .order_by(order_data)

    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    index = 0
    for dat in mapping_results[start_index:stop_index]:

        sku_code = dat['sku__sku_code']
        if sku_code == 'TEMP':
            sku_code = dat['sku_code']

        check_values = dat['sku__sku_code'] + '<>' + sku_code + '<>' + dat['title']
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (check_values, dat['total'])

        temp_data['aaData'].append(
            OrderedDict((('data_value', check_values), ('SKU Code', sku_code), ('Title', dat['title']),
                         ('Total Quantity', dat['total']), ('id', index), ('DT_RowClass', 'results'))))
        index += 1


@csrf_exempt
def get_order_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters={},
                      user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    if user_dict:
        user_dict = eval(user_dict)
    lis = ['id', 'order_id', 'address', 'sku__sku_code', 'title', 'quantity', 'shipment_date', 'city', 'status']

    unsorted_dict = {6: 'Order Taken By', 7: 'Status'}
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}

    if user_dict.get('market_places', ''):
        marketplace = user_dict['market_places'].split(',')
        data_dict['marketplace__in'] = marketplace
    if user_dict.get('customer_id', ''):
        data_dict['customer_id'], data_dict['customer_name'] = user_dict['customer_id'].split(':')

    search_params = get_filtered_params(filters, lis[1:])
    if 'shipment_date__icontains' in search_params.keys():
        search_params['shipment_date__regex'] = search_params['shipment_date__icontains']
        del search_params['shipment_date__icontains']
    if 'order_id__icontains' in search_params.keys():
        order_search = search_params['order_id__icontains']
        search_params['order_id__icontains'] = ''.join(re.findall('\d+', order_search))
        search_params['order_code__icontains'] = ''.join(re.findall('\D+', order_search))

    search_params['sku_id__in'] = sku_master_ids
    if 'city__icontains' in search_params.keys():
        order_taken_val_user = CustomerOrderSummary.objects.filter(
            order_taken_by__icontains=search_params['city__icontains'],
            order__user=user.id)
        search_params['id__in'] = order_taken_val_user.values_list('order_id', flat=True)
        del (search_params['city__icontains'])
    if 'status__icontains' in search_params.keys():
        stat_search = {}
        if search_params.has_key('id__in'):
            stat_search['order_id__in'] = search_params['id__in']
        order_taken_val_user = CustomerOrderSummary.objects.filter(status__icontains=search_params['status__icontains'],
                                                                   order__user=user.id, **stat_search)
        search_params['id__in'] = order_taken_val_user.values_list('order_id', flat=True)
        del (search_params['status__icontains'])

    if not request.user.is_staff:
        perm_status_list, check_ord_status = get_view_order_statuses(request, user)
        if check_ord_status:
            search_params['customerordersummary__status__in'] = perm_status_list
    if search_term:
        master_data = OrderDetail.objects.filter(
            Q(sku__sku_code__icontains=search_term) | Q(order_id__icontains=search_term) | Q(title__icontains=search_term) |
            Q(quantity__icontains=search_term,status=1) | Q(original_order_id__icontains=search_term), user=user.id, status=1, quantity__gt=0).\
            filter(**search_params).exclude(order_code="CO")
    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = OrderDetail.objects.filter(**data_dict).filter(**search_params).exclude(order_code="CO").order_by(
            order_data)
    else:
        master_data = OrderDetail.objects.filter(**data_dict).filter(**search_params).exclude(order_code="CO").order_by(
            'shipment_date')

    custom_search = False
    if col_num in unsorted_dict.keys():
        custom_search = True

    if stop_index and not custom_search:
        master_data = master_data[start_index:stop_index]

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    count = 0
    order_summary_objs = CustomerOrderSummary.objects.filter(order__user=user.id).values('order__order_id', \
                                                                                         'shipment_time_slot', 'status',
                                                                                         'order_taken_by').distinct()
    all_seller_orders = SellerOrder.objects.filter(order__user=user.id, status=0)
    for data in master_data:
        sku_code = data.sku.sku_code
        order_id = ''
        if data.order_id:
            order_id = data.order_code + str(int(data.order_id))
        if data.original_order_id:
            order_id = data.original_order_id
        cust_status_obj = order_summary_objs.filter(order_id=data.id, order__user=user.id)
        cust_status = ''
        time_slot = ''
        order_taken_val = ''
        if cust_status_obj:
            cust_status = cust_status_obj[0]['status']
            time_slot = cust_status_obj[0]['shipment_time_slot']
            order_taken_val = cust_status_obj[0]['order_taken_by']

        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data.id, data.sku.sku_code)
        shipment_data = get_local_date(request.user, data.shipment_date, True).strftime("%d %b, %Y")
        if time_slot:
            if "-" in time_slot:
                time_slot = time_slot.split("-")[0]

            shipment_data = shipment_data + ', ' + time_slot
        # try:
        #     order_id = int(float(order_id))
        # except:
        #     order_id = str(xcode(order_id))
        quantity = float(data.quantity)
        seller_order = all_seller_orders.filter(order_id=data.id).aggregate(Sum('quantity'))['quantity__sum']
        if seller_order:
            quantity = quantity - seller_order
        is_excel_download = request.POST.get('excel')
        central_order_reassigning =  get_misc_value('central_order_reassigning', user.id) # for 72networks
        if central_order_reassigning == 'true' and is_excel_download:
            batch_number =''
            batch_date =''
            branch_name =''
            branch_id = ''
            loan_proposal_code =''
            client_code = ''
            client_id =''
            customer_name = ''
            address1 = ''
            address2 = ''
            landmark = ''
            village = ''
            district = ''
            state = ''
            pincode = ''
            mobile_no =''
            alternative_mobile_no =''
            model = ''
            total_price =''
            unit_price = ''
            cgst = ''
            sgst = ''
            igst = ''
            location_name = ''
            try :
                interm_obj = IntermediateOrders.objects.filter(order_id=str(data.id))
                if interm_obj :
                    orderfield_obj = OrderFields.objects.filter(original_order_id=str(data.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id))
                    if orderfield_obj:
                        for order_field in orderfield_obj :
                            if order_field.name == 'batch_number':
                                batch_number = order_field.value
                            elif order_field.name == 'batch_date' :
                                batch_date = order_field.value
                            elif order_field.name == 'branch_id' :
                                branch_id = order_field.value
                            elif order_field.name == 'branch_name' :
                                branch_name = order_field.value
                            elif order_field.name == 'loan_proposal_code':
                                loan_proposal_code = order_field.value
                            elif order_field.name == 'client_code' :
                                client_code = order_field.value
                            elif order_field.name == 'client_id' :
                                client_id = order_field.value
                            elif order_field.name == 'customer_name' :
                                customer_name = order_field.value
                            elif order_field.name == 'address1' :
                                address1 = order_field.value
                            elif order_field.name == 'address2' :
                                address2 = order_field.value
                            elif order_field.name == 'landmark' :
                                landmark = order_field.value
                            elif order_field.name == 'village' :
                                village = order_field.value
                            elif order_field.name == 'district' :
                                district = order_field.value
                            elif order_field.name == 'state' :
                                state = order_field.value
                            elif order_field.name == 'pincode' :
                                pincode = order_field.value
                            elif order_field.name == 'mobile_no' :
                                mobile_no = order_field.value
                            elif order_field.name == 'alternative_mobile_no' :
                                alternative_mobile_no = order_field.value
                            elif order_field.name == 'model' :
                                model = order_field.value
                            elif order_field.name == 'total_price' :
                                total_price = order_field.value
                    unit_price = interm_obj[0].unit_price
                    cgst = interm_obj[0].cgst_tax
                    sgst = interm_obj[0].sgst_tax
                    igst = interm_obj[0].igst_tax
                    location = interm_obj[0].order_assigned_wh
                    location_name = location.username
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info('downloading excel  failed for %s and params are %s and error statement is %s' % (
                str(user.username), str(request.POST.dict()), str(e)))

            temp_data['aaData'].append(OrderedDict((('Central Order ID', data.original_order_id),('Batch Number',batch_number),
                                                    ('Batch Date',batch_date),('Branch ID',branch_id),('Branch Name',branch_name),('Loan Proposal ID',data.original_order_id),('Loan Proposal Code',loan_proposal_code),('Client Code',client_code),('Client ID',client_id),
                                                    ('Customer Name',data.customer_name),('Address1',address1),('Address2',address2),('Landmark',landmark),('Village',village),('District',district),
                                                    ('State1',state),('Pincode',pincode),('Mobile Number',mobile_no),('Alternative Mobile Number',alternative_mobile_no),('SKU Code',sku_code),('Model',model),
                                                    ('Unit Price',unit_price),('CGST',cgst),('SGST',sgst),('IGST',igst),('Total Price',total_price),('Location',location_name))))
        else:
            temp_data['aaData'].append(OrderedDict((('', checkbox), ('Order ID', order_id), ('SKU Code', sku_code),
                                                ('Title', data.title), ('id', count), ('Product Quantity', quantity),
                                                ('Shipment Date', shipment_data),
                                                ('Marketplace', data.marketplace),
                                                ('Address', data.address),
                                                ('Name',data.address),
                                                ('DT_RowClass', 'results'),
                                                ('DT_RowAttr', {'data-id': str(data.order_id)}),
                                                ('Order Taken By', order_taken_val), ('Status', cust_status))))
        count = count + 1
    col_val = ['Order ID', 'Order ID', 'SKU Code', 'Title', 'Product Quantity', 'Shipment Date', 'Order Taken By',
               'Status']
    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(col_val, temp_data['aaData'], order_term, '', col_num, exact=False)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


@csrf_exempt
def get_stock_transfer_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['id', 'st_po__open_st__warehouse__username', 'order_id', 'sku__sku_code','creation_date', 'quantity']
    users = [user.id]
    users = check_and_get_plants(request, users)
    user_ids = list(users.values_list('id', flat=True))
    if user.userprofile.user_type == 'marketplace_user':
        lis.insert(3, 'st_seller__seller_id')
        lis.insert(4, 'st_seller__name')
        lis.insert(5, 'st_po__open_st__mrp')
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = StockTransfer.objects.filter(sku__user__in=user_ids, status=1, st_type='ST_INTRA').order_by(order_data)
    if search_term:
        master_data = StockTransfer.objects.filter(Q(st_po__open_st__warehouse__username__icontains=search_term) |
                                               Q(quantity__icontains=search_term) | Q(order_id__icontains=search_term) |
                                               Q(sku__sku_code__icontains=search_term) |
                                               Q(st_seller__seller_id__icontains=search_term) |
                                               Q(st_seller__name__icontains=search_term),
                                               sku__user__in=user_ids,
                                               status=1, st_type='ST_INTRA').order_by(order_data)
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    count = 0
    for data in master_data[start_index:stop_index]:
        checkbox = '<input type="checkbox" name="id" value="%s">' % data.id
        w_user = User.objects.get(id=data.st_po.open_st.sku.user)
        data_dict = {'': checkbox, 'source_wh': data.st_po.open_st.warehouse.username, 'Warehouse Name': w_user.username, 'Stock Transfer ID': data.order_id,
                                    'SKU Code': data.sku.sku_code, 'Quantity': data.quantity-data.picked_quantity, 'DT_RowClass': 'results',
                                    'Creation Date':data.creation_date.strftime("%d %b, %Y"),
                                    'Seller ID': '', 'Seller Name': '', 'MRP':'',
                                    'warehouse_id': data.sku.user,
                                    'DT_RowAttr': {'id': data.id}, 'id': count}
        if user.userprofile.user_type == 'marketplace_user' and data.st_seller:
            data_dict['Seller ID'] = data.st_seller.seller_id
            data_dict['Seller Name'] = data.st_seller.name
            data_dict['MRP'] = data.st_po.open_st.mrp
        temp_data['aaData'].append(data_dict)
        count = count + 1


@csrf_exempt
def open_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, status=''):
    #sku_master, sku_master_ids = get_sku_master(user, request.user)
    status_dict = eval(status)
    filter_params = {}
    users = [user.id]
    if request.user.is_staff and user.userprofile.warehouse_type == 'ADMIN':
        users = get_related_users_filters(user.id)
    else:
        users = check_and_get_plants_depts(request, users)
    user_ids = list(users.values_list('id', flat=True))
    isprava_permission = get_misc_value('order_exceed_stock', user.id)
    delivery_challana = get_misc_value('generate_delivery_challan_before_pullConfiramation', user.id)
    lis = ['picklist_number', 'order__customer_name', 'remarks','picklist_number',
          'order__marketplace', 'order__sku__sku_code']
    admin_user = get_admin(user)
    if isprava_permission == 'true':
       lis.append('order__intermediateorders__project_name')
    if delivery_challana == 'true':
       lis.append('order__tempdeliverychallan__dc_number')
    if isinstance(status_dict, dict):
        status = status_dict['status']
        if status_dict.get('market_place', ''):
            filter_params['order__marketplace'] = status_dict['market_place']
        filter_params['status__icontains'] = status
    if 'open' in status:
        filter_params['status__icontains'] = "open"
        filter_params['reserved_quantity__gt'] = 0
    else:
        if not status == 'batch_picked':
            del filter_params['status__icontains']
        filter_params['picked_quantity__gt'] = 0
    log.info(status)
    if status == 'batch_picked':
        col_num = col_num - 1
        header = BATCH_PICK_LIST_HEADERS
    elif status == 'picked':
        header = PICKED_PICK_LIST_HEADERS
    else:
        header = OPEN_PICK_LIST_HEADERS
    all_picks = Picklist.objects.select_related('order', 'stock').\
                                filter(Q(order__sku__user__in=user_ids) | Q(stock__sku__user__in=user_ids), **filter_params)
    if search_term:
        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(lis, search_term)
        master_data = all_picks.filter(search_query)
    elif order_term:
        # col_num = col_num - 1
        order_data = header.values()[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data

        master_data = all_picks.order_by(order_data)
    else:
        master_data = all_picks

    total_reserved_quantity = master_data.aggregate(total_res=Sum(F('reserved_quantity')/F('stock__batch_detail__pcf')))['total_res']
    total_picked_quantity = master_data.aggregate(total_pick=Sum(F('picked_quantity')/F('stock__batch_detail__pcf')))['total_pick']
    master_data = master_data.values('picklist_number', 'stock__sku__user').distinct()
    if order_term:
        master_data = [key for key, _ in groupby(master_data)]

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    if not total_picked_quantity:
        total_picked_quantity = 0
    else:
        temp_data['totalPickedQuantity'] = int(total_picked_quantity)

    if not total_reserved_quantity:
        temp_data['totalReservedQuantity'] = 0
    else:
        temp_data['totalReservedQuantity'] = int(total_reserved_quantity)

    count = 0
    od_id, od_order_id = '', ''
    for data in master_data[start_index:stop_index]:
        dc_num = ''
        prepare_str = ''
        shipment_date = ''
        project_name = ''
        source_wh = ''
        order_type = 'Sales Order'
        create_date_value, order_marketplace, order_customer_name, picklist_id, remarks = '', [], [], '', ''
        pick_filter_dict = {'picklist_number': data['picklist_number']}
        if data['stock__sku__user']:
            pick_filter_dict['stock__sku__user'] = data['stock__sku__user']
        picklist_obj = all_picks.filter(**pick_filter_dict)
        reserved_quantity_sum_value = picklist_obj.aggregate(total_res=Sum(F('reserved_quantity')/F('stock__batch_detail__pcf')))['total_res']
        if not reserved_quantity_sum_value:
            reserved_quantity_sum_value = 0
        picked_quantity_sum_value = picklist_obj.aggregate(total_pick=Sum(F('picked_quantity')/F('stock__batch_detail__pcf')))['total_pick']
        if not picked_quantity_sum_value:
            picked_quantity_sum_value = 0
        if picklist_obj:
            warehouse_id = picklist_obj[0].stock.sku.user if picklist_obj[0].stock else picklist_obj[0].order.sku.user
            order_marketplace = list(
                picklist_obj.exclude(order__marketplace__in='').filter(order_id__isnull=False).values_list(
                    'order__marketplace', flat=True))
            order_customer_name = list(
                picklist_obj.exclude(order__customer_name='').filter(order_id__isnull=False).values_list(
                    'order__customer_name', flat=True))

            order_marketplace1 = [str(x).upper() for x in order_marketplace]
            if 'OFFLINE' in order_marketplace1 and len(set(order_marketplace1)) == 1:
                prepare_str = ','.join(list(set(order_customer_name)))
            else:
                prepare_str = ','.join(list(set(order_marketplace)))
            if not prepare_str:
                st_order = STOrder.objects.filter(picklist_id=picklist_obj[0].id)
                if st_order:
                    if st_order[0].stock_transfer.st_type == 'MR':
                        order_type = 'Material Request'
                    elif st_order[0].stock_transfer.st_type == 'ST_INTRA':
                        order_type = 'Stock Transfer'
                    try:
                        source_wh = st_order[0].stock_transfer.st_po.open_st.warehouse.first_name
                    except Exception as e:
                        source_wh = ''
                    user_id = st_order[0].stock_transfer.st_po.open_st.sku.user
                    user_profile = User.objects.get(id=user_id)
                    if user_profile:
                        prepare_str = user_profile.first_name
            if not prepare_str and picklist_obj[0].order:
                order_id = picklist_obj[0].order.original_order_id
                if admin_user.username == 'isprava_admin':
                    project_details = IntermediateOrders.objects.filter(order__order_id = picklist_obj[0].order.order_id, order_assigned_wh= user.id).values('project_name')
                    if project_details.exists():
                        project_name = project_details[0]['project_name']
                if order_id:
                    order_fields = OrderFields.objects.filter(original_order_id=order_id, name="original_order_id")
                    if order_fields:
                        user_id = order_fields[0].user
                        user_profile = UserProfile.objects.get(user_id=user_id)
                        if user_profile:
                            prepare_str = user_profile.user.first_name
            create_date_value = ""
            if picklist_obj[0].creation_date:
                create_date_value = get_local_date(request.user, picklist_obj[0].creation_date)

            remarks = picklist_obj[0].remarks
            if remarks == 'Auto-generated Picklist':
                od_id = int(picklist_obj[0].order.id)
                od_order_id = str(picklist_obj[0].order.order_code) + str(picklist_obj[0].order.order_id)
            picklist_id = picklist_obj[0].picklist_number
            dc_number_obj = TempDeliveryChallan.objects.filter(order__sku__user = user.id , picklist_number = picklist_id ).values('dc_number')
            if dc_number_obj:
                dc_num = dc_number_obj[0]['dc_number']

            first_ord_obj = picklist_obj.exclude(order__shipment_date__isnull=True).values_list('order__id',
                                                                                                flat=True).order_by(
                'order__shipment_date')
            shipment_date = ""
            if first_ord_obj:
                ship_date = OrderDetail.objects.get(id=first_ord_obj[0]).shipment_date
                shipment_date = get_local_date(user, ship_date, True)
                shipment_date = shipment_date.strftime("%d %b, %Y")

                time_slot = get_shipment_time(first_ord_obj[0], user)
                if time_slot:
                    shipment_date = shipment_date + ', ' + time_slot
        result_data = OrderedDict((('DT_RowAttr', {'data-id': picklist_id}), ('picklist_note', remarks),
                                   ('reserved_quantity', reserved_quantity_sum_value), ('order_type', order_type),
                                   ('picked_quantity', picked_quantity_sum_value), ('source_wh', source_wh),
                                   ('customer', prepare_str), ('shipment_date', shipment_date),
                                   ('date', create_date_value),('dc_number', dc_num), ('id', count), ('DT_RowClass', 'results'),
                                   ('od_id', od_id), ('od_order_id', od_order_id), ('project_name', project_name),
                                   ('warehouse_id', warehouse_id)))
        dat = 'picklist_id'
        count += 1
        if status == 'batch_picked':
            dat = 'picklist_id'

            checkbox = "<input type='checkbox' name='%s' value='%s'>" % (
            data['picklist_number'], data['picklist_number'])
            result_data['checkbox'] = checkbox
        result_data[dat] = picklist_id
        temp_data['aaData'].append(result_data)


@csrf_exempt
def get_customer_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    sno = 0
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    gateout = request.POST.get('gateout', 0)
    filter_dict = {'order__sku_id__in': sku_master_ids, 'order_shipment__user': user.id}
    exclude_dict = {'shipmenttracking__ship_status__in': ['Delivered', 'Out for Delivery']}
    if gateout:
        gateout = int(gateout)
        if gateout:
            filter_dict['shipmenttracking__ship_status__in'] = ['Delivered', 'Out for Delivery']
            del exclude_dict['shipmenttracking__ship_status__in']
    one_assist_qc_check = get_misc_value('dispatch_qc_check', user.id)
    central_order_reassigning =  get_misc_value('central_order_reassigning', user.id)
    one_assist_qc_check = get_misc_value('dispatch_qc_check', user.id)
    if central_order_reassigning == 'true' and one_assist_qc_check != 'true':
        #lis = ['Serial Number', 'Manifest Number', 'Total Quantity', 'Manifest Date']
        lis = ['order_shipment__shipment_number', 'order_shipment__manifest_number', 'ship_quantity', 'order_shipment__shipment_number']
    else:
        lis = ['order_shipment__shipment_number', 'order__customer_id', 'order__customer_name', 'order_shipment__manifest_number', 'ship_quantity',
                'order_shipment__shipment_number']
    all_data = OrderedDict()
    shipment_objs = ShipmentInfo.objects.filter(**filter_dict).\
                                        exclude(**exclude_dict)
    if search_term:
        results = shipment_objs.\
            filter(Q(order_shipment__shipment_number__icontains=search_term) | Q(order_shipment__manifest_number__icontains=search_term) |
                   Q(order__customer_id__icontains=search_term) | Q(order__customer_name__icontains=search_term),
                   order_shipment__user=user.id)
    else:
        results = shipment_objs
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    results = results.filter(order_shipment__user=user.id).values('order_shipment__shipment_number', 'order_shipment__manifest_number',
                            'order__customer_id', 'order__customer_name').\
                            distinct().annotate(ship_quantity=Sum('shipping_quantity')).order_by(order_data)
    for result in results[start_index:stop_index]:
        shipment_obj = shipment_objs.filter(order_shipment__shipment_number=result['order_shipment__shipment_number'],
                            order_shipment__manifest_number=result['order_shipment__manifest_number'], order_shipment__user=user.id).\
                            only('creation_date', 'order_id', 'id')
        shipment_creation_date = shipment_obj[0].creation_date
        manifest_date = get_local_date(user, shipment_creation_date)
        data_dict = OrderedDict((('Shipment Number', result['order_shipment__shipment_number']),
                                        ('Manifest Number', str(result['order_shipment__manifest_number'])),
                                        ('Customer ID', result['order__customer_id']), ('Customer Name', result['order__customer_name']),
                                        ('Total Quantity', result['ship_quantity'])
                                        ))
        pdf_obj = MasterDocs.objects.filter(master_id__in = shipment_obj.values_list('order_id', flat=True), master_type='OneAssistSignedCopies')
        if pdf_obj.exists():
            signed_copy = '<label class="icon-check" style="font-size: 22px;color: #1fa21f;"></label>'
        else:
            signed_copy = '<label class="icon-cloud-upload" style="font-size: 22px;cursor: pointer;"><input type = "file" name="files" id="file-upload" style="display:none" file-uploadd single ng-click= "vm.uploaded_file_data('+"'"+str(shipment_obj[0].id)+"'"+', '+"'"+'table'+"'"+');"/></label>'
        data_dict['Signed Invoice'] = signed_copy
        temp_data['aaData'].append(data_dict)

    temp_data['recordsTotal'] = results.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']


def create_temp_stock(sku_code, zone, quantity, stock_detail, user):
    if not quantity:
        quantity = 0
    inventory = StockDetail.objects.filter(sku__sku_code=sku_code, location__zone__zone=zone, sku__user=user)
    if inventory:
        inventory = inventory[0]
        for stock in stock_detail:
            if stock.id == inventory.id:
                setattr(stock, 'quantity', float(stock.quantity) + float(quantity))
                stock.save()
                break
        else:
            setattr(inventory, 'quantity', float(inventory.quantity) + float(quantity))
            inventory.save()
            stock_detail.append(inventory)
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
            stock_detail.append(stock)
    return stock_detail


def get_picklist_locations(data_dict, user):
    exclude_dict = {'location__lock_status__in': ['Outbound', 'Inbound and Outbound'],
                    'location__zone__zone__in': ['TEMP_ZONE', 'DAMAGED_ZONE']}
    back_order = get_misc_value('back_order', user.id)
    fifo_switch = get_misc_value('fifo_switch', user.id)

    data_dict = {}
    if fifo_switch == 'true':
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0,
                                                                           **data_dict). \
            order_by('receipt_date', 'location__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0, **data_dict). \
            order_by('receipt_date', 'location__pick_sequence')
        data_dict['location__zone__zone'] = 'TEMP_ZONE'
        # del exclude_dict['location__zone__zone']
        stock_detail3 = StockDetail.objects.exclude(**exclude_dict).filter(**data_dict).order_by('receipt_date',
                                                                                                 'location__pick_sequence')
        stock_detail = list(chain(stock_detail1, stock_detail2, stock_detail3))
    else:
        # del exclude_dict['location__zone__zone']
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


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def generate_picklist(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("generate_picklist: %s" % str(get_user_ip(request)))
    remarks = request.POST['ship_reference']
    filters = request.POST.get('filters', '')
    enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
    order_filter = {'status': 1, 'user': user.id, 'quantity__gt': 0}
    seller_order_filter = {'order__status': 1, 'order__user': user.id, 'order__quantity__gt': 0}
    if filters:
        filters = eval(filters)
        if filters['market_places']:
            order_filter['marketplace__in'] = (filters['market_places']).split(',')
            seller_order_filter['order__marketplace__in'] = order_filter['marketplace__in']
        if filters.get('customer_id', ''):
            customer_id = ''.join(re.findall('\d+', filters['customer_id']))
            order_filter['customer_id'] = customer_id
            seller_order_filter['order__customer_id'] = customer_id
    data = []
    stock_status = ''
    out_of_stock = []
    single_order = ''
    picklist_number = get_picklist_number(user)
    picklist_exclude_zones = get_exclude_zones(user)
    switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                   'fifo_switch': get_misc_value('fifo_switch', user.id),
                   'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                   'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id),
                   'allow_partial_picklist': get_misc_value('allow_partial_picklist', user.id)}
    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    if enable_damaged_stock == 'true':
        sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0, location__zone__zone__in=['DAMAGED_ZONE'])
    else:
        sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(location__zone__zone__in=picklist_exclude_zones).filter(sku__user=user.id, quantity__gt=0)
    all_seller_orders = SellerOrder.objects.prefetch_related('order__sku').filter(**seller_order_filter)
    if switch_vals['fifo_switch'] == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
            'receipt_date')
        #data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
            'location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    all_sku_stocks = stock_detail1 | stock_detail2
    log.info("Generate Picklist params " + str(request.POST.dict()))
    seller_stocks = SellerStock.objects.filter(seller__user=user.id).values('stock_id', 'seller_id')
    for key, value in request.POST.iteritems():
        if key in ('sortingTable_length', 'fifo-switch', 'ship_reference', 'remarks', 'filters', 'enable_damaged_stock'):
            continue

        order_data = OrderDetail.objects.filter(id=key, user=user.id, status=1)
        if not order_data.exists():
            continue
        order_data = order_data[0]
        seller_orders = all_seller_orders.filter(order_id=key, status=1).order_by('order__shipment_date')
        try:
            if seller_orders:
                for seller_order in seller_orders:
                    sku_stocks = all_sku_stocks
                    seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(seller_order.seller_id),
                                               seller_stocks)
                    if seller_stock_dict:
                        sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
                        sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
                    else:
                        sku_stocks = sku_stocks.filter(id=0)
                    stock_status, picklist_number = picklist_generation([seller_order], enable_damaged_stock,
                                                                        picklist_number, user, sku_combos, sku_stocks,
                                                                        switch_vals, status='open',
                                                                        remarks=remarks, is_seller_order=True)
            else:
                stock_status, picklist_number = picklist_generation([order_data], enable_damaged_stock, picklist_number,
                                                                    user, sku_combos, sku_stocks, switch_vals,
                                                                    status='open', remarks=remarks)
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Generate Picklist order view failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))
            stock_status = ['Internal Server Error']
        if stock_status:
            out_of_stock = out_of_stock + stock_status

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    check_picklist_number_created(user, picklist_number+1)

    show_image = 'false'
    use_imei = 'false'
    order_status = ''

    data, sku_total_quantities, courier_name = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']
        if order_status == 'open':
            order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
            order_count_len = len(filter(lambda x: len(str(x)) > 0, order_count))
            if order_count_len == 1:
                single_order = str(order_count[0])

    qc_items_qs = UserAttributes.objects.filter(user_id=user.id, attribute_model='dispatch_qc', status=1).values_list('attribute_name', flat=True)
    qc_items = list(qc_items_qs)

    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status,
                                    'order_status': order_status, 'single_order': single_order,
                                    'sku_total_quantities': sku_total_quantities, 'qc_items': qc_items}))


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def batch_generate_picklist(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("generate_picklist: %s" % str(get_user_ip(request)))
    remarks = request.POST.get('ship_reference', '')
    filters = request.POST.get('filters', '')
    enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
    order_filter = {'status': 1, 'user': user.id, 'quantity__gt': 0}
    if filters:
        filters = eval(filters)
        if filters['market_places']:
            order_filter['marketplace__in'] = (filters['market_places']).split(',')
        if filters.get('customer_id', ''):
            customer_id = ''.join(re.findall('\d+', filters['customer_id']))
            order_filter['customer_id'] = customer_id
        if not request.user.is_staff:
            perm_status_list, check_ord_status = get_view_order_statuses(request, user)
            if check_ord_status:
                order_filter['customerordersummary__status__in'] = perm_status_list

    data = []
    order_data = []
    stock_status = ''
    out_of_stock = []

    try:
        picklist_exclude_zones = get_exclude_zones(user)
        switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                       'fifo_switch': get_misc_value('fifo_switch', user.id),
                       'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                       'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id),
                       'allow_partial_picklist': get_misc_value('allow_partial_picklist', user.id)}
        picklist_number = get_picklist_number(user)
        sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
        if enable_damaged_stock  == 'true':
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(
            location__zone__zone__in=['DAMAGED_ZONE']).filter(sku__user=user.id, quantity__gt=0)
        else:
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
            location__zone__zone__in=picklist_exclude_zones).filter(sku__user=user.id, quantity__gt=0)
        all_orders = OrderDetail.objects.prefetch_related('sku').filter(**order_filter)
        if switch_vals['fifo_switch'] == 'true':
            stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
                'receipt_date')
            #data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
            stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
        else:
            stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
                'location_id__pick_sequence')
            stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by(
                'receipt_date')
        sku_stocks = stock_detail1 | stock_detail2

        for key, value in request.POST.iteritems():
            if key in PICKLIST_SKIP_LIST or key in ['filters', 'enable_damaged_stock']:
                continue

            key = key.split('<>')
            sku_code, marketplace_sku_code, title = key
            order_filter = {'sku__sku_code': sku_code, 'quantity__gt': 0, 'title': title, 'status': 1}

            if sku_code != marketplace_sku_code:
                order_filter['sku_code'] = marketplace_sku_code

            if request.POST.get('selected'):
                order_filter['marketplace__in'] = request.POST.get('selected').split(',')

            order_detail = all_orders.filter(**order_filter).order_by('shipment_date')

            stock_status, picklist_number = picklist_generation(order_detail, enable_damaged_stock, picklist_number, user,
                                                                sku_combos, sku_stocks, switch_vals, remarks=remarks)

            if stock_status:
                out_of_stock = out_of_stock + stock_status
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Generate Picklist SKU View failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse(json.dumps({'message': 'Picklist Generation Failed'}))

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    check_picklist_number_created(user, picklist_number + 1)
    order_status = ''
    data, sku_total_quantities, courier_name = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']

    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status, \
                                    'order_status': order_status, 'user': request.user.id, \
                                    'sku_total_quantities': sku_total_quantities}))


def get_sku_location_stock(wms_code, location, user_id, stock_skus, reserved_skus, stocks, reserved_instances):
    stock_left = 0
    if wms_code in stock_skus and not location == 'NO STOCK':
        if location in map(lambda d: d['location__location'],
                           filter(lambda person: person['sku__wms_code'] == wms_code, stocks)):
            stock_left = float(
                filter(lambda person: person['sku__wms_code'] == wms_code and person['location__location'] == location, \
                       stocks)[0]['quantity'])
        if wms_code in reserved_skus:
            if location in map(lambda d: d['stock__location__location'], \
                               filter(lambda person: person['stock__sku__wms_code'] == wms_code, reserved_instances)):
                st_res_quan = filter(lambda person: person['stock__sku__wms_code'] == wms_code and \
                                                    person['stock__location__location'] == location,
                                     reserved_instances)[0]['reserved']
                stock_left -= float(st_res_quan)
        if stock_left < 0:
            stock_left = 0
    return stock_left


def get_picklist_data(data_id, user_id):
    courier_name = ''
    sku_total_quantities = {}
    # sku_imeis_map = {}
    is_combo_picklist = False
    sku_sequence = 999
    # manufactured_date =''
    # st_order =''
    picklist_orders = Picklist.objects.filter(Q(order__sku__user=user_id) | Q(stock__sku__user=user_id),
                                              picklist_number=data_id)
    pick_stocks = StockDetail.objects.filter(sku__user=user_id)
    stocks = pick_stocks.filter(quantity__gt=0).values('sku__wms_code', 'location__location', 'batch_detail__batch_no').distinct().annotate(
        quantity=Sum('quantity'))
    reserved_instances = PicklistLocation.objects.filter(status=1, picklist__order__user=user_id).values(
        'stock__sku__wms_code', 'stock__location__location', 'stock__batch_detail__batch_no'). \
        distinct().annotate(reserved=Sum('reserved'))
    stock_skus = map(lambda d: d['sku__wms_code'], stocks)
    reserved_skus = map(lambda d: d['stock__sku__wms_code'], reserved_instances)
    data = []
    dispatched_imeis = OrderIMEIMapping.objects.filter(status=1, order__user=user_id, po_imei__isnull=False).only('po_imei_id').values_list(
        'po_imei_id', flat=True)
    dict_list = ['sku__sku_code', 'imei_number']
    imei_qs = POIMEIMapping.objects.filter(status=1, sku__user=user_id).exclude(id__in=dispatched_imeis).only(*dict_list).values_list(
        *dict_list).distinct().order_by('creation_date')
    sku_imeis_map = {}
    #for sku_code, imei_number in imei_qs:
    #    sku_imeis_map.setdefault(sku_code, []).append(imei_number)

    if not picklist_orders:
        return data, sku_total_quantities, courier_name
    if picklist_orders.filter(order_type='combo').exists():
        is_combo_picklist = True
    order_status = ''
    for orders in picklist_orders:
        if 'open' in orders.status:
            order_status = orders.status
    if not order_status:
        order_status = 'picked'
    use_imei = get_misc_value('use_imei', user_id)
    if order_status == "batch_open":
        batch_data = {}
        for order in picklist_orders:
            stock_id = ''
            wms_code = order.sku_code
            customer_name = ''
            remarks = ''
            load_unit_handle = ''
            category = ''
            customer_address = ''
            original_order_id = ''
            order_id = ''
            order_code = ''
            mrp = 0
            batch_no = ''
            batch_ref = ''
            manufactured_date =''
            expiry_date = ''
            courier_name = ''
            if order.stock:
                stock_id = pick_stocks.get(id=order.stock_id)
            if order.order:
                sku_code = order.order.sku_code
                sku_sequence = order.order.sku.sequence
                title = order.order.title
                invoice = order.order.invoice_amount
                customer_name = order.order.customer_name
                marketplace = order.order.marketplace
                remarks = order.order.remarks
                order_id = str(order.order.order_id)
                order_code = str(order.order.order_code)
                original_order_id = order.order.original_order_id
                load_unit_handle = order.order.sku.load_unit_handle
                category = order.order.sku.sku_category
                customer_address = order.order.address
                if order.order.customer_id:
                    customer_obj = CustomerMaster.objects.filter(customer_id=order.order.customer_id,
                                                                 user=user_id)
                    if customer_obj:
                        customer_address = customer_obj[0].address
                customer_order_summary = order.order.customerordersummary_set.filter()
                if customer_order_summary:
                    courier_name = customer_order_summary[0].courier_name
                    mrp = customer_order_summary[0].mrp
            else:
                st_order = STOrder.objects.filter(picklist_id=order.id)
                sku_code = ''
                title, invoice, load_unit_handle, category = '', '', '', ''
                if st_order.exists():
                    title = st_order[0].stock_transfer.sku.sku_desc
                    invoice = st_order[0].stock_transfer.invoice_amount
                    load_unit_handle = st_order[0].stock_transfer.sku.load_unit_handle
                    category = st_order[0].stock_transfer.sku.sku_category
                    st_order_picklist = st_order[0].picklist

                marketplace = ""
            pallet_code = ''
            pallet_detail = ''
            if stock_id and stock_id.pallet_detail:
                pallet_code = stock_id.pallet_detail.pallet_code
                pallet_detail = stock_id.pallet_detail

            zone = 'NO STOCK'
            st_id = 0
            sequence = 0
            location = 'NO STOCK'
            image = ''
            sku_brand = ''
            if order.order and order.order.sku:
                image = order.order.sku.image_url
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = stock_id.sku.image_url
                wms_code = stock_id.sku.wms_code
                sku_brand = stock_id.sku.sku_brand
                sku_sequence = stock_id.sku.sequence
                load_unit_handle = stock_id.sku.load_unit_handle
                category = stock_id.sku.sku_category
                if stock_id.batch_detail:
                    mrp = stock_id.batch_detail.mrp
                    batch_no = stock_id.batch_detail.batch_no
                    batch_ref = stock_id.batch_detail.batch_ref
                    try:
                        manufactured_date = datetime.datetime.strftime(stock_id.batch_detail.manufactured_date, "%d/%m/%Y")
                    except:
                        manufactured_date =''
                    try:
                        expiry_date = datetime.datetime.strftime(stock_id.batch_detail.expiry_date, "%d/%m/%Y")
                    except:
                        expiry_date =''
            uom_dict = get_uom_with_sku_code(User.objects.get(id=user_id), wms_code, uom_type='purchase')
            conversion_value = uom_dict.get('sku_conversion', 1)
            reserved_quantity = order.reserved_quantity/conversion_value
            if use_imei == 'true':
                sku_filtered_imei_number = imei_qs.filter(sku__wms_code=wms_code).values_list(*dict_list).order_by('creation_date')
                for sku_code, imei_number in sku_filtered_imei_number:
                    sku_imeis_map.setdefault(sku_code, []).append(imei_number)
            match_condition = (location, batch_no, manufactured_date,pallet_detail, wms_code, sku_code, title)
            if match_condition not in batch_data:
                if order.reserved_quantity == 0:
                    continue
                stock_left = get_sku_location_stock(wms_code, location, user_id, stock_skus, reserved_skus, stocks,
                                                    reserved_instances)
                last_picked_locs = ''
                if location == 'NO STOCK':
                    last_picked = pick_stocks.exclude(location__zone__zone='DAMAGED_ZONE').filter(
                        sku__wms_code=wms_code). \
                                      order_by('-updation_date').values_list('location__location',
                                                                             flat=True).distinct()[:2]
                    last_picked_locs = ','.join(last_picked)
                if not original_order_id:
                    original_order_id = str(order_id) + str(order_code)
                if not invoice :
                    invoice = 0
                batch_data[match_condition] = {'wms_code': wms_code, 'zone': zone, 'sequence': sequence,
                                               'location': location, 'reserved_quantity': reserved_quantity,
                                               'picklist_number': data_id, 'stock_id': st_id, 'sku_sequence': sku_sequence,
                                               'picked_quantity': reserved_quantity, 'id': order.id,
                                               'invoice_amount': invoice, 'price': invoice * reserved_quantity,
                                               'image': image, 'order_id': str(order.order_id), 'status': order.status,
                                               'pallet_code': pallet_code, 'sku_code': sku_code, 'title': title,
                                               'stock_left': stock_left, 'last_picked_locs': last_picked_locs,
                                               'customer_name': customer_name, 'customer_address': customer_address,
                                               'marketplace': marketplace,
                                               'manufactured_date':manufactured_date,
                                               'expiry_date': expiry_date,
                                               'order_no': order_id, 'remarks': remarks,
                                               'load_unit_handle': load_unit_handle, 'category': category,
                                               'original_order_id': original_order_id, 'mrp':mrp,
                                               'batchno':batch_no, "batch_ref":batch_ref, 'is_combo_picklist': is_combo_picklist, 'sku_imeis_map': sku_imeis_map,
                                               'sku_brand': sku_brand,
                                               'conversion_value': conversion_value}
            else:
                batch_data[match_condition]['reserved_quantity'] += reserved_quantity
                batch_data[match_condition]['picked_quantity'] += reserved_quantity
                batch_data[match_condition]['invoice_amount'] += invoice
                if batch_data[match_condition]['marketplace'].find(marketplace) == -1:
                    batch_data[match_condition]['marketplace'] += "," + marketplace
            if wms_code in sku_total_quantities.keys():
                sku_total_quantities[wms_code] += float(order.reserved_quantity)
            else:
                sku_total_quantities[wms_code] = float(order.reserved_quantity)
        data = batch_data.values()
        if get_misc_value('picklist_sort_by_sku_sequence', user_id) == 'false':
            if get_misc_value('picklist_sort_by', user_id) == 'true':
                data = sorted(data, key=itemgetter('order_id'))
            else:
                data = sorted(data, key=itemgetter('sequence'))
        else:
            data = sorted(data, key=itemgetter('sku_sequence'))
        return data, sku_total_quantities, courier_name

    elif order_status == "open":
        courier_name = ''
        for order in picklist_orders:
            stock_id = ''
            customer_name = ''
            remarks = ''
            #load_unit_handle = ''
            #category = ''
            #customer_address = ''
            original_order_id = ''
            order_code = ''
            #order_id = ''
            mrp = ''
            batch_no = ''
            batch_ref = ''
            manufactured_date = ''
            expiry_date = ''
            parent_sku_code = ''
            if order.order_type == 'combo' and order.order:
                parent_sku_code = order.order.sku.sku_code
            if order.order:
                wms_code = order.order.sku.wms_code
                sku_sequence = order.order.sku.sequence
                if order.order_type == 'combo' and order.sku_code:
                    wms_code = order.sku_code
                invoice_amount = order.order.invoice_amount
                order_id = str(order.order.order_id)
                order_code = str(order.order.order_code)
                original_order_id = order.order.original_order_id
                sku_code = order.order.sku_code
                title = order.order.title
                customer_name = order.order.customer_name
                customer_address = order.order.address
                if order.order.customer_id:
                    customer_obj = CustomerMaster.objects.filter(customer_id=order.order.customer_id,
                                                                 user=user_id)
                    if customer_obj:
                        customer_address = customer_obj[0].address
                customer_order_summary = order.order.customerordersummary_set.filter()
                if customer_order_summary:
                    customer_address = customer_order_summary[0].consignee
                    courier_name = customer_order_summary[0].courier_name
                marketplace = order.order.marketplace
                remarks = order.order.remarks
                load_unit_handle = order.order.sku.load_unit_handle
                category = order.order.sku.sku_category
            else:
                wms_code = order.stock.sku.wms_code
                invoice_amount = 0
                order_id = ''
                sku_code = order.stock.sku.sku_code
                sku_sequence = order.order.sku.sequence
                title = order.stock.sku.sku_desc
                marketplace = ""
                load_unit_handle = order.stock.sku.load_unit_handle
                category = order.stock.sku.sku_category
                customer_address = ''
                courier_name = ''
            if order.stock_id:
                stock_id = pick_stocks.get(id=order.stock_id)
            if order.reserved_quantity == 0:
                continue
            pallet_code = ''
            if stock_id and stock_id.pallet_detail:
                pallet_code = stock_id.pallet_detail.pallet_code

            zone = 'NO STOCK'
            st_id = 0
            sequence = 0
            location = 'NO STOCK'
            image = ''
            sku_brand = ''
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = stock_id.sku.image_url
                wms_code = stock_id.sku.wms_code
                sku_brand = stock_id.sku.sku_brand
                sku_sequence = stock_id.sku.sequence
                if stock_id.batch_detail:
                    mrp = stock_id.batch_detail.mrp
                    batch_no = stock_id.batch_detail.batch_no
                    batch_ref = stock_id.batch_detail.batch_ref
                    try:
                        manufactured_date = datetime.datetime.strftime(stock_id.batch_detail.manufactured_date, "%d/%m/%Y")
                    except:
                        manufactured_date = ''
                    try:
                        expiry_date = datetime.datetime.strftime(stock_id.batch_detail.expiry_date, "%d/%m/%Y")
                    except:
                        expiry_date = ''
            stock_left = get_sku_location_stock(wms_code, location, user_id, stock_skus, reserved_skus, stocks,
                                                reserved_instances)
            last_picked_locs = ''
            if location == 'NO STOCK':
                last_picked = pick_stocks.exclude(location__zone__zone='DAMAGED_ZONE').filter(sku__wms_code=wms_code). \
                                  order_by('-updation_date').values_list('location__location',
                                                                         flat=True).distinct()[:2]
                last_picked_locs = ','.join(last_picked)
            if use_imei == 'true':
                sku_filtered_imei_number = imei_qs.filter(sku__wms_code=wms_code).values_list(*dict_list).order_by('creation_date')
                for sku_code, imei_number in sku_filtered_imei_number:
                    sku_imeis_map.setdefault(sku_code, []).append(imei_number)

            if not original_order_id:
                original_order_id = str(order_id) + str(order_code)

            data.append(
                {'wms_code': wms_code, 'zone': zone, 'location': location, 'reserved_quantity': order.reserved_quantity,
                 'picklist_number': data_id, 'stock_id': st_id, 'order_id': str(order.order_id), 'sku_sequence': sku_sequence,
                 'picked_quantity': order.reserved_quantity, 'id': order.id, 'sequence': sequence,
                 'invoice_amount': invoice_amount, 'price': invoice_amount * order.reserved_quantity, 'image': image,
                 'status': order.status, 'order_no': order_id, 'pallet_code': pallet_code, 'sku_code': sku_code,
                 'title': title, 'stock_left': stock_left, 'last_picked_locs': last_picked_locs,
                 'customer_name': customer_name, 'marketplace': marketplace, 'remarks': remarks,
                 'load_unit_handle': load_unit_handle,
                 'manufactured_date':manufactured_date,
                 'expiry_date': expiry_date,
                 'category': category, 'customer_address': customer_address,
                 'original_order_id': original_order_id, 'mrp':mrp, 'batchno':batch_no,"batch_ref":batch_ref,
                 'is_combo_picklist': is_combo_picklist, 'parent_sku_code': parent_sku_code,
                 'sku_imeis_map': sku_imeis_map, 'sku_brand': sku_brand})

            if wms_code in sku_total_quantities.keys():
                sku_total_quantities[wms_code] += float(order.reserved_quantity)
            else:
                sku_total_quantities[wms_code] = float(order.reserved_quantity)
        if get_misc_value('picklist_sort_by_sku_sequence', user_id) == 'false':
            if get_misc_value('picklist_sort_by', user_id) == 'true':
                data = sorted(data, key=itemgetter('order_id'))
            else:
                data = sorted(data, key=itemgetter('sequence'))
        else:
            data = sorted(data, key=itemgetter('sku_sequence'))
        return data, sku_total_quantities, courier_name
    else:
        courier_name = ''
        for order in picklist_orders:
            stock_id = ''
            wms_code = order.order.sku.wms_code
            sku_brand = order.order.sku.sku_brand
            marketplace = order.order.marketplace
            remarks = order.order.remarks
            order_id = ''
            order_code = ''
            original_order_id = ''
            mrp = ''
            batch_no = ''
            batch_ref = ''
            expiry_date = ''
            manufactured_date = ''
            parent_sku_code = ''
            if order.order_type == 'combo' and order.order:
                parent_sku_code = order.order.sku.sku_code
            if order.stock_id:
                stock_id = pick_stocks.get(id=order.stock_id)

            zone = 'NO STOCK'
            st_id = 0
            sequence = 0
            location = 'NO STOCK'
            pallet_code = ''
            image = ''
            load_unit_handle = ''
            category = ''
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = stock_id.sku.image_url
                load_unit_handle = stock_id.sku.load_unit_handle
                category = stock_id.sku.sku_category
                if stock_id.batch_detail:
                    mrp = stock_id.batch_detail.mrp
                    batch_no = stock_id.batch_detail.batch_no
                    batch_ref = stock_id.batch_detail.batch_ref
                    try:
                        manufactured_date = datetime.datetime.strftime(stock_id.batch_detail.manufactured_date, "%d/%m/%Y")
                    except:
                        manufactured_date =''
                    try:
                        expiry_date = datetime.datetime.strftime(stock_id.batch_detail.expiry_date, "%d/%m/%Y")
                    except:
                        expiry_date =''
            customer_name = ''
            if order.order:
                customer_name = order.order.customer_name
                order_id = str(order.order.order_id)
                order_code = str(order.order.order_code)
                original_order_id = str(order.order.original_order_id)
                customer_order_summary = order.order.customerordersummary_set.filter()
                if customer_order_summary:
                    courier_name = customer_order_summary[0].courier_name
            pallet_code = ""
            if order.reserved_quantity == 0:
                continue
            stock_left = get_sku_location_stock(wms_code, location, user_id, stock_skus, reserved_skus, stocks,
                                                reserved_instances)
            last_picked_locs = ''
            if location == 'NO STOCK':
                last_picked = pick_stocks.exclude(location__zone__zone='DAMAGED_ZONE').filter(sku__wms_code=wms_code). \
                                  order_by('-updation_date').values_list('location__location',
                                                                         flat=True).distinct()[:2]
                last_picked_locs = ','.join(last_picked)
            if use_imei == 'true':
                sku_filtered_imei_number = imei_qs.filter(sku__wms_code=wms_code).values_list(*dict_list).order_by('creation_date')
                for sku_code, imei_number in sku_filtered_imei_number:
                    sku_imeis_map.setdefault(sku_code, []).append(imei_number)

            if not original_order_id:
                original_order_id = str(order_id) + str(order_code)

            data.append(
                {'wms_code': wms_code, 'zone': zone, 'location': location, 'reserved_quantity': order.reserved_quantity,
                 'picklist_number': data_id, 'order_id': order_id, 'stock_id': st_id,
                 'picked_quantity': order.reserved_quantity, 'id': order.id, 'sequence': sequence,
                 'invoice_amount': order.order.invoice_amount,
                 'price': order.order.invoice_amount * order.reserved_quantity,
                 'image': image, 'status': order.status, 'pallet_code': pallet_code, 'sku_code': order.order.sku_code,
                 'title': order.order.title, 'stock_left': stock_left, 'last_picked_locs': last_picked_locs,
                 'customer_name': customer_name, 'remarks': remarks, 'load_unit_handle': load_unit_handle,
                 'category': category,
                 'manufactured_date':manufactured_date, 'expiry_date': expiry_date,
                 'marketplace': marketplace, 'original_order_id' : original_order_id,
                 'mrp':mrp, 'batchno':batch_no,"batch_ref":batch_ref, 'is_combo_picklist': is_combo_picklist,
                 'parent_sku_code':parent_sku_code, 'sku_imeis_map': sku_imeis_map, 'sku_brand': sku_brand})

            if wms_code in sku_total_quantities.keys():
                sku_total_quantities[wms_code] += float(order.reserved_quantity)
            else:
                sku_total_quantities[wms_code] = float(order.reserved_quantity)
        if get_misc_value('picklist_sort_by_sku_sequence', user_id) == 'false':
            data = sorted(data, key=itemgetter('sequence'))
        return data, sku_total_quantities, courier_name


def confirm_no_stock(picklist, request, user, picks_all, picklists_send_mail, merge_flag, user_profile,
                     seller_pick_number, val={}, p_quantity=0):
    if float(picklist.reserved_quantity) - p_quantity >= 0:
        picklist.reserved_quantity = float(picklist.reserved_quantity) - p_quantity
        picklist.picked_quantity = float(picklist.picked_quantity) + p_quantity
    else:
        picklist.reserved_quantity = 0
        picklist.picked_quantity = p_quantity
    pi_status = 'picked'
    if 'batch_open' in picklist.status:
        pi_status = 'batch_picked'

    if picklist.order:
        check_and_update_order(picklist.order.user, picklist.order.original_order_id)
    if 'labels' in val.keys() and val['labels'] and picklist.order:
        update_order_labels(picklist, val)
    if float(picklist.reserved_quantity) <= 0:
        picklist.status = pi_status
        if picklist.order and picklist.order.order_type == 'Transit':
            serial_order_mapping(picklist, user)
    picklist.save()
    if not seller_pick_number:
        seller_pick_number = get_seller_pick_id(picklist, user)
    if user_profile.user_type == 'marketplace_user' and picklist.order:
        create_seller_order_summary(picklist, p_quantity, seller_pick_number, picks_all)
    else:
        create_order_summary(picklist, p_quantity, seller_pick_number, picks_all)
    if picklist.picked_quantity > 0 and picklist.order:
        if merge_flag:
            quantity = picklist.picked_quantity
        else:
            quantity = p_quantity
        if picklist.order.order_id in picklists_send_mail.keys():
            if picklist.order.sku.sku_code in picklists_send_mail[picklist.order.order_id].keys():
                qty = float(picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code])
                picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code] = qty + float(quantity)
            else:
                picklists_send_mail[picklist.order.order_id].update({picklist.order.sku.sku_code: float(quantity)})

        else:
            picklists_send_mail.update({picklist.order.order_id: {picklist.order.sku.sku_code: float(quantity)}})
            # picklists_send_mail.append({'order_id': picklist.order.order_id})
            # picklists_send_mail.append(data_count)
            # picklists_send_mail = [{'order_id': str(picklist.order.order_id)}, data_count]
    return seller_pick_number


def validate_location_stock(val, all_locations, all_skus, user, picklist):
    status = []
    error_string = ''
    wms_check = all_skus.filter(wms_code=val['wms_code'], user=user.id)
    loc_check = all_locations.filter(location=val['location'], zone__user=user.id)
    if not loc_check:
        status.append("Invalid Location %s" % val['location'])
    pic_check_data = {'sku__wms_code': val['wms_code'], 'location__location': val['location'], 'sku__user': user.id,
                      'quantity__gt': 0}
    if 'pallet' in val and val['pallet']:
        pic_check_data['pallet_detail__pallet_code'] = val['pallet']
    if picklist.sellerorderdetail_set.filter(seller_order__isnull=False).exists():
        pic_check_data['sellerstock__seller_id'] = picklist.sellerorderdetail_set.\
                                                    filter(seller_order__isnull=False)[0].seller_order.seller_id
    elif picklist.storder_set.filter():
        stock_transfer = picklist.storder_set.filter()[0].stock_transfer
        if stock_transfer and stock_transfer.st_seller:
            pic_check_data['sellerstock__seller_id'] = stock_transfer.st_seller
    '''if val['location'] != val['orig_loc'] and val.get('batchno', ''):
        pic_check_data['batch_detail__batch_no'] = val['batchno']
    else:
        if picklist.stock and picklist.stock.batch_detail_id:
            pic_check_data['batch_detail__mrp'] = picklist.stock.batch_detail.mrp
            pic_check_data['batch_detail__batch_no'] = picklist.stock.batch_detail.batch_no'''
    mrp = 0
    if val.get('mrp', ''):
        try:
            mrp = float(val['mrp'])
        except:
            pass
    if mrp:
        pic_check_data['batch_detail__mrp'] = mrp
    if val.get('batchno', ''):
        pic_check_data['batch_detail__batch_no'] = val['batchno']
    if val.get('manufactured_date', '') and not user.username in MILKBASKET_USERS:
        try:
            pic_check_data['batch_detail__manufactured_date__regex'] = datetime.datetime.strptime(val['manufactured_date'], '%d/%m/%Y').strftime('%Y-%m-%d')
        except:
            pass
    pic_check = StockDetail.objects.filter(**pic_check_data)
    expiry_batches_picklist = get_misc_value('block_expired_batches_picklist', user.id)
    if not pic_check:
        if val.get('batchno', ''):
            status.append("Insufficient Stock in given location with batch number")
        else:
            status.append("Insufficient Stock in given location")
    elif pic_check[0].batch_detail and pic_check[0].batch_detail.expiry_date and expiry_batches_picklist == 'true':
        present_date = datetime.datetime.now().date()
        if pic_check[0].batch_detail.expiry_date <= present_date:
            status.append("Expiry batch number not Allowed")
    location = all_locations.filter(location=val['location'], zone__user=user.id)
    if not location:
        if error_string:
            error_string += ', %s' % val['order_id']
        else:
            error_string += "Zone, location match doesn't exists"
        status.append(error_string)
    return pic_check_data, ', '.join(status)


def insert_order_serial(picklist, val, order='', shipped_orders_dict={}):
    if ',' in val['imei']:
        imei_nos = list(set(val['imei'].split(',')))
    else:
        imei_nos = list(set(val['imei'].split('\r\n')))
    user_id = None
    for imei in imei_nos:
        imei_filter = {}
        if order:
            order_id = order.id
            sku_id = order.sku_id
        else:
            order_id = picklist.order.id
            order = picklist.order
            sku_id = picklist.order.sku_id
        if order:
            user_id = order.user
        po_mapping, status, imei_data = check_get_imei_details(imei, val['wms_code'], user_id,
                                                               check_type='order_mapping', order=order)
        # po_mapping = POIMEIMapping.objects.filter(purchase_order__open_po__sku__sku_code=val['wms_code'], imei_number=imei, status=1,
        #                                          purchase_order__open_po__sku__user=user_id)
        imei_mapping = None
        all_seller_pos = SellerPO.objects.filter(seller__user=user_id)
        all_seller_orders = SellerOrder.objects.filter(seller__user=user_id)
        sor_id = ''
        seller_id = ''
        if imei and po_mapping:
            order_mapping = {'order_id': order_id, 'po_imei_id': po_mapping[0].id, 'imei_number': '',
                             'sku_id': sku_id}
            if po_mapping[0].seller_id:
                seller_id = po_mapping[0].seller_id
                seller_order_obj = all_seller_orders.filter(order_id=order_id, seller_id=seller_id)
                if seller_order_obj:
                    sor_id = seller_order_obj[0].sor_id
            order_mapping_ins = OrderIMEIMapping.objects.filter(po_imei_id=po_mapping[0].id, order_id=order_id)
            if order_mapping_ins:
                imei_mapping = order_mapping_ins[0]
                imei_mapping.sor_id = sor_id
                imei_mapping.status = 1
                imei_mapping.save()
                po_imei = order_mapping_ins[0].po_imei
            else:
                order_mapping['sor_id'] = sor_id
                if seller_id:
                    order_mapping['seller_id'] = seller_id
                imei_mapping = OrderIMEIMapping(**order_mapping)
                imei_mapping.save()
                po_imei = po_mapping[0]
                log.info('%s imei code is mapped for %s and for id %s' % (str(imei), val['wms_code'], str(order_id)))
            if po_imei:
                po_imei.status = 0
                po_imei.save()
        elif imei and not po_mapping:
            order_mapping = {'order_id': order_id, 'po_imei_id': None, 'imei_number': imei, 'sor_id': sor_id}
            if seller_id:
                order_mapping['seller_id'] = seller_id
            imei_mapping = OrderIMEIMapping(**order_mapping)
            imei_mapping.save()
            log.info('%s imei code is mapped for %s and for id %s' % (str(imei), val['wms_code'], str(order_id)))
        if imei_mapping:
            if shipped_orders_dict.has_key(int(order_id)):
                shipped_orders_dict[int(order_id)]['imeis'].append(imei_mapping)
            else:
                shipped_orders_dict[int(order_id)] = {}
                shipped_orders_dict[int(order_id)]['imeis'] = [imei_mapping]
        ReturnsIMEIMapping.objects.filter(order_return__sku__user=user_id, order_imei__po_imei__imei_number=imei,
                                          imei_status=1).update(imei_status=0)
    return shipped_orders_dict


def insert_st_order_serial(picklist, val, order='', shipped_orders_dict={},passed_serial_number = {}):
    if passed_serial_number :
        imei_nos = passed_serial_number.get(val['wms_code'],[])
    else:
        imei_nos = val['imei']
        if not isinstance(val['imei'], list) :
            if ',' in val['imei']:
                imei_nos = list(set(val['imei'].split(',')))
            else:
                imei_nos = list(set(val['imei'].split('\r\n')))
    user_id = None
    for imei in imei_nos:
        imei_filter = {}
        if order:
            order_id = order.id
            sku_id = order.stock_transfer.sku.id
        else:
            order_id = picklist.order.id
            order = picklist.order
            sku_id = picklist.order.sku_id
        if order:
            user_id = order.stock_transfer.sku.user
        po_mapping, status, imei_data = check_get_imei_details(imei, val['wms_code'], user_id,
                                                               check_type='order_mapping', order=order)
        # po_mapping = POIMEIMapping.objects.filter(purchase_order__open_po__sku__sku_code=val['wms_code'], imei_number=imei, status=1,
        #                                          purchase_order__open_po__sku__user=user_id)
        imei_mapping = None
        all_seller_pos = SellerPO.objects.filter(seller__user=user_id)
        all_seller_orders = SellerOrder.objects.filter(seller__user=user_id)
        sor_id = ''
        seller_id = ''
        if imei and po_mapping:
            order_mapping = {'po_imei_id': po_mapping[0].id, 'imei_number': '',
                             'sku_id': sku_id, 'stock_transfer': order.stock_transfer}
            if po_mapping[0].seller_id:
                seller_id = po_mapping[0].seller_id
                seller_order_obj = all_seller_orders.filter(order_id=order_id, seller_id=seller_id)
                if seller_order_obj:
                    sor_id = seller_order_obj[0].sor_id
            order_mapping_ins = OrderIMEIMapping.objects.filter(po_imei_id=po_mapping[0].id, order_id=order_id)
            if order_mapping_ins:
                imei_mapping = order_mapping_ins[0]
                imei_mapping.sor_id = sor_id
                imei_mapping.status = 1
                imei_mapping.save()
                po_imei = order_mapping_ins[0].po_imei
            else:
                order_mapping['sor_id'] = sor_id
                order_mapping['stock_transfer'] = order.stock_transfer
                if seller_id:
                    order_mapping['seller_id'] = seller_id
                imei_mapping = OrderIMEIMapping(**order_mapping)
                imei_mapping.save()
                po_imei = po_mapping[0]
                log.info('%s imei code is mapped for %s and for id %s' % (str(imei), val['wms_code'], str(order_id)))
            if po_imei:
                po_imei.status = 0
                po_imei.save()
        elif imei and not po_mapping:
            order_mapping = {'order_id': order_id.stock_transfer, 'po_imei_id': None, 'imei_number': imei,
            'sor_id': sor_id, 'stock_transfer': order.stock_transfer}
            if seller_id:
                order_mapping['seller_id'] = seller_id
            imei_mapping = OrderIMEIMapping(**order_mapping)
            imei_mapping.save()
            log.info('%s imei code is mapped for %s and for id %s' % (str(imei), val['wms_code'], str(order_id)))
        if imei_mapping:
            if shipped_orders_dict.has_key(int(order_id)):
                shipped_orders_dict[int(order_id)]['imeis'].append(imei_mapping)
            else:
                shipped_orders_dict[int(order_id)] = {}
                shipped_orders_dict[int(order_id)]['imeis'] = [imei_mapping]
        ReturnsIMEIMapping.objects.filter(order_return__sku__user=user_id, order_imei__po_imei__imei_number=imei,
                                          imei_status=1).update(imei_status=0)
    return shipped_orders_dict


def update_picklist_pallet(stock, picking_count1):
    pallet = stock.pallet_detail
    if float(pallet.quantity) - picking_count1 >= 0:
        pallet.quantity -= picking_count1
    if pallet.quantity == 0:
        stock.pallet_detail_id = None
        pallet.status = 0
        stock.location.pallet_filled -= 1
        if stock.location.pallet_filled < 0:
            stock.location.pallet_filled = 0
        stock.location.save()
        pallet_mapping = PalletMapping.objects.filter(pallet_detail_id=pallet.id)
        if pallet_mapping:
            pallet_mapping[0].status = 1
            pallet_mapping[0].save()
    pallet.save()


def send_picklist_mail(picklists, request, user, pdf_file, misc_detail, data_qt="", from_pos=False):
    picklist_order_ids_list = []
    reciever = []

    headers = ['Product Details', 'Ordered Quantity', 'Total']
    items = []
    for picklist in picklists:
        if {picklist.order.order_id: picklist.order.sku.sku_code} in picklist_order_ids_list:
            continue
        if data_qt:
            qty = data_qt.get(picklist.order.sku.sku_code, 0)
            if not qty:
                continue
        else:
            qty = picklist.picked_quantity
        picklist_order_ids_list.append({picklist.order.order_id: picklist.order.sku.sku_code})
        unit_price = float(picklist.order.invoice_amount) / float(picklist.order.quantity)
        items.append([picklist.order.sku.sku_desc, qty, float(qty) * unit_price])
    picklist = picklists[0]

    user_data = UserProfile.objects.get(user_id=user.id);
    client_name = ''
    if picklist.order:
        client_name = picklist.order.customerordersummary_set.values_list('client_name', flat=True)[0]
    data_dict = {'customer_name': picklist.order.customer_name, 'order_id': picklist.order.order_id,
                 'address': picklist.order.address, 'phone_number': picklist.order.telephone, 'all_items': items,
                 'headers': headers, 'query_contact': user_data.phone_number,
                 'company_name': user_data.company.company_name, 'client_name': client_name}

    t = loader.get_template('templates/dispatch_mail.html')
    rendered = t.render(data_dict)

    if misc_detail:
        email = picklist.order.email_id
        reciever.append(email)
    internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='Internal Emails')
    misc_internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='internal_mail', misc_value='true')
    if misc_internal_mail and internal_mail:
        internal_mail = internal_mail[0].misc_value.split(",")
        if 'false' in internal_mail:
            internal_mail.remove('false')
        reciever.extend(internal_mail)

    if reciever:
        try:
            tmp_invoice_date = get_local_date(user, picklist.updation_date, send_date='true')
            tmp_invoice_date = str(tmp_invoice_date.strftime('%m%y'))
            tmp_order_id = 'TI/' + tmp_invoice_date + '/' + picklist.order.original_order_id if from_pos else\
                           'TI/' + tmp_invoice_date + '/' + str(picklist.order.order_id)
            send_mail_attachment(reciever, '%s : Invoice No.%s' % (
            user_data.company.company_name, tmp_order_id), rendered, files=[pdf_file])
        except:
            log.info('mail issue')


def get_picklist_batch(picklist, value, all_picklists):
    title = value[0]['title']
    if '\r' in title:
        title = str(title).replace('\r', '')
    if picklist.order and picklist.stock:
        picklist_batch = all_picklists.filter(stock__location__location=value[0]['orig_loc'],
                                              stock__sku__wms_code=value[0]['wms_code'],
                                              status__icontains='open', order__title=title)
    elif not picklist.stock:
        picklist_batch = all_picklists.filter(order__sku__sku_code=value[0]['wms_code'], order__title=title,
                                              stock__isnull=True,
                                              picklist_number=picklist.picklist_number)
        if not picklist_batch:
            picklist_batch = all_picklists.filter(sku_code=value[0]['wms_code'], order__title=title, stock__isnull=True,
                                                  picklist_number=picklist.picklist_number)
    else:
        picklist_batch_main = all_picklists.filter(Q(stock__sku__wms_code=value[0]['wms_code']) | Q(order_type="combo",
                                                                                               sku_code=value[0][
                                                                                                   'wms_code']),
                                              stock__location__location=value[0]['orig_loc'],
                                              status__icontains='open')
        picklist_batch1 = picklist_batch_main.filter(stock__batch_detail__batch_no=value[0]['orig_batchno'])
        picklist_batch2 = picklist_batch_main.filter(stock__batch_detail__isnull=True)
        picklist_batch = picklist_batch1 | picklist_batch2
    return picklist_batch


def check_and_send_mail(request, user, picklist, picks_all, picklists_send_mail, from_pos=False):
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='dispatch', misc_value='true')

    # order_ids = list(set(map(lambda d: d['order_id'], picklists_send_mail[0])))
    order_ids = picklists_send_mail.keys()
    if not misc_detail:
        return
    elif misc_detail[0].misc_value != 'true':
        return
    if get_misc_value('customer_dc', user.id) == 'true':
        return
    if picklist.order:
        for order_id in order_ids:
            all_picked_items = picks_all.filter(order__order_id=order_id, picked_quantity__gt=0)
            order_ids_list = all_picked_items.values_list('order_id', flat=True)
            if order_ids_list:
                order_ids = [str(int(i)) for i in order_ids_list]
                order_ids = ','.join(order_ids)
            nv_data = get_invoice_data(order_ids, user, picklists_send_mail[order_id], from_pos=from_pos)
            nv_data = modify_invoice_data(nv_data, user)
            ord_ids = order_ids.split(",")
            nv_data = add_consignee_data(nv_data, ord_ids, user)
            nv_data.update({'user': user})
            if nv_data['detailed_invoice']:
                t = loader.get_template('../miebach_admin/templates/toggle/detail_generate_invoice.html')
                rendered = t.render(nv_data)
            else:
                # t = loader.get_template('../miebach_admin/templates/toggle/generate_invoice.html')
                nv_data["customer_invoice"] = True
                rendered = build_invoice(nv_data, user, True)
            # rendered = t.render(nv_data)
            file_name = str(user.id) + '_' + 'dispatch_invoice.html'
            pdf_file = '%s_%s.pdf' % (str(user.id), "dispatch_invoice")
            file_ = open(file_name, "w+b")
            rendered = rendered.encode('ascii', 'ignore')
            file_.write(rendered)
            file_.close()
            os.system("./phantom/bin/phantomjs ./phantom/examples/rasterize.js ./%s ./%s A4" % (file_name, pdf_file))

            send_picklist_mail(all_picked_items, request, user, pdf_file, misc_detail,\
                               picklists_send_mail[order_id], from_pos=from_pos)
            if picklist.picked_quantity > 0 and picklist.order and misc_detail:
                if picklist.order.telephone:
                    order_dispatch_message(picklist.order, user, picklists_send_mail[order_id])
                else:
                    log.info("No telephone no for this order")


def create_seller_order_summary(picklist, picked_count, pick_number, picks_all, stocks=[]):
    # seller_orders = SellerOrder.objects.filter(order_id=picklist.order_id, order__user=picklist.order.user, status=1)
    seller_order_details = SellerOrderDetail.objects.filter(picklist_id=picklist.id,
                                                            picklist__order__user=picklist.order.user)
    financial_year = get_financial_year(datetime.datetime.now())
    for seller_detail in seller_order_details:
        insert_quan = 0
        if not picked_count:
            break
        if seller_detail.reserved > picked_count:
            insert_quan = picked_count
            picked_count = 0
        elif seller_detail.reserved <= picked_count:
            insert_quan = seller_detail.reserved
            picked_count = picked_count - int(seller_detail.reserved)
        seller_detail.reserved = seller_detail.reserved - insert_quan
        if seller_detail.reserved <= 0:
            seller_detail.status = 0
        seller_detail.save()
        if not picklist.order_type == 'combo':
            SellerOrderSummary.objects.create(picklist_id=picklist.id, pick_number=pick_number, quantity=insert_quan,
                                              seller_order_id=seller_detail.seller_order.id,
                                              creation_date=datetime.datetime.now(),
                                              financial_year=financial_year)
        else:
            combo_picks = picks_all.filter(order_id=picklist.order.id, order_type='combo').values(
                'order__sku__sku_code', 'order_id',
                'stock__sku_id', 'sku_code').distinct().annotate(total_reserved_sum=Sum('reserved_quantity'),
                                                                 total_picked_sum=Sum('picked_quantity'))
            final_picked = []
            seller_order_summary = SellerOrderSummary.objects.filter(picklist__order_id=picklist.order.id,
                                                                     picklist__order__user=picklist.order.user)
            for combo_pick in combo_picks:
                seller_picks = \
                seller_order_summary.filter(picklist__order__sku__sku_code=combo_pick['order__sku__sku_code']). \
                    aggregate(Sum('quantity'))['quantity__sum']
                if not seller_picks:
                    seller_picks = 0
                picked_sum = float(combo_pick['total_picked_sum']) - seller_picks
                final_picked.append(picked_sum)
            if final_picked:
                insert_picked = min(final_picked)
                if insert_picked:
                    SellerOrderSummary.objects.create(picklist_id=picklist.id, pick_number=pick_number,
                                                      quantity=insert_picked,
                                                      seller_order_id=seller_detail.seller_order.id,
                                                      creation_date=datetime.datetime.now(),
                                                      financial_year=financial_year)

        for stock in stocks:
            seller_stocks = SellerStock.objects.filter(seller_id=seller_detail.seller_order.seller_id,
                                                       stock_id=stock.id, seller__user=picklist.order.user)
            for seller_stock in seller_stocks:
                if insert_quan <= 0:
                    break
                if float(seller_stock.quantity) < insert_quan:
                    update_quan = float(seller_stock.quantity)
                    insert_quan -= update_quan
                    seller_stock.quantity = 0
                else:
                    update_quan = insert_quan
                    seller_stock.quantity = float(seller_stock.quantity) - insert_quan
                    insert_quan = 0
                seller_stock.save()

@fn_timer
def create_order_summary(picklist,picked_count, pick_number, picks_all, stock=None):
    # seller_orders = SellerOrder.objects.filter(order_id=picklist.order_id, order__user=picklist.order.user, status=1)
    order = picklist.order
    st_order = picklist.storder_set.filter()
    if (not order or not picked_count) and not st_order.exists() :
        return
    financial_year = get_financial_year(datetime.datetime.now())
    if st_order.exists():
        invoice_value = picked_count
        if not pick_number: pick_number = 1
        stocksummarysummary_dict = {'picklist_id': picklist.id, 'pick_number': pick_number, 'quantity': picked_count,
                                    'stock_transfer_id': st_order[0].stock_transfer.id, 'financial_year': financial_year}
        if stock:
            stocksummarysummary_dict['price'] = stock.sku.average_price
        StockTransferSummary.objects.create(**stocksummarysummary_dict)
        return
    insert_quan = 0
    if order.original_quantity > picked_count:
        insert_quan = picked_count
        picked_count = 0
    elif order.original_quantity <= picked_count:
        insert_quan = order.original_quantity
        picked_count = picked_count - int(order.original_quantity)
    if not picklist.order_type == 'combo':
        SellerOrderSummary.objects.create(picklist_id=picklist.id, pick_number=pick_number, quantity=insert_quan,
                                          order_id=order.id, creation_date=datetime.datetime.now(),
                                          financial_year=financial_year)
    else:
        combo_picks = picks_all.filter(order_id=picklist.order.id, order_type='combo').values('order__sku__sku_code',
                                                                                              'order_id',
                                                                                              'stock__sku_id',
                                                                                              'sku_code').distinct().annotate(
            total_reserved_sum=Sum('reserved_quantity'),
            total_picked_sum=Sum('picked_quantity'))
        final_picked = []
        seller_order_summary = SellerOrderSummary.objects.filter(picklist__order_id=picklist.order.id,
                                                                 picklist__order__user=picklist.order.user)
        for combo_pick in combo_picks:
            seller_picks = \
            seller_order_summary.filter(picklist__order__sku__sku_code=combo_pick['order__sku__sku_code']). \
                aggregate(Sum('quantity'))['quantity__sum']
            if not seller_picks:
                seller_picks = 0
            picked_sum = float(combo_pick['total_picked_sum']) - seller_picks
            final_picked.append(picked_sum)
        if final_picked:
            insert_picked = min(final_picked)
            if insert_picked:
                SellerOrderSummary.objects.create(picklist_id=picklist.id, pick_number=pick_number,
                                                  quantity=insert_picked,
                                                  order_id=order.id, creation_date=datetime.datetime.now(),
                                                  financial_year=financial_year)

@fn_timer
def get_seller_pick_id(picklist, user):
    pick_number = 1
    if not picklist.order:
        return ''
    #summary = SellerOrderSummary.objects.filter(Q(seller_order__order__order_id=picklist.order.order_id) |
    #                                            Q(order__order_id=picklist.order.order_id),
    #                                            picklist__order__user=user.id). \
    #    order_by('-creation_date')
    summary1 = SellerOrderSummary.objects.filter(seller_order__order__order_id=picklist.order.order_id,
                                      picklist__order__user=user.id).only('pick_number').\
                                    aggregate(Max('pick_number'))['pick_number__max']
    summary2 = SellerOrderSummary.objects.filter(order__order_id=picklist.order.order_id,
                                      picklist__order__user=user.id).only('pick_number').\
                                    aggregate(Max('pick_number'))['pick_number__max']
    summary = max(summary1, summary2)
    if summary:
        pick_number = int(summary) + 1
    return pick_number

@fn_timer
def update_no_stock_to_location(request, user, picklist, val, picks_all, picklist_batch):
    new_update_ids = []
    for picklist in picklist_batch:
        if not picklist.stock:
            pc_upd_ids = update_exist_picklists(picklist.picklist_number, request, user, sku_code=val['wms_code'],
                                                location=val['location'], \
                                                picklist_obj=picklist)
            new_update_ids = list(chain(new_update_ids, pc_upd_ids))
    if new_update_ids:
        picklist_batch = picks_all.filter(id__in=new_update_ids)
    return picklist_batch


def update_order_labels(picklist, val):
    if ',' in val['labels']:
        label_codes = list(set(val['labels'].split(',')))
    else:
        label_codes = list(set(val['labels'].split('\r\n')))
    for label in label_codes:
        order_labels = OrderLabels.objects.filter(order__user=picklist.order.user, label=label)
        for order_label in order_labels:
            order_label.status = 0
            order_label.save()
            log.info('Order Label ' + str(label) + ' is mapped to ' + str(picklist.order.order_id))


def check_req_min_order_val(user, skus):
    order_val_flag = False
    users_min_order_val = user.userprofile.min_order_val
    users_order_amt = 0
    sku_qty_map = {}
    sku_objs = SKUMaster.objects.filter(wms_code__in=skus, user=user.id, threshold_quantity__gt=0)
    for sku in sku_objs:
        qty, total_qty,max_norm_qty = get_auto_po_quantity(sku)
        supplier_id, price, taxes = auto_po_warehouses(sku, qty)
        sku_qty_map[sku.sku_code] = (qty, price)
        if price:
            users_order_amt += (qty * price)
        intransit_tot_amt = IntransitOrders.objects.filter(sku=sku, user=sku.user, status=1). \
            values('sku__sku_code').annotate(tot_inv_amt=Sum('invoice_amount'))
        if intransit_tot_amt:
            users_order_amt += intransit_tot_amt[0]['tot_inv_amt']
    if users_order_amt > users_min_order_val:
        order_val_flag = True
    return order_val_flag, sku_qty_map


def create_intransit_order(auto_skus, user, sku_qty_map):
    sku_objs = SKUMaster.objects.filter(wms_code__in=auto_skus, user=user.id, threshold_quantity__gt=0)
    intr_data = {'user': user.id, 'customer_id': user.id, 'intr_order_id': get_intr_order_id(user.id), 'status': 1}
    for sku in sku_objs:
        intr_data['sku'] = sku
        quantity, price = sku_qty_map.get(sku.sku_code, (0, 0))
        if quantity:
            intr_data['quantity'] = quantity
        else:
            continue
        intr_data['unit_price'] = price
        intr_data['invoice_amount'] = round(quantity * price, 2)
        intr_obj = IntransitOrders(**intr_data)
        intr_obj.save()
        log.info('Intransit Order Created Successfully')


def delete_intransit_orders(auto_skus, user):
    sku_objs = SKUMaster.objects.filter(wms_code__in=auto_skus, user=user.id, threshold_quantity__gt=0)
    intransit_orders = IntransitOrders.objects.filter(sku__in=sku_objs, user=user.id, status=1)
    if intransit_orders:
        for intr_order in intransit_orders:
            intr_order.status = 0
            intr_order.save()


def validate_picklist_combos(data, all_picklists, picks_all):
    combo_status = []
    combo_orders_dict = OrderedDict()
    final_data_list = []
    combo_exists = False
    for key, value in data.iteritems():
        if key in ('name', 'number', 'order', 'sku', 'invoice', 'warehouse_id', ''):
            continue
        picklist_batch = ''
        picklist_order_id = value[0]['order_id']
        if picklist_order_id:
            picklist = all_picklists.get(order__order_id=picklist_order_id,
                                         order__sku__sku_code=value[0]['wms_code'])
        elif not key:
            scan_wms_codes = map(lambda d: d['wms_code'], value)
            picklist_batch = picks_all.filter(
                Q(stock__sku__wms_code__in=scan_wms_codes) | Q(order__sku__wms_code=scan_wms_codes),
                reserved_quantity__gt=0, status__icontains='open')
        else:
            picklist_status = ''
            if value[0].get('picklist_status', ''):
                picklist_status = value[0]['picklist_status']
            if picklist_status == 'open':
                picklist_batch = picks_all.filter(id=key)
                picklist = picklist_batch[0]
            else:
                picklist = picks_all.get(id=key)
        count = 0
        if not picklist_batch:
            picklist_batch = get_picklist_batch(picklist, value, all_picklists)
        for i in range(0, len(value)):
            if value[i]['picked_quantity']:
                count += float(value[i]['picked_quantity'])
        final_data_list.append({'picklist': picklist, 'picklist_batch': picklist_batch,
                                'count': count, 'picklist_order_id': picklist_order_id,
                                'value': value, 'key': key})
        for val in value:
            if not val['picked_quantity']:
                continue
            else:
                count = float(val['picked_quantity'])
            if picklist_order_id:
                picklist_batch = list(set([picklist]))
            for picklist in picklist_batch:
                if (not picklist.order and not picklist.storder_set.filter()) or not picklist.order_type == 'combo':
                    continue
                if float(picklist.reserved_quantity) < count:
                    pick_val = float(picklist.reserved_quantity)
                else:
                    pick_val = count
                combo_exists = True
                if not picklist.storder_set.filter() :
                    grouping_key = '%s<<>>%s<<>>%s' % (str(picklist.order_id), str(picklist.order.sku_id), str(picklist.order.quantity))
                else:
                    stock_transfer_obj = picklist.storder_set.filter()[0].stock_transfer
                    grouping_key = '%s<<>>%s<<>>%s' % (str(stock_transfer_obj.id), str(stock_transfer_obj.sku_id), str(stock_transfer_obj.quantity))
                if picklist.stock:
                    sku_code = picklist.stock.sku.sku_code
                else:
                    sku_code = picklist.sku_code
                combo_orders_dict.setdefault(grouping_key, {})
                combo_orders_dict[grouping_key].setdefault(sku_code, 0)
                combo_orders_dict[grouping_key][sku_code] += pick_val
                count -= pick_val
    if combo_exists:
        for key, value in combo_orders_dict.iteritems():
            combo_order_id, combo_sku_id, combo_sku_qty = key.split('<<>>')
            sku_relation_qtys = dict(SKURelation.objects.filter(parent_sku_id=combo_sku_id).\
                 values_list('member_sku__sku_code', 'quantity'))
            confirm_qty = []
            for key1, val in value.iteritems():
                confirm_qty.append(round(val/sku_relation_qtys.get(key1, 1),2))
            if len(set(confirm_qty)) > 1:
                combo_status.append({str(combo_order_id): value.keys()})
    return combo_status, final_data_list


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def picklist_confirmation(request, user=''):
    warehouse_id = request.POST.get('warehouse_id_', '')
    if warehouse_id:
        user = User.objects.get(id=warehouse_id)
    if check_consumption_configuration([user.id], extra_flag=True):
        return HttpResponse("Picklist Confirmation Disable Due to Closing Stock Updations")
    if request.POST.get('source'):
        cur_user = request.POST.get('source')
        user = User.objects.get(username=cur_user)
    reversion.set_user(request.user)
    reversion.set_comment("picklist_confirmation: %s" % str(get_user_ip(request)))
    st_time = datetime.datetime.now()
    data = {}
    all_data = {}
    auto_skus = []
    picklists_send_mail = {}
    mod_locations = []
    seller_pick_number = ''
    status = ''
    seller_id = ''
    grn_number_dict = {}
    for key, value in request.POST.iterlists():
        if key not in ['source', 'order_typ']:
            name, picklist_id = key.rsplit('_', 1)
            data.setdefault(picklist_id, [])
            for index, val in enumerate(value):
                if len(data[picklist_id]) < index + 1:
                    data[picklist_id].append({})
                data[picklist_id][index][name] = val
    passed_serial_number = request.POST.get('passed_serial_number', {})
    failed_serial_number = request.POST.get('failed_serial_number', {})
    imei_qc_details = request.POST.get('imei_qc_details', '')
    if passed_serial_number:
        passed_serial_number = eval(passed_serial_number)
    if failed_serial_number:
        failed_serial_number = eval(failed_serial_number)
    if imei_qc_details:
        imei_qc_details = eval(imei_qc_details)
    if 'details' in data.keys():
        del (data['details'])
    if 'number' in data.keys():
        del (data['number'])

    log.info('Request params for ' + user.username + ' is ' + str(data))
    try:
        data = OrderedDict(sorted(data.items(), reverse=True))
        error_string = ''
        picklist_number = request.POST['picklist_number']
        single_order = request.POST.get('single_order', '')
        enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
        user_profile = UserProfile.objects.get(user_id=user.id)
        decimal_limit = get_decimal_value(user.id)
        if not decimal_limit:
            decimal_limit = 1
        all_picklists = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id),
                                                picklist_number=picklist_number,
                                                status__icontains="open")

        merge_flag = request.POST.get('merge_invoice', '')
        if merge_flag == 'true':
            merge_flag = True
        elif merge_flag == 'false':
            merge_flag = False
        picks_all = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id),
                                            picklist_number=picklist_number)
        all_skus = SKUMaster.objects.filter(user=user.id)
        all_locations = LocationMaster.objects.filter(zone__user=user.id)
        all_pick_ids = all_picklists.values_list('id', flat=True)
        all_pick_locations = PicklistLocation.objects.filter(picklist__picklist_number=picklist_number, status=1,
                                                             picklist_id__in=all_pick_ids)

        # validate combo picklists
        combo_status, final_data_list = validate_picklist_combos(data, all_picklists, picks_all)
        if combo_status:
            return HttpResponse(json.dumps({'message': 'Combo Quantities are not matching',
                                            'sku_codes': combo_status, 'status': 0}))
        with transaction.atomic('default'):
            for picklist_dict in final_data_list:
                picklist = picklist_dict['picklist']
                if picklist.storder_set.filter():
                    transact_type = 'st_picklist'
                else:
                    transact_type = 'picklist'
                picklist_batch = picklist_dict['picklist_batch']
                count = picklist_dict['count']
                picklist_order_id = picklist_dict['picklist_order_id']
                value = picklist_dict['value']
                key = picklist_dict['key']
                for val in value:
                    if not val['picked_quantity']:
                        continue
                    else:
                        val['picked_quantity'] = float(val['picked_quantity']) * float(val['conversion_value'])
                        count = float(val['picked_quantity'])
                    if picklist_order_id:
                        picklist_batch = list(set([picklist]))
                    if not val['location'] == 'NO STOCK':
                        picklist_batch = update_no_stock_to_location(request, user, picklist, val, picks_all,
                                                                     picklist_batch)
                    temp_pick_ids = map(lambda x: x.id, picklist_batch)
                    picklist_batch_objs = Picklist.objects.using('default').filter(id__in=temp_pick_ids).select_for_update()
                    for picklist in picklist_batch_objs.iterator():
                        save_status = ''
                        if not failed_serial_number.keys() and count == 0:
                            continue

                        status = ''
                        if not val['location'] == 'NO STOCK':
                            pic_check_data, status = validate_location_stock(val, all_locations, all_skus, user,
                                                                             picklist)
                        if status:
                            continue
                        if not picklist.stock:
                            if val['location'] == 'NO STOCK':
                                if float(picklist.reserved_quantity) > float(val['picked_quantity']):
                                    picking_count = float(val['picked_quantity'])
                                else:
                                    picking_count = float(picklist.reserved_quantity)
                                count -= picking_count
                                seller_pick_number = confirm_no_stock(picklist, request, user, picks_all,
                                                                      picklists_send_mail, merge_flag, user_profile,
                                                                      seller_pick_number, val=val,
                                                                      p_quantity=picking_count)
                                continue
                        if not seller_pick_number:
                            if picklist.storder_set.filter():
                                seller_pick_number  =  get_stocktransfer_picknumber(user, picklist)
                            else:
                                seller_pick_number = get_seller_pick_id(picklist, user)
                        if float(picklist.reserved_quantity) > float(val['picked_quantity']):
                            picking_count = float(val['picked_quantity'])
                        else:
                            picking_count = float(picklist.reserved_quantity)
                        picking_count1 = 0  # picking_count
                        wms_id = all_skus.exclude(sku_code='').get(wms_code=val['wms_code'], user=user.id)
                        if not val.get('batchno', ''):
                            total_stock1 = StockDetail.objects.using('default').filter(batch_detail__batch_no='', **pic_check_data).\
                                                    distinct().select_for_update()
                            total_stock2 = StockDetail.objects.using('default').filter(**pic_check_data).\
                                                    exclude(batch_detail__batch_no='').distinct().select_for_update()
                            total_stock = total_stock1 | total_stock2
                        else:
                            total_stock = StockDetail.objects.using('default').filter(**pic_check_data).distinct().select_for_update()
                        if 'imei' in val.keys() and val['imei'] and picklist.order and val['imei'] != '[]':
                            insert_order_serial(picklist, val)
                        if 'labels' in val.keys() and val['labels'] and picklist.order:
                            update_order_labels(picklist, val)
                        order_id = picklist.order
                        if picklist.order and picklist.order.sku.wms_code in passed_serial_number.keys():
                            if val.get('passed_serial_number', ''):
                                send_imei_qc_details = dict(zip(json.loads(val.get('passed_serial_number', '')), [imei_qc_details[k] for k in json.loads(val.get('passed_serial_number', ''))]))
                                save_status = "PASS"
                            try:
                                dispatch_qc(user, send_imei_qc_details, order_id, save_status)
                            except Exception as e:
                                import traceback
                                picklist_qc_log.debug(traceback.format_exc())
                                picklist_qc_log.info("Error in Dispatch QC - On Pass - %s - %s" % (str(user.username),  str(e)))
                        if picklist.order and picklist.order.sku.wms_code in failed_serial_number.keys():
                            if val.get('failed_serial_number', ''):
                                send_imei_qc_details = dict(zip(json.loads(val.get('failed_serial_number', '')), [imei_qc_details[k] for k in json.loads(val.get('failed_serial_number', ''))]))
                                save_status = "FAIL"
                            try:
                                dispatch_qc(user, send_imei_qc_details, order_id, save_status)
                            except Exception as e:
                                import traceback
                                picklist_qc_log.debug(traceback.format_exc())
                                picklist_qc_log.info("Error in Dispatch QC - On Fail - %s - %s" % (str(user.username), str(e)))
                        if count == 0:
                            continue
                        if  'imei' in val.keys() and val['imei'] and not picklist.order and val['imei'] != '[]' :
                            order = picklist.storder_set.filter()
                            if order:
                                order = order[0]
                                insert_st_order_serial(picklist, val, order=order)
                        if passed_serial_number and picklist.storder_set.filter():
                            order = picklist.storder_set.filter()
                            order = order[0]
                            insert_st_order_serial(picklist, val, order=order,passed_serial_number = passed_serial_number)
                        reserved_quantity1 = picklist.reserved_quantity
                        tot_quan = 0
                        for stock in total_stock:
                            tot_quan += float(stock.quantity)
                            # if tot_quan < reserved_quantity1:
                            # total_stock = create_temp_stock(picklist.stock.sku.sku_code, picklist.stock.location.zone, abs(reserved_quantity1 - tot_quan), list(total_stock), user.id)

                        seller_stock_objs = []
                        for stock in total_stock:
                            update_picked = 0
                            if user.userprofile.user_type == 'marketplace_user':
                                if picklist.order:
                                    seller_order = picklist.order.sellerorder_set.filter()
                                    seller_id = ''
                                    if seller_order:
                                        seller_id = seller_order[0].seller_id
                                elif picklist.storder_set.filter():
                                    stock_transfer = picklist.storder_set.filter()[0].stock_transfer
                                    seller_id = stock_transfer.st_seller_id
                                stock_quantity = SellerStock.objects.filter(stock_id=stock.id, seller_id=seller_id,
                                                                        quantity__gt=0).aggregate(Sum('quantity'))['quantity__sum']
                                if not stock_quantity:
                                    stock_quantity = 0
                            else:
                                stock_quantity = stock.quantity
                            pre_stock = float(stock_quantity)
                            if picking_count == 0:
                                break
                            if picking_count > stock_quantity:
                                update_picked = float(stock_quantity)
                                picking_count -= stock_quantity
                                picklist.reserved_quantity -= stock_quantity
                                stock.quantity = stock.quantity - stock_quantity
                            else:
                                update_picked = picking_count
                                stock.quantity -= picking_count
                                picklist.reserved_quantity -= picking_count
                                picking_count = 0
                            update_picked = truncate_float(update_picked, 5)
                            picklist.reserved_quantity = truncate_float(picklist.reserved_quantity, 5)
                            stock.quantity = truncate_float(stock.quantity, 5)
                            if float(stock.location.filled_capacity) - update_picked >= 0:
                                location_fill_capacity = (float(stock.location.filled_capacity) - update_picked)
                                location_fill_capacity = truncate_float(location_fill_capacity, 5)
                                setattr(stock.location, 'filled_capacity', location_fill_capacity)
                                stock.location.save()
                            if picklist.storder_set.filter():
                                try:
                                    if picklist.storder_set.filter()[0].stock_transfer.st_type == 'MR':
                                        transact_type = 'mr_picklist'
                                    else:
                                        transact_type = 'st_picklist'
                                except Exception as e:
                                    transact_type = 'st_picklist'
                            else:
                                transact_type = 'picklist'
                            search_po_locations = {
                                'picklist_id': picklist.id,
                                'stock__location_id': stock.location_id,
                                'status': 1
                            }
                            if stock.batch_detail:
                                search_po_locations['stock__batch_detail__batch_no'] = stock.batch_detail.batch_no
                            pick_loc = all_pick_locations.filter(**search_po_locations)
                            # update_picked = picking_count1
                            st_order = picklist.storder_set.filter()
                            if st_order:
                                stock_transfer = st_order[0].stock_transfer
                                last_change_date = stock_transfer.creation_date.date()
                                if stock_transfer.status != 1:
                                    stock_transfer.status = 2
                                if stock_transfer.st_seller:
                                    change_seller_stock(stock_transfer.st_seller_id, stock, user, update_picked, 'dec')
                                stock_transfer.save()
                                order_typ = stock_transfer.st_type
                                if not order_typ:
                                    order_typ = request.POST.get('order_typ', '')
                                update_picked_pack_qty = update_picked/float(val['conversion_value'])
                                grn_number_dict = update_stock_transfer_po_batch(user, stock_transfer, stock,
                                                                            update_picked_pack_qty,
                                                               order_typ = order_typ,
                                                                                 grn_number_dict=grn_number_dict, last_change_date=last_change_date)
                                save_sku_stats(user, stock.sku_id, picklist.id, transact_type, update_picked, stock)
                            else:
                                # SKU Stats
                                save_sku_stats(user, stock.sku_id, picklist.id, transact_type, update_picked, stock)
                            if pick_loc:
                                update_picklist_locations(pick_loc, picklist, update_picked, pick_sequence=seller_pick_number)
                            else:
                                data = PicklistLocation(picklist_id=picklist.id, stock=stock, quantity=update_picked,
                                                        reserved=0, status=0,
                                                        creation_date=datetime.datetime.now(),
                                                        updation_date=datetime.datetime.now())
                                data.save()
                                exist_pics = all_pick_locations.exclude(id=data.id).filter(picklist_id=picklist.id,
                                                                                           status=1, reserved__gt=0)
                                po_location_sequence_mapping(data, seller_pick_number, update_picked)
                                update_picklist_locations(exist_pics, picklist, update_picked, 'true')
                            if stock.location.zone.zone == 'BAY_AREA':
                                reduce_putaway_stock(stock, update_picked, user.id)
                            dec_quantity = pre_stock - float(stock.quantity)
                            if stock.pallet_detail:
                                update_picklist_pallet(stock, update_picked)
                            stock.save()
                            seller_stock_objs.append(stock)
                            mod_locations.append(stock.location.location)
                            picking_count1 += update_picked
                        picklist.picked_quantity = float(picklist.picked_quantity) + picking_count1
                        if picklist.reserved_quantity == 0:
                            # Auto Shipment check and Mapping the serial Number
                            if picklist.order and picklist.order.order_type == 'Transit':
                                serial_order_mapping(picklist, user)
                            if picklist.status == 'batch_open':
                                picklist.status = 'batch_picked'
                            else:
                                picklist.status = 'picked'
                            if picklist.order:
                                check_and_update_order(user.id, picklist.order.original_order_id)
                            all_pick_locations.filter(picklist_id=picklist.id, status=1).update(status=0)
                        picklist.save()
                        if user_profile.user_type == 'marketplace_user' and picklist.order:
                            create_seller_order_summary(picklist, picking_count1, seller_pick_number, picks_all,
                                                        seller_stock_objs)
                        else:
                            create_order_summary(picklist, picking_count1, seller_pick_number, picks_all, stock=stock)
                        picked_status = ""
                        if picklist.picked_quantity > 0 and picklist.order:
                            if merge_flag:
                                quantity = picklist.picked_quantity
                            else:
                                quantity = picking_count1
                            if picklist.order.order_id in picklists_send_mail.keys():
                                if picklist.order.sku.sku_code in picklists_send_mail[picklist.order.order_id].keys():
                                    qty = float(picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code])
                                    picklists_send_mail[picklist.order.order_id][picklist.order.sku.sku_code] = qty + float(
                                        quantity)
                                else:
                                    picklists_send_mail[picklist.order.order_id].update(
                                        {picklist.order.sku.sku_code: float(quantity)})

                            else:
                                picklists_send_mail.update(
                                    {picklist.order.order_id: {picklist.order.sku.sku_code: float(quantity)}})
                        count = count - picking_count1
                        auto_skus.append(val['wms_code'])
            for grn_dict in grn_number_dict.values():
                update_sku_avg_from_grn(grn_dict['warehouse'], grn_dict['grn_number'])
        if auto_skus:
            auto_skus = list(set(auto_skus))
            if user.username in MILKBASKET_USERS: check_and_update_marketplace_stock(auto_skus, user)
            price_band_flag = get_misc_value('priceband_sync', user.id)
            if price_band_flag == 'true':
                reaches_order_val, sku_qty_map = check_req_min_order_val(user, auto_skus)
                if reaches_order_val:
                    auto_po(auto_skus, user.id)
                    delete_intransit_orders(auto_skus, user)  # deleting intransit order after creating actual order.
                else:
                    create_intransit_order(auto_skus, user, sku_qty_map)
            else:
                auto_po(auto_skus, user.id)
        detailed_invoice = get_misc_value('detailed_invoice', user.id)

        if (detailed_invoice == 'false' and picklist.order and picklist.order.marketplace == "Offline"):
            check_and_send_mail(request, user, picklist, picks_all, picklists_send_mail)
        order_ids = picks_all.values_list('order_id', flat=True).distinct()
        if get_misc_value('automate_invoice', user.id) == 'true' and single_order:
            order_ids = picks_all.filter(order__order_id=single_order, picked_quantity__gt=0).values_list('order_id',
                                                                                                          flat=True).distinct()
            order_id = picklists_send_mail.keys()
            if order_ids and order_id:
                ord_id = order_id[0]
                order_ids = [str(int(i)) for i in order_ids]
                order_ids = ','.join(order_ids)
                invoice_data = get_invoice_data(order_ids, user, picklists_send_mail[ord_id])
                invoice_data = modify_invoice_data(invoice_data, user)
                # invoice_data['invoice_no'] = 'TI/1116/' + invoice_data['order_no']
                # invoice_data['invoice_date'] = get_local_date(user, datetime.datetime.now())
                offline_flag = False
                if picklist.order.marketplace == "Offline":
                    offline_flag = True
                invoice_data['offline_flag'] = offline_flag
                invoice_data['picklist_id'] = picklist.id
                invoice_data['picklists_send_mail'] = str(picklists_send_mail)

                invoice_data['order_id'] = invoice_data['order_id']
                user_profile = UserProfile.objects.get(user_id=user.id)
                if not invoice_data['detailed_invoice'] and invoice_data['is_gst_invoice']:
                    invoice_data = build_invoice(invoice_data, user, False)
                    #return HttpResponse(json.dumps({'data': invoice_data, 'message': '',
                    #                                'sku_codes': [], 'status': 1}))
                    return HttpResponse(invoice_data)
                return HttpResponse(json.dumps({'data': invoice_data, 'message': '', 'status': 'invoice'}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Picklist Confirmation failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(data), str(e)))
        #return HttpResponse(json.dumps({'message': 'Picklist Confirmation Failed',
        #                                'sku_codes': [], 'status': 0}))
        return HttpResponse('Picklist Confirmation Failed')
    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("process completed")
    log.info("total time -- %s" % (duration))

    if mod_locations:
        update_filled_capacity(list(set(mod_locations)), user.id)
    if status:
        return HttpResponse(status)
    else:
        # try:
        #     netsuite_picklist_confirmation(final_data_list, user)
        # except Exception as e:
        #     import traceback
        #     log.debug(traceback.format_exc())
        #     log.info('Netsuite Picklist Confirmation pushing failed for %s and params are %s and error statement is %s' % (
        #     str(user.username), str(data), str(e)))
        return HttpResponse('Picklist Confirmed')

def netsuite_picklist_confirmation(final_data_list, user):
    from datetime import datetime
    from pytz import timezone
    it_date = datetime.now(timezone("Asia/Kolkata")).replace(microsecond=0).isoformat()
    plant = user.userprofile.reference_id
    subsidary= user.userprofile.company.reference_id
    location_int_id = user.userprofile.location_code
    department= ""
    items=[]
    reason = ""
    try:
        for picklist_dict in final_data_list:
            value = picklist_dict['value']
            key = picklist_dict['key']
            for item in value:
                #st_transfer= StockTransfer.objects.get(order_id=picklist_dict["picklist"].picklist_number, sku_id=picklist_dict["picklist"]._stock_cache.sku_id)
               # open_st= OpenST.objects.get(id=st_transfer.st_po_id)
               # price= open_st.price
               # order_quantity= open_st.order_quantity
               # cgst_tax= open_st.cgst_tax
               # sgst_tax= open_st.sgst_tax
               # igst_tax= open_st.igst_tax
               # cess_tax= open_st.cess_tax
               # mrp= open_st.mrp
                mfg_date,exp_date="",""
                print(item.get("manufactured_date",None), item.get("expiry_date",None) )
                if(item.get("manufactured_date",None)):
                    mfg_date = datetime.strptime(item["manufactured_date"], '%d/%m/%Y').strftime('%d-%m-%Y')
                    m_date= datetime.strptime(mfg_date, '%d-%m-%Y')
                    mfg_date= m_date.isoformat()
                if(item.get("expiry_date",None)):
                    exp_date = datetime.strptime(item["expiry_date"], '%d/%m/%Y').strftime('%d-%m-%Y')
                    e_date=datetime.strptime(exp_date, '%d-%m-%Y')
                    exp_date= e_date.isoformat()
                print(mfg_date, exp_date)
                unitdata = gather_uom_master_for_sku(user, item.get("wms_code"))
                unitexid = unitdata.get('name', None)
                purchaseUOMname = None
                for row in unitdata.get('uom_items', None):
                    if row.get('unit_type', '') == 'Purchase':
                        purchaseUOMname = row.get('unit_name', None)
                items.append({ "adjust_qty_by": item.get("picked_quantity",0),
                            "sku_code": item.get("wms_code"),
                            "batchno": item.get("batchno",""),
                            "mrp" : item.get("mrp",0),
                            "exp_date": exp_date,
                            "mfg_date": mfg_date,
                            'unitypeexid': unitexid,
                            'uom_name': purchaseUOMname,
                            #"price": price,
                            #"order_quantity":order_quantity,
                            #"cgst_tax":cgst_tax,
                            #"sgst_tax":sgst_tax,
                            #"igst_tax":igst_tax,
                            #"cess_tax": cess_tax,
                            #"mrp":mrp
                        })
        stock_transfer = { 'it_number': "stock_transfer_" + str(final_data_list[0]["picklist"].picklist_number),
            'department': department,
            "subsidiary": subsidary,
            "location_int_id": location_int_id,
            "plant": plant,
            'items': items,
            "it_date": it_date,
            "remarks": reason
        }
        from stockone_integrations.views import Integrations
        intObj = Integrations(user, 'netsuiteIntegration')
        intObj.IntegrateInventoryTransfer(stock_transfer, "it_number", is_multiple=False)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('failed In Integration Module %s' % (str(e)))

def serial_order_mapping(picklist, user):
    try:
        order = picklist.order
        original_order_id = order.original_order_id
        if not original_order_id:
            original_order_id = str(order.order_code) + str(order.order_id)
        order_po_mapping = OrderPOMapping.objects.filter(sku__user=user.id, order_id=original_order_id,
                                                         sku_id=order.sku_id, status=1)
        if not order_po_mapping:
            log.info(
                "Order PO Mapping doesn't exists for user %s and for order_id %s" % (user.username, original_order_id))
            return "Mapping not done"
        order_po_mapping = order_po_mapping[0]
        imeis = list(POIMEIMapping.objects.filter(purchase_order__order_id=order_po_mapping.purchase_order_id,
                                                  sku_id=order_po_mapping.sku_id,
                                                  sku__user=user.id,
                                                  status=1).values_list('imei_number', flat=True))

        val = {}
        val['wms_code'] = order.sku.wms_code
        val['imei'] = ','.join(imeis)

        # Map Serial Number with Order
        insert_order_serial(picklist, val)

        # Create Shipment automatically
        create_shipment_entry(picklist)

        order_po_mapping.status = 0
        order_po_mapping.save()

        return "Success"

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Something went wrong")
        return "Failed"


def create_shipment_entry(picklist):
    """ create shipment data """
    order = picklist.order
    status = 1
    order_shipment = {}
    shipment_info = {}
    order_packaging = {}
    order_shipment['user'] = order.user
    shipment_number = OrderShipment.objects.filter(user=order.user).aggregate(Max('shipment_number'))[
        'shipment_number__max']
    if not shipment_number:
        shipment_number = 0
    order_shipment['shipment_number'] = shipment_number + 1
    order_shipment['shipment_date'] = datetime.datetime.now()
    order_shipment['shipment_reference'] = 'Auto Generated'
    order_shipment['status'] = status

    order_shipment_obj = OrderShipment(**order_shipment)
    order_shipment_obj.save()

    order_packaging['order_shipment'] = order_shipment_obj
    order_packaging['status'] = status
    order_packaging_obj = OrderPackaging(**order_packaging)
    order_packaging_obj.save()

    shipment_info['order_shipment'] = order_shipment_obj
    shipment_info['order_packaging'] = order_packaging_obj
    shipment_info['order'] = order
    shipment_info['shipping_quantity'] = order.quantity
    shipment_info['status'] = status
    shipment_info_obj = ShipmentInfo(**shipment_info)
    shipment_info_obj.save()
    picklist.status = 'dispatched'
    picklist.save()
    picklist.order.status = 2
    picklist.order.save()


def remove_sku(request):
    resp = {"message": "Updated Successfully"}
    ord_det_id = request.POST.get('id', '')
    if ord_det_id:
        ord_qs = OrderDetail.objects.filter(id=ord_det_id)
        if ord_qs:
            ord_obj = ord_qs[0]
            ord_obj.status = 3
            ord_obj.save()
            ord_obj.sellerordersummary_set.all().delete()
    else:
        resp = {"message": "Order does not exist"}
    return HttpResponse(json.dumps(resp))


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def update_invoice(request, user=''):
    """ update invoice data """
    reversion.set_user(request.user)
    reversion.set_comment("update_invoice: %s" % str(get_user_ip(request)))
    try:
        log.info('Request params for Update Invoice for ' + user.username + ' is ' + str(request.POST.dict()))
        resp = {"msg": "success", "data": {}}
        order_ids = request.POST.get("order_id", "")
        pick_number = request.POST.get('pick_number',1)
        consignee = request.POST.get("ship_to", "")
        invoice_date = request.POST.get("invoice_date", "")
        invoice_number = request.POST.get("invoice_number", "")
        invoice_reference = request.POST.get("invoice_reference", "")
        increment_invoice = get_misc_value('increment_invoice', user.id)
        marketplace = request.POST.get("marketplace", "")
        partial_quantity = False
        order_reference = request.POST.get("order_reference", "")
        order_reference_date = request.POST.get("order_reference_date", "")
        ord_det_id = request.POST.get("id", "")
        cm_id = request.POST.get("customer_id", "")
        myDict = dict(request.POST.iterlists())
        order_code = get_order_prefix(user.id)
        if invoice_date:
            invoice_date = datetime.datetime.strptime(invoice_date, "%m/%d/%Y").date()
        # order_id_val = ''.join(re.findall('\d+', order_ids))
        # order_code = ''.join(re.findall('\D+', order_ids))
        customer_id = ''
        customer_name = ''
        price_type = ''
        tax_type = ''
        if cm_id:
            cm_obj = CustomerMaster.objects.filter(id=cm_id)
            if not cm_obj:
                log.info('No Proper Customer Object')
                return HttpResponse(json.dumps({'message': 'failed'}))
            else:
                cm_obj = cm_obj[0]
            customer_id = cm_obj.customer_id
            customer_name = cm_obj.name
            price_type = cm_obj.price_type
            tax_type = cm_obj.tax_type
        # SellerOrderSummary.objects.filter(invoice_number=invoice_number).values_list('order__original_order_id', flat=True).distinct()
        for index, ord_id in enumerate(myDict['id']):
            if ord_id:
                continue
            else:
                sku_id = myDict['sku_id'][index]
                sgst_tax = float(myDict['sgst_tax'][index])
                cgst_tax = float(myDict['cgst_tax'][index])
                igst_tax = float(myDict['igst_tax'][index])
                invoice_amount = float(myDict['invoice_amount'][index].replace(',', ''))
                if invoice_amount == 'NaN':
                    invoice_amount = 0
                # unit_price = myDict['unit_price'][index]
                org_ord_id = myDict['order_id'][0]
                invoice_number = myDict['invoice_number'][0]
                shipment_date = myDict['invoice_date'][0]
                if shipment_date:
                    ship_date = shipment_date.split('/')
                    shipment_date = datetime.date(int(ship_date[2]), int(ship_date[0]), int(ship_date[1]))
                order_id = org_ord_id.replace(order_code, '').replace('DC', '').replace('PRE', '')
                ord_obj = OrderDetail.objects.filter(original_order_id=org_ord_id)
                address = myDict['ship_to'][0]
                sku_qs = SKUMaster.objects.filter(sku_code=sku_id, user=user.id)
                if not sku_qs:
                    continue
                else:
                    sku_id = sku_qs[0].id
                    title = sku_qs[0].sku_desc
                    # product_type = sku_qs[0].product_type
                    price_master_obj = PriceMaster.objects.filter(price_type=price_type, sku__id=sku_id)
                    if price_master_obj:
                        price_master_obj = price_master_obj[0]
                        price = price_master_obj.price
                    else:
                        price = sku_qs[0].price
                    # net_amount = price * int(quantity)
                    # org_order_id = 'MN%s' % order_id
                    order_detail_dict = {'sku_id': sku_id, 'title': title, 'order_id': order_id,
                                         'original_order_id': org_ord_id, 'user': user.id, 'customer_id': customer_id,
                                         'customer_name': customer_name, 'shipment_date': shipment_date,
                                         'address': address, 'unit_price': price, 'invoice_amount': invoice_amount,
                                         'creation_date': ord_obj[0].creation_date if ord_obj else None}
                    # tax = get_tax_value(user, order_detail_dict, product_type, tax_type)
                    # total_amount = ((net_amount * tax) / 100) + net_amount
                    # order_detail_dict['invoice_amount'] = invoice_amount
                    # order_detail_dict.pop('price')
                    ord_obj = OrderDetail.objects.filter(sku_id=sku_id, original_order_id=org_ord_id)
                    if ord_obj:
                        ord_obj = ord_obj[0]
                        #ord_obj.quantity = quantity
                        ord_obj.unit_price = price
                        ord_obj.invoice_amount = (invoice_amount/quantity) * ord_obj.quantity
                        ord_obj.save()
                    else:
                        ord_obj = OrderDetail(**order_detail_dict)
                        ord_obj.save()

                    CustomerOrderSummary.objects.create(order=ord_obj, sgst_tax=sgst_tax,cgst_tax=cgst_tax,
                                                        igst_tax=igst_tax, tax_type=tax_type)
                    sos_dict = {'pick_number': 1,
                                'creation_date': datetime.datetime.now(), 'order_id': ord_obj.id,
                                'invoice_number': invoice_number, 'order_status_flag': 'customer_invoices'}
                    sos_obj = SellerOrderSummary(**sos_dict)
                    sos_obj.save()

        existing_order_ids = [x for x in myDict['id'] if x]
        ord_ids = OrderDetail.objects.filter(id__in=existing_order_ids)
        if ord_ids:
            update_dict = {}
            if order_reference:
                update_dict['order_reference'] = order_reference
            if order_reference_date:
                update_dict['order_reference_date'] = datetime.datetime.strptime(order_reference_date,
                                                                                 "%m/%d/%Y").date()
            if update_dict:
                update_multiple_records(ord_ids, update_dict)
                # for ord_id_obj in ord_ids:
                #     for update_dict_key, update_dict_val in update_dict.items():
                #         setattr(ord_id_obj, key, value)
                #     ord_id_obj.save()
                #ord_ids.update(**update_dict)
        '''if increment_invoice == 'true' and invoice_number:
            invoice_sequence = InvoiceSequence.objects.filter(user_id=user.id, marketplace=marketplace)
            if not invoice_sequence:
                invoice_sequence = InvoiceSequence.objects.filter(user_id=user.id, marketplace='')
            if not user.userprofile.user_type == 'marketplace_user':
                seller_orders = SellerOrderSummary.objects.filter(order_id__in=ord_ids, order__user=user.id)
            else:
                seller_orders = SellerOrderSummary.objects.filter(seller_order__order_id__in=ord_ids,
                                                                  seller_order__order__user=user.id)
            if seller_orders and int(seller_orders[0].invoice_number) != int(invoice_number):
                if int(invoice_number) >= int(invoice_sequence[0].value) - 1:
                    seller_orders.update(invoice_number=str(invoice_number).zfill(3))
                    invoice_sequence = invoice_sequence[0]
                    invoice_sequence.value = int(invoice_number) + 1
                    invoice_sequence.save()
                else:
                    resp['msg'] = "Invoice number already Exist"
                    return HttpResponse(json.dumps(resp))'''

        # Updating the Unit Price
        for order_id in ord_ids:
            if not str(order_id.id) in myDict['id']:
                continue

            discount_percentage = 0
            sos_obj = SellerOrderSummary.objects.filter(order_id=order_id, invoice_number=invoice_number)
            sos_update_dict = {'invoice_reference': invoice_reference}
            #sos_obj.update(invoice_reference=invoice_reference)
            if invoice_date and sos_obj[0].creation_date.date() != invoice_date:
                #sos_obj.update(creation_date=invoice_date)
                sos_update_dict['creation_date'] = invoice_date
            update_multiple_records(sos_obj, sos_update_dict)
            unit_price_index = myDict['id'].index(str(order_id.id))
            # if order_id.unit_price != float(myDict['unit_price'][unit_price_index]):
            '''if float(myDict['quantity'][unit_price_index]) == 0:
                cust_objs = CustomerOrderSummary.objects.filter(order__id=order_id.id)
                if cust_objs:
                    cust_obj = cust_objs[0]
                    cust_obj.delete()
                if sos_obj:
                    sos_obj = sos_obj[0]
                    sos_obj.delete()
                order_id.delete()
                continue
            else:'''
            cust_obj = order_id.customerordersummary_set.all()
            if cust_obj:
                cust_obj = cust_obj[0]
                if order_id.quantity * order_id.unit_price:
                    discount_percentage = "%.1f" % (float((cust_obj.discount * 100) / (order_id.quantity * order_id.unit_price)))
            order_id.unit_price = float(myDict['unit_price'][unit_price_index])
            #order_id.invoice_amount = float(myDict['invoice_amount'][unit_price_index].replace(',',''))
            invoice_amount = float(myDict['invoice_amount'][unit_price_index].replace(',',''))
            order_id.invoice_amount = (invoice_amount/float(myDict['quantity'][unit_price_index])) * order_id.quantity
            if order_id.quantity != float(myDict['quantity'][unit_price_index]) :
                partial_quantity = True
            order_id.save()
            sgst_tax = float(myDict['sgst_tax'][unit_price_index])
            cgst_tax = float(myDict['cgst_tax'][unit_price_index])
            igst_tax = float(myDict['igst_tax'][unit_price_index])
            cust_objs = CustomerOrderSummary.objects.filter(order__id=order_id.id)
            if cust_objs:
                cust_obj = cust_objs[0]
                cust_obj.sgst_tax = sgst_tax
                cust_obj.cgst_tax = cgst_tax
                cust_obj.igst_tax = igst_tax
                cust_obj.consignee = consignee
                if invoice_date:
                    cust_obj.invoice_date = invoice_date
                if discount_percentage:
                    cust_obj.discount = ((order_id.quantity * order_id.unit_price)/100) * float(discount_percentage)
                cust_obj.save()
            else:
                CustomerOrderSummary.objects.create(order=order_id, sgst_tax=sgst_tax, cgst_tax=cgst_tax,
                                                    igst_tax=igst_tax, tax_type=tax_type)
            '''sos_objs = SellerOrderSummary.objects.filter(order_id=order_id)
            updating_quantity = float(myDict['quantity'][unit_price_index])
            seller_exist_qty = sos_objs.aggregate(Sum('quantity'))['quantity__sum']
            if not seller_exist_qty:
                seller_exist_qty = 0
            if float(seller_exist_qty) != float(updating_quantity):
                updating_diff = float(updating_quantity) - float(seller_exist_qty)
                for sos_obj in sos_objs:
                    if updating_diff <= 0:
                        if updating_diff > float(sos_obj.quantity):
                            sos_updating_qty = float(sos_obj.quantity)
                            updating_diff -= float(sos_obj.quantity)
                        else:
                            sos_updating_qty = updating_diff
                            updating_diff = 0
                    else:
                        sos_updating_qty = updating_diff
                        updating_diff = 0
                    if sos_updating_qty < 0 :
                        sos_updating_qty = 0

                    sos_obj.quantity = sos_obj.quantity + sos_updating_qty
                    sos_obj.save()'''


        # Updating or Creating Order other charges Table
        for i in range(0, len(myDict.get('charge_name', []))):
            if myDict.get('charge_id') and myDict['charge_id'][i]:
                order_charges = OrderCharges.objects.filter(id=myDict['charge_id'][i], user_id=user.id, order_type='order')
                invoice_order_charge = InvoiceOrderCharges.objects.filter(id = myDict['charge_id'][i] ,user = user.id)
                if order_charges.exists() or  invoice_order_charge.exists():
                    if not myDict['charge_amount'][i]:
                        myDict['charge_amount'][i] = 0
                    if not partial_quantity :
                        order_charges.update(charge_name=myDict['charge_name'][i], charge_amount=myDict['charge_amount'][i],charge_tax_value = myDict['charge_tax_value'][i])
                    else:
                        if  invoice_order_charge.exists():
                            invoice_order_charge = invoice_order_charge [0]
                            invoice_order_charge.charge_tax_value = myDict['charge_tax_value'][i]
                            invoice_order_charge.charge_amount = myDict['charge_amount'][i]
                            invoice_order_charge.save()
                        else:
                            InvoiceOrderCharges.objects.create(original_order_id = order_ids , pick_number = pick_number,charge_name = myDict['charge_name'][i],charge_amount = myDict['charge_amount'][i], charge_tax_value = myDict['charge_tax_value'][i],user = user)

            else:
                OrderCharges.objects.create(order_id=order_ids, charge_name=myDict['charge_name'][i],
                                            charge_amount=myDict['charge_amount'][i],
                                            charge_tax_value = myDict['charge_tax_value'][i],
                                            creation_date=datetime.datetime.now(),
                                            user_id=user.id)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Invoice failed for params for user %s for params %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))
        resp = {"msg": "Failed", "data": {}}

    return HttpResponse(json.dumps(resp))


@csrf_exempt
@login_required
@get_admin_user
def edit_invoice(request, user=''):
    """ The view to edit the invoice """
    order_ids = request.POST.get("order_id", "")
    picklist_id = request.POST.get("picklist_id", "")
    consignee = request.POST.get("consignee", "")
    payment_terms = request.POST.get("credit_period", "")
    dispatch_through = request.POST.get("dispatch_through", "")
    picklists_send_mail = request.POST.get("picklists_send_mail", "")
    invoice_date = request.POST.get("invoice_date", "")
    if invoice_date:
        invoice_date = datetime.datetime.strptime(invoice_date, "%m/%d/%Y").date()
    if picklists_send_mail:
        picklists_send_mail = eval(picklists_send_mail)
    order_id_val = ''.join(re.findall('\d+', order_ids))
    order_code = ''.join(re.findall('\D+', order_ids))
    ord_ids = OrderDetail.objects.filter(
        Q(order_id=order_id_val, order_code=order_code) | Q(original_order_id=order_ids),
        user=user.id).values_list('id', flat=True)
    for order_id in ord_ids:
        cust_objs = CustomerOrderSummary.objects.filter(order__user=user.id, order__id=order_id)
        if cust_objs:
            cust_obj = cust_objs[0]
            cust_obj.consignee = consignee
            cust_obj.payment_terms = payment_terms
            cust_obj.dispatch_through = dispatch_through
            if invoice_date:
                cust_obj.invoice_date = invoice_date
            cust_obj.save()

    picklist_obj = Picklist.objects.filter(order_id__in=ord_ids, order__user=user.id)
    check_and_send_mail(request, user, picklist_obj[0], picklist_obj, picklists_send_mail)

    return HttpResponse('Success')


def add_consignee_data(invoice_data, order_ids, user):
    """ Add Ship to Address and Payment terms"""

    cust_ord_objs = CustomerOrderSummary.objects.filter(order__id__in=order_ids)
    if not cust_ord_objs:
        return invoice_data
    for obj in cust_ord_objs:
        if obj.consignee:
            invoice_data['consignee'] = obj.consignee
        if obj.payment_terms:
            if invoice_data['customer_details']:
                invoice_data['customer_details'][0]['credit_period'] = obj.payment_terms
            else:
                invoice_data['customer_details'] = [{'credit_period': obj.payment_terms}]
        if obj.dispatch_through:
            invoice_data['dispatch_through'] = obj.dispatch_through
            break

    return invoice_data


@csrf_exempt
@login_required
@get_admin_user
def view_picklist(request, user=''):
    show_image = 'false'
    use_imei = 'false'
    data_id = request.GET['data_id']
    warehouse_id = request.GET['warehouse_id']
    user = User.objects.get(id=warehouse_id)
    single_order = ''
    order_status = ''
    headers = list(PRINT_OUTBOUND_PICKLIST_HEADERS)
    qc_items_qs = UserAttributes.objects.filter(user_id=user.id,
                                                attribute_model='dispatch_qc',
                                                status=1).values_list('attribute_name', flat=True)
    qc_items = list(qc_items_qs)
    misc_detail = MiscDetail.objects.filter(user=user.id)
    data = misc_detail.filter(misc_type='show_image')
    if data:
        show_image = data[0].misc_value
    if show_image == 'true':
        headers.insert(0, 'Image')
    imei_data = misc_detail.filter(misc_type='use_imei')
    if imei_data:
        use_imei = imei_data[0].misc_value
    if use_imei == 'true':
        headers.insert(-1, 'Serial Number')
    pallet_switch = get_misc_value('pallet_switch', user.id)
    if pallet_switch == 'true':
        headers.insert(headers.index('Location') + 1, 'Pallet Code')
    data, sku_total_quantities, courier_name = get_picklist_data(data_id, user.id)
    if data:
        order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
        order_count_len = len(filter(lambda x: len(str(x)) > 0, order_count))
        if order_count_len == 1:
            single_order = str(order_count[0])
        order_status = data[0]['status']
    display_order_id = ''
    display_order_id = STOrder.objects.filter(picklist__picklist_number=data_id, stock_transfer__sku__user=user.id).values('stock_transfer__order_id').distinct()
    if display_order_id.exists():
        display_order_id_date = StockTransfer.objects.filter(order_id=display_order_id[0]['stock_transfer__order_id'])[0].creation_date
        display_order_id_date = get_local_date(request.user, display_order_id_date)
        display_order_id = display_order_id[0]['stock_transfer__order_id']
    return HttpResponse(json.dumps({'data': data, 'picklist_id': data_id, 'display_order_id': display_order_id, 'display_order_id_date': display_order_id_date,
                                    'show_image': show_image, 'use_imei': use_imei,
                                    'order_status': order_status, 'user': request.user.id,
                                    'single_order': single_order,
                                    'sku_total_quantities': sku_total_quantities, 'courier_name' : courier_name,
                                    'qc_items': qc_items, 'warehouse_id': warehouse_id}))


@csrf_exempt
@login_required
@get_admin_user
def view_picked_orders(request, user=''):
    data_id = request.GET['data_id']
    marketplace = request.GET.get('market_place', '')
    data = get_picked_data(data_id, user.id, marketplace)
    headers = PICKLIST_HEADER
    show_image = get_misc_value('show_image', user.id)
    if show_image == 'true' and 'Image' not in headers:
        headers = list(headers)
        headers.insert(0, 'Image')
    return HttpResponse(
        json.dumps({'data': data, 'picklist_id': data_id, 'show_image': show_image}, cls=DjangoJSONEncoder))


def get_picked_data(data_id, user, marketplace=''):
    pick_filter = {'picklist_number': data_id, 'picked_quantity__gt': 0}
    if marketplace:
        pick_filter['order__marketplace'] = marketplace

    picklist_orders = Picklist.objects.filter(Q(order__sku__user=user) | Q(stock__sku__user=user), **pick_filter). \
        exclude(picked_quantity=0, reserved_quantity=0)
    data = []
    for order in picklist_orders:
        if not order.stock:
            wms_code = order.order.sku.wms_code
            if order.order_type == 'combo' and order.sku_code:
                wms_code = order.sku_code
            data.append({'wms_code': wms_code, 'zone': 'NO STOCK', 'location': 'NO STOCK',
                         'reserved_quantity': order.reserved_quantity, 'picked_quantity': order.picked_quantity,
                         'stock_id': 0, 'picklist_number': data_id, 'id': order.id, 'order_id': order.order.order_id,
                         'image': '', 'title': order.order.title, 'order_detail_id': order.order_id,
                         'image': order.order.sku.image_url})
            continue

        picklist_location = PicklistLocation.objects.filter(
            Q(picklist__order__sku__user=user) | Q(stock__sku__user=user), picklist_id=order.id).exclude(reserved=0,
                                                                                                         quantity=0)
        for loc in picklist_location:
            if order.picked_quantity > 0:
                stock_detail = StockDetail.objects.get(id=loc.stock_id, sku__user=user)
                if order.picked_quantity == 0:
                    continue
                wms_code = order.stock.sku.wms_code
                if order.order:
                    order_id = order.order.order_id
                    title = order.order.title
                else:
                    st_order = STOrder.objects.filter(picklist_id=order.id)
                    order_id = st_order[0].stock_transfer.order_id
                    title = st_order[0].stock_transfer.sku.sku_desc
                if wms_code == 'TEMP':
                    wms_code = order.order.sku_code

                loc_quantity = loc.quantity - loc.reserved
                data.append({'wms_code': wms_code, 'zone': stock_detail.location.zone.zone,
                             'location': stock_detail.location.location, 'reserved_quantity': loc.reserved,
                             'picked_quantity': loc_quantity, 'stock_id': loc.stock_id, 'picklist_number': data_id,
                             'id': order.id, 'order_id': order_id, 'image': order.stock.sku.image_url, 'title': title,
                             'order_detail_id': order.order_id})
    return data


@csrf_exempt
@get_admin_user
def get_awb_marketplaces(request, user=''):
    api_status = False
    marketplace = ''
    courier_name = ''
    status = int(request.GET.get('status', 0))
    awb_marketplace = OrderAwbMap.objects.exclude(marketplace='').filter(status=status, user_id=user.id)
    marketplace = get_marketplace_names(user, 'all_marketplaces')
    if awb_marketplace:
        marketplace = list(awb_marketplace.values_list('marketplace', flat=True).distinct())
        courier_name = list(awb_marketplace.values_list('courier_name', flat=True).distinct())
    if marketplace:
        api_status = True
    return HttpResponse(json.dumps({'status': api_status, 'marketplaces': marketplace,
                                    'courier_name': courier_name}))


@csrf_exempt
@get_admin_user
def get_courier_name_for_marketplaces(request, user=''):
    api_status = False
    marketplace = request.GET.get('marketplace', '')
    status = int(request.GET.get('status', 0))
    if not marketplace:
        awb_marketplace = OrderAwbMap.objects.exclude(marketplace='').filter(status=status, user_id=user.id)
    else:
        awb_marketplace = OrderAwbMap.objects.filter(marketplace=marketplace, status=status, user_id=user.id)
    if awb_marketplace:
        courier_name = list(awb_marketplace.values_list('courier_name', flat=True).distinct())
        api_status = True
    return HttpResponse(json.dumps({'status': api_status, 'courier_name': courier_name}))


@csrf_exempt
@get_admin_user
def get_awb_view_shipment_info(request, user=''):
    sku_grouping = request.GET.get('sku_grouping', 'false')
    datatable_view = request.GET.get('view', '')
    search_params = {'user': user.id}
    awb_no = request.GET.get('awb_no', '')
    marketplace = request.GET.get('marketplace', [])
    courier_name = request.GET.get('courier_name', [])
    message = ''
    if awb_no:
        order_awb_map = OrderAwbMap.objects.filter(awb_no=awb_no, status=2, user=user).values('original_order_id')
        if courier_name:
            order_awb_map = order_awb_map.filter(courier_name=courier_name)
        if marketplace:
            order_awb_map = order_awb_map.filter(marketplace=marketplace)
            if not order_awb_map:
                message = 'Invalid AWB No. for this Marketplace'
        if order_awb_map.count():
            order_id_val = order_awb_map[0]['original_order_id']
        else:
            if not message:
                message = 'Incorrect AWB No.'
            return HttpResponse(json.dumps({'status': False, 'message': message}))
        order_id_search = ''.join(re.findall('\d+', order_id_val))
        order_code_search = ''.join(re.findall('\D+', order_id_val))
        all_orders = OrderDetail.objects.filter(
            Q(order_id=order_id_search, order_code=order_code_search) | Q(original_order_id=order_id_val), user=user.id,
            status=2)
        if not all_orders:
            return HttpResponse(json.dumps({'status': status, 'message': message}))
        tracking = ShipmentTracking.objects.filter(shipment__order__in=all_orders,
                                                   ship_status__in=['Dispatched', 'In Transit'],
                                                   shipment__order__user=user.id).values_list('shipment_id')
        if tracking.count():
            ship_info_id = ShipmentInfo.objects.filter(order__in=all_orders, order__user=user.id,
                                                       id__in=tracking)
            for ship_info in ship_info_id:
                try:
                    ShipmentTracking.objects.create(shipment_id=ship_info.id, ship_status='Out for Delivery',
                                                    creation_date=datetime.datetime.now())
                except:
                    import traceback
                    log.debug(traceback.format_exc())
                    log.info('Duplicate Entry %s for Shipment Tracking' % (str(user.username)))
                    return HttpResponse(json.dumps({'status': False, 'message': 'Error Occured'}))
                orig_ship_ref = ship_info.order_packaging.order_shipment.shipment_reference
                order_shipment = ship_info.order_packaging.order_shipment
                order_shipment.shipment_reference = orig_ship_ref
                order_shipment.save()
                order_awb_map.update(status=3)
        else:
            return HttpResponse(json.dumps({'status': False, 'message': 'AWB No. Not Found'}))
    return HttpResponse(json.dumps({'status': True, 'message': 'Shipped - Out for Delivery Successfully'}))


@csrf_exempt
@get_admin_user
def get_awb_shipment_details(request, user=''):
    data = {}
    sku_grouping = request.GET.get('sku_grouping', 'false')
    datatable_view = request.GET.get('view', '')
    search_params = {'user': user.id}
    awb_no = request.GET.get('awb_no', '');
    marketplace = request.GET.get('marketplace', '')
    courier_name = request.GET.get('courier_name', '')
    message = ''
    if awb_no:
        order_awb_map = OrderAwbMap.objects.filter(awb_no=awb_no, status=1, user=user).values('original_order_id')
        if courier_name:
            order_awb_map = order_awb_map.filter(courier_name=courier_name)
        if marketplace:
            order_awb_map = order_awb_map.filter(marketplace=marketplace)
            if not order_awb_map:
                message = 'Invalid AWB No. for this Marketplace'
        if order_awb_map.count():
            data['order_id'] = order_awb_map[0]['original_order_id']
        else:
            if not message:
                message = 'Incorrect AWB No.'
            return HttpResponse(json.dumps({'status': False, 'message': 'Incorrect AWB No.'}))
        result_data = 'No Orders found'
        status = False
        order_id_val = data['order_id']
        order_id_search = ''.join(re.findall('\d+', data['order_id']))
        order_code_search = ''.join(re.findall('\D+', data['order_id']))
        all_orders = OrderDetail.objects.filter(
            Q(order_id=order_id_search, order_code=order_code_search) | Q(original_order_id=order_id_val), user=user.id,
            status=0)
        if not all_orders:
            return HttpResponse(json.dumps({'status': status, 'message': message}))
        ship_no = get_shipment_number(user)
        ship_orders_data = get_shipment_quantity_for_awb(user, all_orders)
        if ship_orders_data:
            result = {'data': ship_orders_data, 'shipment_id': '', 'display_fields': '', 'marketplace': '',
                      'shipment_number': ship_no}
            result_data = awb_direct_insert_shipment_info(result, order_awb_map, user)
            status = result_data['status']
            message = result_data['message']
    return HttpResponse(json.dumps({'status': status, 'message': message}))


def awb_create_shipment(request, user):
    data_dict = copy.deepcopy(ORDER_SHIPMENT_DATA)
    for key, value in request.iteritems():
        if key in ('customer_id', 'marketplace'):
            continue
        elif key in ORDER_SHIPMENT_DATA.keys():
            data_dict[key] = value
    data_dict['user'] = user.id
    data_dict['shipment_date'] = datetime.datetime.now()
    data = OrderShipment(**data_dict)
    data.save()
    return data


def awb_direct_insert_shipment_info(data_params, order_awb_obj, user=''):
    ''' Create Shipment Code '''
    ship_data = data_params['data'];
    user_profile = UserProfile.objects.filter(user_id=user.id)
    try:
        order_shipment = awb_create_shipment(data_params, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create shipment failed for params ' + str(data) + ' error statement is ' + str(e))
        return 'Create shipment Failed'
    status = False
    message = 'Shipment Creation Failed'
    try:
        shipped_orders_dict = {}
        for i in range(0, len(ship_data)):
            if not ship_data[i]['shipping_quantity']:
                continue
            order_ids = ship_data[i]['id']
            if not isinstance(order_ids, list):
                order_ids = [order_ids]
            received_quantity = int(ship_data[i]['shipping_quantity'])
            for order_id in order_ids:
                if received_quantity <= 0:
                    break
                invoice_number = ''
                data_dict = copy.deepcopy(ORDER_PACKAGING_FIELDS)
                shipment_data = copy.deepcopy(SHIPMENT_INFO_FIELDS)
                order_detail = OrderDetail.objects.get(id=order_id, user=user.id, status=0)

                for key, value in ship_data[i].iteritems():
                    if key in data_dict:
                        data_dict[key] = value
                    if key in shipment_data and key != 'id':
                        shipment_data[key] = value

                # Need to comment below 3 lines if shipment scan is ready
                if 'imei_number' in ship_data[i].keys() and ship_data[i]['imei_number']:
                    shipped_orders_dict = insert_order_serial([], {'wms_code': order_detail.sku.wms_code,
                                                                   'imei': ship_data[i]['imei_number']},
                                                              order=order_detail,
                                                              shipped_orders_dict=shipped_orders_dict)
                # Until Here
                order_pack_instance = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id,
                                                                    order_shipment__user=user.id)
                if not order_pack_instance:
                    data_dict['order_shipment_id'] = order_shipment.id
                    data = OrderPackaging(**data_dict)
                    data.save()
                else:
                    data = order_pack_instance[0]
                picked_orders = Picklist.objects.filter(order_id=order_id, status__icontains='picked',
                                                        order__user=user.id)
                order_quantity = int(order_detail.quantity)
                if order_quantity == 0:
                    continue
                elif order_quantity < received_quantity:
                    shipped_quantity = order_quantity
                    received_quantity -= order_quantity
                elif order_quantity >= received_quantity:
                    shipped_quantity = received_quantity
                    received_quantity = 0

                shipment_data['order_shipment_id'] = order_shipment.id
                shipment_data['order_packaging_id'] = data.id
                shipment_data['order_id'] = order_id
                shipment_data['shipping_quantity'] = shipped_quantity
                shipment_data['invoice_number'] = invoice_number
                ship_data = ShipmentInfo(**shipment_data)
                ship_data.save()

                default_ship_track_status = 'Dispatched'
                tracking = ShipmentTracking.objects.filter(shipment_id=ship_data.id, shipment__order__user=user.id,
                                                           ship_status=default_ship_track_status)
                if not tracking:
                    ShipmentTracking.objects.create(shipment_id=ship_data.id, ship_status=default_ship_track_status,
                                                    creation_date=datetime.datetime.now())

                # Need to comment below lines if shipment scan is ready
                if shipped_orders_dict.has_key(int(order_id)):
                    shipped_orders_dict[int(order_id)].setdefault('quantity', 0)
                    shipped_orders_dict[int(order_id)]['quantity'] += float(shipped_quantity)
                else:
                    shipped_orders_dict[int(order_id)] = {}
                    shipped_orders_dict[int(order_id)]['quantity'] = float(shipped_quantity)
                # Until Here

                log.info('Shipemnt Info dict is ' + str(shipment_data))
                ship_quantity = ShipmentInfo.objects.filter(order_id=order_id). \
                    aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
                if not ship_quantity:
                    ship_quantity = 0
                if order_quantity == ship_quantity:
                    order_awb_map = OrderAwbMap.objects.filter(original_order_id=order_detail.original_order_id,
                                                               user=user)
                    if order_awb_map.count():
                        order_awb_map.update(status=2)
                    else:
                        original_order_id = str(order_detail.order_code) + str(order_detail.order_id)
                        order_awb_map = OrderAwbMap.objects.filter(original_order_id=original_order_id, user=user)
                        if order_awb_map.count():
                            order_awb_map.update(status=2)
                if ship_quantity >= int(order_detail.quantity):
                    order_detail.status = 2
                    order_detail.save()
                    for pick_order in picked_orders:
                        setattr(pick_order, 'status', 'dispatched')
                        pick_order.save()
        # Need to comment below lines if shipment scan is ready
        if shipped_orders_dict:
            log.info('Order Status update call for user ' + str(user.username) + ' is ' + str(shipped_orders_dict))
            check_and_update_order_status(shipped_orders_dict, user)
            message = 'Shipment Created Successfully'
            status = True
            # Until Here
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Shipment info saving is failed for params ' + str(data) + ' error statement is ' + str(e))

    return {'status': status, 'message': message}


@csrf_exempt
@get_admin_user
def get_customer_sku(request, user=''):
    data = []
    courier_name = ''
    sku_grouping = request.GET.get('sku_grouping', 'false')
    datatable_view = request.GET.get('view', '')
    insert_st_order_serialsearch_params = {'user': user.id}
    invoice_number = ''
    headers = ('', 'SKU Code', 'Order Quantity', 'Shipping Quantity', 'Pack Reference', '')
    request_data = dict(request.GET.iterlists())
    picked_imeis = []
    search_params = {}
    if 'order_id' in request_data.keys() and not datatable_view == 'ShipmentPickedAlternative':
        search_params['id__in'] = request_data['order_id']
        if datatable_view == 'ShipmentPickedInvoice' and request_data['invoice_number']:
            invoice_number = request_data['invoice_number'][0]
            order_id = list(SellerOrderSummary.objects.filter(order__user=user.id, order__original_order_id__in=request_data['order_id'],full_invoice_number=invoice_number).values_list('order_id',flat=True))
            search_params['id__in'] = order_id
    elif 'order_id' in request_data.keys() and request_data['order_id']:
        filter_order_ids = []
        for order_ids in request_data['order_id']:
            order_id_val = order_ids
            order_id_search = ''.join(re.findall('\d+', order_id_val))
            order_code_search = ''.join(re.findall('\D+', order_id_val))
            fil_ids = list(OrderDetail.objects.filter(Q(order_id=order_id_search, order_code=order_code_search) |
                                                      Q(original_order_id=order_id_val), user=user.id).values_list('id',
                                                                                                                   flat=True))
            filter_order_ids = list(chain(filter_order_ids, fil_ids))
        if filter_order_ids:
            search_params['id__in'] = filter_order_ids
            pi_qs = OrderIMEIMapping.objects.filter(order_id__in=filter_order_ids).values_list('imei_number', flat=True)
            if pi_qs:
                picked_imeis = list(pi_qs)
    ship_no = get_shipment_number(user)
    all_orders = OrderDetail.objects.filter(**search_params)
    for obj in all_orders:
        customer_order_summary = obj.customerordersummary_set.filter()
        if customer_order_summary:
            courier_name = customer_order_summary[0].courier_name
    data = get_shipment_quantity(user, all_orders, sku_grouping)
    if data:
        return HttpResponse(json.dumps({'data': data,
                                        'shipment_id': '',
                                        'display_fields': '',
                                        'marketplace': '',
                                        'shipment_number': ship_no,
                                        'picked_imeis': picked_imeis,
                                        'invoice_number':invoice_number,
                                        'courier_name': courier_name}, cls=DjangoJSONEncoder))
    return HttpResponse(json.dumps({'status': 'No Orders found'}))


@login_required
@get_admin_user
def shipment_pack_ref(request, user=''):
    pack_ref_no = get_incremental(user, 'shipment_pack_ref')
    return HttpResponse(json.dumps({'pack_ref_no': pack_ref_no}))

@login_required
@get_admin_user
def shipment_pack_ref_decrease(request, user=''):
    old_pack_ref_no = request.GET['pack_ref_no']
    pack_ref_no = get_decremental(user, 'shipment_pack_ref', old_pack_ref_no)
    if pack_ref_no == 'Success' :
        return HttpResponse('Success')
    else:
        return  HttpResponse('Failed')

@login_required
@get_admin_user
def check_imei(request, user=''):
    ''' Check IMEI status and serial number mapping with order if it is shipment '''
    status = ''
    sku_code = ''
    quantity = 0
    shipped_orders_dict = {}
    dispatch_summary_imei_details = {}
    is_shipment = request.GET.get('is_shipment', False)
    is_rm_picklist = request.GET.get('is_rm_picklist', False)
    order_id = request.GET.get('order_id', '')
    groupby = request.GET.get('groupby', '')
    cost_check = request.GET.get('cost_check', False)
    log.info('Request params for Check IMEI ' + user.username + ' is ' + str(request.GET.dict()))
    shipping_quantity = 0
    cost_price = 0
    try:
        for key, value in request.GET.iteritems():
            picklist = ''
            if key in ['is_shipment', 'order_id', 'groupby', 'is_rm_picklist', 'cost_check']:
                continue
            sku_code = ''
            order = None
            job_order = None
            imei_filter = {'imei_number': value, 'sku__user': user.id}
            if not is_shipment and not key == 'serial':
                if is_rm_picklist:
                    picklist = RMLocation.objects.get(id=key)
                    job_order = picklist.material_picklist.jo_material.job_order
                    sku_code = picklist.material_picklist.jo_material.material_code.sku_code
                else:
                    picklist = Picklist.objects.get(id=key)
                    if not picklist.order:
                        sku_code = picklist.stock.sku.sku_code
                        order = picklist.storder_set.filter()
                        if order:
                            order = order[0]
                    else:
                        sku_code = picklist.order.sku.sku_code
                        order = picklist.order
            po_mapping, status, imei_data = check_get_imei_details(value, sku_code, user.id, check_type='order_mapping',
                                                                   order=order, job_order=job_order)

            if po_mapping.exists():
                if po_mapping[0].stock_id:
                    dispatch_summary_imei_details['serial_number'] = value
                    dispatch_summary_imei_details['sku_code'] = po_mapping[0].sku.sku_code
                    dispatch_summary_imei_details['cost_price'] = po_mapping[0].stock.unit_price
                    dispatch_summary_imei_details['location'] = po_mapping[0].stock.location.location

            if cost_check and po_mapping[0].purchase_order:
                cost_price = po_mapping[0].purchase_order.open_po.price

            if imei_data.get('wms_code', ''):
                sku_code = imei_data['wms_code']

            if not sku_code and po_mapping:
                sku_code = po_mapping[0].sku.sku_code
            if not po_mapping:
                status = str(value) + ' is invalid Imei number'
            order_mapping = OrderIMEIMapping.objects.filter(po_imei__imei_number=value, sku__user=user.id, status=1)
            if order_mapping:
                if order_mapping[0].order:
                    if order and order_mapping[0].order_id == order.id:
                        status = str(value) + ' is already mapped with this order'
                    else:
                        status = str(value) + ' is already mapped with another order'
                elif order_mapping[0].jo_material:
                    status = str(value) + ' is already mapped with this job order ' + \
                            str(order_mapping[0].jo_material.job_order.job_code)
                elif not order_mapping[0].order and picklist:
                    order = picklist.storder_set.filter()
		    if order:
			status = str(value) + ' is already mapped with an order'
            if is_shipment and po_mapping:
                seller_id = ''
                if po_mapping[0].seller:
                    seller_id = seller_po[0].seller_id
                order_details = ''
                seller_order = ''
                if order_id:
                    order_detail_objs = get_order_detail_objs(order_id, user, search_params={}, all_order_objs=[])
                    order_details = order_detail_objs.filter(sku__sku_code=sku_code)
                    if order_detail_objs and seller_id:
                        seller_order = SellerOrder.objects.filter(seller__user=user.id,
                                                                  order_id__in=order_detail_objs.values_list('id'),
                                                                  seller_id=seller_id)
                    if seller_id and not seller_order:
                        status = 'IMEI Mapped to another Seller'
                if order_details:
                    # qty_data = get_shipment_quantity(user, order_details, False)
                    # if qty_data:
                        #    quantity = qty_data[0]['picked']
                    #    shipping_quantity = qty_data[0].get('shipping_quantity', 0)
                    #    if (float(shipping_quantity) + 1) > quantity:
                    #        status = 'Scanned Quantity exceeding the Picked quantity'

                    if not int(order_details[0].sku_id) == int(po_mapping[0].purchase_order.open_po.sku_id):
                        status = 'IMEI Mapped to the another SKU ' + str(
                            po_mapping[0].purchase_order.open_po.sku.sku_code)
                        # if not status:
                        #    order = order_details[0]
                        #    shipped_orders_dict = insert_order_serial([], {'wms_code': order.sku.wms_code,
                        #                                                   'imei': po_mapping[0].imei_number}, order=order,
                        #                                                   shipped_orders_dict=shipped_orders_dict)
                        #    shipped_orders_dict.setdefault(int(order.id), {}).setdefault('quantity', 0)
                        #    shipped_orders_dict[int(order.id)]['quantity'] += 1
                        #    shipping_quantity += 1
                else:
                    if order_id and value:
                        check_st_order_wise = OrderIMEIMapping.objects.filter(sku__user=user.id, stock_transfer__order_id=order_id, status=1, po_imei__imei_number=value)
                        if not check_st_order_wise:
                            status = 'IMEI not related to this Order'
            if not status:
                status = 'Success'
        if shipped_orders_dict:
            log.info('Order Status update call for user ' + str(user.username) + ' is ' + str(shipped_orders_dict))
            check_and_update_order_status(shipped_orders_dict, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Check IMEI failed for params ' + str(request.POST.dict()) + ' error statement is ' + str(e))
    return HttpResponse(json.dumps({'status': status, 'dispatch_summary_imei_details':dispatch_summary_imei_details , 'data': {'sku_code': sku_code, 'quantity': quantity,
                                                               'shipping_quantity': shipping_quantity,'cost_price':cost_price}}))


@get_admin_user
def print_picklist_excel(request, user=''):
    user = User.objects.get(id=request.GET['warehouse_id'])
    if user.userprofile.industry_type == 'FMCG':
        headers = copy.deepcopy(PICKLIST_EXCEL_FMCG)
    else:
        headers = copy.deepcopy(PICKLIST_EXCEL)
    data_id = request.GET['data_id']
    display_order_id = request.GET.get('display_order_id', 'false')
    if display_order_id == 'false':
        headers.pop('Order ID')
    data, sku_total_quantities, courier_name = get_picklist_data(data_id, user.id)
    all_data = []
    if data and not data[0].get('is_combo_picklist', ''):
        headers.pop('Combo SKU')
    for dat in data:
        val = itemgetter(*headers.values())(dat)
        temp = OrderedDict(zip(headers.keys(), val))
        all_data.append(temp)
    path = print_excel(request, {'aaData': all_data}, headers.keys(), str(data_id))
    return HttpResponse(path)


@get_admin_user
def print_picklist(request, user=''):
    temp = []
    user = User.objects.get(id=request.GET['warehouse_id'])
    title = 'Picklist ID'
    data_id = request.GET['data_id']
    display_order_id = request.GET.get('display_order_id', 'false')
    data, sku_total_quantities, courier_name = get_picklist_data(data_id, user.id)
    date_data = {}
    combo_picklist = False
    if data and data[0].get('is_combo_picklist', ''):
        combo_picklist = True
    picklist_orders = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id),
                                              picklist_number=data_id)
    if picklist_orders:
        date = get_local_date(request.user, picklist_orders[0].creation_date, True)
        date_data['date'] = date.strftime("%d/%m/%Y")
        date_data['time'] = date.strftime("%I:%M%p")
    all_data = {}
    customer_name = ''
    customer_data = list(set(map(lambda d: d.get('customer_name', ''), data)))
    customer_data = filter(lambda x: len(x) > 0, customer_data)
    if customer_data:
        customer_name = ','.join(customer_data)
    customer_address = ''
    if data:
        customer_address = data[0].get('customer_address', '')
    order_ids = 'false'
    order_data = list(set(map(lambda d: d.get('order_no', ''), data)))
    order_data = filter(lambda x: len(x) > 0, order_data)
    original_order_ids = ''
    original_order_data = list(set(map(lambda d: d.get('original_order_id', ''), data)))
    original_order_data = filter(lambda x: len(x) > 0, original_order_data)
    remarks_data = ''
    remarks_data = list(set(map(lambda d: d.get('remarks', ''), data)))
    remarks_data = filter(lambda x: len(x) > 0, remarks_data)
    if remarks_data:
        remarks_data = ','.join(remarks_data)
    market_place = list(set(map(lambda d: d.get('marketplace', ''), data)))
    filtered_market = filter(lambda a: a != "Offline", market_place)
    if not filtered_market:
        marketplace = ''
    else:
        marketplace = ','.join(market_place)

    total = 0
    total_price = 0
    type_mapping = SkuTypeMapping.objects.filter(user=user.id)
    for record in data:
        for mapping in type_mapping:
            if mapping.prefix in record['wms_code']:
                cond = (mapping.item_type)
                all_data.setdefault(cond, [0, 0])
                all_data[cond][0] += record['reserved_quantity']
                if not record['order_id'] in temp:
                    all_data[cond][1] += record['invoice_amount']
                    temp.append(record['order_id'])
                break
        else:
            total += record['reserved_quantity']
            if not record['order_id'] in temp:
                total_price += record['invoice_amount']
                temp.append(record['order_id'])

    for key, value in all_data.iteritems():
        total += float(value[0])
        total_price += float(value[1])
    show_picklist_display_address = get_misc_value('picklist_display_address', user.id)
    if show_picklist_display_address == "false":
        customer_address = ''
    fmcg_industry_type = False
    if user.userprofile.industry_type == 'FMCG':
        headers = copy.deepcopy(PRINT_OUTBOUND_PICKLIST_HEADERS_FMCG)
        fmcg_industry_type = True
    else:
        headers = copy.deepcopy(PRINT_OUTBOUND_PICKLIST_HEADERS)
    if combo_picklist:
        headers = ('Combo SKU',) + headers
    if display_order_id == 'true':
        if len(original_order_data):
            order_ids = ','.join(original_order_data)
        elif len(order_data):
            order_ids = ','.join(order_data)
        headers = ('Order ID',) + headers
    return render(request, 'templates/toggle/print_picklist.html',
                  {'data': data, 'all_data': all_data, 'headers': headers,
                   'picklist_id': data_id, 'total_quantity': total,
                   'total_price': total_price, 'picklist_id': data_id,'fmcg_industry_type':fmcg_industry_type,
                   'customer_name': customer_name, 'customer_address': customer_address, 'order_ids': order_ids,
                   'marketplace': marketplace, 'date_data': date_data, 'remarks': remarks_data, 'user': user,
                   'display_order_id': display_order_id, 'courier_name': courier_name,
                   'combo_picklist': combo_picklist})


@csrf_exempt
def get_batch_picked(data_ids, user_id):
    data = {}
    batch_data = {}
    for data_id in data_ids:
        picklist_orders = Picklist.objects.filter(Q(stock__sku__user=user_id) | Q(order__user=user_id),
                                                  picklist_number=data_id)
        if picklist_orders[0].status != 'batch_picked':
            return data

        for order in picklist_orders:
            wms_code = ''
            if order.stock:
                wms_code = order.stock.sku.wms_code
            elif order.order:
                wms_code = order.order.sku.wms_code
            if order.order:
                marketplace = order.order.marketplace
                invoice_amount = order.order.invoice_amount
            else:
                st_order = STOrder.objects.filter(picklist_id=order.id)
                marketplace = ''
                invoice_amount = st_order[0].stock_transfer.invoice_amount
            if order.picked_quantity <= 0:
                continue
            match_condition = (marketplace, wms_code)
            if match_condition not in batch_data:

                batch_data[match_condition] = {'wms_code': wms_code, 'picked_quantity': order.picked_quantity,
                                               'invoice_amount': invoice_amount}
            else:
                batch_data[match_condition]['invoice_amount'] += invoice_amount
                batch_data[match_condition]['picked_quantity'] += order.picked_quantity

    for key, value in batch_data.iteritems():
        data.setdefault(key[0], [])
        data[key[0]].append(value)

    return data


@csrf_exempt
@login_required
@get_admin_user
def marketplace_segregation(request, user=''):
    data_id = request.GET.get('data_id', [])
    data = get_batch_picked(data_id.split(','), user.id)
    return render(request, 'templates/toggle/print_segregation.html', {'data': data, 'picklist_number': data_id,
                                                                       'headers': ('WMS Code', 'Picked Quantity',
                                                                                   'invoice_amount')})


@get_admin_user
def get_orders(request, orders, user=''):
    data = []
    users = ''
    user_list = []
    options = {}
    for order in orders:
        admin_user = UserGroups.objects.filter(Q(admin_user_id=user.id) | Q(user_id=user.id))
        if not admin_user:
            break
        admin_user = admin_user[0].admin_user
        user_list.append(admin_user)
        wms_users = UserGroups.objects.filter(admin_user_id=user.id)
        for u in wms_users:
            user_list.append(u.user)
        for w_user in user_list:
            if user.id == w_user.id:
                continue
            total_quantity = 0
            order_quantity = 0
            reserved_quantity = 0
            sku_master = SKUMaster.objects.filter(sku_code=order.sku.sku_code, user=w_user.id)
            stock_data = StockDetail.objects.filter(sku__user=w_user.id, sku__sku_code=order.sku.sku_code).aggregate(
                Sum('quantity'))
            order_data = OrderDetail.objects.filter(user=w_user.id, sku__sku_code=order.sku.sku_code,
                                                    status=1).aggregate(Sum('quantity'))
            reserved = PicklistLocation.objects.filter(picklist__status__icontains='open',
                                                       picklist__order__user=w_user.id,
                                                       picklist__order__sku__sku_code=order.sku.sku_code).aggregate(
                Sum('reserved'))
            if None not in stock_data.values():
                total_quantity = stock_data['quantity__sum']
            if None not in order_data.values():
                order_quantity = order_data['quantity__sum']
            if None not in reserved.values():
                reserved_quantity = reserved['reserved__sum']
            quantity = total_quantity - order_quantity - reserved_quantity
            if sku_master:
                options[w_user.username] = quantity

        data.append({'order_id': order.order_id, 'wms_code': order.sku.wms_code, 'title': order.sku.sku_desc,
                     'quantity': order.quantity, 'id': order.id})

    return (data, options)


@csrf_exempt
@login_required
@get_admin_user
def transfer_order(request, user=''):
    headers = ['Order ID', 'WMS Code', 'Title', 'Quantity', 'Transfer To']
    orders = []
    for key, value in request.POST.iteritems():
        order = OrderDetail.objects.get(id=key, user=user.id, status=1)
        orders.append(order)

    data, options = get_orders(request, orders)
    if not data:
        return HttpResponse("No Users Found")
    return HttpResponse(json.dumps({'data': data, 'options': options}))


@csrf_exempt
@login_required
@get_admin_user
def batch_transfer_order(request, user=''):
    orders = []
    headers = ['Order ID', 'WMS Code', 'Title', 'Quantity', 'Transfer To']
    for key, value in request.POST.iteritems():
        batch_orders = OrderDetail.objects.filter(sku__sku_code=key, user=user.id, status=1)
        for order in batch_orders:
            orders.append(order)

    data, options = get_orders(request, orders)
    if not data:
        return HttpResponse("No Users Found")

    return HttpResponse(json.dumps({'data': data, 'options': options}))


@csrf_exempt
@login_required
@get_admin_user
def confirm_transfer(request, user=''):
    for key, value in request.POST.iteritems():
        stock = re.findall('\\d+', value)[-1]
        username = value.split('(')[0].strip()
        order = OrderDetail.objects.filter(id=key, user=user.id)
        if not order:
            continue
        order = order[0]
        user = User.objects.get(username=username)
        sku_master = SKUMaster.objects.get(sku_code=order.sku.sku_code, user=user.id)
        setattr(order, 'user', user.id)
        setattr(order, 'sku_id', sku_master.id)
        order.save()

    return HttpResponse('Order Transferred Successfully')


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def mr_generate_picklist(request, user=''):
    reversion.set_user(request.user)
    user_picknumber_dict = {}
    out_of_stock = []
    enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
    for key, value in request.POST.iteritems():
        if key == 'enable_damaged_stock':
            continue
        try:
            user = User.objects.get(id=int(value))
        except Exception as e:
            user = User.objects.get(id=value)
        if check_consumption_configuration([user.id], extra_flag=True):
            return HttpResponse("MR Picklist Generation Disable Due to Closing Stock Updations")
        if user.username in user_picknumber_dict.keys():
            picklist_number = user_picknumber_dict[user.username]
        else:
            picklist_number = get_picklist_number(user)
        picklist_exclude_zones = get_exclude_zones(user)
        sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
        if enable_damaged_stock == 'true':
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0,
                                                                                    location__zone__zone__in=[
                                                                                        'DAMAGED_ZONE'])
        else:
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
                                        location__zone__zone__in=picklist_exclude_zones).filter(sku__user=user.id, quantity__gt=0, status=1)

        company_user = get_company_admin_user(user)
        switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                       'fifo_switch': get_misc_value('fifo_switch', user.id),
                       'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                       'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id),
                       'allow_partial_picklist': get_misc_value('allow_partial_picklist', company_user.id)}
        if switch_vals['fifo_switch'] == 'true':
            stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
                'receipt_date')
            stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
        elif user.userprofile.industry_type == 'FMCG':
            stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).\
                                    order_by('batch_detail__expiry_date')
            stock_detail2 = sku_stocks.filter(quantity__gt=0, location__zone__zone='TEMP_ZONE').\
                order_by('batch_detail__expiry_date')
        else:
            stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
                'location_id__pick_sequence')
            stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
        sku_stocks = stock_detail1 | stock_detail2
        seller_stocks = SellerStock.objects.filter(seller__user=user.id, stock__quantity__gt=0).values('stock_id', 'seller_id')


        orders_data = StockTransfer.objects.filter(order_id=key, status=1, sku__user=user.id)
        if orders_data and orders_data[0].st_seller:
            seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(orders_data[0].st_seller_id),
                                       seller_stocks)
            if seller_stock_dict:
                sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
                sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
            else:
                sku_stocks = sku_stocks.filter(id=0)
        stock_status, picklist_number = picklist_generation(orders_data, enable_damaged_stock, picklist_number, user,
                                                            sku_combos, sku_stocks, switch_vals)
        user_picknumber_dict[user.username] = picklist_number
        if stock_status:
            out_of_stock = out_of_stock + stock_status
    if len(user_picknumber_dict.keys()) == 1:
        order_typ = 'MR'
        current_user = user_picknumber_dict.keys()[0]
        if out_of_stock:
            stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
        else:
            stock_status = ''
        picklist_number = user_picknumber_dict[current_user]
        user = User.objects.get(username=current_user)
        check_picklist_number_created(user, picklist_number + 1)
        order_status = ''
        data, sku_total_quantities, courier_name = get_picklist_data(picklist_number + 1, user.id)
        if data:
            order_status = data[0]['status']
    else:
        data = []
        stock_status , order_status = '', ''
        picklist_number = 0
        order_typ = ''
        current_user = ''
    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status,
                                    'order_status': order_status, 'current_user': current_user, 'order_typ': 'MR'}))


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def st_generate_picklist(request, user=''):
    reversion.set_user(request.user)
    user_picknumber_dict = {}
    out_of_stock = []
    enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
    for key, value in request.POST.iteritems():
        if key =='enable_damaged_stock':
            continue
        try:
            user = User.objects.get(id=int(value))
        except Exception as e:
            user = User.objects.get(id=value)
        if check_consumption_configuration([user.id], extra_flag=True):
            return HttpResponse("Stock Transfer Picklist Generation Disable Due to Closing Stock Updations")
        if user.username in user_picknumber_dict.keys():
            picklist_number = user_picknumber_dict[user.username]
        else:
            picklist_number = get_picklist_number(user)
        picklist_exclude_zones = get_exclude_zones(user)
        sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
        if enable_damaged_stock == 'true':
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0,
                                                                                    location__zone__zone__in=[
                                                                                        'DAMAGED_ZONE'])
        else:
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
                                        location__zone__zone__in=picklist_exclude_zones).filter(sku__user=user.id, quantity__gt=0, status=1)
        company_user = get_company_admin_user(user)
        switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                       'fifo_switch': get_misc_value('fifo_switch', user.id),
                       'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                       'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id),
                       'allow_partial_picklist': get_misc_value('allow_partial_picklist', company_user.id)}
        if switch_vals['fifo_switch'] == 'true':
            stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
                'receipt_date')
            stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
        elif user.userprofile.industry_type == 'FMCG':
            stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).\
                                    order_by('batch_detail__expiry_date')
            stock_detail2 = sku_stocks.filter(quantity__gt=0, location__zone__zone='TEMP_ZONE').\
                order_by('batch_detail__expiry_date')
        else:
            stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
                'location_id__pick_sequence')
            stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
        sku_stocks = stock_detail1 | stock_detail2
        seller_stocks = SellerStock.objects.filter(seller__user=user.id, stock__quantity__gt=0).values('stock_id', 'seller_id')

        orders_data = StockTransfer.objects.filter(order_id=key, status=1, sku__user=user.id)
        if orders_data and orders_data[0].st_seller:
            seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(orders_data[0].st_seller_id),
                                       seller_stocks)
            if seller_stock_dict:
                sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
                sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
            else:
                sku_stocks = sku_stocks.filter(id=0)
        stock_status, picklist_number = picklist_generation(orders_data, enable_damaged_stock, picklist_number, user,
                                                            sku_combos, sku_stocks, switch_vals)
        user_picknumber_dict[user.username] = picklist_number
        if stock_status:
            out_of_stock = out_of_stock + stock_status

    if len(user_picknumber_dict.keys()) == 1:
        order_typ = 'ST_INTRA'
        current_user = user_picknumber_dict.keys()[0]
        if out_of_stock:
            stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
        else:
            stock_status = ''
        picklist_number = user_picknumber_dict[current_user]
        user = User.objects.get(username=current_user)
        check_picklist_number_created(user, picklist_number + 1)
        order_status = ''
        data, sku_total_quantities, courier_name = get_picklist_data(picklist_number + 1, user.id)
        if data:
            order_status = data[0]['status']
    else:
        data = []
        stock_status , order_status = '', ''
        picklist_number = 0
        order_typ = ''
        current_user = ''
    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status,
                                    'order_status': order_status, 'current_user': current_user, 'order_typ': 'ST_INTRA'}))


@csrf_exempt
@get_admin_user
def get_customer_data(request, user=''):
    data_id = request.GET['id']
    try:
        data_id = int(data_id)
    except:
        return HttpResponse('')
    cust_details = CustomerMaster.objects.filter(customer_id=data_id, user=user.id)
    if cust_details:
        data = cust_details[0]
        return HttpResponse(json.dumps({'name': data.name, 'phone_number': data.phone_number, 'email_id': data.email_id,
                                        'address': data.address}))
    else:
        return HttpResponse('')


@get_admin_user
def update_cartdata_for_approval(request, user=''):
    message = 'success'
    admin_items, items = [], []
    approval_status = request.POST.get('approval_status', '')
    approving_user_role = request.POST.get('approving_user_role', '')
    approve_id = request.POST.get('approve_id', '')
    if not approve_id:
        return HttpResponse('Approve Id missing')
    approve_data = ApprovingOrders.objects.filter(user_id=user.id, approve_id=approve_id)
    if approve_data:
        approve_data.update(approval_status=approval_status,
                         approving_user_role=approving_user_role,
                         approve_id=approve_id)
        #mail to Admin and normal user
        for data in approve_data:
            inv_amt = (data.unit_price * data.quantity) + data.tax
            admin_items.append([data.sku.sku_desc, data.quantity, inv_amt])
            items.append([data.sku.sku_desc, data.quantity])
        customer = CustomerUserMapping.objects.get(user_id=approve_data[0].customer_user.id)
        customer = CustomerMaster.objects.filter(id=customer.customer_id)
        customer_id = customer[0].customer_id
        customer_name = customer[0].name
        normal_user_mail_id = customer.values_list('email_id', flat=True)
        role = 'HOD' if approving_user_role == 'Admin' else 'Admin'
        admin_mail_id = CustomerMaster.objects.filter(user=user.id, role=role)\
                                              .values_list('email_id', flat=True)
        admin_headers = ['Product Details', 'Ordered Quantity', 'Total']
        user_headres = ['Product Details', 'Ordered Quantity']
        admin_data_dict = {'customer_name': customer_name, 'items': admin_items, 'approving_user_role': approving_user_role,
                           'headers': admin_headers, 'role': role, 'status': approval_status}
        data_dict = {'customer_name': customer_name, 'items': items, 'approving_user_role': approving_user_role,
                     'headers': user_headres, 'role': 'Normal Customer', 'status': approval_status}
        if approval_status == 'accept':
            t_admin = loader.get_template('templates/customer_portal/order_for_approval.html')
        else:
            t_admin = loader.get_template('templates/customer_portal/order_approved_hod.html')
        rendered_admin = t_admin.render(admin_data_dict)
        t_user = loader.get_template('templates/customer_portal/order_approved.html')
        rendered_user = t_user.render(data_dict)
        if admin_mail_id:
            if approval_status == 'accept':
                send_mail(admin_mail_id, 'Order Approval Request, Customer: %s' % customer_name, rendered_admin)
            else:
                send_mail(admin_mail_id, 'Order Rejected by %s' % approving_user_role, rendered_admin)
        if normal_user_mail_id:
            send_mail(normal_user_mail_id, 'Your Order status got changed', rendered_user)

    else:
        message = 'failure'

    return HttpResponse(json.dumps({'message': message}))


def get_order_approval_statuses(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                                filters):
    lis = ['approve_id', 'customer_user__username', 'approval_status', 'creation_date_only']
    result_values = ['customer_user__username', 'approval_status',
                     'approving_user_role', 'approve_id']
    cust_obj = CustomerUserMapping.objects.filter(user_id=request.user.id)
    if cust_obj:
        customer_role = cust_obj[0].customer.role
    else:
        customer_role = ''
    if customer_role.lower() == 'user':
        user_filters = {'user_id': user.id, 'customer_user_id': request.user.id}
    else:
        user_filters = {'user_id': user.id}
    search_params = get_filtered_params(filters, lis)
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        cart_data = ApprovingOrders.objects.filter(**user_filters).filter(**search_params)\
                                   .values(*result_values).distinct()\
                                   .annotate(creation_date_only=Cast('creation_date', DateField()))\
                                   .order_by(order_data)
    else:
        cart_data = ApprovingOrders.objects.filter(**user_filters)\
                                   .values(*result_values).distinct()\
                                   .annotate(creation_date_only=Cast('creation_date', DateField()))\
                                   .order_by(order_data)
    temp_data['recordsTotal'] = cart_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data in cart_data[start_index: stop_index]:
        #shipment_date = data['shipment_date'].strftime('%d-%m-%Y') if data['shipment_date'] else ''
        temp_data['aaData'].append(
            OrderedDict((('user', data['customer_user__username']),
                         ('date', data['creation_date_only'].strftime('%d-%m-%Y')),
                         ('status', data['approval_status']),
                         ('approve_id', data['approve_id']),
                         ('approving_user_role', data['approving_user_role']),
                       )))
        """image = data.sku.image_url
        sku_code = data.sku.sku_code
        desc = data.sku.sku_desc
        price = data.unit_price
        shipment_date = data.shipment_date.strftime('%d-%m-%Y') if data.shipment_date else ''
        temp_data['aaData'].append(
            OrderedDict((('user', data.customer_user.username), ('date', data.creation_date.strftime('%d-%m-%Y')),
                         ('status', data.approval_status), ('image', image), ('sku_code', sku_code),
                         ('desc', desc), ('price', price), ('tax', data.tax), ('quantity', data.quantity),
                         ('approve_id', data.approve_id), ('approving_user_role', data.approving_user_role),
                         ('shipment_date',shipment_date)
                         )))"""

@get_admin_user
@login_required
def order_approval_sku_details(request, user=''):
    approve_id = request.GET.get('approve_id', '')
    sku_details_list = []
    result_data = ['sku__sku_code', 'sku__sku_desc', 'sku__image_url',
                   'tax', 'quantity', 'unit_price', 'approval_status',
                   'shipment_date', 'approve_id']
    approving_orders = ApprovingOrders.objects.filter(approve_id=approve_id)\
                                      .values(*result_data)
    for item in approving_orders:
        sku_details = {'sku_code': item['sku__sku_code'],
                       'sku_desc': item['sku__sku_desc'],
                       'price': item['unit_price'],
                       'tax': item['tax'],
                       'quantity': item['quantity'],
                       'image': item['sku__image_url']}
        sku_details_list.append(sku_details)
    return HttpResponse(json.dumps({'status': 'success', 'data': sku_details_list}))

@get_admin_user
@csrf_exempt
@login_required
def after_admin_approval(request, user=''):
    status = update_cartdata_for_approval(request, user= '')
    message = 'success'
    admin_items, items = [], []
    approval_status = request.POST.get('approval_status', '')
    user_id = user.id
    order_code_prefix = get_order_prefix(user.id)
    approve_id = request.POST.get('approve_id', '')
    #sku_code = request.POST.get('sku_code', '')
    #quantity = request.POST.get('quantity', '')
    #price = request.POST.get('price', '')
    #tax = request.POST.get('tax', '')
    #title = request.POST.get('sku_desc', '')
    shipment_date = request.POST.get('shipment_date',None)
    order_summary = create_orders_data(request, user='')
    order_id = get_order_id(user.id)
    if shipment_date:
        shipment_date = datetime.datetime.strptime(shipment_date, "%m/%d/%Y")
        shipment_date = datetime.datetime.combine(shipment_date, datetime.datetime.min.time())
    approve_status = ApprovingOrders.objects.filter(user_id=user.id, approve_id=approve_id, approval_status='accept')
    if shipment_date:
        approve_status.update(shipment_date =shipment_date)

    for ap_status in approve_status:
        price = ap_status.unit_price
        quantity = ap_status.quantity
        customer_user = CustomerUserMapping.objects.filter(user=ap_status.customer_user_id)
        customer_user_id = ''
        if customer_user:
            customer_user_id = customer_user[0].customer.customer_id
        if order_summary:
            if not price:
                price = 0
            amt = int(quantity) * int(price)
            invoice_amount = amt + ((amt/100) * (ap_status.cgst_tax + ap_status.sgst_tax + ap_status.igst_tax + ap_status.igst_tax))
            admin_items.append([ap_status.sku.sku_desc, quantity, invoice_amount])
            items.append([ap_status.sku.sku_desc, quantity])
            detail_check = OrderDetail.objects.filter(order_id= order_id,sku_id= ap_status.sku_id,user = user.id,order_code = order_code_prefix)
            data_dict = {'order_id':order_id, 'customer_id':customer_user_id, 'user':user_id,
            'title':ap_status.sku.sku_desc, 'quantity':quantity,'invoice_amount':invoice_amount,
            'sku_id':ap_status.sku_id,'shipment_date':shipment_date,'order_code':order_code_prefix,
            'original_order_id':order_code_prefix+str(order_id), 'status':1}
            if detail_check:
                detail_check.update(quantity= quantity,invoice_amount= invoice_amount)
            else:
                order = OrderDetail.objects.create(**data_dict)
                order.save()
                CustomerOrderSummary.objects.create(order_id = order.id,cgst_tax = ap_status.cgst_tax, sgst_tax = ap_status.sgst_tax,
                igst_tax = ap_status.igst_tax, utgst_tax = ap_status.utgst_tax, inter_state = ap_status.inter_state)
    #mail to HOD and normal user
    customer_id = customer_user[0].customer_id
    customer = CustomerMaster.objects.filter(id=customer_id)
    customer_name = customer[0].name
    normal_user_mail_id = customer.values_list('email_id', flat=True)
    hod_mail_id = CustomerMaster.objects.filter(user=user.id, role='HOD')\
                                         .values_list('email_id', flat=True)
    hod_headers = ['Product Details', 'Ordered Quantity', 'Total']
    user_headres = ['Product Details', 'Ordered Quantity']
    hod_data_dict = {'customer_name': customer_name, 'items': admin_items, 'approving_user_role': 'Admin',
                    'headers': hod_headers, 'role': 'HOD', 'status': approval_status}
    user_data_dict = {'customer_name': customer_name, 'items': items,
                'headers': user_headres, 'role': 'Normal Customer', 'status': approval_status}
    t_admin = loader.get_template('templates/customer_portal/order_approved_hod.html')
    rendered_admin = t_admin.render(hod_data_dict)
    t_user = loader.get_template('templates/customer_portal/order_approved.html')
    rendered_user = t_user.render(user_data_dict)
    if hod_mail_id and approval_status == 'accept':
        send_mail(hod_mail_id, 'Order Approved by Admin for Customer: %s' % customer_name, rendered_admin)
    if normal_user_mail_id:
        send_mail(normal_user_mail_id, 'Your Order status got changed', rendered_user)



    return HttpResponse(json.dumps({'message': message}))
@get_admin_user
def update_orders_for_approval(request, user=''):
    message = 'success'
    items, user_items = [], []
    cart_data = CustomerCartData.objects.filter(user_id=user.id, customer_user_id=request.user.id)
    if cart_data:
        try:
            approve_id = get_approval_id(request.user.id)
            ap_orders = ApprovingOrders.objects.filter(user_id=user.id, customer_user_id=request.user.id,
                                                       approve_id=approve_id)
            for cart_item in cart_data:
                approve_orders_map = {'user_id': user.id, 'customer_user_id': request.user.id,
                                      'approve_id': approve_id, 'approval_status': 'pending',
                                      'approving_user_role': 'hod', 'sku_id': cart_item.sku_id,
                                      'quantity': cart_item.quantity, 'unit_price': cart_item.levelbase_price,
                                      'tax': cart_item.tax, 'inter_state': cart_item.inter_state,
                                      'cgst_tax': cart_item.cgst_tax, 'sgst_tax': cart_item.sgst_tax,
                                      'igst_tax': cart_item.igst_tax, 'utgst_tax': cart_item.utgst_tax
                                      }
                if not ap_orders:
                    ApprovingOrders.objects.create(**approve_orders_map)
                inv_amt = (cart_item.levelbase_price * cart_item.quantity) + cart_item.tax
                items.append([cart_item.sku.sku_desc, cart_item.quantity, inv_amt])
                user_items.append([cart_item.sku.sku_desc, cart_item.quantity])
        except:
            log.info('Update Orders Approval Failed')
        else:
            #mail to Admin and normal user
            mail_ids = CustomerMaster.objects.filter(user=user.id, role='Admin')\
                                             .values_list('email_id', flat=True)
            customer_id = CustomerUserMapping.objects.get(user_id=request.user.id).customer_id
            user_mail_id = CustomerMaster.objects.filter(id=customer_id).values_list('email_id', flat=True)
            headers = ['Product Details', 'Ordered Quantity', 'Total']
            user_headers = ['Product Details', 'Ordered Quantity']
            data_dict = {'customer_name': request.user.username, 'items': items,
                         'headers': headers, 'role': 'HOD'}
            user_data_dict = {'customer_name': request.user.username, 'items': user_items,
                              'headers': user_headers, 'role': 'Normal User'}
            t = loader.get_template('templates/customer_portal/order_for_approval.html')
            rendered = t.render(data_dict)
            t_user = loader.get_template('templates/customer_portal/order_placed.html')
            rendered_user = t_user.render(user_data_dict)
            if mail_ids:
                send_mail(mail_ids, 'Order Approval Request, Customer: %s' % request.user.username, rendered)
            if user_mail_id:
                send_mail(user_mail_id, 'Order Placed Successfully', rendered_user)

            cart_data.delete()
    else:
        message = 'failure'

    return HttpResponse(json.dumps({'message': message}))


@fn_timer
def validate_order_form(myDict, request, user):
    invalid_skus = []
    invalid_quantities = []
    less_stocks = []

    # Purchase Order checks
    po_status = ''
    po_imeis = []

    status = ''
    temp_distinct_skus = []
    direct_dispatch = request.POST.get('direct_dispatch', '')
    if not myDict['shipment_date'][0]:
        status = 'Shipment Date should not be empty'
    seller_id = request.POST.get('seller_id', '')
    seller_status = ""
    sor_id_status = ""
    if request.POST.has_key('seller_id'):
        if not seller_id:
            seller_status = 'Seller should not be emtpy'
        else:
            seller_data = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
            if not seller_data:
                seller_status = 'Seller not found'
        sor_id = request.POST.get('sor_id', '')
        if not sor_id:
            sor_id_status = 'SOR ID should not be emtpy'
        else:
            seller_order = SellerOrder.objects.filter(order__user=user.id, sor_id=sor_id)
            if seller_order:
                sor_id_status = 'SOR ID already userd'
    sku_masters = SKUMaster.objects.filter(user=user.id).values('sku_code', 'wms_code', 'id', 'sku_desc')
    all_sku_codes = {}
    if myDict.get('po_number', '') and myDict['po_number'][0]:
        po_number = myDict['po_number'][0]
        if '_' in po_number:
            po_number = po_number.split('_')[-1]
            po_imei_objs = POIMEIMapping.objects.filter(purchase_order__order_id=po_number,
                                                        sku__user=user.id)
            po_imeis = dict(po_imei_objs.values_list('purchase_order__open_po__sku__sku_code').annotate(Count('id')))

            if not po_imeis:
                po_status = "Purchase Order does not exists"

            elif seller_id:
                seller_po = SellerPO.objects.filter(seller__user=user.id,
                                                    open_po_id=po_imei_objs[0].purchase_order.open_po_id)
                if seller_po and str(seller_po[0].seller.seller_id) != str(seller_id):
                    po_status = "Purchase Order Mapped to another Seller"
        else:
            po_status = "Invalid Purchase Order Number"

    for i in range(0, len(myDict['sku_id'])):
        if not myDict['sku_id'][i]:
            continue
        stock_check = True
        sku_master = sku_masters.filter(Q(sku_code=myDict['sku_id'][i]) | Q(wms_code=myDict['sku_id'][i]))
        if not sku_master:
            invalid_skus.append(myDict['sku_id'][i])
            stock_check = False
        else:
            all_sku_codes[i] = sku_master[0]
            temp_distinct_skus.append(sku_master[0]['wms_code'])
        try:
            value = float(myDict['quantity'][i])
        except:
            stock_check = False
            if myDict['sku_id'][i]:
                invalid_quantities.append(myDict['sku_id'][i])

        if not po_status and po_imeis and stock_check:
            po_qty = po_imeis.get(myDict['sku_id'][i], '')
            if po_qty:
                if float(po_qty) != float(value):
                    po_status = "Order Quantity is not matching with PO quantity"
                else:
                    del po_imeis[myDict['sku_id'][i]]

        if stock_check and myDict.get('location', ''):
            avail_stock = get_sku_available_dict(user, sku_code=sku_master[0]['sku_code'],
                                                 location=myDict['location'][i], available=True)
            if float(avail_stock) < float(value):
                less_stocks.append(str(myDict['sku_id'][i]) + '-' + str(myDict['location'][i]))

    if invalid_skus:
        status = " Invalid sku codes are " + ",".join(invalid_skus)
    if invalid_quantities:
        status += " Quantities missing sku codes are " + ",".join(invalid_quantities)
    if less_stocks:
        status += " Insufficient stock combindations are " + ",".join(less_stocks)

    if po_status:
        status += " " + po_status
    if not po_status and po_imeis:
        status += " Number of Order SKUS is not matching with Number of PO SKUS"
    if seller_status:
        status += " " + seller_status
    if sor_id_status:
        status += " " + sor_id_status

    return status, all_sku_codes, list(set(temp_distinct_skus))


def create_order_json(order_detail, json_dat={}, ex_image_url={}):
    for key, value in json_dat.get('vendors_list', {}).iteritems():
        OrderMapping.objects.create(mapping_id=value, mapping_type=key, order_id=order_detail.id)
    keys_list = ['vendors_list', 'remarks', 'sku_code', 'quantity', 'description']
    for key in keys_list:
        if json_dat.get(key, ''):
            del json_dat[key]

    if json_dat.get('image_url', ''):
        temp_url = json_dat['image_url']
        if ex_image_url.get(json_dat['image_url'], ''):
            json_dat['image_url'] = ex_image_url[json_dat['image_url']]
        elif os.path.exists(json_dat['image_url'][1:]):
            new_path = 'static/images/co_images/' + str(order_detail.user)
            if not os.path.exists(new_path):
                os.makedirs(new_path)
            extension = json_dat['image_url'].split('.')[-1]
            new_file_path = new_path + str(order_detail.id) + '.' + extension
            shutil.move(json_dat['image_url'][1:], new_file_path)
            if os.path.exists(json_dat['image_url'][1:]):
                os.remove(json_dat['image_url'][1:])
            json_dat['image_url'] = '/' + new_file_path
            ex_image_url[temp_url] = json_dat['image_url']
        else:
            json_dat['image_url'] = ''
    if json_dat:
        OrderJson.objects.create(order_id=order_detail.id, json_data=json.dumps(json_dat),
                                 creation_date=datetime.datetime.now())
    return ex_image_url


def get_order_customer_details(order_data, request):
    customer_user = CustomerUserMapping.objects.filter(user_id=request.user.id)
    if customer_user:
        order_data['customer_id'] = customer_user[0].customer.customer_id
        order_data['customer_name'] = customer_user[0].customer.name
        order_data['telephone'] = customer_user[0].customer.phone_number
        order_data['email_id'] = customer_user[0].customer.email_id
        order_data['address'] = customer_user[0].customer.address
    return order_data


def check_and_raise_po(generic_order_id, cm_id, ord_det_id=None):
    ''' it will create purchese order in warehouse '''
    generic_data = GenericOrderDetailMapping.objects.filter(generic_order_id=generic_order_id, customer_id=cm_id)
    if ord_det_id:
        generic_data = generic_data.filter(orderdetail_id=ord_det_id)
    if not generic_data:
        log.info("No Order Found")
        return "No Order Found"
    mapping = WarehouseCustomerMapping.objects.filter(customer=cm_id, status=1)
    if not mapping:
        return "Customer Don't Have Warehouse"
    mapping = mapping[0]
    wh_list = list(generic_data.values_list('cust_wh_id', flat=True).distinct())
    user_profile = UserProfile.objects.filter(user_id=mapping.warehouse.id)
    po_sub_user_prefix = get_misc_value('po_sub_user_prefix', mapping.warehouse.id)
    for wh in wh_list:
        po_data = generic_data.filter(cust_wh_id=wh)
        supplier = NetworkMaster.objects.filter(dest_location_code_id=mapping.warehouse.id, source_location_code_id=wh)
        if not supplier:
            continue
        supplier = supplier[0]
        if not supplier.supplier:
            continue
        po_id = get_purchase_order_id(mapping.warehouse) + 1
        if po_sub_user_prefix == 'true':
            po_id = update_po_order_prefix(mapping.warehouse, po_id)
        for data in po_data:
            purchase_data = copy.deepcopy(PO_DATA)
            po_sku_data = copy.deepcopy(PO_SUGGESTIONS_DATA)
            sku_data = OrderDetail.objects.get(id=data.orderdetail.id)
            sku = SKUMaster.objects.get(wms_code=sku_data.sku.sku_code, user=mapping.warehouse.id)
            po_sku_data['supplier_id'] = supplier.supplier.id
            po_sku_data['wms_code'] = sku.sku_code
            po_sku_data['sku_id'] = sku.id
            po_sku_data['order_quantity'] = data.quantity
            po_sku_data['price'] = sku_data.unit_price
            po_sku_data['measurement_unit'] = 'UNITS'
            po_sku_data['status'] = 0
            create_po = OpenPO(**po_sku_data)
            create_po.save()
            purchase_data['open_po_id'] = create_po.id
            purchase_data['order_id'] = po_id
            if user_profile:
                purchase_data['prefix'] = user_profile[0].prefix
            order = PurchaseOrder(**purchase_data)
            order.po_number = get_po_reference(order)
            order.save()
        check_prefix = ''
        if user_profile:
            check_prefix = user_profile[0].prefix
        check_purchase_order_created(mapping.warehouse, po_id, check_prefix)


def fetch_asn_stock(dist_user_id, sku_code, req_stock):
    segregate_stock_wh_map = OrderedDict()
    today_filter = datetime.datetime.today()
    threeday_filter = today_filter + datetime.timedelta(days=10) #Client asked to change days. So changing date values only.
    thirtyday_filter = today_filter + datetime.timedelta(days=45)
    hundred_day_filter = today_filter + datetime.timedelta(days=90)
    source_whs = list(NetworkMaster.objects.filter(dest_location_code_id=dist_user_id).filter(
        source_location_code__userprofile__warehouse_level=1).values_list('source_location_code_id',
                                                                          flat=True).order_by('lead_time',
                                                                                              'priority'))
    ints_filters = {'quantity__gt': 0, 'sku__sku_code': sku_code, 'sku__user__in': source_whs, 'status': 'open'}
    asn_qs = ASNStockDetail.objects.filter(**ints_filters)
    intr_obj_3days_qs = asn_qs.filter(Q(arriving_date__lte=threeday_filter) | Q(asn_po_num='NON_KITTED_STOCK'))
    intr_obj_3days_ids = intr_obj_3days_qs.values_list('id', flat=True)
    asn_res_3days_qs = ASNReserveDetail.objects.filter(asnstock__in=intr_obj_3days_ids)
    asn_res_3days_qty = dict(asn_res_3days_qs.values_list('asnstock__sku__user').annotate(in_res=Sum('reserved_qty')))

    intr_obj_30days_qs = asn_qs.exclude(Q(arriving_date__lte=threeday_filter) | Q(asn_po_num='NON_KITTED_STOCK')).filter(arriving_date__lte=thirtyday_filter)
    intr_obj_30days_ids = intr_obj_30days_qs.values_list('id', flat=True)
    asn_res_30days_qs = ASNReserveDetail.objects.filter(asnstock__in=intr_obj_30days_ids)
    asn_res_30days_qty = dict(asn_res_30days_qs.values_list('asnstock__sku__user').annotate(in_res=Sum('reserved_qty')))

    intr_obj_100days_qs = asn_qs.exclude(arriving_date__lte=thirtyday_filter).filter(arriving_date__lte=hundred_day_filter)
    intr_obj_100days_ids = intr_obj_100days_qs.values_list('id', flat=True)
    asn_res_100days_qs = ASNReserveDetail.objects.filter(asnstock__in=intr_obj_100days_ids)
    asn_res_100days_qty = dict(asn_res_100days_qs.values_list('asnstock__sku__user').annotate(in_res=Sum('reserved_qty')))

    intr_3d_st = dict(intr_obj_3days_qs.values_list('sku__user').distinct().annotate(in_asn=Sum('quantity')))
    for k, v in intr_3d_st.items():
        if k in asn_res_3days_qty:
            intr_3d_st[k] = intr_3d_st[k] - asn_res_3days_qty[k]

    intr_30d_st = dict(intr_obj_30days_qs.values_list('sku__user').distinct().annotate(in_asn=Sum('quantity')))
    for k, v in intr_30d_st.items():
        if k in asn_res_30days_qty:
            intr_30d_st[k] = intr_30d_st[k] - asn_res_30days_qty[k]

    intr_100d_st = dict(intr_obj_100days_qs.values_list('sku__user').distinct().annotate(in_asn=Sum('quantity')))
    for k, v in intr_100d_st.items():
        if k in asn_res_100days_qty:
            intr_100d_st[k] = intr_100d_st[k] - asn_res_100days_qty[k]

    segregate_stock_wh_map.setdefault(10, {}).update(intr_3d_st)
    segregate_stock_wh_map.setdefault(45, {}).update(intr_30d_st)
    segregate_stock_wh_map.setdefault(90, {}).update(intr_100d_st)
    stock_wh_map = OrderedDict()
    for lt in [10, 45, 90]:
        stock_wh_map[lt] = OrderedDict()
    for lt, st_wh_map in segregate_stock_wh_map.items():
        break_flag = False
        for source_wh, avail_stock in st_wh_map.items():
            req_qty = req_stock - avail_stock
            if req_qty < avail_stock and req_qty < 0:
                stock_wh_map[lt][source_wh] = avail_stock - abs(req_qty)
                break_flag = True
                break
            if req_qty >= 0:
                stock_wh_map[lt][source_wh] = avail_stock
            else:
                break_flag = True
                break
            req_stock = req_qty
        if break_flag:
            break
    return stock_wh_map


def split_orders(**order_data):
    stock_wh_map = {}
    warehouse_level = order_data['warehouse_level']
    customer_id = order_data['customer_id']
    user_id = order_data['user']
    cm_id = CustomerMaster.objects.filter(customer_id=customer_id, user=user_id)
    dist_mapping = WarehouseCustomerMapping.objects.filter(customer_id=cm_id, status=1)
    if dist_mapping:
        dist_user_id = dist_mapping[0].warehouse
    else:
        log.info("No DIST id map::Order_DATA::" + repr(order_data))
        dist_user_id = user_id  # Parent of the Reseller is Distributor.

    req_stock = order_data['quantity']
    sku_id = order_data['sku_id']

    sku_code = SKUMaster.objects.get(id=sku_id).sku_code
    if warehouse_level == 3:
        stock_wh_map = fetch_asn_stock(dist_user_id, sku_code, req_stock)
    else:
        source_whs = list(NetworkMaster.objects.filter(dest_location_code_id=dist_user_id).filter(
            source_location_code__userprofile__warehouse_level=warehouse_level).values_list(
            'source_location_code_id', flat=True).order_by('lead_time', 'priority'))
        pick_filter_map = {'picklist__order__user__in': source_whs, 'picklist__order__sku__wms_code': sku_code}
        res_qtys = dict(PicklistLocation.objects.prefetch_related('picklist', 'stock').filter(status=1).filter(
            **pick_filter_map).values_list('stock__sku__user').annotate(total=Sum('reserved')))
        blocked_qtys = dict(EnquiredSku.objects.filter(sku__user__in=source_whs, sku_code=sku_code,
                                                       warehouse_level=warehouse_level).filter(
            ~Q(enquiry__extend_status='rejected')).values_list('sku__user').annotate(Sum('quantity')))
        if warehouse_level == 0 and user_id not in source_whs:  # Resellers wont have NETWORK MASTER
            source_whs.insert(0, user_id)

        stk_dtl_obj = dict(StockDetail.objects.filter(
            sku__user__in=source_whs, sku__wms_code=sku_code, quantity__gt=0).values_list(
            'sku__user').distinct().annotate(in_stock=Sum('quantity')))
        nk_filters = {'status': 'open', 'sku__sku_code': sku_code, 'asn_po_num': 'NON_KITTED_STOCK'}
        nk_stock_map = dict(ASNStockDetail.objects.filter(**nk_filters).values_list('sku__user').annotate(nk_stock=Sum('quantity')))
        log.info("Stock Avail, Reserved and Blocked(Enquiry) for SKU Code (%s)::%s:%s:%s" %
                 (sku_code, repr(stk_dtl_obj), repr(res_qtys), repr(blocked_qtys)))
        for source_wh in source_whs:
            avail_stock = stk_dtl_obj.get(source_wh, 0)
            res_stock = res_qtys.get(source_wh, 0)
            blocked_stock = blocked_qtys.get(source_wh, 0)
            # While fetching Inventory from Emiza, it includes Non Kitted Stock,
            # So excluding it as we are including it in Level 3
            nk_stock = nk_stock_map.get(source_wh, 0)
            if not res_stock:
                res_stock = 0
            if not blocked_stock:
                blocked_stock = 0
            if not nk_stock:
                nk_stock = 0
            avail_stock = avail_stock - res_stock - blocked_stock - nk_stock
            if avail_stock <= 0:
                continue
            req_qty = req_stock - avail_stock
            if req_qty < avail_stock and req_qty < 0:
                stock_wh_map[source_wh] = avail_stock - abs(req_qty)
                break
            if req_qty >= 0:
                stock_wh_map[source_wh] = avail_stock
            else:
                break
            req_stock = req_qty
    log.info("Stock assigning Map for SKU Code (%s):: %s" % (sku_code, repr(stock_wh_map)))
    return stock_wh_map


def construct_order_data_dict(request, i, order_data, myDict, all_sku_codes, custom_order):
    extra_order_fields = {}
    continue_list = ['payment_received', 'charge_name', 'charge_amount', 'custom_order', 'user_type', 'invoice_amount',
                     'description', 'extra_data', 'location', 'serials', 'direct_dispatch', 'seller_id', 'sor_id',
                     'ship_to', 'client_name', 'po_number', 'corporate_po_number', 'address_selected', 'is_sample',
                     'invoice_type', 'default_shipment_addr', 'manual_shipment_addr', 'sample_client_name',
                     'mode_of_transport', 'payment_status', 'courier_name', 'order_discount','charge_tax_percent','charge_tax_value',]
    inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
    order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
    sku_master = {}
    payment_mode = ''
    for key, value in request.POST.iteritems():
        if key in continue_list:
            continue
        if 'order_field_' in key:
            extra_order_fields[key.replace('order_field_', '')] = value
            continue
        if key == 'sku_id':
            if not myDict[key][i]:
                continue
            sku_master = all_sku_codes[i]

            if custom_order == 'true':
                _sku_mas = sku_master
                if "Custom" in _sku_mas['sku_desc']:
                    _sku_mas = SKUMaster.objects.get(id=sku_master['id'])
                    _sku_mas.sku_desc = myDict['description'][i]
                    _sku_mas.save()

            order_data['sku_id'] = sku_master['id']
            order_data['title'] = sku_master['sku_desc']
        elif key == 'quantity' or key == 'pin_code':
            try:
                value = float(myDict[key][i])
            except:
                value = 0
            order_data[key] = value
        elif key == 'shipment_date':
            if value:
                #ship_date = value.split('/')
                order_data[key] = datetime.datetime.strptime(value, '%d/%m/%Y').date()
        elif key == 'total_amount':
            try:
                value = float(myDict[key][i])
            except:
                value = 0
            order_data['invoice_amount'] = value
        elif key == 'customer_id':
            if not value:
                value = 0
            order_data[key] = value
        elif key == 'unit_price':
            value = myDict[key][i]
            if not value:
                value = 0
            order_data[key] = value
        elif key in ['cgst_tax', 'sgst_tax', 'igst_tax']:
            value = myDict[key][i]
            try:
                invoice = float(myDict['invoice_amount'][i])
            except:
                invoice = 0
            if not value:
                value = 0
            order_summary_dict[key] = value
        elif key == 'tax_type':
            order_summary_dict['tax_type'] = inter_state_dict.get(value, 2)
            order_summary_dict['inter_state'] = inter_state_dict.get(value, 2)
        elif key == 'order_taken_by':
            order_summary_dict['order_taken_by'] = value
        elif key == 'shipment_time_slot':
            order_summary_dict['shipment_time_slot'] = value
        elif key in ['discount', 'mrp']:
            try:
                discount = float(myDict[key][i])
            except:
                discount = 0
            order_summary_dict[key] = discount
        elif key == 'warehouse_level':
            order_data[key] = int(myDict[key][i])
        elif key == 'el_price':
            value = float(myDict[key][i])
            if not value:
                value = 0
            order_data[key] = value
        elif key == 'del_date':
            value = myDict[key][i]
            if value:
                order_data[key] = datetime.datetime.strptime(value, '%d/%m/%Y').date()
        elif key == 'payment_modes' :
            if not payment_mode :
                payment_dict = myDict['payment_modes'][0]
                for payment_type , value in  json.loads(payment_dict).iteritems() :
                    payment_type = payment_type.replace(' Amount' ,'')
                    order_field_name = "order_payment_"+payment_type
                    extra_order_fields[order_field_name] = value
                    payment_mode +=payment_type+","
            order_data['payment_mode'] = payment_mode
        else:
            order_data[key] = value

    return order_data, order_summary_dict, sku_master, extra_order_fields


def get_syncedusers_mapped_sku(wh, sku_id):
    sku_code = SKUMaster.objects.get(id=sku_id).sku_code
    sku_qs = SKUMaster.objects.filter(user=wh, sku_code=sku_code)
    if sku_qs:
        sku_id = sku_qs[0].id
    else:
        sku_id = None
    return sku_id


def custom_order_data(request, order_detail, ex_image_url, custom_order):
    extra_data = request.POST.get('extra_data', '')
    from_custom_order = request.POST.get('from_custom_order', '')
    if from_custom_order == 'true':
        if extra_data:
            OrderJson.objects.create(order_id=order_detail.id, json_data=extra_data,
                                     creation_date=datetime.datetime.now())
    elif custom_order == 'true' and extra_data:
        ex_image_url = create_order_json(order_detail, json.loads(extra_data), ex_image_url)


def construct_other_charge_amounts_map(created_order_id, myDict, creation_date, other_charge_amounts, user):
    if created_order_id and 'charge_name' in myDict.keys():
        for i in range(0, len(myDict['charge_name'])):
            if myDict['charge_name'][i] and myDict['charge_amount'][i]:
                OrderCharges.objects.create(user_id=user.id, order_id=created_order_id,
                                            charge_name=myDict['charge_name'][i],
                                            charge_amount=myDict['charge_amount'][i],
                                            charge_tax_value = myDict['charge_tax_value'][i],
                                            creation_date=creation_date)
                other_charge_amounts += float(myDict['charge_amount'][i])
    return other_charge_amounts

def send_mail_dispatch(order_shipment,invoice_number,original_order_id ,user):
    email = ''
    diff = 1
    admin_user = get_admin(user)
    today = datetime.date.today()
    if order_shipment.shipment_date:
        diff = order_shipment.shipment_date - today
        diff = diff.days
    company_name = UserProfile.objects.filter(user=user.id)[0].company_name
    data_dict = {'order_id':original_order_id, 'invoice_number':invoice_number,'shipment_id':order_shipment.id,
                 'company_name':company_name, 'user':user, 'admin_user':admin_user.username.lower(), 'eta':diff,
                 'shipment_reference':order_shipment.shipment_reference}
    order_obj = OrderDetail.objects.filter(original_order_id=original_order_id,user=user.id)
    if order_obj:
        email = order_obj[0].email_id
        data_dict['customer_name'] = order_obj[0].customer_name
    t = loader.get_template('templates/dispatched.html')
    rendered = t.render(data_dict)
    if email:
        send_mail([email], 'Order Dispatched: %s' % (original_order_id), rendered)

def send_mail_ordered_report(order_detail, telephone, items, other_charge_amounts, order_data, user, gen_order_id=None):
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='order', misc_value='true')
    order_id = None
    admin_user = get_admin(user)
    if gen_order_id:
        order_id = gen_order_id
    elif order_detail:
        order_id = order_detail.order_id
    else:
        log.info("Order ID Not Found")
    if misc_detail:
        company_name = UserProfile.objects.filter(user=user.id)[0].company.company_name
        headers = ['Product Details', 'Ordered Quantity', 'Total']
        if admin_user.username == 'isprava_admin':
            headers.insert(0,'Image')
        data_dict = {'customer_name': order_data['customer_name'], 'order_id': order_id,
                     'address': order_data['address'], 'phone_number': order_data['telephone'], 'items': items,
                     'headers': headers, 'company_name': company_name, 'user': user, 'client_name': order_data.get('client_name', '')}

        t = loader.get_template('templates/order_confirmation.html')
        rendered = t.render(data_dict)

        email = order_data['email_id']
        if email:
            send_mail([email], 'Order Confirmation: %s' % order_id, rendered)
        if not telephone:
            telephone = order_data.get('telephone', "")
        if telephone:
            order_creation_message(items, telephone, str(order_id),
                                   other_charges=other_charge_amounts)


def send_mail_enquiry_order_report(items, enquiry_id, user, customer_details, is_expiry=False):
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='enquiry', misc_value='true')
    email = customer_details['email_id']
    receivers = [email]
    internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='Internal Emails')
    misc_internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='internal_mail', misc_value='true')
    if misc_internal_mail and internal_mail:
        internal_mail = internal_mail[0].misc_value.split(",")
        receivers.extend(internal_mail)
    if misc_detail:
        company_name = UserProfile.objects.filter(user=user.id)[0].company.company_name
        headers = ['Product Details', 'Ordered Quantity', 'Total']
        data_dict = {'customer_name': customer_details['customer_name'], 'enquiry_id': enquiry_id,
                     'items': items, 'headers': headers, 'company_name': company_name, 'user': user}

        t = loader.get_template('templates/enq_order_confirmation.html')
        rendered = t.render(data_dict)

        if receivers:
            if is_expiry:
                subject = 'Enquiry Order %s is going to expire today'
            else:
                subject = 'Order Confirmation: %s'
            send_mail(receivers, subject % enquiry_id, rendered)


def fetch_order_ids(stock_wh_map, user_order_ids_map):
    for usr, qty in stock_wh_map.iteritems():
        order_id = get_order_id(usr)
        if usr not in user_order_ids_map:
            user_order_ids_map[usr] = order_id


def sku_level_total_qtys(myDict, sku_total_qty_map):
    for i in range(0, len(myDict['sku_id'])):
        sku_id, quantity = myDict['sku_id'][i], myDict['quantity'][i]
        if sku_id in sku_total_qty_map:
            sku_total_qty_map[sku_id] += int(quantity)
        else:
            sku_total_qty_map[sku_id] = int(quantity)


def create_central_order(request, user):
    mail_ids, user_mail_id, items = [], [], []
    message = 'Success'
    customer_id = request.user.id
    host_details = request.META.get('wsgi.url_scheme')+'://'+request.META.get('HTTP_HOST')
    interm_order_id = get_central_order_id(customer_id)
    ship_date = request.POST.get('shipment_date', '')
    myDict = dict(request.POST.iterlists())
    remarks_dict = dict(zip(myDict['sku_id'], myDict['remarks']))
    if not ship_date:
        return HttpResponse('Failed')
    project_name = request.POST.get('client_name', '') #Corporates In SM is used as Projects for ISPRAVA
    ship_date = ship_date.split('/')
    shipment_date = datetime.date(int(ship_date[2]), int(ship_date[1]), int(ship_date[0]))
    cart_items = CustomerCartData.objects.filter(customer_user_id=customer_id)
    if not cart_items:
        return HttpResponse('No Data in Cart')
    stock_display_warehouse = get_misc_value('stock_display_warehouse', user.id)
    if stock_display_warehouse and stock_display_warehouse != "false":
        stock_display_warehouse = stock_display_warehouse.split(',')
        stock_display_warehouse = map(int, stock_display_warehouse)
    try:
        interm_order_map = {'user_id': user.id, 'interm_order_id': interm_order_id,
                            'customer_user_id': customer_id, 'shipment_date': shipment_date,
                            'project_name': project_name}
        for cart_item in cart_items:
            interm_order_map['quantity'] = cart_item.quantity
            interm_order_map['unit_price'] = cart_item.levelbase_price
            interm_order_map['sku_id'] = cart_item.sku_id
            interm_order_map['remarks'] = remarks_dict[cart_item.sku.sku_code]
            cart_qty, inter_qty = 0, 0
            cart_obj = CustomerCartData.objects.filter(sku__sku_code=cart_item.sku.sku_code).exclude(customer_user_id=customer_id)
            inter_obj = IntermediateOrders.objects.filter(sku__sku_code=cart_item.sku.sku_code, status='')
            if cart_obj:
                cart_qty = cart_obj.aggregate(Sum('quantity'))['quantity__sum']
            if inter_obj:
                inter_qty = inter_obj.aggregate(Sum('quantity'))['quantity__sum']
            blocked_qty = cart_qty + inter_qty
            stocks = StockDetail.objects.filter(sku__user__in=stock_display_warehouse, sku__sku_code=cart_item.sku.sku_code,
                                                quantity__gt=0)
            avail_qty = check_stock_available_quantity(stocks, user, stock_ids=None)
            if (avail_qty - blocked_qty) < cart_item.quantity:
                return HttpResponse('Order Cant be placed as stock not available for sku: %s' %cart_item.sku.sku_code)
            intermediate_obj =  IntermediateOrders.objects.create(**interm_order_map)
            #x = intermediate_obj.shipment_date
            order_date = intermediate_obj.creation_date.strftime("%d, %b, %Y")
            #order_date =  intermediate_obj.shipment_date.day + "/"+intermediate_obj.shipment_date.month+"/"+intermediate_obj.shipment_date.year
            inv_amt = (cart_item.levelbase_price * cart_item.quantity) + cart_item.tax
            items.append([host_details +cart_item.sku.image_url, intermediate_obj.interm_order_id,cart_item.sku.sku_code,cart_item.sku.sku_desc,cart_item.quantity, inv_amt,intermediate_obj.project_name,order_date])

        #mail to Admin and normal user
        central_orders_mail = MiscDetail.objects.filter(user=user.id, misc_type='central_orders', misc_value='true')
        if central_orders_mail:
            """if user.userprofile.warehouse_type == 'CENTRAL_ADMIN':
                mail_ids = [user.userprofile.email]
            else:
                admin_users = UserGroups.objects.filter(user_id=user.id)
                if admin_users:
                    mail_ids = [admin_users[0].admin_user.userprofile.email]"""
            mail_ids = [user.email]
            user_mail_id = [request.user.email]
            headers = ['Image', 'Order number','isprava code','Product Details', 'Ordered Quantity', 'Total','Project name','Order Date']
            data_dict = {'customer_name': request.user.username, 'items': items,
                         'headers': headers, 'role': 'Admin', 'order_id': interm_order_id}
            t = loader.get_template('templates/central_order/order_for_approval.html')
            rendered = t.render(data_dict)
            t_user = loader.get_template('templates/central_order/order_placed.html')
            rendered_user = t_user.render(data_dict)
            internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='Internal Emails')
            misc_internal_mail = MiscDetail.objects.filter(user=user.id, misc_type='internal_mail', misc_value='true')
            if misc_internal_mail and internal_mail:
                internal_mail = internal_mail[0].misc_value.split(",")
                mail_ids.extend(internal_mail)
                user_mail_id.extend(internal_mail)
            if mail_ids:
                send_mail(mail_ids, 'Order Approval Request, Customer: %s' % request.user.username, rendered)
            if user_mail_id:
                send_mail(user_mail_id, 'Order Placed Successfully', rendered_user)



    except:
        import traceback
        log.debug(traceback.format_exc())
        message = 'Failed'
    else:
        CustomerCartData.objects.filter(customer_user=request.user.id).delete()
    return HttpResponse(message)


@csrf_exempt
@login_required
@get_admin_user
@fn_timer
def create_order_from_intermediate_order(request, user):
    mail_ids, user_mail_id, items = [], [], []
    order_dict = {}
    created_order_objs = []
    message = 'Success'
    first = True
    inter_obj_data = {}
    host_details = request.META.get('wsgi.url_scheme')+'://'+request.META.get('HTTP_HOST')
    dispatch_qc_check = get_misc_value('dispatch_qc_check', user.id)
    central_order_reassigning =  get_misc_value('central_order_reassigning', user.id) #for 72networks
    order_code = get_order_prefix(user.id)
    warehouses = json.loads(request.POST.get('warehouse'))
    for wh, wh_data in warehouses.iteritems():
        # Picklist generation
        order_user_sku = {}
        order_user_objs = {}
        order_sku = {}
        order_objs = []

        if int(wh_data['quantity']) > 0:
            wh_name = wh
            alt_sku_code = request.POST.get('alt_sku_code', '')
            sku_master = SKUMaster.objects.filter(user=user.id, sku_code=alt_sku_code)
            if not sku_master.exists():
                return HttpResponse('Invalid Alt SKU code')
            wh_usr_obj = User.objects.filter(username=wh_name)
            status = request.POST.get('status', '')
            if status != '0':
                if wh_usr_obj:
                    wh_id = wh_usr_obj[0].id
                    wh_usr_obj = wh_usr_obj[0]
                else:
                    return HttpResponse('User Missing')
            interm_det_id = request.POST.get('interm_det_id', '')
            shipment_date = request.POST.get('shipment_date', '')
            if shipment_date:
                shipment_date = datetime.datetime.strptime(shipment_date, "%m/%d/%Y")
            if not status:
                return HttpResponse('Status Missing')
            interm_qs = IntermediateOrders.objects.filter(id=interm_det_id)
            if not interm_qs:
                return HttpResponse('Failed')
            sel_sku_id = interm_qs[0].sku.id
            update_alt_sku = False
            if interm_qs[0].sku.sku_code != alt_sku_code:
                update_alt_sku = True
                sel_sku_id = sku_master[0].id
            try:
                interm_obj = interm_qs[0]
                inter_obj_data = {'interm_order_id': interm_obj.interm_order_id,
                                  'unit_price': interm_obj.unit_price,
                                  'tax': interm_obj.tax,
                                  'user_id': interm_obj.user_id,
                                  'customer_user_id': interm_obj.customer_user_id,
                                  'shipment_date': interm_obj.shipment_date,
                                  'project_name': interm_obj.project_name,
                                  'sku_id': interm_obj.sku_id,
                                  'remarks': interm_obj.remarks,
                                  'status': interm_obj.status,
                                  'alt_sku_id': interm_obj.alt_sku_id
                                 }
                #inv_amt = (interm_obj.unit_price * interm_obj.quantity) + interm_obj.tax
                if first:
                    if (interm_obj.order_id or interm_obj.order_assigned_wh) and dispatch_qc_check == 'false':
                        if central_order_reassigning :
                            interm_obj.order_assigned_wh = wh_usr_obj
                            interm_obj.remarks = ''
                        if status:
                            interm_obj.status = status
                        if shipment_date and status:
                            interm_obj.shipment_date = shipment_date
                            interm_obj.order.shipment_date = shipment_date
                        if update_alt_sku:
                            interm_obj.alt_sku_id = sel_sku_id
                        interm_obj.quantity = wh_data['quantity']
                        interm_obj.save()
                        first = False
                        return HttpResponse('Success, Order Already Created')
                else:
                    inter_obj_data['quantity'] = int(wh_data['quantity'])
                    interm_obj = IntermediateOrders.objects.create(**inter_obj_data)
                    inv_amt = (interm_obj.unit_price * interm_obj.quantity) + interm_obj.tax
                    items.append([interm_obj.sku.sku_desc, interm_obj.quantity, inv_amt])

                if status != '0':
                    order_dict['user'] = wh_id
                    sku_id = get_syncedusers_mapped_sku(wh=wh_id, sku_id=sel_sku_id)
                    if not sku_id:
                        return HttpResponse("SKU Not found in Selected Warehouse")
                    order_dict['sku_id'] = sku_id
                    order_dict['title'] = interm_obj.sku.sku_desc
                    order_dict['sku_code'] = interm_obj.sku.sku_code
                    if update_alt_sku:
                        interm_obj.alt_sku_id = sel_sku_id
                        interm_obj.save()
                        order_dict['title'] = interm_obj.alt_sku.sku_desc
                        order_dict['sku_code'] = interm_obj.alt_sku.sku_code
                    if interm_obj.customer_user:
                        customer_user = CustomerUserMapping.objects.filter(user_id=interm_obj.customer_user.id)
                        if customer_user:
                            order_dict['customer_id'] = customer_user[0].customer.customer_id
                            order_dict['customer_name'] = customer_user[0].customer.name
                            order_dict['telephone'] = customer_user[0].customer.phone_number
                            order_dict['email_id'] = customer_user[0].customer.email_id
                            order_dict['address'] = customer_user[0].customer.address
                        else:
                            return HttpResponse('Failed')
                    elif interm_obj.customer_id:
                        customer_master = CustomerMaster.objects.filter(user=user.id, customer_id=interm_obj.customer_id)
                        if customer_master:
                            order_dict['customer_id'] = customer_master[0].customer_id
                            order_dict['customer_name'] = customer_master[0].name
                            order_dict['email_id'] = customer_master[0].email_id
                            order_dict['telephone'] = customer_master[0].phone_number
                            order_dict['address'] = customer_master[0].address
                    else:
                        order_dict['customer_id'] = 0
                        mail_obj = OrderFields.objects.filter(original_order_id=str(interm_obj.interm_order_id), order_type='intermediate_order', user=user.id, name='email_id')
                        if mail_obj:
                            order_dict['email_id'] = mail_obj[0].value

                        mobile_no_obj = OrderFields.objects.filter(original_order_id=str(interm_obj.interm_order_id), order_type='intermediate_order', user=user.id, name='mobile_no')
                        if mobile_no_obj:
                            order_dict['telephone'] = mobile_no_obj[0].value

                        address_obj = OrderFields.objects.filter(original_order_id=str(interm_obj.interm_order_id), order_type='intermediate_order', user=user.id, name='address')
                        if address_obj:
                            order_dict['address'] = address_obj[0].value

                        intermediate_obj = IntermediateOrders.objects.filter(user=user.id, interm_order_id=str(interm_obj.interm_order_id))
                        if intermediate_obj:
                            order_dict['customer_name'] = intermediate_obj[0].customer_name
                    order_dict['quantity'] = int(wh_data['quantity'])
                    order_dict['order_code'] = order_code
                    order_dict['shipment_date'] = interm_obj.shipment_date
                    order_dict['order_id'] = get_order_id(wh_id)
                    order_dict['original_order_id'] = order_dict['order_code'] + str(order_dict['order_id'])
                    if user.username == 'one_assist':
                        org_obj = OrderFields.objects.filter(original_order_id=str(interm_obj.interm_order_id),
                                                             order_type='intermediate_order', user=user.id,
                                                             name='original_order_id')
                        if org_obj:
                            order_dict['original_order_id'] = org_obj[0].value
                            order_dict['order_id'] = org_obj[0].value
                            order_dict['order_code'] = ''
                    order_dict['status'] = 1
                    order_dict['remarks'] = interm_obj.remarks
                    ord_obj = OrderDetail(**order_dict)
                    ord_obj.save()
                    order_objs.append(ord_obj)
                    order_sku.update({ord_obj.sku: order_dict['quantity']})
                    # Collecting needed data for Picklist generation
                    order_user_sku.setdefault(wh_id, {})
                    order_user_sku[wh_id].setdefault(ord_obj.sku, 0)
                    order_user_sku[wh_id][ord_obj.sku] += order_dict['quantity']

                    # Collecting User order objs for picklist generation
                    order_user_objs.setdefault(wh_id, [])
                    order_user_objs[wh_id].append(ord_obj)

                    auto_picklist_signal = get_misc_value('auto_generate_picklist', wh_id)
                    if auto_picklist_signal == 'true':
                        message = check_stocks(order_sku, wh_usr_obj, request, order_objs)

                    if first:
                        # inv_amt = (interm_obj.unit_price * interm_obj.quantity) + interm_obj.tax
                        inv_amt = 0
                        items.append([host_details+interm_obj.sku.image_url, interm_obj.interm_order_id,interm_obj.sku.sku_code, interm_obj.sku.sku_desc,interm_obj.quantity, inv_amt, interm_obj.project_name])
                        inter_obj_data = {'interm_order_id': interm_obj.interm_order_id,
                                          'unit_price': interm_obj.unit_price,
                                          'tax': interm_obj.tax,
                                          'user_id': interm_obj.user_id,
                                          'customer_user_id': interm_obj.customer_user_id,
                                          'shipment_date': interm_obj.shipment_date,
                                          'project_name': interm_obj.project_name,
                                          'sku_id': interm_obj.sku_id,
                                          'remarks': interm_obj.remarks,
                                          'status': interm_obj.status,
                                          'alt_sku_id': interm_obj.alt_sku_id
                                         }
                        first = False
                    interm_obj.order_id = ord_obj.id
                    interm_obj.quantity = int(wh_data['quantity'])
                    interm_obj.order_assigned_wh_id = wh_id
                    interm_obj.shipment_date = shipment_date
                    interm_obj.save()
                    cust_ord_dict = {'order_id': ord_obj.id, 'sgst_tax': interm_obj.sgst_tax, 'cgst_tax': interm_obj.cgst_tax,
                                     'igst_tax': interm_obj.igst_tax}
                    cos_qs = CustomerOrderSummary.objects.filter(order_id=ord_obj.id)
                    if cos_qs:
                        cos_qs.update(**cust_ord_dict)
                    else:
                        cos_obj = CustomerOrderSummary(**cust_ord_dict)
                        cos_obj.save()

                    #mail to Admin and normal user
                    central_orders_mail = MiscDetail.objects.filter(user=request.user.id, misc_type='central_orders', misc_value='true')
                    if central_orders_mail:
                        """if user.userprofile.warehouse_type == 'CENTRAL_ADMIN':
                            mail_ids = [user.userprofile.email]
                        else:
                            admin_users = UserGroups.objects.filter(user_id=user.id)
                            if admin_users:
                                mail_ids = [admin_users[0].admin_user.userprofile.email]"""
                        mail_ids = [request.user.email]
                        interm_qs = interm_qs[0]
                        user_mail_id = [interm_qs.customer_user.email]
                        headers = ['Image', 'Order number','isprava code','Product Details', 'Ordered Quantity', 'Total','Project name']
                        mail_order_id = order_dict['order_code'] + str(order_dict['order_id']) + ' ('\
                                        + str(interm_qs.order_id) + ')'
                        data_dict = {'customer_name': interm_qs.customer_user.username, 'items': items,
                                     'headers': headers, 'role': 'Admin',
                                     'status': 'accept', 'order_id': mail_order_id}
                        t = loader.get_template('templates/central_order/order_approved_admin.html')
                        rendered = t.render(data_dict)
                        t_user = loader.get_template('templates/central_order/order_approved.html')
                        rendered_user = t_user.render(data_dict)
                        if mail_ids:
                            send_mail(mail_ids, 'Order Approved, Customer: %s' % interm_qs.customer_user.username, rendered)
                        if user_mail_id:
                            send_mail(user_mail_id, 'Order Approved Successfully', rendered_user)
                    created_order_objs.append(ord_obj)
                #admin_user = get_admin(user)
                #if admin_user.username in ['one_assist']:
                #    create_order_pos(user, created_order_objs)
            except:
                import traceback
                log.debug(traceback.format_exc())
                message = 'Failed'
            else:
                interm_obj.status = status
                interm_obj.save()
    return HttpResponse(message)


def block_asn_stock(sku_id, qty, lead_time, ord_det_id, is_enquiry=False):
    todays_date = datetime.datetime.today().date()
    lt_date = todays_date + datetime.timedelta(days=lead_time)
    asn_common_qs = ASNStockDetail.objects.filter(sku_id=sku_id, status='open')
    asn_qs = asn_common_qs.filter(asn_po_num='NON_KITTED_STOCK')
    if not asn_qs:
        asn_qs = asn_common_qs.filter(arriving_date__lte=lt_date).order_by('arriving_date')
    for asn_obj in asn_qs:
        asn_res_map = {'asnstock_id': asn_obj.id}
        if not is_enquiry:
            asn_res_map['orderdetail_id'] = ord_det_id
        else:
            asn_res_map['enquirydetail'] = ord_det_id  # Here ord_det_id is EnquiryDetailID when calling block_asn_stock
        if not asn_obj.asnreservedetail_set.values():
            # Create ASN Reserve Detail Object
            if qty and qty <= asn_obj.quantity:
                asn_res_map['reserved_qty'] = qty
                ASNReserveDetail.objects.create(**asn_res_map)
                break
            else:
                qty = qty - asn_obj.quantity
                asn_res_map['reserved_qty'] = asn_obj.quantity
                ASNReserveDetail.objects.create(**asn_res_map)
        else:
            res_stock_obj = asn_obj.asnreservedetail_set.values('asnstock').annotate(in_res=Sum('reserved_qty'))
            res_stock = res_stock_obj[0]['in_res']
            avail_stock = asn_obj.quantity - res_stock
            if qty and qty <= avail_stock:
                asn_res_map['reserved_qty'] = qty
                ASNReserveDetail.objects.create(**asn_res_map)
                break
            else:
                qty = qty - avail_stock
                asn_res_map['reserved_qty'] = avail_stock
                ASNReserveDetail.objects.create(**asn_res_map)


def construct_backorder_dict(myDict, backorder_map):
    for i in range(0, len(myDict['sku_id'])):
        sku_id, quantity, wh_level = myDict['sku_id'][i], myDict['quantity'][i], myDict['warehouse_level'][i]
        backorder_map.setdefault(sku_id, {}).setdefault(wh_level, quantity)


def create_backorders(backorder_splitup_map, admin_user, sku_total_qty_map):
    for sku_code, wh_level_map in backorder_splitup_map.items():
        for wh_level, qty_map in wh_level_map.items():
            for usr, qty in qty_map.items():
                dist_mapping = WarehouseCustomerMapping.objects.filter(warehouse_id=usr, status=1)
                taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0}
                order_summary_dict = {'discount': 0, 'issue_type': 'order', 'vat': 0, 'tax_value': 0, 'status': 1,
                                      'shipment_time_slot': '9-12', 'creation_date': datetime.datetime.now()}
                if dist_mapping:
                    usr_sku_master = SKUMaster.objects.get(user=usr, sku_code=sku_code)
                    cust_obj = dist_mapping[0].customer
                    cm_id = cust_obj.id
                    generic_order_id = get_generic_order_id(cm_id)
                    parent_user = cust_obj.user
                    order_code = get_order_prefix(parent_user.id)
                    backorder_copy = {'quantity': qty, 'order_code': order_code, 'customer_id': cust_obj.customer_id,
                                      'customer_name': cust_obj.name, 'telephone': cust_obj.phone_number,
                                      'email_id': cust_obj.email_id, 'address': cust_obj.address, 'user': parent_user,
                                      'order_id': get_order_id(parent_user)}
                    backorder_copy['original_order_id'] = '%s%s' % (order_code,backorder_copy['order_id'])
                    if cust_obj.tax_type:
                        inter_state_dict = dict(
                            zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
                        inter_state = inter_state_dict.get(cust_obj.tax_type, 2)
                        tax_master = TaxMaster.objects.filter(user_id=admin_user.id, inter_state=inter_state,
                                                              product_type=usr_sku_master.product_type)
                        if tax_master:
                            tax_master = tax_master[0]
                            taxes['cgst_tax'] = float(tax_master.cgst_tax)
                            taxes['sgst_tax'] = float(tax_master.sgst_tax)
                            taxes['igst_tax'] = float(tax_master.igst_tax)
                            taxes['utgst_tax'] = float(tax_master.utgst_tax)
                    order_summary_dict.update(taxes)
                else:
                    continue
                total_qty = sku_total_qty_map[sku_code]
                sku_obj = SKUMaster.objects.filter(user=usr, sku_code=sku_code)
                if sku_obj:
                    sku_id = sku_obj[0].id
                    backorder_copy['sku_id'] = sku_id
                else:
                    continue
                # sending level 1 as we need to place back orders to SM Warehouses only
                price_ranges_map = fetch_unit_price_based_ranges(usr, 1, admin_user.id, sku_code)
                backorder_feasibility_flag = False
                if price_ranges_map.has_key('price_ranges'):
                    max_unit_ranges = [i['max_unit_range'] for i in price_ranges_map['price_ranges']]
                    highest_max = max(max_unit_ranges)
                    for index, each_map in enumerate(price_ranges_map['price_ranges']):
                        if index == 0:
                            continue
                        min_qty, max_qty, price = each_map['min_unit_range'], each_map['max_unit_range'], each_map[
                            'price']
                        if min_qty <= total_qty <= max_qty:
                            backorder_copy['unit_price'] = price
                            invoice_amount = get_tax_inclusive_invoice_amt(cust_obj.id, price, qty,
                                                                           usr, sku_code, admin_user)
                            backorder_copy['invoice_amount'] = invoice_amount
                            backorder_feasibility_flag = True
                            break
                        elif max_qty >= highest_max:
                            backorder_copy['unit_price'] = price
                            invoice_amount = get_tax_inclusive_invoice_amt(cust_obj.id, price, qty,
                                                                           usr, sku_code, admin_user)
                            backorder_copy['invoice_amount'] = invoice_amount
                else:
                    continue
                if not backorder_feasibility_flag:
                    log.info("Not Creating Back order as total qty (%s) is in Price Grid A" % total_qty)
                    continue
                order_obj = OrderDetail.objects.filter(order_id=backorder_copy['order_id'],
                                                       sku_id=backorder_copy['sku_id'],
                                                       order_code=backorder_copy['order_code'])
                # Distributor can place order directly to any wh/distributor
                backorder_copy['shipment_date'] = datetime.datetime.today().date()
                if not order_obj:
                    order_detail = OrderDetail(**backorder_copy)
                    order_detail.save()
                else:
                    order_detail = order_obj[0]
                order_summary_dict['order_id'] = order_detail.id
                create_ordersummary_data(order_summary_dict, order_detail, backorder_copy['address'])
                el_price = backorder_copy['unit_price'] # Considering same unit price as el_price as both would be same here
                del_date = backorder_copy['shipment_date']
                create_grouping_order_for_generic(generic_order_id, order_detail, cm_id, parent_user,
                                                  backorder_copy['quantity'], '', '',
                                                  backorder_copy['unit_price'], el_price, del_date)

                generic_orders = GenericOrderDetailMapping.objects.filter(generic_order_id=generic_order_id,
                                                                          customer_id=cm_id). \
                    values('orderdetail__original_order_id', 'orderdetail__user').distinct()
                for generic_order in generic_orders:
                    original_order_id = generic_order['orderdetail__original_order_id']
                    order_detail_user = User.objects.get(id=generic_order['orderdetail__user'])
                    resp = order_push(original_order_id, order_detail_user, "NEW")
                    log.info('New (Back) Order Push Status: %s' % (str(resp)))
                check_and_raise_po(generic_order_id, cm_id, order_detail.id)


def check_backorder_compatibility(myDict, admin_user, user):
    sku_qty_map = {}
    sku_total_qty_map = {}
    backorder_feasibility_flag = False
    for i in range(len(myDict['sku_id'])):
        sku_id = myDict['sku_id'][i]
        qty = myDict['quantity'][i]
        sku_qty_map.setdefault(sku_id, []).append(qty)

    for sku, qties in sku_qty_map.items():
        sku_total_qty_map[sku] = [sum(map(int, qties)), False]

    for sku_code, val in sku_total_qty_map.items():
        total_qty, flag_val = val
        price_ranges_map = fetch_unit_price_based_ranges(user, 1, admin_user.id, sku_code)
        if price_ranges_map.has_key('price_ranges'):
            for index, each_map in enumerate(price_ranges_map['price_ranges']):
                if index == 0:
                    continue
                min_qty, max_qty, price = each_map['min_unit_range'], each_map['max_unit_range'], each_map['price']
                if min_qty <= total_qty <= max_qty:
                    backorder_feasibility_flag = True
                    sku_total_qty_map[sku_code][1] = backorder_feasibility_flag
                    break
        if not backorder_feasibility_flag:
            log.info("Not Creating Back order as total qty (%s) is in Price Grid A" % total_qty)
    return backorder_feasibility_flag, sku_total_qty_map


@csrf_exempt
@login_required
@get_admin_user
@fn_timer
@reversion.create_revision(atomic=False, using='reversion')
def insert_order_data(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("create_order: %s" % str(get_user_ip(request)))
    myDict = dict(request.POST.iterlists())
    order_id = ''
    # Sending mail and message

    host_details = request.META.get('wsgi.url_scheme')+'://'+request.META.get('HTTP_HOST')

    items = []

    other_charge_amounts = 0

    # Picklist generation
    order_user_sku = {}
    order_user_objs = {}
    order_sku = {}
    order_objs = []

    # Initialize creation date

    #Collecting Created order objects
    created_order_objs = []
    # Intialize to stored saved skus and dispatch data
    created_skus = []
    dispatch_orders = {}
    direct_dispatch = request.POST.get('direct_dispatch', '')
    dispatch_orders = OrderedDict()

    # Validate sku, quantity, stock
    valid_status, all_sku_codes, temp_distinct_skus = validate_order_form(myDict, request, user)
    payment_modes = request.POST.get('payment_modes', '')
    if payment_modes:
        payment_modes =  json.loads(payment_modes)
    payment_received = request.POST.get('payment_received', '')
    payment_status = request.POST.get('payment_status', '')
    tax_percent = request.POST.get('tax', '')
    telephone = request.POST.get('telephone', '')
    custom_order = request.POST.get('custom_order', '')
    user_type = request.user.userprofile.user_type #request.POST.get('user_type', '')
    seller_id = request.POST.get('seller_id', '')
    sor_id = request.POST.get('sor_id', '')
    ship_to = request.POST.get('ship_to', '')
    po_number = request.POST.get('po_number', '')
    client_name = request.POST.get('client_name', '')
    corporate_po_number = request.POST.get('corporate_po_number', '')
    address_selected = request.POST.get('address_selected', '')
    is_sample = request.POST.get('is_sample', '')
    invoice_type = request.POST.get('invoice_type', '')
    sample_client_name = request.POST.get('sample_client_name', '')
    mode_of_transport = request.POST.get('mode_of_transport','')
    courier_name = request.POST.get('courier_name', '')
    order_discount = request.POST.get('order_discount', 0)
    dist_shipment_address = request.POST.get('manual_shipment_addr', '')
    vehicle_number = request.POST.get('vehicle_num', '')
    is_central_order = request.POST.get('is_central_order', '')
    marketplace_value = request.POST.get('market_list', '')
    order_code = get_order_prefix(user.id)
    isprava_user = get_admin(user)
    if dist_shipment_address:
        ship_to = dist_shipment_address
    created_order_id = ''
    ex_image_url = {}
    inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
    po_data = []
    if valid_status:
        return HttpResponse(valid_status)
    if is_central_order:
        message = create_central_order(request, user)
        return HttpResponse(message)


    log.info('Request params for ' + user.username + ' is ' + str(myDict))
    enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
    auto_picklist_signal = get_misc_value('auto_generate_picklist', user.id)
    order_status_key = 1
    if auto_picklist_signal == 'true':
        order_status_key = 9

    # Using the display_sku_cust_mapping flag for ANT Stationers
    # orders_for_approval_flag = get_misc_value('display_sku_cust_mapping', user.id)
    # if orders_for_approval_flag == 'true':
    #     status = update_cartdata_for_approval(request, user)
    #     return HttpResponse(status)
    is_distributor = False
    cm_id = 0
    generic_order_id = 0
    admin_user = get_priceband_admin_user(user)
    order_detail = None
    # backorder_flag = False
    if admin_user:
        # get_order_customer_details
        user_order_ids_map = {}
        sku_total_qty_map = {}
        backorder_map = {}
        backorder_splitup_map = {}
        construct_backorder_dict(myDict, backorder_map)
        sku_level_total_qtys(myDict, sku_total_qty_map)
        if user_type == 'customer':
            customer_user = CustomerUserMapping.objects.filter(user_id=request.user.id)

            customer_obj = CustomerMaster.objects.filter(customer_id=customer_user[0].customer.customer_id,
                                                         user=user.id)
            if customer_obj:
                is_distributor = customer_obj[0].is_distributor
                cm_id = customer_obj[0].id
                generic_order_id = get_generic_order_id(cm_id)
                # if not is_distributor:
                #     backorder_flag, sku_total_qty_map = check_backorder_compatibility(myDict, admin_user, user)
    try:
        for i in range(0, len(myDict['sku_id'])):
            order_data = copy.deepcopy(UPLOAD_ORDER_DATA)
            #order_summary_dict = copy.deepcopy(ORDER_SUMMARY_FIELDS)
            # order_data['order_id'] = order_id
            order_data['status'] = order_status_key
            order_data['order_code'] = order_code
            order_data['marketplace'] = 'Offline'
            if is_sample == 'true':
                order_data['marketplace'] = 'Sample'
            if marketplace_value:
                order_data['marketplace'] = marketplace_value
            if custom_order == 'true':
                order_data['order_code'] = 'CO'
            order_data['user'] = user.id
            order_data['unit_price'] = 0
            order_data['sku_code'] = myDict['sku_id'][i]
            vendor_items = ['printing_vendor', 'embroidery_vendor', 'production_unit']
            exclude_order_items = ['warehouse_level', 'margin_data', 'el_price', 'del_date', 'vehicle_num', 'cost_price','marginal_flag','market_list']
            # Written a separate function to make the code simpler
            order_data, order_summary_dict, sku_master, extra_order_fields = construct_order_data_dict(
                request, i, order_data, myDict, all_sku_codes, custom_order)
            if not order_data['sku_id'] or not order_data['quantity']:
                continue
            order_summary_dict['invoice_type'] = invoice_type
            order_summary_dict['client_name'] = sample_client_name
            order_summary_dict['mode_of_transport'] = mode_of_transport
            order_summary_dict['payment_status'] = payment_status
            order_summary_dict['vehicle_number'] = vehicle_number
            if order_discount:
                order_summary_dict.setdefault('discount', 0)
                order_summary_dict['discount'] = order_summary_dict['discount'] + \
                                                 (float(order_discount)/len(temp_distinct_skus))

            if admin_user:
                if user_type == 'customer':
                    order_data = get_order_customer_details(order_data, request)
                else:
                    order_data['warehouse_level'] = 0
                stock_wh_map = split_orders(**order_data)
                if order_data['warehouse_level'] != 1:
                    sku_id = myDict['sku_id'][i]
                    wh_level = order_data['warehouse_level']
                    backorder_splitup_map.setdefault(sku_id, {}).setdefault(wh_level, {}).update(stock_wh_map)
                if order_data['warehouse_level'] == 3:
                    for lt, st_wh_map in stock_wh_map.items():
                        fetch_order_ids(st_wh_map, user_order_ids_map)
                else:
                    fetch_order_ids(stock_wh_map, user_order_ids_map)
                if not is_distributor and user_order_ids_map.has_key(user.id) and stock_wh_map.has_key(user.id):
                    order_data['order_id'] = user_order_ids_map[user.id]
                    order_data['user'] = user.id
                    mapped_sku_id = get_syncedusers_mapped_sku(user.id, order_data['sku_id'])
                    order_obj = OrderDetail.objects.filter(order_id=user_order_ids_map[user.id], user=user.id,
                                                           sku_id=mapped_sku_id, order_code=order_data['order_code'])
                    if not order_obj:
                        el_price = order_data['el_price']
                        del_date = order_data['del_date']

                        for item in exclude_order_items:
                            if item in order_data:
                                order_data.pop(item)
                        order_data['sku_id'] = mapped_sku_id
                        order_obj = OrderDetail(**order_data)
                        order_obj.save()

                        # Collecting needed data for Picklist generation
                        order_user_sku.setdefault(user.id, {})
                        order_user_sku[user.id].setdefault(order_obj.sku, 0)
                        order_user_sku[user.id][order_obj.sku] += order_data['quantity']

                        # Collecting User order objs for picklist generation
                        order_user_objs.setdefault(user.id, [])
                        order_user_objs[user.id].append(order_obj)

                        create_grouping_order_for_generic(generic_order_id, order_obj, cm_id, user.id,
                                                          order_data['quantity'], corporate_po_number, client_name,
                                                          order_data['unit_price'], el_price, del_date)
                        create_ordersummary_data(order_summary_dict, order_obj, ship_to, courier_name)
                    wh_name = User.objects.get(id=user.id).first_name
                    cont_vals = (order_data['customer_name'], order_data['order_id'], wh_name)
                    contents = {"en": "%s placed an order %s to %s warehouse" % cont_vals}
                    users_list = [user.id, admin_user.id]
                    send_push_notification(contents, users_list)
                if order_data.get('warehouse_level', '') == 3:
                    order_data['warehouse_level'] = 1
                    for lt, st_wh_map in stock_wh_map.iteritems():
                        for usr, qty in st_wh_map.iteritems():
                            order_data['order_id'] = user_order_ids_map[usr]
                            order_data['user'] = usr
                            if qty <= 0:
                                continue
                            order_data['quantity'] = qty
                            creation_date = datetime.datetime.now()
                            order_data['creation_date'] = creation_date
                            mapped_sku_id = get_syncedusers_mapped_sku(usr, order_data['sku_id'])
                            ord_code = str(order_data['order_code'])
                            ord_id = str(order_data['order_id'])
                            order_data['original_order_id'] = ord_code + ord_id
                            order_obj = OrderDetail.objects.filter(order_id=order_data['order_id'], user=usr,
                                                                   sku_id=mapped_sku_id,
                                                                   order_code=order_data['order_code'])
                            if not order_obj:
                                order_data['sku_id'] = mapped_sku_id
                                create_generic_order(order_data, cm_id, user.id, generic_order_id, order_objs,
                                                     is_distributor, order_summary_dict, ship_to, corporate_po_number,
                                                     client_name, admin_user, sku_total_qty_map, order_user_sku,
                                                     order_user_objs, address_selected)
                                ord_det_id = order_summary_dict['order_id']
                                block_asn_stock(mapped_sku_id, qty, lt, ord_det_id)
                            else:
                                created_skus.append(order_data['sku_id'])
                            items.append(
                                [sku_master['sku_desc'], order_data['quantity'], order_data.get('invoice_amount', 0)])
                            wh_name = User.objects.get(id=usr).first_name
                            cont_vals = (order_data['customer_name'], order_data['original_order_id'], wh_name)
                            contents = {"en": "%s placed an order %s to %s warehouse" % cont_vals}
                            users_list = [user.id, admin_user.id]
                            send_push_notification(contents, users_list)
                else:
                    for usr, qty in stock_wh_map.iteritems():
                        order_data['order_id'] = user_order_ids_map[usr]
                        order_data['user'] = usr
                        if qty <= 0:
                            continue
                        # if backorder_flag:
                        #     bqty, bflag = sku_total_qty_map.get(order_data['sku_code'])
                        #     if bflag:
                        #         qty = bqty
                        order_data['quantity'] = qty
                        creation_date = datetime.datetime.now()
                        order_data['creation_date'] = creation_date
                        mapped_sku_id = get_syncedusers_mapped_sku(usr, order_data['sku_id'])
                        ord_code = str(order_data['order_code'])
                        ord_id = str(order_data['order_id'])
                        order_data['original_order_id'] = ord_code + ord_id
                        order_obj = OrderDetail.objects.filter(order_id=order_data['order_id'], user=usr,
                                                               sku_id=mapped_sku_id, order_code=order_data['order_code'])
                        if not order_obj:
                            order_data['sku_id'] = mapped_sku_id
                            create_generic_order(order_data, cm_id, user.id, generic_order_id, order_objs, is_distributor,
                                                 order_summary_dict, ship_to, corporate_po_number, client_name, admin_user,
                                                 sku_total_qty_map, order_user_sku, order_user_objs, address_selected)
                        else:
                            created_skus.append(order_data['sku_id'])
                        items.append([sku_master['sku_desc'], order_data['quantity'], order_data.get('invoice_amount', 0)])
                        wh_name = User.objects.get(id=usr).first_name
                        cont_vals = (order_data['customer_name'], order_data['original_order_id'], wh_name)
                        contents = {"en": "%s placed an order %s to %s warehouse" % cont_vals}
                        users_list = [usr, admin_user.id]
                        send_push_notification(contents, users_list)

            else:
                if not order_id:
                    order_id = get_order_id(user.id)
                order_data['order_id'] = order_id

                if po_number:
                    order_data['order_type'] = 'Transit'

                order_obj = OrderDetail.objects.filter(order_id=order_data['order_id'], user=user.id,
                                                       sku_id=order_data['sku_id'], order_code=order_data['order_code'])
                if not order_obj:
                    if user_type == 'customer':
                        order_data = get_order_customer_details(order_data, request)
                    if payment_received:
                        order_payment = 0
                        if i != (len(myDict['sku_id']) - 1):
                            if float(order_data['invoice_amount']) < float(payment_received):
                                payment_received = float(payment_received) - float(order_data['invoice_amount'])
                                order_payment = float(order_data['invoice_amount'])
                        else:
                            payment_received = float(payment_received)
                            order_payment = float(payment_received)
                        order_data['payment_received'] = order_payment
                    creation_date = datetime.datetime.now()
                    order_data['creation_date'] = creation_date
                    if not order_data.get('original_order_id', ''):
                        order_data['original_order_id'] = str(order_data['order_code']) + str(order_data['order_id'])
                    for item in exclude_order_items:
                        if item in order_data:
                            order_data.pop(item)

                    order_detail = OrderDetail(**order_data)
                    order_detail.save()
                    created_order_objs.append(order_detail)
                    if seller_id:
                        seller_master_id = SellerMaster.objects.filter(seller_id=seller_id, user=user.id)
                        SellerOrder.objects.create(seller_id=seller_master_id[0].id, sor_id=sor_id,
                                                   order_id=order_detail.id,
                                                   quantity=order_detail.quantity, order_status='PENDING',
                                                   creation_date=datetime.datetime.now())

                    order_objs.append(order_detail)
                    order_sku.update({order_detail.sku: order_data['quantity']})
                    created_order_id = order_detail.order_code + str(order_detail.order_id)

                    create_ordersummary_data(order_summary_dict, order_detail, ship_to)

                    created_skus.append(order_data['sku_id'])
                    if myDict.get('location', '') and myDict['location'][i]:
                        serials = ''
                        if myDict.get('serials'):
                            serials = myDict['serials'][i]
                        dispatch_orders[order_detail.id] = {'order_instance': order_detail,
                                                            'data': [{'quantity': order_data['quantity'],
                                                                      'location': myDict['location'][i],
                                                                      'serials': serials}]}
                    custom_order_data(request, order_detail, ex_image_url, custom_order)
                    # contents = {"en": "Order has been placed by %s" % order_data['customer_name']}
                    # player_ids = []
                    # wh_player_qs = OneSignalDeviceIds.objects.filter(user=usr)
                    # if wh_player_qs:
                    #     wh_player_id = wh_player_qs[0].device_id
                    #     player_ids.append(wh_player_id)
                    # send_push_notification(contents, player_ids)
                elif order_obj and order_data['sku_id'] in created_skus:
                    order_det = order_obj[0]
                    order_det.quantity += float(order_data['quantity'])
                    order_det.invoice_amount += order_data['invoice_amount']
                    order_det.save()
                    order_sku[order_det.sku] += order_data['quantity']
                    if dispatch_orders.has_key(order_det.id):
                        serials = ''
                        if myDict.get('serials'):
                            serials = myDict['serials'][i]
                        dispatch_orders[order_det.id]['order_instance'] = order_det
                        dispatch_orders[order_det.id]['data'].append(
                            {'quantity': order_data['quantity'], 'location': myDict['location'][i],
                             'serials': serials})
                mail_items_list = [sku_master['sku_desc'], order_data['quantity'], order_data.get('invoice_amount', 0)]
                if isprava_user.username == 'isprava_admin':
                    mail_items_list.insert(0, host_details+order_detail.sku.image_url)
                items.append(mail_items_list)
                if po_number:
                    OrderPOMapping.objects.create(order_id=order_data['original_order_id'], sku_id=order_data['sku_id'],
                                                  purchase_order_id=po_number.split('_')[-1], status=1,
                                                  creation_date=datetime.datetime.now())
        other_charge_amounts = construct_other_charge_amounts_map(created_order_id, myDict,
                                                                    datetime.datetime.now(), other_charge_amounts, user)
        if extra_order_fields:
            create_extra_fields_for_order(created_order_id, extra_order_fields, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create order failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(myDict), str(e)))
        return HttpResponse("Order Creation Failed")

    try:
        # if not admin_user:
        order_data['client_name'] = sample_client_name
        send_mail_ordered_report(order_detail, telephone, items, other_charge_amounts,
                                 order_data, user, generic_order_id)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create order mail sending failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(myDict), str(e)))
    message = "Success"
    success_messages = ["Success", "Order created, Picklist generated Successfully",
                        "Order Created and Dispatched Successfully", "Order created Successfully"]
    if not admin_user:
        if direct_dispatch == 'true':
            message = direct_dispatch_orders(user, dispatch_orders)
        elif auto_picklist_signal == 'true':
            message = check_stocks(order_sku, user, enable_damaged_stock, order_objs)
        if is_sample == 'true' and created_order_objs:
            create_order_pos(user, created_order_objs)
    else:
        for user_id, order_user_data in order_user_sku.iteritems():
            auto_picklist_signal = get_misc_value('auto_generate_picklist', user_id)
            order_objs = order_user_objs.get(user_id, [])
            log.info("Picklist checking for user %s and order id is %s" % (str(user_id), str(order_user_data)))
            if auto_picklist_signal == 'true':
                message = check_stocks(order_user_data, User.objects.get(id=user_id), enable_damaged_stock, order_objs)
        #qssi push order api call
        is_emiza_order_failed = False
        generic_orders = GenericOrderDetailMapping.objects.filter(generic_order_id=generic_order_id,
                                                                   customer_id=cm_id).\
                                        values('orderdetail__original_order_id', 'orderdetail__user').distinct()
        for generic_order in generic_orders:
            original_order_id = generic_order['orderdetail__original_order_id']
            order_detail_user = User.objects.get(id=generic_order['orderdetail__user'])
            try:
                resp = order_push(original_order_id, order_detail_user, "NEW")
            except Exception as e:
                import traceback
                log.debug('New Order Push Exception: %s' %traceback.format_exc())
                log.info('Order Push failed for %s and params are %s and error statement is %s' % (
                    str(user.username), str(myDict), str(e)))
                resp = {'status': 'Internal Server Error'}

            log.info('New Order Push Status: %s' % (str(resp)))
            if resp.get('Status', '') == 'Failure' or resp.get('status', '') == 'Internal Server Error':
                is_emiza_order_failed = True
                if resp.get('status', '') == 'Internal Server Error':
                    message = "400 Bad Request"
                else:
                    message = resp['Result']['Errors'][0]['ErrorMessage']
                order_detail = OrderDetail.objects.filter(original_order_id=original_order_id, user=order_detail_user.id)
                picklist_number = order_detail.values_list('picklist__picklist_number', flat=True)
                if picklist_number:
                    picklist_number = picklist_number[0]
                ord_detail_ids = order_detail.values_list('id', flat=True)
                order_cancel_functionality(ord_detail_ids)
                if picklist_number:
                    check_picklist_number_created(order_detail_user, picklist_number)

        if generic_order_id and not is_emiza_order_failed:
            check_and_raise_po(generic_order_id, cm_id)
            #create_backorders(backorder_splitup_map, admin_user, sku_total_qty_map)

        if user_type == 'customer' and not is_distributor and message in success_messages:
            # Creating Uploading POs object with file upload pending.
            # upload_po Api is called in front-end if file is present
            upload_po_map = {'uploaded_user_id': request.user.id, 'po_number': corporate_po_number,
                             'customer_name': client_name}
            ord_obj = OrderUploads.objects.filter(**upload_po_map)
            if not ord_obj:
                upload_po_map['uploaded_date'] = datetime.datetime.today()
                ord_obj = OrderUploads(**upload_po_map)
                ord_obj.save()
            else:
                log.info('Uploaded PO Already Created::%s' %(upload_po_map))
    # if message in success_messages:
    # Deleting Customer Cart data after successful order creation
    CustomerCartData.objects.filter(customer_user=request.user.id).delete()

    return HttpResponse(message)


@fn_timer
def direct_dispatch_orders(user, dispatch_orders, creation_date=datetime.datetime.now()):
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(location__zone__zone='DAMAGED_ZONE'). \
        filter(sku__user=user.id, quantity__gt=0)
    picklist_number = int(get_picklist_number(user)) + 1
    mod_locations = []
    loc_serial_mapping_switch = get_misc_value('loc_serial_mapping_switch', user.id)
    serial_nums = ''
    for order_id, orders in dispatch_orders.iteritems():
        order = orders['order_instance']
        for data in orders.get('data', []):
            if loc_serial_mapping_switch == 'true':
                if data['serials']:
                    serial_nums = data['serials'].split(',')
                po_imei_mapping = POIMEIMapping.objects.filter(sku__user=user.id,
                                                               imei_number__in=serial_nums)
                po_mapping_ids = list(po_imei_mapping.values_list('stock_id', flat=True))
                order_stocks = sku_stocks.filter(id__in = po_mapping_ids, sku_id=order.sku_id, location__location=data['location'], quantity__gt=0)
            else:
                order_stocks = sku_stocks.filter(sku_id=order.sku_id, location__location=data['location'], quantity__gt=0)
            needed_quantity = float(data['quantity'])
            val = {}
            val['wms_code'] = order.sku.wms_code
            val['imei'] = data['serials']
            insert_order_serial(None, val, order=order)

            for stock in order_stocks:
                picked_quantity = 0
                if float(stock.quantity) <= needed_quantity:
                    picked_quantity = stock.quantity
                    stock.quantity = 0
                else:
                    picked_quantity = needed_quantity
                    stock.quantity = float(stock.quantity) - picked_quantity
                if stock.quantity < 0:
                    stock.quantity = 0
                stock.save()

                mod_locations.append(stock.location.location)

                new_picklist = Picklist.objects.create(picklist_number=picklist_number, reserved_quantity=0,
                                                       picked_quantity=picked_quantity,
                                                       remarks='Direct-Dispatch Orders', status='dispatched',
                                                       creation_date=creation_date,
                                                       order_id=order.id, stock_id=stock.id)
                pick_loc = PicklistLocation.objects.create(quantity=picked_quantity, status=0,
                                                           creation_date=creation_date,
                                                           updation_date=creation_date, picklist_id=new_picklist.id,
                                                           stock_id=stock.id,
                                                           reserved=0)
                order_summary = SellerOrderSummary.objects.create(picklist_id=new_picklist.id, pick_number=1,
                                                                  quantity=picked_quantity,
                                                                  order_id=order.id, creation_date=creation_date)
                needed_quantity -= picked_quantity
                if needed_quantity <= 0:
                    break
            order.status = 2
            order.save()

    if mod_locations:
        update_filled_capacity(list(set(mod_locations)), user.id)

    return 'Order Created and Dispatched Successfully'


def update_temp_order_detail_status(order_objs):
    for order_obj in order_objs:
        order_obj.status = 1
        order_obj.save()


def check_stocks(order_sku, user, enable_damaged_stock, order_objs, continue_flag=True):
    picklist_exclude_zones = get_exclude_zones(user)
    switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                   'fifo_switch': get_misc_value('fifo_switch', user.id),
                   'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                   'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id)}
    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
        location__zone__zone__in=picklist_exclude_zones).filter(sku__user=user.id, quantity__gt=0)

    if switch_vals['fifo_switch'] == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
            'receipt_date')
        #data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
            'location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    sku_stocks = stock_detail1 | stock_detail2

    sku_id_stocks = sku_stocks.values('id', 'sku_id').annotate(total=Sum('quantity'))
    pick_res_locat = PicklistLocation.objects.prefetch_related('picklist', 'stock').filter(status=1). \
        filter(Q(picklist__order__user=user.id) | Q(picklist__stock__sku__user=user.id)).values(
        'stock__sku_id').annotate(total=Sum('reserved'))
    val_dict = {}
    members = []
    val_dict['pic_res_ids'] = map(lambda d: d['stock__sku_id'], pick_res_locat)
    val_dict['pic_res_quans'] = map(lambda d: d['total'], pick_res_locat)

    val_dict['sku_ids'] = map(lambda d: d['sku_id'], sku_id_stocks)
    val_dict['stock_ids'] = map(lambda d: d['id'], sku_id_stocks)
    val_dict['stock_totals'] = map(lambda d: d['total'], sku_id_stocks)

    for sku in order_sku.keys():
        if sku.relation_type == 'combo':
            combo_data = sku_combos.filter(parent_sku_id=sku.id)
            for combo in combo_data:
                stock_detail, stock_count, sku.wms_code = get_sku_stock(combo.member_sku, sku_stocks, user,
                                                                        val_dict, sku_id_stocks)
                if stock_count < order_sku[sku]:
                    update_temp_order_detail_status(order_objs)
                    return "Order created Successfully"
        else:
            stock_detail, stock_count, sku.wms_code = get_sku_stock(sku, sku_stocks, user, val_dict,
                                                                    sku_id_stocks)
            if stock_count < order_sku[sku]:
                update_temp_order_detail_status(order_objs)
                return "Order created Successfully"

    picklist_number = get_picklist_number(user)
    for order_obj in order_objs:
        is_asn_order = ASNReserveDetail.objects.filter(orderdetail=order_obj.id)
        if is_asn_order and continue_flag: # We cant create Picklist for ASN Order as stock is not yet dispatched.
            update_temp_order_detail_status([order_obj])
            continue
        picklist_generation([order_obj], enable_damaged_stock, picklist_number, user, sku_combos, sku_stocks,
                            switch_vals, status='open', remarks='Auto-generated Picklist')
    check_picklist_number_created(user, picklist_number + 1)

    return "Order created, Picklist generated Successfully"


@csrf_exempt
@login_required
@get_admin_user
def get_warehouses_list(request, user=''):
    user_list = []
    warehouse_type = request.GET.get('warehouse_type', '')
    user_states = {}
    users = [user.id]
    if warehouse_type == 'STORE':
        users = check_and_get_plants(request, users)
    elif warehouse_type == 'STORE_DEPTS':
        users = check_and_get_plants_depts(request, users)
    else:
        admin_user = UserGroups.objects.filter(
            Q(admin_user__username__iexact=user.username) | Q(user__username__iexact=user.username)). \
            values_list('admin_user_id', flat=True)
        user_groups = UserGroups.objects.filter(admin_user_id__in=admin_user).values_list('user_id', flat=True)
        users = User.objects.filter(id__in=user_groups)
    #user_ids = list(users.values_list('id', flat=True))
    admin_user = UserGroups.objects.filter(
        Q(admin_user__username__iexact=user.username) | Q(user__username__iexact=user.username)). \
        values_list('admin_user_id', flat=True)
    user_groups = users.values('username', 'userprofile__state', 'first_name', 'userprofile__company_id',
                               'userprofile__stockone_code')
    for users in user_groups:
        #for key, value in users.iteritems():
        #    if user.username != value and value not in user_list and key not in ['user__userprofile__state']:
        #        user_list.append(value)
        #        warehouse_mapping
        #        user_states[value] = users['user__userprofile__state']
        user_list.append(users['username'])
        user_states[users['username']] = users['userprofile__state']
    return HttpResponse(json.dumps({'warehouses': user_list, 'states': user_states,
                                    'warehouse_mapping': list(user_groups)}))


@csrf_exempt
@login_required
@get_admin_user
def create_stock_transfer(request, user=''):
    warehouse_name = request.POST.get('warehouse_name', '')
    if request.POST.get('source_plant', ''):
        cur_user = request.POST.get('source_plant', '')
        user = User.objects.get(username=cur_user)
        if cur_user == warehouse_name:
            return HttpResponse("Source and Destination should be different")
    all_data = {}
    order_typ = request.POST.get('order_typ', 'ST_INTRA')
    source_seller_id = request.POST.get('source_seller_id', '')
    dest_seller_id = request.POST.get('dest_seller_id', '')
    data_dict = dict(request.POST.iterlists())
    warehouse = User.objects.filter(username=warehouse_name)
    if not warehouse:
        return HttpResponse("Invalid Destination Plant")
    warehouse = warehouse[0]
    urs = [user.id]
    if order_typ == 'ST_INTRA':
        urs.append(warehouse.id)
    if check_consumption_configuration(urs):
        return HttpResponse('MR & Stock Transfer Disable Due to Closing Stock Updations')
    status, source_seller = validate_st_seller(user, source_seller_id, error_name='Source')
    if status:
        return HttpResponse(status)
    status, dest_seller = validate_st_seller(warehouse, dest_seller_id, error_name='Destination')
    if status:
        return HttpResponse(status)
    for i in range(len(data_dict['wms_code'])):
        if not data_dict['wms_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        data_dict['cgst'][i] = data_dict['cgst'][i] if data_dict['cgst'][i] else 0
        data_dict['sgst'][i] = data_dict['sgst'][i] if data_dict['sgst'][i] else 0
        data_dict['igst'][i] = data_dict['igst'][i] if data_dict['igst'][i] else 0
        data_dict['cess'][i] = data_dict['cess'][i] if data_dict['cess'][i] else 0
        mrp = data_dict['mrp'][i] if data_dict.get('mrp', '') and data_dict['mrp'][i] else 0
        cond = (user.username, warehouse.id, source_seller, dest_seller)
        all_data.setdefault(cond, [])
        all_data[cond].append(
            [data_dict['wms_code'][i], data_dict['order_quantity'][i], data_dict['price'][i],data_dict['cgst'][i],
             data_dict['sgst'][i],data_dict['igst'][i], data_dict['cess'][i],data_id, mrp, order_typ])
    f_name = 'stock_transfer_' + warehouse_name + '_'
    status = validate_st(all_data, warehouse)
    if not status:
        all_data = insert_st_gst(all_data, warehouse)
        status = confirm_stock_transfer_gst(all_data, user.username, order_typ = order_typ)
        #rendered_html_data = render_st_html_data(request, user, warehouse, all_data)
        #stock_transfer_mail_pdf(request, f_name, rendered_html_data, warehouse)
    return HttpResponse(status)


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def stock_transfer_delete(request,stock_transfer ='', user=""):
    """ This code will delete the stock tranfer and po selected"""
    reversion.set_user(request.user)
    reversion.set_comment("stock_transfer_delete")
    user = User.objects.get(id=request.GET['warehouse_id'])
    st_time = datetime.datetime.now()
    log.info('Request params for ' + user.username + ' is ' + str(request.GET.dict()))
    log.info("deletion of stock transfer order process started")
    transfer_order_id = request.GET.get("order_id", "")

    try:
        with transaction.atomic('default'):
            stock_transfer_ids = list(StockTransfer.objects.filter(sku__user=user.id, status=1, order_id=transfer_order_id).\
                                                            values_list('id', flat=True))
            stock_transfer_lock = StockTransfer.objects.using('default').select_for_update().filter(id__in=stock_transfer_ids)
            for stock_transfer in stock_transfer_lock:
                st_po = stock_transfer.st_po
                po = st_po.po
                open_st = st_po.open_st
                stock_transfer.cancelled_quantity = stock_transfer.cancelled_quantity + stock_transfer.quantity
                stock_transfer.quantity = 0#stock_transfer.original_quantity - stock_transfer.cancelled_quantity
                stock_transfer.status = 0
                if stock_transfer.original_quantity == stock_transfer.cancelled_quantity:
                    stock_transfer.status = 3
                    po.status = 'location-assigned'
                    po.reason = 'Stock Transfer Cancelled'
                    po.save()
                stock_transfer.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(e)

    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("process completed")
    log.info("total time -- %s" % (duration))
    return HttpResponse("Order is Cancelled")


@csrf_exempt
@login_required
@get_admin_user
def get_marketplaces_list(request, user=''):
    status_type = request.GET.get('status', '')
    marketplace = get_marketplace_names(user, status_type)
    segregation_options = OrderedDict(SELLABLE_CHOICES)
    '''if status_type == 'picked':
        marketplace = list(Picklist.objects.exclude(order__marketplace='').filter(picked_quantity__gt=0, order__user = user.id).\
                                            values_list('order__marketplace', flat=True).distinct())
    elif status_type == 'all_marketplaces':
        marketplace = list(OrderDetail.objects.exclude(marketplace='').filter(user = user.id, quantity__gt=0).values_list('marketplace', flat=True).\
                                                       distinct())
    else:
        marketplace = list(OrderDetail.objects.exclude(marketplace='').filter(status=1, user = user.id, quantity__gt=0).values_list('marketplace', flat=True).\
                                               distinct())'''
    return HttpResponse(json.dumps({'marketplaces': marketplace, 'segregation_options': segregation_options}))


@csrf_exempt
def get_back_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    is_production = get_misc_value('production_switch', user.id)
    user = user
    order_detail = OrderDetail.objects.filter(user=user.id, status=1, quantity__gt=0).values('sku_id', 'sku__wms_code',
                                                                                             'sku__sku_code',
                                                                                             'sku__sku_desc').distinct()
    master_data = []

    stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values('sku_id').distinct(). \
        annotate(in_stock=Sum('quantity'))
    reserved_objs = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1, reserved__gt=0).values(
        'stock__sku_id').distinct(). \
        annotate(reserved=Sum('reserved'))
    order_quantity_objs = OrderDetail.objects.filter(status=1, user=user.id).values('sku_id').distinct(). \
        annotate(order_quantity=Sum('quantity'))

    purchase_objs = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']). \
        filter(open_po__sku__user=user.id). \
        values('open_po__sku_id').annotate(total_order=Sum('open_po__order_quantity'),
                                           total_received=Sum('received_quantity'))

    stocks = map(lambda d: d['sku_id'], stock_objs)
    purchases = map(lambda d: d['open_po__sku_id'], purchase_objs)
    reserveds = map(lambda d: d['stock__sku_id'], reserved_objs)
    order_quantities = map(lambda d: d['sku_id'], order_quantity_objs)

    table_headers = ['WMS Code', 'WMS Code', 'Product Description', 'Ordered Quantity', 'Stock Quantity',
                     'Transit Quantity', 'Procurement Quantity']
    for order in order_detail:
        temp = {}
        production_quantity = 0
        transit_quantity = 0
        stock_quantity = 0
        order_quantity = 0
        if order['sku_id'] in stocks:
            stock_quantity = map(lambda d: d['in_stock'], stock_objs)[stocks.index(order['sku_id'])]
        if order['sku_id'] in reserveds:
            stock_quantity = map(lambda d: d['reserved'], reserved_objs)[reserveds.index(order['sku_id'])]
        if order['sku_id'] in order_quantities:
            order_quantity = map(lambda d: d['order_quantity'], order_quantity_objs)[
                order_quantities.index(order['sku_id'])]

        if order['sku_id'] in purchases:
            total_order = map(lambda d: d['total_order'], purchase_objs)[purchases.index(order['sku_id'])]
            total_received = map(lambda d: d['total_received'], purchase_objs)[purchases.index(order['sku_id'])]
            diff_quantity = float(total_order) - float(total_received)
            if diff_quantity > 0:
                transit_quantity = diff_quantity

        if is_production == 'true':
            production_orders = JobOrder.objects.filter(product_code__sku_code=order['sku__sku_code'],
                                                        product_code__user=user.id). \
                exclude(status__in=['open', 'confirmed-putaway']).values('product_code__sku_code'). \
                annotate(total_order=Sum('product_quantity'), total_received=Sum('received_quantity'))
            if production_orders:
                production_order = production_orders[0]
                diff_quantity = float(production_order['total_order']) - float(production_order['total_received'])
                if diff_quantity > 0:
                    production_quantity = diff_quantity
        procured_quantity = order_quantity - stock_quantity - transit_quantity - production_quantity
        if procured_quantity > 0:
            checkbox = "<input type='checkbox' id='back-checked' name='%s'>" % order['sku__sku_desc']
            temp = OrderedDict(
                (('', checkbox), ('WMS Code', order['sku__wms_code']), ('Product Description', order['sku__sku_desc']),
                 ('Ordered Quantity', order_quantity), ('Stock Quantity', stock_quantity),
                 ('Transit Quantity', transit_quantity), ('Procurement Quantity', procured_quantity),
                 ('DT_RowClass', 'results')
                 ))
            if is_production == 'true':
                temp['In Production Quantity'] = production_quantity
                if not 'In Production Quantity' in table_headers:
                    table_headers.insert(6, 'In Production Quantity')
            master_data.append(temp)
    if search_term:
        master_data = filter(lambda person: search_term in person['WMS Code'] or \
                                            str(search_term).lower() in str(person['Product Description']).lower() or \
                                            search_term in str(person['Ordered Quantity']) or \
                                            search_term in str(person['Stock Quantity']) or search_term in str(
            person['Transit Quantity']) or \
                                            search_term in str(person['Procurement Quantity']), master_data)
    elif order_term:
        if order_term == 'asc':
            master_data = sorted(master_data, key=lambda x: x[table_headers[col_num]])
        else:
            master_data = sorted(master_data, key=lambda x: x[table_headers[col_num]], reverse=True)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    temp_data['aaData'] = master_data[start_index:stop_index]


@csrf_exempt
@get_admin_user
def generate_po_data(request, user=''):
    data_dict = []
    supplier_list = []
    suppliers = SupplierMaster.objects.filter(user=user.id)
    for supplier in suppliers:
        supplier_list.append({'id': supplier.id, 'name': supplier.name})
    for key, value in request.POST.iteritems():
        price = 0
        key = key.split(":")
        selected_item = ''
        sku_supplier = SKUSupplier.objects.filter(sku__wms_code=key[0], sku__user=user.id)
        if sku_supplier:
            selected_item = {'id': sku_supplier[0].supplier_id, 'name': sku_supplier[0].supplier.name}
            price = sku_supplier[0].price
        data_dict.append(
            {'wms_code': key[0], 'title': key[1], 'quantity': value, 'selected_item': selected_item, 'price': price})
    return HttpResponse(json.dumps({'data_dict': data_dict, 'supplier_list': supplier_list}))


@csrf_exempt
@get_admin_user
def generate_jo_data(request, user=''):
    all_data = []
    title = 'Raise Job Order'
    for key, value in request.POST.iteritems():
        data = []
        key = key.split(':')[0]
        bom_master = BOMMaster.objects.filter(product_sku__sku_code=key, product_sku__user=user.id)
        description = ''
        if bom_master:
            for bom in bom_master:
                data.append(
                    {'material_code': bom.material_sku.sku_code, 'material_quantity': float(bom.material_quantity),
                     'id': '', 'measurement_type': bom.unit_of_measurement})
            description = bom.product_sku.sku_desc
        all_data.append({'product_code': key, 'product_description': value,
                         'sub_data': data, 'description': description})
    return HttpResponse(json.dumps({'data': all_data}))


@csrf_exempt
@get_admin_user
def create_stock_transfer_data(request, user=''):
    all_data = []
    title = 'Create Stock Transfer'
    data = []
    key = request.POST.get('WMS Code')
    quantity = int(request.POST.get('Ordered Quantity', 0))
    supplier_data = SKUSupplier.objects.filter(sku__wms_code=key, sku__user=user.id)
    if supplier_data:
        price = supplier_data[0].price * quantity;
    else:
        price = 0

    return HttpResponse(json.dumps({'price': price}))


def get_shipment_number(user):
    order_shipment = OrderShipment.objects.filter(user=user.id).order_by('-shipment_number')
    if order_shipment:
        shipment_number = int(order_shipment[0].shipment_number) + 1
    else:
        shipment_number = 1
    return shipment_number


@csrf_exempt
@get_admin_user
def shipment_info(request, user=''):
    shipment_number = get_shipment_number(user)
    market_place = list(Picklist.objects.filter(order__user=user.id, status__icontains='picked'). \
                        values_list('order__marketplace', flat=True).distinct())
    return HttpResponse(json.dumps({'shipment_number': shipment_number, 'market_places': market_place}))


def create_shipment(request, user):
    from random import randint
    data_dict = copy.deepcopy(ORDER_SHIPMENT_DATA)
    for key, value in request.POST.iteritems():
        if key in ('customer_id', 'marketplace'):
            continue
        elif key == 'shipment_date':
            ship_date = value.split('/')
            data_dict[key] = datetime.date(int(ship_date[2]), int(ship_date[0]), int(ship_date[1]))
        elif key in ORDER_SHIPMENT_DATA.keys():
            data_dict[key] = value
    data_dict['user'] = user.id
    manifest_number = str(user.id)+str(randint(100, 999999))
    manifest_number = random_number_check(manifest_number,user)
    data_dict['manifest_number'] = manifest_number
    data = OrderShipment(**data_dict)
    data.save()
    return data

def random_number_check(manifest_number, user):
    from random import randint
    if OrderShipment.objects.filter(manifest_number = manifest_number).exists():
        manifest_number = str(user.id)+str(randint(100, 999999))
        random_number_check(manifest_number,user)
    return manifest_number

@csrf_exempt
@get_admin_user
def get_under_taking_form(request, user=''):
    id = request.POST.get('id', '')
    original_order_id = request.POST.get('order_id', '')
    imei = request.POST.get('serial_number', '')
    shipment_detail = ShipmentInfo.objects.get(id=id)
    order_detail = shipment_detail.order
    admin_user = get_admin(user)
    if admin_user.username in ['one_assist']:
        if order_detail:
            product_make = order_detail.sku.sku_brand
            product_model = order_detail.sku.sku_code
            customer_name = order_detail.customer_name
        final_data = {'customer_name': customer_name, 'product_make': product_make,
                     'product_model': product_model, 'imei': imei, 'date': ' '}
        if final_data:
            return render(request, 'templates/toggle/order_shipment_confirmation_form.html', final_data)

def upload_signed_under_taking_form(request, user=''):
    from masters import upload_master_file
    user = request.user
    shipment_id = request.POST.get('id', '')
    pdf_file = request.FILES.get('pdf_file', '')
    if not shipment_id and pdf_file:
        return HttpResponse('Fields are missing.')
    try:
        shipment_detail = ShipmentInfo.objects.get(id=shipment_id)
        order_detail = shipment_detail.order
        if order_detail:
            order_obj_id = order_detail.id
            response = upload_master_file(request, user, order_obj_id, 'OneAssistSignedCopies', master_file=pdf_file)
    except Exception as e:
        log.info('Upload PDF is failed for user %s and params are %s and error statement is %s' % (
            str(request.user.username), str(request.POST.dict()), str(e)))
    if response == 'Uploaded Successfully':
        return HttpResponse('Uploaded Successfully')

def get_signed_oneassist_form(request, user=''):
    shipment_id = request.POST.get('shipment_id', '')
    if not shipment_id:
        return HttpResponse('Fields are missing.')
    try:
        one_assist_pdf = []
        shipment_detail = ShipmentInfo.objects.filter(id=shipment_id).values('order_shipment__shipment_number', 'order_shipment__manifest_number', 'order_shipment__user')
        order_detail = ShipmentInfo.objects.filter(**shipment_detail[0]).values_list('order_id', flat=True)
        if order_detail:
            pdf_obj = MasterDocs.objects.filter(master_id__in = order_detail, master_type='OneAssistSignedCopies')
            if pdf_obj:
                images = list(pdf_obj.values_list('uploaded_file', flat=True))
                one_assist_pdf.extend(images)
            else:
                return HttpResponse('Please Upload Signed Invoice Copy')
        else:
            return HttpResponse('No Orders Found')
    except Exception as e:
        log.info('PDF is not Available for user %s and params are %s and error statement is %s' % (
            str(request.user.username), str(request.POST.dict()), str(e)))
    return HttpResponse(json.dumps({'data_dict': one_assist_pdf}))

@csrf_exempt
@get_admin_user
def insert_shipment_info(request, user=''):
    ''' Create Shipment Code '''
    myDict = dict(request.POST.iterlists())
    log.info('Request params are ' + str(request.POST.dict()))
    user_profile = UserProfile.objects.filter(user_id=user.id)
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='dispatch', misc_value='true')
    created_order_objs = []
    try:
        order_shipment = create_shipment(request, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create shipment failed for params ' + str(request.POST.dict()) + ' error statement is ' + str(e))
        return HttpResponse('Create shipment Failed')
    try:
        shipped_orders_dict = {}
        for i in range(0, len(myDict['sku_code'])):
            if not myDict['shipping_quantity'][i]:
                continue
            order_ids = eval(myDict['id'][i])
            if not isinstance(order_ids, list):
                order_ids = [order_ids]
            received_quantity = int(myDict['shipping_quantity'][i])
            for order_id in order_ids:
                if received_quantity <= 0:
                    break
                invoice_number = ''
                if myDict.get('invoice_number',''):
                     invoice_number = myDict.get('invoice_number','')[0]
                data_dict = copy.deepcopy(ORDER_PACKAGING_FIELDS)
                shipment_data = copy.deepcopy(SHIPMENT_INFO_FIELDS)
                order_detail = OrderDetail.objects.get(id=order_id, user=user.id)

                created_order_objs.append(order_detail)
                for key, value in myDict.iteritems():
                    if key in data_dict:
                        data_dict[key] = value[i]
                    if key in shipment_data and key != 'id':
                        shipment_data[key] = value[i]

                # Need to comment below 3 lines if shipment scan is ready
                if 'imei_number' in myDict.keys() and myDict['imei_number'][i]:
                    shipped_orders_dict = insert_order_serial([], {'wms_code': order_detail.sku.wms_code,
                                                                   'imei': myDict['imei_number'][i]},
                                                              order=order_detail,
                                                              shipped_orders_dict=shipped_orders_dict)
                # Until Here
                order_pack_instance = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id,
                                                                    package_reference=myDict['package_reference'][i],
                                                                    box_number=myDict['box_num'][i],
                                                                    order_shipment__user=user.id)
                if not order_pack_instance:
                    data_dict['order_shipment_id'] = order_shipment.id
                    data = OrderPackaging(**data_dict)
                    data.save()
                else:
                    data = order_pack_instance[0]
                picked_orders = Picklist.objects.filter(order_id=order_id, status__icontains='picked',
                                                        order__user=user.id)
                order_quantity = int(order_detail.original_quantity)
                customers_name = order_detail.customer_name
                original_order_id = order_detail.original_order_id
                if order_quantity == 0:
                    continue
                elif order_quantity < received_quantity:
                    shipped_quantity = order_quantity
                    received_quantity -= order_quantity
                elif order_quantity >= received_quantity:
                    shipped_quantity = received_quantity
                    received_quantity = 0

                shipment_data['order_shipment_id'] = order_shipment.id
                shipment_data['order_packaging_id'] = data.id
                shipment_data['order_id'] = order_id
                shipment_data['shipping_quantity'] = shipped_quantity
                shipment_data['invoice_number'] = invoice_number
                ship_data = ShipmentInfo(**shipment_data)
                ship_data.save()

                default_ship_track_status = 'Dispatched'
                tracking = ShipmentTracking.objects.filter(shipment_id=ship_data.id, shipment__order__user=user.id,
                                                           ship_status=default_ship_track_status)
                if not tracking:
                    ShipmentTracking.objects.create(shipment_id=ship_data.id, ship_status=default_ship_track_status,
                                                    creation_date=datetime.datetime.now())
                order_awb_map = OrderAwbMap.objects.filter(original_order_id=order_detail.original_order_id, user=user)
                if order_awb_map.count():
                    order_awb_map.update(status=2)
                else:
                    original_order_id = str(order_detail.order_code) + str(order_detail.order_id)
                    order_awb_map = OrderAwbMap.objects.filter(original_order_id=original_order_id, user=user)
                    if order_awb_map.count():
                        order_awb_map.update(status=2)

                # Need to comment below lines if shipment scan is ready
                if shipped_orders_dict.has_key(int(order_id)):
                    shipped_orders_dict[int(order_id)].setdefault('quantity', 0)
                    shipped_orders_dict[int(order_id)]['quantity'] += float(shipped_quantity)
                else:
                    shipped_orders_dict[int(order_id)] = {}
                    shipped_orders_dict[int(order_id)]['quantity'] = float(shipped_quantity)
                # Until Here

                log.info('Shipemnt Info dict is ' + str(shipment_data))
                ship_quantity = ShipmentInfo.objects.filter(order_id=order_id). \
                    aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
                if (ship_quantity + order_detail.cancelled_quantity) >= int(order_detail.original_quantity):
                    order_detail.status = 2
                    order_detail.save()
                    for pick_order in picked_orders:
                        setattr(pick_order, 'status', 'dispatched')
                        pick_order.save()
        # Need to comment below lines if shipment scan is ready
        if shipped_orders_dict:
            log.info('Order Status update call for user ' + str(user.username) + ' is ' + str(shipped_orders_dict))
            check_and_update_order_status(shipped_orders_dict, user)
            # Until Here
        if misc_detail:
            send_mail_dispatch(order_shipment,invoice_number,original_order_id ,user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(
            'Shipment info saving is failed for params ' + str(request.POST.dict()) + ' error statement is ' + str(e))
    admin_user = get_admin(user)
    if admin_user.username in ['one_assist']:
        if order_detail:
            product_make = order_detail.sku.sku_brand
            product_model = order_detail.sku.sku_code
            imei = order_detail.orderimeimapping_set.values_list('po_imei_id__imei_number', flat=True)
            if imei:
                imei = imei[0]
            else:
                imei = '---------------'
        create_order_pos(user, created_order_objs, admin_user=admin_user)
        final_data = {'customer_name': customers_name, 'product_make': product_make,
                     'product_model': product_model, 'imei': imei, 'date': ' '}
        if final_data:
            return render(request, 'templates/toggle/order_shipment_confirmation_form.html', final_data)
    return HttpResponse(json.dumps({'status': True, 'message': 'Shipment Created Successfully'}))


@csrf_exempt
@get_admin_user
def insert_st_shipment_info(request, user=''):
    ''' Create Shipment Code '''
    myDict = dict(request.POST.iterlists())
    log.info('Request params are ' + str(request.POST.dict()))
    user_profile = UserProfile.objects.filter(user_id=user.id)
    try:
        order_shipment = create_shipment(request, user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create shipment failed for params ' + str(request.POST.dict()) + ' error statement is ' + str(e))
        return HttpResponse('Create shipment Failed')
    try:
        sku_data_eval = len(myDict['sku_data'])
        if sku_data_eval:
            all_sku_data = eval(myDict['sku_data'][0])
        else:
            return HttpResponse('Data not found')
        shipped_orders_dict = {}
        for i in range(0, len(all_sku_data)):
            if not all_sku_data[i]['shipping_quantity']:
                continue
            order_ids = all_sku_data[i]['order_id']
            if not isinstance(order_ids, list):
                order_ids = [order_ids]
            received_quantity = int(all_sku_data[i]['shipping_quantity'])
            for order_id in order_ids:
                if received_quantity <= 0:
                    break
                invoice_number = ''
                data_dict = copy.deepcopy(ORDER_PACKAGING_FIELDS)
                shipment_data = copy.deepcopy(SHIPMENT_INFO_FIELDS)
                order_detail = STOrder.objects.filter(stock_transfer__order_id=order_id, stock_transfer__sku__user=user.id)
                picklist_ids = order_detail.values_list('picklist_id',flat=True)
                if order_detail:
                    order_detail = order_detail[0]
                for key, value in myDict.iteritems():
                    if key in data_dict:
                        data_dict[key] = value[i]
                    if key in shipment_data and key != 'id':
                        shipment_data[key] = value[i]
                # Need to comment below 3 lines if shipment scan is ready
                if 'imei_number' in myDict.keys() or 'imei_list' in all_sku_data[0].keys():
                    shipped_orders_dict = insert_st_order_serial([], {'wms_code': order_detail.stock_transfer.sku.wms_code,
                                            'imei': all_sku_data[i]['imei_list']}, order=order_detail,
                                            shipped_orders_dict=shipped_orders_dict)
                # Until Here
                order_pack_instance = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id,
                                                                    package_reference=all_sku_data[i].get('pack_reference', ''),
                                                                    order_shipment__user=user.id)
                if not order_pack_instance:
                    data_dict['order_shipment_id'] = order_shipment.id
                    data = OrderPackaging(**data_dict)
                    data.save()
                else:
                    data = order_pack_instance[0]
                picked_orders = Picklist.objects.filter(id__in=picklist_ids)
                order_quantity = 0
                stock_transfer_id = order_detail.stock_transfer_id
                if stock_transfer_id:
                    stock_transfer_qty = StockTransfer.objects.get(id=stock_transfer_id).quantity
                    order_quantity = stock_transfer_qty
                #order_quantity = int(order_detail.quantity)
                if order_quantity == 0:
                    continue
                elif order_quantity < received_quantity:
                    shipped_quantity = order_quantity
                    received_quantity -= order_quantity
                elif order_quantity >= received_quantity:
                    shipped_quantity = received_quantity
                    received_quantity = 0
                shipment_data['order_shipment_id'] = order_shipment.id
                shipment_data['order_packaging_id'] = data.id
                shipment_data['order_id'] = order_id
                shipment_data['shipping_quantity'] = shipped_quantity
                shipment_data['invoice_number'] = invoice_number
                ship_data = ShipmentInfo(**shipment_data)
                ship_data.save()

                default_ship_track_status = 'Dispatched'
                tracking = ShipmentTracking.objects.filter(shipment_id=ship_data.id, shipment__order__user=user.id,
                                                           ship_status=default_ship_track_status)
                if not tracking:
                    ShipmentTracking.objects.create(shipment_id=ship_data.id, ship_status=default_ship_track_status,
                                                    creation_date=datetime.datetime.now())
                #if st order not in AWB
                """
                order_awb_map = OrderAwbMap.objects.filter(original_order_id=order_detail.order_id, user=user)
                if order_awb_map.count():
                    order_awb_map.update(status=2)
                else:
                    original_order_id = str(order_detail.order_code) + str(order_detail.order_id)
                    order_awb_map = OrderAwbMap.objects.filter(original_order_id=original_order_id, user=user)
                    if order_awb_map.count():
                        order_awb_map.update(status=2)
                """

                # Need to comment below lines if shipment scan is ready
                if shipped_orders_dict.has_key(int(order_id)):
                    shipped_orders_dict[int(order_id)].setdefault('quantity', 0)
                    shipped_orders_dict[int(order_id)]['quantity'] += float(shipped_quantity)
                else:
                    shipped_orders_dict[int(order_id)] = {}
                    shipped_orders_dict[int(order_id)]['quantity'] = float(shipped_quantity)
                # Until Here

                log.info('Shipemnt Info dict is ' + str(shipment_data))
                ship_quantity = ShipmentInfo.objects.filter(order_id=order_id, order_shipment__user=user.id). \
                    aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
                if ship_quantity >= int(order_quantity):
                    stock_transfer = StockTransfer.objects.filter(order_id=order_id, sku__user=user.id)
                    if stock_transfer:
                        stock_transfer.update(status=3)
                    #order_detail.status = 3
                    #order_detail.save()
                    for pick_order in picked_orders:
                        setattr(pick_order, 'status', 'dispatched')
                        pick_order.save()
        # Need to comment below lines if shipment scan is ready
        if shipped_orders_dict:
            log.info('Order Status update call for user ' + str(user.username) + ' is ' + str(shipped_orders_dict))
            check_and_update_order_status(shipped_orders_dict, user)
            # Until Here
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(
            'Shipment info saving is failed for params ' + str(request.POST.dict()) + ' error statement is ' + str(e))

    return HttpResponse(json.dumps({'status': True, 'message': 'Shipment Created Successfully'}))


@csrf_exempt
@login_required
@get_admin_user
def shipment_info_data(request, user=''):
    headers = ('Order ID', 'SKU Code', 'Shipping Quantity', 'Shipment Reference', 'Pack Reference', 'Status')
    data = []
    loan_proposal_id = 0
    mobile_no = 0
    model = ''
    district = ''
    alternative_mobile_no = 0
    customer_id = request.GET['customer_id']
    shipment_number = request.GET['shipment_number']
    manifest_number = request.GET.get('manifest_number' ,0)
    gateout = request.GET.get('gateout', '')
    if gateout:
        gateout = int(gateout)
    ship_reference = ''
    shipment_orders = ShipmentInfo.objects.filter(order_shipment__shipment_number=shipment_number,order_shipment__manifest_number = manifest_number,
                                                  order_shipment__user=user.id)
    print shipment_orders.count()
    truck_number = ''
    driver_phone_number = ''
    driver_name = ''
    manifest_number = ''
    manifest_date = ''
    if shipment_orders:
        truck_number = shipment_orders[0].order_shipment.truck_number
        driver_name = shipment_orders[0].order_shipment.driver_name
        driver_phone_number = shipment_orders[0].order_shipment.driver_phone_number
        manifest_number = shipment_orders[0].order_shipment.manifest_number
        manifest_date = get_local_date(user,shipment_orders[0].order_shipment.creation_date)
    for orders in shipment_orders:
        ship_status = copy.deepcopy(SHIPMENT_STATUS)
        status = 'Dispatched'
        tracking = ShipmentTracking.objects.filter(shipment_id=orders.id, shipment__order__user=user.id).order_by(
            '-creation_date'). \
            values_list('ship_status', flat=True)
        if tracking:
            status = tracking[0]
            if gateout:
                if status != 'Delivered' and status != 'Out for Delivery':
                    continue
            else:
                if not (status != 'Delivered' and status != 'Out for Delivery'):
                    continue
        interm_obj = IntermediateOrders.objects.filter(order_id=str(orders.order.id))
        if interm_obj:
            order_fields_dict = dict(OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id),
                                       order_type='intermediate_order', user=str(interm_obj[0].user.id)).\
                                       values_list('name', 'value'))
            district = order_fields_dict.get('district', '')
            loan_proposal_id = order_fields_dict.get('loan_proposal_id', '')
            mobile_no = order_fields_dict.get('mobile_no', '')
            alternative_mobile_no = order_fields_dict.get('alternative_mobile_no', '')
            # model = order_fields_dict.get('model', '')
            # district_obj = OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id),name='district')
            # if district_obj:
            #     district = district_obj[0].value
            #     if not district :
            #         district = ''
            # loan_proposal_obj = OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id),name='loan_proposal_id')
            # if loan_proposal_obj :
            #     loan_proposal_id = loan_proposal_obj[0].value
            #     if not loan_proposal_id :
            #         loan_proposal_id = 0
            # model_obj = OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id),name='model')
            # if model_obj :
            #     model = model_obj[0].value
            #     if not model :
            #         model = ''
            # mobile_no_obj = OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id),name='mobile_no')
            # if mobile_no_obj :
            #     mobile_no = mobile_no_obj[0].value
            #     if not mobile_no :
            #         mobile_no = 0
            # alternative_mobile_no_obj = OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id),name='alternative_mobile_no')
            # if alternative_mobile_no_obj :
            #     alternative_mobile_no = alternative_mobile_no_obj[0].value
            #     if not alternative_mobile_no :
            #         alternative_mobile_no = 0
        serial_number = OrderIMEIMapping.objects.filter(po_imei__sku__wms_code =orders.order.sku.sku_code,order_id= orders.order.id,po_imei__sku__user=user.id)
        if serial_number :
            serial_number = serial_number[0].po_imei.imei_number
        else:
            serial_number = 0
        result = {}
        admin_user = get_admin(user)
        if admin_user.get_username().lower() == '72Networks'.lower() :
            try:
                from firebase import firebase
                firebase = firebase.FirebaseApplication('https://pod-stockone.firebaseio.com/', None)
                result = firebase.get('/OrderDetails/'+orders.order.original_order_id, None)
            except Exception as e:
                result = {}
                import traceback
                log.debug(traceback.format_exc())
                log.info('Firebase query  failed for %s and params are %s and error statement is %s' % (
                str(user.username), str(request.POST.dict()), str(e)))
        if not result:
            result = {}
        signed_invoice_copy = result.get('signed_invoice_copy', '')
        id_type = result.get('id_type', '')
        id_card = result.get('id_card', '')
        id_proof_number = result.get('id_proof_number', '')
        pod_status = result.get('pod_status', '')
        status = 'In Transit'
        if pod_status:
            status = 'Delivered'
        ship_status = ship_status[ship_status.index(status):]
        original_order_id = orders.order.original_order_id
        if not original_order_id:
            original_order_id = orders.order.order_code + str(orders.order.order_id)
        data.append({'id': orders.id, 'order_id': original_order_id, 'customer_name':orders.order.customer_name, 'sku_code': orders.order.sku.sku_code,
                     'ship_quantity': orders.shipping_quantity,
                     'model':orders.order.sku.sku_desc,
                     'serial_number':serial_number,
                     'pack_reference': orders.order_packaging.package_reference,
                     'ship_status': ship_status, 'status': status})
        if not ship_reference:
            ship_reference = orders.order_packaging.order_shipment.shipment_reference

    return HttpResponse(json.dumps({'data': data, 'customer_id': customer_id, 'ship_status': SHIPMENT_STATUS,'shipment_number':shipment_number,'manifest_number':manifest_number,
                                    'ship_reference': ship_reference, 'truck_number': truck_number, 'driver_phone_number' : driver_phone_number,'driver_name':driver_name, 'manifest_date':manifest_date},
                                   cls=DjangoJSONEncoder))


def app_shipment_info_data(request, user=''):
    headers = ('Order ID', 'SKU Code', 'Shipping Quantity', 'Shipment Reference', 'Pack Reference', 'Status')
    data = []
    loan_proposal_id = 0
    mobile_no = 0
    model = ''
    district = ''
    alternative_mobile_no = 0
    response = request.GET['manifest_number']
    manifest_number = response.split('/')[0]
    page = response.split('/')[1]
    stop_index = int(page)*10
    start_index = stop_index -10
    ship_reference = ''
    shipment_orders = ShipmentInfo.objects.filter(order_shipment__manifest_number=manifest_number)
    truck_number = ''
    driver_phone_number = ''
    driver_name = ''
    manifest_number = ''
    if shipment_orders:
        truck_number = shipment_orders[0].order_shipment.truck_number
        driver_name = shipment_orders[0].order_shipment.driver_name
        driver_phone_number = shipment_orders[0].order_shipment.driver_phone_number
        manifest_number = shipment_orders[0].order_shipment.manifest_number

    for orders in shipment_orders[start_index:stop_index]:
        ship_status = copy.deepcopy(SHIPMENT_STATUS)
        status = 'Dispatched'
        interm_obj = IntermediateOrders.objects.filter(order_id=str(orders.order.id))
        if interm_obj :
            district_obj = OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id),name='district')
            if district_obj:
                district = district_obj[0].value
                if not district :
                    district = ''
            loan_proposal_obj = OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id),name='loan_proposal_id')
            if loan_proposal_obj :
                loan_proposal_id = loan_proposal_obj[0].value
                if not loan_proposal_id :
                    loan_proposal_id = 0
            model_obj = OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id),name='model')
            if model_obj :
                model = model_obj[0].value
                if not model :
                    model = ''
            mobile_no_obj = OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id),name='mobile_no')
            if mobile_no_obj :
                mobile_no = mobile_no_obj[0].value
                if not mobile_no :
                    mobile_no = 0
            alternative_mobile_no_obj = OrderFields.objects.filter(original_order_id=str(orders.order.original_order_id), order_type='intermediate_order',user=str(interm_obj[0].user.id),name='alternative_mobile_no')
            if alternative_mobile_no_obj :
                alternative_mobile_no = alternative_mobile_no_obj[0].value
                if not alternative_mobile_no :
                    alternative_mobile_no = 0
        serial_number = OrderIMEIMapping.objects.filter(po_imei__sku__wms_code =orders.order.sku.sku_code,order_id= orders.order.id)
        if serial_number :
            serial_number = serial_number[0].po_imei.imei_number
        else:
            serial_number = '0'
        id_card =' '
        signed_invoice_copy =' '
        uid = ' '
        id_proof_number =' '
        time =0
        id_type =' '
        refusal = False
        refusal_reason = ' '
        pod_status = False
        returned = False
        loan_proposal_id = str(orders.order.original_order_id)
        order_return_obj = OrderReturns.objects.filter(order__original_order_id = orders.order.original_order_id,sku__wms_code = orders.order.sku_id)
        if order_return_obj.exists() :
            returned = True
        result = get_firebase_order_data(loan_proposal_id)
        if  result :
            signed_invoice_copy = result.get('signed_invoice_copy','')
            id_type = result.get('id_type','')
            id_card = result.get('id_card','')
            id_proof_number = result.get('id_proof_number','')
            uid = result.get('uid','')
            pod_status = result.get('pod_status',False)
            uid = result.get('uid','')
            refusal = result.get('refusal',False)
            refusal_reason = result.get('refusal_reason','')
        data.append({'id': orders.id,
                     'customer_name':orders.order.customer_name,
                     'sku_code': orders.order.sku.sku_code,
                     'ship_quantity': orders.shipping_quantity,
                     'loan_proposal_id':orders.order.original_order_id,
                     'serial_number':serial_number,
                     'id_card':id_card,
                     'signed_invoice_copy':signed_invoice_copy,
                     'uid':uid,
                     'pod_status': pod_status,
                     'id_proof_number': id_proof_number,
                     'time': time,
                     'id_type' : id_type,
                     'refusal':refusal,
                     'refusal_reason':refusal_reason,
                     'model':model,
                     'returned':returned,
                     'mobile_no':mobile_no,
                     'alternative_mobile_no':alternative_mobile_no,
                     'district':district})
        if not ship_reference:
            ship_reference = orders.order_packaging.order_shipment.shipment_reference
    if manifest_number :
        return HttpResponse(json.dumps({'data': data,'manifest_number':manifest_number,
                                     'truck_number': truck_number, 'driver_phone_number' : driver_phone_number,'driver_name':driver_name},
                                   cls=DjangoJSONEncoder))
    else:
        return HttpResponse("Invalid Manifest Number")


def confirm_order_request(request, user=''):
    confirm_order_number = request.GET['loan_proposal_id']
    from firebase import firebase
    firebase = firebase.FirebaseApplication('https://pod-stockone.firebaseio.com/', None)
    result = firebase.get('/OrderDetails/'+confirm_order_number, None)
    if  result and result['pod_status']:
        delivered_time = time.strftime('%Y-%m-%d', time.localtime(int(result['time'])/1e3))
        try:
            send_request = [{
                "LoanProposalID":result['loan_proposal_id'],
                "DeliveryStatus":'Delivered',
                "DeliveryDate": delivered_time,
                "TypeOfPOD":result['id_type'],
                "POD":result['id_proof_number'],
                "pod1":result['id_card'],
                "pod2":result['signed_invoice_copy']
            }]
            h = httplib2.Http(".cache")
            h.add_credentials('bfil00072', 'c20ed6361a70b18c2265512d5cde8dcc') # Basic authentication
            resp, content = h.request("https://www.72networks.in/amp/stockone_deliver.php", "POST", body=json.dumps(send_request))
            if content:
                return HttpResponse(eval(content)[0].get('Remarks'))
            else:
                return HttpResponse("Failed")
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('72_Networks API Integration Server Error')
            return HttpResponse("Server Not Found")
    else:
        return HttpResponse("Invalid loan proposal ID")

@csrf_exempt
@get_admin_user
def update_shipment_status(request, user=''):
    data_dict = dict(request.GET.iterlists())
    ship_reference = request.GET.get('ship_reference', '')
    truck_number = request.GET.get('truck_number', '')
    for i in range(len(data_dict['id'])):
        shipment_info = ShipmentInfo.objects.get(id=data_dict['id'][i])
        tracking = ShipmentTracking.objects.filter(shipment_id=shipment_info.id, shipment__order__user=user.id,
                                                   ship_status=data_dict['status'][i])
        if not tracking:
            ShipmentTracking.objects.create(shipment_id=shipment_info.id, ship_status=data_dict['status'][i],
                                            creation_date=datetime.datetime.now())
        else:
            tracking.update(ship_status=data_dict['status'][i])

        order_shipment = shipment_info.order_packaging.order_shipment
        if ship_reference:
            order_shipment.shipment_reference = ship_reference
        if truck_number:
            order_shipment.truck_number = truck_number
        order_shipment.save()

    return HttpResponse(json.dumps({'status': True, 'message': "Updated Successfully"}));


@csrf_exempt
@login_required
@get_admin_user
def print_shipment(request, user=''):
    data_dict = dict(request.GET.iterlists())
    report_data = []
    for i in range(0, len(data_dict['ship_id'])):
        for key, value in request.GET.iteritems():
            ship_id = data_dict[key][i]
            order_shipment1 = OrderShipment.objects.filter(shipment_number=ship_id, user=user.id)
            if order_shipment1:
                order_shipment = order_shipment1[0]
            else:
                return HttpResponse('No Records')
            order_package = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id).order_by(
                'package_reference')
            package_data = []
            all_data = {}
            total = {}
            report_data.append({'shipment_number': ship_id, 'date': datetime.datetime.now(),
                                'truck_number': order_shipment.truck_number})
            for package in order_package:
                shipment_info = ShipmentInfo.objects.filter(order_packaging_id=package.id)
                for data in shipment_info:
                    cond = data.order.customer_name
                    all_data.setdefault(cond, [])
                    all_data[cond].append({'pack_reference': str(data.order_packaging.package_reference),
                                           'sku_code': str(data.order.sku.sku_code),
                                           'quantity': str(data.shipping_quantity)})

    for key, value in all_data.iteritems():
        total[key] = 0
        for i in value:
            total[key] += float(i['quantity'])

    headers = ('Package Reference', 'SKU Code', 'Shipping Quantity')
    return render(request, 'templates/toggle/shipment_template.html',
                  {'table_headers': headers, 'report_data': report_data,
                   'package_data': all_data, 'total': total})


@csrf_exempt
@login_required
@get_admin_user
def get_sku_categories(request, user=''):
    price_band_flag = get_misc_value('priceband_sync', user.id)
    if price_band_flag == 'true':
        user = get_admin(user)
    brands, categories, sizes, colors, categories_details = get_sku_categories_data(request, user)
    stages_list = list(
        ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    sub_categories = list(SKUMaster.objects.filter(user=user.id).exclude(sub_category='').values_list('sub_category',
                                                                                                      flat=True).distinct())
    sku_brand = request.GET.get('brand', '')
    images= []
    if sku_brand:
        cluster_masters = dict(list(ClusterSkuMapping.objects.filter(sku__user=user.id, sku__sku_brand=sku_brand).values_list('cluster_name', 'image_url').distinct()))
        for url in cluster_masters:
            if cluster_masters[url]:
                images.append({'cluster_name':url, 'image':cluster_masters[url]})
            else:
                images.append({'cluster_name':url, 'image':'/static/images/categories/default.png'})
    reseller_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    corp_names = []
    if reseller_obj and price_band_flag == 'true':
        reseller_id = reseller_obj[0].customer_id
        res_corps = list(CorpResellerMapping.objects.filter(reseller_id=reseller_id,
                                                   status=1).values_list('corporate_id', flat=True).distinct())
        corp_names = list(CorporateMaster.objects.filter(corporate_id__in=res_corps, user=user.id).values_list('name', flat=True).distinct())

    return HttpResponse(
        json.dumps({'categories': categories, 'brands': brands, 'size': sizes, 'stages_list': stages_list, 'Image_urls': images,
                    'sub_categories': sub_categories, 'colors': colors, 'customization_types': dict(CUSTOMIZATION_TYPES),\
                    'primary_details': categories_details['primary_details'], 'reseller_corporates': corp_names}))


@csrf_exempt
@login_required
@get_admin_user
def get_sku_categories_list(request, user=''):
    sku_master = SKUMaster.objects.filter(user=user.id)
    categories = list(
        sku_master.exclude(sku_category='').only('sku_category').values_list('sku_category', flat=True).distinct())
    brands = list(sku_master.exclude(sku_brand='').only('sku_brand').values_list('sku_brand', flat=True).distinct())
    sizes = list(sku_master.exclude(sku_brand='').only('sku_size').values_list('sku_size', flat=True).order_by('sequence').distinct())
    sizes = list(OrderedDict.fromkeys(sizes))
    colors = list(sku_master.exclude(sku_brand='').exclude(color='').only('color').values_list('color', flat=True).distinct())
    brands, categories, sizes, colors, categories_details = get_sku_categories_data(request, user)
    stages_list = list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    sub_categories = list(sku_master.exclude(sub_category='').values_list('sub_category',
                                                                                                      flat=True).distinct())
    warehouse_groups = list(
                UserGroups.objects.filter(Q(admin_user=user) | Q(user=user)).values_list('user__username',flat=True).distinct())
    return HttpResponse(
        json.dumps({'categories': categories, 'brands': brands, 'size': sizes, 'stages_list': stages_list,
                    'sub_categories': sub_categories, 'colors': colors, 'warehouse_groups': warehouse_groups}))


def fetch_unit_price_based_ranges(dest_loc_id, level, admin_id, wms_code):
    price_ranges_map = {}
    pricemaster_obj = PriceMaster.objects.filter(sku__user=admin_id,
                                                 sku__sku_code=wms_code)

    price_data = NetworkMaster.objects.filter(dest_location_code_id=dest_loc_id).filter(
        source_location_code_id__userprofile__warehouse_level=level). \
        values_list('source_location_code_id', 'price_type')
    nw_pricetypes = [j for i, j in price_data]
    pricemaster_obj = pricemaster_obj.filter(price_type__in=nw_pricetypes)

    if pricemaster_obj:
        for pm_obj in pricemaster_obj:
            pm_obj_map = {'min_unit_range': pm_obj.min_unit_range, 'max_unit_range': pm_obj.max_unit_range,
                          'price': pm_obj.price}
            price_ranges_map.setdefault('price_ranges', []).append(pm_obj_map)

    return price_ranges_map


@get_admin_user
def get_levels(request, user=''):
    """
    API Call to display levels in Customer portal Dropdown
    :param request:
    :param user: Currently Not Used, But need to distinguish levels based on the User.
    :return:
    """
    is_distributor = ''
    cust_obj = CustomerMaster.objects.filter(user=user.id, name=request.user.first_name)
    if cust_obj:
        is_distributor = cust_obj[0].is_distributor
    if is_distributor:
        wh_levels = list(UserProfile.objects.exclude(warehouse_level=0).
                         values_list('warehouse_level', flat=True).distinct().order_by('warehouse_level'))
    else:
        wh_levels = list(UserProfile.objects.values_list('warehouse_level', flat=True).
                         distinct().order_by('warehouse_level'))
    levels = []
    central_admin = get_admin(user)
    users_list = UserGroups.objects.filter(admin_user=central_admin.id).values_list('user').distinct()
    for wh_level in wh_levels:
        levels.append({'warehouse_level': wh_level,
                       'level_name': get_level_name_with_level(user, wh_level, users_list=users_list)})
    levels.append({'warehouse_level': 3, 'level_name': 'L3-IntransitStock'})
    return HttpResponse(json.dumps(levels))


def get_leadtimes(user='', level=0):
    central_admin = get_admin(user)
    same_level_users = get_same_level_warehouses(level, central_admin)
    lead_times = NetworkMaster.objects.filter(dest_location_code=user,
                                              source_location_code_id__in=same_level_users). \
        values_list('lead_time', 'source_location_code').distinct().order_by('lead_time')
    lead_times_dict = OrderedDict()
    for lt, wh_code in lead_times:
        lead_times_dict.setdefault(lt, []).append(wh_code)
    return lead_times_dict


def get_same_level_warehouses(level, central_admin):
    if level == 3:
        level = 1
    users_list = UserGroups.objects.filter(admin_user=central_admin.id).values_list('user').distinct()
    warehouses = UserProfile.objects.filter(user_id__in=users_list, warehouse_level=level).values_list('user_id',
                                                                                                       flat=True)
    return warehouses

def get_stock_qty_leadtime(item, wh_code):
    wms_code = item['wms_code']
    if not isinstance(wh_code, list):
        wh_code = [wh_code]
    lt_stock = StockDetail.objects.filter(sku__user__in=wh_code,
                                          sku__sku_class=item['sku_class'],
                                          quantity__gt=0,
                                          sku__wms_code=wms_code).values_list('sku__wms_code').distinct(). \
        aggregate(Sum('quantity'))['quantity__sum']
    log.info("Stock Avail for SKU Code (%s)::%s::%s" % (wms_code, wh_code, repr(lt_stock)))
    reserved_quantities = PicklistLocation.objects.filter(stock__sku__user__in=wh_code,
                                                          stock__sku__wms_code=wms_code,
                                                          status=1).values_list('stock__sku__wms_code'). \
        aggregate(Sum('reserved'))['reserved__sum']
    log.info("Reserved Qtys for SKU Code (%s)::%s::%s" % (wms_code, wh_code, repr(reserved_quantities)))
    enquiry_res_quantities = EnquiredSku.objects.filter(sku__user__in=wh_code, sku_code=wms_code).\
    exclude(warehouse_level=3).filter(~Q(enquiry__extend_status='rejected')).values_list('sku_code').\
        aggregate(Sum('quantity'))['quantity__sum']
    log.info("EnquiryOrders for SKU Code (%s)::%s::%s" % (wms_code, wh_code, repr(enquiry_res_quantities)))
    if not reserved_quantities:
        reserved_quantities = 0
    if not enquiry_res_quantities:
        enquiry_res_quantities = 0
    if not lt_stock:
        lt_stock = 0
    avail_stock = int(lt_stock) - int(reserved_quantities) - int(enquiry_res_quantities)
    if avail_stock > 0:
        return avail_stock
    else:
        return None


def all_whstock_quant(sku_master, user, level=0, lead_times=None, dist_reseller_leadtime=0):
    stock_display_warehouse = get_misc_value('stock_display_warehouse', user.id)
    if stock_display_warehouse and stock_display_warehouse != "false":
        stock_display_warehouse = stock_display_warehouse.split(',')
        stock_display_warehouse = map(int, stock_display_warehouse)
    else:
        central_admin = get_admin(user)
        stock_display_warehouse = get_same_level_warehouses(level, central_admin)
    stock_qty_all = dict(StockDetail.objects.filter(sku__user__in=stock_display_warehouse,
                                                    sku__sku_class=sku_master[0]['sku_class'],
                                                    quantity__gt=0).values_list('sku__wms_code').distinct().
                         annotate(in_stock=Sum('quantity')))

    purchase_orders_obj = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']). \
        filter(open_po__sku__user__in=stock_display_warehouse,
               open_po__sku__sku_class=sku_master[0]['sku_class'])

    ordered_qties = dict(purchase_orders_obj.values_list('open_po__sku__wms_code').
                         annotate(total_order=Sum('open_po__order_quantity')))
    recieved_qties = dict(purchase_orders_obj.values_list('open_po__sku__wms_code').
                          annotate(total_recieved=Sum('received_quantity')))

    reserved_quantities = dict(PicklistLocation.objects.filter(stock__sku__user__in=stock_display_warehouse,
                                                               stock__sku__sku_class=sku_master[0]['sku_class'],
                                                               status=1).values_list(
        'stock__sku__wms_code').distinct().annotate(in_reserved=Sum('reserved')))

    putaway_pending_job = dict(POLocation.objects.filter(location__zone__user__in=stock_display_warehouse, status=1,
                                                         job_order__product_code__sku_class=sku_master[0][
                                                             'sku_class']).values_list(
        'job_order__product_code__wms_code').distinct().annotate(Sum('quantity')))

    putaway_pending_purchase = dict(
        POLocation.objects.filter(location__zone__user__in=stock_display_warehouse, status=1,
                                  purchase_order__open_po__sku__sku_class=sku_master[0]['sku_class']).values_list(
            'purchase_order__open_po__sku__wms_code').distinct().annotate(Sum('quantity')))

    job_order_pro_qty = dict(JobOrder.objects.filter(product_code__user__in=stock_display_warehouse,
                                                     product_code__sku_class=sku_master[0]['sku_class']).values_list(
        'product_code__wms_code').distinct().annotate(Sum('product_quantity')))

    job_order_rec_qty = dict(JobOrder.objects.filter(product_code__user__in=stock_display_warehouse,
                                                     product_code__sku_class=sku_master[0]['sku_class']).values_list(
        'product_code__wms_code').distinct().annotate(Sum('received_quantity')))
    sku_filter = [sku_master[0]['sku_class']]
    overall_asn_stock = {}
    if level == 3:
        overall_asn_stock = fetch_asn_detailed_qty(sku_filter, stock_display_warehouse)

    day_1_total = 0
    day_3_total = 0
    total_qty = {}
    for item in sku_master:
        ordered_qty = ordered_qties.get(item["wms_code"], 0)
        recieved_qty = recieved_qties.get(item["wms_code"], 0)
        cart_qty, inter_qty = 0, 0
        cart_obj = CustomerCartData.objects.filter(sku__sku_code=item['wms_code'])
        inter_obj = IntermediateOrders.objects.filter(sku__sku_code=item['wms_code'], status='')
        if cart_obj:
            cart_qty = cart_obj.aggregate(Sum('quantity'))['quantity__sum']
        if inter_obj:
            inter_qty = inter_obj.aggregate(Sum('quantity'))['quantity__sum']
        blocked_qty = cart_qty + inter_qty
        item['blocked_quantity'] = blocked_qty

        putaway_pending_job_qty = putaway_pending_job.get(item["wms_code"], 0)
        putaway_pending_purchase_qty = putaway_pending_purchase.get(item["wms_code"], 0)

        job_order_product_qty = job_order_pro_qty.get(item["wms_code"], 0)
        job_order_recieved_qty = job_order_rec_qty.get(item["wms_code"], 0)

        intransit_qty = ordered_qty - recieved_qty

        reserved_qty = reserved_quantities.get(item["wms_code"], 0)
        stock_qty = stock_qty_all.get(item["wms_code"], 0)

        job_order_qty = job_order_product_qty - job_order_recieved_qty + putaway_pending_job_qty

        all_quantity = stock_qty - reserved_qty + intransit_qty + putaway_pending_purchase_qty + job_order_qty
        if user.id in stock_display_warehouse:
            all_quantity -= item['physical_stock']
        item['all_quantity'] = all_quantity
        if level == 3:
            item[10] = overall_asn_stock.get('first_and_nk_set', {}).get(item["wms_code"], 0)
            item[45] = overall_asn_stock.get('second_set', {}).get(item["wms_code"], 0)
            item[90] = overall_asn_stock.get('third_set', {}).get(item["wms_code"], 0)
        if lead_times and level != 3:
            for lead_time, wh_code in lead_times.items():
                output = get_stock_qty_leadtime(item, wh_code)
                if not isinstance(wh_code, list): wh_code = [wh_code]
                nk_map = dict(ASNStockDetail.objects.filter(sku__sku_code=item["wms_code"], sku__user__in=wh_code,
                                                            asn_po_num='NON_KITTED_STOCK',
                                                            status='open').values_list('sku__user').annotate(Sum('quantity')))
                if not output: output = 0
                for wc in wh_code:
                    if nk_map.get(wc):
                        output = output - nk_map[wc]
                if output < 0:
                    output = 0
                if dist_reseller_leadtime and level:
                    item[lead_time + dist_reseller_leadtime] = output
                else:
                    item[lead_time] = output

        day_1_total += item['physical_stock']
        day_3_total += item['all_quantity']
    total_qty['physical_stock'] = day_1_total
    total_qty['all_quantity'] = day_3_total
    return sku_master, total_qty


@csrf_exempt
@login_required
@get_admin_user
def get_sku_catalogs(request, user=''):
    checked_items = eval(request.POST.get('checked_items', '{}'))
    search_key = request.POST.get('sku_class', '')
    if not checked_items:
        data, start, stop = get_sku_catalogs_data(request, user)
    else:
        data = checked_items.values()
        style_quantities = eval(request.POST.get('required_quantity', '{}'))
        for style_data in data:
            if style_quantities.get(style_data['sku_class'], ''):
               style_data['style_data'] = get_cal_style_data(style_data, style_quantities[style_data['sku_class']])
               # style_data['tax_percentage']= '%.1f'%tax_percentage
            else:
                tax = style_data['variants'][0]['taxes']
                if tax:
                    tax = tax[0]
                    tax_percentage = float(tax['sgst_tax']) + float(tax['igst_tax']) + float(tax['cgst_tax'])
                    style_data['tax_percentage']= '%.1f'%tax_percentage
    download_pdf = request.POST.get('share', '')
    if download_pdf:
        remarks = ''
        remarks = MiscDetail.objects.filter(user=user.id, misc_type='customer_pdf_remarks')
        if remarks:
            remarks = remarks[0].misc_value
        display_stock = request.POST.get('display_stock', '')
        bank_dets_check = request.POST.get('bank_details', '')
        addr_dets_check = request.POST.get('address_details', '')
        bank_details = ''
        address_details = {}
        usr_obj = UserProfile.objects.get(user=request.user)
        import base64
        logo_image = ''
        if usr_obj.customer_logo:
            logo_path = usr_obj.customer_logo.url
            try:
                with open(logo_path, "rb") as image_file:
                    logo_image = base64.b64encode(image_file.read())
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info("Exception Raised in Get SKU Catalogs while reading Images")
        if bank_dets_check:
            bank_details = usr_obj.bank_details
        if addr_dets_check:
            address_details = {'phone': usr_obj.phone_number, 'gst': usr_obj.gst_number,
                               'address': usr_obj.address, 'email': usr_obj.user.email}
        user_type = request.POST.get('user_type', '')
        terms_list = request.POST.get('terms_list', '').split('<>')
        admin = get_admin(user)
        image = get_company_logo(admin, COMPANY_LOGO_PATHS)
        date = get_local_date(user, datetime.datetime.now())
        import math
        if user_type in ['reseller', 'dist_customer']:
            t = loader.get_template('templates/reseller_search.html')
            pages = math.ceil(float(len(data))/8)
        else:
            t = loader.get_template('templates/customer_search.html')
            pages = math.ceil(float(len(data))/10)
        rendered = t.render({'data': data, 'user': request.user.first_name, 'date': date,
                             'remarks': remarks, 'display_stock': display_stock, 'image': image,
                             'style_quantities': eval(request.POST.get('required_quantity', '{}')),
                             'terms_list': terms_list, 'pages': int(pages), 'style_count': len(data),
                             'bank_details': bank_details, 'address_details': address_details, 'logo_image':logo_image})

        if not os.path.exists('static/pdf_files/'):
            os.makedirs('static/pdf_files/')
        file_name = 'static/pdf_files/%s_customer_search.html' % str(request.user.id)
        name = str(request.user.id) + "_customer_search"
        pdf_file = 'static/pdf_files/%s.pdf' % name
        file_ = open(file_name, "w+b")
        file_.write(str(rendered))
        file_.close()
        os.system("./phantom/bin/phantomjs ./phantom/examples/rasterize.js ./%s ./%s A4" % (file_name, pdf_file))
        return HttpResponse("static/pdf_files/" + str(request.user.id) + "_customer_search.pdf")
    return HttpResponse(json.dumps({'data': data, 'search_key':search_key, 'next_index': str(start + 20) + ':' + str(stop + 20)},
                                   cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def get_sku_variants(request, user=''):
    from qssi_inventory_api import calc_update_inventory
    filter_params = {'user': user.id}
    get_values = ['wms_code', 'sku_desc', 'image_url', 'sku_class', 'cost_price', 'price', 'mrp', 'id', 'sku_category',
                  'sku_brand', 'sku_size', 'style_name', 'product_type', 'youtube_url']
    reseller_leadtimes = {}
    lead_times = {}
    sku_class = request.POST.get('sku_class', '')
    customer_id = request.POST.get('customer_id', '')
    customer_data_id = request.POST.get('customer_data_id', '')
    sku_code = request.POST.get('sku_code', '')
    is_catalog = request.POST.get('is_catalog', '')
    sale_through = request.POST.get('sale_through', '')
    level = request.POST.get('level', '')
    if level:
        level = int(level)
    else:
        level = 0
    is_style_detail = request.POST.get('is_style_detail', '')
    levels_config = get_misc_value('generic_wh_level', user.id)
    cust_obj = CustomerMaster.objects.filter(user=user.id, name=request.user.first_name)
    if cust_obj:
        is_distributor = cust_obj[0].is_distributor
        dist_reseller_leadtime = cust_obj[0].lead_time
    else:
        dist_reseller_leadtime = 0
        is_distributor = 0
    if sku_class:
        filter_params['sku_class'] = sku_class
    if sku_code:
        filter_params['sku_code'] = sku_code
    if is_catalog:
        filter_params['status'] = 1
    if sale_through:
        filter_params['sale_through__iexact'] = sale_through

    sku_master1 = SKUMaster.objects.filter(**filter_params).values(*get_values).order_by('sequence')
    sku_master = list(sku_master1)
    dist_userid = 0
    if levels_config == 'true':
        if is_distributor:
            customer_user = CustomerUserMapping.objects.filter(user=request.user.id)[0].customer.customer_id
            cm_id = CustomerMaster.objects.filter(customer_id=customer_user, user=user.id)
            if cm_id:
                dist_mapping = WarehouseCustomerMapping.objects.filter(customer_id=cm_id, status=1)
                dist_userid = dist_mapping[0].warehouse_id
                lead_times = get_leadtimes(dist_userid, level)
                if level == 3:
                    lead_times = OrderedDict(((10, None), (45, None), (90, None)))
        else:
            if level:
                if level == 3:
                    reseller_leadtimes = [10, 45, 90]
                else:
                    lead_times = get_leadtimes(user.id, level)
                    reseller_leadtimes = map(lambda x: x + dist_reseller_leadtime, lead_times)
            else:
                lead_times = {dist_reseller_leadtime: user.id}
                reseller_leadtimes = [dist_reseller_leadtime]
    needed_stock_data = {}
    gen_whs = get_gen_wh_ids(request, user, '')
    needed_stock_data['gen_whs'] = gen_whs
    needed_skus = list(sku_master1.values_list('sku_code', flat=True))
    needed_stock_data['stock_objs'] = dict(StockDetail.objects.filter(sku__user__in=gen_whs, quantity__gt=0,
                                            sku__sku_code__in=needed_skus).only('sku__sku_code', 'quantity').\
                                    values_list('sku__sku_code').distinct().annotate(in_stock=Sum('quantity')))
    needed_stock_data['reserved_quantities'] = dict(PicklistLocation.objects.filter(stock__sku__user__in=gen_whs, status=1,
                                                          stock__sku__sku_code__in=needed_skus).\
                                           only('stock__sku__sku_code', 'reserved').\
                                    values_list('stock__sku__sku_code').distinct().annotate(in_reserved=Sum('reserved')))
    needed_stock_data['enquiry_res_quantities'] = dict(EnquiredSku.objects.filter(sku__user__in=gen_whs,
                                                                                  sku__sku_code__in=needed_skus
                                                                                  ).exclude(warehouse_level=3).
                                                filter(~Q(enquiry__extend_status='rejected')).\
                                only('sku__sku_code', 'quantity').values_list('sku__sku_code').\
                                annotate(tot_qty=Sum('quantity')))

    needed_stock_data['purchase_orders'] = dict(PurchaseOrder.objects.exclude(status__in=['location-assigned',
                                                                                     'confirmed-putaway']).\
                                          filter(open_po__sku__user=user.id, open_po__sku__sku_code__in=needed_skus).\
                                          values_list('open_po__sku__sku_code').distinct().\
                                            annotate(total_order=Sum('open_po__order_quantity'),
                                                                             total_received=Sum('received_quantity')).\
                                            annotate(tot_rem=F('total_order')-F('total_received')).\
                                            values_list('open_po__sku__sku_code', 'tot_rem'))
    # needed_stock_data['asn_quantities'] = dict(
    #     ASNStockDetail.objects.filter(quantity__gt=0, sku__sku_code__in=needed_skus).only(
    #         'sku__sku_code', 'quantity').values_list('sku__sku_code').distinct().annotate(in_asn=Sum('quantity')))

    today_filter = datetime.datetime.today()
    hundred_day_filter = today_filter + datetime.timedelta(days=90)
    ints_filters = {'quantity__gt': 0, 'sku__sku_code__in': needed_skus, 'sku__user__in': gen_whs, 'status': 'open'}
    asn_qs = ASNStockDetail.objects.filter(**ints_filters)
    intr_obj_100days_qs = asn_qs.filter(arriving_date__lte=hundred_day_filter)
    intr_obj_100days_ids = intr_obj_100days_qs.values_list('id', flat=True)
    asn_res_100days_qs = ASNReserveDetail.objects.filter(asnstock__in=intr_obj_100days_ids)
    asn_res_100days_qty = dict(asn_res_100days_qs.values_list('asnstock__sku__sku_code').annotate(in_res=Sum('reserved_qty')))

    needed_stock_data['asn_quantities'] = dict(
        intr_obj_100days_qs.values_list('sku__sku_code').distinct().annotate(in_asn=Sum('quantity')))
    for k, v in needed_stock_data['asn_quantities'].items():
        if k in asn_res_100days_qty:
            needed_stock_data['asn_quantities'][k] = needed_stock_data['asn_quantities'][k] - asn_res_100days_qty[k]

    sku_master = get_style_variants(sku_master, user, customer_id=customer_id, customer_data_id=customer_data_id,
                                    levels_config=levels_config, dist_wh_id=dist_userid, level=level,
                                    is_style_detail=is_style_detail, needed_stock_data=needed_stock_data
                                    )
    if get_priceband_admin_user(user) and level != 0:
        integration_obj = Integrations.objects.filter(user=user.id)
        if not integration_obj and not is_distributor:
            dist_customer = WarehouseCustomerMapping.objects.filter(warehouse=user.id, status=1)
            wh_user = dist_customer[0].customer.user
            integration_obj = Integrations.objects.filter(user=wh_user)
        if integration_obj:
            company_name = integration_obj[0].name
            integration_users = Integrations.objects.filter(name=company_name).values_list('user', flat=True)
            api_resp = {}
            for user_id in integration_users:
                user = User.objects.get(id=user_id)
                #if qssi, update inventory first
                if company_name == "qssi":
                    sku_ids = [item['wms_code'] for item in sku_master]
                    suffix_tu_skus = map(lambda x: x+'-TU', sku_ids)
                    all_skus = sku_ids + suffix_tu_skus
                    if not api_resp:
                        api_resp = get_inventory(all_skus, user)
                    calc_update_inventory(api_resp, user)
    sku_master, total_qty = all_whstock_quant(sku_master, user, level, lead_times, dist_reseller_leadtime)
    central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
    sku_spl_attrs = {}
    if central_order_mgmt == 'true':
        sku_id = sku_master[0]['id']
        sku_spl_attrs = dict(SKUAttributes.objects.filter(sku_id=sku_id).values_list('attribute_name', 'attribute_value'))
    _data = {'data': sku_master, 'gen_wh_level_status': levels_config, 'total_qty': total_qty, 'sku_spl_attrs': sku_spl_attrs}
    if level == 2:
        _data['freight_charges'] = "true"
    else:
        _data['freight_charges'] = "false"
    if not is_distributor:
        _data['lead_times'] = reseller_leadtimes
    else:
        _data['lead_times'] = lead_times.keys()
    if levels_config != 'true':
        _data.update({'style_headers': STYLE_DETAIL_HEADERS})
    else:
        _data.update({'style_headers': STYLE_DETAIL_WITHOUT_STATIC_LEADTIME})
    if user.username == 'isprava_admin':
        from stock_locator import get_aggregate_data
        wh_lists = list(get_sister_warehouse(user).values_list('user_id', flat=True))
        sku_codes = []
        selected_sku_code = request.POST.get('sku_class', '')
        sku_codes.append(selected_sku_code)
        warehouses_data = get_aggregate_data(wh_lists, sku_codes)
        _data['available_warehouses_stock'] = warehouses_data
    return HttpResponse(json.dumps(_data))


def modify_invoice_data(invoice_data, user):
    data = {}
    new_data = []
    detailed_invoice = get_misc_value('detailed_invoice', user.id)
    detailed_invoice = True if (detailed_invoice == 'true') else False
    invoice_data['detailed_invoice'] = detailed_invoice
    sku_class = []
    if detailed_invoice:
        mydata = sorted(invoice_data['data'], key=lambda item: item["sku_category"])
        for key, group in groupby(mydata, lambda item: item["sku_category"]):
            data[key] = list(group)

        for one in data.keys():
            category = one

            data_to = sorted(data[one], key=lambda item: item["unit_price"])
            for key2, group2 in groupby(data_to, lambda item: item["unit_price"]):
                price = key2
                discount, invoice_amount, quantity, tax, amount = 0, 0, 0, 0, 0
                sku_list = OrderedDict()
                styles_att = {'discount': 0, 'invoice_amount': 0, 'quantity': 0, 'tax': 0, 'amount': 0, 'sku_size': {},
                              'display_sizes': [], 'amt': 0}
                styles = {}
                sub_total = 0
                amt = 0
                base_price = 0
                taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'cgst_amt': 0, 'sgst_amt': 0, 'igst_amt': 0}
                for single_entry in group2:
                    if not single_entry['sku_class'] in styles:
                        styles[single_entry['sku_class']] = copy.deepcopy(styles_att)
                    styles[single_entry['sku_class']]['sku_size'][single_entry['sku_size']] = int(
                        single_entry['quantity'])
                    if not single_entry['sku_size'] in styles[single_entry['sku_class']]['display_sizes']:
                        styles[single_entry['sku_class']]['display_sizes'].append(single_entry['sku_size'])
                    if not styles[single_entry['sku_class']].has_key('hsn_code'):
                        styles[single_entry['sku_class']]['hsn_code'] = single_entry['hsn_code']
                    discount += float(single_entry['discount'])
                    invoice_amount += float(single_entry['invoice_amount'])
                    quantity += single_entry['quantity']
                    tax += float(single_entry['tax'])
                    amount += invoice_amount
                    main_class = single_entry['sku_class']
                    vat = single_entry['vat']
                    amt += single_entry['amt']
                    base_price = single_entry['base_price']
                    if single_entry.has_key('taxes') and single_entry['taxes'].has_key('cgst_tax'):
                        taxes['cgst_tax'] = single_entry['taxes']['cgst_tax']
                        taxes['sgst_tax'] = single_entry['taxes']['sgst_tax']
                        taxes['igst_tax'] = single_entry['taxes']['igst_tax']
                        taxes['cgst_amt'] += float(single_entry['taxes']['cgst_amt'])
                        taxes['sgst_amt'] += float(single_entry['taxes']['sgst_amt'])
                        taxes['igst_amt'] += float(single_entry['taxes']['igst_amt'])
                total = amount - tax
                formated_inv = "%.2f" % invoice_amount
                new_data.append(
                    {'price': price, 'sku_class': sku_list, 'discount': discount, 'invoice_amount': formated_inv,
                     'quantity': quantity, 'tax': tax, 'amount': amount, 'category': category, 'vat': vat,
                     'styles': styles, 'amt': amt, 'taxes': taxes, 'base_price': base_price})
        invoice_data['data'] = new_data
    return invoice_data


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def generate_order_invoice(request, user=''):
    reversion.set_user(request.user)
    order_ids = request.GET.get('order_ids', '')
    invoice_data = get_invoice_data(order_ids, user)
    invoice_data = modify_invoice_data(invoice_data, user)
    ord_ids = order_ids.split(",")
    invoice_data = add_consignee_data(invoice_data, ord_ids, user)
    user_profile = UserProfile.objects.get(user_id=user.id)
    # invoice_data = build_invoice(invoice_data, user, False)
    if get_misc_value('show_imei_invoice', user.id) == 'true' and user.userprofile.user_type == 'marketplace_user':
        invoice_data = build_marketplace_invoice(invoice_data, user, False)
    else:
        invoice_data = build_invoice(invoice_data, user, False)
    # invoice_data.update({'user': user})
    # if invoice_data['detailed_invoice']:
    #    t = loader.get_template('../miebach_admin/templates/toggle/detail_generate_invoice.html')
    # else:
    #    t = loader.get_template('../miebach_admin/templates/toggle/generate_invoice.html')
    # c = Context(invoice_data)
    # rendered = t.render(c)
    return HttpResponse(invoice_data)


@csrf_exempt
def get_shipment_picked(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                        user_dict={}, filters={}):
    '''Shipment Info datatable code '''

    sku_master, sku_master_ids = get_sku_master(user, request.user)
    if user_dict:
        user_dict = eval(user_dict)
    lis = ['id', 'order__order_id', 'order__sku__sku_code', 'order__title', 'order__customer_id',
           'order__customer_name',
           'order__marketplace', 'picked_quantity']
    data_dict = {'status__icontains': 'picked', 'order__user': user.id, 'picked_quantity__gt': 0}

    if user_dict.get('market_place', ''):
        marketplace = user_dict['market_place'].split(',')
        data_dict['order__marketplace__in'] = marketplace
    if user_dict.get('customer', ''):
        data_dict['order__customer_id'], data_dict['order__customer_name'] = user_dict['customer'].split(':')

    search_params = get_filtered_params(filters, lis[1:])

    if search_term:
        master_data = Picklist.objects.filter(
            Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids)). \
            filter(Q(order__order_id__icontains=search_term) |
                   Q(order__sku__sku_code__icontains=search_term) |
                   Q(order__title__icontains=search_term) | Q(order__customer_id__icontains=search_term) |
                   Q(order__customer_name__icontains=search_term) | Q(picked_quantity__icontains=search_term) |
                   Q(order__marketplace__icontains=search_term), **data_dict). \
            values_list('order_id', flat=True).distinct()

    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = Picklist.objects.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids),
                                              **data_dict). \
            filter(**search_params).order_by(order_data). \
            values_list('order_id', flat=True).distinct()
    else:
        master_data = Picklist.objects.filter(Q(order__sku_id__in=sku_master_ids) | Q(stock__sku_id__in=sku_master_ids),
                                              **data_dict). \
            filter(**search_params).order_by('updation_date'). \
            values_list('order_id', flat=True).distinct()

    master_data = list(OrderedDict.fromkeys(master_data))
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    count = 0
    for dat in master_data[start_index:stop_index]:
        data = OrderDetail.objects.get(id=dat)
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (dat, data.sku.sku_code)
        quantity = data.quantity
        shipped = ShipmentInfo.objects.filter(order_id=dat).aggregate(Sum('shipping_quantity'))[
            'shipping_quantity__sum']
        if shipped:
            quantity = float(quantity) - shipped
            if quantity < 0:
                continue

        temp_data['aaData'].append(
            OrderedDict((('', checkbox), ('Order ID', str(data.order_id)), ('SKU Code', data.sku.sku_code),
                         ('Title', data.title), ('id', count), ('Customer ID', data.customer_id),
                         ('Customer Name', data.customer_name), ('Marketplace', data.marketplace),
                         ('Picked Quantity', quantity),
                         ('DT_RowClass', 'results'), ('order_id', dat))))
        count = count + 1


@csrf_exempt
@get_admin_user
def generate_order_jo_data(request, user=''):
    all_data = []
    title = 'Raise Job Order'
    data_dict = dict(request.POST.iterlists())
    order_id = request.POST.get('order_id', '')
    table_type_name = request.POST.get('table_name', '')
    if table_type_name == 'stock_transfer_order':
        stock_transfer_id = request.POST.getlist('stock_transfer_id', '')
        table_id = request.POST.get('id', '')
        sku_code = request.POST.get('sku_code', '')
        stock_transfer_obj = StockTransfer.objects.filter(id=table_id, order_id__in=stock_transfer_id, sku__sku_code=sku_code, sku__user=user.id)
    else:
        order_details = OrderDetail.objects.none()
        if order_id:
            for i in range(0, len(data_dict['order_id'])):
                main_id = str(data_dict['order_id'][i])
                order_code = ''.join(re.findall('\D+', main_id))
                order_id = ''.join(re.findall('\d+', main_id))
                order_details = order_details | OrderDetail.objects.filter(Q(order_id=order_id, \
                    order_code=order_code) | Q(original_order_id=main_id), user=user.id)
        else:
            order_details = OrderDetail.objects.filter(id__in=data_dict['id'], user=user.id)
            if order_details:
                original_order_id = order_details[0].original_order_id
                order_details = OrderDetail.objects.filter(original_order_id=original_order_id, user=user.id)
    if table_type_name == 'stock_transfer_order':
        for sku_id in stock_transfer_obj.values('sku__id').distinct():
            stock_transfer = stock_transfer_obj.filter(sku__id=sku_id['sku__id'])
            data = []
            product_qty = stock_transfer.aggregate(Sum('quantity'))['quantity__sum']
            data_id = ','.join([str(order_id.id) for order_id in stock_transfer])
            stock_transfer = stock_transfer[0]
            bom_master = BOMMaster.objects.filter(product_sku__sku_code=stock_transfer.sku.sku_code,
                                                                                              product_sku__user=user.id)
            if bom_master:
                for bom in bom_master:
                    data.append({'material_code': bom.material_sku.sku_code, 'material_quantity': float(bom.material_quantity),
                        'id': '', 'measurement_type': bom.unit_of_measurement})
            all_data.append({'order_id': data_id, 'product_code': stock_transfer.sku.sku_code, 'product_description': product_qty, 'description': stock_transfer.sku.sku_desc, 'sub_data': data})
    else:
        for sku_id in order_details.values('sku__id').distinct():
            order_detail= order_details.filter(sku__id=sku_id['sku__id'])
            data = []
            product_qty = order_detail.aggregate(Sum('quantity'))['quantity__sum']
            data_id = ','.join([str(order_id.id) for order_id in order_detail])
            order_detail = order_detail[0]
            bom_master = BOMMaster.objects.filter(product_sku__sku_code=order_detail.sku.sku_code,product_sku__user=user.id)
            if bom_master:
                for bom in bom_master:
                    data.append({'material_code': bom.material_sku.sku_code, 'material_quantity': float(bom.material_quantity), 'id': '', 'measurement_type': bom.unit_of_measurement})
            all_data.append({ 'order_id': data_id, 'product_code': order_detail.sku.sku_code, 'product_description': product_qty, 'description': order_detail.sku.sku_desc, 'sub_data': data })
    return HttpResponse(json.dumps({'data': all_data}))

@get_admin_user
def search_customer_data(request, user=''):
    search_key = request.GET.get('q', '')
    type = request.GET.get('type' ,'')
    total_data = []
    if not search_key:
        return HttpResponse(json.dumps(total_data))

    lis = ['name', 'email_id', 'phone_number', 'address', 'status', 'tax_type']
    filter_params  = {'user':user.id,'status':1}
    if type:
        filter_params['customer_type'] = type
    master_data = CustomerMaster.objects.filter(Q(phone_number__icontains=search_key) | Q(name__icontains=search_key) |
                                                Q(customer_id__icontains=search_key), **filter_params)

    for data in master_data[:30]:
        make, model = '', ''
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        make_obj = MasterAttributes.objects.filter(attribute_id=data.id, attribute_model='customer',
                                                   attribute_name='make')
        if make_obj.exists():
            make = make_obj[0].attribute_value
        model_obj = MasterAttributes.objects.filter(attribute_id=data.id, attribute_model='customer',
                                                   attribute_name='model')
        if model_obj.exists():
            model = model_obj[0].attribute_value
        total_data.append({'customer_id':str(data.customer_id), 'name': data.name, 'phone_number': str(data.phone_number),
                           'chassis_number': data.chassis_number, 'customer_reference': data.customer_reference,
                           'email': data.email_id, 'address': data.address, 'tax_type': data.tax_type,
                           'ship_to': data.shipping_address, 'make': make, 'model': model})
    return HttpResponse(json.dumps(total_data))


@csrf_exempt
@get_admin_user
def generate_order_po_data(request, user=''):
    data_dict = []
    supplier_list = []
    suppliers = SupplierMaster.objects.filter(user=user.id)
    for supplier in suppliers:
        supplier_list.append({'id': supplier.id, 'name': supplier.name, 'tax_type': supplier.tax_type})
    request_dict = dict(request.POST.iterlists())
    table_type_name = request.POST.get('table_name', '')
    if table_type_name == 'stock_transfer_order':
        stock_transfer_id = request.POST.getlist('stock_transfer_id', '')
        table_id = request.POST.get('id', '')
        sku_code = request.POST.get('sku_code', '')
        stock_transfer_obj = StockTransfer.objects.filter(id=table_id, order_id__in=stock_transfer_id, sku__sku_code=sku_code, sku__user=user.id)
        request_dict['order_id'] = stock_transfer_obj.values_list('st_po__po__order_id', flat=True)
        if request_dict.get('order_id', ''):
            order_id = str(request_dict['order_id'][0])
        order_id = stock_transfer_id
        order_id_list = request_dict.get('stock_transfer_id', '')
    else:
        order_id = request.POST.get('order_id', '')
        order_id_list = request_dict.get('order_id','')
    order_details = OrderDetail.objects.none()
    if order_id:
        for i in range(0, len(order_id_list)):
            main_id = str(order_id_list[i])
            order_code = ''.join(re.findall('\D+', main_id))
            order_id = ''.join(re.findall('\d+', main_id))
            order_details = order_details | OrderDetail.objects.filter(Q(order_id=order_id, \
                                                                         order_code=order_code) | Q(
                original_order_id=main_id), user=user.id)
    else:
        order_details = OrderDetail.objects.filter(id__in=request_dict['id'], user=user.id)
        if order_details:
            original_order_id = order_details[0].original_order_id
            order_details = OrderDetail.objects.filter(original_order_id=original_order_id, user=user.id)
    if table_type_name == 'stock_transfer_order':
        for sku_id in stock_transfer_obj.values('sku__id').distinct():
            taxes = {}
            order_detail = stock_transfer_obj.filter(sku__id=sku_id['sku__id'])
            product_qty = order_detail.aggregate(Sum('quantity'))['quantity__sum']
            data_id = ','.join([str(order_id.id) for order_id in order_detail])
            price = 0
            selected_item = ''
            order_detail = order_detail[0]
            sku_supplier = SKUSupplier.objects.filter(sku__wms_code=order_detail.sku.wms_code, sku__user=user.id)
            if sku_supplier:
                selected_item = {'id': sku_supplier[0].supplier_id, 'name': sku_supplier[0].supplier.name}
                price = sku_supplier[0].price
            else:
                selected_item = supplier_list[1]
            data_dict.append({'order_id': data_id, 'wms_code': order_detail.sku.wms_code, 'title': order_detail.sku.sku_desc,
                              'quantity': product_qty, 'selected_item': selected_item, 'price': price})
    else:
        for sku_id in order_details.values('sku__id').distinct():
            taxes = {}
            order_detail = order_details.filter(sku__id=sku_id['sku__id'])
            product_qty = order_detail.aggregate(Sum('quantity'))['quantity__sum']
            data_id = ','.join([str(order_id.id) for order_id in order_detail])
            price = 0
            selected_item = ''
            order_detail = order_detail[0]
            sku_master = SKUMaster.objects.get(sku_code=order_detail.sku.wms_code, user=user.id)
            sku_supplier = SKUSupplier.objects.filter(sku__wms_code=order_detail.sku.wms_code, sku__user=user.id)
            if not sku_supplier:
                attr_mapping = copy.deepcopy(SKU_NAME_FIELDS_MAPPING)
                for attr_key, attr_val in attr_mapping.items():
                    supplier_sku = SKUSupplier.objects.filter(user=user.id,
                                                              supplier_id=supplier_list[1]['id'],
                                                              attribute_type=attr_key,
                                                              attribute_value=getattr(sku_master, attr_val))
                    if supplier_sku.exists():
                        sku_supplier = supplier_sku
            if sku_supplier:
                price, sku_price_details = calculate_price(sku_supplier, sku_master, user)
                if sku_price_details:
                    taxes = sku_price_details[0]['taxes']
                    if taxes:
                        taxes = taxes[0]
                selected_item = {'id': sku_supplier[0].supplier_id, 'name': sku_supplier[0].supplier.name,
                                 'tax_type': sku_supplier[0].supplier.tax_type}
            else:
                selected_item = supplier_list[1]
            data_dict.append({'order_id': data_id, 'wms_code': order_detail.sku.wms_code, 'title': order_detail.sku.sku_desc,
                              'quantity': product_qty, 'selected_item': selected_item, 'price': price,
                              'taxes': taxes, 'original_order_id':order_detail.original_order_id, 'brand': order_detail.sku.sku_brand})
    return HttpResponse(json.dumps({'data_dict': data_dict, 'supplier_list': supplier_list}))

@csrf_exempt
@get_admin_user
def backorder_supplier_data(request, user=''):
    price = 0
    taxes = {}
    request_dict = dict(request.POST.iterlists())
    if request_dict:
        supplier = request_dict['selected_item[id]'][0]
        wms_code = request_dict['wms_code'][0]
    sku_master = SKUMaster.objects.get(sku_code=wms_code, user=user.id)
    sku_supplier = SKUSupplier.objects.filter(sku__wms_code=wms_code, sku__user=user.id, supplier_id=supplier)
    if not sku_supplier:
        attr_mapping = copy.deepcopy(SKU_NAME_FIELDS_MAPPING)
        for attr_key, attr_val in attr_mapping.items():
            supplier_sku = SKUSupplier.objects.filter(user=user.id,
                                                      supplier_id=supplier,
                                                      attribute_type=attr_key,
                                                      attribute_value=getattr(sku_master, attr_val))
            if supplier_sku.exists():
                sku_supplier = supplier_sku
    if sku_supplier:
        price, sku_price_details = calculate_price(sku_supplier, sku_master,user)
        if sku_price_details:
            taxes = sku_price_details[0]['taxes']
            if taxes:
                taxes = taxes[0]
    return HttpResponse(json.dumps({'taxes': taxes, 'price':price}))


def calculate_price(sku_supplier, sku_master, user):
    sku_price_details = get_supplier_sku_price_values(sku_supplier[0].supplier_id, sku_master.sku_code, user)
    mrp_value = sku_master.mrp
    margin_percentage = sku_supplier[0].margin_percentage
    if sku_supplier[0].costing_type == 'Margin Based':
        prefill_unit_price = mrp_value - ((mrp_value * margin_percentage) / 100)
        if len(sku_price_details):
            tax_list=sku_price_details[0].get('taxes',[])
        if len(tax_list):
            tax_list = tax_list[0]
            if tax_list.get('inter_state'):
                tax=tax_list.get('igst_tax',0)+tax_list.get('apmc_tax',0)+tax_list.get('cess_tax',0)
            else:
                tax=tax_list.get('cgst_tax',0)+tax_list.get('sgst_tax',0)+tax_list.get('apmc_tax',0)+tax_list.get('cess_tax',0)

        price = (prefill_unit_price * 100) / (100 + tax)
    elif sku_supplier[0].costing_type == 'Markup Based':
        prefill_unit_price = mrp_value / (1+(markup_percentage/100))
        price = prefill_unit_price
    else:
        price = sku_supplier[0].price
    price = float("%.2f" % price)
    return price, sku_price_details

@csrf_exempt
@get_admin_user
def get_stock_transfer_details(request, user=''):
    ids = request.GET.get('order_id', '')
    main_ids = []
    if ids:
        main_ids = ids.split(",")
    else:
        HttpResponse("Fail")

    total_data = {}
    order_details_data = []

    for order_id in main_ids:
        order_data = get_order_detail_objs(order_id, user)
        for sku_data in order_data:
            if total_data.has_key(sku_data.sku.sku_code):
                total_data[sku_data.sku.sku_code]['order_quantity'] += int(
                    total_data[sku_data.sku.sku_code]['order_quantity'])
            else:
                total_data[sku_data.sku.sku_code] = {'order_quantity': int(sku_data.quantity),
                                                     'wms_code': sku_data.sku.sku_code, 'price': 0}

    order_details_data = total_data.values()

    return HttpResponse(json.dumps({'data_dict': order_details_data}))


@csrf_exempt
@get_admin_user
def get_seller_order_details(request, user=''):
    sor_id = request.GET.get('sor_id', '')
    uor_id = request.GET.get('uor_id', '')
    if not sor_id and uor_id:
        return HttpResponse("Fail")

    order_code = ''.join(re.findall('\D+', uor_id))
    order_id = ''.join(re.findall('\d+', uor_id))
    seller_data = SellerOrder.objects.filter(Q(order__order_id=order_id, order__order_code=order_code) | \
                                             Q(order__original_order_id=order_id), order__user=user.id, sor_id=sor_id,
                                             status=1)

    order_details = seller_data
    seller_details = seller_data[0].seller.json()
    row_id = order_details[0].order_id

    custom_data = OrderJson.objects.filter(order_id=row_id)
    status_obj = ''
    central_remarks = ''
    invoice_types = get_invoice_types(user)
    invoice_type = ''
    customer_order_summary = CustomerOrderSummary.objects.filter(order_id=row_id)
    if customer_order_summary:
        status_obj = customer_order_summary[0].status
        central_remarks = customer_order_summary[0].central_remarks
        invoice_type = customer_order_summary[0].invoice_type

    data_dict = []
    cus_data = []
    order_details_data = []
    sku_id_list = []
    attr_list = []
    if custom_data:
        attr_list = json.loads(custom_data[0].json_data)
        if isinstance(attr_list, dict):
            attr_list = attr_list.get('attribute_data', '')
        else:
            attr_list = []
    for attr in attr_list:
        tuple_data = (attr['attribute_name'], attr['attribute_value'])
        cus_data.append(tuple_data)
    tax_type = ''
    inter_state = 2
    if customer_order_summary:
        inter_state = customer_order_summary[0].inter_state
        if customer_order_summary[0].inter_state == 0:
            tax_type = 'intra_state'
        elif customer_order_summary[0].inter_state == 1:
            tax_type = 'inter_state'
    for one_order in order_details:
        quantity = one_order.quantity
        one_order = one_order.order
        order_id = one_order.order_id
        _order_id = order_id
        order_code = one_order.order_code
        market_place = one_order.marketplace
        order_id = order_code + str(order_id)
        original_order_id = one_order.original_order_id
        if original_order_id:
            order_id = original_order_id
        customer_id = one_order.customer_id
        customer_name = one_order.customer_name
        shipment_date = get_local_date(request.user, one_order.shipment_date)
        phone = one_order.telephone
        email = one_order.email_id
        address = one_order.address
        city = one_order.city
        state = one_order.state
        pin = one_order.pin_code
        sku_id = one_order.sku_id
        sku_id_list.append(sku_id)
        product_title = one_order.title
        invoice_amount = one_order.invoice_amount
        remarks = one_order.remarks
        sku_code = one_order.sku.sku_code
        sku_type = one_order.sku.sku_type
        field_type = 'product_attribute'
        vend_dict = {'printing_vendor': "", 'embroidery_vendor': "", 'production_unit': ""}
        sku_extra_data = {}
        if str(order_code) == 'CO':
            vendor_list = ['printing_vendor', 'embroidery_vendor', 'production_unit']
            for item in vendor_list:
                var = ""
                map_obj = OrderMapping.objects.filter(order__order_id=_order_id, order__user=user.id, mapping_type=item)
                if map_obj:
                    var_id = map_obj[0].mapping_id
                    vend_obj = VendorMaster.objects.filter(id=var_id)
                    if vend_obj:
                        var = vend_obj[0].name
                        vend_dict[item] = var

            order_json = OrderJson.objects.filter(order_id=one_order.id)
            if order_json:
                sku_extra_data = eval(order_json[0].json_data)

        customer_order = one_order.customerordersummary_set.filter()
        sgst_tax = 0
        cgst_tax = 0
        igst_tax = 0
        discount_percentage = 0
        mrp = 0
        if customer_order:
            sgst_tax = customer_order[0].sgst_tax
            cgst_tax = customer_order[0].cgst_tax
            igst_tax = customer_order[0].igst_tax
            mrp = customer_order[0].mrp
            discount_percentage = 0
            if (quantity * one_order.unit_price):
                discount_percentage = float(
                    "%.1f" % (float((customer_order[0].discount * 100) / (quantity * one_order.unit_price))))

        tax_masters = TaxMaster.objects.filter(user_id=user.id, product_type=one_order.sku.product_type,
                                               inter_state=inter_state)
        taxes_data = []
        for tax_master in tax_masters:
            taxes_data.append(tax_master.json())

        if order_id:
            order_charge_obj = OrderCharges.objects.filter(user_id=user.id, order_id=order_id, order_type='order')
            order_charges = list(order_charge_obj.values('charge_name', 'charge_amount', 'id'))

        order_details_data.append(
            {'product_title': product_title, 'quantity': quantity, 'invoice_amount': invoice_amount, 'remarks': remarks,
             'cust_id': customer_id, 'cust_name': customer_name, 'phone': phone, 'email': email, 'address': address,
             'city': city, 'state': state, 'pin': pin, 'shipment_date': str(shipment_date), 'item_code': sku_code,
             'order_id': order_id, 'image_url': one_order.sku.image_url, 'market_place': one_order.marketplace,
             'order_id_code': one_order.order_code + str(one_order.order_id),
             'print_vendor': vend_dict['printing_vendor'],
             'embroidery_vendor': vend_dict['embroidery_vendor'], 'production_unit': vend_dict['production_unit'],
             'sku_extra_data': sku_extra_data, 'sgst_tax': sgst_tax, 'cgst_tax': cgst_tax, 'igst_tax': igst_tax,
             'unit_price': one_order.unit_price, 'discount_percentage': discount_percentage, 'taxes': taxes_data,
             'order_charges': order_charges, 'sku_status': one_order.status, 'mrp': mrp})
    data_dict.append({'cus_data': cus_data, 'status': status_obj, 'ord_data': order_details_data,
                      'central_remarks': central_remarks, 'seller_details': seller_details,
                      'invoice_type': invoice_type, 'invoice_types': invoice_types})

    return HttpResponse(json.dumps({'data_dict': data_dict}))


@csrf_exempt
@get_admin_user
def get_view_order_details(request, user=''):
    view_order_status, check_ord_status = get_view_order_statuses(request, user)
    data_dict = []
    main_id = request.GET.get('order_id', '')

    row_id = request.GET.get('id', '')
    try :
        intermediate_object  = IntermediateOrders.objects.get(order_id=row_id)
        project_name = intermediate_object.project_name
    except:
        project_name = "empty"
    sor_id = request.GET.get('sor_id', '')

    supplier_status, supplier_user, supplier, supplier_parent = get_supplier_info(request)
    if supplier_status:
        request.user.id = supplier.user
        user.id = supplier.user

    if sor_id:
        order_id = request.GET.get('uor_id', '')
        order_code = ''.join(re.findall('\D+', order_id))
        order_id = ''.join(re.findall('\d+', order_id))
        # seller_data = SellerOrder.objects.filter(sor_id = seller, order__order_id = float(order_id[2:]), order__user=user.id)
        seller_data = SellerOrder.objects.filter(Q(order__order_id=order_id, order__order_code=order_code) | \
                                                 Q(order__original_order_id=order_id), order__user=user.id,
                                                 sor_id=sor_id)
        order_details = seller_data[0].order
        row_id = order_details.id
        order_details = [order_details]
    else:
        order_code = ''.join(re.findall('\D+', main_id))
        order_id = ''.join(re.findall('\d+', main_id))
        order_details = OrderDetail.objects.filter(
            Q(order_id=order_id, order_code=order_code) | Q(original_order_id=main_id), user=user.id).exclude(status=3)
        if not row_id:
            row_id = order_details[0].id

    custom_data = OrderJson.objects.filter(order_id=row_id)
    status_obj = ''
    central_remarks = ''
    client_name = ''
    customer_order_summary = CustomerOrderSummary.objects.filter(order_id=row_id)
    invoice_types = get_invoice_types(user)
    invoice_type = ''
    courier_name = ''
    mrp = 0
    if customer_order_summary:
        status_obj = customer_order_summary[0].status
        central_remarks = customer_order_summary[0].central_remarks
        invoice_type = customer_order_summary[0].invoice_type
        client_name = customer_order_summary[0].client_name
        courier_name = customer_order_summary[0].courier_name
        mrp = customer_order_summary[0].mrp

    cus_data = []
    order_details_data = []
    sku_id_list = []
    attr_list = []
    if custom_data:
        attr_list = json.loads(custom_data[0].json_data)
        if isinstance(attr_list, dict):
            attr_list = attr_list.get('attribute_data', '')
        else:
            attr_list = []

    tax_type = ''
    inter_state = 2
    if customer_order_summary:
        inter_state = customer_order_summary[0].inter_state
        if customer_order_summary[0].inter_state == 0:
            tax_type = 'intra_state'
        elif customer_order_summary[0].inter_state == 1:
            tax_type = 'inter_state'

    for attr in attr_list:
        tuple_data = (attr['attribute_name'], attr['attribute_value'])
        cus_data.append(tuple_data)
    for one_order in order_details:
        order_id = one_order.order_id
        _order_id = order_id
        order_code = one_order.order_code
        market_place = one_order.marketplace
        order_id = order_code + str(order_id)
        original_order_id = one_order.original_order_id
        if original_order_id:
            order_id = original_order_id
        customer_id = one_order.customer_id
        customer_name = one_order.customer_name
        shipment_date = get_local_date(request.user, one_order.shipment_date)
        phone = one_order.telephone
        email = one_order.email_id
        address = one_order.address
        city = one_order.city
        state = one_order.state
        pin = one_order.pin_code
        sku_id = one_order.sku_id
        sku_id_list.append(sku_id)
        product_title = one_order.title
        quantity = one_order.quantity
        unit_price = one_order.unit_price
        invoice_amount = one_order.invoice_amount
        remarks = one_order.remarks
        sku_code = one_order.sku.sku_code
        sku_type = one_order.sku.sku_type
        sku_brand = one_order.sku.sku_brand
        order_sku_attributes = []
        if one_order.original_order_id and one_order.sku.id:
            order_sku_attr = OrderFields.objects.filter(user=user.id, original_order_id=one_order.original_order_id, order_type='order_sku', extra_fields=one_order.sku.id)
            if order_sku_attr.exists():
                for datum in order_sku_attr:
                    tmp_obj = {}
                    tmp_obj[datum.name] = datum.value
                    order_sku_attributes.append(tmp_obj)
        field_type = 'product_attribute'
        vend_dict = {'printing_vendor': "", 'embroidery_vendor': "", 'production_unit': ""}
        sku_extra_data = {}
        if str(order_code) == 'CO':
            vendor_list = ['printing_vendor', 'embroidery_vendor', 'production_unit']
            for item in vendor_list:
                var = ""
                map_obj = OrderMapping.objects.filter(order__order_id=_order_id, order__user=user.id, mapping_type=item)
                if map_obj:
                    var_id = map_obj[0].mapping_id
                    vend_obj = VendorMaster.objects.filter(id=var_id)
                    if vend_obj:
                        var = vend_obj[0].name
                        vend_dict[item] = var

            order_json = OrderJson.objects.filter(order_id=one_order.id)
            if order_json:
                sku_extra_data = json.loads(order_json[0].json_data)
                if sku_extra_data.get('image_data', ''):
                    for key, value in sku_extra_data['image_data'].iteritems():
                        sku_extra_data['image_data'][key] = resize_image(value, user)

        customer_order = CustomerOrderSummary.objects.filter(order_id=one_order.id)
        sgst_tax = 0
        cgst_tax = 0
        igst_tax = 0
        cess_tax = 0
        payment_status = ''
        discount_percentage = 0
        discount = 0
        mrp = 0
        if customer_order:
            client_name = customer_order[0].client_name
            sgst_tax = customer_order[0].sgst_tax
            cgst_tax = customer_order[0].cgst_tax
            igst_tax = customer_order[0].igst_tax
            cess_tax = customer_order[0].cess_tax
            discount_percentage = 0
            mrp = customer_order[0].mrp
            payment_status = customer_order[0].payment_status
            discount = customer_order[0].discount
            if (quantity * unit_price):
                discount_percentage = float(
                    "%.1f" % (float((customer_order[0].discount * 100) / (quantity * unit_price))))

        tax_masters = TaxMaster.objects.filter(user_id=user.id, product_type=one_order.sku.product_type,
                                               inter_state=inter_state)
        taxes_data = []
        for tax_master in tax_masters:
            taxes_data.append(tax_master.json())

        if order_id:
            order_charge_obj = OrderCharges.objects.filter(user_id=user.id, order_id=order_id, order_type='order')
            order_charges = list(order_charge_obj.values('charge_name', 'charge_amount', 'id'))

        order_details_data.append(
            {'product_title': product_title, 'sku_brand': sku_brand, 'quantity': quantity, 'invoice_amount': float("%.2f" % invoice_amount), 'remarks': remarks,
             'cust_id': customer_id, 'cust_name': customer_name, 'phone': phone, 'email': email, 'address': address,
             'city': city,
             'state': state, 'pin': pin, 'shipment_date': str(shipment_date), 'item_code': sku_code,
             'order_id': order_id,
             'image_url': one_order.sku.image_url, 'market_place': one_order.marketplace,
             'project_name':project_name,
             'order_id_code': one_order.order_code + str(one_order.order_id),
             'print_vendor': vend_dict['printing_vendor'],
             'embroidery_vendor': vend_dict['embroidery_vendor'], 'production_unit': vend_dict['production_unit'],
             'sku_extra_data': sku_extra_data, 'sgst_tax': sgst_tax, 'cgst_tax': cgst_tax, 'igst_tax': igst_tax,
             'cess_tax': cess_tax, 'order_sku_attributes': order_sku_attributes,
             'unit_price': float("%.2f" % unit_price), 'discount_percentage': discount_percentage, 'discount': float("%.2f" % discount),
             'taxes': taxes_data,
             'order_charges': order_charges,
             'sku_status': one_order.status, 'client_name':client_name, 'payment_status':payment_status, 'mrp':float("%.2f" % mrp)})
    if status_obj in view_order_status:
        view_order_status = view_order_status[view_order_status.index(status_obj):]
    data_dict.append({'cus_data': cus_data, 'status': status_obj, 'ord_data': order_details_data,
                      'central_remarks': central_remarks, 'all_status': view_order_status, 'tax_type': tax_type,
                      'invoice_type': invoice_type, 'invoice_types': invoice_types, 'courier_name':courier_name})
    hide_buttons = False
    return HttpResponse(json.dumps({'data_dict': data_dict, 'hide_buttons':hide_buttons}))


def get_stock_location_quantity_data(wms_code, location, user):
    filter_params = {'sku__user': user.id}
    picklist_filter = {'stock__sku__user': user.id, 'status': 1}
    rm_filter = {'material_picklist__jo_material__material_code__user': user.id, 'status': 1}
    if wms_code:
        sku_master = SKUMaster.objects.filter(user=user.id, wms_code=wms_code)
        if not sku_master:
            return 0, 'Invalid SKU Code'
        filter_params['sku__wms_code'] = wms_code
        picklist_filter['stock__sku__wms_code'] = wms_code
        rm_filter['stock__sku__wms_code'] = wms_code

    if location:
        location_master = LocationMaster.objects.filter(zone__user=user.id, location=location)
        if not location_master:
            return 0, 'Invalid Location'
        filter_params['location__location'] = location
        picklist_filter['stock__location__location'] = location
        rm_filter['stock__location__location'] = location

    stock_quantity = StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE').filter(**filter_params). \
        aggregate(Sum('quantity'))['quantity__sum']

    reserved_quantity = PicklistLocation.objects.filter(**picklist_filter).aggregate(Sum('reserved'))['reserved__sum']

    raw_reserved = RMLocation.objects.filter(**rm_filter).aggregate(Sum('reserved'))['reserved__sum']
    if not stock_quantity:
        stock_quantity = 0
    if not reserved_quantity:
        reserved_quantity = 0
    if raw_reserved:
        reserved_quantity += float(raw_reserved)
    diff = stock_quantity - reserved_quantity

    if diff < 0:
        diff = 0

    return diff, ''


@csrf_exempt
@get_admin_user
def get_stock_location_quantity(request, user=''):
    wms_code = request.GET.get('wms_code')
    location = request.GET.get('location')
    diff, message = get_stock_location_quantity_data(wms_code, location, user)
    if message:
        return HttpResponse(json.dumps({'message': message}))

    return HttpResponse(json.dumps({'stock': diff, 'message': 'Success'}))


@login_required
@csrf_exempt
@get_admin_user
def payment_tracker(request, user=''):
    response = {}
    total_payment_received = 0
    total_invoice_amount = 0
    total_payment_receivable = 0
    data_dict = OrderedDict()
    status_filter = request.GET.get('filter', '')
    user_filter = {'order__user': user.id, 'order_status_flag':'customer_invoices'}
    result_values = ['invoice_number', 'order__customer_name', 'order__customer_id', 'order__marketplace',
                        'order__order_id', 'order__original_order_id', 'order__order_code', 'full_invoice_number']
    master_data = SellerOrderSummary.objects.filter(**user_filter)\
                        .exclude(full_invoice_number='')\
                        .values(*result_values).distinct()\
                        .annotate(payment_received = Sum('order__payment_received'), invoice_amount = Sum('order__invoice_amount'))
    customer_data = []
    master_data = master_data.exclude(invoice_amount=F('payment_received'))
    for data in master_data:
        seller_ord_summary = SellerOrderSummary.objects.filter(**user_filter)\
                                      .filter(full_invoice_number=data['full_invoice_number'])
        picked_amount = seller_ord_summary.values('order__sku_id', 'order__invoice_amount', 'order__quantity')\
                                        .distinct().annotate(pic_qty=Sum('quantity'))\
                                        .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                        .aggregate(Sum('cur_amt'))['cur_amt__sum']
        payment_received = float(data['payment_received'])
        payment_obj = PaymentSummary.objects.filter(invoice_number=data['full_invoice_number'], order__user = user.id)
        if payment_obj:
            payment_received = payment_obj.aggregate(payment_received = Sum('payment_received'))['payment_received']
        if round(picked_amount) > round(float(payment_received)):
            receivable = picked_amount - payment_received
            total_payment_received += payment_received
            total_invoice_amount += picked_amount
            total_payment_receivable += receivable
            grouping_key = data['order__customer_id']
            data_dict.setdefault(grouping_key, {'channel': data['order__marketplace'],
                                                'customer_name':data['order__customer_name'],
                                                'customer_id': data['order__customer_id'],
                                                'invoice_amount': 0,
                                                'payment_received': 0,
                                                'payment_receivable': 0
                                                })
            data_dict[grouping_key]['invoice_amount'] +=picked_amount
            data_dict[grouping_key]['payment_received'] +=payment_received
            data_dict[grouping_key]['payment_receivable'] +=receivable

    order_data_loop = data_dict.values()
    data_append = []
    for data1 in order_data_loop:
        data1['invoice_amount'] = float("%.2f" % data1['invoice_amount'])
        data1['payment_received'] = float("%.2f" % data1['payment_received'])
        data1['payment_receivable'] = float("%.2f" % data1['payment_receivable'])
        customer_data.append(data1)
    response["data"] = customer_data
    response.update({'total_payment_received': "%.2f" % total_payment_received,
                     'total_invoice_amount': "%.2f" % total_invoice_amount,
                     'total_payment_receivable': "%.2f" % total_payment_receivable})
    return HttpResponse(json.dumps(response))


@login_required
@get_admin_user
@csrf_exempt
def get_customer_list(request, user=''):
    '''all customers for multiselect in outbound payments'''

    user_profile = UserProfile.objects.get(user_id=user)
    user_filter = {'order__user': user.id, 'order_status_flag': 'customer_invoices'}
    result_values = ['order__customer_name', 'order__customer_id']
    customer_data = []
    response = {}

    master_data = SellerOrderSummary.objects.filter(**user_filter)\
                    .exclude(invoice_number='')\
                    .values(*result_values).distinct()\
                    .annotate(invoice_amount = Sum('order__invoice_amount'),\
                     payment_received = Sum('order__payment_received'))
    for data in master_data:
        payment_receivable = data['invoice_amount'] - data['payment_received']
        data_dict = OrderedDict((('customer_name', data['order__customer_name']),
                                ('customer_id', data['order__customer_id']),
                                ('invoice_amount', "%.2f" % data['invoice_amount']),
                                ('payment_received', "%.2f" % data['payment_received']),
                                ('payment_receivable', "%.2f" % payment_receivable)
                               ))
        customer_data.append(data_dict)

    response["data"] = customer_data
    return HttpResponse(json.dumps(response))

@csrf_exempt
def get_inv_based_payment_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                         filters):
    ''' Invoice Based Payment Tracker datatable code '''
    data_dict = OrderedDict()
    user_profile = UserProfile.objects.get(user_id=user.id)
    admin_user = get_priceband_admin_user(user)
    lis = ['invoice_number', 'order__customer_name', 'invoice_number', 'invoice_number','invoice_number', 'invoice_number', 'creation_date', 'invoice_number']#for filter purpose
    user_filter = {'order__user': user.id, 'order_status_flag': 'customer_invoices'}
    result_values = ['invoice_number', 'order__customer_name', 'order__customer_id', 'full_invoice_number']#to make distinct grouping
    cust_ids = request.POST.get("customer_ids", '')
    if cust_ids:
        cust_ids = cust_ids.split(',')
        cust_ids = [int(id) for id in cust_ids]
        user_filter['order__customer_id__in'] = cust_ids
    #invoice date= seller order summary creation date
    #invoice_date = get_local_date(user, invoice_date, send_date='true')
    #invoice_date = invoice_date.strftime("%d %b %Y")

    if search_term:
        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(lis, search_term)
        master_data = SellerOrderSummary.objects.filter(search_query, **user_filter)\
                        .exclude(invoice_number='')\
                        .values(*result_values).distinct()\
                        .annotate(payment_received = Sum('order__payment_received'), invoice_amount = Sum('order__invoice_amount'))

    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            order_by = '%s' % lis[col_num]
        else:
            order_by = '-%s' % lis[col_num]
        master_data = SellerOrderSummary.objects.filter(**user_filter)\
                        .exclude(invoice_number='')\
                        .values(*result_values).distinct()\
                        .annotate(payment_received = Sum('order__payment_received'), invoice_amount = Sum('order__invoice_amount'))\
                        .order_by('-%s' % lis[col_num])
    else:
        master_data = SellerOrderSummary.objects.filter(**user_filter)\
                            .exclude(invoice_number='')\
                            .values(*result_values).distinct()\
                            .annotate(payment_received = Sum('order__payment_received'), invoice_amount = Sum('order__invoice_amount'))
    master_data = master_data.exclude(invoice_amount=F('payment_received'))
    # temp_data['recordsTotal'] = master_data.count()
    # temp_data['recordsFiltered'] = temp_data['recordsTotal']

    for data in master_data:
        credit_period, due_date, invoice_date = 0, '', ''
        seller_ord_summary = SellerOrderSummary.objects.filter(**user_filter)\
                                      .filter(full_invoice_number=data['full_invoice_number'])
        order_ids = seller_ord_summary.values_list('order__id', flat= True)
        picked_amount = seller_ord_summary.values('order__sku_id', 'order__invoice_amount', 'order__quantity')\
                                        .distinct().annotate(pic_qty=Sum('quantity'))\
                                        .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                        .aggregate(Sum('cur_amt'))['cur_amt__sum']
        order_amt_cal = OrderDetail.objects.filter(id__in=order_ids).aggregate(invoice_amount = Sum('invoice_amount'), payment_received=Sum('payment_received'))
        invoice_date = seller_ord_summary[0].creation_date
        customer_order_sum = CustomerOrderSummary.objects.filter()
        customer_master_obj = CustomerMaster.objects.filter(customer_id = data['order__customer_id'])
        if customer_master_obj:
            credit_period = customer_master_obj[0].credit_period
        if invoice_date:
            due_date = (invoice_date + datetime.timedelta(days=credit_period)).strftime("%d %b %Y")
            invoice_date = invoice_date.strftime("%d %b %Y")
        payment_received = 0
        payment_obj = PaymentSummary.objects.filter(invoice_number=data['full_invoice_number'], order__user = user.id)
        if payment_obj:
            payment_received = payment_obj.aggregate(payment_received = Sum('payment_received'))['payment_received']
        payment_receivable = round(picked_amount) - round(payment_received)
        grouping_key = data['invoice_number']
        data_dict.setdefault(grouping_key, {'due_date': due_date,
                                            'invoicee_date': invoice_date,
                                            'invoice_number': data['invoice_number'],
                                            'customer_name':data['order__customer_name'],
                                            'customer_id': data['order__customer_id'],
                                            'invoice_amount': round(picked_amount),
                                            'payment_received': round(payment_received),
                                            'payment_receivable': payment_receivable
                                            })
    order_data_loop = data_dict.values()
    data_append = []
    for data1 in order_data_loop:
        if round(data1['invoice_amount']) > round(float(data1['payment_received'])):
            data_append.append(data1)
    temp_data['recordsTotal'] =len(data_append)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data in data_append[start_index:stop_index]:
        temp_data['aaData'].append(data)


@login_required
@csrf_exempt
@get_admin_user
def get_invoice_payment_tracker(request, user=''):
    response = {}
    invoice_number = request.GET.get('invoice_number', '')
    customer_id = request.GET.get('customer_id', '')
    if not invoice_number:
        return "Invoice number is missing"
    user_filter = {'order__user': user.id, "invoice_number": invoice_number,
                   "order__customer_id": customer_id, 'order_status_flag__in': ['delivery_challans', 'customer_invoices']}
    result_values = ['challan_number', 'order__order_id', 'order__original_order_id',
                     'order__customer_id', 'order__customer_name', 'invoice_number']
    #customer_id = request.GET['id']
    customer_name = request.GET.get('customer_name')
    master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct()\
                                    .annotate(invoice_amount_sum = Sum('order__invoice_amount'),\
                                    payment_received_sum = Sum('order__payment_received'))
    order_data = []
    expected_date = ''
    for data in master_data:
        seller_ord_summary = SellerOrderSummary.objects.filter(**user_filter)\
                                      .filter(invoice_number=data['invoice_number'])
        picked_amount = seller_ord_summary.values('order__sku_id', 'order__invoice_amount', 'order__quantity')\
                                        .distinct().annotate(pic_qty=Sum('quantity'))\
                                        .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                        .aggregate(Sum('cur_amt'))['cur_amt__sum']
        payment_received = 0
        payment_obj = PaymentSummary.objects.filter(invoice_number=data['invoice_number'], order__user = user.id)
        if payment_obj:
            payment_received = payment_obj.aggregate(payment_received = Sum('payment_received'))['payment_received']
        payment_receivable = round(picked_amount) - round(payment_received)
        order_data.append(
            {'order_id': str(data['order__order_id']), 'display_order': data['challan_number'],
             'account': '', 'original_order_id': data['order__original_order_id'],
             'inv_amount': round(picked_amount),
             'receivable': payment_receivable ,
             'received': round(payment_received),
             'invoice_number': data['invoice_number'],
             'expected_date': expected_date})
    response["data"] = order_data
    return HttpResponse(json.dumps(response))



@login_required
@csrf_exempt
@get_admin_user
def update_inv_payment_status(request, user=''):
    data_dict = dict(request.GET.iterlists())
    for i in range(0, len(data_dict['order_id'])):
        if not data_dict['amount'][i]:
            continue
        payment = float(data_dict['amount'][i])
        order_details = OrderDetail.objects.filter(order_id=data_dict['order_id'][i], user=user.id,
                                                   payment_received__lt=F('invoice_amount'))
        payment_id = get_incremental(user, "payment_summary", 1)
        entered_amount = float(data_dict.get('entered_amount', {}).get(i, 0))
        balance_amount = float(data_dict.get('balance_amount', {}).get(i, 0))
        tds_amount = float(data_dict.get('tds_amount', {}).get(i, 0))
        for order in order_details:
            if not payment:
                break
            if float(order.invoice_amount) > float(order.payment_received):
                diff = float(order.invoice_amount) - float(order.payment_received)
                if payment > diff:
                    order.payment_received = diff
                    payment -= diff
                    PaymentSummary.objects.create(order_id=order.id, creation_date=datetime.datetime.now(),
                                                  payment_received=diff)
                else:
                    PaymentSummary.objects.create(order_id=order.id, creation_date=datetime.datetime.now(),
                                                  payment_received=payment)
                    order.payment_received = float(order.payment_received) + float(payment)
                    payment = 0
                order.save()
    return HttpResponse("Success")




@login_required
@csrf_exempt
@get_admin_user
def get_customer_payment_tracker(request, user=''):
    response = {}
    customer_id = request.GET['id']
    customer_name = request.GET['name']
    # channel = request.GET['channel']
    status_filter = request.GET.get('filter', '')
    data_dict = OrderedDict()
    user_filter = {'order__user': user.id, 'order_status_flag': 'customer_invoices',
                    'order__customer_name':customer_name, 'order__customer_id':customer_id}
    result_values = ['invoice_number', 'full_invoice_number','order__customer_name', 'order__customer_id', 'order__order_id', 'order__original_order_id', 'order__order_code']
    master_data = SellerOrderSummary.objects.filter(**user_filter)\
                        .exclude(full_invoice_number='')\
                        .values(*result_values).distinct()\
                        .annotate(payment_received = Sum('order__payment_received'), invoice_amount = Sum(F('order__invoice_amount')))
    master_data = master_data.exclude(invoice_amount=F('payment_received'))
    order_data = []
    for data in master_data:
        credit_period, due_date, invoice_date = 0, '', ''
        seller_ord_summary = SellerOrderSummary.objects.filter(**user_filter)\
                                      .filter(full_invoice_number=data['full_invoice_number'])
        order_ids = seller_ord_summary.values_list('order__id', flat= True)
        picked_amount = seller_ord_summary.values('order__sku_id', 'order__invoice_amount', 'order__quantity')\
                                        .distinct().annotate(pic_qty=Sum('quantity'))\
                                        .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                        .aggregate(Sum('cur_amt'))['cur_amt__sum']
        order_amt_cal = OrderDetail.objects.filter(id__in=order_ids).aggregate(invoice_amount = Sum('invoice_amount'), payment_received=Sum('payment_received'))
        invoice_date = seller_ord_summary[0].creation_date
        customer_order_sum = CustomerOrderSummary.objects.filter()
        customer_master_obj = CustomerMaster.objects.filter(customer_id = data['order__customer_id'])
        if customer_master_obj:
            credit_period = customer_master_obj[0].credit_period
        if invoice_date:
            due_date = (invoice_date + datetime.timedelta(days=credit_period)).strftime("%d %b %Y")
            invoice_date = invoice_date.strftime("%d %b %Y")
        payment_received = float(data['payment_received'])
        payment_obj = PaymentSummary.objects.filter(invoice_number=data['full_invoice_number'], order__user = user.id)
        if payment_obj:
            payment_received = payment_obj.aggregate(payment_received = Sum('payment_received'))['payment_received']
        payment_receivable = picked_amount - payment_received
        order_id = str(data['order__order_code']) + str(data['order__order_id'])
        grouping_key = data['full_invoice_number']
        data_dict.setdefault(grouping_key, {'expected_date': due_date,
                                            'order_id': str(data['order__order_id']),
                                            'display_order': order_id,
                                            'invoicee_date': invoice_date,
                                            'invoice_number': data['full_invoice_number'],
                                            'customer_name':data['order__customer_name'],
                                            'customer_id': data['order__customer_id'],
                                            'inv_amount': float("%.2f" % picked_amount),
                                            'received': float("%.2f" % payment_received),
                                            'receivable': float("%.2f" % payment_receivable)
                                            })
    order_data_loop = data_dict.values()
    data_append = []
    for data1 in order_data_loop:
        if round(data1['inv_amount']) > round(float(data1['received'])):
            order_data.append(data1)
    response["data"] = order_data
    return HttpResponse(json.dumps(response))


@login_required
@csrf_exempt
@get_admin_user
def get_customer_master_id(request, user=''):
    customer_id = 1
    reseller_price_type = ''
    customer_master = CustomerMaster.objects.filter(user=user.id).values_list('customer_id', flat=True).order_by(
        '-customer_id')
    if customer_master:
        customer_id = customer_master[0] + 1

    price_band_flag = get_misc_value('priceband_sync', user.id)
    level_2_price_type = ''
    admin_user = user
    if price_band_flag == 'true':
        admin_user = get_admin(user)
        level_2_price_type = 'D1-R'
    if user.userprofile.warehouse_type == 'DIST':
        reseller_price_type = 'D-R'

    price_types = get_distinct_price_types(admin_user)
    return HttpResponse(json.dumps({'customer_id': customer_id, 'tax_data': TAX_VALUES, 'price_types': price_types,
                                    'level_2_price_type': level_2_price_type, 'price_type': reseller_price_type}))

@login_required
@csrf_exempt
@get_admin_user
def get_company_master_id(request, user=''):
    company_id = 1
    company_master = CompanyMaster.objects.filter().values_list('id', flat=True).order_by(
        '-id')
    if company_master:
        company_id = company_master[0] + 1
    return HttpResponse(json.dumps({'id': company_id}))

def get_order_ids(user, invoice_number):
    sell_ids = {}
    sell_ids['order__user'] = user.id
    sell_ids['full_invoice_number'] = invoice_number
    seller_summary = SellerOrderSummary.objects.filter(**sell_ids)
    order_id_list = list(set(seller_summary.values_list('order__order_id', flat=True)))
    order_id_list = map(lambda x: str(x), order_id_list)
    return order_id_list


@login_required
@csrf_exempt
@get_admin_user
def update_payment_status(request, user=''):
    today_date = datetime.datetime.today()
    if request.method == "POST":
        data_dict = dict(request.POST.iterlists())
        invoice_numbers = []
        order_ids = []
        for key, val in data_dict.iteritems():
            if "[invoice_number]" in key:
                invoice_numbers.append(request.POST.get(key))
    else:
        data_dict = dict(request.GET.iterlists())
        invoice_numbers = [request.GET.get('invoice_number', '')]
    payment_id = get_incremental(user, "payment_summary", 1)
    payment_log.info('Update payment request from user %s is %s' % (str(user.username),str(data_dict)))
    for index, invoice_number in enumerate(invoice_numbers):
        order_ids = get_order_ids(user, invoice_number)
        data_dict['order_id'] = order_ids
        entered_amount, balance_amount, tds_amount = 0,0,0

        if request.method == "POST":
            payment = float(data_dict.get('data['+str(index)+'][amount]', [0])[0])
            entered_amount = float(data_dict.get('data['+str(index)+'][enter_amount]', [0])[0])
            balance_amount = float(data_dict.get('data['+str(index)+'][balance]', [0])[0])
            tds_amount = float(data_dict.get('data[0][update_tds][0]', [0])[0])
            bank = data_dict.get('data[0][bank_name]', [''])[0]
            mode_of_pay = data_dict.get('data[0][mode_of_pay]', [''])[0]
            remarks = data_dict.get('data[0][neft_cheque]', [''])[0]
            payment_date = data_dict.get('data[0][date]', [None])[0]
            if payment_date:
                payment_date = datetime.datetime.strptime(payment_date, "%m/%d/%Y")
        else:
            payment = float(data_dict['amount'][0])
            bank = request.GET.get('bank', '')
            mode_of_pay = request.GET.get('mode_of_payment', '')
            remarks = request.GET.get('remarks', '')
            payment_date = today_date.strftime('%Y-%m-%d')
        if not payment:
            continue

        # for i in range(0, len(data_dict['order_id'])):
        order_details = OrderDetail.objects.filter(order_id__in=data_dict['order_id'], user=user.id,
                                                   payment_received__lt=F('invoice_amount'))
        picked_amount = SellerOrderSummary.objects.filter(full_invoice_number=invoice_number, order__user=user.id).values('order__sku_id', 'order__invoice_amount', 'order__quantity')\
                                                  .distinct().annotate(pic_qty=Sum('quantity'))\
                                                  .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                                  .aggregate(Sum('cur_amt'), payment_received=Sum('order__payment_received'))
        if order_details:
            order = order_details.aggregate(payment_received=Sum('payment_received'), invoice_amount=Sum('invoice_amount'))
            # for order in order_details:
            payment_received = 0
            invoice_amount = round(picked_amount['cur_amt__sum'])
            payment_obj = PaymentSummary.objects.filter(invoice_number=invoice_number, order__user=user.id)
            if payment_obj:
                payment_received = payment_obj.aggregate(payment_received = Sum('payment_received'))['payment_received']
            if not payment:
                break
            payment_received = round(payment_received)
            if float(invoice_amount) > float(payment_received):
                diff = float(invoice_amount) - float(payment_received)
                if payment > diff:
                    order_details[0].payment_received = diff
                    payment -= diff
                    PaymentSummary.objects.create(order_id=order_details[0].id, creation_date=datetime.datetime.now(),\
                                                  payment_received=diff, bank=bank, mode_of_pay=mode_of_pay,\
                                                  remarks=remarks, payment_id=payment_id,\
                                                  entered_amount=entered_amount, balance_amount=balance_amount,\
                                                  tds_amount=tds_amount, payment_date=payment_date, invoice_number=invoice_number)
                else:
                    PaymentSummary.objects.create(order_id=order_details[0].id, creation_date=datetime.datetime.now(),\
                                                  payment_received=payment, bank=bank,\
                                                  mode_of_pay=mode_of_pay, remarks=remarks,\
                                                  payment_id=payment_id, entered_amount=entered_amount,\
                                                  balance_amount=balance_amount, tds_amount=tds_amount,\
                                                  payment_date=payment_date, invoice_number=invoice_number)
                    order_details[0].payment_received = float(payment_received) + float(payment)
                    payment = 0
                order_details[0].save()
            payment_log.info('Payment updated for user %s of amount %s for invoice_number %s' % (str(user.username),str(order_details[0].payment_received), str(invoice_number)))
    return HttpResponse(json.dumps({'status': True, 'message': 'Payment Successfully Completed !'}))


@csrf_exempt
def get_outbound_payment_report(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):

    ''' Outbound Payment Report datatable code '''
    data_dict = OrderedDict()
    headers, search_params, filter_params = get_search_params(request)
    user_profile = UserProfile.objects.get(user_id=user.id)
    admin_user = get_priceband_admin_user(user)
    lis = ['payment_id', 'payment_date', 'invoice_number', 'order__customer_name', 'order__invoice_amount', 'payment_received', 'mode_of_pay', 'remarks']#for filter purpose
    user_filter = {'order__user': user.id}
    result_values = ['payment_id', 'payment_date', 'invoice_number',
                     'mode_of_pay', 'remarks', 'order__customer_name', 'order__customer_id',
                     'order__invoice_amount', 'payment_received', 'order__order_id', 'order__quantity']#to make distinct grouping
    #filter
    if 'from_date' in search_params:
        from_date = datetime.datetime.combine(search_params['from_date'], datetime.time())
        user_filter['creation_date__gt'] = from_date
    if 'to_date' in search_params:
        to_date = datetime.datetime.combine(search_params['to_date'] + datetime.timedelta(1), datetime.time())
        user_filter['creation_date__lt'] = to_date
    if 'customer' in search_params:
        user_filter['order__customer_name'] = search_params['customer']
    if 'invoice_number' in search_params:
        user_filter['invoice_number'] = search_params['invoice_number']
    cust_ids = request.POST.get("customer_ids", '')
    if cust_ids:
        cust_ids = cust_ids.split(',')
        cust_ids = [int(id) for id in cust_ids]
        user_filter['order__customer_id__in'] = cust_ids
    all_received_amounts = PaymentSummary.objects.filter(**user_filter)\
                            .exclude(Q(invoice_number='') | Q(payment_id=''))\
                            .filter(order__user=user.id).values('invoice_number', 'order__customer_id').distinct()\
                            .annotate(tot_rcvd_amt=Sum('payment_received'))\
                            .values_list('order__customer_id', 'invoice_number', 'tot_rcvd_amt')
    competed_inv_nos = []
    for item in all_received_amounts:
        #if item in all_invoice_numbers:
            competed_inv_nos.append(item[1])
    if search_term:
        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(lis, search_term)
        master_data = PaymentSummary.objects.filter(search_query, **user_filter)\
                        .values(*result_values).distinct()\
                        .annotate(payments_received = Sum('payment_received'))


    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            order_by = '%s' % lis[col_num]
        else:
            order_by = '-%s' % lis[col_num]
        master_data = PaymentSummary.objects.filter(invoice_number__in=competed_inv_nos)\
                        .filter(**user_filter)\
                        .values(*result_values).distinct()\
                        .annotate(payments_received = Sum('payment_received'))\
                        .order_by(order_by)
    else:
        master_data = PaymentSummary.objects.filter(invoice_number__in=competed_inv_nos)\
                            .filter(**user_filter)\
                            .values(*result_values).distinct()\
                            .annotate(payments_received = Sum('payment_received'))
    for data in master_data:
        seller_order_summary = SellerOrderSummary.objects.filter(full_invoice_number=data['invoice_number'], order__user=user.id)
        picked_amount = seller_order_summary.values('order__invoice_amount', 'order__quantity')\
                                               .distinct().annotate(pic_qty=Sum('quantity'))\
                                               .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                               .aggregate(Sum('cur_amt'))['cur_amt__sum']
        grouping_key = data['payment_id']
        payment_date = data['payment_date'].strftime("%d %b %Y") if data['payment_date'] else ''
        if not picked_amount:
            picked_amount = 0
        data_dict.setdefault(grouping_key, {'payment_id': data['payment_id'],
                                            'payment_date': payment_date,
                                            'invoicee_number': data['invoice_number'],
                                            'mode_of_pay':data['mode_of_pay'],
                                            'remarks': data['remarks'],
                                            'customer_name':data['order__customer_name'],
                                            'customer_id': data['order__customer_id'],
                                            'invoice_amount': float('%.2f' % picked_amount),
                                            'payment_received':0
                                            })
        data_dict[grouping_key]['payment_received'] += data['payments_received']
    order_data_loop = data_dict.values()
    temp_data['recordsTotal'] =len(order_data_loop)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data1 in order_data_loop[start_index:stop_index]:
        data1['payment_received'] = float('%.2f' % data1['payment_received'])
        temp_data['aaData'].append(data1)


@login_required
@csrf_exempt
@get_admin_user
def create_orders_data(request, user=''):
    tax_types = copy.deepcopy(TAX_VALUES)
    if not get_misc_value('stop_default_tax', user.id) == 'true':
        tax_types.insert(0,{'tax_name': 'DEFAULT', 'tax_value': ''})
    invoice_types = get_invoice_types(user)
    mode_of_transport = get_mode_of_transport(user)
    return HttpResponse(json.dumps({'payment_mode': PAYMENT_MODES, 'taxes': tax_types,
                                    'invoice_types': invoice_types, 'mode_of_transport': mode_of_transport }))


@csrf_exempt
@get_admin_user
def dispatch_serial_numbers(request, user=''):
    myDict = dict(request.POST.iterlists())
    if myDict['dispatch_Serial_data'][0]:
        data = json.loads(myDict['dispatch_Serial_data'][0])
    else:
        return HttpResponse("Enter Dispatch Data")
    final_data = OrderedDict()
    data_dict = OrderedDict()
    sku_code,sku_id,sku_desc,location = '','','',''
    for i in range(0, len(data)):
        sku_code = data[i]['sku_code']
        serial_number = data[i]['serial_number']
        if serial_number:
            check_params = {'imei_number': serial_number, 'sku__user': user.id}
            po_mapping = POIMEIMapping.objects.filter(**check_params)
            if po_mapping.exists():
                location = po_mapping[0].stock.location.location
        if sku_code:
            sku = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
            if sku.exists():
                sku_id = sku[0].id
                sku_desc = sku[0].sku_desc
        cost_price = float(data[i]['cost_price'])
        selling_price = float(data[i]['selling_price'])
        group_key = sku_code
        final_data.setdefault(group_key, {'sku_code': sku_code, 'location':location, 'sku_id': sku_id,'sku_desc': sku_desc, 'serial_number': [], 'cost_price':0, 'selling_price':0})
        final_data[group_key]['selling_price'] += selling_price
        final_data[group_key]['cost_price'] += cost_price
        final_data[group_key]['serial_number'].append(serial_number)
    final_data = final_data.values()

    return HttpResponse(json.dumps({'serial_data': final_data}))


@csrf_exempt
def get_order_category_view_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                                 filters={}, user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_dict = eval(user_dict)

    lis = ['id', 'customer_name', 'order_id', 'address', 'sku__sku_category', 'total', 'city', 'status']

    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}

    if user_dict.get('market_places', ''):
        marketplace = user_dict['market_places'].split(',')
        data_dict['marketplace__in'] = marketplace
    if user_dict.get('customer_id', ''):
        data_dict['customer_id'], data_dict['customer_name'] = user_dict['customer_id'].split(':')

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_params = get_filtered_params(filters, lis[1:])

    if 'order_id__icontains' in search_params.keys():
        order_search = search_params['order_id__icontains']
        search_params['order_id__icontains'] = ''.join(re.findall('\d+', order_search))
        search_params['order_code__icontains'] = ''.join(re.findall('\D+', order_search))
    search_params['sku_id__in'] = sku_master_ids
    order_taken_val_user = CustomerOrderSummary.objects.filter(order__user=user.id)
    single_search = "no"
    if 'city__icontains' in search_params.keys():
        single_search = "yes"
        order_taken_val_user = CustomerOrderSummary.objects.filter(
            Q(order_taken_by__icontains=search_params['city__icontains']))
        del (search_params['city__icontains'])
    if not request.user.is_staff:
        perm_status_list, check_ord_status = get_view_order_statuses(request, user)
        if check_ord_status:
            search_params['customerordersummary__status__in'] = perm_status_list

    if search_term:
        mapping_results = OrderDetail.objects.filter(**data_dict).values('customer_name', 'order_id',
                                                                         'sku__sku_category',
                                                                         'order_code', 'original_order_id', 'address').distinct(). \
            annotate(total=Sum('quantity')).filter(Q(customer_name__icontains=search_term) |
                                                   Q(order_id__icontains=search_term) |
                                                   Q(sku__sku_category__icontains=search_term)|
                                                   Q(original_order_id__icontains=search_term),
                                                   **search_params).exclude(order_code="CO").order_by(order_data)
    else:
        mapping_results = OrderDetail.objects.filter(**data_dict).exclude(order_code="CO").values('customer_name',
                                                                                                  'order_id',
                                                                                                  'sku__sku_category',
                                                                                                  'order_code',
                                                                                                  'original_order_id', 'address').distinct(). \
            annotate(total=Sum('quantity')).filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    index = 0
    for dat in mapping_results[start_index:stop_index]:
        cust_status_obj = CustomerOrderSummary.objects.filter(order__order_id=dat['order_id'])
        if cust_status_obj:
            cust_status = cust_status_obj[0].status
        else:
            cust_status = ""

        order_id = dat['order_code'] + str(dat['order_id'])
        check_values = order_id + '<>' + dat['sku__sku_category']
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (check_values, dat['total'])
        order_taken_val = ''
        if order_taken_val_user:
            order_taken_val = order_taken_val_user.filter(order__order_id=dat['order_id'])
            if order_taken_val:
                order_taken_val = order_taken_val[0].order_taken_by
            else:
                order_taken_val = ''
        if single_search == "yes" and order_taken_val == '':
            continue

        temp_data['aaData'].append(OrderedDict((('data_value', check_values), ('Customer Name', dat['customer_name']),
                                                ('Order ID', order_id), ('Category', dat['sku__sku_category']),
                                                ('Total Quantity', dat['total']), ('Order Taken By', order_taken_val),
                                                ('Address', dat['address']), ('Status', cust_status),
                                                ('id', index), ('DT_RowClass', 'results'))))
        index += 1


    col_val = ['Customer Name', 'Customer Name', 'Order ID', 'Address', 'Category', 'Total Quantity', 'Order Taken By', 'Status']

    if order_term:
        order_data = col_val[col_num]
        if order_term == "asc":
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data])
        else:
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data], reverse=True)


@csrf_exempt
def get_order_view_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters,
                        user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_dict = eval(user_dict)
    lis = ['order_id', 'customer_name', 'order_id', 'address', 'marketplace', 'total', 'shipment_date', 'date_only',
        'city', 'status', 'order_reference']

    # unsort_lis = ['Customer Name', 'Order ID', 'Market Place ', 'Total Quantity']
    unsorted_dict = {8: 'Order Taken By', 9: 'Status'}
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    if user_dict.get('market_places', ''):
        marketplace = user_dict['market_places'].split(',')
        data_dict['marketplace__in'] = marketplace
    if user_dict.get('customer_id', ''):
        data_dict['customer_id'], data_dict['customer_name'] = user_dict['customer_id'].split(':')
    search_params = get_filtered_params(filters, lis[1:])

    if 'shipment_date__icontains' in search_params.keys():
        search_params['shipment_date__regex'] = search_params['shipment_date__icontains']
        del search_params['shipment_date__icontains']
    if 'order_id__icontains' in search_params.keys():
        order_search = search_params['order_id__icontains']
        search_params['order_id__icontains'] = ''.join(re.findall('\d+', order_search))
        search_params['order_code__icontains'] = ''.join(re.findall('\D+', order_search))
    search_params['sku_id__in'] = sku_master_ids

    if 'city__icontains' in search_params.keys():
        order_taken_val_user = CustomerOrderSummary.objects.filter(
            order_taken_by__icontains=search_params['city__icontains'],
            order__user=user.id)
        search_params['id__in'] = order_taken_val_user.values_list('order_id', flat=True)
        del (search_params['city__icontains'])
    if 'status__icontains' in search_params.keys():
        stat_search = {}
        if search_params.has_key('id__in'):
            stat_search['order_id__in'] = search_params['id__in']
        order_taken_val_user = CustomerOrderSummary.objects.filter(status__icontains=search_params['status__icontains'],
                                                                   order__user=user.id, **stat_search)
        search_params['id__in'] = order_taken_val_user.values_list('order_id', flat=True)
        del (search_params['status__icontains'])

    custom_search = False
    if col_num in unsorted_dict.keys():
        custom_search = True

    if not request.user.is_staff:
        perm_status_list, check_ord_status = get_view_order_statuses(request, user)
        if check_ord_status:
            search_params['customerordersummary__status__in'] = perm_status_list
    all_orders = OrderDetail.objects.filter(**data_dict).exclude(order_code="CO")
    if search_term:
        mapping_results = all_orders.values('customer_name', 'order_id', 'order_code', 'original_order_id',
                                            'marketplace', 'address', 'order_reference'). \
            distinct().annotate(total=Sum('quantity'), date_only=Cast('creation_date', DateField())).filter(Q(customer_name__icontains=search_term) |
                                                              Q(order_id__icontains=search_term) |
                                                              Q(sku__sku_category__icontains=search_term) | Q(order_reference__icontains=search_term)|
                                                              Q(original_order_id__icontains=search_term),
                                                              **search_params).order_by(order_data)
    else:
        mapping_results = all_orders.values('customer_name', 'order_id', 'order_code', 'original_order_id',
                                            'marketplace', 'address', 'order_reference'). \
            distinct().annotate(total=Sum('quantity'), date_only=Cast('creation_date', DateField())).\
            filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    index = 0
    po_list = list(PurchaseOrder.objects.filter(open_po__sku__user=user.id).values_list('open_po__po_name', flat=True))
    all_seller_orders = SellerOrder.objects.filter(order__user=user.id)
    order_summary_objs = CustomerOrderSummary.objects.filter(order__user=user.id).values('order__order_id', \
                                                                                         'shipment_time_slot', 'status',
                                                                                         'order_taken_by').distinct()

    if stop_index and not custom_search:
        mapping_results = mapping_results[start_index:stop_index]
    for dat in mapping_results:
        cust_status_obj = order_summary_objs.filter(order__order_id=dat['order_id'])
        cust_status = ''
        time_slot = ''
        order_taken_val = ''
        po_status = ''
        if cust_status_obj:
            cust_status = cust_status_obj[0]['status']
            time_slot = cust_status_obj[0]['shipment_time_slot']
            order_taken_val = cust_status_obj[0]['order_taken_by']

        order_id = dat['order_code'] + str(dat['order_id'])
        order_reference = dat['order_reference']
        if dat['original_order_id']:
            order_id = dat['original_order_id']
        check_values = order_id
        # name = all_orders.filter(order_id=dat['order_id'], order_code=dat['order_code'], user=user.id)[0].id
        name = ''
        order_dates = all_orders.filter(order_id=dat['order_id'], order_code=dat['order_code'], user=user.id).order_by(
            '-shipment_date')
        creation_date = order_dates[0].creation_date
        creation_data = get_local_date(request.user, creation_date, True).strftime("%d %b, %Y")
        shipment_date = order_dates[0].shipment_date
        shipment_data = get_local_date(request.user, shipment_date, True).strftime("%d %b, %Y")
        if time_slot:
            if "-" in time_slot:
                time_slot = time_slot.split("-")[0]

            shipment_data = shipment_data + ', ' + time_slot
        # if time_slot:
        #    shipment_data = shipment_data + ', ' + time_slot

        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (name, dat['total'])
        tot_quantity = dat['total']
        seller_order = all_seller_orders.filter(order__order_id=dat['order_id'], order__order_code=dat['order_code'],
                                                order__user=user.id, status=1).aggregate(Sum('quantity'))[
            'quantity__sum']
        if seller_order:
            tot_quantity = seller_order
        if order_id in po_list:
            po_status = 'PO Raised'

        temp_data['aaData'].append(OrderedDict((('', checkbox), ('Customer Name', dat['customer_name']),
                                                ('Order ID', order_id), ('Market Place', dat['marketplace']),
                                                ('Total Quantity', tot_quantity), ('Address', dat['address']),
                                                ('Creation Date', creation_data),
                                                ('Shipment Date', shipment_data), ('Order Taken By', order_taken_val),
                                                ('Status', cust_status), ('Order Reference', order_reference), ('id', index), ('DT_RowClass', 'results'),
                                                ('data_value', check_values),('PO Status', po_status))))
        index += 1

    if stop_index and custom_search:
        if temp_data['aaData']:
            temp_data['aaData'] = apply_search_sort(temp_data['aaData'][0].keys(), temp_data['aaData'], order_term, '',
                                                    col_num, exact=False)
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data


@csrf_exempt
def get_custom_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                          filters={}, user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    # user_dict = eval(user_dict)
    lis = ['id', 'customer_name', 'order_id', 'total', 'shipment_date', 'creation_date', 'production_unit',
           'printing_vendor', 'embroidery_unit', 'order_taken_by', 'status']
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0, 'order_code': "CO"}

    order_taken_val_user = CustomerOrderSummary.objects.filter(order__user=user.id)

    all_orders = OrderDetail.objects.filter(**data_dict)
    mapping_results = all_orders.values('customer_name', 'order_id', 'order_code', 'original_order_id',
                                        'shipment_date'). \
        distinct().annotate(total=Sum('quantity'))

    index = 0
    vendor_list = ['printing_vendor', 'embroidery_vendor', 'production_unit']
    for dat in mapping_results:
        vend_dict = {'printing_vendor': "", 'embroidery_vendor': "", 'production_unit': ""}
        cust_status, time_slot, order_taken_val = "", "", ""
        if order_taken_val_user:
            cust_status_obj = order_taken_val_user.filter(order__order_id=dat['order_id'])
            if cust_status_obj:
                cust_status = cust_status_obj[0].status
                time_slot = cust_status_obj[0].shipment_time_slot
                order_taken_val = cust_status_obj[0].order_taken_by

        for item in vendor_list:
            var = ""
            map_obj = OrderMapping.objects.filter(order__order_id=dat['order_id'], order__user=user.id,
                                                  mapping_type=item)
            if map_obj:
                var_id = map_obj[0].mapping_id
                vend_obj = VendorMaster.objects.filter(id=var_id)
                if vend_obj:
                    var = vend_obj[0].name
                    vend_dict[item] = var

        order_id = dat['order_code'] + str(dat['order_id'])
        check_values = order_id
        name = all_orders.filter(order_id=dat['order_id'], order_code=dat['order_code'], user=user.id)[0].id
        creation_date = all_orders.filter(order_id=dat['order_id'], order_code=dat['order_code'], user=user.id)[
            0].creation_date
        creation_data = get_local_date(request.user, creation_date, True).strftime("%d %b, %Y")

        shipment_data = get_local_date(request.user, dat['shipment_date'], True).strftime("%d %b, %Y")
        if time_slot:
            if "-" in time_slot:
                time_slot = time_slot.split("-")[0]

            shipment_data = shipment_data + ', ' + time_slot

        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (name, dat['total'])

        temp_data['aaData'].append(
            OrderedDict((('', checkbox), ('data_value', check_values), ('Customer Name', dat['customer_name']),
                         ('Order ID', order_id), ('Production Unit', vend_dict['production_unit']),
                         ('Printing Unit', vend_dict['printing_vendor']),
                         ('Embroidery Unit', vend_dict['embroidery_vendor']),
                         ('Total Quantity', dat['total']), ('Order Taken By', order_taken_val),
                         ('Creation Date', creation_data), ('Shipment Date', shipment_data),
                         ('id', index), ('DT_RowClass', 'results'), ('Status', cust_status))))
        index += 1

    col_val = ['id', 'Customer Name', 'Order ID', 'Total Quantity', 'Shipment Date', 'Creation Date', 'Production Unit',
               'Printing Unit', 'Embroidery Unit', 'Order Taken By', 'Status']

    temp_data['aaData'] = apply_search_sort(col_val, temp_data['aaData'], order_term, search_term, col_num)
    temp_data['recordsTotal'] = len(temp_data['aaData'])
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


def get_ratings_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                         filters):
    ''' Order Rating datatable code '''
    user_profile = UserProfile.objects.get(user_id=user.id)
    admin_user = get_priceband_admin_user(user)
    lis = ['rating__original_order_id', 'rating__original_order_id', 'rating__original_order_id',\
           'rating__rating_order', 'rating__reason_product', 'rating__rating_order',\
           'rating__reason_order', 'rating__updation_date']#for filter purpose
    user_filter = {'rating__user': user.id}
    result_values = ['rating__original_order_id', 'rating__rating_product',\
                     'rating__reason_product', 'rating__rating_order',\
                     'rating__reason_order', 'rating__updation_date']#to make distinct grouping

    if search_term:
        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(lis, search_term)
        master_data = RatingSKUMapping.objects.filter(search_query, **user_filter)\
                                              .values(*result_values).distinct()

    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            order_by = '%s' % lis[col_num]
        else:
            order_by = '-%s' % lis[col_num]
        master_data = RatingSKUMapping.objects.filter(**user_filter)\
                                      .values(*result_values).distinct()\
                                      .order_by('-%s' % lis[col_num])
    else:
        master_data = RatingSKUMapping.objects.filter(**user_filter)\
                                      .values(*result_values).distinct()
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    for data in master_data[start_index:stop_index]:
        customer_name, tot_inv_amt = '', 0
        original_order_id = data['rating__original_order_id']
        order_filter = {'original_order_id': original_order_id,
                        'user': user.id}
        order_detail = OrderDetail.objects.filter(**order_filter)\
                                  .values('customer_name', 'original_order_id')\
                                  .distinct().annotate(tot_inv_amt=Sum('invoice_amount'))
        if order_detail:
            customer_name = order_detail[0]['customer_name']
            tot_inv_amt = order_detail[0]['tot_inv_amt']
        data_dict = OrderedDict((('order_id', original_order_id),
                                ('customer_name', customer_name),
                                ('invoice_value', "%.2f" % tot_inv_amt),
                                ('rating_order', data['rating__rating_order']),
                                ('reason_order', data['rating__reason_order']),
                                ('rating_product', data['rating__rating_product']),
                                ('reason_product', data['rating__reason_product']),
                                ('updation_date', get_local_date(user, data['rating__updation_date'])),
                               ))
        temp_data['aaData'].append(data_dict)


@csrf_exempt
@login_required
@get_admin_user
def get_ratings_details(request, user=''):
    result_data, order_date = [], ''
    order_id = request.POST.get('order_id', '')
    order_filter = {'user': user.id, 'original_order_id': order_id}
    rating_master = RatingsMaster.objects.filter(**order_filter)
    order_detail = OrderDetail.objects.filter(**order_filter)
    if order_detail:
        order_detail = order_detail[0]
        order_date = get_local_date(user, order_detail.creation_date, True).strftime("%d/%m/%Y")

    if rating_master:
        rating_id = rating_master[0].id
        master_data = RatingSKUMapping.objects.filter(rating_id=rating_id)\
                                      .values('sku__sku_code', 'sku__sku_desc', 'remarks')
        for data in master_data:
            result_data.append({
                                'wms_code': data['sku__sku_code'],
                                'sku_desc': data['sku__sku_desc'],
                                'remarks': data['remarks']
                              })
        result_dict = {'sku_data': result_data,
                       'order_id': order_id,
                       'order_date': order_date
                      }
    return HttpResponse(json.dumps({'data': result_dict}))


@csrf_exempt
def get_central_orders_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                          filters={}, user_dict={}):
    un_sort_dict = {7: 'Status'}
    lis = ['interm_order_id', 'interm_order_id', 'sku__sku_code', 'sku__sku_desc', 'quantity', 'shipment_date', 'project_name', 'remarks',
           'order_assigned_wh__username', 'status', 'id','creation_date', 'sku__sku_code']
    data_dict = {'user': user.id, 'quantity__gt': 0}
    status_map = {'1': 'Accept', '0': 'Reject','2': 'Pending'}
    if not col_num: col_num = 0
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    interm_orders = IntermediateOrders.objects.filter(**data_dict).exclude(status = 3)
    interm_orders = IntermediateOrders.objects.filter(**data_dict).exclude(status=3)
    if search_term:
        all_orders = interm_orders.filter(Q(sku__sku_code__icontains=search_term) | Q(sku__sku_desc__icontains=search_term)|
                                            Q(quantity__icontains=search_term) | Q(shipment_date__regex=search_term)|
                                            Q(project_name__icontains=search_term) | Q(order_assigned_wh__username__icontains=search_term)|
                                            Q(interm_order_id__icontains=search_term)|Q(creation_date__regex=search_term) |
                                            Q(order__original_order_id__icontains=search_term)).order_by(order_data)
    else:
        all_orders = interm_orders.order_by(order_data)
    index = 0
    custom_sort = False
    if col_num in un_sort_dict.keys():
        custom_sort = True
        if stop_index:
            all_orders = all_orders[start_index:stop_index]
    ord_items = all_orders.only('interm_order_id', 'order__original_order_id', 'order_assigned_wh__username',
                                   'status', 'sku__sku_code', 'sku__sku_desc', 'quantity', 'shipment_date', 'id',
                                   'creation_date', 'project_name', 'remarks', 'alt_sku__sku_code')\
        .values('interm_order_id', 'order__original_order_id', 'order_assigned_wh__username', 'status',
                     'sku__sku_code', 'sku__sku_desc', 'quantity', 'shipment_date', 'id',
                     'creation_date', 'project_name', 'remarks', 'alt_sku__sku_code')
    temp_data['recordsTotal'] = ord_items.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for dat in ord_items[start_index:stop_index]:
        alternate_sku = ''
        order_date = get_local_date(user, dat['creation_date'])
        shipment_date = dat['shipment_date'].strftime("%d/%m/%Y")
        status = dat['status']
        if status:
            status = status_map.get(status)
        else:
            status = 'Pending'
        if user.username == 'one_assist':
            alternate_sku = dat['sku__sku_code']
            if dat['alt_sku__sku_code']:
                alternate_sku = dat['alt_sku__sku_code']
            ord_val = OrderFields.objects.filter(order_type='intermediate_order', name='original_order_id',
                                                 original_order_id=dat['interm_order_id'])
            if ord_val:
                loan_proposal_id = ord_val[0].value
            else:
                loan_proposal_id = 'NO SR NUMBER'
        else:
            loan_proposal_id = dat['order__original_order_id']
        temp_data['aaData'].append(
            OrderedDict((('Order ID', int(dat['interm_order_id'])), ('SKU Code', dat['sku__sku_code']), ('SKU Desc', dat['sku__sku_desc']),
                         ('Product Quantity', dat['quantity']), ('Shipment Date', shipment_date), ('data_id', dat['id']),
                         ('Project Name', dat['project_name']), ('Remarks', dat['remarks']),
                         ('Warehouse', dat['order_assigned_wh__username']), ('Status', status), ('Order Date',order_date),
                         ('Loan Proposal ID', loan_proposal_id), ('Alternative Sku', alternate_sku), ('id', index), ('DT_RowClass', 'results'))))
        index += 1

    col_headers = ['Order ID', 'SKU Code', 'SKU Desc', 'Product Quantity', 'Shipment Date', 'Project Name', 'Remarks',
                   'Warehouse', 'Status','Order Date']

    if custom_sort:
        temp_data['aaData'] = apply_search_sort(col_headers, temp_data['aaData'], order_term, search_term, col_num)[start_index:stop_index]


@csrf_exempt
@login_required
@get_admin_user
def get_central_order_detail(request, user=''):
    central_order_id = request.GET.get('central_order_id', '')
    interm_obj = IntermediateOrders.objects.filter(id=central_order_id, user=user.id)
    interm_obj = interm_obj[0]
    order_id = interm_obj.order_id
    already_assigned = False
    if interm_obj.order_assigned_wh:
        wh_name = interm_obj.order_assigned_wh.username
    else:
        wh_name = ''
    already_picked = False
    if order_id or wh_name:
        #already_assigned = True
        picked_qs = Picklist.objects.filter(order_id=order_id)
        if picked_qs:
            picked_qty = picked_qs[0].picked_quantity
            if picked_qty:
                already_picked = True

    shipment_date = interm_obj.shipment_date.strftime("%m/%d/%Y")
    warehouses = UserGroups.objects.filter(admin_user_id=interm_obj.user)
    warehouse_names = warehouses.values_list('user__username', flat=True)
    wh_level_stock_map = {}
    sku_code = interm_obj.sku.sku_code
    if request.GET.get('alt_sku_code', ''):
        sku_code= request.GET['alt_sku_code']
    warehouses.values_list('user_id', flat=True)
    wh_users = warehouses.values_list('user_id', flat=True)
    stock_obj_dict = dict(StockDetail.objects.filter(sku__sku_code=sku_code, sku__user__in=wh_users,
                                           quantity__gt=0).exclude(location__zone__zone='DAMAGED_ZONE').values_list('sku__user').distinct().annotate(in_stock=Sum('quantity')))
    reserved_obj_dict = dict(PicklistLocation.objects.filter(stock__sku__sku_code=sku_code,stock__sku__user__in=wh_users, status=1).\
                                            values_list('stock__sku__user').distinct().annotate(in_reserved=Sum('reserved')))
    raw_reserved_dict = dict(RMLocation.objects.filter(status=1, stock__sku__user__in=wh_users, stock__sku__sku_code=sku_code). \
                                            values_list('material_picklist__jo_material__material_code__user').distinct(). \
                                            annotate(rm_reserved=Sum('reserved')))
    for wh in warehouses:
        #stock_obj = StockDetail.objects.filter(sku__sku_code=sku_code, sku__user=wh.user.id,
        #                                       quantity__gt=0).values('sku_id').distinct().annotate(
        #    in_stock=Sum('quantity'))
        stock_qty = stock_obj_dict.get(wh.user.id, 0)
        #if stock_obj:
        #    stock_qty = stock_obj[0]['in_stock']
        #else:
        #    stock_qty = 0
        #reserved_obj = PicklistLocation.objects.filter(stock__sku__sku_code=sku_code,
        #                                               stock__sku__user=wh.user.id, status=1).values(
        #    'stock__sku_id').distinct().annotate(in_reserved=Sum('reserved'))
        #if reserved_obj:
        #    reserved_qty = reserved_obj[0]['in_reserved']
        #else:
        #    reserved_qty = 0
        reserved_qty = reserved_obj_dict.get(wh.user.id, 0)
        reserved_qty = reserved_qty + raw_reserved_dict.get(wh.user.id, 0)
        avail_stock = stock_qty - reserved_qty
        wh_uname = wh.user.username
        wh_level_stock_map[wh_uname] = {'quantity': 0, 'available': 0}
        if wh_uname not in wh_level_stock_map:
            wh_level_stock_map[wh_uname]['available'] = avail_stock
        else:
            wh_level_stock_map[wh_uname]['available'] += avail_stock
    alt_sku_code = interm_obj.sku.sku_code
    alt_sku_desc = interm_obj.sku.sku_desc
    if interm_obj.alt_sku:
        alt_sku_code = interm_obj.alt_sku.sku_code
        alt_sku_desc = interm_obj.alt_sku.sku_desc
    resp = {'warehouses': list(warehouse_names), 'interm_order_id': interm_obj.interm_order_id,
            'sku_code': interm_obj.sku.sku_code, 'sku_desc': interm_obj.sku.sku_desc,
            'alt_sku_code': alt_sku_code, 'alt_sku_desc': alt_sku_desc,
            'quantity': int(interm_obj.quantity), 'status': interm_obj.status,
            'warehouse': wh_name, 'data_id': interm_obj.id, 'shipment_date': shipment_date,
            'wh_level_stock_map': wh_level_stock_map, 'already_assigned': already_assigned,
            'already_picked': already_picked, 'project_name': interm_obj.project_name}
    return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def order_category_generate_picklist(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("generate_picklist: %s" % str(get_user_ip(request)))
    filters = request.POST.get('filters', '')
    enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
    order_filter = OrderedDict((('status', 1), ('user', user.id), ('quantity__gt', 0)))
    seller_order_filter = {'order__status': 1, 'order__user': user.id, 'order__quantity__gt': 0}
    if filters:
        filters = eval(filters)
        if filters['market_places']:
            order_filter['marketplace__in'] = (filters['market_places']).split(',')
            seller_order_filter['order__marketplace__in'] = order_filter['marketplace__in']
        if filters.get('customer_id', ''):
            customer_id = ''.join(re.findall('\d+', filters['customer_id']))
            order_filter['customer_id'] = customer_id
            seller_order_filter['order__customer_id'] = customer_id

    qc_items_qs = UserAttributes.objects.filter(user_id=user.id, attribute_model='dispatch_qc', status=1).values_list('attribute_name', flat=True)
    qc_items = list(qc_items_qs)

    data = []
    order_data = []
    stock_status = ''
    out_of_stock = []
    picklist_number = get_picklist_number(user)
    picklist_exclude_zones = get_exclude_zones(user)
    switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                   'fifo_switch': get_misc_value('fifo_switch', user.id),
                   'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                   'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id),
                   'allow_partial_picklist': get_misc_value('allow_partial_picklist', user.id)}
    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    if enable_damaged_stock  == 'true':
        sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0, location__zone__zone__in=['DAMAGED_ZONE'])
    else:
        sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
        location__zone__zone__in=picklist_exclude_zones).filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(**order_filter)
    all_seller_orders = SellerOrder.objects.prefetch_related('order__sku').filter(**seller_order_filter)
    if switch_vals['fifo_switch'] == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
            'receipt_date')
        #data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
            'location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    all_sku_stocks = stock_detail1 | stock_detail2
    seller_stocks = SellerStock.objects.filter(seller__user=user.id, stock__quantity__gt=0).values('stock_id', 'seller_id')
    for key, value in request.POST.iteritems():
        if key in PICKLIST_SKIP_LIST or key in ['filters', 'enable_damaged_stock']:
            continue
        order_filter = {'quantity__gt': 0, 'status': 1}
        if '<>' in key:
            key = key.split('<>')
            order_id, sku_category = key
            order_filter['sku__sku_category'] = sku_category
        else:
            order_id = key
        order_code = ''.join(re.findall('\D+', order_id))
        order_id = ''.join(re.findall('\d+', order_id))
        order_filter['order_id'] = order_id
        order_filter['order_code'] = order_code
        order_detail = all_orders.filter(**order_filter).order_by('sku__sequence','shipment_date')
        seller_orders = all_seller_orders.filter(order_id__in=order_detail.values_list('id', flat=True), status=1). \
            order_by('order__shipment_date')
        try:
            if seller_orders:
                for seller_order in seller_orders:
                    sku_stocks = all_sku_stocks
                    seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(seller_order.seller_id),
                                               seller_stocks)
                    if seller_stock_dict:
                        sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
                        sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
                    else:
                        sku_stocks = sku_stocks.filter(id=0)
                    stock_status, picklist_number = picklist_generation([seller_order], enable_damaged_stock,
                                                                        picklist_number, user, sku_combos, sku_stocks,
                                                                        switch_vals, status='open',
                                                                        remarks='', is_seller_order=True)
                    if stock_status:
                        out_of_stock = out_of_stock + stock_status
            else:
                stock_status, picklist_number = picklist_generation(order_detail, enable_damaged_stock,
                                                                    picklist_number, user,
                                                                    sku_combos, sku_stocks, switch_vals, \
                                                                    status='open', remarks='')
                if stock_status:
                    out_of_stock = out_of_stock + stock_status
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Generate Picklist order view failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))
    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''
    order_status = ''
    check_picklist_number_created(user, picklist_number + 1)
    data, sku_total_quantities, courier_name = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']
        if order_status == 'open':
            order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
            order_count_len = len(filter(lambda x: len(str(x)) > 0, order_count))
            if order_count_len == 1:
                single_order = str(order_count[0])
    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status,
                                    'order_status': order_status, 'user': request.user.id,
                                    'sku_total_quantities': sku_total_quantities, 'qc_items': qc_items}))


@csrf_exempt
@login_required
@get_admin_user
def delete_order_data(request, user=""):
    """ This code is used to delete the orders when that coloumn in deleted from view order """
    order_delete(request, user="")
    return HttpResponse("Order Deleted")


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def update_order_data(request, user=""):
    """ This code will update data if order is updated """
    reversion.set_user(request.user)
    reversion.set_comment("update_order: %s" % str(get_user_ip(request)))
    st_time = datetime.datetime.now()
    log.info("updation of order process started")
    myDict = dict(request.POST.iterlists())
    log.info('Order update request params for ' + user.username + ' is ' + str(request.GET.dict()))
    try:
        complete_id = myDict['order_id'][0]
        order_id = ''.join(re.findall('\d+', complete_id))
        order_code = ''.join(re.findall('\D+', complete_id))
        older_objs = OrderDetail.objects.filter(
            Q(order_id=order_id, order_code=order_code) | Q(original_order_id=complete_id),
            user=user.id)
        old_cust_obj = ""
        order_creation_date = datetime.datetime.now()
        tax_type = 2
        tax_name = request.POST.get('tax_type', '')
        client_name = request.POST.get('client_name', '')
        courier_name = request.POST.get('courier_name', '')
        if tax_name == 'intra_state':
            tax_type = 0
        elif tax_name == 'inter_state':
            tax_type = 1
        if older_objs:
            older_order = older_objs[0]
            order_creation_date = older_order.creation_date
        else:
            return HttpResponse("Order Creation Failed")
        for i in range(0, len(myDict['item_code'])):
            s_date = datetime.datetime.strptime(myDict['shipment_date'][0], '%d %b, %Y %H:%M %p')
            if not myDict['item_code'][i] or not myDict['quantity'][i]:
                continue
            quantity = float(myDict['quantity'][i])
            sku_id = SKUMaster.objects.get(sku_code=myDict['item_code'][i], user=user.id)
            if not myDict['invoice_amount'][i]:
                myDict['invoice_amount'][i] = 0
            default_dict = {'title': myDict['product_title'][i], 'quantity': quantity,
                            'invoice_amount': myDict['invoice_amount'][i],
                            'user': user.id, 'customer_id': older_order.customer_id,
                            'customer_name': older_order.customer_name,
                            'telephone': older_order.telephone, 'email_id': older_order.email_id,
                            'address': older_order.address,
                            'shipment_date': older_order.shipment_date, "marketplace": older_order.marketplace,
                            'remarks': myDict['remarks'][i], 'original_order_id': older_order.original_order_id,
                            'unit_price': myDict['unit_price'][i]}
            sku_order = older_objs.filter(order_id=order_id, order_code=order_code, sku=sku_id)
            if not sku_order:
                default_dict['status'] = 1
            if older_order:
                to_save_courier_name = CustomerOrderSummary.objects.filter(order=older_order.id)
                if to_save_courier_name:
                    to_save_courier_name = to_save_courier_name[0]
                    to_save_courier_name.courier_name = courier_name
                    to_save_courier_name.save()
            elif int(sku_order[0].status) == 0:
                continue
            order_obj = OrderDetail.objects.filter(order_id=order_id, order_code=order_code, sku=sku_id)
            created = False
            if not order_obj:
                default_dict['order_id'] = order_id
                default_dict['order_code'] = order_code
                default_dict['sku_id'] = sku_id.id
                order_obj = OrderDetail.objects.create(**default_dict)
                created = True
            else:
                remainging_quantity =  quantity - order_obj[0].quantity
                default_dict['original_quantity'] = order_obj[0].original_quantity + remainging_quantity
                default_dict['invoice_amount'] = (float(myDict['invoice_amount'][i]) / quantity) * \
                                                    default_dict['original_quantity']
                #order_obj.update(**default_dict)
                update_multiple_records(order_obj, default_dict)
                order_obj = order_obj[0]
            # order_obj, created = OrderDetail.objects.update_or_create(
            #     order_id=order_id, order_code=order_code, sku=sku_id, defaults=default_dict
            # )
            if not created and order_obj.sellerorder_set.filter().exists():
                seller_order = order_obj.sellerorder_set.filter()[0]
                seller_order.quantity = order_obj.quantity
                seller_order.save()
            sgst_tax = myDict['sgst'][i]
            cgst_tax = myDict['cgst'][i]
            igst_tax = myDict['igst'][i]
            discount = myDict['discount'][i]
            if not sgst_tax:
                sgst_tax = 0
            if not cgst_tax:
                cgst_tax = 0
            if not igst_tax:
                igst_tax = 0
            if not discount:
                discount = 0

            old_cust_obj = CustomerOrderSummary.objects.filter(order=order_obj.id)
            if created:
                order_obj.creation_date = order_creation_date
                order_obj.save()
                if old_cust_obj:
                    CustomerOrderSummary.objects.create(order=order_obj, discount=discount, vat=old_cust_obj[0].vat,
                                                        tax_value=old_cust_obj[0].tax_value,
                                                        order_taken_by=old_cust_obj[0].order_taken_by,
                                                        mrp=old_cust_obj[0].mrp, tax_type=old_cust_obj[0].tax_type,
                                                        status=old_cust_obj[0].status,
                                                        central_remarks=old_cust_obj[0].central_remarks,
                                                        sgst_tax=sgst_tax, cgst_tax=cgst_tax, igst_tax=igst_tax,
                                                        invoice_type=myDict['invoice_type'][0])
                else:
                    CustomerOrderSummary.objects.create(order=order_obj, status=myDict['status_type'][0],
                                                        central_remarks=myDict['central_remarks'][0], sgst_tax=sgst_tax,
                                                        cgst_tax=cgst_tax, igst_tax=igst_tax, discount=discount,
                                                        tax_type=tax_type, invoice_type=myDict['invoice_type'][0])
            else:
                status_obj = old_cust_obj
                if not status_obj:
                    status_obj = CustomerOrderSummary.objects.create(order=order_obj, status=myDict['status_type'][0])
                else:
                    status_obj = status_obj[0]
                status_obj.status = myDict['status_type'][0]
                status_obj.central_remarks = myDict['central_remarks'][0]
                status_obj.sgst_tax = sgst_tax
                status_obj.cgst_tax = cgst_tax
                status_obj.igst_tax = igst_tax
                status_obj.discount = discount
                status_obj.tax_type = tax_type
                status_obj.invoice_type = myDict['invoice_type'][0]
                status_obj.client_name = client_name
                status_obj.courier_name = courier_name
                status_obj.payment_status = myDict['payment_status'][0]
                status_obj.save()

                vendor_list = ['printing_vendor', 'embroidery_vendor', 'production_unit']
                for item in vendor_list:
                    if myDict.has_key(item):
                        if not myDict[item][0]:
                            OrderMapping.objects.filter(order__id=order_obj.id, order__user=user.id,
                                                        mapping_type=item).delete()
                        else:
                            ord_map_obj = OrderMapping.objects.filter(order__id=order_obj.id, order__user=user.id,
                                                                      mapping_type=item)
                            vend_obj = VendorMaster.objects.filter(vendor_id=myDict[item][0], user=user.id)
                            if vend_obj:
                                vendor_id = vend_obj[0].id
                                if ord_map_obj:
                                    ord_map_obj = ord_map_obj[0]
                                    ord_map_obj.mapping_id = vendor_id
                                    ord_map_obj.save()
                                else:
                                    OrderMapping.objects.create(mapping_id=vendor_id, mapping_type=item,
                                                                order_id=order_obj.id)

        end_time = datetime.datetime.now()
        duration = end_time - st_time
        log.info("process completed")
        log.info("total time -- %s" % (duration))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Order failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
        return HttpResponse("Update Order Failed")
    return HttpResponse("Success")


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def picklist_delete(request, user=""):
    """ This code will delete the picklist selected"""
    reversion.set_user(request.user)
    st_time = datetime.datetime.now()
    warehouse_id = request.GET['warehouse_id']
    user = User.objects.get(id=warehouse_id)
    log.info("deletion of picklist process started")
    stock_transfer_order = False
    order_ids =[]
    picklist_id = request.GET.get("picklist_id", "")
    key = request.GET.get("key", "")
    picklist_objs = Picklist.objects.filter(picklist_number=picklist_id, status__in=["open", "batch_open"],
                                            order_id__user=user.id)
    if not picklist_objs.exists():
        picklist_objs = Picklist.objects.filter(picklist_number=picklist_id, status__in=["open", "batch_open"],
                                                stock__sku__user=user.id)
        if picklist_objs.exists():
            stock_transfer_order = True

    if not stock_transfer_order :
        order_ids = list(picklist_objs.values_list('order_id', flat=True).distinct())
        order_objs = OrderDetail.objects.filter(id__in=order_ids, user=user.id)
    log.info('Cancel Picklist request params for ' + user.username + ' is ' + str(request.GET.dict()))
    cancelled_orders_dict = {}
    try:
        if key == "process":
            status_message = 'Picklist is saved for later use'
            if not stock_transfer_order :
                for order in order_objs:
                    combo_picklists = picklist_objs.filter(order_type='combo', order_id=order.id)
                    if combo_picklists:
                        #is_picked = combo_picklists.filter(picked_quantity__gt=0, order_id=order.id)
                        #remaining_qty = order.quantity
                        #if is_picked:
                        remaining_qty = get_remaining_combo_reserved(combo_picklists)
                        '''remaining_qty_objs = combo_picklists.values('stock__sku_id').\
                                                    annotate(res_qty=Sum('reserved_quantity'))
                        if remaining_qty_objs:
                            remaining_qty_objs = remaining_qty_objs[0]
                            combo_qty = SKURelation.objects.\
                                        filter(member_sku_id=remaining_qty_objs['stock__sku_id'])[0].quantity
                            remaining_qty = float(remaining_qty_objs['res_qty'])/combo_qty'''
                    else:
                        remaining_qty = picklist_objs.filter(order_id=order).\
                            aggregate(Sum('reserved_quantity'))['reserved_quantity__sum']

                    if remaining_qty and remaining_qty > 0:
                        order.status = 1
                        if order.original_quantity == order.quantity:
                            order.quantity = remaining_qty
                        else:
                            order.quantity = order.quantity + remaining_qty
                        order.save()
                        seller_orders = SellerOrder.objects.filter(order__user=user.id, order_id=order.id)
                        if seller_orders:
                            seller_orders.update(status=1)
            else:
                updated_st_ids = []
                for picklist in  picklist_objs :
                    st_orders = STOrder.objects.filter(picklist = picklist.id)
                    for st_order in st_orders:
                        stock_transfer_obj = st_order.stock_transfer
                        if stock_transfer_obj.id in updated_st_ids:
                            continue
                        uom_dict = get_uom_with_sku_code(user, picklist.stock.sku.wms_code, uom_type='purchase')
                        pcf = uom_dict['sku_conversion']
                        st_picklist_objs = Picklist.objects.filter(picklist_number=picklist.picklist_number,\
                                                                   stock__sku__user =user.id,\
                                                                   stock__sku__wms_code = picklist.stock.sku.wms_code,
                                                                   storder__id=st_order.id).\
                                                                   aggregate(Sum('picked_quantity'),Sum('reserved_quantity'))
                        st_picked_quantity = st_picklist_objs['picked_quantity__sum']
                        st_reserved_quantity = st_picklist_objs['reserved_quantity__sum']
                        stock_transfer_obj.picked_quantity = stock_transfer_obj.picked_quantity + float(st_picked_quantity/pcf)
                        if stock_transfer_obj.quantity == stock_transfer_obj.original_quantity:
                            stock_transfer_obj.quantity = stock_transfer_obj.quantity - float(st_picked_quantity/pcf)
                        else:
                            stock_transfer_obj.quantity = float(stock_transfer_obj.original_quantity - stock_transfer_obj.picked_quantity - stock_transfer_obj.cancelled_quantity)
                        stock_transfer_obj.status = 1
                        stock_transfer_obj.save()
                        updated_st_ids.append(stock_transfer_obj.id)

            if order_ids or stock_transfer_order :
                if not stock_transfer_order :
                    OrderLabels.objects.filter(order_id__in=order_ids, picklist__picklist_number=picklist_id).update(
                        picklist=None)
                picked_objs = picklist_objs.filter(picked_quantity__gt=0)
                not_picked_objs = picklist_objs.filter(picked_quantity=0)
                if not_picked_objs.exists():
                    not_picked_objs.delete()
                if picked_objs.exists():
                    pick_obj_status = picked_objs[0].status
                    if 'batch' in pick_obj_status:
                        pick_obj_status = 'batch_picked'
                    else:
                        pick_obj_status = 'picked'
                    picklist_locations = PicklistLocation.objects.filter(picklist_id__in=picked_objs.\
                                                                         values_list('id', flat=True))
                    for pick_location in picklist_locations:
                        pick_location.quantity = float(pick_location.quantity) - float(pick_location.reserved)
                        pick_location.reserved = 0
                        pick_location.status = 0
                        pick_location.save()
                    picked_objs.update(reserved_quantity=0, status=pick_obj_status)
                check_picklist_number_created(user, picklist_id)
                end_time = datetime.datetime.now()
                duration = end_time - st_time
                log.info("process completed")
                log.info("total time -- %s" % (duration))
            return HttpResponse(status_message)

        elif key == "delete":
            status_message = 'Picklist is deleted'
            if not stock_transfer_order :
                for order in order_objs:
                    '''if picklist_objs.filter(order_type='combo', order_id=order.id):
                        is_picked = picklist_objs.filter(picked_quantity__gt=0, order_id=order.id)
                        #remaining_qty = order.quantity
                        if is_picked:
                            status_message = 'Partial Picked Picklist not allowed to cancel'
                            continue
                        else:
                            order.delete()
                    else:'''
                    all_seller_orders = SellerOrder.objects.filter(order__user=user.id,
                                                                   order_id__in=order_objs.values_list('id', flat=True))
                    picklist_qty_objs = picklist_objs.filter(order_id=order.id).aggregate(Sum('picked_quantity'), Sum('reserved_quantity'))
                    picked_qty = picklist_qty_objs['picked_quantity__sum']
                    reserved_qty = picklist_qty_objs['reserved_quantity__sum']
                    if picklist_objs.filter(order_type='combo', order_id=order.id):
                        combo_picklists = picklist_objs.filter(order_type='combo', order_id=order.id)
                        reserved_qty = get_remaining_combo_reserved(combo_picklists)

                    pick_order = picklist_objs.filter(order_id=order)
                    pick_status = 'picked'
                    if pick_order.filter(status__icontains='batch'):
                        pick_status = 'batch_picked'
                    seller_order = all_seller_orders.filter(order_id=order.id, order__user=user.id)
                    if seller_order:
                        cancelled_orders_dict.setdefault(seller_order[0].id, {})
                        cancelled_orders_dict[seller_order[0].id].setdefault('quantity', 0)
                        cancelled_orders_dict[seller_order[0].id]['quantity'] = float(
                            cancelled_orders_dict[seller_order[0].id]['quantity']) + \
                                                                                float(picked_qty)

                    order.cancelled_quantity = order.cancelled_quantity + reserved_qty
                    shipping_quantity = order.shipmentinfo_set.filter().aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
                    if not shipping_quantity:
                        shipping_quantity = 0
                    if order.original_quantity == order.cancelled_quantity:
                        order.status = 3
                    elif order.original_quantity == (order.cancelled_quantity + shipping_quantity):
                        order.status = 2
                    order.save()
                    if picked_qty <= 0 and not seller_order:
                        order.save()
                        order.picklist_set.filter(status__icontains='open').delete()
                        continue
                    save_order_tracking_data(order, quantity=picked_qty, status='cancelled', imei='')
                    #temp_order_quantity = float(order.original_quantity) - float(picked_qty)
                    #if temp_order_quantity > 0:
                    #    order.quantity = temp_order_quantity
                    #order.status = 3
                    # shipped = ShipmentInfo.objects.filter(order_id=order.id).aggregate(Sum('shipping_quantity'))[
                    #     'shipping_quantity__sum']
                    # proc_pick_obj = Picklist.objects.filter(order_id=order.id, status='dispatched', order__user=user.id)
                    # proc_pick_qty = 0
                    # if proc_pick_obj and proc_pick_obj[0].order:
                    #     proc_pick_qty = float(proc_pick_obj[0].order.quantity)
                    # if shipped:
                    #     shipped = float(shipped) - float(proc_pick_qty)
                    #     if float(shipped) == float(order.original_quantity):
                    #         order.status = 2
                    #         pick_status = 'dispatched'
                    del_seller_order = all_seller_orders.filter(order_id=order.id, order_status='DELIVERY_RESCHEDULED')
                    if del_seller_order and not pick_status == 'dispatched':
                        order.status = 5
                        del_seller_order = del_seller_order[0]
                        del_seller_order.status = 0
                        del_seller_order.order_status = 'PROCESSED'
                        del_seller_order.save()
                    order.save()
                    picklist_locations = PicklistLocation.objects.filter(picklist__order_id=order.id,
                                                                         picklist__picklist_number=picklist_id,
                                                                         picklist__status__in=["open", "batch_open"],
                                                                         picklist__order__user=user.id)
                    for pick_location in picklist_locations:
                        pick_location.quantity = float(pick_location.quantity) - float(pick_location.reserved)
                        pick_location.reserved = 0
                        pick_location.status = 0
                        pick_location.save()
                    pick_order.update(reserved_quantity=0, status=pick_status)
            else:
                for picklist in  picklist_objs :
                    st_orders = STOrder.objects.filter(picklist = picklist.id)
                    stock_transfer_obj = st_orders[0].stock_transfer
                    if picklist.picked_quantity > 0:
                        picklist.reserved_quantity = 0
                        stock_transfer_obj.quantity = Picklist.objects.filter(picklist_number=picklist.picklist_number,\
                                                                   stock__sku__user =user.id,\
                                                                   stock__sku__wms_code = picklist.stock.sku.wms_code).aggregate(Sum('picked_quantity'))['picked_quantity__sum']
                        stock_transfer_obj.save()
                        picklist.save()
                    else:
                        st_po = stock_transfer_obj.st_po
                        po = st_po.po
                        open_st = st_po.open_st
                        open_st.delete()
                        po.delete()
                        picklist.delete()


            check_picklist_number_created(user, picklist_id)
            end_time = datetime.datetime.now()
            duration = end_time - st_time
            log.info("process completed")
            log.info("total time -- %s" % (duration))
            if cancelled_orders_dict:
                check_and_update_order_status_data(cancelled_orders_dict, user, status='CANCELLED')

            return HttpResponse(status_message)

        else:
            log.info("Invalid key")
            return HttpResponse("Something is wrong there, please check")
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Cancel Picklist failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
        return HttpResponse("Something is wrong there, please check")


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def order_delete(request, user=""):
    """ This code will delete the order selected"""
    reversion.set_user(request.user)
    st_time = datetime.datetime.now()
    log.info('Request params for ' + user.username + ' is ' + str(request.POST.dict()))
    log.info("deletion of order process started")
    complete_id = request.GET.get("order_id", "")
    wms_code = ''
    if not complete_id :
        complete_id =  request.GET.get('order_id_code', '')
    wms_code = request.GET.get("item_code", "")

    admin_user = get_admin(user)
    search_params = {}

    order_id = ''.join(re.findall('\d+', complete_id))
    order_code = ''.join(re.findall('\D+', complete_id))

    try:
        if wms_code :
            search_params['sku__wms_code'] = wms_code
        order_detail = OrderDetail.objects.filter(order_id=order_id, order_code=order_code, user=user.id, status=1).filter(**search_params)
        if not order_detail:
            complete_id = request.GET.get("order_id_code", "")
            order_id = ''.join(re.findall('\d+', complete_id))
            order_code = ''.join(re.findall('\D+', complete_id))
            order_detail = OrderDetail.objects.filter(order_id=order_id, order_code=order_code, user=user.id, status=1).filter(**search_params)
        if order_detail:
            order_detail_ids = order_detail.values_list('id', flat=True)
            seller_orders = list(
                SellerOrder.objects.filter(order_id__in=order_detail_ids, order_status='DELIVERY_RESCHEDULED',
                                           status=1). \
                values_list('order_id', flat=True))
            order_detail_ids = list(order_detail_ids)
            IntermediateOrders.objects.filter(order__id__in=order_detail_ids).update(status = 3)
            if seller_orders:
                OrderDetail.objects.filter(id__in=seller_orders).update(status=5)
                SellerOrder.objects.filter(order_id__in=seller_orders).update(status=0, order_status='PROCESSED')
                order_detail_ids = list(set(order_detail_ids) - set(seller_orders))
            if order_detail_ids:
                for order_detail_id in order_detail_ids:
                    # picked_qty_check = Picklist.objects.filter(order_id=order_detail_id).annotate(total_quantity=Sum('picked_quantity'))
                    # if not picked_qty_check.exists():
                    order_obj = OrderDetail.objects.get(id=order_detail_id)
                    order_obj.cancelled_quantity = order_obj.cancelled_quantity + order_obj.quantity
                    if order_obj.original_quantity == order_obj.cancelled_quantity:
                        order_obj.status = 3
                    elif order_obj.shipmentinfo_set.filter().exists() and not order_obj.picklist_set.filter(reserved_quantity__gt=0).exists():
                        order_obj.status = 2
                    else:
                        order_obj.status = 0
                    order_obj.save()
                    if admin_user:
                        OrderFields.objects.filter(user=admin_user.id, original_order_id=complete_id).delete()
                    # else:
                    #     OrderDetail.objects.filter(id=order_detail_id).update(quantity=picked_qty_check[0].total_quantity,status = 3)


    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info(e)

    end_time = datetime.datetime.now()
    duration = end_time - st_time
    log.info("process completed")
    log.info("total time -- %s" % (duration))
    return HttpResponse("Order is deleted")


def get_only_date(request, date):
    """" return only data like 01/01/17 """
    date = get_local_date(request.user, date, True)
    date = date.strftime("%d/%m/%Y")
    return date


def get_level_based_customer_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    lis = ['generic_order_id','quantity','Emiza_order_ids', 'corporate_name', 'Delivered Qty', 'Pending Qty', 'Order Value', 'creation_date', 'orderdetail__status', 'po_number', 'schedule_date', 'remarks']
    search_params = get_filtered_params(filters, lis)
    order_code = get_order_prefix(user.id)
    corporatae_name = ''
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    response_data = {'data': []}
    is_autobackorder = request.GET.get('autobackorder', 'false')
    user_profile = UserProfile.objects.get(user=user.id)
    admin_user = get_priceband_admin_user(user)
    orderprefix_map = {}
    all_wh_dists_obj = UserGroups.objects.filter(admin_user=admin_user)
    if request.user.userprofile.zone:
        all_wh_dists = all_wh_dists_obj.filter(user__userprofile__zone=request.user.userprofile.zone).values_list('user_id', flat=True)
    else:
        all_wh_dists = all_wh_dists_obj.values_list('user_id', flat=True)
    orderprefix_map = dict(all_wh_dists_obj.values_list('user_id', 'user__userprofile__order_prefix'))
    if is_autobackorder == 'true':
        customer = WarehouseCustomerMapping.objects.filter(warehouse=user.id, status=1)
        if customer:
            cm_ids = CustomerUserMapping.objects.filter(customer__user=user.id).values_list('customer_id', flat=True)
            em_qs = EnquiryMaster.objects.filter(customer_id=cm_ids,**search_params)
            if em_qs.exists():
                corporatae_name = em_qs[0].corporate_name
            filter_dict = {'customer_id__in': cm_ids}
    # elif user_profile.warehouse_type == 'WH':
    #     filter_dict = {'cust_wh_id__in': [user.id]}
    #     cus_mapping = CustomerUserMapping.objects.filter(user_id=request.user.id)
    #     if cus_mapping:
    #         customer = WarehouseCustomerMapping.objects.filter(customer_id=cus_mapping[0].customer_id, status=1)
    #         if customer:
    #             filter_dict['cust_wh_id__in'].append(customer[0].warehouse_id)
    #             filter_dict['customer_id'] = customer[0].customer_id
    else:
        cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
        cm_ids = cum_obj.values_list('customer_id', flat=True)
        em_qs = EnquiryMaster.objects.filter(customer_id=cm_ids,**search_params)
        if em_qs.exists():
            corporatae_name = em_qs[0].corporate_name
        filter_dict = {'customer_id__in': cm_ids}
    generic_orders = GenericOrderDetailMapping.objects.filter(**filter_dict)
    if  order_data :
        generic_orders = GenericOrderDetailMapping.objects.filter(**filter_dict).order_by(order_data)

    if search_term:
        if search_term == 'open':
            generic_orders = GenericOrderDetailMapping.objects.filter(Q(orderdetail__status__icontains= '1'), **filter_dict).order_by(order_data)
        elif search_term == 'closed':
            generic_orders = GenericOrderDetailMapping.objects.filter(Q(orderdetail__status__icontains= '0'), **filter_dict).order_by(order_data)
        elif search_term == 'cancel':
            generic_orders = GenericOrderDetailMapping.objects.filter(Q(orderdetail__status__icontains= '3'), **filter_dict).order_by(order_data)
        elif search_term in corporatae_name:
            em_qs = EnquiryMaster.objects.filter(Q(corporate_name__icontains= search_term), **filter_dict).order_by(order_data)
        elif search_term:
            generic_orders = GenericOrderDetailMapping.objects.filter(Q(generic_order_id__icontains=search_term) | Q(orderdetail__sku__sku_code__icontains=search_term) | Q(creation_date__regex=search_term) | Q(po_number__icontains=search_term) | Q(orderdetail__original_order_id__icontains=search_term) | Q(orderdetail__remarks__icontains=search_term) | Q(orderdetail__status__icontains=search_term), **filter_dict).order_by(order_data)

    temp_data['recordsTotal'] = len(generic_orders)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    generic_details_ids = generic_orders.values_list('orderdetail_id', flat=True)
    picklist = Picklist.objects.filter(order_id__in=generic_details_ids)
    response_data['data'] = list(generic_orders.values('generic_order_id', 'customer_id','po_number').
                                 annotate(total_quantity=Sum('quantity'),
                                          date_only=Cast('creation_date', DateField())).order_by(order_data))
    response_data['data'] = response_data['data'][start_index:stop_index]
    for record in response_data['data']:
        order_details = generic_orders.filter(generic_order_id=record['generic_order_id'],
                                              customer_id=record['customer_id'])
        order_detail_ids = order_details.values_list('orderdetail_id', flat=True)
        data = OrderDetail.objects.filter(id__in=order_detail_ids)
        if order_data == 'Receive Status':
            data = OrderDetail.objects.filter(id__in=order_detail_ids).order_by("-status")
        ord_det_qs = data.values('order_id', 'id', 'user', 'original_order_id', 'order_code')
        if ord_det_qs:
            order_detail_order_id = ord_det_qs[0]['original_order_id']
            if not order_detail_order_id:
                order_detail_order_id = str(ord_det_qs[0]['order_code']) + str(ord_det_qs[0]['order_id'])
            other_charges = order_charges_obj_for_orderid(order_detail_order_id, request.user.id)
            if not other_charges:
                other_charges = 0
        data_status = data.filter(status=1)
        if data_status:
            status = 'open'
        elif data.filter(status=3):
            status = 'cancel'
        else:
            status = 'closed'
            pick_status = picklist.filter(order_id__in=order_detail_ids,
                                          status__icontains='open')
            if pick_status:
                status = 'open'
        picked_quantity = picklist.filter(order_id__in=order_detail_ids).aggregate(Sum('picked_quantity'))
        if picked_quantity:
            picked_quantity = picked_quantity['picked_quantity__sum']
        if not picked_quantity:
            picked_quantity = 0
        record['picked_quantity'] = picked_quantity
        record['status'] = status
        if data:
            record['date'] = get_only_date(request, data[0].creation_date)
        else:
            record['date'] = ''
        if record['generic_order_id']:
            record['order_id'] = record['generic_order_id']

        record['Emiza_ids'] = ''
        emiza_order_ids = []
        if record['order_id']:
            related_order_ids = generic_orders.filter(generic_order_id=record['order_id']).values_list(
            'orderdetail__user','orderdetail__order_id','schedule_date')
            for usr , org_id, expected_date in related_order_ids:
                record['expected_date'] = expected_date.strftime("%d/%m/%y")
                if usr in orderprefix_map:
                    emiza_id = orderprefix_map[usr]+order_code+str(org_id)
                    emiza_order_ids.append(emiza_id)
            record['Emiza_ids'] = list(set(emiza_order_ids))

        record['order_detail_ids'] = list(order_details.values_list('orderdetail__order_id', flat=True).distinct())
        customer_id = record['customer_id']
        record['reseller_name'] = CustomerMaster.objects.get(id=customer_id).name
        for ord_det_id in order_detail_ids:
            gen_ord_obj = generic_orders.filter(orderdetail_id=ord_det_id)
            if gen_ord_obj:
                el_price = gen_ord_obj[0].el_price
                res_unit_price = gen_ord_obj[0].unit_price
                cm_id = gen_ord_obj[0].customer_id
                qty = gen_ord_obj[0].quantity
                user = gen_ord_obj[0].cust_wh_id
                sku_code = OrderDetail.objects.get(id=gen_ord_obj[0].orderdetail_id).sku_code
                if el_price:
                    record['el_price'] = el_price
                if res_unit_price:
                    tax_inclusive_inv_amt = get_tax_inclusive_invoice_amt(cm_id, res_unit_price, qty, user,
                                                                          sku_code, admin_user)
                    if 'total_inv_amt' not in record:
                        record['total_inv_amt'] = round(tax_inclusive_inv_amt, 2)
                    else:
                        record['total_inv_amt'] = round(record['total_inv_amt'] + tax_inclusive_inv_amt, 2)

                    data = OrderDetail.objects.filter(id=ord_det_id)
                    ord_det_qs = data.values('order_id', 'id', 'user', 'original_order_id', 'order_code', 'remarks')
                    if ord_det_qs:
                        order_detail_order_id = ord_det_qs[0]['original_order_id']
                        remarks = ord_det_qs[0]['remarks']
                        if not order_detail_order_id:
                            order_detail_order_id = str(ord_det_qs[0]['order_code']) + str(ord_det_qs[0]['order_id'])
                        other_charges = order_charges_obj_for_orderid(order_detail_order_id, request.user.id)
                        if other_charges:
                            record['total_inv_amt'] += round(other_charges, 2)

        temp_data['aaData'].append(OrderedDict(
            (('Order ID', record['order_id']), ('Ordered Qty', record['total_quantity']),('Emiza_order_ids', record['Emiza_ids']),('corporate_name', corporatae_name), ('po_number', record['po_number']),('remarks', remarks),('schedule_date', record['expected_date']),
             ('Delivered Qty',record['picked_quantity']), ('Pending Qty',record['total_quantity']-record['picked_quantity']), ('Order Value', record['total_inv_amt']),('Order Date', record['date']),('Receive Status',record['status']))))
    """return response_data"""


@csrf_exempt
def get_customer_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    """ Return customer orders"""
    response_data = {'data': []}
    admin_user = get_priceband_admin_user(user)
    if admin_user:
       get_level_based_customer_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters)
    else:
        lis = ['order_id','quantity', 'Delivered Qty', 'Pending Qty', 'Order Value', 'creation_date', 'Receive Status']
        search_params = get_filtered_params(filters, lis)
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data

        central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
        users_list = UserGroups.objects.filter(admin_user=user.id).values_list('user').distinct()
        customer = CustomerUserMapping.objects.filter(user=request.user.id)
        # lis = ['order_id', 'total_quantity', 'picked_quantity','total_quantity'-'picked_quantity', 'total_inv_amt']
        # search_params = get_filtered_params(filters, lis)

        intermediate_orders = []
        if customer:
            customer_id = customer[0].customer.customer_id
            if central_order_mgmt == 'true':
                orders_dict = {'customer_id': customer_id, 'user__in': users_list}
                pick_dict = {'order__customer_id': customer_id, 'order__user__in': users_list}
                intermediate_orders = list(IntermediateOrders.objects.filter(customer_user=request.user.id,\
                                                             status='')\
                                                             .values('interm_order_id').distinct()\
                                                             .annotate(total_quantity=Sum('quantity'),\
                                                              date_only=Cast('creation_date', DateField()),
                                                             intermediate_order=Value(True, output_field=BooleanField()))\
                                                             .order_by('-date_only'))
            else:
                orders_dict = {'customer_id': customer_id, 'user': user.id}
                pick_dict = {'order__customer_id': customer_id, 'order__user': user.id}
            orders = OrderDetail.objects.filter(**orders_dict).exclude(status=3).order_by('-creation_date')
            # if order_data:
            #     orders = OrderDetail.objects.filter(**orders_dict).order_by(order_data)
            if search_term:
                orders = OrderDetail.objects.filter(Q(original_order_id__icontains=search_term) |
                                                    Q(sku__sku_code__icontains=search_term)|
                                                    Q(sku__style_name__icontains=search_term),**orders_dict).order_by(order_data)
            temp_data['recordsTotal'] = len(orders)
            temp_data['recordsFiltered'] = temp_data['recordsTotal']
            picklist = Picklist.objects.filter(**pick_dict)
            real_orders = list(orders.values('order_id', 'order_code', 'original_order_id', 'intermediateorders__interm_order_id', 'intermediateorders__project_name')\
                                         .distinct()\
                                         .annotate(total_quantity=Sum('quantity'), total_inv_amt=Sum('invoice_amount'),
                                                  date_only=Cast('creation_date', DateField()),
                                                  intermediate_order=Value(False, output_field=BooleanField())).order_by('-date_only'))
            response_data['data'] = list(chain(intermediate_orders, real_orders))
        response_data['data'] = response_data['data'][start_index:stop_index]
        for record in response_data['data']:
            if record['intermediate_order']:
                record['status'] = 'Waiting For Approval'
                record['order_id'] = str(record['interm_order_id'])
                record['date'] = record['date_only']
                tot_inv_amt = IntermediateOrders.objects.filter(customer_user=request.user.id,\
                                        interm_order_id=record['interm_order_id'])\
                                        .values('interm_order_id', 'unit_price', 'quantity')\
                                        .aggregate(tot_inv_amt=Sum(F('unit_price')*F('quantity')))['tot_inv_amt']
                record['total_inv_amt'] = round(tot_inv_amt, 2)
                record['picked_quantity'] = 0
            else:
                data = orders.filter(order_id=int(record['order_id']), order_code=record['order_code'])
                data_status = data.filter(status=1)
                if data_status:
                    status = 'open'
                else:
                    status = 'closed'
                    pick_status = picklist.filter(order__order_id=int(record['order_id']),
                                                  order__order_code=record['order_code'], status__icontains='open')
                    if pick_status:
                        status = 'open'
                picked_quantity = picklist.filter(order__order_id=int(record['order_id'])).aggregate(
                    Sum('picked_quantity'))['picked_quantity__sum']
                if not picked_quantity:
                    picked_quantity = 0
                record['status'] = status
                record['date'] = get_only_date(request, data[0].creation_date)
                if record['original_order_id']:
                    record['order_id'] = record['original_order_id']
                else:
                    record['order_id'] = str(record['order_code']) + str(record['order_id'])
                other_charges = order_charges_obj_for_orderid(record['order_id'], request.user.id)
                if not other_charges:
                    other_charges = 0
                record['total_inv_amt'] = round(record['total_inv_amt'] + other_charges, 2)
                record['picked_quantity'] = picked_quantity

                temp_data['aaData'].append(OrderedDict(
                    (('Order ID', record['order_id']),('Ordered Qty', record['total_quantity']),
                    ('Delivered Qty',record['picked_quantity']), ('Pending Qty',record['total_quantity']-record['picked_quantity']),
                    ('Order Value', record['total_inv_amt']),('Order Date', record['date']), ('Project Name', record['intermediateorders__project_name']), ('Receive Status', record['status']))))

    """return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder))"""


@login_required
@get_admin_user
def print_pdf_my_orders_swiss(request, user=''):
    data = eval(request.POST['data'])
    data_dict = data['data'][0]['data']
    level_name_check = data_dict[0]
    sku_wise_details = data['sku_wise_details']['data']
    order_id = data['data'][0]['order_id']
    order_quantity = data['data'][0]['sum_data']['quantity']
    order_date = data['data'][0]['date']
    tax = data['data'][0]['tax']
    total_amount = data['data'][0]['sum_data']['amount']
    order_value =  total_amount - tax
    return render(request, 'templates/toggle/print_pdf_my_orders_swiss.html',{'data':data, 'data_dict':data_dict, 'order_id':order_id, 'order_quantity':order_quantity, 'order_value':order_value, 'tax':tax, 'total_amount':total_amount, 'order_date':order_date, 'sku_wise_details':sku_wise_details, 'level_name_check':level_name_check})




def construct_order_customer_order_detail(request, order, user):
    data_list = list(order.values('id', 'order_id', 'creation_date', 'status', 'quantity', 'invoice_amount',
                                  'sku__sku_code', 'sku__image_url', 'sku__sku_desc', 'sku__sku_brand',
                                  'sku__sku_category', 'sku__sku_class'))

    total_picked_quantity = 0
    admin_user = get_priceband_admin_user(user)
    for record in data_list:
        tax_data = CustomerOrderSummary.objects.filter(order__id=record['id'], order__user=user)
        picked_quantity = Picklist.objects.filter(order_id=record['id']).values(
            'picked_quantity').aggregate(Sum('picked_quantity'))['picked_quantity__sum']
        if not picked_quantity:
            picked_quantity = 0
        record['picked_quantity'] = picked_quantity
        total_picked_quantity += picked_quantity
        if tax_data:
            tax_data = tax_data[0]
            record['invoice_amount'] = record['invoice_amount'] - tax_data.tax_value
        gen_ord_obj = GenericOrderDetailMapping.objects.filter(orderdetail_id=record['id'])
        if gen_ord_obj:
            el_price = gen_ord_obj[0].el_price
            res_unit_price = gen_ord_obj[0].unit_price
            cm_id = gen_ord_obj[0].customer_id
            qty = gen_ord_obj[0].quantity
            record['quantity'] = qty
            user = gen_ord_obj[0].cust_wh_id
            sku_code = record['sku__sku_code']
            if el_price:
                record['el_price'] = el_price
            if res_unit_price:
                tax_exclusive_inv_amt = float(res_unit_price) * int(qty)
                tax_inclusive_inv_amt = get_tax_inclusive_invoice_amt(cm_id, res_unit_price, qty, user,
                                                                      sku_code, admin_user)
                record['invoice_amount'] = tax_inclusive_inv_amt
                record['sku_tax_amt'] = round(tax_inclusive_inv_amt - tax_exclusive_inv_amt, 2)
            schedule_date = gen_ord_obj[0].schedule_date
            if schedule_date:
                record['schedule_date'] = schedule_date.strftime('%d/%m/%Y')
            record['pending_quantity'] = record['quantity'] - record['picked_quantity']
    return data_list, total_picked_quantity


def prepare_your_orders_data(request, ord_id, usr_id, det_ids, order):
    response_data = {}
    other_charges = 0
    central_order_mgmt = get_misc_value('central_order_mgmt', usr_id)
    tax = CustomerOrderSummary.objects.filter(order_id__in=det_ids,
                                              order__user=usr_id).aggregate(Sum('tax_value'))[
        'tax_value__sum']
    if not tax:
        tax = 0
    order_ids = det_ids
    data_status = order.filter(status=1)
    if data_status:
        status = 'open'
    elif order.filter(status=3):
        status = 'cancel'
    else:
        status = 'closed'
        pick_status = Picklist.objects.filter(order_id__in=order_ids, status__icontains='open')
        if pick_status:
            status = 'open'
    response_data['status'] = status
    response_data['date'] = get_only_date(request, order[0].creation_date)
    response_data['order_id'] = order[0].order_id
    response_data['data'] = []
    if central_order_mgmt == 'true':
        sku = order[0].sku
        response_data['sku_spl_attrs'] = dict(SKUAttributes.objects.filter(sku_id__sku_code=sku.sku_code, sku__user =usr_id).
                                         values_list('attribute_name', 'attribute_value'))
    res, total_picked_quantity = construct_order_customer_order_detail(request, order, usr_id)
    total_inv_amt = map(sum, [[x['invoice_amount'] for x in res]])
    total_qty = map(sum, [[x['quantity'] for x in res]])
    total_tax = map(sum, [[x.get('sku_tax_amt', 0) for x in res]])
    response_data['tax'] = round(total_tax[0], 2)
    order_detail_order_id = order[0].original_order_id
    if not order[0].original_order_id:
        order_detail_order_id = str(order[0].order_code) + str(order[0].order_id)
    other_charges = order_charges_obj_for_orderid(order_detail_order_id, request.user.id)
    amount = float(total_inv_amt[0])
    if other_charges:
        amount = float(total_inv_amt[0]) + float(other_charges)
    else:
        other_charges = 0
    sum_data = {'picked_quantity': total_picked_quantity, 'amount': amount, 'quantity': total_qty[0]}
    response_data['sum_data'] = sum_data
    response_data['other_charges'] = other_charges
    response_data['data'].extend(res)
    return response_data, res


def get_level_based_customer_order_detail(request, user):
    whole_res_map = {}
    response_data_list = []
    sku_wise_details = {}
    order_charge_dict = {}
    generic_order_id = request.GET['order_id']
    is_autobackorder = request.GET.get('autobackorder', 'false')
    customer_id = request.GET.get('customer_id', '')
    user_profile = UserProfile.objects.get(user=request.user.id)
    if is_autobackorder == 'true':
        customer = WarehouseCustomerMapping.objects.filter(warehouse=user.id, status=1)
        if customer:
            cm_ids = CustomerUserMapping.objects.filter(customer__user=user.id).values_list('customer_id', flat=True)
            filter_dict = {'customer_id__in': cm_ids}
    elif user_profile.warehouse_type == 'WH':
        filter_dict = {'cust_wh_id__in': [user.id]}
        cus_mapping = CustomerUserMapping.objects.filter(user_id=request.user.id)
        if cus_mapping:
            customer = WarehouseCustomerMapping.objects.filter(customer_id=cus_mapping[0].customer_id, status=1)
            if customer:
                filter_dict['cust_wh_id__in'].append(customer[0].warehouse_id)
    else:
        cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
        cm_ids = cum_obj.values_list('customer_id', flat=True)
        filter_dict = {'customer_id__in': cm_ids}
    generic_orders = GenericOrderDetailMapping.objects.filter(**filter_dict)
    if customer_id:
        generic_orders = generic_orders.filter(customer_id=customer_id)
    order_detail_ids = generic_orders.filter(generic_order_id=generic_order_id).values_list(
        'orderdetail_id', flat=True)

    ord_det_qs = OrderDetail.objects.filter(id__in=order_detail_ids).values_list('order_id', 'id', 'user',
                                                                                 'original_order_id', 'order_code')
    ord_det_map = {}
    if ord_det_qs:
        order_detail_order_id = ord_det_qs[0][3]
        if not order_detail_order_id:
            order_detail_order_id = str(ord_det_qs[0][4]) + str(ord_det_qs[0][0])
        other_charges = order_charges_obj_for_orderid(order_detail_order_id, request.user.id)

    for ord_id, det_id, usr_id, original_order_id, order_code in ord_det_qs:
        ord_det_map.setdefault(int(ord_id), {}).setdefault(usr_id, []).append(det_id)
    for ord_id, usr_det_ids in ord_det_map.items():
        for usr_id, det_ids in usr_det_ids.items():
            response_data, res = prepare_your_orders_data(request, ord_id, usr_id, det_ids,
                                                     OrderDetail.objects.filter(id__in=det_ids))
            ord_usr_profile = UserProfile.objects.get(user_id=usr_id)
            for sku_rec in res:
                sku_code = sku_rec['sku__sku_code']
                sku_qty = sku_rec['quantity']
                sku_el_price = round(sku_rec.get('el_price', 0), 2)
                sku_tax_amt = round(sku_rec.get('sku_tax_amt', 0), 2)
                gen_obj = GenericOrderDetailMapping.objects.get(orderdetail_id=sku_rec['id'])
                cm_obj = CustomerMaster.objects.get(id=gen_obj.customer_id)
                is_distributor = cm_obj.is_distributor
                if not is_distributor and cm_obj.user == usr_id:
                     response_data['warehouse_level'] = 0
                else:
                    response_data['warehouse_level'] = ord_usr_profile.warehouse_level
                response_data['level_name'] = get_level_name_with_level(user, response_data['warehouse_level'],
                                                                     users_list=[usr_id])
                if sku_code not in sku_wise_details:
                    sku_wise_details[sku_code] = {'quantity': sku_qty, 'el_price': sku_el_price,
                                                  'sku_tax_amt': sku_tax_amt}
                else:
                    existing_map = sku_wise_details[sku_code]
                    existing_map['quantity'] = existing_map['quantity'] + sku_qty
                    existing_map['sku_tax_amt'] = existing_map['sku_tax_amt'] + sku_tax_amt
            response_data_list.append(response_data)
    sku_whole_map = {'data': [], 'totals': {}}
    sku_totals = {'sub_total': 0, 'total_amount': 0, 'tax': 0}
    for sku_code, sku_det in sku_wise_details.items():
        el_price = sku_det['el_price']
        qty = sku_det['quantity']
        tax_amt = sku_det['sku_tax_amt']
        total_amt = float(qty) * float(el_price)
        sku_map = {'sku_code': sku_code, 'quantity': qty, 'landing_price': el_price, 'total_amount': total_amt}
        if other_charges:
            sku_totals['other_charges'] = other_charges
        else:
            other_charges = 0
            sku_totals['other_charges'] = 0
        sku_totals['sub_total'] = sku_totals['sub_total'] + total_amt
        sku_totals['tax'] = round(sku_totals['tax'] + tax_amt, 2)
        sku_totals['total_amount'] = round(sku_totals['sub_total'] + sku_totals['tax'] + other_charges, 2)
        sku_whole_map['data'].append(sku_map)
        sku_whole_map['totals'] = sku_totals
    whole_res_map['data'] = response_data_list
    whole_res_map['sku_wise_details'] = sku_whole_map
    return whole_res_map


def order_charges_obj_for_orderid(order_id, user_id):
    total_charge_amount = 0
    order_charge_obj = []
    dist_id_obj = CustomerUserMapping.objects.filter(user=user_id).values_list('customer__id')
    if dist_id_obj:
        dist_id = dist_id_obj[0]
        if dist_id:
            cust_wh_ids = GenericOrderDetailMapping.objects.filter(customer_id__in=dist_id).values_list('cust_wh_id',
                                                                                                        flat=True).distinct()
            if cust_wh_ids:
                order_charge_obj = OrderCharges.objects.filter(order_id=order_id, user__in=cust_wh_ids, order_type='order')
                total_charge_amount = order_charge_obj.aggregate(Sum('charge_amount'))['charge_amount__sum']
    return total_charge_amount


@login_required
@get_admin_user
def get_intermediate_order_detail(request, user=""):
    """ Return intermediate order detail """
    log.info('Request params for ' + user.username + ' is ' + str(request.GET.dict()))
    response_data = {'data': [], 'sum_data': {}}
    order_id = request.GET['order_id']
    if not order_id:
        return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder))

    admin_user = get_priceband_admin_user(user)
    intermediate_order = IntermediateOrders.objects.filter(customer_user=request.user.id,\
                                                    interm_order_id=order_id)\
                                                    .values('interm_order_id', 'unit_price', 'quantity',\
                                                    'sku__image_url', 'tax', 'creation_date', 'status',\
                                                    'sku__sku_brand', 'sku__sku_category', 'sku__sku_class',\
                                                    'sku__sku_code', 'sku__sku_desc')
    aggr_values = intermediate_order.aggregate(tot_inv_amt=Sum(F('unit_price')*F('quantity')), tot_qty = Sum('quantity'))
    response_data['sum_data'] = {'amount': aggr_values['tot_inv_amt'],
                                 'picked_quantity': 0,
                                 'quantity': aggr_values['tot_qty']
                                }
    response_data['date'] = intermediate_order[0]['creation_date'].strftime('%d/%m/%Y')
    response_data['status'] = 'Waiting For Approval'
    response_data['order_id'] = intermediate_order[0]['interm_order_id']
    response_data['other_charges'] = 0
    for order in intermediate_order:
        response_data['data'].append({
                                        'order_id': order['interm_order_id'],
                                        'sku__image_url': order['sku__image_url'],
                                        'sku__sku_brand': order['sku__sku_brand'],
                                        'sku__sku_category': order['sku__sku_category'],
                                        'sku__sku_class': order['sku__sku_class'],
                                        'sku__sku_code': order['sku__sku_code'],
                                        'sku__sku_desc': order['sku__sku_desc'],
                                        'quantity': order['quantity'],
                                        'picked_quantity': 0,
                                        'invoice_amount': order['unit_price']*order['quantity']
                                    })
    final_data = {'data': [response_data]}
    return HttpResponse(json.dumps(final_data, cls=DjangoJSONEncoder))


@login_required
@get_admin_user
def get_customer_order_detail(request, user=""):
    """ Return customer order detail """
    log.info('Request params for ' + user.username + ' is ' + str(request.GET.dict()))
    response_data = {'data': []}
    order_id = request.GET['order_id']
    if not order_id:
        return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder))

    admin_user = get_priceband_admin_user(user)
    if admin_user:
        response_data_list = get_level_based_customer_order_detail(request, user)
        final_data = response_data_list
    else:
        central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
        if central_order_mgmt == 'true':
            customer = CustomerUserMapping.objects.filter(user=request.user.id)
            if customer:
                customer_id = customer[0].customer.customer_id
                users_list = UserGroups.objects.filter(admin_user=user.id).values_list('user').distinct()
                search_params = {'user__in': users_list, 'customer_id': customer_id}
                order_id_search = ''.join(re.findall('\d+', order_id))
                order_code_search = ''.join(re.findall('\D+', order_id))
                order = OrderDetail.objects.filter(Q(order_id=order_id_search, order_code=order_code_search) |
                                                   Q(original_order_id=order_id), **search_params)
        else:
            order = get_order_detail_objs(order_id, user)
        det_ids = order.values_list('id', flat=True)
        if not order:
            return HttpResponse(json.dumps(response_data, cls=DjangoJSONEncoder))
        ord_id = order[0].original_order_id
        if not ord_id:
            ord_id = order[0].order_code + str(order[0].order_id)
        response_data, res = prepare_your_orders_data(request, order_id, user.id, det_ids, order)
        response_data_list = [response_data]
        final_data = {'data': response_data_list}
    log.info('Response data for parent user ' + user.username + ' request user ' + request.user.username + ' is ' + str(
        final_data))
    return HttpResponse(json.dumps(final_data, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def generate_pdf_file(request, user=""):
    nv_data = request.POST['data']
    c = {'name': 'kanna'}
    if request.POST.get('css', '') == 'page':
        top = loader.get_template('../miebach_admin/templates/toggle/invoice/top.html')
    else:
        top = loader.get_template('../miebach_admin/templates/toggle/invoice/top1.html')
    top = top.render(c)
    nv_data = nv_data.encode('utf-8')
    html_content = str(top) + nv_data  # +"</div>"
    if not os.path.exists('static/pdf_files/'):
        os.makedirs('static/pdf_files/')
    file_name = 'static/pdf_files/%s_dispatch_invoice.html' % str(request.user.id)
    name = str(request.user.id) + "_dispatch_invoice"
    pdf_file = 'static/pdf_files/%s.pdf' % name
    file_ = open(file_name, "w+b")
    file_.write(html_content)
    file_.close()
    os.system("./phantom/bin/phantomjs ./phantom/examples/rasterize.js ./%s ./%s A4" % (file_name, pdf_file))
    return HttpResponse("../static/pdf_files/" + str(request.user.id) + "_dispatch_invoice.pdf")


def get_tax_value(user, record, product_type, tax_type):
    inter_state = False
    if tax_type == 'inter_state' or tax_type == 'Inter State':
        inter_state = True
    amt = record['price']
    admin_user = get_priceband_admin_user(user)
    if admin_user:
        tax_data = TaxMaster.objects.filter(user_id=admin_user.id, product_type=product_type, inter_state=inter_state,
                                            min_amt__lte=amt, max_amt__gte=amt)
    else:
        tax_data = TaxMaster.objects.filter(user_id=user.id, product_type=product_type, inter_state=inter_state,
                                            min_amt__lte=amt, max_amt__gte=amt)
    if tax_data:
        tax_data = tax_data[0]
        if inter_state:
            record['igst_tax'] = tax_data.igst_tax
            record['cgst_tax'] = 0
            record['sgst_tax'] = 0
            return tax_data.igst_tax
        else:
            record['igst_tax'] = 0
            record['cgst_tax'] = tax_data.cgst_tax
            record['sgst_tax'] = tax_data.sgst_tax
            return tax_data.sgst_tax + tax_data.cgst_tax
    else:
        return 0


@login_required
@get_admin_user
def get_customer_cart_data(request, user=""):
    """  return customer cart data """

    response = {'data': [], 'msg': 0, 'reseller_corporates': []}
    price_band_flag = get_misc_value('priceband_sync', user.id)
    central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
    reseller_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    if reseller_obj and price_band_flag == 'true':
        reseller_id = reseller_obj[0].customer_id
        central_admin = get_admin(user)
        res_corps = list(CorpResellerMapping.objects.filter(reseller_id=reseller_id,
                                                   status=1).values_list('corporate_id', flat=True).distinct())
        corp_names = CorporateMaster.objects.filter(corporate_id__in=res_corps, user=central_admin.id).values_list('name', flat=True).distinct()
        response['reseller_corporates'].extend(corp_names)
    elif reseller_obj and central_order_mgmt == 'true': # ISPRAVA
        corp_names = CorporateMaster.objects.filter(user=user.id).values_list('name', flat=True).distinct()
        response['reseller_corporates'].extend(corp_names)

    cart_data = CustomerCartData.objects.filter(user_id=user.id, customer_user_id=request.user.id)

    if cart_data:
        cust_user_obj = CustomerUserMapping.objects.filter(user=request.user.id)
        tax_type = CustomerUserMapping.objects.filter(user_id=request.user.id).values_list('customer__tax_type',
                                                                                           flat=True)
        tax = 0
        if tax_type:
            tax_type = tax_type[0]
        cm_obj = CustomerMaster.objects.get(id=cust_user_obj[0].customer_id)
        is_distributor = cm_obj.is_distributor
        todays_date = datetime.datetime.today().date()
        for record in cart_data:
            del_days = 0
            if is_distributor:
                dist_mapping = WarehouseCustomerMapping.objects.get(customer_id=cm_obj.id, status=1)
                dist_wh_id = dist_mapping.warehouse.id
                price_type = NetworkMaster.objects.filter(dest_location_code_id=dist_wh_id,
                                                          source_location_code_id=user.id). \
                    values_list('price_type', flat=True)
                dist_reseller_leadtime = 0
            else:
                price_type = cm_obj.price_type
                dist_reseller_leadtime = cm_obj.lead_time
            json_record = record.json()
            sku_obj = SKUMaster.objects.filter(user=user.id, sku_code=json_record['sku_id'])
            warehouses = list(UserGroups.objects.filter(admin_user_id=user.id).values_list('user_id', flat=True))
            warehouses.append(user.id)
            available_stock = StockDetail.objects.exclude(Q(receipt_number=0) | \
                              Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE']))\
                              .filter(sku__sku_code=sku_obj[0].sku_code, sku__user__in=warehouses)\
                              .aggregate(Sum('quantity'))['quantity__sum']
            cart_qty, inter_qty = 0, 0
            inter_obj = IntermediateOrders.objects.filter(sku=sku_obj[0].id, status='')
            if inter_obj:
                inter_qty = inter_obj.aggregate(Sum('quantity'))['quantity__sum']#inter_obj[0].quantity
            blocked_qty = inter_qty
            if available_stock:
                json_record['available_stock'] = available_stock - blocked_qty
            else:
                json_record['available_stock'] = 0
            if central_order_mgmt == 'true':
                sku_id = sku_obj[0].id
                sku_spl_attrs = dict(SKUAttributes.objects.filter(sku_id=sku_id).
                                     values_list('attribute_name', 'attribute_value'))
                json_record.update(sku_spl_attrs)
            json_record['mrp'] = sku_obj[0].mrp
            json_record['cost_price'] = sku_obj[0].cost_price
            json_record['sku_style'] = sku_obj[0].sku_class
            json_record['sku_desc'] = sku_obj[0].sku_desc
            json_record['colour'] = sku_obj[0].color
            json_record['sku_pk'] = sku_obj[0].id
            json_record['add_to_cart'] = 'true'
            product_type = sku_obj[0].product_type
            price_field = get_price_field(user)
            is_sellingprice = False
            if price_field == 'price':
                is_sellingprice = True
            json_record['price'], json_record['mrp'] = get_customer_based_price(cm_obj, json_record[price_field], json_record['mrp'],
                                                            is_sellingprice)
            if not tax_type and product_type:
                json_record['tax'] = 0
            else:
                json_record['tax'] = get_tax_value(user, json_record, product_type, tax_type)
            if price_band_flag == 'true':
                central_admin = get_admin(user)
                #Getting level name
                users_list = UserGroups.objects.filter(admin_user=central_admin.id).values_list('user').distinct()
                level_name = get_level_name_with_level(user, json_record['warehouse_level'],
                                                       users_list=users_list)
                json_record['level_name'] = level_name
                if json_record['warehouse_level'] == 2:
                    json_record['freight_charges'] = "true"
                else:
                    json_record['freight_charges'] = "false"
                if record.warehouse_level:
                    whs = get_same_level_warehouses(level=record.warehouse_level, central_admin=central_admin)
                else:
                    whs = [record.user.id]
                tot_avail_stock = 0
                cart_qty = json_record['quantity']
                wh_level_stock_map = {}
                nk_filters = {'status': 'open', 'sku__sku_code': record.sku.sku_code, 'asn_po_num': 'NON_KITTED_STOCK'}
                nk_stock_map = dict(ASNStockDetail.objects.filter(**nk_filters).values_list('sku__user').annotate(Sum('quantity')))
                for wh in whs:
                    sku_id = get_syncedusers_mapped_sku(wh=wh, sku_id=record.sku.id)
                    if record.warehouse_level == 3:
                        intransit_obj = ASNStockDetail.objects.filter(quantity__gt=0, status='open',
                                                                      sku=sku_id).only('sku__sku_code',
                                                                                       'quantity').values(
                            'sku__sku_code').distinct().annotate(in_asn=Sum('quantity'))
                        if intransit_obj:
                            avail_stock = intransit_obj[0]['in_asn']
                        else:
                            avail_stock = 0
                    else:

                        stock_obj = StockDetail.objects.filter(sku=sku_id, quantity__gt=0).values(
                            'sku_id').distinct().annotate(in_stock=Sum('quantity'))
                        if stock_obj:
                            stock_qty = stock_obj[0]['in_stock']
                        else:
                            stock_qty = 0
                        reserved_obj = PicklistLocation.objects.filter(stock__sku=sku_id, status=1).values(
                            'stock__sku_id').distinct().annotate(in_reserved=Sum('reserved'))
                        if reserved_obj:
                            reserved_qty = reserved_obj[0]['in_reserved']
                        else:
                            reserved_qty = 0
                        enq_qty = EnquiredSku.objects.filter(sku__user=wh, sku_code=record.sku.sku_code,
                                                             warehouse_level=record.warehouse_level).filter(
                            ~Q(enquiry__extend_status='rejected')).values_list('sku_code').aggregate(Sum('quantity'))[
                            'quantity__sum']
                        if not enq_qty:
                            enq_qty = 0
                        avail_stock = stock_qty - reserved_qty - enq_qty
                        avail_stock = avail_stock - nk_stock_map.get(wh, 0)
                    if wh not in wh_level_stock_map:
                        wh_level_stock_map[wh] = avail_stock
                    else:
                        wh_level_stock_map[wh] += avail_stock
                    tot_avail_stock = tot_avail_stock + avail_stock
                json_record['avail_stock'] = tot_avail_stock
                # level = json_record['warehouse_level']
                if is_distributor:
                    if price_type:
                        price_type = price_type[0]
                    if cm_obj:
                        dist_mapping = WarehouseCustomerMapping.objects.filter(customer_id=cm_obj, status=1)
                        dist_userid = dist_mapping[0].warehouse_id
                        lead_times = get_leadtimes(dist_userid, record.warehouse_level)
                        leadtime_qty = 0
                        for lead_time, whs in lead_times.items():
                            for wh in whs:
                                if wh in wh_level_stock_map:
                                    leadtime_qty += wh_level_stock_map[wh]
                            if cart_qty <= leadtime_qty:
                                del_days = lead_time
                                break
                        else:
                            del_days = lead_time
                        json_record['default_shipment_address'] = cm_obj.address
                else:
                    price_type = update_level_price_type(cm_obj, record.warehouse_level, price_type)
                    if record.warehouse_level:
                        lead_times = get_leadtimes(user.id, record.warehouse_level)
                        # reseller_leadtimes = map(lambda x: x + dist_reseller_leadtime, lead_times)
                        leadtime_qty = 0
                        for lead_time, whs in lead_times.items():
                            for wh in whs:
                                if wh in wh_level_stock_map:
                                    leadtime_qty += wh_level_stock_map[wh]
                            if cart_qty <= leadtime_qty:
                                del_days = lead_time + dist_reseller_leadtime
                                break
                    else:
                        del_days = dist_reseller_leadtime
                    res_address = cm_obj.address
                    dist_cm_obj = WarehouseCustomerMapping.objects.get(warehouse_id=cm_obj.user).customer
                    dist_address = dist_cm_obj.address
                    json_record['reseller_addr'] = res_address
                    json_record['distributor_addr'] = dist_address
                price_master_objs = PriceMaster.objects.filter(price_type=price_type,
                                                               sku__user=central_admin.id,
                                                               sku__sku_code=json_record['sku_id'])
                if price_master_objs:
                    for pm_obj in price_master_objs:
                        pm_obj_map = {'min_unit_range': pm_obj.min_unit_range,
                                      'max_unit_range': pm_obj.max_unit_range,
                                      'price': pm_obj.price}
                        json_record.setdefault('prices', []).append(pm_obj_map)
                        if pm_obj.min_unit_range == 0:
                            json_record['price'] = pm_obj.price
            else:
                price_master_obj = PriceMaster.objects.filter(price_type=price_type,
                                                              sku__id=record.sku_id)
                if price_master_obj:
                    price_master_obj = price_master_obj[0]
                    json_record['price'] = price_master_obj.price
            #if cm_obj.margin:
            #    json_record['price'] = float(json_record['price']) * (1 + (float(cm_obj.margin) / 100))
            json_record['invoice_amount'] = json_record['quantity'] * json_record['price']
            json_record['total_amount'] = ((json_record['invoice_amount'] * json_record['tax']) / 100) + \
                                          json_record['invoice_amount']
            total_qty = 0
            break_flag = False
            if record.warehouse_level == 3:
                stock_wh_map = fetch_asn_stock(record.sku.user, record.sku.sku_code, cart_qty)
                lt_wh_map = dict(NetworkMaster.objects.filter(dest_location_code=user.id).values_list('source_location_code', 'lead_time'))
                for lt, wh_map in stock_wh_map.items():
                    for wh, avail_qty in wh_map.items():
                        total_qty = total_qty + avail_qty
                        if cart_qty <= total_qty:
                            wh_lt = lt_wh_map.get(wh, 0)
                            del_days = lt + wh_lt
                            break_flag = True
                            break
                    if break_flag:
                        break
                else:
                    del_days = lt

            date = datetime.datetime.now()
            date += datetime.timedelta(days=del_days)
            del_date = date.strftime("%d/%m/%Y")
            json_record['del_date'] = del_date
            response['data'].append(json_record)
    if cart_data and cm_obj.is_distributor:
        warehouse_obj = WarehouseCustomerMapping.objects.filter(customer = cm_obj)
        if warehouse_obj.exists():
            min_order_value = warehouse_obj[0].warehouse.userprofile.min_order_val
            response['is_distributor'] = cm_obj.is_distributor
            response['min_order_value'] = min_order_value
    response['invoice_types'] = get_invoice_types(user)
    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


@login_required
@get_admin_user
def insert_customer_cart_data(request, user=""):
    """ insert customer cart data """
    response = {'data': [], 'msg': 0}
    items = []
    cart_data = request.GET.get('data', '')
    if cart_data:
        cart_data = eval(cart_data)
        for record in cart_data:
            sku = SKUMaster.objects.get(sku_code=record['sku_id'], user=user.id)
            cart = CustomerCartData.objects.filter(user_id=user.id, customer_user_id=request.user.id,
                                                   sku__sku_code=record['sku_id'], warehouse_level=record['level'])
            if not cart:
                isprava_unique = get_misc_value('order_exceed_stock',user.id)
                if isprava_unique == 'true':
                    stock_display_warehouse = get_misc_value('stock_display_warehouse', user.id)
                    if stock_display_warehouse and stock_display_warehouse != "false":
                        stock_display_warehouse = stock_display_warehouse.split(',')
                        stock_display_warehouse = map(int, stock_display_warehouse)
                    cart_obj = CustomerCartData.objects.filter(sku__sku_code=record['sku_id']).exclude(customer_user_id=request.user.id)
                    cart_qty = 0
                    if cart_obj:
                        cart_qty = cart_obj.aggregate(Sum('quantity'))['quantity__sum']
                    stocks = StockDetail.objects.filter(sku__user__in=stock_display_warehouse, sku__sku_code=record['sku_id'],
                                                        quantity__gt=0)
                    avail_qty = check_stock_available_quantity(stocks, user, stock_ids=None)
                    quantity = cart_qty + record['quantity']
                    if quantity > avail_qty:
                        response['msg'] = 0
                        response['data'] = "No Available Quantiy for Sku  %s' "% (str(record['sku_id']))
                        return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))

                data = {'user_id': user.id, 'customer_user_id': request.user.id, 'sku_id': sku.id,
                        'quantity': record['quantity'], 'tax': record['tax'], 'warehouse_level': record['level'],
                        'levelbase_price': record['price']}
                customer_cart_data = CustomerCartData(**data)
                customer_cart_data.save()
            else:
                cart = cart[0]
                cart.quantity = cart.quantity + record['quantity']
                cart.save()

        response['data'] = "Inserted Successfully"
        response['msg'] = 1
    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


@login_required
@get_admin_user
def update_customer_cart_data(request, user=""):
    """ update customer cart data """

    response = {'data': [], 'msg': 0}
    sku_code = request.POST.get('sku_code', '')
    quantity = request.POST.get('quantity', '')
    remarks = request.POST.get('remarks', '')
    price = request.POST.get('price', '')
    level = request.POST.get('level', '')

    if sku_code:
        cart = CustomerCartData.objects.filter(user_id=user.id, customer_user_id=request.user.id,
                                               sku__sku_code=sku_code, warehouse_level=level)
        if cart:
            cart = cart[0]
            cart.quantity = quantity
            cart.levelbase_price = price
            cart.remarks = remarks
            if float(quantity) == 0.0:
                cart.delete()
                response['data'] = "Deleted Successfully"
            else:
                cart.save()
                response['data'] = "Updated Successfully"
    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


@login_required
@get_admin_user
def delete_customer_cart_data(request, user=""):
    """ delete customer cart data """

    log.info('Request params for ' + user.username + ' is ' + str(request.GET.dict()))
    try:
        response = {'msg': 0}
        sku_level_map = request.GET.dict()

        if sku_level_map:
            sku_code, level = sku_level_map.items()[0]
            if level == '':
                level = 0
            CustomerCartData.objects.filter(user_id=user.id, customer_user_id=request.user.id,
                                            sku__sku_code=sku_code, warehouse_level=level).delete()
            response["msg"] = "Deleted Successfully"
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Deleting customer cart data failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))

@csrf_exempt
def get_invoice_shipment(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              user_dict={}, filters={}):
    lis = ['invoice_number','invoice_number', 'order__order_id', 'order__customer_id', 'order__customer_name', 'order__marketplace',
            'invoice_number', 'invoice_number', 'invoice_number','creation_date']
    result_values = ['invoice_number', 'full_invoice_number', 'financial_year','order__original_order_id',
                     'order__customer_name', 'order__marketplace', 'order__customer_id', 'order__address']
    if user_dict:
        user_dict = eval(user_dict)
    user_filter = {'order__user': user.id}
    if user_dict.get('market_place', ''):
            marketplace = user_dict['market_place'].split(',')
            user_filter['order__marketplace__in'] = marketplace
    if user_dict.get('customer', ''):
        user_filter['order__customer_id'] = user_dict['customer']
    if user_dict.get('order_id', ''):
        order_id_filter = ''.join(re.findall('\d+', user_dict['order_id']))
        order_code_filter = ''.join(re.findall('\D+', user_dict['order_id']))
        user_filter['order_id__in'] = OrderDetail.objects.filter(Q(original_order_id__icontains=user_dict['order_id']) |
                                                               Q(order_id__icontains=order_id_filter,
                                                                 order_code__icontains=order_code_filter),
                                                               user=user.id)
    if user_dict.get('from_date', ''):
        from_date = user_dict['from_date'].split('/')
        user_dict['from_date'] = datetime.date(int(from_date[2]), int(from_date[0]), int(from_date[1]))
        user_dict['from_date'] = datetime.datetime.combine(user_dict['from_date'], datetime.time())
        user_filter['creation_date__gt'] = user_dict['from_date']
    if user_dict.get('to_date', ''):
        to_date = user_dict['to_date'].split('/')
        user_dict['to_date'] = datetime.date(int(to_date[2]), int(to_date[0]), int(to_date[1]))
        user_dict['to_date'] = datetime.datetime.combine(user_dict['to_date'] + datetime.timedelta(1), datetime.time())
        user_filter['creation_date__lt'] = user_dict['to_date']
    #shiped_invoices = list(ShipmentInfo.objects.filter(order__user=user.id).values_list('invoice_number', flat=True))
    shiped_invoices = list(ShipmentInfo.objects.filter(order__user=user.id).values('order_id').distinct().\
                           annotate(ship_total=Sum('shipping_quantity'),
                        ordered=Cast(Sum(F('order__original_quantity')-F('order__cancelled_quantity'))/Count('order_id'),output_field=FloatField())).\
                           filter(ship_total__gte=F('ordered')).values_list('invoice_number', flat=True))
    if search_term:
        search_term = search_term.replace('(', '\(').replace(')', '\)')
        search_query = build_search_term_query(list(set(lis)), search_term)
        order_id_search = ''.join(re.findall('\d+', search_term))
        order_code_search = ''.join(re.findall('\D+', search_term))
        master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                                                annotate(total_quantity=Sum('quantity'),
                                                         ordered_quantity=Sum('order__quantity', distinct=True)).\
                                                    filter(Q(full_invoice_number__icontains=search_term)| search_query)
    elif order_term:
        if order_term == 'asc' and (col_num or col_num == 0):
            master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                annotate(total_quantity=Sum('quantity'),\
                         ordered_quantity=Sum('order__quantity', distinct=True)).order_by(lis[col_num])
        else:
            master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                annotate(total_quantity=Sum('quantity'),\
                         ordered_quantity=Sum('order__quantity', distinct=True)).order_by('-%s' % lis[col_num])
    else:
        master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'), ordered_quantity=Sum('order__quantity', distinct=True))
    order_summaries = SellerOrderSummary.objects.filter(Q(order__user=user.id))
    master_data = master_data.exclude(full_invoice_number__in=shiped_invoices).exclude(invoice_number='')
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for data in master_data[start_index:stop_index]:
        invoice_amount = 0
        picked_amount = 0
        tax_amount = 0
        invoice_date = ''
        total_inv_dict = {}
        seller_order_summaries = order_summaries.filter(invoice_number=data['invoice_number'],
                                                    financial_year=data['financial_year'], order__marketplace=data['order__marketplace'])
        order_ids = seller_order_summaries.values_list('order__id', flat= True)
        picked_dict = seller_order_summaries.annotate(pic_qty=Sum('quantity'))\
                        .values_list('order__id','pic_qty')
        invoice_dict = OrderDetail.objects.filter(id__in=order_ids)\
                                          .annotate(cur_amt=((F('unit_price')* F('original_quantity'))-F('customerordersummary__discount')))\
                                          .annotate(tax_amt=((F('cur_amt')*(F('customerordersummary__cgst_tax')+F('customerordersummary__sgst_tax')+F('customerordersummary__igst_tax'))*0.01)))\
                                          .values('tax_amt','cur_amt','id','original_quantity')
        for obj in invoice_dict:
            order_id=obj.get('id')
            total_inv_dict[order_id]=obj
        for value in picked_dict:
            if value:
                invoice_amount+=(total_inv_dict[value[0]].get('cur_amt',0)*(value[1]/total_inv_dict[value[0]].get('original_quantity',1)))
                tax_amount +=(total_inv_dict[value[0]].get('tax_amt',0)*(value[1]/total_inv_dict[value[0]].get('original_quantity',1)))
                picked_amount =invoice_amount+tax_amount
        order = seller_order_summaries[0].order
        original_order_id = order.original_order_id
        #invoice_date = seller_order_summaries[0].order.customerordersummary_set.filter()[0].invoice_date
        #invoice_date = CustomerOrderSummary.objects.filter(order_id__in=order_ids)\
        #                                   .order_by('-invoice_date').values_list('invoice_date', flat=True)[0]
        #if not invoice_date:
        invoice_date = seller_order_summaries[0].creation_date
        data['ordered_quantity'] = OrderDetail.objects.filter(user=user.id, original_order_id=original_order_id).\
                only('original_quantity').aggregate(Sum('original_quantity'))['original_quantity__sum']

        if not data['ordered_quantity']:
            data['ordered_quantity'] = 0

        order_date = get_local_date(user, order.creation_date)
        invoice_date = invoice_date.strftime("%d %b %Y") if invoice_date else order.creation_date.strftime("%d %b %Y")
        temp_data['aaData'].append(OrderedDict((('Order ID', data['order__original_order_id']), ('Invoice Number', data['full_invoice_number']),
                                                ('Customer ID', data['order__customer_id']),
                                                ('Customer Name', data['order__customer_name']),
                                                ('Marketplace', data['order__marketplace']),
                                                ('Address',data['order__address']),
                                                ('Picked Quantity', data['total_quantity']),
                                                ('Total Quantity', data['ordered_quantity']), ('Invoice Date', invoice_date),
                                                ('DT_RowClass', 'results'), ('order_id', data['order__original_order_id']))))

@csrf_exempt
def get_order_shipment_picked(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              user_dict={}, filters={}):
    '''Shipment Info Alternative datatable code '''
    log.info("Shipment Alternative view started")
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    if user_dict:
        user_dict = eval(user_dict)
    user_dict['groupby'] = 'order'
    if user_dict['groupby'] == 'invoice':
        temp_data['aaData'] == ''
        # get_invoice_shipment(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
        #                       user_dict, filters)
    else:
        lis = ['order__order_id', 'order__order_id', 'order__customer_id', 'order__customer_name', 'order__marketplace',
               'order__address',
               'total_picked',
               'total_ordered', 'order__creation_date']
        data_dict = {'status__in': ['picked', 'batch_picked', 'open', 'batch_open'], 'order__user': user.id,
                     'picked_quantity__gt': 0}

        if user_dict.get('market_place', ''):
            marketplace = user_dict['market_place'].split(',')
            data_dict['order__marketplace__in'] = marketplace
        if user_dict.get('customer', ''):
            # data_dict['order__customer_id'], data_dict['order__customer_name'] = user_dict['customer'].split(':')
            data_dict['order__customer_id'] = user_dict['customer']
        if user_dict.get('order_id', ''):
            order_id_filter = ''.join(re.findall('\d+', user_dict['order_id']))
            order_code_filter = ''.join(re.findall('\D+', user_dict['order_id']))
            data_dict['order_id__in'] = OrderDetail.objects.filter(Q(original_order_id__icontains=user_dict['order_id']) |
                                                                   Q(order_id__icontains=order_id_filter,
                                                                     order_code__icontains=order_code_filter),
                                                                   user=user.id)
        if user_dict.get('from_date', ''):
            from_date = user_dict['from_date'].split('/')
            user_dict['from_date'] = datetime.date(int(from_date[2]), int(from_date[0]), int(from_date[1]))
            user_dict['from_date'] = datetime.datetime.combine(user_dict['from_date'], datetime.time())
            data_dict['order__creation_date__gt'] = user_dict['from_date']
        if user_dict.get('to_date', ''):
            to_date = user_dict['to_date'].split('/')
            user_dict['to_date'] = datetime.date(int(to_date[2]), int(to_date[0]), int(to_date[1]))
            user_dict['to_date'] = datetime.datetime.combine(user_dict['to_date'] + datetime.timedelta(1), datetime.time())
            data_dict['order__creation_date__lt'] = user_dict['to_date']

        search_params = get_filtered_params(filters, lis[1:])

        ship = dict(ShipmentInfo.objects.filter(order__user=user.id).annotate(full_order=Concat('order__order_code',
                                                                                                'order__order_id',
                                                                                                output_field=CharField())).values_list(
            'full_order'). \
                    annotate(tshipped=Sum('shipping_quantity')))
        pick = dict(
            Picklist.objects.filter(order__user=user.id, status__in=['open', 'batch_open', 'picked', 'batch_picked']). \
            annotate(full_order=Concat('order__order_code', 'order__order_id', output_field=CharField())). \
            values_list('full_order').distinct().annotate(tpicked=Sum('picked_quantity')))

        pick_diff = ({key: pick[key] - ship.get(key, 0) for key in pick.keys()})
        excl_order_ids = ({k: v for k, v in pick_diff.items() if v <= 0}).keys()


        if search_term:
            order_id_search = ''.join(re.findall('\d+', search_term))
            order_code_search = ''.join(re.findall('\D+', search_term))
            master_data = Picklist.objects.exclude(order__original_order_id__in=excl_order_ids).filter(
                Q(order__sku_id__in=sku_master_ids) |
                Q(stock__sku_id__in=sku_master_ids), **data_dict). \
                values('order__order_id', 'order__order_code', 'order__original_order_id', 'order__customer_id',
                       'order__customer_name', 'order__address','order__marketplace').distinct(). \
                annotate(total_picked=Sum('picked_quantity'), total_ordered=Sum('order__quantity')). \
                filter(Q(order__order_id__icontains=order_id_search) |
                       Q(order__sku__sku_code__icontains=search_term) |
                       Q(order__address__icontains=search_term) |
                       Q(order__title__icontains=search_term) | Q(order__customer_id__icontains=search_term) |
                       Q(order__customer_name__icontains=search_term) | Q(picked_quantity__icontains=search_term) |
                       Q(order__marketplace__icontains=search_term) |
                       Q(order__original_order_id__icontains=search_term))

        elif order_term:
            order_data = lis[col_num]
            if order_term == 'desc':
                order_data = '-%s' % order_data
            master_data = Picklist.objects.exclude(order__original_order_id__in=excl_order_ids).filter(
                Q(order__sku_id__in=sku_master_ids) | \
                Q(stock__sku_id__in=sku_master_ids), **data_dict). \
                values('order__order_id', 'order__order_code', 'order__original_order_id', 'order__customer_id',
                       'order__customer_name','order__address', 'order__marketplace').distinct(). \
                annotate(total_picked=Sum('picked_quantity'), total_ordered=Sum('order__quantity')). \
                filter(**search_params).order_by(order_data)
        else:
            master_data = Picklist.objects.exclude(order__original_order_id__in=excl_order_ids).filter(
                Q(order__sku_id__in=sku_master_ids) | \
                Q(stock__sku_id__in=sku_master_ids), **data_dict). \
                values('order__order_id', 'order__order_code', 'order__original_order_id', 'order__customer_id',
                       'order__customer_name', 'order__address','order__marketplace').distinct(). \
                annotate(total_picked=Sum('picked_quantity'), total_ordered=Sum('order__quantity')). \
                filter(**search_params).order_by('updation_date')

        temp_data['recordsTotal'] = master_data.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']
        count = 0
        picklist = Picklist.objects.filter(**data_dict).exclude(order__status__in=[1, 3, 5])
        # tot_order_qtys = OrderDetail.objects.filter(user=user.id, quantity__gt=0).values_list('order_id', 'quantity')
        tot_order_qtys = dict(
            OrderDetail.objects.filter(user=user.id, quantity__gt=0).values_list('order_id').distinct().annotate(
                ordered=Sum('quantity')))
        all_seller_orders = SellerOrder.objects.filter(seller__user=user.id, order_status='DELIVERY_RESCHEDULED')
        # all_shipment_orders = ShipmentInfo.objects.filter(order__user=user.id)

        order_dates = dict(OrderDetail.objects.filter(id__in=master_data.values_list('order_id').distinct(), user=user.id). \
                           annotate(full_order=Concat('order_code', 'order_id', output_field=CharField())). \
                           values_list('full_order').distinct().annotate(date=Min('creation_date')))
        for data in master_data[start_index:stop_index]:
            data1 = copy.deepcopy(data)
            del data1['total_ordered']
            del data1['total_picked']
            # order_pick = picklist.filter(**data1).prefetch_related('order')
            creation_date = datetime.datetime.now()
            if order_dates.get(data['order__order_code'] + str(data['order__order_id']), ''):
                creation_date = order_dates[data['order__order_code'] + str(data['order__order_id'])]
            # if order_pick:
            #    creation_date = order_pick[0].creation_date
            #    data['total_picked'] = order_pick.aggregate(Sum('picked_quantity'))['picked_quantity__sum']
            creation_date = get_local_date(user, creation_date)
            order_id = data['order__original_order_id']
            address = ''
            address = data['order__address']
            if not order_id:
                order_id = data['order__order_code'] + str(data['order__order_id'])
                data['order__original_order_id'] = order_id

            # shipped = all_shipment_orders.filter(order_id__in=order_pick.values_list('order_id', flat=True)).\
            #                               aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
            # shipped = all_shipment_orders.filter(Q(order__order_id=data['order__order_id'], order__order_code=data['order__order_code']) |
            #                                     Q(order__original_order_id=data['order__original_order_id']),
            #                                     order__customer_id=data['order__customer_id'], order__customer_name=data['order__customer_name'],
            #                                     order__marketplace=data['order__marketplace']).aggregate(Sum('shipping_quantity'))\
            #                                     ['shipping_quantity__sum']

            seller_order = all_seller_orders.filter(order__order_id=data['order__order_id'])
            dis_quantity = 0
            if seller_order:
                dis_pick = picklist.filter(order__order_id=data['order__order_id'], status='dispatched')
                if dis_pick:
                    dis_quantity = dis_pick[0].order.quantity

            if ship.get(data['order__order_code'] + str(data['order__order_id']), 0):
                shipped = ship.get(data['order__order_code'] + str(data['order__order_id']), 0) - dis_quantity
                data['total_picked'] = float(data['total_picked']) - shipped
                if data['total_picked'] <= 0:
                    continue

            total_quantity = tot_order_qtys.get(data['order__order_id'], 0)
            temp_data['aaData'].append(OrderedDict((('Order ID', str(order_id)), ('id', count),
                                                    ('Customer ID', data['order__customer_id']),
                                                    ('Customer Name', data['order__customer_name']),
                                                    ('Marketplace', data['order__marketplace']),
                                                    ('Address',data['order__address']),
                                                    ('Picked Quantity', data['total_picked']),
                                                    ('Total Quantity', total_quantity), ('Order Date', creation_date),
                                                    ('DT_RowClass', 'results'), ('order_id', order_id))))
            count = count + 1
    log.info('Shipment info alternative view filtered ' + str(temp_data['recordsTotal']))


def fetch_relevant_orders_by_reseller(user_id, gen_ords):
    relevant_orders = {}
    for gen_ord in gen_ords:
        gen_id, cw_id, cid, ord_det_id = gen_ord[0]
        rem_ord_ids = GenericOrderDetailMapping.objects.filter(generic_order_id=gen_id, customer_id=cid).\
            exclude(orderdetail_id=ord_det_id).values_list('orderdetail_id', flat=True)
        if rem_ord_ids:
            relevant_orders.setdefault(ord_det_id, []).extend(list(rem_ord_ids))
    return relevant_orders


@get_admin_user
def get_invoice_details(request, user=''):
    gen_id = request.GET.get('gen_id', '')
    customer_id = request.GET.get('customer_id', '')
    if not (gen_id and customer_id):
        return HttpResponse('Generic Id or Customer Id is missing')
    gen_ord_objs = GenericOrderDetailMapping.objects.filter(customer_id=customer_id, generic_order_id=gen_id)
    gen_data_list = []
    for gen_ord_obj in gen_ord_objs:
        ord_id = OrderDetail.objects.get(id=gen_ord_obj.orderdetail_id)
        summary_ord_obj = ord_id.sellerordersummary_set
        summary_id_pick_num = ''
        picked_qty = 0
        if summary_ord_obj.values():
            sum_ord_vals = summary_ord_obj.values('order_id', 'pick_number')
            picked_qty_obj = sum_ord_vals.values('order_id', 'pick_number').annotate(picked_qty=Sum('quantity'))
            if picked_qty_obj:
                picked_qty = picked_qty_obj[0]['picked_qty']
            if sum_ord_vals:
                order_id = sum_ord_vals[0]['order_id']
                pick_num = sum_ord_vals[0]['pick_number']
                summary_id_pick_num = str(order_id) + ":" + str(pick_num)
        else:
            continue

        if not ord_id:
            continue
        order_id = ord_id.order_id
        qty = ord_id.quantity
        level_id = UserProfile.objects.get(user=gen_ord_obj.cust_wh_id).warehouse_level
        if user.id == gen_ord_obj.cust_wh_id:
            level_id = 0
        data_dict = OrderedDict((('Level ID', level_id),
                                 ('Order ID', order_id),
                                 ('id', str(summary_id_pick_num)),
                                 ('ord_det_id', ord_id.id),))
        data_dict.update(OrderedDict((('Order Quantity', qty),
                                      ('Picked Quantity', picked_qty),
                                      )))
        gen_data_list.append(data_dict)
    return HttpResponse(json.dumps({'data_dict': gen_data_list, 'status': 1}, cls=DjangoJSONEncoder))


def get_levelbased_invoice_data(start_index, stop_index, temp_data, user, search_term):
    filter_dict = {'user': user.id}
    if search_term:
        filter_dict['name__icontains'] = search_term
    reseller_objs = CustomerMaster.objects.filter(**filter_dict)
    reseller_ids = reseller_objs.values_list('id', flat=True)
    reseller_ords_map = {}
    total_ords = []
    ord_picked_qty_map = OrderedDict()
    org_order_map = OrderedDict()
    for reseller in reseller_ids:
        gen_ord_objs = GenericOrderDetailMapping.objects.filter(customer_id=reseller).order_by('-creation_date')
        gen_ord_vals = gen_ord_objs.values_list('generic_order_id', 'orderdetail')
        for gen_id, ord_det_id in gen_ord_vals:
            ord_det_obj = OrderDetail.objects.get(id=ord_det_id)
            org_order_id = ord_det_obj.order_id
            summary_ord_obj = ord_det_obj.sellerordersummary_set
            picked_qty = 0
            if summary_ord_obj:
                sum_ord_vals = summary_ord_obj.values('order__order_id', 'pick_number')
                picked_qty_obj = sum_ord_vals.values('order__order_id', 'pick_number').annotate(
                    picked_qty=Sum('quantity'))
                if picked_qty_obj:
                    picked_qty = picked_qty_obj[0]['picked_qty']
            else:
                continue
            total_ords.append(ord_det_id)
            reseller_ords_map.setdefault(reseller, OrderedDict()).setdefault(gen_id, []).append(ord_det_id)
            ord_picked_qty_map[ord_det_id] = picked_qty
            org_order_map[ord_det_id] = org_order_id
    temp_data['recordsTotal'] = len(total_ords)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for reseller, res_gen_ords in reseller_ords_map.items():
        for gen_id, res_ords in res_gen_ords.items():
            try:
                tot_picked_qty = 0
                original_order = ''
                for ord in res_ords:
                    tot_picked_qty += ord_picked_qty_map[ord]
                    if original_order:
                        original_order = original_order + ", " + str(org_order_map[ord])
                    else:
                        original_order = str(org_order_map[ord])
                orders = GenericOrderDetailMapping.objects.filter(orderdetail_id__in=res_ords)
                total_qty = orders.values('generic_order_id').annotate(total_qty=Sum('quantity'))[0]['total_qty']
                order_date = get_local_date(user, orders[0].creation_date)
                ordered_quantity = total_qty
                cust_name = CustomerMaster.objects.get(id=orders[0].customer_id).name
                data_dict = OrderedDict((('Gen Order Id', gen_id),
                                         ('Order Ids', original_order),
                                         ('check_field', 'Order ID'),
                                         ))
                data_dict.update(OrderedDict((('Customer Name', cust_name),
                                              ('Customer ID', orders[0].customer_id),
                                              ('Order Quantity', ordered_quantity),
                                              ('Picked Quantity', tot_picked_qty),
                                              ('Order Date&Time', order_date), ('Invoice Number', '')
                                              )))
                if not tot_picked_qty:
                    continue
                temp_data['aaData'].append(data_dict)
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info('Order Not found for user %s, order_det_id %s and error statement is %s'
                         % (str(user.username), str(res_ords), str(e)))
    temp_data['recordsTotal'] = len(temp_data['aaData'])
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data

@csrf_exempt
def get_stock_transfer_invoice_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    st_list=['order_id','order_id','order_id','quantity','order_id', 'order_id', 'order_id', 'stocktransfersummary__invoice_number','quantity']
    summary_params = {'status':2}
    users = [user.id]
    users = check_and_get_plants(request, users)
    user_ids = list(users.values_list('id', flat=True))
    summary_term = st_list[col_num]
    if order_term == 'desc':
        summary_term = '-%s' % summary_term
    if search_term :
        summary_params['order_id__icontains'] = search_term
    stock_transfer_summary = StockTransfer.objects.filter(sku__user__in=user_ids, st_type='ST_INTRA', **summary_params).select_related('st_po__open_st').order_by(summary_term)
    stock_transfer_summary_values = stock_transfer_summary.filter(storder__picklist__picked_quantity__gt=0).values('order_id', 'st_po__open_st__sku__user',
                                                'stocktransfersummary__full_invoice_number', 'stocktransfersummary__pick_number').\
                                                distinct()
    data_dict = StockTransferSummary.objects.filter(stock_transfer_id__in=stock_transfer_summary.filter(storder__picklist__picked_quantity__gt=0) \
                                                .values_list('id', flat=True)).values('stock_transfer__order_id', 'pick_number').distinct() \
                                                .annotate(total_sm=Sum(F('quantity')/F('picklist__stock__batch_detail__pcf')),
                                                amount=Sum((F('quantity')/F('picklist__stock__batch_detail__pcf')) * F('stock_transfer__st_po__open_st__price') + (F('quantity') * F('stock_transfer__st_po__open_st__price')/100) * (F('stock_transfer__st_po__open_st__igst_tax')+F('stock_transfer__st_po__open_st__cgst_tax')+F('stock_transfer__st_po__open_st__sgst_tax'))),
                                                grouping_key=Concat('stock_transfer__order_id', Value(':'), 'pick_number',output_field=CharField()))
    # import pdb; pdb.set_trace()
    qty_dict = dict(data_dict.values_list('grouping_key', 'total_sm'))
    amount_dict = dict(data_dict.values_list('grouping_key', 'amount'))
    temp_data['recordsTotal'] = stock_transfer_summary_values.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for stock_transfer in stock_transfer_summary_values[start_index:stop_index]:
        summary_price =0
        order_quantity = 0
        source_wh = ''
        current_material_tns = stock_transfer_summary.filter(order_id=stock_transfer['order_id'])
        if current_material_tns.exists():
            source_wh = current_material_tns[0].st_po.open_st.warehouse
            creation_date = current_material_tns.latest('creation_date').creation_date
            try:
                order_quantitys = current_material_tns.annotate(total_qty=Sum('original_quantity')).values('total_qty')
                for qty in order_quantitys:
                    order_quantity += float(qty['total_qty'])
            except Exception as e:
                order_quantity = 0
        group_key = "{}{}{}".format(str(stock_transfer['order_id']), ':', str(stock_transfer['stocktransfersummary__pick_number']))
        picked_quantity = qty_dict.get(group_key,0)
        summary_price = amount_dict.get(group_key,0)
        invoice_number = ''
        if stock_transfer['stocktransfersummary__full_invoice_number']:
            invoice_number = stock_transfer['stocktransfersummary__full_invoice_number']
        pick_number = ''
        if stock_transfer['stocktransfersummary__pick_number']:
            pick_number = stock_transfer['stocktransfersummary__pick_number']
        warehouse_name = User.objects.get(id=stock_transfer['st_po__open_st__sku__user'])
        data_dict = {'Stock Transfer ID': stock_transfer['order_id'], 'Order Quantity': order_quantity, 'Picked Quantity': round(picked_quantity, 2),
             'Total Amount': "%.2f"% float(summary_price), 'Stock Transfer Date&Time': get_local_date(user, creation_date),'Pick Receipt Number': pick_number,
             'Invoice Number': invoice_number, 'source_wh': source_wh.id, 'Source Warehouse': "%s %s" %(source_wh.first_name, source_wh.last_name), 'Destination Warehouse': "%s %s" %(warehouse_name.first_name, warehouse_name.last_name)}
        temp_data['aaData'].append(data_dict)
    return temp_data

@csrf_exempt
def get_stock_transfer_inter_invoice_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    st_list=['order_id','order_id','order_id','quantity','order_id','stocktransfersummary__invoice_number','quantity']
    summary_params = {'status':2}
    users = [user.id]
    users = check_and_get_plants(request, users)
    user_ids = list(users.values_list('id', flat=True))
    summary_term = st_list[col_num]
    if order_term == 'desc':
        summary_term = '-%s' % summary_term
    if search_term :
        summary_params['order_id__icontains'] = search_term
    stock_transfer_summary = StockTransfer.objects.filter(sku__user__in=user_ids, st_type='ST_INTER', **summary_params).select_related('st_po__open_st').order_by(summary_term)
    stock_transfer_summary_values = stock_transfer_summary.filter(storder__picklist__picked_quantity__gt=0).values('order_id', 'st_po__open_st__sku__user',
                                                'stocktransfersummary__full_invoice_number', 'stocktransfersummary__pick_number').\
                                                distinct()
    data_dict = StockTransferSummary.objects.filter(stock_transfer_id__in=stock_transfer_summary.filter(storder__picklist__picked_quantity__gt=0) \
                                                .values_list('id', flat=True)).values('stock_transfer__order_id', 'pick_number').distinct() \
                                                .annotate(total_sm=Sum(F('quantity')/F('picklist__stock__batch_detail__pcf')),
                                                amount=Sum(F('quantity') * F('stock_transfer__st_po__open_st__price') + (F('quantity') * F('stock_transfer__st_po__open_st__price')/100) * (F('stock_transfer__st_po__open_st__igst_tax')+F('stock_transfer__st_po__open_st__cgst_tax')+F('stock_transfer__st_po__open_st__sgst_tax'))),
                                                grouping_key=Concat('stock_transfer__order_id', Value(':'), 'pick_number',output_field=CharField()))
    qty_dict = dict(data_dict.values_list('grouping_key', 'total_sm'))
    amount_dict = dict(data_dict.values_list('grouping_key', 'amount'))
    temp_data['recordsTotal'] = stock_transfer_summary_values.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for stock_transfer in stock_transfer_summary_values[start_index:stop_index]:
        summary_price =0
        creation_date = stock_transfer_summary.filter(order_id=stock_transfer['order_id']).latest('creation_date').creation_date
        group_key = "{}{}{}".format(str(stock_transfer['order_id']), ':', str(stock_transfer['stocktransfersummary__pick_number']))
        picked_quantity = qty_dict.get(group_key,0)
        summary_price = amount_dict.get(group_key,0)
        invoice_number = ''
        if stock_transfer['stocktransfersummary__full_invoice_number']:
            invoice_number = stock_transfer['stocktransfersummary__full_invoice_number']
        pick_number = ''
        if stock_transfer['stocktransfersummary__pick_number']:
            pick_number = stock_transfer['stocktransfersummary__pick_number']
        warehouse_name = User.objects.get(id=stock_transfer['st_po__open_st__sku__user']).username
        data_dict = {'Sale Order ID': stock_transfer['order_id'], 'Order Quantity': 0, 'Picked Quantity': picked_quantity,
             'Total Amount': "%.2f"% float(summary_price), 'Sale Order Date&Time': get_local_date(user, creation_date),'pick_number': pick_number,
             'Invoice Number': invoice_number,#value['full_invoice_number'],
             'Warehouse Name': warehouse_name}
        temp_data['aaData'].append(data_dict)
    return temp_data

@csrf_exempt
def get_material_request_challan_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    st_list=['order_id','order_id','order_id','quantity','order_id','stocktransfersummary__invoice_number','quantity']
    summary_params = {'status':2}
    users = [user.id]
    users = check_and_get_plants(request, users)
    user_ids = list(users.values_list('id', flat=True))
    summary_term = st_list[col_num]
    if order_term == 'desc':
        summary_term = '-%s' % summary_term
    if search_term :
        summary_params['order_id__icontains'] = search_term
    stock_transfer_summary = StockTransfer.objects.filter(sku__user__in=user_ids, st_type='MR', **summary_params).select_related('st_po__open_st').order_by(summary_term)
    stock_transfer_summary_values = stock_transfer_summary.filter(storder__picklist__picked_quantity__gt=0).values('order_id', 'st_po__open_st__sku__user',
                                                'stocktransfersummary__full_invoice_number', 'stocktransfersummary__pick_number', ).\
                                                distinct()
    
    data_dict = StockTransferSummary.objects.filter(stock_transfer_id__in=stock_transfer_summary.filter(storder__picklist__picked_quantity__gt=0) \
                                                .values_list('id', flat=True)).values('stock_transfer__order_id', 'pick_number').distinct() \
                                                .annotate(total_sm=Sum(F('quantity')/F('picklist__stock__batch_detail__pcf')),
                                                amount=Sum(F('quantity') * F('stock_transfer__st_po__open_st__price') + (F('quantity') * F('stock_transfer__st_po__open_st__price')/100) * (F('stock_transfer__st_po__open_st__igst_tax')+F('stock_transfer__st_po__open_st__cgst_tax')+F('stock_transfer__st_po__open_st__sgst_tax'))),
                                                grouping_key=Concat('stock_transfer__order_id', Value(':'), 'pick_number',output_field=CharField()))
    qty_dict = dict(data_dict.values_list('grouping_key', 'total_sm'))
    amount_dict = dict(data_dict.values_list('grouping_key', 'amount'))
    temp_data['recordsTotal'] = stock_transfer_summary_values.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for stock_transfer in stock_transfer_summary_values[start_index:stop_index]:
        summary_price = 0
        order_quantity = 0
        current_material_tns = stock_transfer_summary.filter(order_id=stock_transfer['order_id'])
        if current_material_tns.exists():
            source_wh = current_material_tns[0].st_po.open_st.warehouse_id
            creation_date = current_material_tns.latest('creation_date').creation_date
            try:
                order_quantitys = current_material_tns.annotate(total_qty=Sum('quantity')).values('total_qty')
                for qty in order_quantitys:
                    order_quantity += float(qty['total_qty'])
            except Exception as e:
                order_quantity = 0
        group_key = "{}{}{}".format(str(stock_transfer['order_id']), ':', str(stock_transfer['stocktransfersummary__pick_number']))
        picked_quantity = qty_dict.get(group_key,0)
        summary_price = amount_dict.get(group_key,0)
        invoice_number = ''
        if stock_transfer['stocktransfersummary__full_invoice_number']:
            invoice_number = stock_transfer['stocktransfersummary__full_invoice_number']
        pick_number = ''
        if stock_transfer['stocktransfersummary__pick_number']:
            pick_number = stock_transfer['stocktransfersummary__pick_number']
        warehouse_name = User.objects.get(id=stock_transfer['st_po__open_st__sku__user'])
        data_dict = {'Material Request ID': stock_transfer['order_id'], 'Order Quantity': order_quantity, 'Picked Quantity': round(picked_quantity, 2),
             'Total Amount': "%.2f"% float(summary_price), 'Material Request Date&Time': get_local_date(user, creation_date),'pick_number': pick_number,
             'Invoice Number': invoice_number,#value['full_invoice_number'],
             'source_wh': source_wh,
             'Destination Department': "%s %s" %(warehouse_name.first_name, warehouse_name.last_name)}
        temp_data['aaData'].append(data_dict)
    return temp_data


@csrf_exempt
def get_picklist_delivery_challan(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['order_id','order_id','order_id','quantity','updation_date','quantity']
    order_by_term = 'order_id'
    if order_term == 'desc':
        order_by_term = '-'+lis[col_num]
    try :
        if search_term :
            temp_dc_objs = TempDeliveryChallan.objects.filter(Q(order__order_id__icontains=search_term)|Q(order__order_code__icontains=search_term)|Q(order__original_order_id__icontains=search_term)|Q(order__customer_name__icontains=search_term)|Q(dc_number=search_term)).filter(order__sku__user = user.id).values('order__order_id','order__order_code','order__original_order_id','order__customer_name','dc_number').distinct()
        else:
            temp_dc_objs = TempDeliveryChallan.objects.filter(order__sku__user = user.id).values('order__order_id','order__order_code','order__original_order_id','order__customer_name','dc_number').distinct()
        for dc in temp_dc_objs :
            if dc['order__original_order_id'] :
               order_id = dc['order__original_order_id']
            else:
               order_id = dc['order__order_code'] + dc['order__order_id']

            temp_data['aaData'].append({'Order ID' : order_id ,
                 'Customer Name': dc['order__customer_name'],'dc_number': dc['dc_number']})

        temp_data['recordsTotal'] = temp_dc_objs.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']

        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
        return temp_data


    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Exception raised for piclist delivery challan: %s" %str(e))




@csrf_exempt
def get_customer_invoice_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              filters):
    ''' Customer Invoice datatable code '''
    user_profile = UserProfile.objects.get(user_id=user.id)

    admin_user = get_priceband_admin_user(user)
    exclude_status = {'order_status_flag': 'cancelled'}
    if admin_user and user_profile.warehouse_type == 'DIST':
        temp_data = get_levelbased_invoice_data(start_index, stop_index, temp_data, user, search_term)
    else:
        if user_profile.user_type == 'marketplace_user':
            lis = ['seller_order__order__order_id', 'seller_order__order__order_id', 'seller_order__sor_id',
                   'seller_order__seller__seller_id', 'seller_order__order__original_order_id',
                   'seller_order__order__customer_name', 'quantity', 'quantity', 'date_only', 'id']
            user_filter = {'seller_order__seller__user': user.id}
            result_values = ['seller_order__order__order_id', 'seller_order__seller__name', 'pick_number',
                             'seller_order__sor_id', 'seller_order__order__original_order_id', 'delivered_flag']
            field_mapping = {'order_quantity_field': 'seller_order__quantity', 'date_only': 'seller_order__creation_date'}
            is_marketplace = True
        else:
            lis = ['order__order_id', 'order__order_id', 'order__customer_name', 'quantity', 'quantity', 'date_only',
                   'seller_order__order__original_order_id']
            user_filter = {'order__user': user.id}
            result_values = ['order__order_id', 'pick_number', 'order__original_order_id', 'delivered_flag']
            field_mapping = {'order_quantity_field': 'order__quantity', 'date_only': 'order__creation_date'}
            is_marketplace = False

        if search_term:
            if 'date_only' in lis:
                lis1 = copy.deepcopy(lis)
                lis1 = map(lambda x: x if x not in ['date_only', 'seller_order__order__order_id', 'order__order_id'] else
                field_mapping['date_only'], lis1)
            search_term = search_term.replace('(', '\(').replace(')', '\)')
            search_query = build_search_term_query(lis1, search_term)
            order_id_search = ''.join(re.findall('\d+', search_term))
            order_code_search = ''.join(re.findall('\D+', search_term))
            if not is_marketplace:
                master_data = SellerOrderSummary.objects.exclude(**exclude_status).filter(Q(order__order_id__icontains=order_id_search,
                                                                  order__order_code__icontains=order_code_search) |
                                                                Q(order__original_order_id__icontains=search_term) |
                                                                search_query, **user_filter). \
                    values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'),
                             total_order=Sum(field_mapping['order_quantity_field']))
            else:
                master_data = SellerOrderSummary.objects.exclude(**exclude_status).filter(Q(seller_order__order__order_id__icontains=order_id_search,
                                                                  seller_order__order__order_code__icontains=order_code_search) |
                                                                Q(
                                                                    seller_order__order__original_order_id__icontains=search_term) |
                                                                search_query, **user_filter).values(
                    *result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'),
                             total_order=Sum(field_mapping['order_quantity_field']))

        elif order_term:
            if order_term == 'asc' and (col_num or col_num == 0):
                master_data = SellerOrderSummary.objects.exclude(**exclude_status).filter(**user_filter).values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']),
                             date_only=Cast(field_mapping['date_only'], DateField())).order_by(lis[col_num])
            else:
                master_data = SellerOrderSummary.objects.exclude(**exclude_status).filter(**user_filter).values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']),
                             date_only=Cast(field_mapping['date_only'], DateField())).order_by('-%s' % lis[col_num])
        else:
            master_data = SellerOrderSummary.objects.exclude(**exclude_status).filter(**user_filter).order_by('-%s' % lis[col_num]).values(
                *result_values).distinct(). \
                annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']))

        temp_data['recordsTotal'] = master_data.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']

        order_summaries = SellerOrderSummary.objects.exclude(**exclude_status).filter(Q(seller_order__seller__user=user.id) |
                                                            Q(order__user=user.id))
        seller_orders = SellerOrder.objects.filter(seller__user=user.id)
        orders = OrderDetail.objects.filter(user=user.id)
        for data in master_data[start_index:stop_index]:
            if is_marketplace:
                summary = order_summaries.filter(seller_order__order__original_order_id=data['seller_order__order__original_order_id'],
                                                 seller_order__seller__name=data['seller_order__seller__name'])[0]
                order = summary.seller_order.order
                ordered_quantity = seller_orders.filter(order__order_id=data['seller_order__order__order_id'],
                                                        sor_id=data['seller_order__sor_id']).aggregate(Sum('quantity'))[
                    'quantity__sum']
                total_quantity = data['total_quantity']
                picked_amount = order_summaries.filter(seller_order__order__original_order_id=\
                                               data['seller_order__order__original_order_id'])\
                                               .values('order__sku_id', 'order__invoice_amount', 'order__quantity', 'delivered_flag').distinct()\
                                               .annotate(pic_qty=Sum('quantity'))\
                                               .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                               .aggregate(Sum('cur_amt'))['cur_amt__sum']
            else:
                order = orders.filter(original_order_id=data['order__original_order_id'])[0]
                invoice_number = order.sellerordersummary_set.values_list('invoice_number', flat=True)
                if invoice_number:
                    invoice_number = invoice_number[0]
                else:
                    invoice_number = ''
                #ordered_quantity = orders.filter(original_order_id=data['order__original_order_id'])\
                #                         .aggregate(Sum('original_quantity'))['original_quantity__sum']
                ordered_quantity = orders.filter(original_order_id=data['order__original_order_id']) \
                                    .aggregate(order_qty=Sum(Case(
                                        When(status=3, then=(F('original_quantity')-F('quantity'))),
                                        default=F('original_quantity')
                                             )))['order_qty']
                picked_amount = order_summaries.filter(order__original_order_id=data['order__original_order_id'])\
                                               .values('order__sku_id', 'order__invoice_amount', 'order__quantity', 'delivered_flag')\
                                               .distinct().annotate(pic_qty=Sum('quantity'))\
                                               .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                               .aggregate(Sum('cur_amt'))['cur_amt__sum']
            order_id = order.order_code + str(order.order_id)

            if str(data['delivered_flag']) == '0':
                delivered_status = "Not Delivered"
            elif str(data['delivered_flag']) == '1':
                delivered_status = "Delivered"
            elif str(data['delivered_flag']) == '2':
                delivered_status = "Ratings Updated"

            if order.original_order_id:
                order_id = order.original_order_id

            if not ordered_quantity:
                ordered_quantity = 0

            order_date = get_local_date(user, order.creation_date)

            if is_marketplace:
                data_dict = OrderedDict((('UOR ID', order_id), ('SOR ID', summary.seller_order.sor_id),
                                         ('Seller ID', summary.seller_order.seller.seller_id),
                                         ('id', str(data['seller_order__order__order_id']) + \
                                          ":" + str(data['pick_number']) + ":" + data['seller_order__seller__name']),
                                         ('check_field', 'SOR ID')
                                         ))
            else:
                data_dict = OrderedDict((("Invoice ID", invoice_number), ('Order ID', order_id),
                                         ('id', str(data['order__order_id']) + ":" + str(data['pick_number'])),
                                         ('check_field', 'Order ID')))
            data_dict.update(OrderedDict((('Customer Name', order.customer_name),
                                          ('Order Quantity', ordered_quantity), ('Picked Quantity', data['total_quantity']),
                                          ('Invoice Amount', picked_amount), ('Delivered Flag', delivered_status),
                                          ('Order Date&Time', order_date), ('Invoice Number', '')
                                          )))
            temp_data['aaData'].append(data_dict)
        log.info('Customer Invoice filtered %s for %s ' % (str(temp_data['recordsTotal']), user.username))


@csrf_exempt
def get_customer_invoice_tab_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              filters):
    ''' Customer Invoice datatable code '''

    user_profile = UserProfile.objects.get(user_id=user.id)
    admin_user = get_priceband_admin_user(user)
    user_filter = {}
    user_filter['order_status_flag'] = 'customer_invoices'
    if filters.get('cancel_invoice',0):
        user_filter['order_status_flag'] = 'cancelled'
    if admin_user and user_profile.warehouse_type == 'DIST':
        temp_data = get_levelbased_invoice_data(start_index, stop_index, temp_data, user, search_term)
    else:
        if user_profile.user_type == 'marketplace_user':
            lis = ['seller_order__order__original_order_id', 'seller_order__order__order_id', 'seller_order__sor_id',
                   'seller_order__seller__seller_id', 'seller_order__order__customer_name', 'quantity', 'quantity',
                   'quantity', 'date_only', 'invoice_number','invoice_number','invoice_number']
            user_filter['seller_order__seller__user']= user.id
            result_values = ['invoice_number', 'full_invoice_number', 'seller_order__seller__name',
                             'seller_order__sor_id', 'financial_year', 'seller_order__order__customer_name']
            field_mapping = {'order_quantity_field': 'seller_order__quantity',
                             'date_only': 'seller_order__order__creation_date'}
            is_marketplace = True
        else:
            lis = ['invoice_number', 'invoice_number', 'financial_year', 'order__customer_name', 'invoice_number', 'invoice_number',
                   'date_only', 'invoice_number', 'invoice_number','invoice_number','invoice_number']
            user_filter['order__user'] = user.id
            result_values = ['invoice_number', 'full_invoice_number', 'financial_year', 'order__customer_name', 'order__marketplace']
            field_mapping = {'order_quantity_field': 'order__quantity', 'date_only': 'creation_date'}
            is_marketplace = False

        if search_term:
            #if 'date_only' in lis:
                #lis1 = copy.deepcopy(lis)
                #lis1 = map(lambda x: x if x not in ['date_only', 'seller_order__order__order_id', 'order__order_id'] else
                #field_mapping['date_only'], lis1)
            search_term = search_term.replace('(', '\(').replace(')', '\)')
            search_query = build_search_term_query(list(set(lis)), search_term)
            order_id_search = ''.join(re.findall('\d+', search_term))
            order_code_search = ''.join(re.findall('\D+', search_term))
            if not is_marketplace:
                master_data = SellerOrderSummary.objects.filter(**user_filter). \
                    values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'),
                             ordered_quantity=Sum(field_mapping['order_quantity_field'], distinct=True),
                             date_only=Cast(field_mapping['date_only'], DateField())).\
                    filter(Q(full_invoice_number__icontains=search_term)|search_query)
            else:
                master_data = SellerOrderSummary.objects.filter(**user_filter).values(
                    *result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'),
                             ordered_quantity=Sum(field_mapping['order_quantity_field'], distinct=True),
                             date_only=Cast(field_mapping['date_only'], DateField())).\
                        filter(Q(full_invoice_number__icontains=search_term)|
                                                                search_query)

        elif order_term:
            if order_term == 'asc' and (col_num or col_num == 0):
                master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'),\
                             ordered_quantity=Sum(field_mapping['order_quantity_field'], distinct=True),
                             date_only=Cast(field_mapping['date_only'], DateField())).order_by(lis[col_num])
            else:
                master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'),\
                             ordered_quantity=Sum(field_mapping['order_quantity_field'], distinct=True),
                             date_only=Cast(field_mapping['date_only'], DateField())).order_by('-%s' % lis[col_num])
        else:
            master_data = SellerOrderSummary.objects.filter(**user_filter).order_by('-%s' % lis[col_num]).values(
                *result_values).distinct(). \
                annotate(total_quantity=Sum('quantity'), ordered_quantity=Sum(field_mapping['order_quantity_field'], distinct=True),
                         date_only=Cast(field_mapping['date_only'], DateField()))

        temp_data['recordsTotal'] = master_data.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']

        order_summaries = SellerOrderSummary.objects.filter(Q(seller_order__seller__user=user.id) |
                                                            Q(order__user=user.id))
        if is_marketplace:
            seller_orders = dict(SellerOrder.objects.filter(id__in=master_data.values_list('seller_order_id', flat=True)).\
                            values_list('sor_id').distinct().annotate(tsum=Sum('quantity')))
        #else:
        #    orders = dict(OrderDetail.objects.filter(id__in=master_data.values_list('order_id', flat=True)). \
        #                  values_list('original_order_id').distinct().annotate(tsum=Sum('quantity')))
        for data in master_data[start_index:stop_index]:
            invoice_amount = 0
            picked_amount = 0
            tax_amount = 0
            invoice_date = ''
            total_inv_dict = {}
            if is_marketplace:
                summary = order_summaries.filter(invoice_number=data['invoice_number'],
                                                 seller_order__seller__name=data['seller_order__seller__name'])[0]
                order = summary.seller_order.order
                #ordered_quantity = seller_orders.filter(order__order_id=data['seller_order__order__order_id'],
                                                        #sor_id=data['seller_order__sor_id']).aggregate(Sum('quantity'))[
                    #'quantity__sum']
                total_quantity = data['total_quantity']
                picked_amount = order_summaries.filter(invoice_number=data['invoice_number'],
                                                       financial_year=data['financial_year'])\
                                                       .values('seller_order__order__sku_id',
                                                       'seller_order__order__invoice_amount',
                                                       'seller_order__order__original_quantity').distinct()\
                                               .annotate(pic_qty=Sum('quantity'))\
                                               .annotate(cur_amt=(F('seller_order__order__invoice_amount')/F('seller_order__order__original_quantity'))* F('pic_qty'))\
                                               .aggregate(Sum('cur_amt'))['cur_amt__sum']
                data['ordered_quantity'] = seller_orders.get(data['seller_order__sor_id'], 0)
            else:
                seller_order_summaries = order_summaries.filter(invoice_number=data['invoice_number'],
                                                                financial_year=data['financial_year'], order__marketplace=data['order__marketplace'])
                order_ids = seller_order_summaries.values_list('order__id', flat= True)
                picked_dict = seller_order_summaries.annotate(pic_qty=Sum('quantity'))\
                                .values_list('order__id','pic_qty')
                invoice_dict = OrderDetail.objects.filter(id__in=order_ids)\
                                                  .annotate(cur_amt=((F('unit_price')* F('original_quantity'))-F('customerordersummary__discount')))\
                                                  .annotate(tax_amt=((F('cur_amt')*(F('customerordersummary__cgst_tax')+F('customerordersummary__sgst_tax')+F('customerordersummary__igst_tax'))*0.01)))\
                                                  .values('tax_amt','cur_amt','id','original_quantity')
                for obj in invoice_dict:
                    order_id=obj.get('id')
                    total_inv_dict[order_id]=obj
                for value in picked_dict:
                    if value:
                        invoice_amount+=(total_inv_dict[value[0]].get('cur_amt',0)*(value[1]/total_inv_dict[value[0]].get('original_quantity',1)))
                        tax_amount +=(total_inv_dict[value[0]].get('tax_amt',0)*(value[1]/total_inv_dict[value[0]].get('original_quantity',1)))
                        picked_amount =invoice_amount+tax_amount
                order = seller_order_summaries[0].order
                original_order_id = order.original_order_id
                #invoice_date = seller_order_summaries[0].order.customerordersummary_set.filter()[0].invoice_date
                #invoice_date = CustomerOrderSummary.objects.filter(order_id__in=order_ids)\
                #                                   .order_by('-invoice_date').values_list('invoice_date', flat=True)[0]
                #if not invoice_date:
                invoice_date = seller_order_summaries[0].creation_date
                data['ordered_quantity'] = OrderDetail.objects.filter(user=user.id, original_order_id=original_order_id).\
						only('original_quantity').aggregate(Sum('original_quantity'))['original_quantity__sum']

                if not data['ordered_quantity']:
                    data['ordered_quantity'] = 0

            order_date = get_local_date(user, order.creation_date)
            invoice_date = invoice_date.strftime("%d %b %Y") if invoice_date else order.creation_date.strftime("%d %b %Y")
            if is_marketplace:
                data_dict = OrderedDict((("Invoice ID", data['full_invoice_number']), ('UOR ID', order_id), ('SOR ID', summary.seller_order.sor_id),
                                         ('Seller ID', summary.seller_order.seller.seller_id),
                                         ('id', str(data['invoice_number']) + \
                                          ":" + str(data.get('pick_number', '')) + ":" + data['seller_order__seller__name'] + \
                                           ':' + data['financial_year']),
                                         ('check_field', 'SOR ID')
                                         ))
                customer_name = data['seller_order__order__customer__name']
            else:
                data_dict = OrderedDict((("Invoice ID", data['full_invoice_number']), ('Order ID', order_id),
                                         ('id', str(data['invoice_number']) + ":" + str(data.get('pick_number', '')) + ':' + data['financial_year']),
                                         ('check_field', 'Order ID'),('Invoice Amount(w/o tax)', "%.2f" %invoice_amount),('Tax Amount', "%.2f" %tax_amount)))
                customer_name = data['order__customer_name']
            data_dict.update(OrderedDict((('Financial Year', data['financial_year']), ('Customer Name', customer_name),
                                          ('Order Quantity', data['ordered_quantity']), ('Picked Quantity', data['total_quantity']),
                                          ('Total Amount', round(picked_amount,2)),
                                          ('Invoice Date&Time', invoice_date), ('Invoice Number', ''), ('Marketplace', order.marketplace)
                                          )))
            temp_data['aaData'].append(data_dict)
        log.info('Customer Invoice filtered %s for %s ' % (str(temp_data['recordsTotal']), user.username))


@csrf_exempt
def get_processed_orders_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              filters):
    ''' Customer Invoice datatable code '''

    user_profile = UserProfile.objects.get(user_id=user.id)
    admin_user = get_priceband_admin_user(user)
    if admin_user and user_profile.warehouse_type == 'DIST':
        temp_data = get_levelbased_invoice_data(start_index, stop_index, temp_data, user, search_term)
    else:
        if user_profile.user_type == 'marketplace_user':
            lis = ['seller_order__order__order_id', 'seller_order__order__order_id', 'seller_order__sor_id',
                   'seller_order__seller__seller_id',
                   'seller_order__order__customer_name', 'quantity', 'quantity', 'date_only', 'id']
            user_filter = {'seller_order__seller__user': user.id, 'order_status_flag': 'processed_orders'}
            result_values = ['seller_order__order__order_id', 'seller_order__seller__name', 'pick_number',
                             'seller_order__sor_id', 'seller_order__order__original_order_id']
            field_mapping = {'order_quantity_field': 'seller_order__quantity', 'date_only': 'seller_order__creation_date'}
            is_marketplace = True
        else:
            lis = ['order__order_id', 'order__order_id', 'order__customer_name', 'quantity', 'quantity', 'date_only']
            user_filter = {'order__user': user.id, 'order_status_flag': 'processed_orders'}
            result_values = ['order__order_id', 'pick_number', 'order__original_order_id', 'creation_date']
            field_mapping = {'order_quantity_field': 'order__quantity', 'date_only': 'order__creation_date'}
            is_marketplace = False

        if search_term:
            if 'date_only' in lis:
                lis1 = copy.deepcopy(lis)
                lis1 = map(lambda x: x if x not in ['date_only', 'seller_order__order__order_id', 'order__order_id'] else
                field_mapping['date_only'], lis1)
            search_term = search_term.replace('(', '\(').replace(')', '\)')
            search_query = build_search_term_query(lis1, search_term)
            order_id_search = ''.join(re.findall('\d+', search_term))
            order_code_search = ''.join(re.findall('\D+', search_term))
            if not is_marketplace:
                master_data = SellerOrderSummary.objects.filter(Q(order__order_id__icontains=order_id_search,
                                                                  order__order_code__icontains=order_code_search) |
                                                                Q(order__original_order_id__icontains=search_term) |
                                                                Q(order__marketplace__icontains=search_term) |
                                                                search_query, **user_filter). \
                    values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'),
                             total_order=Sum(field_mapping['order_quantity_field']))
            else:
                master_data = SellerOrderSummary.objects.filter(Q(seller_order__order__order_id__icontains=order_id_search,
                                                                  seller_order__order__order_code__icontains=order_code_search) |
                                                                Q(
                                                                    seller_order__order__original_order_id__icontains=search_term) |
                                                                search_query, **user_filter).values(
                    *result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'),
                             total_order=Sum(field_mapping['order_quantity_field']))

        elif order_term:
            if order_term == 'asc' and (col_num or col_num == 0):
                master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']),
                             date_only=Cast(field_mapping['date_only'], DateField())).order_by(lis[col_num])
            else:
                master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']),
                             date_only=Cast(field_mapping['date_only'], DateField())).order_by('-%s' % lis[col_num])
        else:
            master_data = SellerOrderSummary.objects.filter(**user_filter).order_by('-%s' % lis[col_num]).values(
                *result_values).distinct(). \
                annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']))

        temp_data['recordsTotal'] = master_data.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']

        order_summaries = SellerOrderSummary.objects.filter(Q(seller_order__seller__user=user.id) |
                                                            Q(order__user=user.id))
        if is_marketplace:
            seller_orders = dict(SellerOrder.objects.filter(id__in=master_data.values_list('seller_order_id', flat=True)).\
                            values_list('sor_id').distinct().annotate(tsum=Sum('quantity')))
        else:
            orders = dict(OrderDetail.objects.filter(user=user.id). \
                          values_list('original_order_id').distinct().annotate(tsum=Sum('original_quantity')))
        for data in master_data[start_index:stop_index]:
            #order_summaries.filter
            if is_marketplace:
                summary = order_summaries.filter(seller_order__order__order_id=data['seller_order__order__order_id'],
                                                 seller_order__seller__name=data['seller_order__seller__name'])[0]
                order = summary.seller_order.order
                ordered_quantity = seller_orders.get(data['seller_order__sor_id'], 0)
                total_quantity = data['total_quantity']
                picked_amount = order_summaries.filter(seller_order__order__original_order_id=data['seller_order__order__original_order_id'])\
                                            .values('seller_order__order__sku_id',
                                                    'seller_order__order__invoice_amount',
                                                    'seller_order__order__quantity').distinct()\
                                            .annotate(pic_qty=Sum('quantity'))\
                                            .annotate(cur_amt=(F('seller_order__order__invoice_amount')/F('seller_order__order__quantity'))* F('pic_qty'))\
                                            .aggregate(Sum('cur_amt'))['cur_amt__sum']
            else:
                order = OrderDetail.objects.filter(original_order_id=data['order__original_order_id'], user=user.id)[0]
                ordered_quantity = orders.get(data['order__original_order_id'], 0)
                picked_amount = order_summaries.filter(order__original_order_id=data['order__original_order_id'], creation_date=data['creation_date'])\
                                .values('order__sku_id', 'order__invoice_amount', 'order__quantity')\
                                .distinct().annotate(pic_qty=Sum('quantity'))\
                                .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                .aggregate(Sum('cur_amt'))['cur_amt__sum']
            if not picked_amount:
                picked_amount = 0
            order_id = order.order_code + str(order.order_id)
            if order.original_order_id:
                order_id = order.original_order_id

            if not ordered_quantity:
                ordered_quantity = 0

            order_date = get_local_date(user, order.creation_date)

            if is_marketplace:
                data_dict = OrderedDict((('UOR ID', order_id), ('SOR ID', summary.seller_order.sor_id),
                                         ('Seller ID', summary.seller_order.seller.seller_id),
                                         ('id', str(data['seller_order__order__order_id']) + \
                                          ":" + str(data['pick_number']) + ":" + data['seller_order__seller__name']),
                                         ('check_field', 'SOR ID')
                                         ))
            else:
                data_dict = OrderedDict((('Order ID', order_id),
                                         ('id', str(data['order__order_id']) + ":" + str(data['pick_number'])),
                                         ('check_field', 'Order ID')))
            data_dict.update(OrderedDict((('Customer Name', order.customer_name),
                                          ('Order Quantity', ordered_quantity), ('Invoice Amount', round(picked_amount, 2)),
                                          ('Picked Quantity', data['total_quantity']),
                                          ('Order Date&Time', order_date), ('Invoice Number', ''), ('Marketplace', order.marketplace)
                                          )))
            temp_data['aaData'].append(data_dict)
        log.info('Customer Invoice filtered %s for %s ' % (str(temp_data['recordsTotal']), user.username))


@csrf_exempt
def get_delivery_challans_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                              filters):
    ''' Customer Invoice datatable code '''

    user_profile = UserProfile.objects.get(user_id=user.id)
    admin_user = get_priceband_admin_user(user)
    if admin_user and user_profile.warehouse_type == 'DIST':
        temp_data = get_levelbased_invoice_data(start_index, stop_index, temp_data, user, search_term)
    else:
        if user_profile.user_type == 'marketplace_user':
            lis = ['seller_order__order__order_id', 'seller_order__order__order_id', 'seller_order__sor_id',
                   'seller_order__seller__seller_id', 'seller_order__order__original_order_id',
                   'seller_order__order__customer_name', 'quantity', 'quantity', 'date_only', 'id']
            user_filter = {'seller_order__seller__user': user.id}
            result_values = ['seller_order__order__order_id', 'seller_order__seller__name', 'pick_number',
                             'seller_order__sor_id', 'seller_order__order__order_id',
                             'seller_order__order__original_order_id', 'challan_number']
            field_mapping = {'order_quantity_field': 'seller_order__quantity', 'date_only': 'seller_order__creation_date'}
            is_marketplace = True
        else:
            lis = ['order__order_id', 'order__order_id', 'order__customer_name', 'quantity', 'quantity',
                   'order__original_order_id', 'date_only']
            user_filter = {'order__user': user.id, 'order_status_flag': 'delivery_challans'}
            result_values = ['order__order_id', 'pick_number', 'challan_number', 'order__original_order_id']
            field_mapping = {'order_quantity_field': 'order__quantity', 'date_only': 'order__creation_date'}
            is_marketplace = False

        if search_term:
            if 'date_only' in lis:
                lis1 = copy.deepcopy(lis)
                lis1 = map(lambda x: x if x not in ['date_only', 'seller_order__order__order_id', 'order__order_id'] else
                field_mapping['date_only'], lis1)
            search_term = search_term.replace('(', '\(').replace(')', '\)')
            search_query = build_search_term_query(lis1, search_term)
            order_id_search = ''.join(re.findall('\d+', search_term))
            order_code_search = ''.join(re.findall('\D+', search_term))
            if not is_marketplace:
                master_data = SellerOrderSummary.objects.filter(Q(order__order_id__icontains=order_id_search,
                                                                  order__order_code__icontains=order_code_search) |
                                                                Q(order__original_order_id__icontains=search_term) |
                                                                search_query, **user_filter). \
                    values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'),
                             total_order=Sum(field_mapping['order_quantity_field']))
            else:
                master_data = SellerOrderSummary.objects.filter(Q(seller_order__order__order_id__icontains=order_id_search,
                                                                  seller_order__order__order_code__icontains=order_code_search) |
                                                                Q(
                                                                    seller_order__order__original_order_id__icontains=search_term) |
                                                                search_query, **user_filter).values(
                    *result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'),
                             total_order=Sum(field_mapping['order_quantity_field']))

        elif order_term:
            if order_term == 'asc' and (col_num or col_num == 0):
                master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']),
                             date_only=Cast(field_mapping['date_only'], DateField())).order_by(lis[col_num])
            else:
                master_data = SellerOrderSummary.objects.filter(**user_filter).values(*result_values).distinct(). \
                    annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']),
                             date_only=Cast(field_mapping['date_only'], DateField())).order_by('-%s' % lis[col_num])
        else:
            master_data = SellerOrderSummary.objects.filter(**user_filter).order_by('-%s' % lis[col_num]).values(
                *result_values).distinct(). \
                annotate(total_quantity=Sum('quantity'), total_order=Sum(field_mapping['order_quantity_field']))

        temp_data['recordsTotal'] = master_data.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']

        order_summaries = SellerOrderSummary.objects.filter(Q(seller_order__seller__user=user.id) |
                                                            Q(order__user=user.id))
        seller_orders = SellerOrder.objects.filter(seller__user=user.id)
        orders = OrderDetail.objects.filter(user=user.id)
        for data in master_data[start_index:stop_index]:
            if is_marketplace:
                summary = order_summaries.filter(seller_order__order__order_id=data['seller_order__order__order_id'],
                                                 seller_order__seller__name=data['seller_order__seller__name'])[0]
                order = summary.seller_order.order
                ordered_quantity = seller_orders.filter(order__order_id=data['seller_order__order__order_id'],
                                                        sor_id=data['seller_order__sor_id']).aggregate(Sum('quantity'))[
                    'quantity__sum']
                total_quantity = data['total_quantity']
                picked_amount = order_summaries.filter(order__original_order_id=data['seller_order__order__original_order_id'])\
                                               .values('order__sku_id', 'order__invoice_amount', 'order__quantity').distinct()\
                                               .annotate(pic_qty=Sum('quantity'))\
                                               .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                               .aggregate(Sum('cur_amt'))['cur_amt__sum']
            else:
                order = orders.filter(original_order_id=data['order__original_order_id'])[0]
                ordered_quantity = orders.filter(original_order_id=data['order__original_order_id']).aggregate(Sum('quantity'))[
                    'quantity__sum']
                picked_amount = order_summaries.filter(order__original_order_id=data['order__original_order_id'])\
                                               .values('order__sku_id', 'order__invoice_amount', 'order__quantity')\
                                               .distinct().annotate(pic_qty=Sum('quantity'))\
                                               .annotate(cur_amt=(F('order__invoice_amount')/F('order__quantity'))* F('pic_qty'))\
                                               .aggregate(Sum('cur_amt'))['cur_amt__sum']
            if not picked_amount:
                picked_amount = 0
            order_id = order.order_code + str(order.order_id)
            if order.original_order_id:
                order_id = order.original_order_id

            if not ordered_quantity:
                ordered_quantity = 0

            order_date = get_local_date(user, order.creation_date)

            if is_marketplace:
                data_dict = OrderedDict((('Challan ID', data['challan_number']), ('UOR ID', order_id),
                                         ('SOR ID', summary.seller_order.sor_id),
                                         ('Seller ID', summary.seller_order.seller.seller_id),
                                         ('id', str(data['seller_order__order__order_id']) + \
                                          ":" + str(data['pick_number']) + ":" + data['seller_order__seller__name']),
                                         ('check_field', 'SOR ID')
                                         ))
            else:
                data_dict = OrderedDict((('Challan ID', data['challan_number']), ('Order ID', order_id),
                                         ('id', str(data['order__order_id']) + ":" + str(data['pick_number'])),
                                         ('check_field', 'Customer Name')))
            data_dict.update(OrderedDict((('Customer Name', order.customer_name),
                                          ('Order Quantity', ordered_quantity), ('Picked Quantity', data['total_quantity']),
                                          ('Invoice Amount', round(picked_amount, 2)), ('Order Date&Time', order_date),
                                          ('Invoice Number', '')
                                          )))
            temp_data['aaData'].append(data_dict)
        log.info('Customer Invoice filtered %s for %s ' % (str(temp_data['recordsTotal']), user.username))

@get_admin_user
def update_dc(request, user=''):
    form_dict = dict(request.POST.iterlists())
    address = form_dict['form_data[address]'][0]
    challan_number = form_dict['form_data[challan_no]'][0]
    rep_id = form_dict['form_data[rep]']
    lr_no = form_dict['form_data[lr_no]']
    carrier = form_dict['form_data[carrier]']
    sku_id = form_dict['form_data[wms_code]']
    pkgs = form_dict['form_data[pkgs]']
    terms = form_dict['form_data[terms]']
    skus_data = form_dict['data']
    order_id = form_dict['form_data[order_no]'][0]
    pick_number = form_dict['form_data[pick_number]'][0]
    cm_id = form_dict['form_data[customer_id]'][0]
    req_data = eval(request.POST.get("data"))
    if req_data:
        original_order_id = req_data[0]["order_id"]
    if not cm_id:
        log.info("No Customer Master Id found")
        return HttpResponse(json.dumps({'message': 'failed'}))
    else:
        cm_obj = CustomerMaster.objects.filter(id=cm_id)
        if not cm_obj:
            log.info('No Proper Customer Object')
            return HttpResponse(json.dumps({'message': 'failed'}))
        else:
            cm_obj = cm_obj[0]
        customer_id = cm_obj.customer_id
        customer_name = cm_obj.name
        price_type = cm_obj.price_type
        tax_type = cm_obj.tax_type
    for sku_data in skus_data:
        sku_data = eval(sku_data)
        shipment_date = sku_data[0].get('shipment_date', '')
        for each_sku in sku_data:
            ord_det_id = each_sku.get('id', '')
            quantity = each_sku.get('quantity', '')
            unit_price = each_sku.get('unit_price', '')
            sgst_tax = each_sku['taxes'].get('sgst_tax', '')
            cgst_tax = each_sku['taxes'].get('cgst_tax', '')
            igst_tax = each_sku['taxes'].get('igst_tax', '')
            invoice_amount = each_sku.get('invoice_amount', '')

            if not int(quantity):
                if ord_det_id:
                    ord_obj = OrderDetail.objects.filter(id=ord_det_id)
                    if ord_obj:
                        ord_obj = ord_obj[0]
                        original_order_id = ord_obj.original_order_id
                        cust_objs = CustomerOrderSummary.objects.filter(order__id=ord_obj.id)
                        if cust_objs:
                            cust_obj = cust_objs[0]
                            cust_obj.delete()
                        sos_obj = SellerOrderSummary.objects.filter(order_id=ord_obj)
                        if sos_obj:
                            sos_obj = sos_obj[0]
                            sos_obj.delete()
                        ord_obj.delete()
                continue
            if ord_det_id:
                ord_obj = OrderDetail.objects.filter(id=ord_det_id)
                if ord_obj:
                    original_order_id = ord_obj[0].original_order_id
                    ord_obj[0].quantity = int(quantity)
                    ord_obj[0].invoice_amount = invoice_amount
                    ord_obj[0].unit_price = unit_price
                    cust_order_summary = CustomerOrderSummary.objects.filter(order_id = ord_obj[0].id)
                    if cust_order_summary:
                        if cgst_tax:
                            cust_order_summary[0].cgst_tax = cgst_tax
                        if sgst_tax:
                            cust_order_summary[0].sgst_tax = sgst_tax
                        if igst_tax:
                            cust_order_summary[0].igst_tax = igst_tax
                        cust_order_summary[0].save()

                    ord_obj[0].save()
            else:
                sku_qs = SKUMaster.objects.filter(sku_code=each_sku['sku_code'], user=user.id)
                if not sku_qs:
                    continue
                else:
                    sku_id = sku_qs[0].id
                    title = sku_qs[0].sku_desc
                    product_type = sku_qs[0].product_type
                    """price_master_obj = PriceMaster.objects.filter(price_type=price_type, sku__id=sku_id)
                    if price_master_obj:
                        price_master_obj = price_master_obj[0]
                        price = price_master_obj.price
                    else:
                        price = sku_qs[0].price
                    net_amount = price * int(quantity)"""
                    order_detail_dict = {'sku_id': sku_id, 'title': title, 'quantity': quantity,
                                         'order_id': order_id, 'original_order_id': original_order_id, 'user': user.id,
                                         'customer_id': customer_id, 'customer_name': customer_name,
                                         'shipment_date': shipment_date, 'address': address, 'price': unit_price,
                                         'unit_price': unit_price, 'creation_date': ord_obj[0].creation_date}
                    #tax = get_tax_value(user, order_detail_dict, product_type, tax_type)
                    #total_amount = ((net_amount * tax) / 100) + net_amount
                    order_detail_dict['invoice_amount'] = invoice_amount #total_amount
                    order_detail_dict.pop('price')
                    ord_obj = OrderDetail(**order_detail_dict)
                    ord_obj.save()
                    cos_dict = {'order_id': ord_obj.id, 'cgst_tax': cgst_tax,
                                'igst_tax': igst_tax, 'sgst_tax': sgst_tax
                                }
                    cos_obj = CustomerOrderSummary(**cos_dict)
                    cos_obj.save()
                    sos_dict = {'quantity': quantity, 'pick_number': pick_number,
                                'creation_date': datetime.datetime.now(), 'order_id': ord_obj.id,
                                'challan_number': challan_number, 'order_status_flag': 'delivery_challans'}
                    sos_obj = SellerOrderSummary(**sos_dict)
                    sos_obj.save()

    return HttpResponse(json.dumps({'message': 'success'}))


def construct_sell_ids(request, user, status_flag='processed_orders', cancel_inv=False):
    data_dict = dict(request.GET.iterlists())
    seller_summary_dat = data_dict.get('seller_summary_id', '')
    seller_summary_dat = seller_summary_dat[0]
    seller_summary_dat = seller_summary_dat.split('<<>>')
    if user.userprofile.user_type == 'marketplace_user':
        sell_ids = {'seller_order__order__user': user.id}
        field_mapping = {'sku_code': 'seller_order__order__sku__sku_code', 'order_id': 'seller_order__order_id',
                         'order_id_in': 'seller_order__order__order_id__in'}
    else:
        sell_ids = {'order__user': user.id}
        field_mapping = {'sku_code': 'order__sku__sku_code', 'order_id': 'order_id', 'order_id_in': 'order__order_id__in'}

    if cancel_inv:
        del field_mapping['order_id_in']
        field_mapping['full_invoice_number_in'] = 'full_invoice_number__in'
    for data_id in seller_summary_dat:
        splitted_data = data_id.split(':')
        common_id = 'full_invoice_number_in' if cancel_inv else 'order_id_in'
        sell_ids.setdefault(field_mapping[common_id], [])
        sell_ids[field_mapping[common_id]].append(splitted_data[0])
        if not cancel_inv:
            if splitted_data[1]:
                sell_ids.setdefault('pick_number__in', [])
                sell_ids['pick_number__in'].append(splitted_data[1])
        # sell_ids['order_status_flag'] = status_flag
    return sell_ids


@csrf_exempt
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def move_to_dc(request, user=''):
    reversion.set_user(request.user)
    cancel_flag = request.GET.get('cancel', '')
    if cancel_flag == 'true':
        status_flag = 'processed_orders'
        # sell_ids = construct_sell_ids(request, user)
    else:
        status_flag = 'delivery_challans'
    sell_ids = construct_sell_ids(request, user)
    seller_summary = SellerOrderSummary.objects.filter(**sell_ids)
    chn_no, chn_sequence = get_challan_number(user, seller_summary)
    try:
        for sel_obj in seller_summary:
            sel_obj.order_status_flag = status_flag
            sel_obj.save()
        return HttpResponse(json.dumps({'message': 'success'}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Exception raised wile updating status of Seller Order Summary: %s" %str(e))
        return HttpResponse(json.dumps({'message': 'failed'}))

@csrf_exempt
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def move_to_inv(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("move_to_inv: %s" % str(get_user_ip(request)))
    log.info('Move To Invoice: Request params for ' + user.username + ' are ' + str(request.GET.dict()))
    cancel_flag = request.GET.get('cancel', '')
    is_sample_option =  get_misc_value('create_order_po', user.id)
    if cancel_flag == 'true':
        sell_ids = construct_sell_ids(request, user, cancel_inv=True)
        #del sell_ids['pick_number__in']
    else:
        sell_ids = construct_sell_ids(request, user)
        #del sell_ids['pick_number__in']
    user_type = user.userprofile.user_type
    seller_summary = SellerOrderSummary.objects.filter(**sell_ids)
    if is_sample_option == 'true':
        for data in seller_summary:
            mappingData = list(OrderMapping.objects.filter(mapping_type='PO', order_id=data.order_id).values_list('mapping_id', flat=True))
            if mappingData:
                purchase_order_data = PurchaseOrder.objects.filter(id=mappingData[0]).values('received_quantity')
                if purchase_order_data:
                    received_quantity = purchase_order_data[0].get('received_quantity', 0)
                    if received_quantity != 0:
                        data.quantity = data.quantity - received_quantity
    if cancel_flag != 'true':
        if user_type == 'marketplace_user':
            marketplace = seller_summary[0].seller_order.order.marketplace
        else:
            marketplace = seller_summary[0].order.marketplace
        #if user.userprofile.multi_level_system == 1:
        #    admin_user_id = UserGroups.objects.filter(user_id=user.id).values_list('admin_user_id', flat=True)[0]
        #    admin_user = User.objects.get(id=admin_user_id)
        #    invoice_sequence = get_invoice_sequence_obj(admin_user, marketplace)
        #else:
        invoice_sequence = get_invoice_sequence_obj(user, marketplace)
        if invoice_sequence:
            invoice_seq = invoice_sequence[0]
            inv_no = int(invoice_seq.value)
            order_no = str(inv_no).zfill(3)
            is_inv_num_added = False
            date = datetime.datetime.now()
            for sel_obj in seller_summary:
                if not sel_obj.invoice_number:
                    sel_obj.invoice_number = order_no
                    if user_type == 'marketplace_user':
                        order_obj = sel_obj.seller_order.order
                    else:
                        order_obj = sel_obj.order
                    full_invoice_number = get_full_invoice_number(user, order_no, order_obj, invoice_date=sel_obj.creation_date,
                                                                    pick_number=sel_obj.pick_number)
                    sel_obj.full_invoice_number = full_invoice_number
                    sel_obj.creation_date=date
                    sel_obj.save()
                    is_inv_num_added = True
                else:
                    log.info("Invoice number already generated for Sel Obj ID:%s" %(sel_obj.id))
            if is_inv_num_added:
                invoice_seq.value = inv_no + 1
                invoice_seq.save()
    try:
        for sel_obj in seller_summary:
            if cancel_flag == 'true':
                if sel_obj.challan_number:
                    status_flag = 'delivery_challans'
                else:
                    status_flag = 'processed_orders'
            else:
                status_flag = 'customer_invoices'
            sel_obj.order_status_flag = status_flag
            sel_obj.save()
        return HttpResponse(json.dumps({'message': 'success'}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Exception raised wile updating status of Seller Order Summary: %s" %str(e))
        return HttpResponse(json.dumps({'message': 'failed'}))


@csrf_exempt
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def generate_customer_invoice_tab(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("create_invoice: %s" % str(get_user_ip(request)))
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
    merge_data = {}
    data_dict = dict(request.GET.iterlists())
    log.info('Request params for ' + user.username + ' is ' + str(request.GET.dict()))
    admin_user = get_priceband_admin_user(user)
    try:
        seller_summary_dat = data_dict.get('seller_summary_id', '')
        seller_summary_dat = seller_summary_dat[0]
        sor_id = ''
        sell_ids = {}
        field_mapping = {}
        if data_dict.get('sor_id', ''):
            is_marketplace = True
            sor_id = data_dict.get('sor_id', '')[0]
            sell_ids['seller_order__sor_id'] = sor_id
            field_mapping['invoice_number_in'] = 'invoice_number__in'
            field_mapping['sku_code'] = 'seller_order__order__sku__sku_code'
            field_mapping['order_id'] = 'seller_order__order_id'
            sell_ids['seller_order__seller__user'] = user.id
        else:
            is_marketplace = False
            if admin_user and user.userprofile.warehouse_type == 'DIST':
                field_mapping['invoice_number_in'] = 'invoice_number__in'
            else:
                sell_ids['order__user'] = user.id
                field_mapping['invoice_number_in'] = 'invoice_number__in'
            field_mapping['sku_code'] = 'order__sku__sku_code'
            field_mapping['order_id'] = 'order_id'
        seller_summary_dat = seller_summary_dat.split(',')
        all_data = OrderedDict()
        seller_order_ids = []
        pick_number = 1
        if request.GET.get('Marketplace', ''):
            sell_ids['order__marketplace'] = request.GET.get('Marketplace')
        for data_id in seller_summary_dat:
            splitted_data = data_id.split(':')
            sell_ids.setdefault(field_mapping['invoice_number_in'], [])
            sell_ids.setdefault('financial_year__in', [])
            #sell_ids.setdefault('pick_number__in', [])
            sell_ids[field_mapping['invoice_number_in']].append(splitted_data[0])
            sell_ids['financial_year__in'].append(splitted_data[2])
            #sell_ids['pick_number__in'].append(splitted_data[1])
            pick_number = splitted_data[1]
        seller_summary = SellerOrderSummary.objects.filter(**sell_ids)
        sequence_number = seller_summary[0].invoice_number if seller_summary else ''
        sell_ids['pick_number__in'] = seller_summary.values_list('pick_number', flat=True)
        order_ids = list(seller_summary.values_list(field_mapping['order_id'], flat=True))
        order_ids = map(lambda x: str(x), order_ids)
        order_ids = ','.join(order_ids)
        summary_details = seller_summary.values(field_mapping['sku_code']).distinct().annotate(
            total_quantity=Sum('quantity'))
        for detail in summary_details:
            if not detail[field_mapping['sku_code']] in merge_data.keys():
                merge_data[detail[field_mapping['sku_code']]] = detail['total_quantity']
            else:
                merge_data[detail[field_mapping['sku_code']]] += detail['total_quantity']

        invoice_data = get_invoice_data(order_ids, user, merge_data=merge_data, is_seller_order=True, sell_ids=sell_ids)
        edit_invoice = request.GET.get('edit_invoice', '')
        edit_dc = request.GET.get('edit_dc', '')
        if edit_invoice != 'true' or edit_dc != 'true':
            invoice_data = modify_invoice_data(invoice_data, user)
        ord_ids = order_ids.split(",")
        invoice_data = add_consignee_data(invoice_data, ord_ids, user)
        invoice_data['sequence_number'] = sequence_number
        invoice_data['challan_number'] = seller_summary[0].challan_number if seller_summary else ''
        invoice_date = datetime.datetime.now()
        if seller_summary:
            if seller_summary[0].seller_order:
                seller = seller_summary[0].seller_order.seller
                order = seller_summary[0].seller_order.order
            else:
                order = seller_summary[0].order

            invoice_date = seller_summary.order_by('-creation_date')[0].creation_date
        # invoice_date = get_local_date(user, invoice_date, send_date='true')
        invoice_data['sale_signature'] = get_auth_signature(request, user, invoice_date)
        inv_month_year = invoice_date.strftime("%m-%y")
        invoice_data['invoice_time'] = invoice_date.strftime("%H:%M")
        invoice_date = invoice_date.strftime("%d %b %Y")
        invoice_no = invoice_data['invoice_no']
        if is_marketplace:
            # invoice_no = user_profile.prefix + '/' + str(inv_month_year) + '/' + 'A-' + str(order.order_id)
            # invoice_data['order_id'] = sor_id
            invoice_data['sor_id'] = sor_id
        #if not len(set(sell_ids.get('pick_number__in', ''))) > 1:
        #    invoice_no = invoice_no + '/' + str(max(map(int, sell_ids.get('pick_number__in', ''))))
        invoice_data['invoice_no'] = invoice_no
        invoice_data['pick_number'] = pick_number
        invoice_data = add_consignee_data(invoice_data, ord_ids, user)
        return_data = request.GET.get('data', '')
        delivery_challan = request.GET.get('delivery_challan', '')
        invoice_data['invoice_date'] = invoice_date
        invoice_data['dc_display']  = get_misc_value('display_dc_invoice', user.id)
        order_reference_display = get_misc_value('display_order_reference', user.id)
        if order_reference_display == 'false':
            invoice_data['order_reference'] = ''
        if delivery_challan == "true":
            titles = ['']
            title_dat = get_misc_value('invoice_titles', user.id)
            if not title_dat == 'false':
                titles = title_dat.split(",")
            invoice_data['titles'] = titles
            invoice_data['total_items'] = len(invoice_data['data'])
            invoice_data['data'] = pagination(invoice_data['data'])
            invoice_data['username'] = user.username
            return render(request, 'templates/toggle/delivery_challan.html', invoice_data)
        elif return_data:
            invoice_data = json.dumps(invoice_data)
        elif get_misc_value('show_imei_invoice', user.id) == 'true' and user.userprofile.user_type == 'marketplace_user':
            invoice_data = build_marketplace_invoice(invoice_data, user, False)
        else:
            invoice_data = build_invoice(invoice_data, user, False)

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create customer invoice failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
        return HttpResponse(json.dumps({'message': 'failed'}))
    return HttpResponse(invoice_data)


# @csrf_exempt
# @get_admin_user
# def generate_stock_transfer_invoice(request, user=''):
#     resp_list = {'data': [],'titles': ['Stock transfer invoice (Non-Commercial)']}
#     data= json.loads(request.POST.get('data'))
#     total_invoice_amount, total_taxable_amount, total_tax, total_cgst_amt, total_sgst_amt, total_igst_amt,total_quantity,invoice_number,full_invoice_number = 0,0,0,0,0,0,0,0,0
#     order_id=data['order_id']
#     cess_amt,total_cess_amt = 0 ,0
#     get_stock_transfer = StockTransfer.objects.filter(order_id=order_id)
#     warehouse_id = get_stock_transfer[0].st_po.open_st.sku.user
#     order_date = get_stock_transfer[0].creation_date
#     invoice_date = ''
#     mb_user=False
#     if user.username in MILKBASKET_USERS :
#         mb_user = True
#     is_cess_tax_flag = 0
#     if mb_user:
#         is_cess_tax_flag = 1
#     interfix , prefix, date_type,full_invoice_number, invoice_number = '','','','',''
#     prefix_obj= UserTypeSequence.objects.filter(user=user.id,type_name='stock_transfer_invoice',type_value = 'Offline')
#     if prefix_obj.exists():
#         interfix = prefix_obj[0].interfix
#         prefix = prefix_obj[0].prefix
#         date_type = prefix_obj[0].date_type

#     user_profile = UserProfile.objects.get(user_id=user.id)
#     details_data = {'invoice_header': 'Stock Transfer Invoice',
#                     'gstin_no': user_profile.gst_number,
#                     'pan_number': user_profile.pan_number,
#                     'cin_no': user_profile.cin_number,
#                     'company_name': user_profile.company.company_name,
#                     'company_address': user_profile.address,
#                     'company_number': user_profile.phone_number,
#                     'email': user.email}
#     warehouse_obj = User.objects.get(id=warehouse_id)
#     if warehouse_obj:
#         warehouse = warehouse_obj.username
#     to_warehouse = UserProfile.objects.filter(user_id=warehouse_id)[0]
#     inter_state=False
#     if str(to_warehouse.state).lower() == str(user_profile.state).lower():
#         inter_state=True
#     dest_data = {'destination_gstin_no': to_warehouse.gst_number,
#                  'destination_pan_number': to_warehouse.pan_number,
#                  'destination_cin_no': to_warehouse.cin_number,
#                  'destination_company_name': to_warehouse.company.company_name,
#                  'destination_company_address': to_warehouse.address,
#                  'destination_company_number': to_warehouse.phone_number,
#                  'destination_email': warehouse_obj.email}
#     pick_qtys = dict(STOrder.objects.filter(stock_transfer_id__in=get_stock_transfer.values_list('id', flat=True)).\
#         annotate(group_key=Concat('stock_transfer__order_id', Value('<<>>'), 'stock_transfer__sku__sku_code', output_field=CharField())).values_list('group_key').annotate(tot_sum=Sum(F('picklist__picked_quantity')/F('picklist__stock__batch_detail__pcf'))))
#     for stock_transfer in get_stock_transfer:
#         if mb_user:
#             st_order_list=STOrder.objects.filter(stock_transfer_id=stock_transfer.id)
#         else:
#             st_order_list = [stock_transfer]
#         for i in st_order_list:
#             mb_picked_quantity = 0
#             cgst_tax,sgst_tax,igst_tax =0,0,0
#             try:
#                 if mb_user:
#                     if inter_state:
#                         igst_tax = i.picklist.stock.batch_detail.tax_percent
#                     else:
#                         cgst_tax = float(i.picklist.stock.batch_detail.tax_percent)/2
#                         sgst_tax = cgst_tax
#                     mb_picked_quantity = i.picklist.picked_quantity
#                     rate = i.picklist.stock.batch_detail.buy_price
#                 else:
#                     cgst_tax = stock_transfer.st_po.open_st.cgst_tax
#                     sgst_tax = stock_transfer.st_po.open_st.sgst_tax
#                     igst_tax = stock_transfer.st_po.open_st.igst_tax
#                     rate = stock_transfer.st_po.open_st.price
#                 shipment_date = str(stock_transfer.updation_date)
#                 invoice_date = stock_transfer.creation_date
#                 cess_tax = stock_transfer.st_po.open_st.cess_tax
#                 if data.get('pick_number','')[0]:
#                     stock_transfer_summary =StockTransferSummary.objects.filter(stock_transfer_id=stock_transfer.id,pick_number__in=data.get('pick_number'))
#                     if not stock_transfer_summary.exists():
#                         continue
#                     if full_invoice_number:
#                         stock_transfer_summary.update(invoice_number=invoice_number,
#                                                       full_invoice_number=full_invoice_number, invoice_date=invoice_date)
#                     if not mb_user:
#                         total_picked_quantity = pick_qtys.get(str(stock_transfer.order_id) + '<<>>' + str(stock_transfer.sku.sku_code), 0)
#                         #total_picked_quantity = stock_transfer_summary.aggregate(tot_quantity=Sum('quantity'))['tot_quantity']
#                     if stock_transfer_summary[0].invoice_number:
#                         invoice_number = stock_transfer_summary[0].invoice_number
#                         full_invoice_number = stock_transfer_summary[0].full_invoice_number
#                         invoice_date = stock_transfer_summary[0].invoice_date
#                     else:
#                         invoice_date = stock_transfer_summary[0].creation_date
#                         in_obj = IncrementalTable.objects.filter(user=user.id,type_name='stock_transfer_invoice')
#                         if in_obj.exists():
#                             invoice_number = in_obj[0].value
#                             in_obj.update(value=invoice_number+1)
#                         else:
#                             invoice_number = 1
#                             in_obj = IncrementalTable.objects.create(user=user, type_name='stock_transfer_invoice',value =invoice_number+1)
#                         date_format = invoice_date.strftime('%m%y')
#                         if prefix:
#                             if date_type == 'financial':
#                                 date_format = get_financial_year(invoice_date)
#                             full_invoice_number = '{}/{}/{}'.format(prefix,
#                                                                        date_format,
#                                                                        str(invoice_number).zfill(3))
#                         else:
#                             full_invoice_number = '{}/{}/{}'.format(user_profile.prefix,
#                                                                          date_format,
#                                                                        str(invoice_number).zfill(3))
#                         stock_transfer_summary.update(invoice_number=invoice_number,full_invoice_number =full_invoice_number,invoice_date=invoice_date)
#                 else:
#                     total_picked_quantity = pick_qtys.get(str(stock_transfer.order_id) + '<<>>' + str(stock_transfer.sku.sku_code), 0)
#                 if mb_user:
#                     total_picked_quantity = mb_picked_quantity
#                 price = rate * total_picked_quantity
#                 total_quantity+=total_picked_quantity
#                 cgst_amt, sgst_amt ,igst_amt,gst,cess_amt = 0,0,0,0,0
#                 if cgst_tax :
#                     cgst_amt = (price * cgst_tax)/100
#                     sgst_amt = (price * sgst_tax)/100
#                 else:
#                     igst_amt  = (price * igst_tax)/100
#                 if cess_tax:
#                     cess_amt = (price * cess_tax)/100
#                 total_cgst_amt+=cgst_amt
#                 total_sgst_amt+=sgst_amt
#                 total_igst_amt+=igst_amt
#                 total_cess_amt+=cess_amt
#                 gst = cgst_amt+ sgst_amt + igst_amt
#                 total_price = price+gst+cess_amt
#                 total_taxable_amount +=price
#                 total_invoice_amount += total_price
#                 total_tax +=gst
#                 sku_description = stock_transfer.sku.sku_desc
#                 sku = stock_transfer.sku.wms_code
#                 hsn_code = stock_transfer.sku.hsn_code
#             except Exception as e:
#                 import traceback
#                 log.debug(traceback.format_exc())
#                 log.info('Stock Transfer  invoice Generation failed for %s and params are %s and error statement is %s' % (
#                     str(user.username), str(request.POST.dict()), str(e)))
#             final_data = {'order_id' : order_id, 'picked_quantity' : total_picked_quantity,'price':price,
#                     'cgst_tax':cgst_tax,'sgst_tax':sgst_tax,'igst_tax':igst_tax,'unit_price' : rate,
#                     'igst_amt':igst_amt, 'cgst_amt':cgst_amt , 'sgst_amt':sgst_amt,'hsn_code':hsn_code,
#                     'amount' : total_price, 'stock_transfer_date_time' : str(shipment_date), 'warehouse_name': warehouse,
#                     'sku_code' : sku, 'invoice_date' : '','cess_tax':cess_tax,'cess_amt':cess_amt,
#                     'to_warehouse' : to_warehouse, 'title' : sku_description,
#                     'invoice_number' : '' }
#             resp_list['data'].append(final_data)
#     if invoice_date:
#         invoice_date = invoice_date.strftime("%d %b %Y")
#     order_date =  order_date.strftime("%d %b %Y")

#     total_prices_dict = {'total_taxable_amount':total_taxable_amount,'total_quantity':total_quantity,'full_invoice_number':full_invoice_number,
#                          'order_id':order_id,'invoice_date':invoice_date,'order_date':order_date,'declaration': DECLARATIONS['default'],
#                          'total_invoice_amount':total_invoice_amount,'total_tax':total_tax,'total_tax_words':number_in_words(total_tax),
#                          'invoice_header':'Stock transfer invoice (Non-Commercial)','is_cess_tax_flag':is_cess_tax_flag,'total_cess_amt':total_cess_amt,
#                          'rounded_invoice_amount':round(total_invoice_amount), 'price_in_words':number_in_words(round(total_invoice_amount)),
#                          'total_igst_amt':total_igst_amt, 'total_cgst_amt':total_cgst_amt, 'total_sgst_amt': total_sgst_amt}
#     title_dat = get_misc_value('invoice_titles', user.id)
#     if not title_dat == 'false':
#         resp_list['titles'] = title_dat.split(",")
#     resp_list.update(details_data)
#     resp_list.update(dest_data)
#     resp_list.update(total_prices_dict)
#     html = build_invoice(resp_list,user,css=False,stock_transfer=True)
#     return HttpResponse(html)

@csrf_exempt
@get_admin_user
def generate_stock_transfer_invoice(request, user=''):
    resp_list = {'data': [],'titles': ['Stock transfer invoice (Non-Commercial)']}
    data= json.loads(request.POST.get('data'))
    total_invoice_amount, total_taxable_amount, total_tax, total_cgst_amt, total_sgst_amt, total_igst_amt,total_quantity,invoice_number,full_invoice_number = 0,0,0,0,0,0,0,0,0
    order_id=data['order_id']
    cess_amt,total_cess_amt, total_qty = 0 ,0, 0
    user = User.objects.get(id=data['source_wh'])
    get_stock_transfer = StockTransfer.objects.filter(order_id=order_id, sku__user=data['source_wh'])
    warehouse_id = get_stock_transfer[0].st_po.open_st.sku.user
    order_date = get_stock_transfer[0].creation_date
    invoice_date = ''
    interfix , prefix, date_type,full_invoice_number, invoice_number = '','','','',''
    user_profile = UserProfile.objects.get(user_id=user.id)
    source_address = UserAddresses.objects.filter(user=user, address_type='Shipment Address').order_by('-creation_date').values('mobile_number', 'address', 'pincode')
    if source_address.exists():
        source_address = source_address[0]
        source_phoneno = source_address['mobile_number']
        source_address = "%s %s : %s - %s" %(user.first_name, user.last_name, source_address['address'], source_address['pincode'])
    else:
        source_address = user_profile.address
        source_phoneno = user_profile.phone_number
    details_data = {'invoice_header': 'Stock Transfer Invoice',
                    'gstin_no': user_profile.gst_number,
                    'pan_number': user_profile.pan_number,
                    'cin_no': user_profile.cin_number,
                    'company_name': user_profile.company.company_name,
                    'company_address': source_address,
                    'company_number': source_phoneno,
                    'email': user.email}
    warehouse_obj = User.objects.get(id=warehouse_id)
    if warehouse_obj:
        warehouse = warehouse_obj.username
    to_warehouse = UserProfile.objects.filter(user_id=warehouse_id)[0]
    inter_state=False
    if str(to_warehouse.state).lower() == str(user_profile.state).lower():
        inter_state=True
    dest_address = UserAddresses.objects.filter(user=warehouse_obj, address_type='Shipment Address').order_by('-creation_date').values('mobile_number', 'address', 'pincode')
    if dest_address.exists():
        dest_address = dest_address[0]
        dest_phoneno = dest_address['mobile_number']
        dest_address = "%s - %s" %(dest_address['address'], dest_address['pincode'])
    else:
        dest_address = to_warehouse.address
        dest_phoneno = to_warehouse.phone_number
    dest_data = {'destination_gstin_no': to_warehouse.gst_number,
                 'destination_pan_number': to_warehouse.pan_number,
                 'destination_cin_no': to_warehouse.cin_number,
                 # 'destination_company_name': to_warehouse.company.company_name,
                 'destination_company_name': "%s %s" %(warehouse_obj.first_name, warehouse_obj.last_name),
                 'destination_company_address': dest_address,
                 'destination_company_number': dest_phoneno,
                 'destination_email': warehouse_obj.email}
    stock_transfer_data = StockTransferSummary.objects.filter(stock_transfer__st_type='ST_INTRA', stock_transfer__order_id=data['order_id'], stock_transfer__status=2, pick_number = data['pick_number'], stock_transfer__sku__user=user.id)
    for invoice_no in stock_transfer_data:
        cgst_tax,sgst_tax,igst_tax, igst_amt, cgst_amt, sgst_amt = 0,0,0,0,0,0
        try:
            uom_dict = get_uom_with_sku_code(user, invoice_no.stock_transfer.sku.sku_code, uom_type='purchase')
            batch_pcf = uom_dict.get('sku_conversion', 1)
            batch_number = ''
            expiry_date = ''
            manufactured_date = ''
            batch_po_loc_list = list(invoice_no.picklist.picklistlocation_set.filter().values_list('id', flat=True))
            batch_data = PickSequenceMapping.objects.filter(pick_loc_id__in= batch_po_loc_list, pick_number=invoice_no.pick_number).values(
                'pick_loc__stock__batch_detail__batch_no',
                'pick_loc__stock__batch_detail__manufactured_date',
                'pick_loc__stock__batch_detail__expiry_date'
                )
            if batch_data.exists():
                batch_number = batch_data[0]['pick_loc__stock__batch_detail__batch_no']
                expiry_date = batch_data[0]['pick_loc__stock__batch_detail__expiry_date'].strftime(
                    "%d %b, %Y") if batch_data[0]['pick_loc__stock__batch_detail__expiry_date'] else ''
                manufactured_date = batch_data[0]['pick_loc__stock__batch_detail__manufactured_date'].strftime(
                    "%d %b, %Y") if batch_data[0]['pick_loc__stock__batch_detail__manufactured_date'] else ''
            try:
                invoice_no.quantity = float(invoice_no.quantity) / float(batch_pcf)
            except Exception as e:
                invoice_no.quantity = float(invoice_no.quantity) / float(invoice_no.picklist.stock.batch_detail.pcf)
            invoice_date = invoice_no.creation_date.strftime("%d %b %Y")
            if invoice_no.price:
                price = invoice_no.price
            else:
                price = invoice_no.stock_transfer.st_po.open_st.price
            temp_dict = {}
            temp_dict['order_id'] = invoice_no.stock_transfer.order_id
            temp_dict['sku_code'] = invoice_no.stock_transfer.sku.sku_code
            temp_dict['desc'] = invoice_no.stock_transfer.sku.sku_desc
            temp_dict['qty'] = invoice_no.quantity
            temp_dict['amount'] = round(invoice_no.quantity * price, 3)
            temp_dict['batch_number'] = batch_number
            temp_dict['manufactured_date'] = manufactured_date
            temp_dict['expiry_date'] = expiry_date
            total_quantity += float(invoice_no.quantity)
            total_invoice_amount += temp_dict['amount']

        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Stock Transfer  invoice Generation failed for %s and params are %s and error statement is %s' % (
                str(user.username), str(request.POST.dict()), str(e)))
        final_data = {'order_id' : temp_dict['order_id'], 'picked_quantity' : temp_dict['qty'],'price':price,
                'cgst_tax':cgst_tax,'sgst_tax':sgst_tax,'igst_tax':igst_tax,'unit_price' : price,
                'igst_amt':igst_amt, 'cgst_amt':cgst_amt , 'sgst_amt':sgst_amt,'hsn_code':invoice_no.stock_transfer.sku.hsn_code,
                'amount' : temp_dict['amount'], 'stock_transfer_date_time' : str(''), 'warehouse_name': user.username,
                'sku_code' : temp_dict['sku_code'], 'invoice_date' : invoice_date,'cess_tax':0,'cess_amt':0,
                'to_warehouse' : warehouse_obj.username, 'title' : temp_dict['desc'],
                'invoice_number' : '' }
        resp_list['data'].append(final_data)
    order_date =  order_date.strftime("%d %b %Y")
    total_prices_dict = {'total_taxable_amount':total_invoice_amount,'total_quantity':total_quantity,'full_invoice_number':"%s/%s"%(data['order_id'], data['pick_number']),
                         'order_id':data['order_id'],'invoice_date':invoice_date,'order_date':order_date,'declaration': DECLARATIONS['default'],
                         'total_invoice_amount':total_invoice_amount,'total_tax':total_tax,'total_tax_words':number_in_words(total_tax),
                         'invoice_header':'Stock transfer invoice (Non-Commercial)','is_cess_tax_flag':0,'total_cess_amt':0,
                         'rounded_invoice_amount':round(total_invoice_amount), 'price_in_words':number_in_words(round(total_invoice_amount)),
                         'total_igst_amt':0, 'total_cgst_amt':0, 'total_sgst_amt': 0}
    title_dat = get_misc_value('invoice_titles', user.id)
    if not title_dat == 'false':
        resp_list['titles'] = title_dat.split(",")
    resp_list.update(details_data)
    resp_list.update(dest_data)
    resp_list.update(total_prices_dict)
    html = build_invoice(resp_list,user,css=False,stock_transfer=True)
    return HttpResponse(html)


@csrf_exempt
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def generate_customer_invoice(request, user=''):
    reversion.set_user(request.user)
    reversion.set_comment("create_invoice: %s" % str(get_user_ip(request)))
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
    merge_data = {}
    delivery_challan = request.GET.get('delivery_challan', 'false')
    data_dict = dict(request.GET.iterlists())
    log.info('Request params for ' + user.username + ' is ' + str(request.GET.dict()))
    admin_user = get_priceband_admin_user(user)
    try:
        pick_number_list = []
        if data_dict['seller_summary_id']:
            value = data_dict['seller_summary_id'][0]
            if '<<>>' in value:
                ids_list = value.split('<<>>')
                for id_value in ids_list:
                    if ':' in id_value:
                        pic_num = id_value.split(':')
                        pick_number_list.append(pic_num[1])
            elif ':' in value:
                pic_num = value.split(':')
                pick_number_list.append(pic_num[1])
            else:
                pick_number_list.append(1)
        seller_summary_dat = data_dict.get('seller_summary_id', '')
        delivery_challan_pickid = data_dict.get('picklist_id', '')
        seller_summary_dat = seller_summary_dat[0]
        sor_id = ''
        sell_ids = {}
        field_mapping = {}
        if data_dict.get('sor_id', ''):
            is_marketplace = True
            sor_id = data_dict.get('sor_id', '')[0]
            sell_ids['seller_order__sor_id'] = sor_id
            field_mapping['order_id_in'] = 'seller_order__order__order_id__in'
            field_mapping['sku_code'] = 'seller_order__order__sku__sku_code'
            field_mapping['order_id'] = 'seller_order__order_id'
            sell_ids['seller_order__seller__user'] = user.id
        else:
            is_marketplace = False
            if admin_user and user.userprofile.warehouse_type == 'DIST':
                field_mapping['order_id_in'] = 'order__id__in'
            else:
                sell_ids['order__user'] = user.id
                field_mapping['order_id_in'] = 'order__order_id__in'
            field_mapping['sku_code'] = 'order__sku__sku_code'
            field_mapping['order_id'] = 'order_id'
        seller_summary_dat = seller_summary_dat.split('<<>>')
        all_data = OrderedDict()
        seller_order_ids = []
        pick_number = 1
        for data_id in seller_summary_dat:
            splitted_data = data_id.split(':')
            sell_ids.setdefault(field_mapping['order_id_in'], [])
            sell_ids.setdefault('pick_number__in', [])
            sell_ids[field_mapping['order_id_in']].append(splitted_data[0])
            sell_ids['pick_number__in'].append(splitted_data[1])
            pick_number = splitted_data[1]
        generate_delivery_challan =  get_misc_value('generate_delivery_challan_before_pullConfiramation', user.id)
        if generate_delivery_challan and delivery_challan_pickid:
            seller_summary = OrderDetail.objects.filter(order_id=splitted_data[0], user=user.id)
            order_ids = list(seller_summary.values_list('id', flat=True))
            order_ids = map(lambda x: str(x), order_ids)
            order_ids = ','.join(order_ids)
            summary_details = seller_summary.values('sku_code').annotate(
                total_quantity=Sum('quantity'))
        else:
            seller_summary = SellerOrderSummary.objects.filter(**sell_ids)
            order_ids = list(seller_summary.values_list(field_mapping['order_id'], flat=True))
            order_ids = map(lambda x: str(x), order_ids)
            order_ids = ','.join(order_ids)
            summary_details = seller_summary.values(field_mapping['sku_code']).distinct().annotate(
                total_quantity=Sum('quantity'))
        for detail in summary_details:
            if generate_delivery_challan and delivery_challan_pickid:
                data, sku_total_quantities, courier_name = get_picklist_data(delivery_challan_pickid[0], user.id)
                merge_data = sku_total_quantities
            else:
                if not detail[field_mapping['sku_code']] in merge_data.keys():
                    merge_data[detail[field_mapping['sku_code']]] = detail['total_quantity']
                else:
                    merge_data[detail[field_mapping['sku_code']]] += detail['total_quantity']
        invoice_data = get_invoice_data(order_ids, user, merge_data=merge_data, pick_num = pick_number_list, is_seller_order=True,
                                        sell_ids=sell_ids, delivery_challan=delivery_challan)
        edit_invoice = request.GET.get('edit_invoice', '')
        edit_dc = request.GET.get('edit_dc', '')
        if edit_invoice != 'true' or edit_dc != 'true':
            invoice_data = modify_invoice_data(invoice_data, user)
        ord_ids = order_ids.split(",")
        invoice_data = add_consignee_data(invoice_data, ord_ids, user)
        invoice_date = datetime.datetime.now()
        if seller_summary and generate_delivery_challan == False:
            if seller_summary[0].seller_order:
                seller = seller_summary[0].seller_order.seller
                order = seller_summary[0].seller_order.order
            else:
                order = seller_summary[0].order

            invoice_date = seller_summary.order_by('-creation_date')[0].creation_date
        invoice_date = get_local_date(user, invoice_date, send_date='true')
        inv_month_year = invoice_date.strftime("%m-%y")
        invoice_data['invoice_time'] = invoice_date.strftime("%H:%M")
        invoice_date = invoice_date.strftime("%d %b %Y")
        invoice_no = invoice_data['invoice_no']
        if is_marketplace:
            # invoice_no = user_profile.prefix + '/' + str(inv_month_year) + '/' + 'A-' + str(order.order_id)
            # invoice_data['order_id'] = sor_id
            invoice_data['sor_id'] = sor_id
        if not len(set(sell_ids.get('pick_number__in', ''))) > 1:
            invoice_no = invoice_no + '/' + str(max(map(int, sell_ids.get('pick_number__in', ''))))
        invoice_data['invoice_no'] = invoice_no
        invoice_data['pick_number'] = pick_number
        invoice_data = add_consignee_data(invoice_data, ord_ids, user)
        return_data = request.GET.get('data', '')
        delivery_challan = request.GET.get('delivery_challan', '')
        if delivery_challan == "true":
            titles = ['']
            title_dat = get_misc_value('invoice_titles', user.id)
            if not title_dat == 'false':
                titles = title_dat.split(",")
            invoice_data['titles'] = titles
            invoice_data['total_items'] = len(invoice_data['data'])
            invoice_data['data'] = pagination(invoice_data['data'])
            invoice_data['username'] = user.username
            return render(request, 'templates/toggle/delivery_challan.html', invoice_data)
        elif return_data:
            invoice_data = json.dumps(invoice_data)
        elif get_misc_value('show_imei_invoice', user.id) == 'true' and user.userprofile.user_type == 'marketplace_user':
            invoice_data = build_marketplace_invoice(invoice_data, user, False)
        else:
            invoice_data = build_invoice(invoice_data, user, False)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create customer invoice failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
        return HttpResponse(json.dumps({'message': 'failed'}))
    return HttpResponse(invoice_data)


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

@csrf_exempt
def get_seller_order_view(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters,
                          user_dict={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    user_dict = eval(user_dict)
    lis = ['sor_id', 'sor_id', 'order__order_id', 'seller__name', 'order__customer_name', 'order__marketplace', 'total',
           'order__creation_date', 'order__city', 'order__status']
    data_dict = {'order__status': 1, 'order__user': user.id, 'order__quantity__gt': 0, 'status': 1}

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    if user_dict.get('market_places', ''):
        marketplace = user_dict['market_places'].split(',')
        data_dict['order__marketplace__in'] = marketplace
    if user_dict.get('customer_id', ''):
        data_dict['order__customer_id'], data_dict['order__customer_name'] = user_dict['customer_id'].split(':')
    search_params = get_filtered_params(filters, lis[1:])

    if 'order__order_id__icontains' in search_params.keys():
        order_search = search_params['order__order_id__icontains']
        search_params['order__order_id__icontains'] = ''.join(re.findall('\d+', order_search))
        search_params['order__order_code__icontains'] = ''.join(re.findall('\D+', order_search))
    search_params['order__sku_id__in'] = sku_master_ids
    order_taken_val_user = CustomerOrderSummary.objects.filter(order__user=user.id)
    single_search = "no"
    if 'city__icontains' in search_params.keys():
        order_taken_val_user = CustomerOrderSummary.objects.filter(
            Q(order_taken_by__icontains=search_params['city__icontains']))
        single_search = "yes"
        del (search_params['city__icontains'])

    all_seller_orders = SellerOrder.objects.select_related('order', 'seller').filter(**data_dict)
    if search_term:
        mapping_results = all_seller_orders.values('order__customer_name', 'order__order_id', 'order__order_code',
                                                   'order__original_order_id',
                                                   'order__marketplace', 'sor_id', 'seller__name', 'seller_id'). \
            distinct().annotate(total=Sum('quantity')).filter(Q(order__customer_name__icontains=search_term) |
                                                              Q(order__order_id__icontains=search_term) | Q(
            order__marketplace__icontains=search_term) |
                                                              Q(sor_id__icontains=search_term) | Q(
            seller__name__icontains=search_term) |
                                                              Q(total__icontains=search_term),
                                                              **search_params).order_by(order_data)
    else:
        mapping_results = all_seller_orders.values('order__customer_name', 'order__order_id', 'order__order_code',
                                                   'order__original_order_id',
                                                   'order__marketplace', 'sor_id', 'seller__name', 'seller_id'). \
            distinct().annotate(total=Sum('quantity')).filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    index = 0
    for dat in mapping_results[start_index:stop_index]:
        cust_status_obj = CustomerOrderSummary.objects.filter(order__order_id=dat['order__order_id']).only('status', 'shipment_time_slot', 'order_taken_by',
                                                                'order__creation_date')
        if cust_status_obj:
            cust_status = cust_status_obj[0].status
            time_slot = cust_status_obj[0].shipment_time_slot
            order_taken_val = cust_status_obj[0].order_taken_by
            creation_date = cust_status_obj[0].order.creation_date
            creation_data = get_local_date(user, creation_date, True).strftime("%d %b, %Y")
        else:
            cust_status = ""
            time_slot = ""
            order_taken_val = ''
            creation_data = ''

        '''order_taken_val = ''
        if order_taken_val_user:
            order_taken_val = order_taken_val_user.filter(order__order_id=dat['order__order_id'])
            if order_taken_val:
                order_taken_val = order_taken_val[0].order_taken_by
            else:
                order_taken_val = ""'''
        if single_search == "yes" and order_taken_val == '':
            continue

        if dat['order__original_order_id']:
            order_id = dat['order__original_order_id']
        else:
            order_id = dat['order__order_code'] + str(dat['order__order_id'])
        check_values = str(order_id) + '<>' + str(dat['sor_id']) + '<>' + str(dat['seller_id'])
        #name = all_seller_orders.filter(order__order_id=dat['order__order_id'],
        #                                order__order_code=dat['order__order_code'], order__user=user.id)
        #creation_date = name[0].creation_date
        #name = name[0].id
        #creation_data = get_local_date(user, creation_date, True).strftime("%d %b, %Y")
        # if time_slot:
        #    shipment_data = shipment_data + ', ' + time_slot

        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (
        str(order_id) + '<>' + str(dat['sor_id']), dat['total'])

        temp_data['aaData'].append(OrderedDict((('', checkbox), ('data_value', check_values), ('SOR ID', dat['sor_id']),
                                                ('UOR ID', order_id), ('Seller Name', dat['seller__name']),
                                                ('Customer Name', dat['order__customer_name']),
                                                ('Market Place', dat['order__marketplace']),
                                                ('Total Quantity', dat['total']), ('Order Taken By', order_taken_val),
                                                ('Creation Date', creation_data),
                                                ('id', index), ('DT_RowClass', 'results'), ('Status', cust_status))))
        index += 1
    col_val = ['SOR ID', 'SOR ID', 'UOR ID', 'Seller Name', 'Customer Name', 'Market Place', 'Total Quantity',
               'Creation Date', 'Order Taken By', 'Status']
    if order_term:
        order_data = col_val[col_num]
        if order_term == "asc":
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data])
        else:
            temp_data['aaData'] = sorted(temp_data['aaData'], key=lambda x: x[order_data], reverse=True)


@csrf_exempt
@login_required
@get_admin_user
def seller_generate_picklist(request, user=''):
    filters = request.POST.get('filters', '')
    enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
    order_filter = {'order__status': 1, 'order__user': user.id, 'order__quantity__gt': 0}
    if filters:
        filters = eval(filters)
        if filters['market_places']:
            order_filter['order__marketplace__in'] = (filters['market_places']).split(',')
        if filters.get('customer_id', ''):
            customer_id = ''.join(re.findall('\d+', filters['customer_id']))
            order_filter['order__customer_id'] = customer_id
    data = []
    order_data = []
    stock_status = ''
    out_of_stock = []
    picklist_number = get_picklist_number(user)

    log.info('Request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        picklist_exclude_zones = get_exclude_zones(user)
        switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                       'fifo_switch': get_misc_value('fifo_switch', user.id),
                       'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                       'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id),
                       'allow_partial_picklist': get_misc_value('allow_partial_picklist', user.id)}
        sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
        if enable_damaged_stock =='true' :
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(
                        sku__user=user.id, quantity__gt=0,location__zone__zone='DAMAGED_ZONE')
        else:
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
                            location__zone__zone__in=picklist_exclude_zones). \
                             filter(sku__user=user.id, quantity__gt=0)
        all_seller_orders = SellerOrder.objects.prefetch_related('order__sku').filter(**order_filter)

        if switch_vals['fifo_switch'] == 'true':
            stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by(
                'receipt_date')
            #data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
            stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
        else:
            stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by(
                'location_id__pick_sequence')
            stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by(
                'receipt_date')
        all_sku_stocks = stock_detail1 | stock_detail2
        seller_stocks = SellerStock.objects.filter(seller__user=user.id, stock__quantity__gt=0).values('stock_id', 'seller_id')
        for key, value in request.POST.iteritems():
            if key in PICKLIST_SKIP_LIST or key in ['filters', 'enable_damaged_stock']:
                continue

            sku_stocks = all_sku_stocks
            order_filter = {'quantity__gt': 0}
            seller_id = ''
            if '<>' in key:
                key = key.split('<>')
                order_id, sor_id, seller_id = key
                order_filter['sor_id'] = sor_id
                order_filter['seller_id'] = seller_id
            else:
                order_id = key
            if seller_id:
                seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(seller_id), seller_stocks)
                if seller_stock_dict:
                    sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
                    sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
                else:
                    sku_stocks = sku_stocks.filter(id=0)
            order_code = ''.join(re.findall('\D+', order_id))
            order_id = ''.join(re.findall('\d+', order_id))
            order_filter['order__order_id'] = order_id
            order_filter['order__order_code'] = order_code

            seller_orders = all_seller_orders.filter(**order_filter).order_by('order__shipment_date')

            stock_status, picklist_number = picklist_generation(seller_orders, enable_damaged_stock, picklist_number,
                                                                user, sku_combos, sku_stocks, switch_vals,
                                                                status='open', remarks='', is_seller_order=True)

            if stock_status:
                out_of_stock = out_of_stock + stock_status

        if out_of_stock:
            stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
        else:
            stock_status = ''

        check_picklist_number_created(user, picklist_number + 1)
        show_image = 'false'
        use_imei = 'false'
        order_status = ''
        headers = list(PROCESSING_HEADER)
        data1 = MiscDetail.objects.filter(user=user.id, misc_type='show_image')
        if data1:
            show_image = data1[0].misc_value
        if show_image == 'true':
            headers.insert(0, 'Image')
        imei_data = MiscDetail.objects.filter(user=user.id, misc_type='use_imei')
        if imei_data:
            use_imei = imei_data[0].misc_value
        if use_imei == 'true':
            headers.insert(-1, 'Serial Number')
        if get_misc_value('pallet_switch', user.id) == 'true':
            headers.insert(headers.index('Location') + 1, 'Pallet Code')

        data, sku_total_quantities, courier_name = get_picklist_data(picklist_number + 1, user.id)
        if data:
            order_status = data[0]['status']
            if order_status == 'open':
                headers.insert(headers.index('WMS Code'), 'Order ID')
                order_count = list(set(map(lambda d: d.get('order_no', ''), data)))
                order_count_len = len(filter(lambda x: len(str(x)) > 0, order_count))
                if order_count_len == 1:
                    single_order = str(order_count[0])
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Seller Order level Generate Picklist failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse(json.dumps({'stock_status': 'Generate Picklist Failed'}))

    return HttpResponse(json.dumps({'data': data, 'headers': headers,
                                    'picklist_id': picklist_number + 1, 'stock_status': stock_status,
                                    'show_image': show_image,
                                    'use_imei': use_imei, 'order_status': order_status, 'user': request.user.id, \
                                    'sku_total_quantities': sku_total_quantities}))


def update_exist_picklists(picklist_no, request, user, sku_code='', location='', picklist_obj=None):
    filter_param = {'reserved_quantity__gt': 0, 'picklist_number': picklist_no}
    if picklist_obj:
        picklist_objs = [picklist_obj]
    elif not sku_code:
        picklist_objs = Picklist.objects.filter(Q(stock__sku__user=user.id) | Q(order__user=user.id), **filter_param)
    else:
        picklist_objs = Picklist.objects.filter(Q(stock__sku__user=user.id) | Q(order__user=user.id),
                                                Q(stock__sku__sku_code=sku_code) |
                                                Q(order__sku__sku_code=sku_code) | Q(sku_code=sku_code), **filter_param)
    picklist_data = {}
    new_pc_locs_list = []
    picklist_exclude_zones = get_exclude_zones(user)
    for item in picklist_objs:
        _sku_code = ''
        if item.order:
            _sku_code = item.order.sku.sku_code
        elif item.stock:
            _sku_code = item.stock.sku.sku_code
        if item.sku_code:
            _sku_code = item.sku_code
        stock_params = {'sku__user': user.id, 'quantity__gt': 0, 'sku__sku_code': _sku_code}
        if location:
            stock_params['location__location'] = location
        if item.damage_suggested:
            stock_objs = StockDetail.objects.prefetch_related('sku', 'location').filter(location__zone__zone__in=['DAMAGED_ZONE']).filter(**stock_params).order_by('location__pick_sequence')
        else:
            stock_objs = StockDetail.objects.prefetch_related('sku', 'location').exclude(location__zone__zone__in=picklist_exclude_zones).filter(**stock_params).order_by('location__pick_sequence')
        picklist_data['stock_id'] = 0
        stock_quan = 0
        if item.stock_id:
            picklist_data['stock_id'] = item.stock_id
            current_stock_objs = stock_objs.filter(id=item.stock_id)
            if current_stock_objs:
                current_stock_obj = current_stock_objs[0]
                stock_quan = current_stock_obj.quantity
                if current_stock_obj.quantity >= item.reserved_quantity:
                    continue

        needed_quantity = item.reserved_quantity
        if stock_quan:
            needed_quantity = needed_quantity - stock_quan
        if not needed_quantity:
            continue
        consumed_qty = 0

        if item.order:
            picklist_data['order_id'] = item.order.id
        picklist_data['sku_code'] = item.sku_code
        picklist_data['picklist_number'] = picklist_no
        picklist_data['reserved_quantity'] = 0
        picklist_data['picked_quantity'] = 0
        picklist_data['remarks'] = item.remarks
        picklist_data['order_type'] = item.order_type
        picklist_data['status'] = item.status
        picklist_data['damage_suggested'] = int(item.damage_suggested)

        consumed_qty, new_pc_locs = picklist_location_suggestion(request, item.order, stock_objs, user, needed_quantity,
                                                                 picklist_data)
        if new_pc_locs:
            new_pc_locs_list = list(chain(new_pc_locs_list, new_pc_locs))

        item.reserved_quantity -= float(consumed_qty)
        item.save()
        if consumed_qty:
            exist_pics = PicklistLocation.objects.filter(picklist_id=item.id, status=1, reserved__gt=0)
            update_picklist_locations(exist_pics, item, consumed_qty, 'true')
        if item.reserved_quantity == 0 and not item.picked_quantity:
            item.delete()
    return new_pc_locs_list

@csrf_exempt
@login_required
@get_admin_user
def update_picklist_loc(request, user=""):
    picklist_no = request.GET.get('picklist_id', "")
    if not picklist_no:
        return HttpResponse('PICKLIST ID missing')
    update_exist_picklists(picklist_no, request, user, sku_code='', location='', picklist_obj=None)
    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def customer_invoice_data(request, user=''):
    user_profile = UserProfile.objects.get(user_id=user.id)
    tab_type = request.GET.get('tabType', '')
    if user_profile.warehouse_type == 'DIST':
        headers = DIST_CUSTOMER_INVOICE_HEADERS
    elif user_profile.user_type == 'marketplace_user':
        if tab_type == 'DeliveryChallans':
            headers = ['Challan ID'] + MP_CUSTOMER_INVOICE_HEADERS
        elif tab_type == 'CustomerInvoices':
            headers = ["Invoice ID"] + WH_CUSTOMER_INVOICE_HEADERS_TAB
        else:
            headers = MP_CUSTOMER_INVOICE_HEADERS
    else:
        if tab_type == 'DeliveryChallans':
            headers = ['Challan ID'] + WH_CUSTOMER_INVOICE_HEADERS
        elif tab_type == 'CustomerInvoices':
            headers = ["Invoice ID"] + WH_CUSTOMER_INVOICE_HEADERS_TAB
        else:
            headers = WH_CUSTOMER_INVOICE_HEADERS
    return HttpResponse(json.dumps({'headers': headers}))


@csrf_exempt
@login_required
@get_admin_user
def stock_transfer_invoice_data(request, user=''):
    headers = STOCK_TRANSFER_INVOICE_HEADERS
    return HttpResponse(json.dumps({'headers': headers}))

@csrf_exempt
@login_required
@get_admin_user
def stock_transfer_inter_invoice_data(request, user=''):
    headers = STOCK_TRANSFER_INTER_INVOICE_HEADERS
    return HttpResponse(json.dumps({'headers': headers}))

@csrf_exempt
@login_required
@get_admin_user
def search_template_names(request, user=''):
    template_names = []
    name = request.GET.get('q', '')

    if name:
        template_names = list(
            ProductProperties.objects.filter(user_id=user.id, name__icontains=name).values_list('name',
                                                                                                flat=True).distinct())

    return HttpResponse(json.dumps(template_names, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def get_custom_template_styles(request, user=''):
    request_data = request.GET
    filter_params = {'user': user.id, 'status': 1}
    sku_category = request_data.get('category', '')
    sku_brand = request_data.get('brand', '')
    customer_data_id = request_data.get('customer_data_id', '')
    name = request_data.get('name', '')
    customer_id = ''

    product_properties = ProductProperties.objects.filter(user=user.id, name=name)
    brands_list = product_properties.values_list('brand', flat=True)
    categories_list = product_properties.values_list('category', flat=True)
    sku_master = SKUMaster.objects.exclude(sku_class='').filter(user=user.id, sku_brand__in=brands_list,
                                                                sku_category__in=categories_list)
    if sku_brand and not sku_brand.upper() == 'ALL':
        filter_params['sku_brand'] = sku_brand
    if sku_category and not sku_category.upper() == 'ALL':
        filter_params['sku_category'] = sku_category
    start, stop = 0, None

    sku_master = sku_master.filter(**filter_params)
    size_dict = request_data.get('size_filter', '')
    query_string = 'sku__sku_code'
    if size_dict:
        size_dict = eval(size_dict)
        if size_dict:
            classes = get_sku_available_stock(user, sku_master, query_string, size_dict)
            sku_master = sku_master.filter(sku_class__in=classes)

    sku_master = sku_master.order_by('sequence')
    product_styles = sku_master.values_list('sku_class', flat=True).distinct()
    product_styles = list(OrderedDict.fromkeys(product_styles))
    needed_stock_data = {}
    gen_whs = get_gen_wh_ids(request, user, '')
    needed_stock_data['gen_whs'] = gen_whs
    needed_skus = list(sku_master.only('sku_code').values_list('sku_code', flat=True))
    needed_stock_data['stock_objs'] = dict(StockDetail.objects.filter(sku__user__in=gen_whs, quantity__gt=0,
                                            sku__sku_code__in=needed_skus).only('sku__sku_code', 'quantity').\
                                    values_list('sku__sku_code').distinct().annotate(in_stock=Sum('quantity')))
    needed_stock_data['reserved_quantities'] = dict(PicklistLocation.objects.filter(stock__sku__user__in=gen_whs, status=1,
                                                          stock__sku__sku_code__in=needed_skus).\
                                           only('stock__sku__sku_code', 'reserved').\
                                    values_list('stock__sku__sku_code').distinct().annotate(in_reserved=Sum('reserved')))
    needed_stock_data['enquiry_res_quantities'] = dict(EnquiredSku.objects.filter(sku__user__in=gen_whs,
                                                                                  sku__sku_code__in=needed_skus
                                                                                  ).exclude(warehouse_level=3).\
                                                filter(~Q(enquiry__extend_status='rejected')).\
                                only('sku__sku_code', 'quantity').values_list('sku__sku_code').\
                                annotate(tot_qty=Sum('quantity')))

    needed_stock_data['purchase_orders'] = dict(PurchaseOrder.objects.exclude(status__in=['location-assigned',
                                                                                     'confirmed-putaway']).\
                                          filter(open_po__sku__user=user.id, open_po__sku__sku_code__in=needed_skus).\
                                          values_list('open_po__sku__sku_code').distinct().\
                                            annotate(total_order=Sum('open_po__order_quantity'),
                                                                             total_received=Sum('received_quantity')).\
                                            annotate(tot_rem=F('total_order')-F('total_received')).\
                                            values_list('open_po__sku__sku_code', 'tot_rem'))
    data = get_styles_data(user, product_styles, sku_master, start, stop, request, customer_id='', customer_data_id='',
                           is_file='', needed_stock_data=needed_stock_data)
    return HttpResponse(json.dumps({'data': data}))


@csrf_exempt
@login_required
@get_admin_user
def get_order_labels(request, user=''):
    picklist_number = request.GET.get('picklist_number', 0)
    if not picklist_number:
        return HttpResponse(json.dumps({'message': 'Please send picklist number', 'data': []}))
    picklists = Picklist.objects.filter(Q(stock__sku__user=user.id) | Q(order__user=user.id),
                                        picklist_number=picklist_number,
                                        reserved_quantity__gt=0)

    data = []
    for picklist in picklists:
        if not picklist.order:
            continue
        labels = OrderLabels.objects.filter(order_id=picklist.order_id, status=1).exclude(
            picklist__picklist_number=picklist_number)
        label_count = 0
        mapped_labels = OrderLabels.objects.filter(picklist_id=picklist.id, status=1, order_id=picklist.order_id)
        for map_label in mapped_labels:
            data.append({'label': map_label.label, 'wms_code': map_label.order.sku.sku_code, 'quantity': 1})
            label_count += 1
            if int(picklist.reserved_quantity) == int(label_count):
                break

        for label in labels:
            if int(picklist.reserved_quantity) == int(label_count):
                break
            label.picklist_id = picklist.id
            label.save()
            data.append({'label': label.label, 'wms_code': label.order.sku.sku_code, 'quantity': 1})
            label_count += 1

    return HttpResponse(json.dumps({'message': 'Success', 'data': data}))


@csrf_exempt
@login_required
@get_admin_user
def get_sub_category_styles(request, user=''):
    resp = {'message': 'Success', 'data': []}
    sub_category = request.GET.get('sub_category', '')

    if not sub_category:
        resp['message'] = 'Fail'
        return HttpResponse(json.dumps(resp))
    product_styles = SKUMaster.objects.exclude(sku_class='').filter(user=user.id,
                                                                    sub_category=sub_category).values_list('sku_class',
                                                                                                           flat=True).distinct()

    if not product_styles:
        resp['message'] = 'date empty'
        return HttpResponse(json.dumps(resp))

    sku_data = []
    sku_master = SKUMaster.objects.filter(user=user.id)
    for product in product_styles:
        sku_object = sku_master.filter(sku_class=product)
        sku_styles = sku_object.values('image_url', 'sku_class', 'sku_desc', 'sequence', 'id'). \
            order_by('-image_url')
        sku_data.append(sku_styles[0])

    resp['data'] = sku_data
    return HttpResponse(json.dumps(resp))


def save_custom_order_images(user, request, sku_class):
    path = 'static/images/custom'
    if not os.path.exists(path):
        os.makedirs(path)
    folder = user.id
    if not os.path.exists(path + "/" + str(folder)):
        os.makedirs(path + "/" + str(folder))
    image_data = {}
    if len(request.FILES):
        for file_name, file_data in request.FILES.iteritems():
            extension = file_data.name.split('.')[-1]
            full_filename = os.path.join(path, str(folder), str(sku_class) + "_" + file_name + '.' + str(extension))
            fout = open(full_filename, 'wb+')
            file_content = ContentFile(file_data.read())

            try:
                # Iterate through the chunks.
                file_contents = file_content.chunks()
                for chunk in file_contents:
                    fout.write(chunk)
                fout.close()
                image_data[file_name] = "/" + full_filename
            except:
                print 'not saved'
            print file_name
    return image_data


@csrf_exempt
@login_required
@get_admin_user
def create_custom_skus(request, user=''):
    # it will create new skus and returns the data

    resp = {'message': 'Success', 'data': []}
    data = request.POST.get('model', '')

    if not data:
        resp['message'] = "Fail"
        return HttpResponse(json.dumps(resp))

    order_data = []

    image_data = {}
    image_status = True
    data = json.loads(json.loads(data))
    for size_name, value in data['sizeEnable'].iteritems():
        if value and data['sizeTotals'][size_name]:
            sku = get_incremental(user, "sku_code")
            if image_status:
                image_status = False
                image_data = save_custom_order_images(user, request, sku)
                ''''if data['printEmbroidery']:
                    for place, image in data['print']['places'].iteritems():
                        name = ""
                        if image:
                            name = str(sku)+"_print_"+place
                            image_data['print'][name] = data['print']['placeImgs'][place]
                        data['print']['placeImgs'][place] = name
                    for place, image in data['embroidery']['places'].iteritems():
                        name = ""
                        if image:
                            name = str(sku)+"_emboidery_"+place
                            image_data['embroidery'][name] = data['embroidery']['placeImgs'][place]
                        data['embroidery']['placeImgs'][place] = name
                else:
                    data['print']['placeImgs'] = {}
                    data['embroidery']['placeImgs'] = {}
                '''
                data['image_data'] = image_data
                data['sku_class'] = sku
            for size, quantity in data['sizeValues'][size_name].iteritems():
                if quantity:
                    data_dict = copy.deepcopy(SKU_DATA)
                    data_dict['user'] = user.id
                    data_dict['sku_code'] = "CS" + str(sku) + "-" + size
                    data_dict['wms_code'] = data_dict['sku_code']
                    data_dict['sku_class'] = str(sku) + "-" + size_name
                    fabric = ' Single Fabric ' if data['fabric']['fabric'] else ' Multi Fabric '
                    data_dict['style_name'] = data['style'] + fabric + size_name
                    if data.get('bodyColor', ''):
                        data['style_name'] = data_dict['style_name'] + ' ' + data['bodyColor']
                    data_dict['sku_size'] = size
                    data_dict['sku_type'] = "CS"
                    data_dict['sub_category'] = data['style']

                    sku_desc = size_name + "_" + size
                    if data['bodyStyle'].get('sku_class', ''):
                        sku_desc = data['bodyStyle'].get('sku_class', '') + "_" + sku_desc
                        data_dict['image_url'] = data['bodyStyle'].get('image_url', '')

                    data_dict['sku_desc'] = sku_desc
                    sku_master = SKUMaster(**data_dict)
                    sku_master.save()
                    SKUJson.objects.create(sku_id=sku_master.id, json_data=json.dumps(data))
                    order_data.append({'sku_id': data_dict['sku_code'], 'sku_desc': data_dict['sku_desc'], \
                                       'quantity': quantity, 'extra': data})
    resp['data'] = order_data
    return HttpResponse(json.dumps(resp))


@csrf_exempt
@login_required
@get_admin_user
def insert_enquiry_data(request, user=''):
    log.info("Inserting Enquiry Order: %s" % str(request.POST))
    message = 'Success'
    customer_id = request.user.id
    corporate_name = request.POST.get('name', '')
    remarks = request.POST.get('remarks', '')
    admin_user = get_priceband_admin_user(user)
    enq_limit = get_misc_value('auto_expire_enq_limit', admin_user.id)
    if enq_limit:
        enq_limit = int(enq_limit)
    else:
        enq_limit = 7
    cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    if not cum_obj:
        return "No Customer User Mapping Object"
    cm_id = cum_obj[0].customer_id
    enquiry_id = get_enquiry_id(cm_id)
    cart_items = CustomerCartData.objects.filter(customer_user_id=customer_id)
    if not cart_items:
        return HttpResponse('No Data in Cart')
    items = []
    try:
        customer_details = {}
        customer_details = get_order_customer_details(customer_details, request)
        customer_details['customer_id'] = cm_id  # Updating Customer Master ID
        enquiry_map = {'user': user.id, 'enquiry_id': enquiry_id,
                       'extend_date': datetime.datetime.today() + datetime.timedelta(days=enq_limit),
                       'remarks': remarks}
        if corporate_name:
            enquiry_map['corporate_name'] = corporate_name
        enquiry_map.update(customer_details)
        enq_master_obj = EnquiryMaster(**enquiry_map)
        enq_master_obj.save()
        for cart_item in cart_items:
            if cart_item.quantity <= 0:
                continue
            enquiry_data = {'customer_id': customer_id, 'warehouse_level': cart_item.warehouse_level,
                            'user': user.id, 'quantity': cart_item.quantity, 'sku_id': cart_item.sku.id}
            stock_wh_map = split_orders(**enquiry_data)
            if not stock_wh_map:
                log.info('Stock not present for sku:%s' %cart_item.sku.sku_code)
                continue
            if cart_item.warehouse_level == 3:
                for lt, stc_wh_map in stock_wh_map.items():
                    for wh_code, qty in stc_wh_map.items():
                        if qty <= 0:
                            continue
                        wh_sku_id = get_syncedusers_mapped_sku(wh_code, cart_item.sku.id)
                        enq_sku_obj = EnquiredSku()
                        enq_sku_obj.sku_id = wh_sku_id
                        enq_sku_obj.title = cart_item.sku.style_name
                        enq_sku_obj.enquiry = enq_master_obj
                        enq_sku_obj.quantity = qty
                        tot_amt = get_tax_inclusive_invoice_amt(cm_id, cart_item.levelbase_price, qty,
                                                                user.id, cart_item.sku.sku_code, admin_user)
                        enq_sku_obj.invoice_amount = tot_amt
                        enq_sku_obj.status = 1
                        enq_sku_obj.sku_code = cart_item.sku.sku_code
                        enq_sku_obj.levelbase_price = cart_item.levelbase_price
                        enq_sku_obj.warehouse_level = cart_item.warehouse_level
                        enq_sku_obj.save()
                        block_asn_stock(wh_sku_id, qty, lt, enq_sku_obj, is_enquiry=True)
                        wh_name = User.objects.get(id=wh_code).first_name
                        cont_vals = (customer_details['customer_name'], enquiry_id, wh_name, cart_item.sku.sku_code)
                        contents = {"en": "%s placed an enquiry order %s to %s for SKU Code %s" % cont_vals}
                        users_list = list(set([user.id, wh_code, admin_user.id]))
                        send_push_notification(contents, users_list)
                        items.append([cart_item.sku.style_name, qty, tot_amt])
            else:
                for wh_code, qty in stock_wh_map.items():
                    if qty <= 0:
                        continue
                    wh_sku_id = get_syncedusers_mapped_sku(wh_code, cart_item.sku.id)
                    enq_sku_obj = EnquiredSku()
                    enq_sku_obj.sku_id = wh_sku_id
                    enq_sku_obj.title = cart_item.sku.style_name
                    enq_sku_obj.enquiry = enq_master_obj
                    enq_sku_obj.quantity = qty
                    tot_amt = get_tax_inclusive_invoice_amt(cm_id, cart_item.levelbase_price, qty,
                                                            user.id, cart_item.sku.sku_code, admin_user)
                    enq_sku_obj.invoice_amount = tot_amt
                    enq_sku_obj.status = 1
                    enq_sku_obj.sku_code = cart_item.sku.sku_code
                    enq_sku_obj.levelbase_price = cart_item.levelbase_price
                    enq_sku_obj.warehouse_level = cart_item.warehouse_level
                    enq_sku_obj.save()
                    wh_name = User.objects.get(id=wh_code).first_name
                    cont_vals = (customer_details['customer_name'], enquiry_id, wh_name, cart_item.sku.sku_code)
                    contents = {"en": "%s placed an enquiry order %s to %s for SKU Code %s" % cont_vals}
                    users_list = list(set([user.id, wh_code, admin_user.id]))
                    send_push_notification(contents, users_list)
                    items.append([cart_item.sku.style_name, qty, tot_amt])
    except:
        import traceback
        log.debug(traceback.format_exc())
        message = 'Failed'
    else:
        send_mail_enquiry_order_report(items, enquiry_id, user, customer_details)
        CustomerCartData.objects.filter(customer_user=request.user.id).delete()
    return HttpResponse(message)


# @get_admin_user
def get_enquiry_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    lis = ['enquiry_id','creation_date','Quantity','Amount','Days Left','corporate_name']
    search_params = get_filtered_params(filters, lis)
    is_excel_download = request.POST.get('excel')
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    response_data = {'data': []}
    cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    if not cum_obj:
        return HttpResponse("No Customer User Mapping Object")
    cm_id = cum_obj[0].customer_id
    em_qs = EnquiryMaster.objects.filter(customer_id=cm_id,**search_params)
    if order_data:
        em_qs = EnquiryMaster.objects.filter(customer_id=cm_id).order_by(order_data)
    if search_term:
        em_qs = EnquiryMaster.objects.annotate(full_order=Concat('customer_id','enquiry_id',
                output_field=CharField())).filter(customer_id=cm_id).filter(
                Q(enquiry_id__icontains=search_term) | Q(creation_date__regex=search_term)
                | Q(enquiredsku__sku__sku_code__icontains=search_term) | Q(corporate_name__icontains=search_term)
                | Q(full_order__icontains=search_term),
                 customer_id=cm_id, **search_params).order_by(order_data)
    temp_data['recordsTotal'] = len(em_qs)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    em_vals = em_qs.values_list('enquiry_id', 'extend_status', 'extend_date', 'corporate_name','remarks').distinct()
    total_qty = dict(em_qs.values_list('enquiry_id').distinct().annotate(quantity=Sum('enquiredsku__quantity')))
    total_inv_amt = dict(
        em_qs.values_list('enquiry_id').distinct().annotate(inv_amt=Sum('enquiredsku__invoice_amount')))
    for enq_id, ext_status, ext_date, corp_name, remarks in em_vals[start_index:stop_index]:
        enq_id, ext_status, ext_date, corp_name, remarks = int(enq_id), ext_status, ext_date, corp_name, remarks
        if ext_date:
            days_left_obj = ext_date - datetime.datetime.today().date()
            days_left = days_left_obj.days
        else:
            days_left = 0
        each_total_inv_amt = total_inv_amt[enq_id]
        if each_total_inv_amt:
            each_total_inv_amt = round(each_total_inv_amt, 2)
        else:
            each_total_inv_amt = 0
        if ext_status == 'pending':
            input_label = '<label style="color: #33cc66;">Pending ..</label>'
            input_div = ''
        else:
            input_label = '<a href="" id='+str(int(enq_id))+"_extdate"' class="extend_date_picker" ng-click="showCase.extend_order_date('+str(int(enq_id))+');" style="text-decoration: underline; color: #33cc66;">Extend Date</a>'
            input_div = '<div id='+str(int(enq_id))+"_save"' class="col-lg-12 col-md-12 col-sm-12 hide"><div class="col-lg-6 col-md-6"><input name="extended_date" ui-jq="datepicker" ng-model="showCase.extended_date" placeholder="Select Date" class="form-control stk-readonly" type="text" id="extended_date" data-date-today-highlight="true" data-date-autoclose="true" readonly="true" style="height: 26px;width: 100px !important;"></div><div class="col-lg-6 col-md-6"><button type="button" class="btn btn-primary" style="height: 26px;padding: 2px 5px;" ng-click="showCase.confirm_to_extend('+str(int(enq_id))+');">Save</button></div></div>'
        button = '<button type="button" class="btn btn-warning pull-right" style="min-width: 75px;height: 26px;padding: 2px 5px;" ng-click="orders.moveToCart('+str(int(enq_id))+', $index, $event)" ng-disabled="orders.moving">Move to Cart</button>'
        uniq_enq_id = str(cm_id) + str(enq_id)
        if is_excel_download:
            ord_tuple = (('ID', enq_id), ('Enquiry ID', uniq_enq_id),('Date',get_only_date(request, em_qs.filter(enquiry_id=enq_id)[0].creation_date)),
            ('Quantity',total_qty[enq_id]), ('Amount',each_total_inv_amt), ('Days Left', days_left),('Corporate Name',corp_name))
        else:
            ord_tuple = (('ID', enq_id), ('Enquiry ID', uniq_enq_id),('Date',get_only_date(request, em_qs.filter(enquiry_id=enq_id)[0].creation_date)),
            ('Quantity',total_qty[enq_id]), ('Amount',each_total_inv_amt), ('Days Left', days_left),('Corporate Name',corp_name),
            ('Remarks', remarks),('Extend Date', input_label + input_div), ('Move to Cart', button))
        temp_data['aaData'].append(OrderedDict(ord_tuple))
        temp_data['recordsTotal'] = em_vals.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']




def get_manual_enquiry_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    lis = ['enquiry_id', 'creation_date', 'customer_name', 'sku__sku_class', 'customization_type', 'sku__sku_code', 'status']
    order_data = lis[col_num]
    uniq_ord_search_flag = False
    if order_term == 'desc':
        order_data = '-%s' % order_data
    em_qs = ManualEnquiry.objects.filter(user=request.user.id).order_by(order_data)
    if search_term:
        em_qs = em_qs.filter(
            Q(enquiry_id__icontains=search_term) | Q(creation_date__regex=search_term) |
            Q(customer_name__icontains=search_term) | Q(sku__sku_class__icontains=search_term) |
            Q(customization_type__icontains=search_term) | Q(sku__sku_code__icontains=search_term) |
            Q(status__icontains=search_term)).order_by(order_data)
        if not em_qs.exists():
            uniq_ord_search_flag = True
            em_qs = ManualEnquiry.objects.filter(user=request.user.id).order_by(order_data)
    cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    cm_ids = cum_obj.values_list('customer_id', flat=True)
    orderprefix_map = {}
    user_profile = UserProfile.objects.get(user=user.id)
    admin_user = get_priceband_admin_user(user)
    all_wh_dists_obj = UserGroups.objects.filter(admin_user=admin_user)
    if request.user.userprofile.zone:
        all_wh_dists = all_wh_dists_obj.filter(user__userprofile__zone=request.user.userprofile.zone).values_list('user_id', flat=True)
    else:
        all_wh_dists = all_wh_dists_obj.values_list('user_id', flat=True)
    orderprefix_map = dict(all_wh_dists_obj.values_list('user_id', 'user__userprofile__order_prefix'))
    filter_dict = {'customer_id__in': cm_ids}
    generic_orders = GenericOrderDetailMapping.objects.filter(**filter_dict)
    for enquiry in em_qs[start_index:stop_index]:
        customization_type = '  Price and Product Customization'
        emiza_order_ids = []
        generic_order_id = enquiry.generic_order_id
        if generic_order_id:
            related_order_ids = generic_orders.filter(generic_order_id=generic_order_id).values_list('cust_wh_id', 'orderdetail__original_order_id')
        else:
            related_order_ids = generic_orders.filter(po_number=enquiry.po_number,
                                                      client_name=enquiry.customer_name,
                                                      orderdetail__sku__sku_code=enquiry.sku.sku_code).values_list('cust_wh_id', 'orderdetail__original_order_id')
        for usr , org_id in related_order_ids:
            if usr in orderprefix_map:
                emiza_id = orderprefix_map[usr]+str(org_id)
                emiza_order_ids.append(emiza_id)
        Emiza_ids = list(set(emiza_order_ids))
        #res_map = {'order_id': enquiry.enquiry_id, 'customer_name': enquiry.customer_name,
        #           'date': get_only_date(request, enquiry.creation_date),
        #           'sku_code': enquiry.sku.sku_code, 'style_name': enquiry.sku.sku_class}
        if enquiry.customization_type:
            if enquiry.customization_type == 'price_custom':
                customization_type = 'Price Customization'
        cm_qs = CustomerUserMapping.objects.filter(user=enquiry.user)
        if cm_qs:
            cm_id = cm_qs[0].customer_id
            uniq_enq_id = str(cm_id) + str(enquiry.enquiry_id)
            if uniq_ord_search_flag and search_term not in uniq_enq_id:
                continue
            temp_data['aaData'].append(OrderedDict(
                (('ID', float(enquiry.enquiry_id)), ('Enquiry ID', uniq_enq_id), ('Emiza Order Id', Emiza_ids), ('Enquiry Date', get_only_date(request, enquiry.creation_date)),
              ('Customer Name', enquiry.customer_name), ('Style Name', enquiry.sku.sku_class), ('Customization', customization_type),('SKU Code', enquiry.sku.sku_code), ('Status', enquiry.status))))
        temp_data['recordsTotal'] = em_qs.count()
        temp_data['recordsFiltered'] = temp_data['recordsTotal']

@get_admin_user
def get_customer_enquiry_detail(request, user=''):
    whole_res_map = {}
    response_data_list = []
    sku_wise_details = {}
    enquiry_id = request.GET['enquiry_id']
    cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    filters = {'enquiry_id': float(enquiry_id)}
    if not cum_obj:
        if not request.GET.get('customer_id', ''):
            return HttpResponse("Please Send Customer ID")
        filters['customer_id'] = request.GET.get('customer_id', '')
    else:
        filters['customer_id'] = cum_obj[0].customer_id
    em_qs = EnquiryMaster.objects.filter(**filters)
    if not em_qs:
        return HttpResponse("No Enquiry Data for Id")
    cm_id = em_qs[0].customer_id
    sku_lbprice_map = {}
    sku_tot_qty_map ={}
    sku_tot_inv_map = {}
    for em_obj in em_qs:
        data_vals = list(em_obj.enquiredsku_set.values('sku', 'sku__sku_code', 'sku__image_url',
                                                       'sku__sku_desc', 'quantity', 'levelbase_price',
                                                       'invoice_amount', 'warehouse_level'))
        for data_val in data_vals:
            sku_code = data_val['sku__sku_code']
            qty = data_val['quantity']
            inv_amt = data_val['invoice_amount']
            lb_price = data_val['levelbase_price']
            sub_total = qty * lb_price
            data_val['invoice_amount'] = inv_amt
            data_val['tax_excl_inv_amt'] = sub_total
            if sku_code not in sku_tot_qty_map:
                sku_tot_qty_map[sku_code] = qty
            else:
                sku_tot_qty_map[sku_code] = sku_tot_qty_map[sku_code] + qty
            if sku_code not in sku_tot_inv_map:
                sku_tot_inv_map[sku_code] = sub_total
            else:
                sku_tot_inv_map[sku_code] = sku_tot_inv_map[sku_code] + sub_total
            data_val['level_name'] = get_level_name_with_level(user, data_val['warehouse_level'], users_list=[])

        for sku_code in sku_tot_qty_map:
            sku_lbprice_map[sku_code] = sku_tot_inv_map[sku_code] / sku_tot_qty_map[sku_code]
        tot_amt_inc_taxes = map(sum, [[i['invoice_amount'] for i in em_obj.enquiredsku_set.values()]])[0]
        total_inv_amt = map(sum, [[i['tax_excl_inv_amt'] for i in data_vals]])[0]
        total_tax_amt = round(tot_amt_inc_taxes - total_inv_amt, 2)
        total_qty = map(sum, [[i['quantity'] for i in em_obj.enquiredsku_set.values()]])[0]
        sum_data = {'amount': round(tot_amt_inc_taxes, 2), 'quantity': total_qty}
        cust_id = str(filters['customer_id'])
        enq_id = str(em_obj.enquiry_id)
        uniq_enq_id = cust_id + enq_id
        res_map = {'order_id': uniq_enq_id, 'customer_id': cm_id,
                   'date': get_only_date(request, em_obj.creation_date),
                   'data': data_vals, 'sum_data': sum_data, 'tax': total_tax_amt}
        # res_map['level_name'] = ''
        # if data_vals:
        #     res_map['level_name'] = get_level_name_with_level(user, data_vals[0]['warehouse_level'], users_list=[])
        for sku_rec in data_vals:
            sku_code = sku_rec['sku__sku_code']
            tot_amt = sku_rec['invoice_amount']
            if sku_code not in sku_wise_details:
                sku_qty = sku_rec['quantity']
                sku_el_price = sku_lbprice_map[sku_code]
                sku_wise_details[sku_code] = {'quantity': sku_qty, 'el_price': sku_el_price,
                                              'tot_inc_tax_inv_amt': tot_amt}
            else:
                existing_map = sku_wise_details[sku_code]
                existing_map['quantity'] = existing_map['quantity'] + sku_rec['quantity']
                existing_map['el_price'] = sku_lbprice_map[sku_code]
                existing_map['tot_inc_tax_inv_amt'] = existing_map['tot_inc_tax_inv_amt'] + tot_amt
        response_data_list.append(res_map)
    sku_whole_map = {'data': [], 'totals': {}}
    sku_totals = {'sub_total': 0, 'total_amount': 0, 'tax': 0}
    for sku_code, sku_det in sku_wise_details.items():
        el_price = round(sku_det['el_price'], 2)
        qty = sku_det['quantity']
        total_amt = round(float(qty) * float(el_price), 2)
        tax_amt = sku_det['tot_inc_tax_inv_amt'] - total_amt
        sku_map = {'sku_code': sku_code, 'quantity': qty, 'landing_price': el_price, 'total_amount': total_amt}
        sku_totals['sub_total'] = sku_totals['sub_total'] + total_amt
        sku_totals['tax'] = sku_totals['tax'] + tax_amt
        sku_totals['total_amount'] = sku_totals['sub_total'] + sku_totals['tax']
        sku_whole_map['data'].append(sku_map)
        sku_whole_map['totals'] = sku_totals
    whole_res_map['data'] = response_data_list
    whole_res_map['sku_wise_details'] = sku_whole_map
    whole_res_map['extend_status'] = em_qs[0].extend_status
    whole_res_map['extend_date'] = em_qs[0].extend_date
    return HttpResponse(json.dumps(whole_res_map, cls=DjangoJSONEncoder))


@csrf_exempt
def get_enquiry_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                       filters={}, user_dict={}):
    central_admin_zone = request.user.userprofile.zone
    if user.userprofile.warehouse_type == 'CENTRAL_ADMIN':
        em_qs = EnquiryMaster.objects.all()
    else:
        em_qs = EnquiryMaster.objects.filter(user=user.id)
    for em_obj in em_qs:
        enq_id = str(em_obj.enquiry_id)
        cust_id = str(em_obj.customer_id)
        uniq_enq_id = cust_id + enq_id
        total_qty = map(sum, [[i['quantity'] for i in em_obj.enquiredsku_set.values()]])[0]
        cm_obj = CustomerMaster.objects.get(id=cust_id)
        customer_name = cm_obj.name
        dist_obj = User.objects.get(id=em_obj.user)
        distributor_name = dist_obj.username
        zone = dist_obj.userprofile.zone
        corporate_name = em_obj.corporate_name
        extend_status = em_obj.extend_status
        if central_admin_zone and zone != central_admin_zone:
            continue
        if search_term:
            st = search_term.lower()
            if st not in corporate_name.lower() and st not in distributor_name.lower() and \
                    st not in zone.lower() and str(st) not in str(em_obj.enquiry_id) and \
                    str(st) not in str(extend_status) and str(st) not in cust_id and str(st) not in str(uniq_enq_id):
                continue
        date = em_obj.creation_date.strftime('%Y-%m-%d')
        if em_obj.extend_date:
            days_left_obj = em_obj.extend_date - datetime.datetime.today().date()
            days_left = days_left_obj.days
        else:
            days_left = 0
        temp_data['aaData'].append(OrderedDict((('ID', enq_id), ('Enquiry ID', uniq_enq_id),
                                                ('Sub Distributor', customer_name),
                                                ('Distributor', distributor_name),
                                                ('Customer Name', corporate_name), ('Zone', zone),
                                                ('Quantity', total_qty), ('Date', date),
                                                ('Customer ID', em_obj.customer_id),
                                                ('Extend Status', extend_status), ('Days Left', days_left))))
    temp_data['recordsTotal'] = len(temp_data['aaData'])
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


@get_admin_user
def move_enquiry_to_order(request, user=''):
    message = 'Success'
    enquiry_id = request.POST.get('enquiry_id', '')
    if not enquiry_id:
        return HttpResponse('No enquiry ID')
    changed_data = request.POST.get('changed_data', [])
    if changed_data:
        changed_data = eval(changed_data)
    cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
    if not cum_obj:
        return "No Customer User Mapping Object"
    cm_id = cum_obj[0].customer_id
    delete_flag = True
    admin_user = get_priceband_admin_user(user)
    em_qs = EnquiryMaster.objects.filter(enquiry_id=enquiry_id, customer_id=cm_id)
    try:
        for em_obj in em_qs:
            data_vals = em_obj.enquiredsku_set.values_list('sku', 'quantity', 'levelbase_price', 'warehouse_level')
            for data_val in data_vals:
                sku, quantity, lb_price, warehouse_level = data_val
                for i in changed_data:
                    if i['sku'] == sku and i['warehouse_level'] == warehouse_level:
                        delete_flag = False
                        quantity = int(i['move_quantity'])
                        enq_qs = EnquiredSku.objects.filter(sku=sku, warehouse_level=warehouse_level,
                                                            enquiry_id=em_obj.id)
                        if enq_qs:
                            enq_obj = enq_qs[0]
                            if quantity < enq_obj.quantity:
                                enq_obj.quantity -= quantity
                                enq_obj.invoice_amount = get_tax_inclusive_invoice_amt(cm_id, lb_price, enq_obj.quantity,
                                                                        user.id, enq_obj.sku.sku_code, admin_user)
                                enq_obj.save()
                            else:
                                em_obj.delete()
                sku_id = get_syncedusers_mapped_sku(user.id, sku)
                data = {'user_id': user.id, 'customer_user_id': request.user.id, 'sku_id': sku_id,
                        'tax': 0, 'warehouse_level': warehouse_level, 'levelbase_price': lb_price}
                cart_obj = CustomerCartData.objects.filter(**data)
                if cart_obj:
                    cart_obj = cart_obj[0]
                    cart_obj.quantity += quantity
                    cart_obj.save()
                else:
                    data['quantity'] = quantity
                    customer_cart_data = CustomerCartData(**data)
                    customer_cart_data.save()
    except:
        import traceback
        log.debug(traceback.format_exc())
        message = 'Failed'
    else:
        if delete_flag:
            em_qs.delete()  # Removing item from Enquiry Table after converting it to Order
    return HttpResponse(message)

@get_admin_user
def extend_enquiry_date(request, user = ''):
    message = 'Success'
    users_list = []
    extended_date = request.GET.get('extended_date', '')
    enquiry_id = request.GET.get('order_id', '')
    status = request.GET.get('extend_status','')
    if not enquiry_id:
        enquiry_id = request.GET.get('enquiry_id', '')
    user_profile = UserProfile.objects.filter(user=request.user.id)
    customer_id = request.GET.get('customer_id', '')
    extend_status = request.GET.get('extend_status', 'pending')
    admin_user = get_priceband_admin_user(user)
    if not admin_user:
        admin_user = user
    date_ext_days = int(get_misc_value('auto_expire_enq_limit', admin_user.id)) * 2
    if user_profile[0].warehouse_type == 'CENTRAL_ADMIN' and customer_id:
        cm_id = int(customer_id)
    else:
        cum_obj = CustomerUserMapping.objects.filter(user=request.user.id)
        if not cum_obj and not customer_id:
            message = 'Failed'
        cm_id = cum_obj[0].customer_id
    try:
        enq_qs = EnquiryMaster.objects.filter(enquiry_id=enquiry_id, customer_id=cm_id)
        if enq_qs:
            users_list.append(admin_user.id)
            ext_dt = datetime.datetime.strptime(extended_date, '%m/%d/%Y')
            ct_dtt = enq_qs[0].creation_date
            ct_dt = ct_dtt.replace(tzinfo=None)
            dt_days = ext_dt - ct_dt
            days = dt_days.days
            username = request.user.username
            if user_profile[0].user_type != 'customer':
                if user_profile[0].user_type != 'customer' and request.user.username.lower() == 'sm_admin':
                    reseller = UserProfile.objects.filter(user = enq_qs[0].user)[0].user
                    zonal_admin_id = get_zonal_admin_id(admin_user,reseller)
                    users_list.append(zonal_admin_id)
                else:
                    users_list.append(request.user.id)
                users_list.append(enq_qs[0].user)
                contents = {"en": "%s has %s to  extend date upto %s for order %s"\
                          % (request.user.username, str(status), str(extended_date), str(enquiry_id))}
                if days > date_ext_days and username.lower() != 'sm_admin':
                    return HttpResponse('Admin')
            else:
                zonal_admin_id = get_zonal_admin_id(admin_user,user)
                users_list.append(zonal_admin_id)
                users_list.append(user.id)
                contents = {"en": "%s-%s is requested to extend date upto %s for order %s"\
                          % (request.user.username, request.user.first_name, str(extended_date), str(enquiry_id))}
            enq_qs[0].extend_status = extend_status
            enq_qs[0].extend_date = datetime.datetime.strptime(extended_date, '%m/%d/%Y')
            enq_qs[0].save()
            send_push_notification(contents, users_list)
    except:
        import traceback
        log.debug(traceback.format_exc())
        message = 'Failed'
    return HttpResponse(message)


@csrf_exempt
@login_required
@get_admin_user
def delete_order_charges(request, user=''):
    # It Will delete the other charges for Order.

    status = 1
    message = 'Deleted Successfully'
    log.info('Request Params for Delete Order Charges for user %s is %s' % (user.username, str(request.GET.dict())))
    try:
        data_id = request.GET.get('id', '')
        if data_id:
            other_charges = OrderCharges.objects.filter(id=data_id, user_id=user.id, order_type='order')
            if other_charges:
                other_charges.delete()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Delete Order Charges failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.GET.dict()), str(e)))
        status = 0
        message = 'Order Charges Deletion failed'

    return HttpResponse(json.dumps({'status': status, 'message': message}))

@csrf_exempt
@login_required
@get_admin_user
def order_cancel(request, user=''):
    message = 'Success'
    customer_user = CustomerUserMapping.objects.filter(user_id=request.user.id)
    customer_obj = CustomerMaster.objects.filter(customer_id=customer_user[0].customer.customer_id, user=user.id)
    if not customer_obj:
        message = 'Failed'
        return HttpResponse(message)
    cm_id = customer_obj[0].id
    admin_user = get_priceband_admin_user(user)
    try:
        if admin_user:
            gen_ord_id = request.GET.get('order_id', '')
            if gen_ord_id:
                #qssi push order api call to cancel order
                gen_qs = GenericOrderDetailMapping.objects.filter(generic_order_id=gen_ord_id,
                                                                          customer_id=cm_id)
                generic_orders = gen_qs.values('orderdetail__original_order_id', 'orderdetail__user').distinct()
                for generic_order in generic_orders:
                    original_order_id = generic_order['orderdetail__original_order_id']
                    order_detail_user = User.objects.get(id=generic_order['orderdetail__user'])
                    resp = order_push(original_order_id, order_detail_user, "CANCEL")
                    log.info('Cancel Order Push Status: %s' % (str(resp)))
                #gen_qs = GenericOrderDetailMapping.objects.filter(generic_order_id=gen_ord_id, customer_id=cm_id)
                uploaded_po_details = gen_qs.values('po_number', 'client_name').distinct()
                if uploaded_po_details.count() == 1:
                    po_number = uploaded_po_details[0]['po_number']
                    client_name = uploaded_po_details[0]['client_name']
                    ord_upload_qs = OrderUploads.objects.filter(uploaded_user=request.user.id,
                                                                po_number=po_number, customer_name=client_name)
                    ord_upload_qs.delete()
                order_det_ids = gen_qs.values_list('orderdetail_id', flat=True)
                order_cancel_functionality(order_det_ids)
                gen_qs.delete()
        else:
            central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
            if central_order_mgmt == 'true': # Here user.id is admin id. Bcz all customers are created under admin login only.
                order_id = request.GET.get('order_id', '')
                customer_id = customer_obj[0].customer_id
                whusers = UserGroups.objects.filter(admin_user=user.id).values_list('user').distinct()
                search_params = {'customer_id': customer_id, 'user__in': whusers}
                order_id_search = ''.join(re.findall('\d+', order_id))
                order_code_search = ''.join(re.findall('\D+', order_id))
                order = OrderDetail.objects.filter(Q(order_id=order_id_search, order_code=order_code_search) |
                                                   Q(original_order_id=order_id), **search_params).exclude(status=3)
                order_det_ids = order.values_list('id', flat=True)
                order_cancel_functionality(order_det_ids)
    except:
        import traceback
        log.debug(traceback.format_exc())
        message = 'Failed'
    return HttpResponse(message)


@csrf_exempt
@login_required
@get_admin_user
def intermediate_order_cancel(request, user=''):
    message = 'Success'
    customer_user = CustomerUserMapping.objects.filter(user_id=request.user.id)
    customer_obj = CustomerMaster.objects.filter(customer_id=customer_user[0].customer.customer_id, user=user.id)
    if not customer_obj:
        message = 'Failed'
        return HttpResponse(message)
    cm_id = customer_obj[0].id
    admin_user = get_priceband_admin_user(user)
    interm_order_id = request.GET.get('order_id', '')
    order_filter = {'interm_order_id': interm_order_id,
                    'customer_user_id': request.user.id}
    order_to_delete = IntermediateOrders.objects.filter(**order_filter)
    if order_to_delete:
        order_to_delete.delete()
    else:
        message = 'Failed'
    return HttpResponse(message)


@csrf_exempt
@login_required
@get_admin_user
def add_order_charges(request, user=''):
    order_id = request.POST.get('order_id', '')
    order_charges = eval(request.POST.get('order_charges', ''))
    order_charges_obj = OrderCharges.objects.filter(user=user.id, order_id=order_id, order_type='order')
    data_dict = {}
    data_response = {}
    for obj in order_charges:
        order_charges_obj_present = order_charges_obj.filter(charge_name=obj['charge_name'])
        if order_charges_obj_present:
            order_charges_obj_save = order_charges_obj_present[0]
            order_charges_obj_save.charge_amount = obj['charge_amount']
            order_charges_obj_save.save()
        else:
            data_dict['charge_name'] = obj['charge_name']
            data_dict['charge_amount'] = obj['charge_amount']
            data_dict['order_id'] = order_id
            data_dict['user_id'] = user.id
            data_dict['order_type'] = 'order'
            OrderCharges.objects.create(**data_dict)
    message = "Order Charges Saved Successfully"
    data_response['data'] = order_charges
    data_response['message'] = message
    return HttpResponse(json.dumps(data_response))


def get_manual_enquiry_id(request):
    enq_qs = ManualEnquiry.objects.filter(user=request.user.id).order_by('-enquiry_id')
    if enq_qs:
        enq_id = int(enq_qs[0].enquiry_id) + 1
    else:
        enq_id = 10001
    return enq_id


def save_manual_enquiry_images(request, enq_data, art_work=False):
    image_urls = []
    for file_data in  request.FILES.getlist('po_file'):
        image_data = {'enquiry_id': enq_data.id, 'image': file_data}
        if art_work:
            image_data['image_type'] = 'art_work'
        save_img = ManualEnquiryImages(**image_data)
        save_img.save()
        image_urls.append(str(save_img.image))
    return image_urls


@csrf_exempt
@login_required
@get_admin_user
def place_manual_order(request, user=''):
    try:
        MANUAL_ENQUIRY_DICT = {'customer_name': '', 'sku_id': '', 'customization_type': '', 'quantity': '',
                               'client_po_rate': ''}
        MANUAL_ENQUIRY_DETAILS_DICT = {'ask_price': '', 'expected_date': '', 'remarks': ''}
        manual_enquiry = copy.deepcopy(MANUAL_ENQUIRY_DICT)
        manual_enquiry_details = copy.deepcopy(MANUAL_ENQUIRY_DETAILS_DICT)
        for key, value in MANUAL_ENQUIRY_DICT.iteritems():
            value = request.POST.get(key, '')
            if not value:
                return HttpResponse("Please Fill "+ key)
            if key == 'sku_id':
                sku_data = SKUMaster.objects.filter(user=user.id, sku_class=value)
                if not sku_data:
                    return HttpResponse("Style Not Found")
                value = sku_data[0].id
            elif key == 'quantity':
                value = int(value)
            manual_enquiry[key] = value
        manual_enquiry['status'] = 'new_order'
        for key, value in MANUAL_ENQUIRY_DETAILS_DICT.iteritems():
            value = request.POST.get(key, '')
            if key == 'ask_price' and manual_enquiry['customization_type'] == 'product_custom':
                manual_enquiry_details[key] = 0
                continue
            if not value:
                return HttpResponse("Please Fill "+ key)
            if key == 'ask_price':
                value = float(value)
            elif key == 'expected_date':
                expected_date = value.split('/')
                value = datetime.date(int(expected_date[2]), int(expected_date[0]), int(expected_date[1]))
            manual_enquiry_details[key] = value
        manual_enquiry['custom_remarks'] = request.POST.get('custom_remarks', '')
        check_enquiry = ManualEnquiry.objects.filter(user=request.user.id, sku=manual_enquiry['sku_id'],
                                                     status__in=['', 'approved', 'confirm_order'],
                                                     customer_name=manual_enquiry['customer_name'])
        if check_enquiry:
            return HttpResponse("Manual Enquiry Already Exists")
        manual_enquiry['user_id'] = request.user.id
        manual_enquiry['enquiry_id'] = get_manual_enquiry_id(request)

        sku_variants = request.POST.get('sku_quantity_map', '')
        if sku_variants:
            sku_variants = eval(sku_variants)
            for each_sku, qty in sku_variants.items():
                sku_data = SKUMaster.objects.filter(user=user.id, sku_code=each_sku)
                if not sku_data:
                    return HttpResponse("Style Not Found")
                manual_enquiry['sku_id'] = sku_data[0].id
                manual_enquiry['quantity'] = int(qty)
                enq_data = ManualEnquiry(**manual_enquiry)
                enq_data.save()
        else:
            enq_data = ManualEnquiry(**manual_enquiry)
            enq_data.save()
        manual_enquiry_details['enquiry_id'] = enq_data.enquiry_id
        manual_enquiry_details['order_user_id'] = request.user.id
        manual_enquiry_details['remarks_user_id'] = request.user.id  #Remarks mentioned while placing order will be considered here.
        manual_enq_data = ManualEnquiryDetails(**manual_enquiry_details)
        manual_enq_data.save()
        admin_user = get_priceband_admin_user(user)
        # market_admin_user_id = AdminGroups.objects.get(user_id=admin_user.id).group.user_set.filter(
        #     Q(userprofile__warehouse_type='SM_MARKET_ADMIN')).values_list('id', flat=True)
        # if market_admin_user_id:
        #     market_admin_user_id = market_admin_user_id[0]
        purchase_admin_user_id = AdminGroups.objects.get(user_id=admin_user.id).group.user_set.filter(
            Q(userprofile__warehouse_type='SM_PURCHASE_ADMIN')).values_list('id', flat=True)
        if purchase_admin_user_id:
            purchase_admin_user_id = purchase_admin_user_id[0]
        cont_vals = (request.user.username, request.user.first_name, str(enq_data.enquiry_id), str(enq_data.quantity),
                     str(enq_data.sku.sku_code), enq_data.customer_name)
        contents = {"en": "%s-%s placed a custom order %s of %s Pcs %s for %s" % cont_vals}
        users_list = [user.id, admin_user.id, purchase_admin_user_id]
        marketing_admin_user_id = AdminGroups.objects.get(user_id=admin_user.id).group.user_set.filter(
            Q(userprofile__zone=user.userprofile.zone)).values_list('id', flat=True)
        if marketing_admin_user_id:
            users_list.append(marketing_admin_user_id[0])
        send_push_notification(contents, users_list)
        if request.FILES.get('po_file', ''):
            save_manual_enquiry_images(request, enq_data)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Custom Order Placement failed. User: %s, Params: %s, Error: %s'
                 %(user.username, str(request.POST.dict()), str(e)))
        return HttpResponse("Custom Order Placement failed")
    return HttpResponse("Success")

@csrf_exempt
@login_required
@get_admin_user
def save_manual_enquiry_data(request, user=''):
    try:
        enquiry_id = request.POST.get('enquiry_id', '')
        user_id = request.POST.get('user_id', '')
        enq_status = request.POST.get('enq_status', '')
        admin_remarks = request.POST.get('admin_remarks', '')
        from_flag = request.POST.get('from', '')
        status = request.POST.get('status', '')
        if from_flag == 'pending_approval' and status == 'marketing_pending':  # Changing the status even admin provides remarks
            enq_status = status
        if not enquiry_id or not user_id:
            return HttpResponse("Give information insufficient")
        smd_price = request.POST.get('sm_d_price', 0)
        rc_price = request.POST.get('r_c_price', 0)
        SMD_PRICE_EXCLUDE_STATUSES = ['reseller_pending', 'pending_approval', 'purchase_pending']
        if request.user.userprofile.warehouse_type == 'CENTRAL_ADMIN' and enq_status not in SMD_PRICE_EXCLUDE_STATUSES:
            if not smd_price:
                return HttpResponse('SM-D price is missing')
            smd_price = float(smd_price)
            rc_price = float(rc_price)
        filters = {'enquiry_id': float(enquiry_id), 'user': user_id}
        manual_enq = ManualEnquiry.objects.filter(**filters)
        if not manual_enq:
            return HttpResponse("No Enquiry Data for Id")
        MANUAL_ENQUIRY_DETAILS_DICT = {'ask_price': 0, 'expected_date': '', 'remarks': ''}
        if enq_status:
            manual_enq.update(status=enq_status)
        manual_enq = manual_enq[0]
        if smd_price or rc_price:
            manual_enq.smd_price = smd_price
            manual_enq.rc_price = rc_price
            manual_enq.save()
        ask_price = request.POST.get('ask_price', 0)
        expected_date = request.POST.get('expected_date', '')
        remarks = request.POST.get('remarks', '')
        if admin_remarks == 'true':
            remarks = request.POST.get('admin_remark', '')
        designer_flag = False
        if request.user.userprofile.warehouse_type == "SM_DESIGN_ADMIN":
            designer_flag = True
        if not expected_date and not designer_flag:
            return HttpResponse("Please Fill Expected Date")
        if not remarks:
            return HttpResponse("Please Fill Remarks")
        if manual_enq.customization_type != 'product_custom' and not ask_price and not designer_flag:
            return HttpResponse("Please Fill Price")
        else:
            ask_price = float(ask_price)
        enquiry_data = {'enquiry_id': manual_enq.enquiry_id, 'remarks_user_id': request.user.id,
                        'order_user_id': manual_enq.user_id, 'ask_price': float(ask_price), 'remarks': remarks,
                        'status': status}
        if expected_date:
            expected_date = expected_date.split('/')
            expected_date = datetime.date(int(expected_date[2]), int(expected_date[1]), int(expected_date[0]))
            enquiry_data['expected_date'] = expected_date
        manual_enq_data = ManualEnquiryDetails(**enquiry_data)
        manual_enq_data.save()
        users_list = []
        if request.user.userprofile.warehouse_type in ('SM_MARKET_ADMIN', 'SM_PURCHASE_ADMIN'):
            users_list.append(request.user.id)
            users_list.append(user.id)
        else:
            admin_user = get_priceband_admin_user(user)
            if not admin_user:
                admin_user = request.user
            # market_admin_user_id = AdminGroups.objects.get(user_id=admin_user.id).group.user_set.filter(
            #     Q(userprofile__warehouse_type='SM_MARKET_ADMIN')).values_list('id', flat=True)
            # if market_admin_user_id:
            #     market_admin_user_id = market_admin_user_id[0]
            #     users_list.append(market_admin_user_id)
            users_list.append(admin_user.id)
            if admin_remarks == 'true':
                enq_user = User.objects.get(id=manual_enq_data.order_user_id)
                customer_user = get_customer_parent_user(enq_user)
                temp_group = Group.objects.filter(name=user.username)
                if temp_group and customer_user:
                    zone_user = temp_group[0].user_set.filter(userprofile__zone=customer_user.userprofile.zone)
                    if zone_user:
                        users_list.append(zone_user[0].id)
        if enq_status == 'reseller_pending':
            users_list.append(manual_enq_data.order_user_id)
        else:
            # Adding Zonal Admin for every status update
            try:
                marketing_admin_user_id = AdminGroups.objects.get(user_id=admin_user.id).group.user_set.filter(
                    Q(userprofile__zone=user.userprofile.zone)).values_list('id', flat=True)
                if marketing_admin_user_id:
                    users_list.append(marketing_admin_user_id[0])
            except Exception as e:
                import traceback
                log.info(traceback.format_exc())
                log.info('Users List exception raised')
        custom_message = "%s updated status" % (request.user.first_name)
        message_content = prepare_notification_message(manual_enq, custom_message)
        contents = {"en": message_content}
        send_push_notification(contents, list(set(users_list)))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Save Manual Enquiry Failed. User: %s, Params: %s, Error: %s'
                 %(user.username, str(request.POST.dict()), str(e)))
        return HttpResponse("Manual Enquiry Failed.")
    return HttpResponse("Success")


@csrf_exempt
def get_manual_enquiry_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                       filters={}, user_dict={}):
    try:
        data_filters = {}
        lis = ['enquiry_id', 'customer_name', 'user__username', 'sku__sku_class',
               'customization_type', 'status', 'creation_date']
        special_key = request.POST.get('special_key', '')
        if special_key:
            data_filters['status'] = special_key
            lis = ['enquiry_id', 'customer_name', 'user__username', 'sku__sku_class', 'customization_type', 'creation_date']
        if user.userprofile.warehouse_type != 'CENTRAL_ADMIN':
            data_filters['user'] = user.id
        elif request.user.userprofile.warehouse_type in ('SM_DESIGN_ADMIN'):
            data_filters['customization_type'] = 'price_product_custom'
        elif request.user.userprofile.warehouse_type == 'CENTRAL_ADMIN' and request.user.userprofile.zone != '': # Sub Admins
            distributors = get_same_level_warehouses(2, user)
            zone_code = request.user.userprofile.zone
            distributors = UserProfile.objects.filter(user__in=distributors, zone=zone_code).values_list('user_id',
                                                                                                         flat=True)
            resellers_qs = CustomerUserMapping.objects.filter(customer__user__in=distributors)
            resellers = resellers_qs.values_list('user_id', flat=True)
            data_filters['user__in'] = resellers
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        uniq_ord_search_flag = False
        if search_term:
            if search_term.startswith('ad'):
                search_term = 'pending_approval'
            em_qs = ManualEnquiry.objects.filter(Q(customer_name__icontains=search_term) |
                                                 Q(enquiry_id__icontains=search_term) |
                                                 Q(user__username__icontains=search_term) |
                                                 Q(sku__sku_code__icontains=search_term) |
                                                 Q(sku__sku_class__icontains=search_term) |
                                                 Q(customization_type__icontains=search_term) |
                                                 Q(status__istartswith=search_term),
                                                 **data_filters).order_by(order_data)
            if not em_qs.exists():
                em_qs = ManualEnquiry.objects.filter(**data_filters).order_by(order_data)
                if em_qs.exists():
                    uniq_ord_search_flag = True
        else:
            em_qs = ManualEnquiry.objects.filter(**data_filters).order_by(order_data)
        if request.user.username == 'sm_purchase_admin':
            status = 'Purchase Pending'
        elif request.user.username == 'sm_design_admin':
            status = 'Design Pending'
        elif request.user.username == 'sm_finance_admin':
            status = 'Order Placed'
        else:
            status = 'Remaining Status'
        uniq_orders = []
        for em_obj in em_qs:
            date = em_obj.creation_date.strftime('%Y-%m-%d')
            customization_types = dict(CUSTOMIZATION_TYPES)
            customization_type = customization_types[em_obj.customization_type]
            ord_uniq_key = (em_obj.enquiry_id, em_obj.user.username, em_obj.customer_name)
            if ord_uniq_key not in uniq_orders:
                uniq_orders.append(ord_uniq_key)
            else:
                continue
            if MANUAL_ENQUIRY_STATUS.get(em_obj.status, '') == status or status == 'Remaining Status':
                cm_qs = CustomerUserMapping.objects.filter(user=em_obj.user)
                if cm_qs:
                    cm_id = cm_qs[0].customer_id
                    uniq_enq_id = str(cm_id) + str(em_obj.enquiry_id)
                    if uniq_ord_search_flag and search_term not in uniq_enq_id:
                        continue
                    temp_data['aaData'].append(OrderedDict((('ID', int(em_obj.enquiry_id)), ('Enquiry ID', uniq_enq_id),
                                                            ('Sub Distributor', em_obj.user.username),
                                                            ('Customer Name', em_obj.customer_name),
                                                            ('Style Name', em_obj.sku.sku_class),
                                                            ('Date', date), ('User ID', em_obj.user.id),
                                                            ('Customization Type', customization_type),
                                                            ('status', MANUAL_ENQUIRY_STATUS.get(em_obj.status, ''))
                                                           )))
        temp_data['recordsTotal'] = len(temp_data['aaData'])
        temp_data['recordsFiltered'] = temp_data['recordsTotal']
        temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Save Manual Enquiry Failed. User: %s, Params: %s, Error: %s'
                 % (user.username, str(request.POST.dict()), str(e)))

@get_admin_user
def get_manual_enquiry_detail(request, user=''):
    try:
        from stock_locator import get_quantity_data
        enquiry_id = request.GET.get('enquiry_id', '')
        main_user = user
        user_id = request.GET.get('user_id', '')
        if not enquiry_id or not user_id:
            return HttpResponse("Give information insufficient")
        filters = {'enquiry_id': float(enquiry_id), 'user': user_id}
        manual_enq = ManualEnquiry.objects.filter(**filters)
        if not manual_enq:
            return HttpResponse("No Enquiry Data for Id")
        smd_approved_price = manual_enq[0].smd_price
        rc_price= manual_enq[0].rc_price
        customization_types = dict(CUSTOMIZATION_TYPES)
        customization_type = customization_types[manual_enq[0].customization_type]
        total_qty = manual_enq.aggregate(Sum('quantity'))
        ordered_qty = total_qty.get('quantity__sum', 0)
        cm_qs = CustomerUserMapping.objects.filter(user=manual_enq[0].user)
        if cm_qs:
            cm_id = cm_qs[0].customer_id
            enq_id = str(manual_enq[0].enquiry_id)
            uniq_enq_id = str(cm_id) + enq_id
        manual_eq_dict = {'id': enq_id, 'enquiry_id': uniq_enq_id, 'customer_name': manual_enq[0].customer_name,
                          'date': manual_enq[0].creation_date.strftime('%Y-%m-%d'), 'customization_type': customization_type,
                          'quantity': ordered_qty, 'custom_remarks': manual_enq[0].custom_remarks.split("<<>>"),
                          'enq_status': manual_enq[0].status, 'enq_det_id': int(manual_enq[0].id),
                          'client_po_rate': manual_enq[0].client_po_rate}
        if request.user.userprofile.warehouse_type in ('CENTRAL_ADMIN', 'SM_DESIGN_ADMIN', 'SM_PURCHASE_ADMIN', 'SM_FINANCE_ADMIN'):
            admin_user = user
        else:
            admin_user = get_priceband_admin_user(user)
        dr_price = PriceMaster.objects.filter(sku__user=admin_user.id, sku__sku_code=manual_enq[0].sku.sku_code,
                                              price_type='D-R').filter(min_unit_range__lte=ordered_qty,
                                                                       max_unit_range__gte=ordered_qty)
        if dr_price:
            dr_price = dr_price[0].price
        else:
            dr_price = ''
        manual_eq_dict['dr_price'] = dr_price
        smd_price = PriceMaster.objects.filter(sku__user=admin_user.id, sku__sku_code=manual_enq[0].sku.sku_code,
                                              price_type='SM-D').filter(min_unit_range__lte=ordered_qty,
                                                                       max_unit_range__gte=ordered_qty)
        if smd_price:
            smd_price = smd_price[0].price
        else:
            smd_price = ''
        manual_eq_dict['smd_price'] = smd_price
        emiza_order_ids = []
        if manual_enq[0].status == 'order_placed':
            po_number = manual_enq[0].po_number
            client_name = manual_enq[0].customer_name
            sku_code = manual_enq[0].sku.sku_code
            generic_order_id = manual_enq[0].generic_order_id
            if generic_order_id:
                gen_qs = GenericOrderDetailMapping.objects.filter(generic_order_id=generic_order_id,
                                                                  customer_id=cm_id). values_list(
                    'orderdetail__original_order_id', 'cust_wh_id')
            else:
                gen_qs = GenericOrderDetailMapping.objects.filter(client_name=client_name,
                                                                  po_number=po_number,
                                                                  orderdetail__sku__sku_code=sku_code).values_list(
                    'orderdetail__original_order_id', 'cust_wh_id')
            for ord_id, wh_id in gen_qs:
                emiza_ord_prefix = UserProfile.objects.get(user_id=wh_id).order_prefix
                emiza_ord_id = '%s%s' %(emiza_ord_prefix, ord_id)
                if emiza_ord_id:
                    emiza_order_ids.append(emiza_ord_id)
        manual_eq_dict['EmizaOrderIds'] = ', '.join(emiza_order_ids)
        variants_qty_map = dict(manual_enq.values_list('sku__sku_code', 'quantity'))
        enquiry_images = list(ManualEnquiryImages.objects.filter(enquiry=manual_enq[0].id, image_type='res_images').values_list('image', flat=True))
        art_images = list(ManualEnquiryImages.objects.filter(enquiry=manual_enq[0].id, image_type='art_work').values_list('image', flat=True))
        style_dict = {'sku_code': manual_enq[0].sku.sku_code, 'style_name':  manual_enq[0].sku.sku_class,
                      'description': manual_enq[0].sku.sku_desc, 'images': enquiry_images,
                      'category': manual_enq[0].sku.sku_category, 'art_images': art_images, 'variants_qty': variants_qty_map}
        enquiry_data = ManualEnquiryDetails.objects.filter(enquiry_id=manual_enq[0].enquiry_id, order_user_id=user_id)
        if request.user.id == long(user_id):
            enquiry_data = enquiry_data.filter(status__in=["", "reseller_pending"])
        enquiry_dict = []
        enq_details = {}
        md_approved_details = {}
        for enquiry in enquiry_data:
            date = enquiry.creation_date.strftime('%Y-%m-%d')
            if enquiry.expected_date:
                expected_date = enquiry.expected_date.strftime('%Y-%m-%d')
            else:
                expected_date = ''
            user = UserProfile.objects.get(user=enquiry.remarks_user_id)
            if user.user_type != 'customer':
                if enquiry.status != 'approved' or enquiry.status == 'pending_approved':
                    enq_details = enquiry
                else:
                    md_approved_details = enquiry

            enq_dict = {'ask_price': enquiry.ask_price, 'remarks': enquiry.remarks, 'date': date,
                        'expected_date': expected_date, 'username': user.user.username, 'status': enquiry.status,
                        'sm_d_price': smd_approved_price, 'r_c_price': rc_price}

            if enquiry.status == 'pending_approved':
                enq_dict['smd_price'] = smd_approved_price
                enq_dict['rc_price'] = rc_price

            enquiry_dict.append(enq_dict)
        if enq_details:
            exp_date = enq_details.expected_date
            if exp_date:
                expected_date = exp_date.strftime('%d/%m/%Y')
            else:
                expected_date = ''
            enq_details = {'ask_price': enq_details.ask_price, 'remarks': enq_details.remarks,\
                           'expected_date': expected_date}
        if md_approved_details:
            exp_date = md_approved_details.expected_date
            if exp_date:
                expected_date = exp_date.strftime('%d/%m/%Y')
            else:
                expected_date = ''
            md_approved_details = {'ask_price': md_approved_details.ask_price, 'remarks': md_approved_details.remarks,
                                   'expected_date': expected_date, 'smd_price': smd_approved_price,
                                   'rc_price': rc_price}
        far_wh_lt = 0
        cust_obj = CustomerUserMapping.objects.filter(user_id=user_id)
        if cust_obj:
            dest_user = cust_obj[0].customer.user
            res_lt = cust_obj[0].customer.lead_time
            far_wh_lt = NetworkMaster.objects.filter(dest_location_code_id=dest_user,
                                                     source_location_code__userprofile__warehouse_level=1).aggregate(
                max_lt=Max('lead_time'))['max_lt']
            if not far_wh_lt:
                far_wh_lt = 0
            far_wh_lt += res_lt
        #Get L1, L3 level stocks data
        wh_lists = get_sister_warehouse(main_user)
        wh_users = User.objects.filter(id__in=wh_lists.values_list('user_id', flat=True))
        wh_stock_list = []
        l1_users = wh_users.filter(userprofile__warehouse_level=1)
        for l1_user in l1_users:
            sku_variants = list(manual_enq.values_list('sku__sku_code', flat=True))
            wh_stock = get_quantity_data([l1_user.id], sku_variants, True)
            if wh_stock:
                for x in wh_stock:
                    wh_total = x['available']
                    wh_res = x['reserved']
                    if wh_total == 'No SKU':
                        wh_total = 0
                    wh_open = wh_total - wh_res
                    if wh_open < 0:
                        wh_open = 0
                    wh_blocked = x['blocked']
                    intr_open = x['asn']
                    intr_blocked = x['asn_blocked']
                    sku_code = x['sku_code']
                    wh_stock_list.append({'warehouse': l1_user.username, 'quantity': 0, 'sku_code': sku_code,
                                          'wh_total': wh_open, 'wh_blocked': wh_blocked,
                                          'intr_open': intr_open, 'intr_blocked': intr_blocked})
            else:
                wh_stock_list.append({'warehouse': l1_user.username, 'quantity': 0, 'sku_code': 'No SKU',
                                      'wh_total': 0, 'wh_blocked': 0,
                                      'intr_open': 0, 'intr_blocked': 0})
        wh_stock_dict = {'L1': wh_stock_list}
        return HttpResponse(json.dumps({'data': enquiry_dict, 'style': style_dict, 'order': manual_eq_dict,
                                        'enq_details': enq_details, 'far_wh_leadtime': far_wh_lt,
                                        'wh_stock_dict': wh_stock_dict, 'md_approved_details': md_approved_details,
                                        'status': True}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Get Manual Enquiry Detail failed. User: %s, Params: %s, Error: %s'
                 % (main_user.username, str(request.POST.dict()), str(e)))
        return HttpResponse(json.dumps({'data':'Get Manual Enquiry Detail Failed', 'status': False}))


@csrf_exempt
@login_required
@get_admin_user
def remove_manual_enquiry_image(request, user=''):
    enquiry_id = request.POST.get('enquiry_id', '')
    user_id = request.POST.get('user_id', '')
    image = request.POST.get('image', '')
    if not enquiry_id or not user_id or not image:
        return HttpResponse("Give information insufficient")
    filters = {'enquiry__enquiry_id': float(enquiry_id), 'enquiry__user': user_id, 'image': image}
    image_data = ManualEnquiryImages.objects.filter(**filters)
    if not image_data:
        return HttpResponse("Image Not Found")
    image_data[0].delete()
    return HttpResponse("Success")


@csrf_exempt
@login_required
@get_admin_user
def save_manual_enquiry_image(request, user=''):
    enquiry_id = request.POST.get('enquiry_id', '')
    user_id = request.POST.get('user_id', '')
    resp = {'msg': 'Success', 'data': []}
    if not enquiry_id or not user_id:
        resp['msg'] = "Give information insufficient"
        return HttpResponse(json.dumps(resp))
    filters = {'enquiry_id': float(enquiry_id), 'user': user_id}
    enq_data = ManualEnquiry.objects.filter(**filters)
    enq_det_id = request.POST.get('enq_det_id', '')
    if enq_det_id:
        enq_data = ManualEnquiry.objects.filter(id=enq_det_id)
    if not enq_data:
        resp['msg'] = "No Enquiry Data for Id"
        return HttpResponse(json.dumps(resp))
    enq_data = enq_data[0]
    if request.FILES.get('po_file', ''):
        if request.user.userprofile.warehouse_type == 'SM_DESIGN_ADMIN':
            resp['data'] = save_manual_enquiry_images(request, enq_data, art_work=True)
        else:
            resp['data'] = save_manual_enquiry_images(request, enq_data)
    else:
        resp['msg'] = "Please Select Image"
    return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def notify_designer(request, user=''):
    enquiry_id = request.POST.get('enquiry_id', '')
    user_id = request.POST.get('user_id', '')
    enq_status = request.POST.get('enq_status', '')
    if not enquiry_id or not user_id:
        return HttpResponse("Give information insufficient")
    filters = {'enquiry_id': float(enquiry_id), 'user': user_id}
    manual_enq = ManualEnquiry.objects.filter(**filters)
    if not manual_enq:
        return HttpResponse("No Enquiry Data for Id")
    manual_enq = manual_enq[0]
    if enq_status:
        manual_enq.status = enq_status
        manual_enq.save()
    users_list = []
    if request.user.userprofile.warehouse_type in ('SM_MARKET_ADMIN', 'SM_PURCHASE_ADMIN'):
        users_list.append(request.user.id)
        users_list.append(user.id)
    elif request.user.userprofile.warehouse_type == 'CENTRAL_ADMIN' and request.user.userprofile.zone != '':
        users_list.append(user.id)
    else:
        admin_user = get_priceband_admin_user(user)
        if not admin_user:
            admin_user = request.user
        purchase_admin_user_id = AdminGroups.objects.get(user_id=admin_user.id).group.user_set.filter(
            Q(userprofile__warehouse_type='SM_PURCHASE_ADMIN')).values_list('id', flat=True)
        if purchase_admin_user_id:
            purchase_admin_user_id = purchase_admin_user_id[0]
            users_list.append(purchase_admin_user_id)
        users_list.append(admin_user.id)
    qty = manual_enq.quantity
    sku_code = manual_enq.sku.sku_code
    cust_name = manual_enq.customer_name
    vals = (request.user.username, enquiry_id, qty, sku_code, cust_name)
    contents = {"en": "%s require artwork for custom order %s of %s Pcs %s for %s" % (vals)}
    send_push_notification(contents, users_list)
    return HttpResponse("Success")


@csrf_exempt
@login_required
@get_admin_user
def request_manual_enquiry_approval(request, user=''):
    enquiry_id = request.POST.get('enquiry_id', '')
    user_id = request.POST.get('user_id', '')
    status = request.POST.get('enq_status', '')
    quantity = request.POST.get('quantity', 0)
    resp = {'msg': 'Success', 'data': []}
    if not enquiry_id or not user_id or not status:
        resp['msg'] = "Given information insufficient"
        return HttpResponse(json.dumps(resp))
    smd_price = request.POST.get('sm_d_price', 0)
    rc_price = request.POST.get('r_c_price', 0)
    if request.user.userprofile.warehouse_type == 'CENTRAL_ADMIN' and status != 'pending_approval':
        if not smd_price and not rc_price:
            return HttpResponse('SM-D and R-C prices are missing')
        smd_price = float(smd_price)
        rc_price = float(rc_price)

    if not MANUAL_ENQUIRY_STATUS.get(status, ''):
        resp['msg'] = "status incorrect"
    filters = {'enquiry_id': float(enquiry_id), 'user': user_id}
    enq_data = ManualEnquiry.objects.filter(**filters)
    if not enq_data:
        resp['msg'] = "No Enquiry Data for Id"
        return HttpResponse(json.dumps(resp))
    if quantity:
        enq_data.update(quantity=int(quantity))
    expected_date = request.POST.get('expected_date', '')
    if expected_date or request.user.userprofile.warehouse_type == 'SM_DESIGN_ADMIN':
        save_manual_enquiry_data(request)
    enq_data[0].status = status
    if smd_price or rc_price:
        enq_data[0].smd_price = smd_price
        enq_data[0].rc_price = rc_price
    enq_data[0].save()
    ord_no = enq_data[0].enquiry_id
    qty = enq_data[0].quantity
    sku_code = enq_data[0].sku.sku_code
    cust_name = enq_data[0].customer_name
    users_list = []
    if request.user.userprofile.warehouse_type in ('SM_MARKET_ADMIN', 'SM_PURCHASE_ADMIN', 'SM_DESIGN_ADMIN'):
        users_list.append(request.user.id)
        admin_user = user
        users_list.append(admin_user.id)
    elif request.user.userprofile.warehouse_type == 'CENTRAL_ADMIN' and request.user.userprofile.zone != '':
        admin_user = user
        users_list.append(admin_user.id)
    else:
        admin_user = get_priceband_admin_user(user)
        if not admin_user:
            admin_user = request.user
        purchase_admin_user_id = AdminGroups.objects.get(user_id=admin_user.id).group.user_set.filter(
            Q(userprofile__warehouse_type='SM_PURCHASE_ADMIN')).values_list('id', flat=True)
        if purchase_admin_user_id:
            purchase_admin_user_id = purchase_admin_user_id[0]
            users_list.append(purchase_admin_user_id)
    if request.user.userprofile.warehouse_type not in ('SM_PURCHASE_ADMIN', 'SM_DESIGN_ADMIN'):
        vals = (request.user.username, enq_data[0].enquiry_id, qty, sku_code, cust_name)
        contents_msg = "%s updated the status for custom order %s of %s Pcs %s for %s" %vals
    else:
        if request.user.userprofile.warehouse_type == "SM_PURCHASE_ADMIN":
            contents_msg = "Purchase Admin requesting Designer for ArtWork"
        else:
            vals = (ord_no, qty, sku_code, cust_name)
            contents_msg = "SM Design Admin uploaded artwork for custom order %s of %s Pcs %s for %s" %vals

    contents = {"en": contents_msg}
    users_list.append(enq_data[0].user_id)
    try:
        send_push_notification(contents, list(set(users_list)))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info("Send Push Notification failed and error message is %s" % str(e))
    return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def confirm_or_hold_custom_order(request, user=''):
    resp = {'msg': 'Success', 'data': []}
    cust_order_id = request.POST.get('order_id')
    cust_order_status = request.POST.get('enq_status')
    cust_po_number = request.POST.get('po_number', '')
    ch_map = {'confirm_order': 'Confirmed the Order', 'hold_order': 'Requesting to Block the Stock'}
    try:
        cust_ord_qs = ManualEnquiry.objects.filter(user=request.user.id, enquiry_id=cust_order_id)
        if cust_ord_qs:
            cust_ord_obj = cust_ord_qs[0]
            if cust_ord_obj.status in ['order_placed', 'confirm_order']:
                return HttpResponse('Already Accepted')
            if cust_ord_obj.status != 'approved':
                return HttpResponse('Yet to be approved by Admin')
            cust_ord_obj.status = cust_order_status
            cust_ord_obj.po_number = cust_po_number
            cust_ord_obj.save()
            users_list = []
            admin_user = get_priceband_admin_user(user)
            users_list.append(admin_user.id)
            contents = {"en": "%s  %s  for custom order %s" % ( request.user.username, ch_map[cust_order_status],
                                                                cust_ord_obj.enquiry_id)}
            send_push_notification(contents, users_list)
    except:
        resp['msg'] = 'Fail'
    return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def convert_customorder_to_actualorder(request, user=''):
    log.info("Converting Custom Order To Actual Order for User: %s and Request: %s " % (user.username, str(request.POST.dict())))
    stock_wh_map = {}
    user_id_obj_map = {}
    try:
        warehouse_data = json.loads(request.POST['warehouse_data'])
        remarks_value = request.POST.get('remarks', '')
        for level, warehouse_list in warehouse_data.items():
            for warehouse in warehouse_list:
                if warehouse['quantity']:
                    wh_user_obj = User.objects.get(username=warehouse['warehouse'])
                    stock_wh_map[wh_user_obj.id] = float(warehouse['quantity'])
                    user_id_obj_map[wh_user_obj.id] = wh_user_obj
    except:
        return HttpResponse(json.dumps({'msg': 'Something Went Wrong', 'data': []}))
    resp = {'msg': 'Success', 'data': []}
    try:
        enq_id = request.POST.get('enquiry_id', '')
        res_user_id = request.POST.get('user_id', '')
        en_qs = ManualEnquiry.objects.filter(enquiry_id=enq_id, user_id=res_user_id)
        if not en_qs:
            resp['msg'] = 'Fail'
            return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))
        enq_obj = en_qs[0]
        if enq_obj.status != 'confirm_order':
            return HttpResponse(json.dumps({'msg': 'Either Order is not approved by Admin or Order already Created', 'data': []}))
        sku_id = enq_obj.sku.id
        sku_code = enq_obj.sku.sku_code
        title = enq_obj.sku.sku_desc
        #quantity = enq_obj.quantity
        quantity = en_qs.aggregate(tot_qty=Sum('quantity'))
        if quantity:
            req_stock = quantity['tot_qty']
        corp_name = enq_obj.customer_name
        smd_price = enq_obj.smd_price
        if not smd_price:
            resp['msg'] = 'Fail'
            return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))
        #ask_price_qs = enq_obj.manualenquirydetails_set.values_list('ask_price', flat=True).order_by('-id')
        man_det_qs = ManualEnquiryDetails.objects.filter(enquiry_id=enq_obj.enquiry_id, order_user_id=enq_obj.user.id)
        if man_det_qs:
            ask_price_qs = man_det_qs.values_list('ask_price', flat=True).order_by('-id')
            if ask_price_qs:
                ask_price = ask_price_qs[0]
            exp_date_qs = man_det_qs.values_list('expected_date', flat=True).order_by('-id')
            if not exp_date_qs:
                return HttpResponse(json.dumps({"msg": "Some thing went wrong, please check with team", "data": []}))
            else:
                exp_date = exp_date_qs[0]
                if exp_date < datetime.date.today():
                    exp_date = datetime.date.today()

        cust_qs = CustomerUserMapping.objects.filter(user_id=enq_obj.user)
        if not cust_qs:
            resp['msg'] = 'Fail'
            return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))
        cust_obj = cust_qs[0]
        cm_id = cust_obj.customer.id
        customer_id = cust_obj.customer.customer_id
        customer_name = cust_obj.customer.name
        dist_user_id = cust_obj.customer.user
        admin_user = get_priceband_admin_user(dist_user_id)

        dist_order_copy = {}
        customer_obj = CustomerMaster.objects.filter(id=cm_id)
        if not customer_obj:
            return HttpResponse(json.dumps({'msg': 'Customer Not Found, Something went wrong', 'data': []}))

        cm_id = customer_obj[0].id
        generic_order_id = get_generic_order_id(cm_id)
        dist_user_id = customer_obj[0].user

        customer_user = WarehouseCustomerMapping.objects.filter(warehouse_id=dist_user_id)
        if customer_user:
            dist_order_copy['customer_id'] = customer_user[0].customer.customer_id
            dist_order_copy['customer_name'] = customer_user[0].customer.name
            dist_order_copy['telephone'] = customer_user[0].customer.phone_number
            dist_order_copy['email_id'] = customer_user[0].customer.email_id
            dist_order_copy['address'] = customer_user[0].customer.address

        if req_stock < sum(stock_wh_map.values()):
            resp['msg'] = 'Order has been placed to more quantity'
            return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))
        is_emiza_order_failed = False
        message = ''
        order_objs = []
        order_sku = {}
        for usr, qty in stock_wh_map.items():
            order_code = get_order_prefix(usr)
            if qty <= 0:
                continue
            order_id = get_order_id(usr)  # user.id should be either DL01 or MH01
            org_ord_id = order_code + str(order_id)
            invoice_amount = get_tax_inclusive_invoice_amt(cm_id, smd_price, qty, usr, sku_code, admin_user=admin_user)
            mapped_sku_id = get_syncedusers_mapped_sku(usr, sku_id)

            order_detail_dict = {'sku_id': mapped_sku_id, 'title': title, 'quantity': qty, 'order_id': order_id,
                                 'original_order_id': org_ord_id, 'user': usr,
                                 'shipment_date': exp_date, 'unit_price': smd_price, 'invoice_amount': invoice_amount,
                                 'creation_date': datetime.datetime.now(), 'status': 1,
                                 'order_code': order_code, 'remarks' : remarks_value, 'marketplace': 'Offline'}
            order_detail_dict.update(dist_order_copy)
            ord_qs = OrderDetail.objects.filter(sku_id=mapped_sku_id, order_id=order_id, user=usr)
            if not ord_qs:
                ord_obj = OrderDetail(**order_detail_dict)
                ord_obj.save()
            else:
                ord_obj = ord_qs[0]
                ord_obj.qty = qty
                ord_obj.save()

            corporate_po_number = enq_obj.po_number
            create_grouping_order_for_generic(generic_order_id, ord_obj, cm_id, usr, qty, corporate_po_number,
                                              corp_name, ask_price, ask_price, exp_date)
            usr_sku_master = SKUMaster.objects.filter(user=usr, sku_code=sku_code)
            if usr_sku_master:
                product_type = usr_sku_master[0].product_type
            else:
                log.info('No SKUMaster for user(%s) and sku_code(%s)' % (usr, sku_code))
                product_type = ''
            customer_master = CustomerMaster.objects.get(id=cm_id)
            taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0}
            if customer_master.tax_type:
                inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
                inter_state = inter_state_dict.get(customer_master.tax_type, 2)
                if admin_user:
                    tax_master = TaxMaster.objects.filter(user_id=admin_user, inter_state=inter_state,
                                                          product_type=product_type,
                                                          min_amt__lte=smd_price, max_amt__gte=smd_price)
                else:
                    tax_master = TaxMaster.objects.filter(user_id=usr, inter_state=inter_state,
                                                          product_type=product_type,
                                                          min_amt__lte=smd_price, max_amt__gte=smd_price)
                if tax_master:
                    tax_master = tax_master[0]
                    taxes['cgst_tax'] = float(tax_master.cgst_tax)
                    taxes['sgst_tax'] = float(tax_master.sgst_tax)
                    taxes['igst_tax'] = float(tax_master.igst_tax)
                    taxes['utgst_tax'] = float(tax_master.utgst_tax)
            CustomerOrderSummary.objects.create(order=ord_obj, sgst_tax=taxes['sgst_tax'], cgst_tax=taxes['cgst_tax'],
                                                igst_tax=taxes['igst_tax'], tax_type=customer_master.tax_type)
            upload_po_map = {'uploaded_user_id': enq_obj.user.id, 'po_number': corporate_po_number,
                             'customer_name': enq_obj.customer_name, 'generic_order_id': 0}
            ordupload_obj = OrderUploads.objects.filter(**upload_po_map)
            if ordupload_obj:
                ordupload_obj = ordupload_obj[0]
                ordupload_obj.generic_order_id = generic_order_id
                ordupload_obj.save()

            order_objs.append(ord_obj)
            order_sku.update({ord_obj.sku: qty})
            auto_picklist_signal = get_misc_value('auto_generate_picklist', usr)
            if auto_picklist_signal == 'true':
                message = check_stocks(order_sku, user_id_obj_map[usr], request, order_objs)

            generic_orders = GenericOrderDetailMapping.objects.filter(generic_order_id=generic_order_id,
                                                                      customer_id=cm_id, cust_wh_id=usr). \
                values('orderdetail__original_order_id', 'orderdetail__user').distinct()
            for generic_order in generic_orders:
                original_order_id = generic_order['orderdetail__original_order_id']
                order_detail_user = User.objects.get(id=generic_order['orderdetail__user'])
                try:
                    order_push_status = order_push(original_order_id, order_detail_user, "NEW")
                    log.info('New Order Push Status: %s' % (str(order_push_status)))
                    if order_push_status.get('Status', '') == 'Failure' or order_push_status.get('status', '') == 'Internal Server Error':
                        is_emiza_order_failed = True
                        if order_push_status.get('status', '') == 'Internal Server Error':
                            message = "400 Bad Request"
                        else:
                            message = order_push_status['Result']['Errors'][0]['ErrorMessage']
                        order_detail = OrderDetail.objects.filter(original_order_id=original_order_id,
                                                                  user=order_detail_user.id)
                        picklist_number = order_detail.values_list('picklist__picklist_number', flat=True)
                        if picklist_number:
                            picklist_number = picklist_number[0]
                        check_picklist_number_created(order_detail_user, picklist_number)
                    if generic_order_id and not is_emiza_order_failed:
                        check_and_raise_po(generic_order_id, cm_id)
                except Exception as e:
                    import traceback
                    log.debug(traceback.format_exc())
                    log.info("Order Push failed for order: %s, Error: %s" %(original_order_id, str(e)))

        if not is_emiza_order_failed:
            enq_obj.status = 'order_placed'
            enq_obj.generic_order_id = generic_order_id
            enq_obj.save()
        else:
            log.info("Order Push failed for order:%s : Customer Id:%s : Error: %s" %(generic_order_id, cm_id, message))
            cancel_emiza_order(generic_order_id, cm_id)
            return HttpResponse(json.dumps({'msg': 'Order is not placed properly in Emiza, please check with Stockone Team', 'data': []}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Converting Custom Order to Actual Order Failed. User: %s, Params: %s, Error: %s'
                 % (user.username, str(request.POST.dict()), str(e)))
        return HttpResponse(json.dumps({'msg': 'Converting Custom Order to Actual Order Failed.', 'data': []}))

    return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def convert_customorder_to_enquiryorder(request, user=''):
    resp = {'msg': 'Success', 'data': []}
    smd_price = request.POST.get('sm_d_price', '')
    if smd_price:
        smd_price = float(smd_price)
    rc_price = request.POST.get('r_c_price', '')
    enq_id = request.POST.get('enquiry_id', '')
    res_user_id = request.POST.get('user_id', '')
    en_qs = ManualEnquiry.objects.filter(enquiry_id=enq_id, user_id=res_user_id)
    if not en_qs:
        resp['msg'] = 'Fail'
        return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))
    enq_obj = en_qs[0]
    if enq_obj.status != 'hold_order':
        return HttpResponse('Either Order is not approved by Admin or Order already Created')

    corporate_name = enq_obj.customer_name  # Corporate Name only

    cust_qs = CustomerUserMapping.objects.filter(user_id=enq_obj.user)
    if not cust_qs:
        resp['msg'] = 'Fail'
        return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))
    cust_obj = cust_qs[0]
    cm_id = cust_obj.customer.id
    customer_id = cust_obj.customer.customer_id
    customer_name = cust_obj.customer.name
    dist_user_id = cust_obj.customer.user
    admin_user = get_priceband_admin_user(dist_user_id)
    enq_limit = get_misc_value('auto_expire_enq_limit', admin_user.id)
    if enq_limit:
        enq_limit = int(enq_limit)
    else:
        enq_limit = 7
    enquiry_id = get_enquiry_id(cm_id)
    sku_id = enq_obj.sku.id
    sku_code = enq_obj.sku.sku_code
    title = enq_obj.sku.sku_desc
    quantity = enq_obj.quantity
    req_stock = quantity
    # corp_name = enq_obj.customer_name
    ask_price_qs = enq_obj.manualenquirydetails_set.values_list('ask_price', flat=True).order_by('-id')
    if ask_price_qs:
        ask_price = ask_price_qs[0]
    exp_date_qs = enq_obj.manualenquirydetails_set.values_list('expected_date', flat=True).order_by('-id')
    if exp_date_qs:
        exp_date = exp_date_qs[0]

    items = []
    try:
        customer_details = {}
        customer_details = get_order_customer_details(customer_details, request)
        customer_details['customer_id'] = cm_id  # Updating Customer Master ID
        enquiry_map = {'user': user.id, 'enquiry_id': enquiry_id,
                       'extend_date': datetime.datetime.today() + datetime.timedelta(days=enq_limit)}
        if corporate_name:
            enquiry_map['corporate_name'] = corporate_name
        enquiry_map.update(customer_details)
        enq_master_obj = EnquiryMaster(**enquiry_map)
        enq_master_obj.save()

        stock_wh_map = {}
        source_whs = list(NetworkMaster.objects.filter(dest_location_code_id=dist_user_id).filter(
            source_location_code__username__in=['DL01', 'MH01']).values_list(
            'source_location_code_id', flat=True).order_by('lead_time', 'priority'))
        pick_filter_map = {'picklist__order__user__in': source_whs, 'picklist__order__sku__wms_code': sku_code}
        res_qtys = dict(PicklistLocation.objects.prefetch_related('picklist', 'stock').filter(status=1).filter(
            **pick_filter_map).values_list('stock__sku__user').annotate(total=Sum('reserved')))
        blocked_qtys = dict(EnquiredSku.objects.filter(sku__user__in=source_whs, sku_code=sku_code).filter(
            ~Q(enquiry__extend_status='rejected')).values_list('sku__user').annotate(Sum('quantity')))
        stk_dtl_obj = dict(StockDetail.objects.filter(
            sku__user__in=source_whs, sku__wms_code=sku_code, quantity__gt=0).values_list(
            'sku__user').distinct().annotate(in_stock=Sum('quantity')))
        for source_wh in source_whs:
            avail_stock = stk_dtl_obj.get(source_wh, 0)
            res_stock = res_qtys.get(source_wh, 0)
            blocked_stock = blocked_qtys.get(source_wh, 0)
            if not res_stock:
                res_stock = 0
            if not blocked_stock:
                blocked_stock = 0
            avail_stock = avail_stock - res_stock - blocked_stock
            if avail_stock <= 0:
                continue
            req_qty = req_stock - avail_stock
            if req_qty < avail_stock and req_qty < 0:
                stock_wh_map[source_wh] = avail_stock - abs(req_qty)
                break
            if req_qty >= 0:
                stock_wh_map[source_wh] = avail_stock
            else:
                break
            req_stock = req_qty

        for wh_code, qty in stock_wh_map.items():
            if qty <= 0:
                continue
            wh_sku_id = get_syncedusers_mapped_sku(wh_code, sku_id)
            enq_sku_obj = EnquiredSku()
            enq_sku_obj.sku_id = wh_sku_id
            enq_sku_obj.title = title
            enq_sku_obj.enquiry = enq_master_obj
            enq_sku_obj.quantity = qty
            tot_amt = get_tax_inclusive_invoice_amt(cm_id, ask_price, qty, user.id, sku_code, admin_user)
            enq_sku_obj.invoice_amount = tot_amt
            enq_sku_obj.status = 1
            enq_sku_obj.sku_code = sku_code
            enq_sku_obj.levelbase_price = ask_price
            enq_sku_obj.warehouse_level = 1  # TODO
            enq_sku_obj.save()
            wh_name = User.objects.get(id=wh_code).first_name
            cont_vals = (customer_details['customer_name'], enquiry_id, wh_name, sku_code)
            contents = {"en": "%s placed an enquiry order %s to %s for SKU Code %s" % cont_vals}
            users_list = list(set([user.id, wh_code, admin_user.id]))
            send_push_notification(contents, users_list)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Stock Blocking for Custom Order Failed. User: %s, Params: %s, Error: %s'
                 % (user.username, str(request.POST.dict()), str(e)))
    return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def update_cust_profile(request, user=''):
    resp = {'message': 'success', 'data':[]}
    logo = request.FILES.get('logo', '')
    user_id = request.POST.get('user_id', '')
    first_name = request.POST.get('first_name', '')
    email = request.POST.get('email', '')
    phone_number = request.POST.get('phone_number', '')
    gst_number = request.POST.get('gst_number', '')
    address = request.POST.get('address', '')
    bank_details = request.POST.get('bank_details', '')

    try:
        exe_user_data = User.objects.filter(id=user_id)
        exe_user_data[0].first_name = first_name
        exe_user_data[0].email = email
        exe_user_data[0].save()

        filters = {'user_id': user_id}
        exe_data = UserProfile.objects.filter(**filters)
        if exe_data:
            exe_data = exe_data[0]
            exe_data.phone_number = phone_number
            exe_data.gst_number = gst_number
            exe_data.address = address
            exe_data.bank_details = bank_details
            if logo:
                if exe_data.customer_logo:
                    os.remove(os.path.join(settings.MEDIA_ROOT, exe_data.customer_logo.url))
                exe_data.customer_logo = logo
            exe_data.save()
            data = UserProfile.objects.filter(user_id=user_id)
            resp['data'].append(data[0].customer_logo.url)
    except Exception as e:
        import traceback
        log.info("Error Occurred while updating the Customer Profile data: %s" %traceback.format_exc())
        resp['message'] = 'fail'

    return HttpResponse(json.dumps(resp, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def remove_customer_profile_image(request, user=''):
    try:
        message = 'Success'
        user_id = request.POST.get('user_id', '')
        image = request.POST.get('image', '')
        filters = {'user_id': user_id}
        exe_data = UserProfile.objects.filter(**filters)
        exe_user_data = User.objects.filter(id=user_id)
        if not image:
            return HttpResponse("Image Not Found")
        os.remove(os.path.join(settings.MEDIA_ROOT,image))
        exe_data[0].customer_logo.delete()
    except Exception as e:
        import traceback
        log.info("Error Occurred while Removing the Customer Profile Picture: %s" %traceback.format_exc())
        message = 'fail'
    return HttpResponse(message)

@csrf_exempt
@login_required
@get_admin_user
def print_cartons_data(request, user=''):
    request_dict = dict(request.POST.iterlists())
    company_info = user.userprofile.__dict__
    company_name = user.userprofile.company.company_name
    sel_carton = request.POST.get('sel_carton', '')
    table_headers = ['S.No', 'Carton Number', 'SKU Code', ' SKU Description', 'Quantity']
    address = company_info['address']
    shipment_number = request.POST.get('shipment_number', '')
    shipment_date = get_local_date(user, datetime.datetime.now(), True).strftime("%d %b, %Y")
    truck_number = request.POST.get('truck_number', '')
    courier_name = request.POST.get('courier_name', '')
    selected_carton = request.POST.get('sel_carton', '')
    is_excel = request.POST.get('is_excel', '')
    data = OrderedDict()
    count = 1
    total_quantity = 0
    customers_obj = OrderDetail.objects.select_related('customer_id', 'customer_name', 'marketplace').\
                                filter(id__in=request_dict['id']).only('customer_id', 'customer_name', 'marketplace').\
                                values('customer_id', 'customer_name', 'marketplace', 'address').distinct()
    customer_info = {}
    if customers_obj.count() > 1:
        customer_info = {'name': customers_obj[0]['marketplace']}
    elif customers_obj:
        cust_master = CustomerMaster.objects.filter(user=user.id, customer_id=customers_obj[0]['customer_id'])
        if cust_master:
            customer_info = {'name': cust_master[0].name, 'address': cust_master[0].address}
        else:
            customer_info = {'name': customers_obj[0]['customer_name'], 'address': customers_obj[0]['address']}
    for ind in xrange(0, len(request_dict['sku_code'])):
        pack_reference = request_dict['package_reference'][ind]
        box_num = request_dict['box_num'][ind]
        if pack_reference != selected_carton:
            continue
        sku_code = request_dict['sku_code'][ind]
        title = ''
        order_obj = OrderDetail.objects.select_related('sku__sku_code', 'title').\
                        filter(id=request_dict['id'][ind]).only('sku__sku_code', 'title', 'sku__sku_desc').\
                        values('sku__sku_code', 'title', 'sku__sku_desc')
        if order_obj:
            sku_code = order_obj[0]['sku__sku_code']
            title = order_obj[0]['sku__sku_desc']
        quantity = request_dict['shipping_quantity'][ind]
        try:
            quantity = int(quantity)
            total_quantity = quantity + total_quantity
        except:
            quantity = 0
        grouping_key = '%s:%s' % (str(pack_reference), str(sku_code))
        data.setdefault(grouping_key, [])
        if data[grouping_key]:
            data[grouping_key][4] = int(data[grouping_key][4]) + quantity
            total_quantity = data[grouping_key][4] + total_quantity
        else:
            if not is_excel:
                data[grouping_key] = [count, pack_reference, sku_code, title, quantity]
            else:
                data[grouping_key] = [count, pack_reference, sku_code, title, quantity, shipment_number, shipment_date]
        count+=1
    final_data = {'table_headers': table_headers, 'customer_address': customer_info.get('address', ''),
                  'customer_name': customer_info.get('name', ''), 'name': company_name,
                  'shipment_number': shipment_number, 'company_address': address,
                  'shipment_date': shipment_date, 'company_name': company_name, 'truck_number':truck_number,
                  'courier_name': courier_name, 'data': data.values(), 'total_quantity':total_quantity}
    if not is_excel:
        return render(request, 'templates/toggle/print_cartons_wise_qty.html', final_data)
    else:
        table_headers.extend(('Shipment Number', 'Shipment Date'))
        excel_headers = ''
        temp_data = {}
        temp_data['aaData'] = [final_data]
        excel_name = 'shipment_carton_excel'
        if temp_data['aaData']:
            excel_headers = temp_data['aaData'][0].keys()
        file_name = "%s.%s" % (user.id, excel_name.split('=')[-1])
        file_type = 'xls'
        path = ('static/excel_files/%s.%s') % (file_name, file_type)
        if not os.path.exists('static/excel_files/'):
            os.makedirs('static/excel_files/')
        path_to_file = '../' + path
        wb, ws = get_work_sheet('skus', table_headers)
        data_count = 0
        for data in temp_data['aaData']:
            data_count += 1
            column_count = 0
            for list_obj in data['data']:
                for value in list_obj:
                    ws.write(data_count, column_count, value)
                    column_count += 1
        wb.save(path)
        return HttpResponse(json.dumps({'path' : path_to_file}))

@csrf_exempt
@login_required
@get_admin_user
def print_cartons_data_view(request, user=''):
    table_headers = ['S.No', 'Carton Number', 'SKU Code', 'SKU Description', 'Quantity']
    customer_id = request.GET.get('customer_id', '')
    shipment_number = request.GET.get('shipment_number', '')
    selected_carton = request.GET.get('sel_carton', '')
    data = OrderedDict()
    customer_info = {}
    truck_number = ''
    courier_name = ''

    company_info = user.userprofile.__dict__
    company_name = user.userprofile.company.company_name
    address = company_info['address']
    shipment_date = get_local_date(user, datetime.datetime.now(), True).strftime("%d %b, %Y")
    shipment_orders = ShipmentInfo.objects.filter(order__customer_id=customer_id,
                                                  order_shipment__shipment_number=shipment_number,
                                                  order_packaging__package_reference=selected_carton,
                                                  order_shipment__user=user.id)
    customers_obj = shipment_orders.values('order__customer_id', 'order__customer_name', 'order__marketplace', 'order__address').\
                                    distinct()
    if customers_obj.count() > 1:
        customer_info = {'name': customers_obj[0]['order__marketplace']}
    elif customers_obj:
        cust_master = CustomerMaster.objects.filter(user=user.id, customer_id=customers_obj[0]['order__customer_id'])
        if cust_master:
            customer_info = {'name': cust_master[0].name, 'address': cust_master[0].address}
        else:
            customer_info = {'name': customers_obj[0]['order__customer_name'],
                             'address': customers_obj[0]['order__address']}
    count = 1
    for orders in shipment_orders:
        pack_reference = orders.order_packaging.package_reference
        sku_code = orders.order.sku.sku_code
        if pack_reference != selected_carton:
            continue
        if not truck_number:
            truck_number = orders.order_shipment.truck_number
            shipment_date = get_local_date(user, orders.order_shipment.creation_date, True).strftime("%d %b, %Y")
        if not courier_name:
            courier_name = orders.order_shipment.courier_name
        title = orders.order.sku.sku_desc
        quantity = int(orders.shipping_quantity)
        grouping_key = '%s:%s' % (str(pack_reference), str(sku_code))
        data.setdefault(grouping_key, [])
        if data[grouping_key]:
            data[grouping_key][4] = int(data[grouping_key][4]) + quantity
        else:
            data[grouping_key] = [count, pack_reference, sku_code, title, quantity]
        count += 1

    final_data = {'table_headers': table_headers, 'customer_address': customer_info.get('address', ''),
                  'customer_name': customer_info.get('name', ''), 'name': company_name,
                  'shipment_number': shipment_number, 'company_address': address,
                  'shipment_date': shipment_date, 'company_name': company_name, 'truck_number':truck_number,
                  'courier_name': courier_name, 'data': data.values()}
    return render(request, 'templates/toggle/print_cartons_wise_qty.html', final_data)


@csrf_exempt
@get_admin_user
def create_orders_check_ean(request, user=''):
    data = {}
    sku_code = ''
    ean = request.GET.get('ean')
    try:
        sku_obj = SKUMaster.objects.filter(sku_code=ean, user=user.id)
        if sku_obj.exists():
            sku_code = sku_obj[0].sku_code
        elif not sku_code:
            sku_obj = SKUMaster.objects.filter(ean_number=ean, user=user.id)
            if sku_obj.exists():
                sku_code = sku_obj[0].sku_code
        elif not sku_code:
            sku_obj = SKUMaster.objects.filter(eannumbers__ean_number=ean, user=user.id)
            if sku_obj.exists():
                sku_code = sku_obj[0].sku_code
    except:
        sku_obj = SKUMaster.objects.filter(sku_code=ean, user=user.id)
        if sku_obj:
            sku_code = sku_obj[0].sku_code
    return HttpResponse(json.dumps({ 'sku' : sku_code }))


@csrf_exempt
def get_stock_transfer_order_level_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, st_type=''):
    lis = ['order_id', 'st_po__open_st__warehouse__username', 'order_id', 'date_only','tsum']
    users = [user.id]
    users = check_and_get_plants(request, users)
    user_ids = list(users.values_list('id', flat=True))
    if user.username == 'mhl_admin':
        stock_transfer_objs = StockTransfer.objects.filter(status=1, st_type=st_type, upload_type='UI').\
                                        values('st_po__open_st__sku__user', 'order_id',
                                               'st_po__open_st__warehouse__username', 'sku__user').\
                                        distinct().annotate(tsum=Sum('quantity'), tpicked=Sum('picked_quantity'), toriginal_qty=Sum('original_quantity'),
                                        date_only=Cast('creation_date', DateField()))
    else:
        stock_transfer_objs = StockTransfer.objects.filter(sku__user__in=user_ids, status=1, st_type=st_type, upload_type='UI').\
                                        values('st_po__open_st__sku__user', 'order_id',
                                               'st_po__open_st__warehouse__username', 'sku__user').\
                                        distinct().annotate(tsum=Sum('quantity'), tpicked=Sum('picked_quantity'), toriginal_qty=Sum('original_quantity'),
                                        date_only=Cast('creation_date', DateField()))
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        user_ids = User.objects.filter(username__icontains=search_term).values_list('id', flat=True)
        master_data = stock_transfer_objs.filter(Q(st_po__open_st__sku__user__in=user_ids) |
                                                   Q(tsum__icontains=search_term) | Q(order_id__icontains=search_term)).order_by(order_data)
    else:
        master_data = stock_transfer_objs.order_by(order_data)
    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    count = 0

    for data in master_data[start_index:stop_index]:
        checkbox = '<input type="checkbox" name="order_id" value="%s">' % data['order_id']
        source_name = User.objects.get(username=data['st_po__open_st__warehouse__username'])
        warehouse = User.objects.get(id=data['st_po__open_st__sku__user'])
        temp_data['aaData'].append({'': checkbox, 'Warehouse Name': warehouse.username,
                                    'warehouse_label': "%s %s" % (warehouse.first_name, warehouse.last_name),
                                    'source_label': "%s %s" % (source_name.first_name, source_name.last_name),
                                    'Stock Transfer ID': data['order_id'],
                                    'Quantity': data['toriginal_qty'], 'Pending Qty': data['tsum'], 'Creation Date': data['date_only'].strftime("%d %b, %Y"),
                                    'DT_RowClass': 'results', 'source_wh': data['st_po__open_st__warehouse__username'],
                                    'warehouse_id': data['sku__user'],
                                    'DT_RowAttr': {'id': data['order_id']}, 'id': count})
        count = count + 1


@csrf_exempt
@get_admin_user
def get_stock_transfer_order_details(request, user=''):
    """ Get Stock Transfer Order Details"""

    order_id = request.GET.get('order_id', '')
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    search_params = {'quantity__gt': 0}
    warehouse_id = request.GET['warehouse_id']
    user = User.objects.get(id=warehouse_id)
    stock_params = {}
    if from_date:
        from_date = from_date.split('/')
        search_params['creation_date__gte'] = datetime.date(int(from_date[2]), int(from_date[0]), int(from_date[1]))
        stock_params['creation_date__gte'] = search_params['creation_date__gte']
    if to_date:
        to_date = to_date.split('/')
        to_date = datetime.date(int(to_date[2]), int(to_date[0]), int(to_date[1]))
        to_date = datetime.datetime.combine(to_date + datetime.timedelta(1), datetime.time())
        search_params['creation_date__lt'] = to_date
        stock_params['creation_date__lt'] = to_date
    order_details_data = []
    wh_details = {}
    order_date = ''
    order_details = StockTransfer.objects.filter(sku__user=user.id, status=1, order_id=order_id)
    for one_order in order_details:
        received, consumed, adjusted, opening_stock, closing_stock = 0, 0, 0, 0, 0
        #sku_stats = {}
        warehouse = User.objects.get(id=one_order.st_po.open_st.sku.user)
        if from_date or to_date:
            stock_stats = StockStats.objects.filter(sku__sku_code=one_order.sku.sku_code, sku__user=warehouse.id,
                                                    **stock_params)
            if stock_stats.exists():
                opening_stock = stock_stats.first().opening_stock
                closing_stock = stock_stats.last().closing_stock
            #sku_stats = dict(SKUDetailStats.objects.filter(sku__sku_code=one_order.sku.sku_code,
            #                                                sku__user=warehouse.id, **search_params).\
            #                 values_list('transact_type').distinct().annotate(tsum=Sum('quantity')))
            stock_stat_vals = stock_stats.aggregate(received=Sum('receipt_qty'), produced=Sum('produced_qty'),
                                                    returned=Sum('return_qty'), uploaded=Sum('uploaded_qty'),
                                                    dispatched=Sum('dispatch_qty'), consumed=Sum('consumed_qty'),
                                                    adjusted=Sum('adjustment_qty'))
            if not stock_stat_vals['received']:
                stock_stat_vals['received'] = 0
            if not stock_stat_vals['produced']:
                stock_stat_vals['produced'] = 0
            if not stock_stat_vals['returned']:
                stock_stat_vals['returned'] = 0
            if not stock_stat_vals['dispatched']:
                stock_stat_vals['dispatched'] = 0
            if not stock_stat_vals['consumed']:
                stock_stat_vals['consumed'] = 0
            if not stock_stat_vals['adjusted']:
                stock_stat_vals['adjusted'] = 0
            received = stock_stat_vals['received'] + stock_stat_vals['produced'] + stock_stat_vals['returned']
            consumed = stock_stat_vals['dispatched'] + stock_stat_vals['consumed']
            adjusted = stock_stat_vals['adjusted']
        #received = sku_stats.get('PO', 0) + sku_stats.get('return', 0) + sku_stats.get('inventory-upload', 0) + \
        #           sku_stats.get('jo', 0)
        #consumed = sku_stats.get('picklist', 0) + sku_stats.get('rm_picklist', 0)
        #adjustment = sku_stats.get('inventory-adjustment', 0)
        total_stock = opening_stock + received
        order_id = one_order.order_id
        sku = one_order.sku
        unit_price = one_order.invoice_amount/one_order.quantity
        order_details_data.append(
            {'product_title': sku.sku_desc, 'quantity': one_order.quantity,
             'invoice_amount': one_order.invoice_amount, 'item_code': sku.sku_code,
             'order_id': order_id,
             'unit_price': unit_price, 'opening_stock': opening_stock, 'received': received,
             'total_stock': total_stock, 'consumed': consumed, 'closing_stock': closing_stock,
             'adjusted': adjusted})
    if order_details:
        warehouse = order_details[0].st_po.open_st.warehouse
        order_date = get_local_date(user, order_details[0].creation_date)
        pincode = ''
        if warehouse.userprofile.pin_code:
            pincode = warehouse.userprofile.pin_code
        wh_details = {'name': "%s %s"%(warehouse.first_name, warehouse.last_name), 'city': warehouse.userprofile.city,
                      'pincode': pincode, 'address': warehouse.userprofile.address,
                      'state': warehouse.userprofile.state}

    return HttpResponse(json.dumps({'data_dict': order_details_data, 'wh_details': wh_details,
                                    'order_date': order_date}))


@csrf_exempt
@login_required
@get_admin_user
def update_stock_transfer_data(request, user=""):
    """ This code will update data if stock transfer order is updated """
    st_time = datetime.datetime.now()
    log.info("updation of order process started")
    myDict = dict(request.POST.iterlists())
    log.info('Stock Transfer Order update request params for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        order_id = myDict['order_id'][0]
        for i in range(0, len(myDict['item_code'])):
            sku_code = myDict['item_code'][i]
            stock_transfer_obj = StockTransfer.objects.filter(sku__user=user.id, status=1, order_id=order_id,
                                         sku__sku_code=sku_code)
            if stock_transfer_obj:
                stock_transfer_obj = stock_transfer_obj[0]
                stock_transfer_obj.quantity = myDict['quantity'][i]
                stock_transfer_obj.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Order failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
        return HttpResponse("Update Order Failed")
    return HttpResponse("Success")


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def stock_transfer_generate_picklist(request, user=''):
    reversion.set_user(request.user)
    enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
    out_of_stock = []
    picklist_number = get_picklist_number(user)
    picklist_exclude_zones = get_exclude_zones(user)
    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                   'fifo_switch': get_misc_value('fifo_switch', user.id),
                   'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                   'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id),
                   'allow_partial_picklist': get_misc_value('allow_partial_picklist', user.id)}
    seller_stocks = SellerStock.objects.filter(seller__user=user.id, stock__quantity__gt=0).values('stock_id', 'seller_id')
    for key, value in request.POST.iteritems():
        if key == 'enable_damaged_stock':
            continue
        warehouse_id = value
        user = User.objects.get(id=value)
        if enable_damaged_stock == 'true':
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id,
                                                                                        quantity__gt=0,
                                                                                        location__zone__zone__in=[
                                                                                            'DAMAGED_ZONE'])
        else:
            sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').exclude(
                location__zone__zone__in=picklist_exclude_zones).filter(sku__user=user.id, quantity__gt=0)
        if switch_vals['fifo_switch'] == 'true':
            stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').order_by(
                'receipt_date')
            stock_detail2 = sku_stocks.order_by('receipt_date')
        else:
            stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).order_by(
                'location_id__pick_sequence')
            stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).order_by(
                'receipt_date')
        sku_stocks = stock_detail1 | stock_detail2
        orders_data = StockTransfer.objects.filter(order_id=key, status=1, sku__user=user.id)
        if orders_data and orders_data[0].st_seller:
            seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(orders_data[0].st_seller_id),
                                       seller_stocks)
            if seller_stock_dict:
                sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
                sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
            else:
                sku_stocks = sku_stocks.filter(id=0)
        stock_status, picklist_number = picklist_generation(orders_data, enable_damaged_stock, picklist_number, user,
                                                            sku_combos, sku_stocks, switch_vals)

        if stock_status:
            out_of_stock = out_of_stock + stock_status

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    check_picklist_number_created(user, picklist_number + 1)
    order_status = ''
    data, sku_total_quantities, courier_name = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']

    return HttpResponse(json.dumps({'data': data, 'picklist_id': picklist_number + 1, 'stock_status': stock_status,
                                    'order_status': order_status, 'warehouse_id': warehouse_id}))


"""
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
"""
def create_mail_attachments(f_name, html_data):
    html_data = html_data.encode('utf-8').strip()
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

@csrf_exempt
@login_required
@get_admin_user
def get_create_order_mapping_values(request, user=''):
    wms_code = request.GET['wms_code']
    sku_supplier = {}
    data = {}
    if wms_code:
        sku_code_obj = SKUMaster.objects.filter(wms_code=wms_code, user=user.id)
        if sku_code_obj:
            sku_supplier = list(sku_code_obj.values('wms_code', 'price'))
    return HttpResponse(json.dumps(sku_supplier), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def invoice_mark_delivered(request, user=''):
    try:
        order_id = request.POST.getlist('selected_invoice', [])
        selected_order_invoice = eval(request.POST.get('selected_invoice', '{}'))
        failed_order_id = []
        order_id_already_marked_delivered = []
        group_picked_dict = {}
        for sel_inv in selected_order_invoice:
            group_picked_dict.setdefault(sel_inv['order_id'], 0)
            group_picked_dict[sel_inv['order_id']] += float(sel_inv['picked_qty'])
        for obj in selected_order_invoice:
            picked_qty = group_picked_dict[obj['order_id']] #obj['picked_qty']
            order_qty = obj['order_qty']
            invoice_id = obj['invoice_id']
            sor_id = obj['order_id']
            if order_qty != picked_qty:
                failed_order_id.append(sor_id)
                continue
                #return HttpResponse(json.dumps({'status':False, 'message':'Partial Picked Qty Not Allowed'}), content_type='application/json')
            sell_ids = {}
            ids = obj['id']
            invoice_no = obj['invoice_number']
            sell_ids['order__user'] = user.id
            sell_ids['order__original_order_id'] = sor_id
            if invoice_id:
                sell_ids['invoice_number'] = invoice_id
            sell_ids['delivered_flag'] = 0
            #sell_ids['quantity'] = order_qty
            seller = SellerOrderSummary.objects.filter(**sell_ids)
            if len(seller):
                if seller.aggregate(Sum('quantity'))['quantity__sum'] == picked_qty:
                    if seller.filter(delivered_flag=2):
                        order_id_already_marked_delivered.append(sor_id)
                    else:
                        seller.update(delivered_flag=1)
                else:
                    failed_order_id.append(sor_id)
                return HttpResponse(json.dumps({'status':True, 'message':'Marked as Delivered Successfully', 'already_marked_delivered' : order_id_already_marked_delivered}), content_type='application/json')
            else:
                failed_order_id.append(sor_id)
                continue
        if len(failed_order_id):
            failed_order_ids = ', '.join(failed_order_id)
            return HttpResponse(json.dumps({'status':False, 'message':'Failed for '+failed_order_ids + ', Other Orders Successfully Marked as Delivered'}), content_type='application/json')
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Marking as delivered for order failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse(json.dumps({'status': False, 'message': 'Mark as delivered Failed'}),
                            content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def get_ratings_data_popup(request, user=''):
    request_data = request.POST
    customer_name = request.user.get_full_name()
    customer_id = request.user.id
    username = request.user.username
    original_order_id = ''
    #seller = SellerOrderSummary.objects.filter(order__user=user.id, order__customer_id = customer_id, order__customer_name = customer_name, delivered_flag=1).order_by('-updation_date').first()
    seller_obj = SellerOrderSummary.objects.filter(order__user=user.id, order__customer_name = customer_name, delivered_flag=1).order_by('-updation_date').first()
    if seller_obj:
        original_order_id = seller_obj.order.original_order_id
        if not original_order_id:
            order_id = str(seller_obj.order.order_id)
            order_code = str(seller_obj.order.order_code)
            original_order_id = order_id + order_code
        seller = SellerOrderSummary.objects.filter(order__user=user.id, order__customer_name = customer_name, order__original_order_id = original_order_id, delivered_flag=1).order_by('-updation_date')
        data_dict = {}
        for obj in seller:
            data_dict['order_id'] = original_order_id
            creation_date = obj.creation_date
            updation_date = obj.updation_date
            data_dict['order_creation_date'] = str(creation_date)
            data_dict['order_updation_date'] = str(updation_date)
            #seller_order.seller.order.sku
            #quantity = obj.quantity
            #customer_name = obj.order.customer_name
            #original_order_id = obj.order.original_order_id
            #if not original_order_id:
                #order_id = str(obj.order.order_id)
                #order_code = str(obj.order.order_code)
                #original_order_id = order_id + order_code
            sku_code = obj.order.sku.sku_code
            sku_desc = obj.order.sku.sku_desc
            data_dict.setdefault('items', [])
            sku_dict = {}
            sku_dict['sku_code'] = obj.order.sku.sku_code
            sku_dict['sku_desc'] = obj.order.sku.sku_desc
            sku_dict['remarks'] = ''
            data_dict['items'].append(sku_dict)
        return HttpResponse(json.dumps({'status':True, 'data' : data_dict}), content_type='application/json')
    else:
        return HttpResponse(json.dumps({'status':True, 'data' : {}}), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def save_cutomer_ratings(request, user=''):
    try:
        warehouse_user = user.id
        order_rate = request.POST.get('order_rate', '')
        product_rate = request.POST.get('product_rate', '')
        order_reason = request.POST.get('order_reason', '')
        product_reason = request.POST.get('product_reason', '')
        order_ratings_data = eval(request.POST.get('order_details', '{}'))
        customer_name = request.user.get_full_name()
        original_order_id = order_ratings_data['order_id']
        items = order_ratings_data['items']
        seller = SellerOrderSummary.objects.filter(order__user=warehouse_user, order__customer_name=customer_name, order__original_order_id=original_order_id, delivered_flag=1).update(delivered_flag=2)
        rating_obj = RatingsMaster.objects.create(user=user, original_order_id=original_order_id, rating_product=product_rate, rating_order=order_rate, reason_product=product_reason, reason_order=order_reason)
        if rating_obj:
            for obj in items:
                sku_obj = SKUMaster.objects.filter(sku_code = obj['sku_code'], user = user.id)
                if sku_obj:
                    RatingSKUMapping.objects.create(rating=rating_obj, sku_id=sku_obj[0].id, remarks=obj['remarks'])
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Save Customer Ratings failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse(json.dumps({'status': False}), content_type='application/json')
    return HttpResponse(json.dumps({'status':True}), content_type='application/json')

"""
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
"""

def list_notifications(request):
    resp = {'msg': 'Success', 'data': []}
    push_notifications = PushNotifications.objects.filter(user=request.user.id).order_by('-id')
    push_nots = []
    for push_not in push_notifications:
        push_map = {'message': push_not.message, 'is_read': push_not.is_read,
                    'creation_date': push_not.creation_date.strftime("%d %b %Y"), 'id': push_not.id}
        push_nots.append(push_map)

    resp['data'] = push_nots
    return HttpResponse(json.dumps(resp), content_type='application/json')


@csrf_exempt
@login_required
def make_notifications_read(request):
    resp = {'msg': 'Success', 'data': []}
    is_all_read = request.POST.get('is_all_read', '')
    push_id = request.POST.get('push_id', '')
    if not is_all_read and not push_id:
        return HttpResponse('Either push_id or is_all_read should be sent')
    else:
        try:
            if is_all_read == 'true':
                PushNotifications.objects.filter(user=request.user.id).update(is_read=True)
            else:
                PushNotifications.objects.filter(id=push_id).update(is_read=True)
        except:
            resp['msg'] = 'Fail'
    return HttpResponse(json.dumps(resp), content_type='application/json')


@csrf_exempt
@login_required
def delete_notification(request):
    resp = {'msg': 'Success', 'data': []}
    notification_id = request.POST.get('notification_id', '')
    if not notification_id:
        return HttpResponse('Provide Notification ID')
    else:
        try:
            PushNotifications.objects.filter(id=notification_id).delete()
        except:
            resp['msg'] = 'Fail'
    return HttpResponse(json.dumps(resp), content_type='application/json')

@csrf_exempt
def get_stock_transfer_shipment_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters):
    stock_transfer_dict = {}
    sort_column_list = ['order_id', 'order_id', 'st_po__open_st__warehouse__username', 'ordered', 'ordered',
                        'date_only']
    stock_transfer_dict['sku__user'] = user.id
    stock_transfer_dict['status'] = 2
    filter_dict = eval(filters)
    if filter_dict['stock_transfer_id']:
        stock_transfer_dict['order_id'] = filter_dict['stock_transfer_id']
    if filter_dict['from_date']:
        from_date = datetime.datetime.strptime(filter_dict['from_date'], '%m/%d/%Y')
        stock_transfer_dict['creation_date__gte'] = from_date
    if filter_dict['to_date']:
        to_date = datetime.datetime.strptime(filter_dict['to_date'], '%m/%d/%Y')
        stock_transfer_dict['creation_date__lte'] = to_date
    sort_data = sort_column_list[col_num]
    if order_term == 'desc':
        sort_data = '-%s' % sort_data
    stock_transfer_objs = StockTransfer.objects.filter(**stock_transfer_dict)
    stock_transfers = stock_transfer_objs.values('order_id', 'st_po__open_st__sku__user').distinct().\
                                annotate(ordered=Sum('quantity'), date_only=Cast('creation_date', DateField())).\
                                    order_by(sort_data)
    temp_data['recordsTotal'] = stock_transfers.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for stock_transfer in stock_transfers:
        destination_wh = ''
        order_id = stock_transfer['order_id']
        user_id = stock_transfer['st_po__open_st__sku__user']
        user_profile = User.objects.get(id=user_id)
        if user_profile:
            destination_wh = user_profile.username
        picked_qty = total_qty = 0
        picked_total_qty = STOrder.objects.filter(stock_transfer__st_po__open_st__sku__user=user_id, stock_transfer__order_id=order_id).values_list('stock_transfer__order_id').annotate(picked_qty=Sum('picklist__picked_quantity', distinct=True), st_obj=Sum('stock_transfer__quantity', distinct=True))
        if picked_total_qty:
            picked_total_qty = picked_total_qty[0]
            picked_qty = picked_total_qty[2]
            total_qty = picked_total_qty[1]
        temp_data['aaData'].append(OrderedDict(( ('Stock Transfer ID', order_id),
                                            ('Picked Quantity', picked_qty),
                                            ('Stock Transfer Date&Time', str(stock_transfer['date_only'])),
                                            ('Destination Warehouse', destination_wh),
                                            ('Total Quantity', total_qty))))


@csrf_exempt
@login_required
def create_shipment_stock_transfer(request, user=''):
    stock_transfer_id = request.GET.get('stock_transfer_id', '')
    try:
        st_order = StockTransfer.objects.filter(order_id=stock_transfer_id, sku__user=user.id)
        if len(st_order):
            st_order = st_order[0]
            st_order.stock_transfer.status = 3
            st_order.save()
    except:
        pass


@csrf_exempt
@login_required
@get_admin_user
def get_stock_transfer_shipment_popup_data(request, user=''):
    data = []
    courier_name = ''
    ship_no = get_shipment_number(user)
    sku_grouping = request.GET.get('sku_grouping', 'false')
    datatable_view = request.GET.get('view', '')
    st_order_id = request.GET.get('st_order_id', '')
    dest_wh_username = request.GET.get('dest_warehouse', '')
    search_params = {'user': user.id}
    request_data = dict(request.GET.iterlists())
    if 'st_order_id' in request_data.keys() and datatable_view == 'StockTransferShipment':
        filter_order_ids = []
        st_order_id = request_data['st_order_id']
        dest_user_id = User.objects.get(username=dest_wh_username)
        stock_transfer_obj = StockTransfer.objects.filter(order_id__in = st_order_id, st_po__open_st__sku__user = dest_user_id.id)
        if len(stock_transfer_obj):
            stock_transfer_obj = stock_transfer_obj.values()
        '''
        {'status': 2L, u'sku_id': 149723L, 'updation_date': datetime.datetime(2017, 2, 27, 11, 5, 22, tzinfo=<UTC>),
        'order_id': 1008L, u'st_po_id': 24L, 'creation_date': datetime.datetime(2017, 2, 27, 9, 38, 44, tzinfo=<UTC>),
        'shipment_date': datetime.datetime(2017, 2, 27, 9, 38, 44, tzinfo=<UTC>), 'invoice_amount': 0.0,
        'id': 24L, 'quantity': 1.0}
        '''
        for obj in stock_transfer_obj:
            picked_qty = total_qty = 0
            data_dict = obj
            sku_obj = SKUMaster.objects.get(id=data_dict['sku_id'])
            if sku_obj:
                sku_code = sku_obj.sku_code
                sku_desc = sku_obj.sku_desc
            data_dict['sku_code'] = sku_code
            data_dict['sku_desc'] = sku_desc
            picked_total_qty = STOrder.objects.filter(stock_transfer__st_po__open_st__sku__user=dest_user_id.id, stock_transfer__order_id=st_order_id[0]).values_list('stock_transfer__order_id').annotate(picked_qty=Sum('picklist__picked_quantity', distinct=True), st_obj=Sum('stock_transfer__quantity', distinct=True))
            if picked_total_qty:
                picked_total_qty = picked_total_qty[0]
                picked_qty = picked_total_qty[1]
                total_qty = picked_total_qty[2]
            data_dict['quantity'] = total_qty
            data_dict['picked_quantity'] = picked_qty
            data.append(data_dict)
        '''
        for order_ids in request_data['stock_transfer_id']:
            order_id_val = order_ids
            order_id_search = ''.join(re.findall('\d+', order_id_val))
            order_code_search = ''.join(re.findall('\D+', order_id_val))
            fil_ids = list(OrderDetail.objects.filter(Q(order_id=order_id_search,
                order_code=order_code_search) | Q(original_order_id=order_id_val),
                user=user.id).values_list('id', flat=True))
            filter_order_ids = list(chain(filter_order_ids, fil_ids))
        if filter_order_ids:
            search_params['id__in'] = filter_order_ids
        all_orders = OrderDetail.objects.filter(**search_params)
        for obj in all_orders:
            customer_order_summary = obj.customerordersummary_set.filter()
            if customer_order_summary:
                courier_name = customer_order_summary[0].courier_name
        data = get_shipment_quantity(user, all_orders, sku_grouping)
        '''
    if len(data):
        return HttpResponse(json.dumps({'data': data,
                                        'shipment_id': '',
                                        'display_fields': '',
                                        'marketplace': '',
                                        'shipment_number': ship_no,
                                        'courier_name': ''}, cls=DjangoJSONEncoder))
    return HttpResponse(json.dumps({'status': 'No Orders found'}))

@login_required
@get_admin_user
def delete_central_order(request, user=''):
    status = 'Success'
    orders_dict = dict(request.POST)
    for i in range(len(orders_dict['interm_id'])):
        try:
            interm_obj = IntermediateOrders.objects.filter(id=orders_dict['interm_id'][i],user = user.id)
            if interm_obj.exists():
                if interm_obj.filter(order__status__in=['1','3']) or interm_obj.filter(status__in=['2','']):
                    order_ids = interm_obj.exclude(order__status__in = [0,2]).values('order__id')
                    for id in order_ids :
                        OrderDetail.objects.filter(id = id['order__id']).update(status =3)
                    for obj in interm_obj :
                        int_order_obj = obj
                        int_order_obj.remarks = orders_dict['remarks'][i]
                        int_order_obj.status = 3
                        int_order_obj.save()
                else :
                     status = 'Orders are  Picked or Dispatched Already'


        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Deletion of central order failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))
    return HttpResponse(json.dumps({'status': status}))

@login_required
@get_admin_user
def do_delegate_orders(request, user=''):
    message = ''
    delegate_order = eval(request.POST.get('delegate_order_data', ''))
    for obj_data in delegate_order:
        mail_ids, user_mail_id, items = [], [], []
        order_dict = {}
        wh_level_stock_map = {}
        created_order_objs = []
        result_data = {}
        status_map = {'Accept' : '1', 'Reject' : '0', 'Pending' : '2'}
        #message = 'Success'
        #first = True
        #inter_obj_data = {}
        output_list = []
        reserved_obj_dict, raw_reserved_dict = {}, {}
        interm_obj_filter = IntermediateOrders.objects.filter(id=obj_data['interm_det_id'], user=user.id)
        interm_obj = interm_obj_filter[0]
        warehouses = UserGroups.objects.filter(admin_user_id=interm_obj.user, user__username=interm_obj.order_assigned_wh.username)
        wh_users = warehouses.values_list('user_id', flat=True)
        #warehouse_names = warehouses.values_list('user__username', flat=True)
        for wh in warehouses:
            stock_obj_dict = dict(StockDetail.objects.filter(sku__sku_code=obj_data['alt_sku_code'],
                sku__user__in=wh_users, quantity__gt=0).values_list('sku__user').distinct().annotate(in_stock=Sum('quantity')))
            stock_qty = stock_obj_dict.get(wh.user.id, 0)
            reserved_qty = reserved_obj_dict.get(wh.user.id, 0)
            reserved_qty = reserved_qty + raw_reserved_dict.get(wh.user.id, 0)
            avail_stock = stock_qty - reserved_qty
            wh_uname = wh.user.username
            wh_level_stock_map[wh_uname] = {'quantity': 0, 'available': 0}
            if wh_uname not in wh_level_stock_map:
                wh_level_stock_map[wh_uname]['available'] = avail_stock
            else:
                wh_level_stock_map[wh_uname]['available'] += avail_stock
        for wh, wh_data in wh_level_stock_map.iteritems():
            resp_dict = {}
            # Picklist generation
            order_user_sku = {}
            order_user_objs = {}
            order_sku = {}
            order_objs = []
            wh_name = wh
            alt_sku_code = obj_data['alt_sku_code']
            sku_master = SKUMaster.objects.filter(user=user.id, sku_code=alt_sku_code)
            if not sku_master.exists():
                resp_dict[str(interm_obj.interm_order_id)] = ' Invalid Alt SKU code'
                resp_str = str(interm_obj.interm_order_id) + ' - Invalid Alt SKU code'
                output_list.append(resp_str)
                created_order_objs.append(resp_dict)
                continue
            wh_usr_obj = User.objects.filter(username=wh_name)
            status = status_map.get(obj_data['status'])
            if status != '0':
                if wh_usr_obj:
                    wh_id = wh_usr_obj[0].id
                    wh_usr_obj = wh_usr_obj[0]
                else:
                    resp_dict[str(interm_obj.interm_order_id)] = 'User Missing'
                    resp_str = str(interm_obj.interm_order_id) + ' - User Missing'
                    created_order_objs.append(resp_dict)
                    output_list.append(resp_str)
                    continue
            interm_det_id = obj_data['interm_det_id']
            shipment_date = obj_data['shipment_date']
            if shipment_date:
                shipment_date = datetime.datetime.strptime(shipment_date, "%d/%m/%Y")
            if not status:
                resp_dict[str(interm_obj.interm_order_id)] = 'Status Missing'
                resp_str = str(interm_obj.interm_order_id) + ' - Status Missing'
                created_order_objs.append(resp_dict)
                output_list.append(resp_str)
                continue
            interm_qs = IntermediateOrders.objects.filter(id=interm_det_id)
            if not interm_qs:
                resp_dict[str(interm_obj.interm_order_id)] = 'Failed, Intermediate Order Not Found'
                resp_str = str(interm_obj.interm_order_id) + ' - Failed, Intermediate Order Not Found'
                created_order_objs.append(resp_dict)
                output_list.append(resp_str)
                continue
            sel_sku_id = interm_qs[0].sku.id
            update_alt_sku = False
            if interm_qs[0].sku.sku_code != alt_sku_code:
                update_alt_sku = True
                sel_sku_id = sku_master[0].id
            try:
                interm_obj = interm_qs[0]
                inter_obj_data = {'interm_order_id': interm_obj.interm_order_id,
                                  'unit_price': interm_obj.unit_price,
                                  'tax': interm_obj.tax,
                                  'user_id': interm_obj.user_id,
                                  'customer_user_id': interm_obj.customer_user_id,
                                  'shipment_date': interm_obj.shipment_date,
                                  'project_name': interm_obj.project_name,
                                  'sku_id': interm_obj.sku_id,
                                  'remarks': interm_obj.remarks,
                                  'status': interm_obj.status,
                                  'alt_sku_id': interm_obj.alt_sku_id
                                 }
                inv_amt = (interm_obj.unit_price * interm_obj.quantity) + interm_obj.tax
                """
                if first:
                    if interm_obj.order_id:
                        if status:
                            interm_obj.status = status
                        if shipment_date and status:
                            interm_obj.shipment_date = shipment_date
                            if interm_obj.order:
                                interm_obj.order.shipment_date = shipment_date
                        if update_alt_sku:
                            interm_obj.alt_sku_id = sel_sku_id
                        interm_obj.quantity = wh_data['quantity']
                        interm_obj.save()
                        first = False
                        resp_dict[str(interm_obj.interm_order_id)] = 'SKU Not found in Selected Warehouse'
                        continue
                else:
                    inter_obj_data['quantity'] = int(wh_data['quantity'])
                    interm_obj = IntermediateOrders.objects.create(**inter_obj_data)
                    inv_amt = (interm_obj.unit_price * interm_obj.quantity) + interm_obj.tax
                    items.append([interm_obj.sku.sku_desc, interm_obj.quantity, inv_amt])
                """
                if status != '0':
                    order_dict['user'] = wh_id
                    sku_id = get_syncedusers_mapped_sku(wh=wh_id, sku_id=sel_sku_id)
                    if not sku_id:
                        resp_dict[str(interm_obj.interm_order_id)] = 'SKU Not found in Selected Warehouse'
                        created_order_objs.append(resp_dict)
                        resp_str = str(interm_obj.interm_order_id) + ' - SKU Not found in Selected Warehouse'
                        output_list.append(resp_str)
                        continue
                    order_dict['sku_id'] = sku_id
                    order_dict['title'] = interm_obj.sku.sku_desc
                    order_dict['sku_code'] = interm_obj.sku.sku_code
                    if update_alt_sku:
                        interm_obj.alt_sku_id = sel_sku_id
                        interm_obj.save()
                        order_dict['title'] = interm_obj.alt_sku.sku_desc
                        order_dict['sku_code'] = interm_obj.alt_sku.sku_code
                    if interm_obj.customer_user:
                        customer_user = CustomerUserMapping.objects.filter(user_id=interm_obj.customer_user.id)
                        if customer_user:
                            order_dict['customer_id'] = customer_user[0].customer.customer_id
                            order_dict['customer_name'] = customer_user[0].customer.name
                            order_dict['telephone'] = customer_user[0].customer.phone_number
                            order_dict['email_id'] = customer_user[0].customer.email_id
                            order_dict['address'] = customer_user[0].customer.address

                    #Order Detail Save Block
                    original_order_id, address1, address2, client_code, village, state,marketplace, pincode = '','', '', '', '', '', '', ''
                    central_order_reassigning =  get_misc_value('central_order_reassigning', user.id)#for 72 networks

                    if central_order_reassigning == 'true':
                        ord_det_obj = OrderDetail.objects.filter(id = interm_obj.order_id)
                        order_fields = OrderFields.objects.filter(user=user.id, original_order_id=ord_det_obj[0].original_order_id)
                    else:
                        order_fields = OrderFields.objects.filter(user=user.id, original_order_id=interm_obj.original_order_id)
                    order_field_name_values = order_fields.values('name', 'value')
                    for obj in list(order_field_name_values):
                        if obj['name'] == "original_order_id":
                            original_order_id = obj['value']
                        if obj['name'] == "address1":
                            address1 = obj['value']
                        if obj['name'] == "address2":
                            address2 = obj['value']
                        if obj['name'] == "client_code":
                            client_code = obj['value']
                        if obj['name'] == "village":
                            village = obj['value']
                        if obj['name'] == "state1":
                            state = obj['value']
                        if obj['name'] == "pincode":
                            pincode = obj['value']
                        if obj['name'] == 'marketplace':
                            marketplace = obj['value']
                        if central_order_reassigning == 'true':
                            marketplace = 'Offline'
                    order_dict['customer_id'] = interm_obj.customer_id
                    order_dict['customer_name'] = interm_obj.customer_name
                    order_dict['email_id'] = ''
                    order_dict['address'] = address1 + ' ' + address2 + ' ' + client_code
                    order_dict['telephone'] = ''
                    order_dict['quantity'] = 1
                    order_dict['invoice_amount'] = inv_amt
                    order_dict['shipment_date'] = datetime.datetime.now()
                    order_dict['vat_percentage'] = 0
                    order_dict['status'] = 0
                    order_dict['city'] = village[:59]
                    order_dict['state'] = state
                    order_dict['marketplace'] = marketplace
                    try:
                        order_dict['pin_code'] = int(pincode)
                    except:
                        order_dict['pin_code'] = 0
                    order_dict['remarks'] = ''
                    order_dict['payment_mode'] = ''
                    order_dict['payment_received'] = 0
                    order_dict['unit_price'] = interm_obj.unit_price
                    order_dict['nw_status'] = ''
                    order_dict['order_type'] = 'Normal'
                    order_dict['order_reference'] = ''
                    order_dict['order_reference_date'] = datetime.datetime.now().strftime("%Y-%m-%d")
                    order_dict['shipment_date'] = datetime.datetime.now().strftime("%Y-%m-%d")
                    order_dict['original_order_id'] = original_order_id
                    order_dict['status'] = 1
                    order_dict['remarks'] = interm_obj.remarks
                    order_id_value = ''.join(re.findall('\d+', original_order_id))
                    if not order_id_value:
                        order_id_value = 0
                    order_code_value = ''.join(re.findall('\D+', original_order_id))
                    order_dict['order_id'] = order_id_value
                    order_dict['order_code'] = order_code_value
                    get_existing_order = OrderDetail.objects.filter(**{'sku_id': sku_id,
                        'original_order_id': original_order_id,
                        'user': wh_id})
                    if get_existing_order.exists() and str(get_existing_order[0].status) == '1':
                        #get_existing_order = get_existing_order[0]
                        #get_existing_order.quantity = get_existing_order.quantity + 1
                        #get_existing_order.save()
                        order_fields.update(original_order_id=original_order_id)
                        interm_obj_filter.update(status=1)
                        if central_order_reassigning == 'true':
                            interm_obj_filter.update(order_id = get_existing_order.id)
                            interm_obj.order_id = get_existing_order.id
                            interm_obj.status = 1
                            interm_obj.save()

                    else:
                        try:
                            if get_existing_order.exists() and str(get_existing_order[0].status) == '3':
                                ord_obj = get_existing_order[0]
                                ord_obj.status = 1
                                ord_obj.save()
                            else:
                                ord_obj = OrderDetail(**order_dict)
                                ord_obj.save()
                            order_fields.update(original_order_id=original_order_id)
                            interm_obj_filter.update(status=1)
                            if central_order_reassigning == 'true':
                                interm_obj.order_id = ord_obj.id
                                interm_obj.status = 1
                                interm_obj.save()



                        except Exception as e:
                            import traceback
                            log.debug(traceback.format_exc())
                            resp_dict[str(interm_obj.interm_order_id)] = 'Error in Saving Order ID'
                            created_order_objs.append(resp_dict)
                            resp_str = str(interm_obj.interm_order_id) + ' - Error in Saving Order ID'
                            output_list.append(resp_str)
                            continue
                    order_objs.append(ord_obj)
                    #Picklist Block
                    order_sku.update({ord_obj.sku: order_dict['quantity']})
                    # Collecting needed data for Picklist generation
                    order_user_sku.setdefault(wh_id, {})
                    order_user_sku[wh_id].setdefault(ord_obj.sku, 0)
                    order_user_sku[wh_id][ord_obj.sku] += order_dict['quantity']
                    # Collecting User order objs for picklist generation
                    order_user_objs.setdefault(wh_id, [])
                    order_user_objs[wh_id].append(ord_obj)
                    # Auto Picklist
                    """
                    auto_picklist_signal = get_misc_value('auto_generate_picklist', wh_id)
                    if auto_picklist_signal == 'true':
                        message = check_stocks(order_sku, wh_usr_obj, request, order_objs)
                    """

                    #Customer Order Summary Create
                    """
                    if first:
                        inv_amt = (interm_obj.unit_price * interm_obj.quantity) + interm_obj.tax
                        items.append([interm_obj.sku.sku_desc, interm_obj.quantity, inv_amt])
                        inter_obj_data = {'interm_order_id': interm_obj.interm_order_id,
                                          'unit_price': interm_obj.unit_price,
                                          'tax': interm_obj.tax,
                                          'user_id': interm_obj.user_id,
                                          'customer_user_id': interm_obj.customer_user_id,
                                          'shipment_date': interm_obj.shipment_date,
                                          'project_name': interm_obj.project_name,
                                          'sku_id': interm_obj.sku_id,
                                          'remarks': interm_obj.remarks,
                                          'status': interm_obj.status,
                                          'alt_sku_id': interm_obj.alt_sku_id
                                         }
                        first = False
                        interm_obj.order_id = ord_obj.id
                        interm_obj.quantity = int(wh_data['quantity'])
                        interm_obj.order_assigned_wh_id = wh_id
                        interm_obj.shipment_date = shipment_date
                        interm_obj.status = 1
                        interm_obj.save()
                    """
                    tax_percentage = float(interm_obj.sgst_tax) + float(interm_obj.igst_tax) + float(interm_obj.cgst_tax)
                    tax_value = (inv_amt / 100) * tax_percentage
                    cust_ord_dict = {'order_id': ord_obj.id, 'sgst_tax': interm_obj.sgst_tax,
                                    'cgst_tax': interm_obj.cgst_tax, 'igst_tax': interm_obj.igst_tax,
                                    'vehicle_number': '', 'tax_value': tax_value,
                                    'invoice_date': datetime.datetime.now()}
                    cos_qs = CustomerOrderSummary.objects.filter(order_id=ord_obj.id)
                    if cos_qs:
                        cos_qs.update(**cust_ord_dict)
                    else:
                        cos_obj = CustomerOrderSummary(**cust_ord_dict)
                        cos_obj.save()
                    #mail to Admin and normal user
                    central_orders_mail = MiscDetail.objects.filter(user=request.user.id,
                        misc_type='central_orders', misc_value='true')
                    if central_orders_mail:
                        if user.userprofile.warehouse_type == 'CENTRAL_ADMIN':
                            mail_ids = [user.userprofile.email]
                        else:
                            admin_users = UserGroups.objects.filter(user_id=user.id)
                            if admin_users:
                                mail_ids = [admin_users[0].admin_user.userprofile.email]
                        mail_ids = [request.user.email]
                        interm_qs = interm_qs[0]
                        user_mail_id = [interm_qs.customer_user.email]
                        headers = ['Product Details', 'Ordered Quantity', 'Total']
                        mail_order_id = order_dict['order_code'] + str(order_dict['order_id']) + ' ('\
                                        + str(interm_qs.order_id) + ')'
                        data_dict = {'customer_name': interm_qs.customer_user.username, 'items': items,
                                     'headers': headers, 'role': 'Admin',
                                     'status': 'accept', 'order_id': mail_order_id}
                        t = loader.get_template('templates/central_order/order_approved_admin.html')
                        rendered = t.render(data_dict)
                        t_user = loader.get_template('templates/central_order/order_approved.html')
                        rendered_user = t_user.render(data_dict)
                        if mail_ids:
                            send_mail(mail_ids, 'Order Approved, Customer: %s' % interm_qs.customer_user.username, rendered)
                        if user_mail_id:
                            send_mail(user_mail_id, 'Order Approved Successfully', rendered_user)
                #admin_user = get_admin(user)
                #if admin_user.username in ['one_assist']:
                    #create_order_pos(user, created_order_objs)
            except:
                import traceback
                log.debug(traceback.format_exc())
                message = 'Failed'
        #return HttpResponse('Orders Delegated')
        message = 'Orders Delegated'
        output_msg = ''
        if len(output_list):
            output_msg = (', ').join(output_list)
        else:
            output_msg = "Well Done ! Successfully Delegated"
        if len(created_order_objs):
            message = 'Orders Delegated Partially'
            result_data['resp_data'] = created_order_objs
        result_data['message'] = message
        result_data['output_msg'] = output_msg
        result_data['status'] = True
    return HttpResponse(json.dumps(result_data), content_type='application/json')


def dispatch_qc(user, sku_details, order_id, validation_status):
    user_id = user.id
    get_po_imei_qs = ''
    for key, value in sku_details.items():
        imei_qs = POIMEIMapping.objects.filter(status=1, sku__user=user_id, imei_number__in=[key])
        if imei_qs:
            get_po_imei_qs = imei_qs[0]
        if not get_po_imei_qs:
            continue
        if value:
            value = eval(value[0])
        if key:
            for dict_obj in value:
                for key_obj, value_obj in dict_obj.items():
                    disp_imei_map = {}
                    disp_imei_map['order_id'] = order_id.id
                    disp_imei_map['po_imei_num'] = get_po_imei_qs
                    disp_imei_map['qc_name'] = key_obj
                    dispatch_checklist = DispatchIMEIChecklist.objects.filter(**disp_imei_map)
                    if value_obj[1] == "false":
                        value_obj[1] = False
                    elif value_obj[1] == "true":
                        value_obj[1] = True
                    if validation_status == "PASS":
                        validation_status = True
                    elif validation_status == "FAIL":
                        validation_status = False
                    if not dispatch_checklist:
                        disp_imei_map['qc_status'] = value_obj[1]
                        disp_imei_map['final_status'] = validation_status
                        disp_imei_map['qc_type'] = 'sales_order'
                        disp_imei_map['remarks'] = value_obj[0]
                        try:
                            disp_imei_obj = DispatchIMEIChecklist.objects.create(**disp_imei_map)
                        except Exception as e:
                            import traceback
                            picklist_qc_log.debug(traceback.format_exc())
                            picklist_qc_log.info("Error Occured in Saving Dispatch IMEI" + str(e))
                    else:
                        dispatch_checklist = dispatch_checklist[0]
                        dispatch_checklist.qc_status = value_obj[1]
                        dispatch_checklist.final_status = validation_status
                        dispatch_checklist.remarks = value_obj[0]
                        dispatch_checklist.qc_type = 'sales_order'
                        dispatch_checklist.save()
            try:
                dest_loc = ''
                source_loc = ''
                if len(imei_qs) and validation_status:
                    sku_id = order_id.sku.id
                    OrderIMEIMapping.objects.create(**{'order_id':order_id.id, 'sku_id': sku_id,
                    'po_imei' : imei_qs[0], 'imei_number': get_po_imei_qs.imei_number, 'status':1, 'sor_id': '',
                    'order_reference': '', 'marketplace': ''})
                elif not validation_status:
                    wms_code = order_id.sku.wms_code
                    quantity = 1
                    # cycle_count = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
                    # if not cycle_count:
                    #     cycle_id = 1
                    # else:
                    #     cycle_id = cycle_count[0].cycle + 1
                    sku_stocks = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0, sku__wms_code=wms_code).order_by('creation_date')
                    if sku_stocks:
                        source_loc = sku_stocks[0].location.location
                    from rest_api.views.inbound import *
                    dest_loc = get_returns_location('DAMAGED_ZONE', '', user)
                    if dest_loc:
                        dest_loc = dest_loc[0].location
                    if source_loc and dest_loc:
                        move_stock_location(wms_code, source_loc, dest_loc, quantity, user)
                imei_qs.update(status=0)
            except Exception as e:
                import traceback
                picklist_qc_log.debug(traceback.format_exc())
                picklist_qc_log.info("Error Occured in Saving Dispatch IMEI" + str(e))


@login_required
@get_admin_user
def print_pdf_shipment_info(request, user=''):
    data = eval(request.POST['data'])['data']
    driver_name = eval(request.POST['data'])['driver_name']
    manifest_number = eval(request.POST['data'])['manifest_number']
    truck_number = eval(request.POST['data'])['truck_number']
    driver_phone_number = eval(request.POST['data'])['driver_phone_number']


    return render(request, 'templates/toggle/shipment_info.html',{'data':data,'driver_name':driver_name,'manifest_number':manifest_number,'truck_number':truck_number,'driver_phone_number':driver_phone_number})

@login_required
@get_admin_user
def send_order_back(request, user=''):
    order_det_id=[]
    order_det_reassigned_id =[]
    order_det_not_reassigned_id =[]
    order_det_reassigned_orderid =[]
    order_det_not_reassigned_orderid =[]
    try:
        order_id_list =request.POST.getlist('order_id')
        remarks_list = request.POST.getlist('remarks')
        alt_sku_list = request.POST.getlist('sku_id')
        for i in range(len(order_id_list)) :
            ord_obj = OrderDetail.objects.filter(original_order_id=order_id_list[i], user=user.id)
            for obj in ord_obj :
                interm_obj = IntermediateOrders.objects.filter(order_id=obj.id).exclude(status = 3)
                if interm_obj:
                    interm_obj = interm_obj[0]
                    if obj.quantity != interm_obj.quantity :
                        order_det_not_reassigned_id.append(obj.id)
                        order_det_not_reassigned_orderid.append(obj.original_order_id)
                        log.info('%s orderid is not assigned ' % (str(order_id_list[i],)))
                    else:
                        order_det_reassigned_id.append(obj.id)
                        log.info('%s orderid is  assigned' % (str(order_id_list[i],)))
                        interm_obj.status = 0
                        interm_obj.remarks=remarks_list[i]
                        if alt_sku_list:
                            sku_obj = SKUMaster.objects.filter(user=user.id, sku_code=alt_sku_list[i])
                            interm_obj.alt_sku = sku_obj[0]
                        PushNotifications.objects.create(user_id=interm_obj.user_id, message=obj.original_order_id+"  "+"order got rejected from"+"  "+interm_obj.order_assigned_wh.username+" "+"with central order id"+" "+str(interm_obj.interm_order_id))
                        interm_obj.save()
                        order_det_reassigned_orderid.append(obj.original_order_id)
                        order_cancel_functionality(order_det_reassigned_id)

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Reassign of orders failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
    if  len(order_det_not_reassigned_orderid) > 0 :
        status = "These Order ID's are not sent back"
    else:
        status ="Successfully sent all the orders back"

    return HttpResponse(json.dumps({'data':order_det_not_reassigned_orderid , 'message': 'Success', 'status':status }))


@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def invoice_print_manifest(request, user=''):
    reversion.set_user(request.user)
    shipment_number = request.POST.get('shipment_id')
    shipment_orders = ShipmentInfo.objects.filter(order_shipment__shipment_number=int(shipment_number),
                                                  order_shipment__user=user.id)
    manifest_number = shipment_orders[0].order_shipment.manifest_number
    final_data = ''
    for orders in shipment_orders :
        invoice_data = get_invoice_data(str(orders.order.id),user)
        central_order_reassigning =  get_misc_value('central_order_reassigning', user.id)
        if central_order_reassigning:
            invoice_data['manifest_number']= manifest_number
        invoice_data = modify_invoice_data(invoice_data, user)
        if get_misc_value('show_imei_invoice', user.id) == 'true' and user.userprofile.user_type == 'marketplace_user':
            invoice_data = build_marketplace_invoice(invoice_data, user, False)
        else:
            invoice_data = build_invoice(invoice_data, user, False)
        final_data += invoice_data

    return HttpResponse(final_data)


@csrf_exempt
@login_required
@get_admin_user
@reversion.create_revision(atomic=False, using='reversion')
def generate_picklist_dc(request, user=''):
    reversion.set_user(request.user)
    st_time = datetime.datetime.now()
    data = {}
    count = 0
    total_qty = 0
    iterator=itertools.count()
    picklist_number = request.POST['picklist_number']
    for key, value in request.POST.iterlists():
        name, picklist_id = key.rsplit('_', 1)
        data.setdefault(picklist_id, [])
        for index, val in enumerate(value):
            if len(data[picklist_id]) < index + 1:
                data[picklist_id].append({})
            data[picklist_id][index][name] = val
    picks_all = Picklist.objects.filter(order__sku__user=user.id, picklist_number=picklist_number,
                                            status__icontains="open")
    if not picks_all:
        return HttpResponse("No Orders Found")
    batch_group_data = OrderedDict()
    batch_group_data_order_wise = OrderedDict()
    for key, value in data.iteritems():
        if key in ('name', 'number', 'order', 'sku', 'invoice'):
            continue
        picklist_batch = ''
        picklist_order_id = value[0]['order_id']
        if picklist_order_id:
            picklist = picks_all.get(order__order_id=picklist_order_id,
                                         order__sku__sku_code=value[0]['wms_code'])
        elif not key:
            scan_wms_codes = map(lambda d: d['wms_code'], value)
            picklist_batch = picks_all.filter(
                Q(stock__sku__wms_code__in=scan_wms_codes) | Q(order__sku__wms_code=scan_wms_codes),
                reserved_quantity__gt=0, status__icontains='open')
        else:
            picklist_status = ''
            if value[0].get('picklist_status', ''):
                picklist_status = value[0]['picklist_status']
            if picklist_status == 'open':
                picklist_batch = picks_all.filter(id=key)
                picklist = picklist_batch[0]
            else:
                picklist = picks_all.get(id=key)
        if not picklist_batch:
            picklist_batch = get_picklist_batch(picklist, value, picks_all)
        if not picklist_batch:
            continue
        picklist_obj = picklist_batch[0]
        extra_fields ={}
        extra_order_fields = get_misc_value('extra_order_fields', user.id)
        if extra_order_fields == 'false' :
            extra_order_fields = []
        else:
            extra_order_fields = extra_order_fields.split(',')
        for extra in extra_order_fields :
            order_field_obj = OrderFields.objects.filter(original_order_id=picklist_obj.order.original_order_id,user=user.id ,name = extra)
            if order_field_obj.exists():
                extra_fields[order_field_obj[0].name] = order_field_obj[0].value
        customer_address =[]
        customer_details = []
        consignee =''
        customer_details = list(CustomerMaster.objects.filter(user=user.id, customer_id=picklist_obj.order.customer_id).
                                values('id', 'customer_id', 'name', 'email_id', 'tin_number', 'address', 'shipping_address',
                                       'credit_period', 'phone_number'))
        if customer_details:
            customer_id = customer_details[0]['id']
            customer_address = customer_details[0]['name'] + '\n' + customer_details[0]['address']
            if customer_details[0]['tin_number']:
                customer_address += ("\nGSTIN No: " + customer_details[0]['tin_number'])
            if customer_details[0]['phone_number']:
                customer_address += ("\nCall: " + customer_details[0]['phone_number'])
            if customer_details[0]['email_id']:
                customer_address += ("\tEmail: " + customer_details[0]['email_id'])
            consignee = customer_address
        else:
            customer_id = picklist_obj.order.customer_id
            customer_address = picklist_obj.order.customer_name + '\n' + picklist_obj.order.address + "\nCall: " \
                               + str(picklist_obj.order.telephone) + "\nEmail: " + str(picklist_obj.order.email_id)
        for val in value:
            order = picklist_obj.order
            is_combo = False
            sku = order.sku
            parent_sku_code = sku.sku_code
            parent_sku_desc = sku.sku_desc
            if picklist_obj.order_type == 'combo':
                is_combo = True
                if picklist_obj.stock:
                    sku = picklist_obj.stock.sku
                else:
                    sku = SKUMaster.objects.filter(sku_code=picklist_obj.sku_code, user=user.id)[0]
            if val['reserved_quantity']:
                total_qty = total_qty + int(val['reserved_quantity'])
            sku_code = sku.sku_code
            sku_desc = sku.sku_desc
            sku_class = sku.sku_class
            sku_category = sku.sku_category
            sku_size = sku.sku_size
            title = order.title
            order_id = order.original_order_id
            invoice_amount = 0
            _tax = 0
            unit_price = 0
            tax_type = ''
            vat = 0
            mrp_price = 0
            discount = 0
            amt = 0
            base_price = 0
            count = count+1
            taxes_dict = {}
            if not order_id:
                order_id = order.order_code + str(order.order_id)
            batch_no = val.get('batchno', '')
            mfd_date = val.get('manufactured_date', '')
            exp_date = val.get('expiry_date', '')
            batch_group_data.setdefault(parent_sku_code, {})
            batch_group_data_order_wise.setdefault(order_id, {})
            batch_grouping_order_key = '%s:%s:%s:%s:%s' % (str(sku_code),order_id, batch_no, mfd_date, exp_date)
            batch_grouping_key = '%s:%s:%s:%s' % (str(sku_code), batch_no, mfd_date, exp_date)
            batch_group_data[parent_sku_code].setdefault(batch_grouping_key,
                                        {'order_id': order_id, 'sku_code': sku_code, 'sku_desc': sku_desc,
                                         'title': title, 'invoice_amount': str(invoice_amount),
                                         'quantity': 0, 'tax': "%.2f" % (_tax),
                                         'unit_price': unit_price, 'tax_type': tax_type,
                                         'count':count,
                                         'vat': vat, 'mrp_price': mrp_price, 'discount': discount,
                                         'sku_class': sku_class,
                                         'sku_category': sku_category, 'sku_size': sku_size,
                                         'amt': amt, 'taxes': taxes_dict,
                                         'base_price': base_price, 'hsn_code': sku.hsn_code,
                                         'imeis': [],
                                         'discount_percentage': 0, 'id': order.id,
                                         'shipment_date': '', 'sno': 0,
                                         'measurement_type': '',
                                         'batch_no': batch_no, 'mfd_date': mfd_date, 'exp_date': exp_date,
                                         'is_combo': is_combo, 'parent_sku_code': parent_sku_code,
                                         'parent_sku_desc': parent_sku_desc})
            batch_group_data[parent_sku_code][batch_grouping_key]['quantity'] += float(val['reserved_quantity'])

            batch_group_data_order_wise[order_id].setdefault(batch_grouping_order_key,
                                        {'order_id': order_id, 'sku_code': sku_code, 'sku_desc': sku_desc,
                                         'order':order,
                                         'title': title, 'invoice_amount': str(invoice_amount),
                                         'quantity': 0, 'tax': "%.2f" % (_tax),
                                         'unit_price': unit_price, 'tax_type': tax_type,
                                         'count':count,
                                         'vat': vat, 'mrp_price': mrp_price, 'discount': discount,
                                         'sku_class': sku_class,
                                         'sku_category': sku_category, 'sku_size': sku_size,
                                         'amt': amt, 'taxes': taxes_dict,
                                         'base_price': base_price, 'hsn_code': sku.hsn_code,
                                         'imeis': [],
                                         'discount_percentage': 0, 'id': order.id,
                                         'shipment_date': '', 'sno': 0,
                                         'measurement_type': '',
                                         'batch_no': batch_no, 'mfd_date': mfd_date, 'exp_date': exp_date,
                                         'is_combo': is_combo, 'parent_sku_code': parent_sku_code,
                                         'parent_sku_desc': parent_sku_desc})
            batch_group_data_order_wise[order_id][batch_grouping_order_key]['quantity'] += float(val['reserved_quantity'])

    invoice_data = {}
    invoice_data['data'] = batch_group_data
    invoice_data['username'] = user.username
    invoice_data['extra_order_fields'] = extra_fields
    user_profile = UserProfile.objects.get(user_id=user.id)
    invoice_data['gstin_no'] = user_profile.gst_number
    invoice_data['company_name'] = user_profile.company.company_name
    invoice_data['company_address'] = user_profile.address
    invoice_data['company_number'] = user_profile.phone_number
    invoice_data['order_no'] = picklist_obj.order.order_id
    invoice_data['customer_details'] = customer_details
    invoice_data['customer_address'] = customer_address
    invoice_data['consignee'] = consignee
    invoice_data['iterator'] = iterator
    invoice_data['total_quantity'] = total_qty
    for key , value in batch_group_data_order_wise.items() :
        tempdc = TempDeliveryChallan.objects.filter(order = value.values()[0].get('order'))
        if tempdc.exists():
            invoice_data['dc_number'] =  tempdc[0].dc_number
            invoice_date = tempdc[0].creation_date
            if not tempdc[0].dc_number:
                challan_num = get_challan_number_for_dc(order , user)
                temp = tempdc[0]
                temp.dc_number = challan_num
                temp.save()
                invoice_data['dc_number'] = challan_num
                invoice_date = tempdc[0].creation_date
        if not tempdc.exists():
            delivery_challan_dict = {}
            challan_num = get_challan_number_for_dc(order , user)
            delivery_challan_dict['dc_number'] = challan_num
            invoice_data['dc_number'] = challan_num
            delivery_challan_dict['order'] = value.values()[0].get('order','')
            delivery_challan_dict['picklist_number'] = picklist_number
            delivery_challan_dict['total_qty'] = total_qty
            for val in value.values():
                val['order'] = ''
            delivery_challan_dict['dcjson'] = json.dumps(value)
            TempDeliveryChallan.objects.create(**delivery_challan_dict)
            invoice_date = datetime.datetime.now()
        invoice_date = get_local_date(user, invoice_date, send_date='true')
        invoice_data['invoice_time'] = invoice_date.strftime("%H:%M")
        invoice_data['inv_date'] = invoice_date.strftime("%d %b %Y")


    return render(request, 'templates/toggle/delivery_challan_batch_level.html', invoice_data)


@login_required
@get_admin_user
def get_order_extra_fields(request , user =''):
    extra_order_fields ,order_level_data = [], 0
    sku_level_order_fields , sku_level = [] ,0
    order_field_obj = get_misc_value('extra_order_fields', user.id)
    sku_level_fields = get_misc_value('extra_order_sku_fields', user.id)
    if not order_field_obj == 'false':
        extra_order_fields = order_field_obj.split(',')
    if not sku_level_fields == 'false':
        sku_level_order_fields = sku_level_fields.split(',')
        if sku_level_order_fields:
            sku_level = 1
    if extra_order_fields:
        order_level_data = 1
    return HttpResponse(json.dumps({'order_level':extra_order_fields,
                                    'order_level_data': order_level_data,
                                    'sku_level_order_fields': sku_level_order_fields,
                                    'sku_level':sku_level,}))


@login_required
@get_admin_user
def create_feedback_form(request, user=''):
    resp = {'message': 'success'}
    fb_type = request.POST.get('feedbackType', '')
    sku_style = request.POST.get('SKU', '')
    url = request.POST.get('sku', '')
    remarks = request.POST.get('remarks', '')
    if not (fb_type == 'Technical Support' or fb_type == 'Others'):
        sku_qs = SKUMaster.objects.filter(style_name=sku_style, user=user.id)
        if not sku_qs:
            return HttpResponse('No SKU Style Found')
        url_name = ''
        sku_id = sku_qs[0].id
        image_file = request.FILES.get('files-0', '')
    else:
        if fb_type == 'Technical Support':
            sku_id = image_file = ''
            url_name = url
        else:
            sku_id = url_name = image_file = ''
    feedback_map = {'user_id': request.user.id, 'feedback_type': fb_type, 'sku_id': sku_id,
                    'feedback_remarks': remarks, 'feedback_image': image_file, 'url_name': url_name}
    try:
        fb_master = FeedbackMaster(**feedback_map)
        fb_master.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Exception raised while creating the feedback form for %s and params are %s and error statement is %s'
                 % (str(user.username), str(request.POST.dict()), str(e)))
    return HttpResponse(json.dumps(resp), content_type='application/json')


@csrf_exempt
def get_feedback_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters={}):
    lis = ['user__username', 'feedback_type', 'sku__sku_class', 'feedback_remarks', 'url_name']
    search_params = get_filtered_params(filters, lis)
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    response_data = {'data': []}
    warehouse_qs = UserGroups.objects.filter(admin_user=user.id)
    dist_users = warehouse_qs.filter(user__userprofile__warehouse_level=1).values_list('user_id__username', flat=True)
    wh_userids = warehouse_qs.values_list('user_id', flat=True)
    reseller_qs = CustomerUserMapping.objects.filter(customer__user__in=wh_userids).values('user')
    feedback_data = FeedbackMaster.objects.filter(user_id__in=reseller_qs).order_by(order_data)
    if search_term:
        feedback_data = FeedbackMaster.objects.filter(Q(user__username__icontains=search_term)| Q(feedback_type__icontains=search_term)
            | Q(sku__sku_class__icontains=search_term) | Q(feedback_remarks__icontains=search_term) | Q(url_name__icontains=search_term)).order_by(order_data)
    try:
        if feedback_data:
            for data in feedback_data:
                username = data.user.username
                feedback_type = data.feedback_type
                if data.sku_id:
                    sku_class = data.sku.sku_class
                else:
                    sku_class = ''
                if data.feedback_image:
                    feedback_image = data.feedback_image
                else:
                    feedback_image = ''
                if data.url_name:
                    url_name = data.url_name
                else:
                    url_name = ''
                feedback_remarks = data.feedback_remarks
                temp_data['aaData'].append(OrderedDict(
                    (('User Name', username), ('Feedback Type', feedback_type), ('SKU', sku_class), ('Feedback Remarks', feedback_remarks), ('Feedback Image', str(feedback_image)), ('URL', url_name))))
                temp_data['recordsTotal'] = feedback_data.count()
                temp_data['recordsFiltered'] = temp_data['recordsTotal']
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Exception raised while display feedback form for %s and params are %s and error statement is %s'
                 % (str(user.username), str(request.POST.dict()), str(e)))


def get_distributors_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters={}):
    filter_dict = {}
    whs = get_same_level_warehouses(2, user)
    dist_custs = WarehouseCustomerMapping.objects.filter(warehouse__in=whs, status=1)
    if dist_custs:
        cm_ids = dist_custs.values_list('customer_id', flat=True)
        filter_dict = {'customer_id__in': cm_ids}
    generic_orders = GenericOrderDetailMapping.objects.filter(**filter_dict)
    gen_ord_qty_qs = generic_orders.values_list('generic_order_id', 'customer_id', 'orderdetail__original_order_id',
                                                'cust_wh_id').annotate(tot_qty=Sum('quantity'),
                                                                       date_only=Cast('creation_date', DateField()))
    temp_data['recordsTotal'] = gen_ord_qty_qs.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    all_wh_dists_obj = UserGroups.objects.filter(admin_user=user.id)
    orderprefix_map = dict(all_wh_dists_obj.values_list('user_id', 'user__userprofile__order_prefix'))
    for gen_ord in gen_ord_qty_qs[start_index:stop_index]:
        emiza_order_ids = []
        gen_ord_id, customer_id, org_ord_id, cust_wh_id, cdate, total_qty = gen_ord
        cust_qs = CustomerMaster.objects.filter(id=customer_id)
        if cust_qs:
            dist_name = cust_qs[0].name
        else:
            dist_name = ''
        if cust_wh_id in orderprefix_map:
            emiza_id = orderprefix_map[cust_wh_id] + str(org_ord_id)
            emiza_order_ids.append(emiza_id)
        temp_data['aaData'].append(OrderedDict(
            (('distributor', dist_name), ('order_id', gen_ord_id), ('emizaids', emiza_order_ids),
             ('uploaded_date', cdate.strftime('%Y-%m-%d')), ('tot_qty', total_qty), ('dist_cust_id', customer_id))))


def get_distributor_order(request):
    dist_cust_id = request.POST.get('distributor', '')
    gen_ord_id = request.POST.get('gen_ord_id', '')
    filters_dict = {'generic_order_id': gen_ord_id, 'customer_id': dist_cust_id}
    dist_qs = CustomerMaster.objects.filter(id=dist_cust_id)
    if dist_qs:
        dist_name = dist_qs[0].name
    else:
        return HttpResponse('Something went wrong, please approach Tech Team')
    gen_ord_qs = GenericOrderDetailMapping.objects.filter(**filters_dict)
    gen_ord_map = []
    for order in gen_ord_qs:
        po = {'sku_code': order.orderdetail.sku.sku_code, 'quantity': order.orderdetail.quantity,
              'unit_price': order.unit_price, 'sku_desc': order.orderdetail.sku.sku_desc}
        po['amount'] = round(po['quantity'] * po['unit_price'], 2)
        customer_summary = order.orderdetail.customerordersummary_set.values()
        user_profile_obj = UserProfile.objects.filter(user_type='warehouse_user', user=order.orderdetail.user)
        if user_profile_obj:
            user_profile = user_profile_obj[0]
            po['wharehouse_name'] = user_profile.user.username
            total_tax = 0
            if customer_summary:
                customer_summary = customer_summary[0]
                for tax in ['sgst', 'cgst', 'igst']:
                    po[tax+'_tax'] = customer_summary[tax+'_tax']
                    po[tax] = round((po['amount']/100)*po[tax+'_tax'], 2)
                    total_tax += po[tax]
            po['invoice_amt'] = po['amount'] + total_tax
            gen_ord_map.append(po)
    data = {'sku_quantity': gen_ord_map, 'generic_order_id': gen_ord_id, 'distributor': dist_cust_id, 'dist_name': dist_name}
    return HttpResponse(json.dumps({'data': data}))


@csrf_exempt
@login_required
def sm_cancel_distributor_order(request):
    message = 'Success'
    gen_ord_id = request.POST.get('gen_ord_id', '')
    dist_cust_id = request.POST.get('distributor', '')
    try:
        gen_qs = GenericOrderDetailMapping.objects.filter(generic_order_id=gen_ord_id,
                                                          customer_id=dist_cust_id)
        is_emiza_order_failed = False
        generic_orders = gen_qs.values('orderdetail__original_order_id', 'orderdetail__user').distinct()
        for generic_order in generic_orders:
            original_order_id = generic_order['orderdetail__original_order_id']
            order_detail_user = User.objects.get(id=generic_order['orderdetail__user'])
            resp = order_push(original_order_id, order_detail_user, "CANCEL")
            log.info('Cancel Order Push Status done by Admin Login: %s' % (str(resp)))
            if resp.get('Status', '') == 'Failure' or resp.get('status', '') == 'Internal Server Error':
                is_emiza_order_failed = True
                if resp.get('status', '') == 'Internal Server Error':
                    message = "400 Bad Request"
                else:
                    message = resp['Result']['Errors'][0]['ErrorMessage']
        if not is_emiza_order_failed:
            order_det_ids = gen_qs.values_list('orderdetail_id', flat=True)
            order_cancel_functionality(order_det_ids)
            # gen_qs.delete()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Order Cancellation failed for user %s and params are %s and error statement is %s' % (
            str(request.user.username), str(request.GET.dict()), str(e)))
    return HttpResponse(message)


@csrf_exempt
@login_required
@get_admin_user
def get_order_extra_options(request, user=''):
    misc_options =[]
    options_dict = {}
    try:
        misc_options =list( MiscDetailOptions.objects.filter(misc_detail__user=user.id).values('misc_key','misc_value'))
        for option in misc_options :
            options_dict[option.get('misc_key','')]  =  option.get('misc_value','').split(",")
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Exception raised for getting extra order options for  %s and error statement is %s'
                 % (str(user.username), str(e)))
    return HttpResponse(json.dumps(options_dict), content_type='application/json')


@get_admin_user
@csrf_exempt
@login_required
def sm_custom_order_cancel(request, user=''):
    message = 'Success'
    enq_id = request.POST.get('enquiry_id')
    usr_id = request.POST.get('user_id')
    try:
        if enq_id:
            manual_enquiry_object = ManualEnquiry.objects.filter(enquiry_id=enq_id,
                                                              user_id=usr_id)
            manual_enquiry_details_object = ManualEnquiryDetails.objects.filter(enquiry_id=enq_id,
                                                              remarks_user_id=usr_id)
            order_status = manual_enquiry_object[0].status
            if user.userprofile.warehouse_type == 'CENTRAL_ADMIN' and order_status.lower() != 'order_placed':
                manual_enquiry_object[0].delete()
                manual_enquiry_details_object[0].delete()
            else :
                message = 'Placed Orders Can Not Be Deleted '
        else :
            message = 'Order Not Available '

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Order Cancellation failed for user %s and params are %s and error statement is %s' % (
            str(request.user.username), str(request.GET.dict()), str(e)))
    return HttpResponse(message)

@csrf_exempt
@get_admin_user
def generate_dc(request , user = ''):
    invoice_data = {}
    orders = request.POST.get('selected_orders' ,'')
    iterator=itertools.count()
    batch_group_data_order = OrderedDict()
    total_qty = 0
    search_params = {}
    if orders :
        orders = json.loads(orders)
        for order in orders :
            order_id = ''.join(re.findall('\d+', order['order_id']))
            order_code = ''.join(re.findall('\D+', order['order_id']))
            if order_id :
                search_params['order__order_id'] = order_id
            if order_code :
                search_params['order__order_code'] = order_code
            original_order_id = order_code + order_id
            temp_dc_objs = TempDeliveryChallan.objects.filter(order__sku__user = user.id, **search_params)
            if temp_dc_objs.exists() :
                order = temp_dc_objs[0].order
                batch_group_data = temp_dc_objs[0].dcjson
                dc_number_obj = temp_dc_objs[0].dc_number
                total_qty = temp_dc_objs[0].total_qty
                creation_date = temp_dc_objs[0].creation_date
                invoice_date = get_local_date(user, creation_date, send_date='true')
                invoice_data['invoice_time'] = invoice_date.strftime("%H:%M")
                invoice_data['inv_date'] = invoice_date.strftime("%d %b %Y")

                customer_address =[]
                customer_details = []
                consignee =''
                customer_details = list(CustomerMaster.objects.filter(user=user.id, customer_id=order.customer_id).
                                        values('id', 'customer_id', 'name', 'email_id', 'tin_number', 'address', 'shipping_address',
                                               'credit_period', 'phone_number'))
                if customer_details:
                    customer_id = customer_details[0]['id']
                    customer_address = customer_details[0]['name'] + '\n' + customer_details[0]['address']
                    if customer_details[0]['tin_number']:
                        customer_address += ("\nGSTIN No: " + customer_details[0]['tin_number'])
                    if customer_details[0]['phone_number']:
                        customer_address += ("\nCall: " + customer_details[0]['phone_number'])
                    if customer_details[0]['email_id']:
                        customer_address += ("\tEmail: " + customer_details[0]['email_id'])
                    consignee = customer_address
                else:
                    customer_id = order.customer_id
                    customer_address = order.customer_name + '\n' + order.address + "\nCall: " \
                                       + str(order.telephone) + "\nEmail: " + str(order.email_id)

                extra_fields ={}
                extra_order_fields = get_misc_value('extra_order_fields', user.id)
                if extra_order_fields == 'false' :
                    extra_order_fields = []
                else:
                    extra_order_fields = extra_order_fields.split(',')
                for extra in extra_order_fields :
                    order_field_obj = OrderFields.objects.filter(original_order_id=order.original_order_id,user=user.id ,name = extra)
                    if order_field_obj.exists():
                        extra_fields[order_field_obj[0].name] = order_field_obj[0].value
                batch_group_data_order[original_order_id] = json.loads(batch_group_data)
                invoice_data['data'] = batch_group_data_order
                invoice_data['username'] = user.username
                invoice_data['extra_order_fields'] = extra_fields
                user_profile = UserProfile.objects.get(user_id=user.id)
                invoice_data['gstin_no'] = user_profile.gst_number
                invoice_data['company_name'] = user_profile.company.company_name
                invoice_data['company_address'] = user_profile.address
                invoice_data['company_number'] = user_profile.phone_number
                invoice_data['order_no'] = order.order_id
                invoice_data['customer_details'] = customer_details
                invoice_data['customer_address'] = customer_address
                invoice_data['consignee'] = consignee
                invoice_data['iterator'] = iterator
                invoice_data['dc_number'] = dc_number_obj
                invoice_data['total_quantity'] = total_qty
    return render(request, 'templates/toggle/delivery_challan_batch_level.html', invoice_data)


@csrf_exempt
@get_admin_user
def generate_mr_dc(request , user = ''):
    invoice_data = {}
    orders = request.POST.get('selected_orders' ,'')
    iterator=itertools.count()
    batch_group_data_order = OrderedDict()
    total_qty = 0
    search_params = {}
    if orders :
        order = json.loads(orders)[0]
        datum = []
        user = User.objects.get(id=order['source_wh'])
        idsm = StockTransferSummary.objects.filter(stock_transfer__st_type='MR', stock_transfer__order_id=order['order_id'], stock_transfer__status=2, pick_number = order['pick_number'])
        stock_transfer_data = StockTransferSummary.objects.filter(stock_transfer__st_type='MR', stock_transfer__order_id=order['order_id'], stock_transfer__status=2, pick_number = order['pick_number'])
        for invoice_no in stock_transfer_data:
            date = get_local_date(user, invoice_no.stock_transfer.creation_date)
            destination = User.objects.get(id=invoice_no.stock_transfer.st_po.open_st.sku.user)
            dest_up = destination.userprofile
            invoice_data['destination_dept_name'] = "%s %s" %(destination.first_name, destination.last_name)
            invoice_data['destination_dept_address'] = dest_up.address
            invoice_data['destination_dept_gst_number'] = dest_up.gst_number
            if dest_up.phone_number != '0':
                invoice_data['destination_dept_phone'] = dest_up.phone_number
            else:
                invoice_data['destination_dept_phone'] = ''
            creation_date = invoice_no.creation_date
            invoice_date = get_local_date(user, creation_date, send_date='true')
            invoice_data['invoice_time'] = invoice_date.strftime("%H:%M")
            invoice_data['inv_date'] = invoice_date.strftime("%d %b %Y")
            uom_dict = get_uom_with_sku_code(user, invoice_no.stock_transfer.sku.sku_code, uom_type='purchase')
            batch_pcf = uom_dict.get('sku_conversion', 0)
            batch_number = ''
            expiry_date = ''
            manufactured_date = ''
            batch_po_loc_list = list(invoice_no.picklist.picklistlocation_set.filter().values_list('id', flat=True))
            batch_data = PickSequenceMapping.objects.filter(pick_loc_id__in= batch_po_loc_list, pick_number=invoice_no.pick_number).values(
                'pick_loc__stock__batch_detail__batch_no',
                'pick_loc__stock__batch_detail__manufactured_date',
                'pick_loc__stock__batch_detail__expiry_date'
                )
            if batch_data.exists():
                batch_number = batch_data[0]['pick_loc__stock__batch_detail__batch_no']
                expiry_date = batch_data[0]['pick_loc__stock__batch_detail__expiry_date'].strftime(
                    "%d %b, %Y") if batch_data[0]['pick_loc__stock__batch_detail__expiry_date'] else ''
                manufactured_date = batch_data[0]['pick_loc__stock__batch_detail__manufactured_date'].strftime(
                    "%d %b, %Y") if batch_data[0]['pick_loc__stock__batch_detail__manufactured_date'] else ''
            try:
                invoice_no.quantity = float(invoice_no.quantity) / float(batch_pcf)
            except Exception as e:
                invoice_no.quantity = float(invoice_no.quantity) / float(invoice_no.picklist.stock.batch_detail.pcf)
            total_qty += float(invoice_no.quantity)
            temp_dict = {}
            temp_dict['sku_code'] = invoice_no.stock_transfer.sku.sku_code
            temp_dict['desc'] = invoice_no.stock_transfer.sku.sku_desc
            temp_dict['qty'] = invoice_no.quantity
            temp_dict['batch_number'] = batch_number
            temp_dict['manufactured_date'] = manufactured_date
            temp_dict['expiry_date'] = expiry_date
            datum.append(temp_dict)
        invoice_data['username'] = user.username
        invoice_data['data'] = datum
        invoice_data['name'] = "%s - %s" %(str(user.first_name), str(user.last_name))
        user_profile = UserProfile.objects.get(user_id=user.id)
        invoice_data['gstin_no'] = user_profile.gst_number
        invoice_data['company_name'] = user_profile.company.company_name
        invoice_data['company_address'] = user_profile.address
        invoice_data['company_number'] = user_profile.phone_number
        invoice_data['order_no'] = "%s/%s"%(order['order_id'], order['pick_number'])
        invoice_data['total_quantity'] = round(total_qty, 2)
        invoice_data['iterator'] = iterator
    return render(request, 'templates/toggle/mr_transfer_doc.html', invoice_data)


@csrf_exempt
@login_required
@get_admin_user
@fn_timer
def insert_allocation_data(request, user=''):
    myDict = dict(request.POST.iterlists())
    single_key = ['customer_name', 'customer_id','customer_type','remarks', 'location', 'zone']
    number_fields = ["quantity", "unit_price", "cgst_tax", "sgst_tax", "igst_tax"]
    error_dict = {'quantity': 'Quantity'}
    data_list = []
    picklist_exclude_zones = get_exclude_zones(user)
    original_order_id = ''
    for ind in range(0, len(myDict['sku_id'])):
        data_dict = {}
        for key, value in myDict.items():
            if key in single_key:
                val = myDict[key][0]
            else:
                try:
                    val = myDict[key][ind]
                except:
                    pass
            if key in number_fields:
                try:
                    val = float(val)
                except:
                    if key in error_dict.keys():
                        return HttpResponse("Invalid %s" % error_dict[key])
                    else:
                        val = 0
            data_dict[key] = val
        sku_master = SKUMaster.objects.filter(sku_code=data_dict['sku_id'], user=user.id)
        if not sku_master.exists():
            return HttpResponse("Invalid SKU Code %s" % data_dict['sku_id'])
        else:
            data_dict['sku_master_id'] = sku_master[0].id
        customer_master = CustomerMaster.objects.filter(customer_id=data_dict['customer_id'], user=user.id)
        if not customer_master.exists():
            return HttpResponse("Invalid Customer %s" % data_dict['customer_id'])
        else:
            customer_master = customer_master[0]
        stocks = StockDetail.objects.filter(sku_id=data_dict['sku_master_id'],quantity__gt=0,
                                            location__location=data_dict['location']).\
                        exclude(location__zone__zone__in=picklist_exclude_zones)
        stock_qty = check_stock_available_quantity(stocks, user)
        if stock_qty < data_dict['quantity']:
            return HttpResponse("Insufficent Stock for %s" % str(data_dict['sku_id']))
        amt = data_dict['quantity'] * data_dict['unit_price']
        data_dict['invoice_amount'] = amt + ((amt/100) * data_dict['cgst_tax'] + data_dict['sgst_tax'] + \
                                                data_dict['igst_tax'])
        data_list.append(data_dict)
    if data_list:
        try:
            shipment_date = datetime.datetime.now()
            order_id = get_incremental(user, 'allocation_order_id', default_val='1000')
            picklist_number = get_picklist_number(user)
            order_code = 'AL'
            original_order_id = order_code + str(order_id)
            created_orders = []
            for final_data in data_list:
                order_fields_objs = []
                order = OrderDetail.objects.create(order_id=order_id, sku_id=final_data['sku_master_id'], order_code=order_code,
                                           original_order_id=original_order_id, quantity=final_data['quantity'],
                                           shipment_date=shipment_date,
                                           unit_price=final_data['unit_price'], user=user.id,
                                           invoice_amount=final_data['invoice_amount'],
                                           customer_id=customer_master.customer_id,
                                           customer_name=customer_master.name,
                                           remarks = final_data.get('remarks',''),
                                           email_id=customer_master.email_id, telephone=customer_master.phone_number,
                                           address=customer_master.address, status=1,
                                           marketplace='Offline')

                order_field_list = list(filter(lambda x: 'order_field' in x, final_data.keys()))
                for key in order_field_list:
                    value = final_data.get(key,'')
                    order_fields_data = {'original_order_id': order.id, 'name': key, 'value': value,
                                         'user': user.id,'order_type': 'allocate_order_sku'}
                    order_fields_objs.append(OrderFields(**order_fields_data))
                OrderFields.objects.bulk_create(order_fields_objs)
                inter_state = 2
                if customer_master.tax_type == 'inter_state':
                    inter_state = 1
                elif customer_master.tax_type == 'intra_state':
                    inter_state = 0
                CustomerOrderSummary.objects.create(order_id=order.id, inter_state=inter_state,
                                                    cgst_tax=final_data['cgst_tax'], sgst_tax=final_data['sgst_tax'],
                                                    igst_tax=final_data['igst_tax'])
                created_orders.append(order)
                if 'serials' in final_data.keys() and final_data['serials'] and final_data['serials'] != '[]':
                    serial_dict = {'imei': final_data['serials'], 'wms_code': final_data['sku_id']}
                    insert_order_serial(None, serial_dict, order)
            sku_combos, all_sku_stocks, switch_vals = picklist_generation_data(user, picklist_exclude_zones, locations=[final_data['location']])
            stock_status, picklist_number = picklist_generation(created_orders, '',
                                                                picklist_number, user,
                                                                sku_combos, all_sku_stocks, switch_vals,
                                                                status='open', remarks='Allocation Picklist')
            picklist_objs = Picklist.objects.filter(order__user=user.id, picklist_number=picklist_number+1,
                                                    status='open')
            for picklist in picklist_objs.iterator():
                stock = picklist.stock
                update_picked = picklist.reserved_quantity
                stock.quantity -= update_picked
                picklist.picked_quantity = update_picked
                picklist.reserved_quantity = 0
                picklist.status = 'picked'
                picklist.save()
                picklist_locs = picklist.picklistlocation_set.filter()
                picklist_locs.update(status=0, reserved=0)
                stock.save()
                save_sku_stats(user, stock.sku_id, picklist.id, 'picklist', update_picked, stock)
            check_picklist_number_created(user, picklist_number + 1)
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Parts Allocation failed for %s and params are %s and error statement is %s' % (
                str(user.username), str(request.POST.dict()), str(e)))
            return HttpResponse("Failed")
    return HttpResponse("Order ID %s Created Successfuly" % str(original_order_id))


def get_order_allocation_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, col_filters={}):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    search_params = {'order_code': 'AL', 'user': user.id, 'sku_id__in': sku_master_ids}
    lis = ['customer_id', 'customer_name', 'sku__sku_code', 'original_quantity',
           'original_quantity', 'original_quantity']
    headers1, filters, filter_params1 = get_search_params(request)
    # if 'from_date' in filters:
    #     search_params['creation_date__gt'] = filters['from_date']
    # if 'to_date' in filters:
    #     to_date = datetime.datetime.combine(filters['to_date'] + datetime.timedelta(1),
    #                                                          datetime.time())
    #     search_params['creation_date__lt'] = to_date
    print filters
    if 'sku_code' in filters:
        search_params['sku__sku_code'] = filters['sku_code'].upper()
    if 'customer_id' in filters:
        search_params['customer_id__in'] = [filters['customer_id'].split(':')[0]]
    if 'chassis_number' in filters:
        customer_ids = list(CustomerMaster.objects.filter(user=user.id, chassis_number__icontains=filters['chassis_number']).\
                                                    values_list('customer_id', flat=True))
        if search_params.get('customer_id__in'):
            search_params['customer_id__in'] = set(search_params['customer_id__in']).intersection(customer_ids)
        else:
            search_params['customer_id__in'] = customer_ids
    if 'make' in filters:
        attr_query = MasterAttributes.objects.filter(user=user.id, attribute_model='customer',
                                attribute_name='make', attribute_value__icontains=filters['make']).\
                                                    values_list('attribute_id', flat=True)
        customer_ids = list(CustomerMaster.objects.filter(user=user.id, id__in=attr_query).\
                                            values_list('customer_id', flat=True))
        if search_params.get('customer_id__in'):
            search_params['customer_id__in'] = set(search_params['customer_id__in']).intersection(customer_ids)
        else:
            search_params['customer_id__in'] = customer_ids
    if 'model' in filters:
        attr_query = MasterAttributes.objects.filter(user=user.id, attribute_model='customer',
                                attribute_name='model', attribute_value__icontains=filters['model']).\
                                                    values_list('attribute_id', flat=True)
        customer_ids = list(CustomerMaster.objects.filter(user=user.id, id__in=attr_query).\
                                            values_list('customer_id', flat=True))
        if search_params.get('customer_id__in'):
            search_params['customer_id__in'] = set(search_params['customer_id__in']).intersection(customer_ids)
        else:
            search_params['customer_id__in'] = customer_ids

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    orders = OrderDetail.objects.filter(**search_params).annotate(return_qty=Sum('orderreturns__quantity')).\
                                exclude(return_qty__isnull=False, return_qty__gte=F('original_quantity'))
    order_data_ids = orders.values_list('id', flat=True)
    orders_data = OrderDetail.objects.filter(id__in=order_data_ids).values('customer_id', 'customer_name',
                                                                           'sku__sku_code', 'sku__sku_desc').distinct().\
                        annotate(orig_qty = Sum('original_quantity'))
    updated_customer_dict = dict(CustomerMaster.objects.filter(user =user.id,customer_id__in=list(orders_data.values_list('customer_id',flat=True)))
                                 .values_list('customer_id','name'))
    if order_term:
        orders = orders.order_by(order_data)

    temp_data['recordsTotal'] = orders_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    count = 0
    for order in orders_data[start_index: stop_index]:
        make, model, chassis_number = '', '', ''
        quantity = order['orig_qty']
        return_check_dict = {}
        return_check_dict1 = copy.deepcopy(order)
        del return_check_dict1['orig_qty']
        allocation_ids = OrderDetail.objects.filter(id__in=order_data_ids, **return_check_dict1).\
                                                values_list('id', flat=True)
        for key, value in return_check_dict1.items():
            return_check_dict['order__%s' % key] = value
        order_returns = OrderReturns.objects.filter(order_id__in=order_data_ids, **return_check_dict).\
                                                aggregate(Sum('quantity'))['quantity__sum']
        if order_returns:
            quantity -= order_returns
        data_id = count
        customer = CustomerMaster.objects.filter(user=user.id, customer_id=order['customer_id'])
        if customer.exists():
            customer = customer[0]
            chassis_number = customer.chassis_number
            attr_data = dict(MasterAttributes.objects.filter(attribute_id=customer.id, attribute_model='customer',
                                            attribute_name__in=['make', 'model']).values_list('attribute_name', 'attribute_value'))
            make = attr_data.get('Make')
            model = attr_data.get('Model')
        temp_data['aaData'].append(OrderedDict((('data_id', data_id),
                                                ('Vehicle ID', order['customer_id']),
                                                ('Updated Vehicle Number', updated_customer_dict.get(order['customer_id'])),
                                                ('Vehicle Number', order['customer_name']),
                                                ('SKU Code', order['sku__sku_code']),
                                                ('SKU Description', order['sku__sku_desc']),
                                                ('Chassis Number', chassis_number),
                                                ('Make', make),
                                                ('Model', model),
                                                ('Allocated Quantity', quantity),
                                                ('Deallocation Quantity',
                                                 '<input type="number" class="form-control" name="deallocation_qty" min="0" ng-model="showCase.deallocation_qty_val_%s" ng-init="showCase.deallocation_qty_val_%s=0" ng-keyup="showCase.check_dealloc_qty(%s, %s)">' % (str(data_id), str(data_id), str(count), str(data_id))),
                                                ('', '<button type="button" name="submit" value="Save" class="btn btn-primary" ng-click="showCase.save_dealloc_qty(%s, %s)">Save</button>' % (str(count), str(data_id))),
                                                ('id', count),
                                                ('DT_RowClass', 'results'),
                                                ('allocation_ids', json.dumps(list(allocation_ids))))))
        count += 1


@csrf_exempt
@login_required
@get_admin_user
@fn_timer
def insert_deallocation_data(request, user=''):
    from rest_api.views.inbound import create_return_order, save_return_locations, confirm_returns_putaway, returns_order_tracking
    return_wms_codes = []
    receipt_number = get_stock_receipt_number(user)
    mod_locations = []
    marketplace_data = []
    seller_receipt_mapping = {}
    unique_mrp = get_misc_value('unique_mrp_putaway', user.id)
    allocation_ids = json.loads(request.POST.get('allocation_ids', ''))
    confirm_qty = int(request.POST.get('dealloc_qty', 0))
    locations = LocationMaster.objects.filter(zone__user=user.id, location=request.POST['location'])
    if not locations:
        return HttpResponse("Invalid Location")
    if not (allocation_ids or confirm_qty):
        return HttpResponse("Required Fields Missing")
    orders = OrderDetail.objects.filter(id__in=allocation_ids, user=user.id)
    if not orders.exists():
        return HttpResponse("Invalid Order")
    try:
        for order in orders:
            if not confirm_qty:
                break
            credit_note_number = ''
            returned_quantity,quantity = 0,0
            or_obj= OrderReturns.objects.filter(order_id=order.id).aggregate(Sum('quantity'))['quantity__sum']
            if or_obj:
                returned_quantity = or_obj
            if (order.original_quantity - returned_quantity) >= confirm_qty :
                quantity = confirm_qty
                confirm_qty = 0
            else:
                quantity = order.original_quantity - returned_quantity
                confirm_qty = confirm_qty - quantity


            data_dict = {'sku_code': order.sku.sku_code, 'return': quantity, 'damaged': 0, 'order_imei_id': '',
                         'order_id': order.original_order_id, 'order_detail_id': order.id}
            data_dict['id'], status, seller_order_ids, credit_note_number = create_return_order(data_dict, user.id,
                                                                                                  credit_note_number)
            order_returns = OrderReturns.objects.filter(id=data_dict['id'])
            if not order_returns:
                return HttpResponse("Failed")
            order_returns = order_returns[0]
            save_return_locations([order_returns], [], 0, request, user, locations=locations)
            returns_order_tracking(order_returns, user, quantity, 'returned', imei='', invoice_no='')
            returns_location_data = ReturnsLocation.objects.filter(returns_id=order_returns.id, status=1)
            for returns_data in returns_location_data:
                location = returns_data.location.location
                zone = returns_data.location.zone.zone
                status, return_wms_codes, mod_locations, marketplace_data,\
                seller_receipt_mapping = confirm_returns_putaway(user, returns_data, location, zone, returns_data.quantity,
                                                                 unique_mrp, receipt_number, return_wms_codes, mod_locations, marketplace_data,
                                                                 seller_receipt_mapping)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Parts DeAllocation failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Failed")
    return HttpResponse("Success")


@csrf_exempt
@login_required
@get_admin_user
def get_sku_attributes_data(request, user=''):
     sku_code = request.GET.get('wms_code','')
     sku_attributes = get_sku_attributes(user,sku_code)
     return HttpResponse(json.dumps({'attribute_dict': sku_attributes}))


@csrf_exempt
@login_required
@get_admin_user
def get_previous_order_data(request, user=''):
     sku_code = request.GET.get('wms_code','')
     previous_order_data = get_previous_order(user,sku_code)
     return HttpResponse(json.dumps({'previous_order_data': previous_order_data}))

@csrf_exempt
@login_required
@get_admin_user
def get_customer_types(request, user=''):
    customer_types = get_unique_customer_types(user)
    return HttpResponse(json.dumps({'data': customer_types}))


def get_auth_signature(request, user, inv_date):
    auth_signature = ''
    master_docs_obj = MasterDocs.objects.filter(master_type='auth_sign_copy', user_id=user.id).order_by('-creation_date')
    if master_docs_obj.exists():
        url = request.META.get('wsgi.url_scheme')+'://'+request.META.get('HTTP_HOST')+'/'
        if len(master_docs_obj) > 1:
            for auth_sign in master_docs_obj:
                if inv_date > auth_sign.creation_date:
                    auth_signature = url+auth_sign.uploaded_file.url
                    break
                else:
                    auth_signature = url+auth_sign.uploaded_file.url
        if len(master_docs_obj) == 1 or (not auth_signature):
            auth_signature = url+master_docs_obj[0].uploaded_file.url
    return auth_signature

@csrf_exempt
@login_required
@get_admin_user
def create_manual_test_approval(request, user=''):
    user = User.objects.get(username=request.POST['warehouse'])
    main_user = get_company_admin_user(user)
    request_data = dict(request.POST.iterlists())
    group_data = {}
    for i in range(0, len(request_data['test_code'])):
        data_dict = {}
        test_code = request_data['test_code'][i]
        test_obj = TestMaster.objects.filter(test_code=test_code, user=main_user.id)
        data_dict['remarks'] = request_data.get('remarks', '')[i]
        if not test_obj.exists():
            return HttpResponse("Invalid Test Code %s" % test_code)
        else:
            data_dict['test_id'] = test_obj[0].id
        if not request_data['wms_code'][i]:
            continue
        data_dict['test_code'] = test_code
        data_dict['uom'] = request_data['uom'][i]
        data_dict['wms_code'] = request_data['wms_code'][i]
        data_dict['description'] = request_data['description'][i]
        data_dict['test_desc'] = request_data['test_desc'][i]
        try:
            data_dict['sku_quantity'] = float(request_data['sku_quantity'][i])
        except:
            return HttpResponse("Invalid Quantity")
        sku = SKUMaster.objects.filter(user=user.id, sku_code=data_dict['wms_code'])
        if not sku:
            return HttpResponse("Invalid SKU Code %s" % data_dict['wms_code'])
        else:
            data_dict['sku_id'] = sku[0].id
            uom_dict = get_uom_with_sku_code(user, sku[0].sku_code, 'consumption',
                                             uom=request_data['uom'][i])
            pcf = uom_dict['sku_conversion']
            if data_dict.get('sku_quantity', 0):
                sku_stocks = StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE'). \
                    filter(sku_id=sku[0].id, quantity__gt=0).order_by('batch_detail__expiry_date')
                total_qty = sku_stocks.aggregate(Sum('quantity'))['quantity__sum']
                total_qty = total_qty if total_qty else 0
                data_dict['needed_quantity'] = data_dict['sku_quantity'] * pcf
                if total_qty < data_dict['needed_quantity']:
                    return HttpResponse("Insufficient Stock for SKU Code %s" % data_dict['wms_code'])
        group_data.setdefault(data_dict['test_code'], [])
        group_data[test_code].append(data_dict)

    MastersDOA.objects.create(requested_user=request.user, wh_user=user, model_id=0,
                              model_name='ManualTestData', json_data=json.dumps(group_data))

    return HttpResponse("Confirmed Successfully")

@csrf_exempt
@login_required
@get_admin_user
def create_manual_test(request, user=''):
    user = User.objects.get(username=request.POST['warehouse'])
    main_user = get_company_admin_user(user)
    request_data = dict(request.POST.iterlists())
    group_data = {}
    for i in range(0, len(request_data['test_code'])):
        data_dict = {}
        test_code = request_data['test_code'][i]
        test_obj = TestMaster.objects.filter(test_code=test_code, user=main_user.id)
        data_dict['remarks'] = request_data.get('remarks', '')[i]
        if not test_obj.exists():
            return HttpResponse("Invalid Test Code %s" % test_code)
        else:
            data_dict['test_id'] = test_obj[0].id
        data_dict['test_code'] = test_code
        data_dict['wms_code'] = request_data['wms_code'][i]
        try:
            data_dict['sku_quantity'] = float(request_data['sku_quantity'][i])
        except:
            return HttpResponse("Invalid Quantity")
        sku = SKUMaster.objects.filter(user=user.id, sku_code=data_dict['wms_code'])
        if not sku:
            return HttpResponse("Invalid SKU Code %s" % data_dict['wms_code'])
        else:
            data_dict['sku_id'] = sku[0].id
            uom_dict = get_uom_with_sku_code(user, sku[0].sku_code, 'consumption',
                                             uom=request_data['uom'][i])
            pcf = uom_dict['sku_conversion']
            pcf = 1
            if data_dict.get('sku_quantity', 0):
                sku_stocks = StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE'). \
                    filter(sku_id=sku[0].id, quantity__gt=0).order_by('batch_detail__expiry_date')
                total_qty = sku_stocks.aggregate(Sum('quantity'))['quantity__sum']
                total_qty = total_qty if total_qty else 0
                data_dict['needed_quantity'] = data_dict['sku_quantity'] * pcf
                if total_qty < data_dict['needed_quantity']:
                    return HttpResponse("Insufficient Stock for SKU Code %s" % data_dict['wms_code'])
        group_data.setdefault(data_dict['test_code'], [])
        group_data[test_code].append(data_dict)

    for key, value in group_data.items():
        try:
            with transaction.atomic('default'):
                consumption_dict = {'user_id': user.id, 'test_id': value[0]['test_id'], 'total_test': 1,
                                    'consumption_type': 'manual', 'remarks': value[0]['remarks'],
                                    'status': 1}
                consumption = Consumption.objects.create(**consumption_dict)
                # TempJson.objects.create(model_id=consumption.id, model_json=json.dumps(value),
                #                         model_name='manual_test_sku_data')
                consumption_id, prefix, consumption_number, check_prefix, inc_status = get_user_prefix_incremental(user, 'consumption_prefix', None)
                for val in value:
                    sku = SKUMaster.objects.get(id=val['sku_id'])
                    quantity = val['needed_quantity']
                    sku_stocks = StockDetail.objects.using('default').select_for_update().\
                        exclude(location__zone__zone='DAMAGED_ZONE').\
                        filter(sku_id=sku.id, quantity__gt=0).order_by('batch_detail__expiry_date')
                    consumption_data = ConsumptionData.objects.create(
                        order_id=consumption_id,
                        consumption_number=consumption_number,
                        sku_id=sku.id,
                        quantity=quantity,
                        consumption_id=consumption.id,
                        consumption_type=1
                    )
                    update_stock_detail(sku_stocks, quantity, user,
                                        consumption_data.id, transact_type='consumption',
                                        mapping_obj=consumption_data, inc_type='dec')
        except Exception as e:
            log_message(log, request, user, "Manual Test Creation Failed", request_data)
            import traceback
            log.debug(traceback.format_exc())
            return HttpResponse("Creation Failed")
    data_id = request.POST['data_id']
    MastersDOA.objects.filter(id=data_id).update(doa_status='approved', validated_by=request.user.username)
    return HttpResponse("Confirmed Successfully")


@csrf_exempt
def view_manual_test_entries(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['creation_date', 'user', 'user', 'test__test_code', 'quantity', 'remarks']
    users = [user.id]
    users = check_and_get_plants_depts(request, users)
    user_ids = list(users.values_list('id', flat=True))
    masters_doa = MastersDOA.objects.filter(wh_user_id__in=user_ids, model_name='ManualTestData',
                                            doa_status__in=['pending', 'rejected'])
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = masters_doa.order_by(order_data)
    if search_term:
        master_data = masters_doa.filter(Q(st_po__open_st__warehouse__username__icontains=search_term) |
                                               Q(quantity__icontains=search_term) | Q(order_id__icontains=search_term) |
                                               Q(sku__sku_code__icontains=search_term) |
                                               Q(st_seller__seller_id__icontains=search_term) |
                                               Q(st_seller__name__icontains=search_term)).order_by(order_data)
    temp_data['recordsTotal'] = masters_doa.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    count = 0
    for data in masters_doa[start_index:stop_index]:
        dept = data.wh_user
        store = get_admin(dept)
        json_data = json.loads(data.json_data)
        total_qty = len(json_data.keys())
        data_dict = {'Created Date': get_local_date(user, data.creation_date),
                     'Requested User': data.requested_user.first_name,
                    'Store': store.first_name,
                     'Department': dept.first_name, 'Test Quantity': total_qty,
                     'Status': data.doa_status.capitalize(),
                    'DT_RowAttr': {'data-id': data.id}, 'id': count}
        temp_data['aaData'].append(data_dict)
        count = count + 1

@csrf_exempt
@login_required
@get_admin_user
def get_manual_test_approval_pending(request, user=''):
    masters_doa = MastersDOA.objects.filter(id=request.GET['id'])
    doa = masters_doa[0]
    json_data = json.loads(doa.json_data)
    dept = doa.wh_user
    store = get_admin(dept)
    data_dict = {'data': [], 'data_id': doa.id, 'plant_name': store.first_name,
                                    'warehouse_name': dept.first_name, 'warehouse': dept.username}
    for key, value in json_data.items():
        sub_data = []
        for val in value:
            sub_data.append({'wms_code': val['wms_code'], 'order_quantity': 1, 'uom': val['uom'],
                             'sku_quantity': float(val['sku_quantity']),
                             'description': val['description']})
        data_dict['data'].append({'test_code': value[0]['test_code'], 'test_desc': value[0]['test_desc'],
                                  'sub_data': sub_data, 'remarks': value[0]['remarks']})
    return HttpResponse(json.dumps({'data': data_dict}))


def get_closing_stock_ui_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, col_filters={}):
    users = [user.id]
    if request.user.is_staff and user.userprofile.warehouse_type == 'ADMIN':
        users = get_related_users_filters(user.id)
    else:
        users = [user.id]
        users = check_and_get_plants_depts_wo_request(request.user, user, users)
    lis = ['user', 'user', 'user','sku_code', 'sku_desc', 'stock_quantity', 'sku_code', 'sku_code', 'sku_code', 'sku_code', 'sku_code', 'sku_code',
    'sku_code', 'sku_code']
    headers1, search_params, filter_params1 = get_search_params(request)
    search_parameters = {}
    if 'sku_code' in search_params:
        search_parameters['sku_code'] = search_params['sku_code'].upper()
    if 'sku_category' in search_params:
       search_parameters['sku_category'] = search_params['sku_category']
    user_query = False
    if 'plant_code' in search_params:
        plant_code = search_params['plant_code']
        plant_users = list(users.filter(userprofile__stockone_code=plant_code,
                                    userprofile__warehouse_type__in=['STORE', 'SUB_STORE']).values_list('username', flat=True))
        if plant_users:
            users = get_related_users_filters(user.id, warehouse_types=['DEPT'], warehouse=plant_users, send_parent=True)
        else:
            users = User.objects.none()
        user_query = True
    if 'plant_name' in search_params.keys():
        plant_name = search_params['plant_name']
        plant_users = list(users.filter(first_name=plant_name, userprofile__warehouse_type__in=['STORE', 'SUB_STORE']).\
                        values_list('username', flat=True))
        if plant_users:
            users = get_related_users_filters(user.id, warehouse_types=['DEPT'], warehouse=plant_users, send_parent=True)
        else:
            users = User.objects.none()
        user_query = True
    if 'sister_warehouse' in search_params:
        dept_type = search_params['sister_warehouse']
        if dept_type.lower() != 'na':
            users = users.filter(userprofile__stockone_code=dept_type)
        else:
            users = users.filter(userprofile__warehouse_type__in=['STORE', 'SUB_STORE'])
    user_ids = list(users.values_list('id', flat=True))
    if not user_query:
        skus = SKUMaster.objects.none()
    else:
        skus = SKUMaster.objects.filter(user__in=user_ids, **search_parameters).values('id', 'sku_code', 'sku_desc', 'average_price', 'user').\
                                exclude(id__in=AssetMaster.objects.all()).exclude(id__in=ServiceMaster.objects.all()).\
                                exclude(id__in=OtherItemsMaster.objects.all()).exclude(id__in=TestMaster.objects.all()).annotate(stock_quantity=Sum('stockdetail__quantity')).distinct()
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if order_term:
        skus = skus.order_by(order_data)
    temp_data['recordsTotal'] = skus.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']

    count = 0
    skus = skus[start_index: stop_index]
    model_sku_codes = []
    model_sku_ids = []
    stock_dict = {}
    consumption_dict = {}
    for sku in skus:
        model_sku_codes.append(sku['sku_code'])
        model_sku_ids.append(sku['id'])

    stocks = StockDetail.objects.filter(sku_id__in=model_sku_ids, quantity__gt=0).\
                                exclude(location__zone__zone='DAMAGED_ZONE').order_by('batch_detail__expiry_date').only('sku_id', 'quantity')
    for stock in stocks:
        stock_dict.setdefault(stock.sku_id, 0)
        stock_dict[stock.sku_id] += stock.quantity
    cons_filter = {'sku_id__in': model_sku_ids, 'quantity__gt': 0}
    if 'year' in search_params and 'month_no' in search_params:
        first_date = datetime.datetime.strptime('%s-%s-1' % (str(search_params['year']),str(search_params['month_no'])), '%Y-%m-%d')
        last_date = first_date + relativedelta(months=1)
        cons_filter['creation_date__range'] = [first_date.date(), last_date.date()]
    skus_uom_dict = get_uom_with_multi_skus(user, model_sku_codes, uom_type='purchase')
    consumption = ConsumptionData.objects.filter(**cons_filter).\
                                            only('sku_id', 'quantity', 'price')
    for cons in consumption:
       consumption_dict.setdefault(cons.sku_id, {'qty': 0, 'value': 0})
       uom_dict = skus_uom_dict.get(sku['sku_code'], {})
       pcf = uom_dict.get('sku_conversion', 1)
       cons_pqty = cons.quantity/pcf
       cons_value = cons_pqty * cons.price
       consumption_dict[cons.sku_id]['qty'] += cons.quantity
       consumption_dict[cons.sku_id]['value'] += cons_value
    dept_mapping = copy.deepcopy(DEPARTMENT_TYPES_MAPPING)
    for sku in skus:
        user_obj = User.objects.get(id=sku['user'])
        department = ''
        if user_obj.userprofile.warehouse_type == 'DEPT':
            department = dept_mapping.get(user_obj.userprofile.stockone_code, user_obj.userprofile.stockone_code)
            user_obj = get_admin(user_obj)
        plant_code = user_obj.userprofile.stockone_code
        plant_name = user_obj.first_name
        data_id = sku['id']
        stock_qty = stock_dict.get(data_id, 0)
        cons_dict = consumption_dict.get(data_id, {})
        cons_qty = cons_dict.get('qty', 0)
        cons_value = round(cons_dict.get('value', 0), 5)
        uom_dict = skus_uom_dict.get(sku['sku_code'], {})
        base_uom = uom_dict.get('base_uom', '')
        pcf = uom_dict.get('sku_conversion', 1)
        pqty = stock_qty/pcf
        cons_pqty = cons_qty/pcf
        stock_value = round(pqty * sku['average_price'], 5)
        #cons_value = cons_pqty * sku['average_price']
        cls_input = '<input type="number" class="form-control" name="closing_qty" min="0" ng-model="showCase.closing_qty_val_%s" ng-init="showCase.closing_qty_val_%s=0" ng-keyup="showCase.check_closing_qty(%s, %s, showCase.closing_qty_val_%s)" style="width: 120px !important">' % (str(data_id), str(data_id), str(count), str(data_id), str(data_id))
        remarks_input = '<input type="text"  class="form-control" name="remarks" ng-model="showCase.remarks_%s" ng-init="showCase.remarks_%s=%s" auto-complete="false" style="width: 150px !important">' % \
                                (str(data_id), str(data_id), str("''"))
        data_dict = OrderedDict((('data_id', data_id),
                                                ('Plant Code', plant_code),
                                                ('Plant Name', plant_name),
                                                ('Department', department),
                                                ('SKU Code', sku['sku_code']),
                                                ('SKU Description', sku['sku_desc']),
                                                ('Current Available Stock', stock_qty),
                                                ('Base UOM', base_uom),
                                                ('Stock Value', stock_value),
                                                ('Closing Quantity', cls_input),
                                                ('Consumption Quantity', cons_qty),
                                                ('Consumption Value', cons_value),
                                                ('Remarks', remarks_input),
                                                ('sku_avg_price', sku['average_price']),
                                                ('sku_pcf', pcf),
                                                ('', '<button type="button" name="submit" value="Save" class="btn btn-primary" ng-click="showCase.save_closing_qty(%s, %s)" ng-disabled="showCase.conf_disable">Save</button>' % (str(count), str(data_id))),
                                                ('id', data_id),
                                                ('DT_RowClass', 'results'),
                                ))

        temp_data['aaData'].append(data_dict)
        count += 1

@csrf_exempt
@login_required
@get_admin_user
def save_closing_stock_ui(request, user=''):
    log.info('Request params for Closing Stock UI for ' + user.username + ' is ' + str(request.POST.dict()))
    from rest_api.views.uploads import update_closing_stock_quantity
    data_id = request.POST['data_id']
    quantity = float(request.POST['quantity'])
    year = request.POST['year']
    month = request.POST['month']
    sku = SKUMaster.objects.get(id=data_id)
    user = User.objects.get(id=sku.user)
    stocks = StockDetail.objects.filter(sku_id=sku.id, quantity__gt=0).exclude(
                                        location__zone__zone='DAMAGED_ZONE').order_by('batch_detail__expiry_date')
    stock_quantity = stocks.aggregate(Sum('quantity'))['quantity__sum']
    stock_quantity = stock_quantity if stock_quantity else 0
    uom_dict = get_uom_with_sku_code(user, sku.sku_code, uom_type='purchase')
    if stock_quantity < quantity:
        return HttpResponse("Quantity is less than Stock quantity")
    data_dict = {}
    data_dict['sku'] = sku
    data_dict['user'] = user
    data_dict['base_uom_quantity'] = quantity
    data_dict['stocks'] = stocks
    data_dict['uom_dict'] = uom_dict
    data_dict['remarks'] = request.POST.get('remarks', '')
    try:
        update_closing_stock_quantity([data_dict], year, month)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Closing Stock UI failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
        return HttpResponse("Failed")

    return HttpResponse("Success")

def get_plant_dept_subsidary_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, col_filters={}):
    user = User.objects.get(username='mhl_admin')
    users = get_related_users_filters(user.id)
    headers1, search_params, filter_params1 = get_search_params(request)
    search_parameters = {}
    user_query = False
    if 'plant_code' in search_params:
        plant_code = search_params['plant_code']
        plant_users = list(users.filter(userprofile__stockone_code=plant_code,
                                    userprofile__warehouse_type__in=['STORE', 'SUB_STORE']).values_list('username', flat=True))
        if plant_users:
            users = get_related_users_filters(user.id, warehouse_types=['DEPT'], warehouse=plant_users, send_parent=True)
        else:
            users = User.objects.none()
        user_query = True
    if 'plant_name' in search_params.keys():
        plant_name = search_params['plant_name']
        plant_users = list(users.filter(first_name=plant_name, userprofile__warehouse_type__in=['STORE', 'SUB_STORE']).\
                        values_list('username', flat=True))
        if plant_users:
            users = get_related_users_filters(user.id, warehouse_types=['DEPT'], warehouse=plant_users, send_parent=True)
        else:
            users = User.objects.none()
        user_query = True
    if 'sister_warehouse' in search_params:
        dept_type = search_params['sister_warehouse']
        if dept_type.lower() != 'na':
            users = users.filter(userprofile__stockone_code=dept_type)
        else:
            users = users.filter(userprofile__warehouse_type__in=['STORE', 'SUB_STORE'])
    user_ids = list(users.values_list('id', flat=True))
    total_data = UserProfile.objects.filter(user_id__in = user_ids, warehouse_type__in = ['SUB_STORE', 'STORE', 'DEPT']).values('user_id').distinct()
    temp_data['recordsTotal'] = total_data.count()
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    count = 0
    total_data = total_data[start_index: stop_index]
    dept_mapping = copy.deepcopy(DEPARTMENT_TYPES_MAPPING)
    for source in total_data:
        try:
            user_obj = User.objects.get(id=source['user_id'])
            department, subsidary, plant_addresss = '', '', ''
            if user_obj.userprofile.warehouse_type == 'DEPT':
                department = dept_mapping.get(user_obj.userprofile.stockone_code, user_obj.userprofile.stockone_code)
                user_obj = get_admin(user_obj)
            plant_code = user_obj.userprofile.stockone_code
            plant_name = user_obj.first_name
            #dept, plant, subsidary = get_plant_subsidary_and_department(user_obj)
            #if subsidary:
            #    #subsidary = User.objects.get(id=subsidary)
            subsidary = user_obj.userprofile.company.company_name
            plant_address = UserAddresses.objects.filter(user=user_obj, address_type='Shipment Address').order_by('-creation_date')
            if plant_address.exists():
                plant_address = plant_address[0]
                plant_addresss = "%s - %s" %(plant_address.address, plant_address.pincode)
            data_dict = OrderedDict((
                                    ('Plant Code', plant_code),
                                    ('Plant Name', plant_name),
                                    ('Plant Internal ID', user_obj.userprofile.reference_id),
                                    ('Plant Creation Date',get_local_date(user_obj, user_obj.date_joined)),
                                    ('Plant Address', plant_addresss),
                                    ('Subsidiary', subsidary),
                                    ('Department', department),
                                    ))
            temp_data['aaData'].append(data_dict)
            count += 1
        except Exception as e:
            pass
