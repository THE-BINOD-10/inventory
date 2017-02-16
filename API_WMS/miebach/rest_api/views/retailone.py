from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import os
import json, ast, traceback
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
import requests
import traceback
from urlparse import urlparse, urljoin, urlunparse, parse_qs
from retailone_api import *
from dateutil import parser

from utils import *

#retail_orders_url = 'http://176.9.181.39:8000/orders/'
#HOST = 'http://dev.retail.one'
#HOST = 'http://176.9.181.43:9111'
HOST = 'http://beta.retail.one'

retail_orders_url = '/api/v1/channels/orders/sync'
RETAIL_ADD_MARKETPLACE_URL = '/api/v1/seller'
EXTRA_INFO_FIELDS = ['merchant_id', 'auth_token', 'secret_key']
IGNORE_MARKETPLACE = []

log = init_logger('logs/retailone.log')

@csrf_exempt
def update_orders(orders, user='', from_returns=False):
    try:
        orders = orders.get('items', [])
        order_details = {}
        log.info('orders: %s', len(orders))
        for order in orders:
            try:
                order_id = order['order_id'].replace('-', '')
                order_id = ''.join(re.findall('\d+', order_id))
                original_order_id = order['order_id']

                can_fulfill = order.get('can_fulfill', '1')
                channel_name = order['channel_sku']['channel'].get('name', '')
                is_fbm = order['channel_sku']['is_fbm']
                if is_fbm == "1" or channel_name in IGNORE_MARKETPLACE or can_fulfill == '0':
                    continue

                order_details = copy.deepcopy(ORDER_DATA)
                data = order

                order_det = OrderDetail.objects.filter(order_id=order_id,user=user.id)
                if order_det:
                    order_det = order_det[0]
                    swx_mapping = SWXMapping.objects.filter(local_id = order_det.id, swx_type='order')
                    if swx_mapping:
                        for mapping in swx_mapping:
                            mapping.swx_id = order['id']
                            mapping.updation_date = NOW
                            mapping.save()
                    else:
                        mapping = SWXMapping(local_id=order_det.id, swx_id=order['id'], swx_type='order', creation_date=NOW,updation_date=NOW)
                        mapping.save()
                    continue
                if not data['sku']: continue
                order_details['order_id'] = order_id
                sku_code = SKUMaster.objects.filter(sku_code=data['sku'], user=user.id)
                log.info('sku_code: %s', sku_code)
                if not sku_code:
                    orders_track = OrdersTrack.objects.filter(order_id=order_details['order_id'], sku_code=data['sku'], user=user.id)
                    if not orders_track:
                        OrdersTrack.objects.create(order_id=order_details['order_id'], sku_code=data['sku'], status=1, user=user.id,
                                                   reason = "SKU Mapping doesn't exists", creation_date=NOW)
                    continue

                order_details['order_code'] = ''.join(re.findall('\D+', data['order_id']))
                order_details['sku_id'] = sku_code[0].id
                order_details['title'] = data['title']
                order_details['user'] = user.id
                order_details['quantity'] = data['quantity']
                order_details['shipment_date'] = data['ship_by']
                if not order_details['shipment_date']:
                    order_details['shipment_date'] = order['order_date']
                order_details['marketplace'] = channel_name
                order_details['invoice_amount'] = data.get('total_price', 0)
                order_details['original_order_id'] = original_order_id

                if from_returns:
                    order_details['status'] = 3

                order_detail = OrderDetail(**order_details)
                order_detail.save()

                swx_mapping = SWXMapping.objects.filter(local_id = order_detail.id, swx_type='order')
                if not swx_mapping:
                    mapping = SWXMapping(local_id=order_detail.id, swx_id=order['id'], swx_type='order', creation_date=NOW,updation_date=NOW)
                    mapping.save()
            except:
                log.error('%s', traceback.format_exc())
    except:
        log.error('%s', traceback.format_exc())

