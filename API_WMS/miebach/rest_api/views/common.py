import xlsxwriter

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from django.contrib.auth import authenticate, login, logout as wms_logout
from miebach_admin.custom_decorators import login_required, get_admin_user
from django.contrib.auth.models import User
from miebach_admin.models import *
from miebach_utils import *
import pytz
from send_message import send_sms
from operator import itemgetter
from django.contrib.auth.models import User,Permission
from xlwt import Workbook, easyxf
from xlrd import open_workbook, xldate_as_tuple
import operator
from django.db.models import Q, F
from django.conf import settings

import csv
import hashlib
import os
from generate_reports import *
from num2words import num2words
import datetime
from utils import *
from django.core.serializers.json import DjangoJSONEncoder

log = init_logger('logs/common.log')
# Create your views here.

def process_date(value):
    value = value.split('/')
    value = datetime.date(int(value[2]), int(value[0]), int(value[1]))
    return value

def get_decimal_limit(user_id, value):
    decimal_limit = 0
    if get_misc_value('float_switch', user_id) == 'true':
        decimal_limit = 1
        if get_misc_value('float_switch', user_id, number=True):
            decimal_limit = get_misc_value('decimal_limit', user_id, number=True)
    return float(("%."+ str(decimal_limit) +"f") % (value))

def number_in_words(value):
    value = (num2words(int(round(value)), lang='en_IN')).capitalize()
    return value


def get_user_permissions(request, user):
    roles = {}
    label_perms = []
    configuration = list(MiscDetail.objects.filter(user=user.id).values('misc_type', 'misc_value'))
    if 'order_headers' not in map(lambda d: d['misc_type'], configuration):
        configuration.append({'misc_type': 'order_headers', 'misc_value': ''})
    config = dict(zip(map(operator.itemgetter('misc_type'), configuration), map(operator.itemgetter('misc_value'), configuration)))
    user_perms = PERMISSION_KEYS
    permissions = Permission.objects.all()
    user_perms = []
    ignore_list = ['session', 'webhookdata', 'swxmapping', 'userprofile', 'useraccesstokens', 'contenttype', 'user',
                   'permission','group','logentry']
    for permission in permissions:
        temp = permission.codename.split('_')[-1]
        if not temp in user_perms and not temp in ignore_list and 'add' in permission.codename:
            user_perms.append(permission.codename)
    for perm in user_perms:
        roles[perm] = get_permission(request.user, perm)
        if roles[perm]:
            label_perms.append(perm.replace('add_', ''))
    roles.update(config)
    return {'permissions': roles, 'label_perms': label_perms}

def get_label_permissions(request, user, role_perms):
    label_keys = copy.deepcopy(LABEL_KEYS)
    sub_label_keys = copy.deepcopy(PERMISSION_DICT)
    labels = {}
    for label in label_keys:
        if request.user.is_staff:
            labels[label] = True
        else:
            if set(map(lambda d: d[1], sub_label_keys[label])).intersection(role_perms):
                labels[label] = True
            else:
                labels[label] = False

    return labels

@get_admin_user
def add_user_permissions(request, response_data, user=''):
    status_dict = {1: 'true', 0: 'false'}
    multi_warehouse = 'false'
    user_profile = UserProfile.objects.get(user_id=user.id)
    request_user_profile = UserProfile.objects.get(user_id=request.user.id)
    show_pull_now = False
    integrations = Integrations.objects.filter(user=user.id, status=1)
    if integrations:
        show_pull_now = True
    #warehouses = UserGroups.objects.filter(Q(user__username=user.username) | Q(admin_user__username=user.username))
    #if warehouses:
    #    multi_warehouse = 'true'
    if user_profile.multi_warehouse:
        multi_warehouse = 'true'
    response_data['data']['userName'] = request.user.username
    response_data['data']['userId'] = request.user.id
    response_data['data']['roles'] = get_user_permissions(request, user)
    response_data['data']['roles']['labels'] = get_label_permissions(request, user, response_data['data']['roles']['label_perms'])
    response_data['data']['roles']['permissions']['is_superuser'] = status_dict[int(request.user.is_superuser)]
    response_data['data']['roles']['permissions']['is_staff'] = status_dict[int(request.user.is_staff)]
    response_data['data']['roles']['permissions']['multi_warehouse'] = multi_warehouse
    response_data['data']['roles']['permissions']['show_pull_now'] = show_pull_now
    response_data['data']['user_profile'] = {'first_name': request.user.first_name, 'last_name': request.user.last_name,
                                             'registered_date': get_local_date(request.user, user_profile.creation_date),
                                             'email': request.user.email,
                                             'trail_user': status_dict[int(user_profile.is_trail)], 'company_name': user_profile.company_name,
                                             'user_type': request_user_profile.user_type}

    setup_status ='false'
    if 'completed' not in user_profile.setup_status:
        setup_status = 'true'
    response_data['data']['roles']['permissions']['setup_status'] = setup_status
    if user_profile.is_trail:
        time_now = datetime.datetime.now().replace(tzinfo=pytz.timezone('UTC'))
        exp_time = get_local_date(request.user, time_now, send_date=1) - get_local_date(request.user, user_profile.creation_date, send_date=1)
        response_data['data']['user_profile']['expiry_days'] = 30 - int(exp_time.days)
    response_data['message'] = 'Success'
    return response_data

@csrf_exempt
def wms_login(request):
    """
    Checks if user is a valid user or not
    """

    response_data = {'data': {}, 'message': 'Fail'}
    username = request.POST.get('login_id', '')
    password = request.POST.get('password', '')
    status_dict = {1: 'true', 0: 'false'}

    if username and password:
        user = authenticate(username=username, password=password)

        if user and user.is_active:
            login(request, user)
            user_profile = UserProfile.objects.filter(user_id=user.id)

            if not user_profile:
                prefix = re.sub('[^A-Za-z0-9]+', '', user.username)[:3].upper()
                user_profile = UserProfile(user=user, phone_number='',
	                                           is_active=1, prefix=prefix, swx_id=0)
                user_profile.save()
        else:
            return HttpResponse(json.dumps(response_data), content_type='application/json')

        response_data = add_user_permissions(request, response_data)

    return HttpResponse(json.dumps(response_data), content_type='application/json')

@csrf_exempt
def create_user(request):
    """
    Creating a new User
    """
    full_name = request.POST.get('full_name', '')
    username = request.POST.get('username', '')
    password = request.POST.get('password', '')
    email = request.POST.get('email', '')
    if not username:
        username = email
    status = 'Missing required fields'
    if username and password:
        user = User.objects.filter(username=username, email=email)
        status = "User already exists"
        if not user:
            user = User.objects.create_user(username=username, email=email, password=password, first_name=full_name)
            user.save()
            hash_code = hashlib.md5(b'%s:%s' % (user.id, email)).hexdigest()
            if user:
                prefix = re.sub('[^A-Za-z0-9]+', '', user.username)[:3].upper()
                user_profile = UserProfile.objects.create(phone_number=request.POST.get('phone', ''),
                                                          company_name=request.POST.get('company', ''), user_id=user.id, api_hash=hash_code,
                                                          is_trail=1, prefix=prefix, setup_status='')
                user_profile.save()
            user.is_staff=1
            user.save()
            user = authenticate(username=username, password=password)
            login(request, user)
            status = 'User Added Successfully'
            BookTrial.objects.filter(email=email).update(status=0)
    return HttpResponse(json.dumps(status), content_type='application/json')

@csrf_exempt
@login_required
def status(request):
    """
    Checks if user is a valid user or not
    """

    response_data = {'data': {}, 'message': 'Fail'}
    status_dict = {1: 'true', 0: 'false'}

    if request.user.is_authenticated():
        response_data = add_user_permissions(request, response_data)
 
    return HttpResponse(json.dumps(response_data), content_type='application/json')

@csrf_exempt
def logout(request):
    wms_logout(request)
    return HttpResponse('success')

def get_trial_user_data(request):
    response = {'message': 'success', 'data':{}}
    hashcode = request.GET.get('hash_code')
    trial_data = BookTrial.objects.filter(hash_code = hashcode)
    if trial_data:
        data = trial_data[0]
        if not data.status:
            return HttpResponse(json.dumps({'message': 'Sign up completed'}), content_type='application/json')
        response['data']['full_name'] = data.full_name
        response['data']['email'] = data.email
        response['data']['company'] = data.company
        response['data']['phone'] = data.contact
        response['message'] = 'success'
    else:
        response['message'] = 'fail'
    return HttpResponse(json.dumps(response), content_type='application/json')

