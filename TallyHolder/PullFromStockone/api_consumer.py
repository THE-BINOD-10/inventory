activate_this = 'C:\\Users\\Headrun\\Downloads\\TallyHolder\\TallyHolder\\headrunvenv\\Scripts\\activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
import os, sys
sys.path.append('C:\\Users\\Headrun\\Downloads\\TallyHolder\\TallyHolder\\TallyHolder')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TallyHolder.settings")
import django
django.setup()
import datetime
import requests
import traceback
import json
from PullFromStockone.models import *

dns = 'http://94.130.136.118:8988/rest_api/'

def populate_api_item_data(user_id):
    url = dns + 'GetItemMaster/'
    resp_data = requests.post(url=url, data={'user_id': user_id})
    print resp_data
    for obj in resp_data.json():
        try:
            data = {'client_name': user_id, 'item_code': obj['sku_code'],
                    'ip': '', 'port': '', 'data': json.dumps(obj), 'push_status': 0,
                    }

            status = ItemMaster(**data)
            status.save()
        except:
            print traceback.format_exc()
            return traceback.format_exc()
    return 0

def populate_api_customer_data(user_id):
    url = dns + 'GetCustomerMaster/'
    print(url)
    resp_data = requests.post(url=url, data={'user_id': user_id})
    print resp_data
    for obj in resp_data.json():
        try:
            data = {'client_name': str(user_id), 'customer_id': obj['ledger_name'],
                    'ip': '', 'port': '', 'data': json.dumps(obj), 'push_status': 0,
                    }
            status = CustomerVendorMaster(**data)
            status.save()
        except:
            pass
            #print traceback.format_exc()
            #return traceback.format_exc()
    return 0

def populate_api_supplier_data():
    url = dns + 'GetSupplierMaster/'
    resp_data = requests.post(url=url, data={})
    for obj in resp_data.json():
        print(obj)
        try:
            data = {'client_name': obj['tally_company_name'], 'customer_id': obj['sku_code'],
                    'ip': '', 'port': '', 'data': json.dumps(obj), 'push_status': 0,
                    }
            status = CustomerVendorMaster(**data)
            status.save()
            return status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

def populate_api_sales_invoice_data(user_id):
    url = dns + 'GetSalesInvoices/'
    resp_data = requests.post(url=url, data={'user_id': user_id})
    for obj in resp_data.json():
        try:
            data = {'client_name': user_id, 'invoice_num': obj['voucher_no'],
                    'ip': '', 'port': '', 'data': json.dumps(obj), 'push_status': 0, 'order_id': obj['voucher_foreign_key']
                    }
            status = SalesInvoice(**data)
            status.save()

        except:
            print traceback.format_exc()
            #return traceback.format_exc()
    return 0

def populate_api_sales_returns_data():
    url = dns + 'GetSalesReturns/'
    resp_data = requests.post(url=url, data={})
    for obj in resp_data.json():
        try:
            data = {'client_name': obj['tally_company_name'], 'customer_id': obj['invoice_num'],
                    'ip': '', 'port': '', 'data': json.dumps(obj), 'push_status': 0, 'order_id': obj['order_id']
                    }
            status = SalesReturn(**data)
            status.save()
        except:
            print traceback.format_exc()
            #return traceback.format_exc()
    return 0

def populate_api_purchase_invoice_data():
    url = dns + 'GetPurchaseInvoices/'
    resp_data = requests.post(url=url, data={})
    for key, obj in resp_data.json():
        try:
            data = {'client_name': obj['tally_company_name'], 'customer_id': obj['invoice_num'],
                    'ip': '', 'port': '', 'data': json.dumps(obj), 'push_status': 0, 'order_id': obj['order_id']
                    }
            status = PurchaseInvoice(**data)
            status.save()
        except:
            print traceback.format_exc()
            return traceback.format_exc()
    return 0

def populate_api_purchase_returns_data():
    url = dns + 'GetPurchaseReturns/'
    resp_data = requests.post(url=url, data={})
    for obj in resp_data.json():
        try:
            data = {'client_name': obj['tally_company_name'], 'customer_id': obj['invoice_num'],
                    'ip': '', 'port': '', 'data': json.dumps(obj), 'push_status': 0, 'order_id': obj['order_id']
                    }
            status = PurchaseReturn(**data)
            status.save()
        except:
            return traceback.format_exc()
    return status

populate_api_item_data(3)

populate_api_customer_data(3)

populate_api_sales_invoice_data(3)

populate_api_sales_returns_data(3)

populate_api_supplier_data(3)