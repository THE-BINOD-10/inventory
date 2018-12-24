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


apiKey = '945ae8b1-1886-43f4-9d0e-4986c0f383d3'
secretKey = 'lolnJIoZK2otG_d_PUiAXFgWOWOuglfJ8wnwNvDhg-w'

API_HOST = 'api.ristaapps.com'
ENDPOINT = '/v1/inventory/indents/page'

SCHEME = 'https'

def make_request():
    tokencreationtime = int(round(time.time()))
    payload = {
        "iss": apiKey,
        "iat": tokencreationtime
    }
    token = jwt.encode(payload, secretKey, algorithm='HS256')
    import pdb;pdb.set_trace()
    headers =  {
        'x-api-key': apiKey,
        'x-api-token': token,
        'content-type': 'application/json'
    }
    url = "{}://{}{}".format(SCHEME, API_HOST, ENDPOINT)
    inv_payload = {'branch' : 'BW', 'day' : '2018-12-23'}
    resp = requests.get(url, headers=headers, params=inv_payload)
    #with open('inventory_indent.json', 'w') as f:
    #    f.write(resp.content)
    #import pdb;pdb.set_trace()
    print len(resp.json())
    print resp.json()
    if resp.json():
	sendToStockOne(resp.json())


def sendToStockOne(resp):
    resp = resp['data']
    import pdb;pdb.set_trace()
    stockone_auth = {}
    get_client_secret = User.objects.filter(username='BW')
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
	print "Error in generating Access Token"
    try:
	writeOrders(access_token, resp)
    except:
	print "Error in Creating Orders"


def getAuthToken(stockone_auth):
        url = "http://beta.stockone.in:3331/o/token/"
	dbData = [stockone_auth['client_id'], stockone_auth['client_secret'], stockone_auth['authorization_grant_type']]
	payload = "------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"client_id\"\r\n\r\n{}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"client_secret\"\r\n\r\n{}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"redirect_uri\n\n\"\r\n\r\nhttp://api.stockone.in/o/token/\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name=\"grant_type\"\r\n\r\n{}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--".format(*dbData)
        headers = {'content-type': 'multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW'}
        response = requests.request("POST", url, data=payload,headers=headers)
        #import pdb;pdb.set_trace()
        accessToken = response.json()['access_token']
    	return accessToken


def clearLineItems(order):
    itemsArr = []
    sub_total_price = float(order['itemsAmount'])
    #cgst_percent = 0
    #sgst_percent = 0
    #for ind in order.get('tax_lines'):
	#if ind['title'] == "CGST":
	    #cgst_percent = (float(ind['price']) * 100) / sub_total_price
	#elif ind['title'] == "SGST":
	    #sgst_percent = (float(ind['price']) * 100) / sub_total_price
    #import pdb;pdb.set_trace()
    for Item in order['items']:
	tax_list = Item.get('taxes')
	cgst_percent = 0
	sgst_percent = 0
	for tax_value in tax_list:
	    if (tax_value['taxName']).startswith('CGST'):
		cgst_percent = tax_value['percentage']
	    if (tax_value['taxName']).startswith('SGST'):
                sgst_percent = tax_value['percentage']
	    #tax_value['percentage']
	    #tax_value['taxName']
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
    url = "http://beta.stockone.in:3331/api/rista_update_orders/"
    count = 0
    headers = {
            'Content-Type': "application/json",
            'Authorization': access_token
    }
    allOrders = []
    for order in resp:
	try:
	    customer_details = order['fromBranch']
            import pdb;pdb.set_trace()
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
	    print "Order List Check"
    payload = json.dumps(allOrders)
    response = requests.request("POST", url, data=payload, headers=headers)
    return True

make_request()