def get_search_params(request):
    search_params = {}
    filter_params = {}
    headers = []
    date_fields = ['from_date', 'to_date']
    data_mapping = {'start': 'start', 'length': 'length', 'draw': 'draw', 'search[value]': 'search_term',
                    'order[0][dir]': 'order_term',
                    'order[0][column]': 'order_index', 'from_date': 'from_date', 'to_date': 'to_date', 'wms_code': 'wms_code',
                    'supplier': 'supplier', 'sku_code': 'sku_code', 'category': 'sku_category', 'sku_category': 'sku_category', 'sku_type': 'sku_type',
                    'class': 'sku_class', 'zone_id': 'zone', 'location': 'location', 'open_po': 'open_po', 'marketplace': 'marketplace',
                    'special_key': 'special_key', 'brand': 'sku_brand', 'stage': 'stage', 'jo_code': 'job_code', 'sku_class': 'sku_class', 'sku_size':'sku_size'}
    int_params = ['start', 'length', 'draw', 'order[0][column]']
    filter_mapping = { 'search0': 'search_0', 'search1': 'search_1',
                       'search2': 'search_2', 'search3': 'search_3',
                       'search4': 'search_4', 'search5': 'search_5',
                       'search6': 'search_6', 'search7': 'search_7',
                       'search8': 'search_8', 'search9': 'search_9', 'search10': 'search_10', 'search11': 'search_11'}
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
        elif key in filter_mapping:
            filter_params[filter_mapping[key]] = value
        elif key == 'special_key':
            search_params[data_mapping[key]] = value

    return headers, search_params, filter_params

data_datatable = {#masters
                  'SKUMaster': 'get_sku_results', 'SupplierMaster': 'get_supplier_results',\
                  'SupplierSKUMappingMaster': 'get_supplier_mapping', 'CustomerMaster': 'get_customer_master',\
                  'BOMMaster':'get_bom_results', 'CustomerSKUMapping': 'get_customer_sku_mapping',\
                  'WarehouseMaster': 'get_warehouse_user_results', 'VendorMaster': 'get_vendor_master_results',\
                  'DiscountMaster':'get_discount_results', 'CustomSKUMaster': 'get_custom_sku_properties',\
                  'SizeMaster': 'get_size_master_data', 'PricingMaster': 'get_price_master_results', \
                  #inbound
                  'RaisePO': 'get_po_suggestions', 'ReceivePO': 'get_confirmed_po',\
                  'QualityCheck': 'get_quality_check_data', 'POPutaway': 'get_order_data',\
                  'ReturnsPutaway': 'get_order_returns_data', 'SalesReturns': 'get_order_returns',\
                  'RaiseST': 'get_raised_stock_transfer',\
                  #production
                  'RaiseJobOrder': 'get_open_jo', 'RawMaterialPicklist': 'get_jo_confirmed',\
                  'PickelistGenerated':'get_generated_jo', 'ReceiveJO': 'get_confirmed_jo',\
                  'PutawayConfirmation': 'get_received_jo', 'PutawayConfirmationSKU':'get_received_jo',
                  'ProductionBackOrders': 'get_rm_back_order_data',
                  'RaiseRWO': 'get_saved_rworder', 'ReceiveJOSKU': "get_confirmed_jo_all", \
                  'RawMaterialPicklistSKU': 'get_rm_picklist_confirmed_sku',\
                  #stock locator
                  'StockSummary': 'get_stock_results', 'OnlinePercentage': 'get_sku_stock_data',\
                  'StockDetail': 'get_stock_detail_results', 'CycleCount': 'get_cycle_count',\
                  'MoveInventory': 'get_move_inventory', 'InventoryAdjustment': 'get_move_inventory',\
                  'ConfirmCycleCount': 'get_cycle_confirmed','VendorStockTable': 'get_vendor_stock',\
                  'Available':'get_available_stock','Available+Intransit':'get_availintra_stock','Total': 'get_avinre_stock',
                  #outbound
                  'SKUView': 'get_batch_data', 'OrderView': 'get_order_results', 'OpenOrders': 'open_orders',\
                  'PickedOrders': 'open_orders', 'BatchPicked': 'open_orders',\
                  'ShipmentInfo':'get_customer_results', 'ShipmentPickedOrders': 'get_shipment_picked',\
                  'PullToLocate': 'get_cancelled_putaway',\
                  'StockTransferOrders': 'get_stock_transfer_orders', 'OutboundBackOrders': 'get_back_order_data',\
                  'CustomerOrderView': 'get_order_view_data', 'CustomerCategoryView': 'get_order_category_view_data',
                  #manage users
                  'ManageUsers': 'get_user_results', 'ManageGroups': 'get_user_groups',
                  #retail one
                  'channels_list': 'get_marketplace_data',
                  #Integrations
                  'OrderSyncTable': 'get_order_sync_issues'
                 }

def filter_by_values(model_obj, search_params, filter_values):
    data = filter_or_none(model_obj, search_params)
    data = data.values(*filter_values)
    return data

def filter_or_none(model_obj, search_params):
    data = model_obj.objects.filter(**search_params)
    return data

def get_or_none(model_obj, search_params):
    try:
        data = model_obj.objects.get(**search_params)
    except:
        data = ''
    return data

def get_misc_value(misc_type, user, number=False):
    misc_value = 'false'
    if number:
       misc_value = 0
    data = MiscDetail.objects.filter(user=user, misc_type=misc_type)
    if data:
        misc_value = data[0].misc_value
    return misc_value

def permissionpage(request,cond=''):
    if cond:
        return ((request.user.is_staff or request.user.is_superuser) or (cond in request.user.get_group_permissions()) or request.user.has_perm(cond))
    else:
        return (request.user.is_staff or request.user.is_superuser)

def get_permission(user, codename):
    in_group = False
    groups = user.groups.all()
    for grp in groups:
        in_group = codename in grp.permissions.values_list('codename', flat=True)
        if in_group:
            break
    return codename in user.user_permissions.values_list('codename', flat=True) or in_group

def get_filtered_params(filters, data_list):
    filter_params = {}
    for key, value in filters.iteritems():
        col_num = int(key.split('_')[-1])
        if value:
            filter_params[data_list[col_num] + '__icontains'] = value
    return filter_params

@csrf_exempt
def get_local_date(user, input_date, send_date=''):
    utc_time = input_date.replace(tzinfo=pytz.timezone('UTC'))
    user_details = UserProfile.objects.get(user_id = user.id)
    time_zone = 'Asia/Calcutta'
    if user_details.timezone:
        time_zone = user_details.timezone
    local_time = utc_time.astimezone(pytz.timezone(time_zone))
    if send_date:
        return local_time
    dt = local_time.strftime("%d %b, %Y %I:%M %p")
    return dt

@csrf_exempt
def get_user_results(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis  = ['username', 'first_name', 'email', 'id']
    group = ''
    admin_group = AdminGroups.objects.filter(user_id=user.id)
    if admin_group:
        group = admin_group[0].group
    if group:
        if search_term:
            master_data = group.user_set.filter(Q(username__icontains=search_term) | Q(first_name__icontains=search_term) |
                                                Q(email__icontains=search_term)).exclude(id=user.id)
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
def get_user_groups(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis  = ['Group Name', 'Members Count']
    group = ''
    #admin_group = AdminGroups.objects.filter(user_id=user.id)
    #if admin_group:
    #    group = admin_group[0].group
    #if group:
    if search_term:
        master_data = user.groups.filter(name__icontains=search_term).exclude(name=user.username)
    #elif order_term:
    #    if order_term == 'asc':
    #        master_data = group.user_set.filter().exclude(id=user.id).order_by(lis[col_num])
    #    else:
    #        master_data = group.user_set.filter().exclude(id=user.id).order_by("-%s" % lis[col_num])
    else:
        master_data = user.groups.exclude(name=user.username)
    temp_data['recordsTotal'] = len(master_data)
    temp_data['recordsFiltered'] = len(master_data)
    for data in master_data:
        member_count = data.user_set.all().exclude(username=user.username).count()
        group_name = (data.name).replace(user.username + ' ', '')
        temp_data['aaData'].append({'Group Name': group_name,'DT_RowClass': 'results', 'Members Count': member_count, 'DT_RowId': data.id})

    sort_col = lis[col_num]

    if order_term == 'asc':
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col))
    else:
        temp_data['aaData'] = sorted(temp_data['aaData'], key=itemgetter(sort_col), reverse=True)
    temp_data['aaData'] = temp_data['aaData'][start_index:stop_index]

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
        #add_extra_permissions(new_user)
        new_user.groups.add(group)
        status = 'Added Successfully'
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
def configurations(request, user=''):
    display_none = 'display: block;'
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
    float_switch = get_misc_value('float_switch', user.id)
    automate_invoice = get_misc_value('automate_invoice', user.id)
    show_mrp = get_misc_value('show_mrp', user.id)
    decimal_limit = get_misc_value('decimal_limit', user.id)
    picklist_sort_by = get_misc_value('picklist_sort_by', user.id)
    stock_sync = get_misc_value('stock_sync', user.id)
    auto_generate_picklist = get_misc_value('auto_generate_picklist', user.id)
    detailed_invoice = get_misc_value('detailed_invoice', user.id) 
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    internal_mails = get_misc_value('Internal Emails', user.id)
    all_groups = str(','.join(all_groups))

    order_manage = get_misc_value('order_manage', user.id)

    all_stages = ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True)
    all_stages = str(','.join(all_stages))

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
    return HttpResponse(json.dumps({'batch_switch': batch_switch, 'fifo_switch': fifo_switch, 'pos_switch': pos_switch,
                                                             'send_message': send_message, 'use_imei': use_imei, 'back_order': back_order,
                                                             'show_image': show_image, 'online_percentage': online_percentage,
                                                             'prefix': prefix, 'pallet_switch': pallet_switch,
                                                             'production_switch': production_switch, 'mail_alerts': mail_alerts,
                                                             'mail_inputs': mail_inputs, 'mail_options': MAIL_REPORTS_DATA,
                                                             'mail_reports': MAIL_REPORTS, 'data_range': data_range,
                                                             'report_freq': report_freq, 'email': email,
                                                             'reports_data': reports_data, 'display_none': display_none,
                                                             'internal_mails' : internal_mails,
                                                             'is_config': 'true', 'order_headers': ORDER_HEADERS_d,
                                                             'all_groups': all_groups, 'display_pos': display_pos,
                                                             'auto_po_switch': auto_po_switch, 'no_stock_switch': no_stock_switch,
                                                             'float_switch': float_switch, 'all_stages': all_stages,
                                                             'automate_invoice': automate_invoice, 'show_mrp': show_mrp,
                                                             'decimal_limit': decimal_limit, 'picklist_sort_by': picklist_sort_by,
                                                             'stock_sync': stock_sync, 'auto_generate_picklist': auto_generate_picklist,
                                                             'order_management' : order_manage, 'detailed_invoice': detailed_invoice}))

