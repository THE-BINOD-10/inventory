import datetime
import json
from collections import OrderedDict
from operator import itemgetter
import traceback

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from miebach_utils import OrderUploads, GenericOrderDetailMapping, CustomerOrderSummary, UserProfile
from common import get_filtered_params, get_admin, order_cancel_functionality, order_push
from miebach_admin.custom_decorators import get_admin_user, login_required
from miebach_admin.models import CustomerUserMapping, CustomerMaster, UserGroups, User
from utils import *


log = init_logger('logs/upload_po.log')


def upload_po(request):
    po_number = request.POST.get('po_number', '')
    customer_name = request.POST.get('customer_name', '')
    po_file = request.FILES.get('po_file', '')
    if not po_number and customer_name and po_file:
        return HttpResponse('Fields are missing.')
    try:
        upload_po_map = {'uploaded_user_id': request.user.id, 'po_number': po_number,
                         'customer_name': customer_name}
        customer_qs = CustomerUserMapping.objects.filter(user_id=request.user.id)
        if not customer_qs:
            return HttpResponse('No Customer ID Mapping')
        customer_id = customer_qs[0].customer.id

        gen_id = GenericOrderDetailMapping.objects.filter(po_number=po_number, client_name=customer_name,
                                                          customer_id=customer_id).order_by('-id')
        if gen_id:
            upload_po_map['generic_order_id'] = gen_id[0].generic_order_id
        ord_obj = OrderUploads.objects.filter(**upload_po_map)
        if ord_obj:
            ord_obj = ord_obj[0]
            ord_obj.uploaded_file = po_file
            ord_obj.uploaded_date = datetime.datetime.today()
        else:
            upload_po_map['uploaded_file'] = po_file
            upload_po_map['uploaded_date'] = datetime.datetime.today()
            ord_obj = OrderUploads(**upload_po_map)
        ord_obj.save()
        log.info('Uploaded PO for user %s and params are %s' % (
            str(request.user.username), str(request.POST.dict())))
    except Exception as e:
        log.debug(traceback.format_exc())
        log.info('Upload PO is failed for user %s and params are %s and error statement is %s' % (
            str(request.user.username), str(request.POST.dict()), str(e)))
    return HttpResponse('Uploaded Successfully')


def get_updated_pos(request):
    data = {}
    upload_po_id = request.POST.get('id', '')
    if not upload_po_id:
        return HttpResponse('Uploaded PO id is not found')
    up_obj = OrderUploads.objects.filter(id=upload_po_id)
    if not up_obj:
        return HttpResponse('No record found')
    else:
        up_obj = up_obj[0]
    try:
        cm_user_map = CustomerUserMapping.objects.get(user_id=up_obj.uploaded_user.id)
        cm_obj = CustomerMaster.objects.filter(id=cm_user_map.customer_id)
        gen_ord_map = get_skucode_quantity(up_obj.po_number, up_obj.customer_name, cm_obj[0])
        if up_obj.uploaded_file.name:
            uploaded_file_url = up_obj.uploaded_file.url
        else:
            uploaded_file_url = ''
        data = {'id': up_obj.id, 'uploaded_user': up_obj.uploaded_user.first_name, 'po_number': up_obj.po_number,
                'uploaded_date': up_obj.uploaded_date.strftime('%Y-%m-%d'), 'customer_name': up_obj.customer_name,
                'uploaded_file': uploaded_file_url, 'verification_flag': up_obj.verification_flag,
                'remarks': up_obj.remarks, 'sku_quantity': gen_ord_map}
    except Exception as e:
        log.debug(traceback.format_exc())
        log.info('Getting updated POs failed for user %s and params are %s and error statement is %s' % (
            str(request.user.username), str(request.POST.dict()), str(e)))
    return HttpResponse(json.dumps({'data': data}))


def get_skucode_quantity(po_number, customer_name, uploaded_user):
    gen_ord_qs = GenericOrderDetailMapping.objects.filter(po_number=po_number, client_name=customer_name)
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
            if uploaded_user.user == user_profile.user_id:
                po['warehouse_level'] = 0
            else:
                po['warehouse_level'] = user_profile.warehouse_level
            total_tax = 0
            if customer_summary:
                customer_summary = customer_summary[0]
                for tax in ['sgst', 'cgst', 'igst']:
                    po[tax+'_tax'] = customer_summary[tax+'_tax']
                    po[tax] = round((po['amount']/100)*po[tax+'_tax'], 2)
                    total_tax += po[tax]
            po['invoice_amt'] = po['amount'] + total_tax
            gen_ord_map.append(po)
    return gen_ord_map


