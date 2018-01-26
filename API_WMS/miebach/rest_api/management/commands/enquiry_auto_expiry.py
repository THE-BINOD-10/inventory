from django.core.management import BaseCommand
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from miebach_admin.models import *
from utils import *
from datetime import datetime, timedelta

log = init_logger('logs/auto_expiry_enq_orders.log')

class Command(BaseCommand):
    """
    Deleting Enquiry Orders which are 10 days ago
    """
    help = "Delete 10 days old Enquiry Orders"

    def __init__(self, expiry_days=10):
        self.expiry_days = expiry_days

    def handle(self, *args, **options):
        self.stdout.write("Started Updating")
        old_enqs = EnquiryMaster.objects.filter(updation_date__lt=datetime.now()-timedelta(days=self.expiry_days))
        old_enq_ids = old_enqs.values_list('enquiry_id', 'user', 'customer_name')
        log.info("Deleted records in Enquiry Master::%s" %(old_enq_ids))
        log.info(old_enqs.delete())