@csrf_exempt
def get_work_sheet(sheet_name, sheet_headers, f_name=''):
    if '.xlsx' in f_name:
        wb = xlsxwriter.Workbook(f_name)
        ws = wb.add_worksheet(sheet_name)
        header_style = wb.add_format({'bold': True})
    else:
        wb = Workbook()
        ws = wb.add_sheet(sheet_name)
        header_style = easyxf('font: bold on')
    for count, header in enumerate(sheet_headers):
        ws.write(0, count, header, header_style)
    return wb, ws

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
    try:
        wb, ws = get_work_sheet('skus', itemgetter(*excel_headers)(headers))
    except:
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
    path = 'static/excel_files/' + file_name + '.xls'
    if not os.path.exists('static/excel_files/'):
        os.makedirs('static/excel_files/')
    wb.save(path)
    path_to_file = '../' + path
    return HttpResponse(path_to_file)

def po_message(po_data, phone_no, user_name, f_name, order_date, ean_flag):
    data = '%s Orders for %s dated %s' %(user_name, f_name, order_date)
    total_quantity = 0
    total_amount = 0
    if ean_flag:
        for po in po_data:
            data += '\nD.NO: %s, Qty: %s' % (po[2], po[4])
            total_quantity += int(po[4])
            total_amount += int(po[6])
    else:
        for po in po_data:
            data += '\nD.NO: %s, Qty: %s' % (po[1], po[3])
            total_quantity += int(po[3])
            total_amount += int(po[5])
    data += '\nTotal Qty: %s, Total Amount: %s\nPlease check WhatsApp for Images' % (total_quantity,total_amount)
    send_sms(phone_no, data)

def order_creation_message(items, telephone, order_id):
    data = 'Your order with ID %s has been successfully placed for ' % order_id
    total_quantity = 0
    total_amount = 0
    items_data = []
    for item in items:
        sku_desc = (item[0][:30] + '..') if len(item[0]) > 30 else item[0]
        items_data.append('%s with Qty: %s' % (sku_desc, int(item[2])))
        total_quantity += int(item[2])
        total_amount += int(item[3])
    data += ', '.join(items_data)
    data += '\n\nTotal Qty: %s, Total Amount: %s' % (total_quantity,total_amount)
    send_sms(telephone, data)

def order_dispatch_message(order, user, order_qt = ""):

    data = 'Your order with ID %s has been successfully picked and ready for dispatch by %s %s :' % (order.order_id, user.first_name, user.last_name)
    total_quantity = 0
    total_amount = 0
    telephone = order.telephone
    items_data = []
    items = OrderDetail.objects.filter(order_id = order.order_id, order_code= order.order_code, user = user.id)
    for item in items:
        #sku_desc = (item.title[:30] + '..') if len(item.title) > 30 else item.title
        qty = int(order_qt.get(item.sku.sku_code, 0))
        if not qty:
            continue
        items_data.append('\n %s  Qty: %s' % (item.sku.sku_code, qty))
        total_quantity += qty
        total_amount += int((item.invoice_amount / item.quantity) * qty)
    data += ', '.join(items_data)
    data += '\n\nTotal Qty: %s, Total Amount: %s' % (total_quantity,total_amount)
    log.info(data)
    send_sms(telephone, data)

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

def add_misc_email(user, email):
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='email')
    if misc_detail:
        misc_detail[0].misc_value = email
        misc_detail[0].save()
    else:
        misc_detail = MiscDetail(user=user.id, misc_type='email', misc_value=email)
        misc_detail.save()

@csrf_exempt
@get_admin_user
def update_mail_configuration(request, user=''):

    data = {}
    selected = request.POST.getlist('selected[]')
    removed = request.POST.getlist('removed[]')
    frequency = request.POST.get('frequency')
    data_range = request.POST.get('range')
    email = request.POST.get('email', '')
    date_val = request.POST.get('date_val')

    for select_data in selected:
        misc_type = 'report_' + REPORTS_DATA[select_data.strip()]
        misc_detail = MiscDetail.objects.filter(user=user.id, misc_type=misc_type)
        if misc_detail:
            misc_detail[0].misc_value = 'true'
            misc_detail[0].save()
            continue

        misc_detail = MiscDetail(user=user.id, misc_type=misc_type, misc_value='true')
        misc_detail.save()

    for select_data in removed:
        misc_type = 'report_' + REPORTS_DATA[select_data.strip()]
        misc_detail = MiscDetail.objects.filter(user=user.id, misc_type=misc_type)
        if misc_detail:
            misc_detail[0].misc_value = 'false'
            misc_detail[0].save()
            continue

        misc_detail = MiscDetail(user=user.id, misc_type=misc_type, misc_value='false')
        misc_detail.save()

    if frequency:
        data_dict = {'user': user.id, 'misc_type': 'report_frequency'}
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
        misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='report_data_range')
        if misc_detail:
            misc_detail[0].misc_value = frequency
            misc_detail[0].save()
        else:
            misc_detail = MiscDetail(user=user.id, misc_type='report_data_range', misc_value=data_range)
            misc_detail.save()

    existing_emails = MiscDetail.objects.filter(misc_type='email', user=user.id).values_list('misc_value', flat=True)

    
    add_misc_email(user, email)

    return HttpResponse('Success')

@csrf_exempt
@get_admin_user
def get_internal_mails(request, user = ""):
    """ saving internal mails from config page """
    internal_emails = request.GET.get('internal_mails', '')

    MiscDetail.objects.update_or_create(user = user.id, misc_type='Internal Emails', defaults={'misc_value': internal_emails})

    return HttpResponse('Success')

@get_admin_user
def send_mail_reports(request, user=''):
    email = request.GET.get('mails', '')
    if email:
        add_misc_email(user, email)
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='email')
    if misc_detail and misc_detail[0].misc_value:
        MailReports().send_reports_mail(user, mail_now=True)
        return HttpResponse('Success')
    return HttpResponse('Email ids not found')

@csrf_exempt
def set_timezone(request):
    timezone = request.GET['tz']
    user_details = UserProfile.objects.filter(user_id = request.user.id)
    for user in user_details:
        if not user.timezone:
            user.timezone = timezone;
            user.save()
    return HttpResponse("Success")

def get_auto_po_quantity(sku, stock_quantity=''):
    if not stock_quantity:
        sku_stock = StockDetail.objects.filter(sku_id=sku.id, sku__user=sku.user, quantity__gt=0).aggregate(Sum('quantity'))['quantity__sum']
        stock_quantity = 0
        if sku_stock:
            stock_quantity = sku_stock

    purchase_order = PurchaseOrder.objects.exclude(status__in=['location-assigned', 'confirmed-putaway']).\
                                           filter(open_po__sku__user=sku.user, open_po__sku_id=sku.id, open_po__vendor_id__isnull=False).\
                                           values('open_po__sku_id').annotate(total_order=Sum('open_po__order_quantity'),
                                           total_received=Sum('received_quantity'))

    production_orders = JobOrder.objects.filter(product_code_id=sku.id, product_code__user=sku.user).\
                                         exclude(status__in=['open', 'confirmed-putaway']).values('product_code_id').\
                                         annotate(total_order=Sum('product_quantity'), total_received=Sum('received_quantity'))
    production_quantity = 0
    if production_orders:
        production_order = production_orders[0]
        diff_quantity = float(production_order['total_order']) - float(production_order['total_received'])
        if diff_quantity > 0:
            production_quantity = diff_quantity

    transit_quantity = 0
    if purchase_order:
        purchase_order = purchase_order[0]
        diff_quantity = float(purchase_order['total_order']) - float(purchase_order['total_received'])
        if diff_quantity > 0:
            transit_quantity = diff_quantity

    raise_quantity = int(sku.threshold_quantity) - (stock_quantity + transit_quantity + production_quantity)
    if raise_quantity < 0:
        raise_quantity = 0

    return int(raise_quantity)