def get_uploaded_pos_by_customers(start_index, stop_index, temp_data, search_term, order_term, col_num,
                                  request, user, filters={}):
    lis = ['id', 'uploaded_user__first_name', 'po_number', 'uploaded_date', 'customer_name', 'verification_flag']
    all_data = OrderedDict()
    orderprefix_map = {}
    filter_params = get_filtered_params(filters, lis)
    if user.userprofile.warehouse_type == 'DIST':
        dist_customers = CustomerUserMapping.objects.filter(customer__user=user.id).values_list('user_id', flat=True)
        if dist_customers:
            filter_params['uploaded_user_id__in'] = dist_customers
    elif user.userprofile.warehouse_type == 'CENTRAL_ADMIN':
        all_wh_dists_obj = UserGroups.objects.filter(admin_user=user.id)
        if request.user.userprofile.zone:
            all_wh_dists = all_wh_dists_obj.filter(user__userprofile__zone=request.user.userprofile.zone).values_list('user_id', flat=True)
        else:
            all_wh_dists = all_wh_dists_obj.values_list('user_id', flat=True)
        orderprefix_map = dict(all_wh_dists_obj.values_list('user_id', 'user__userprofile__order_prefix'))
        customers = CustomerUserMapping.objects.filter(customer__user__in=all_wh_dists).values_list('user_id', flat=True)
        if customers:
            filter_params['uploaded_user_id__in'] = customers
    if search_term:
        results = OrderUploads.objects.filter(Q(uploaded_user__first_name__icontains=search_term) |
                                              Q(po_number__icontains=search_term) |
                                              Q(customer_name__icontains=search_term) |
                                              Q(verification_flag__icontains=search_term), **filter_params
                                              ).order_by('-id')
    else:
        results = OrderUploads.objects.filter(**filter_params).order_by('-id')
    for result in results:
        generic_id = ''
        distributor = ''
        emiza_order_ids = []
        customer_user = CustomerUserMapping.objects.filter(user=result.uploaded_user.id)
        if customer_user:
            customer_user = customer_user[0]
            dist_id = customer_user.customer.user
            distributor = UserProfile.objects.get(user=dist_id).user.username
            generic_id = result.generic_order_id
            order_data = GenericOrderDetailMapping.objects.filter(customer_id=customer_user.customer.id,
                         po_number=result.po_number, client_name=result.customer_name, generic_order_id=generic_id)
            if order_data:
                ord_det_ids = order_data.values_list('orderdetail__user', 'orderdetail__order_id')
                for usr, org_id in ord_det_ids:
                    if usr in orderprefix_map:
                        emiza_id = orderprefix_map[usr]+'MN'+str(org_id)
                        emiza_order_ids.append(emiza_id)
                emiza_order_ids = list(set(emiza_order_ids))
        cond = (result.id, result.uploaded_user, result.po_number, result.uploaded_date,
                result.customer_name, result.uploaded_file, result.verification_flag, result.remarks,
                generic_id, result.uploaded_user.userprofile.zone, distributor, tuple(emiza_order_ids))
        all_data.setdefault(cond, 0)
    temp_data['recordsTotal'] = len(all_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for key, value in all_data.iteritems():
        _id, uploaded_user, po_number, uploaded_date, customer_name, uploaded_file, \
        verification_flag, remarks, generic_id, zone, distributor, emiza_order_ids = key
        temp_data['aaData'].append(
            {'id': _id, 'uploaded_user': uploaded_user.first_name, 'po_number': po_number,
             'uploaded_date': uploaded_date.strftime('%Y-%m-%d'),
             'customer_name': customer_name, 'uploaded_file': str(uploaded_file),
             'verification_flag': verification_flag, 'zone': zone, 'order_id': generic_id, 'distributor': distributor,
             'emizaids': emiza_order_ids})
    sort_col = lis[col_num]

    # if order_term == 'asc':
    #     temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
    # else:
    #     temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]


@csrf_exempt
@login_required
@get_admin_user
def validate_po(request, user=''):
    po_number = request.POST.get('po_number', '')
    uploaded_user = request.POST.get('uploaded_user', '')
    customer_name = request.POST.get('customer_name', '')
    verification_flag = request.POST.get('verification_flag', '')
    remarks = request.POST.get('remarks', '')
    if not po_number and uploaded_user and customer_name:
        return HttpResponse('Values Missing')
    try:
        order_po_obj = OrderUploads.objects.filter(uploaded_user__first_name=uploaded_user, po_number=po_number,
                                                   customer_name=customer_name)
        if not order_po_obj:
            return HttpResponse('Record not found')
        else:
            order_po_obj = order_po_obj[0]
            order_po_obj.verification_flag = verification_flag
            order_po_obj.remarks = remarks
            order_po_obj.save()
    except Exception as e:
        log.debug(traceback.format_exc())
        log.info('Getting updated POs failed for user %s and params are %s and error statement is %s' % (
            str(request.user.username), str(request.POST.dict()), str(e)))
        return HttpResponse('Update Failed')
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def pending_pos(request, user=''):
    uploaded_user_id = request.user.id
    pending_objs = OrderUploads.objects.filter(uploaded_user=uploaded_user_id,
                                               uploaded_file='').order_by('-uploaded_date')
    pending_pos_list = []
    for pending_obj in pending_objs:
        po_number = pending_obj.po_number
        customer_name = pending_obj.customer_name
        pending_pos_list.append({'po_number': po_number, 'customer_name': customer_name})
    return HttpResponse(json.dumps({'data': pending_pos_list}))


@csrf_exempt
@login_required
def sm_cancel_order_from_uploaded_pos(request):
    message = 'Success'
    upload_id = request.GET.get('upload_id', '')
    if not upload_id:
        return HttpResponse("No Upload ID")
    try:
        upload_qs = OrderUploads.objects.filter(id=upload_id)
        if upload_qs:
            upload_obj = upload_qs[0]
            po_number = upload_obj.po_number
            client_name = upload_obj.customer_name
            reseller = upload_obj.uploaded_user
            cm_obj = CustomerUserMapping.objects.filter(user_id=reseller)
            if not cm_obj:
                return HttpResponse("There is something wrong, pelase check with StockOne Team")
            cm_id = cm_obj[0].customer_id
            gen_qs = GenericOrderDetailMapping.objects.filter(po_number=po_number, client_name=client_name,
                                                              customer_id=cm_id)
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
                upload_qs.delete()
                gen_qs.delete()
    except Exception as e:
        log.debug(traceback.format_exc())
        log.info('Order Cancellation failed for user %s and params are %s and error statement is %s' % (
            str(request.user.username), str(request.GET.dict()), str(e)))
    return HttpResponse(message)