def update_returns(orders, user=''):
    try:
        order_details = {}
        for ind, order in enumerate(orders['items']):
            try:
                order_id = order['order_id'].replace('-', '')
                order_id = ''.join(re.findall('\d+', order_id))
                order_code = ''.join(re.findall('\D+', order['order_id']))
                return_date = order['return_date']
                return_date = parser.parse(return_date) if return_date else ''
                return_id = order['return_id']
                #filter_params = {'user': user.id, 'order_id': order_id}
                filter_params = {'order_id': order_id}
                if order_code:
                    filter_params['order_code'] = order_code
                #if order_mapping.get('order_items', ''):
                #    order_items = eval(order_mapping['order_items'])

                #for order in order_items:
                sku_code = order['sku']
                if not sku_code:
                    continue

                filter_params['sku__sku_code'] = sku_code
                order_data = OrderDetail.objects.filter(**filter_params)
                if not order_data:
                    continue
                order_data = order_data[0]
                return_instance = OrderReturns.objects.filter(return_id=return_id, order_id=order_data.id, order__user=user.id)
                if return_instance:
                    continue
                return_data = copy.deepcopy(RETURN_DATA)
                return_data['return_id'] = return_id
                return_data['damaged_quantity'] = 0
                return_data['quantity'] = order['quantity']
                return_data['return_type'] = order['return_type']
                return_data['return_date'] = return_date
                return_data['order_id'] = order_data.id
                return_data['sku_id'] = order_data.sku_id
                return_data['status'] = 1
                order_returns = OrderReturns(**return_data)
                order_returns.save()
            except:
                log.error('%s', traceback.format_exc())
    except:
        log.error('%s', traceback.format_exc())

@csrf_exempt
@login_required
@get_admin_user
def get_marketplace_data(request, user=''):
    obj = RetailoneAPI()
    resp_data = obj.get_seller_channels(user=user)
    return HttpResponse(json.dumps(resp_data))

@csrf_exempt
@login_required
@get_admin_user
def update_market_status(request, user=''):
    status_dict = {"true": True, "false": False}
    data_id = request.POST.get('data_id', '')
    status = request.POST.get('status', '')
    obj = RetailoneAPI()
    data_dict = {'id': data_id, 'is_active': status_dict[status], 'form' : 'status'}

    #user_details
    data_dict.setdefault('user_details', {})
    data_dict['user_details']['user_id'] = str(user.id)
    data_dict['user_details']['source'] = "stockone" 

    resp_data = obj.add_update_marketplace(data_dict, user = user.id)
    return HttpResponse("Updated Successfully")

def _pull_market_data(user, account_id, marketplace):
    obj = RetailoneAPI()
    user_details = 'user='+ str(user.id) + '&username=' + str(user.username)
    url_string = marketplace+'/orders/pull?mp_info_id='+account_id+'&'+user_details

    if marketplace:
        resp_data = obj.pull_marketplace_data(url_string, user = user)
        if 'errorCode' in resp_data.keys() or 'error_message' in resp_data.keys():
            return HttpResponse(json.dumps({ 'status' : 'Pull Now Failed', 'errorMessage' : resp_data }))

    try:
        log.info('calling sync orders')
        resp = requests.post(urljoin(HOST, retail_orders_url), data=json.dumps({"sync_token": 0, 'user' : user.id, "mp_info_id": int(account_id) if account_id else '', 'states': ['APPROVED', 'UnShipped', 'Pending'], 'source' : 'stockone', 'marketplace' : marketplace }))
    except:
        log.error('%s', traceback.format_exc())
        return HttpResponse(json.dumps({ 'status' :  '500', 'errorMessage': 'Pull Now Failed' }))

    resp = resp.json()
    log.info('resp: %s', len(resp))
    if resp:
        log.info("Updating resp")
        update_orders(resp, user)
    else:
        log.info("nothing to update")

    try:
        log.info('calling sync orders for RETURNS')
        resp = requests.post(urljoin(HOST, retail_orders_url), data=json.dumps({"sync_token": 0, 'user' : user.id, "mp_info_id": int(account_id) if account_id else '', 'states': ['RETURNS'], 'source' : 'stockone', 'marketplace' : marketplace }))
    except:
        log.error('%s', traceback.format_exc())
        return HttpResponse(({ 'status' : '500', 'errorMessage': 'Pull Now Failed' }))

    resp = resp.json()
    log.info("resp: %s", len(resp))
    if resp:
        log.info("Updating resp")
        update_orders(resp, user, from_returns=True)
        update_returns(resp, user)
    else:
        log.info("nothing to update")