@csrf_exempt
def auto_po(wms_codes, user):
    sku_codes = SKUMaster.objects.filter(wms_code__in=wms_codes, user=user, threshold_quantity__gt=0)
    for sku in sku_codes:
        supplier_id = SKUSupplier.objects.filter(sku_id=sku.id, sku__user=user).order_by('preference')
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
                if not supplier_id[0].moq:
                    po_suggestions['order_quantity'] = get_auto_po_quantity(sku, stock_quantity=total_sku)
                
                po_suggestions['status'] = 'Automated'
                po_suggestions['price'] = supplier_id[0].price
                if po_suggestions['order_quantity'] > 0:
                    po = OpenPO(**po_suggestions)
                    po.save()

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

def alphanum_validation(cell_data, check_type, index_status, row_idx):
    if isinstance(cell_data, (int, float)):
        cell_data = int(cell_data)
    cell_data = str(cell_data)
    error_code = anvalid(cell_data)
    if error_code:
        index_status.setdefault(row_idx, set()).add(error_code % check_type)
    return index_status

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
        move_quantity = float(quantity)
    else:
        return 'Quantity should not be empty'
    stocks = StockDetail.objects.filter(sku_id=sku_id, location_id=source[0].id, sku__user=user.id)
    stock_count = stocks.aggregate(Sum('quantity'))['quantity__sum']
    reserved_quantity = PicklistLocation.objects.exclude(stock=None).filter(stock__sku_id=sku_id, stock__sku__user=user.id, status=1,
                                                         stock__location_id=source[0].id).aggregate(Sum('reserved'))['reserved__sum']
    if reserved_quantity:
        if (stock_count - reserved_quantity) < float(quantity):
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
        dest_stocks = StockDetail(receipt_number=1, receipt_date=datetime.datetime.now(), quantity=float(quantity), status=1,
                                  creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now(), location_id=dest[0].id,
                                  sku_id=sku_id)
        dest_stocks.save()
    else:
        dest_stocks = dest_stocks[0]
        dest_stocks.quantity += float(quantity)
    dest_stocks.save()

    data_dict = copy.deepcopy(CYCLE_COUNT_FIELDS)
    data_dict['cycle'] = cycle_id
    data_dict['sku_id'] = sku_id
    data_dict['location_id'] = source[0].id
    data_dict['quantity'] = quantity
    data_dict['seen_quantity'] = 0
    data_dict['status'] = 0
    data_dict['creation_date'] = datetime.datetime.now()
    data_dict['updation_date'] = datetime.datetime.now()

    cycle_instance = CycleCount.objects.filter(cycle=cycle_id, location_id=source[0].id, sku_id=sku_id)
    if not cycle_instance:
        dat = CycleCount(**data_dict)
        dat.save()
    else:
        cycle_instance = cycle_instance[0]
        cycle_instance.quantity = float(cycle_instance.quantity) + quantity
        cycle_instance.save()
    data_dict['location_id'] = dest[0].id
    data_dict['quantity'] = quantity
    cycle_instance = CycleCount.objects.filter(cycle=cycle_id, location_id=dest[0].id, sku_id=sku_id)
    if not cycle_instance:
        dat = CycleCount(**data_dict)
        dat.save()
    else:
        cycle_instance = cycle_instance[0]
        cycle_instance.quantity = float(cycle_instance.quantity) + quantity
        cycle_instance.save()

    data = copy.deepcopy(INVENTORY_FIELDS)
    data['cycle_id'] = cycle_id
    data['adjusted_location'] = dest[0].id
    data['adjusted_quantity'] = quantity
    data['creation_date'] = datetime.datetime.now()
    data['updation_date'] = datetime.datetime.now()

    inventory_instance = InventoryAdjustment.objects.filter(cycle_id=cycle_id, adjusted_location=dest[0].id)
    if not inventory_instance:
        dat = InventoryAdjustment(**data)
        dat.save()
    else:
        inventory_instance = inventory_instance[0]
        inventory_instance.adjusted_quantity += float(inventory_instance.adjusted_quantity) + quantity
        inventory_instance.save()

    return 'Added Successfully'

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
    if quantity == '':
        return 'Quantity should not be empty'

    total_stock_quantity = 0
    if quantity:
        quantity = float(quantity)
        stocks = StockDetail.objects.filter(sku_id=sku_id, location_id=location[0].id, sku__user=user.id)
        for stock in stocks:
            total_stock_quantity += float(stock.quantity)

        remaining_quantity = total_stock_quantity - quantity
        for stock in stocks:
            if total_stock_quantity < quantity:
                stock.quantity += abs(remaining_quantity)
                stock.save()
                break
            else:
                stock_quantity = float(stock.quantity)
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
            dest_stocks = StockDetail(receipt_number=1, receipt_date=datetime.datetime.now(), quantity=float(quantity), status=1,
                                      creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now(), location_id=location[0].id,
                                      sku_id=sku_id)
            dest_stocks.save()
    if quantity == 0:
        StockDetail.objects.filter(sku_id=sku_id, location__location=location[0].location, sku__user=user.id).update(quantity=0)
        location[0].filled_capacity = 0
        location[0].save()

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

def update_picklist_locations(pick_loc, picklist, update_picked, update_quantity=''):
    for pic_loc in pick_loc:
        if float(pic_loc.reserved) >= update_picked:
            pic_loc.reserved = float(pic_loc.reserved) - update_picked
            if update_quantity:
                pic_loc.quantity = float(pic_loc.quantity) - update_picked
            update_picked = 0
        elif float(pic_loc.reserved) < update_picked:
            update_picked = update_picked - pic_loc.reserved
            if update_quantity:
                pic_loc.quantity = 0
            pic_loc.reserved = 0
        if pic_loc.reserved <= 0:
            pic_loc.status = 0
        pic_loc.save()
        if not update_picked:
            break

@csrf_exempt
@login_required
@get_admin_user
def add_group_data(request, user=''):
    permissions = Permission.objects.all()
    prod_stages = ProductionStages.objects.filter(user=user.id).values_list('stage_name',flat=True)
    brands = Brands.objects.filter(user=user.id).values_list('brand_name',flat=True)
    perms_list = []
    ignore_list = ['session', 'webhookdata', 'swxmapping', 'userprofile', 'useraccesstokens', 'contenttype', 'user',
                   'permission','group','logentry']
    permission_dict = copy.deepcopy(PERMISSION_DICT)
    reversed_perms = {}
    for key, value in permission_dict.iteritems():
        sub_perms = permission_dict[key]
        if len(sub_perms) == 2:
            reversed_perms[sub_perms[1]] = sub_perms[0]
        else:
            for i in sub_perms:
                reversed_perms[i[1]] = i[0]
    for permission in permissions:
        temp = permission.codename.split('_')[-1]
        if not temp in perms_list and not temp in ignore_list:
            if temp in reversed_perms.keys() and reversed_perms[temp] not in perms_list:
                perms_list.append(reversed_perms[temp])
    return HttpResponse(json.dumps({'perms_list': perms_list, 'prod_stages': list(prod_stages), 'brands': list(brands)}))

