import json
import traceback
from tally.tally.tally_wrapper import TallyBridgeApp
from tally.tally.common_exceptions import *
from PullFromStockone.models import *


bridge = TallyBridgeApp(dll="C:\\Users\\stockone\\PycharmProjects\\TallyHolder\\TallyHolder\\tally\\DLL\\TallyBridgeDll.dll")

def push_to_tally(ip, port, data):
    pass

def push_item_master():
    resp_data = ItemMaster.objects.filter(push_status=0)
    for obj in resp_data:
        try:
            status = bridge.item_master(json.loads(obj.data))
            obj.push_status = 1
            obj.save()
        except TallyDataTransferError:
            pass
        except:
            obj.push_status = 9
            obj.save()
            print traceback.format_exc()
    return 0

def push_customer_vendor_master():
    resp_data = CustomerVendorMaster.objects.filter(push_status=0)
    for obj in resp_data:
        print obj
        try:
            status = bridge.customer_and_vendor_master(json.loads(obj.data))
            obj.push_status=1
            obj.save()
        except TallyDataTransferError:
            print traceback.format_exc()
            pass
        except:
            print traceback.format_exc()
            return traceback.format_exc()


def push_sales_invoice_data():
    resp_data = SalesInvoice.objects.filter(push_status=0)
    for obj in resp_data:
        #sample_obj = {u'bill_of_lading_dt': u'03/07/2017', u'other_reference': u'Other Reference', u'terms_of_payment': u'123', u'reference': 17180711882772, u'bill_of_lading_no': u'123', u'del_notes': [{u'delivery_note_no': '321', u'delivery_note_Date': u'03/07/2017'}], u'buyer_name': u'buyerSample', u'narration': u'Narration', u'carrier_name': u'Carry', u'orders': [u'MM/17-18/07/PO11882772'], u'address_line1': u'Address1234', u'buyer_tin_no': u'123', u'despatch_doc_no': u'MM/-//PO', u'destination': u'Chennai', u'party_ledger': {u'amount': 0, u'is_deemeed_positive': True}, u'voucher_foreign_key': u'17180711882772', u'buyer_state': u'State1234', u'party_ledger_tax': {u'amount': 12, u'entry_rate': 24, u'name': u'name12q', u'is_deemeed_positive': True}, u'voucher_typeName': u'Sales', u'despatched_through': u'Lorry', u'voucher_no': 17180711882772, u'terms_of_delivery_1': u'Check', u'tally_company_name': u'Mieone', u'items': [{u'ledger_name': u'LedgerName', u'name': u'Womens T-Shirt:Silly People Womens casual T-Shirt', u'is_deemeed_positive': True, u'rate': 456.0, u'rate_unit': u'123', u'amount': 123.0, u'actual_qty': 1.0, u'unit': u'mrp', u'billed_qty': 1.0}], u'type_of_dealer': u'Dealer123', u'buyer_cst_no': u'1223', u'dt_of_voucher': u'03/07/2017'}
        try:
            status = bridge.sales_invoice(json.loads(obj.data))
            obj.push_status=1
            obj.save()
        except TallyDataTransferError:
            print traceback.format_exc()
            pass
        except:
            print traceback.format_exc()
            #return traceback.format_exc()
    return 0

def push_sales_return_data():
    resp_data = SalesReturn.objects.filter(push_status=0)
    for obj in resp_data:
        try:
            print(obj)
            status = bridge.sales_returns(json.loads(obj.data))
            print status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

def push_purchase_invoice_data():
    resp_data = PurchaseInvoice.objects.filter(push_status=0)
    for obj in resp_data.iteritems():
        try:
            status = bridge.purchase_invoice(json.loads(obj))
            print status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

def push_purchase_return_data():
    resp_data = PurchaseReturn.objects.filter(push_status=0)
    for obj in resp_data:
        try:
            status = bridge.purchase_returns(json.loads(obj))
            print status
        except:
            print traceback.format_exc()
            return traceback.format_exc()

#push_item_master()
#push_customer_vendor_master()
push_sales_invoice_data()
