from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import csv
from django.template import loader, Context
from django.shortcuts import render, redirect
from django.contrib import auth
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import smart_str
from models import *
from django.contrib.auth.models import User,Permission
from custom_decorators import login_required,get_admin_user
from dateutil.relativedelta import relativedelta
from itertools import chain
from django.db.models import Q, F
from collections import OrderedDict
from django.template.defaultfilters import date as date_format
from django.core.serializers.json import DjangoJSONEncoder
import logging
import pprint
import copy
import json
import os
import subprocess
import sys
import re
from send_message import send_sms
from miebach_utils import *
from xlwt import Workbook, easyxf
from xlrd import open_workbook, xldate_as_tuple
from django.conf import settings
from mail_server import send_mail, send_mail_attachment
from sellerworx_api import *
from operator import itemgetter
from django.db.models import Sum, Count
from itertools import groupby
import traceback
import miebach_utils
import operator

from generate_reports import *

logger = logging.getLogger(__name__)
import datetime, time
from django.utils import timezone
import pytz
import time

def get_misc_value(misc_type, user):
    misc_value = 'false'
    data = MiscDetail.objects.filter(user=user, misc_type=misc_type)
    if data:
        misc_value = data[0].misc_value
    return misc_value

def get_order_id(user_id):
    order_detail_id = OrderDetail.objects.filter(user=user_id, order_code__in=['MN', 'Delivery Challan', 'sample', 'R&D', 'online', 'offline', 'Pre Order']).order_by('-order_id')
    if order_detail_id:
        order_id = int(order_detail_id[0].order_id) + 1
    else:
        order_id = 1001

    return order_id

def insert_sku_stock_data(data, sku, user, receipt_number):
    stock_data1 = StockDetail.objects.filter(sku_id=data[0].id, location__location='TEMP1', sku__user=user.id)
    stock_data2 = StockDetail.objects.filter(sku_id=data[0].id, sku__user=user.id).exclude(location__location='TEMP1')
    quantity = int(sku['stock'])
    if stock_data1 and not stock_data2:
        total_stock_quantity = 0
        for stock in stock_data1:
            total_stock_quantity += int(stock.quantity)

        remaining_quantity = total_stock_quantity - quantity
        for stock in stock_data1:
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

    elif not stock_data1 and not stock_data2:
        if not quantity == 0:
            inventory_data = {'status': 1, 'creation_date': str(datetime.datetime.now()), 'receipt_date': str(datetime.datetime.now()),
                              'receipt_number': receipt_number, 'sku_id': data[0].id, 'location_id': 21, 'quantity': quantity}
        inventory = StockDetail(**inventory_data)
        inventory.save()

IGNORE_MARKETPLACE = ['Amazon', 'Snapdeal']
PICKLIST_SKIP_LIST = ('sortingTable_length', 'fifo-switch', 'ship_reference', 'selected', 'remarks')

def haserror(f):
    def new_f(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception:
            error_message = 'Failed at %s' % f.func_name
            receivers = []
            send_mail(receivers, 'High: Issue in WMS UI', error_message)
            return HttpResponseRedirect('/errorpage/')
    return new_f

@csrf_exempt
def check_sku(request):
    sku_code = request.GET.get('sku_code')
    sku_master = SKUMaster.objects.filter(sku_code=sku_code)
    if sku_master:
        return HttpResponse("confirmed")
    return HttpResponse("%s not found" % sku_code)

@csrf_exempt
def get_local_date(user, input_date):
    utc_time = input_date.replace(tzinfo=pytz.timezone('UTC'))
    user_details = UserProfile.objects.filter(user_id = user.id)
    for user in user_details:
        time_zone = user.timezone
    local_time = utc_time.astimezone(pytz.timezone(time_zone))
    dt = local_time.strftime("%d %b, %Y %I:%M %p")
    return dt

@csrf_exempt
def set_timezone(request):
    timezone = request.GET['tz']
    user_details = UserProfile.objects.filter(user_id = request.user.id)
    for user in user_details:
        if not user.timezone:
            user.timezone = timezone;
            user.save()
    return HttpResponse("Success")



def po_message(po_data, phone_no, user_name, f_name, order_date):
    data = '%s Orders for %s dated %s' %(user_name, f_name, order_date)
    total_quantity = 0
    total_amount = 0
    for po in po_data:
        data += '\nD.NO: %s, Qty: %s' % (po[1], po[3])
        total_quantity += int(po[3])
        total_amount += int(po[5])
    data += '\nTotal Qty: %s, Total Amount: %s\nPlease check WhatsApp for Images' % (total_quantity,total_amount)
    send_sms(phone_no, data)

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

def errorpage(request):
    return render(request,'templates/errorpage.html')

def get_permission(user, codename):
    in_group = False
    groups = user.groups.all()
    for grp in groups:
        in_group = codename in grp.permissions.values_list('codename', flat=True)
        if in_group:
            break
    return codename in user.user_permissions.values_list('codename', flat=True) or in_group

def permissionpage(request,cond=''):
    if cond:
        return ((request.user.is_staff or request.user.is_superuser) or get_permission(request.user, cond))
    else:
        return (request.user.is_staff or request.user.is_superuser)


@csrf_exempt
def login(request):
    http_host = request.META['HTTP_HOST']
    if not http_host.startswith('wms-dev'):
        return HttpResponseRedirect('/wms_login')
    return HttpResponseRedirect(AUTHORIZE_URL % (URL, CLIENT_ID, REDIRECT))


@csrf_exempt
def wms_login(request):
    username = request.POST.get('login_id', '')
    password = request.POST.get('password', '')
    full_name = request.POST.get('user_name', '')
    token = request.POST.get('token', '')
    token = 'grtrhhethgrrgr'
    if username and token and full_name:
        user = User.objects.filter(username=username)
        if not user:
            user = User.objects.create_user(username, '', 'Miebach$1#JUN11@2015')
            user.username = full_name
            user.save()
            user = User.objects.filter(username=username)
        if user:
            user = user[0]
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            auth.login(request, user)
            return HttpResponseRedirect('/home/')
    elif username and password:
        user = authenticate(username=username, password=password)
        if user and user.is_active:
            auth.login(request, user)
            user_profile = UserProfile.objects.filter(user_id=user.id)
            if not user_profile:
                prefix = re.sub('[^A-Za-z0-9]+', '', user.username)[:3].upper()
                user_profile = UserProfile(user=user, phone_number='',
                                           is_active=1, prefix=prefix)
                user_profile.save()

            request.session['token'] = token
            return HttpResponseRedirect('/home/')
    return render(request, 'templates/login.html')


def logout(request):
    auth.logout(request)
    return render(request,'templates/logout.html')

def check_location(location, user, quantity=0):
    loc_existance = LocationMaster.objects.get(location=location, zone__user=user)
    if loc_existance:
        return int(loc_existance.id)
    else:
        return

def get_or_none(model_obj, search_params):
    try:
        data = model_obj.objects.get(**search_params)
    except:
        data = ''
    return data

def filter_or_none(model_obj, search_params):
    data = model_obj.objects.filter(**search_params)
    return data

def filter_by_values(model_obj, search_params, filter_values):
    data = filter_or_none(model_obj, search_params)
    data = data.values(*filter_values)
    return data

@csrf_exempt
@login_required
def update_issues(request):

    resolved_headers = OrderedDict( ( ('ID',  'id'),
                                      ('Issue Title', 'issue_title'),
                                      ('Issue Description', 'issue_description'),
                                      ('Status', 'status'),
                                      ('Priority', 'priority'),
                                      ('Resolved Descrption', 'resolved_description') ) )

    data_id = request.GET['data-id']
    filter_params = {'id': data_id}
    data = get_or_none(Issues, filter_params)
    report_data = []
    for key, value in request.GET.iteritems():
        setattr(data, key, value)
    data.save()

    for key, value in resolved_headers.iteritems():
        report_data.append((key, getattr(data, value)))

    headers = ('Name', 'Value')
    html_data = create_mail_table(headers, report_data)
    send_mail([request.user.email], 'Resolved Report: WMS Issue', html_data)

    return HttpResponse('Updated Successfully')

def get_quantity(data_dict, key_pair, no_date=False):
    for key, value in key_pair.iteritems():
        if no_date and not key == 'executed':
            date_str = [k for (k, v) in value[1].iteritems() if 'date' in k]
            if date_str:
                del value[1][date_str[0]]
        if value[0] == OrderDetail:
            results = value[0].objects.filter(**value[1]).values('order_id', 'sku_id').distinct()
        elif value[0] == PurchaseOrder:
            results = value[0].objects.filter(**value[1]).values('order_id').distinct()
        else:
            results = value[0].objects.filter(**value[1]).values('order__order_id', 'order__sku_id').distinct()
        for result in results:
            data_dict[key] += 1

def get_daily_transactions(data_dict, key_pair, table, user):
    for key, value in key_pair.iteritems():
        results = table.objects.filter(order__user=user,**value[0])
        for result in results:
            data_dict[key] += 1

@csrf_exempt
@login_required
@get_admin_user
def get_orders_count(request, user=''):
    filter_params = {'user': user.id, 'quantity__gt': 0}
    orders = filter_or_none(OrderDetail, filter_params)
    orders_count = orders.count()
    
    return HttpResponse(json.dumps({'orders': orders_count}))
    

@csrf_exempt
@login_required
@get_admin_user
def home(request, user=''):
    user_id = user.id
    orders_list = []
    aging_count = [0, 0, 0]
    aging_classes = ( (NOW, NOW - relativedelta(months=3)),
                      (NOW - relativedelta(months=3), NOW - relativedelta(months=6)),
                      (NOW - relativedelta(months=6), 0) )
    for index, aging in enumerate(aging_classes):
        if aging[1] == 0:
            filter_params = {'receipt_date__lt': str(aging[0]).split('.')[0], 'quantity__gt': 0,'sku__user': user_id}
            data = StockDetail.objects.filter(**filter_params).aggregate(Sum('quantity'))['quantity__sum']
        else:
            filter_params = {'receipt_date__lt': str(aging[0]).split('.')[0],
                    'receipt_date__gt': str(aging[1]).split('.')[0], 'quantity__gt': 0, 'sku__user': user_id}
            data = StockDetail.objects.filter(**filter_params).aggregate(Sum('quantity'))['quantity__sum']
        if data:
            aging_count[index] = data

    filter_params = {'user': user_id, 'quantity__gt': 0}
    orders = filter_or_none(OrderDetail, filter_params)
    orders_count = orders.count()
    pending_orders = orders.filter(status=1).count()

    filter_params = {'user': user_id}
    locations_count = {}
    zone_list = ZoneMaster.objects.exclude(zone__in=['TEMP_ZONE', 'DEFAULT', 'DAMAGED_ZONE']).filter(**filter_params)
    for zones in zone_list:
        total_stock = 0
        max_capacity = 0
        stock_data = StockDetail.objects.filter(location__zone__zone=zones.zone,
                     location__zone__user=user_id).aggregate(Sum('quantity'))
        if not None in stock_data.values():
            total_stock = int(stock_data['quantity__sum'])
        locations = LocationMaster.objects.filter(zone__user=user_id,zone__zone=zones.zone).aggregate(Sum('max_capacity'))
        if not None in locations.values():
            max_capacity = int(locations['max_capacity__sum'])
        locations_count[zones.zone] = [total_stock,max_capacity - total_stock]

    filter_params = {'zone_id': None, 'user': user_id}
    wms_count = filter_or_none(SKUMaster, filter_params).count()
    dates = [];
    for i in range(7):
        dates.append(NOW- datetime.timedelta(days = i))
    weekly =[]


    for d in dates:
        daily = {"orders":0,"picked":0,"dispatched":0}
        results_dict = {'orders': ({'order__creation_date__startswith': d.date()},'reserved_quantity','picked_quantity'),'picked': ({'updation_date__startswith': d.date(),'status__icontains':'picked'}, 'picked_quantity'), 'dispatched': ( {'updation_date__startswith': d.date(),'status__icontains': 'picked'}, 'picked_quantity')}
        get_daily_transactions(daily, results_dict, Picklist,user_id)

        daily["Day"] = str(d.date())
        weekly.append(daily)
        day_order = orders.filter(user=user_id, quantity__gt=0, creation_date__startswith= d.date()).extra(select={'date':'DATE(creation_date)','count':'COUNT(id)'}).values('count').order_by('date')[0]['count']
        orders_list.append(int(day_order))
    purchase_count = PurchaseOrder.objects.filter(open_po__sku__user=user.id, open_po__order_quantity__gt=0).values_list('order_id', flat=True).distinct().count()

    picking = {'executed':0, 'inprogress':0, 'pending':0}
    pie_picking = {'executed':0, 'inprogress':0, 'pending':0}
    results_dict = {'pending': (OrderDetail, {'user': user_id, 'status': 1, 'creation_date__startswith': NOW.date() }),
                    'inprogress': (Picklist, {'status__contains': 'open', 'order__user': user_id, 'creation_date__startswith': NOW.date()}),
                    'executed': (Picklist, {'status__icontains': 'picked', 'order__user': user_id, 'updation_date__startswith': NOW.date()})}
    get_quantity(picking, results_dict)
    get_quantity(pie_picking, results_dict, True)

    putaway  = {'executed':0, 'inprogress':0, 'pending':0}
    pie_putaway = {'executed':0, 'inprogress':0, 'pending':0}
    results_dict = {'executed': (PurchaseOrder, {'status': 'confirmed-putaway', 'open_po__sku__user': user_id,
                                'updation_date__startswith': NOW.date()}),
                    'inprogress': (PurchaseOrder, {'status__in': ['grn-generated', 'location-assigned'], 'open_po__sku__user': user_id,
                                 'updation_date__startswith': NOW.date()}),
                    'pending': (PurchaseOrder, {'status': '', 'open_po__sku__user': user_id, 'updation_date__startswith': NOW.date()})}
    get_quantity(putaway, results_dict)
    get_quantity(pie_putaway, results_dict, True)
    max_order = sum(orders_list) + orders_count
    max_purchase = purchase_count + (purchase_count * 2)
    top_skus = orders.filter(user=user.id).values('sku__sku_code').annotate(Count('sku_id')).order_by('-sku_id__count')[:5]
    top_selling = orders.filter(user=user.id).values('sku__sku_code').annotate(Sum('invoice_amount')).\
                                      order_by('-invoice_amount__sum')[:5]
    suppliers = SupplierMaster.objects.filter(user=user.id).values_list('name', flat=True)

    return render(request,'templates/home.html',{'orders_count': orders_count,'locations_count': locations_count, 'aging_count': aging_count,
                                                 'wms_count': wms_count, 'weekly_tr': weekly, 'picking': picking, 'putaway': putaway,
                                                 'pie_putaway': pie_putaway, 'pie_picking': pie_picking, 'max_order': max_order,
                                                 'top_skus': top_skus, 'top_selling': top_selling, 'pending_orders': pending_orders,
                                                 'purchase_count': purchase_count, 'max_purchase': max_purchase, 'suppliers': suppliers,
                                                 'marketplaces': MARKETPLACE_LIST })

@csrf_exempt
@login_required
@get_admin_user
def raise_po(request, user=''):
    is_display = ''
    if not permissionpage(request,'add_openpo'):
        return render(request, 'templates/permission_denied.html')
    filter_params = {'user': user.id}
    warehouses = UserGroups.objects.filter(Q(user__username=user.username) | Q(admin_user__username=user.username))
    if not warehouses:
        is_display = 'display-none'
    suppliers = filter_by_values(SupplierMaster, filter_params, ['id', 'name'])
    return render(request, 'templates/raise_po.html', {'po_fields': RAISE_PO_FIELDS, 'suppliers': suppliers,
                                                       'po_fields1': RAISE_PO_FIELDS1, 'headers': OPEN_STOCK_HEADERS,
                                                       'is_display': is_display})
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
    return render(request, 'templates/toggle/toggle_po.html', {'send_message': send_message, 'po_fields': RAISE_PO_FIELDS,
                                                               'suppliers': suppliers, 'po_fields1': RAISE_PO_FIELDS1})

def update_skus(skus, user=''):
    if isinstance(skus, dict):
        skus = skus['items']

    for sku in skus:
        filter_params = {'sku_code': sku['sku'], 'user':  user.id}
        data = filter_or_none(SKUMaster, filter_params)

        if not data:
            filter_params = {'wms_code': sku['sku'], 'user':  user.id}
            data = filter_or_none(SKUMaster, filter_params)
            if data and not data[0].sku_code:
                data = data[0]
                data.sku_code = sku['sku']
                image = sku.get('image', '')
                if image:
                    data.image_url = sku.get('image', '')
                if not data.sku_desc:
                    data.sku_desc = sku.get('title', '')
                data.save()
                continue
        if data:
            swx_mapping = SWXMapping.objects.filter(local_id = data[0].id, swx_type='sku')
            if swx_mapping:
                for mapping in swx_mapping:
                    mapping.swx_id = sku['id']
                    mapping.updation_date = NOW
                    mapping.save()
            else:
                mapping = SWXMapping(swx_id = sku['id'], local_id = data[0].id, swx_type = 'sku', creation_date = NOW, updation_date = NOW)
                mapping.save()

        if data:
            sku_image = sku.get('image')
            if sku_image:
                sku_image = sku_image.replace('100x100', '1024x800')
            if sku_image and data[0].image_url != sku_image:
                data[0].image_url = sku_image
                data[0].status = sku.get('active')
                data[0].save()
            continue

        data_dict = copy.deepcopy(SKU_DATA)
        data_dict['user'] = user.id
        needed_data = {'sku_code': 'sku',
        'sku_desc': 'title',
        'image_url': 'image',
        'status': 'active'}
        for data in needed_data:
            if sku[needed_data[data]]:
                data_dict[data] = sku[needed_data[data]]
                continue
            data_dict[data] = ''

        data_dict['user'] = user.id
        sku_master = SKUMaster(**data_dict)
        sku_master.save()

@csrf_exempt
@login_required
@fn_timer
@get_admin_user
def sku_master(request,user=''):
    FIELDS = ''
    filter_params = {'user': user.id}
    zones = filter_by_values(ZoneMaster, filter_params, ['zone'])
    logger.info('In SKU Master')
    data = filter_by_values(SKUMaster, filter_params, ['sku_code'])
    categories = SKUMaster.objects.exclude(sku_category='').filter(user=user.id).values_list('sku_category', flat=True).distinct()
    FIELDS = ADD_SKU_FIELDS
    if get_permission(request.user,'add_qualitycheck'):
        FIELDS = SKU_FIELDS[:4] + (SKU_FIELDS[4] + (('Quality Check', 'qc_check'),),)
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    market_places = Marketplaces.objects.filter(user=user.id).values_list('name', flat=True)
    return render(request, 'templates/sku_master.html', {'add_sku': FIELDS, 'locations': zones, 'headers': SKU_MASTER_HEADERS,
                                                         'market_list': MARKET_LIST_HEADERS,
                                                         'data': data[:5], 'marketplace_list': market_places, 'categories': categories,
                                                         'all_groups': all_groups})


@csrf_exempt
@login_required
@get_admin_user
def receive_po(request, user=''):
    if not permissionpage(request,'add_purchaseorder'):
        return render(request, 'templates/permission_denied.html')
    return render(request, 'templates/receive_po.html')

@csrf_exempt
@login_required
@get_admin_user
def quality_check(request, user=''):
    if not get_permission(request.user,'add_qualitycheck'):
        return render(request, 'templates/permission_denied.html')
    return render(request, 'templates/quality_check.html')


@csrf_exempt
@get_admin_user
def get_customer_data(request, user=''):
    data_id = request.GET['id']
    cust_details = CustomerMaster.objects.filter(id=data_id, user=user.id)
    if cust_details:
        data = cust_details[0]
        return HttpResponse(data.name + '<br>' + data.phone_number + '<br>' + data.email_id + '<br>' + data.address)
    else:
        return HttpResponse('')


@csrf_exempt
@get_admin_user
def get_customer_sku(request, user=''):
    temp1 = []
    order_shipments = []
    search_params = {'user': user.id}
    headers = ('', 'SKU Code', 'Order Quantity', 'Shipping Quantity', 'Pack Reference', '')
    c_id = request.GET['customer_id']
    marketplace = request.GET['marketplace']
    if c_id:
        search_params['customer_id'] = c_id
    if marketplace:
        search_params['marketplace'] = marketplace.replace('Default','')
    ship_no = request.GET['shipment_number']
    data_dict = copy.deepcopy(ORDER_SHIPMENT_DATA)
    order_shipment = OrderShipment.objects.filter(shipment_number = ship_no)
    customer_dict = OrderDetail.objects.filter(**search_params).values('customer_id', 'customer_name').distinct()
    for customer in customer_dict:
        all_data = Picklist.objects.filter(order__customer_id=customer['customer_id'], status__icontains='picked', order__user=user.id).\
                                         values('order__sku__sku_code', 'order_id').distinct().annotate(picked=Sum('picked_quantity'))

        for ind,dat in enumerate(all_data):
            shipped = ShipmentInfo.objects.filter(order_id=dat['order_id']).aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
            if shipped:
                all_data[ind]['picked'] = int(dat['picked']) - shipped

        if not order_shipment and all_data:
            for key, value in request.GET.iteritems():
                if key in ('customer_id', 'marketplace'):
                    continue
                elif key == 'shipment_date':
                    ship_date = value.split('/')
                    data_dict[key] = datetime.date(int(ship_date[2]), int(ship_date[0]), int(ship_date[1]))
                else:
                    data_dict[key] = value

            data_dict['user'] = user.id
            data = OrderShipment(**data_dict)
            data.save()
            order_shipment = [data]
            order_shipments.append(data)
    if all_data:
        display_fields = ['Customer ID', 'Customer Name']
        if len(customer_dict) > 1:
            display_fields = ['Market Place']
            customer_dict = {'marketplace': marketplace}
        return render(request, 'templates/toggle/add_customer.html', {'customer_details': customer_dict, 'data': all_data,
                                                                      'headers': headers, 'shipment_id': order_shipment[0].id,
                                                                      'display_fields': display_fields,
                                                                      'marketplace': marketplace})
    else:
        return HttpResponse('No orders Found')


@csrf_exempt
@get_admin_user
def shipment_info(request, user=''):
    if not get_permission(request.user, 'add_shipmentinfo'):
        return render(request, 'templates/permission_denied.html')
    customer_ids = OrderDetail.objects.filter(user = user.id).values('customer_id', 'customer_name').distinct()
    order_shipment = OrderShipment.objects.filter(user = user.id).order_by('-shipment_number')
    marketplaces = list(OrderDetail.objects.filter(user = user.id).values_list('marketplace', flat=True).distinct())
    if marketplaces and '' in marketplaces:
        marketplaces[marketplaces.index('')] = 'Default'
    if order_shipment:
        shipment_number = int(order_shipment[0].shipment_number) + 1
    else:
        shipment_number = 1
    return render(request, 'templates/shipment_info.html', {'customer_ids': customer_ids, 'shipment_fields': SHIPMENT_FIELDS,
                                                            'shipment_number': shipment_number, 'marketplaces': marketplaces})


@csrf_exempt
@get_admin_user
def insert_shipment_info(request, user=''):
    myDict = dict(request.GET.iterlists())
    for i in range(0, len(myDict['order_shipment_id'])):
        if not myDict['package_reference'][i] or not myDict['shipping_quantity'][i]:
            continue
        order_id = myDict['order_id'][i]
        data_dict = copy.deepcopy(ORDER_PACKAGING_FIELDS)
        shipment_data = copy.deepcopy(SHIPMENT_INFO_FIELDS)
        for key, value in myDict.iteritems():
            if key in data_dict:
                data_dict[key] = value[i]
            if key in shipment_data:
                shipment_data[key] = value[i]

        data = OrderPackaging(**data_dict)
        data.save()
        shipment_data['order_packaging_id'] = data.id
        order_detail = OrderDetail.objects.filter(user = user.id, id=order_id)
        shipment_data['order'] = order_detail[0]
        ship_data = ShipmentInfo(**shipment_data)
        ship_data.save()
        received_quantity = int(myDict['shipping_quantity'][i])
        picked_orders = Picklist.objects.filter(order_id=myDict['order_id'][i], status__icontains='picked', order__user=user.id)
        for orders in picked_orders:
            remaining_capacity = int(orders.picked_quantity)
            if remaining_capacity == 0:
                continue
            elif remaining_capacity < received_quantity:
                location_quantity = remaining_capacity
                received_quantity -= remaining_capacity
            elif remaining_capacity >= received_quantity:
                location_quantity = received_quantity
                received_quantity = 0
            ship_quantity = ShipmentInfo.objects.filter(order_id=orders.order_id).aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
            if ship_quantity >= int(orders.picked_quantity):
                setattr(orders, 'status', 'dispatched')
                orders.save()

    return HttpResponse('Inserted Successfully')


@csrf_exempt
@login_required
@get_admin_user
def online_percentage(request, user=''):
    if not get_permission(request.user, 'add_skustock'):
        return render(request, 'templates/permission_denied.html')
    sku_stock = SKUStock.objects.filter(sku__user = user.id, status=0)
    for data in sku_stock:
        setattr(data, 'status', 1)
        data.save()

    return render(request, 'templates/online_percentage.html')

@get_admin_user
def get_sku_data(request, user=''):
    market_data = []
    combo_data = []
    data_id = request.GET['data_id']

    filter_params = {'id': data_id, 'user': user.id}
    data = get_or_none(SKUMaster, filter_params)

    filter_params = {'user': user.id}
    zones = filter_by_values(ZoneMaster, filter_params, ['zone'])

    zone_name = ''
    if data.zone_id:
        zone_name = data.zone.zone
    FIELDS = SKU_FIELDS
    if get_permission(request.user,'add_qualitycheck'):
        FIELDS = SKU_FIELDS[:4] + (SKU_FIELDS[4] + (('Quality Check', 'qc_check'),),)
    market_map = MarketplaceMapping.objects.filter(sku_id=data.id)
    for market in market_map:
        market_data.append(OrderedDict( (('market_sku_type', market.sku_type), ('marketplace_code', market.marketplace_code),
                                         ('description', market.description), ('market_id', market.id) )) )
    combo_skus = SKURelation.objects.filter(relation_type='combo', parent_sku_id=data_id)
    for combo in combo_skus:
        combo_data.append(OrderedDict( (('combo_sku', combo.member_sku.wms_code), ('combo_desc', combo.member_sku.sku_desc) )) )
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    market_places = Marketplaces.objects.filter(user=user.id).values_list('name', flat=True)
    return render(request, 'templates/toggle/update_sku.html', {'data': data, 'update_sku': FIELDS, 'zones': zones,
                                                                'zone_name': zone_name, 'image': data.image_url,
                                                                'market_list': MARKET_LIST_HEADERS, 'market_data': market_data,
                                                                'marketplace_list': market_places, 'combo_data': combo_data,
                                                                'combo_sku_headers': COMBO_SKU_HEADERS, 'all_groups': all_groups})

@csrf_exempt
@login_required
@get_admin_user
def get_user_data(request, user=''):
    for key,value in request.GET.iteritems():
        group_names = []
        exclude_list = ['Pull to locate', 'Admin', 'WMS']
        exclude_group = AdminGroups.objects.filter(user_id = user.id)
        if exclude_group:
            exclude_list.append(exclude_group[0].group.name)
        cur_user = User.objects.get(id=value)
        groups = user.groups.filter().exclude(name__in = exclude_list)
        user_groups = cur_user.groups.filter()
        if user_groups:
            for i in user_groups:
                group_names.append(i.name)
    return render(request, 'templates/toggle/update_user.html', {'data': cur_user, 'update_user': USER_FIELDS, 'groups': groups,
                  'user_groups': group_names, 'data_id': cur_user.id })

@csrf_exempt
@login_required
@get_admin_user
def get_supplier_update(request, user=''):
    data_id = request.GET['data_id']
    filter_params = {'id': data_id, 'user': user.id}
    data = get_or_none(SupplierMaster, filter_params)
    return render(request, 'templates/toggle/update_supplier.html', {'data': data, 'update_supplier': SUPPLIER_FIELDS})

@csrf_exempt
@login_required
@get_admin_user
def get_customer_sku_data(request, user=''):
   data_id = request.GET['data_id']
   data = get_or_none(CustomerSKU, {'id': data_id})
   return render(request, 'templates/toggle/update_customer_sku.html', {'data': data, 'id': data_id ,'update_customer': SKU_CUSTOMER_FIELDS})

@csrf_exempt
@login_required
@get_admin_user
def search_customer_sku_mapping(request, user=''):
   data_id = request.GET['search_data']
   data = CustomerMaster.objects.filter(Q(id__icontains = data_id) | Q(name__icontains = data_id), user=user.id)
   search_data = []
   if data:
       for record in data:
           search_data.append(str(record.id)+" : "+str(record.name))
       return HttpResponse(json.dumps(search_data))
   return HttpResponse(json.dumps(search_data))

@csrf_exempt
@login_required
@get_admin_user
def get_location_data(request,user=''):
    FIELDS = ''
    location_group = []
    loc_id = request.GET['location_id']
    filter_params = {'location': loc_id, 'zone__user': user.id}
    data = get_or_none(LocationMaster, filter_params)
    FIELDS = LOCATION_FIELDS
    pallet_switch = get_misc_value('pallet_switch', user.id)
    if pallet_switch == "true":
        FIELDS = FIELDS + ((('Pallet Capacity', 'pallet_capacity'),),)
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    location_group = LocationGroups.objects.filter(location__zone__user=user.id, location_id=data.id).values_list('group', flat=True)
    return render(request, 'templates/toggle/update_location.html', {'data': data, 'update_location': FIELDS, 'lock_fields': LOCK_FIELDS,
                                                                     'all_groups': all_groups, 'location_group': location_group})


@csrf_exempt
@login_required
@get_admin_user
def add_location_data(request,user=''):

    FIELDS = ''
    filter_params = {'user': user.id}
    zones = filter_by_values(ZoneMaster, filter_params, ['zone'])
    add_zone = ((('Zone ID *', 'zone_id'),),)
    FIELDS = LOCATION_FIELDS
    pallet_switch = get_misc_value('pallet_switch', user.id)
    if pallet_switch == "true":
        FIELDS = FIELDS[:3] + ((('Pallet Capacity', 'pallet_capacity'),),)
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    return render(request, 'templates/toggle/add_location.html', {'loctype': zones, 'add_location': FIELDS, 'add_zone': add_zone,
                                                                  'lock_fields': LOCK_FIELDS, 'loc_groups': all_groups})

@csrf_exempt
@login_required
def add_user_data(request):
    return render(request, 'templates/toggle/add_user.html', {'add_user_fields': ADD_USER_FIELDS})

@csrf_exempt
@login_required
@get_admin_user
def add_group_data(request, user=''):
    permissions = user.user_permissions.all()
    perms_list = []
    ignore_list = ['session', 'webhookdata', 'swxmapping', 'userprofile', 'useraccesstokens', 'contenttype', 'user',
                   'permission','group','logentry']
    for permission in permissions:
        temp = permission.codename.split('_')[-1]
        if not temp in perms_list and not temp in ignore_list:
            perms_list.append(temp)
    return render(request, 'templates/toggle/add_group.html', {'add_group_fields': ADD_GROUP_FIELDS, 'perms_list': perms_list})


@csrf_exempt
@login_required
@get_admin_user
def location_master(request,user=''):
    filter_params = {'user': user.id}
    distinct_loctype = filter_by_values(ZoneMaster, filter_params, ['zone'])
    new_loc = []
    for loc_type in distinct_loctype:
        filter_params = {'zone__zone': loc_type['zone'], 'zone__user': user.id}
        loc = filter_by_values(LocationMaster, filter_params, ['location', 'max_capacity', 'fill_sequence', 'pick_sequence', 'status'])
        new_loc.append(loc)

    add_zone = ((('Zone ID', 'zone'),),)
    modified_zone = zip(distinct_loctype, new_loc)
    return render(request, 'templates/location_master.html', {'loctype': distinct_loctype, 'loc_ids': modified_zone, 'add_location': LOCATION_FIELDS, 'add_zone': add_zone})


def update_marketplace_mapping(user, data_dict={}, data=''):
    if 'market_sku_type' not in data_dict.keys():
        return

    for i in range(len(data_dict['market_sku_type'])):
        if (data_dict['market_sku_type'][i] and data_dict['marketplace_code'][i]):
            market_mapping = MarketplaceMapping.objects.filter(sku_type=data_dict['market_sku_type'][i], description=data_dict['description'][i], marketplace_code=data_dict['marketplace_code'][i], sku_id=data.id,sku__user=user.id)
            if market_mapping:
                continue

            mapping_data = {'sku_id': data.id, 'sku_type': data_dict['market_sku_type'][i],
                    'marketplace_code': data_dict['marketplace_code'][i], 'description': data_dict['description'][i],
                    'creation_date': NOW}
            map_data = MarketplaceMapping(**mapping_data)
            map_data.save()

@csrf_exempt
@login_required
@get_admin_user
def insert_sku(request,user=''):
    wms = request.POST['wms_code']
    description = request.POST['sku_desc']
    zone = request.POST['zone_id']
    if not wms or not description or not zone:
        return HttpResponse('Missing Required Fields')
    filter_params = {'zone': zone, 'user': user.id}
    zone_master = filter_or_none(ZoneMaster, filter_params)
    if not zone_master:
        return HttpResponse('Invalid Zone, Please enter valid Zone')
    filter_params = {'wms_code': wms, 'user': user.id}
    data = filter_or_none(SKUMaster, filter_params)
    status_msg = 'SKU exists'

    if not data:
        data_dict = copy.deepcopy(SKU_DATA)
        data_dict['user'] = user.id
        for key, value in request.POST.iteritems():
            if key in data_dict.keys():
                if key == 'zone_id':
                    value = get_or_none(ZoneMaster, {'zone': value, 'user': user.id})
                    value = value.id
                elif key == 'status':
                    if value == 'Active':
                        value = 1
                    else:
                        value = 0
                elif key == 'qc_check':
                    if value == 'Enable':
                        value = 1
                    else:
                        value = 0
                if value == '':
                    continue
                data_dict[key] = value

        data_dict['sku_code'] = data_dict['wms_code']
        sku_master = SKUMaster(**data_dict)
        sku_master.save()
        image_file = request.FILES.get('files-0','')
        if image_file:
            save_image_file(image_file, sku_master, user)
        status_msg = 'New WMS Code Added'

        update_marketplace_mapping(user, data_dict=dict(request.POST.iterlists()), data=sku_master)


    return HttpResponse(status_msg)

@csrf_exempt
@login_required
def insert_issue(request):

    issue_pairs = {}
    report_data = []
    for data in RAISE_ISSUE_FIELDS:
        issue_pairs[data[1]] = data[0]

    status_msg = 'Issue already added'
    title = request.GET['issue_title']
    if not title:
        return HttpResponse('Missing Required Fields')
    data_dict = copy.deepcopy(ISSUE_DATA)
    for key, value in request.GET.iteritems():
        data_dict[key] = value
        report_data.append((issue_pairs[key], value))

    data_dict['user'] = request.user

    issue = Issues(**data_dict)
    issue.save()

    report_data.insert(0, ('ID', issue.id))
    headers = ('Name', 'Value')
    html_data = create_mail_table(headers, report_data)
    try:
        send_mail([ request.user.email ], 'Report: WMS Issue', html_data)
    except:
        pass

    status_msg = 'New Issue Added Successfully'

    return HttpResponse(status_msg)

@csrf_exempt
@login_required
@get_admin_user
def insert_supplier(request, user=''):
    supplier_id = request.GET['id']
    if not supplier_id:
        return HttpResponse('Missing Required Fields')
    data = filter_or_none(SupplierMaster, {'id': supplier_id})
    status_msg = 'Supplier Exists'
    sku_status = 0
    rep_email = filter_or_none(SupplierMaster, {'email_id': request.GET['email_id'], 'user': user.id})
    rep_phone = filter_or_none(SupplierMaster, {'phone_number': request.GET['phone_number'], 'user': user.id})
    if rep_email:
        return HttpResponse('Email already exists')
    if rep_phone:
        return HttpResponse('Phone Number already exists')

    if not data:
        data_dict = copy.deepcopy(SUPPLIER_DATA)
        for key, value in request.GET.iteritems():
            if key == 'status':
                if value == 'Active':
                    value = 1
                else:
                    value = 0
            if value == '':
                continue
            data_dict[key] = value

        data_dict['user'] = user.id
        supplier_master = SupplierMaster(**data_dict)
        supplier_master.save()
        status_msg = 'New Supplier Added'

    return HttpResponse(status_msg)

def save_image_file(image_file, data, user, extra_image=''):
    extension = image_file.name.split('.')[-1]
    path = 'static/images/'
    folder = str(user.id)
    image_name = str(data.wms_code)
    if extra_image:
        image_name = image_file.name.strip('.' + image_file.name.split('.')[-1])
    if not os.path.exists(path + folder):
        os.makedirs(path + folder)
    full_filename = os.path.join(path, folder, str(image_name) + '.' +str(extension))
    fout = open(full_filename, 'wb+')
    file_content = ContentFile( image_file.read() )

    try:
        # Iterate through the chunks.
        for chunk in file_content.chunks():
            fout.write(chunk)
        fout.close()
        image_url = '/' + path + folder + '/' + str(image_name) + '.' +str(extension)
        if not extra_image:
            data.image_url = image_url
            data.save()
            return
        sku_image = SKUImages.objects.filter(sku_id=data.id, image_url=image_url)
        if not sku_image:
            SKUImages.objects.create(sku_id=data.id, image_url=image_url, creation_date=NOW)
            
    except:
        print 'not saved'

@csrf_exempt
@login_required
@get_admin_user
def update_sku(request,user=''):
    wms = request.POST['wms_code']
    description = request.POST['sku_desc']
    zone = request.POST['zone_id']
    if not wms or not description or not zone:
        return HttpResponse('Missing Required Fields')
    data = get_or_none(SKUMaster, {'wms_code': wms, 'user': user.id})
    image_file = request.FILES.get('files-0','')
    if image_file:
        save_image_file(image_file, data, user)
    for key, value in request.POST.iteritems():

        if key == 'status':
            if value == 'Active':
                value = 1
            else:
                value = 0
        elif key == 'qc_check':
            if value == 'Enable':
                value = 1
            else:
                value = 0
        elif key == 'threshold_quantity':
            if not value:
                value = 0
        elif key == 'zone_id' and value:
            zone = get_or_none(ZoneMaster, {'zone': value, 'user': request.user.id})
            value = zone.id
        setattr(data, key, value)

    data.save()

    update_marketplace_mapping(user, data_dict=dict(request.POST.iterlists()), data=data)

    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def update_supplier_values(request,user=''):
    data_id = request.GET['id']
    data = get_or_none(SupplierMaster, {'id': data_id, 'user': user.id})
    for key, value in request.GET.iteritems():
        if key == 'status':
            if value == 'Active':
                value = 1
            else:
                value = 0
        setattr(data, key, value)

    data.save()
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def update_sku_supplier_values(request, user=''):
    data_id = request.GET['data-id']
    data = get_or_none(SKUSupplier, {'id': data_id, 'sku__user': user.id})
    for key, value in request.GET.iteritems():
        if key in ('moq', 'price'):
            if not value:
                value = 0
        setattr(data, key, value)
    data.save()
    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def insert_mapping(request,user=''):
    data_dict = copy.deepcopy(SUPPLIER_SKU_DATA)
    integer_data = ('preference', 'moq')
    for key, value in request.GET.iteritems():

        if key == 'wms_id':
            sku_id = SKUMaster.objects.filter(wms_code=value.upper(), user=user.id)
            if not sku_id:
                return HttpResponse('Wrong WMS Code')
            key = 'sku'
            value = sku_id[0]

        elif key == 'supplier_id':
            supplier = SupplierMaster.objects.get(id=value, user=user.id)
            value = supplier.id

        elif key == 'price' and not value:
            value = 0

        elif key in integer_data:
            if not value.isdigit():
                return HttpResponse('Plese enter Integer values for Priority and MOQ')

        if key == 'preference':
            preference = value

        if value != '':
            data_dict[key] = value

    data = SKUSupplier.objects.filter(supplier_id=supplier, sku_id=sku_id[0].id, sku__user=user.id)
    if data:
        return HttpResponse('Duplicate Entry')
    preference_data = SKUSupplier.objects.filter(sku_id=sku_id[0].id, sku__user=user.id).order_by('-preference')
    min_preference = 0
    if preference_data:
        min_preference = int(preference_data[0].preference)
    if int(preference) <= min_preference:
        return HttpResponse('Duplicate Priority, Next incremantal value is %s' % str(min_preference + 1))

    sku_supplier = SKUSupplier(**data_dict)
    sku_supplier.save()
    return HttpResponse('Added Successfully')

def save_location_group(data_id, value, user):
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    for sku_group in all_groups:
        loc_map = LocationGroups.objects.filter(location__zone__user=user.id, location_id=data_id, group=sku_group)
        if sku_group in value:
            if not loc_map:
                map_dict = copy.deepcopy(LOCATION_GROUP_FIELDS)
                map_dict['group'] = sku_group
                map_dict['location_id'] = data_id
                new_map = LocationGroups(**map_dict)
                new_map.save()
        elif loc_map:
            loc_map.delete()


@csrf_exempt
@login_required
@get_admin_user
def update_location(request, user=''):
    loc_id = request.GET['location']
    data = LocationMaster.objects.get(location=loc_id, zone__user = user.id)
    for key, value in request.GET.iteritems():
        if key in ('max_capacity', 'pick_sequence', 'fill_sequence', 'pallet_capacity'):
            if not value:
                value = 0
        elif key == 'location_group':
            value = value.split(',')
            save_location_group(data.id, value, user)
            continue

        elif key == 'status':
            if value == 'Active':
                value = 1
            else:
                value = 0
        elif key == 'zone_id':
            continue
        setattr(data, key, value)
    data.save()
    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def add_location(request,user=''):
    loc_id = request.GET['location']
    data = LocationMaster.objects.filter(location=loc_id, zone__user=user.id)
    if not data and loc_id:
        location_dict = copy.deepcopy(LOC_DATA)

        for key, value in request.GET.iteritems():
            if key == 'status':
                value = 0
                if value == 'Active':
                    value = 1
            elif key == 'zone_id':
                value = ZoneMaster.objects.get(zone=value, user=user.id).id
            elif key == 'location_group':
                continue
            if not value:
                continue
            location_dict[key] = value

        loc_master = LocationMaster(**location_dict)
        loc_master.save()
        loc_group =  request.GET.get('location_group', '')
        if loc_group:
            loc_group = loc_group.split(',')
            save_location_group(loc_master.id, loc_group, user)
        status = 'Added Successfully'
    else:
        status = 'Entry Exists in DB'

    if not loc_id:
        status = 'Missing required parameters'
    return HttpResponse(status)

@csrf_exempt
@login_required
@get_admin_user
def add_zone(request, user=''):
    zone = request.GET['zone']
    data = LocationMaster.objects.filter(zone__zone=zone, zone__user=user.id)
    if not zone:
        status = 'Please enter ZONE value'
    elif not data:
        location_dict = copy.deepcopy(ZONE_DATA)
        location_dict['user'] = user.id
        for key, value in request.GET.iteritems():
            location_dict[key] = value
        loc_master = ZoneMaster(**location_dict)
        loc_master.save()
        status = 'Added Successfully'
    else:
        status = 'Entry Exists in DB'
    return HttpResponse(status)


@csrf_exempt
@login_required
@get_admin_user
def create_orders(request, user=''):
    if not permissionpage(request):
        return render(request, 'templates/permission_denied.html')
    user_list = []
    admin_user = UserGroups.objects.filter(Q(admin_user__username__iexact=user.username) | Q(user__username__iexact=user.username)).\
                 values_list('admin_user_id', flat=True)
    user_groups = UserGroups.objects.filter(admin_user_id__in=admin_user).values('user__username', 'admin_user__username')
    for users in user_groups:
        for key, value in users.iteritems():
            if user.username != value and value not in user_list:
                user_list.append(value)
    is_display = ''
    if not user_list:
        is_display = 'display-none'
    categories = SKUMaster.objects.exclude(sku_category='').filter(user=user.id).values_list('sku_category', flat=True).distinct()
    return render(request, 'templates/create_orders.html', {'create_order_fields': CREATE_ORDER_FIELDS,
                                                            'create_order_fields1': CREATE_ORDER_FIELDS1, 'st_fields': RAISE_ST_FIELDS,
                                                            'st_fields1': RAISE_ST_FIELDS1, 'user_list': user_list, 'is_display': is_display,
                                                            'categories': categories })

@login_required
@get_admin_user
def view_manifest(request, user):
    is_display = ''
    if not permissionpage(request,'add_orderdetail'):
        return render(request, 'templates/permission_denied.html')
    marketplace = OrderDetail.objects.filter(status=1, user = user.id).values('marketplace').distinct()
    batch_switch = 'false'
    data = MiscDetail.objects.filter(user = user.id, misc_type='batch_switch')
    if data:
        batch_switch = data[0].misc_value

    tb1_class = 'block'
    tb2_class = 'none'
    if batch_switch == 'true':
        tb1_class = 'none'
        tb2_class = 'block'
    warehouses = UserGroups.objects.filter(Q(user__username=user.username) | Q(admin_user__username=user.username))
    if not warehouses:
        is_display = 'display-none'
    return render(request, 'templates/view_manifest.html', {'batch_switch': batch_switch, 'tb1_class': tb1_class, 'tb2_class': tb2_class,
                                                            'marketplace': marketplace, 'st_headers': STOCK_TRANSFER_HEADERS,
                                                            'is_display': is_display})


@csrf_exempt
@login_required
@get_admin_user
def pull_confirmation(request, user=''):
    if not permissionpage(request,'add_picklist'):
        return render(request, 'templates/permission_denied.html')
    return render(request, 'templates/pull_confirmation.html')

@csrf_exempt
@login_required
def pullto_locate(request):
    return render(request, 'templates/pullto_locate.html')

@csrf_exempt
@login_required
def stock_detail(request):
    if not permissionpage(request,'add_stockdetail'):
        return render(request, 'templates/permission_denied.html')
    return render(request, 'templates/stock_detail.html')

def xls_to_response(xls, fname):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=%s' % fname
    xls.save(response)
    return response

def anvalid(name):
    test = re.findall('[^a-zA-Z0-9_-]', name)
    message = ''
    if test:
        message = '%s should accepts only alphanumeric, _ and -'
    return message

def namevalid(name):
    test = re.findall('[^a-zA-Z&/. ]|^[. ]', name)
    message = ''
    if test:
        message = '%s should accepts only letters and space.'
    return message


@csrf_exempt
def error_file_download(error_file):
    with open(error_file, 'r') as excel:
        data = excel.read()
    response = HttpResponse(data, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(error_file)
    return response

@csrf_exempt
def get_work_sheet(sheet_name, sheet_headers):
    wb = Workbook()
    ws = wb.add_sheet(sheet_name)
    header_style = easyxf('font: bold on')
    for count, header in enumerate(sheet_headers):
        ws.write(0, count, header, header_style)
    return wb, ws

@csrf_exempt
@get_admin_user
def sku_form(request, user=''):
    sku_file = request.GET['download-sku-file']
    if sku_file:
        return error_file_download(sku_file)

    wb, ws = get_work_sheet('skus', SKU_HEADERS)
    data = SKUMaster.objects.filter(wms_code='', user = user.id)
    for data_count, record in enumerate(data):
        if record.wms_code:
            continue

        data_count += 1
        ws.write(data_count, 0, record.wms_code)

    return xls_to_response(wb, '%s.sku_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def supplier_form(request, user=''):
    supplier_file = request.GET['download-supplier-file']
    if supplier_file:
        return error_file_download(supplier_file)

    wb, ws = get_work_sheet('supplier', SUPPLIER_HEADERS)
    return xls_to_response(wb, '%s.supplier_form.xls' % str(user.id))


@csrf_exempt
@get_admin_user
def supplier_sku_form(request, user=''):
    supplier_file = request.GET['download-supplier-sku-file']
    if supplier_file:
        return error_file_download(supplier_file)

    wb, ws = get_work_sheet('supplier', SUPPLIER_SKU_HEADERS)
    return xls_to_response(wb, '%s.supplier_sku_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def marketplace_sku_form(request, user=''):
    market_list = ['WMS Code']
    market_sku = []
    market_desc = []
    supplier_file = request.GET['download-marketplace-sku-file']
    if supplier_file:
        return error_file_download(supplier_file)
    market_places = Marketplaces.objects.filter(user=user.id).values_list('name', flat=True)
    for market in market_places:
        market_sku.append(market + " SKU")
        market_desc.append(market + " Description")
    market_list = market_list + market_sku + market_desc

    wb, ws = get_work_sheet('supplier', market_list)
    return xls_to_response(wb, '%s.marketplace_sku_form.xls' % str(user.id))

@csrf_exempt
@get_admin_user
def order_form(request, user=''):
    order_file = request.GET['download-order-form']
    if order_file:
        with open(order_file, 'r') as excel:
            data = excel.read()
        response = HttpResponse(data, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(order_file)
        return response

    wb = Workbook()
    ws = wb.add_sheet('supplier')
    header_style = easyxf('font: bold on')

    for count, header in enumerate(ORDER_HEADERS):
        ws.write(0, count, header, header_style)

    return xls_to_response(wb, '%s.order_form.xls' % str(user.id))


@csrf_exempt
@get_admin_user
def purchase_order_form(request, user=''):
    order_file = request.GET['download-purchase-order-form']
    if order_file:
        with open(order_file, 'r') as excel:
            data = excel.read()
        response = HttpResponse(data, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(order_file)
        return response
    wb = Workbook()
    ws = wb.add_sheet('supplier')
    header_style = easyxf('font: bold on')
    for count, header in enumerate(PURCHASE_ORDER_HEADERS):
        ws.write(0, count, header, header_style)

    return xls_to_response(wb, '%s.purchase_order_form.xls' % str(user.id))


@csrf_exempt
@get_admin_user
def location_form(request, user=''):
    loc_file = request.GET['download-loc-file']
    if loc_file:
        return error_file_download(loc_file)

    wb, ws = get_work_sheet('Locations', LOCATION_HEADERS)
    return xls_to_response(wb, '%s.location_form.xls' % str(user.id))


@csrf_exempt
@login_required
@get_admin_user
def inventory_form(request, user=''):
    inventory_file = request.GET['download-file']
    if inventory_file:
        return error_file_download(inventory_file)
    pallet_switch = get_misc_value('pallet_switch', user.id)
    if pallet_switch == 'true' and 'Pallet Number' not in EXCEL_HEADERS:
        EXCEL_HEADERS.append("Pallet Number")
    wb, ws = get_work_sheet('Inventory', EXCEL_HEADERS)
    return xls_to_response(wb, '%s.inventory_form.xls' % str(user.id))


@csrf_exempt
@login_required
@get_admin_user
def move_inventory_form(request, user=''):
    inventory_file = request.GET['download-move-inventory-file']
    if inventory_file:
        return error_file_download(inventory_file)
    wb, ws = get_work_sheet('Inventory', MOVE_INVENTORY_UPLOAD_FIELDS)
    return xls_to_response(wb, '%s.move_inventory_form.xls' % str(user.id))


@csrf_exempt
def write_error_file(f_name, index_status, open_sheet, headers_data, work_sheet):
    headers = copy.copy(headers_data)
    headers.append('Status')
    wb, ws = get_work_sheet(work_sheet, headers)

    for row_idx in range(1, open_sheet.nrows):
        for col_idx in range(0, len(headers_data)):
            ws.write(row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value)

        index_data = index_status.get(row_idx, '')
        if index_data:
            index_data = ', '.join(index_data)
        ws.write(row_idx, col_idx + 1, index_data)

    wb.save(f_name)

@csrf_exempt
def rewrite_excel_file(f_name, index_status, open_sheet):
    wb = Workbook()
    ws = wb.add_sheet(open_sheet.name)
    for row_idx in range(0, open_sheet.nrows):
        if row_idx == 0:
            for col_idx in range(0, open_sheet.ncols):
                ws.write(row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value, easyxf('font: bold on'))
            ws.write(row_idx, col_idx + 1, 'Status', easyxf('font: bold on'))

        else:
            for col_idx in range(0, open_sheet.ncols):
                ws.write(row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value)

            index_data = index_status.get(row_idx, '')
            if index_data:
                index_data = ', '.join(index_data)
            ws.write(row_idx, col_idx + 1, index_data)

    wb.save(f_name)

@csrf_exempt
def rewrite_csv_file(f_name, index_status, reader):
    with open(f_name, 'w') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, delimiter=',')
        counter = 0
        for row in reader:
            if counter == 0:
                row.append('Status')
            else:
                row.append(', '.join(index_status.get(counter, [])))
            thedatawriter.writerow(row)
            counter += 1

def alphanum_validation(cell_data, check_type, index_status, row_idx):
    if isinstance(cell_data, (int, float)):
        cell_data = int(cell_data)
    cell_data = str(cell_data)
    error_code = anvalid(cell_data)
    if error_code:
        index_status.setdefault(row_idx, set()).add(error_code % check_type)
    return index_status

@csrf_exempt
def validate_location_form(open_sheet, user):
    location_data = []
    index_status = {}
    header_data = open_sheet.cell(0, 0).value
    if header_data != 'Zone':
        return 'Invalid File'

    for row_idx in range(1, open_sheet.nrows):
        for col_idx in range(0, len(LOCATION_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value

            validation_dict = {0: 'Zone', 1: 'Location'}
            if col_idx in validation_dict:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing %s' % value)
                    break

                value = validation_dict[col_idx]
                index_status = alphanum_validation(cell_data, value, index_status, row_idx)

            if col_idx == 1:
                if cell_data in location_data:
                    index_status.setdefault(row_idx, set()).add('Duplicate Location')
                for index, location in enumerate(location_data):
                    if location == cell_data:
                        index_status.setdefault(index + 1, set()).add('Duplicate Location')

                location_data.append(cell_data)
            elif col_idx in (2, 3, 4):
                if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')
            elif col_idx == 5:
                all_groups = SKUGroups.objects.filter(user=user).values_list('group', flat=True)
                cell_datas = cell_data.split(',')
                for cell_data in cell_datas:
                    if cell_data and not cell_data in all_groups:
                        index_status.setdefault(row_idx, set()).add('SKU Group not found')


    if not index_status:
        return 'Success'
    f_name = '%s.location_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, LOCATION_HEADERS, 'Issues')
    return f_name

@csrf_exempt
def process_location(request, open_sheet, user):
    for row_idx in range(1, open_sheet.nrows):
        location_data = copy.deepcopy(LOC_DATA)
        for col_idx in range(0, len(LOCATION_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value

            if col_idx == 0:
                zone = cell_data.upper()
                zone_data = ZoneMaster.objects.filter(zone=zone, user=user.id)
                if not zone_data:
                    zone_data = copy.deepcopy(ZONE_DATA)
                    zone_data['user'] = user.id
                    zone_data['zone'] = zone
                    zone_data = ZoneMaster(**zone_data)
                    zone_data.save()
                else:
                    zone_data = zone_data[0]

            if not cell_data:
                continue

            index_dict = {1: 'location', 2: 'max_capacity', 3: 'fill_sequence', 4: 'pick_sequence'}

            if col_idx in index_dict:
                location_data[index_dict[col_idx]] = cell_data

        location = LocationMaster.objects.filter(location=location_data['location'], zone__user = user.id)
        if not location:
            location_data['zone_id'] = zone_data.id
            location = LocationMaster(**location_data)
            location.save()
        else:
            location = location[0]
        sku_group = open_sheet.cell(row_idx, 5).value
        if sku_group:
            sku_group = sku_group.split(',')
            save_location_group(location.id, sku_group, user)

@csrf_exempt
@get_admin_user
def location_upload(request, user=''):
    fname = request.FILES['files']
    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')

    status = validate_location_form(open_sheet, user.id)
    if status != 'Success':
        return HttpResponse(status)
    process_location(request, open_sheet, user)
    return HttpResponse('Success')

def process_date(value):
    value = value.split('/')
    value = datetime.date(int(value[2]), int(value[0]), int(value[1]))
    return value

def get_search_params(request):
    search_params = {}
    headers = []
    date_fields = ['from_date', 'to_date']
    data_mapping = {'start': 'start', 'length': 'length', 'draw': 'draw', 'search[value]': 'search_term',
                    'columns[0][search][value]': 'search_0', 'columns[1][search][value]': 'search_1',
                    'columns[2][search][value]': 'search_2', 'columns[3][search][value]': 'search_3',
                    'columns[4][search][value]': 'search_4', 'columns[5][search][value]': 'search_5',
                    'columns[6][search][value]': 'search_6', 'columns[7][search][value]': 'search_7',
                    'columns[8][search][value]': 'search_8', 'columns[9][search][value]': 'search_9',
                    'columns[10][search][value]': 'search_10', 'columns[11][search][value]': 'search_11', 'order[0][dir]': 'order_term',
                    'order[0][column]': 'order_index', 'from_date': 'from_date', 'to_date': 'to_date', 'wms_code': 'wms_code',
                    'supplier': 'supplier', 'sku_code': 'sku_code', 'sku_category': 'sku_category', 'sku_type': 'sku_type',
                    'sku_class': 'sku_class', 'zone_id': 'zone', 'location': 'location', 'open_po': 'open_po', 'marketplace': 'marketplace'}
    int_params = ['start', 'length', 'draw', 'order[0][column]']
    request_data = request.POST
    if not request_data:
        request_data = request.GET
    for key, value in request_data.iteritems():

        if '[data]' in key:
            headers.append(value)

        if key in data_mapping and value:
            if key in int_params:
                value = int(value)

            if key in date_fields:
                value = process_date(value)
            search_params[data_mapping[key]] = value

    return (headers, search_params)

@get_admin_user
def print_sales_returns(request, user=''):
    search_parameters = {}
    headers, search_params = get_search_params(request)
    if 'creation_date' in search_params:
        from_date = search_params['creation_date'].split('/')
        search_parameters['creation_date__startswith'] = datetime.date(int(from_date[2]), int(from_date[0]), int(from_date[1]))
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code'].upper()
    if 'wms_code' in search_params:
        search_parameters['sku__wms_code'] = search_params['wms_code'].upper()
    if 'order_id' in search_params:
        value = search_params['order_id'].strip('OD').strip('MN').strip('SR')
        search_parameters['order_id'] = value
    if 'customer_id' in search_params:
        search_parameters['order__customer_id'] = value
    search_parameters['sku__user'] = user.id
    if search_parameters:
        sales_return = OrderReturns.objects.filter(**search_parameters)
    else:
        sales_return = OrderReturns.objects.filter(user = user.id)
    report_data = []
    for data in sales_return:
        order_id = ''
        customer_id = ''
        if data.order:
            order_id = data.order.order_id
            customer_id = data.order.customer_id
        report_data.append((data.sku.sku_code, order_id, customer_id, str(data.creation_date).split('+')[0],
                            data.status, data.quantity))

    headers = ('SKU Code', 'Order ID', 'Customer ID', 'Return Date', 'Status', 'Quantity')
    html_data = create_reports_table(headers, report_data)
    return HttpResponse(html_data)

@csrf_exempt
@login_required
@get_admin_user
def get_dispatch_filter(request, user=''):
    headers, search_params = get_search_params(request)
    temp_data = get_dispatch_data(search_params, user)

    return HttpResponse(json.dumps(temp_data, cls=DjangoJSONEncoder), content_type='application/json')

@get_admin_user
def print_dispatch_summary(request, user=''):
    search_parameters = {}

    headers, search_params = get_search_params(request)
    report_data = get_dispatch_data(search_params, user)
    report_data = report_data['aaData']

    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

@csrf_exempt
@get_admin_user
def excel_reports(request, user=''):
    excel_name = ''
    func_name = ''
    headers, search_params = get_search_params(request)
    form_data = request.POST['serialize_data'].split('&')
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
    report_data = func_name(search_params, user)
    if isinstance(report_data, tuple):
        report_data = report_data[0]
    excel_data = print_excel(request,report_data, headers, excel_name)
    return excel_data

@csrf_exempt
@login_required
@get_admin_user
def print_po_reports(request, user=''):
    data_id = int(request.GET['data'])
    results = PurchaseOrder.objects.filter(order_id = data_id, open_po__sku__user = user.id)
    po_data = []
    total = 0
    for data in results:
        po_data.append([data.open_po.sku.wms_code, data.open_po.sku.sku_desc, data.received_quantity, data.open_po.price])
        total += data.open_po.order_quantity * data.open_po.price

    if results:
        address = results[0].open_po.supplier.address
        address = '\n'.join(address.split(','))
        telephone = results[0].open_po.supplier.phone_number
        name = results[0].open_po.supplier.name
        order_id = results[0].order_id
        po_reference = '%s%s_%s' %(results[0].prefix, str(results[0].creation_date).split(' ')[0].replace('-', ''), results[0].order_id)
        order_date = str(results[0].open_po.creation_date).split('+')[0]
        user_profile = UserProfile.objects.get(user_id=user.id)
        w_address = user_profile.address
    table_headers = ('WMS CODE', 'Description', 'Received Quantity', 'Unit Price')
    return render(request, 'templates/toggle/po_template.html', {'table_headers': table_headers, 'data': po_data, 'address': address,
                           'order_id': order_id, 'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total, 
                           'po_reference': po_reference, 'w_address': w_address, 'company_name': user_profile.company_name,
                           'display': 'display-none' })


@csrf_exempt
@login_required
@get_admin_user
def get_receipt_filter(request, user=''):
    headers, search_params = get_search_params(request)
    temp_data = get_receipt_filter_data(search_params, user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def print_receipt_summary(request, user=''):
    html_data = ''
    headers, search_params = get_search_params(request)
    report_data = get_receipt_filter_data(search_params, user)

    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

@csrf_exempt
@login_required
@get_admin_user
def print_shipment(request, user=''):
    ship_id = request.GET['ship_id']
    order_shipment1 = OrderShipment.objects.filter(shipment_number=ship_id)
    if order_shipment1:
        order_shipment = order_shipment1[0]
    else:
        return HttpResponse('No Records')
    order_package = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id).order_by('package_reference')
    package_data = []
    all_data = {}
    total = {}
    report_data = {'shipment_number': ship_id, 'date': NOW, 'truck_number': order_shipment.truck_number}
    for package in order_package:
        shipment_info = ShipmentInfo.objects.filter(order_packaging_id=package.id)
        for data in shipment_info:
            cond = data.order.customer_name
            all_data.setdefault(cond, [])
            all_data[cond].append({'pack_reference': str(data.order_packaging.package_reference), 'sku_code': str(data.order.sku.sku_code),
                                   'quantity': str(data.shipping_quantity)})

    for key, value in all_data.iteritems():
        total[key] = 0
        for i in value:
            total[key] += int(i['quantity'])

    headers = ('Package Reference', 'SKU Code', 'Shipping Quantity')
    return render(request, 'templates/toggle/shipment_template.html', {'table_headers': headers, 'report_data': report_data,
                                                                       'package_data': all_data, 'total': total})

@csrf_exempt
@login_required
@get_admin_user
def print_po(request, user=''):
    data_id = request.GET.get('data','')
    search_parameters = {'open_po__sku__user': user.id}
    if request.GET.get('wms_code',''):
        search_parameters['open_po__sku__wms_code'] = request.GET['wms_code']
    if data_id:
        search_parameters['open_po_id'] = data_id
    results = PurchaseOrder.objects.filter(**search_parameters)

    po_data = []
    total = 0
    total_qty = 0
    for data in results:
        po_data.append([data.open_po.sku.wms_code, data.open_po.sku.sku_desc, data.open_po.order_quantity, data.open_po.price])
        total += data.open_po.order_quantity * data.open_po.price
        total_qty += int(data.open_po.order_quantity)

    address = results[0].open_po.supplier.address
    address = '\n'.join(address.split(','))
    telephone = results[0].open_po.supplier.phone_number
    name = results[0].open_po.supplier.name
    order_id = data_id
    order_date = str(results[0].open_po.creation_date).split('+')[0]
    table_headers = ('WMS CODE', 'Description', 'Order Quantity', 'Unit Price')
    return render(request, 'templates/toggle/po_template.html', {'table_headers': table_headers, 'data': po_data, 'address': address,
                           'order_id': order_id, 'telephone': str(telephone), 'name': name, 'order_date': order_date, 'total': total,
                           'user_name': user.username, 'total_qty': total_qty, 'display': 'display-none'})

@csrf_exempt
@login_required
@get_admin_user
def print_shipment(request, user=''):
    ship_id = request.GET['ship_id']
    order_shipment1 = OrderShipment.objects.filter(shipment_number=ship_id)
    if order_shipment1:
        order_shipment = order_shipment1[0]
    else:
        return HttpResponse('No Records')
    order_package = OrderPackaging.objects.filter(order_shipment_id=order_shipment.id).order_by('package_reference')
    package_data = []
    all_data = {}
    total = {}
    report_data = {'shipment_number': ship_id, 'date': NOW, 'truck_number': order_shipment.truck_number}
    for package in order_package:
        shipment_info = ShipmentInfo.objects.filter(order_packaging_id=package.id)
        for data in shipment_info:
            cond = data.order.customer_name
            all_data.setdefault(cond, [])
            all_data[cond].append({'pack_reference': str(data.order_packaging.package_reference), 'sku_code': str(data.order.sku.sku_code),
                                   'quantity': str(data.shipping_quantity)})

    for key, value in all_data.iteritems():
        total[key] = 0
        for i in value:
            total[key] += int(i['quantity'])

    headers = ('Package Reference', 'SKU Code', 'Shipping Quantity')
    return render(request, 'templates/toggle/shipment_template.html', {'table_headers': headers, 'report_data': report_data,
                                                                       'package_data': all_data, 'total': total})

@csrf_exempt
@login_required
@get_admin_user
def get_sku_supplier_update(request,user=''):
    data_id = int(request.GET['data_id'])
    record = SKUSupplier.objects.filter(id=data_id, sku__user=user.id)
    for dat in record:
        data = ((('Supplier ID', ('supplier_id', dat.supplier.id), 15), ('WMS Code', ('sku_id', dat.sku.wms_code), 60)), (('Supplier Code', ('supplier_code', dat.supplier_code), 32), ('Priority *', ('preference', dat.preference), 32)), (('MOQ', ('moq', dat.moq), 256), ('Price', ('price', dat.price))))

    return render(request, 'templates/toggle/update_sku_supplier.html', {'data': data, 'record_id': dat.id})


def get_supplier_details_data(search_params, user):
    lis = ['Order Date', 'PO Number', 'Supplier Name', 'WMS Code', 'Design', 'Ordered Quantity', 'Received Quantity', 'Status']
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    supplier_data = {'aaData': []}
    supplier_name = search_params.get('supplier')
    if supplier_name:
        suppliers = PurchaseOrder.objects.exclude(status='location-assigned').filter(open_po__supplier__id=supplier_name, received_quantity__lt=F('open_po__order_quantity'), open_po__sku__user=user.id)
    else:
        suppliers = PurchaseOrder.objects.exclude(status='location-assigned').filter(received_quantity__lt=F('open_po__order_quantity'), open_po__sku__user=user.id)

    supplier_data['recordsTotal'] = len(suppliers)
    supplier_data['recordsFiltered'] = len(suppliers)
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)

    for supplier in suppliers:
        design_codes = SKUSupplier.objects.filter(supplier=supplier.open_po.supplier, sku=supplier.open_po.sku, sku__user=user.id)
        supplier_code = ''
        if design_codes:
            supplier_code = design_codes[0].supplier_code
        status = ''
        if supplier.received_quantity == 0:
            status = 'Yet to Receive'
        elif (supplier.open_po.order_quantity - supplier.received_quantity) == 0:
            status = 'Received'
        else:
            status = 'Partially Received'
        supplier_data['aaData'].append(OrderedDict(( ('Order Date', str(supplier.po_date).split(' ')[0]),
                                        ('PO Number', '%s%s_%s' %(supplier.prefix, str(supplier.po_date).split(' ')[0].replace('-', ''), supplier.order_id)),
                                        ('Supplier Name', supplier.open_po.supplier.name), ('WMS Code', supplier.open_po.sku.wms_code), ('Design', supplier_code),
                                        ('Ordered Quantity', supplier.open_po.order_quantity),
                                        ('Received Quantity', supplier.received_quantity), ('Status', status) )))

    sort_col = lis[col_num]

    if order_term == 'asc':
        supplier_data['aaData'] = sorted(supplier_data['aaData'], key=itemgetter(sort_col))
    else:
        supplier_data['aaData'] = sorted(supplier_data['aaData'], key=itemgetter(sort_col), reverse=True)

    if stop_index:
        supplier_data['aaData'] = supplier_data['aaData'][start_index:stop_index]

    return supplier_data


@csrf_exempt
@login_required
@get_admin_user
def get_supplier_details(request, user=''):
    headers, search_params = get_search_params(request)
    supplier_data = get_supplier_details_data(search_params, user)
    return HttpResponse(json.dumps(supplier_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def print_supplier_pos(request, user=''):
    html_data = ''
    headers, search_params = get_search_params(request)
    supplier_pos = get_supplier_details_data(search_params, user)
    supplier_pos = supplier_pos['aaData']
    user_profile = UserProfile.objects.filter(user_id = request.user.id)

    if supplier_pos:
        html_data = create_po_reports_table(supplier_pos[0].keys(), supplier_pos, user_profile[0], '')
    return HttpResponse(html_data)

@csrf_exempt
@login_required
@get_admin_user
def get_location_filter(request, user=''):
    headers, search_params = get_search_params(request)
    temp_data, total_quantity = get_location_stock_data(search_params, user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def print_stock_location(request, user=''):

    headers, search_params = get_search_params(request)
    report_data, total_quantity = get_location_stock_data(search_params, user)

    data = 'Total Stock: %s<br/><br/>' % total_quantity

    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(data + html_data)

@csrf_exempt
@login_required
@get_admin_user
def get_po_filter(request, user=''):
    headers, search_params = get_search_params(request)

    temp_data = get_po_filter_data(search_params, user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
@login_required
@get_admin_user
def print_sku(request, user=''):
    headers, search_params = get_search_params(request)
    report_data = get_sku_filter_data(search_params, user)

    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

@csrf_exempt
@login_required
@get_admin_user
def get_sku_filter(request, user=''):

    headers, search_params = get_search_params(request)
    temp_data = get_sku_filter_data(search_params, user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

def print_sku_wise_data(search_params, user):
    lis = ['SKU Code', 'WMS Code', 'Product Description', 'SKU Category', 'Total Quantity']
    lis1 = ['sku_code', 'wms_code', 'sku_desc', 'sku_category', 'id']
    order_index = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    order_data = lis1[order_index]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    cmp_data = ('sku_code', 'wms_code', 'sku_category', 'sku_type', 'sku_class')
    for data in cmp_data:
        if data in search_params:
            search_parameters['%s__%s' % (data, 'iexact')] = search_params[data]

    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['user'] = user.id

    stock_detail = StockDetail.objects.exclude(location__zone__zone='DEFAULT').filter(sku__user=user.id).values('sku_id').distinct().\
                                                                               annotate(total=Sum('quantity'))
    sku_master = SKUMaster.objects.filter(**search_parameters).order_by(order_data).values('id', 'sku_code', 'wms_code', 'sku_desc',
                                                                                           'sku_category')
    temp_data['recordsTotal'] = sku_master.count()
    temp_data['recordsFiltered'] = sku_master.count()

    if stop_index and not 'id' in order_data:
        sku_master = sku_master[start_index:stop_index]

    sku_ids = map(lambda d: d['sku_id'], stock_detail)
    total_sums = map(lambda d: d['total'], stock_detail)
    for data in sku_master:
        total_quantity = 0
        if data['id'] in sku_ids:
            total_quantity = total_sums[sku_ids.index(data['id'])]
        temp_data['aaData'].append(OrderedDict(( ('SKU Code', data['sku_code']), ('WMS Code', data['wms_code']),
                                                 ('Product Description', data['sku_desc']), ('SKU Category', data['sku_category']),
                                                 ('Total Quantity', total_quantity) )))
    if 'id' in order_data:
        sort_col = lis[order_index]
        if order_term == 'asc':
            temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
        else:
            temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)
        if stop_index:
            temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]
    return temp_data

@csrf_exempt
@login_required
@get_admin_user
def get_sku_stock_filter(request, user=''):
    headers, search_params = get_search_params(request)
    temp_data = print_sku_wise_data(search_params, user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def print_sku_wise_stock(request, user=''):
    headers, search_params = get_search_params(request)
    report_data = print_sku_wise_data(search_params, user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

@csrf_exempt
@login_required
@get_admin_user
def get_sku_purchase_filter(request, user=''):
    headers, search_params = get_search_params(request)
    temp_data = sku_wise_purchase_data(search_params, user)

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def print_sku_wise_purchase(request, user=''):
    headers, search_params = get_search_params(request)
    report_data = sku_wise_purchase_data(search_params, user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

def get_sales_return_filter_data(search_params, user):
    temp_data = copy.deepcopy(AJAX_DATA)
    lis = ['sku__sku_code', 'order__order_id', 'order__customer_id', 'creation_date', 'status', 'quantity']
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    search_parameters = {}
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        from_date = search_params['from_date']
        search_parameters['creation_date__startswith'] = from_date
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code'].upper()
    if 'wms_code' in search_params:
        search_parameters['sku__wms_code'] = search_params['wms_code'].upper()
    if 'order_id' in search_params:
        value = search_params['order_id'].strip('OD').strip('MN').strip('SR')
        search_parameters['order_id'] = value
    if 'customer_id' in search_params:
        search_parameters['order__customer_id'] = value
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['sku__user'] = user.id
    if search_parameters:
        sales_return = OrderReturns.objects.filter(**search_parameters).order_by(order_data)
    temp_data['recordsTotal'] = len(sales_return)
    temp_data['recordsFiltered'] = len(sales_return)
    if stop_index:
        sales_return = sales_return[start_index:stop_index]
    for data in sales_return:
        order_id = ''
        customer_id = ''
        if data.order:
            order_id = str(data.order.order_code) + str(data.order.order_id)
            customer_id = data.order.customer_id
        temp_data['aaData'].append(OrderedDict(( ('SKU Code', data.sku.sku_code), ('Order ID', order_id),
                                                 ('Customer ID', customer_id), ('Return Date', get_local_date(user, data.creation_date)),
                                                 ('Status', data.status), ('Quantity', data.quantity) )))
    return temp_data

@csrf_exempt
@login_required
@get_admin_user
def get_sales_return_filter(request, user=''):
    headers, search_params = get_search_params(request)
    temp_data = get_sales_return_filter_data(search_params, user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')


def get_adjust_filter_data(search_params, user):
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    temp_data['draw'] = search_params.get('draw')
    lis = ['cycle__sku__sku_code', 'cycle__location__location', 'cycle__seen_quantity', 'creation_date', 'reason']
    col_num = search_params.get('order_index', 0)
    order_term = search_params.get('order_term', 'asc')
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['cycle__updation_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date']  + datetime.timedelta(1), datetime.time())
        search_parameters['cycle__updation_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['cycle__sku__sku_code'] = search_params['sku_code'].upper()
    if 'wms_code' in search_params:
        search_parameters['cycle__sku__wms_code'] = search_params['wms_code'].upper()
    if 'location' in search_params:
        search_parameters['cycle__location__location'] = search_params['location'].upper()
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['cycle__sku__user'] = user.id
    if search_parameters:
        adjustments = InventoryAdjustment.objects.filter(**search_parameters).order_by(order_data)
    temp_data['recordsTotal'] = len(adjustments)
    temp_data['recordsFiltered'] = len(adjustments)
    if stop_index:
        adjustments = adjustments[start_index:stop_index]
    for data in adjustments:
        quantity = int(data.cycle.seen_quantity) - int(data.cycle.quantity)

        temp_data['aaData'].append(OrderedDict(( ('SKU Code', data.cycle.sku.sku_code), ('Location', data.cycle.location.location),
                                                 ('Quantity', quantity), ('Date', str(data.creation_date).split('+')[0]),
                                                 ('Remarks', data.reason) )))
    return temp_data

@csrf_exempt
@login_required
@get_admin_user
def get_inventory_adjust_filter(request, user=''):
    headers, search_params = get_search_params(request)
    temp_data = get_adjust_filter_data(search_params, user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def print_adjust_report(request, user=''):
    headers, search_params = get_search_params(request)
    report_data = get_adjust_filter_data(search_params, user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

def get_aging_filter_data(search_params, user):
    temp_data = copy.deepcopy(AJAX_DATA)
    search_parameters = {}
    all_data = OrderedDict()
    temp_data['draw'] = search_params.get('draw')
    if 'from_date' in search_params:
        search_params['from_date'] = datetime.datetime.combine(search_params['from_date'], datetime.time())
        search_parameters['receipt_date__gt'] = search_params['from_date']
    if 'to_date' in search_params:
        search_params['to_date'] = datetime.datetime.combine(search_params['to_date']  + datetime.timedelta(1), datetime.time())
        search_parameters['receipt_date__lt'] = search_params['to_date']
    if 'sku_code' in search_params:
        search_parameters['sku__sku_code'] = search_params['sku_code'].upper()
    if 'sku_category' in search_params:
        search_parameters['sku__sku_category'] = search_params['sku_category']
    start_index = search_params.get('start', 0)
    stop_index = start_index + search_params.get('length', 0)
    search_parameters['sku__user'] = user.id
    search_parameters['quantity__gt'] = 0
    filtered = StockDetail.objects.filter(**search_parameters).\
                                   values('receipt_date', 'sku__sku_code', 'sku__sku_desc', 'sku__sku_category', 'location__location').\
                                   annotate(total=Sum('quantity'))

    for stock in filtered:
        cond = (stock['sku__sku_code'], stock['sku__sku_desc'], stock['sku__sku_category'],
                (datetime.datetime.now().date() - stock['receipt_date'].date()).days, stock['location__location'])
        all_data.setdefault(cond, 0)
        all_data[cond] += stock['total']
    temp_data['recordsTotal'] = len(all_data)
    temp_data['recordsFiltered'] = len(all_data)
    temp = all_data
    all_data = all_data.keys()
    if stop_index:
        all_data = all_data[start_index:stop_index]
    for data in all_data:
        temp_data['aaData'].append(OrderedDict(( ('SKU Code', data[0]), ('SKU Description', data[1]), ('SKU Category', data[2]),
                                                 ('Location', data[4]), ('Quantity', temp[data]), ('As on Date(Days)', data[3]) )))
    return temp_data

@csrf_exempt
@login_required
@get_admin_user
def get_inventory_aging_filter(request, user=''):
    headers, search_params = get_search_params(request)
    temp_data = get_aging_filter_data(search_params, user)
    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def print_aging_report(request, user=''):
    headers, search_params = get_search_params(request)
    report_data = get_aging_filter_data(search_params, user)
    report_data = report_data['aaData']
    if report_data:
        html_data = create_reports_table(report_data[0].keys(), report_data)
    return HttpResponse(html_data)

@csrf_exempt
@login_required
@get_admin_user
def resolved_issues(request, user=''):
    headers, search_params = get_search_params(request)
    temp_data = copy.deepcopy(AJAX_DATA)
    temp_data['draw'] = search_params.get('draw')

    start_index = search_params.get('start')
    stop_index = start_index + search_params.get('length')
    master_data = Issues.objects.filter(status='Resolved', user=request.user.id)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)

    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append({'Issue ID': data.id, 'Issue Title': data.issue_title, 'Priority': data.priority,
                                    'Creation Date': str(data.creation_date).split('+')[0], 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'data-id': data.id}})

    return HttpResponse(json.dumps(temp_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def results_issue(request, user=''):
    headers, search_params = get_search_params(request)
    temp_data = copy.deepcopy( AJAX_DATA )
    temp_data['draw'] = search_params.get('draw')

    start_index = search_params.get('start')
    stop_index = start_index + search_params.get('length')

    master_data = Issues.objects.filter(status='Active', user=request.user.id)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)

    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append({'Issue ID': data.id, 'Issue Title': data.issue_title, 'Priority': data.priority,
                                    'Creation Date': str(data.creation_date).split('+')[0], 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'data-id': data.id}})

    return HttpResponse(json.dumps(temp_data), content_type='application/json')


@csrf_exempt
def get_discount_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):

    order_data = ''
    category_filter = {'user': user.id, 'discount__gt': 0}
    index_headers = {0: 'sku_code', 1: 'sku_category', 2: 'discount_percentage'}
    reverse = False

    if order_term and index_headers.get(col_num):
        order_data = '%s' % index_headers[col_num]
        if order_term == 'desc':
            reverse = True
            order_data = '%s' % index_headers[col_num]

    category = CategoryDiscount.objects.filter(**category_filter)
    category_list = category.values_list('category', flat=True)

    search_params = {'user': user.id}
    if search_term:
        master_data = SKUMaster.objects.filter(Q(discount_percentage__gt=0) | Q(sku_category__in = category_list)).\
                                        filter(Q(sku_code__icontains=search_term) | Q(sku_category__icontains=search_term),
                                        **search_params)
    else:
        master_data = SKUMaster.objects.filter(Q(discount_percentage__gt=0) | Q(sku_category__in = category_list), **search_params)

    if order_data:
        master_data = sorted(master_data, key=lambda instance: getattr(instance, order_data), reverse=reverse)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)

    for data in master_data[start_index:stop_index]:
        sku_category = category.filter(category = data.sku_category)
        category_discount = 0
        if sku_category:
            category_discount = sku_category[0].discount

        temp_data['aaData'].append(OrderedDict(( ('SKU Code', data.wms_code),('SKU Category', data.sku_category),
                                                 ('SKU Discount', data.discount_percentage),('Category Discount', category_discount),
                                                 ('DT_RowClass', 'results'),('DT_RowAttr', {'data-id': data.id}) )))
@fn_timer
def sku_excel_download(search_params, temp_data, headers, user):
    status_dict = {'1': 'Active', '0': 'Inactive'}
    marketplace_list = Marketplaces.objects.filter(user=user.id).values_list('name').distinct()
    search_terms = {}
    if search_params.get('search_0',''):
        search_terms["wms_code__icontains"] = search_params.get('search_0','')
    if search_params.get('search_1',''):
        search_terms["sku_desc__icontains"] = search_params.get('search_1','')
    if search_params.get('search_2',''):
        search_terms["sku_type__icontains"] = search_params.get('search_2','')
    if search_params.get('search_3',''):
        search_terms["sku_category__icontains"] = search_params.get('search_3','')
    if search_params.get('search_4',''):
        search_terms["sku_class__icontains"] = search_params.get('search_4','')
    if search_params.get('search_5',''):
        search_terms["zone__zone__icontains"] = search_params.get('search_5','')
    if search_params.get('search_6',''):
        if (str(search_params.get('search_6','')).lower() in "active"):
            search_terms["status__icontains"] = 1
        elif (str(search_params.get('search_6','')).lower() in "inactive"):
            search_terms["status__icontains"] = 0
        else:
            search_terms["status__icontains"] = "none"
    search_terms["user"] =  user.id
    sku_master = SKUMaster.objects.filter(**search_terms)
    sku_ids = sku_master.values_list('id', flat=True)
    master_data = MarketplaceMapping.objects.exclude(sku_type='').filter(sku_id__in=sku_ids, sku_type__in=marketplace_list)
    marketplaces = master_data.values_list('sku_type', flat=True).distinct()
    if master_data.count():
        for market in marketplaces:
            headers = headers + [market +' SKU', market + ' Description']
    excel_headers = headers
    wb, ws = get_work_sheet('skus', excel_headers)
    data_count = 0
    for data in sku_master:
        data_count += 1
        zone = ''
        if data.zone:
            zone = data.zone.zone
        ws.write(data_count, 0, data.wms_code)
        ws.write(data_count, 1, data.sku_desc)
        ws.write(data_count, 2, data.sku_type)
        ws.write(data_count, 3, data.sku_category)
        ws.write(data_count, 4, data.sku_class)
        ws.write(data_count, 5, zone)
        ws.write(data_count, 6, status_dict[str(int(data.status))])
        market_map = master_data.filter(sku_id=data.id).values('sku_id', 'sku_type').distinct()
        for dat in market_map:
            map_dat = market_map.values('marketplace_code', 'description')
            market_codes = map(operator.itemgetter('marketplace_code'), map_dat)
            market_desc = map(operator.itemgetter('description'), map_dat)
            indices = [i for i, s in enumerate(headers) if dat['sku_type'] in s]
            ws.write(data_count, indices[0], ', '.join(market_codes))
            ws.write(data_count, indices[1], ', '.join(market_desc))

    file_name = "%s.%s" % (user.id, 'SKU Master')
    path = 'static/excel_files/' + file_name + '.xls'
    wb.save(path)
    path_to_file = '../' + path
    return path_to_file

@csrf_exempt
@login_required
@get_admin_user
def results_data(request, user=''):
    excel = ''
    headers, search_params = get_search_params(request)
    temp_data = copy.deepcopy( AJAX_DATA )
    if not search_params:
        search_params = {'start': 0, 'draw': 1, 'length': 0, 'order_index': 0, 'order_term': u'asc',
                        'search_term' : request.POST.get('columns[]','')}
        index = 0
        search_index = 0
        while True:
          if (request.POST.get('columns[%s][search_data][index]' % str(search_index))):
              index = int(request.POST.get('columns[%s][search_data][index]' % str(search_index)))
              break
          else:
              search_index = search_index + 1

        main_index = search_index
        search_index = 0

        while (index):
            search_data = request.POST.get('columns[%s][search_data][search_%s]' % (str(main_index), str(search_index)))
            if (search_data):
                search_params['search_'+str(search_index)] = search_data
            search_index = search_index + 1
            index = index - 1

        data_table = request.POST.get('serialize_data', '').split('=')[-1]
        if data_table == 'sku_master':
            excel_data = sku_excel_download(search_params, temp_data, headers, user)
            return HttpResponse(str(excel_data))
        excel = 'true'
    temp_data['draw'] = search_params.get('draw')
    start_index = search_params.get('start')
    stop_index = start_index + search_params.get('length')
    if not stop_index:
        stop_index = None
    user_id = user.id
    if request.GET.get('table_name','') == 'stock-summary':
        wms_index = headers.index('  WMS Code')
        if not wms_index == 1:
            headers[1],headers[wms_index] = headers[wms_index], headers[1]
        if not 'Damaged Quantity' in headers and excel == 'true':
            headers.insert(headers.index('Quantity') + 1, 'Damaged Quantity')
    search_func = OrderedDict((('WMS SKU Code', (0, get_sku_results, [search_params.get('order_term'), search_params.get('order_index'),
search_params.get('search_0'), search_params.get('search_1'), search_params.get('search_2'),\
                                                       search_params.get('search_3'), search_params.get('search_4'), search_params.get('search_5'),\
                                                       search_params.get('search_6')])),
                               ('Receipt ID', (0, get_stock_detail_results, [search_params.get('order_term'), search_params.get('order_index'),
                                              search_params.get('search_0'), search_params.get('search_1'), search_params.get('search_2'),\
                                              search_params.get('search_3'), search_params.get('search_4'), search_params.get('search_5'),\
                                              search_params.get('search_6'), search_params.get('search_7'), search_params.get('search_8')])),
                               ('User Name', (0, get_user_results, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('Username', (0, get_warehouse_user_results, [search_params.get('order_term'), search_params.get('order_index'),
                                                search_params.get('search_0'), search_params.get('search_1'), search_params.get('search_2'),
                                                search_params.get('search_3')])),
                               ('Return ID', (0, get_order_returns, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('Product SKU Code', (0, get_bom_results, [search_params.get('order_term'), search_params.get('order_index'),
                                                     search_params.get('search_0'), search_params.get('search_1')])),
                               ('Total Quantity', (1, get_raised_stock_transfer, [search_params.get('order_term'), search_params.get('order_index'), search_params.get('search_0'), search_params.get('search_1')])),
                               ('Warehouse Name', (1, get_stock_transfer_orders, [search_params.get('order_term'), search_params.get('order_index')])),
                               (' Supplier ID', (1, get_po_suggestions, [search_params.get('order_term'), search_params.get('order_index'),
                                                 search_params.get('search_0'), search_params.get('search_1'), search_params.get('search_2'),
                                                search_params.get('search_3')])),
                               ('Shipment Date', (1, get_order_results, [search_params.get('order_term'), search_params.get('order_index'),
                                                  search_params.get('marketplace'), search_params.get('search_1'),
                                                  search_params.get('search_2'),search_params.get('search_3'), search_params.get('search_4'),
                                                  search_params.get('search_5'), search_params.get('search_6')])),
                               (' Zone', (1, get_order_returns_data, [search_params.get('order_term'), search_params.get('order_index')])),
                               (' Procurement Quantity', (1, get_rm_back_order_data, [search_params.get('order_term'), search_params.get('order_index')])),
                               (' Job Code', (0, get_confirmed_jo, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('  Job Code', (0, get_received_jo, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('Job Code ', (0, get_generated_jo, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('Job Code  ', (0, get_jo_confirmed, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('JO Reference', (1, get_open_jo, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('Picklist ID', (0, open_orders, ['open', search_params.get('order_term'), search_params.get('order_index')])),
                               ('Picklist ID ', (0, open_orders, ['picked', search_params.get('order_term'), search_params.get('order_index')])),
                               ('Picklist ID  ', (1, open_orders, ['batch_picked', search_params.get('order_term'), search_params.get('order_index')])),
                               ('Cycle Count ID', (0, get_cycle_confirmed, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('  WMS Code', (1, get_stock_results, [search_params.get('order_term'), search_params.get('order_index'),
                                              search_params.get('search_0'), search_params.get('search_1'), search_params.get('search_2'),
                                              search_params.get('search_3'), search_params.get('search_4'), excel])),
                               (' PO Number', (0, get_order_data, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('PO Number', (0, get_confirmed_po, [search_params.get('order_term'), search_params.get('order_index'),
                                                 search_params.get('search_0'), search_params.get('search_1'), search_params.get('search_2'),
                                                 search_params.get('search_3'), search_params.get('search_4')])),
                               ('Supplier ID', (0, get_supplier_results, [search_params.get('order_term'), search_params.get('order_index'),
                                               search_params.get('search_0'), search_params.get('search_1'), search_params.get('search_2'),\
                                               search_params.get('search_3'), search_params.get('search_4'), search_params.get('search_5')])),
                               ('Vendor ID', (0, get_vendor_master_results, [search_params.get('order_term'), search_params.get('order_index'),
                                               search_params.get('search_0'), search_params.get('search_1'), search_params.get('search_2'),\
                                               search_params.get('search_3'), search_params.get('search_4'), search_params.get('search_5')])),
                               ('Vendor Name', (2, get_saved_rworder, [search_params.get('order_term'), search_params.get('order_index')])),
                               (' Customer ID', (0, get_customer_master, [search_params.get('order_term'), search_params.get('order_index'),\
                                                 search_params.get('search_0'), search_params.get('search_1'), search_params.get('search_2'),
                                                 search_params.get('search_3'), search_params.get('search_4'), search_params.get('search_5')])),
                               ('Customer Name', (1, get_customer_sku_mapping, [search_params.get('order_term'),
                                                  search_params.get('order_index'),search_params.get('search_0'),search_params.get('search_1'),
                                                  search_params.get('search_2'), search_params.get('search_3')])),
                               ('Supplier ID ', (0, get_supplier_mapping, [search_params.get('order_term'), search_params.get('order_index'),
                                                search_params.get('search_0'), search_params.get('search_1'), search_params.get('search_2'),\
                                                search_params.get('search_3'), search_params.get('search_4')])),
                               (' SKU Code', (1, get_batch_data, [search_params.get('order_term'), search_params.get('order_index'),
                                             search_params.get('marketplace'), search_params.get('search_1'), search_params.get('search_2'),
                                             search_params.get('search_3')])),
                               ('Purchase Order ID', (0, get_quality_check_data, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('Shipment Number', (0, get_customer_results, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('Damaged Quantity', (1, get_returned_orders, [search_params.get('order_term'), search_params.get('order_index')])),
                               (' Damaged Quantity', (1, get_cancelled_orders, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('Move Quantity', (1, get_move_inventory, ['move'])),
                               ('Physical Quantity', (1, get_move_inventory, ['adj'])),
                               ('Offline Quantity', (2, get_sku_stock_data, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('WMS Code', (0, get_cycle_count, [search_params.get('order_term'), search_params.get('order_index'), search_params.get('search_0'),search_params.get('search_1'), search_params.get('search_2'), search_params.get('search_3')])),
                               ('SKU Discount', (2, get_discount_results, [search_params.get('order_term'), search_params.get('order_index')])),
                               ('Transit Quantity', (3, get_back_order_data, [search_params.get('order_term'), search_params.get('order_index')]))))
    for key, value in search_func.iteritems():
        if headers[value[0]] == key:
            params = [start_index, stop_index, temp_data, search_params.get('search_term')]
            params.extend(value[2])
            params.append(request)
            params.append(user)
            search_func[key][1](*params)
            break

    if excel == 'true':
        excel_data = print_excel(request,temp_data, headers)
        return excel_data
    return HttpResponse(json.dumps(temp_data, cls=DjangoJSONEncoder), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def stock_summary(request, user=''):
    headers = ['  WMS Code', 'Product Description', 'SKU Category', 'Quantity']
    if get_misc_value('production_switch', user.id) == 'true':
        stages = list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
        headers = headers + stages
    if not permissionpage(request,'add_stockdetail'):
        return render(request, 'templates/permission_denied.html')
    return render(request, 'templates/stock_summary.html', {'headers': headers})


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
                    'tax_inclusive': request.GET.get('tax_inclusive', ''),
                  }

    for key, value in toggle_data.iteritems():
        if not value:
            continue

        toggle_field = key
        selection = value
        break

    user_id = user.id
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

@csrf_exempt
@login_required
@get_admin_user
def save_groups(request, user=''):
    groups = request.GET.get('sku_groups')
    groups = groups.split(',')
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    for group in groups:
        group_obj = SKUGroups.objects.filter(group=group, user=user.id)
        if not group_obj:
            group_dict = copy.deepcopy(SKU_GROUP_FIELDS)
            group_dict['group'] = group
            group_dict['user'] = user.id
            new_group = SKUGroups(**group_dict)
            new_group.save()
    deleted_groups = set(all_groups) - set(groups)
    for group in deleted_groups:
        SKUGroups.objects.get(group=group, user=user.id).delete()
        skus = SKUMaster.objects.filter(sku_group=group, user=user.id).update(sku_group='')
        LocationGroups.objects.filter(group=group, location__zone__user=user.id).delete()
    return HttpResponse("Saved Successfully")

@csrf_exempt
@login_required
def supplier_master(request):
    return render(request, 'templates/supplier_master.html', {'add_supplier': SUPPLIER_FIELDS})

@csrf_exempt
@login_required
def uploads(request):
    return render(request, 'templates/uploads.html')

@csrf_exempt
@login_required
def sku_list_report(request):
    return render(request, 'templates/reports.html', {'reports_data': SKU_LIST_REPORTS_DATA, 'report': 'sku_list' })

@csrf_exempt
@login_required
def location_wise_filter(request):
    return render(request, 'templates/reports.html', {'reports_data': LOCATION_WISE_FILTER, 'report': 'location_wise' })

@csrf_exempt
@login_required
@get_admin_user
def supplier_wise_pos(request, user=''):
    suppliers = SupplierMaster.objects.filter(user=user.id)
    return render(request, 'templates/reports.html', {'reports_data': SUPPLIER_WISE_POS, 'report': 'supplier_wise',
                                                      'suppliers': suppliers})

@csrf_exempt
@login_required
def goods_receipt_note(request):
    return render(request, 'templates/reports.html', {'reports_data': GOODS_RECEIPT_NOTE, 'report': 'goods_receipt' })

@csrf_exempt
@login_required
@get_admin_user
def receipt_summary_report(request, user=''):
    suppliers = SupplierMaster.objects.filter(user=user.id)
    return render(request, 'templates/reports.html', {'reports_data': RECEIPT_SUMMARY, 'report': 'receipt_summary', 'suppliers': suppliers })

@csrf_exempt
@login_required
def dispatch_summary_report(request):
    return render(request, 'templates/reports.html', {'reports_data': DISPATCH_SUMMARY, 'report': 'dispatch_summary' })

@csrf_exempt
@login_required
@get_admin_user
def sku_wise_stock(request, user=''):
    categories = SKUMaster.objects.exclude(sku_category='').filter(user=user.id).values_list('sku_category', flat=True).distinct()
    return render(request, 'templates/reports.html', {'reports_data': SKU_WISE_STOCK, 'report': 'sku_stock', 'categories': categories})

@csrf_exempt
@login_required
@get_admin_user
def sku_wise_purchases(request, user=''):
    FIELDS = copy.deepcopy(SKU_WISE_PURCHASES)
    if get_permission(user, 'add_qualitycheck'):
        FIELDS.values()[0][0].insert(5, 'Rejected Quantity')
    return render(request, 'templates/reports.html', {'reports_data': FIELDS, 'report': 'sku_wise_purchases' })

@csrf_exempt
@login_required
def sales_return_report(request):
    return render(request, 'templates/reports.html', {'reports_data': SALES_RETURN_REPORT, 'report': 'sales_report'})

@csrf_exempt
@login_required
@get_admin_user
def inventory_adjust_report(request, user=''):
    return render(request, 'templates/reports.html', {'reports_data': INVENTORY_ADJUST_REPORT, 'report': 'inventory_adjust_report'})

@csrf_exempt
@login_required
@get_admin_user
def inventory_aging_report(request, user=''):
    categories = SKUMaster.objects.exclude(sku_category='').filter(user=user.id).values_list('sku_category', flat=True).distinct()
    return render(request, 'templates/reports.html', {'reports_data': INVENTORY_AGING_REPORT, 'report': 'inventory_aging_report',
                                                      'categories': categories})

@csrf_exempt
@login_required
def manage_users(request):
    if not permissionpage(request):
        return render(request, 'templates/permission_denied.html')
    headers = ['User Name', 'Name', 'Email', 'Member of Groups']
    return render(request, 'templates/manage_users.html',{'headers': headers})

@csrf_exempt
@login_required
@get_admin_user
def configurations(request, user=''):
    display_none = 'display: block;'
    if not permissionpage(request):
        return render(request, 'templates/permission_denied.html')
    fifo_switch = get_misc_value('fifo_switch', user.id)
    batch_switch = get_misc_value('batch_switch', user.id)
    send_message = get_misc_value('send_message', user.id)
    use_imei = get_misc_value('use_imei', user.id)
    back_order = get_misc_value('back_order', user.id)
    show_image = get_misc_value('show_image', user.id)
    online_percentage = get_misc_value('online_percentage', user.id)
    pallet_switch = get_misc_value('pallet_switch', user.id)
    production_switch = get_misc_value('production_switch', user.id)
    mail_alerts = get_misc_value('mail_alerts', user.id)
    pos_switch = get_misc_value('pos_switch', user.id)
    auto_po_switch = get_misc_value('auto_po_switch', user.id)
    no_stock_switch = get_misc_value('no_stock_switch', user.id)
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    all_groups = str(','.join(all_groups))
    all_stages = ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True)
    all_stages = str(','.join(all_stages))
    picklist_display_address = 'false'

    if mail_alerts == 'false':
        mail_alerts = 0
    if production_switch == 'false':
        display_none = 'display:none;'
    mail_inputs = []

    for key, val in MAIL_REPORTS_DATA.iteritems():
        temp_value = get_misc_value(val, user.id)
        if temp_value == 'true':
            mail_inputs.append(val)

    if online_percentage == "false":
        online_percentage = 0
    user_profile = UserProfile.objects.filter(user_id=user.id)
    prefix = ''
    if user_profile:
        prefix = user_profile[0].prefix

    enabled_reports = MiscDetail.objects.filter(misc_type__contains='report', misc_value='true', user=request.user.id)
    reports_data = []
    for reports in enabled_reports:
        reports_data.append(str(reports.misc_type.replace('report_', '')))

    mail_listing = MiscDetail.objects.filter(misc_type='email', user=request.user.id)
    email = ''
    if mail_listing:
        email = mail_listing[0].misc_value

    report_frequency = MiscDetail.objects.filter(misc_type='report_frequency', user=request.user.id)
    report_freq = ''
    if report_frequency:
         report_freq = report_frequency[0].misc_value

    report_data_range = MiscDetail.objects.filter(misc_type='report_data_range', user=request.user.id)
    data_range = ''
    if report_data_range:
        data_range = report_data_range[0].misc_value
    display_pos = ''
    if pos_switch == 'false':
        display_pos = 'display:none'

    picklist_display_address = MiscDetail.objects.filter(misc_type='report_data_range', user=request.user.id)
    if picklist_display_address:
        picklist_display_address = picklist_display_address[0].misc_value

    return render(request, 'templates/configurations.html', {'batch_switch': batch_switch, 'fifo_switch': fifo_switch, 'pos_switch': pos_switch,
                                                             'send_message': send_message, 'use_imei': use_imei, 'back_order': back_order,
                                                             'show_image': show_image, 'online_percentage': online_percentage,
                                                             'prefix': prefix, 'pallet_switch': pallet_switch,
                                                             'production_switch': production_switch, 'mail_alerts': mail_alerts,
                                                             'mail_inputs': mail_inputs, 'mail_options': MAIL_REPORTS_DATA,
                                                             'mail_reports': MAIL_REPORTS, 'data_range': data_range,
                                                             'report_freq': report_freq, 'email': email, 'mail_listing': mail_listing,
                                                             'reports_data': reports_data, 'display_none': display_none, 'is_config': 'true',
                                                             'all_groups': all_groups, 'display_pos': display_pos,
                                                             'auto_po_switch': auto_po_switch, 'no_stock_switch': no_stock_switch,
                                                             'all_stages': all_stages, 'picklist_display_address':picklist_display_address })

#tax_inclusive_pos = get_misc_value('tax_inclusive', user.id)

@csrf_exempt
@login_required
@get_admin_user
def confirm_move_inventory(request, user=''):
    for key, value in request.GET.iteritems():
        data1 = CycleCount.objects.get(id=key, sku__user = user.id)
        data1.status = 'completed'
        data1.save()
        data2 = CycleCount.objects.get(id=value, sku__user = user.id)
        data2.status = 'completed'
        data2.save()
        dat = InventoryAdjustment.objects.get(cycle_id=key, cycle__sku__user = user.id)
        dat.reason = 'Moved Successfully'
        dat.save()

    return HttpResponse('Moved Successfully')

@csrf_exempt
@login_required
def add_move_inventory(request):
    return render(request, 'templates/toggle/add_move_inventory.html', {'move_inventory_fields': MOVE_INVENTORY_FIELDS})

@csrf_exempt
@login_required
def add_inventory_adjust(request):
    return render(request, 'templates/toggle/add_inventory_adjust.html', {'inventory_adjust_fields': ADJUST_INVENTORY_FIELDS})

@csrf_exempt
@login_required
@get_admin_user
def add_inventory(request, user=''):
    headers = ['SKU *', 'Quantity *', 'Current Stock', 'Location *']
    profile = UserProfile.objects.get(user_id=user.id)
    return render(request, 'templates/toggle/add_inventory.html', {'headers': headers, 'company_name': profile.company_name,
                           'address': profile.address})

@csrf_exempt
@login_required
@get_admin_user
def get_id_cycle(request, user=''):
    cycle_data = CycleCount.objects.exclude(status__in=['checked']).filter(cycle=request.GET['data_id'], sku__user = user.id)
    return render(request, 'templates/toggle/cycle_form.html', {'data': cycle_data, 'cycle_id': cycle_data[0].cycle})


@csrf_exempt
@login_required
@get_admin_user
def submit_cycle_count(request, user=''):
    for data_id, count in request.GET.iteritems():
        if not count:
            continue
        data = CycleCount.objects.get(id = data_id, sku__user = user.id)
        data.seen_quantity = count
        data.status = 'checked'
        data.save()
    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def confirm_inventory_adjustment(request, user=''):
    for key, value in request.GET.iteritems():
        data = CycleCount.objects.get(id = key, sku__user = user.id)
        data.status = 'completed'
        data.save()
        dat = InventoryAdjustment.objects.get(cycle_id = key, cycle__sku__user = user.id)
        dat.reason = value
        dat.save()
        location_count = StockDetail.objects.filter(location_id=dat.cycle.location_id, sku_id=dat.cycle.sku_id, quantity__gt=0,
                                                    sku__user = user.id)
        difference = data.seen_quantity - data.quantity
        for count in location_count:
            if difference > 0:
                count.quantity += difference
                count.save()
                break
            elif difference < 0:
                if (count.quantity + difference) >= 0:
                    count.quantity += difference
                    count.save()
                    break
                elif (count.quantity + difference) <= 0:
                    difference -= count.quantity
                    count.quantity = 0
                    count.save()

                if difference == 0:
                    break

    return HttpResponse('Updated Successfully')

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
                po = PurchaseOrder.objects.get(id=myDict['id'][i])
                setattr(po, 'status', 'location-assigned')
                po.save()

    if status:
        return HttpResponse(status)
    return HttpResponse('Updated Successfully')

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
    if not purchase_orders:
        rw_orders = RWPurchase.objects.filter(purchase_order__order_id=supplier_id, rwo__vendor__user = user.id).\
                                       exclude(purchase_order__status__in=['', 'confirmed-putaway', 'stock-transfer']).\
                                       values_list('purchase_order_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=rw_orders)
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
                data[location.id] = (order_data['wms_code'], location.location.location, int(location.quantity), int(location.quantity),
                                     location.location.fill_sequence, location.id, pallet_number)

    if temp == 'true' and all_data:
        for key, value in all_data.iteritems():
            data[key[0]] = (value[1], key[1], value[0], value[0], value[3], '', key[0], value[4])

    data_list = data.values()
    data_list.sort(key=lambda x: x[4])
    po_number = '%s%s_%s' % (order.prefix, str(order.po_date).split(' ')[0].replace('-', ''), order.order_id)
    return render(request, 'templates/toggle/view_putaway.html', {'headers': headers, 'data': data_list, 'po_number': po_number,
                                                                  'order_id': order_id,'user': request.user})


@csrf_exempt
@login_required
@get_admin_user
def get_order_detail_data(request, user=''):
    data = ''
    order_code = ''
    picked_orders = []
    order_data = []
    search = {'status': 'dispatched', 'order__user': user.id}
    order_id = request.GET['order_id']
    for key,value in request.GET.iteritems():
        if key=='order_id' and value:
            temp = re.findall('\D+',order_id)
            if len(temp)>0:
                order_code = temp[0]
                search['order__order_code'] = order_code
            order_id = order_id.replace(order_code,'')
            search['order__order_id'] = order_id
        elif key == 'order_date' and value:
            to_date = value.split('/')
            search['creation_date'] = datetime.date(int(to_date[2]), int(to_date[0]), int(to_date[1]))
        elif key == 'customer_id' and value:
            search['order__customer_id'] = value
    if 'order__order_id' in search or 'order__customer_id' in search or 'creation_date' in search:
        picked_orders = Picklist.objects.filter(**search).values('order_id').distinct()
    for picked in picked_orders:
        order_detail = OrderDetail.objects.filter(id=picked['order_id'])
        for order in order_detail:
            if data == '':
                data = str(order.id) + ',' + str(order.order_code) + str(order.order_id) + ',' + str(order.sku.sku_code) + ',' + str(order.customer_id) + ',' + str(order.quantity)
            else:
                data += '$' + str(order.id) + ',' + str(order.order_code) + str(order.order_id) + ',' + str(order.sku.sku_code) + ',' + str(order.customer_id) + ',' + str(order.quantity)

    if not data:
        data = 'Orders are not in dispatched state'
    return HttpResponse(data)


@csrf_exempt
@login_required
@get_admin_user
def quality_check_data(request, user=''):
    headers = ('WMS CODE', 'Location', 'Quantity', 'Accepted Quantity', 'Rejected Quantity', 'Reason')
    data = {}
    order_id = request.GET['order_id']
    purchase_orders = PurchaseOrder.objects.filter(order_id=order_id, open_po__sku__user = user.id)
    if not purchase_orders:
        purchase_orders = []
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['confirmed-putaway', 'stock-transfer']).\
                                                filter(open_st__sku__user=user.id).values_list('po_id', flat=True)
        rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['confirmed-putaway', 'stock-transfer']).\
                                                filter(rwo__vendor__user=user.id).values_list('purchase_order_id', flat=True)
        stock_results = list(chain(stock_results, rw_results))
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
            data[qc_data.id] = {'id': qc_data.id, 'wms_code': purchase_data['wms_code'],
                                'location': qc_data.po_location.location.location, 'quantity': qc_data.putaway_quantity,
                                'accepted_quantity': qc_data.accepted_quantity, 'rejected_quantity': qc_data.rejected_quantity}

    return render(request, 'templates/quality_table.html', {'headers': headers, 'data': data, 'po_reference': po_reference,
                             'order_id': order_id})

@csrf_exempt
@login_required
@get_admin_user
def shipment_info_data(request, user=''):
    headers = ('Order ID', 'SKU Code', 'Shipping Quantity', 'Shipment Reference', 'Pack Reference', 'Status')
    data = {}
    customer_id = request.GET['customer_id']
    shipment_number = request.GET['shipment_number']
    shipment_orders = ShipmentInfo.objects.filter(order__customer_id=customer_id, order_shipment__shipment_number=shipment_number,
                                                  order_shipment__user=user.id)
    for orders in shipment_orders:
        ship_status = copy.deepcopy(SHIPMENT_STATUS)
        status = 'Dispatched'
        tracking = ShipmentTracking.objects.filter(shipment_id=orders.id, shipment__order__user=user.id).order_by('-creation_date').\
                                            values_list('ship_status', flat=True)
        if tracking:
            status = tracking[0]
            if status == 'Delivered':
                continue
        ship_status =  ship_status[ship_status.index(status):]
        data[orders.id] = (orders.order.order_id, orders.order.sku.sku_code, orders.shipping_quantity,
                           orders.order_packaging.order_shipment.shipment_reference, orders.order_packaging.package_reference, ship_status,
                           status)

    return render(request, 'templates/toggle/shipment_info_data.html', {'headers': headers, 'data': data, 'customer_id': customer_id,
                                                                        'ship_status': SHIPMENT_STATUS})

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
@get_admin_user
def update_receive_po(request, user=''):
    data_id = request.GET['data_id']
    record = PurchaseOrder.objects.get(id=data_id, open_po__sku__user = user.id)
    data = ((('WMS CODE', ('wms_code', record.po_id.sku_id.wms_code)), ('Order Quantity', ('order_quantity', int(record.po_id.order_quantity)))), (('Received Quantity', ('received_quantity', record.received_quantity)), ('Price', ('price', int(record.po_id.price)))))
    return render(request, 'templates/toggle/po_received.html', {'data': data, 'record_id': record.id})

@csrf_exempt
@login_required
@get_admin_user
def update_receiving(request, user=''):
    data_id = request.GET['data-id']
    po = PurchaseOrder.objects.get(id=data_id, open_po__sku__user = user.id)
    total_count = po.received_quantity + int(request.GET['received_quantity'])
    if total_count > po.po_id.order_quantity:
        return HttpResponse('Given quantity is greater than Order quantity')
    setattr(po, 'received_quantity', int(total_count))
    po.save()
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
    purchase_orders = PurchaseOrder.objects.filter(order_id=order_id, open_po__sku__user = user.id,
                                           received_quantity__lt=F('open_po__order_quantity')).exclude(status='location-assigned')
    if not purchase_orders:
        st_orders = STPurchaseOrder.objects.filter(po__order_id=order_id, open_st__sku__user = user.id).\
                                exclude(po__status__in=['location-assigned', 'stock-transfer']).values_list('po_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=st_orders)
    if not purchase_orders:
        rw_orders = RWPurchase.objects.filter(purchase_order__order_id=order_id, rwo__vendor__user=user.id).\
                                       exclude(purchase_order__status__in=['location-assigned', 'stock-transfer']).\
                                       values_list('purchase_order_id', flat=True)
        purchase_orders = PurchaseOrder.objects.filter(id__in=rw_orders)
    for order in purchase_orders:
        order_data = get_purchase_order_data(order)
        po_quantity = int(order_data['order_quantity']) - int(order.received_quantity)
        if po_quantity > 0:
            data[order.id] = {'wms_code': order_data['wms_code'],'po_quantity': int(order_data['order_quantity'])-int(order.received_quantity),
                              'name': str(order.order_id) + '-' + str(order_data['wms_code']), 'value': str(int(order.saved_quantity)),
                              'price': order_data['price'], 'temp_wms': order_data['temp_wms'] }

    return render(request, 'templates/toggle/view_confirmed_po.html', {'headers': headers, 'data': data, 'po_id': order_id,
                           'supplier_id': order_data['supplier_id'], 'use_imei': use_imei, 'temp': temp})


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
def delete_inventory(request, user=''):
    for key, value in request.GET.iteritems():
        inventory = CycleCount.objects.get(id=key).delete()
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def delete_po_group(request, user=''):
    for key, value in request.GET.iteritems():
        purchase_order = OpenPO.objects.filter(Q(supplier_id=key, status='Manual') | Q(supplier_id=key, status='Automated'),
                                                 sku__user = user.id).delete()

    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def generated_po_data(request, user=''):
    send_message = 'true'
    data = MiscDetail.objects.filter(user = user.id, misc_type='send_message')
    if data:
        send_message = data[0].misc_value

    generated_id = request.GET['data_id']
    record = OpenPO.objects.filter(Q(supplier_id=generated_id, status='Manual') | Q(supplier_id=generated_id, status='Automated'),
                                     sku__user = user.id)
    '''for rec in record:
        supplier_mapping = SKUSupplier.objects.filter(supplier=rec.supplier, sku=rec.sku)
        if supplier_mapping:
            if not rec.supplier_code:
                rec.supplier_code = supplier_mapping[0].supplier_code'''

    data = ((('Supplier ID', ('supplier_id', record[0].supplier_id), 11), ('PO Name', ('po_name', record[0].po_name), 11), ('Ship To', ('ship_to', ''), '')),)
    return render(request, 'templates/toggle/update_po.html', {'send_message': send_message, 'data': data, 'record_id': record[0].id,
                                                               'records': record, 'po_fields1': RAISE_PO_FIELDS1})


@csrf_exempt
@login_required
@get_admin_user
def stock_summary_data(request, user=''):
    wms_code = request.GET['wms_code']
    stock_data = StockDetail.objects.exclude(receipt_number=0).filter(sku_id__wms_code=wms_code, quantity__gt=0, sku__user = user.id)
    zones_data = {}
    for stock in stock_data:
        res_qty = PicklistLocation.objects.filter(stock_id=stock.id, status=1, picklist__order__user=user.id).\
                                           aggregate(Sum('reserved'))['reserved__sum']
        if not res_qty:
            res_qty = 0
        zones_data.setdefault(stock.location.zone.zone, {})
        zones_data[stock.location.zone.zone].setdefault(stock.location.location, [0, res_qty])
        zones_data[stock.location.zone.zone][stock.location.location][0] += stock.quantity

    headers = ('Zone', 'Location', 'Total Quantity', 'Reserved Quantity')
    html_data = create_table_data(headers, zones_data)
    return HttpResponse(html_data)

@csrf_exempt
def get_cycle_confirmed(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['cycle', 'creation_date']
    if search_term:
        cycle_data = CycleCount.objects.filter(Q(cycle__icontains=search_term) | Q(creation_date__startswith=search_term),
                                               sku__user=user.id,status=1).order_by(lis[col_num]).values('cycle').distinct()
    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        cycle_data = CycleCount.objects.filter(status='1',sku__user=user.id).order_by(order_data).values('cycle').distinct()
    else:
        cycle_data = CycleCount.objects.filter(status='1',sku__user=user.id).values('cycle').distinct()
    data = []

    for count in cycle_data:
        record = CycleCount.objects.filter(cycle=count['cycle'],sku__user=user.id)
        data.append(record[0])

    temp_data['recordsTotal'] = len(data)
    temp_data['recordsFiltered'] = len(data)

    for item in data[start_index:stop_index]:
        temp_data['aaData'].append(OrderedDict(( ('Cycle Count ID', item.cycle), ('Date', get_local_date(request.user, item.creation_date)),
                                                 ('DT_RowClass', 'results'), ('DT_RowId', item.cycle) )))

@csrf_exempt
def get_batch_data(start_index, stop_index, temp_data, search_term, order_term, col_num, marketplace, col_1, col_2, col_3, request, user):
    lis = ['id', 'sku__sku_code', 'title', 'total']
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}
    if marketplace:
        data_dict['marketplace__in'] = marketplace.split(',')
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    if search_term:
        mapping_results = OrderDetail.objects.values('sku__sku_code', 'title', 'sku_code').distinct().annotate(total=Sum('quantity')).\
                                              filter(Q(sku__sku_code__icontains=search_term) | Q(title__icontains=search_term) |
                                                     Q(total__icontains=search_term), **data_dict).order_by(order_data)
    else:
        mapping_results = OrderDetail.objects.values('sku__sku_code', 'title', 'sku_code').distinct().annotate(total=Sum('quantity')).\
                                              filter(**data_dict).order_by(order_data)

    search_params = {}
    if col_1:
        search_params['sku__sku_code__iexact'] = col_1
    if col_2:
        search_params['title__icontains'] = col_2
    if col_3:
        search_params['total'] = col_3
    if search_params:
        search_params.update(data_dict)
        mapping_results = OrderDetail.objects.values('sku__sku_code', 'title', 'sku_code').distinct().annotate(total=Sum('quantity')).\
                                              filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = mapping_results.count()
    temp_data['recordsFiltered'] = mapping_results.count()

    for dat in mapping_results[start_index:stop_index]:

        sku_code = dat['sku__sku_code']
        if sku_code == 'TEMP':
            sku_code = dat['sku_code']
        check_values = dat['sku__sku_code'] + '<>' + sku_code
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (check_values, dat['total'])
        temp_data['aaData'].append(OrderedDict(( ('', checkbox), (' SKU Code', sku_code), ('Title', dat['title']), ('Total Quantity',
                                   dat['total']), ('DT_RowClass', 'results') )))

@csrf_exempt
def get_po_suggestions(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, request, user):
    lis = ['supplier_id', 'supplier_id', 'supplier__name', 'total']

    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    if search_term:
        results = OpenPO.objects.exclude(status = 0).filter( Q( supplier__id__icontains = search_term ) | Q( order_quantity__icontains = search_term ) | Q( price__icontains = search_term) | Q(sku__wms_code__icontains = search_term) | Q( status__icontains = search_term ),sku__user=user.id).values('supplier_id', 'supplier__name').distinct().annotate(total=Sum('order_quantity')).order_by(order_data)

    elif order_term:
        results = OpenPO.objects.exclude(status = 0).filter(sku__user=user.id).values('supplier_id', 'supplier__name').\
                                 distinct().annotate(total=Sum('order_quantity')).order_by(order_data)
    else:
        results = OpenPO.objects.exclude(status = 0).filter(sku__user=user.id).values('supplier_id', 'supplier__name').\
                                 distinct().annotate(total=Sum('order_quantity')).order_by('supplier_id')

    search_params = {}
    if col_2:
        search_params["supplier__id__icontains"] = col_2
    if col_3:
        search_params["supplier__name__icontains"] = col_3
    if col_4:
        open_po_ids = OpenPO.objects.exclude(status=0).filter(sku__user=user.id).values('supplier_id').distinct().\
                                            annotate(total=Sum('order_quantity')).filter(total=col_4).values_list('supplier_id', flat=True)
        search_params["supplier_id__in"] = open_po_ids
    if search_params:
        results = OpenPO.objects.exclude(status = 0).filter(**search_params).values('supplier_id', 'supplier__name').distinct().\
                                 annotate(total=Sum('order_quantity')).order_by(order_data)

    temp_data['recordsTotal'] = results.count()
    temp_data['recordsFiltered'] = results.count()

    for result in results:
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (result['supplier_id'], result['supplier__name'])
        temp_data['aaData'].append({ '': checkbox, ' Supplier ID': result['supplier_id'], 'Supplier Name': result['supplier__name'],
                                     'Total Quantity': result['total'],'DT_RowClass': 'results'})

@csrf_exempt
def generate_grn(start_index, stop_index, temp_data, search_term, user):
    supplier_data = {}
    if search_term:
        results = PurchaseOrder.objects.filter(open_po__supplier__name=search_term,open_po__sku__user=user.id)
    else:
        suppliers = PurchaseOrder.objects.filter(open_po__sku__user=user.id).values('open_po_id__supplier_id_id').distinct()
        for supplier in suppliers:
            results = PurchaseOrder.objects.filter(open_po__supplier_id = supplier['open_po_id__supplier_id'],open_po__sku__user=user.id)
            for result in results:
                if result.received_quantity != result.po_id.order_quantity:
                    break
                else:
                    supplier_data[result.po_id.supplier_id] = (result.po_id.supplier_id.name, result.order_id)

    for supplier_id, name in supplier_data.iteritems():
        temp_data['aaData'].append({'DT_RowId': supplier_id, 'Supplier ID': supplier_id, 'Supplier Name ': name[0], 'Order ID': name[1]})

@csrf_exempt
def get_supplier_mapping(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, col_5, request, user):
    order_data = SKU_SUPPLIER_MAPPING.values()[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        mapping_results = SKUSupplier.objects.filter( Q(supplier_id = search_term) | Q(preference__icontains = search_term) | Q(moq__icontains = search_term) | Q(sku__wms_code__icontains = search_term) | Q(supplier_code__icontains = search_term),sku__user=user.id ).order_by(order_data)

    else:
        mapping_results = SKUSupplier.objects.filter(sku__user = user.id).order_by(order_data)
    search_params = {}
    if col_1:
        search_params['supplier__id__icontains'] = col_1
    if col_2:
        search_params['sku__wms_code__icontains'] = col_2
    if col_3:
        search_params['supplier_code__icontains'] = col_3
    if col_4:
        search_params['preference__icontains'] = col_4
    if col_5:
        search_params['moq__icontains'] = col_5
    if search_params:
        search_params["sku__user"] = user.id
        mapping_results = SKUSupplier.objects.filter(**search_params).order_by(order_data)
    temp_data['recordsTotal'] = len(mapping_results)
    temp_data['recordsFiltered'] = len(mapping_results)

    for result in mapping_results[start_index : stop_index]:
        temp_data['aaData'].append(OrderedDict(( ('Supplier ID ', result.supplier_id), ('WMS Code', result.sku.wms_code),
                                                 ('Supplier Code', result.supplier_code), ('MOQ', result.moq), ('Priority', result.preference),
                                                 ('DT_RowClass', 'results'), ('DT_RowId', result.id) )))

@csrf_exempt
def get_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    supplier_data = {}
    lis = [' PO Number', 'Order Date', 'Supplier ID', 'Supplier Name', 'Order Type']
    if search_term:
        results = PurchaseOrder.objects.filter(Q(open_po__supplier__name__icontains=search_term) | Q(open_po__supplier__id__icontains=search_term) | Q(order_id__icontains=search_term) | Q(creation_date__regex=search_term), open_po__sku__user = user.id).exclude(status__in=['', 'confirmed-putaway']).values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['','confirmed-putaway', 'stock-transfer']).\
                                                filter(Q(open_st__warehouse__id__icontains = search_term) |
                                                       Q(open_st__warehouse__username__icontains = search_term) |
                                                       Q(po__order_id__icontains = search_term) | Q(po__creation_date__regex=search_term),
                                                       open_st__sku__user=user.id).\
                                                 values_list('po__order_id', flat=True).distinct()
        rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['','confirmed-putaway', 'stock-transfer']).\
                                                filter(Q(rwo__vendor__id__icontains = search_term) |
                                                       Q(rwo__vendor__name__icontains = search_term) |
                                                       Q(purchase_order__order_id__icontains = search_term) |
                                                       Q(purchase_order__creation_date__regex=search_term),
                                                       rwo__vendor__user=user.id).\
                                                 values_list('purchase_order__order_id', flat=True).distinct()
        results = list(chain(results, stock_results, rw_results))
    elif order_term:
        results = PurchaseOrder.objects.filter(open_po__sku__user = user.id).exclude(status__in=['', 'confirmed-putaway']).values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['','confirmed-putaway', 'stock-transfer']).\
                                                filter(open_st__sku__user = user.id).values_list('po__order_id', flat=True).\
                                                values_list('po__order_id', flat=True).distinct()
        rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['','confirmed-putaway', 'stock-transfer']).\
                                        filter(rwo__vendor__user = user.id).values_list('purchase_order__order_id', flat=True)
        results = list(chain(results, stock_results, rw_results))
    else:
        results = PurchaseOrder.objects.filter(open_po__sku__user = user.id).exclude(status__in=['', 'confirmed-putaway']).values('order_id').distinct()
    data = []
    temp = []
    for result in results:
        suppliers = PurchaseOrder.objects.filter(order_id=result, open_po__sku__user = user.id).exclude(status__in=['', 'confirmed-putaway'])
        if not suppliers:
            st_order_ids = STPurchaseOrder.objects.filter(po__order_id=result, open_st__sku__user = user.id).values_list('po_id', flat=True)
            suppliers = PurchaseOrder.objects.filter(id__in=st_order_ids)
        if not suppliers:
            rw_ids = RWPurchase.objects.filter(purchase_order__order_id=result, rwo__vendor__user = user.id).\
                                              values_list('purchase_order_id', flat=True)
            suppliers = PurchaseOrder.objects.filter(id__in=rw_ids)
        for supplier in suppliers:
            po_loc = POLocation.objects.filter(purchase_order_id=supplier.id, status=1, location__zone__user = user.id)
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
                                    ' Order ID': supplier.order_id, 'Order Date': str(supplier.creation_date).split('+')[0],
                                    'DT_RowClass': 'results', ' PO Number': po_reference,
                                    'DT_RowAttr': {'data-id': supplier.order_id}})

    order_data = lis[col_num]
    if order_term == 'asc':
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(order_data))
    else:
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(order_data), reverse=True)
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]

@csrf_exempt
def get_quality_check_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['Purchase Order ID', 'Supplier ID', 'Supplier Name', 'Order Type', 'Total Quantity']
    all_data = OrderedDict()
    if search_term:
        results = QualityCheck.objects.filter(Q(purchase_order__order_id__icontains=search_term, status='qc_pending') |
                                              Q(purchase_order__open_po__supplier__id__icontains=search_term, status='qc_pending') |
                                              Q(purchase_order__open_po__supplier__name__icontains=search_term, status='qc_pending'),
                                              purchase_order__open_po__sku__user = user.id, putaway_quantity__gt=0)
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['confirmed-putaway', 'stock-transfer']).\
                                                filter(Q(open_st__warehouse__username__icontains = search_term) |
                                                       Q(po__order_id__icontains = search_term ), open_st__sku__user=user.id).\
                                                 values_list('po_id', flat=True)
        rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['confirmed-putaway', 'stock-transfer']).\
                                        filter(Q(rwo__vendor__name__icontains = search_term) | Q(rwo__vendor__id__icontains = search_term) |
                                               Q(purchase_order__order_id__icontains = search_term ), rwo__vendor__user=user.id).\
                                        values_list('purchase_order_id', flat=True)
        stock_results = list(chain(stock_results, rw_results))
        qc_results = QualityCheck.objects.filter(purchase_order_id__in=stock_results, status='qc_pending',
                                       po_location__location__zone__user = user.id, putaway_quantity__gt=0).order_by(order_data)

        results = list(chain(results, qc_results))
    else:
        results = QualityCheck.objects.filter(status='qc_pending', po_location__location__zone__user = user.id, putaway_quantity__gt=0)

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
def get_confirmed_po(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, col_5, request, user):
    lis = ['PO Number', 'Order Date', 'Supplier ID', 'Supplier Name', 'Order Type', 'Receive Status']
    data_list = []
    data = []
    supplier_data = {}
    col_num1 = 0
    if search_term:
        results = PurchaseOrder.objects.filter(Q(open_po__supplier_id__id = search_term) | Q(open_po__supplier__name__icontains = search_term)
                                               |Q( order_id__icontains = search_term ) | Q(creation_date__regex=search_term),
                                              open_po__sku__user=user.id, received_quantity__lt=F('open_po__order_quantity')).\
                                        exclude(status__in=['location-assigned','confirmed-putaway']).\
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
        results = PurchaseOrder.objects.filter(open_po__sku__user = user.id, received_quantity__lt=F('open_po__order_quantity')).\
                                        exclude(status__in=['location-assigned', 'confirmed-putaway'],
                                              open_po=None).values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                                filter(open_st__sku__user = user.id).values_list('po__order_id', flat=True).distinct()
        rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                        filter(rwo__vendor__user = user.id).values_list('purchase_order__order_id', flat=True).distinct()
        results = list(set(list(chain(results, stock_results, rw_results))))

    search_params = {}
    search_params1 = {}
    search_params2 = {}
    if col_1:
        cols = re.findall('\d+', col_1)
        string = re.findall('\D+', col_1)
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
            if string:
                search_params['prefix__icontains'] = string[0]
        else:
            col_val = re.findall('\d+', col_1)[0]
            po_ids = PurchaseOrder.objects.filter(Q(order_id__icontains = col_val) | Q(creation_date__regex = col_val),
                                                  open_po__sku__user = user.id, received_quantity__lt=F('open_po__order_quantity')).\
                                           exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                           values_list('id', flat=True)
            stock_results = STPurchaseOrder.objects.exclude(po__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                                    filter(Q(po__order_id__icontains = col_val) | Q(creation_date__regex = col_val),
                                                           open_st__sku__user=user.id, po__open_po= None).\
                                                    values_list('po_id', flat=True).distinct()
            rw_results = RWPurchase.objects.exclude(purchase_order__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                            filter(Q(po__order_id__icontains = col_val) | Q(creation_date__regex = col_val),
                                                   rwo__vendor__user = user.id).values_list('purchase_order_id', flat=True).distinct()
            search_params['id__in'] = list(chain(po_ids, stock_results, rw_results))
    if col_2:
        search_params['creation_date__regex']  = col_2
    if col_3:
        search_params['open_po__supplier__id__icontains'] = col_3
        search_params1['open_st__warehouse__id__icontains'] = col_3
        search_params2['rwo__vendor__id__icontains'] = col_3
    if col_4:
        search_params['rwo__vendor__name__icontains'] = col_4
        search_params1['open_st__wareihouse__username__icontains'] = col_4
        search_params2['rwo__vendor__name__icontains'] = col_4
    if search_params:
        search_params['open_po__sku__user'] = user.id
        search_params1['open_st__sku__user'] = user.id
        search_params['received_quantity__lt'] = F('open_po__order_quantity')
        results = PurchaseOrder.objects.filter(**search_params).exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                        values_list('order_id', flat=True).distinct()
        stock_results = STPurchaseOrder.objects.exclude(po__status__in=['location-assigned','confirmed-putaway', 'stock-transfer']).\
                                                filter(**search_params1).values_list('po__order_id', flat=True).distinct()
        results = list(chain(results, stock_results))


    for result in results:
        suppliers = PurchaseOrder.objects.filter(order_id=result, open_po__sku__user = user.id,
                           received_quantity__lt=F('open_po__order_quantity')).exclude(status__in=['location-assigned', 'confirmed-putaway'])
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
        quantity = "<input type='text' name='quantity' value='%s' class='smallbox numvalid'><input type='hidden' name='hide_quantity' value='%s'>" % (int(data.quantity), int(data.quantity))
        temp_data['aaData'].append({'': checkbox, 'Return ID': data.returns.return_id,
                                    'Return Date': get_local_date(user, data.returns.return_date), 'WMS Code': data.returns.sku.wms_code,
                                    'Product Description': data.returns.sku.sku_desc, ' Zone': zone, 'Location': location,
                                    'Quantity': quantity, 'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.id}})

@csrf_exempt
def get_stock_results(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, col_5, excel, request, user):
    lis = ['sku__wms_code', 'sku__sku_desc', 'sku__sku_category', 'total']
    exclude_dict = {'location__zone__zone': 'DAMAGED_ZONE'}
    extra_headers = []
    if get_misc_value('production_switch', user.id) == 'true':
        extra_headers =  list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
        lis = lis + ['id'] * len(extra_headers)
    col_num = col_num - 1
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data

    search_params = {}
    search_params1 = {}
    if col_2:
        search_params['sku__wms_code__icontains'] = col_2
        search_params1['product_code__wms_code__icontains'] = col_2
    if col_3:
        search_params['sku__sku_desc__icontains'] = col_3
        search_params1['product_code__sku_desc__icontains'] = col_3
    if col_4:
        search_params['sku__sku_category__icontains'] = col_4
        search_params1['product_code__sku_category__icontains'] = col_4
    if col_5:
        search_params['total__icontains'] = col_5


    job_order = JobOrder.objects.filter(product_code__user=user.id, status__in=['grn-generated', 'pick_confirm'])
    if search_term:
        master_data = StockDetail.objects.exclude(**exclude_dict).values_list('sku__wms_code', 'sku__sku_desc', 'sku__sku_category').distinct().\
                                          annotate(total=Sum('quantity')).filter(Q(sku_id__wms_code__icontains=search_term) |
                                                  Q(sku_id__sku_code__icontains=search_term) |
                                                  Q(sku_id__sku_desc__icontains=search_term) | Q(sku_id__sku_category__icontains=search_term) |                                                   Q(total__icontains=search_term),
                                                  sku__user = user.id, quantity__gt=0).filter(**search_params).order_by(order_data)
        wms_codes = map(lambda d: d[0], master_data)
        master_data1 = job_order.exclude(product_code__wms_code__in=wms_codes).filter(Q(product_code__wms_code__icontains=search_term) |
                                      Q(product_code__sku_desc__icontains=search_term) | Q(product_code__sku_category__icontains=search_term),
                                      **search_params1).values_list('product_code__wms_code',
                                         'product_code__sku_desc', 'product_code__sku_category')
        master_data = list(chain(master_data, master_data1))

    else:
        master_data = StockDetail.objects.exclude(**exclude_dict).values_list('sku__wms_code', 'sku__sku_desc', 'sku__sku_category').\
                                          distinct().annotate(total=Sum('quantity')).filter(sku__user=user.id, quantity__gt=0,
                                          **search_params).order_by(order_data)
        wms_codes = map(lambda d: d[0], master_data)
        master_data1 = job_order.exclude(product_code__wms_code__in=wms_codes).filter(**search_params1).\
                                 values_list('product_code__wms_code', 'product_code__sku_desc', 'product_code__sku_category')
        master_data = list(chain(master_data, master_data1))

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for ind, data in enumerate(master_data[start_index:stop_index]):
        total = data[3] if len(data) > 3 else 0
        temp_data['aaData'].append(OrderedDict(( ('  WMS Code', data[0]), ('Product Description', data[1]),
                                                 ('SKU Category', data[2]), ('Quantity', total),
                                                 ('DT_RowId', data[0]) )))
        if excel == 'true':
            damaged = StockDetail.objects.filter(sku__wms_code=data[0], sku__user=user.id, **exclude_dict).aggregate(Sum('quantity'))['quantity__sum']
            if not damaged:
                damaged = 0
            temp_data['aaData'][ind].update({'Damaged Quantity': damaged})
        if extra_headers:
            job_ids = job_order.filter(product_code__wms_code=data[0]).values_list('id', flat=True)
            status_track = StatusTracking.objects.filter(status_type='JO', status_id__in=job_ids,status_value__in=extra_headers).\
                                                  values('status_value').distinct().annotate(total=Sum('quantity'))
            tracking = dict(zip(map(lambda d: d.get('status_value', ''), status_track), map(lambda d: d.get('total', '0'), status_track)))
            for head in extra_headers:
                temp_data['aaData'][ind].update({head: tracking.get(head, 0) })


@csrf_exempt
def get_order_results(start_index, stop_index, temp_data, search_term, order_term, col_num, marketplace, col_1, col_2, col_3, col_4, col_5, col_6, request, user):

    lis = ['id', 'order_id', 'sku__sku_code', 'title', 'quantity', 'shipment_date', 'marketplace']
    data_dict = {'status': 1, 'user': user.id, 'quantity__gt': 0}
    if marketplace:
        marketplace = marketplace.split(',')
        data_dict['marketplace__in'] = marketplace

    if search_term:
        master_data = OrderDetail.objects.filter( Q(sku__sku_code__icontains = search_term, status=1) | Q(order_id__icontains = search_term, status=1) | Q(title__icontains = search_term, status=1) | Q(quantity__icontains = search_term, status=1),user=user.id, quantity__gt=0)

    elif order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = OrderDetail.objects.filter(**data_dict).order_by(order_data)
    else:
        master_data = OrderDetail.objects.filter(**data_dict).order_by('shipment_date')

    search_params = {}
    if col_1:
        search_params['order_id__icontains'] = col_1
    if col_2:
        search_params['sku__sku_code__iexact'] = col_2
    if col_3:
        search_params['title__icontains'] = col_3
    if col_4:
        search_params['quantity__icontains'] = col_4
    if col_5:
        search_params['shipment_date__regex'] = col_5
    if col_6:
        search_params['marketplace__icontains'] = col_6
    if search_params:
        search_params['user'] = user.id
        search_params['status'] = 1
        search_params['quantity__gt'] = 0
        if marketplace:
            search_params['marketplace__in'] = marketplace
        master_data = OrderDetail.objects.filter(**search_params)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        sku = SKUMaster.objects.get(sku_code=data.sku.sku_code,user=request.user.id)
        sku_code = sku.sku_code
        if sku_code == 'TEMP':
            sku_code = data.sku_code
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data.id, data.sku.sku_code)

        temp_data['aaData'].append(OrderedDict(( ('', checkbox), ('Order ID', data.order_id), ('SKU Code', sku_code), ('Title', data.title),
                                                 ('Product Quantity', data.quantity),  ('Shipment Date', get_local_date(request.user, data.shipment_date)), ('Marketplace', data.marketplace), ('DT_RowClass', 'results'), ('DT_RowAttr', {'data-id': data.order_id} )) ) )

@csrf_exempt
def get_stock_detail_results(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8, col_9, request, user):
    lis = ['receipt_number','receipt_date', 'sku_id__wms_code','sku_id__sku_desc','location__zone','location__location', 'quantity', 'receipt_type', 'id']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        master_data = StockDetail.objects.exclude(receipt_number=0).filter( Q(receipt_number__icontains = search_term,quantity__gt=0) | Q(sku__wms_code__icontains = search_term, quantity__gt=0) | Q(quantity__icontains=search_term, quantity__gt=0) | Q(location__zone__zone__icontains = search_term,quantity__gt=0) | Q(sku__sku_code__icontains = search_term,quantity__gt=0) | Q(sku__sku_desc__icontains = search_term,quantity__gt=0) | Q(location__location__icontains = search_term,quantity__gt=0),sku__user=user.id ).order_by(order_data)

    else:
        master_data = StockDetail.objects.exclude(receipt_number=0).filter(quantity__gt=0, sku__user=user.id).order_by(order_data)
    search_params = {}
    if col_1:
        search_params['receipt_number__iexact'] = col_1
    if col_2:
        search_params['receipt_date__regex'] = col_2
    if col_3:
        search_params['sku__wms_code__icontains'] = col_3
    if col_4:
        search_params['sku__sku_desc__icontains'] = col_4
    if col_5:
        search_params['sku__zone__zone__icontains'] = col_5
    if col_6:
        search_params['location__location__icontains'] = col_6
    if col_7:
        search_params['quantity__icontains'] = col_7
    if col_8:
        search_params['receipt_type__icontains'] = col_8
    if col_9:
        search_params['pallet_detail__pallet_code__iexact'] = col_9
    if search_params:
        search_params['sku__user'] = user.id
        search_params['quantity__gt'] = 0
        master_data = StockDetail.objects.exclude(receipt_number=0).filter(**search_params).order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        pallet_switch = get_misc_value('pallet_switch', user.id)
        if pallet_switch == 'true':
            pallet_code = ''
            if data.pallet_detail:
                pallet_code = data.pallet_detail.pallet_code
            temp_data['aaData'].append(OrderedDict(( ('Receipt ID', data.receipt_number), ('DT_RowClass', 'results'),
                                        ('Receipt Date', get_local_date(request.user, data.receipt_date)), ('SKU Code', data.sku.sku_code),
                                        ('WMS Code', data.sku.wms_code), ('Product Description', data.sku.sku_desc),
                                        ('Zone', data.location.zone.zone), ('Location', data.location.location), ('Quantity', data.quantity),
                                        ('Pallet Code', pallet_code), ('Receipt Type', data.receipt_type) )) )
        else:
            temp_data['aaData'].append(OrderedDict(( ('Receipt ID', data.receipt_number), ('DT_RowClass', 'results'),
                                        ('Receipt Date', get_local_date(request.user, data.receipt_date)), ('SKU Code', data.sku.sku_code),
                                        ('WMS Code', data.sku.wms_code), ('Product Description', data.sku.sku_desc),
                                        ('Zone', data.location.zone.zone), ('Location', data.location.location), ('Quantity', data.quantity), ('Receipt Type', data.receipt_type))))
@csrf_exempt
def get_user_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis  = ['username', 'first_name', 'email', 'id']
    group = ''
    admin_group = AdminGroups.objects.filter(user_id=user.id)
    if admin_group:
        group = admin_group[0].group
    if group:
        if search_term:
            master_data = group.user_set.filter().exclude(id=user.id)
        elif order_term:
            if order_term == 'asc':
                master_data = group.user_set.filter().exclude(id=user.id).order_by(lis[col_num])
            else:
                master_data = group.user_set.filter().exclude(id=user.id).order_by("-%s" % lis[col_num])
        else:
            master_data = group.user_set.filter().exclude(id=user.id)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        member_count = data.groups.all().exclude(name=group.name).count()
        temp_data['aaData'].append({'User Name': data.username,'DT_RowClass': 'results', 'Name': data.first_name,
                                    'Email': data.email, 'Member of Groups': member_count, 'DT_RowId': data.id})

@csrf_exempt
@login_required
@get_admin_user
def supplier_sku_mapping(request, user=''):
    suppliers = SupplierMaster.objects.filter(user=user.id).values('id')
    return render(request, 'templates/supplier_sku_mapping.html', {'add_supplier': SKU_SUPPLIER_FIELDS, 'suppliers': suppliers})

@csrf_exempt
@login_required
@get_admin_user
def customer_sku_mapping(request, user=''):
    return render(request, 'templates/customer_sku_mapping.html', {'add_customer': SKU_CUSTOMER_FIELDS})

@csrf_exempt
@login_required
def raise_issue(request):
    return render(request, 'templates/raise_issue.html',{'issue_fields': RAISE_ISSUE_FIELDS })

@csrf_exempt
@login_required
def view_issues(request):
    return render(request, 'templates/view_issues.html')

@csrf_exempt
@login_required
def move_inventory(request):
    return render(request, 'templates/move_inventory.html')

@csrf_exempt
@login_required
def cycle_count(request):
    if not permissionpage(request,'add_cyclecout'):
        return render(request, 'templates/permission_denied.html')
    return render(request, 'templates/cycle_count.html')

@csrf_exempt
@login_required
@get_admin_user
def putaway_confirmation(request, user=''):
    if not permissionpage(request,'add_polocation'):
        return render(request, 'templates/permission_denied.html')
    results = PurchaseOrder.objects.filter(open_po__sku__user=user.id).exclude(status='').values('order_id').distinct()
    temp = []
    po_count = 0
    for result in results:
        suppliers = PurchaseOrder.objects.filter(order_id=result['order_id'], open_po__sku__user=user.id).exclude(status='')
        for supplier in suppliers:
            po_loc = POLocation.objects.filter(purchase_order_id=supplier.id, status=1, location__zone__user=user.id)
            if po_loc and result['order_id'] not in temp:
                temp.append(result['order_id'])
                po_count += 1

    returns_count = ReturnsLocation.objects.filter(returns__order__user=user.id, status=1).count()
    return render(request, 'templates/putaway_confirmation.html', {'po_count': po_count, 'returns_count': returns_count})


@csrf_exempt
@login_required
def display_resolved(request):

    data_id = request.GET['data_id']
    data = Issues.objects.filter(id = data_id,status = 'Resolved')
    return render(request, 'templates/toggle/display_resolved.html', {'data': data[0], 'issue_fields': RESOLVED_ISSUE_FIELDS, 'issue_id': data_id })

@csrf_exempt
@login_required
@get_admin_user
def view_picked_orders(request, user=''):
    data_id = request.GET['data_id']
    data = get_picked_data(data_id, user.id)
    headers = PICKLIST_HEADER
    show_image = get_misc_value('show_image', user.id)
    if show_image == 'true' and 'Image' not in headers:
        headers = list(headers)
        headers.insert(0, 'Image')
    return render(request, 'templates/toggle/picked_orders.html', {'data': data, 'headers': headers, 'picklist_id': data_id,
                                                                   'show_image': show_image})


@csrf_exempt
def auto_po(wms_codes, user):
    sku_codes = SKUMaster.objects.filter(wms_code__in=wms_codes, user=user, threshold_quantity__gt=0)
    for sku in sku_codes:
        supplier_id = SKUSupplier.objects.filter(sku_id=sku.id, sku__user=user, moq__gt=0).order_by('preference')
        if not supplier_id:
            continue
        sku_stock = StockDetail.objects.filter(sku_id=sku.id, sku__user=user,quantity__gt=0).aggregate(Sum('quantity'))['quantity__sum']
        total_sku = 0
        if sku_stock:
            total_sku = sku_stock

        if total_sku > int(sku.threshold_quantity):
            return
        suggestions_data = OpenPO.objects.filter(sku_id=sku.id, sku__user=user, status__in=['Automated', 1])
        if not suggestions_data:
            po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
            po_suggestions['sku_id'] = sku.id
            if supplier_id:
                po_suggestions['supplier_id'] = supplier_id[0].supplier_id
                po_suggestions['order_quantity'] = supplier_id[0].moq
                po_suggestions['status'] = 'Automated'
                po_suggestions['price'] = supplier_id[0].price
                po = OpenPO(**po_suggestions)
                po.save()

@csrf_exempt
@login_required
@get_admin_user
def view_picklist(request, user=''):
    show_image = 'false'
    use_imei = 'false'
    data_id = request.GET['data_id']
    headers = list(PICKLIST_HEADER1)
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
    data = get_picklist_data(data_id, user.id)
    if data[0]['status'] == 'open':
        headers.insert(headers.index('WMS Code'),'Order ID')
    return render(request, 'templates/toggle/generate_picklist.html', {'data': data, 'headers': headers, 'picklist_id': data_id,
                                                                       'show_image': show_image, 'use_imei': use_imei,
                                                                       'order_status': data[0]['status'], 'user': request.user})

@get_admin_user
def print_picklist(request, user=''):
    temp = []
    title = 'Picklist ID'
    data_id = request.GET['data_id']
    data = get_picklist_data(data_id, user.id)
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
                if not record['order_id'] in temp:
                    all_data[cond][1] += record['invoice_amount']
                    temp.append(record['order_id'])
                break
        else:
            total += record['reserved_quantity']
            if not record['order_id'] in temp:
                total_price += record['invoice_amount']
                temp.append(record['order_id'])

    for key,value in all_data.iteritems():
        total += int(value[0])
        total_price += int(value[1])

    return render(request, 'templates/toggle/print_picklist.html', {'data': data, 'all_data': all_data, 'headers': PRINT_PICKLIST_HEADERS,
                                                                    'picklist_id': data_id,'total_quantity': total, 'total_price': total_price})

@get_admin_user
def print_picklist_excel(request, user=''):
    headers = copy.deepcopy(PICKLIST_EXCEL)
    data_id = request.GET['data_id']
    data = get_picklist_data(data_id, user.id)
    all_data = []
    for dat in data:
        val = itemgetter(*headers.values())(dat)
        temp = OrderedDict(zip(headers.keys(),val))
        all_data.append(temp)
    path = print_excel(request, {'aaData': all_data}, headers.keys(), str(data_id))
    return HttpResponse(path)

@csrf_exempt
@login_required
def edit_issue(request):
    data_id = request.GET['data_id']
    data = Issues.objects.filter(id=data_id)
    return render(request, 'templates/toggle/update_issue.html', {'data': data[0], 'issue_fields': UPDATE_ISSUE_FIELDS, 'issue_id': data_id})


@csrf_exempt
def get_customer_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['Shipment Number', 'Customer ID', 'Customer Name ', 'Total Quantity']
    all_data = OrderedDict()
    if search_term:
        results = ShipmentInfo.objects.filter(Q(order_shipment__shipment_number__icontains=search_term) |
                                              Q(order__customer_id__icontains=search_term) | Q(order__customer_name__icontains=search_term),
                                              order_shipment__user=user.id).order_by('order_id')
    else:
        results = ShipmentInfo.objects.filter(order_shipment__user=user.id).order_by('order_id')
    for result in results:
        tracking = ShipmentTracking.objects.filter(shipment_id=result.id, shipment__order__user=user.id).order_by('-creation_date').\
                                            values_list('ship_status', flat=True)
        if tracking and tracking[0] == 'Delivered':
            continue
        cond = (result.order_shipment.shipment_number, result.order.customer_id, result.order.customer_name)
        all_data.setdefault(cond, 0)
        all_data[cond] += result.shipping_quantity

    temp_data['recordsTotal'] = len(all_data)
    temp_data['recordsFiltered'] = len(all_data)
    for key, value in all_data.iteritems():
        temp_data['aaData'].append({'DT_RowId': key[0], 'Shipment Number': key[0], 'Customer ID': key[1], 'Customer Name ': key[2],
                                    'Total Quantity': value, 'DT_RowClass': 'results' })
    sort_col = lis[col_num]

    if order_term == 'asc':
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
    else:
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)


def get_picked_data(data_id, user):
    picklist_orders = Picklist.objects.filter(picklist_number=data_id, order__sku__user=user).exclude(status='open')
    data = []
    for order in picklist_orders:
        if not order.stock:
            data.append({'wms_code': order.order.sku.wms_code, 'zone': 'NO STOCK', 'location': 'NO STOCK', 'reserved_quantity': int(order.reserved_quantity), 'picked_quantity': int(order.picked_quantity), 'stock_id': 0, 'picklist_number': data_id, 'id': order.id, 'order_id': order.order.order_id, 'image': '', 'title': order.order.title})
            continue
        picklist_location = PicklistLocation.objects.filter(picklist_id=order.id, picklist__order__sku__user=user)
        for loc in picklist_location:
            if 'picked' in order.status or order.status == 'dispatched':
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
                data.append({'wms_code': wms_code, 'zone': stock_detail.location.zone.zone, 'location': stock_detail.location.location, 'reserved_quantity': int(loc.quantity), 'picked_quantity': int(loc.quantity), 'stock_id': loc.stock_id, 'picklist_number': data_id, 'id': order.id, 'order_id': order_id, 'image': order.stock.sku.image_url, 'title': title})
    return data

@csrf_exempt
@login_required
def process_orders(request):
    return render(request, 'templates/process_orders.html')

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

def check_duplicates(data_set, data_type, cell_data, index_status, row_idx):
    if cell_data and cell_data in data_set:
        #index_status.setdefault(row_idx, set()).add('Duplicate %s Code' % data_type)
        for index, data in enumerate(data_set):
            if data == cell_data:
                index_status.setdefault(index + 1, set()).add('Duplicate %s Code' % data_type)
    data_set.append(cell_data)
    return index_status

def validate_combo_sku_form(open_sheet, user):
    index_status = {}
    header_data = open_sheet.cell(0, 1).value
    if header_data != 'Combo SKU':
        return 'Invalid File'

    for row_idx in range(1, open_sheet.nrows):

        for col_idx in range(0, len(COMBO_SKU_EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if not cell_data:
                if col_idx == 0:
                    message = 'SKU Code Missing'
                if col_idx == 1:
                    message = 'Combo SKU Code Missing'
                index_status.setdefault(row_idx, set()).add(message)
                continue
            if isinstance(cell_data, (int, float)):
                cell_data = int(cell_data)
            cell_data = str(cell_data)

            sku_master = MarketplaceMapping.objects.filter(marketplace_code=cell_data, sku__user=user)
            if not sku_master:
                sku_master = SKUMaster.objects.filter(sku_code=cell_data, user=user)
            if not sku_master:
                if col_idx == 0:
                    message = 'Invalid SKU Code'
                else:
                    message = 'Invalid Combo SKU'
                index_status.setdefault(row_idx, set()).add(message)

    if not index_status:
        return 'Success'

    f_name = '%s.combo_sku_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, COMBO_SKU_EXCEL_HEADERS, 'Combo SKU')
    return f_name


@csrf_exempt
def validate_sku_form(open_sheet, user):
    sku_data = []
    wms_data = []
    index_status = {}
    header_data = open_sheet.cell(0, 0).value
    if header_data != 'WMS Code':
        return 'Invalid File'

    for row_idx in range(1, open_sheet.nrows):
        for col_idx in range(0, len(SKU_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            validation_dict = {0: 'WMS Code'}

            if col_idx in validation_dict:
                value = validation_dict[col_idx]
                #index_status = alphanum_validation(cell_data, value, index_status, row_idx)

            if col_idx == 0:
                data_set = wms_data
                data_type = 'WMS'

                #index_status = check_duplicates(data_set, data_type, cell_data, index_status, row_idx)

            if col_idx == 0:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('WMS Code missing')
            if col_idx == 2 and cell_data:
                sku_groups = SKUGroups.objects.filter(group__iexact=cell_data, user=user.id)
                if not sku_groups:
                    index_status.setdefault(row_idx, set()).add("Group doesn't exists")

            if col_idx == 6:
                if cell_data:
                    data = ZoneMaster.objects.filter(zone=cell_data.upper(),user=user.id)
                    if not data:
                        index_status.setdefault(row_idx, set()).add('Invalid Zone')
                #else:
                #    index_status.setdefault(row_idx, set()).add('Zone should not be empty')
            if col_idx == 7:
                if not isinstance(cell_data, (int, float)) and cell_data:
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')

                if cell_data and isinstance(cell_data, (int, float)):
                    if int(cell_data) < 0:
                        index_status.setdefault(row_idx, set()).add('Quantity should not be in negative')

    master_sku = SKUMaster.objects.filter(user=user.id)
    master_sku = [data.sku_code for data in master_sku]
    missing_data = set(sku_data) - set(master_sku)

    if not index_status:
        return 'Success'

    f_name = '%s.sku_form.xls' % user.id
    write_error_file(f_name, index_status, open_sheet, SKU_HEADERS, 'Inventory')
    return f_name

@csrf_exempt
def validate_inventory_form(open_sheet, user_id):
    mapping_dict = {}
    index_status = {}
    location = {}
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'Receipt Number':
                    return 'Invalid File'
                break

            validation_dict = {0: 'Receipt Number', 1: 'receipt date', 3: 'Location'}
            if col_idx in validation_dict and not cell_data:
                index_status.setdefault(row_idx, set()).add('Invalid %s' % validation_dict[col_idx])

            if col_idx == 1:
                try:
                    receipt_date = xldate_as_tuple(cell_data, 0)
                except:
                    index_status.setdefault(row_idx, set()).add('Invalid Receipt Date format')

            if col_idx == 2:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                mapping_dict[row_idx] = cell_data
                sku_master = SKUMaster.objects.filter(wms_code = cell_data,user=user_id)
                if not sku_master:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU-WMS Mapping')
            elif col_idx == 3:
                location[row_idx] = cell_data
            elif col_idx == 4:
                if cell_data and (not isinstance(cell_data, (int, float)) or (int(cell_data) < 0)):
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')
            elif col_idx == 5:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Receipt Type')

    locations = LocationMaster.objects.filter(zone__user=user_id).values('location')
    locations = [loc['location'] for loc in locations]
    location_diff = set(location.values()) - set(locations)

    for key, value in location.iteritems():
        if value and value in location_diff:
            index_status.setdefault(key, set()).add('Invalid Location')

    if not index_status:
        return 'Success'

    f_name = '%s.inventory_form.xls' % user_id
    write_error_file(f_name, index_status, open_sheet, EXCEL_HEADERS, 'Inventory')
    return f_name


@csrf_exempt
def validate_move_inventory_form(open_sheet, user):
    mapping_dict = {}
    index_status = {}
    location = {}
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(MOVE_INVENTORY_UPLOAD_FIELDS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'WMS Code':
                    return 'Invalid File'
                break
            if col_idx == 0:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                sku_master = SKUMaster.objects.filter(wms_code=cell_data, user=user)
                if not sku_master:
                    index_status.setdefault(row_idx, set()).add('Invalid WMS Code')
            elif col_idx == 1:
                if cell_data:
                    location_master = LocationMaster.objects.filter(zone__user=user, location=cell_data)
                    if not location_master:
                        index_status.setdefault(row_idx, set()).add('Invalid Source Location')
                    if location_master and sku_master:
                        source_stock = StockDetail.objects.filter(sku__user=user, location__location=cell_data, sku_id=sku_master[0].id)
                        if not source_stock:
                            index_status.setdefault(row_idx, set()).add('location not have the stock of wms code')
                else:
                    index_status.setdefault(row_idx, set()).add('Source Location should not be empty')
            elif col_idx == 2:
                if cell_data:
                    dest_location = LocationMaster.objects.filter(zone__user=user, location=cell_data)
                    if not dest_location:
                        index_status.setdefault(row_idx, set()).add('Invalid Destination Location')
                else:
                    index_status.setdefault(row_idx, set()).add('Destination Location should not be empty')
            elif col_idx == 3:
                if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')

    if not index_status:
        return 'Success'
    f_name = '%s.move_inventory_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, MOVE_INVENTORY_UPLOAD_FIELDS, 'Move Inventory')
    return f_name


@csrf_exempt
@login_required
@get_admin_user
def sku_upload(request, user=''):
    fname = request.FILES['files']
    if fname.name.split('.')[-1] != 'xls' and fname.name.split('.')[-1] != 'xlsx':
        return HttpResponse('Invalid File Format')

    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')

    status = validate_sku_form(open_sheet, user)
    if status != 'Success':
        return HttpResponse(status)

    for row_idx in range(1, open_sheet.nrows):
        sku_code = ''
        wms_code = ''
        sku_data = None
        for col_idx in range(0, len(SKU_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value

            if col_idx == 0:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)

                wms_code = cell_data
                if wms_code:
                    if not sku_data:
                        sku_data = SKUMaster.objects.filter(wms_code = wms_code,user=user.id)
                        if sku_data:
                            sku_data = sku_data[0]

            if col_idx == 6:
                zone_id = None
                if cell_data:
                    cell_data = ZoneMaster.objects.get(zone=cell_data.upper(),user=user.id).id
                    zone_id = cell_data

            if col_idx == 8:
                if cell_data.lower() == 'inactive':
                    status = 0
                else:
                    status = 1

            if sku_data:
                if col_idx == 1 and cell_data:
                    if isinstance(cell_data, (int, float)):
                        cell_data = int(cell_data)
                    cell_data = str(cell_data)

                if col_idx == 7 and cell_data:
                    if not cell_data:
                        cell_data = 0

                if col_idx == 8 and cell_data:
                    cell_data = status

                if cell_data:
                    setattr(sku_data, SKU_EXCEL[col_idx], cell_data)

        if sku_data:
            sku_data.save()

        if not sku_data:
            data_dict = copy.deepcopy(SKU_DATA)
            data_dict['user'] = user.id
            for col_idx in range(0, len(SKU_HEADERS)):
                cell_data = open_sheet.cell(row_idx, col_idx).value
                if SKU_EXCEL[col_idx] == 'wms_code':
                    data_dict[SKU_EXCEL[col_idx]] = wms_code
                elif SKU_EXCEL[col_idx] == 'threshold_quantity':
                    if not cell_data:
                        cell_data = 0
                    data_dict[SKU_EXCEL[col_idx]] = int(cell_data)
                elif SKU_EXCEL[col_idx] == 'zone_id' and zone_id:
                    data_dict[SKU_EXCEL[col_idx]] = zone_id
                elif SKU_EXCEL[col_idx] == 'status':
                    if cell_data.lower() == 'inactive':
                        status = 0
                    else:
                        status = 1
                    data_dict[SKU_EXCEL[col_idx]] = status
                else:
                    data_dict[SKU_EXCEL[col_idx]] = cell_data
            data_dict['sku_code'] = data_dict['wms_code']
            sku_master = SKUMaster(**data_dict)
            sku_master.save()

    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def combo_sku_upload(request, user=''):
    fname = request.FILES['files']
    if (fname.name).split('.')[-1] != 'xls' and (fname.name).split('.')[-1] != 'xlsx':
        return HttpResponse('Invalid File Format')

    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')

    status = validate_combo_sku_form(open_sheet, str(user.id))
    if status != 'Success':
        return HttpResponse(status)

    for row_idx in range(1, open_sheet.nrows):
        for col_idx in range(0, len(COMBO_SKU_EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value

            if col_idx in (0, 1):
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                sku_data = MarketplaceMapping.objects.filter(marketplace_code=cell_data, sku__user=user.id)
                if sku_data:
                    sku_data = sku_data[0].sku
                if not sku_data:
                    sku_data = SKUMaster.objects.filter(sku_code=cell_data, user=user.id)[0]

            if col_idx == 0:
                sku_code = sku_data

            if col_idx == 1:
                combo_data = sku_data

        relation_data = {'relation_type': 'combo', 'member_sku': combo_data, 'parent_sku': sku_code}
        sku_relation = SKURelation.objects.filter(**relation_data)
        if not sku_relation:
            sku_relation = SKURelation(**relation_data)
            sku_relation.save()
        elif sku_relation:
            sku_relation = sku_relation[0]
        sku_relation.parent_sku.relation_type = 'combo'
        sku_relation.parent_sku.save()
    return HttpResponse('Success')

@csrf_exempt
def validate_supplier_form(open_sheet, user_id):
    index_status = {}
    supplier_ids = []
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(SUPPLIER_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'Supplier Id':
                    return 'Invalid File'
                break

            if col_idx == 0:
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if cell_data and cell_data in supplier_ids:
                    index_status.setdefault(row_idx, set()).add('Duplicate Supplier ID')
                    for index, data in enumerate(supplier_ids):
                        if data == cell_data:
                            index_status.setdefault(index + 1, set()).add('Duplicate Supplier ID')
                supplier_ids.append(cell_data)

            if col_idx == 1:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Supplier Name')
                '''else:
                    temp1 = namevalid(cell_data)
                    if temp1:
                        index_status.setdefault(row_idx, set()).add(temp1 % 'Supplier Name')'''

            if col_idx == 4:
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Wrong contact information')

    if not index_status:
        return 'Success'

    f_name = '%s.supplier_form.xls' % user_id
    write_error_file(f_name, index_status, open_sheet, SUPPLIER_HEADERS, 'Supplier')
    return f_name

@csrf_exempt
def validate_supplier_sku_form(open_sheet, user_id):
    index_status = {}
    supplier_ids = []
    temp1 = ''
    supplier_list = SupplierMaster.objects.filter(user=user_id).values_list('id',flat=True)
    if supplier_list:
        for i in supplier_list:
            supplier_ids.append(i)
    wms_code1 = ''
    preference1 = ''
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(SUPPLIER_SKU_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'Supplier Id':
                    return 'Invalid File'
                break
            if col_idx == 0:
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if cell_data and cell_data not in supplier_ids:
                    index_status.setdefault(row_idx, set()).add('Supplier ID Not Found')
                    for index, data in enumerate(supplier_ids):
                        if data == cell_data:
                            index_status.setdefault(index + 1, set()).add('Supplier ID Not Found')
                supplier_ids.append(cell_data)

            if col_idx == 1:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing WMS Code')
                else:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    wms_check = SKUMaster.objects.filter(wms_code=cell_data,user=user_id)
                    if not wms_check:
                        index_status.setdefault(row_idx, set()).add('Invalid WMS Code')
                    wms_code1=cell_data
            if col_idx == 2:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing Preference')
                else:
                    preference1 = int(cell_data)
    if wms_code1 and preference1:
        supp_val=SKUMaster.objects.filter(wms_code=wms_code1,user=user_id)
        if supp_val:
            temp1=SKUSupplier.objects.filter(Q(sku_id=supp_val[0].id) & Q(preference=preference1),sku__user=user_id)
    if temp1:
        index_status.setdefault(row_idx, set()).add('Preference matched with existing WMS Code')

    if not index_status:
        return 'Success'

    f_name = '%s.supplier_sku_form.xls' % user_id
    write_error_file(f_name, index_status, open_sheet, SUPPLIER_SKU_HEADERS, 'Supplier')
    return f_name


@csrf_exempt
def validate_purchase_order(open_sheet, user):
    index_status = {}
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(PURCHASE_ORDER_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'PO Name':
                    return 'Invalid File'
                break
            if col_idx == 2:
                if isinstance(cell_data, (int, float)):
                    cell_data = str(int(cell_data))
                if cell_data:
                    supplier = SupplierMaster.objects.filter(user=user, id=cell_data.upper())
                    if not supplier:
                        index_status.setdefault(row_idx, set()).add("Supplier ID doesn't exist")
                else:
                    index_status.setdefault(row_idx, set()).add('Missing Supplier ID')
            elif col_idx == 1:
                if not (isinstance(cell_data, float) or '-' in str(cell_data)):
                    index_status.setdefault(row_idx, set()).add('Check the date format')
            elif col_idx == 3:
                if not cell_data:
                    index_status.setdefault(row_idx, set()).add('Missing WMS Code')
                else:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    sku_master = SKUMaster.objects.filter(wms_code=cell_data.upper())
                    if not sku_master:
                        index_status.setdefault(row_idx, set()).add("WMS Code doesn't exist")
            elif col_idx == 4:
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Quantity should be integer')
                else:
                    index_status.setdefault(row_idx, set()).add('Missing Quantity')
            elif col_idx == 5:
                if cell_data !='':
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Price should be a number')
                else:
                    index_status.setdefault(row_idx, set()).add('Missing Price')

    if not index_status:
        return 'Success'
    wb = Workbook()
    ws = wb.add_sheet('Purchase Order')
    header_style = easyxf('font: bold on')
    headers = copy.copy(PURCHASE_ORDER_HEADERS)
    headers.append('Status')
    for count, header in enumerate(headers):
        ws.write(0, count, header, header_style)

    for row_idx in range(1, open_sheet.nrows):
        for col_idx in range(0, len(PURCHASE_ORDER_HEADERS)):
            ws.write(row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value)
        else:
            index_data = index_status.get(row_idx, '')
            if index_data:
                index_data = ', '.join(index_data)
            ws.write(row_idx, col_idx + 1, index_data)

    wb.save('%s.purchase_order_form.xls' % user)
    return '%s.purchase_order_form.xls' % user


@csrf_exempt
@login_required
@get_admin_user
def supplier_upload(request, user=''):
    fname = request.FILES['files']
    if fname.name.split('.')[-1] == 'xls' or fname.name.split('.')[-1] == 'xlsx':
        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')

        status = validate_supplier_form(open_sheet, str(user.id))
        if status != 'Success':
            return HttpResponse(status)

        for row_idx in range(1, open_sheet.nrows):
            sku_code = ''
            wms_code = ''
            supplier_data = copy.deepcopy(SUPPLIER_DATA)
            for col_idx in range(0, len(SUPPLIER_HEADERS)):
                cell_data = open_sheet.cell(row_idx, col_idx).value
                if col_idx == 0:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    supplier_data['id'] = cell_data
                if col_idx == 1:
                    supplier_data['name']  = cell_data
                    if not isinstance(cell_data, (str, unicode)):
                        supplier_data['name'] = str(int(cell_data))

                if col_idx == 2:
                    supplier_data['address'] = cell_data
                if col_idx == 3:
                    supplier_data['email_id'] = cell_data
                if col_idx == 4:
                    cell_data = int(float(cell_data))
                    supplier_data['phone_number'] = cell_data

            supplier = SupplierMaster.objects.filter(id=supplier_data['id'], user=user.id)
            if not supplier:
                supplier_data['user'] = user.id
                supplier = SupplierMaster(**supplier_data)
                supplier.save()

    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def supplier_sku_upload(request, user=''):
    fname = request.FILES['files']
    if fname.name.split('.')[-1] == 'xls' or fname.name.split('.')[-1] == 'xlsx':
        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')

        status = validate_supplier_sku_form(open_sheet, str(user.id))
        if status != 'Success':
            return HttpResponse(status)

        for row_idx in range(1, open_sheet.nrows):
            sku_code = ''
            wms_code = ''
            supplier_data = copy.deepcopy(SUPPLIER_SKU_DATA)
            for col_idx in range(0, len(SUPPLIER_SKU_HEADERS)):
                cell_data = open_sheet.cell(row_idx, col_idx).value
                if col_idx == 0:
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    supplier_data['supplier_id'] = cell_data
                elif col_idx == 1:
                    if isinstance(cell_data, (int, float)):
                        cell_data = int(cell_data)
                    cell_data = str(cell_data)
                    sku_master = SKUMaster.objects.filter(wms_code=cell_data, user=user.id)
                    if sku_master:
                        supplier_data['sku'] = sku_master[0]
                elif col_idx == 2:
                    supplier_data['preference'] = str(int(cell_data))
                elif col_idx == 3:
                    if not cell_data:
                        cell_data = 0
                    cell_data = int(cell_data)
                    supplier_data['moq'] = cell_data
                elif col_idx == 4:
                    if not cell_data:
                        cell_data = 0
                    cell_data = float(cell_data)
                    supplier_data['price'] = cell_data

            supplier_sku = SupplierMaster.objects.filter(id=supplier_data['supplier_id'], user=user.id)
            if supplier_sku:
                supplier_sku = SKUSupplier(**supplier_data)
                supplier_sku.save()
        return HttpResponse('Success')
    else:
        return HttpResponse('Invalid File Format')

@csrf_exempt
@login_required
@get_admin_user
def insert_order_data(request, user=''):
    myDict = dict(request.GET.iterlists())
    order_id = get_order_id(user.id)

    invalid_skus = []
    items = []
    for i in range(0, len(myDict['sku_id'])):
        order_data = copy.deepcopy(UPLOAD_ORDER_DATA)
        order_data['order_id'] = order_id
        order_data['order_code'] = 'MN'
        order_data['user'] = user.id

        for key, value in request.GET.iteritems():
            if key == 'sku_id':
                sku_master = SKUMaster.objects.filter(sku_code=myDict[key][i].upper(), user=user.id)
                if not sku_master:
                    sku_master = SKUMaster.objects.filter(wms_code=myDict[key][i].upper(), user=user.id)

                if not sku_master:
                    invalid_skus.append(myDict[key][i])
                    continue

                order_data['sku_id'] = sku_master[0].id
                order_data['title'] = sku_master[0].sku_desc
            elif key == 'quantity' or key == 'pin_code':
                try:
                    value = int(myDict[key][i])
                except:
                    value = 0
                order_data[key] = value
            elif key == 'shipment_date':
                if value:
                    ship_date = value.split('/')
                    order_data[key] = datetime.date(int(ship_date[2]), int(ship_date[0]), int(ship_date[1]))
            elif key == 'invoice_amount':
                try:
                    value = int(myDict[key][i])
                except:
                    value = 0
                order_data[key] = value
            else:
                order_data[key] = value

        if not order_data['sku_id'] or invalid_skus:
            continue

        order_obj = OrderDetail.objects.filter(order_id=order_data['order_id'], user=user.id, sku_id=order_data['sku_id'], order_code=order_data['order_code'])
        if not order_obj:
            order_detail = OrderDetail(**order_data)
            order_detail.save()

        items.append([sku_master[0].sku_desc, request.user.username, order_data['quantity'], order_data.get('invoice_amount', 0)])

    if invalid_skus:
        return HttpResponse("Invalid SKU: %s" % ', '.join(invalid_skus))

    misc_detail = MiscDetail.objects.filter(user=request.user.id, misc_type='order', misc_value='true')
    if misc_detail:
        headers = ['Product Details', 'Seller Details', 'Ordered Quantity', 'Total']
        data_dict = {'customer_name': order_data['customer_name'], 'order_id': order_detail.order_id,
                                    'address': order_data['address'], 'phone_number': order_data['telephone'], 'items': items,
                                     'headers': headers}

        t = loader.get_template('templates/order_confirmation.html')
        c = Context(data_dict)
        rendered = t.render(c)

        email = order_data['email_id']
        if email:
            send_mail([email], 'Order Confirmation: %s' % order_detail.order_id, rendered)

    return HttpResponse('Success')

def get_marketplace_headers(row_idx, open_sheet):
    market_excel = {}
    mapping = OrderedDict()
    for col_idx in range(1, open_sheet.ncols):
        cell_data = open_sheet.cell(row_idx, col_idx).value
        if ' SKU' in cell_data:
            market_excel[cell_data] = col_idx
        if ' Description' in cell_data:
            sub_str = ' '.join(cell_data.split(' ')[:-1])
            for s in filter (lambda x: sub_str in x, market_excel.keys()):
                mapping[market_excel[s]] = col_idx
    marketplace_excel = {'marketplace_code': mapping.keys(), 'description': mapping.values()}
    return marketplace_excel


@csrf_exempt
@login_required
@get_admin_user
def marketplace_sku_upload(request, user=''):
    fname = request.FILES['files']
    if (fname.name).split('.')[-1] == 'xls' or (fname.name).split('.')[-1] == 'xlsx':
        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')

        market_excel = {}
        for row_idx in range(0, open_sheet.nrows):
            save_records = []
            print 'Record Processing Started: %s' % str(datetime.datetime.now())
            if row_idx == 0:
                marketplace_excel = get_marketplace_headers(row_idx, open_sheet)
                continue

            sku_code = ''
            sku_desc = ''
            wms_code_data = open_sheet.cell(row_idx, 0).value
            if not wms_code_data:
                continue

            if isinstance(wms_code_data, float):
                sku_code = str(int(wms_code_data))
            else:
                sku_code = wms_code_data.upper()

            sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
            if sku_master:
                sku_master = sku_master[0]

            for marketplace_code, marketplace_desc in zip(marketplace_excel['marketplace_code'], marketplace_excel['description']):
                marketplace_name = open_sheet.cell(0, marketplace_code).value.split(' ')[0]
                market_sku = open_sheet.cell(row_idx, marketplace_code).value
                market_desc = open_sheet.cell(row_idx, marketplace_desc).value

                if isinstance(market_sku, float):
                    market_sku = str(int(market_sku))
                else:
                    market_sku = market_sku.upper()

                sku_codes = market_sku.split('###')
                sku_descs = market_desc.split('###')
                for key, value in zip(sku_codes, sku_descs):
                    market_sku_mapping = MarketplaceMapping.objects.filter(sku_type=marketplace_name, marketplace_code=key, sku__user=user.id)
                    if market_sku_mapping:
                        continue

                    if not sku_desc:
                        sku_desc = value

                    if not sku_master:
                        sku_data = {'sku_code': sku_code, 'wms_code': sku_code, 'sku_desc': sku_desc, 'status': 1, 'creation_date': NOW,
                                'user': user.id, 'threshold_quantity': 0, 'online_percentage': 0}
                        sku_master = SKUMaster(**sku_data)
                        sku_master.save()

                    if not sku_master.sku_desc and sku_desc:
                        sku_master.sku_desc = sku_desc
                        sku_master.save()

                    market_mapping = copy.deepcopy(MARKETPLACE_SKU_FIELDS)
                    market_mapping['sku_type'] = marketplace_name
                    market_mapping['marketplace_code'] = key
                    market_mapping['description'] = value
                    market_mapping['sku_id'] = sku_master.id
                    market_data = MarketplaceMapping(**market_mapping)
                    save_records.append(market_data)
                    #market_data.save()
            if save_records:
                MarketplaceMapping.objects.bulk_create(save_records)

            print 'Record processing ended: %s' % str(datetime.datetime.now())
        return HttpResponse('Success')
    else:
        return HttpResponse('Invalid File Format')

@csrf_exempt
@login_required
@get_admin_user
def purchase_order_upload(request, user=''):
    order_ids = {}
    fname = request.FILES['files']
    if fname.name.split('.')[-1] == 'xls' or fname.name.split('.')[-1] == 'xlsx':
        try:
            open_book = open_workbook(filename=None, file_contents=fname.read())
            open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse('Invalid File')

        status = validate_purchase_order(open_sheet, str(user.id))
        if status != 'Success':
            return HttpResponse(status)
        for row_idx in range(1, open_sheet.nrows):
            order_data = copy.deepcopy(PO_SUGGESTIONS_DATA)
            data = copy.deepcopy(PO_DATA)
            for col_idx in range(0, len(PURCHASE_ORDER_HEADERS)):
                cell_data = open_sheet.cell(row_idx, col_idx).value
                if col_idx == 2:
                    if type(cell_data) == float:
                        cell_data = int(cell_data)
                    else:
                        cell_data = cell_data.upper()
                    supplier = SupplierMaster.objects.filter(user=user.id, id=cell_data)
                    if supplier:
                        order_data['supplier_id'] = cell_data
                elif col_idx == 3:
                    if type(cell_data) == float:
                        cell_data = int(cell_data)
                    else:
                        cell_data = cell_data.upper()
                    sku_master = SKUMaster.objects.filter(wms_code=cell_data, user=user.id)
                    if sku_master:
                        order_data['sku_id'] = sku_master[0].id
                elif col_idx == 4:
                    order_data['order_quantity'] = int(cell_data)
                elif col_idx == 5:
                    order_data['price'] = cell_data
                elif col_idx == 1:
                    if cell_data and '-' in str(cell_data):
                        order_date = cell_data.split('-')
                        data['po_date'] = datetime.date(int(order_date[2]), int(order_date[0]), int(order_date[1]))
                    elif isinstance(cell_data, float):
                        data['po_date'] = xldate_as_tuple(cell_data, 0)
                elif col_idx == 0:
                    order_data['po_name'] = cell_data
                elif col_idx == 6:
                    data['ship_to'] = cell_data

            if (order_data['po_name'], order_data['supplier_id'], data['po_date']) not in order_ids.keys():
                po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).order_by('-order_id')
                if not po_data:
                    po_id = 0
                else:
                    po_id = po_data[0].order_id
                order_ids[order_data['po_name'], order_data['supplier_id'], data['po_date']] = po_id
            else:
                po_id = order_ids[order_data['po_name'], order_data['supplier_id'], data['po_date']]
            ids_dict = {}
            po_data = []
            total = 0
            order_data['status'] = 0
            data1 = OpenPO(**order_data)
            data1.save()
            purchase_order = OpenPO.objects.get(id=data1.id, sku__user=user.id)
            sup_id = purchase_order.id
            supplier = purchase_order.supplier_id
            if supplier not in ids_dict:
                po_id = po_id + 1
                ids_dict[supplier] = po_id
            data['open_po_id'] = sup_id
            data['order_id'] = ids_dict[supplier]
            user_profile = UserProfile.objects.filter(user_id=user.id)
            if user_profile:
                data['prefix'] = user_profile[0].prefix
            order = PurchaseOrder(**data)
            order.save()

    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def order_upload(request, user=''):
    index_status = {}
    fname = request.FILES['files']
    order_mapping = {}
    if (fname.name).split('.')[-1] == 'csv':
        count = 0
        reader = [[val.replace('\n', '').replace('\t', '').replace('\r','') for val in row] for row in csv.reader(fname.read().splitlines())]
        
        for row in reader:
            if not row:
               continue
            order_data = copy.deepcopy(UPLOAD_ORDER_DATA)
            if count == 0:
                count +=1
                if row[1] == 'Order No':
                    order_mapping = copy.deepcopy(SHOPCLUES_EXCEL)
                elif row[1] == 'FSN' and row[16] == 'Invoice No.':
                    order_mapping = copy.deepcopy(FLIPKART_EXCEL)
                elif row[1] == 'FSN' and row[16] != 'Invoice No.':
                    order_mapping = copy.deepcopy(FLIPKART_EXCEL1)
                elif row[1] == 'Shipment ID' and row[2] == 'ORDER ITEM ID':
                    order_mapping = copy.deepcopy(FLIPKART_EXCEL2)
                elif row[3] == 'customer_firstname':
                    order_mapping = copy.deepcopy(PAYTM_EXCEL1)
                elif row[1] == 'item_name':
                    order_mapping = copy.deepcopy(PAYTM_EXCEL2)
                elif row[1] == 'Order Item ID':
                    order_mapping = copy.deepcopy(FLIPKART_FA_EXCEL)
                elif row[0] == 'Sr. No' and row[1] == 'PO No':
                    order_mapping = copy.deepcopy(MYNTRA_EXCEL)
                elif row[1] == 'PO No':
                    order_mapping = copy.deepcopy(JABONG_EXCEL)
                elif row[0] == 'Product Name' and row[1] == 'FSN':
                    order_mapping = copy.deepcopy(FLIPKART_FA_EXCEL1)
                elif row[0] == 'Shipping' and row[1] == 'Date':
                    order_mapping = copy.deepcopy(CAMPUS_SUTRA_EXCEL)
                continue

            if not order_mapping:
                break

            sku_id = ''
            cell_data = row[order_mapping['sku_code']]
            title = ''
            if 'title' in order_mapping.keys():
                title = row[order_mapping['title']]

            if type(cell_data) == float:
                sku_code = str(int(cell_data))
            elif isinstance(cell_data, str) and '.' in cell_data:
                sku_code = str(int(float(cell_data)))
            else:
                sku_code = cell_data.upper()

            sku_master=SKUMaster.objects.filter(sku_code=sku_code,user=user.id)
            if sku_master:
                sku_id = sku_master[0].id
            else:
                market_mapping = ''
                if sku_code:
                    market_mapping = MarketplaceMapping.objects.filter(marketplace_code=sku_code, sku__user=user.id, sku__status=1)
                if not market_mapping and title:
                    market_mapping = MarketplaceMapping.objects.filter(description=title, sku__user=user.id, sku__status=1)
                if market_mapping:
                    sku_id = market_mapping[0].sku_id

            if not sku_id:
                index_status.setdefault(count, set()).add('SKU Mapping Not Available')
            count += 1

        if index_status:
            f_name = fname.name.replace(' ', '_')
            rewrite_csv_file(f_name, index_status, reader)
            return HttpResponse(f_name)

        reader = csv.reader(fname)
        for row in reader:
            if reader.line_num == 1:
                continue

            if not order_mapping:
                break
            for key, value in order_mapping.iteritems():
                if key == 'marketplace' or key not in order_mapping.keys():
                    continue
                if key == 'order_id' and 'order_id' in order_mapping.keys():
                    if order_mapping['marketplace'] == 'Jabong':
                        order_id = row[order_mapping['order_id']].strip("'").strip('"')
                        search_params = {'user': user.id}
                        if order_id:
                            order_code = re.findall('\D+',order_id)
                            if order_code:
                                search_params['order_code'] = order_code[0].replace('/','')
                            else:
                                search_params['order_code'] = 'MN'
                            order_data['order_code'] = search_params['order_code']
                        order_detail = OrderDetail.objects.filter(**search_params).order_by('-order_id')
                        if order_detail:
                            order_data['order_id'] = int(order_detail[0].order_id) + 1
                        else:
                            order_data['order_id'] = 1001
                    else:
                        order_id = row[order_mapping['order_id']].strip("'").strip('"')
                        order_data['order_id'] = int(order_id)
                        order_data['order_code'] = 'OD'
                elif key == 'quantity':
                    order_data[key] = int(row[order_mapping[key]])
                elif key == 'item_name':
                    order_data['invoice_amount'] += int(row[11])
                elif key == 'address':
                    order_data[key] = row[order_mapping[key]][:256]
                elif key == 'sku_code':
                    sku_code = row[order_mapping[key]]
                elif key == 'shipment_date':
                    try:
                        if cell_data and ' ' in cell_data:
                            order_data['shipment_date'] = datetime.datetime.strptime(cell_data, '%d/%m/%Y %H:%M')
                        elif cell_data:
                            order_data['shipment_date'] = datetime.datetime(1899,12,30) + datetime.timedelta(days=cell_data)
                    except:
                        order_data['shipment_date'] = NOW
                else:
                    order_data[key] = row[order_mapping[key]]
            order_data['user'] = user.id
            if not 'quantity' in order_data.keys():
                order_data['quantity'] = 1

            if type(sku_code) == float:
                cell_data = int(sku_code)
            else:
                cell_data = sku_code.upper()

            sku_master=SKUMaster.objects.filter(sku_code=cell_data, user=user.id)
            if sku_master:
                order_data['sku_id'] = sku_master[0].id
            else:
                market_mapping = ''
                if cell_data:
                    market_mapping = MarketplaceMapping.objects.filter(marketplace_code=cell_data, sku__user=user.id, sku__status=1)
                if not market_mapping and order_data['title']:
                    market_mapping = MarketplaceMapping.objects.filter(description=order_data['title'], sku__user=user.id, sku__status=1)
                if market_mapping:
                    order_data['sku_id'] = market_mapping[0].sku_id
                else:
                    order_data['sku_id'] = SKUMaster.objects.get(sku_code='TEMP', user=request.user.id).id
                    order_data['sku_code'] = sku_code

            if not order_data.get('order_id', ''):
                order_detail = OrderDetail.objects.filter(order_code='MN',user=user.id).order_by('-order_id')
                if order_detail:
                    order_data['order_id'] = int(order_detail[0].order_id) + 1
                    order_data['order_code'] = 'MN'
                else:
                    order_data['order_id'] = 1001
                    order_data['order_code'] = 'MN'

            order_obj = OrderDetail.objects.filter(order_id = order_data['order_id'], sku=order_data['sku_id'], user=user.id)
            if not order_obj:
                order_data['marketplace'] = order_mapping['marketplace']
                order_detail = OrderDetail(**order_data)
                order_detail.save()

    elif (fname.name).split('.')[-1] == 'xls' or (fname.name).split('.')[-1] == 'xlsx':
        try:
            data = fname.read()
            if '<table' in data:
                open_book, open_sheet = html_excel_data(data, fname)
            else:
                open_book = open_workbook(filename=None, file_contents=data)
                open_sheet = open_book.sheet_by_index(0)
        except:
            return HttpResponse("Invalid File")
        if open_sheet.cell(0,0).value == 'Order ID':
            order_mapping = copy.deepcopy(ORDER_DEF_EXCEL)
        elif open_sheet.cell(0,0).value == 'Courier':
            order_mapping = copy.deepcopy(SNAPDEAL_EXCEL)
        elif 'Courier' in open_sheet.cell(0,1).value:
            order_mapping = copy.deepcopy(SNAPDEAL_EXCEL1)
        elif open_sheet.cell(0,0).value == 'ASIN':
            order_mapping = copy.deepcopy(AMAZON_FA_EXCEL)
        elif open_sheet.cell(0,0).value == 'Sl no':
            order_mapping = copy.deepcopy(SNAPDEAL_FA_EXCEL)
        elif open_sheet.cell(0,1).value == 'Payment Mode':
            order_mapping = copy.deepcopy(INDIA_TIMES_EXCEL)
        elif open_sheet.cell(0,3).value == 'Billing Name':
            order_mapping = copy.deepcopy(HOMESHOP18_EXCEL)
        elif open_sheet.cell(0,2).value == 'purchase-date' and open_sheet.cell(0,4).value == 'payments-date':
            order_mapping = copy.deepcopy(AMAZON_EXCEL)
        elif open_sheet.cell(0,2).value == 'purchase-date' and open_sheet.cell(0,4).value == 'buyer-email':
            order_mapping = copy.deepcopy(AMAZON_EXCEL1)
        elif open_sheet.cell(0,1).value == 'AMB Order No':
            order_mapping = copy.deepcopy(ASKMEBAZZAR_EXCEL)
        elif open_sheet.cell(0,0).value == 'Order Id' and open_sheet.cell(0,1).value == 'Date Time':
            order_mapping = copy.deepcopy(LIMEROAD_EXCEL)

        for row_idx in range(1, open_sheet.nrows):
            sku_id = ''
            sku_index = order_mapping['sku_code']
            cell_data = open_sheet.cell(row_idx, sku_index).value

            title = ''
            if 'title' in order_mapping.keys():
                title_index = order_mapping['title']
                title = str(open_sheet.cell(row_idx, title_index).value)

            if type(cell_data) == float:
                sku_code = str(int(cell_data))
            elif isinstance(cell_data, str) and '.' in cell_data:
                sku_code = str(int(float(cell_data)))
            else:
                sku_code = cell_data.upper()

            sku_master=SKUMaster.objects.filter(sku_code=sku_code,user=user.id)
            if sku_master:
                sku_id = sku_master[0].id
            else:
                market_mapping = ''
                if sku_code:
                    market_mapping = MarketplaceMapping.objects.filter(marketplace_code=sku_code, sku__user=user.id, sku__status=1)
                if not market_mapping and title:
                    market_mapping = MarketplaceMapping.objects.filter(description=title, sku__user=user.id, sku__status=1)
                if market_mapping:
                    sku_id = market_mapping[0].sku_id

            if not sku_id:
                index_status.setdefault(row_idx, set()).add('SKU Mapping Not Available')

        if index_status:
            f_name = fname.name.replace(' ', '_')
            rewrite_excel_file(f_name, index_status, open_sheet)
            return HttpResponse(f_name)

        for row_idx in range(1, open_sheet.nrows):
            if not order_mapping:
                break
            order_data = copy.deepcopy(UPLOAD_ORDER_DATA)

            if not open_sheet.cell(row_idx, 0).value and not order_mapping['marketplace'] == '':
                continue
            for key,value in order_mapping.iteritems():
                if key == 'marketplace':
                    order_data['marketplace'] = order_mapping['marketplace']
                    continue
                if isinstance(value, (list)):
                    cell_data = ''
                    for val in value:
                        if not cell_data:
                            cell_data = str(open_sheet.cell(row_idx, val).value)
                        else:
                            cell_data = str(cell_data) + ", " + str(open_sheet.cell(row_idx, val).value)
                else:
                    cell_data = open_sheet.cell(row_idx, order_mapping[key]).value
                if key == 'order_id':
                    if isinstance(cell_data,float):
                        cell_data = str(int(cell_data))
                    if cell_data:
                        order_id = re.findall('\d+', cell_data)
                        order_code = re.findall('\D+',cell_data)
                        if order_id:
                            order_data['order_id'] = order_id[0]
                        if order_code:
                            order_data['order_code'] = order_code[0]
                        if not order_code:
                            order_data['order_code'] = 'OD'
                    else:
                        order_detail = OrderDetail.objects.filter(order_code='MN',user=request.user.id).order_by('-order_id')
                        if order_detail:
                            order_data['order_id'] = int(order_detail[0].order_id) + 1
                            order_data['order_code'] = 'MN'
                        else:
                            order_data['order_id'] = 1001
                            order_data['order_code'] = 'MN'
                elif key == 'sku_code':
                    if type(cell_data) == float:
                        sku_code = int(cell_data)
                    else:
                        sku_code = cell_data.upper()
                    sku_master=SKUMaster.objects.filter(sku_code=sku_code,user=user.id)
                    if sku_master:
                        order_data['sku_id'] = sku_master[0].id
                    else:
                        market_mapping = ''
                        if sku_code:
                            market_mapping = MarketplaceMapping.objects.filter(marketplace_code=sku_code, sku__user=user.id, sku__status=1)
                        if not market_mapping and order_data['title']:
                            market_mapping = MarketplaceMapping.objects.filter(description=order_data['title'], sku__user=user.id, sku__status=1)
                        if market_mapping:
                            order_data['sku_id'] = market_mapping[0].sku_id
                        else:
                            order_data['sku_id'] = SKUMaster.objects.get(sku_code='TEMP', user=user.id).id
                            order_data['sku_code'] = sku_code
                elif key == 'quantity':
                    try:
                        order_data['quantity'] = int(cell_data)
                    except:
                        order_data['quantity'] = 0
                elif key == 'shipment_date':
                    try:
                        if cell_data and ' ' in cell_data:
                            order_data['shipment_date'] = datetime.datetime.strptime(cell_data, '%d/%m/%Y %H:%M')
                        elif cell_data:
                            order_data['shipment_date'] = datetime.datetime(1899,12,30) + datetime.timedelta(days=cell_data)
                    except:
                        order_data['shipment_date'] = NOW
                else:
                    if cell_data:
                        order_data[key] = cell_data

            if not order_data.get('order_id', ''):
                order_detail = OrderDetail.objects.filter(order_code='MN',user=user.id).order_by('-order_id')
                if order_detail:
                    order_data['order_id'] = int(order_detail[0].order_id) + 1
                    order_data['order_code'] = 'MN'
                else:
                    order_data['order_id'] = 1001
                    order_data['order_code'] = 'MN'

            if not 'quantity' in order_data.keys():
                order_data['quantity'] = 1
            order_data['user'] = user.id
            order_obj = []
            if order_data['sku_id']:
                order_obj = OrderDetail.objects.filter(order_id=order_data['order_id'],sku_id=order_data['sku_id'], user=user.id)
            if not order_obj and order_data['sku_id'] and order_data['quantity']:
                order_detail = OrderDetail(**order_data)
                order_detail.save()
    return HttpResponse('Success')


@csrf_exempt
@login_required
@get_admin_user
def inventory_upload(request, user=''):
    fname = request.FILES['files']
    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')
    status =  validate_inventory_form(open_sheet, str(user.id))

    if status != 'Success':
        return HttpResponse(status)
    RECORDS = list(EXCEL_RECORDS)
    pallet_switch = get_misc_value('pallet_switch', user.id)
    if pallet_switch == 'true' and 'Pallet Number' not in EXCEL_HEADERS:
        EXCEL_HEADERS.append('Pallet Number')
        RECORDS.append('pallet_number')

    for row_idx in range(1, open_sheet.nrows):
        location_data = ''
        inventory_data = {}
        pallet_number = ''
        for col_idx in range(0, len(EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value

            if col_idx == 1:
                year, month, day, hour, minute, second = xldate_as_tuple(cell_data, 0)
                receipt_date = datetime.datetime(year, month, day, hour, minute, second)

            if col_idx == 2 and cell_data:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                data = SKUMaster.objects.filter(wms_code=cell_data, user=user.id)
                inventory_data['sku_id'] = data[0].id
                if not data:
                    break
                continue
            elif col_idx == 2 and not cell_data:
                break

            if not cell_data:
                continue
            data_id = RECORDS[col_idx]
            if data_id in ('wms_code', 'location'):
                cell_data = cell_data.strip().upper()

            if data_id == 'location':
                location_data = cell_data

            if data_id == 'wms_quantity':
                inventory_data['quantity'] = cell_data

            if data_id == 'receipt_number':
                receipt_number = cell_data

            if data_id == 'wms_code':
                wms_id = SKUMaster.objects.get(wms_code=cell_data, user=user.id)
                inventory_data['sku_id'] = wms_id.id
            if data_id == 'pallet_number':
                pallet_number = cell_data
            if data_id == 'receipt_type':
                inventory_data['receipt_type'] = cell_data
        if location_data:
            quantity = inventory_data.get('quantity', 0)
            location_id = check_location(location_data, user.id, quantity)
            inventory_data['location_id'] = location_id

        if inventory_data.get('sku_id', '') and inventory_data.get('location_id', ''):
            if pallet_number:
                pallet_data = {'pallet_code': pallet_number, 'quantity': int(inventory_data['quantity']), 'user': user.id,
                               'status': 1, 'creation_date': str(datetime.datetime.now()), 'updation_date': str(datetime.datetime.now())}
                pallet_detail = PalletDetail(**pallet_data)
                pallet_detail.save()
                inventory_status = StockDetail.objects.filter(sku_id=inventory_data.get('sku_id', ''), location_id=inventory_data.get('location_id', ''), receipt_number=receipt_number, sku__user=user.id, pallet_detail_id=pallet_detail.id)
            else:
                inventory_status = StockDetail.objects.filter(sku_id=inventory_data.get('sku_id', ''), location_id=inventory_data.get('location_id', ''), receipt_number=receipt_number, sku__user=user.id)
            if not inventory_status and inventory_data.get('quantity', ''):
                inventory_data['status'] = 1
                inventory_data['creation_date'] = str(datetime.datetime.now())
                inventory_data['receipt_date'] = receipt_date
                inventory_data['receipt_number'] = receipt_number
                if pallet_switch == 'true' and pallet_number:
                    inventory_data['pallet_detail_id'] = pallet_detail.id
                sku_master = SKUMaster.objects.get(id=inventory_data['sku_id'])
                if not sku_master.zone:
                    location_master = LocationMaster.objects.get(id=inventory_data['location_id'])
                    sku_master.zone_id = location_master.zone_id
                    sku_master.save()
                inventory = StockDetail(**inventory_data)
                inventory.save()

            elif inventory_status and inventory_data.get('quantity', ''):
                inventory_status = inventory_status[0]
                inventory_status.quantity = int(inventory_status.quantity) + int(inventory_data.get('quantity', 0))
                inventory_status.receipt_date = receipt_date
                inventory_status.save()

            location_master = LocationMaster.objects.get(id=inventory_data.get('location_id', ''), zone__user=user.id)
            location_master.filled_capacity += inventory_data.get('quantity', 0)
            location_master.save()

    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def move_inventory_upload(request, user=''):
    fname = request.FILES['files']
    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')

    status = validate_move_inventory_form(open_sheet, str(user.id))
    if status != 'Success':
        return HttpResponse(status)
    cycle_count = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not cycle_count:
        cycle_id = 1
    else:
        cycle_id = cycle_count[0].cycle + 1
    for row_idx in range(1, open_sheet.nrows):
        location_data = ''
        for col_idx in range(0, len(MOVE_INVENTORY_UPLOAD_FIELDS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if col_idx == 0 and cell_data:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                wms_code = cell_data
            elif col_idx == 1:
                source_loc = cell_data
            elif col_idx == 2:
                dest_loc = cell_data
            elif col_idx == 3:
               quantity = int(cell_data)
        move_stock_location(cycle_id, wms_code, source_loc, dest_loc, quantity, user)
    return HttpResponse('Success')

@csrf_exempt
def online_percentage_update(data, quantity, picked):
    sku_online = data.sku.online_percentage
    if sku_online:
        if quantity:
            online_quantity = int(round(float(int(quantity) * sku_online) / 100))
        else:
            online_quantity = int(round(float(int(data.total_quantity) * sku_online) / 100))
    else:
        online_quantity = int(data.total_quantity)
    sku_stock_online = data.online_quantity
    offline_quantity = int(data.total_quantity) - online_quantity
    if sku_stock_online:
        if online_quantity > int(sku_stock_online) or picked == 'true':
            setattr(data, 'online_quantity', online_quantity)
            setattr(data, 'offline_quantity', offline_quantity)
            data.save()
    else:
        setattr(data, 'online_quantity', online_quantity)
        setattr(data, 'offline_quantity', offline_quantity)
        data.save()

def create_temp_stock(sku_code, zone, quantity, stock_detail, user):
    if not quantity:
        quantity = 0
    inventory = StockDetail.objects.filter(sku__sku_code=sku_code, location__zone__zone=zone, sku__user=user)
    if inventory:
        inventory = inventory[0]
        for stock in stock_detail:
            if stock.id == inventory.id:
                setattr(stock, 'quantity', int(stock.quantity) + int(quantity))
                stock.save()
                break
        else:
            setattr(inventory, 'quantity', int(inventory.quantity) + int(quantity))
            inventory.save()
            stock_detail.append(inventory)
    else:
       location_id = LocationMaster.objects.filter(zone__zone=zone, zone__user=user)
       sku_id = SKUMaster.objects.filter(sku_code=sku_code, user=user)
       if sku_id and location_id:
           stock_dict = {'location_id': location_id[0].id, 'receipt_number': 0, 'receipt_date': NOW,
                         'sku_id':sku_id[0].id, 'quantity': quantity, 'status': 1, 'creation_date': NOW}
           stock = StockDetail(**stock_dict)
           stock.save()
           stock_detail.append(stock)
    return stock_detail

def get_picklist_locations(data_dict, user):
    exclude_dict = {'location__lock_status__in': ['Outbound', 'Inbound and Outbound'], 'location__zone__zone__in':['TEMP_ZONE', 'DAMAGED_ZONE']}
    back_order = get_misc_value('back_order', user.id)
    fifo_switch = get_misc_value('fifo_switch', user.id)

    if fifo_switch == 'true':
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0, **data_dict).\
                                                                    order_by('receipt_date', 'location__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0, **data_dict).\
                                                                    order_by('receipt_date', 'location__pick_sequence')
        data_dict['location__zone__zone'] = 'TEMP_ZONE'
        #del exclude_dict['location__zone__zone']
        stock_detail3 = StockDetail.objects.exclude(**exclude_dict).filter(**data_dict).order_by('receipt_date', 'location__pick_sequence')
        stock_detail = list(chain(stock_detail1, stock_detail2, stock_detail3))
    else:
        #del exclude_dict['location__zone__zone']
        stock_detail1 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence__gt=0, **data_dict).\
                                                                    order_by('location_id__pick_sequence')
        stock_detail2 = StockDetail.objects.exclude(**exclude_dict).filter(location_id__pick_sequence=0, **data_dict).order_by('receipt_date')
        stock_detail = list(chain(stock_detail1, stock_detail2))
        if back_order == 'true':
             data_dict['location__zone__zone'] = 'BAY_AREA'
             back_stock = StockDetail.objects.filter(**data_dict)
             stock_detail = list(chain(back_stock, stock_detail))
    return stock_detail


@csrf_exempt
@login_required
@get_admin_user
def generate_picklist(request, user=''):
    remarks = request.POST['ship_reference']
    data = []
    stock_status = ''
    out_of_stock = []
    picklist_number = get_picklist_number(user)

    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(status=1, user=user.id, quantity__gt=0)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by('receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by('location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    sku_stocks = stock_detail1 | stock_detail2
    for key, value in request.POST.iteritems():
        if key in ('sortingTable_length', 'fifo-switch', 'ship_reference', 'remarks'):
            continue

        order_data = OrderDetail.objects.get(id=key,user=user.id)
        stock_status, picklist_number = picklist_generation([order_data], request, picklist_number, user, sku_combos, sku_stocks, status = 'open', remarks=remarks)

        if stock_status:
            out_of_stock = out_of_stock + stock_status

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

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
    if not stock_status:
        data = get_picklist_data(picklist_number + 1, user.id)
        order_status = data[0]['status']
        if order_status == 'open':
            headers.insert(headers.index('WMS Code'),'Order ID')

    return render(request, 'templates/toggle/generate_picklist.html', {'data': data, 'headers': headers, 'picklist_id': picklist_number + 1,
                                                                       'stock_status': stock_status, 'show_image': show_image,
                                                                       'use_imei': use_imei, 'order_status': order_status, 'user': request.user})

def get_picklist_number(user):
    picklist_obj = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id)).values_list('picklist_number',
                                           flat=True).distinct().order_by('-picklist_number')
    if not picklist_obj:
        picklist_number = 1000
    else:
        picklist_number = picklist_obj[0]
    return picklist_number

@fn_timer
def get_sku_stock(request, sku, sku_stocks, user, val_dict, sku_id_stocks=''):
    data_dict = {'sku_id': sku.id, 'quantity__gt': 0}
    stock_detail = sku_stocks.filter(**data_dict)

    stock_count = 0
    if sku.id in val_dict['sku_ids']:
        indices = [i for i, x in enumerate(sku_id_stocks) if x['sku_id'] == sku.id]
        for index in indices:
            stock_count += val_dict['stock_totals'][index]
        if sku.id in val_dict['pic_res_ids']:
            stock_count = stock_count - val_dict['pic_res_quans'][val_dict['pic_res_ids'].index(sku.id)]

    return stock_detail, stock_count, sku.wms_code

def get_stock_count(request, order, stock, stock_diff, user):
    reserved_quantity = PicklistLocation.objects.filter(stock_id=stock.id, status=1, picklist__order__user=user.id).aggregate(Sum('reserved'))['reserved__sum']
    if not reserved_quantity:
        reserved_quantity = 0

    stock_quantity = int(stock.quantity) - reserved_quantity
    if stock_quantity <= 0:
        return '', stock_diff

    if stock_diff:
        if stock_quantity >= stock_diff:
            stock_count = stock_diff
            stock_diff = 0
        else:
            stock_count = stock_quantity
            stock_diff -= stock_quantity
    else:
        if stock_quantity >= order.quantity:
            stock_count = order.quantity
        else:
            stock_count = stock_quantity
            stock_diff = order.quantity - stock_quantity

    return stock_count, stock_diff

def picklist_headers(request, user):
    show_image = 'false'
    use_imei = 'false'
    headers = list(PROCESSING_HEADER)

    data1 = MiscDetail.objects.filter(user=request.user.id, misc_type='show_image')
    if data1:
        show_image = data1[0].misc_value
    if show_image == 'true':
        headers.insert(0, 'Image')

    imei_data = MiscDetail.objects.filter(user=request.user.id, misc_type='use_imei')
    if imei_data:
        use_imei = imei_data[0].misc_value
    if use_imei == 'true':
        headers.insert(-1, 'Serial Number')

    if get_misc_value('pallet_switch', user) == 'true':
        headers.insert(headers.index('Location') + 1, 'Pallet Code')

    return headers, show_image, use_imei

@fn_timer
def picklist_generation(order_data, request, picklist_number, user, sku_combos, sku_stocks, status='', remarks=''):
    stock_status = []
    if not status:
        status = 'batch_open'
    for order in order_data:
        picklist_data = copy.deepcopy(PICKLIST_FIELDS)
        picklist_data['picklist_number'] = picklist_number + 1
        if remarks:
            picklist_data['remarks'] = remarks
        else:
            picklist_data['remarks'] = 'Picklist_' + str(picklist_number + 1)

        sku_id_stocks = sku_stocks.values('id', 'sku_id').annotate(total=Sum('quantity'))
        pick_res_locat = PicklistLocation.objects.prefetch_related('picklist', 'stock').filter(status=1).\
                                          filter(picklist__order__user=user.id).values('stock__sku_id').annotate(total=Sum('reserved'))
        val_dict = {}
        val_dict['pic_res_ids'] = map(lambda d: d['stock__sku_id'], pick_res_locat)
        val_dict['pic_res_quans'] = map(lambda d: d['total'], pick_res_locat)

        val_dict['sku_ids'] = map(lambda d: d['sku_id'], sku_id_stocks)
        val_dict['stock_ids'] = map(lambda d: d['id'], sku_id_stocks)
        val_dict['stock_totals'] = map(lambda d: d['total'], sku_id_stocks)

        members = [ order.sku ]
        if order.sku.relation_type == 'combo':
            picklist_data['order_type'] = 'combo'
            members = []
            combo_data = sku_combos.filter(parent_sku_id=order.sku.id)
            for combo in combo_data:
                members.append(combo.member_sku)

        for member in members:
            stock_detail, stock_quantity, sku_code = get_sku_stock(request, member, sku_stocks, user, val_dict, sku_id_stocks)
            if order.sku.relation_type=='member':
                parent = sku_combos.filter(member_sku_id=member.id).filter(relation_type='member')
                stock_detail1, stock_quantity1, sku_code = get_sku_stock(request, parent[0].parent_sku, sku_stocks, user, val_dict, sku_id_stocks)
                stock_detail = list(chain(stock_detail, stock_detail1))
                stock_quantity += stock_quantity1
            elif order.sku.relation_type=='combo':
                stock_detail, stock_quantity, sku_code = get_sku_stock(request, member, sku_stocks, user, val_dict, sku_id_stocks)

            if stock_quantity < int(order.quantity):
                if get_misc_value('no_stock_switch', user.id) == 'false':
                    stock_status.append(str(member.sku_code))
                    continue
                stock_detail = []
                #stock_detail = create_temp_stock(member.sku_code, 'DEFAULT', int(order.quantity) - stock_quantity, stock_detail, user.id)
                picklist_data['reserved_quantity'] = order.quantity
                picklist_data['stock_id'] =  ''
                picklist_data['order_id'] = order.id
                picklist_data['status'] = status
                if sku_code:
                    picklist_data['sku_code'] = sku_code
                if 'st_po' not in dir(order):
                    new_picklist = Picklist(**picklist_data)
                    new_picklist.save()

                    order.status = 0
                    order.save()
                continue

            stock_diff = 0

            for stock in stock_detail:
                stock_count, stock_diff = get_stock_count(request, order, stock, stock_diff, user)
                if not stock_count:
                    continue

                picklist_data['reserved_quantity'] = stock_count
                picklist_data['stock_id'] = stock.id
                if 'st_po' in dir(order):
                    picklist_data['order_id'] = None
                else:
                    picklist_data['order_id'] = order.id
                picklist_data['status'] = status

                new_picklist = Picklist(**picklist_data)
                new_picklist.save()

                picklist_loc_data = {'picklist_id': new_picklist.id , 'status': 1, 'quantity': stock_count, 'creation_date':   NOW,
                                     'stock_id': new_picklist.stock_id, 'reserved': stock_count}
                po_loc = PicklistLocation(**picklist_loc_data)
                po_loc.save()
                if 'st_po' in dir(order):
                    st_order_dict = copy.deepcopy(ST_ORDER_FIELDS)
                    st_order_dict['picklist_id'] = new_picklist.id
                    st_order_dict['stock_transfer_id'] = order.id
                    st_order = STOrder(**st_order_dict)
                    st_order.save()

                if not stock_diff:
                    setattr(order, 'status', 0)
                    break

            order.save()
    return stock_status, picklist_number



@csrf_exempt
@login_required
@get_admin_user
def batch_generate_picklist(request, user=''):
    remarks = request.POST.get('remarks', '')

    data = []
    order_data = []
    stock_status = ''
    out_of_stock = []
    picklist_number = get_picklist_number(user)

    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(status=1, user=user.id, quantity__gt=0)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by('receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by('location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    sku_stocks = stock_detail1 | stock_detail2
    for key, value in request.POST.iteritems():
        if key in PICKLIST_SKIP_LIST:
            continue

        key = key.split('<>')
        sku_code, marketplace_sku_code = key
        order_filter = {'sku__sku_code': sku_code, 'quantity__gt': 0 }

        if sku_code != marketplace_sku_code:
            order_filter['sku_code'] = marketplace_sku_code

        if request.POST.get('selected'):
            order_filter['marketplace__in'] = request.POST.get('selected').split(',')

        order_detail = all_orders.filter(**order_filter).order_by('shipment_date')

        stock_status, picklist_number = picklist_generation(order_detail, request, picklist_number, user, sku_combos, sku_stocks, remarks=remarks)

        if stock_status:
            out_of_stock = out_of_stock + stock_status

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    headers, show_image, use_imei = picklist_headers(request, user.id)

    order_status = ''
    data = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']
        if order_status == 'open':
            headers.insert(headers.index('WMS Code'),'Order ID')

    return render(request, 'templates/toggle/generate_picklist.html', {'data': data, 'headers': headers,
                           'picklist_id': picklist_number + 1,'stock_status': stock_status, 'show_image': show_image,
                           'use_imei': use_imei, 'order_status': order_status, 'user': request.user})

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
            stock_data = StockDetail.objects.filter(sku__user=w_user.id, sku__sku_code=order.sku.sku_code).aggregate(Sum('quantity'))
            order_data = OrderDetail.objects.filter(user=w_user.id, sku__sku_code=order.sku.sku_code, status=1).aggregate(Sum('quantity'))
            reserved = PicklistLocation.objects.filter(picklist__status__icontains='open', picklist__order__user=w_user.id, picklist__order__sku__sku_code=order.sku.sku_code).aggregate(Sum('reserved'))
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
    return render(request, 'templates/toggle/transfer_toggle.html', {'data': data, 'headers': headers, 'options': options})


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

    return render(request, 'templates/toggle/transfer_toggle.html', {'data': data, 'headers': headers, 'options': options})

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

def get_picklist_data(data_id,user_id):

    picklist_orders = Picklist.objects.filter(Q(order__sku__user=user_id) | Q(stock__sku__user=user_id), picklist_number=data_id)
    pick_stocks = StockDetail.objects.filter(sku__user=user_id)
    data = []
    if not picklist_orders:
        return data
    order_status = ''
    for orders in picklist_orders:
        if 'open' in orders.status:
            order_status = orders.status
    if not order_status:
        order_status = 'picked'
    if order_status == "batch_open":
        batch_data = {}
        for order in picklist_orders:
            stock_id = ''
            wms_code = order.sku_code
            if order.stock:
                stock_id = pick_stocks.get(id=order.stock_id)
            if order.order:
                sku_code = order.order.sku_code
                title = order.order.title
                invoice = order.order.invoice_amount
            else:
                st_order = STOrder.objects.filter(picklist_id=order.id)
                sku_code = ''
                title = st_order[0].stock_transfer.sku.sku_desc
                invoice = st_order[0].stock_transfer.invoice_amount

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
            if order.order.sku:
                image = order.order.sku.image_url
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = stock_id.sku.image_url
                wms_code = stock_id.sku.wms_code

            match_condition = (location, pallet_detail, wms_code, sku_code, title)
            if match_condition not in batch_data:
                if order.reserved_quantity == 0:
                    continue

                batch_data[match_condition] = {'wms_code': wms_code, 'zone': zone, 'sequence': sequence, 'location': location, 'reserved_quantity': int(order.reserved_quantity), 'picklist_number': data_id, 'stock_id': st_id, 'picked_quantity': int(order.picked_quantity), 'id': order.id, 'invoice_amount': invoice, 'price': invoice * order.reserved_quantity, 'image': image, 'order_id': order.order_id, 'status': order.status, 'pallet_code': pallet_code, 'sku_code': sku_code, 'title': title}
            else:
                batch_data[match_condition]['reserved_quantity'] += int(order.reserved_quantity)
                batch_data[match_condition]['invoice_amount'] += invoice
        data = batch_data.values()

        data = sorted(data, key=itemgetter('sequence'))
        return data

    elif order_status == "open":
        for order in picklist_orders:
            stock_id = ''
            if order.order:
                wms_code = order.order.sku.wms_code
                invoice_amount = order.order.invoice_amount
                order_id = order.order.order_id
                sku_code = order.order.sku_code
                title = order.order.title
            else:
                wms_code = order.stock.sku.wms_code
                invoice_amount = 0
                order_id = ''
                sku_code = order.stock.sku.sku_code
                title = order.stock.sku.sku_desc
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
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = stock_id.sku.image_url

            data.append({'wms_code': wms_code, 'zone': zone, 'location': location, 'reserved_quantity': int(order.reserved_quantity), 'picklist_number': data_id, 'stock_id': st_id, 'order_id': order.order_id, 'picked_quantity': int(order.picked_quantity), 'id': order.id, 'sequence': sequence, 'invoice_amount': invoice_amount, 'price': invoice_amount * order.reserved_quantity, 'image': image, 'status': order.status, 'order_no': order_id,'pallet_code': pallet_code, 'sku_code': sku_code, 'title': title})
        data = sorted(data, key=itemgetter('sequence'))
        return data
    else:
        for order in picklist_orders:
            stock_id = ''
            wms_code = order.order.sku.wms_code
            if order.stock_id:
                stock_id = pick_stocks.get(id=order.stock_id)

            zone = 'NO STOCK'
            st_id = 0
            sequence = 0
            location = 'NO STOCK'
            image = ''
            if stock_id:
                zone = stock_id.location.zone.zone
                st_id = order.stock_id
                sequence = stock_id.location.pick_sequence
                location = stock_id.location.location
                image = stock_id.sku.image_url

            if order.reserved_quantity == 0:
                continue

            data.append({'wms_code': wms_code, 'zone': zone, 'location': location, 'reserved_quantity': int(order.reserved_quantity), 'picklist_number': data_id, 'order_id': order.order_id, 'stock_id': st_id, 'picked_quantity': int(order.picked_quantity), 'id': order.id, 'sequence': sequence, 'invoice_amount': order.order.invoice_amount, 'price': order.order.invoice_amount * order.reserved_quantity, 'image': image, 'status': order.status, 'pallet_code': pallet_code, 'sku_code': order.order.sku_code, 'title': order.order.title })
        data = sorted(data, key=itemgetter('sequence'))
        return data

def create_market_mapping(order, val):
    sku_code = val['wmscode']
    market_obj = MarketplaceMapping.objects.filter(sku_type=order.marketplace, marketplace_code=order.sku_code, sku__user=order.user,
                                                   description=order.title)
    sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=order.user)
    if not sku_code == order.sku_code:
        if not sku_master:
            return 'Invalid WMS Code'
        order.sku_id = sku_master[0].id
        order.save()
    if not market_obj and sku_master:
        mapping_data = {'sku_id': sku_master[0].id, 'sku_type': order.marketplace, 'marketplace_code': order.sku_code,
                        'description': order.title, 'creation_date': NOW}
        map_data = MarketplaceMapping(**mapping_data)
        map_data.save()
    stock_detail = StockDetail.objects.filter(sku__sku_code=val['wmscode'], location__location=val['location'], sku__user=order.user,
                                              quantity__gte=val['picked_quantity'])
    if stock_detail:
        return 'true'
    else:
        return 'false'

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
        if int(order.open_po.order_quantity) - int(order.received_quantity) <= 0 and not active_po_loc:
            order.status = 'confirmed-putaway'
        order.save()

def get_picklist_batch(picklist, value, all_picklists):
    if picklist.order and picklist.stock:
        picklist_batch = all_picklists.filter(stock__location__location=value[0]['orig_loc'], stock__sku__wms_code=value[0]['wms_code'],
                                              status__icontains='open', order__sku_code=value[0]['orig_wms'],
                                              order__title=value[0]['title'])
    elif not picklist.stock:
        picklist_batch = all_picklists.filter(order__sku__sku_code=value[0]['wms_code'], order__title=value[0]['title'], stock__isnull=True,
                                              picklist_number=picklist.picklist_number)
        if not picklist_batch:
            picklist_batch = all_picklists.filter(sku_code=value[0]['wms_code'], order__title=value[0]['title'], stock__isnull=True,
                                                  picklist_number=picklist.picklist_number)
    else:
        picklist_batch = all_picklists.filter(Q(stock__sku__wms_code=value[0]['wms_code']) | Q(order_type="combo",
                                              sku_code=value[0]['wms_code']), stock__location__location=value[0]['orig_loc'],
                                              status__icontains='open')
    return picklist_batch

def confirm_no_stock(picklist, p_quantity=0):
    if int(picklist.reserved_quantity) - p_quantity >= 0:
        picklist.reserved_quantity = int(picklist.reserved_quantity) - p_quantity
        picklist.picked_quantity = int(picklist.picked_quantity) + p_quantity
    else:
        picklist.reserved_quantity = 0
        picklist.picked_quantity = p_quantity
    pi_status = 'picked'
    if 'batch_open' in picklist.status:
        pi_status = 'batch_picked'
    if int(picklist.reserved_quantity) <= 0:
        picklist.status = pi_status
    picklist.save()

def validate_location_stock(val, all_locations, all_skus, user):
    status = []
    wms_check = all_skus.filter(wms_code = val['wms_code'],user=user.id)
    loc_check = all_locations.filter(zone__zone = val['zone'] ,location = val['location'],zone__user=user.id )
    if not loc_check:
        status.append("Invalid Location %s" % val['location'])
    pic_check_data = {'sku_id': wms_check[0].id, 'location_id': loc_check[0].id, 'sku__user': user.id, 'quantity__gt': 0}
    if 'pallet' in val and val['pallet']:
        pic_check_data['pallet_detail__pallet_code'] = val['pallet']
    #pic_check = StockDetail.objects.filter(**pic_check_data)
    #if not pic_check:
    #    status.append("Insufficient Stock in given location")
    location = all_locations.filter(zone__zone=val['zone'], location=val['location'],zone__user=user.id)
    if not location:
        if error_string:
            error_string += ', %s' % val['order_id']
        else:
            error_string += "Zone, location match doesn't exists"
        status.append(error_string)
    return pic_check_data, ', '.join(status)

def insert_order_serial(picklist, val):
    imei_nos = list(set(val['imei'].split('\r\n')))
    for imei in imei_nos:
        po_mapping = POIMEIMapping.objects.filter(purchase_order__open_po__sku__sku_code=val['wms_code'], imei_number=imei)
        if imei and po_mapping:
            order_mapping = {'order_id': picklist.order.id, 'po_imei_id': po_mapping[0].id, 'imei_number': ''}
            imei_mapping = OrderIMEIMapping(**order_mapping)
            imei_mapping.save()
        elif imei and not po_mapping:
            order_mapping = {'order_id': picklist.order.id, 'po_imei_id': None, 'imei_number': imei}
            imei_mapping = OrderIMEIMapping(**order_mapping)
            imei_mapping.save() 

def update_picklist_locations(pick_loc, picklist, update_picked, update_quantity=''):
    for pic_loc in pick_loc:
        if int(pic_loc.reserved) >= update_picked:
            pic_loc.reserved = int(pic_loc.reserved) - update_picked
            if update_quantity:
                pic_loc.quantity = int(pic_loc.quantity) - update_picked
            update_picked = 0
        elif int(pic_loc.reserved) < update_picked:
            update_picked = update_picked - pic_loc.reserved
            if update_quantity:
                pic_loc.quantity = 0
            pic_loc.reserved = 0
        if pic_loc.reserved <= 0:
            pic_loc.status = 0
        pic_loc.save()
        if not update_picked:
            break

def update_picklist_pallet(stock, picking_count1):
    pallet = stock.pallet_detail
    if int(pallet.quantity) - picking_count1 >=0:
        pallet.quantity -= picking_count1
    if pallet.quantity == 0:
        stock.pallet_detail_id = None
        pallet.status = 0
        stock.location.pallet_filled -= 1
        if stock.location.pallet_filled < 0:
            stock.location.pallet_filled = 0
        stock.location.save()
        pallet_mapping = PalletMapping.objects.filter(pallet_detail_id = pallet.id)
        if pallet_mapping:
            pallet_mapping[0].status=1
            pallet_mapping[0].save()
    pallet.save()

def send_picklist_mail(picklist, request):
    headers = ['Product Details', 'Seller Details', 'Ordered Quantity', 'Total']
    items = [picklist.stock.sku.sku_desc, request.user.username, picklist.order.quantity, picklist.order.invoice_amount]

    data_dict = {'customer_name': picklist.order.customer_name, 'order_id': picklist.order.order_id,
                 'address': picklist.order.address, 'phone_number': picklist.order.telephone, 'items': items,
                 'headers': headers}

    t = loader.get_template('templates/dispatch_mail.html')
    c = Context(data_dict)
    rendered = t.render(c)

    email = picklist.order.email_id
    if email:
        send_mail([email], 'Order %s on %s is ready to be shipped by the seller' % (picklist.order.order_id, request.user.username), rendered)

@csrf_exempt
@login_required
@get_admin_user
def picklist_confirmation(request, user=''):

    data = {}
    auto_skus = []
    all_data = {}
    for key, value in request.POST.iterlists():
        name, picklist_id = key.rsplit('_', 1)
        data.setdefault(picklist_id, [])
        for index, val in enumerate(value):
            if len(data[picklist_id]) < index + 1:
                data[picklist_id].append({})
            data[picklist_id][index][name] = val

    error_string = ''
    picklist_number = request.POST['picklist_number']
    all_picklists = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id), picklist_number=picklist_number,
                                            status__icontains="open")
    all_skus = SKUMaster.objects.filter(user=user.id)
    all_locations = LocationMaster.objects.filter(zone__user=user.id)
    all_pick_ids = all_picklists.values_list('id', flat=True)
    all_pick_locations = PicklistLocation.objects.filter(picklist__picklist_number=picklist_number, status=1, picklist_id__in=all_pick_ids)
    for key, value in data.iteritems():
        if key in ('name', 'number'):
            continue
        picklist_order_id = value[0]['order_id']
        if picklist_order_id:
            picklist = all_picklists.get(order_id=picklist_order_id)
        else:
            picklist = all_picklists.get(id=key)
        count = 0

        picklist_batch = get_picklist_batch(picklist, value, all_picklists)
        for i in range(0,len(value)):
            if value[i]['picked_quantity']:
                count += int(value[i]['picked_quantity'])

        for val in value:
            if not val['picked_quantity']:
                continue
            else:
                count = int(val['picked_quantity'])

            if picklist_order_id:
                picklist_batch = [picklist]
            for picklist in picklist_batch:
                if count == 0:
                    continue

                if not picklist.stock:
                    confirm_no_stock(picklist, int(val['picked_quantity']))
                    continue

                if val['wms_code'] == 'TEMP' and val['wmscode']:
                    if picklist.order:
                        map_status = create_market_mapping(picklist.order, val)
                    if map_status == 'true':
                        val['wms_code'] = val['wmscode']
                    elif map_status == 'Invalid WMS Code':
                        return HttpResponse(map_status)
                pic_check_data, status = validate_location_stock(val, all_locations, all_skus, user)
                if status:
                    return HttpResponse(status)
                if int(picklist.reserved_quantity) > int(val['picked_quantity']):
                    picking_count = int(val['picked_quantity'])
                else:
                    picking_count = int(picklist.reserved_quantity)
                picking_count1 = picking_count
                wms_id = all_skus.exclude(sku_code='').get(wms_code=val['wms_code'],user=request.user.id)
                total_stock = StockDetail.objects.filter(**pic_check_data)

                if 'imei' in val.keys() and val['imei'] and picklist.order:
                    insert_order_serial(picklist, val)

                reserved_quantity1 = picklist.reserved_quantity
                tot_quan = 0
                for stock in total_stock:
                    tot_quan += int(stock.quantity)
                if tot_quan < reserved_quantity1:
                    total_stock = create_temp_stock(picklist.stock.sku.sku_code, picklist.stock.location.zone, abs(reserved_quantity1 - tot_quan), list(total_stock), user.id)

                for stock in total_stock:

                    pre_stock = int(stock.quantity)
                    if picking_count == 0:
                        break

                    if picking_count > stock.quantity:
                        picking_count -= stock.quantity
                        picklist.reserved_quantity -= stock.quantity

                        stock.quantity = 0
                    else:
                        stock.quantity -= picking_count
                        picklist.reserved_quantity -= picking_count

                        if int(stock.location.filled_capacity) - picking_count >= 0:
                            setattr(stock.location,'filled_capacity',(int(stock.location.filled_capacity) - picking_count))
                            stock.location.save()

                        pick_loc = all_pick_locations.filter(picklist_id=picklist.id,stock__location_id=stock.location_id,status=1)
                        update_picked = picking_count1
                        if pick_loc:
                            update_picklist_locations(pick_loc, picklist, update_picked)
                        else:
                            data = PicklistLocation(picklist_id=picklist.id, stock=stock, quantity=picking_count1, reserved=0, status = 0,
                                                    creation_date=NOW, updation_date=NOW)
                            data.save()
                            exist_pics = all_pick_locations.exclude(id=data.id).filter(picklist_id=picklist.id, status=1, reserved__gt=0)
                            update_picklist_locations(exist_pics, picklist, update_picked, 'true')
                        picking_count = 0
                    if stock.location.zone.zone == 'BAY_AREA':
                        reduce_putaway_stock(stock, picking_count1, user.id)
                    dec_quantity = pre_stock - int(stock.quantity)
                    if stock.pallet_detail:
                        update_picklist_pallet(stock, picking_count1)
                    stock.save()

                picklist.picked_quantity = int(picklist.picked_quantity) + picking_count1
                if picklist.reserved_quantity == 0:
                    if picklist.status == 'batch_open':
                        picklist.status = 'batch_picked'
                    else:
                        picklist.status = 'picked'
                    all_pick_locations.filter(picklist_id=picklist.id, status=1).update(status=0)

                    misc_detail = MiscDetail.objects.filter(user=request.user.id, misc_type='dispatch', misc_value='true')

                    if misc_detail and picklist.order:
                        send_picklist_mail(picklist, request)

                picklist.save()
                count = count - picking_count1
                auto_skus.append(val['wms_code'])

    if get_misc_value('auto_po_switch', user.id) == 'true' and auto_skus:
        auto_po(list(set(auto_skus)),request.user.id)

    return HttpResponse('Picklist Confirmed')


@csrf_exempt
def get_sku_results(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, col_5, col_6, col_7, request, user):
    order_data = SKU_MASTER_HEADERS.values()[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        status_dict = {'active': 1, 'inactive': 0}
        if search_term.lower() in status_dict:
            search_terms = status_dict[search_term.lower()]
            master_data = SKUMaster.objects.filter(status=search_terms, user=user.id).order_by(order_data)
        else:
            master_data = SKUMaster.objects.filter(Q(sku_code__icontains=search_term) | Q(wms_code__icontains=search_term) | Q(sku_desc__icontains=search_term) | Q(sku_type__icontains=search_term) | Q(sku_category__icontains=search_term) | Q(sku_class__icontains=search_term) | Q(zone__zone__icontains=search_term), user=user.id).order_by(order_data)
    else:
        master_data = SKUMaster.objects.filter(user=user.id).order_by(order_data)
    search_params = {}
    if col_1:
        search_params["wms_code__icontains"] = col_1
    if col_2:
        search_params["sku_desc__icontains"] = col_2
    if col_3:
        search_params["sku_type__icontains"] = col_3
    if col_4:
        search_params["sku_category__icontains"] = col_4
    if col_5:
        search_params["sku_class__icontains"] = col_5
    if col_6:
        search_params["zone__zone__icontains"] = col_6
    if col_7:
        if (str(col_7).lower() in "active"):
            search_params["status__icontains"] = 1
        elif (str(col_7).lower() in "inactive"):
            search_params["status__icontains"] = 0
        else:
            search_params["status__icontains"] = "none"
    if search_params:
        search_params["user"] =  user.id
        master_data = SKUMaster.objects.filter(**search_params).distinct().order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        zone = ''
        if data.zone_id:
            zone = data.zone.zone
        temp_data['aaData'].append(OrderedDict(( ('WMS SKU Code', data.wms_code), ('Product Description', data.sku_desc),
                                    ('SKU Type', data.sku_type), ('SKU Category', data.sku_category), ('DT_RowClass', 'results'),
                                    ('Zone', zone), ('SKU Class', data.sku_class), ('Status', status), ('DT_RowAttr', {'data-id': data.id}) )))


@csrf_exempt
def get_sku_stock_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    if order_term:
        if col_num == 4:
            col_num = col_num - 1
        if order_term == 'asc':
            master_data = SKUStock.objects.filter(sku__user=user.id).order_by(SKU_STOCK_HEADERS.values()[col_num])
        elif order_term == 'desc':
            master_data = SKUStock.objects.filter(sku__user=user.id).order_by('-%s' % SKU_STOCK_HEADERS.values()[col_num])
        else:
            master_data = SKUStock.objects.filter(sku__user=user.id)
    if search_term:
        master_data = SKUStock.objects.filter(Q(sku__sku_code__icontains=search_term) | Q(total_quantity__icontains=search_term) | Q(online_quantity__icontains=search_term) | Q(offline_quantity__icontains=search_term), sku__user=user.id)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        open_orders = Picklist.objects.filter(order__sku_id=data.sku_id, status='open')
        reserved_quantity = 0
        for order in open_orders:
            reserved_quantity += order.reserved_quantity

        quantity = int(data.total_quantity) - reserved_quantity
        sku_online = data.sku.online_percentage
        online_percentage_update(data, quantity, 'false')
        if sku_online:
            online_quantity = int(round(float(int(quantity) * sku_online) / 100))
        else:
            online_quantity = int(data.total_quantity)
        if data.status == 0:
            online_quantity = data.online_quantity
        temp_data['aaData'].append({'SKU Code': data.sku.sku_code, 'Total Quantity': quantity, 'Suggested Online Quantity': online_quantity,
                                    'Current Online Quantity': data.online_quantity, 'Offline Quantity': data.offline_quantity,
                                    'DT_RowAttr': {'data-id': data.id}})


@csrf_exempt
def picked_orders(start_index, stop_index, temp_data, search_term, status, order_term, col_num, request, user):
    if search_term:
        master_data = Picklist.objects.filter(Q(picklist_number__icontains=search_term) | Q(remarks__icontains=search_term), order__user=user.id, picked_quantity__gt=0).exclude(status__icontains='batch')
    elif order_term:
        order_data = PICK_LIST_HEADERS.values()[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = Picklist.objects.filter(picked_quantity__gt=0, order__user=user.id).exclude(status__icontains='batch').order_by(order_data)
    else:
        master_data = Picklist.objects.filter(picked_quantity__gt=0, order__user=user.id).exclude(status__icontains='batch')
    data_dict = {}
    picklist_count = []
    final_data = []
    for data in master_data:
        if data.picklist_number in picklist_count:
            continue
        picklist_count.append(data.picklist_number)
        final_data.append(data)

    temp_data['recordsTotal'] = len(final_data)
    temp_data['recordsFiltered'] = len(final_data)
    for data in final_data[start_index:stop_index]:
        picklist_id = PicklistLocation.objects.filter(picklist_id=data.id, picklist__order__user=user.id)
        dat = 'Picklist ID '
        temp_data['aaData'].append({'DT_RowAttr': {'data-id': data.picklist_number}, dat: data.picklist_number, 'Picklist Note': data.remarks,
                                    'Date': str(data.creation_date).split('+')[0], 'DT_RowClass': 'results'})

@csrf_exempt
def open_orders(start_index, stop_index, temp_data, search_term, status, order_term, col_num, request, user):

    filter_params = {'status__icontains': status}
    if 'open' in status:
        filter_params['reserved_quantity__gt'] = 0
    if status == 'batch_picked':
        col_num = col_num - 1
    if search_term:
        master_data = Picklist.objects.filter( Q(picklist_number__icontains = search_term) | Q( remarks__icontains = search_term ),
                                               Q(order__sku__user = user.id) | Q(stock__sku__user=user.id), **filter_params).\
                                       values('picklist_number', 'remarks').distinct()

    elif order_term:
        order_data = PICK_LIST_HEADERS.values()[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = Picklist.objects.filter(Q(order__sku__user = user.id) | Q(stock__sku__user=user.id), **filter_params).\
                                       values('picklist_number', 'remarks').distinct().order_by(order_data)
    else:
        master_data = Picklist.objects.filter( Q(order__sku__user = user.id) | Q(stock__sku__user=user.id), **filter_params).\
                                       values('picklist_number', 'remarks').distinct()

    temp_data['recordsTotal'] = len( master_data )
    temp_data['recordsFiltered'] = len( master_data )

    all_picks = Picklist.objects.filter(Q(order__sku__user = user.id) | Q(stock__sku__user=user.id))
    for data in master_data[start_index:stop_index]:
        create_date = all_picks.filter(picklist_number=data['picklist_number'])[0].creation_date
        result_data = OrderedDict(( ('DT_RowAttr', { 'data-id': data['picklist_number'] }), ('Picklist Note', data['remarks']),
                                    ('Date', get_local_date(request.user, create_date)), ('DT_RowClass', 'results') ))
        if 'open' in status:
            dat = 'Picklist ID'
        elif status == 'picked':
            dat = 'Picklist ID '
        else:
            dat = 'Picklist ID  '
            checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data['picklist_number'], data['picklist_number'])
            result_data[''] = checkbox
        result_data[dat] = data['picklist_number']
        temp_data['aaData'].append(result_data)


@csrf_exempt
def batch_picked_orders(start_index, stop_index, temp_data, search_term, status, order_term, col_num, request, user):
    status = 'batch'
    if search_term:
        master_data = Picklist.objects.filter(Q(picklist_number__icontains=search_term, status__icontains=status) | Q(remarks__icontains=search_term, status__icontains=status, picked_quantity__gt=0), order__user=user.id)
    elif order_term:
        order_data = PICK_LIST_HEADERS.values()[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = Picklist.objects.filter(status__contains=status, order__user=user.id, picked_quantity__gt=0).order_by(order_data)
    else:
        master_data = Picklist.objects.filter(order__user=user.id, picked_quantity__gt=0)
    data_dict = {}
    picklist_count = []
    final_data = []
    for data in master_data:
        if data.picklist_number in picklist_count:
            continue

        picklist_count.append(data.picklist_number)
        final_data.append(data)

    temp_data['recordsTotal'] = len( final_data )
    temp_data['recordsFiltered'] = len( final_data )

    for data in final_data[start_index:stop_index]:
        picklist_id = PicklistLocation.objects.filter(picklist_id=data.id,picklist__order__user=request.user.id)
        dat = "Picklist ID  "
        checkbox = "<input type='checkbox' name='%s' value='%s'>" % (data.picklist_number, data.picklist_number)
        temp_data["aaData"].append({"DT_RowAttr": { "data-id": data.picklist_number },'': checkbox, dat : data.picklist_number, "Picklist Note": data.remarks, "Date": str(data.creation_date).split("+")[0], "DT_RowClass": "results"})


@csrf_exempt
def get_returned_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    if search_term:
        master_data = OrderDetail.objects.filter(Q(order_id__icontains=search_term) | Q(sku__sku_code__icontains=search_term) | Q(customer_id__icontains=search_term), user=user.id, status='RETURNS')
    elif order_term:
        if col_num == 5 or col_num == 4:
            col_num = col_num - 2
        if order_term == 'asc':
            master_data = OrderDetail.objects.filter(user=user.id, status='RETURNS').order_by(CANCEL_ORDER_HEADERS.values()[col_num])
        else:
            master_data = OrderDetail.objects.filter(user=user.id, status='RETURNS').order_by('-%s' % CANCEL_ORDER_HEADERS.values()[col_num])
    else:
        master_data = OrderDetail.objects.filter(user=user.id, status='RETURNS')
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append({'DT_RowAttr': {'data-id': data.id},
                                    '': '<input type="checkbox" name="%s" value="%s">' % (data.id, data.quantity), 'Order ID': data.order_id,
                                    'SKU Code': data.sku.sku_code, 'Customer ID': data.customer_id,
                                    'Return Quantity': '<input type="text" name="return_quantity" class="smallbox">',
                                    'Damaged Quantity': '<input type="text" name="damaged_quantity" class="smallbox">',
                                    'DT_RowClass': 'results'})


@csrf_exempt
def get_cancelled_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    if search_term:
        master_data = OrderDetail.objects.filter(Q(order_id__icontains=search_term) | Q(sku__sku_code__icontains=search_term) | Q(customer_id__icontains=search_term), user=user.id, status__icontains='CANCELLED')
    elif order_term:
        if col_num == 5 or col_num == 4:
            col_num = col_num - 2
        if order_term == 'asc':
            master_data = OrderDetail.objects.filter(user=user.id, status__icontains='CANCELLED').order_by(CANCEL_ORDER_HEADERS.values()[col_num])
        else:
            master_data = OrderDetail.objects.filter(user=user.id, status__icontains='CANCELLED').order_by('-%s' % CANCEL_ORDER_HEADERS.values()[col_num])
    else:
        master_data = OrderDetail.objects.filter(user=user.id, status__icontains='CANCELLED')
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        picked_data = Picklist.objects.filter(order_id=data.id)
        if picked_data:
            if picked_data[0].status == 'dispatched':
                input_damage = '<input type="text" name="damaged_quantity" class="smallbox">'
            else:
                input_damage = '<input type="text" name="damaged_quantity" class="smallbox" readonly>'
            temp_data['aaData'].append({'DT_RowAttr': {'data-id': data.id},
                                        '': '<input type="checkbox" name="%s" value="%s">' % (data.id, data.quantity),'Order ID': data.order_id,
                                        'SKU Code': data.sku.sku_code, 'Customer ID': data.customer_id,
                                        'Return Quantity': '<input type="text" name="return_quantity" class="smallbox">',
                                        ' Damaged Quantity': input_damage, 'DT_RowClass': 'results'})


@csrf_exempt
def get_move_inventory(start_index, stop_index, temp_data, search_term, status, request, user):
    cycle_count = CycleCount.objects.filter(status='checked', sku__user=user.id)
    ids_list = []
    negative_items = []
    positive_items = []
    move_items = []
    for count in cycle_count:
        if count.quantity > count.seen_quantity:
            negative_items.append(count)
        elif count.quantity < count.seen_quantity:
            positive_items.append(count)

    for positive in positive_items[:]:
        positive_difference = positive.seen_quantity - positive.quantity
        positive_sku = positive.sku_id
        for negative in negative_items[:]:
            negative_difference = negative.quantity - negative.seen_quantity
            negative_sku = negative.sku_id
            if positive_sku == negative_sku:
                if positive_difference >= negative_difference:
                    positive_difference -= negative_difference
                    move_items.append((positive, negative, negative_difference))
                    negative_items.remove(negative)

            if positive_difference == 0:
                positive_items.remove(positive)
                break    
    all_data = []
    if status == 'adj':
        total_items = positive_items + negative_items
        for positive in total_items:
            data_dict = {'cycle_id': positive.id, 'adjusted_location': '', 'adjusted_quantity': positive.seen_quantity,
                         'reason': '', 'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}
            data = InventoryAdjustment.objects.filter(cycle_id=positive.id, cycle__sku__user=user.id)
            if not data:
                data = InventoryAdjustment(**data_dict)
                data.save()
            all_data.append(positive)
        temp_data['recordsTotal'] = len(all_data)
        temp_data['recordsFiltered'] = len(all_data)
        for positive in all_data[start_index:stop_index]:
            checkbox = "<input type='checkbox' name='%s' value='%s'>" % (positive.id, positive.id)
            temp_data['aaData'].append({'': checkbox, 'Location': positive.location.location, 'WMS Code': positive.sku.wms_code,
                                        'Description': positive.sku.sku_desc, 'Total Quantity': positive.quantity,
                                        'Physical Quantity': positive.seen_quantity, 'Reason': "<input type='text'>",
                                        'DT_RowClass': 'results'})
    else:
        for items in move_items[start_index:stop_index]:
            data_dict = {'cycle_id': items[0].id, 'adjusted_location': items[1].location_id, 'adjusted_quantity': items[2],
                         'reason': '', 'creation_date': datetime.datetime.now(), 'updation_date': datetime.datetime.now()}
            data = InventoryAdjustment.objects.filter(cycle_id=items[0].id, cycle__sku__user=user.id)
            if not data:
                data = InventoryAdjustment(**data_dict)
                data.save()
                data = InventoryAdjustment.objects.filter(cycle_id=items[0].id, cycle__sku__user=user.id)
            checkbox = "<input type='checkbox' name='%s' value='%s'>" % (items[0].id, items[1].id)
            temp_data['aaData'].append({'': checkbox, 'Source Location': items[0].location.location, 'WMS Code': items[0].sku.wms_code,
                                        'Description': items[0].sku.sku_desc, 'Destination Location': items[1].location.location,
                                        'Move Quantity': items[2], 'Reason': '', 'DT_RowClass': 'results'})
        temp_data['recordsTotal'] = len(move_items)
        temp_data['recordsFiltered'] = len(move_items)


@csrf_exempt
def get_cycle_count(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, request, user):
    order_data = CYCLE_COUNT_HEADERS.values()[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        cycle_data = StockDetail.objects.filter(Q(sku__wms_code__icontains=search_term, status=1, quantity__gt=0) | Q(location__zone__zone__icontains=search_term, status=1, quantity__gt=0) | Q(location__location__icontains=search_term, status=1, quantity__gt=0) | Q(quantity__icontains=search_term, status=1, quantity__gt=0), sku__user=user.id).values('sku__wms_code', 'location__location', 'location__zone__zone').distinct()
    else:
        if 'quantity' in order_data:
            order_data = order_data.replace('quantity', 'total')
        cycle_data = StockDetail.objects.filter(status=1,sku__user=user.id, quantity__gt=0).values('sku__wms_code', 'location__location',
                                    'location__zone__zone').distinct().annotate(total=Sum('quantity')).order_by(order_data)
    search_params = {}
    if col_1:
        search_params['sku__wms_code__iexact'] = col_1
    if col_2:
        search_params['location__zone__zone__iexact'] = col_2
    if col_3:
        search_params['location__location__iexact'] = col_3
    if col_4:
        search_params['total'] = col_4

    if search_params:
        search_params['status'] = 1
        search_params['sku__user'] = user.id
        search_params['quantity__gt'] = 0
        if 'total' in search_params:
            cycle_data = StockDetail.objects.annotate(total=Sum('quantity')).filter(**search_params).values('sku__wms_code',
                                                 'location__location', 'location__zone__zone','total').distinct().order_by(order_data)
        else:
            cycle_data = StockDetail.objects.filter(**search_params).values('sku__wms_code', 'location__location', 'location__zone__zone').\
                                             annotate(total=Sum('quantity')).order_by(order_data)

    temp_data['recordsTotal'] = len(cycle_data)
    temp_data['recordsFiltered'] = len(cycle_data)
    for data in cycle_data[start_index:stop_index]:
        if 'total' in data:
            quantity = data['total']
        else:
            quantity = StockDetail.objects.filter(status=1,sku__user=user.id,**data).values(*data.keys()).distinct().\
                                           aggregate(Sum('quantity'))['quantity__sum']
        temp_data['aaData'].append(OrderedDict(( ('WMS Code', data['sku__wms_code']), ('Zone', data['location__zone__zone']),
                                                 ('Location', data['location__location']), ('Quantity', quantity) )))


@csrf_exempt
def get_supplier_results(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, col_5, col_6, request, user):
    order_data = SUPPLIER_MASTER_HEADERS.values()[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        search_dict = {'active': 1, 'inactive': 0}
        if search_term.lower() in search_dict:
            search_terms = search_dict[search_term.lower()]
            master_data = SupplierMaster.objects.filter(status = search_terms,user=user.id).order_by(order_data)

        else:
            master_data = SupplierMaster.objects.filter( Q(id__icontains = search_term) | Q(name__icontains = search_term) | Q(address__icontains = search_term) | Q(phone_number__icontains = search_term) | Q(email_id__icontains = search_term),user=user.id ).order_by(order_data)

            master_data = SupplierMaster.objects.filter(Q(id__icontains=search_term) | Q(name__icontains=search_term) | Q(address__icontains=search_term) | Q(phone_number__icontains=search_term) | Q(email_id__icontains=search_term), user=user.id)
    else:
        master_data = SupplierMaster.objects.filter(user=user.id).order_by(order_data)
    search_params = {}
    if col_1:
        search_params["id__icontains"] = col_1
    if col_2:
        search_params["name__icontains"] = col_2
    if col_3:
        search_params["address__icontains"] = col_3
    if col_4:
        search_params["phone_number__icontains"] = col_4
    if col_5:
        search_params["email_id__icontains"] = col_5
    if col_6:
        if (str(col_6).lower() in "active"):
            search_params["status__iexact"] = 1
        elif (str(col_6).lower() in "inactive"):
            search_params["status__iexact"] = 0
        else:
            search_params["status__iexact"] = "none"
    if search_params:
        search_params["user"] = user.id
        master_data = SupplierMaster.objects.filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)

    for data in master_data[start_index : stop_index]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        temp_data['aaData'].append(OrderedDict(( ('Supplier ID', data.id), ('Name', data.name), ('Address', data.address),
                                                 ('Phone Number', data.phone_number), ('Email', data.email_id), ('Status', status),
                                                 ('DT_RowId', data.id), ('DT_RowClass', 'results') )))

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
    myDict = dict(request.GET.iterlists())
    for i in range(0, len(myDict['wms_code'])):
        price = 0
        if myDict['price'][i]:
            price = myDict['price'][i]
        if i < len(myDict['data-id']):
            purchase_order = OpenPO.objects.get(id=myDict['data-id'][i], sku__user=user.id)
            sup_id = myDict['data-id'][i]
            setattr(purchase_order, 'order_quantity', myDict['order_quantity'][i])
            setattr(purchase_order, 'price', myDict['price'][i])
            setattr(purchase_order, 'po_name', myDict['po_name'][0])
            setattr(purchase_order, 'supplier_code', myDict['supplier_code'][i])
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
            po_suggestions['order_quantity'] = myDict['order_quantity'][i]
            po_suggestions['price'] = float(price)
            po_suggestions['status'] = 'Manual'

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
        if purchase_order.sku.wms_code == 'TEMP':
            wms_code = purchase_order.wms_code
        else:
            wms_code = purchase_order.sku.wms_code
        po_data.append((wms_code, myDict['supplier_code'][i], purchase_order.sku.sku_desc, purchase_order.order_quantity,
                        purchase_order.price, amount))
        suggestion = OpenPO.objects.get(id=sup_id, sku__user=user.id)
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
            'name': name, 'order_date': order_date, 'total': total, 'po_reference': po_reference, 'company_name': profile.company_name, 'location': profile.location}
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
    import pdb;pdb.set_trace()

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

        data = OpenPO(**po_suggestions)
        data.save()

    status_msg="Updated Successfully"
    return HttpResponse(status_msg)

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
    exclude_zones_list = ['QC_ZONE', 'DAMAGED_ZONE']
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
    exclude_dict = {'location__exact': '', 'lock_status__in': ['Inbound', 'Inbound and Outbound']}
    filter_params = {'zone__zone': put_zone, 'zone__user': user}
    if sku_group and locations:
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

    location1 = LocationMaster.objects.exclude(**exclude_dict).filter(fill_sequence__gt=min_max[0], **filter_params).order_by('fill_sequence')
    location11 = LocationMaster.objects.exclude(**exclude_dict).filter(fill_sequence__lt=min_max[0], **filter_params).order_by('fill_sequence')
    location2 = LocationMaster.objects.exclude(**exclude_dict).filter(**cond1).order_by('fill_sequence')
    if put_zone not in ['QC_ZONE', 'DAMAGED_ZONE']:
        location1 = list(chain(stock_locations,location1))
    location2 = list(chain(location1, location11, location2))

    if 'pallet_capacity' in exclude_dict.keys():
        del exclude_dict['pallet_capacity']

    location3 = LocationMaster.objects.exclude(**exclude_dict).filter(**cond2)
    del exclude_dict['location__exact']
    del filter_params['zone__zone']
    location4 = LocationMaster.objects.exclude(Q(location__exact='') | Q(zone__zone=put_zone), **exclude_dict).\
                                       exclude(zone__zone__in=exclude_zones_list).filter(**filter_params).order_by('fill_sequence')

    location = list(chain(location2, location3, location4))

    return location

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

@csrf_exempt
@get_admin_user
def add_lr_details(request, user=''):
    lr_number = request.GET['lr_number']
    carrier_name = request.GET['carrier_name']
    po_id = request.GET['po_id']
    po_data = PurchaseOrder.objects.filter(order_id=po_id, open_po__sku__user=user.id)
    for data in po_data:
        lr_details = LRDetail(lr_number=lr_number, carrier_name=carrier_name, quantity=data.received_quantity, creation_date=NOW, updation_date=NOW, purchase_order_id=data.id)
        lr_details.save()

    return HttpResponse('success')

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
@get_admin_user
def supplier_code_mapping(request, myDict, i, data, user=''):
    sku_master = SKUMaster.objects.filter(wms_code=myDict['wms_code'][i].upper(), user=user.id)
    if sku_master:
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

    order_data = {'order_quantity': order_quantity, 'price': price, 'wms_code': sku.wms_code,
                  'sku_code': sku.sku_code, 'supplier_id': user_data.id, 'zone': sku.zone,
                  'qc_check': sku.qc_check, 'supplier_name': username,
                  'sku_desc': sku.sku_desc, 'address': address,
                  'phone_number': user_data.phone_number, 'email_id': email_id,
                  'sku_group': sku.sku_group, 'sku_id': sku.id, 'sku': sku, 'temp_wms': temp_wms }

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
        pallet_map = {'pallet_detail_id': save_pallet.id, 'po_location_id': po_location_id.id,'creation_date': NOW, 'status': status}
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
def confirm_quality_check(request, user=''):
    scan_data = request.POST.get("qc_scan",'')
    myDict = dict(request.POST.iterlists())
    total_sum = sum(int(i) for i in myDict['accepted_quantity'] + myDict['rejected_quantity'])
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
                order_data = get_purchase_order_data(data.purchase_order)

                if (int(data.purchase_order.received_quantity) - value) < 0:
                    status = 'Putaway quantity should be less than the Received Quantity'

                if back_order == "true":
                    sku_code = order_data['sku_code']
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
        if int(stock.quantity) > quantity:
            setattr(stock, 'quantity', int(stock.quantity) - quantity)
            stock.save()
        else:
            setattr(stock, 'quantity', 0)
            stock.save()

def putaway_location(data, value, exc_loc, user, order_id, po_id):
    diff_quan = 0
    if int(data.quantity) >= int(value):
        diff_quan = int(data.quantity) - int(value)
        data.quantity = diff_quan
    if diff_quan == 0:
        data.status = 0
    if not data.location_id == exc_loc:
        if int(data.original_quantity) - value >= 0:
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


@csrf_exempt
@login_required
@get_admin_user
def returns_putaway_data(request, user=''):
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
        quantity = int(myDict['quantity'][i])
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
            stock_data = StockDetail.objects.filter(location_id=location_id[0].id, receipt_number=receipt_number, sku_id=sku_id,
                                                    sku__user=user.id)
            if stock_data:
                stock_data = stock_data[0]
                setattr(stock_data, 'quantity', int(stock_data.quantity) + quantity)
                stock_data.save()
            else:
                stock_dict = {'location_id': location_id[0].id, 'receipt_number': receipt_number, 'receipt_date': NOW,
                              'sku_id':sku_id, 'quantity': quantity, 'status': 1,
                              'creation_date': NOW, 'updation_date': NOW}
                new_stock = StockDetail(**stock_dict)
                new_stock.save()
            returns_data.quantity = int(returns_data.quantity) - int(quantity)
            if returns_data.quantity <= 0:
                returns_data.status = 0
            if not returns_data.location_id == location_id[0].id:
                setattr(returns_data, 'location_id', location_id[0].id)
            returns_data.save()
            status = 'Updated Successfully'

    return HttpResponse(status)



@csrf_exempt
@login_required
def sales_returns(request):
    if not permissionpage(request,'add_orderreturns'):
        return render(request, 'templates/permission_denied.html')
    return render(request, 'templates/order_returns.html', {'headers': SALES_RETURN_HEADERS, 'toggle_fields': SALES_RETURN_FIELDS,
                                                            'return_fields': SALES_RETURN_TOGGLE})

@csrf_exempt
@login_required
def get_returns_page(request):
    return render(request, 'templates/toggle/scan_returns.html', {'toggle_fields': SALES_RETURN_FIELDS, 'return_fields': SALES_RETURN_TOGGLE})


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
            returns.save()

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

@csrf_exempt
def update_returns_data(request):
    data_dict = dict(request.GET.iterlists())
    for i in range(0, len(data_dict['id'])):
        if not data_dict['id'][i]:
            data_dict['id'][i], status = create_return_order(data_dict, i , data_dict['user_id'][i])
    return HttpResponse('Success')


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


@csrf_exempt
@login_required
@get_admin_user
def confirm_cycle_count(request, user=''):
    stocks = []
    search_params = {}
    stock_data = []
    myDict = dict(request.GET.iterlists())
    for i in range(0,len(myDict['wms_code'])):
        search_params['sku__user'] = user.id
        search_params['status'] = 1
        search_params['quantity__gt'] = 0
        if myDict['wms_code'][i]:
            search_params['sku_id__wms_code'] = myDict['wms_code'][i]
        if myDict['zone'][i]:
            search_params['location__zone__zone'] = myDict['zone'][i]
        if myDict['location'][i]:
            search_params['location_id__location'] = myDict['location'][i]
        if myDict['quantity'][i]:
            search_params['total'] = myDict['quantity'][i]

        if search_params:
            stock_values = StockDetail.objects.values('sku_id', 'location_id', 'location__zone_id').distinct().\
                                               annotate(total=Sum('quantity')).filter(**search_params)
            for value in stock_values:
                del value['total']
                stocks = list(chain(stocks,(StockDetail.objects.filter(**value))))

    if 'search_term' in request.GET.keys() and not stocks:
        search_term = request.GET['search_term']
        if search_term:
            stocks = StockDetail.objects.filter(Q(sku__wms_code__icontains=search_term, status=1, quantity__gt=0) |
                                                Q(location__zone__zone__icontains=search_term, status=1, quantity__gt=0) |
                                                Q(location__location__icontains=search_term, status=1, quantity__gt=0) |
                                                Q(quantity__icontains=search_term, status=1, quantity__gt=0), sku__user=user.id)
    data = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not data:
        cycle_id = 1
    else:
        cycle_id = data[0].cycle + 1

    now = str(datetime.datetime.now())

    location_wise = {}
    saved_data = []
    for data in stocks:
        location_wise.setdefault(data.location_id, {})
        location_wise[data.location_id].setdefault(data.sku_id, 0)
        location_wise[data.location_id][data.sku_id] += data.quantity

    for location, sku_list in location_wise.iteritems():
        for sku, quantity in sku_list.iteritems():
            data_dict = copy.deepcopy(CYCLE_COUNT_FIELDS)
            data_dict['cycle'] = cycle_id
            data_dict['sku_id'] = sku
            data_dict['location_id'] = location
            data_dict['quantity'] = quantity
            data_dict['seen_quantity'] = 0
            data_dict['creation_date'] = now
            data_dict['updation_date'] = now

            dat = CycleCount(**data_dict)
            dat.save()

            saved_data.append(dat)
    return render(request, 'templates/toggle/cycle_form.html', {'data': saved_data, 'cycle_id': dat.cycle})

def move_stock_location(cycle_id, wms_code, source_loc, dest_loc, quantity, user):
    sku = SKUMaster.objects.filter(wms_code=wms_code, user=user.id)
    if sku:
        sku_id = sku[0].id
    else:
        return 'Invalid WMS Code'
    source = LocationMaster.objects.filter(location=source_loc, zone__user=user.id)
    if not source:
        return 'Invalid Source'
    dest = LocationMaster.objects.filter(location=dest_loc, zone__user=user.id)
    if not dest:
        return 'Invalid Destination'

    if quantity:
        move_quantity = int(quantity)
    else:
        return 'Quantity should not be empty'
    stocks = StockDetail.objects.filter(sku_id=sku_id, location_id=source[0].id, sku__user=user.id)
    stock_count = stocks.aggregate(Sum('quantity'))['quantity__sum']
    reserved_quantity = PicklistLocation.objects.exclude(stock=None).filter(stock__sku_id=sku_id, stock__sku__user=user.id, status=1,
                                                         stock__location_id=source[0].id).aggregate(Sum('reserved'))['reserved__sum']
    if reserved_quantity:
        if (stock_count - reserved_quantity) < int(quantity):
            return 'Source Quantity reserved for Picklist'
    for stock in stocks:
        if stock.quantity > move_quantity:
            stock.quantity -= move_quantity
            move_quantity = 0
            stock.save()
        elif stock.quantity <= move_quantity:
            move_quantity -= stock.quantity
            stock.quantity = 0
            stock.save()
        if move_quantity == 0:
            break

    dest_stocks = StockDetail.objects.filter(sku_id=sku_id, location_id=dest[0].id, sku__user=user.id)
    if not dest_stocks:
        dest_stocks = StockDetail(receipt_number=1, receipt_date=datetime.datetime.now(), quantity=int(quantity), status=1,
                                  creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now(), location_id=dest[0].id,
                                  sku_id=sku_id)
        dest_stocks.save()
    else:
        dest_stocks = dest_stocks[0]
        dest_stocks.quantity += int(quantity)
    dest_stocks.save()

    data_dict = copy.deepcopy(CYCLE_COUNT_FIELDS)
    data_dict['cycle'] = cycle_id
    data_dict['sku_id'] = sku_id
    data_dict['location_id'] = source[0].id
    data_dict['quantity'] = quantity
    data_dict['seen_quantity'] = 0
    data_dict['status'] = 0
    data_dict['creation_date'] = NOW
    data_dict['updation_date'] = NOW

    cycle_instance = CycleCount.objects.filter(cycle=cycle_id, location_id=source[0].id, sku_id=sku_id)
    if not cycle_instance:
        dat = CycleCount(**data_dict)
        dat.save()
    else:
        cycle_instance = cycle_instance[0]
        cycle_instance.quantity = int(cycle_instance.quantity) + quantity
        cycle_instance.save()
    data_dict['location_id'] = dest[0].id
    data_dict['quantity'] = quantity
    cycle_instance = CycleCount.objects.filter(cycle=cycle_id, location_id=dest[0].id, sku_id=sku_id)
    if not cycle_instance:
        dat = CycleCount(**data_dict)
        dat.save()
    else:
        cycle_instance = cycle_instance[0]
        cycle_instance.quantity = int(cycle_instance.quantity) + quantity
        cycle_instance.save()

    data = copy.deepcopy(INVENTORY_FIELDS)
    data['cycle_id'] = cycle_id
    data['adjusted_location'] = dest[0].id
    data['adjusted_quantity'] = quantity
    data['creation_date'] = NOW
    data['updation_date'] = NOW

    inventory_instance = InventoryAdjustment.objects.filter(cycle_id=cycle_id, adjusted_location=dest[0].id)
    if not inventory_instance:
        dat = InventoryAdjustment(**data)
        dat.save()
    else:
        inventory_instance = inventory_instance[0]
        inventory_instance.adjusted_quantity += int(inventory_instance.adjusted_quantity) + quantity
        inventory_instance.save()

    return 'Added Successfully'

@csrf_exempt
@login_required
@get_admin_user
def insert_move_inventory(request, user=''):
    data = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
    if not data:
        cycle_id = 1
    else:
        cycle_id = data[0].cycle + 1

    now = str(datetime.datetime.now())
    wms_code = request.GET['wms_code']
    source_loc = request.GET['source_loc']
    dest_loc = request.GET['dest_loc']
    quantity = request.GET['quantity']
    status = move_stock_location(cycle_id, wms_code, source_loc, dest_loc, quantity, user)

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
    if get_misc_value('auto_po_switch', user.id) == 'true':
        auto_po([wmscode],request.user.id)

    return HttpResponse(status)

@csrf_exempt
@login_required
def inventory_adjustment(request):
    if not permissionpage(request,'add_inventoryadjustment'):
        return render(request, 'templates/permission_denied.html')
    return render(request, 'templates/inventory_adjustment.html')

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
def get_batch_picked(data_ids, user_id):
    data = {}
    batch_data = {}
    for data_id in data_ids:
        picklist_orders = Picklist.objects.filter(picklist_number=data_id, stock__sku__user=user_id)
        if picklist_orders[0].status != 'batch_picked':
            return data

        for order in picklist_orders:
            stock_id = StockDetail.objects.get(id=order.stock_id,sku__user=user_id)
            if order.order:
                marketplace = order.order.marketplace
                invoice_amount = order.order.invoice_amount
            else:
                st_order = STOrder.objects.filter(picklist_id=order.id)
                marketplace = ''
                invoice_amount = st_order[0].stock_transfer.invoice_amount
            match_condition = (marketplace, stock_id.sku.wms_code)
            if match_condition not in batch_data:

                batch_data[match_condition] = {'wms_code': stock_id.sku.wms_code, 'picked_quantity':order.picked_quantity,
                                               'invoice_amount': invoice_amount }
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
    return render(request, 'templates/toggle/print_segregation.html', {'data': data, 'picklist_number': data_id, 'headers': ('WMS Code', 'Picked Quantity', 'invoice_amount')})

@csrf_exempt
def webhook(request):
    msg = {}
    msg["status"] = "Fail"
    if request.body:
        pprint.pprint(request.POST)
        pprint.pprint(request.body)
    return HttpResponse('Success')


@login_required
@get_admin_user
def validate_wms(request, user=''):
    myDict = dict(request.GET.iterlists())
    wms_list = ''
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


@login_required
@get_admin_user
def check_imei(request, user=''):
    status = ''
    for key, value in request.GET.iteritems():
        picklist = Picklist.objects.get(id=key)
        if not picklist.order:
            continue
        po_mapping = POIMEIMapping.objects.filter(imei_number=value, purchase_order__open_po__sku__user=user.id, purchase_order__open_po__sku__sku_code=picklist.order.sku.sku_code)
        if not po_mapping:
            status = str(value) + ' is invalid for this sku'
        order_mapping = OrderIMEIMapping.objects.filter(po_imei__imei_number=value, order__user=user.id)
        if order_mapping:
            status = str(value) + ' is already mapped with another order'

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

def add_extra_permissions(user):
    add_permissions = ['Inbound', 'Outbound']
    permission_dict = {'Inbound': ['openpo', 'purchaseorder', 'polocation'], 'Outbound': ['orderdetail', 'picklist', 'picklistlocation'],
                       'Stock Adjustment': ['inventoryadjustment']}
    for key, value in permission_dict.iteritems():
        group, created = Group.objects.get_or_create(name=key)
        for perm in value:
            permissions = Permission.objects.filter(codename__icontains=perm)
            for permission in permissions:
                group.permissions.add(permission)
            if key in add_permissions:
                user.groups.add(group)


@csrf_exempt
@login_required
@get_admin_user
def add_user(request, user=''):
    status = 'Username already exists'
    user_dict = {}
    for key,value in request.GET.iteritems():
        if not key == 're_password':
            user_dict[key] = value
    user_exists = User.objects.filter(username=user_dict['username'])
    if not user_exists:
        new_user = User.objects.create_user(**user_dict)
        admin_group = AdminGroups.objects.filter(user_id=user.id)
        if admin_group:
            group = admin_group[0].group
        else:
            group,created = Group.objects.get_or_create(name=user.username)
            admin_dict = {'group_id': group.id, 'user_id': user.id}
            admin_group  = AdminGroups(**admin_dict)
            admin_group.save()
            user.groups.add(group)
        new_user.groups.add(group)
        add_extra_permissions(new_user)
        new_user.groups.add(group)
        status = 'Added Successfully'
    return HttpResponse(status)


@csrf_exempt
@login_required
@get_admin_user
def add_group(request, user=''):
    selected_list = ''
    group = ''
    selected = request.POST.get('selected')
    if selected:
        selected_list = selected.split(',')
    name = request.POST.get('name')
    group_exists = Group.objects.filter(name=name)
    if group_exists:
         return HttpResponse('Group Name already exists')
    if not group_exists and selected_list:
        group,created = Group.objects.get_or_create(name=name)
        for perm in selected_list:
            permissions = Permission.objects.filter(codename__icontains=perm)
            for permission in permissions:
                group.permissions.add(permission)
        user.groups.add(group)
    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
def update_user(request):
    exclude_name = ''
    selected_list = []
    data_id = request.GET['id']
    user = User.objects.get(id=data_id)
    selected = request.GET.get('perms')
    if selected:
        selected_list = selected.split(',')
    user_groups = request.user.groups.filter()
    exclude_group = AdminGroups.objects.filter(user_id=request.user.id)
    if exclude_group:
        exclude_name = exclude_group[0].group.name
    for group in user_groups:
        if group.name in selected_list:
            user.groups.add(group)
        else:
            if exclude_name:
                if not group.name == exclude_name:
                    group.user_set.remove(user)
    if request.GET['first_name']:
        user.first_name = request.GET['first_name']
        user.save()
    return HttpResponse('Updated Successfully')

def get_extra_data(excel_headers, result_data, user):
    data = []
    if 'Product SKU Code' in excel_headers and 'Product Description' in excel_headers:
        excel_headers = ['Product SKU Code', 'Product SKU Description', 'Material SKU Code','Material SKU Description', 'Material Quantity',
                         'Unit of Measurement']
        for i in result_data:
            data_id = i['DT_RowAttr']['data-id']
            bom_data = BOMMaster.objects.filter(product_sku__sku_code=data_id, product_sku__user=user.id)
            for bom in bom_data:
                data.append(OrderedDict(( ('Product SKU Code', bom.product_sku.sku_code), ('Product SKU Description', bom.product_sku.sku_desc),
                                       ('Material SKU Code',bom.material_sku.wms_code), ('Material SKU Description', bom.material_sku.sku_desc),
                                          ('Material Quantity', bom.material_quantity), ('Unit of Measurement', bom.unit_of_measurement) )))

    elif 'WMS SKU Code' in excel_headers and excel_headers.index('WMS SKU Code') == 0:
        excel_headers = excel_headers + ['Market Place', 'Market Place SKU', 'Market Place Description']
        for idx, i in enumerate(result_data):
            market_data = MarketplaceMapping.objects.filter(sku__wms_code=i['WMS SKU Code'], sku__user=user.id)
            for index, dat in enumerate(market_data):
                result = copy.deepcopy(i)
                result['Market Place'] = dat.sku_type
                result['Market Place SKU'] = dat.marketplace_code
                result['Market Place Description'] = dat.description
                data.append(result)
            if not market_data:
                data.append(i)
    if data:
        result_data = data

    return excel_headers, result_data

@csrf_exempt
@login_required
@get_admin_user
def print_excel(request, temp_data, headers, excel_name='', user=''):
    excel_headers = ''
    if temp_data['aaData']:
        excel_headers = temp_data['aaData'][0].keys()
    if '' in headers:
        headers = filter(lambda a: a != '', headers)
    if not excel_headers:
        excel_headers = headers
    for i in set(excel_headers) - set(headers):
        excel_headers.remove(i)
    excel_headers, temp_data['aaData'] = get_extra_data(excel_headers, temp_data['aaData'], user)
    wb, ws = get_work_sheet('skus', excel_headers)
    data_count = 0
    for data in temp_data['aaData']:
        data_count += 1
        column_count = 0
        for key, value in data.iteritems():
            if key in excel_headers:
                ws.write(data_count, column_count, value)
                column_count += 1
    if not excel_name:
        excel_name = request.POST.get('serialize_data', '')
    if excel_name:
        file_name = "%s.%s" % (user.id, excel_name.split('=')[-1])
    else:
        file_name = "%s.%s" % (user.id, wms_data)
    path = 'static/excel_files/' + file_name + '.xls'
    wb.save(path)
    path_to_file = '../' + path
    return HttpResponse(path_to_file)

@csrf_exempt
@login_required
@get_admin_user
def back_orders(request, user=''):
    headers = BACK_ORDER_TABLE
    if get_misc_value('production_switch', user.id) == 'true' and 'In Production Quantity' not in headers:
        headers.insert(-1, 'In Production Quantity')
    return render(request, 'templates/back_orders.html',{'headers': headers})

@csrf_exempt
def get_back_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    is_production = get_misc_value('production_switch', user.id)
    user = user
    order_detail = OrderDetail.objects.filter(user=user.id, status=1, quantity__gt=0).values('sku__wms_code', 'sku__sku_code', 'title').distinct()
    master_data = []
    for order in order_detail:
        temp = {}
        production_quantity = 0
        transit_quantity = 0
        stock_quantity = StockDetail.objects.filter(sku__sku_code=order['sku__sku_code'],
                                                sku__user=user.id).aggregate(Sum('quantity'))['quantity__sum']
        reserved_quantity = PicklistLocation.objects.filter(stock__sku__sku_code=order['sku__sku_code'],
                                                            stock__sku__user=user.id).aggregate(Sum('reserved'))['reserved__sum']
        order_quantity = OrderDetail.objects.filter(sku__sku_code=order['sku__sku_code'],
                                                    title=order['title'], status=1).aggregate(Sum('quantity'))['quantity__sum']
        purchase_order = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                               filter(open_po__sku__user=user.id, open_po__sku__sku_code=order['sku__wms_code']).\
                                               values('open_po__sku__sku_code').annotate(total_order=Sum('open_po__order_quantity'),
                                               total_received=Sum('received_quantity'))
        if is_production == 'true':
            production_orders = JobOrder.objects.filter(product_code__sku_code=order['sku__sku_code'], product_code__user=user.id).\
                                                   exclude(status__in=['open', 'confirmed-putaway']).values('product_code__sku_code').\
                                                   annotate(total_order=Sum('product_quantity'), total_received=Sum('received_quantity'))
            if production_orders:
                production_order = production_orders[0]
                diff_quantity = int(production_order['total_order']) - int(production_order['total_received'])
                if diff_quantity > 0:
                    production_quantity = diff_quantity
        if purchase_order:
            purchase_order = purchase_order[0]
            diff_quantity = int(purchase_order['total_order']) - int(purchase_order['total_received'])
            if diff_quantity > 0:
                transit_quantity = diff_quantity
        if not stock_quantity:
            stock_quantity = 0
        if not reserved_quantity:
            reserved_quantity = 0
        if not order_quantity:
            order_quantity = 0
        procured_quantity = order_quantity - stock_quantity - transit_quantity - production_quantity
        if procured_quantity > 0:
            checkbox = "<input type='checkbox' id='back-checked' name='%s'>" % order['title']
            temp  = {'': checkbox, 'WMS Code': order['sku__wms_code'], 'Ordered Quantity': order_quantity,
                                'Stock Quantity': stock_quantity, 'Transit Quantity': transit_quantity,
                                'Procurement Quantity': procured_quantity, 'DT_RowClass': 'results'}
            if is_production == 'true':
                temp['In Production Quantity'] = production_quantity
            master_data.append(temp)
    if search_term:
        master_data = filter(lambda person: search_term in person['WMS Code'] or search_term in str(person['Ordered Quantity']) or\
               search_term in str(person['Stock Quantity']) or search_term in str(person['Transit Quantity']) or \
               search_term in str(person['Procurement Quantity']), master_data)
    elif order_term:
        if order_term == 'asc':
            master_data = sorted(master_data, key = lambda x: x[BACK_ORDER_TABLE[col_num-1]])
        else:
            master_data = sorted(master_data, key = lambda x: x[BACK_ORDER_TABLE[col_num-1]], reverse=True)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    temp_data['aaData'] = master_data[start_index:stop_index]

@csrf_exempt
@get_admin_user
def generate_po_data(request, user=''):
    data_dict = []
    supplier_list = []
    suppliers = SupplierMaster.objects.filter(user=request.user.id)
    for supplier in suppliers:
        supplier_list.append({'id': supplier.id, 'name': supplier.name})
    for key,value in request.POST.iteritems():
        price = 0
        key = key.split(":")
        selected_item = ''
        sku_supplier = SKUSupplier.objects.filter(sku__wms_code=key[0], sku__user=request.user.id)
        if sku_supplier:
            selected_item = {'id': sku_supplier[0].supplier_id, 'name': sku_supplier[0].supplier.name}
            price = sku_supplier[0].price
        data_dict.append({'wms_code': key[0], 'title': key[1] , 'quantity': value, 'selected_item': selected_item, 'price': price})
    return render(request, 'templates/toggle/back_order_toggle.html',{'data_dict': data_dict, 'headers': BACK_ORDER_HEADER,
                                                                      'supplier_list': supplier_list})

@csrf_exempt
def confirm_back_order(request):
    all_data = {}
    status = ''
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['wms_code'])):
        if not (data_dict['quantity'][i] and data_dict['supplier_id'][i]):
            continue
        cond = (data_dict['supplier_id'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append(( data_dict['wms_code'][i], data_dict['quantity'][i], data_dict['title'][i], data_dict['price'][i]))

    for key,value in all_data.iteritems():
        order_id = 1
        purchase_order_id = PurchaseOrder.objects.filter(open_po__sku__user=request.user.id).order_by('-order_id')
        if purchase_order_id:
            order_id = int(purchase_order_id[0].order_id) + 1

        for val in value:
            price = 0
            sku_master = SKUMaster.objects.get(wms_code=val[0], user=request.user.id)
            supplier_master = SupplierMaster.objects.get(id=key, user=request.user.id)
            prefix = UserProfile.objects.get(user_id=request.user.id).prefix
            sku_supplier = SKUSupplier.objects.filter(sku__wms_code=val[0], supplier_id=key, sku__user=request.user.id)
            if val[3]:
                price = float(val[3])
            open_po_dict = copy.deepcopy(PO_SUGGESTIONS_DATA)

            open_po_dict['sku_id'] = sku_master.id
            open_po_dict['supplier_id'] = supplier_master.id
            open_po_dict['order_quantity'] = int(val[1])
            open_po_dict['price'] = price
            open_po_dict['status'] = 0
            open_po = OpenPO(**open_po_dict)
            open_po.save()

            purchase_order_dict = copy.deepcopy(PO_DATA)
            purchase_order_dict['order_id'] = order_id
            purchase_order_dict['open_po_id'] = open_po.id
            purchase_order_dict['po_date'] = NOW
            purchase_order_dict['prefix'] = prefix
            purchase_order = PurchaseOrder(**purchase_order_dict)
            purchase_order.save()
        if not status:
            status = "Created PO Numbers are " + str(order_id)
        else:
            status += ", " + str(order_id)
    return HttpResponse(status)

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
        rw_purchase = RWPurchase.objects.exclude(purchase_order__status__in=['confirmed-putaway', 'stock-transfer']).\
                                         filter(purchase_order__order_id=value, rwo__job_order__product_code__wms_code=key,
                                                rwo__vendor__user=user.id).\
                                              values_list('purchase_order_id', flat=True)
        st_purchase = list(chain(st_purchase, rw_purchase))
        if st_purchase:
            del filter_params['purchase_order__open_po__sku__wms_code']
            filter_params['purchase_order_id__in'] = st_purchase


        quality_check_data = QualityCheck.objects.filter(**filter_params)
        if not quality_check_data:
            return HttpResponse("WMS Code not found for quality check")
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
    return render(request, 'templates/toggle/wms_wise_qc.html', {'data_dict': qc_data, 'sku_data': sku_data, 'image': image,
                                                                 'headers': QC_WMS_HEADER, 'options': REJECT_REASONS, 'use_imei': use_imei})


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

@csrf_exempt
@get_admin_user
def raise_jo(request, user=''):
    if get_misc_value('production_switch', user.id) == 'false':
        return render(request, 'templates/permission_denied.html')
    filter_params = {'user': user.id}
    return render(request, 'templates/raise_jo.html', {'headers': RAISE_JO_TABLE_HEADERS})

@csrf_exempt
@login_required
@get_admin_user
def raise_jo_toggle(request, user=''):
    filter_params = {'user': user.id}
    title = 'Raise Job Order'
    return render(request, 'templates/toggle/update_jo.html', {'headers': RAISE_JO_HEADERS, 'title': title})

def get_job_code(user):
    jo_code = JobOrder.objects.filter(product_code__user=user).order_by('-job_code')
    if jo_code:
        job_code = int(jo_code[0].job_code) + 1
    else:
        job_code = 1
    return job_code

def get_jo_reference(user):
    jo_code = JobOrder.objects.filter(product_code__user=user).order_by('-jo_reference')
    if jo_code:
        jo_reference = int(jo_code[0].jo_reference) + 1
    else:
        jo_reference = 1
    return jo_reference


def insert_jo(all_data, user, jo_reference, vendor_id=''):
    for key,value in all_data.iteritems():
        job_order_dict = copy.deepcopy(JO_PRODUCT_FIELDS)
        if not value:
            continue
        product_sku = SKUMaster.objects.get(wms_code = key, user=user)
        job_instance = JobOrder.objects.filter(jo_reference=jo_reference, product_code__sku_code=key, product_code__user=user)
        if not job_instance:
            product_quantity = int(value[0].keys()[0])
            job_order_dict['product_code_id'] = product_sku.id
            job_order_dict['product_quantity'] = product_quantity
            job_order_dict['jo_reference'] = jo_reference
            job_order = JobOrder(**job_order_dict)
            job_order.save()
            if vendor_id:
                insert_rwo(job_order.id, vendor_id)
                job_order.status = 'RWO'
                job_order.save()
        else:
            job_order = job_instance[0]
            job_order.product_quantity = int(value[0].keys()[0])
            job_order.save()
        for idx,val in enumerate(value):
            for k,data in val.iteritems():
                if data[2]:
                    sku = SKUMaster.objects.get(sku_code=data[0], user=user)
                    jo_material = JOMaterial.objects.get(id=data[2])
                    jo_material.material_quantity = int(float(data[1]))
                    jo_material.material_code_id = sku.id
                    jo_material.save()
                    continue
                jo_material_dict = copy.deepcopy(JO_MATERIAL_FIELDS)
                material_sku = SKUMaster.objects.get(wms_code = data[0], user=user)
                jo_material_dict['material_code_id'] = material_sku.id
                jo_material_dict['job_order_id'] = job_order.id
                jo_material_dict['material_quantity'] = int(float(data[1]))
                jo_material = JOMaterial(**jo_material_dict)
                jo_material.save()
                all_data[key][idx][k][2] = jo_material.id
    return all_data

def validate_jo(all_data, user, jo_reference):
    sku_status = ''
    other_status = ''
    for key,value in all_data.iteritems():
        if not value:
            continue
        product_sku = SKUMaster.objects.filter(wms_code = key, sku_type__in=['FG', 'RM'],user=user)
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
                material_sku = SKUMaster.objects.filter(wms_code = data[0], sku_type='RM',user=user)
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
                    reserved_quantity += int(float(raw_reserved))
                diff = stock_quantity - reserved_quantity
                if diff < int(float(data[1])):
                    if not status:
                        status = "Insufficient stock for " + data[0]
                    else:
                        status += ', ' + data[0]
    return status

@csrf_exempt
@login_required
@get_admin_user
def save_jo(request, user=''):
    all_data = {}
    jo_reference = request.POST.get('jo_reference','')
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
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i], data_dict['material_quantity'][i], data_id ]})
    status = validate_jo(all_data, user.id, '')
    if not status:
        all_data = insert_jo(all_data, user.id, jo_reference)
        status = "Added Successfully"
    return HttpResponse(status)

@csrf_exempt
def get_open_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['id', 'jo_reference', 'creation_date']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id, status='open').order_by(order_data).\
                                       values_list('jo_reference', flat=True)
    if search_term:
        master_data = JobOrder.objects.filter(Q(job_code__icontains=search_term, status='open'), product_code__user=user.id).\
                                       values_list('jo_reference', flat=True).order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        data = JobOrder.objects.filter(jo_reference=data_id, product_code__user=user.id, status='open')[0]
        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        temp_data['aaData'].append({'': checkbox, 'JO Reference': data.jo_reference, 'Creation Date': str(data.creation_date).split('+')[0],
                                    'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.jo_reference}})

@csrf_exempt
def get_generated_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['material_picklist__jo_material__job_order__job_code', 'material_picklist__creation_date', 'material_picklist_id']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = RMLocation.objects.filter(material_picklist__jo_material__material_code__user=user.id, material_picklist__status='open',
                                 status=1).order_by(order_data).values_list('material_picklist__jo_material__job_order__job_code',
                                 flat=True).distinct()
    if search_term:
        master_data = RMLocation.objects.filter(Q(material_picklist__jo_material__job_order__job_code__icontains=search_term,
                                                material_picklist__status='open'), material_picklist__jo_material__material_code__user=user.id,
                                               status=1).values_list('material_picklist__jo_material__job_order__job_code', flat=True).\
                                               order_by(order_data).distinct()

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = master_data.count()
    for data_id in master_data[start_index:stop_index]:
        data = MaterialPicklist.objects.filter(jo_material__job_order__job_code=data_id, jo_material__material_code__user=user.id,
                                               status='open')[0]
        order_type = 'Job Order'
        rw_purchase = RWOrder.objects.filter(job_order_id=data.jo_material.job_order.id)
        if rw_purchase:
            order_type = 'Returnable Work Order'
        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        temp_data['aaData'].append({'': checkbox, 'Job Code ': data.jo_material.job_order.job_code,
                                    'Creation Date': str(data.creation_date).split('+')[0], 'Order Type': order_type, 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'data-id': data.jo_material.job_order.job_code}})

@csrf_exempt
def get_jo_confirmed(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['job_code', 'creation_date', 'id']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id, status='order-confirmed').\
                                               order_by(order_data).values_list('job_code', flat=True)
    if search_term:
        master_data = JobOrder.objects.filter(Q(job_code__icontains=search_term, status='order-confirmed'),
                                                product_code__user=user.id).values_list('job_code', flat=True).order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        data = JobOrder.objects.filter(job_code=data_id, product_code__user=user.id, status='order-confirmed')[0]
        order_type = 'Job Order'
        rw_purchase = RWOrder.objects.filter(job_order_id=data.id)
        if rw_purchase:
            order_type = 'Returnable Work Order'
        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        temp_data['aaData'].append({'': checkbox, 'Job Code  ': data.job_code,
                                    'Creation Date': str(data.creation_date).split('+')[0], 'Order Type': order_type, 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'data-id': data.job_code}})


@csrf_exempt
@login_required
@get_admin_user
def generated_jo_data(request, user=''):
    jo_reference = request.GET['data_id']
    all_data = {}
    title = "Update Job Order"
    record = JobOrder.objects.filter(jo_reference=jo_reference, product_code__user=user.id, status='open')
    for rec in record:
        jo_material = JOMaterial.objects.filter(job_order_id= rec.id,status=1)
        cond = (rec.product_code.sku_code, rec.product_quantity)
        for jo_mat in jo_material:
            all_data.setdefault(cond, [])
            all_data[cond].append({'material_code': jo_mat.material_code.sku_code, 'material_quantity': jo_mat.material_quantity,
                                   'id': jo_mat.id })
    return render(request, 'templates/toggle/update_jo.html', {'data': all_data, 'headers': RAISE_JO_HEADERS, 'jo_reference': jo_reference,
                                                               'title': title})

def save_jo_locations(all_data, user, job_code):
    for key,value in all_data.iteritems():
        job_order = JobOrder.objects.filter(job_code=job_code, product_code__wms_code=key, product_code__user=user.id)
        for val in value:
            for data in val.values():
                jo_material = JOMaterial.objects.get(id=data[2])
                data_dict = {'sku_id': jo_material.material_code_id, 'quantity__gt': 0, 'sku__user': user.id}
                stock_detail = get_picklist_locations(data_dict, user)
                stock_diff = 0
                material_picklist_dict = copy.deepcopy(MATERIAL_PICKLIST_FIELDS)
                material_picklist_dict['jo_material_id'] = jo_material.id
                material_picklist_dict['reserved_quantity'] = int(jo_material.material_quantity)
                material_picklist = MaterialPicklist(**material_picklist_dict)
                material_picklist.save()

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

                    stock_quantity = int(stock.quantity) - reserved_quantity
                    if stock_quantity <= 0:
                        continue
                    if stock_diff:
                        if stock_quantity >= stock_diff:
                            stock_count = stock_diff
                            stock_diff = 0
                        else:
                            stock_count = stock_quantity
                            stock_diff -= stock_quantity
                    elif stock_quantity >= jo_material.material_quantity:
                        stock_count = jo_material.material_quantity
                    else:
                        stock_count = stock_quantity
                        stock_diff = jo_material.material_quantity - stock_quantity

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
def confirm_jo(request, user=''):
    all_data = {}
    sku_list = []
    tot_mat_qty = 0
    tot_pro_qty = 0
    jo_reference = request.POST.get('jo_reference','')
    if not jo_reference:
        jo_reference = get_jo_reference(user.id)
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['product_code'])):
        p_quantity = data_dict['product_quantity'][i]
        if data_dict['product_code'][i] not in sku_list and p_quantity:
            sku_list.append(data_dict['product_code'][i])
            tot_pro_qty += int(float(p_quantity))
        if not data_dict['product_code'][i] or not data_dict['material_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        tot_mat_qty += int(float(data_dict['material_quantity'][i]))
        cond = (data_dict['product_code'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i], data_dict['material_quantity'][i], data_id ]})
    status = validate_jo(all_data, user.id, jo_reference)
    if not status:
        all_data = insert_jo(all_data, user.id, jo_reference)
        job_code = get_job_code(user.id)
        confirm_job_order(all_data, user.id, jo_reference, job_code)
        #save_jo_locations(all_data, user, job_code)
    if status:
        return HttpResponse(status)
    creation_date = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id)[0].creation_date
    user_profile = UserProfile.objects.get(user_id=user.id)
    user_data = {'company_name': user_profile.company_name, 'username': user.first_name, 'location': user_profile.location}

    return render(request, 'templates/toggle/jo_template.html', {'tot_mat_qty': tot_mat_qty, 'tot_pro_qty': tot_pro_qty, 'all_data': all_data,
                                                                 'creation_date': creation_date, 'job_code': job_code, 'user_data': user_data,
                                                                 'headers': RAISE_JO_HEADERS})

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
    data_id = request.POST['rem_id']
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
def confirm_jo_group(request, user=''):
    job_data = {}
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['id'])):
        tot_mat_qty = 0
        tot_pro_qty = 0
        all_data = {}
        sku_list = []
        jo_reference = data_dict['id'][i]
        job_order = JobOrder.objects.filter(jo_reference=jo_reference, product_code__user=user.id)
        job_code = get_job_code(user.id)
        for order in job_order:
            p_quantity = order.product_quantity
            if order.product_code.sku_code not in sku_list and p_quantity:
                sku_list.append(order.product_code.sku_code)
                tot_pro_qty += int(p_quantity)
            jo_material = JOMaterial.objects.filter(job_order__id=order.id, material_code__user=user.id)
            for material in jo_material:
                data_id = material.id
                cond = (order.product_code.wms_code)
                all_data.setdefault(cond, [])
                all_data[cond].append({order.product_quantity: [material.material_code.wms_code, material.material_quantity, data_id ]})
                tot_mat_qty += int(material.material_quantity)
        c_date = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id)
        if c_date:
            creation_date = c_date[0].creation_date
        else:
            creation_date = NOW
        job_data[job_code] = { 'all_data': all_data, 'tot_pro_qty': tot_pro_qty, 'tot_mat_qty': tot_mat_qty, 'creation_date': creation_date}
        status = validate_jo(all_data, user.id, jo_reference)
    if not status:
        confirm_job_order(all_data, user.id, jo_reference, job_code)
        #status = save_jo_locations(all_data, user, job_code)
        status = "Confirmed Successfully"
    else:
        return HttpResponse(status)
    user_profile = UserProfile.objects.get(user_id=user.id)
    user_data = {'company_name': user_profile.company_name, 'username': user.username, 'location': user_profile.location}

    return render(request, 'templates/toggle/jo_template_group.html', {'job_data': job_data, 'user_data': user_data, 'headers': RAISE_JO_HEADERS})

@csrf_exempt
@login_required
@get_admin_user
def delete_jo_group(request, user=''):
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['id'])):
        jo_reference = data_dict['id'][i]
        job_order = JobOrder.objects.filter(jo_reference=jo_reference, product_code__user=user.id)
        delete_jo_list(job_order)
    return HttpResponse("Deleted Successfully")

@csrf_exempt
@login_required
@get_admin_user
def rm_picklist(request, user=''):
    if get_misc_value('production_switch', user.id) == 'false':
        return render(request, 'templates/permission_denied.html')
    filter_params = {'user': user.id}
    return render(request, 'templates/rm_picklist.html', {'headers': RM_CONFIRMED_HEADERS})

def get_raw_picklist_data(data_id, user):
    data = []
    batch_data = {}
    material_picklist = MaterialPicklist.objects.filter(jo_material__job_order__job_code=data_id,
                                                        jo_material__job_order__product_code__user=user.id, status='open')
    for picklist in material_picklist:
        picklist_locations = RMLocation.objects.filter(material_picklist_id=picklist.id, status=1)
        for location in picklist_locations:
            match_condition = (location.stock.location.location, location.stock.pallet_detail, picklist.jo_material.material_code.sku_code)
            if match_condition not in batch_data:
                pallet_detail = location.stock.pallet_detail
                if pallet_detail:
                    pallet_code = location.stock.pallet_detail.pallet_code
                else:
                    pallet_code = ''
                if picklist.reserved_quantity == 0:
                   continue
                batch_data[match_condition] = {'wms_code': location.material_picklist.jo_material.material_code.sku_code,
                                               'zone': location.stock.location.zone.zone, 'sequence': location.stock.location.pick_sequence,
                                               'location': location.stock.location.location,
                                               'reserved_quantity': location.reserved, 'job_code': picklist.jo_material.job_order.job_code,
                                               'stock_id': location.stock_id, 'picked_quantity': location.reserved,
                                               'pallet_code': pallet_code, 'id': location.id,
                                               'title': location.material_picklist.jo_material.material_code.sku_desc,
                                               'image': picklist.jo_material.material_code.image_url}
            else:
                batch_data[match_condition]['reserved_quantity'] += int(location.reserved)
                batch_data[match_condition]['picked_quantity'] += int(location.reserved)

    for key, value in batch_data.iteritems():
        data.append(value)

    data = sorted(data, key=itemgetter('sequence'))
    return data



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

    return render(request, 'templates/toggle/view_raw_picklist.html', {'data': data, 'headers': headers, 'job_code': data_id,
                                                                       'show_image': show_image, 'user': request.user})

def validate_picklist(data, user):
    loc_status = ''
    stock_status = ''
    for key, value in data.iteritems():
        raw_loc = RMLocation.objects.get(id=key)
        sku = raw_loc.material_picklist.jo_material.material_code
        for val in value:
            location = val['location']
            zone = val['zone']
            loc_obj = LocationMaster.objects.filter(location=location, zone__zone=zone, zone__user=user)
            if not loc_obj:
                if not loc_status:
                    loc_status = 'Invalid Location and Zone combination (%s,%s)' % (zone, location)
                else:
                    loc_status += ', (%s,%s)' % (zone, location)
            stock_dict = {'sku_id': sku.id, 'location__location': location, 'sku__user': user}
            stock_quantity = StockDetail.objects.filter(**stock_dict).aggregate(Sum('quantity'))['quantity__sum']
            if not stock_quantity:
                stock_quantity = 0
            if stock_quantity < int(float(val['picked_quantity'])):
                if not stock_status:
                    stock_status = "Insufficient stock for " + sku.wms_code
                elif sku.wms_code not in stock_status:
                    stock_status += ', ' + sku.wms_code
    if stock_status:
        loc_status = loc_status + ' ' + stock_status
    return loc_status

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
        po_dict = {'order_id': po_id, 'received_quantity': 0, 'saved_quantity': 0, 'po_date': NOW, 'ship_to': '',
                   'status': '', 'prefix': prefix, 'creation_date': NOW}
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

@csrf_exempt
@login_required
@get_admin_user
def rm_picklist_confirmation(request, user=''):
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
        raw_loc = RMLocation.objects.get(id=key)
        picklist = raw_loc.material_picklist
        count = 0
        for val in value:
            count += int(float(val['picked_quantity']))
        for val in value:
            if not val['picked_quantity'] or int(float(val['picked_quantity'])) == 0:
                continue
            sku = picklist.jo_material.material_code
            location = LocationMaster.objects.filter(location=val['location'], zone__zone=val['zone'], zone__user=user.id)
            if not location:
                return HttpResponse("Invalid Location and Zone combination")
            stock_dict = {'sku_id': sku.id, 'location_id': location[0].id, 'sku__user': request.user.id}
            stock_detail = StockDetail.objects.filter(**stock_dict)
            picking_count = int(float(val['picked_quantity']))
            picking_count1 = picking_count
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

                    if int(stock.location.filled_capacity) - picking_count1 >= 0:
                        setattr(stock.location, 'filled_capacity', int(stock.location.filled_capacity) - picking_count1)
                        stock.location.save()

                    pick_loc = RMLocation.objects.filter(material_picklist_id=picklist.id, stock__location_id=stock.location_id,
                                                         material_picklist__jo_material__material_code__user=user.id, status=1)
                    update_picked = picking_count1
                    if pick_loc:
                        update_picklist_locations(pick_loc, picklist, update_picked)
                    else:
                        data = RMLocation(material_picklist_id=picklist.id, stock=stock, quantity=picking_count1, reserved=0,
                                          status = 0, creation_date=NOW, updation_date=NOW)
                        data.save()
                        exist_pics = RMLocation.objects.exclude(id=data.id).filter(material_picklist_id=picklist.id, status=1, reserved__gt=0)
                        update_picklist_locations(exist_pics, picklist, update_picked, 'true')

                    picklist.picked_quantity = int(picklist.picked_quantity) + picking_count1
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
        if picklist.reserved_quantity == 0:
            picklist.status = 'picked'
        picklist.save()

        material = MaterialPicklist.objects.filter(jo_material__job_order_id=picklist.jo_material.job_order_id, status='open',
                                                   jo_material__material_code__user=user.id)
        if not material:
            picklist.jo_material.job_order.status = 'pick_confirm'
            picklist.jo_material.job_order.save()
            rw_order = RWOrder.objects.filter(job_order_id=picklist.jo_material.job_order_id, vendor__user=user.id)
            if rw_order:
                rw_order = rw_order[0]
                picklist.jo_material.job_order.status = 'confirmed-putaway'
                insert_rwo_po(rw_order, request, user)

    if get_misc_value('auto_po_switch', user.id) == 'true' and auto_skus:
        auto_po(list(set(auto_skus)),request.user.id)

    return HttpResponse('Picklist Confirmed')

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
        total += int(value[0])
        total_price += int(value[1])

    return render(request, 'templates/toggle/print_picklist.html', {'data': data, 'all_data': all_data, 'headers': PRINT_PICKLIST_HEADERS,
                                                                    'picklist_id': data_id,'total_quantity': total, 'total_price': total_price,
                                                                    'title': title})


@csrf_exempt
@login_required
@get_admin_user
def receive_jo(request, user=''):
    filter_params = {'user': user.id}
    return render(request, 'templates/receive_jo.html', {'headers': RECEIVE_JO_TABLE })

@csrf_exempt
def get_confirmed_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['job_code', 'creation_date', 'received_quantity']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id, status__in=['grn-generated', 'pick_confirm'],
                                              product_quantity__gt=F('received_quantity')).order_by(order_data).\
                                       values_list('job_code', flat=True)
    if search_term:
        master_data = JobOrder.objects.filter(Q(job_code__icontains=search_term), status__in=['grn-generated', 'pick_confirm'],
                                              product_code__user=user.id, product_quantity__gt=F('received_quantity')).\
                                              values_list('job_code', flat=True).order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        receive_status = 'Yet to Receive'
        data = JobOrder.objects.filter(job_code=data_id, product_code__user=user.id, status__in=['grn-generated', 'pick_confirm'])
        for dat in data:
            if dat.received_quantity:
                receive_status = 'Partially Received'
                break
        data = data[0]
        temp_data['aaData'].append({' Job Code': data.job_code, 'Creation Date': str(data.creation_date).split('+')[0],
                                    'Receive Status': receive_status, 'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.job_code}})


@csrf_exempt
@login_required
@get_admin_user
def confirmed_jo_data(request, user=''):
    job_code = request.GET['data_id']
    all_data = {}
    headers = copy.deepcopy(RECEIVE_JO_TABLE_HEADERS)
    stages = list(ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True))
    temp = get_misc_value('pallet_switch', user.id)
    record = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id, status__in=['grn-generated', 'pick_confirm'])
    if temp == 'true':
        headers.insert(2, 'Pallet Number')
        headers.append('')
    for rec in record:
        stage_quantity = 0
        status_track = StatusTracking.objects.order_by('creation_date').filter(status_id=rec.id, status_type='JO', quantity__gt=0)
        sku_cat = rec.product_code.sku_category
        stages_list = copy.deepcopy(stages)
        for tracking in status_track:
            rem_stages = stages_list
            if tracking.status_value in stages_list:
                rem_stages = stages_list[stages_list.index(tracking.status_value):]
            cond = (rec.id)
            #jo_quantity = int(rec.product_quantity) - int(rec.received_quantity)
            jo_quantity = tracking.quantity
            stage_quantity += int(tracking.quantity)
            all_data.setdefault(cond, [])

            pallet_mapping = PalletMapping.objects.filter(pallet_detail__user=user.id,po_location__job_order__job_code=rec.job_code,
                                                          po_location__job_order__product_code__wms_code=rec.product_code.wms_code, status=2)

            if pallet_mapping:
                for pallet in pallet_mapping:
                    all_data[cond].append({'wms_code': rec.product_code.wms_code,
                                           'product_quantity': jo_quantity, 'received_quantity': pallet.pallet_detail.quantity,
                                           'pallet_number': pallet.pallet_detail.pallet_code, 'stages_list': rem_stages,
                                           'status_track_id': tracking.id })
            else:
                all_data[rec.id].append({'wms_code': rec.product_code.wms_code,
                                         'product_quantity': jo_quantity, 'received_quantity': tracking.quantity, 'pallet_number': '',
                                         'stages_list': rem_stages, 'status_track_id': tracking.id})
        else:
            cond = (rec.id)
            jo_quantity = int(rec.product_quantity) - int(rec.received_quantity) - stage_quantity
            if jo_quantity <= 0:
                continue
            all_data.setdefault(cond, [])

            pallet_mapping = PalletMapping.objects.filter(pallet_detail__user=user.id,po_location__job_order__job_code=rec.job_code,
                                                          po_location__job_order__product_code__wms_code=rec.product_code.wms_code, status=2)

            if pallet_mapping:
                for pallet in pallet_mapping:
                    all_data[cond].append({'wms_code': rec.product_code.wms_code,
                                           'product_quantity': jo_quantity, 'received_quantity': pallet.pallet_detail.quantity,
                                           'pallet_number': pallet.pallet_detail.pallet_code, 'stages_list': stages_list,
                                           'status_track_id': '' })
            else:
                all_data[rec.id].append({'wms_code': rec.product_code.wms_code,
                                         'product_quantity': jo_quantity, 'received_quantity': jo_quantity, 'pallet_number': '',
                                         'stages_list': stages_list, 'status_track_id': ''})

    return render(request, 'templates/toggle/view_confirmed_jo.html', {'data': all_data, 'headers': headers,
                                                                       'job_code': job_code, 'temp': temp})

def update_pallet_data(pallet_dict, pallet_mapping):
    pallet_mapping.pallet_detail.quantity = pallet_dict['received_quantity']
    pallet_mapping.po_location.quantity = pallet_dict['received_quantity']
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

def save_receive_pallet(all_data,user):
    for key,value in all_data.iteritems():
        job_order = JobOrder.objects.get(id=key)
        for val_ind, val in enumerate(value):
            if not val[0]:
                continue
            if val[1]:
                pallet_dict = {'pallet_number': val[1], 'received_quantity': int(val[0]), 'user': user.id}
                pallet_mapping = PalletMapping.objects.filter(pallet_detail__pallet_code=val[1], pallet_detail__user=user.id,
                                                              po_location__job_order__product_code__wms_code=job_order.product_code.wms_code,
                                                              po_location__job_order__job_code=job_order.job_code, status=2)
                if not pallet_mapping:
                    location_data = {'job_order_id': job_order.id, 'location_id': None, 'status': 1, 'quantity': int(val[0]),
                                     'original_quantity': int(val[0]), 'creation_date': NOW}
                    po_location = POLocation(**location_data)
                    po_location.save()
                    pallet_dict = {'pallet_number': val[1], 'received_quantity': int(val[0]), 'user': user.id}
                    insert_pallet_data(pallet_dict, po_location, 2)

                else:
                    update_pallet_data(pallet_dict, pallet_mapping[0])
            else:
                job_order.saved_quantity = int(val[0])
                job_order.save()
                if val[3]:
                    prev_status = StatusTracking.objects.get(id=val[3])
                    if not (prev_status.status_value == val[2]):
                        prev_status.quantity = int(prev_status.quantity) - int(val[0])
                        prev_status.save()
                    else:
                        continue
                if val[2]:
                    stats_track = StatusTracking.objects.filter(status_id=key, status_type='JO', status_value=val[2])
                    if not stats_track:
                        stats_track = save_status_tracking(key, 'JO', val[2], int(val[0]))
                    else:
                        stats_track = stats_track[0]
                        stats_track.quantity = int(stats_track.quantity) + int(val[0])
                        stats_track.original_quantity = int(stats_track.original_quantity) + int(val[0])
                        stats_track.save()
                    all_data[key][val_ind][3] = stats_track.id

@csrf_exempt
@login_required
@get_admin_user
def save_receive_jo(request, user=''):
    all_data = {}
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['id'])):
        pallet_number = ''
        if 'pallet_number' in data_dict.keys():
            pallet_number = data_dict['pallet_number'][i]
        cond = (data_dict['id'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['received_quantity'][i], pallet_number, data_dict['stage'][i], data_dict['status_track_id'][i] ])
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
        pallet_number = ''
        if 'pallet_number' in data_dict.keys():
            pallet_number = data_dict['pallet_number'][i]
        cond = (data_dict['id'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['received_quantity'][i], pallet_number, data_dict['stage'][i], data_dict['status_track_id'][i] ])

    save_receive_pallet(all_data,user)
    for key,value in all_data.iteritems():
        count = 0
        job_order = JobOrder.objects.get(id=key)
        #pre_product = int(job_order.product_quantity) - int(job_order.received_quantity)
        sku_cat = job_order.product_code.sku_category
        stages_list = copy.deepcopy(stages)
        for val in value:
            if not val[3]:
                stage_status.append(job_order.product_code.wms_code)
                continue
            stats_track = StatusTracking.objects.get(id=val[3])
            if not stats_track.status_value == stages_list[-1]:
                stage_status.append(job_order.product_code.wms_code)
                continue
            count += int(val[0])
            pre_product = int(val[0])
            zone = job_order.product_code.zone
            if zone:
                put_zone = zone.zone
            else:
                put_zone = 'DEFAULT'
            temp_dict = {'user': user.id}
            if val[1]:
                temp_dict['pallet_number'] = val[1]
            temp_dict['data'] = job_order
            locations = get_purchaseorder_locations(put_zone, temp_dict)
            job_order.received_quantity = int(job_order.received_quantity) + int(val[0])
            for loc in locations:
                location_quantity, received_quantity = get_remaining_capacity(loc, int(val[0]), put_zone, val[1], user.id)
                if not location_quantity:
                    continue
                job_order.status = 'grn-generated'
                if val[1]:
                    pallet_mapping = PalletMapping.objects.filter(pallet_detail__pallet_code=val[1], pallet_detail__user=user.id,
                                                                 po_location__job_order__product_code__wms_code=job_order.product_code.wms_code,
                                                                  po_location__job_order__job_code=job_order.job_code, status=2)
                    pallet_mapping = pallet_mapping[0]
                    pallet_mapping.po_location.location_id = loc.id
                    pallet_mapping.po_location.save()
                    pallet_mapping.status = 1
                    pallet_mapping.save()
                else:
                    job_order.saved_quantity = 0
                    location_data = {'job_order_id': job_order.id, 'location_id': loc.id, 'status': 1}

                    save_update_order(location_quantity, location_data, {}, 'job_order__product_code__user', user.id)
                if not received_quantity or received_quantity == 0:
                    break
            stats_track.quantity = int(stats_track.quantity) - int(val[0])
            stats_track.save()
            total_received_qty += int(val[0])
            total_order_qty += pre_product
        if count:
            putaway_data[GRN_HEADERS].append((job_order.product_code.wms_code, pre_product, count))
        if job_order.received_quantity >= job_order.product_quantity:
            job_order.status = 'location-assigned'
        job_order.save()
    if not putaway_data.values()[0]:
        return HttpResponse("Complete the production process to generate GRN for wms codes " + ", ".join(list(set(stage_status))))
    return render(request, 'templates/toggle/jo_grn.html', {'data': putaway_data, 'job_code': job_order.job_code,
                                                            'total_received_qty': total_received_qty, 'total_order_qty': total_order_qty,
                                                            'order_date': job_order.creation_date})

@csrf_exempt
@login_required
@get_admin_user
def jo_putaway_confirmation(request, user=''):
    if get_misc_value('production_switch', user.id) == 'false':
        return render(request, 'templates/permission_denied.html')
    filter_params = {'user': user.id}
    return render(request, 'templates/jo_putaway_confirmation.html', {'headers': PUTAWAY_JO_TABLE_HEADERS })

@csrf_exempt
def get_received_jo(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['job_code', 'creation_date']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = JobOrder.objects.filter(product_code__user=user.id, status__in=['location-assigned', 'grn-generated']).\
                                              order_by(order_data).values_list('job_code', flat=True)
    if search_term:
        master_data = JobOrder.objects.filter(Q(job_code__icontains=search_term),status__in=['location-assigned', 'grn-generated'],
                                              product_code__user=user.id).values_list('job_code', flat=True).order_by(order_data)

    master_data = [ key for key,_ in groupby(master_data)]
    for data_id in master_data[start_index:stop_index]:
        po_location = POLocation.objects.filter(job_order__job_code=data_id, status=1, job_order__product_code__user=user.id)
        if po_location:
            data = JobOrder.objects.filter(job_code=data_id, product_code__user=user.id, status__in=['location-assigned', 'grn-generated'])
            data = data[0]
            temp_data['aaData'].append({'  Job Code': data.job_code, 'Creation Date': str(data.creation_date).split('+')[0],
                                        'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.job_code}})
    temp_data['recordsTotal'] = len(temp_data['aaData'])
    temp_data['recordsFiltered'] = len(temp_data['aaData'])


@csrf_exempt
@login_required
@get_admin_user
def received_jo_data(request, user=''):
    job_code = request.GET['data_id']
    all_data = {}
    headers = PUTAWAY_HEADERS
    temp = get_misc_value('pallet_switch', user.id)
    record = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id, status__in=['location-assigned', 'grn-generated'])
    if temp == 'true' and 'Pallet Number' not in headers:
        headers.insert(2, 'Pallet Number')
    for rec in record:
        po_location = POLocation.objects.exclude(location__isnull=True).filter(job_order_id=rec.id, status=1,
                                                 job_order__product_code__user=user.id)
        for location in po_location:
            cond = (location.id)
            all_data.setdefault(cond, [])
            pallet_mapping = PalletMapping.objects.filter(pallet_detail__user=user.id, po_location_id=location.id, status=1)

            if pallet_mapping:
                for pallet in pallet_mapping:
                    all_data[cond].append({'wms_code': rec.product_code.wms_code, 'location': location.location.location,
                                           'product_quantity': location.quantity, 'putaway_quantity': location.quantity,
                                           'pallet_number': pallet.pallet_detail.pallet_code })
            else:
                all_data[cond].append({'wms_code': rec.product_code.wms_code, 'location': location.location.location,
                                       'product_quantity': location.quantity, 'putaway_quantity': location.quantity, 'pallet_number': ''})
    return render(request, 'templates/toggle/view_received_jo.html', {'data': all_data, 'headers': headers,
                                                                       'job_code': job_code, 'temp': temp})

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
        return status
    for key,value in all_data.iteritems():
        data = POLocation.objects.get(id=key)
        for val in value:
            location = LocationMaster.objects.get(location=val[0], zone__user=user.id)
            if not val[1] or val[1] == '0':
                continue
            putaway_location(data, int(val[1]), location.id, user, 'job_order_id', data.job_order_id)
            filter_params = {'location_id': location.id, 'receipt_number': data.job_order.job_code,
                             'sku_id': data.job_order.product_code_id, 'sku__user': user.id, 'receipt_type': 'job order'}
            stock_data = StockDetail.objects.filter(**filter_params)
            pallet_mapping = PalletMapping.objects.filter(po_location_id=data.id,status=1)
            if pallet_mapping:
                stock_data = StockDetail.objects.filter(pallet_detail_id=pallet_mapping[0].pallet_detail.id,**filter_params)
            if pallet_mapping:
                setattr(location, 'pallet_filled', int(location.pallet_filled) + 1)
            else:
                setattr(location, 'filled_capacity', int(location.filled_capacity) + int(val[1]))
            if location.pallet_filled > location.pallet_capacity:
                setattr(location, 'pallet_capacity', location.pallet_filled)
            location.save()
            if stock_data:
                stock_data = stock_data[0]
                add_quan = int(stock_data.quantity) + int(val[1])
                setattr(stock_data, 'quantity', add_quan)
                if pallet_mapping:
                    pallet_detail = pallet_mapping[0].pallet_detail
                    setattr(stock_data, 'pallet_detail_id', pallet_detail.id)
                stock_data.save()
            else:
                record_data = {'location_id': location.id, 'receipt_number': data.job_order.job_code,
                               'receipt_date': str(data.job_order.creation_date).split('+')[0], 'sku_id': data.job_order.product_code_id,
                               'quantity': val[1], 'status': 1, 'creation_date': NOW, 'updation_date': NOW, 'receipt_type': 'job order'}
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
        diff_quantity = int(data.job_order.received_quantity) - int(putaway_quantity)
        if (int(data.job_order.received_quantity) >= int(data.job_order.product_quantity)) and (diff_quantity <= 0):
            data.job_order.status = 'confirmed-putaway'

        data.job_order.save()

    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
@fn_timer
def daily_stock_report(request, user=''):
    get_date = request.GET.get('date', '')
    header_style = easyxf('font: bold on')
    headers = ['SKU Code', 'Description', 'Opening Stock', 'Inwards Quantity', 'Outwards Quantity', 'Adjustment Quantity', 'Closing Stock']
    market_places = []
    data_dict = []
    all_data = {}
    if get_date:
        today = datetime.datetime.strptime(get_date, '%d-%m-%Y')
    else:
        today = NOW.date()
    wb, ws = get_work_sheet('skus', headers)

    tomorrow = today + datetime.timedelta(1)
    today_start =  datetime.datetime.combine(today, datetime.time())
    today_end =  datetime.datetime.combine(tomorrow, datetime.time())
    sku_codes = SKUMaster.objects.filter(user=user.id).order_by('sku_code').values('id', 'sku_code', 'sku_desc').distinct()
    data_count = 1
    receipt_objs = POLocation.objects.exclude(status='').filter(Q(updation_date__range=(today_start,today_end)) |
                                                  Q(creation_date__range=(today_start,today_end)),
                                                  location__zone__user=user.id).values('purchase_order__open_po__sku_id').distinct().\
                                          annotate(receipts=Sum('original_quantity'))
    putaway_objs = POLocation.objects.filter(Q(updation_date__range=(today_start,today_end)) |
                                                 Q(creation_date__range=(today_start,today_end)),
                                                 purchase_order__open_po__sku__user=user.id, status=0).\
                                          values('purchase_order__open_po__sku_id').distinct().annotate(putaway = Sum('original_quantity'))
    market_data = Picklist.objects.filter(Q(updation_date__range=(today_start,today_end)) |
                                          Q(creation_date__range=(today_start,today_end)), status__icontains='picked',
                                          order__user=user.id).values('stock__sku_id', 'order__marketplace').distinct().\
                                   annotate(picked=Sum('picked_quantity'))
    stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values('sku_id').distinct().\
                                         annotate(in_stock=Sum('quantity'))
    adjust_objs = CycleCount.objects.filter(Q(updation_date__range=(today_start,today_end)) |
                                                Q(creation_date__range=(today_start,today_end)), sku__user=user.id).values('sku_id').\
                                         distinct().annotate(adjusted = Sum('quantity'), seen_quantity=Sum('seen_quantity'))
    for sku in sku_codes:
        receipt_quantity = 0
        receipts = map(lambda d: d['purchase_order__open_po__sku_id'], receipt_objs)
        if sku['id'] in receipts:
            data_value = map(lambda d: d['receipts'], receipt_objs)[receipts.index(sku['id'])]
            if data_value:
                receipt_quantity = data_value
        putaway_quantity = 0
        putaways = map(lambda d: d['purchase_order__open_po__sku_id'], putaway_objs)
        if sku['id'] in putaways:
            data_value = map(lambda d: d['putaway'], putaway_objs)[putaways.index(sku['id'])]
            if data_value:
                putaway_quantity = data_value
        stock_quantity = 0
        stocks = map(lambda d: d['sku_id'], stock_objs)
        if sku['id'] in stocks:
            data_value = map(lambda d: d['in_stock'], stock_objs)[stocks.index(sku['id'])]
            if data_value:
                stock_quantity = data_value
        adjusted = 0
        adjusts = map(lambda d: d['sku_id'], adjust_objs)
        if sku['id'] in adjusts:
            data_value = map(lambda d: d['adjusted'], adjust_objs)[adjusts.index(sku['id'])]
            seen_quantity = map(lambda d: d['seen_quantity'], adjust_objs)[adjusts.index(sku['id'])]
            if data_value:
                adjusted = seen_quantity - data_value

        temp = OrderedDict(( ('SKU Code', sku['sku_code']), ('Description', sku['sku_desc']), ('Inwards Quantity', receipt_quantity),
                             ('Outwards Quantity', 0), ('Adjustment Quantity', adjusted), ('Closing Stock', stock_quantity)))
        markets = map(lambda d: d['stock__sku_id'], market_data)
        indices = [i for i, x in enumerate(markets) if x == sku['id']]
        for data_index in indices:
            picked_quantity = map(lambda d: d['picked'], market_data)[data_index]
            marketplace = map(lambda d: d['order__marketplace'], market_data)[data_index]
            temp['Outwards Quantity'] += int(picked_quantity)
            cond = (sku['sku_code'], marketplace)
            all_data.setdefault(cond, 0)
            all_data[cond] += int(picked_quantity)
            if marketplace not in market_places:
                market_places.append(marketplace)
                ws.write(0, len(headers), marketplace, header_style)
                headers.append(marketplace)

        temp['market_data'] = all_data
        temp['Opening Stock'] = (int(stock_quantity) - int(putaway_quantity)) + (int(temp['Outwards Quantity']) - adjusted)
        for i in range(len(headers)):
            if i in range(0,7):
                ws.write(data_count, i, temp[headers[i]])
            elif (temp['SKU Code'], headers[i]) in all_data.keys():
                ws.write(data_count, i, all_data[(temp['SKU Code'], headers[i])])
        data_count += 1

    file_name = "%s.%s" % (user.id, 'Daily Stock Report on ' + str(get_date))
    path = 'static/excel_files/' + file_name + '.xls'
    wb.save(path)
    path_to_file = '../' + path
    return HttpResponseRedirect(path_to_file)

@csrf_exempt
@login_required
def back_orders_rm(request):
    return render(request, 'templates/back_orders_rm.html',{'headers': BACK_ORDER_RM_TABLE})

@csrf_exempt
def get_rm_back_order_data(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    order_detail = JOMaterial.objects.filter(material_code__user=user.id, status=1).values('material_code__wms_code',
                                             'material_code__sku_code', 'material_code__sku_desc').distinct()
    master_data = []
    for order in order_detail:
        transit_quantity = 0
        sku_code = order['material_code__sku_code']
        title = order['material_code__sku_desc']
        wms_code = order['material_code__wms_code']
        filter_params = {'material_code__wms_code': wms_code, 'material_code__user': user.id, 'status': 1}
        rw_orders = RWOrder.objects.filter(job_order__product_code__sku_code=sku_code, vendor__user=user.id).\
                                    values_list('job_order_id', flat=True)
        if rw_orders:
            filter_params['job_order_id__in'] = rw_orders
        stock_quantity = StockDetail.objects.filter(sku__sku_code=sku_code, sku__user=user.id).aggregate(Sum('quantity'))['quantity__sum']
        reserved_quantity = PicklistLocation.objects.filter(stock__sku__sku_code=sku_code, stock__sku__user=user.id, status=1).\
                                                     aggregate(Sum('reserved'))['reserved__sum']
        order_quantity = JOMaterial.objects.filter(**filter_params).\
                                            aggregate(Sum('material_quantity'))['material_quantity__sum']
        purchase_order = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                               filter(open_po__sku__user=user.id, open_po__sku__sku_code=wms_code).\
                                               values('open_po__sku__wms_code').annotate(total_order=Sum('open_po__order_quantity'),
                                               total_received=Sum('received_quantity'))
        if purchase_order:
            purchase_order = purchase_order[0]
            diff_quantity = int(purchase_order['total_order']) - int(purchase_order['total_received'])
            if diff_quantity > 0:
                transit_quantity = diff_quantity
        if not stock_quantity:
            stock_quantity = 0
        if not reserved_quantity:
            reserved_quantity = 0
        if not order_quantity:
            order_quantity = 0
        procured_quantity = order_quantity - stock_quantity - transit_quantity
        if procured_quantity > 0:
            checkbox = "<input type='checkbox' id='back-checked' name='%s'>" % title
            master_data.append({'': checkbox, 'WMS Code': wms_code, 'Ordered Quantity': order_quantity,
                                'Stock Quantity': stock_quantity, 'Transit Quantity': transit_quantity,
                                ' Procurement Quantity': procured_quantity, 'DT_RowClass': 'results'})
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
    return render(request, 'templates/toggle/back_order_toggle.html',{'data_dict': data_dict, 'headers': BACK_ORDER_HEADER,
                                                                      'supplier_list': supplier_list})

@csrf_exempt
@login_required
def customer_master(request):
    return render(request, 'templates/customer_master.html', {'add_supplier': CUSTOMER_FIELDS, 'headers': CUSTOMER_MASTER_HEADERS})

@csrf_exempt
def get_customer_master(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, col_5, col_6,\
                        request, user):
    lis = ['id', 'name', 'email_id', 'phone_number', 'address', 'status']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        search_dict = {'active': 1, 'inactive': 0}
        if search_term.lower() in search_dict:
            search_terms = search_dict[search_term.lower()]
            master_data = CustomerMaster.objects.filter(status = search_terms,user=user.id).order_by(order_data)

        else:
            master_data = CustomerMaster.objects.filter( Q(name__icontains = search_term) | Q(address__icontains = search_term) |
                                                         Q(phone_number__icontains = search_term) | Q(email_id__icontains = search_term),
                                                         user=user.id ).order_by(order_data)

    else:
        master_data = CustomerMaster.objects.filter(user=user.id).order_by(order_data)

    search_params = {}

    if col_1:
        search_params["id__icontains"] = col_1
    if col_2:
        search_params["name__icontains"] = col_2
    if col_3:
        search_params["email_id__icontains"] = col_3
    if col_4:
        search_params["phone_number__icontains"] = col_4
    if col_5:
        search_params["address__icontains"] = col_5
    if col_6:
        if (str(col_6).lower() in "active"):
            search_params["status__icontains"] = 1
        elif (str(col_6).lower() in "inactive"):
            search_params["status__icontains"] = 0
        else:
            search_params["status__icontains"] = "none"
    if search_params:
        search_params["user"] =  user.id
        master_data = CustomerMaster.objects.filter(**search_params).order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)

    for data in master_data[start_index : stop_index]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        temp_data['aaData'].append(OrderedDict(( (' Customer ID', data.id), ('Customer Name', data.name), ('Address', data.address),
                                                 ('Phone Number', data.phone_number), ('Email', data.email_id), ('Status', status),
                                                 ('DT_RowId', data.id), ('DT_RowClass', 'results') )))

@csrf_exempt
@login_required
@get_admin_user
def insert_customer(request, user=''):
    customer_id = request.GET['id']
    if not customer_id:
        return HttpResponse('Missing Required Fields')
    data = filter_or_none(SupplierMaster, {'id': customer_id, 'user': user.id})
    status_msg = 'Customer Exists'
    sku_status = 0
    rep_email = filter_or_none(CustomerMaster, {'email_id': request.GET['email_id'], 'user': user.id})
    rep_phone = filter_or_none(CustomerMaster, {'phone_number': request.GET['phone_number'], 'user': user.id})
    if rep_email:
        return HttpResponse('Email already exists')
    if rep_phone:
        return HttpResponse('Phone Number already exists')

    if not data:
        data_dict = copy.deepcopy(CUSTOMER_DATA)
        for key, value in request.GET.iteritems():
            if key == 'status':
                if value == 'Active':
                    value = 1
                else:
                    value = 0
            if value == '':
                continue
            data_dict[key] = value

        data_dict['user'] = user.id
        customer_master = CustomerMaster(**data_dict)
        customer_master.save()
        status_msg = 'New Customer Added'

    return HttpResponse(status_msg)

@csrf_exempt
@login_required
@get_admin_user
def get_customer_update(request, user=''):
    data_id = request.GET['data_id']
    filter_params = {'id': data_id, 'user': user.id}
    data = get_or_none(CustomerMaster, filter_params)
    return render(request, 'templates/toggle/update_customer.html', {'data': data, 'update_supplier': CUSTOMER_FIELDS})

@csrf_exempt
@login_required
@get_admin_user
def update_customer_values(request,user=''):
    data_id = request.GET['id']
    data = get_or_none(CustomerMaster, {'id': data_id, 'user': user.id})
    for key, value in request.GET.iteritems():
        if key == 'status':
            if value == 'Active':
                value = 1
            else:
                value = 0
        setattr(data, key, value)

    data.save()
    return HttpResponse('Updated Successfully')

@csrf_exempt
@get_admin_user
def generate_jo_data(request, user=''):
    all_data = {}
    title = 'Raise Job Order'
    for key, value in request.POST.iteritems():
        key = key.split(':')[0]
        cond = (key, value)
        bom_master = BOMMaster.objects.filter(product_sku__sku_code=key, product_sku__user=user.id)
        if bom_master:
            all_data.setdefault(cond, [])
            for bom in bom_master:
                all_data[cond].append({'material_code': bom.material_sku.sku_code, 'material_quantity': int(bom.material_quantity) * int(value),
                                       'id': ''})
        else:
            all_data[cond] = [{'material_code': '', 'material_quantity': '', 'id': ''}]
    return render(request, 'templates/toggle/update_jo.html', {'headers': RAISE_JO_HEADERS, 'title': title, 'data': all_data,
                                                               'display': 'display-none'})

@csrf_exempt
@login_required
@get_admin_user
def bom_master(request, user=''):
    return render(request, 'templates/bom_master.html', {'headers': BOM_TABLE_HEADERS, 'add_bom_fields': ADD_BOM_HEADERS})

@csrf_exempt
@login_required
@get_admin_user
def add_bom_data(request,user=''):
    title = 'Add new BOM Data'
    return render(request, 'templates/toggle/add_bom_data.html', {'add_bom_fields': ADD_BOM_HEADERS, 'title': title, 'uom': UOM_FIELDS})

def validate_bom_data(all_data, product_sku, user):
    status = ''
    m_status = ''
    q_status = ''
    d_status = ''
    p_sku = SKUMaster.objects.filter(sku_code=product_sku, user=user)
    if not p_sku:
        status = "Invalid Product SKU Code %s" % product_sku
    else:
        if p_sku[0].sku_type not in ('FG', 'RM'):
            status = 'Invalid Product SKU Code %s' % product_sku

    for key, value in all_data.iteritems():
        if product_sku == key:
            status = "Product and Material SKU's should not be equal"
        for val in value:
            m_sku = SKUMaster.objects.filter(sku_code=key, user=user)
            if not m_sku:
                if not m_status:
                    m_status = "Invalid Material SKU Code %s" % key
                else:
                    m_status += ', %s' % key
            else:
                if m_sku[0].sku_type != 'RM':
                    if not m_status:
                        m_status = 'Invalid Material SKU Code %s' % key
                    else:
                        m_status += ', %s' % key

            if not val[0]:
                if not q_status:
                    q_status = 'Quantity missing for Material Sku Codes %s' % key
                else:
                    q_status += ', %s' % key
            bom_master = BOMMaster.objects.filter(product_sku__sku_code=product_sku, material_sku__sku_code=key)
            if bom_master and not val[2]:
                if not d_status:
                    d_status = 'SKU Codes already exists (%s,%s)' % (product_sku, key)
                else:
                    d_status += ', (%s,%s)' % (product_sku, key)
    if m_status:
        status += ' ' + m_status
    if q_status:
        status += ' ' + q_status
    if d_status:
        status += ' ' + d_status
    return status

def insert_bom(all_data, product_code, user):
    product_sku = SKUMaster.objects.get(sku_code=product_code, user=user)
    for key,value in all_data.iteritems():
        for val in value:
            bom = BOMMaster.objects.filter(product_sku__sku_code=product_code, material_sku__sku_code=key, product_sku__user=user)
            if bom:
                bom = bom[0]
                bom.material_quantity = int(val[0])
                bom.unit_of_measurement = val[1]
                bom.save()
            else:
                material_sku = SKUMaster.objects.get(sku_code=key, user=user)
                bom_dict = copy.deepcopy(ADD_BOM_FIELDS)
                bom_dict['product_sku_id'] = product_sku.id
                bom_dict['material_sku_id'] = material_sku.id
                bom_dict['unit_of_measurement'] = val[1]
                if val[0]:
                    bom_dict['material_quantity'] = int(val[0])
                bom_master = BOMMaster(**bom_dict)
                bom_master.save()

@csrf_exempt
@login_required
@get_admin_user
def insert_bom_data(request, user=''):
    all_data = {}
    product_sku = request.POST.get('product_sku','')
    if not product_sku:
        return HttpResponse('Product Sku Code should not be empty')
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['material_sku'])):
        if not data_dict['material_sku'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        cond = (data_dict['material_sku'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['material_quantity'][i], data_dict['unit_of_measurement'][i], data_id ])
    status = validate_bom_data(all_data, product_sku, user.id)
    if not status:
        all_data = insert_bom(all_data, product_sku, user.id)
        status = "Added Successfully"
    return HttpResponse(status)

@csrf_exempt
def get_bom_results(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, request, user):
    lis = ['product_sku__sku_code', 'product_sku__sku_desc']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if order_term:
        master_data = BOMMaster.objects.filter(product_sku__user=user.id).order_by(order_data).\
                                        values('product_sku__sku_code', 'product_sku__sku_desc').distinct().order_by(order_data)
    if search_term:
        master_data = BOMMaster.objects.filter(Q(product_sku__sku_code__icontains=search_term) |
                                               Q(product_sku__sku_desc__icontains=search_term), product_sku__user=user.id).\
                                        values('product_sku__sku_code', 'product_sku__sku_desc').distinct().order_by(order_data)
    search_params = {}
    if col_1:
        search_params["product_sku__sku_code__icontains"] = col_1
    if col_2:
        search_params["product_sku__sku_desc__icontains"] = col_2
    if search_params:
        search_params['product_sku__user'] = user.id
        master_data = BOMMaster.objects.filter(**search_params).values('product_sku__sku_code', 'product_sku__sku_desc').\
                                                                distinct().order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append({'Product SKU Code': data['product_sku__sku_code'], 'Product Description': data['product_sku__sku_desc'],
                                    'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data['product_sku__sku_code']}})

@csrf_exempt
@login_required
@get_admin_user
def get_bom_data(request, user=''):
    all_data = {}
    data_id = request.GET['data_id']
    bom_master = BOMMaster.objects.filter(product_sku__sku_code=data_id, product_sku__user=user.id)
    for bom in bom_master:
        cond = (bom.material_sku.sku_code)
        all_data.setdefault(cond, [])
        all_data[cond].append([int(bom.material_quantity), bom.unit_of_measurement, bom.id ])
    title = 'Update BOM Data'
    return render(request, 'templates/toggle/add_bom_data.html', {'add_bom_fields': ADD_BOM_HEADERS, 'title': title, 'data': all_data,
                                                                  'product_sku': data_id, 'uom': UOM_FIELDS})

@csrf_exempt
@login_required
@get_admin_user
def delete_bom_data(request, user=''):
    for key, value in request.GET.iteritems():
        bom_master = BOMMaster.objects.get(id=value, product_sku__user = user.id).delete()

    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def get_material_codes(request, user=''):
    sku_code = request.POST.get('sku_code','')
    all_data = {}
    bom_master = BOMMaster.objects.filter(product_sku__sku_code=sku_code, product_sku__user=user.id)
    if not bom_master:
        return HttpResponse("No Data Found")
    for bom in bom_master:
        cond = (bom.material_sku.sku_code)
        all_data.setdefault(cond, 0)
        all_data[cond] = bom.material_quantity
    return HttpResponse(json.dumps(all_data), content_type='application/json')

@csrf_exempt
@login_required
@get_admin_user
def bom_form(request, user=''):
    bom_file = request.GET['download-bom-file']
    if bom_file:
        return error_file_download(bom_file)
    wb, ws = get_work_sheet('BOM', BOM_UPLOAD_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.bom_form.xls' % str(user.id))

@csrf_exempt
@login_required
@get_admin_user
def combo_sku_form(request, user=''):
    combo_sku_file = request.GET['download-combo-sku-file']
    if combo_sku_file:
        return error_file_download(combo_sku_file)
    wb, ws = get_work_sheet('COMBO_SKU', COMBO_SKU_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.combo_sku_form.xls' % str(user.id))

def validate_bom_form(open_sheet, user, bom_excel):
    index_status = {}
    for row_idx in range(0, open_sheet.nrows):
        if row_idx == 0:
            cell_data = open_sheet.cell(row_idx, 0).value
            if cell_data != 'Product SKU Code':
                return 'Invalid File'
            continue
        for key, value in bom_excel.iteritems():
            if key == 'product_sku':
                product_sku = open_sheet.cell(row_idx, bom_excel[key]).value
                if isinstance(product_sku, (int, float)):
                    product_sku = int(product_sku)
                sku_code = SKUMaster.objects.filter(sku_code=product_sku, user=user)
                if not sku_code:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Code %s' % product_sku)
            if key == 'material_sku':
                material_sku = open_sheet.cell(row_idx, bom_excel[key]).value
                if isinstance(material_sku, (int, float)):
                    material_sku = int(material_sku)
                sku_code = SKUMaster.objects.filter(sku_code=material_sku, user=user)
                if not sku_code:
                    index_status.setdefault(row_idx, set()).add('Invalid SKU Code %s'% material_sku)
            elif key == 'material_quantity':
                cell_data = open_sheet.cell(row_idx, bom_excel[key]).value
                if cell_data:
                    if not isinstance(cell_data, (int, float)):
                        index_status.setdefault(row_idx, set()).add('Quantity Should be in integer')
                else:
                    index_status.setdefault(row_idx, set()).add('Quantity Should not be empty')
        if product_sku == material_sku:
            index_status.setdefault(row_idx, set()).add('Product and Material SKU Code should not be same')
        bom = BOMMaster.objects.filter(product_sku__sku_code=product_sku, material_sku__sku_code=material_sku, product_sku__user=user)
        if bom:
            index_status.setdefault(row_idx, set()).add('Product and Material Sku codes combination already exists')
    if not index_status:
        return 'Success'

    f_name = '%s.bom_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, BOM_UPLOAD_EXCEL_HEADERS, 'BOM')
    return f_name

@csrf_exempt
@login_required
@get_admin_user
def bom_upload(request, user=''):
    fname = request.FILES['files']
    bom_excel = {'product_sku': 0, 'material_sku': 1, 'material_quantity': 2, 'unit_of_measurement': 3}
    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse("Invalid File")
    status = validate_bom_form(open_sheet, str(user.id), bom_excel)

    if status != 'Success':
        return HttpResponse(status)
    for row_idx in range(1, open_sheet.nrows):
        all_data = {}
        product_sku = open_sheet.cell(row_idx, bom_excel['product_sku']).value
        material_sku = open_sheet.cell(row_idx, bom_excel['material_sku']).value
        material_quantity = open_sheet.cell(row_idx, bom_excel['material_quantity']).value
        uom = open_sheet.cell(row_idx, bom_excel['unit_of_measurement']).value
        if isinstance(product_sku, (int, float)):
            product_sku = int(product_sku)
        if isinstance(material_sku, (int, float)):
            material_sku = int(material_sku)
        if not material_quantity:
            material_quantity = 0
        data_id = ''
        cond = (material_sku)
        all_data.setdefault(cond, [])
        all_data[cond].append([material_quantity, uom, data_id ])
        insert_bom(all_data, product_sku, user.id)
    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def get_sku_grid(request, user=''):
    search = request.POST.get('search','')
    category = request.POST.get('category','')
    value = request.POST.get('index','')
    search_params = {}
    if value:
        data = value.split(':')
        start = int(data[0])
        stop = int(data[1])
    else:
        start = 0
        stop = 20
    search_params['user'] = user.id
    if category:
        search_params['sku_category'] = category
    if search:
        sku_master = SKUMaster.objects.filter(Q(sku_desc__icontains=search) | Q(sku_code__icontains=search) |
                                              Q(wms_code__icontains=search),**search_params).order_by('-image_url').\
                                             values('id', 'sku_code', 'sku_desc', 'image_url')
    else:
        sku_master = SKUMaster.objects.filter(**search_params).order_by('-image_url').\
                                             values('id', 'sku_code', 'sku_desc', 'image_url')
    if 'sku_codes' in request.POST.keys():
        select_skus = SKUMaster.objects.filter(sku_code__in=request.POST['sku_codes'].split(','), user=user.id)
        sel_codes = select_skus.values_list('sku_code', flat=True)
        sku_master = sku_master.exclude(sku_code__in=sel_codes)
        sku_master = list(chain(select_skus, sku_master))
    last_index = len(sku_master)
    sku_master = sku_master[start:stop]
    return render(request, 'templates/toggle/grid_sku.html', {'data': sku_master, 'start': int(start) + 20, 'stop': int(stop) + 20,
                                                              'last_index': last_index})

@csrf_exempt
@login_required
@get_admin_user
def get_category_view(request, user=''):
    search = request.POST.get('search','')
    category = request.POST.get('category','')
    search_params = {}
    all_data = OrderedDict()
    search_params['user'] = user.id
    if category:
        search_params['sku_category'] = category
    if search:
        sku_master = SKUMaster.objects.filter(Q(sku_desc__icontains=search) | Q(sku_code__icontains=search) |
                                              Q(wms_code__icontains=search),**search_params).order_by('-image_url', 'sku_category')
    else:
        sku_master = SKUMaster.objects.filter(**search_params).order_by('-image_url', 'sku_category')
    for sku in sku_master:
        cond = (sku.sku_category)
        all_data.setdefault(cond, [])
        if len(all_data[cond]) > 20:
            continue
        all_data[cond].append({'sku_code': sku.sku_code, 'sku_desc': sku.sku_desc,
                               'image_url': sku.image_url })
        if len(all_data) > 20:
            break
    return render(request, 'templates/toggle/category_view.html', {'data': all_data})


@csrf_exempt
@login_required
@get_admin_user
def view_confirmed_jo(request, user=''):
    job_code = request.POST['data_id']
    all_data = {}
    title = "Update Job Order"
    record = JobOrder.objects.filter(job_code=job_code, product_code__user=user.id, status='order-confirmed')
    for rec in record:
        jo_material = JOMaterial.objects.filter(job_order_id= rec.id,status=1)
        cond = (rec.product_code.sku_code, rec.product_quantity)
        for jo_mat in jo_material:
            all_data.setdefault(cond, [])
            all_data[cond].append({'material_code': jo_mat.material_code.sku_code, 'material_quantity': int(jo_mat.material_quantity),
                                   'id': jo_mat.id })
    return render(request, 'templates/toggle/confirmed_job_order.html', {'data': all_data, 'headers': RAISE_JO_HEADERS, 'job_code': job_code})

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
    status = validate_jo_stock(all_data, user.id, job_code)
    if status:
        return HttpResponse(status)
    save_jo_locations(all_data, user, job_code)
    data = get_raw_picklist_data(job_code, user)
    show_image = get_misc_value('show_image', user.id)
    if show_image == 'true':
        headers.insert(0, 'Image')
    if get_misc_value('pallet_switch', user.id) == 'true' and 'Pallet Code' not in headers:
        headers.insert(headers.index('Location') + 1, 'Pallet Code')

    return render(request, 'templates/toggle/view_raw_picklist.html', {'data': data, 'headers': headers, 'job_code': job_code,
                                                                       'show_image': show_image, 'user': user})

@login_required
def mail_report_configuration(request):
    enabled_reports = MiscDetail.objects.filter(misc_type__contains='report', misc_value='true', user=request.user.id)
    reports_data = []
    for reports in enabled_reports:
        reports_data.append(str(reports.misc_type.replace('report_', '')))

    mail_listing = MiscDetail.objects.filter(misc_type='email', user=request.user.id)
    email = ''
    if mail_listing:
        email = mail_listing[0].misc_value

    report_frequency = MiscDetail.objects.filter(misc_type='report_frequency', user=request.user.id)
    report_freq = ''
    if report_frequency:
         report_freq = report_frequency[0].misc_value

    report_data_range = MiscDetail.objects.filter(misc_type='report_data_range', user=request.user.id)
    data_range = ''
    if report_data_range:
        data_range = report_data_range[0].misc_value

    return render(request, 'templates/mail_report_configuration.html',  {'mail_reports': MAIL_REPORTS, 'data_range': data_range, 'report_freq': report_freq, 'email': email, 'mail_listing': mail_listing, 'reports_data': reports_data})


def enable_mail_reports(request):
    data = request.GET.get('data').split(',')
    data_enabled = []
    data_disabled = []
    for d in data:
        if d:
            data_enabled.append(MAIL_REPORTS_DATA[d])

    data_disabled = set(MAIL_REPORTS_DATA.values()) - set(data_enabled)

    for d in data_disabled:
        misc_detail = MiscDetail.objects.filter(user=request.user.id, misc_type=d)
        if misc_detail:
            misc_detail[0].misc_value = 'false'
            misc_detail[0].save()
            continue
        data_obj = MiscDetail(user=request.user.id, misc_type=d, misc_value='false')

    for d in data_enabled:
        misc_detail = MiscDetail.objects.filter(user=request.user.id, misc_type=d)
        if misc_detail:
            misc_detail[0].misc_value = 'true'
            misc_detail[0].save()
            continue
        data_obj = MiscDetail(user=request.user.id, misc_type=d, misc_value='true')
        data_obj.save()


    return HttpResponse('Success')

@csrf_exempt
def update_mail_configuration(request):
    data = {}
    selected = request.POST.getlist('selected[]')
    removed = request.POST.getlist('removed[]')
    frequency = request.POST.get('frequency')
    data_range = request.POST.get('range')
    email = request.POST.get('email')
    date_val = request.POST.get('date_val')

    for select_data in selected:
        misc_type = 'report_' + REPORTS_DATA[select_data.strip()]
        misc_detail = MiscDetail.objects.filter(user=request.user.id, misc_type=misc_type)
        if misc_detail:
            misc_detail[0].misc_value = 'true'
            misc_detail[0].save()
            continue

        misc_detail = MiscDetail(user=request.user.id, misc_type=misc_type, misc_value='true')
        misc_detail.save()

    for select_data in removed:
        misc_type = 'report_' + REPORTS_DATA[select_data.strip()]
        misc_detail = MiscDetail.objects.filter(user=request.user.id, misc_type=misc_type)
        if misc_detail:
            misc_detail[0].misc_value = 'false'
            misc_detail[0].save()
            continue

        misc_detail = MiscDetail(user=request.user.id, misc_type=misc_type, misc_value='false')
        misc_detail.save()

    if frequency:
        data_dict = {'user': request.user.id, 'misc_type': 'report_frequency'}
        if date_val:
            date_val = time.strptime(date_val, '%d/%M/%Y')
            date_val = time.strftime('%Y-%M-%d', date_val)
        misc_detail = MiscDetail.objects.filter(**data_dict)
        if misc_detail:
            misc_detail[0].misc_value = frequency
            if date_val:
                misc_detail[0].creation_date = date_val
            misc_detail[0].save()
        else:
            if date_val:
                data_dict['creation_date'] = date_val
            misc_detail = MiscDetail(**data_dict)
            misc_detail.misc_value = frequency
            misc_detail.save()

    if data_range:
        misc_detail = MiscDetail.objects.filter(user=request.user.id, misc_type='report_data_range')
        if misc_detail:
            misc_detail[0].misc_value = frequency
            misc_detail[0].save()
        else:
            misc_detail = MiscDetail(user=request.user.id, misc_type='report_data_range', misc_value=data_range)
            misc_detail.save()

    if email:
        misc_detail = MiscDetail.objects.filter(user=request.user.id, misc_type='email')
        if misc_detail:
            misc_detail[0].misc_value = email
            misc_detail[0].save()
        else:
            misc_detail = MiscDetail(user=request.user.id, misc_type='email', misc_value=email)
            misc_detail.save()

    return HttpResponse('Success')

@get_admin_user
def send_mail_reports(request, user=''):
    MailReports().send_reports_mail(user, mail_now=True)
    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def insert_customer_sku(request, user=''):
    customer_id = request.GET['customer_id']
    if not ":" in customer_id:
        return HttpResponse('Given Customer ID / Name not correct.')
    ID = str(customer_id.split(":")[0][:-1])
    name = str(customer_id.split(":")[1][1:])
    customer_sku_data = filter_or_none(CustomerSKU, {'customer_name__name': name, 'sku__sku_code': request.GET['sku_code']})
    if customer_sku_data:
        return HttpResponse('Customer SKU Mapping already exists.')
    status_msg = 'Supplier Exists'
    sku_status = 0
    customer_data = filter_or_none(CustomerMaster, {'id': ID, 'user': user.id})
    customer_sku = filter_or_none(SKUMaster, {'sku_code': request.GET['sku_code'], 'user': user.id})
    if not customer_data:
        return HttpResponse("customer doesn't exists.")
    elif not customer_sku:
        return HttpResponse("Customer SKU doesn't exists.")
    data_dict = copy.deepcopy(CUSTOMER_SKU_DATA)
    for key, value in request.GET.iteritems():
        if key == 'customer_id':
            value = customer_data[0].id
            key = "customer_name_id"
        if key == 'sku_code':
            value = customer_sku[0].id
            key = "sku_id"
        data_dict[key] = value

    customer = CustomerSKU(**data_dict)
    customer.save()
    status_msg = 'New Customer SKU Mapping Added'
    return HttpResponse(status_msg)

@csrf_exempt
def get_customer_sku_mapping(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, request, user):
    order_data = CUSTOMER_SKU_MAPPING_HEADERS.values()[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if order_term:
        master_data = CustomerSKU.objects.filter(sku__user=user.id).order_by(order_data)
    if search_term:
        master_data = CustomerSKU.objects.filter(Q(customer_name__id=search_term) | Q(customer_name__name__icontains=search_term) | Q(sku__sku_code__icontains=search_term) | Q(price__icontains=search_term), sku__user=user.id)

    search_params = {}
    if col_1:
        search_params["customer_name__id__icontains"] = col_1
    if col_2:
        search_params["customer_name__name__icontains"] = col_2
    if col_3:
        search_params["sku__sku_code__icontains"] = col_3
    if col_4:
        search_params["price__icontains"] = col_4

    if search_params:
        search_params["sku__user"] =  user.id
        master_data = CustomerSKU.objects.filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append(OrderedDict(( ('DT_RowId', data.id), ('Customer ID ', data.customer_name.id),
                                                 ('Customer Name', data.customer_name.name),
                                                 ('SKU Code', data.sku.sku_code), ('Price', data.price), ('DT_RowClass', 'results') )))

@csrf_exempt
@login_required
@get_admin_user
def update_customer_sku_mapping(request , user=""):
    data_id = request.GET['data-id']
    cust_name = request.GET['customer_name']
    cust_sku = request.GET['sku_code']
    cust_price = request.GET['price']
    data = CustomerSKU.objects.filter(customer_name__name = cust_name, sku__sku_code = cust_sku).exclude(id = data_id)
    if data:
        return HttpResponse('This Customer SKU Mapping already exist')
    sku_data = SKUMaster.objects.filter(sku_code = cust_sku)
    if not sku_data:
        return HttpResponse("Given SKU Code doesn't exists")
    else:
        data = get_or_none(CustomerSKU, {'id':data_id})
        data.sku_id = sku_data[0].id
        data.price = cust_price
        data.save()
    return HttpResponse('Updated Successfully')

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
    open_po = OrderedDict()
    open_orders = OrderedDict()
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
        open_po[(open_po_id, total)] = {'order_data': temp_data, 'stage': json.dumps(stage),
                                                                  'index': po_data[0].order_id}

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
        open_orders[order, invoice] = {'order_data': temp_data, 'stage': json.dumps(stage), 'index': order}
    if (search and not p_index) or not search:
        orders_data['orders'] = open_orders
    if (search and not o_index) or not search:
        orders_data['purchase-orders'] = open_po
    if (order_id or o_index or p_index) and not is_db:
        return render(request, 'templates/toggle/search_track_order.html', {'orders_data': orders_data})

    return render(request, 'templates/track_orders.html', {'orders_data': orders_data})

@csrf_exempt
@login_required
@get_admin_user
def inventory_adjust_form(request, user=''):
    inventory_file = request.GET['download-inventory-adjust-file']
    if inventory_file:
        return error_file_download(inventory_file)
    wb, ws = get_work_sheet('INVENTORY_ADJUST', ADJUST_INVENTORY_EXCEL_HEADERS)
    return xls_to_response(wb, '%s.inventory_adjustment_form.xls' % str(user.id))

@csrf_exempt
def validate_inventory_adjust_form(open_sheet, user):
    mapping_dict = {}
    index_status = {}
    location = {}
    for row_idx in range(0, open_sheet.nrows):
        for col_idx in range(0, len(ADJUST_INVENTORY_EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if row_idx == 0:
                if col_idx == 0 and cell_data != 'WMS Code':
                    return 'Invalid File'
                break
            if col_idx == 0:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                sku_master = SKUMaster.objects.filter(wms_code=cell_data, user=user)
                if not sku_master:
                    index_status.setdefault(row_idx, set()).add('Invalid WMS Code')
            elif col_idx == 1:
                if cell_data:
                    location_master = LocationMaster.objects.filter(zone__user=user, location=cell_data)
                    if not location_master:
                        index_status.setdefault(row_idx, set()).add('Invalid Location')
                else:
                    index_status.setdefault(row_idx, set()).add('Location should not be empty')
            elif col_idx == 2:
                if cell_data and (not isinstance(cell_data, (int, float)) or int(cell_data) < 0):
                    index_status.setdefault(row_idx, set()).add('Invalid Quantity')

    if not index_status:
        return 'Success'
    f_name = '%s.inventory_adjust_form.xls' % user
    write_error_file(f_name, index_status, open_sheet, ADJUST_INVENTORY_EXCEL_HEADERS, 'Inventory Adjustment')
    return f_name

@csrf_exempt
@login_required
@get_admin_user
def inventory_adjust_upload(request, user=''):
    fname = request.FILES['files']
    try:
        open_book = open_workbook(filename=None, file_contents=fname.read())
        open_sheet = open_book.sheet_by_index(0)
    except:
        return HttpResponse('Invalid File')

    status = validate_inventory_adjust_form(open_sheet, str(user.id))
    if status != 'Success':
        return HttpResponse(status)
    for row_idx in range(1, open_sheet.nrows):
        cycle_count = CycleCount.objects.filter(sku__user=user.id).order_by('-cycle')
        if not cycle_count:
            cycle_id = 1
        else:
            cycle_id = cycle_count[0].cycle + 1
        location_data = ''
        for col_idx in range(0, len(ADJUST_INVENTORY_EXCEL_HEADERS)):
            cell_data = open_sheet.cell(row_idx, col_idx).value
            if col_idx == 0 and cell_data:
                if isinstance(cell_data, (int, float)):
                    cell_data = int(cell_data)
                cell_data = str(cell_data)
                wms_code = cell_data
            elif col_idx == 1:
                loc = cell_data
            elif col_idx == 2:
               quantity = int(cell_data)
            elif col_idx == 3:
               reason = cell_data
        adjust_location_stock(cycle_id, wms_code, loc, quantity, reason, user)
    return HttpResponse('Success')

@csrf_exempt
@login_required
def delete_market_mapping(request):
    data_id = request.GET.get('data_id', '')
    if data_id:
        MarketplaceMapping.objects.get(id=data_id).delete()
    return HttpResponse("Deleted Successfully")


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

    return render(request, 'templates/toggle/raise_st_toggle.html', {'st_fields': RAISE_ST_FIELDS, 'st_fields1': RAISE_ST_FIELDS1,
                                                                     'user_list': user_list})

def validate_st(all_data, user):
    sku_status = ''
    other_status = ''
    price_status = ''
    wh_status = ''

    for key,value in all_data.iteritems():
        warehouse = User.objects.get(username=key)
        if not value:
            continue
        for val in value:
            sku = SKUMaster.objects.filter(wms_code = val[0], user=warehouse.id)
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
            code = val[0]
            sku_code = SKUMaster.objects.filter(wms_code__iexact=val[0], user=user.id)
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
def get_raised_stock_transfer(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, request, user):
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
    search_params = {}
    if col_1:
        search_params['warehouse__username__icontains'] = col_1
    if col_2:
        open_st_ids = OpenST.objects.exclude(status=0).filter(sku__user=user.id).values('warehouse_id').distinct().\
                                            annotate(total=Sum('order_quantity')).filter(total__icontains=col_2).values_list('warehouse_id', flat=True)
        search_params["warehouse_id__in"] = open_st_ids
    if search_params:
        search_params['sku__user'] = user.id
        search_params['status'] = 1
        master_data = OpenST.objects.filter(**search_params).values('warehouse__username').annotate(total=Sum('order_quantity')).\
                                     order_by(order_data).distinct()
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        temp_data['aaData'].append({'Warehouse Name': data['warehouse__username'], 'Total Quantity': data['total'], 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'id': data['warehouse__username']}})

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
    return render(request, 'templates/toggle/update_st.html', {'st_fields': RAISE_ST_FIELDS, 'st_fields1': RAISE_ST_FIELDS1,
                    'data': all_data})

@csrf_exempt
@login_required
@get_admin_user
def delete_st(request, user=''):
    data_id = request.GET.get('data_id')
    OpenST.objects.get(id=data_id).delete()
    return HttpResponse("Deleted Successfully")


def get_purchase_order_id(user):
    po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).values_list('order_id', flat=True).order_by("-order_id")
    st_order = STPurchaseOrder.objects.filter(open_st__sku__user=user.id).values_list('po__order_id', flat=True).order_by("-po__order_id")
    rw_order = RWPurchase.objects.filter(rwo__vendor__user=user.id).values_list('purchase_order__order_id', flat=True).\
                                  order_by("-purchase_order__order_id")
    order_ids = list(chain(po_data, st_order, rw_order))
    order_ids = sorted(order_ids,reverse=True)
    if not order_ids:
        po_id = 1
    else:
        po_id = int(order_ids[0]) + 1
    return po_id


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


@csrf_exempt
@login_required
@get_admin_user
def create_stock_transfer(request, user=''):
    all_data = {}
    warehouse_name = request.POST.get('warehouse_name','')
    data_dict = dict(request.POST.iterlists())
    for i in range(len(data_dict['wms_code'])):
        if not data_dict['wms_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        cond = (user.username)
        all_data.setdefault(cond, [])
        all_data[cond].append([data_dict['wms_code'][i], data_dict['order_quantity'][i], data_dict['price'][i], data_id ])
    warehouse = User.objects.get(username=warehouse_name)

    status = validate_st(all_data, warehouse)
    if not status:
        all_data = insert_st(all_data, warehouse)
        status = confirm_stock_transfer(all_data, warehouse, user.username)
    return HttpResponse(status)

@csrf_exempt
def get_stock_transfer_orders(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['id', 'st_po__open_st__warehouse__username', 'order_id', 'sku__sku_code', 'quantity']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = StockTransfer.objects.filter(sku__user=user.id, status=1).order_by(order_data)
    if search_term:
        master_data = StockTransfer.objects.filter(Q(st_po__open_st__warehouse__username__icontains=search_term) |
                                                   Q(quantity__icontains=search_term) | Q(order_id__icontains=search_term) |
                                                   Q(sku__sku_code__icontains=search_term), sku__user=user.id, status=1).order_by(order_data)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        checkbox = '<input type="checkbox" name="id" value="%s">' % data.id
        w_user = User.objects.get(id=data.st_po.open_st.sku.user)
        temp_data['aaData'].append({'': checkbox, 'Warehouse Name': w_user.username, 'Stock Transfer ID': data.order_id,
                                    'SKU Code': data.sku.sku_code, 'Quantity': data.quantity, 'DT_RowClass': 'results',
                                    'DT_RowAttr': {'id': data.id}})

@csrf_exempt
@login_required
@get_admin_user
def st_generate_picklist(request, user=''):
    out_of_stock = []
    picklist_number = get_picklist_number(user)

    sku_combos = SKURelation.objects.prefetch_related('parent_sku', 'member_sku').filter(parent_sku__user=user.id)
    sku_stocks = StockDetail.objects.prefetch_related('sku', 'location').filter(sku__user=user.id, quantity__gt=0)
    all_orders = OrderDetail.objects.prefetch_related('sku').filter(status=1, user=user.id, quantity__gt=0)

    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == 'true':
        stock_detail1 = sku_stocks.exclude(location__zone__zone='TEMP_ZONE').filter(quantity__gt=0).order_by('receipt_date')
        data_dict['location__zone__zone__in'] = ['TEMP_ZONE', 'DEFAULT']
        stock_detail2 = sku_stocks.filter(quantity__gt=0).order_by('receipt_date')
    else:
        stock_detail1 = sku_stocks.filter(location_id__pick_sequence__gt=0).filter(quantity__gt=0).order_by('location_id__pick_sequence')
        stock_detail2 = sku_stocks.filter(location_id__pick_sequence=0).filter(quantity__gt=0).order_by('receipt_date')
    sku_stocks = stock_detail1 | stock_detail2
    for key, value in request.POST.iteritems():
        order_data = StockTransfer.objects.filter(id=value)
        stock_status, picklist_number = picklist_generation(order_data, request, picklist_number, user, sku_combos, sku_stocks)

        if stock_status:
            out_of_stock = out_of_stock + stock_status

    if out_of_stock:
        stock_status = 'Insufficient Stock for SKU Codes ' + ', '.join(list(set(out_of_stock)))
    else:
        stock_status = ''

    headers, show_image, use_imei = picklist_headers(request, user.id)

    order_status = ''
    data = get_picklist_data(picklist_number + 1, user.id)
    if data:
        order_status = data[0]['status']
        if order_status == 'open':
            headers.insert(headers.index('WMS Code'),'Order ID')

    return render(request, 'templates/toggle/generate_picklist.html', {'data': data, 'headers': headers,
                           'picklist_id': picklist_number + 1,'stock_status': stock_status, 'show_image': show_image,
                           'use_imei': use_imei, 'order_status': order_status, 'user': request.user})

@csrf_exempt
@login_required
@get_admin_user
def warehouse_master(request, user=''):
    if not user.is_superuser:
        return render(request, 'templates/permission_denied.html')
    return render(request, 'templates/warehouse_master.html', {'headers': WAREHOUSE_HEADERS, 'add_user_fields': WAREHOUSE_USER_FIELDS })

@csrf_exempt
def get_warehouse_user_results(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, request, user):
    lis  = ['username', 'first_name', 'email', 'id']
    user_dict = OrderedDict()
    order_data = 'user__' + lis[col_num]
    order_data1 = 'admin_user__' + lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
        order_data1 = '-%s' % order_data1
    if search_term:
        master_data1 = UserGroups.objects.filter(Q(user__first_name__icontains=search_term) | Q(user__email__icontains=search_term),
                                                 admin_user__username__iexact=user.username).\
                                                 order_by(order_data, order_data).values_list('user__username', 'user__first_name',
                                                 'user__email')
        master_data2 = UserGroups.objects.filter(Q(admin_user__first_name__icontains=search_term) |
                                                 Q(admin_user__email__icontains=search_term), user__username__iexact=user.username).\
                                                 order_by(order_data, order_data).values_list('admin_user__username',
                                                'admin_user__first_name', 'admin_user__email')
        master_data = list(chain(master_data1, master_data2))
    elif order_term:
        master_data1 = UserGroups.objects.filter(admin_user__username__iexact=user.username).order_by(order_data, order_data).\
                                          values_list('user__username', 'user__first_name', 'user__email')
        master_data2 = UserGroups.objects.filter(user__username__iexact=user.username).values_list('admin_user__username',
                                                'admin_user__first_name', 'admin_user__email')
        master_data = list(chain(master_data1, master_data2))

    search_params1 = {}
    search_params2 = {}
    if col_1:
        search_params1["user__username__icontains"] = col_1
        search_params2["admin_user__username__icontains"] = col_1
    if col_2:
        search_params1["user__first_name__icontains"] = col_2
        search_params2["admin_user__first_name__icontains"] = col_2
    if col_3:
        search_params1["user__email__icontains"] = col_3
        search_params2["admin_user__email__icontains"] = col_3
    if col_4:
        city_ids = UserProfile.objects.filter(city__icontains=col_4).values_list('user_id', flat=True)
        search_params1["user_id__in"] = city_ids
        search_params2["admin_user_id__in"] = city_ids
    if search_params1:
        search_params1['admin_user__username__iexact'] = user.username
        search_params2['user__username__iexact'] = user.username
        master_data1 = UserGroups.objects.filter(**search_params1).values_list('user__username','user__first_name',
                                                 'user__email').order_by(order_data, order_data)
        master_data2 = UserGroups.objects.filter(**search_params2).values_list('admin_user__username','admin_user__first_name',
                                                 'admin_user__email').order_by(order_data, order_data)
        master_data = list(chain(master_data1, master_data2))
            
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data[start_index:stop_index]:
        user_profile = UserProfile.objects.get(user__username=data[0])
        temp_data['aaData'].append({'Username': data[0],'DT_RowClass': 'results', 'Name': data[1],
                                    'Email': data[2], 'City': user_profile.city, 'DT_RowId': data[0]})

@csrf_exempt
@login_required
@get_admin_user
def add_warehouse_user(request, user=''):
    status = ''
    user_dict = copy.deepcopy(ADD_USER_DICT)
    user_profile_dict = copy.deepcopy(ADD_WAREHOUSE_DICT)
    for key,value in request.POST.iteritems():
        if key in user_dict.keys():
            user_dict[key] = value
        if key in user_profile_dict.keys():
            user_profile_dict[key] = value
    if not user_dict['password'] == request.POST['re_password']:
        status = "Passwords doesn't match"
    user_exists = User.objects.filter(username=user_dict['username'])
    if not user_exists and not status:
        new_user = User.objects.create_user(**user_dict)
        new_user.is_staff = True
        new_user.save()
        user_profile_dict['user_id'] = new_user.id
        user_profile_dict['location'] = user_profile_dict['state']
        user_profile_dict['prefix'] = new_user.username[:3]
        user_profile = UserProfile(**user_profile_dict)
        user_profile.save()
        group,created = Group.objects.get_or_create(name=new_user.username)
        admin_dict = {'group_id': group.id, 'user_id': new_user.id}
        admin_group  = AdminGroups(**admin_dict)
        admin_group.save()
        new_user.groups.add(group)
        UserGroups.objects.create(admin_user_id=user.id, user_id=new_user.id)
        status = 'Added Successfully'
    else:
        status = 'Username already exists'
    return HttpResponse(status)

@csrf_exempt
@login_required
@get_admin_user
def get_warehouse_user_data(request, user=''):
    username = request.GET['username']
    user_profile = UserProfile.objects.get(user__username=username)
    data = {'username': user_profile.user.username, 'first_name': user_profile.user.first_name, 'last_name': user_profile.user.last_name, 
            'phone_number': user_profile.phone_number, 'email': user_profile.user.email, 'country': user_profile.country,
            'state': user_profile.state, 'city': user_profile.city, 'address': user_profile.address, 'pin_code': user_profile.pin_code} 
    return render(request, 'templates/toggle/update_warehouse_user.html', {'data': data, 'headers': WAREHOUSE_HEADERS,
                                                               'add_user_fields': WAREHOUSE_UPDATE_FIELDS })

@csrf_exempt
@login_required
@get_admin_user
def update_warehouse_user(request, user=''):
    username = request.POST['username']
    user_dict = copy.deepcopy(ADD_USER_DICT)
    user_profile_dict = copy.deepcopy(ADD_WAREHOUSE_DICT)
    user_profile = UserProfile.objects.get(user__username=username)
    for key,value in request.POST.iteritems():
        if key in user_dict.keys() and not key == 'username':
            setattr(user_profile.user, key, value)
        if key in user_profile_dict.keys():
            setattr(user_profile, key, value)
    user_profile.user.save()
    user_profile.save()
    return HttpResponse("Updated Successfully")

def discount_master(request):
    return render(request, 'templates/discount_master.html',{'headers': DISCOUNT_HEADERS, 'add_discount': ADD_DISCOUNT_FIELDS})

@csrf_exempt
@login_required
def insert_discount(request):
    data = request.POST.get('data')
    save = {}
    if data:
      data = eval(data)
      for field in data:
        if not field['value']:
            continue
        save[field['name']] = field['value']


    if save.get('sku_code'):
        sku = SKUMaster.objects.filter(wms_code = save['sku_code'])
        if not sku:
            return HttpResponse("Given SKU not found")

        sku = sku[0]
        sku.discount_percentage = float(save['sku_discount'])
        sku.save()

    if save.get('category'):
        category = CategoryDiscount.objects.filter(category=save.get('category', ''), user_id=request.user.id)
        if category:
            category = category[0]
            category.discount = float(save['category_discount'])
            category.save()
        else:
            category = CategoryDiscount(discount=float(save['category_discount']),
                                        category=save.get('category', ''),
                                        creation_date=NOW, user_id=request.user.id)
            category.save()

    return HttpResponse('Updated Successfully')

def get_customer_all_data(request):
    lis = ['name', 'email_id', 'phone_number', 'address', 'status']
    master_data = CustomerMaster.objects.filter()
    total_data = []
    for data in master_data:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        total_data.append({'ID': data.id, 'FirstName': data.name,'Address': data.address,\
                           'Number': str(data.phone_number), 'Email': data.email_id})
    return HttpResponse(json.dumps(total_data))

def get_sku_total_data(request):
    master_data = SKUMaster.objects.filter(user = 4)
    total_data = []
    for data in master_data:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        zone = ''
        if data.zone_id:
            zone = data.zone.zone
        total_data.append({'search': str(data.wms_code)+" "+data.sku_desc, 'SKUCode': data.wms_code, 'ProductDescription': data.sku_desc, 'price': 100, 'url': data.image_url, 'data-id': data.id})
    return HttpResponse(json.dumps(total_data))

@csrf_exempt
def validate_sales_person(request):
    response_data = {'status': 'Fail'}
    user_id = request.GET.get('user_id')
    user_name = request.GET.get('user_name')
    if user_id and user_name:
        data = SalesPersons.objects.filter(id=user_id, user_name=user_name)
        if data:
            VAT = UserProfile.objects.filter(user__id= data[0].user_id)[0]
            VAT = TaxMaster.objects.filter(state = VAT.state)
            VAT = VAT.filter(tax_type = 'VAT')
            if VAT:
                VAT = VAT[0].tax_percentage
            else:
                VAT = '14.5'
            response_data['status'] = 'Success'
            response_data['VAT'] = VAT
            response_data['user_name'] = data[0].user_name
            response_data['sales_person_id'] = data[0].id
            response_data['parent_id'] = data[0].user.id
            return HttpResponse(json.dumps(response_data))
    return HttpResponse(json.dumps(response_data))

@csrf_exempt
@login_required
@get_admin_user
def image_upload(request, user=''):
    return render(request, 'templates/image_upload.html')

@csrf_exempt
@login_required
@get_admin_user
def upload_images(request, user=''):
    status = 'Uploaded Successfully'
    image_file = request.FILES.get('files-0','')
    extra_image = ''
    if image_file:
        image_name = image_file.name.strip('.' + image_file.name.split('.')[-1])
        sku_code = image_name
        if '__' in image_name:
            sku_code = image_name.split('__')[0]
        sku_master = SKUMaster.objects.filter(sku_code__iexact=sku_code, user=user.id)
        if sku_master:
            sku_master = sku_master[0]
            if sku_master.image_url:
                extra_image = 'true'
            save_image_file(image_file, sku_master, user, extra_image)
        else:
            status = "SKU Code doesn't exists"
    return HttpResponse(status)

@csrf_exempt
@login_required
@get_admin_user
def get_selected_skus(request, user=''):
    skus = request.GET['skus']
    data = []
    for sku_code in skus.split(','):
        invoice_amount = 0
        customer_sku = CustomerSKU.objects.filter(sku__sku_code=sku_code, sku__user=user.id)
        if customer_sku:
            invoice_amount = customer_sku[0].price
        data.append({'sku_id': sku_code, 'quantity': 1, 'invoice_amount': invoice_amount})
    return render(request, 'templates/toggle/order_template.html', {'create_order_fields': CREATE_ORDER_FIELDS,
                                                            'create_order_fields1': CREATE_ORDER_FIELDS1, 'selected_skus': data })

@csrf_exempt
@login_required
@get_admin_user
def vendor_master(request, user=''):
    return render(request, 'templates/vendor_master.html', {'headers': VENDOR_HEADERS, 'add_vendor': VENDOR_FIELDS})

@csrf_exempt
@login_required
@get_admin_user
def insert_vendor(request, user=''):
    vendor_id = request.GET['vendor_id']
    if not vendor_id:
        return HttpResponse('Missing Required Fields')
    data = filter_or_none(VendorMaster, {'vendor_id': vendor_id, 'user': user.id})
    status_msg = 'Vendor Exists'
    sku_status = 0
    rep_email = filter_or_none(VendorMaster, {'email_id': request.GET['email_id'], 'user': user.id})
    rep_phone = filter_or_none(VendorMaster, {'phone_number': request.GET['phone_number'], 'user': user.id})
    if rep_email:
        return HttpResponse('Email already exists')
    if rep_phone:
        return HttpResponse('Phone Number already exists')

    if not data:
        data_dict = copy.deepcopy(VENDOR_DATA)
        for key, value in request.GET.iteritems():
            if key == 'status':
                if value == 'Active':
                    value = 1
                else:
                    value = 0
            if value == '':
                continue
            data_dict[key] = value

        data_dict['user'] = user.id
        vendor_master = VendorMaster(**data_dict)
        vendor_master.save()
        status_msg = 'New Vendor Added'

    return HttpResponse(status_msg)

@csrf_exempt
def get_vendor_master_results(start_index, stop_index, temp_data, search_term, order_term, col_num, col_1, col_2, col_3, col_4, col_5, col_6,
                              request, user):
    lis = ['vendor_id', 'name', 'address', 'phone_number', 'email_id', 'status']
    order_data = lis[col_num]
    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        search_dict = {'active': 1, 'inactive': 0}
        if search_term.lower() in search_dict:
            search_terms = search_dict[search_term.lower()]
            master_data = VendorMaster.objects.filter(status = search_terms,user=user.id).order_by(order_data)

        else:
            master_data = VendorMaster.objects.filter( Q(vendor_id__icontains = search_term) | Q(name__icontains = search_term) | Q(address__icontains = search_term) | Q(phone_number__icontains = search_term) | Q(email_id__icontains = search_term),user=user.id ).order_by(order_data)

            master_data = VendorMaster.objects.filter(Q(vendor_id__icontains=search_term) | Q(name__icontains=search_term) | Q(address__icontains=search_term) | Q(phone_number__icontains=search_term) | Q(email_id__icontains=search_term), user=user.id)
    else:
        master_data = VendorMaster.objects.filter(user=user.id).order_by(order_data)
    search_params = {}
    if col_1:
        search_params["vendor_id__icontains"] = col_1
    if col_2:
        search_params["name__icontains"] = col_2
    if col_3:
        search_params["address__icontains"] = col_3
    if col_4:
        search_params["phone_number__icontains"] = col_4
    if col_5:
        search_params["email_id__icontains"] = col_5
    if col_6:
        if (str(col_6).lower() in "active"):
            search_params["status__iexact"] = 1
        elif (str(col_6).lower() in "inactive"):
            search_params["status__iexact"] = 0
        else:
            search_params["status__iexact"] = "none"
    if search_params:
        search_params["user"] = user.id
        master_data = VendorMaster.objects.filter(**search_params).order_by(order_data)

    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)

    for data in master_data[start_index : stop_index]:
        status = 'Inactive'
        if data.status:
            status = 'Active'

        if data.phone_number:
            data.phone_number = int(float(data.phone_number))
        temp_data['aaData'].append(OrderedDict(( ('Vendor ID', data.id), ('Name', data.name), ('Address', data.address),
                                                 ('Phone Number', data.phone_number), ('Email', data.email_id), ('Status', status),
                                                 ('DT_RowId', data.id), ('DT_RowClass', 'results') )))

@csrf_exempt
@login_required
@get_admin_user
def get_vendor_data(request, user=''):
    data_id = request.GET['data_id']
    filter_params = {'vendor_id': data_id, 'user': user.id}
    data = get_or_none(VendorMaster, filter_params)
    return render(request, 'templates/toggle/update_vendor.html', {'data': data, 'update_vendor': VENDOR_FIELDS})

@csrf_exempt
@login_required
@get_admin_user
def update_vendor_values(request,user=''):
    data_id = request.GET['vendor_id']
    data = get_or_none(VendorMaster, {'vendor_id': data_id, 'user': user.id})
    for key, value in request.GET.iteritems():
        if key == 'status':
            if value == 'Active':
                value = 1
            else:
                value = 0
        setattr(data, key, value)

    data.save()
    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def raise_rwo_toggle(request, user=''):
    title = 'Raise Returnable Work Order'
    vendors = VendorMaster.objects.filter(user=user.id).values('vendor_id', 'name')
    return render(request, 'templates/toggle/raise_rwo_toggle.html', {'headers': RAISE_JO_HEADERS, 'title': title, 'vendors': vendors})

def validate_rwo(all_data, user):
    status = ''
    sku_status = []
    quantity_status = []
    price_status = []
    alter_status = []

    for key,value in all_data.iteritems():
        if not value:
            continue
        if not key:
            status = 'Supplier Name Missing'
        for val in value:
            sku = SKUMaster.objects.filter(wms_code = val[0], user=user.id)
            if not sku:
                sku_status.append(val[0])
            order_quantity = val[2]
            if not order_quantity:
                quantity_status.append(val[0])
            try:
                price = float(val[3])
            except:
                price_status.append(val[0])
            if val[1]:
                sku_code = SKUMaster.objects.filter(wms_code__iexact=val[1], user=user.id)
                if not sku_code:
                    alter_status.append(val[1])
    if sku_status:
        status += ' Invalid SKU Code '  + ', '.join(sku_status)
    if alter_status:
        status += ' Invalid Returnable Code ' + ', '.join(alter_status)
    if price_status:
        status += ' Price Missing for ' + ', '.join(price_status)
    if quantity_status:
        status += ' Quantity Missing for ' + ', '.join(quantity_status)

    return status

def insert_rwo(job_order_id, vendor_id):
    rwo_dict = copy.deepcopy(RWO_FIELDS)
    rwo_dict['job_order_id'] = job_order_id
    rwo_dict['vendor_id']  = vendor_id
    rw_order = RWOrder(**rwo_dict)
    rw_order.save()

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
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i], data_dict['material_quantity'][i], data_id ]})
    status = validate_jo(all_data, user.id, '')
    if not status:
        all_data = insert_jo(all_data, user.id, jo_reference, vendor_id)
        status = "Added Successfully"
    return HttpResponse(status)

@csrf_exempt
def get_saved_rworder(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['job_order__jo_reference', 'vendor__vendor_id', 'vendor__name', 'creation_date']
    if order_term:
        order_data = lis[col_num]
        if order_term == 'desc':
            order_data = '-%s' % order_data
        master_data = RWOrder.objects.filter(job_order__product_code__user=user.id, job_order__status='RWO').order_by(order_data).\
                                       values_list('job_order__jo_reference', flat=True)
    if search_term:
        master_data = RWOrder.objects.filter(Q(job_order__job_code__icontains=search_term) | Q(vendor__vendor_id__icontains=search_term) |
                                              Q(vendor__name__icontains=search_term) | Q(creation_date__regex=search_term),
                                              job_order__status='RWO', job_order__product_code__user=user.id).\
                                       values_list('job_order__jo_reference', flat=True).order_by(order_data)
    master_data = [ key for key,_ in groupby(master_data)]
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data_id in master_data[start_index:stop_index]:
        data = RWOrder.objects.filter(job_order__jo_reference=data_id, job_order__product_code__user=user.id, job_order__status='RWO')[0]
        checkbox = "<input type='checkbox' name='id' value='%s'>" % data_id
        temp_data['aaData'].append({'': checkbox, 'RWO Reference': data.job_order.jo_reference, 'Vendor ID': data.vendor.vendor_id,
                                    'Vendor Name': data.vendor.name, 'Creation Date': str(data.creation_date).split('+')[0],
                                    'DT_RowClass': 'results', 'DT_RowAttr': {'data-id': data.job_order.jo_reference}})

@csrf_exempt
@login_required
@get_admin_user
def saved_rwo_data(request, user=''):
    jo_reference = request.GET['data_id']
    all_data = {}
    title = "Update Returnable Work Order"
    record = RWOrder.objects.filter(job_order__jo_reference=jo_reference, job_order__product_code__user=user.id, job_order__status='RWO')
    for rec in record:
        jo_material = JOMaterial.objects.filter(job_order_id= rec.job_order.id,status=1)
        cond = (rec.job_order.product_code.sku_code, rec.job_order.product_quantity)
        for jo_mat in jo_material:
            all_data.setdefault(cond, [])
            all_data[cond].append({'material_code': jo_mat.material_code.sku_code, 'material_quantity': jo_mat.material_quantity,
                                   'id': jo_mat.id })
    return render(request, 'templates/toggle/raise_rwo_toggle.html', {'data': all_data, 'headers': RAISE_JO_HEADERS,
                                                                      'jo_reference': jo_reference, 'title': title, 'vendor': record[0].vendor})

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
            tot_pro_qty += int(p_quantity)
        if not data_dict['product_code'][i]:
            continue
        data_id = ''
        if data_dict['id'][i]:
            data_id = data_dict['id'][i]
        tot_mat_qty += int(data_dict['material_quantity'][i])
        cond = (data_dict['product_code'][i])
        all_data.setdefault(cond, [])
        all_data[cond].append({data_dict['product_quantity'][i]: [data_dict['material_code'][i], data_dict['material_quantity'][i], data_id ]})
    status = validate_jo(all_data, user.id, '')
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

@csrf_exempt
@get_admin_user
def generate_rm_rwo_data(request, user=''):
    all_data = {}
    title = 'Raise Returnable Order'
    for key, value in request.POST.iteritems():
        key = key.split(':')[0]
        cond = (key, value)
        bom_master = BOMMaster.objects.filter(product_sku__sku_code=key, product_sku__user=user.id)
        if bom_master:
            all_data.setdefault(cond, [])
            for bom in bom_master:
                all_data[cond].append({'material_code': bom.material_sku.sku_code, 'material_quantity': int(bom.material_quantity) * int(value),
                                       'id': ''})
        else:
            all_data[cond] = [{'material_code': '', 'material_quantity': '', 'id': ''}]
    vendors = VendorMaster.objects.filter(user=user.id).values('vendor_id', 'name')
    return render(request, 'templates/toggle/raise_rwo_toggle.html', {'headers': RAISE_JO_HEADERS, 'title': title, 'data': all_data,
                                                               'display': 'display-none', 'vendors': vendors})

@csrf_exempt
@get_admin_user
def update_shipment_status(request, user=''):
    data_dict = dict(request.GET.iterlists())
    for i in range(len(data_dict['id'])):
        shipment_info = ShipmentInfo.objects.get(id=data_dict['id'][i])
        tracking = ShipmentTracking.objects.filter(shipment_id=shipment_info.id, shipment__order__user=user.id, ship_status=data_dict['status'][i])
        if not tracking:
            ShipmentTracking.objects.create(shipment_id=shipment_info.id, ship_status=data_dict['status'][i], creation_date=NOW)
    return HttpResponse("Updated Successfully")

@csrf_exempt
@login_required
@get_admin_user
def save_stages(request, user=''):
    stages = request.GET.get('stage_names', '')
    stages = stages.split(',')
    all_stages = ProductionStages.objects.filter(user=user.id).values_list('stage_name', flat=True)
    index = 1
    for stage in stages:
        if not stage:
            continue
        stage_obj = ProductionStages.objects.filter(stage_name=stage, user=user.id)
        if not stage_obj:
            stage_dict = copy.deepcopy(STAGES_FIELDS)
            stage_dict['stage_name'] = stage
            stage_dict['user'] = user.id
            stage_dict['order'] = index
            new_stage = ProductionStages(**stage_dict)
            new_stage.save()
            index += 1
    deleted_stages = set(all_stages) - set(stages)
    for stage in deleted_stages:
        ProductionStages.objects.get(stage_name=stage, user=user.id).delete()
        job_ids = JobOrder.objects.filter(product_code__user=user.id, status__in=['grn-generated', 'pick_confirm']).values_list('id', flat=True)
        StatusTracking.objects.filter(status_value=stage, status_id__in=job_ids, status_type='JO').delete()
    return HttpResponse("Saved Successfully")

def generate_request_params(params):
    params_data = {}
    for key, value in params.iteritems():
        for count, val in enumerate(value):
            params_data.setdefault(count, {})[key] = val
    return params_data

@csrf_exempt
@login_required
@get_admin_user
def get_sku_stock_count(request, user=''):
    sku_code = request.GET.get('sku_code')
    data = {'status': 'Invalid SKU Code'}
    sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
    if not sku_master:
        return HttpResponse(json.dumps(data))

    sku_stock = StockDetail.objects.filter(sku__wms_code=sku_code, sku__user=user.id).aggregate(Sum('quantity'))
    data['status'] = 'Success'
    data['results'] = 0
    if sku_stock['quantity__sum']:
        data['results'] = sku_stock['quantity__sum']
    return HttpResponse(json.dumps(data))

@csrf_exempt
@login_required
@get_admin_user
def add_inventory_data(request, user=''):
    status=''
    invalid_locations = []
    invalid_skus = []
    stock_data_list = []
    stock = StockDetail.objects.filter(sku__user=user.id).order_by('-receipt_number')
    if stock:
        receipt_number = int(stock[0].receipt_number) + 1
    else:
        receipt_number = 1

    request_dict = generate_request_params(dict(request.POST.iterlists()))

    for index, data in request_dict.iteritems():
        if index == 0:
            receipt_type = data['receipt_type']

        if not data['wms_code']:
            continue

        location_data = LocationMaster.objects.filter(location=data['location'], zone__user=request.user.id)
        if not location_data:
            invalid_locations.append(data['location'])

        sku_master = SKUMaster.objects.filter(wms_code=data['wms_code'], user=user.id)
        if not sku_master:
            invalid_skus.append(data['wms_code'])

        if not location_data or not sku_master:
            continue
        sku_id = SKUMaster.objects.filter(wms_code=data['wms_code'], user=user.id)[0].id
        stock_data_list.append(StockDetail(receipt_number=receipt_number, receipt_date=datetime.datetime.now(), quantity=int(data['quantity']), status=1, updation_date=datetime.datetime.now(), location_id=location_data[0].id, sku_id=sku_id, receipt_type=receipt_type))

    if invalid_locations:
        status += 'Invalid locations: %s' % ','.join(invalid_locations)
    if invalid_skus:
        status += ' Invalid skus: %s' % ','.join(invalid_skus)
    if status:
        return HttpResponse(json.dumps(status))

    if stock_data_list:
        StockDetail.objects.bulk_create(stock_data_list)
    return HttpResponse(json.dumps('Inventory Added Successfully'))