@csrf_exempt
@login_required
@get_admin_user
def add_group(request, user=''):
    perm_selected_list = ''
    stages_list = ''
    selected_list = ''
    brands_list = ''
    group = ''
    permission_dict = copy.deepcopy(PERMISSION_DICT)
    reversed_perms = {} 
    for key, value in permission_dict.iteritems():
        sub_perms = permission_dict[key]
        for i in sub_perms:
            reversed_perms[i[1]] = i[0] 
    #reversed_perms = OrderedDict(( ([(value, key) for key, value in permission_dict.iteritems()]) ))
    selected = request.POST.get('perm_selected')
    stages = request.POST.get('stage_selected')
    brands = request.POST.get('brand_selected')
    if selected:
        selected_list = selected.split(',')
    if stages:
        stages_list = stages.split(',')
    if brands:
        brands_list = brands.split(',')

    name = request.POST.get('name')
    if name:
        name = user.username + ' ' + name
    group_exists = Group.objects.filter(name=name)
    if group_exists:
         return HttpResponse('Group Name already exists')
    if not group_exists and (selected_list or stages_list or brands_list):
        group,created = Group.objects.get_or_create(name=name)
        if stages_list:
            stage_group = GroupStages.objects.create(group = group)
        if brands_list:
            brand_group = GroupBrand.objects.create(group = group)
        for stage in stages_list:
            if not stage:
                continue
	        stage_obj = ProductionStages.objects.filter(stage_name = stage, user=user.id)
            if stage_obj:
                stage_group.stages_list.add(stage_obj[0])
                stage_group.save()
        for brand in brands_list:
            if not brand:
                continue
            brand_obj = Brands.objects.filter(brand_name=brand, user=user.id)
            if brand_obj:
                brand_group.brand_list.add(brand_obj[0])
                brand_group.save()
        for perm in selected_list:
            if not perm:
                continue
            for key, value in permission_dict.iteritems():
                sub_perms = permission_dict[key]
                if len(sub_perms) == 2:
                    if sub_perms[0] == perm:
                        permi = sub_perms[1]
                        permissions = Permission.objects.filter(codename__icontains=permi)
                        for permission in permissions:
                            group.permissions.add(permission)
                else:
                    for i in sub_perms:
                        if i[0] == perm:
                            permi = i[1]
                            #perm = permission_dict.get(perm, '')
                            permissions = Permission.objects.filter(codename__icontains=permi)
                            for permission in permissions:
                                group.permissions.add(permission)
        user.groups.add(group)
    return HttpResponse('Updated Successfully')

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
                i_name = (i.name).replace(user.username + ' ', '')
                group_names.append(i_name)
        total_groups = []
        for group in groups:
            group_name = (group.name).replace(user.username + ' ', '')
            total_groups.append(group_name)
    return HttpResponse(json.dumps({'username': cur_user.username, 'first_name': cur_user.first_name, 'groups': total_groups,
                  'user_groups': group_names, 'id': cur_user.id }))

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
    modified_list = [request.user.username + ' ' + s for s in selected_list]
    user_groups = request.user.groups.filter()
    exclude_group = AdminGroups.objects.filter(user_id=request.user.id)
    if exclude_group:
        exclude_name = exclude_group[0].group.name
    for group in user_groups:
        if group.name in selected_list or group.name in modified_list:
            user.groups.add(group)
        else:
            if exclude_name:
                if not group.name == exclude_name:
                    group.user_set.remove(user)
    if request.GET['first_name']:
        user.first_name = request.GET['first_name']
        user.save()
    return HttpResponse('Updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def get_update_setup_state(request, user=''):
    user_profile = UserProfile.objects.get(user_id=user.id)
    step_count = request.POST.get('step_count', '')
    if step_count:
        user_profile.setup_status = step_count
        if step_count == '3':
            user_profile.setup_status = 'completed'
        user_profile.save()
    data = {'username': user.username, 'email': user.email, 'current_state': user_profile.setup_status}
    return HttpResponse(json.dumps({'message': 'success', 'data': data}))

@csrf_exempt
@login_required
@get_admin_user
def load_demo_data(request, user=''):
    from delete_demo_data import delete_user_demo_data
    from rest_api.views import *

    user_profile = UserProfile.objects.get(user_id=user.id)

    delete_user_demo_data(user.id)

    upload_files_path = OrderedDict(( ('sku_upload', {'file_name': 'sku_form.xls', 'function_name': 'sku_excel_upload'}),
                                ('location_upload', { 'file_name': 'location_form.xls', 'function_name': 'process_location'}),
                                ('supplier_upload', { 'file_name': 'supplier_form.xls', 'function_name': 'supplier_excel_upload'}),
                                ('inventory_upload', { 'file_name': 'inventory_form.xls', 'function_name': 'inventory_excel_upload'}),
                                ('order_upload', { 'file_name': 'order_form.xls', 'function_name': 'order_csv_xls_upload'}),
                                ('purchase_order_upload', { 'file_name': 'purchase_order_form.xls',
                                 'function_name': 'purchase_order_excel_upload'})

                             ))

    for key, value in upload_files_path.iteritems():
        open_book = open_workbook(os.path.join(settings.BASE_DIR + "/rest_api/demo_data/", value['file_name']))
        open_sheet = open_book.sheet_by_index(0)
        func_params = [request, open_sheet, user]
        if key in ['order_upload', 'sku_upload']:
            func_params.append(open_sheet.nrows)
            func_params.append(value['file_name'])
        elif key in ['supplier_upload', 'purchase_order_upload']:
            func_params.append(True)
        eval(value['function_name'])(*func_params)

    if request.GET.get('first_time', ''):
        user_profile.setup_status = 'demo-completed'
        user_profile.save()

    return HttpResponse('success')

@csrf_exempt
@login_required
@get_admin_user
def clear_demo_data(request, user=''):
    from delete_demo_data import delete_user_demo_data
    delete_status = 'Cannot delete for this user'
    user_profile = UserProfile.objects.get(user_id=user.id)
    if user_profile.is_trail:
        delete_user_demo_data(user.id)
        delete_status = 'Success'
    

    return HttpResponse(delete_status)

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

@csrf_exempt
@login_required
@get_admin_user
def search_wms_codes(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    data_id = request.GET.get('q', '')
    sku_type = request.GET.get('type', '')
    extra_filter = {}
    data_exact = sku_master.filter(Q(wms_code__iexact = data_id) | Q(sku_desc__iexact = data_id), user=user.id).order_by('wms_code')
    exact_ids = list(data_exact.values_list('id', flat=True))
    data = sku_master.exclude(id__in=exact_ids).filter(Q(wms_code__icontains = data_id) | Q(sku_desc__icontains = data_id),
                              user=user.id).order_by('wms_code')
    data = list(chain(data_exact, data))
    wms_codes = []
    count = 0
    if data:
        for wms in data:
            if not sku_type in ['FG', 'RM', 'CS']:
                wms_codes.append(str(wms.wms_code))
            elif wms.sku_type in ['FG', 'RM', 'CS']:
                wms_codes.append(str(wms.wms_code))
            if len(wms_codes) >= 10:
                break
    return HttpResponse(json.dumps(wms_codes))

def get_order_id(user_id):
    order_detail_id = OrderDetail.objects.filter(user=user_id, order_code__in=['MN', 'Delivery Challan', 'sample', 'R&D', 'CO']).order_by('-order_id')
    if order_detail_id:
        order_id = int(order_detail_id[0].order_id) + 1
    else:
        order_id = 1001

    return order_id

def check_and_update_stock(wms_codes, user):
    stock_sync = get_misc_value('stock_sync', user.id)
    if not stock_sync == 'true':
        return
    from rest_api.views.easyops_api import *
    integrations = Integrations.objects.filter(user=user.id)
    stock_instances = StockDetail.objects.exclude(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE']).filter(sku__wms_code__in=wms_codes,
                                          sku__user=user.id).values('sku__wms_code').distinct().annotate(total_sum=Sum('quantity'))

    reserved_instances = Picklist.objects.exclude(order__order_code='MN').filter(status__icontains='picked', order__user=user.id,
                                                  picked_quantity__gt=0, order__sku__wms_code__in=wms_codes).\
                                          values('order__sku__wms_code').distinct().\
                                         annotate(total_reserved=Sum('picked_quantity'))
    stocks = map(lambda d: d['sku__wms_code'], stock_instances)
    stocks = [(str(x)).lower() for x in stocks]
    stocks_quantities = map(lambda d: d['total_sum'], stock_instances)
    reserveds = map(lambda d: d['order__sku__wms_code'], reserved_instances)
    reserveds = [(str(x)).lower() for x in reserveds]
    reserved_quantities = map(lambda d: d['total_reserved'], reserved_instances)
    for integrate in integrations:
        data = []
        obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
        for wms_code in wms_codes:
            wms_code = (str(wms_code)).lower()
            stock_quantity = 0
            reserved_quantity = 0
            if wms_code in stocks:
                stock_quantity = stocks_quantities[stocks.index(wms_code)]
            if wms_code in reserveds:
                reserved_quantity = reserved_quantities[reserveds.index(wms_code)]
            sku_count = float(stock_quantity) + float(reserved_quantity)
            sku_count = int(sku_count)
            if sku_count < 0:
                sku_count = 0
            data.append({'sku': wms_code, 'quantity': sku_count})
        try:
            obj.update_sku_count(data=data, user=user)
        except:
            continue

def get_order_json_data(user, mapping_id='', mapping_type='', sku_id='', order_ids=[]):
    extra_data = []
    product_images = []
    sku_fields = SKUFields.objects.filter(sku_id=sku_id, field_type='product_attribute')
    jo_order_mapping = OrderMapping.objects.filter(mapping_id=mapping_id, mapping_type=mapping_type, order__user=user.id)
    for jo_mapping in jo_order_mapping:
        order_json = OrderJson.objects.filter(order_id=jo_mapping.order_id)
        if order_json:
            extra_data = eval(order_json[0].json_data)
        if jo_mapping.order:
            order_id = str(jo_mapping.order.order_code) + str(jo_mapping.order.order_id)
            if jo_mapping.order.original_order_id:
                order_id = jo_mapping.order.original_order_id
            order_ids.append(order_id)
        if not product_images and jo_mapping.order.sku:
            product_images = [jo_mapping.order.sku.image_url]

    if sku_fields and not product_images:
        product_attributes = list(ProductAttributes.objects.filter(id=sku_fields[0].field_id))
        if product_attributes:
            product_images = list(ProductImages.objects.filter(image_id=product_attributes[0].product_property_id,
                                                               image_type='product_property').values_list('image_url', flat=True))

    return extra_data, product_images, order_ids

def check_and_update_order(user, order_id):
    from rest_api.views.easyops_api import *
    user = User.objects.get(id=user)
    integrations = Integrations.objects.filter(user=user.id)
    for integrate in integrations:
        obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
        try:
            obj.confirm_picklist(order_id, user=user)
        except:
            continue

def get_invoice_number(user):
    invoice_number = 1
    invoice_detail = InvoiceDetail.objects.filter(user.id).order_by('-invoice_number')
    if invoice_detail:
        invoice_number = int(invoice_detail[0].invoice_number) + 1
    return invoice_number

def get_invoice_data(order_ids, user, merge_data = ""):
    data = []
    user_profile = UserProfile.objects.get(user_id=user.id)
    order_date = ''
    order_id = ''
    marketplace = ''
    total_quantity = 0
    total_amt = 0
    total_invoice = 0
    total_tax = 0
    total_mrp = 0
    customer_details = []
    consignee = ''
    order_no = ''
    invoice_date = datetime.datetime.now()
    if order_ids:
        order_ids = order_ids.split(',')
        order_data = OrderDetail.objects.filter(id__in=order_ids)
        picklist = Picklist.objects.filter(order_id__in=order_ids).order_by('-updation_date')
        picklist_obj = picklist
        if picklist:
            invoice_date = picklist[0].updation_date
        for dat in order_data:
            order_id = dat.original_order_id
            order_no = str(dat.order_id)
            if not order_id:
                order_id = dat.order_code + str(dat.order_id)
            title = dat.title
            if not title:
                title = dat.sku.sku_desc
            if ':' in dat.sku.sku_desc:
                title = dat.sku.sku_desc.split(':')[0]
            if not order_date:
                order_date = get_local_date(user, dat.creation_date, send_date='true')
                order_date = order_date.strftime("%d %b %Y")
            if dat.customer_id and dat.customer_name and not customer_details:
                customer_details = list(CustomerMaster.objects.filter(user=user.id, customer_id=dat.customer_id,
                                                                      name=dat.customer_name).\
                                                          values('customer_id', 'name', 'email_id', 'tin_number', 'address',
                                                                 'credit_period', 'phone_number'))
                if customer_details:
                    consignee = customer_details[0]['name'] + '\n' + customer_details[0]['address'] + "\nCall: " \
                                + customer_details[0]['phone_number'] + "\nEmail: " + customer_details[0]['email_id']
            if not marketplace:
                marketplace = dat.marketplace
                if marketplace == 'Myntra':
                    marketplace = 'Myntra Designs Pvt Ltd\nSSN Logistics Pvt Ltd, B-2, Antariksha Lodgidrome Warehousing Complex, Opp\
                                   Vashere HP petrol pump Aamne-sape, Pagdha, Kalyan rd,Bhiwandi - 421302\
                                   TIN: 27590747736'
            tax = 0
            vat = 5.5
            discount = 0
            mrp_price = dat.sku.mrp
            order_summary = CustomerOrderSummary.objects.filter(order__user=user.id, order_id=dat.id)
            if order_summary:
                tax = order_summary[0].tax_value
                vat = order_summary[0].vat
                mrp_price = order_summary[0].mrp
                discount = order_summary[0].discount
            else:
                tax = float(float(dat.invoice_amount)/100) * vat

            #total_invoice += float(dat.invoice_amount)
            #total_quantity += int(dat.quantity)
            #total_quantity =picklist_obj.filter(order__sku__sku_code=dat.sku.sku_code).aggregate(Sum('picked_quantity'))['picked_quantity__sum']
            total_tax += float(tax)
            total_mrp += float(mrp_price)

            picklist = Picklist.objects.exclude(order_type='combo').filter(order_id=dat.id).\
                                        aggregate(Sum('picked_quantity'))['picked_quantity__sum']
            quantity = picklist

            if merge_data:
                quantity_picked = merge_data.get(dat.sku.sku_code, "")
                if quantity_picked:
                    quantity = float(quantity_picked)
                else:
                    continue

            if not picklist:
                picklist = Picklist.objects.filter(order_id=dat.id, order_type='combo', picked_quantity__gt=0).\
                                            annotate(total=Sum('picked_quantity'))
                if picklist:
                    quantity = picklist[0].total

            unit_price = ((float(dat.invoice_amount)/ float(dat.quantity))) - discount - (tax/float(dat.quantity))
            invoice_amount = (float(dat.invoice_amount)/ float(dat.quantity)) * quantity
            unit_price = "%.2f" % unit_price
            total_invoice += invoice_amount
            total_quantity += quantity

            data.append({'order_id': order_id, 'sku_code': dat.sku.sku_code, 'title': title, 'invoice_amount': str(invoice_amount),
                         'quantity': quantity, 'tax': "%.2f" % (tax/float(dat.quantity) * quantity), 'unit_price': unit_price,
                         'vat': vat, 'mrp_price': mrp_price, 'discount': discount, 'sku_class': dat.sku.sku_class})

    invoice_date = get_local_date(user, invoice_date, send_date='true')
    invoice_date = invoice_date.strftime("%d %b %Y")
    order_charges = {}

    total_invoice_amount = total_invoice
    if order_id:
        order_charge_obj = OrderCharges.objects.filter(user_id=user.id, order_id=order_id)
        order_charges = list(order_charge_obj.values('charge_name', 'charge_amount'))
        total_charge_amount = order_charge_obj.aggregate(Sum('charge_amount'))['charge_amount__sum']
        if total_charge_amount:
            total_invoice_amount = float(total_charge_amount) + total_invoice

    total_amt = "%.2f" % (float(total_invoice) - float(total_tax))
    invoice_data = {'data': data, 'company_name': user_profile.company_name, 'company_address': user_profile.address,
                    'order_date': order_date, 'email': user.email, 'marketplace': marketplace, 'total_amt': total_amt,
                    'total_quantity': total_quantity, 'total_invoice': "%.2f" % total_invoice, 'order_id': order_id,
                    'customer_details': customer_details, 'order_no': order_no, 'total_tax': "%.2f" % total_tax, 'total_mrp': total_mrp,
                    'invoice_no': 'TI/1116/' + order_no, 'invoice_date': invoice_date, 'price_in_words': number_in_words(total_invoice),
                    'order_charges': order_charges, 'total_invoice_amount': "%.2f" % total_invoice_amount, 'consignee': consignee}

    return invoice_data

def get_sku_categories_data(request, user, request_data={}, is_catalog=''):
    if not request_data:
        request_data = request.GET
    filter_params = {'user': user.id}
    sku_brand = request_data.get('brand', '')
    sku_category = request_data.get('category', '')
    if not is_catalog:
        is_catalog = request_data.get('is_catalog', '')
    sale_through = request_data.get('sale_through', '')
    size_dict = request_data.get('size_filter', '')
    if sku_brand:
        filter_params['sku_brand'] = sku_brand
    if sku_category:
        filter_params['sku_category'] = sku_category
    if is_catalog:
        filter_params['status'] = 1
    if sale_through:
        filter_params['sale_through__iexact'] = sale_through

    sku_master = SKUMaster.objects.filter(**filter_params)

    categories = list(sku_master.exclude(sku_category='').filter(**filter_params).values_list('sku_category', flat=True).distinct())
    brands = list(sku_master.exclude(sku_brand='').values_list('sku_brand', flat=True).distinct())
    sizes = list(sku_master.exclude(sku_brand='').values_list('sku_size', flat=True).order_by('sequence').distinct())
    sizes = list(OrderedDict.fromkeys(sizes))
    _sizes = {}
    integer = []
    character = []
    for size in sizes:
        try:
            integer.append(int(eval(size)))
        except:
            character.append(size)
    _sizes = {'type2': integer, 'type1': character}
    return brands, sorted(categories), _sizes


def get_sku_available_stock(user, sku_masters, query_string, size_dict):
    selected_sizes = [i for i in size_dict if size_dict[i] not in ["", 0]]
    classes = list(sku_masters.values_list('sku_class', flat=True).distinct())
    stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values(query_string).distinct().\
                                     annotate(in_stock=Sum('quantity'))
    stock_query = "stock__%s" %(query_string)
    reserved_quantities = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1).values(stock_query).distinct().\
                                       annotate(in_reserved=Sum('reserved'))
    stock_skus = map(lambda d: d[query_string], stock_objs)
    stock_quans = map(lambda d: d['in_stock'], stock_objs)
    reserved_skus = map(lambda d: d[stock_query], reserved_quantities)
    reserved_quans = map(lambda d: d['in_reserved'], reserved_quantities)
    for product in sku_masters:
        _class = product.sku_class

        if _class not in classes:
            continue

        new_sizes = []
        sizes_exist = sku_masters.filter(sku_class = _class).values_list('sku_size', flat=True)
        for size in sizes_exist:
            try:
                new_sizes.append(str(int(eval(size))))
            except:
                new_sizes.append(size)

        if not (set(selected_sizes) < set(new_sizes)):
            classes.remove(_class)
            continue

        total_quantity = 0
        if product.sku_code in stock_skus:
            total_quantity = stock_quans[stock_skus.index(product.sku_code)]
        if product.sku_code in reserved_skus:
            total_quantity = total_quantity - float(reserved_quans[reserved_skus.index(product.sku_code)])
        try:
            _sizes = str(int(eval(product.sku_size)))
        except:
            _sizes = str(product.sku_size)


        qty = size_dict.get(_sizes, 0)
        if not qty:
            qty = 0
        if total_quantity < int(qty):
            classes.remove(_class)
    return classes

def resize_image(url, user):

    path = 'static/images/resized/'
    folder = str(user.id)

    height = 600
    width = 400

    if url:
        new_file_name = url.split("/")[-1].split(".")[0]+"_"+str(height)+"_"+str(width)+"."+url.split(".")[1]
        file_name = url.split(".")
        file_name = "%s_%s_%s.%s" %(file_name[0], height, width, file_name[1])

        if not os.path.exists(path + folder):
            os.makedirs(path + folder)

        if os.path.exists(path+folder+"/"+new_file_name):
            return "/"+path+folder+"/"+new_file_name;

        else:
            from PIL import Image
            temp_url = url[1:]
            image = Image.open(temp_url)
            imageresize = image.resize((height ,width), Image.ANTIALIAS)
            imageresize.save(path+folder+"/"+new_file_name, 'JPEG', quality=75)
            return "/"+path+folder+"/"+new_file_name
    else:
        return url

def get_sku_catalogs_data(request, user, request_data={}, is_catalog=''):
    if not request_data:
        request_data = request.GET
    from rest_api.views.outbound import get_style_variants
    filter_params = {'user': user.id}
    get_values = ['wms_code', 'sku_desc', 'image_url', 'sku_class', 'price', 'mrp', 'id', 'sku_category', 'sku_brand', 'sku_size', 'style_name', 'sale_through']
    sku_category = request_data.get('category', '')
    sku_class = request_data.get('sku_class', '')
    sku_brand = request_data.get('brand', '')
    sku_category = request_data.get('category', '')
    if not is_catalog:
        is_catalog = request_data.get('is_catalog', '')
    indexes = request_data.get('index', '0:20')
    is_file = request_data.get('file', '')
    sale_through = request_data.get('sale_through', '')

    if not indexes:
        indexes = '0:20'
    if sku_brand:
        filter_params['sku_brand'] = sku_brand
    if sku_category:
        filter_params['sku_category'] = sku_category
    if is_catalog:
        filter_params['status'] = 1
    if sale_through:
        filter_params['sale_through__iexact'] = sale_through

    start, stop = indexes.split(':')
    start, stop = int(start), int(stop)
    if sku_class:
        filter_params['sku_class__icontains'] = sku_class

    sku_master = SKUMaster.objects.exclude(sku_class='').filter(**filter_params)
    size_dict = request_data.get('size_filter', '')
    query_string = 'sku__sku_code'
    if size_dict:
        size_dict = eval(size_dict)
        classes = get_sku_available_stock(user, sku_master, query_string, size_dict)
        sku_master = sku_master.filter(sku_class__in = classes)

    sku_master = sku_master.order_by('sequence')
    product_styles = sku_master.values_list('sku_class', flat=True).distinct()
    product_styles = list(OrderedDict.fromkeys(product_styles))
    data = []
    if is_file:
        start, stop = 0, len(product_styles)

    stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values('sku__sku_class').distinct().\
                                     annotate(in_stock=Sum('quantity'))
    reserved_quantities = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1).values('stock__sku__sku_class').distinct().\
                                       annotate(in_reserved=Sum('reserved'))
    stock_skus = map(lambda d: d['sku__sku_class'], stock_objs)
    stock_quans = map(lambda d: d['in_stock'], stock_objs)
    reserved_skus = map(lambda d: d['stock__sku__sku_class'], reserved_quantities)
    reserved_quans = map(lambda d: d['in_reserved'], reserved_quantities)
    for product in product_styles[start: stop]:
        sku_object = sku_master.filter(user=user.id, sku_class=product)
        sku_styles = sku_object.values('image_url', 'sku_class', 'sku_desc', 'sequence').\
                                       order_by('-image_url')
        total_quantity = 0
        if product in stock_skus:
            total_quantity = stock_quans[stock_skus.index(product)]
        if product in reserved_skus:
            total_quantity = total_quantity - float(reserved_quans[reserved_skus.index(product)])
        if sku_styles:
            sku_variants = list(sku_object.values(*get_values))
            sku_variants = get_style_variants(sku_variants, user, total_quantity=total_quantity)
            sku_styles[0]['variants'] = sku_variants
            sku_styles[0]['style_quantity'] = total_quantity

            #sku_styles[0]['image_url'] = resize_image(sku_styles[0]['image_url'],user)

            data.append(sku_styles[0])
        if not is_file and len(data) >= 20:
            break
    return data, start, stop

