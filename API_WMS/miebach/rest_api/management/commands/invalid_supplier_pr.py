from django.core.management import BaseCommand
import os
import logging
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from miebach_admin.models import *
# from rest_api.views.inbound import *
from rest_api.views.common import *
import datetime

def init_logger(log_file):
    log = logging.getLogger(log_file)
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    return log


log = init_logger('logs/invalid_supplier_pr.log')

class Command(BaseCommand):
    help = "invalid supplier pr"
    def handle(self, *args, **options):
        mistake_pr = []
        all_prs = PendingPR.objects.filter().exclude(final_status__in=['pr_converted_to_po', 'cancelled', 'rejected'])
        for pr in all_prs:
            dept_user = pr.wh_user
            storeObj = get_admin(dept_user)
            lineItems = pr.pending_prlineItems.filter(quantity__gt=0)
            for rec in lineItems:
                updatedLineItem = TempJson.objects.filter(model_name='PENDING_PR_PURCHASE_APPROVER', model_id=rec.id)
                if updatedLineItem.exists():
                    json_data = eval(updatedLineItem[0].model_json)
                    # print json_data
                    supplierId = json_data['supplier_id']
                    supplierQs = SupplierMaster.objects.filter(user=storeObj.id, supplier_id=supplierId)
                    if supplierQs.exists():
                        supplier_gst_num = supplierQs[0].tin_number
                        if supplier_gst_num and json_data['tax'] <= 0:
                            print supplier_gst_num
                            print json_data['tax']
                            if pr.full_pr_number not in mistake_pr:
                                mistake_pr.append(pr.full_pr_number)
        print mistake_pr
        self.stdout.write("Updation Completed")
