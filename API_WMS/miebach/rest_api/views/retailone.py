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
from miebach_utils import *
from mail_server import send_mail, send_mail_attachment
from django.core import serializers
from django.template import loader, Context
import dicttoxml
from operator import itemgetter
from common import *
from xmljson import badgerfish as bf
from xml.etree.ElementTree import fromstring
#from retailone_api import *
import requests
import traceback
from urlparse import urlparse, urljoin, urlunparse, parse_qs
from retailone_api import *

retail_orders_url = 'http://176.9.181.39:8000/orders/'
HOST = 'http://dev.retail.one'
RETAIL_ADD_MARKETPLACE_URL = '/api/v1/seller'
EXTRA_INFO_FIELDS = ['flipkart_advantage']
IGNORE_MARKETPLACE = []

@csrf_exempt
def update_orders(orders, user=''):
    try:
        orders = orders.get('items', [])
        order_details = {}
        for order in orders:

            can_fulfill = order.get('can_fulfill', '1')
            channel_name = order['channel_sku']['channel'].get('name', '')
            is_fbm = order['channel_sku']['is_fbm']
            if is_fbm == "1" or channel_name in IGNORE_MARKETPLACE or can_fulfill == '0':
                continue

            order_details = copy.deepcopy(ORDER_DATA)
            data = order

            order_det = OrderDetail.objects.filter(order_id=data['channel_orderitem_id'],user=user.id)
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

            order_details['order_id'] = data['channel_orderitem_id']
            sku_code = SKUMaster.objects.filter(sku_code=data['sku'], user=user.id)
            if not sku_code:
                orders_track = OrdersTrack.objects.filter(order_id=order_details['order_id'], sku_code=data['sku'], user=user.id)
                if not orders_track:
                    OrdersTrack.objects.create(order_id=order_details['order_id'], sku_code=data['sku'], status=1, user=user.id,
                                               reason = "SKU Mapping doesn't exists", creation_date=NOW)
                continue

            order_details['sku_id'] = sku_code[0].id
            order_details['title'] = data['title']
            order_details['user'] = user.id
            order_details['quantity'] = data['quantity']
            order_details['shipment_date'] = data['ship_by']
            if not order_details['shipment_date']:
                order_details['shipment_date'] = order['ordered_on']
            order_details['marketplace'] = channel_name
            order_details['invoice_amount'] = data.get('total_price', 0)

            order_detail = OrderDetail(**order_details)
            order_detail.save()

            swx_mapping = SWXMapping.objects.filter(local_id = order_detail.id, swx_type='order')
            if not swx_mapping:
                mapping = SWXMapping(local_id=order_detail.id, swx_id=order['id'], swx_type='order', creation_date=NOW,updation_date=NOW)
                mapping.save()
    except:
        traceback.print_exc()


@csrf_exempt
@login_required
@get_admin_user
def get_marketplace_data(request, user=''):
    obj = RetailoneAPI()
    resp_data = obj.get_seller_channels(user=user.id)
    sample_dict = {"recordsTotal": len(resp_data), "recordsFiltered": len(resp_data), "draw": 1, "aaData": []}
    for dat in resp_data.get('data', ''):
        if not dat.get('last_pull', ''):
            dat['last_pull'] = ''
    sample_dict['aaData'] = resp_data['data']

    return HttpResponse(json.dumps(sample_dict))

@csrf_exempt
@login_required
@get_admin_user
def update_market_status(request, user=''):
    status_dict = {1: 'ACTIVE', 0: 'INACTIVE'}
    data_id = request.POST.get('data_id', '')
    status = request.POST.get('status', 1)
    obj = RetailoneAPI()
    data_dict = {'id': data_id, 'status': status_dict[int(status)]}
    resp_data = obj.add_update_marketplace(data_dict)
    if data_id and status != '':
        marketplace = Marketplaces.objects.filter(id=data_id).update(status=status)
    return HttpResponse("Updated Successfully")

@csrf_exempt
@login_required
@get_admin_user
def pull_market_data(request, user=''):
    marketplace = request.POST.get('marketplace', '')
    market_places = Marketplaces.objects.filter(user=user.id, status=1, name=marketplace)
    if not market_places:
        return HttpResponse(marketplace + ' is inactive')
    for market in market_places:
        if market.name == 'Flipkart':
            orders = requests.get(retail_orders_url)
            orders = orders.json()
            update_orders(orders, user)
        market.last_synced = datetime.datetime.now()
        market.save()
    return HttpResponse('updated Successfully')

@csrf_exempt
@login_required
@get_admin_user
def add_market_credentials(request, user=''):
    data_dict = {}
    form_data = request.POST
    status = {'message': 'Add Market failed'}
    url = urljoin(HOST, RETAIL_ADD_MARKETPLACE_URL)
    for key, value in form_data.iteritems():
        if key in EXTRA_INFO_FIELDS:
            data_dict.setdefault('extra_info', {})
            data_dict['extra_info'][key] = value
        else:
            data_dict[key] = value
    data_dict['user_id'] = user.id

    obj = RetailoneAPI()
    resp_data = obj.add_update_marketplace(data_dict)
    
    if resp_data.get('data', ''):
        status = {'auth_url': resp_data['data'].get('auth_url', ''), 'message': 'Redirecting to ' + form_data['market_place']}
    return HttpResponse(json.dumps(status))
