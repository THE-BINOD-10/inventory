import datetime
import json
from collections import OrderedDict
from operator import itemgetter

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from miebach_utils import OrderUploads, GenericOrderDetailMapping
from common import get_filtered_params
from miebach_admin.custom_decorators import get_admin_user, login_required
from miebach_admin.models import CustomerUserMapping


def upload_po(request):
    po_number = request.POST.get('po_number', '')
    customer_name = request.POST.get('customer_name', '')
    po_file = request.FILES.get('po_file', '')
    if not po_number and customer_name and po_file:
        return HttpResponse('Fields are missing.')

    upload_po_map = {'uploaded_user_id': request.user.id, 'po_number': po_number,
                     'customer_name': customer_name}
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
    return HttpResponse('Uploaded Successfully')


def get_updated_pos(request):
    upload_po_id = request.POST.get('id', '')

    if not upload_po_id:
        return HttpResponse('Uploaded PO id is not found')
    up_obj = OrderUploads.objects.filter(id=upload_po_id)
    if not up_obj:
        return HttpResponse('No record found')
    else:
        up_obj = up_obj[0]
    gen_ord_map = get_skucode_quantity(up_obj.po_number, up_obj.customer_name)
    if up_obj.uploaded_file.name:
        uploaded_file_url = up_obj.uploaded_file.url
    else:
        uploaded_file_url = ''
    data = {'id': up_obj.id, 'uploaded_user': up_obj.uploaded_user.first_name, 'po_number': up_obj.po_number,
            'uploaded_date': up_obj.uploaded_date.strftime('%Y-%m-%d'), 'customer_name': up_obj.customer_name,
            'uploaded_file': uploaded_file_url, 'verification_flag': up_obj.verification_flag,
            'remarks': up_obj.remarks, 'sku_quantity': gen_ord_map}
    return HttpResponse(json.dumps({'data': data}))


def get_skucode_quantity(po_number, customer_name):
    gen_ord_qs = GenericOrderDetailMapping.objects.filter(po_number=po_number, client_name=customer_name).values(
        'orderdetail__sku__sku_code', 'orderdetail__quantity', 'orderdetail__unit_price', 'orderdetail__invoice_amount')
    gen_ord_map = [{'sku_code': i['orderdetail__sku__sku_code'],
                    'quantity': i['orderdetail__quantity'],
                    'unit_price': i['orderdetail__unit_price'],
                    'invoice_amt': i['orderdetail__invoice_amount']} for i in gen_ord_qs]
    return gen_ord_map


def get_uploaded_pos_by_customers(start_index, stop_index, temp_data, search_term, order_term, col_num,
                                  request, user, filters={}):
    lis = ['id', 'uploaded_user__first_name', 'po_number', 'uploaded_date', 'customer_name', 'verification_flag']
    all_data = OrderedDict()
    filter_params = get_filtered_params(filters, lis)
    if user.userprofile.warehouse_type == 'DIST':
        dist_customers = CustomerUserMapping.objects.filter(customer__user=user.id).values_list('user_id', flat=True)
        if dist_customers:
            filter_params['uploaded_user_id__in'] = dist_customers
    if search_term:
        results = OrderUploads.objects.filter(Q(uploaded_user__first_name__icontains=search_term) |
                                              Q(po_number__icontains=search_term) |
                                              Q(customer_name__icontains=search_term) |
                                              Q(verification_flag__icontains=search_term), **filter_params
                                              ).order_by('id')
    else:
        results = OrderUploads.objects.filter(**filter_params)
    for result in results:
        cond = (result.id, result.uploaded_user, result.po_number, result.uploaded_date,
                result.customer_name, result.uploaded_file, result.verification_flag, result.remarks,
                result.uploaded_user.userprofile.zone)
        all_data.setdefault(cond, 0)
    temp_data['recordsTotal'] = len(all_data)
    temp_data['recordsFiltered'] = temp_data['recordsTotal']
    for key, value in all_data.iteritems():
        _id, uploaded_user, po_number, uploaded_date, customer_name, uploaded_file, \
        verification_flag, remarks, zone = key
        temp_data['aaData'].append(
            {'id': _id, 'uploaded_user': uploaded_user.first_name, 'po_number': po_number,
             'uploaded_date': uploaded_date.strftime('%Y-%m-%d'),
             'customer_name': customer_name, 'uploaded_file': str(uploaded_file),
             'verification_flag': verification_flag, 'zone': zone})
    sort_col = lis[col_num]

    if order_term == 'asc':
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
    else:
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)
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
    order_po_obj = OrderUploads.objects.filter(uploaded_user__first_name=uploaded_user, po_number=po_number,
                                               customer_name=customer_name)
    if not order_po_obj:
        return HttpResponse('Record not found')
    else:
        order_po_obj = order_po_obj[0]
        order_po_obj.verification_flag = verification_flag
        order_po_obj.remarks = remarks
        order_po_obj.save()
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
