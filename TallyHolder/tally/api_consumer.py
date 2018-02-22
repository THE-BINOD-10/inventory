import requests
import traceback
from tally_wrapper import TallyBridgeApp
bridge = TallyBridgeApp(dll="C:\\Users\\stockone\\TallySetup\\WMS_ANGULAR\\tally\\tally\\DLL\\TallyBridgeDll.dll")
dns = 'http://94.130.136.118:8988/rest_api/';

def apiItemData():
    url = dns + 'GetItemMaster/';
    resp_data = requests.post(url = url, data = {})
    for obj in resp_data.json():
        try:
            status = bridge.item_master(obj)
            print status
            return status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

def apiCustomerData():
    url = dns + 'GetCustomerMaster/';
    resp_data = requests.post(url = url, data = {})
    for obj in resp_data.json():
        print obj
        try:
            status = bridge.customer_and_vendor_master(obj)
            print status
            return status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

def apiSupplierData():
    url = dns + 'GetSupplierMaster/';
    resp_data = requests.post(url = url, data = {})
    for obj in resp_data.json():
        try:
            status = bridge.customer_and_vendor_master(obj)
            print status
            return status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

def apiSalesInvoiceData():
    url = dns + 'GetSalesInvoices/';
    resp_data = requests.post(url = url, data = {})
    for obj in resp_data.json():
        #sample_obj = {u'bill_of_lading_dt': u'03/07/2017', u'other_reference': u'Other Reference', u'terms_of_payment': u'123', u'reference': 17180711882772, u'bill_of_lading_no': u'123', u'del_notes': [{u'delivery_note_no': '321', u'delivery_note_Date': u'03/07/2017'}], u'buyer_name': u'buyerSample', u'narration': u'Narration', u'carrier_name': u'Carry', u'orders': [u'MM/17-18/07/PO11882772'], u'address_line1': u'Address1234', u'buyer_tin_no': u'123', u'despatch_doc_no': u'MM/-//PO', u'destination': u'Chennai', u'party_ledger': {u'amount': 0, u'is_deemeed_positive': True}, u'voucher_foreign_key': u'17180711882772', u'buyer_state': u'State1234', u'party_ledger_tax': {u'amount': 12, u'entry_rate': 24, u'name': u'name12q', u'is_deemeed_positive': True}, u'voucher_typeName': u'Sales', u'despatched_through': u'Lorry', u'voucher_no': 17180711882772, u'terms_of_delivery_1': u'Check', u'tally_company_name': u'Mieone', u'items': [{u'ledger_name': u'LedgerName', u'name': u'Womens T-Shirt:Silly People Womens casual T-Shirt', u'is_deemeed_positive': True, u'rate': 456.0, u'rate_unit': u'123', u'amount': 123.0, u'actual_qty': 1.0, u'unit': u'mrp', u'billed_qty': 1.0}], u'type_of_dealer': u'Dealer123', u'buyer_cst_no': u'1223', u'dt_of_voucher': u'03/07/2017'}
        try:
            status = bridge.sales_invoice(obj)
            print status
            return status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

def apiSalesReturnsData():
    url = dns + 'GetSalesReturns/';
    resp_data = requests.post(url = url, data = {})
    for obj in resp_data.json():
        try:
            print(obj)
            status = bridge.sales_returns(obj)
            print status
            return status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

def apiPurchaseInvoiceData():
    url = dns + 'GetPurchaseInvoices/';
    resp_data = requests.post(url = url, data = {})
    for key,value in resp_data.json().iteritems():
        try:
            status = bridge.purchase_invoice(value)
            print status
            return status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

def apiPurchaseReturnsData():
    url = dns + 'GetPurchaseReturns/';
    resp_data = requests.post(url = url, data = {})
    for obj in resp_data.json():
        try:
            status = bridge.purchase_returns(obj)
            print status
            return status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

#DONE
#apiItemData()
#apiCustomerData()
#apiSupplierData()

#errors found
#apiPurchaseInvoiceData() - Purchase Not Supported
#apiSalesReturnsData() - Credit Note Not supported
apiSalesInvoiceData()
