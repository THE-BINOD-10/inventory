import datetime
import requests
import traceback
import json
from PullFromStockone.models import *

dns = 'http://94.130.136.118:8988/rest_api/'


def populate_api_item_data(user_id):
    url = dns + 'GetItemMaster/'
    resp_data = requests.post(url=url, data={'user_id': user_id})
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
            #return status
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
    import pdb;pdb.set_trace()
    resp_data = requests.post(url=url, data={'user_id': user_id})
    for obj in resp_data.json():
        print obj
        #sample_obj = {u'bill_of_lading_dt': u'03/07/2017', u'other_reference': u'Other Reference', u'terms_of_payment': u'123', u'reference': 17180711882772, u'bill_of_lading_no': u'123', u'del_notes': [{u'delivery_note_no': '321', u'delivery_note_Date': u'03/07/2017'}], u'buyer_name': u'buyerSample', u'narration': u'Narration', u'carrier_name': u'Carry', u'orders': [u'MM/17-18/07/PO11882772'], u'address_line1': u'Address1234', u'buyer_tin_no': u'123', u'despatch_doc_no': u'MM/-//PO', u'destination': u'Chennai', u'party_ledger': {u'amount': 0, u'is_deemeed_positive': True}, u'voucher_foreign_key': u'17180711882772', u'buyer_state': u'State1234', u'party_ledger_tax': {u'amount': 12, u'entry_rate': 24, u'name': u'name12q', u'is_deemeed_positive': True}, u'voucher_typeName': u'Sales', u'despatched_through': u'Lorry', u'voucher_no': 17180711882772, u'terms_of_delivery_1': u'Check', u'tally_company_name': u'Mieone', u'items': [{u'ledger_name': u'LedgerName', u'name': u'Womens T-Shirt:Silly People Womens casual T-Shirt', u'is_deemeed_positive': True, u'rate': 456.0, u'rate_unit': u'123', u'amount': 123.0, u'actual_qty': 1.0, u'unit': u'mrp', u'billed_qty': 1.0}], u'type_of_dealer': u'Dealer123', u'buyer_cst_no': u'1223', u'dt_of_voucher': u'03/07/2017'}
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


#populate_api_item_data(3)

#populate_api_customer_data(3)

populate_api_sales_invoice_data(3)

#populate_api_sales_returns_data(3)

#populate_api_supplier_data()