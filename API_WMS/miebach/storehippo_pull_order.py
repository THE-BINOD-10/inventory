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
from api_calls.views import *
from miebach.settings import *
import ConfigParser
pull_order_storehippo_stockone = init_logger('logs/pull_order_storehippo_stockone.log')
SCHEME = 'https'
LOAD_CONFIG = ConfigParser.ConfigParser()
LOAD_CONFIG.read(INTEGRATIONS_CFG_FILE)
stockone_url = LOAD_CONFIG.get('storehippo', 'orders_pull_url', '')
api_key = LOAD_CONFIG.get('storehippo', 'access_key', '')

def make_request():
    a = datetime.datetime.now()
    pull_order_storehippo_stockone.info(' ----- Started - Order Push Storehippo to Stockone -------')
    url = stockone_url
    headers =  {'access-key': api_key, 'content-type': 'application/json'}
    resp_data = []
    start_order_id = 4953
    stop_order_id = 5911
    lastKey = 1
    counter = 0
    start_list = [2200, 1769, 1330]
    for lis in start_list:
        response = requests.get(url, headers=headers, params={'limit':958, 'start':lis, 'total':1})
	if str(response.status_code) in ['500', '422', '409', '404', '403', '401', '400', '429']:
	    print "Error Occured"
	    break
	else:
	    resp_json = response.json()
	    resp_data += resp_json['data']
    pull_order_storehippo_stockone.info(' --- Response of Stockone - Branch Code ---')
    if resp_data:
        send_to_stockone_resp = sendToStockOne({'data':resp_data})
    b = datetime.datetime.now()
    delta = b - a
    time_taken = str(delta.total_seconds())
    print time_taken + 'in seconds'


def sendToStockOne(resp):
    resp = resp['data']
    stockone_auth = {}
    write_order_resp = ''
    get_client_secret_obj = User.objects.filter(username='acecraft')
    if get_client_secret_obj:
	try:
	    user_id = get_client_secret_obj[0].id
	    int_obj = Integrations.objects.filter(**{'user':user_id, 'name':'storehippo', 'status':1})
	    if not int_obj:
		Integrations.objects.create(**{'user':user_id, 'name':'storehippo', 'api_instance':'storehippo', 'status':1, 'client_id':stockone_auth['client_id'], 'secret':stockone_auth['client_secret']})
	    write_order_resp = writeOrders(get_client_secret_obj[0], resp)
	except:
	    print "Error in Creating Orders"
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


def store_hippo_line_items(line_items):
    itemsArr = []
    for Item in line_items:
        cgst_percent = 0
        sgst_percent = 0
        igst_percent = 0
        for ind in Item['taxes']:
            if ind['name'] == "IGST":
                igst_percent += ind['rate']
            if ind['name'] == "SGST":
                sgst_percent += ind['rate']
            if ind['name'] == "CGST":
                cgst_percent += ind['rate']
        obj = {
            "line_item_id": Item.get('_id',None),
            "sku": Item.get('sku',None),
            "name": Item.get('name',None),
            "quantity": Item.get('quantity',None),
            "unit_price": Item.get('price',None),
            "shipping_charge": Item.get('shipping_total',None),
            "discount_amount": 0,
            "tax_percent": {
                "CGST": cgst_percent,
                "SGST": sgst_percent,
                "IGST": igst_percent
            }
        }
        itemsArr.append(obj)
    return itemsArr


def writeOrders(user, store_hippo_data_list):
    api_status = 'fail'
    allOrders = []
    for store_hippo_data in store_hippo_data_list:
        data = {}
        data_dict = {}
        count = 0
        pull_order_storehippo_stockone.info('Push Store Hippo Data' + str(store_hippo_data))
        create_order = {}
        customer_obj = store_hippo_data.get('billing_address', '')
        create_order['source'] = 'store_hippo'
        create_order['original_order_id'] = store_hippo_data.get('order_id', '')
        create_order['order_id'] = create_order.get('original_order_id', '')
        create_order['order_code'] = ''
        create_order['order_date'] = store_hippo_data['created_on'][0:10] + " " + store_hippo_data['created_on'][11:19]
        create_order['order_status'] = 'NEW'
        create_order['billing_address'] = customer_obj
        create_order['shipping_address'] = store_hippo_data.get('shipping_address', '')
        create_order['items'] = store_hippo_line_items(store_hippo_data.get('items', ''))
        create_order['discount'] = store_hippo_data.get('discounts_total', 0)
        create_order['shipping_charges'] = store_hippo_data.get('shipping_total', 0)
        create_order['customer_name'] = customer_obj.get('full_name', '')
        create_order['customer_code'] = ''
        create_order['item_count'] = store_hippo_data.get('item_count', 0)
        create_order['all_total_items'] = store_hippo_data.get('sub_total', 0)
        create_order['all_total_tax'] = store_hippo_data.get('taxes_total', 0)
        create_order['status'] = store_hippo_data.get('status', 0)
        create_order['fulfillmentStatus'] = store_hippo_data.get('fulfillment_status', '')
        create_order['custom_shipping_applied'] = store_hippo_data.get('custom_shipping_applied', 0)
        create_order['order_reference'] = store_hippo_data.get('_id', '')
        admin_discounts = store_hippo_data.get('discounts', [])
        if admin_discounts:
            admin_discounts = admin_discounts[0].get('saved_amount',0)
        create_order['invoice_amount'] = create_order.get('all_total_items', 0) + create_order.get('all_total_tax', 0) + create_order.get('shipping_charges', 0) - create_order.get('discount', 0)
        allOrders.append(create_order)
    try:
        validation_dict, failed_status, final_data_dict = validate_orders_format_storehippo(allOrders, user=user, company_name='mieone')
        if validation_dict:
            return json.dumps({'messages': validation_dict, 'status': 0})
        if failed_status:
            if type(failed_status) == dict:
                failed_status.update({'Status': 'Failure'})
            if type(failed_status) == list:
                failed_status = failed_status[0]
                failed_status.update({'Status': 'Failure'})
            return json.dumps(failed_status)
        create_order_storehippo_log.info('StoreHippo Data Sent to Stockone ' + str(final_data_dict))
        status = update_order_dicts(final_data_dict, user=user, company_name='storehippo')
        create_order_storehippo_log.info(status)
        return status
    except Exception as e:
        import traceback
        create_order_storehippo_log.debug(traceback.format_exc())
        create_order_storehippo_log.info('Update orders data failed for %s and params are %s and error statement is %s' % (str(user_obj.username), str(request.body), str(e)))
        status = {'messages': 'Internal Server Error', 'status': 0}
        return status

make_request()
