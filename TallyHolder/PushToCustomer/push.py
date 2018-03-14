activate_this = 'C:\\Users\\Headrun\\Downloads\\TallyHolder\\TallyHolder\\headrunvenv\\Scripts\\activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
import os, sys
sys.path.append('C:\\Users\\Headrun\\Downloads\\TallyHolder\\TallyHolder\\TallyHolder')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TallyHolder.settings")
import django
django.setup()
import json
import traceback

from tally.tally.tally_wrapper import TallyBridgeApp
from tally.tally.common_exceptions import *
from PullFromStockone.models import *
bridge = TallyBridgeApp(dll="C:\\Users\\Headrun\\Downloads\\TallyHolder\\TallyHolder\\TallyHolder\\tally\\DLL\\TallyBridgeDll.dll")

def push_to_tally(ip, port, data):
    pass

def push_item_master():
    resp_data = ItemMaster.objects.filter(push_status__in=[0,9], data__icontains='SKUCODE-1')
    for obj in resp_data:
        try:
            print obj.data
            d = json.loads(obj.data)
            status = bridge.item_master(d)
            obj.push_status = 1
            obj.save()
        except TallyDataTransferError:
            print traceback.format_exc()
            if 'Duplicate Entry!' in TallyDataTransferError['message'] or 'already exists' in TallyDataTransferError['message']:
                obj.push_status = 1
                obj.save()
            pass
        except:
            obj.push_status = 9
            obj.save()
            print traceback.format_exc()
    return 0

def push_customer_vendor_master():
    resp_data = CustomerVendorMaster.objects.filter(push_status__in=[0,9])
    for obj in resp_data:
        try:
            d = json.loads(obj.data)
            print(d)
            status = bridge.customer_and_vendor_master(d)
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
        try:
            d = json.loads(obj.data)
            print(d)
            for i in d['items']:
                i['actual_qty'] = int(i['actual_qty'])
                i['billed_qty'] = int(i['billed_qty'])
            status = bridge.sales_invoice(d)
            obj.push_status=1
            obj.save()
        except TallyDataTransferError:
            print traceback.format_exc()
            pass
        except:
            print traceback.format_exc()
            return traceback.format_exc()
    return 0

def push_sales_return_data():
    resp_data = SalesReturn.objects.filter(push_status=0)
    for obj in resp_data:
        try:
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
            return tpush_customer_vendor_master()
            return traceback.format_exc()

#push_item_master()
#push_customer_vendor_master()
push_sales_invoice_data()
