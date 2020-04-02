import xlsxwriter
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.http import HttpResponse
import json
from django.contrib.auth import authenticate, login, logout as wms_logout
from miebach_admin.custom_decorators import login_required, get_admin_user, check_process_status
from django.utils.encoding import smart_str
from django.contrib.auth.models import User
from miebach_admin.models import *
from miebach_utils import *
import pytz
from send_message import send_sms
from operator import itemgetter
from django.contrib.auth.models import User, Permission
from xlwt import Workbook, easyxf
from xlrd import open_workbook, xldate_as_tuple
import operator
from django.db.models import Q, F, Value, FloatField, BooleanField, CharField
from django.conf import settings
from sync_sku import *
import csv
import hashlib
import os
import time
from generate_reports import *
from num2words import num2words
import datetime
from utils import *
from django.core.files.base import ContentFile
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum, Count, Max, Min
from requests import post
import math
from django.db.models.functions import Cast, Concat
from django.db.models.fields import DateField, CharField
import re
import subprocess
import importlib
import requests
from generate_reports import *

from django.template import loader, Context
from barcodes import *
import ConfigParser
from miebach.settings import INTEGRATIONS_CFG_FILE

LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read(INTEGRATIONS_CFG_FILE)

log = init_logger('logs/common.log')
init_log = init_logger('logs/integrations.log')
log_qssi = init_logger('logs/qssi_order_status_update.log')
log_sellable = init_logger('logs/auto_sellable_suggestions.log')

# Create your views here.

def create_log_message(log_obj, request_user, user, message, request_data):
    log_obj.info('Request params for %s for request user %s user %s is %s' %
                 (str(message), str(request_user.username), str(user.username), str(request_data)))

def process_date(value):
    value = value.split('/')
    value = datetime.date(int(value[2]), int(value[0]), int(value[1]))
    return value


def get_company_logo(user, IMAGE_PATH_DICT):
    import base64
    try:
        logo_name = IMAGE_PATH_DICT.get(user.username, '')
        logo_path = 'static/company_logos/' + logo_name
        image = logo_path
        with open(logo_path, "rb") as image_file:
            image = base64.b64encode(image_file.read())
    except:
        image = ""
    return image


def get_decimal_value(user_id ,price = ''):
    decimal_limit = 0
    if get_misc_value('float_switch', user_id) == 'true':
        decimal_limit = 1
        if get_misc_value('float_switch', user_id, number=True):
            if price :
                decimal_limit = get_misc_value('decimal_limit_price', user_id, number=True)
            else:
                decimal_limit = get_misc_value('decimal_limit', user_id, number=True)
            if not decimal_limit :
                decimal_limit = 2

    return decimal_limit


def get_decimal_limit(user_id, value,price =''):
    decimal_limit = get_decimal_value(user_id,price)
    return truncate_float(value, decimal_limit)


def truncate_float(value, decimal_limit):
    return float(("%." + str(decimal_limit) + "f") % (value))


def number_in_words(value):
    value = (num2words(int(round(value)), lang='en_IN').replace(',', '').replace('-', ' ')).capitalize()
    return value

def get_order_prefix(userId):
    order_prefix = 'MN'
    data = get_misc_value('order_prefix', userId)
    if data != 'false' and data:
        order_prefix = data
    return order_prefix

def service_worker_check(request):
    current_sw = request.GET.get('current_version')
    sw_version = settings.SERVICE_WORKER_VERSION
    request_user = ''
    if request.user.is_authenticated():
        request_user = request.user.username
    log.info("Current SW Version %s and System SW Version %s for request user name %s" %
             (current_sw, sw_version, request_user))
    if current_sw != sw_version:
        return HttpResponse(json.dumps({'reload': True}))
    else:
        return HttpResponse(json.dumps({'reload': False}))


@fn_timer
def get_user_permissions(request, user):
    roles = {}
    label_perms = []
    configuration = list(MiscDetail.objects.filter(user=user.id).values('misc_type', 'misc_value'))
    if 'order_headers' not in map(lambda d: d['misc_type'], configuration):
        configuration.append({'misc_type': 'order_headers', 'misc_value': ''})
    config = dict(zip(map(operator.itemgetter('misc_type'), configuration),
                      map(operator.itemgetter('misc_value'), configuration)))

    permissions = Permission.objects.values('codename')
    user_perms = []
    ignore_list = PERMISSION_IGNORE_LIST
    all_groups = request.user.groups.all()
    group_ids = all_groups.values_list('id', flat=True)
    user_perms_list = list(Permission.objects.filter(group__id__in=group_ids).\
                                        values_list('codename', flat=True).distinct())
    for permission in permissions:
        temp = permission['codename']
        if not temp in user_perms and not temp in ignore_list:
            user_perms.append(temp)
            roles[temp] = get_permission(request.user, temp, groups=all_groups,
                                         user_perms_list=user_perms_list)
            if roles[temp]:
                label_perms.append(temp)

    roles.update(config)
    return {'permissions': roles, 'label_perms': label_perms}


@login_required
@csrf_exempt
@get_admin_user
def get_corporate_master_id(request, user=''):
    corporate_id = 1
    corporate_master = CorporateMaster.objects.filter(user=user.id).values_list('corporate_id', flat=True).order_by(
        '-corporate_id')
    if corporate_master:
        corporate_id = corporate_master[0] + 1

    return HttpResponse(json.dumps({'corporate_id': corporate_id, 'tax_data': TAX_VALUES}))


def get_label_permissions(request, user, role_perms, user_type):
    label_keys = copy.deepcopy(LABEL_KEYS)
    sub_label_keys = copy.deepcopy(PERMISSION_DICT)
    labels = {}
    for label in label_keys:
        # if request.user.is_staff:
        #     labels[label] = True
        # else:
        if set(map(lambda d: d[1], sub_label_keys[label])).intersection(role_perms):
            labels[label] = True
        else:
            labels[label] = False

    extra_labels = ['DASHBOARD']
    for label in extra_labels:
        labels[label] = True if user_type != 'supplier' else False
    return labels


@get_admin_user
def add_user_permissions(request, response_data, user=''):
    status_dict = {1: 'true', 0: 'false'}
    multi_warehouse = 'false'
    user_profile = UserProfile.objects.get(user_id=user.id)
    cust_obj = CustomerUserMapping.objects.filter(user_id=request.user.id)
    tax_type = cust_obj.values_list('customer__tax_type', flat=True)
    if tax_type:
        tax_type = tax_type[0]
    else:
        tax_type = ''
    user_role = cust_obj.values_list('customer__role', flat=True)
    if user_role:
        user_role = user_role[0]
    else:
        user_role = ''
    request_user_profile = UserProfile.objects.get(user_id=request.user.id)
    show_pull_now = False
    integrations = Integrations.objects.filter(user=user.id, status=1)
    if integrations:
        show_pull_now = True
    # warehouses = UserGroups.objects.filter(Q(user__username=user.username) | Q(admin_user__username=user.username))
    # if warehouses:
    #    multi_warehouse = 'true'
    #notification count
    notification_count = PushNotifications.objects\
                                   .filter(user_id=request.user.id, is_read=False)\
                                   .count()
    if user_profile.multi_warehouse:
        multi_warehouse = 'true'
    parent_data = {}
    parent_data['userId'] = user.id
    parent_data['userName'] = user.username
    admin_user = get_admin(user)
    parent_data['parent_username'] = admin_user.get_username().lower()
    parent_data['logo'] = COMPANY_LOGO_PATHS.get(user.username, '')
    response_data['data']['userName'] = request.user.username
    response_data['data']['userId'] = request.user.id
    response_data['data']['notification_count'] = notification_count
    response_data['data']['parent'] = parent_data
    response_data['data']['roles'] = get_user_permissions(request, user)
    response_data['data']['roles']['tax_type'] = tax_type
    response_data['data']['roles']['user_role'] = user_role
    response_data['data']['roles']['labels'] = get_label_permissions(request, user,
                                                                     response_data['data']['roles']['label_perms'],
                                                                     request_user_profile.user_type)
    response_data['data']['roles']['permissions']['is_superuser'] = status_dict[int(request.user.is_superuser)]
    response_data['data']['roles']['permissions']['is_staff'] = status_dict[int(request.user.is_staff)]
    response_data['data']['roles']['permissions']['multi_warehouse'] = multi_warehouse
    response_data['data']['roles']['permissions']['show_pull_now'] = show_pull_now
    response_data['data']['roles']['permissions']['order_manage'] = get_misc_value('order_manage', user.id)
    response_data['data']['roles']['permissions']['customer_portal_prefered_view'] = get_misc_value('customer_portal_prefered_view', request.user.id)
    if response_data['data']['roles']['permissions']['customer_portal_prefered_view'] == 'false':
        response_data['data']['roles']['permissions']['customer_portal_prefered_view'] = ''
    response_data['data']['roles']['permissions']['weight_integration_name'] = get_misc_value('weight_integration_name', request.user.id)
    if response_data['data']['roles']['permissions']['weight_integration_name'] == 'false':
        response_data['data']['roles']['permissions']['weight_integration_name'] = ''
    response_data['data']['user_profile'] = {'first_name': request.user.first_name, 'last_name': request.user.last_name,
                                             'registered_date': get_local_date(request.user,
                                                                               user_profile.creation_date),
                                             'email': request.user.email,
                                             'state': user_profile.state,
                                             'trail_user': status_dict[int(user_profile.is_trail)],
                                             'company_name': user_profile.company_name,
                                             'industry_type': user_profile.industry_type,
                                             'user_type': user_profile.user_type,
                                             'request_user_type': request_user_profile.user_type,
                                             'warehouse_type': user_profile.warehouse_type,
                                             'warehouse_level': user_profile.warehouse_level,
                                             'multi_level_system': user_profile.multi_level_system}

    setup_status = 'false'
    if 'completed' not in user_profile.setup_status:
        setup_status = 'true'
    response_data['data']['roles']['permissions']['setup_status'] = setup_status

    scan_picklist_option = MiscDetail.objects.filter(misc_type='scan_picklist_option', user=user.id)
    _pick_option = "scan_sku_location"
    if scan_picklist_option:
        _pick_option = scan_picklist_option[0].misc_value

    response_data['data']['roles']['permissions']['scan_picklist_option'] = _pick_option

    if user_profile.is_trail:
        time_now = datetime.datetime.now().replace(tzinfo=pytz.timezone('UTC'))
        exp_time = get_local_date(request.user, time_now, send_date=1) - get_local_date(request.user,
                                                                                        user_profile.creation_date,
                                                                                        send_date=1)
        response_data['data']['user_profile']['expiry_days'] = 30 - int(exp_time.days)
    user_type = 'default'
    if get_priceband_admin_user(user):
        if request_user_profile.warehouse_type == 'DIST':
            warehouse_data = WarehouseCustomerMapping.objects.filter(warehouse=request.user.id, status=1)
            if not warehouse_data:  # For Distributor Sub User
                warehouse_data = WarehouseCustomerMapping.objects.filter(warehouse=user.id, status=1)
            if warehouse_data and warehouse_data[0].customer.is_distributor:
                user_type = 'distributor'  # distributor warehouse login
        elif request_user_profile.warehouse_type == 'WH':
            user_type = 'warehouse'
        elif request_user_profile.user_type == 'customer':
            customer_data = CustomerUserMapping.objects.filter(user=request.user.id)
            if customer_data and not customer_data[0].customer.is_distributor:
                user_type = 'reseller'  # reseller customer login
            else:
                user_type = 'dist_customer'  # distributor customer login
    elif request_user_profile.warehouse_type == 'CENTRAL_ADMIN':
        if not request_user_profile.zone:
            user_type = 'central_admin'
        else:
            user_type = 'admin_sub_user'
    elif request_user_profile.warehouse_type == 'SM_MARKET_ADMIN':
        user_type = 'sm_market_admin'
    elif request_user_profile.warehouse_type == 'SM_PURCHASE_ADMIN':
        user_type = 'sm_purchase_admin'
    elif request_user_profile.warehouse_type == 'SM_DESIGN_ADMIN':
        user_type = 'sm_design_admin'
    elif request_user_profile.warehouse_type == 'SM_FINANCE_ADMIN':
        user_type = 'sm_finance_admin'
    else:
        user_type = request_user_profile.user_type
    response_data['data']['roles']['permissions']['user_type'] = user_type
    response_data['message'] = 'Success'
    return response_data

def add_user_type_permissions(user_profile):
    update_perm = False
    if user_profile.user_type == 'warehouse_user':
        exc_perms = ['qualitycheck', 'qcserialmapping', 'palletdetail', 'palletmapping', 'ordershipment',
                     'shipmentinfo', 'shipmenttracking', 'networkmaster', 'tandcmaster', 'enquirymaster',
                     'corporatemaster', 'corpresellermapping', 'staffmaster']
        update_perm = True
    elif user_profile.user_type == 'marketplace_user':
        exc_perms = ['productproperties', 'sizemaster', 'pricemaster', 'networkmaster', 'tandcmaster', 'enquirymaster',
                    'corporatemaster', 'corpresellermapping', 'staffmaster']
        update_perm = True
    if update_perm:
        exc_perms = exc_perms + PERMISSION_IGNORE_LIST
        perms_list = []
        for perm in exc_perms:
            perms_list.append('add_' + str(perm))
            perms_list.append('change_' + str(perm))
            perms_list.append('delete_' + str(perm))
            perms_list.append('view_' + str(perm))
        permissions = Permission.objects.exclude(codename__in=perms_list)
        for permission in permissions:
            user_profile.user.user_permissions.add(permission)


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
                up_obj = UserProfile(user=user, phone_number='',
                                           is_active=1, prefix=prefix, swx_id=0)
                up_obj.save()
                if user.is_staff:
                    add_user_type_permissions(up_obj)
                user_profile = UserProfile.objects.filter(user_id=user.id)
        else:
            return HttpResponse(json.dumps(response_data), content_type='application/json')

        response_data = add_user_permissions(request, response_data)
        price_band_flag = get_misc_value('priceband_sync', user.id)
        if response_data['data'].get('parent', '') and not user_profile[0].warehouse_type \
                and user_profile[0].user_type != 'customer' and price_band_flag:
            parent_user_profile = UserProfile.objects.get(user_id=response_data['data']['parent']['userId'])
            if parent_user_profile.warehouse_type:
                user_profile[0].warehouse_type = parent_user_profile.warehouse_type
                user_profile[0].save()

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
            user = User.objects.create_user(username=username, email=email, password=password, first_name=full_name,
                                            last_login=datetime.datetime.now())
            user.save()
            hash_code = hashlib.md5(b'%s:%s' % (user.id, email)).hexdigest()
            if user:
                prefix = re.sub('[^A-Za-z0-9]+', '', user.username)[:3].upper()
                user_profile = UserProfile.objects.create(phone_number=request.POST.get('phone', ''),
                                                          company_name=request.POST.get('company', ''), user_id=user.id,
                                                          api_hash=hash_code,
                                                          is_trail=1, prefix=prefix, setup_status='')
                user_profile.save()
                add_user_type_permissions(user_profile)
            user.is_staff = 1
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
    response = {'message': 'success', 'data': {}}
    hashcode = request.GET.get('hash_code')
    trial_data = BookTrial.objects.filter(hash_code=hashcode)
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


def get_search_params(request, user=''):
    """
    Zone Code is (NORTH, EAST, WEST, SOUTH)
    Zone Id is Warehouse Zone.
    """
    search_params = {}
    filter_params = {}
    headers = []
    date_fields = ['from_date', 'to_date','invoice_date','creation_date']
    data_mapping = {'start': 'start', 'length': 'length', 'draw': 'draw', 'search[value]': 'search_term',
                    'order[0][dir]': 'order_term',
                    'order[0][column]': 'order_index', 'from_date': 'from_date', 'to_date': 'to_date',
                    'wms_code': 'wms_code','status':'status', 'sku_brand':'sku_brand', 'manufacturer':'manufacturer',
                    'searchable':'searchable','bundle':'bundle',
                    'supplier': 'supplier', 'sku_code': 'sku_code', 'category': 'sku_category', 'sub_category': 'sub_category',
                    'sku_category': 'sku_category', 'sku_type': 'sku_type','sister_warehouse':'sister_warehouse',
                    'class': 'sku_class', 'zone_id': 'zone', 'location': 'location', 'open_po': 'open_po',
                    'marketplace': 'marketplace','central_order_id':'central_order_id',
                    'marketplace': 'marketplace','source_location':'source_location','destination_location':'destination_location',
                    'special_key': 'special_key', 'brand': 'sku_brand', 'stage': 'stage', 'jo_code': 'jo_code',
                    'sku_class': 'sku_class', 'sku_size': 'sku_size','order_reference':'order_reference',
                    'order_report_status': 'order_report_status', 'customer_id': 'customer_id',
                    'imei_number': 'imei_number','creation_date':'creation_date',
                    'order_id': 'order_id', 'job_code': 'job_code', 'job_order_code': 'job_order_code',
                    'fg_sku_code': 'fg_sku_code','warehouse_level':'warehouse_level','invoice':'invoice',
                    'rm_sku_code': 'rm_sku_code', 'pallet': 'pallet','invoice_date':'invoice_date',
                    'staff_id': 'id', 'ean': 'ean', 'invoice_number': 'invoice_number', 'dc_number': 'challan_number',
                    'zone_code': 'zone_code', 'distributor_code': 'distributor_code', 'reseller_code': 'reseller_code',
                    'supplier_id': 'supplier_id', 'rtv_number': 'rtv_number', 'corporate_name': 'corporate_name',
                    'enquiry_number': 'enquiry_number', 'enquiry_status': 'enquiry_status',
                    'aging_period': 'aging_period', 'source_sku_code': 'source_sku_code',
                    'destination_sku_code': 'destination_sku_code',
                    'destination_sku_category': 'destination_sku_category','warehouse':'warehouse',
                    'source_sku_category': 'source_sku_category', 'level': 'level', 'project_name':'project_name', 'customer':'customer'}
    int_params = ['start', 'length', 'draw', 'order[0][column]']
    filter_mapping = {'search0': 'search_0', 'search1': 'search_1',
                      'search2': 'search_2', 'search3': 'search_3',
                      'search4': 'search_4', 'search5': 'search_5',
                      'search6': 'search_6', 'search7': 'search_7',
                      'search8': 'search_8', 'search9': 'search_9',
                      'search10': 'search_10', 'search11': 'search_11'}
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
    #pos extra headers
    if user:
        headers.extend(["Billing Address" ,"Shipping Address"])
        headers.extend(["Order Taken By", "Payment Cash", "Payment Card","Payment PhonePe","Payment GooglePay","Payment Paytm"])
        extra_fields_obj = MiscDetail.objects.filter(user=user.id, misc_type__icontains="pos_extra_fields")
        for field in extra_fields_obj:
            tmp = field.misc_value.split(',')
            for i in tmp:
                headers.append(str(i))

    return headers, search_params, filter_params


data_datatable = {  # masters
    'SKUMaster': 'get_sku_results', 'SupplierMaster': 'get_supplier_results', \
    'SupplierSKUMappingMaster': 'get_supplier_mapping', 'CustomerMaster': 'get_customer_master', \
    'BOMMaster': 'get_bom_results', 'CustomerSKUMapping': 'get_customer_sku_mapping', 'SKUPackMaster' :'get_sku_pack_master',\
    'WarehouseMaster': 'get_warehouse_user_results', 'VendorMaster': 'get_vendor_master_results', \
    'DiscountMaster': 'get_discount_results', 'CustomSKUMaster': 'get_custom_sku_properties', \
    'SizeMaster': 'get_size_master_data', 'PricingMaster': 'get_price_master_results', \
    'SellerMaster': 'get_seller_master', 'SellerMarginMapping': 'get_seller_margin_mapping', \
    'TaxMaster': 'get_tax_master', 'NetworkMaster': 'get_network_master_results',\
    'StaffMaster': 'get_staff_master', 'CorporateMaster': 'get_corporate_master',\
    'WarehouseSKUMappingMaster': 'get_wh_sku_mapping', 'ClusterMaster': 'get_cluster_sku_results',
    'ReplenushmentMaster':'get_replenushment_master', 'supplierSKUAttributes': 'get_source_sku_attributes_mapping',
    'LocationMaster' :'get_zone_details','AttributePricingMaster': 'get_attribute_price_master_results',\

    # inbound
    'RaisePO': 'get_po_suggestions', 'ReceivePO': 'get_confirmed_po', \
    'QualityCheck': 'get_quality_check_data', 'POPutaway': 'get_order_data', \
    'ReturnsPutaway': 'get_order_returns_data', 'SalesReturns': 'get_order_returns', \
    'RaiseST': 'get_raised_stock_transfer', 'SellerInvoice': 'get_seller_invoice_data', \
    'RaiseIO': 'get_intransit_orders', 'PrimarySegregation': 'get_segregation_pos', \
    'ProcessedPOs': 'get_processed_po_data', 'POChallans': 'get_po_challans_data', \
    'SupplierInvoices': 'get_supplier_invoice_data', \
    'POPaymentTrackerInvBased': 'get_inv_based_po_payment_data', \
    'InboundPaymentReport': 'get_inbound_payment_report',\
    'ReturnToVendor': 'get_po_putaway_data', \
    'CreatedRTV': 'get_saved_rtvs', \
    'PastPO':'get_past_po',\
    # production
    'RaiseJobOrder': 'get_open_jo', 'RawMaterialPicklist': 'get_jo_confirmed', \
    'PickelistGenerated': 'get_generated_jo', 'ReceiveJO': 'get_confirmed_jo', \
    'PutawayConfirmation': 'get_received_jo', 'PutawayConfirmationSKU': 'get_received_jo',
    'ProductionBackOrders': 'get_rm_back_order_data', 'ProductionBackOrdersAlt': 'get_rm_back_order_data_alt',
    'RaiseRWO': 'get_saved_rworder', 'ReceiveJOSKU': "get_confirmed_jo_all", \
    'RawMaterialPicklistSKU': 'get_rm_picklist_confirmed_sku', \
    # stock locator
    'StockSummary': 'get_stock_results', 'OnlinePercentage': 'get_sku_stock_data', \
    'StockDetail': 'get_stock_detail_results', 'CycleCount': 'get_cycle_count', \
    'MoveInventory': 'get_move_inventory', 'InventoryAdjustment': 'get_move_inventory', \
    'InventoryModification' : 'get_inventory_modification', \
    'ConfirmCycleCount': 'get_cycle_confirmed', 'VendorStockTable': 'get_vendor_stock', \
    'Available': 'get_available_stock', 'Available+Intransit': 'get_availintra_stock', 'Total': 'get_avinre_stock', \
    'StockSummaryAlt': 'get_stock_summary_size', 'SellerStockTable': 'get_seller_stock_data', \
    'BatchLevelStock': 'get_batch_level_stock', 'WarehouseStockAlternative': 'get_alternative_warehouse_stock',
    'Available+ASN': 'get_availasn_stock',
    'SerialNumberSKU': 'get_stock_summary_serials_excel',
    'AutoSellableSuggestion': 'get_auto_sellable_suggestion_data',
    'SkuClassification':'get_skuclassification',
    # outbound
    'SKUView': 'get_batch_data', 'OrderView': 'get_order_results', 'OpenOrders': 'open_orders', \
    'PickedOrders': 'open_orders', 'BatchPicked': 'open_orders', \
    'ShipmentInfo': 'get_customer_results', 'ShipmentPickedOrders': 'get_shipment_picked', \
    'PullToLocate': 'get_cancelled_putaway', \
    'StockTransferOrders': 'get_stock_transfer_orders', 'OutboundBackOrders': 'get_back_order_data', \
    'CustomerOrderView': 'get_order_view_data', 'CustomerCategoryView': 'get_order_category_view_data', \
    'CustomOrders': 'get_custom_order_data', 'CentralOrders': 'get_central_orders_data',
    'ShipmentPickedAlternative': 'get_order_shipment_picked', 'CustomerInvoices': 'get_customer_invoice_data', \
    'OrderApprovals': 'get_order_approval_statuses',
    'ProcessedOrders': 'get_processed_orders_data', 'DeliveryChallans': 'get_delivery_challans_data',
    'CustomerInvoicesTab': 'get_customer_invoice_tab_data', 'SellerOrderView': 'get_seller_order_view', \
    'StockTransferInvoice' : 'get_stock_transfer_invoice_data',
    'StockTransferShipment' : 'get_stock_transfer_shipment_data',
    'PicklistDeliveryChallan':'get_picklist_delivery_challan',
    'AltStockTransferOrders': 'get_stock_transfer_order_level_data', 'RatingsTable': 'get_ratings_data',\
    'MyOrdersTbl' : 'get_customer_orders',\
    'MarketEnqTbl': 'get_enquiry_data', 'CustomOrdersTbl': 'get_manual_enquiry_data',\
    # manage users
    'ManageUsers': 'get_user_results', 'ManageGroups': 'get_user_groups',
    # retail one
    'channels_list': 'get_marketplace_data',
    # Integrations
    'OrderSyncTable': 'get_order_sync_issues',
    # Uploaded POs (Display only to Central Admin)
    'UploadedPos': 'get_uploaded_pos_by_customers',
    'EnquiryOrders': 'get_enquiry_orders',
    'ManualEnquiryOrders': 'get_manual_enquiry_orders',
    'Targets': 'get_distributor_targets',
    # feedBack Details
    'FeedbackData': 'get_feedback_data',
    #invoice based payment tracker
    'PaymentTrackerInvBased': 'get_inv_based_payment_data',
    'OutboundPaymentReport': 'get_outbound_payment_report',
    'DistributorOrdersData': 'get_distributors_orders',  # Outbound.py

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


def permissionpage(request, cond=''):
    if cond:
        return ((request.user.is_staff or request.user.is_superuser) or (
        cond in request.user.get_group_permissions()) or request.user.has_perm(cond))
    else:
        return (request.user.is_staff or request.user.is_superuser)


def get_permission(user, codename, groups=None, user_perms_list=None):
    in_group = False
    if not groups:
        groups = user.groups.all()
    if user_perms_list:
        if codename in user_perms_list:
            in_group = True
    else:
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


def get_filtered_params_search(filters, data_list):
    filter_params1 = {}
    filter_params2 = {}
    for key, value in filters.iteritems():
        col_num = int(key.split('_')[-1])
        if value:
            filter_params2[data_list[col_num] + '__icontains'] = value
            filter_params1[data_list[col_num] + '__istartswith'] = value
    return filter_params1, filter_params2


@csrf_exempt
def get_local_date(user, input_date, send_date=''):
    utc_time = input_date.replace(tzinfo=pytz.timezone('UTC'))
    user_details = UserProfile.objects.get(user_id=user.id)
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
    lis = ['username', 'first_name', 'email', 'id']
    group = ''
    admin_group = AdminGroups.objects.filter(user_id=user.id)
    if admin_group:
        group = admin_group[0].group
    if group:
        if search_term:
            master_data = group.user_set.filter(
                Q(username__icontains=search_term) | Q(first_name__icontains=search_term) |
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
        temp_data['aaData'].append({'User Name': data.username, 'DT_RowClass': 'results', 'Name': data.first_name,
                                    'Email': data.email, 'Member of Groups': member_count, 'DT_RowId': data.id})


@csrf_exempt
def get_user_groups(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user):
    lis = ['Group Name', 'Members Count']
    group = ''
    # admin_group = AdminGroups.objects.filter(user_id=user.id)
    # if admin_group:
    #    group = admin_group[0].group
    # if group:
    if search_term:
        master_data = user.groups.filter(name__icontains=search_term).exclude(name=user.username)
    # elif order_term:
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
        temp_data['aaData'].append(
            {'Group Name': group_name, 'DT_RowClass': 'results', 'Members Count': member_count, 'DT_RowId': data.id})

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
    for key, value in request.GET.iteritems():
        if not key == 're_password':
            user_dict[key] = value
    user_dict['last_login'] = datetime.datetime.now()
    user_exists = User.objects.filter(username=user_dict['username'])
    if not user_exists:
        new_user = User.objects.create_user(**user_dict)
        admin_group = AdminGroups.objects.filter(user_id=user.id)
        if admin_group:
            group = admin_group[0].group
        else:
            group, created = Group.objects.get_or_create(name=user.username)
            admin_dict = {'group_id': group.id, 'user_id': user.id}
            admin_group = AdminGroups(**admin_dict)
            admin_group.save()
            user.groups.add(group)
        new_user.groups.add(group)
        # add_extra_permissions(new_user)
        new_user.groups.add(group)
        status = 'Added Successfully'
    return HttpResponse(status)


def add_extra_permissions(user):
    add_permissions = ['Inbound', 'Outbound']
    permission_dict = {'Inbound': ['openpo', 'purchaseorder', 'polocation'],
                       'Outbound': ['orderdetail', 'picklist', 'picklistlocation'],
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
    config_dict = copy.deepcopy(CONFIG_DEF_DICT)
    config_dict['display_none'] = 'display: block;'
    for key, value in CONFIG_SWITCHES_DICT.iteritems():
        config_dict[key] = get_misc_value(value, user.id)
    for key, value in CONFIG_INPUT_DICT.iteritems():
        query_user = user
        if key == 'weight_integration_name':
            query_user = request.user
        config_dict[key] = ''
        value = get_misc_value(value, query_user.id)
        if not value == 'false':
            config_dict[key] = value
    all_groups = SKUGroups.objects.filter(user=user.id).values_list('group', flat=True)
    config_dict['all_groups'] = str(','.join(all_groups))
    if config_dict['receive_process'] == 'false':
        MiscDetail.objects.create(user=user.id, misc_type='receive_process', misc_value='2-step-receive',
                                  creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now())
        config_dict['receive_process'] = '2-step-receive'

    total_groups = request.user.groups.all()
    if not get_permission(request.user, 'add_qualitycheck', groups=total_groups):
        del config_dict['receive_options']['One step Receipt + Qc']

    config_dict['view_order_status'] = config_dict['view_order_status'].split(',')
    config_dict['style_headers'] = config_dict['style_headers'].split(',')

    if config_dict['stock_display_warehouse'] and config_dict['stock_display_warehouse'] != "false":
        config_dict['stock_display_warehouse'] = config_dict['stock_display_warehouse'].split(',')
        config_dict['stock_display_warehouse'] = map(int, config_dict['stock_display_warehouse'])
    else:
        config_dict['stock_display_warehouse'] = []

    # Invoice Marketplaces list and selected Option
    config_dict['marketplaces'] = get_marketplace_names(user, 'all_marketplaces')
    config_dict['prefix_data'] = list(InvoiceSequence.objects.filter(user=user.id, status=1).exclude(marketplace=''). \
                                      values('marketplace', 'prefix', 'interfix', 'date_type'))
    config_dict['prefix_dc_data'] = list(ChallanSequence.objects.filter(user=user.id, status=1).exclude(marketplace=''). \
                                      values('marketplace', 'prefix'))
    config_dict['prefix_cn_data'] = list(UserTypeSequence.objects.filter(user=user.id, status=1,
                                            type_name='credit_note_sequence').exclude(type_value=''). \
                                      values('prefix').annotate(marketplace=F('type_value')))
    all_stages = ProductionStages.objects.filter(user=user.id).order_by('order').values_list('stage_name', flat=True)
    config_dict['all_stages'] = str(','.join(all_stages))
    order_field_obj =  MiscDetail.objects.filter(user=user.id,misc_type='extra_order_fields')
    extra_order_fields = get_misc_value('extra_order_fields', user.id)
    if extra_order_fields == 'false' :
        config_dict['all_order_fields'] = ''
    else:
        config_dict['all_order_fields'] = extra_order_fields
    extra_order_sku_fields = get_misc_value('extra_order_sku_fields', user.id)
    if extra_order_sku_fields == 'false' :
        config_dict['all_order_sku_fields'] = ''
    else:
        config_dict['all_order_sku_fields'] = extra_order_sku_fields
    grn_fields = get_misc_value('grn_fields', user.id)
    if grn_fields == 'false' :
        config_dict['grn_fields'] = ''
    else:
        config_dict['grn_fields'] = grn_fields

    po_fields = get_misc_value('po_fields', user.id)
    if po_fields == 'false' :
        config_dict['po_fields'] = ''
    else:
        config_dict['po_fields'] = po_fields

    rtv_reasons = get_misc_value('rtv_reasons', user.id)
    if rtv_reasons == 'false' :
        config_dict['rtv_reasons'] = ''
    else:
        config_dict['rtv_reasons'] = rtv_reasons
    move_inventory_reasons = get_misc_value('move_inventory_reasons', user.id)
    if move_inventory_reasons == 'false':
        config_dict['move_inventory_reasons'] = ''
    else:
        config_dict['move_inventory_reasons'] = move_inventory_reasons

    if config_dict['mail_alerts'] == 'false':
        config_dict['mail_alerts'] = 0
    if config_dict['production_switch'] == 'false':
        config_dict['display_none'] = 'display:none;'
    config_dict['mail_inputs'] = []

    for key, val in MAIL_REPORTS_DATA.iteritems():
        temp_value = get_misc_value(val, user.id)
        if temp_value == 'true':
            config_dict['mail_inputs'].append(val)

    if config_dict['online_percentage'] == "false":
        config_dict['online_percentage'] = 0
    user_profile = UserProfile.objects.filter(user_id=user.id)
    config_dict['prefix'] = ''
    if user_profile:
        config_dict['prefix'] = user_profile[0].prefix

    enabled_reports = MiscDetail.objects.filter(misc_type__contains='report', misc_value='true', user=request.user.id)
    config_dict['reports_data'] = []
    for reports in enabled_reports:
        config_dict['reports_data'].append(str(reports.misc_type.replace('report_', '')))

    all_related_warehouse_id = get_related_users(user.id)
    config_dict['all_related_warehouse'] = dict(
        User.objects.filter(id__in=all_related_warehouse_id).exclude(id=user.id).values_list('first_name', 'id'))
    config_dict['all_related_warehouse'].update({"Intransit of Current Warehouse": user.id})

    config_dict['display_pos'] = ''
    if config_dict['pos_switch'] == 'false':
        config_dict['display_pos'] = 'display:none'

    tax_details = MiscDetail.objects.filter(misc_type__istartswith='tax_', user=request.user.id)
    config_dict['tax_data'] = []
    if tax_details:
        for tax in tax_details:
            config_dict['tax_data'].append({'tax_name': tax.misc_type[4:], 'tax_value': tax.misc_value})
    config_dict['rem_saved_mail_alerts'] = list(MailAlerts.objects.filter(user_id=user.id).\
                                                values('alert_name', 'alert_value'))
    config_dict['selected_receive_po_mandatory'] = []
    mandatory_receive_po = get_misc_value('receive_po_mandatory_fields', user.id)
    if mandatory_receive_po != 'false':
        config_dict['selected_receive_po_mandatory'] = mandatory_receive_po.split(',')
    terms_condition = UserTextFields.objects.filter(user=user.id, field_type = 'terms_conditions')
    dc_terms_conditions = UserTextFields.objects.filter(user=user.id, field_type = 'dc_terms_conditions')
    if terms_condition.exists():
        config_dict['raisepo_terms_conditions'] = terms_condition[0].text_field
    if dc_terms_conditions.exists():
        config_dict['delivery_challan_terms_condtions'] = dc_terms_conditions[0].text_field
    config_dict['all_order_field_options'] = {}
    misc_options = MiscDetailOptions.objects.filter(misc_detail__user=user.id).values('misc_key','misc_value')
    for misc in misc_options :
        misc_list = misc.get('misc_value').split(',')
        config_dict['all_order_field_options'][misc.get('misc_key')]=[]
        for misc_value in misc_list :
            temp_dict = {}
            temp_dict['field_name'] = misc_value
            config_dict['all_order_field_options'][misc.get('misc_key')].append(temp_dict)

    return HttpResponse(json.dumps(config_dict))


@csrf_exempt
def get_work_sheet(sheet_name, sheet_headers, f_name='', headers_index=0):
    if '.xlsx' in f_name:
        wb = xlsxwriter.Workbook(f_name)
        ws = wb.add_worksheet(sheet_name)
        header_style = wb.add_format({'bold': True})
    else:
        wb = Workbook()
        ws = wb.add_sheet(sheet_name)
        header_style = easyxf('font: bold on')
    for count, header in enumerate(sheet_headers):
        ws.write(headers_index, count, header, header_style)
    return wb, ws


def get_extra_data(excel_headers, result_data, user):
    data = []
    if 'Product SKU Code' in excel_headers and 'Product Description' in excel_headers:
        excel_headers = ['Product SKU Code', 'Product SKU Description', 'Material SKU Code', 'Material SKU Description',
                         'Material Quantity', 'Wastage Percentage',
                         'Unit of Measurement']
        for i in result_data:
            data_id = i['DT_RowAttr']['data-id']
            bom_data = BOMMaster.objects.filter(product_sku__sku_code=data_id, product_sku__user=user.id)
            for bom in bom_data:
                data.append(OrderedDict((('Product SKU Code', bom.product_sku.sku_code),
                                         ('Product SKU Description', bom.product_sku.sku_desc),
                                         ('Material SKU Code', bom.material_sku.wms_code),
                                         ('Material SKU Description', bom.material_sku.sku_desc),
                                         ('Material Quantity', bom.material_quantity),
                                         ('Wastage Percentage', bom.wastage_percent),
                                         ('Unit of Measurement', bom.unit_of_measurement))))
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
def print_excel(request, temp_data, headers, excel_name='', user='', file_type='', tally_report=0):
    excel_headers = ''
    if temp_data['aaData']:
        excel_headers = temp_data['aaData'][0].keys()
    if '' in headers:
        headers = filter(lambda a: a != '', headers)
    if not excel_headers:
        excel_headers = headers
    for i in set(excel_headers) - set(headers):
        excel_headers.remove(i)
    if tally_report ==1:
        excel_headers = headers
    excel_headers, temp_data['aaData'] = get_extra_data(excel_headers, temp_data['aaData'], user)
    if not excel_name:
        excel_name = request.POST.get('serialize_data', '')
    if excel_name:
        file_name = "%s.%s" % (user.username, excel_name.split('=')[-1])
    if not file_type:
        file_type = 'xls'
    if len(temp_data['aaData']) > 65535:
        file_type = 'csv'
    path = ('static/excel_files/%s.%s') % (file_name, file_type)
    if not os.path.exists('static/excel_files/'):
        os.makedirs('static/excel_files/')
    path_to_file = '../' + path
    if file_type == 'csv':
        with open(path, 'w') as mycsvfile:
            thedatawriter = csv.writer(mycsvfile, delimiter=',')
            counter = 0
            try:
                thedatawriter.writerow(itemgetter(*excel_headers)(headers))
            except:
                thedatawriter.writerow(excel_headers)
            for data in temp_data['aaData']:
                temp_csv_list = []
                for key, value in data.iteritems():
                    if key in excel_headers:
                        temp_csv_list.append(str(xcode(value)))
                thedatawriter.writerow(temp_csv_list)
                counter += 1
    else:
        try:
            wb, ws = get_work_sheet('skus', itemgetter(*excel_headers)(headers))
        except:
            wb, ws = get_work_sheet('skus', excel_headers)
        data_count = 0
        data = temp_data['aaData']
        for i in range(0, len(data)):
            index = i + 1
            for ind, header_name in enumerate(excel_headers):
                ws.write(index, excel_headers.index(header_name), data[i].get(header_name, ''))

        # for data in temp_data['aaData']:
        #     data_count += 1
        #     column_count = 0
        #     for key, value in data.iteritems():
        #         if key in excel_headers:
        #             ws.write(data_count, column_count, value)
        #             column_count += 1
        wb.save(path)
    return HttpResponse(path_to_file)


def po_message(po_data, phone_no, user_name, f_name, order_date, ean_flag, table_headers=None):
    data = '%s Orders for %s dated %s' % (user_name, f_name, order_date)
    total_quantity = 0
    total_amount = 0
    if ean_flag:
        for po in po_data:
            data += '\nD.NO: %s, Qty: %s' % (po[2], po[5])
            if table_headers:
                total_quantity += int(po[table_headers.index('Qty')])
                total_amount += float(po[table_headers.index('Amt')])
            else:
                total_quantity += int(po[5])
                total_amount += float(po[7])
    else:
        for po in po_data:
            data += '\nD.NO: %s, Qty: %s' % (po[1], po[4])
            if table_headers:
                total_quantity += int(po[table_headers.index('Qty')])
                total_amount += float(po[table_headers.index('Amt')])
            else:
                total_quantity += int(po[4])
                total_amount += float(po[6])
    data += '\nTotal Qty: %s, Total Amount: %s\nPlease check WhatsApp for Images' % (total_quantity, total_amount)
    send_sms(phone_no, data)


def grn_message(po_data, phone_no, user_name, f_name, order_date):
    data = 'Dear Supplier,\n%s received the goods against PO NO. %s on dated %s' % (user_name, f_name, order_date)
    total_quantity = 0
    total_amount = 0
    for po in po_data:
        data += '\nD.NO: %s, Qty: %s' % (po[0], po[5])
        total_quantity += int(po[5])
        total_amount += int(po[6])
    data += '\nTotal Qty: %s, Total Amount: %s' % (total_quantity, total_amount)
    send_sms(phone_no, data)


def jo_message(po_data, phone_no, user_name, f_name, order_date):
    # data = 'Dear Vendor,\n%s received the goods against JO NO. %s on dated %s' %(user_name, f_name, order_date)
    data = 'Dear Vendor, Please find the Job Order details for Job Code %s on dated %s from %s' % (
    f_name, order_date, user_name)
    total_quantity = 0
    for po in po_data.get('material_data', []):
        data += '\nSKU: %s, Qty: %s' % (po['SKU Code'], po['Quantity'])
        total_quantity += int(po['Quantity'])
    data += '\nTotal Qty: %s' % (total_quantity)
    send_sms(phone_no, data)


def order_creation_message(items, telephone, order_id, other_charges=0):
    data = 'Your order with ID %s has been successfully placed for ' % order_id
    total_quantity = 0
    total_amount = 0
    items_data = []
    for item in items:
        sku_desc = (item[0][:30] + '..') if len(item[0]) > 30 else item[0]
        items_data.append('%s with Qty: %s' % (sku_desc, int(item[1])))
        total_quantity += int(item[1])
        total_amount += float(("%.2f") % (item[2]))
    if other_charges:
        total_amount += other_charges
    data += ', \n '.join(items_data)
    data += '\n\nTotal Qty: %s, Total Amount: %s' % (total_quantity, total_amount)
    send_sms(telephone, data)


def order_dispatch_message(order, user, order_qt=""):
    data = 'Your order with ID %s has been successfully picked and ready for dispatch by %s %s :' % (
    (order.order_code + str(order.order_id)), user.first_name, user.last_name)
    total_quantity = 0
    total_amount = 0
    telephone = order.telephone
    items_data = []
    items = OrderDetail.objects.filter(order_id=order.order_id, order_code=order.order_code, user=user.id)
    for item in items:
        # sku_desc = (item.title[:30] + '..') if len(item.title) > 30 else item.title
        qty = int(order_qt.get(item.sku.sku_code, 0))
        if not qty:
            continue
        items_data.append('\n %s  Qty: %s' % (item.sku.sku_code, qty))
        total_quantity += qty
        total_amount += int((item.invoice_amount / item.quantity) * qty)
    data += ', '.join(items_data)
    data += '\n\nTotal Qty: %s, Total Amount: %s' % (total_quantity, total_amount)
    log.info(data)
    send_sms(telephone, data)


@get_admin_user
def enable_mail_reports(request, user=''):
    data = request.GET.get('data').split(',')
    data_enabled = []
    data_disabled = []
    for d in data:
        if d:
            data_enabled.append(MAIL_REPORTS_DATA[d])

    data_disabled = set(MAIL_REPORTS_DATA.values()) - set(data_enabled)
    for d in data_disabled:
        misc_detail = MiscDetail.objects.filter(user=user.id, misc_type=d)
        if misc_detail:
            misc_detail[0].misc_value = 'false'
            misc_detail[0].save()
            continue
        data_obj = MiscDetail(user=user.id, misc_type=d, misc_value='false')

    for d in data_enabled:
        misc_detail = MiscDetail.objects.filter(user=user.id, misc_type=d)
        if misc_detail:
            misc_detail[0].misc_value = 'true'
            misc_detail[0].save()
            continue
        data_obj = MiscDetail(user=user.id, misc_type=d, misc_value='true')
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
            date_val = time.strftime('%Y-%d-%M', date_val)
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
            misc_detail[0].misc_value = data_range
            misc_detail[0].save()
        else:
            misc_detail = MiscDetail(user=user.id, misc_type='report_data_range', misc_value=data_range)
            misc_detail.save()

    existing_emails = MiscDetail.objects.filter(misc_type='email', user=user.id).values_list('misc_value', flat=True)

    add_misc_email(user, email)

    return HttpResponse('Success')


@csrf_exempt
@get_admin_user
def get_internal_mails(request, user=""):
    """ saving internal mails from config page """
    internal_emails = request.GET.get('internal_mails', '')

    MiscDetail.objects.update_or_create(user=user.id, misc_type='Internal Emails',
                                        defaults={'misc_value': internal_emails})

    return HttpResponse('Success')


@get_admin_user
def send_mail_reports(request, user=''):
    from generate_reports import *
    mail_report_obj = MailReports()
    email = request.GET.get('mails', '')
    if email:
        add_misc_email(user, email)
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='email')
    if misc_detail and misc_detail[0].misc_value:
        mail_report_obj.send_reports_mail(user, mail_now=True)
        return HttpResponse('Success')
    return HttpResponse('Email ids not found')


@csrf_exempt
def set_timezone(request):
    timezone = request.GET['tz']
    user_details = UserProfile.objects.filter(user_id=request.user.id)
    for user in user_details:
        if not user.timezone:
            user.timezone = timezone
            user.save()
    return HttpResponse("Success")


def get_auto_po_quantity(sku, stock_quantity=''):
    if not stock_quantity:
        sku_stock = StockDetail.objects.exclude(location__zone__zone='DAMAGED_ZONE').filter(sku_id=sku.id,
                                                                                            sku__user=sku.user,
                                                                                            quantity__gt=0). \
            aggregate(Sum('quantity'))['quantity__sum']
        stock_quantity = 0
        if sku_stock:
            stock_quantity = sku_stock

    open_po_qty = OpenPO.objects.filter(sku_id=sku.id, sku__user=sku.user,
                                             status__in=['Automated', 1, 'Manual']).only('order_quantity').\
        aggregate(Sum('order_quantity'))['order_quantity__sum']

    purchase_order = PurchaseOrder.objects.exclude(status__in=['confirmed-putaway', 'location-assigned']). \
        filter(open_po__sku__user=sku.user, open_po__sku_id=sku.id, open_po__vendor_id__isnull=True). \
        values('open_po__sku_id').annotate(total_order=Sum('open_po__order_quantity'),
                                           total_received=Sum('received_quantity'))

    qc_pending = POLocation.objects.filter(purchase_order__open_po__sku__user=sku.user, purchase_order__open_po__sku_id=sku.id,
                                            qualitycheck__status='qc_pending', status=2).\
                                    only('quantity').aggregate(Sum('quantity'))['quantity__sum']
    putaway_pending = POLocation.objects.filter(purchase_order__open_po__sku__user=sku.user, purchase_order__open_po__sku_id=sku.id,
                                                status=1).only('quantity').aggregate(Sum('quantity'))['quantity__sum']
    if not qc_pending:
        qc_pending = 0
    if not putaway_pending:
        putaway_pending = 0
    if not open_po_qty:
        open_po_qty = 0

    production_orders = JobOrder.objects.filter(product_code_id=sku.id, product_code__user=sku.user). \
        exclude(status__in=['open', 'confirmed-putaway']).values('product_code_id'). \
        annotate(total_order=Sum('product_quantity'), total_received=Sum('received_quantity'))
    production_quantity = 0
    if production_orders:
        production_order = production_orders[0]
        diff_quantity = float(production_order['total_order']) - float(production_order['total_received'])
        if diff_quantity > 0:
            production_quantity = diff_quantity

    intransit_orders = IntransitOrders.objects.filter(sku=sku, user=sku.user, status=1).\
        values('sku__sku_code').annotate(tot_qty=Sum('quantity'), tot_inv_amt=Sum('invoice_amount'))
    intr_qty = 0
    if intransit_orders:
        intr_order = intransit_orders[0]
        intr_qty = intr_order['tot_qty']
    transit_quantity = 0
    if purchase_order:
        purchase_order = purchase_order[0]
        diff_quantity = float(purchase_order['total_order']) - float(purchase_order['total_received'])
        if diff_quantity > 0:
            transit_quantity = diff_quantity
        transit_quantity += (qc_pending + putaway_pending)

    total_quantity = (stock_quantity + transit_quantity + production_quantity + intr_qty + open_po_qty)
    raise_quantity = int(sku.threshold_quantity) - total_quantity
    if raise_quantity < 0:
        raise_quantity = 0
    
    max_norm_qty = int(sku.max_norm_quantity)
    return int(raise_quantity), int(total_quantity), max_norm_qty


def auto_po_warehouses(sku, qty):
    supplier_id = ''
    price = 0
    taxes = {}
    order_code = get_order_prefix(sku.user.id)
    wh_customer_map = WarehouseCustomerMapping.objects.filter(warehouse_id=sku.user)
    if not wh_customer_map:
        return supplier_id, price, taxes
    cm_id = wh_customer_map[0].customer_id
    generic_order_id = get_generic_order_id(cm_id)
    near_whs = NetworkMaster.objects.filter(dest_location_code_id=sku.user).filter(
        source_location_code__userprofile__warehouse_level=1). \
        order_by('lead_time', 'priority')
    if near_whs:
        near_wh = near_whs[0]
        if not near_wh.supplier:
            return '', '', ''
        admin_user = get_priceband_admin_user(User.objects.get(id=sku.user))
        price_type = near_wh.price_type
        supplier_id = near_wh.supplier.id
        price_obj = PriceMaster.objects.filter(price_type=price_type, sku__user=admin_user.id,
                                               sku__sku_code=sku.sku_code,
                                               min_unit_range__lte=qty, max_unit_range__gte=qty)
        unit_price = sku.price
        if price_obj:
            unit_price = price_obj[0].price
        usr = near_wh.source_location_code_id
        usr_sku_master = SKUMaster.objects.get(user=usr, sku_code=sku.sku_code)
        sku_id = usr_sku_master.id
        order_id = get_order_id(usr)
        customer_master = CustomerMaster.objects.get(id=cm_id)
        taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0}
        if customer_master.tax_type:
            inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
            inter_state = inter_state_dict.get(customer_master.tax_type, 2)
            tax_master = TaxMaster.objects.filter(user_id=usr, inter_state=inter_state,
                                                    product_type=usr_sku_master.product_type,
                                                    min_amt__lte=unit_price, max_amt__gte=unit_price)
            if tax_master:
                tax_master = tax_master[0]
                taxes['cgst_tax'] = float(tax_master.cgst_tax)
                taxes['sgst_tax'] = float(tax_master.sgst_tax)
                taxes['igst_tax'] = float(tax_master.igst_tax)
                taxes['utgst_tax'] = float(tax_master.utgst_tax)
        invoice_amount = qty * unit_price
        invoice_amount = invoice_amount + ((invoice_amount/100) * sum(taxes.values()))
        order_data = {'sku_id': sku_id, 'order_id': order_id, 'order_code': order_code,
                      'original_order_id': order_code + str(order_id), 'user': usr, 'quantity': qty,
                      'unit_price': unit_price, 'marketplace': 'Offline', 'customer_id': customer_master.customer_id,
                      'customer_name': customer_master.name, 'invoice_amount': invoice_amount,
                      'title': sku.sku_desc, 'status': 1, 'shipment_date': datetime.datetime.now(),
                      'creation_date': datetime.datetime.now()}
        order_summary_dict = {'discount': 0, 'issue_type': 'order', 'vat': 0, 'tax_value': 0, 'status': 1,
                              'shipment_time_slot': '9-12', 'creation_date': datetime.datetime.now()}
        order_summary_dict.update(taxes)
        order_obj = OrderDetail.objects.filter(order_id=order_data['order_id'], user=usr,
                                               sku_id=sku_id, order_code=order_data['order_code'])
        if not order_obj:
            order_data['sku_id'] = sku_id
            sku_total_qty_map = {sku_id: qty}
            order_user_sku = {}
            order_user_objs = {}
            order_data['del_date'] = datetime.datetime.now() + datetime.timedelta(days=near_wh.lead_time)
            create_generic_order(order_data, cm_id, sku.user, generic_order_id, [], True,
                                 order_summary_dict, '', '', '', admin_user,
                                 sku_total_qty_map, order_user_sku, order_user_objs)
            #qssi order push
            user = User.objects.get(id=usr)
            resp = order_push(order_data['original_order_id'], user, "NEW")
            log.info('New Order Push Status: %s' %(str(resp)))
        price = unit_price
    return supplier_id, price, taxes


@csrf_exempt
def auto_po(wms_codes, user):
    auto_po_switch = get_misc_value('auto_po_switch', user)
    po_sub_user_prefix = get_misc_value('po_sub_user_prefix', user)
    auto_raise_stock_transfer = get_misc_value('auto_raise_stock_transfer', user)
    sku_less_than_threshold = get_misc_value('sku_less_than_threshold', user)
    if 'true' in [auto_po_switch, auto_raise_stock_transfer] or sku_less_than_threshold == 'true':
        sku_codes = SKUMaster.objects.filter(wms_code__in=wms_codes, user=user, threshold_quantity__gt=0)
        price_band_flag = get_misc_value('priceband_sync', user)
        for sku in sku_codes:
            taxes = {}
            qty, total_qty, max_norm_qty = get_auto_po_quantity(sku)
            if total_qty >= int(sku.threshold_quantity):
                continue
            if price_band_flag == 'true':
                intransit_orders = IntransitOrders.objects.filter(sku=sku, user=sku.user, status=1). \
                    values('sku__sku_code').annotate(tot_qty=Sum('quantity'))
                intr_qty = 0
                if intransit_orders:
                    intr_order = intransit_orders[0]
                    intr_qty = intr_order['tot_qty']
                supplier_master_id, price, taxes = auto_po_warehouses(sku, qty)
                moq = qty + intr_qty
                if not supplier_master_id:
                    continue
            elif auto_po_switch == 'true' or sku_less_than_threshold == 'true':
                supplier_id = SKUSupplier.objects.filter(sku_id=sku.id, sku__user=user, moq__gt=0).order_by('preference')
                if not supplier_id:
                    continue
                moq = supplier_id[0].moq
                if not moq:
                    # moq = qty
                    continue
                supplier_master_id = supplier_id[0].supplier_id
                taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0}
                price = supplier_id[0].price
                inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
                inter_state = inter_state_dict.get(supplier_id[0].supplier.tax_type, 2)
                tax_master = TaxMaster.objects.filter(user_id=user, inter_state=inter_state,
                                                      product_type=sku.product_type,
                                                      min_amt__lte=price, max_amt__gte=price).\
                    values('cgst_tax', 'sgst_tax', 'igst_tax', 'utgst_tax')
                if tax_master.exists():
                    taxes = copy.deepcopy(tax_master[0])
            elif auto_raise_stock_transfer == 'true':
                all_data = {}
                user_obj = User.objects.get(id=user)

                wh_sku = WarehouseSKUMapping.objects.filter(sku=sku, sku__user=user_obj.id).order_by("priority")
                if wh_sku:
                    wh_sku = wh_sku[0]
                    cond = wh_sku.warehouse.username
                    all_data[cond] = [[sku.wms_code, qty, wh_sku.price, '']]

                    all_data = insert_st(all_data, user_obj)
                    status = confirm_stock_transfer(all_data, user_obj, cond)
                continue

            if moq <= 0:
                continue
            suggestions_data = OpenPO.objects.filter(sku_id=sku.id, sku__user=user,
                                                     status__in=['Automated', 1, 'Manual'])
            if not suggestions_data.exists():
                order_quantity = max(qty,moq,max_norm_qty)
            else:
                order_quantity = qty
            automated_po = OpenPO.objects.filter(sku_id=sku.id, sku__user=user,
                                                     status='Automated')
            if not automated_po.exists():
                if sku_less_than_threshold == 'true' :
                    push_notify = PushNotifications.objects.filter(user=user ,message = sku.wms_code+"  "+"quantity is below Threshold quantity")
                    if not push_notify.exists() :
                        PushNotifications.objects.create(user_id=user, message=sku.wms_code+"  "+"quantity is below Threshold quantity")
                else:
                    po_suggestions = copy.deepcopy(PO_SUGGESTIONS_DATA)
                    po_suggestions['sku_id'] = sku.id
                    po_suggestions['supplier_id'] = supplier_master_id
                    po_suggestions['order_quantity'] = order_quantity
                    po_suggestions['status'] = 'Automated'
                    po_suggestions['price'] = price
                    po_suggestions['mrp'] = sku.mrp
                    po_suggestions.update(taxes)
                    po = OpenPO(**po_suggestions)
                    po.save()
                    auto_confirm_po = get_misc_value('auto_confirm_po', user)
                    if auto_confirm_po == 'true':
                        po.status = 0
                        po.save()
                        user_obj = User.objects.get(id=user)
                        po_order_id = get_purchase_order_id(user_obj) + 1
                        if po_sub_user_prefix == 'true':
                            po_order_id = update_po_order_prefix(user_obj, po_order_id)
                        user_profile = UserProfile.objects.get(user_id=sku.user)
                        PurchaseOrder.objects.create(open_po_id=po.id, order_id=po_order_id, status='',
                                                     received_quantity=0, po_date=datetime.datetime.now(),
                                                     prefix=user_profile.prefix,
                                                     creation_date=datetime.datetime.now())
                        check_purchase_order_created(User.objects.get(id=user), po_order_id)
            else:
                automated_po = automated_po[0]
                automated_po.order_quantity += order_quantity
                automated_po.save()


@csrf_exempt
def rewrite_excel_file(f_name, index_status, open_sheet):
    # wb = Workbook()
    # ws = wb.add_sheet(open_sheet.name)
    f_name = f_name.replace('+', '')
    wb1, ws1 = get_work_sheet(open_sheet.name, [], f_name)

    if 'xlsx' in f_name:
        header_style = wb1.add_format({'bold': True})
    else:
        header_style = easyxf('font: bold on')

    for row_idx in range(0, open_sheet.nrows):
        if row_idx == 0:
            for col_idx in range(0, open_sheet.ncols):
                ws1.write(row_idx, col_idx, str(open_sheet.cell(row_idx, col_idx).value), header_style)
            ws1.write(row_idx, col_idx + 1, 'Status', header_style)

        else:
            for col_idx in range(0, open_sheet.ncols):
                # print row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value
                if col_idx == 4 and 'xlsx' in f_name:
                    date_format = wb1.add_format({'num_format': 'yyyy-mm-dd'})
                    ws1.write(row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value, date_format)
                else:
                    ws1.write(row_idx, col_idx, open_sheet.cell(row_idx, col_idx).value)

            index_data = index_status.get(row_idx, '')
            if index_data:
                index_data = ', '.join(index_data)
                ws1.write(row_idx, col_idx + 1, index_data)

    if 'xlsx' in f_name:
        wb1.close()
        return f_name
    else:
        path = 'static/temp_files/'
        folder_check(path)
        wb1.save(path + f_name)
        return path + f_name


def read_and_send_excel(file_name):
    with open(file_name, 'r') as excel:
        data = excel.read()
    response = HttpResponse(data, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(file_name.replace('static/temp_files/', ''))
    return response


@csrf_exempt
def rewrite_csv_file(f_name, index_status, reader):
    path = 'static/temp_files/'
    folder_check(path)
    f_name = f_name.replace('+', '')
    with open(path + f_name, 'w') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, delimiter=',')
        counter = 0
        for row in reader:
            if counter == 0:
                row.append('Status')
            else:
                row.append(', '.join(index_status.get(counter, [])))
            thedatawriter.writerow(row)
            counter += 1
    return path + f_name


@csrf_exempt
def write_error_file(f_name, index_status, open_sheet, headers_data, work_sheet):
    headers = copy.copy(headers_data)
    headers.append('Status')
    wb, ws = get_work_sheet(work_sheet, headers)

    f_name = f_name.replace('+', '')
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


def change_seller_stock(seller_id='', stock='', user='', quantity=0, status='dec'):
    # it will create or update seller stock
    if seller_id:
        quantity = float(quantity)
        seller_stock_data = SellerStock.objects.filter(stock_id=stock.id, seller__user=user.id, seller_id=seller_id)
        if seller_stock_data:

            temp_quantity = quantity
            for seller_stock in seller_stock_data:
                if status == 'inc':
                    seller_stock.quantity += quantity
                    temp_quantity = 0
                    seller_stock.save()
                elif status == 'dec':
                    if seller_stock.quantity > temp_quantity:
                        seller_stock.quantity -= temp_quantity
                        temp_quantity = 0
                        seller_stock.save()
                    elif seller_stock.quantity <= temp_quantity:
                        temp_quantity -= seller_stock.quantity
                        seller_stock.quantity = 0
                        seller_stock.save()
                if temp_quantity == 0:
                    break
        else:
            print "Entered else cond"
            SellerStock.objects.create(seller_id=seller_id, stock_id=stock.id, quantity=quantity)


def update_stocks_data(stocks, move_quantity, dest_stocks, quantity, user, dest, sku_id, src_seller_id='',
                       dest_seller_id='', source_updated=False, mrp_dict=None, dest_updated=False,
                       receipt_type='', receipt_number=1):
    batch_obj = ''
    dest_batch = ''
    if not source_updated:
        for stock in stocks:
            batch_obj = stock.batch_detail
            if stock.quantity > move_quantity:
                stock.quantity -= move_quantity
                change_seller_stock(src_seller_id, stock, user, move_quantity, 'dec')
                move_quantity = 0
                if stock.quantity < 0:
                    stock.quantity = 0
                stock.save()
            elif stock.quantity <= move_quantity:
                move_quantity -= stock.quantity
                change_seller_stock(src_seller_id, stock, user, stock.quantity, 'dec')
                stock.quantity = 0
                stock.save()
            if move_quantity == 0:
                break
    else:
        batch_obj = stocks[0].batch_detail
    if not dest_updated:
        if not dest_stocks:
            dict_values = {'receipt_number': receipt_number, 'receipt_date': datetime.datetime.now(),
                           'quantity': float(quantity), 'status': 1,
                           'creation_date': datetime.datetime.now(),
                           'updation_date': datetime.datetime.now(),
                           'location_id': dest[0].id, 'sku_id': sku_id,
                           'receipt_type': receipt_type}
            if mrp_dict:
                mrp_dict['creation_date'] = datetime.datetime.now()
                new_batch = BatchDetail.objects.create(**mrp_dict)
                dict_values['batch_detail_id'] = new_batch.id
                dest_batch = new_batch
            elif batch_obj:
                dict_values['batch_detail'] = batch_obj
                dest_batch = batch_obj
            if batch_obj:
                batch_stock_filter = {'sku_id': sku_id, 'location_id': dest[0].id, 'batch_detail_id': batch_obj.id,
                                      'quantity__gt': 0}
                if dest_seller_id:
                    batch_stock_filter['sellerstock__seller_id'] = dest_seller_id
                dest_stock_objs = StockDetail.objects.filter(**batch_stock_filter)
                if not dest_stock_objs:
                    dest_stocks = StockDetail(**dict_values)
                    dest_stocks.save()
                    change_seller_stock(dest_seller_id, dest_stocks, user, float(quantity), 'create')
                else:
                    dest_stocks = dest_stock_objs[0]
                    dest_stocks.quantity = dest_stocks.quantity + float(quantity)
                    dest_stocks.save()
                    change_seller_stock(dest_seller_id, dest_stocks, user, float(quantity), 'inc')
            else:
                dest_stocks = StockDetail(**dict_values)
                dest_stocks.save()
                change_seller_stock(dest_seller_id, dest_stocks, user, float(quantity), 'create')
        else:
            dest_stocks = dest_stocks[0]
            dest_stocks.quantity += float(quantity)
            dest_stocks.save()
            change_seller_stock(dest_seller_id, dest_stocks, user, quantity, 'inc')
            if dest_stocks.batch_detail:
                dest_batch = dest_stocks.batch_detail
    return dest_batch

def move_stock_location(wms_code, source_loc, dest_loc, quantity, user, seller_id='', batch_no='', mrp='',
                        weight='', receipt_number='', receipt_type='',reason=''):
    # sku = SKUMaster.objects.filter(wms_code=wms_code, user=user.id)
    try:
        sku = check_and_return_mapping_id(wms_code, "", user, False)
        if sku:
            sku_id = sku
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

        if seller_id:
            seller_id = SellerMaster.objects.filter(user=user.id, seller_id=seller_id)
            if not seller_id:
                return 'Seller Not Found'
            seller_id = seller_id[0].id

        stock_dict = {"sku_id": sku_id,
                      "location_id": source[0].id,
                      "sku__user": user.id}
        reserved_dict = {'stock__sku_id': sku_id, 'stock__sku__user': user.id, 'status': 1,
                         'stock__location_id': source[0].id}
        raw_reserved_dict = {'stock__sku_id': sku_id, 'stock__sku__user': user.id, 'status': 1,
                             'stock__location_id': source[0].id}
        if batch_no:
            stock_dict["batch_detail__batch_no"] =  batch_no
            reserved_dict["stock__batch_detail__batch_no"] =  batch_no
            raw_reserved_dict["stock__batch_detail__batch_no"] = batch_no
        if mrp:
            stock_dict["batch_detail__mrp"] = mrp
            reserved_dict["stock__batch_detail__mrp"] = mrp
            raw_reserved_dict["stock__batch_detail__mrp"] = mrp
        if weight:
            stock_dict["batch_detail__weight"] =  weight
            reserved_dict["stock__batch_detail__weight"] =  weight
            raw_reserved_dict["stock__batch_detail__weight"] = weight
        if seller_id:
            stock_dict['sellerstock__seller_id'] = seller_id
            reserved_dict["stock__sellerstock__seller_id"] = seller_id
            raw_reserved_dict["stock__sellerstock__seller_id"] = seller_id
        stocks = StockDetail.objects.filter(**stock_dict).distinct()
        if not stocks:
            return 'No Stocks Found'
        stock_count = stocks.aggregate(Sum('quantity'))['quantity__sum']
        #stocks = StockDetail.objects.filter(sku_id=sku_id, location_id=source[0].id, sku__user=user.id)
        # stock_count = stocks.aggregate(Sum('quantity'))['quantity__sum']
        # if seller_id:
        #     stock_filter_ids = stocks.filter(quantity__gt=0).values_list('id', flat=True)
        #     seller_stock = SellerStock.objects.filter(stock_id__in=stock_filter_ids, seller_id=seller_id)
        #     if not seller_stock:
        #         return 'Seller Stock Not Found'
        reserved_quantity = \
        PicklistLocation.objects.exclude(stock=None).filter(**reserved_dict).aggregate(Sum('reserved'))[
            'reserved__sum']
        raw_reserved_quantity = RMLocation.objects.exclude(stock=None).filter(**raw_reserved_dict). \
            aggregate(Sum('reserved'))['reserved__sum']
        if not reserved_quantity:
            reserved_quantity = 0
        if not raw_reserved_quantity:
            raw_reserved_quantity = 0
        avail_stock = stock_count - reserved_quantity - raw_reserved_quantity
        if avail_stock < float(quantity):
            return 'Quantity Exceeding available quantity'
        # if reserved_quantity:
        #     if (stock_count - reserved_quantity) < float(quantity):
        #         return 'Source Quantity reserved for Picklist'

        stock_dict['location_id'] = dest[0].id
        stock_dict['quantity__gt'] = 0
        dest_stocks = StockDetail.objects.filter(**stock_dict).distinct()

        dest_batch = update_stocks_data(stocks, move_quantity, dest_stocks, quantity, user, dest, sku_id, src_seller_id=seller_id,
                           dest_seller_id=seller_id, receipt_type=receipt_type, receipt_number=receipt_number)
        move_inventory_dict = {'sku_id': sku_id, 'source_location_id': source[0].id,'reason':reason,
                               'dest_location_id': dest[0].id, 'quantity': move_quantity, }
        if seller_id:
            move_inventory_dict['seller_id'] = seller_id
        if dest_batch:
            move_inventory_dict['batch_detail_id'] = dest_batch.id

        MoveInventory.objects.create(**move_inventory_dict)

        return 'Added Successfully'
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        result_data = []
        log.info('move stock location failed  for {} source location {} destination location {} quantity {}'
                 .format(wms_code, source_loc, dest_loc, quantity))


def create_invnetory_adjustment_record(user, dat, quantity, reason, location, now, pallet_present, stock='', seller_id='',
                                       adjustment_objs=''):
    data = copy.deepcopy(INVENTORY_FIELDS)
    data['cycle_id'] = dat.id
    data['adjusted_quantity'] = quantity
    data['reason'] = reason
    data['adjusted_location'] = location[0].id
    data['creation_date'] = now
    data['updation_date'] = now
    inv_adj_filter = {'cycle__cycle': dat.cycle, 'adjusted_location': location[0].id,
                      'cycle__sku__user': user.id}
    if stock:
        inv_adj_filter['stock_id'] = stock.id
        data['stock_id'] = stock.id
    if seller_id:
        inv_adj_filter['seller_id'] = seller_id
        data['seller_id'] = seller_id
    if pallet_present:
        inv_adj_filter['pallet_detail_id'] = pallet_present.id
        data['pallet_detail_id'] = pallet_present.id
    inv_obj = InventoryAdjustment.objects.filter(**inv_adj_filter)
    if inv_obj:
        inv_obj = inv_obj[0]
        inv_obj.adjusted_quantity = quantity
        inv_obj.save()
        dat = inv_obj
    else:
        adjustment_objs.append(InventoryAdjustment(**data))
    return adjustment_objs


def adjust_location_stock(cycle_id, wmscode, loc, quantity, reason, user, stock_stats_objs, pallet='', batch_no='', mrp='',
                          seller_master_id='', weight='', receipt_number=1, receipt_type='',):
    now_date = datetime.datetime.now()
    now = str(now_date)
    adjustment_objs = []
    if wmscode:
        sku = SKUMaster.objects.filter(user=user.id, sku_code=wmscode)
        if not sku:
            return 'Invalid WMS Code'
        sku_id = sku[0].id
    if loc:
        location = LocationMaster.objects.filter(zone__user=user.id, location=loc)
        if not location:
            return 'Invalid Location'
    if quantity == '':
        return 'Quantity should not be empty'
    quantity = float(quantity)
    stock_dict = {'sku_id': sku_id, 'location_id': location[0].id,
                  'sku__user': user.id, 'quantity__gt': 0}
    pallet_present = ''
    if pallet:
        pallet_present = PalletDetail.objects.filter(user = user.id, status = 1, pallet_code = pallet)
        if not pallet_present:
            pallet_present = PalletDetail.objects.create(user = user.id, status = 1, pallet_code = pallet,
                quantity = quantity, creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now())
        else:
            pallet_present.update(quantity = quantity)
            pallet_present = pallet_present[0]

        stock_dict['pallet_detail_id'] = pallet_present.id

    if batch_no:
        stock_dict["batch_detail__batch_no"] =  batch_no
    if mrp:
        stock_dict["batch_detail__mrp"] = mrp
    if weight:
        stock_dict["batch_detail__weight"] = weight
    if seller_master_id:
        stock_dict['sellerstock__seller_id'] = seller_master_id
    total_stock_quantity = 0
    dest_stocks = ''

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
    if cycle_obj:
        cycle_obj = cycle_obj[0]
        cycle_obj.seen_quantity += quantity
        cycle_obj.save()
        dat = cycle_obj
    else:
        dat = CycleCount(**data_dict)
        dat.save()

    if quantity:
        #quantity = float(quantity)
        stocks = StockDetail.objects.filter(**stock_dict).distinct().order_by('-id')
        if user.userprofile.user_type == 'marketplace_user':
            total_stock_quantity = SellerStock.objects.filter(seller_id=seller_master_id,
                                                              stock__id__in=stocks.values_list('id', flat=True)). \
                aggregate(Sum('quantity'))['quantity__sum']
        else:
            total_stock_quantity = stocks.aggregate(Sum('quantity'))['quantity__sum']
        if not total_stock_quantity:
            total_stock_quantity = 0
        remaining_quantity = total_stock_quantity - quantity
        for stock in stocks:
            if total_stock_quantity < quantity:
                stock.quantity += abs(remaining_quantity)
                stock_stats_objs = save_sku_stats(user, sku_id, dat.id, 'inventory-adjustment', abs(remaining_quantity), stock, stock_stats_objs, bulk_insert=True)
                stock.save()
                change_seller_stock(seller_master_id, stock, user, abs(remaining_quantity), 'inc')
                adjustment_objs = create_invnetory_adjustment_record(user, dat, abs(remaining_quantity), reason, location, now, pallet_present,
                                                   stock=stock, seller_id=seller_master_id, adjustment_objs=adjustment_objs)
                break
            else:
                stock_quantity = float(stock.quantity)
                if not stock_quantity:
                    continue
                if remaining_quantity == 0:
                    break
                elif stock_quantity >= remaining_quantity:
                    setattr(stock, 'quantity', stock_quantity - remaining_quantity)
                    stock_stats_objs = save_sku_stats(user, sku_id, dat.id, 'inventory-adjustment', -remaining_quantity, stock, stock_stats_objs, bulk_insert=True)
                    stock.save()
                    change_seller_stock(seller_master_id, stock, user, remaining_quantity, 'dec')
                    adjustment_objs = create_invnetory_adjustment_record(user, dat, -remaining_quantity, reason, location, now, pallet_present,
                                                       stock=stock, seller_id=seller_master_id,
                                                        adjustment_objs=adjustment_objs)
                    remaining_quantity = 0
                elif stock_quantity < remaining_quantity:
                    setattr(stock, 'quantity', 0)
                    stock_stats_objs = save_sku_stats(user, sku_id, dat.id, 'inventory-adjustment', -stock_quantity, stock, stock_stats_objs, bulk_insert=True)
                    stock.save()
                    change_seller_stock(seller_master_id, stock, user, stock_quantity,
                                        'dec')
                    remaining_quantity = remaining_quantity - stock_quantity
                    adjustment_objs = create_invnetory_adjustment_record(user, dat, -stock_quantity, reason, location, now, pallet_present,
                                                       stock=stock, seller_id=seller_master_id, adjustment_objs=adjustment_objs)
        if not stocks:
            batch_dict = {}
            stock_dict1 = copy.deepcopy(stock_dict)
            del stock_dict1['quantity__gt']
            if batch_no:
                batch_dict = {'batch_no': batch_no}
                del stock_dict["batch_detail__batch_no"]
            if mrp:
                batch_dict['mrp'] = mrp
                del stock_dict["batch_detail__mrp"]
            if weight:
                batch_dict['weight'] = weight
                del stock_dict["batch_detail__weight"]
            if 'sellerstock__seller_id' in stock_dict.keys():
                del stock_dict['sellerstock__seller_id']
            latest_batch = SellerPOSummary.objects.filter(purchase_order__open_po__sku_id=sku_id, receipt_number=1).\
                                                    exclude(batch_detail__isnull=True)
            if latest_batch.exists():
                batch_obj = latest_batch.latest('id').batch_detail
                batch_dict['buy_price'] = batch_obj.buy_price
                batch_dict['tax_percent'] = batch_obj.tax_percent
                add_ean_weight_to_batch_detail(sku[0], batch_dict)

            #latest_stock = StockDetail.objects.filter(**stock_dict1)
            #if latest_stock.exists():
                #latest_batch = SellerPOSummary.objects.filter(purchase_order__open_po__sku_id=sku_id, receipt_number=1).\
                #                                        exclude(batch_detail__isnull=True).latest('id')
                #latest_stock_obj = latest_stock.latest('id')
                #batch_obj = latest_stock_obj.batch_detail
                #if batch_obj:
                #    stock_dict["batch_detail_id"] = batch_obj.id
            if batch_dict.keys():
                batch_obj = BatchDetail.objects.create(**batch_dict)
                stock_dict["batch_detail_id"] = batch_obj.id
            if pallet:
                del stock_dict['pallet_detail_id']
            del stock_dict["sku__user"]
            stock_dict.update({"receipt_number": receipt_number, "receipt_date": now_date, "receipt_type": receipt_type,
                               "quantity": quantity, "status": 1, "creation_date": now_date,
                               "updation_date": now_date
                              })
            del stock_dict['quantity__gt']
            dest_stocks = StockDetail(**stock_dict)
            dest_stocks.save()
            stock_stats_objs = save_sku_stats(user, sku_id, dat.id, 'inventory-adjustment', dest_stocks.quantity, dest_stocks, stock_stats_objs, bulk_insert=True)
            change_seller_stock(seller_master_id, dest_stocks, user, abs(remaining_quantity), 'create')
            adjustment_objs = create_invnetory_adjustment_record(user, dat, abs(remaining_quantity), reason, location, now, pallet_present,
                                               stock=dest_stocks, seller_id=seller_master_id, adjustment_objs=adjustment_objs)

    if quantity == 0:
        stock_dict['quantity__gt'] = 0
        all_stocks = StockDetail.objects.filter(**stock_dict).distinct()
        for stock in all_stocks:
            stock_quantity = stock.quantity
            SellerStock.objects.filter(stock_id=stock.id).update(quantity=0)
            stock.quantity = 0
            stock.save()
            stock_stats_objs = save_sku_stats(user, stock.sku_id, dat.id, 'inventory-adjustment', -stock_quantity, stock, stock_stats_objs, bulk_insert=True)
            adjustment_objs = create_invnetory_adjustment_record(user, dat, -stock_quantity, reason, location, now, pallet_present,
                                               stock=stock, seller_id=seller_master_id, adjustment_objs=adjustment_objs)

    if adjustment_objs:
        InventoryAdjustment.objects.bulk_create(adjustment_objs)
    return 'Added Successfully', stock_stats_objs


def update_picklist_locations(pick_loc, picklist, update_picked, update_quantity='', decimal_limit=0):
    for pic_loc in pick_loc:
        if float(pic_loc.reserved) >= update_picked:
            pic_loc.reserved = truncate_float(float(pic_loc.reserved) - update_picked, decimal_limit)
            if update_quantity:
                pic_loc.quantity = truncate_float(float(pic_loc.quantity) - update_picked, decimal_limit)
            update_picked = 0
        elif float(pic_loc.reserved) < update_picked:
            update_picked = truncate_float(update_picked - pic_loc.reserved, decimal_limit)
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
    #permissions = Permission.objects.all()
    permissions = user.user_permissions.filter()
    prod_stages = ProductionStages.objects.filter(user=user.id).values_list('stage_name', flat=True)
    brands = Brands.objects.filter(user=user.id).values_list('brand_name', flat=True)
    order_statuses = get_misc_value('extra_view_order_status', user.id)
    order_statuses = order_statuses.split(',')
    perms_list = []
    ignore_list = ['session', 'webhookdata', 'swxmapping', 'userprofile', 'useraccesstokens', 'contenttype', 'user',
                   'permission', 'group', 'logentry']
    permission_dict = copy.deepcopy(PERMISSION_DICT)
    reversed_perms = {}
    exclude_labels = ['UPLOADS']
    for key, value in permission_dict.iteritems():
        if key in exclude_labels:
            continue
        sub_perms = permission_dict[key]
        if len(sub_perms) == 2:
            reversed_perms[sub_perms[1]] = sub_perms[0]
        else:
            for i in sub_perms:
                reversed_perms[i[1]] = i[0]

    for permission in permissions:
        temp = permission.codename
        if not temp in perms_list and not temp in ignore_list:
            if temp in reversed_perms.keys() and reversed_perms[temp] not in perms_list:
                perms_list.append(reversed_perms[temp])
    return HttpResponse(
        json.dumps({'perms_list': perms_list, 'prod_stages': list(prod_stages), 'brands': list(brands),
                    'order_statuses': order_statuses}))


@csrf_exempt
@login_required
@get_admin_user
def add_group(request, user=''):
    perm_selected_list = ''
    stages_list = ''
    selected_list = ''
    brands_list = ''
    status_list = ''
    group = ''
    permission_dict = copy.deepcopy(PERMISSION_DICT)
    reversed_perms = {}
    for key, value in permission_dict.iteritems():
        sub_perms = permission_dict[key]
        for i in sub_perms:
            reversed_perms[i[1]] = i[0]
    # reversed_perms = OrderedDict(( ([(value, key) for key, value in permission_dict.iteritems()]) ))
    selected = request.POST.get('perm_selected')
    stages = request.POST.get('stage_selected')
    brands = request.POST.get('brand_selected')
    statuses = request.POST.get('status_selected')
    if selected:
        selected_list = selected.split(',')
    if stages:
        stages_list = stages.split(',')
    if brands:
        brands_list = brands.split(',')
    if statuses:
        status_list = statuses.split(',')

    name = request.POST.get('name')
    if name:
        name = user.username + ' ' + name
    group_exists = Group.objects.filter(name=name)
    if group_exists:
        return HttpResponse('Group Name already exists')
    if not group_exists and (selected_list or stages_list or brands_list or status_list):
        group, created = Group.objects.get_or_create(name=name)
        if stages_list:
            stage_group = GroupStages.objects.create(group=group)
        if brands_list:
            brand_group = GroupBrand.objects.create(group=group)
        for stage in stages_list:
            if not stage:
                continue
            stage_obj = ProductionStages.objects.filter(stage_name=stage, user=user.id)
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
        for stage in stages_list:
            if not stage:
                continue
            stage_obj = ProductionStages.objects.filter(stage_name=stage, user=user.id)
            if stage_obj:
                stage_group.stages_list.add(stage_obj[0])
                stage_group.save()
        for sequence, ord_status in enumerate(status_list):
            if not ord_status:
                continue
            group_perm_obj = GroupPermMapping.objects.filter(group_id=group.id, perm_type='extra_order_status',
                                                             perm_value=ord_status)
            if group_perm_obj:
                group_perm = group_perm_obj[0]
                group_perm.perm_value = ord_status
                group_perm.save()
            else:
                GroupPermMapping.objects.create(group_id=group.id, perm_type='extra_order_status',
                                                perm_value=ord_status, sequence=sequence)
        for perm in selected_list:
            if not perm:
                continue
            for key, value in permission_dict.iteritems():
                sub_perms = permission_dict[key]
                if len(sub_perms) == 2:
                    if sub_perms[0] == perm:
                        permi = sub_perms[1]
                        permissions = Permission.objects.filter(codename=permi)
                        for permission in permissions:
                            group.permissions.add(permission)
                else:
                    sub_perms = dict(sub_perms)
                    if sub_perms.has_key(perm):
                        permissions = Permission.objects.filter(codename=sub_perms[perm])
                        for permission in permissions:
                            group.permissions.add(permission)
        user.groups.add(group)
    return HttpResponse('Updated Successfully')


@csrf_exempt
@login_required
@get_admin_user
def get_user_data(request, user=''):
    for key, value in request.GET.iteritems():
        group_names = []
        exclude_list = ['Pull to locate', 'Admin', 'WMS']
        exclude_group = AdminGroups.objects.filter(user_id=user.id)
        if exclude_group:
            exclude_list.append(exclude_group[0].group.name)
        cur_user = User.objects.get(id=value)
        groups = user.groups.filter().exclude(name__in=exclude_list)
        user_groups = cur_user.groups.filter()
        if user_groups:
            for i in user_groups:
                i_name = (i.name).replace(user.username + ' ', '')
                group_names.append(i_name)
        total_groups = []
        for group in groups:
            group_name = (group.name).replace(user.username + ' ', '')
            total_groups.append(group_name)
    return HttpResponse(
        json.dumps({'username': cur_user.username, 'first_name': cur_user.first_name, 'groups': total_groups,
                    'user_groups': group_names, 'id': cur_user.id}))


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
    upload_files_path = OrderedDict((('sku_upload', {'file_name': 'sku_form.xls', 'function_name': 'sku_excel_upload',
                                                     'validate_func_name': 'validate_sku_form'}),
                                     ('location_upload',
                                      {'file_name': 'location_form.xls', 'function_name': 'process_location'}),
                                     ('supplier_upload',
                                      {'file_name': 'supplier_form.xls', 'function_name': 'supplier_excel_upload'}),
                                     ('inventory_upload',
                                      {'file_name': 'inventory_form.xls', 'function_name': 'inventory_excel_upload',
                                       'validate_func_name': 'validate_inventory_form'}),
                                     ('order_upload',
                                      {'file_name': 'order_form.xls', 'function_name': 'order_csv_xls_upload'}),
                                     ('purchase_order_upload', {'file_name': 'purchase_order_form.xls',
                                                                'function_name': 'purchase_order_excel_upload',
                                                                'validate_func_name':'validate_purchase_order'})

                                     ))

    for key, value in upload_files_path.iteritems():
        open_book = open_workbook(os.path.join(settings.BASE_DIR + "/rest_api/demo_data/", value['file_name']))
        open_sheet = open_book.sheet_by_index(0)
        func_params = [request, open_sheet, user]
        if key in ['purchase_order_upload', 'inventory_upload']:
            reader = open_sheet
            no_of_rows = reader.nrows
            file_type = 'xls'
            no_of_cols = open_sheet.ncols
            func_params = [request, reader, user, no_of_rows, no_of_cols, open_sheet.name,file_type]
            if key in ['purchase_order_upload']:
                func_params.append(True)
            in_status, data_list = eval(value['validate_func_name'])(*func_params)
            eval(value['function_name'])(request, user, data_list)
            continue
        elif key in ['sku_upload']:
            reader = open_sheet
            no_of_rows = reader.nrows
            file_type = 'xls'
            no_of_cols = open_sheet.ncols
            in_status = eval(value['validate_func_name'])(request, reader, user, no_of_rows, no_of_cols, open_sheet,
                                                           file_type)
            eval(value['function_name'])(request, reader, user, no_of_rows, no_of_cols, open_sheet,
                                              file_type='xls')
            continue
        elif key in ['order_upload']:
            func_params.append(open_sheet.nrows)
            func_params.append(value['file_name'])
        elif key in ['supplier_upload']:
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
        elif stage_obj:
            stage_obj[0].order = index
            stage_obj[0].save()
        index += 1
    deleted_stages = set(all_stages) - set(stages)
    for stage in deleted_stages:
        ProductionStages.objects.get(stage_name=stage, user=user.id).delete()
        job_ids = JobOrder.objects.filter(product_code__user=user.id,
                                          status__in=['grn-generated', 'pick_confirm']).values_list('id', flat=True)
        StatusTracking.objects.filter(status_value=stage, status_id__in=job_ids, status_type='JO').delete()
    return HttpResponse("Saved Successfully")
@csrf_exempt
@login_required
@get_admin_user
def save_order_extra_fields(request, user=''):
    order_extra_fields = request.GET.get('extra_order_fields', '')
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='extra_order_fields')
    try:
        if not misc_detail.exists():
             MiscDetail.objects.create(user=user.id,misc_type='extra_order_fields',misc_value=order_extra_fields)
        else:
            misc_order_option_list = list(MiscDetailOptions.objects.filter(misc_detail__user=user.id).values_list('misc_key',flat=True))
            order_extra_list = order_extra_fields.split(',')
            diff_list = list(set(misc_order_option_list)- set(order_extra_list))
            if len(diff_list) > 0 :
                for key in diff_list :
                    misc_records = MiscDetailOptions.objects.filter(misc_detail__user= user.id,misc_key = key)
                    for record in misc_records :
                        record.delete()
            misc_detail_obj = misc_detail[0]
            misc_detail_obj.misc_value = order_extra_fields
            misc_detail_obj.save()
    except:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Issue for ' + request)
        return HttpResponse("Something Went Wrong")

    return HttpResponse("Saved Successfully")

@csrf_exempt
@login_required
@get_admin_user
def save_order_sku_extra_fields(request, user=''):
    extra_order_sku_fields = request.GET.get('extra_order_sku_fields', '')
    misc_detail = MiscDetail.objects.filter(user=user.id, misc_type='extra_order_sku_fields')
    try:
        if not misc_detail.exists():
             MiscDetail.objects.create(user=user.id,misc_type='extra_order_sku_fields',misc_value=extra_order_sku_fields)
        else:
            misc_order_option_list = list(MiscDetailOptions.objects.filter(misc_detail__user=user.id).values_list('misc_key',flat=True))
            order_extra_list = extra_order_sku_fields.split(',')
            diff_list = list(set(misc_order_option_list)- set(order_extra_list))
            if len(diff_list) > 0 :
                for key in diff_list :
                    misc_records = MiscDetailOptions.objects.filter(misc_detail__user= user.id,misc_key = key)
                    for record in misc_records :
                        record.delete()
            misc_detail_obj = misc_detail[0]
            misc_detail_obj.misc_value = extra_order_sku_fields
            misc_detail_obj.save()
    except:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Issue for ' + request)
        return HttpResponse("Something Went Wrong")

    return HttpResponse("Saved Successfully")

@csrf_exempt
@login_required
@get_admin_user
def save_config_extra_fields(request, user=''):
    field_type = request.GET.get('field_type', '')
    fields = request.GET.get('config_extra_fields', '')
    field_type =field_type.strip('.')
    if len(fields.split(',')) <=  4 or field_type == 'move_inventory_reasons' :
        misc_detail = MiscDetail.objects.filter(user=user.id, misc_type=field_type)
        try:
            if not misc_detail.exists():
                 MiscDetail.objects.create(user=user.id,misc_type=field_type,misc_value=fields)
            else:
                misc_detail_obj = misc_detail[0]
                misc_detail_obj.misc_value = fields
                misc_detail_obj.save()
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Issue for {} withe exception {}'.format(request.GET.dict(),str(e)))
            return HttpResponse("Something Went Wrong")
    else:
        return HttpResponse("Limit Exceeded Enter only Four Fields")


    return HttpResponse("Saved Successfully")

@csrf_exempt
@login_required
@get_admin_user
def search_wms_codes(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    data_id = request.GET.get('q', '')
    sku_type = request.GET.get('type', '')
    extra_filter = {}
    data_exact = sku_master.filter(Q(wms_code__iexact=data_id) | Q(sku_desc__iexact=data_id), user=user.id).order_by(
        'wms_code')
    exact_ids = list(data_exact.values_list('id', flat=True))
    data = sku_master.exclude(id__in=exact_ids).filter(Q(wms_code__icontains=data_id) | Q(sku_desc__icontains=data_id),
                                                       user=user.id).order_by('wms_code')
    market_place_code = MarketplaceMapping.objects.filter(marketplace_code__icontains=data_id,
                                                          sku__user=user.id).values_list('sku__sku_code',
                                                                                         flat=True).distinct()
    market_place_code = list(market_place_code)
    data = list(chain(data_exact, data))
    wms_codes = []
    count = 0
    if data:
        for wms in data:
            wms_codes.append(str(wms.wms_code))
            #if not sku_type in ['FG', 'RM', 'CS']:
            #    wms_codes.append(str(wms.wms_code))
            #elif wms.sku_type in ['FG', 'RM', 'CS']:
            #    wms_codes.append(str(wms.wms_code))
            if len(wms_codes) >= 10:
                break
    if len(wms_codes) <= 10:
        if market_place_code:
            for marketplace in market_place_code:
                if len(wms_codes) <= 10:
                    if marketplace not in wms_codes:
                        wms_codes.append(marketplace)
                else:
                    break

    # wms_codes = list(set(wms_codes))

    return HttpResponse(json.dumps(wms_codes))

@csrf_exempt
@login_required
@get_admin_user
def search_sku_brands(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    data_id = request.GET.get('q', '')
    sku_type = request.GET.get('type', '')
    extra_filter = {}
    data_exact = sku_master.filter(Q(sku_brand__iexact=data_id) | Q(sku_desc__iexact=data_id), user=user.id).order_by(
        'sku_brand')
    exact_ids = list(data_exact.values_list('id', flat=True))
    data = sku_master.exclude(id__in=exact_ids).filter(Q(sku_brand__icontains=data_id) | Q(sku_desc__icontains=data_id),
                                                       user=user.id).order_by('sku_brand')
    market_place_code = MarketplaceMapping.objects.filter(marketplace_code__icontains=data_id,
                                                          sku__user=user.id).values_list('sku__sku_code',
                                                                                         flat=True).distinct()
    market_place_code = list(market_place_code)
    data = list(chain(data_exact, data))
    sku_brands = []
    count = 0
    if data:
        for brand in data:
            sku_brands.append(str(brand.sku_brand))
            if len(sku_brands) >= 10:
                break
    if len(sku_brands) <= 10:
        if market_place_code:
            for marketplace in market_place_code:
                if len(sku_brands) <= 10:
                    if marketplace not in sku_brands:
                        sku_brands.append(marketplace)
                else:
                    break
    return HttpResponse(json.dumps(list(set(sku_brands))))

@csrf_exempt
@login_required
@get_admin_user
def search_sku_categorys(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    data_id = request.GET.get('q', '')
    sku_type = request.GET.get('type', '')
    extra_filter = {}
    data_exact = sku_master.filter(Q(sku_category__iexact=data_id) | Q(sku_desc__iexact=data_id), user=user.id).order_by(
        'sku_category')
    exact_ids = list(data_exact.values_list('id', flat=True))
    data = sku_master.exclude(id__in=exact_ids).filter(Q(sku_category__icontains=data_id) | Q(sku_desc__icontains=data_id),
                                                       user=user.id).order_by('sku_category')
    market_place_code = MarketplaceMapping.objects.filter(marketplace_code__icontains=data_id,
                                                          sku__user=user.id).values_list('sku__sku_code',
                                                                                         flat=True).distinct()
    market_place_code = list(market_place_code)
    data = list(chain(data_exact, data))
    sku_categorys = []
    count = 0
    if data:
        for category in data:
            sku_categorys.append(str(category.sku_category))
            if len(sku_categorys) >= 10:
                break
    if len(sku_categorys) <= 10:
        if market_place_code:
            for marketplace in market_place_code:
                if len(sku_categorys) <= 10:
                    if marketplace not in sku_categorys:
                        sku_categorys.append(marketplace)
                else:
                    break
    return HttpResponse(json.dumps(list(set(sku_categorys))))

@csrf_exempt
@login_required
@get_admin_user
def search_batches(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    data_id = request.GET.get('q', '')
    row_data = json.loads(request.GET.get('type'))
    search_params = {'sku__user': user.id}
    if row_data.get('wms_code', ''):
        search_params['sku__sku_code'] =  row_data['wms_code']

    if row_data['location']:
        location_master = LocationMaster.objects.filter(zone__user=user.id, location=row_data['location'])
        if not location_master:
            return HttpResponse(json.dumps({'status': 0, 'message': 'Invalid Location'}))
        search_params['location__location'] = row_data['location']

    if row_data.get('pallet_code', ''):
        search_params['pallet_detail__pallet_code'] = row_data['pallet_code']
        stock_detail = StockDetail.objects.exclude(
            Q(receipt_number=0) | Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'])). \
            filter(location__location=request.GET.get('location', ''), sku__user=user.id,
                   sku__sku_code=search_params['sku__sku_code'],
                   pallet_detail__pallet_code=request.GET['pallet_code'])
        if not stock_detail:
            return HttpResponse(json.dumps({'status': 0, 'message': 'Invalid Location and Pallet code Combination'}))
    stock_data = StockDetail.objects.exclude(
        Q(receipt_number=0) | Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'])). \
        filter(**search_params)
    batchno =[]
    total_data =[]
    if stock_data:
        for stock in stock_data:
            try:
                manufactured_date = datetime.datetime.strftime(stock.batch_detail.manufactured_date, "%d/%m/%Y")
                batchno =  stock.batch_detail.batch_no
            except:
                manufactured_date = ''
                batchno  = ''
            try:
                expiry_batches_picklist = get_misc_value('block_expired_batches_picklist', user.id)
                if stock.batch_detail.batch_no and expiry_batches_picklist == 'true':
                    present_date = datetime.datetime.now().date()
                    if stock.batch_detail.expiry_date and stock.batch_detail.expiry_date >= present_date:
                        total_data.append({'batchno': batchno, 'manufactured_date':manufactured_date })
                else:
                    if batchno:
                        total_data.append({'batchno': batchno, 'manufactured_date':manufactured_date })
            except:
                total_data.append({'batchno': batchno, 'manufactured_date':manufactured_date })
    return HttpResponse(json.dumps(total_data))


@csrf_exempt
@login_required
@get_admin_user
def search_corporate_names(request, user=''):
    data_id = request.GET.get('q', '')
    data_exact = CorporateMaster.objects.filter(Q(name__iexact=data_id), user=user.id).order_by('name')
    exact_ids = list(data_exact.values_list('id', flat=True))
    data = CorporateMaster.objects.exclude(id__in=exact_ids).filter(Q(name__icontains=data_id),
                                                                    user=user.id).order_by('name')
    data = list(chain(data_exact, data))
    corporate_names = []
    if data:
        for corporate in data:
            corporate_names.append(str(corporate.name))
            if len(corporate_names) >= 10:
                break
    return HttpResponse(json.dumps(corporate_names))


@csrf_exempt
@login_required
@get_admin_user
def search_reseller_names(request, user=''):
    from rest_api.views.outbound import get_same_level_warehouses
    data_id = request.GET.get('q', '')
    distributors = get_same_level_warehouses(2, user)
    data_exact = CustomerMaster.objects.filter(Q(name__iexact=data_id), user__in=distributors).order_by('name')
    exact_ids = list(data_exact.values_list('id', flat=True))
    data = CustomerMaster.objects.exclude(id__in=exact_ids).filter(Q(name__icontains=data_id),
                                                                    user__in=distributors).order_by('name')
    data = list(chain(data_exact, data))
    reseller_names = []
    if data:
        for reseller in data:
            reseller_names.append(str(reseller.name))
            if len(reseller_names) >= 10:
                break
    return HttpResponse(json.dumps(reseller_names))


@csrf_exempt
@login_required
@get_admin_user
def search_distributor_codes(request, user=''):
    from rest_api.views.outbound import get_same_level_warehouses
    data_id = request.GET.get('q', '')
    distributors = get_same_level_warehouses(2, user)
    data_exact = UserProfile.objects.filter(user__in=distributors).filter(Q(user__first_name__iexact=data_id))
    exact_ids = list(data_exact.values_list('id', flat=True))
    data = UserProfile.objects.exclude(id__in=exact_ids).filter(user__in=distributors).\
        filter(Q(user__first_name__icontains=data_id)).order_by('user__first_name')
    data = list(chain(data_exact, data))
    distributor_codes = []
    if data:
        for distributor in data:
            distributor_codes.append(str(distributor.user.first_name))
            if len(distributor_codes) >= 10:
                break
    return HttpResponse(json.dumps(distributor_codes))


def get_order_id(user_id, is_pos=False):
    user = User.objects.get(id=user_id)
    order_id = get_incremental(user, 'order')
    # if is_pos:
    #     order_key = "-order_id"
    # else:
    #     order_key = "-creation_date"
    # order_code = get_order_prefix(user_id)
    # order_detail_id = OrderDetail.objects.filter(Q(order_code__in=\
    #                                       [order_code, 'Delivery Challan', 'sample', 'R&D', 'CO','Pre Order']) |
    #                                       reduce(operator.or_, (Q(order_code__icontains=x)\
    #                                       for x in ['DC', 'PRE'])), user=user_id)
    # if order_detail_id.exists():
    #     order_detail_id = order_detail_id.latest("creation_date")
    # if order_detail_id:
    #     order_id = int(order_detail_id.order_id) + 1
    # else:
    #     order_id = 1001
    return order_id


def get_generic_order_id(customer_id):
    gen_ord_qs = GenericOrderDetailMapping.objects.filter(customer_id=customer_id).order_by('-generic_order_id')
    if gen_ord_qs:
        gen_ord_id = int(gen_ord_qs[0].generic_order_id) + 1
    else:
        gen_ord_id = 10001

    return gen_ord_id

def get_approval_id(customer_id):
    cust_cart_qs = ApprovingOrders.objects.filter(customer_user_id=customer_id).order_by('-approve_id')
    cust_appr_id = 10001
    if cust_cart_qs:
        if cust_cart_qs[0].approve_id:
            cust_appr_id = int(cust_cart_qs[0].approve_id) + 1
    return cust_appr_id

def get_intr_order_id(user_id):
    intr_ord_qs = IntransitOrders.objects.filter(user=user_id).order_by('-intr_order_id')
    if intr_ord_qs:
        intr_ord_id = int(intr_ord_qs[0].intr_order_id) + 1
    else:
        intr_ord_id = 10001

    return intr_ord_id


def get_enquiry_id(customer_id):
    enq_qs = EnquiryMaster.objects.filter(customer_id=customer_id).order_by('-enquiry_id')
    if enq_qs:
        enq_id = int(enq_qs[0].enquiry_id) + 1
    else:
        enq_id = 10001
    return enq_id


def get_central_order_id(customer_id):
    inter_qs = IntermediateOrders.objects.filter(customer_user_id=customer_id).order_by('-interm_order_id')
    if inter_qs:
        interm_id = int(inter_qs[0].interm_order_id) + 1
    else:
        interm_id = 10001
    return interm_id


def check_and_update_stock(wms_codes, user):
    stock_sync = get_misc_value('stock_sync', user.id)
    order_code = get_order_prefix(user.id)
    if not stock_sync == 'true':
        return
    from rest_api.views.easyops_api import *
    integrations = Integrations.objects.filter(user=user.id, status=1)
    stock_instances = StockDetail.objects.exclude(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE']).filter(
        sku__wms_code__in=wms_codes,
        sku__user=user.id).values('sku__wms_code').distinct().annotate(total_sum=Sum('quantity'))

    reserved_instances = Picklist.objects.exclude(order__order_code=order_code).filter(status__icontains='picked',
                                                                                 order__user=user.id,
                                                                                 picked_quantity__gt=0,
                                                                                 order__sku__wms_code__in=wms_codes). \
        values('order__sku__wms_code').distinct(). \
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
            temp_data_dict = {'sku': wms_code, 'quantity': sku_count, 'sku_options': []}
            sku_attributes = SKUAttributes.objects.filter(sku__user=user.id, sku__sku_code=wms_code).values('attribute_name', 'attribute_value')
            if sku_attributes.exists():
                temp_data_dict['sku_options'] = list(sku_attributes)
            data.append(temp_data_dict)
        try:
            obj.update_sku_count(data=data, user=user)
        except:
            continue

def mb_stock_sycn_log(data, user):
    today = datetime.datetime.now()
    today_date = get_local_date(user,today,1)
    file_name = 'logs/mb_stock_sync_'+today_date.strftime("%Y%m%d")+'.txt'
    file = open(file_name, 'a')
    file.write(today_date.strftime("%d-%m-%Y %H:%M:%S")+': '+data+'\n')
    file.close()

def check_and_update_marketplace_stock(sku_codes, user):
    from rest_api.views.easyops_api import *
    integrations = Integrations.objects.filter(user=user.id, status=1)
    for integrate in integrations:
        obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
        try:
            sku_tupl = (user.username, sku_codes)
            log.info('Update for stock sync of'+str(sku_tupl))
            log_mb_sync = ('Updating for stock sync of skus %s from the user %s ' %
                                        (str(sku_codes), str(user.username)))
            mb_stock_sycn_log(log_mb_sync, user)
            response = obj.update_stock_count(sku_tupl, user=user)
        except Exception as e:
            log.info('Stock sync failed for %s and skus are %s and error statement is %s'%
                        (str(user.username),str(sku_codes), str(e)))
            log_mb_sync = ('Stock sync failed for %s and skus are %s and error statement is %s'%
                           (str(user.username),str(sku_codes), str(e)))
            mb_stock_sycn_log(log_mb_sync, user)

            continue

def get_order_json_data(user, mapping_id='', mapping_type='', sku_id='', order_ids=[]):
    extra_data = []
    product_images = []
    sku_fields = SKUFields.objects.filter(sku_id=sku_id, field_type='product_attribute')
    jo_order_mapping = OrderMapping.objects.filter(mapping_id=mapping_id, mapping_type=mapping_type,
                                                   order__user=user.id)
    for jo_mapping in jo_order_mapping:
        order_json = OrderJson.objects.filter(order_id=jo_mapping.order_id)
        if order_json:
            extra_data = json.loads(order_json[0].json_data)
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
                                                               image_type='product_property').values_list('image_url',
                                                                                                          flat=True))

    return extra_data, product_images, order_ids


def check_and_update_order(user, order_id):
    from rest_api.views.easyops_api import *
    try:
        log.info("User %s" % str(user))
        user = User.objects.get(id=user)
        user_profile = UserProfile.objects.get(user_id=user)
        integrations = Integrations.objects.filter(user=user.id, status=1)
        for integrate in integrations:
            obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
            try:
                if not user_profile.user_type == 'marketplace_user':
                    obj.confirm_picklist(order_id, user=user)
            except:
                continue
    except:
        log.info("Order Push failed")


def get_financial_year(date):
    # It will return financial period

    date = date.date()
    year_of_date = date.year
    financial_year_start_date = datetime.datetime.strptime(str(year_of_date) + "-04-01", "%Y-%m-%d").date()
    if date < financial_year_start_date:
        return str(financial_year_start_date.year - 1)[2:] + '-' + str(financial_year_start_date.year)[2:]
    else:
        return str(financial_year_start_date.year)[2:] + '-' + str(financial_year_start_date.year + 1)[2:]


def get_challan_number(user, seller_order_summary):
    challan_num = ""
    challan_number = ""
    chn_date = datetime.datetime.now()
    invoice_no_gen = MiscDetail.objects.filter(user=user.id, misc_type='increment_invoice')
    if invoice_no_gen:
        if seller_order_summary:
            if seller_order_summary[0].seller_order:
                order = seller_order_summary[0].seller_order.order
            else:
                order = seller_order_summary[0].order
            challan_num = seller_order_summary[0].challan_number
            if invoice_no_gen[0].misc_value == 'true' and not challan_num:
                challan_sequence = ChallanSequence.objects.filter(user=user.id, status=1, marketplace=order.marketplace)
                if not challan_sequence:
                    challan_sequence = ChallanSequence.objects.filter(user=user.id, marketplace='')
                if challan_sequence:
                    challan_sequence = challan_sequence[0]
                    challan_num = int(challan_sequence.value)
                    order_no = challan_sequence.prefix + str(challan_num).zfill(3)
                    seller_order_summary.update(challan_number=order_no)
                    challan_sequence.value = challan_num + 1
                    challan_sequence.save()
                else:
                    ChallanSequence.objects.create(marketplace='', prefix='CHN', value=1, status=1, user_id=user.id,
                                                   creation_date=datetime.datetime.now())
                    order_no = '001'
                    challan_num = int(order_no)
            elif invoice_no_gen[0].misc_value == 'true' and challan_num:
                seller_order_summary.update(challan_number=challan_num)
            else:
                log.info("Challan No not updated for seller_order_summary")
        challan_number = 'CHN/%s/%s' % (chn_date.strftime('%m%y'), challan_num)
    return challan_number, challan_num


def get_full_invoice_number(user, order_no, order, invoice_date='', pick_number=''):
    user_profile = user.userprofile
    invoice_sequence = ''
    from_pos = False
    if not invoice_date:
        invoice_date = datetime.datetime.now()
    if order:
        cod = order.customerordersummary_set.filter()
        if not invoice_date and cod and cod[0].invoice_date:
            invoice_date = cod[0].invoice_date
        elif not invoice_date and pick_number:
            seller_summary = SellerOrderSummary.objects.filter(Q(seller_order__order_id=order.id) |
                                                               Q(order_id=order.id), pick_number=pick_number)
            if seller_summary:
                invoice_date = seller_summary.creation_date
        if cod:
            if cod[0].issue_type in ['PRE', 'DC']:
                from_pos = True
                order_ids = [order.id]
        invoice_sequence = get_invoice_sequence_obj(user, order.marketplace)
    if invoice_sequence:
        invoice_sequence = invoice_sequence[0]
        inv_num_lis = []
        if invoice_sequence.prefix:
            inv_num_lis.append(invoice_sequence.prefix)
        if invoice_sequence.date_type:
            if invoice_sequence.date_type == 'financial':
                inv_num_lis.append(get_financial_year(invoice_date))
            elif invoice_sequence.date_type == 'month_year':
                inv_num_lis.append(invoice_date.strftime('%m%y'))
        if invoice_sequence.interfix:
            inv_num_lis.append(invoice_sequence.interfix)
        inv_num_lis.append(str(order_no))
        invoice_number = '/'.join(['%s'] * len(inv_num_lis)) % tuple(inv_num_lis)
    else:
        if user_profile.user_type == 'marketplace_user':
            invoice_number = user_profile.prefix + '/' + str(invoice_date.strftime('%m-%y')) + '/A-' + str(order_no)
        elif user.username == 'TranceHomeLinen':
            invoice_number = user_profile.prefix + '/' + str(get_financial_year(invoice_date)) + '/' + 'GST' + '/' + str(
                order_no)
        elif user.username == 'Subhas_Publishing':
            invoice_number = user_profile.prefix + '/' + str(get_financial_year(invoice_date)) + '/' + str(order_no)
        elif user.username == 'campus_sutra':
            invoice_number = str(get_financial_year(invoice_date)) + '/' + str(order_no)
        elif user_profile.warehouse_type == 'DIST':
            invoice_number = 'TI/%s/%s' % (invoice_date.strftime('%m%y'), order_no)
        else:
            if from_pos:
                sub_usr = ''.join(re.findall('\d+', OrderDetail.objects.get(id=order_ids[0]).order_code))
                invoice_number = 'TI/%s/%s' % (invoice_date.strftime('%m%y'), sub_usr + order_no)
            else:
                invoice_number = 'TI/%s/%s' % (invoice_date.strftime('%m%y'), order_no)
    return invoice_number


def get_invoice_number(user, order_no, invoice_date, order_ids, user_profile, from_pos=False, sell_ids='', order_obj=None):
    invoice_number = ""
    inv_no = ""
    invoice_sequence = None
    if order_obj:
        order = order_obj
    else:
        order = None
    invoice_no_gen = MiscDetail.objects.filter(user=user.id, misc_type='increment_invoice')
    seller_order_summary_ids = []
    '''if user.userprofile.user_type == 'marketplace_user':
        seller_order_summary = SellerOrderSummary.objects.filter(seller_order__order__user=user.id,
                                                                   seller_order__order_id__in=order_ids)
        if seller_order_summary.exists():
            order_obj = seller_order_summary[0].seller_order.order
            exist_sos = SellerOrderSummary.objects.filter(seller_order__order__user=user.id,
                                                          seller_order__order__order_id=order_obj.order_id,
                                                          seller_order__order__order_code=order_obj.order_code,
                                                          seller_order__order__original_order_id=order_obj.original_order_id)
    else:
        seller_order_summary = SellerOrderSummary.objects.filter(order__id__in=order_ids)
        if seller_order_summary.exists():
            order_obj = seller_order_summary[0].order
            exist_sos = SellerOrderSummary.objects.filter(order__user=user.id,
                                                      order__order_id=order_obj.order_id,
                                                      order__order_code=order_obj.order_code,
                                                      order__original_order_id=order_obj.original_order_id)
            if not exist_sos.filter(full_invoice_number='').exists():
                return exist_sos[0].full_invoice_number, exist_sos[0].invoice_number'''

    if invoice_no_gen:
        if user.userprofile.user_type == 'marketplace_user':
            seller_order_summary = SellerOrderSummary.objects.filter(seller_order__order__user=user.id,
                                                                   seller_order__order_id__in=order_ids)
        else:
            seller_order_summary = SellerOrderSummary.objects.filter(Q(order__id__in=order_ids))
        if seller_order_summary and invoice_no_gen[0].creation_date < seller_order_summary[0].creation_date:
            check_dict = {}
            prefix_key = 'order__'
            if seller_order_summary[0].seller_order:
                order = seller_order_summary[0].seller_order.order
                prefix_key = 'seller_order__order__'
            else:
                order = seller_order_summary[0].order
            check_dict = {prefix_key + 'order_id': order.order_id, prefix_key + 'order_code': order.order_code,
                          prefix_key + 'original_order_id': order.original_order_id, prefix_key + 'user': user.id}
            if user.userprofile.user_type == 'marketplace_user':
                invoice_ins = SellerOrderSummary.objects.filter(seller_order__order__id__in=order_ids).\
                                exclude(invoice_number='')
            else:
                if sell_ids:
                    invoice_ins = SellerOrderSummary.objects.filter(**sell_ids).exclude(invoice_number='')
                else:
                    invoice_ins = SellerOrderSummary.objects.filter(order__id__in=order_ids).exclude(invoice_number='')
            #invoice_ins = exist_sos.exclude(invoice_number='')
            invoice_sequence = get_invoice_sequence_obj(user, order.marketplace)
            if invoice_ins:
                order_no = invoice_ins[0].invoice_number
                seller_order_summary.filter(invoice_number='').update(invoice_number=order_no)
                inv_no = order_no
            elif invoice_no_gen[0].misc_value == 'true':
                if invoice_sequence:
                    invoice_seq = invoice_sequence[0]
                    inv_no = int(invoice_seq.value)
                    order_no = str(inv_no).zfill(3)
                    seller_order_summary.update(invoice_number=order_no)
                    invoice_seq.value = inv_no + 1
                    invoice_seq.save()
            else:
                seller_order_summary.filter(invoice_number='').update(invoice_number=order_no)
    else:
        seller_order_summary = SellerOrderSummary.objects.filter(Q(order__id__in=order_ids) |
                                                                 Q(seller_order__order__user=user.id,
                                                                   seller_order__order_id__in=order_ids),
                                                                 full_invoice_number='')
    if sell_ids:
        invoice_update_objs1 = seller_order_summary.filter(**sell_ids)
    else:
        invoice_update_objs1 = seller_order_summary
    if invoice_update_objs1 and invoice_update_objs1[0].full_invoice_number:
        invoice_number = invoice_update_objs1[0].full_invoice_number
    else:
        invoice_number = get_full_invoice_number(user, order_no, order, invoice_date=invoice_date, pick_number='')
    if invoice_number and invoice_update_objs1:
        invoice_update_objs = invoice_update_objs1.filter(full_invoice_number='')
        if invoice_update_objs.exists():
            invoice_update_objs.update(full_invoice_number=invoice_number)
    return invoice_number, inv_no


def get_dist_auto_ord_det_ids(order_ids):
    sister_orderids_map = {}
    for ord_id in order_ids:
        ord_obj = OrderDetail.objects.get(id=ord_id)
        cm_id = CustomerMaster.objects.get(user=ord_obj.user, customer_id=ord_obj.customer_id).id
        gen_id = ord_obj.genericorderdetailmapping_set.values_list('generic_order_id')[0]
        auto_id_qty = GenericOrderDetailMapping.objects.filter(generic_order_id=gen_id[0], customer_id=cm_id). \
            exclude(orderdetail_id=ord_id).aggregate(tot_qty=Sum('quantity'))['tot_qty']
        if not auto_id_qty:
            auto_id_qty = 0
        if ord_id not in sister_orderids_map:
            sister_orderids_map[ord_id] = auto_id_qty
        else:
            sister_orderids_map[ord_id] = sister_orderids_map[ord_id] + auto_id_qty
    return sister_orderids_map



def get_mapping_imeis(user, dat, seller_summary, sor_id='', sell_ids=''):
    summary_filter = {}
    start_index = ''
    stop_index = ''
    order_seller_summary = seller_summary.filter(Q(seller_order__order_id=dat.id) | Q(order_id=dat.id))
    if sell_ids and sell_ids.get('pick_number__in'):
        summary_filter['pick_number__lt'] = int(min(sell_ids['pick_number__in']))
        start_index = order_seller_summary.filter(**summary_filter).aggregate(Sum('quantity'))['quantity__sum']
        if not start_index:
            start_index = 0
        stop_index = \
        order_seller_summary.filter(pick_number__in=sell_ids['pick_number__in']).aggregate(Sum('quantity'))[
            'quantity__sum']
        if not stop_index:
            stop_index = 0
    if sor_id :
        imeis = list(
            OrderIMEIMapping.objects.filter(sku__user=user.id, order_id=dat.id, sor_id=sor_id).order_by('creation_date'). \
            values_list('po_imei__imei_number', flat=True))
    else:
        imeis = list(
            OrderIMEIMapping.objects.filter(sku__user=user.id, order_id=dat.id).order_by('creation_date'). \
            values_list('po_imei__imei_number', flat=True))

    if start_index or stop_index:
        stop_index = int(start_index) + int(stop_index)
        imeis = imeis[int(start_index): stop_index]
    return imeis


def get_invoice_data(order_ids, user, merge_data="", is_seller_order=False, sell_ids='', pick_num = '', from_pos=False, delivery_challan='false'):
    """ Build Invoice Json Data"""
    # Initializing Default Values
    data, imei_data, customer_details = [], [], []
    order_date, order_id, marketplace, consignee, order_no, purchase_type, seller_address, customer_address, email = '', '', '', '', '', '', '', '', ''
    tax_type, seller_company, order_reference, order_reference_date = '', '', '', ''
    invoice_header = ''
    total_quantity, total_amt, total_taxable_amt, total_invoice, total_tax, total_mrp, _total_tax = 0, 0, 0, 0, 0, 0, 0
    taxable_cal = 0.0
    total_taxes = {'cgst_amt': 0, 'sgst_amt': 0, 'igst_amt': 0, 'utgst_amt': 0, 'cess_amt': 0}
    hsn_summary = {}
    partial_order_quantity_price = 0
    order_charges_percent =1
    is_gst_invoice = False
    invoice_date = ''
    order_reference_date_field = ''
    order_charges = {}
    total_order_quantity_price = 0
    customer_id = ''
    mode_of_transport = ''
    vehicle_number = ''
    invoice_reference = ''
    advance_amount = 0
    admin_user = get_admin(user)
    # Getting the values from database
    user_profile = UserProfile.objects.get(user_id=user.id)
    gstin_no = user_profile.gst_number
    pan_number = user_profile.pan_number
    cin_no = user_profile.cin_number
    display_customer_sku = get_misc_value('display_customer_sku', user.id)
    show_imei_invoice = get_misc_value('show_imei_invoice', user.id)
    invoice_remarks = get_misc_value('invoice_remarks', user.id)
    invoice_declaration = get_misc_value('invoice_declaration', user.id)
    show_disc_invoice = get_misc_value('show_disc_invoice', user.id)
    show_mrp = get_misc_value('show_mrp', user.id)
    show_sno = get_misc_value('sno_in_invoice',user.id)
    is_sample_option =  get_misc_value('create_order_po', user.id)
    count = 0

    if len(invoice_remarks.split("<<>>")) > 1:
        invoice_remarks = invoice_remarks.split("<<>>")
        invoice_remarks = "\n".join(invoice_remarks)

    if len(invoice_declaration.split("<<>>")) > 1:
        invoice_declaration = invoice_declaration.split("<<>>")
        invoice_declaration = "\n".join(invoice_declaration)

    if display_customer_sku == 'true':
        customer_sku_codes = CustomerSKU.objects.filter(sku__user=user.id).exclude(customer_sku_code='').values(
            'sku__sku_code',
            'customer__customer_id', 'customer_sku_code')
    else:
        customer_sku_codes = ''
    if order_ids:
        sor_id = ''
        order_ids = list(set(order_ids.split(',')))
        order_data = OrderDetail.objects.filter(id__in=order_ids).select_related('sku')
        if user.userprofile.user_type == 'marketplace_user':
            seller_summary = SellerOrderSummary.objects.filter(seller_order__order_id__in=order_ids)
            invoice_date = seller_summary[0].creation_date
        else:
            seller_summary = SellerOrderSummary.objects.filter(order_id__in=order_ids)
            invoice_date = seller_summary[0].creation_date
        if seller_summary.exists():
            invoice_reference = seller_summary[0].invoice_reference
            if seller_summary[0].seller_order:
                seller = seller_summary[0].seller_order.seller
                sor_id = seller_summary[0].seller_order.sor_id
                seller_company = seller.name
                seller_address = seller.name + '\n' + seller.address + "\nCall: " \
                                 + seller.phone_number + "\nEmail: " + seller.email_id \
                                 + "\nGSTIN No: " + seller.tin_number
        if order_data and order_data[0].customer_id:
            dat = order_data[0]
            gen_ord_customer_id = order_data[0].genericorderdetailmapping_set.values_list('customer_id', flat=True)
            if gen_ord_customer_id and user.userprofile.warehouse_type == 'DIST':
                customer_details = list(CustomerMaster.objects.filter(id=gen_ord_customer_id[0]).
                                        values('id', 'customer_id', 'name', 'email_id', 'tin_number', 'address', 'shipping_address',
                                               'credit_period', 'phone_number','pan_number'))
            else:
                customer_details = list(CustomerMaster.objects.filter(user=user.id, customer_id=dat.customer_id).
                                        values('id', 'customer_id', 'name', 'email_id', 'tin_number', 'address', 'shipping_address',
                                               'credit_period', 'phone_number','pan_number'))
            if customer_details:
                customer_id = customer_details[0]['id']
                customer_address = customer_details[0]['name'] + '\n' + customer_details[0]['address']
                if customer_details[0]['tin_number']:
                    customer_address += ("\nGSTIN No: " + customer_details[0]['tin_number'])
                if customer_details[0]['phone_number']:
                    customer_address += ("\nCall: " + customer_details[0]['phone_number'])
                if customer_details[0]['email_id']:
                    customer_address += ("\tEmail: " + customer_details[0]['email_id'])
                if customer_details[0]['pan_number']:
                    customer_address += ("\tPAN No.: " + customer_details[0]['pan_number'])
                if customer_details[0]['shipping_address']:
                    consignee = customer_details[0]['shipping_address']
                else:
                    consignee = customer_address
            else:
                customer_id = dat.customer_id
                customer_address = dat.customer_name + '\n' + dat.address + "\nCall: " \
                                   + str(dat.telephone) + "\nEmail: " + str(dat.email_id)
        if not customer_address:
            dat = order_data[0]
            customer_address = dat.customer_name + '\n' + dat.address + "\nCall: " \
                               + dat.telephone + "\nEmail: " + dat.email_id
        if not customer_details and dat.address:
            customer_details.append({'id' : dat.customer_id, 'name' : dat.customer_name, 'address' : dat.address})
        if admin_user.username.lower() == 'gomechanic_admin':
            customer_details[0]['id'] = dat.customer_id
            customer_details[0]['name'] = dat.customer_name
            customer_details[0]['address']= dat.address
            customer_details[0]['email_id'] = dat.email_id
            customer_details[0]['phone_number'] = dat.telephone

        picklist = Picklist.objects.filter(order_id__in=order_ids).order_by('-updation_date')
        if not invoice_date and picklist:
            invoice_date = picklist[0].updation_date
        invoice_date = get_local_date(user, invoice_date, send_date='true')

        if datetime.datetime.strptime('2017-07-01', '%Y-%m-%d').date() <= invoice_date.date():
            is_gst_invoice = True

        for dat in order_data:
            count += 1
            profit_price,marginal_flag = 0, 0
            order_id = dat.original_order_id
            advance_amount += dat.payment_received
            gen_ord_num = GenericOrderDetailMapping.objects.filter(orderdetail_id=order_data[0].id)
            if gen_ord_num and user.userprofile.warehouse_type == 'DIST':
                order_no = str(gen_ord_num[0].generic_order_id)
                order_id = dat.order_code + order_no
            else:
                order_no = str(dat.order_id)
            shipment_date = ''
            if dat.shipment_date:
                shipment_date = dat.shipment_date.strftime('%Y-%m-%d %H:%M')
            order_reference = dat.order_reference
            order_reference_date = ''
            order_reference_date_field = ''
            if dat.order_reference_date:
                order_reference_date_field = dat.order_reference_date.strftime("%m/%d/%Y")
                order_reference_date = dat.order_reference_date.strftime("%d %b %Y")
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

            if not marketplace:
                marketplace = dat.marketplace
                username = user.username + ':' + marketplace.lower()
                if 'bays' in (dat.original_order_id).lower():
                    username = username + ':bulk'
                    purchase_type = 'SMART_JIT'

                marketplace = USER_CHANNEL_ADDRESS.get(username, marketplace)
            if not marketplace:
                marketplace = 'offline'
            tax = 0
            vat = 0
            discount = 0
            el_price = 0
            cgst_tax, sgst_tax, igst_tax, utgst_tax, cess_tax = 0, 0, 0, 0, 0
            mrp_price = dat.sku.mrp
            taxes_dict = {}
            tax_type, invoice_header, vehicle_number, mode_of_transport = '', '', 0, ''
            order_summary = CustomerOrderSummary.objects.filter(order_id=dat.id)
            if order_summary:
                tax = order_summary[0].tax_value
                vat = order_summary[0].vat
                mrp_price = order_summary[0].mrp
                discount = order_summary[0].discount
                tax_type = order_summary[0].tax_type
                cgst_tax = order_summary[0].cgst_tax
                sgst_tax = order_summary[0].sgst_tax
                igst_tax = order_summary[0].igst_tax
                utgst_tax = order_summary[0].utgst_tax
                cess_tax = order_summary[0].cess_tax
                invoice_header = order_summary[0].invoice_type
                mode_of_transport = order_summary[0].mode_of_transport
                vehicle_number = order_summary[0].vehicle_number
                if order_summary[0].invoice_date and get_misc_value('customer_dc', user.id) != 'true':
                    invoice_date = order_summary[0].invoice_date
            total_tax += float(tax)
            total_mrp += float(mrp_price)
            picklist = Picklist.objects.exclude(order_type='combo').filter(order_id=dat.id). \
                aggregate(Sum('picked_quantity'))['picked_quantity__sum']
            quantity = picklist
            el_price_qs = GenericOrderDetailMapping.objects.filter(orderdetail_id=dat.id).values_list('el_price',
                                                                                                      flat=True)
            if el_price_qs:
                el_price = round(el_price_qs[0], 2)

            if merge_data and user.userprofile.warehouse_type != 'DIST':
                quantity_picked = merge_data.get(dat.sku.sku_code, "")
                if quantity_picked:
                    quantity = float(quantity_picked)
                else:
                    continue

            if not picklist and not is_seller_order:
                picklist = Picklist.objects.filter(order_id=dat.id, order_type='combo', picked_quantity__gt=0). \
                    annotate(total=Sum('picked_quantity'))
                if picklist:
                    quantity = picklist[0].total
            if dat.unit_price > 0:
                unit_price = dat.unit_price
            else:
                unit_price = (float(dat.invoice_amount) / float(dat.quantity)) - (tax / float(dat.quantity))
            if el_price:
                unit_price = el_price
            if dat.sku.sku_code:
                sku_attr_obj = SKUAttributes.objects.filter(sku_id=dat.sku_id,
                                        attribute_name='MARGINAL GST').only('attribute_value')
                imei_data_sku_wise = []
                if sku_attr_obj.exists() and sku_attr_obj[0].attribute_value.upper() == 'YES':
                    marginal_flag = 1
                    if pick_num:
                        cost_price_obj = seller_summary.filter(order_id = dat.id, pick_number__in = pick_num).values('picklist__stock__unit_price', 'quantity')
                    else:
                        cost_price_obj = seller_summary.filter(order_id = dat.id).values('picklist__stock__unit_price', 'quantity')
                    for index,margin_cost_price_obj in enumerate(cost_price_obj):
                        cost_price = margin_cost_price_obj['picklist__stock__unit_price']
                        quantity = margin_cost_price_obj['quantity']
                        profit_price = (unit_price * quantity) - (cost_price * quantity)
                        seller_summary_obj_sku_wise = seller_summary.filter(order__sku_id = dat.sku_id)
                        seller_id_value = seller_summary_obj_sku_wise[index].id
                        # seller_id_value = seller_summary[index].id
                        if pick_num:
                            seller_summary_imei = seller_summary.filter(order_id = dat.id, pick_number__in = pick_num, id= seller_id_value)
                        else:
                            seller_summary_imei = seller_summary.filter(order_id = dat.id, id= seller_id_value)
                        if profit_price < 1:
                            cgst_tax,sgst_tax,igst_tax,utgst_tax = 0, 0 ,0, 0

                        arg_data = {'unit_price':unit_price,'quantity':quantity,'discount':discount,'dat':dat,'is_gst_invoice':is_gst_invoice,'marginal_flag':marginal_flag,
                                    'cgst_tax':cgst_tax,'sgst_tax':sgst_tax,'igst_tax':igst_tax,'utgst_tax':utgst_tax,'cess_tax':cess_tax,'profit_price':profit_price,'hsn_summary':hsn_summary,
                                    'total_quantity':total_quantity,'partial_order_quantity_price':partial_order_quantity_price,'_total_tax':_total_tax,
                                    'total_invoice':total_invoice,'total_taxable_amt':total_taxable_amt,'display_customer_sku':display_customer_sku,'customer_sku_codes':customer_sku_codes,
                                    'user':user,'sor_id':sor_id,'sell_ids':sell_ids,'seller_summary':seller_summary,'data':data,'order_id':order_id,'title':title,'tax_type':tax_type,'vat':vat,'mrp_price':mrp_price,
                                    'shipment_date':shipment_date,'count':count,'total_taxes':total_taxes,'imei_data':imei_data,'taxable_cal':taxable_cal, 'taxes_dict':taxes_dict, 'seller_summary_imei':seller_summary_imei, 'imei_data_sku_wise':imei_data_sku_wise}
                        data,total_invoice,_total_tax,total_taxable_amt,taxable_cal,total_quantity, partial_order_quantity_price = common_calculations(arg_data)

                else:
                    arg_data = {'unit_price':unit_price,'quantity':quantity,'discount':discount,'dat':dat,'is_gst_invoice':is_gst_invoice,'marginal_flag':marginal_flag,
                                        'cgst_tax':cgst_tax,'sgst_tax':sgst_tax,'igst_tax':igst_tax,'utgst_tax':utgst_tax,'cess_tax':cess_tax,'profit_price':profit_price,'hsn_summary':hsn_summary,
                                        'total_quantity':total_quantity,'partial_order_quantity_price':partial_order_quantity_price,'_total_tax':_total_tax,
                                        'total_invoice':total_invoice,'total_taxable_amt':total_taxable_amt,'display_customer_sku':display_customer_sku,'customer_sku_codes':customer_sku_codes,
                                        'user':user,'sor_id':sor_id,'sell_ids':sell_ids,'seller_summary':seller_summary,'data':data,'order_id':order_id,'title':title,'tax_type':tax_type,'vat':vat,'mrp_price':mrp_price,
                                        'shipment_date':shipment_date,'count':count,'total_taxes':total_taxes,'imei_data':imei_data,'taxable_cal':taxable_cal,'taxes_dict':taxes_dict, 'seller_summary_imei':'','imei_data_sku_wise':imei_data_sku_wise}
                    data,total_invoice,_total_tax,total_taxable_amt,taxable_cal,total_quantity, partial_order_quantity_price = common_calculations(arg_data)

    is_cess_tax_flag = 'true'
    for ord_dict in data:
        if ord_dict['taxes'].get('cess_tax', 0):
            break
    else:
        is_cess_tax_flag = 'false'

    if is_cess_tax_flag == 'false':
        for ord_dict in data:
            if 'cess_tax' in ord_dict:
                ord_dict.pop('cess_tax')
            if 'cess_amt' in ord_dict:
                ord_dict.pop('cess_amt')

    is_igst_tax_flag = 'true'
    for ord_dict in data:
        if ord_dict['taxes'].get('igst_tax', 0):
            break
    else:
        is_igst_tax_flag = 'false'

    if is_igst_tax_flag == 'false':
        for ord_dict in data:
            if 'igst_tax' in ord_dict:
                ord_dict.pop('igst_tax')
            if 'igst_amt' in ord_dict:
                ord_dict.pop('igst_amt')
    _invoice_no = ''
    _sequence = ''
    if delivery_challan != 'true':
        _invoice_no, _sequence = get_invoice_number(user, order_no, invoice_date, order_ids, user_profile, from_pos, sell_ids, order_obj=dat)
    challan_no, challan_sequence = get_challan_number(user, seller_summary)
    inv_date = invoice_date.strftime("%m/%d/%Y")
    invoice_date = invoice_date.strftime("%d %b %Y")
    order_charges = {}

    #create order extra fileds
    extra_fields ={}
    extra_order_fields = get_misc_value('extra_order_fields', user.id)
    if extra_order_fields == 'false' :
        extra_order_fields = []
    else:
        extra_order_fields = extra_order_fields.split(',')
    for extra in extra_order_fields :
        order_field_obj = OrderFields.objects.filter(original_order_id=order_id,user=user.id ,name = extra)
        if order_field_obj.exists():
            extra_fields[order_field_obj[0].name] = order_field_obj[0].value

    total_invoice_amount = total_invoice
    if order_id:
        order_charge_obj = OrderCharges.objects.filter(user_id=user.id, order_id=order_id)
        if order_charge_obj.exists():
            total_order_qtys = OrderDetail.objects.filter(original_order_id = order_id,user = user.id ).values('sku__wms_code').annotate(total=F('quantity') * F('unit_price'))
            for quantity in total_order_qtys :
                total_order_quantity_price += quantity.get('total' ,0)

        order_charges = list(order_charge_obj.values('charge_name', 'charge_amount', 'charge_tax_value','id'))
        if total_order_quantity_price :
            order_charges_percent = (partial_order_quantity_price / total_order_quantity_price)
        invoice_order_charge = ''
        full_order_charge = True
        if order_charges_percent != 1 and sell_ids :
            if sell_ids.get('pick_number__in',0) :
                pick_num = sell_ids.get('pick_number__in')[0]
                invoice_order_charge = InvoiceOrderCharges.objects.filter(original_order_id = order_id , pick_number = pick_num,user = user.id)
                if invoice_order_charge.exists():
                    order_charges = list(invoice_order_charge.values('charge_name', 'charge_amount', 'charge_tax_value','id'))
                    full_order_charge = False
                    for order_chrg in order_charges :
                        total_invoice_amount += order_chrg['charge_amount']+order_chrg['charge_tax_value']
                        order_chrg['charge_amount'] = round(order_chrg['charge_amount'], 2)
                        order_chrg['charge_tax_value'] = round(order_chrg['charge_tax_value'], 2)
        if full_order_charge :
            for order_chrg in order_charges :
                order_chrg['charge_amount'] = order_charges_percent * order_chrg['charge_amount']
                order_chrg['charge_tax_value'] = order_charges_percent * order_chrg['charge_tax_value']
                total_invoice_amount += order_chrg['charge_amount']+order_chrg['charge_tax_value']
                order_chrg['charge_amount'] = round(order_chrg['charge_amount'], 2)
                order_chrg['charge_tax_value'] = round(order_chrg['charge_tax_value'], 2)


    total_amt = "%.2f" % (float(total_invoice) - float(_total_tax))
    dispatch_through = "By Road"
    _total_invoice = round(total_invoice_amount)
    admin_user = get_admin(user)
    if admin_user.get_username() .lower()== '72Networks'.lower() :
        side_image = get_company_logo(admin_user, COMPANY_LOGO_PATHS)
    else:
        side_image = get_company_logo(user, COMPANY_LOGO_PATHS)
    top_image = get_company_logo(user, TOP_COMPANY_LOGO_PATHS)

    declaration = DECLARATIONS.get(user.username, '')
    if not declaration:
        declaration = DECLARATIONS['default']
    company_name = user_profile.company_name
    company_address = user_profile.address
    company_number = user_profile.phone_number
    email = user.email

    if seller_address:
        company_address = seller.address
        email = seller.email_id
        gstin_no = seller.tin_number
        company_address = company_address.replace("\n", " ")
        company_name = seller.name #'SHPROC Procurement Pvt. Ltd.'
    if math.ceil(total_quantity) == total_quantity:
        total_quantity = int(total_quantity)
    dc_terms_conditions = ''
    terms_condition = UserTextFields.objects.filter(user=user.id, field_type = 'dc_terms_conditions')
    if terms_condition.exists():
        dc_terms_conditions = terms_condition[0].text_field.replace('<<>>', '\n')
    invoice_data = {'data': data, 'imei_data': imei_data, 'company_name': company_name,'company_pan_number':pan_number,
                    'company_address': company_address, 'company_number': company_number,
                    'order_date': order_date, 'email': email, 'marketplace': marketplace, 'total_amt': total_amt,
                    'total_quantity': total_quantity, 'total_invoice': "%.2f" % total_invoice, 'order_id': order_id,
                    'customer_details': customer_details, 'order_no': order_no, 'total_tax': "%.2f" % _total_tax,
                    'total_mrp': total_mrp,'extra_fields':extra_fields,
                    'invoice_no': _invoice_no, 'invoice_date': invoice_date,
                    'price_in_words': number_in_words(_total_invoice),
                    'order_charges': order_charges, 'total_invoice_amount': "%.2f" % total_invoice_amount,
                    'consignee': consignee,
                    'invoice_reference': invoice_reference,
                    'dispatch_through': dispatch_through, 'inv_date': inv_date, 'tax_type': tax_type,
                    'rounded_invoice_amount': _total_invoice, 'purchase_type': purchase_type,
                    'is_gst_invoice': is_gst_invoice,
                    'gstin_no': gstin_no, 'total_taxable_amt': total_taxable_amt, 'total_taxes': total_taxes,
                    'side_image': side_image,
                    'top_image' : top_image,
                    'total_tax_words': number_in_words(_total_tax), 'declaration': declaration,
                    'hsn_summary': hsn_summary,
                    'hsn_summary_display': get_misc_value('hsn_summary', user.id), 'seller_address': seller_address,
                    'customer_address': customer_address, 'invoice_remarks': invoice_remarks,
                    'invoice_declaration':invoice_declaration,
                    'show_disc_invoice': show_disc_invoice,
                    'show_sno':show_sno,
                    'seller_company': seller_company, 'sequence_number': _sequence, 'order_reference': order_reference,
                    'order_reference_date_field': order_reference_date_field,
                    'order_reference_date': order_reference_date, 'invoice_header': invoice_header,
                    'cin_no': cin_no, 'challan_no': challan_no, 'customer_id': customer_id,'challan_sequence':challan_sequence,
                    'show_mrp': show_mrp, 'mode_of_transport' : mode_of_transport, 'vehicle_number' : vehicle_number,
                    'is_cess_tax_flag': is_cess_tax_flag, 'is_igst_tax_flag': is_igst_tax_flag, 'advance_amount':str(advance_amount), 'terms_condition': dc_terms_conditions}
    return invoice_data

def common_calculations(arg_data):
    for key,val in arg_data.items():
        exec(key + '=val')
    order_discount = discount
    unit_discount = float(order_discount)/dat.original_quantity
    discount = unit_discount * quantity
    amt = (unit_price * quantity) - discount
    base_price = "%.2f" % (unit_price * quantity)
    hsn_code = ''
    if dat.sku.hsn_code:
        hsn_code = dat.sku.hsn_code

    if is_gst_invoice:
        if marginal_flag:
            cess_amt = 0
            marginal_tax = cgst_tax + sgst_tax + igst_tax + utgst_tax
            tax_amount = (profit_price * marginal_tax)/(100 + marginal_tax)
            taxable_amt = profit_price - tax_amount
            if cgst_tax:
                cgst_amt = tax_amount/2
                sgst_amt = tax_amount/2
                igst_amt, utgst_amt = 0, 0
            elif igst_tax:
                igst_amt = tax_amount
                cgst_amt, sgst_amt, utgst_amt = 0, 0, 0
            elif utgst_tax:
                utgst_amt = tax_amount
                cgst_amt, sgst_amt, igst_amt = 0, 0, 0
            else :
                cgst_amt,sgst_amt,igst_amt,utgst_amt = 0, 0 ,0, 0

        else:
            cgst_amt = float(cgst_tax) * (float(amt) / 100)
            sgst_amt = float(sgst_tax) * (float(amt) / 100)
            igst_amt = float(igst_tax) * (float(amt) / 100)
            utgst_amt = float(utgst_tax) * (float(amt) / 100)
            cess_amt = float(cess_tax) * (float(amt) / 100)
        taxes_dict = {'cgst_tax': cgst_tax, 'sgst_tax': sgst_tax, 'igst_tax': igst_tax, 'utgst_tax': utgst_tax,
                      'cess_tax': cess_tax, 'cgst_amt': '%.2f' % cgst_amt, 'sgst_amt': '%.2f' % sgst_amt,
                      'igst_amt': '%.2f' % igst_amt,
                      'utgst_amt': '%.2f' % utgst_amt, 'cess_amt': '%.2f' % cess_amt}
        total_taxes['cgst_amt'] += float(taxes_dict['cgst_amt'])
        total_taxes['sgst_amt'] += float(taxes_dict['sgst_amt'])
        total_taxes['igst_amt'] += float(taxes_dict['igst_amt'])
        total_taxes['utgst_amt'] += float(taxes_dict['utgst_amt'])
        total_taxes['cess_amt'] += float(taxes_dict['cess_amt'])
        _tax = float(taxes_dict['cgst_amt']) + float(taxes_dict['sgst_amt']) + float(taxes_dict['igst_amt']) + \
               float(taxes_dict['utgst_amt']) + float(taxes_dict['cess_amt'])
        summary_key = str(hsn_code) + "@" + str(cgst_tax + sgst_tax + igst_tax + utgst_tax+cess_tax)
        if hsn_summary.get(summary_key, ''):
            hsn_summary[summary_key]['taxable'] += float("%.2f" % float(amt))
            hsn_summary[summary_key]['sgst_amt'] += float("%.2f" % float(sgst_amt))
            hsn_summary[summary_key]['cgst_amt'] += float("%.2f" % float(cgst_amt))
            hsn_summary[summary_key]['igst_amt'] += float("%.2f" % float(igst_amt))
            hsn_summary[summary_key]['utgst_amt'] += float("%.2f" % float(utgst_amt))
            hsn_summary[summary_key]['cess_amt'] += float("%.2f" % float(cess_amt))
        else:
            hsn_summary[summary_key] = {}
            hsn_summary[summary_key]['taxable'] = float("%.2f" % float(amt))
            hsn_summary[summary_key]['sgst_amt'] = float("%.2f" % float(sgst_amt))
            hsn_summary[summary_key]['cgst_amt'] = float("%.2f" % float(cgst_amt))
            hsn_summary[summary_key]['igst_amt'] = float("%.2f" % float(igst_amt))
            hsn_summary[summary_key]['utgst_amt'] = float("%.2f" % float(utgst_amt))
            hsn_summary[summary_key]['cess_amt'] = float("%.2f" % float(cess_amt))
    else:
        _tax = (amt * (vat / 100))

    discount_percentage = 0
    if (quantity * unit_price):
        discount_percentage = "%.1f" % (float((discount * 100) / (quantity * unit_price)))
    unit_price = "%.2f" % unit_price
    total_quantity += quantity
    partial_order_quantity_price += (float(unit_price) * float(quantity))
    _total_tax += _tax
    invoice_amount = _tax + amt
    total_invoice += _tax + amt
    total_taxable_amt += amt
    if marginal_flag:
        total_invoice = total_invoice - tax_amount
        amt  = '%.2f'% taxable_amt if taxable_amt >= 0 else 0
        invoice_amount = invoice_amount - tax_amount
        taxable_cal = taxable_cal + float(amt)
        total_taxable_amt = taxable_cal
    sku_code = dat.sku.sku_code
    sku_desc = dat.sku.sku_desc
    measurement_type = dat.sku.measurement_type
    if display_customer_sku == 'true':
        customer_sku_code_ins = customer_sku_codes.filter(customer__customer_id=dat.customer_id,
                                                          sku__sku_code=sku_code)
        if customer_sku_code_ins:
            sku_code = customer_sku_code_ins[0]['customer_sku_code']

    temp_imeis = []
    if seller_summary_imei:
        # temp_imeis = get_mapping_imeis(user, dat, seller_summary_imei, sor_id, sell_ids=sell_ids)
        imeis = list(
            OrderIMEIMapping.objects.filter(sku__user=user.id, order_id=dat.id).order_by('creation_date'). \
            values_list('po_imei__imei_number', flat=True))
        if seller_summary_imei[0].quantity == len(imeis):
            temp_imeis.extend(imeis)
        else:
            stop_index = int(seller_summary_imei[0].quantity)
            for del_item in imei_data_sku_wise:
                if del_item in imeis:
                    imeis.remove(del_item)
            imei_details = imeis[0 : stop_index]
            temp_imeis.extend(imei_details)
    else:
        temp_imeis = get_mapping_imeis(user, dat, seller_summary, sor_id, sell_ids=sell_ids)
    imei_data.append(temp_imeis)
    imei_data_sku_wise.extend(temp_imeis)
    # if sku_code in [x['sku_code'] for x in data]:
    #     continue
    if math.ceil(quantity) == quantity:
        quantity = int(quantity)
    quantity = get_decimal_limit(user.id ,quantity)
    invoice_amount = get_decimal_limit(user.id ,invoice_amount ,'price')
    data.append(
        {'order_id': order_id, 'sku_code': sku_code, 'sku_desc': sku_desc,
         'title': title, 'invoice_amount': str(invoice_amount),
         'quantity': quantity, 'tax': "%.2f" % _tax, 'unit_price': unit_price, 'tax_type': tax_type,
         'vat': vat, 'mrp_price': mrp_price, 'discount': discount, 'sku_class': dat.sku.sku_class,
         'sku_category': dat.sku.sku_category, 'sku_size': dat.sku.sku_size, 'amt':amt, 'taxes': taxes_dict,
         'base_price': base_price, 'hsn_code': hsn_code, 'imeis': temp_imeis,
         'discount_percentage': discount_percentage, 'id': dat.id, 'shipment_date': shipment_date,'sno':count,
         'measurement_type': measurement_type})
    return data,total_invoice,_total_tax,total_taxable_amt,taxable_cal,total_quantity, partial_order_quantity_price


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

    categories = list(
        sku_master.exclude(sku_category='').filter(**filter_params).only('sku_category').values_list('sku_category', flat=True).distinct())
    brands = list(sku_master.exclude(sku_brand='').only('sku_brand').values_list('sku_brand', flat=True).distinct())
    sizes = list(sku_master.exclude(sku_brand='').only('sku_size').values_list('sku_size', flat=True).order_by('sequence').distinct())
    sizes = list(OrderedDict.fromkeys(sizes))
    colors = list(sku_master.exclude(sku_brand='').exclude(color='').only('color').values_list('color', flat=True).distinct())

    primary_details = {'data': {}}
    primary_details['primary_categories'] = list(sku_master.exclude(primary_category='').filter(**filter_params). \
                                                 only('primary_category').values_list('primary_category', flat=True).\
                                                 distinct())
    primary_details['sub_category_list'] = {}
    for primary in primary_details['primary_categories']:
        primary_filtered = sku_master.exclude(sku_category='').filter(primary_category=primary).only('sku_category').\
                                    values_list('sku_category', flat=True).distinct()
        primary_details['data'][primary] = list(primary_filtered)
        for primary_filt in primary_filtered:
            primary_details['sub_category_list'][primary_filt] = list(sku_master.\
                                            filter(sku_category=primary_filt).exclude(sub_category=''). \
                                            only('sub_category').values_list('sub_category', flat=True).distinct())
    _sizes = {}
    integer = []
    character = []
    categories_details = {}
    for category in categories:
        categories_details[category] = ""
        if user.username == 'sagar_fab' and category == 'Gents Polo':
            category = sku_master.filter(sku_category=category).order_by('sequence')
        else:
            category = sku_master.filter(sku_category=category)
        if category:
            category = category[0]
            if category.image_url:
                categories_details[category.sku_category] = resize_image(category.image_url, user)

    for size in sizes:
        try:
            integer.append(int(eval(size)))
        except:
            character.append(size)
    _sizes = {'type2': integer, 'type1': character}
    category_data = {'categories_details': categories_details, 'primary_details': primary_details}
    return brands, sorted(categories), _sizes, colors, category_data


def get_sku_available_stock(user, sku_masters, query_string, size_dict):
    selected_sizes = [i for i in size_dict if size_dict[i] not in ["", 0]]
    classes = list(sku_masters.values_list('sku_class', flat=True).distinct())
    stock_objs = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values(query_string).distinct(). \
        annotate(in_stock=Sum('quantity'))
    stock_query = "stock__%s" % (query_string)
    reserved_quantities = PicklistLocation.objects.filter(stock__sku__user=user.id, status=1).values(
        stock_query).distinct(). \
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
        sizes_exist = sku_masters.filter(sku_class=_class).values_list('sku_size', flat=True)
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
    try:
        path = 'static/images/resized/'
        folder = str(user.id)

        height = 193
        width = 258

        if url:
            new_file_name = url.split("/")[-1].split(".")[0] + "-" + str(width) + "x" + str(height) + "." + url.split(".")[
                1]
            file_name = url.split(".")
            file_name = "%s-%sx%s.%s" % (file_name[0], width, height, file_name[1])

            if not os.path.exists(path + folder):
                os.makedirs(path + folder)

            # if os.path.exists(path+folder+"/"+new_file_name):
            #    return "/"+path+folder+"/"+new_file_name;

            try:
                from PIL import Image
                temp_url = url[1:]
                image = Image.open(temp_url)
                if image.size[0] == image.size[1]:
                    height = width = 250
                imageresize = image.resize((height, width), Image.ANTIALIAS)
                imageresize.save(path + folder + "/" + new_file_name, 'JPEG', quality=75)
                url = "/" + path + folder + "/" + new_file_name
                return url
            except:
                import traceback
                log.debug(traceback.format_exc())
                log.info('Issue for ' + url)
                return url
        else:
            return url
    except:
        return ''


def get_sku_catalogs_data(request, user, request_data={}, is_catalog=''):
    if not request_data:
        request_data = request.POST
    filter_params = {'user': user.id}
    sku_class = request_data.get('sku_class', '')
    cluster = request_data.get('cluster', '')
    sku_brand = request_data.get('brand', '')
    sku_category = request_data.get('category', '')
    sub_category = request_data.get('sub_category', '')
    from_price = request_data.get('from_price', '')
    to_price = request_data.get('to_price', '')
    color = request_data.get('color', '')
    custom_margin = request_data.get('margin', 0)
    hot_release = request_data.get('hot_release', '')
    quantity = request_data.get('quantity', 0)
    delivery_date = request_data.get('delivery_date', '')
    dimensions = request_data.get('dimensions', {})
    brand_categorization_exclude = request_data.get('brand_categorization', '')
    brand_categorization = get_misc_value('brand_categorization', user.id)
    customer_master = None
    if not quantity:
        quantity = 0
    try:
        custom_margin = float(custom_margin)
    except:
        custom_margin = 0
    admin_user = get_priceband_admin_user(user)
    msp_min_price = msp_max_price = 0
    if admin_user and from_price and to_price:
        msp_min_price = from_price
        msp_max_price = to_price
        from_price = to_price = ''
    is_margin_percentage = request_data.get('is_margin_percentage', 'false')
    specific_margins = request_data.get('margin_data', [])
    customer_data_id = request_data.get('customer_data_id', '')
    price_type = ''
    customer_id = ''
    disp_sku_map = get_misc_value('display_sku_cust_mapping', user.id)
    if disp_sku_map == 'true':
        cust_mapped_skus = CustomerSKU.objects.filter(sku__user=user.id).values_list('sku_id', flat=True)
        filtered_sku_master = SKUMaster.objects.exclude(sku_class='').filter(id__in=cust_mapped_skus)
    else:
        cust_mapped_skus = []
        filtered_sku_master = SKUMaster.objects.exclude(sku_class='')

    price_field = get_price_field(user)
    customer_master, price_type, customer_data_id, customer_id = get_customer_and_price_type(request, user, customer_data_id, customer_id)
    if not is_catalog:
        is_catalog = request_data.get('is_catalog', '')

    customer_id = ''
    indexes = request_data.get('index', '0:20')
    is_file = request_data.get('file', '')
    sale_through = request_data.get('sale_through', '')

    filter_params1 = {}
    if not indexes:
        indexes = '0:20'
    if sku_brand:
        filter_params['sku_brand__in'] = [i.strip() for i in sku_brand.split(",") if i]
        filter_params1['sku__sku_brand__in'] = filter_params['sku_brand__in']
    if sku_category and sku_category.lower() != 'all':
        filter_params['sku_category__in'] = [i.strip() for i in sku_category.split(",") if i]
        filter_params1['sku__sku_category__in'] = filter_params['sku_category__in']
    if sub_category and sub_category.lower() != 'all':
        filter_params['sub_category__in'] = [i.strip() for i in sub_category.split(",") if i]
        filter_params1['sku__sub_category__in'] = filter_params['sub_category__in']
    if is_catalog:
        filter_params['status'] = 1
        filter_params1['sku__status'] = 1
    if color:
        filter_params['color__in'] = [i.strip() for i in color.split(",") if i]
        filter_params1['sku__color__in'] = filter_params['color__in']
    if sale_through:
        filter_params['sale_through__iexact'] = sale_through
        filter_params1['sku__sale_through__iexact'] = sale_through
    if from_price:
        filter_params['new_price__gte'] = from_price
        filter_params1['new_price__gte'] = from_price
    if to_price:
        filter_params['new_price__lte'] = to_price
        filter_params1['new_price__lte'] = to_price
    if hot_release == 'true':
        hot_release_data = SKUFields.objects.filter(sku__user=user.id, field_type='hot_release',
                                                    field_value='1').values_list('sku_id', flat=True)
        filter_params['id__in'] = hot_release_data
        filter_params1['id__in'] = hot_release_data
    start, stop = indexes.split(':')
    start, stop = int(start), int(stop)
    if brand_categorization == 'true' and brand_categorization_exclude != 'true':
        sku_brand_list, sku_class_list = [], []
        sku_brands = SKUMaster.objects.filter(user=user.id, sku_category=sku_category, status = 1).values_list('sku_brand', flat=True).distinct()
        for sku_brand in sku_brands:
            sku_class_list.extend(list(SKUMaster.objects.filter(user=user.id, sku_category=sku_category, sku_brand=sku_brand, status = 1).distinct().values_list('sku_class', flat=True)[:5]))
        sku_brand_list.extend(list(SKUMaster.objects.filter(user=user.id, sku_category=sku_category, sku_class__in=sku_class_list, status = 1).values_list('id', flat=True)))
        if sku_brand_list:
            filter_params.setdefault('id__in',[])
            filter_params1.setdefault('id__in',[])
            filter_params['id__in'] = list(chain(filter_params['id__in'], sku_brand_list))
            filter_params1['id__in'] = list(chain(filter_params1['id__in'], sku_brand_list))
            start, stop = 0, len(sku_brand_list)
    skumaster_qs = SKUMaster.objects.exclude(sku_class='')
    if admin_user:
        filter_params1['sku__user'] = admin_user.id
    else:
        filter_params1['sku__user'] = user.id
    if cluster:
        cluster_sku_list = list(ClusterSkuMapping.objects.filter(cluster_name = cluster, sku__user = filter_params1['sku__user']).values_list('sku__sku_code', flat=True))
        filter_params['sku_code__in'] = cluster_sku_list
        filter_params1['sku__sku_code__in'] = cluster_sku_list
    if sku_class:
        filter_params['sku_class__icontains'] = sku_class
        filter_params1['sku__sku_class__icontains'] = sku_class
    if dimensions:
        dimensions = eval(dimensions)
        if "from_Length" in dimensions:
            if dimensions["from_Length"]:
                from_length = int(dimensions["from_Length"])
                skumaster_qs = skumaster_qs.filter(user=user.id).\
                    filter(Q(skuattributes__attribute_name='length')&
                           Q(skuattributes__attribute_value__gte=Value(from_length)))
        if "to_Length" in dimensions:
            if dimensions["to_Length"]:
                to_length = int(dimensions["to_Length"])
                skumaster_qs = skumaster_qs.filter(user=user.id). \
                    filter(Q(skuattributes__attribute_name='length') &
                           Q(skuattributes__attribute_value__lte=Value(to_length)))
        if "from_Breadth" in dimensions:
            if dimensions["from_Breadth"]:
                from_breadth = int(dimensions["from_Breadth"])
                skumaster_qs = skumaster_qs.filter(user=user.id).\
                    filter(Q(skuattributes__attribute_name='breadth')&
                           Q(skuattributes__attribute_value__gte=Value(from_breadth)))
        if "to_Breadth" in dimensions:
            if dimensions["to_Breadth"]:
                to_breadth = int(dimensions["to_Breadth"])
                skumaster_qs = skumaster_qs.filter(user=user.id). \
                    filter(Q(skuattributes__attribute_name='breadth') &
                           Q(skuattributes__attribute_value__lte=Value(to_breadth)))
        if "from_Height" in dimensions:
            if dimensions["from_Height"]:
                from_height = int(dimensions["from_Height"])
                skumaster_qs = skumaster_qs.filter(user=user.id).\
                    filter(Q(skuattributes__attribute_name='height')&
                           Q(skuattributes__attribute_value__gte=Value(from_height)))
        if "to_Height" in dimensions:
            if dimensions["to_Height"]:
                to_height = int(dimensions["to_Height"])
                skumaster_qs = skumaster_qs.filter(user=user.id). \
                    filter(Q(skuattributes__attribute_name='height') &
                           Q(skuattributes__attribute_value__lte=Value(to_height)))
        if "intfrom_Height" in dimensions:
            if dimensions["intfrom_Height"]:
                intfrom_Height = int(dimensions["intfrom_Height"])
                skumaster_qs = skumaster_qs.filter(user=user.id). \
                    filter(Q(skuattributes__attribute_name='Internal Height') &
                           Q(skuattributes__attribute_value__gte=Value(intfrom_Height)))
        if "intto_Height" in dimensions:
            if dimensions["intto_Height"]:
                intto_Height = int(dimensions["intto_Height"])
                skumaster_qs = skumaster_qs.filter(user=user.id). \
                    filter(Q(skuattributes__attribute_name='Internal Height') &
                           Q(skuattributes__attribute_value__lte=Value(intto_Height)))
        if "intfrom_Length" in dimensions:
            if dimensions["intfrom_Length"]:
                intfrom_Length = int(dimensions["intfrom_Length"])
                skumaster_qs = skumaster_qs.filter(user=user.id). \
                    filter(Q(skuattributes__attribute_name='Internal Length') &
                           Q(skuattributes__attribute_value__gte=Value(intfrom_Length)))
        if "intto_Length" in dimensions:
            if dimensions["intto_Length"]:
                intto_Length = int(dimensions["intto_Length"])
                skumaster_qs = skumaster_qs.filter(user=user.id). \
                    filter(Q(skuattributes__attribute_name='Internal Length') &
                           Q(skuattributes__attribute_value__lte=Value(intto_Length)))
        if "intfrom_Breadth" in dimensions:
            if dimensions["intfrom_Breadth"]:
                intfrom_Breadth = int(dimensions["intfrom_Breadth"])
                skumaster_qs = skumaster_qs.filter(user=user.id). \
                    filter(Q(skuattributes__attribute_name='Internal Breadth') &
                           Q(skuattributes__attribute_value__gte=Value(intfrom_Breadth)))
        if "intto_Breadth" in dimensions:
            if dimensions["intto_Breadth"]:
                intto_Breadth = int(dimensions["intto_Breadth"])
                skumaster_qs = skumaster_qs.filter(user=user.id). \
                    filter(Q(skuattributes__attribute_name='Internal Breadth') &
                           Q(skuattributes__attribute_value__lte=Value(intto_Breadth)))
    all_pricing_ids = PriceMaster.objects.filter(sku__user=user.id, price_type=price_type).values_list('sku_id',
                                                                                                    flat=True)
    if is_margin_percentage == 'true':
        pricemaster = PriceMaster.objects.prefetch_related('sku').filter(price_type=price_type).annotate(
            new_price=F('price') + ((F('price') / Value(100)) * Value(custom_margin))).filter(**filter_params1)
        if price_field == 'price':
            dis_percent = 0
            if customer_master:
                dis_percent = customer_master[0].discount_percentage
            sku_master1 = filtered_sku_master.annotate(
                n_price=F(price_field) * (1 - (Value(dis_percent) / Value(100)))).annotate(
                new_price=F('n_price') + (F('n_price') / Value(100)) * Value(custom_margin))\
                .filter(**filter_params).exclude(id__in=all_pricing_ids)
        else:
            markup = 0
            if customer_master:
                markup = customer_master[0].markup
            sku_master1 = filtered_sku_master.annotate(
                n_price=F(price_field) * (1 + (Value(markup) / Value(100)))).annotate(
                new_price=F('n_price') + (F('n_price') / Value(100)) * Value(custom_margin))\
                .filter(**filter_params).exclude(id__in=all_pricing_ids)
        if filter_params.has_key('new_price__lte'):
            del filter_params['new_price__lte']
        if filter_params.has_key('new_price__gte'):
            del filter_params['new_price__gte']

        sku_master2 = filtered_sku_master.filter(
            sku_code__in=pricemaster.values_list('sku__sku_code', flat=True)).filter(**filter_params)
        sku_master = sku_master1 | sku_master2
        sku_prices = dict(sku_master.only('id', 'new_price').values_list('id', 'new_price'))
        pricemaster_prices = dict(pricemaster.only('sku_id', 'new_price').values_list('sku_id', 'new_price'))
        prices_dict = dict(sku_prices.items() + pricemaster_prices.items())
    else:
        pricemaster = PriceMaster.objects.filter(price_type=price_type).annotate(
            new_price=F('price') + Value(custom_margin)).filter(**filter_params1)
        if price_field == 'price':
            dis_percent = 0
            if customer_master:
                dis_percent = customer_master[0].discount_percentage
            sku_master1 = filtered_sku_master.annotate(
                n_price=F(price_field) * (1 - (Value(dis_percent) / Value(100)))).annotate(
                new_price=F('n_price') + Value(custom_margin))\
                .filter(**filter_params).exclude(id__in=all_pricing_ids)
        else:
            markup = 0
            if customer_master:
                markup = customer_master[0].markup
            sku_master1 = filtered_sku_master.annotate(
                n_price=F(price_field) * (1 + (Value(markup) / Value(100)))).annotate(
                new_price=F('n_price') + Value(custom_margin))\
                .filter(**filter_params).exclude(id__in=all_pricing_ids)

        if filter_params.has_key('new_price__lte'):
            del filter_params['new_price__lte']
        if filter_params.has_key('new_price__gte'):
            del filter_params['new_price__gte']
        if cust_mapped_skus:
            sku_master2 = SKUMaster.objects.exclude(sku_class='').filter(id__in=cust_mapped_skus)
        else:
            sku_master2 = SKUMaster.objects.exclude(sku_class='')
        sku_master2 = sku_master2.filter(id__in=pricemaster.values_list('sku_id', flat=True)).filter(**filter_params)
        sku_master = sku_master1 | sku_master2
        sku_prices = dict(sku_master.only('id', 'new_price').values_list('id', 'new_price'))
        pricemaster_prices = dict(pricemaster.only('sku_id', 'new_price').values_list('sku_id', 'new_price'))
        prices_dict = dict(sku_prices.items() + pricemaster_prices.items())
    size_dict = request_data.get('size_filter', '')
    query_string = 'sku__sku_code'
    if size_dict:
        size_dict = eval(size_dict)
        if size_dict:
            classes = get_sku_available_stock(user, sku_master, query_string, size_dict)
            sku_master = sku_master.filter(sku_class__in=classes)
    # this code is commented because of overriding the sku_master as a empty it is checking the admin stock , always empty so commented.
    # if quantity and not admin_user:
    #     filt_ids = sku_master.values('id').annotate(stock_sum=Sum('stockdetail__quantity')).\
    #                             filter(stock_sum__gt=quantity).values_list('id', flat=True).distinct()
    #     sku_master = sku_master.filter(id__in=filt_ids)
    sku_master = sku_master.order_by('sequence')
    product_styles = sku_master.values_list('sku_class', flat=True).distinct()
    product_styles = list(OrderedDict.fromkeys(product_styles))
    if is_file or (msp_min_price and msp_max_price):
        start, stop = 0, len(product_styles)

    needed_stock_data = {}
    gen_whs = get_gen_wh_ids(request, user, delivery_date)
    is_central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
    if is_central_order_mgmt == 'true':
        gen_whs = UserGroups.objects.filter(admin_user=user).values_list('user', flat=True)
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
                                                                                  sku__sku_code__in=needed_skus).\
                                                filter(~Q(enquiry__extend_status='rejected')).exclude(warehouse_level=3).\
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

    # today_filter = datetime.datetime.today()
    # hundred_day_filter = today_filter + datetime.timedelta(days=90)
    ints_filters = {'quantity__gt': 0, 'sku__sku_code__in': needed_skus, 'sku__user__in': gen_whs, 'status': 'open'}
    asn_qs = ASNStockDetail.objects.filter(**ints_filters)
    nk_stock = asn_qs.filter(asn_po_num='NON_KITTED_STOCK')
    # intr_obj_100days_qs = asn_qs.filter(Q(arriving_date__lte=hundred_day_filter)| Q(asn_po_num='NON_KITTED_STOCK'))
    intr_obj_100days_ids = asn_qs.values_list('id', flat=True)
    asnres_det_qs = ASNReserveDetail.objects.filter(asnstock__in=intr_obj_100days_ids)
    asn_res_100days_qs = asnres_det_qs.filter(orderdetail__isnull=False)  # Reserved Quantity
    asn_res_100days_qty = dict(asn_res_100days_qs.values_list('asnstock__sku__sku_code').annotate(in_res=Sum('reserved_qty')))
    asn_blk_100days_qs = asnres_det_qs.filter(orderdetail__isnull=True)  # Blocked Quantity
    asn_blk_100days_qty = dict(
        asn_blk_100days_qs.values_list('asnstock__sku__sku_code').annotate(in_res=Sum('reserved_qty')))

    needed_stock_data['asn_quantities'] = dict(asn_qs.values_list('sku__sku_code').distinct().annotate(in_asn=Sum('quantity')))
    needed_stock_data['nonkitted_stock'] = dict(nk_stock.values_list('sku__sku_code').distinct().annotate(Sum('quantity')))
    needed_stock_data['asn_blocked_quantities'] = {}
    for k, v in needed_stock_data['asn_quantities'].items():
        asn_qty = needed_stock_data['asn_quantities'][k]
        asn_res_qty = asn_res_100days_qty.get(k, 0)
        asn_blk_qty = asn_blk_100days_qty.get(k, 0)
        needed_stock_data['asn_quantities'][k] = asn_qty - asn_res_qty - asn_blk_qty
        needed_stock_data['asn_blocked_quantities'][k] = asn_blk_qty
    if dimensions:
        product_styles = skumaster_qs.values_list('sku_class', flat=True).distinct()
        product_styles = list(OrderedDict.fromkeys(product_styles))
        data = get_styles_data(user, product_styles, skumaster_qs, start, stop, request, customer_id=customer_id,
                               customer_data_id=customer_data_id, is_file=is_file, prices_dict=prices_dict,
                               price_type=price_type, custom_margin=custom_margin, specific_margins=specific_margins,
                               is_margin_percentage=is_margin_percentage, stock_quantity=quantity,
                               needed_stock_data=needed_stock_data, msp_min_price=msp_min_price, msp_max_price=msp_max_price)
    else:
        data = get_styles_data(user, product_styles, sku_master, start, stop, request, customer_id=customer_id,
                               customer_data_id=customer_data_id, is_file=is_file, prices_dict=prices_dict,
                               price_type=price_type, custom_margin=custom_margin, specific_margins=specific_margins,
                               is_margin_percentage=is_margin_percentage, stock_quantity=quantity,
                               needed_stock_data=needed_stock_data, msp_min_price=msp_min_price, msp_max_price=msp_max_price)
    return data, start, stop


'''def get_user_sku_data(user):
    request = {}
    #user = User.objects.get(id=sku.user)
    _brand, _categories, _size, _colors, category_details = get_sku_categories_data(request, user, request_data={'file': True}, is_catalog='true')
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
        file_dump.save()'''


@csrf_exempt
@login_required
@get_admin_user
def get_file_checksum(request, user=''):
    name = request.GET.get('name', '')
    #user = request.GET.get('user', '')
    file_content = ''
    file_data = list(FileDump.objects.filter(name=name, user=user.id).values('name', 'checksum', 'path'))
    if file_data:
        file_data = file_data[0]
    return HttpResponse(json.dumps({'file_data': file_data}))


@csrf_exempt
@login_required
@get_admin_user
def get_file_content(request, user=''):
    name = request.GET.get('name', '')
    #user = request.GET.get('user', '')
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

    lis = ['wms_code', 'sku_desc', 'mrp']
    query_objects = sku_master.filter(Q(wms_code__icontains=search_key) | Q(sku_desc__icontains=search_key),
                                      status = 1,user=user.id)

    master_data = query_objects.filter(Q(wms_code__exact=search_key) | Q(sku_desc__exact=search_key), user=user.id)
    if master_data:
        master_data = master_data[0]

        total_data.append({'wms_code': master_data.wms_code, 'sku_desc': master_data.sku_desc, \
                           'measurement_unit': master_data.measurement_type,
                           'load_unit_handle': master_data.load_unit_handle,
                           'mrp': master_data.mrp})

    master_data = query_objects.filter(Q(wms_code__istartswith=search_key) | Q(sku_desc__istartswith=search_key),
                                       user=user.id)
    total_data = build_search_data(total_data, master_data, limit)

    if len(total_data) < limit:
        total_data = build_search_data(total_data, query_objects, limit)
    return HttpResponse(json.dumps(total_data))


def get_admin(user):
    is_admin_exists = UserGroups.objects.filter(user=user)
    if is_admin_exists:
        admin_user = is_admin_exists[0].admin_user
    else:
        admin_user = user
    return admin_user


@csrf_exempt
@login_required
@get_admin_user
def get_supplier_sku_prices(request, user=""):
    suppli_id = request.POST.get('suppli_id', '')
    sku_codes = request.POST.get('sku_codes', '')
    log.info('Get Customer SKU Taxes data for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        result_data=get_supplier_sku_price_values(suppli_id,sku_codes,user)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        result_data = []
        log.info('Get Supplier SKU Taxes Data failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(request.GET.dict()), str(e)))
    return HttpResponse(json.dumps(result_data))


def get_order_sku_price(customer_master, data, user):
    price_bands_list = []
    sku_code = data.sku_code
    customer_price_name = get_misc_value('calculate_customer_price', user.id)
    is_sellingprice = False
    price = data.cost_price
    if customer_price_name == 'price':
        price = data.price
        is_sellingprice = True
    discount = 0

    if customer_master:
        customer_obj = customer_master[0]
        price_type = customer_obj.price_type
        price_band_flag = get_misc_value('priceband_sync', user.id)
        if price_band_flag == 'true':
            user = get_admin(user)
        price, mrp = get_customer_based_price(customer_obj, price, data.mrp, is_sellingprice)
        price_master_objs = PriceMaster.objects.filter(price_type=price_type, sku__sku_code=sku_code,
                                                       sku__user=user.id)
        if price_master_objs:
            price_bands_list = []
            for i in price_master_objs:
                price_band_map = {'price': i.price, 'discount': i.discount,
                                  'min_unit_range': i.min_unit_range, 'max_unit_range': i.max_unit_range}
                price_bands_list.append(price_band_map)
            price = price_master_objs[0].price
            discount = price_master_objs[0].discount
        elif price_type:
            attr_mapping = copy.deepcopy(SKU_NAME_FIELDS_MAPPING)
            for attr_key, attr_val in attr_mapping.items():
                price_master_objs = PriceMaster.objects.filter(user=user.id, price_type=price_type,
                                                                    attribute_type=attr_key,
                                                                    attribute_value=getattr(data, attr_val))
                if price_master_objs.exists():
                    price_master_obj = price_master_objs[0]
                    if price_master_obj.price:
                        price = price_master_obj.price
                    discount = price_master_obj.discount
                    price_bands_list = [{'price': price, 'discount': price_master_obj.discount,
                                        'min_unit_range': price_master_obj.min_unit_range,
                                         'max_unit_range': price_master_obj.max_unit_range}]
                    break

    return price, discount, price_bands_list


@csrf_exempt
@login_required
@get_admin_user
def get_customer_sku_prices(request, user=""):
    cust_id = request.POST.get('cust_id', '')
    sku_codes = request.POST.get('sku_codes', '')
    tax_type = request.POST.get('tax_type', '')
    igst_tax = ''
    sgst_tax = ''
    cgst_tax = ''
    product_type = ''
    skuPack_quantity = ''
    marginal_flag = 0
    log.info('Get Customer SKU Prices data for ' + user.username + ' is ' + str(request.POST.dict()))
    sku_pack_config = get_misc_value('sku_pack_config', user.id)
    inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
    try:
        if sku_codes:
            sku_values = SKUMaster.objects.filter(wms_code=sku_codes, user=user.id).values()
            if len(sku_values) > 0 :
                product_type = sku_values[0]['product_type']
            tax_values = TaxMaster.objects.filter(product_type=product_type, user=user.id).values()
            if tax_values.exists():
                igst_tax = tax_values[0]['igst_tax']
                sgst_tax = tax_values[0]['sgst_tax']
                cgst_tax = tax_values[0]['cgst_tax']

        sku_codes = [sku_codes]
        result_data = []
        price_bands_list = []
        customer_master = ""

        inter_state = inter_state_dict.get(tax_type, 2)
        if cust_id:
            customer_master = CustomerMaster.objects.filter(customer_id=cust_id, user=user.id)

        for sku_code in sku_codes:
            if not sku_code:
                continue
            data = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
            if data:
                data = data[0]
                sku_attr_obj = SKUAttributes.objects.filter(sku_id=data.id,
                                        attribute_name='MARGINAL GST').only('attribute_value')
                if sku_attr_obj:
                    if sku_attr_obj[0].attribute_value.upper() == 'YES':
                        marginal_flag = 1
            else:
                return "sku_doesn't exist"
            tax_masters = TaxMaster.objects.filter(user_id=user.id, product_type=data.product_type,
                                                   inter_state=inter_state)
            taxes_data = []
            for tax_master in tax_masters:
                taxes_data.append(tax_master.json())

            price, discount, price_bands_list = get_order_sku_price(customer_master, data, user)
            # customer_price_name = get_misc_value('calculate_customer_price', user.id)
            # is_sellingprice = False
            # price = data.cost_price
            # if customer_price_name == 'price':
            #     price = data.price
            #     is_sellingprice = True
            # discount = 0
            #
            # if customer_master:
            #     customer_obj = customer_master[0]
            #     price_type = customer_obj.price_type
            #     price_band_flag = get_misc_value('priceband_sync', user.id)
            #     if price_band_flag == 'true':
            #         user = get_admin(user)
            #     price, mrp = get_customer_based_price(customer_obj, price, data.mrp, is_sellingprice)
            #     price_master_objs = PriceMaster.objects.filter(price_type=price_type, sku__sku_code=sku_code,
            #                                                    sku__user=user.id)
            #     if price_master_objs:
            #         price_bands_list = []
            #         for i in price_master_objs:
            #             price_band_map = {'price': i.price, 'discount': i.discount,
            #                               'min_unit_range': i.min_unit_range, 'max_unit_range': i.max_unit_range}
            #             price_bands_list.append(price_band_map)
            #         price = price_master_objs[0].price
            #         discount = price_master_objs[0].discount
            if sku_pack_config == 'true' and data.id:
                skuPack_data = SKUPackMaster.objects.filter(sku__id= data.id, sku__user= user.id)
                if skuPack_data:
                    skuPack_quantity = skuPack_data[0].pack_quantity
            result_data.append(
                {'wms_code': data.wms_code, 'sku_desc': data.sku_desc, 'price': price, 'discount': discount, 'sku_pack_quantity': skuPack_quantity,
                 'taxes': taxes_data, 'price_bands_map': price_bands_list, 'mrp': data.mrp, 'product_type': product_type, 'igst_tax': igst_tax, 'sgst_tax': sgst_tax, 'cgst_tax': cgst_tax, 'marginal_flag':marginal_flag})

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        result_data = []
        log.info('Get Customer SKU Prices Data failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
    return HttpResponse(json.dumps(result_data))


def build_search_data(to_data, from_data, limit):
    if (len(to_data) >= limit):
        return to_data
    else:
        for data in from_data:
            if (len(to_data) >= limit):
                break
            else:
                status = True
                for item in to_data:
                    if (item['wms_code'] == data.wms_code):
                        status = False
                        break
                if status:
                    to_data.append({'wms_code': data.wms_code, 'sku_desc': data.sku_desc,
                                    'measurement_unit': data.measurement_type,
                                    'mrp': data.mrp, 'sku_class': data.sku_class,
                                    'style_name': data.style_name})
        return to_data


def build_style_search_data(to_data, from_data, limit):
    if (len(to_data) >= limit):
        return to_data
    else:
        for data in from_data:
            if (len(to_data) >= limit):
                break
            else:
                status = True
                for item in to_data:
                    if (item['sku_class'] == data['sku_class']):
                        status = False
                        break
                if status:
                    to_data.append({'sku_class': data['sku_class'],
                                    'style_name': data['style_name']})
        return to_data

@fn_timer
def insert_update_brands(user):
    request = {}
    sku_master = list(
        SKUMaster.objects.filter(user=user.id).exclude(sku_brand='').values_list('sku_brand', flat=True).distinct())
    if not 'All' in sku_master:
        sku_master.append('All')
    brand_instance = Brands.objects.filter(user_id=user.id)
    brands_list = list(brand_instance.values_list('brand_name', flat=True))
    brand_creation_list = set(sku_master) - set(brands_list)
    all_brand_objs = []
    for brand in brand_creation_list:
        all_brand_objs.append(Brands(**{'user_id': user.id, 'brand_name': brand}))
    if all_brand_objs:
        Brands.objects.bulk_create(all_brand_objs)
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
    # reversed_perms = OrderedDict(( ([(value, key) for key, value in permission_dict.iteritems()]) ))
    group = Group.objects.get(id=data_id)
    group_name = (group.name).replace(user.username + ' ', '')
    brands = list(GroupBrand.objects.filter(group_id=group.id).values_list('brand_list__brand_name', flat=True))
    stages = list(GroupStages.objects.filter(group_id=group.id).values_list('stages_list__stage_name', flat=True))
    permissions = group.permissions.values_list('codename', flat=True)
    statuses = list(GroupPermMapping.objects.filter(group_id=group.id, perm_type='extra_order_status').\
                                    values_list('perm_value', flat=True).order_by('sequence'))
    perms = []
    for perm in permissions:
        temp = perm
        if temp in reversed_perms.keys() and (reversed_perms[temp] not in perms):
            perms.append(reversed_perms[temp])
    return HttpResponse(
        json.dumps({'group_name': group_name, 'data': {'brands': brands, 'stages': stages, 'permissions': perms,
                                                       'View Order Statuses': statuses}}))


def get_sku_master(user, sub_user, is_list=''):
    if not is_list:
        sku_master = SKUMaster.objects.filter(user=user.id)
    else:
        sku_master = SKUMaster.objects.filter(user__in=user)
    sku_master_ids = sku_master.values_list('id', flat=True)
    if not sub_user.is_staff:
        if is_list:
            usernames = list(User.objects.filter(id__in=user).values_list('username', flat=True))
            sub_user_groups = sub_user.groups.filter().exclude(name__in=usernames).values_list('name', flat=True)
        else:
            sub_user_groups = sub_user.groups.filter().exclude(name=user.username).values_list('name', flat=True)
        brands_list = GroupBrand.objects.filter(group__name__in=sub_user_groups).values_list('brand_list__brand_name',
                                                                                             flat=True)
        if not 'All' in brands_list:
            sku_master = sku_master.filter(sku_brand__in=brands_list)
        sku_master_ids = sku_master.values_list('id', flat=True)

    return sku_master, sku_master_ids


def create_update_user(full_name, email, phone_number, password, username, role_name='customer'):
    """
    Creating a new Customer User
    """
    new_user_id = ''
    if username and password:
        user = User.objects.filter(username=username)
        if user:
            status = "User already exists"
        else:
            user = User.objects.create_user(username=username, email=email, password=password, first_name=full_name,
                                            last_login=datetime.datetime.now())
            user.save()
            new_user_id = user.id
            hash_code = hashlib.md5(b'%s:%s' % (user.id, email)).hexdigest()
            if user:
                prefix = re.sub('[^A-Za-z0-9]+', '', user.username)[:3].upper()
                user_profile = UserProfile.objects.create(phone_number=phone_number, user_id=user.id,
                                                          api_hash=hash_code, prefix=prefix, user_type=role_name)
                user_profile.save()
            status = 'New Customer Added'

    return status, new_user_id


@csrf_exempt
@login_required
@get_admin_user
def pull_orders_now(request, user=''):
    from rest_api.views.easyops_api import *
    from rest_api.views.integrations import *
    integrations = Integrations.objects.filter(user=user.id, status=1)
    for integrate in integrations:
        obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
        orders = obj.get_pending_orders(user=user)
        update_orders(orders, user=user, company_name=integrate.name)
    return HttpResponse("Success")


@csrf_exempt
def get_order_sync_issues(start_index, stop_index, temp_data, search_term, order_term, col_num, request, user,
                          filters={}):
    lis = ['order_id', 'sku_code', 'reason', 'creation_date']
    order_data = lis[col_num]
    filter_params = get_filtered_params(filters, lis)

    if order_term == 'desc':
        order_data = '-%s' % order_data
    if search_term:
        master_data = OrdersTrack.objects.filter(
            Q(order_id__icontains=search_term) | Q(sku_code__icontains=search_term) |
            Q(reason__icontains=search_term), status=1, **filter_params).order_by(order_data)

    else:
        master_data = OrdersTrack.objects.filter(user=user.id, status=1, **filter_params).order_by(order_data)

    temp_data['recordsTotal'] = master_data.count()
    temp_data['recordsFiltered'] = master_data.count()

    for result in master_data[start_index: stop_index]:
        temp_data['aaData'].append(OrderedDict((('Order ID', result.order_id), ('SKU Code', result.sku_code),
                                                ('Reason', result.reason),
                                                ('Created Date', get_local_date(user, result.creation_date)),
                                                ('DT_RowClass', 'results'), ('DT_RowId', result.id))))


@csrf_exempt
@login_required
@get_admin_user
def delete_order_sync_data(request, user=""):
    """ The code to delete the order_sync_data """
    order_sync_id = request.POST.get('sync_id', "")
    if order_sync_id:
        sync_entry = OrdersTrack.objects.filter(id=order_sync_id, user=user.id)
        if sync_entry:
            sync_entry = sync_entry[0]
            sync_entry.status = 2
            sync_entry.save()

    return HttpResponse(json.dumps({"resp": True, "resp_message": "Issue is deleted"}))


@csrf_exempt
@login_required
@get_admin_user
def order_sync_data_detail(request, user=""):
    """ The code to show the detail of order_sync_data """

    order_sync_id = request.GET.get('sync_id', "")
    if order_sync_id:
        sync_entry = OrdersTrack.objects.filter(id=order_sync_id, user=user.id)
        if sync_entry:
            sync_entry = sync_entry[0]
            shipment_date = ''
            if sync_entry.shipment_date:
                shipment_date = get_local_date(user, sync_entry.shipment_date)
            data = {'sku_code': sync_entry.sku_code, 'order_id': sync_entry.order_id, 'reason': sync_entry.reason,
                    'channel_sku': sync_entry.channel_sku,
                    'marketplace': sync_entry.marketplace, 'quantity': sync_entry.quantity,
                    'title': sync_entry.title, 'shipment_date': shipment_date}
    return HttpResponse(json.dumps(data))


@csrf_exempt
@login_required
@get_admin_user
def confirm_order_sync_data(request, user=""):
    """This code confirms the order sync data, once proper sku_id is entered """
    order_sync_id = request.POST.get('sync_id', "")
    new_sku_code = request.POST.get('sku_code', "")

    if order_sync_id:
        sync_entry = OrdersTrack.objects.filter(id=order_sync_id, user=user.id)
        if sync_entry:
            sync_entry = sync_entry[0]
            sku_obj = SKUMaster.objects.filter(sku_code=new_sku_code, user=user.id)

            if not sku_obj:
                return HttpResponse(json.dumps({"resp": False, "resp_message": "wrong sku code"}))
            else:
                sku_obj = sku_obj[0]
            ord_id = "".join(re.findall("\d+", sync_entry.order_id))
            ord_code = "".join(re.findall("\D+", sync_entry.order_id))

            ord_obj = OrderDetail.objects.filter(
                Q(order_id=ord_id, order_code=ord_code) | Q(original_order_id=sync_entry.order_id), sku=sku_obj,
                user=user.id)

            if ord_obj:
                return HttpResponse(json.dumps({"resp": False, "resp_message": "Order already exist"}))

            shipment_date = datetime.datetime.now()
            if sync_entry.shipment_date:
                shipment_date = sync_entry.shipment_date
            ord_obj = OrderDetail.objects.create(user=user.id, order_id=ord_id, order_code=ord_code, status=1,
                                                 shipment_date=shipment_date, title=sync_entry.title,
                                                 quantity=sync_entry.quantity,
                                                 original_order_id=sync_entry.order_id,
                                                 marketplace=sync_entry.marketplace, sku=sku_obj)

            CustomerOrderSummary.objects.create(order=ord_obj)

            sync_entry.mapped_sku_code = new_sku_code
            sync_entry.status = 0
            sync_entry.save()

        else:
            return HttpResponse(json.dumps({"resp": False, "resp_message": "wrong id"}))

    else:
        return HttpResponse(json.dumps({"resp": False, "resp_message": "id not present"}))
    return HttpResponse(json.dumps({"resp": True, "resp_message": "Success"}))


def check_and_return_mapping_id(sku_code, title, user, check=True):
    sku_id = ''
    sku_master = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
    if sku_master:
        sku_id = sku_master[0].id
    else:
        market_mapping = ''
        if not check:
            if sku_code:
                market_mapping = MarketplaceMapping.objects.filter(marketplace_code=sku_code, sku__user=user.id)
                # if not market_mapping and title:
                #    market_mapping = MarketplaceMapping.objects.filter(description=title, sku__user=user.id)
        else:
            if sku_code:
                market_mapping = MarketplaceMapping.objects.filter(marketplace_code=sku_code, sku__user=user.id,
                                                                   sku__status=1)
                # if not market_mapping and title:
                #    market_mapping = MarketplaceMapping.objects.filter(description=title, sku__user=user.id, sku__status=1)

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


def all_size_list(user):
    all_sizes = []
    size_objs = SizeMaster.objects.filter(user=user.id)
    if size_objs:
        sizes_items = size_objs.values_list('size_value', flat=True)
        for sizes in sizes_items:
            all_sizes.extend(sizes.split('<<>>'))

    all_sizes = list(set(all_sizes))

    return all_sizes


@csrf_exempt
@login_required
@get_admin_user
def get_size_names(requst, user=""):
    size_names = SizeMaster.objects.filter(user=user.id)
    sizes_list = {}
    if not size_names.filter(size_name='DEFAULT'):
        SizeMaster.objects.create(user=user.id, size_name='DEFAULT', creation_date=datetime.datetime.now(),
                                  size_value='S<<>>M<<>>L<<>>XL<<>>XXL')
        size_names = SizeMaster.objects.filter(user=user.id)
    for sizes in size_names:
        size_value_list = (sizes.size_value).split('<<>>')
        size_value_list = filter(None, size_value_list)
        sizes_list.update({sizes.size_name: size_value_list})

    size_name = list(size_names.values_list('size_name', flat=True))
    sizes_list.update({'size_names': size_name})

    return HttpResponse(json.dumps(sizes_list))


@csrf_exempt
@login_required
@get_admin_user
def get_sellers_list(request, user=''):
    sellers = SellerMaster.objects.filter(user=user.id).order_by('seller_id')
    terms_condition = UserTextFields.objects.filter(user=user.id, field_type = 'terms_conditions')
    if terms_condition.exists():
        raise_po_terms_conditions = terms_condition[0].text_field
        raise_po_terms_conditions = raise_po_terms_conditions.replace('<<>>', '\n')
    else:
        raise_po_terms_conditions = get_misc_value('raisepo_terms_conditions', user.id)
    ship_address_details = []
    ship_address_names = []
    user_ship_address = UserAddresses.objects.filter(user_id=user.id)
    if user_ship_address:
        shipment_names = list(user_ship_address.values_list('address_name', flat=True))
        ship_address_names.extend(shipment_names)
        for data in user_ship_address:
            ship_address_details.append({'title':data.address_name,'addr_name':data.user_name,'mobile_number':data.mobile_number,'pincode':data.pincode,'address':data.address})
    seller_list = []
    seller_supplier = {}
    for seller in sellers:
        seller_list.append({'id': seller.seller_id, 'name': seller.name})
        if seller.supplier:
            seller_supplier[seller.seller_id] = seller.supplier.id
    user_list = get_all_warehouses(user)
    return HttpResponse(json.dumps({'sellers': seller_list, 'tax': 5.5, 'receipt_types': PO_RECEIPT_TYPES, 'shipment_add_names':ship_address_names, \
                                    'seller_supplier_map': seller_supplier, 'warehouse' : user_list, 'raise_po_terms_conditions' : raise_po_terms_conditions, 'shipment_addresses' : ship_address_details}))


def update_filled_capacity(locations, user_id):
    location_masters = LocationMaster.objects.filter(location__in=locations, zone__user=user_id)
    location_ids = list(location_masters.values_list('id', flat=True))
    location_stocks = StockDetail.objects.filter(location_id__in=location_ids, sku__user=user_id,
                                                 quantity__gt=0).values('location_id').distinct().annotate(
        total_filled=Sum('quantity'))
    loc_mast_ids = map(lambda d: d['location_id'], location_stocks)
    loc_quantities = map(lambda d: d['total_filled'], location_stocks)
    for location in location_masters:
        filled_capacity = 0
        if location.id in loc_mast_ids:
            filled_capacity = loc_quantities[loc_mast_ids.index(location.id)]
        location.filled_capacity = filled_capacity
        location.save()


def get_dictionary_query(data_dict={}):
    queries = [Q(**{key: value}) for key, value in data_dict.iteritems()]
    if queries:
        query = queries.pop()
        for item in queries:
            query |= item
    else:
        query = Q()
    return query


def get_shipment_time(ord_id, user):
    "function to return shipment slot for an order"
    cust_status_obj = CustomerOrderSummary.objects.filter(order__id=ord_id, order__user=user.id)
    time_slot = ""
    try:
        if cust_status_obj:
            time_slot = cust_status_obj[0].shipment_time_slot
            if time_slot:
                if "-" in time_slot:
                    time_slot = time_slot.split("-")[0]


    except:
        log.info("no shipment time for order %s" % (ord_id))

    return time_slot


@csrf_exempt
@login_required
@get_admin_user
def get_vendors_list(request, user=''):
    vendor_objs = VendorMaster.objects.filter(user=user.id)
    resp = {}
    for vendor in vendor_objs:
        resp.update({vendor.vendor_id: vendor.name})

    return HttpResponse(json.dumps({'data': resp}))


def apply_search_sort(columns, data_dict, order_term, search_term, col_num, exact=False):
    if search_term:
        search_filter = []
        for item in columns:
            comp_var = 'in'
            if exact:
                comp_var = '=='
            search_filter.append("'%s'.lower() %s str(person['%s']).lower()" % (search_term, comp_var, item))
        final_filter = "filter(lambda person: " + ' or '.join(search_filter) + ', data_dict)'
        data_dict = eval(final_filter)

    if order_term:
        order_data = columns[col_num]
        if order_term == "asc":
            data_dict = sorted(data_dict, key=lambda x: x[order_data])
        else:
            data_dict = sorted(data_dict, key=lambda x: x[order_data], reverse=True)
    return data_dict


def password_notification_message(username, password, name, to, role_name='Customer'):
    """ Send SMS for password modification """
    arguments = "%s -- %s -- %s -- %s" % (username, password, name, to)
    log.info(arguments)
    try:

        data = " Dear %s, Your credentials for %s %s Portal are as follows: \n Username: %s \n Password: %s" % (
                        role_name, role_name, name, username, password)
        send_sms(to, data)
    except:
        log.info("message sending failed")


def build_search_term_query(columns, search_term):
    filter_params = OrderedDict()
    query = Q
    if not search_term:
        return Q()
    for col in columns:
        if not 'date' in col:
            filter_params[col + '__icontains'] = search_term
        else:
            filter_params[col + '__regex'] = search_term
    query = get_dictionary_query(data_dict=filter_params)
    return query


def validate_email(email):
    check = re.match(r"[^@]+@[^@]+\.[^@]+", email)
    if not check:
        return True
    else:
        return False


def get_tally_model_data(model_name, col_filter, col_data, field_name):
    data_list = []
    exist_values = []
    for col_name in col_data:
        temp_filter = copy.deepcopy(col_filter)
        temp_filter[field_name] = col_name
        model_group = model_name.objects.filter(**temp_filter)
        if model_group:
            model_group = model_group[0]
            data_list.append(model_group.json())
            exist_values.append(col_name)
        else:
            data_list.append({field_name: col_name})

    exc_filter = {field_name + '__in': exist_values}
    model_name.objects.exclude(**exc_filter).filter(**col_filter).delete()
    return data_list


@csrf_exempt
@login_required
@get_admin_user
def get_tally_data(request, user=""):
    """ Get Tally Configuration Data"""

    try:
        result_data = {}
        tab_col_dict = {'SupplierMaster': 'supplier_type', 'CustomerMaster': 'customer_type',
                        'SKUMaster': 'product_type'}

        for table_name, col_name in tab_col_dict.iteritems():
            log.info("%s ---- %s" % (table_name, col_name))

            django_objs = eval(table_name).objects.filter(user=user.id).exclude(**{col_name: ""}).values_list(col_name,
                                                                                                              flat=True).distinct()

            result_data[col_name] = list(django_objs)
            if col_name in ['customer_type', 'supplier_type']:
                result_data[col_name].append('Default')

        headers = OrderedDict(
            (('sku_brand', 'Brand'), ('sku_category', 'Category'), ('sku_group', 'Group'), ('sku_class', 'Class'),
             ('sku_type', 'Type')
             ))
        result_data['headers'] = headers
        result_data['product_group'] = result_data['product_type']
        tally_config = TallyConfiguration.objects.filter(user_id=user.id)
        config_dict = {}
        if tally_config:
            config_dict = tally_config[0].json()
            config_dict['automatic_voucher'] = STATUS_DICT[config_dict['automatic_voucher']]
            config_dict['maintain_bill'] = STATUS_DICT[config_dict['maintain_bill']]
        master_groups = OrderedDict()
        master_groups['vendor'] = get_tally_model_data(MasterGroupMapping,
                                                       {'master_type': 'vendor', 'user_id': user.id}, \
                                                       result_data['supplier_type'], 'master_value')
        master_groups['customer'] = get_tally_model_data(MasterGroupMapping,
                                                         {'master_type': 'customer', 'user_id': user.id},
                                                         result_data['customer_type'], 'master_value')
        result_data['master_groups'] = master_groups
        group_ledger_mapping = GroupLedgerMapping.objects.filter(user_id=user.id)
        group_ledgers = OrderedDict()
        for group_ledger in group_ledger_mapping:
            group_ledgers.setdefault(group_ledger.ledger_type, [])
            group_ledgers[group_ledger.ledger_type].append(group_ledger.json())
        result_data['group_ledgers'] = group_ledgers
        vat_ledger_mapping = VatLedgerMapping.objects.filter(user_id=user.id)
        vat_ledgers = OrderedDict()
        for vat_ledger in vat_ledger_mapping:
            vat_ledgers.setdefault(vat_ledger.tax_type, [])
            vat_ledgers[vat_ledger.tax_type].append(vat_ledger.json())
        if not vat_ledgers.get('purchase', ''):
            vat_ledgers['purchase'] = []
        if not vat_ledgers.get('sales', ''):
            vat_ledgers['sales'] = []
        if not group_ledgers.get('purchase', ''):
            group_ledgers['purchase'] = []
        if not group_ledgers.get('sales', ''):
            group_ledgers['sales'] = []

        result_data['vat_ledgers'] = vat_ledgers
        result_data['config_dict'] = config_dict
        res = {'data': result_data}
        log.info('Tally data for ' + user.username + ' is ' + str(res))
        res['status'] = 1
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        res = {'status': 0, 'data': {}}
        log.info('Get Tally Data failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))

    return HttpResponse(json.dumps(res))


@csrf_exempt
@login_required
@get_admin_user
def save_tally_data(request, user=""):
    """ Save or Update Tally Configuration Data"""
    data = {}
    request_data = copy.deepcopy(request.POST)
    log.info('Save Tally Configuration data for ' + user.username + ' is ' + str(request.POST.dict()))
    try:
        for key, value in request.POST.iterlists():
            if not ('purchase' in key or 'sales' in key or 'customer' in key or 'vendor' in key):
                continue
            if key in request_data.keys():
                del request_data[key]
            field_type, name = key.split('_', 1)
            data.setdefault(field_type, [])
            for index, val in enumerate(value):
                if len(data[field_type]) < index + 1:
                    data[field_type].append({})
                data[field_type][index][name] = val

        tally_config = TallyConfiguration.objects.filter(user_id=user.id)
        tally_obj = None
        if tally_config:
            tally_obj = tally_config[0]

        tally_dict = {'creation_date': datetime.datetime.now(), 'user_id': user.id}
        number_fields = ['tally_port', 'credit_period']
        switch_fields = ['automatic_voucher', 'maintain_bill']
        status_dict = {'true': 1, 'false': 0}
        for key, value in request_data.iteritems():
            if not value and key in number_fields:
                value = 0
            if key in switch_fields:
                value = status_dict[value]
            tally_dict[key] = value
            if tally_obj:
                setattr(tally_obj, key, value)
        if tally_obj:
            if 'maintain_bill' not in request_data.keys():
                tally_obj.maintain_bill = 0
            if 'automatic_voucher' not in request_data.keys():
                tally_obj.automatic_voucher = 0
            tally_obj.save()
        else:
            TallyConfiguration.objects.create(**tally_dict)

        for key, value in data.iteritems():
            if key in ['customer', 'vendor']:
                for val in value:
                    table_ins = MasterGroupMapping.objects.filter(master_type=key, master_value=val['type'],
                                                                  user_id=user.id)
                    if table_ins:
                        table_ins = table_ins[0]
                        table_ins.parent_group = val['parent_group']
                        table_ins.sub_group = val['sub_group']
                        table_ins.save()
                    else:
                        MasterGroupMapping.objects.create(master_type=key, master_value=val['type'],
                                                          parent_group=val['parent_group'],
                                                          user_id=user.id, sub_group=val['sub_group'],
                                                          creation_date=datetime.datetime.now())
            else:
                for val in value:
                    if val.get('product_group', ''):
                        table_ins = GroupLedgerMapping.objects.filter(ledger_type=key,
                                                                      product_group=val['product_group'],
                                                                      state=val['state'], user_id=user.id)
                        if table_ins:
                            table_ins = table_ins[0]
                            table_ins.ledger_name = val['ledger_name']
                            table_ins.state = val['state']
                            table_ins.save()
                        else:
                            GroupLedgerMapping.objects.create(ledger_type=key, product_group=val['product_group'],
                                                              user_id=user.id,
                                                              ledger_name=val['ledger_name'], state=val['state'],
                                                              creation_date=datetime.datetime.now())
                    if val.get('vat_ledger_name', ''):
                        table_ins = VatLedgerMapping.objects.filter(tax_type=key, ledger_name=val['vat_ledger_name'],
                                                                    user_id=user.id)
                        if table_ins:
                            table_ins = table_ins[0]
                            table_ins.tax_percentage = val['vat_percentage']
                            table_ins.save()
                        else:
                            VatLedgerMapping.objects.create(tax_type=key, ledger_name=val['vat_ledger_name'],
                                                            user_id=user.id,
                                                            tax_percentage=val['vat_percentage'],
                                                            creation_date=datetime.datetime.now())
        res = {'status': 1, 'message': 'Updated Successfully'}
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        res = {'status': 0, 'message': 'Updating Failed'}
        log.info('Save Tally Data failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
    return HttpResponse(json.dumps(res))


@csrf_exempt
@login_required
@get_admin_user
def delete_tally_data(request, user=""):
    """Delete Tally Group Ledger Mapping or Vat Ledger Mapping"""

    log.info('Delete tally data for ' + user.username + ' request params is ' + str(request.GET.dict()))
    try:
        for key, value in request.GET.iteritems():
            if key == 'group_ledger_id':
                GroupLedgerMapping.objects.filter(id=value, user_id=user.id).delete()
            elif key == 'vat_ledger_id':
                VatLedgerMapping.objects.filter(id=value, user_id=user.id).delete()
        res = {'status': 1, 'message': 'Deleted Successfully'}
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        res = {'status': 0, 'message': 'Deletion Failed'}
        log.info('Delete Tally Data failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
    return HttpResponse(json.dumps(res))


@csrf_exempt
@login_required
@get_admin_user
def get_categories_list(request, user=""):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    brand = request.GET.get('brand', '')
    name = request.GET.get('name', '')
    filter_params = {'user': user.id}
    if name:
        filter_params['name'] = name
        if not brand == 'ALL':
            filter_params['brand'] = brand
        categories_list = ProductProperties.objects.filter(**filter_params).values_list('category',
                                                                                        flat=True).distinct()
    else:
        if brand:
            filter_params['sku_brand__in'] = brand.split('<<>>')
        categories_list = sku_master.filter(**filter_params).exclude(sku_category='').values_list('sku_category',
                                                                                                  flat=True).distinct()
    return HttpResponse(json.dumps(list(categories_list)))


def get_generic_warehouses_list(user):
   return UserGroups.objects.filter(admin_user=user).exclude(user__userprofile__warehouse_level=2).values_list('user', flat=True)

@fn_timer
def get_cal_style_data(style_data, quantity):

    quantity = int(quantity)
    unit_price = style_data['variants'][0]['price']
    if style_data['variants'][0].get('price_ranges', ''):
        status = False
        for price in style_data['variants'][0]['price_ranges']:
            if quantity >= price['min_unit_range'] and quantity <= price['max_unit_range']:
                unit_price = price['price']
                status = True
                break
        if not status:
            unit_price = style_data['variants'][0]['price_ranges'][0]['price']
    amount = unit_price * quantity
    tax_percentage = 0
    tax_value = 0
    if style_data['variants'][0]['taxes']:
        tax = style_data['variants'][0]['taxes'][0]
        tax_percentage = float(tax['sgst_tax']) + float(tax['igst_tax']) + float(tax['cgst_tax'])
        tax_value = (amount / 100) * tax_percentage
    data = {'unit_price': int(unit_price), 'quantity': int(quantity), 'amount': int(amount),
            'tax_percentage': '%.1f'%tax_percentage, 'tax_value': int(tax_value),
            'total_amount': amount + tax_value}
    return data

@fn_timer
def get_styles_data(user, product_styles, sku_master, start, stop, request, customer_id='', customer_data_id='', is_file='',
                    prices_dict={}, price_type='', custom_margin=0, specific_margins=[], is_margin_percentage=0,
                    stock_quantity=0, needed_stock_data={}, msp_min_price=0, msp_max_price=0):
    data = []
    style_quantities = eval(request.POST.get('required_quantity', '{}'))
    levels_config = get_misc_value('generic_wh_level', user.id)
    admin_user = get_admin(user)
    central_order_mgmt = get_misc_value('central_order_mgmt', user.id)
    sku_spl_attrs = {}
    get_values = ['wms_code', 'sku_desc', 'hsn_code', 'image_url', 'sku_class', 'cost_price', 'price', 'mrp', 'id',
                  'sku_category', 'sku_brand', 'sku_size', 'style_name', 'sale_through', 'product_type']

    #To fix quantity based filter
    product_styles_filtered = []
    qty_dict_flag = False
    product_styles_tot_qty_map = {}
    if stock_quantity:
        for product in product_styles:
            total_quantity = 0
            prd_sku_codes = sku_master.filter(sku_class=product).only('sku_code').values_list('sku_code', flat=True)
            for prd_sku in prd_sku_codes:
                total_quantity += needed_stock_data['stock_objs'].get(prd_sku, 0)
                # total_quantity += needed_stock_data['asn_quantities'].get(prd_sku, 0)
                total_quantity = total_quantity - float(needed_stock_data['reserved_quantities'].get(prd_sku, 0))
                total_quantity = total_quantity - float(needed_stock_data['enquiry_res_quantities'].get(prd_sku, 0))
            if total_quantity >= int(stock_quantity):
                product_styles_filtered.append(product)
            product_styles_tot_qty_map[product] = total_quantity
        qty_dict_flag = True
    else:
        product_styles_filtered = product_styles
    for product in product_styles_filtered[start: stop]:
        prd_sku_codes = sku_master.filter(sku_class=product).only('sku_code').values_list('sku_code', flat=True)
        sku_object = sku_master.filter(user=user.id, sku_class=product)
        sku_styles = sku_object.values('image_url', 'sku_class', 'sku_desc', 'sequence', 'id', 'sku_brand'). \
            order_by('-image_url')
        if central_order_mgmt == 'true':
            sku_id = sku_object[0].id
            sku_spl_attrs = dict(SKUAttributes.objects.filter(sku_id=sku_id).
                                 values_list('attribute_name', 'attribute_value'))
        if qty_dict_flag:
            total_quantity = product_styles_tot_qty_map[product]
        else:
            total_quantity = 0
            for prd_sku in prd_sku_codes:
                total_quantity += needed_stock_data['stock_objs'].get(prd_sku, 0)
                # total_quantity += needed_stock_data['asn_quantities'].get(prd_sku, 0)
                total_quantity = total_quantity - float(needed_stock_data['reserved_quantities'].get(prd_sku, 0))
                total_quantity = total_quantity - float(needed_stock_data['enquiry_res_quantities'].get(prd_sku, 0))
                total_quantity = total_quantity - float(needed_stock_data['nonkitted_stock'].get(prd_sku, 0))
        if total_quantity < 0:
            total_quantity = 0
        if sku_styles:
            sku_variants = list(sku_object.values(*get_values))
            for index, i in enumerate(sku_variants):
                sku_variants[index]['hsn_code'] = i['hsn_code']
            sku_variants = get_style_variants(sku_variants, user, customer_id, total_quantity=total_quantity,
                                              customer_data_id=customer_data_id, prices_dict=prices_dict,
                                              levels_config=levels_config, price_type=price_type,
                                              default_margin=custom_margin, specific_margins=specific_margins,
                                              is_margin_percentage=is_margin_percentage, needed_stock_data=needed_stock_data)
            sku_variants[0].update(sku_spl_attrs)
            sku_styles[0]['variants'] = sku_variants
            sku_styles[0]['style_quantity'] = total_quantity
            sku_styles[0]['asn_quantity'] = 0
            sku_styles[0]['blocked_qty'] = 0
            for prd_sku in prd_sku_codes:
                sku_styles[0]['asn_quantity'] += needed_stock_data['asn_quantities'].get(prd_sku, 0)
                stock_blk_qty = needed_stock_data['enquiry_res_quantities'].get(prd_sku, 0)
                intr_blk_qty = needed_stock_data['asn_blocked_quantities'].get(prd_sku, 0)
                sku_styles[0]['blocked_qty'] += stock_blk_qty + intr_blk_qty

            sku_styles[0]['image_url'] = resize_image(sku_styles[0]['image_url'], user)
            if style_quantities.get(sku_styles[0]['sku_class'], ''):
                sku_styles[0]['style_data'] = get_cal_style_data(sku_styles[0],\
                                              style_quantities[sku_styles[0]['sku_class']])
                # sku_styles[0]['tax_percentage'] = '%.1f'%tax_percentage
            else:
                tax = sku_styles[0]['variants'][0]['taxes']
                if tax:
                    tax = tax[0]
                    tax_percentage = float(tax['sgst_tax']) + float(tax['igst_tax']) + float(tax['cgst_tax'])
                    sku_styles[0]['tax_percentage'] = '%.1f'%tax_percentage

            is_prava_check = True
            if admin_user.username == 'isprava_admin' :
                if sku_styles[0]['style_quantity'] == 0 :
                    is_prava_check = False

            if total_quantity >= int(stock_quantity) and is_prava_check:
                if msp_min_price and msp_max_price:
                    if float(msp_min_price) <= sku_variants[0]['your_price'] <= float(msp_max_price):
                        data.append(sku_styles[0])
                else:
                    data.append(sku_styles[0])
        # if not is_file and len(data) >= 20:
        #     break
    return data


def save_image_file_path(path, image_file, image_name):
    if not os.path.exists(path):
        os.makedirs(path)
    extension = image_file.name.split('.')[-1]
    full_filename = os.path.join(path, str(image_name) + '.' + str(extension))
    fout = open(full_filename, 'wb+')
    file_content = ContentFile(image_file.read())

    try:
        # Iterate through the chunks.
        for chunk in file_content.chunks():
            fout.write(chunk)
        fout.close()
        image_url = '/' + path + '/' + str(image_name) + '.' + str(extension)
    except:
        image_url = ''
    return image_url


def folder_check(path):
    ''' Check and Create New Directory '''
    if not os.path.exists(path):
        os.makedirs(path)
    return True


@csrf_exempt
@login_required
@get_admin_user
def get_sku_stock_check(request, user=''):
    ''' Check and return sku level stock'''
    search_params = {'sku__user': user.id}
    if request.GET.get('sku_code', ''):
        search_params['sku__sku_code'] = request.GET.get('sku_code')
    if request.GET.get('location', ''):
        location_master = LocationMaster.objects.filter(zone__user=user.id, location=request.GET['location'])
        if not location_master:
            return HttpResponse(json.dumps({'status': 0, 'message': 'Invalid Location'}))
        search_params['location__location'] = request.GET.get('location')
    if request.GET.get('pallet_code', ''):
        search_params['pallet_detail__pallet_code'] = request.GET.get('pallet_code')
        stock_detail = StockDetail.objects.exclude(
            Q(receipt_number=0) | Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'])). \
            filter(location__location=request.GET.get('location', ''), sku__user=user.id,
                   sku__sku_code=search_params['sku__sku_code'],
                   pallet_detail__pallet_code=request.GET['pallet_code'])
        if not stock_detail:
            return HttpResponse(json.dumps({'status': 0, 'message': 'Invalid Location and Pallet code Combination'}))
    stock_data = StockDetail.objects.exclude(
        Q(receipt_number=0) | Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'])). \
        filter(**search_params)
    load_unit_handle = ''
    if stock_data:
        load_unit_handle = stock_data[0].sku.load_unit_handle
    else:
        return HttpResponse(json.dumps({'status': 0, 'message': 'No Stock Found'}))
    zones_data, available_quantity = get_sku_stock_summary(stock_data, load_unit_handle, user)
    avail_qty = sum(map(lambda d: available_quantity[d] if available_quantity[d] > 0 else 0, available_quantity))
    return HttpResponse(json.dumps({'status': 1, 'data': zones_data, 'available_quantity': avail_qty}))


def get_sku_stock_summary(stock_data, load_unit_handle, user):
    zones_data = {}
    pallet_switch = get_misc_value('pallet_switch', user.id)
    availabe_quantity = {}
    industry_type = user.userprofile.industry_type
    res_qty_dict = {}
    res_qty_objs = PicklistLocation.objects.filter(picklist__order__user=user.id,
                                                   stock_id__in=stock_data.values_list('id', flat=True), status=1).\
        only('stock_id', 'reserved')
    for res_qty_obj in res_qty_objs:
        res_qty_dict.setdefault(res_qty_obj.stock_id, 0)
        res_qty_dict[res_qty_obj.stock_id] += res_qty_obj.reserved
    for stock in stock_data:
        res_qty = res_qty_dict.get(stock.id, 0)

        raw_reserved = RMLocation.objects.filter(material_picklist__jo_material__material_code__user=user.id,
                                                 stock_id=stock.id, status=1).aggregate(Sum('reserved'))['reserved__sum']

        if not res_qty:
            res_qty = 0
        if raw_reserved:
            res_qty = float(res_qty) + float(raw_reserved)

        location = stock.location.location
        zone = stock.location.zone.zone
        pallet_number, batch, mrp, ean, weight = ['']*5
        if pallet_switch == 'true' and stock.pallet_detail:
            pallet_number = stock.pallet_detail.pallet_code
        if industry_type == "FMCG" and stock.batch_detail:
            batch_detail = stock.batch_detail
            batch = batch_detail.batch_no
            mrp = batch_detail.mrp
            weight = batch_detail.weight
            if batch_detail.ean_number:
                ean = batch_detail.ean_number
        cond = str((zone, location, pallet_number, batch, mrp, ean, weight))
        zones_data.setdefault(cond,
                              {'zone': zone, 'location': location, 'pallet_number': pallet_number, 'total_quantity': 0,
                               'reserved_quantity': 0, 'batch': batch, 'mrp': mrp, 'ean': ean,
                               'weight': weight})
        zones_data[cond]['total_quantity'] += stock.quantity
        zones_data[cond]['reserved_quantity'] += res_qty
        availabe_quantity.setdefault(location, 0)
        availabe_quantity[location] += (stock.quantity - res_qty)

    return zones_data, availabe_quantity


def check_ean_number(sku_code, ean_number, user):
    ''' Check ean number exists'''
    sku_ean_objs = SKUMaster.objects.filter(ean_number=ean_number, user=user.id).only('ean_number', 'sku_code')
    ean_objs = EANNumbers.objects.filter(sku__user=user.id, ean_number=ean_number)
    sku_ean_check = list(sku_ean_objs.exclude(sku_code=sku_code).values_list('sku_code', flat=True)[:2])
    ean_number_check = list(ean_objs.exclude(sku__sku_code=sku_code).values_list('sku__sku_code', flat=True)[:2])
    ean_check = []
    mapped_check = []
    ean_check.extend(sku_ean_check)
    ean_check.extend(ean_number_check)
    if sku_ean_objs.exists():
        mapped_check.append(sku_ean_objs[0].ean_number)
    if ean_objs.exists():
        mapped_check.append(ean_objs[0].ean_number)
    #if ean_check:
    #    status = 'Ean Number is already mapped for sku codes ' + ', '.join(ean_check)
    return ean_check, mapped_check


def get_seller_reserved_stocks(dis_seller_ids, sell_stock_ids, user):
    reserved_dict = OrderedDict()
    raw_reserved_dict = OrderedDict()
    for seller in dis_seller_ids:
        pick_params = {'status': 1, 'picklist__order__user': user.id}
        rm_params = {'status': 1, 'material_picklist__jo_material__material_code__user': user.id}
        stock_id_dict = filter(lambda d: d['seller__seller_id'] == seller, sell_stock_ids)
        if stock_id_dict:
            stock_ids = map(lambda d: d['stock_id'], stock_id_dict)
            pick_params['stock_id__in'] = stock_ids
            rm_params['stock_id__in'] = stock_ids
        reserved_dict[seller] = dict(PicklistLocation.objects.filter(**pick_params). \
                                     values_list('stock__sku__wms_code').distinct().annotate(reserved=Sum('reserved')))
        raw_reserved_dict[seller] = dict(RMLocation.objects.filter(**rm_params). \
                                         values('material_picklist__jo_material__material_code__wms_code').distinct(). \
                                         annotate(rm_reserved=Sum('reserved')))
    return reserved_dict, raw_reserved_dict


def get_sku_available_dict(user, sku_code='', location='', available=False):
    reserved_dict = OrderedDict()
    raw_reserved_dict = OrderedDict()
    pick_params = {'status': 1, 'picklist__order__user': user.id}
    rm_params = {'status': 1, 'material_picklist__jo_material__material_code__user': user.id}
    stock_params = {}
    if sku_code:
        stock_params['sku__sku_code'] = sku_code
        pick_params['stock__sku__sku_code'] = sku_code
        rm_params['stock__sku__sku_code'] = sku_code
    if location:
        stock_params['location__location'] = location
        pick_params['stock__location__location'] = location
        rm_params['stock__location__location'] = location
    all_stocks = dict(
        StockDetail.objects.exclude(Q(receipt_number=0) | Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'])). \
        filter(quantity__gt=0, **stock_params).values_list('sku__wms_code').distinct(). \
        annotate(reserved=Sum('quantity')))
    pick_params = {'status': 1, 'picklist__order__user': user.id}
    rm_params = {'status': 1, 'material_picklist__jo_material__material_code__user': user.id}
    reserved_dict = dict(PicklistLocation.objects.filter(**pick_params). \
                         values_list('stock__sku__wms_code').distinct().annotate(reserved=Sum('reserved')))
    raw_reserved_dict = dict(RMLocation.objects.filter(**rm_params). \
                             values('material_picklist__jo_material__material_code__wms_code').distinct(). \
                             annotate(rm_reserved=Sum('reserved')))
    if available:
        avail_stock = all_stocks.get(sku_code, 0) - pick_params.get(sku_code, 0) - rm_params.get(sku_code, 0)
        return avail_stock
    return all_stocks, reserved_dict, raw_reserved_dict


def get_order_detail_objs(order_id, user, search_params={}, all_order_objs=[]):
    search_param = copy.deepcopy(search_params)
    if not search_param.has_key('user') and not search_param.has_key('user__in'):
        search_param['user'] = user.id
    if not all_order_objs:
        all_order_objs = OrderDetail.objects.filter(user=user.id)
    order_id_search = ''.join(re.findall('\d+', order_id))
    order_code_search = ''.join(re.findall('\D+', order_id))
    order_detail_objs = OrderDetail.objects.filter(Q(order_id=order_id_search, order_code=order_code_search) |
                                                   Q(original_order_id=order_id), **search_param)
    return order_detail_objs


def order_cancel_functionality(order_det_ids):
    ord_det_qs = OrderDetail.objects.filter(id__in=order_det_ids)
    for order_det in ord_det_qs:
        if int(order_det.status) == 1:
            order_det.status = 3
            order_det.save()
        else:
            picklists = Picklist.objects.filter(order_id=order_det.id)
            for picklist in picklists:
                if picklist.picked_quantity <= 0:
                    picklist.delete()
                elif picklist.stock:
                    cancel_location = CancelledLocation.objects.filter(picklist_id=picklist.id,
                                                                       picklist__order_id=order_det.id)
                    if not cancel_location:
                        CancelledLocation.objects.create(picklist_id=picklist.id,
                                                         quantity=picklist.picked_quantity,
                                                         location_id=picklist.stock.location_id,
                                                         creation_date=datetime.datetime.now(), status=1)
                        picklist.status = 'cancelled'
                        picklist.save()
                else:
                    picklist.status = 'cancelled'
                    picklist.save()
            order_det.status = 3
            order_det.save()


@csrf_exempt
@get_admin_user
def check_labels(request, user=''):
    status = {}
    label = request.GET.get('label', '')
    filter_params = {'order__user': user.id}
    if not label:
        status = {'message': 'Please send label', 'data': {}}
    if not status:
        filter_params['label'] = label
        picklist_number = request.GET.get('picklist_number', '')
        if picklist_number:
            filter_params['picklist__picklist_number'] = picklist_number
        order_labels = OrderLabels.objects.filter(**filter_params)
        data = {}
        if order_labels:
            order_label = order_labels[0]
            if int(order_label.status) == 1:
                data = {'label': order_label.label, 'sku_code': order_label.order.sku.sku_code,
                        'order_id': order_label.order.order_id}
                status = {'message': 'Success', 'data': data}
            else:
                status = {'message': 'Label already processed', 'data': data}
        else:
            status = {'message': 'Invalid Label', 'data': {}}
    return HttpResponse(json.dumps(status, cls=DjangoJSONEncoder))


def get_po_reference(order):
    po_number = '%s%s_%s' % (order.prefix, str(order.creation_date).split(' ')[0].replace('-', ''), order.order_id)
    return po_number


@csrf_exempt
@get_admin_user
def get_imei_data(request, user=''):
    status = {}
    imei = request.GET.get('imei')
    if not imei:
        return HttpResponse(json.dumps({'imei': imei, 'message': 'Please scan imei number'}))
    po_imei_mapping = POIMEIMapping.objects.filter(sku__user=user.id,
                                                   imei_number=imei).order_by('creation_date')
    if not po_imei_mapping:
        return HttpResponse(json.dumps({'imei': imei, 'message': 'Invalid IMEI Number'}))
    data = []
    imei_status = ''
    stock_skus = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0).values_list('sku__sku_code',
                                                                                           flat=True).distinct()
    sku_details = {}
    log.info('Get IMEI Tracker History data for ' + user.username + ' is ' + str(request.GET.dict()))
    format_types = {}
    for i in BarcodeSettings.objects.filter(user=request.user).order_by('-format_type'):
        if i.size:
            try:
                size = "%sX%s" % eval(i.size)
            except:
                size = i.size
            format_t = "_".join([i.format_type, size])
            format_types.update({format_t: i.format_type})
    try:
        for index, po_mapping in enumerate(po_imei_mapping):
            imei_data = {}
            sku = po_mapping.sku
            if po_mapping.purchase_order:
                purchase_order = po_mapping.purchase_order
                if not sku_details:
                    sku_details = {'sku_code': sku.sku_code, 'sku_desc': sku.sku_desc, 'sku_category': sku.sku_category,
                                   'image_url': sku.image_url}
                imei_data['po_details'] = {'po_number': get_po_reference(purchase_order),
                                           'supplier_id': purchase_order.open_po.supplier_id,
                                           'supplier_name': purchase_order.open_po.supplier.name,
                                           'received_date': get_local_date(user, po_mapping.creation_date),
                                           'supplier_address': purchase_order.open_po.supplier.address}
            elif po_mapping.job_order:
                job_order = po_mapping.job_order
                if not sku_details:
                    sku_details = {'sku_code': sku.sku_code, 'sku_desc': sku.sku_desc, 'sku_category': sku.sku_category,
                                   'image_url': sku.image_url}
                imei_data['jo_details'] = {'jo_number': job_order.job_code,
                                           'jo_creation_date': get_local_date(user, job_order.creation_date),
                                           'received_date': get_local_date(user, po_mapping.creation_date)}
                jo_materials = job_order.jomaterial_set.filter()
                imei_data['rm_picklist_data'] = []
                for jo_material in jo_materials:
                    jo_imeis = list(jo_material.orderimeimapping_set.filter().values_list('po_imei__imei_number', flat=True))
                    imei_data['rm_picklist_data'].append({'sku_code': jo_material.material_code.sku_code,
                                                          'sku_desc': jo_material.material_code.sku_desc,
                                                          'required_quantity': jo_material.material_quantity,
                                                          'imeis': jo_imeis})

            order_mappings = OrderIMEIMapping.objects.filter(po_imei_id=po_mapping.id, sku__user=user.id).order_by(
                '-creation_date')
            if not order_mappings:
                data.append(imei_data)
                if sku.sku_code in stock_skus:
                    imei_status = 'Available'
                continue
            if order_mappings:
                order_mapping = order_mappings[0]
                if order_mapping.order:
                    order_id = order_mapping.order.original_order_id
                    if not order_id:
                        order_id = str(order_mapping.order.order_code) + str(order_mapping.order.order_id)
                    if order_mapping.order_reference:
                        order_id = order_mapping.order_reference

                    customer_id = order_mapping.order.customer_id
                    customer_name = order_mapping.order.customer_name
                    customer_address = order_mapping.order.address
                    if customer_id:
                        customer_master = CustomerMaster.objects.filter(customer_id=order_mapping.order.customer_id,
                                                                        user=user.id)
                        if customer_master:
                            customer_name = customer_master[0].name
                            customer_address = customer_master[0].address
                    imei_data['order_details'] = {'order_id': order_id,
                                                  'order_date': get_local_date(user, order_mapping.order.creation_date),
                                                  'customer_id': str(customer_id), 'customer_name': customer_name,
                                                  'customer_address': customer_address,
                                                  'dispatch_date': get_local_date(user, order_mapping.creation_date),
                                                  'order_reference': order_mapping.order_reference,
                                                  'order_marketplace': order_mapping.marketplace
                                                  }
                    return_mapping = ReturnsIMEIMapping.objects.filter(order_imei_id=order_mapping.id,
                                                                       order_imei__order__user=user.id)
                    if not return_mapping:
                        data.append(imei_data)
                        imei_status = 'Dispatched'
                        continue
                    return_mapping = return_mapping[0]
                    imei_data['return_details'] = {'return_id': return_mapping.order_return.return_id,
                                                   'return_date': get_local_date(user,
                                                                                 return_mapping.order_return.creation_date),
                                                   'customer_id': str(customer_id), 'customer_name': customer_name,
                                                   'customer_address': customer_address,
                                                   'reason': return_mapping.order_return.reason}
                    imei_status = 'Returned'
                    data.append(imei_data)
                elif order_mapping.jo_material:
                    jo_material = order_mapping.jo_material
                    imei_data['jo_rm_details'] = {'job_code': jo_material.job_order.job_code,
                                                  'product_sku_code': jo_material.job_order.product_code.sku_code,
                                                  'product_sku_desc': jo_material.job_order.product_code.sku_desc,
                                                  'order_date': get_local_date(user, jo_material.job_order.creation_date),
                                                  'dispatch_date': get_local_date(user, order_mapping.creation_date),
                                                  }
                    data.append(imei_data)
                    imei_status = 'Consumed'
                elif order_mapping.stock_transfer:
                    stock_transfer = order_mapping.stock_transfer
                    if stock_transfer.st_po.open_st.sku.user:
                        destination_user_id = stock_transfer.st_po.open_st.sku.user
                        warehouse_user = User.objects.get(id=destination_user_id)
                    imei_data['stock_transfer'] = {'stock_transfer_id': stock_transfer.order_id,
                                                   'order_date': get_local_date(user, order_mapping.creation_date),
                                                   'warehouse': warehouse_user.username,
                                                   'address' : warehouse_user.userprofile.address,
                                                   }
                    data.append(imei_data)
                    imei_status = 'Transfered'
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        result_data = []
        log.info('Get IMEI Tracker History Data failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.GET.dict()), str(e)))
    status = {'imei': imei, 'sku_details': sku_details, 'imei_status': imei_status, 'data': data, 'format_types': format_types, 'message': 'Success'}
    return HttpResponse(json.dumps(status))


def generate_barcode_dict(pdf_format, myDicts, user):
    barcode_pdf_dict = {}
    barcodes_list = []
    barcode_mapping_dict = {'Size': 'sku_size', 'Brand': 'sku_brand', 'SKUDes': 'sku_desc',
                            'UOM': 'measurement_type', 'Style': 'style_name', 'Color': 'color',
                            'DesignNo': 'sku_class', 'MRP': 'mrp',
                            'SKUDes/Prod': 'sku_desc', 'Price': 'price'}
    user_prf = UserProfile.objects.filter(user_id=user.id)[0]
    barcode_opt = get_misc_value('barcode_generate_opt', user.id)
    attribute_names = get_user_attributes(user, 'sku').values_list('attribute_name', flat=True)
    format_type = "_".join(pdf_format.split("_")[:-1]) if "_" in pdf_format else (1, '60X30')
    barcode_formats = BarcodeSettings.objects.filter(user=user_prf.user, format_type=str(format_type))
    mapping_fields = {}
    show_fields = []
    if barcode_formats:
        if barcode_formats[0].show_fields:
            show_fields = eval(barcode_formats[0].show_fields)
        if barcode_formats[0].mapping_fields:
            mapping_fields = eval(barcode_formats[0].mapping_fields)
    if isinstance(myDicts, dict):
        myDicts = [myDicts]
    for myDict in myDicts:
        if isinstance(myDict['wms_code'], list):
            for ind in range(0, len(myDict['wms_code'])):
                sku = myDict['wms_code'][ind]
                quant = myDict['quantity'][ind]
                label = ''
                if myDict.has_key('label'):
                    label = myDict['label'][ind]
                single = {}
                if sku and quant:
                    if sku.isdigit():
                        sku_data = SKUMaster.objects.filter(Q(ean_number=sku) | Q(wms_code=sku), user=user.id)
                    else:
                        sku_data = SKUMaster.objects.filter(sku_code=sku, user=user.id)
                    if not sku_data:
                        continue
                    sku_data = sku_data[0]
                    single.update()
                    single['SKUCode'] = sku if sku else label
                    single['Label'] = label if label else sku
                    if barcode_opt == 'sku_ean' :
                        if sku_data.ean_number:
                            single['Label'] = str(sku_data.ean_number)
                        elif  EANNumbers.objects.filter(sku__id = sku_data.id).exists():
                            single['Label'] = EANNumbers.objects.filter(sku__id=sku_data.id)[0].ean_number
                    single['SKUPrintQty'] = quant
                    if myDict.get('mfg_date', ''):
                        single['mfg_date'] = myDict['mfg_date'][ind]
                    for show_keys1 in show_fields:
                        show_keys2 = [show_keys1]
                        if isinstance(show_keys1, list):
                            show_keys2 = copy.deepcopy(show_keys1)
                        for show_key in show_keys2:
                            show_key = show_key.split('/')[0]
                            if show_key in barcode_mapping_dict.keys():
                                single[show_key] = str(getattr(sku_data, barcode_mapping_dict[show_key]))
                                if barcode_mapping_dict[show_key] == 'sku_desc':
                                    single[show_key] = sku_data.sku_desc[0:24].replace("'", '') + '...'
                            elif show_key in mapping_fields.keys():
                                single[show_key] = str(getattr(sku_data, mapping_fields[show_key]))
                                if mapping_fields[show_key] == 'sku_desc':
                                    single[show_key] = sku_data.sku_desc[0:24].replace("'", '') + '...'
                            else:
                                attr_obj = sku_data.skuattributes_set.filter(attribute_name=show_key)
                                if attr_obj.exists():
                                    single[show_key] = attr_obj[0].attribute_value
                single['Company'] = user_prf.company_name.replace("'", '')
                present = get_local_date(user, datetime.datetime.now(), send_date=True).strftime("%b %Y")
                single["Packed on"] = str(present).replace("'", '')
                single['Marketed By'] = user_prf.company_name.replace("'", '')
                single['MFD'] = str(present).replace("'", '')
                phone_number = user_prf.phone_number
                if not phone_number:
                    phone_number = ''
                single['Contact No'] = phone_number
                single['Email'] = user.email
                order_label = OrderLabels.objects.filter(label=single['Label'], order__user=user.id)

                if order_label:
                    order_label = order_label[0]
                    single["Vendor SKU"] = order_label.vendor_sku
                    single["SKUCode"] = order_label.item_sku
                    single['MRP'] = order_label.mrp
                    single['Phone'] = user_prf.phone_number
                    single['Email'] = user.email
                    single["PO No"] = order_label.order.original_order_id
                    single['Color'] = order_label.color.replace("'", '')
                    single['Size'] = str(order_label.size).replace("'", '')
                    single['Customer Name'] = order_label.order.customer_name
                    single['Customer Address'] = order_label.order.address
                    single['Customer Telephone'] = order_label.order.telephone
                    single['Customer Email'] = order_label.order.email_id
                    if not single["PO No"]:
                        single["PO No"] = str(order_label[0].order.order_code) + str(order_label[0].order.order_id)
                c_id = ''
                if single.has_key('Customer Id') and single.get('Customer Id', ''):
                    c_id = single.get('Customer Id')
                if single.has_key('customer_id') and single.get('customer_id', ''):
                    c_id = single.get('customer_id')
                if c_id:
                    c_details = CustomerMaster.objects.filter(customer_id=c_id, user=user.id)
                    single['Customer Name'] = c_details[0].name if c_details else ''
                    single['Customer Address'] = c_details[0].address if c_details else ''
                    single['Customer Telephone'] = c_details[0].phone_number if c_details else ''
                    single['Customer Email'] = c_details[0].email_id if c_details else ''

                address = user_prf.address
                if BARCODE_ADDRESS_DICT.get(user.username, ''):
                    address = BARCODE_ADDRESS_DICT.get(user.username)
                single['Manufactured By'] = address.replace("'", '')
                if "bulk" in pdf_format.lower():
                    single['Qty'] = single['SKUPrintQty']
                    single['SKUPrintQty'] = "1"

                barcodes_list.append(single)

        elif myDict.has_key('imei'):
            single = myDict
            single['SKUPrintQty'] = "1"
            single['Label'] = myDict['imei']
            if single['wms_code']:
                single.pop('wms_code')
            barcodes_list.append(single)

        else:
        #for ind in range(0, len(myDict['wms_code'])):
            sku = myDict['wms_code']
            quant = myDict['quantity']
            label = ''
            if myDict.has_key('label'):
                label = myDict['label']
            single = myDict
            if sku and quant:
                if sku.isdigit():
                    sku_data = SKUMaster.objects.filter(Q(ean_number=sku) | Q(wms_code=sku), user=user.id)
                else:
                    sku_data = SKUMaster.objects.filter(sku_code=sku, user=user.id)
                if not sku_data:
                    continue
                sku_data = sku_data[0]
                single.update()
                single['SKUCode'] = sku if sku else label
                single['Label'] = label if label else sku
                if barcode_opt == 'sku_ean' and sku_data.ean_number:
                    single['Label'] = str(sku_data.ean_number)
                if barcode_opt == 'sku_pack' :
                    single['Label'] = myDict['pack_id']
                    single['pack_id'] = myDict['pack_id']
                single['SKUPrintQty'] = quant
                for show_keys1 in show_fields:
                    show_keys2 = [show_keys1]
                    if isinstance(show_keys1, list):
                        show_keys2 = copy.deepcopy(show_keys1)
                    for show_key in show_keys2:
                        show_key = show_key.split('/')[0]
                        if show_key in barcode_mapping_dict.keys():
                            single[show_key] = str(getattr(sku_data, barcode_mapping_dict[show_key]))
                            if barcode_mapping_dict[show_key] == 'sku_desc':
                                single[show_key] = sku_data.sku_desc[0:24].replace("'", '') + '...'
                        elif show_key in mapping_fields.keys():
                            single[show_key] = str(getattr(sku_data, mapping_fields[show_key]))
                            if mapping_fields[show_key] == 'sku_desc':
                                single[show_key] = sku_data.sku_desc[0:24].replace("'", '') + '...'
                        else:
                            attr_obj = sku_data.skuattributes_set.filter(attribute_name=show_key)
                            if attr_obj.exists():
                                single[show_key] = attr_obj[0].attribute_value
            single['Company'] = user_prf.company_name.replace("'", '')
            present = get_local_date(user, datetime.datetime.now(), send_date=True).strftime("%b %Y")
            single["Packed on"] = str(present).replace("'", '')
            single['Marketed By'] = user_prf.company_name.replace("'", '')
            single['MFD'] = str(present).replace("'", '')
            phone_number = user_prf.phone_number
            if not phone_number:
                phone_number = ''
            single['Contact No'] = phone_number
            single['Email'] = user.email
            order_label = OrderLabels.objects.filter(label=single['Label'], order__user=user.id)

            if order_label:
                order_label = order_label[0]
                single["Vendor SKU"] = order_label.vendor_sku
                single["SKUCode"] = order_label.item_sku
                single['MRP'] = order_label.mrp
                single['Phone'] = user_prf.phone_number
                single['Email'] = user.email
                single["PO No"] = order_label.order.original_order_id
                single['Color'] = order_label.color.replace("'", '')
                single['Size'] = str(order_label.size).replace("'", '')
                single['Customer Name'] = order_label.order.customer_name
                single['Customer Address'] = order_label.order.address
                single['Customer Telephone'] = order_label.order.telephone
                single['Customer Email'] = order_label.order.email_id
                if not single["PO No"]:
                    single["PO No"] = str(order_label[0].order.order_code) + str(order_label[0].order.order_id)
            c_id = ''
            if single.has_key('Customer Id') and single.get('Customer Id', ''):
                c_id = single.get('Customer Id')
            if single.has_key('customer_id') and single.get('customer_id', ''):
                c_id = single.get('customer_id')
            if c_id:
                c_details = CustomerMaster.objects.filter(customer_id=c_id, user=user.id)
                single['Customer Name'] = c_details[0].name if c_details else ''
                single['Customer Address'] = c_details[0].address if c_details else ''
                single['Customer Telephone'] = c_details[0].phone_number if c_details else ''
                single['Customer Email'] = c_details[0].email_id if c_details else ''
            address = user_prf.address
            if BARCODE_ADDRESS_DICT.get(user.username, ''):
                address = BARCODE_ADDRESS_DICT.get(user.username)
            single['Manufactured By'] = address.replace("'", '')
            if "bulk" in pdf_format.lower():
                single['Qty'] = single['SKUPrintQty']
                single['SKUPrintQty'] = "1"
            barcodes_list.append(single)
    log.info(barcodes_list)
    return get_barcodes(make_data_dict(barcodes_list, user_prf, pdf_format))


def make_data_dict(barcodes_list, user_prf, pdf_format):
    format_type = "_".join(pdf_format.split("_")[:-1]) if "_" in pdf_format else (1, '60X30')
    if format_type:
        objs = BarcodeSettings.objects.filter(user=user_prf.user, format_type=str(format_type))
        if objs:
            data_dict = {'customer': user_prf.user.username,
                         'info': barcodes_list,
                         'type': objs[0].format_type if objs[0].format_type else settings.BARCODE_DEFAULT.get(
                             'format_type'),
                         'size': eval(objs[0].size) if objs[0].size else settings.BARCODE_DEFAULT.get('size'),
                         'show_fields': eval(objs[0].show_fields) if objs[
                             0].show_fields else settings.BARCODE_DEFAULT.get('show_fields'),
                         'rows_columns': eval(objs[0].rows_columns) if objs[
                             0].rows_columns else settings.BARCODE_DEFAULT.get('rows_columns'),
                         'styles': eval(objs[0].styles) if objs[0].styles not in (
                         '{}', '', None) else settings.BARCODE_DEFAULT.get('styles'),
                         'format_type': pdf_format,
                         }
            return data_dict
    data_dict = {'customer': user_prf.user.username, 'info': barcodes_list}
    data_dict.update(settings.BARCODE_DEFAULT)
    if data_dict['info']:
        if data_dict['info'][0].has_key('imei'):
            data_dict['show_fields'] = []
    return data_dict


def barcode_service(key, data_to_send, format_name=''):
    url = 'http://sandhani-001-site1.htempurl.com/Webservices/BarcodeServices.asmx/GetBarCode'
    payload = ''
    if data_to_send:
        if format_name == 'format3':
            payload = {'argJsonData': json.dumps(data_to_send), 'argCompany': 'Adam', 'argBarcodeFormate': key}
        elif format_name == 'format4':
            payload = {'argJsonData': json.dumps(data_to_send), 'argCompany': 'Campus_Sutra', 'argBarcodeFormate': key}
        elif format_name == 'Bulk Barcode':
            payload = {'argJsonData': json.dumps(data_to_send), 'argCompany': 'Scholar_Clothing',
                       'argBarcodeFormate': key}
        else:
            payload = {'argJsonData': json.dumps(data_to_send), 'argCompany': 'Brilhante', 'argBarcodeFormate': key}

    r = post(url, data=payload)
    if ('<string xmlns="http://tempuri.org/">' in r.text) and ('</string>' in r.text):
        token_value = r.text.split('<string xmlns="http://tempuri.org/">')[1].split('</string>')[0]
        pdf_url = 'data:application/pdf;base64,' + token_value
        return pdf_url
    else:
        pdf_url = ''


def get_purchase_order_data(order):
    order_data = {}
    status_dict = PO_ORDER_TYPES
    rw_purchase = RWPurchase.objects.filter(purchase_order_id=order.id)
    st_order = STPurchaseOrder.objects.filter(po_id=order.id)
    temp_wms = ''
    unit = ""
    gstin_number = ''
    intransit_quantity = 0
    if 'job_code' in dir(order):
        order_data = {'wms_code': order.product_code.wms_code, 'sku_group': order.product_code.sku_group,
                      'sku': order.product_code,
                      'supplier_code': '', 'load_unit_handle': order.product_code.load_unit_handle,
                      'sku_desc': order.product_code.sku_desc,'sku_brand':order.product_code.sku_brand,
                      'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0, 'apmc_tax': 0, 'tin_number': '',
                      'intransit_quantity': intransit_quantity, 'shelf_life': order.product_code.shelf_life,
                      'show_imei': order.product_code.enable_serial_based}
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
        mrp = 0
        supplier_code = ''
        cgst_tax = 0
        sgst_tax = 0
        igst_tax = 0
        utgst_tax = 0
        apmc_tax = 0
        cess_tax = 0
        tin_number = ''
    elif order.open_po:
        open_data = order.open_po
        user_data = order.open_po.supplier
        address = user_data.address
        email_id = user_data.email_id
        username = user_data.name
        order_quantity = open_data.order_quantity
        intransit_quantity = order.intransit_quantity
        sku = open_data.sku
        price = open_data.price
        mrp = open_data.mrp
        user_profile = UserProfile.objects.get(user_id=sku.user)
        if user_profile.user_type == 'warehouse_user':
            mrp = sku.mrp
        unit = open_data.measurement_unit
        order_type = status_dict[order.open_po.order_type]
        supplier_code = open_data.supplier_code
        gstin_number = order.open_po.supplier.tin_number
        cgst_tax = open_data.cgst_tax
        sgst_tax = open_data.sgst_tax
        igst_tax = open_data.igst_tax
        utgst_tax = open_data.utgst_tax
        cess_tax = open_data.cess_tax
        apmc_tax = open_data.apmc_tax
        tin_number = open_data.supplier.tin_number
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
        mrp = 0
        order_type = ''
        supplier_code = ''
        cgst_tax = 0
        sgst_tax = 0
        igst_tax = 0
        utgst_tax = 0
        cess_tax = 0
        apmc_tax = 0
        tin_number = ''
    order_data = {'order_quantity': order_quantity, 'price': price, 'mrp': mrp,'wms_code': sku.wms_code,
                  'sku_code': sku.sku_code, 'sku_brand':sku.sku_brand,'supplier_id': user_data.id, 'zone': sku.zone,
                  'qc_check': sku.qc_check, 'supplier_name': username, 'gstin_number': gstin_number,
                  'sku_desc': sku.sku_desc, 'address': address, 'unit': unit, 'load_unit_handle': sku.load_unit_handle,
                  'phone_number': user_data.phone_number, 'email_id': email_id,
                  'sku_group': sku.sku_group, 'sku_id': sku.id, 'sku': sku, 'temp_wms': temp_wms,
                  'order_type': order_type,
                  'supplier_code': supplier_code, 'cgst_tax': cgst_tax, 'sgst_tax': sgst_tax, 'igst_tax': igst_tax,
                  'utgst_tax': utgst_tax, 'cess_tax':cess_tax, 'apmc_tax': apmc_tax,
                  'intransit_quantity': intransit_quantity,
                  'tin_number': tin_number, 'shelf_life': sku.shelf_life, 'show_imei': sku.enable_serial_based }

    return order_data


def check_get_imei_details(imei, wms_code, user_id, check_type='', order='', job_order=''):
    status = ''
    data = {}
    po_mapping = []
    log.info('Get IMEI Details data for user id ' + str(user_id) + ' for imei ' + str(imei))
    try:
        if check_type == 'purchase_check':
            status = get_serial_limit(user_id, imei)
            if status:
                return po_mapping, status, data
        check_params = {'imei_number': imei, 'sku__user': user_id}
        #st_purchase = STPurchaseOrder.objects.filter(open_st__sku__user=user_id, open_st__sku__wms_code=wms_code). \
        #    values_list('po_id', flat=True)
        #check_params1 = {'imei_number': imei, 'purchase_order_id__in': st_purchase}

        po_mapping = POIMEIMapping.objects.filter(**check_params)
        #mapping = POIMEIMapping.objects.filter(**check_params1)
        #po_mapping = po_mapping | mapping
        po_mapping = po_mapping.order_by('-creation_date')
        if po_mapping:
            #order_data = get_purchase_order_data(po_mapping[0].purchase_order)
            order_wms_code = po_mapping[0].sku.wms_code
            order_imei_mapping = OrderIMEIMapping.objects.filter(po_imei_id=po_mapping[0].id, status=1)
            if check_type == 'purchase_check':
                order_imei_mapping = OrderIMEIMapping.objects.filter(po_imei_id=po_mapping[0].id, status=1)

                if po_mapping[0].status == 1 and not order_imei_mapping:
                    if po_mapping[0].purchase_order:
                        purchase_order_id = get_po_reference(po_mapping[0].purchase_order)
                        status = '%s is already mapped with purchase_order %s' % (str(imei), purchase_order_id)
                    elif po_mapping[0].job_order:
                        status = '%s is already mapped with job order %s' % (str(imei),
                                                                             str(po_mapping[0].job_order.job_code))
                    else:
                        status = '%s is already in Stock' % str(imei)
                elif not (order_wms_code == wms_code):
                    status = '%s will only maps with %s' % (str(imei), order_wms_code)
            elif check_type == 'order_mapping':
                if not wms_code:
                    wms_code = order_wms_code
                elif not (order_wms_code == wms_code):
                    status = '%s will only maps with %s' % (str(imei), order_wms_code)
                data['wms_code'] = wms_code
                if order_imei_mapping:
                    status = validate_order_imei_mapping_status(imei, order_imei_mapping, order, job_order)
            elif check_type == 'shipped_check':
                order_imei_mapping = OrderIMEIMapping.objects.filter(po_imei_id=po_mapping[0].id, status=1)
                if order_imei_mapping:
                    data['order_imei_obj'] = order_imei_mapping[0]
        elif not po_mapping and check_type == 'order_mapping':
            status = str(imei) + ' is invalid Imei number'
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        po_mapping = None
        status = 'Get IMEI details Failed'
        log.info('Get IMEI details Data failed for user id %s for imei %s and error statement is %s' % (
        str(user_id), str(imei), str(e)))

    return po_mapping, status, data


def update_seller_order(seller_order_dict, order, user):
    seller_orders = SellerOrder.objects.filter(sor_id=seller_order_dict['sor_id'], order_id=order.id,
                                               seller__user=user.id)
    for seller_order in seller_orders:
        seller_order.order_status = seller_order_dict.get('order_status', '')
        seller_order.status = 1
        seller_order.save()


def get_invoice_html_data(invoice_data):
    show_mrp = invoice_data.get('show_mrp', 'false')
    show_sno = invoice_data.get('show_sno', 'false')
    data = {'totals_data': {'label_width': 6, 'value_width': 6}, 'columns': 11, 'emty_tds': [], 'hsn_summary_span': 3}
    if show_mrp == 'true':
        data['columns'] += 1
    if show_sno == 'true' :
        data['columns'] += 1
    if invoice_data.get('is_cess_tax_flag', '') == 'false':
        data['columns'] -= 1
    if invoice_data.get('invoice_remarks', '') not in ['false', '']:
        data['totals_data']['label_width'] = 4
        data['totals_data']['value_width'] = 8

    if invoice_data.get('show_disc_invoice', '') == 'true':
        data['columns'] += 1
        data['hsn_summary_span'] = 4
    data['empty_tds'] = [i for i in range(data['columns'])]
    return data

def build_invoice(invoice_data, user, css=False):
    # it will create invoice template
    user_profile = UserProfile.objects.get(user_id=user.id)
    if not (not invoice_data['detailed_invoice'] and invoice_data['is_gst_invoice']):
        return json.dumps(invoice_data, cls=DjangoJSONEncoder)
    titles = ['']
    import math
    if not (invoice_data.get("customer_invoice", "") == True):
        title_dat = get_misc_value('invoice_titles', user.id)
        if not title_dat == 'false':
            titles = title_dat.split(",")
    invoice_data['html_data'] = get_invoice_html_data(invoice_data)
    invoice_data['user_type'] = user_profile.user_type
    invoice_data['titles'] = titles
    perm_hsn_summary = get_misc_value('hsn_summary', user.id)
    invoice_data['perm_hsn_summary'] = str(perm_hsn_summary)
    if len(invoice_data['hsn_summary'].keys()) == 0:
        invoice_data['perm_hsn_summary'] = 'false'
    # invoice_data['html_data']['empty_tds'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    invoice_height = 1358
    if 'side_image' in invoice_data.keys() and 'top_image' in invoice_data.keys():
        if not invoice_data['side_image'] and invoice_data['top_image']:
            invoice_height = 1250
        if not invoice_data['top_image'] and invoice_data['side_image']:
            invoice_height = 1358
    inv_height = invoice_height  # total invoice height
    inv_details = 317  # invoice details height
    inv_footer = 95  # invoice footer height
    inv_totals = 127  # invoice totals height
    inv_header = 47  # invoice tables headers height
    inv_product = 47  # invoice products cell height
    inv_summary = 47  # invoice summary headers height
    inv_total = 27  # total display height
    inv_charges = 20  # height of other charges
    inv_totals = inv_totals + len(invoice_data['order_charges']) * inv_charges
    '''
    if invoice_data['user_type'] == 'marketplace_user':
        inv_details = 142
        s_count = invoice_data['seller_address'].count('\n')
        s_count = s_count - 4
        b_count = invoice_data['customer_address'].count('\n')
        b_count = b_count - 4
        s_count = s_count if s_count > b_count else b_count
        if s_count > 0:
            inv_details = inv_details + (20*s_count)
        else:
            inv_details = inv_details + 20
        inv_details = 230
    '''
    render_data = []
    render_space = 0
    hsn_summary_length = len(invoice_data['hsn_summary'].keys()) * inv_total
    if (perm_hsn_summary == 'true'):
        render_space = inv_height - (
        inv_details + inv_footer + inv_totals + inv_header + inv_summary + inv_total + hsn_summary_length)
    else:
        render_space = inv_height - (inv_details + inv_footer + inv_totals + inv_header + inv_total)
    no_of_skus = int(render_space / inv_product)
    data_length = len(invoice_data['data'])
    data_value = 0
    no_of_sku_count = 0
    if get_misc_value('show_imei_invoice', user.id) == 'false':
        invoice_data['imei_data'] = []
        for data in invoice_data['data']:
            data['imeis'] = []
    if invoice_data['imei_data']:
        count = 0
        for imei in invoice_data['imei_data']:
            for imei_count in range(len(imei)+1):
                imei_count
            count+=imei_count
        if count == data_length:
            pass
        else:
            no_of_sku_count = int(count/2)
        if no_of_sku_count:
            if no_of_sku_count + data_length > 14:
                data_value = 1
                data_length = no_of_sku_count + data_length

    '''
    if user.username in top_logo_users:
        no_of_skus -= 2
    if data_length == 1:
        no_of_skus += 2
    '''
    invoice_data['empty_data'] = []
    if data_length >= no_of_skus:

        needed_space = inv_footer + inv_footer + inv_total
        if perm_hsn_summary == 'true':
            needed_space = needed_space + inv_summary + hsn_summary_length
        temp_render_space = 0
        temp_render_space = inv_height - (inv_details + inv_header)
        temp_no_of_skus = int(temp_render_space / inv_product)
        number_of_pages = int(math.ceil(float(data_length) / temp_no_of_skus))
        if data_value :
            number_of_pages = number_of_pages + 1
        for i in range(number_of_pages):
            temp_page = {'data': invoice_data['data'][i * temp_no_of_skus: (i + 1) * temp_no_of_skus], 'empty_data': []}
            render_data.append(temp_page)
        if int(math.ceil(float(data_length) / temp_no_of_skus)) == 0:
            temp_page = {'data': invoice_data['data'], 'empty_data': []}
            render_data.append(temp_page)
        last = len(render_data) - 1
        data_length = len(render_data[last]['data'])

        if no_of_skus < data_length:
            render_data.append({'empty_data': [], 'data': [render_data[last]['data'][data_length - 1]]})
            render_data[last]['data'] = render_data[last]['data'][:data_length - 1]

        last = len(render_data) - 1
        data_length = len(render_data[last]['data'])
        empty_data = [""] * (no_of_skus - data_length)
        render_data[last]['empty_data'] = empty_data
        invoice_data['data'] = render_data
    else:
        temp = invoice_data['data']
        invoice_data['data'] = []
        #empty_data = [""] * (no_of_skus - data_length)
        if no_of_sku_count > 0:
            data_length = data_length+no_of_sku_count
        no_of_space = (13 - data_length)
        if no_of_space < 0:
            no_of_space = 0
        empty_data = [""] * no_of_space
        invoice_data['data'].append({'data': temp, 'empty_data': empty_data})
    top = ''
    if css:
        c = {'name': 'invoice'}
        top = loader.get_template('../miebach_admin/templates/toggle/invoice/top1.html')
        top = top.render(c)
    html = loader.get_template('../miebach_admin/templates/toggle/invoice/customer_invoice.html')
    html = html.render(invoice_data)
    return top + html


def get_sku_height(sku_data, row_items):
    inv_product = 47  # invoice products cell height
    imei_height = 16
    imei_header = 22

    if not sku_data['imeis']:
        return inv_product

    if sku_data.get('continue', ''):
        inv_product = 0

    if len(sku_data['imeis']) <= row_items:
        return inv_product + imei_header + imei_height
    else:
        import math
        return inv_product + imei_header + (int(math.ceil(float(len(sku_data['imeis'])) / row_items)) * imei_height)


def build_marketplace_invoice(invoice_data, user, css=False):
    # it will create invoice template

    user_profile = UserProfile.objects.get(user_id=user.id)
    if not (not invoice_data['detailed_invoice'] and invoice_data['is_gst_invoice']):
        return json.dumps(invoice_data, cls=DjangoJSONEncoder)

    titles = ['']
    import math
    if not (invoice_data.get("customer_invoice", "") == True):
        title_dat = get_misc_value('invoice_titles', user.id)
        if not title_dat == 'false':
            titles = title_dat.split(",")

    invoice_data['html_data'] = get_invoice_html_data(invoice_data)
    invoice_data['user_type'] = user_profile.user_type

    invoice_data['titles'] = titles
    perm_hsn_summary = get_misc_value('hsn_summary', user.id)
    invoice_data['perm_hsn_summary'] = str(perm_hsn_summary)
    if len(invoice_data['hsn_summary'].keys()) == 0:
        invoice_data['perm_hsn_summary'] = 'false'
    invoice_data['empty_tds'] = [1, 2, 3, 4, 5, 6, 7, 8]

    inv_height = 1358  # total invoice height
    inv_details = 317  # 292 #invoice details height 292
    inv_footer = 95  # invoice footer height
    inv_totals = 127  # invoice totals height
    inv_header = 47  # invoice tables headers height
    inv_product = 47  # invoice products cell height
    inv_summary = 47  # invoice summary headers height
    inv_total = 27  # total display height
    inv_charges = 20  # height of other charges

    inv_totals = inv_totals + len(invoice_data['order_charges']) * inv_charges
    '''
    if invoice_data['user_type'] == 'marketplace_user':
        inv_details = 121
        s_count = invoice_data['seller_address'].count('\n')
        s_count = s_count - 3
        b_count = invoice_data['customer_address'].count('\n')
        b_count = b_count - 3
        s_count = s_count if s_count > b_count else b_count
        if s_count > 0:
            inv_details = inv_details + (20*s_count)
        else:
            inv_details = inv_details + 20
        inv_details = 230
    '''
    # invoice_data['user_type'] = 'warehouse_user'
    render_data = []
    render_space = 0
    hsn_summary_length = len(invoice_data['hsn_summary'].keys()) * inv_total
    if (perm_hsn_summary == 'true'):
        render_space = inv_height - (
        inv_details + inv_footer + inv_totals + inv_header + inv_summary + inv_total + hsn_summary_length)
    else:
        render_space = inv_height - (inv_details + inv_footer + inv_totals + inv_header + inv_total)

    render_space2 = inv_height - (inv_details + inv_header)

    # random imeis
    # import random
    # for index,data in enumerate(invoice_data['data']):
    #    data['imeis'] = [random.randint(100000000000000,999999999999999) for _ in xrange(random.choice([200, 10, 20, 30, 50, 40, 60]))]
    #    data['quantity'] = len(data['imeis'])

    render_data
    space1 = render_space
    space2 = render_space2
    row_items = 2
    temp_sku_data = {'empty_data': [], 'data': [], 'space_left': 0}
    # preparing pages
    for index, data in enumerate(invoice_data['data']):
        sku_height = get_sku_height(data, row_items)
        if (space2 < sku_height):
            if (space2 > 100):
                arr_index = (int(math.ceil(
                    (float(sku_height - space2) / 16))) * row_items) * -1  # ((sku_height - space2)/20)*row_items
                if (len(temp_sku_data['data']) == 0):
                    arr_index = 114
                temp_data = copy.deepcopy(data)
                temp_data['imeis'] = temp_data['imeis'][:arr_index]
                temp_data['imei_quantity'] = len(temp_data['imeis'])
                temp_sku_data['data'].append(temp_data)
                data['imeis'] = data['imeis'][arr_index:]
                data['continue'] = True
            temp_sku_data['space_left'] = space2
            temp = copy.deepcopy(temp_sku_data)
            render_data.append(temp)
            temp_sku_data['data'] = []
            space2 = render_space2

            imei_limit = 114
            if (len(data['imeis']) > imei_limit):
                temp_imeis = data['imeis']
                if data.get('continue', ''):
                    imei_limit = 120
                for i in range(len(data['imeis']) / imei_limit):
                    temp_data = copy.deepcopy(data)
                    temp_data['imeis'] = temp_data['imeis'][i * imei_limit: (i + 1) * imei_limit]
                    temp_data['imei_quantity'] = len(temp_data['imeis'])
                    data['continue'] = True
                    if temp_data['imeis']:
                        render_data.append({'empty_data': [], 'data': [temp_data], 'space_left': 0})
                        temp_imeis = data['imeis'][(i + 1) * imei_limit:]
                data['imeis'] = temp_imeis

            sku_height = get_sku_height(data, row_items)

        data['imei_quantity'] = len(data['imeis'])
        temp_sku_data['data'].append(data)
        space2 = space2 - sku_height

        if index == len(invoice_data['data']) - 1:
            temp_sku_data['space_left'] = space2
            render_data.append(temp_sku_data)

    last = len(render_data) - 1
    space1 = render_space
    page_split = False
    # checking last page have enough space
    for index, data in enumerate(render_data[last]['data']):
        sku_height = get_sku_height(data, row_items)
        if (space1 < sku_height):
            if len(render_data[last]['data'][index:]) == 1:
                temp_imeis1 = render_data[last]['data'][index]['imeis'][:-1]
                # temp_imeis2 = render_data[last]['data'][index]['imeis'][-1:]
                render_data[last]['data'][index]['imeis'] = render_data[last]['data'][index]['imeis'][-1:]
                render_data[last]['data'][index]['imei_quantity'] = len(render_data[last]['data'][index]['imeis'])
                sku_height = get_sku_height(render_data[last]['data'][index], row_items)
                temp_render_data = copy.deepcopy(render_data[last]['data'][index:])
                temp_render_data[0]['continue'] = True
                sku_height = get_sku_height(temp_render_data[0], row_items)
                render_data.append(
                    {'empty_data': [], 'data': temp_render_data, 'space_left': render_space - sku_height})
                data['imeis'] = temp_imeis1
                data['imei_quantity'] = len(data['imeis'])
                # render_data[last]['data'].pop(index)
                page_split = True
            else:
                sku_height = get_sku_height(render_data[last]['data'][-1:][0], row_items)
                render_data.append({'empty_data': [], 'data': copy.deepcopy(render_data[last]['data'][-1:]),
                                    'space_left': render_space - sku_height})
                render_data[last]['data'].pop(len(render_data[last]['data']) - 1)
                page_split = True

            break
        space1 = space1 - sku_height
    last = len(render_data) - 1
    if not page_split:
        render_data[last]['space_left'] = space1
    if render_data[last]['space_left'] >= inv_product:
        render_data[last]['empty_data'] = [""] * ((render_data[last]['space_left']) / inv_product)

    invoice_data['data'] = render_data
    top = ''
    if css:
        c = {'name': 'invoice'}
        top = loader.get_template('../miebach_admin/templates/toggle/invoice/top1.html')
        top = top.render(c)
    html = loader.get_template('../miebach_admin/templates/toggle/invoice/customer_invoice.html')
    html = html.render(invoice_data)
    return top + html


def get_new_supplier_id(user):
    max_sup_id = SupplierMaster.objects.count()
    run_iterator = 1
    while run_iterator:
        supplier_obj = SupplierMaster.objects.filter(id=max_sup_id)
        if not supplier_obj:
            run_iterator = 0
        else:
            max_sup_id += 1
    return max_sup_id


def create_swx_mapping(swx_id, local_id, swx_type, app_host):
    swx_mapping = SWXMapping.objects.filter(swx_id=swx_id, local_id=local_id, swx_type=swx_type, app_host=app_host)
    if not swx_mapping:
        SWXMapping.objects.create(swx_id=swx_id, local_id=local_id, swx_type=swx_type, app_host=app_host,
                                  creation_date=datetime.datetime.now())


def check_and_update_order_status(shipped_orders_dict, user):
    from rest_api.views.easyops_api import EasyopsAPI
    integrations = Integrations.objects.filter(user=user.id, status=1)
    for integrate in integrations:
        order_status_dict = {}
        obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
        all_seller_orders = SellerOrder.objects.filter(order__user=user.id, order_id__in=shipped_orders_dict.keys())
        all_orders = OrderDetail.objects.filter(user=user.id, id__in=shipped_orders_dict.keys())
        line_items_ids = SWXMapping.objects.filter(app_host='shotang')
        try:
            for order_id, order_data in shipped_orders_dict.iteritems():

                order = all_orders.filter(id=order_id)
                if not order:
                    continue
                else:
                    order = order[0]
                seller_orders = all_seller_orders.filter(order_id=order_id)

                order_detail_id = str(order.original_order_id)
                if not order_detail_id:
                    order_detail_id = str(order.order_code) + str(order.order_id)
                if not order_status_dict.has_key(order_detail_id):
                    order_status_dict[order_detail_id] = {}
                    order_status_dict[order_detail_id]['uorId'] = order_detail_id
                    order_status_dict[order_detail_id]['dateAdded'] = 1476901800000
                    order_status_dict[order_detail_id]['retailerId'] = str(order.customer_id)
                    order_status_dict[order_detail_id]['retailerAddress'] = {'retailerId': str(order.customer_id),
                                                                             'city': order.city,
                                                                             'address': order.address,
                                                                             'name': order.customer_name,
                                                                             'phoneNo': order.telephone}

                order_status_dict[order_detail_id].setdefault('subOrders', [])
                for seller_order in seller_orders:
                    is_sor_id = filter(lambda a: str(a['sorId']) == str(seller_order.sor_id),
                                       order_status_dict[order_detail_id]['subOrders'])
                    if not len(is_sor_id) > 0:
                        seller_dict = {}
                        seller_dict['sorId'] = str(seller_order.sor_id)
                        seller_dict['sellerId'] = seller_order.seller.seller_id
                        seller_dict['invoiceNo'] = seller_order.invoice_no
                        # seller_dict['seller_city'] = ''
                        # seller_dict['sellerAddress'] = {}
                        order_status_dict[order_detail_id]['subOrders'].append(seller_dict)
                        index = len(order_status_dict[order_detail_id]['subOrders']) - 1
                    else:
                        index = order_status_dict[order_detail_id]['subOrders'].index(is_sor_id[0])
                    order_status_dict[order_detail_id]['subOrders'][index].setdefault('lineItems', [])
                    for imei in order_data.get('imeis', []):
                        hsn_code = ''
                        if order.sku.hsn_code:
                            hsn_code = order.sku.hsn_code
                        seller_item_obj = line_items_ids.filter(local_id=seller_order.id, app_host='shotang',
                                                                swx_type='seller_item_id',
                                                                imei='')
                        seller_item_id = ''
                        if seller_item_obj:
                            seller_item_id = seller_item_obj[0].swx_id
                            seller_item_obj[0].imei = imei.po_imei.imei_number
                            seller_item_obj[0].save()

                        seller_parent_item_obj = line_items_ids.filter(local_id=seller_order.id, app_host='shotang',
                                                                       swx_type='seller_parent_item_id', imei='')
                        seller_parent_id = ''
                        if seller_parent_item_obj:
                            seller_parent_id = seller_parent_item_obj[0].swx_id
                            seller_parent_item_obj[0].imei = imei.po_imei.imei_number
                            seller_parent_item_obj[0].save()
                        elif not seller_parent_item_obj:
                            seller_parent_item_obj = line_items_ids.filter(local_id=seller_order.id, app_host='shotang',
                                                                           swx_type='seller_parent_item_id').order_by(
                                '-creation_date')
                            if seller_parent_item_obj:
                                seller_parent_id = seller_parent_item_obj[0].swx_id
                        imei_dict = {'lineItemId': seller_item_id, 'name': order.title,
                                     'unitPrice': str(order.unit_price), 'quantity': str(1),
                                     'sku': order.sku.sku_code, 'cgstTax': 0, 'sgstTax': 0, 'igstTax': 0,
                                     'parentLineItemId': seller_parent_id, 'status': 'PROCESSED',
                                     'imei': imei.po_imei.imei_number, 'hsn': hsn_code}
                        order_status_dict[order_detail_id]['subOrders'][index].setdefault('lineItems', [])
                        order_status_dict[order_detail_id]['subOrders'][index]['lineItems'].append(imei_dict)
            final_data = order_status_dict.values()
            init_log.info("Order Update request params for %s is %s" % (str(user.username), str(final_data)))
            call_response = obj.confirm_order_status(final_data, user=user)
            init_log.info("Order Update response for %s is %s" % (str(user.username), str(call_response)))
            if isinstance(call_response, dict) and call_response.get('status') == 1:
                init_log.info('Order Update status for username ' + str(user.username) + ' the data ' + str(
                    final_data) + ' is Successfull')
        except Exception as e:
            import traceback
            init_log.debug(traceback.format_exc())
            init_log.info('Update Order status failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(shipped_orders_dict), str(e)))
            continue


def get_returns_seller_order_id(order_detail_id, sku_code, user, sor_id=''):
    filt_params = {'order_id': order_detail_id, 'order__sku__sku_code': sku_code, 'order__user': user.id}
    if sor_id:
        filt_params['sor_id'] = sor_id
    seller_order = SellerOrder.objects.filter(**filt_params)
    if seller_order:
        return seller_order[0]
    else:
        return ''


def check_and_update_order_status_data(shipped_orders_dict, user, status=''):
    from rest_api.views.easyops_api import EasyopsAPI
    integrations = Integrations.objects.filter(user=user.id, status=1)
    for integrate in integrations:
        order_status_dict = {}
        obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
        all_seller_orders = SellerOrder.objects.filter(order__user=user.id, id__in=shipped_orders_dict.keys())
        all_orders = OrderDetail.objects.filter(user=user.id, id__in=shipped_orders_dict.keys())
        line_items_ids = SWXMapping.objects.filter(app_host='shotang')

        try:
            for order_id, order_data in shipped_orders_dict.iteritems():

                seller_order = all_seller_orders.get(id=order_id)
                order = seller_order.order
                if not order:
                    continue

                order_detail_id = str(order.original_order_id)
                if not order_detail_id:
                    order_detail_id = str(order.order_code) + str(order.order_id)
                if not order_status_dict.has_key(order_detail_id):
                    order_status_dict[order_detail_id] = {}
                    order_status_dict[order_detail_id]['uorId'] = order_detail_id
                    order_status_dict[order_detail_id]['dateAdded'] = get_local_date(user, order.creation_date)
                    order_status_dict[order_detail_id]['retailerId'] = str(order.customer_id)
                    order_status_dict[order_detail_id]['retailerAddress'] = {'retailerId': str(order.customer_id),
                                                                             'city': order.city,
                                                                             'address': order.address,
                                                                             'name': order.customer_name,
                                                                             'phoneNo': order.telephone}

                order_status_dict[order_detail_id].setdefault('subOrders', [])

                is_sor_id = filter(lambda a: str(a['sorId']) == str(seller_order.sor_id),
                                   order_status_dict[order_detail_id]['subOrders'])
                if not len(is_sor_id) > 0:
                    seller_dict = {}
                    seller_dict['sorId'] = str(seller_order.sor_id)
                    seller_dict['sellerId'] = seller_order.seller.seller_id
                    seller_dict['invoiceNo'] = seller_order.invoice_no
                    order_status_dict[order_detail_id]['subOrders'].append(seller_dict)
                    index = len(order_status_dict[order_detail_id]['subOrders']) - 1
                else:
                    index = order_status_dict[order_detail_id]['subOrders'].index(is_sor_id[0])
                order_status_dict[order_detail_id]['subOrders'][index].setdefault('lineItems', [])
                hsn_code = ''
                if order.sku.hsn_code:
                    hsn_code = order.sku.hsn_code
                if order_data.get('quantity', 0):
                    order_data['imeis'] = ['None'] * int(order_data['quantity'])

                for imei in order_data.get('imeis', []):
                    filt_params = {'local_id': seller_order.id, 'app_host': 'shotang'}
                    if status == 'CANCELLED':
                        filt_params['imei'] = ''
                    else:
                        filt_params['imei'] = imei
                    seller_item_obj = line_items_ids.filter(swx_type='seller_item_id', **filt_params)
                    seller_item_id = ''
                    if seller_item_obj:
                        seller_item_id = seller_item_obj[0].swx_id
                        if status == 'CANCELLED':
                            seller_item_obj[0].imei = imei
                            seller_item_obj[0].save()

                    seller_parent_item_obj = line_items_ids.filter(swx_type='seller_parent_item_id', **filt_params)
                    seller_parent_id = ''
                    if seller_parent_item_obj:
                        seller_parent_id = seller_parent_item_obj[0].swx_id
                        if status == 'CANCELLED':
                            seller_parent_item_obj[0].imei = imei
                            seller_parent_item_obj[0].save()
                    imei_dict = {'lineItemId': seller_item_id, 'name': order.title,
                                 'unitPrice': str(order.unit_price), 'quantity': str(1),
                                 'sku': order.sku.sku_code, 'cgstTax': 0, 'sgstTax': 0, 'igstTax': 0,
                                 'parentLineItemId': seller_parent_id, 'status': status,
                                 'imei': imei, 'hsn': hsn_code}
                    order_status_dict[order_detail_id]['subOrders'][index].setdefault('lineItems', [])
                    order_status_dict[order_detail_id]['subOrders'][index]['lineItems'].append(imei_dict)

            final_data = order_status_dict.values()
            call_response = obj.set_return_order_status(final_data, user=user, status=status)
            init_log.info(str(call_response))
            if isinstance(call_response, dict) and call_response.get('status') == 1:
                init_log.info('Order Update status for username ' + str(user.username) + ' the data ' + str(
                    final_data) + ' is Successfull')
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info(
                'Update Order returns or cancelled status failed for %s and params are %s and error statement is %s' % (
                str(user.username), str(shipped_orders_dict), str(e)))
            continue


def check_and_add_dict(grouping_key, key_name, adding_dat, final_data_dict={}, is_list=False):
    final_data_dict.setdefault(grouping_key, {})
    final_data_dict[grouping_key].setdefault(key_name, {})
    if is_list:
        final_data_dict[grouping_key].setdefault(key_name, [])
        final_data_dict[grouping_key][key_name] = copy.deepcopy(
            list(chain(final_data_dict[grouping_key][key_name], adding_dat)))

    elif grouping_key in final_data_dict.keys() and final_data_dict[grouping_key][key_name].has_key('quantity'):
        final_data_dict[grouping_key][key_name]['quantity'] = final_data_dict[grouping_key][key_name]['quantity'] + \
                                                              adding_dat.get('quantity', 0)
    # elif grouping_key in final_data_dict.keys() and final_data_dict[grouping_key][key_name].has_key('invoice_amount'):
        final_data_dict[grouping_key][key_name]['invoice_amount'] = final_data_dict[grouping_key][key_name][
                                                                  'invoice_amount'] + \
                                                              adding_dat.get('invoice_amount', 0)
    else:
        final_data_dict[grouping_key][key_name] = copy.deepcopy(adding_dat)

    return final_data_dict


def update_order_dicts(orders, user='', company_name=''):
    from outbound import check_stocks
    trans_mapping = {}
    orderId = []
    status = {'status': 0, 'messages': ['Something went wrong']}
    for order_key, order in orders.iteritems():
        if company_name == "storehippo":
            customer_name = order['order_details']['customer_name']
            for ord_obj in order.get('extra', ''):
                OrderCharges.objects.create(**ord_obj)
        if not order.get('order_details', {}):
            continue
        order_det_dict = order['order_details']
        original_order_id = order_det_dict.get('original_order_id', '')
        orderId.append(original_order_id)
        if not order.get('order_detail_obj', None):
            order_obj = OrderDetail.objects.filter(original_order_id=order_det_dict['original_order_id'],
                                                   order_id=order_det_dict['order_id'],
                                                   order_code=order_det_dict['order_code'],
                                                   sku_id=order_det_dict['sku_id'],
                                                   user=order_det_dict['user'])
        else:
            order_obj = [order.get('order_detail_obj', None)]
        if order_obj:
            order_obj = order_obj[0]
            order_obj.quantity = float(order_obj.quantity) + float(order_det_dict.get('quantity', 0))
            order_obj.invoice_amount = float(order_obj.invoice_amount) + float(order_det_dict.get('invoice_amount', 0))
            if company_name == "storehippo":
                order_obj.sku_code = str(order_det_dict.get('line_item_id', ''))
            order_obj.save()
            order_detail = order_obj
        else:
            if company_name == "storehippo":
                del(order['order_details']['customer_code'])
                order['order_details']['customer_name'] = customer_name
            order_detail = OrderDetail.objects.create(**order['order_details'])
        if order.get('order_summary_dict', {}) and not order_obj:
            order['order_summary_dict']['order_id'] = order_detail.id
            customer_order_summary = CustomerOrderSummary.objects.create(**order['order_summary_dict'])
        if order.get('seller_order_dict', {}):
            check_create_seller_order(order['seller_order_dict'], order_detail, user,
                                      order.get('swx_mappings', []), trans_mapping=trans_mapping)
        order_sku = {}
        sku_obj = SKUMaster.objects.filter(id=order_det_dict['sku_id'])

        if 'measurement_type' in order_det_dict.keys() and company_name == "storehippo":
            sku_obj.update(measurement_type=order_det_dict['measurement_type'])
        if sku_obj:
            sku_obj = sku_obj[0]
        else:
            continue
        order_sku.update({sku_obj: order_det_dict['quantity']})
        auto_picklist_signal = get_misc_value('auto_generate_picklist', order_det_dict['user'])
        if auto_picklist_signal == 'true':
            message = check_stocks(order_sku, user, 'false', [order_detail])
        if company_name == "storehippo":
            for order_fields in order.get('order_fields_list', ''):
                OrderFields.objects.create(**order_fields)
        status = {'status': 1, 'messages': 'Success', 'order_id':orderId}
    return status


def update_ingram_order_dicts(orders, seller_obj, user=''):
    status = {'status': 0, 'messages': ['Something went wrong']}
    success = ['Success']
    if seller_obj:
        seller_obj = seller_obj[0]
    for order_key, order in orders.iteritems():
        seller_order_dict = {}
        order_charge_dict = {}
        if not order.get('order_details', {}):
            continue
        order_det_dict = order['order_details']
        if not order.get('order_detail_obj', None):
            order_obj = OrderDetail.objects.filter(original_order_id=order_det_dict['original_order_id'],
                                                   order_id=order_det_dict['order_id'],
                                                   order_code=order_det_dict['order_code'],
                                                   sku_id=order_det_dict['sku_id'], user=order_det_dict['user'])
        else:
            order_obj = [order.get('order_detail_obj', None)]
        if order_obj:
            order_obj = order_obj[0]
            order_obj.status = order_det_dict.get('status', 0)
            order_obj.save()
            order_detail = order_obj
            message = 'Orders Updated Successfully'
        else:
            order_obj = OrderDetail.objects.create(**order['order_details'])
            message = 'Orders Created Successfully'

        order_summary_dict = order.get('order_summary_dict', {})
        if order_summary_dict:
            order_summary_dict['order'] = order_obj
            customer_order_summary = CustomerOrderSummary.objects.create(**order_summary_dict)
        if order_obj:
            if seller_obj:
                sor_id = str(seller_obj.id) + '_' + str(order_obj.id)
                sell_order_present = SellerOrder.objects.filter(order_id=order_obj.id,
                                                                seller__user=user.id, sor_id=sor_id)
                if not sell_order_present:
                    seller_order_dict['seller'] = seller_obj
                    seller_order_dict['sor_id'] = sor_id
                    seller_order_dict['order'] = order_obj
                    seller_order_dict['quantity'] = order_obj.quantity
                    seller_order_dict['invoice_no'] = ''
                    seller_order_dict['order_status'] = 'PROCESSED'
                    seller_order_dict['status'] = order_obj.status
                    seller_order_dict['creation_date'] = datetime.datetime.now()
                    seller_order_dict['updation_date'] = datetime.datetime.now()
                    seller_order_obj = SellerOrder.objects.create(**seller_order_dict)

            order_charge = OrderCharges.objects.filter(order_id=order_obj.original_order_id, charge_name='Shipping Tax',
                                                       user_id=order_det_dict['user'])
            if not order_charge:
                order_charge_dict['order_id'] = order_obj.original_order_id
                order_charge_dict['charge_name'] = 'Shipping Tax'
                order_charge_dict['charge_amount'] = order['shipping_tax']
                order_charge_dict['user_id'] = order_det_dict['user']
                OrderCharges.objects.create(**order_charge_dict)

        order_id_pick = order_obj.original_order_id.split('_')
        status = {
            "Status": "Success",
            "OrderId": order_id_pick[1],
            "Result": {
                "Status": order['status_type'],
                "Message": message
            }
        }

    return status


def check_create_seller_order(seller_order_dict, order, user, swx_mappings=[], trans_mapping=None):
    if not trans_mapping:
        trans_mapping = {}
    if seller_order_dict.get('seller_id', ''):
        sell_order_ins = SellerOrder.objects.filter(sor_id=seller_order_dict['sor_id'], order_id=order.id,
                                                    seller__user=user.id)
        seller_order_dict['order_id'] = order.id
        if not sell_order_ins:
            seller_order = SellerOrder(**seller_order_dict)
            seller_order.save()
            #if user.username == 'milkbasket':
            #    aspl_seller = SellerMaster.objects.filter(user=user.id, name='ASPL')
            #    if aspl_seller:
            #        trans_mapping = create_seller_order_transfer(seller_order, aspl_seller[0].id, trans_mapping)
            for swx_mapping in swx_mappings:
                try:
                    create_swx_mapping(swx_mapping['swx_id'], seller_order.id, swx_mapping['swx_type'],
                                       swx_mapping['app_host'])
                except:
                    pass


def save_order_tracking_data(order, quantity, status='', imei=''):
    try:
        log.info('Order Tracking Data Request Params %s, %s, %s, %s' % (
        str(order.__dict__), str(quantity), str(status), str(imei)))
        order_tracking = OrderTracking.objects.filter(order_id=order.id, status=status, imei='')
        if order_tracking:
            order_tracking = order_tracking[0]
            order_tracking.quantity = float(order_tracking.quantity) + float(remaining_qty)
            order_tracking.save()
        else:
            OrderTracking.objects.create(order_id=order.id, status=status, imei=imei, quantity=quantity,
                                         creation_date=datetime.datetime.now(),
                                         updation_date=datetime.datetime.now())
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Order Tracking Insert failed for %s and params are %s and error statement is %s' % (
        str(order.user), str(order.__dict__), str(e)))


def get_stock_receipt_number(user):
    receipt_number = StockDetail.objects.filter(sku__user=user.id).only('receipt_number').\
        aggregate(Max('receipt_number'))['receipt_number__max']
    if receipt_number:
        receipt_number = receipt_number + 1
    else:
        receipt_number = 1
    return receipt_number


@csrf_exempt
def insert_po_mapping(imei_nos, data, user_id, stock=''):
    ''' Inserting IMEI Mapping throught PO'''
    imei_list = []
    imei_nos = list(set(imei_nos.split(',')))
    order_data = get_purchase_order_data(data)
    all_po_labels = []
    all_st_purchases = STPurchaseOrder.objects.filter(open_st__sku__user=user_id)
    all_po_labels = POLabels.objects.filter(sku__user=user_id, status=1)
    if stock:
        stock = stock.id
    for imei in imei_nos:
        if not imei:
            continue
        po_mapping, status, imei_data = check_get_imei_details(imei, order_data['wms_code'], user_id,
                                                               check_type='purchase_check')
        if not status and (imei not in imei_list):
            if po_mapping:
                po_mapping_ids = list(po_mapping.values_list('id', flat=True))
                OrderIMEIMapping.objects.filter(po_imei_id__in=po_mapping_ids, status=1).update(status=0)
                ReturnsIMEIMapping.objects.filter(order_imei__po_imei_id__in=po_mapping_ids, imei_status=1).update(
                    imei_status=0)
            imei_mapping = {'purchase_order_id': data.id, 'imei_number': imei,
                            'status': 1,'stock_id':stock,
                            'sku_id': order_data['sku'].id,
                            'creation_date': datetime.datetime.now(),
                            'updation_date': datetime.datetime.now()}
            if data.open_po and data.open_po.sellerpo_set.filter():
                imei_mapping['seller_id'] = data.open_po.sellerpo_set.filter()[0].seller_id
            po_imei = POIMEIMapping(**imei_mapping)
            po_imei.save()
            all_po_labels.filter(purchase_order_id=data.id, label=imei, status=1).update(status=0)
        imei_list.append(imei)


@csrf_exempt
def insert_jo_mapping(imei_nos, data, user_id):
    ''' Inserting IMEI Mapping throught JO'''
    imei_list = []
    imei_nos = list(set(imei_nos.split(',')))
    all_po_labels = []
    all_po_labels = POLabels.objects.filter(sku__user=user_id, status=1)
    for imei in imei_nos:
        if not imei:
            continue
        po_mapping, status, imei_data = check_get_imei_details(imei, data.product_code.wms_code, user_id,
                                                               check_type='purchase_check')
        if not status and (imei not in imei_list):
            if po_mapping:
                po_mapping_ids = list(po_mapping.values_list('id', flat=True))
                OrderIMEIMapping.objects.filter(po_imei_id__in=po_mapping_ids, status=1).update(status=0)
                ReturnsIMEIMapping.objects.filter(order_imei__po_imei_id__in=po_mapping_ids, imei_status=1).update(
                    imei_status=0)
            imei_mapping = {'job_order_id': data.id, 'imei_number': imei, 'status': 1,
                            'sku_id': data.product_code.id,
                            'creation_date': datetime.datetime.now(),
                            'updation_date': datetime.datetime.now()}
            po_imei = POIMEIMapping(**imei_mapping)
            po_imei.save()
            all_po_labels.filter(job_order_id=data.id, label=imei, status=1).update(status=0)
        imei_list.append(imei)


def get_purchase_order_id(user):
    '''  Provides New Purchase Order ID '''
    # po_data = PurchaseOrder.objects.filter(open_po__sku__user=user.id).values_list('order_id', flat=True).order_by(
    #     "-order_id")
    # st_order = STPurchaseOrder.objects.filter(open_st__sku__user=user.id).values_list('po__order_id',
    #                                                                                   flat=True).order_by(
    #     "-po__order_id")
    # order_ids = list(chain(po_data, st_order))
    # order_ids = sorted(order_ids, reverse=True)
    # if not order_ids:
    #     po_id = 1
    # else:
    #     po_id = int(order_ids[0]) + 1

    po_id = get_incremental(user, 'po', default_val=1)
    po_id = po_id - 1
    return po_id


def get_jo_reference(user):
    ''' It Provides New Jo Reference Number '''
    jo_code = JobOrder.objects.filter(product_code__user=user).order_by('-jo_reference')
    if jo_code:
        jo_reference = int(jo_code[0].jo_reference) + 1
    else:
        jo_reference = 1
    return jo_reference


def get_format_types(request):
    format_types = {}
    for i in BarcodeSettings.objects.filter(user=request.user).order_by('-format_type'):
        if i.size:
            try:
                size = "%sX%s" % eval(i.size)
            except:
                size = i.size
            format_t = "_".join([i.format_type, size])
            format_types.update({format_t: i.format_type})

    return HttpResponse(json.dumps({'data': format_types}))


def get_serial_limit(user_id, imei):
    ''' it will return serial limit '''

    serial_limit = get_misc_value('serial_limit', user_id)
    if serial_limit == 'false' or serial_limit == '0' or not serial_limit:
        return ""
    else:
        serial_limit = int(serial_limit)
        if serial_limit == len(imei):
            return ""
        else:
            return "Serial Number Length Should Be " + str(serial_limit)


def get_shipment_quantity_for_awb(user, all_orders, sku_grouping=False):
    data = []
    log.info('Request Params for Get Shipment quantity for user %s is %s' % (user.username, str(all_orders.values())))
    filter_list = ['sku__sku_code', 'id', 'order_id', 'sku__sku_desc', 'original_order_id']
    status_list = ['open', 'picked', 'batch_open', 'batch_picked']
    if sku_grouping == 'true':
        filter_list = ['sku__sku_code', 'sku__sku_desc']
    picklists_obj = Picklist.objects.filter(order__in=all_orders, status__in=status_list,
                                            picked_quantity__gt=0, order__user=user.id)
    all_data = list(all_orders.values(*filter_list).distinct().annotate(picked=Sum('quantity')))
    for ind, dat in enumerate(all_data):
        ship_dict = {'order_id': dat['id']}
        seller_order = SellerOrder.objects.filter(order_id=dat['id'], order_status='DELIVERY_RESCHEDULED')
        dis_quantity = 0
        if seller_order:
            dis_pick = Picklist.objects.filter(order_id=dat['id'], status='dispatched')
            if dis_pick:
                dis_quantity = dis_pick[0].order.quantity
        if picklists_obj.filter(**ship_dict).exclude(order_type='combo'):
            all_data[ind]['shipping_quantity'] = all_data[ind]['picked'] = \
            picklists_obj.filter(**ship_dict).aggregate(Sum('picked_quantity'))['picked_quantity__sum']
        shipped = ShipmentInfo.objects.filter(**ship_dict).aggregate(Sum('shipping_quantity'))['shipping_quantity__sum']
        if shipped:
            shipped = shipped - dis_quantity
            all_data[ind]['picked'] = float(dat['picked']) - shipped
            all_data[ind]['shipping_quantity'] -= shipped
            if all_data[ind]['picked'] < 0:
                del all_data[ind]
    return all_data


def get_shipment_quantity(user, all_orders, sku_grouping=False):
    ''' Provides picked quantities needed for shipment '''
    data = []
    log.info('Request Params for Get Shipment quantity for user %s is %s' % (user.username, str(all_orders.values())))
    try:
        customer_dict = all_orders.values('customer_id', 'customer_name').distinct()
        filter_list = ['sku__sku_code', 'id', 'order_id', 'sku__sku_desc', 'original_order_id']
        if sku_grouping == 'true':
            filter_list = ['sku__sku_code', 'sku__sku_desc']

        for customer in customer_dict:
            customer_picklists = Picklist.objects.filter(order__customer_id=customer['customer_id'],
                                                         order__customer_name=customer['customer_name'],
                                                         status__in=['open', 'picked', 'batch_open', 'batch_picked'],
                                                         picked_quantity__gt=0, order__user=user.id)
            picklist_order_ids = list(customer_picklists.values_list('order_id', flat=True))
            customer_orders = all_orders.filter(id__in=picklist_order_ids)

            all_data = list(customer_orders.values(*filter_list).distinct().annotate(picked=Sum('quantity'),
                                                                                     ordered=Sum('quantity')))
            for ind, dat in enumerate(all_data):
                if sku_grouping == 'true':
                    ship_dict = {'order__sku__sku_code': dat['sku__sku_code'], 'order__sku__user': user.id,
                                 'order__customer_id': customer['customer_id'],
                                 'order__customer_name': customer['customer_name']}
                    all_data[ind]['id'] = list(
                        customer_picklists.filter(**ship_dict).values_list('order_id', flat=True).distinct())
                else:
                    ship_dict = {'order_id': dat['id']}
                seller_order = SellerOrder.objects.filter(order_id=dat['id'], order_status='DELIVERY_RESCHEDULED')
                dis_quantity = 0
                if seller_order:
                    dis_pick = Picklist.objects.filter(order_id=dat['id'], status='dispatched')
                    if dis_pick:
                        dis_quantity = dis_pick[0].order.quantity
                if customer_picklists.filter(**ship_dict).exclude(order_type='combo'):
                    all_data[ind]['picked'] = customer_picklists.filter(**ship_dict).aggregate(Sum('picked_quantity'))[
                        'picked_quantity__sum']
                shipping_quantity = OrderIMEIMapping.objects.filter(
                    order_id__in=all_orders.filter(sku__sku_code=all_data[ind]['sku__sku_code']).values_list('id'),
                    status=1).count()
                all_data[ind]['shipping_quantity'] = shipping_quantity
                shipped = ShipmentInfo.objects.filter(**ship_dict).aggregate(Sum('shipping_quantity'))[
                    'shipping_quantity__sum']
                if shipped:
                    shipped = shipped - dis_quantity
                    all_data[ind]['picked'] = float(dat['picked']) - shipped
                    all_data[ind]['shipping_quantity'] -= shipped
                    if all_data[ind]['picked'] < 0:
                        del all_data[ind]
                serial_number = OrderIMEIMapping.objects.filter(po_imei__sku__wms_code =all_data[ind]['sku__sku_code'],order_id= all_data[ind]['id'],po_imei__sku__user=user.id)
                serial_numbers_list = []
                if serial_number :
                    for i in range(serial_number.count()):
                        serial_numbers_list.append(serial_number[i].po_imei.imei_number)

                all_data[ind]['serial_number'] = serial_numbers_list

            data = list(chain(data, all_data))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Get Shipment quantity failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(all_orders.values()), str(e)))

    return data


def get_marketplace_names(user, status_type):
    userIds = [user.id]
    #if user.userprofile.multi_level_system == 1:
    #    sameGroupWhs = UserGroups.objects.filter(admin_user_id=user.id).values_list('user_id', flat=True)
    #    userIds = UserProfile.objects.filter(user_id__in=sameGroupWhs, warehouse_level=1).values_list('user_id', flat=True)

    if status_type == 'picked':
        marketplace = list(
            Picklist.objects.exclude(order__marketplace='').filter(picked_quantity__gt=0, order__user__in=userIds). \
            values_list('order__marketplace', flat=True).distinct())
    elif status_type == 'all_marketplaces':
        marketplace = list(OrderDetail.objects.exclude(marketplace='').filter(user__in=userIds, quantity__gt=0). \
                           values_list('marketplace', flat=True).distinct())
    else:
        marketplace = list(OrderDetail.objects.exclude(marketplace='').filter(status=1, user__in=userIds, quantity__gt=0). \
                           values_list('marketplace', flat=True).distinct())
    return marketplace


@csrf_exempt
@login_required
@get_admin_user
def update_invoice_sequence(request, user=''):
    ''' Create or Update Invoice Sequences '''

    log.info('Request Params for Update Invoice Sequences for %s is %s' % (user.username, str(request.GET.dict())))
    status = ''
    try:
        marketplace_name = request.GET.get('marketplace_name', '')
        if not marketplace_name:
            status = 'Marketplace Name Should not be empty'
        marketplace_prefix = request.GET.get('marketplace_prefix', '')
        marketplace_interfix = request.GET.get('marketplace_interfix', '')
        marketplace_date_type = request.GET.get('marketplace_date_type', '')
        delete_status = request.GET.get('delete', '')
        if not status:
            invoice_sequence = InvoiceSequence.objects.filter(user_id=user.id, marketplace=marketplace_name)
            if invoice_sequence:
                invoice_sequence = invoice_sequence[0]
                invoice_sequence.prefix = marketplace_prefix
                invoice_sequence.interfix = marketplace_interfix
                invoice_sequence.date_type = marketplace_date_type
                if delete_status:
                    invoice_sequence.status = 0
                else:
                    invoice_sequence.status = 1
                invoice_sequence.save()
            else:
                InvoiceSequence.objects.create(marketplace=marketplace_name, prefix=marketplace_prefix, value=1,
                                               status=1, interfix=marketplace_interfix, date_type=marketplace_date_type,
                                               user_id=user.id, creation_date=datetime.datetime.now())
            status = 'Success'

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update Invoice Sequence failed for %s and params are %s and error statement is %s' %
                 (str(user.username), str(request.GET.dict()), str(e)))
        status = 'Update Invoice Number Sequence Failed'
    return HttpResponse(json.dumps({'status': status}))

@csrf_exempt
@login_required
@get_admin_user
def update_dc_sequence(request, user=''):

    log.info('Request Params for Update Dc Invoice Sequences for %s is %s' % (user.username, str(request.GET.dict())))
    status = ''
    try:
        marketplace_name = request.GET.get('marketplace_name', '')
        if not marketplace_name:
            status = 'Marketplace Name Should not be empty'
        marketplace_prefix = request.GET.get('marketplace_prefix', '')
        marketplace_interfix = request.GET.get('marketplace_interfix', '')
        marketplace_date_type = request.GET.get('marketplace_date_type', '')
        delete_status = request.GET.get('delete', '')
        if not status:
            challan_sequence = ChallanSequence.objects.filter(user_id=user.id, marketplace=marketplace_name)
            if challan_sequence:
                challan_sequence = invoice_sequence[0]
                challan_sequence.prefix = marketplace_prefix
                challan_sequence.interfix = marketplace_interfix
                challan_sequence.date_type = marketplace_date_type
                if delete_status:
                    challan_sequence.status = 0
                else:
                    challan_sequence.status = 1
                challan_sequence.save()
            else:
                ChallanSequence.objects.create(marketplace=marketplace_name, prefix=marketplace_prefix, value=1,
                                               status=1,user_id=user.id, creation_date=datetime.datetime.now())
            status = 'Success'

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update DC Invoice Sequence failed for %s and params are %s and error statement is %s' %
                 (str(user.username), str(request.GET.dict()), str(e)))
        status = 'Update DC Invoice Number Sequence Failed'
    return HttpResponse(json.dumps({'status': status}))


@csrf_exempt
@login_required
@get_admin_user
def update_user_type_sequence(request, user=''):

    log.info('Request Params for Update Dc Invoice Sequences for %s is %s' % (user.username, str(request.GET.dict())))
    status = ''
    try:
        marketplace_prefix = request.GET.get('marketplace_prefix', '')
        marketplace_interfix = request.GET.get('marketplace_interfix', '')
        marketplace_date_type = request.GET.get('marketplace_date_type', '')
        type_name = request.GET.get('type_name', '')
        type_value = request.GET.get('type_value', '')
        delete_status = request.GET.get('delete', '')
        if not type_name:
            status = 'Type Name Should not be empty'
        if not status:
            sequence = UserTypeSequence.objects.filter(user_id=user.id, type_name=type_name, type_value=type_value)
            if sequence:
                sequence = sequence[0]
                sequence.prefix = marketplace_prefix
                sequence.interfix = marketplace_interfix
                sequence.date_type = marketplace_date_type
                if delete_status:
                    sequence.status = 0
                else:
                    sequence.status = 1
                sequence.save()
            else:
                UserTypeSequence.objects.create(prefix=marketplace_prefix, value=1,
                                               status=1,user_id=user.id, creation_date=datetime.datetime.now(),
                                                date_type=marketplace_date_type,
                                                type_name=type_name, type_value=type_value)
            status = 'Success'

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update User Type Invoice Sequence failed for %s and params are %s and error statement is %s' %
                 (str(user.username), str(request.GET.dict()), str(e)))
        status = 'Update Sequence Failed'
    return HttpResponse(json.dumps({'status': status}))


def get_warehouse_admin(user):
    """ Check and Return Admin user of current """

    is_admin_exists = UserGroups.objects.filter(Q(user=user) | Q(admin_user=user))
    if is_admin_exists:
        admin_user = is_admin_exists[0].admin_user
    else:
        admin_user = user
    return admin_user

@fn_timer
def get_picklist_number(user):
    """ Get the Latest Picklist number"""
    # #picklist_obj = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id)).values_list(
    # #    'picklist_number',
    # #    flat=True).distinct().order_by('-picklist_number')
    # picklist_obj = Picklist.objects.filter(Q(order__sku__user=user.id) | Q(stock__sku__user=user.id))
    # if not picklist_obj.exists():
    #     picklist_number = 1000
    # else:
    #     picklist_number = picklist_obj.latest('picklist_number').picklist_number
    picklist_number = get_incremental(user, 'picklist')
    picklist_number = picklist_number - 1
    return picklist_number


@fn_timer
def get_sku_stock(sku, sku_stocks, user, val_dict, sku_id_stocks='', add_mrp_filter=False, needed_mrp_filter=0):
    data_dict = {'sku_id': sku.id, 'quantity__gt': 0}
    fifo_switch = get_misc_value('fifo_switch', user.id)
    if fifo_switch == "true":
        order_by = 'receipt_date'
    else:
        order_by = 'location_id__pick_sequence'
    if add_mrp_filter and needed_mrp_filter:
        data_dict['batch_detail__mrp'] = needed_mrp_filter
    stock_detail = sku_stocks.filter(**data_dict).order_by(order_by).distinct()
    stock_count = 0
    if sku.id in val_dict['sku_ids']:
        indices = [i for i, x in enumerate(sku_id_stocks) if x['sku_id'] == sku.id]
        for index in indices:
            stock_count += val_dict['stock_totals'][index]
        if sku.id in val_dict['pic_res_ids']:
            pic_res_id_index = val_dict['pic_res_ids'].index(sku.id)
            stock_count = stock_count - val_dict['pic_res_quans'][pic_res_id_index]
    return stock_detail, stock_count, sku.wms_code


def get_stock_count(order, stock, stock_diff, user, order_quantity, prev_reserved=False, seller_master_id=''):
    reserved_quantity = \
    PicklistLocation.objects.filter(stock_id=stock.id, status=1, picklist__order__user=user.id).aggregate(
        Sum('reserved'))['reserved__sum']
    if not reserved_quantity:
        reserved_quantity = 0

    if seller_master_id:
        stock_quantity = SellerStock.objects.filter(stock_id=stock.id, seller_id=seller_master_id).aggregate(Sum('quantity'))['quantity__sum']
        if not stock_quantity:
            stock_quantity = 0
    else:
        stock_quantity = float(stock.quantity) - reserved_quantity
    # if prev_reserved:
    #    if stock_quantity >= 0:
    #        #return order_quantity, 0
    #        return 0, stock_diff
    if stock_quantity <= 0:
        return 0, stock_diff

    if stock_diff:
        if stock_quantity >= stock_diff:
            stock_count = stock_diff
            stock_diff = 0
        else:
            stock_count = stock_quantity
            stock_diff -= stock_quantity
    else:
        if stock_quantity >= order_quantity:
            stock_count = order_quantity
        else:
            stock_count = stock_quantity
            stock_diff = order_quantity - stock_quantity
    return stock_count, stock_diff


def create_seller_summary_details(seller_order, picklist):
    if not seller_order or not picklist:
        return False
    SellerOrderDetail.objects.create(seller_order_id=seller_order.id, picklist_id=picklist.id,
                                     quantity=picklist.reserved_quantity, reserved=picklist.reserved_quantity,
                                     creation_date=datetime.datetime.now())


@fn_timer
def picklist_generation(order_data, enable_damaged_stock, picklist_number, user, sku_combos, sku_stocks, switch_vals, status='',
                        remarks='', is_seller_order=False):
    # enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
    stock_status = []
    if not status:
        status = 'batch_open'
    is_marketplace_model = False
    all_zone_mappings = []
    if switch_vals['marketplace_model'] == 'true':
        all_zone_mappings = ZoneMarketplaceMapping.objects.filter(zone__user=user.id, status=1)
        is_marketplace_model = True
    fefo_enabled = False
    add_mrp_filter = False
    if user.userprofile.industry_type == 'FMCG':
        fefo_enabled = True
        if user.username in MILKBASKET_USERS:
            add_mrp_filter = True
    if switch_vals['fifo_switch'] == 'true':
        order_by = 'receipt_date'
    else:
        order_by = 'location_id__pick_sequence'
    no_stock_switch = False
    if switch_vals['no_stock_switch'] == 'true':
        no_stock_switch = True
    combo_allocate_stock = False
    if switch_vals.get('combo_allocate_stock', '') == 'true':
        combo_allocate_stock = True

    for order in order_data:
        picklist_data = copy.deepcopy(PICKLIST_FIELDS)
        # order_quantity = float(order.quantity)
        seller_order = None
        seller_master_id = ''
        if is_seller_order:
            seller_order = order
            seller_master_id = seller_order.seller_id
            order = order.order
        picklist_data['picklist_number'] = picklist_number + 1
        if remarks:
            picklist_data['remarks'] = remarks
        else:
            picklist_data['remarks'] = 'Picklist_' + str(picklist_number + 1)

        combo_sku_ids = list(sku_combos.filter(parent_sku_id=order.sku_id).values_list('member_sku_id', flat=True))
        combo_sku_ids.append(order.sku_id)
        sku_id_stock_filter = {'sku_id__in': combo_sku_ids}
        needed_mrp_filter = 0
        if order.sku.relation_type == 'combo':
            add_mrp_filter = False
        if add_mrp_filter:
            if 'st_po' not in dir(order) and order.customerordersummary_set.filter().exists():
                needed_mrp_filter = order.customerordersummary_set.filter()[0].mrp
                sku_id_stock_filter['batch_detail__mrp'] = needed_mrp_filter
        if seller_master_id:
            seller_filter_dict = {}
            for stock_filter_key, stock_filter_val in sku_id_stock_filter.iteritems():
                seller_filter_dict['%s__%s' % ('stock', str(stock_filter_key))] = stock_filter_val
            seller_id_stocks = SellerStock.objects.filter(stock_id__in=sku_stocks.values_list('id', flat=True),
                                                          seller_id=seller_master_id, **seller_filter_dict)
            sku_id_stocks_dict = OrderedDict()
            for seller_id_stock in seller_id_stocks:
                sku_id_stocks_dict.setdefault(seller_id_stock.stock_id,
                                              {'total': 0, 'sku_id': seller_id_stock.stock.sku_id,
                                               'id': seller_id_stock.stock_id})
                sku_id_stocks_dict[seller_id_stock.stock_id]['total'] += seller_id_stock.quantity
            sku_id_stocks = sku_id_stocks_dict.values()
            # sku_id_stocks = sku_stocks.filter(sellerstock__seller_id=seller_master_id, **sku_id_stock_filter).values('id', 'sku_id').\
            #                             annotate(total=Sum('sellerstock__quantity')).order_by(order_by)
        else:
            sku_id_stocks = sku_stocks.filter(**sku_id_stock_filter).values('id', 'sku_id').\
                                        annotate(total=Sum('quantity')).order_by(order_by)
        val_dict = {'sku_ids': map(lambda d: d['sku_id'], sku_id_stocks),
                    'stock_ids': map(lambda d: d['id'], sku_id_stocks),
                    'stock_totals': map(lambda d: d['total'], sku_id_stocks)}
        pc_loc_filter = OrderedDict()
        pc_loc_filter['picklist__order__user'] = user.id
        #if is_seller_order or add_mrp_filter:
        pc_loc_filter['stock_id__in'] = val_dict['stock_ids']
        pc_loc_filter['status'] = 1
        print pc_loc_filter
        pick_res_locat = PicklistLocation.objects.filter(**pc_loc_filter).values('stock__sku_id').\
                                                distinct().annotate(total=Sum('reserved'))

        val_dict['pic_res_ids'] = map(lambda d: d['stock__sku_id'], pick_res_locat)
        val_dict['pic_res_quans'] = map(lambda d: d['total'], pick_res_locat)

        if not seller_order:
            order_check_quantity = float(order.quantity)
        else:
            order_check_quantity = float(seller_order.quantity)
        members = {order.sku: order_check_quantity}
        if order.sku.relation_type == 'combo' and not combo_allocate_stock:
            picklist_data['order_type'] = 'combo'
            members = OrderedDict()
            combo_data = sku_combos.filter(parent_sku_id=order.sku.id)
            for combo in combo_data:
                member_check_quantity = order_check_quantity * combo.quantity
                members[combo.member_sku] = member_check_quantity
                stock_detail, stock_quantity, sku_code = get_sku_stock(combo.member_sku, sku_stocks, user,
                                                                       val_dict, sku_id_stocks,
                                                                       add_mrp_filter=add_mrp_filter,
                                                                       needed_mrp_filter=needed_mrp_filter)
                if stock_quantity < float(member_check_quantity):
                    if not no_stock_switch:
                        stock_status.append(str(combo.member_sku.sku_code))
                        members = {}
                        break
        for member, member_qty in members.iteritems():
            stock_detail, stock_quantity, sku_code = get_sku_stock(member, sku_stocks, user, val_dict,
                                                                   sku_id_stocks, add_mrp_filter=add_mrp_filter,
                                                                   needed_mrp_filter=needed_mrp_filter)
            if order.sku.relation_type == 'member':
                parent = sku_combos.filter(member_sku_id=member.id).filter(relation_type='member')
                stock_detail1, stock_quantity1, sku_code = get_sku_stock(parent[0].parent_sku, sku_stocks,
                                                                         user, val_dict, sku_id_stocks)
                stock_detail = list(chain(stock_detail, stock_detail1))
                stock_quantity += stock_quantity1
            elif order.sku.relation_type == 'combo' and not combo_allocate_stock:
                stock_detail, stock_quantity, sku_code = get_sku_stock(member, sku_stocks, user, val_dict,
                                                                       sku_id_stocks)

            order_quantity = member_qty
            # if not seller_order:
            #     order_quantity = float(order.quantity)
            # else:
            #     order_quantity = float(seller_order.quantity)
            if 'st_po' in dir(order) :
                order_quantity = order_quantity - order.picked_quantity

            if stock_quantity < float(order_quantity):
                if not no_stock_switch:
                    stock_status.append(str(member.sku_code))
                    continue

                if stock_quantity < 0:
                    stock_quantity = 0
                order_diff = 0
                order_diff = order_quantity - stock_quantity
                order_quantity -= order_diff
                # stock_detail = []
                # stock_detail = create_temp_stock(member.sku_code, 'DEFAULT', int(order.quantity) - stock_quantity, stock_detail, user.id)
                picklist_data['reserved_quantity'] = order_diff
                picklist_data['stock_id'] = ''
                picklist_data['order_id'] = order.id
                picklist_data['status'] = status
                if enable_damaged_stock  == 'true':
                    picklist_data['damage_suggested'] = 1
                if sku_code:
                    picklist_data['sku_code'] = sku_code
                if 'st_po' not in dir(order):
                    new_picklist = Picklist(**picklist_data)
                    new_picklist.save()
                    if seller_order:
                        create_seller_summary_details(seller_order, new_picklist)
                        seller_order.status = 0
                        seller_order.save()
                        sell_order = SellerOrder.objects.filter(order_id=order.id, status=1)
                        if not sell_order:
                            order.status = 0
                            order.save()
                    else:
                        order.status = 0
                        order.save()
                        # if seller_order:
                        #    create_seller_summary_details(seller_order, new_picklist)
                if stock_quantity <= 0:
                    continue

            stock_diff = 0

            # Marketplace model suggestions based on Zone Marketplace mapping
            if is_marketplace_model:
                if 'st_po' not in dir(order):
                    zone_map_ids = all_zone_mappings.filter(marketplace=order.marketplace).values_list('zone_id', flat=True)
                    rem_zone_map_ids = all_zone_mappings.exclude(zone_id__in=zone_map_ids).values_list('zone_id', flat=True)
                    all_zone_map_ids = zone_map_ids | rem_zone_map_ids
                    stock_zones1 = stock_detail.filter(location__zone_id__in=zone_map_ids).order_by(order_by)
                    stock_zones2 = stock_detail.exclude(location__zone_id__in=all_zone_map_ids).order_by(order_by)
                    stock_zones3 = stock_detail.filter(location__zone_id__in=rem_zone_map_ids).order_by(order_by)
                    stock_detail = stock_zones1.union(stock_zones2, stock_zones3)
            elif fefo_enabled:
                if 'st_po' not in dir(order):
                    stock_detail1 = stock_detail.filter(batch_detail__expiry_date__isnull=False).\
                                                    order_by('batch_detail__expiry_date')
                    stock_detail2 = stock_detail.exclude(batch_detail__expiry_date__isnull=False).\
                                                    order_by(order_by)
                    stock_detail = list(chain(stock_detail1, stock_detail2))
            if seller_order and seller_order.order_status == 'DELIVERY_RESCHEDULED':
                rto_stocks = stock_detail.filter(location__zone__zone='RTO_ZONE')
                stock_detail = list(chain(rto_stocks, stock_detail))
            for stock in stock_detail:
                stock_count, stock_diff = get_stock_count(order, stock, stock_diff, user, order_quantity)
                if not stock_count:
                    continue

                picklist_data['reserved_quantity'] = stock_count
                picklist_data['stock_id'] = stock.id
                if 'st_po' in dir(order):
                    picklist_data['order_id'] = None
                else:
                    picklist_data['order_id'] = order.id
                picklist_data['status'] = status
                # enable_damaged_stock = request.POST.get('enable_damaged_stock', 'false')
                if enable_damaged_stock  == 'true':
                    picklist_data['damage_suggested'] = 1
                new_picklist = Picklist(**picklist_data)
                new_picklist.save()
                if seller_order:
                    create_seller_summary_details(seller_order, new_picklist)

                picklist_loc_data = {'picklist_id': new_picklist.id, 'status': 1, 'quantity': stock_count,
                                     'creation_date': datetime.datetime.now(),
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
                    # setattr(order, 'status', 0)
                    if seller_order:
                        seller_order.status = 0
                        seller_order.save()
                        sell_order = SellerOrder.objects.filter(order_id=order.id, status=1)
                        if not sell_order:
                            order.status = 0
                            order.save()
                    else:
                        order.status = 0
                        order.save()
                    break

            order.save()
    return stock_status, picklist_number


def picklist_location_suggestion(request, order, stock_detail, user, order_quantity, picklist_data,
                                 new_picklist_objs=[]):
    already_reserved = False
    stock_diff = 0
    consumed_qty = 0
    need_quantity = order_quantity
    for stock in stock_detail:
        stock_count, stock_diff = get_stock_count(order, stock, stock_diff, user, order_quantity,
                                                  already_reserved)
        need_quantity -= stock_count
        if 'st_po' in dir(order):
            picklist_data['order_id'] = None
        else:
            picklist_data['order_id'] = order.id
        if not stock_count:
            continue
        else:
            consumed_qty += stock_count
            picklist_data['stock_id'] = stock.id
            picklist_data['reserved_quantity'] = stock_count

        if not (picklist_data.get('stock_id', 0) and picklist_data.get('order_id', 0)):
            return 0, []

        exist_pick = Picklist.objects.filter(stock_id=picklist_data.get('stock_id', 0),
                                             order_id=picklist_data.get('order_id', 0),
                                             status__icontains='open')
        if not exist_pick:
            new_picklist = Picklist(**picklist_data)
            new_picklist.save()
        else:
            new_picklist = exist_pick[0]
            new_picklist.reserved_quantity += stock_count
            new_picklist.save()
        new_picklist_objs.append(new_picklist.id)
        seller_order = ""
        if seller_order:
            create_seller_summary_details(seller_order, new_picklist)

        if stock_count:
            picklist_loc_data = {'picklist_id': new_picklist.id, 'status': 1, 'quantity': stock_count,
                                 'creation_date': datetime.datetime.now(),
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
    if need_quantity > 0:
        picklist_data['reserved_quantity'] = need_quantity
        consumed_qty += need_quantity
        if 'stock_id' in picklist_data.keys():
            del picklist_data['stock_id']
        exist_pick = Picklist.objects.filter(stock_id=picklist_data.get('stock_id', 0),
                                             order_id=picklist_data.get('order_id', 0),
                                             status__icontains='open')
        if not exist_pick:
            new_picklist = Picklist(**picklist_data)
            new_picklist.save()
        else:
            new_picklist = exist_pick[0]
            new_picklist.reserved_quantity += stock_count
            new_picklist.save()
        new_picklist_objs.append(new_picklist.id)

    return consumed_qty, new_picklist_objs


def picklist_allocate_stock(request, user, picklists, stock):
    from outbound import picklist_location_suggestion

    remarks = 'Auto-generated Picklist'
    for picklist in picklists:
        needed_quantity = picklist.reserved_quantity
        picklist_data = {}
        picklist_data['stock_id'] = 0
        picklist_data['order_id'] = picklist.order.id
        picklist_data['sku_code'] = picklist.sku_code
        picklist_data['picklist_number'] = picklist.picklist_number
        picklist_data['reserved_quantity'] = 0
        picklist_data['picked_quantity'] = 0
        picklist_data['remarks'] = picklist.remarks
        picklist_data['order_type'] = picklist.order_type
        picklist_data['status'] = picklist.status
        consumed_qty, new_pc_locs = picklist_location_suggestion(request, picklist.order, stock, user,
                                                                 needed_quantity, picklist_data)
        if consumed_qty:
            picklist_data['remarks'] = remarks
        picklist.reserved_quantity -= float(consumed_qty)
        picklist.save()
        if consumed_qty:
            exist_pics = PicklistLocation.objects.filter(picklist_id=picklist.id, status=1, reserved__gt=0)
            update_picklist_locations(exist_pics, picklist, consumed_qty, 'true')
            if picklist.reserved_quantity == 0 and not picklist.picked_quantity:
                picklist.delete()


def open_orders_allocate_stock(request, user, sku_combos, sku_open_orders, all_seller_orders, seller_stocks,
                               stock_objs, picklist_order_mapping):
    switch_vals = {'marketplace_model': get_misc_value('marketplace_model', user.id),
                   'fifo_switch': get_misc_value('fifo_switch', user.id),
                   'no_stock_switch': get_misc_value('no_stock_switch', user.id),
                   'combo_allocate_stock': get_misc_value('combo_allocate_stock', user.id)}
    remarks = 'Auto-generated Picklist'
    consumed_qty = 0
    for open_order in sku_open_orders:
        picklist_number = picklist_order_mapping.get(open_order.original_order_id, '')
        if not picklist_number:
            picklist_number = get_picklist_number(user)
            picklist_order_mapping[open_order.original_order_id] = picklist_number
        seller_orders = all_seller_orders.filter(order_id=open_order.id).order_by('order__shipment_date')
        if seller_orders:
            for seller_order in seller_orders:
                sku_stocks = stock_objs
                seller_stock_dict = filter(lambda person: str(person['seller_id']) == str(seller_order.seller_id),
                                           seller_stocks)
                if seller_stock_dict:
                    sell_stock_ids = map(lambda person: person['stock_id'], seller_stock_dict)
                    sku_stocks = sku_stocks.filter(id__in=sell_stock_ids)
                else:
                    sku_stocks = sku_stocks.filter(id=0)
                stock_status, picklist_number = picklist_generation([seller_order], 'false', picklist_number, user,
                                                                    sku_combos, sku_stocks, switch_vals, status='open',
                                                                    remarks=remarks, is_seller_order=True)
        else:
            stock_status, picklist_number = picklist_generation([open_order], 'false', picklist_number, user,
                                                                sku_combos, stock_objs, switch_vals, status='open', remarks=remarks)
    return picklist_order_mapping


def check_auto_stock_availability(stock, user):
    zones_data, available_quantity = get_sku_stock_summary(stock, '', user)
    avail_qty = sum(map(lambda d: available_quantity[d] if available_quantity[d] > 0 else 0, available_quantity))
    return avail_qty


def order_allocate_stock(request, user, stock_data=[], mapping_type=''):
    """Allocates the newly added stock to Order or Picklist"""

    try:
        log.info('Auto Allocate Stock function for %s and params are %s' % (str(user.username), str(stock_data)))
        picklist_order_mapping = {}
        all_skus = stock_data.keys()
        picklist_exclude_zones = get_exclude_zones(user)
        all_order_mapping = OrderMapping.objects.none()
        if mapping_type:
            mapping_dict = {'mapping_type': mapping_type, 'order__sku_id__in': all_skus}
            all_order_mapping = OrderMapping.objects.filter(order__user=user.id, **mapping_dict)
        auto_allocate = False
        if get_misc_value('auto_allocate_stock', user.id) == 'true':
            auto_allocate = True
        all_open_picklists = Picklist.objects.filter(order__user=user.id, status__icontains='open', stock__isnull=True)
        sku_combos = SKURelation.objects.none()

        all_open_orders = OrderDetail.objects.filter(user=user.id, quantity__gt=0, status=1, sku_id__in=all_skus)
        all_seller_orders = SellerOrder.objects.prefetch_related('order__sku').filter(order__user=user.id,
                                                                                      order__status=1,
                                                                                      quantity__gt=0,
                                                                                      order__sku_id__in=all_skus)
        seller_stocks = SellerStock.objects.filter(seller__user=user.id, quantity__gt=0, stock__sku_id__in=all_skus). \
            values('stock_id', 'seller_id')
        sku_stocks = StockDetail.objects.prefetch_related('sku', 'location'). \
            exclude(Q(receipt_number=0) | Q(location__zone__zone__in=picklist_exclude_zones)). \
            filter(sku__user=user.id, quantity__gt=0, sku_id__in=all_skus)

        for sku_id, mapping_ids in stock_data.iteritems():
            stock = sku_stocks.filter(sku_id=sku_id)
            sku = stock[0].sku
            sku_open_orders = all_open_orders.filter(sku_id=sku_id)
            picklists = all_open_picklists.filter(Q(order__sku_id=sku_id, order_type='') |
                                                  Q(sku_code=sku.sku_code, order_type='combo')). \
                order_by('order__creation_date')
            if mapping_ids:
                picklist_filter = {}
                order_mapping = all_order_mapping.filter(mapping_id__in=mapping_ids)
                if order_mapping:
                    picklist_filter['order_id__in'] = order_mapping.values_list('order_id', flat=True)
                # If Order Mapping exists then stock allocation for picklists or orders
                if picklist_filter:
                    # Stock Allocation for open picklists with NO STOCK
                    picklist_allocate_stock(request, user, picklists.filter(**picklist_filter), stock)

                    avail_qty = check_auto_stock_availability(stock, user)
                    if avail_qty <= 0:
                        continue

                    # Stock Allocation for open orders in view orders.
                    open_order_args = [request, user, sku_combos]
                    open_order_args.append(sku_open_orders.filter(id__in=picklist_filter['order_id__in']))
                    open_order_args.append(all_seller_orders)
                    open_order_args.append(seller_stocks)
                    open_order_args.append(stock)
                    open_order_args.append(picklist_order_mapping)
                    picklist_order_mapping = open_orders_allocate_stock(*open_order_args)

            # If auto stock allocation is on then stock allocation will happen for picklists or orders
            if auto_allocate:
                avail_qty = check_auto_stock_availability(stock, user)
                if avail_qty <= 0:
                    continue

                # Stock Allocation for open picklists with NO STOCK
                if picklists:
                    picklist_allocate_stock(request, user, picklists, stock)

                if avail_qty <= 0:
                    continue

                # Stock Allocation for open orders in view orders.
                open_order_args = [request, user, sku_combos, sku_open_orders, all_seller_orders, seller_stocks]
                open_order_args.append(stock)
                open_order_args.append(picklist_order_mapping)
                picklist_order_mapping = open_orders_allocate_stock(*open_order_args)

        suggested_picklist_numbers = list(set(picklist_order_mapping.values()))
        for pick_number in suggested_picklist_numbers:
            check_picklist_number_created(user, pick_number+1)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Auto Allocate Stock function failed for %s and params are %s and error statement is %s' %
                 (str(user.username), str(stock_data), str(e)))


@login_required
@get_admin_user
def get_user_profile_data(request, user=''):
    ''' return user profile data '''

    data = {'name': user.username, 'email': user.email}
    main_user = UserProfile.objects.get(user_id=user.id)
    data['address'] = main_user.address
    data['gst_number'] = main_user.gst_number
    data['main_user'] = request.user.is_staff
    data['company_name'] = main_user.company_name
    data['cin_number'] = request.user.userprofile.cin_number
    data['wh_address'] = main_user.wh_address
    data['wh_phone_number'] = main_user.wh_phone_number
    data['pan_number'] = main_user.pan_number
    data['phone_number'] = main_user.phone_number
    return HttpResponse(json.dumps({'msg': 1, 'data': data}))

@login_required
@get_admin_user
def get_user_profile_shipment_addresses(request, user=''):
    ''' return user profile Shipment Addresses '''
    ship_address_details = []
    user_ship_address = UserAddresses.objects.filter(user_id=user.id)
    if user_ship_address:
        for data in user_ship_address:
            ship_address_details.append({'title':data.address_name,'addr_name':data.user_name,'mobile_number':data.mobile_number,'pincode':data.pincode,'address':data.address})
        return HttpResponse(json.dumps({'msg': 1, 'data': ship_address_details}))
    else:
        return HttpResponse(json.dumps({'msg': 1, 'data': 'null'}))

@login_required
@get_admin_user
def get_cust_profile_info(request, user=''):
    data = {'user_id': request.POST.get('user_id','')}
    customer_info = UserProfile.objects.get(user_id=request.POST.get('user_id',''))
    data['address'] = customer_info.address
    data['gst_number'] = customer_info.gst_number
    data['phone_number'] = customer_info.phone_number
    data['bank_details'] = customer_info.bank_details
    if customer_info.customer_logo:
        data['logo'] = customer_info.customer_logo.url
    return HttpResponse(json.dumps({'message': 1, 'data': data}, cls=DjangoJSONEncoder))


@csrf_exempt
@login_required
@get_admin_user
def change_user_password(request, user=''):
    resp = {'msg': 0, 'data': 'Successfully Updated'}
    try:
        log.info('Change Password  for user %s , %s' % (str(request.user.id), str(request.user.username)))

        old_password = request.POST.get('old_password', '')
        if not request.user.check_password(old_password):
            resp['data'] = 'Invalid Old Password'
            return HttpResponse(json.dumps(resp))
        new_password = request.POST.get('new_password', '')
        retype_password = request.POST.get('retype_password', '')
        if not new_password:
            resp['data'] = 'New Password Should Not Be Empty'
            return HttpResponse(json.dumps(resp))
        if not retype_password:
            resp['data'] = 'Retype Password Should Not Be Empty'
            return HttpResponse(json.dumps(resp))
        if new_password != retype_password:
            resp['data'] = 'New Password and Retype Password Should Be Same'
            return HttpResponse(json.dumps(resp))
        if old_password == new_password:
            resp['data'] = 'Old Password and New Password Should Be Same'
            return HttpResponse(json.dumps(resp))

        resp['msg'] = 1
        request.user.set_password(new_password)
        request.user.save()
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Change Password Faild User ' + str(request.user.username))
        resp['data'] = 'Password Updation Fail'
    return HttpResponse(json.dumps(resp))


@csrf_exempt
@login_required
@get_admin_user
def update_profile_data(request, user=''):
    ''' will update profile data '''

    address = request.POST.get('address', '')
    gst_number = request.POST.get('gst_number', '')
    company_name = request.POST.get('company_name', '')
    email = request.POST.get('email', '')
    cin_number = request.POST.get('cin_number', '')
    pan_number = request.POST.get('pan_number', '')
    wh_address = request.POST.get('wh_address', '')
    wh_phone_number = request.POST.get('wh_phone_number', '')
    phone_number = request.POST.get('phone_number', '')
    main_user = UserProfile.objects.get(user_id=user.id)
    main_user.address = address
    main_user.gst_number = gst_number
    main_user.company_name = company_name
    main_user.cin_number = cin_number
    main_user.wh_address = wh_address
    main_user.wh_phone_number = wh_phone_number
    main_user.phone_number = phone_number
    main_user.pan_number = pan_number
    main_user.save()
    user.email = email
    user.save()
    return HttpResponse('Success')

@csrf_exempt
@login_required
@get_admin_user
def update_profile_shipment_address(request, user=''):
    ''' will update profile Shipment Address '''
    try:
        shipment_address = {}
        shipment_address['address_type'] = 'Shipment Address'
        shipment_address['address_name'] = request.POST.get('address_title', '')
        shipment_address['user_name'] = request.POST.get('address_name', '')
        shipment_address['mobile_number'] = request.POST.get('address_mobile_number', '')
        shipment_address['pincode'] = request.POST.get('address_pincode', '')
        shipment_address['address'] = request.POST.get('address_shipment', '')
        shipment_address['user_id'] = user.id
        UserAddresses.objects.create(**shipment_address)
        return HttpResponse('Success')
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('updation of user shipment Address Failed %s ' % (str(user.username)))


@csrf_exempt
@login_required
@get_admin_user
def update_barcode_configuration(request, user=''):
    "Different BarCode Configurations will be stored based"
    scanning_type = request.POST.get('scanning_type', 'sku_based')
    config_name = request.POST.get('configuration_title', '')
    removeAfterSpacesFlag = request.POST.get('remove_after_spaces', 'false')
    condition1 = request.POST.get('condition1', '')
    expression1 = request.POST.get('expression1', '')
    condition2 = request.POST.get('condition2', '')
    expression2 = request.POST.get('expression2', '')
    miscOptionsDict = {'scanning_type': scanning_type, 'remove_after_spaces': removeAfterSpacesFlag}
    if condition1 and expression1:
        miscOptionsDict.update({'condition1': condition1, 'expression1': expression1})
    if condition2 and expression2:
        miscOptionsDict.update({'condition2': condition2, 'expression2': expression2})

    miscExistingObj = MiscDetail.objects.filter(misc_type__contains='barcode_configuration', user=user.id, misc_value=config_name)
    configId = 1
    if not miscExistingObj.exists():
        dbMaxConfigId = MiscDetail.objects.filter(misc_type__contains='barcode_configuration', 
                    user=user.id).order_by('-id').values_list('misc_type', flat=True)
        if dbMaxConfigId:
            configId = int(dbMaxConfigId[0].split('_')[-1])+1
        miscObj = MiscDetail.objects.create(misc_type='barcode_configuration_%s'%configId, misc_value=config_name, user=user.id)
    else:
        miscObj = miscExistingObj[0]
    for k, v in miscOptionsDict.items():
        MiscDetailOptions.objects.create(misc_detail=miscObj, misc_key=k, misc_value=v)
    return HttpResponse('Success')


@login_required
@get_admin_user
def get_barcode_configurations(request, user=''):
    barcode_configs = []
    barcodeConfigs = MiscDetail.objects.filter(user=user.id, misc_type__contains='barcode_configuration')
    if barcodeConfigs.exists():
        for eachConfig in barcodeConfigs:
            configDict = {'title': eachConfig.misc_value}
            for configData in eachConfig.miscdetailoptions_set.values():
                configDict.update({configData['misc_key']: configData['misc_value']})
            barcode_configs.append(configDict)
        return HttpResponse(json.dumps({'msg':1, 'data': barcode_configs}))
    else:
        return HttpResponse(json.dumps({'msg':1, 'data': 'null'}))


def check_and_return_barcodeconfig_sku(user, sku_code, sku_brand):
    configName = ''
    conditions = {}
    configMappingObj = BarCodeBrandMappingMaster.objects.filter(sku_brand=sku_brand, user=user)
    if configMappingObj.exists():
        configName = configMappingObj[0].configName
    brandConfigObj = MiscDetail.objects.filter(user=user.id, misc_type__contains='barcode_configuration', misc_value=configName)
    if brandConfigObj.exists():
        conditions = dict(brandConfigObj[0].miscdetailoptions_set.values_list('misc_key', 'misc_value'))
    for k, v in conditions.items():
        if k == 'remove_after_spaces' and v == 'true':
            sku_code = sku_code.split(' ')[0]
        elif k == 'condition1':
            vThChar = sku_code[int(v)-1]
            if sku_code[int(v)-1].isdigit():
                expression1Char = int(conditions.get('expression1'))
                sku_code = sku_code[:expression1Char]
        elif k == 'condition2':
            vThChar = sku_code[int(v)-1]
            if sku_code[int(v)-1].isalpha():
                expression2Char = int(conditions.get('expression2'))
                sku_code = sku_code[:expression2Char]
    return sku_code


def get_purchase_company_address(profile):
    """ Returns Company address for purchase order"""

    company_address = profile.address
    if profile.wh_address:
        address = profile.wh_address
    else:
        address = profile.address
    if not (address and company_address):
        return '', ''
    if profile.user.email:
        address = ("%s, Email:%s") % (address, profile.user.email)
        company_address = ("%s, Email:%s") % (company_address, profile.user.email)
    if profile.phone_number:
        #address = ("%s, Phone:%s") % (address, profile.phone_number)
        company_address = ("%s, Phone:%s") % (company_address, profile.phone_number)
    if profile.gst_number:
        #address = ("%s, GSTINo:%s") % (address, profile.gst_number)
        company_address = ("%s, GSTINo:%s") % (company_address, profile.gst_number)
    return address, company_address


def update_level_price_type(customer_master, level, price_type):
    """ Check and update price types """
    if level == 2:
        warehouse_mapping = WarehouseCustomerMapping.objects.filter(customer_id=customer_master.id)
        cus_price_types = customer_master.customerpricetypes_set.filter(level=level)
        if cus_price_types and not warehouse_mapping:
            price_type = cus_price_types[0].price_type
    return price_type


def create_grouping_order_for_generic(generic_order_id, order_detail, cm_id, wh, stock_cnt, corporate_po_number,
                                      client_name, order_unit_price, el_price, del_date):
    order_detail_map = {'generic_order_id': generic_order_id,
                        'orderdetail_id': order_detail.id,
                        'customer_id': cm_id,
                        'cust_wh_id': wh,
                        'po_number': corporate_po_number,
                        'client_name': client_name,
                        'el_price': el_price,
                        }
    if del_date:
        order_detail_map['schedule_date'] = del_date
    gen_ord_dt_map_obj = GenericOrderDetailMapping.objects.filter(**order_detail_map)
    order_detail_map['quantity'] = stock_cnt
    order_detail_map['unit_price'] = order_unit_price
    log.info("OrderDETAILMAP::" + repr(order_detail_map))
    if not gen_ord_dt_map_obj:
        ord_det_mapping = GenericOrderDetailMapping(**order_detail_map)
        ord_det_mapping.save()


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


def create_generic_order(order_data, cm_id, user_id, generic_order_id, order_objs, is_distributor,
                         order_summary_dict, ship_to, corporate_po_number, client_name, admin_user, sku_total_qty_map,
                         order_user_sku, order_user_objs, address_selected=''):
    if order_data.get('del_date', ''):
        if order_data['del_date'] >= order_data['shipment_date']:
            order_data['shipment_date'] = order_data.get('del_date', '')
        else:
            order_data['del_date'] = order_data['shipment_date']
    order_data1 = copy.deepcopy(order_data)
    order_data_excluding_keys = ['warehouse_level', 'margin_data', 'el_price', 'del_date']
    order_unit_price = order_data1['unit_price']
    el_price = order_data1.get('el_price', 0)
    del_date = order_data1.get('del_date', '')
    if not is_distributor:

        sku_code = order_data1['sku_code']
        qty = order_data1['quantity']
        if isinstance(sku_total_qty_map[sku_code], list):
            total_qty = sku_total_qty_map[sku_code][0]
        else:
            total_qty = sku_total_qty_map[sku_code]
        price_ranges_map = fetch_unit_price_based_ranges(user_id, order_data1['warehouse_level'],
                                                         admin_user.id, sku_code)
        if price_ranges_map.has_key('price_ranges'):
            max_unit_ranges = [i['max_unit_range'] for i in price_ranges_map['price_ranges']]
            highest_max = max(max_unit_ranges)
            for each_map in price_ranges_map['price_ranges']:
                min_qty, max_qty, price = each_map['min_unit_range'], each_map['max_unit_range'], each_map['price']
                if min_qty <= total_qty <= max_qty:
                    order_data1['unit_price'] = price
                    invoice_amount = get_tax_inclusive_invoice_amt(cm_id, price, qty, user_id, sku_code, admin_user)
                    order_data1['invoice_amount'] = invoice_amount
                    break
                elif max_qty >= highest_max:
                    order_data1['unit_price'] = price
                    invoice_amount = get_tax_inclusive_invoice_amt(cm_id, price, qty, user_id, sku_code, admin_user)
                    order_data1['invoice_amount'] = invoice_amount


        dist_order_copy = copy.deepcopy(order_data1)
        # dist_order_copy['user'] = user_id
        customer_user = WarehouseCustomerMapping.objects.filter(warehouse_id=user_id)
        if customer_user:
            dist_order_copy['customer_id'] = customer_user[0].customer.customer_id
            dist_order_copy['customer_name'] = customer_user[0].customer.name
            dist_order_copy['telephone'] = customer_user[0].customer.phone_number
            dist_order_copy['email_id'] = customer_user[0].customer.email_id
            dist_order_copy['address'] = customer_user[0].customer.address
            if address_selected == 'Your Address':  # If reseller selects his address while placing order.
                ship_to = CustomerMaster.objects.get(id=cm_id).address
        order_obj = OrderDetail.objects.filter(order_id=dist_order_copy['order_id'],
                                               sku_id=dist_order_copy['sku_id'],
                                               order_code=dist_order_copy['order_code'],
                                               user=dist_order_copy['user'])
        if not order_obj:
            for exc_key in order_data_excluding_keys:
                if exc_key in dist_order_copy:
                    dist_order_copy.pop(exc_key)
            order_detail = OrderDetail(**dist_order_copy)
            order_detail.save()
        else:
            order_detail = order_obj[0]

    else:
        order_obj = OrderDetail.objects.filter(order_id=order_data1['order_id'],
                                               sku_id=order_data1['sku_id'],
                                               order_code=order_data1['order_code'])
        dist_order_copy = copy.deepcopy(order_data)
        # Distributor can place order directly to any wh/distributor
        for exc_key in order_data_excluding_keys:
            if exc_key in dist_order_copy:
                dist_order_copy.pop(exc_key)

        if not order_obj:
            order_detail = OrderDetail(**dist_order_copy)
            order_detail.save()
        else:
            order_detail = order_obj[0]

    order_summary_dict['order_id'] = order_detail.id
    create_ordersummary_data(order_summary_dict, order_detail, ship_to)
    order_objs.append(order_detail)

    # Collecting needed data for Picklist generation
    order_user_sku.setdefault(order_detail.user, {})
    order_user_sku[order_detail.user].setdefault(order_detail.sku, 0)
    order_user_sku[order_detail.user][order_detail.sku] += order_data1['quantity']

    # Collecting User order objs for picklist generation
    order_user_objs.setdefault(order_detail.user, [])
    order_user_objs[order_detail.user].append(order_detail)

    create_grouping_order_for_generic(generic_order_id, order_detail, cm_id, order_data1['user'], order_data1['quantity'],
                                      corporate_po_number, client_name, order_unit_price, el_price, del_date)


def create_ordersummary_data(order_summary_dict, order_detail, ship_to, courier_name=''):
    order_summary_dict['order_id'] = order_detail.id
    order_summary_dict['consignee'] = ship_to
    order_summary_dict['courier_name'] = courier_name
    order_summary = CustomerOrderSummary(**order_summary_dict)
    order_summary.save()


def get_priceband_admin_user(user):
    if isinstance(user, long):
        price_band_flag = get_misc_value('priceband_sync', user)
    else:
        price_band_flag = get_misc_value('priceband_sync', user.id)
    if price_band_flag == 'true':
        admin_user = get_admin(user)
    else:
        admin_user = None
    return admin_user

def order_push(order_id, user, order_status="NEW"):
    #cal integration_get_order
    response = {}
    integrations = Integrations.objects.filter(user=user.id, status=1)
    from rest_api.views.easyops_api import *
    for integrate in integrations:
        integration_module = importlib.import_module("rest_api.views.%s" % (integrate.name))
        order_dict = integration_module.integration_get_order(order_id, user, order_status)
        obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
        response = obj.qssi_order_push(data=order_dict, user=user)
    return response


def get_inventory(sku_ids, user):
    #get inventory API call
    response = {}
    integrations = Integrations.objects.filter(user=user.id, status=1)
    from rest_api.views.easyops_api import *
    for integrate in integrations:
        integration_module = importlib.import_module("rest_api.views.%s" % (integrate.name))
        sku_dict = integration_module.integration_get_inventory(sku_ids, user) if isinstance(sku_ids, list)\
                   else sku_ids
        obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
        response = obj.qssi_get_inventory(sku_dict, user=user)
    return response


def order_status_update(order_ids, user):
    #update order status API call
    response = {}
    integrations = Integrations.objects.filter(user=user.id, status=1)
    from rest_api.views.easyops_api import *
    for integrate in integrations:
        integration_module = importlib.import_module("rest_api.views.%s" % (integrate.name))
        order_id_dict = integration_module.integration_get_order_status(order_ids, user)
        log_qssi.info("Order status request: %s" %(str(order_id_dict)))
        obj = eval(integrate.api_instance)(company_name=integrate.name, user=user)
        response = obj.qssi_get_order_status(order_id_dict, user=user)
    return response


def get_tax_inclusive_invoice_amt(cm_id, unit_price, qty, usr, sku_code, admin_user=''):
    usr_sku_master = SKUMaster.objects.filter(user=usr, sku_code=sku_code)
    if usr_sku_master:
        product_type = usr_sku_master[0].product_type
    else:
        log.info('No SKUMaster for user(%s) and sku_code(%s)' %(usr, sku_code))
        product_type = ''
    customer_master = CustomerMaster.objects.get(id=cm_id)
    taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0}
    if customer_master.tax_type:
        inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
        inter_state = inter_state_dict.get(customer_master.tax_type, 2)
        if admin_user:
            tax_master = TaxMaster.objects.filter(user_id=admin_user, inter_state=inter_state,
                                                  product_type=product_type,
                                                  min_amt__lte=unit_price, max_amt__gte=unit_price)
        else:
            tax_master = TaxMaster.objects.filter(user_id=usr, inter_state=inter_state,
                                                  product_type=product_type,
                                                  min_amt__lte=unit_price, max_amt__gte=unit_price)
        if tax_master:
            tax_master = tax_master[0]
            taxes['cgst_tax'] = float(tax_master.cgst_tax)
            taxes['sgst_tax'] = float(tax_master.sgst_tax)
            taxes['igst_tax'] = float(tax_master.igst_tax)
            taxes['utgst_tax'] = float(tax_master.utgst_tax)
    invoice_amount = qty * unit_price
    invoice_amount = invoice_amount + ((invoice_amount / 100) * sum(taxes.values()))
    return invoice_amount


def get_level_name_with_level(user, warehouse_level, users_list=[]):
    ''' Getting Level name by using level'''
    if warehouse_level == 0:
        return 'L0-Source Distributor'
    if not users_list:
        central_admin = get_admin(user)
        users_list = UserGroups.objects.filter(admin_user=central_admin.id).values_list('user').distinct()
    level_name = 'Level-%s' % (str(warehouse_level))
    level_name_objs = UserProfile.objects.exclude(level_name='').filter(user_id__in=users_list,
                                                                        warehouse_level=warehouse_level)
    if level_name_objs:
        level_name = level_name_objs[0].level_name
    return level_name

def get_supplier_info(request):
    supplier_user = ''
    supplier = ''
    supplier_parent = ''
    profile = UserProfile.objects.get(user=request.user)
    if profile.user_type == 'supplier':
        supplier_data = UserRoleMapping.objects.get(user=request.user, role_type='supplier')
        supplier = SupplierMaster.objects.get(id = supplier_data.role_id)
        supplier_parent = User.objects.get(id = supplier.user)
        return True, supplier_data, supplier, supplier_parent
    return False, supplier_user, supplier, supplier_parent

def create_new_supplier(user, supp_name, supp_email, supp_phone, supp_address, supp_tin):
    ''' Create New Supplier with dynamic supplier id'''
    max_sup_id = SupplierMaster.objects.count()
    run_iterator = 1
    supplier_id = ''
    while run_iterator:
        supplier_obj = SupplierMaster.objects.filter(id=max_sup_id)
        if not supplier_obj:
            supplier_master, created = SupplierMaster.objects.get_or_create(id=max_sup_id, user=user.id,
                                                                            name=supp_name,
                                                                            email_id=supp_email,
                                                                            phone_number=supp_phone,
                                                                            address=supp_address,
                                                                            tin_number=supp_tin,
                                                                            status=1)
            run_iterator = 0
            supplier_id = supplier_master.id
        else:
            max_sup_id += 1
    return supplier_id


def create_order_pos(user, order_objs, admin_user=None):
    ''' Creating Sampling PO for orders'''
    po_id = ''
    customer_id = ''
    try:
        cust_supp_mapping = {}
        user_profile = UserProfile.objects.get(user_id=user.id)
        po_id = get_purchase_order_id(user) + 1
        po_sub_user_prefix = get_misc_value('po_sub_user_prefix', user.id)
        if po_sub_user_prefix == 'true':
            po_id = update_po_order_prefix(user, po_id)
        for order_obj in order_objs:
            if order_obj.customer_id:
                customer_id = str(int(order_obj.customer_id))
            order_map_check = OrderMapping.objects.filter(mapping_type='PO', order_id=order_obj.id)
            if order_map_check.exists():
                continue
            if customer_id not in cust_supp_mapping.keys():
                if admin_user:
                    cust_master = CustomerMaster.objects.filter(customer_id=customer_id, user=admin_user.id)
                else:
                    cust_master = CustomerMaster.objects.filter(customer_id=customer_id, user=user.id)
                if cust_master:
                    cust_master = cust_master[0]
                    master_mapping = MastersMapping.objects.filter(master_id=cust_master.id,
                                                                   mapping_type='customer-supplier', user=user.id)
                    if not master_mapping:
                        supplier_id = create_new_supplier(user, cust_master.name, cust_master.email_id,
                                                          cust_master.phone_number, cust_master.address,
                                                          cust_master.tin_number)
                        if supplier_id:
                            mapping_obj = MastersMapping.objects.create(master_id=cust_master.id, mapping_id=supplier_id,
                                                          mapping_type='customer-supplier', user=user.id,
                                                          creation_date=datetime.datetime.now())
                            cust_supp_mapping[str(cust_master.customer_id)] = supplier_id
                    else:
                        cust_supp_mapping[str(cust_master.customer_id)] = master_mapping[0].mapping_id
            if not cust_supp_mapping.get(customer_id, ''):
                continue
            taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'utgst_tax': 0}
            cust_order_summary = order_obj.customerordersummary_set.filter()
            if cust_order_summary:
                taxes = cust_order_summary.values('cgst_tax', 'sgst_tax', 'igst_tax', 'utgst_tax')[0]
            supplier_id = cust_supp_mapping[str(customer_id)]
            po_reference = order_obj.original_order_id
            purchase_data = copy.deepcopy(PO_DATA)
            po_sku_data = copy.deepcopy(PO_SUGGESTIONS_DATA)
            sku = order_obj.sku
            po_sku_data['supplier_id'] = supplier_id
            po_sku_data['wms_code'] = sku.sku_code
            po_sku_data['sku_id'] = sku.id
            po_sku_data['order_quantity'] = order_obj.quantity
            po_sku_data['price'] = order_obj.unit_price
            po_sku_data['measurement_unit'] = sku.measurement_type
            po_sku_data['order_type'] = 'SP'
            po_sku_data['status'] = 0
            po_sku_data['po_name'] = po_reference
            po_sku_data.update(taxes)
            create_po = OpenPO(**po_sku_data)
            create_po.save()
            purchase_data['open_po_id'] = create_po.id
            purchase_data['order_id'] = po_id
            if user_profile:
                purchase_data['prefix'] = user_profile.prefix
            order = PurchaseOrder(**purchase_data)
            order.save()
            OrderMapping.objects.create(mapping_id=order.id, mapping_type='PO', order_id=order_obj.id,
                                        creation_date=datetime.datetime.now())
        if len(order_objs):
            log.info("Sampling PO Creation for the user %s is PO number %s created for Order Id %s " % (user.username,
                                                                str(po_id), str(order_objs[0].original_order_id)))
        else:
            log.info("Sampling PO Creation for the user %s is PO number %s created for Order Id %s " % (user.username,
                                                                str(po_id), '' ))
        check_purchase_order_created(user, po_id)
    except Exception as e:
        if po_id:
            check_purchase_order_created(user, po_id)
        import traceback
        log.debug(traceback.format_exc())
        log.info('Sampling PO Creation failed for %s and params are %s and error statement is %s' % (
            str(user.username), str(order_objs), str(e)))

def get_customer_based_price(customer_obj, price, mrp,is_sellingprice='', user_id=''):
    if is_sellingprice == '':
        customer_price = get_misc_value('calculate_customer_price', user_id)
        is_sellingprice = False
        if customer_price == 'price':
            is_sellingprice = True
    if is_sellingprice and customer_obj.discount_percentage:
        price = price * float(1 - float(customer_obj.discount_percentage) / 100)
    elif customer_obj.markup:
        price = price * float(1 + float(customer_obj.markup) / 100)
        if mrp and price > mrp:
            price = mrp
    if not mrp:
        mrp = price
    return price, mrp


def get_price_field(user):
    calc_customer_price = get_misc_value('calculate_customer_price', user.id)
    price_field = 'cost_price'
    if calc_customer_price == 'price':
        price_field = 'price'
    return price_field


def save_sku_stats(user, sku_id, transact_id, transact_type, quantity, stock_detail=None, stock_stats_objs=None,
                   bulk_insert=False):
    try:
        stats_dict = {'sku_id': sku_id, 'transact_id': transact_id, 'transact_type': transact_type,
                                  'quantity': quantity, 'creation_date': datetime.datetime.now(),
                      'stock_detail': stock_detail}
        if bulk_insert:
            stock_stats_objs.append(SKUDetailStats(**stats_dict))
            return stock_stats_objs
        else:
            SKUDetailStats.objects.create(**stats_dict)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        result_data = []
        log.info('Save SKU Detail Stats failed for %s and sku id is %s and error statement is %s' % (
            str(user.username), str(sku_id), str(e)))


def get_view_order_statuses(request, user):
    view_order_status = get_misc_value('extra_view_order_status', user.id)
    if view_order_status == 'false':
        view_order_status = ''
    if not view_order_status:
        return view_order_status, False
    view_order_status = view_order_status.split(',')
    if not request.user.is_staff:
        view_order_status = list(GroupPermMapping.objects.filter(group__user__id=request.user.id, status=1).\
                                        values_list('perm_value', flat=True).distinct().order_by('sequence'))
    return view_order_status, True


def update_created_extra_status(user, selection):
    """ If the sequence changed or updated for view order status"""
    sub_users = get_related_users(user.id)
    status_selected = selection.split(',')
    for sub_user in sub_users:
        grp_perm_map = GroupPermMapping.objects.filter(group__user__id=sub_user)
        exist_grp_sequence = list(grp_perm_map.filter(status=1).\
            values_list('perm_value', flat=True).distinct().order_by('sequence'))
        if exist_grp_sequence != status_selected:
            for sequence, grp_perm in enumerate(grp_perm_map):
                if grp_perm.perm_value not in status_selected:
                    grp_perm.status = 0
                    grp_perm.sequence = 0
                    grp_perm.save()
                else:
                    grp_perm.sequence = status_selected.index(grp_perm.perm_value)
                    grp_perm.status = 1
                    grp_perm.save()


def get_user_attributes(user, attr_model):
    attributes = []
    if attr_model:
        attributes = UserAttributes.objects.filter(user_id=user.id, status=1, attribute_model=attr_model).\
                                        values('id', 'attribute_model', 'attribute_name', 'attribute_type')
    return attributes


@csrf_exempt
@login_required
@get_admin_user
def get_user_attributes_list(request, user=''):
    attr_model = request.GET.get('attr_model')
    attributes = get_user_attributes(user, 'sku')
    return HttpResponse(json.dumps({'data': list(attributes), 'status': 1}))


def get_invoice_types(user):
    invoice_types = get_misc_value('invoice_types', user.id)
    if invoice_types in ['', 'false']:
        invoice_types = ['Tax Invoice']
    else:
        invoice_types = invoice_types.split(',')
    return invoice_types


def get_mode_of_transport(user):
    mode_of_transport = get_misc_value('mode_of_transport', user.id)
    if mode_of_transport:
        mode_of_transport = mode_of_transport.split(',')
    return mode_of_transport


def get_max_seller_transfer_id(user):
    trans_id = get_incremental(user, 'seller_stock_transfer')
    return trans_id


def get_max_combo_allocation_id(user):
    ''' Returns Max ID for Combo Allocation for Substitute Summary table'''
    trans_id = get_incremental(user, 'combo_allocation')
    return trans_id


def get_max_substitute_allocation_id(user):
    ''' Returns Max ID for Substitute Allocation for Substitute Summary table'''
    trans_id = get_incremental(user, 'substitute_allocation')
    return trans_id


def write_excel(ws, data_count, ind, val, file_type='xls'):
    if file_type == 'xls':
        ws.write(data_count, ind, val)
    else:
        try:
            val = str(val).replace(',', '  ').replace('\n', '').replace('"', "\'")
            ws = ws + val + ','
        except Exception as e:
            ws = ws + val + ','
            import traceback
            log.debug(traceback.format_exc())
            log.info('Writing Data to excel failed for %s ' % val)
    return ws


@csrf_exempt
@login_required
@get_admin_user
def update_mail_alerts(request, user=''):
    alert_name = request.GET.get('alert_name', '')
    alert_value = request.GET.get('alert_value', '')
    to_delete = request.GET.get('delete', '')
    try:
        log.info("Update Mail Alerts for user %s and request params are %s" %
                 (str(user.username), str(request.GET.dict())))
        if alert_name and alert_value:
            mail_alert_obj = MailAlerts.objects.filter(user_id=user.id, alert_name=alert_name)
            if mail_alert_obj:
                if to_delete == 'true':
                    mail_alert_obj.delete()
                else:
                    mail_alert_obj = mail_alert_obj[0]
                    mail_alert_obj.alert_value = alert_value
                    mail_alert_obj.save()
            else:
                MailAlerts.objects.create(user_id=user.id, alert_name=alert_name, alert_type='days',
                                          alert_value=alert_value, creation_date=datetime.datetime.now())
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        result_data = []
        log.info('Update Remainder Mail alerts failed for %s and request is %s and error statement is %s' % (
            str(user.username), str(request.GET.dict()), str(e)))
    return HttpResponse("Success")


def update_order_batch_details(user, order):
    picklists = order.picklist_set.filter()
    batch_data = {}
    for picklist in picklists:
        pick_locs = picklist.picklistlocation_set.filter(stock__isnull=False)
        for pick in pick_locs:
            if pick.stock.batch_detail:
                batch_detail = picklist.stock.batch_detail
                mfg_date = ''
                if batch_detail.manufactured_date:
                    mfg_date = batch_detail.manufactured_date.strftime('%m/%d/%Y')
                exp_date = ''
                if batch_detail.expiry_date:
                    exp_date = batch_detail.expiry_date.strftime('%m/%d/%Y')
                group_key = '%s:%s:%s' % (str(batch_detail.mrp), str(batch_detail.manufactured_date),
                                          str(batch_detail.expiry_date))
                batch_data.setdefault(group_key, {'mrp': batch_detail.mrp, 'manufactured_date': mfg_date,
                                                   'expiry_date': exp_date, 'quantity': 0,
                                                  'buy_price': batch_detail.buy_price,
                                                  'tax_percent': batch_detail.tax_percent})
                batch_data[group_key]['quantity'] += pick.quantity
    return batch_data.values()

def allocate_order_returns(user, sku_data, request):
    excl_filter = {}
    data = {}
    order_filter = {'user': user.id, 'sku_id': sku_data.id}
    if request.GET.get('marketplace', ''):
        order_filter['marketplace'] = request.GET.get('marketplace', '')
    if request.GET.get('seller_id', ''):
        order_filter['sellerorder__seller__seller_id'] = request.GET.get('seller_id', '').split(':')[0]
    if request.GET.get('exclude_order_ids', []):
        excl_filter['original_order_id__in'] = request.GET.get('exclude_order_ids', []).split(',')
    if request.GET.get('order_id', ''):
        order_filter['original_order_id'] = request.GET.get('order_id', '')
    if request.GET.get('mrp', 0):
        order_filter['customerordersummary__mrp'] = request.GET['mrp']
    if get_permission(user, 'add_shipmentinfo'):
        order_filter['picklist__status'] = 'dispatched'
    else:
        order_filter['picklist__status__in'] = ['picked', 'batch_picked']
    orders = OrderDetail.objects.exclude(**excl_filter).filter(**order_filter).\
                                annotate(ret=Sum(F('orderreturns__quantity')),
                                        dam=Sum(F('orderreturns__damaged_quantity'))).annotate(tot=F('ret')+F('dam')). \
                                filter(Q(tot__isnull=True) | Q(quantity__gt=F('tot')))
    if user.username in MILKBASKET_USERS:
        orders = orders.order_by('-creation_date')
    if orders:
        order = orders[0]
        cust_order_obj_dict ={}
        cust_order_obj = order.customerordersummary_set.filter().values('cgst_tax', 'sgst_tax',
                                                                    'igst_tax', 'utgst_tax')
        if not order.tot:
            order.tot = 0
        if cust_order_obj:
            cust_order_obj_dict = cust_order_obj[0]
        ship_quantity = order.quantity - order.tot
        data = {'status': 'confirmed', 'sku_code': sku_data.sku_code, 'description': sku_data.sku_desc,
                'order_id': order.original_order_id, 'ship_quantity': ship_quantity, 'unit_price': order.unit_price,
                'return_quantity': 1,'cgst':cust_order_obj_dict.get('cgst_tax',''),
                'sgst':cust_order_obj_dict.get('sgst_tax',''),'igst':cust_order_obj_dict.get('igst_tax','')}
        user_profile = user.userprofile
        if user_profile.industry_type == 'FMCG':
            data['batch_data'] = update_order_batch_details(user, order)
        if user_profile.user_type == 'marketplace_user' and order.sellerorder_set.filter().exists():
            data['sor_id'] = order.sellerorder_set.filter()[0].sor_id
    return data


def update_sku_attributes_data(data, key, value, is_bulk_create=False, create_sku_attrs=None, sku_attr_mapping=None):
    if not value == '':
        sku_attr_obj = SKUAttributes.objects.filter(sku_id=data.id, attribute_name=key)
        if not sku_attr_obj and value:
            if not is_bulk_create:
                SKUAttributes.objects.create(sku_id=data.id, attribute_name=key, attribute_value=value,
                                             creation_date=datetime.datetime.now())
            else:
                grp_key = '%s:%s' % (str(data.id), str(key))
                if grp_key not in sku_attr_mapping:
                    create_sku_attrs.append(SKUAttributes(**{'sku_id': data.id, 'attribute_name': key, 'attribute_value': value,
                                                 'creation_date': datetime.datetime.now()}))
                    sku_attr_mapping.append(grp_key)
        elif sku_attr_obj and sku_attr_obj[0].attribute_value != value:
            sku_attr_obj.update(attribute_value=value)
    return create_sku_attrs, sku_attr_mapping


def update_sku_attributes(data, request):
    for key, value in request.POST.iteritems():
        if 'attr_' not in key:
            continue
        key = key.replace('attr_', '')
        update_sku_attributes_data(data, key, value)


def get_invoice_sequence_obj(user, marketplace):
    invoice_sequence = InvoiceSequence.objects.filter(user=user.id, status=1, marketplace=marketplace)
    if not invoice_sequence:
        invoice_sequence = InvoiceSequence.objects.filter(user=user.id, marketplace='')
    return invoice_sequence


def user_type_sequence_obj(user, type_name, type_value):
    user_type_sequence = UserTypeSequence.objects.filter(user=user.id, status=1, type_name=type_name, type_value=type_value)
    if not user_type_sequence:
        user_type_sequence = UserTypeSequence.objects.filter(user=user.id, type_name=type_name,type_value='')
    return user_type_sequence


def create_update_batch_data(batch_dict):
    batch_obj = None
    batch_dict1 = copy.deepcopy(batch_dict)
    if {'batch_no', 'mrp', 'expiry_date'}.issubset(batch_dict1):
        if batch_dict1['expiry_date']:
            batch_dict1['expiry_date'] = datetime.datetime.strptime(batch_dict1['expiry_date'], '%m/%d/%Y')
        else:
            batch_dict1['expiry_date'] = None
        if batch_dict1['manufactured_date']:
            batch_dict1['manufactured_date'] = datetime.datetime.strptime(batch_dict1['manufactured_date'], '%m/%d/%Y')
        else:
            batch_dict1['manufactured_date'] = None
        number_fields = ['mrp', 'buy_price', 'tax_percent']
        for field in number_fields:
            try:
                batch_dict1[field] = float(batch_dict1.get(field, 0))
            except:
                batch_dict1[field] = 0
        batch_objs = BatchDetail.objects.filter(**batch_dict1)
        if not batch_objs.exists():
            batch_dict1['creation_date'] = datetime.datetime.now()
            batch_obj = BatchDetail.objects.create(**batch_dict1)
        else:
            batch_obj = batch_objs[0]
    return batch_obj


def get_or_create_batch_detail(batch_dict, temp_dict):
    batch_obj = None
    batch_dict1 = copy.deepcopy(batch_dict)
    if 'batch_no' in batch_dict:
        batch_obj = create_update_batch_data(batch_dict1)
    elif 'quality_check' in temp_dict:
        batch_obj = BatchDetail.objects.filter(transact_id=temp_dict['quality_check'].po_location.id,
                                               transact_type='po_loc')
        if batch_obj:
            batch_obj = batch_obj[0]
    return batch_obj


def get_batch_dict(transact_id, transact_type):
    batch_dict = {}
    batch_obj = BatchDetail.objects.filter(transact_id=transact_id, transact_type=transact_type)
    if batch_obj:
        batch_dict = batch_obj.values('batch_no', 'mrp', 'buy_price', 'expiry_date', 'manufactured_date','weight')[0]
        if batch_dict['expiry_date']:
            batch_dict['expiry_date'] = batch_dict['expiry_date'].strftime('%m/%d/%Y')
        if batch_dict['manufactured_date']:
            batch_dict['manufactured_date'] = batch_dict['manufactured_date'].strftime('%m/%d/%Y')
    return batch_dict


def get_style_variants(sku_master, user, customer_id='', total_quantity=0, customer_data_id='',
                       prices_dict={}, levels_config=0, dist_wh_id=0, level=0, specific_margins=[],
                       is_margin_percentage=0, default_margin=0, price_type='', is_style_detail='',
                       needed_stock_data=None):
    stocks = needed_stock_data['stock_objs']
    purchase_orders = needed_stock_data['purchase_orders']
    reserved_quantities = needed_stock_data['reserved_quantities']
    asn_quantities = needed_stock_data['asn_quantities']

    tax_master = TaxMaster.objects.filter(user_id=user.id)
    rev_inter_states = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))

    price_band_flag = get_misc_value('priceband_sync', user.id)
    if price_band_flag == 'true':
        central_admin = get_admin(user)
        tax_master = TaxMaster.objects.filter(user_id=central_admin.id)
    else:
        central_admin = user

    for ind, sku in enumerate(sku_master):
        stock_quantity = stocks.get(sku['wms_code'], 0)
        intransit_quantity = purchase_orders.get(sku['wms_code'], 0)
        if intransit_quantity < 0:
            intransit_quantity = 0
        res_value = reserved_quantities.get(sku['wms_code'], 0)
        asn_stock = asn_quantities.get(sku['wms_code'], 0)
        stock_quantity = stock_quantity - res_value + asn_stock
        total_quantity = total_quantity + stock_quantity
        sku_master[ind]['physical_stock'] = stock_quantity
        sku_master[ind]['intransit_quantity'] = intransit_quantity
        sku_master[ind]['style_quantity'] = total_quantity
        sku_master[ind]['asn_quantity'] = asn_stock
        sku_master[ind]['taxes'] = []
        customer_data = []
        sku_master[ind]['your_price'] = prices_dict.get(sku_master[ind]['id'], 0)
        if customer_id:
            customer_user = CustomerUserMapping.objects.filter(user=customer_id)[0].customer.customer_id
            customer_data = CustomerMaster.objects.filter(customer_id=customer_user, user=user.id)
        elif customer_data_id:
            customer_data = CustomerMaster.objects.filter(customer_id=customer_data_id, user=user.id)
        if customer_data:
            taxes = {}
            if customer_data[0].tax_type:
                taxes = list(tax_master.filter(product_type=sku['product_type'],
                                               inter_state=rev_inter_states.get(customer_data[0].tax_type, 2)). \
                             values('product_type', 'inter_state', 'cgst_tax', 'sgst_tax', 'igst_tax', 'min_amt',
                                    'max_amt'))
            sku_master[ind]['taxes'] = taxes
            if customer_data[0].price_type and levels_config != 'true':
                price_data = PriceMaster.objects.filter(sku__user=user.id, sku__sku_code=sku['wms_code'],
                                                        price_type=customer_data[0].price_type)
                if price_data:
                    sku_master[ind]['pricing_price'] = price_data[0].price
                    if price_data[0].price > 0:
                        sku_master[ind]['price'] = price_data[0].price
                else:
                    sku_master[ind]['pricing_price'] = 0
            else:
                buy_pm_objs = ''
                is_distributor = customer_data[0].is_distributor
                pricemaster_obj = PriceMaster.objects.filter(sku__user=central_admin.id,
                                                             sku__sku_code=sku['wms_code'])
                cm_id = customer_data[0].id
                if is_distributor:
                    dist_mapping = WarehouseCustomerMapping.objects.filter(customer_id=cm_id, status=1)
                    if dist_mapping:
                        dist_wh_id = dist_mapping[0].warehouse_id
                        if not level:
                            price_data = NetworkMaster.objects.filter(dest_location_code_id=dist_wh_id).\
                                values_list('source_location_code_id', 'price_type')
                        else:
                            if level == 3:
                                level = 1
                            price_data = NetworkMaster.objects.filter(dest_location_code_id=dist_wh_id).filter(
                                source_location_code_id__userprofile__warehouse_level=level). \
                                values_list('source_location_code_id', 'price_type')
                    sku_master[ind].setdefault('prices_map', {}).update(dict(price_data))
                    nw_pricetypes = ['D-R']
                    if is_style_detail == 'true':
                        nw_pricetypes = [j for i, j in price_data]
                    pricemaster_obj = pricemaster_obj.filter(price_type__in=nw_pricetypes)
                    if pricemaster_obj:
                        sku_master[ind]['price'] = pricemaster_obj[0].price
                        sku_master[ind]['your_price'] = pricemaster_obj[0].price
                    else:
                        sku_master[ind]['your_price'] = 0
                else:
                    if is_style_detail != 'true':
                        price_type = 'R-C'
                        buy_pricetype = customer_data[0].price_type
                        buy_pm_objs = pricemaster_obj.filter(price_type=buy_pricetype)
                    if price_type != 'R-C':
                        # Assuming Reseller, taking price type from Customer Master
                        price_type = customer_data[0].price_type
                        # Customer Level price types
                        price_type = update_level_price_type(customer_data[0], level, price_type)

                    pricemaster_obj = pricemaster_obj.filter(price_type=price_type)

                if pricemaster_obj:
                    sku_master[ind]['pricing_price'] = pricemaster_obj[0].price
                    sku_master[ind]['price'] = pricemaster_obj[0].price
                    sku_master[ind]['your_price'] = pricemaster_obj[0].price
                    apply_margin_price(sku['wms_code'], sku_master[ind], specific_margins, is_margin_percentage,
                                       default_margin, user)
                    for pm_obj in pricemaster_obj:
                        pm_obj_map = {'min_unit_range': pm_obj.min_unit_range, 'max_unit_range': pm_obj.max_unit_range,
                                      'price': pm_obj.price}
                        if buy_pm_objs:
                            buy_pm_obj = buy_pm_objs.filter(min_unit_range=pm_obj.min_unit_range,
                                                            max_unit_range=pm_obj.max_unit_range)
                            pm_obj_map['buy_price'] = buy_pm_obj[0].price
                        apply_margin_price(pm_obj.sku.sku_code, pm_obj_map, specific_margins, is_margin_percentage,
                                           default_margin, user)
                        sku_master[ind].setdefault('price_ranges', []).append(pm_obj_map)
                else:
                    price_field = get_price_field(user)
                    is_sellingprice = False
                    if price_field == 'price':
                        is_sellingprice = True
                    sku_master[ind]['price'], sku_master[ind]['mrp'] = get_customer_based_price(customer_data[0], sku_master[ind][price_field],
                                                                        sku_master[ind]['mrp'],
                                                                        is_sellingprice=is_sellingprice)
                    apply_margin_price(sku['wms_code'], sku_master[ind], specific_margins, is_margin_percentage,
                                       default_margin, user)
                    # current_sku_price = sku_master[ind]['price']
                    # sku_master[ind]['price'] = current_sku_price + float(default_margin)

                    # sku_master[ind]['charge_remarks'] = pricemaster_obj[0].charge_remarks
    return sku_master


def apply_margin_price(sku, each_sku_map, specific_margins, is_margin_percentage, default_margin, user):
    current_price = each_sku_map['price']
    each_sku_map['price'] = current_price
    if specific_margins:
        specific_margins = json.loads(specific_margins)
    specific_margin_skus = [(i['wms_code'], i['margin']) for i in specific_margins]
    spc_margin_sku_map = dict(specific_margin_skus)
    each_sku_map['margin'] = 0
    if is_margin_percentage == 'false':
        if sku in spc_margin_sku_map:
            each_sku_map['price'] = current_price + float(spc_margin_sku_map[sku])
            each_sku_map['margin'] = float(spc_margin_sku_map[sku])
        elif default_margin:
            each_sku_map['price'] = current_price + float(default_margin)
            each_sku_map['margin'] = float(default_margin)
    else:
        if sku in spc_margin_sku_map:
            raising_amt = (current_price * float(spc_margin_sku_map[sku])) / 100
            each_sku_map['price'] = current_price + raising_amt
            each_sku_map['margin'] = float(spc_margin_sku_map[sku])
        elif default_margin:
            raising_amt = (current_price * float(default_margin)) / 100
            each_sku_map['price'] = current_price + raising_amt
            each_sku_map['margin'] = float(default_margin)


def get_customer_and_price_type(request, user, customer_data_id, customer_id):
    customer_master = None
    price_type = ''
    if not customer_data_id:
        if request:
            request_user = request.user.id
        else:
            request_user = user.id
        user_type = CustomerUserMapping.objects.filter(user=request_user)
        if user_type:
            customer_master = [user_type[0].customer]
            customer_data_id = user_type[0].customer.customer_id
            customer_id = user_type[0].customer_id
            is_distributor = user_type[0].customer.is_distributor
            if is_distributor:
                price_type = user_type[0].customer.price_type
            else:  # Need to show R-C price grids in Catalogs and Download PDFs
                price_type = 'R-C'
    elif customer_id:
        customer_master = CustomerMaster.objects.filter(customer_id=customer_id, user=user.id)
        if customer_master:
            price_type = customer_master[0].price_type
    elif customer_data_id:
        customer_master = CustomerMaster.objects.filter(customer_id=customer_data_id, user=user.id)
        if customer_master:
            price_type = customer_master[0].price_type
    return customer_master, price_type, customer_data_id, customer_id


def get_gen_wh_ids(request, user, delivery_date):
    gen_whs = [user.id]
    admin = get_priceband_admin_user(user)
    res_lead_time = 0
    if admin:
        gen_whs = list(get_generic_warehouses_list(admin))
        gen_whs.append(user.id)
        cm_obj = CustomerUserMapping.objects.filter(user=request.user.id)
        if cm_obj:
            cm_id = cm_obj[0].customer
            res_lead_time = cm_obj[0].customer.lead_time
            dist_wh_obj = WarehouseCustomerMapping.objects.filter(customer_id=cm_id)
            if dist_wh_obj:
                dist_wh_id = dist_wh_obj[0].warehouse.id
                if dist_wh_id in gen_whs:
                    gen_whs.remove(dist_wh_id)
        if delivery_date:
            del_date = datetime.datetime.strptime(delivery_date, '%m/%d/%Y').date()
            today_date = datetime.datetime.today().date()
            days_filter = (del_date - today_date).days
            if res_lead_time:
                day_filter = days_filter + res_lead_time
            nw_gen_whs = NetworkMaster.objects.filter(source_location_code__in=gen_whs,
                                                   dest_location_code=user.id, lead_time__lte=days_filter).\
                values_list('source_location_code', flat=True)
            gen_whs = [user.id]
            gen_whs.extend(list(nw_gen_whs))
    return gen_whs


def get_incremental(user, type_name, default_val=''):
    # custom sku counter
    if not default_val:
        default = 1001
    else:
        default = default_val
    data = IncrementalTable.objects.filter(user=user.id, type_name=type_name)
    if data:
        data = data[0]
        count = data.value + 1
        data.value = data.value + 1
        data.save()
    else:
        IncrementalTable.objects.create(user_id=user.id, type_name=type_name, value=default)
        count = default
    return count

def get_decremental(user, type_name, old_pack_ref_no):
    # custom sku counter
    data = IncrementalTable.objects.filter(user=user.id, type_name=type_name)
    if data:
        data = data[0]
        if int(data.value) == int(old_pack_ref_no) :
            data.value = data.value - 1
        data.save()
        return 'Success'
    else:
        return 'Fail'

def check_and_update_incremetal_type_val(table_value, user, type_name):
    table_value = int(table_value)
    data = IncrementalTable.objects.filter(user=user.id, type_name=type_name)
    if data and int(data[0].value) == table_value:
        IncrementalTable.objects.filter(user=user.id, type_name=type_name).update(value=table_value-1)


def check_picklist_number_created(user, picklist_number):
    pick_check_obj = Picklist.objects.filter(Q(order__user=user.id) | Q(stock__sku__user=user.id),
                                             picklist_number=picklist_number)
    if not pick_check_obj.exists():
        check_and_update_incremetal_type_val(picklist_number, user, 'picklist')


def check_purchase_order_created(user, po_id):
    po_data = PurchaseOrder.objects.filter(Q(open_po__sku__user=user.id) |
                                           Q(stpurchaseorder__open_st__sku__user=user.id),
                                           order_id=po_id)
    if not po_data.exists():
        check_and_update_incremetal_type_val(po_id, user, 'po')


def check_order_detail_created(user, order_id):
    order_code = get_order_prefix(user.id)
    order_data = OrderDetail.objects.filter(Q(order_code__in=[order_code, 'Delivery Challan', 'sample', 'R&D', 'CO','Pre Order']) |reduce(operator.or_, (Q(order_code__icontains=x)for x in ['DC', 'PRE'])),
                                            user=user.id, order_id=order_id)
    if not order_data.exists():
        check_and_update_incremetal_type_val(order_id, user, 'order_detail')


def get_po_challan_number(user, seller_po_summary):
    challan_num = ""
    chn_date = datetime.datetime.now()
    challan_num = seller_po_summary[0].challan_number
    if not challan_num:
        challan_sequence = ChallanSequence.objects.filter(user=user.id, status=1)
        if not challan_sequence:
            challan_sequence = ChallanSequence.objects.filter(user=user.id)
        if challan_sequence:
            challan_sequence = challan_sequence[0]
            challan_num = int(challan_sequence.value)
            order_no = challan_sequence.prefix + str(challan_num).zfill(3)
            seller_po_summary.update(challan_number=order_no)
            challan_sequence.value = challan_num + 1
            challan_sequence.save()
        else:
            ChallanSequence.objects.create(prefix='CHN', value=1, status=1, user_id=user.id,
                                           creation_date=datetime.datetime.now())
            order_no = '001'
            challan_num = int(order_no)
    else:
        log.info("Challan No not updated for seller_order_summary")
    challan_number = 'CHN/%s/%s' % (chn_date.strftime('%m%y'), challan_num)

    return challan_number, challan_num


def create_seller_order_transfer(seller_order, seller_id, trans_mapping):
    """ Update Seller with ASPL Seller and creates SellerOrderTransfer table record"""
    user = User.objects.get(id=seller_order.order.user)
    try:
        if not seller_order.seller.name == 'ASPL':
            source_seller = seller_order.seller
            group_key = '%s:%s' % (str(source_seller.id), str(seller_id))
            seller_order.seller_id = seller_id
            seller_order.save()
            if group_key not in trans_mapping.keys():
                trans_mapping[group_key] = get_incremental(user, 'seller_order_transfer')
            order_transfer_id = trans_mapping[group_key]
            seller_transfer_obj = SellerTransfer.objects.filter(source_seller_id=source_seller.id,
                                                    dest_seller_id=seller_id, transact_id=order_transfer_id,
                                                    transact_type='seller_order_transfer')
            if not seller_transfer_obj:
                new_seller_transfer_obj = SellerTransfer.objects.create(source_seller_id=source_seller.id,
                                          dest_seller_id=seller_id, transact_id=order_transfer_id,
                                          transact_type='seller_order_transfer', status=1,
                                          creation_date=datetime.datetime.now())
                seller_transfer_obj = [new_seller_transfer_obj]
            SellerOrderTransfer.objects.create(seller_transfer_id=seller_transfer_obj[0].id,
                                               seller_order_id=seller_order.id,
                                               creation_date=datetime.datetime.now())
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        result_data = []
        log.info('Create Seller Order Transfer Record failed for seller order id %s and destination seller id %s and request is %s and error statement is %s' % (
            str(user.username), str(seller_order.id),str(seller_id), str(e)))
    return trans_mapping


def update_substitution_data(src_stocks, dest_stocks, src_sku, src_loc, src_qty, dest_sku, dest_loc, dest_qty, user,
                             seller_id, source_updated, mrp_dict, transact_number):
    desc_batch_obj = update_stocks_data(src_stocks, float(src_qty), dest_stocks, float(dest_qty), user, [dest_loc], dest_sku.id,
                       src_seller_id=seller_id, dest_seller_id=seller_id, source_updated=source_updated,
                       mrp_dict=mrp_dict)
    sub_data = {'source_sku_code_id': src_sku.id, 'source_location': src_loc.location, 'source_quantity': src_qty,
                'destination_sku_code_id': dest_sku.id, 'destination_location': dest_loc.location,
                'destination_quantity': dest_qty, 'transact_number': transact_number}
    if src_stocks and src_stocks[0].batch_detail:
        sub_data['source_batch_id'] = src_stocks[0].batch_detail_id
    if desc_batch_obj:
        sub_data['dest_batch_id'] = desc_batch_obj.id
    if seller_id:
        sub_data['seller_id'] = seller_id
    SubstitutionSummary.objects.create(**sub_data)
    log.info("Substitution Done For " + str(json.dumps(sub_data)))


def update_stock_detail(stocks, quantity, user, rtv_id):
    for stock in stocks.iterator():
        save_sku_stats(user, stock.sku.id, rtv_id, 'rtv', quantity, stock)
        if stock.quantity > quantity:
            stock.quantity -= quantity
            seller_stock = stock.sellerstock_set.filter()
            if seller_stock.exists():
                change_seller_stock(seller_stock[0].seller_id, stock, user, quantity, 'dec')
            quantity = 0
            if stock.quantity < 0:
                stock.quantity = 0
            stock.save()
        elif stock.quantity <= quantity:
            quantity -= stock.quantity
            seller_stock = stock.sellerstock_set.filter()
            if seller_stock.exists():
                change_seller_stock(seller_stock[0].seller_id, stock, user, stock.quantity, 'dec')
            stock.quantity = 0
            stock.save()
        if quantity == 0:
            break


def reduce_location_stock(cycle_id, wmscode, loc, quantity, reason, user, pallet='', batch_no='', mrp='',
                          seller_master_id='', weight=''):
    now_date = datetime.datetime.now()
    now = str(now_date)
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
    stock_dict = {'sku_id': sku_id, 'location_id': location[0].id,
                  'sku__user': user.id}
    if pallet:
        pallet_present = PalletDetail.objects.filter(user = user.id, status = 1, pallet_code = pallet)
        if not pallet_present:
            pallet_present = PalletDetail.objects.create(user = user.id, status = 1, pallet_code = pallet,
                quantity = quantity, creation_date=datetime.datetime.now(), updation_date=datetime.datetime.now())
        else:
            pallet_present.update(quantity = quantity)
            pallet_present = pallet_present[0]

        stock_dict['pallet_detail_id'] = pallet_present.id

    if batch_no:
        stock_dict["batch_detail__batch_no"] =  batch_no
    if mrp:
        stock_dict["batch_detail__mrp"] = mrp
    if weight:
        stock_dict["batch_detail__weight"] = weight
    if seller_master_id:
        stock_dict['sellerstock__seller_id'] = seller_master_id

    total_stock_quantity = 0
    if quantity:
        quantity = float(quantity)
        stocks = StockDetail.objects.filter(**stock_dict)
        total_stock_quantity = stocks.aggregate(Sum('quantity'))['quantity__sum']
        if not total_stock_quantity:
            return 'No Stocks Found'
        elif total_stock_quantity < quantity:
            return 'Reducing quantity is more than total quantity'
        data_dict = copy.deepcopy(CYCLE_COUNT_FIELDS)
        data_dict['cycle'] = cycle_id
        data_dict['sku_id'] = sku_id
        data_dict['location_id'] = location[0].id
        data_dict['quantity'] = total_stock_quantity
        data_dict['seen_quantity'] = total_stock_quantity - quantity
        data_dict['status'] = 0
        data_dict['creation_date'] = now
        data_dict['updation_date'] = now
        cycle_obj = CycleCount.objects.filter(cycle=cycle_id, sku_id=sku_id, location_id=data_dict['location_id'])
        if cycle_obj:
            cycle_obj = cycle_obj[0]
            cycle_obj.seen_quantity += quantity
            cycle_obj.save()
            dat = cycle_obj
        else:
            dat = CycleCount(**data_dict)
            dat.save()
        remaining_quantity = quantity
        for stock in stocks:
            if remaining_quantity == 0:
                break
            if stock.quantity:
                stock_quantity = float(stock.quantity)
                if stock_quantity >= remaining_quantity:
                    setattr(stock, 'quantity', stock_quantity - remaining_quantity)
                    save_sku_stats(user, sku_id, dat.id, 'inventory-adjustment', -remaining_quantity, stock)
                    stock.save()
                    if seller_master_id:
                        change_seller_stock(seller_master_id, stock, user, remaining_quantity, 'dec')
                    remaining_quantity = 0
                elif stock_quantity < remaining_quantity:
                    setattr(stock, 'quantity', 0)
                    save_sku_stats(user, sku_id, dat.id, 'inventory-adjustment', stock.quantity, stock)
                    stock.save()
                    if seller_master_id:
                        change_seller_stock(seller_master_id, stock, user, remaining_quantity, 'dec')
                    remaining_quantity = remaining_quantity - stock_quantity
    else:
        return 'Invalid Quantity'

    data = copy.deepcopy(INVENTORY_FIELDS)
    data['cycle_id'] = dat.id
    data['adjusted_quantity'] = quantity
    data['reason'] = reason
    data['adjusted_location'] = location[0].id
    data['creation_date'] = now
    data['updation_date'] = now
    inv_obj = InventoryAdjustment.objects.filter(cycle__cycle=dat.cycle, adjusted_location=location[0].id,
        cycle__sku__user=user.id)
    if pallet:
        data['pallet_detail_id'] = pallet_present.id
        inv_obj = inv_obj.filter(pallet_detail_id = pallet_present.id)
    if inv_obj:
        inv_obj = inv_obj[0]
        inv_obj.adjusted_quantity = quantity
        inv_obj.save()
        dat = inv_obj
    else:
        dat = InventoryAdjustment(**data)
        dat.save()

    return 'Added Successfully'


def check_stock_available_quantity(stocks, user, stock_ids=None, seller_master_id=''):
    stock_detail = stocks
    if stock_ids:
        stock_detail = StockDetail.objects.filter(id__in=stock_ids)
    else:
        stock_ids = list(stock_detail.values_list('id', flat=True))
    if seller_master_id:
        stock_qty = stock_detail.filter(sellerstock__seller_id=seller_master_id).\
            aggregate(quantity__sum=Sum('sellerstock__quantity'))['quantity__sum']
    else:
        stock_qty = stock_detail.aggregate(Sum('quantity'))['quantity__sum']
    if not stock_qty:
        return 0
    sister_warehouses = get_sister_warehouse(user)
    sister_warehouse_ids = sister_warehouses.values('user_id')
    res_qty = PicklistLocation.objects.filter(stock_id__in=stock_ids, status=1, picklist__order__user__in=sister_warehouse_ids).\
        aggregate(Sum('reserved'))['reserved__sum']
    raw_reserved = RMLocation.objects.filter(status=1, material_picklist__jo_material__material_code__user=user.id,
                                             stock_id__in=stock_ids).aggregate(Sum('reserved'))['reserved__sum']
    if not res_qty:
        res_qty = 0
    if raw_reserved:
        res_qty = float(res_qty) + float(raw_reserved)
    stock_qty = stock_qty - res_qty
    if stock_qty < 0:
        stock_qty = 0
    return stock_qty


@csrf_exempt
@login_required
def save_webpush_id(request):
    null = 'null'
    true = True
    false = False
    wpn_obj = eval(request.body)
    wpn_id = wpn_obj.get('wpn_id', '')
    if not wpn_id:
        return HttpResponse({"message": "failure"})
    user_id = request.user.id
    os_qs = OneSignalDeviceIds.objects.filter(user_id=user_id)
    if os_qs:
        os_obj = os_qs[0]
        os_obj.device_id = wpn_id
        os_obj.save()
    else:
        OneSignalDeviceIds.objects.create(user_id=user_id, device_id=wpn_id)
    return HttpResponse({"message": "success"})


def send_push_notification(contents, users_list):
    player_ids = []
    wh_player_qs = OneSignalDeviceIds.objects.filter(user__in=users_list).distinct()
    for wh_player in wh_player_qs:
        wh_player_id = wh_player.device_id
        player_ids.append(wh_player_id)

    auth_key = settings.ONESIGNAL_AUTH_KEY
    app_id = settings.ONESIGNAL_APP_ID
    os_notification_url = "https://onesignal.com/api/v1/notifications"
    header = {"Content-Type": "application/json; charset=utf-8",
              "Authorization": "Basic %s" %auth_key}

    payload = {"app_id": app_id,
               "include_player_ids": player_ids,
               "contents": contents}
    req = requests.post(os_notification_url, headers=header, data=json.dumps(payload))
    log.info("Notification Status %s for contents: %s and player_ids: %s " %(req.status_code, contents, player_ids))
    for user in users_list:
        PushNotifications.objects.create(user_id=user, message=contents['en'])
    return req.status_code, req.reason


def update_ean_sku_mapping(user, ean_numbers, data, remove_existing=False):
    ean_status = ''
    exist_ean_list = list(data.eannumbers_set.filter().annotate(str_eans=Cast('ean_number', CharField())).\
                          values_list('str_eans', flat=True))
    if data.ean_number:
        exist_ean_list.append(str(data.ean_number))
    error_eans = []
    rem_ean_list = []
    if remove_existing:
        rem_ean_list = list(set(exist_ean_list) - set(ean_numbers))
    for ean_number in ean_numbers:
        if ean_number :
            ean_dict = {'ean_number': ean_number, 'sku_id': data.id}
            ean_status, mapped_check = check_ean_number(data.sku_code, ean_number, user)
            if not (ean_status or mapped_check):
                EANNumbers.objects.create(**ean_dict)
            elif ean_status:
                error_eans.append(str(ean_number))
    for rem_ean in rem_ean_list:
        if str(data.ean_number) == str(rem_ean):
            data.ean_number = ''
            data.save()
        else:
            EANNumbers.objects.filter(sku_id=data.id, ean_number=rem_ean).delete()
    if error_eans:
        ean_status = '%s EAN Numbers already mapped to Other SKUS' % ','.join(error_eans)
    return ean_status


def po_invoice_number_check(user, invoice_num, supplier_id):
    status = ''
    exist_inv_obj = SellerPOSummary.objects.filter(purchase_order__open_po__sku__user=user.id,
                                                   invoice_number=invoice_num,
                                                   purchase_order__open_po__supplier_id=supplier_id)
    if exist_inv_obj.exists():
        status = 'Invoice Number already Mapped to %s/%s' % (get_po_reference(exist_inv_obj[0].purchase_order),
                                                             str(exist_inv_obj[0].receipt_number))
    return status


def get_sister_warehouse(user):
    warehouses = UserGroups.objects.filter(Q(admin_user=user) | Q(user=user))
    return warehouses


def get_linked_user_objs(current_user, user):
    warehouses = get_sister_warehouse(user)
    if current_user == 'true':
        wh_names = list(warehouses.values_list('user__username', flat=True))
    else:
        wh_names = list(warehouses.exclude(user_id=user.id).values_list('user__username', flat=True))
    return wh_names


@login_required
@csrf_exempt
@get_admin_user
def get_linked_warehouse_names(request, user=''):
    current_user = request.GET.get('current_user', '')
    wh_names = get_linked_user_objs(current_user, user)
    return HttpResponse(json.dumps({'wh_names': wh_names}))


def get_sku_ean_list(sku, order_by_val=''):
    eans_list = []
    if sku.ean_number not in ['', '0']:
        eans_list.append(str(sku.ean_number))
    multi_eans = sku.eannumbers_set.filter().annotate(str_eans=Cast('ean_number', CharField())).\
                    values_list('str_eans', flat=True)
    if order_by_val and multi_eans:
        order_by_field = 'creation_date'
        if order_by_val == 'desc':
            order_by_field = '-creation_date'
        multi_eans = multi_eans.order_by(order_by_field)
    if multi_eans:
        eans_list = list(chain(eans_list, multi_eans))
    return eans_list


def get_exclude_zones(user, is_putaway=False):
    exclude_zones = ['DAMAGED_ZONE', 'QC_ZONE']
    if user.userprofile.industry_type == 'FMCG' and not is_putaway:
        non_sellable_zones = list(ZoneMaster.objects.filter(user=user.id, segregation='non_sellable').values_list('zone',
                                                                                                             flat=True))
        exclude_zones.extend(non_sellable_zones)
    sub_zones = SubZoneMapping.objects.filter(zone__zone__in=exclude_zones, zone__user=user.id).\
        values_list('sub_zone__zone', flat=True)
    if sub_zones:
        exclude_zones = list(chain(exclude_zones, sub_zones))
    return exclude_zones


def get_all_zones(user, zones=None):
    """ Send Zones under the mentioned Zones"""
    zone_filter = {'user': user.id}
    all_zones = []
    if not zones:
        zones = []
    if zones:
        zone_filter['zone__in'] = zones
    zone_master = ZoneMaster.objects.filter(**zone_filter)
    all_zones = list(zone_master.values_list('zone', flat=True))
    sub_zones = SubZoneMapping.objects.filter(zone__user=user.id, zone__zone__in=all_zones).\
                                        values_list('sub_zone__zone', flat=True)
    if sub_zones.exists():
        all_zones = list(set(chain(all_zones, list(sub_zones))))
    return all_zones


def update_existing_suggestions(user):
    ''' Updating Existing Suggestions'''
    suggestions = SellableSuggestions.objects.filter(stock__sku__user=user.id, status=1)
    for suggestion in suggestions:
        if float(suggestion.stock.quantity) == float(suggestion.quantity):
            continue
        suggestion.quantity = suggestion.stock.quantity
        if suggestion.quantity <= 0:
            suggestion.status = 0
        suggestion.save()


def update_auto_sellable_data(user):
    ''' Create Sellable Suggestions '''
    from rest_api.views.inbound import get_purchaseorder_locations, get_remaining_capacity, get_stock_locations
    creation_date = datetime.datetime.now()
    industry_type = user.userprofile.industry_type
    user_type = user.userprofile.user_type
    log_sellable.info('Updating the Sellable Auto suggestions for user %s at %s' %
             (user.username, get_local_date(user,creation_date)))
    try:
        picklist_exclude_zones = get_exclude_zones(user)
        non_sellable_zones = get_all_zones(user, zones=['Non Sellable Zone'])
        non_sellable_stock = StockDetail.objects.filter(sku__user=user.id, location__zone__zone__in=non_sellable_zones,
                                                        quantity__gt=0)
        non_sellable_skus = non_sellable_stock.values_list('sku_id', flat=True)
        zero_quantity = StockDetail.objects.filter(sku__user=user.id, quantity=0, sku_id__in=non_sellable_skus).\
                                            exclude(location__zone__zone__in=picklist_exclude_zones)

        zero_quantity_skus = list(zero_quantity.values_list('sku_id', flat=True))
        remaining_skus = list(SKUMaster.objects.filter(user=user.id).values_list('id', flat=True))
        sugg_skus = set(non_sellable_skus).intersection(zero_quantity_skus + remaining_skus)

        # Updating already created suggestion Entries
        update_existing_suggestions(user)
        for sugg_sku in sugg_skus:
            sugg_stock = non_sellable_stock.filter(sku_id=sugg_sku)
            exist_obj = SellableSuggestions.objects.filter(stock_id__in=sugg_stock.values_list('id', flat=True),
                                                           status=1)
            if exist_obj.exists():
                continue
            if industry_type == 'FMCG':
                last_used = zero_quantity.filter(batch_detail__isnull=False, sku_id=sugg_sku).order_by('updation_date')
                if last_used.exists():
                    last_mrp = last_used[0].batch_detail.mrp
                    mrp_stock = sugg_stock.filter(batch_detail__mrp=last_mrp)
                    if mrp_stock:
                        sugg_stock = mrp_stock
                    else:
                        other_mrp_obj = sugg_stock.filter(batch_detail__isnull=False)
                        if other_mrp_obj.exists():
                            sugg_stock = sugg_stock.filter(batch_detail__mrp=other_mrp_obj[0].batch_detail.mrp)
            if sugg_stock:
                suggsting_zone_list = get_all_zones(user, zones=[sugg_stock[0].location.zone.zone])
                sugg_stock = sugg_stock.filter(location__zone__zone__in=suggsting_zone_list)
            for stock in sugg_stock:
                sellable_dict = {'stock_id': stock.id, 'status': 1}
                quantity = stock.quantity
                if user_type == 'marketplace_user':
                    seller_stock = stock.sellerstock_set.filter(quantity__gt=0)
                    if not seller_stock.exists():
                        continue
                    sellable_dict['seller_id'] = seller_stock[0].seller_id
                    quantity = seller_stock[0].quantity
                sellable_suggestions = SellableSuggestions.objects.filter(**sellable_dict)
                if not sellable_suggestions:
                    sellable_dict['quantity'] = quantity
                    put_zone = 'DEFAULT'
                    if stock.sku.zone:
                        put_zone = stock.sku.zone.zone
                    temp_dict = {'sku_group': stock.sku.sku_group, 'wms_code': stock.sku.wms_code,
                          'sku': stock.sku, 'seller_id': sellable_dict.get('seller_id', ''),
                                 'data': '', 'user': user.id}
                    sellable_dict['creation_date'] = creation_date
                    locations = get_purchaseorder_locations(put_zone, temp_dict)
                    received_quantity = sellable_dict['quantity']
                    for location in locations:
                        location_quantity, received_quantity = get_remaining_capacity(location, received_quantity,
                                                                                      put_zone,
                                                                                      '', user.id)
                        if not location_quantity:
                            continue
                        sellable_dict1 = copy.deepcopy(sellable_dict)
                        sellable_dict1['quantity'] = location_quantity
                        sellable_dict1['location_id'] = location.id
                        SellableSuggestions.objects.create(**sellable_dict1)
    except Exception as e:
        import traceback
        log_sellable.debug(traceback.format_exc())
        result_data = []
        log_sellable.info('Create Sellable Auto Suggestions failed for user %s' % (str(user.username)))


def validate_order_imei_mapping_status(imei, order_imei_mapping, order, job_order):
    ''' Validate IMEI Order status'''
    if order and order_imei_mapping[0].order:
        if order_imei_mapping[0].order_id == order.id:
            status = str(imei) + ' is already mapped with this order'
        else:
            status = str(imei) + ' is already mapped with another order'
    elif job_order and order_imei_mapping[0].jo_material:
        if int(order_imei_mapping[0].jo_material.job_order.job_code) == int(job_order.job_code):
            status = str(imei) + ' is already mapped with this order'
        else:
            status = str(imei) + ' is already mapped with another order'
    else:
        status = str(imei) + 'is already Mapped'


@csrf_exempt
@get_admin_user
@login_required
def check_custom_generated_label(request, user=''):
    status = ''
    imei = request.GET.get('imei', '')
    sku_code = request.GET.get('sku_code', '')
    po_mapping, status, imei_data = check_get_imei_details(imei, sku_code, user.id, check_type='purchase_check')
    if not status:
        po_labels = POLabels.objects.filter(sku__user=user.id, label=imei)
        if po_labels:
            status = 'Label already used'
    if not status:
        status = 'Success'
    return HttpResponse(json.dumps({'message': status}))


def create_update_table_history(user, model_id, model_name, model_field, prev_val, new_val):
    table_history = TableUpdateHistory.objects.filter(user_id=user.id, model_id=model_id,
                                                     model_name=model_name, model_field=model_field)
    if not table_history.exists():
        TableUpdateHistory.objects.create(user_id=user.id, model_id=model_id,
                                         model_name=model_name, model_field=model_field,
                                         previous_val=prev_val, updated_val=new_val)


def get_customer_parent_user(user):
    parent_user = None
    cus_user_mapping = CustomerUserMapping.objects.filter(user_id=user.id)
    if cus_user_mapping.exists():
        parent_user_id = cus_user_mapping[0].customer.user
        parent_user = User.objects.get(id=parent_user_id)
    return parent_user


def prepare_notification_message(enq_data, message):
    def_const = (str(enq_data.enquiry_id), str(enq_data.quantity),
                 str(enq_data.sku.sku_code), enq_data.customer_name)
    def_message = "for custom order %s of %s Pcs %s for %s" % def_const
    final_message = "%s %s" % (message, def_message)
    return final_message


def get_po_company_logo(user, IMAGE_PATH_DICT, request):
    import base64
    logo_path = ""
    try:
        logo_name = IMAGE_PATH_DICT.get(user.username, '')
        if logo_name:
            logo_path = 'http://' + request.get_host() + '/static/company_logos/' + logo_name
    except:
        pass
    return logo_path

def get_all_warehouses(user):
    user_list = []
    admin_user = UserGroups.objects.filter(
        Q(admin_user__username__iexact=user.username) | Q(user__username__iexact=user.username)). \
        values_list('admin_user_id', flat=True)
    user_groups = UserGroups.objects.filter(admin_user_id__in=admin_user).values('user__username',
                                                                                 'admin_user__username')
    for users in user_groups:
        for key, value in users.iteritems():
            if user.username != value and value not in user_list:
                user_list.append(value)
    return user_list


def check_and_create_supplier_wh_mapping(user, warehouse, supplier_id):
    master_mapping = MastersMapping.objects.filter(user=user.id, master_id=supplier_id,
                                               mapping_type='central_supplier_mapping')
    supplier_master = SupplierMaster.objects.get(id=supplier_id, user=user.id)
    if master_mapping:
        new_supplier_id = master_mapping[0].mapping_id
    else:
        new_supplier_id = create_new_supplier(warehouse, supplier_master.name, supplier_master.email_id,
                                          supplier_master.phone_number,
                                        supplier_master.address, supplier_master.tin_number)
        if new_supplier_id:
            MastersMapping.objects.create(user=user.id, master_id=supplier_id, mapping_id=new_supplier_id,
                                         mapping_type='central_supplier_mapping')
    return new_supplier_id


def check_and_create_wh_supplier(retailUserObj, levelOneWarehouseObj):
    new_supplier_id = None
    userProfileObj = UserProfile.objects.filter(user=levelOneWarehouseObj)
    if userProfileObj:
        userProfileObj = userProfileObj[0]
        master_mapping = MastersMapping.objects.filter(user=retailUserObj.id, master_id=userProfileObj.id,
                                               mapping_type='warehouse_supplier_mapping')
        if master_mapping:
            new_supplier_id = master_mapping[0].mapping_id
    else:
        supplier_master = SupplierMaster.objects.get(id=levelOneWarehouseObj, user=retailUserObj.id)
        if supplier_master:
            # master_mapping = MastersMapping.objects.filter(user=retailUserObj.id, mapping_id=supplier_master.id,
            #                                    mapping_type='warehouse_supplier_mapping')
            new_supplier_id = supplier_master.id
    
    if not new_supplier_id:
        phone_number = userProfileObj.phone_number or 0
        new_supplier_id = create_new_supplier(retailUserObj, userProfileObj.user.first_name, userProfileObj.user.email,
                                          userProfileObj.phone_number,
                                        userProfileObj.address, userProfileObj.gst_number)
        if new_supplier_id:
            MastersMapping.objects.create(user=retailUserObj.id, master_id=userProfileObj.id, mapping_id=new_supplier_id,
                                         mapping_type='warehouse_supplier_mapping')
    return new_supplier_id


def createSalesOrderAtLevelOneWarehouse(user, po_suggestions, order_id):
    try:
        mappingObj = MastersMapping.objects.filter(user=user.id, mapping_id=po_suggestions['supplier_id'])
        levelOneWhId = int(mappingObj[0].master_id)
        actUserId = UserProfile.objects.get(id=levelOneWhId).user.id
        retailAddress = UserProfile.objects.get(user_id=user.id).address
        # order_id = get_order_id(levelOneWhId)
        order_code = get_order_prefix(actUserId)
        org_ord_id = order_code + str(order_id)
        quantity = po_suggestions['order_quantity']
        customer_id = 0 #TODO Currently not creating LevelTwoWarehouses as Customers. So Taking 0 as customer Id
        customer_name = user.username
        shipment_date = po_suggestions['delivery_date']
        sgst_tax = po_suggestions['sgst_tax']
        cgst_tax = po_suggestions['cgst_tax']
        igst_tax = po_suggestions['igst_tax']
        tax_type = 'NA' #TODO
        address = po_suggestions.get('ship_to', '') or retailAddress
        unit_price = po_suggestions['price']
        taxes = {}
        taxes['cgst_tax'] = float(po_suggestions['cgst_tax'])
        taxes['sgst_tax'] = float(po_suggestions['sgst_tax'])
        taxes['igst_tax'] = float(po_suggestions['igst_tax'])
        taxes['utgst_tax'] = float(po_suggestions['utgst_tax'])
        invoice_amount = quantity * unit_price
        invoice_amount = invoice_amount + ((invoice_amount / 100) * sum(taxes.values()))
        sku_id = po_suggestions['sku_id']
        from rest_api.views.outbound import get_syncedusers_mapped_sku
        actSku = get_syncedusers_mapped_sku(actUserId, sku_id)
        title = SKUMaster.objects.get(id=actSku).sku_desc
        order_detail_dict = {'sku_id': actSku, 'title': title, 'quantity': quantity, 'order_id': order_id,
                             'original_order_id': org_ord_id, 'user': actUserId, 'customer_id': customer_id,
                             'customer_name': customer_name, 'shipment_date': shipment_date,
                             'address': address, 'unit_price': unit_price, 'invoice_amount': invoice_amount,
                             'creation_date': None, 'status':1, 'order_code': order_code, 'marketplace': 'Offline'}
        ord_obj = OrderDetail.objects.filter(order_id=order_id, sku_id=sku_id, order_code=order_code)
        if ord_obj:
            ord_obj = ord_obj[0]
            ord_obj.quantity = quantity
            ord_obj.unit_price = unit_price
            ord_obj.invoice_amount = invoice_amount
            ord_obj.save()
        else:
            ord_obj = OrderDetail(**order_detail_dict)
            ord_obj.save()

        CustomerOrderSummary.objects.create(order=ord_obj, sgst_tax=sgst_tax,cgst_tax=cgst_tax,
                                            igst_tax=igst_tax, tax_type=tax_type)
    except Exception as e:
        import traceback; print(traceback.format_exc())


@get_admin_user
def search_style_data(request, user=''):
    sku_master, sku_master_ids = get_sku_master(user, request.user)
    search_key = request.GET.get('q', '')
    total_data = []
    limit = 10

    if not search_key:
        return HttpResponse(json.dumps(total_data))

    lis = ['sku_class', 'style_name']
    query_objects = sku_master.filter(Q(sku_class__icontains=search_key) | Q(style_name__icontains=search_key),
                                      user=user.id).values(*lis).distinct()

    master_data = query_objects.filter(Q(sku_class__exact=search_key) | Q(style_name__exact=search_key),
                                       user=user.id).values(*lis).distinct()
    if master_data:
        master_data = master_data[0]
        total_data.append(master_data)

    master_data = query_objects.filter(Q(sku_class__istartswith=search_key) | Q(style_name__istartswith=search_key),
                                       user=user.id).values(*lis).distinct()
    total_data = build_style_search_data(total_data, master_data, limit)

    if len(total_data) < limit:
        total_data = build_style_search_data(total_data, query_objects, limit)
    return HttpResponse(json.dumps(total_data))


@csrf_exempt
@login_required
@get_admin_user
def get_style_level_stock(request, user=''):
    sku_wise_list = []
    sku_class = request.GET.get('sku_class', '')
    sel_warehouse = request.GET.get('warehouse', '')
    if sel_warehouse:
        user = User.objects.get(username=sel_warehouse)
    if not sku_class:
        return HttpResponse(json.dumps({}))
    sku_codes = SKUMaster.objects.filter(sku_class=sku_class, user=user.id)
    for sku in sku_codes[0:3]:
        stock_data = StockDetail.objects.exclude(Q(receipt_number=0) |
                                                 Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'])).\
                                            filter(sku__user=user.id, sku__sku_code=sku.sku_code)
        zones_data, available_quantity = get_sku_stock_summary(stock_data, '', user)
        avail_qty = sum(map(lambda d: available_quantity[d] if available_quantity[d] > 0 else 0, available_quantity))
        sku_wise_list.append({'sku_code': sku.sku_code, 'sku_desc': sku.sku_desc, 'avail_qty': avail_qty})
    return HttpResponse(json.dumps(sku_wise_list))


def add_ean_weight_to_batch_detail(sku, batch_dict):
    ean_number = get_sku_ean_list(sku, order_by_val='desc')
    if ean_number and ean_number != '0':
        batch_dict['ean_number'] = ean_number[0]
    weight_obj = sku.skuattributes_set.filter(attribute_name='weight')
    if weight_obj and not 'weight' in batch_dict.keys():
        batch_dict['weight'] = weight_obj[0].attribute_value


def check_and_create_duplicate_batch(batch_detail_obj, model_obj):
    extra_batch = batch_detail_obj.sellerposummary_set.filter(id=model_obj.id)
    if extra_batch.exists():
        batch_detail_obj.pk = None
        batch_detail_obj.id = None
        batch_detail_obj.save()
        model_obj.batch_detail_id = batch_detail_obj.id
        model_obj.save()
    return model_obj


@csrf_exempt
@login_required
@get_admin_user
def delete_temp_json(request, user=''):
    model_name = request.POST.get('model_name', '')
    json_id = request.POST.get('json_id', '')
    if json_id and model_name:
        temp_json_obj = TempJson.objects.filter(id=json_id, model_name=model_name)
        if temp_json_obj.exists():
            temp_json_obj.delete()
    return HttpResponse(json.dumps({'message': 'deleted'}))


def get_sub_users(user):
    sub_users = AdminGroups.objects.get(user_id=user.id).group.user_set.filter()
    return sub_users

def insert_st_gst(all_data, user):
    for key, value in all_data.iteritems():
        for val in value:
            if val[6]:
                open_st = OpenST.objects.get(id=val[6])
                open_st.warehouse_id = User.objects.get(username__iexact=key[0]).id
                open_st.sku_id = SKUMaster.objects.get(wms_code=val[0], user=user.id).id
                open_st.price = float(val[2])
                open_st.order_quantity = float(val[1])
                open_st.cgst_tax = float(val[3])
                open_st.sgst_tax = float(val[4])
                open_st.igst_tax = float(val[5])
                open_st.save()
                continue
            stock_dict = copy.deepcopy(OPEN_ST_FIELDS)
            stock_dict['warehouse_id'] = User.objects.get(username__iexact=key[0]).id
            stock_dict['sku_id'] = SKUMaster.objects.get(wms_code=val[0], user=user.id).id
            stock_dict['order_quantity'] = float(val[1])
            stock_dict['price'] = float(val[2])
            stock_dict['cgst_tax'] = float(val[3])
            stock_dict['sgst_tax'] = float(val[4])
            stock_dict['igst_tax'] = float(val[5])
            stock_transfer = OpenST(**stock_dict)
            stock_transfer.save()
            all_data[key][all_data[key].index(val)][6] = stock_transfer.id
    return all_data


def confirm_stock_transfer_gst(all_data, warehouse_name):
    warehouse = User.objects.get(username__iexact=warehouse_name)
    for key, value in all_data.iteritems():
        user = User.objects.get(id=key[1])
        po_id = get_purchase_order_id(user) + 1
        stock_transfer_obj = StockTransfer.objects.filter(sku__user=warehouse.id).order_by('-order_id')
        if stock_transfer_obj:
            order_id = int(stock_transfer_obj[0].order_id) + 1
        else:
            order_id = 1001
        for val in value:
            open_st = OpenST.objects.get(id=val[6])
            sku_id = SKUMaster.objects.get(wms_code__iexact=val[0], user=warehouse.id).id
            user_profile = UserProfile.objects.filter(user_id=user.id)
            prefix = ''
            if user_profile:
                prefix = user_profile[0].prefix
            po_dict = {'order_id': po_id, 'received_quantity': 0, 'saved_quantity': 0,
                       'po_date': datetime.datetime.now(), 'ship_to': '',
                       'status': 'stock-transfer', 'prefix': prefix, 'creation_date': datetime.datetime.now()}
            po_order = PurchaseOrder(**po_dict)
            po_order.save()
            st_purchase_dict = {'po_id': po_order.id, 'open_st_id': open_st.id,
                                'creation_date': datetime.datetime.now()}
            st_purchase = STPurchaseOrder(**st_purchase_dict)
            st_purchase.save()
            st_dict = copy.deepcopy(STOCK_TRANSFER_FIELDS)
            st_dict['order_id'] = order_id
            st_dict['invoice_amount'] = (float(val[1]) * float(val[2])) + float(val[3]) + float(val[4]) + float(val[5])
            st_dict['quantity'] = float(val[1])
            st_dict['st_po_id'] = st_purchase.id
            st_dict['sku_id'] = sku_id
            stock_transfer = StockTransfer(**st_dict)
            stock_transfer.save()
            open_st.status = 0
            open_st.save()
        check_purchase_order_created(user, po_id)
    return HttpResponse("Confirmed Successfully")

def update_order_dicts_rista(orders, rista_resp, user='', company_name=''):
    from outbound import check_stocks
    trans_mapping = {}
    collect_order_detail_list = []
    order_sku = {}
    status = {'status': 0, 'messages': ['Something went wrong']}
    for order_key, order in orders.iteritems():
        customer_name = order['order_details']['customer_name']
        if order_key == "extra":
            if float(order.get('shipping_charges', 0)):
                OrderCharges.objects.create(**{'order_id': order.get('original_order_id', ''), 'user':user, 'charge_name':'Shipping Charges', 'charge_amount': float(order.get('shipping_charges', 0)) })
            if float(order.get('discount', 0)):
                OrderCharges.objects.create(**{'order_id': order.get('original_order_id', ''), 'user':user, 'charge_name':'Discount', 'charge_amount': float(order.get('discount',0)) })
            continue
        if not order.get('order_details', {}):
            continue
        order_det_dict = order['order_details']
        original_order_id = order_det_dict.get('original_order_id', '')
        if not order.get('order_detail_obj', None):
            order_obj = OrderDetail.objects.filter(original_order_id=order_det_dict['original_order_id'],
                                                   order_id=order_det_dict['order_id'],
                                                   order_code=order_det_dict['order_code'],
                                                   sku_id=order_det_dict['sku_id'],
                                                   user=order_det_dict['user'])
        else:
            order_obj = [order.get('order_detail_obj', None)]
        if order_obj:
            order_obj = order_obj[0]
            order_obj.quantity = float(order_obj.quantity) + float(order_det_dict.get('quantity', 0))
            order_obj.invoice_amount = float(order_obj.invoice_amount) + float(order_det_dict.get('invoice_amount', 0))
            order_obj.sku_code = str(order_det_dict.get('line_item_id', ''))
            order_obj.save()
            order_detail = order_obj
            collect_order_detail_list.append(order_detail)
        else:
            del(order['order_details']['customer_code'])
            order['order_details']['customer_name'] = customer_name
            order_detail = OrderDetail.objects.create(**order['order_details'])
            collect_order_detail_list.append(order_detail)
        if order.get('order_summary_dict', {}) and not order_obj:
            order['order_summary_dict']['order_id'] = order_detail.id
            customer_order_summary = CustomerOrderSummary.objects.create(**order['order_summary_dict'])
        if order.get('seller_order_dict', {}):
            trans_mapping = check_create_seller_order(order['seller_order_dict'], order_detail, user,
                                                      order.get('swx_mappings', []), trans_mapping=trans_mapping)
        sku_obj = SKUMaster.objects.filter(id=order_det_dict['sku_id'])
        if 'measurement_type' in order_det_dict.keys():
            sku_obj.update(measurement_type=order_det_dict['measurement_type'])
        if sku_obj:
            sku_obj = sku_obj[0]
        else:
            continue
        order_sku.update({sku_obj: order_det_dict['quantity']})
        for order_fields in order.get('order_fields_list', ''):
            OrderFields.objects.create(**order_fields)
    for resp_obj in rista_resp:
        rista_orders_obj = TempJson.objects.filter(**{'model_id': user.id, 'model_name': 'rista<<>>indent_out<<>>' + resp_obj['indentNumber']})
        if not rista_orders_obj:
            TempJson.objects.create(**{'model_id': user.id, 'model_name': 'rista<<>>indent_out<<>>' + resp_obj['indentNumber'], 'model_json': str(resp_obj)})
    status = {'status': 1, 'messages': ['Success']}
    return status


def mysql_query_to_file(load_file, table_name, columns, values1, date_string='', update_string=''):
    values = copy.deepcopy(values1)
    columns_string = ','.join(columns)
    query = 'insert into %s %s' % (table_name, '('+columns_string+')')
    string_vals = str(tuple(map(str, values)))
    if date_string:
        string_vals = string_vals[:-1] + ',' + date_string + ')'
    query += ' %s' % ('values' + string_vals)
    if update_string:
        query += ' on duplicate key update %s' % update_string
    #file_str = query + ';'
    file_str = "#<>#".join(values)
    load_file.write('%s\n' % file_str)
    load_file.flush()


def load_by_file(load_file_name, table_name, columns, id_dependency=False):
    db_name = settings.DATABASES['default']['NAME']
    mysql_user = settings.DATABASES['default']['USER']
    mysql_password = settings.DATABASES['default']['PASSWORD']
    mysql_host = settings.DATABASES['default']['HOST']
    base_cmd = 'mysql -u %s -p%s '
    cmd_tuple = [mysql_user, mysql_password]
    if mysql_host:
        base_cmd = 'mysql -u %s -h %s -p%s '
        cmd_tuple = [mysql_user, mysql_host, mysql_password]
    if id_dependency:
        cmd = base_cmd + db_name + ' < %s'
        cmd_tuple.append(load_file_name)
    else:
        cmd = base_cmd + db_name + ' --local-infile=1 -e "%s"'
        columns_string = '(' + ','.join(columns) +')'
        query = "LOAD DATA LOCAL INFILE '%s' REPLACE INTO TABLE %s CHARACTER SET utf8 FIELDS TERMINATED BY '#<>#' lines terminated by '\n' %s" %\
                (load_file_name, table_name, columns_string)
        if table_name in ['SKU_ATTRIBUTES', 'CUSTOMER_ORDER_SUMMARY', 'SELLER_ORDER', 'ORDER_CHARGES']:
            query += " SET creation_date=NOW(), updation_date=NOW();"
        else:
            query += ";"
        cmd_tuple.append(query)
    try:
        log.info("Loading Started for: %s" % load_file_name)
        log.info(cmd % tuple(cmd_tuple))
        cmd = cmd % tuple(cmd_tuple)
        subprocess.check_output(cmd+'&', stderr=subprocess.STDOUT,shell=True)
        log.info('loading completed')
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())

def insert_st(all_data, user):
    for key, value in all_data.iteritems():
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

def confirm_stock_transfer(all_data, user, warehouse_name, request=''):
    sub_user = user
    if request:
        sub_user = request.user
    warehouse = User.objects.get(username__iexact=warehouse_name)
    po_sub_user_prefix = get_misc_value('po_sub_user_prefix', user.id)
    for key, value in all_data.iteritems():
        po_id = get_purchase_order_id(user) + 1
        if po_sub_user_prefix == 'true':
            po_id = update_po_order_prefix(sub_user, po_id)
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

            po_dict = {'order_id': po_id, 'received_quantity': 0, 'saved_quantity': 0,
                       'po_date': datetime.datetime.now(), 'ship_to': '',
                       'status': '', 'prefix': prefix, 'creation_date': datetime.datetime.now()}
            po_order = PurchaseOrder(**po_dict)
            po_order.save()
            st_purchase_dict = {'po_id': po_order.id, 'open_st_id': open_st.id,
                                'creation_date': datetime.datetime.now()}
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
        check_purchase_order_created(user, po_id)
    return HttpResponse("Confirmed Successfully")


def update_po_order_prefix(sub_user, po_id):
    ''' Returns Purchase Order Id with User Prefix'''
    po_id = '%s%s' % (str(sub_user.id), str(po_id))
    return int(po_id)


def storehippo_sync_price_value(user, update_dict):
    from rest_api.views.easyops_api import *
    storehippo_response = {}
    alert_message_for_email = LOAD_CONFIG.get('storehippo', 'alert_message_for_email', '')
    send_alert_msg_to = eval(LOAD_CONFIG.get('storehippo', 'send_alert_msg_to', ''))
    body_of_alert_email = LOAD_CONFIG.get('storehippo', 'body_of_alert_email', '')
    check_store_hippo = Integrations.objects.filter(**{'user':user.id, 'name':'storehippo', 'status':1})
    if len(check_store_hippo):
    	for integrate in check_store_hippo:
    	    obj = eval(integrate.api_instance)(company_name=integrate.name, user=user.id)
    	    storehippo_response = obj.storehippo_sku_update({'wms_code':update_dict.get('wms_code', ''), 'price': update_dict.get('price', '')}, user)
    	    if storehippo_response['status']:
                storehippo_fulfillments_log.info('For User: ' + str(user.username) + ', Storehippo Product Update - ' + str(storehippo_response))
    	    else:
                storehippo_fulfillments_log.info('For User : ' + str(user.username) + ' , Response - ' + str(storehippo_response))
                send_mail(send_alert_msg_to, body_of_alert_email, 'For User : ' + str(user.username) + ' , ' + str(alert_message_for_email) + ', Response - ' + str(storehippo_response))
    return storehippo_response


def get_all_sellable_zones(user):
    ''' Returns all Sellable Zones list '''
    sellable_zones = ZoneMaster.objects.filter(user=user.id, segregation='sellable').exclude(zone__in=['DAMAGED_ZONE', 'QC_ZONE']).values_list('zone', flat=True)
    if sellable_zones:
        sellable_zones = get_all_zones(user, zones=sellable_zones)
    return sellable_zones


def cancel_emiza_order(gen_ord_id, cm_id):
    log.info("Cancelling Emiza Order. Gen Ord: %s and Customer Id: %s" %(gen_ord_id, cm_id))
    customer_qs = CustomerUserMapping.objects.filter(customer_id=cm_id)
    if customer_qs:
        customer_user = customer_qs[0]
    gen_qs = GenericOrderDetailMapping.objects.filter(generic_order_id=gen_ord_id, customer_id=cm_id)
    generic_orders = gen_qs.values('orderdetail__original_order_id', 'orderdetail__user').distinct()
    for generic_order in generic_orders:
        original_order_id = generic_order['orderdetail__original_order_id']
        order_detail_user = User.objects.get(id=generic_order['orderdetail__user'])
        resp = order_push(original_order_id, order_detail_user, "CANCEL")
        log.info('Cancel Order Push Status: %s' % (str(resp)))
    uploaded_po_details = gen_qs.values('po_number', 'client_name').distinct()
    if uploaded_po_details.count() == 1:
        po_number = uploaded_po_details[0]['po_number']
        client_name = uploaded_po_details[0]['client_name']
        ord_upload_qs = OrderUploads.objects.filter(uploaded_user=customer_user.id,
                                                    po_number=po_number, customer_name=client_name)
        ord_upload_qs.delete()
    order_det_ids = gen_qs.values_list('orderdetail_id', flat=True)
    ord_det_qs = OrderDetail.objects.filter(id__in=order_det_ids)
    for order_det in ord_det_qs:
        if order_det.status == 1:
            order_det.status = 3
            order_det.save()
        else:
            picklists = Picklist.objects.filter(order_id=order_det.id)
            for picklist in picklists:
                if picklist.picked_quantity <= 0:
                    picklist.delete()
                elif picklist.stock:
                    cancel_location = CancelledLocation.objects.filter(picklist_id=picklist.id)
                    if not cancel_location:
                        CancelledLocation.objects.create(picklist_id=picklist.id,
                                                         quantity=picklist.picked_quantity,
                                                         location_id=picklist.stock.location_id,
                                                         creation_date=datetime.datetime.now(), status=1)
                        picklist.status = 'cancelled'
                        picklist.save()
                else:
                    picklist.status = 'cancelled'
                    picklist.save()
            order_det.status = 3
            order_det.save()
    gen_qs.delete()


def update_stock_transfer_po_batch(user, stock_transfer, stock, update_picked):
    try:
        st_po = stock_transfer.st_po
        temp_json = copy.deepcopy(PO_TEMP_JSON_DEF)
        if st_po:
            po = st_po.po
            open_st = st_po.open_st
            if po and po.status not in ['confirmed-putaway']:
                if po.status == 'stock-transfer':
                    po.status = ''
                    po.save()
                if user.userprofile.industry_type == 'FMCG':
                    exist_temp_json_objs = TempJson.objects.filter(model_id=po.id, model_name='PO').\
                                    exclude(model_json__icontains='"is_stock_transfer": "true"')
                    if exist_temp_json_objs.exists():
                        exist_temp_json_objs.delete()
                    temp_json['id'] = po.id
                    temp_json['unit'] = open_st.sku.measurement_type
                    temp_json['supplier_id'] = open_st.warehouse_id
                    temp_json['buy_price'] = open_st.price
                    temp_json['price'] = open_st.price
                    temp_json['po_quantity'] = open_st.order_quantity
                    temp_json['quantity'] = update_picked
                    temp_json['wms_code'] = open_st.sku.wms_code
                    temp_json['tax_percent'] = open_st.cgst_tax + open_st.sgst_tax + open_st.igst_tax
                    temp_json['mrp'] = 0
                    temp_json['mfg_date'] = ''
                    temp_json['exp_date'] = ''
                    temp_json['weight'] = ''
                    temp_json['is_stock_transfer'] = 'true'
                    if stock.batch_detail:
                        batch_detail = stock.batch_detail
                        temp_json['mrp'] = batch_detail.mrp
                        temp_json['weight'] = batch_detail.weight
                        temp_json['batch_no'] = batch_detail.batch_no
                        if batch_detail.manufactured_date:
                            temp_json['mfg_date'] = batch_detail.manufactured_date.strftime('%m/%d/%Y')
                        if batch_detail.expiry_date:
                            temp_json['exp_date'] = batch_detail.expiry_date.strftime('%m/%d/%Y')
                    TempJson.objects.create(model_id=po.id, model_name='PO', model_json=json.dumps(temp_json))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Adding stock transfer batch detail data failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(stock_transfer.__dict__), str(e)))


def create_extra_fields_for_order(created_order_id, extra_order_fields, user):
    try:
        order_field_objs = []
        for key, value in extra_order_fields.iteritems():
            if value:
                order_field_objs.append(OrderFields(**{'user': user.id, 'original_order_id': created_order_id,
                                                       'name': key, 'value': str(value)[:255]}))
        if order_field_objs:
            OrderFields.objects.bulk_create(order_field_objs)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create order extra fields failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(extra_order_fields), str(e)))

def get_mapping_values_po(wms_code = '',supplier_id ='',user =''):
    data = {}
    try:
        sku_master = SKUMaster.objects.get(wms_code=wms_code, user=user.id)
        if wms_code.isdigit():
            ean_number = wms_code
            sku_supplier = SKUSupplier.objects.filter(Q(sku__ean_number=wms_code) | Q(sku__wms_code=wms_code),
                                                      supplier_id=supplier_id, sku__user=user.id)
        else:
            ean_number = ''
            sku_supplier = SKUSupplier.objects.filter(sku__wms_code=wms_code, supplier_id=supplier_id, sku__user=user.id)
        if not sku_supplier:
            attr_mapping = copy.deepcopy(SKU_NAME_FIELDS_MAPPING)
            for attr_key, attr_val in attr_mapping.items():
                supplier_sku = SKUSupplier.objects.filter(user=user.id,
                                                          supplier_id=supplier_id,
                                                          attribute_type=attr_key,
                                                          attribute_value=getattr(sku_master, attr_val))
                if supplier_sku.exists():
                    sku_supplier = supplier_sku
        sup_markdown = SupplierMaster.objects.get(id=supplier_id)
        data = {'supplier_code': '', 'price': sku_master.cost_price, 'sku': sku_master.sku_code,'weight':'',
                'ean_number': 0, 'measurement_unit': sku_master.measurement_type}
        if sku_master.block_options:
            data['sku_block'] = sku_master.block_options
        else:
            data['sku_block'] = ''
        skuattributes = SKUAttributes.objects.filter(sku_id=sku_master.id, attribute_name = 'weight' )
        weight = ''
        if skuattributes.exists():
            weight = skuattributes[0].attribute_value
        data['weight'] = weight
        if sku_supplier:
            mrp_value = sku_master.mrp
            if sku_supplier[0].costing_type == 'Margin Based':
                margin_percentage = sku_supplier[0].margin_percentage
                prefill_unit_price = mrp_value - ((mrp_value * margin_percentage) / 100)
                tax=0
                tax_list=get_supplier_sku_price_values(supplier_id, wms_code, user)
                if len(tax_list):
                    tax_list=tax_list[0].get('taxes',[])
                    if len(tax_list):
                        tax_list = tax_list[0]
                        if tax_list.get('inter_state'):
                            tax=tax_list.get('igst_tax',0)+tax_list.get('apmc_tax',0)+tax_list.get('cess_tax',0)
                        else:
                            tax=tax_list.get('cgst_tax',0)+tax_list.get('sgst_tax',0)+tax_list.get('apmc_tax',0)+tax_list.get('cess_tax',0)

                prefill_unit_price = (prefill_unit_price * 100) / (100 + tax)
                data['price'] = float("%.2f" % prefill_unit_price)
            elif sku_supplier[0].costing_type == 'Markup Based':
                 markup_percentage = sku_supplier[0].markup_percentage
                 prefill_unit_price = mrp_value / (1+(markup_percentage/100))
                 data['price'] = float("%.2f" % prefill_unit_price)
            else:
                data['price'] = sku_supplier[0].price
            data['supplier_code'] = sku_supplier[0].supplier_code
            data['ean_number'] = ean_number
            if sku_supplier[0].sku is not None:
                data['sku'] = sku_supplier[0].sku.sku_code
                data['measurement_unit'] = sku_supplier[0].sku.measurement_type
        else:
            if int(sup_markdown.ep_supplier):
                data['price'] = 0
            mandate_supplier = get_misc_value('mandate_sku_supplier', user.id)
            if mandate_supplier == 'true' and not int(sup_markdown.ep_supplier):
                data['supplier_mapping'] = True
        if sku_master.block_options == "PO":
            if not int(sup_markdown.ep_supplier):
                data = {'error_msg':'This SKU is Blocked for PO'}
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Getting po Values failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(wms_code), str(e)))
    return data


@csrf_exempt
@login_required
@get_admin_user
def save_extra_order_options(request, user=''):
    try:
        data_dict = json.loads(request.POST.get('data'))
        field = data_dict.get('field','')
        options_list = data_dict.get('order_field_options')
        options_string = ",".join(options_list)
        misc_obj = MiscDetail.objects.filter(user=user.id,misc_type='extra_order_fields')
        if misc_obj.exists():
            misc_obj = misc_obj[0]
            misc_options = MiscDetailOptions.objects.filter(misc_detail= misc_obj,misc_key = field)
            if misc_options.exists():
                misc_options =  misc_options[0]
                misc_options.misc_value = options_string
                misc_options.save()
            else:
                MiscDetailOptions.objects.create(misc_detail= misc_obj,misc_key = field,misc_value = options_string)
            message = "Success"
        else:
            message = "Please Enter Extra Fields"
    except:
       import traceback
       log.debug(traceback.format_exc())
       log.info('Issue for ' + request)
       log.info('extra options Insert failed for %s and params are %s and error statement is %s' % (
       str(user), str(request.POST), str(e)))
       return HttpResponse("Something Went Wrong")
    return HttpResponse(json.dumps({'message': message}))


@get_admin_user
@csrf_exempt
@login_required
def get_sku_mrp(request ,user =''):
    mrp = 0
    wms_code  = json.loads(request.POST.get('wms_code',''))
    sku_mrp = SKUMaster.objects.filter(wms_code=wms_code, user=user.id).values('mrp')
    if sku_mrp :
        mrp = sku_mrp[0]['mrp']
    return HttpResponse(json.dumps({'mrp':mrp}))


def get_firebase_order_data(order_id):
    from firebase import firebase
    firebase = firebase.FirebaseApplication('https://pod-stockone.firebaseio.com/', None)
    try:
        result = firebase.get('/OrderDetails/'+order_id, None)
    except Exception as e:
        result = 0
        import traceback
        log.debug(traceback.format_exc())
        log.info('Firebase query  failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))
    return result

@get_admin_user
def get_classfication_settings(request, user =''):
    classifiaction_dict = {}
    classifiaction_dict =list(ClassificationSettings.objects.filter(user = user.id).values('id','classification','units_per_day'))
    return HttpResponse(json.dumps({'data': classifiaction_dict}))

@get_admin_user
def save_update_classification(request , user =''):
    data_dict = dict(request.POST)
    try:
        for ind in range(0, len(data_dict['id'])):
            if(data_dict['id'][ind]):
                classifcations = ClassificationSettings.objects.filter(id=data_dict['id'][ind])
                if classifcations:
                    classifcations.update(units_per_day=data_dict['units_per_day'][ind])
            else:
                classifcations = ClassificationSettings.objects.filter(classification=data_dict['classification'][ind] , user__id=user.id )
                if classifcations:
                    user_attr.update(units_per_day=data_dict['units_per_day'][ind])
                else:
                    ClassificationSettings.objects.create(
                                                  classification=data_dict['classification'][ind],
                                                  units_per_day=data_dict['units_per_day'][ind],
                                                  creation_date=datetime.datetime.now(),
                                                  user_id =user.id)
        return HttpResponse(json.dumps({'message': 'Updated Successfully'}))
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('classification query  failed for %s and params are %s and error statement is %s' % (
        str(user.username), str(request.POST.dict()), str(e)))

@get_admin_user
def delete_classification(request, user=''):
    id = request.GET.get('data_id', '')
    if id:
        ClassificationSettings.objects.filter(id=id).delete()
    return HttpResponse(json.dumps({'message': 'Updated Successfully', 'status': 1}))

def get_challan_number_for_dc(order , user):
    challan_sequence = ChallanSequence.objects.filter(user=user.id, status=1, marketplace=order.marketplace)
    if not challan_sequence:
        challan_sequence = ChallanSequence.objects.filter(user=user.id, marketplace='')
    if challan_sequence:
        challan_sequence = challan_sequence[0]
        challan_val = int(challan_sequence.value)
        challan_sequence.value = challan_val + 1
        challan_num = challan_sequence.value
        challan_sequence.save()
    else:
        ChallanSequence.objects.create(marketplace='', prefix='CHN', value=1, status=1, user_id=user.id,
                                       creation_date=datetime.datetime.now())
        challan_num = 1
    return challan_num


def get_sku_weight(sku):
    """ Returns SKU Weight"""
    weight = ''
    weight_obj = sku.skuattributes_set.filter(attribute_name='weight')
    if weight_obj.exists():
        weight = weight_obj[0].attribute_value
    return weight


@csrf_exempt
@login_required
@get_admin_user
def get_current_weight(request, user=''):
    from rest_api.views.weighing_machine_api import get_integration_weight_val
    weight_topic = get_misc_value('weight_integration_name', request.user.id)
    if weight_topic != 'false':
        result_val, is_updated = get_integration_weight_val(weight_topic)
        result_val = str(result_val).replace('\r\n', '')
        return HttpResponse(json.dumps({'weight': result_val, 'is_updated': is_updated, 'status': 1}))
    else:
        return HttpResponse(json.dumps({'weight': 0 , 'is_updated': False, 'status': 0}))


def fetch_asn_detailed_qty(sku_class_list, sku_users):
    overall_asn_stock = {'first_and_nk_set': {}, 'second_set': {}, 'third_set': {}}
    today_filter = datetime.datetime.today()
    threeday_filter = today_filter + datetime.timedelta(days=10)
    thirtyday_filter = today_filter + datetime.timedelta(days=45)
    asn_filters = {'quantity__gt': 0, 'sku__sku_class__in': sku_class_list, 'sku__user__in': sku_users,
                   'status': 'open'}
    asn_qs = ASNStockDetail.objects.filter(**asn_filters)
    asn_3_qs = asn_qs.filter(Q(arriving_date__lte=threeday_filter) | Q(asn_po_num='NON_KITTED_STOCK'))
    asn_3_ids = asn_3_qs.values_list('id', flat=True)
    asn_res_3days_qs = ASNReserveDetail.objects.filter(asnstock__in=asn_3_ids)
    asn_res_3days_qty = dict(
        asn_res_3days_qs.values_list('asnstock__sku__sku_code').annotate(in_res=Sum('reserved_qty')))
    intr_3d_st = dict(asn_3_qs.values_list('sku__sku_code').distinct().annotate(in_asn=Sum('quantity')))
    for k, v in intr_3d_st.items():
        if k in asn_res_3days_qty:
            intr_3d_st[k] = intr_3d_st[k] - asn_res_3days_qty[k]

    asn_30_qs = asn_qs.exclude(arriving_date__lte=threeday_filter).filter(arriving_date__lte=thirtyday_filter)
    asn_30_ids = asn_30_qs.values_list('id', flat=True)
    asn_res_30days_qs = ASNReserveDetail.objects.filter(asnstock__in=asn_30_ids)
    asn_res_30days_qty = dict(
        asn_res_30days_qs.values_list('asnstock__sku__sku_code').annotate(in_res=Sum('reserved_qty')))
    intr_30d_st = dict(asn_30_qs.values_list('sku__sku_code').distinct().annotate(in_asn=Sum('quantity')))
    for k, v in intr_30d_st.items():
        if k in asn_res_30days_qty:
            intr_30d_st[k] = intr_30d_st[k] - asn_res_30days_qty[k]

    asn_100_qs = asn_qs.filter(arriving_date__gt=thirtyday_filter)
    asn_100_ids = asn_100_qs.values_list('id', flat=True)
    asn_res_100days_qs = ASNReserveDetail.objects.filter(asnstock__in=asn_100_ids)
    asn_res_100days_qty = dict(asn_res_100days_qs.values_list('asnstock__sku__sku_code').annotate(
        in_res=Sum('reserved_qty')))
    intr_100d_st = dict(asn_100_qs.values_list('sku__sku_code').distinct().annotate(in_asn=Sum('quantity')))
    for k, v in intr_100d_st.items():
        if k in asn_res_100days_qty:
            intr_100d_st[k] = intr_100d_st[k] - asn_res_100days_qty[k]

    overall_asn_stock['first_and_nk_set'] = intr_3d_st
    overall_asn_stock['second_set'] = intr_30d_st
    overall_asn_stock['third_set'] = intr_100d_st
    return overall_asn_stock


@csrf_exempt
def get_zonal_admin_id(admin_user, reseller):
    zonal_id = 0
    try:
        zonal_admin_id = AdminGroups.objects.get(user_id=admin_user.id).group.user_set.filter(
            Q(userprofile__zone=reseller.userprofile.zone)).values_list('id', flat=True)
        if zonal_admin_id:
            zonal_id = zonal_admin_id[0]
            return zonal_id
    except Exception as e:
        import traceback
        log.info(traceback.format_exc())
        log.info('Users List exception raised')


def get_utc_start_date(date_obj):
    # Getting Time zone aware start time

    ist_unaware = datetime.datetime.strptime(str(date_obj.date()), '%Y-%m-%d')
    ist_aware = pytz.timezone("Asia/Calcutta").localize(ist_unaware)
    converted_date = ist_aware.astimezone(pytz.UTC)
    return converted_date


def get_stock_starting_date(receipt_number, receipt_type, user_id, stock_date):
    if receipt_type == 'purchase order':
        st_purchase = PurchaseOrder.objects.filter(order_id=receipt_number,
                                                   stpurchaseorder__open_st__sku__user=user_id)
        if st_purchase.exists():
            stock_receipt = st_purchase.\
                values_list('stpurchaseorder__stocktransfer__storder__picklist__stock__receipt_date',
                       'stpurchaseorder__stocktransfer__storder__picklist__stock__receipt_number',
                       'stpurchaseorder__stocktransfer__storder__picklist__stock__receipt_type',
                       'stpurchaseorder__stocktransfer__storder__picklist__stock__sku__user')[0]
            user_id = stock_receipt[3]
            stock_date = stock_receipt[0]
            stock_date = get_stock_starting_date(stock_receipt[1], stock_receipt[2], user_id, stock_date)
    return stock_date

def get_decimal_data(cell_data, index_status, count, user):
    if get_misc_value('float_switch', user.id) == 'false':
        try:
            cell_data = float(cell_data)
            frac, whole = math.modf(cell_data)
            if frac:
                index_status.setdefault(count, set()).add('Decimal Not Allowed In Qty')
        except:
            index_status.setdefault(count, set()).add('Invalid Number')
    return index_status

def get_supplier_sku_price_values(suppli_id, sku_codes,user):
    tax_type = ''
    inter_state_dict = dict(zip(SUMMARY_INTER_STATE_STATUS.values(), SUMMARY_INTER_STATE_STATUS.keys()))
    sku_codes = [sku_codes]
    result_data = []
    supplier_sku = []
    supplier_master = ""
    inter_state = 2
    edit_tax = False
    ep_supplier = False
    if suppli_id:
        supplier_master = SupplierMaster.objects.filter(id=suppli_id, user=user.id)
        if supplier_master:
            tax_type = supplier_master[0].tax_type
            inter_state = inter_state_dict.get(tax_type, 2)
            ep_supplier = supplier_master[0].ep_supplier
    for sku_code in sku_codes:
        if not sku_code:
            continue
        data = SKUMaster.objects.filter(sku_code=sku_code, user=user.id)
        if data:
            data = data[0]
        else:
            return "sku_doesn't exist"
        tax_masters = TaxMaster.objects.filter(user_id=user.id, product_type=data.product_type,
                                               inter_state=inter_state, max_amt__gte=data.price, min_amt__lte=data.price)
        taxes_data = []
        for tax_master in tax_masters:
            taxes_data.append(tax_master.json())
        if supplier_master:
            supplier_sku = SKUSupplier.objects.filter(sku_id=data.id, supplier_id=supplier_master[0].id)
        mandate_sku_supplier = get_misc_value('mandate_sku_supplier', user.id)
        if not supplier_sku and ep_supplier and mandate_sku_supplier == "true":
            edit_tax = True
        result_data.append({'wms_code': data.wms_code, 'sku_desc': data.sku_desc, 'tax_type': tax_type,
                            'taxes': taxes_data, 'mrp': data.mrp, 'edit_tax': edit_tax})

        return result_data


@csrf_exempt
@login_required
@get_admin_user
def save_misc_value(request, user=''):
    misc_dictionary = json.loads(request.POST.get('data'))
    if misc_dictionary:
        misc_obj=MiscDetail.objects.filter(user=user.id,misc_type=misc_dictionary.keys()[0])
        if misc_obj.exists():
            misc_obj=misc_obj[0]
            misc_obj.misc_value=misc_dictionary.values()[0]
            misc_obj.save()
        else:
            MiscDetail.objects.create(user=user.id, misc_type=misc_dictionary.keys()[0],misc_value=misc_dictionary.values()[0])
    return HttpResponse("Success")

@csrf_exempt
@login_required
@get_admin_user
def get_value_for_misc_type(request, user=''):
    misc_type=request.GET.get('misc_type')
    misc_value = get_misc_value(misc_type, user.id)
    return HttpResponse(json.dumps({'selected_view': misc_value}))


def get_distinct_price_types(user):
    price_types1 = list(PriceMaster.objects.exclude(price_type__in=["", 'D1-R', 'R-C']).
                       filter(sku__user=user.id).values_list('price_type', flat=True).
                       distinct())
    price_types2 = list(PriceMaster.objects.exclude(price_type__in=["", 'D1-R', 'R-C']).
                       filter(user=user.id).values_list('price_type', flat=True).
                       distinct())
    price_types = list(chain(price_types1, price_types2))
    return price_types

def validate_mrp_weight(data_dict, user):
    collect_dict_form = {}
    status = ''
    collect_all_sellable_location = list(LocationMaster.objects.filter(zone__segregation='sellable',  zone__user=user.id, status=1).values_list('location', flat=True))
    bulk_zones= get_all_zones(user ,zones=[MILKBASKET_BULK_ZONE])
    bulk_locations=list(LocationMaster.objects.filter(zone__zone__in=bulk_zones, zone__user=user.id, status=1).values_list('location', flat=True))
    sellable_bulk_locations=list(chain(collect_all_sellable_location ,bulk_locations))
    if data_dict['location'] in sellable_bulk_locations:
        sku_mrp_weight_map = StockDetail.objects.filter(sku__user=user.id, quantity__gt=0, sku__wms_code=data_dict['sku_code'],
                                             location__location__in=sellable_bulk_locations).\
                            exclude(batch_detail__mrp=data_dict['mrp'], batch_detail__weight=data_dict['weight']).values_list('sku__wms_code', 'batch_detail__mrp', 'batch_detail__weight').distinct()
        if sku_mrp_weight_map:
            for sku_code, mrp, weight_dict in sku_mrp_weight_map:
                mrp_weight_dict = {'mrp':[str(mrp)], 'weight':[weight_dict]}
                if sku_code in collect_dict_form.keys():
                    collect_dict_form[sku_code]['mrp'].append(mrp_weight_dict['mrp'][0])
                    collect_dict_form[sku_code]['weight'].append(mrp_weight_dict['weight'][0])
                else:
                    collect_dict_form[sku_code] = mrp_weight_dict
            if data_dict['sku_code'] in collect_dict_form.keys():
                if not str(data_dict['mrp']) in str(collect_dict_form[data_dict['sku_code']]["mrp"]) or not str(data_dict['weight']) in str(collect_dict_form[data_dict['sku_code']]["weight"]):
                    status = 'For SKU '+str(data_dict['sku_code'])+', MRP '+str(",".join(collect_dict_form[data_dict['sku_code']]["mrp"]))+' and WEIGHT '+str(",".join(collect_dict_form[data_dict['sku_code']]["weight"]))+' are only accepted.'
    return status

def mb_weight_correction(weight):
    if weight:
        weight = re.sub("\s\s+" , " ", weight).upper().replace('UNITS', 'Units').replace('PCS', 'Pcs').\
                replace('UNIT', 'Unit').replace('INCHES', 'Inches').replace('INCH', 'Inch').strip()
    return weight


def get_orders_with_invoice_no(user, invoice_no):
    if user.userprofile.user_type == 'marketplace_user':
        sos_objs = SellerOrderSummary.objects.filter(seller_order__order__user=user.id,
                                    invoice_number=invoice_no)
        invoice_qty_dict = dict(sos_objs.values_list('seller_order__order_id').annotate(Sum('quantity')))
    else:
        sos_objs = SellerOrderSummary.objects.filter(order__user=user.id, invoice_number=invoice_no)
        invoice_qty_dict = dict(sos_objs.values_list('order_id').annotate(Sum('quantity')))
    picklist_ids = sos_objs.values_list('picklist_id', flat=True)
    return invoice_qty_dict, picklist_ids


def get_full_sequence_number(user_type_sequence, creation_date):
    inv_num_lis = []
    if user_type_sequence.prefix:
        inv_num_lis.append(user_type_sequence.prefix)
    if user_type_sequence.date_type:
        if user_type_sequence.date_type == 'financial':
            inv_num_lis.append(get_financial_year(creation_date))
        elif user_type_sequence.date_type == 'month_year':
            inv_num_lis.append(creation_date.strftime('%m%y'))
    if user_type_sequence.interfix:
        inv_num_lis.append(user_type_sequence.interfix)
    inv_num_lis.append(str(user_type_sequence.value).zfill(3))
    sequence_number = '/'.join(['%s'] * len(inv_num_lis)) % tuple(inv_num_lis)
    return sequence_number