def get_user_sku_data(user):
    request = {}
    #user = User.objects.get(id=sku.user)
    _brand, _categories, _size = get_sku_categories_data(request, user, request_data={'file': True}, is_catalog='true')
    brands_data = [_brand, _categories]
    skus_data = get_sku_catalogs_data(request, user, request_data={'file': True}, is_catalog='true')
    path = 'static/text_files'
    if not os.path.exists(path):
        os.makedirs(path)
    data = json.dumps({'brands_data': brands_data, 'skus_data': skus_data})
    path = path + '/' + str(user.id) + '.sku_master.txt'
    fil = open(path, 'w').write(data)
    checksum = hashlib.sha256(data).hexdigest()
    file_dump = FileDump.objects.filter(name='sku_master', user_id=user.id)
    NOW = datetime.datetime.now
    if not file_dump:
        FileDump.objects.create(name='sku_master', user_id=user.id, checksum=checksum, path=path, creation_date=NOW, updation_date=NOW)
    else:
        file_dump = file_dump[0]
        file_dump.checksum = checksum
        file_dump.save()

@csrf_exempt
@login_required
@get_admin_user
def get_file_checksum(request,user=''):
    name = request.GET.get('name', '')
    file_content = ''
    file_data = list(FileDump.objects.filter(name=name, user=user.id).values('name', 'checksum', 'path'))
    if file_data:
        file_data = file_data[0]
    return HttpResponse(json.dumps({'file_data': file_data}))