@csrf_exempt
@login_required
@get_admin_user
def pull_market_data(request, user=''):
    marketplace = str(request.POST.get('marketplace', ''))
    account_id = str(request.POST.get('account_id', ''))

    _pull_market_data(user, account_id, marketplace)

    status_resp = json.dumps({ 'status' : 'Pull Successfully' })

    return HttpResponse(status_resp)

@csrf_exempt
@login_required
@get_admin_user
def add_market_credentials(request, user=''):
    data_dict = {}
    form_data = request.POST
    status = {'message': 'Add Market failed'}
    for key, value in form_data.iteritems():
        if key in EXTRA_INFO_FIELDS:
            data_dict.setdefault('extra', {})
            data_dict['extra'][key] = value
        else:
            data_dict[key] = value
    log.info('user: %s', user)
    data_dict['user'] = user.id

    #user_details
    data_dict.setdefault('user_details', {})
    data_dict['user_details']['first_name'] = str(user.first_name)
    data_dict['user_details']['last_name'] = str(user.last_name)
    data_dict['user_details']['user_id'] = str(user.id)
    data_dict['user_details']['user_name'] = str(user.username)
    data_dict['user_details']['email'] = str(user.email)
    data_dict['user_details']['source'] = "stockone"

    obj = RetailoneAPI()
    resp_data = obj.add_update_marketplace(data_dict)

    if resp_data.get('data', ''):
	marketplace = form_data['market_place']
	account_name = resp_data['data'].get('name', '')
	if data_dict['form'] == "update":
    	    status = {'auth_url' : '', 'message': 'Updated '+marketplace+' of Name "'+ account_name +'"', 'marketplace' : marketplace}
	if data_dict['form'] == "add":
	    if marketplace == "flipkart":
		auth_url = resp_data['data'].get('auth_url', '')
		if auth_url:
		    status = { 'auth_url' : auth_url, 'message': 'Redirecting to '+marketplace, 'marketplace' : marketplace }
		else:
		    status = {'auth_url' : '', 'message': 'Something Went Wrong', 'marketplace' : marketplace }
	    else:
	        account_name = resp_data['data']['data'].get('name', '')
	        status = {'auth_url' : '', 'message': 'Added '+marketplace+' of Name "'+ account_name +'"', 'marketplace' : marketplace}

    elif resp_data['errorCode'] == 'dataInconsistency':
	status = { 'auth_url' : '', 'message': resp_data['errorMessage'] }

    return HttpResponse(json.dumps(status))

@csrf_exempt
def get_marketplace_logo(request, user=''):
    obj = RetailoneAPI()
    resp_data = obj.get_all_channel_data()
    return HttpResponse(json.dumps(resp_data))

@csrf_exempt
@login_required
@get_admin_user
def order_management_toggle(request, user=''):
    toggle = request.GET.get('order_manage', '')
    if toggle:
        config_obj, created = MiscDetail.objects.get_or_create( user = user.id, misc_type="order_manage" )
        config_obj.misc_value = toggle
        config_obj.save()

        integrations_obj, is_created = Integrations.objects.get_or_create(user=user.id, name='retailone', api_instance='RetailoneAPI')
        integrations_obj.status = 1 if toggle == 'true' else 0
        integrations_obj.save()
    return HttpResponse(toggle)
