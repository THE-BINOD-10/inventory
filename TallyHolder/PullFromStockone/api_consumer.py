activate_this = 'C:\\Users\stockone\\Downloads\\Project\\WMS_ANGULAR\\TallyHolder\\stockone\\Scripts\\activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
import os, sys
sys.path.append('C:\\Users\\stockone\\Downloads\\Project\\WMS_ANGULAR\\TallyHolder')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TallyHolder.settings")
import django
django.setup()
import datetime
import requests
import traceback
import json

from django.db.models import Max
from PullFromStockone.models import *
from tally.tally.logger_file import *

log = init_logger('logs/stockone_to_db.log')

dns = 'http://beta.stockone.in:8988/rest_api/'

def get_latest_updation_date(model_name, filter_dict={}):
    updated_date = model_name.objects.filter(**filter_dict).aggregate(Max('updated_at'))['updated_at__max']
    if not updated_date:
        return ''
    return str(updated_date)

def populate_api_item_data(user_id):
    log.info('------Item Master started Data transfer to Local DB-----')
    url = dns + 'GetItemMaster/'
    data = {'user_id': user_id}
    upd_date = get_latest_updation_date(ItemMaster, filter_dict={'client_name': user_id})
    if upd_date:
        data['updation_date'] = upd_date
    resp_data = requests.post(url=url, data=data)
    for obj in resp_data.json():
        try:
            data = {'client_name': user_id, 'item_code': obj['sku_code'],
                    'ip': '', 'port': '', 'data': json.dumps(obj), 'push_status': 0,
                    }
            item_ins = ItemMaster.objects.filter(item_code=data['item_code'], client_name=user_id)
            if not item_ins:
                status = ItemMaster(**data)
                status.save()
            else:
                item_ins.update(data=data['data'], push_status=0, updated_at=str(datetime.datetime.now()))
        except:
            log.info('------Item Master Error Occured-----')
            log.debug(traceback.format_exc())
            return traceback.format_exc()
    log.info('------Item Master Data transfer Completed-----')
    return 0

def populate_api_customer_data(user_id):
    log.info('------Customer Master started Data transfer to Local DB-----')
    url = dns + 'GetCustomerMaster/'
    data = {'user_id': user_id}
    upd_date = get_latest_updation_date(CustomerVendorMaster, filter_dict={'client_name': user_id})
    if upd_date:
        data['updation_date'] = upd_date
    resp_data = requests.post(url=url, data=data)
    for obj in resp_data.json():
        try:
            data = {'client_name': str(user_id), 'customer_id': obj['ledger_name'],
                    'ip': '', 'port': '', 'data': json.dumps(obj), 'push_status': 0,
            }
            customer_ins = CustomerVendorMaster.objects.filter(customer_id=data['customer_id'], client_name=user_id)
            if not customer_ins:
                status = CustomerVendorMaster(**data)
                status.save()
            else:
                customer_ins.update(data=data['data'], push_status=0)
        except:
            log.info('------Customer Master Error Occured-----')
            log.debug(traceback.format_exc())
            return traceback.format_exc()
    log.info('------Customer Master Data transfer completed-----')
    return 0


def populate_api_supplier_data():
    url = dns + 'GetSupplierMaster/'
    resp_data = requests.post(url=url, data={})
    for obj in resp_data.json():
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
    log.info('------Sales Invoice started Data transfer to Local DB-----')
    url = dns + 'GetSalesInvoices/'
    data = {'user_id': user_id}
    upd_date = get_latest_updation_date(SalesInvoice, filter_dict={'client_name': user_id})
    if upd_date:
        data['updation_date'] = upd_date
    resp_data = requests.post(url=url, data=data)
    for obj in resp_data.json():
        try:
            data = {'client_name': user_id, 'invoice_num': obj['voucher_no'],
                    'ip': '', 'port': '', 'data': json.dumps(obj), 'push_status': 0, 'order_id': obj['voucher_foreign_key']
                    }
            status = SalesInvoice(**data)
            status.save()
        except:
            log.info('------Sales Invoice Error Occured-----')
            log.debug(traceback.format_exc())
            return traceback.format_exc()
    log.info('------Sales Invoice Data transfer Completed-----')
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
            return traceback.format_exc()
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

#populate_api_item_data(12)
#populate_api_customer_data(12)
populate_api_sales_invoice_data(12)