@csrf_exempt
@login_required
@get_admin_user
def get_file_content(request,user=''):
    name = request.GET.get('name', '')
    file_content = ''
    file_data = list(FileDump.objects.filter(name=name, user=user.id).values('name', 'checksum', 'path'))
    if file_data:
        file_data = file_data[0]
        file_content = open(file_data['path'], 'r').read()
    return HttpResponse(json.dumps({'file_content': eval(file_content)}))

@get_admin_user
def search_wms_data(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    search_key = request.GET.get('q', '')
    total_data = []
    limit = 10

    if not search_key:
      return HttpResponse(json.dumps(total_data))

    lis = ['wms_code', 'sku_desc']
    query_objects = sku_master.filter(Q(wms_code__icontains = search_key) | Q(sku_desc__icontains = search_key),user=user.id)

    master_data = query_objects.filter(Q(wms_code__exact = search_key) | Q(sku_desc__exact = search_key),user=user.id)
    if master_data:
        master_data = master_data[0]
        total_data.append({'wms_code': master_data.wms_code, 'sku_desc': master_data.sku_desc})

    master_data = query_objects.filter(Q(wms_code__istartswith = search_key) | Q(sku_desc__istartswith = search_key),user=user.id)
    total_data = build_search_data(total_data, master_data, limit)

    if len(total_data) < limit:
        total_data = build_search_data(total_data, query_objects, limit)
    return HttpResponse(json.dumps(total_data))


@csrf_exempt
@login_required
@get_admin_user
def get_customer_sku_prices(request, user = ""):
    cust_id = request.POST.get('cust_id', '')
    sku_codes = request.POST.get('sku_codes', '')

    sku_codes = sku_codes.split(",")
    result_data = []
    price_type = ""
    if cust_id:
        price_type = CustomerMaster.objects.filter(customer_id = cust_id, user = user.id)

    for sku_code in sku_codes:
        if not sku_code:
            continue
        data = SKUMaster.objects.filter(sku_code = sku_code, user = user.id)
        if data:
            data = data[0]
        else:
            return "sku_doesn't exist"
        price = data.price
        discount = 0

        if price_type:
            price_type = price_type[0].price_type
            price_master_objs = PriceMaster.objects.filter(price_type = price_type, sku__sku_code = sku_code, sku__user = user.id)
            if price_master_objs:
                price = price_master_objs[0].price
                discount = price_master_objs[0].discount
        result_data.append({'wms_code': data.wms_code, 'sku_desc': data.sku_desc, 'price': price, 'discount': discount})

    return HttpResponse(json.dumps(result_data))


def build_search_data(to_data, from_data, limit):
    if(len(to_data) >= limit):
        return to_data
    else:
        for data in from_data:
            if(len(to_data) >= limit):
                break;
            else:
                status = True
                for item in to_data:
                    if(item['wms_code'] == data.wms_code):
                        status = False
                        break;
                if status:
                    to_data.append({'wms_code': data.wms_code, 'sku_desc': data.sku_desc})
        return to_data

def insert_update_brands(user):
    request = {}
    #user = User.objects.get(id=sku.user)
    sku_master = list(SKUMaster.objects.filter(user=user.id).exclude(sku_brand='').values_list('sku_brand', flat=True).distinct())
    if not 'All' in sku_master:
        sku_master.append('All')
    for brand in sku_master:
        brand_instance = Brands.objects.filter(brand_name=brand, user_id=user.id)
        if not brand_instance:
            Brands.objects.create(brand_name=brand, user_id=user.id)
    deleted_brands = Brands.objects.filter(user_id=user.id).exclude(brand_name__in=sku_master).delete()

@csrf_exempt
@login_required
@get_admin_user
def get_group_data(request, user=''):
    data_id = request.GET.get('data_id', '')
    if not data_id:
        return HttpResponse("Data id not found")
    data_dict = {}
    permission_dict = copy.deepcopy(PERMISSION_DICT)
    reversed_perms = {}
    for key, value in permission_dict.iteritems():
        sub_perms = permission_dict[key]
        if len(sub_perms) == 2:
            reversed_perms[sub_perms[1]] = sub_perms[0]
        else:
            for i in sub_perms:
                reversed_perms[i[1]] = i[0]
    #reversed_perms = OrderedDict(( ([(value, key) for key, value in permission_dict.iteritems()]) ))
    group = Group.objects.get(id=data_id)
    group_name = (group.name).replace(user.username + ' ', '')
    brands = list(GroupBrand.objects.filter(group_id=group.id).values_list('brand_list__brand_name', flat=True))
    stages = list(GroupStages.objects.filter(group_id=group.id).values_list('stages_list__stage_name',flat=True))
    permissions = group.permissions.values_list('codename', flat=True)
    perms = []
    for perm in permissions:
        temp = perm.split('_')[-1]
        if temp in reversed_perms.keys() and (reversed_perms[temp] not in perms):
            perms.append(reversed_perms[temp])
    return HttpResponse(json.dumps({'group_name': group_name, 'data': {'brands': brands, 'stages': stages, 'permissions': perms}}))

def get_sku_master(user,sub_user):
    sku_master = SKUMaster.objects.filter(user=user.id)
    sku_master_ids = sku_master.values_list('id',flat=True)

    if not sub_user.is_staff:
        sub_user_groups = sub_user.groups.filter().exclude(name=user.username).values_list('name', flat=True)
        brands_list = GroupBrand.objects.filter(group__name__in=sub_user_groups).values_list('brand_list__brand_name', flat=True)
        if not 'All' in brands_list:
            sku_master = sku_master.filter(sku_brand__in=brands_list)
        sku_master_ids = sku_master.values_list('id',flat=True)

    return sku_master, sku_master_ids

def create_update_user(data, password, username):
    """
    Creating a new Customer User
    """
    full_name = data.name
    password = password
    email = data.email_id
    if username and password:
        user = User.objects.filter(username=username)
        if user:
            status = "User already exists"
        else:
            user = User.objects.create_user(username=username, email=email, password=password, first_name=full_name)
            user.save()
            hash_code = hashlib.md5(b'%s:%s' % (user.id, email)).hexdigest()
            if user:
                prefix = re.sub('[^A-Za-z0-9]+', '', user.username)[:3].upper()
                user_profile = UserProfile.objects.create(phone_number=data.phone_number, user_id=user.id, api_hash=hash_code,
                                                          prefix=prefix, user_type='customer')
                user_profile.save()
                CustomerUserMapping.objects.create(customer_id=data.id, user_id=user.id, creation_date=datetime.datetime.now())
            status = 'User Added Successfully'

    return status

@csrf_exempt
@login_required
@get_admin_user
def pull_orders_now(request, user=''):
    from rest_api.views.easyops_api import *
    integrations = Integrations.objects.filter(user=user.id)
    for integrate in integrations:
        obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
        obj.get_pending_orders(user=user)
    return HttpResponse("Success")

@csrf_exempt
def get_order_sync_issues(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user, filters={}):
    lis = ['order_id', 'sku_code', 'reason', 'creation_date']
    order_data = lis[col_num]
    filter_params = get_filtered_params(filters, lis)

    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        master_data = OrdersTrack.objects.filter( Q(order_id__icontains = search_term) | Q(sku_code__icontains = search_term) |
                                                  Q(reason__icontains = search_term), status = 1 , **filter_params ).order_by(order_data)

    else:
        master_data = OrdersTrack.objects.filter(user = user.id, status = 1, **filter_params).order_by(order_data)

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = master_data.count()

    for result in master_data[start_index : stop_index]:
        temp_data['aaData'].append(OrderedDict(( ('Order ID', result.order_id), ('SKU Code', result.sku_code),
                                                 ('Reason', result.reason), ('Created Date', get_local_date(user, result.creation_date)),
                                                 ('DT_RowClass', 'results'), ('DT_RowId', result.id) )))

@csrf_exempt
@login_required
@get_admin_user
def delete_order_sync_data(request, user = ""):
    """ The code to delete the order_sync_data """
    order_sync_id = request.POST.get('sync_id', "")
    if order_sync_id:
        sync_entry = OrdersTrack.objects.filter(id = order_sync_id, user = user.id)
        if sync_entry:
            sync_entry = sync_entry[0]
            sync_entry.status = 2
            sync_entry.save()

    return HttpResponse(json.dumps({"resp": True, "resp_message": "Issue is deleted"}))


@csrf_exempt
@login_required
@get_admin_user
def order_sync_data_detail(request, user = ""):
    """ The code to show the detail of order_sync_data """

    order_sync_id = request.GET.get('sync_id', "")
    if order_sync_id:
        sync_entry = OrdersTrack.objects.filter(id = order_sync_id, user = user.id)
        if sync_entry:
            sync_entry = sync_entry[0]
            shipment_date = ''
            if sync_entry.shipment_date:
                shipment_date = get_local_date(user, sync_entry.shipment_date)
            data = {'sku_code' : sync_entry.sku_code, 'order_id' : sync_entry.order_id, 'reason' : sync_entry.reason,
                    'channel_sku': sync_entry.channel_sku,
                    'marketplace' : sync_entry.marketplace, 'quantity': sync_entry.quantity,
                    'title' : sync_entry.title, 'shipment_date' : shipment_date}
    return HttpResponse(json.dumps(data))


@csrf_exempt
@login_required
@get_admin_user
def confirm_order_sync_data(request, user = ""):
    """This code confirms the order sync data, once proper sku_id is entered """
    order_sync_id = request.POST.get('sync_id', "")
    new_sku_code = request.POST.get('sku_code', "")

    if order_sync_id:
        sync_entry = OrdersTrack.objects.filter(id = order_sync_id, user = user.id)
        if sync_entry:
            sync_entry = sync_entry[0]
            sku_obj = SKUMaster.objects.filter(sku_code = new_sku_code, user = user.id)

            if not sku_obj:
                return HttpResponse(json.dumps({"resp": False, "resp_message": "wrong sku code"}))
            else:
                sku_obj = sku_obj[0]
            ord_id = "".join(re.findall("\d+", sync_entry.order_id))
            ord_code = "".join(re.findall("\D+", sync_entry.order_id))

            ord_obj = OrderDetail.objects.filter(Q(order_id = ord_id, order_code = ord_code)|Q(original_order_id = sync_entry.order_id), sku = sku_obj, user = user.id)

            if ord_obj:
                return HttpResponse(json.dumps({"resp": False, "resp_message": "Order already exist"}))

            shipment_date = datetime.datetime.now()
            if sync_entry.shipment_date:
                shipment_date = sync_entry.shipment_date
            ord_obj = OrderDetail.objects.create(user = user.id, order_id = ord_id, order_code = ord_code, status = 1,
                                shipment_date = shipment_date, title = sync_entry.title, quantity = sync_entry.quantity,
                                original_order_id = sync_entry.order_id,
                                marketplace = sync_entry.marketplace, sku = sku_obj)

            CustomerOrderSummary.objects.create(order = ord_obj)

            sync_entry.mapped_sku_code = new_sku_code
            sync_entry.status = 0
            sync_entry.save()

        else:
            return HttpResponse(json.dumps({"resp": False, "resp_message": "wrong id"}))

    else:
        return HttpResponse(json.dumps({"resp": False, "resp_message": "id not present"}))
    return HttpResponse(json.dumps({"resp": True, "resp_message": "Success"}))


def check_and_return_mapping_id(sku_code, title, user):
    sku_id = ''
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
    return sku_id


@csrf_exempt
@login_required
@get_admin_user
def update_sync_issues(request, user=''):
    return HttpResponse("Success")

def xcode(text, encoding='utf8', mode='strict'):
    return text.encode(encoding, mode) if isinstance(text, unicode) else text

@csrf_exempt
@login_required
@get_admin_user
def order_management_check(request, user=''):
    order_manage = get_misc_value('order_manage', user.id)
    return HttpResponse(order_manage)
