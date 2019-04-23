import requests
import jwt

import time
import json

import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from django.db.models import Q
from miebach_admin.models import *
import datetime
from rest_api.views.utils import *
from miebach.settings import *
import ConfigParser
order_pull_rista_stockone_logs = init_logger('logs/rista_order_pull_stockone.log')
SCHEME = 'https'
LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read(INTEGRATIONS_CFG_FILE)
stockone_url = LOAD_CONFIG.get('rista', 'stockone_url', '')
API_HOST = LOAD_CONFIG.get('rista', 'rista_app_url', '')
ENDPOINT = LOAD_CONFIG.get('rista', 'inventory_indent_url', '')
rista_location_keys = eval(LOAD_CONFIG.get('rista', 'rista_location_keys', ''))
branch_list = rista_location_keys.keys()
map_stockone_rista_username = eval(LOAD_CONFIG.get('rista', 'map_stockone_rista_username', ''))

def make_request():
    a = datetime.datetime.now()
    order_pull_rista_stockone_logs.info(' ----- Started - Order Push Rista to Stockone -------  branch_list' + str(branch_list))
    url = "{}://{}{}".format(SCHEME, API_HOST, ENDPOINT)
    for branch_code in branch_list:
        get_api_key_secret = rista_location_keys[branch_code]
        apiKey = get_api_key_secret[0]
        secretKey = get_api_key_secret[1]
        tokencreationtime = int(round(time.time()))
        jti = int(time.time() * 1000.0)
        payload = { "jti": jti, "iss": apiKey, "iat": tokencreationtime }
        token = jwt.encode(payload, secretKey, algorithm='HS256')
        headers =  { 'x-api-key': apiKey, 'x-api-token': token, 'content-type': 'application/json' }
        inv_payload = {'branch' : branch_code, 'day' : str(datetime.datetime.now().date())}
        resp_data = []
        lastKey = 1
        while lastKey:
            response = requests.get(url, headers=headers, params=inv_payload)
            if str(response.status_code) in ['500', '422', '409', '404', '403', '401', '400']:
                lastKey = 0
	    else:
                resp_json = response.json()
                resp_data += resp_json['data']
                if 'lastKey' in resp_json.keys():
                    lastKey = 1
                    inv_payload['lastKey'] = resp_json['lastKey']
                else:
                    lastKey = 0
        order_pull_rista_stockone_logs.info(' --- Response of Stockone - Branch Code' + branch_code + ' ------' + str(resp_data))
        if resp_data:
            send_to_stockone_resp = sendToStockOne({'data':resp_data}, branch_code)
    b = datetime.datetime.now()
    delta = b - a
    time_taken = str(delta.total_seconds() * 1000)
    order_pull_rista_stockone_logs.info('----- Ended - Order Push Rista to Stockone ------- ')


def sendToStockOne(resp, branch_code):
    resp = resp['data']
    stockone_auth = {}
    write_order_resp = ''
    branch_code = map_stockone_rista_username[branch_code]
    get_client_secret = User.objects.filter(username=branch_code)
    if get_client_secret:
	get_client_secret = get_client_secret[0].oauth2_provider_application.values()
	if get_client_secret:
	    get_client_secret = get_client_secret[0]
	    stockone_auth['client_id'] = get_client_secret['client_id']
	    stockone_auth['client_secret'] = get_client_secret['client_secret']
	    stockone_auth['client_name'] = get_client_secret['name']
	    stockone_auth['client_type'] = get_client_secret['client_type']
	    stockone_auth['authorization_grant_type'] = 'client_credentials'
	    stockone_auth['redirect_uris'] = get_client_secret['redirect_uris']
    	try:
	    access_token = getAuthToken(stockone_auth)
	except:
	    order_pull_rista_stockone_logs.info('Error in generating Access Token for Username - ' + str(branch_code))
	try:
            user_id = get_client_secret['user_id']
	    int_obj = Integrations.objects.filter(**{'user':user_id, 'name':'rista', 'status':0})
	    if not int_obj:
		Integrations.objects.create(**{'user':user_id, 'name':'rista', 'api_instance':'rista', 'status':0, 'client_id':stockone_auth['client_id'], 'secret':stockone_auth['client_secret']})
            write_order_resp = writeOrders(access_token, resp)
	except:
	    order_pull_rista_stockone_logs.info("Error in Creating Orders")
    return write_order_resp


def getAuthToken(stockone_auth):
    url = stockone_url + "/o/token/"
    dbData = [stockone_auth['client_id'], stockone_auth['client_secret'], stockone_auth['authorization_grant_type']]
    payload = "------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"client_id\"\r\n\r\n{}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"client_secret\"\r\n\r\n{}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"redirect_uri\n\n\"\r\n\r\nhttp://api.stockone.in/o/token/\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"grant_type\"\r\n\r\n{}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--".format(*dbData)
    headers = {'content-type': 'multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW'}
    response = requests.request("POST", url, data=payload,headers=headers)
    accessToken = response.json()['access_token']
    return accessToken


def clearLineItems(order):
    itemsArr = []
    sub_total_price = float(order['itemsAmount'])
    for Item in order['items']:
	tax_list = Item.get('taxes')
	cgst_percent = 0
	sgst_percent = 0
	for tax_value in tax_list:
	    if (tax_value['taxName']).startswith('CGST'):
		cgst_percent = tax_value['percentage']
	    if (tax_value['taxName']).startswith('SGST'):
                sgst_percent = tax_value['percentage']
	obj = {
	    "sku": Item.get('skuCode',None),
	    "name": Item.get('itemName',None),
	    "quantity": Item.get('quantity',None),
	    "unit_price": Item.get('unitCost',None),
            "measurement_type": Item.get('measuringUnit', None),
	    "shipping_charge": 0,
	    "discount_amount": 0,
	    "tax_percent": {
		"CGST": cgst_percent,
		"SGST": sgst_percent
	    }
	}
	itemsArr.append(obj)
    return itemsArr


def writeOrders(access_token, resp):
    api_status = 'fail'
    data = {}
    data_dict = {}
    url = stockone_url + "/api/rista_update_orders/"
    count = 0
    headers = {
            'Content-Type': "application/json",
            'Authorization': access_token
    }
    allOrders = []
    for order in resp:
	try:
	    customer_details = order['fromBranch']
            allOrders.append({
                    "source":"drunken_monkey",
                    "original_order_id": order['indentNumber'],
                    "order_id": order['indentNumber'],
                    "order_code": '',
                    "order_date": order['indentDate'][0:10] + " " + order['indentDate'][11:19],
                    "order_status": "NEW",
                    "billing_address": {},
                    "shipping_address": {},
                    "items": clearLineItems(order),
                    "discount": 0,
                    "shipping_charges": 0,
                    "invoice_amount": order['totalAmount'],
                    "customer_name": customer_details['branchName'],
                    "customer_code": customer_details['branchCode'],
                    "to_branch_code": order['branchCode'],
                    "to_branch_name": order['branchName'],
                    "item_count": order['itemCount'],
                    "all_total_items": order['itemsAmount'],
                    "all_total_tax": order['taxAmount'],
                    "status": order['status'],
                    "fulfillmentStatus": order['fulfillmentStatus']
	    })
	except:
	    print "Error Occured Order List Check"
    payload = json.dumps(allOrders)
    data_dict['all_orders'] = json.dumps(allOrders)
    data_dict['resp'] = json.dumps(resp)
    response = requests.request("POST", url, data=json.dumps(data_dict), headers=headers)
    return response

make_request()
