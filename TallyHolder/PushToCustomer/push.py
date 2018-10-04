import os, sys
activate_this = os.path.abspath('../stockone/Scripts/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))
#sys.path.append('C:\\Users\\stockone\\Downloads\\Project\\WMS_ANGULAR\\TallyHolder')
sys.path.append('C:\\Users\\stockone\\Documents\\tally_partial_invoices\\WMS_ANGULAR\\TallyHolder')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TallyHolder.settings")
import django
django.setup()
import json
import traceback

from tally.tally.tally_wrapper import TallyBridgeApp
from tally.tally.common_exceptions import *
from PullFromStockone.models import *
from tally.tally.logger_file import *

bridge = TallyBridgeApp(dll="C:\\Users\\stockone\\Documents\\tally_partial_invoices\\WMS_ANGULAR\\TallyHolder\\tally\\DLL\\TallyBridgeDll.dll")

log = init_logger('logs/db_to_tally.log')

def push_to_tally(ip, port, data):
    pass

def push_item_master():
    log.info('------Item Master started Data transfer to Tally-----')
    resp_data = ItemMaster.objects.filter(push_status__in=[0,9])
    for obj in resp_data:
        try:
            d = json.loads(obj.data)
            status = bridge.item_master(d)
            obj.push_status = 1
            obj.save()
            log.info('Data Inserted to Tally : ' + str(obj))
        except TallyDataTransferError:
            log.debug(traceback.format_exc())
            if 'Duplicate Entry!' in TallyDataTransferError.message or 'already exists' in TallyDataTransferError.message:
                obj.push_status = 1
                obj.save()
                log.info('Duplicate Entry : ' + str(obj))
            pass
        except:
            obj.push_status = 9
            obj.save()
            log.info('Error Occured : ' + str(obj))
            log.debug(traceback.format_exc())
            print traceback.format_exc()
    log.info('------Item Master Completed Data transfer to Tally-----')
    return 0

def push_customer_vendor_master():
    log.info('------Customer Master started Data transfer to Tally-----')
    resp_data = CustomerVendorMaster.objects.filter(push_status__in=[0,9])
    for obj in resp_data:
        try:
            d = json.loads(obj.data)
            status = bridge.customer_and_vendor_master(d)
            obj.push_status=1
            obj.save()
            log.info('Data Inserted to Tally : ' + str(obj))
        except TallyDataTransferError:
            log.debug(traceback.format_exc())
            if 'Duplicate Entry!' in TallyDataTransferError.message or 'already exists' in TallyDataTransferError.message:
                obj.push_status = 1
                obj.save()
                log.info('Duplicate Entry : ' + str(obj))
            pass
        except:
            obj.push_status = 9
            obj.save()
            log.info('Error Occured : ' + str(obj))
            log.debug(traceback.format_exc())
            print traceback.format_exc()
    log.info('------Customer Master Completed Data transfer to Tally-----')
    return 0

def push_sales_invoice_data():
    log.info('------Sales Invoice started Data transfer to Tally-----')
    resp_data = SalesInvoice.objects.filter(push_status=0)
    for obj in resp_data:
        try:
            d = json.loads(obj.data)
            for i in d['items']:
                i['actual_qty'] = int(i['actual_qty'])
                i['billed_qty'] = int(i['billed_qty'])
            status = bridge.sales_invoice(d)
            obj.push_status=1
            obj.save()
            log.info('Data Inserted to Tally : ' + str(obj))
        except TallyDataTransferError:
            log.debug(traceback.format_exc())
            if 'Duplicate Entry!' in TallyDataTransferError.message or 'already exists' in TallyDataTransferError.message:
                obj.push_status = 1
                obj.save()
                log.info('Duplicate Entry : ' + str(obj))
            pass
        except:
            obj.push_status = 9
            obj.save()
            log.info('Error Occured : ' + str(obj))
            log.debug(traceback.format_exc())
            print traceback.format_exc()
    log.info('------Sales Invoice Completed Data transfer to Tally-----')
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
            return traceback.format_exc()
